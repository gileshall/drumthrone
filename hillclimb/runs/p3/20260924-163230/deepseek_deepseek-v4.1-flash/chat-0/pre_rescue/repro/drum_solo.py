#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drum_solo.py

Writes a ~2 minute General MIDI drum solo to 'solo.mid' in the current
directory.  Everything happens on MIDI channel 10 (GM percussion, notes
35-81).  The output is deterministic: running the script twice produces
byte-for-byte identical files.

Musical plan (70 bars of 4/4 at 140 BPM = 120 seconds):

  bars  0- 1   intro, laid back, establishes the pulse
  bars  2- 5   MOTIF A stated and varied
  bars  6- 7   MOTIF A + fill carrying into the next downbeat
  bars  8-11   MOTIF A moved onto the toms, big fill
  bars 12-15   MOTIF B (busier, pushing the beat)
  bars 16-19   MOTIF B developed, big fill
  bars 20-23   breakdown - space, rim clicks, cowbell, laying back
  bars 24-31   build: singles, doubles, rolls that swell, pushing harder
  bars 32-39   PEAK - MOTIF A returns at full power
  bars 40-45   transition through congas/timbales, then release
  bars 46-51   release: sparse, relaxed, ghost notes, then rebuild
  bars 52-59   development: MOTIF B returns, rolls, fills
  bars 60-65   final build, crescendo
  bars 66-68   climax: fastest singles + a big roll that resolves
  bar  69      the last hit, left ringing
"""

import mido
from collections import defaultdict

# ----------------------------------------------------------------------
#  global timing
# ----------------------------------------------------------------------
TPB = 960                # ticks per quarter note
BPM = 140.0              # 70 bars of 4/4 == exactly 120 seconds
CH  = 9                  # MIDI channel 10 (zero based)

# ----------------------------------------------------------------------
#  General MIDI percussion key map
# ----------------------------------------------------------------------
KICK    = 36
KICK2   = 35
SNARE   = 38
RIM     = 37
CLAP    = 39
ESNARE  = 40
PHAT    = 44
HAT     = 42
OHAT    = 46
RIDE    = 51
BELL    = 53
RIDE2   = 59
CRASH   = 49
CRASH2  = 57
SPLASH  = 55
CHINA   = 52
FTL     = 41      # low floor tom
FTH     = 43      # high floor tom
TOML    = 45      # low tom
TOMLM   = 47      # low-mid tom
TOMHM   = 48      # hi-mid tom
TOMH    = 50      # high tom
BONGO_H = 60
BONGO_L = 61
CONGA_H = 62
CONGA_O = 63
CONGA_L = 64
TIMP_H  = 65
TIMP_L  = 66
AGOGO_H = 67
AGOGO_L = 68
CABASA  = 69
MARACAS = 70
CLAVES  = 75
WBLK_H  = 76
WBLK_L  = 77
TRI_M   = 80
TRI_O   = 81
TAMB    = 54
COWBELL = 56

# two feet: bass drum and pedal hi-hat.  everything else is a hand.
FEET = frozenset((KICK, KICK2, PHAT))

# ----------------------------------------------------------------------
#  event list and the timing "feel" machinery
# ----------------------------------------------------------------------
events = []          # (tick, note, velocity)
SWING  = 0.0         # 16th note swing, in beats (0.0 = straight)
LEAN   = 0.0         # laid back (+) / pushed (-), in ticks


def pos(bar, q):
    """Absolute beat position of offset q (in beats) inside bar `bar`."""
    base = bar * 4.0 + q
    f = q % 1.0
    if abs(f - 0.25) < 1e-9 or abs(f - 0.75) < 1e-9:
        base += SWING
    return base


def P(bar, i16):
    """Position of the i-th 16th note of the bar."""
    return pos(bar, i16 * 0.25)


def emit(p, note, vel):
    if note is None:
        return
    f = p % 1.0
    off = LEAN * (0.25 if f < 1e-9 else 1.0)
    t = int(round(p * TPB + off))
    if t < 0:
        t = 0
    v = int(max(1, min(127, round(vel))))
    events.append((t, note, v))


def h16(bar, i, note, vel):
    """Hit note `note` on the i-th 16th of bar `bar`."""
    emit(P(bar, i), note, vel)


def hat8(bar, vs):
    """Hi-hat on the 8th notes.  vs is 8 velocities (None = rest)."""
    for k, v in enumerate(vs):
        if v is not None:
            h16(bar, k * 2, HAT, v)


def swell(bar, i0, n16, note, v0, v1, rate=2):
    """A roll, `rate` strokes per 16th, `n16` sixteenths long."""
    total = int(n16 * rate)
    for k in range(total):
        slot = i0 + k / float(rate)
        b = bar + int(slot) // 16
        j = slot - (int(slot) // 16) * 16
        v = v0 + (v1 - v0) * (k / float(max(1, total - 1)))
        emit(pos(b, j * 0.25), note, v)


# ======================================================================
#  THE MOTIFS
# ======================================================================
def intro_bar(b, second):
    if not second:
        h16(b, 0, CRASH, 100)
    h16(b, 0, KICK, 112)
    h16(b, 4, SNARE, 108)
    h16(b, 8, KICK, 96)
    if second:
        h16(b, 10, KICK, 88)
    h16(b, 12, SNARE, 114 if second else 112)
    vs = [None, 74, 66, 62, 82, 64, 84, None if second else 66]
    hat8(b, vs)
    if second:
        h16(b, 14, OHAT, 90)
        h16(b, 15, SNARE, 34)


def bar_A(b, ohat=False):
    """MOTIF A - the hook.  One bar."""
    h16(b, 0, KICK, 114)
    h16(b, 6, KICK, 98)
    h16(b, 10, KICK, 102)
    h16(b, 13, KICK, 88)
    h16(b, 4, SNARE, 118)
    h16(b, 12, SNARE, 120)
    h16(b, 7, SNARE, 34)
    h16(b, 11, SNARE, 32)
    h16(b, 14, SNARE, 34)
    if ohat:
        hat8(b, [90, 66, 86, 64, 92, 68, 88, None])
        h16(b, 14, OHAT, 88)
    else:
        hat8(b, [90, 66, 86, 64, 92, 68, 88, 70])


def bar_A1(b):
    """MOTIF A, variation 1 - displaced kick, extra ghosts."""
    h16(b, 0, KICK, 114)
    h16(b, 3, KICK, 88)
    h16(b, 6, KICK, 96)
    h16(b, 9, KICK, 84)
    h16(b, 11, KICK, 104)
    h16(b, 13, KICK, 90)
    h16(b, 4, SNARE, 118)
    h16(b, 12, SNARE, 120)
    h16(b, 2, SNARE, 30)
    h16(b, 7, SNARE, 36)
    h16(b, 10, SNARE, 30)
    h16(b, 14, SNARE, 34)
    hat8(b, [92, 66, 88, 64, 94, 68, 90, 70])
    h16(b, 15, OHAT, 86)


def bar_A2(b):
    """MOTIF A, variation 2 - sixteenth-note hi-hat flow."""
    h16(b, 0, KICK, 116)
    h16(b, 3, KICK, 86)
    h16(b, 6, KICK, 100)
    h16(b, 10, KICK, 104)
    h16(b, 13, KICK, 92)
    h16(b, 4, SNARE, 120)
    h16(b, 12, SNARE, 122)
    h16(b, 7, SNARE, 38)
    h16(b, 11, SNARE, 36)
    h16(b, 14, SNARE, 38)
    hv = [96, 58, 64, 56, None, 60, 66, None,
          98, 58, 64, 56, None, 60, 68, None]
    for i, v in enumerate(hv):
        if v:
            h16(b, i, HAT, v)


def bar_A_toms(b):
    """MOTIF A with the right hand flowing around the toms."""
    h16(b, 0, KICK, 116)
    h16(b, 6, KICK, 98)
    h16(b, 10, KICK, 104)
    h16(b, 13, KICK, 92)
    h16(b, 4, SNARE, 120)
    h16(b, 12, SNARE, 122)
    h16(b, 7, SNARE, 38)
    h16(b, 11, SNARE, 36)
    h16(b, 14, SNARE, 38)
    toms = [TOMHM, TOMLM, TOMHM, TOMLM, TOMH, TOMLM, TOMHM, TOML]
    vs   = [84, 62, 80, 60, 88, 64, 82, 64]
    for k in range(8):
        h16(b, k * 2, toms[k], vs[k])


def bar_A_fill(b):
    """Half a bar of MOTIF A, half a bar of fill."""
    h16(b, 0, KICK, 116)
    h16(b, 4, SNARE, 120)
    h16(b, 6, KICK, 100)
    h16(b, 7, SNARE, 38)
    hv = [94, 58, 64, 56, None, 60, 66, None]
    for i, v in enumerate(hv):
        if v:
            h16(b, i, HAT, v)
    fill = [SNARE, SNARE, TOMH, TOMH,
            TOMHM, TOMLM, TOML, TOML,
            FTH, FTL, SNARE, SNARE,
            TOMHM, TOMLM, TOML, FTL]
    for k in range(8, 16):
        v = 108 if k % 2 == 0 else 92
        h16(b, k, fill[k], v)


def bar_B(b):
    """MOTIF B - busy, ride cymbal, syncopated kick."""
    h16(b, 0, KICK, 118)
    h16(b, 3, KICK, 88)
    h16(b, 7, KICK, 96)
    h16(b, 10, KICK, 104)
    h16(b, 13, KICK, 90)
    h16(b, 4, SNARE, 122)
    h16(b, 12, SNARE, 124)
    h16(b, 6, SNARE, 34)
    h16(b, 11, SNARE, 36)
    h16(b, 15, SNARE, 32)
    h16(b, 0, BELL, 102)
    h16(b, 8, BELL, 104)
    for i, v in ((2, 66), (4, 72), (6, 68), (10, 66), (12, 72), (14, 68)):
        h16(b, i, RIDE, v)


def bar_B1(b):
    h16(b, 0, KICK, 118)
    h16(b, 3, KICK, 90)
    h16(b, 6, KICK, 100)
    h16(b, 9, KICK, 86)
    h16(b, 11, KICK, 106)
    h16(b, 13, KICK, 92)
    h16(b, 4, SNARE, 122)
    h16(b, 12, SNARE, 124)
    h16(b, 2, SNARE, 34)
    h16(b, 7, SNARE, 36)
    h16(b, 10, SNARE, 32)
    h16(b, 14, SNARE, 36)
    h16(b, 0, BELL, 104)
    h16(b, 8, BELL, 106)
    for i, v in ((2, 68), (4, 74), (6, 70), (10, 68), (12, 74), (14, 70)):
        h16(b, i, RIDE, v)


def bar_B2(b):
    h16(b, 0, KICK, 120)
    h16(b, 3, KICK, 92)
    h16(b, 7, KICK, 98)
    h16(b, 10, KICK, 106)
    h16(b, 13, KICK, 94)
    h16(b, 4, SNARE, 122)
    h16(b, 12, SNARE, 124)
    h16(b, 6, SNARE, 34)
    h16(b, 11, SNARE, 36)
    h16(b, 15, SNARE, 32)
    h16(b, 0, BELL, 106)
    h16(b, 8, BELL, 106)
    for i, v in ((2, 68), (6, 70), (10, 68), (14, 70)):
        h16(b, i, RIDE, v)


def bar_B_toms(b):
    """MOTIF B with the right hand trading ride for toms."""
    h16(b, 0, KICK, 120)
    h16(b, 3, KICK, 92)
    h16(b, 7, KICK, 100)
    h16(b, 10, KICK, 106)
    h16(b, 13, KICK, 94)
    h16(b, 4, SNARE, 122)
    h16(b, 12, SNARE, 124)
    h16(b, 6, SNARE, 34)
    h16(b, 11, SNARE, 36)
    h16(b, 0, BELL, 106)
    h16(b, 8, BELL, 106)
    h16(b, 2, TOMH, 88)
    h16(b, 6, TOMHM, 82)
    h16(b, 10, TOMHM, 86)
    h16(b, 14, TOMLM, 80)
    h16(b, 4, TOML, 76)


def bar_break(b, variant):
    """Sparse, dramatic, laid back."""
    if variant == 0:
        h16(b, 0, KICK, 102)
        h16(b, 0, COWBELL, 94)
        h16(b, 4, RIM, 102)
        h16(b, 8, KICK, 94)
        h16(b, 8, COWBELL, 88)
        h16(b, 12, RIM, 106)
        h16(b, 14, SNARE, 32)
    elif variant == 1:
        h16(b, 0, KICK, 102)
        h16(b, 0, COWBELL, 94)
        h16(b, 3, RIM, 72)
        h16(b, 4, RIM, 102)
        h16(b, 6, SNARE, 58)
        h16(b, 8, KICK, 96)
        h16(b, 8, COWBELL, 90)
        h16(b, 11, RIM, 74)
        h16(b, 12, RIM, 106)
        h16(b, 14, SNARE, 34)
    elif variant == 2:
        h16(b, 0, KICK, 98)
        h16(b, 0, FTL, 90)
        h16(b, 4, RIM, 100)
        h16(b, 6, TOML, 82)
        h16(b, 8, KICK, 102)
        h16(b, 8, TOMLM, 86)
        h16(b, 10, TOMLM, 78)
        h16(b, 12, SNARE, 110)
        h16(b, 15, SNARE, 34)
    else:
        h16(b, 0, KICK, 104)
        h16(b, 4, SNARE, 110)
        h16(b, 6, TOMHM, 92)
        h16(b, 8, TOMH, 94)
        h16(b, 10, TOMHM, 90)
        h16(b, 12, SNARE, 112)
        h16(b, 12, TOML, 86)
        h16(b, 13, TOMLM, 88)
        h16(b, 14, TOMHM, 90)
        h16(b, 15, TOMH, 98)


def bar_latin(b, mut=0):
    h16(b, 0, KICK, 112)
    h16(b, 4, SNARE, 108)
    h16(b, 8, KICK, 102)
    h16(b, 12, SNARE, 112)
    if mut == 0:
        h16(b, 0, CRASH, 110)
        pat = [(0, CONGA_H, 94), (2, CONGA_O, 74), (3, CONGA_M, 82),
               (6, CONGA_O, 78), (8, CONGA_H, 96), (10, CONGA_O, 76),
               (11, CONGA_M, 84), (14, CONGA_O, 80)]
    else:
        pat = [(0, CONGA_H, 96), (2, BONGO_H, 78), (3, CONGA_M, 84),
               (5, BONGO_L, 72), (8, CONGA_H, 98), (9, BONGO_H, 76),
               (11, CONGA_M, 86), (13, BONGO_L, 74),
               (14, CONGA_O, 82), (15, CONGA_L, 80)]
    for i, n, v in pat:
        h16(b, i, n, v)


def bar_timbale(b, crash=False):
    if crash:
        h16(b, 0, CRASH, 108)
    h16(b, 0, KICK, 110)
    h16(b, 0, TIMP_H, 100)
    h16(b, 4, SNARE, 108)
    h16(b, 8, KICK, 100)
    h16(b, 12, SNARE, 110)
    pat = [(2, TIMP_L, 80), (3, TIMP_H, 86), (6, TIMP_L, 78), (7, TIMP_H, 84),
           (10, TIMP_L, 82), (11, TIMP_H, 88), (14, TIMP_L, 80), (15, TIMP_H, 94)]
    for i, n, v in pat:
        h16(b, i, n, v)


def big_fill(b):
    seq = [(SNARE, 112), (SNARE, 90), (TOMH, 106), (TOMHM, 94),
           (TOMHM, 102), (TOMLM, 90), (TOML, 98), (TOML, 100),
           (FTH, 106), (FTL, 94), (SNARE, 110), (SNARE, 92),
           (TOMH, 112), (TOMHM, 100), (TOMLM, 106), (FTL, 116)]
    for k, (n, v) in enumerate(seq):
        h16(b, k, n, v)


def big_fill2(b):
    seq = [(TOMHM, 104), (TOMLM, 88), (TOML, 96), (FTH, 92),
           (FTL, 100), (FTH, 94), (TOML, 102), (TOMLM, 90),
           (TOMHM, 106), (TOMH, 94), (TOMHM, 100), (TOMLM, 92),
           (TOML, 104), (FTH, 96), (FTL, 108), (SNARE, 118)]
    for k, (n, v) in enumerate(seq):
        h16(b, k, n, v)


# ======================================================================
#  SECTION 1 - INTRO  (bars 0-1)
# ======================================================================
LEAN, SWING = 14.0, 0.0
intro_bar(0, False)
intro_bar(1, True)

# ======================================================================
#  SECTION 2 - MOTIF A STATED AND VARIED  (bars 2-5)
# ======================================================================
LEAN, SWING = 12.0, 0.0
bar_A(2)
bar_A(3, ohat=True)
bar_A1(4)
bar_A2(5)

# ======================================================================
#  SECTION 3 - MOTIF A + FILL  (bars 6-7)
# ======================================================================
LEAN, SWING = 10.0, 0.0
bar_A2(6)
bar_A_fill(7)

# ======================================================================
#  SECTION 4 - MOTIF A ON THE TOMS  (bars 8-11)
# ======================================================================
LEAN, SWING = 8.0, 0.0
h16(8, 0, CRASH, 112)
bar_A(8)
bar_A1(9)
bar_A_toms(10)
big_fill(11)

# ======================================================================
#  SECTION 5 - MOTIF B  (bars 12-15)   pushing the beat
# ======================================================================
LEAN, SWING = -12.0, 0.015
h16(12, 0, CRASH, 110)
bar_B(12)
bar_B1(13)
bar_B(14)
bar_B2(15)

# ======================================================================
#  SECTION 6 - MOTIF B DEVELOPED  (bars 16-19)
# ======================================================================
LEAN, SWING = -14.0, 0.02
bar_B1(16)
bar_B2(17)
bar_B_toms(18)
big_fill2(19)

# ======================================================================
#  SECTION 7 - BREAKDOWN  (bars 20-23)   laying way back
# ======================================================================
LEAN, SWING = 18.0, 0.025
bar_break(20, 0)
bar_break(21, 1)
bar_break(22, 2)
bar_break(23, 3)

# ======================================================================
#  SECTION 8 - BUILD  (bars 24-31)
# ======================================================================
# bar 24 - space, one idea
LEAN, SWING = 0.0, 0.0
h16(24, 0, KICK, 110)
h16(24, 0, OHAT, 90)
h16(24, 4, SNARE, 116)
h16(24, 6, KICK, 96)
h16(24, 8, KICK, 104)
h16(24, 10, SNARE, 50)
h16(24, 12, SNARE, 118)
h16(24, 14, SNARE, 54)

# bar 25 - sixteenths wake up
LEAN = -3.0
h16(25, 0, KICK, 112)
h16(25, 4, SNARE, 120)
h16(25, 6, KICK, 98)
h16(25, 8, KICK, 106)
h16(25, 12, SNARE, 122)
for i, v in ((2, 58), (3, 66), (6, 60), (7, 68),
             (10, 62), (11, 70), (14, 64), (15, 74)):
    h16(25, i, SNARE, v)

# bar 26 - singles travelling snare -> toms
LEAN = -5.0
h16(26, 0, KICK, 114)
seq26 = [SNARE, SNARE, TOMH, TOMHM, TOMLM, TOML, TOML, FTH,
         FTL, FTL, SNARE, TOMH, TOMHM, TOMLM, TOML, FTL]
for i, n in enumerate(seq26):
    v = 108 if i % 4 == 0 else 84
    h16(26, i, n, v)

# bar 27 - doubles
LEAN = -7.0
h16(27, 0, KICK, 114)
dbl27 = [SNARE, SNARE, TOMH, TOMH, TOMHM, TOMHM, TOMLM, TOMLM,
         TOML, TOML, FTH, FTH, FTL, FTL, SNARE, SNARE]
for i, n in enumerate(dbl27):
    v = 112 if i % 2 == 0 else 84
    h16(27, i, n, v)

# bar 28 - second half is a 32nd roll that swells
LEAN = -9.0
h16(28, 0, KICK, 116)
h16(28, 0, CRASH2, 100)
h16(28, 4, SNARE, 120)
h16(28, 6, SNARE, 70)
h16(28, 7, SNARE, 78)
swell(28, 8, 8, SNARE, 60, 112, rate=2)

# bar 29 - winding around the toms
LEAN = -11.0
h16(29, 0, KICK, 118)
seq29 = [TOMHM, TOMH, TOMHM, TOMLM, TOML, TOMLM, TOML, FTH,
         FTL, FTH, FTL, TOML, TOMLM, TOMHM, TOMH, SNARE]
for i, n in enumerate(seq29):
    v = 112 if i % 4 == 0 else 86
    h16(29, i, n, v)

# bar 30 - high energy singles
LEAN = -13.0
h16(30, 0, KICK, 118)
seq30 = [SNARE, SNARE, TOMH, TOMLM, SNARE, SNARE, TOMHM, TOML,
         SNARE, SNARE, TOMH, TOMLM, SNARE, TOMHM, TOML, FTL]
for i, n in enumerate(seq30):
    v = 116 if i % 4 == 0 else 88
    h16(30, i, n, v)

# bar 31 - last push
LEAN = -15.0
h16(31, 0, KICK, 120)
seq31 = [SNARE, TOMH, TOMHM, TOMLM, TOML, FTH, FTL, SNARE,
         TOMH, TOMHM, TOMLM, TOML, FTH, FTL, SNARE, SNARE]
for i, n in enumerate(seq31):
    v = 118 if i % 4 == 0 else 92
    h16(31, i, n, v)
h16(31, 15, SNARE, 70)

# ======================================================================
#  SECTION 9 - PEAK : MOTIF A RETURNS  (bars 32-39)
# ======================================================================
LEAN, SWING = -8.0, 0.0
h16(32, 0, CRASH, 120)
bar_A(32)
bar_A1(33)
bar_A2(34)
h16(35, 0, CRASH, 116)
bar_A(35)
bar_A1(36)
bar_A2(37)
bar_A_toms(38)
big_fill(39)

# ======================================================================
#  SECTION 10 - TRANSITION  (bars 40-45)
# ======================================================================
LEAN, SWING = 6.0, 0.03
h16(40, 0, CRASH, 110)
bar_latin(40, 0)
bar_latin(41, 1)
bar_timbale(42, crash=True)
bar_timbale(43)

# bar 44 - backing off, decrescendo fill
LEAN = 10.0
h16(44, 0, KICK, 104)
seq44 = [SNARE, TOMHM, TOMLM, TOML, FTH, FTL, TOML, TOMHM,
         SNARE, TOMHM, TOMLM, TOML, FTH, FTL, TOML, TOMLM]
for i, n in enumerate(seq44):
    v = max(40, 96 - i * 2)
    h16(44, i, n, v)

# bar 45 - settle, leave space
LEAN = 12.0
h16(45, 0, KICK, 96)
h16(45, 4, SNARE, 88)
h16(45, 10, TOML, 70)
h16(45, 12, SNARE, 90)
h16(45, 14, SNARE, 34)

# ======================================================================
#  SECTION 11 - RELEASE  (bars 46-51)
# ======================================================================
LEAN, SWING = 14.0, 0.03

# bar 46
h16(46, 0, KICK, 100)
h16(46, 4, SNARE, 92)
h16(46, 8, KICK, 86)
h16(46, 12, SNARE, 96)
hat8(46, [72, 52, 66, 50, 74, 52, 68, 54])
h16(46, 14, SNARE, 30)

# bar 47
h16(47, 0, KICK, 100)
h16(47, 4, SNARE, 94)
h16(47, 8, KICK, 88)
h16(47, 12, SNARE, 98)
hat8(47, [74, 54, 68, 52, 76, 54, 70, 56])
h16(47, 0, TAMB, 70)
h16(47, 8, TAMB, 68)
h16(47, 7, SNARE, 32)
h16(47, 15, SNARE, 30)

# bar 48 - ride opens the sound up
h16(48, 0, KICK, 104)
h16(48, 4, SNARE, 96)
h16(48, 8, KICK, 92)
h16(48, 12, SNARE, 100)
for i, v in ((0, 84), (2, 56), (4, 68), (6, 54),
             (8, 86), (10, 56), (12, 70), (14, 58)):
    h16(48, i, RIDE, v)
h16(48, 15, SNARE, 32)

# bar 49 - relaxed tom melody
h16(49, 0, KICK, 104)
h16(49, 4, SNARE, 96)
h16(49, 8, KICK, 94)
h16(49, 12, SNARE, 102)
toms49 = [TOMHM, TOMLM, TOMHM, TOML, TOMHM, TOMLM, TOMHM, TOMLM]
vs49   = [72, 54, 68, 50, 74, 54, 70, 56]
for k in range(8):
    h16(49, k * 2, toms49[k], vs49[k])

# bar 50 - rebuild begins
h16(50, 0, KICK, 108)
h16(50, 4, SNARE, 104)
h16(50, 8, KICK, 100)
h16(50, 12, SNARE, 108)
h16(50, 14, SNARE, 40)
hat8(50, [80, 56, 74, 54, 82, 58, 76, 60])

# bar 51 - lead back in
LEAN = 4.0
h16(51, 0, KICK, 110)
h16(51, 4, SNARE, 112)
h16(51, 8, KICK, 104)
h16(51, 12, SNARE, 114)
seq51 = [(SNARE, 70), (SNARE, 80), (TOMHM, 88), (TOMLM, 76),
         (TOML, 90), (FTH, 80), (FTL, 96), (SNARE, 104)]
for k, (n, v) in enumerate(seq51):
    h16(51, 8 + k, n, v)

# ======================================================================
#  SECTION 12 - DEVELOPMENT: MOTIF B RETURNS  (bars 52-59)
# ======================================================================
LEAN, SWING = -6.0, 0.01
h16(52, 0, CRASH, 112)
bar_B(52)
bar_B1(53)
bar_B2(54)
bar_B(55)
bar_B1(56)
bar_B_toms(57)
big_fill(58)
big_fill2(59)

# ======================================================================
#  SECTION 13 - FINAL BUILD  (bars 60-65)
# ======================================================================
LEAN, SWING = -6.0, 0.0
h16(60, 0, CRASH, 120)
h16(60, 0, KICK, 120)
h16(60, 4, SNARE, 122)
h16(60, 12, SNARE, 124)
h16(60, 6, KICK, 102)
h16(60, 10, KICK, 108)
h16(60, 14, KICK, 96)
h16(60, 7, SNARE, 38)
h16(60, 11, SNARE, 36)
hv60 = [100, 60, 66, 58, None, 62, 68, None,
        102, 60, 66, 58, None, 62, 70, None]
for i, v in enumerate(hv60):
    if v:
        h16(60, i, HAT, v)

LEAN = -8.0
h16(61, 0, KICK, 120)
seq61 = [SNARE, SNARE, TOMH, TOMHM, SNARE, SNARE, TOMLM, TOML,
         SNARE, SNARE, TOMH, TOMHM, SNARE, SNARE, TOMLM, FTL]
for i, n in enumerate(seq61):
    v = 122 if i % 4 == 0 else 92
    h16(61, i, n, v)

LEAN = -10.0
h16(62, 0, KICK, 120)
seq62 = [TOMH, TOMHM, TOMLM, TOML, FTH, FTL, FTH, TOML,
         TOMLM, TOMHM, TOMH, TOMHM, TOMLM, TOML, FTL, SNARE]
for i, n in enumerate(seq62):
    v = 118 if i % 4 == 0 else 90
    h16(62, i, n, v)

LEAN = -12.0
h16(63, 0, KICK, 122)
h16(63, 0, CRASH2, 104)
h16(63, 4, SNARE, 124)
swell(63, 5, 11, SNARE, 62, 118, rate=2)

LEAN = -14.0
h16(64, 0, KICK, 122)
dbl64 = [SNARE, SNARE, TOMH, TOMH, TOMHM, TOMHM, TOMLM, TOMLM,
         TOML, TOML, FTH, FTH, FTL, FTL, SNARE, SNARE]
for i, n in enumerate(dbl64):
    v = 118 if i % 2 == 0 else 88
    h16(64, i, n, v)

LEAN = -16.0
h16(65, 0, KICK, 124)
seq65 = [SNARE, TOMH, TOMHM, TOMLM, TOML, FTH, FTL, SNARE,
         TOMH, TOMHM, TOMLM, TOML, FTH, FTL, SNARE, SNARE]
for i, n in enumerate(seq65):
    v = 80 + i * 3
    if i % 4 == 0:
        v += 20
    h16(65, i, n, min(126, v))

# ======================================================================
#  SECTION 14 - CLIMAX  (bars 66-68)
# ======================================================================
LEAN, SWING = -14.0, 0.0
h16(66, 0, CRASH, 124)
h16(66, 0, KICK, 124)
seq66 = [SNARE, SNARE, TOMH, TOMHM, SNARE, TOMLM, TOML, TOML,
         SNARE, SNARE, TOMH, TOMHM, SNARE, TOMLM, FTL, FTL]
for i, n in enumerate(seq66):
    v = 124 if i % 4 == 0 else 96
    h16(66, i, n, v)

LEAN = -16.0
h16(67, 0, KICK, 124)
seq67 = [TOMH, TOMHM, TOMLM, TOML, FTH, FTL, TOML, TOMLM,
         TOMHM, TOMH, TOMHM, TOMLM, TOML, FTH, FTL, SNARE]
for i, n in enumerate(seq67):
    v = 122 if i % 4 == 0 else 94
    h16(67, i, n, v)

LEAN = -12.0
h16(68, 0, KICK, 120)
h16(68, 0, CRASH2, 110)
swell(68, 0, 12, SNARE, 124, 60, rate=2)
h16(68, 12, TOML, 100)
h16(68, 13, TOMLM, 96)
h16(68, 14, TOMHM, 104)
h16(68, 15, SNARE, 60)

# ======================================================================
#  SECTION 15 - THE LANDING  (bar 69)
# ======================================================================
LEAN, SWING = 0.0, 0.0
h16(69, 0, CRASH, 127)
h16(69, 0, KICK, 124)
h16(69, 0, SNARE, 120)

# ----------------------------------------------------------------------
#  playability pass: at most two hands and two feet at any instant
# ----------------------------------------------------------------------
by_tick = defaultdict(list)
for t, n, v in events:
    by_tick[t].append((n, v))

clean = []
for t in sorted(by_tick):
    notes = sorted(by_tick[t], key=lambda x: -x[1])
    hands = [x for x in notes if x[0] not in FEET][:2]
    feet = [x for x in notes if x[0] in FEET][:2]
    for n, v in hands + feet:
        clean.append((t, n, v))
events = clean

# ----------------------------------------------------------------------
#  build the MIDI file
# ----------------------------------------------------------------------
FINAL_TICK = int(round(69 * 4 * TPB))
DUR = 30

msgs = []
for t, n, v in events:
    d = 1500 if t >= FINAL_TICK else DUR
    msgs.append((t, 0, n, v))
    msgs.append((t + d, 1, n, 0))
msgs.sort(key=lambda m: (m[0], m[1]))

mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
track = mido.MidiTrack()
mid.tracks.append(track)

track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
track.append(mido.MetaMessage('time_signature',
                              numerator=4, denominator=4, time=0))
track.append(mido.MetaMessage('set_tempo',
                              tempo=mido.bpm2tempo(BPM), time=0))

last = 0
for t, kind, n, v in msgs:
    dt = t - last
    last = t
    if kind == 0:
        track.append(mido.Message('note_on', note=n, velocity=v,
                                  channel=CH, time=dt))
    else:
        track.append(mido.Message('note_off', note=n, velocity=0,
                                  channel=CH, time=dt))

track.append(mido.MetaMessage('end_of_track', time=TPB))

mid.save('solo.mid')
print('wrote solo.mid  (%d notes, %.1f s)'
      % (len(events), mid.length))
