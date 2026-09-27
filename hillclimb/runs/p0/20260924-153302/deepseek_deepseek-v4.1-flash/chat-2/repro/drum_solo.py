#!/usr/bin/env python3
# drum_solo.py
"""
Generates solo.mid -- a two minute General MIDI drum solo on channel 10.

Deterministic: no randomness anywhere, the same file comes out every run.

Structure (54 bars, 4/4):
    0-3    intro            (92 bpm)  sparse, establishes the ride feel
    4-11   theme A          (100)     hi-hat groove, motif stated twice
    12-15  development 1    (102)     ride bell + melodic toms
    16-19  build            (108)     accelerando single strokes -> crash
    20-27  release          (112)     full-power "chorus" groove
    28-33  contrast         (92)      half-time, heavy swing, laid back
    34-41  development 2    (116)     ghost-note funk, cowbell, congas
    42-49  climax           (126)     theme A returns, ride chorus, triplet fill
    50-53  coda             (132)     final blows
"""

import math
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

TPB = 480                 # ticks per beat
CH = 9                    # MIDI channel 10 (mido is 0-based)

# --------------------------------------------------------------- GM drums
KICK2      = 35
KICK       = 36
STICK      = 37
SNARE      = 38
CLAP       = 39
SNARE2     = 40
FLOOR2     = 41
HH         = 42
FLOOR1     = 43
HHP        = 44
TOM_LO     = 45
HH_OPEN    = 46
TOM_MID    = 47
TOM_HI     = 48
CRASH      = 49
TOM_HI2    = 50
RIDE       = 51
CHINA      = 52
RIDE_B     = 53
TAMB       = 54
SPLASH     = 55
COWBELL    = 56
CRASH2     = 57
RIDE2      = 59
CONGA_MUTE = 62
CONGA_OPEN = 63
CONGA_LO   = 64
CLAVES     = 75
WB_HI      = 76
WB_LO      = 77
TRIANGLE   = 81

# ------------------------------------------------- note lengths (ticks)
DUR = {
    KICK: 90, KICK2: 90,
    STICK: 60, SNARE: 140, CLAP: 140, SNARE2: 140,
    FLOOR2: 300, FLOOR1: 300, TOM_LO: 300, TOM_MID: 300,
    TOM_HI: 300, TOM_HI2: 300,
    HH: 150, HHP: 90, HH_OPEN: 480,
    RIDE: 960, RIDE_B: 720, RIDE2: 960,
    CRASH: 1920, CRASH2: 1920, CHINA: 1920, SPLASH: 960,
    TAMB: 240, COWBELL: 240, CLAVES: 160, WB_HI: 160, WB_LO: 160,
    CONGA_MUTE: 160, CONGA_OPEN: 300, CONGA_LO: 300, TRIANGLE: 1200,
}
DEFAULT_DUR = 200

# -------------------------------------- deliberate per-limb placement
# (positive = lays back behind the grid, negative = pushes ahead of it)
FEEL = {
    KICK: -7, KICK2: -7,
    SNARE: 10, SNARE2: 10, STICK: 9, CLAP: 9,
    HH: -2, HHP: -4, HH_OPEN: -2,
    FLOOR2: 5, FLOOR1: 5, TOM_LO: 5, TOM_MID: 6, TOM_HI: 6, TOM_HI2: 6,
    COWBELL: 7, TAMB: 7, CONGA_MUTE: 8, CONGA_OPEN: 8, CONGA_LO: 8,
    CLAVES: 8, WB_HI: 8, WB_LO: 8, TRIANGLE: 10,
    CRASH: 0, CRASH2: 0, CHINA: 0, SPLASH: 0,
    RIDE: 0, RIDE_B: 0, RIDE2: 0,
}

# default velocity per pattern letter
DEFAULT_V = {'X': 116, 'x': 88, 'o': 102, 'd': 68,
             'g': 30, 'p': 46, 'm': 74, 's': 58}

SW = 0        # swing: ticks the off-beat eighth is displaced by
FSHIFT = 0    # global push / lay-back for the current section

notes = []


def set_feel(swing, shift):
    """Set the feel for the following bars."""
    global SW, FSHIFT
    SW = swing
    FSHIFT = shift


def beat_ticks(beats):
    """Musical position (in beats) -> tick, with swing on off-beat eighths."""
    t = beats * TPB
    if SW:
        f = (beats * 2.0) % 2.0
        if abs(f - 1.0) < 1e-9:
            t += SW
    return t


def add(n, tick, vel, dur=None):
    if dur is None:
        dur = DUR.get(n, DEFAULT_DUR)
    t = int(round(tick))
    if t < 0:
        t = 0
    v = int(round(vel))
    v = 1 if v < 1 else (127 if v > 127 else v)
    notes.append([t, n, v, t + int(dur)])


def hit(n, beat, vel, dur=None):
    add(n, beat_ticks(beat) + FEEL.get(n, 0) + FSHIFT, vel, dur)


def play(n, pat, bar, vels=None, dur=None):
    """Play one bar (16 sixteenth slots) of `pat` on instrument `n`."""
    base = bar * 4.0
    vels = vels or {}
    for i, ch in enumerate(pat):
        if ch == '.':
            continue
        hit(n, base + i * 0.25, vels.get(ch, DEFAULT_V.get(ch, 88)), dur)


# ======================================================================
#                              THE SOLO
# ======================================================================

def compose():
    # ------------------------------------------------ PART 1 : INTRO
    set_feel(48, 8)

    # bar 0 -- one hit, then space
    play(CRASH, "X...............", 0, {'X': 104})
    play(KICK,  "x...............", 0, {'x': 100})
    play(HHP,   "x...x...x...x...", 0, {'x': 58})

    # bar 1 -- only the foot and a few ghosts
    play(HHP,   "x...x...x...x...", 1, {'x': 56})
    play(SNARE, ".......g..g...g.", 1, {'g': 26})
    play(KICK,  "........x.......", 1, {'x': 86})

    # bar 2 -- the ride pattern arrives
    play(RIDE,  "X.x.x.x.X.x.x.x.", 2, {'X': 84, 'x': 70})
    play(KICK,  "x.....x.........", 2, {'x': 92})
    play(HHP,   "....x.......x...", 2, {'x': 56})

    # bar 3 -- first fill, down the toms
    play(RIDE,  "x.x.x.x.x.x.....", 3, {'x': 74})
    play(KICK,  "x...............", 3, {'x': 98})
    play(SNARE, "....x...........", 3, {'x': 74})
    for i, (n, v) in enumerate([(TOM_HI, 92), (TOM_MID, 100),
                                (TOM_LO, 108), (FLOOR1, 116)]):
        hit(n, 12 + 3.0 + i * 0.25, v)

    # ------------------------------------------------ PART 2 : THEME A
    set_feel(34, 0)

    def groove_a(bar, hat=HH, hatpat="X.x.x.x.X.x.x.x.", hX=96, hx=80,
                 kick="x.....x...x.....", kv=110,
                 snare="....X.......X...", sX=116, sx=110,
                 ghost=".......g...g..g.", gv=30, crashv=0):
        if crashv:
            play(CRASH, "X...............", bar, {'X': crashv})
        play(hat, hatpat, bar, {'X': hX, 'x': hx, 'o': 100})
        play(KICK, kick, bar, {'x': kv})
        play(SNARE, snare, bar, {'X': sX, 'x': sx})
        if ghost:
            play(SNARE, ghost, bar, {'g': gv})

    groove_a(4, crashv=118)                                    # statement
    groove_a(5, kick="x.....x...x...x.")                        # answer
    groove_a(6, hatpat="XxxxXxxxXxxxXxxx", hX=98, hx=72,
             kick="x..x..x...x.x...")                          # 16ths, push
    groove_a(7, kick="x.....x...x.x...", hatpat="X.x.x.x.X.x.....")
    hit(TOM_HI,  28 + 3.25, 104)
    hit(TOM_MID, 28 + 3.5,  110)
    hit(TOM_LO,  28 + 3.75, 116)

    groove_a(8, crashv=120, ghost=".......g...g.g.g")          # restate
    groove_a(9, kick="x.....x.x.x.....")                        # vary
    groove_a(10, hatpat="XxxxXxxxXxxxXxxx", hX=100, hx=74,
             kick="x..x..x..xx.x...")
    groove_a(11, hatpat="X.x.x.x.X.......", ghost=".......g...g....")
    for i, (n, v) in enumerate([(SNARE, 106), (SNARE, 58), (SNARE, 110),
                                (SNARE, 62), (TOM_HI, 110), (TOM_HI, 64),
                                (TOM_MID, 114), (TOM_LO, 120)]):
        hit(n, 44 + 2.25 + i * 0.25, v)

    # ------------------------------------------------ PART 3 : DEV 1
    set_feel(26, 0)

    play(CRASH,  "X...............", 12, {'X': 112})
    play(RIDE_B, "x.......x.......", 12, {'x': 100})
    play(RIDE,   "..x.x.x...x.x.x.", 12, {'x': 82})
    play(KICK,   "x.....x...x.....", 12, {'x': 112})
    play(SNARE,  "....X.......X...", 12, {'X': 116})
    play(SNARE,  ".......g...g..g.", 12, {'g': 30})

    play(RIDE_B, "x.......x.......", 13, {'x': 100})
    play(RIDE,   "..x.x.x...x.x.x.", 13, {'x': 82})
    play(KICK,   "x.....x...x...x.", 13, {'x': 112})
    play(SNARE,  "....X.......X...", 13, {'X': 116})
    play(SNARE,  ".......g...g..g.", 13, {'g': 30})

    play(TOM_LO, "x.......x.......", 14, {'x': 96})      # melodic toms
    play(TOM_HI, "..x...x...x...x.", 14, {'x': 86})
    play(SNARE,  "....X.......X...", 14, {'X': 112})
    play(SNARE,  ".......g...g....", 14, {'g': 28})
    play(KICK,   "x.....x...x.....", 14, {'x': 112})

    play(TOM_LO, "x.......x.......", 15, {'x': 96})
    play(TOM_HI, "..x...x...x.....", 15, {'x': 86})
    play(SNARE,  "....X.......X...", 15, {'X': 114})
    play(KICK,   "x.....x...x.....", 15, {'x': 112})
    hit(TOM_MID, 60 + 3.25, 106)
    hit(TOM_LO,  60 + 3.5,  112)
    hit(FLOOR1,  60 + 3.75, 120)

    # ------------------------------------------------ PART 4 : BUILD
    set_feel(20, 0)

    play(CRASH, "X...............", 16, {'X': 110})
    play(HH,    "X.x.x.x.X.x.....", 16, {'X': 96, 'x': 78})
    play(KICK,  "x.....x...x.....", 16, {'x': 114})
    play(SNARE, "....X.......X...", 16, {'X': 118})
    play(SNARE, ".......g...g....", 16, {'g': 30})
    for i, v in enumerate((88, 96, 104, 112)):
        hit(SNARE, 64 + 3.0 + i * 0.25, v)

    # bar 17 -- single strokes, accelerating subdivision
    set_feel(12, 0)
    play(KICK, "x.......x.......", 17, {'x': 114})
    for i in range(8):
        hit(SNARE, 68 + i * 0.5, 62 + i * 4)
    for i in range(4):
        hit(SNARE, 68 + 2.0 + i * 0.25, 92 + i * 4)
    for i in range(8):
        hit(SNARE, 68 + 3.0 + i * 0.125, 106 + i * 2)

    # bar 18 -- tom cascade in sixteenths
    set_feel(8, 0)
    cascade = [(TOM_HI, 96), (TOM_HI, 100), (TOM_HI, 104), (TOM_HI, 108),
               (TOM_MID, 100), (TOM_MID, 104), (TOM_MID, 108), (TOM_MID, 112),
               (TOM_LO, 104), (TOM_LO, 108), (TOM_LO, 112), (TOM_LO, 116),
               (FLOOR1, 108), (FLOOR1, 112), (FLOOR1, 116), (FLOOR2, 120)]
    for i, (n, v) in enumerate(cascade):
        hit(n, 72 + i * 0.25, v)
    play(KICK, "x...x...x...x...", 18, {'x': 112})

    # bar 19 -- diagonal across the kit, flam into the downbeat
    for i in range(4):
        hit(SNARE, 76 + i * 0.25, 104 + i * 5)
    for i in range(4):
        hit(TOM_HI, 77 + i * 0.25, 104 + i * 5)
    for i in range(4):
        hit(TOM_MID, 78 + i * 0.25, 108 + i * 5)
    for i in range(3):
        hit(TOM_LO, 79 + i * 0.25, 112 + i * 5)
    hit(TOM_LO, 79 + 0.75, 124)
    hit(KICK,   79 + 0.75, 120)

    # ------------------------------------------------ PART 5 : RELEASE
    set_feel(16, -6)

    def power(bar, hatpat="X.x.x.x.X.x.x.x.", kick="x.....x...x.....",
              ghost=".......g...g..g.", crashv=0, kv=118, crashnote=CRASH):
        if crashv:
            play(crashnote, "X...............", bar, {'X': crashv})
        play(HH, hatpat, bar, {'X': 102, 'x': 86})
        play(KICK, kick, bar, {'x': kv})
        play(SNARE, "....X.......X...", bar, {'X': 122})
        if ghost:
            play(SNARE, ghost, bar, {'g': 32})

    power(20, crashv=124)
    power(21, kick="x.....x...x.x...", hatpat="X.x.x.x.X.x.x...")
    play(HH_OPEN, "..............x.", 21, {'x': 104})
    power(22, hatpat="XxxxXxxxXxxxXxxx")
    play(HHP, "x...............", 22, {'x': 70})          # pedal closes it
    power(23, kick="x.....x.x.x.....", hatpat="X.x.x.x.X.x.....")
    hit(SNARE,   92 + 3.25, 110)
    hit(TOM_HI,  92 + 3.5,  114)
    hit(TOM_MID, 92 + 3.75, 120)

    power(24, crashv=124, kick="x.....x...x...x.")
    power(25, kick="x..x..x...x.x...", hatpat="X.x.x.x.X.x.x...")
    play(HH_OPEN, "..............x.", 25, {'x': 106})
    power(26, hatpat="XxxxXxxxXxxxXxxx", kick="x.....x.x.x.x...")
    play(CRASH2, "........X.......", 26, {'X': 110})
    play(HHP, "x...............", 26, {'x': 70})
    power(27, hatpat="X.x.x.x.X.......", ghost=".......g...g....")
    for i in range(8):
        hit(SNARE, 108 + 2.25 + i * 0.25, 98 + i * 3)

    # ------------------------------------------------ PART 6 : CONTRAST
    set_feel(50, 12)

    play(SPLASH, "X...............", 28, {'X': 94})
    play(KICK,   "x.......x.......", 28, {'x': 96})
    play(RIDE,   "X.x.x.x.X.x.x.x.", 28, {'X': 84, 'x': 70})
    play(SNARE,  "........X.......", 28, {'X': 108})     # half-time backbeat
    play(SNARE,  "....g..g....g.g.", 28, {'g': 26})
    play(HHP,    "..x...x.........", 28, {'x': 52})

    play(RIDE,   "X.x.x.x...x.x.x.", 29, {'X': 84, 'x': 70})
    play(RIDE_B, "........x.......", 29, {'x': 94})
    play(KICK,   "x.....x.........", 29, {'x': 98})
    play(SNARE,  "........X.......", 29, {'X': 110})
    play(SNARE,  "..g..g..g...g.g.", 29, {'g': 24})
    play(HHP,    "x...x...x...x...", 29, {'x': 50})

    play(RIDE_B, "X.x.X.x.X.x.X.x.", 30, {'X': 92, 'x': 74})
    play(KICK,   "x.......x...x...", 30, {'x': 98})
    play(SNARE,  "....g.......g...", 30, {'g': 26})
    play(HHP,    "..x...x...x...x.", 30, {'x': 48})

    play(TOM_MID, "x.......x.......", 31, {'x': 94})      # sparse statement
    play(TOM_HI,  "....x.......x...", 31, {'x': 88})
    play(KICK,    "x.......x.......", 31, {'x': 98})
    play(SNARE,   "........X.......", 31, {'X': 108})
    play(SNARE,   "..............g.", 31, {'g': 28})

    play(RIDE,  "X.x.x.x.X.x.x.x.", 32, {'X': 88, 'x': 74})   # back to time
    play(KICK,  "x.....x...x.....", 32, {'x': 106})
    play(SNARE, "....X.......X...", 32, {'X': 110})
    play(SNARE, ".......g...g..g.", 32, {'g': 28})

    play(SNARE, "X...x...........", 33, {'X': 114, 'x': 72})
    play(KICK,  "x...x...........", 33, {'x': 108})
    for i, (n, v) in enumerate([(TOM_HI, 98), (TOM_HI, 64), (TOM_MID, 102),
                                (TOM_MID, 66), (TOM_LO, 108), (TOM_LO, 70),
                                (FLOOR1, 114), (FLOOR2, 122)]):
        hit(n, 132 + 2.0 + i * 0.25, v)

    # ------------------------------------------------ PART 7 : DEV 2
    set_feel(34, 0)

    def ghostfunk(bar, crashv=0, kv=112):
        if crashv:
            play(CRASH, "X...............", bar, {'X': crashv})
        play(HH, "XxxxXxxxXxxxXxxx", bar, {'X': 94, 'x': 68})
        play(SNARE, "....X.......X...", bar, {'X': 116})
        play(SNARE, ".....g.g..g..g.g", bar, {'g': 26})
        play(KICK, "x.....x...x.....", bar, {'x': kv})
        play(KICK, "..x.........x...", bar, {'x': kv - 16})

    ghostfunk(34, crashv=116)
    ghostfunk(35, kv=116)

    def cowbell_groove(bar, crashv=0):
        if crashv:
            play(CRASH, "X...............", bar, {'X': 114})
        play(COWBELL, "X.x.X.x.X.x.X.x.", bar, {'X': 92, 'x': 72})
        play(SNARE, "....X.......X...", bar, {'X': 116})
        play(SNARE, ".....g.g..g..g.g", bar, {'g': 26})
        play(KICK, "x.....x...x.....", bar, {'x': 114})
        play(KICK, "..x.........x...", bar, {'x': 98})

    cowbell_groove(36, crashv=118)
    cowbell_groove(37)

    def conga_groove(bar, kv=110):
        play(CONGA_OPEN, "x...x...x...x...", bar, {'x': 92})
        play(CONGA_LO,   "..x...x...x...x.", bar, {'x': 88})
        play(KICK,       "x.....x...x.....", bar, {'x': kv})
        play(SNARE,      "....g.......g...", bar, {'g': 28})
        play(HHP,        "x.......x.......", bar, {'x': 52})

    conga_groove(38)
    conga_groove(39, kv=114)
    play(CONGA_MUTE, ".........x......", 39, {'x': 80})

    set_feel(20, 0)
    play(SNARE, "X.x.X.x.X.x.X.x.", 40, {'X': 118, 'x': 76})
    play(SNARE, "...g...g...g...g", 40, {'g': 30})
    play(KICK,  "x.......x.......", 40, {'x': 116})
    play(HHP,   "....x.......x...", 40, {'x': 54})

    set_feel(10, 0)
    for i in range(4):
        hit(SNARE, 164 + i * 0.5, 78 + i * 6)
    for i in range(8):
        hit(SNARE, 164 + 2.0 + i * 0.25, 100 + i * 3)

    # ------------------------------------------------ PART 8 : CLIMAX
    set_feel(22, -5)

    def climax(bar, crashv=0, hatpat="X.x.x.x.X.x.x.x.",
               kick="x.....x...x.....", ghost=".......g...g..g."):
        if crashv:
            play(CRASH, "X...............", bar, {'X': crashv})
        play(HH, hatpat, bar, {'X': 108, 'x': 88})
        play(KICK, kick, bar, {'x': 120})
        play(SNARE, "....X.......X...", bar, {'X': 124})
        if ghost:
            play(SNARE, ghost, bar, {'g': 34})

    climax(42, crashv=126)
    climax(43, kick="x.....x...x.x...")
    climax(44, hatpat="XxxxXxxxXxxxXxxx", kick="x..x..x...x.x...")
    climax(45, hatpat="X.x.x.x.X.x.....", ghost=".......g...g....")
    hit(SNARE,   180 + 3.25, 114)
    hit(TOM_HI,  180 + 3.5,  118)
    hit(TOM_MID, 180 + 3.75, 124)

    # ride chorus
    play(CRASH,  "X...............", 46, {'X': 126})
    play(RIDE_B, "x.......x.......", 46, {'x': 108})
    play(RIDE,   "..x.x.x...x.x.x.", 46, {'x': 92})
    play(KICK,   "x.....x...x...x.", 46, {'x': 120})
    play(SNARE,  "....X.......X...", 46, {'X': 124})
    play(SNARE,  ".......g...g..g.", 46, {'g': 34})

    play(RIDE_B, "x.......x.......", 47, {'x': 108})
    play(RIDE,   "..x.x.x...x.x.x.", 47, {'x': 92})
    play(KICK,   "x..x..x...x.x...", 47, {'x': 120})
    play(SNARE,  "....X.......X...", 47, {'X': 124})
    play(SNARE,  ".......g...g.g.g", 47, {'g': 34})

    climax(48, hatpat="XxxxXxxxXxxxXxxx", kick="x.....x.x.x.x...")
    play(CRASH2, "........X.......", 48, {'X': 112})

    play(KICK, "x.......x.......", 49, {'x': 120})
    triplets = [(SNARE, 112), (SNARE, 60), (TOM_HI, 110), (TOM_HI, 62),
                (TOM_HI, 114), (TOM_HI, 64), (TOM_MID, 114), (TOM_MID, 66),
                (TOM_MID, 118), (TOM_LO, 118), (TOM_LO, 70), (TOM_LO, 122)]
    for i, (n, v) in enumerate(triplets):
        hit(n, 196 + i / 3.0, v)

    # ------------------------------------------------ PART 9 : CODA
    set_feel(18, -5)

    play(CRASH, "X...............", 50, {'X': 127})
    play(HH,    "X.x.x.x.X.x.x.x.", 50, {'X': 110, 'x': 92})
    play(KICK,  "x.....x...x.....", 50, {'x': 122})
    play(SNARE, "....X.......X...", 50, {'X': 126})
    play(SNARE, ".......g...g..g.", 50, {'g': 36})

    play(HH,    "X.x.x.x.X.x.x...", 51, {'X': 110, 'x': 90})
    play(HH_OPEN, "..............x.", 51, {'x': 106})
    play(KICK,  "x..x..x...x.x...", 51, {'x': 122})
    play(SNARE, "....X.......X...", 51, {'X': 126})
    play(SNARE, ".......g...g..g.", 51, {'g': 36})
    play(CRASH2, "...............x", 51, {'x': 106})

    play(KICK, "x.......x.......", 52, {'x': 122})
    for i in range(4):
        hit(SNARE, 208 + i * 0.25, 100 + i * 6)
    for i in range(4):
        hit(TOM_HI, 209 + i * 0.25, 106 + i * 5)
    for i in range(4):
        hit(TOM_MID, 210 + i * 0.25, 110 + i * 5)
    for i in range(3):
        hit(TOM_LO, 211 + i * 0.25, 114 + i * 5)
    hit(FLOOR1, 211 + 0.75, 126)
    hit(KICK,   211 + 0.75, 124)

    # the last bar: two big blows and ring out
    play(CRASH, "X...............", 53, {'X': 127}, dur=2880)
    play(CHINA, "X...............", 53, {'X': 116}, dur=2880)
    play(KICK,  "x...............", 53, {'x': 124})
    play(TOM_LO, "........x.......", 53, {'x': 118})
    play(KICK,   "........x.......", 53, {'x': 118})
    hit(CRASH2, 212 + 2.0, 120, dur=2880)


# ======================================================================
#                        ASSEMBLE THE MIDI FILE
# ======================================================================

TEMPO_MAP = [
    (0, 92), (16, 100), (48, 102), (64, 108), (80, 112),
    (112, 92), (136, 116), (168, 126), (200, 132),
]

HANDS = set(range(35, 82)) - {KICK2, KICK, HHP}
FEET = {KICK2, KICK, HHP}


def sanitize_playability():
    """Drop notes so that never more than two hands / two feet hit at once."""
    by_tick = {}
    for nt in notes:
        by_tick.setdefault(nt[0], []).append(nt)
    keep = set()
    for tick, group in by_tick.items():
        for limb_set in (HANDS, FEET):
            limbs = [n for n in group if n[1] in limb_set]
            if len(limbs) > 2:
                limbs.sort(key=lambda n: -n[2])
                group = [n for n in group if n not in limbs[2:]]
        for n in group:
            keep.add(id(n))
    return [n for n in notes if id(n) in keep]


def write_midi(path):
    global notes
    notes = sanitize_playability()

    # keep the musical order stable, then fix overlapping repeats of a pitch
    notes.sort(key=lambda n: (n[0], n[2], n[1]))
    last = {}
    for i, nt in enumerate(notes):
        n = nt[1]
        if n in last:
            j = last[n]
            if notes[j][3] > nt[0]:
                notes[j][3] = max(notes[j][0] + 30, nt[0] - 2)
        last[n] = i

    events = []
    for t, n, v, end in notes:
        events.append((t, 1, Message('note_on', note=n, velocity=v, channel=CH)))
        events.append((end, 0, Message('note_off', note=n, velocity=0, channel=CH)))
    for beat, bpm in TEMPO_MAP:
        events.append((int(beat * TPB), -1,
                       MetaMessage('set_tempo', tempo=bpm2tempo(bpm))))
    events.sort(key=lambda e: (e[0], e[1]))

    mid = MidiFile(ticks_per_beat=TPB)
    tr = MidiTrack()
    mid.tracks.append(tr)
    tr.append(MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(MetaMessage('time_signature', numerator=4, denominator=4,
                          clocks_per_click=24, notated_32nd_notes_per_beat=8,
                          time=0))
    tr.append(MetaMessage('set_tempo', tempo=bpm2tempo(92), time=0))

    prev = 0
    for t, kind, msg in events:
        msg.time = t - prev
        prev = t
        tr.append(msg)

    mid.save(path)


def main():
    compose()
    write_midi('solo.mid')


if __name__ == '__main__':
    main()
