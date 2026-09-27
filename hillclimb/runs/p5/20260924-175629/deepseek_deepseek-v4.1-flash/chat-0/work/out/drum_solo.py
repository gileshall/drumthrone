#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drum_solo.py -- writes solo.mid, a ~2 minute General MIDI drum solo
played on MIDI channel 10 by a single (two-handed, two-footed) drummer.

Deterministic: same bytes every run.
"""

import random
import mido

TPB = 960          # ticks per quarter note
CH = 9             # zero-based channel 10 (GM percussion)

# ------------------------------------------------------------------ GM notes
KICK, KICK2 = 36, 35
SNARE, RIM = 38, 37
HAT, HATP, HATO = 42, 44, 46
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
RIDE, BELL, RIDE2 = 51, 53, 59
TOM_HP, TOM_HM, TOM_ML, TOM_LO, TOM_FH, TOM_FL = 50, 48, 47, 45, 43, 41
CONGA_H, CONGA_M, CONGA_L = 63, 62, 64
BONGO_H, BONGO_L = 60, 61
TAMB, COWBELL, CLAVES, WOOD_H, WOOD_L = 54, 56, 75, 76, 77
CABASA, MARACAS, TRIANGLE = 69, 70, 81

# --------------------------------------------------------- tempo / feel maps
SECTIONS = [
    # (start_beat, end_beat, bpm_start, bpm_end)
    (0.0, 8.0, 102.0, 102.0),       # 1  intro, spacious
    (8.0, 40.0, 110.0, 110.0),      # 2  statement of motif A
    (40.0, 72.0, 116.0, 116.0),     # 3  development 1 - hands travel
    (72.0, 96.0, 111.0, 111.0),     # 4  contrast: space, half-time
    (96.0, 112.0, 112.0, 132.0),    # 5  roll build (accel)
    (112.0, 160.0, 131.0, 131.0),   # 6  peak - motif B
    (160.0, 184.0, 116.0, 116.0),   # 7  breakdown - motif A returns
    (184.0, 216.0, 114.0, 134.0),   # 8  big build (accel)
    (216.0, 241.0, 137.0, 137.0),   # 9  finale
]

FEEL = [
    # push/pull per section, milliseconds (+ = laid back, - = pushing)
    (0.0, 8.0, 3.0),
    (8.0, 40.0, 0.0),
    (40.0, 72.0, -2.0),
    (72.0, 96.0, 5.0),
    (96.0, 112.0, -4.0),
    (112.0, 160.0, -3.0),
    (160.0, 184.0, 6.0),
    (184.0, 216.0, -5.0),
    (216.0, 241.0, -2.0),
]


def bpm_at(beat):
    b = 0.0 if beat < 0.0 else (240.0 if beat > 240.0 else beat)
    for a, z, t0, t1 in SECTIONS:
        if a <= b < z:
            return t0 + (t1 - t0) * (b - a) / (z - a)
    return SECTIONS[-1][3]


def feel_at(beat):
    for a, z, f in FEEL:
        if a <= beat < z:
            return f
    return 0.0


_rng = random.Random(0x5EED)

# slow random walk -> the pulse surges and settles
DRIFT = []
_v = 0.0
for _i in range(243):
    _v = 0.82 * _v + _rng.gauss(0.0, 3.2)
    DRIFT.append(_v)


def drift_at(beat):
    b = 0.0 if beat < 0.0 else (240.0 if beat > 240.0 else beat)
    i = int(b)
    f = b - i
    if i >= 242:
        return DRIFT[242] + feel_at(b)
    return DRIFT[i] * (1.0 - f) + DRIFT[i + 1] * f + feel_at(b)


def ms2b(beat, ms):
    """milliseconds -> beats, at the local tempo"""
    return ms / 1000.0 * bpm_at(beat) / 60.0


EV = []


def hit(beat, note, vel, hand=None, push=0.0, jit=None, spread=4.0):
    """One percussion stroke, humanised in time and velocity."""
    if hand is None:
        hand = note not in (KICK, KICK2, HATP)
    if jit is None:
        jit = 4.0 if vel >= 78 else 7.0
    off = push + drift_at(beat) + _rng.gauss(0.0, jit)
    t = beat + ms2b(beat, off)
    v = int(round(vel + _rng.gauss(0.0, spread)))
    if v < 1:
        v = 1
    if v > 127:
        v = 127
    EV.append((t, note, v, hand))


def run16(t0, n, notes, v0, v1, accent=8.0, jit=4.5):
    """n sixteenth notes starting at t0, cycling through `notes`."""
    m = len(notes)
    for i in range(n):
        v = v0 + (v1 - v0) * (i / (n - 1.0)) if n > 1 else v0
        if i % 4 == 0:
            v += accent
        hit(t0 + i * 0.25, notes[i % m], v, jit=jit)


# ============================================================ the solo itself

def sec_intro():
    """bars 1-2 : the solo announces itself, quietly."""
    for i in range(8):
        hit(i * 0.5, RIDE, 60 if i % 2 == 0 else 46)
    hit(0.0, KICK, 62)
    hit(2.5, KICK, 54)
    hit(1.0, HATP, 46)
    hit(3.0, HATP, 48)
    for g in (0.75, 1.75, 2.75, 3.75):
        hit(g, SNARE, 30, push=4.0, jit=9.0)

    for i in range(4):
        hit(4.0 + i * 0.5, RIDE, 62 if i % 2 == 0 else 48)
    hit(4.0, KICK, 64)
    hit(5.0, HATP, 48)
    hit(6.0, KICK, 60)
    # pickup into the first downbeat
    hit(6.5, SNARE, 58)
    hit(7.0, TOM_HM, 64)
    hit(7.25, TOM_HM, 58)
    hit(7.5, TOM_ML, 70)
    hit(7.75, TOM_LO, 80)


def motifA(t0, v=1.0, ride=RIDE, back=SNARE, ghost=SNARE,
           ghosts=(1.25, 2.75, 3.75), sw=0.0):
    """The seed motif: a ride/hi-hat time feel with accented backbeats,
    a syncopated bass drum and a scatter of ghost notes."""
    for i in range(8):
        bt = t0 + i * 0.5 + (sw if i % 2 else 0.0)
        hit(bt, ride, (88 if i % 2 == 0 else 64) * v)
    hit(t0 + 0.0, KICK, 106 * v)
    hit(t0 + 2.5, KICK, 86 * v)
    hit(t0 + 1.0, back, 102 * v)
    hit(t0 + 3.0, back, 108 * v)
    hit(t0 + 1.0, HATP, 58 * v)
    hit(t0 + 3.0, HATP, 62 * v)
    for g in ghosts:
        hit(t0 + g, ghost, 32 * v, push=4.0, jit=9.0)


def motifA_bell(t0, v=1.0):
    """Motif A with the ride bell answering, tom accent on the & of 4."""
    for i in range(8):
        bt = t0 + i * 0.5
        hit(bt, BELL if i % 2 == 0 else RIDE, (94 if i % 2 == 0 else 62) * v)
    hit(t0 + 0.0, KICK, 112 * v)
    hit(t0 + 1.75, KICK, 82 * v)
    hit(t0 + 2.5, KICK, 96 * v)
    hit(t0 + 1.0, SNARE, 106 * v)
    hit(t0 + 3.0, SNARE, 112 * v)
    hit(t0 + 1.0, HATP, 60 * v)
    hit(t0 + 3.0, HATP, 64 * v)
    hit(t0 + 2.25, SNARE, 34 * v, push=4.0, jit=9.0)
    hit(t0 + 3.5, TOM_ML, 68 * v)


def groove_hats(t0, v=1.0):
    """Motif A relocated to the hi-hat with a walking bass drum."""
    for i in range(8):
        hit(t0 + i * 0.5, HAT, (86 if i % 2 == 0 else 62) * v)
    hit(t0 + 0.0, KICK, 112 * v)
    hit(t0 + 1.75, KICK, 76 * v)
    hit(t0 + 2.5, KICK, 90 * v)
    hit(t0 + 3.75, KICK, 72 * v)
    hit(t0 + 1.0, SNARE, 104 * v)
    hit(t0 + 3.0, SNARE, 110 * v)
    hit(t0 + 2.25, SNARE, 34 * v, push=4.0, jit=9.0)
    hit(t0 + 3.25, SNARE, 30 * v, push=4.0, jit=9.0)


def motifA_toms(t0, ride=RIDE, v=1.0):
    """Motif A whose ghost notes have migrated onto the toms."""
    for i in range(8):
        hit(t0 + i * 0.5, ride, (86 if i % 2 == 0 else 60) * v)
    hit(t0 + 0.0, KICK, 110 * v)
    hit(t0 + 2.0, KICK, 80 * v)
    hit(t0 + 2.5, KICK, 92 * v)
    hit(t0 + 1.0, SNARE, 106 * v)
    hit(t0 + 3.0, SNARE, 112 * v)
    hit(t0 + 1.25, TOM_HP, 46 * v, push=3.0)
    hit(t0 + 2.75, TOM_HM, 42 * v, push=3.0)
    hit(t0 + 3.75, TOM_ML, 50 * v, push=3.0)


def sec_statement():
    """bars 3-10 : motif A stated, varied, and driven into a fill."""
    hit(8.0, CRASH, 106)
    hit(8.0, KICK, 112)
    motifA(8.0)
    motifA(12.0)

    motifA_bell(16.0)
    motifA_bell(20.0)

    groove_hats(24.0)
    groove_hats(28.0)

    # bar 9 : sixteenths on the hat, rising
    for i in range(16):
        v = (68 if i % 4 == 0 else 50) + i * 1.6
        hit(32.0 + i * 0.25, HAT, v)
    hit(32.0, KICK, 114)
    hit(33.5, KICK, 94)
    hit(34.5, KICK, 98)
    hit(33.0, SNARE, 110)
    hit(35.0, SNARE, 114)
    hit(35.75, SNARE, 42, push=4.0, jit=8.0)

    # bar 10 : fill that lands on the next section's downbeat
    run16(36.0, 16, [SNARE, TOM_HP, TOM_HM, TOM_ML,
                     TOM_LO, TOM_FH, TOM_FL, TOM_FL], 92, 122)
    hit(36.0, KICK, 112)
    hit(38.0, KICK, 108)


def sec_dev1():
    """bars 11-18 : development -- the hands start travelling."""
    hit(40.0, CRASH, 114)
    hit(40.0, KICK, 118)

    # bars 11-12 : driving sixteenth-note hats
    for t in (40.0, 44.0):
        for i in range(16):
            v = 86 if i % 4 == 0 else (62 if i % 2 == 0 else 50)
            hit(t + i * 0.25, HAT, v)
        hit(t + 0.0, KICK, 116)
        hit(t + 2.5, KICK, 92)
        hit(t + 3.75, KICK, 86)
        hit(t + 1.0, SNARE, 112)
        hit(t + 3.0, SNARE, 116)
        hit(t + 1.75, SNARE, 36, push=4.0, jit=8.0)
        hit(t + 2.75, SNARE, 32, push=4.0, jit=8.0)

    # bars 13-14 : motif A, ghosts on toms, ride then hat
    motifA_toms(48.0, ride=RIDE)
    motifA_toms(52.0, ride=HAT)

    # bars 15-16 : doubles down the kit, singles back up
    run16(56.0, 16, [SNARE, SNARE, TOM_HP, TOM_HP, TOM_HM, TOM_HM,
                     TOM_ML, TOM_ML], 90, 108)
    hit(56.0, KICK, 112)
    hit(58.0, KICK, 106)
    run16(60.0, 16, [TOM_LO, TOM_LO, TOM_FH, TOM_FH, TOM_FL, TOM_FL,
                     SNARE, SNARE], 98, 118)
    hit(60.0, KICK, 114)
    hit(62.0, KICK, 110)

    # bars 17-18 : crescendo, then the fill
    for i in range(16):
        note = SNARE if (i // 4) % 2 == 0 else TOM_HM
        hit(64.0 + i * 0.25, note, 72 + i * 2.2)
    hit(64.0, KICK, 112)
    hit(66.0, KICK, 108)
    run16(68.0, 16, [TOM_HP, TOM_HM, TOM_ML, TOM_LO,
                     TOM_FH, TOM_FL, SNARE, SNARE], 100, 126)
    hit(68.0, KICK, 116)
    hit(70.0, KICK, 118)


def sec_contrast():
    """bars 19-24 : release -- space, half-time, a different colour."""
    hit(72.0, CRASH, 118)
    hit(72.0, KICK, 108)

    # bars 19-20 : half-time, ride bell on the quarters
    for t in (72.0, 76.0):
        for q in range(4):
            hit(t + q, BELL if q % 2 == 0 else RIDE, 74)
        hit(t + 0.0, KICK, 98)
        hit(t + 2.0, SNARE, 100)
        hit(t + 1.0, HATP, 54)
        hit(t + 3.0, HATP, 56)
        hit(t + 3.5, SNARE, 34, push=4.0, jit=9.0)

    # bars 21-22 : maracas, congas, bass drum triplet
    for t in (80.0, 84.0):
        for i in range(16):
            hit(t + i * 0.25, MARACAS, 34 + (7 if i % 4 == 0 else 0), jit=6.0)
        hit(t + 0.0, KICK, 96)
        hit(t + 2.0, RIM, 94)
        hit(t + 1.5, CONGA_H, 80)
        hit(t + 2.5, CONGA_M, 76)
        hit(t + 3.5, CONGA_L, 74)
    hit(87.0, KICK, 88)
    hit(87.333, KICK, 84)
    hit(87.667, KICK, 92)

    # bars 23-24 : leave some air
    hit(88.0, KICK, 72)
    hit(88.0, HATP, 52)
    hit(88.0, RIDE, 64)
    hit(90.0, KICK, 68)
    hit(90.0, HATP, 50)
    hit(91.5, SNARE, 32, push=4.0, jit=9.0)
    hit(92.0, KICK, 70)
    hit(92.0, HATP, 54)
    hit(93.5, SNARE, 36, push=4.0, jit=9.0)
    hit(94.0, KICK, 74)
    hit(94.0, RIDE, 66)
    hit(95.0, SNARE, 46)
    hit(95.5, SNARE, 54)
    hit(95.75, SNARE, 62)


def sec_rollbuild():
    """bars 25-28 : the roll swells and resolves (tempo accelerating)."""
    # bar 25 : pp -> mp
    for i in range(32):
        v = 28 + 22 * (i / 31.0) + (10 if i % 8 == 0 else 0)
        hit(96.0 + i * 0.125, SNARE, v, jit=2.5, push=0.0)
    # bar 26 : mp -> mf, feet join
    for i in range(32):
        v = 52 + 26 * (i / 31.0) + (10 if i % 8 == 0 else 0)
        hit(100.0 + i * 0.125, SNARE, v, jit=2.5, push=0.0)
    hit(100.0, KICK, 84)
    hit(102.0, KICK, 92)
    # bar 27 : the roll walks onto the toms
    for i in range(16):
        note = SNARE if i % 2 == 0 else (TOM_HP if i % 4 == 1 else TOM_HM)
        hit(104.0 + i * 0.25, note, 78 + i * 2.6, jit=3.5)
    hit(104.0, KICK, 100)
    hit(106.0, KICK, 104)
    # bar 28 : cascade into the peak
    run16(108.0, 16, [TOM_HP, TOM_HM, TOM_ML, TOM_LO,
                      TOM_FH, TOM_FL, TOM_ML, TOM_LO], 94, 124,
          accent=0.0, jit=3.0)
    hit(108.0, KICK, 108)
    hit(110.0, KICK, 112)


def sec_peak():
    """bars 29-40 : motif B -- the solo's high point."""
    hit(112.0, CRASH, 122)
    hit(112.0, KICK, 122)

    # bars 29-30 : sixteenths on the hat, driving kick and backbeat
    for b in range(2):
        t = 112.0 + 4 * b
        if b == 1:
            hit(t, CRASH, 118)
        for i in range(16):
            v = 96 if i % 4 == 0 else (68 if i % 2 == 0 else 54)
            hit(t + i * 0.25, HAT, v)
        hit(t + 1.0, SNARE, 116)
        hit(t + 3.0, SNARE, 120)
        hit(t + 1.75, SNARE, 40, push=3.0)
        hit(t + 0.0, KICK, 120)
        hit(t + 2.5, KICK, 104)
        hit(t + 3.75, KICK, 98)
        hit(t + 2.0, HATP, 62)

    # bars 31-32 : the hands move to the toms
    for b, drum in ((2, TOM_HM), (3, TOM_ML)):
        t = 112.0 + 4 * b
        for i in range(16):
            v = 104 if i % 4 == 0 else (74 if i % 2 == 0 else 60)
            hit(t + i * 0.25, drum, v)
        hit(t + 1.0, SNARE, 114)
        hit(t + 3.0, SNARE, 118)
        hit(t + 0.0, KICK, 120)
        hit(t + 1.5, KICK, 102)
        hit(t + 3.5, KICK, 106)

    # bars 33-34 : doubles down the kit and back up
    dbl = [SNARE, SNARE, TOM_HP, TOM_HP, TOM_HM, TOM_HM, TOM_ML, TOM_ML,
           TOM_LO, TOM_LO, TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_FL, TOM_FL]
    run16(128.0, 16, dbl, 100, 118, jit=3.5)
    run16(132.0, 16, list(reversed(dbl)), 106, 124, jit=3.5)
    hit(128.0, KICK, 118)
    hit(130.0, KICK, 112)
    hit(132.0, KICK, 120)
    hit(134.0, KICK, 116)

    # bars 35-36 : snare & toms in a long single-stroke flow
    flow = [SNARE, TOM_HP, SNARE, TOM_HM, SNARE, TOM_ML, SNARE, TOM_LO]
    for i in range(32):
        v = 104 + 16 * (i / 31.0) + (8 if i % 4 == 0 else 0)
        hit(136.0 + i * 0.25, flow[i % 8], v, jit=3.5)
    hit(136.0, KICK, 118)
    hit(138.0, KICK, 114)
    hit(140.0, KICK, 120)
    hit(142.0, KICK, 116)

    # bars 37-38 : everything at once
    for b in range(2):
        t = 144.0 + 4 * b
        hit(t, CRASH, 120)
        for i in range(16):
            v = 100 if i % 4 == 0 else (70 if i % 2 == 0 else 56)
            hit(t + i * 0.25, HAT, v)
        hit(t + 1.0, SNARE, 118)
        hit(t + 3.0, SNARE, 122)
        hit(t + 0.0, KICK, 122)
        hit(t + 1.75, KICK, 100)
        hit(t + 2.5, KICK, 108)
        hit(t + 3.5, KICK, 96)
        hit(t + 2.0, HATP, 64)

    # bar 39 : sixteenths swell on the snare
    for i in range(16):
        hit(152.0 + i * 0.25, SNARE,
            100 + i * 1.2 + (8 if i % 4 == 0 else 0))
    hit(152.0, KICK, 116)
    hit(154.0, KICK, 112)
    # bar 40 : roll then cascade, resolving into the breakdown
    for i in range(16):
        hit(156.0 + i * 0.125, SNARE, 104 + i * 1.2, jit=3.0)
    run16(158.0, 8, [TOM_FL, TOM_FH, TOM_LO, TOM_ML,
                     TOM_HM, TOM_HP, SNARE, SNARE], 112, 126,
          accent=0.0, jit=3.0)
    hit(156.0, KICK, 118)
    hit(158.0, KICK, 120)


def sec_breakdown():
    """bars 41-46 : motif A comes back, quiet and laid back."""
    hit(160.0, CRASH, 104)
    hit(160.0, KICK, 90)

    # bar 41
    for i in range(8):
        hit(160.0 + i * 0.5 + (0.02 if i % 2 else 0.0),
            RIDE, 58 if i % 2 == 0 else 42)
    hit(160.0, KICK, 76)
    hit(162.5, KICK, 62)
    hit(161.0, RIM, 62)
    hit(163.0, RIM, 66)
    hit(161.0, HATP, 40)
    hit(163.0, HATP, 42)
    hit(163.75, RIM, 28, push=4.0, jit=9.0)

    # bar 42
    for i in range(8):
        hit(164.0 + i * 0.5 + (0.02 if i % 2 else 0.0),
            RIDE, 60 if i % 2 == 0 else 44)
    hit(164.0, KICK, 78)
    hit(165.75, KICK, 60)
    hit(166.5, KICK, 66)
    hit(165.0, RIM, 64)
    hit(167.0, SNARE, 70)
    hit(165.0, HATP, 42)
    hit(167.0, HATP, 44)
    hit(165.25, TOM_HM, 34, push=3.0)
    hit(166.75, TOM_ML, 32, push=3.0)

    # bar 43 : bell answers
    for i in range(8):
        hit(168.0 + i * 0.5, BELL if i % 2 == 0 else RIDE,
            68 if i % 2 == 0 else 46)
    hit(168.0, KICK, 82)
    hit(170.5, KICK, 70)
    hit(169.0, SNARE, 74)
    hit(171.0, SNARE, 80)
    hit(169.0, HATP, 44)
    hit(171.0, HATP, 46)
    hit(171.5, CONGA_H, 56)
    hit(171.75, CONGA_M, 60)

    # bar 44 : congas sing
    for i in range(4):
        hit(172.0 + i, BELL, 72 if i % 2 == 0 else 58)
    hit(172.0, KICK, 88)
    hit(173.0, CONGA_H, 66)
    hit(173.5, CONGA_M, 62)
    hit(174.0, CONGA_L, 68)
    hit(174.0, SNARE, 84)
    hit(175.5, SNARE, 40, push=4.0, jit=9.0)
    hit(175.75, TOM_ML, 60)

    # bars 45-46 : space, with a small pickup waiting to happen
    hit(176.0, KICK, 74)
    hit(176.0, HATP, 50)
    hit(176.0, RIDE, 60)
    hit(177.5, SNARE, 30, push=4.0, jit=9.0)
    hit(178.0, KICK, 68)
    hit(178.0, HATP, 48)
    hit(179.5, TOM_ML, 42)
    hit(180.0, KICK, 76)
    hit(180.0, RIDE, 62)
    hit(180.0, HATP, 52)
    hit(181.5, SNARE, 34, push=4.0, jit=9.0)
    hit(182.0, KICK, 72)
    hit(182.5, TOM_HM, 44)
    hit(182.75, TOM_ML, 48)
    hit(183.5, TOM_LO, 56)
    hit(183.75, SNARE, 64)


def sec_build():
    """bars 47-54 : the long crescendo back into the finale."""
    hit(184.0, KICK, 96)
    hit(184.0, HATP, 60)

    # bars 47-48 : hats, crescendo, 3-3-2 kick
    for b in range(2):
        t = 184.0 + 4 * b
        for i in range(8):
            v = (80 + 6 * b) if i % 2 == 0 else (58 + 5 * b)
            hit(t + i * 0.5, HAT, v)
        hit(t + 0.0, KICK, 102 + 6 * b)
        hit(t + 1.5, KICK, 88 + 6 * b)
        hit(t + 3.0, KICK, 94 + 6 * b)
        hit(t + 1.0, SNARE, 102 + 6 * b)
        hit(t + 3.0, SNARE, 106 + 6 * b)
        hit(t + 2.25, SNARE, 36, push=3.0)

    # bars 49-50 : snare sixteenths, 3-3-2 accents
    for b in range(2):
        t = 192.0 + 4 * b
        for i in range(16):
            v = 96 + 4 * b
            if i % 8 in (0, 3, 6):
                v += 12
            else:
                v -= 16 if i % 2 else 6
            hit(t + i * 0.25, SNARE, v)
        hit(t + 0.0, KICK, 110)
        hit(t + 2.0, KICK, 100)

    # bars 51-52 : run out and back around the kit
    run16(200.0, 32, [SNARE, TOM_HP, TOM_HM, TOM_ML, TOM_LO, TOM_FH,
                      TOM_FL, TOM_FL, TOM_FL, TOM_FH, TOM_LO, TOM_ML,
                      TOM_HM, TOM_HP, SNARE, SNARE], 104, 124, jit=3.5)
    hit(200.0, KICK, 112)
    hit(202.0, KICK, 108)
    hit(204.0, KICK, 114)
    hit(206.0, KICK, 110)

    # bars 53-54 : roll and cascade
    for i in range(32):
        v = 70 + 44 * (i / 31.0) + (8 if i % 8 == 0 else 0)
        hit(208.0 + i * 0.125, SNARE, v, jit=2.5)
    hit(208.0, KICK, 112)
    hit(210.0, KICK, 116)
    run16(212.0, 16, [TOM_HP, TOM_HM, TOM_ML, TOM_LO,
                      TOM_FH, TOM_FL, TOM_FL, TOM_FH], 108, 126,
          accent=0.0, jit=3.0)
    hit(212.0, KICK, 118)
    hit(214.0, KICK, 120)


def sec_finale():
    """bars 55-60 : everything, then land the last hit."""
    hit(216.0, CRASH, 124)
    hit(216.0, KICK, 124)

    # bars 55-58 : full-tilt with crash accents
    for b in range(4):
        t = 216.0 + 4 * b
        if b:
            hit(t, CRASH, 118)
        for i in range(16):
            v = 104 if i % 4 == 0 else (74 if i % 2 == 0 else 58)
            hit(t + i * 0.25, HAT, v)
        hit(t + 1.0, SNARE, 120)
        hit(t + 3.0, SNARE, 124)
        hit(t + 0.0, KICK, 124)
        hit(t + 2.5, KICK, 108)
        if b % 2 == 1:
            hit(t + 1.75, KICK, 100)
            hit(t + 3.5, TOM_HP, 100)
            hit(t + 3.75, TOM_HM, 104)
        else:
            hit(t + 3.75, KICK, 100)
        hit(t + 2.0, HATP, 66)

    # bar 59 : last big fill
    run16(232.0, 8, [SNARE, SNARE, TOM_HP, TOM_HM,
                     TOM_ML, TOM_LO, TOM_FH, TOM_FL], 112, 126, jit=3.0)
    run16(234.0, 8, [TOM_FL, TOM_FH, TOM_LO, TOM_ML,
                     TOM_HM, TOM_HP, SNARE, SNARE], 118, 127, jit=3.0)
    hit(232.0, KICK, 120)
    hit(234.0, KICK, 124)

    # bar 60 : the landing
    hit(236.0, CRASH, 124)
    hit(236.0, KICK, 124)
    hit(236.0, SNARE, 120)
    hit(236.5, HATP, 70)
    hit(237.0, SNARE, 74)
    hit(237.5, SNARE, 64)
    hit(237.75, TOM_HP, 84)
    hit(238.0, TOM_HM, 88)
    hit(238.0, KICK, 104)
    hit(238.25, TOM_ML, 92)
    hit(238.5, TOM_LO, 96)
    hit(238.75, TOM_FH, 100)
    hit(239.0, TOM_FL, 104)
    hit(239.0, KICK, 108)
    hit(239.5, SNARE, 100)
    hit(239.75, TOM_FL, 108)
    hit(239.9, SNARE, 120)
    # final chord: two hands, two feet, nothing after it
    hit(240.0, CRASH, 127)
    hit(240.0, CHINA, 120)
    hit(240.0, KICK, 127)
    hit(240.0, HATP, 80)


# ============================================================ MIDI assembly

def enforce_limbs():
    """Keep it playable: at most two hands and two feet at any instant."""
    ev = sorted(EV, key=lambda e: e[0])
    out = []
    for e in ev:
        t = e[0]
        w = ms2b(t, 24.0)
        conflict = []
        for o in reversed(out[-24:]):
            if t - o[0] > w:
                break
            if o[3] == e[3]:
                conflict.append(o)
        if len(conflict) >= 2:
            weakest = min(conflict, key=lambda o: o[2])
            if e[2] > weakest[2] + 8:
                out.remove(weakest)
                out.append(e)
            continue
        out.append(e)
    out.sort(key=lambda e: e[0])
    return out


def note_duration_beats(note, beat):
    if note in (CRASH, CRASH2, CHINA, SPLASH, RIDE, RIDE2, BELL, TRIANGLE, HATO):
        return ms2b(beat, 2000.0)
    if note in (TAMB, MARACAS, CABASA, CLAVES, WOOD_H, WOOD_L, COWBELL):
        return ms2b(beat, 180.0)
    return ms2b(beat, 80.0)


def write_midi(path):
    evs = enforce_limbs()

    ons = []
    for (t, note, vel, hand) in evs:
        tick = int(round(t * TPB))
        if tick < 0:
            tick = 0
        ons.append((tick, note, vel, t))

    offs = []
    for (tick, note, vel, t) in ons:
        d = note_duration_beats(note, t)
        offs.append(tick + max(2, int(round(d * TPB))))

    # never let a note-off collide with the next strike of the same drum
    nxt = {}
    for i in range(len(ons) - 1, -1, -1):
        n = ons[i][1]
        if n in nxt and offs[i] >= nxt[n]:
            offs[i] = max(ons[i][0] + 1, nxt[n] - 1)
        nxt[n] = ons[i][0]

    msgs = []
    for b in range(0, 241):
        msgs.append((b * TPB, 0,
                     mido.MetaMessage('set_tempo',
                                      tempo=int(round(60000000.0 / bpm_at(b))))))
    for i, (tick, note, vel, t) in enumerate(ons):
        msgs.append((tick, 2,
                     mido.Message('note_on', channel=CH, note=note,
                                  velocity=vel, time=0)))
        msgs.append((offs[i], 1,
                     mido.Message('note_off', channel=CH, note=note,
                                  velocity=64, time=0)))
    msgs.sort(key=lambda x: (x[0], x[1]))

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('time_signature', numerator=4,
                                  denominator=4, time=0))
    track.append(mido.Message('program_change', channel=CH, program=0, time=0))

    last = 0
    for tick, order, msg in msgs:
        d = tick - last
        if d < 0:
            d = 0
        msg.time = d
        last = tick
        track.append(msg)
    track.append(mido.MetaMessage('end_of_track', time=TPB // 2))

    mid.save(path)


def solo_length_seconds():
    total = 0.0
    b = 0.0
    step = 0.01
    while b < 240.0:
        total += step * 60.0 / bpm_at(b)
        b += step
    return total


def main():
    sec_intro()
    sec_statement()
    sec_dev1()
    sec_contrast()
    sec_rollbuild()
    sec_peak()
    sec_breakdown()
    sec_build()
    sec_finale()
    write_midi('solo.mid')
    print('solo.mid written: %d events, about %.1f seconds'
          % (len(EV), solo_length_seconds()))


if __name__ == '__main__':
    main()
