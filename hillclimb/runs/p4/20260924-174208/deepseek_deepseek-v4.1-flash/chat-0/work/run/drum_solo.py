#!/usr/bin/env python3
"""
drum_solo.py

Generates a ~2 minute General MIDI drum solo on MIDI channel 10 (GM percussion)
and writes it to solo.mid in the current directory.

The performance is fully deterministic: running the script twice produces
byte-identical output.

Musical design
--------------
*   A four bar motif (kick 1 / & of 2 / & of 3, snare backbeat, ride 8ths) is
    stated in the intro, developed on the toms, buried under a breakdown,
    rebuilt through a snare roll and returned at full force in the finale.
*   Density and dynamics are shaped *inside* phrases with accents, ghost notes
    and crescendos rather than by simply making whole sections louder.
*   Singles and doubles run around the kit; rolls swell and resolve; every fill
    carries into the next downbeat.
*   Micro-timing is deliberate: each instrument class has a fixed offset
    (snare sits back, cymbals ride ahead, toms a hair behind) and each section
    has a global push/pull, so the pulse breathes without random jitter.
*   Maximum two hands and two feet sound at any instant.
"""

import mido

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
PPQ = 480
S   = 120       # 16th note
E   = 240       # 8th note
Q   = 480       # quarter note
BAR = 4 * Q     # 1920 ticks
CH  = 9         # zero-based index -> MIDI channel 10

# ---------------------------------------------------------------------------
# GM percussion map (subset used)
# ---------------------------------------------------------------------------
KICK   = 36
KICK2  = 35
SNARE  = 38
STICK  = 37
HAT    = 42
PEDAL  = 44
OHAT   = 46
RIDE   = 51
RIDE2  = 59
BELL   = 53
CRASH  = 49
CRASH2 = 57
SPLASH = 55
CHINA  = 52
TOM1   = 50     # high tom
TOM2   = 48     # hi-mid tom
TOM3   = 47     # low-mid tom
TOM4   = 45     # low tom
TOM5   = 43     # high floor tom
TOM6   = 41     # low floor tom

FOOT_NOTES = frozenset((KICK, KICK2, PEDAL))

events = []

# ---------------------------------------------------------------------------
# Feel: consistent, deliberate placement
# ---------------------------------------------------------------------------
NOFF = {
    KICK: 0, KICK2: 0,
    SNARE: 6, STICK: 4,
    HAT: -4, PEDAL: 0, OHAT: -3,
    RIDE: -3, RIDE2: -3, BELL: -3,
    CRASH: 0, CRASH2: 0, SPLASH: 0, CHINA: 0,
    TOM1: 3, TOM2: 3, TOM3: 3, TOM4: 4, TOM5: 4, TOM6: 4,
}


def section_feel(bar):
    """Global push (negative) / pull (positive) in ticks, per section."""
    if bar < 4:   return 6      # settling in, laid back
    if bar < 12:  return 2      # groove
    if bar < 20:  return 0      # straight
    if bar < 28:  return 8      # relaxed, floating
    if bar < 36:  return -3     # leaning forward
    if bar < 46:  return -5     # pushing hard
    if bar < 54:  return -1
    if bar < 62:  return 3      # broad and heavy
    return 5                    # final land


def place(t, note, vel, dur=90):
    bar = int(t // BAR)
    off = section_feel(bar) + NOFF.get(note, 0)
    events.append([int(t + off), int(note), int(vel), int(dur)])


def b(bar, step, note, vel, dur=90):
    place(bar * BAR + step * S, note, vel, dur)


# ---------------------------------------------------------------------------
# Reusable patterns
# ---------------------------------------------------------------------------
def ride_bar(bar, note=RIDE, vel=66, skip=()):
    """8th note time line with an accented downbeat and softer offbeats."""
    for i in range(0, 16, 2):
        if i in skip:
            continue
        v = vel
        if i == 0:
            v += 16
        elif i % 4 == 0:
            v += 10
        else:
            v -= 4
        b(bar, i, note, v)


def groove(bar, crash=None, ride=True, ride_note=RIDE, ride_vel=66,
           kvel=100, svel=102, kick_steps=(0, 6, 10), snare_steps=(4, 12),
           ghosts=(7, 15), ghost_vel=30, pedal=True, extra=()):
    """One bar of the core motif with a few knobs for variation."""
    if crash is not None:
        b(bar, 0, CRASH, crash, 480)
    if ride:
        ride_bar(bar, ride_note, ride_vel)
    for i, k in enumerate(kick_steps):
        b(bar, k, KICK, kvel - 3 * i)
    for i, s in enumerate(snare_steps):
        b(bar, s, SNARE, svel + 3 * i)
    for g in ghosts:
        b(bar, g, SNARE, ghost_vel)
    if pedal:
        b(bar, 4, PEDAL, 54)
        b(bar, 12, PEDAL, 54)
    for (st, nt, vl) in extra:
        b(bar, st, nt, vl)


# ===========================================================================
#  INTRO  - bars 0-3 : state the motif quietly
# ===========================================================================
b(0, 0, CRASH, 100, 960)
b(0, 0, KICK, 106, 240)
b(0, 4, RIDE, 60, 200)
b(0, 8, RIDE, 64, 200)
b(0, 12, RIDE, 60, 200)
b(0, 4, PEDAL, 56, 120)
b(0, 12, PEDAL, 56, 120)

for i in range(0, 16, 2):
    b(1, i, RIDE, 58 + (10 if i % 4 == 0 else 0))
b(1, 0, KICK, 94)
b(1, 10, KICK, 86)
b(1, 4, SNARE, 76)
b(1, 12, SNARE, 82)
b(1, 4, PEDAL, 54)
b(1, 12, PEDAL, 54)

for i in range(0, 16, 2):
    b(2, i, RIDE, 60 + (10 if i % 4 == 0 else 0))
b(2, 0, KICK, 98)
b(2, 6, KICK, 84)
b(2, 10, KICK, 90)
b(2, 4, SNARE, 82)
b(2, 12, SNARE, 88)
b(2, 7, SNARE, 28)
b(2, 15, SNARE, 26)
b(2, 4, PEDAL, 54)
b(2, 12, PEDAL, 54)

# bar 3 : pickup fill carrying into the downbeat
for i in range(0, 8, 2):
    b(3, i, RIDE, 60 + (10 if i % 4 == 0 else 0))
b(3, 0, KICK, 100)
b(3, 4, SNARE, 86)
b(3, 6, KICK, 88)
_f3 = [SNARE, SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6]
for k, n in enumerate(_f3):
    b(3, 8 + k, n, 54 + k * 8)

# ===========================================================================
#  GROOVE  - bars 4-11 : the motif, hi-hat, ghost notes, doubles
# ===========================================================================
groove(4, crash=112, ride_note=HAT, ride_vel=68)
groove(5, ride_note=HAT, ride_vel=68)
groove(6, ride_note=HAT, ride_vel=68, kick_steps=(0, 3, 6, 10))
groove(7, ride_note=HAT, ride_vel=68, ghosts=(7,))
b(7, 13, TOM1, 88)
b(7, 14, TOM2, 94)
b(7, 15, TOM3, 100)

groove(8, crash=114, ride_note=HAT, ride_vel=70)
groove(9, ride_note=HAT, ride_vel=70, ghosts=(3, 5, 11, 13))
groove(10, ride_note=HAT, ride_vel=70, kick_steps=(0, 6, 10, 14), ghosts=(7,))

# bar 11 : fill into the development
for i in range(0, 8, 2):
    b(11, i, HAT, 68 + (12 if i % 4 == 0 else 0))
b(11, 0, KICK, 104)
b(11, 4, SNARE, 104)
b(11, 6, KICK, 94)
_f11 = [SNARE, TOM1, SNARE, TOM2, TOM3, TOM4, TOM5, TOM6]
for k, n in enumerate(_f11):
    b(11, 8 + k, n, 66 + k * 7)

# ===========================================================================
#  DEVELOPMENT  - bars 12-19 : motif moved to toms, syncopation, runs
# ===========================================================================
groove(12, ride_vel=70, kvel=104, svel=106)

# bar 13 : the kick motif re-voiced on the toms
ride_bar(13, RIDE, 68)
b(13, 0, TOM2, 102)
b(13, 6, TOM3, 98)
b(13, 10, TOM4, 102)
b(13, 4, SNARE, 106)
b(13, 12, SNARE, 110)
b(13, 4, PEDAL, 54)
b(13, 12, PEDAL, 54)
b(13, 15, SNARE, 30)

# bar 14 : syncopated kick with scattered ghosts
ride_bar(14, RIDE, 68)
b(14, 0, KICK, 106)
b(14, 5, KICK, 92)
b(14, 10, KICK, 98)
b(14, 13, KICK, 88)
b(14, 4, SNARE, 106)
b(14, 12, SNARE, 110)
b(14, 7, SNARE, 32)
b(14, 11, SNARE, 28)
b(14, 15, SNARE, 34)
b(14, 4, PEDAL, 54)
b(14, 12, PEDAL, 54)

# bar 15 : fill
for i in range(0, 8, 2):
    b(15, i, RIDE, 68 + (12 if i % 4 == 0 else 0))
b(15, 0, KICK, 104)
b(15, 4, SNARE, 102)
b(15, 6, KICK, 90)
_f15 = [SNARE, SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6]
for k, n in enumerate(_f15):
    b(15, 8 + k, n, 72 + k * 6)

groove(16, crash=116, ride_vel=72, kvel=106, svel=108)

# bar 17 : open hi-hat on the last offbeat
ride_bar(17, RIDE, 72, skip=(14,))
b(17, 0, KICK, 106)
b(17, 6, KICK, 96)
b(17, 10, KICK, 102)
b(17, 4, SNARE, 108)
b(17, 12, SNARE, 112)
b(17, 7, SNARE, 32)
b(17, 4, PEDAL, 54)
b(17, 14, OHAT, 96, 300)

# bar 18 : 16th note run around the kit
_r18 = [SNARE, SNARE, TOM1, TOM1, TOM2, TOM2, TOM3, TOM3,
        TOM4, TOM4, TOM5, TOM5, TOM6, TOM6, TOM5, TOM6]
for k, n in enumerate(_r18):
    b(18, k, n, 84 + (k % 4) * 5)
b(18, 0, KICK, 104)
b(18, 8, KICK, 98)

# bar 19 : big fill resolving on the next downbeat
_f19 = [TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, SNARE, SNARE,
        TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, TOM5, TOM6]
for k, n in enumerate(_f19):
    b(19, k, n, 82 + (k % 4) * 7)
b(19, 0, KICK, 106)
b(19, 8, KICK, 100)

# ===========================================================================
#  BREAKDOWN  - bars 20-27 : space, laid back ride, brush-like ghosts, swell
# ===========================================================================
b(20, 0, CRASH, 72, 960)
b(20, 0, KICK, 82)
b(20, 4, RIDE, 56)
b(20, 8, RIDE, 60)
b(20, 12, RIDE, 56)
b(20, 4, PEDAL, 48)
b(20, 12, PEDAL, 48)

for bar in (21, 22):
    for i in range(0, 16, 2):
        b(bar, i, RIDE, 54 + (10 if i % 4 == 0 else 0))
    b(bar, 0, KICK, 78)
    b(bar, 10, KICK, 70)
    b(bar, 4, SNARE, 60)
    b(bar, 12, SNARE, 64)
    b(bar, 7, SNARE, 24)
    b(bar, 4, PEDAL, 46)
    b(bar, 12, PEDAL, 46)

# bar 23 : ride bell, sparse
for i, st in enumerate((0, 6, 10, 14)):
    b(23, st, BELL, 66 - i * 2)
b(23, 0, KICK, 74)
b(23, 12, SNARE, 52)
b(23, 4, PEDAL, 46)
b(23, 12, PEDAL, 46)

# bar 24 : brush-like ghost swirl
for i in range(16):
    b(24, i, SNARE, 22 + (16 if i % 4 == 0 else 0))
b(24, 0, KICK, 70)
b(24, 8, KICK, 66)
b(24, 4, PEDAL, 44)
b(24, 12, PEDAL, 44)

# bar 25 : crescendo 16ths
for i in range(16):
    b(25, i, SNARE, 38 + i * 3)
b(25, 0, KICK, 78)
b(25, 8, KICK, 74)

# bar 26 : 8th note tom build
_seq26 = [TOM1, TOM2, TOM3, TOM4, TOM5, TOM6]
for i in range(0, 16, 2):
    b(26, i, _seq26[(i // 2) % 6], 66 + i * 2)
b(26, 0, KICK, 86)
b(26, 12, KICK, 86)

# bar 27 : bigger fill into the build
_f27 = [SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, SNARE,
        TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, TOM5, TOM6]
for k, n in enumerate(_f27):
    b(27, k, n, 72 + k * 3)
b(27, 0, KICK, 92)
b(27, 8, KICK, 92)

# ===========================================================================
#  BUILD  - bars 28-35 : quiet -> 16ths -> snare roll -> full kit
# ===========================================================================
for i in range(0, 16, 2):
    b(28, i, RIDE, 56 + (10 if i % 4 == 0 else 0))
b(28, 0, KICK, 84)
b(28, 10, KICK, 76)
b(28, 4, SNARE, 66)
b(28, 12, SNARE, 70)
b(28, 6, SNARE, 26)
b(28, 14, SNARE, 26)
b(28, 4, PEDAL, 48)
b(28, 12, PEDAL, 48)

for i in range(0, 16, 2):
    b(29, i, RIDE, 58 + (10 if i % 4 == 0 else 0))
b(29, 0, KICK, 88)
b(29, 6, KICK, 80)
b(29, 10, KICK, 84)
b(29, 4, SNARE, 72)
b(29, 12, SNARE, 76)
for g in (3, 7, 11, 15):
    b(29, g, SNARE, 28)
b(29, 4, PEDAL, 48)
b(29, 12, PEDAL, 48)

for i in range(16):
    b(30, i, RIDE, 60 + (14 if i % 4 == 0 else 0))
b(30, 0, KICK, 92)
b(30, 8, KICK, 88)
b(30, 4, SNARE, 80)
b(30, 12, SNARE, 84)
b(30, 4, PEDAL, 48)
b(30, 12, PEDAL, 48)

for i in range(0, 16, 2):
    b(31, i, SNARE, 50 + i * 2)
b(31, 0, KICK, 96)
b(31, 8, KICK, 92)

for i in range(16):
    b(32, i, SNARE, 58 + i * 2)
b(32, 0, KICK, 100)
b(32, 8, KICK, 96)

for i in range(16):
    b(33, i, SNARE, 90 + (20 if i % 4 == 0 else 0))
b(33, 0, KICK, 106)
b(33, 8, KICK, 100)
b(33, 0, CRASH, 108, 480)

groove(34, ride_vel=78, kvel=112, svel=114, ghosts=(7, 15))

for i in range(0, 8, 2):
    b(35, i, RIDE, 76 + (12 if i % 4 == 0 else 0))
b(35, 0, KICK, 108)
b(35, 4, SNARE, 110)
b(35, 6, KICK, 100)
_f35 = [SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, TOM6]
for k, n in enumerate(_f35):
    b(35, 8 + k, n, 92 + (k % 4) * 6)

# ===========================================================================
#  CLIMAX  - bars 36-45 : full kit, driving, tom punctuation
# ===========================================================================
groove(36, crash=120, ride_vel=80, kvel=114, svel=116)
groove(37, ride_vel=80, kvel=114, svel=116, kick_steps=(0, 3, 6, 10), ghosts=(7,))
groove(38, ride_vel=80, kvel=114, svel=116, ghosts=(7,))
b(38, 14, TOM2, 110)
b(38, 15, TOM3, 114)
groove(39, ride_vel=80, kvel=114, svel=116, kick_steps=(0, 6, 10, 14))
groove(40, crash=120, ride_vel=82, kvel=116, svel=118)
groove(41, ride_vel=82, kvel=116, svel=118, ghosts=(3, 5, 11, 13))

for i in range(0, 8, 2):
    b(42, i, RIDE, 80 + (12 if i % 4 == 0 else 0))
b(42, 0, KICK, 112)
b(42, 4, SNARE, 114)
b(42, 6, KICK, 104)
_f42 = [TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, SNARE, TOM6]
for k, n in enumerate(_f42):
    b(42, 8 + k, n, 96 + (k % 4) * 6)

groove(43, crash=118, ride_vel=80, kvel=114, svel=116)

# bar 44 : ghost snare 16ths against the ride
for i in range(0, 16, 2):
    v = 78
    if i == 0:
        v += 16
    elif i % 4 == 0:
        v += 10
    else:
        v -= 4
    b(44, i, RIDE, v)
for i in range(1, 16, 2):
    if i == 7:
        continue
    b(44, i, SNARE, 34)
b(44, 0, KICK, 114)
b(44, 6, KICK, 104)
b(44, 10, KICK, 110)
b(44, 4, SNARE, 116)
b(44, 12, SNARE, 118)
b(44, 4, PEDAL, 54)
b(44, 12, PEDAL, 54)

# bar 45 : fill into the run section
_f45 = [SNARE, SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6,
        SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, TOM6]
for k, n in enumerate(_f45):
    b(45, k, n, 96 + (k % 4) * 6)
b(45, 0, KICK, 112)
b(45, 8, KICK, 108)

# ===========================================================================
#  RUNS  - bars 46-53 : long lines of singles and doubles around the kit
# ===========================================================================
_r46 = [SNARE, SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6,
        TOM6, TOM5, TOM4, TOM3, TOM2, TOM1, TOM2, TOM3]
for k, n in enumerate(_r46):
    b(46, k, n, 88 + (k % 4) * 6)
b(46, 0, KICK, 110)
b(46, 8, KICK, 106)

_r47 = [TOM1, TOM1, TOM2, TOM2, TOM3, TOM3, TOM4, TOM4,
        TOM5, TOM5, TOM6, TOM6, SNARE, SNARE, TOM5, TOM6]
for k, n in enumerate(_r47):
    b(47, k, n, 90 + (k % 4) * 5)
b(47, 0, KICK, 108)
b(47, 8, KICK, 104)

groove(48, crash=118, ride_vel=78, kvel=112, svel=114)

_r49 = [SNARE, TOM1, SNARE, TOM2, TOM3, TOM4, TOM3, TOM4,
        TOM5, TOM6, TOM5, TOM6, SNARE, TOM1, TOM2, TOM3]
for k, n in enumerate(_r49):
    b(49, k, n, 86 + (k % 4) * 8)
b(49, 0, KICK, 110)
b(49, 4, KICK, 100)
b(49, 12, KICK, 104)

groove(50, ride_vel=78, kvel=112, svel=114, kick_steps=(0, 3, 6, 10))

_r51 = [SNARE, SNARE, TOM1, TOM1, TOM2, TOM2, TOM3, TOM4,
        TOM5, TOM6, TOM5, TOM4, TOM3, TOM2, TOM1, SNARE]
for k, n in enumerate(_r51):
    b(51, k, n, 92 + (k % 4) * 6)
b(51, 0, KICK, 112)
b(51, 8, KICK, 106)

groove(52, crash=120, ride_vel=80, kvel=114, svel=116)

_f53 = [SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, SNARE,
        TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, TOM5, TOM6]
for k, n in enumerate(_f53):
    b(53, k, n, 94 + (k % 4) * 6)
b(53, 0, KICK, 112)
b(53, 8, KICK, 108)

# ===========================================================================
#  FINALE  - bars 54-61 : the motif comes home, then builds for the last hit
# ===========================================================================
groove(54, crash=122, ride_note=HAT, ride_vel=82, kvel=116, svel=118)
groove(55, ride_note=HAT, ride_vel=82, kvel=116, svel=118, ghosts=(7, 15))
groove(56, ride_note=HAT, ride_vel=82, kvel=116, svel=118,
       kick_steps=(0, 6, 10, 14))
groove(57, ride_note=HAT, ride_vel=82, kvel=116, svel=118,
       ghosts=(3, 5, 11, 13))
groove(58, crash=122, ride_vel=84, kvel=118, svel=120)

# bar 59 : open hi-hat lift
ride_bar(59, RIDE, 84, skip=(14,))
b(59, 0, KICK, 118)
b(59, 6, KICK, 108)
b(59, 10, KICK, 114)
b(59, 4, SNARE, 120)
b(59, 12, SNARE, 122)
b(59, 4, PEDAL, 56)
b(59, 14, OHAT, 108, 300)

# bar 60 : 16th snare build
for i in range(16):
    b(60, i, SNARE, 96 + (i % 4) * 5)
b(60, 0, KICK, 118)
b(60, 8, KICK, 112)

# bar 61 : fill
_f61 = [TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, TOM5, TOM6,
        SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, SNARE]
for k, n in enumerate(_f61):
    b(61, k, n, 100 + (k % 4) * 6)
b(61, 0, KICK, 118)
b(61, 8, KICK, 114)

# ===========================================================================
#  CODA  - bars 62-65 : final flourish and the landing hit
# ===========================================================================
_f62 = [SNARE, SNARE, TOM1, TOM1, TOM2, TOM2, TOM3, TOM3,
        TOM4, TOM4, TOM5, TOM5, TOM6, TOM6, TOM5, TOM6]
for k, n in enumerate(_f62):
    b(62, k, n, 100 + (k % 4) * 5)
b(62, 0, KICK, 118)
b(62, 8, KICK, 114)

_seq63 = [TOM6, TOM5, TOM4, TOM3, TOM2, TOM1, SNARE, SNARE]
for k, n in enumerate(_seq63):
    b(63, k * 2, n, 100 + k * 3)
b(63, 0, KICK, 118)
b(63, 8, KICK, 112)

# THE LANDING HIT : crash + kick + snare, ringing for two bars
b(64, 0, CRASH, 127, 2 * BAR)
b(64, 0, KICK, 127, 480)
b(64, 0, SNARE, 122, 240)

# ===========================================================================
#  Rendering
# ===========================================================================
def finalize(evts):
    """Enforce one-drummer physical limits: <=2 hands and <=2 feet at a time."""
    groups = {}
    for t, n, v, d in evts:
        groups.setdefault(t, []).append([t, n, v, d])
    out = []
    for t in sorted(groups):
        g = groups[t]
        best = {}
        for e in g:
            k = e[1]
            if k not in best or e[2] > best[k][2]:
                best[k] = e
        g = list(best.values())
        hands = sorted((e for e in g if e[1] not in FOOT_NOTES),
                       key=lambda e: -e[2])[:2]
        feet = sorted((e for e in g if e[1] in FOOT_NOTES),
                      key=lambda e: -e[2])[:2]
        out.extend(hands)
        out.extend(feet)
    return out


def build_midi(evts, path='solo.mid'):
    evts = finalize(evts)

    msgs = []
    for t, n, v, d in evts:
        msgs.append((t, 1, n, v))          # note_on
        msgs.append((t + d, 0, n, 0))      # note_off
    msgs.sort(key=lambda x: (x[0], x[1]))  # offs before ons at the same tick

    mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(132), time=0))
    track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                  time=0))

    last = 0
    for t, typ, n, v in msgs:
        delta = t - last
        if delta < 0:
            delta = 0
        last = t
        if typ:
            track.append(mido.Message('note_on', channel=CH, note=n,
                                      velocity=v, time=delta))
        else:
            track.append(mido.Message('note_off', channel=CH, note=n,
                                      velocity=0, time=delta))

    mid.save(path)


if __name__ == '__main__':
    build_midi(events, 'solo.mid')
    print('wrote solo.mid')
