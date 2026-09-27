#!/usr/bin/env python3
"""
drum_solo.py

Writes 'solo.mid' into the current directory: a two minute solo drum
performance rendered for a General MIDI synthesiser on MIDI channel 10.

The piece is composed from a couple of rhythmic motifs that get stated,
varied, displaced, re-voiced and brought back, over a tempo map that
accelerates and broadens.  Every note is placed by hand-written phrase
logic and micro-timed with a fixed seed, so the produced file is byte for
byte identical on every run.

Requires only mido.
"""

import random

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------
PPQ = 480
CHANNEL = 9              # zero based -> MIDI channel 10
SEED = 20240607

# --- General MIDI percussion key map ---------------------------------------
KICK, KICK2 = 36, 35
STICK = 37
SNARE, SNARE_E = 38, 40
HAT, PHAT, OHAT = 42, 44, 46
RIDE, RIDE2, BELL = 51, 59, 53
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
T_HI, T_HM, T_LM, T_LO, T_HF, T_LF = 50, 48, 47, 45, 43, 41
TAMB, COW, WB_HI, WB_LO, CLAVES = 54, 56, 76, 77, 75

R = random.Random(SEED)

events = []              # (beat, note, velocity, duration_beats, limb)
CYMBALS = set()          # beats already claimed by a cymbal stroke

# ---------------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------------


def h(beat, note, vel, limb, dur=0.25, jt=0.005):
    """Add one stroke: human timing scatter is applied here."""
    v = int(round(vel))
    v = 1 if v < 1 else (127 if v > 127 else v)
    events.append((beat + R.uniform(-jt, jt), note, v, dur, limb))


def crash(beat, vel=118, dur=4.0, note=CRASH):
    """A cymbal stroke; remembers the beat so no time-voice doubles it."""
    CYMBALS.add(round(beat, 6))
    h(beat, note, vel, 'RH', dur, jt=0.004)


def time_voice(bar, style='ride', energy=0.6, skip=(), openhat=()):
    """The cymbal / hi-hat continuum of one bar (eight notes)."""
    b = bar * 4.0
    skip = set(skip) | CYMBALS
    for i in range(8):
        p = i * 0.5
        if round(b + p, 6) in skip:
            continue
        if p in openhat:
            h(b + p, OHAT, 88 + 22 * energy, 'RH', 0.5, jt=0.006)
            continue
        if style == 'ride':
            note = BELL if i in (0, 4) else RIDE
            v = (94 if i % 2 == 0 else 76) + 10 * energy
        elif style == 'hat':
            note = HAT
            v = (86 if i % 2 == 0 else 68) + 12 * energy
        else:
            note = RIDE2
            v = (90 if i % 2 == 0 else 74) + 10 * energy
        h(b + p, note, v + R.uniform(-4, 4), 'RH', 0.5, jt=0.006)


def groove_bar(bar, style='ride', energy=0.6, ghost=0.5, kick=(0.0, 2.0),
               crash_beats=(), skip=(), snare=(1.0, 3.0), openhat=(), gpos=None):
    """One bar of time playing: cymbal + backbeats + ghosts + bass drum."""
    b = bar * 4.0
    for p in crash_beats:
        crash(b + p, 112 + 14 * energy)
    time_voice(bar, style, energy, skip=skip, openhat=openhat)
    for p in snare:
        h(b + p + 0.010, SNARE, 94 + 16 * energy + R.uniform(-5, 5), 'LH', 0.25)
    if ghost > 0:
        positions = gpos if gpos is not None else \
            (0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75)
        for p in positions:
            if R.random() < ghost * 0.75:
                h(b + p, SNARE, 20 + 20 * R.random() + 14 * energy,
                  'LH', 0.2, jt=0.012)
    for p in kick:
        h(b + p, KICK, 96 + 20 * energy + R.uniform(-5, 5), 'RF', 0.25)


# --- the main motif ---------------------------------------------------------
# two beats of 16ths: kick - snare - ghost - kick - snare - ghost
MOTIF = ((0.00, 'K', 1.00),
         (0.50, 'S', 1.00),
         (0.75, 'g', 0.34),
         (1.00, 'K', 0.80),
         (1.50, 'S', 1.00),
         (1.75, 'g', 0.34))


def motif(beat, loud=0.6, kick_note=KICK, snare_note=SNARE, ghost_note=SNARE,
          invert=False, lt=0.0):
    """State the motif; lt loosens/tightens the internal timing."""
    for off, kind, w in MOTIF:
        t = beat + off * (1.0 + lt)
        if kind == 'K':
            note, limb = (snare_note, 'LH') if invert else (kick_note, 'RF')
            v = (58 + 62 * loud) * w
        elif kind == 'S':
            note, limb = (kick_note, 'RF') if invert else (snare_note, 'LH')
            v = (54 + 66 * loud) * w
        else:
            note, limb = ghost_note, 'LH'
            v = 10 + 26 * loud + 12 * R.random()
        h(t, note, v, limb, 0.25, jt=0.006)


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------


def sec_intro():
    # --- bar 0 -------------------------------------------------------------
    crash(0.0, 124, 6.0)
    h(0.00, KICK, 114, 'RF')
    h(0.75, SNARE, 34, 'LH', 0.2, jt=0.010)
    h(1.00, SNARE, 108, 'LH')
    h(1.50, SNARE, 30, 'LH', 0.2, jt=0.010)
    h(1.75, SNARE, 26, 'LH', 0.2, jt=0.010)
    h(2.00, KICK, 104, 'RF')
    h(2.25, SNARE, 36, 'LH', 0.2, jt=0.010)
    h(2.50, SNARE, 100, 'LH')
    h(3.00, T_HM, 98, 'RH')
    h(3.25, T_LM, 88, 'LH')
    h(3.50, T_LO, 94, 'RH')
    h(3.75, SNARE, 104, 'LH')

    # --- bar 1 : laid back, rim clicks and ghosts --------------------------
    h(4.00, KICK, 96, 'RF')
    h(4.00, STICK, 88, 'RH')
    h(4.50, SNARE, 30, 'LH', 0.2, jt=0.010)
    h(5.00, SNARE, 76, 'RH')
    h(5.50, SNARE, 28, 'LH', 0.2, jt=0.010)
    h(5.75, SNARE, 34, 'RH', 0.2, jt=0.010)
    h(6.00, KICK, 94, 'RF')
    h(6.00, STICK, 84, 'LH')
    h(6.50, SNARE, 38, 'RH', 0.2, jt=0.010)
    h(6.75, SNARE, 32, 'LH', 0.2, jt=0.010)
    h(7.00, SNARE, 80, 'RH')
    h(7.25, SNARE, 36, 'LH', 0.2, jt=0.010)
    h(7.50, SNARE, 86, 'RH')
    h(7.75, SNARE, 92, 'LH')

    # --- bar 2 : eight note swell -----------------------------------------
    h(8.00, KICK, 104, 'RF')
    h(10.00, KICK, 104, 'RF')
    for i in range(8):
        h(8 + i * 0.5, SNARE, 58 + i * 4.5,
          'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 3 : sixteenth note crescendo into the first groove -----------
    h(12.00, KICK, 106, 'RF')
    h(14.00, KICK, 106, 'RF')
    for i in range(16):
        v = 82 + i * 2.1 + (10 if i % 4 == 0 else 0)
        h(12 + i * 0.25, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.003)


def sec_groove():
    # --- bar 4 : the theme settles into time -------------------------------
    groove_bar(4, 'ride', 0.55, 0.45, (0.0, 2.0, 2.75), crash_beats=(0.0,))
    groove_bar(5, 'ride', 0.60, 0.60, (0.0, 1.5, 2.0, 3.5))
    groove_bar(6, 'ride', 0.65, 0.50, (0.0, 2.0, 2.5), crash_beats=(0.0,))

    # --- bar 7 : hat groove, tom pickup ------------------------------------
    groove_bar(7, 'hat', 0.60, 0.65, (0.0, 2.25, 3.0), skip=(3.5,))
    h(31.50, T_HM, 92, 'RH', 0.25, jt=0.006)
    h(31.75, T_LO, 96, 'LH', 0.25, jt=0.006)

    # --- bar 8 : the motif out loud ----------------------------------------
    crash(32.0, 118)
    time_voice(8, 'ride', 0.65)
    motif(32.0, loud=0.70)
    motif(34.0, loud=0.75)

    # --- bar 9 : light, funky hat groove -----------------------------------
    groove_bar(9, 'hat', 0.50, 0.70, (0.0, 1.75, 2.5, 3.75))

    # --- bar 10 : ride with an open hat lift -------------------------------
    groove_bar(10, 'ride', 0.60, 0.55, (0.0, 2.0, 2.75), openhat=(3.5,))

    # --- bar 11 : build into the development -------------------------------
    h(44.0, KICK, 104, 'RF')
    h(46.0, KICK, 104, 'RF')
    for i in range(8):
        h(44 + i * 0.25, SNARE, 84 + i * 2.2 + (8 if i % 4 == 0 else 0),
          'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    toms = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF, T_LO, T_LM)
    for i in range(8):
        h(46 + i * 0.25, toms[i], 94 + i * 2.5 + (10 if i % 4 == 0 else 0),
          'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)


def sec_develop():
    # --- bar 12 : theme in double time over the ride -----------------------
    crash(48.0, 120)
    h(48.0, SNARE, 112, 'LH')
    time_voice(12, 'ride', 0.65)
    motif(48.0, loud=0.60)
    motif(50.0, loud=0.65)

    # --- bar 13 : theme on the toms, then inverted -------------------------
    time_voice(13, 'ride', 0.65)
    motif(52.0, loud=0.65, snare_note=T_HI, ghost_note=T_HM)
    motif(54.0, loud=0.70, invert=True)

    # --- bar 14 : linear funk ---------------------------------------------
    lin = ((0.00, SNARE, 'RH', 110), (0.50, SNARE, 'LH', 36),
           (0.75, KICK, 'RF', 100), (1.00, SNARE, 'LH', 88),
           (1.25, SNARE, 'RH', 40), (1.50, SNARE, 'LH', 44),
           (1.75, KICK, 'RF', 96), (2.00, SNARE, 'RH', 108),
           (2.25, KICK, 'RF', 92), (2.50, SNARE, 'LH', 84),
           (3.00, SNARE, 'RH', 104), (3.25, SNARE, 'LH', 38),
           (3.50, KICK, 'RF', 98), (3.75, SNARE, 'LH', 42))
    for off, note, limb, vel in lin:
        h(56 + off, note, vel + R.uniform(-4, 4), limb, 0.25, jt=0.006)

    # --- bar 15 : heavy ghosting, pickup ----------------------------------
    groove_bar(15, 'hat', 0.55, 0.85, (0.0, 1.5, 2.25, 3.5), skip=(3.5,))
    h(63.50, T_HI, 90, 'RH', 0.25, jt=0.006)
    h(63.75, T_LO, 96, 'LH', 0.25, jt=0.006)

    # --- bar 16 : the shout, then a descending fill ------------------------
    crash(64.0, 124)
    time_voice(16, 'ride', 0.80, skip=(2.0, 2.5, 3.0, 3.5))
    motif(64.0, loud=1.00)
    fill = (T_HI, T_HM, SNARE, T_LM, T_LO, T_HF, T_LF, T_LO)
    for i, note in enumerate(fill):
        h(66 + i * 0.25, note, 100 + i * 2.5,
          'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 17 : double strokes on the floor toms -------------------------
    time_voice(17, 'ride', 0.75, skip=(2.0, 2.5, 3.0, 3.5))
    doubles = ((0.00, T_HF, 'RH'), (0.25, T_HF, 'RH'),
               (0.50, T_LF, 'LH'), (0.75, T_LF, 'LH'),
               (1.00, T_HF, 'RH'), (1.25, T_HF, 'RH'),
               (1.50, T_LF, 'LH'), (1.75, T_LF, 'LH'))
    for off, note, limb in doubles:
        v = 106 - (18 if off % 1.0 != 0.0 else 0)
        h(70 + off, note, v, limb, 0.25, jt=0.004)

    # --- bar 18 : sixteenths on the snare ---------------------------------
    h(72.0, KICK, 108, 'RF')
    h(74.0, KICK, 108, 'RF')
    for i in range(16):
        v = 76 + i * 2.0 + (14 if i % 4 == 0 else 0)
        h(72 + i * 0.25, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 19 : tom run, slightly rushed ---------------------------------
    toms = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF, T_HF, T_LO)
    for i in range(16):
        t = 76 + i * 0.25 - 0.045 * (i / 15.0) ** 2
        v = 88 + i * 1.8 + (12 if i % 4 == 0 else 0)
        h(t, toms[i % 8], v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)


def sec_quiet():
    # a splash and a soft bass drum open the calm
    crash(80.0, 96, 3.0, note=SPLASH)
    h(80.0, KICK, 88, 'RF')

    for k, bar in enumerate((20, 21, 22, 23)):
        b = bar * 4.0
        energy = 0.25 + 0.12 * k
        for i in range(8):
            v = 44 + 14 * (1 if i % 2 == 0 else 0) + 18 * energy + R.uniform(-3, 3)
            h(b + i * 0.5, HAT, v, 'RH', 0.25, jt=0.007)
        h(b + 2.0, STICK, 64 + 22 * energy, 'LH', 0.25, jt=0.006)
        if k < 2:
            h(b + 0.0, KICK, 70 + 22 * energy, 'RF')
            h(b + 2.5, KICK, 66 + 20 * energy, 'RF')
            gpos = (0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75)
        else:
            motif(b, loud=0.10 + 0.09 * k)
            gpos = (2.25, 2.75, 3.25, 3.75)
        for p in gpos:
            if R.random() < 0.45 + 0.18 * k:
                h(b + p, SNARE, 16 + 16 * R.random() + 10 * energy,
                  'LH', 0.2, jt=0.014)

    # --- bar 24 : eight notes on the snare, growing ------------------------
    h(96.0, KICK, 84, 'RF')
    h(98.0, KICK, 82, 'RF')
    for i in range(8):
        h(96 + i * 0.5, SNARE, 52 + i * 3.0,
          'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.005)

    # --- bar 25 : sixteenths ----------------------------------------------
    h(100.0, KICK, 86, 'RF')
    for i in range(16):
        v = 56 + i * 2.2 + (8 if i % 4 == 0 else 0)
        h(100 + i * 0.25, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 26 : sixteenths with tom accents ------------------------------
    h(104.0, KICK, 90, 'RF')
    h(106.0, KICK, 90, 'RF')
    for i in range(16):
        note = T_HM if i % 8 == 6 else SNARE
        v = 64 + i * 2.0 + (12 if i % 4 == 0 else 0)
        h(104 + i * 0.25, note, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 27 : travelling sixteenths, pushing ---------------------------
    toms = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF)
    for i in range(16):
        t = 108 + i * 0.25 - 0.05 * (i / 15.0) ** 2
        v = 78 + i * 2.2 + (14 if i % 4 == 0 else 0)
        h(t, toms[i % 6], v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(108.0, KICK, 96, 'RF')
    h(110.0, KICK, 96, 'RF')


def sec_build():
    # --- bars 28-29 : driving time, energy climbing ------------------------
    groove_bar(28, 'ride', 0.70, 0.50, (0.0, 2.0, 2.75), crash_beats=(0.0,))
    groove_bar(29, 'ride', 0.74, 0.60, (0.0, 1.5, 2.0, 3.5))

    # --- bar 30 ------------------------------------------------------------
    b = 120.0
    h(b + 0.0, KICK, 108, 'RF')
    h(b + 2.0, KICK, 104, 'RF')
    for i in range(16):
        note = SNARE if i < 12 else (T_HM, T_LM, T_LO, T_HF)[i - 12]
        v = 80 + i * 1.6 + (12 if i % 4 == 0 else 0)
        h(b + i * 0.25, note, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 31 ------------------------------------------------------------
    b = 124.0
    h(b + 0.0, KICK, 108, 'RF')
    h(b + 2.0, KICK, 104, 'RF')
    tail = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF, T_HF, T_LO)
    for i in range(16):
        note = SNARE if i < 8 else tail[i - 8]
        v = 84 + i * 1.8 + (12 if i % 4 == 0 else 0)
        h(b + i * 0.25, note, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 32 : doubles down the toms ------------------------------------
    b = 128.0
    order = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF)
    for i in range(16):
        note = order[(i // 2) % 6]
        limb = 'RH' if (i // 2) % 2 == 0 else 'LH'
        v = 96 - 20 * (i % 2) + (10 if i % 4 == 0 else 0)
        h(b + i * 0.25, note, v, limb, 0.25, jt=0.004)
    h(b + 0.0, KICK, 106, 'RF')
    h(b + 2.0, KICK, 106, 'RF')

    # --- bar 33 : doubles back up the toms --------------------------------
    b = 132.0
    order2 = (T_LF, T_HF, T_LO, T_LM, T_HM, T_HI)
    for i in range(16):
        note = order2[(i // 2) % 6]
        limb = 'RH' if (i // 2) % 2 == 0 else 'LH'
        v = 100 - 20 * (i % 2) + (12 if i % 4 == 0 else 0)
        h(b + i * 0.25, note, v, limb, 0.25, jt=0.004)
    h(b + 0.0, KICK, 108, 'RF')
    h(b + 2.0, KICK, 108, 'RF')

    # --- bars 34-35 : thirty-second rolls swelling toward the peak ---------
    b = 136.0
    h(b + 0.0, KICK, 104, 'RF')
    h(b + 2.0, KICK, 104, 'RF')
    for i in range(32):
        v = 60 + i * 1.8
        h(b + i * 0.125, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.2, jt=0.003)

    b = 140.0
    h(b + 0.0, KICK, 110, 'RF')
    h(b + 2.0, KICK, 110, 'RF')
    for i in range(32):
        v = 88 + i * 1.2 + (10 if i % 4 == 0 else 0)
        h(b + i * 0.125, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.2, jt=0.003)


def sec_climax():
    # --- bar 36 : the shout chorus ----------------------------------------
    crash(144.0, 126)
    h(144.0, KICK, 118, 'RF')
    h(144.0, SNARE, 118, 'LH')
    time_voice(36, 'ride', 0.85)
    h(145.0, SNARE, 116, 'LH', 0.25, jt=0.008)
    h(146.5, KICK, 108, 'RF')
    h(147.0, SNARE, 118, 'LH', 0.25, jt=0.008)
    h(147.75, KICK, 104, 'RF')

    groove_bar(37, 'ride', 0.85, 0.45, (0.0, 1.5, 2.0, 2.75))
    groove_bar(38, 'ride', 0.88, 0.50, (0.0, 2.0, 2.5), crash_beats=(0.0,))

    # --- bar 39 : groove with a tom fill in the last half ------------------
    groove_bar(39, 'ride', 0.90, 0.40, (0.0, 2.0), snare=(1.0,),
               skip=(2.0, 2.5, 3.0, 3.5))
    fill = (T_HI, T_HM, T_LM, T_HF, T_LF, T_LO, T_LM, T_HM)
    for i, note in enumerate(fill):
        h(158 + i * 0.25, note, 104 + i * 2.0,
          'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 40 : motif, once more, at full voice --------------------------
    crash(160.0, 126)
    time_voice(40, 'ride', 0.85)
    motif(160.0, loud=1.00)
    motif(162.0, loud=1.00, snare_note=T_HI, ghost_note=T_HM)

    # --- bar 41 : motif inverted, answered ---------------------------------
    crash(164.0, 122)
    time_voice(41, 'ride', 0.85)
    motif(164.0, loud=0.95, invert=True)
    motif(166.0, loud=1.00)

    # --- bar 42 : linear sixteenths, machine tight -------------------------
    b = 168.0
    pat = (SNARE, T_HM, SNARE, T_LM, SNARE, T_HI, SNARE, T_HM) * 2
    for i in range(16):
        v = 92 + (16 if i % 4 == 0 else 0) + (8 if i % 2 == 0 else 0)
        h(b + i * 0.25, pat[i], v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 110, 'RF')
    h(b + 1.5, KICK, 104, 'RF')
    h(b + 2.0, KICK, 110, 'RF')
    h(b + 3.5, KICK, 104, 'RF')

    # --- bar 43 : fill around the kit --------------------------------------
    b = 172.0
    order = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF, T_LO, T_LM,
             T_HI, T_HM, T_LM, T_LO, T_HF, T_LF, SNARE, SNARE)
    for i in range(16):
        v = 96 + (14 if i % 4 == 0 else 0) + i * 0.8
        h(b + i * 0.25, order[i], v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 44 : driving ----------------------------------------------
    groove_bar(44, 'ride', 0.90, 0.45, (0.0, 1.5, 2.0, 2.75), crash_beats=(0.0,))

    # --- bar 45 : syncopated, tom pickup -----------------------------------
    groove_bar(45, 'ride', 0.88, 0.60, (0.0, 0.75, 2.0, 3.5), skip=(3.5,))
    h(183.50, T_HM, 106, 'RH', 0.25, jt=0.006)
    h(183.75, T_LO, 110, 'LH', 0.25, jt=0.006)

    # --- bar 46 : sixteenths travelling ------------------------------------
    b = 184.0
    order = (SNARE, T_HI, SNARE, T_HM, SNARE, T_LM, SNARE, T_LO)
    for i in range(16):
        note = order[i % 8] if i < 12 else (T_HF, T_LF, T_HF, T_LO)[i - 12]
        v = 94 + (16 if i % 4 == 0 else 0) + i * 0.7
        h(b + i * 0.25, note, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 110, 'RF')
    h(b + 2.0, KICK, 108, 'RF')

    # --- bar 47 : double pedal burst ---------------------------------------
    crash(188.0, 124)
    h(188.0, SNARE, 118, 'LH')
    h(188.0, KICK, 116, 'RF')
    time_voice(47, 'ride', 0.80, skip=(2.0, 2.5, 3.0, 3.5))
    h(189.00, SNARE, 114, 'LH', 0.25, jt=0.006)
    h(189.50, SNARE, 110, 'LH', 0.25, jt=0.006)
    h(189.75, SNARE, 104, 'LH', 0.25, jt=0.006)
    for i in range(8):
        h(190 + i * 0.25, KICK, 102 + (12 if i % 2 == 0 else 0),
          'RF' if i % 2 == 0 else 'LF', 0.25, jt=0.005)

    # --- bar 48 : the theme, last full statement ---------------------------
    crash(192.0, 126)
    h(192.0, SNARE, 120, 'LH')
    time_voice(48, 'ride', 0.90, skip=(2.0, 2.5, 3.0, 3.5))
    motif(192.0, loud=1.00)
    motif(194.0, loud=1.00, snare_note=T_HI, ghost_note=T_HM)

    # --- bar 49 : accented sixteenths --------------------------------------
    b = 196.0
    for i in range(16):
        note = T_HM if i % 8 == 7 else SNARE
        v = 88 + i * 1.4 + (16 if i % 4 == 0 else 0) - (20 if i % 4 == 3 else 0)
        h(b + i * 0.25, note, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 112, 'RF')
    h(b + 2.0, KICK, 110, 'RF')

    # --- bar 50 : doubles down the toms ------------------------------------
    b = 200.0
    order = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF)
    for i in range(16):
        note = order[(i // 2) % 6]
        limb = 'RH' if (i // 2) % 2 == 0 else 'LH'
        v = 100 - 18 * (i % 2) + (12 if i % 4 == 0 else 0)
        h(b + i * 0.25, note, v, limb, 0.25, jt=0.004)
    h(b + 0.0, KICK, 108, 'RF')
    h(b + 2.0, KICK, 108, 'RF')

    # --- bar 51 : release, decrescendo into the breakdown ------------------
    b = 204.0
    for i in range(16):
        v = 100 - i * 2.4 + (10 if i % 4 == 0 else 0)
        h(b + i * 0.25, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 106, 'RF')
    h(b + 2.0, KICK, 102, 'RF')


def sec_break():
    """Quiet, sparse, rim clicks and ghosts; the motif whispers."""
    for k, bar in enumerate((52, 53, 54, 55)):
        b = bar * 4.0
        energy = 0.22 + 0.10 * k
        for i in range(8):
            if i % 2 == 0:
                h(b + i * 0.5, HAT, 44 + 8 * energy + R.uniform(-3, 3),
                  'RH', 0.25, jt=0.008)
            elif R.random() < 0.5:
                h(b + i * 0.5, HAT, 30 + R.uniform(-3, 3), 'RH', 0.25, jt=0.008)
        h(b + 2.0, STICK, 60 + 30 * energy, 'LH', 0.25, jt=0.006)
        if k < 2:
            h(b + 0.0, KICK, 66 + 24 * energy, 'RF')
            h(b + 2.5, KICK, 62 + 24 * energy, 'RF')
            gpos = (0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75)
        else:
            motif(b, loud=0.10 + 0.10 * k)
            gpos = (2.25, 2.75, 3.25, 3.75)
        for p in gpos:
            if R.random() < 0.40 + 0.15 * k:
                h(b + p, SNARE, 16 + 12 * R.random() + 14 * energy,
                  'LH', 0.2, jt=0.016)


def sec_push():
    # --- bars 56-59 : medium groove, growing -------------------------------
    crash(224.0, 112)
    h(224.0, KICK, 104, 'RF')
    time_voice(56, 'ride', 0.60)
    h(225.0, SNARE, 96, 'LH', 0.25, jt=0.008)
    h(227.0, SNARE, 98, 'LH', 0.25, jt=0.008)
    groove_bar(57, 'ride', 0.65, 0.55, (0.0, 1.5, 2.0, 3.5))
    groove_bar(58, 'ride', 0.70, 0.60, (0.0, 2.0, 2.75))
    groove_bar(59, 'ride', 0.72, 0.50, (0.0, 2.0, 3.5), skip=(3.5,))
    h(239.50, T_HI, 96, 'RH', 0.25, jt=0.006)
    h(239.75, T_HM, 100, 'LH', 0.25, jt=0.006)

    # --- bars 60-63 : sixteenth note phrases -------------------------------
    for bar in (60, 61, 62, 63):
        b = bar * 4.0
        e = (bar - 60) / 3.0
        h(b + 0.0, KICK, 100 + 10 * e, 'RF')
        h(b + 2.0, KICK, 98 + 10 * e, 'RF')
        tail = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF, T_HF, T_LO)
        for i in range(16):
            if bar >= 62 and i >= 8:
                note = tail[i - 8]
            else:
                note = SNARE
            v = 78 + 16 * e + i * 1.2 + (12 if i % 4 == 0 else 0)
            if i % 4 == 3:
                v -= 26
            h(b + i * 0.25, note, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bars 64-67 : double strokes travelling the kit --------------------
    order = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF)
    for bar in (64, 65, 66, 67):
        b = bar * 4.0
        for i in range(16):
            note = order[(i // 2 + (bar - 64) * 3) % 6]
            limb = 'RH' if (i // 2) % 2 == 0 else 'LH'
            v = 94 + (12 if i % 4 == 0 else 0) - (16 if i % 2 else 0) + 2 * (bar - 64)
            h(b + i * 0.25, note, v, limb, 0.25, jt=0.004)
        h(b + 0.0, KICK, 106, 'RF')
        h(b + 2.0, KICK, 106, 'RF')

    # --- bar 68 : sixteenths, accented -------------------------------------
    b = 272.0
    for i in range(16):
        v = 84 + i * 0.8 + (16 if i % 4 == 0 else 0)
        h(b + i * 0.25, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 108, 'RF')
    h(b + 2.0, KICK, 108, 'RF')

    # --- bar 69 : thirty-second roll ---------------------------------------
    b = 276.0
    for i in range(32):
        v = 70 + i * 1.1
        h(b + i * 0.125, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.2, jt=0.003)
    h(b + 0.0, KICK, 110, 'RF')
    h(b + 2.0, KICK, 110, 'RF')

    # --- bar 70 : sixteenths snare / toms ----------------------------------
    b = 280.0
    order = (SNARE, SNARE, T_HI, T_HM, SNARE, SNARE, T_LM, T_LO,
             SNARE, T_HF, T_LF, T_HF, T_LO, T_LM, T_HM, T_HI)
    for i in range(16):
        v = 92 + (16 if i % 4 == 0 else 0) + i * 1.0
        h(b + i * 0.25, order[i], v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 112, 'RF')
    h(b + 2.0, KICK, 112, 'RF')

    # --- bar 71 : big roll into the ending ---------------------------------
    b = 284.0
    for i in range(32):
        v = 84 + i * 1.4
        h(b + i * 0.125, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.2, jt=0.003)
    h(b + 0.0, KICK, 112, 'RF')
    h(b + 2.0, KICK, 112, 'RF')


def sec_ending():
    # --- bar 72 : last statement of the theme ------------------------------
    crash(288.0, 126)
    h(288.0, SNARE, 120, 'LH')
    time_voice(72, 'ride', 0.85, skip=(3.0, 3.5))
    motif(288.0, loud=1.00)
    for i, note in enumerate((T_HI, T_HM, T_LM, T_LO)):
        h(291 + i * 0.25, note, 106 + i * 2,
          'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)

    # --- bar 73 : tom run ---------------------------------------------------
    b = 292.0
    order = (T_HI, T_HM, T_LM, T_LO, T_HF, T_LF, T_HF, T_LO)
    for i in range(16):
        v = 100 + (12 if i % 4 == 0 else 0) + i * 0.6
        h(b + i * 0.25, order[i % 8], v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 110, 'RF')
    h(b + 2.0, KICK, 110, 'RF')

    # --- bar 74 : snare sixteenths crescendo --------------------------------
    b = 296.0
    for i in range(16):
        v = 84 + i * 2.4 + (10 if i % 4 == 0 else 0)
        h(b + i * 0.25, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.25, jt=0.004)
    h(b + 0.0, KICK, 112, 'RF')
    h(b + 2.0, KICK, 112, 'RF')

    # --- bar 75 : thirty-second roll, rushing a little ----------------------
    b = 300.0
    for i in range(32):
        t = b + i * 0.125 - 0.10 * (i / 31.0) ** 2
        v = 88 + i * 1.1
        h(t, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.2, jt=0.003)
    h(b + 0.0, KICK, 114, 'RF')
    h(b + 2.0, KICK, 114, 'RF')

    # --- bar 76 : the final hit, landed, not faded --------------------------
    crash(304.0, 127, dur=6.0)
    h(304.0, KICK, 124, 'RF')
    h(304.0, SNARE, 126, 'LH')


def compose():
    sec_intro()
    sec_groove()
    sec_develop()
    sec_quiet()
    sec_build()
    sec_climax()
    sec_break()
    sec_push()
    sec_ending()


# ---------------------------------------------------------------------------
# tempo map: the pulse breathes with the phrasing
# ---------------------------------------------------------------------------
TEMPO_MAP = (
    (0, 132),      # intro, held back
    (16, 148),     # the groove settles
    (48, 152),     # development
    (80, 148),     # calm
    (112, 152),    # build begins
    (128, 158),
    (144, 168),    # peak
    (208, 152),    # breakdown
    (224, 152),    # push
    (256, 160),
    (288, 170),    # ending
    (296, 166),
    (300, 156),
    (302, 150),    # broadening into the last hit
)


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def verify_playable():
    """Cheap sanity check: never three hands / three feet at once."""
    hands, feet = [], []
    for beat, note, vel, dur, limb in events:
        (hands if limb in ('RH', 'LH') else feet).append(beat * PPQ)
    hands.sort()
    feet.sort()
    bad = 0
    for lst in (hands, feet):
        for i in range(len(lst) - 2):
            if lst[i + 2] - lst[i] < 48:      # ~40 ms
                bad += 1
    return bad


def build_midi(path='solo.mid'):
    raw = []
    for beat, note, vel, dur, limb in events:
        on = int(round(beat * PPQ))
        off = on + max(1, int(round(dur * PPQ)))
        raw.append((on, 1, note, vel))
        raw.append((off, 0, note, 0))
    raw.sort(key=lambda e: (e[0], e[1]))       # note offs first at equal ticks

    msgs = []
    for beat, bpm in TEMPO_MAP:
        msgs.append((int(round(beat * PPQ)), -1,
                     MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm))))
    for tick, kind, note, vel in raw:
        msgs.append((tick, kind,
                     Message('note_on' if kind else 'note_off',
                             channel=CHANNEL, note=note, velocity=vel)))
    msgs.sort(key=lambda m: (m[0], m[1]))

    mid = MidiFile(ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('text', text='two minute GM drum solo', time=0))

    last = 0
    for tick, kind, msg in msgs:
        msg.time = tick - last
        last = tick
        track.append(msg)
    track.append(MetaMessage('end_of_track', time=0))

    mid.save(path)


def main():
    compose()
    problems = verify_playable()
    if problems:
        print('warning: %d crowded hand/foot collisions' % problems)
    build_midi('solo.mid')
    print('wrote solo.mid (%d strokes)' % len(events))


if __name__ == '__main__':
    main()
