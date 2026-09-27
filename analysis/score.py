#!/usr/bin/env python3
"""Score every solo against the human reference set, on several axes.

Each metric is placed against the human solos (a robust z-score from their median and interquartile
range, with the solo itself left out when it is human). Anywhere inside the human interquartile band
scores 100; outside it the score falls off like a Gaussian, in either direction: the human set defines
what good looks like. Only playability is one-sided (fewer impossible strokes is never worse). Two metrics
check the task instead, for generated solos only: playability, and the length the benchmark asks for.
An axis is the mean of its metrics, and the overall score is the mean of the axes.

usage: uv run python score.py
"""
import json

import mido
import numpy as np
import umap

import pipeline

Z0 = 0.6745  # robust z at the human quartiles
LENGTH_S = (110.0, 130.0)  # the grader's window for "a two minute drum solo", on the MIDI file's own length
LENGTH_FALLOFF_S = 10.0    # outside it: 61 points at 10 s out, 14 at 20 s
ZERO_IF_SHORT = {"rhythm_vocab_per_block"}  # too short to measure (under 64 beats) counts as no vocabulary

# key, description, direction (two / higher / lower, or task: set by the benchmark), transform, source for generated
# solos (native: the program's own MIDI; human solos get full marks on these)
AXES = {
    "Dynamics": [
        ("lra_lu", "loudness range (LU)", "two", "lin", "transcribed"),
        ("momentary_spread_lu", "loud-to-quiet spread (LU)", "two", "lin", "transcribed"),
        ("level_iqr_db_snare", "snare ghost-to-accent spread (dB)", "two", "lin", "transcribed"),
    ],
    "Rhythm": [
        ("ioi_entropy_bits", "variety of stroke spacings (bits)", "two", "lin", "transcribed"),
        ("rhythm_vocab_per_block", "distinct one-beat rhythms per 64 beats", "two", "lin", "transcribed"),
        ("npvi", "contrast between neighboring spacings (nPVI)", "two", "lin", "transcribed"),
        ("lz_relative", "pattern complexity vs shuffled", "two", "lin", "transcribed"),
    ],
    "Feel": [
        ("stroke_jitter_ms", "stroke timing jitter in steady runs (ms)", "two", "log", "transcribed"),
        ("grid_lock", "lock to a steady 16th/triplet grid (0-1)", "two", "lin", "transcribed"),
        ("local_ibi_cv_median", "beat-to-beat tempo wobble", "two", "log", "transcribed"),
    ],
    "Structure": [
        ("section_median_s", "typical section length (s)", "two", "log", "transcribed"),
        ("intensity_peak_pos", "where the climax falls (share of the solo)", "two", "lin", "transcribed"),
        ("density_contrast", "sparse-to-dense contrast", "two", "lin", "transcribed"),
        ("rest_time_frac", "share of time spent resting", "two", "lin", "transcribed"),
        ("length_s", "length against the two minutes asked for (s)", "task", "lin", "native"),
    ],
    "Orchestration": [
        ("distinct_notes", "distinct drums the transcriber hears", "two", "lin", "transcribed"),
        ("category_entropy_bits", "balance across drum families (bits)", "two", "lin", "transcribed"),
        ("orchestration_changes_per_min", "lead-drum changes per minute", "two", "log1p", "transcribed"),
    ],
    "Energy": [
        ("hits_per_s", "hits per second", "two", "log", "transcribed"),
        ("peak_hits_per_s", "most hits in one second", "two", "log", "transcribed"),
        ("steady_run_share", "share of strokes inside steady runs (fluency)", "two", "lin", "transcribed"),
    ],
    "Playability": [
        ("limb_violations_per_min", "stroke groups needing 3+ hands, per minute", "lower", "log1p", "native"),
    ],
}
METRICS = [m for ms in AXES.values() for m in ms]
TRANSFORM = {"lin": lambda x: x, "log": np.log, "log1p": np.log1p}


def band(values, transform):
    t = TRANSFORM[transform](np.asarray(values, dtype=float))
    med = float(np.median(t))
    sigma = float(np.subtract(*np.percentile(t, [75, 25]))) / 1.349
    if sigma <= 0:
        raise SystemExit(f"human values have no spread: {values}")
    return med, sigma


def metric_score(x, med, sigma, direction, transform):
    z = (TRANSFORM[transform](x) - med) / sigma
    excess = {"two": abs(z), "higher": -z, "lower": z}[direction] - Z0
    return float(100 * np.exp(-0.5 * max(0.0, excess) ** 2)), float(z)


def length_score(seconds):
    """Full points inside the grader's window, falling off like a Gaussian outside it."""
    lo, hi = LENGTH_S
    return float(100 * np.exp(-0.5 * (max(lo - seconds, 0.0, seconds - hi) / LENGTH_FALLOFF_S) ** 2))


def midi_length(path):
    """A MIDI file's length in seconds, as the grader measures it."""
    return float(mido.MidiFile(path).length)


def main():
    items = pipeline.snapshot()
    out = pipeline.OUT
    solos = []
    for it in items:
        tr = json.loads((out / it["id"] / "features.json").read_text())["scalars"]
        nat = json.loads((out / it["id"] / "features_native.json").read_text())["scalars"] if it["group"] != "human" else None
        if nat is not None:
            nat["length_s"] = midi_length(it["native"])
        vals, unmeasured = {}, []
        for key, _, direction, _, source in METRICS:
            if direction == "task" and nat is None:  # nobody asked a person for a length
                continue
            src = nat if (source == "native" and nat is not None) else tr
            if key not in src:
                raise SystemExit(f"{it['id']}: missing {key}")
            if src[key] is None:  # features.py could not measure it for this solo (e.g. no steady runs)
                unmeasured.append(key)
                continue
            vals[key] = float(src[key])
            if not np.isfinite(vals[key]):
                raise SystemExit(f"{it['id']}: {key} is {vals[key]}")
        solos.append({"id": it["id"], "group": it["group"], "label": it["label"], "short": it["short"],
                      "model": it.get("model"), "mode": it.get("mode"), "metrics": vals, "unmeasured": unmeasured,
                      "duration_s": tr["duration_s"]})

    humans = [s for s in solos if s["group"] == "human"]
    for s in solos:
        ref = [h for h in humans if h["id"] != s["id"]]
        s["metric_scores"], s["z"] = {}, {}
        for key, _, direction, transform, source in METRICS:
            if key in s["unmeasured"]:
                if key in ZERO_IF_SHORT:
                    s["metric_scores"][key] = 0.0
                continue
            if source == "native" and s["group"] == "human":
                # playability checks a generated solo's own MIDI; a person played this one, and anything flagged in its
                # transcription is the transcriber misreading flams, grace notes or chokes
                s["metric_scores"][key], s["z"][key] = 100.0, 0.0
                continue
            if direction == "task":
                s["metric_scores"][key] = length_score(s["metrics"][key])
                continue
            med, sigma = band([h["metrics"][key] for h in ref if key in h["metrics"]], transform)
            s["metric_scores"][key], s["z"][key] = metric_score(s["metrics"][key], med, sigma, direction, transform)
        s["axis_scores"] = {}
        for a, ms in AXES.items():
            got = [s["metric_scores"][k] for k, *_ in ms if k in s["metric_scores"]]
            if not got:
                raise SystemExit(f"{s['id']}: nothing measurable on the {a} axis")
            s["axis_scores"][a] = float(np.mean(got))
        s["overall"] = float(np.mean(list(s["axis_scores"].values())))

    human_overall = np.array([h["overall"] for h in humans])
    for s in solos:
        s["human_percentile"] = float(np.mean(human_overall <= s["overall"] + 1e-9))

    # A shared space: z against all humans, then nearest human and a 2-D projection
    bands = {}
    for key, _, direction, transform, _ in METRICS:
        if direction == "task":
            continue
        hv = [h["metrics"][key] for h in humans if key in h["metrics"]]
        med, sigma = band(hv, transform)
        bands[key] = {"median": float(np.median(hv)), "p25": float(np.percentile(hv, 25)),
                      "p75": float(np.percentile(hv, 75)), "min": float(min(hv)), "max": float(max(hv)),
                      "t_median": med, "t_sigma": sigma}
    # The shared space only uses metrics measured for every solo; the rest are named in the output.
    shared = [m for m in METRICS if m[2] != "task" and all(m[0] in s["metrics"] for s in solos)]
    Z = np.array([[(TRANSFORM[t](s["metrics"][k]) - bands[k]["t_median"]) / bands[k]["t_sigma"]
                   for k, _, _, t, _ in shared] for s in solos])
    Z = np.clip(Z, -6, 6)
    hi = np.array([s["group"] == "human" for s in solos])
    for i, s in enumerate(solos):
        d = np.linalg.norm(Z[hi] - Z[i], axis=1)
        order = [j for j in np.argsort(d) if humans[j]["id"] != s["id"]]
        s["nearest"] = {"id": humans[order[0]]["id"], "short": humans[order[0]]["short"],
                        "distance": float(d[order[0]])}
        s["human_distance"] = float(np.mean(np.sort(d[[j for j in range(len(humans)) if humans[j]["id"] != s["id"]]])[:3]))
    Zc = Z - Z[hi].mean(axis=0)
    _, sv, vt = np.linalg.svd(Zc[hi], full_matrices=False)
    xy = Zc @ vt[:2].T
    for s, p in zip(solos, xy):
        s["pca"] = [float(p[0]), float(p[1])]
    explained = (sv ** 2 / np.sum(sv ** 2))[:2]
    for s, p in zip(solos, umap.UMAP(n_neighbors=10, min_dist=0.35, random_state=0).fit_transform(Z)):
        s["umap"] = [float(p[0]), float(p[1])]
    D = np.linalg.norm(Z[:, None] - Z[None], axis=2)
    pairs = {tuple(sorted((i, int(j)))) for i in range(len(solos)) for j in np.argsort(D[i])[1:4]}  # 3 nearest each
    edges = [[solos[i]["id"], solos[j]["id"], float(D[i, j])] for i, j in sorted(pairs)]

    result = {
        "axes": {a: [{"key": k, "label": d, "direction": dr, "transform": t, "source": src}
                     for k, d, dr, t, src in ms] for a, ms in AXES.items()},
        "length": {"window_s": list(LENGTH_S), "falloff_s": LENGTH_FALLOFF_S},
        "bands": bands,
        "pca": {"explained": explained.tolist(),
                "loadings": {k: [float(vt[0, i]), float(vt[1, i])] for i, (k, *_) in enumerate(shared)},
                "left_out": [k for k, _, d, *_ in METRICS if d != "task" and k not in {m[0] for m in shared}]},
        "edges": edges,
        "solos": sorted(solos, key=lambda s: -s["overall"]),
    }
    (out / "scores.json").write_text(json.dumps(result, indent=1))
    print(f"{'solo':42s} {'overall':>7s} {'pct':>5s}  " + " ".join(f"{a[:6]:>6s}" for a in AXES))
    for s in result["solos"]:
        print(f"{s['label'][:42]:42s} {s['overall']:7.1f} {s['human_percentile']:5.0%}  "
              + " ".join(f"{s['axis_scores'][a]:6.0f}" for a in AXES))


if __name__ == "__main__":
    main()
