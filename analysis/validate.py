#!/usr/bin/env python3
"""Score the transcription of a solo whose true MIDI is known (a generated solo).

usage: uv run python validate.py <audio> <true.mid> <transcribed.mid> <out.json>
"""
import json
import sys
from collections import Counter
from pathlib import Path

import librosa
import mido
import numpy as np
from scipy import stats

import drums
from features import SR, align_and_refine, group_hits, hit_levels, rnd, sharp_flux

TOL = 0.050  # onset tolerance, as in mir_eval


def load(path):
    t, out = 0.0, []
    for m in mido.MidiFile(path):
        t += m.time
        if m.type == "note_on" and m.velocity > 0:
            out.append((t, m.note, m.velocity))
    out.sort()
    return (np.array([h[i] for h in out]) for i in range(3))


def match(a_t, a_c, b_t, b_c, same_cat):
    """Greedy one-to-one matching within TOL, optionally requiring the same category."""
    used, pairs = np.zeros(len(b_t), bool), []
    for i in np.argsort(a_t):
        ok = (np.abs(b_t - a_t[i]) <= TOL) & ~used
        if same_cat:
            ok &= b_c == a_c[i]
        cand = np.flatnonzero(ok)
        if len(cand):
            j = cand[np.argmin(np.abs(b_t[cand] - a_t[i]))]
            used[j] = True
            pairs.append((i, j))
    return pairs


def main(audio, true_mid, trans_mid, out_path):
    tt, tn, tv = load(true_mid)
    et, en, _ = load(trans_mid)
    tc = np.array([drums.category(n) for n in tn])
    ec = np.array([drums.category(n) for n in en])

    near = np.array([et[np.argmin(np.abs(et - t))] - t for t in tt])
    offset = float(np.median(near[np.abs(near) <= 0.060]))
    pairs = match(tt + offset, tc, et, ec, same_cat=True)
    per_cat = {}
    for c in drums.CATEGORIES:
        n_true, n_trans = int((tc == c).sum()), int((ec == c).sum())
        hit = sum(1 for i, _ in pairs if tc[i] == c)
        if n_true or n_trans:
            per_cat[c] = {"true": n_true, "transcribed": n_trans,
                          "recall": hit / n_true if n_true else None,
                          "precision": hit / n_trans if n_trans else None}
    rec, prec = len(pairs) / len(tt), len(pairs) / len(et)

    confusion = Counter((tc[i], ec[j]) for i, j in match(tt + offset, tc, et, ec, same_cat=False))

    # Timing: transcription alone, then refined against the audio
    y, _ = librosa.load(audio, sr=SR, mono=True)
    flux = sharp_flux(y)
    groups = group_hits(et)
    gt = np.array([et[g[0]] for g in groups])
    _, g_ref = align_and_refine(gt, flux)
    e_ref = np.empty(len(et))
    for g, r in zip(groups, g_ref):
        e_ref[g] = r
    raw = np.array([et[j] - tt[i] for i, j in pairs])
    ref = np.array([e_ref[j] - tt[i] for i, j in pairs])
    raw, ref = (x - np.median(x) for x in (raw, ref))  # a constant clock offset is not timing error

    # Per-hit audio level against true velocity, at the true hit times
    audio_off, t_audio = align_and_refine(tt, flux)
    level = hit_levels(y, t_audio, tc)
    rho = {c: float(stats.spearmanr(tv[tc == c], level[tc == c])[0])
           for c in drums.CATEGORIES if (tc == c).sum() >= 30 and len(set(tv[tc == c])) > 1}

    out = {
        "audio": str(audio), "true_midi": str(true_mid), "transcribed_midi": str(trans_mid),
        "tolerance_ms": TOL * 1000, "clock_offset_ms": offset * 1000,
        "recall": rec, "precision": prec, "f1": 2 * rec * prec / (rec + prec),
        "per_category": per_cat,
        "confusion": [[a, b, n] for (a, b), n in sorted(confusion.items())],
        "true_notes": sorted(Counter(int(n) for n in tn).items()),
        "transcribed_notes": sorted(Counter(int(n) for n in en).items()),
        "timing_error_ms": {"raw": rnd(raw * 1000, 2), "refined": rnd(ref * 1000, 2)},
        "timing_summary": {k: {"median_abs_ms": float(np.median(np.abs(v)) * 1000),
                               "within_5ms": float(np.mean(np.abs(v) <= 0.005))}
                           for k, v in (("raw", raw), ("refined", ref))},
        "level_vs_velocity": {"cat": tc.tolist(), "velocity": tv.tolist(), "level_db": rnd(level, 1),
                              "spearman": rho},
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out))
    print(f"F1 {out['f1']:.3f} (recall {rec:.3f}, precision {prec:.3f}), clock offset {offset * 1000:+.1f} ms")
    for k, v in out["timing_summary"].items():
        print(f"timing {k:8s} median |err| {v['median_abs_ms']:.1f} ms, within 5 ms {v['within_5ms']:.1%}")
    print("level vs velocity (Spearman):", {k: round(v, 2) for k, v in rho.items()})
    print("true notes never transcribed:", sorted(set(tn) - set(en)))


def pool(paths, out_path):
    """Combine per-solo validations: counts summed, timing errors and level pairs concatenated."""
    vs = [json.loads(Path(p).read_text()) for p in paths]
    per_cat, hits = {}, {}
    for v in vs:
        for c, d in v["per_category"].items():
            a = per_cat.setdefault(c, {"true": 0, "transcribed": 0})
            a["true"] += d["true"]
            a["transcribed"] += d["transcribed"]
            hits[c] = hits.get(c, 0) + (round(d["recall"] * d["true"]) if d["true"] else 0)
    for c, a in per_cat.items():
        a["recall"] = hits[c] / a["true"] if a["true"] else None
        a["precision"] = hits[c] / a["transcribed"] if a["transcribed"] else None
    n_true = sum(a["true"] for a in per_cat.values())
    n_trans = sum(a["transcribed"] for a in per_cat.values())
    rec, prec = sum(hits.values()) / n_true, sum(hits.values()) / n_trans
    notes = lambda key: sorted(sum((Counter(dict(v[key])) for v in vs), Counter()).items())
    err = {k: np.concatenate([np.array(v["timing_error_ms"][k]) for v in vs]) for k in ("raw", "refined")}
    lv = {k: sum((v["level_vs_velocity"][k] for v in vs), []) for k in ("cat", "velocity", "level_db")}
    cats, vel, lev = np.array(lv["cat"]), np.array(lv["velocity"]), np.array(lv["level_db"])
    rho = {c: float(stats.spearmanr(vel[cats == c], lev[cats == c])[0])
           for c in drums.CATEGORIES if (cats == c).sum() >= 30 and len(set(vel[cats == c])) > 1}
    out = {"solos": [Path(p).stem for p in paths], "tolerance_ms": vs[0]["tolerance_ms"],
           "recall": rec, "precision": prec, "f1": 2 * rec * prec / (rec + prec), "per_category": per_cat,
           "true_notes": notes("true_notes"), "transcribed_notes": notes("transcribed_notes"),
           "timing_error_ms": {k: rnd(e, 2) for k, e in err.items()},
           "timing_summary": {k: {"median_abs_ms": float(np.median(np.abs(e))), "within_5ms": float(np.mean(np.abs(e) <= 5))}
                              for k, e in err.items()},
           "level_vs_velocity": {**lv, "spearman": rho}}
    Path(out_path).write_text(json.dumps(out))


if __name__ == "__main__":
    main(*sys.argv[1:5])
