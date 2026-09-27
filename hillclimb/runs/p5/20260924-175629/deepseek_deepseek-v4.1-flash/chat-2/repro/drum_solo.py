#!/usr/bin/env python3
"""drum_solo.py

Generates ``solo.mid`` - a two minute General MIDI drum solo on channel 10.

The piece is written out bar by bar as a (beat, note, velocity) score, then
"performed": every note is given human timing (push/pull warp + jitter),
human dynamics, and the result is filtered so that never more than two hands
and two feet strike at the same instant.
"""

import math
import random

import mido

# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------
SEED = 20240607
random.seed(SEED)

PPQ = 480
BPM = 120
BEAT = PPQ                      # ticks per quarter note
TOTAL_BEATS = 240               # 60 bars of 4/4 -> exactly 2:00 at 120 BPM

# --------------------------------------------------------------------------
# General MIDI percussion voices (notes 35..81)
# --------------------------------------------------------------------------
BD, BD2 = 36, 35
SD, SS, ES = 38, 37, 40
HH, HHO, HHP = 42, 46, 44
RIDE, RIDE2 = 51, 59
BELL = 53
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
T_HI, T_HIMID, T_LOMID, T_LOW = 50, 48, 47, 45
T_HIFLOOR, T_LOFLOOR = 43, 41
CONGA_H, CONGA_M, CONGA_L = 63, 62, 64
BONGO_H, BONGO_L = 60, 61
COWBELL, CLAVES = 56, 75
WOODH, WOODL = 76, 77
TAMB, CABASA, MARACAS = 54, 69, 70
TRI_M, TRI_O = 80, 81

FEET = frozenset((35, 36, 44))

# --------------------------------------------------------------------------
# Score storage
# --------------------------------------------------------------------------
_events = []                    # (beat, note, velocity)


def hit(t, note, vel):
    _events.append((float(t), int(note), float(vel)))


def bar(n):
    """First beat of bar *n* (1-indexed)."""
    return (n - 1) * 4.0


# --------------------------------------------------------------------------
# Fill / run helpers
# --------------------------------------------------------------------------
def f_seq(b0, start, step, notes, v0, v1):
    """A linear run of *notes* starting at b0+start, one every *step* beats."""
    n = len(notes)
    for i, nt in enumerate(notes):
        v = v0 + (v1 - v0) * (i / (n - 1)) if n > 1 else v0
        hit(b0 + start + i * step, nt, v)


def f_roll(b0, start, dur, note, v0, v1, step=0.125):
    """A roll (buzz / single stroke) on a single voice."""
    n = max(1, int(round(dur / step)))
    for i in range(n):
        v = v0 + (v1 - v0) * (i / (n - 1)) if n > 1 else v0
        hit(b0 + start + i * step, note, v)


def f_doubles(b0, start, notes, v0, v1, step=0.125):
    """Each voice struck twice - the classic 'doubles around the kit'."""
    total = len(notes) * 2
    idx = 0
    for nt in notes:
        for _ in range(2):
            v = v0 + (v1 - v0) * (idx / (total - 1)) if total > 1 else v0
            hit(b0 + start + idx * step, nt, v)
            idx += 1


# --------------------------------------------------------------------------
# Bar patterns (motifs)
# --------------------------------------------------------------------------
def g_ride(b0, v=1.0, note=RIDE):
    """MOTIF A - ride/hi-hat eighths, backbeat, ghost notes, syncopated kick."""
    for i in range(8):
        vel = 100.0 if i % 2 == 0 else 68.0
        if i == 0:
            vel = 94.0
        hit(b0 + i * 0.5, note, vel * v)
    hit(b0 + 1.0, SD, 106 * v)
    hit(b0 + 3.0, SD, 108 * v)
    hit(b0 + 0.75, SD, 30 * v)
    hit(b0 + 2.75, SD, 34 * v)
    hit(b0 + 3.75, SD, 28 * v)
    hit(b0 + 0.0, BD, 100 * v)
    hit(b0 + 1.5, BD, 90 * v)
    hit(b0 + 2.5, BD, 86 * v)


def g_busy(b0, v=1.0):
    """Busier variant of motif A with a tom punctuating the second half."""
    hit(b0 + 0.0, HH, 96 * v)
    hit(b0 + 0.0, BD, 104 * v)
    hit(b0 + 0.5, HH, 68 * v)
    hit(b0 + 1.0, SD, 108 * v)
    hit(b0 + 1.25, SD, 30 * v)
    hit(b0 + 1.5, HH, 70 * v)
    hit(b0 + 1.5, BD, 92 * v)
    hit(b0 + 2.0, T_HI, 92 * v)
    hit(b0 + 2.0, BD, 100 * v)
    hit(b0 + 2.5, HH, 72 * v)
    hit(b0 + 2.75, SD, 34 * v)
    hit(b0 + 3.0, SD, 110 * v)
    hit(b0 + 3.5, HH, 70 * v)
    hit(b0 + 3.5, BD, 88 * v)
    hit(b0 + 3.75, SD, 40 * v)


def g_half(b0, v=1.0):
    """Half-time feel - space, ghost notes, pedal hat on the foot."""
    hit(b0 + 0.0, HH, 78 * v)
    hit(b0 + 0.0, BD, 96 * v)
    hit(b0 + 0.5, SD, 24 * v)
    hit(b0 + 1.0, HH, 66 * v)
    hit(b0 + 1.0, HHP, 58 * v)
    hit(b0 + 1.75, SD, 28 * v)
    hit(b0 + 2.0, HH, 80 * v)
    hit(b0 + 2.0, SD, 112 * v)
    hit(b0 + 2.5, BD, 86 * v)
    hit(b0 + 3.0, HH, 66 * v)
    hit(b0 + 3.0, HHP, 56 * v)
    hit(b0 + 3.0, BD, 78 * v)
    hit(b0 + 3.75, SD, 30 * v)


def g_toms(b0, v=1.0):
    """Melodic tom groove."""
    hit(b0 + 0.00, T_LOMID, 100 * v)
    hit(b0 + 0.00, BD, 96 * v)
    hit(b0 + 0.50, T_HIMID, 68 * v)
    hit(b0 + 0.75, SD, 30 * v)
    hit(b0 + 1.00, T_HI, 90 * v)
    hit(b0 + 1.50, T_HI, 60 * v)
    hit(b0 + 2.00, T_LOW, 104 * v)
    hit(b0 + 2.00, SD, 42 * v)
    hit(b0 + 2.50, T_LOMID, 72 * v)
    hit(b0 + 2.50, BD, 88 * v)
    hit(b0 + 3.00, T_HIFLOOR, 94 * v)
    hit(b0 + 3.50, T_LOFLOOR, 82 * v)
    hit(b0 + 3.75, SD, 52 * v)


def g_bell(b0, v=1.0):
    """Quiet ride-bell motif with soft snare answers."""
    hit(b0 + 0.00, BELL, 88 * v)
    hit(b0 + 0.00, BD, 74 * v)
    hit(b0 + 0.75, BELL, 62 * v)
    hit(b0 + 1.00, SD, 28 * v)
    hit(b0 + 1.50, BELL, 74 * v)
    hit(b0 + 2.00, BELL, 88 * v)
    hit(b0 + 2.00, SD, 46 * v)
    hit(b0 + 2.50, BD, 68 * v)
    hit(b0 + 2.75, BELL, 60 * v)
    hit(b0 + 3.00, SD, 30 * v)
    hit(b0 + 3.50, BELL, 72 * v)


# --------------------------------------------------------------------------
# The piece
# --------------------------------------------------------------------------
def build_piece():
    # ================= 1. INTRO (bars 1-2) =================
    b = bar(1)
    hit(b + 0.00, SS, 58)
    hit(b + 1.00, SD, 42)
    hit(b + 2.00, SS, 74)
    hit(b + 2.50, SD, 36)
    hit(b + 3.00, SD, 56)
    hit(b + 3.25, SD, 64)
    hit(b + 3.50, SD, 72)
    hit(b + 3.75, SD, 80)

    b = bar(2)
    hit(b + 0.00, SD, 44)
    hit(b + 0.00, BD, 62)
    hit(b + 0.50, SD, 36)
    hit(b + 1.00, SD, 50)
    hit(b + 1.50, SD, 42)
    hit(b + 2.00, SD, 58)
    hit(b + 2.50, SD, 50)
    hit(b + 3.00, SD, 66)
    hit(b + 3.25, SD, 60)
    hit(b + 3.50, SD, 76)
    hit(b + 3.75, SD, 88)

    # ============ 2. MOTIF A - STATEMENT (bars 3-6) ============
    b = bar(3)
    hit(b, CRASH, 114)
    g_ride(b, 1.00)
    g_ride(bar(4), 1.00)
    g_ride(bar(5), 1.00, note=HH)

    b = bar(6)
    for i in range(4):
        hit(b + i * 0.5, HH, 96 if i % 2 == 0 else 70)
    hit(b + 0.00, BD, 100)
    hit(b + 0.75, SD, 30)
    hit(b + 1.00, SD, 104)
    hit(b + 1.50, BD, 88)
    f_seq(b, 2.0, 0.25,
          [SD, SD, T_HI, T_HI, T_HIMID, T_LOMID, T_LOW, T_LOFLOOR],
          60, 104)

    # ============ 3. DEVELOPMENT OF A (bars 7-10) ============
    b = bar(7)
    for i in range(8):
        note, vel = HH, (96 if i % 2 == 0 else 70)
        if i == 5:
            note, vel = T_HI, 88
        if i == 7:
            note, vel = T_HIMID, 82
        hit(b + i * 0.5, note, vel)
    hit(b + 0.00, BD, 102)
    hit(b + 0.75, SD, 30)
    hit(b + 1.00, SD, 106)
    hit(b + 1.50, BD, 88)
    hit(b + 2.50, BD, 92)
    hit(b + 2.75, SD, 32)
    hit(b + 3.00, SD, 108)
    hit(b + 3.50, BD, 80)

    b = bar(8)
    for i in range(8):
        note = HHO if i == 6 else HH
        vel = 96 if i % 2 == 0 else 70
        if i == 6:
            vel = 86
        hit(b + i * 0.5, note, vel)
    hit(b + 0.00, BD, 100)
    hit(b + 0.75, SD, 30)
    hit(b + 1.00, SD, 106)
    hit(b + 1.50, BD, 90)
    hit(b + 2.50, BD, 86)
    hit(b + 2.75, SD, 34)
    hit(b + 3.00, SD, 108)
    hit(b + 3.75, SD, 44)

    for n in (9, 10):
        b = bar(n)
        g_ride(b, 1.02, note=HH)
        hit(b + 2.25, SD, 60)

    # ================= 4. BUILD (bars 11-14) =================
    for k, n in enumerate((11, 12, 13)):
        b = bar(n)
        v = 0.82 + 0.08 * k
        for i in range(8):
            hit(b + i * 0.5, RIDE, (98 if i % 2 == 0 else 68) * v)
        hit(b + 0.0, BD, 98 * v)
        hit(b + 1.0, SD, 100 * v)
        hit(b + 1.5, BD, 88 * v)
        hit(b + 2.5, BD, 84 * v)
        hit(b + 3.0, SD, 104 * v)
        hit(b + 3.75, SD, 42 * v)

    b = bar(14)
    for i in range(4):
        hit(b + i * 0.5, RIDE, 98 if i % 2 == 0 else 70)
    hit(b + 0.0, BD, 102)
    hit(b + 1.0, SD, 106)
    hit(b + 1.5, BD, 96)
    f_seq(b, 1.5, 0.25,
          [SD, SD, SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW, T_HIFLOOR, T_LOFLOOR],
          62, 114)

    # ============ 5. SECTION B - BUSY / TOMS (bars 15-18) ============
    b = bar(15)
    hit(b, CRASH, 118)
    g_busy(b, 1.00)
    g_busy(bar(16), 1.02)
    g_toms(bar(17), 1.00)
    b = bar(18)
    g_toms(b, 1.03)
    f_seq(b, 3.0, 0.25, [SD, SD, T_HI, T_HIMID], 78, 106)

    # ============ 6. CONTRAST - HALF TIME (bars 19-22) ============
    for k, n in enumerate((19, 20, 21)):
        g_half(bar(n), 0.82 + 0.05 * k)

    b = bar(22)
    hit(b + 0.0, HH, 76)
    hit(b + 0.0, BD, 92)
    hit(b + 0.5, SD, 24)
    hit(b + 1.0, HH, 64)
    hit(b + 1.0, HHP, 56)
    hit(b + 1.75, SD, 26)
    hit(b + 2.0, HH, 78)
    hit(b + 2.0, SD, 108)
    hit(b + 2.5, BD, 84)
    f_seq(b, 3.0, 0.25, [SD, SD, T_HI, T_HIMID], 46, 86)

    # ============ 7. MOTIF A RETURNS (bars 23-26) ============
    b = bar(23)
    hit(b, CRASH2, 112)
    g_ride(b, 1.05, note=HH)
    g_ride(bar(24), 1.05, note=HH)
    g_ride(bar(25), 1.05, note=RIDE)

    b = bar(26)
    for i in range(4):
        hit(b + i * 0.5, RIDE, 98 if i % 2 == 0 else 70)
    hit(b + 0.0, BD, 102)
    hit(b + 1.0, SD, 106)
    hit(b + 1.5, BD, 90)
    f_seq(b, 2.0, 0.25,
          [SD, SD, SD, SD, T_HI, T_HI, T_HIMID, T_LOMID], 64, 110)

    # ============ 8. SINGLES AROUND THE KIT (bars 27-30) ============
    b = bar(27)
    f_seq(b, 0.0, 0.25,
          [SD] * 4 + [T_HI] * 2 + [T_HIMID] * 2 + [T_LOMID] * 2 +
          [T_LOW] * 2 + [T_HIFLOOR] * 2 + [T_LOFLOOR] * 2,
          72, 104)
    hit(b + 0.0, BD, 96)
    hit(b + 2.0, BD, 92)

    b = bar(28)
    f_seq(b, 0.0, 0.25,
          [SD, SD, T_HI, SD, T_HIMID, SD, T_LOMID, SD,
           T_LOW, T_HIFLOOR, T_LOFLOOR, T_LOW,
           T_HIFLOOR, T_LOFLOOR, SD, SD],
          70, 108)
    hit(b + 0.0, BD, 96)
    hit(b + 1.0, BD, 88)
    hit(b + 2.0, BD, 92)
    hit(b + 3.0, BD, 86)

    b = bar(29)
    f_doubles(b, 0.0,
              [T_HI, T_HIMID, T_LOMID, T_LOW,
               T_HIFLOOR, T_LOFLOOR, T_LOW, T_LOMID], 68, 106)
    hit(b + 0.0, BD, 100)
    hit(b + 2.0, BD, 96)
    f_doubles(b, 2.0,
              [T_HI, T_HIMID, T_LOMID, T_LOW,
               T_HIFLOOR, T_LOFLOOR, T_LOW, T_LOMID], 72, 110)

    b = bar(30)
    f_seq(b, 0.0, 0.25,
          [SD] * 8 + [T_HI, T_HIMID, T_LOMID, T_LOW,
                      T_HIFLOOR, T_LOFLOOR, SD, SD],
          74, 112)
    hit(b + 0.0, CRASH, 108)
    hit(b + 0.0, BD, 104)
    hit(b + 2.0, BD, 98)

    # ============ 9. TOMS / DOUBLES CRESCENDO (bars 31-34) ============
    for k, n in enumerate((31, 32, 33)):
        g_toms(bar(n), 0.80 + 0.09 * k)

    b = bar(34)
    f_roll(b, 0.0, 2.0, SD, 58, 100, step=0.125)
    f_seq(b, 2.0, 0.125,
          [SD, T_HI, SD, T_HIMID, SD, T_LOMID, SD, T_LOW,
           T_HIFLOOR, T_LOFLOOR, T_LOW, T_HIFLOOR, T_LOFLOOR, SD, SD, SD],
          90, 120)

    # ============ 10. QUIET - RIDE BELL (bars 35-38) ============
    b = bar(35)
    hit(b, CRASH, 90)
    g_bell(b, 0.85)
    g_bell(bar(36), 0.80)
    b = bar(37)
    g_bell(b, 0.86)
    hit(b + 1.25, CLAVES, 42)
    hit(b + 3.25, CLAVES, 40)
    b = bar(38)
    g_bell(b, 0.90)
    f_seq(b, 3.0, 0.25, [SD, T_HI, T_HIMID, T_LOMID], 60, 96)

    # ============ 11. BUILD - ROLLING TOMS (bars 39-42) ============
    for k, n in enumerate((39, 40, 41)):
        b = bar(n)
        v0 = 46 + 14 * k
        v1 = 70 + 14 * k
        f_seq(b, 0.0, 0.25,
              [T_LOFLOOR, T_HIFLOOR, T_LOW, T_LOMID,
               T_HIMID, T_HI, T_LOMID, T_LOW,
               T_HIFLOOR, T_LOFLOOR, T_HIFLOOR, T_LOW,
               T_LOMID, T_HIMID, T_HI, T_HIMID],
              v0, v1)
        hit(b + 0.0, BD, 84 + 8 * k)
        hit(b + 2.0, BD, 80 + 8 * k)

    b = bar(42)
    f_seq(b, 0.0, 0.25,
          [SD] * 8 + [T_HI, T_HIMID, T_LOMID, T_LOW,
                      T_HIFLOOR, T_LOFLOOR, SD, SD],
          84, 122)
    hit(b + 0.0, CRASH, 112)
    hit(b + 0.0, BD, 110)
    hit(b + 2.0, BD, 104)

    # ============ 12. CLIMAX (bars 43-46) ============
    b = bar(43)
    hit(b, CRASH, 120)
    g_ride(b, 1.10)
    g_ride(bar(44), 1.10)
    b = bar(45)
    hit(b, CRASH2, 118)
    g_ride(b, 1.10, note=HH)
    g_ride(bar(46), 1.10, note=HH)

    # ============ 13. FAST SINGLES (bars 47-50) ============
    b = bar(47)
    f_seq(b, 0.0, 0.25,
          [SD, T_HI, SD, T_HIMID, SD, T_LOMID, SD, T_LOW,
           SD, T_HIFLOOR, SD, T_LOFLOOR, SD, T_HIFLOOR, SD, T_LOW],
          78, 112)
    hit(b + 0.0, BD, 100)
    hit(b + 2.0, BD, 96)

    b = bar(48)
    f_doubles(b, 0.0,
              [SD, T_HI, T_HIMID, T_LOMID,
               T_LOW, T_HIFLOOR, T_LOFLOOR, T_LOW], 80, 112)
    hit(b + 0.0, BD, 102)
    f_doubles(b, 2.0,
              [SD, T_HI, T_HIMID, T_LOMID,
               T_LOW, T_HIFLOOR, T_LOFLOOR, T_LOW], 84, 116)

    b = bar(49)
    f_seq(b, 0.0, 0.25, [SD] * 16, 76, 118)
    hit(b + 0.0, BD, 104)
    hit(b + 2.0, BD, 100)

    b = bar(50)
    f_seq(b, 0.0, 0.25,
          [SD, SD, SD, SD, T_HI, T_HI, T_HIMID, T_HIMID,
           T_LOMID, T_LOMID, T_LOW, T_LOW,
           T_HIFLOOR, T_LOFLOOR, T_HIFLOOR, T_LOW],
          82, 118)
    hit(b + 0.0, CRASH, 116)
    hit(b + 0.0, BD, 108)
    hit(b + 2.0, BD, 102)

    # ============ 14. SETTLE (bars 51-54) ============
    g_half(bar(51), 0.86)
    g_half(bar(52), 0.92)
    g_ride(bar(53), 1.00, note=HH)

    b = bar(54)
    for i in range(4):
        hit(b + i * 0.5, HH, 96 if i % 2 == 0 else 70)
    hit(b + 0.0, BD, 100)
    hit(b + 1.0, SD, 104)
    hit(b + 1.5, BD, 90)
    f_seq(b, 2.0, 0.125,
          [SD, SD, SD, SD, T_HI, T_HI, T_HIMID, T_HIMID,
           T_LOMID, T_LOW, T_HIFLOOR, T_LOFLOOR,
           T_HIFLOOR, T_LOW, T_LOMID, T_HIMID],
          60, 110)

    # ============ 15. FINAL BUILD (bars 55-58) ============
    b = bar(55)
    hit(b, CRASH2, 112)
    hit(b + 0.0, BD, 106)
    f_doubles(b, 0.0,
              [SD, T_HI, T_HIMID, T_LOMID,
               T_LOW, T_HIFLOOR, T_LOFLOOR, T_LOW], 70, 100)
    f_doubles(b, 2.0,
              [SD, T_HI, T_HIMID, T_LOMID,
               T_LOW, T_HIFLOOR, T_LOFLOOR, T_LOW], 78, 108)

    swell = [SD, SD, T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOMID,
             T_LOW, T_LOW, T_HIFLOOR, T_HIFLOOR, T_LOFLOOR, T_LOFLOOR,
             T_LOW, T_LOMID] * 2

    for k, n in enumerate((56, 57, 58)):
        b = bar(n)
        v0 = 78 + 10 * k
        v1 = min(100 + 10 * k, 124)
        f_seq(b, 0.0, 0.125, swell, v0, v1)
        hit(b + 0.0, BD, 104 + 4 * k)
        hit(b + 2.0, BD, 102 + 4 * k)

    # ============ 16. FINALE (bars 59-60) ============
    b = bar(59)
    f_seq(b, 0.0, 0.125,
          [SD, SD, SD, SD, T_HI, T_HI, T_HI, T_HI,
           T_HIMID, T_HIMID, T_LOMID, T_LOMID,
           T_LOW, T_LOW, T_HIFLOOR, T_HIFLOOR,
           T_LOFLOOR, T_LOFLOOR, T_HIFLOOR, T_LOW,
           T_LOMID, T_LOMID, T_HIMID, T_HI, SD, SD, T_HI, T_HIMID,
           T_LOMID, T_LOW, T_HIFLOOR, T_LOFLOOR],
          96, 120)
    hit(b + 0.0, BD, 108)
    hit(b + 2.0, BD, 112)

    # the landing - loudest hit of the whole solo, left ringing
    b = bar(60)
    hit(b + 0.0, CRASH, 124)
    hit(b + 0.0, SD, 118)
    hit(b + 0.0, BD, 122)
    hit(b + 2.0, CRASH2, 104)
    hit(b + 2.0, BD, 100)
    hit(b + 3.0, T_LOFLOOR, 92)
    hit(b + 3.0, BD, 96)


# --------------------------------------------------------------------------
# "Performance": timing, dynamics, playability
# --------------------------------------------------------------------------
def humanize(evts):
    """Apply a slow push/pull, per-note jitter and velocity variation."""
    out = []
    for t, note, vel in evts:
        warp = 0.014 * math.sin(2.0 * math.pi * t / 30.0 + 0.7)
        jitter = random.gauss(0.0, 0.011)
        tick = int(round((t + warp + jitter) * BEAT))
        if tick < 0:
            tick = 0
        v = int(round(vel + random.gauss(0.0, 2.5)))
        v = max(1, min(127, v))
        out.append((tick, note, v))
    return out


WINDOW = 20          # ticks (~21 ms) treated as "the same instant"


def enforce_playable(evts):
    """Keep at most 2 hand-strikes and 2 foot-strikes at any instant."""
    evts = sorted(evts, key=lambda e: (e[0], -e[2], e[1]))
    kept = []
    for tick, note, vel in evts:
        hands = 0
        feet = 0
        for kt, kn, _kv in reversed(kept):
            if kt < tick - WINDOW:
                break
            if kn in FEET:
                feet += 1
            else:
                hands += 1
        is_foot = note in FEET
        if is_foot and feet >= 2:
            continue
        if (not is_foot) and hands >= 2:
            continue
        kept.append((tick, note, vel))
    return kept


def note_duration(note):
    if note in (49, 57, 55, 52):        # crashes / china / splash
        return 900
    if note == 46:                      # open hi-hat
        return 420
    if note in (42, 44):                # closed / pedal hat
        return 90
    if note in (51, 59, 53):            # ride / bell
        return 200
    return 20


# --------------------------------------------------------------------------
# MIDI assembly
# --------------------------------------------------------------------------
def build_midi(note_events, path='solo.mid'):
    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
    track.append(mido.MetaMessage('time_signature', numerator=4,
                                  denominator=4, time=0))

    raw = []
    for tick, note, vel in note_events:
        raw.append((tick, 1, note, vel))
        raw.append((tick + note_duration(note), 0, note, 0))
    raw.sort(key=lambda r: (r[0], r[1]))     # note-offs before note-ons

    now = 0
    for tick, is_on, note, vel in raw:
        if tick < now:
            tick = now
        delta = tick - now
        now = tick
        if is_on:
            track.append(mido.Message('note_on', channel=9, note=note,
                                      velocity=vel, time=delta))
        else:
            track.append(mido.Message('note_off', channel=9, note=note,
                                      velocity=0, time=delta))

    end_tick = TOTAL_BEATS * BEAT
    track.append(mido.MetaMessage('end_of_track',
                                  time=max(0, end_tick - now)))

    mid.save(path)
    return mid


def main():
    build_piece()
    performed = enforce_playable(humanize(_events))
    build_midi(performed, 'solo.mid')
    print('wrote solo.mid  (%d notes)' % len(performed))


if __name__ == '__main__':
    main()
