#!/usr/bin/env python3
"""
drum_solo.py

Generates solo.mid -- a two-minute General MIDI drum solo on MIDI channel 10
(percussion).  Deterministic: running this in an empty directory always writes
a byte-identical solo.mid.

Musical design
    * motif A  : ride/backbeat groove with a signature bass-drum placement
    * motif B  : tribal tom groove
    * motif C  : heavy half-time feel
    * development, crescendo rolls, double-stroke runs, big fills
    * dynamics through accents / ghosts / crescendos inside phrases
    * human feel: smooth rubato warp + per-note jitter + ghost notes
"""

import math
import random

import mido

# --------------------------------------------------------------------------
PPQ = 480
TARGET_SECONDS = 120.0
CHANNEL = 9                      # 0-based -> MIDI channel 10
rng = random.Random(0x5EED1A)

# ------------------------------------------------------------- GM drum notes
KICK, KICK2 = 36, 35
STICK, SNARE, CLAP = 37, 38, 39
PEDAL_HAT, HAT, HAT_OPEN = 44, 42, 46
RIDE, RIDE_BELL, RIDE2 = 51, 53, 59
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
T_HIGH, T_MID, T_LOWMID = 50, 48, 47
T_LOW, T_FLOORH, T_FLOORL = 45, 43, 41
TAMB, COWBELL, CLAVES = 54, 56, 75
WOOD_H, WOOD_L, TRIANGLE, CABASA = 76, 77, 81, 69
CONGA_H = 63                     # open high conga -- for colour

EVENTS = []                      # (beat, note, velocity, duration_in_beats)
TEMPOS = []                      # (beat, bpm)


# --------------------------------------------------------------------------
# timing / humanisation
# --------------------------------------------------------------------------
def set_tempo(beat, bpm):
    TEMPOS.append((float(beat), float(bpm)))


def warp(beat):
    """Smooth micro-rubato: the pulse surges and settles with the music."""
    return (0.0080 * math.sin(beat * 0.19)
            + 0.0060 * math.sin(beat * 0.071 + 2.3)
            + 0.0040 * math.sin(beat * 0.41 + 0.6)
            + 0.0020 * math.sin(beat * 0.97 + 4.1))


def hit(beat, note, vel, dur=0.12, jit=0.009):
    """Place one stroke.  `beat` is nominal; output is humanised."""
    t = beat + warp(beat) + rng.uniform(-jit, jit)
    v = int(max(1, min(127, round(vel))))
    EVENTS.append((t, note, v, max(0.02, dur)))


def seq(b0, notes, sub=0.25, base=80.0, dur=0.11, accents=(), dvel=16.0):
    """A run of strokes, `sub` beats apart, with accents and phrasing."""
    n = len(notes)
    for i, note in enumerate(notes):
        v = base + (dvel if i in accents else 0.0)
        v += 5.0 * math.sin(i * 0.7)          # tiny phrase shape
        hit(b0 + i * sub, note, v, dur)


def roll(b0, b1, note, n, v0, v1, dur=0.06):
    """A swelling roll between two beats."""
    step = (b1 - b0) / n
    for i in range(n):
        v = v0 + (v1 - v0) * (i / max(1, n - 1))
        hit(b0 + i * step, note, v, dur)


# --------------------------------------------------------------------------
# motifs
# --------------------------------------------------------------------------
def groove_A(bar, vary=0, vel=76):
    """Motif A: ride 8ths, backbeat snare, ghost notes, shifting bass drum."""
    b = bar * 4
    for i in range(8):
        p = i * 0.5
        v = vel + (13 if i % 2 == 0 else 0)
        note = RIDE_BELL if (vary == 3 and i in (4, 5)) else RIDE
        hit(b + p, note, v, 0.20)
    hit(b + 1, PEDAL_HAT, 60, 0.10)
    hit(b + 3, PEDAL_HAT, 60, 0.10)

    kicks = [0.0, 2.5]
    if vary >= 1:
        kicks.append(1.75)
    if vary >= 2:
        kicks.append(3.25)
    if vary >= 3:
        kicks.append(0.75)
    for p in kicks:
        hit(b + p, KICK, (vel + 6) if p == 0.0 else (vel - 4), 0.25)

    for p in (1.0, 3.0):
        hit(b + p, SNARE, vel + 16, 0.10)

    for i, p in enumerate((0.75, 1.75, 2.75, 3.75)):
        if (vary + i) % 3 != 0:
            hit(b + p, SNARE, 26 + (i % 3) * 5, 0.07)

    if vary == 2 and rng.random() < 0.55:          # never quite the same bar
        hit(b + 3.5, T_MID, vel - 6, 0.16)
    if vary == 1 and rng.random() < 0.40:
        hit(b + 1.5, T_HIGH, vel - 8, 0.14)


def groove_B(bar, vary=0):
    """Motif B: tribal tom groove on the feet-and-hands."""
    b = bar * 4
    for q in range(4):
        hit(b + q, PEDAL_HAT, 56, 0.08)
    hit(b + 0.0, KICK, 88, 0.25)
    hit(b + 2.5, KICK, 78, 0.25)
    if vary % 2 == 1:
        hit(b + 1.5, KICK, 70, 0.22)
    if vary == 3:
        hit(b + 3.5, KICK, 72, 0.22)

    hit(b + 1.0, SNARE, 96, 0.10)
    hit(b + 3.0, SNARE, 96, 0.10)

    order = [T_HIGH, T_MID, T_LOWMID, T_LOW, T_FLOORH, T_FLOORL]
    for i in range(8):
        p = i * 0.5
        note = order[(i + vary * 2) % 6]
        v = 72 if i % 2 == 0 else 58
        hit(b + p, note, v, 0.18)

    for i, p in enumerate((0.75, 1.75, 2.75, 3.75)):
        if (vary + i) % 2 == 0:
            hit(b + p, SNARE, 30, 0.07)


def groove_C(bar, vary=0):
    """Motif C: heavy half-time statement."""
    b = bar * 4
    hit(b + 0.0, KICK, 94, 0.32)
    hit(b + 2.0, SNARE, 106, 0.16)
    hit(b + 2.5, KICK, 80, 0.28)
    if vary % 2:
        hit(b + 1.75, KICK, 74, 0.28)

    for i in range(8):
        p = i * 0.5
        v = 74 + (14 if i % 2 == 0 else 0)
        hit(b + p, RIDE, v, 0.22)

    for i, p in enumerate((0.75, 1.75, 3.75)):
        if (vary + i) % 3 != 0:
            hit(b + p, SNARE, 26 + i * 3, 0.07)

    if vary == 3:
        hit(b + 3.25, T_MID, 84, 0.16)
        hit(b + 3.5, T_LOW, 86, 0.16)
        hit(b + 3.75, T_FLOORH, 88, 0.16)


# --------------------------------------------------------------------------
# fills
# --------------------------------------------------------------------------
def fill_A(bar, style=0):
    """Two beats of time, two beats of hands travelling down the kit."""
    b = bar * 4
    for i in range(4):
        hit(b + i * 0.5, RIDE, 74 + (12 if i % 2 == 0 else 0), 0.20)
    hit(b + 0.0, KICK, 88, 0.26)
    hit(b + 1.0, SNARE, 92, 0.12)

    if style == 0:
        notes = [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, SNARE]
    else:
        notes = [T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, T_LOW, T_FLOORH, SNARE]
    seq(b + 2.0, notes, 0.25, 84, 0.10, accents=(0, 4))
    hit(b + 3.5, KICK, 84, 0.24)


def fill_B(bar):
    """Tom fill that walks back up into the next downbeat."""
    b = bar * 4
    hit(b + 0.0, KICK, 90, 0.28)
    hit(b + 0.0, T_LOW, 88, 0.18)
    seq(b + 0.5, [T_MID, T_MID, T_LOW, T_LOW, T_FLOORH, T_FLOORH],
        0.25, 84, 0.10)
    seq(b + 2.0, [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, SNARE],
        0.25, 86, 0.10, accents=(0, 4))
    hit(b + 3.5, KICK, 86, 0.24)


# --------------------------------------------------------------------------
# the solo
# --------------------------------------------------------------------------
def build():
    # ============ 1. Intro: bars 0-1 (beats 0-8) ============
    set_tempo(0, 92)
    for i in range(4):
        hit(i, PEDAL_HAT, 52 + i * 4, 0.08)
    hit(0.0, KICK, 78, 0.22)
    hit(2.0, KICK, 68, 0.22)
    hit(1.0, STICK, 56, 0.12)
    hit(3.0, STICK, 66, 0.12)
    hit(3.5, SNARE, 34, 0.06)
    hit(3.75, WOOD_H, 44, 0.06)

    for i in range(8):
        hit(4 + i * 0.5, HAT, 48 + i * 4.5, 0.12)
    for i in range(4):
        hit(6.5 + i * 0.25, SNARE, 54 + i * 11, 0.08)
    hit(7.5, KICK, 74, 0.22)

    # ============ 2. Motif A stated: bars 2-9 (beats 8-40) ============
    set_tempo(8, 104)
    hit(8.0, CRASH, 104, 0.55)
    hit(8.0, KICK, 88, 0.28)
    for bar in range(2, 9):
        groove_A(bar, vary=(bar - 2) % 4)
    fill_A(9)

    # ============ 3. Motif A developed: bars 10-17 (beats 40-72) ============
    set_tempo(40, 110)
    hit(40.0, CRASH, 106, 0.55)
    hit(40.0, KICK, 90, 0.28)
    for bar in range(10, 16):
        groove_A(bar, vary=(bar - 10) % 4, vel=78)
    groove_A(16, vary=2, vel=78)
    fill_A(17, style=1)

    # ============ 4. Motif B (toms): bars 18-25 (beats 72-104) ============
    set_tempo(72, 118)
    hit(72.0, SPLASH, 96, 0.35)
    hit(72.0, KICK, 90, 0.28)
    for bar in range(18, 25):
        groove_B(bar, vary=(bar - 18) % 4)
    fill_B(25)

    # ============ 5. Crescendo build: bars 26-29 (beats 104-120) ============
    set_tempo(104, 118)
    set_tempo(108, 122)
    set_tempo(112, 126)
    set_tempo(116, 130)

    b = 104                                   # bar 26: swelling 8ths
    for i in range(8):
        hit(b + i * 0.5, SNARE, 52 + i * 5, 0.10)
    hit(b, KICK, 88, 0.25)
    hit(b + 2.0, KICK, 84, 0.25)

    b = 108                                   # bar 27: swelling 16ths
    for i in range(16):
        hit(b + i * 0.25, SNARE, 60 + i * 2.6, 0.08)
    hit(b, KICK, 90, 0.25)
    hit(b + 2.0, KICK, 86, 0.25)

    b = 112                                   # bar 28: accented 16ths + tamb
    for i in range(16):
        v = 68 + i * 2.2
        if i % 4 == 0:
            hit(b + i * 0.25, SNARE, v + 14, 0.10)
        else:
            hit(b + i * 0.25, SNARE, v, 0.08)
    for i in range(8):
        hit(b + i * 0.5, TAMB, 50 + i * 4, 0.10)
    hit(b, KICK, 92, 0.25)
    hit(b + 2.5, KICK, 88, 0.25)

    b = 116                                   # bar 29: full-kit 16ths
    seq(b, [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOWMID, T_LOWMID,
            T_LOW, T_LOW, T_FLOORH, T_FLOORH, T_FLOORL, T_FLOORL, SNARE, SNARE],
        0.25, 88, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 94, 0.28)
    hit(b + 2.0, KICK, 90, 0.25)
    hit(b + 3.5, KICK, 86, 0.25)

    # ============ 6. Motif C, heavy half-time: bars 30-33 (beats 120-136) ====
    set_tempo(120, 114)
    hit(120.0, CRASH2, 112, 0.80)
    hit(120.0, KICK, 96, 0.35)
    hit(120.0, SNARE, 104, 0.18)
    for bar in range(31, 34):
        groove_C(bar, vary=(bar - 31) % 4)
    hit(120.5, COWBELL, 66, 0.10)
    hit(134.5, COWBELL, 62, 0.10)
    hit(135.5, CONGA_H, 70, 0.12)          # colour at phrase end

    # ============ 7. Doubles / development: bars 34-41 (beats 136-168) ======
    set_tempo(136, 124)
    hit(136.0, CRASH, 108, 0.60)
    hit(136.0, KICK, 92, 0.30)
    groove_A(34, vary=1, vel=80)
    groove_A(35, vary=3, vel=80)

    b = 144                                    # bar 36 -- doubles down the kit
    seq(b, [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, T_LOW,
            SNARE, SNARE, T_MID, T_MID, T_LOW, T_LOW, T_FLOORH, T_FLOORH],
        0.25, 82, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 86, 0.26)
    hit(b + 2.5, KICK, 82, 0.26)

    b = 148                                    # bar 37
    seq(b, [T_FLOORH, T_FLOORH, T_LOW, T_LOW, T_MID, T_MID, T_HIGH, T_HIGH,
            SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, SNARE],
        0.25, 84, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 88, 0.26)
    hit(b + 3.5, KICK, 82, 0.26)

    b = 152                                    # bar 38 -- singles weaved
    seq(b, [SNARE, T_HIGH, SNARE, T_MID, SNARE, T_LOW, SNARE, T_FLOORH,
            SNARE, T_LOW, SNARE, T_MID, SNARE, T_HIGH, SNARE, SNARE],
        0.25, 84, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 88, 0.26)
    hit(b + 2.0, KICK, 84, 0.26)

    b = 156                                    # bar 39 -- doubles displaced
    seq(b, [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, SNARE, T_LOW, T_LOW,
            T_FLOORH, T_FLOORH, T_LOW, T_LOW, T_MID, SNARE, T_HIGH, T_HIGH],
        0.25, 84, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 90, 0.26)
    hit(b + 1.5, KICK, 84, 0.26)
    hit(b + 3.5, KICK, 84, 0.26)

    b = 160                                    # bar 40 -- snare swell
    for i in range(16):
        hit(b + i * 0.25, SNARE, 70 + i * 1.6, 0.08)
    hit(b, KICK, 88, 0.26)
    hit(b + 2.0, KICK, 84, 0.26)
    hit(b + 3.5, KICK, 80, 0.26)

    b = 164                                    # bar 41 -- launch
    seq(b, [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, T_LOW,
            T_LOWMID, T_LOWMID, T_FLOORH, T_FLOORH, T_FLOORL, T_FLOORL,
            SNARE, SNARE],
        0.25, 92, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 92, 0.26)
    hit(b + 3.0, KICK, 86, 0.26)

    # ============ 8. Big fills: bars 42-49 (beats 168-200) ============
    set_tempo(168, 132)
    hit(168.0, CRASH, 112, 0.60)
    hit(168.0, KICK, 96, 0.30)

    b = 168
    seq(b, [SNARE, T_HIGH, T_MID, T_LOWMID, SNARE, T_HIGH, T_MID, T_LOWMID,
            T_LOW, T_FLOORH, T_FLOORL, T_LOW, SNARE, SNARE, T_FLOORH, T_FLOORL],
        0.25, 86, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 92, 0.28)
    hit(b + 2.5, KICK, 86, 0.26)

    b = 172
    seq(b, [SNARE, T_HIGH, SNARE, T_MID, SNARE, T_LOW, SNARE, T_FLOORH],
        0.5, 84, 0.12)
    seq(b + 2.0, [SNARE, T_HIGH, T_MID, T_LOW, T_LOWMID, T_FLOORH,
                  T_FLOORL, SNARE], 0.25, 86, 0.10, accents=(0, 4))
    hit(b, KICK, 90, 0.28)
    hit(b + 2.5, KICK, 84, 0.26)

    for bar in (44, 45):                       # ride-bell contrast
        bb = bar * 4
        for i in range(8):
            v = 78 + (12 if i % 2 == 0 else 0)
            note = RIDE_BELL if i % 4 == 0 else RIDE
            hit(bb + i * 0.5, note, v, 0.20)
        hit(bb + 0.0, KICK, 90, 0.28)
        hit(bb + 2.5, KICK, 82, 0.26)
        hit(bb + 1.0, SNARE, 94, 0.12)
        hit(bb + 3.0, SNARE, 94, 0.12)
        for i, p in enumerate((0.75, 1.75, 2.75, 3.75)):
            if (i + bar) % 3 != 0:
                hit(bb + p, SNARE, 28, 0.07)

    b = 184
    seq(b, [SNARE, SNARE, SNARE, SNARE, T_HIGH, T_HIGH, T_HIGH, T_HIGH,
            T_MID, T_MID, T_MID, T_MID, T_LOW, T_LOW, T_LOW, T_LOW],
        0.25, 88, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 94, 0.28)
    hit(b + 2.0, KICK, 90, 0.26)

    b = 188
    seq(b, [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, T_LOW,
            T_LOWMID, T_LOWMID, T_FLOORH, T_FLOORH, T_FLOORL, T_FLOORL,
            SNARE, SNARE], 0.25, 90, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 94, 0.28)
    hit(b + 3.0, KICK, 88, 0.26)

    b = 192                                    # 32nd burst
    for i in range(16):
        hit(b + i * 0.125, SNARE, 80 + i * 1.2, 0.07)
    hit(b, KICK, 94, 0.28)
    seq(b + 2.0, [T_HIGH, T_MID, T_LOWMID, T_LOW, T_FLOORH, T_FLOORL,
                  SNARE, SNARE], 0.25, 94, 0.10, accents=(0, 4))

    b = 196                                    # final push
    for i in range(16):
        hit(b + i * 0.25, SNARE, 92 + i * 1.5, 0.09)
    hit(b, KICK, 96, 0.28)
    hit(b + 2.0, KICK, 92, 0.26)
    hit(b + 3.5, KICK, 90, 0.26)

    # ============ 9. Motif A returns: bars 50-57 (beats 200-232) ============
    set_tempo(200, 126)
    hit(200.0, CRASH, 112, 0.60)
    hit(200.0, KICK, 96, 0.30)
    for bar in range(50, 57):
        groove_A(bar, vary=(bar - 50) % 4, vel=80)
    fill_A(57, style=1)

    # ============ 10. Finale: bars 58-59 (beats 232-240) ============
    set_tempo(232, 130)
    b = 232
    seq(b, [SNARE, SNARE, T_HIGH, T_HIGH, T_MID, T_MID, T_LOW, T_LOW,
            T_LOWMID, T_LOWMID, T_FLOORH, T_FLOORH, T_FLOORL, T_FLOORL,
            SNARE, SNARE], 0.25, 94, 0.10, accents=(0, 4, 8, 12))
    hit(b, KICK, 96, 0.30)
    hit(b + 2.0, KICK, 92, 0.26)

    b = 236                                    # last bar of the solo
    hit(b + 0.0, KICK, 98, 0.30)
    hit(b + 0.0, SNARE, 100, 0.12)
    hit(b + 0.5, SNARE, 60, 0.08)
    hit(b + 1.0, SNARE, 104, 0.12)
    hit(b + 1.5, T_LOW, 90, 0.16)
    hit(b + 2.0, T_FLOORH, 92, 0.16)
    hit(b + 2.5, T_FLOORL, 96, 0.16)
    hit(b + 3.0, SNARE, 106, 0.12)
    hit(b + 3.5, SNARE, 108, 0.12)
    hit(b + 3.25, T_MID, 88, 0.14)

    # the landing
    hit(240.0, CRASH, 122, 2.00)
    hit(240.0, KICK, 106, 0.50)
    hit(240.0, SNARE, 112, 0.30)


# --------------------------------------------------------------------------
# timing helpers / MIDI output
# --------------------------------------------------------------------------
def clean_tempos(raw):
    seen = {}
    order = []
    for b, bpm in raw:
        if b not in seen:
            order.append(b)
        seen[b] = bpm
    order.sort()
    return [(b, seen[b]) for b in order]


def seconds_at(tempos, beat):
    total = 0.0
    cur_beat = 0.0
    cur_bpm = tempos[0][1]
    for b, bpm in tempos:
        if b >= beat:
            break
        if b > cur_beat:
            total += (b - cur_beat) * 60.0 / cur_bpm
            cur_beat = b
        cur_bpm = bpm
    total += (beat - cur_beat) * 60.0 / cur_bpm
    return total


def write_midi(path, events, tempos):
    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)

    # ---- conductor track -------------------------------------------------
    t0 = mido.MidiTrack()
    mid.tracks.append(t0)
    t0.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    t0.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                               time=0))
    cur = 0
    for b, bpm in tempos:
        tick = int(round(b * PPQ))
        if tick < cur:
            tick = cur
        t0.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm),
                                   time=tick - cur))
        cur = tick
    t0.append(mido.MetaMessage('end_of_track', time=0))

    # ---- note track ------------------------------------------------------
    onoffs = []
    for t, note, vel, dur in events:
        on = int(round(t * PPQ))
        off = int(round((t + dur) * PPQ))
        if off <= on:
            off = on + 1
        onoffs.append([on, off, note, vel])

    bynote = {}
    for i, item in enumerate(onoffs):
        bynote.setdefault(item[2], []).append(i)
    for note, idxs in bynote.items():
        idxs.sort(key=lambda i: onoffs[i][0])
        for a, b in zip(idxs, idxs[1:]):
            limit = onoffs[b][0] - 1
            if onoffs[a][1] > limit:
                onoffs[a][1] = max(onoffs[a][0] + 1, limit)

    msgs = []
    for on, off, note, vel in onoffs:
        msgs.append((on, 1, mido.Message('note_on', note=note, velocity=vel,
                                         channel=CHANNEL, time=0)))
        msgs.append((off, 0, mido.Message('note_off', note=note, velocity=0,
                                          channel=CHANNEL, time=0)))
    msgs.sort(key=lambda x: (x[0], x[1]))

    t1 = mido.MidiTrack()
    mid.tracks.append(t1)
    t1.append(mido.MetaMessage('track_name', name='Kit', time=0))
    cur = 0
    for tick, _prio, msg in msgs:
        if tick < cur:
            tick = cur
        msg.time = tick - cur
        cur = tick
        t1.append(msg)
    t1.append(mido.MetaMessage('end_of_track', time=0))

    mid.save(path)


def main():
    build()

    tempos = clean_tempos(TEMPOS)
    end_beat = max(e[0] for e in EVENTS)

    natural = seconds_at(tempos, end_beat)
    scale = TARGET_SECONDS / natural
    tempos = [(b, bpm * scale) for b, bpm in tempos]

    events = sorted(EVENTS, key=lambda e: e[0])
    write_midi('solo.mid', events, tempos)

    print('wrote solo.mid  (%.1f s, %d events, %d tempo changes)'
          % (seconds_at(tempos, end_beat), len(events), len(tempos)))


if __name__ == '__main__':
    main()
