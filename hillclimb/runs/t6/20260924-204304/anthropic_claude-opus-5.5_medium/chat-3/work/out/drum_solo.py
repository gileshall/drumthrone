#!/usr/bin/env python3
"""drum_solo.py - generates a ~2 minute General MIDI drum solo (solo.mid, channel 10)."""
import math
import random
import mido

rng = random.Random(90210)

# ---------------- General MIDI percussion ----------------
KICK = 36; KICK2 = 35; SN = 38; STICK = 37
HHC = 42; HHP = 44; HHO = 46; RIDE = 51; BELL = 53
CR1 = 49; CR2 = 57; CHINA = 52; SPLASH = 55
T1 = 50; T2 = 48; T3 = 47; T4 = 45; F1 = 43; F2 = 41
COW = 56; WBH = 76; WBL = 77
DRUMS = [SN, T1, T2, T4, F1, F2]
TOMS5 = [T1, T2, T4, F1, F2]
R, L, RF, LF = 'R', 'L', 'RF', 'LF'

ORCH_KIT = {'hi': SN, 'mid': T1, 'low': F1}
ORCH_KIT2 = {'hi': SN, 'mid': T2, 'low': F2}
ORCH_TOMS = {'hi': T1, 'mid': T4, 'low': F2}
ORCH_TOMS2 = {'hi': T2, 'mid': F1, 'low': F2}
ORCH_WOOD = {'hi': WBH, 'mid': WBL, 'low': F2}
ORCH_COW = {'hi': COW, 'mid': SN, 'low': F1}

# The motif: syncopated 3-3-2 shaped figure (16th grid) and its triplet cousin
MOTIF16 = [(0, 'hi', 3), (3, 'mid', 2), (6, 'hi', 3), (10, 'low', 2),
           (12, 'hi', 2), (13, 'mid', 1), (14, 'low', 3)]
MOTIF12 = [(0, 'hi', 3), (2, 'mid', 2), (4, 'hi', 3), (7, 'low', 2),
           (9, 'hi', 2), (10, 'mid', 1), (11, 'low', 3)]

events = []   # (beat, note, vel, limb, dt_seconds)


def hit(beat, note, vel, limb, dt=0.0):
    events.append((beat, note, vel, limb, dt))


def bb(bar, pos16=0.0):
    return bar * 4 + pos16 / 4.0


# ---------------- building blocks ----------------
def make_path(kind, G, N):
    if G <= 1:
        return [N - 1] if kind == 'up' else [0]
    if kind == 'down':
        return [round(i * (N - 1) / (G - 1)) for i in range(G)]
    if kind == 'up':
        return [N - 1 - round(i * (N - 1) / (G - 1)) for i in range(G)]
    if kind == 'wave':
        out = []
        for i in range(G):
            x = i / (G - 1)
            out.append(round((1 - abs(2 * x - 1)) * (N - 1)))
        return out
    idx = rng.randrange(N)
    out = []
    for _ in range(G):
        out.append(idx)
        idx += rng.choice((-1, 1, 1, 2))
        if idx >= N:
            idx = N - 2
        if idx < 0:
            idx = 1
    return out


def run(start, n, step, pattern='RL', v0=70, v1=110, path='down', group=2,
        drums=None, shape=1.0, acc=8):
    drums = drums or DRUMS
    nh = sum(1 for i in range(n) if pattern[i % len(pattern)] in 'RL')
    G = max(1, (nh + group - 1) // group)
    seq = make_path(path, G, len(drums))
    prev = None
    h = 0
    for i in range(n):
        c = pattern[i % len(pattern)]
        frac = i / (n - 1) if n > 1 else 1.0
        v = v0 + (v1 - v0) * frac ** shape
        t = start + i * step
        if c == 'K':
            hit(t, KICK, v * 0.9, RF)
        elif c == 'F':
            hit(t, KICK, v * 0.86, LF)
        else:
            d = drums[seq[min(G - 1, h // group)]]
            vv = v + acc if h % group == 0 else v - acc * 0.5
            if prev == c:
                vv *= 0.92
            hit(t, d, vv, R if c == 'R' else L)
            h += 1
        prev = c


def roll(start, beats, v0, v1, sub=8, note=SN, shape=1.6, kick_quarters=False):
    n = int(round(beats * sub))
    for i in range(n):
        frac = i / max(1, n - 1)
        v = v0 + (v1 - v0) * frac ** shape
        hand = R if i % 2 == 0 else L
        hit(start + i / sub, note, v + (2 if hand == R else -2), hand)
    if kick_quarters:
        for q in range(int(beats)):
            hit(start + q, KICK, 50 + (v1 - 40) * (q / beats) ** shape, RF)


def land(bar, v=118, cym=CR1, extra=None):
    b = bb(bar)
    hit(b, cym, v, R)
    hit(b, KICK, v - 6, RF)
    if extra:
        hit(b, extra, v - 8, L)


def hhfoot(bar, positions=(4, 12), v=52):
    for p in positions:
        hit(bb(bar, p), HHP, v + rng.uniform(-4, 4), LF)


def motif(bar, orch, level=1.0, density=0.0, shift=0, kick=True, crash_on=(),
          flam=False, trip=False, ghost_note=SN, cym=CR1, aug=1, fragment=None,
          cresc=(1.0, 1.0)):
    grid = MOTIF12 if trip else MOTIF16
    base = 1 / 3 if trip else 0.25
    length = (12 if trip else 16) * aug
    notes = grid if fragment is None else grid[:fragment]
    occ = set()
    cyms = [cym, CR2 if cym != CR2 else CR1]
    ci = 0
    for pos, role, a in notes:
        p = (pos * aug + shift) % length
        t = bar * 4 + p * base
        hand = R if p % 2 == 0 else L
        other = L if hand == R else R
        mult = level * (cresc[0] + (cresc[1] - cresc[0]) * p / length)
        v = {1: 76, 2: 96, 3: 112}[a] * mult
        note = orch[role]
        if pos in crash_on:
            hit(t, cyms[ci % 2], v + 6, R)
            ci += 1
            if hand == L:
                hit(t, note, v, L)
            hit(t, KICK, v, RF)
        else:
            hit(t, note, v, hand)
            if flam and a == 3:
                hit(t, note, v * 0.42, other, dt=-0.03)
            if kick is True and a == 3 or kick == 'all' and a >= 2:
                hit(t, KICK, v * 0.95, RF)
        occ.add(p)
    if density > 0:
        gl = max(0.8, min(level, 1.1))
        for p in range(length):
            if p not in occ and rng.random() < density:
                hit(bar * 4 + p * base, ghost_note, rng.uniform(24, 40) * gl,
                    R if p % 2 == 0 else L)


def answer(bar, level=1.0, ghost=SN, color=None):
    hit(bb(bar, 0), KICK, 72 * level, RF)
    for p in range(1, 12):
        if p != 8 and rng.random() < 0.38:
            hit(bb(bar, p), ghost, rng.uniform(26, 42), R if p % 2 == 0 else L)
    hit(bb(bar, 8), F1, 98 * level, R)
    hit(bb(bar, 8), KICK, 88 * level, RF)
    if color:
        hit(bb(bar, rng.choice([6, 10])), color, 82 * level, R)
    hit(bb(bar, 14), T1, 88 * level, R)
    hit(bb(bar, 15), T2, 96 * level, L)


KICK_PATS = [[0, 10], [0, 7, 10], [0, 8, 11], [0, 3, 10], [0, 6, 10, 11],
             [0, 10, 13], [0, 2, 7, 10], [0, 9, 10, 14], [0, 3, 8, 14]]


def groove(bar, level=1.0, ride=False, ghosts=0.4, open_prob=0.3, hits=False,
           hit_shift=0, beats=4, bell=False):
    n = beats * 4
    kp = [p for p in rng.choice(KICK_PATS) if p < n]
    if rng.random() < 0.3:
        x = rng.choice([5, 9, 15])
        if x < n and x not in kp:
            kp.append(x)
    open_pos = None
    if not ride and rng.random() < open_prob:
        open_pos = rng.choice([6, 14])
        if open_pos >= n:
            open_pos = None
    for p in range(0, n, 2):
        if ride:
            note = BELL if (bell and p % 4 == 0) else RIDE
            v = 86 if p % 4 == 0 else 66
        else:
            note = HHO if p == open_pos else HHC
            v = 86 if p % 4 == 0 else 62
        hit(bb(bar, p), note, v * level, R)
    if open_pos is not None:
        hit(bb(bar, open_pos + 2), HHP, 60, LF)
    if ride:
        for p in (4, 12):
            if p < n:
                hit(bb(bar, p), HHP, 56, LF)
    for p in (4, 12):
        if p < n:
            hit(bb(bar, p), SN, 106 * level, L)
    for p in range(n):
        if p in (4, 12):
            continue
        if (p % 2 == 1 or p in (2, 10, 14)) and rng.random() < ghosts:
            hit(bb(bar, p), SN, rng.uniform(24, 40), L)
    for p in kp:
        hit(bb(bar, p), KICK, (104 if p == 0 else 90) * level, RF)
    if hits:
        cy = [CR1, CR2, CHINA]
        k = 0
        for pos, role, a in MOTIF16:
            p = (pos + hit_shift) % 16
            if p >= n:
                continue
            if a >= 2:
                if p % 2 == 0:
                    hit(bb(bar, p), cy[k % 3], 112 * level, R)
                    k += 1
                else:
                    hit(bb(bar, p), SN, 112 * level, L)
                hit(bb(bar, p), KICK, 106 * level, RF)
            else:
                hit(bb(bar, p), SN, 88 * level, L)


LIN_GROUPS = ['RLK', 'RLRK', 'RLKK', 'RKLK', 'RLLK', 'RRLK']


def linear_bar(bar, level=1.0, groups=None, overlay=False, beats=4):
    slots = []
    while len(slots) < beats * 4:
        g = rng.choice(groups or LIN_GROUPS)
        slots += [(c, j) for j, c in enumerate(g)]
    slots = slots[:beats * 4]
    ri = rng.randrange(len(TOMS5))
    mpos = {pos: (role, a) for pos, role, a in MOTIF16}
    for p, (c, j) in enumerate(slots):
        t = bb(bar, p)
        acc = (j == 0)
        if overlay and p in mpos:
            role, a = mpos[p]
            v = {1: 84, 2: 100, 3: 114}[a] * level
            if c == 'K':
                hit(t, KICK, v, RF)
                if a == 3:
                    hit(t, CR1, v, R)
            else:
                hit(t, ORCH_KIT[role], v, R if c == 'R' else L)
            continue
        if c == 'K':
            hit(t, KICK, (92 if acc else 80) * level, RF)
        elif c == 'R':
            if acc:
                ri = max(0, min(len(TOMS5) - 1, ri + rng.choice((-1, 1, 1))))
            hit(t, TOMS5[ri], (108 if acc else 78) * level, R)
        else:
            hit(t, SN, (102 if acc else 52) * level, L)


def pdd_bar(bar, level=1.0):
    st = 'RLRRLL'
    rv = [rng.choice([F1, T4, F2, T2]) for _ in range(4)]
    lacc = rng.randrange(4)
    for i in range(24):
        c = st[i % 6]
        k = i % 6
        bi = i // 6
        t = bar * 4 + i / 6
        cres = 0.9 + 0.2 * i / 23
        if k == 0:
            hit(t, rv[bi], 110 * level * cres, R)
            hit(t, KICK, 92 * level * cres, RF)
        elif k == 4 and bi == lacc:
            hit(t, T1, 102 * level * cres, L)
        else:
            vv = {1: 50, 2: 58, 3: 50, 4: 56, 5: 48}[k]
            hit(t, SN, vv * level * cres, R if c == 'R' else L)


def ghost_texture(bar, level=0.7):
    accs = set(rng.sample(range(2, 11), 2))
    for p in range(16):
        hand = R if p % 2 == 0 else L
        t = bb(bar, p)
        if p >= 12:
            hit(t, [T1, T2, T4, F1][p - 12], (70 + 7 * (p - 12)) * level / 0.7, hand)
        elif p in accs:
            hit(t, T1 if hand == L else F1, 84 * level / 0.7, hand)
        else:
            hit(t, SN, rng.uniform(22, 36) + p, hand)


def shuffle_bar(bar, level=1.0):
    for beat in range(4):
        base = bar * 4 + beat
        hit(base, RIDE, (88 if beat % 2 == 0 else 76) * level, R)
        hit(base + 2 / 3, RIDE, 62 * level, R)
        if rng.random() < 0.7:
            hit(base + 1 / 3, SN, rng.uniform(26, 40), L)
        if beat in (1, 3):
            hit(base, SN, 108 * level, L)
            hit(base, HHP, 54, LF)
        if beat in (0, 2):
            hit(base, KICK, 98 * level, RF)
        if rng.random() < 0.45:
            hit(base + 2 / 3, KICK, 80 * level, RF)


def four_three(bar):
    cy = [CR1, CHINA, CR2]
    for s in range(12):
        t = bar * 4 + s / 3
        hand = R if s % 2 == 0 else L
        if s % 4 == 0:
            hit(t, cy[s // 4], 114, R)
            hit(t, KICK, 108, RF)
        else:
            hit(t, SN if hand == L else T4, rng.uniform(40, 58), hand)
            if s % 3 == 0:
                hit(t, KICK, 86, RF)
        if s % 3 == 0:
            hit(t, HHP, 50, LF)


def dbass(bar, v=90, beats=(0, 4), level=1.0):
    for p in range(beats[0] * 4, beats[1] * 4):
        foot = RF if p % 2 == 0 else LF
        vv = v + (12 if p % 4 == 0 else 0) - (5 if foot == LF else 0)
        hit(bb(bar, p), KICK, vv * level, foot)


def run32_threes(bar, nbars=2):
    n = 32 * nbars
    walk = make_path('walk', n // 3 + 2, len(TOMS5))
    for i in range(n):
        t = bar * 4 + i / 8
        hand = R if i % 2 == 0 else L
        frac = i / (n - 1)
        if i % 3 == 0:
            hit(t, TOMS5[walk[i // 3]], 98 + 20 * frac, hand)
        else:
            hit(t, SN, 46 + 22 * frac, hand)
    for k in range(8 * nbars):
        hit(bar * 4 + k / 2, KICK, 94 + (8 if k % 2 == 0 else 0), RF)


# ---------------- the solo ----------------
# 1. Statement (bars 0-3)
for b in range(4):
    hhfoot(b, (4, 12), 52)
motif(0, ORCH_KIT, level=0.92, flam=True)
answer(1, 0.9)
motif(2, ORCH_KIT2, level=0.97, density=0.45, flam=True)
motif(3, ORCH_KIT, level=1.0, fragment=3)
run(bb(3, 8), 8, 0.25, 'RL', 74, 112, 'down', 2)

# 2. Groove & motif as hits (bars 4-11)
land(4, 116)
groove(4, 0.95, ghosts=0.35)
groove(5, 1.0, ghosts=0.3, hits=True)
groove(6, 1.0, ride=True, ghosts=0.45)
groove(7, 1.0, ghosts=0.4, beats=2)
run(bb(7, 8), 8, 0.25, 'RL', 80, 114, 'walk', 2)
land(8, 118, CR2)
groove(8, 1.0, ride=True, bell=True, hits=True)
groove(9, 1.0, ghosts=0.75, open_prob=0.6)
groove(10, 1.05, ride=True, hits=True, hit_shift=2)
groove(11, 1.05, ghosts=0.5, beats=2)
run(bb(11, 8), 12, 1 / 6, 'RLRLKK', 84, 118, 'down', 4)
land(12, 122, CR1, extra=CHINA)

# 3. Linear travel, paradiddles, roll (bars 12-19)
for b in range(12, 19):
    hhfoot(b, (4, 12), 50)
linear_bar(12, 0.95)
linear_bar(13, 1.0, overlay=True)
linear_bar(14, 1.0, groups=['RLK', 'RKL', 'LRK'])
linear_bar(15, 1.0, beats=2)
run(bb(15, 8), 16, 1 / 8, 'RRLL', 70, 116, 'down', 4, shape=1.3)
land(16, 118)
pdd_bar(16, 0.95)
pdd_bar(17, 1.0)
motif(18, ORCH_TOMS, level=1.05, density=0.7, kick='all', crash_on=(0,))
roll(bb(19, 0), 3, 34, 102, 8, SN, shape=1.5, kick_quarters=True)
run(bb(19, 12), 8, 1 / 8, 'RL', 104, 120, 'down', 2, drums=TOMS5)
land(20, 118, CR2)

# 4. Breakdown: color, ghosts, augmentation, long swell (bars 20-27)
for b in range(20, 28):
    hhfoot(b, (0, 4, 8, 12), 46)
for b in (20, 21, 22, 23):
    if b != 20:
        hit(bb(b, 0), KICK, 62, RF)
    hit(bb(b, 10), KICK, 55, RF)
motif(20, ORCH_WOOD, level=0.62, kick=False)
answer(21, 0.65, ghost=STICK, color=COW)
motif(22, ORCH_WOOD, level=0.66, density=0.3, kick=False, ghost_note=SN)
ghost_texture(23, 0.7)
motif(24, ORCH_TOMS2, level=0.72, aug=2, kick=False, cresc=(0.85, 1.2))
for p in range(32):
    if p % 2 == 1 and rng.random() < 0.8:
        hit(bb(24, p), SN, 22 + 22 * p / 31, L)
for q in range(8):
    hit(bb(24, 4 * q), KICK, 55 + 3.5 * q, RF)
roll(bb(26, 0), 7, 18, 112, 8, SN, shape=2.2, kick_quarters=True)
run(bb(27, 12), 8, 1 / 8, 'RL', 112, 122, 'down', 2, drums=TOMS5)
land(28, 124, CR1, extra=CHINA)

# 5. Triplets (bars 28-35)
T = 1 / 3
for b in range(28, 34):
    if b not in (32,):
        hhfoot(b, (0, 4, 8, 12), 48)
run(bb(28, 0), 12, T, 'RLK', 88, 104, 'walk', 2)
run(bb(29, 0), 12, T, 'LRK', 90, 110, 'up', 2)
motif(30, ORCH_KIT, level=1.0, trip=True, crash_on=(0,), density=0.4)
run(bb(31, 0), 6, T, 'RLK', 92, 100, 'walk', 2)
for i, d in enumerate([T1, T2, T4, F1, F2, F2]):
    t = bb(31, 8) + i * T
    v = 96 + 5 * i
    hit(t, d, v, R)
    hit(t, d, v * 0.42, L, dt=-0.03)
    if i % 3 == 0:
        hit(t, KICK, v - 6, RF)
land(32, 120, CR2)
shuffle_bar(32, 1.0)
motif(33, ORCH_TOMS, level=1.02, trip=True, shift=6, density=0.5)
four_three(34)
run(bb(35, 0), 24, 1 / 6, 'RLRLKK', 80, 122, 'wave', 4)
land(36, 124, CR1, extra=CHINA)

# 6. Climax (bars 36-45)
dbass(36)
motif(36, ORCH_TOMS, level=1.05, crash_on=(0, 6, 12), kick=False)
dbass(37)
run(bb(37, 0), 16, 0.25, 'RL', 96, 116, 'walk', 3, drums=DRUMS, acc=14)
dbass(38)
motif(38, ORCH_KIT2, level=1.08, shift=4, crash_on=(0, 6), kick=False,
      cym=CHINA, density=0.35)
dbass(39, beats=(0, 2))
run(bb(39, 0), 8, 0.25, 'RL', 100, 106, 'up', 2)
run(bb(39, 8), 16, 1 / 8, 'RRLL', 90, 120, 'down', 4)
hit(bb(39, 8), KICK, 100, RF)
hit(bb(39, 12), KICK, 106, RF)
land(40, 122)
run32_threes(40, 2)
land(42, 124, CR2)
dbass(42)
motif(42, ORCH_COW, level=1.1, crash_on=(0,), kick=False, density=0.3)
dbass(43, beats=(0, 3))
for p in range(12):
    t = bb(43, p)
    if p % 4 == 0:
        hit(t, CHINA, 112, R)
    elif p % 2 == 0:
        hit(t, rng.choice([T1, T2]), 74, R)
    else:
        hit(t, SN, 102 if p in (3, 7) else rng.uniform(40, 52), L)
run(bb(43, 12), 6, 1 / 6, 'RLRLKF', 100, 120, 'down', 2)
dbass(44)
for k, d in enumerate([T1, T2, T4, F1, F2, T4, T2, T1]):
    t = bb(44, 0) + k / 2
    v = 96 + 3 * k
    hit(t, d, v, R)
    hit(t, d, v * 0.45, L, dt=-0.03)
    hit(t + 0.25, SN, 52 + 3 * k, L)
dbass(45, v=94)
roll(bb(45, 0), 3, 60, 112, 8, SN, shape=1.4)
run(bb(45, 12), 8, 1 / 8, 'RL', 110, 124, 'down', 2, drums=TOMS5)
land(46, 126, CR1, extra=CR2)

# 7. Recap & ending (bars 46-51)
for b in range(46, 51):
    hhfoot(b, (0, 4, 8, 12) if b != 48 else (4, 12), 50)
motif(46, ORCH_KIT, level=1.12, crash_on=(0, 6, 12), kick='all', flam=True)
motif(47, ORCH_TOMS, level=1.0, shift=2, density=0.5)
motif(48, ORCH_KIT, level=0.55, density=0.25, kick=True)
run(bb(49, 0), 16, 0.25, 'RL', 58, 112, 'wave', 2, shape=1.2)
for k in range(8):
    hit(bb(49, 0) + k / 2, KICK, 60 + 6 * k, RF)
motif(50, ORCH_KIT, level=1.15, crash_on=(0, 6), kick='all', fragment=4)
run(bb(50, 12), 6, 1 / 6, 'RL', 100, 118, 'down', 1, drums=TOMS5)
roll(bb(51, 0), 3, 44, 118, 8, SN, shape=1.7, kick_quarters=True)
run(bb(51, 12), 8, 1 / 8, 'RL', 116, 126, 'down', 2, drums=TOMS5)
for p in range(12, 16):
    hit(bb(51, p), KICK, 104 + 4 * (p - 12), RF if p % 2 == 0 else LF)
FINAL_BEAT = 52 * 4
hit(FINAL_BEAT, CR1, 127, R)
hit(FINAL_BEAT, CR2, 125, L)
hit(FINAL_BEAT, KICK, 127, RF)
hit(FINAL_BEAT, KICK2, 124, LF)

# ---------------- tempo map (rubato) ----------------
KEYS = [(0, 96), (4, 102), (12, 104), (19, 109), (20, 108), (20.5, 100), (24, 100),
        (27, 105), (28, 104), (35, 106), (36, 108), (45, 112), (46, 109),
        (50, 106), (51, 102), (52, 82), (60, 82)]


def base_bpm(barf):
    for (b0, t0), (b1, t1) in zip(KEYS, KEYS[1:]):
        if barf <= b1:
            f = (barf - b0) / (b1 - b0) if b1 > b0 else 0.0
            return t0 + (t1 - t0) * max(0.0, f)
    return KEYS[-1][1]


def bpm(beat):
    barf = beat / 4.0
    b = base_bpm(barf)
    if barf < 50:
        phr = (barf % 4) / 4.0
        b *= 1 - 0.006 + 0.018 * phr * phr          # push into phrase ends
        b *= 1 + 0.007 * math.sin(2 * math.pi * beat / 27.0)  # slow drift
    return b


RES = 96
TABLE = [0.0]
for k in range(1, (FINAL_BEAT + 8) * RES + 1):
    mid = (k - 0.5) / RES
    TABLE.append(TABLE[-1] + 60.0 / bpm(mid) / RES)


def raw_sec(beat):
    x = max(0.0, beat) * RES
    i = int(math.floor(x))
    i = min(i, len(TABLE) - 2)
    f = x - i
    return TABLE[i] + (TABLE[i + 1] - TABLE[i]) * f


SCALE = 117.0 / raw_sec(FINAL_BEAT)
FERMATA = 0.38
LEAD = 0.3


def beat2sec(beat):
    s = raw_sec(beat) * SCALE + LEAD
    if beat >= FINAL_BEAT - 1e-9:
        s += FERMATA
    return s


def human_offset(limb, vel, note):
    if limb in (R, L):
        o = rng.gauss(0, 0.0045)
        if limb == L:
            o += 0.0025
        if vel < 48:
            o += 0.005
        elif vel > 108:
            o -= 0.002
    else:
        o = rng.gauss(0, 0.0035)
        if note in (KICK, KICK2):
            o -= 0.001
    return max(-0.015, min(0.015, o))


# ---------------- realize ----------------
proc = []
for beat, note, vel, limb, dt in events:
    final = beat >= FINAL_BEAT - 1e-9
    off = 0.0 if final else human_offset(limb, vel, note)
    v = vel + rng.gauss(0, 3.0)
    v = int(round(max(1, min(127, v))))
    proc.append((beat2sec(beat) + dt + off, note, v, limb, final))

# playability: one stroke per limb at a time, minimum spacing per limb
kept = []
for limb in (R, L, RF, LF):
    lst = sorted([e for e in proc if e[3] == limb], key=lambda e: (e[0], -e[2], e[1]))
    minsp = 0.04 if limb in (R, L) else 0.075
    last = -10.0
    for e in lst:
        if e[0] - last >= minsp:
            kept.append(e)
            last = e[0]

TPS = 960  # ticks per second (480 tpb @ 120 bpm)
notes = {}
for s, note, v, limb, final in kept:
    tick = max(0, int(round(s * TPS)))
    key = (tick, note)
    if key not in notes or notes[key][0] < v:
        notes[key] = (v, final)

by_note = {}
for (tick, note), (v, final) in notes.items():
    by_note.setdefault(note, []).append((tick, v, final))

msgs = []
for note, lst in by_note.items():
    lst.sort()
    for i, (tick, v, final) in enumerate(lst):
        dur = int((3.0 if final else 0.1) * TPS)
        off = tick + dur
        if i + 1 < len(lst):
            off = min(off, lst[i + 1][0] - 1)
        off = max(off, tick + 1)
        msgs.append((tick, 1, note, v))
        msgs.append((off, 0, note, 0))
msgs.sort(key=lambda m: (m[0], m[1], m[2]))

mid = mido.MidiFile(type=0, ticks_per_beat=480)
tr = mido.MidiTrack()
mid.tracks.append(tr)
tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
tr.append(mido.Message('program_change', channel=9, program=0, time=0))
tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
tr.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
now = 0
for tick, kind, note, v in msgs:
    delta = tick - now
    now = tick
    if kind == 1:
        tr.append(mido.Message('note_on', channel=9, note=note, velocity=v, time=delta))
    else:
        tr.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=delta))
tr.append(mido.MetaMessage('end_of_track', time=int(0.2 * TPS)))
mid.save('solo.mid')
