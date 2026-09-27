#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid: a two minute General MIDI drum solo.

The solo lives on MIDI channel 10 (GM percussion).  It is built from a few
rhythmic motifs that get stated, displaced, orchestrated around the kit,
stretched (augmentation), compressed (diminution) and finally brought back
quietly before the last hit.  Everything is humanised: phrase level push
and drag, micro timing scatter, a touch of sixteenth swing, ghost notes
against accents, and velocity shaping inside each phrase.  The result is
also kept playable: never more than two hands or two feet at one instant.

Only mido is used.  The output is byte-for-byte identical on every run.
"""

import bisect
import random

import mido

# ----------------------------------------------------------------------
#  constants
# ----------------------------------------------------------------------
PPQ = 960                     # ticks per quarter note
CHANNEL = 9                   # zero based -> MIDI channel 10 (GM drums)
BARS = 60                     # 4/4

# General MIDI percussion key map
KICK, KICK2 = 36, 35
STICK, SNARE, SNARE2 = 37, 38, 40
HH, HH_PEDAL, HH_OPEN = 42, 44, 46
TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL = 50, 48, 47, 45, 43, 41
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
RIDE, RIDE_BELL, RIDE2 = 51, 53, 59
COWBELL, TAMB, CLAP = 56, 54, 39
WOOD_HI, WOOD_LO = 76, 77

FOOT_NOTES = frozenset((KICK, KICK2, HH_PEDAL))
LONG_NOTES = frozenset((CRASH, CRASH2, SPLASH, CHINA,
                        RIDE, RIDE_BELL, RIDE2, HH_OPEN, HH_PEDAL))


def beat_of(bar, step):
    """Absolute beat position of a sixteenth-note step inside a 1-based bar."""
    return (bar - 1) * 4.0 + step / 4.0


# ----------------------------------------------------------------------
#  the performance buffer
# ----------------------------------------------------------------------
class Solo:
    """Collects humanised hits and keeps the result playable by one drummer."""

    def __init__(self, seed=20240517):
        self.rng = random.Random(seed)
        self.notes = []          # (tick, note, velocity)
        self.hand_ticks = []     # sorted ticks of hand strokes
        self.foot_ticks = []     # sorted ticks of foot strokes
        self.used = set()        # (tick, note) already scheduled
        self.push = 0.0          # phrase offset in ticks (+ = laid back)
        self.jitter = 6.0        # random timing scatter in ticks
        self.swing = 0.0         # sixteenth-note swing in ticks
        self.vel_jitter = 5.0

    # -- placement -----------------------------------------------------
    def hit(self, beat, note, vel, kind=None, extra=0.0, human=1.0):
        if vel <= 0:
            return
        if kind is None:
            kind = 'foot' if note in FOOT_NOTES else 'hand'

        pos16 = beat * 4.0
        off = self.push + extra
        if abs(pos16 - round(pos16)) < 0.02 and int(round(pos16)) % 2:
            off += self.swing
        off += self.rng.uniform(-self.jitter, self.jitter)

        tick = int(round(beat * PPQ + off))
        if tick < 0:
            tick = 0

        vel = int(round(vel + self.rng.uniform(-self.vel_jitter,
                                               self.vel_jitter) * human))
        vel = max(1, min(127, vel))

        # nudge (or, very rarely, drop) anything that would need three hands
        for attempt in range(5):
            t = tick + 5 * attempt
            if self._fits(t, note, kind):
                self._add(t, note, vel, kind)
                return

    def _fits(self, tick, note, kind):
        arr = self.hand_ticks if kind == 'hand' else self.foot_ticks
        i = bisect.bisect_left(arr, tick - 14)
        n = 0
        while i < len(arr) and arr[i] <= tick + 14:
            n += 1
            i += 1
        if n >= 2:                       # never a third hand / foot
            return False
        for d in range(-6, 7):           # never the same drum twice at once
            if (tick + d, note) in self.used:
                return False
        return True

    def _add(self, tick, note, vel, kind):
        bisect.insort(self.hand_ticks if kind == 'hand' else self.foot_ticks,
                      tick)
        self.used.add((tick, note))
        self.notes.append((tick, note, vel))


# ----------------------------------------------------------------------
#  motifs -- (sixteenth offset, is-accent)
# ----------------------------------------------------------------------
MOTIF_A = ((0, 1), (1, 0), (2, 0), (3, 1), (5, 0), (6, 1), (7, 0))
MOTIF_A2 = ((0, 1), (1, 0), (3, 1), (4, 0), (6, 1), (7, 0))
MOTIF_A3 = ((0, 1), (2, 0), (3, 1), (5, 0), (6, 1), (7, 1))


def play_cell(P, bar, start, cell, notes, accent, ghost, human=1.0):
    """Play a motif cell; `notes` may be a single drum or a list to cycle."""
    if not isinstance(notes, (list, tuple)):
        notes = (notes,)
    for i, (step, is_acc) in enumerate(cell):
        P.hit(beat_of(bar, start + step), notes[i % len(notes)],
              accent if is_acc else ghost, human=human)


# ----------------------------------------------------------------------
#  1. bars 1-8 : the pulse, then MOTIF A, stated plainly
# ----------------------------------------------------------------------
def part_statement(P):
    P.push, P.jitter, P.swing = -3.0, 6.0, 0.0

    # bar 1 -- hats, backbeat, two kicks.  Nothing else.
    for s in (0, 4, 8, 12):
        P.hit(beat_of(1, s), HH, 64 if s == 0 else 57)
    P.hit(beat_of(1, 0), KICK, 104, 'foot')
    P.hit(beat_of(1, 10), KICK, 74, 'foot')
    P.hit(beat_of(1, 4), SNARE, 86, extra=7)
    P.hit(beat_of(1, 12), SNARE, 92, extra=7)

    # bar 2 -- ghosts creep into the backbeat
    for s in (0, 4, 8, 12):
        P.hit(beat_of(2, s), HH, 58)
    P.hit(beat_of(2, 0), KICK, 106, 'foot')
    P.hit(beat_of(2, 10), KICK, 76, 'foot')
    P.hit(beat_of(2, 4), SNARE, 88, extra=7)
    P.hit(beat_of(2, 12), SNARE, 94, extra=7)
    P.hit(beat_of(2, 6), SNARE, 33)
    P.hit(beat_of(2, 15), SNARE, 40)

    # bar 3 -- MOTIF A, first statement
    P.hit(beat_of(3, 0), KICK, 102, 'foot')
    P.hit(beat_of(3, 11), KICK, 70, 'foot')
    P.hit(beat_of(3, 4), HH_PEDAL, 70, 'foot')
    P.hit(beat_of(3, 12), HH_PEDAL, 70, 'foot')
    play_cell(P, 3, 0, MOTIF_A, SNARE, 106, 40)
    P.hit(beat_of(3, 8), SNARE, 100)
    P.hit(beat_of(3, 10), SNARE, 34)
    P.hit(beat_of(3, 11), SNARE, 92)
    P.hit(beat_of(3, 14), SNARE, 38)

    # bar 4 -- the answer, same shape, now on the toms
    P.hit(beat_of(4, 0), KICK, 104, 'foot')
    P.hit(beat_of(4, 9), KICK, 72, 'foot')
    P.hit(beat_of(4, 4), HH_PEDAL, 70, 'foot')
    P.hit(beat_of(4, 12), HH_PEDAL, 70, 'foot')
    play_cell(P, 4, 0, MOTIF_A, SNARE, 110, 42)
    play_cell(P, 4, 8, MOTIF_A2,
              [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL], 104, 58)

    # bar 5 -- the motif displaced, then a shorter variant of itself
    P.hit(beat_of(5, 0), KICK, 106, 'foot')
    P.hit(beat_of(5, 6), KICK, 80, 'foot')
    P.hit(beat_of(5, 11), KICK, 72, 'foot')
    P.hit(beat_of(5, 4), HH_PEDAL, 72, 'foot')
    P.hit(beat_of(5, 12), HH_PEDAL, 72, 'foot')
    play_cell(P, 5, 0, MOTIF_A, SNARE, 110, 42)
    play_cell(P, 5, 8, MOTIF_A3, SNARE, 102, 34)

    # bar 6 -- the motif travels over the toms
    P.hit(beat_of(6, 0), KICK, 108, 'foot')
    P.hit(beat_of(6, 7), KICK, 78, 'foot')
    P.hit(beat_of(6, 10), KICK, 72, 'foot')
    P.hit(beat_of(6, 4), HH_PEDAL, 72, 'foot')
    P.hit(beat_of(6, 12), HH_PEDAL, 72, 'foot')
    play_cell(P, 6, 0, MOTIF_A,
              [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_M, TOM_M, TOM_LM], 108, 60)
    play_cell(P, 6, 8, MOTIF_A3,
              [TOM_LM, TOM_L, TOM_L, TOM_LL, TOM_LL, TOM_L], 102, 54)

    # bar 7 -- eighth notes, all uphill
    walk = [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L]
    for i, s in enumerate((0, 2, 4, 6, 8, 10, 12, 14)):
        P.hit(beat_of(7, s), walk[i], 60 + i * 5.5)
    P.hit(beat_of(7, 0), KICK, 108, 'foot')
    P.hit(beat_of(7, 8), KICK, 92, 'foot')
    P.hit(beat_of(7, 14), KICK, 84, 'foot')

    # bar 8 -- sixteenths, and it is all uphill
    run = [SNARE] * 8 + [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL,
                         SNARE, SNARE]
    for i in range(16):
        P.hit(beat_of(8, i), run[i], 74 + i * 2.9)
    P.hit(beat_of(8, 0), KICK, 112, 'foot')
    P.hit(beat_of(8, 6), KICK, 86, 'foot')
    P.hit(beat_of(8, 12), KICK, 98, 'foot')


# ----------------------------------------------------------------------
#  2. bars 9-16 : the crash lands, the motif starts to move
# ----------------------------------------------------------------------
def part_develop(P):
    P.push, P.jitter, P.swing = 0.0, 6.0, 0.0

    # bar 9 -- crash on the downbeat, then straight time
    P.hit(beat_of(9, 0), CRASH, 122)
    P.hit(beat_of(9, 0), KICK, 114, 'foot')
    for s in (2, 4, 6, 8, 10, 12, 14):
        P.hit(beat_of(9, s), HH, 66 if s % 4 == 0 else 56)
    P.hit(beat_of(9, 4), SNARE, 96, extra=7)
    P.hit(beat_of(9, 12), SNARE, 100, extra=7)
    P.hit(beat_of(9, 6), KICK, 80, 'foot')
    P.hit(beat_of(9, 10), KICK, 78, 'foot')
    P.hit(beat_of(9, 7), SNARE, 36)
    P.hit(beat_of(9, 15), SNARE, 44)

    # bar 10 -- MOTIF A, doubled by the kick
    P.hit(beat_of(10, 0), KICK, 108, 'foot')
    P.hit(beat_of(10, 3), KICK, 82, 'foot')
    P.hit(beat_of(10, 6), KICK, 88, 'foot')
    P.hit(beat_of(10, 4), HH_PEDAL, 72, 'foot')
    P.hit(beat_of(10, 12), HH_PEDAL, 72, 'foot')
    play_cell(P, 10, 0, MOTIF_A, SNARE, 110, 40)
    P.hit(beat_of(10, 8), SNARE, 104)
    P.hit(beat_of(10, 10), SNARE, 36)
    P.hit(beat_of(10, 11), SNARE, 96)
    P.hit(beat_of(10, 13), SNARE, 32)
    P.hit(beat_of(10, 14), SNARE, 88)

    # bar 11 -- the motif splits between snare and toms
    P.hit(beat_of(11, 0), KICK, 108, 'foot')
    P.hit(beat_of(11, 6), KICK, 86, 'foot')
    P.hit(beat_of(11, 10), KICK, 78, 'foot')
    P.hit(beat_of(11, 4), HH_PEDAL, 72, 'foot')
    P.hit(beat_of(11, 12), HH_PEDAL, 72, 'foot')
    play_cell(P, 11, 0, MOTIF_A, SNARE, 110, 42)
    play_cell(P, 11, 8, MOTIF_A2,
              [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL], 106, 60)

    # bar 12 -- sixteenths down the toms, into the next phrase
    run = [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_M, TOM_M,
           TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_LL, TOM_LL, SNARE, TOM_L]
    for i in range(16):
        P.hit(beat_of(12, i), run[i], 76 + i * 2.6)
    P.hit(beat_of(12, 0), KICK, 112, 'foot')
    P.hit(beat_of(12, 8), KICK, 96, 'foot')
    P.hit(beat_of(12, 14), KICK, 104, 'foot')

    # bar 13 -- pocket, but heavier, with an open hat to lean on
    for s in (0, 2, 4, 6, 8, 10, 12, 14):
        P.hit(beat_of(13, s), HH_OPEN if s == 10 else HH,
              68 if s % 4 == 0 else 56)
    P.hit(beat_of(13, 0), KICK, 112, 'foot')
    P.hit(beat_of(13, 4), SNARE, 100, extra=7)
    P.hit(beat_of(13, 12), SNARE, 104, extra=7)
    P.hit(beat_of(13, 7), KICK, 84, 'foot')
    P.hit(beat_of(13, 6), SNARE, 38)
    P.hit(beat_of(13, 11), SNARE, 30)
    P.hit(beat_of(13, 14), SNARE, 44)

    # bar 14 -- motif, then double strokes that swell
    P.hit(beat_of(14, 0), KICK, 110, 'foot')
    P.hit(beat_of(14, 4), HH_PEDAL, 72, 'foot')
    P.hit(beat_of(14, 6), KICK, 88, 'foot')
    P.hit(beat_of(14, 10), HH_PEDAL, 72, 'foot')
    play_cell(P, 14, 0, MOTIF_A, SNARE, 112, 44)
    for i in range(8):
        s = 8 + i
        v = 64 + i * 5.5 - (9 if i % 2 else 0)
        P.hit(beat_of(14, s), SNARE if i < 6 else TOM_H, v)

    # bar 15 -- the toms take over
    P.hit(beat_of(15, 0), KICK, 110, 'foot')
    P.hit(beat_of(15, 0), TOM_L, 106)
    P.hit(beat_of(15, 2), TOM_M, 92)
    P.hit(beat_of(15, 3), TOM_HM, 88)
    P.hit(beat_of(15, 6), KICK, 86, 'foot')
    P.hit(beat_of(15, 6), TOM_H, 98)
    P.hit(beat_of(15, 8), TOM_HM, 88)
    P.hit(beat_of(15, 10), TOM_M, 100)
    P.hit(beat_of(15, 11), TOM_LM, 82)
    P.hit(beat_of(15, 12), KICK, 92, 'foot')
    P.hit(beat_of(15, 14), HH_PEDAL, 70, 'foot')
    P.hit(beat_of(15, 14), TOM_L, 100)

    # bar 16 -- crescendo: sixteenths into thirty-seconds
    for i in range(8):
        P.hit(beat_of(16, i), SNARE if i < 4 else TOM_H, 82 + i * 3.0)
    seq = [TOM_HM, TOM_M, TOM_M, TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_LL]
    for i in range(16):
        P.hit(beat_of(16, 8 + i * 0.5), seq[i % 8], 96 + i * 1.5)
    P.hit(beat_of(16, 0), KICK, 112, 'foot')
    P.hit(beat_of(16, 8), KICK, 100, 'foot')


# ----------------------------------------------------------------------
#  3. bars 17-28 : the pocket, with the motif poking its head out
# ----------------------------------------------------------------------
def part_pocket(P):
    P.push, P.jitter, P.swing = 0.0, 6.5, 9.0

    # bar 17 -- crash, then the deepest groove of the solo
    P.hit(beat_of(17, 0), CRASH, 124)
    P.hit(beat_of(17, 0), KICK, 114, 'foot')
    for s in (2, 4, 6, 8, 10, 12, 14):
        P.hit(beat_of(17, s), HH, 66 if s % 4 == 0 else 56)
    P.hit(beat_of(17, 4), SNARE, 100, extra=8)
    P.hit(beat_of(17, 12), SNARE, 104, extra=8)
    P.hit(beat_of(17, 7), SNARE, 36)
    P.hit(beat_of(17, 10), KICK, 84, 'foot')
    P.hit(beat_of(17, 15), SNARE, 42)

    # bar 18
    for s in (0, 2, 4, 6, 8, 10, 12, 14):
        P.hit(beat_of(18, s), HH, 64 if s % 4 == 0 else 54)
    P.hit(beat_of(18, 0), KICK, 110, 'foot')
    P.hit(beat_of(18, 3), KICK, 78, 'foot')
    P.hit(beat_of(18, 10), KICK, 86, 'foot')
    P.hit(beat_of(18, 4), SNARE, 98, extra=8)
    P.hit(beat_of(18, 12), SNARE, 102, extra=8)
    P.hit(beat_of(18, 6), SNARE, 34)
    P.hit(beat_of(18, 11), SNARE, 30)
    P.hit(beat_of(18, 14), SNARE, 40)

    # bar 19 -- MOTIF A again, dressed in ghosts
    P.hit(beat_of(19, 0), KICK, 108, 'foot')
    P.hit(beat_of(19, 4), HH_PEDAL, 74, 'foot')
    P.hit(beat_of(19, 6), KICK, 86, 'foot')
    P.hit(beat_of(19, 12), HH_PEDAL, 74, 'foot')
    play_cell(P, 19, 0, MOTIF_A, SNARE, 112, 42)
    P.hit(beat_of(19, 10), SNARE, 36)
    P.hit(beat_of(19, 11), SNARE, 98)
    P.hit(beat_of(19, 12), SNARE, 106, extra=8)
    P.hit(beat_of(19, 14), SNARE, 40)

    # bar 20 -- fill that carries into the ride
    fill = [(0, SNARE, 88), (2, SNARE, 94), (3, SNARE, 78), (4, SNARE, 102),
            (6, TOM_H, 96), (7, TOM_HM, 88), (8, TOM_M, 100),
            (10, TOM_LM, 92), (11, TOM_L, 88), (12, TOM_LL, 106),
            (14, SNARE, 108), (15, SNARE, 96)]
    for s, n, v in fill:
        P.hit(beat_of(20, s), n, v)
    P.hit(beat_of(20, 0), KICK, 112, 'foot')
    P.hit(beat_of(20, 8), KICK, 96, 'foot')
    P.hit(beat_of(20, 14), KICK, 100, 'foot')

    # bars 21-22 -- ride cymbal, the solo starts to sing
    for b in (21, 22):
        for s in (0, 2, 4, 6, 8, 10, 12, 14):
            note = RIDE_BELL if s in (0, 8) else RIDE
            P.hit(beat_of(b, s), note, 78 if s in (0, 8) else 58)
        P.hit(beat_of(b, 0), KICK, 110, 'foot')
        P.hit(beat_of(b, 3), KICK, 82, 'foot')
        P.hit(beat_of(b, 10), KICK, 88, 'foot')
        P.hit(beat_of(b, 4), SNARE, 100, extra=8)
        P.hit(beat_of(b, 12), SNARE, 104, extra=8)
        P.hit(beat_of(b, 7), SNARE, 36)
        P.hit(beat_of(b, 15), SNARE, 42)
    P.hit(beat_of(22, 11), COWBELL, 74)          # a little colour

    # bar 23 -- the motif comes back, an octave up the kit
    for s in (0, 2, 4, 6):
        P.hit(beat_of(23, s), RIDE, 58)
    P.hit(beat_of(23, 0), KICK, 108, 'foot')
    P.hit(beat_of(23, 4), SNARE, 102, extra=8)
    P.hit(beat_of(23, 6), KICK, 84, 'foot')
    play_cell(P, 23, 8, MOTIF_A2,
              [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL], 104, 60)
    P.hit(beat_of(23, 12), KICK, 90, 'foot')

    # bar 24 -- build out of the toms
    seq = [SNARE, SNARE, SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM,
           TOM_M, TOM_M, TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_LL, TOM_LL]
    for i in range(16):
        P.hit(beat_of(24, i), seq[i], 80 + i * 2.4)
    P.hit(beat_of(24, 0), KICK, 112, 'foot')
    P.hit(beat_of(24, 8), KICK, 98, 'foot')

    # bars 25-26 -- double strokes travel round the kit
    for b, drums in ((25, [SNARE, TOM_H, TOM_M]), (26, [TOM_L, TOM_LL, SNARE])):
        for i in range(16):
            v = 66 + i * 2.6 - (10 if i % 2 else 0)
            P.hit(beat_of(b, i), drums[(i // 4) % 3], v)
        P.hit(beat_of(b, 0), KICK, 112, 'foot')
        P.hit(beat_of(b, 8), KICK, 98, 'foot')
        P.hit(beat_of(b, 12), KICK, 92, 'foot')

    # bar 27 -- singles around the kit, pushing a little
    P.push = -6.0
    seq = [SNARE, TOM_H, SNARE, TOM_HM, SNARE, TOM_M, SNARE, TOM_LM,
           SNARE, TOM_L, SNARE, TOM_LL, TOM_L, TOM_LM, TOM_M, TOM_HM]
    for i in range(16):
        P.hit(beat_of(27, i), seq[i], 84 + (10 if i % 4 == 0 else 0) + i * 1.4)
    P.hit(beat_of(27, 0), KICK, 114, 'foot')
    P.hit(beat_of(27, 8), KICK, 100, 'foot')

    # bar 28 -- crescendo into the crash
    for i in range(8):
        P.hit(beat_of(28, i), SNARE if i < 4 else TOM_H, 84 + i * 4.0)
    seq = [TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L, TOM_LM, TOM_M]
    for i in range(16):
        P.hit(beat_of(28, 8 + i * 0.5), seq[i % 8], 100 + i * 1.3)
    P.hit(beat_of(28, 0), KICK, 114, 'foot')
    P.hit(beat_of(28, 8), KICK, 102, 'foot')


# ----------------------------------------------------------------------
#  4. bars 29-36 : rolls, swells, doubles
# ----------------------------------------------------------------------
def part_rolls(P):
    P.push, P.jitter, P.swing = -2.0, 6.0, 0.0

    # bar 29 -- the press roll swells over four beats
    P.hit(beat_of(29, 0), KICK, 104, 'foot')
    P.hit(beat_of(29, 4), HH_PEDAL, 74, 'foot')
    P.hit(beat_of(29, 12), HH_PEDAL, 74, 'foot')
    for i in range(32):
        v = 42 + (i / 31.0) ** 1.5 * 76
        P.hit(beat_of(29, i * 0.5), SNARE, v, human=1.2)

    # bar 30 -- the roll resolves; groove with toms
    P.hit(beat_of(30, 0), CRASH, 122)
    P.hit(beat_of(30, 0), KICK, 114, 'foot')
    for s in (2, 4, 6, 8, 10, 12, 14):
        P.hit(beat_of(30, s), HH, 66 if s % 4 == 0 else 56)
    P.hit(beat_of(30, 4), SNARE, 102, extra=8)
    P.hit(beat_of(30, 12), SNARE, 106, extra=8)
    P.hit(beat_of(30, 6), TOM_H, 84)
    P.hit(beat_of(30, 7), KICK, 84, 'foot')
    P.hit(beat_of(30, 10), TOM_HM, 80)
    P.hit(beat_of(30, 14), COWBELL, 78)

    # bar 31 -- double strokes swell and turn into toms
    for i in range(16):
        v = 60 + i * 3.6 - (10 if i % 2 else 0)
        P.hit(beat_of(31, i), SNARE if i < 10 else TOM_HM, v)
    P.hit(beat_of(31, 0), KICK, 110, 'foot')
    P.hit(beat_of(31, 8), KICK, 98, 'foot')
    P.hit(beat_of(31, 12), KICK, 92, 'foot')

    # bar 32 -- crash and a breath
    P.hit(beat_of(32, 0), CRASH, 118)
    P.hit(beat_of(32, 0), KICK, 112, 'foot')
    P.hit(beat_of(32, 4), SNARE, 106, extra=8)
    P.hit(beat_of(32, 6), KICK, 84, 'foot')
    P.hit(beat_of(32, 8), HH_PEDAL, 76, 'foot')
    P.hit(beat_of(32, 10), SNARE, 40)
    P.hit(beat_of(32, 12), SNARE, 110, extra=8)
    P.hit(beat_of(32, 14), SPLASH, 84)

    # bars 33-34 -- triplet rolls travel around the kit
    trip = [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL]
    for b in (33, 34):
        for i in range(12):
            s = i * (4.0 / 3.0)
            v = 74 + (i % 3) * 5 + (6 if i % 3 == 0 else 0)
            P.hit(beat_of(b, s), trip[(i // 3) % 6], v)
        P.hit(beat_of(b, 0), KICK, 112, 'foot')
        P.hit(beat_of(b, 8), KICK, 100, 'foot')
        P.hit(beat_of(b, 12), KICK, 96, 'foot')

    # bar 35 -- singles up and down the kit
    seq = [SNARE, TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L,
           TOM_LM, TOM_M, TOM_HM, TOM_H, SNARE, SNARE, TOM_H, TOM_HM]
    for i in range(16):
        P.hit(beat_of(35, i), seq[i], 88 + (12 if i % 4 == 0 else 0))
    P.hit(beat_of(35, 0), KICK, 114, 'foot')
    P.hit(beat_of(35, 8), KICK, 102, 'foot')

    # bar 36 -- build: sixteenths, then thirty-seconds
    for i in range(8):
        P.hit(beat_of(36, i), SNARE if i < 4 else TOM_H, 84 + i * 3.0)
    seq = [TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L, TOM_LM, TOM_M]
    for i in range(16):
        P.hit(beat_of(36, 8 + i * 0.5), seq[i % 8], 100 + i * 1.3)
    P.hit(beat_of(36, 0), KICK, 114, 'foot')
    P.hit(beat_of(36, 8), KICK, 104, 'foot')
    P.hit(beat_of(36, 15), WOOD_HI, 92)


# ----------------------------------------------------------------------
#  5. bars 37-46 : motif development, hemiola, tension
# ----------------------------------------------------------------------
def part_tension(P):
    P.push, P.jitter, P.swing = -5.0, 6.0, 0.0

    # bar 37 -- crash, then MOTIF A at double speed (diminution)
    P.hit(beat_of(37, 0), CRASH, 124)
    P.hit(beat_of(37, 0), KICK, 118, 'foot')
    for s in (2, 4, 6):
        P.hit(beat_of(37, s), HH, 64)
    for s, is_acc in MOTIF_A:
        P.hit(beat_of(37, 8 + s * 0.5), SNARE, 108 if is_acc else 38)
    P.hit(beat_of(37, 8), KICK, 100, 'foot')
    P.hit(beat_of(37, 12), SNARE, 104)
    P.hit(beat_of(37, 14), SNARE, 40)
    P.hit(beat_of(37, 15), SNARE, 96)

    # bar 38 -- the same figure at half speed, on the toms (augmentation)
    P.hit(beat_of(38, 0), KICK, 114, 'foot')
    P.hit(beat_of(38, 0), HH_PEDAL, 74, 'foot')
    P.hit(beat_of(38, 4), HH_PEDAL, 74, 'foot')
    P.hit(beat_of(38, 8), KICK, 100, 'foot')
    toms = [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L]
    for i, (s, is_acc) in enumerate(MOTIF_A):
        P.hit(beat_of(38, s * 2), toms[i], 106 if is_acc else 54)

    # bar 39 -- the kick asks, the hands answer
    P.hit(beat_of(39, 0), KICK, 116, 'foot')
    P.hit(beat_of(39, 2), SNARE, 110)
    P.hit(beat_of(39, 3), SNARE, 44)
    P.hit(beat_of(39, 6), KICK, 100, 'foot')
    P.hit(beat_of(39, 7), SNARE, 106)
    P.hit(beat_of(39, 8), SNARE, 40)
    P.hit(beat_of(39, 10), KICK, 104, 'foot')
    P.hit(beat_of(39, 11), SNARE, 108)
    P.hit(beat_of(39, 13), KICK, 96, 'foot')
    P.hit(beat_of(39, 14), SNARE, 112)
    P.hit(beat_of(39, 15), SNARE, 46)

    # bar 40 -- hemiola: the kick stays in four, the hands go in three
    for s in (0, 4, 8, 12):
        P.hit(beat_of(40, s), KICK, 108 if s == 0 else 96, 'foot')
    for s in (0, 6, 12):
        P.hit(beat_of(40, s), SNARE, 112)
        P.hit(beat_of(40, s + 1), SNARE, 44)
        P.hit(beat_of(40, s + 2), SNARE, 38)

    # bar 41 -- singles down the toms
    seq = [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_M, TOM_M,
           TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_LL, TOM_LL, TOM_L, TOM_LM]
    for i in range(16):
        P.hit(beat_of(41, i), seq[i], 88 + (10 if i % 4 == 0 else 0) + i * 1.2)
    P.hit(beat_of(41, 0), KICK, 116, 'foot')
    P.hit(beat_of(41, 8), KICK, 104, 'foot')

    # bar 42 -- thirty-second singles, accents on the downbeats
    for i in range(32):
        v = 72 + (30 if i % 8 == 0 else 0) + (10 if i > 24 else 0)
        P.hit(beat_of(42, i * 0.5), SNARE if i < 24 else TOM_H, v)
    P.hit(beat_of(42, 0), KICK, 116, 'foot')
    P.hit(beat_of(42, 8), KICK, 106, 'foot')
    P.hit(beat_of(42, 12), KICK, 110, 'foot')

    # bar 43 -- full kit groove, hats and ghosts, second crash
    P.hit(beat_of(43, 0), CRASH2, 118)
    P.hit(beat_of(43, 0), KICK, 116, 'foot')
    for s in (2, 4, 6, 8, 10, 12, 14):
        P.hit(beat_of(43, s), HH, 68 if s % 4 == 0 else 56)
    P.hit(beat_of(43, 4), SNARE, 106, extra=8)
    P.hit(beat_of(43, 12), SNARE, 110, extra=8)
    P.hit(beat_of(43, 7), SNARE, 38)
    P.hit(beat_of(43, 10), KICK, 92, 'foot')
    P.hit(beat_of(43, 14), SNARE, 44)

    # bar 44 -- doubles around the toms
    for i in range(16):
        d = [TOM_H, TOM_HM, TOM_M, TOM_LM][(i // 4) % 4]
        v = 78 + i * 2.2 - (10 if i % 2 else 0)
        P.hit(beat_of(44, i), d, v)
    P.hit(beat_of(44, 0), KICK, 116, 'foot')
    P.hit(beat_of(44, 8), KICK, 104, 'foot')
    P.hit(beat_of(44, 12), KICK, 108, 'foot')

    # bar 45 -- eighths, rising
    walk = [SNARE, SNARE, SNARE, TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L]
    for i, s in enumerate((0, 2, 4, 6, 8, 10, 12, 14)):
        P.hit(beat_of(45, s), walk[i], 84 + i * 5.0)
    P.hit(beat_of(45, 0), KICK, 118, 'foot')
    P.hit(beat_of(45, 8), KICK, 108, 'foot')

    # bar 46 -- sixteenths to thirty-seconds, all the way up
    for i in range(8):
        P.hit(beat_of(46, i), SNARE if i < 4 else TOM_H, 88 + i * 3.5)
    seq = [TOM_HM, TOM_M, TOM_M, TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_LL]
    for i in range(16):
        P.hit(beat_of(46, 8 + i * 0.5), seq[i % 8], 106 + i * 1.2)
    P.hit(beat_of(46, 0), KICK, 118, 'foot')
    P.hit(beat_of(46, 8), KICK, 110, 'foot')


# ----------------------------------------------------------------------
#  6. bars 47-52 : the climax
# ----------------------------------------------------------------------
def part_climax(P):
    P.push, P.jitter, P.swing = -6.0, 5.0, 0.0

    # bar 47 -- crash and a wall of sixteenths
    P.hit(beat_of(47, 0), CRASH, 127)
    P.hit(beat_of(47, 0), KICK, 120, 'foot')
    seq = [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_M, TOM_M,
           TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_LL, TOM_LL, TOM_L, TOM_LM]
    for i in range(16):
        v = 100 + (14 if i % 4 == 0 else 0) + (6 if i % 2 == 0 else 0)
        P.hit(beat_of(47, i), seq[i], v)
    P.hit(beat_of(47, 8), KICK, 110, 'foot')

    # bar 48 -- kick and snare in unison, big and square
    for s, v in ((0, 118), (3, 96), (4, 112), (6, 92),
                 (8, 118), (11, 96), (12, 112), (14, 94)):
        P.hit(beat_of(48, s), SNARE, v)
    for s, v in ((0, 120), (4, 110), (6, 104), (8, 118), (12, 112)):
        P.hit(beat_of(48, s), KICK, v, 'foot')

    # bar 49 -- thirty-second roll with accents
    for i in range(32):
        v = 100 + (16 if i % 8 == 0 else 0) - (10 if i % 2 else 0)
        P.hit(beat_of(49, i * 0.5), SNARE if i < 20 else TOM_H, v)
    P.hit(beat_of(49, 0), KICK, 120, 'foot')
    P.hit(beat_of(49, 8), KICK, 112, 'foot')
    P.hit(beat_of(49, 12), KICK, 114, 'foot')

    # bar 50 -- fills the room
    seq = [TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L, TOM_LM,
           TOM_M, TOM_HM, TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL]
    for i in range(16):
        P.hit(beat_of(50, i), seq[i], 106 + (12 if i % 4 == 0 else 0))
    P.hit(beat_of(50, 0), KICK, 120, 'foot')
    P.hit(beat_of(50, 8), KICK, 114, 'foot')

    # bar 51 -- crash, then one last chorus of the pocket
    P.hit(beat_of(51, 0), CRASH, 126)
    P.hit(beat_of(51, 0), KICK, 120, 'foot')
    for s in (2, 4, 6, 8, 10, 12, 14):
        P.hit(beat_of(51, s), HH, 72 if s % 4 == 0 else 60)
    P.hit(beat_of(51, 4), SNARE, 112, extra=6)
    P.hit(beat_of(51, 12), SNARE, 116, extra=6)
    P.hit(beat_of(51, 7), SNARE, 40)
    P.hit(beat_of(51, 10), KICK, 100, 'foot')
    P.hit(beat_of(51, 15), SNARE, 46)

    # bar 52 -- everything, then it stops dead
    for i in range(8):
        P.hit(beat_of(52, i), SNARE if i < 4 else TOM_H, 104 + i * 2.5)
    seq = [TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L, TOM_LM, TOM_M]
    for i in range(16):
        P.hit(beat_of(52, 8 + i * 0.5), seq[i % 8], 116 + i * 0.6)
    P.hit(beat_of(52, 0), KICK, 118, 'foot')
    P.hit(beat_of(52, 8), KICK, 112, 'foot')


# ----------------------------------------------------------------------
#  7. bars 53-60 : release, the motif remembered, and the last hit
# ----------------------------------------------------------------------
def part_release(P):
    P.push, P.jitter, P.swing = 5.0, 7.0, 0.0     # lay back, let the air in

    # bar 53 -- one bell, a lot of space
    P.hit(beat_of(53, 0), RIDE_BELL, 92)
    P.hit(beat_of(53, 4), HH_PEDAL, 66, 'foot')
    P.hit(beat_of(53, 8), SNARE, 58)
    P.hit(beat_of(53, 9), SPLASH, 62)
    P.hit(beat_of(53, 10), SNARE, 34)
    P.hit(beat_of(53, 12), HH_PEDAL, 66, 'foot')

    # bars 54-55 -- the opening motif, remembered quietly
    for b in (54, 55):
        P.hit(beat_of(b, 0), KICK, 98, 'foot')
        P.hit(beat_of(b, 4), HH_PEDAL, 68, 'foot')
        P.hit(beat_of(b, 6), KICK, 74, 'foot')
        P.hit(beat_of(b, 11), KICK, 70, 'foot')
        P.hit(beat_of(b, 12), HH_PEDAL, 68, 'foot')
        play_cell(P, b, 0, MOTIF_A, SNARE, 88, 32)
        for s in (8, 10, 12, 14):
            P.hit(beat_of(b, s), RIDE, 66 if s == 8 else 56)

    # bar 56 -- a small, tidy fill
    for s, n, v in ((0, SNARE, 80), (2, SNARE, 84), (4, TOM_H, 88),
                    (6, TOM_HM, 84), (8, TOM_M, 92), (10, TOM_LM, 86),
                    (12, TOM_L, 96), (14, SNARE, 88)):
        P.hit(beat_of(56, s), n, v)
    P.hit(beat_of(56, 0), KICK, 100, 'foot')
    P.hit(beat_of(56, 8), KICK, 86, 'foot')

    # bar 57 -- brakes off, doubles on the snare
    P.push = 0.0
    for i in range(16):
        v = 70 + i * 3.2 - (9 if i % 2 else 0)
        P.hit(beat_of(57, i), SNARE, v)
    P.hit(beat_of(57, 0), KICK, 104, 'foot')
    P.hit(beat_of(57, 8), KICK, 94, 'foot')
    P.hit(beat_of(57, 12), KICK, 90, 'foot')

    # bar 58 -- around the kit, faster
    seq = [SNARE, TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L,
           TOM_LM, TOM_M, TOM_HM, TOM_H, TOM_HM, TOM_M, TOM_LM, TOM_L]
    for i in range(16):
        P.hit(beat_of(58, i), seq[i], 92 + (12 if i % 4 == 0 else 0) + i * 1.4)
    P.hit(beat_of(58, 0), KICK, 110, 'foot')
    P.hit(beat_of(58, 8), KICK, 102, 'foot')

    # bar 59 -- the last fill, rushing the finish line
    P.push = -8.0
    for i in range(8):
        P.hit(beat_of(59, i), SNARE if i < 4 else TOM_H, 96 + i * 2.5)
    seq = [TOM_HM, TOM_M, TOM_LM, TOM_L, TOM_LL, TOM_L, TOM_LM, TOM_M]
    for i in range(16):
        P.hit(beat_of(59, 8 + i * 0.5), seq[i % 8], 112 + i * 0.9)
    P.hit(beat_of(59, 0), KICK, 118, 'foot')
    P.hit(beat_of(59, 8), KICK, 112, 'foot')
    P.hit(beat_of(59, 14), KICK, 116, 'foot')

    # bar 60 -- land it.  Crash, crash and a kick, then air.
    P.hit(beat_of(60, 0), CRASH, 127)
    P.hit(beat_of(60, 0), CRASH2, 120)
    P.hit(beat_of(60, 0), KICK, 122, 'foot')


def compose(P):
    part_statement(P)
    part_develop(P)
    part_pocket(P)
    part_rolls(P)
    part_tension(P)
    part_climax(P)
    part_release(P)


# ----------------------------------------------------------------------
#  tempo map -- the pulse surges and settles with the music
# ----------------------------------------------------------------------
TEMPO_BARS = [
    (1, 92), (3, 96), (5, 100), (7, 103), (9, 106), (13, 110),
    (17, 116), (21, 120), (25, 124), (29, 126), (33, 128), (37, 130),
    (41, 133), (45, 136), (47, 139), (50, 137), (52, 133), (53, 112),
    (55, 108), (57, 111), (58, 115), (59, 123), (60, 130),
]


def tempo_curve():
    pts = [((bar - 1) * 4.0, bpm) for bar, bpm in TEMPO_BARS]

    def bpm(beat):
        if beat <= pts[0][0]:
            return pts[0][1]
        if beat >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            b0, v0 = pts[i]
            b1, v1 = pts[i + 1]
            if b0 <= beat <= b1:
                t = (beat - b0) / (b1 - b0)
                return v0 + (v1 - v0) * t
        return pts[-1][1]

    return bpm


def total_seconds(bpm, beats, steps=20000):
    dt = beats / steps
    return sum(dt * 60.0 / bpm(i * dt) for i in range(steps))


# ----------------------------------------------------------------------
#  MIDI output
# ----------------------------------------------------------------------
def write_midi(notes, bpm, total_beats, path):
    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    events = [
        (0, 0, mido.MetaMessage('track_name', name='Drum Solo', time=0)),
        (0, 0, mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                time=0)),
    ]

    for b in range(int(total_beats) + 1):
        events.append((b * PPQ, 0,
                       mido.MetaMessage('set_tempo',
                                        tempo=mido.bpm2tempo(bpm(b)), time=0)))

    for tick, note, vel in notes:
        ring = 700 if note in LONG_NOTES else 80
        events.append((tick, 1,
                       mido.Message('note_on', channel=CHANNEL, note=note,
                                    velocity=vel, time=0)))
        events.append((tick + ring, 0,
                       mido.Message('note_off', channel=CHANNEL, note=note,
                                    velocity=0, time=0)))

    events.sort(key=lambda e: (e[0], e[1]))

    last = 0
    for tick, _order, msg in events:
        msg.time = tick - last
        last = tick
        track.append(msg)

    track.append(mido.MetaMessage('end_of_track', time=PPQ * 3))
    mid.save(path)


# ----------------------------------------------------------------------
def main():
    P = Solo()
    compose(P)
    bpm = tempo_curve()
    total_beats = BARS * 4
    write_midi(P.notes, bpm, total_beats, 'solo.mid')
    print('solo.mid written: %d bars, %d notes, about %.1f seconds'
          % (BARS, len(P.notes), total_seconds(bpm, total_beats)))


if __name__ == '__main__':
    main()
