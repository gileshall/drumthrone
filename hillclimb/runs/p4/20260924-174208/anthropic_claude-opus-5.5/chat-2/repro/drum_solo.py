#!/usr/bin/env python3
"""drum_solo.py - generates solo.mid, a ~2 minute General MIDI drum solo (channel 10).

Built around one motif: accents grouped 3-3-3-3-2-2 across a bar of 16ths.
It is stated, orchestrated around the kit, augmented, diminished, turned into
linear patterns, whispered on cowbell, and brought back at the end.
Every note belongs to a limb (R/L hands, R/L feet) so it stays playable.
"""
import math
import random
import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

# ---------------------------------------------------------------- kit (GM)
K = 36; SN = 38; SS = 37; HHC = 42; HHP = 44; HHO = 46
F2 = 41; F1 = 43; T3 = 45; T2 = 48; T1 = 50
CR1 = 49; CR2 = 57; RIDE = 51; BELL = 53; CHN = 52; SPL = 55
COW = 56; WBH = 76; WBL = 77; TIMH = 65; TIML = 66
CYMBALS = {CR1, CR2, RIDE, BELL, CHN, SPL, HHO}
TOMS = {F2, F1, T3, T2, T1, TIMH, TIML}

rng = random.Random(1964)
EV = []
LIMB = {'R': 'R', 'L': 'L', 'K': 'RF', 'H': 'LF', 'F': 'LF'}


def hit(beat, limb, note, vel, dt=0.0, dur=None):
    EV.append({'b': float(beat), 'limb': LIMB[limb], 'n': note,
               'v': float(vel), 'dt': dt, 'dur': dur})


def flam(beat, lead, note, vel):
    other = 'L' if lead == 'R' else 'R'
    hit(beat, lead, note, vel)
    hit(beat, other, note, max(22, vel * 0.33), dt=-0.024)


def crash(b, v=118, note=CR1, hand='R', kick=True):
    hit(b, hand, note, v)
    if kick:
        hit(b, 'K', K, v - 4)


def lin(start, sub, pattern, orch, vel):
    """Linear phrase. R/L hands, K kick, H hat foot, '-' rest."""
    n = len(pattern)
    for i, c in enumerate(pattern):
        if c == '-':
            continue
        b = start + i / sub
        v = vel(i, n, c) if callable(vel) else vel
        if c in 'RL':
            note = orch(i, c) if callable(orch) else orch
            hit(b, c, note, v)
        elif c == 'K':
            hit(b, 'K', K, v)
        elif c == 'H':
            hit(b, 'H', HHP, v * 0.7)


def ramp(v0, v1, acc=0, every=0, curve=1.0, dbl_soft=0):
    def f(i, n, c):
        x = i / max(1, n - 1)
        v = v0 + (v1 - v0) * x ** curve
        if every and i % every == 0:
            v += acc
        if dbl_soft and i % 2 == 1:
            v -= dbl_soft
        return v
    return f


def seg_path(notes, steps):
    L = len(notes)
    return lambda i, c: notes[min(L - 1, i * L // steps)]


def roll(start, dur, note, v0, v1, sub=8, lead='R', curve=1.5, kind='single'):
    other = 'L' if lead == 'R' else 'R'
    n = int(round(dur * sub))
    for i in range(n):
        if kind == 'single':
            limb, soft = (lead if i % 2 == 0 else other), 0
        else:
            limb, soft = (lead if (i // 2) % 2 == 0 else other), (5 if i % 2 else 0)
        x = i / max(1, n - 1)
        hit(start + i / sub, limb, note, v0 + (v1 - v0) * x ** curve - soft)


def dbl_kick(start, beats, v0=80, v1=None, sub=4):
    v1 = v0 if v1 is None else v1
    n = int(round(beats * sub))
    for i in range(n):
        v = v0 + (v1 - v0) * i / max(1, n - 1) + (10 if i % sub == 0 else 0)
        hit(start + i / sub, 'K' if i % 2 == 0 else 'F', K, v)


def hat_foot(start_bar, nbars, pos=(1, 3), v=58):
    for k in range(nbars):
        for q in pos:
            hit((start_bar + k) * 4 + q, 'H', HHP, v + (4 if q == 3 else 0))


# ---------------------------------------------------------------- the motif
MOT_ACC = [0, 3, 6, 9, 12, 14]
MOT_STICK = "RLRLRLRLLRLRLLRL"
MOT = [T1, T2, T3, F1, SN, F2]


def motif(start, unit, orch, acc=108, ghost=None, kicks=(0,), sticking=MOT_STICK,
          inner=1, tap=None, grow=0, gnote=SN, kv=None):
    steps = 16 * inner
    st = (sticking * steps)[:steps]
    du = unit / inner
    accs = {a * inner: j for j, a in enumerate(MOT_ACC)}
    for s in range(steps):
        b = start + s * du
        limb = st[s]
        g = grow * s / (steps - 1)
        if s in accs:
            j = accs[s]
            hit(b, limb, orch[j], acc + g - (0 if j in (0, 4) else 6))
            if j in kicks:
                hit(b, 'K', K, (kv if kv else acc - 6) + g)
        elif ghost is not None:
            v = ghost + 0.5 * g
            if tap is not None and s % inner == 0:
                v = tap + 0.5 * g
            if (s - 1) in accs:
                v -= 5
            if (s + 1) in accs:
                v += 4
            hit(b, limb, gnote, v)


GH = [[7, 15], [5, 7, 15], [7, 10, 15], [2, 7, 11, 15]]
KP = [[0, 3, 6, 10], [0, 3, 6, 9, 14], [0, 6, 9, 14], [0, 3, 6, 9, 11, 14]]


def groove_bar(bb, var=0, upto=4.0, open_hat=False, lvl=0):
    for e in range(8):
        p = e * 0.5
        if p >= upto - 1e-9:
            break
        note = HHC
        v = (98 if e == 0 else 88 if e % 2 == 0 else 64) + lvl
        if open_hat and e == 7:
            note, v = HHO, 90 + lvl
        hit(bb + p, 'R', note, v)
    for p in (1.0, 3.0):
        if p < upto - 1e-9:
            hit(bb + p, 'L', SN, 110 + lvl)
    for g in GH[var % 4]:
        p = g * 0.25
        if p < upto - 1e-9:
            hit(bb + p, 'L', SN, 28 + (g % 3) * 3)
    for k in KP[var % 4]:
        p = k * 0.25
        if p < upto - 1e-9:
            hit(bb + p, 'K', K, (96 if k == 0 else 84) + lvl)
    if open_hat and upto >= 4.0:
        hit(bb + 4, 'H', HHP, 62)


# ================================================================ THE SOLO
# ---- INTRO (bars 0-3): statement, answer, statement w/ ghosts, roll
hat_foot(0, 4, pos=(0, 1, 2, 3), v=46)
motif(0, .25, MOT, acc=100, kicks=(0, 3))
hit(4, 'R', F2, 102); hit(4, 'K', K, 98)
flam(5, 'R', SN, 106)
hit(5.5, 'R', F2, 88); hit(5.75, 'K', K, 78)
hit(6.5, 'L', SN, 34); hit(6.75, 'R', SN, 40)
lin(7, 6, "RLRLKK", lambda i, c: [T1, T2, T1, T2][i], ramp(62, 96))
motif(8, .25, MOT, acc=106, ghost=32, kicks=(0, 3))
lin(12, 4, "RLRLRLRL", lambda i, c: [T1, SN, SN, T2, SN, SN, T3, SN][i],
    lambda i, n, c: 104 if i in (0, 3, 6) else 36 + 2 * i)
hit(12, 'K', K, 92)
roll(14, 2, SN, 40, 112)
hit(14, 'K', K, 52); hit(15, 'K', K, 68)

# ---- GROOVE A (bars 4-11): the motif lives in the kick
crash(16, 116)
groove_bar(16, 0); groove_bar(20, 1); groove_bar(24, 2)
groove_bar(28, 0, upto=2.0)
lin(30, 4, "RLRLRLRL", lambda i, c: [SN, SN, T1, T1, T2, T2, F1, F2][i],
    lambda i, n, c: 106 if i in (0, 3, 6) else 60 + 4 * i)
hit(30, 'K', K, 88); hit(31.5, 'K', K, 96)
crash(32, 118)
groove_bar(32, 3, open_hat=True, lvl=4)
groove_bar(36, 1, open_hat=True, lvl=4)
groove_bar(40, 2, open_hat=True, lvl=6)
motif(44, .25, MOT, acc=110, ghost=36, kicks=(0, 3, 5))

# ---- DEVELOPMENT (bars 12-19): feet keep time, hands develop the motif
hat_foot(12, 8, v=58)
motif(48, 0.5, [CR1, T1, T2, F1, SN, F2], acc=100, ghost=30, tap=44, inner=2,
      sticking="RL", kicks=(0, 1, 2, 3, 4, 5), grow=16)            # augmentation
lin(56, 6, "RLRLKK" * 4,
    lambda i, c: [[SN, SN], [T1, T2], [T2, T3], [F1, F2]][i // 6][0 if c == 'R' else 1],
    ramp(58, 98, acc=16, every=6))                                   # sixlets
motif(60, .25, MOT, acc=108, ghost=46, sticking="RRLL", kicks=(0, 3))  # in doubles
motif(64, .125, [CR1, SN, T1, T2, F1, F2], acc=110, ghost=40, sticking="RL",
      kicks=(0, 3, 5))                                               # diminution
motif(66, .125, [SN, T1, T2, T3, F1, F2], acc=114, ghost=42, sticking="RL",
      kicks=(0, 5))
crash(68, 120)                                                       # space
flam(69.5, 'L', SN, 112)
hit(70.75, 'K', K, 92)
hit(71, 'R', F2, 112); hit(71, 'K', K, 108)
hit(71.5, 'R', T1, 86); hit(71.75, 'L', T2, 92)
lin(72, 6, "RL" * 12, seg_path([F2, F1, T3, T2, T1, SN], 24),
    lambda i, n, c: 42 + 62 * (i / (n - 1)) ** 1.3 + (16 if i % 3 == 0 else 0))
for q in range(4):
    hit(72 + q, 'K', K, 60 + q * 10)
roll(76, 2, SN, 58, 112)
lin(78, 4, "RLRLRLRL", lambda i, c: [T1, T1, T2, T2, T3, F1, F1, F2][i],
    lambda i, n, c: 98 + (14 if i % 3 == 0 else 0))
hit(78, 'K', K, 96); hit(79, 'K', K, 102); hit(79.5, 'K', K, 104)

# ---- BREAKDOWN (bars 20-27): colors, space, swing, swelling rolls
crash(80, 112, note=CR2, hand='L')
hat_foot(20, 8, v=60)
for k in range(4):
    bb = 80 + 4 * k
    if k < 3:
        motif(bb, .25, [COW] * 6, acc=74, kicks=(), sticking="R" * 16)
    else:
        for p, v in ((0, 76), (0.75, 70), (1.5, 72)):
            hit(bb + p, 'R', COW, v)
    for p, v in ((0, 86), (1.75, 62), (2.5, 74)):
        if k == 3 and p > 0:
            continue
        hit(bb + p, 'K', K, v)
    if k == 0:
        hit(bb + 3, 'L', SS, 74)
        for g in (1.25, 1.75, 3.25):
            hit(bb + g, 'L', SN, 26)
    elif k == 1:
        for p, n, v in ((1, WBH, 72), (2.75, WBL, 66), (3.25, WBL, 60), (3.75, WBH, 70)):
            hit(bb + p, 'L', n, v)
    elif k == 2:
        for p, n, v in ((0.5, T3, 50), (1.75, F1, 56), (2.75, F2, 60), (3.25, T2, 48), (3.75, SN, 64)):
            hit(bb + p, 'L', n, v)
    else:
        hit(bb + 1, 'L', SS, 70)
        roll(bb + 2, 2, SN, 26, 94)
        hit(bb + 3, 'K', K, 50)
hit(96, 'L', SPL, 96); hit(96, 'K', K, 86)
for k, bb in enumerate((96, 100)):                                   # jazz ride
    for q in range(4):
        if k == 1 and q == 3:
            continue
        hit(bb + q, 'R', RIDE, 84 if q in (1, 3) else 72)
        if q in (1, 3):
            hit(bb + q + 2 / 3, 'R', RIDE, 56)
    for q in range(4):
        if q > 0 or k == 1:
            hit(bb + q, 'K', K, 36)
for p, n, v in ((97 + 2 / 3, SN, 44), (98 + 2 / 3, SN, 78), (99 + 1 / 3, T3, 48),
                (100 + 2 / 3, SN, 40), (101 + 1 / 3, SN, 62), (102, T2, 70), (102 + 2 / 3, SN, 50)):
    hit(p, 'L', n, v)
hit(103, 'R', T1, 72); hit(103 + 1 / 3, 'L', T2, 78); hit(103 + 2 / 3, 'R', F1, 90)
hit(103 + 2 / 3, 'K', K, 80)
motif(104, .25, [SN, SN, SN, T3, SN, F1], acc=76, ghost=32, sticking="RRLL",
      grow=22, kicks=(0, 3))
lin(108, 4, "RLRLRLRL", lambda i, c: TIMH if c == 'R' else TIML,
    lambda i, n, c: 96 if i in (0, 3, 6) else 58 + 3 * i)
hit(108, 'K', K, 72)
roll(110, 2, SN, 44, 118)
for p, v in ((110, 50), (111, 72), (111.5, 84)):
    hit(p, 'K', K, v)

# ---- BUILD (bars 28-35): motif as linear grouping, rising density
P = "RLKRLKRLKRLKRLRL"


def build_lin(bb, rorch, rv, lacc_idx, lg, kv):
    def orch(i, c):
        return rorch(i) if c == 'R' else SN

    def vel(i, n, c):
        if c == 'R':
            return rv + (6 if i in (0, 12) else 0)
        if c == 'L':
            return 108 if i in lacc_idx else lg + i * 0.6
        return kv
    lin(bb, 4, P, orch, vel)


crash(112, 120)
build_lin(112, lambda i: HHC, 94, (4,), 36, 88)
build_lin(116, lambda i: HHO if i == 14 else HHC, 94, (4, 13), 38, 90)
hit(120, 'H', HHP, 64)
hat_foot(30, 6, v=60)
build_lin(120, lambda i: [CR1, T2, T3, F1, SN, F2][MOT_ACC.index(i)], 106, (4,), 44, 96)
hit(120, 'K', K, 102)
build_lin(124, lambda i: [T1, T2, T3, F1, SN, F2][MOT_ACC.index(i)], 110, (4, 13), 48, 98)
lin(128, 6, "RLRLKK" * 4,
    lambda i, c: [[T1, T2], [T2, T3], [T3, F1], [F1, F2]][i // 6][0 if c == 'R' else 1],
    ramp(70, 104, acc=16, every=6))
lin(132, 6, "RL" * 12,
    lambda i, c: [T1, T2, T3, F1, F2, SN][(i // 4) % 6] if i % 4 == 0 else SN,
    lambda i, n, c: (100 + 12 * i / (n - 1)) if i % 4 == 0 else 42 + 22 * i / (n - 1))
for q in range(4):
    hit(132 + q, 'K', K, 82)
HALF = [SN, T1, T2, T3, F1, F2]
lin(136, 8, "RL" * 16, lambda i, c: HALF[(i % 16) * 6 // 16], ramp(64, 114, acc=12, every=4))
for q in range(4):
    hit(136 + q, 'K', K, 84 + 5 * q)
motif(140, .25, [CR1, SN, T2, F1, SN, F2], acc=116, ghost=46, kicks=(0, 1, 2, 3, 4, 5))

# ---- CLIMAX (bars 36-45): double kick, runs, breaks
crash(144, 122)
for k, bb in enumerate((144, 148)):
    dbl_kick(bb, 4, 78)
    for p in sorted(set(range(0, 16, 2)) | set(MOT_ACC)):
        if p == 0:
            note, v = (CR1, 118) if k == 0 else (CHN, 104)
        elif p in (3, 9, 14):
            note, v = CHN, 100
        else:
            note, v = BELL, (84 if p % 4 == 0 else 72)
        hit(bb + p * 0.25, 'R', note, v)
    for p in (4, 12):
        hit(bb + p * 0.25, 'L', SN, 116)
    for p in (7, 10, 15):
        hit(bb + p * 0.25, 'L', SN, 36)
lin(152, 6, "RL" * 12, seg_path([T1, T2, T3, F1, F2, F2], 24), ramp(76, 100, acc=18, every=6))
lin(156, 6, "RL" * 12, seg_path([F2, F1, T3, T2, T1, SN], 24), ramp(84, 112, acc=12, every=3))
dbl_kick(152, 8, 64, 74)
motif(160, .125, [CR1, SN, T1, T2, F1, F2], acc=116, ghost=44, sticking="RL",
      kicks=(0, 1, 2, 3, 4, 5))
motif(162, .125, [CR2, T1, T2, T3, F1, F2], acc=118, ghost=46, sticking="RL",
      kicks=(0, 1, 2, 3, 4, 5))
for p, cn in ((0, CR1), (0.75, CHN), (1.5, CR2)):                    # the break
    hit(164 + p, 'R', cn, 122); hit(164 + p, 'L', SN, 118); hit(164 + p, 'K', K, 120)
hit(166, 'H', HHP, 58); hit(167, 'H', HHP, 62)
lin(167, 6, "RLRLKK", lambda i, c: [SN, T1, T2, T3][i], ramp(82, 112))
crash(168, 120)
WAVE = [SN, T1, T2, T3, F1, F2, F1, T3, T2, T1, SN, T1, T2, T3, F1, F2]
lin(168, 6, "RL" * 24, lambda i, c: WAVE[i // 3], ramp(72, 112, acc=18, every=3))
for q in range(8):
    hit(168 + q, 'K', K, 92)
hat_foot(42, 3, v=58)
lin(176, 8, "RRLL" * 8, lambda i, c: [SN, T1, T2, T3, F1, F2, F1, F2][i // 4],
    ramp(70, 116, dbl_soft=6))
for e in range(8):
    hit(176 + e * 0.5, 'K', K, 86)
roll(180, 3, SN, 60, 118)
dbl_kick(180, 3, 60, 108)
for p, lead, n in ((183, 'R', SN), (183.25, 'L', T2), (183.5, 'R', F1), (183.75, 'L', F2)):
    flam(p, lead, n, 118)
hit(183, 'K', K, 112); hit(183.5, 'K', K, 116)

# ---- RECAP & ENDING (bars 46-53)
crash(184, 124)
groove_bar(184, 0, open_hat=True, lvl=8)
groove_bar(188, 1, upto=3.0, lvl=8)
lin(191, 4, "RLRL", lambda i, c: [SN, T1, T2, F1][i], lambda i, n, c: [98, 90, 102, 112][i])
hit(191, 'K', K, 92)
motif(192, .25, [CR1, T2, T3, F1, SN, F2], acc=114, kicks=(0, 1, 2, 3, 4, 5))  # the return
hat_foot(48, 2, v=60)
motif(196, .25, MOT, acc=112, ghost=48, sticking="RRLL", kicks=(0, 3, 5))
crash(200, 122)
groove_bar(200, 3, open_hat=True, lvl=10)
motif(204, .125, [CR1, SN, T1, T2, F1, F2], acc=116, ghost=46, sticking="RL",
      kicks=(0, 1, 2, 3, 4, 5))
motif(206, .125, [CR2, T1, T2, T3, F1, F2], acc=120, ghost=50, sticking="RL",
      kicks=(0, 1, 2, 3, 4, 5))
lin(208, 6, "RL" * 6, seg_path(HALF, 12), ramp(96, 108, acc=16, every=3))
hit(208, 'K', K, 110); hit(209, 'K', K, 104)
lin(210, 4, "RLRLRL", lambda i, c: [T1, T2, T3, F1, F2, F2][i], ramp(104, 120, acc=6, every=2))
hit(210, 'K', K, 108); hit(211, 'K', K, 112)
flam(211.5, 'R', SN, 124); hit(211.5, 'K', K, 118)
FINAL = 212
BREATH = 0.10
for limb, n in (('R', CR1), ('L', CR2), ('K', K)):
    hit(FINAL, limb, n, 127, dt=BREATH, dur=3.2)

# ================================================================ time feel
TEMPO_BARS = [(0, 4, 102, 106), (4, 12, 106, 110), (12, 20, 110, 117), (20, 22, 113, 104),
              (22, 28, 104, 103), (28, 36, 104, 116), (36, 46, 116, 122), (46, 52, 120, 118),
              (52, 53, 117, 92), (53, 70, 92, 92)]
PUSH_BARS = [(3, 4, .03), (7.5, 8, .025), (11, 12, .03), (18, 20, .035), (23.5, 24, .02),
             (26, 28, .04), (33, 36, .04), (42, 46, .03), (51, 52, .03)]
SWING_BARS = [(0, 4, .01), (4, 12, .03), (12, 20, .02), (20, 28, .045), (28, 36, .025),
              (36, 46, .012), (46, 70, .03)]
FEEL_BARS = [(0, 4, .004), (4, 12, .002), (12, 20, 0.0), (20, 28, .007), (28, 36, -.002),
             (36, 46, -.005), (46, 70, 0.0)]


def region(tbl, b):
    br = b / 4.0
    for a, z, val in tbl:
        if a <= br < z:
            return val
    return tbl[-1][2]


def bpm_at(b):
    br = b / 4.0
    base = TEMPO_BARS[-1][3]
    for a, z, t0, t1 in TEMPO_BARS:
        if a <= br < z:
            base = t0 + (t1 - t0) * (br - a) / (z - a)
            break
    for a, z, amt in PUSH_BARS:
        if a <= br < z:
            x = (br - a) / (z - a)
            base *= 1 + amt * math.sin(math.pi * x ** 0.65) ** 2
    return base


RES = 192
NBEATS = 240
TBL = [0.0]
for k in range(NBEATS * RES):
    TBL.append(TBL[-1] + (60.0 / bpm_at((k + 0.5) / RES)) / RES)


def beat_time(b):
    idx = b * RES
    k = min(int(idx), len(TBL) - 2)
    return TBL[k] + (TBL[k + 1] - TBL[k]) * (idx - k)


def swing_warp(b, sw):
    x6 = b * 6
    if abs(x6 - round(x6)) < 1e-6 and abs(b * 2 - round(b * 2)) > 1e-6:
        return b                              # triplet grid: leave alone
    fl = math.floor(b + 1e-9)
    x = b - fl
    half = 0.0 if x < 0.5 else 0.5
    y = x - half
    if y < 0.25:
        y2 = y * (0.25 + sw) / 0.25
    else:
        y2 = 0.25 + sw + (y - 0.25) * (0.25 - sw) / 0.25
    return fl + half + y2


LEAD = 0.25
TARGET_FINAL = 117.0
SCALE = (TARGET_FINAL - LEAD - BREATH) / beat_time(FINAL)

timed = []
for e in EV:
    b = e['b']
    tb = beat_time(swing_warp(b, region(SWING_BARS, b))) * SCALE
    off = e['dt']
    limb, n, v = e['limb'], e['n'], e['v']
    final = e['dur'] is not None
    if limb == 'RF':
        off -= 0.003
    if limb in ('R', 'L'):
        off += region(FEEL_BARS, b)
        if n == SN and v >= 100:
            off += 0.006
        elif v < 50:
            off += 0.003
    if not final:
        off += max(-0.004, min(0.004, rng.gauss(0, 0.0018)))
        v = v + rng.randint(-3, 3)
    vv = int(round(max(8, min(127, v))))
    if e['dur'] is not None:
        d = e['dur']
    elif n in CYMBALS:
        d = 1.2
    elif n in TOMS:
        d = 0.25
    else:
        d = 0.12
    timed.append({'t': tb + off + LEAD, 'limb': limb, 'n': n, 'v': vv, 'd': d})


# ---------------------------------------------------------------- playability
def clean(evs):
    out = []
    for limb in ('R', 'L', 'RF', 'LF'):
        lst = sorted([e for e in evs if e['limb'] == limb], key=lambda e: (e['t'], -e['v'], e['n']))
        gap = 0.04 if limb in ('R', 'L') else 0.07
        changed = True
        while changed:
            changed = False
            kept = []
            for e in lst:
                if kept and e['t'] - kept[-1]['t'] < gap:
                    changed = True
                    if e['v'] > kept[-1]['v']:
                        kept[-1] = e
                    continue
                kept.append(e)
            lst = kept
        out.extend(lst)
    return out


cleaned = clean(timed)

# ---------------------------------------------------------------- write MIDI
TPB = 960
TPS = TPB * 2              # 120 bpm file tempo -> 1920 ticks per second
notes = sorted(cleaned, key=lambda e: (e['t'], e['n']))
by_note = {}
for e in notes:
    by_note.setdefault(e['n'], []).append(e)

msgs = []
for n in sorted(by_note):
    ons = []
    for e in by_note[n]:
        tk = max(0, int(round(e['t'] * TPS)))
        if ons and ons[-1][0] == tk:
            if e['v'] > ons[-1][1]:
                ons[-1] = (tk, e['v'], e['d'])
            continue
        ons.append((tk, e['v'], e['d']))
    for i, (tk, v, d) in enumerate(ons):
        off = tk + max(1, int(round(d * TPS)))
        if i + 1 < len(ons):
            off = min(off, ons[i + 1][0])
        msgs.append((tk, 1, n, v))
        msgs.append((off, 0, n, 0))
msgs.sort(key=lambda m: (m[0], m[1], m[2]))

mid = MidiFile(type=0, ticks_per_beat=TPB)
tr = MidiTrack()
mid.tracks.append(tr)
tr.append(MetaMessage('track_name', name='Drum Solo', time=0))
tr.append(MetaMessage('set_tempo', tempo=500000, time=0))
tr.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
tr.append(Message('control_change', channel=9, control=7, value=118, time=0))
tr.append(Message('control_change', channel=9, control=91, value=40, time=0))
now = 0
for tk, kind, n, v in msgs:
    delta = tk - now
    now = tk
    if kind == 1:
        tr.append(Message('note_on', channel=9, note=n, velocity=v, time=delta))
    else:
        tr.append(Message('note_off', channel=9, note=n, velocity=0, time=delta))
end_tick = max(now, int(round(120.5 * TPS)))
tr.append(MetaMessage('end_of_track', time=end_tick - now))
mid.save('solo.mid')
print("wrote solo.mid: %d notes, %.1f s" % (len(msgs) // 2, end_tick / TPS))
