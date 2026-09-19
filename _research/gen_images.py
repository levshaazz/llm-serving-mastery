#!/usr/bin/env python3
"""
gen_images.py — generate the Serega deck illustrations for LLM Serving Mastery.

Style canon and the locked character bible are inherited from the Deep Learning for Search
course (same brand): PREAMBLE + ANTIPATTERN below, Serega's look in _research/mascots.py.
This course's setting: THE KITCHEN AT RUSH HOUR — the model is the cook, requests are orders,
the GPU is the stove, the KV cache is counter space. Serega is the head cook: he wears an
apron over his tunic and KEEPS the green tübetey — never a chef's toque (one hat, always).

API:   https://imgeditor.co/api  (model nano-banana-pro)
Key:   IMAGE_API_KEY (or IMAGE_GENERATION_API_KEY) from .env in the repo root or its parent.

Usage:
  python3 _research/gen_images.py L0             # every L0 plate not yet on disk
  python3 _research/gen_images.py --only L0-03 --force   # redo one plate
  python3 _research/gen_images.py --list
"""
import os, sys, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Masters (full-size PNG from the API) live OUTSIDE git; scripts/optimize_images.py turns them
# into the WebP files the deck ships. Never optimize in place — a lossy pass over the only copy
# destroyed the first set of plates (2026-09-19).
IMG  = ROOT / "_research" / "masters"
BASE_URL = "https://imgeditor.co/api/v1"
MODEL = "nano-banana-pro"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

def load_key():
    names = ("IMAGE_GENERATION_API_KEY", "IMAGE_API_KEY")
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if not env.exists():
            continue
        for line in env.read_text().splitlines():
            line = line.strip()
            for n in names:
                if line.startswith(n + "="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        return v
    raise SystemExit("IMAGE_API_KEY not found (env or .env in repo root / parent)")

API_KEY = load_key()
import requests  # noqa: E402

KITCHEN = (
    " Setting for this course: a small restaurant kitchen drawn as simple flat doodles — a stove, "
    "pans, a ticket rail with order tickets, a serving hatch ('the pass'). When Serega appears he "
    "is the HEAD COOK: a plain white apron over his course-blue tunic, and on his head ONLY his "
    "green tübetey — he NEVER wears a chef's toque or any other hat. Other cooks and guests are "
    "bare-headed stick figures with no green. "
)

PREAMBLE = (
    "Hand-drawn explanatory marker-doodle illustration (the look of a smart, brisk sketch on "
    "paper): thick confident black ink outlines, off-white #FBFAF6 paper background, FLAT colour "
    "fills using only black ink, course blue #2A6FDB, and warm orange #E8743B (no other colours). "
    "Charming, slightly crude, expressive minimal stick figures. Flat 2D only, no perspective, no "
    "shading, no gradients. Composition: clean, generous white space; figures fill 60–80% of the "
    "frame with at least 8–12% empty paper margin on every side; nothing touches the canvas edge; "
    "everything readable from the back of a lecture hall. Hand-lettered labels are HORIZONTAL "
    "ONLY — never tilted, never stacked letter-on-letter, never rotated; properly spaced; spelled "
    "exactly as named in the scene description below. Line weight is uniform across the image "
    "(no thin spidery passages mixed with thick brush passages). "
)
# Serega's locked appearance + the whole recurring cast now live in the character bible
# (_research/mascots.py) — ONE source of truth so the mascots stay consistent across lectures
# and Claude Code sessions. The image-gate (_research/check_images.py) enforces Serega's
# presence per lecture and the green-only-on-the-tübetey palette rule.
from mascots import SEREGA, MASCOTS  # noqa: E402
# Appended to every prompt: kills baked-in text/titles and 3D/photoreal failure modes.
# Stricter than session 0: explicit cap-colour ban list, no header bars, no English style names.
ANTIPATTERN = (
    " STRICT NEGATIVE CONSTRAINTS — the image must NOT include any of the following, under any "
    "circumstances: the words 'Wait But Why', 'WBW', 'doodle', 'sketch', 'style', or ANY style "
    "name or genre label anywhere; a title card, banner header, top header bar, bottom caption "
    "strip, watermark, artist signature, copyright mark, page number, decorative frame or border "
    "around the whole image; ANY text, letters, numbers, words or labels EXCEPT the few short "
    "hand-lettered English labels explicitly named in the scene description above (one label per "
    "named subject, no extras invented); gibberish, scribbled pseudo-text, lorem-ipsum, or asemic "
    "writing anywhere; faux-handwritten squiggles standing in for text; glyph-like marks, "
    "sparkles-shaped-as-letters or pseudo-text INSIDE any burst, firework, explosion, starfield, "
    "speech-cloud or background flourish (bursts contain only short straight strokes — no curves "
    "that resemble letters); rotated/vertical/diagonal text — every label is horizontal; any "
    "second Serega (only one Serega per image, never a reflection or shadow-clone); the colour "
    "GREEN used ANYWHERE except Serega's own skullcap — every OTHER figure (creatures, a knight's "
    "mount, the trickster, the alien, bystanders) is BARE-HEADED and wears no green and no "
    "skullcap; when Serega is absent from the scene there is NO green in the image at all; any "
    "second hat, helmet, hood or cap stacked above/below the green skullcap (Serega wears EXACTLY "
    "ONE piece of headwear — the green tübetey — never two pieces of headwear at once); any "
    "gradient, drop shadow, glow, bloom, halo, ambient occlusion, 3D, isometric projection, "
    "perspective, photorealism, painterly oil/watercolour shading, cel shading, cross-hatching, "
    "stippling; cluttered or busy backgrounds (background must be plain off-white #FBFAF6); "
    "more than four labels in total in one image; thin spidery linework — keep lines thick, "
    "uniform, and confident. All hand-lettered labels must be SHORT real English words, spelled "
    "correctly, sans-serif marker style, horizontal, and ONLY the labels requested by the scene "
    "description — no decorative subtitles, no signatures, no captions. "
    "ADDITIONAL session-3 constraints — large empty letterbox rails are FORBIDDEN: the subject "
    "and its labels must together occupy at least 80% of the canvas width (do not centre a small "
    "drawing in a sea of empty paper). When the warm orange accent is used, it appears ONLY as "
    "thin strokes, small spot fills (≤15% of the canvas area), or short underlines — NEVER as a "
    "large solid fill behind text, NEVER filling the body/cloak/clothing of a major figure, NEVER "
    "as a background wash. Wraiths / shadows / hooded figures / villains are filled in solid "
    "BLACK INK only — pure shadow, not warm-coloured. Any banner motif requested in the scene is "
    "a SLIM RIBBON (≤12% of the canvas height) at top or bottom, never a thick rectangular "
    "header bar that competes with the main subject. Knights / dinosaurs / animals NEVER carry "
    "topic-name signboards, posters, placards, billboards, or banners spelling out the lecture "
    "topic — labels are short tag words floating beside the relevant element only."
)


# (group, filename, aspect, has_serega, scene)
JOBS = [
    ("L0", "L0/L0-01-rush-hour.png", "16:9", True,
     "RUSH HOUR. Serega the head cook stands at ONE stove with one pan, eyes wide, while a long ticket "
     "rail above him overflows with dozens of paper order tickets curling off both ends. Through the "
     "serving hatch behind him a crowd of hungry stick-figure guests leans in, waving forks. A single "
     "small hand-lettered tag beside the rail reads 'rush hour'. Energetic but friendly, not scary."),
    ("L0", "L0/L0-02-one-pan.png", "16:9", True,
     "THE NAIVE KITCHEN. On the left, Serega carefully cooks ONE order in ONE small pan, perfectly "
     "calm. From the pass a very long single-file queue of stick-figure guests snakes across the "
     "whole width of the image and doubles back, the last guests yawning and checking wristwatches. "
     "The last guest holds a small ticket lettered '#64'. One small tag near the pan reads 'one at a "
     "time'. Only these two labels."),
    ("L0", "L0/L0-03-big-wok.png", "16:9", True,
     "CONTINUOUS BATCHING. Serega tosses one huge wok full of many small separate portions at once. "
     "On the left, new order tickets slide into the wok on a little conveyor; on the right, finished "
     "plates slide out to waiting guests who are already eating. Small tags: 'orders in' on the left, "
     "'plates out' on the right. Only these two labels. Busy, joyful, efficient."),
    ("L0", "L0/L0-04-trail.png", "16:9", True,
     "THE COURSE PATH. Four stepping stones climb from left to right, each carrying a small drawing: "
     "one stove; one stove with a big wok; four stoves side by side; a row of little restaurant "
     "buildings. Serega hops from the first stone to the second, apron flying. Hand-lettered labels "
     "under the stones, one each: 'one stove', 'vLLM', 'multi-GPU', 'Kubernetes'."),
    ("L0", "L0/L0-05-scoreboard.png", "16:9", True,
     "THE LEADERBOARD. A kitchen cook-off: three bare-headed stick-figure student cooks at three "
     "stoves race to send plates out, while Serega stands aside holding a big stopwatch and a "
     "clipboard, judging. On the wall hangs a big scoreboard with horizontal bars of different "
     "lengths (bars only, no numbers, no names). One label on the scoreboard frame: 'leaderboard'."),
    ("L0", "L0/L0-06-journal.png", "16:9", True,
     "THE DEFENSE. Serega stands at a small easel presenting a huge open recipe notebook. Across its "
     "two pages runs a hand-drawn line that climbs step by step from bottom-left to top-right, with "
     "tiny sketches of pans at each step. The first step is labelled 'v1' and the last 'v10'. A few "
     "stick-figure listeners sit on stools nodding. Only the labels 'v1' and 'v10'."),
    ("L0", "L0/L0-07-sendoff.png", "16:9", True,
     "THE SEND-OFF. Serega throws open the double doors of the kitchen onto a full, cheerful dining "
     "room, one hand raising a ladle like a salute, apron on. A slim ribbon above the doors reads "
     "'kitchen is open'. Warm, earned, optimistic."),
    ("L01", "L01/L01-01-rush-hour.png", "16:9", True,
     "THE 09:00 INCIDENT. Serega stands at one GPU stove while a wall of order tickets and a long "
     "queue arrive together. One request worked; the production load changed the system. No labels, "
     "no plants, and no food garnish. The green tübetey is the ONLY green object."),
    ("L01", "L01/L01-02-retry-storm.png", "16:9", True,
     "THE RETRY STORM. Serega closes an admission valve while late order tickets loop back, duplicate, "
     "and overflow a bounded conveyor queue. Background workers are bare-headed. Food icons use only "
     "course blue, warm orange, black ink, and off-white. The green tübetey is the ONLY green object."),
    ("L01", "L01/L01-03-stable-system.png", "16:9", True,
     "CONTROLLED FLOW. Serega calmly supervises a bounded queue feeding three coordinated GPU stoves; "
     "simple chart shapes show stable observable operation. The left third remains open for slide copy. "
     "No labels or plants. The green tübetey is the ONLY green object."),
    ("L02", "L02/L02-01-memory-wall.png", "16:9", True,
     "THE MEMORY WALL. In a GPU kitchen, Serega stands between an enormous pantry wall and a small "
     "blazing compute stove. A long conveyor of tiny ingredient cards travels from the pantry to the "
     "stove for every serving; the stove intermittently waits while the conveyor is packed. No labels, "
     "no plants, and no text. The green tübetey is the ONLY green object."),
    ("L02", "L02/L02-02-kv-overflow.png", "16:9", True,
     "TOKEN-BLIND ADMISSION. Serega measures a counter filled with blue memory trays while a few very "
     "long order scrolls consume the space and push the final trays over the edge. A bare-headed queue "
     "manager counts tickets instead of their lengths. No labels or text. The green tübetey is the ONLY "
     "green object."),
    ("L02", "L02/L02-03-predict-measure.png", "16:9", True,
     "PREDICT, MEASURE, RECONCILE. Serega runs a controlled GPU-kitchen experiment: a balance compares "
     "blue memory trays with an orange compute whisk; a probe connects one GPU stove to a monitor with "
     "abstract timeline, roofline, and memory-bar shapes. Leave the leftmost quarter relatively open. "
     "No labels or text. The green tübetey is the ONLY green object."),
]

H = {"Authorization": f"Bearer {API_KEY}"}

def build_prompt(has_serega, scene):
    # Single source of truth = mascots.py: inject the LOCKED `appearance` of every NON-Serega cast
    # member named (by keyword) in the scene, so the canon — not a brief's paraphrase — drives each
    # mascot's look (the same guarantee SEREGA already gets). Keywords are specific (e.g. "victor the
    # vector", "wraith", "ragdoll", "chunk norris", "confabulous") so a generic word never false-triggers.
    low = scene.lower()
    cast = "".join(" Recurring cast — keep this EXACT locked design: " + v["appearance"]
                   for m, v in MASCOTS.items()
                   if m != "serega" and any(kw in low for kw in v["keywords"]))
    return PREAMBLE + (SEREGA if has_serega else "") + KITCHEN + cast + scene + ANTIPATTERN

def generate_one(job, force=False, ref_url=None, model=MODEL):
    group, fname, aspect, has_serega, scene = job
    out = IMG / fname
    if out.exists() and not force:
        print(f"  · skip (exists): {fname}")
        return ("skip", fname)
    out.parent.mkdir(parents=True, exist_ok=True)
    res = "1K" if aspect == "1:1" else "2K"
    # Reference-image mode: only for Serega scenes, and never for the charsheet/portrait
    # itself (it would be circular). A/B-validated: mode=image composes a NEW scene while
    # keeping the character. Requires ref_url to be a public https URL.
    use_ref = bool(ref_url) and has_serega and "charsheet" not in fname and "whoami" not in fname
    if use_ref:
        prompt = ("Use the supplied image ONLY as the character reference for Serega "
                  "(same face, same long black hair, same green Tatar skullcap, same blue tunic). "
                  "Draw a COMPLETELY NEW scene, do not copy the reference's pose or background: "
                  + build_prompt(has_serega, scene))
        body = {"prompt": prompt, "mode": "image", "image_url": ref_url, "model": model,
                "aspect_ratio": aspect, "resolution": res, "num_images": 1, "output_format": "png"}
    else:
        prompt = build_prompt(has_serega, scene)
        body = {"prompt": prompt, "mode": "text", "model": model,
                "aspect_ratio": aspect, "resolution": res,
                "num_images": 1, "output_format": "png"}
    try:
        r = requests.post(f"{BASE_URL}/images/generate", headers=H, json=body, timeout=60)
        j = r.json()
    except Exception as e:
        print(f"  ✗ {fname}: request error {e}")
        return ("error", fname)
    if r.status_code != 200 or not j.get("data", {}).get("task_id"):
        print(f"  ✗ {fname}: generate failed [{r.status_code}] {str(j)[:200]}")
        return ("error", fname)
    task_id = j["data"]["task_id"]
    # poll
    url = None
    for _ in range(120):  # up to ~6 min
        time.sleep(3)
        try:
            s = requests.get(f"{BASE_URL}/images/status", headers=H,
                             params={"task_id": task_id}, timeout=30).json()
        except Exception as e:
            print(f"    … poll retry ({e})")
            continue
        st = s.get("data", {}).get("status")
        if st == "completed":
            url = s["data"].get("image_url")
            break
        if st == "failed":
            print(f"  ✗ {fname}: generation failed {s['data'].get('error')}")
            return ("error", fname)
    if not url:
        print(f"  ✗ {fname}: timed out")
        return ("error", fname)
    try:
        dl = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        dl.raise_for_status()
        out.write_bytes(dl.content)
    except Exception as e:
        print(f"  ✗ {fname}: download error {e} (url={url})")
        return ("error", fname)
    kb = out.stat().st_size // 1024
    print(f"  ✓ {fname}  [{aspect} {res}, {kb} KB]")
    return ("ok", fname)

def main():
    args = [a for a in sys.argv[1:]]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    ref_url = None
    if "--ref" in args:
        idx = args.index("--ref"); ref_url = args[idx+1] if idx+1 < len(args) else None; del args[idx:idx+2]
    model = MODEL
    if "--model" in args:
        idx = args.index("--model"); model = args[idx+1] if idx+1 < len(args) else MODEL; del args[idx:idx+2]
    if "--list" in args:
        for g, f, a, s, _ in JOBS:
            print(f"  [{g}] {f}  {a}  serega={s}")
        print(f"\n  {len(JOBS)} jobs total")
        return
    if not args:
        print(__doc__); return
    only = None
    if "--only" in args:
        idx = args.index("--only"); only = [a for a in args[idx+1:]]; args = args[:idx]
    if only:
        jobs = [j for j in JOBS if any(s in j[1] for s in only)]
    elif args == ["all"]:
        jobs = JOBS
    elif args == ["charsheet"]:
        jobs = [j for j in JOBS if j[1].endswith("serega-charsheet.png")]
    else:
        groups = set(a if a != "char" else "char" for a in args)
        # Позиционный аргумент — ТОЛЬКО имя группы. Неизвестное значение раньше молча
        # игнорировалось, и «gen_images.py L9 --force L9/L9-17-….png» перерисовывал ВСЮ
        # лекцию: 18 плат вместо одной, с потерей уже принятых картинок (2026-09-05).
        # Отбор одного файла делается флагом --only.
        known = {j[0] for j in JOBS}
        unknown = sorted(groups - known)
        if unknown:
            raise SystemExit(
                "не группа: %s\n"
                "  позиционный аргумент — это ГРУППА (%s) либо all/charsheet.\n"
                "  чтобы взять один файл, используй: --only <кусок-имени> [--force]"
                % (", ".join(unknown), ", ".join(sorted(known)[:6]) + ", …"))
        jobs = [j for j in JOBS if j[0] in groups]
    if not jobs:
        raise SystemExit(f"no jobs matched {args}")
    if force and len(jobs) > 1:
        # --force стирает готовые платы. На группе это дорого и необратимо, поэтому
        # требуем явного подтверждения переменной окружения, а не одного флага.
        import os as _os
        if _os.environ.get("GEN_IMAGES_FORCE_MANY") != "1":
            raise SystemExit(
                "--force затронул бы %d плат(ы) — это перерисует уже принятые картинки.\n"
                "  сузь до одной: --only <кусок-имени> --force\n"
                "  если правда нужно всю группу: GEN_IMAGES_FORCE_MANY=1 …" % len(jobs))
    print(f"[gen] {len(jobs)} job(s) · model={model}" + (f" · ref={ref_url[:50]}…" if ref_url else " · text-only"))
    counts = {"ok": 0, "skip": 0, "error": 0}
    errors = []
    for job in jobs:
        st, fname = generate_one(job, force=force, ref_url=ref_url, model=model)
        counts[st] += 1
        if st == "error":
            errors.append(fname)
    print(f"\n[gen] done: {counts['ok']} ok, {counts['skip']} skipped, {counts['error']} errors")
    if errors:
        print("  failed:", ", ".join(errors))
        sys.exit(1)

if __name__ == "__main__":
    main()
