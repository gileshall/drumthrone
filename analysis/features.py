#!/usr/bin/env python3
"""Audio and MIDI features for one drum solo.

usage: uv run python features.py <audio> <midi> <out.json> [--start S --end E] [--native]

--start/--end analyse only that stretch of the recording (the bracketed solo).
--native: the MIDI is the solo's own score, so its times are exact and its velocities real;
hit times are only shifted by one clock offset against the audio, never refined.
"""
import argparse
import json
import re
import subprocess
import zlib
from collections import Counter
from pathlib import Path

import librosa
import mido
import numpy as np
from scipy import signal

import drums

SR = 44100
HOP_FINE = 64       # sharp onset envelope for hit timing, 1.45 ms
HOP_T = 512         # tempo, spectra and structure, 11.6 ms
GROUP_TOL = 0.030   # hits within 30 ms of a group's first hit form one stroke group
WIN = 2.0           # seconds per window for curves and self-similarity
STEPS = 12          # grid steps per beat: 8ths, 16ths, 8th triplets, 16th triplets
REST = 0.5          # a silence at least this long between hits counts as a rest
RUN_MIN = 6         # strokes in a steady run before its evenness is measured
EVEN_MIN = 30       # strokes measured before timing jitter is reported: enough to estimate a spread to ~13%
VOCAB_BLOCK = 64    # beats per block when counting distinct rhythms, so solo length drops out
NOVELTY_HALF = 8    # novelty kernel half-width in windows (16 s)
BANDS = {"low": (30, 150), "mid": (150, 2500), "high": (5000, 16000)}
CATS = list(drums.CATEGORIES)
GRID = {0: "beat", 6: "8th", 3: "16th", 9: "16th", 4: "triplet", 8: "triplet", 2: "sextuplet", 10: "sextuplet"}
DEPTH = {"beat": 0, "8th": 1, "16th": 2, "triplet": 2, "sextuplet": 3, "off-grid": 4}
rng = np.random.default_rng(0)


def rnd(a, d=3):
    return np.round(np.asarray(a, dtype=float), d).tolist()


# ---------------------------------------------------------------- audio

def loudness(path, start, end):
    """EBU R128 via ffmpeg: momentary (400 ms) and short-term (3 s) loudness every 100 ms, plus summary."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                        "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    rows = re.findall(r"t:\s*([\d.]+)\s+TARGET:\S+\s+LUFS\s+M:\s*(\S+)\s+S:\s*(\S+)", p.stderr)
    t, m, s = (np.array([float(r[i]) for r in rows]) for i in range(3))
    m[m < -70], s[s < -70] = np.nan, np.nan  # meter floor (-120.7) before the signal starts
    summary = p.stderr.rsplit("Summary:", 1)[1]

    def val(key):
        return float(re.search(rf"{key}:\s*(-?[\d.]+)", summary)[1])

    return t, m, s, {"integrated_lufs": val("I"), "lra_lu": val("LRA"), "lra_low_lufs": val("LRA low"),
                     "lra_high_lufs": val("LRA high"), "true_peak_dbfs": val("Peak")}


def band_envelope(y, lo, hi, hop=128, win=512):
    """Band-limited energy in dB, one centered frame every `hop` samples."""
    sos = signal.butter(4, [lo, hi], btype="band", fs=SR, output="sos")
    p = np.pad(signal.sosfiltfilt(sos, y) ** 2, win // 2)
    e = librosa.util.frame(p, frame_length=win, hop_length=hop).mean(axis=0)
    return 10 * np.log10(e + 1e-12)


def peak_times(env, frames, hop):
    """Frame indices to seconds, with parabolic interpolation around each peak."""
    fr = hop / SR
    out = frames.astype(float)
    for i, k in enumerate(frames):
        if 0 < k < len(env) - 1:
            a, b, c = env[k - 1], env[k], env[k + 1]
            den = a - 2 * b + c
            if b >= a and b >= c and den < 0:  # the parabola vertex is only meaningful at a local maximum
                out[i] = k + 0.5 * (a - c) / den
    return out * fr


def sharp_flux(y):
    """Spectral flux on short (11.6 ms) frames: peaks narrow enough to separate 16ths at 180 BPM."""
    return librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP_FINE, n_fft=512, n_mels=64)


def refine(times, env, hop, radius):
    """Snap each time to the strongest onset-envelope frame within `radius` seconds."""
    fr = hop / SR
    r = int(round(radius / fr))
    frames = np.empty(len(times), dtype=int)
    for i, t in enumerate(times):
        c = int(round(t / fr))
        lo, hi = max(c - r, 0), min(c + r, len(env) - 1)
        frames[i] = lo + int(np.argmax(env[lo:hi + 1]))
    return peak_times(env, frames, hop)


def windows(values_at, t, n, reducer=np.mean):
    """Reduce samples (times t) into n consecutive WIN-second windows."""
    idx = np.floor(t / WIN).astype(int)
    out = np.full(n, np.nan)
    for w in range(n):
        v = values_at[idx == w]
        v = v[~np.isnan(v)]
        if len(v):
            out[w] = reducer(v)
    return out


def align_and_refine(times, env):
    """Estimate the transcription's clock offset against the audio, then refine every time within 15 ms."""
    offset = float(np.median(refine(times, env, HOP_FINE, radius=0.040) - times))
    return offset, refine(times + offset, env, HOP_FINE, radius=0.015)


def hit_levels(y, times, cats):
    """Peak band energy around each hit, in dB below that band's 99th percentile."""
    efr = 128 / SR
    level = np.empty(len(times))
    for b, (lo, hi) in BANDS.items():
        env = band_envelope(y, lo, hi)
        ref = np.percentile(env, 99)
        for i in np.flatnonzero([drums.BAND_OF[c] == b for c in cats]):
            a, z = int((times[i] - 0.010) / efr), int((times[i] + 0.050) / efr) + 1
            level[i] = env[max(a, 0):max(z, 1)].max() - ref
    return level


def energy_mean_db(v):
    return 10 * np.log10(np.mean(10 ** (v / 10)))


def cosine_ssm(X):
    """Cosine similarity of mean-centered rows, mapped from [-1, 1] to [0, 1]."""
    X = X - X.mean(axis=0)
    n = np.linalg.norm(X, axis=1, keepdims=True)
    Xn = X / np.where(n == 0, 1, n)
    return (1 + Xn @ Xn.T) / 2


def novelty(S, half):
    """Foote novelty: a Gaussian-tapered checkerboard kernel slid along the diagonal."""
    g = signal.windows.gaussian(2 * half, std=half / 2)
    sign = np.block([[np.ones((half, half)), -np.ones((half, half))],
                     [-np.ones((half, half)), np.ones((half, half))]])
    K = np.outer(g, g) * sign
    P = np.pad(S, half, mode="reflect")
    nov = np.array([np.sum(P[i:i + 2 * half, i:i + 2 * half] * K) for i in range(len(S))])
    nov = np.clip(nov, 0, None)
    return nov / nov.max()


def smooth(x, k=5):
    x = np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    num = np.convolve(np.where(ok, x, 0), np.ones(k), "same")
    den = np.convolve(ok.astype(float), np.ones(k), "same")
    return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)


def zscore(x):
    return (x - np.nanmean(x)) / np.nanstd(x)


# ---------------------------------------------------------------- symbolic

def load_hits(path, with_velocity=False):
    t, out = 0.0, []
    for m in mido.MidiFile(path):
        t += m.time
        if m.type == "note_on" and m.velocity > 0:
            out.append((t, m.note, m.velocity))
    out.sort()
    cols = [np.array([h[i] for h in out]) for i in range(3)]
    return cols if with_velocity else cols[:2]


def group_hits(times):
    groups = []
    for i, t in enumerate(times):
        if groups and t - times[groups[-1][0]] <= GROUP_TOL:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def smooth_beats(beats, half=4):
    """Local linear fit of beat time against beat index (+-half beats): a steady pulse that follows drift."""
    idx = np.arange(len(beats))
    out = np.empty(len(beats))
    for i in idx:
        lo, hi = max(0, i - half), min(len(beats), i + half + 1)
        a, b = np.polyfit(idx[lo:hi], beats[lo:hi], 1)
        out[i] = a * i + b
    return out


def lz76(s):
    """Phrase count of the Lempel-Ziv (1976) parsing (Kaspar-Schuster algorithm)."""
    n = len(s)
    i, k, l, c, kmax = 0, 1, 1, 1, 1
    while True:
        if s[i + k - 1] == s[l + k - 1]:
            k += 1
            if l + k > n:
                c += 1
                break
        else:
            kmax = max(k, kmax)
            i += 1
            if i == l:
                c += 1
                l += kmax
                if l + 1 > n:
                    break
                i, k, kmax = 0, 1, 1
            else:
                k = 1
    return c


def entropy_bits(counts):
    p = np.asarray([c for c in counts if c > 0], dtype=float)
    p /= p.sum()
    return float(-(p * np.log2(p)).sum())


def npvi(d):
    d = np.asarray(d)
    return float(100 * np.mean(np.abs(np.diff(d)) / ((d[1:] + d[:-1]) / 2)))


# ---------------------------------------------------------------- main

def main(audio, midi, out_path, start=None, end=None, native=False):
    audio, midi = Path(audio), Path(midi)
    full = librosa.get_duration(path=audio)
    start = 0.0 if start is None else start
    end = full if end is None else end
    y, _ = librosa.load(audio, sr=SR, mono=True, offset=start, duration=end - start)
    dur = len(y) / SR
    nwin = int(dur // WIN)
    wt = (np.arange(nwin) + 0.5) * WIN
    sc = {"duration_s": dur}

    # Loudness and level
    lt, lm, ls, lsum = loudness(audio, start, end)
    sc.update(lsum)
    sc["plr_db"] = lsum["true_peak_dbfs"] - lsum["integrated_lufs"]
    sc["crest_db"] = float(20 * np.log10(np.abs(y).max() / np.sqrt(np.mean(y ** 2))))
    sc["momentary_p10_lufs"], sc["momentary_p95_lufs"] = np.nanpercentile(lm, [10, 95]).tolist()
    sc["momentary_spread_lu"] = sc["momentary_p95_lufs"] - sc["momentary_p10_lufs"]

    # Spectra
    D = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP_T)) ** 2
    ft = librosa.frames_to_time(np.arange(D.shape[1]), sr=SR, hop_length=HOP_T)
    mel64 = librosa.feature.melspectrogram(S=D, sr=SR, n_mels=64, fmax=16000)
    mel_f = librosa.mel_frequencies(n_mels=64, fmax=16000)
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(mel64), n_mfcc=20)
    centroid = librosa.feature.spectral_centroid(S=np.sqrt(D), sr=SR)[0]
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    band_pow = {b: D[(freqs >= lo) & (freqs < hi)].sum(axis=0) for b, (lo, hi) in BANDS.items()}
    oenv_t = librosa.onset.onset_strength(S=librosa.power_to_db(librosa.feature.melspectrogram(S=D, sr=SR)), sr=SR)
    del D

    # Sharp onset envelope for hit timing and an audio-only activity curve
    flux = sharp_flux(y)
    flux_t = librosa.frames_to_time(np.arange(len(flux)), sr=SR, hop_length=HOP_FINE)

    # Tempo and beats
    tempo_global = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=oenv_t, sr=SR, hop_length=HOP_T))[0])
    tempo_local = librosa.feature.tempo(onset_envelope=oenv_t, sr=SR, hop_length=HOP_T, aggregate=None)
    bt_tempo, beat_frames = librosa.beat.beat_track(onset_envelope=oenv_t, sr=SR, hop_length=HOP_T)
    beats = peak_times(oenv_t, np.asarray(beat_frames), HOP_T)
    ibi = np.diff(beats)
    ibi_bpm = 60 / ibi
    sbeats = smooth_beats(beats)
    tg = librosa.feature.tempogram(onset_envelope=oenv_t, sr=SR, hop_length=HOP_T, win_length=384)
    tg_bpm = librosa.tempo_frequencies(tg.shape[0], hop_length=HOP_T, sr=SR)
    local_cv = [np.std(ibi[i:i + 8]) / np.mean(ibi[i:i + 8]) for i in range(0, len(ibi) - 7)]
    ratio = ibi[1:] / ibi[:-1]
    slope = np.polyfit(beats[1:], ibi_bpm, 1)[0] * 60
    sc.update(tempo_global_bpm=tempo_global, tempo_beat_tracker_bpm=float(np.atleast_1d(bt_tempo)[0]),
              n_beats=len(beats), ibi_median_ms=float(np.median(ibi) * 1000),
              tempo_p10_bpm=float(np.percentile(ibi_bpm, 10)), tempo_p90_bpm=float(np.percentile(ibi_bpm, 90)),
              ibi_cv=float(np.std(ibi) / np.mean(ibi)), local_ibi_cv_median=float(np.median(local_cv)),
              tempo_drift_bpm_per_min=float(slope),
              octave_jumps=int(np.sum((ratio > 1.8) | (ratio < 0.55))))

    # Hits, aligned to the audio clock
    times, notes, vels = load_hits(midi, with_velocity=True)
    keep = (times >= start) & (times < end)
    times, notes, vels = times[keep] - start, notes[keep], vels[keep]
    cats = np.array([drums.category(n) for n in notes])
    groups = group_hits(times)
    gt = np.array([times[g[0]] for g in groups])
    offset, gt_ref = align_and_refine(gt, flux)
    if native:  # exact score times: one clock shift, no per-stroke snapping
        gt_ref = gt + offset
    shift = gt_ref - (gt + offset)
    t_ref = np.empty(len(times))
    for g, tr in zip(groups, gt_ref):
        t_ref[g] = tr
    sc.update(midi_offset_ms=offset * 1000, refine_shift_median_abs_ms=float(np.median(np.abs(shift)) * 1000),
              refine_at_edge_frac=float(np.mean(np.abs(shift) >= 0.015 - HOP_FINE / SR)))
    level = hit_levels(y, t_ref, cats)

    # Counts and range
    note_counts = Counter(int(n) for n in notes)
    cat_counts = Counter(cats.tolist())
    sc.update(n_hits=len(times), n_groups=len(groups), hits_per_s=len(times) / dur,
              groups_per_s=len(groups) / dur, distinct_notes=len(note_counts),
              distinct_categories=len(cat_counts), note_entropy_bits=entropy_bits(note_counts.values()),
              category_entropy_bits=entropy_bits(cat_counts.values()),
              notes_outside_gm=int(sum(c for n, c in note_counts.items() if not 35 <= n <= 81)))
    sc["note_entropy_norm"] = sc["note_entropy_bits"] / np.log2(len(note_counts)) if len(note_counts) > 1 else 0.0
    per_sec = np.histogram(times, bins=np.arange(0, np.ceil(dur) + 1))[0]
    sc["peak_hits_per_s"] = int(per_sec.max())
    for c in CATS:
        sc[f"share_{c}"] = cat_counts.get(c, 0) / len(times)
    lvl = {c: level[cats == c] for c in CATS if (cats == c).any()}
    for c, v in lvl.items():
        sc[f"level_median_db_{c}"] = float(np.median(v))
        sc[f"level_iqr_db_{c}"] = float(np.subtract(*np.percentile(v, [75, 25])))

    if native:
        for c in CATS:
            v = vels[cats == c]
            if len(v) >= 20:
                sc[f"velocity_median_{c}"] = float(np.median(v))
                sc[f"velocity_iqr_{c}"] = float(np.subtract(*np.percentile(v, [75, 25])))

    # Rhythm: inter-onset intervals between stroke groups
    ioi = np.diff(gt_ref)
    ioi_bins = 2 ** np.arange(np.log2(0.02), np.log2(2.0) + 1e-9, 1 / 6)
    sc.update(ioi_median_ms=float(np.median(ioi) * 1000),
              ioi_entropy_bits=entropy_bits(np.histogram(np.clip(ioi, 0.02, 2.0), bins=ioi_bins)[0]),
              npvi=npvi(ioi))
    rests = ioi[ioi >= REST]
    phrase_breaks = np.flatnonzero(ioi >= REST)
    bounds = np.r_[0, phrase_breaks + 1, len(gt_ref)]
    phrase_len = np.array([gt_ref[b - 1] - gt_ref[a] for a, b in zip(bounds[:-1], bounds[1:])])
    sc.update(n_rests=len(rests), rest_time_frac=float(rests.sum() / dur), n_phrases=len(phrase_len),
              phrase_median_s=float(np.median(phrase_len)))

    # Beat grid: phase, subdivision class and microtiming for every hit
    k = np.searchsorted(sbeats, t_ref, side="right") - 1
    inside = (k >= 0) & (k < len(sbeats) - 1)
    kk = np.clip(k, 0, len(sbeats) - 2)
    blen = sbeats[kk + 1] - sbeats[kk]
    phase = np.where(inside, (t_ref - sbeats[kk]) / blen, np.nan)
    pos = np.round(phase * STEPS)
    step = np.where(inside, pos % STEPS, -1).astype(int)
    beat_of = np.where(pos == STEPS, kk + 1, kk)
    dev_ms = np.where(inside, (phase * STEPS - pos) / STEPS * blen * 1000, np.nan)
    gclass = np.array([GRID.get(s, "off-grid") if s >= 0 else "" for s in step])
    gi = gclass != ""
    class_counts = Counter(gclass[gi].tolist())
    for cl in DEPTH:
        sc[f"grid_{cl}"] = class_counts.get(cl, 0) / gi.sum()
    sc["metrical_depth_mean"] = float(np.mean([DEPTH[c] for c in gclass[gi]]))
    sc["microtiming_mad_ms"] = float(np.median(np.abs(dev_ms[gi])))
    sc["microtiming_sd_ms"] = float(np.std(dev_ms[gi]))
    for c in CATS:
        sel = gi & (cats == c)
        if sel.sum() >= 20:
            sc[f"microtiming_mean_ms_{c}"] = float(np.mean(dev_ms[sel]))
    for c in ("kick", "snare"):
        sel = gi & (cats == c)
        if sel.any():
            sc[f"offbeat_frac_{c}"] = float(np.mean(~np.isin(step[sel], (0, 6))))

    sc["grid_lock"] = float(np.abs(np.mean(np.exp(2j * np.pi * STEPS * phase[gi]))))

    # Evenness: in steady runs, each stroke against the midpoint of the strokes two either side. Comparing
    # same-parity neighbours keeps swing (long-short pairs) from counting as timing error.
    pair = ioi[:-1] + ioi[1:]  # pair[k] = t[k + 2] - t[k]
    even_dev, even_ioi = [], []
    i = 0
    while i < len(pair):
        j = i + 1
        while j < len(pair) and 0.080 <= pair[j] <= 0.500 and 0.8 <= pair[j] / pair[i] <= 1.25:
            j += 1
        if 0.080 <= pair[i] <= 0.500 and j + 2 - i >= RUN_MIN:
            tr = gt_ref[i:j + 2]
            even_dev.extend((tr[2:-2] - (tr[:-4] + tr[4:]) / 2).tolist())
            even_ioi.extend([float(np.median(pair[i:j])) / 2] * (len(tr) - 4))
        i = j
    even_dev = np.array(even_dev)
    measurable = len(even_dev) >= EVEN_MIN
    sc.update(even_run_strokes=len(even_dev), steady_run_share=len(even_dev) / len(groups),
              stroke_jitter_ms=float(np.std(even_dev) / np.sqrt(1.5) * 1000) if measurable else None,
              stroke_jitter_rel=float(np.std(even_dev / np.array(even_ioi)) / np.sqrt(1.5)) if measurable else None)

    # Complexity: symbol per grid step = which categories sound there
    nb = len(sbeats) - 1
    seq = np.zeros(nb * STEPS, dtype=np.int64)
    for b, s, c in zip(beat_of[gi], step[gi], cats[gi]):
        if b < nb:
            seq[b * STEPS + s] |= 1 << CATS.index(c)
    lz = lz76(seq.tolist())
    lz_sh = np.mean([lz76(rng.permutation(seq).tolist()) for _ in range(5)])
    zb = seq.astype(np.uint8).tobytes()
    z_sh = np.mean([len(zlib.compress(rng.permutation(seq).astype(np.uint8).tobytes(), 9)) for _ in range(5)])
    cells = seq.reshape(nb, STEPS)
    rhythm_cells = [int(sum(1 << i for i in range(STEPS) if row[i])) for row in cells]
    orch_cells = [tuple(row) for row in cells]

    def growth(cs):
        seen, out = set(), []
        for x in cs:
            seen.add(x)
            out.append(len(seen))
        return out

    rg, og = growth(rhythm_cells), growth(orch_cells)
    nblk = nb // VOCAB_BLOCK
    blocks = range(0, nblk * VOCAB_BLOCK, VOCAB_BLOCK)
    # a solo shorter than one block has no per-block vocabulary: not measurable
    sc["rhythm_vocab_per_block"] = float(np.mean([len(set(rhythm_cells[b:b + VOCAB_BLOCK])) for b in blocks])) if nblk else None
    sc["orch_vocab_per_block"] = float(np.mean([len(set(orch_cells[b:b + VOCAB_BLOCK])) for b in blocks])) if nblk else None
    sc.update(lz_relative=float(lz / lz_sh), zlib_relative=float(len(zlib.compress(zb, 9)) / z_sh),
              rhythm_cell_vocab=rg[-1], rhythm_cell_repeat_rate=1 - rg[-1] / nb,
              rhythm_cell_entropy_bits=entropy_bits(Counter(rhythm_cells).values()),
              orch_cell_vocab=og[-1], orch_cell_repeat_rate=1 - og[-1] / nb)
    top_cells = Counter(rhythm_cells).most_common(12)

    # Playability: stroke groups against a four-limb body
    sizes = np.array([len(g) for g in groups])
    hands = np.array([sum(notes[i] not in drums.FEET for i in g) for g in groups])
    feet = sizes - hands
    viol = [(float(gt_ref[j]), [int(notes[i]) for i in g]) for j, g in enumerate(groups)
            if hands[j] > 2 or feet[j] > 2]
    sc.update(max_group_size=int(sizes.max()), max_hands_in_group=int(hands.max()),
              limb_violations=len(viol), limb_violations_per_min=len(viol) / dur * 60)

    # Windowed curves
    cat_rate = {c: rnd(windows(np.ones((cats == c).sum()), t_ref[cats == c], nwin, np.sum) / WIN, 2)
                for c in CATS if (cats == c).any()}
    total_rate = windows(np.ones(len(t_ref)), t_ref, nwin, np.sum) / WIN
    total_rate = np.nan_to_num(total_rate)
    for c in cat_rate:
        cat_rate[c] = np.nan_to_num(np.array(cat_rate[c], dtype=float)).tolist()
    activity = windows(flux, flux_t, nwin)
    activity = activity / np.nanmax(activity)
    loud_w = windows(lm, lt, nwin, energy_mean_db)
    cent_w = windows(centroid, ft, nwin)
    band_w = {b: windows(p, ft, nwin) for b, p in band_pow.items()}
    band_tot = sum(band_w.values())
    band_tot[band_tot == 0] = np.nan  # digitally silent windows have no band shares
    tempo_w = windows(tempo_local, librosa.frames_to_time(np.arange(len(tempo_local)), sr=SR, hop_length=HOP_T),
                      nwin, np.median)
    level_w = {c: rnd(windows(level[cats == c], t_ref[cats == c], nwin, np.median), 1)
               for c in ("kick", "snare", "hi-hat", "ride") if (cats == c).sum() >= 50}
    dom = [max(CATS, key=lambda c: cat_rate.get(c, [0] * nwin)[w]) if total_rate[w] > 0 else None
           for w in range(nwin)]
    changes = sum(1 for a, b in zip(dom, dom[1:]) if a and b and a != b)
    intensity = smooth((zscore(total_rate) + zscore(loud_w)) / 2)
    sc["density_contrast"] = float(np.subtract(*np.percentile(total_rate, [90, 10])) / np.mean(total_rate))
    ok = ~np.isnan(loud_w)
    sc.update(orchestration_changes_per_min=changes / dur * 60,
              intensity_peak_pos=float(wt[np.nanargmax(intensity)] / dur),
              density_loudness_corr=float(np.corrcoef(total_rate[ok], loud_w[ok])[0, 1]),
              density_activity_corr=float(np.corrcoef(total_rate, np.nan_to_num(activity))[0, 1]))

    # Structure: three self-similarity views on the same 2 s windows
    def win_mean(F, frame_t):
        idx = np.floor(frame_t / WIN).astype(int)
        return np.stack([F[:, idx == w].mean(axis=1) for w in range(nwin)])

    timbre = win_mean(mfcc[1:], ft)
    timbre = (timbre - timbre.mean(0)) / timbre.std(0)
    lag_ok = (tg_bpm >= 30) & (tg_bpm <= 400)
    rhythm = win_mean(tg[lag_ok], librosa.frames_to_time(np.arange(tg.shape[1]), sr=SR, hop_length=HOP_T))
    symb = np.zeros((nwin, len(CATS) * STEPS))
    for t, s, c in zip(t_ref[gi], step[gi], cats[gi]):
        w = int(t // WIN)
        if w < nwin:
            symb[w, CATS.index(c) * STEPS + s] += 1
    ssm = {"timbre": cosine_ssm(timbre), "rhythm": cosine_ssm(rhythm), "symbolic": cosine_ssm(symb)}
    nov = novelty(sum(ssm.values()) / 3, NOVELTY_HALF)
    pk, _ = signal.find_peaks(nov, distance=NOVELTY_HALF, prominence=0.15)
    edges = np.r_[0, wt[pk], dur]
    sc.update(n_sections=len(pk) + 1, section_median_s=float(np.median(np.diff(edges))))

    # Images for display
    blk = int(round(0.25 * SR / HOP_T))
    nblk = mel64.shape[1] // blk
    mel_img = librosa.power_to_db(mel64[:, :nblk * blk].reshape(64, nblk, blk).mean(axis=2), ref=np.max)
    tg_t = librosa.frames_to_time(np.arange(tg.shape[1]), sr=SR, hop_length=HOP_T)
    bpm_axis = np.geomspace(40, 320, 96)
    lag_sel = np.flatnonzero((tg_bpm >= 35) & (tg_bpm <= 340))
    tg_half = int(round(0.5 * SR / HOP_T))
    ntg = tg.shape[1] // tg_half
    tg_blk = tg[:, :ntg * tg_half].reshape(tg.shape[0], ntg, tg_half).mean(axis=2)
    tg_img = np.stack([np.interp(bpm_axis, tg_bpm[lag_sel][::-1], col[lag_sel][::-1]) for col in tg_blk.T], axis=1)
    tg_img /= np.maximum(tg_img.max(axis=0, keepdims=True), 1e-9)

    out = {
        "clip": {"audio": str(audio), "midi": str(midi), "segment": [start, end], "native": native},
        "scalars": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in sc.items()},
        "hits": {"t": rnd(t_ref), "note": notes.tolist(), "cat": cats.tolist(), "level_db": rnd(level, 1),
                 "velocity": vels.tolist(),
                 "phase": rnd(phase), "step": step.tolist(), "dev_ms": rnd(dev_ms, 1), "grid": gclass.tolist()},
        "evenness": {"dev_ms": rnd(even_dev * 1000, 2), "run_ioi_ms": rnd(np.array(even_ioi) * 1000, 1)},
        "groups": {"t": rnd(gt_ref), "size": sizes.tolist(), "hands": hands.tolist(), "feet": feet.tolist(),
                   "violations": viol[:200]},
        "beats": {"t": rnd(beats), "smoothed": rnd(sbeats), "ibi_bpm": rnd(ibi_bpm, 1)},
        "loudness": {"t": rnd(lt, 1), "momentary": rnd(lm, 1), "short_term": rnd(ls, 1)},
        "windows": {"t": rnd(wt, 1), "hits_per_s": rnd(total_rate, 2), "hits_per_s_by_cat": cat_rate,
                    "audio_activity": rnd(activity, 3), "loudness_lufs": rnd(loud_w, 1),
                    "centroid_hz": rnd(cent_w, 0),
                    "band_share": {b: rnd(v / band_tot, 3) for b, v in band_w.items()},
                    "tempo_bpm": rnd(tempo_w, 1), "level_db_by_cat": level_w,
                    "intensity": rnd(intensity, 3), "novelty": rnd(nov, 3), "dominant": dom},
        "sections": {"boundaries_s": rnd(wt[pk], 1)},
        "cells": {"rhythm_growth": rg, "orch_growth": og, "top_rhythm": top_cells, "steps": STEPS},
        "images": {
            "mel": {"t_step": 0.25, "freqs": rnd(mel_f, 0), "db": rnd(mel_img, 0)},
            "tempogram": {"t_step": 0.5, "bpm": rnd(bpm_axis, 1), "z": rnd(tg_img, 2)},
            "ssm": {k: rnd(v, 2) for k, v in ssm.items()},
        },
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out))
    for k, v in out["scalars"].items():
        print(f"{k:32s} {v}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("midi")
    ap.add_argument("out")
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--native", action="store_true")
    a = ap.parse_args()
    main(a.audio, a.midi, a.out, a.start, a.end, a.native)
