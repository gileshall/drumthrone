#!/usr/bin/env python3
"""drum_solo.py - generates solo.mid, a ~2 minute General MIDI drum solo (channel 10).

Deterministic: fixed random seed, so every run writes an identical file.
Every note is assigned to a limb (R, L hands; RF, LF feet) and a final pass
guarantees no limb strikes twice at once, so at most 2 hands + 2 feet sound
at any instant. Feet only play kick (35/36) and hi-hat pedal (44).
"""
import math
import random
import bisect
import mido

rng = random.Random(1964)

# ---------------- General MIDI percussion ----------------
KICK2, KICK, STICK, SNARE, CLAP, SNARE2 = 35, 36, 37, 38, 39, 40
T_LF, HH_C, T_HF, HH_P, T_LM, HH_O, T_HM, T_HM2, CRASH, T_H = 41, 42, 43, 44, 45, 46, 47, 48, 49, 50
RIDE, CHINA, TAMB, BELL, SPLASH, COWBELL, CRASH2, VIBRA, RIDE2 = 51, 52, 54, 53, 55, 56, 57, 58, 59
BONGO_H, BONGO_L, CONGA_M, CONGA_O, CONGA_L = 60, 61, 62, 63, 64
AGOGO_H, AGOGO_L, CLAVES, WB_H, WB_L = 67, 68, 75, 76, 77

TOMS6 = [T_H, T_HM2, T_HM, T_LM, T_HF, T_LF]          # high -> low
KIT6 = [SNARE, T_H, T_HM2, T_LM, T_HF, T_LF]           # snare then down the toms

EV = []       # (beat, limb, note, vel, tag)
ANCH = []     # tempo anchors (beat, factor)
BUMPS = []    # (start, end, amount) tempo surges (+) / holds (-)


def add(beat, limb, note, vel, tag=''):
    if note is None:
        return
    EV.append((beat, limb, note, int(max(1, min(127, round(vel)))), tag))


def J(v, a=4.0):
    return v + rng.uniform(-a, a)


def pos(bar, p, grid=16, span=4.0):
    return bar * 4 + p * span / grid


def rush(b0, b1, amt=0.028):
    BUMPS.append((b0, b1, amt))


def anchor(b, f):
    ANCH.append((b, f))


STICKS = {'single': 'RL', 'double': 'RRLL', 'para': 'RLRRLRLL',
          'inv': 'RRLRLLRL', 'pdd': 'RLRRLL', 'six': 'RLLRRL'}


def stick(pattern, i, flip=False):
    s = STICKS[pattern][i % len(STICKS[pattern])]
    if flip:
        s = 'L' if s == 'R' else 'R'
    return s


# ---------------- vocabulary ----------------
def land(bar, v=115, both=False, note=CRASH):
    b = bar * 4
    add(b, 'R', note, J(v, 3), 'acc')
    add(b, 'RF', KICK, J(v, 3), 'acc')
    if both:
        add(b, 'L', CRASH2, J(v - 5, 3), 'acc')


M_POS = [0, 3, 6, 8, 10, 11, 14]
M_ROLE = ['L', 'M', 'H', 'S', 'S', 'L', 'X']
T_POS = [0, 2, 4, 6, 8, 9, 11]      # the motif recast in triplets (12 per bar)


def motif(bar, orch, lvl=1.0, shift=0, ghosts=0.0, kick=True, grid=16, span=4.0,
          positions=M_POS, roles=M_ROLE, upto=None, skip=(), flams=False, x2=False):
    used = set()
    base = {'L': 114, 'M': 102, 'H': 106, 'S': 98, 'X': 118}
    for p, r in zip(positions, roles):
        q = (p + shift) % grid
        if upto is not None and q >= upto:
            continue
        if q in skip:
            used.add(q)
            continue
        b = bar * 4 + q * span / grid
        limb = 'L' if r == 'S' else 'R'
        note = orch[r]
        add(b, limb, note, J(base[r] * lvl, 4), 'acc')
        used.add(q)
        if flams and limb == 'R' and r != 'X':
            add(b, 'L', note, J(42, 4), 'grace')
        if x2 and r == 'X':
            add(b, 'L', CRASH2, J(base[r] * lvl - 6, 3), 'acc')
        if kick and r in ('L', 'X'):
            add(b, 'RF', KICK, J(104 * lvl, 4))
    if ghosts:
        for q in range(grid):
            if q in used or q in skip or (upto is not None and q >= upto):
                continue
            if rng.random() < ghosts:
                add(bar * 4 + q * span / grid, 'L', SNARE, rng.uniform(20, 40), 'ghost')


def travel(b0, n, sub, path, v0, v1, pattern='single', acc=None, boost=18, soft=0,
           kick=None, flip=False, skip=(), kick_note=KICK, foot='RF'):
    for i in range(n):
        b = b0 + i / sub
        frac = i / max(1, n - 1)
        base = v0 + (v1 - v0) * frac
        if acc is None:
            a = False
        elif callable(acc):
            a = bool(acc(i))
        elif isinstance(acc, int):
            a = (i % acc == 0)
        else:
            a = i in acc
        if kick is not None:
            k = kick(i, a) if callable(kick) else (i % kick == 0)
            if k:
                add(b, foot, kick_note, J(min(122, base + (10 if a else 0))))
        if i in skip:
            continue
        limb = stick(pattern, i, flip)
        if callable(path):
            note = path(i, limb, a)
        else:
            note = path[min(len(path) - 1, int(i * len(path) / n))]
        v = base + boost if a else base - soft
        tag = 'acc' if a else ('ghost' if v < 50 else '')
        add(b, limb, note, J(v, 4), tag)


def roll(b0, beats, v0, v1, note=SNARE, sub=8, kick=True, curve=1.5):
    n = int(round(beats * sub))
    for i in range(n):
        limb = 'R' if (i // 2) % 2 == 0 else 'L'
        frac = i / max(1, n - 1)
        v = v0 + (v1 - v0) * frac ** curve
        if i % 2:
            v *= 0.92
        add(b0 + i / sub, limb, note, J(v, 3), 'ghost' if v < 50 else '')
    if kick:
        nb = int(beats)
        for q in range(nb):
            add(b0 + q, 'RF', KICK, J(45 + (v1 - 45) * 0.8 * q / max(1, nb - 1)))


def groove(bar, cym='hat', kicks=(0, 6, 10), ghost=0.3, open_at=(), fill_from=16,
           lvl=1.0, crash=False, bell_on=(), extra_snare=()):
    rpos = sorted(set(range(0, fill_from, 2)) | set(p for p in bell_on if p < fill_from))
    for p in rpos:
        if p == 0 and crash:
            continue
        if cym == 'hat':
            n = HH_O if p in open_at else HH_C
        else:
            n = BELL if p in bell_on else RIDE
        if n == BELL:
            v = 98
        elif n == HH_O:
            v = 90
        else:
            v = 96 if p % 8 == 0 else (82 if p % 4 == 0 else 64)
        add(pos(bar, p), 'R', n, J(v * lvl), 'acc' if v >= 90 else '')
        if n == HH_O:
            add(pos(bar, p + 2), 'LF', HH_P, J(64))
    lused = set()
    for p in (4, 12):
        if p < fill_from:
            add(pos(bar, p), 'L', SNARE, J(110 * lvl, 4), 'acc')
            lused.add(p)
    for p, v in extra_snare:
        add(pos(bar, p), 'L', SNARE, J(v), 'acc')
        lused.add(p)
    for p in kicks:
        if p < fill_from:
            add(pos(bar, p), 'RF', KICK, J((100 if p % 4 == 0 else 88) * lvl))
    if cym == 'ride':
        for p in (4, 12):
            if p < fill_from:
                add(pos(bar, p), 'LF', HH_P, J(60))
    for p in range(fill_from):
        if p in lused:
            continue
        pr = ghost * (1.0 if p % 2 else 0.5)
        if rng.random() < pr:
            add(pos(bar, p), 'L', SNARE, rng.uniform(20, 40), 'ghost')


def shuffle(bar, cym=RIDE, kicks=(0, 5, 8), ghost=0.8, crash=False, open_at=()):
    for q in range(12):
        if q % 3 == 1:
            continue
        if q == 0 and crash:
            continue
        n = HH_O if q in open_at else cym
        v = 88 if q in open_at else (92 if q % 3 == 0 else 62)
        add(pos(bar, q, 12), 'R', n, J(v), 'acc' if v >= 88 else '')
        if n == HH_O:
            add(pos(bar, q + 1, 12), 'LF', HH_P, J(62))
    add(pos(bar, 6, 12), 'L', SNARE, J(116), 'acc')
    for q in range(12):
        if q == 6:
            continue
        pr = ghost if q % 3 == 1 else 0.18
        if rng.random() < pr:
            add(pos(bar, q, 12), 'L', SNARE, rng.uniform(18, 36), 'ghost')
    for q in kicks:
        add(pos(bar, q, 12), 'RF', KICK, J(96 if q % 3 == 0 else 84))
    for q in (3, 9):
        add(pos(bar, q, 12), 'LF', HH_P, J(58))


def color(bar, R=(), L=(), K=(), LF=(0, 4, 8, 12)):
    for p, n, v in R:
        add(pos(bar, p), 'R', n, J(v), 'acc' if v > 80 else '')
    for p, n, v in L:
        add(pos(bar, p), 'L', n, J(v), 'ghost' if v < 45 else '')
    for p, v in K:
        add(pos(bar, p), 'RF', KICK, J(v))
    for p in LF:
        add(pos(bar, p), 'LF', HH_P, J(52))


def dk(bar, v0, v1, skip0=True):
    for i in range(16):
        if i == 0 and skip0:
            continue
        foot = 'RF' if i % 2 == 0 else 'LF'
        note = KICK if foot == 'RF' else KICK2
        v = v0 + (v1 - v0) * i / 15 + (12 if i % 4 == 0 else 0)
        add(pos(bar, i), foot, note, J(v))


# ======================= THE SOLO =======================
for b, f in [(0, 0.95), (8, 0.98), (16, 1.0), (44, 1.0), (48, 1.02), (76, 1.03),
             (82, 0.96), (92, 0.97), (96, 1.0), (124, 1.01), (128, 1.02), (136, 1.0),
             (144, 0.98), (158, 0.99), (160, 0.97), (176, 1.0), (188, 1.05),
             (200, 1.06), (208, 1.03), (212, 0.98), (216, 0.82), (240, 0.82)]:
    anchor(b, f)

# ---- 1. Intro: motif stated with space (bars 0-3)
ORCH_A = {'L': T_LF, 'M': T_LM, 'H': T_HM2, 'S': SNARE, 'X': T_HF}
motif(0, ORCH_A, lvl=0.82)
b = 1
for p in (0, 3, 6):
    add(pos(b, p), 'R', BELL, J(74 + p * 2), 'acc')
add(pos(b, 0), 'RF', KICK, J(78))
add(pos(b, 8), 'RF', KICK, J(72))
add(pos(b, 10), 'L', STICK, J(66))
add(pos(b, 11), 'L', STICK, J(74))
add(pos(b, 14), 'R', BELL, J(88), 'acc')
add(pos(b, 14), 'RF', KICK, J(84))
for p in (4, 12):
    add(pos(b, p), 'LF', HH_P, J(58))
for p in (5, 7, 13, 15):
    if rng.random() < 0.6:
        add(pos(b, p), 'L', SNARE, rng.uniform(18, 32), 'ghost')
motif(2, {'L': T_LM, 'M': T_HM2, 'H': T_H, 'S': SNARE, 'X': SPLASH}, lvl=0.9, ghosts=0.3)
motif(3, ORCH_A, lvl=0.95, ghosts=0.35, upto=8)
travel(pos(3, 8), 8, 4, [SNARE, SNARE, T_H, T_HM2, T_LM, T_HF, T_LF, T_LF], 72, 104,
       acc=2, boost=10, kick=4)
rush(pos(3, 6), pos(4, 0), 0.03)

# ---- 2. Groove development: motif in the kick (bars 4-11)
land(4, 112)
groove(4, 'hat', kicks=(0, 3, 6, 10), ghost=0.3, crash=True)
groove(5, 'hat', kicks=(0, 3, 6, 10, 11), ghost=0.35, open_at=(14,))
groove(6, 'hat', kicks=(0, 3, 7, 10, 13), ghost=0.4, open_at=(6,))
groove(7, 'hat', kicks=(0, 3, 6), ghost=0.45, fill_from=12)
travel(pos(7, 12), 6, 6, KIT6, 82, 110, acc=3, boost=8, kick=3)
rush(pos(7, 10), pos(8, 0))
land(8, 110)
groove(8, 'ride', kicks=(0, 3, 6, 10), ghost=0.45, crash=True)
groove(9, 'ride', kicks=(0, 3, 6, 11), ghost=0.5, extra_snare=((10, 96),))
groove(10, 'ride', kicks=(0, 3, 6, 8, 11), ghost=0.45, bell_on=(0, 3, 6, 14))
groove(11, 'ride', kicks=(0, 3, 6), ghost=0.4, fill_from=8)
F11 = [SNARE, T_H, T_HM2, T_LM, T_HF, T_LF]
travel(pos(11, 8), 12, 6, lambda i, l, a: F11[(i // 2) % 6], 78, 112, pattern='double',
       acc=lambda i: i % 2 == 0, boost=6, kick=6)
rush(pos(11, 6), pos(12, 0), 0.03)

# ---- 3. Singles travelling the kit (bars 12-19)
land(12, 116)
A12 = {3: T_H, 6: T_HM2, 8: T_LM, 11: T_HF, 14: T_LF}
travel(pos(12, 0), 16, 4, lambda i, l, a: A12.get(i, SNARE), 80, 92, acc=set(A12) | {0},
       boost=22, soft=38, skip=(0,), kick=lambda i, a: i in (8, 14))
A13 = {1: T_LF, 4: T_HF, 7: T_LM, 9: T_HM, 12: T_HM2, 15: T_H}
travel(pos(13, 0), 16, 4, lambda i, l, a: A13.get(i, SNARE), 82, 94, acc=set(A13),
       boost=20, soft=38, skip=(2, 10), kick=lambda i, a: i in (0, 2, 10))
TRI = [T_H, T_H, T_HM2, T_HM2, T_HM, T_LM, T_HF, T_LF, T_LF, T_HF, T_LM, T_HM, T_HM2,
       T_H, SNARE, SNARE]
travel(pos(14, 0), 16, 4, TRI, 62, 100, acc=4, boost=16, kick=8)
travel(pos(15, 0), 24, 6, lambda i, l, a: KIT6[i % 6] if (i // 6) != 2 else KIT6[5 - i % 6],
       78, 98, acc=6, boost=14, kick=6)
travel(pos(16, 0), 24, 6, lambda i, l, a: TOMS6[(i // 4) % 6] if a else SNARE, 80, 100,
       acc=4, boost=20, soft=30, kick=lambda i, a: a)
offs = [0, 0.25, 0.5, 0.625, 0.75, 0.875]
starts = [0, 2, 1, 3]
idx = 0
for beat in range(4):
    b0 = pos(17, 0) + beat
    for j, o in enumerate(offs):
        limb = 'R' if idx % 2 == 0 else 'L'
        idx += 1
        drum = KIT6[min(5, starts[beat] + j)]
        v = 106 if j == 0 else (84 if j == 1 else 68 + j * 6 + beat * 2)
        add(b0 + o, limb, drum, J(v), 'acc' if j == 0 else '')
    add(b0, 'RF', KICK, J(100))
    add(b0 + 0.5, 'RF', KICK, J(82))
A18 = {0: T_LF, 3: T_LM, 6: T_HM2, 8: SNARE, 10: SNARE, 11: T_LF, 14: CRASH}
travel(pos(18, 0), 16, 4, lambda i, l, a: A18.get(i, SNARE), 84, 96, acc=set(A18),
       boost=20, soft=44, kick=lambda i, a: i in (0, 11, 14))
travel(pos(19, 0), 12, 6, [T_LF, T_HF, T_LM, T_HM, T_HM2, T_H, SNARE], 80, 96,
       acc=3, boost=10, kick=6)
travel(pos(19, 8), 16, 8, KIT6, 92, 120, acc=4, boost=6, kick=4)
rush(pos(19, 0), pos(20, 0), 0.035)

# ---- 4. Space and color: motif on hand percussion, tension (bars 20-23)
land(20, 110)
color(20, R=[(3, COWBELL, 70), (6, COWBELL, 76), (8, COWBELL, 60), (10, COWBELL, 62),
             (11, COWBELL, 70), (14, COWBELL, 84)],
      L=[(5, CONGA_L, 55), (9, CONGA_M, 46), (13, CONGA_O, 62), (15, CONGA_M, 40)],
      K=[(11, 66)], LF=(4, 8, 12))
color(21, R=[(0, WB_L, 76), (3, WB_H, 68), (6, WB_H, 72), (8, WB_L, 58), (10, WB_H, 56),
             (11, WB_L, 64), (14, WB_H, 82)],
      L=[(4, STICK, 72), (7, SNARE, 26), (9, SNARE, 30), (12, STICK, 76), (15, SNARE, 28)],
      K=[(0, 70), (8, 62)])
L22 = []
for p in (1, 3, 5, 7, 9, 11, 13, 15):
    if rng.random() < 0.7:
        L22.append((p, BONGO_H if p % 4 == 1 else BONGO_L, rng.uniform(40, 56)))
color(22, R=[(0, AGOGO_H, 84), (2, AGOGO_L, 74), (5, AGOGO_H, 70), (8, AGOGO_H, 74),
             (10, AGOGO_L, 60), (12, AGOGO_H, 62), (13, AGOGO_L, 68)],
      L=L22, K=[(0, 68), (6, 58), (10, 64)])
b = 23
for p in range(0, 8, 2):
    add(pos(b, p), 'R', BELL, J(62 + p * 4))
for p in (1, 3, 5, 7):
    add(pos(b, p), 'L', SNARE, J(30 + p * 4), 'ghost')
for p in (0, 4):
    add(pos(b, p), 'RF', KICK, J(60 + p * 5))
add(pos(b, 4), 'LF', HH_P, J(55))
travel(pos(b, 8), 12, 6, [SNARE], 45, 112, acc=3, boost=6, kick=6)
rush(pos(23, 8), pos(24, 0), 0.03)

# ---- 5. Doubles and rudiments around the kit (bars 24-31)
land(24, 112)


def p24(i, l, a):
    if a:
        return (T_HF if (i // 8) % 2 == 0 else T_LF) if l == 'R' else T_HM2
    return HH_C if l == 'R' else SNARE


travel(pos(24, 0), 16, 4, p24, 76, 86, pattern='para', acc=4, boost=30, soft=32,
       skip=(0,), kick=lambda i, a: i in (6, 8, 14))
for p in (4, 12):
    add(pos(24, p), 'LF', HH_P, J(56))


def p25(i, l, a):
    if a:
        return T_LF if l == 'R' else SNARE
    return RIDE if l == 'R' else SNARE


travel(pos(25, 0), 16, 4, p25, 78, 90, pattern='inv', acc=4, boost=28, soft=38,
       kick=lambda i, a: i in (0, 2, 10, 13))
T26 = [T_H, T_HM2, T_LM, T_LF]


def p26(i, l, a):
    t = T26[(i // 6) % 4]
    if i % 6 == 0 or l == 'R':
        return t
    return SNARE


travel(pos(26, 0), 24, 6, p26, 82, 100, pattern='pdd', acc=6, boost=18, soft=26,
       kick=lambda i, a: i % 6 in (0, 4))
SEQ27 = [SNARE, T_H, T_HM2, T_LM, T_HF, T_LF, T_HF, T_LM]
travel(pos(27, 0), 16, 4, lambda i, l, a: SEQ27[(i // 2) % 8], 62, 106, pattern='double',
       acc=lambda i: i % 4 == 0, boost=10, kick=lambda i, a: i % 4 == 2)
acc28 = [T_HF, T_HM2, T_LF, CRASH]
for beat in range(4):
    b0 = pos(28, 0) + beat
    for j, (o, l) in enumerate(((0, 'R'), (0.125, 'R'), (0.25, 'L'), (0.375, 'L'))):
        add(b0 + o, l, SNARE, J(44 + j * 6 + beat * 3), 'ghost')
    add(b0 + 0.5, 'R', acc28[beat], J(112), 'acc')
    add(b0 + 0.5, 'RF', KICK, J(108))
    add(b0 + 0.75, 'L', SNARE, J(34), 'ghost')
T29 = [T_H, T_HM2, T_HF, T_LF]


def p29(i, l, a):
    k = i % 6
    if k in (0, 3, 4):
        return T29[(i // 6) % 4]
    return SNARE


travel(pos(29, 0), 24, 6, p29, 70, 92, pattern='six', acc=lambda i: i % 6 in (0, 5),
       boost=26, soft=30, kick=lambda i, a: i % 6 == 0)
motif(30, {'L': T_LF, 'M': T_HF, 'H': T_H, 'S': SNARE, 'X': CHINA}, lvl=0.96, ghosts=0.55)
roll(pos(31, 0), 4, 24, 120)
BUMPS.append((127, 128, -0.04))          # hold back before the release

# ---- 6. Release: the motif, full force (bars 32-33)
land(32, 124, both=True)
BIG = {'L': T_LF, 'M': T_HF, 'H': T_LM, 'S': SNARE, 'X': CRASH}
motif(32, BIG, lvl=1.1, flams=True, x2=True, skip=(0,))
motif(33, {'L': T_HF, 'M': T_HM, 'H': T_H, 'S': SNARE, 'X': CHINA}, lvl=1.0, shift=2,
      ghosts=0.35, upto=12)
travel(pos(33, 12), 6, 6, [T_H, T_HM2, T_LM, T_HF, T_LF, T_LF], 88, 114, acc=3, boost=8, kick=3)
rush(pos(33, 10), pos(34, 0))

# ---- 7. Triplet world: half-time shuffle, triplet motif, hemiola (bars 34-39)
land(34, 106)
shuffle(34, cym=RIDE, crash=True, kicks=(0, 5, 8))
shuffle(35, cym=HH_C, kicks=(0, 5, 8, 11), open_at=(11,), ghost=0.85)
ORCH_T = {'L': T_LF, 'M': T_LM, 'H': T_HM2, 'S': SNARE, 'X': CRASH}
motif(36, ORCH_T, grid=12, positions=T_POS, ghosts=0.4, lvl=1.0)
travel(pos(37, 0), 6, 3, [T_H, T_HM2, T_LM, T_HF, T_LF, T_LF], 74, 88, acc=3, boost=14, kick=3)
UD = [T_LF, T_HF, T_LM, T_HM2, T_H, SNARE, SNARE, T_H, T_HM2, T_LM, T_HF, T_LF]
travel(pos(37, 8), 12, 6, UD, 82, 110, acc=3, boost=10, kick=6)
TOMS_UP = list(reversed(TOMS6))
travel(pos(38, 0), 24, 6, lambda i, l, a: TOMS_UP[(i // 8 * 3 + (i % 8) // 3) % 6] if a else SNARE,
       78, 100, acc=lambda i: i % 8 in (0, 3, 6), boost=22, soft=32, kick=lambda i, a: a)
motif(39, ORCH_T, grid=12, positions=T_POS, shift=1, upto=9, ghosts=0.3)
travel(pos(39, 12), 6, 6, KIT6, 92, 118, acc=3, boost=6, kick=3)
rush(pos(39, 8), pos(40, 0), 0.03)

# ---- 8. The long build: whisper to thunder (bars 40-47)
land(40, 96)
travel(pos(40, 0), 16, 4, [SNARE], 28, 38, acc={3, 6, 11}, boost=40, skip=(0,))
for p in (4, 8, 12):
    add(pos(40, p), 'LF', HH_P, J(50))
A41 = {0: SNARE, 3: SNARE, 6: SNARE, 8: T_HM2, 10: SNARE, 11: T_LF, 14: T_H}
travel(pos(41, 0), 16, 4, lambda i, l, a: A41.get(i, SNARE), 32, 46, acc=set(A41),
       boost=48, kick=lambda i, a: i in (0, 3, 6))
for p in (4, 8, 12):
    add(pos(41, p), 'LF', HH_P, J(54))
A42 = {0: T_LF, 3: T_LM, 6: T_HM2, 8: SNARE, 10: SNARE, 11: T_LF, 14: T_H, 15: T_H}
travel(pos(42, 0), 16, 4, lambda i, l, a: A42.get(i, SNARE), 38, 56, acc=set(A42),
       boost=50, kick=2)
travel(pos(43, 0), 12, 4, lambda i, l, a: SEQ27[(i // 2 + 3) % 8], 60, 92, pattern='double',
       acc=lambda i: i % 2 == 0, boost=8, kick=4)
roll(pos(43, 12), 1, 80, 114, kick=False)
rush(pos(43, 8), pos(44, 0), 0.025)
land(44, 116)
dk(44, 70, 86)
motif(44, {'L': T_LF, 'M': T_LM, 'H': T_H, 'S': SNARE, 'X': CRASH}, lvl=1.05, kick=False,
      skip=(0,), ghosts=0.3)
dk(45, 74, 90, skip0=False)
A45 = {0: CRASH, 3: T_LM, 6: T_HF, 8: CRASH, 11: T_HM2, 14: T_LF}
travel(pos(45, 0), 16, 4, lambda i, l, a: A45.get(i, SNARE), 82, 96, acc=set(A45),
       boost=22, soft=30)
dk(46, 78, 96, skip0=False)
SEQ46 = [T_H, T_HM2, T_HM, T_LM, T_HF, T_LF, T_LF]
for beat in range(4):
    b0 = pos(46, 0) + beat
    add(b0, 'R', CRASH if beat % 2 == 0 else CHINA, J(112), 'acc')
    for j in range(1, 8):
        limb = 'L' if j % 2 else 'R'
        add(b0 + j / 8.0, limb, SEQ46[j - 1], J(70 + j * 4 + beat * 3))
UP_DOWN18 = [T_LF, T_HF, T_LM, T_HM, T_HM2, T_H, SNARE, SNARE, T_H, T_HM2, T_HM, T_LM,
             T_HF, T_LF, T_HF, T_LM, T_HM2, T_H]
travel(pos(47, 0), 18, 6, UP_DOWN18, 88, 112, acc=3, boost=8, kick=3)
roll(pos(47, 12), 1, 92, 122, kick=False)
add(pos(47, 12), 'RF', KICK, J(96))
BUMPS.append((191, 192, -0.03))          # breath before the climax

# ---- 9. Climax: recapitulation and development (bars 48-51)
land(48, 126, both=True)
motif(48, {'L': T_LF, 'M': T_HF, 'H': T_HM2, 'S': SNARE, 'X': CRASH}, lvl=1.15, flams=True,
      x2=True, skip=(0,))
for p in (1, 4, 7, 12):
    add(pos(48, p), 'LF', KICK2, J(90))
F49 = [(0, T_LF), (3, T_HF), (6, T_LM), (8, T_HM), (11, T_HM2), (14, CRASH)]
for p, n in F49:
    add(pos(49, p), 'R', n, J(112 + p * 0.6), 'acc')
    add(pos(49, p), 'RF', KICK, J(104))
    if p + 1 < 16:
        add(pos(49, p + 1), 'LF', KICK2, J(88))
    if p > 0:
        add(pos(49, p - 1), 'L', SNARE, J(52))
    if n == CRASH:
        add(pos(49, p), 'L', CRASH2, J(112), 'acc')
    else:
        add(pos(49, p), 'L', n, J(44), 'grace')
motif(50, {'L': T_LF, 'M': T_HF, 'H': T_H, 'S': SNARE, 'X': CHINA}, shift=1, ghosts=0.6, lvl=1.08)
travel(pos(51, 0), 12, 6, lambda i, l, a: KIT6[i % 6], 96, 108, acc=3, boost=8, kick=3)
travel(pos(51, 8), 16, 8, lambda i, l, a: [T_H, T_HM2, T_LM, T_LF][i // 4], 100, 124,
       acc=4, boost=4)
for j in range(8):
    foot = 'RF' if j % 2 == 0 else 'LF'
    add(pos(51, 8 + j), foot, KICK if foot == 'RF' else KICK2, J(92 + j * 3))
rush(pos(51, 0), pos(52, 0), 0.04)

# ---- 10. Ending: augmented motif, swelling roll, final hit (bars 52-54)
land(52, 122, both=True)
A52 = {6: T_LF, 12: T_LM}
travel(pos(52, 0), 16, 4, lambda i, l, a: A52.get(i, SNARE), 44, 70, acc=set(A52) | {0},
       boost=50, skip=(0,), kick=lambda i, a: i in (6, 12))
A53 = {0: SNARE, 4: SNARE, 6: T_LF}
travel(pos(53, 0), 8, 4, lambda i, l, a: A53.get(i, SNARE), 60, 80, acc=set(A53), boost=38,
       soft=10, kick=lambda i, a: i in (0, 6))
roll(pos(53, 8), 1, 62, 112, kick=False)
travel(pos(53, 12), 8, 8, [T_H, T_HM2, T_LM, T_HM, T_HF, T_HF, T_LF, T_LF], 108, 124,
       acc=2, boost=3)
add(pos(53, 12), 'RF', KICK, J(104))
add(pos(53, 14), 'RF', KICK, J(112))
FINAL = 54 * 4
add(FINAL, 'R', CRASH, 127, 'acc')
add(FINAL, 'L', CRASH2, 124, 'acc')
add(FINAL, 'RF', KICK, 127, 'acc')
add(FINAL, 'LF', KICK2, 120, 'acc')

# ======================= TEMPO MAP =======================
ANCH.sort()


def factor(b):
    if b <= ANCH[0][0]:
        f = ANCH[0][1]
    elif b >= ANCH[-1][0]:
        f = ANCH[-1][1]
    else:
        f = ANCH[-1][1]
        for i in range(len(ANCH) - 1):
            b0, f0 = ANCH[i]
            b1, f1 = ANCH[i + 1]
            if b0 <= b < b1:
                f = f0 + (f1 - f0) * (b - b0) / (b1 - b0) if b1 > b0 else f1
                break
    for s, e, amt in BUMPS:
        if s < b < e:
            f *= 1 + amt * math.sin(math.pi * (b - s) / (e - s))
    f *= 1 + 0.006 * math.sin(2 * math.pi * b / 32.0)
    return f


TPQ = 960
SEG = 0.5
NSEG = int((FINAL + 12) / SEG)
fs = [factor((k + 0.5) * SEG) for k in range(NSEG)]
raw = [SEG * 0.5 / f for f in fs]
Tf = sum(raw[:int(FINAL / SEG)])
scale = 117.0 / Tf                        # final hit lands at ~1:57, rings to 2:00
tempos = [int(round(0.5 / f * scale * 1e6)) for f in fs]
spb = [t / 1e6 for t in tempos]
T = [0.0]
for k in range(NSEG):
    T.append(T[-1] + spb[k] * SEG)


def b2s(b):
    k = min(NSEG - 1, max(0, int(b / SEG)))
    return T[k] + (b - k * SEG) * spb[k]


def s2tick(s):
    k = bisect.bisect_right(T, s) - 1
    k = min(max(k, 0), NSEG - 1)
    return int(round(k * SEG * TPQ + (s - T[k]) / spb[k] * TPQ))


# ======================= HUMAN FEEL =======================
LIMB_BIAS = {'R': 0.0, 'L': 0.002, 'RF': -0.002, 'LF': 0.003}
notes = []
for (b, limb, note, vel, tag) in EV:
    off = max(-0.009, min(0.009, rng.gauss(0, 0.0045)))
    if tag == 'ghost':
        off += 0.004
    elif tag == 'acc':
        off -= 0.003
    off += LIMB_BIAS[limb]
    if tag == 'grace':
        off = -0.03 + rng.uniform(-0.004, 0.004)
    t = max(0.0, b2s(b) + off)
    notes.append([t, limb, note, vel, tag, b])

# ---- playability: one stroke per limb at a time, realistic minimum spacing
MING = {'R': 0.048, 'L': 0.048, 'RF': 0.07, 'LF': 0.07}
final_notes = []
for limb in ('R', 'L', 'RF', 'LF'):
    seq = sorted([n for n in notes if n[1] == limb], key=lambda n: (n[0], -n[3], n[2]))
    kept = []
    for n in seq:
        if kept:
            d = n[0] - kept[-1][0]
            if d < 0.025:
                if n[3] > kept[-1][3]:
                    n[0] = kept[-1][0]
                    kept[-1] = n
                continue
            if d < MING[limb]:
                n[0] = kept[-1][0] + MING[limb]
        kept.append(n)
    final_notes += kept

# ======================= WRITE MIDI =======================
by_note = {}
for n in final_notes:
    by_note.setdefault(n[2], []).append(n)

msgs = []
for note in sorted(by_note):
    lst = sorted(by_note[note], key=lambda n: (n[0], -n[3]))
    merged = []
    for n in lst:
        tk = s2tick(n[0])
        if merged and tk - merged[-1][0] < 4:
            if n[3] > merged[-1][1][3]:
                merged[-1] = (merged[-1][0], n)
            continue
        merged.append((tk, n))
    for i, (on, n) in enumerate(merged):
        dur = 3.0 if n[5] >= FINAL else 0.11
        off = s2tick(n[0] + dur)
        if i + 1 < len(merged):
            off = min(off, merged[i + 1][0] - 1)
        if off <= on:
            off = on + 1
        msgs.append((on, 1, note, mido.Message('note_on', channel=9, note=note, velocity=n[3])))
        msgs.append((off, 0, note, mido.Message('note_off', channel=9, note=note, velocity=0)))
msgs.sort(key=lambda m: (m[0], m[1], m[2]))

mid = mido.MidiFile(type=1, ticks_per_beat=TPQ)
tempo_track = mido.MidiTrack()
mid.tracks.append(tempo_track)
tempo_track.append(mido.MetaMessage('track_name', name='Tempo', time=0))
tempo_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
last = 0
for k in range(NSEG):
    if k == 0 or tempos[k] != tempos[k - 1]:
        tk = int(k * SEG * TPQ)
        tempo_track.append(mido.MetaMessage('set_tempo', tempo=tempos[k], time=tk - last))
        last = tk
tempo_track.append(mido.MetaMessage('end_of_track', time=0))

drums = mido.MidiTrack()
mid.tracks.append(drums)
drums.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
drums.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
drums.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
drums.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
last = 0
for tk, _, _, m in msgs:
    drums.append(m.copy(time=tk - last))
    last = tk
end_tick = max(last, s2tick(b2s(FINAL) + 3.2))
drums.append(mido.MetaMessage('end_of_track', time=end_tick - last))

mid.save('solo.mid')
