#!/usr/bin/env python3
"""Same-kit control: every human solo rebuilt as MIDI from its transcribed hits, played on the General MIDI kit the
generated solos use, then transcribed, measured and scored the way a generated solo is. If the rebuilt solos score
like the recordings, the score follows the playing more than the sound of the recording.

usage: uv run python samekit.py [prepare] [score]      work in work/samekit/<id>/, results in out/samekit.json
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import mido
import numpy as np

import pipeline
from hillclimb import score_one
from score import METRICS, band

WORK = pipeline.WORK / "samekit"
RESULTS = pipeline.OUT / "samekit.json"
TPB = 960  # ticks per beat at the default 120 BPM: about half a millisecond per tick
NOTE_S = 0.1  # note length, cut short where the same drum is hit again sooner


def velocities(h):
    """Hit levels as MIDI velocities: each drum family's loudest hits (95th percentile) at 127, and every dB quieter
    in the recording a dB quieter on the kit, inverting FluidSynth's default velocity curve (40 log10(127/velocity)
    dB), so the rebuilt solo keeps the recording's accents and ghost notes."""
    lvl, cat = np.array(h["level_db"], dtype=float), np.array(h["cat"])
    if not np.isfinite(lvl).all():
        raise SystemExit("a hit has no level")
    ref = {c: np.percentile(lvl[cat == c], 95) for c in set(cat)}
    return [int(np.clip(round(127 * 10 ** (min(l - ref[c], 0.0) / 40)), 1, 127)) for l, c in zip(lvl, cat)]


def rebuild(f, out):
    """A MIDI file with every transcribed hit of the scored part, on channel 10."""
    h = f["hits"]
    t, notes = np.array(h["t"], dtype=float), np.array(h["note"], dtype=int)
    vel = velocities(h)
    events = []
    for i, (ti, n) in enumerate(zip(t, notes)):
        later = t[i + 1:][notes[i + 1:] == n]
        off = min(ti + NOTE_S, later[0]) if len(later) else ti + NOTE_S
        on_tick, off_tick = round(ti * 2 * TPB), round(off * 2 * TPB)
        events.append((on_tick, 1, mido.Message("note_on", channel=9, note=int(n), velocity=vel[i])))
        events.append((max(off_tick, on_tick + 1), 0, mido.Message("note_off", channel=9, note=int(n), velocity=0)))
    events.sort(key=lambda e: (e[0], e[1]))  # a note ends before the same tick starts another
    mf = mido.MidiFile(ticks_per_beat=TPB)
    track = mido.MidiTrack()
    mf.tracks.append(track)
    now = 0
    for tick, _, msg in events:
        track.append(msg.copy(time=tick - now))
        now = tick
    mf.save(out)


def render(d):
    """render.py in the sandbox image, exactly as bench.py renders a generated solo."""
    p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-e", "HOME=/tmp", "--user",
                        f"{os.getuid()}:{os.getgid()}", "-v", f"{d.resolve()}:/in:ro", "-v", f"{d.resolve()}:/out",
                        "-v", f"{pipeline.ROOT / 'render.py'}:/render.py:ro", pipeline.IMAGE, "python", "/render.py",
                        "/in/solo.mid", "/out/solo.mp3"], capture_output=True, text=True)
    if p.returncode:
        raise SystemExit(f"{d.name}: render failed: {p.stderr.strip()[-2000:]}")
    (d / "render.json").write_text(p.stdout)


def transcribe(d):
    with open(d / "transcribe.log", "w") as log:
        subprocess.run(["uvx", "muscriptor", "transcribe", d / "solo.mp3", "--instruments", "drums", "-o",
                        d / "transcribed.mid"], check=True, stdout=log, stderr=subprocess.STDOUT)


def measure(d):
    with open(d / "features.log", "w") as log:
        subprocess.run([sys.executable, pipeline.HERE / "features.py", d / "solo.mp3", d / "transcribed.mid",
                        d / "features.json"], check=True, stdout=log, stderr=subprocess.STDOUT)


def humans():
    hum = [it for it in pipeline.snapshot() if it["group"] == "human"]
    orig = {it["id"]: json.loads((pipeline.OUT / it["id"] / "features.json").read_text()) for it in hum}
    return orig, {it["id"]: WORK / it["id"] for it in hum}


def prepare():
    orig, dirs = humans()
    for i, d in dirs.items():
        d.mkdir(parents=True, exist_ok=True)
        if pipeline.stale(d / "solo.mid", pipeline.OUT / i / "features.json"):
            rebuild(orig[i], d / "solo.mid")
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(render, [d for d in dirs.values() if pipeline.stale(d / "solo.mp3", d / "solo.mid")]))
    for d in dirs.values():  # one at a time on the GPU
        if pipeline.stale(d / "transcribed.mid", d / "solo.mp3"):
            transcribe(d)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(measure, [d for d in dirs.values()
                              if pipeline.stale(d / "features.json", d / "transcribed.mid", pipeline.HERE / "features.py")]))


def score():
    orig, dirs = humans()
    scores = {s["id"]: s for s in json.loads((pipeline.OUT / "scores.json").read_text())["solos"]}
    results = {}
    for i, d in dirs.items():
        others = [orig[j]["scalars"] for j in orig if j != i]  # the recording's own original is left out, as in score.py
        bands = {k: band([f[k] for f in others if f[k] is not None], t) for k, _, dr, t, _ in METRICS if dr != "task"}
        sc = json.loads((d / "features.json").read_text())["scalars"]
        ms, axes, overall, unmeasured = score_one(sc, sc, bands, human=True)
        results[i] = {"original": scores[i]["overall"], "original_axes": scores[i]["axis_scores"], "samekit": overall,
                      "samekit_axes": axes, "metric_scores": ms, "unmeasured": unmeasured,
                      "hits": len(orig[i]["hits"]["t"]), "duration_s": sc["duration_s"]}
        print(f"{i:40s} {scores[i]['overall']:5.1f} -> {overall:5.1f}", flush=True)
    RESULTS.write_text(json.dumps(results, indent=1))
    o, s = np.array([r["original"] for r in results.values()]), np.array([r["samekit"] for r in results.values()])
    print(f"median {np.median(o):.1f} -> {np.median(s):.1f}; middle half {np.percentile(o, 25):.1f}-{np.percentile(o, 75):.1f}"
          f" -> {np.percentile(s, 25):.1f}-{np.percentile(s, 75):.1f}")


if __name__ == "__main__":
    for stage in sys.argv[1:] or ["prepare", "score"]:
        {"prepare": prepare, "score": score}[stage]()
