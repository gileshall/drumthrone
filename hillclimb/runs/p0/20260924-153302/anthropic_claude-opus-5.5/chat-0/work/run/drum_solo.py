#!/usr/bin/env python3
"""
drum_solo.py - generates solo.mid, a two-minute General MIDI drum solo (channel 10).

Form (100 BPM, 4/4, 50 bars = 120 s):
  bars  0-3   Intro        - motif stated on toms, answered, re-orchestrated, fill
  bars  4-11  Groove       - swung 16th groove; the kick drum plays the motif
  bars 12-19  Development  - linear motif accents, displacement, paradiddle-diddles,
                             unison motif hits, then a big release into space
  bars 20-27  Latin        - the motif revealed as son clave: claves, timbales, agogo
  bars 28-35  Build        - ride groove, 4-over-6 hemiola, 32nd roll, stop-time motif
  bars 36-43  Climax       - china groove + double bass, augmented motif over
                             sextuplets, 3-over-4 R-L-K linear figure, flams, big fill
  bars 44-45  Break        - ring-out, whispered motif on bell, buzz crescendo
  bars 46-49  Recap/Ending - groove returns, motif fill, unison motif hits, last crash

Every note is assigned to a limb (R hand, L hand, K = right foot, H = left foot),
so at most two hands and two feet ever play at once.  Feel is deliberate: 16th swing,
hats/ride pushing ahead, backbeat laid back, hand drums behind, build rushing slightly.
Deterministic: fixed random seed, sorted processing.
"""
import math
import random
import mido

BPM = 100
TPB = 480
BEAT_SEC = 60.0 / BPM
BARS = 50
SWING = 0.04          # 16th off-beats delayed by 0.04 beat (~58% swing)

# ---- General MIDI percussion ----
KICK2 = 35; KICK = 36; SIDE = 37; SNARE = 38; CLAP = 39
FLOOR_LO = 41; CHH = 42; FLOOR_HI = 43; PHH = 44; TOM_LO = 45; OHH = 46
TOM_LM = 47; TOM_HM = 48; CRASH = 49; TOM_HI = 50; RIDE = 51; CHINA = 52
BELL = 53; TAMB = 54; SPLASH = 55; COWBELL = 56; CRASH2 = 57
HI_BONGO = 60; LO_BONGO = 61; MUTE_CONGA = 62; OPEN_CONGA = 63; LO_CONGA = 64
HI_TIMB = 65; LO_TIMB = 66; HI_AGOGO = 67; LO_AGOGO = 68; CLAVES = 75
MUTE_TRI = 80; OPEN_TRI = 81

TOMS = [TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO]
MOTIF = [0, 3, 6, 10, 12]          # the motif (= son clave) in 16th steps

events = []   # [beat, note, vel, limb, extra_ms, swing]


def st(bar, step):
    return bar * 4 + step * 0.25


def hit(t, note, vel, limb, ms=0.0, swing=True):
    events.append([float(t), int(note), float(vel), limb, float(ms), bool(swing)])


# ------------------------------------------------------------------ building blocks
def grooveA(bar, variant=1, d=1.0, crash=False, open_hat=False, half=False):
    last = 8 if half else 16
    for s in range(0, last, 2):
        if s == 0 and crash:
            hit(st(bar, 0), CRASH, 112 * d, 'R')
        elif s == 14 and open_hat:
            hit(st(bar, 14), OHH, 90 * d, 'R')
            hit(st(bar + 1, 0), PHH, 64 * d, 'H')     # foot closes the open hat
        else:
            hit(st(bar, s), CHH, (86 if s % 4 == 0 else 60) * d, 'R')
    for s in (4, 12):
        if s < last:
            hit(st(bar, s), SNARE, 108 * d, 'L')
    ghosts = [7, 9, 15] if variant == 1 else [1, 7, 9, 11, 14, 15]
    for g in ghosts:
        if g < last:
            v = 40 if g in (11, 15) else 31
            hit(st(bar, g), SNARE, v * math.sqrt(d), 'L')
    kicks = [0, 3, 6, 10] + ([13] if variant == 2 else [])
    for k in kicks:
        if k < last:
            hit(st(bar, k), KICK, (100 if k == 0 else 86) * d, 'K')


def linear(bar, accents, d=1.0, start=0, end=16, kicks=(0, 4, 8, 12), kvel=66,
           avel=104, g0=30, g1=46, pedal=True):
    n = max(1, end - start - 1)
    for s in range(start, end):
        limb = 'R' if s % 2 == 0 else 'L'
        if s in accents:
            hit(st(bar, s), accents[s], avel * d, limb)
        else:
            hit(st(bar, s), SNARE, (g0 + (g1 - g0) * (s - start) / n) * d, limb)
    for k in kicks:
        if start <= k < end:
            hit(st(bar, k), KICK, kvel * d, 'K')
    if pedal:
        for p in (4, 12):
            if start <= p < end:
                hit(st(bar, p), PHH, 54 * d, 'H')


def dim_fill(bar, d=1.0):
    """Motif in diminution: 16ths RLRL, motif steps accented on descending toms."""
    acc = {0: TOM_HI, 3: TOM_HM, 6: TOM_LO, 10: FLOOR_HI, 12: FLOOR_LO}
    tail = {13: (SNARE, 96), 14: (FLOOR_LO, 102), 15: (FLOOR_HI, 106)}
    for s in range(16):
        limb = 'R' if s % 2 == 0 else 'L'
        if s in acc:
            hit(st(bar, s), acc[s], 106 * d, limb)
        elif s in tail:
            n, v = tail[s]
            hit(st(bar, s), n, v * d, limb)
        else:
            hit(st(bar, s), SNARE, (30 + s * 2.5) * d, limb)
    for k in (0, 3, 6, 10, 12, 14):
        hit(st(bar, k), KICK, (92 if k in (0, 12) else 80) * d, 'K')


def motif_unison(bar, d=1.0, pickups=True):
    cyms = [CRASH, CRASH2, CRASH, CRASH2, CHINA]
    for s, cym in zip(MOTIF, cyms):
        cl = 'R' if cym in (CRASH, CHINA) else 'L'
        ol = 'L' if cl == 'R' else 'R'
        hit(st(bar, s), cym, 116 * d, cl)
        hit(st(bar, s), SNARE, 110 * d, ol)
        hit(st(bar, s), KICK, 118 * d, 'K')
    if pickups:
        hit(st(bar, 8), TOM_HI, 78 * d, 'R')
        hit(st(bar, 9), TOM_HM, 84 * d, 'L')


# ------------------------------------------------------------------ the solo
def build():
    # ============ INTRO (bars 0-3) ============
    for b in range(0, 4):
        for s in (4, 12):
            hit(st(b, s), PHH, 50, 'H')
    # bar 0: statement
    orch0 = [(TOM_HI, 'R', 88), (TOM_HI, 'L', 74), (TOM_HM, 'R', 84),
             (FLOOR_HI, 'L', 86), (FLOOR_LO, 'R', 100)]
    for s, (n, l, v) in zip(MOTIF, orch0):
        hit(st(0, s), n, v, l)
    hit(st(0, 0), KICK, 70, 'K')
    hit(st(0, 12), KICK, 96, 'K')
    # bar 1: answer - space, whispered fragment on bell, ghost pickup
    hit(st(1, 0), KICK, 68, 'K')
    hit(st(1, 0), BELL, 72, 'R')
    hit(st(1, 3), BELL, 56, 'R')
    hit(st(1, 6), BELL, 64, 'R')
    hit(st(1, 13), SNARE, 30, 'L')
    hit(st(1, 14), SNARE, 36, 'R')
    hit(st(1, 15), SNARE, 44, 'L')
    # bar 2: restated, lower, flam, ghosts, crash on the last note
    orch2 = [(TOM_HM, 'R', 94), (TOM_HM, 'L', 78), (TOM_LO, 'R', 88),
             (FLOOR_LO, 'L', 92), (CRASH, 'R', 108)]
    for s, (n, l, v) in zip(MOTIF, orch2):
        hit(st(2, s), n, v, l)
    hit(st(2, 0), TOM_HM, 48, 'L', ms=-26)          # flam grace
    for s, l in ((1, 'L'), (2, 'R'), (8, 'L'), (9, 'R')):
        hit(st(2, s), SNARE, 32, l)
    hit(st(2, 0), KICK, 72, 'K')
    hit(st(2, 12), KICK, 104, 'K')
    # bar 3: fill - linear motif fragment on snare, then toms down
    linear(3, {0: SNARE, 3: SNARE, 6: SNARE}, d=0.95, start=0, end=8,
           kicks=(0,), avel=100, pedal=False)
    down = [TOM_HI, TOM_HI, TOM_HM, TOM_HM, TOM_LO, TOM_LO, FLOOR_LO, FLOOR_LO]
    for i, n in enumerate(down):
        s = 8 + i
        hit(st(3, s), n, 72 + i * 5, 'R' if s % 2 == 0 else 'L')
    hit(st(3, 8), KICK, 80, 'K')
    hit(st(3, 12), KICK, 92, 'K')

    # ============ GROOVE (bars 4-11) ============
    grooveA(4, 1, 0.92, crash=True)
    grooveA(5, 1, 0.92)
    grooveA(6, 1, 0.94, open_hat=True)
    grooveA(7, 1, 0.95, half=True)
    fill7 = [(8, SNARE, 'R', 100), (9, SNARE, 'L', 38), (10, TOM_HM, 'R', 96),
             (11, TOM_HM, 'L', 70), (12, FLOOR_LO, 'R', 104), (13, SNARE, 'L', 42),
             (14, FLOOR_HI, 'R', 92), (15, FLOOR_LO, 'L', 98)]
    for s, n, l, v in fill7:
        hit(st(7, s), n, v, l)
    for k in (8, 12, 14):
        hit(st(7, k), KICK, 90, 'K')
    grooveA(8, 2, 1.0, crash=True)
    grooveA(9, 2, 1.0)
    grooveA(10, 2, 1.02, open_hat=True)
    dim_fill(11, 1.0)

    # ============ DEVELOPMENT (bars 12-19) ============
    linear(12, {0: CRASH, 3: TOM_HI, 6: TOM_HM, 10: TOM_LO, 12: FLOOR_LO}, d=0.86)
    hit(st(12, 0), KICK, 104, 'K')
    linear(13, {0: FLOOR_LO, 3: TOM_LO, 6: TOM_HM, 10: TOM_HI, 12: SNARE}, d=0.9)
    # displaced by two 16ths
    linear(14, {2: TOM_HI, 5: TOM_HM, 8: TOM_LO, 12: FLOOR_HI, 14: FLOOR_LO}, d=0.94)
    # groups of three: 3-3-3-3-4 tension
    linear(15, {0: FLOOR_LO, 3: TOM_LO, 6: TOM_HM, 9: TOM_HI, 12: CRASH}, d=0.98,
           kicks=(0, 4, 8, 12, 14))
    # paradiddle-diddle sextuplets around the toms
    stick = 'RLRRLL'
    for bi, b in enumerate((16, 17)):
        order = [TOM_HI, TOM_HM, TOM_LO, FLOOR_LO] if bi == 0 else \
                [FLOOR_LO, TOM_LO, TOM_HM, TOM_HI]
        for beat in range(4):
            d = 0.9 + (bi * 4 + beat) * 0.02
            tom = order[beat]
            for i in range(6):
                t = b * 4 + beat + i / 6.0
                limb = stick[i]
                if i == 0:
                    n, v = tom, 102
                elif limb == 'R':
                    n, v = tom, 60
                else:
                    n, v = (TOM_HI, 70) if (bi == 1 and beat == 3) else (SNARE, 40)
                hit(t, n, v * d, limb, swing=False)
            hit(b * 4 + beat, KICK, 78 * d, 'K')
        for s in (4, 12):
            hit(st(b, s), PHH, 56, 'H')
    # unison motif hits
    motif_unison(18, 1.0)
    hit(st(18, 14), TOM_LO, 92, 'R')
    hit(st(18, 15), FLOOR_LO, 100, 'L')
    hit(st(18, 15), KICK, 90, 'K')
    # release: one big hit, then space, timbale pickup
    hit(st(19, 0), CRASH, 122, 'R')
    hit(st(19, 0), FLOOR_LO, 118, 'L')
    hit(st(19, 0), KICK, 124, 'K')
    for i, (n, v) in enumerate([(HI_TIMB, 58), (HI_TIMB, 68), (LO_TIMB, 80), (LO_TIMB, 92)]):
        s = 12 + i
        hit(st(19, s), n, v, 'R' if s % 2 == 0 else 'L')

    # ============ LATIN (bars 20-27): the motif is the clave ============
    for b in range(20, 28):
        d = 0.78 if b < 24 else (0.85 if b < 26 else 0.92)
        for s in (0, 4, 8, 12):
            hit(st(b, s), PHH, 42, 'H')
        hit(st(b, 6), KICK, 66 * d, 'K')
        hit(st(b, 12), KICK, 74 * d, 'K')
    hit(st(20, 0), KICK, 92, 'K')
    hit(st(20, 0), LO_TIMB, 96, 'L')
    # bars 20-21: claves play the motif, conga tumbao in the left hand
    for bi, b in enumerate((20, 21)):
        d = 0.8
        for s in MOTIF:
            hit(st(b, s), CLAVES, (96 if s == 0 else 86) * d, 'R')
        conga = {0: (MUTE_CONGA, 36), 2: (MUTE_CONGA, 30), 4: (MUTE_CONGA, 80),
                 6: (MUTE_CONGA, 34), 8: (MUTE_CONGA, 36), 10: (MUTE_CONGA, 30),
                 14: (OPEN_CONGA if bi == 0 else LO_CONGA, 90),
                 15: (OPEN_CONGA if bi == 0 else LO_CONGA, 82)}
        for s, (n, v) in conga.items():
            hit(st(b, s), n, v * d, 'L')
    # bars 22-23: cowbell; timbales take the motif
    for b in (22, 23):
        d = 0.82
        for s, v in {0: 94, 4: 70, 6: 80, 8: 90, 12: 72, 14: 82}.items():
            hit(st(b, s), COWBELL, v * d, 'R')
        for s, (n, v) in {0: (HI_TIMB, 92), 3: (HI_TIMB, 80), 6: (LO_TIMB, 88),
                          10: (LO_TIMB, 90), 12: (HI_TIMB, 98)}.items():
            hit(st(b, s), n, v * d, 'L')
        hit(st(b, 8), MUTE_CONGA, 32, 'L')
        hit(st(b, 14), OPEN_CONGA, 70 * d, 'L')
    # bars 24-25: agogo carries the motif, bongo martillo
    for b in (24, 25):
        d = 0.86
        for s in MOTIF:
            hit(st(b, s), HI_AGOGO, (94 if s == 0 else 82) * d, 'R')
        for s in (8, 14):
            hit(st(b, s), LO_AGOGO, 70 * d, 'R')
        bongo = {0: (HI_BONGO, 72), 2: (HI_BONGO, 40), 4: (HI_BONGO, 56),
                 6: (LO_BONGO, 68), 8: (HI_BONGO, 72), 10: (HI_BONGO, 40),
                 12: (HI_BONGO, 56), 14: (LO_BONGO, 74), 15: (LO_BONGO, 62)}
        for s, (n, v) in bongo.items():
            hit(st(b, s), n, v * d, 'L')
    # bar 26: displaced timbale motif over cowbell
    d = 0.92
    for s, v in {0: 94, 4: 72, 6: 80, 8: 90, 12: 74, 14: 82}.items():
        hit(st(26, s), COWBELL, v * d, 'R')
    for s, (n, v) in {2: (HI_TIMB, 84), 5: (HI_TIMB, 76), 8: (LO_TIMB, 86),
                      12: (LO_TIMB, 90), 14: (HI_TIMB, 98)}.items():
        hit(st(26, s), n, v * d, 'L')
    hit(st(26, 0), MUTE_CONGA, 34, 'L')
    hit(st(26, 10), MUTE_CONGA, 32, 'L')
    # bar 27: motif fragment, then timbale fill into the build
    for s in (0, 4, 6):
        hit(st(27, s), COWBELL, (94 if s == 0 else 76), 'R')
    for s, (n, v) in {0: (HI_TIMB, 90), 3: (HI_TIMB, 80), 6: (LO_TIMB, 92)}.items():
        hit(st(27, s), n, v, 'L')
    tfill = [HI_TIMB, HI_TIMB, HI_TIMB, LO_TIMB, HI_TIMB, LO_TIMB, LO_TIMB, LO_TIMB]
    for i, n in enumerate(tfill):
        s = 8 + i
        hit(st(27, s), n, 70 + i * 6, 'R' if s % 2 == 0 else 'L')
    hit(st(27, 15), KICK, 90, 'K')

    # ============ BUILD (bars 28-35) ============
    def ride_groove(bar, d, crash=False, bell=False, extra_ghosts=False):
        rn = BELL if bell else RIDE
        for s in (0, 4, 6, 8, 12, 14):
            if s == 0 and crash:
                hit(st(bar, 0), CRASH, 114 * d, 'R')
            else:
                hit(st(bar, s), rn, (88 if s % 4 == 0 else 66) * d, 'R')
        for s in (4, 12):
            hit(st(bar, s), SNARE, 108 * d, 'L')
        gh = [7, 9, 11, 15] + ([1, 2, 14] if extra_ghosts else [])
        for g in gh:
            hit(st(bar, g), SNARE, (42 if g in (11, 15) else 33) * math.sqrt(d), 'L')
        for k in (0, 3, 6, 10):
            hit(st(bar, k), KICK, (100 if k == 0 else 88) * d, 'K')
        for p in (4, 12):
            hit(st(bar, p), PHH, 56 * d, 'H')

    ride_groove(28, 0.84, crash=True)
    ride_groove(29, 0.87)
    ride_groove(30, 0.9, bell=True, extra_ghosts=True)
    linear(31, {0: CRASH, 3: TOM_HI, 6: TOM_HM, 10: TOM_LO, 12: FLOOR_LO, 14: FLOOR_LO},
           d=0.93, kicks=(0, 2, 4, 6, 8, 10, 12, 14), kvel=74)
    hit(st(31, 0), KICK, 100, 'K')
    # 4-over-6 hemiola: sextuplet singles, accent every fourth note
    for bi, b in enumerate((32, 33)):
        for n in range(24):
            t = b * 4 + n / 6.0
            limb = 'R' if n % 2 == 0 else 'L'
            d = 0.92 + (bi * 24 + n) * 0.0025
            if n % 4 == 0:
                if bi == 1 and n >= 18:
                    note = CRASH
                else:
                    note = [TOM_HI, TOM_HM, TOM_LO, FLOOR_HI, FLOOR_LO, TOM_LM][(n // 4) % 6]
                hit(t, note, 106 * d, limb, swing=False)
                if n % 12 == 0 or (bi == 1 and n >= 18):
                    hit(t, KICK, 96 * d, 'K', swing=False)
            else:
                hit(t, SNARE, (36 + n * 0.8 + bi * 10) * d, limb, swing=False)
        for s in (4, 12):
            hit(st(b, s), PHH, 58, 'H')
    # 32nd-note snare roll with the motif accented
    acc32 = {0, 6, 12, 20, 24}
    for n in range(32):
        t = 34 * 4 + n / 8.0
        limb = 'R' if n % 2 == 0 else 'L'
        if n in acc32:
            hit(t, SNARE, 112, limb, swing=False)
        else:
            hit(t, SNARE, 28 + n * 2.3, limb, swing=False)
    for k in range(4):
        hit(34 * 4 + k, KICK, 90, 'K')
    # stop-time motif: hits and silence, then sextuplet tom run
    for s in MOTIF[:4]:
        hit(st(35, s), CRASH, 118, 'R')
        hit(st(35, s), SNARE, 112, 'L')
        hit(st(35, s), KICK, 120, 'K')
    for s in (4, 8):
        hit(st(35, s), PHH, 50, 'H')
    for i, n in enumerate(TOMS):
        hit(35 * 4 + 3 + i / 6.0, n, 92 + i * 5, 'R' if i % 2 == 0 else 'L', swing=False)
    hit(st(35, 12), KICK, 110, 'K')

    # ============ CLIMAX (bars 36-43) ============
    for bi, b in enumerate((36, 37)):
        d = 1.02
        for s in range(0, 16, 2):
            if s == 0 and bi == 0:
                hit(st(b, 0), CRASH, 124, 'R')
            else:
                hit(st(b, s), CHINA, (98 if s % 4 == 0 else 80) * d, 'R')
        for s in (4, 12):
            hit(st(b, s), SNARE, 120, 'L')
        for g in ([7, 15] if bi == 0 else [7, 10, 11]):
            hit(st(b, g), SNARE, 44, 'L')
        if bi == 0:
            for k in (0, 3, 6, 8, 10, 14):
                hit(st(b, k), KICK, 100, 'K')
            for s in (4, 12):
                hit(st(b, s), PHH, 60, 'H')
        else:
            for k in (0, 3, 6):
                hit(st(b, k), KICK, 100, 'K')
            for s in range(8, 16):                    # double bass run
                if s % 2 == 0:
                    hit(st(b, s), KICK, 92 + s, 'K')
                else:
                    hit(st(b, s), KICK2, 88 + s, 'H')
    # augmented motif (beats 0,1.5,3,5,6) over sextuplet tom sweeps
    hits = {0, 9, 18, 30, 36}
    skip = set()
    for h in hits:
        skip.update({h + 1, h + 2})
    for n in range(48):
        t = 38 * 4 + n / 6.0
        limb = 'R' if n % 2 == 0 else 'L'
        if n in hits:
            hit(t, CRASH if limb == 'R' else CRASH2, 122, limb, swing=False)
            hit(t, KICK, 124, 'K', swing=False)
        elif n in skip:
            continue
        else:
            v = 52 + (n % 6) * 5 + (20 if n >= 40 else 0)
            hit(t, TOMS[n % 6], v, limb, swing=False)
            if n % 6 == 0:
                hit(t, KICK, 80, 'K', swing=False)
    # 3-over-4 linear: R (moving accent) - L (snare) - K, across two bars
    cyc = [TOM_HI, TOM_HM, TOM_LO, FLOOR_LO, CRASH]
    k = 0
    for n in range(32):
        t = 40 * 4 + n * 0.25
        r = n % 3
        if r == 0:
            hit(t, cyc[k % 5], 110 if cyc[k % 5] == CRASH else 104, 'R')
            k += 1
        elif r == 1:
            hit(t, SNARE, 62, 'L')
        else:
            hit(t, KICK, 98, 'K')
    for s in range(0, 32, 4):
        hit(40 * 4 + s * 0.25, PHH, 60, 'H')
    # flammed motif with left-hand ghost stream
    for s, n in zip(MOTIF, [SNARE, TOM_HI, TOM_HM, TOM_LO, FLOOR_LO]):
        hit(st(42, s), n, 118, 'R')
        hit(st(42, s), n, 58, 'L', ms=-26)
        hit(st(42, s), KICK, 112, 'K')
    for g in (1, 4, 8, 9, 14, 15):
        hit(st(42, g), SNARE, 40, 'L')
    for s in (4, 8):
        hit(st(42, s), PHH, 62, 'H')
    # big fill: triplet-accented sextuplets, then toms down in pairs
    for n in range(12):
        t = 43 * 4 + n / 6.0
        limb = 'R' if n % 2 == 0 else 'L'
        if n % 3 == 0:
            hit(t, SNARE, 112, limb, swing=False)
            hit(t, KICK, 100, 'K', swing=False)
        else:
            hit(t, SNARE, 50 + n * 2, limb, swing=False)
    for i in range(12):
        t = 43 * 4 + 2 + i / 6.0
        hit(t, TOMS[i // 2], 96 + i * 2, 'R' if i % 2 == 0 else 'L', swing=False)
    hit(st(43, 8), KICK, 104, 'K')
    hit(st(43, 12), KICK, 110, 'K')

    # ============ BREAK (bars 44-45) ============
    hit(st(44, 0), CRASH, 124, 'R')
    hit(st(44, 0), CRASH2, 118, 'L')
    hit(st(44, 0), KICK, 127, 'K')
    hit(st(44, 0), KICK2, 112, 'H')
    hit(st(44, 8), PHH, 38, 'H')
    hit(st(44, 12), PHH, 42, 'H')
    hit(st(44, 10), OPEN_TRI, 46, 'R')
    for s in (0, 4, 8, 12):
        hit(st(45, s), PHH, 44, 'H')
    hit(st(45, 0), BELL, 62, 'R')
    hit(st(45, 3), BELL, 48, 'R')
    hit(st(45, 6), BELL, 56, 'R')
    for n in range(16, 32):
        t = 45 * 4 + n / 8.0
        hit(t, SNARE, 18 + (n - 16) * 5.2, 'R' if n % 2 == 0 else 'L', swing=False)

    # ============ RECAP / ENDING (bars 46-49) ============
    grooveA(46, 2, 1.06, crash=True)
    dim_fill(47, 1.1)
    motif_unison(48, 1.06, pickups=False)
    hit(st(48, 13), SNARE, 104, 'L')
    hit(st(48, 14), FLOOR_HI, 112, 'R')
    hit(st(48, 15), FLOOR_LO, 118, 'L')
    hit(st(48, 14), KICK, 110, 'K')
    hit(st(48, 15), KICK2, 110, 'H')
    hit(st(49, 0), CRASH, 127, 'R')
    hit(st(49, 0), CRASH2, 124, 'L')
    hit(st(49, 0), KICK, 127, 'K')
    hit(st(49, 0), KICK2, 118, 'H')


# ------------------------------------------------------------------ playability
MIN_GAP = {'R': 0.12, 'L': 0.12, 'K': 0.2, 'H': 0.2}


def sanitize(evs):
    evs = sorted(evs, key=lambda e: (e[3], e[0], -e[2], e[1]))
    kept = []
    last = {}
    for e in evs:
        l = e[3]
        if l in last and e[0] - last[l][0] < MIN_GAP[l] - 1e-9:
            if e[2] > last[l][2]:
                kept[last[l][6]] = None
                e = e + [len(kept)]
                kept.append(e)
                last[l] = e
            continue
        e = e + [len(kept)]
        kept.append(e)
        last[l] = e
    return [k[:6] for k in kept if k is not None]


# ------------------------------------------------------------------ feel
PUSH = {CHH: -5, OHH: -5, RIDE: -6, BELL: -6, CHINA: -4}
LATIN_BELLS = {COWBELL: -3, HI_AGOGO: -3, LO_AGOGO: -3, CLAVES: -3}
HAND_DRUMS = {HI_BONGO, LO_BONGO, MUTE_CONGA, OPEN_CONGA, LO_CONGA, HI_TIMB, LO_TIMB}


def micro_ms(note, vel, t):
    if note in (SNARE, SIDE, CLAP):
        off = 10.0 if vel >= 90 else 4.0      # backbeat lays back, ghosts slightly
    elif note in PUSH:
        off = PUSH[note]
    elif note in LATIN_BELLS:
        off = LATIN_BELLS[note]
    elif note in HAND_DRUMS:
        off = 7.0
    elif note == PHH:
        off = 2.0
    else:
        off = 0.0
    bar = int(t // 4)
    if 28 <= bar < 36:
        off -= 4.0            # the build leans forward
    elif 36 <= bar < 44:
        off -= 2.0
    elif 44 <= bar < 46:
        off += 6.0            # the break sits back
    return off


def swung(t, sw):
    if not sw:
        return t
    frac = t - math.floor(t)
    if abs(frac - 0.25) < 1e-6 or abs(frac - 0.75) < 1e-6:
        return t + SWING
    return t


# ------------------------------------------------------------------ output
def write():
    rng = random.Random(1977)
    evs = sanitize(events)
    evs.sort(key=lambda e: (e[0], e[3], e[1]))
    notes = {}
    for t, note, vel, limb, ms, sw in evs:
        total_ms = ms + micro_ms(note, vel, t) + rng.gauss(0.0, 1.5)
        beat = swung(t, sw) + total_ms / 1000.0 / BEAT_SEC
        tick = max(0, int(round(beat * TPB)))
        v = vel + rng.gauss(0.0, 2.0)
        v = int(round(max(12 if vel < 45 else 20, min(127, v))))
        key = (tick, note)
        if key not in notes or notes[key] < v:
            notes[key] = v

    ons = sorted((tk, n, v) for (tk, n), v in notes.items())
    by_note = {}
    for tk, n, v in ons:
        by_note.setdefault(n, []).append(tk)
    msgs = []
    for n, ticks in by_note.items():
        for i, tk in enumerate(ticks):
            nxt = ticks[i + 1] if i + 1 < len(ticks) else None
            dur = 40
            if nxt is not None:
                dur = max(1, min(40, nxt - tk - 1))
            msgs.append((tk, 1, n, notes[(tk, n)]))
            msgs.append((tk + dur, 0, n, 0))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=110, time=0))
    tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
    now = 0
    for tk, kind, n, v in msgs:
        delta = tk - now
        now = tk
        if kind == 1:
            tr.append(mido.Message('note_on', channel=9, note=n, velocity=v, time=delta))
        else:
            tr.append(mido.Message('note_off', channel=9, note=n, velocity=0, time=delta))
    end_tick = max(BARS * 4 * TPB, now)
    tr.append(mido.MetaMessage('end_of_track', time=end_tick - now))
    mid.save('solo.mid')


if __name__ == '__main__':
    build()
    write()
