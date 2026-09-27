#!/usr/bin/env python3
"""Hill-climb the benchmark prompt and sweep thinking effort, scoring every solo against the human set.

usage:
  uv run python hillclimb.py gen <prompt.md> <tag> <runs> <model[@effort]> ... [-- bench args]
                                                                               generate solos with bench.py (chat)
  uv run python hillclimb.py rescue                                            finish runs that wrote no MIDI (rescue.py)
  uv run python hillclimb.py render                                            render runs whose solo.mp3 is missing
  uv run python hillclimb.py score                                             analyse and score every finished run
  uv run python hillclimb.py table [tag ...]                                   compare prompts and thinking settings

Everything lives in hillclimb/ at the project root: prompts/<tag>.md, runs/<tag>/ (bench.py output), work/ and
results.json. prompt.md, runs/ and the published site are never touched.
"""
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import pipeline
from score import AXES, METRICS, ZERO_IF_SHORT, band, length_score, metric_score, midi_length

HERE = pipeline.HERE
ROOT = pipeline.ROOT
HC = ROOT / "hillclimb"
RUNS = HC / "runs"
WORK = HC / "work"
RESULTS = HC / "results.json"
PLANNING = ["n_sections", "section_median_s", "intensity_peak_pos", "density_contrast", "rhythm_vocab_per_block",
            "rhythm_cell_repeat_rate", "lz_relative", "orch_vocab_per_block", "rest_time_frac", "hits_per_s",
            "grid_lock", "steady_run_share"]


def read_env(path):
    """KEY=VALUE lines, so bench.py gets the API key without it ever being printed."""
    out = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


BENCH = ["--chat-repairs", "2", "--max-cost", "50"]  # as the main experiment's batches


def gen(prompt, tag, runs, models, extra=()):
    (HC / "prompts").mkdir(parents=True, exist_ok=True)
    kept = HC / "prompts" / f"{tag}.md"
    if Path(prompt).resolve() != kept.resolve():
        shutil.copyfile(prompt, kept)
    env = {**os.environ, **read_env(ROOT / ".env")}
    cmd = [ROOT / ".venv" / "bin" / "python", ROOT / "bench.py", *models, "--mode", "chat", "--runs", str(runs),
           "--prompt", kept, "--out", RUNS / tag, "--jobs", "5", *BENCH, *extra]
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=ROOT, env=env, check=True)


def rescue():
    env = {**os.environ, **read_env(ROOT / ".env")}
    subprocess.run([str(ROOT / ".venv" / "bin" / "python"), str(HERE / "rescue.py")], cwd=ROOT, env=env, check=True)


def render():
    """Render every run's MIDI that has no solo.mp3 (a fresh clone of the repository), exactly as bench.py does."""
    todo = [r.parent.parent for r in sorted(RUNS.glob("*/*/*/chat-*/repro/solo.mid")) if not (r.parent.parent / "solo.mp3").exists()]
    for run_dir in todo:
        p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-e", "HOME=/tmp",
                            "--user", f"{os.getuid()}:{os.getgid()}", "-v", f"{(run_dir / 'repro').resolve()}:/in:ro",
                            "-v", f"{run_dir.resolve()}:/out", "-v", f"{ROOT / 'render.py'}:/render.py:ro", pipeline.IMAGE,
                            "python", "/render.py", "/in/solo.mid", "/out/solo.mp3"], capture_output=True, text=True)
        if p.returncode:
            raise SystemExit(f"{run_dir}: render failed: {p.stderr.strip()[-2000:]}")
        (run_dir / "render.json").write_text(p.stdout)
    print(f"rendered {len(todo)} runs")


def human_bands():
    hum = [it for it in pipeline.corpus() if it["group"] == "human"]
    feats = [json.loads((pipeline.OUT / it["id"] / "features.json").read_text())["scalars"] for it in hum]
    return {k: band([f[k] for f in feats if f[k] is not None], t) for k, _, d, t, _ in METRICS if d != "task"}


def score_one(tr, nat, bands, human=False):
    """Score one solo against the human bands, as score.py does; a human performance gets full marks on the metrics
    read from a program's own MIDI."""
    ms, unmeasured = {}, []
    for key, _, direction, transform, source in METRICS:
        if source == "native" and human:
            ms[key] = 100.0
            continue
        v = (nat if source == "native" else tr)[key]
        if v is None:
            unmeasured.append(key)
            if key in ZERO_IF_SHORT:
                ms[key] = 0.0
            continue
        if direction == "task":
            ms[key] = length_score(float(v))
            continue
        ms[key] = metric_score(float(v), *bands[key], direction, transform)[0]
    axes = {}
    for a, specs in AXES.items():
        got = [ms[k] for k, *_ in specs if k in ms]
        if not got:
            raise SystemExit(f"nothing measurable on the {a} axis")
        axes[a] = float(np.mean(got))
    return ms, axes, float(np.mean(list(axes.values()))), unmeasured


def runs_meta():
    """bench.py's per-run records (model, thinking, cost, tokens), keyed by run directory."""
    meta = {}
    for res in RUNS.glob("*/*/results.jsonl"):
        for line in res.read_text().splitlines():
            r = json.loads(line)
            meta[(ROOT / r["dir"]).resolve() if not Path(r["dir"]).is_absolute() else Path(r["dir"]).resolve()] = r
    return meta


def analyse(run_dir):
    """Transcribe (GPU, one at a time) happens before this; features for one run."""
    w = WORK / "__".join(run_dir.relative_to(RUNS).parts)
    audio, native, trans = run_dir / "solo.mp3", run_dir / "repro" / "solo.mid", w / "transcribed.mid"
    for out, mid, extra in ((w / "features.json", trans, []), (w / "features_native.json", native, ["--native"])):
        if not out.exists():
            with open(out.with_suffix(".log"), "w") as log:
                subprocess.run([sys.executable, HERE / "features.py", audio, mid, out, *extra], check=True,
                               stdout=log, stderr=subprocess.STDOUT)
    return w


def score():
    bands, meta = human_bands(), runs_meta()
    records, todo = [], []
    for grade in sorted(RUNS.glob("*/*/*/chat-*/grade.json")):
        run_dir = grade.parent
        tag = run_dir.relative_to(RUNS).parts[0]
        m = meta[run_dir.resolve()]
        rec = {"dir": str(run_dir.relative_to(ROOT)), "tag": tag, "model": m["model"].split("@")[0],
               "thinking": m["thinking"], "cost": m["cost"], "reasoning_tokens": m["reasoning_tokens"],
               "completion_tokens": m["completion_tokens"], "seconds": m["seconds"], "turns": m["turns"],
               "providers": m["providers"],
               "rescued": "rescued" in m, "error": None, "failed": []}
        records.append(rec)
        if m["stop"] == "error":  # the request itself broke (API or sandbox): no verdict on the model
            rec["error"] = m["error"]
            continue
        checks = json.loads(grade.read_text()).get("checks", {})
        rec["failed"] = [c for c in pipeline.ELIGIBLE if checks.get(c, {}).get("value") != 1]
        if not (run_dir / "solo.mp3").exists():
            rec["failed"].append("render")
        if not rec["failed"]:
            w = WORK / "__".join(run_dir.relative_to(RUNS).parts)
            w.mkdir(parents=True, exist_ok=True)
            if not (w / "transcribed.mid").exists():
                subprocess.run(["uvx", "muscriptor", "transcribe", run_dir / "solo.mp3", "--instruments", "drums",
                                "-o", w / "transcribed.mid"], check=True, capture_output=True)
            todo.append((rec, run_dir))
    with ThreadPoolExecutor(3) as ex:
        dirs = list(ex.map(lambda job: analyse(job[1]), todo))
    for (rec, run_dir), w in zip(todo, dirs):
        tr = json.loads((w / "features.json").read_text())["scalars"]
        nat = json.loads((w / "features_native.json").read_text())["scalars"]
        nat["length_s"] = midi_length(run_dir / "repro" / "solo.mid")
        ms, axes, overall, unmeasured = score_one(tr, nat, bands)
        rec.update(overall=overall, axes=axes, metric_scores=ms, unmeasured=unmeasured,
                   planning={k: tr[k] for k in PLANNING},
                   script_lines=len((run_dir / "repro" / "drum_solo.py").read_text().splitlines()))
    RESULTS.write_text(json.dumps(records, indent=1))
    errs = [r for r in records if r["error"]]
    print(f"{len(records)} runs: {len(todo)} scored, {len(records) - len(todo) - len(errs)} wrote no MIDI file (or it "
          f"would not render), {len(errs)} never produced a result")
    for (tag, model, thinking), rs in sorted(group(errs).items()):
        print(f"  no result: {tag} {model}@{thinking} x{len(rs)}: {rs[0]['error'][:140]}")


def group(recs):
    out = defaultdict(list)
    for r in recs:
        out[(r["tag"], r["model"].split("/")[1], r["thinking"])].append(r)
    return out


def table(tags):
    recs = json.loads(RESULTS.read_text())
    groups = group(r for r in recs if not r["error"] and (not tags or r["tag"] in tags))
    axes = list(AXES)
    print(f"{'tag':10s} {'model':24s} {'thinking':16s} {'n':>2s} {'ok':>2s} {'overall':>12s}  "
          + " ".join(f"{a[:5]:>5s}" for a in axes) + f" {'$/run':>6s} {'think tok':>9s}")
    for (tag, model, thinking), rs in sorted(groups.items()):
        ok = [r for r in rs if not r["failed"]]
        if ok:
            o = np.array([r["overall"] for r in ok])
            ax = " ".join(f"{np.mean([r['axes'][a] for r in ok]):5.0f}" for a in axes)
            overall = f"{o.mean():5.1f} +/-{o.std(ddof=1) if len(o) > 1 else 0:4.1f}"
        else:
            ax, overall = " ".join(f"{'-':>5s}" for _ in axes), f"{'-':>12s}"
        print(f"{tag:10s} {model[:24]:24s} {thinking[:16]:16s} {len(rs):2d} {len(ok):2d} {overall:>12s}  {ax} "
              f"{np.mean([r['cost'] for r in rs]):6.2f} {np.mean([r['reasoning_tokens'] for r in rs]):9.0f}")
    errs = [r for r in recs if r["error"] and (not tags or r["tag"] in tags)]
    if errs:
        print(f"{len(errs)} runs never produced a result (API or sandbox errors) and are left out above")
    print(f"total cost: ${sum(r['cost'] for r in recs):.2f}")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "gen":
        extra = args[args.index("--") + 1:] if "--" in args else []
        args = args[:args.index("--")] if "--" in args else args
        gen(args[0], args[1], int(args[2]), args[3:], extra)
    elif cmd == "rescue":
        rescue()
    elif cmd == "render":
        render()
    elif cmd == "score":
        score()
    elif cmd == "table":
        table(args)
    else:
        raise SystemExit(__doc__)
