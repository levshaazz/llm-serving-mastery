#!/usr/bin/env python3
"""
snapshot.py — freeze every student's round at the deadline (Thursday 23:59; run it from cron at 00:00).

    python judge/snapshot.py --round 1 --roster judge/roster.csv --dir judge/rounds/round-01

For every student it makes a bare MIRROR of the repository (all objects, as they are right now) and
records the commit the round-NN tag points to. The judge then measures that commit from the mirror, so
deleting, moving or force-pushing the tag after the deadline changes nothing — and commit dates, which
can be forged, are never consulted. One unreachable repository never stops the others.

roster.csv (private, not in git): github,repo   — header line, one student per line
"""
import argparse, csv, datetime as dt, json, os, pathlib, shutil, subprocess, sys

ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")


def git(*args, timeout=600):
    return subprocess.run(["git", *args], text=True, capture_output=True, stdin=subprocess.DEVNULL,
                          env=ENV, timeout=timeout)


def snapshot_one(repo, tag, mirror):
    if mirror.exists():
        shutil.rmtree(mirror)
    try:
        r = git("clone", "--quiet", "--mirror", repo, str(mirror))
        if r.returncode:
            return None, f"clone failed: {r.stderr.strip()[-300:]}"
        r = git("-C", str(mirror), "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}", timeout=60)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    if r.returncode or not r.stdout.strip():
        return None, f"no tag {tag}"
    return r.stdout.strip(), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--roster", required=True)
    ap.add_argument("--dir", required=True, help="judge/rounds/round-NN (private, not in git)")
    a = ap.parse_args()
    tag, base = f"round-{a.round:02d}", pathlib.Path(a.dir)
    (base / "mirrors").mkdir(parents=True, exist_ok=True)
    snap = {"round": a.round, "tag": tag,
            "taken_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "students": {}}
    for row in csv.DictReader(open(a.roster)):
        who = row["github"].strip()
        mirror = (base / "mirrors" / f"{who}.git").resolve()
        sha, err = snapshot_one(row["repo"].strip(), tag, mirror)
        snap["students"][who] = {"repo": row["repo"].strip(), "mirror": str(mirror) if sha else None,
                                 "commit": sha, "error": err}
        print(f"{who:<24} {sha or '—':<42} {err or ''}", flush=True)
    json.dump(snap, open(base / "snapshot.json", "w"), indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
