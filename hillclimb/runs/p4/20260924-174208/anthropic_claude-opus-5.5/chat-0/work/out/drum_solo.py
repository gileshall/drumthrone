#!/usr/bin/env python3
"""
drum_solo.py - generates solo.mid, a two-minute General MIDI drum solo on channel 10.

Structure (4/4 bars, one tempo curve):
  0-3   Intro        motif A stated on toms, answered by motif B, first fill
  4-11  Groove       swung 16th groove with ghost notes, motif fragment, fills
  12-19 Development  motif moved to kick/snare, displaced, augmented, 32nd run
  20-23 Breakdown    clave from motif A's accents on cowbell/agogo, snare swell
  24-31 Build        linear patterns, sextuplet runs around the kit, flam fill
  32-39 Shuffle      half-time triplet shuffle, laid back, motif in triplets
  40-47 Climax       double bass, motif fortissimo, call and response, stop-time
  48-51 Recap        motif A and B return, final roll with a ritard, last hit

The output is deterministic because every random choice uses a seeded generator.
"""
import random
import mido

TPB = 480
R = random.Random(1971)      # musical choices (ghost velocities etc.)
J = random.Random(4242)      # tiny timing variation at render time
EV = []                      # [beat, note, vel, limb, dur_beats]

# ---------------------------------------------------------------- GM notes
KICK, KICK2 = 36, 35
SN, RIM = 38, 37
HHC, HHP, HHO = 42, 44, 46
CR1, CR2, RIDE, BELL, CHINA, SPL = 49, 57, 51, 53, 52, 55
COW, TIMH, TIML, AGH, AGL = 56, 65, 66, 67, 68
T1, T2, T3, T4, T5, T6 = 50, 48, 47, 45, 43, 41
TOMS = (T1, T2, T3, T4, T5, T6)


def hit(t, n, v, limb, d=0.2):
    EV.append([float(t), int(n), max(1, min(127, int(round(v)))), limb, float(d)])


def g16(bar, p, sw=0.0):
    return bar * 4 + p * 0.25 + (sw * 0.25 if p % 2 else 0.0)


# ---------------------------------------------------------------- motifs
# (position, role, accent level)   roles: S snare, T1..T4 toms, g ghost, K kick
MA = [(0, 'S', 2), (3, 'T1', 1), (4, 'g', 0), (6, 'T2', 2), (8, 'g', 0), (9, 'g', 0),
      (10, 'T3', 2), (12, 'S', 1), (13, 'g', 0), (14, 'T4', 2)]
MB = [(0, 'K', 1), (2, 'T4', 1), (3, 'g', 0), (4, 'S', 1), (7, 'g', 0), (8, 'K', 1),
      (10, 'T3', 1), (11, 'T4', 1), (12, 'S', 2), (15, 'g', 0)]
# motif A in a triplet grid (12 per bar)
MAT = [(0, 'S', 2), (2, 'T1', 1), (4, 'T2', 2), (6, 'g', 0), (7, 'g', 0),
       (8, 'T3', 2), (9, 'S', 1), (10, 'g', 0), (11, 'T4', 2)]

MAP1 = {'S': SN, 'T1': T1, 'T2': T3, 'T3': T5, 'T4': T6}
MAP2 = {'S': SN, 'T1': T2, 'T2': T4, 'T3': T6, 'T4': T5}
MAPG = {'S': SN, 'T1': SN, 'T2': KICK, 'T3': KICK, 'T4': SN}
MAPF = {'S': SN, 'T1': T3, 'T2': T5, 'T3': T6, 'T4': T6}


def motif(bar, m, mp, dyn, shift=0, lo=0, hi=99, kick=True, sw=0.0,
          crash=(), grid=0.25, aug=1):
    for p, role, acc in m:
        if p < lo or p >= hi:
            continue
        q = p * aug + shift
        t = bar * 4 + q * grid + (sw * grid if (grid == 0.25 and q % 2) else 0.0)
        if role == 'g':
            hit(t, SN, 30 + R.randint(0, 10), 'A', 0.1)
            continue
        note = KICK if role == 'K' else mp[role]
        vel = dyn + (18 if acc == 2 else 4 if acc == 1 else -30)
        hit(t, note, vel, 'K' if note == KICK else 'A')
        if acc == 2 and kick and note != KICK:
            hit(t, KICK, vel - 8, 'K')
        if acc == 2 and p in crash:
            hit(t, CR1 if (p // 4) % 2 == 0 else CR2, vel, 'A', 1.5)


# ---------------------------------------------------------------- building blocks
def land(t, v=115, cym=CR1, kick=True, dur=2.0):
    hit(t, cym, v, 'A', dur)
    if kick:
        hit(t, KICK, v + 4, 'K')


GHOSTS = [(3, 7, 9, 15), (1, 7, 11, 13), (3, 9, 14, 15), (7, 9, 13, 15)]
KICKS = [(0, 6, 10), (0, 3, 8, 10), (0, 7, 10, 14), (0, 6, 8, 11)]


def groove(bar, dyn=86, ride=False, kick=0, ghost=0, open_at=(), sw=0.1, end=16, pedal=None):
    if pedal is None:
        pedal = ride
    skip = {o + 1 for o in open_at}
    for p in range(end):
        t = g16(bar, p, sw)
        if ride:
            if p % 2 == 0 or p == 7:
                vel = dyn - 4 if p % 4 == 0 else (dyn - 16 if p % 2 == 0 else dyn - 24)
                hit(t, BELL if (p == 0 and bar % 2 == 0) else RIDE, vel, 'R', 0.5)
        elif p not in skip:
            if p in open_at:
                hit(t, HHO, dyn - 4, 'R', 0.4)
                hit(bar * 4 + (p + 2) * 0.25, HHP, 60, 'H', 0.1)
            else:
                vel = dyn - 6 if p % 4 == 0 else (dyn - 18 if p % 2 == 0 else dyn - 32)
                hit(t, HHC, vel + R.randint(-2, 2), 'R', 0.1)
        if p in (4, 12):
            hit(t, SN, dyn + 26, 'L')
        elif p in GHOSTS[ghost]:
            hit(t, SN, R.randint(26, 40), 'L', 0.1)
        if p in KICKS[kick]:
            hit(t, KICK, dyn + (6 if p % 4 == 0 else -6), 'K')
        if pedal and p in (4, 12):
            hit(t, HHP, 52, 'H', 0.1)


def shuffle(bar, dyn=84, ride=False, kick=(0, 5, 8), end=12):
    for p in range(end):
        t = bar * 4 + p / 3.0
        s = p % 3
        if s in (0, 2):
            vel = (dyn if s == 0 else dyn - 18) + (4 if p % 6 == 0 else 0)
            hit(t, RIDE if ride else HHC, vel, 'R', 0.3)
        if p == 6:
            hit(t, SN, dyn + 26, 'L')
        elif s == 1:
            hit(t, SN, R.randint(24, 38), 'L', 0.1)
        if p in kick:
            hit(t, KICK, dyn - 2, 'K')
        if ride and p in (3, 9):
            hit(t, HHP, 55, 'H', 0.1)


def run(t0, n, sub, seq, v0, v1, stick='RL', per=2, acc_every=0, acc_amt=14, shape=1.0):
    for i in range(n):
        t = t0 + i * sub
        x = i / max(1, n - 1)
        vel = v0 + (v1 - v0) * (x ** shape)
        if acc_every:
            vel += acc_amt if i % acc_every == 0 else -6
        limb = stick[i % len(stick)]
        if limb == 'K':
            hit(t, KICK, vel - 6, 'K')
            continue
        hit(t, seq[(i // per) % len(seq)], vel, limb, 0.15)


def roll(t0, dur, note, v0, v1, sub=0.125, shape=1.4, stick='RRLL'):
    n = int(round(dur / sub))
    for i in range(n):
        x = i / max(1, n - 1)
        vel = v0 + (v1 - v0) * (x ** shape)
        if stick == 'RRLL' and i % 2 == 1:
            vel *= 0.92
        hit(t0 + i * sub, note, vel, stick[i % len(stick)], 0.1)


def paradiddle(t0, n, seq, v0, v1, sub=0.25):
    st = 'RLRRLRLL'
    for i in range(n):
        x = i / max(1, n - 1)
        vel = v0 + (v1 - v0) * x
        limb = st[i % 8]
        acc = (i % 4 == 0)
        d = seq[(i // 2) % len(seq)] if limb == 'R' else (SN if i < n // 2 else seq[-1])
        hit(t0 + i * sub, d, vel + (14 if acc else -18), limb, 0.15)
        if acc:
            hit(t0 + i * sub, KICK, vel, 'K')


def linear(bar, pat, rv, lv, dyn, acc=(), sw=0.0):
    for p, ch in enumerate(pat):
        if ch == '.':
            continue
        t = g16(bar, p, sw)
        a = p in acc
        if ch == 'K':
            hit(t, KICK, dyn + (10 if a else -4), 'K')
            continue
        voices = rv if ch == 'R' else lv
        note = voices[(p // 4) % len(voices)]
        vel = dyn + 22 if a else (dyn - 10 if ch == 'R' else dyn - 42)
        hit(t, note, vel, ch, 0.15)


def flam_fill(bar, seq, v0, v1):
    for p in range(16):
        t = bar * 4 + p * 0.25
        vel = v0 + (v1 - v0) * p / 15.0
        if p % 2 == 0:
            d = seq[(p // 2) % len(seq)]
            hit(t - 0.06, d, vel * 0.45, 'L', 0.1)
            hit(t, d, vel + 10, 'R', 0.2)
            if p % 4 == 0:
                hit(t, KICK, vel, 'K')
        else:
            hit(t, SN, vel * 0.4, 'L', 0.1)


def dbl(t0, n, sub=0.25, v=86):
    for i in range(n):
        hit(t0 + i * sub, KICK, v + (8 if i % 4 == 0 else 0) - (5 if i % 2 else 0), 'F', 0.1)


# ================================================================ THE SOLO
SW = 0.1

# ---- Intro (bars 0-3): state the motif, answer it, first fill
for b in range(4):
    for q in range(4):
        hit(b * 4 + q, HHP, 46 + (8 if q % 2 else 0), 'H', 0.1)
motif(0, MA, MAP1, 76)
motif(1, MB, MAP1, 68)
motif(2, MA, MAP1, 82, hi=12)
run(11, 4, 0.25, [T1, T2, T3, T4], 78, 96, 'RL', per=1)
motif(3, MA, MAP1, 88, hi=7)
run(14, 12, 1 / 6, [T1, T2, T3, T4, T5, T6], 74, 112, 'RLK', per=3, acc_every=3, acc_amt=10)

# ---- Groove (bars 4-11)
land(16, 112)
groove(4, kick=0, ghost=0, sw=SW)
groove(5, kick=1, ghost=1, open_at=(14,), sw=SW)
groove(6, kick=2, ghost=2, sw=SW)
groove(7, kick=0, ghost=3, end=8, sw=SW)
motif(7, MA, MAP1, 88, lo=8, sw=SW)
land(32, 108)
groove(8, dyn=90, kick=0, ghost=3, sw=SW)
groove(9, dyn=90, kick=3, ghost=1, open_at=(6, 14), sw=SW)
groove(10, dyn=92, kick=1, ghost=2, sw=SW)
groove(11, dyn=92, kick=2, ghost=0, end=8, sw=SW)
paradiddle(46, 8, [T1, T2, T3, T5], 82, 108)

# ---- Development (bars 12-19)
land(48, 110)
for p in range(2, 16, 2):
    hit(g16(12, p, SW), HHC, 80 if p % 4 == 0 else 66, 'R', 0.1)
motif(12, MA, MAPG, 86, kick=False, sw=SW)                 # motif as a groove
groove(13, dyn=90, kick=2, ghost=0, open_at=(14,), sw=SW)
land(56, 104)
for q in range(4):
    hit(56 + q, HHP, 54, 'H', 0.1)
motif(14, MA, MAP2, 90, shift=2, hi=14)                    # displaced motif
groove(15, dyn=90, kick=0, ghost=1, end=8, sw=SW)
run(62, 8, 0.25, [TIMH, TIMH, TIML, TIML, T1, T3, T5, T6], 80, 106, 'RL', per=1)
hit(62, KICK, 92, 'K'); hit(63, KICK, 100, 'K')
for b in (16, 17):                                          # augmented motif
    for q in range(4):
        if b == 16 and q == 0:
            continue
        hit(b * 4 + q, BELL if q == 0 else RIDE, 84 if q == 0 else 74, 'R', 0.8)
        if q % 2 == 1:
            hit(b * 4 + q, HHP, 54, 'H', 0.1)
motif(16, MA, MAPF, 82, aug=2, crash=(0,))
groove(18, dyn=88, ride=True, kick=1, ghost=1, sw=SW)
groove(19, dyn=90, ride=True, kick=0, ghost=2, end=8, sw=SW)
run(78, 16, 0.125, [SN, T1, T2, T3, T4, T5, T6, T6], 72, 116, 'RRLL', per=2)
for i in range(4):
    hit(78 + i * 0.5, KICK, 80 + i * 8, 'K')

# ---- Breakdown (bars 20-23): clave built from motif A's accents
land(80, 96)
CLAVE = (0, 3, 6, 10, 12)
for b in (20, 21, 22):
    for p in (0, 10) + ((6,) if b == 22 else ()):
        hit(g16(b, p), KICK, 78, 'K')
    for p in (4, 12):
        hit(g16(b, p), HHP, 60, 'H', 0.1)
for b in (20, 21):
    for p in CLAVE:
        if b == 20:
            hit(g16(b, p, SW), COW, 84 if p == 0 else 72, 'R', 0.3)
        else:
            hit(g16(b, p, SW), AGH if p in (0, 6, 12) else AGL, 86 if p == 0 else 74, 'R', 0.3)
    for p in (4, 12):
        hit(g16(b, p, SW), RIM, 72, 'L', 0.1)
    for p in (2, 7, 9, 14, 15):
        hit(g16(b, p, SW), SN, R.randint(24, 36), 'L', 0.1)
for p in range(16):                                         # bar 22: slow swell
    x = p / 15.0
    hit(g16(22, p, SW), HHC, 50 + 30 * x + (6 if p % 4 == 0 else 0), 'R', 0.1)
    if p % 2 == 1:
        hit(g16(22, p, SW), SN, 28 + 42 * x, 'L', 0.1)
    elif p in (4, 12):
        hit(g16(22, p, SW), SN, 70 + 20 * x, 'L', 0.1)
for q in range(4):
    hit(92 + q, KICK, 50 + q * 16, 'K')
roll(92, 3, SN, 28, 112, shape=1.6)
run(95, 8, 0.125, [T1, T2, T3, T4, T5, T6, T6, T6], 104, 122, 'RL', per=1)

# ---- Build (bars 24-31): linear flow, sextuplets, flams
ACC3 = (0, 3, 6, 9, 12, 15)
land(96, 118)
linear(24, "RLKRLKRLKRLKRLKR", [HHC], [SN], 88, ACC3)
linear(25, "RLKRLKRLKRLKRLKR", [HHC, HHC, T2, T4], [SN, SN, T1, T3], 90, ACC3)
linear(26, "RLLKRLLKRLLKRLKK", [BELL], [SN, SN, T2, T4], 92, (0, 4, 8, 12))
hit(g16(26, 12), SPL, 104, 'A', 1.0)
for b in (25, 26, 27):
    for q in range(4):
        hit(b * 4 + q, HHP, 52, 'H', 0.1)
run(108, 16, 0.25, [T1, T2, T3, T4, T5, T6, T5, T3], 86, 106, 'RL', per=2, acc_every=3, acc_amt=16)
for q in range(4):
    hit(108 + q, KICK, 88 + q * 4, 'K')
land(112, 114)
run(112, 24, 1 / 6, [T1, T2, T3, T4, T5, T6, T5, T4, T3, T2, SN, SN],
    80, 100, 'RLK', per=3, acc_every=3, acc_amt=12)
hit(116, SPL, 100, 'A', 1.0)
run(116, 24, 1 / 6, [T1, T3, T5, T6, T4, T2], 92, 116, 'RLLK', per=4, acc_every=4, acc_amt=14)
roll(120, 2, SN, 48, 104)
hit(120, KICK, 80, 'K'); hit(121, KICK, 88, 'K')
motif(30, MA, MAP1, 100, lo=8, crash=(10, 14))
flam_fill(31, [SN, T1, SN, T2, T3, T4, T5, T6], 82, 116)

# ---- Shuffle (bars 32-39): half-time, triplets, laid back
land(128, 108)
shuffle(32, ride=True, kick=(0, 5, 8))
shuffle(33, ride=True, kick=(0, 8, 11))
shuffle(34, dyn=86, kick=(0, 5, 8, 9))
shuffle(35, end=6, kick=(0, 5))
run(142, 12, 1 / 6, [T1, T2, T3, T4, T5, T6], 78, 108, 'RLL', per=3, acc_every=3)
hit(142, KICK, 90, 'K'); hit(143, KICK, 98, 'K')
land(144, 108)
for q in range(4):
    hit(144 + q, HHP, 56, 'H', 0.1)
motif(36, MAT, MAP1, 90, grid=1 / 3)
motif(37, MAT, MAP2, 96, grid=1 / 3, crash=(0, 8))
shuffle(38, ride=True, dyn=92, kick=(0, 5, 8, 11))
run(156, 12, 1 / 6, [SN, T1, T2, T3, T4, T5], 80, 100, 'RLK', per=3, acc_every=3)
run(158, 8, 0.25, [T1, T2, T3, T4, T5, T6, T6, SN], 100, 120, 'RL', per=1)
for i in range(4):
    hit(158 + i * 0.5, KICK, 96 + i * 6, 'K')

# ---- Climax (bars 40-47)
land(160, 122, kick=False)
dbl(160, 16, 0.25, 86)
for p in range(0, 16, 2):
    hit(g16(40, p), BELL, 98 if p % 4 == 0 else 80, 'R', 0.4)
hit(161, SN, 118, 'L'); hit(163, SN, 120, 'L')
hit(g16(40, 10), T4, 100, 'L'); hit(g16(40, 14), T5, 104, 'L')
motif(41, MA, MAP1, 102, crash=(0, 6, 10, 14))
land(168, 116, kick=False)
dbl(168, 16, 0.25, 86)
run(168, 16, 0.25, [T1, T2, T3, T4, T5, T6, T5, T4], 86, 110, 'RL', per=2, acc_every=3, acc_amt=18)
dbl(172, 16, 0.25, 88)
motif(43, MA, MAP2, 104, kick=False, crash=(0, 10))
# call and response
roll(176, 1, SN, 64, 112)
hit(177, CR1, 120, 'A', 1.2); hit(177, KICK, 120, 'K'); hit(177, T6, 110, 'A')
run(178, 8, 0.125, [T1, T3, T5, T6], 92, 118, 'RL', per=2)
hit(179, CHINA, 118, 'A', 1.0); hit(179, KICK, 118, 'K')
hit(179.5, CHINA, 122, 'A', 1.0); hit(179.5, KICK, 122, 'K'); hit(179.5, SN, 112, 'A')
run(180, 6, 1 / 6, [T1, T2], 96, 112, 'RLK', per=3)
hit(181, CR1, 118, 'A', 1.0); hit(181, KICK, 118, 'K')
hit(181.5, T6, 110, 'A'); hit(181.5, KICK, 108, 'K')
run(182, 6, 1 / 6, [T4, T5], 100, 116, 'RLK', per=3)
hit(183, CHINA, 120, 'A', 1.0); hit(183, KICK, 120, 'K')
hit(183.25, SN, 112, 'A'); hit(183.25, KICK, 110, 'K')
hit(183.5, CR2, 122, 'A', 1.5); hit(183.5, KICK, 122, 'K')
hit(183.75, T6, 108, 'A')
run(184, 16, 0.125, [SN, T1, T2, T3, T4, T5, T6, SN], 96, 118, 'RL', per=2)
dbl(184, 8, 0.25, 90)
run(186, 12, 1 / 6, [T6, T5, T4, T3, T2, T1], 96, 124, 'RLK', per=3, acc_every=3)
# stop-time
hit(188, CR1, 127, 'R', 3.0); hit(188, CR2, 120, 'L', 3.0)
hit(188, KICK, 127, 'K'); hit(188, KICK2, 118, 'H')
hit(189, HHP, 50, 'H', 0.1); hit(190, HHP, 56, 'H', 0.1)
roll(190.5, 1.5, SN, 22, 114, shape=1.5)

# ---- Recap and ending (bars 48-51)
motif(48, MA, MAP1, 106, crash=(0, 6, 10, 14))
motif(49, MB, MAP1, 100, crash=(12,))
motif(50, MA, MAP2, 108, hi=12, crash=(0, 6, 10))
run(203, 8, 0.125, [T1, T2, T3, T4, T5, T6, T6, T6], 100, 122, 'RL', per=1)
roll(204, 3, SN, 54, 120, shape=1.3)
for q in range(3):
    hit(204 + q, KICK, 90 + q * 10, 'K')
run(207, 6, 1 / 6, [T3, T6], 112, 126, 'RL', per=3)
hit(208, CR1, 127, 'R', 4.0); hit(208, CR2, 127, 'L', 4.0)
hit(208, KICK, 127, 'K', 2.0); hit(208, KICK2, 124, 'H', 2.0)


# ================================================================ playability
HANDS, FEET = ('R', 'L'), ('K', 'H')


def resolve(evs):
    evs = sorted(evs, key=lambda e: (round(e[0], 4), 1 if e[3] in 'AF' else 0, -e[2], e[1]))
    last = {'R': -99.0, 'L': -99.0, 'K': -99.0, 'H': -99.0}
    used, notes_at, out = {}, {}, []
    for e in evs:
        t = round(e[0], 4)
        lb = e[3]
        u = used.setdefault(t, set())
        na = notes_at.setdefault(t, set())
        if e[1] in na:
            continue
        if lb == 'A':
            cands = sorted(HANDS, key=lambda h: last[h])
        elif lb == 'F':
            cands = sorted(FEET, key=lambda h: last[h])
        else:
            cands = [lb]
        pick = None
        for h in cands:
            if h in u:
                continue
            mn = 0.1 if h in HANDS else 0.16
            if t - last[h] < mn - 1e-6:
                continue
            pick = h
            break
        if pick is None:
            continue
        u.add(pick)
        na.add(e[1])
        last[pick] = t
        out.append([e[0], e[1], e[2], pick, e[4]])
    return out


# ================================================================ time feel
def interp(kp, x):
    if x <= kp[0][0]:
        return kp[0][1]
    for (x0, y0), (x1, y1) in zip(kp, kp[1:]):
        if x0 <= x <= x1:
            return y1 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return kp[-1][1]


# tempo factor by bar: leans forward in the heat, settles when it relaxes
TEMPO_KP = [(0, 0.97), (4, 1.0), (11, 1.005), (12, 1.015), (16, 1.02), (16.5, 1.0),
            (18, 1.0), (20, 1.02), (21, 0.965), (23, 0.965), (24, 1.0), (31, 1.06),
            (32, 1.04), (33, 0.975), (38, 0.975), (40, 1.04), (47, 1.08), (48, 1.06),
            (51, 1.05), (52, 0.9)]
# placement relative to the grid in ticks: + lays back, - pushes
LEAN_KP = [(0, 0), (20, 0), (20.5, 4), (23.5, 4), (24, -2), (31, -6), (32, 4), (33, 8),
           (38.5, 8), (40, -4), (47, -6), (48, -3), (52, 0)]


def feel(n, v):
    if n in (KICK, KICK2):
        return -4                      # kick sits on top of the beat
    if n in (SN, RIM):
        return 3 + int(4 * max(0, v - 60) / 67)   # snare lays back, more when loud
    if n in TOMS or n in (TIMH, TIML):
        return -2
    if n == HHP:
        return 2
    return 0


TOTAL_BEATS = 208
TAIL = 4.5
S = sum(60.0 / interp(TEMPO_KP, (k + 0.5) / 4) for k in range(TOTAL_BEATS))
BASE = S / 117.0                       # content ends at ~117 s, ring-out to ~120 s


def render():
    evs = resolve(EV)
    notes = []
    for t, n, v, limb, d in evs:
        off = feel(n, v) + interp(LEAN_KP, t / 4.0) + J.randint(-2, 2)
        on = max(0, int(round(t * TPB + off)))
        notes.append([on, n, v, int(d * TPB)])
    notes.sort()
    msgs = []
    nxt = {}
    for on, n, v, dt in reversed(notes):
        off = on + max(20, dt)
        if n in nxt:
            off = min(off, nxt[n] - 1)
        off = max(off, on + 1)
        nxt[n] = on
        msgs.append((on, 2, n, mido.Message('note_on', channel=9, note=n, velocity=v)))
        msgs.append((off, 1, n, mido.Message('note_off', channel=9, note=n, velocity=0)))
    end_tick = int((TOTAL_BEATS + TAIL) * TPB)
    for k in range(int(TOTAL_BEATS + TAIL) + 1):
        bpm = BASE * interp(TEMPO_KP, min((k + 0.5) / 4.0, 52.0))
        msgs.append((k * TPB, 0, 0, mido.MetaMessage('set_tempo', tempo=int(round(60000000 / bpm)))))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
    tr.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
    tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
    now = 0
    for tick, _, _, msg in msgs:
        tick = min(tick, end_tick)
        tr.append(msg.copy(time=tick - now))
        now = tick
    tr.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - now)))
    mid.save('solo.mid')


if __name__ == '__main__':
    render()
