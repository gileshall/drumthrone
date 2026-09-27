#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid  --  a two minute General MIDI drum solo on channel 10.

The solo is put together with motifs, phrase shapes, deliberate time
placement (laid back / pushing) and a final downbeat, rather than by
making sections simply louder or softer.  Everything is deterministic:
the file is byte-identical on every run.

Requires only mido.
"""

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

# ----------------------------------------------------------------- timing
PPQ   = 480
BPM   = 120
TEMPO = 60_000_000 // BPM          # 500000 -> 120 bpm
TPS   = PPQ * BPM / 60.0           # 960 ticks per second
BEAT  = 60.0 / BPM                 # 0.5 s
BAR   = 4 * BEAT                   # 2.0 s
S16   = BEAT / 4.0                 # 0.125 s (one sixteenth)
CH    = 9                          # MIDI channel 10

# ------------------------------------------------------------ GM drum map
KICK, RIM, SNARE       = 36, 37, 38
HHC, HHP, HHO          = 42, 44, 46
TOM1, TOM2, TOM3, TOM4 = 50, 48, 47, 45
FLR1, FLR2             = 43, 41
CRASH1, CRASH2         = 49, 57
RIDE, BELL, SPLASH     = 51, 53, 55
CHINA, TAMB, COWBELL   = 52, 54, 56
BLOCK_HI, BLOCK_LO     = 76, 77

# swung eighth positions (2:1) inside a 4/4 bar, in sixteenth units
SW2 = 4.0 + 8.0 / 3.0              # "&" of 2
SW4 = 12.0 + 8.0 / 3.0             # "&" of 4

events = []                        # (t seconds, note, velocity, duration)


def add(t, note, vel, dur=0.09):
    events.append((t, note, int(max(1, min(127, round(vel)))), dur))


def tt(bar, pos, feel=0.0):
    """Absolute time of sixteenth-position `pos` in 1-indexed `bar`."""
    return (bar - 1) * BAR + pos * S16 + feel


def play(bar, pattern, feel=0.0):
    for pos, note, vel, dur in pattern:
        add(tt(bar, pos, feel), note, vel, dur)


# ======================================================================
#  I.  THEME  (bars 1-4)  -- the motif, stated plainly
# ======================================================================
L = 0.014                                   # laid back

# bar 1 -- alone, spacious
play(1, [
    (0,  SNARE, 112, .10), (3,  SNARE, 40, .05), (6,  SNARE, 98, .10),
    (10, SNARE, 104, .10), (14, SNARE, 44, .05),
    (0,  KICK,  110, .12), (8,  KICK,  100, .12), (11, KICK, 70, .10),
    (4,  HHP,    78, .12), (12, HHP,    74, .12)], L)

# bar 2 -- the motif with an answer on the toms
play(2, [
    (0,  SNARE, 110, .10), (3,  SNARE, 40, .05), (6,  SNARE, 96, .10),
    (10, SNARE, 100, .10),
    (12, TOM1,  104, .10), (13, TOM1,  62, .05), (14, TOM3, 100, .10),
    (15, FLR1,   96, .10),
    (0,  KICK,  106, .12), (8,  KICK,  98, .12), (15, KICK, 92, .12),
    (4,  HHP,    76, .12), (12, HHP,    72, .12)], L)

# bar 3 -- theme again, hi-hat joins, a touch more forward
p  = [(0, SNARE, 114, .10), (3, SNARE, 44, .05), (6, SNARE, 100, .10),
      (10, SNARE, 108, .10), (14, SNARE, 46, .05),
      (0, KICK, 112, .12), (8, KICK, 104, .12), (11, KICK, 72, .10),
      (4, HHP, 80, .12), (12, HHP, 76, .12)]
p += [(q, HHC, 66 if q % 8 == 0 else 54, .07) for q in range(0, 16, 2)]
play(3, p, 0.010)

# bar 4 -- fill that carries into the groove
p  = [(0, SNARE, 104, .08), (1, SNARE, 58, .05), (2, SNARE, 62, .05), (3, SNARE, 68, .05),
      (4, SNARE, 108, .08), (5, SNARE, 62, .05), (6, SNARE, 66, .05), (7, SNARE, 74, .05),
      (8, TOM1, 102, .08), (9, TOM1, 76, .05), (10, TOM2, 98, .08), (11, TOM2, 78, .05),
      (12, TOM3, 104, .08), (13, TOM3, 80, .05), (14, FLR1, 108, .08), (15, FLR1, 88, .05),
      (0, KICK, 104, .12), (4, KICK, 92, .12), (8, KICK, 98, .12), (12, KICK, 108, .12)]
play(4, p, 0.005)

# ======================================================================
#  II.  THE GROOVE  (bars 5-8)  -- the beat drops
# ======================================================================
play(5, [(0, CRASH1, 112, 1.6), (0, KICK, 114, .12),
         (4, SNARE, 110, .10), (12, SNARE, 114, .10),
         (3, SNARE, 40, .05), (11, SNARE, 42, .05), (14, SNARE, 46, .05),
         (7, KICK, 92, .12), (10, KICK, 88, .12),
         (4, HHP, 76, .12), (12, HHP, 74, .12)]
        + [(q, RIDE, 92 if q % 8 == 0 else 68, .08) for q in range(2, 16, 2)],
        0.008)

play(6, [(0, KICK, 112, .12), (4, SNARE, 110, .10), (12, SNARE, 112, .10),
         (3, SNARE, 38, .05), (5, SNARE, 42, .05), (11, SNARE, 40, .05), (14, SNARE, 44, .05),
         (7, KICK, 94, .12), (10, KICK, 90, .12), (15, KICK, 84, .12),
         (4, HHP, 76, .12), (12, HHP, 74, .12)]
        + [(q, RIDE, 92 if q % 8 == 0 else 68, .08) for q in range(0, 16, 2)],
        0.008)

play(7, [(0, KICK, 112, .12), (4, SNARE, 110, .10), (12, SNARE, 114, .10),
         (3, SNARE, 40, .05), (10, KICK, 92, .12), (11, SNARE, 42, .05), (14, SNARE, 46, .05),
         (4, HHP, 78, .12), (12, HHP, 76, .12),
         (0, BELL, 102, .30), (8, BELL, 98, .30),
         (2, RIDE, 66, .08), (6, RIDE, 70, .08), (10, RIDE, 68, .08), (14, RIDE, 72, .08)],
        0.008)

play(8, [(0, KICK, 112, .12), (4, SNARE, 112, .10), (4, HHP, 74, .12),
         (0, RIDE, 92, .08), (2, RIDE, 68, .08), (6, RIDE, 70, .08),
         (8, KICK, 96, .12), (12, KICK, 100, .12),
         (8, TOM1, 100, .06), (9, TOM1, 78, .06), (10, TOM2, 100, .06), (11, TOM2, 80, .06),
         (12, TOM3, 104, .06), (13, TOM4, 86, .06), (14, FLR1, 110, .06), (15, FLR2, 100, .06)],
        0.005)

# ======================================================================
#  III.  HANDS  (bars 9-12)  -- single strokes that travel
# ======================================================================
# bar 9: train beat on the snare
p = []
for q in range(16):
    p.append((q, SNARE, 112 if q % 4 == 0 else (66 if q % 2 == 0 else 58), .07))
for q in (0, 4, 8, 12):
    p.append((q, KICK, 100 + (6 if q in (0, 12) else 0), .10))
play(9, p, 0.003)

# bar 10: same hand, but the accents spell the motif
p = []
for q in range(16):
    p.append((q, SNARE, 108 if q in (0, 3, 6, 10, 14) else (62 if q % 2 == 0 else 56), .07))
p += [(0, KICK, 104, .10), (8, KICK, 104, .10), (6, KICK, 84, .10), (14, KICK, 84, .10)]
play(10, p, 0.002)

# bar 11: down the toms
run11 = [(TOM1, 104), (TOM1, 76), (TOM1, 72), (TOM2, 100), (TOM2, 80), (TOM2, 74),
         (TOM3, 100), (TOM3, 82), (TOM3, 78), (TOM4, 104), (TOM4, 84), (TOM4, 80),
         (FLR1, 108), (FLR1, 86), (FLR2, 106), (FLR2, 92)]
p = [(i, n, v, .07) for i, (n, v) in enumerate(run11)]
p += [(0, KICK, 106, .10), (4, KICK, 96, .10), (8, KICK, 100, .10), (12, KICK, 108, .10)]
play(11, p, 0.002)

# bar 12: and back up, landing on the snare
run12 = [(FLR2, 102), (FLR2, 80), (FLR1, 100), (FLR1, 80), (TOM4, 102), (TOM4, 82),
         (TOM3, 100), (TOM3, 82), (TOM2, 102), (TOM2, 84), (TOM1, 104), (TOM1, 86),
         (TOM1, 110), (TOM2, 90), (TOM2, 96), (SNARE, 116)]
p = [(i, n, v, .07) for i, (n, v) in enumerate(run12)]
p += [(0, KICK, 106, .10), (8, KICK, 104, .10), (15, KICK, 110, .10)]
play(12, p, 0.001)

# ======================================================================
#  IV.  THEME RETURN, full kit (bars 13-16)
# ======================================================================
play(13, [(0, CRASH1, 118, 1.6), (0, KICK, 118, .12), (0, SNARE, 112, .10),
          (3, SNARE, 44, .05), (6, SNARE, 104, .10), (10, SNARE, 110, .10), (14, SNARE, 48, .05),
          (8, KICK, 108, .12), (11, KICK, 78, .10),
          (4, HHP, 80, .12), (12, HHP, 78, .12)]
         + [(q, RIDE, 94 if q % 8 == 0 else 72, .08) for q in range(2, 16, 2)],
         0.003)

play(14, [(0, KICK, 116, .12), (0, SNARE, 114, .10),
          (3, SNARE, 44, .05), (6, SNARE, 106, .10), (10, SNARE, 112, .10),
          (12, TOM1, 110, .10), (13, TOM1, 66, .05), (14, TOM3, 106, .10), (15, FLR1, 104, .10),
          (8, KICK, 106, .12), (15, KICK, 96, .12),
          (4, HHP, 80, .12), (12, HHP, 78, .12)]
         + [(q, RIDE, 94 if q % 8 == 0 else 72, .08) for q in range(2, 11, 2)],
         0.003)

play(15, [(0, KICK, 116, .12), (0, SNARE, 116, .10),
          (3, SNARE, 46, .05), (6, SNARE, 108, .10), (10, SNARE, 114, .10), (14, SNARE, 50, .05),
          (7, SNARE, 40, .05), (13, SNARE, 42, .05),
          (8, KICK, 108, .12), (11, KICK, 80, .10),
          (4, HHP, 82, .12), (12, HHP, 80, .12)]
         + [(q, RIDE, 96 if q % 8 == 0 else 74, .08) for q in range(2, 16, 2)],
         0.002)

play(16, [(0, KICK, 112, .12), (0, SNARE, 110, .10), (4, SNARE, 100, .08),
          (2, SNARE, 56, .05), (3, SNARE, 60, .05), (6, SNARE, 62, .05), (7, SNARE, 68, .05),
          (8, TOM1, 104, .07), (9, TOM1, 76, .05), (10, TOM2, 100, .07), (11, TOM2, 78, .05),
          (12, TOM3, 106, .07), (13, TOM4, 88, .05), (14, FLR1, 112, .07), (15, FLR2, 100, .05),
          (8, KICK, 104, .12), (12, KICK, 106, .12)], 0.001)

# ======================================================================
#  V.  ROLLS THAT SWELL (bars 17-20)
# ======================================================================
add(tt(17, 0), CHINA, 120, 1.6)
add(tt(17, 0), KICK, 120, .12)
for i in range(32):                                   # two bar crescendo
    v = 34 + 60 * (i / 31.0) ** 1.7
    add(tt(17, i), SNARE, v, .07)
for b in (17, 18):
    add(tt(b, 0),  KICK, 72, .10)
    add(tt(b, 8),  KICK, 66, .10)
    add(tt(b, 4),  HHP,  62, .10)
    add(tt(b, 12), HHP,  60, .10)

# bar 19 -- buzz roll, still growing
for i in range(32):
    v = 94 + 26 * (i / 31.0)
    add(tt(19, i * 0.5), SNARE, v, .04)
add(tt(19, 0),  KICK,  92, .10)
add(tt(19, 8),  KICK,  98, .10)
add(tt(19, 12), KICK, 104, .10)

# bar 20 -- resolution
play(20, [(0, KICK, 118, .12), (0, TOM1, 118, .10),
          (2, TOM1, 80, .06), (3, TOM2, 96, .06), (4, TOM2, 110, .08),
          (6, TOM3, 84, .06), (7, TOM3, 96, .06), (8, TOM4, 114, .08),
          (10, FLR1, 88, .06), (11, FLR1, 98, .06), (12, FLR2, 116, .08),
          (14, FLR2, 96, .06), (15, SNARE, 120, .08),
          (4, KICK, 100, .10), (8, KICK, 104, .10), (12, KICK, 108, .10), (15, KICK, 116, .10)],
         -0.002)

# ======================================================================
#  VI.  GROOVE WITH BELL (bars 21-24) -- building again
# ======================================================================
play(21, [(0, CRASH1, 118, 1.6), (0, KICK, 118, .12), (0, SNARE, 112, .10),
          (4, SNARE, 112, .10), (12, SNARE, 116, .10),
          (3, SNARE, 42, .05), (11, SNARE, 44, .05), (14, SNARE, 48, .05),
          (7, KICK, 96, .12), (10, KICK, 92, .12),
          (4, HHP, 78, .12), (12, HHP, 76, .12)]
         + [(q, RIDE, 94 if q % 8 == 0 else 70, .08) for q in range(2, 16, 2)],
         -0.004)

play(22, [(0, KICK, 116, .12), (4, SNARE, 112, .10), (12, SNARE, 114, .10),
          (3, SNARE, 40, .05), (5, SNARE, 44, .05), (11, SNARE, 42, .05), (14, SNARE, 46, .05),
          (7, KICK, 98, .12), (10, KICK, 94, .12), (15, KICK, 88, .12),
          (4, HHP, 78, .12), (12, HHP, 76, .12)]
         + [(q, RIDE, 94 if q % 8 == 0 else 70, .08) for q in range(0, 16, 2)],
         -0.004)

play(23, [(0, KICK, 116, .12), (4, SNARE, 114, .10), (12, SNARE, 116, .10),
          (3, SNARE, 42, .05), (6, SNARE, 46, .05), (11, SNARE, 44, .05), (14, SNARE, 48, .05),
          (7, KICK, 100, .12), (10, KICK, 96, .12),
          (4, HHP, 80, .12), (12, HHP, 78, .12),
          (0, BELL, 104, .30), (8, BELL, 100, .30),
          (2, RIDE, 68, .08), (6, RIDE, 72, .08), (10, RIDE, 70, .08), (14, RIDE, 74, .08)],
         -0.005)

play(24, [(0, KICK, 110, .12), (0, RIDE, 92, .08), (2, RIDE, 70, .08),
          (4, SNARE, 108, .10), (5, SNARE, 60, .05), (6, SNARE, 64, .05), (7, SNARE, 70, .05),
          (8, TOM1, 100, .06), (9, TOM2, 96, .06), (10, TOM3, 100, .06), (11, TOM4, 92, .06),
          (12, FLR1, 96, .06), (13, FLR2, 92, .06), (14, FLR2, 88, .06), (15, FLR2, 76, .06),
          (8, KICK, 96, .10), (12, KICK, 100, .10)], 0.0)

# ======================================================================
#  VII.  BREATHE (bars 25-32) -- laid back, swung ride, space
# ======================================================================
def swing_bar(bar, feel, r0, r1, r2, kick0, kick1, extra=()):
    p = [(0, RIDE, r0, .10), (4, RIDE, r1, .10), (SW2, RIDE, r1 - 8, .10),
         (8, RIDE, r0 - 2, .10), (12, RIDE, r1, .10), (SW4, RIDE, r2, .10),
         (4, HHP, 70, .12), (12, HHP, 68, .12),
         (0, KICK, kick0, .10), (8, KICK, kick1, .10)]
    p += list(extra)
    play(bar, p, feel)

swing_bar(25, 0.020, 86, 74, 64, 54, 50,
          [(6, SNARE, 46, .05), (11, SNARE, 42, .05)])
swing_bar(26, 0.020, 86, 74, 64, 56, 52,
          [(7, SNARE, 84, .08), (9, SNARE, 40, .05), (14, KICK, 46, .10), (15, SNARE, 44, .05)])
swing_bar(27, 0.018, 88, 76, 66, 58, 54,
          [(2, SNARE, 80, .08), (5, SNARE, 44, .05), (10, SNARE, 86, .08), (13, SNARE, 42, .05)])
swing_bar(28, 0.018, 88, 76, 66, 60, 56,
          [(3, SNARE, 88, .08), (6, SNARE, 46, .05), (10, KICK, 58, .10),
           (11, SNARE, 92, .08), (14, SNARE, 48, .05)])

swing_bar(29, 0.016, 92, 80, 70, 66, 62,
          [(2, SNARE, 82, .08), (5, SNARE, 46, .05), (7, SNARE, 88, .08),
           (10, SNARE, 84, .08), (13, SNARE, 44, .05), (15, SNARE, 90, .08)])
swing_bar(30, 0.014, 94, 82, 72, 72, 68,
          [(3, SNARE, 46, .05), (6, SNARE, 88, .08), (10, SNARE, 48, .05),
           (11, KICK, 62, .10), (14, SNARE, 92, .08)])

# bar 31 -- the swing hands over to straight time
p  = [(0, RIDE, 94, .10), (4, RIDE, 84, .10), (4, HHP, 76, .12),
      (0, KICK, 78, .10), (6, SNARE, 92, .08), (7, KICK, 72, .10)]
for i, (n, v) in enumerate([(TOM1, 98), (TOM1, 80), (TOM2, 100), (TOM2, 82),
                            (TOM3, 102), (TOM4, 92), (FLR1, 106), (FLR2, 98)]):
    p.append((8 + i, n, v, .06))
play(31, p, 0.010)

# bar 32 -- build out of the quiet
p  = [(0, KICK, 96, .10), (4, KICK, 88, .10), (8, KICK, 100, .10), (12, KICK, 110, .10)]
seq = [(SNARE, 76), (SNARE, 80), (SNARE, 84), (SNARE, 88),
       (TOM1, 92), (TOM1, 94), (TOM2, 96), (TOM2, 98),
       (TOM3, 100), (TOM3, 102), (TOM4, 104), (TOM4, 106),
       (FLR1, 110), (FLR1, 112), (FLR2, 116), (SNARE, 120)]
for i, (n, v) in enumerate(seq):
    p.append((i, n, v, .06))
play(32, p, 0.004)

# ======================================================================
#  VIII.  TRIPLET BUILD (bars 33-36)
# ======================================================================
# bar 33 -- eighth note triplets on the snare
p = [(0, CRASH1, 120, 1.6), (0, KICK, 120, .12), (8, KICK, 106, .12)]
for i in range(12):
    v = 74 + 26 * (i / 11.0)
    p.append((i * (4.0 / 3.0), SNARE, v + (18 if i % 3 == 0 else 0), .07))
play(33, p, -0.002)

# bar 34 -- triplets down the toms
p = []
toms = [TOM1, TOM1, TOM1, TOM2, TOM2, TOM2, TOM3, TOM3, TOM3, FLR1, FLR1, FLR2]
for i in range(12):
    p.append((i * (4.0 / 3.0), toms[i], 92 if i % 3 == 0 else 76, .07))
p += [(0, KICK, 110, .12), (4, KICK, 100, .12), (8, KICK, 106, .12), (12, KICK, 112, .12)]
play(34, p, -0.003)

# bar 35 -- triplets back up
p = []
toms = [FLR2, FLR2, FLR1, FLR1, TOM4, TOM4, TOM3, TOM3, TOM2, TOM2, TOM1, SNARE]
for i in range(12):
    p.append((i * (4.0 / 3.0), toms[i], 96 if i % 3 == 0 else 78, .07))
p += [(0, KICK, 110, .12), (8, KICK, 108, .12)]
play(35, p, -0.004)

# bar 36 -- sixteenth triplets, crescendo into the theme
p = []
toms = [TOM1, TOM1, TOM2, TOM2, TOM3, TOM3, TOM4, TOM4, FLR1, FLR1, FLR2, FLR2]
for i in range(24):
    v = 96 + 24 * (i / 23.0) + (10 if i % 6 == 0 else 0)
    p.append((i * (2.0 / 3.0), toms[i // 2], v, .05))
p += [(0, KICK, 108, .10), (4, KICK, 104, .10), (8, KICK, 108, .10), (12, KICK, 114, .10)]
play(36, p, -0.006)

# ======================================================================
#  IX.  THEME AT FULL VOICE (bars 37-40)
# ======================================================================
play(37, [(0, CRASH1, 122, 1.6), (0, KICK, 122, .12), (0, SNARE, 118, .10),
          (3, SNARE, 48, .05), (6, SNARE, 110, .10), (10, SNARE, 116, .10), (14, SNARE, 52, .05),
          (8, KICK, 112, .12), (11, KICK, 82, .10),
          (4, HHP, 84, .12), (12, HHP, 82, .12)]
         + [(q, RIDE, 98 if q % 8 == 0 else 76, .08) for q in range(2, 16, 2)],
         -0.006)

play(38, [(0, KICK, 118, .12), (0, SNARE, 116, .10),
          (3, SNARE, 46, .05), (6, SNARE, 108, .10), (10, SNARE, 114, .10),
          (12, TOM1, 112, .10), (13, TOM1, 70, .05), (14, TOM3, 108, .10), (15, FLR1, 106, .10),
          (8, KICK, 110, .12), (15, KICK, 100, .12),
          (4, HHP, 84, .12), (12, HHP, 82, .12)]
         + [(q, RIDE, 98 if q % 8 == 0 else 76, .08) for q in range(2, 11, 2)],
         -0.006)

play(39, [(0, KICK, 118, .12), (0, SNARE, 118, .10),
          (3, SNARE, 48, .05), (5, SNARE, 40, .05), (6, SNARE, 112, .10),
          (10, SNARE, 118, .10), (13, SNARE, 44, .05), (14, SNARE, 54, .05),
          (7, SNARE, 42, .05),
          (8, KICK, 112, .12), (11, KICK, 84, .10),
          (4, HHP, 84, .12), (12, HHP, 82, .12)]
         + [(q, RIDE, 100 if q % 8 == 0 else 78, .08) for q in range(2, 16, 2)],
         -0.007)

play(40, [(0, KICK, 116, .12), (0, SNARE, 114, .10), (2, SNARE, 60, .05), (3, SNARE, 66, .05),
          (4, SNARE, 112, .10), (6, SNARE, 68, .05), (7, SNARE, 74, .05),
          (8, TOM1, 108, .07), (9, TOM1, 80, .05), (10, TOM2, 104, .07), (11, TOM2, 82, .05),
          (12, TOM3, 110, .07), (13, TOM4, 92, .05), (14, FLR1, 116, .07), (15, FLR2, 104, .05),
          (8, KICK, 108, .12), (12, KICK, 112, .12)], -0.008)

# ======================================================================
#  X.  PEAK SINGLES (bars 41-44) -- pushed ahead
# ======================================================================
p = []
for q in range(16):
    p.append((q, SNARE, 116 if q in (0, 3, 6, 10, 14) else (78 if q % 2 == 0 else 70), .06))
p += [(0, KICK, 114, .10), (8, KICK, 112, .10), (11, KICK, 90, .10)]
play(41, p, -0.010)

toms = [SNARE, SNARE, TOM1, TOM1, TOM2, TOM2, TOM3, TOM3,
        TOM4, TOM4, FLR1, FLR1, FLR2, FLR2, FLR2, FLR2]
p = [(i, n, 114 if i % 4 == 0 else 84, .06) for i, n in enumerate(toms)]
p += [(0, KICK, 110, .10), (4, KICK, 106, .10), (8, KICK, 110, .10), (12, KICK, 114, .10)]
play(42, p, -0.011)

toms = [TOM2, TOM2, TOM1, TOM1, SNARE, SNARE, TOM1, TOM1,
        TOM2, TOM2, TOM3, TOM3, TOM4, TOM4, FLR1, FLR2]
p = [(i, n, 116 if i % 4 == 0 else 86, .06) for i, n in enumerate(toms)]
p += [(0, KICK, 112, .10), (8, KICK, 114, .10)]
play(43, p, -0.012)

p = []
seq = [(SNARE, 100), (SNARE, 104), (SNARE, 108), (SNARE, 112),
       (TOM1, 114), (TOM1, 116), (TOM2, 116), (TOM2, 118),
       (TOM3, 118), (TOM3, 118), (TOM4, 118), (TOM4, 120),
       (FLR1, 120), (FLR1, 122), (FLR2, 122), (SNARE, 124)]
p += [(i, n, v, .06) for i, (n, v) in enumerate(seq)]
p += [(0, KICK, 112, .10), (4, KICK, 110, .10), (8, KICK, 114, .10),
      (12, KICK, 120, .10), (15, KICK, 122, .10), (15, SPLASH, 110, .80)]
play(44, p, -0.012)

# ======================================================================
#  XI.  DRIVING (bars 45-48)
# ======================================================================
play(45, [(0, CRASH1, 122, 1.6), (0, KICK, 122, .12), (0, SNARE, 116, .10),
          (4, SNARE, 116, .10), (12, SNARE, 120, .10),
          (3, SNARE, 48, .05), (11, SNARE, 50, .05), (14, SNARE, 54, .05),
          (7, KICK, 104, .12), (10, KICK, 100, .12),
          (4, HHP, 84, .12), (12, HHP, 82, .12)]
         + [(q, RIDE, 100 if q % 8 == 0 else 78, .08) for q in range(2, 16, 2)],
         -0.010)

play(46, [(0, KICK, 120, .12), (4, SNARE, 116, .10), (12, SNARE, 118, .10),
          (3, SNARE, 46, .05), (5, SNARE, 50, .05), (11, SNARE, 48, .05), (14, SNARE, 52, .05),
          (7, KICK, 106, .12), (10, KICK, 102, .12), (15, KICK, 96, .12),
          (4, HHP, 84, .12), (12, HHP, 82, .12),
          (14, HHO, 96, .18)]
         + [(q, RIDE, 100 if q % 8 == 0 else 78, .08) for q in range(0, 14, 2)],
         -0.010)

play(47, [(0, CRASH2, 118, 1.6), (8, CRASH1, 112, 1.2),
          (0, KICK, 120, .12), (4, SNARE, 118, .10), (12, SNARE, 120, .10),
          (3, SNARE, 48, .05), (11, SNARE, 50, .05),
          (7, KICK, 106, .12), (10, KICK, 104, .12),
          (4, HHP, 84, .12), (12, HHP, 82, .12)]
         + [(q, RIDE, 100 if q % 8 == 0 else 78, .08) for q in (2, 6, 10, 14)],
         -0.012)

play(48, [(0, KICK, 116, .12), (0, SNARE, 116, .10), (4, SNARE, 112, .10),
          (2, SNARE, 62, .05), (3, SNARE, 68, .05), (6, SNARE, 70, .05), (7, SNARE, 76, .05),
          (8, TOM1, 110, .07), (9, TOM1, 84, .05), (10, TOM2, 106, .07), (11, TOM2, 86, .05),
          (12, TOM3, 112, .07), (13, TOM4, 96, .05), (14, FLR1, 118, .07), (15, FLR2, 108, .05),
          (8, KICK, 110, .12), (12, KICK, 114, .12)], -0.012)

# ======================================================================
#  XII.  CALL AND ANSWER (bars 49-52) -- cowbell colours the gaps
# ======================================================================
play(49, [(0, CRASH1, 118, 1.6), (0, KICK, 120, .12), (0, SNARE, 118, .10),
          (3, SNARE, 108, .08), (6, SNARE, 112, .08), (6, KICK, 110, .12),
          (10, SNARE, 100, .08), (10, KICK, 112, .12),
          (12, COWBELL, 96, .10), (14, COWBELL, 98, .10),
          (15, SNARE, 116, .08), (15, KICK, 118, .12)], -0.008)

p = []
toms = [SNARE, SNARE, TOM1, TOM1, TOM2, TOM2, TOM3, TOM3,
        TOM3, TOM4, TOM4, FLR1, FLR1, FLR2, FLR2, FLR2]
p += [(i, n, 112 if i % 4 == 0 else 84, .06) for i, n in enumerate(toms)]
p += [(0, KICK, 112, .10), (8, KICK, 110, .10), (12, KICK, 114, .10)]
play(50, p, -0.008)

play(51, [(0, KICK, 120, .12), (0, SNARE, 118, .10),
          (3, COWBELL, 98, .10), (6, COWBELL, 96, .10),
          (8, SNARE, 112, .08), (8, KICK, 114, .12),
          (10, COWBELL, 100, .10), (12, COWBELL, 98, .10),
          (14, SNARE, 116, .08), (15, SNARE, 120, .08), (15, KICK, 120, .12)], -0.008)

p = []
seq = [(SNARE, 88), (SNARE, 92), (SNARE, 96), (SNARE, 100),
       (TOM1, 104), (TOM1, 106), (TOM2, 108), (TOM2, 110),
       (TOM3, 112), (TOM3, 114), (TOM4, 116), (TOM4, 118),
       (FLR1, 120), (FLR1, 122), (FLR2, 124), (SNARE, 126)]
p += [(i, n, v, .06) for i, (n, v) in enumerate(seq)]
p += [(0, KICK, 112, .10), (4, KICK, 110, .10), (8, KICK, 114, .10), (12, KICK, 120, .10)]
play(52, p, -0.006)

# ======================================================================
#  XIII.  THE LONG BUILD (bars 53-56)
# ======================================================================
play(53, [(0, CRASH1, 122, 1.6), (0, KICK, 122, .12), (0, SNARE, 116, .10),
          (4, SNARE, 116, .10), (12, SNARE, 120, .10),
          (3, SNARE, 50, .05), (11, SNARE, 52, .05),
          (7, KICK, 108, .12), (10, KICK, 104, .12),
          (4, HHP, 84, .12), (12, HHP, 82, .12)]
         + [(q, RIDE, 102 if q % 8 == 0 else 80, .08) for q in range(2, 16, 2)],
         -0.006)

p = [(i, SNARE, 58 + 34 * (i / 15.0), .06) for i in range(16)]
p += [(0, KICK, 112, .10), (8, KICK, 108, .10), (4, HHP, 70, .10), (12, HHP, 68, .10)]
play(54, p, -0.006)

p = [(i, SNARE, 90 + 24 * (i / 15.0), .06) for i in range(16)]
p += [(0, KICK, 116, .10), (4, KICK, 110, .10), (8, KICK, 116, .10), (12, KICK, 120, .10)]
play(55, p, -0.006)

p = [(i * 0.5, SNARE, 104 + 22 * (i / 31.0), .04) for i in range(32)]
p += [(0, KICK, 118, .10), (8, KICK, 116, .10), (12, KICK, 120, .10), (14, KICK, 122, .10)]
play(56, p, -0.005)

# ======================================================================
#  XIV.  FINALE (bars 57-60) -- and land it
# ======================================================================
p = []
seq = [(SNARE, 118), (SNARE, 92), (SNARE, 88), (SNARE, 96),
       (TOM1, 120), (TOM1, 92), (TOM1, 88), (TOM1, 96),
       (TOM2, 118), (TOM2, 90), (TOM2, 88), (TOM2, 96),
       (TOM3, 120), (TOM3, 92), (TOM3, 90), (TOM3, 98)]
p += [(i, n, v, .06) for i, (n, v) in enumerate(seq)]
p += [(0, KICK, 118, .10), (8, KICK, 116, .10), (12, KICK, 120, .10)]
play(57, p, -0.004)

p = []
seq = [(TOM4, 118), (TOM4, 92), (TOM4, 90), (TOM4, 98),
       (FLR1, 120), (FLR1, 94), (FLR1, 92), (FLR1, 100),
       (TOM3, 118), (TOM3, 94), (TOM2, 116), (TOM2, 94),
       (TOM1, 120), (TOM1, 96), (SNARE, 122), (SNARE, 108)]
p += [(i, n, v, .06) for i, (n, v) in enumerate(seq)]
p += [(0, KICK, 118, .10), (8, KICK, 118, .10), (12, KICK, 122, .10)]
play(58, p, -0.004)

p = [(i * 0.5, SNARE, 100 + 28 * (i / 31.0), .04) for i in range(32)]
p += [(8, KICK, 120, .10), (12, KICK, 122, .10), (14, KICK, 124, .10)]
play(59, p, -0.003)

# bar 60 -- the last downbeat, two hands and two feet, then ring out
add(tt(60, 0), CRASH1, 127, 2.0)
add(tt(60, 0), KICK,   127, .20)
add(tt(60, 0), SNARE,  124, .12)
add(tt(60, 0), HHP,     90, .20)


# ======================================================================
#  Write the file
# ======================================================================
def build_midi():
    ons = []
    for t, note, vel, dur in events:
        on  = int(round(t * TPS))
        off = int(round((t + dur) * TPS))
        if off <= on:
            off = on + 1
        ons.append([on, note, vel, off])

    ons.sort(key=lambda e: (e[0], e[1]))

    # one strike at a time per drum head / cymbal
    seen = {}
    for e in ons:
        key = (e[0], e[1])
        if key in seen:
            if e[2] > seen[key][2]:
                seen[key][2] = e[2]
            if e[3] > seen[key][3]:
                seen[key][3] = e[3]
        else:
            seen[key] = e
    ons = list(seen.values())
    ons.sort(key=lambda e: (e[0], e[1]))

    # a note may never ring past its own next stroke
    by_pitch = {}
    for e in ons:
        by_pitch.setdefault(e[1], []).append(e)
    for lst in by_pitch.values():
        lst.sort(key=lambda e: e[0])
        for i in range(len(lst) - 1):
            if lst[i][3] > lst[i + 1][0] and lst[i + 1][0] > lst[i][0]:
                lst[i][3] = lst[i + 1][0]
        if lst[-1][3] <= lst[-1][0]:
            lst[-1][3] = lst[-1][0] + 1

    msgs = []
    for on, note, vel, off in ons:
        msgs.append((on, 1, note,
                     Message('note_on', channel=CH, note=note, velocity=vel)))
        msgs.append((off, 0, note,
                     Message('note_off', channel=CH, note=note, velocity=0)))
    msgs.sort(key=lambda x: (x[0], x[1], x[2]))

    track = MidiTrack()
    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('set_tempo', tempo=TEMPO, time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))

    last = 0
    for tick, _order, _note, msg in msgs:
        msg.time = tick - last
        track.append(msg)
        last = tick
    track.append(MetaMessage('end_of_track', time=0))

    mid = MidiFile(type=0, ticks_per_beat=PPQ)
    mid.tracks.append(track)
    mid.save('solo.mid')


if __name__ == '__main__':
    build_midi()
