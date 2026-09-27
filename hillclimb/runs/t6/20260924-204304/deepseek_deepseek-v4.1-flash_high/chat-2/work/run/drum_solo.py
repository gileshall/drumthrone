#!/usr/bin/env python3
"""
drum_solo.py

Generates a two-minute General MIDI drum solo (channel 10) and writes it to
solo.mid in the current working directory.

The performance is deterministic: the same file is produced on every run.
Only mido is used for the MIDI file handling.
"""

import math
import random

from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

# ---------------------------------------------------------------------------
# Global parameters
# ---------------------------------------------------------------------------
random.seed(19740801)

PPQ = 480                     # ticks per quarter note
BPM = 120.0                   # tempo (constant; feel comes from micro-timing)
N_BARS = 60                   # 60 bars of 4/4 at 120 bpm  ->  120 seconds
CHANNEL = 9                   # MIDI channel 10 (zero based)
SPB = 60.0 / BPM              # seconds per beat

# ---------------------------------------------------------------------------
# General MIDI percussion key map
# ---------------------------------------------------------------------------
KICK    = 36
KICK2   = 35
SNARE   = 38
STICK   = 37
HAT     = 42
PEDHAT  = 44
OHAT    = 46
RIDE    = 51
RIDE2   = 59
BELL    = 53
CRASH   = 49
CRASH2  = 57
SPLASH  = 55
CHINA   = 52
TOM_H   = 50        # high tom
TOM_HM  = 48        # hi-mid tom
TOM_M   = 47        # low-mid tom
TOM_LM  = 45        # low tom
TOM_HF  = 43        # high floor tom
TOM_LF  = 41        # low floor tom
TAMB    = 54
COWBELL = 56
CONGA_M = 62
CONGA_O = 63
CONGA_L = 64
WOOD_H  = 76
WOOD_L  = 77
TRI_O   = 81

HANDS = frozenset([SNARE, STICK, HAT, OHAT, RIDE, RIDE2, BELL, CRASH, CRASH2,
                   SPLASH, CHINA, TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_HF, TOM_LF,
                   TAMB, COWBELL, CONGA_M, CONGA_O, CONGA_L, WOOD_H, WOOD_L,
                   TRI_O])
FEET = frozenset([KICK, KICK2, PEDHAT])

# ---------------------------------------------------------------------------
# Note collection
# ---------------------------------------------------------------------------
NOTES = []          # entries: [absolute_beat, note, velocity, duration_beats]


def A(bar, x, note, vel, dur=0.20):
    """Place a note at `x` beats into bar number `bar` (1 based)."""
    NOTES.append([(bar - 1) * 4.0 + x, note, int(round(vel)), dur])


# ===========================================================================
#  THE SOLO
# ===========================================================================

# ---------------------------------------------------------------------------
# 1) Intro - a sparse call, the kit waking up.  (bars 1-4)
# ---------------------------------------------------------------------------
A(1, 0.0, KICK, 92); A(1, 0.0, BELL, 76)
A(1, 1.0, RIDE, 54)
A(1, 2.0, RIDE, 66); A(1, 2.5, SNARE, 40)
A(1, 3.0, RIDE, 58)
A(1, 3.5, KICK, 80)

A(2, 0.0, KICK, 90); A(2, 0.0, BELL, 74)
A(2, 0.5, HAT, 48)
A(2, 1.0, RIDE, 56); A(2, 1.75, SNARE, 34)
A(2, 2.0, RIDE, 66); A(2, 2.0, KICK, 84)
A(2, 2.5, SNARE, 38)
A(2, 3.0, RIDE, 60)
A(2, 3.5, KICK, 80); A(2, 3.5, HAT, 52)
A(2, 3.75, SNARE, 32)

# bar 3 - eighth-note hats arrive, backbeat settles in
for i in range(8):
    A(3, i * 0.5, HAT, 78 if i % 2 == 0 else 56)
A(3, 0.0, KICK, 98)
A(3, 0.75, SNARE, 38)
A(3, 1.0, SNARE, 96)
A(3, 1.5, KICK, 82)
A(3, 2.0, SNARE, 42)
A(3, 2.5, KICK, 88)
A(3, 3.0, SNARE, 102)
A(3, 3.75, SNARE, 34)

# bar 4 - same again with a pickup into the theme
for i in range(8):
    A(4, i * 0.5, HAT, 80 if i % 2 == 0 else 58)
A(4, 0.0, KICK, 100)
A(4, 0.75, SNARE, 36)
A(4, 1.0, SNARE, 98)
A(4, 1.5, KICK, 84)
A(4, 2.25, SNARE, 38)
A(4, 2.5, KICK, 90)
A(4, 3.0, SNARE, 104)
A(4, 3.25, SNARE, 54)
A(4, 3.5, SNARE, 62)
A(4, 3.75, SNARE, 74)


# ---------------------------------------------------------------------------
# 2) The theme - "Motif A", a funk groove carried by the hi-hat.  (bars 5-12)
# ---------------------------------------------------------------------------
def theme(bar, cym=HAT, son=80, soff=56, kicks=(0.0, 1.5, 2.5),
          kv=(100, 88, 90), ghosts=(0.75, 2.25), gv=(40, 36),
          sv=(106, 110)):
    """One bar of the main motif."""
    for i in range(8):
        A(bar, i * 0.5, cym, son if i % 2 == 0 else soff)
    for x, v in zip(kicks, kv):
        A(bar, x, KICK, v)
    A(bar, 1.0, SNARE, sv[0])
    A(bar, 3.0, SNARE, sv[1])
    for k, x in enumerate(ghosts):
        A(bar, x, SNARE, gv[k % len(gv)])


theme(5)
A(5, 0.0, CRASH, 106)

theme(6, ghosts=(0.75, 1.75, 2.25, 3.25), gv=(42, 34, 38, 36))

theme(7, kicks=(0.0, 2.5, 3.5), kv=(102, 92, 84), ghosts=(1.75, 2.25))

theme(8, ghosts=(0.75,))
A(8, 3.25, TOM_H, 76)
A(8, 3.5, TOM_HM, 82)
A(8, 3.75, TOM_M, 88)

theme(9, cym=RIDE, son=86, soff=62)
A(9, 0.0, CRASH2, 100)

theme(10, cym=RIDE, son=84, soff=60, kicks=(0.0, 0.75, 1.5, 2.5),
      kv=(100, 78, 86, 90), ghosts=(1.75, 2.25, 3.25))

theme(11, cym=RIDE, son=86, soff=62, ghosts=(0.75, 2.25))

# bar 12 - the theme tumbles into a fill
A(12, 0.0, KICK, 102); A(12, 0.0, RIDE, 80); A(12, 0.0, SNARE, 100)
A(12, 0.5, SNARE, 52)
A(12, 1.0, SNARE, 105); A(12, 1.0, KICK, 90)
A(12, 1.25, TOM_H, 62); A(12, 1.5, TOM_H, 76); A(12, 1.75, TOM_HM, 80)
A(12, 2.0, TOM_HM, 88); A(12, 2.0, KICK, 86)
A(12, 2.25, TOM_M, 74); A(12, 2.5, TOM_M, 84); A(12, 2.75, TOM_LM, 88)
A(12, 3.0, TOM_LM, 94); A(12, 3.25, TOM_HF, 90)
A(12, 3.5, TOM_LF, 98); A(12, 3.75, TOM_LF, 84)


# ---------------------------------------------------------------------------
# 3) The theme re-voiced on the toms.  (bars 13-16)
# ---------------------------------------------------------------------------
for x, n, v in [(0.0, KICK, 100), (0.0, TOM_H, 96),
                (0.5, TOM_H, 60), (0.75, TOM_HM, 76),
                (1.0, SNARE, 92),
                (1.5, TOM_HM, 84), (1.75, TOM_M, 72),
                (2.0, TOM_M, 94), (2.25, SNARE, 44),
                (2.5, TOM_LM, 86),
                (3.0, SNARE, 106),
                (3.5, TOM_HF, 88), (3.75, TOM_LM, 74)]:
    A(13, x, n, v)

for x, n, v in [(0.0, TOM_LF, 98), (0.0, KICK, 96),
                (0.5, TOM_HF, 66), (0.75, TOM_LM, 74),
                (1.0, SNARE, 94), (1.0, HAT, 58),
                (1.5, TOM_M, 86),
                (2.0, TOM_HM, 92), (2.0, KICK, 88),
                (2.5, TOM_H, 84), (2.75, SNARE, 40),
                (3.0, SNARE, 104),
                (3.25, TOM_H, 70), (3.5, TOM_HM, 78), (3.75, TOM_M, 86)]:
    A(14, x, n, v)

for i in range(8):
    A(15, i * 0.5, HAT, 76 if i % 2 == 0 else 54)
A(15, 0.0, KICK, 100); A(15, 0.0, TOM_H, 88)
A(15, 1.0, SNARE, 100)
A(15, 1.5, KICK, 86)
A(15, 2.0, TOM_M, 92)
A(15, 2.5, KICK, 90)
A(15, 3.0, SNARE, 106)
A(15, 3.5, TOM_LM, 88)

A(16, 0.0, KICK, 104); A(16, 0.0, SNARE, 100); A(16, 0.0, CRASH, 96)
A(16, 1.0, SNARE, 102)
A(16, 1.5, SNARE, 60)
A(16, 2.0, SNARE, 70)
A(16, 2.25, TOM_H, 74); A(16, 2.5, TOM_HM, 80); A(16, 2.75, TOM_M, 84)
A(16, 3.0, TOM_LM, 90); A(16, 3.25, TOM_HF, 94)
A(16, 3.5, TOM_LF, 98); A(16, 3.75, SNARE, 96)


# ---------------------------------------------------------------------------
# 4) Contrast - "Motif B", sixteenths on the bell / ride.  (bars 17-20)
# ---------------------------------------------------------------------------
def ride16(bar, cym=RIDE, a=92, b=66, c=52):
    for i in range(16):
        v = a if i % 4 == 0 else (b if i % 2 == 0 else c)
        A(bar, i * 0.25, cym, v)


ride16(17, cym=BELL, a=96, b=70, c=56)
A(17, 0.0, KICK, 102)
A(17, 1.0, SNARE, 108)
A(17, 1.5, KICK, 88)
A(17, 2.0, KICK, 96)
A(17, 3.0, SNARE, 112)
A(17, 3.5, KICK, 86)

ride16(18, cym=BELL, a=94, b=68, c=54)
A(18, 0.0, KICK, 100)
A(18, 0.75, KICK, 84)
A(18, 1.0, SNARE, 106)
A(18, 2.0, KICK, 94)
A(18, 2.5, SNARE, 60)
A(18, 3.0, SNARE, 110)
A(18, 3.5, KICK, 88)

ride16(19, cym=RIDE, a=90, b=64, c=50)
A(19, 0.0, KICK, 104)
A(19, 1.0, SNARE, 110)
A(19, 1.75, SNARE, 42)
A(19, 2.0, KICK, 98)
A(19, 2.75, SNARE, 40)
A(19, 3.0, SNARE, 112)
A(19, 3.25, SNARE, 46)
A(19, 3.75, KICK, 88)

A(20, 0.0, KICK, 104); A(20, 0.0, CRASH, 104); A(20, 0.0, SNARE, 96)
A(20, 0.5, SNARE, 60)
A(20, 1.0, SNARE, 104)
A(20, 1.25, TOM_H, 66); A(20, 1.5, TOM_H, 78); A(20, 1.75, TOM_HM, 74)
A(20, 2.0, TOM_HM, 88); A(20, 2.25, TOM_M, 76); A(20, 2.5, TOM_M, 90)
A(20, 2.75, TOM_LM, 82); A(20, 3.0, TOM_LM, 94); A(20, 3.25, TOM_HF, 86)
A(20, 3.5, TOM_LF, 100); A(20, 3.75, KICK, 92)


# ---------------------------------------------------------------------------
# 5) Release - lots of air, side stick, quiet feet.  (bars 21-24)
# ---------------------------------------------------------------------------
A(21, 0.0, KICK, 74); A(21, 0.0, STICK, 62)
A(21, 1.5, STICK, 50)
A(21, 2.0, KICK, 66)
A(21, 2.75, WOOD_H, 34)
A(21, 3.0, STICK, 66)
A(21, 3.5, HAT, 46)

A(22, 0.0, KICK, 72); A(22, 0.0, STICK, 60)
A(22, 1.0, STICK, 54)
A(22, 1.75, STICK, 40)
A(22, 2.0, KICK, 70); A(22, 2.0, STICK, 64)
A(22, 3.0, STICK, 68)
A(22, 3.5, KICK, 72)
A(22, 3.75, WOOD_L, 32)

A(23, 0.0, KICK, 76); A(23, 0.0, HAT, 58)
A(23, 0.5, HAT, 44)
A(23, 0.75, TAMB, 38)
A(23, 1.0, STICK, 62)
A(23, 1.5, HAT, 46)
A(23, 2.0, KICK, 78); A(23, 2.0, HAT, 58)
A(23, 2.5, HAT, 44)
A(23, 3.0, STICK, 66)
A(23, 3.5, HAT, 48); A(23, 3.75, STICK, 42)

A(24, 0.0, KICK, 78)
A(24, 0.5, HAT, 46)
A(24, 1.0, STICK, 60)
A(24, 1.5, SNARE, 44)
A(24, 2.0, KICK, 80)
A(24, 2.5, SNARE, 50)
A(24, 3.0, SNARE, 62)
A(24, 3.25, SNARE, 54)
A(24, 3.5, SNARE, 68)
A(24, 3.75, SNARE, 76)


# ---------------------------------------------------------------------------
# 6) First build - density and volume inside the phrases.  (bars 25-32)
# ---------------------------------------------------------------------------
for k, x in enumerate([0.0, 0.75, 1.5, 2.0, 2.75, 3.5]):
    A(25, x, SNARE, 52 + k * 3)
A(25, 0.0, KICK, 84)
A(25, 2.0, KICK, 78)

for k, x in enumerate([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]):
    A(26, x, SNARE, 56 + k * 3)
A(26, 0.0, KICK, 86)
A(26, 1.5, KICK, 78)
A(26, 2.5, KICK, 84)

for i in range(16):
    A(27, i * 0.25, SNARE, 62 + i * 2)
A(27, 0.0, KICK, 88)
A(27, 2.0, KICK, 84)

for i in range(16):
    x = i * 0.25
    A(28, x, SNARE if x < 2.0 else TOM_LM, 66 + i * 2)
A(28, 0.0, KICK, 90)
A(28, 2.0, KICK, 86)

tom_line = [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_M, TOM_M, TOM_LM, TOM_LM,
            TOM_HF, TOM_HF, TOM_LF, TOM_LF, TOM_HF, TOM_LM, TOM_HM, TOM_H]
for i, n in enumerate(tom_line):
    A(29, i * 0.25, n, 72 + i * 2)
A(29, 0.0, KICK, 92)
A(29, 2.0, KICK, 88)

for i in range(16):
    A(30, i * 0.25, SNARE if i % 4 < 2 else TOM_M, 78 + i * 2)
A(30, 0.0, KICK, 96); A(30, 1.5, KICK, 90); A(30, 3.0, KICK, 92)

for i in range(12):
    A(31, i / 3.0, SNARE if i < 6 else TOM_M, 82 + i * 2)
A(31, 0.0, KICK, 98); A(31, 2.0, KICK, 94)

for i in range(12):
    A(32, i * 0.25, SNARE if i % 4 < 2 else TOM_M, 92 + i)
A(32, 0.0, KICK, 102); A(32, 2.0, KICK, 98)
for i in range(8):
    A(32, 3.0 + i * 0.125, TOM_HF if i < 4 else TOM_LF, 96 + i)


# ---------------------------------------------------------------------------
# 7) Theme returns, big and proud.  (bars 33-36)
# ---------------------------------------------------------------------------
theme(33, son=88, soff=62, kv=(108, 94, 96), sv=(112, 116))
A(33, 0.0, CRASH, 112)

theme(34, son=86, soff=60, kicks=(0.0, 0.75, 2.5), kv=(106, 84, 94),
      ghosts=(1.75, 2.25, 3.25))

theme(35, cym=RIDE, son=90, soff=64, ghosts=(0.75, 2.25))

A(36, 0.0, KICK, 108); A(36, 0.0, SNARE, 104); A(36, 0.0, CRASH2, 104)
A(36, 0.5, SNARE, 58)
A(36, 1.0, SNARE, 106)
A(36, 1.5, SNARE, 64)
A(36, 1.75, SNARE, 72)
A(36, 2.0, TOM_H, 90); A(36, 2.25, TOM_HM, 86); A(36, 2.5, TOM_M, 92)
A(36, 2.75, TOM_LM, 88); A(36, 3.0, TOM_HF, 96); A(36, 3.25, TOM_LF, 92)
A(36, 3.5, KICK, 100); A(36, 3.5, SNARE, 100)
A(36, 3.75, SNARE, 80)


# ---------------------------------------------------------------------------
# 8) Development - displacement and call-and-answer with the feet. (37-44)
# ---------------------------------------------------------------------------
for i in range(8):
    A(37, i * 0.5, HAT, 78 if i % 2 == 0 else 56)
A(37, 0.0, KICK, 104)
A(37, 0.75, SNARE, 44)
A(37, 1.0, SNARE, 108)
A(37, 1.75, SNARE, 40)
A(37, 2.0, KICK, 96)
A(37, 2.25, SNARE, 42)
A(37, 2.75, KICK, 88)
A(37, 3.0, SNARE, 110)
A(37, 3.5, SNARE, 46)
A(37, 3.75, KICK, 92)

for i in range(8):
    A(38, i * 0.5, HAT, 76 if i % 2 == 0 else 54)
A(38, 0.25, KICK, 100)
A(38, 0.75, SNARE, 46)
A(38, 1.0, SNARE, 106)
A(38, 1.5, KICK, 92)
A(38, 2.0, KICK, 98)
A(38, 2.25, SNARE, 40)
A(38, 3.0, SNARE, 108)
A(38, 3.25, SNARE, 44)
A(38, 3.5, KICK, 94)

A(39, 0.0, KICK, 104); A(39, 0.0, TOM_H, 96)
A(39, 0.75, TOM_HM, 72)
A(39, 1.0, TOM_HM, 92)
A(39, 1.5, KICK, 90)
A(39, 2.0, TOM_M, 96)
A(39, 2.25, TOM_M, 70)
A(39, 2.5, TOM_LM, 88)
A(39, 3.0, SNARE, 110)
A(39, 3.5, SNARE, 60)
A(39, 3.75, SNARE, 72)

A(40, 0.0, KICK, 106); A(40, 0.0, TOM_LF, 100)
A(40, 0.5, TOM_HF, 74); A(40, 0.75, TOM_LM, 80)
A(40, 1.0, TOM_M, 92); A(40, 1.25, TOM_M, 74)
A(40, 1.5, TOM_HM, 84); A(40, 1.75, TOM_HM, 70)
A(40, 2.0, TOM_H, 96); A(40, 2.25, TOM_H, 72)
A(40, 2.5, TOM_HM, 88); A(40, 2.75, TOM_M, 84)
A(40, 3.0, TOM_LM, 96); A(40, 3.25, TOM_HF, 92)
A(40, 3.5, TOM_LF, 104); A(40, 3.75, SNARE, 90)

theme(41, son=90, soff=64, kv=(110, 96, 98), sv=(112, 116))
A(41, 0.0, CRASH, 110)

theme(42, son=88, soff=62, kicks=(0.0, 0.75, 2.5), kv=(108, 86, 96),
      ghosts=(1.75, 2.25))

theme(43, cym=RIDE, son=92, soff=66, ghosts=(0.75, 2.25))

A(44, 0.0, KICK, 108); A(44, 0.0, SNARE, 106)
A(44, 0.5, SNARE, 60)
A(44, 1.0, SNARE, 108)
A(44, 1.5, SNARE, 64)
A(44, 2.0, TOM_H, 92); A(44, 2.5, TOM_HM, 88)
A(44, 3.0, TOM_M, 94); A(44, 3.5, TOM_LM, 90)


# ---------------------------------------------------------------------------
# 9) Breakdown - back to almost nothing.  (bars 45-48)
# ---------------------------------------------------------------------------
A(45, 0.0, KICK, 70)
A(45, 0.75, SNARE, 36)
A(45, 1.0, SNARE, 72)
A(45, 1.5, COWBELL, 40)
A(45, 1.75, SNARE, 34)
A(45, 2.0, KICK, 64)
A(45, 2.5, SNARE, 38)
A(45, 3.0, SNARE, 74)
A(45, 3.5, SNARE, 40)

A(46, 0.0, PEDHAT, 52)
A(46, 1.0, SNARE, 64)
A(46, 1.5, SNARE, 36)
A(46, 2.0, KICK, 68)
A(46, 2.5, COWBELL, 36)
A(46, 2.75, SNARE, 34)
A(46, 3.0, SNARE, 70)
A(46, 3.75, SNARE, 38)

A(47, 0.0, SNARE, 68)
A(47, 0.5, HAT, 44)
A(47, 1.0, SNARE, 40)
A(47, 1.5, HAT, 42)
A(47, 2.0, SNARE, 72)
A(47, 2.75, SNARE, 36)
A(47, 3.0, KICK, 76)
A(47, 3.5, HAT, 46)
A(47, 3.75, WOOD_H, 40)

A(48, 0.0, KICK, 80); A(48, 0.0, HAT, 50)
A(48, 0.75, SNARE, 42)
A(48, 1.0, SNARE, 78)
A(48, 1.5, HAT, 48)
A(48, 1.75, TAMB, 44)
A(48, 2.0, SNARE, 84)
A(48, 2.5, SNARE, 46)
A(48, 2.75, HAT, 50)
A(48, 3.0, KICK, 84)
A(48, 3.25, SNARE, 52)
A(48, 3.5, SNARE, 64)
A(48, 3.75, SNARE, 76)


# ---------------------------------------------------------------------------
# 10) Big build - singles travelling around the kit.  (bars 49-56)
# ---------------------------------------------------------------------------
for i in range(16):
    A(49, i * 0.25, SNARE, 54 + (i % 4) * 6)
A(49, 0.0, KICK, 88); A(49, 2.0, KICK, 84)

for i in range(16):
    A(50, i * 0.25, SNARE if i % 4 < 3 else TOM_H, 58 + (i % 4) * 7)
A(50, 0.0, KICK, 92); A(50, 1.5, KICK, 86); A(50, 2.5, KICK, 88)

for i in range(16):
    A(51, i * 0.25, [SNARE, SNARE, TOM_HM, TOM_HM][i % 4], 64 + (i % 4) * 8)
A(51, 0.0, KICK, 96); A(51, 2.0, KICK, 92)

for i in range(16):
    A(52, i * 0.25, [TOM_H, TOM_HM, TOM_M, TOM_LM][i % 4], 70 + (i % 4) * 8)
A(52, 0.0, KICK, 98); A(52, 1.0, KICK, 90)
A(52, 2.0, KICK, 94); A(52, 3.0, KICK, 96)

for i in range(16):
    A(53, i * 0.25, [TOM_HF, TOM_HF, TOM_LF, TOM_LF][i % 4], 76 + (i % 4) * 8)
A(53, 0.0, KICK, 102); A(53, 0.0, CRASH, 100)
A(53, 2.0, KICK, 96)

for i in range(16):
    A(54, i * 0.25, [SNARE, TOM_H, TOM_HM, TOM_M][i % 4], 80 + (i % 4) * 8)
A(54, 0.0, KICK, 106); A(54, 1.5, KICK, 98); A(54, 2.5, KICK, 100)

tri_line = [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_HF, TOM_LF]
for i in range(12):
    A(55, i / 3.0, tri_line[i % 6], 86 + (i % 3) * 5)
A(55, 0.0, KICK, 108); A(55, 2.0, KICK, 104)

for i in range(16):
    A(56, i * 0.25, SNARE if i % 4 < 2 else TOM_M, 88 + (i % 4) * 4)
A(56, 0.0, KICK, 110); A(56, 2.0, KICK, 106)


# ---------------------------------------------------------------------------
# 11) Climax and the final hit.  (bars 57-60)
# ---------------------------------------------------------------------------
theme(57, son=94, soff=68, kv=(114, 100, 102), sv=(116, 118))
A(57, 0.0, CRASH, 116)

theme(58, son=92, soff=66, kicks=(0.0, 1.5, 2.5, 3.5),
      kv=(112, 98, 100, 96), ghosts=(0.75, 2.25, 3.25), sv=(114, 118))

# bar 59 - the last fill: sixteenths that break into thirty-seconds
for i in range(8):
    A(59, i * 0.25, [TOM_H, TOM_HM, TOM_M, TOM_LM][i % 4], 84 + (i % 4) * 6)
for i in range(16):
    x = 2.0 + i * 0.125
    if i < 6:
        n = TOM_HF if i % 2 == 0 else TOM_LM
    else:
        n = SNARE if i % 2 == 0 else TOM_LF
    A(59, x, n, 100 + i)

# bar 60 - one last hit, and let it ring
A(60, 0.0, KICK, 120)
A(60, 0.0, SNARE, 118)
A(60, 0.0, CRASH, 122)


# ===========================================================================
#  RENDERING
# ===========================================================================

def enforce_limbs(notes):
    """Never more than two hands and two feet striking at the same instant."""
    notes = sorted(notes, key=lambda n: (n[0], n[1], n[2]))
    out = []
    i = 0
    n = len(notes)
    while i < n:
        j = i
        cluster = [notes[i]]
        while j + 1 < n and notes[j + 1][0] - cluster[0][0] < 0.045:
            j += 1
            cluster.append(notes[j])
        hands = [x for x in cluster if x[1] in HANDS]
        feet = [x for x in cluster if x[1] in FEET]
        other = [x for x in cluster if x[1] not in HANDS and x[1] not in FEET]
        if len(hands) > 2:
            hands.sort(key=lambda x: -x[2])
            hands = hands[:2]
        if len(feet) > 2:
            feet.sort(key=lambda x: -x[2])
            feet = feet[:2]
        out.extend(other + hands + feet)
        i = j + 1
    return out


DEF_DUR = {
    CRASH: 4.0, CRASH2: 4.0, CHINA: 3.0, SPLASH: 2.0,
    RIDE: 1.0, RIDE2: 1.0, BELL: 0.9, OHAT: 0.8,
    PEDHAT: 0.5, HAT: 0.14, STICK: 0.14,
}


def render(notes, path='solo.mid'):
    # --- expressive timing -------------------------------------------------
    def phrase_offset(beat):
        # slow "hands" drift: the pulse surges and settles
        return (0.013 * math.sin(beat * 0.37 + 1.1) +
                0.009 * math.sin(beat * 0.127 + 2.7) +
                0.006 * math.sin(beat * 0.61 + 0.4))

    base = phrase_offset(0.0)

    notes = sorted(notes, key=lambda x: (x[0], x[1], x[2]))

    onsets = []
    for beat, note, vel, dur in notes:
        off = phrase_offset(beat) - base + random.gauss(0.0, 0.004)
        pos = beat + off / SPB
        onsets.append(int(round(pos * PPQ)))

    # --- lengths, clamped so the same drum never overlaps itself ----------
    by_pitch = {}
    for i, (_b, note, _v, _d) in enumerate(notes):
        by_pitch.setdefault(note, []).append(i)

    durs = [0] * len(notes)
    for note, idxs in by_pitch.items():
        natural = int(round(DEF_DUR.get(note, 0.20) * PPQ))
        for k, i in enumerate(idxs):
            if k + 1 < len(idxs):
                gap = onsets[idxs[k + 1]] - onsets[i]
                d = min(natural, gap - 2)
                if d < 12:
                    d = min(12, max(1, gap - 1))
            else:
                d = natural
            durs[i] = max(1, d)

    # --- build the event list ---------------------------------------------
    events = []
    for i, (_b, note, vel, _d) in enumerate(notes):
        vel = max(1, min(127, vel))
        on = onsets[i]
        events.append((on, 1, note, vel))            # note on
        events.append((on + durs[i], 0, note, 0))    # note off (first at tie)
    events.sort(key=lambda e: (e[0], e[1]))

    # --- write the file ----------------------------------------------------
    mid = MidiFile(ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('set_tempo', tempo=bpm2tempo(BPM), time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             time=0))
    track.append(MetaMessage('text',
                             text='Two-minute drum solo, GM channel 10',
                             time=0))
    track.append(Message('program_change', channel=CHANNEL, program=0, time=0))

    last = 0
    for tick, kind, note, vel in events:
        delta = tick - last
        if delta < 0:
            delta = 0
        last = tick
        if kind:
            track.append(Message('note_on', channel=CHANNEL, note=note,
                                 velocity=vel, time=delta))
        else:
            track.append(Message('note_off', channel=CHANNEL, note=note,
                                 velocity=0, time=delta))

    track.append(MetaMessage('end_of_track', time=PPQ))
    mid.save(path)
    return mid


def main():
    notes = enforce_limbs(NOTES)
    mid = render(notes, 'solo.mid')
    total = sum(msg.time for msg in mid.tracks[0])
    print('solo.mid written: %d notes, %d ticks (%.1f s at %g bpm)'
          % (len(notes), total, total / PPQ * 60.0 / BPM, BPM))


if __name__ == '__main__':
    main()
