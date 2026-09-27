#!/usr/bin/env python3
"""
drum_solo.py - generates a ~2 minute General MIDI drum solo (solo.mid) on channel 10.

Only depends on mido. Output is deterministic: all "human" variation comes from a
fixed-seed RNG, and the feel (swing, push/lay-back) is applied as deliberate,
section-wide offsets.

Architecture
  * Every stroke is an event in beat time, tagged with the limb that plays it
    (R, L = hands; RF, LF = feet).
  * A resolver guarantees each limb strikes at most one thing at any instant,
    so at most two hands and two feet ever sound together.
  * A "feel" map applies swing and push/lay-back per section.
  * A tempo map leans forward in hot passages and settles back in relaxed ones.
    The base tempo is solved so the solo lands its final hit near the two-minute mark.

Main motif "A" (sixteenth grid, 3+3+4+2+2 grouping): slots 0, 3, 6, 10, 12, 14.
It is stated in the intro, grooved, displaced, compressed into 32nds, orchestrated
on Latin percussion, augmented, used for stop-time, and restated at the end.
"""
import math
import random

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

TPB = 480   # ticks per beat
CH = 9      # MIDI channel 10 (mido counts channels from 0)
rng = random.Random(1972)

# ---------------------------------------------------------------- GM notes
KICK2, KICK, XS, SN, CLAP, SN2 = 35, 36, 37, 38, 39, 40
F2, HH, F1, HHP, T4, HHO, T3, T2 = 41, 42, 43, 44, 45, 46, 47, 48
CR, T1, RIDE, CHINA, BELL, TAMB, SPL, COW, CR2, VIB, RIDE2 = (
    49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59)
BONGO_H, BONGO_L, CONGA_M, CONGA_O, CONGA_L = 60, 61, 62, 63, 64
TIMB_H, TIMB_L, AGO_H, AGO_L, CAB, MAR = 65, 66, 67, 68, 69, 70
GUI_S, GUI_L, CLAV, WB_H, WB_L, CUI_M, CUI_O, TRI_M, TRI_O = (
    73, 74, 75, 76, 77, 78, 79, 80, 81)

CYMBALS = {CR, CR2, CHINA, SPL, RIDE, RIDE2, BELL, HHO, TRI_O}

E = []  # events: [t_beats, note, vel, limb, offset_beats, dur_beats, grid_step]


def hit(t, note, vel, limb, off=0.0, dur=None, step=0.25):
    if note is None:
        return
    E.append([float(t), int(note), float(vel), limb, float(off), dur, float(step)])


def B(bar, beat=0.0):
    return bar * 4 + beat


# ---------------------------------------------------------------- building blocks
def run(start, n, step, sticking, notes, v0, v1, accents=(), boost=18, curve=1.0,
        kickvel=None):
    """A run of strokes following a sticking pattern (R, L, K = right foot kick,
    k = left foot kick). Velocity swells from v0 to v1. The second stroke of a
    double is played slightly softer, the way real hands play it."""
    prev = None
    for k in range(n):
        ch = sticking[k % len(sticking)]
        t = start + k * step
        x = k / (n - 1) if n > 1 else 1.0
        v = v0 + (v1 - v0) * (x ** curve)
        if k in accents:
            v += boost
        if ch in 'Kk':
            hit(t, KICK, kickvel if kickvel else v - 4,
                'RF' if ch == 'K' else 'LF', step=step)
            prev = ch
            continue
        if callable(notes):
            nt = notes(k, ch)
        elif len(notes) == n:
            nt = notes[k]
        else:
            nt = notes[min(len(notes) - 1, int(k * len(notes) / n))]
        if prev == ch:
            v -= 7
        hit(t, nt, v, ch, step=step)
        prev = ch


def roll(start, beats, note, v0, v1, rate=0.125, curve=1.6):
    """Double-stroke roll that swells."""
    n = int(round(beats / rate))
    run(start, n, rate, 'RRLL', [note], v0, v1, curve=curve)


# Main motif: (slot, contour index, accent weight)
MOTIF = [(0, 0, 1.0), (3, 1, 0.86), (6, 0, 0.94), (10, 3, 0.9), (12, 2, 0.86), (14, 0, 1.0)]


def motif(start, voices, acc=105, step=0.25, ghost=None, gvel=34, shift=0,
          slots=(0, 16), kicks=(0, 10), kvel=100, cym=None, cres=0.0, gcres=0.0):
    """Play motif A on a grid of alternating single strokes.

    Accents go to voices[contour]. The other slots get ghost notes, if a ghost
    note is given. `cym` maps motif positions to cymbal notes. `kicks` lists the
    motif positions that are doubled by the kick drum."""
    cym = cym or {}
    mp = {}
    for p, c, a in MOTIF:
        mp[(p + shift) % 16] = (p, c, a)
    for s in range(slots[0], slots[1]):
        t = start + s * step
        hand = 'R' if s % 2 == 0 else 'L'
        x = (s - slots[0]) / max(1, slots[1] - slots[0] - 1)
        if s in mp:
            p, c, a = mp[s]
            note = cym.get(p, voices[c])
            hit(t, note, acc * a + cres * x, hand, step=step)
            if p in kicks:
                hit(t, KICK, kvel * a, 'RF', step=step)
        elif ghost is not None:
            hit(t, ghost, gvel + gcres * x, hand, step=step)


def groove(bar, ride=False, crash_one=False, open_last=False, ghosts=(1.75, 2.25, 3.75),
           kicks=(0, 0.75, 2.5), extra_L=(), bell=(), fill_from=4.0):
    b0 = B(bar)
    for i in range(8):
        tb = i * 0.5
        if tb >= fill_from:
            break
        if i == 0 and crash_one:
            hit(b0, CR, 114, 'R', step=0.5, dur=1.5)
            continue
        if ride:
            note = RIDE
            v = (90 if i % 2 == 0 else 70) + (6 if i in (0, 4) else 0)
        else:
            note = HHO if (open_last and i == 7) else HH
            v = (96 if i % 2 == 0 else 64) + (8 if i in (0, 4) else 0)
        hit(b0 + tb, note, v, 'R', step=0.5)
    for tb in bell:
        if tb < fill_from:
            hit(b0 + tb, BELL, 104, 'R')
    for tb in (1.0, 3.0):
        if tb < fill_from:
            hit(b0 + tb, SN, 110, 'L', off=0.018, step=1.0)  # laid-back backbeat
    for tb in ghosts:
        if tb < fill_from:
            hit(b0 + tb, SN, 32 + (6 if (tb % 1) == 0.75 else 0), 'L')
    for tb in extra_L:
        if tb < fill_from:
            hit(b0 + tb, SN, 100, 'L', off=0.01)
    for tb in kicks:
        if tb < fill_from:
            hit(b0 + tb, KICK, 104 if tb % 1 == 0 else 86, 'RF')
    if ride:
        for tb in (1.0, 3.0):
            if tb < fill_from:
                hit(b0 + tb, HHP, 66, 'LF', step=1.0)
    if open_last and fill_from >= 4.0:
        hit(b0 + 4.0, HHP, 60, 'LF', step=1.0)  # foot closes the open hat


def dbass(start, beats, v=86, rate=0.25):
    n = int(round(beats / rate))
    for k in range(n):
        t = start + k * rate
        acc = 10 if abs(t - round(t)) < 1e-6 else 0
        hit(t, KICK, v + acc - (6 if k % 2 else 0), 'RF' if k % 2 == 0 else 'LF', step=rate)


def four_floor(bar, v0=98, v1=None, lf=True, lfv=58):
    for q in range(4):
        v = v0 if v1 is None else v0 + (v1 - v0) * q / 3
        hit(B(bar, q), KICK, v, 'RF', step=1.0)
        if lf:
            hit(B(bar, q + 0.5), HHP, lfv, 'LF', step=0.5)


def pedal(bar, beats, v=52):
    for q in beats:
        hit(B(bar, q), HHP, v, 'LF', step=1.0)


# ================================================================ THE SOLO
V0 = (SN, T1, T3, F1)   # the motif's "home" orchestration
CYC = [CR, CHINA, CR2, SPL, CR, CR2]

# ---------------- Section 1: Intro - state the motif (bars 0-3)
for b in range(3):
    for q in range(4):
        hit(B(b, q), HHP, 46 + (8 if q % 2 else 0), 'LF', step=1.0)
pedal(3, (0, 1), 54)
motif(B(0), V0, acc=94, kicks=(0, 10), kvel=92)
motif(B(1), V0, acc=98, ghost=SN, gvel=26, gcres=10, kicks=(0, 10), kvel=95)
motif(B(2), V0, acc=100, ghost=SN, gvel=30, gcres=6, slots=(0, 12), kicks=(0, 10))
run(B(2, 3), 4, 0.25, 'RL', [T2, T3, T4, F1], 84, 104)
hit(B(2, 3.5), KICK, 80, 'RF')
motif(B(3), V0, acc=104, ghost=SN, gvel=32, slots=(0, 8), kicks=(0,))
run(B(3, 2), 12, 1 / 6, 'RL', [SN, SN, T1, T1, T2, T2, T3, T3, T4, F1, F1, F2],
    70, 118, accents=(0, 3, 6, 9), boost=10, curve=1.3)
hit(B(3, 2), KICK, 90, 'RF')
hit(B(3, 3), KICK, 100, 'RF')

# ---------------- Section 2: Groove - motif hidden in the pocket (bars 4-11)
groove(4, crash_one=True, ghosts=(1.75, 2.25, 3.75))
groove(5, ghosts=(0.25, 1.75, 2.75, 3.75), kicks=(0, 0.75, 2.5, 3.25))
groove(6, ghosts=(1.75, 2.25, 2.75), open_last=True)
groove(7, ghosts=(0.25, 1.75, 2.75), fill_from=3.0)
run(B(7, 3), 6, 1 / 6, 'RLKRLK', [SN, T1, None, T3, F1, None], 88, 114)
groove(8, ride=True, crash_one=True, extra_L=(1.5, 3.5), ghosts=(2.25,))
groove(9, ride=True, bell=(0.75, 2.5), ghosts=(1.75, 2.25, 3.75))
groove(10, ride=True, ghosts=(0.25, 1.75, 2.25, 2.75, 3.75), kicks=(0, 0.75, 1.5, 2.5, 3.25))
groove(11, ride=True, fill_from=2.0, kicks=(0, 0.75), ghosts=(0.25, 1.75))
run(B(11, 2), 12, 1 / 6, 'RL', [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2],
    64, 120, accents=(0, 6), boost=12, curve=1.4)
hit(B(11, 2), KICK, 90, 'RF')
hit(B(11, 3), KICK, 100, 'RF')

# ---------------- Section 3: Development (bars 12-19)
motif(B(12), (SN, T1, T2, F1), acc=112, ghost=SN, gvel=40, cym={0: CR}, kicks=(0, 10))
pedal(12, (1, 2, 3), 56)
motif(B(13), (T1, T3, T1, F2), acc=108, ghost=SN, gvel=38, shift=2, kicks=(0, 10))
pedal(13, (0, 1, 2, 3), 56)


def pdnote(k, ch):
    if ch == 'R':
        return [T1, T2, T3, F1][k // 4]
    return SN


run(B(14), 16, 0.25, 'RLRRLRLL', pdnote, 50, 70, accents=(0, 4, 8, 12), boost=44)
for q in range(4):
    hit(B(14, q), KICK, 96, 'RF', step=1.0)
    hit(B(14, q + 0.5), HHP, 55, 'LF', step=0.5)

motif(B(15), (SN, T1, T2, F1), acc=106, step=0.125, ghost=SN, gvel=32, kicks=(0, 10))
motif(B(15, 2), (T2, T3, F1, F2), acc=112, step=0.125, ghost=SN, gvel=38,
      kicks=(0, 10), cym={0: CR})
pedal(15, (0, 1, 2, 3), 54)

# call and response
motif(B(16), (SN, T1, T2, F1), acc=115, ghost=SN, gvel=36, slots=(0, 8), cym={0: CR})
hit(B(16, 2), CR2, 120, 'R', dur=1.0)
hit(B(16, 2), SN, 115, 'L')
hit(B(16, 2), KICK, 110, 'RF')
hit(B(16, 2.75), CHINA, 104, 'L')
hit(B(16, 2.75), KICK, 95, 'RF')
hit(B(16, 3.5), SPL, 100, 'R')
hit(B(16, 3.5), KICK2, 92, 'LF')
hit(B(16, 3.0), HHP, 44, 'LF', step=1.0)
motif(B(17), (T1, T2, T3, F1), acc=114, ghost=SN, gvel=36, shift=2, slots=(0, 8), kicks=(0, 10, 14))
roll(B(17, 2), 2, SN, 28, 116)
hit(B(17, 2), KICK, 70, 'RF')
hit(B(17, 3), KICK, 86, 'RF')

path18 = [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2]


def n18(k, ch):
    if k == 0:
        return CR
    return path18[min(11, k * 12 // 24)]


run(B(18), 24, 1 / 6, 'RLRLK', n18, 76, 112, accents=tuple(range(0, 24, 5)), boost=16)
pedal(18, (1, 3), 50)
roll(B(19), 2, SN, 44, 118)
hit(B(19, 0), KICK, 84, 'RF', step=1.0)
hit(B(19, 1), KICK, 100, 'RF', step=1.0)
# big hit, then space
hit(B(19, 2), CR, 127, 'R', dur=1.8)
hit(B(19, 2), CHINA, 124, 'L', dur=1.5)
hit(B(19, 2), KICK, 127, 'RF')
hit(B(19, 2), KICK2, 120, 'LF')
hit(B(19, 3), HHP, 40, 'LF', step=1.0)
hit(B(19, 3.5), HHP, 34, 'LF', step=0.5)

# ---------------- Section 4: Breakdown - Latin colours (bars 20-27)
for b in range(20, 27):
    for tb, v in ((0, 72), (0.75, 48), (1.0, 60), (2, 70), (2.75, 48), (3, 60)):
        hit(B(b, tb), KICK, v, 'RF')
    hit(B(b, 1), HHP, 52, 'LF', step=1.0)
    hit(B(b, 3), HHP, 56, 'LF', step=1.0)

CASC_A = [0, 2, 4, 5, 7]
CASC_B = [0, 2, 3, 5, 7]


def cascara(bar, pat, note, base=66):
    for i in pat:
        hit(B(bar, i * 0.5), note, base + (12 if i in (0, 4) else 0), 'R', step=0.5)


def clave(bar, pos, note=XS, v=74):
    for p in pos:
        hit(B(bar, p), note, v, 'L', step=0.5)


CLAVE2 = [1.0, 2.0]
CLAVE3 = [0.0, 1.5, 3.0]
cascara(20, CASC_A, BELL, 60)
clave(20, CLAVE2)
hit(B(20), TRI_O, 70, 'L', dur=2.0)
cascara(21, CASC_B, BELL, 62)
clave(21, CLAVE3)
motif(B(22), (TIMB_H, CONGA_O, CONGA_L, TIMB_L), acc=90, ghost=CONGA_M, gvel=28, gcres=8, kicks=())
motif(B(23), (TIMB_H, CONGA_O, TIMB_L, CONGA_L), acc=92, ghost=CONGA_M, gvel=30, shift=8, kicks=())
for tb, nt, v in ((0, AGO_L, 80), (0.5, AGO_H, 60), (1.0, AGO_H, 66), (1.5, AGO_L, 70),
                  (2.0, AGO_H, 62), (2.5, AGO_L, 74), (3.0, AGO_H, 66)):
    hit(B(24, tb), nt, v, 'R', step=0.5)
hit(B(24, 3.5), VIB, 84, 'R', step=0.5, dur=1.0)
clave(24, CLAVE2, XS, 70)
motif(B(25), (AGO_H, WB_H, AGO_L, WB_L), acc=86, ghost=MAR, gvel=40, kicks=())
motif(B(26), (TIMB_H, T1, TIMB_L, F1), acc=98, ghost=SN, gvel=30, gcres=22, cres=10, kicks=())
run(B(27), 16, 0.25, 'RL',
    [TIMB_H, TIMB_H, TIMB_L, TIMB_L, T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2],
    52, 118, accents=(0, 3, 6, 10, 12, 14), boost=14, curve=1.2)
for q in range(4):
    hit(B(27, q), KICK, 70 + 12 * q, 'RF', step=1.0)
    hit(B(27, q + 0.5), HHP, 50 + 6 * q, 'LF', step=0.5)

# ---------------- Section 5: Build (bars 28-35)
motif(B(28), (SN, T1, T2, F1), acc=112, ghost=SN, gvel=46, cym={0: CR}, kicks=())
four_floor(28)
motif(B(29), (SN, T1, T3, F2), acc=114, ghost=SN, gvel=50, shift=4, kicks=())
four_floor(29)

circ = [SN, T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1, SN, T1, T2, T3]


def n30(k, ch):
    if k in (0, 16):
        return CR
    return circ[(k // 2) % len(circ)]


run(B(30), 32, 0.125, 'RRLL', n30, 78, 106, accents=(0, 8, 16, 24), boost=16)
four_floor(30, 100)

# half-time contrast
for i in range(6):
    hit(B(31, i * 0.5), CHINA, 96 if i % 2 == 0 else 72, 'R', step=0.5)
hit(B(31, 2), SN, 122, 'L', off=0.02, step=1.0)
for g in (0.75, 1.25, 2.75):
    hit(B(31, g), SN, 36, 'L')
for kk in (0, 0.75, 1.5):
    hit(B(31, kk), KICK, 104, 'RF')
hit(B(31, 1), HHP, 55, 'LF', step=1.0)
run(B(31, 3), 6, 1 / 6, 'RLRLKk', [T1, T2, None, T3, F1, None], 96, 118)

# motif with a swelling 32nd-note buzz between the accents
mpos = {p: (c, a) for p, c, a in MOTIF}
for s in range(32):
    t = B(32, s * 0.125)
    hand = 'R' if s % 2 == 0 else 'L'
    x = s / 31
    if s % 2 == 0 and s // 2 in mpos:
        c, a = mpos[s // 2]
        note = CR if s == 0 else (SN, T1, T2, F1)[c]
        hit(t, note, 116 * a, hand, step=0.125)
    else:
        hit(t, SN, 24 + 46 * x ** 1.3, hand, step=0.125)
four_floor(32, 96, 110)

roll(B(33), 4, SN, 30, 122)
four_floor(33, 70, 118, lf=True, lfv=50)

motif(B(34), (SN, T1, T2, F1), acc=122, ghost=SN, gvel=44,
      cym={0: CR, 6: CR2, 10: CHINA, 14: CR}, kicks=(0, 3, 6, 10, 12, 14))
pedal(34, (1, 2), 58)

run(B(35), 12, 1 / 6, 'RLRLKk', [T1, T1, T2, T2, T3, T3, T4, T4], 92, 110, accents=(0, 6), boost=10)
run(B(35, 2), 16, 0.125, 'RL', [T1, T2, T3, T4, F1, F2], 96, 124)
hit(B(35, 2), KICK, 105, 'RF', step=1.0)
hit(B(35, 3), KICK, 110, 'RF', step=1.0)
hit(B(35, 2.5), KICK, 100, 'LF', step=0.5)
hit(B(35, 3.5), KICK, 106, 'LF', step=0.5)

# ---------------- Section 6: Climax (bars 36-45)
dbass(B(36), 4)
for i, (p, c, a) in enumerate(MOTIF):
    t = B(36, p * 0.25)
    hit(t, CYC[i], 122 * a, 'R', dur=1.0)
    hit(t, SN, 118 * a, 'L')
dbass(B(37), 4)
for i, (p, c, a) in enumerate(MOTIF[:3]):
    t = B(37, p * 0.25)
    hit(t, CYC[i], 122 * a, 'R', dur=1.0)
    hit(t, SN, 118 * a, 'L')
run(B(37, 2), 8, 0.25, 'RL', [T1, T2, T2, T3, T4, F1, F1, F2], 84, 112, accents=(2, 4, 6), boost=14)


def n38(k, ch):
    if k % 12 == 0:
        return CR
    return [T1, T2, T3, T4, F1, F2][(k // 2) % 6]


run(B(38), 24, 1 / 6, 'RLRLKk', n38, 96, 116, accents=tuple(range(0, 24, 6)), boost=12)

motif(B(39), (SN, T1, T3, F1), acc=118, ghost=SN, gvel=58, shift=1, kicks=())
for i in range(8):
    hit(B(39, i * 0.5), KICK, 100, 'RF', step=0.5)
pedal(39, (1, 3), 56)

# motif augmented over two bars, toms travelling underneath, double bass
aug = {p * 2: (c, a) for p, c, a in MOTIF}
tpath = [SN, T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1]
ci = 0
for s in range(32):
    t = B(40, s * 0.25)
    hand = 'R' if s % 2 == 0 else 'L'
    x = s / 31
    if s in aug:
        c, a = aug[s]
        hit(t, CYC[ci % len(CYC)], 124 * a, 'R', dur=1.0)
        hit(t, SN, 116 * a, 'L')
        ci += 1
    else:
        hit(t, tpath[(s // 2) % len(tpath)], 58 + 38 * x, hand)
dbass(B(40), 8, v=84)

for beat in range(4):
    g = [CR, T1, T1, T2, T3, T4, F1, F2] if beat % 2 == 0 else [CHINA, SN, T1, T2, T3, T4, F1, F2]
    run(B(42, beat), 8, 0.125, 'RL', g, 88, 112, accents=(0,), boost=24)
    hit(B(42, beat), KICK, 110, 'RF', step=1.0)
    hit(B(42, beat + 0.5), KICK, 95, 'LF', step=0.5)


def n43(k, ch):
    i = k % 6
    if k == 0:
        return CR
    if i == 0:
        return [T1, T2, T3, F1][k // 6]
    if i == 5:
        return [T2, T3, F1, F2][k // 6]
    return SN


run(B(43), 24, 1 / 6, 'RLLRRL', n43, 58, 78,
    accents=tuple(k for k in range(24) if k % 6 in (0, 5)), boost=45)
for q in range(4):
    hit(B(43, q), KICK, 108, 'RF', step=1.0)
    hit(B(43, q + 0.5), KICK, 92, 'LF', step=0.5)

# stop-time: the motif as full-kit hits with silence in between
for i, (p, c, a) in enumerate(MOTIF):
    t = B(44, p * 0.25)
    hit(t, CYC[i], 126 * a, 'R', dur=1.0)
    hit(t, SN, 124 * a, 'L')
    hit(t, KICK, 120 * a, 'RF')
    hit(t, KICK2, 110 * a, 'LF')
pedal(44, (1.0, 2.0), 48)
for i, (p, c, a) in enumerate(MOTIF[:3]):
    t = B(45, p * 0.25)
    hit(t, CYC[i + 2], 126 * a, 'R', dur=1.0)
    hit(t, SN, 124 * a, 'L')
    hit(t, KICK, 120 * a, 'RF')
    hit(t, KICK2, 110 * a, 'LF')
pedal(45, (1.0,), 48)
run(B(45, 2), 12, 1 / 6, 'RL', [SN, T1, T1, T2, T2, T3, T3, T4, F1, F1, F2, F2], 80, 122, curve=1.3)
hit(B(45, 2), KICK, 96, 'RF', step=1.0)
hit(B(45, 3), KICK, 108, 'RF', step=1.0)

# ---------------- Section 7: Finale - the motif returns, then land it (bars 46-49)
motif(B(46), V0, acc=118, ghost=SN, gvel=40, cym={0: CR}, kicks=(0, 10), kvel=110)
pedal(46, (1, 2, 3), 58)
motif(B(47), V0, acc=116, ghost=SN, gvel=44, slots=(0, 8), kicks=(0, 6))
pedal(47, (1,), 56)
run(B(47, 2), 12, 1 / 6, 'RLRLKk', [T1, T2, T3, T4, F1, F2], 96, 120, accents=(0, 6), boost=8)
roll(B(48), 3.5, SN, 54, 124)
four_floor(48, 80, 112, lf=False)
hit(B(48, 3.5), KICK, 116, 'RF', step=0.5)
run(B(48, 3.5), 4, 0.125, 'RL', [T2, T3, F1, F2], 118, 126)
# THE final hit
FINAL = B(49)
hit(FINAL, CR, 127, 'R', dur=4.0)
hit(FINAL, CR2, 124, 'L', dur=4.0)
hit(FINAL, KICK, 127, 'RF', dur=2.0)
hit(FINAL, KICK2, 122, 'LF', dur=2.0)

# ================================================================ FEEL & TEMPO
FEEL = [
    (0,   dict(sw16=0.020, sw8=0.0,   hand=0.000,  foot=0.000)),
    (16,  dict(sw16=0.035, sw8=0.0,   hand=0.006,  foot=0.000)),   # laid-back groove
    (48,  dict(sw16=0.015, sw8=0.0,   hand=-0.004, foot=-0.002)),
    (80,  dict(sw16=0.000, sw8=0.045, hand=0.012,  foot=0.004)),   # relaxed, behind the beat
    (112, dict(sw16=0.012, sw8=0.0,   hand=-0.006, foot=-0.003)),  # leaning in
    (144, dict(sw16=0.000, sw8=0.0,   hand=-0.010, foot=-0.005)),  # on top of the beat
    (176, dict(sw16=0.000, sw8=0.0,   hand=0.004,  foot=0.000)),
    (184, dict(sw16=0.015, sw8=0.0,   hand=0.000,  foot=0.000)),
]


def feel_at(t):
    f = FEEL[0][1]
    for b, d in FEEL:
        if t >= b - 1e-9:
            f = d
    return f


ANCH = [(0, 0.96), (16, 1.0), (48, 1.0), (79.99, 1.045), (80, 0.93), (104, 0.95),
        (111.99, 0.97), (112, 1.0), (140, 1.06), (144, 1.07), (175.99, 1.10),
        (176, 1.03), (184, 1.03), (192, 1.02), (196, 0.90), (220, 0.90)]


def tf(b):
    if b <= ANCH[0][0]:
        return ANCH[0][1]
    for (b0, f0), (b1, f1) in zip(ANCH, ANCH[1:]):
        if b0 <= b <= b1:
            if b1 == b0:
                return f1
            return f0 + (f1 - f0) * (b - b0) / (b1 - b0)
    return ANCH[-1][1]


# ================================================================ RENDER
def resolve(events):
    """One stroke per limb per instant: keep the strongest one."""
    best = {}
    for e in events:
        key = (round(e[0] * 960), e[3])
        if key not in best or e[2] > best[key][2]:
            best[key] = e
    return sorted(best.values(), key=lambda e: (e[0], e[3], e[1]))


def render():
    evs = resolve(E)
    notes = {}
    for t, note, vel, limb, off, dur, step in evs:
        f = feel_at(t)
        frac = t - math.floor(t)
        sh = 0.0
        if step >= 0.249 and (abs(frac - 0.25) < 1e-6 or abs(frac - 0.75) < 1e-6):
            sh += f['sw16']
        if step >= 0.499 and abs(frac - 0.5) < 1e-6:
            sh += f['sw8']
        lo = f['hand'] if limb in ('R', 'L') else f['foot']
        if vel < 50:
            lo += 0.006  # ghost notes sit a hair late
        jit = rng.uniform(-0.003, 0.003)
        if abs(t - FINAL) < 1e-9:
            sh, lo, jit = 0.0, 0.0, 0.0
        tick = max(0, int(round((t + sh + off + lo + jit) * TPB)))
        v = max(12, min(127, int(round(vel + rng.randint(-3, 3)))))
        if dur is None:
            dur = 1.0 if note in CYMBALS else 0.25
        key = (tick, note)
        if key not in notes or v > notes[key][0]:
            notes[key] = (v, dur)
    # note-offs, clipped so they never cut a following strike of the same note
    by_note = {}
    for (tick, note), (v, dur) in notes.items():
        by_note.setdefault(note, []).append((tick, v, dur))
    msgs = []
    for note, lst in by_note.items():
        lst.sort()
        for i, (tick, v, dur) in enumerate(lst):
            off_tick = tick + int(dur * TPB)
            if i + 1 < len(lst):
                off_tick = min(off_tick, lst[i + 1][0] - 1)
            off_tick = max(off_tick, tick + 1)
            msgs.append((tick, 1, note, Message('note_on', channel=CH, note=note, velocity=v)))
            msgs.append((off_tick, 0, note, Message('note_off', channel=CH, note=note, velocity=0)))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))
    return msgs


def main():
    msgs = render()
    last_tick = max(m[0] for m in msgs)

    n_beats = int(math.ceil(last_tick / TPB)) + 1
    factors = [tf(i) for i in range(n_beats)]
    target = 117.0  # seconds until the final hit (plus ring-out, about two minutes)
    final_beat = int(FINAL)
    base = sum(60.0 / f for f in factors[:final_beat]) / target

    mid = MidiFile(type=1, ticks_per_beat=TPB)
    tempo_tr = MidiTrack()
    mid.tracks.append(tempo_tr)
    tempo_tr.append(MetaMessage('track_name', name='Tempo', time=0))
    tempo_tr.append(MetaMessage('time_signature', numerator=4, denominator=4,
                                clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    prev_tick, prev_tempo = 0, None
    for i, f in enumerate(factors):
        tempo = int(mido.bpm2tempo(base * f))
        if tempo != prev_tempo:
            tick = i * TPB
            tempo_tr.append(MetaMessage('set_tempo', tempo=tempo, time=tick - prev_tick))
            prev_tick, prev_tempo = tick, tempo
    tempo_tr.append(MetaMessage('end_of_track', time=0))

    dr = MidiTrack()
    mid.tracks.append(dr)
    dr.append(MetaMessage('track_name', name='Drum Solo', time=0))
    dr.append(Message('program_change', channel=CH, program=0, time=0))
    dr.append(Message('control_change', channel=CH, control=7, value=112, time=0))
    dr.append(Message('control_change', channel=CH, control=10, value=64, time=0))
    prev = 0
    for tick, _, _, msg in msgs:
        dr.append(msg.copy(time=tick - prev))
        prev = tick
    dr.append(MetaMessage('end_of_track', time=TPB // 2))

    mid.save('solo.mid')
    print('Wrote solo.mid: %.1f s, base tempo %.1f BPM, %d notes'
          % (mid.length, base, len(msgs) // 2))


if __name__ == '__main__':
    main()
