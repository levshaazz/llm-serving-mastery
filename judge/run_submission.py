#!/usr/bin/env python3
"""
run_submission.py — measure ONE leaderboard submission exactly the way the judge does.

    python judge/run_submission.py --repo https://github.com/<you>/<repo> --ref round-01 --out runs/me
    python judge/run_submission.py --repo ./submission-template --out runs/reference      # a local directory
    python judge/run_submission.py --repo judge/rounds/round-01/mirrors/<who>.git --ref <sha> \
        --out … --sandbox docker                                                           # the judge itself

Pipeline (each step is recorded in <out>/result.json; logs next to it):
  1. fetch     clean checkout of the ref (git URL, bare mirror, or a copy of a local directory)
  2. contract  submission.yaml + JOURNAL.md, and either a self-contained Dockerfile or
               prepare.sh + serve.sh + pyproject.toml + uv.lock
  3. gpu       the GPU and the port must be free before we start
  4. start     Dockerfile → build then offline run; else networked `prepare.sh` followed by offline `serve.sh`;
               wait until /v1/models lists "submission"
  5. smoke     one streaming chat completion must return text
  6. canary    a few speed-style prompts answered at rest (compared with the same prompts under load, step 8)
  7. quality   lm-eval (GSM8K, IFEval, MMLU-Pro) on a SECRET, seed-chosen subset — not the public first N
  8. speed     GuideLLM at each concurrency level, natural-text prompts drawn with the secret seed;
               canaries re-sent under load; only steady state is measured (one wave of warm-up and cool-down)
  9. stop      kill the process group / container, wait until the GPU is free again

Failure classes, recorded in result.json:
  ok=false, judge_error=false   the submission failed a step → the round scores 0
  ok=false, judge_error=true    the judge failed (GPU busy, a crash in this script) → rerun, never scored

The judge's tools (lm-eval, GuideLLM, datasets) run in the judge's Python with their own HF cache; the
submission gets its own environment from its uv.lock, its own HF cache, and an allow-listed environment.
The secret seed ($JUDGE_SEED) is never written to a log or to result.json.
"""
import argparse, concurrent.futures, datetime as dt, difflib, glob, hashlib, importlib.metadata, json, os, pathlib
import platform, random, shutil, signal, subprocess, sys, tempfile, threading, time
import urllib.error, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
DEVNULL = subprocess.DEVNULL
MMLU_PRO_SUBJECTS = ["biology", "business", "chemistry", "computer_science", "economics", "engineering", "health",
                     "history", "law", "math", "other", "philosophy", "physics", "psychology"]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), text=True, capture_output=True, stdin=DEVNULL, **kw)


class Step(Exception):
    """The submission failed a step: the run stops and the round scores 0."""


class JudgeError(Exception):
    """The judge failed (not the student): the run must be repeated, never scored."""


class Deadline:
    """One wall-clock budget for the entire run, not a fresh timeout for every step."""

    def __init__(self, seconds):
        self.seconds = seconds
        self.end = time.monotonic() + seconds

    def timeout(self, cap, phase):
        left = self.end - time.monotonic()
        if left <= 0:
            raise Step(f"over the per-submission time budget of {self.seconds} s during {phase}")
        return max(1, min(cap, left))

    def check(self, phase):
        self.timeout(1, phase)


class PhaseDeadline:
    """A phase budget capped by the submission-wide deadline."""

    def __init__(self, parent, seconds, label):
        self.parent = parent
        self.seconds = seconds
        self.label = label
        self.end = min(parent.end, time.monotonic() + seconds)

    def timeout(self, cap, phase):
        self.parent.check(phase)
        left = self.end - time.monotonic()
        if left <= 0:
            raise Step(f"{self.label} exceeded its total budget of {self.seconds} s during {phase}")
        return max(1, min(cap, left))

    def check(self, phase):
        self.timeout(1, phase)


# ── 1. fetch ─────────────────────────────────────────────────────────────────────────────
def is_git_dir(p):
    p = pathlib.Path(p)
    return p.is_dir() and (((p / "HEAD").is_file() and (p / "objects").is_dir()) or (p / ".git").exists())


def fetch(repo, ref, dest, deadline):
    if dest.exists():
        shutil.rmtree(dest)
    if os.path.isdir(repo) and not is_git_dir(repo):
        shutil.copytree(repo, dest, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git", "._*"))
        return {"source": "local", "path": os.path.abspath(repo), "commit": None}
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = sh(["git", "clone", "--quiet", "--no-checkout", repo, str(dest)], env=env,
           timeout=deadline.timeout(600, "git clone"))
    if r.returncode:
        raise Step(f"git clone failed: {r.stderr.strip()[-500:]}")
    r = sh(["git", "-C", str(dest), "checkout", "--quiet", ref or "HEAD"], env=env,
           timeout=deadline.timeout(300, "git checkout"))
    if r.returncode:
        raise Step(f"git checkout {ref!r} failed: {r.stderr.strip()[-500:]}")
    sha = sh(["git", "-C", str(dest), "rev-parse", "HEAD"]).stdout.strip()
    shutil.rmtree(dest / ".git", ignore_errors=True)   # the submission runs without its history
    return {"source": "git", "repo": repo, "ref": ref, "commit": sha}


# ── 2. contract ──────────────────────────────────────────────────────────────────────────
def check_contract(src, cfg):
    import yaml

    c, errors, warnings, meta = cfg["contract"], [], [], {}
    for f in c["required_files"]:
        if not (src / f).is_file():
            errors.append(f"missing {f}")
    docker = (src / "Dockerfile").is_file()
    if not docker:
        for f in c["serve_files"]:
            if not (src / f).is_file():
                errors.append(f"missing {f} (required unless you ship a Dockerfile)")
    if (src / "submission.yaml").is_file():
        try:
            meta = yaml.safe_load((src / "submission.yaml").read_text())
        except yaml.YAMLError as e:
            errors.append(f"submission.yaml is not valid YAML: {e}")
        if not isinstance(meta, dict):
            errors.append("submission.yaml must be a mapping (key: value lines)")
            meta = {}
        for k in c["submission_yaml_keys"]:
            if not meta.get(k):
                errors.append(f"submission.yaml: missing '{k}'")
    if (src / "serve.sh").is_file() and not os.access(src / "serve.sh", os.X_OK):
        warnings.append("serve.sh is not executable (chmod +x); ran it with bash")
    meta = {str(k): str(v)[:200] for k, v in meta.items()}
    return {"ok": not errors, "errors": errors, "warnings": warnings, "mode": "docker" if docker else "serve.sh",
            "submission": meta}


# ── 3. gpu ───────────────────────────────────────────────────────────────────────────────
def gpu_info():
    r = sh("nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader,nounits")
    if r.returncode:
        raise JudgeError("nvidia-smi failed — no GPU?")
    name, total, used, driver = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
    return {"name": name, "memory_total_mib": int(total), "memory_used_mib": int(used), "driver": driver}


def wait_gpu_idle(cfg, kill=False, deadline=None):
    """Wait until the GPU is idle; with kill=True, SIGKILL whatever still holds it (leftovers of a submission)."""
    limit = cfg["server"]["gpu_idle_mib"]
    for _ in range(2 if kill else 1):
        for _ in range(60):
            if deadline:
                deadline.check("waiting for an idle GPU")
            if gpu_info()["memory_used_mib"] <= limit:
                return True
            time.sleep(1)
        if kill:
            for pid in sh("nvidia-smi --query-compute-apps=pid --format=csv,noheader").stdout.split():
                if pid.strip().isdigit() and int(pid) != os.getpid():
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except OSError:
                        pass
    return gpu_info()["memory_used_mib"] <= limit


def port_free(port):
    return sh(f"ss -ltnH 'sport = :{port}'").stdout.strip() == ""


def verify_docker_egress_blocked(cfg, deadline):
    """Fail closed unless a normal judge-network container can run but cannot reach the public Internet."""
    network = cfg["server"]["measurement_network"]
    inspected = sh(["docker", "network", "inspect", network],
                   timeout=deadline.timeout(30, "measurement network inspection"))
    if inspected.returncode:
        raise JudgeError(f"missing Docker network {network!r}; create it with --internal")
    if not json.loads(inspected.stdout)[0].get("Internal"):
        raise JudgeError(f"Docker network {network!r} is not internal")
    base = ["docker", "run", "--rm", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit", "64", "--network", network,
            cfg["server"]["sandbox_image"]]
    healthy = sh(base + ["python", "-c", "print('ok')"],
                 timeout=deadline.timeout(120, "sandbox image preflight"))
    if healthy.returncode:
        raise JudgeError(f"sandbox image preflight failed: {healthy.stderr.strip()[-500:]}")
    probe = sh(base + ["python", "-c",
                       "import socket; s=socket.create_connection(('1.1.1.1',80),5); s.close()"],
               timeout=deadline.timeout(30, "submission egress probe"))
    if probe.returncode == 0:
        raise JudgeError("submission-container egress is open; repair the internal measurement network before scoring")
    return {"blocked": True, "probe": "TCP 1.1.1.1:80 denied"}


# ── 4. start / stop ──────────────────────────────────────────────────────────────────────
def http_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def submission_env(cfg, cache_dir):
    """Only allow-listed variables reach the submission — never JUDGE_*, tokens or the judge's caches."""
    keep = {k: v for k, v in os.environ.items() if k in cfg["server"]["env_allowlist"]}
    keep["HF_HOME"] = str(cache_dir)
    return keep


def start_server(src, cfg, out, tag, sandbox, cache_dir, runtime_dir, deadline, submission):
    port = cfg["server"]["port"]
    log = open(out / "serve.log", "w")
    env = submission_env(cfg, cache_dir)
    os.makedirs(env["HF_HOME"], exist_ok=True)
    if (src / "Dockerfile").is_file() or sandbox == "docker":
        image, name = f"lsm-{tag}".lower(), f"lsm-run-{tag}".lower()
        sh(["docker", "rm", "-f", name])
        if (src / "Dockerfile").is_file():
            try:
                b = subprocess.run(["docker", "build", "-t", image, str(src)], stdout=log, stderr=subprocess.STDOUT,
                                   stdin=DEVNULL,
                                   timeout=deadline.timeout(cfg["server"]["docker_build_timeout_s"], "docker build"))
            except subprocess.TimeoutExpired:
                raise Step(f"docker build took longer than {cfg['server']['docker_build_timeout_s']} s")
            if b.returncode:
                raise Step("docker build failed (see serve.log)")
            run_cmd = [image]
        else:  # the sandbox for serve.sh: the student's code never runs as the judge's user
            common = ["--rm", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                      "--pids-limit", str(cfg["server"]["pids_limit"]), "--ipc=private",
                      "--tmpfs", "/tmp:rw,exec,nosuid,size=16g", "-v", f"{src}:/work:ro",
                      "-v", f"{runtime_dir}:/runtime", "-v", f"{env['HF_HOME']}:/root/.cache/huggingface",
                      "-e", "HF_HOME=/root/.cache/huggingface", "-e", "HOME=/tmp/home",
                      "-e", "UV_CACHE_DIR=/tmp/uv-cache", "-e", "UV_PROJECT_ENVIRONMENT=/runtime/.venv",
                      "-w", "/work"]
            # Bootstrap has egress but receives no judge seed or prompts. Only its ephemeral runtime/cache
            # survive into the measurement container, which runs on the internal network below.
            try:
                prep = subprocess.run(["docker", "run"] + common + [cfg["server"]["sandbox_image"],
                                      "bash", "prepare.sh"], stdout=log, stderr=subprocess.STDOUT, stdin=DEVNULL,
                                      timeout=deadline.timeout(cfg["server"]["docker_build_timeout_s"], "prepare.sh"))
            except subprocess.TimeoutExpired:
                raise Step("prepare.sh exceeded the remaining time budget")
            if prep.returncode:
                raise Step("prepare.sh failed (see serve.log)")
            model_key = "models--" + submission["model"].strip("/").replace("/", "--")
            snapshot = cache_dir / "hub" / model_key / "snapshots" / submission["model_revision"]
            if not snapshot.is_dir():
                raise Step(f"prepare.sh did not cache declared model revision {submission['model_revision']}")
            run_cmd = ["-v", f"{src}:/work:ro", "-v", f"{runtime_dir}:/runtime",
                       "-w", "/work", cfg["server"]["sandbox_image"], "bash", "serve.sh"]
        cmd = ["docker", "run", "--rm", "--name", name, "--gpus", "all", "--read-only",
               "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit",
               str(cfg["server"]["pids_limit"]), "--ipc=private", "--tmpfs", "/tmp:rw,exec,nosuid,size=16g",
               "--tmpfs", "/run:rw,noexec,nosuid,size=64m", "--network", cfg["server"]["measurement_network"],
               "-p", f"{port}:{port}",
               "-v", f"{env['HF_HOME']}:/root/.cache/huggingface", "-e", "HF_HOME=/root/.cache/huggingface",
               "-e", "HOME=/tmp/home", "-e", "UV_CACHE_DIR=/tmp/uv-cache",
               "-e", "UV_PROJECT_ENVIRONMENT=/work/.venv"]
        for k in cfg["server"]["env_allowlist"]:
            if k in env and k not in ("PATH", "HOME"):
                cmd += ["-e", f"{k}={env[k]}"]
        proc = subprocess.Popen(cmd + run_cmd, stdout=log, stderr=subprocess.STDOUT, stdin=DEVNULL,
                                preexec_fn=os.setsid)
        return {"mode": "docker", "proc": proc, "container": name}
    proc = subprocess.Popen(["bash", "serve.sh"], cwd=src, stdout=log, stderr=subprocess.STDOUT, stdin=DEVNULL,
                            preexec_fn=os.setsid, env=env)
    return {"mode": "serve.sh", "proc": proc}


def wait_ready(server, cfg, deadline):
    port, name = cfg["server"]["port"], cfg["server"]["model_name"]
    t0 = time.time()
    while True:
        deadline.check("server startup")
        if server["proc"].poll() is not None:
            raise Step(f"server exited with code {server['proc'].returncode} before becoming ready (see serve.log)")
        try:
            models = http_json(f"http://127.0.0.1:{port}/v1/models").get("data", [])
        except Exception:
            models = None
        if models is not None:
            ids = [m.get("id") for m in models]
            if name in ids:
                m = next(m for m in models if m.get("id") == name)
                return {"ready_after_s": round(time.time() - t0, 1), "root": m.get("root")}
            if ids:
                raise Step(f"/v1/models lists {ids}, expected '{name}' (use --served-model-name {name})")
        time.sleep(5)


def stop_server(server, cfg):
    if not server:
        return
    if server["mode"] == "docker":
        sh(["docker", "stop", "-t", str(cfg["server"]["shutdown_grace_s"]), server["container"]])
        sh(["docker", "rm", "-f", server["container"]])
    p = server["proc"]
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if p.poll() is not None:
            break
        try:
            os.killpg(os.getpgid(p.pid), sig)
            p.wait(timeout=cfg["server"]["shutdown_grace_s"])
        except Exception:
            continue


def cleanup_submission_state(cfg, cache_dir, runtime_dir):
    """Remove files even when a root-running container created them on a Linux bind mount."""
    shutil.rmtree(cache_dir, ignore_errors=True)
    shutil.rmtree(runtime_dir, ignore_errors=True)
    if (cache_dir.exists() or runtime_dir.exists()) and shutil.which("docker"):
        sh(["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "-v", f"{cache_dir}:/state/cache",
            "-v", f"{runtime_dir}:/state/runtime", cfg["server"]["sandbox_image"],
            "sh", "-c", "rm -rf /state/cache/* /state/cache/.[!.]* /state/runtime/* /state/runtime/.[!.]* 2>/dev/null || true"])
        shutil.rmtree(cache_dir, ignore_errors=True)
        shutil.rmtree(runtime_dir, ignore_errors=True)


# ── 5. smoke ─────────────────────────────────────────────────────────────────────────────
def stream_chat(body, port, timeout):
    """POST a streaming chat completion; return (text, n_chunks). Raises Step on any protocol/network error."""
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    text, chunks = [], 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for line in r:
                line = line.decode(errors="replace").strip()
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                ch = json.loads(line[6:]).get("choices") or [{}]
                piece = (ch[0].get("delta") or {}).get("content") or ""
                if piece:
                    chunks += 1
                    text.append(piece)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Step(f"chat completion failed: {type(e).__name__}: {e}")
    return "".join(text), chunks


def smoke(cfg, deadline):
    body = {"model": cfg["server"]["model_name"], "stream": True, "max_tokens": 32, "temperature": 0,
            "messages": [{"role": "user", "content": "Say hello in five words."}]}
    text, chunks = stream_chat(body, cfg["server"]["port"], deadline.timeout(120, "smoke test"))
    if not text.strip():
        raise Step("smoke test: streaming chat completion returned no text")
    if chunks < 2:
        raise Step("smoke test: response was not streamed (expected several SSE chunks)")
    return {"text": text.strip()[:200], "chunks": chunks}


# ── prompts (secret) ─────────────────────────────────────────────────────────────────────
def build_prompts(cfg, seed, path):
    """Natural-text prompts of ~prompt_tokens tokens (judge tokenizer), drawn with the secret seed.
    Returns the canary prompts; writes the speed prompts to `path` (never published)."""
    from datasets import load_dataset
    from transformers import AutoTokenizer
    s, k = cfg["speed"], cfg["canary"]["count"]
    tok = AutoTokenizer.from_pretrained(s["tokenizer"], revision=s["tokenizer_revision"])
    ds = load_dataset(s["corpus"]["path"], s["corpus"]["name"], split=s["corpus"]["split"],
                      revision=s["corpus"]["revision"])
    paras = [t.strip() for t in ds["text"] if len(t.strip()) > 200 and not t.strip().startswith("=")]
    random.Random(seed).shuffle(paras)
    need = k + s["requests_per_level"] + 2 * max(s["concurrency"])
    prefix = s["instruction"] + "\n\n"
    budget = s["prompt_tokens"] - len(tok.encode(prefix))
    rows, cur = [], []
    for p in paras:
        cur.append(p)
        ids = tok.encode("\n\n".join(cur))
        if len(ids) >= budget:
            rows.append(prefix + tok.decode(ids[:budget]))
            cur = []
            if len(rows) == need:
                break
    if len(rows) < need:
        raise JudgeError(f"corpus too small for {need} prompts")
    with open(path, "w") as f:
        for r in rows[k:]:
            f.write(json.dumps({"prompt": r, "output_tokens_count": s["output_tokens"]}) + "\n")
    return rows[:k], tok


def speed_body(cfg, prompt):
    """Mirror the GuideLLM request shape and configured extras for hidden probes."""
    return {"model": cfg["server"]["model_name"], "stream": True,
            "stream_options": {"include_usage": True, "continuous_usage_stats": True},
            "max_completion_tokens": cfg["speed"]["output_tokens"], "ignore_eos": True,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            **cfg["speed"]["extra_body"]}


def similarity(a, b, n=600):
    return difflib.SequenceMatcher(None, a[:n], b[:n]).ratio()


# ── 7. quality ───────────────────────────────────────────────────────────────────────────
def prepare_quality_datasets(cfg, deadline):
    """Fetch only declared immutable revisions before the offline measurement phase."""
    from datasets import load_dataset

    pinned = {}
    for task, spec in cfg["quality"]["tasks"].items():
        deadline.check(f"prefetching {task}")
        kwargs = {"revision": spec["dataset_revision"]}
        if spec.get("dataset_name"):
            kwargs["name"] = spec["dataset_name"]
        load_dataset(spec["dataset_path"], **kwargs)
        pinned[task] = {"path": spec["dataset_path"], "name": spec.get("dataset_name"),
                        "revision": spec["dataset_revision"]}
    return pinned


def quality_samples(cfg, task, seed):
    spec, rng = cfg["quality"]["tasks"][task], random.Random(f"{seed}:{task}")
    if task == "mmlu_pro":
        return {f"mmlu_pro_{s}": sorted(rng.sample(range(spec["pool"]), spec["n"])) for s in MMLU_PRO_SUBJECTS}
    return {task: sorted(rng.sample(range(spec["pool"]), spec["n"]))}


def run_quality(cfg, out, seed, judge_env, deadline):
    q, port, name = cfg["quality"], cfg["server"]["port"], cfg["server"]["model_name"]
    scores, qdir = {}, out / "lm_eval"
    for task, spec in q["tasks"].items():
        model_args = (f"model={name},base_url=http://127.0.0.1:{port}/v1/chat/completions,"
                      f"num_concurrent={q['num_concurrent']},max_retries=3,tokenized_requests=False,"
                      f"tokenizer_backend=None")
        cmd = [sys.executable, "-m", "lm_eval", "--model", "local-chat-completions", "--model_args", model_args,
               "--tasks", task, "--samples", json.dumps(quality_samples(cfg, task, seed)),
               "--apply_chat_template", "--fewshot_as_multiturn", "--output_path", str(qdir / task), "--seed", "1234"]
        if "num_fewshot" in spec:
            cmd += ["--num_fewshot", str(spec["num_fewshot"])]
        if "gen_kwargs" in spec:
            cmd += ["--gen_kwargs", spec["gen_kwargs"]]
        shutil.rmtree(qdir / task, ignore_errors=True)
        with open(out / f"lm_eval-{task}.log", "w") as log:
            log.write(f"lm_eval --tasks {task}  (subset chosen with the secret seed)\n\n"); log.flush()
            try:
                r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=DEVNULL,
                                   timeout=deadline.timeout(spec["timeout_s"], f"lm-eval {task}"), env=judge_env)
            except subprocess.TimeoutExpired:
                raise Step(f"lm-eval {task}: timed out after {spec['timeout_s']} s")
        if r.returncode:
            tail = open(out / f"lm_eval-{task}.log").read()[-3000:]
            if "ModuleNotFoundError" in tail or "ImportError" in tail:
                raise JudgeError(f"lm-eval {task}: the judge's environment is missing a package (see log)")
            raise Step(f"lm-eval {task} failed with code {r.returncode} (see lm_eval-{task}.log)")
        files = sorted(glob.glob(str(qdir / task / "**" / "results_*.json"), recursive=True))
        if not files:
            raise JudgeError(f"lm-eval {task}: no results file")
        res = json.load(open(files[-1]))["results"]
        if task not in res or spec["metric"] not in res[task]:
            raise JudgeError(f"lm-eval {task}: metric {spec['metric']!r} not in {sorted(res.get(task, {}))}")
        scores[task] = round(float(res[task][spec["metric"]]), 4)
    return scores


# ── 8. speed ─────────────────────────────────────────────────────────────────────────────
def run_speed(cfg, out, seed, prompts_path, canaries, judge_env, deadline):
    """Returns ({level: metrics}, {level: [(canary index, text under load)]})."""
    s, port, name = cfg["speed"], cfg["server"]["port"], cfg["server"]["model_name"]
    levels, under_load = {}, {}
    for li, c in enumerate(s["concurrency"]):
        path = out / f"guidellm-c{c}.json"
        path.unlink(missing_ok=True)
        # One full wave of `c` requests is warm-up (every stream prefilling at once) and one is
        # cool-down (the drain, when fewer than `c` streams are left): only steady state is measured.
        n = s["requests_per_level"] + 2 * c
        backend = json.dumps({"kind": "openai_http", "target": f"http://127.0.0.1:{port}", "model": name,
                              "request_format": "/v1/chat/completions", "extras": {"body": s["extra_body"]}})
        profile = json.dumps({"kind": "concurrent", "streams": c,
                              "warmup": {"value": c, "mode": "requests"},
                              "cooldown": {"value": c, "mode": "requests"}})
        # load_kwargs.split: without it datasets returns a DatasetDict, which guidellm 0.7.4 cannot map
        data = json.dumps({"kind": "json_file", "path": str(prompts_path), "load_kwargs": {"split": "train"}})
        cmd = ["guidellm", "run", "--backend", backend, "--profile", profile,
               "--constraint", f"kind=max_requests,count={n}", "--data", data,
               "--tokenizer", f"kind=huggingface_auto,model={s['tokenizer']}",
               "--seed", f"kind=static,value={seed}",
               "--output", f"kind=json,path={path}", "--disable-console-interactive"]
        shown = ["kind=static,value=***" if x.startswith("kind=static,value=") else x for x in cmd]
        mine = list(range(li, len(canaries), len(s["concurrency"])))      # canaries fired at this level
        texts = {}

        def fire(i, delay):
            time.sleep(delay)
            try:
                texts[i] = stream_chat(speed_body(cfg, canaries[i]), port,
                                       deadline.timeout(900, f"canary at concurrency {c}"))[0]
            except Step:
                texts[i] = ""
        threads = [threading.Thread(target=fire, args=(i, s["canary_delay_s"] + j * s["canary_spacing_s"]), daemon=True)
                   for j, i in enumerate(mine)]
        with open(out / f"guidellm-c{c}.log", "w") as log:
            log.write(" ".join(shown) + "\n\n"); log.flush()
            for t in threads:
                t.start()
            try:
                r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=DEVNULL,
                                   timeout=deadline.timeout(s["timeout_s"], f"GuideLLM at concurrency {c}"),
                                   env=judge_env)
            except subprocess.TimeoutExpired:
                raise Step(f"GuideLLM at concurrency {c}: timed out after {s['timeout_s']} s")
            for t in threads:
                t.join(timeout=900)
        if r.returncode or not path.exists():
            raise Step(f"GuideLLM at concurrency {c} failed (see guidellm-c{c}.log)")
        levels[str(c)] = parse_guidellm(json.load(open(path)), s["output_tokens"])
        _redact_seed(path)
        under_load[str(c)] = [(i, texts.get(i, "")) for i in mine]
    return levels, under_load


def _redact_seed(path):
    """GuideLLM stores its config (incl. the seed) in the report; keep the report, drop the seed."""
    raw = open(path).read()
    rep = json.loads(raw)
    def scrub(x):
        if isinstance(x, dict):
            return {k: ("***" if k in ("random_seed", "seed") else scrub(v)) for k, v in x.items()}
        if isinstance(x, list):
            return [scrub(v) for v in x]
        return x
    json.dump(scrub(rep), open(path, "w"))


def _dig(d, path):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def parse_guidellm(report, expected_output_tokens):
    """Steady-state numbers of one GuideLLM run (schema of guidellm 0.7.x, pinned in requirements.lock)."""
    b = report["benchmarks"][0]
    m, sm = b["metrics"], b["scheduler_metrics"]
    fields = {
        "output_tok_s": "output_tokens_per_second.successful.mean",
        "ttft_p50_ms": "time_to_first_token_ms.successful.median",
        "ttft_p95_ms": "time_to_first_token_ms.successful.percentiles.p95",
        "tpot_p50_ms": "time_per_output_token_ms.successful.median",
        "output_tokens_mean": "output_token_count.successful.mean",
        "requests_ok": "request_totals.successful",
    }
    got = {k: _dig(m, p) for k, p in fields.items()}
    missing = [k for k, v in got.items() if v is None]
    if missing:  # a schema change must never turn into a silent 0 for a student
        raise JudgeError(f"GuideLLM report lacks {missing} — schema changed? (version pinned in requirements.lock)")
    return {
        "output_tok_s": round(got["output_tok_s"], 2),
        "ttft_p50_s": round(got["ttft_p50_ms"] / 1000, 4),
        "ttft_p95_s": round(got["ttft_p95_ms"] / 1000, 4),
        "tpot_p50_ms": round(got["tpot_p50_ms"], 2),
        "output_tokens_mean": got["output_tokens_mean"],
        "output_tokens_expected": expected_output_tokens,
        "requests_ok": got["requests_ok"],
        "requests_failed": (_dig(m, "request_totals.errored") or 0) + (_dig(m, "request_totals.incomplete") or 0),
        "measured_s": round(sm["measure_end_time"] - sm["measure_start_time"], 1),
    }


def provenance(config_path):
    """Information needed to reproduce and audit a measurement without exposing the seed."""
    packages = {}
    for name in ("lm_eval", "guidellm", "datasets", "transformers", "PyYAML"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    rev = sh(["git", "-C", str(HERE.parent), "rev-parse", "HEAD"]).stdout.strip() or None
    dirty = bool(sh(["git", "-C", str(HERE.parent), "status", "--porcelain", "--untracked-files=no"]).stdout.strip())
    raw = pathlib.Path(config_path).read_bytes()
    lock_path = HERE / "requirements.lock"
    lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest() if lock_path.is_file() else None
    complete = bool(rev and lock_sha and not dirty and all(packages.values()))
    return {"complete": complete, "judge_commit": rev, "judge_dirty": dirty,
            "config_sha256": hashlib.sha256(raw).hexdigest(), "dependency_lock_sha256": lock_sha,
            "python": platform.python_version(),
            "platform": platform.platform(), "packages": packages}


def verify_model_identity(contract, ready):
    declared = contract["submission"]["model"].strip().rstrip("/").lower()
    root = str(ready.get("root") or "").strip().rstrip("/").split("@", 1)[0].lower()
    if not root:
        raise Step("/v1/models must expose a non-empty root for model provenance")
    if root != declared:
        raise Step(f"/v1/models root {ready.get('root')!r} does not match declared model {contract['submission']['model']!r}")


def canary_evidence(cfg, tokenizer, at_rest, under_load):
    pairs = [(at_rest[i], text) for level in under_load.values() for i, text in level]
    sims = [similarity(a, b) for a, b in pairs]
    lengths = [len(tokenizer.encode(text, add_special_tokens=False)) for _, text in pairs]
    normalized = [" ".join(text.lower().split()) for _, text in pairs if text.strip()]
    unique_share = len({hashlib.sha256(x.encode()).hexdigest() for x in normalized}) / len(pairs) if pairs else 0
    minimum = int(cfg["scoring"]["min_output_share"] * cfg["speed"]["output_tokens"])
    return {"count": len(pairs),
            "similarity_mean": round(sum(sims) / len(sims), 3) if sims else None,
            "similarity_min": round(min(sims), 3) if sims else None,
            "empty_under_load": sum(1 for _, text in pairs if not text.strip()),
            "output_tokens_min": min(lengths) if lengths else None,
            "output_tokens_each": lengths,
            "output_tokens_required": minimum,
            "short_outputs": sum(1 for n in lengths if n < minimum),
            "unique_output_share": round(unique_share, 3)}


# ── main ─────────────────────────────────────────────────────────────────────────────────
def main():
    import yaml

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="git URL, bare mirror, or a plain local directory")
    ap.add_argument("--ref", default=None, help="commit SHA (from the deadline snapshot) or tag")
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=str(HERE / "config.yaml"))
    ap.add_argument("--sandbox", choices=["none", "docker"], default="none",
                    help="docker: run serve.sh inside a container (the judge); none: self-check on Colab")
    ap.add_argument("--skip-quality", action="store_true")
    ap.add_argument("--skip-speed", action="store_true")
    a = ap.parse_args()

    cfg = yaml.safe_load(open(a.config))
    out = pathlib.Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    seed = int(os.environ.get("JUDGE_SEED", "0"))
    judge_env = dict(os.environ, HF_HOME=os.path.expanduser(cfg["judge_hf_home"]))
    os.environ["HF_HOME"] = judge_env["HF_HOME"]          # datasets/transformers inside this process too
    res = {"started_at": now(), "config_version": cfg["version"], "provenance": provenance(a.config),
           "steps": {}, "ok": False, "judge_error": False}
    res["provenance"]["speed_assets"] = {
        "tokenizer": cfg["speed"]["tokenizer"], "tokenizer_revision": cfg["speed"]["tokenizer_revision"],
        "corpus": cfg["speed"]["corpus"]}
    server, t0, deadline = None, time.time(), Deadline(cfg["budget_s"])
    cache_dir = pathlib.Path(tempfile.mkdtemp(prefix="lsm-submission-hf-"))
    runtime_dir = pathlib.Path(tempfile.mkdtemp(prefix="lsm-submission-runtime-"))

    def budget_alarm(_signum, _frame):
        raise Step(f"over the per-submission time budget of {cfg['budget_s']} s")

    if hasattr(signal, "setitimer"):
        signal.signal(signal.SIGALRM, budget_alarm)
        signal.setitimer(signal.ITIMER_REAL, cfg["budget_s"])

    try:
        src = out / "src"
        if a.sandbox == "docker":
            marker = cfg["server"].get("egress_block_confirmation_env")
            if marker and os.environ.get(marker) != "1":
                raise JudgeError(f"verify the internal measurement network and set {marker}=1 before sandboxed runs")
            res["steps"]["egress"] = verify_docker_egress_blocked(cfg, deadline)
        res["steps"]["fetch"] = fetch(a.repo, a.ref, src, deadline)
        res["steps"]["contract"] = c = check_contract(src, cfg)
        if not c["ok"]:
            raise Step("contract: " + "; ".join(c["errors"]))
        if not wait_gpu_idle(cfg, deadline=deadline):
            raise JudgeError("GPU is busy before start — judge problem, not yours; the run will be repeated")
        if not port_free(cfg["server"]["port"]):
            raise JudgeError(f"port {cfg['server']['port']} is busy before start — judge problem; rerun")
        res["steps"]["gpu"] = gpu_info()
        if not a.skip_quality:
            res["provenance"]["quality_datasets"] = prepare_quality_datasets(cfg, deadline)
        canaries, tokenizer = ([], None) if a.skip_speed else build_prompts(cfg, seed, out / "prompts.jsonl")
        judge_env.update(HF_DATASETS_OFFLINE="1", HF_HUB_OFFLINE="1")
        setup_started = time.monotonic()
        setup_deadline = PhaseDeadline(deadline, cfg["server"]["startup_timeout_s"], "server setup")
        server = start_server(src, cfg, out, out.name, a.sandbox, cache_dir, runtime_dir, setup_deadline,
                              c["submission"])
        ready = wait_ready(server, cfg, setup_deadline)
        ready["ready_after_s"] = round(time.monotonic() - setup_started, 1)
        verify_model_identity(c, ready)
        res["steps"]["start"] = {"mode": server["mode"], **ready,
                                   "declared_revision": c["submission"]["model_revision"]}
        res["steps"]["smoke"] = smoke(cfg, deadline)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(canaries))) as pool:
            futures = [pool.submit(stream_chat, speed_body(cfg, p), cfg["server"]["port"],
                                   deadline.timeout(300, "at-rest canaries")) for p in canaries]
            at_rest = [f.result()[0] for f in futures]
        errors = []  # quality and speed are independent: a failure in one must not hide the other
        phases = (["quality"] if not a.skip_quality else []) + (["speed"] if not a.skip_speed else [])
        random.Random(f"{seed}:phase-order").shuffle(phases)
        res["steps"]["phase_order"] = phases
        for phase in phases:
            deadline.check(phase)
            try:
                if phase == "quality":
                    res["steps"]["quality"] = run_quality(cfg, out, seed, judge_env, deadline)
                else:
                    levels, under_load = run_speed(cfg, out, seed, out / "prompts.jsonl", canaries, judge_env,
                                                   deadline)
                    res["steps"]["speed"] = levels
                    res["steps"]["canary"] = canary_evidence(cfg, tokenizer, at_rest, under_load)
            except Step as e:
                errors.append(f"{phase}: {e}")
        if errors:
            raise Step("; ".join(errors))
        res["ok"] = True
    except Step as e:
        res["error"] = str(e)
    except JudgeError as e:
        res["error"], res["judge_error"] = f"JUDGE ERROR: {e}", True
    except Exception as e:  # a crash in this script must never look like a student failure
        res["error"], res["judge_error"] = f"JUDGE ERROR {type(e).__name__}: {e}", True
    finally:
        if hasattr(signal, "setitimer"):
            signal.setitimer(signal.ITIMER_REAL, 0)
        stop_server(server, cfg)
        if server and not (wait_gpu_idle(cfg, kill=True) and port_free(cfg["server"]["port"])):
            res.setdefault("warnings", []).append("GPU or port still busy after stop — the next run will detect it")
        res["finished_at"] = now()
        res["elapsed_s"] = round(time.time() - t0, 1)
        (out / "prompts.jsonl").unlink(missing_ok=True)     # the secret prompts never outlive the run
        cleanup_submission_state(cfg, cache_dir, runtime_dir)  # no state is shared between submissions
        json.dump(res, open(out / "result.json", "w"), indent=2)
    print(json.dumps({k: res[k] for k in ("ok", "judge_error", "error") if k in res}))
    return 0 if res["ok"] else (2 if res["judge_error"] else 1)


if __name__ == "__main__":
    sys.exit(main())
