#!/usr/bin/env python3
"""
drum_solo.py -- writes a two-minute General MIDI drum solo to solo.mid.

* Everything lands on MIDI channel 10 (zero-based channel index 9).
* Fully deterministic: running the script twice in an empty directory
  produces byte-identical output.
* At most two hands and two feet strike at any single instant.
"""

import random
from collections import defaultdict

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
PPQ = 480
BAR = 4 * PPQ
CHAN = 9                       # MIDI channel 10

# --- General MIDI percussion -------------------------------------------------
KICK      = 36
SIDE      = 37
SNARE     = 38
CLAP      = 39
E_SNARE   = 40
FLOOR_L   = 41
HH_CLOSED = 42
FLOOR_H   = 43
HH_PEDAL  = 44
TOM_L     = 45
HH_OPEN   = 46
TOM_LM    = 47
TOM_HM    = 48
CRASH1    = 49
TOM_H     = 50
RIDE1     = 51
CHINA     = 52
RIDE_BELL = 53
TAMB      = 54
SPLASH    = 55
COWBELL   = 56
CRASH2    = 57
RIDE2     = 59
BONGO_H   = 60
BONGO_L   = 61
CONGA_M   = 62
CONGA_O   = 63
CONGA_L   = 64
TIMB_H    = 65
TIMB_L    = 66
CLAVES    = 75
WOOD_H    = 76
WOOD_L    = 77
TRI_OPEN  = 81

FEET = frozenset((KICK, HH_PEDAL))

# Note lengths (ticks).  Cymbals ring, drums are short.
DUR = {
    KICK: 90, SIDE: 70, SNARE: 90, CLAP: 80, E_SNARE: 80,
    FLOOR_L: 200, FLOOR_H: 200,
    TOM_L: 180, TOM_LM: 180, TOM_HM: 170, TOM_H: 160,
    HH_CLOSED: 60, HH_PEDAL: 60, HH_OPEN: 220,
    CRASH1: 1500, CRASH2: 1500, CHINA: 1000, SPLASH: 520,
    RIDE1: 320, RIDE2: 320, RIDE_BELL: 260,
    TAMB: 130, COWBELL: 120, CLAVES: 90, WOOD_H: 80, WOOD_L: 80,
    BONGO_H: 110, BONGO_L: 120, CONGA_M: 120, CONGA_O: 140, CONGA_L: 150,
    TIMB_H: 130, TIMB_L: 140, TRI_OPEN: 800,
}

# ----------------------------------------------------------------------------
# Timing / feel
# ----------------------------------------------------------------------------
def place(bar, sub, swing=0.0, push=0.0):
    """Absolute tick for a position on the 16th-note grid.

    `sub` may be fractional (e.g. 24.5 for a 32nd).  `swing` (ticks) delays
    the second 8th of each beat; `push` shifts the whole event in time.
    """
    b = int(sub // 4)
    i = sub - 4.0 * b
    off = i * 120.0
    if i == 2.0:                       # the swung off-beat 8th
        off += swing
    return bar * BAR + b * PPQ + off + push


class Solo:
    def __init__(self, seed=20240607):
        self.notes = []                # (tick, note, vel, dur)
        self.tempos = []               # (tick, bpm)
        self.rng = random.Random(seed)

    def hit(self, tick, note, vel, dur=None):
        if dur is None:
            dur = DUR.get(note, 100)
        vel = max(1, min(127, int(round(vel))))
        tick = max(0, int(round(tick)))
        self.notes.append((tick, note, vel, dur))


def play(S, start_bar, nbars, pattern, period=32, swing=0.0, push=0.0,
         lay=None, vel_scale=1.0, vel_jitter=0.0):
    """Stamp a repeating pattern of (sub, note, vel[, dur]) onto the timeline."""
    if lay is None:
        lay = {}
    assert (nbars * 16) % period == 0, "pattern must divide the section"
    reps = (nbars * 16) // period
    for r in range(reps):
        for item in pattern:
            sub, note, vel = item[0], item[1], item[2]
            dur = item[3] if len(item) > 3 else None
            s = r * period + sub
            bar = start_bar + s // 16
            sib = s % 16
            tick = place(bar, sib, swing, push + lay.get(note, 0.0))
            v = vel * vel_scale
            if vel_jitter:
                v += S.rng.uniform(-vel_jitter, vel_jitter)
            S.hit(tick, note, v, dur)


def run16(S, bar0, nbars, notes, swing=0.0, push=0.0,
          accent=104, strong=86, weak=64, kick_subs=()):
    """A single-stroke run of 16ths cycling through `notes`."""
    idx = 0
    for bar in range(bar0, bar0 + nbars):
        for sub in range(16):
            note = notes[idx % len(notes)]
            idx += 1
            if sub % 4 == 0:
                v = accent
            elif sub % 2 == 0:
                v = strong
            else:
                v = weak
            S.hit(place(bar, sub, swing, push), note, v)
        for ks in kick_subs:
            S.hit(place(bar, ks, swing, push), KICK, 106)


# ----------------------------------------------------------------------------
# Per-voice micro placement ("deliberate" feel, not random jitter)
# ----------------------------------------------------------------------------
LAY_LOOSE = {SNARE: 8.0, SIDE: 6.0, KICK: -4.0, TOM_HM: 3.0, TOM_L: 3.0}
LAY_TIGHT = {SNARE: -2.0, KICK: -6.0}
LAY_NONE  = {}


# ============================================================================
#  THE PIECE
# ============================================================================
def build_solo():
    S = Solo(seed=20240607)

    # ------------------------------------------------------------------ tempo
    tempo_map = [
        (0, 96), (4, 100), (12, 104), (18, 108),
        (20, 92),
        (28, 100), (29, 102), (30, 104), (31, 106),
        (32, 108), (33, 110), (34, 112), (35, 114),
        (36, 120),
        (44, 104),
    ]
    for bar, bpm in tempo_map:
        S.tempos.append((bar * BAR, bpm))

    # ================================================== A. INTRO (bars 0-3)
    intro = [
        # bar 0 -- pedal hat + cross stick, very sparse
        (0, HH_PEDAL, 62), (4, SIDE, 80), (8, HH_PEDAL, 58), (12, SIDE, 88),
        # bar 1 -- wood block answers
        (16, HH_PEDAL, 62), (20, CLAVES, 82), (24, HH_PEDAL, 58), (28, CLAVES, 88),
        (24, RIDE1, 54),
        # bar 2 -- ride pattern arrives
        (32, RIDE1, 74), (34, RIDE1, 56), (36, RIDE1, 68), (38, RIDE1, 54),
        (40, RIDE1, 72), (42, RIDE1, 56), (44, RIDE1, 68), (46, RIDE1, 54),
        (36, SIDE, 86), (44, SIDE, 90),
        (32, KICK, 84),
        # bar 3 -- full voice, ghost note into the downbeat
        (48, RIDE1, 78), (50, RIDE1, 60), (52, RIDE1, 72), (54, RIDE1, 58),
        (56, RIDE1, 76), (58, RIDE1, 60), (60, RIDE1, 72), (62, RIDE1, 58),
        (52, SNARE, 98), (60, SNARE, 104),
        (48, KICK, 98), (56, KICK, 92),
        (63, SNARE, 46),
    ]
    play(S, 0, 4, intro, period=64, swing=8.0, vel_jitter=2.0, lay=LAY_LOOSE)

    # ========================================== B. MOTIF (bars 4-11, tempo 100)
    GROOVE = [
        # ---- bar 1
        (0, HH_CLOSED, 80), (2, HH_CLOSED, 58), (4, HH_CLOSED, 72), (6, HH_CLOSED, 56),
        (8, HH_CLOSED, 78), (10, HH_CLOSED, 58), (12, HH_CLOSED, 72), (14, HH_CLOSED, 56),
        (0, KICK, 108), (10, KICK, 96),
        (4, SNARE, 104), (12, SNARE, 108),
        (4, HH_PEDAL, 52), (12, HH_PEDAL, 52),
        (7, SNARE, 34), (15, SNARE, 30),
        # ---- bar 2 (answer)
        (16, HH_CLOSED, 80), (18, HH_CLOSED, 58), (20, HH_CLOSED, 72), (22, HH_CLOSED, 56),
        (24, HH_CLOSED, 78), (26, HH_CLOSED, 58), (28, HH_CLOSED, 72), (30, HH_OPEN, 70),
        (16, KICK, 108), (22, KICK, 92), (26, KICK, 98),
        (20, SNARE, 104), (28, SNARE, 110),
        (20, HH_PEDAL, 52),
        (19, SNARE, 32), (31, SNARE, 34),
    ]
    play(S, 4, 4, GROOVE, period=32, swing=25.0, vel_jitter=2.5, lay=LAY_LOOSE)
    play(S, 8, 2, GROOVE, period=32, swing=25.0, vel_jitter=2.5, lay=LAY_LOOSE)

    GROOVE_B = [                       # denser kick, little tom tag
        (0, HH_CLOSED, 82), (2, HH_CLOSED, 60), (4, HH_CLOSED, 74), (6, HH_CLOSED, 58),
        (8, HH_CLOSED, 80), (10, HH_CLOSED, 60), (12, HH_CLOSED, 74), (14, HH_CLOSED, 58),
        (0, KICK, 110), (6, KICK, 92), (10, KICK, 98),
        (4, SNARE, 106), (12, SNARE, 110),
        (7, SNARE, 36), (15, SNARE, 32),
        (16, HH_CLOSED, 82), (18, HH_CLOSED, 60), (20, HH_CLOSED, 74), (22, HH_CLOSED, 58),
        (24, HH_CLOSED, 80), (26, HH_CLOSED, 60), (28, HH_CLOSED, 74), (30, HH_OPEN, 74),
        (16, KICK, 110), (22, KICK, 94), (28, KICK, 100),
        (20, SNARE, 106), (28, SNARE, 112),
        (17, SNARE, 34),
        (18, TOM_HM, 74), (19, TOM_HM, 52),
        (31, TOM_HM, 80),
    ]
    play(S, 10, 2, GROOVE_B, period=32, swing=25.0, vel_jitter=2.5, lay=LAY_LOOSE)

    # ==================================== C. DEVELOPMENT (bars 12-17, tempo 104)
    GROOVE_C = [
        # ---- bar 1 : 16th hat chatter around the same motif
        (0, HH_CLOSED, 84), (1, HH_CLOSED, 50), (2, HH_CLOSED, 62), (3, HH_CLOSED, 48),
        (4, HH_CLOSED, 76), (6, HH_CLOSED, 58),
        (8, HH_CLOSED, 82), (10, HH_CLOSED, 62), (11, HH_CLOSED, 50),
        (12, HH_CLOSED, 76), (14, HH_CLOSED, 58), (15, HH_CLOSED, 48),
        (0, KICK, 112), (10, KICK, 98),
        (4, SNARE, 108), (12, SNARE, 112),
        (7, SNARE, 38), (13, SNARE, 34),
        # ---- bar 2 : tom answer
        (16, HH_CLOSED, 84), (18, HH_CLOSED, 62), (20, HH_CLOSED, 76), (22, HH_CLOSED, 58),
        (16, KICK, 112), (22, KICK, 96),
        (20, SNARE, 108),
        (24, TOM_HM, 92), (26, TOM_HM, 74), (28, TOM_L, 96), (30, TOM_L, 78),
        (28, KICK, 100),
    ]
    play(S, 12, 4, GROOVE_C, period=32, swing=20.0, vel_jitter=2.0, lay=LAY_LOOSE)

    run16(S, 16, 2,
          [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, FLOOR_H, FLOOR_L, FLOOR_L,
           TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, TOM_HM, TOM_LM, SNARE],
          swing=20.0, push=0.0, accent=108, strong=90, weak=68, kick_subs=(0, 8))

    # ========================================= D. FILL (bars 18-19, tempo 108)
    d1 = [
        (0, SNARE, 108), (1, SNARE, 60), (2, SNARE, 88), (3, SNARE, 64),
        (4, SNARE, 110), (5, SNARE, 62), (6, TOM_H, 96), (7, TOM_H, 66),
        (8, TOM_H, 102), (9, TOM_H, 68), (10, TOM_HM, 100), (11, TOM_HM, 68),
        (12, TOM_HM, 106), (13, TOM_HM, 70), (14, TOM_LM, 102), (15, TOM_LM, 72),
    ]
    d2 = [
        (0, TOM_LM, 108), (1, TOM_LM, 72), (2, TOM_L, 104), (3, TOM_L, 74),
        (4, TOM_L, 110), (5, TOM_L, 76), (6, FLOOR_H, 104), (7, FLOOR_H, 74),
        (8, FLOOR_H, 100), (9, SNARE, 96), (10, SNARE, 70), (11, SNARE, 100),
        (12, KICK, 112), (13, KICK, 90), (14, SNARE, 108), (15, SNARE, 80),
        (0, KICK, 108), (8, KICK, 100),
    ]
    play(S, 18, 1, d1, period=16, swing=0.0, push=-3.0)
    play(S, 19, 1, d2, period=16, swing=0.0, push=-3.0)

    # ==================================== E. BREAKDOWN (bars 20-27, tempo 92)
    E_PAT = [
        # ---- bar 0 : crash resolves, cross-stick and ride bell take over
        (0, CRASH2, 64),
        (2, RIDE_BELL, 74), (4, SIDE, 72), (6, RIDE_BELL, 56),
        (8, RIDE_BELL, 72), (10, RIDE_BELL, 56), (12, SIDE, 74), (14, RIDE_BELL, 54),
        (0, KICK, 78), (0, HH_PEDAL, 62), (8, HH_PEDAL, 58),
        # ---- bar 1
        (16, RIDE_BELL, 76), (18, RIDE_BELL, 54), (20, SIDE, 72), (22, RIDE_BELL, 52),
        (24, RIDE_BELL, 72), (26, RIDE_BELL, 54), (28, SIDE, 74), (30, RIDE_BELL, 52),
        (16, KICK, 76), (24, KICK, 74),
        (21, SNARE, 30), (29, SNARE, 28),
        # ---- bar 2
        (32, TRI_OPEN, 62), (32, RIDE_BELL, 78), (34, RIDE_BELL, 56),
        (36, SIDE, 76), (38, RIDE_BELL, 56),
        (40, RIDE_BELL, 74), (42, RIDE_BELL, 56), (44, SIDE, 78), (46, RIDE_BELL, 56),
        (32, KICK, 76), (32, HH_PEDAL, 60), (40, HH_PEDAL, 58), (44, KICK, 80),
        (39, SNARE, 32), (47, SNARE, 30),
        # ---- bar 3
        (48, RIDE_BELL, 78), (50, RIDE_BELL, 56), (52, SIDE, 74), (54, RIDE_BELL, 54),
        (56, RIDE_BELL, 74), (58, RIDE_BELL, 56), (60, SNARE, 80), (62, SNARE, 52),
        (48, KICK, 78), (56, KICK, 80), (60, KICK, 86),
    ]
    play(S, 20, 4, E_PAT, period=64, swing=35.0, push=14.0,
         vel_scale=0.92, vel_jitter=2.0)

    E_PAT2 = [
        (0, RIDE_BELL, 80), (2, RIDE_BELL, 56), (4, SIDE, 74), (6, RIDE_BELL, 56),
        (8, RIDE_BELL, 76), (10, RIDE_BELL, 58), (12, SIDE, 78), (14, RIDE_BELL, 58),
        (0, KICK, 84), (8, KICK, 82),
        (5, SNARE, 34), (13, SNARE, 36),
        (16, RIDE_BELL, 80), (18, RIDE_BELL, 56), (20, SIDE, 76), (22, RIDE_BELL, 56),
        (24, RIDE_BELL, 78), (26, RIDE_BELL, 58), (28, SNARE, 86), (30, SNARE, 58),
        (16, KICK, 84), (24, KICK, 86), (28, KICK, 90),
    ]
    play(S, 24, 2, E_PAT2, period=32, swing=30.0, push=10.0, vel_jitter=2.0)

    E_BUILD = []                        # two bars of swelling snare
    for i in range(32):
        v = 70 + i * 1.7
        if i % 2 == 1:
            v -= 20
        E_BUILD.append((i, SNARE, v))
    for i in (0, 8, 16, 24):
        E_BUILD.append((i, KICK, 84 + 3 * (i // 8)))

    play(S, 26, 2, E_BUILD, period=32, swing=20.0, push=4.0, vel_jitter=2.0)

    # ======================================== F. BUILD (bars 28-35, 100..114)
    F_A = [
        (0, HH_CLOSED, 86), (2, HH_CLOSED, 62), (4, HH_CLOSED, 78), (6, HH_CLOSED, 58),
        (8, HH_CLOSED, 84), (10, HH_CLOSED, 62), (12, HH_CLOSED, 78), (14, HH_CLOSED, 58),
        (0, KICK, 112), (6, KICK, 94), (10, KICK, 100),
        (4, SNARE, 110), (12, SNARE, 112),
        (7, SNARE, 40), (15, SNARE, 36),
        (16, HH_CLOSED, 86), (18, HH_CLOSED, 62), (20, HH_CLOSED, 78), (22, HH_CLOSED, 58),
        (24, HH_CLOSED, 84), (26, HH_CLOSED, 62), (28, HH_CLOSED, 78), (30, HH_CLOSED, 58),
        (16, KICK, 112), (22, KICK, 96), (26, KICK, 102),
        (20, SNARE, 110), (28, SNARE, 112),
        (19, SNARE, 38), (31, SNARE, 42),
    ]
    play(S, 28, 2, F_A, period=32, swing=14.0, push=0.0,
         vel_scale=0.96, vel_jitter=2.0, lay=LAY_TIGHT)

    F_ROLL = []
    for i in range(32):
        bar_i = i // 16
        v = 96 + 18 * bar_i + (8 if i % 4 == 0 else 0)
        if i % 2 == 1:
            v -= 26
        F_ROLL.append((i, SNARE, v))
    for i in (0, 8, 16, 24):
        F_ROLL.append((i, KICK, 104 + 4 * (i // 16)))
    play(S, 30, 2, F_ROLL, period=32, swing=10.0, push=-2.0, vel_jitter=2.0)

    run16(S, 32, 2,
          [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, FLOOR_H, FLOOR_L, FLOOR_L,
           TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, TOM_HM, TOM_LM, SNARE],
          swing=8.0, push=-4.0, accent=110, strong=92, weak=70, kick_subs=(0, 8))

    F_RUN2 = [
        (0, SNARE, 104), (2, TOM_H, 96), (4, TOM_HM, 100), (6, TOM_LM, 96),
        (8, TOM_L, 104), (10, FLOOR_H, 98), (12, FLOOR_L, 102), (14, TOM_L, 96),
        (0, KICK, 110), (8, KICK, 108),
        (16, TOM_L, 106), (18, TOM_LM, 100), (20, TOM_HM, 104), (22, TOM_H, 100),
        (24, SNARE, 110), (24.5, SNARE, 84), (25, SNARE, 96), (25.5, TOM_H, 80),
        (26, TOM_H, 106), (27, TOM_HM, 96), (28, TOM_HM, 110), (28.5, TOM_LM, 84),
        (29, TOM_LM, 98), (29.5, TOM_L, 82), (30, TOM_L, 108), (30.5, FLOOR_H, 86),
        (31, FLOOR_H, 100), (31.5, FLOOR_L, 90),
        (16, KICK, 110), (24, KICK, 112),
    ]
    play(S, 34, 2, F_RUN2, period=32, swing=0.0, push=-6.0, vel_jitter=2.0)

    # ========================================= G. PEAK (bars 36-43, tempo 120)
    G_OPEN = [
        (0, CRASH1, 118), (0, KICK, 118), (0, HH_PEDAL, 60),
        (2, HH_CLOSED, 66), (4, SNARE, 112), (6, HH_CLOSED, 62),
        (8, HH_CLOSED, 86), (8, KICK, 110), (10, HH_CLOSED, 64),
        (12, SNARE, 114), (14, HH_CLOSED, 64),
        (11, KICK, 96), (14, KICK, 100),
    ]
    play(S, 36, 1, G_OPEN, period=16, swing=0.0, push=-8.0, lay=LAY_TIGHT)

    run16(S, 37, 2,
          [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, FLOOR_H, FLOOR_L, TOM_L,
           TOM_HM, TOM_H, SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, FLOOR_H],
          swing=0.0, push=-8.0, accent=112, strong=94, weak=70, kick_subs=(0, 8))

    G_BURST = []                        # 32nd-note double-stroke burst
    tour = [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM,
            TOM_L, TOM_L, FLOOR_H, FLOOR_H, SNARE, TOM_H, TOM_HM, TOM_LM]
    k = 0
    for i in range(32):
        note = tour[k // 2]
        k += 1
        v = 110 if i % 4 == 0 else (94 if i % 2 == 0 else 82)
        G_BURST.append((i * 0.5, note, v))
    for i in (0, 8, 16, 24):
        G_BURST.append((i * 0.5, KICK, 112))
    play(S, 39, 1, G_BURST, period=16, swing=0.0, push=-8.0, vel_jitter=2.0)

    G_GROOVE = [
        (0, HH_CLOSED, 86), (2, HH_CLOSED, 62), (4, SNARE, 112), (6, HH_CLOSED, 62),
        (8, HH_CLOSED, 86), (10, HH_CLOSED, 64), (12, SNARE, 114), (14, HH_CLOSED, 64),
        (0, KICK, 116), (6, KICK, 100), (10, KICK, 106),
        (7, SNARE, 44),
        (16, HH_CLOSED, 86), (18, HH_CLOSED, 62), (20, SNARE, 112), (22, HH_CLOSED, 62),
        (24, HH_CLOSED, 86), (26, HH_CLOSED, 64), (28, TOM_HM, 108), (30, TOM_HM, 88),
        (16, KICK, 116), (22, KICK, 102), (28, KICK, 110),
        (19, SNARE, 46),
    ]
    play(S, 40, 2, G_GROOVE, period=32, swing=0.0, push=-8.0,
         vel_jitter=2.0, lay=LAY_TIGHT)

    G_FILL = [
        (0, SNARE, 112), (1, SNARE, 84), (2, TOM_H, 108), (3, TOM_H, 82),
        (4, TOM_HM, 110), (5, TOM_HM, 84), (6, TOM_LM, 108), (7, TOM_LM, 82),
        (8, TOM_L, 112), (9, TOM_L, 86), (10, FLOOR_H, 110), (11, FLOOR_H, 84),
        (12, FLOOR_L, 112), (13, FLOOR_L, 88), (14, SNARE, 110), (15, SNARE, 90),
        (0, KICK, 114), (4, KICK, 108), (8, KICK, 112), (12, KICK, 110),
    ]
    play(S, 42, 1, G_FILL, period=16, swing=0.0, push=-8.0)

    G_END = [
        (0, SNARE, 116), (1, SNARE, 90), (2, SNARE, 108), (3, SNARE, 86),
        (4, TOM_H, 112), (5, TOM_H, 88), (6, TOM_HM, 110), (7, TOM_HM, 86),
        (8, TOM_LM, 112), (9, TOM_LM, 88), (10, TOM_L, 110), (11, TOM_L, 86),
        (12, FLOOR_H, 114), (13, FLOOR_H, 92), (14, FLOOR_L, 112), (15, FLOOR_L, 96),
        (0, KICK, 116), (6, KICK, 110), (12, KICK, 114),
    ]
    play(S, 43, 1, G_END, period=16, swing=0.0, push=-8.0)

    # ==================================== H. RESOLUTION (bars 44-51, tempo 104)
    H_OPEN = [
        (0, CRASH1, 118), (0, KICK, 116),
        (2, HH_CLOSED, 62), (4, SNARE, 108), (6, HH_CLOSED, 58),
        (8, HH_CLOSED, 82), (10, HH_CLOSED, 60), (12, SNARE, 112), (14, HH_CLOSED, 58),
        (8, KICK, 100),
    ]
    play(S, 44, 1, H_OPEN, period=16, swing=25.0, push=0.0, lay=LAY_LOOSE)

    play(S, 45, 4, GROOVE, period=32, swing=25.0, vel_jitter=2.5, lay=LAY_LOOSE)

    H_FILLS = [
        (0, SNARE, 106), (2, SNARE, 78), (4, TOM_H, 104), (6, TOM_H, 76),
        (8, TOM_HM, 106), (10, TOM_HM, 78), (12, TOM_LM, 104), (14, TOM_LM, 76),
        (0, KICK, 108), (8, KICK, 104),
        (16, TOM_L, 108), (17, TOM_L, 80), (18, FLOOR_H, 106), (19, FLOOR_H, 80),
        (20, FLOOR_L, 110), (21, FLOOR_L, 84), (22, SNARE, 106), (23, SNARE, 82),
        (24, TOM_L, 104), (25, TOM_LM, 84), (26, TOM_HM, 108), (27, TOM_H, 86),
        (28, SNARE, 112), (29, SNARE, 88), (30, SNARE, 116), (31, SNARE, 94),
        (16, KICK, 108), (24, KICK, 112), (28, KICK, 110),
    ]
    play(S, 49, 2, H_FILLS, period=32, swing=20.0, push=2.0, vel_jitter=2.0)

    # big final statement -- crash, china, kick, snare
    final = [
        (0, CRASH1, 122), (0, KICK, 122), (0, SNARE, 118),
        (8, CHINA, 114), (8, KICK, 120), (8, SNARE, 104),
    ]
    play(S, 51, 1, final, period=16, swing=0.0, push=0.0)

    return S


# ============================================================================
#  Post-processing / validation / output
# ============================================================================
def dedupe(notes):
    seen = set()
    out = []
    for t, n, v, d in notes:
        key = (t, n)
        if key in seen:
            continue
        seen.add(key)
        out.append((t, n, v, d))
    return out


def trim_overlaps(notes):
    """Never let a note-off land after the next hit of the same drum."""
    by_note = defaultdict(list)
    for i, (t, n, v, d) in enumerate(notes):
        by_note[n].append(i)
    for n, idxs in by_note.items():
        idxs.sort(key=lambda i: notes[i][0])
        for a, b in zip(idxs, idxs[1:]):
            ta, na, va, da = notes[a]
            tb = notes[b][0]
            if ta + da >= tb:
                notes[a] = (ta, na, va, max(1, tb - ta - 1))
    return notes


def check_playable(notes):
    by_tick = defaultdict(list)
    for t, n, v, d in notes:
        by_tick[t].append(n)
    for t in sorted(by_tick):
        ns = by_tick[t]
        hands = sum(1 for n in ns if n not in FEET)
        feet = sum(1 for n in ns if n in FEET)
        assert hands <= 2, "more than two hands at tick %d: %r" % (t, ns)
        assert feet <= 2, "more than two feet at tick %d: %r" % (t, ns)


def write_midi(S, path):
    mid = MidiFile(ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    events = []
    events.append((0, -2, MetaMessage('track_name', name='Drum Solo')))
    events.append((0, -2, MetaMessage('time_signature', numerator=4,
                                      denominator=4, clocks_per_click=24,
                                      notated_32nd_notes_per_beat=8)))
    for tick, bpm in S.tempos:
        events.append((tick, -1, MetaMessage('set_tempo', tempo=bpm2tempo(bpm))))
    for (t, n, v, d) in S.notes:
        events.append((t, 1, Message('note_on', channel=CHAN, note=n, velocity=v)))
        events.append((t + d, 0, Message('note_off', channel=CHAN, note=n, velocity=0)))

    events.sort(key=lambda e: (e[0], e[1]))

    last = 0
    for tick, _prio, msg in events:
        msg.time = tick - last
        last = tick
        track.append(msg)

    track.append(MetaMessage('end_of_track', time=PPQ))
    mid.save(path)


def main():
    S = build_solo()
    notes = dedupe(S.notes)
    notes = trim_overlaps(notes)
    notes.sort(key=lambda e: (e[0], e[1]))
    check_playable(notes)
    S.notes = notes
    write_midi(S, 'solo.mid')
    print("wrote solo.mid  (%d note events)" % len(notes))


if __name__ == '__main__':
    main()
