#!/usr/bin/env python3
"""
drum_solo.py - generates solo.mid, a two-minute General MIDI drum solo on channel 10.

Main ideas:
  * Motif A is a 3+3+2 / 3+3+2 accent cell. It is stated in the intro, grooved,
    displaced, turned into linear groupings and triplet figures, set in colour
    percussion, and finally played in unison for the ending.
  * Every note is assigned to a limb: R hand, L hand, right foot or left foot.
    A final pass enforces a minimum re-strike time per limb, so at any instant
    at most two hands and two feet are playing.
  * Timing is not quantised. A tempo map surges and settles (fills push ahead,
    phrase downbeats settle back, the ending broadens). On top of that, each
    limb has correlated micro-timing, ghost notes sit slightly late, accents
    and the kick sit slightly early, and flam grace notes lead the main stroke.
  * All randomness is seeded, so every run writes an identical file.
"""
import math
import random
import bisect
import mido

PPQ = 960
R = random.Random(20250601)   # compositional choices
H = random.Random(4242)       # humanisation

# ---------------- General MIDI percussion ----------------
KICK2, KICK, XSTICK, SNARE, CLAP = 35, 36, 37, 38, 39
F2, F1, HHC, T4, HHP, T3, HHO, T2, T1 = 41, 43, 42, 45, 44, 47, 46, 48, 50
CR1, RIDE, CHINA, BELL, TAMB, SPLASH, COWBELL, CR2, VIBRA = 49, 51, 52, 53, 54, 55, 56, 57, 58
HITIMB, LOTIMB, HIAGO, LOAGO, CLAVES, WBH, WBL = 65, 66, 67, 68, 75, 76, 77

E = []        # [beat, pitch, vel, limb, kind, dt_seconds]
PUSH = {}     # beat index -> bpm offset (rushing in fills)


def hit(b, p, v, limb, kind='n', dt=0.0):
    E.append([float(b), int(p), float(v), limb, kind, float(dt)])


def push(b0, b1, amt):
    for k in range(int(math.floor(b0 + 1e-9)), int(math.ceil(b1 - 1e-9))):
        PUSH[k] = PUSH.get(k, 0.0) + amt


def qb(bar, q):
    return bar * 4 + q / 4.0


MOTIF = (0, 3, 6, 8, 11, 14)   # 3+3+2 3+3+2 in sixteenths


# ---------------- building blocks ----------------
def motif(bar, voices, vels, shift=0, kicks=(), crash=(), idx=None):
    occ = set()
    for i, pos in enumerate(MOTIF):
        if idx is not None and i not in idx:
            continue
        q = pos + shift
        b = qb(bar, q)
        v = vels[i]
        if i in crash:
            hit(b, CR1 if (i // 3) % 2 == 0 else CR2, v + 5, 'R', 'a')
            hit(b, voices[i], v, 'L', 'a')
        else:
            hit(b, voices[i], v, 'R' if i % 2 == 0 else 'L', 'a' if v >= 85 else 'n')
        if i in kicks:
            hit(b, KICK, v, 'RF', 'k')
        occ.add(q)
    return occ


def ghosts(bar, occ, prob, lo, hi, limb='L', pitch=SNARE, qs=None, cresc=False):
    for q in (qs if qs is not None else range(16)):
        if q in occ:
            continue
        if R.random() < prob:
            v = lo + (hi - lo) * (q / 15.0) if cresc else R.uniform(lo, hi)
            hit(qb(bar, q), pitch, v, limb, 'g')


def flam(b, p, v, main='L', gp=None):
    other = 'R' if main == 'L' else 'L'
    hit(b, gp if gp else p, v * 0.33, other, 'g', dt=-0.028)
    hit(b, p, v, main, 'a')


def run(b0, length, sub, sticking, path, v0, v1, acc=None, acc_boost=24,
        kick=None, curve=1.0, rush=0.0, first=None, env=None):
    n = int(round(length * sub))
    for i in range(n):
        x = i / float(n)
        s = sticking[i % len(sticking)]
        base = env(x) if env else v0 + (v1 - v0) * (x ** curve)
        is_acc = bool(acc(i)) if acc else False
        v = base + (acc_boost if is_acc else 0)
        if not is_acc and i > 0 and sticking[(i - 1) % len(sticking)] == s:
            v -= 5                       # second stroke of a double is softer
        b = b0 + i / float(sub)
        dt = -rush * x                   # hands run ahead through the fill
        if s in 'RL':
            if i == 0 and first:
                hit(b, first, v + 10, s, 'a', dt)
            else:
                hit(b, path(x, s, i, is_acc), v, s, 'a' if is_acc else 'n', dt)
        elif s == 'K':
            hit(b, KICK, v, 'RF', 'k', dt)
        elif s == 'k':
            hit(b, KICK2, v, 'LF', 'k', dt)
        if kick and kick(i):
            hit(b, KICK, max(v - 8, 50), 'RF', 'k', dt)


def descend(seq):
    return lambda x, s, i, a: seq[min(len(seq) - 1, int(x * len(seq)))]


def acc_travel(seq, unacc=SNARE):
    st = {'k': -1}

    def f(x, s, i, a):
        if a:
            st['k'] += 1
            return seq[st['k'] % len(seq)]
        return unacc[s] if isinstance(unacc, dict) else unacc
    return f


BON = [(T1, T2), (T2, T3), (T3, F1), (F1, F2), (T1, F1), (T2, F2)]


def bonham(offset=0):
    return lambda x, s, i, a: BON[((i // 6) + offset) % len(BON)][0 if s == 'R' else 1]


def swell_roll(b0, segs, v0, v1, pitch=SNARE, curve=1.6):
    total = sum(l for l, _ in segs)
    t = 0.0
    hand = 0
    for length, sub in segs:
        n = int(round(length * sub))
        for i in range(n):
            pos = t + i / float(sub)
            x = pos / total
            hit(b0 + pos, pitch, v0 + (v1 - v0) * (x ** curve), 'RL'[hand], 'r')
            hand ^= 1
        t += length


def groove(bar, kick16, ghost_p=0.3, ride=False, hat16=False, open_at=(),
           snare_extra=(), backbeat=(4, 12), pedal=None, crash_first=False,
           upto=16, inten=0.8, bb_vel=110, bell_on=()):
    step = 1 if hat16 else 2
    for q in range(0, upto, step):
        b = qb(bar, q)
        if crash_first and q == 0:
            hit(b, CR1, 112, 'R', 'a')
            continue
        if ride:
            p = BELL if q in bell_on else RIDE
        else:
            p = HHO if q in open_at else HHC
        v = 90 if q % 4 == 0 else (66 if q % 2 == 0 else 48)
        if p == BELL:
            v += 10
        v = v * (0.75 + 0.3 * inten) + R.uniform(-4, 4)
        hit(b, p, v, 'R', 'n' if q % 4 == 0 else 'h')
    occ = set()
    for q in backbeat:
        if q < upto:
            hit(qb(bar, q), SNARE, bb_vel + R.uniform(-4, 4), 'L', 'a')
            occ.add(q)
    for q, v in snare_extra:
        if q < upto:
            hit(qb(bar, q), SNARE, v, 'L', 'a' if v > 85 else 'n')
            occ.add(q)
    ghosts(bar, occ, ghost_p, 18, 38, qs=range(upto))
    for q in kick16:
        if q < upto:
            hit(qb(bar, q), KICK, (100 if q % 4 == 0 else 86) + R.uniform(-5, 5), 'RF', 'k')
    peds = set(pedal) if pedal else set()
    if not ride:
        for q in open_at:
            if q + 2 < upto:
                peds.add(q + 2)
    for q in sorted(peds):
        if q < upto:
            hit(qb(bar, q), HHP, 55 + R.uniform(-5, 5), 'LF', 'p')


CELLS = {2: ['RK', 'LK', 'RL'],
         3: ['RLK', 'RKL', 'LRK', 'RLL', 'RKK'],
         4: ['RLRK', 'RKLK', 'RLLK', 'RLKK'],
         5: ['RLRLK', 'RLKLK']}


def linear_bar(bar, parts, toms, v_acc=105, v_ghost=32, v_hat=60,
               crash_first=False, cresc=0.0, pedal=True):
    q = 0
    k = 0
    for n in parts:
        opts = CELLS[n]
        if crash_first and q == 0:
            opts = [c for c in opts if c[0] == 'R']
        cell = R.choice(opts)
        for j, s in enumerate(cell):
            if q >= 16:
                break
            b = qb(bar, q)
            boost = cresc * q / 16.0
            if j == 0:
                if s == 'R':
                    if crash_first and q == 0:
                        p = CR1
                    else:
                        p = toms[k % len(toms)]
                        k += 1
                    hit(b, p, v_acc + boost, 'R', 'a')
                elif s == 'L':
                    hit(b, SNARE, v_acc + 5 + boost, 'L', 'a')
                if (crash_first and q == 0) or R.random() < 0.35:
                    hit(b, KICK, v_acc - 5 + boost, 'RF', 'k')
            else:
                if s == 'R':
                    hit(b, HHC if R.random() < 0.7 else T1, v_hat + boost * 0.5, 'R', 'h')
                elif s == 'L':
                    hit(b, SNARE, v_ghost + boost * 0.5, 'L', 'g')
                else:
                    hit(b, KICK, 80 + boost * 0.5, 'RF', 'k')
            q += 1
    if pedal:
        for beat in (1, 3):
            if beat * 4 < q:
                hit(bar * 4 + beat, HHP, 50, 'LF', 'p')


def half_time(bar, kick16, rh='ride', ghost_p=0.4, glo=16, ghi=32, gcresc=False,
              back_pitch=XSTICK, back_vel=84, rh_skip=(), motif_bell=False,
              extra_occ=(), crash_first=False):
    rpos = set(range(0, 16, 2))
    if motif_bell:
        rpos |= set(MOTIF)
    if rh == 'cowbell':
        rpos = {0, 3, 6, 8, 10, 12, 14}
    for q in sorted(rpos):
        if q in rh_skip:
            continue
        b = qb(bar, q)
        if crash_first and q == 0:
            hit(b, CR1, 100, 'R', 'a')
            continue
        if rh == 'cowbell':
            a = q in (0, 3, 6, 10, 12)
            hit(b, COWBELL, 80 if a else 48, 'R', 'a' if a else 'h')
        elif motif_bell and q in MOTIF:
            hit(b, BELL, 80, 'R', 'a')
        elif rh == 'bell' and q % 4 == 0:
            hit(b, BELL, 72, 'R', 'n')
        else:
            hit(b, RIDE, 56 if q % 4 == 0 else 44, 'R', 'h')
    hit(qb(bar, 8), back_pitch, back_vel, 'L', 'a')
    occ = {8} | set(extra_occ)
    ghosts(bar, occ, ghost_p, glo, ghi, cresc=gcresc)
    for q in kick16:
        hit(qb(bar, q), KICK, (78 if q == 0 else 64) + R.uniform(-4, 4), 'RF', 'k')
    for beat in range(4):
        hit(bar * 4 + beat, HHP, 46 if beat % 2 == 0 else 56, 'LF', 'p')


def double_bass(bar, v0, v1=None):
    if v1 is None:
        v1 = v0
    for q in range(16):
        v = v0 + (v1 - v0) * q / 15.0 + (8 if q % 4 == 0 else 0)
        if q % 2 == 0:
            hit(qb(bar, q), KICK, v, 'RF', 'k')
        else:
            hit(qb(bar, q), KICK2, v - 4, 'LF', 'k')


def stabs_fill(bar, cymbals, v_stab, seq, fv0, fv1, shift=0):
    pos = [p + shift for p in MOTIF]
    pset = set(pos)
    for i, q in enumerate(pos):
        b = qb(bar, q)
        hit(b, cymbals[i], v_stab, 'R', 'a')
        hit(b, SNARE, v_stab - 4, 'L', 'a')
    hand = 0
    k = 0
    for q in range(16):
        if q in pset:
            hand = 0
            continue
        hit(qb(bar, q), seq[k % len(seq)], fv0 + (fv1 - fv0) * q / 15.0, 'RL'[hand], 'n')
        hand ^= 1
        k += 1


def motif_flurry(bar, vbig, crash_idx=(0, 3), fl=(50, 90)):
    pos = list(MOTIF) + [16]
    toms = [T1, T2, T3, T4, F1, F2]
    for i, p in enumerate(MOTIF):
        b = qb(bar, p)
        hit(b, (CR1 if i % 2 == 0 else CR2) if i in crash_idx else T1, vbig, 'R', 'a')
        hit(b, F1 if i in crash_idx else SNARE, vbig - 3, 'L', 'a')
        hit(b, KICK, vbig, 'RF', 'k')
        m = 2 * (pos[i + 1] - p)
        for j in range(1, m):
            x = j / float(m)
            hit(b + j / 8.0, toms[(j - 1 + i) % len(toms)],
                fl[0] + (fl[1] - fl[0]) * x, 'LR'[(j - 1) % 2], 'n')


def latin(bar, var, upto=16):
    rh = sorted(set(range(0, 16, 2)) | {3, 11})
    for q in rh:
        if q >= upto:
            continue
        a = q in (0, 3, 6, 10, 12)
        p = (HIAGO if a else LOAGO) if var == 1 else COWBELL
        hit(qb(bar, q), p, 92 if a else 58, 'R', 'a' if a else 'h')
    lh = {4: (HITIMB, 96), 12: (LOTIMB, 100)}
    if var == 1:
        lh[7] = (HITIMB, 80)
        lh[14] = (LOTIMB, 84)
    if var == 2:
        lh[9] = (HITIMB, 78)
        lh[15] = (T1, 80)
    for q, (p, v) in lh.items():
        if q < upto:
            hit(qb(bar, q), p, v, 'L', 'a')
    ghosts(bar, set(lh), 0.3, 18, 30, qs=range(upto))
    kp = {0: [0, 6, 8, 14], 1: [0, 3, 8, 11], 2: [0, 6, 10]}[var]
    for q in kp:
        if q < upto:
            hit(qb(bar, q), KICK, 90 + R.uniform(-5, 5), 'RF', 'k')
    for q in (4, 12):
        if q < upto:
            hit(qb(bar, q), HHP, 55, 'LF', 'p')


# =====================================================================
# THE SOLO (58 bars of 4/4)
# =====================================================================

# ---- 1. Intro: motif stated with space (bars 0-3) ----
for bar in range(3):
    for beat in range(4):
        hit(bar * 4 + beat, HHP, 44 + (8 if beat % 2 else 0), 'LF', 'p')
occ = motif(0, [F1, T4, T3, SNARE, F1, SNARE], [96, 62, 72, 90, 78, 104], kicks=(0, 4))
ghosts(0, occ, 0.25, 16, 28)
occ = motif(1, [F1, T4, T3, SNARE, T1, T2], [98, 60, 76, 94, 86, 100], kicks=(0,))
hit(qb(1, 15), T3, 70, 'R', 'n')
ghosts(1, occ | {15}, 0.3, 16, 30)
occ = motif(2, [F1, T4, T3, SNARE, F2, SNARE], [100, 66, 80, 100, 84, 110], kicks=(0, 3, 4))
hit(qb(2, 8), SNARE, 36, 'R', 'g', dt=-0.028)      # flams on the snare hits
hit(qb(2, 14), SNARE, 38, 'R', 'g', dt=-0.028)
hit(qb(2, 15), KICK, 90, 'RF', 'k')
ghosts(2, occ, 0.3, 18, 32)
swell_roll(12, [(1, 4), (1, 6), (1.5, 8)], 22, 100)
run(15.5, 0.5, 8, 'RLRL', descend([T1, T2, T4, F1]), 104, 116)
for beat in range(4):
    hit(12 + beat, KICK, 50 + 16 * beat, 'RF', 'k')
hit(12, HHP, 40, 'LF', 'p')
hit(13, HHP, 44, 'LF', 'p')
push(12, 16, 2.5)

# ---- 2. Groove statement (bars 4-11) ----
groove(4, [0, 3, 6, 10], ghost_p=0.3, open_at=(14,), crash_first=True)
groove(5, [0, 6, 8, 11, 14], ghost_p=0.35, open_at=(6,))
groove(6, [0, 3, 10, 13], ghost_p=0.3, hat16=True, snare_extra=[(15, 70)])
groove(7, [0, 7, 8], ghost_p=0.35, upto=10)
run(qb(7, 10), 1.5, 4, 'RLRLRL', descend([SNARE, T1, T2, T3, F1, F2]), 72, 108, rush=0.006)
hit(qb(7, 15), KICK, 95, 'RF', 'k')
push(30, 32, 2)
groove(8, [0, 3, 6, 8, 11], ride=True, ghost_p=0.35, crash_first=True, pedal=(4, 12), bell_on=(6, 14))
groove(9, [0, 2, 6, 10, 11], ride=True, ghost_p=0.45, pedal=(4, 12), snare_extra=[(7, 88)])
groove(10, list(MOTIF), backbeat=(), ghost_p=0.25, open_at=(14,),
       snare_extra=[(q, 104 if q in (0, 8) else 92) for q in MOTIF])
run(44, 4, 4, 'RLRL', acc_travel([T1, T2, T3, T4, F1, F2]), 34, 58,
    acc=lambda i: i in MOTIF, acc_boost=48, kick=lambda i: i in MOTIF, rush=0.008)
push(44, 48, 2.5)

# ---- 3. Development: linear phrases, sextuplets, displacement (bars 12-19) ----
linear_bar(12, [3, 3, 2, 3, 3, 2], [T1, T2, F1, T3, F2], crash_first=True)
linear_bar(13, R.choice([[4, 3, 3, 3, 3], [3, 3, 3, 3, 4]]), [T2, T1, F1], cresc=10)
linear_bar(14, [3, 3, 3, 3, 2, 2], [T1, T2, T3, T4, F1, F2], cresc=8)
linear_bar(15, [3, 3, 2], [F1, T2, T1])
run(qb(15, 8), 2, 6, 'RLLRLL', acc_travel([T1, T2, T3, T4, F1, F2]), 40, 70,
    acc=lambda i: i % 3 == 0, acc_boost=34, kick=lambda i: i % 6 == 0, rush=0.006)
push(60, 64, 2)
PAIRS = [(T1, SNARE), (T2, T1), (T3, T2), (F1, T3), (F2, F1), (F1, T4)]
run(64, 4, 6, 'RLRLKk', lambda x, s, i, a: PAIRS[(i // 6) % 6][0 if s == 'R' else 1],
    62, 90, acc=lambda i: i % 6 == 0, acc_boost=18, kick=lambda i: i == 0, first=CR1)
run(68, 4, 6, 'RLLRLL', acc_travel([F2, F1, T4, T3, T2, T1]), 30, 50,
    acc=lambda i: i % 3 == 0, acc_boost=50, kick=lambda i: i % 3 == 0)
for beat in range(4):
    hit(72 + beat, HHP, 50, 'LF', 'p')
occ = motif(18, [SNARE, T2, F1, SNARE, T1, F1], [112, 90, 96, 110, 94, 104], shift=2,
            kicks=(0, 2, 3, 4), crash=(0, 3), idx=(0, 1, 2, 3, 4))
ghosts(18, occ, 0.4, 20, 34)
run(76, 4, 8, 'RRLL', descend([SNARE, SNARE, T1, T2, T3, T4, F1, F2]), 50, 116, curve=1.4,
    first=CR2, kick=lambda i: i % 8 == 0 or (i >= 24 and i % 2 == 0), rush=0.01)
push(76, 80, 3)

# ---- 4. Contrast: quiet half-time, ghost notes, colour, swells (bars 20-27) ----
half_time(20, [0, 10], rh='ride', ghost_p=0.45, crash_first=True)
half_time(21, [0, 7, 10], rh='bell', ghost_p=0.6, glo=18, ghi=60, gcresc=True,
          rh_skip=(14,), extra_occ=(14,))
flam(qb(21, 14), SNARE, 102, main='L')
for beat in range(4):
    hit(88 + beat, HHP, 50, 'LF', 'p')
occ = motif(22, [F1, XSTICK, T4, XSTICK, F1, T1], [72, 56, 64, 60, 74, 82], kicks=(0,))
hit(qb(22, 2), WBL, 50, 'R', 'n')
hit(qb(22, 10), WBH, 55, 'R', 'n')
ghosts(22, occ | {2, 10}, 0.35, 14, 26)
run(92, 4, 6, 'RLRLRL', descend([F2, F1, T4, T3, T2, T1, T2, T3, T4, F1]), 0, 0,
    env=lambda x: 26 + 52 * math.sin(math.pi * x))
for beat in range(4):
    hit(92 + beat, KICK, 55 + 18 * math.sin(math.pi * (beat + 0.5) / 4), 'RF', 'k')
hit(93, HHP, 50, 'LF', 'p')
hit(95, HHP, 50, 'LF', 'p')
half_time(24, [0, 7, 10, 14], rh='cowbell', ghost_p=0.45, back_pitch=SNARE, back_vel=88)
half_time(25, [0, 3, 10], rh='ride', motif_bell=True, ghost_p=0.4)
for beat in range(4):
    hit(104 + beat, HHP, 52, 'LF', 'p')
occ = motif(26, [T4, SNARE, F1, SNARE, T2, F1], [74, 70, 82, 86, 80, 92], shift=2,
            kicks=(0, 3), idx=(0, 1, 2, 3, 4))
ghosts(26, occ, 0.4, 16, 30)
swell_roll(108, [(1, 4), (1, 6), (1.5, 8)], 18, 108, curve=1.8)
run(111.5, 0.5, 8, 'RLRL', descend([T1, T2, T3, F1]), 108, 118)
for beat in range(4):
    hit(108 + beat, KICK, 48 + 18 * beat, 'RF', 'k')
push(108, 112, 3)

# ---- 5. Build: triplet feel, Bonham triplets, six-stroke rolls (bars 28-35) ----
run(112, 4, 6, 'RLRLRL', acc_travel([T1, T2, T3, F1, T4, F2]), 30, 48,
    acc=lambda i: i % 4 == 0, acc_boost=52, kick=lambda i: i % 6 == 0, first=CR1)
hit(113, HHP, 52, 'LF', 'p')
hit(115, HHP, 52, 'LF', 'p')
run(116, 4, 6, 'RLRRLRLL', acc_travel([F1, T1, T3, T2, F2, T4]), 36, 56,
    acc=lambda i: i % 8 in (0, 4), acc_boost=46, kick=lambda i: i % 6 == 0)
hit(117, HHP, 54, 'LF', 'p')
hit(119, HHP, 54, 'LF', 'p')
run(120, 4, 6, 'RLK', bonham(0), 70, 96, acc=lambda i: i % 3 == 0, acc_boost=18)
push(122, 124, 1.5)
occ = motif(31, [SNARE, T1, F1, SNARE, T1, F1], [115, 98, 104, 0, 0, 0],
            kicks=(0, 1, 2), crash=(0,), idx=(0, 1, 2))
ghosts(31, occ, 0.5, 20, 34, qs=range(8))
run(qb(31, 8), 2, 6, 'RLK', bonham(2), 80, 106, acc=lambda i: i % 3 == 0, acc_boost=16)
push(126, 128, 2)
run(128, 4, 8, 'RLLRRL', acc_travel([T1, T2, T3, T4, F1, F2]), 44, 66,
    acc=lambda i: i % 6 in (0, 5), acc_boost=40, kick=lambda i: i % 8 == 0, first=CR1)
run(132, 4, 8, 'RLLRRL', acc_travel([F2, F1, T4, T3, T2, T1]), 56, 84,
    acc=lambda i: i % 6 in (0, 5), acc_boost=36, kick=lambda i: i % 6 == 0)
linear_bar(34, [3, 3, 2, 3, 3, 2], [CR1, T2, F1, CR2, T1, F2], crash_first=True, cresc=12, v_acc=110)
run(140, 4, 8, 'RRLL', descend([SNARE, T1, T1, T2, T2, T3, T4, F1, F2]), 60, 120,
    kick=lambda i: i % 4 == 0 or (i >= 24 and i % 2 == 0), rush=0.01)
push(140, 144, 3)

# ---- 6. Climax: double bass, stabs, 32nd runs, motif in unison (bars 36-43) ----
double_bass(36, 84)
stabs_fill(36, [CR1, CHINA, CR2, CR1, SPLASH, CR2], 116, [T1, T2, T3, F1, F2], 50, 72)
double_bass(37, 80)
for q in range(16):
    if q % 4 == 0:
        hit(qb(37, q), CHINA, 104, 'R', 'a')
    elif q % 2 == 0:
        hit(qb(37, q), BELL, 82, 'R', 'n')
for q in (4, 12):
    hit(qb(37, q), SNARE, 116, 'L', 'a')
ghosts(37, {4, 12}, 0.35, 26, 44)
double_bass(38, 86)
stabs_fill(38, [CR2, CR1, CHINA, CR2, CR1, SPLASH], 118, [F2, F1, T3, T2, T1], 56, 80, shift=1)
double_bass(39, 88, 100)
run(156, 4, 6, 'RLRLRL', acc_travel([T1, T2, T3, T4, F1, F2]), 50, 80,
    acc=lambda i: i % 3 == 0, acc_boost=34)
push(156, 160, 2)
run(160, 4, 8, 'RLRL', acc_travel([T1, T2, T3, T4, F1, F2]), 44, 70,
    acc=lambda i: i % 3 == 0, acc_boost=40, kick=lambda i: i % 8 == 0, first=CR1)
run(164, 4, 8, 'RLRL', acc_travel([F2, F1, T4, T3, T2, T1]), 64, 92,
    acc=lambda i: i % 5 == 0, acc_boost=30, kick=lambda i: i % 4 == 0, rush=0.008)
push(164, 168, 3)
motif_flurry(42, 120, crash_idx=(0, 3), fl=(48, 88))
hit(172, CR2, 124, 'R', 'a')          # the stop: one big hit, then air
hit(172, SNARE, 120, 'L', 'a')
hit(172, KICK, 124, 'RF', 'k')
hit(173.5, VIBRA, 80, 'R', 'n')
hit(173, HHP, 52, 'LF', 'p')
hit(174, HHP, 56, 'LF', 'p')
hit(175, HHP, 60, 'LF', 'p')
run(175, 1, 4, 'LRLR', lambda *a: SNARE, 24, 60)

# ---- 7. Call-back: motif in colour percussion, call and response (bars 44-49) ----
latin(44, 0)
latin(45, 1)
occ = motif(46, [LOTIMB, HITIMB, T2, HITIMB, F1, HITIMB], [104, 92, 96, 100, 98, 108], kicks=(0, 4))
hit(qb(46, 2), COWBELL, 70, 'R', 'n')
hit(qb(46, 13), COWBELL, 72, 'R', 'n')
ghosts(46, occ, 0.3, 18, 30)
hit(qb(46, 4), HHP, 55, 'LF', 'p')
hit(qb(46, 12), HHP, 55, 'LF', 'p')
latin(47, 2, upto=8)
run(qb(47, 8), 2, 4, 'RLRLRLRL', descend([HITIMB, HITIMB, LOTIMB, LOTIMB, T2, T3, F1, F2]),
    70, 110, kick=lambda i: i % 2 == 0)
push(190, 192, 2)
motif(48, [SNARE, T2, F1, 0, 0, 0], [118, 104, 110, 0, 0, 0], kicks=(0, 1, 2), crash=(0,), idx=(0, 1, 2))
run(qb(48, 8), 2, 4, 'RLRLRLRL', lambda *a: SNARE, 18, 44)
for beat in range(4):
    hit(192 + beat, HHP, 52, 'LF', 'p')
run(196, 2, 6, 'RLRLRL', lambda *a: SNARE, 20, 40)
motif(49, [0, 0, 0, T1, T3, F1], [0, 0, 0, 110, 112, 118], kicks=(3, 4, 5), idx=(3, 4, 5))
hit(qb(49, 14), F1, 36, 'R', 'g', dt=-0.028)
hit(qb(49, 15), T4, 96, 'R', 'n')
hit(qb(49, 15), KICK, 96, 'RF', 'k')
hit(196, HHP, 52, 'LF', 'p')
hit(197, HHP, 52, 'LF', 'p')
push(198, 200, 2)

# ---- 8. Finale: groove reprise, big build, unison motif, final hit (bars 50-57) ----
groove(50, [0, 3, 6, 10, 11], open_at=(14,), crash_first=True, ghost_p=0.3, inten=1.0, bb_vel=118)
groove(51, [0, 3, 6, 8, 11, 14], ride=True, bell_on=(0, 4, 8, 12), ghost_p=0.35,
       pedal=(4, 12), snare_extra=[(14, 98)], inten=1.0, bb_vel=118)
groove(52, [0, 3, 8, 10], hat16=True, upto=12, ghost_p=0.35, inten=1.0, bb_vel=118)
run(211, 1, 8, 'RLRL', descend([SNARE, T1, T2, F1]), 80, 116, kick=lambda i: i % 2 == 0)
push(211, 212, 2)
linear_bar(53, [3, 3, 2, 3, 3, 2], [CR1, T1, F1, SPLASH, T2, F2], crash_first=True, cresc=14, v_acc=112)
double_bass(54, 80, 96)
run(216, 4, 6, 'RLLRLL', acc_travel([T1, T2, T3, T4, F1, F2]), 44, 72,
    acc=lambda i: i % 3 == 0, acc_boost=44, first=CR1)
push(216, 220, 1.5)
swell_roll(220, [(2, 8), (1.5, 12)], 60, 122, curve=1.3)
run(223.5, 0.5, 8, 'RLRL', descend([T1, T2, F1, F2]), 116, 124)
double_bass(55, 66, 112)
push(220, 224, 3)
motif_flurry(56, 124, crash_idx=(0, 3, 5), fl=(56, 100))
hit(228, CR1, 127, 'R', 'f')
hit(228, CR2, 127, 'L', 'f')
hit(228, KICK, 127, 'RF', 'f')
hit(228, KICK2, 120, 'LF', 'f')

# =====================================================================
# Tempo map: surges and settles
# =====================================================================
KEY = [(0, 108), (3, 112), (3.95, 114), (4, 116), (11.9, 118), (12, 118), (19.9, 121),
       (20, 112), (26.9, 113), (27.9, 116), (28, 117), (35.9, 123), (36, 123), (42, 126),
       (42.9, 125), (43, 117), (44, 115), (49.9, 118), (50, 119), (54.9, 126), (55.9, 128),
       (56, 124), (56.5, 120), (57, 96), (60, 96)]


def key_tempo(beat):
    barf = beat / 4.0
    for (b0, t0), (b1, t1) in zip(KEY, KEY[1:]):
        if b0 <= barf <= b1:
            return t0 + (t1 - t0) * (barf - b0) / (b1 - b0) if b1 > b0 else t1
    return KEY[-1][1]


NB = 240
raw = []
for k in range(NB):
    t = key_tempo(k + 0.5) + PUSH.get(k, 0.0)
    t += 0.7 * math.sin(2 * math.pi * k / 22.0) + 0.4 * math.sin(2 * math.pi * k / 9.3 + 1.0)
    if k % 16 == 0 and k > 0:
        t -= 1.2              # settle onto phrase downbeats
    raw.append(t)
sm = [0.25 * raw[max(0, k - 1)] + 0.5 * raw[k] + 0.25 * raw[min(NB - 1, k + 1)] for k in range(NB)]
TEMPOS = [int(round(60e6 / x)) for x in sm]
BPM = [60e6 / t for t in TEMPOS]
T = [0.0]
for k in range(NB):
    T.append(T[-1] + 60.0 / BPM[k])


def beat_to_sec(b):
    k = min(max(int(math.floor(b)), 0), NB - 1)
    return T[k] + (b - k) * 60.0 / BPM[k]


def sec_to_tick(s):
    if s <= 0:
        return 0.0
    k = min(bisect.bisect_right(T, s) - 1, NB - 1)
    return (k + (s - T[k]) * BPM[k] / 60.0) * PPQ


# =====================================================================
# Humanise: correlated per-limb micro-timing, feel biases, velocity spread
# =====================================================================
SD = {'a': 0.004, 'n': 0.006, 'g': 0.008, 'h': 0.005, 'k': 0.004, 'p': 0.006, 'r': 0.004, 'f': 0.002}
BIAS = {'g': 0.004, 'h': 0.002, 'k': -0.002, 'a': -0.002, 'p': 0.003}
E.sort(key=lambda e: (e[0], e[3], e[1]))
last_off = {'R': 0.0, 'L': 0.0, 'RF': 0.0, 'LF': 0.0}
notes = []
for b, p, v, limb, kind, dt in E:
    if v <= 0:
        continue
    off = 0.55 * last_off[limb] + H.gauss(0, SD.get(kind, 0.006))
    last_off[limb] = off
    s = max(0.0, beat_to_sec(b) + off + BIAS.get(kind, 0.0) + dt)
    vel = v + H.gauss(0, 2.5 if kind in ('a', 'k', 'f') else 3.5)
    vel = int(round(max(8 if kind == 'g' else 15, min(127, vel))))
    notes.append([s, p, vel, limb, kind])

# =====================================================================
# Playability: each limb needs time to re-strike (so <=2 hands, <=2 feet at once)
# =====================================================================
MIN_GAP = {'R': 0.042, 'L': 0.042, 'RF': 0.075, 'LF': 0.075}
notes.sort(key=lambda n: (n[0], n[3], n[1]))
kept = {l: [] for l in MIN_GAP}
for n in notes:
    lst = kept[n[3]]
    if lst and n[0] - lst[-1][0] < MIN_GAP[n[3]]:
        if n[2] > lst[-1][2]:
            lst[-1] = n
        continue
    lst.append(n)
fin = sorted([n for l in ('R', 'L', 'RF', 'LF') for n in kept[l]], key=lambda n: (n[0], n[3], n[1]))
# the same drum struck by two limbs almost at once: keep the louder one
dedup = []
lastp = {}
for n in fin:
    j = lastp.get(n[1])
    if j is not None and n[0] - dedup[j][0] < 0.015:
        if n[2] > dedup[j][2]:
            dedup[j] = n
        continue
    lastp[n[1]] = len(dedup)
    dedup.append(n)
fin = sorted(dedup, key=lambda n: (n[0], n[3], n[1]))

# =====================================================================
# Write the MIDI file
# =====================================================================
evs = []
nxt_l, nxt_p = {}, {}
last_tick = 0
for i in reversed(range(len(fin))):
    s, p, v, l, kd = fin[i]
    dur = 2.5 if kd == 'f' else 0.08
    dur = min(dur, nxt_l.get(l, 1e9) - s - 0.004, nxt_p.get(p, 1e9) - s - 0.004)
    dur = max(dur, 0.006)
    on = int(round(sec_to_tick(s)))
    off = int(round(sec_to_tick(s + dur)))
    if off <= on:
        off = on + 1
    nxt_l[l] = s
    nxt_p[p] = s
    evs.append((on, 2, mido.Message('note_on', channel=9, note=p, velocity=v)))
    evs.append((off, 1, mido.Message('note_off', channel=9, note=p, velocity=0)))
    last_tick = max(last_tick, off)

for k, tp in enumerate(TEMPOS):
    if k * PPQ > last_tick:
        break
    if k == 0 or tp != TEMPOS[k - 1]:
        evs.append((k * PPQ, 0, mido.MetaMessage('set_tempo', tempo=tp)))

evs.sort(key=lambda e: (e[0], e[1]))

mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
cur = 0
for tick, _, msg in evs:
    msg.time = tick - cur
    cur = tick
    track.append(msg)
track.append(mido.MetaMessage('end_of_track', time=PPQ // 4))
mid.save('solo.mid')
