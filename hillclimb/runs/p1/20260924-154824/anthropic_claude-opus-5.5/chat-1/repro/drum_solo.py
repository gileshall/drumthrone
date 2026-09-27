#!/usr/bin/env python3
"""
drum_solo.py - generates solo.mid, a ~2 minute General MIDI drum solo (channel 10).

Structure (bars of 4/4):
  0-3    Intro: main motif stated sparsely on toms, answered, fragment + fill
  4-11   Swung groove, laid-back backbeat, ghost notes, kick borrows motif rhythm
  12-19  Development: motif re-voiced, displaced, tresillo'd, crossed in 3s,
         paradiddles / paradiddle-diddles around the kit, roll swell into downbeat
  20-27  Release: Latin interlude (cowbell, clave, tumbao), motif on timbales/congas
  28-39  Build: triplet ride feel + hemiola, travelling doubles in sextuplets,
         motif returns loud, long roll swell (tempo leans forward)
  40-49  Climax: double bass, motif as unison cymbal/drum hits, cross-rhythms,
         sudden breakdown, then six-stroke rolls and 32nd runs
  50-56  Recap: motif returns softly as in the intro, grows, final roll + hit
Every note is assigned to a limb (R, L hands; RF, LF feet) so at most two
hands and two feet ever strike at once.
"""
import random
import mido

PPQ = 480
TARGET_SECONDS = 118.5          # time of the final hit
rng = random.Random(19660713)   # fixed seed -> identical output every run

# ---- General MIDI percussion ----
ABD = 35; KICK = 36; SIDE = 37; SNARE = 38; CLAP = 39
TOM_FL = 41; HHC = 42; TOM_FH = 43; HHP = 44; TOM_L = 45; HHO = 46
TOM_LM = 47; TOM_HM = 48; CRASH = 49; TOM_H = 50; RIDE = 51; CHINA = 52
BELL = 53; TAMB = 54; SPLASH = 55; COWBELL = 56; CRASH2 = 57; RIDE2 = 59
HBONGO = 60; LBONGO = 61; MCONGA = 62; OCONGA = 63; LCONGA = 64
HTIMB = 65; LTIMB = 66; HAGOGO = 67; LAGOGO = 68; CABASA = 69
CLAVES = 75; HWOOD = 76; LWOOD = 77; MTRI = 80; OTRI = 81

FOOT_NOTES = {ABD, KICK, HHP}
CYMS = {HHC, HHO, RIDE, BELL, CRASH, CRASH2, CHINA, SPLASH, COWBELL, RIDE2,
        HAGOGO, LAGOGO, OTRI, MTRI}

EVENTS = []  # (beat, limb, note, vel, swingable)


def hit(beat, limb, note, vel, sw=True):
    if limb in ('RF', 'LF'):
        assert note in FOOT_NOTES
    else:
        assert limb in ('R', 'L') and note not in FOOT_NOTES
    EVENTS.append((beat, limb, note, float(vel), sw))


def B(bar, step, div=4):
    return bar * 4 + step / div


def T(bar, t):  # 8th-note triplet grid (12 per bar)
    return bar * 4 + t / 3


def run(start, n, div, stick, notes, v0, v1, acc=None, boost=22, curve=1.0,
        kick_acc=False):
    sw = div in (2, 4)
    for i in range(n):
        b = start + i / div
        limb = stick[i % len(stick)]
        note = notes(i) if callable(notes) else notes[i % len(notes)]
        f = (i / (n - 1)) if n > 1 else 1.0
        v = v0 + (v1 - v0) * (f ** curve)
        is_acc = acc(i) if acc else False
        if is_acc:
            v += boost
        elif i > 0 and stick[(i - 1) % len(stick)] == limb:
            v *= 0.88  # second stroke of a double is a touch softer
        hit(b, limb, note, v, sw)
        if is_acc and kick_acc:
            hit(b, 'RF', KICK, min(v, 118), sw)


def flam(beat, limb, note, vel, grace=None):
    other = 'L' if limb == 'R' else 'R'
    hit(beat - 0.04, other, grace or note, vel * 0.4, sw=False)
    hit(beat, limb, note, vel, sw=False)


def hh_foot(bar, steps, vel):
    for s in steps:
        hit(B(bar, s), 'LF', HHP, vel)


def kicks(bar, steps, vel, limb='RF'):
    for s in steps:
        hit(B(bar, s), limb, KICK, vel)


def dbl_bass(bar, von=100, voff=84, start=0, end=16):
    for s in range(start, end):
        hit(B(bar, s), 'RF' if s % 2 == 0 else 'LF', KICK, von if s % 4 == 0 else voff)


# ---- Motif material ----
TOMS = dict(low=TOM_FL, high=TOM_H, mid=TOM_LM, snare=SNARE)
TOMS2 = dict(low=TOM_L, high=TOM_HM, mid=TOM_FH, snare=SNARE)
TIMB = dict(low=LTIMB, high=HTIMB, mid=OCONGA, snare=COWBELL)
CONGA = dict(low=LCONGA, high=OCONGA, mid=MCONGA, snare=HBONGO)

MOTIF = [(0, 'low', 1.0), (3, 'high', 0.8), (6, 'snare', 0.95),
         (10, 'mid', 0.8), (11, 'mid', 0.66), (14, 'snare', 0.9)]
MOTIF_KICK = (0, 8)
ANSWER = [(4, 'mid', 0.8), (6, 'high', 0.9), (7, 'high', 0.72), (12, 'low', 1.0)]
ANSWER_KICK = (0, 12)
TRESILLO = [(0, 'low', 1.0), (3, 'high', 0.8), (6, 'snare', 0.95),
            (8, 'low', 0.95), (11, 'high', 0.8), (14, 'snare', 1.0)]
DESC = [TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL]
ASC = DESC[::-1]


def motif(bar, voice, base, cells=MOTIF, shift=0, kick=True, kick_steps=MOTIF_KICK,
          ghosts=None, fill=SNARE, gvel=30, crash0=False, cresc=0.0):
    used = set()
    for step, role, a in cells:
        s = step + shift
        limb = 'R' if s % 2 == 0 else 'L'
        v = base * a * (1 + cresc * s / 16)
        note = voice[role]
        if s == 0 and crash0:
            hit(B(bar, 0), 'R', CRASH, v + 10)
            hit(B(bar, 0), 'L', note, v)
        else:
            hit(B(bar, s), limb, note, v)
        used.add(s)
    if kick:
        for ks in kick_steps:
            k = ks + shift
            hit(B(bar, k), 'RF', KICK, base * 0.85 * (1 + cresc * k / 16))
    if ghosts is not None:
        gs = range(16) if ghosts == 'all' else ghosts
        for s in gs:
            if s in used:
                continue
            limb = 'R' if s % 2 == 0 else 'L'
            fn = fill(s) if callable(fill) else fill
            hit(B(bar, s), limb, fn, gvel * (1 + cresc * s / 16) + (4 if s % 4 == 0 else 0))


MOTIF_ACC = {c[0]: c[2] for c in MOTIF}
BIG = {0: (CRASH, TOM_FL), 3: (CHINA, TOM_H), 6: (CRASH2, SNARE),
       10: (TOM_HM, TOM_LM), 11: (TOM_HM, TOM_LM), 14: (CRASH, SNARE)}


def big_motif(bar, base, fill_hands=False):
    for s, (r, l) in BIG.items():
        a = MOTIF_ACC[s]
        hit(B(bar, s), 'R', r, base * a + 8)
        hit(B(bar, s), 'L', l, base * a)
    if fill_hands:
        path = [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, TOM_FL]
        for s in range(16):
            if s in BIG:
                continue
            hit(B(bar, s), 'R' if s % 2 == 0 else 'L', path[s // 2], 62 + s)


# =================== COMPOSITION ===================

# ---- Section 1: Intro (bars 0-3) ----
for bar in range(4):
    hh_foot(bar, (4, 12), 50)
motif(0, TOMS, 70)
motif(1, TOMS, 64, cells=ANSWER, kick_steps=ANSWER_KICK)
motif(2, TOMS, 80, ghosts=(1, 5, 9, 13, 15), gvel=26)
motif(3, TOMS, 86, cells=MOTIF[:3], kick_steps=(0,))
run(B(3, 8), 8, 4, 'RL', [SNARE, SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL],
    62, 100, acc=lambda i: i % 2 == 0, boost=10)
kicks(3, (8,), 75)
hit(B(3, 12), 'RF', KICK, 82)

# ---- Section 2: Groove (bars 4-11) ----
GHOSTS = [(7, 9, 15), (3, 7, 10, 11), (7, 9, 13, 15), (1, 3, 7, 11, 15)]
KPAT = [(0, 6, 8, 10), (0, 3, 6, 10, 14), (0, 6, 8, 11), (0, 3, 8, 10)]
for k, bar in enumerate(range(4, 12)):
    g = 0.82 + 0.18 * k / 7
    end = 8 if bar in (7, 11) else 16
    for s in range(0, end, 2):
        if s == 0 and bar in (4, 8):
            hit(B(bar, 0), 'R', CRASH, 112 * g)
        elif s == 14 and bar in (5, 9):
            hit(B(bar, s), 'R', HHO, 88 * g)
        else:
            hit(B(bar, s), 'R', HHC, (90 if s % 4 == 0 else 60) * g)
    if bar in (6, 10):
        hit(B(bar, 0), 'LF', HHP, 70)
    for s in (4, 12):
        if s < end:
            hit(B(bar, s), 'L', SNARE, 108 * g)
    for s in GHOSTS[k % 4]:
        if s < end:
            hit(B(bar, s), 'L', SNARE, 29 + (5 if s in (7, 15) else 0))
    for s in KPAT[k % 4]:
        if s < end:
            hit(B(bar, s), 'RF', KICK, (100 if s in (0, 8) else 84) * g)
run(B(7, 8), 8, 4, 'RL', [SNARE, SNARE, TOM_H, TOM_H, TOM_LM, TOM_LM, TOM_FL, TOM_FL],
    70, 102, acc=lambda i: i in (0, 2, 6), boost=14)
kicks(7, (8, 14), 90)
F11 = [SNARE, TOM_H, TOM_HM, SNARE, TOM_HM, TOM_LM, SNARE, TOM_LM, TOM_L, SNARE, TOM_L, TOM_FL]
run(B(11, 8), 12, 6, 'RL', F11, 72, 108, acc=lambda i: i % 3 == 0, boost=14)
kicks(11, (8, 12), 95)

# ---- Section 3: Development (bars 12-19) ----
for bar in range(12, 20):
    hh_foot(bar, (4, 12), 52)
for bar in range(12, 18):
    kicks(bar, (0, 4, 8, 12), 54)  # feathered
motif(12, TOMS, 96, ghosts='all', gvel=30, crash0=True)
motif(13, TOMS2, 98, ghosts='all', gvel=31)
CROSS = [(0, TOM_H), (3, TOM_HM), (6, TOM_LM), (9, TOM_L), (12, TOM_FL)]
for s, n in CROSS:
    hit(B(14, s), 'R' if s % 2 == 0 else 'L', n, 100)
for s in range(16):
    if s not in (0, 3, 6, 9, 12):
        hit(B(14, s), 'R' if s % 2 == 0 else 'L', SNARE, 30 + (20 if s in (14, 15) else 0))
kicks(14, (0, 6, 12), 88)


def pd_note(i):
    if i % 8 == 0:
        return TOM_FL
    if i % 8 == 4:
        return TOM_H
    return SNARE


run(B(15, 0), 16, 4, 'RLRRLRLL', pd_note, 40, 52, acc=lambda i: i % 4 == 0, boost=50)
motif(16, TOMS, 100, shift=2, ghosts='all', gvel=32)
motif(17, TOMS, 102, cells=TRESILLO, kick_steps=(0, 8), ghosts='all', gvel=33)
PDD_T = [TOM_H, TOM_HM, TOM_LM, TOM_FL]


def pdd(i):
    g, k = divmod(i, 6)
    return PDD_T[g % 4] if k in (0, 2, 3) else SNARE


run(B(18, 0), 24, 6, 'RLRRLL', pdd, 55, 92, acc=lambda i: i % 6 == 0, boost=20)
kicks(18, (0, 4, 8, 12), 70)
run(B(19, 0), 24, 8, 'RL', [SNARE], 28, 104, curve=1.6, acc=lambda i: i % 8 == 0, boost=8)
run(B(19, 12), 6, 6, 'RL', DESC, 104, 118, acc=lambda i: i % 2 == 0, boost=6)
for j, s in enumerate((0, 4, 8, 12)):
    hit(B(19, s), 'RF', KICK, 50 + j * 18)
hit(B(19, 14), 'RF', KICK, 105)

# ---- Section 4: Release / Latin interlude (bars 20-27) ----
hit(B(20, 0), 'R', CRASH, 120)
hit(B(20, 0), 'L', TOM_FL, 112)
hit(B(20, 0), 'RF', KICK, 122)
hh_foot(20, (8, 12), 48)
hit(B(20, 8), 'R', OTRI, 52)
for bar in range(21, 28):
    kicks(bar, (6, 12), 72)  # tumbao
    hh_foot(bar, (4, 12), 54)
for bar in range(24, 28):
    kicks(bar, (0,), 78)
for bar in (21, 22, 23):
    for s in (0, 4, 8, 12):
        hit(B(bar, s), 'R', COWBELL, 86 if s == 0 else 74)
    for s in (6, 14):
        hit(B(bar, s), 'R', COWBELL, 56)
    for s in ((0, 6, 12) if bar != 22 else (4, 8)):
        hit(B(bar, s), 'L', CLAVES, 80)
    if bar in (22, 23):
        hit(B(bar, 10), 'L', LCONGA, 60)
        hit(B(bar, 11), 'L', LCONGA, 48)
motif(24, TIMB, 88, kick=False, ghosts=(1, 5, 9, 13), fill=LCONGA, gvel=38)
motif(25, CONGA, 80, cells=ANSWER, kick=False, ghosts=(1, 9, 13, 15), fill=MCONGA, gvel=36)
hit(B(25, 0), 'R', HAGOGO, 78)
hit(B(25, 8), 'R', LAGOGO, 72)
motif(26, TIMB, 94, kick=False, ghosts=(1, 5, 9, 13, 15), fill=LCONGA, gvel=40)
motif(27, TIMB, 98, cells=MOTIF[:3], kick=False)
run(B(27, 8), 8, 4, 'RL', [HTIMB, HTIMB, HTIMB, LTIMB, HTIMB, LTIMB, LTIMB, LTIMB],
    72, 108, acc=lambda i: i in (0, 3, 6), boost=12)

# ---- Section 5: Build (bars 28-39) ----
RIDE_T = (0, 3, 5, 6, 9, 11)
ACC28 = {28: {4: 92, 10: 100}, 29: {2: 88, 4: 96, 10: 102},
         30: {2: 98, 6: 100, 10: 104}, 31: {2: 90, 4: 96}}
KIK28 = {28: (0, 7), 29: (0, 6, 11), 30: (0, 4, 8), 31: (0,)}
for bar in range(28, 32):
    end = 6 if bar == 31 else 12
    for t in RIDE_T:
        if t >= end:
            continue
        if bar == 28 and t == 0:
            hit(T(bar, t), 'R', CRASH, 112, False)
            continue
        hit(T(bar, t), 'R', RIDE, (84 if t % 3 == 0 else 62) + (6 if t in (3, 9) else 0), False)
    acc = ACC28[bar]
    for t in range(end):
        if t in acc:
            hit(T(bar, t), 'L', SNARE, acc[t], False)
        elif t % 3 == 1:
            hit(T(bar, t), 'L', SNARE, 27, False)
        elif t in (2, 8):
            hit(T(bar, t), 'L', SNARE, 22, False)
    for t in KIK28[bar]:
        hit(T(bar, t), 'RF', KICK, 88, False)
    for t in (3, 9):
        if t < end:
            hit(T(bar, t), 'LF', HHP, 62, False)
run(B(31, 8), 12, 6, 'RL',
    [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_FL, TOM_FL],
    80, 114, acc=lambda i: i % 3 == 0, boost=10)
hit(T(31, 6), 'RF', KICK, 96, False)
hit(T(31, 9), 'RF', KICK, 100, False)


def doubles_bar(bar, path, v0, v1, kick_acc=False):
    def nt(i, path=path):
        g, k = divmod(i, 4)
        first = path[g % len(path)]
        if k == 0:
            return first
        if k == 1:
            return first if first not in CYMS else DESC[g % 6]
        return SNARE
    run(B(bar, 0), 24, 6, 'RRLL', nt, v0, v1, acc=lambda i: i % 4 == 0, boost=26,
        kick_acc=kick_acc)


doubles_bar(32, [CRASH, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL], 50, 64)
doubles_bar(33, ASC, 56, 72)
doubles_bar(34, [CRASH, CHINA, CRASH2, CHINA, CRASH, CHINA], 62, 80, kick_acc=True)
F35 = [SNARE, TOM_H, TOM_HM, SNARE, TOM_HM, TOM_LM,
       SNARE, TOM_LM, TOM_L, SNARE, TOM_L, TOM_FL,
       TOM_FL, TOM_FH, TOM_L, TOM_L, TOM_LM, TOM_HM,
       TOM_HM, TOM_H, SNARE, SNARE, SNARE, SNARE]
run(B(35, 0), 24, 6, 'RL', F35, 70, 116, acc=lambda i: i % 3 == 0, boost=10)
for bar in (32, 33):
    kicks(bar, (0, 4, 8, 12), 84)
for bar in range(32, 36):
    hh_foot(bar, (4, 12), 60)
for j, s in enumerate(range(0, 16, 2)):
    hit(B(35, s), 'RF', KICK, 80 + j * 3)
motif(36, TOMS, 108, ghosts='all', gvel=34, crash0=True)
motif(37, TOMS2, 112, ghosts='all', gvel=36, crash0=True)
for bar in (36, 37):
    hh_foot(bar, (0, 4, 8, 12), 60)
    kicks(bar, (0, 4, 8, 12), 60)
run(B(38, 0), 32, 8, 'RL', [SNARE], 24, 70, curve=1.3, acc=lambda i: i % 8 == 0, boost=6)
kicks(38, (0, 4, 8, 12), 62)
hh_foot(38, (4, 12), 56)
run(B(39, 0), 24, 8, 'RL', [SNARE], 72, 112, acc=lambda i: i % 8 == 0, boost=8)
run(B(39, 12), 8, 8, 'RL', [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL],
    110, 122, acc=lambda i: i % 2 == 0, boost=4)
for j, s in enumerate(range(0, 16, 2)):
    hit(B(39, s), 'RF', KICK, 70 + j * 6)
hh_foot(39, (4,), 58)

# ---- Section 6: Climax (bars 40-49) ----
dbl_bass(40)
big_motif(40, 110)
dbl_bass(41)
F41 = [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM,
       TOM_L, TOM_L, TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_FL, TOM_FL]
motif(41, TOMS, 112, kick=False, ghosts='all', fill=lambda s: F41[s], gvel=60, crash0=True)
dbl_bass(42)
for s, r, l in [(0, CRASH, TOM_FL), (3, CHINA, SNARE), (6, CRASH2, TOM_L),
                (9, CHINA, SNARE), (12, CRASH, TOM_FL)]:
    hit(B(42, s), 'R', r, 118)
    hit(B(42, s), 'L', l, 110)
hit(B(42, 14), 'R', SNARE, 100)
hit(B(42, 15), 'L', SNARE, 106)
kicks(43, (0, 4, 8, 12), 100)
hit(B(43, 14), 'RF', KICK, 110)
run(B(43, 0), 16, 8, 'RL',
    [SNARE, SNARE, SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM,
     TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_FH, TOM_FH, TOM_FL, TOM_FL],
    96, 116, acc=lambda i: i % 4 == 0, boost=8)
for j, (s, n) in enumerate([(8, SNARE), (9, TOM_H), (10, TOM_LM), (11, TOM_FL)]):
    flam(B(43, s), 'R' if j % 2 == 0 else 'L', n, 112)
for s, limb, n, v in [(12, 'R', SNARE, 108), (13, 'L', SNARE, 100),
                      (14, 'R', TOM_FL, 116), (15, 'L', TOM_FL, 110)]:
    hit(B(43, s), limb, n, v)
# breakdown
hit(B(44, 0), 'R', CRASH, 124)
hit(B(44, 0), 'L', CRASH2, 118)
hit(B(44, 0), 'RF', KICK, 124)
run(B(44, 8), 8, 4, 'RL', [SNARE], 18, 42)
hh_foot(44, (8, 12), 50)
motif(45, TOMS, 64, ghosts='all', gvel=26, cresc=0.6)
hh_foot(45, (4, 12), 56)
S46 = [[SNARE, TOM_H, TOM_HM], [SNARE, TOM_HM, TOM_LM],
       [SNARE, TOM_LM, TOM_L], [SNARE, TOM_L, TOM_FL]]
run(B(46, 0), 24, 6, 'RL',
    lambda i: CRASH if i == 0 else S46[(i // 3) % 4][i % 3],
    92, 112, acc=lambda i: i % 3 == 0, boost=12, kick_acc=True)
hh_foot(46, (4, 12), 60)
SIX_T = [TOM_FL, TOM_L, TOM_LM, TOM_H]
run(B(47, 0), 24, 6, 'RLLRRL',
    lambda i: SIX_T[i // 6] if i % 6 == 0 else SNARE,
    70, 90, acc=lambda i: i % 6 in (0, 5), boost=30)
dbl_bass(47, 96, 80)
dbl_bass(48, 104, 88)
big_motif(48, 118, fill_hands=True)
dbl_bass(49, 104, 90)
P49 = [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, SNARE]
run(B(49, 0), 32, 8, 'RL', lambda i: P49[i // 4], 96, 122, acc=lambda i: i % 4 == 0, boost=6)

# ---- Section 7: Recap & ending (bars 50-56) ----
hit(B(50, 0), 'R', CRASH, 124)
hit(B(50, 0), 'L', TOM_FL, 116)
hit(B(50, 0), 'RF', KICK, 124)
hh_foot(50, (8, 12), 46)
for bar in range(51, 55):
    hh_foot(bar, (4, 12), 50)
motif(51, TOMS, 60)
motif(52, TOMS, 66, cells=ANSWER, kick_steps=ANSWER_KICK)
motif(53, TOMS, 84, ghosts='all', gvel=27)
motif(54, TOMS2, 104, ghosts='all', gvel=32, crash0=True)
run(B(55, 0), 24, 8, 'RL', [SNARE], 36, 112, curve=1.4, acc=lambda i: i % 8 == 0, boost=6)
for j, s in enumerate((0, 4, 8)):
    hit(B(55, s), 'RF', KICK, 70 + j * 18)
flam(B(55, 12), 'R', TOM_FL, 118, grace=SNARE)
hit(B(55, 12), 'RF', KICK, 112)
hit(B(55, 14), 'R', TOM_FL, 120)
hit(B(55, 14), 'L', SNARE, 118)
hit(B(55, 14), 'RF', KICK, 116)
hit(B(56, 0), 'R', CRASH, 127)
hit(B(56, 0), 'L', CRASH2, 124)
hit(B(56, 0), 'RF', KICK, 127)
FINAL_BEAT = 56 * 4

# =================== PERFORMANCE / RENDER ===================
CP = [(0, 94), (4, 98), (8, 100), (11, 103), (12, 102), (17, 106), (19.99, 110),
      (20, 100), (22, 95), (26, 96), (27.99, 99), (28, 100), (31, 104), (32, 106),
      (35, 112), (38, 114), (39.99, 119), (40, 120), (43.99, 124), (44, 110),
      (45, 112), (46, 118), (49.99, 126), (50, 112), (51, 104), (53, 102),
      (54, 104), (55, 98), (56, 76)]


def bpm_at(barpos):
    if barpos <= CP[0][0]:
        return CP[0][1]
    for (b0, v0), (b1, v1) in zip(CP, CP[1:]):
        if b0 <= barpos <= b1:
            return v0 + (v1 - v0) * (barpos - b0) / (b1 - b0)
    return CP[-1][1]


def section_params(bar):
    if bar < 4:
        return 0.05, dict(cym=-3, back=8, ghost=3, kick=0)
    if bar < 12:
        return 0.045, dict(cym=-4, back=10, ghost=3, kick=2)
    if bar < 20:
        return 0.03, dict(cym=-4, back=5, ghost=2, kick=0)
    if bar < 28:
        return 0.0, dict(cym=-3, back=0, ghost=2, kick=-3)
    if bar < 36:
        return 0.0, dict(cym=-5, back=6, ghost=3, kick=0)
    if bar < 40:
        return 0.0, dict(cym=-5, back=0, ghost=2, kick=0)
    if bar < 50:
        return 0.0, dict(cym=-6, back=-3, ghost=1, kick=-2)
    return 0.05, dict(cym=-3, back=8, ghost=3, kick=0)


def warp(beat, d):
    if d == 0:
        return beat
    base = int(beat * 2) / 2.0
    u = beat - base
    if u < 0.25:
        u2 = u * (0.25 + d) / 0.25
    else:
        u2 = 0.25 + d + (u - 0.25) * (0.25 - d) / 0.25
    return base + u2


def offset(feel, note, vel):
    o = 0
    if note in CYMS:
        o += feel['cym']
    if note in (SNARE, SIDE, CLAP) and vel >= 85:
        o += feel['back']
    if vel < 50:
        o += feel['ghost']
    if note in (KICK, ABD):
        o += feel['kick']
    return o


notes = []
for beat, limb, note, vel, sw in EVENTS:
    bar = int(beat // 4)
    swing, feel = section_params(bar)
    w = warp(beat, swing if sw else 0.0)
    t = int(round(w * PPQ)) + offset(feel, note, vel) + rng.choice((-1, 0, 0, 1))
    t = max(0, t)
    spread = 2 if vel < 40 else 3
    v = int(round(vel + rng.uniform(-spread, spread)))
    v = max(1, min(127, v))
    notes.append((t, limb, note, v))

LIMB_ORDER = {'RF': 0, 'LF': 1, 'R': 2, 'L': 3}
notes.sort(key=lambda x: (x[0], LIMB_ORDER[x[1]], x[2], x[3]))
kept = []
last = {}
for n in notes:
    t, limb, note, v = n
    if limb in last:
        j = last[limb]
        if t - kept[j][0] < 30:          # one limb can't strike twice that fast
            if v > kept[j][3]:
                kept[j] = n
            continue
    last[limb] = len(kept)
    kept.append(n)
kept.sort(key=lambda x: (x[0], LIMB_ORDER[x[1]], x[2], x[3]))

# durations: short, never overlapping the next stroke of the same pitch
by_pitch = {}
for t, limb, note, v in kept:
    by_pitch.setdefault(note, []).append(t)
for p in by_pitch:
    by_pitch[p].sort()

msgs = []
for t, limb, note, v in kept:
    ts = by_pitch[note]
    idx = ts.index(t)
    nxt = None
    for k in range(idx + 1, len(ts)):
        if ts[k] > t:
            nxt = ts[k]
            break
    dur = 30 if nxt is None else max(1, min(30, nxt - t - 1))
    msgs.append((t, 1, note, mido.Message('note_on', channel=9, note=note, velocity=v)))
    msgs.append((t + dur, 0, note, mido.Message('note_off', channel=9, note=note, velocity=0)))
msgs.sort(key=lambda x: (x[0], x[1], x[2]))

# tempo map: one tempo per beat, scaled so the final hit lands at TARGET_SECONDS
end_tick = max(m[0] for m in msgs) + 2 * PPQ
n_beats = end_tick // PPQ + 2
raw = [bpm_at((k + 0.5) / 4.0) for k in range(n_beats)]
raw_secs = sum(60.0 / raw[k] for k in range(FINAL_BEAT))
scale = raw_secs / TARGET_SECONDS
bpms = [r * scale for r in raw]

mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
tempo_track = mido.MidiTrack()
tempo_track.append(mido.MetaMessage('track_name', name='Tempo', time=0))
tempo_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
prev = 0
for k in range(n_beats):
    tick = k * PPQ
    tempo_track.append(mido.MetaMessage('set_tempo', tempo=int(round(60000000.0 / bpms[k])),
                                        time=tick - prev))
    prev = tick
tempo_track.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - prev)))
mid.tracks.append(tempo_track)

drums = mido.MidiTrack()
drums.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
drums.append(mido.Message('program_change', channel=9, program=0, time=0))
drums.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
prev = 0
for t, _, _, m in msgs:
    drums.append(m.copy(time=t - prev))
    prev = t
drums.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - prev)))
mid.tracks.append(drums)

mid.save('solo.mid')
