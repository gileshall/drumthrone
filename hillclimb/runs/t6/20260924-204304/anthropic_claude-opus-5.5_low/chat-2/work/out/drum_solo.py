#!/usr/bin/env python3
"""drum_solo.py - writes solo.mid, a two-minute drum solo for General MIDI channel 10.

Only mido is used. The random generator has a fixed seed, so every run writes the
same file.
"""
import math
import random
import mido

rng = random.Random(7031)

# ---------------------------------------------------------------- GM notes
K, K2, SS, SN = 36, 35, 37, 38
HH, HHP, HHO = 42, 44, 46
CR, CR2, CHINA, SPL = 49, 57, 52, 55
RIDE, BELL, COW = 51, 53, 56
TOMS = [50, 48, 47, 45, 43, 41]            # high tom down to low floor tom
BONGO_HI, BONGO_LO = 60, 61
TIMB_HI, TIMB_LO = 65, 66

# Every event is [beat, limb, note, velocity, duration]. Each limb is kept
# monophonic, so at most two hands and two feet strike at any instant.
EV = []
LIMB = {'R': 'RH', 'L': 'LH', 'K': 'RF', 'F': 'LF'}


def hit(t, limb, note, vel, dur=0.12):
    EV.append([t, limb, note, int(max(1, min(127, round(vel)))), dur])


# ---------------------------------------------------------------- the motif
# The motif sits on a 16th-note grid within one bar.
MOT = [0, 3, 6, 10, 12, 14]
MACC = [1.0, 0.8, 0.95, 0.85, 0.75, 1.0]
O1 = [SN, 50, SN, 43, SN, 41]
O2 = [SN, 48, 47, 43, 50, 41]
O4 = [50, 48, 45, 43, 41, 41]
O6 = [SN, SPL, SN, CHINA, SN, CR2]


def grid(t0, n, per, acc, ghost_p=0.0, ghosts=(SN,), gv=(20, 36), stick='RL', kicks=()):
    step = 1.0 / per
    for s in range(n):
        t = t0 + s * step
        h = stick[s % len(stick)]
        if s in acc:
            note, v = acc[s]
            hit(t, LIMB[h], K if h == 'K' else note, v)
        elif rng.random() < ghost_p:
            note = K if h == 'K' else rng.choice(ghosts)
            hit(t, LIMB[h], note, rng.uniform(*gv) + (15 if h == 'K' else 0))
    for s, note, v in kicks:
        if s < n:
            hit(t0 + s * step, 'RF', note, v)


def motif_bar(t0, orch, base, ghost_p=0.3, rot=0, per=4, kick_idx=(0, 5),
              crash=True, upto=4, ghosts=(SN,)):
    n = per * 4
    acc, kicks = {}, {}
    for i, s in enumerate(MOT):
        ss = (int(round(s * n / 16.0)) + rot) % n
        acc[ss] = (orch[i], base * MACC[i] + rng.uniform(-6, 6))
        if i in kick_idx:
            kicks[ss] = base * 0.9 + rng.uniform(-5, 5)
    if crash:
        acc[0] = (CR, base + 15)
        kicks[0] = base + 5
    grid(t0, int(per * upto), per, acc, ghost_p, ghosts=ghosts,
         kicks=[(s, K, v) for s, v in sorted(kicks.items())])


def travel(t0, beats, per, stick, path, v0, v1, curve=1.3, accent_every=None,
           accn=0, split=False):
    """A run that moves along `path` (a list of drums) over the phrase and
    shapes a crescendo from v0 to v1."""
    n = int(round(beats * per))
    for i in range(n):
        t = t0 + i / per
        h = stick[i % len(stick)]
        f = i / max(1, n - 1)
        v = v0 + (v1 - v0) * f ** curve
        if h == 'K':
            hit(t, 'RF', K, v * 0.9 + rng.uniform(-4, 4))
            continue
        if h == 'F':
            hit(t, 'LF', K2, v * 0.85 + rng.uniform(-4, 4))
            continue
        j = min(len(path) - 1, int(f * len(path)))
        if split and h == 'L' and j > 0 and rng.random() < 0.5:
            j -= 1
        if accent_every and i % accent_every == accn:
            v += 16
        elif i > 0 and stick[i % len(stick)] == stick[(i - 1) % len(stick)]:
            v -= 7                       # the second stroke of a double is softer
        hit(t, LIMB[h], path[j], v + rng.uniform(-5, 5))


def feet_q(t0, beats, v, note=K, limb='RF', step=1.0, start=0.0):
    b = start
    while b < beats - 1e-9:
        hit(t0 + b, limb, note, v + rng.uniform(-4, 4))
        b += step


KPATS = [[0, 6, 10], [0, 3, 6, 10], [0, 7, 10, 14], [0, 6, 8, 11], [0, 10, 11, 14]]


def groove(t0, inten, beats=4, ride=False, crash=False, motif=False, ghost_p=0.35):
    ne = int(beats * 2)
    for e in range(ne):
        t = t0 + e * 0.5
        if e == 0 and crash:
            hit(t, 'RH', CR, 105 + 15 * inten)
        elif ride:
            note = BELL if (e % 2 == 0 and rng.random() < 0.25) else RIDE
            hit(t, 'RH', note, (82 if e % 2 == 0 else 60) + 15 * inten + rng.uniform(-4, 4))
        else:
            note = HHO if (e == ne - 1 and rng.random() < 0.4) else HH
            hit(t, 'RH', note, (80 if e % 2 == 0 else 56) + 18 * inten + rng.uniform(-5, 5))
    for b in (1, 3):
        if b < beats:
            hit(t0 + b, 'LH', SN, 104 + 18 * inten + rng.uniform(-4, 4))
    for s in range(int(beats * 4)):
        if s % 2 == 1 and rng.random() < ghost_p:
            hit(t0 + s / 4, 'LH', SN, rng.uniform(20, 38))
    pat = [0, 3, 6, 10, 14] if motif else rng.choice(KPATS)
    for s in pat:
        if s < beats * 4:
            hit(t0 + s / 4, 'RF', K, (96 if s % 4 == 0 else 82) + 12 * inten + rng.uniform(-5, 5))
    if ride:
        for b in (1, 3):
            if b < beats:
                hit(t0 + b, 'LF', HHP, 60)


def blast(t0, rot=0, base=110, feet=True, hands=True, cyms=(CR, CHINA, CR2)):
    ms = {(s + rot) % 16: k for k, s in enumerate(MOT)}
    if hands:
        for s in range(16):
            t = t0 + s / 4
            if s in ms:
                k = ms[s]
                hit(t, 'RH', cyms[k % len(cyms)], base * MACC[k] + 10 + rng.uniform(-5, 5))
                hit(t, 'LH', SN, base * MACC[k] + 8 + rng.uniform(-5, 5))
            elif s % 2 == 0:
                hit(t, 'RH', RIDE, 70 + rng.uniform(-6, 6))
            elif rng.random() < 0.3:
                hit(t, 'LH', SN, rng.uniform(25, 40))
    if feet:
        for s in range(16):
            hit(t0 + s / 4, 'RF' if s % 2 == 0 else 'LF', K if s % 2 == 0 else K2,
                (95 if s % 4 == 0 else 74) + rng.uniform(-5, 5))


# ================================================================ A: intro (bars 0-3)
for q in range(16):
    hit(q, 'LF', HHP, 48 + (10 if q % 2 else 0))
motif_bar(0, O4, 70, ghost_p=0.0, crash=False, kick_idx=(0,))
motif_bar(4, O4, 76, ghost_p=0.25, crash=False)
motif_bar(8, O1, 82, ghost_p=0.35, crash=False)
motif_bar(12, O1, 86, ghost_p=0.3, crash=False, upto=2)
travel(14, 2, 4, 'RL', TOMS, 60, 102, split=True)

# ================================================================ B: groove (bars 4-11)
for i in range(8):
    t0 = 16 + 4 * i
    inten = 0.2 + 0.05 * i
    ride = i >= 4
    crash = i in (0, 4)
    if i == 3:
        groove(t0, inten, beats=3, ride=ride, crash=crash, motif=True)
        travel(t0 + 3, 1, 4, 'RL', [SN, SN, 50, 48], 70, 100)
    elif i == 7:
        groove(t0, inten, beats=2, ride=ride, motif=True)
        travel(t0 + 2, 2, 6, 'RLRLRK', [SN, 50, 48, 47, 43, 41], 70, 112, accent_every=6)
    else:
        groove(t0, inten, ride=ride, crash=crash, motif=(i % 2 == 0))

# ================================================================ C: development (bars 12-19)
t = 48
motif_bar(t, O2, 95, ghost_p=0.4); t += 4
motif_bar(t, O2, 92, ghost_p=0.4, rot=2, crash=False); t += 4
travel(t, 4, 4, 'RLRRLRLL', [SN, 50, 48, 47, 45, 43, 41, 43], 72, 104, accent_every=4)
feet_q(t, 4, 62); feet_q(t, 4, 55, HHP, 'LF', 2.0, 1.0); t += 4
motif_bar(t, O4, 100, ghost_p=0.3, per=6); t += 4
motif_bar(t, O1, 95, ghost_p=0.45, rot=3); t += 4
travel(t, 4, 4, 'RLK', [50, 48, 47, 45, 43, 41], 78, 108, accent_every=3, split=True)
feet_q(t, 4, 52, HHP, 'LF', 1.0); t += 4
motif_bar(t, O6, 105, ghost_p=0.35); t += 4
motif_bar(t, O1, 95, ghost_p=0.3, upto=2, crash=False)
travel(t + 2, 2, 6, 'RL', TOMS, 80, 115, split=True)
hit(t + 2, 'RF', K, 90); hit(t + 3, 'RF', K, 95)

# ================================================================ D: soft color (bars 20-25)
for i in range(6):
    t0 = 80 + 4 * i
    lvl = max(0.0, (i - 2) / 3.0)
    rot = 2 if i == 4 else 0
    rs = {(s + rot) % 16: k for k, s in enumerate(MOT)}
    upto = 8 if i == 5 else 16
    for s in range(upto):
        tt = t0 + s / 4
        if s in rs:
            hit(tt, 'RH', BELL if i % 2 == 0 else COW,
                56 + 28 * lvl + 14 * MACC[rs[s]] + rng.uniform(-4, 4))
        elif s == 8:
            hit(tt, 'LH', SS, 68 + 20 * lvl)
        elif rng.random() < 0.35 + 0.4 * lvl:
            n = rng.choice([SN, SN, BONGO_HI, BONGO_LO])
            v = (rng.uniform(22, 36) + 30 * lvl) if n == SN else rng.uniform(45, 65) + 20 * lvl
            hit(tt, 'LH', n, v)
    feet_q(t0, upto / 4, 40 + 25 * lvl)
    for b in (1, 3):
        if b < upto / 4:
            hit(t0 + b, 'LF', HHP, 55)
    if i == 5:
        travel(t0 + 2, 2, 8, 'RRLL', [SN], 35, 118, curve=1.6)
        hit(t0 + 2, 'RF', K, 55); hit(t0 + 3, 'RF', K, 75)

# ================================================================ E: build (bars 26-33)
t = 104
travel(t, 4, 6, 'RL', TOMS + TOMS[::-1], 78, 104, accent_every=4)
hit(t, 'RF', K, 105); feet_q(t, 4, 85, start=1.0); t += 4
motif_bar(t, O2, 100, ghost_p=0.5); t += 4
travel(t, 4, 4, 'RRLL', [SN, 50, 48, 47, 45, 43, 41, 41], 80, 110, accent_every=4)
feet_q(t, 4, 88); feet_q(t, 4, 60, HHP, 'LF', 2.0, 1.0); t += 4
motif_bar(t, O6, 105, ghost_p=0.35, per=6); t += 4
travel(t, 4, 4, 'RLK', [SN, 50, 48, 45, 43, 41], 85, 115, accent_every=3, split=True)
feet_q(t, 4, 60, HHP, 'LF'); t += 4
motif_bar(t, O1, 108, ghost_p=0.5, rot=1); t += 4
travel(t, 4, 8, 'RL', [SN, SN, 50, 48, 47, 45, 43, 41], 70, 120, curve=2.0)
feet_q(t, 4, 90); t += 4
travel(t, 2, 8, 'RRLL', [SN], 50, 120, curve=1.5)
travel(t + 2, 2, 6, 'RLRLRK', TOMS, 95, 122, accent_every=3)
hit(t, 'RF', K, 90); t += 4

# ================================================================ F: latin color break (bars 34-37)
for i in range(4):
    t0 = 136 + 4 * i
    upto = 8 if i == 3 else 16
    rh = set(MOT) | {0, 4, 8, 12}
    for s in range(upto):
        tt = t0 + s / 4
        if s in rh:
            acc = s in MOT
            hit(tt, 'RH', CR if (s == 0 and i == 0) else COW,
                (104 if acc else 72) + rng.uniform(-5, 5))
        elif rng.random() < 0.55:
            hit(tt, 'LH', rng.choice([TIMB_HI, TIMB_LO, TIMB_HI, SN]), rng.uniform(40, 80))
    for s in ([0, 6, 12] if i == 0 else [6, 12]):
        if s < upto:
            hit(t0 + s / 4, 'RF', K, 92)
    for s in (4, 12):
        if s < upto:
            hit(t0 + s / 4, 'LF', HHP, 60)
    if i == 3:
        travel(t0 + 2, 2, 4, 'RL', [TIMB_HI, TIMB_LO, TIMB_HI, TIMB_LO, 50, 48, 45, 41], 70, 116)
        hit(t0 + 2, 'RF', K, 85); hit(t0 + 3, 'RF', K, 95)

# ================================================================ G: climax (bars 38-45)
t = 152
blast(t, 0, 108); t += 4
blast(t, 0, 110, cyms=(CHINA, CR, CHINA)); t += 4
blast(t, hands=False); travel(t, 4, 6, 'RL', TOMS + [SN], 90, 116, accent_every=3); t += 4
motif_bar(t, O4, 112, ghost_p=0.3); t += 4
blast(t, 2, 112); hit(t, 'RH', CR, 118); t += 4
travel(t, 4, 6, 'RLRLKF', TOMS + TOMS[::-1][1:], 92, 120, accent_every=6); t += 4
motif_bar(t, O1, 80, ghost_p=0.6); t += 4                 # pull back: tension
travel(t, 4, 8, 'RL', [SN, SN, 50, 48, 47, 45, 43, 41], 58, 125, curve=1.8, accent_every=8)
feet_q(t, 4, 95); t += 4

# ================================================================ H: return and ending (bars 46-50)
motif_bar(t, O1, 115, ghost_p=0.4); t += 4
motif_bar(t, O2, 115, ghost_p=0.45); t += 4
motif_bar(t, O4, 118, ghost_p=0.3, per=6); t += 4
travel(t, 4, 6, 'RLRLKF', TOMS + TOMS[::-1][1:], 95, 122, accent_every=6)
hit(t, 'RH', CR, 120); t += 4
travel(t, 3, 8, 'RRLL', [SN], 40, 120, curve=1.5)
feet_q(t, 3, 55, HHP, 'LF')
travel(t + 3, 1, 4, 'RL', [50, 47, 43, 41], 112, 127)
hit(t + 3, 'RF', K, 110); hit(t + 3.5, 'RF', K, 118)
t += 4
END = t                                   # beat 204: the final hit
hit(END, 'RH', CR, 127, 4.0)
hit(END, 'LH', CR2, 127, 4.0)
hit(END, 'RF', K, 127, 2.0)
hit(END, 'LF', K2, 120, 2.0)

# ================================================================ playability cleanup
# Keep each limb monophonic. If two strokes on one limb are closer than 0.06
# beat, keep only the louder one.
EV.sort(key=lambda e: (e[1], e[0], -e[3]))
clean, lastidx = [], {}
for e in EV:
    l = e[1]
    if l in lastidx and e[0] - clean[lastidx[l]][0] < 0.06:
        if e[3] > clean[lastidx[l]][3]:
            clean[lastidx[l]] = e
        continue
    lastidx[l] = len(clean)
    clean.append(e)

# ================================================================ humanize the timing
# Accents push ahead, ghost notes lay back and the kick sits a touch early.
# The final hit is left exact.
for e in clean:
    tb, l, n, v, d = e
    if tb >= END:
        continue
    off = rng.gauss(0, 0.012 if v < 50 else 0.007)
    if v >= 100:
        off -= 0.006
    if v < 45:
        off += 0.006
    if l == 'RF':
        off -= 0.003
    e[0] = max(0.0, tb + off)

# ================================================================ tempo map
PTS = [(0, 96), (16, 102), (48, 106), (80, 98), (104, 104), (136, 110),
       (152, 112), (184, 114), (200, 112), (204, 104)]


def bpm_raw(b):
    b = min(b, PTS[-1][0])
    for (b0, v0), (b1, v1) in zip(PTS, PTS[1:]):
        if b0 <= b <= b1:
            base = v0 + (v1 - v0) * (b - b0) / (b1 - b0)
            break
    p = (b % 16) / 16.0
    mod = 1 + 0.03 * max(0.0, (p - 0.75) / 0.25)    # rush into the phrase's fill
    if p < 0.0625:
        mod -= 0.008                                  # then settle on the downbeat
    mod += 0.01 * math.sin(b * 0.37)                  # slow breathing of the pulse
    return base * mod


HALF = [bpm_raw(k * 0.5) for k in range(int(END * 2) + 12)]
secs = sum(0.5 * 60.0 / HALF[k] for k in range(int(END * 2)))
factor = secs / 117.5                                 # final hit lands at ~117.5 s

# ================================================================ write the MIDI file
TPB = 480
msgs = []
for k, bp in enumerate(HALF):
    msgs.append((k * TPB // 2, 0, mido.MetaMessage(
        'set_tempo', tempo=int(round(60e6 / (bp * factor))))))
for tb, l, n, v, d in clean:
    on = int(round(tb * TPB))
    off = max(on + 1, int(round((tb + d) * TPB)))
    msgs.append((on, 2, mido.Message('note_on', channel=9, note=n, velocity=v)))
    msgs.append((off, 1, mido.Message('note_off', channel=9, note=n, velocity=0)))
msgs.sort(key=lambda m: (m[0], m[1], getattr(m[2], 'note', 0)))

mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
tr = mido.MidiTrack()
mid.tracks.append(tr)
tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
tr.append(mido.Message('program_change', channel=9, program=0, time=0))
tr.append(mido.Message('control_change', channel=9, control=7, value=115, time=0))
now = 0
for tick, _, m in msgs:
    tr.append(m.copy(time=tick - now))
    now = tick
tr.append(mido.MetaMessage('end_of_track', time=TPB))
mid.save('solo.mid')
