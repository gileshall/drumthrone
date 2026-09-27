#!/usr/bin/env python3
"""
drum_solo.py
============

Writes ``solo.mid``: a two-minute General MIDI drum solo on channel 10.

Everything is generated from a fixed RNG seed, so the file produced on every
run is identical.

Structure (57 bars of 4/4):

    0- 3   intro        motif stated quietly, fill into the first downbeat
    4-11   groove       motif A full voice, variations, doubles fill
   12-19   development  motif displaced onto the toms, singles, presses
   20-27   build        density climbs, big fill, sudden release
   28-35   contrast     half-time, rim clicks, ride, swell back up
   36-43   return       motif A fortissimo, then toms and rolls
   44-51   climax       fast singles, thirty-second bursts, huge fill
   52-56   finale       last statement and a single final hit
"""

import random

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

PPQ = 480          # ticks per quarter note
CH = 9             # MIDI channel 10 (zero based)
SEED = 20180611

# --- General MIDI percussion (only 35..81 is used) --------------------------
KICK, KICK2 = 36, 35
SNARE, RIM, CLAP = 38, 37, 39
FLOOR_LO, HAT, FLOOR_HI, PEDAL = 41, 42, 43, 44
TOM_LO, HAT_OPEN, TOM_MID, TOM_MIDHI = 45, 46, 47, 48
CRASH, TOM_HI, RIDE, CHINA, BELL = 49, 50, 51, 52, 53
TAMB, SPLASH, COWBELL, CRASH2, RIDE2 = 54, 55, 56, 57, 59
CONGA_HI, CONGA_LO, TIMB_HI, TIMB_LO = 62, 63, 64, 65
AGOGO_HI, AGOGO_LO, CABASA, MARACAS = 66, 67, 68, 69
CLAVES, WBLOCK_HI, WBLOCK_LO = 74, 75, 76
TRI_MUTE, TRI_OPEN = 79, 80

#: Anything struck by a foot rather than a hand.
FOOT = {KICK, KICK2, PEDAL}

TEMPO_MAP = [
    (0, 108), (4, 112), (8, 112), (12, 116), (16, 116), (20, 118),
    (24, 122), (28, 106), (32, 110), (36, 118), (40, 120), (44, 124),
    (48, 128), (52, 132), (56, 132),
]

rng = random.Random(SEED)

#: [beat, note, velocity, duration_in_beats]
EVENTS = []


# ---------------------------------------------------------------------------
#  Low level helpers
# ---------------------------------------------------------------------------

def T(bar, pos16):
    """Absolute beat of sixteenth-note slot *pos16* of bar *bar*."""
    return bar * 4.0 + pos16 * 0.25


def _vel(v):
    return int(max(1, min(127, round(v))))


def hit(beat, note, vel, dur=0.10, jit=0.013):
    """One drum stroke, placed by a pair of human hands."""
    EVENTS.append([beat + rng.uniform(-jit, jit),
                   note,
                   _vel(vel + rng.gauss(0.0, 1.8)),
                   max(0.02, dur * rng.uniform(0.90, 1.15))])


def play(beat, pairs, jit=0.013):
    """Two hands (or hand + foot) landing together, very nearly in sync."""
    t = beat + rng.uniform(-jit, jit)
    for item in pairs:
        note, vel = item[0], item[1]
        dur = item[2] if len(item) > 2 else 0.10
        EVENTS.append([t + rng.uniform(-0.006, 0.006),
                       note,
                       _vel(vel + rng.gauss(0.0, 1.8)),
                       max(0.02, dur * rng.uniform(0.90, 1.15))])


def hat8(bar, vel, acc=(4, 12), acc_amt=14, note=HAT, dur=0.10, skip=()):
    """Eighth notes on a cymbal with a pair of accents."""
    for p in range(0, 16, 2):
        if p in skip:
            continue
        hit(T(bar, p), note, vel + (acc_amt if p in acc else 0), dur)


def hat16(bar, vel, acc=(0, 4, 8, 12), acc_amt=14, note=HAT, dur=0.08, skip=()):
    """Sixteenth notes on a cymbal: eighths stronger than the in-betweens."""
    for p in range(16):
        if p in skip:
            continue
        v = vel + (acc_amt if p in acc else 0) - (5 if p % 2 else 0)
        hit(T(bar, p), note, v, dur)


def run16(bar, notes, v0, v1, start=0, accents=(), dur=0.08):
    """A run of sixteenths across the kit, with a crescendo built in."""
    n = len(notes)
    for i, note in enumerate(notes):
        f = i / max(1, n - 1)
        v = v0 + (v1 - v0) * f
        if (start + i) in accents:
            v += 10
        hit(T(bar, start + i), note, v, dur)


# ---------------------------------------------------------------------------
#  The music
# ---------------------------------------------------------------------------

def compose():
    # =====================================================================
    #  1. INTRO -- bars 0..3
    # =====================================================================

    # bar 0 : the motif, stated softly
    hat8(0, 52)
    hit(T(0, 0), KICK, 88)
    hit(T(0, 10), KICK, 68)
    hit(T(0, 4), SNARE, 80)
    hit(T(0, 12), SNARE, 84)
    hit(T(0, 15), SNARE, 30)

    # bar 1 : identical shape, different detail
    hat8(1, 54)
    hit(T(1, 0), KICK, 92)
    hit(T(1, 6), KICK, 66)
    hit(T(1, 10), KICK, 72)
    hit(T(1, 4), SNARE, 82)
    hit(T(1, 12), SNARE, 86)
    hit(T(1, 7), SNARE, 32)
    hit(T(1, 14), SNARE, 28)

    # bar 2 : the beat opens out, then a rising pickup
    hat8(2, 56, skip=(8, 12))
    hit(T(2, 0), KICK, 94)
    hit(T(2, 6), KICK, 70)
    hit(T(2, 10), KICK, 74)
    hit(T(2, 4), SNARE, 84)
    for p, n, v in ((8, SNARE, 60), (9, SNARE, 56),
                    (10, SNARE, 64), (11, SNARE, 58),
                    (12, TOM_MID, 76), (13, SNARE, 66),
                    (14, TOM_LO, 78), (15, SNARE, 72)):
        hit(T(2, p), n, v)

    # bar 3 : the fill that carries into the first crash
    fill_intro = [SNARE, SNARE, TOM_HI, SNARE,
                  TOM_HI, TOM_MIDHI, SNARE, TOM_MIDHI,
                  TOM_MID, TOM_MIDHI, TOM_MID, TOM_LO,
                  FLOOR_HI, TOM_LO, FLOOR_HI, FLOOR_LO]
    run16(3, fill_intro, 58, 120, accents=(0, 4, 8, 12), dur=0.09)

    # =====================================================================
    #  2. GROOVE -- bars 4..11
    # =====================================================================

    # bar 4 : motif A at full voice
    hit(T(4, 0), CRASH, 106, 1.0)
    hit(T(4, 0), KICK, 104)
    hat8(4, 70, skip=(0,))
    hit(T(4, 6), KICK, 78)
    hit(T(4, 10), KICK, 88)
    hit(T(4, 4), SNARE, 100)
    hit(T(4, 12), SNARE, 104)
    hit(T(4, 3), SNARE, 40)
    hit(T(4, 7), SNARE, 36)
    hit(T(4, 15), SNARE, 34)

    # bar 5 : the open hi-hat lets the phrase breathe
    hat8(5, 70, skip=(12, 14))
    hit(T(5, 14), HAT_OPEN, 76, 0.45)
    hit(T(5, 0), KICK, 100)
    hit(T(5, 6), KICK, 76)
    hit(T(5, 10), KICK, 84)
    hit(T(5, 11), KICK, 58)
    hit(T(5, 4), SNARE, 100)
    hit(T(5, 12), SNARE, 102)
    hit(T(5, 3), SNARE, 38)
    hit(T(5, 7), SNARE, 34)

    # bar 6 : ride bell, looser kick
    for p in range(0, 16, 2):
        if p % 4 == 0:
            hit(T(6, p), BELL, 74, 0.30)
        else:
            hit(T(6, p), RIDE, 58, 0.22)
    hit(T(6, 0), KICK, 100)
    hit(T(6, 6), KICK, 76)
    hit(T(6, 10), KICK, 84)
    hit(T(6, 4), SNARE, 98)
    hit(T(6, 12), SNARE, 102)
    hit(T(6, 9), SNARE, 36)
    hit(T(6, 15), SNARE, 32)

    # bar 7 : sixteenths creep in and push toward the fill
    hat8(7, 68, skip=(14,))
    for p in (9, 11, 13, 15):
        hit(T(7, p), HAT, 48 + (p - 9) * 1.6, 0.07)
    hit(T(7, 0), KICK, 102)
    hit(T(7, 6), KICK, 78)
    hit(T(7, 10), KICK, 86)
    hit(T(7, 4), SNARE, 100)
    hit(T(7, 12), SNARE, 104)
    hit(T(7, 7), SNARE, 36)
    hit(T(7, 14), SNARE, 32)

    # bar 8 : denser phrasing
    hat16(8, 60, skip=(13,))
    hit(T(8, 0), KICK, 102)
    hit(T(8, 6), KICK, 76)
    hit(T(8, 10), KICK, 86)
    hit(T(8, 13), KICK, 64)
    hit(T(8, 4), SNARE, 98)
    hit(T(8, 12), SNARE, 102)
    for p in (3, 7, 11, 15):
        hit(T(8, p), SNARE, 32)

    # bar 9 : same idea, accents moved around
    hat16(9, 60, skip=(11,))
    hit(T(9, 3), KICK, 56)
    hit(T(9, 0), KICK, 104)
    hit(T(9, 6), KICK, 78)
    hit(T(9, 10), KICK, 88)
    hit(T(9, 11), KICK, 62)
    hit(T(9, 4), SNARE, 100)
    hit(T(9, 12), SNARE, 104)
    for p in (7, 14):
        hit(T(9, p), SNARE, 34)

    # bar 10 : crescendo with the hats
    for p in range(16):
        v = 54 + (p / 15.0) * 28 + (10 if p % 4 == 0 else 0)
        hit(T(10, p), HAT, v, 0.08)
    hit(T(10, 0), KICK, 104)
    hit(T(10, 8), KICK, 92)
    hit(T(10, 4), SNARE, 100)
    hit(T(10, 12), SNARE, 104)
    hit(T(10, 14), SNARE, 58)

    # bar 11 : doubles travel down the kit
    fill_11 = [SNARE, SNARE, SNARE, SNARE,
               TOM_HI, TOM_HI, TOM_MIDHI, TOM_MIDHI,
               TOM_MID, TOM_MID, TOM_LO, TOM_LO,
               FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO]
    run16(11, fill_11, 68, 124, accents=(0, 4, 8, 12))

    # =====================================================================
    #  3. DEVELOPMENT -- bars 12..19
    # =====================================================================

    # bar 12 : crash, then the motif restated on the toms (hands only)
    hit(T(12, 0), CRASH, 110, 1.0)
    hit(T(12, 0), TOM_HI, 100, 0.30)
    hit(T(12, 0), KICK, 106)
    hit(T(12, 4), TOM_HI, 92, 0.30)
    hit(T(12, 6), TOM_MIDHI, 70, 0.30)
    hit(T(12, 10), TOM_MID, 88, 0.30)
    hit(T(12, 12), TOM_LO, 94, 0.30)
    hit(T(12, 14), TOM_LO, 58, 0.30)

    # bar 13 : the answer, lower, with the kick back underneath
    hat8(13, 56, skip=(4, 6, 10, 12))
    hit(T(13, 0), KICK, 100)
    hit(T(13, 0), TOM_MID, 96, 0.30)
    hit(T(13, 4), TOM_MIDHI, 90, 0.30)
    hit(T(13, 6), TOM_MID, 72, 0.30)
    hit(T(13, 8), KICK, 88)
    hit(T(13, 10), TOM_LO, 86, 0.30)
    hit(T(13, 12), FLOOR_HI, 94, 0.30)
    hit(T(13, 14), TOM_LO, 62, 0.30)

    # bar 14 : doubles falling down the toms
    seq14 = [SNARE, SNARE, TOM_HI, TOM_HI, TOM_MIDHI, TOM_MIDHI, TOM_MID, TOM_MID,
             TOM_LO, TOM_LO, FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, TOM_LO, FLOOR_HI]
    hit(T(14, 0), KICK, 100)
    run16(14, seq14, 74, 112, accents=(0, 4, 8, 12))

    # bar 15 : running back up
    seq15 = [FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MID, TOM_MIDHI, TOM_HI, SNARE, SNARE,
             TOM_HI, TOM_MIDHI, TOM_MID, TOM_LO, FLOOR_HI, FLOOR_LO, SNARE, SNARE]
    hit(T(15, 0), KICK, 104)
    hit(T(15, 8), KICK, 96)
    run16(15, seq15, 76, 114, accents=(0, 4, 8, 12))

    # bar 16 : a pressing roll starts to build
    for i in range(16):
        hit(T(16, i), SNARE, 54 + i * 2.2 + (6 if i % 4 == 0 else 0), 0.07)

    # bar 17 : doubles it, thirty-seconds, still rising
    for i in range(32):
        p = i * 0.5
        v = 76 + (i / 31.0) * 34 + (6 if i % 8 == 0 else 0)
        if i < 24:
            n = SNARE
        elif i < 28:
            n = TOM_HI
        else:
            n = TOM_MIDHI
        hit(T(17, p), n, v, 0.06)

    # bar 18 : accents against ghosts
    accent_pat = (0, 3, 4, 6, 8, 10, 11, 14)
    for i in range(16):
        n = SNARE
        v = 104 if i in accent_pat else 44
        if i >= 12:
            n = TOM_MIDHI if i % 2 else TOM_MID
        hit(T(18, i), n, v, 0.08)

    # bar 19 : fill into the build
    fill_19 = [SNARE, TOM_HI, SNARE, TOM_HI, TOM_MIDHI, TOM_MID, TOM_MIDHI, TOM_MID,
               TOM_LO, FLOOR_HI, TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_LO, FLOOR_LO, FLOOR_LO]
    run16(19, fill_19, 78, 120, accents=(0, 4, 8, 12))

    # =====================================================================
    #  4. BUILD -- bars 20..27
    # =====================================================================

    # bar 20
    hit(T(20, 0), CRASH, 112, 1.0)
    hit(T(20, 0), KICK, 108)
    hat16(20, 62)
    hit(T(20, 6), KICK, 80)
    hit(T(20, 10), KICK, 88)
    hit(T(20, 4), SNARE, 102)
    hit(T(20, 12), SNARE, 106)
    for p in (3, 7, 15):
        hit(T(20, p), SNARE, 34)

    # bar 21
    hat16(21, 62, skip=(11,))
    hit(T(21, 0), KICK, 106)
    hit(T(21, 6), KICK, 78)
    hit(T(21, 7), KICK, 56)
    hit(T(21, 10), KICK, 88)
    hit(T(21, 11), KICK, 60)
    hit(T(21, 4), SNARE, 102)
    hit(T(21, 12), SNARE, 106)
    hit(T(21, 3), SNARE, 34)
    hit(T(21, 14), SNARE, 32)

    # bar 22 : motif onto the toms, the cymbal thins out
    hat8(22, 54, skip=(0, 4, 6, 10, 12))
    hit(T(22, 0), KICK, 106)
    hit(T(22, 0), TOM_HI, 96, 0.30)
    hit(T(22, 4), TOM_HI, 88, 0.30)
    hit(T(22, 6), TOM_MIDHI, 66, 0.30)
    hit(T(22, 8), TOM_MIDHI, 82, 0.30)
    hit(T(22, 10), TOM_MID, 84, 0.30)
    hit(T(22, 12), TOM_LO, 92, 0.30)
    hit(T(22, 14), TOM_LO, 56, 0.30)

    # bar 23 : answer phrase, lower again
    hat8(23, 54, skip=(0, 4, 6, 8, 12, 14))
    hit(T(23, 0), KICK, 104)
    hit(T(23, 0), TOM_MID, 94, 0.30)
    hit(T(23, 4), TOM_MIDHI, 86, 0.30)
    hit(T(23, 6), TOM_MID, 68, 0.30)
    hit(T(23, 8), KICK, 92)
    hit(T(23, 8), TOM_LO, 82, 0.30)
    hit(T(23, 12), FLOOR_HI, 94, 0.30)
    hit(T(23, 14), FLOOR_LO, 60, 0.30)

    # bar 24 : hands tighten, dynamics rise
    for p in range(16):
        hit(T(24, p), HAT, 58 + p * 2.2 + (8 if p % 4 == 0 else 0), 0.08)
    hit(T(24, 0), KICK, 106)
    hit(T(24, 8), KICK, 96)
    hit(T(24, 4), SNARE, 102)
    hit(T(24, 12), SNARE, 106)
    hit(T(24, 14), SNARE, 66)

    # bar 25 : doubles on the snare dissolving into the toms
    for i in range(16):
        v = 68 + i * 3
        if i < 8:
            n = SNARE
        elif i < 12:
            n = TOM_MIDHI if i % 2 == 0 else TOM_HI
        else:
            n = TOM_LO if i % 2 == 0 else TOM_MID
        hit(T(25, i), n, v, 0.08)

    # bar 26 : first half of the big fill
    fill_26 = [SNARE, SNARE, TOM_HI, TOM_HI, TOM_MIDHI, TOM_MIDHI, TOM_MID, TOM_MID,
               TOM_LO, TOM_LO, FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, TOM_LO, FLOOR_HI]
    run16(26, fill_26, 82, 122, accents=(0, 4, 8, 12))

    # bar 27 : the fill exhales -- a beat of silence before the release
    fill_27 = [SNARE, TOM_HI, TOM_MIDHI, TOM_MIDHI, TOM_MID, TOM_MID,
               TOM_LO, TOM_LO, FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO]
    run16(27, fill_27, 100, 62, dur=0.10)

    # =====================================================================
    #  5. CONTRAST -- bars 28..35
    # =====================================================================

    # bar 28 : the release -- half time, ride, lots of air
    hit(T(28, 0), SPLASH, 74, 0.9)
    hit(T(28, 0), KICK, 84)
    hit(T(28, 10), KICK, 62)
    for p in range(0, 16, 2):
        hit(T(28, p), RIDE, 46 + (8 if p % 8 == 0 else 0), 0.22)
    hit(T(28, 8), SNARE, 78)
    hit(T(28, 12), RIM, 44)
    hit(T(28, 15), SNARE, 26)

    # bar 29
    hit(T(29, 0), KICK, 86)
    hit(T(29, 6), KICK, 54)
    hit(T(29, 10), KICK, 64)
    for p in range(0, 16, 2):
        hit(T(29, p), RIDE, 48 + (8 if p % 8 == 0 else 0), 0.22)
    hit(T(29, 8), SNARE, 80)
    hit(T(29, 12), RIM, 46)
    hit(T(29, 3), SNARE, 26)
    hit(T(29, 15), SNARE, 26)

    # bar 30 : foot hat anchors the pulse
    for p in (0, 8):
        hit(T(30, p), PEDAL, 54, 0.16)
    hit(T(30, 0), KICK, 88)
    hit(T(30, 10), KICK, 66)
    for p in range(0, 16, 2):
        hit(T(30, p), RIDE, 50 + (8 if p % 8 == 0 else 0), 0.22)
    hit(T(30, 8), SNARE, 82)
    hit(T(30, 12), RIM, 48)
    hit(T(30, 11), SNARE, 26)

    # bar 31 : a small pickup out of the quiet
    for p in range(0, 16, 2):
        hit(T(31, p), RIDE, 50, 0.22)
    hit(T(31, 0), KICK, 90)
    hit(T(31, 8), SNARE, 84)
    for i, (p, n) in enumerate(((12, SNARE), (13, SNARE),
                                (14, TOM_MID), (15, TOM_LO))):
        hit(T(31, p), n, 60 + i * 6, 0.10)

    # bar 32 : hats come back, still just above a whisper
    for p in range(0, 16, 2):
        hit(T(32, p), HAT, 54 + (8 if p % 8 == 0 else 0), 0.10)
    hit(T(32, 0), KICK, 92)
    hit(T(32, 6), KICK, 70)
    hit(T(32, 8), SNARE, 88)
    hit(T(32, 12), SNARE, 92)
    hit(T(32, 3), SNARE, 30)
    hit(T(32, 15), SNARE, 28)

    # bar 33
    hat16(33, 54, acc=(0, 8), acc_amt=8)
    hit(T(33, 0), KICK, 96)
    hit(T(33, 6), KICK, 72)
    hit(T(33, 8), SNARE, 92)
    hit(T(33, 12), SNARE, 96)
    hit(T(33, 11), SNARE, 30)
    hit(T(33, 14), SNARE, 26)

    # bar 34 : crescendo
    for p in range(16):
        hit(T(34, p), HAT, 60 + p * 2.4 + (8 if p % 4 == 0 else 0), 0.08)
    hit(T(34, 0), KICK, 100)
    hit(T(34, 8), KICK, 92)
    hit(T(34, 4), SNARE, 96)
    hit(T(34, 12), SNARE, 100)

    # bar 35 : the fill that sets the motif free again
    fill_35 = [SNARE, SNARE, TOM_HI, TOM_HI, TOM_MIDHI, TOM_MIDHI, TOM_MID, TOM_MID,
               TOM_LO, TOM_LO, FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, TOM_LO, FLOOR_LO]
    run16(35, fill_35, 78, 122, accents=(0, 4, 8, 12))

    # =====================================================================
    #  6. RETURN -- bars 36..43
    # =====================================================================

    # bar 36 : motif A, fortissimo
    hit(T(36, 0), CRASH, 118, 1.2)
    hit(T(36, 0), KICK, 112)
    hat8(36, 78, skip=(0,))
    hit(T(36, 6), KICK, 86)
    hit(T(36, 10), KICK, 96)
    hit(T(36, 4), SNARE, 108)
    hit(T(36, 12), SNARE, 112)
    hit(T(36, 3), SNARE, 46)
    hit(T(36, 7), SNARE, 40)
    hit(T(36, 15), SNARE, 36)

    # bar 37 : crash moves to beat three
    hit(T(37, 0), KICK, 110)
    hit(T(37, 8), CRASH2, 102, 1.0)
    hit(T(37, 8), SNARE, 106)
    hat8(37, 78, skip=(8,))
    hit(T(37, 6), KICK, 84)
    hit(T(37, 10), KICK, 92)
    hit(T(37, 4), SNARE, 106)
    hit(T(37, 12), SNARE, 110)
    hit(T(37, 14), SNARE, 42)

    # bar 38 : bell groove, widescreen
    for p in range(0, 16, 2):
        if p % 4 == 0:
            hit(T(38, p), BELL, 78, 0.28)
        else:
            hit(T(38, p), RIDE, 60, 0.24)
    hit(T(38, 0), KICK, 110)
    hit(T(38, 6), KICK, 84)
    hit(T(38, 10), KICK, 92)
    hit(T(38, 4), SNARE, 106)
    hit(T(38, 12), SNARE, 110)
    hit(T(38, 9), SNARE, 38)

    # bar 39 : sixteenth hats and syncopated kick
    hat16(39, 66, skip=(11,))
    hit(T(39, 0), KICK, 110)
    hit(T(39, 6), KICK, 82)
    hit(T(39, 7), KICK, 60)
    hit(T(39, 10), KICK, 94)
    hit(T(39, 11), KICK, 64)
    hit(T(39, 4), SNARE, 106)
    hit(T(39, 12), SNARE, 110)
    hit(T(39, 3), SNARE, 38)
    hit(T(39, 15), SNARE, 34)

    # bar 40 : motif displaced onto the toms again
    hat8(40, 62, skip=(0, 4, 6, 10, 12))
    hit(T(40, 0), KICK, 108)
    hit(T(40, 0), TOM_HI, 104, 0.30)
    hit(T(40, 4), TOM_HI, 96, 0.30)
    hit(T(40, 6), TOM_MIDHI, 74, 0.30)
    hit(T(40, 8), TOM_MIDHI, 90, 0.30)
    hit(T(40, 10), TOM_MID, 92, 0.30)
    hit(T(40, 12), TOM_LO, 100, 0.30)
    hit(T(40, 14), TOM_LO, 62, 0.30)

    # bar 41 : doubles rolling down
    seq41 = [SNARE, SNARE, TOM_HI, TOM_HI, TOM_MIDHI, TOM_MIDHI, TOM_MID, TOM_MID,
             TOM_LO, TOM_LO, FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, TOM_LO, FLOOR_LO]
    hit(T(41, 0), KICK, 106)
    run16(41, seq41, 84, 116, accents=(0, 4, 8, 12))

    # bar 42 : racing back up the kit
    seq42 = [FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MID, TOM_MIDHI, TOM_HI, SNARE, SNARE,
             TOM_HI, TOM_MIDHI, TOM_MID, TOM_LO, FLOOR_HI, FLOOR_LO, SNARE, TOM_HI]
    hit(T(42, 0), KICK, 108)
    hit(T(42, 8), KICK, 100)
    run16(42, seq42, 86, 118, accents=(0, 4, 8, 12))

    # bar 43 : snare roll with accents, still climbing
    for i in range(16):
        v = 74 + i * 2.6 + (10 if i % 4 == 0 else 0)
        hit(T(43, i), SNARE, v, 0.08)

    # =====================================================================
    #  7. CLIMAX -- bars 44..51
    # =====================================================================

    # bar 44 : crash and a charge around the kit
    hit(T(44, 0), CRASH, 120, 1.3)
    hit(T(44, 0), KICK, 114)
    pat44 = [SNARE, TOM_HI, TOM_MIDHI, TOM_MID, TOM_LO, FLOOR_HI, FLOOR_LO, TOM_LO,
             TOM_MID, TOM_MIDHI, TOM_HI, SNARE, TOM_HI, TOM_MIDHI, TOM_MID, TOM_LO]
    for i, n in enumerate(pat44):
        v = 88 + (12 if i % 4 == 0 else 0) - (4 if i % 2 else 0)
        hit(T(44, i), n, v, 0.08)
    hit(T(44, 8), KICK, 96)

    # bar 45 : the same idea running the other way
    pat45 = [FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MID, TOM_MIDHI, TOM_HI, SNARE, TOM_HI,
             TOM_MIDHI, TOM_MID, TOM_LO, FLOOR_HI, FLOOR_LO, TOM_LO, TOM_MID, SNARE]
    hit(T(45, 0), KICK, 112)
    hit(T(45, 4), KICK, 92)
    hit(T(45, 12), KICK, 96)
    for i, n in enumerate(pat45):
        v = 88 + (12 if i % 4 == 0 else 0) - (4 if i % 2 else 0)
        hit(T(45, i), n, v, 0.08)

    # bar 46 : thirty-second bursts, rolling accents
    for i in range(32):
        p = i * 0.5
        v = 76 + (i % 8) * 3 + (10 if i % 8 == 0 else 0)
        hit(T(46, p), SNARE, v, 0.06)

    # bar 47 : the burst travels onto the toms
    for i in range(32):
        p = i * 0.5
        v = 80 + (i % 8) * 3 + (10 if i % 8 == 0 else 0)
        if i < 8:
            n = SNARE
        elif i < 16:
            n = TOM_HI
        elif i < 24:
            n = TOM_MIDHI
        else:
            n = TOM_MID
        hit(T(47, p), n, v, 0.06)

    # bar 48 : full-tilt sixteenth groove
    hit(T(48, 0), CRASH2, 118, 1.0)
    hit(T(48, 0), KICK, 114)
    hat16(48, 70)
    hit(T(48, 6), KICK, 88)
    hit(T(48, 10), KICK, 96)
    hit(T(48, 4), SNARE, 110)
    hit(T(48, 12), SNARE, 114)
    for p in (3, 7, 15):
        hit(T(48, p), SNARE, 42)

    # bar 49 : the motif on the toms, huge
    hat16(49, 66, skip=(0, 2, 4, 6, 8, 10, 12, 14))
    hit(T(49, 0), KICK, 114)
    hit(T(49, 0), TOM_HI, 110, 0.30)
    hit(T(49, 2), TOM_MIDHI, 84, 0.25)
    hit(T(49, 4), TOM_HI, 100, 0.25)
    hit(T(49, 6), TOM_MIDHI, 78, 0.25)
    hit(T(49, 8), TOM_MIDHI, 96, 0.25)
    hit(T(49, 10), TOM_MID, 98, 0.25)
    hit(T(49, 12), TOM_LO, 106, 0.25)
    hit(T(49, 14), TOM_LO, 68, 0.25)

    # bar 50 : subdivisions double as the roll swells
    for i in range(8):
        hit(T(50, i), SNARE, 66 + i * 4, 0.07)
    for i in range(16):
        hit(T(50, 8 + i * 0.5), SNARE, 92 + i * 1.8, 0.06)

    # bar 51 : the roll turns into a fill
    pat51 = [SNARE, SNARE, SNARE, SNARE,
             TOM_HI, TOM_HI, TOM_HI, TOM_HI,
             TOM_MIDHI, TOM_MIDHI, TOM_MIDHI, TOM_MIDHI,
             TOM_MID, TOM_MID, TOM_MID, TOM_MID]
    hit(T(51, 0), KICK, 116)
    run16(51, pat51, 90, 124, accents=(0, 4, 8, 12), dur=0.07)

    # =====================================================================
    #  8. FINALE -- bars 52..56
    # =====================================================================

    # bar 52 : last full statement
    hit(T(52, 0), CRASH, 122, 1.4)
    hit(T(52, 0), KICK, 116)
    hat16(52, 72)
    hit(T(52, 6), KICK, 90)
    hit(T(52, 10), KICK, 98)
    hit(T(52, 4), SNARE, 112)
    hit(T(52, 12), SNARE, 116)
    for p in (3, 7, 15):
        hit(T(52, p), SNARE, 44)

    # bar 53 : variation, extra kick movement
    hat16(53, 72, skip=(11,))
    hit(T(53, 0), KICK, 116)
    hit(T(53, 6), KICK, 88)
    hit(T(53, 7), KICK, 62)
    hit(T(53, 10), KICK, 98)
    hit(T(53, 11), KICK, 68)
    hit(T(53, 4), SNARE, 112)
    hit(T(53, 12), SNARE, 116)
    hit(T(53, 3), SNARE, 44)
    hit(T(53, 14), SNARE, 40)

    # bar 54 : final swell
    for i in range(8):
        hit(T(54, i), SNARE, 70 + i * 5, 0.07)
    for i in range(16):
        hit(T(54, 8 + i * 0.5), SNARE, 104 + i * 1.3, 0.06)

    # bar 55 : the last fill
    pat55 = [SNARE, SNARE, SNARE, SNARE,
             TOM_HI, TOM_HI, TOM_MIDHI, TOM_MIDHI,
             TOM_MID, TOM_MID, TOM_LO, TOM_LO,
             FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO]
    hit(T(55, 0), KICK, 118)
    run16(55, pat55, 100, 127, accents=(0, 4, 8, 12), dur=0.07)

    # bar 56 : land it
    play(T(56, 0), [(CRASH, 127, 4.0), (CRASH2, 120, 4.0), (KICK, 120, 1.0)])


# ---------------------------------------------------------------------------
#  Playability guard -- one drummer, two hands, two feet
# ---------------------------------------------------------------------------

def enforce_playability():
    """Never let more than two hands or two feet strike at the same instant."""
    window = 0.04                     # ~20 ms
    ev = sorted(EVENTS, key=lambda e: e[0])
    keep = [True] * len(ev)
    for i in range(len(ev)):
        if not keep[i]:
            continue
        group = [i]
        j = i + 1
        while j < len(ev) and ev[j][0] - ev[i][0] <= window:
            if keep[j]:
                group.append(j)
            j += 1
        hands = [k for k in group if ev[k][1] not in FOOT]
        feet = [k for k in group if ev[k][1] in FOOT]
        for limb, limit in ((hands, 2), (feet, 2)):
            if len(limb) > limit:
                limb.sort(key=lambda k: ev[k][2])
                for k in limb[:len(limb) - limit]:
                    keep[k] = False
    EVENTS[:] = [e for e, k in zip(ev, keep) if k]


# ---------------------------------------------------------------------------
#  Assemble the MIDI file
# ---------------------------------------------------------------------------

def write_midi(path='solo.mid'):
    msgs = []                          # (tick, ordering, message)

    for bar, bpm in TEMPO_MAP:
        msgs.append((bar * 4 * PPQ, 0,
                     MetaMessage('set_tempo', tempo=bpm2tempo(bpm))))

    # Percussion voices in General MIDI are one-shot, so no note_off is
    # emitted: a note_off would chop the ring off the cymbals.
    for beat, note, vel, _dur in EVENTS:
        tick = int(round(beat * PPQ))
        if tick < 0:
            tick = 0
        msgs.append((tick, 2,
                     Message('note_on', note=int(note), velocity=int(vel),
                             channel=CH)))

    msgs.sort(key=lambda m: (m[0], m[1]))

    mid = MidiFile(type=1, ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             time=0))

    last = 0
    for tick, _order, msg in msgs:
        msg.time = tick - last
        last = tick
        track.append(msg)

    # a little air after the last hit so the final crash can ring out
    track.append(MetaMessage('marker', text='end', time=4 * PPQ))

    mid.save(path)


# ---------------------------------------------------------------------------

def main():
    compose()
    enforce_playability()
    write_midi('solo.mid')
    print('wrote solo.mid  (%d notes)' % len(EVENTS))


if __name__ == '__main__':
    main()
