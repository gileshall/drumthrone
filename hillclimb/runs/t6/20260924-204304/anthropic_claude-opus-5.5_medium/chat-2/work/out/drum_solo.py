#!/usr/bin/env python3
"""
drum_solo.py - generates a two-minute General MIDI drum solo (solo.mid) on channel 10.

Only mido is used.  The output is deterministic: every random choice comes from
fixed-seed generators.

How the solo is built:
  * Motif A is a 3-3-2 accent cell (16th slots 0,3,6,8,11,14).  It is stated in
    the intro, then re-orchestrated, displaced, played at double speed and at
    half speed, hidden in the feet, answered on cowbell and woodblock, turned
    into accent patterns inside long 32nd-note runs, and finally used for the
    unison hits before the last roll.
  * Motif B is a hand-hand-foot triplet run that travels around the toms.
  * The music is written on a beat grid.  It is then rendered to real time
    through an expressive tempo map (surges, holds and phrase-level push and
    settle), a slow timing drift, and per-stroke timing and velocity
    humanisation (ghost notes sit slightly behind the beat, accents a hair ahead).
  * Every stroke belongs to a limb (R, L, right foot, left foot).  A final pass
    guarantees that no limb plays two notes too close together, so at most two
    hands and two feet strike at any instant.
"""
import math
import random
import mido

SEED = 7031
rng = random.Random(SEED)          # composition choices
hrng = random.Random(SEED + 1)     # humanisation

# ---------------- General MIDI percussion ----------------
KICK = 36; SN = 38; HHP = 44
CR1 = 49; CR2 = 57; RIDE = 51; BELL = 53; CHINA = 52; SPLASH = 55; COW = 56
T1 = 50; T2 = 48; T3 = 47; T4 = 45; F1 = 43; F2 = 41
WBH = 76; WBL = 77
DOWN = [T1, T2, T3, T4, F1, F2]
UP = DOWN[::-1]
AROUND = [SN, T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1]

MA = [0, 3, 6, 8, 11, 14]          # motif A: 3-3-2 + 3-3-2 in 16ths

EV = []                            # [beat, note, velocity, limb, dt_seconds]


def B(bar, beat=0.0):
    return bar * 4.0 + beat


def hit(b, note, vel, hand='R', dt=0.0):
    if note == KICK:
        limb = 'RF'
    elif note == HHP:
        limb = 'LF'
    else:
        limb = hand
    EV.append([b, note, float(vel), limb, dt])


def run(b0, sub, sticking, voice, v0, v1, acc=(), boost=28):
    """Play a sticking string.
    R/L = accented hand, r/l = normal hand, K/k = kick, f = hi-hat foot, '.' = rest.
    voice(i, hand, accented) returns the drum for stroke i.
    Velocity crescendos linearly from v0 to v1 across the run."""
    st = sticking.replace(' ', '')
    n = len(st)
    prev = None
    for i, c in enumerate(st):
        if c == '.':
            prev = None
            continue
        b = b0 + i * sub
        t = i / (n - 1) if n > 1 else 0.0
        base = v0 + (v1 - v0) * t
        if c in 'kK':
            hit(b, KICK, base + (boost if (c == 'K' or i in acc) else 0))
            prev = 'F'
            continue
        if c == 'f':
            hit(b, HHP, base * 0.6)
            continue
        hand = 'R' if c in 'Rr' else 'L'
        a = c.isupper() or i in acc
        v = base + boost if a else base
        if prev == hand and not a:
            v *= 0.88                  # second stroke of a double is a touch softer
        hit(b, voice(i, hand, a), v, hand)
        prev = hand


def along(route, n):
    return lambda i, h, a: route[min(len(route) - 1, i * len(route) // n)]


def const(note):
    return lambda i, h, a: note


def motifA(b0, voices, vel, ghost=0.0, kicks=(0,), hat=(4, 12), grid=0.25,
           shift=0, upto=16, gnote=SN):
    contour = [1.04, 0.86, 0.92, 1.08, 0.88, 0.97]
    acc = {(s + shift) % 16: k for k, s in enumerate(MA)}
    for s in range(upto):
        b = b0 + s * grid
        hand = 'R' if s % 2 == 0 else 'L'
        if s in acc:
            k = acc[s]
            hit(b, voices[k], vel * contour[k], hand)
            if voices[k] == SN and grid >= 0.25 and vel > 80:   # flam the snare accent
                hit(b, SN, vel * 0.35, 'L' if hand == 'R' else 'R', dt=-0.024)
        elif ghost and rng.random() < ghost:
            hit(b, gnote, rng.uniform(24, 40), hand)
    for s in kicks:
        if s < upto:
            hit(b0 + s * grid, KICK, vel * 0.92)
    for s in hat:
        if s < upto:
            hit(b0 + s * grid, HHP, 48)


def motif_runs(b0, accv, vel, fillroutes, fv0, fv1, left_acc=None, kick=True, fillnote=None):
    """Motif A accents (right hand + kick) with 32nd-note fills between them.
    Every gap holds an odd number of fill strokes, so the sticking always
    resolves L -> R into the next accent."""
    slots = MA + [16]
    for k in range(6):
        s, e = slots[k], slots[k + 1]
        ba = b0 + s * 0.25
        hit(ba, accv[k], vel * (1.0 if k in (0, 3) else 0.93), 'R')
        if kick:
            hit(ba, KICK, vel * 0.95)
        if left_acc and left_acc[k]:
            hit(ba, left_acc[k], vel * 0.9, 'L')
        nf = (e - s) * 2 - 1
        route = fillroutes[k % len(fillroutes)]
        for j in range(nf):
            t = j / max(1, nf - 1)
            note = fillnote if fillnote else route[min(len(route) - 1, int(t * len(route)))]
            hit(ba + (j + 1) * 0.125, note, fv0 + (fv1 - fv0) * t, 'L' if j % 2 == 0 else 'R')


def motif_32_run(b0, bars, path, v0, v1, groups, boost=24):
    """Long 32nd-note singles around the kit, with motif A as the accent pattern."""
    n = bars * 32
    acc = {i for i in range(n) if (i % 16) in MA}

    def voice(i, h, a):
        if a:
            return groups[(i // 16) % len(groups)][MA.index(i % 16)]
        return path[(i // 2) % len(path)]
    run(b0, 0.125, 'rl' * (n // 2), voice, v0, v1, acc=acc, boost=boost)


def ghost_groove(b0, rh_slots=None, rh_note=BELL, rh_vel=64, density=0.6,
                 crash=False, kick_keep=0.7, swing=0.035, bb_vel=92):
    """Quiet half-time groove: right-hand ostinato, left-hand ghost notes with a
    backbeat on 3, motif A carried by the kick, hi-hat foot on 2 and 4."""
    if rh_slots is None:
        rh_slots = [0, 4, 8, 12] + [s for s in (2, 6, 10, 14) if rng.random() < 0.45]
    used = set()
    for s in sorted(rh_slots):
        b = b0 + s * 0.25 + (swing if s % 2 else 0)
        note = rh_note.get(s, BELL) if isinstance(rh_note, dict) else rh_note
        if crash and s == 0:
            note, v = CR1, 100
        else:
            v = rh_vel * (1.12 if s % 8 == 0 else (0.9 if s % 4 else 1.0))
        hit(b, note, v, 'R')
        used.add(s)
    for s in range(16):
        b = b0 + s * 0.25 + (swing if s % 2 else 0)
        if s == 8:
            hit(b, SN, bb_vel, 'L')
            continue
        if s in used:
            continue
        if s % 2 == 1 and rng.random() < density:
            hit(b, SN, rng.uniform(22, 38), 'L')
        elif s % 4 == 2 and rng.random() < density * 0.3:
            hit(b, SN, rng.uniform(20, 30), 'L')
    for s in MA:
        if s == 0 or rng.random() < kick_keep:
            hit(b0 + s * 0.25 + (swing if s % 2 else 0), KICK,
                68 if s == 0 else rng.uniform(52, 66))
    for s in (4, 12):
        hit(b0 + s * 0.25, HHP, 52)


# =====================================================================
#                               THE SOLO
# =====================================================================

# ---------- A. Intro: state motif A (bars 0-7) ----------
motifA(B(0), [F2, T1, T2, SN, F1, T4], 92, ghost=0, kicks=(0,))
hit(B(1, 0), F1, 74, 'R'); hit(B(1, 0), KICK, 70)
hit(B(1, 0.75), T3, 58, 'L')
hit(B(1, 1.5), T4, 50, 'R')
hit(B(1, 1), HHP, 45); hit(B(1, 3), HHP, 45)
run(B(1, 2), 1 / 6, 'rl' * 6, const(SN), 18, 84)                    # swell into bar 2
motifA(B(2), [F2, T1, T2, SN, T3, F1], 97, ghost=0.3, kicks=(0, 8))
motifA(B(3), [F2, T1, T2, SN, T3, F1], 98, ghost=0.4, kicks=(0,), upto=8)
run(B(3, 2), 0.25, 'RlrlRlrl', along(DOWN, 8), 72, 100, boost=20)
hit(B(3, 2), KICK, 90); hit(B(3, 3), KICK, 96); hit(B(3, 3), HHP, 50)

motifA(B(4), [CR1, SN, F1, SN, SN, F2], 100, ghost=0.55, kicks=(0, 6, 11))
motifA(B(5), [SN, T2, SN, SN, F1, SN], 96, ghost=0.6, shift=2, kicks=(0, 2, 8, 13))
motifA(B(6), [F2, SN, T1, SN, F1, SPLASH], 100, ghost=0.5, kicks=(0, 6, 14))
motifA(B(7), [F2, T1, SN, SN, SN, SN], 98, ghost=0.45, kicks=(0,), upto=8, hat=(4,))
run(B(7, 2), 0.25, 'RLRRLRLL', along(DOWN, 8), 70, 98, acc={0, 4}, boost=18)
hit(B(7, 2.5), KICK, 80); hit(B(7, 3.5), KICK, 90)

# ---------- B. Travelling hands (bars 8-15) ----------
r8 = [T1, T1, T2, T2, T3, T3, T4, F1, F2, F2]


def v8(i, h, a):
    if i == 0:
        return CR1
    return r8[min(len(r8) - 1, i * len(r8) // 24)]


run(B(8), 1 / 6, 'rlk' * 8, v8, 82, 104, acc={0, 6, 12, 18}, boost=18)
hit(B(8), KICK, 110)
run(B(9), 1 / 6, 'rlk' * 4, lambda i, h, a: (UP[min(5, i // 2)] if h == 'R' else SN),
    84, 100, acc={0, 6}, boost=16)
hit(B(9, 2), CR2, 116, 'R'); hit(B(9, 2), KICK, 112); hit(B(9, 2.5), CHINA, 96, 'L')
hit(B(9, 3), HHP, 50)
run(B(9, 3.25), 0.25, 'lrl', const(SN), 38, 70)

pn = [T1, SN, F1, T2]
run(B(10), 0.25, 'RlrrLrllRlrrLrll', lambda i, h, a: pn[i // 4] if a else SN, 44, 58, boost=50)
hit(B(10, 0), KICK, 92); hit(B(10, 2), KICK, 88); hit(B(10, 2.5), KICK, 74)
hit(B(10, 1), HHP, 50); hit(B(10, 3), HHP, 50)

pd = [T1, T2, T4, F2]
run(B(11), 1 / 6, 'Rlrrll' * 4, lambda i, h, a: pd[i // 6] if a else SN, 42, 78, boost=42)
for q in range(4):
    hit(B(11, q), KICK, 86)

st12 = list('rrll' * 4)
for s in MA:
    st12[s] = st12[s].upper()
am12 = {0: F1, 3: T1, 6: T2, 8: SN, 11: T4, 14: CR1}
run(B(12), 0.25, ''.join(st12), lambda i, h, a: am12[i] if a else SN, 40, 50, boost=58)
hit(B(12, 0), KICK, 96); hit(B(12, 2), KICK, 92)
hit(B(12, 1), HHP, 50); hit(B(12, 3), HHP, 50)

run(B(13), 1 / 6, 'RllrrL' * 4,
    lambda i, h, a: (F1 if h == 'R' else (T2 if i < 12 else T1)) if a else SN,
    48, 84, boost=36)
for q in range(4):
    hit(B(13, q), KICK, 90)

run(B(14), 0.125, 'rl' * 8, along(AROUND[:8], 16), 70, 96, acc=set(MA), boost=26)
hit(B(14, 0), KICK, 96); hit(B(14, 1), KICK, 92)
motifA(B(14, 2), [CR1, T1, T2, SN, F1, F2], 106, ghost=0.7, kicks=(0, 8), hat=(), grid=0.125)

run(B(15), 1 / 6, 'Rlrlkk' * 2, along(DOWN, 12), 88, 104, boost=18)
run(B(15, 2), 0.125, 'rrll' * 4, const(SN), 55, 118)
hit(B(15, 2), KICK, 90); hit(B(15, 3), KICK, 100)

# ---------- C. Contrast: quiet ghost-note groove, motif in the feet (bars 16-23) ----------
ghost_groove(B(16), crash=True, density=0.55)
ghost_groove(B(17), density=0.65)
ghost_groove(B(18), rh_note=RIDE, density=0.7)
ghost_groove(B(19), rh_slots=MA, rh_note=COW, rh_vel=78, density=0.6)
ghost_groove(B(20), rh_slots=MA, rh_note={0: F1, 3: T1, 6: T2, 8: T3, 11: T4, 14: F2},
             rh_vel=70, density=0.5)
ghost_groove(B(21), rh_note=RIDE, density=0.75)
run(B(22), 0.25, 'rl' * 8, const(SN), 24, 58)
hit(B(22, 0), KICK, 60); hit(B(22, 2), KICK, 58)
hit(B(22, 1), HHP, 48); hit(B(22, 3), HHP, 48)
acc23 = {i for i in range(32) if (i % 16) in MA}
run(B(23), 0.125, 'rl' * 16, lambda i, h, a: DOWN[min(5, i // 6)] if a else SN,
    58, 104, acc=acc23, boost=20)
for q in range(4):
    hit(B(23, q), KICK, 70 + q * 8)

# ---------- D. Build (bars 24-31) ----------
accpos = {2 * s: k for k, s in enumerate(MA)}      # motif A at half speed
st24 = []
for i in range(32):
    h = 'r' if i % 2 == 0 else 'l'
    if i in accpos:
        st24.append(h.upper())
    elif rng.random() < 0.2 + 0.75 * i / 31:
        st24.append(h)
    else:
        st24.append('.')
av24 = [CR1, F1, CR2, SN, F2, CHINA]
fp24 = [T1, T2, T3, T4, F1, T4, T3, T2]
run(B(24), 0.25, ''.join(st24), lambda i, h, a: av24[accpos[i]] if a else fp24[(i // 2) % 8],
    60, 92, boost=36)
for i in accpos:
    hit(B(24) + i * 0.25, KICK, 112)
for bb in (1, 3, 5, 7):
    hit(B(24) + bb, HHP, 52)

run(B(26), 1 / 6, 'rlk' * 8, lambda i, h, a: (DOWN[(i // 3) % 6] if h == 'R' else SN),
    80, 98, acc={0, 6, 12, 18}, boost=18)
run(B(27), 1 / 6, 'rlk' * 4, lambda i, h, a: UP[min(5, i // 2)], 92, 104, acc={0, 6}, boost=16)
run(B(27, 2), 1 / 6, 'Rlrlkk' * 2, along([SN, T2, T4, F2], 12), 98, 114, boost=14)

for bar, accn in ((28, DOWN), (29, [F2, F1, T4, T3, T2, CR1])):
    run(B(bar), 0.25, 'rl' * 8, lambda i, h, a, accn=accn: accn[MA.index(i)] if a else SN,
        56, 66, acc=set(MA), boost=44)
    for e in range(8):
        hit(B(bar) + e * 0.5, KICK, 80 if e % 2 == 0 else 70)
    hit(B(bar, 1), HHP, 55); hit(B(bar, 3), HHP, 55)

run(B(30), 0.125, 'rl' * 16, const(SN), 34, 76)
for q in range(4):
    hit(B(30, q), KICK, 64 + q * 4)
acc31 = {i for i in range(24) if i % 3 == 0}
run(B(31), 0.125, 'rl' * 12, lambda i, h, a: DOWN[min(5, i // 4)] if a else SN,
    78, 108, acc=acc31, boost=16)
run(B(31, 3), 0.125, 'rl' * 4, along([T3, T4, F1, F2], 8), 106, 122)
for q in range(4):
    hit(B(31, q), KICK, 86 + q * 6)

# ---------- E. Climax (bars 32-41) ----------
motif_runs(B(32), [CR1, CR2, CR1, CHINA, CR2, CR1], 118,
           [DOWN, UP, DOWN[1:], UP[1:], DOWN, UP], 72, 100,
           left_acc=[None, None, None, SN, None, None])
motif_runs(B(33), [F2, F1, T4, SN, F1, CR1], 110, [DOWN], 30, 70, fillnote=SN)

groups1 = [[CR1, T1, T2, SN, F1, F2], [F2, T2, T3, SN, T4, CR2],
           [CR1, T3, T4, SN, F1, F2], [F2, F1, T4, SN, T2, CR2]]
motif_32_run(B(34), 2, AROUND, 66, 100, groups1)
for q in range(8):
    hit(B(34) + q, KICK, 96)
for q in range(4):
    hit(B(34) + q + 0.5, HHP, 55)
    hit(B(35) + q + 0.5, KICK, 84)

run(B(36), 0.125, 'rrll' * 4, lambda i, h, a: F1 if a else (T3 if h == 'R' else SN),
    80, 100, acc={0, 8}, boost=24)
hit(B(36, 0), KICK, 105); hit(B(36, 1), KICK, 105)
run(B(36, 2), 1 / 6, 'Rlrlkk' * 2, along(DOWN, 12), 96, 112, boost=16)
run(B(37), 0.125, 'Rlrlk' * 3 + 'R', along(DOWN, 16), 96, 110, boost=16)
run(B(37, 2), 1 / 6, 'Rlrlkk' * 2, along(UP, 12), 104, 118, boost=14)

motif_runs(B(38), [CHINA, SPLASH, CR2, CHINA, SPLASH, CR1], 116, [UP, DOWN], 60, 104,
           left_acc=[None, None, None, SN, None, None])

# bar 39: the big breath - one hit, silence, then motif A whispered
hit(B(39), CR1, 124, 'R'); hit(B(39), KICK, 122); hit(B(39), F2, 112, 'L')
hit(B(39, 1), HHP, 40); hit(B(39, 3), HHP, 45)
motifA(B(39, 2), [SN] * 6, 50, ghost=0.55, kicks=(), hat=(), grid=0.125)


def v40(i, h, a):
    if i < 24:
        return DOWN[min(5, i // 4)] if h == 'R' else SN
    return UP[min(5, (i - 24) // 4)]


run(B(40), 1 / 6, 'rlk' * 16, v40, 56, 118, acc=set(range(0, 48, 6)), boost=14)

# ---------- F. Return of the motif (bars 42-45) ----------
hit(B(42), KICK, 112)
motifA(B(42), [CR1, T1, T2, SN, F1, T4], 100, ghost=0.25, kicks=(0,))
motifA(B(43), [F2, T1, T2, SN, F1, T4], 90, ghost=0, kicks=(0,), upto=8, hat=(4,))
hit(B(43, 2), WBL, 82, 'R'); hit(B(43, 2.75), WBH, 72, 'L')
hit(B(43, 3.5), WBH, 88, 'R'); hit(B(43, 3.75), WBL, 60, 'L')
hit(B(43, 3), HHP, 50)
ghost_groove(B(44), density=0.6, rh_note=BELL)
run(B(45), 0.25, 'rl' * 4, const(SN), 28, 50)
run(B(45, 2), 0.125, 'rl' * 8, lambda i, h, a: DOWN[MA.index(i)] if a else SN,
    56, 112, acc=set(MA), boost=18)
for q in range(4):
    hit(B(45, q), KICK, 60 + q * 12)

# ---------- G. Finale (bars 46-52) ----------
motifA(B(46), [CR1, T1, T2, SN, T4, F2], 108, ghost=0.7, kicks=(0, 8), hat=(), grid=0.125)
motifA(B(46, 2), [CR2, T2, T3, SN, F1, F2], 112, ghost=0.7, kicks=(0, 6, 8), hat=(), grid=0.125)
hit(B(46, 1), HHP, 55); hit(B(46, 3), HHP, 55)
run(B(47), 1 / 6, 'rlk' * 6, lambda i, h, a: DOWN[min(5, i // 3)], 96, 110,
    acc={0, 6, 12}, boost=14)
run(B(47, 3), 1 / 6, 'Rlrlkk', along(UP, 6), 110, 120, boost=8)

groups2 = [[CR2, T4, T3, SN, T1, F2], [CR1, F1, T4, SN, T2, CR2],
           [CHINA, T1, T2, SN, F1, F2], [CR1, F2, F1, SN, T1, CR2]]
motif_32_run(B(48), 2, AROUND[::-1], 80, 120, groups2)
for q in range(4):
    hit(B(48, q), KICK, 100)
    hit(B(48, q + 0.5), HHP, 58)
for e in range(8):
    hit(B(49) + e * 0.5, KICK, 96 + e * 2)

# bar 50: unison hits on motif A with silence between them
for k, s in enumerate(MA):
    b = B(50) + s * 0.25
    hit(b, [CR1, CR2][k % 2], 118 + k, 'R')
    hit(b, SN, 112 + k, 'L')
    hit(b, KICK, 118 + k)
hit(B(50, 1), HHP, 55); hit(B(50, 3), HHP, 55)

run(B(51), 1 / 6, 'rl' * 9, along(DOWN, 18), 92, 116, acc={0, 6, 12}, boost=10)
for q in range(3):
    hit(B(51, q), KICK, 104 + q * 6)
run(B(51, 3), 0.125, 'rlrlrlrl', lambda i, h, a: [SN, SN, T4, T4, F1, F1, F2, F2][i], 104, 124)
hit(B(51, 3), KICK, 112); hit(B(51, 3.5), KICK, 118)

FINAL_BEAT = B(52)
hit(FINAL_BEAT, CR1, 127, 'R')
hit(FINAL_BEAT, CR2, 127, 'L')
hit(FINAL_BEAT, KICK, 127)

# =====================================================================
#                    PERFORMANCE: tempo map and humanising
# =====================================================================
TK = [(0, 98), (16, 102), (32, 104), (48, 106), (63.5, 110), (64, 102), (88, 103),
      (95.5, 108), (96, 106), (120, 110), (127.5, 115), (128, 112), (152, 114),
      (156, 110), (158, 106), (160, 111), (167.5, 115), (168, 106), (183.5, 110),
      (184, 110), (200, 116), (204, 113), (207.5, 103), (208, 100), (216, 100)]


def bpm_at(b):
    if b <= TK[0][0]:
        v = TK[0][1]
    elif b >= TK[-1][0]:
        v = TK[-1][1]
    else:
        v = TK[-1][1]
        for (b1, v1), (b2, v2) in zip(TK, TK[1:]):
            if b1 <= b <= b2:
                v = v1 + (v2 - v1) * (b - b1) / (b2 - b1)
                break
    p = (b % 16.0) / 16.0                    # 4-bar phrase: push mid-phrase, settle at edges
    return v * (1 + 0.012 * math.sin(math.pi * p) ** 2 - 0.004)


STEP = 1.0 / 96
NSTEPS = int(220 / STEP)
cum = [0.0]
for i in range(NSTEPS):
    cum.append(cum[-1] + 60.0 / bpm_at((i + 0.5) * STEP) * STEP)


def sec(b):
    x = max(0.0, b) / STEP
    i = min(int(x), NSTEPS - 1)
    f = x - i
    return cum[i] + (cum[i + 1] - cum[i]) * f


OFFSET = 0.4
SCALE = 117.0 / sec(FINAL_BEAT)              # final hit lands at ~117.4 s, rings to ~120 s

DR = [hrng.gauss(0, 0.004) for _ in range(240)]


def drift(b):
    x = max(0.0, b) / 2.0
    i = int(x)
    f = x - i
    return DR[i] * (1 - f) + DR[i + 1] * f


perf = []
for b, note, vel, limb, dt in EV:
    t = OFFSET + sec(b) * SCALE + dt + drift(b)
    ghost = vel < 48
    if limb in ('RF', 'LF'):
        sd, bias = 0.004, 0.0
    else:
        sd = 0.0095 if ghost else 0.0055
        bias = (0.004 if ghost else 0.0) + (0.002 if limb == 'L' else 0.0)
        if vel > 100:
            bias -= 0.003                    # accents lean slightly ahead
    j = max(-2.5 * sd, min(2.5 * sd, hrng.gauss(0, sd)))
    if b >= FINAL_BEAT:
        j *= 0.3
    t = max(0.0, t + bias + j)
    v = vel + hrng.gauss(0, 3 if ghost else 4.5)
    if b >= FINAL_BEAT:
        v = 127
    perf.append([t, note, max(1, min(127, int(round(v)))), limb])

# ---- playability: one stroke per limb at a time, with a realistic minimum gap ----
perf.sort(key=lambda e: (e[0], -e[2]))
MIN = {'R': 0.045, 'L': 0.045, 'RF': 0.07, 'LF': 0.1}
OTHER = {'R': 'L', 'L': 'R'}
last = {k: -9.0 for k in MIN}
lastidx = {k: None for k in MIN}
keep = [True] * len(perf)
for i, e in enumerate(perf):
    t, note, v, limb = e
    if t - last[limb] >= MIN[limb]:
        pass
    elif limb in ('R', 'L') and t - last[OTHER[limb]] >= MIN[OTHER[limb]]:
        limb = OTHER[limb]
        e[3] = limb
    else:
        jx = lastidx[limb]
        if jx is not None and v > perf[jx][2] + 8:
            keep[jx] = False
        else:
            keep[i] = False
            continue
    last[limb] = t
    lastidx[limb] = i

# =====================================================================
#                               WRITE MIDI
# =====================================================================
TPB = 960
TPS = 2 * TPB                                # 120 bpm file tempo -> 1920 ticks per second
d = {}
for e, k in zip(perf, keep):
    if not k:
        continue
    tk = int(round(e[0] * TPS))
    key = (tk, e[1])
    d[key] = max(e[2], d.get(key, 0))

final_tick = max(tk for tk, _ in d)
by_note = {}
for (tk, n), v in d.items():
    by_note.setdefault(n, []).append((tk, v))

msgs = []
for n, lst in by_note.items():
    lst.sort()
    for idx, (tk, v) in enumerate(lst):
        dur = int(2.5 * TPS) if tk >= final_tick - 100 else int(0.12 * TPS)
        if idx + 1 < len(lst):
            dur = min(dur, lst[idx + 1][0] - tk - 1)
        dur = max(dur, 1)
        msgs.append((tk, 1, n, mido.Message('note_on', channel=9, note=n, velocity=v)))
        msgs.append((tk + dur, 0, n, mido.Message('note_off', channel=9, note=n, velocity=0)))
msgs.sort(key=lambda x: (x[0], x[1], x[2]))

mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
track.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
track.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
track.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))

now = 0
for tk, _, _, m in msgs:
    track.append(m.copy(time=tk - now))
    now = tk
track.append(mido.MetaMessage('end_of_track', time=int(0.05 * TPS)))

mid.save('solo.mid')
print('wrote solo.mid: %d notes, %.1f s' % (len(d), mid.length))
