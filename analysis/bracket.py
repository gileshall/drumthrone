#!/usr/bin/env python3
"""Find where the drum solo starts and ends in a recording, and say when to double-check.

Evidence per 1 s window: drum hits (drums-only transcription), notes from every other instrument
(unrestricted transcription), harmonic energy share (HPSS) and level.

usage: uv run python bracket.py <audio> <drums.mid> <full.json> <out.json>
"""
import json
import sys
from collections import Counter
from pathlib import Path

import librosa
import numpy as np
from scipy import ndimage

from features import load_hits

SR = 22050
HOP = 512
DRUM_MIN = 1.5    # drum hits per second for a window to count as drumming
OTHER_MIN = 4.0   # 5 s average of other-instrument notes per second that can mean a band
OTHER_RATIO = 0.6 # ...and only if it is at least this share of the drum rate: phantom notes ride on drum hits
RUN_MIN = 4       # seconds of solo-like windows that open or close the bracket
PRE = 0.10        # seconds kept before the first hit
TAIL = 1.5        # seconds kept after the last hit, for the ring-out
QUIET_DB = -45    # a region this quiet (dBFS RMS) is silence


def runs_of(mask):
    lab, n = ndimage.label(mask)
    return [np.flatnonzero(lab == k + 1) for k in range(n)]


def per_second(times, n):
    return np.bincount(np.clip(np.floor(times).astype(int), 0, n - 1), minlength=n)[:n].astype(float)


def describe(sl, drum, band, voice, level, inst_by_w):
    """Plain description of what a trimmed region contains."""
    n = sl.stop - sl.start
    if n < 1:
        return {"seconds": 0, "text": "nothing"}
    parts = []
    insts = Counter()
    for w in range(sl.start, sl.stop):
        insts.update(inst_by_w[w])
    if np.median(level[sl]) < QUIET_DB:
        parts.append("near silence")
    if (drum[sl] >= DRUM_MIN).mean() > 0.3:
        parts.append("drumming")
    if band[sl].mean() > 0.2:
        parts.append("other instruments (" + ", ".join(i for i, _ in insts.most_common(3) if i != "voice") + ")")
    if voice[sl].sum() >= 3:
        parts.append("voice")
    if not parts:
        parts.append("sound with no transcribed notes (crowd, room or effects)")
    return {"seconds": n, "text": ", ".join(parts), "instruments": insts.most_common(5),
            "drumming_frac": float((drum[sl] >= DRUM_MIN).mean())}


def main(audio, drums_mid, full_json, out_path):
    y, _ = librosa.load(audio, sr=SR, mono=True)
    dur = len(y) / SR
    n = int(np.ceil(dur))

    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    H, P = librosa.decompose.hpss(S)
    ft = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=HOP)
    w_of = np.clip(np.floor(ft).astype(int), 0, n - 1)
    eh = np.bincount(w_of, (H ** 2).sum(0), minlength=n)
    ep = np.bincount(w_of, (P ** 2).sum(0), minlength=n)
    harm = eh / np.maximum(eh + ep, 1e-12)
    del S, H, P
    frames = librosa.util.frame(np.pad(y, (0, n * SR - len(y))), frame_length=SR, hop_length=SR)
    level = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=0)) + 1e-9)

    times, _ = load_hits(drums_mid)
    drum = per_second(times, n)
    ev = [e for e in json.loads(Path(full_json).read_text()) if e["type"] == "start" and e["instrument"] != "drums"]
    other = per_second(np.array([e["start_time"] for e in ev]), n)
    voice = per_second(np.array([e["start_time"] for e in ev if e["instrument"] == "voice"]), n)
    inst_by_w = [Counter() for _ in range(n)]
    for e in ev:
        inst_by_w[min(int(e["start_time"]), n - 1)][e["instrument"]] += 1

    other_s = ndimage.uniform_filter1d(other, 5)
    band = (other_s >= OTHER_MIN) & (other_s >= OTHER_RATIO * ndimage.uniform_filter1d(drum, 5))
    solo_like = (drum >= DRUM_MIN) & ~band
    closed = ndimage.binary_closing(np.r_[False, solo_like, False], structure=np.ones(3))[1:-1] | solo_like
    long_runs = [r for r in runs_of(closed) if len(r) >= RUN_MIN]
    series = {"drum": drum.tolist(), "other": other.tolist(), "voice": voice.tolist(),
              "harmonic": np.round(harm, 3).tolist(), "level_db": np.round(level, 1).tolist(),
              "band": band.astype(int).tolist(), "solo_like": solo_like.astype(int).tolist()}
    if not long_runs:  # recorded, not raised: the caller decides whether a solo is required
        whole = describe(slice(0, n), drum, band, voice, level, inst_by_w)
        out = {"audio": str(audio), "duration": dur, "start": None, "end": None, "covered_frac": 0.0, "check": True,
               "reasons": [f"no stretch of at least {RUN_MIN} s sounds like solo drums"], "lead": whole,
               "tail": {"seconds": 0, "text": "nothing"}, "inside": {}, "series": series}
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(out))
        print(f"NONE  {Path(audio).stem}: no solo stretch; {whole['text']}")
        return
    w0, w1 = int(long_runs[0][0]), int(long_runs[-1][-1]) + 1
    first = times[(times >= w0) & (times < w0 + 1)]
    last = times[(times >= w1 - 1) & (times < w1)]
    start = max(0.0, float(first.min()) - PRE)
    end = min(dur, float(last.max()) + TAIL)

    inside = slice(w0, w1)
    ins = Counter()
    for w in range(w0, w1):
        ins.update(inst_by_w[w])
    gaps = [len(r) for r in runs_of(drum[inside] < 0.5)]
    lead = describe(slice(0, w0), drum, band, voice, level, inst_by_w)
    tail = describe(slice(w1, n), drum, band, voice, level, inst_by_w)
    other_frac = float(band[inside].mean())
    voice_s = int((voice[inside] > 0).sum())
    reasons = []
    if other_frac > 0.03:
        reasons.append(f"band-like activity in {other_frac:.0%} of the solo's seconds "
                       f"({', '.join(i for i, _ in ins.most_common(3))})")
    if voice_s > 3:
        reasons.append(f"voice notes in {voice_s} s of the solo")
    for name, region in (("before", lead), ("after", tail)):
        if region["seconds"] > 5 and region["drumming_frac"] > 0.3:
            reasons.append(f"{region['seconds']} s trimmed {name} the solo contain drumming ({region['text']})")
    if gaps and max(gaps) > 6:
        reasons.append(f"a {max(gaps)} s stretch without drums inside the solo")
    if (end - start) / dur < 0.6:
        reasons.append(f"the solo is only {(end - start) / dur:.0%} of the track")

    out = {
        "audio": str(audio), "duration": dur, "start": round(start, 2), "end": round(end, 2),
        "covered_frac": (end - start) / dur, "check": bool(reasons), "reasons": reasons,
        "lead": lead, "tail": tail,
        "inside": {"other_frac": other_frac, "voice_seconds": voice_s, "instruments": ins.most_common(6),
                   "longest_gap_s": max(gaps) if gaps else 0, "harmonic_share_median": float(np.median(harm[inside]))},
        "series": series,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out))
    flag = "CHECK" if reasons else "ok"
    print(f"{flag:5s} {Path(audio).stem}: {start:.1f}-{end:.1f} s of {dur:.1f} ({(end - start) / dur:.0%}); "
          f"before: {lead['text']} ({lead['seconds']} s); after: {tail['text']} ({tail['seconds']} s)")
    for r in reasons:
        print(f"      - {r}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
