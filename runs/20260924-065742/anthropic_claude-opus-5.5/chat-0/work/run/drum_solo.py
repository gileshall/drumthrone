#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

Tempo is 100 BPM in 4/4, so 50 bars last exactly 120 seconds.

Feel:
  * 16th notes are swung at a 58/42 split.
  * Hats and ride sit slightly ahead of the beat.
  * Backbeats on beats 2 and 4 lay back about 9 ms.
  * Hand percussion lays back slightly.
  * The climax pushes ahead of the beat; the release after it lays back.

Motif A is the cell 0-3-6-10-12 in 16ths. The piece states it, displaces it,
orchestrates it, plays it as a hemiola, uses it for stop-time stabs, and
restates it at the end.

Every note is assigned to a limb: R, L, RF or LF. A final pass enforces a
minimum re-strike gap per limb, so no instant ever has more than two hands
and two feet.

The random generator has a fixed seed, so the output is identical on every run.
"""
import bisect
import random

import mido

BPM = 100
PPQ = 480
BEAT_MS = 60000.0 / BPM
SWING = 0.58
OUT = "solo.mid"

rng = random.Random(1964)
EV = []  # (time_in_beats, note, velocity, limb)

# ---------------------------------------------------------------- GM notes
KICK, KICK2 = 36, 35
SN, STICK = 38, 37
HHC, HHP, HHO = 42, 44, 46
CR1, CR2, CHINA, SPLASH = 49, 57, 52, 55
RIDE, BELL = 51, 53
T1, T2, T3, T4, F1, F2 = 50, 48, 47, 45, 43, 41
TOMS = [T1, T2, T3, T4, F1, F2]
COWBELL, VIBRA, TRI_OPEN = 56, 58, 81
CONGA_MUTE, CONGA_OPEN, CONGA_LOW = 62, 63, 64
TIMB_HI, TIMB_LO, WOOD_HI = 65, 66, 76

MOTIF = [(0, 1.0), (3, 0.8), (6, 0.95), (10, 0.75), (12, 0.9)]
MPOS = [p for p, _ in MOTIF]


# ---------------------------------------------------------------- helpers
def tpos(bar, p, straight=False):
    """Bar number plus position in 16ths -> time in beats (swung unless straight)."""
    if straight:
        return bar * 4 + p / 4.0
    e = int(p // 2)
    x = p - 2 * e
    s = 2 * SWING
    y = x * s if x < 1 else s + (x - 1) * (2 - s)
    return bar * 4 + (2 * e + y) / 4.0


def H(bar, p, note, vel, limb, straight=False):
    EV.append((tpos(bar, p, straight), note, float(vel), limb))


def par(p):
    return 'R' if int(round(p)) % 2 == 0 else 'L'


def flam(bar, p, note, vel, main='R', straight=False):
    t = tpos(bar, p, straight)
    other = 'L' if main == 'R' else 'R'
    EV.append((t, note, float(vel), main))
    EV.append((t - 20.0 / BEAT_MS, note, vel * 0.4, other))


def motif(bar, voices, base, span, shift=0, limbs=None, straight=False, kick=None):
    if isinstance(voices, int):
        voices = [voices] * len(MOTIF)
    for i, (p, a) in enumerate(MOTIF):
        pp = p + shift
        lb = limbs[i] if limbs else par(pp)
        H(bar, pp, voices[i], base + span * a, lb, straight)
        if kick:
            H(bar, pp, kick[0], kick[1] * (0.8 + 0.2 * a), 'RF', straight)


def ghosts(bar, positions, vel=30):
    for p in positions:
        H(bar, p, SN, vel, 'L')


def roll(bar, p0, n, v0, v1, note=SN, first='R'):
    """Straight single-stroke 32nd roll with a crescendo from v0 to v1."""
    other = 'L' if first == 'R' else 'R'
    for j in range(n):
        v = v0 + (v1 - v0) * (j / max(1, n - 1))
        H(bar, p0 + j * 0.5, note, v, first if j % 2 == 0 else other, True)


def groove(bar, cym='hh', ghost=(7, 9, 15), kick=(0, 3, 6, 10), open_hat=False,
           start=0, stop=16, lf=False, snare=(4, 12)):
    for p in range(start, stop):
        if cym == 'hh':
            if open_hat and p == 14:
                H(bar, p, HHO, 88, 'R')
            elif open_hat and p == 15:
                pass
            else:
                v = 92 if p % 4 == 0 else (74 if p % 2 == 0 else 46)
                H(bar, p, HHC, v, 'R')
        else:
            if p % 2 == 0:
                if p in (6, 10):
                    H(bar, p, BELL, 88, 'R')
                else:
                    H(bar, p, RIDE, 80 if p % 4 == 0 else 66, 'R')
            elif p in (7, 15):
                H(bar, p, RIDE, 44, 'R')
        if p in snare:
            H(bar, p, SN, 108, 'L')
        elif p in ghost:
            H(bar, p, SN, 30, 'L')
        if p in kick:
            H(bar, p, KICK, 96 if p == 0 else 84, 'RF')
        if lf and p in (4, 12):
            H(bar, p, HHP, 48, 'LF')


def crash_in(bar, note=CR1, vel=112, kick_vel=108):
    H(bar, 0, note, vel, 'R')
    H(bar, 0, KICK2, kick_vel, 'RF')


# ================================================================ THE SOLO
# ---- Intro (bars 0-3): state motif A on the toms, softly
motif(0, [F2, F1, F2, T4, F2], 52, 28)
H(0, 0, KICK, 70, 'RF')
for p in (4, 12):
    H(0, p, HHP, 50, 'LF')

H(1, 8, T2, 70, 'R')
H(1, 11, T3, 65, 'L')
H(1, 14, T4, 76, 'R')
H(1, 14, KICK, 60, 'RF')
for p in (4, 12):
    H(1, p, HHP, 50, 'LF')

motif(2, [F2, F1, F2, T4, F2], 58, 30, limbs=['R'] * 5)
ghosts(2, [2, 5, 7, 9, 11, 14, 15], 28)
H(2, 0, KICK, 72, 'RF')
H(2, 6, KICK, 66, 'RF')
for p in (4, 12):
    H(2, p, HHP, 50, 'LF')

motif(3, [T2, T3, T4, F1, F2], 64, 30, kick=(KICK, 78))
roll(3, 13, 6, 50, 96)
H(3, 4, HHP, 50, 'LF')

# ---- Groove (bars 4-11): hats, then ride; kick carries the motif
crash_in(4)
groove(4)
groove(5, ghost=(2, 7, 9, 14), open_hat=True)
groove(6, kick=(0, 3, 6, 10, 11))
groove(7, stop=12)
H(7, 12, T2, 88, 'R')
H(7, 13, T2, 72, 'L')
H(7, 14, T4, 98, 'R')
H(7, 15, F2, 92, 'L')
H(7, 14, KICK, 90, 'RF')

crash_in(8, CR2)
groove(8, cym='ride', lf=True)
groove(9, cym='ride', lf=True, ghost=(2, 7, 11, 15))
groove(10, cym='ride', lf=True, kick=(0, 3, 8, 10, 11), ghost=(5, 9, 15))
groove(11, cym='ride', lf=True, stop=8)
fill_notes = [T1, T1, T2, T2, T3, T4, F1, F2]
for i, p in enumerate(range(8, 16)):
    acc = p in (8, 11, 14)
    H(11, p, fill_notes[i], 102 if acc else 64 + i * 2, par(p))
    if acc:
        H(11, p, KICK, 92, 'RF')

# ---- Development (bars 12-19): displaced motif, then a hemiola, then stabs
crash_in(12)
groove(12, stop=8)
motif(12, [T2, T3, T4, F1, F2], 75, 35, shift=8, kick=(KICK, 92))
ghosts(12, [9, 13, 15])
ghosts(13, [1, 3, 5])
groove(13, start=6)

groove(14, stop=6)
motif(14, [T1, T2, T3, T4, F2], 78, 35, shift=6, kick=(KICK, 92))
ghosts(14, [7, 11, 13, 15])
ghosts(15, [1, 3])
groove(15, start=4, stop=12)
roll(15, 12, 8, 55, 105)
H(15, 12, KICK, 80, 'RF', True)

# 3-over-4 linear hemiola (R tom, L ghost, kick) against a hi-hat foot pulse
for n in range(48):
    cell, k = divmod(n, 3)
    ramp = n / 47.0
    if k == 0:
        if n == 0:
            H(16, 0, CR1, 112, 'R')
        else:
            H(16, n, TOMS[cell % 6], 72 + 40 * ramp, 'R')
    elif k == 1:
        H(16, n, SN, 38 + 30 * ramp, 'L')
    else:
        H(16, n, KICK, 70 + 35 * ramp, 'RF')
    if n % 4 == 0:
        H(16, n, HHP, 55, 'LF')
H(16, 0, KICK2, 105, 'RF')

# Bar 19: motif as unison stabs, a roll, then release into the Latin section
for i, (p, a) in enumerate(MOTIF):
    H(19, p, [CR1, CR2, CR1, CHINA, CR2][i], 108 + 12 * a, 'R')
    H(19, p, SN, 105 + 12 * a, 'L')
    H(19, p, KICK2, 108 + 12 * a, 'RF')
roll(19, 13, 6, 60, 112)

# ---- Latin contrast (bars 20-27): cowbell, timbales, congas; quieter
crash_in(20, CR2, 112, 110)
TUMBAO = {0: (CONGA_MUTE, 44), 4: (CONGA_MUTE, 76), 6: (CONGA_OPEN, 86),
          7: (CONGA_OPEN, 78), 8: (CONGA_MUTE, 42), 12: (CONGA_MUTE, 72),
          14: (CONGA_LOW, 88), 15: (CONGA_LOW, 80)}
for bar in range(20, 27):
    for p in range(16):
        if bar < 24:
            if p in MPOS:
                H(bar, p, COWBELL, 96, 'R')
            elif p % 2 == 0:
                H(bar, p, COWBELL, 58, 'R')
        else:
            if p in MPOS:
                note = TIMB_LO if (bar % 2 == 1 and p in (10, 12)) else TIMB_HI
                H(bar, p, note, 96, 'R')
            elif p % 2 == 0:
                H(bar, p, WOOD_HI, 56, 'R')
    for p, (nt, v) in TUMBAO.items():
        H(bar, p, nt, v, 'L')
    if bar == 26:
        for p in MPOS:
            H(bar, p, CONGA_OPEN, 98, 'L')
    H(bar, 6, KICK, 70, 'RF')
    H(bar, 12, KICK, 76, 'RF')
for bar in range(20, 28):
    for p in (0, 4, 8, 12):
        if not (bar == 20 and p == 0):
            H(bar, p, HHP, 40, 'LF')
H(23, 14, VIBRA, 100, 'R')
H(24, 0, TRI_OPEN, 82, 'L')

# Bar 27: timbale fill with 3-3-2 accents, ending on a splash stop
for p in range(12):
    acc = p in (0, 3, 6, 8, 11)
    note = TIMB_HI if par(p) == 'R' else TIMB_LO
    H(27, p, note, (98 if acc else 50) + p * 1.5, par(p))
    if acc:
        H(27, p, KICK, 80, 'RF')
for j in range(6):
    H(27, 12 + j * 0.5, TIMB_HI if j % 2 == 0 else TIMB_LO, 60 + j * 8,
      'R' if j % 2 == 0 else 'L', True)
H(27, 15, SPLASH, 115, 'R', True)
H(27, 15, TIMB_HI, 112, 'L', True)
H(27, 15, KICK2, 110, 'RF', True)

# ---- Build (bars 28-35): pp snare 16ths with motif accents, crescendo
for bar in range(28, 34):
    g = (bar - 28) / 7.0
    if bar == 32:
        crash_in(32, CR1, 105, 100)
    for p in range(16):
        lb = par(p)
        if p in MPOS:
            i = MPOS.index(p)
            a = MOTIF[i][1]
            v = (62 + 50 * g) * (0.85 + 0.15 * a)
            note = SN if bar < 30 else [T2, T4, T3, F1, F2][i]
            H(bar, p, note, v, lb)
            if bar >= 32:
                H(bar, p, KICK2, 80 + 30 * g, 'RF')
        else:
            H(bar, p, SN, 26 + 36 * g, lb)
            if bar >= 32 and p % 4 == 1:
                H(bar, p + 0.5, SN, 24 + 36 * g, lb)   # diddle
    for p in (0, 4, 8, 12):
        H(bar, p, KICK, 55 + 40 * g, 'RF')
    if bar < 32:
        for p in (4, 12):
            H(bar, p, HHP, 45, 'LF')
    else:
        for p in (2, 6, 10, 14):
            H(bar, p, HHP, 58, 'LF')

# Bars 34-35: continuous 32nd roll; bar 34 accents motif A, bar 35 the hemiola
HEMI = (0, 3, 6, 9, 12, 15)
for bar in (34, 35):
    for j in range(32):
        p = j * 0.5
        lb = 'R' if j % 2 == 0 else 'L'
        prog = ((bar - 34) * 32 + j) / 63.0
        base = 48 + 52 * prog
        if bar == 34 and p in MPOS:
            i = MPOS.index(p)
            H(bar, p, [T1, T2, T3, T4, F1][i], min(127, base + 30), lb, True)
            H(bar, p, KICK, 90, 'RF', True)
        elif bar == 35 and p in HEMI:
            k = int(p // 3)
            H(bar, p, TOMS[k], min(127, base + 28), lb, True)
            H(bar, p, KICK, 100, 'RF', True)
        else:
            H(bar, p, SN, base * 0.75, lb, True)
    for p in (2, 6, 10, 14):
        H(bar, p, HHP, 60, 'LF', True)
H(34, 4, KICK, 80, 'RF', True)
H(34, 8, KICK, 80, 'RF', True)

# ---- Climax (bars 36-43)
# Bars 36-37: double-kick 16ths under crash-and-snare motif stabs
for bar in (36, 37):
    for p in range(16):
        kv = (90 if p % 2 == 0 else 76) + (15 if p in MPOS else 0)
        H(bar, p, KICK, kv, 'RF' if p % 2 == 0 else 'LF')
        if p in MPOS:
            i = MPOS.index(p)
            a = MOTIF[i][1]
            H(bar, p, [CR1, CHINA, CR2, CHINA, CR1][i], 104 + 16 * a, 'R')
            H(bar, p, SN, 104 + 16 * a, 'L')
        elif p % 2 == 0:
            if not (bar == 37 and p == 14):
                H(bar, p, BELL, 78, 'R')
        elif p in (9, 15) and not (bar == 37 and p == 15):
            H(bar, p, SN, 40, 'L')
flam(37, 14, F1, 110, 'R')
H(37, 15, F2, 105, 'L')

# Bars 38-39: the hemiola returns at full volume
for n in range(32):
    cell, k = divmod(n, 3)
    if n == 30:
        flam(38, 30, SN, 122, 'R')
        continue
    if k == 0:
        if cell % 4 == 0:
            H(38, n, CR2, 115, 'R')
        else:
            H(38, n, TOMS[cell % 6], 108, 'R')
    elif k == 1:
        H(38, n, SN, 96, 'L')
    else:
        H(38, n, KICK, 100, 'RF')
    if n % 4 == 0:
        H(38, n, HHP, 70, 'LF')

# Bars 40-41: stop-time motif stabs with space, then a sextuplet tom run
for bar in (40, 41):
    for p in range(0, 16, 4):
        H(bar, p, HHP, 62, 'LF')
    stabs = MOTIF if bar == 40 else MOTIF[:3]
    for i, (p, a) in enumerate(stabs):
        H(bar, p, [CR1, CR2, CHINA, CR2, CR1][i], 108 + 16 * a, 'R')
        H(bar, p, SN, 108 + 12 * a, 'L')
        H(bar, p, KICK2, 112 + 12 * a, 'RF')
seq = [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2]
for j in range(12):
    p = 8 + j * (4 / 6.0)
    H(41, p, seq[j], 72 + j * 4, 'R' if j % 2 == 0 else 'L', True)
    if j % 6 == 0:
        H(41, p, KICK, 95, 'RF', True)

# Bar 42: descending sextuplets with crash-and-kick on each beat
for beat in range(3):
    for j in range(6):
        p = beat * 4 + j * (4 / 6.0)
        if j == 0:
            H(42, p, CR2 if beat == 1 else CR1, 118, 'R', True)
            H(42, p, KICK2, 118, 'RF', True)
        else:
            H(42, p, TOMS[j], 88 + j * 2, 'R' if j % 2 == 0 else 'L', True)
    H(42, beat * 4 + 2, KICK, 90, 'RF', True)
for p in (4, 12):
    H(42, p, HHP, 60, 'LF', True)
H(42, 12, SN, 112, 'R')
H(42, 12, KICK, 100, 'RF')
H(42, 13, SN, 40, 'L')
H(42, 14, F2, 110, 'R')
H(42, 14, KICK, 100, 'RF')
H(42, 15, F2, 100, 'L')

# Bar 43: maximum tension; 32nd roll, hemiola cymbal accents, double kick
for j in range(32):
    p = j * 0.5
    lb = 'R' if j % 2 == 0 else 'L'
    if p in HEMI:
        k = HEMI.index(p)
        H(43, p, [CR2, CR1, CHINA, CR2, CR1, SPLASH][k], 118, 'R', True)
    else:
        H(43, p, SN, 70 + 50 * (j / 31.0), lb, True)
for p in range(16):
    H(43, p, KICK, 85 + (20 if p in HEMI else 0),
      'RF' if p % 2 == 0 else 'LF', True)


# ---- Release (bars 44-47): half-time ride, side stick, lots of space
def ride_half(bar, start=0, stop=16, bells=()):
    for p in range(start, stop, 2):
        if p in bells:
            H(bar, p, BELL, 84, 'R')
        else:
            H(bar, p, RIDE, 64 if p % 4 == 0 else 52, 'R')
    if start <= 8 < stop:
        H(bar, 8, STICK, 74, 'L')
    if stop == 16:
        H(bar, 13, SN, 22, 'L')
        H(bar, 15, SN, 28, 'L')
    for p in (4, 12):
        if start <= p < stop:
            H(bar, p, HHP, 40, 'LF')


H(44, 0, CR2, 112, 'R')
H(44, 0, KICK2, 110, 'RF')
ride_half(44, start=4)
H(44, 10, KICK, 58, 'RF')

ride_half(45)
H(45, 0, KICK, 70, 'RF')
H(45, 6, KICK, 58, 'RF')

ride_half(46, bells=MPOS)
H(46, 3, BELL, 80, 'R')
for p in MPOS:
    H(46, p, KICK, 72, 'RF')

ride_half(47, stop=8)
H(47, 0, KICK, 70, 'RF')
f47 = [T2, SN, T2, T3, T4, SN, F1, F2]
for i, p in enumerate(range(8, 16)):
    acc = p in (8, 11, 14)
    H(47, p, f47[i], 68 + i * 5 + (20 if acc else 0), par(p))
    if acc:
        H(47, p, KICK, 90, 'RF')

# ---- Finale (bar 48): the full motif fortissimo, a roll, then the final hit
for i, (p, a) in enumerate(MOTIF):
    H(48, p, [CR1, CR2, CR1, CHINA, CR2][i], 110 + 15 * a, 'R')
    H(48, p, SN, 108 + 12 * a, 'L')
    H(48, p, KICK2, 110 + 12 * a, 'RF')
for idx, p in enumerate([1, 2, 4, 5, 7, 8, 9, 11]):
    H(48, p, TOMS[idx % 6], 78 + idx * 2, par(p))
roll(48, 13, 6, 85, 120)
H(48, 14, KICK, 100, 'RF', True)

H(49, 0, CR1, 127, 'R')
H(49, 0, CR2, 127, 'L')
H(49, 0, KICK2, 127, 'RF')


# ================================================================ RENDER
def feel_ms(note, vel, t):
    bar = int(t // 4)
    frac = t % 4
    off = 0.0
    if note in (HHC, HHO, RIDE, BELL, 59, COWBELL, WOOD_HI, 75):
        off -= 6.0                                  # cymbals push
    elif note in (SN, 40, STICK):
        if vel >= 80 and (abs(frac - 1.0) < 1e-6 or abs(frac - 3.0) < 1e-6):
            off += 9.0                              # backbeat lays back
        elif vel < 50:
            off += 2.0
    elif note in (60, 61, CONGA_MUTE, CONGA_OPEN, CONGA_LOW, TIMB_HI, TIMB_LO):
        off += 5.0
    elif note in (KICK, KICK2):
        off -= 1.0
    if 36 <= bar <= 43:
        off -= 4.0                                  # climax pushes
    elif 44 <= bar <= 47:
        off += 4.0                                  # release lays back
    return off


MS_TO_BEAT = BPM / 60000.0
notes = []
for (t, note, vel, limb) in EV:
    j = max(-4.0, min(4.0, rng.gauss(0, 1.8)))
    off = feel_ms(note, vel, t) + j
    tick = max(0, int(round((t + off * MS_TO_BEAT) * PPQ)))
    jv = rng.randint(-2, 2) if vel < 50 else rng.randint(-4, 4)
    v = max(1, min(127, int(round(vel + jv))))
    notes.append((tick, note, v, limb))

# Playability: one strike per limb within a minimum gap (hands 45 ms, feet 90 ms)
GAP = {'R': 36, 'L': 36, 'RF': 72, 'LF': 72}
final = []
for limb in ('R', 'L', 'RF', 'LF'):
    lst = sorted([n for n in notes if n[3] == limb],
                 key=lambda n: (n[0], -n[2], n[1]))
    kept = []
    for n in lst:
        if kept and n[0] - kept[-1][0] < GAP[limb]:
            if n[2] > kept[-1][2] and (len(kept) < 2 or
                                       n[0] - kept[-2][0] >= GAP[limb]):
                kept[-1] = n
        else:
            kept.append(n)
    final.extend(kept)

# Remove duplicates of the same note on the same tick, keeping the louder one
dedup = {}
for n in final:
    key = (n[0], n[1])
    if key not in dedup or n[2] > dedup[key][2]:
        dedup[key] = n
final = sorted(dedup.values(), key=lambda n: (n[0], n[1]))

by_note = {}
for n in final:
    by_note.setdefault(n[1], []).append(n[0])
for k in by_note:
    by_note[k].sort()

msgs = []
for tick, note, v, _ in final:
    lst = by_note[note]
    i = bisect.bisect_right(lst, tick)
    dur = 60
    if i < len(lst):
        dur = min(dur, lst[i] - tick - 1)
    dur = max(1, dur)
    msgs.append((tick, 1, note,
                 mido.Message('note_on', channel=9, note=note, velocity=v)))
    msgs.append((tick + dur, 0, note,
                 mido.Message('note_off', channel=9, note=note, velocity=0)))
msgs.sort(key=lambda m: (m[0], m[1], m[2]))

mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
tr = mido.MidiTrack()
mid.tracks.append(tr)
tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
tr.append(mido.Message('control_change', channel=9, control=7, value=120, time=0))
tr.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
last = 0
for tick, _, _, m in msgs:
    m.time = tick - last
    tr.append(m)
    last = tick
end = 50 * 4 * PPQ  # 50 bars at 100 BPM = 120 s
tr.append(mido.MetaMessage('end_of_track', time=max(0, end - last)))
mid.save(OUT)
