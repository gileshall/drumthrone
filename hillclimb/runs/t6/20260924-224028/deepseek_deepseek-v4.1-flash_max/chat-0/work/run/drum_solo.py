#!/usr/bin/env python3
"""
drum_solo.py
============

Writes ``solo.mid`` in the current directory: a two minute unaccompanied
drum solo for General MIDI percussion (MIDI channel 10).

How it is put together
----------------------
* The music is composed in score time (480 ticks per quarter) and a smooth
  tempo curve is laid over it afterwards, so phrases rush forward into
  cadences and ease back afterwards instead of sitting on a click.
* Every stroke is then humanised in micro timing and in dynamics: accents
  land on top of the beat, ghost notes sit back behind it.
* The material grows out of a couple of small rhythmic motifs which keep
  coming back in new orchestrations; density and volume are shaped inside
  phrases (roll swells, crescendos, sudden drops) rather than by making
  whole sections louder.
* Playability is enforced: never more than two hands and two feet at one
  instant, and no drum retriggered faster than a hand can move.
* Fully deterministic: the same file is written on every run.
"""

import bisect
import math
import random

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

# ---------------------------------------------------------------------------
#  timing constants
# ---------------------------------------------------------------------------
PPQ = 480
S32 = PPQ // 8          # 60  ticks
S16 = PPQ // 4          # 120 ticks
S8 = PPQ // 2           # 240 ticks
BEAT = PPQ
BAR = 4 * PPQ
CHANNEL = 9             # that is MIDI channel 10

TARGET = 117.4          # when the last hit should land (seconds)


def B(n):
    """Absolute tick of the first beat of bar *n* (bars counted from 1)."""
    return (n - 1) * BAR


rng = random.Random(20190714)

# ---------------------------------------------------------------------------
#  the kit:  character -> (GM note, base velocity, ring length, limb)
# ---------------------------------------------------------------------------
KIT = {
    'K': (36, 112,  90, 'foot'),   # bass drum, accented
    'k': (36,  76,  90, 'foot'),   # bass drum, soft
    'p': (44,  72,  40, 'foot'),   # hi-hat pedal
    'S': (38, 112,  70, 'hand'),   # snare, accented
    's': (38,  84,  70, 'hand'),   # snare, normal
    'g': (38,  30,  55, 'hand'),   # ghost note
    'G': (38,  46,  55, 'hand'),   # half ghost
    'e': (40, 110,  70, 'hand'),   # rim shot / electric snare
    'x': (37,  78,  40, 'hand'),   # side stick
    'h': (42,  70,  40, 'hand'),   # closed hi-hat
    'H': (42,  98,  40, 'hand'),   # closed hi-hat, accented
    'o': (46,  92, 400, 'hand'),   # open hi-hat
    'R': (51,  74, 150, 'hand'),   # ride
    'y': (51,  98, 150, 'hand'),   # ride, accented
    'b': (53,  96, 190, 'hand'),   # ride bell
    'c': (49, 108, 800, 'hand'),   # crash 1
    'd': (57, 106, 800, 'hand'),   # crash 2
    'B': (52, 104, 700, 'hand'),   # china
    'P': (55,  94, 300, 'hand'),   # splash
    '1': (50,  94, 200, 'hand'),   # high tom
    '2': (48,  94, 220, 'hand'),
    '3': (47,  94, 250, 'hand'),
    '4': (45,  94, 280, 'hand'),
    '5': (43,  94, 320, 'hand'),
    '6': (41,  94, 360, 'hand'),   # low floor tom
    't': (54,  66,  60, 'hand'),   # tambourine
    'w': (56,  76, 100, 'hand'),   # cowbell
    'v': (75,  82,  50, 'hand'),   # claves
    'T': (81,  70, 400, 'hand'),   # triangle
}

EVENTS = []          # [tick, note, velocity, length, limb, character]


# ---------------------------------------------------------------------------
#  little writing tools
# ---------------------------------------------------------------------------
def add(t, ch, vel=None, scale=1.0, dur=None):
    note, v0, d0, limb = KIT[ch]
    if vel is None:
        vel = v0 * scale
    v = max(1, min(127, int(round(vel))))
    EVENTS.append([float(t), note, v, d0 if dur is None else dur, limb, ch])


def pat(t, s, step=S16, scale=1.0, push=0.0):
    """Write a pattern string.  '.' is a rest, spaces are ignored so that a
    bar can be written as four clearly countable groups of four."""
    i = 0
    for c in s:
        if c == ' ':
            continue
        if c != '.':
            add(t + i * step + push, c, scale=scale)
        i += 1


def run(t, chars, step, v0=94.0, v1=112.0):
    """Even stream of single strokes with a velocity ramp (a fill)."""
    n = len(chars)
    for i, c in enumerate(chars):
        if c == '.':
            continue
        f = i / max(1, n - 1)
        add(t + i * step, c, vel=v0 + (v1 - v0) * f)


def roll(t0, t1, ch, v0, v1, step0, step1=None, curve=1.0):
    """A press roll between two ticks: velocity swell plus optional change
    of stroke rate (accelerando) towards the end."""
    if step1 is None:
        step1 = step0
    span = float(t1 - t0)
    pos = float(t0)
    while pos < t1 - 2:
        f = min(1.0, max(0.0, (pos - t0) / span))
        add(pos, ch, vel=v0 + (v1 - v0) * (f ** curve))
        pos += step0 + (step1 - step0) * (f ** curve)


# ---------------------------------------------------------------------------
#  the solo
# ---------------------------------------------------------------------------
def compose():
    # -----------------------------------------------------------------
    #  bars 1-4 : entrance, groove stated quietly
    # -----------------------------------------------------------------
    t = B(1)
    pat(t, "c...  ....  ....  ....")
    pat(t, "K...  ....  ....  ....")
    pat(t, "..R.  R.R.  R.R.  R.R.")
    pat(t, ".g..  ....  ....  ....")
    pat(t, "....  ....  ....  ..S.")

    t = B(2)                                    # the hook, first time
    pat(t, "yRyRyRyR", step=S8)
    pat(t, "K..k  ..K.  ..K.  ..k.")
    pat(t, ".g..  S..g  ..g.  S..g")

    t = B(3)
    pat(t, "yRRRyRRR", step=S8)
    pat(t, "K..k  .K.k  ..K.  .k..")
    pat(t, ".gg.  S..g  ..g.  S..g")
    pat(t, "....  ....  ....  ..o.")

    t = B(4)                                    # first fill
    pat(t, "yRyR  ....", step=S8)
    pat(t, "K..k  ..K.  ....  ....")
    pat(t, ".g..  S..g  ....  ....")
    pat(t, "....  ....  K..K  ....")
    pat(t, "....  ....  Ssss  2345")

    # -----------------------------------------------------------------
    #  bars 5-12 : the theme stated and varied, never twice the same way
    # -----------------------------------------------------------------
    t = B(5)
    pat(t, "c...  ....  ....  ....")
    pat(t, ".RyRyRyR", step=S8)
    pat(t, "K..k  ..K.  ..K.  ..k.")
    pat(t, ".g..  S..g  ..g.  S..g")

    t = B(6)
    pat(t, "yRRRyRRR", step=S8)
    pat(t, "K..k  .K.k  ..K.  .k..")
    pat(t, ".g..  S..g  ..g.  S..g")
    pat(t, "....  ....  ....  ..1.")

    t = B(7)                                    # hands answer the feet
    pat(t, "HhHh  HhHh", step=S8, scale=0.95)
    pat(t, "K..k  ..K.", step=S8)
    pat(t, "..g.  S...", step=S8)
    pat(t + 2 * BEAT, "1..2  3.45")

    t = B(8)
    pat(t, "yRyR  ....", step=S8)
    pat(t, "K..k  ..K.", step=S8)
    pat(t, ".g..  S..g", step=S8)
    pat(t + 2 * BEAT, "SsS1  2345")

    t = B(9)                                    # busier, ghost flurries
    pat(t, "c...  ....  ....  ....")
    pat(t, ".RyRyRyR", step=S8)
    pat(t, "K..k  ..K.  k.K.  ..k.")
    pat(t, ".gg.  S..g  ..g.  S.gg")

    t = B(10)
    pat(t, "yRyRbRyR", step=S8)                 # a bell sneaks in
    pat(t, "K..k  .K..  K.k.  K...")
    pat(t, ".g.g  S..g  ..g.  S..g")

    t = B(11)
    pat(t, "HhHh  HhHh", step=S8, scale=0.92)
    pat(t, "K..k  ..K.", step=S8, scale=0.95)
    pat(t, ".g.S  ...g", step=S8, scale=0.95)
    pat(t + 2 * BEAT, "2..3  4.56")             # same motif, lower toms

    t = B(12)
    pat(t, "yRyR  ....", step=S8)
    pat(t, "K..k  ..K.", step=S8)
    pat(t, ".g..  S..g", step=S8)
    pat(t + 2 * BEAT, "SSs1  2345")
    pat(t + 2 * BEAT, "K..K  ....")

    # -----------------------------------------------------------------
    #  bars 13-20 : development - the motif walks around the kit
    # -----------------------------------------------------------------
    t = B(13)
    pat(t, "c...  ....  ....  ....")
    pat(t, "..1.  ..2.  ..3.  ..4.")
    pat(t, "K...  ..k.  ..K.  ....")
    pat(t, "....  S...  ....  S...")

    t = B(14)
    pat(t, "..2.  ..3.  ..4.  3456")
    pat(t, "K...  ..k.  ..K.  ....")
    pat(t, "....  S...  ....  S...")
    pat(t, "..g.  ....  ....  ....")

    t = B(15)
    pat(t, "HhHh  HhHh", step=S8, scale=0.95)
    pat(t, "K..k  ..K.", step=S8)
    pat(t, "..g.  S...", step=S8)
    pat(t + 2 * BEAT, "1..2  3.45")

    t = B(16)                                   # doubles round the kit
    pat(t, "yRyR  ....", step=S8)
    pat(t, "K..k  ..K.", step=S8)
    pat(t, ".g..  S..g", step=S8)
    pat(t + 2 * BEAT, "1122  3344")

    t = B(17)                                   # sudden drop
    pat(t, "h.h.  h.h.  h.h.  h.h.", scale=0.80)
    pat(t, "K..k  ..K.  ...K  ..k.", scale=0.85)
    pat(t, ".g..  S..g  ..g.  S..g", scale=0.78)

    t = B(18)                                   # and the build
    pat(t, "K..K  ..K.  K.K.  K.K.", scale=0.90)
    pat(t, "S.s.  S.s.  S.s.  S.sS", scale=0.95)
    pat(t, ".g.g  .g.g  .g.g  .g.g", scale=0.95)

    t = B(19)                                   # cascade there and back
    pat(t, "c...  ....  c...  ....", scale=0.95)
    pat(t, "Ss12  3456  6543  21SS")
    pat(t, "K...  ..K.  K...  ..K.")

    t = B(20)
    pat(t, "Ssgs  Ssgs  ....  ....", scale=0.95)
    pat(t, "K..K  ..K.  ....  ....")
    pat(t + 2 * BEAT, "1234  56S.")
    pat(t + 2 * BEAT, "K...  K...")

    # -----------------------------------------------------------------
    #  bars 21-28 : first climax - the hands take over
    # -----------------------------------------------------------------
    t = B(21)
    pat(t, "c...  ....  ....  ....")
    pat(t, "K..k  ..K.  ..k.  K..k")
    pat(t, "S.sg  S.sg  S.sg  S.sg")

    t = B(22)
    pat(t, "K..k  ..K.  ..k.  K..k")
    pat(t, "S.sg  S.sg  S.sg  1234")

    t = B(23)
    pat(t, "HhHh  HhHh", step=S8)
    pat(t, "K..K  ..K.  K.K.  K.K.")
    pat(t, "..S.  ..S.  ..S.  ..S.")

    t = B(24)                                   # stop-time break
    pat(t, "c...  ....  ....  ....")
    pat(t, "K...  ..K.  ..K.  ....")
    pat(t, "S...  ..S.  ..S.  ..gg")

    t = B(25)
    pat(t, "HhHh  HhHh", step=S8, scale=0.95)
    pat(t, "K..k  ..K.  ..k.  K..k")
    pat(t, "..S.  ..S.  ..S.  ..S.")
    pat(t, "....  ...g  ....  ...g")

    t = B(26)
    pat(t, "K..k  ..K.  ..k.  K..k")
    pat(t, "Ssgs  Ssgs  Ssgs  Ssgs", scale=0.98)

    t = B(27)
    pat(t, "K..K  ..K.  K..K  ..K.")
    run(t, "1234561234561234", S16, 98, 114)

    t = B(28)
    pat(t, "c...  ....  ....  ....", scale=0.95)
    pat(t, "Ssgs  Ssgs  ....  ....")
    pat(t, "K..K  ..K.  ....  ....")
    pat(t + 2 * BEAT, "1234  5612")
    pat(t + 2 * BEAT, "K...  K...")

    # -----------------------------------------------------------------
    #  bars 29-36 : release - whisper, then build back up
    # -----------------------------------------------------------------
    t = B(29)
    pat(t, "P...  ....  ....  ....", scale=0.85)
    pat(t, "p...  p...  p...  p...")
    pat(t, "....  x...  ....  x...", scale=0.90)

    t = B(30)
    pat(t, "p...  p...  p...  p...", scale=0.95)
    pat(t, "....  x...  ....  x...", scale=0.85)
    pat(t, "..6.  ....  ....  ..5.")

    t = B(31)
    pat(t, "p...  p...  p...  p...", scale=0.95)
    pat(t, "....  x...  ..x.  x...", scale=0.85)
    pat(t, "..g.  ..g.  ..g.  ..g.", scale=0.95)

    t = B(32)
    pat(t, "p...  p...  p...  p...")
    pat(t, "....  x...  ....  x...", scale=0.90)
    pat(t, "..5.  ....  ..4.  ....", scale=0.90)
    pat(t, "....  ....  ....  ..S.", scale=0.90)

    t = B(33)
    pat(t, "H.h.  H.h.  H.h.  H.h.", scale=0.72)
    pat(t, "K..k  ..K.  ...k  ..k.", scale=0.85)
    pat(t, "..g.  S..g  ..g.  S..g", scale=0.82)

    t = B(34)
    pat(t, "H.h.  H.h.  H.h.  H.h.", scale=0.82)
    pat(t, "K..k  ..K.  K.k.  K.k.", scale=0.88)
    pat(t, "..g.  S..g  ..g.  S..g", scale=0.85)

    t = B(35)
    pat(t, "H.h.  H.h.  H.h.  H.h.", scale=0.90)
    pat(t, "K..k  K.k.  K.k.  K.k.", scale=0.94)
    pat(t, "..g.  S..g  ..g.  S..g", scale=0.92)

    t = B(36)
    pat(t, "H.h.  H.h.  H.h.  H.h.")
    pat(t, "K..K  K..K  K..K  K..K")
    pat(t, "....  S...  ....  S..S")

    # -----------------------------------------------------------------
    #  bars 37-42 : the roll grows and carries into the second climax
    # -----------------------------------------------------------------
    t = B(37)
    pat(t, "p...  p...  p...  p...")
    pat(t, "K...  K...  K...  K...")
    pat(t, "....  x...  ....  x...", scale=0.95)
    roll(t + 2 * BEAT, t + 4 * BEAT, 'S', 46, 72, S16, S16)

    t = B(38)
    pat(t, "K...  K...  K...  K...")
    roll(t, t + 4 * BEAT, 'S', 60, 88, S16, S16)

    t = B(39)
    pat(t, "K...  K...  K...  K...")
    roll(t, t + 4 * BEAT, 'S', 72, 100, S32, S32)

    t = B(40)
    pat(t, "K...  K...  K...  K...")
    roll(t, t + 4 * BEAT, 'S', 88, 116, S32, S32, curve=0.8)

    t = B(41)
    pat(t, "K...  K...  K...  K...")
    roll(t, t + 2 * BEAT, 'S', 100, 122, S32, S32)
    pat(t + 2 * BEAT, "1234  5612")
    pat(t + 2 * BEAT, "K...  K...")

    t = B(42)
    pat(t, "Ssgs  Ssgs  ....  ....")
    pat(t, "K..K  ..K.  ....  ....")
    pat(t + 2 * BEAT, "1234  56S.")
    pat(t + 2 * BEAT, "K...  K...")

    # -----------------------------------------------------------------
    #  bars 43-52 : the theme comes back, fortissimo
    # -----------------------------------------------------------------
    t = B(43)
    pat(t, "c...  ....  ....  ....")
    pat(t, "bRbRbRbR", step=S8)
    pat(t, "K..k  ..K.  ..k.  K..k")
    pat(t, ".g..  S..g  ..g.  S..g")

    t = B(44)
    pat(t, "bRbRbRbR", step=S8)
    pat(t, "K..k  .K.k  ..K.  .k..")
    pat(t, ".g..  S..g  ..g.  S..g")
    pat(t, "....  ....  ....  ..1.")

    t = B(45)
    pat(t, "S.sg  S.sg  S.sg  S.sg")
    pat(t, "K..K  ..K.  K..K  ..K.")

    t = B(46)
    pat(t, "HhHh  HhHh", step=S8)
    pat(t, "K..K  K..K  K..K  K..K")
    pat(t, "S...  S...  S...  S...")
    pat(t, "..g.  ..g.  ..g.  ..g.")

    t = B(47)
    pat(t, "bRbRbRbR", step=S8)
    pat(t, "K..k  .K.k  K.k.  K.k.")
    pat(t, "..S.  ..S.  ..S.  ..S.")

    t = B(48)
    pat(t, "c...  ....  ....  ....", scale=0.98)
    run(t, "1234561234561234", S16, 102, 118)
    pat(t, "K...  K...  K...  K...")

    t = B(49)
    pat(t, "1122  3344  5566  1122")
    pat(t, "K..k  ..K.  ..k.  K..k")

    t = B(50)
    pat(t, "Ssgs  Ssgs  Ssgs  ....")
    pat(t, "K..K  ..K.  K..K  ....")
    pat(t + 3 * BEAT, "1234")

    t = B(51)
    pat(t, "c...  ....  d...  ....", scale=0.98)
    pat(t, "S.s.  S.s.  S.s.  S.sS")
    pat(t, "K..K  K..K  K..K  K..K")

    t = B(52)
    pat(t, "Ssgs  Ssgs  Ssgs  ....")
    pat(t, "K..K  ..K.  K..K  ....")
    pat(t + 3 * BEAT, "2345")

    # -----------------------------------------------------------------
    #  bars 53-64 : finale - highest energy, one last dip, land the hit
    # -----------------------------------------------------------------
    t = B(53)
    pat(t, "c...  ....  ....  ....")
    pat(t, "Ssgs  Ssgs  Ssgs  Ssgs")
    pat(t, "K..K  ..K.  K..K  ..K.")

    t = B(54)
    pat(t, "bRbRbRbR", step=S8)
    pat(t, "K..k  ..K.  ..K.  ..k.")
    pat(t, ".g..  S..g  ..g.  S..g")

    t = B(55)
    pat(t, "Ssgs  Ssgs  Ssgs  1234")
    pat(t, "K..K  ..K.  K..K  ....")

    t = B(56)
    pat(t, "c...  ....  ....  ....")
    pat(t, "K...  ..K.  K...  ..K.")
    pat(t, "S...  ..S.  S...  ..S.")
    pat(t, "....  ....  ....  ..gg")

    t = B(57)                                   # pull the volume right out
    pat(t, "h.h.  h.h.  h.h.  h.h.", scale=0.60)
    pat(t, "K..k  ..K.  ...k  ..k.", scale=0.75)
    pat(t, ".g..  S..g  ..g.  S..g", scale=0.68)

    t = B(58)
    pat(t, "h.h.  h.h.  h.h.  h.h.", scale=0.70)
    pat(t, "K..k  K.k.  K.k.  K.k.", scale=0.85)
    pat(t, "...g  S...  ...g  S...", scale=0.78)

    t = B(59)
    pat(t, "H.h.  H.h.  H.h.  H.h.", scale=0.85)
    pat(t, "K..K  K..K  K..K  K..K", scale=0.90)
    pat(t, "S.s.  S.s.  S.s.  S.sS", scale=0.90)

    t = B(60)
    pat(t, "H.h.  H.h.  H.h.  H.h.", scale=0.97)
    pat(t, "K..K  K..K  K..K  K..K", scale=0.98)
    pat(t, "S.s.  S.s.  S.s.  S.sS", scale=0.98)
    pat(t, "....  ....  ....  ..1.", scale=0.95)

    t = B(61)
    pat(t, "Ssgs  Ssgs  ....  ....")
    pat(t, "K..K  ..K.  ....  ....")
    pat(t + 2 * BEAT, "1234  5612")
    pat(t + 2 * BEAT, "K...  K...")

    t = B(62)
    pat(t, "1122  3344  1234  5612")
    pat(t, "K..K  K..K  K..K  K..K")

    t = B(63)                                   # last roll, breath, hit
    pat(t, "K...  K...  K...  K...")
    roll(t, t + 4 * BEAT - S16, 'S', 98, 127, S32, S32, curve=0.9)

    t = B(64)
    add(t, 'c', vel=124, dur=6 * BEAT)
    add(t, 'K', vel=127)
    add(t, 'S', vel=125)


# ---------------------------------------------------------------------------
#  human performance
# ---------------------------------------------------------------------------
def tidy():
    """Micro timing, dynamics, and physical plausibility."""

    # --- every stroke gets its own timing and weight -------------------
    for e in EVENTS:
        t, note, vel, dur, limb, ch = e
        if ch in 'gG' or vel < 50:
            dt = rng.gauss(3.6, 3.0)        # ghost notes sit back
        elif vel >= 100:
            dt = rng.gauss(-0.6, 2.2)       # accents sit on top
        else:
            dt = rng.gauss(0.4, 2.6)
        dt += 1.7 * math.sin(2.0 * math.pi * t / (2.0 * BAR) + 0.6)
        e[0] = t + dt
        e[2] = max(1, min(127, int(round(vel + rng.gauss(0.0, 3.0)))))

    # --- at most two hands and two feet at any instant -----------------
    for _ in range(12):
        EVENTS.sort(key=lambda e: (e[0], -e[2]))
        groups = {}
        for e in EVENTS:
            groups.setdefault(int(round(e[0])), []).append(e)
        moved = 0
        for tick, evs in groups.items():
            for limb, limit in (('hand', 2), ('foot', 2)):
                sel = [e for e in evs if e[4] == limb]
                if len(sel) > limit:
                    sel.sort(key=lambda e: -e[2])
                    for e in sel[limit:]:
                        e[0] = tick + 2.5
                        moved += 1
        if not moved:
            break

    # --- a drum can only be struck so fast by a real hand --------------
    EVENTS.sort(key=lambda e: e[0])
    last = {}
    for e in EVENTS:
        n = e[1]
        if n in last and e[0] - last[n] < 16.0:
            e[0] = last[n] + 16.0
        last[n] = e[0]
    EVENTS.sort(key=lambda e: e[0])


# ---------------------------------------------------------------------------
#  time: a smooth tempo curve that breathes with the phrases
# ---------------------------------------------------------------------------
TEMPO = [
    (B(1), 96), (B(3), 104), (B(5), 112), (B(9), 115),
    (B(13), 119), (B(17), 122), (B(21), 126), (B(25), 128),
    (B(29), 106), (B(31), 104), (B(33), 110), (B(37), 116),
    (B(39), 122), (B(42), 130), (B(43), 134), (B(47), 138),
    (B(51), 141), (B(53), 144), (B(57), 130), (B(59), 138),
    (B(61), 144), (B(63), 150), (B(64), 152),
]

# (where the phrase leans forward, how many bpm, how wide the approach is)
PUSH = [
    (B(5), 6, 960), (B(9), 5, 960), (B(13), 7, 960), (B(17), 5, 960),
    (B(21), 8, 960), (B(25), 4, 720), (B(29), 9, 960), (B(37), 6, 960),
    (B(43), 10, 960), (B(49), 6, 960), (B(53), 8, 960), (B(57), 4, 720),
    (B(61), 6, 960), (B(63), 8, 960), (B(64), 10, 960),
]


def push_bpm(t):
    tot = 0.0
    for pt, amt, half in PUSH:
        if t <= pt:
            w = 1.0 - (pt - t) / float(half)
            if w > 0.0:
                tot += amt * (w ** 1.6)
        else:
            w = 1.0 - (t - pt) / (2.0 * half)
            if w > 0.0:
                tot += amt * 0.5 * (w ** 1.2)
    return tot


def bpm_at(t):
    tm = TEMPO
    if t <= tm[0][0]:
        base = tm[0][1]
    elif t >= tm[-1][0]:
        base = tm[-1][1]
    else:
        base = tm[-1][1]
        for i in range(len(tm) - 1):
            t0, v0 = tm[i]
            t1, v1 = tm[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / float(t1 - t0)
                f = f * f * (3.0 - 2.0 * f)
                base = v0 + (v1 - v0) * f
                break
    return base + push_bpm(t)


def make_tempo_map(end_tick):
    evs = []
    t = 0
    while t < end_tick:
        evs.append([t, bpm_at(t)])
        t += S8
    evs.append([end_tick, bpm_at(end_tick)])
    return evs


def time_of(tick, evs):
    total = 0.0
    pt, pb = evs[0]
    if tick <= pt:
        return 0.0
    for i in range(1, len(evs)):
        t, bpm = evs[i]
        if t >= tick:
            total += (tick - pt) * 60.0 / (PPQ * pb)
            return total
        total += (t - pt) * 60.0 / (PPQ * pb)
        pt, pb = t, bpm
    total += (tick - pt) * 60.0 / (PPQ * pb)
    return total


# ---------------------------------------------------------------------------
#  rendering
# ---------------------------------------------------------------------------
def render(tempo_events, end_tick):
    mid = MidiFile(type=1, ticks_per_beat=PPQ)

    conductor = MidiTrack()
    mid.tracks.append(conductor)
    conductor.append(MetaMessage('track_name', name='Drum Solo', time=0))
    conductor.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    prev = 0
    for tick, bpm in tempo_events:
        tick = int(tick)
        conductor.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm),
                                     time=max(0, tick - prev)))
        prev = tick
    conductor.append(MetaMessage('end_of_track', time=max(0, int(end_tick) - prev)))

    drums = MidiTrack()
    mid.tracks.append(drums)
    drums.append(MetaMessage('track_name', name='Drums', time=0))
    drums.append(Message('program_change', channel=CHANNEL, program=0, time=0))

    # a fresh stroke chokes the previous one on the same drum
    onsets = {}
    for e in EVENTS:
        onsets.setdefault(e[1], []).append(int(round(e[0])))
    for k in onsets:
        onsets[k].sort()

    msgs = []
    for e in EVENTS:
        t = int(round(e[0]))
        lst = onsets[e[1]]
        j = bisect.bisect_right(lst, t)
        length = int(e[3])
        if j < len(lst):
            gap = lst[j] - t
            if gap < length:
                length = max(10, gap - 3)
        msgs.append((t, 1, e[1], e[2]))
        msgs.append((t + length, 0, e[1], 0))

    msgs.sort(key=lambda m: (m[0], m[1]))
    prev = 0
    for tick, onoff, note, vel in msgs:
        delta = max(0, tick - prev)
        prev = tick
        if onoff:
            drums.append(Message('note_on', channel=CHANNEL, note=note,
                                 velocity=vel, time=delta))
        else:
            drums.append(Message('note_off', channel=CHANNEL, note=note,
                                 velocity=0, time=delta))
    drums.append(MetaMessage('end_of_track', time=0))
    return mid


def main():
    compose()
    tidy()

    end_tick = B(64) + 2 * BAR
    evs = make_tempo_map(end_tick)

    # stretch the whole tempo curve so that the last hit lands right around
    # the two minute mark, with room for the final cymbal to ring out
    k = time_of(B(64), evs) / TARGET
    evs = [[t, bpm * k] for t, bpm in evs]

    mid = render(evs, end_tick)
    mid.save('solo.mid')

    length = time_of(max(m[0] for m in
                         [(int(round(e[0])) + int(e[3]), 0) for e in EVENTS]), evs)
    print("solo.mid written: %d strokes, %.1f s, tempo %.0f-%.0f bpm"
          % (len(EVENTS), length, min(b for _, b in evs), max(b for _, b in evs)))


if __name__ == '__main__':
    main()
