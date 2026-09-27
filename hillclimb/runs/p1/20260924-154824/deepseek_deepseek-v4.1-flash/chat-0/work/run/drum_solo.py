#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drum_solo.py

Writes ``solo.mid``: a ~2 minute General MIDI drum solo for one drummer,
on MIDI channel 10 (zero based channel 9).

The solo is built from a handful of motifs that are stated, varied, developed
and recalled; density and dynamics are shaped in long waves so the music has
tension and release.  Every ghost note, every push and pull of the beat and
every roll is placed deliberately -- there is no randomness anywhere, so the
same bytes are produced on every run.

Playability: at most two hands (everything except notes 35/36/44) and two
feet (35/36/44) strike at any instant.
"""

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

# ----------------------------------------------------------------------
#  time base
# ----------------------------------------------------------------------
TPB    = 480          # ticks per quarter note
STEP   = 120          # a sixteenth note
BEAT   = 480
BARLEN = 1920         # 4/4


def bar(n):
    return n * BARLEN


# ----------------------------------------------------------------------
#  General MIDI percussion map (35-81) -- only what we need
# ----------------------------------------------------------------------
KICK, KICK2              = 36, 35
SNARE, STICK, CLAP       = 38, 37, 39
HH, PHH, OHH             = 42, 44, 46
T_HI, T_HIMID            = 50, 48
T_LOMID, T_LOW           = 47, 45
T_HIFL, T_LOWFL          = 43, 41
CRASH, CRASH2            = 49, 57
SPLASH, CHINA            = 55, 52
RIDE, RIDE2, BELL        = 51, 59, 53
COWBELL, TAMB            = 56, 54
BONGO_H, BONGO_L         = 60, 61
CONGA_M, CONGA_O, CONGA_L = 62, 63, 64
TIMB_H, TIMB_L           = 65, 66
AGOGO_H, AGOGO_L         = 67, 68
CABASA, MARACAS          = 69, 70
GUIRO_S, GUIRO_L         = 73, 74
CLAVES, WB_H, WB_L       = 75, 76, 77
TRI_M, TRI_O             = 80, 81

FOOT_NOTES = (35, 36, 44)

DUR = {
    35: 140, 36: 140, 37: 60, 38: 130, 39: 90, 40: 130,
    41: 260, 42: 80, 43: 240, 44: 80, 45: 220, 46: 600,
    47: 220, 48: 220, 49: 1680, 50: 220, 51: 240, 52: 1680,
    53: 340, 54: 180, 55: 960, 56: 220, 57: 1680, 59: 240,
    60: 150, 61: 170, 62: 190, 63: 210, 64: 230, 65: 170, 66: 190,
    67: 150, 68: 150, 69: 110, 70: 110, 73: 110, 74: 240, 75: 130,
    76: 130, 77: 150, 80: 260, 81: 500,
}

EVENTS = []           # (tick, note, duration, velocity)
TEMPOS = []           # (tick, bpm)


def tempo(tick, bpm):
    TEMPOS.append((int(tick), float(bpm)))


def hit(note, t, vel, dur=None):
    """Place one stroke."""
    if dur is None:
        dur = DUR.get(note, 150)
    v = int(round(vel))
    if v < 1:
        v = 1
    if v > 127:
        v = 127
    EVENTS.append((int(round(t)), int(note), int(dur), v))


# ----------------------------------------------------------------------
#  small writing helpers
# ----------------------------------------------------------------------
def hats(t0, base, steps=None, note=HH, swing=0.0):
    """Eighth note ride/hat pattern.  ``swing`` delays the off-beat eighths."""
    if steps is None:
        steps = list(range(0, 16, 2))
    for st in steps:
        v = base if st % 4 == 0 else base * 0.78
        off = swing if st % 4 == 2 else 0
        hit(note, t0 + st * STEP + off, v)


def run(t0, start, seq, spc=1):
    """Consecutive single strokes; ``spc`` in sixteenths (0.5 == 32nd notes)."""
    for i, (nn, v) in enumerate(seq):
        hit(nn, t0 + (start + i * spc) * STEP, v)


def grooveA(t0, base=78, kick=((0, 110), (10, 90)), snare=((4, 104), (12, 108)),
            ghosts=((3, 32), (7, 38), (11, 30)), feel=0, hat_steps=None,
            extra=()):
    """Hi-hat groove with ghosted snare.  ``feel`` lays the snare back."""
    hats(t0, base, hat_steps)
    for st, v in kick:
        hit(KICK, t0 + st * STEP + feel, v)
    for st, v in snare:
        hit(SNARE, t0 + st * STEP + feel, v)
    for st, v in ghosts:
        hit(SNARE, t0 + st * STEP + feel, v, 90)
    for nn, st, v in extra:
        hit(nn, t0 + st * STEP, v)


def grooveB(t0, base=90, kick=((0, 112), (10, 96)), snare=((4, 108), (12, 112)),
            ghosts=((3, 30), (7, 36), (11, 30)), feel=5, bell=(), ohh=(),
            hat_steps=None):
    """Riding groove on the ride cymbal (bell and open-hat substitutions)."""
    steps = list(range(0, 16, 2)) if hat_steps is None else hat_steps
    for st in steps:
        v = base if st % 4 == 0 else base * 0.80
        if st in bell:
            hit(BELL, t0 + st * STEP, v)
        elif st in ohh:
            hit(OHH, t0 + st * STEP, v)
        else:
            hit(RIDE, t0 + st * STEP, v)
    for st, v in kick:
        hit(KICK, t0 + st * STEP + feel, v)
    for st, v in snare:
        hit(SNARE, t0 + st * STEP + feel, v)
    for st, v in ghosts:
        hit(SNARE, t0 + st * STEP + feel, v, 90)


# ----------------------------------------------------------------------
#  the solo
# ----------------------------------------------------------------------
def build():

    # ------------------------------------------------------------------
    #  tempo map: the pulse leans forward in the hot passages and settles
    #  back when the music relaxes.
    # ------------------------------------------------------------------
    tempo(bar(0), 120)
    tempo(bar(4), 124)
    tempo(bar(12), 128)
    tempo(bar(20), 124)
    tempo(bar(28), 132)
    tempo(bar(36), 112)
    tempo(bar(44), 118)
    tempo(bar(46), 122)
    tempo(bar(48), 126)
    tempo(bar(50), 130)
    tempo(bar(52), 136)
    tempo(bar(58), 132)
    tempo(bar(60), 114)
    tempo(bar(62), 104)

    # ==================================================================
    #  1. INTRO  -- bars 0-3
    #  The drummer sits down alone and quietly states Motif A.
    # ==================================================================
    t = bar(0)
    hit(PHH, t, 72)
    hit(PHH, t + 4 * STEP, 64)
    hit(PHH, t + 8 * STEP, 72)
    hit(PHH, t + 12 * STEP, 64)
    hit(RIDE, t, 60)
    hit(RIDE, t + 8 * STEP, 64)
    # four sixteenths of snare carrying into the first downbeat
    run(t, 12, [(SNARE, 40), (SNARE, 50), (SNARE, 62), (SNARE, 78)])

    for b in (1, 2):                       # Motif A, stated
        t = bar(b)
        hats(t, 62, swing=55)              # light shuffle in the hats
        hit(KICK, t, 96)
        hit(KICK, t + 10 * STEP, 78)
        hit(SNARE, t + 4 * STEP, 92)
        hit(SNARE, t + 12 * STEP, 98)
        hit(SNARE, t + 3 * STEP, 26, 80)
        hit(SNARE, t + 7 * STEP, 30, 80)
        hit(SNARE, t + 11 * STEP, 28, 80)

    t = bar(3)                             # Motif A + pickup into section A
    hats(t, 68, steps=[0, 2, 4, 6, 8, 10], swing=55)
    hit(KICK, t, 100)
    hit(KICK, t + 10 * STEP, 84)
    hit(SNARE, t + 4 * STEP, 94)
    hit(SNARE, t + 3 * STEP, 30, 80)
    run(t, 12, [(SNARE, 58), (T_HI, 74), (T_LOMID, 90), (T_LOW, 106)])

    # ==================================================================
    #  2. SECTION A  -- bars 4-11.  Motif A becomes a groove.
    # ==================================================================
    t = bar(4)
    hit(CRASH, t, 114)
    hit(KICK, t, 112)
    grooveA(t, kick=((10, 92),), snare=((4, 104), (12, 108)),
            ghosts=((3, 32), (7, 38), (11, 30)), feel=7)

    t = bar(5)
    grooveA(t, kick=((0, 110), (10, 90)), snare=((4, 104), (12, 108)),
            ghosts=((1, 26), (3, 34), (7, 38), (11, 30), (15, 36)), feel=7)

    t = bar(6)                             # variation: kick doubles + open hat
    grooveA(t, kick=((0, 110), (6, 86), (10, 92)), snare=((4, 106), (12, 110)),
            ghosts=((3, 32),), feel=7, hat_steps=[0, 2, 4, 6, 8, 10, 12],
            extra=((OHH, 14, 76),))

    t = bar(7)                             # short fill into b8
    grooveA(t, kick=((0, 110),), snare=((4, 106),), ghosts=((3, 32),), feel=7,
            hat_steps=[0, 2, 4, 6, 8, 10])
    run(t, 12, [(SNARE, 66), (T_HI, 78), (T_HIMID, 90), (T_LOMID, 102)])

    t = bar(8)
    grooveA(t, kick=((0, 110), (10, 92)), snare=((4, 106), (12, 110)),
            ghosts=((3, 32), (7, 36)), feel=7,
            hat_steps=[0, 2, 4, 6, 8, 10, 12], extra=((OHH, 14, 78),))

    t = bar(9)                             # busier ghosting
    grooveA(t, kick=((0, 110), (6, 88), (10, 92)), snare=((4, 106), (12, 110)),
            ghosts=((1, 26), (3, 32), (7, 38), (11, 30), (15, 36)), feel=7)

    t = bar(10)                            # build: sixteenths on the hat
    for st in range(16):
        v = 66 + 26 * (st / 15.0)
        if st % 4 == 0:
            v += 8
        hit(HH, t + st * STEP, v)
    hit(KICK, t, 110)
    hit(KICK, t + 8 * STEP, 100)
    hit(SNARE, t + 4 * STEP, 108)
    hit(SNARE, t + 12 * STEP, 112)

    t = bar(11)                            # fill carrying into section B
    for st in (0, 2, 4, 6):
        hit(HH, t + st * STEP, 84 - st)
    hit(KICK, t, 112)
    hit(SNARE, t + 4 * STEP, 108)
    run(t, 8, [(T_HI, 74), (T_HI, 82), (T_HIMID, 90), (T_HIMID, 96),
               (T_LOMID, 100), (T_LOMID, 104), (T_LOW, 108), (T_LOW, 112)])
    hit(CRASH, bar(12), 118)
    hit(KICK, bar(12), 116)

    # ==================================================================
    #  3. SECTION B  -- bars 12-19.  Contrast: ride cymbal, bell, more drive.
    # ==================================================================
    t = bar(12)
    grooveB(t, base=92, kick=((10, 96),), snare=((4, 110), (12, 114)),
            ghosts=((3, 32), (7, 36)), feel=5)

    t = bar(13)
    grooveB(t, base=92, kick=((0, 112), (6, 88), (10, 96)),
            snare=((4, 110), (12, 112)), ghosts=((3, 32), (15, 38)),
            feel=5, bell=(14,))

    t = bar(14)
    grooveB(t, base=92, kick=((0, 112), (10, 96)), snare=((4, 110), (12, 112)),
            ghosts=((3, 32), (7, 36), (11, 30)), feel=5, bell=(6,))

    t = bar(15)                            # fill into b16
    grooveB(t, base=92, kick=((0, 112),), snare=((4, 110),), ghosts=(),
            feel=5, hat_steps=[0, 2, 4, 6])
    run(t, 8, [(SNARE, 72), (SNARE, 78), (T_HI, 86), (T_HI, 92),
               (T_HIMID, 96), (T_LOMID, 102), (T_LOW, 108), (SNARE, 116)])
    hit(CRASH, bar(16), 118)
    hit(KICK, bar(16), 116)

    t = bar(16)                            # the left hand starts to wander
    for st in range(0, 16, 2):
        hit(RIDE, t + st * STEP, 84 if st % 4 == 0 else 68)
    hit(KICK, t, 112)
    hit(KICK, t + 10 * STEP, 96)
    hit(SNARE, t + 4 * STEP, 110)
    hit(SNARE, t + 12 * STEP, 112)
    hit(T_HI, t + 9 * STEP, 70)
    hit(T_HI, t + 11 * STEP, 72)

    t = bar(17)
    for st in range(0, 16, 2):
        hit(RIDE, t + st * STEP, 84 if st % 4 == 0 else 68)
    hit(KICK, t, 112)
    hit(KICK, t + 6 * STEP, 90)
    hit(KICK, t + 10 * STEP, 96)
    hit(SNARE, t + 4 * STEP, 110)
    hit(SNARE, t + 12 * STEP, 112)
    hit(T_HIMID, t + 1 * STEP, 66)
    hit(T_HIMID, t + 3 * STEP, 70)
    hit(T_LOMID, t + 13 * STEP, 74)
    hit(T_LOW, t + 15 * STEP, 82)

    for b, (v0, v1) in ((18, (72, 94)), (19, (96, 118))):   # build to C
        t = bar(b)
        for st in range(16):
            v = v0 + (v1 - v0) * (st / 15.0)
            if st % 4 == 0:
                v += 6
            hit(HH, t + st * STEP, v)
        hit(KICK, t, 112)
        hit(KICK, t + 8 * STEP, 104)
        hit(SNARE, t + 4 * STEP, 110)
        hit(SNARE, t + 12 * STEP, 112)

    # ==================================================================
    #  4. SECTION C  -- bars 20-27.  The hands take over: singles around
    #     the kit, then doubles, then a roll that swells and resolves.
    # ==================================================================
    t = bar(20)                            # Motif H  -- 16th singles descending
    hit(CRASH, t, 118)
    seq = [SNARE, T_HI, T_HIMID, T_LOMID] * 4
    for i, nn in enumerate(seq):
        v = 92 + (10 if i % 4 == 0 else 0) - (4 if i % 2 else 0)
        hit(nn, t + i * STEP, v)
    hit(KICK, t, 114)
    hit(KICK, t + 8 * STEP, 104)
    hit(PHH, t + 4 * STEP, 88)
    hit(PHH, t + 12 * STEP, 90)

    t = bar(21)                            # Motif H, new orchestration
    seq = [SNARE, T_HIMID, T_LOMID, T_LOW,
           T_HIFL, T_LOWFL, SNARE, T_LOW] * 2
    for i, nn in enumerate(seq):
        v = 88 + (12 if i % 4 == 0 else 0)
        hit(nn, t + i * STEP, v)
    hit(KICK, t, 114)
    hit(KICK, t + 10 * STEP, 100)
    hit(PHH, t + 4 * STEP, 88)
    hit(PHH, t + 12 * STEP, 90)

    t = bar(22)                            # doubles / diddles
    dl = []
    for nn in (SNARE, T_HI, T_HIMID, T_LOMID):
        dl += [nn, nn]
    for i, nn in enumerate(dl * 2):
        hit(nn, t + i * STEP, 98 if i % 2 == 0 else 60)
    hit(KICK, t, 114)
    hit(KICK, t + 8 * STEP, 104)
    hit(PHH, t + 4 * STEP, 90)
    hit(PHH, t + 12 * STEP, 92)

    t = bar(23)
    dl = []
    for nn in (T_HI, T_HIMID, T_LOMID, T_LOW):
        dl += [nn, nn]
    for i, nn in enumerate(dl * 2):
        hit(nn, t + i * STEP, 100 if i % 2 == 0 else 62)
    hit(KICK, t, 114)
    hit(KICK, t + 6 * STEP, 96)
    hit(KICK, t + 10 * STEP, 102)
    hit(PHH, t + 4 * STEP, 90)
    hit(PHH, t + 12 * STEP, 92)

    t = bar(24)                            # roll begins to swell
    for i in range(16):
        v = 44 + 30 * (i / 15.0)
        if i % 4 == 0:
            v += 10
        hit(SNARE, t + i * STEP, v, 70)
    hit(KICK, t, 110)
    hit(KICK, t + 8 * STEP, 102)
    hit(PHH, t + 4 * STEP, 88)
    hit(PHH, t + 12 * STEP, 92)

    t = bar(25)                            # the roll tightens to 32nds
    for i in range(32):
        v = 72 + 40 * (i / 31.0)
        hit(SNARE, t + i * 60, v, 50)
    hit(KICK, t, 114)
    hit(KICK, t + 960, 108)

    t = bar(26)                            # roll with the feet joining
    for i in range(16):
        v = 100 if i % 4 == 0 else 78
        hit(SNARE, t + i * STEP, v, 60)
    hit(KICK, t, 116)
    hit(KICK, t + 4 * STEP, 100)
    hit(KICK, t + 8 * STEP, 112)
    hit(KICK, t + 12 * STEP, 104)

    t = bar(27)                            # the fill that resolves into D
    run(t, 0, [(T_HI, 82), (T_HI, 84), (T_HIMID, 88), (T_HIMID, 90),
               (T_LOMID, 94), (T_LOMID, 96), (T_LOW, 100), (T_LOW, 102),
               (T_HIFL, 106), (T_HIFL, 108), (T_LOWFL, 112), (T_LOWFL, 114),
               (SNARE, 116), (SNARE, 118)])
    hit(SPLASH, t + 14 * STEP, 120)
    hit(SNARE, t + 15 * STEP, 124)
    hit(CRASH, bar(28), 122)
    hit(KICK, bar(28), 120)

    # ==================================================================
    #  5. SECTION D  -- bars 28-35.  Full kit, the motif back at power.
    # ==================================================================
    t = bar(28)
    grooveB(t, base=98, kick=((10, 104),), snare=((4, 114), (12, 116)),
            ghosts=((3, 34), (7, 40)), feel=4, bell=(0, 4, 8, 12))

    t = bar(29)
    grooveB(t, base=98, kick=((0, 118), (6, 92), (10, 104)),
            snare=((4, 114), (12, 116)), ghosts=((3, 34), (11, 32), (15, 40)),
            feel=4, bell=(2, 10))

    t = bar(30)
    grooveB(t, base=96, kick=((0, 118), (10, 106)), snare=((4, 114), (12, 118)),
            ghosts=((3, 34), (7, 40), (11, 34)), feel=4,
            hat_steps=[0, 2, 4, 6, 8, 10, 12], ohh=(14,))

    t = bar(31)                            # fill into b32
    grooveB(t, base=96, kick=((0, 118),), snare=((4, 114),), ghosts=(),
            feel=4, hat_steps=[0, 2, 4, 6])
    run(t, 8, [(SNARE, 84), (T_HI, 92), (T_HI, 96), (T_HIMID, 100),
               (T_LOMID, 104), (T_LOW, 108), (T_HIFL, 112), (T_LOWFL, 118)])
    hit(CRASH, bar(32), 122)
    hit(KICK, bar(32), 120)

    t = bar(32)
    grooveB(t, base=98, kick=((10, 104),), snare=((4, 114), (12, 116)),
            ghosts=((3, 34), (7, 40)), feel=4, bell=(0, 8))

    t = bar(33)
    grooveB(t, base=96, kick=((0, 118), (6, 94), (10, 104)),
            snare=((4, 114), (12, 116)), ghosts=((3, 34), (7, 40), (11, 32)),
            feel=4, bell=(14,))

    t = bar(34)                            # build
    for st in range(16):
        v = 78 + 40 * (st / 15.0)
        if st % 4 == 0:
            v += 6
        hit(HH, t + st * STEP, v)
    hit(KICK, t, 118)
    hit(KICK, t + 8 * STEP, 110)
    hit(SNARE, t + 4 * STEP, 114)
    hit(SNARE, t + 12 * STEP, 116)

    t = bar(35)                            # long run around the kit
    run(t, 0, [(SNARE, 86), (SNARE, 88), (T_HI, 92), (T_HI, 94),
               (T_HIMID, 98), (T_HIMID, 100), (T_LOMID, 104), (T_LOMID, 106),
               (T_LOW, 110), (T_LOW, 112), (T_HIFL, 114), (T_HIFL, 116),
               (T_LOWFL, 118), (T_LOWFL, 120)])
    hit(SPLASH, t + 14 * STEP, 122)
    hit(SNARE, t + 15 * STEP, 124)
    hit(CRASH2, bar(36), 110)
    hit(KICK, bar(36), 108)

    # ==================================================================
    #  6. SECTION E  -- bars 36-43.  Release.  Sparse, half time, latin
    #     colours, ghost notes -- the kit breathes.
    # ==================================================================
    t = bar(36)
    hit(KICK, t, 100)
    hit(KICK, t + 8 * STEP, 92)
    hit(PHH, t + 4 * STEP, 80)
    hit(PHH, t + 12 * STEP, 82)
    for st in (2, 6, 10, 14):
        hit(COWBELL, t + st * STEP, 72)

    t = bar(37)                            # side stick + ride bell
    hit(KICK, t, 100)
    hit(KICK, t + 10 * STEP, 84)
    hit(STICK, t + 4 * STEP, 96)
    hit(STICK, t + 12 * STEP, 100)
    for st in (0, 3, 6, 8, 11, 14):
        hit(BELL, t + st * STEP, 72)

    t = bar(38)
    hit(KICK, t, 100)
    hit(KICK, t + 8 * STEP, 88)
    hit(SNARE, t + 4 * STEP, 96)
    hit(SNARE, t + 12 * STEP, 100)
    hit(SNARE, t + 15 * STEP, 34, 80)
    for st in (2, 6, 10, 14):
        hit(CONGA_O, t + st * STEP, 76)
    hit(CONGA_L, t + 7 * STEP, 70)
    hit(CONGA_L, t + 13 * STEP, 68)

    t = bar(39)                            # bongo call
    for st, nn, v in ((0, BONGO_H, 84), (1, BONGO_L, 70), (3, BONGO_H, 76),
                      (4, BONGO_H, 86), (6, BONGO_L, 72), (8, BONGO_H, 84),
                      (9, BONGO_L, 68), (11, BONGO_H, 76), (12, BONGO_H, 88),
                      (14, BONGO_L, 72)):
        hit(nn, t + st * STEP, v)
    hit(KICK, t, 100)
    hit(KICK, t + 10 * STEP, 86)

    t = bar(40)                            # brushes-like, very soft
    hit(KICK, t, 92)
    hit(KICK, t + 8 * STEP, 84)
    hit(SNARE, t + 4 * STEP, 88)
    hit(SNARE, t + 12 * STEP, 92)
    for st in (2, 3, 6, 7, 10, 11, 14, 15):
        hit(SNARE, t + st * STEP, 28, 70)
    for st in (0, 4, 8, 12):
        hit(PHH, t + st * STEP, 70)

    t = bar(41)
    hit(KICK, t, 96)
    hit(KICK, t + 10 * STEP, 86)
    hit(SNARE, t + 4 * STEP, 92)
    hit(SNARE, t + 12 * STEP, 96)
    for st in (1, 3, 6, 7, 10, 11, 13, 15):
        hit(SNARE, t + st * STEP, 30, 70)
    for st in (0, 2, 4, 6, 8, 10, 12, 14):
        hit(RIDE, t + st * STEP, 74 if st % 4 == 0 else 66)

    t = bar(42)                            # start to rebuild
    for st in range(0, 16, 2):
        hit(HH, t + st * STEP, 72 if st % 4 == 0 else 58)
    hit(KICK, t, 104)
    hit(KICK, t + 10 * STEP, 88)
    hit(SNARE, t + 4 * STEP, 100)
    hit(SNARE, t + 12 * STEP, 104)
    hit(SNARE, t + 7 * STEP, 32, 80)
    hit(SNARE, t + 15 * STEP, 34, 80)

    t = bar(43)
    for st in range(12):
        v = 74 + 24 * (st / 11.0)
        if st % 4 == 0:
            v += 6
        hit(HH, t + st * STEP, v)
    hit(KICK, t, 106)
    hit(KICK, t + 8 * STEP, 96)
    hit(SNARE, t + 4 * STEP, 104)
    hit(SNARE, t + 12 * STEP, 108)
    run(t, 12, [(T_HI, 90), (T_HIMID, 96), (T_LOMID, 104), (SNARE, 112)])

    # ==================================================================
    #  7. SECTION F  -- bars 44-51.  The build: the pulse pushes forward
    #     bar by bar and a roll swells into the climax.
    # ==================================================================
    t = bar(44)
    hit(CRASH, t, 112)
    hit(KICK, t, 110)
    hats(t, 86)
    hit(KICK, t + 10 * STEP, 92)
    hit(SNARE, t + 4 * STEP, 106)
    hit(SNARE, t + 12 * STEP, 110)
    hit(SNARE, t + 3 * STEP, 32, 80)
    hit(SNARE, t + 7 * STEP, 36, 80)
    hit(SNARE, t + 11 * STEP, 30, 80)

    t = bar(45)
    hats(t, 86)
    hit(KICK, t, 110)
    hit(KICK, t + 6 * STEP, 88)
    hit(KICK, t + 10 * STEP, 94)
    hit(SNARE, t + 4 * STEP, 106)
    hit(SNARE, t + 12 * STEP, 110)
    hit(SNARE, t + 3 * STEP, 32, 80)
    hit(SNARE, t + 15 * STEP, 38, 80)

    t = bar(46)                            # bell takes over
    for st in range(0, 16, 2):
        hit(BELL, t + st * STEP, 92 if st % 4 == 0 else 76)
    hit(KICK, t, 112)
    hit(KICK, t + 10 * STEP, 100)
    hit(SNARE, t + 4 * STEP, 110)
    hit(SNARE, t + 12 * STEP, 112)
    hit(T_HI, t + 7 * STEP, 72)
    hit(T_HI, t + 15 * STEP, 76)

    t = bar(47)
    for st in range(0, 16, 2):
        hit(BELL, t + st * STEP, 94 if st % 4 == 0 else 78)
    hit(KICK, t, 112)
    hit(KICK, t + 6 * STEP, 92)
    hit(KICK, t + 10 * STEP, 100)
    hit(SNARE, t + 4 * STEP, 110)
    hit(SNARE, t + 12 * STEP, 112)
    hit(T_HIMID, t + 1 * STEP, 74)
    hit(T_LOMID, t + 3 * STEP, 78)
    hit(T_LOW, t + 13 * STEP, 84)
    hit(T_LOW, t + 15 * STEP, 90)

    t = bar(48)                            # Motif H again, rising
    seq = [SNARE, T_HI, T_HIMID, T_LOMID] * 4
    for i, nn in enumerate(seq):
        v = 88 + 14 * (i / 15.0) + (10 if i % 4 == 0 else 0)
        hit(nn, t + i * STEP, v)
    hit(KICK, t, 114)
    hit(KICK, t + 8 * STEP, 106)
    hit(PHH, t + 4 * STEP, 92)
    hit(PHH, t + 12 * STEP, 94)

    t = bar(49)
    seq = [SNARE, T_HIMID, T_LOMID, T_LOW, T_HIFL, T_LOWFL] * 2
    seq += [SNARE, T_HI, T_HIMID, T_LOMID]
    for i, nn in enumerate(seq):
        v = 96 + 20 * (i / 15.0) + (10 if i % 4 == 0 else 0)
        hit(nn, t + i * STEP, v)
    hit(KICK, t, 116)
    hit(KICK, t + 10 * STEP, 108)
    hit(PHH, t + 4 * STEP, 92)
    hit(PHH, t + 12 * STEP, 94)

    t = bar(50)                            # the roll starts to grow
    for i in range(16):
        v = 60 + 30 * (i / 15.0)
        if i % 4 == 0:
            v += 8
        hit(SNARE, t + i * STEP, v, 70)
    hit(KICK, t, 114)
    hit(KICK, t + 8 * STEP, 106)
    hit(PHH, t + 4 * STEP, 90)
    hit(PHH, t + 12 * STEP, 92)

    t = bar(51)                            # roll at 32nds, roaring
    for i in range(32):
        v = 76 + 44 * (i / 31.0)
        hit(SNARE, t + i * 60, v, 50)
    hit(KICK, t, 118)
    hit(KICK, t + 960, 112)
    hit(KICK, t + 1440, 116)

    # ==================================================================
    #  8. SECTION G  -- bars 52-59.  Climax.
    # ==================================================================
    t = bar(52)
    hit(CRASH, t, 124)
    hit(KICK, t, 122)
    grooveB(t, base=104, kick=((10, 108),), snare=((4, 118), (12, 120)),
            ghosts=((3, 36), (7, 42)), feel=4, bell=(0, 4, 8, 12))

    t = bar(53)
    grooveB(t, base=104, kick=((0, 122), (6, 96), (10, 108)),
            snare=((4, 118), (12, 120)), ghosts=((3, 36), (11, 34), (15, 42)),
            feel=4, bell=(2, 10))

    t = bar(54)
    grooveB(t, base=102, kick=((0, 122), (10, 110)), snare=((4, 118), (12, 122)),
            ghosts=((3, 36), (7, 42), (11, 34)), feel=4,
            hat_steps=[0, 2, 4, 6, 8, 10, 12], ohh=(14,))

    t = bar(55)                            # fill into b56
    grooveB(t, base=102, kick=((0, 122),), snare=((4, 118),), ghosts=(),
            feel=4, hat_steps=[0, 2, 4, 6])
    run(t, 8, [(SNARE, 90), (T_HI, 96), (T_HI, 100), (T_HIMID, 104),
               (T_LOMID, 108), (T_LOW, 112), (T_HIFL, 116), (T_LOWFL, 122)])
    hit(CRASH, bar(56), 124)
    hit(KICK, bar(56), 122)

    t = bar(56)
    grooveB(t, base=104, kick=((10, 108),), snare=((4, 118), (12, 120)),
            ghosts=((3, 36), (7, 42)), feel=4, bell=(2, 6, 10, 14))

    t = bar(57)                            # Motif H at full tilt
    seq = [SNARE, T_HI, T_HIMID, T_LOMID] * 4
    for i, nn in enumerate(seq):
        hit(nn, t + i * STEP, 104 + (12 if i % 4 == 0 else 0))
    hit(KICK, t, 122)
    hit(KICK, t + 8 * STEP, 114)
    hit(PHH, t + 4 * STEP, 98)
    hit(PHH, t + 12 * STEP, 100)

    t = bar(58)                            # doubles, wide open
    dl = []
    for nn in (SNARE, T_HI, T_HIMID, T_LOMID):
        dl += [nn, nn]
    for i, nn in enumerate(dl * 2):
        hit(nn, t + i * STEP, 110 if i % 2 == 0 else 70)
    hit(KICK, t, 122)
    hit(KICK, t + 8 * STEP, 114)
    hit(PHH, t + 4 * STEP, 98)
    hit(PHH, t + 12 * STEP, 100)

    t = bar(59)                            # last run, then let go
    run(t, 0, [(T_HI, 96), (T_HI, 98), (T_HIMID, 102), (T_HIMID, 104),
               (T_LOMID, 108), (T_LOMID, 110), (T_LOW, 114), (T_LOW, 116),
               (T_HIFL, 118), (T_HIFL, 120), (T_LOWFL, 122), (T_LOWFL, 124)])
    hit(KICK, t, 122)
    hit(KICK, t + 8 * STEP, 114)
    hit(SNARE, t + 12 * STEP, 126)
    hit(SNARE, t + 13 * STEP, 100, 70)
    hit(SNARE, t + 14 * STEP, 120)
    hit(SNARE, t + 15 * STEP, 96, 70)

    # ==================================================================
    #  9. OUTRO  -- bars 60-63.  Motif A comes home, slow and settled.
    # ==================================================================
    t = bar(60)
    hit(CRASH, t, 116)
    hit(KICK, t, 112)
    hats(t, 84)
    hit(KICK, t + 10 * STEP, 90)
    hit(SNARE, t + 4 * STEP, 108)
    hit(SNARE, t + 12 * STEP, 112)
    hit(SNARE, t + 3 * STEP, 34, 80)
    hit(SNARE, t + 7 * STEP, 38, 80)
    hit(SNARE, t + 11 * STEP, 30, 80)

    t = bar(61)                            # the theme, with an open hat
    hats(t, 84, steps=[0, 2, 4, 6, 8, 10, 12])
    hit(KICK, t, 110)
    hit(KICK, t + 10 * STEP, 90)
    hit(SNARE, t + 4 * STEP, 108)
    hit(SNARE, t + 12 * STEP, 112)
    hit(SNARE, t + 3 * STEP, 34, 80)
    hit(SNARE, t + 15 * STEP, 40, 80)
    hit(OHH, t + 14 * STEP, 82)

    t = bar(62)                            # final fill
    hats(t, 82, steps=[0, 2, 4, 6])
    hit(KICK, t, 108)
    hit(KICK, t + 10 * STEP, 88)
    hit(SNARE, t + 4 * STEP, 104)
    hit(SNARE, t + 3 * STEP, 34, 80)
    run(t, 8, [(SNARE, 80), (T_HI, 88), (T_HIMID, 96), (T_LOMID, 104),
               (T_LOW, 110), (T_HIFL, 114), (T_LOWFL, 118), (SNARE, 124)])

    t = bar(63)                            # the landing
    hit(CRASH, t, 126, 1920)
    hit(KICK, t, 124)
    hit(SNARE, t + 4 * STEP, 118)
    hit(T_HI, t + 8 * STEP, 100)
    hit(T_LOMID, t + 9 * STEP, 88)
    hit(T_LOW, t + 10 * STEP, 104)
    hit(SNARE, t + 12 * STEP, 116)
    hit(CRASH2, t + 14 * STEP, 122, 2880)
    hit(KICK, t + 14 * STEP, 118)


# ----------------------------------------------------------------------
#  diagnostics
# ----------------------------------------------------------------------
def check_playability():
    """Returns (max simultaneous hands, max simultaneous feet)."""
    by_tick = {}
    for (t, note, dur, vel) in EVENTS:
        by_tick.setdefault(t, []).append(note)
    worst_h = worst_f = 0
    for notes in by_tick.values():
        h = sum(1 for n in notes if n not in FOOT_NOTES)
        f = sum(1 for n in notes if n in FOOT_NOTES)
        worst_h = max(worst_h, h)
        worst_f = max(worst_f, f)
    return worst_h, worst_f


def total_seconds():
    ts = sorted(TEMPOS)
    end_all = max(t + d for (t, n, d, v) in EVENTS)
    total = 0.0
    for i, (tick, bpm) in enumerate(ts):
        nxt = ts[i + 1][0] if i + 1 < len(ts) else end_all
        total += (nxt - tick) / float(TPB) * 60.0 / bpm
    return total


# ----------------------------------------------------------------------
#  MIDI writing
# ----------------------------------------------------------------------
def write_midi(path='solo.mid'):
    mid = MidiFile(type=1, ticks_per_beat=TPB)

    # --- conductor track: tempo map + time signature -------------------
    ttrack = MidiTrack()
    mid.tracks.append(ttrack)
    ttrack.append(MetaMessage('track_name', name='Drum Solo', time=0))
    ttrack.append(MetaMessage('time_signature', numerator=4, denominator=4,
                              time=0))
    last = 0
    for tick, bpm in sorted(TEMPOS):
        dt = tick - last
        if dt < 0:
            dt = 0
        ttrack.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm),
                                  time=dt))
        last = tick
    ttrack.append(MetaMessage('end_of_track', time=0))

    # --- drum track ----------------------------------------------------
    ntrack = MidiTrack()
    mid.tracks.append(ntrack)
    ntrack.append(MetaMessage('track_name', name='Drums', time=0))

    evs = []
    for (t, note, dur, vel) in EVENTS:
        evs.append((t, 1, note, vel))          # note on
        evs.append((t + dur, 0, note, 0))      # note off (vel 0 on ch 10)
    evs.sort()                                 # offs before ons at same tick

    last = 0
    for tick, _order, note, vel in evs:
        dt = tick - last
        if dt < 0:
            dt = 0
        ntrack.append(Message('note_on', note=note, velocity=vel,
                              channel=9, time=dt))
        last = tick
    ntrack.append(MetaMessage('end_of_track', time=0))

    mid.save(path)


def main():
    build()
    hands, feet = check_playability()
    if hands > 2 or feet > 2:
        print('WARNING: unplayable moment (hands=%d, feet=%d)' % (hands, feet))
    write_midi('solo.mid')
    print('solo.mid written: %d events, %.1f seconds'
          % (len(EVENTS), total_seconds()))


if __name__ == '__main__':
    main()
