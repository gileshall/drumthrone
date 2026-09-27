#!/usr/bin/env python3
"""
drum_solo.py

Writes ``solo.mid``: a two minute General MIDI drum solo on channel 10.

The solo is built from a couple of motifs that are stated, varied, developed
and recalled.  Dynamics are shaped inside the phrases (accents, ghost notes,
crescendos) rather than by pushing whole sections up and down; the time is
humanised with micro jitter plus a phrase level push/pull; the tempo map
surges and settles so the pulse breathes.  Every onset is checked so that no
more than two hands and two feet strike at the same instant, and the whole
piece is exactly two minutes long.  The output is deterministic.
"""

import math
import random

from mido import MidiFile, MidiTrack, Message, MetaMessage

# --------------------------------------------------------------------------
#  setup
# --------------------------------------------------------------------------
PPQ = 960                       # ticks per quarter note
CHANNEL = 9                     # 0 based -> MIDI channel 10 (percussion)
TOTAL_BARS = 64                 # 64 bars of 4/4
TARGET_SECONDS = 120.0
RNG = random.Random(20240517)

# --- General MIDI percussion (notes 35..81) -------------------------------
BD, BD2 = 36, 35                # bass drum / acoustic bass drum
SD, SD2 = 38, 40                # snare / electric snare
RIM = 37                        # side stick
HH, PHH, OHH = 42, 44, 46       # closed hat, pedal hat, open hat
RIDE, BELL, RIDE2 = 51, 53, 59
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
TOM = [50, 48, 47, 45, 43, 41]  # high tom -> low floor tom
COW, TAMB, WBLK, CLAVE = 56, 54, 76, 75
TRI_OPEN = 81

FEET = frozenset((BD, BD2, PHH))

# how long each drum is allowed to ring (beats) before note-off
DURATION = {
    CRASH: 2.0, CRASH2: 2.0, CHINA: 2.0, SPLASH: 1.0,
    RIDE: 0.6, RIDE2: 0.6, BELL: 0.6,
    HH: 0.08, PHH: 0.08, OHH: 0.6,
    SD: 0.15, SD2: 0.15, RIM: 0.1, BD: 0.2, BD2: 0.2,
    COW: 0.2, TAMB: 0.25, WBLK: 0.15, CLAVE: 0.15, TRI_OPEN: 1.0,
}

events = []                     # (beat, note, velocity)


def hit(beat, note, vel):
    """One stroke at ``beat`` with the given velocity."""
    events.append((float(beat), int(note),
                   int(max(1, min(127, round(vel))))))


def accent(beat, note, base=108):
    hit(beat, note, base + RNG.uniform(-6.0, 6.0))


def normal(beat, note, base=88):
    hit(beat, note, base + RNG.uniform(-6.0, 6.0))


def ghost(beat, note, base=32):
    """Ghost note: much softer, and a hair behind the beat."""
    hit(beat + 0.015, note, base + RNG.uniform(-7.0, 9.0))


# --------------------------------------------------------------------------
#  bars 0-3 : intro -- the pulse appears, then a roll into the first downbeat
# --------------------------------------------------------------------------
def build_intro():
    # bar 0 -- sparse, one bell, one kick, a whisper on the snare
    hit(0.0, BELL, 64)
    hit(2.0, BELL, 58)
    hit(1.0, PHH, 46)
    hit(3.0, PHH, 46)
    hit(0.0, BD, 64)
    ghost(3.5, SD, 28)

    # bar 1 -- motif A, whispered, over a ride pulse
    for i in range(8):
        hit(4 + 0.5 * i, RIDE, (60 if i % 2 == 0 else 45) + RNG.uniform(-3, 3))
    for rep in (0.0, 2.0):
        b = 4 + rep
        accent(b + 0.0, BD, 78)
        ghost(b + 0.75, SD, 32)
        accent(b + 1.0, SD, 82)
        normal(b + 1.5, BD, 62)
        ghost(b + 1.75, SD, 26)

    # bars 2-3 -- a long crescendo roll that carries into the first downbeat
    for i in range(16):
        hit(8 + 0.25 * i, SD, 44 + 30 * (i / 15.0) + RNG.uniform(-3, 3))
    seq = [SD, SD, TOM[0], TOM[1], TOM[2], TOM[3], TOM[4], TOM[5],
           TOM[3], TOM[4], TOM[5], TOM[5], TOM[4], TOM[5], TOM[5], TOM[5]]
    for i in range(16):
        hit(12 + 0.25 * i, seq[i], 76 + 36 * (i / 15.0) + RNG.uniform(-3, 3))


# --------------------------------------------------------------------------
#  bars 4-11 : motif A stated over a groove, then developed
# --------------------------------------------------------------------------
def build_a():
    kicks = [
        [0.0, 1.5, 2.5],
        [0.0, 2.0, 3.5],
        [0.0, 0.75, 2.0, 2.5],
        [0.0, 1.5, 3.0],
        [0.0, 2.5, 3.5],
        [0.0, 1.75, 2.5],
        [0.0, 0.5, 2.0, 3.5],
        [0.0, 1.5, 2.75],
    ]
    for idx, bar in enumerate(range(4, 12)):
        base = bar * 4.0
        cym = HH if idx < 4 else RIDE
        for i in range(8):
            hit(base + 0.5 * i, cym,
                (68 if i % 2 == 0 else 50) + RNG.uniform(-4, 4))
        if idx in (0, 4):
            hit(base + 0.0, CRASH, 108)
            hit(base + 0.0, BD, 100)
        for k in kicks[(idx * 3) % len(kicks)]:
            hit(base + k, BD, (96 if k == 0.0 else 80) + RNG.uniform(-5, 5))
        hit(base + 1.0, SD, 102 + RNG.uniform(-5, 5))          # backbeat on 2
        if idx == 7:
            for i in range(8):                                 # closing fill
                hit(base + 2.0 + 0.25 * i, TOM[i % 6], 84 + 6 * i)
        elif idx % 4 == 3:
            for i in range(4):                                 # small fill
                hit(base + 3.0 + 0.25 * i, TOM[i], 88 + 8 * i)
        else:
            hit(base + 3.0, SD, 104 + RNG.uniform(-5, 5))      # backbeat on 4
            ghost(base + 0.75, SD, 30)
            ghost(base + 1.75, SD, 28)
            if idx % 2 == 0:
                ghost(base + 2.25, SD, 36)
            if idx == 2:                                       # motif on the floor tom
                hit(base + 2.0, TOM[3], 88)
                hit(base + 2.5, SD, 40)
                hit(base + 2.75, TOM[4], 80)


# --------------------------------------------------------------------------
#  bars 12-19 : double strokes that travel around the kit
# --------------------------------------------------------------------------
def build_b():
    doubles = [SD, SD, TOM[0], TOM[0], TOM[1], TOM[1], TOM[2], TOM[2],
               TOM[3], TOM[3], TOM[4], TOM[4], TOM[5], TOM[5], TOM[4], TOM[4]]
    for idx, bar in enumerate(range(12, 20)):
        base = bar * 4.0
        v0 = 74.0 + 4.0 * idx
        hit(base + 0.0, BD, 98)
        hit(base + 2.0, BD, 90)
        hit(base + 2.5, BD, 78)
        hit(base + 1.0, PHH, 52)
        hit(base + 3.0, PHH, 52)
        if idx in (0, 4):
            hit(base + 0.0, CRASH, 106)
        off = (idx * 2) % 16
        if idx == 5:
            # a breath: half a bar of doubles, then air
            for i in range(8):
                note = doubles[(off + i) % 16]
                v = v0 + (10.0 if i % 2 == 0 else -6.0) + 5.0 * (i / 7.0)
                hit(base + 0.25 * i, note, v + RNG.uniform(-4, 4))
            hit(base + 3.0, CRASH2, 100)
            hit(base + 3.0, BD, 102)
            hit(base + 3.5, TOM[5], 92)
        else:
            for i in range(16):
                note = doubles[(off + i) % 16]
                v = v0 + (10.0 if i % 2 == 0 else -6.0) + 8.0 * (i / 15.0)
                hit(base + 0.25 * i, note, v + RNG.uniform(-4, 4))
            if idx == 7:
                hit(base + 3.75, CRASH, 110)


# --------------------------------------------------------------------------
#  bars 20-27 : singles, a thirty-second burst, then a drop in density
# --------------------------------------------------------------------------
def build_c():
    for idx, bar in enumerate(range(20, 28)):
        base = bar * 4.0
        if idx < 2:
            # snare singles with the accents grouped in threes (3 against 4)
            for i in range(16):
                v = 106 if i % 3 == 0 else 64 + RNG.uniform(-7, 7)
                hit(base + 0.25 * i, SD, v)
            hit(base + 0.0, BD, 102)
            hit(base + 1.0, BD, 86)
            hit(base + 2.5, BD, 82)
            hit(base + 3.5, BD, 78)
            hit(base + 1.0, PHH, 50)
            hit(base + 3.0, PHH, 50)
        elif idx < 4:
            seq = [SD, SD, TOM[0], SD, TOM[1], SD, TOM[2], SD,
                   TOM[3], SD, TOM[4], SD, TOM[5], TOM[4], TOM[5], TOM[5]]
            for i in range(16):
                v = 104 if i % 4 == 0 else 66 + RNG.uniform(-8, 8)
                hit(base + 0.25 * i, seq[i], v)
            hit(base + 0.0, BD, 102)
            hit(base + 2.0, BD, 94)
            hit(base + 2.5, BD, 84)
            if idx == 3:
                hit(base + 0.0, CRASH2, 106)
        elif idx == 4:
            # thirty-second burst, crash, then space
            for i in range(8):
                hit(base + 0.125 * i, SD, 68 + 5 * i + RNG.uniform(-3, 3))
            hit(base + 1.0, TOM[5], 104)
            hit(base + 1.25, TOM[4], 96)
            hit(base + 1.5, TOM[3], 92)
            hit(base + 1.75, TOM[2], 96)
            hit(base + 2.0, CRASH, 112)
            hit(base + 2.0, BD, 108)
            hit(base + 2.5, PHH, 52)
            hit(base + 3.0, COW, 84)
            hit(base + 3.5, COW, 76)
        elif idx == 5:
            # contrast: half time, ride and rim clicks
            hit(base + 0.0, BD, 96)
            hit(base + 0.0, RIDE, 78)
            hit(base + 1.5, SD, 92)
            hit(base + 2.0, BD, 88)
            hit(base + 2.5, RIDE, 74)
            hit(base + 3.0, SD, 86)
            hit(base + 3.5, PHH, 50)
        elif idx == 6:
            # dying away, setting up the breakdown
            for i in range(16):
                hit(base + 0.25 * i, SD,
                    84 - 26 * (i / 15.0) + RNG.uniform(-4, 4))
            hit(base + 0.0, BD, 92)
            hit(base + 2.0, BD, 82)
        else:
            # last crumbs before the quiet section
            hit(base + 0.0, TOM[2], 70)
            hit(base + 0.75, TOM[3], 62)
            hit(base + 1.5, TOM[4], 58)
            hit(base + 2.0, BD, 76)
            hit(base + 2.5, TOM[5], 54)
            hit(base + 3.0, PHH, 44)


# --------------------------------------------------------------------------
#  bars 28-35 : breakdown -- space, rim clicks, a slow build
# --------------------------------------------------------------------------
def build_d():
    for idx, bar in enumerate(range(28, 36)):
        base = bar * 4.0
        if idx < 6:
            hit(base + 0.0, BD, 78)
            hit(base + 2.5, BD, 66)
            hit(base + 1.0, PHH, 44)
            hit(base + 3.0, PHH, 44)
            hit(base + 1.0, RIM, 74)
            hit(base + 3.0, RIM, 70)
            ghost(base + 0.25, SD, 26)
            ghost(base + 2.75, SD, 30)
            if idx % 2 == 1:                      # the motif, on wood
                hit(base + 1.5, WBLK, 72)
                hit(base + 2.0, WBLK, 66)
                hit(base + 3.5, WBLK, 62)
            if idx in (2, 4):                     # the motif, on toms
                hit(base + 2.0, TOM[3], 72)
                hit(base + 2.75, TOM[4], 66)
            if idx == 5:
                hit(base + 3.5, TAMB, 60)
                hit(base + 3.75, TRI_OPEN, 68)
        elif idx == 6:
            # the build begins
            for i in range(16):
                hit(base + 0.25 * i, SD,
                    42 + 26 * (i / 15.0) + RNG.uniform(-4, 4))
            hit(base + 0.0, BD, 88)
            hit(base + 2.0, BD, 84)
        else:
            seq = [SD, SD, SD, SD, SD, SD, TOM[0], TOM[1],
                   TOM[2], TOM[3], TOM[4], TOM[5], TOM[4], TOM[5], TOM[5], TOM[5]]
            for i in range(16):
                hit(base + 0.25 * i, seq[i], 72 + 40 * (i / 15.0))
            hit(base + 0.0, BD, 96)
            hit(base + 2.0, BD, 92)


# --------------------------------------------------------------------------
#  bars 36-47 : the climax
# --------------------------------------------------------------------------
def build_e():
    # --- bars 36-39 : full power, the motif hammered home
    for idx, bar in enumerate(range(36, 40)):
        base = bar * 4.0
        cym = BELL if idx < 2 else RIDE
        for i in range(8):
            hit(base + 0.5 * i, cym,
                (78 if i % 2 == 0 else 58) + RNG.uniform(-4, 4))
        if idx in (0, 2):
            hit(base + 0.0, CRASH, 112)
        if idx == 3:
            hit(base + 0.0, BD, 106)
            accent(base + 1.0, SD, 110)
            hit(base + 1.5, BD, 96)
            for i in range(8):
                hit(base + 2.0 + 0.25 * i, TOM[i % 6], 94 + 4 * i)
            hit(base + 3.5, BD, 100)
        else:
            hit(base + 0.0, BD, 106)
            hit(base + 0.75, BD, 88)
            hit(base + 2.0, BD, 98)
            hit(base + 2.75, BD, 86)
            accent(base + 1.0, SD, 108)
            accent(base + 3.0, SD, 112)
            ghost(base + 1.75, SD, 34)
            ghost(base + 3.5, SD, 32)

    # --- bars 40-43 : climbing, sixteenths through the kit
    for idx, bar in enumerate(range(40, 44)):
        base = bar * 4.0
        v0 = 80.0 + 7.0 * idx
        seq = [SD, TOM[0], SD, TOM[2], SD, TOM[3], SD, TOM[5],
               SD, TOM[1], SD, TOM[3], SD, TOM[4], TOM[5], TOM[5]]
        for i in range(16):
            v = (v0 + 18.0) if i % 4 == 0 else v0 + RNG.uniform(-6, 6)
            hit(base + 0.25 * i, seq[i], v)
        hit(base + 0.0, BD, 106)
        hit(base + 1.0, BD, 96)
        hit(base + 2.0, BD, 102)
        hit(base + 3.0, BD, 98)
        hit(base + 0.0, PHH, 54)
        hit(base + 2.5, PHH, 54)
        if idx in (1, 3):
            hit(base + 0.0, CRASH2 if idx == 1 else CRASH, 112)

    # --- bars 44-45 : doubles, snare against floor tom
    for idx, bar in enumerate(range(44, 46)):
        base = bar * 4.0
        pattern = [SD, SD, TOM[5], TOM[5], SD, SD, TOM[4], TOM[4]]
        for rep in range(2):
            for i, note in enumerate(pattern):
                v = (108.0 if i % 2 == 0 else 76.0) + RNG.uniform(-4, 4)
                hit(base + 2.0 * rep + 0.25 * i, note, v)
        hit(base + 0.0, BD, 108)
        hit(base + 2.0, BD, 104)

    # --- bars 46-47 : roll back up into the hook
    base = 46 * 4.0
    seq = [SD] * 8 + [TOM[0], TOM[1], TOM[2], TOM[3], TOM[4], TOM[5], TOM[5], TOM[5]]
    for i in range(16):
        hit(base + 0.25 * i, seq[i], 82 + 30 * (i / 15.0))
    hit(base + 0.0, BD, 104)
    hit(base + 2.0, BD, 100)

    base = 47 * 4.0
    for i in range(16):
        hit(base + 0.25 * i, SD, 60 + 40 * (i / 15.0) + RNG.uniform(-4, 4))
    hit(base + 3.5, BD, 114)
    hit(base + 3.5, SD, 114)


# --------------------------------------------------------------------------
#  bars 48-59 : the hook returns, then more invention
# --------------------------------------------------------------------------
def build_f():
    # --- bars 48-49 : the hook, played big
    base = 48 * 4.0
    hit(base + 0.0, CRASH, 116)
    hit(base + 0.0, BD, 112)
    accent(base + 1.0, SD, 112)
    hit(base + 1.5, BD, 96)
    ghost(base + 1.75, SD, 38)
    accent(base + 2.0, TOM[3], 108)
    hit(base + 2.5, BD, 92)
    accent(base + 3.0, SD, 110)
    ghost(base + 3.5, SD, 40)

    base = 49 * 4.0
    hit(base + 0.0, BD, 106)
    ghost(base + 0.5, SD, 36)
    accent(base + 1.0, TOM[2], 108)
    hit(base + 1.5, BD, 96)
    accent(base + 2.0, SD, 112)
    hit(base + 2.5, TOM[4], 100)
    hit(base + 3.0, SD, 106)
    hit(base + 3.5, CRASH2, 104)

    # --- bars 50-51 : the motif handed between toms and snare
    for idx, bar in enumerate(range(50, 52)):
        base = bar * 4.0
        pattern = [TOM[0], TOM[1], SD, TOM[2], TOM[3], SD, TOM[4], TOM[5]]
        for rep in range(2):
            for i, note in enumerate(pattern):
                v = (104.0 if i % 2 == 0 else 78.0) + RNG.uniform(-5, 5)
                hit(base + 2.0 * rep + 0.25 * i, note, v)
        hit(base + 0.0, BD, 104)
        hit(base + 1.0, BD, 92)
        hit(base + 2.0, BD, 100)
        hit(base + 1.0, PHH, 54)
        hit(base + 3.0, PHH, 54)
        if idx == 0:
            hit(base + 0.0, CRASH, 110)

    # --- bars 52-55 : singles that travel, building all the way
    for idx, bar in enumerate(range(52, 56)):
        base = bar * 4.0
        v0 = 84.0 + 6.0 * idx
        if idx < 2:
            seq = [SD, TOM[0], SD, TOM[1], SD, TOM[2], SD, TOM[3],
                   SD, TOM[4], SD, TOM[5], SD, TOM[4], TOM[5], TOM[5]]
        else:
            seq = [TOM[5], SD, TOM[4], SD, TOM[3], SD, TOM[2], SD,
                   TOM[1], SD, TOM[0], SD, TOM[1], TOM[2], TOM[3], TOM[5]]
        for i in range(16):
            v = (v0 + 18.0) if i % 2 == 0 else v0 + RNG.uniform(-6, 6)
            hit(base + 0.25 * i, seq[i], v)
        hit(base + 0.0, BD, 106)
        hit(base + 2.0, BD, 100)
        if idx in (0, 2):
            hit(base + 0.0, CRASH2 if idx == 0 else CRASH, 110)

    # --- bars 56-57 : double strokes on snare and floor tom
    for idx, bar in enumerate(range(56, 58)):
        base = bar * 4.0
        pairs = [SD, SD, TOM[5], TOM[5], SD, SD, TOM[3], TOM[3],
                 SD, SD, TOM[5], TOM[5], TOM[4], TOM[4], TOM[5], TOM[5]]
        for i, note in enumerate(pairs):
            v = (110.0 if i % 4 == 0 else
                 (84.0 if i % 2 == 0 else 70.0)) + RNG.uniform(-4, 4)
            hit(base + 0.25 * i, note, v)
        hit(base + 0.0, BD, 108)
        hit(base + 1.0, BD, 100)
        hit(base + 2.0, BD, 106)
        if idx == 1:
            hit(base + 3.5, CRASH, 112)

    # --- bars 58-59 : last fill before the finale
    base = 58 * 4.0
    run = [TOM[0], TOM[1], TOM[2], TOM[3], TOM[4], TOM[5],
           TOM[4], TOM[5], TOM[3], TOM[4], TOM[5], TOM[5],
           TOM[2], TOM[3], TOM[4], TOM[5]]
    for i in range(16):
        hit(base + 0.25 * i, run[i], 94 + 22 * (i / 15.0))
    hit(base + 0.0, BD, 106)

    base = 59 * 4.0
    for i in range(8):
        hit(base + 0.25 * i, SD, 88 + 5 * i)
    hit(base + 2.0, BD, 108)
    hit(base + 2.0, CRASH2, 110)
    hit(base + 3.0, TOM[5], 108)
    hit(base + 3.25, TOM[4], 104)
    hit(base + 3.5, TOM[3], 108)
    hit(base + 3.75, TOM[2], 112)


# --------------------------------------------------------------------------
#  bars 60-63 : finale -- fill, roll and one last hit that lands
# --------------------------------------------------------------------------
def build_finale():
    down = [TOM[0], TOM[1], TOM[2], TOM[3], TOM[4], TOM[5], TOM[4], TOM[5],
            TOM[0], TOM[1], TOM[2], TOM[3], TOM[4], TOM[5], TOM[4], TOM[5]]
    base = 60 * 4.0
    for i in range(16):
        hit(base + 0.25 * i, down[i], 92 + 4 * i)

    up = [TOM[5], TOM[4], TOM[3], TOM[2], TOM[1], TOM[0], TOM[1], TOM[0],
          TOM[5], TOM[4], TOM[3], TOM[2], TOM[1], TOM[0], SD, SD]
    base = 61 * 4.0
    for i in range(16):
        hit(base + 0.25 * i, up[i], 96 + 4 * i)

    # bar 62 -- a roll that accelerates and lifts into the last bar
    base = 62 * 4.0
    for i in range(16):
        hit(base + 0.125 * i, SD, 70 + 6 * i)
    hit(base + 2.0, BD, 108)
    for i in range(8):
        hit(base + 2.0 + 0.125 * i, SD, 96 + 4 * i)
    hit(base + 3.0, TOM[5], 110)
    hit(base + 3.25, TOM[4], 106)
    hit(base + 3.5, TOM[3], 110)
    hit(base + 3.75, TOM[2], 114)

    # bar 63 -- land it and stop
    base = 63 * 4.0
    hit(base + 0.0, CRASH, 120)
    hit(base + 0.0, BD, 118)
    hit(base + 0.75, SD, 58)
    hit(base + 1.5, BD, 92)
    hit(base + 2.0, SD, 116)
    hit(base + 2.75, SD, 58)
    hit(base + 3.0, TOM[3], 100)
    hit(base + 3.25, TOM[4], 104)
    hit(base + 3.5, TOM[5], 108)
    hit(base + 3.75, CRASH2, 118)
    hit(base + 3.75, BD, 118)
    hit(base + 3.75, SD, 118)


# --------------------------------------------------------------------------
#  tempo curve -- the pulse surges and settles
# --------------------------------------------------------------------------
def tempo_factor(bar):
    """Relative tempo of a bar (1.0 == the base pulse)."""
    if bar < 4:                        # intro: unhurried
        f = 0.96
    elif bar < 12:                     # statement: settles in
        f = 1.00 + 0.01 * (bar - 4) / 8.0
    elif bar < 20:                     # doubles: starting to push
        f = 1.01 + 0.04 * (bar - 12) / 8.0
    elif bar < 28:                     # singles: the fastest rush
        f = 1.05
    elif bar < 36:                     # breakdown: pulled right back
        f = 0.93
    elif bar < 48:                     # climax: climbing again
        f = 0.99 + 0.07 * (bar - 36) / 12.0
    elif bar < 60:                     # statements: riding high
        f = 1.06
    else:                              # finale: settling onto the last hit
        f = 1.06 - 0.05 * (bar - 60) / 3.0
    f *= 1.0 + 0.012 * math.sin(bar * 0.7)     # gentle surge and settle
    return f


# --------------------------------------------------------------------------
#  assemble the MIDI file
# --------------------------------------------------------------------------
def build_midi(path):
    # ---- humanise the timing --------------------------------------------
    jitter_cache = {}

    def timing_jitter(beat):
        key = int(round(beat * 96.0))
        if key not in jitter_cache:
            jitter_cache[key] = RNG.gauss(0.0, 0.011)
        return jitter_cache[key]

    def phrase_push(beat):
        """Phrases lean forward slightly and settle back on the downbeat."""
        bar = int(beat // 4)
        return (0.018 * math.sin(bar * 1.7)
                + 0.012 * math.sin(bar * 0.53 + 1.0)
                - 0.012 * ((bar % 4) / 3.0))

    played = []
    for beat, note, vel in events:
        t = beat + timing_jitter(beat) + phrase_push(beat)
        played.append((max(0, int(round(t * PPQ))), note, vel))
    played.sort(key=lambda e: (e[0], -e[2]))

    # ---- playability: at most two hands and two feet at any instant ------
    used = {}
    safe = []
    for tick, note, vel in played:
        hands, feet = used.get(tick, (0, 0))
        if note in FEET:
            if feet >= 2:
                continue
            used[tick] = (hands, feet + 1)
        else:
            if hands >= 2:
                continue
            used[tick] = (hands + 1, feet)
        safe.append((tick, note, vel))

    # ---- tempo map, scaled so the piece is exactly 120 seconds -----------
    factors = [tempo_factor(b) for b in range(TOTAL_BARS)]
    total_base_beats = sum(4.0 / f for f in factors)
    base_bpm = 60.0 * total_base_beats / TARGET_SECONDS

    messages = []
    for bar, f in enumerate(factors):
        us = int(round(60_000_000.0 / (base_bpm * f)))
        messages.append((bar * 4 * PPQ, 0, MetaMessage('set_tempo', tempo=us)))

    for tick, note, vel in safe:
        dur = max(1, int(round(DURATION.get(note, 0.25) * PPQ)))
        messages.append((tick, 2, Message('note_on', channel=CHANNEL,
                                          note=note, velocity=vel)))
        messages.append((tick + dur, 1, Message('note_off', channel=CHANNEL,
                                                note=note, velocity=0)))

    order = sorted(range(len(messages)),
                   key=lambda i: (messages[i][0], messages[i][1], i))

    mid = MidiFile(type=0, ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))

    last = 0
    for i in order:
        tick, _prio, msg = messages[i]
        msg.time = tick - last
        last = tick
        track.append(msg)

    mid.save(path)
    return len(safe)


def main():
    build_intro()
    build_a()
    build_b()
    build_c()
    build_d()
    build_e()
    build_f()
    build_finale()

    n = build_midi('solo.mid')
    print('wrote solo.mid  ({} strokes, {} bars, {:.0f} s)'.format(
        n, TOTAL_BARS, TARGET_SECONDS))


if __name__ == '__main__':
    main()
