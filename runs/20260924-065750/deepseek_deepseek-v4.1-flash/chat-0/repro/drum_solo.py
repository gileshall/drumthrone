#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid, a two minute General MIDI drum solo for
one drummer (two hands, two feet) on MIDI channel 10 (0-based channel 9).

Design notes
------------
* 108 bpm, 4/4, 54 bars  ->  exactly 120.0 seconds.
* One rhythmic cell carries the whole solo: the 3+3+2 figure
  (sixteenth positions 0 3 6 8 11 14).  It is stated, moved to the snare,
  to the toms, to the cowbell, to hand drums, broken up and brought back.
* Swung sixteenths everywhere: the off-beat eighth sits at 62.5% of the
  beat and the in-between sixteenths are interpolated inside their eighth,
  so the feel never limps.  On top of that grid there is one fixed pocket:
  the kick leans ~8 ticks forward, the backbeat snare sits ~10 ticks back.
  Deliberate placement, not random jitter.
* Ghost notes (vel 30-45) against accents (vel 100-127) throughout.
* Sections build and release: statement / groove / cell on toms / funk /
  build / peak / breakdown (space, cowbell, hand drums) / return /
  development / climax / cell reprise / final fill / ending.
* A safety pass guarantees the result is playable: never more than two
  hands and two feet striking at the same instant.
"""

from collections import defaultdict

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

# --------------------------------------------------------------- timing
PPQ = 480
BEAT = PPQ
BAR = 4 * BEAT
TEMPO = 108                 # 54 bars == exactly 120.0 s
CHANNEL = 9                 # General MIDI channel 10
END_TICK = 54 * BAR

# Swung sixteenth grid: where the four sixteenths of a beat actually land.
# Off-beat eighth at 62.5% of the beat; the sixteenths sit halfway inside
# their own eighth so the subdivision stays even.
SW = (0, 150, 300, 390)

# The pocket: kick pushes, backbeat snare lays back, ghost notes with it.
POCKET = {36: -8, 38: 10, 37: 8, 44: 6}

# ---------------------------------------------------- percussion palette
KICK, SNARE, STICK = 36, 38, 37
HAT, PHAT, OHAT = 42, 44, 46
RIDE, BELL = 51, 53
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
T_HI, T_MID, T_LO, T_FLOOR = 50, 47, 45, 43
COW, CLAVE, WB_HI, WB_LO = 56, 75, 76, 77
TAMB, CABASA, MARACAS = 54, 69, 70
BONGO_H, BONGO_L = 60, 61
CONGA_H, CONGA_L = 63, 64
TIMB_H, TIMB_L = 65, 66
AGOGO_H, AGOGO_L = 67, 68
TRI = 81

CYMBALS = {49, 51, 52, 53, 55, 57, 59}
TOMS = {41, 43, 45, 47, 48, 50}
FEET = {35, 36, 44}

MOTIF = (0, 3, 6, 8, 11, 14)        # 3 + 3 + 2, the cell of the solo

# ------------------------------------------------------------ note store
NOTES = []          # [tick, note, velocity, duration]


def tick_of(bar, g):
    """Absolute tick of sixteenth 'g' (0..15) of 1-based bar 'bar'."""
    return (bar - 1) * BAR + (g // 4) * BEAT + SW[g % 4]


def hit(bar, g, note, vel, dur=None):
    t = tick_of(bar, g) + POCKET.get(note, 0)
    if t < 0:
        t = 0
    if dur is None:
        if note in CYMBALS:
            dur = 720
        elif note in TOMS:
            dur = 400
        else:
            dur = 90
    NOTES.append([t, note, max(1, min(127, int(round(vel)))), dur])


# ======================================================================
# 1. INTRO - bars 1-4 : state the cell, quietly and deliberately
# ======================================================================
for b in (1, 2):
    for g, v in zip(MOTIF, (94, 74, 78, 98, 76, 80)):
        hit(b, g, BELL, v)
    hit(b, 0, KICK, 76)
    hit(b, 8, KICK, 68)
hit(2, 4, PHAT, 62)
hit(2, 12, PHAT, 62)

# bar 3: the cell moves to the snare, ghosts fill the holes
for g, v in zip(MOTIF, (108, 86, 90, 112, 88, 92)):
    hit(3, g, SNARE, v)
for g in (1, 2, 5, 7, 9, 13, 15):
    hit(3, g, SNARE, 30)
for g in (0, 2, 4, 6, 8, 10, 12, 14):
    hit(3, g, HAT, 76 if g % 4 == 0 else 56)
hit(3, 0, KICK, 98)
hit(3, 10, KICK, 84)

# bar 4: same, last beat turns into a tom pickup
for g, v in zip(MOTIF, (108, 86, 90, 112, 88, 92)):
    if g == 14:
        continue
    hit(4, g, SNARE, v)
for g in (1, 2, 5, 7, 9):
    hit(4, g, SNARE, 30)
for g in (0, 2, 4, 6, 8, 10):
    hit(4, g, HAT, 76 if g % 4 == 0 else 56)
hit(4, 0, KICK, 98)
hit(4, 10, KICK, 84)
for g, n, v in ((12, T_HI, 94), (13, T_HI, 98), (14, T_MID, 102), (15, T_LO, 106)):
    hit(4, g, n, v)


# ======================================================================
# 2. GROOVE - bars 5-8 : the cell becomes a groove
# ======================================================================
def groove(b, rv=86, sv=106, kv=104, ghosts=(3, 7, 11, 15), gv=32,
           open_hat=False, extra_kick=()):
    for g in (0, 2, 4, 6, 8, 10, 12, 14):
        if open_hat and g == 14:
            continue
        hit(b, g, RIDE, rv if g % 4 == 0 else rv - 18)
    if open_hat:
        hit(b, 14, OHAT, 92)
    hit(b, 4, SNARE, sv)
    hit(b, 12, SNARE, sv + 4)
    for g in (0, 6, 10):
        hit(b, g, KICK, kv if g == 0 else kv - 14)
    for g in extra_kick:
        hit(b, g, KICK, kv - 10)
    for g in ghosts:
        hit(b, g, SNARE, gv)


groove(5)
groove(6)
groove(7, open_hat=True, extra_kick=(14,), rv=90, sv=110, kv=108)

# bar 8: half a bar of groove, then a fill down the toms
for g in (0, 2, 4, 6):
    hit(8, g, RIDE, 88 if g % 4 == 0 else 70)
hit(8, 0, KICK, 106)
hit(8, 3, SNARE, 32)
hit(8, 4, SNARE, 108)
hit(8, 6, KICK, 92)
for g, n, v in ((8, T_HI, 96), (9, T_HI, 100), (10, T_MID, 104),
                (11, T_LO, 108), (12, T_LO, 110), (13, T_FLOOR, 112),
                (14, SNARE, 114), (15, SNARE, 116)):
    hit(8, g, n, v)


# ======================================================================
# 3. CELL ON THE TOMS - bars 9-12 : loud, full, crashing
# ======================================================================
hit(9, 0, CRASH, 116)
hit(9, 0, KICK, 112)
for g, n, v in ((3, T_HI, 98), (6, T_MID, 96), (8, T_HI, 104),
                (11, T_LO, 98), (14, T_MID, 96)):
    hit(9, g, n, v)
hit(9, 6, KICK, 88)
hit(9, 11, KICK, 92)

hit(10, 0, CRASH, 112)
hit(10, 0, KICK, 110)
for g, n, v in ((3, T_LO, 98), (6, T_MID, 96), (8, T_LO, 104),
                (11, T_FLOOR, 98), (14, T_MID, 96)):
    hit(10, g, n, v)
hit(10, 6, KICK, 88)
hit(10, 14, KICK, 90)

hit(11, 0, CRASH, 118)
hit(11, 0, KICK, 112)
hit(11, 8, CRASH2, 112)
for g, n, v in ((3, T_HI, 100), (6, T_MID, 98), (11, T_LO, 100), (14, T_MID, 98)):
    hit(11, g, n, v)
hit(11, 6, KICK, 90)

# bar 12: two beats of groove then a run down the toms
for g in (0, 2, 4, 6):
    hit(12, g, RIDE, 88 if g % 4 == 0 else 70)
hit(12, 0, KICK, 108)
hit(12, 4, SNARE, 108)
hit(12, 6, KICK, 92)
for g, n, v in ((8, T_HI, 96), (9, T_HI, 100), (10, T_MID, 104),
                (11, T_MID, 106), (12, T_LO, 108), (13, T_LO, 110),
                (14, T_FLOOR, 112), (15, T_FLOOR, 114)):
    hit(12, g, n, v)


# ======================================================================
# 4. FUNK - bars 13-16 : sixteenth hats, ghosts, syncopated kick
# ======================================================================
def funk(b, crash=None, open_hat=False, extra_kick=(), ghosts=(3, 7, 11, 15)):
    for g in range(16):
        if open_hat and g == 15:
            continue
        v = 84 if g % 4 == 0 else (60 if g % 2 == 0 else 46)
        hit(b, g, HAT, v)
    if open_hat:
        hit(b, 15, OHAT, 94)
    if crash:
        hit(b, 0, crash, 110)
    hit(b, 4, SNARE, 108)
    hit(b, 12, SNARE, 112)
    for g in ghosts:
        hit(b, g, SNARE, 34)
    for g in (0, 6, 10):
        hit(b, g, KICK, 104 if g == 0 else 90)
    for g in extra_kick:
        hit(b, g, KICK, 88)


funk(13)
funk(14, extra_kick=(14,))
funk(15, crash=CRASH2, open_hat=True, extra_kick=(3, 14), ghosts=(3, 7, 11))

# bar 16: half a bar, then a fill
for g in range(8):
    v = 84 if g % 4 == 0 else (60 if g % 2 == 0 else 46)
    hit(16, g, HAT, v)
hit(16, 0, KICK, 106)
hit(16, 3, SNARE, 34)
hit(16, 4, SNARE, 110)
hit(16, 6, KICK, 92)
for g, n, v in ((8, T_HI, 100), (9, T_HI, 104), (10, T_MID, 106),
                (11, T_LO, 108), (12, T_LO, 110), (13, T_FLOOR, 112),
                (14, T_FLOOR, 114), (15, SNARE, 118)):
    hit(16, g, n, v)


# ======================================================================
# 5. BUILD - bars 17-20
# ======================================================================
groove(17, rv=94, sv=112, kv=110, gv=34)
groove(18, rv=94, sv=112, kv=110, gv=34, extra_kick=(3, 14))

# bar 19: sixteenths on the snare, accents on the beat
for g in range(16):
    hit(19, g, SNARE, 104 if g % 4 == 0 else 64)
hit(19, 0, KICK, 110)
hit(19, 8, KICK, 106)

# bar 20: crescendo roll
for g in range(16):
    hit(20, g, SNARE, 72 + g * 3)
hit(20, 0, KICK, 112)
hit(20, 4, KICK, 100)
hit(20, 8, KICK, 112)
hit(20, 12, KICK, 100)


# ======================================================================
# 6. PEAK 1 - bars 21-24
# ======================================================================
hit(21, 0, CRASH, 122)
hit(21, 0, KICK, 118)
hit(21, 8, CRASH2, 118)
hit(21, 8, KICK, 112)
for g, n, v in ((3, T_HI, 106), (6, T_MID, 104), (11, T_LO, 106), (14, T_MID, 104)):
    hit(21, g, n, v)
hit(21, 4, SNARE, 112)
hit(21, 12, SNARE, 114)

hit(22, 0, CRASH, 118)
hit(22, 0, KICK, 116)
for g, n, v in ((3, T_HI, 108), (6, T_MID, 106), (8, T_LO, 110),
                (11, T_FLOOR, 108), (14, T_LO, 106)):
    hit(22, g, n, v)
hit(22, 4, SNARE, 110)
hit(22, 6, KICK, 100)
hit(22, 10, KICK, 100)
hit(22, 12, SNARE, 112)

# bar 23: heavy groove, bell on eighths
hit(23, 0, CRASH2, 112)
for g in (0, 2, 4, 6, 8, 10, 12, 14):
    hit(23, g, BELL, 96 if g % 4 == 0 else 76)
hit(23, 4, SNARE, 114)
hit(23, 12, SNARE, 116)
for g in (0, 3, 6, 10, 14):
    hit(23, g, KICK, 112 if g == 0 else 96)

# bar 24: big fill
hit(24, 0, CRASH, 120)
hit(24, 0, KICK, 118)
for g in (2, 4, 6):
    hit(24, g, RIDE, 78)
hit(24, 4, SNARE, 112)
for g, n, v in ((8, T_HI, 108), (9, T_HI, 112), (10, T_MID, 114),
                (11, T_MID, 116), (12, T_LO, 118), (13, T_LO, 120),
                (14, T_FLOOR, 122), (15, T_FLOOR, 124)):
    hit(24, g, n, v)


# ======================================================================
# 7. BREAKDOWN - bars 25-28 : space, cowbell, hand drums
# ======================================================================
hit(25, 0, CRASH, 98)
hit(25, 0, KICK, 76)
hit(25, 4, STICK, 68)
hit(25, 8, PHAT, 58)
hit(25, 12, STICK, 70)
hit(25, 14, STICK, 58)

# bar 26: the cell on the cowbell, rim clicks on the backbeat
for g, v in zip(MOTIF, (86, 66, 70, 90, 68, 72)):
    hit(26, g, COW, v)
hit(26, 0, PHAT, 60)
hit(26, 0, KICK, 74)
hit(26, 4, STICK, 72)
hit(26, 8, PHAT, 60)
hit(26, 12, STICK, 74)

# bars 27-28: hand drums take the cell
for b in (27, 28):
    for g, n, v in ((0, BONGO_H, 92), (3, BONGO_L, 78), (6, CONGA_H, 90),
                    (8, CONGA_L, 94), (11, BONGO_H, 80), (14, CONGA_H, 92)):
        hit(b, g, n, v)
    for g in (1, 2, 5, 7, 9, 10, 13, 15):
        hit(b, g, CONGA_L, 40)
    hit(b, 0, KICK, 80)
    hit(b, 8, KICK, 76)
hit(28, 4, TAMB, 72)


# ======================================================================
# 8. RETURN - bars 29-32 : hand drums to the kit, growing
# ======================================================================
for b in (29, 30):
    for g, n, v in ((0, CONGA_H, 96), (3, CONGA_L, 82), (6, BONGO_H, 92),
                    (8, CONGA_L, 98), (11, CONGA_H, 86), (14, BONGO_L, 94)):
        hit(b, g, n, v)
    for g in (1, 2, 5, 7, 9, 10, 13, 15):
        hit(b, g, CONGA_L, 42)
    for g in (0, 6, 10):
        hit(b, g, KICK, 100 if g == 0 else 88)
    for g in (0, 2, 4, 6, 8, 10, 12, 14):
        hit(b, g, HAT, 74 if g % 4 == 0 else 56)
hit(30, 4, SNARE, 100)
hit(30, 12, SNARE, 104)

# bar 31: toms take the cell back, ride keeps the time
hit(31, 0, CRASH2, 110)
hit(31, 0, KICK, 108)
for g, n, v in ((3, T_HI, 100), (6, T_MID, 98), (8, T_LO, 104),
                (11, T_MID, 100), (14, T_HI, 98)):
    hit(31, g, n, v)
for g in (0, 2, 4, 6, 8, 10, 12, 14):
    hit(31, g, RIDE, 88 if g % 4 == 0 else 70)
hit(31, 4, SNARE, 108)
hit(31, 6, KICK, 96)
hit(31, 10, KICK, 96)
hit(31, 12, SNARE, 110)

# bar 32: build into the development
hit(32, 0, CRASH, 116)
hit(32, 0, KICK, 112)
for g, n, v in ((2, T_HI, 100), (4, SNARE, 108), (6, T_MID, 104),
                (8, T_LO, 108), (10, SNARE, 110), (12, T_FLOOR, 112),
                (13, T_FLOOR, 114), (14, T_LO, 116), (15, SNARE, 118)):
    hit(32, g, n, v)
hit(32, 6, KICK, 100)
hit(32, 10, KICK, 100)


# ======================================================================
# 9. DEVELOPMENT - bars 33-40 : fast, dense, building
# ======================================================================
for b in (33, 34):
    for g in range(16):
        v = 90 if g % 4 == 0 else (66 if g % 2 == 0 else 52)
        hit(b, g, BELL, v)
    hit(b, 4, SNARE, 112)
    hit(b, 12, SNARE, 116)
    for g in (3, 7, 11, 15):
        hit(b, g, SNARE, 38)
    for g in (0, 6, 10, 14):
        hit(b, g, KICK, 108 if g == 0 else 94)

for b in (35, 36):
    hit(b, 0, CRASH if b == 35 else CRASH2, 118)
    hit(b, 0, KICK, 116)
    for g, n, v in ((3, T_HI, 104), (6, T_MID, 102), (8, T_LO, 108),
                    (11, T_FLOOR, 104), (14, T_MID, 102)):
        hit(b, g, n, v)
    for g in (0, 2, 4, 6, 8, 10, 12, 14):
        hit(b, g, RIDE, 86 if g % 4 == 0 else 68)
    hit(b, 6, KICK, 100)
    hit(b, 10, KICK, 100)

# bars 37-38: single strokes on the snare, crescendo
for g in range(16):
    hit(37, g, SNARE, 64 + (g // 4) * 6 + (4 if g % 4 == 0 else 0))
hit(37, 0, KICK, 102)
hit(37, 8, KICK, 98)
for g in range(16):
    hit(38, g, SNARE, 86 + (g // 4) * 5 + (6 if g % 4 == 0 else 0))
hit(38, 0, KICK, 108)
hit(38, 4, KICK, 98)
hit(38, 8, KICK, 106)
hit(38, 12, KICK, 98)

# bars 39-40: the roll travels around the kit
seq39 = [SNARE, SNARE, T_HI, T_HI, T_MID, T_MID, T_LO, T_LO,
         T_FLOOR, T_FLOOR, T_LO, T_MID, T_HI, T_HI, SNARE, SNARE]
for g, n in enumerate(seq39):
    hit(39, g, n, 96 + g // 2)

seq40 = [SNARE, T_HI, SNARE, T_MID, SNARE, T_LO, SNARE, T_FLOOR,
         T_FLOOR, T_LO, T_MID, T_HI, T_MID, T_LO, T_FLOOR, SNARE]
for g, n in enumerate(seq40):
    hit(40, g, n, 102 + g)
hit(40, 0, KICK, 112)
hit(40, 4, KICK, 102)
hit(40, 8, KICK, 112)
hit(40, 12, KICK, 102)


# ======================================================================
# 10. CLIMAX - bars 41-44
# ======================================================================
hit(41, 0, CRASH, 124)
hit(41, 0, KICK, 120)
for g in (0, 2, 4, 6, 8, 10, 12, 14):
    hit(41, g, RIDE, 100 if g % 4 == 0 else 82)
for g in (2, 6, 10, 14):
    hit(41, g, KICK, 104)
hit(41, 4, SNARE, 118)
hit(41, 12, SNARE, 120)

hit(42, 0, CRASH, 122)
hit(42, 0, KICK, 118)
hit(42, 8, CRASH2, 120)
hit(42, 8, KICK, 112)
for g, n, v in ((3, T_HI, 112), (6, T_MID, 110), (11, T_LO, 112), (14, T_MID, 110)):
    hit(42, g, n, v)
hit(42, 4, SNARE, 114)
hit(42, 6, KICK, 102)
hit(42, 10, KICK, 102)
hit(42, 12, SNARE, 116)

# bar 43: groove, open hat and splash on the "and" of 4
hit(43, 0, CRASH, 118)
for g in (0, 2, 4, 6, 8, 10, 12):
    hit(43, g, RIDE, 100 if g % 4 == 0 else 82)
hit(43, 14, OHAT, 108)
hit(43, 14, SPLASH, 100)
hit(43, 0, KICK, 118)
hit(43, 4, SNARE, 118)
hit(43, 6, KICK, 104)
hit(43, 10, KICK, 104)
hit(43, 12, SNARE, 120)
hit(43, 14, KICK, 106)

# bar 44: big fill
hit(44, 0, CRASH2, 120)
hit(44, 0, KICK, 118)
for g, n, v in ((2, T_HI, 108), (3, T_HI, 110), (4, T_MID, 110), (5, T_MID, 112),
                (6, T_LO, 112), (7, T_LO, 114), (8, T_FLOOR, 114), (9, T_FLOOR, 116),
                (10, T_LO, 116), (11, T_MID, 118), (12, T_HI, 118), (13, SNARE, 120),
                (14, SNARE, 122), (15, SNARE, 124)):
    hit(44, g, n, v)


# ======================================================================
# 11. THE CELL RETURNS - bars 45-48
# ======================================================================
for b in (45, 46):
    hit(b, 0, CRASH if b == 45 else CRASH2, 120)
    hit(b, 0, KICK, 116)
    for g, n, v in ((3, T_HI, 108), (6, T_MID, 106), (8, T_LO, 112),
                    (11, T_FLOOR, 108), (14, T_MID, 106)):
        hit(b, g, n, v)
    for g in (0, 2, 4, 6, 8, 10, 12, 14):
        hit(b, g, RIDE, 96 if g % 4 == 0 else 78)
    hit(b, 4, SNARE, 112)
    hit(b, 6, KICK, 104)
    hit(b, 10, KICK, 104)
    hit(b, 12, SNARE, 114)

# bar 47: the cell back on the snare, ghosts everywhere, hats leave room
hit(47, 0, CRASH, 114)
for g, v in zip(MOTIF, (116, 96, 100, 120, 98, 102)):
    hit(47, g, SNARE, v)
for g in (1, 2, 5, 7, 9, 13, 15):
    hit(47, g, SNARE, 40)
for g in (2, 4, 10, 12):
    hit(47, g, HAT, 80)
hit(47, 0, KICK, 114)
hit(47, 10, KICK, 100)
hit(47, 14, KICK, 100)

# bar 48: fill into the finale
hit(48, 0, CRASH, 118)
hit(48, 0, KICK, 114)
for g, n, v in ((2, SNARE, 104), (4, T_HI, 106), (6, T_MID, 108), (8, T_LO, 110),
                (10, T_FLOOR, 112), (12, SNARE, 114), (13, SNARE, 116),
                (14, SNARE, 118), (15, SNARE, 120)):
    hit(48, g, n, v)
hit(48, 4, KICK, 104)
hit(48, 8, KICK, 104)
hit(48, 12, KICK, 104)


# ======================================================================
# 12. FINAL FILL - bars 49-52
# ======================================================================
for g in range(16):
    v = 96 if g % 4 == 0 else (78 if g % 2 == 0 else 64)
    hit(49, g, BELL, v)
hit(49, 0, KICK, 110)
hit(49, 4, SNARE, 112)
hit(49, 6, KICK, 96)
hit(49, 10, KICK, 96)
hit(49, 12, SNARE, 114)
hit(49, 14, KICK, 100)

seq50 = [T_HI, T_HI, T_MID, T_MID, T_LO, T_LO, T_FLOOR, T_FLOOR,
         T_LO, T_LO, T_MID, T_MID, T_HI, T_HI, T_MID, T_LO]
for g, n in enumerate(seq50):
    hit(50, g, n, 104 + g // 2)
hit(50, 0, KICK, 112)
hit(50, 8, KICK, 108)

for g in range(16):
    n = SNARE if g % 2 == 0 else (T_HI if g % 4 == 1 else T_LO)
    hit(51, g, n, 90 + g * 2)
hit(51, 0, KICK, 112)
hit(51, 4, KICK, 104)
hit(51, 8, KICK, 112)
hit(51, 12, KICK, 104)

hit(52, 0, CRASH, 120)
hit(52, 0, KICK, 116)
seq52 = [SNARE, SNARE, T_HI, T_MID, T_LO, T_FLOOR, T_LO, T_MID,
         T_HI, T_MID, T_LO, T_FLOOR, SNARE, T_FLOOR, SNARE, SNARE]
for g, n in enumerate(seq52):
    hit(52, g, n, 106 + g)
hit(52, 8, KICK, 108)
hit(52, 12, KICK, 108)


# ======================================================================
# 13. ENDING - bars 53-54
# ======================================================================
hit(53, 0, CRASH2, 118)
hit(53, 0, KICK, 116)
seq53 = [T_HI, T_HI, T_MID, T_MID, T_LO, T_LO, T_FLOOR, T_FLOOR,
         T_FLOOR, T_LO, T_MID, T_HI, T_MID, T_LO, T_FLOOR, SNARE]
for g, n in enumerate(seq53):
    hit(53, g, n, 108 + g // 2)
hit(53, 8, KICK, 110)

# the last word: crash, china and kick together, then let it ring
hit(54, 0, CRASH, 127)
hit(54, 0, CHINA, 118)
hit(54, 0, KICK, 127)


# ======================================================================
# assemble the MIDI file
# ======================================================================
def prepare():
    """Trim note lengths so a repeated drum is never cut off, and make
    sure no more than two hands and two feet ever strike at once."""
    # 1. same-note overlaps: shorten the earlier stroke
    by_note = defaultdict(list)
    for i, (t, n, v, d) in enumerate(NOTES):
        by_note[n].append((t, i))
    for n, lst in by_note.items():
        lst.sort()
        for k in range(len(lst) - 1):
            t, i = lst[k]
            nxt = lst[k + 1][0]
            if t + NOTES[i][3] > nxt:
                NOTES[i][3] = max(20, nxt - t - 5)

    # 2. playability: at most two hands, at most two feet per instant
    by_tick = defaultdict(list)
    for i, (t, n, v, d) in enumerate(NOTES):
        by_tick[t].append(i)
    dropped = set()
    for t, idxs in by_tick.items():
        hands = [i for i in idxs if NOTES[i][1] not in FEET]
        feet = [i for i in idxs if NOTES[i][1] in FEET]
        for group, limit in ((hands, 2), (feet, 2)):
            if len(group) > limit:
                group.sort(key=lambda i: -NOTES[i][2])
                dropped.update(group[limit:])
    return [NOTES[i] for i in range(len(NOTES)) if i not in dropped]


def main():
    notes = prepare()

    events = []
    for t, n, v, d in notes:
        events.append((t, 2, 'on', n, v))
        events.append((t + d, 1, 'off', n, 0))
    events.sort(key=lambda e: (e[0], e[1]))

    mid = MidiFile(ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('text', text='drum solo - 108 bpm - swung 16ths',
                             time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             clocks_per_click=24, notated_32nd_notes_per_beat=8,
                             time=0))
    track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(TEMPO), time=0))

    last = 0
    for t, _prio, kind, n, v in events:
        dt = t - last
        last = t
        if kind == 'on':
            track.append(Message('note_on', note=n, velocity=v,
                                 channel=CHANNEL, time=dt))
        else:
            track.append(Message('note_off', note=n, velocity=0,
                                 channel=CHANNEL, time=dt))

    track.append(MetaMessage('end_of_track', time=max(0, END_TICK - last)))
    mid.save('solo.mid')


if __name__ == '__main__':
    main()
