#!/usr/bin/env python3
"""
drum_solo.py -- writes a two minute General MIDI drum solo to solo.mid

Channel 10 (GM percussion).  Everything is deterministic: the same bytes are
produced on every run (no randomness anywhere).

Form (55 bars of 4/4, ~119 s)

  bars  0- 3  intro     the motif, stated quietly, growing roll into...
  bars  4-13  A         the main groove: swung ride, laid back snare, ghosts
  bars 14-21  B         contrast: hi-hat driven, syncopated kick, backbeat
  bars 22-26  break     release: very quiet, ghost notes, hands on congas
  bars 27-36  build     layers pile up, sustained crescendo
  bars 37-46  climax    fast + dense, the motif hammered out, big fills
  bars 47-54  ending    recapitulation of the groove, slow final statement

Feel: the ride/hat push slightly ahead of the beat, the snare lays back a
little further, ghost notes lay back most of all -- a fixed, deliberate
placement rather than random jitter.  Swing ratio is fixed per section.

Playability: never more than two hands + two feet at the same instant.
"""

import math

from mido import MidiFile, MidiTrack, Message, MetaMessage

# --------------------------------------------------------------------- setup
PPQ = 480                      # ticks per quarter note
CH = 9                         # MIDI channel 10 (zero based)

# ------------------------------------------------------ General MIDI pitches
KICK    = 36                   # bass drum 1
KICK2   = 35                   # acoustic bass drum
STICK   = 37                   # side stick
SNARE   = 38                   # acoustic snare
CLAP    = 39
ESNARE  = 40
FLR_L   = 41                   # low floor tom
HHC     = 42                   # closed hi-hat
FLR_H   = 43                   # high floor tom
HHP     = 44                   # pedal hi-hat
TL      = 45                   # low tom
HHO     = 46                   # open hi-hat
TLM     = 47                   # low-mid tom
THM     = 48                   # hi-mid tom
CRASH1  = 49
TH      = 50                   # high tom
RIDE    = 51
CHINA   = 52
BELL    = 53                   # ride bell
TAMB    = 54
SPLASH  = 55
COWBELL = 56
CRASH2  = 57
VIBRA   = 58
RIDE2   = 59
BONGO_H = 60
BONGO_L = 61
CONGA_M = 62
CONGA_O = 63                   # open conga
CONGA_L = 64                   # low conga
TIMB_H  = 65
TIMB_L  = 66
AGOGO_H = 67
AGOGO_L = 68
CABASA  = 69
MARACAS = 70
CLAVES  = 75
WOOD_H  = 76
WOOD_L  = 77
TRI_M   = 80
TRI_O   = 81

# ------------------------------------------------------------- the time line
# (start beat, end beat, tempo)
SEC = ((0, 16, 96),
       (16, 88, 116),
       (88, 108, 92),
       (108, 148, 116),
       (148, 188, 132),
       (188, 212, 100),
       (212, 220, 84))

TEMPO_MAP = ((0, 96), (16, 116), (88, 92), (108, 116),
             (148, 132), (188, 100), (212, 84))

# --------------------------------------------------------- feel (in beats)
LAG_RIDE  = -0.006             # right hand pushes a hair
LAG_HAT   = -0.008
LAG_SNARE = 0.012              # backbeat lays back
LAG_GHOST = 0.020              # ghosts lay back more
LAG_TOM   = 0.004
LAG_KICK  = 0.000
LAG_CRASH = 0.000

EV = []                        # (tick, note, velocity)


# ------------------------------------------------------------------ helpers
def hit(beat, note, vel):
    EV.append((int(round(beat * PPQ)), note,
               max(1, min(127, int(round(vel))))))


def sw(p, r):
    """Warp a straight position into a swung one (r = offbeat eighth place)."""
    b = math.floor(p)
    f = p - b
    if f < 0.5:
        f = f * r * 2.0
    else:
        f = r + (f - 0.5) * (1.0 - r) * 2.0
    return b + f


def P(pos, note, vel, r, lag=0.0):
    hit(sw(pos, r) + lag, note, vel)


def ride_comp(base, r, v=1.0):
    """The classic swung ride pattern: quarter notes + the 'a' of 2 and 4."""
    for o, vv in ((0.0, 100), (1.0, 74), (1.5, 86),
                  (2.0, 92), (3.0, 74), (3.5, 86)):
        P(base + o, RIDE, vv * v, r, LAG_RIDE)


def pedal_hat(base, r, v=66):
    for o in (1, 3):
        P(base + o, HHP, v, r, LAG_HAT)


def feather(base, r, v=34):
    """Soft quarter notes on the bass drum -- the jazz pulse."""
    for o in (0, 1, 2, 3):
        P(base + o, KICK, v, r, LAG_KICK)


# ghost-note comping figures (offset inside the bar, velocity)
GHOSTS = (
    ((0.50, 30), (1.75, 34), (2.50, 28), (3.25, 32)),
    ((0.25, 26), (0.75, 32), (2.75, 30), (3.50, 26)),
    ((1.25, 28), (2.25, 34), (3.25, 30), (3.75, 24)),
    ((0.50, 32), (1.50, 28), (2.75, 34), (0.75, 22)),
)


def snare_comp(base, r, idx, bb=(98, 102), g=1.0):
    P(base + 1, SNARE, bb[0] * g, r, LAG_SNARE)
    P(base + 3, SNARE, bb[1] * g, r, LAG_SNARE)
    for o, v in GHOSTS[idx % len(GHOSTS)]:
        P(base + o, SNARE, v * g, r, LAG_GHOST)


def tom_run(base, r, offs, notes, vels, lag=LAG_TOM):
    for o, n, v in zip(offs, notes, vels):
        P(base + o, n, v, r, lag)


MOTIF_OFFS = (0.0, 0.75, 1.25, 1.75)      # "1 . a  ta" inside two beats
MOTIF_VELS = (100.0, 78.0, 86.0, 72.0)


def motif_m(base, r, notes=(TH, THM, TLM, TL), v=1.0):
    """The motif: a four stroke run down the toms."""
    tom_run(base, r, MOTIF_OFFS, notes, [x * v for x in MOTIF_VELS])


# -------------------------------------------------------------- the sections
def intro():
    """bars 0-3 -- quiet, states the motif, crescendo roll into the groove."""
    r = 0.55

    # bar 0: motif, low and slow
    hit(0.0, TRI_O, 52)
    hit(0.0, CRASH1, 58)
    hit(0.0, KICK, 84)
    motif_m(0.0, r, (TH, THM, TLM, TL), 0.92)
    for o, v in ((2.0, 74), (2.5, 60), (3.0, 78), (3.5, 58)):
        P(o, BELL, v, r, LAG_RIDE)
    hit(3.0, KICK, 70)

    # bar 1: same motif, answered lower
    motif_m(4.0, r, (THM, TLM, TL, FLR_H), 0.88)
    for o, v in ((6.0, 74), (6.5, 60), (7.0, 78), (7.5, 58)):
        P(o, BELL, v, r, LAG_RIDE)
    hit(6.0, KICK, 74)

    # bar 2: fragment
    tom_run(8.0, r, (0.0, 0.75), (TH, THM), (86, 72))
    P(9.0, BELL, 70, r, LAG_RIDE)
    P(9.5, BELL, 58, r, LAG_RIDE)
    P(10.0, SNARE, 68, r, LAG_SNARE)
    P(10.5, SNARE, 36, r, LAG_GHOST)
    hit(11.0, KICK, 82)
    P(11.5, BELL, 62, r, LAG_RIDE)

    # bar 3: crescendo roll
    tom_run(12.0, r, (0.0, 0.75, 1.25), (TH, THM, TLM), (76, 70, 66))
    vels = (48, 55, 62, 70, 78, 88, 100, 112)
    for i, o in enumerate((2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75)):
        P(12.0 + o, SNARE, vels[i], r, LAG_SNARE)
    hit(16.0, CRASH1, 112)
    hit(16.0, KICK, 104)


def section_a():
    """bars 4-13 -- the main groove."""
    r = 0.62

    for i in range(8):
        b = 16 + 4 * i
        if i in (0, 4):
            hit(b, CRASH1, 104 if i == 0 else 96)
        ride_comp(b, r, 0.92 + 0.010 * i)
        pedal_hat(b, r, 66)
        feather(b, r, 34)
        snare_comp(b, r, i, (96, 102))
        if i in (3, 5, 7):
            P(b + 2.5, KICK, 88, r, LAG_KICK)          # kick "bomb"
        if i == 6:
            P(b + 3.5, THM, 92, r, LAG_TOM)            # tom accent
        if i == 7:
            P(b + 3.25, TH, 86, r, LAG_TOM)
            P(b + 3.5, THM, 90, r, LAG_TOM)

    # bar 12: groove with a pick-up
    b = 48
    for o, v in ((0.0, 100), (1.0, 76), (1.5, 86), (2.0, 92)):
        P(b + o, RIDE, v, r, LAG_RIDE)
    pedal_hat(b, r, 68)
    P(b + 1, SNARE, 100, r, LAG_SNARE)
    P(b + 1.75, SNARE, 34, r, LAG_GHOST)
    hit(b + 2, KICK, 88)
    tom_run(b, r, (3.0, 3.25, 3.5, 3.75),
            (TH, THM, TLM, TL), (92, 96, 100, 104))

    # bar 13: full bar fill into section B
    b = 52
    seq = ((0.00, SNARE, 84), (0.25, SNARE, 88),
           (0.50, TH, 88), (0.75, THM, 92),
           (1.00, TLM, 94), (1.25, TL, 96),
           (1.50, FLR_H, 98), (1.75, FLR_L, 100),
           (2.00, TLM, 100), (2.25, THM, 104),
           (2.50, TH, 106), (2.75, SNARE, 108),
           (3.00, SNARE, 110), (3.25, SNARE, 112),
           (3.50, SNARE, 114), (3.75, SNARE, 116))
    for o, n, v in seq:
        P(b + o, n, v, r, LAG_SNARE if n == SNARE else LAG_TOM)
    hit(56.0, CRASH2, 110)
    hit(56.0, KICK, 108)


def section_b():
    """bars 14-21 -- contrast: hi-hat driven, syncopated kick."""
    r = 0.62
    kicks = (
        ((0.00, 96), (2.50, 88)),
        ((0.00, 98), (1.50, 78), (2.50, 88), (3.50, 74)),
        ((0.00, 96), (1.75, 74), (2.50, 90)),
        ((0.00, 98), (2.50, 88), (3.75, 80)),
    )
    for i in range(7):
        b = 56 + 4 * i
        if i == 4:
            hit(b, CRASH1, 100)
        for o in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
            acc = (o == int(o))
            vv = 88 if o == 0.0 else (76 if acc else 58)
            P(b + o, HHC, vv, r, LAG_HAT)
        P(b + 1, SNARE, 100, r, LAG_SNARE)
        P(b + 3, SNARE, 104, r, LAG_SNARE)
        for o, v in GHOSTS[(i + 2) % 4]:
            P(b + o, SNARE, v, r, LAG_GHOST)
        for o, v in kicks[i % 4]:
            P(b + o, KICK, v, r, LAG_KICK)
        if i in (4, 5):                                  # latin colour
            for o in (0.5, 1.5, 2.5, 3.5):
                P(b + o, COWBELL, 68, r, LAG_HAT)
        if i == 6:
            P(b + 3.25, THM, 86, r, LAG_TOM)
            P(b + 3.5, TH, 92, r, LAG_TOM)

    # bar 21: fill
    b = 84
    for o in (0.0, 0.5, 1.0, 1.5):
        P(b + o, HHC, 84 if o == 0.0 else 60, r, LAG_HAT)
    P(b + 1, SNARE, 100, r, LAG_SNARE)
    seq = ((2.00, SNARE, 96), (2.25, TL, 84), (2.50, TLM, 88),
           (2.75, THM, 92), (3.00, TH, 96), (3.25, SNARE, 100),
           (3.50, SNARE, 104), (3.75, SNARE, 108))
    for o, n, v in seq:
        P(b + o, n, v, r, LAG_SNARE if n == SNARE else LAG_TOM)


def break_sec():
    """bars 22-26 -- the release: quiet, sparse, ghost notes, congas."""
    r = 0.58

    # bar 22: barely there
    hit(88.0, KICK, 62)
    P(88.75, SNARE, 26, r, LAG_GHOST)
    P(89.00, SNARE, 72, r, LAG_SNARE)
    P(90.00, BELL, 58, r, LAG_RIDE)
    P(90.75, SNARE, 24, r, LAG_GHOST)
    P(91.00, SNARE, 76, r, LAG_SNARE)
    P(91.50, SNARE, 28, r, LAG_GHOST)

    # bar 23: soft hats, motif fragment low in the toms
    b = 92
    for o in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
        P(b + o, HHC, 46 if o == int(o) else 34, r, LAG_HAT)
    P(b + 0.25, SNARE, 28, r, LAG_GHOST)
    P(b + 1.75, SNARE, 30, r, LAG_GHOST)
    P(b + 2.00, SNARE, 74, r, LAG_SNARE)
    tom_run(b, r, (3.0, 3.5), (TH, TLM), (60, 56))

    # bar 24: hands move to the congas
    b = 96
    hit(b + 0.0, KICK, 66)
    for o, n, v in ((0.50, CONGA_L, 52), (1.00, CONGA_O, 56),
                    (1.50, CONGA_L, 48), (2.00, CONGA_O, 58),
                    (2.50, CONGA_L, 50), (3.00, CONGA_O, 60),
                    (3.50, CONGA_L, 54)):
        P(b + o, n, v, r, 0.004)

    # bar 25: the roll starts creeping back
    b = 100
    for o, v in ((0.0, 40), (0.5, 34), (1.0, 44), (1.5, 36)):
        P(b + o, HHC, v, r, LAG_HAT)
    P(b + 1.0, SNARE, 66, r, LAG_SNARE)
    for i, o in enumerate((2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75)):
        P(b + o, SNARE, 44 + i * 5, r, LAG_SNARE)

    # bar 26: crescendo up into the build
    b = 104
    seq = ((0.00, SNARE, 70), (0.25, SNARE, 74),
           (0.50, SNARE, 78), (0.75, SNARE, 82),
           (1.00, TL, 84), (1.25, TLM, 88),
           (1.50, THM, 90), (1.75, TH, 92),
           (2.00, SNARE, 94), (2.25, SNARE, 98),
           (2.50, SNARE, 100), (2.75, SNARE, 104),
           (3.00, TH, 100), (3.25, THM, 104),
           (3.50, TLM, 108), (3.75, TL, 112))
    for o, n, v in seq:
        P(b + o, n, v, r, LAG_SNARE if n == SNARE else LAG_TOM)
    hit(108.0, CRASH1, 112)
    hit(108.0, KICK, 106)


def build_sec():
    """bars 27-36 -- layers pile up, the crescendo builds."""
    r = 0.62
    for i in range(9):
        b = 108 + 4 * i
        g = 0.74 + 0.028 * i                 # 0.74 .. 0.96
        if i == 6:
            hit(b, CRASH2, 96)
        if i < 3:                            # hats, medium
            for o in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
                acc = (o == int(o))
                vv = 84 if o == 0.0 else (68 if acc else 52)
                P(b + o, HHC, vv * g, r, LAG_HAT)
            P(b + 1, SNARE, 88 * g, r, LAG_SNARE)
            P(b + 3, SNARE, 92 * g, r, LAG_SNARE)
            for o, v in GHOSTS[i % 4]:
                P(b + o, SNARE, v * g, r, LAG_GHOST)
            P(b + 0.0, KICK, 92 * g, r, LAG_KICK)
            P(b + 2.5, KICK, 84 * g, r, LAG_KICK)
        elif i < 6:                          # hands to the ride
            ride_comp(b, r, g)
            pedal_hat(b, r, 64 * g)
            P(b + 1, SNARE, 94 * g, r, LAG_SNARE)
            P(b + 3, SNARE, 98 * g, r, LAG_SNARE)
            for o, v in GHOSTS[i % 4]:
                P(b + o, SNARE, v * g, r, LAG_GHOST)
            for o, v in ((0.0, 96), (1.5, 78), (2.5, 88), (3.5, 76)):
                P(b + o, KICK, v * g, r, LAG_KICK)
        else:                                # sixteens on the ride
            for k in range(16):
                o = k * 0.25
                vv = 96 if k % 4 == 0 else (74 if k % 2 == 0 else 60)
                P(b + o, RIDE, vv * g, r, LAG_RIDE)
            P(b + 1, SNARE, 100 * g, r, LAG_SNARE)
            P(b + 3, SNARE, 104 * g, r, LAG_SNARE)
            for o, v in GHOSTS[i % 4]:
                P(b + o, SNARE, v * g, r, LAG_GHOST)
            for o, v in ((0.0, 100), (1.5, 80), (2.5, 92), (3.5, 78)):
                P(b + o, KICK, v * g, r, LAG_KICK)

    # bar 36: rising fill into the climax
    b = 144
    seq = ((0.00, SNARE, 96), (0.25, SNARE, 100),
           (0.50, TLM, 92), (0.75, THM, 96),
           (1.00, TH, 100), (1.25, SNARE, 102),
           (1.50, SNARE, 104), (1.75, SNARE, 106),
           (2.00, TL, 96), (2.25, TLM, 100),
           (2.50, THM, 104), (2.75, TH, 108),
           (3.00, SNARE, 108), (3.25, SNARE, 112),
           (3.50, SNARE, 114), (3.75, SNARE, 118))
    for o, n, v in seq:
        P(b + o, n, v, r, LAG_SNARE if n == SNARE else LAG_TOM)


def climax():
    """bars 37-46 -- fast and dense, the motif hammered out."""
    r = 0.55

    for i in range(8):
        b = 148 + 4 * i
        g = 0.95 + 0.006 * i
        if i == 0:
            hit(b, CRASH1, 114)
        if i == 4:
            hit(b, CRASH2, 112)

        if i < 4:                            # driving sixteens
            for k in range(16):
                o = k * 0.25
                vv = 100 if k % 4 == 0 else (76 if k % 2 == 0 else 64)
                P(b + o, RIDE, vv * g, r, LAG_RIDE)
            P(b + 1, SNARE, 104, r, LAG_SNARE)
            P(b + 3, SNARE, 108, r, LAG_SNARE)
            for o, v in ((0.50, 26), (1.75, 30), (2.50, 28)):
                P(b + o, SNARE, v, r, LAG_GHOST)
            for o, v in ((0.0, 104), (1.5, 84), (2.0, 92),
                         (2.5, 96), (3.5, 82)):
                P(b + o, KICK, v, r, LAG_KICK)

        elif i == 4:                         # motif, stated big
            motif_m(b, r, (TH, THM, TLM, TL), 1.05)
            hit(b, KICK, 108)
            P(b + 2.0, KICK, 100, r, LAG_KICK)
            P(b + 2.5, SNARE, 104, r, LAG_SNARE)
            P(b + 3.0, SNARE, 106, r, LAG_SNARE)
            P(b + 3.5, TLM, 96, r, LAG_TOM)

        elif i == 5:                         # motif, snare answers
            motif_m(b, r, (TH, THM, TLM, TL), 1.0)
            P(b + 2.0, SNARE, 100, r, LAG_SNARE)
            P(b + 2.5, SNARE, 104, r, LAG_SNARE)
            P(b + 3.0, SNARE, 100, r, LAG_SNARE)
            P(b + 3.5, SNARE, 106, r, LAG_SNARE)
            P(b + 0.0, KICK, 106, r, LAG_KICK)
            P(b + 2.5, KICK, 98, r, LAG_KICK)

        elif i == 6:                         # motif in sixteenths
            for k in range(16):
                o = k * 0.25
                n = (TH, THM, TLM, TL)[k % 4]
                P(b + o, n, 96 + (k % 4) * 4, r, LAG_TOM)
            for o in (0.0, 1.0, 2.0, 3.0):
                P(b + o, KICK, 104, r, LAG_KICK)

        else:                                # bar 44: through the kit
            names = (SNARE, SNARE, THM, TH, TLM, TL, THM, TH,
                     SNARE, SNARE, TLM, TL, SNARE, SNARE, SNARE, SNARE)
            for k in range(16):
                n = names[k]
                P(b + k * 0.25, n, 102 + min(k, 8) * 2, r,
                  LAG_SNARE if n == SNARE else LAG_TOM)
            P(b + 0.0, KICK, 108, r, LAG_KICK)
            P(b + 2.0, KICK, 108, r, LAG_KICK)

    # bar 45
    b = 180
    hit(b, CRASH2, 110)
    hit(b, KICK, 108)
    names = (SNARE, SNARE, THM, TH, TLM, TL, SNARE, SNARE,
             TH, THM, TLM, TL, SNARE, THM, TH, TL)
    for k in range(16):
        n = names[k]
        P(b + k * 0.25, n, 100 + (k % 4), r,
          LAG_SNARE if n == SNARE else LAG_TOM)

    # bar 46: final roll into the ending
    b = 184
    names = (SNARE, SNARE, THM, TH, TLM, TL, THM, TH,
             SNARE, SNARE, TLM, TL, SNARE, SNARE, SNARE, SNARE)
    for k in range(16):
        n = names[k]
        P(b + k * 0.25, n, 104 + min(k, 8) * 2, r,
          LAG_SNARE if n == SNARE else LAG_TOM)
    P(b + 0.0, KICK, 110, r, LAG_KICK)
    P(b + 2.0, KICK, 110, r, LAG_KICK)


def ending():
    """bars 47-54 -- the groove returns, then one last slow statement."""
    r = 0.60

    for i in range(6):
        b = 188 + 4 * i
        if i in (0, 3):
            hit(b, CRASH1, 116 if i == 0 else 100)
        ride_comp(b, r, 1.0)
        pedal_hat(b, r, 68)
        snare_comp(b, r, i + 1, (100, 106))
        P(b + 0.0, KICK, 92, r, LAG_KICK)
        P(b + 2.5, KICK, 84, r, LAG_KICK)
        if i == 5:
            P(b + 3.25, SNARE, 104, r, LAG_SNARE)
            P(b + 3.50, SNARE, 108, r, LAG_SNARE)
            P(b + 3.75, SNARE, 112, r, LAG_SNARE)

    # bar 53: the motif, one more time, slow
    b = 212
    motif_m(b, r, (TH, THM, TLM, TL), 1.0)
    P(b + 1.0, SNARE, 96, r, LAG_SNARE)
    P(b + 2.0, SNARE, 100, r, LAG_SNARE)
    P(b + 2.0, KICK, 100, r, LAG_KICK)
    P(b + 3.0, SNARE, 104, r, LAG_SNARE)
    P(b + 3.5, SNARE, 108, r, LAG_SNARE)

    # bar 54: the last word
    b = 216
    hit(b + 0.0, CRASH1, 118)
    hit(b + 0.0, KICK, 112)
    hit(b + 0.0, FLR_L, 100)
    P(b + 1.0, SNARE, 110, r, LAG_SNARE)
    P(b + 1.0, KICK, 98, r, LAG_KICK)
    P(b + 2.0, SNARE, 112, r, LAG_SNARE)
    P(b + 2.0, KICK, 104, r, LAG_KICK)
    hit(b + 3.0, CRASH1, 122)
    hit(b + 3.0, KICK, 116)
    P(b + 3.0, FLR_L, 106, r, LAG_TOM)


def build():
    intro()
    section_a()
    section_b()
    break_sec()
    build_sec()
    climax()
    ending()


# --------------------------------------------------------- time conversions
def tick_to_sec(tick):
    beat = tick / float(PPQ)
    t = 0.0
    for s, e, bpm in SEC:
        if beat <= s:
            break
        seg = min(beat, e)
        t += (seg - s) * 60.0 / bpm
        if beat <= e:
            break
    return t


def sec_to_tick(sec):
    t = 0.0
    for s, e, bpm in SEC:
        seg = (e - s) * 60.0 / bpm
        if sec <= t + seg:
            return int(round((s + (sec - t) * bpm / 60.0) * PPQ))
        t += seg
    return int(round(SEC[-1][1] * PPQ))


def note_dur(note):
    """A sensible ringing time (seconds) for each kind of sound."""
    if note in (HHC, HHP, STICK, CLAVES, MARACAS, CABASA,
                AGOGO_H, AGOGO_L, WOOD_H, WOOD_L, TRI_M):
        return 0.06
    if note in (SNARE, ESNARE, CLAP, KICK, KICK2, CONGA_M,
                BONGO_H, BONGO_L, TIMB_H, TIMB_L):
        return 0.12
    if note in (HHO, TAMB, COWBELL, CONGA_O, CONGA_L, VIBRA, TRI_O):
        return 0.45
    if note in (RIDE, RIDE2, BELL):
        return 0.90
    if note in (CRASH1, CRASH2, CHINA, SPLASH):
        return 2.00
    return 0.45                              # toms etc.


# ------------------------------------------------------------ file assembly
def assemble():
    mid = MidiFile(type=1, ticks_per_beat=PPQ)

    cond = MidiTrack()
    mid.tracks.append(cond)
    cond.append(MetaMessage('track_name', name='drum solo', time=0))
    cond.append(MetaMessage('time_signature', numerator=4, denominator=4,
                            time=0))
    prev = 0
    for beat, bpm in TEMPO_MAP:
        t = int(round(beat * PPQ))
        cond.append(MetaMessage('set_tempo',
                                tempo=int(round(60000000.0 / bpm)),
                                time=t - prev))
        prev = t

    drum = MidiTrack()
    mid.tracks.append(drum)
    drum.append(MetaMessage('track_name', name='drums', time=0))

    # merge accidental duplicates (same note, same tick -> keep the loudest)
    merged = {}
    for t, n, v in EV:
        k = (t, n)
        if k in merged:
            if v > merged[k]:
                merged[k] = v
        else:
            merged[k] = v
    ev = sorted((t, n, v) for (t, n), v in merged.items())

    # add note offs, never letting one cut into the next hit of the same note
    items = []
    last = {}
    for t, n, v in ev:
        off = sec_to_tick(tick_to_sec(t) + note_dur(n))
        if off <= t:
            off = t + 1
        if n in last:
            j = last[n]
            if items[j][3] > t - 1:
                items[j][3] = max(items[j][0] + 1, t - 1)
        last[n] = len(items)
        items.append([t, n, v, off])

    msgs = []
    for t, n, v, off in items:
        msgs.append((t, 1, Message('note_on', note=n, velocity=v, channel=CH)))
        msgs.append((off, 0, Message('note_off', note=n, velocity=0,
                                     channel=CH)))
    msgs.sort(key=lambda x: (x[0], x[1]))

    prev = 0
    for t, _order, m in msgs:
        m.time = t - prev
        prev = t
        drum.append(m)

    drum.append(MetaMessage('end_of_track', time=0))
    return mid


def total_seconds():
    t = 0.0
    for s, e, bpm in SEC:
        t += (e - s) * 60.0 / bpm
    return t


def main():
    build()
    mid = assemble()
    mid.save('solo.mid')
    print('wrote solo.mid  --  %d events, %.1f seconds'
          % (len(EV), total_seconds()))


if __name__ == '__main__':
    main()
