#!/usr/bin/env python3
"""Analyse every human and generated solo.

usage: uv run python pipeline.py [stage ...]
stages, in order: render transcribe bracket features validate score pages (default: all)
Each stage skips outputs that already exist and are newer than their inputs.
"""
import csv
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HUMAN = ROOT / "human_solos"
RUNS = ROOT / "runs"
TRANS = ROOT / "transcriptions"
WORK = HERE / "work"
OUT = HERE / "out"
SITE = Path(os.environ.get("DRUMTHRONE_SITE", OUT)).resolve()  # where pages are written; data stays in OUT
PUBLIC = os.environ.get("DRUMTHRONE_PUBLIC") == "1"  # public build: human recordings are linked on YouTube, not hosted
SF2 = ROOT / "assets" / "FluidR3_GM.sf2"
OVERRIDES = HUMAN / "bracket_overrides.json"  # written by the bracket review page
PROMPT = ROOT / "prompt.md"
IMAGE = "drumbench"
PY = [sys.executable]

LABELS = {  # file stem -> (display name, short name: player and performance, for dense charts)
    "max_roach-the_drum_also_waltzes": ("Max Roach: The Drum Also Waltzes", "M. Roach, Drum Also Waltzes"),
    "buddy_rich-impossible_drum_solo": ("Buddy Rich: \"Impossible\" Drum Solo", "B. Rich, Impossible Solo"),
    "daniel_glass-century_project": ("Daniel Glass: The Century Project", "D. Glass, Century Project"),
    "antonio_sanchez-drumeo": ("Antonio Sanchez (Drumeo)", "A. Sanchez, Drumeo"),
    "mark_guiliana-drumeo": ("Mark Guiliana (Drumeo)", "M. Guiliana, Drumeo"),
    "john_bonham-moby_dick_msg_1973": ("John Bonham: Moby Dick (MSG 1973)", "J. Bonham, Moby Dick '73"),
    "joey_jordison-disasterpieces": ("Joey Jordison: Disasterpieces", "J. Jordison, Disasterpieces"),
    "mario_duplantier-refuge": ("Mario Duplantier: Refuge", "M. Duplantier, Refuge"),
    "thomas_lang-meinl_2015": ("Thomas Lang (Meinl 2015)", "T. Lang, Meinl '15"),
    "senri_kawaguchi-drumeo": ("Senri Kawaguchi (Drumeo)", "S. Kawaguchi, Drumeo"),
    "tony_royster_jr-drumeo": ("Tony Royster Jr. (Drumeo)", "T. Royster Jr., Drumeo"),
    "benny_greb-drumeo": ("Benny Greb (Drumeo)", "B. Greb, Drumeo"),
    "steve_gadd-yamaha": ("Steve Gadd (Yamaha)", "S. Gadd, Yamaha"),
    "steve_smith-khanda_west": ("Steve Smith: Khanda West", "S. Smith, Khanda West"),
    "horacio_hernandez-the_octopus": ("Horacio Hernandez: The Octopus", "H. Hernandez, The Octopus"),
    "dafnis_prieto-drumeo": ("Dafnis Prieto (Drumeo)", "D. Prieto, Drumeo"),
    "terry_bozzio-pats_changes": ("Terry Bozzio: Pat's Changes", "T. Bozzio, Pat's Changes"),
    "jojo_mayer-hudson": ("Jojo Mayer (Hudson)", "J. Mayer, Hudson Music"),
    "todd_sucherman-drumeo": ("Todd Sucherman (Drumeo)", "T. Sucherman, Drumeo"),
    "chris_coleman-drumsolo_1": ("Chris Coleman: Drumsolo #1 (Meinl)", "C. Coleman, Drumsolo #1"),
}


def experiment_batch(batch):
    """A batch belongs to the experiment when it answered the benchmark's prompt (prompt.md)."""
    cfg = batch / "config.json"
    return cfg.exists() and json.loads(cfg.read_text())["prompt"].strip() == PROMPT.read_text().strip()


ELIGIBLE = ("midi_parses",)  # every run that wrote a MIDI file is analysed, whatever its length or kit
LEFT_OUT = {"openai_gpt-chat-latest"}  # an alias that records no model version, so its solo can't be attributed


def model_runs():
    """Every fully graded run in the experiment: (run dir, batch, eligible, reason it is not)."""
    for mid in sorted(RUNS.glob("2*/*/*-*/repro/solo.mid")):
        run = mid.parent.parent
        if not experiment_batch(run.parent.parent) or not (run / "grade.json").exists():  # other prompt, or still grading
            continue
        checks = json.loads((run / "grade.json").read_text()).get("checks", {})
        failed = [f"{c}: {checks.get(c, {}).get('detail') or 'not reached'}" for c in ELIGIBLE
                  if checks.get(c, {}).get("value") != 1]
        yield run, run.parent.parent.name, not failed, "; ".join(failed)


def excluded():
    """Graded runs that fail the basic checks, with the grader's reason."""
    return [{"run": run.parent.name.split("_", 1)[1], "reason": reason}
            for run, ts, ok, reason in model_runs() if not ok]


def corpus():
    """Every solo: the human recordings and each experiment run's reproduced MIDI."""
    manifest = {r["file"]: r for r in csv.DictReader((HUMAN / "manifest.tsv").open(), delimiter="\t")}
    items = []
    for mp3 in sorted(HUMAN.glob("*.mp3")):
        m = manifest[mp3.name]
        label, short = LABELS[mp3.stem]
        items.append({"id": mp3.stem, "group": "human", "label": label, "short": short, "audio": mp3,
                      "url": m["url"], "channel": m["channel"]})
    runs = [(run, ts) for run, ts, ok, _ in model_runs() if ok and run.parent.name not in LEFT_OUT]
    per_model = Counter(run.parent.name for run, _ in runs)
    seen = Counter()
    for run, ts in runs:
        model = run.parent.name
        seen[model] += 1
        name = model.split("_", 1)[1]
        label = name if per_model[model] == 1 else f"{name} (run {seen[model]})"
        rid = f"{model}__{run.name}__{ts}"
        items.append({"id": rid, "group": "model", "model": model.replace("_", "/", 1), "mode": run.name.split("-")[0],
                      "label": label, "short": label, "native": run / "repro" / "solo.mid",
                      "audio": WORK / "render" / rid / "solo.mp3", "run_dir": run})
    return items


def overrides():
    return json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}


def bounds(it):
    """The detector's solo bracket inside a human recording."""
    b = json.loads((OUT / "brackets" / f"{it['id']}.json").read_text())
    if b["start"] is None:
        raise SystemExit(f"{it['id']}: the detection found no solo in this recording")
    return b["start"], b["end"]


def snapshot():
    """The corpus as fixed at the start of the last pipeline run, so later stages see the same solos."""
    ids = json.loads((OUT / "corpus.json").read_text())
    items = {it["id"]: it for it in corpus()}
    missing = [i for i in ids if i not in items]
    if missing:
        raise SystemExit(f"solos in the snapshot are gone: {missing}")
    return [items[i] for i in ids]


def spans_for(it):
    """Solo stretches the detector heard: its bracket minus every second that sounds like a band (none if no solo)."""
    b = json.loads((OUT / "brackets" / f"{it['id']}.json").read_text())
    if b["start"] is None:
        return []
    start, end = b["start"], b["end"]
    band = b["series"]["band"]
    spans = []
    for w in range(int(start), math.ceil(end)):
        if band[w]:
            continue
        a, z = max(start, float(w)), min(end, float(w + 1))
        if spans and abs(spans[-1][1] - a) < 1e-9:
            spans[-1][1] = z
        else:
            spans.append([a, z])
    return [[round(a, 2), round(z, 2)] for a, z in spans if z > a]


def auto_chunk(it):
    """The detector's pick: its longest uninterrupted solo stretch, so tempo and timing see continuous playing."""
    spans = spans_for(it)
    if not spans:
        raise SystemExit(f"{it['id']}: no solo stretch to score")
    return max(spans, key=lambda s: s[1] - s[0])


def best_chunk(it):
    """What gets scored: the part set by listening (human_solos/bracket_overrides.json), exactly as set, else the
    detector's pick."""
    ov = overrides().get(it["id"])
    return [float(ov["start"]), float(ov["end"])] if ov else auto_chunk(it)


def stale(out, *inputs):
    out = Path(out)
    return not out.exists() or any(Path(i).stat().st_mtime > out.stat().st_mtime for i in inputs)


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


# ---------------------------------------------------------------- stages

def render(items):
    """Render generated MIDI exactly as bench.py does (render.py in the sandbox image)."""
    for it in items:
        if it["group"] == "human" or not stale(it["audio"], it["native"], ROOT / "render.py"):
            continue
        out = Path(it["audio"]).parent
        out.mkdir(parents=True, exist_ok=True)
        p = run(["docker", "run", "--rm", "--network", "none", "-e", "HOME=/tmp", "--user", f"{os.getuid()}:{os.getgid()}",
                 "-v", f"{Path(it['native']).parent.resolve()}:/in:ro", "-v", f"{out.resolve()}:/out",
                 "-v", f"{ROOT / 'render.py'}:/render.py:ro", IMAGE, "python", "/render.py", "/in/solo.mid",
                 "/out/solo.mp3"], capture_output=True, text=True)
        (out / "render.json").write_text(p.stdout)


def transcribe(items):
    """MuScriptor: drums only for analysis, and with every instrument allowed for the solo detection."""
    (TRANS / "full").mkdir(parents=True, exist_ok=True)
    for it in sorted(items, key=lambda i: i["group"] == "human"):
        mid = TRANS / f"{it['id']}.mid"
        if stale(mid, it["audio"]):
            cmd = ["uvx", "muscriptor", "transcribe", it["audio"], "--instruments", "drums", "-o", mid]
            if it["group"] == "human":
                cmd += ["--auralize", TRANS / f"{it['id']}.auralize.mp3", "--soundfont", SF2]
            with (TRANS / f"{it['id']}.log").open("w") as log:
                run(cmd, stdout=log, stderr=subprocess.STDOUT)
        full = TRANS / "full" / f"{it['id']}.json"
        if stale(full, it["audio"]):
            with (TRANS / "full" / f"{it['id']}.log").open("w") as log:
                run(["uvx", "muscriptor", "transcribe", it["audio"], "--format", "json", "-o", full],
                    stdout=log, stderr=subprocess.STDOUT)


def bracket(items):
    """Run the solo detection on every recording; only the human brackets decide what is scored."""
    for it in items:
        out = OUT / "brackets" / f"{it['id']}.json"
        mid, full = TRANS / f"{it['id']}.mid", TRANS / "full" / f"{it['id']}.json"
        if stale(out, it["audio"], mid, full, HERE / "bracket.py"):
            run(PY + [HERE / "bracket.py", it["audio"], mid, full, out])


def feature_jobs(items):
    jobs = []
    for it in items:
        d = OUT / it["id"]
        mid = TRANS / f"{it['id']}.mid"
        if it["group"] == "human":
            a, b = best_chunk(it)
            jobs.append((d / "features.json", [it["audio"], mid], ["--start", f"{a:.2f}", "--end", f"{b:.2f}"], [a, b]))
        else:
            jobs.append((d / "features.json", [it["audio"], mid], [], None))
            jobs.append((d / "features_native.json", [it["audio"], it["native"]], ["--native"], None))
    return jobs


def features(items):
    """Audio + MIDI features: bracketed humans, generated solos from their transcription and their own MIDI."""
    from concurrent.futures import ThreadPoolExecutor
    def needs(job):
        out, inputs, extra, chunk = job
        if stale(out, *inputs, HERE / "features.py"):
            return True
        if chunk is None:
            return False
        seg = json.loads(out.read_text())["clip"]["segment"]  # redo only if this track's scored chunk moved
        return abs(seg[0] - chunk[0]) > 0.01 or abs(seg[1] - chunk[1]) > 0.01

    todo = [j for j in feature_jobs(items) if needs(j)]

    def one(job):
        out, (audio, mid), extra, _ = job
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out.with_suffix(".log"), "w") as log:
            run(PY + [HERE / "features.py", audio, mid, out, *extra], stdout=log, stderr=subprocess.STDOUT)

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, todo))


def validate(items):
    """Score the transcriber on every solo whose true MIDI is known."""
    for it in items:
        if it["group"] == "human":
            continue
        out = OUT / "validation" / f"{it['id']}.json"
        mid = TRANS / f"{it['id']}.mid"
        if stale(out, it["audio"], it["native"], mid, HERE / "validate.py", HERE / "features.py"):
            run(PY + [HERE / "validate.py", it["audio"], it["native"], mid, out])
    import validate as V
    V.pool([OUT / "validation" / f"{it['id']}.json" for it in items if it["group"] != "human"],
           OUT / "validation" / "pooled.json")


def score(items):
    run(PY + [HERE / "score.py"])


def page_audio(it):
    """Audio the pages play: generated renders are copied into the site; human recordings stay in human_solos
    locally and are not part of a public build (None)."""
    if it["group"] == "human":
        return None if PUBLIC else Path(it["audio"])
    dst = SITE / "audio" / f"{it['id']}.mp3"
    if stale(dst, it["audio"]):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(it["audio"], dst)
    return dst


def pages(items):
    """One page per solo, the measurements, detection and graph pages, the bracket review, the thinking runs, and the
    main page."""
    pooled = OUT / "validation" / "pooled.json"
    run(PY + [HERE / "sound.py"])
    for it in items:
        d = OUT / it["id"]
        val = pooled if it["group"] == "human" else OUT / "validation" / f"{it['id']}.json"
        audio = page_audio(it)
        cmd = PY + [HERE / "report_solo.py", d / "features.json", val, SITE / it["id"] / "index.html",
                    "--title", it["label"], *(["--audio", audio] if audio else ["--youtube", it["url"]])]
        if it["group"] == "human":
            cmd += ["--validation-label", "generated solos"]
        else:
            cmd += ["--validation-label", "this solo", "--native", d / "features_native.json"]
        run(cmd)
    run(PY + [HERE / "report_corpus.py"])
    run(PY + [HERE / "report_thinking.py"])
    run(PY + [HERE / "report_story.py"])
    run(PY + [HERE / "report_how.py"])


STAGES = {"render": render, "transcribe": transcribe, "bracket": bracket, "features": features,
          "validate": validate, "score": score, "pages": pages}


def main(stages):
    items = corpus()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "corpus.json").write_text(json.dumps([it["id"] for it in items]))
    for s in stages or list(STAGES):
        print(f"== {s}", flush=True)
        STAGES[s](items)


if __name__ == "__main__":
    main(sys.argv[1:])
