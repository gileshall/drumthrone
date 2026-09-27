#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid -- a two minute unaccompanied drum solo for General MIDI
percussion (channel 10).

The solo is generated deterministically from a fixed seed, so running the
script always produces a byte-identical file.  Every note is placed by hand
in "beat time"; a tempo map (with rubato, phrase surges and settles) turns
that into seconds on playback.
"""

import math
import random

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

TICKS_PER_BEAT = 480
CH = 9                      # zero-based index of General MIDI channel 10

# ----------------------------------------------------------------- kit map
BD, BD2 = 36, 35            # acoustic bass drum / bass drum 1
SD, SD2, RS = 38, 40, 37    # snare / electric snare / side stick
HH, HHO, PHH = 42, 46, 44   # closed / open / pedal hi-hat
T_HI, T_HIMID, T_LOMID, T_LOW = 50, 48, 47, 45
F_HI, F_LOW = 43, 41
CRASH, CRASH2 = 49, 57
RIDE, RIDE2, BELL = 51, 59, 53
SPLASH, CHINA = 55, 52
COW, TAMB, CLAVE, WB_HI, WB_LO = 56, 54, 75, 76, 77
BONGO_H, BONGO_L, CONGA_H, MARACAS = 60, 61, 62, 70

CYMBALS = frozenset((CRASH, CRASH2, RIDE, RIDE2, BELL, SPLASH, CHINA))
FEET = frozenset((BD, BD2, PHH))


# ------------------------------------------------------------------ motives
# One bar of 4/4.  Positions are beat offsets: 0.0 = beat 1, 0.25 = "e",
# 0.5 = "and", 0.75 = "a", 1.0 = beat 2, and so on.
#
# MOTIF 1: the main groove -- kick on 1 and 3, backbeat on 2 and 4, hats on
# the eighths, ghost notes sneaking between the backbeats.
GROOVE_1 = [
    (0.0, BD, 100), (0.0, HH, 72), (0.5, HH, 56), (0.5, SD, 32),
    (1.0, SD, 106), (1.0, HH, 68), (1.25, BD, 70), (1.5, HH, 56), (1.5, SD, 28),
    (2.0, BD, 94), (2.0, HH, 72), (2.5, HH, 56), (2.5, SD, 30),
    (3.0, SD, 106), (3.0, HH, 68), (3.5, HH, 56), (3.5, BD, 70), (3.75, SD, 26),
]

# MOTIF 1, busier: extra kick, ghosts pushed to the "a"
GROOVE_2 = [
    (0.0, BD, 104), (0.0, HH, 74), (0.25, SD, 28), (0.5, HH, 58),
    (1.0, SD, 108), (1.0, HH, 70), (1.5, HH, 58), (1.5, BD, 74), (1.75, SD, 30),
    (2.0, BD, 96), (2.0, HH, 72), (2.25, BD, 60), (2.5, HH, 58), (2.5, SD, 32),
    (3.0, SD, 108), (3.0, HH, 70), (3.25, BD, 64), (3.5, HHO, 70),
]

# MOTIF 1 with the pulse displaced -- the kick walks
GROOVE_3 = [
    (0.0, BD, 102), (0.0, HH, 72), (0.5, HH, 56), (0.5, SD, 30),
    (1.0, SD, 106), (1.0, HH, 68), (1.5, HH, 56), (1.75, BD, 72),
    (2.0, HH, 72), (2.5, HH, 56), (2.5, SD, 28), (2.75, BD, 78),
    (3.0, SD, 106), (3.0, HH, 68), (3.5, HH, 56), (3.75, BD, 66),
]

# MOTIF 1 on the ride
GROOVE_4 = [
    (0.0, BD, 100), (0.0, RIDE, 70), (0.5, RIDE, 56), (0.5, SD, 30),
    (1.0, SD, 106), (1.0, RIDE, 66), (1.5, RIDE, 54), (1.5, BD, 72),
    (2.0, BD, 92), (2.0, RIDE, 70), (2.5, RIDE, 56), (2.5, SD, 32),
    (3.0, SD, 106), (3.0, RIDE, 66), (3.5, RIDE, 54), (3.75, BD, 68),
]

# MOTIF 1 stretched into half time -- backbeat lands on beat 3
GROOVE_5 = [
    (0.0, BD, 104), (0.0, HH, 72), (0.5, HH, 56), (0.5, SD, 30),
    (1.0, HH, 60), (1.5, HH, 56), (1.75, BD, 70),
    (2.0, SD, 110), (2.0, HH, 72), (2.5, HH, 56), (2.5, SD, 32),
    (3.0, HH, 60), (3.25, BD, 74), (3.5, HH, 56), (3.75, SD, 28),
]

# MOTIF 2: the same shape played on the floor toms instead of the kick
TOM_1 = [
    (0.0, F_LOW, 104), (0.0, HH, 70), (0.5, HH, 56), (0.5, SD, 30),
    (1.0, SD, 106), (1.0, HH, 66), (1.5, F_HI, 84), (1.5, HH, 54),
    (2.0, F_LOW, 100), (2.0, HH, 70), (2.5, HH, 56), (2.5, SD, 32),
    (3.0, SD, 106), (3.0, HH, 66), (3.5, T_LOW, 86), (3.5, HH, 54),
    (3.75, SD, 26),
]

TOM_2 = [
    (0.0, F_LOW, 106), (0.0, RIDE, 68), (0.5, RIDE, 54), (0.5, SD, 28),
    (1.0, SD, 104), (1.0, RIDE, 64), (1.25, F_HI, 76), (1.5, RIDE, 52),
    (1.75, F_LOW, 82),
    (2.0, F_LOW, 98), (2.0, RIDE, 68), (2.5, RIDE, 54), (2.5, SD, 34),
    (3.0, SD, 104), (3.0, RIDE, 64), (3.25, T_LOMID, 88), (3.5, F_HI, 84),
    (3.75, F_LOW, 90),
]

TOM_3 = [
    (0.0, F_LOW, 102), (0.0, HH, 68), (0.5, HH, 54), (0.75, F_HI, 76),
    (1.0, SD, 104), (1.0, HH, 64), (1.5, HH, 54), (1.5, SD, 30),
    (2.0, F_LOW, 100), (2.0, HH, 68), (2.25, F_HI, 72), (2.5, HH, 54),
    (3.0, SD, 104), (3.0, HH, 64), (3.5, T_LOW, 84), (3.75, T_LOMID, 80),
]

# MOTIF 3: a ride pattern with the snare comping around the backbeat
RIDE_1 = [
    (0.0, RIDE, 72), (0.0, BD, 84), (0.5, RIDE, 56), (0.75, SD, 26),
    (1.0, RIDE, 66), (1.5, RIDE, 54), (1.5, SD, 88), (1.75, BD, 62),
    (2.0, RIDE, 70), (2.0, BD, 80), (2.5, RIDE, 54), (2.75, SD, 30),
    (3.0, RIDE, 66), (3.5, RIDE, 54), (3.5, SD, 92), (3.75, BD, 64),
]

RIDE_2 = [
    (0.0, RIDE, 72), (0.0, BD, 84), (0.5, RIDE, 56), (0.5, SD, 28),
    (1.0, RIDE, 66), (1.0, SD, 96), (1.5, RIDE, 54), (1.75, SD, 30),
    (2.0, BELL, 78), (2.0, BD, 86), (2.5, BELL, 60), (2.75, SD, 34),
    (3.0, RIDE, 66), (3.0, SD, 96), (3.5, RIDE, 54), (3.5, BD, 70),
    (3.75, SD, 26),
]

# Double-time hats with a rock backbeat
DT_1 = [
    (0.0, HH, 74), (0.0, BD, 96), (0.25, HH, 54), (0.5, HH, 60), (0.5, SD, 30),
    (0.75, HH, 52), (1.0, HH, 66), (1.0, SD, 104), (1.25, HH, 54),
    (1.5, HH, 60), (1.5, BD, 72), (1.75, HH, 52),
    (2.0, HH, 74), (2.0, BD, 92), (2.25, HH, 54), (2.5, HH, 60), (2.5, SD, 32),
    (2.75, HH, 52), (3.0, HH, 66), (3.0, SD, 104), (3.25, HH, 54),
    (3.5, HH, 62), (3.5, BD, 74), (3.75, HH, 52),
]

DT_2 = [
    (0.0, HH, 76), (0.0, BD, 98), (0.25, HH, 54), (0.5, HH, 60), (0.5, SD, 30),
    (0.75, HH, 52), (1.0, HH, 66), (1.0, SD, 106), (1.25, HH, 54),
    (1.25, BD, 70), (1.5, HH, 60), (1.75, HH, 52), (1.75, SD, 28),
    (2.0, HH, 74), (2.0, BD, 94), (2.25, HH, 54), (2.5, HH, 60), (2.5, SD, 32),
    (2.75, HH, 52), (3.0, HH, 66), (3.0, SD, 106), (3.25, HH, 54),
    (3.5, HHO, 74), (3.5, BD, 72),
]

# Bell of the ride carrying the time
BELL_1 = [
    (0.0, BELL, 82), (0.0, BD, 100), (0.5, BELL, 60), (0.5, SD, 30),
    (1.0, BELL, 72), (1.0, SD, 106), (1.5, BELL, 58), (1.75, BD, 74),
    (2.0, BELL, 80), (2.0, BD, 96), (2.5, BELL, 60), (2.5, SD, 32),
    (3.0, BELL, 72), (3.0, SD, 106), (3.5, BELL, 58), (3.75, SD, 26),
]

BELL_2 = [
    (0.0, BELL, 82), (0.0, BD, 100), (0.25, BELL, 56), (0.5, BELL, 62),
    (0.5, SD, 30), (0.75, BELL, 54), (1.0, BELL, 70), (1.0, SD, 106),
    (1.25, BELL, 56), (1.5, BELL, 62), (1.75, BELL, 54), (1.75, BD, 76),
    (2.0, BELL, 80), (2.0, BD, 94), (2.25, BELL, 56), (2.5, BELL, 62),
    (2.5, SD, 32), (2.75, BELL, 54), (3.0, BELL, 70), (3.0, SD, 106),
    (3.25, BELL, 56), (3.5, BELL, 62), (3.75, BELL, 54), (3.75, SD, 28),
]

# Fill cells -- two beats each (sixteenths, or eighth triplets)
FILLS = [
    ([SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW, F_LOW], 0.25),
    ([SD, T_HI, SD, T_HIMID, SD, T_LOMID, SD, F_LOW], 0.25),
    ([T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW], 1.0 / 3.0),
    ([SD, SD, T_HIMID, T_HIMID, T_LOW, T_LOW, F_LOW, F_LOW], 0.25),
    ([SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW, SD, SD], 0.25),
]


def ramp_at(beat, b0, b1, v0, v1):
    """Linear tempo reference curve, used to keep gestures glued to the map."""
    if b1 <= b0:
        return v1
    return v0 + (v1 - v0) * (beat - b0) / (b1 - b0)


class Solo(object):
    """Collects notes (in beat time) and tempo events."""

    def __init__(self, seed=20240917):
        self.rng = random.Random(seed)
        self.notes = []       # (beat, note, velocity, duration)
        self.tempos = []      # (beat, bpm)
        self._off = 0.0       # per-phrase timing push / drag

    # ------------------------------------------------------------ tempo
    def tempo(self, beat, bpm):
        self.tempos.append((float(beat), float(bpm)))

    def ramp(self, b0, b1, v0, v1, step=1.0, wob=0.0, period=9.0, phase=0.0):
        """Tempo glides from v0 to v1, with an optional breathing wobble."""
        n = max(1, int(round((b1 - b0) / step)))
        for i in range(n + 1):
            f = i / float(n)
            b = b0 + (b1 - b0) * f
            v = v0 + (v1 - v0) * f
            if wob:
                v += wob * math.sin(2.0 * math.pi * (b - b0) / period + phase)
            self.tempo(b, max(20.0, min(300.0, v)))

    def push(self, b0, b1, base0, base1, amount, step=0.5):
        """A short rush -- the phrase leans forward, then settles back."""
        n = max(1, int(round((b1 - b0) / step)))
        for i in range(n + 1):
            f = i / float(n)
            b = b0 + (b1 - b0) * f
            base = base0 + (base1 - base0) * f
            self.tempo(b, base + amount * math.sin(math.pi * f))

    # ------------------------------------------------------------ notes
    def phrase(self, amount=0.006):
        """Every phrase sits slightly ahead of or behind the beat."""
        self._off = self.rng.uniform(-amount, amount)

    def hit(self, beat, note, vel, dur=0.0, hum=0.006):
        t = beat + self._off + self.rng.gauss(0.0, hum)
        if t < 0.0:
            t = 0.0
        v = int(round(vel + self.rng.gauss(0.0, 2.5)))
        v = max(1, min(127, v))
        if dur <= 0.0:
            dur = 0.55 if note in CYMBALS else 0.12
        self.notes.append((t, int(note), v, float(dur)))

    def bar(self, b0, pattern, energy=1.0, hum=0.006):
        for pos, note, vel in pattern:
            self.hit(b0 + pos, note, vel * energy, hum=hum)

    def run(self, b0, n, notes, step=0.25, v0=70.0, v1=100.0,
            accent=0, acc_amt=1.18, hum=0.006, dur=0.09):
        """n single strokes travelling through the given drums."""
        for i in range(n):
            f = i / float(n - 1) if n > 1 else 0.0
            v = v0 + (v1 - v0) * f
            if accent and i % accent == 0:
                v *= acc_amt
            self.hit(b0 + i * step, notes[i % len(notes)], v, dur=dur, hum=hum)

    def fill(self, b0, kind=0, v0=72.0, v1=104.0):
        seq, step = FILLS[kind % len(FILLS)]
        n = len(seq)
        for i in range(n):
            f = i / float(n - 1) if n > 1 else 0.0
            v = v0 + (v1 - v0) * f
            if i % 4 == 0:
                v *= 1.16
            self.hit(b0 + i * step, seq[i], v, hum=0.005)
        kind %= 3
        if kind == 1:
            self.hit(b0 + 1.0, BD, v1 * 0.72)
        elif kind == 2:
            self.hit(b0 + 0.5, BD, v1 * 0.66)
            self.hit(b0 + 1.5, BD, v1 * 0.70)

    # --------------------------------------------------- playability gate
    def filtered(self):
        """Keep only what one drummer can play: two hands, two feet."""
        ordered = sorted(self.notes, key=lambda e: (e[0], e[1], e[2]))
        kept = []
        dropped = 0
        for ev in ordered:
            t, note = ev[0], ev[1]
            hands = 0 if note in FEET else 1
            feet = 1 if note in FEET else 0
            dup = False
            for k in reversed(kept):
                gap = t - k[0]
                if gap > 0.05:
                    break
                if k[1] == note and gap < 0.02:
                    dup = True          # same drum twice in the same instant
                    break
                if k[1] in FEET:
                    feet += 1
                else:
                    hands += 1
            if dup or hands > 2 or feet > 2 or hands + feet > 4:
                dropped += 1
                continue
            kept.append(ev)
        return kept, dropped


# --------------------------------------------------------------------------
def compose():
    s = Solo(20240917)

    # ==================================================================
    # 1. OPENING (bars 1-4).  A press roll swells out of nothing and
    #    rushes into the first downbeat; two spare bars let it breathe.
    # ==================================================================
    s.ramp(0.0, 4.0, 86.0, 106.0, step=0.5)
    s.ramp(4.0, 8.0, 106.0, 101.0, step=0.5)
    s.ramp(8.0, 16.0, 101.0, 108.0, step=0.5)

    s.phrase(0.004)
    for i in range(8):                                   # sixteenths
        s.hit(0.25 * i, SD, 26 + 3.2 * i, dur=0.14, hum=0.012)
    for i in range(4):                                   # pressure builds
        s.hit(2.0 + 0.25 * i, SD, 52 + 5.0 * i, dur=0.12, hum=0.012)
    for i in range(8):                                   # the buzz
        s.hit(3.0 + 0.125 * i, SD, 74 + 3.4 * i, dur=0.09, hum=0.010)

    s.hit(4.0, CRASH, 116, dur=1.6, hum=0.002)
    s.hit(4.0, BD, 108, dur=0.15, hum=0.002)

    s.phrase(0.008)
    for off, note, vel in [
            (0.5, RIDE, 56), (1.0, RIDE, 64), (1.25, SD, 28), (1.5, RIDE, 54),
            (2.0, SD, 104), (2.0, RIDE, 66), (2.5, RIDE, 54), (2.75, BD, 72),
            (3.0, RIDE, 60), (3.25, SD, 30), (3.5, BD, 74), (3.75, SD, 24)]:
        s.hit(4.0 + off, note, vel)

    s.hit(8.0, CRASH2, 98, dur=1.3)
    s.hit(8.0, BD, 104)
    for i in range(8):
        s.hit(8.0 + 0.5 * i, RIDE, 60 if i % 2 == 0 else 50)
    s.hit(10.0, SD, 102)
    s.hit(10.75, BD, 70)
    s.hit(11.0, SD, 32)
    s.hit(11.5, BD, 64)
    s.hit(11.5, SD, 26)

    s.phrase(0.005)
    s.run(12.0, 6, [SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW],
          step=0.25, v0=62, v1=80)
    s.run(13.5, 10, [F_HI, F_LOW, T_LOW, T_LOMID, T_HIMID, T_HI, SD, SD, SD, SD],
          step=0.25, v0=82, v1=110)

    # ==================================================================
    # 2. THEME (bars 5-16).  Motif 1 stated, then re-invented every bar.
    #    Crescendo inside each four bar phrase, fill into each downbeat.
    # ==================================================================
    s.ramp(16.0, 64.0, 108.0, 124.0, step=1.0, wob=1.6, period=9.5, phase=0.8)
    grooves = [GROOVE_1, GROOVE_5, GROOVE_2, GROOVE_3, GROOVE_4, GROOVE_2]
    for bar in range(12):
        b0 = 16.0 + 4.0 * bar
        s.phrase(0.006)
        pat = grooves[bar % len(grooves)]
        energy = 0.94 + 0.04 * (bar % 4)
        if bar % 4 == 0:
            crash = CRASH if bar % 8 == 0 else CRASH2
            s.hit(b0, crash, 102 if bar % 8 else 106, dur=1.3)
        if bar % 4 == 3:
            s.bar(b0, [e for e in pat if e[0] < 2.0], energy=energy)
            base0 = ramp_at(b0 + 2.0, 16.0, 64.0, 108.0, 124.0)
            base1 = ramp_at(b0 + 4.0, 16.0, 64.0, 108.0, 124.0)
            s.push(b0 + 2.0, b0 + 4.0, base0, base1, 3.0)
            s.fill(b0 + 2.0, (bar // 4) % len(FILLS), 72.0, 104.0)
        else:
            s.bar(b0, pat, energy=energy)
            if s.rng.random() < 0.35:                    # small ornament
                s.hit(b0 + 3.25, T_LOW, 46 + 18 * s.rng.random())

    # ==================================================================
    # 3. THE KIT ANSWERS (bars 17-24).  Motif 1 with the floor toms
    #    playing the kick part; a two bar hands-only excursion; a big fill.
    # ==================================================================
    s.ramp(64.0, 96.0, 124.0, 134.0, step=1.0, wob=1.4, period=8.5, phase=1.9)
    tom_pats = [TOM_1, TOM_2, TOM_3]
    for bar in range(8):
        b0 = 64.0 + 4.0 * bar
        s.phrase(0.006)
        energy = 0.96 + 0.03 * (bar % 4)
        if bar < 6:
            if bar % 2 == 0:
                s.hit(b0, CRASH if bar % 4 == 0 else CRASH2, 102, dur=1.2)
            s.bar(b0, tom_pats[bar % 3], energy=energy)
        elif bar == 6:
            s.hit(b0, CRASH, 106, dur=1.2)
            s.run(b0, 8, [T_HI, T_HIMID, T_LOMID, T_LOW,
                          F_HI, F_LOW, F_HI, T_LOW],
                  step=0.25, v0=80, v1=96, accent=4)
            s.run(b0 + 2.0, 8, [T_HIMID, T_HI, SD, T_HI,
                                T_HIMID, SD, T_LOMID, F_LOW],
                  step=0.25, v0=88, v1=104, accent=4)
            for k in range(4):
                s.hit(b0 + k, BD, 92)
        else:
            s.run(b0, 8, [SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW],
                  step=0.25, v0=84, v1=106)
            s.run(b0 + 2.0, 6, [F_LOW, T_LOW, T_LOMID, T_HIMID, T_HI, SD],
                  step=1.0 / 3.0, v0=98, v1=114)
            s.run(b0 + 3.0, 4, [SD, SD, SD, SD], step=0.25, v0=102, v1=118)

    s.hit(96.0, CRASH, 112, dur=1.5)
    s.hit(96.0, BD, 108)

    # ==================================================================
    # 4. RIDE AND DOUBLE TIME (bars 25-40).  Motif 3 on the ride, then
    #    double-time hats, then the bell, then hands alone, then a climb.
    # ==================================================================
    s.ramp(96.0, 160.0, 134.0, 146.0, step=1.0, wob=1.8, period=10.0, phase=2.2)
    for bar in range(16):
        b0 = 96.0 + 4.0 * bar
        s.phrase(0.007)
        if bar % 4 == 0:
            s.hit(b0, CRASH if bar % 8 == 0 else CRASH2, 106, dur=1.4)
        if bar < 4:
            s.bar(b0, RIDE_1 if bar % 2 == 0 else RIDE_2,
                  energy=0.96 + 0.025 * (bar % 4))
        elif bar < 8:
            s.bar(b0, DT_1 if bar % 2 == 0 else DT_2,
                  energy=0.98 + 0.025 * (bar % 4))
        elif bar < 10:
            s.bar(b0, BELL_1 if bar % 2 == 0 else BELL_2, energy=1.02)
        elif bar < 12:
            s.run(b0, 16, [SD, T_HI, T_HIMID, T_LOMID,
                           T_LOW, F_HI, F_LOW, T_LOW],
                  step=0.25, v0=84, v1=100, accent=4)
            for k in range(4):
                s.hit(b0 + k, BD, 92)
        elif bar < 13:
            s.run(b0, 16, [SD, SD, SD, SD, T_HI, T_HI, T_HIMID, T_HIMID],
                  step=0.25, v0=88, v1=104, accent=2, acc_amt=1.22)
            for k in range(4):
                s.hit(b0 + k, BD, 96)
        elif bar < 14:
            s.run(b0, 16, [T_HI, T_HIMID, T_LOMID, T_LOW,
                           T_LOW, T_LOMID, T_HIMID, T_HI],
                  step=0.25, v0=92, v1=106, accent=4)
            for k in range(4):
                s.hit(b0 + k, BD, 98)
                s.hit(b0 + k + 0.5, PHH, 54)
        elif bar < 15:
            s.run(b0, 16, [SD, T_HI, SD, T_HIMID, SD, T_LOMID, SD, T_LOW],
                  step=0.25, v0=96, v1=112, accent=4)
            for k in range(4):
                s.hit(b0 + k, BD, 100)
        else:
            s.run(b0, 8, [SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW, F_LOW],
                  step=0.25, v0=100, v1=114)
            s.run(b0 + 2.0, 8, [F_LOW, T_LOW, T_LOMID, T_HIMID, T_HI, SD, SD, SD],
                  step=0.25, v0=106, v1=120)
            for k in range(2):
                s.hit(b0 + 2.0 + k, BD, 104)

    # ==================================================================
    # 5. THE QUIET PLACE (bars 41-46).  Space, rim clicks, floor toms.
    #    Colour section: a cowbell pickup starts the next climb.
    # ==================================================================
    s.ramp(160.0, 176.0, 142.0, 124.0, step=1.0, wob=1.2, period=8.0, phase=0.3)
    s.ramp(176.0, 184.0, 124.0, 118.0, step=1.0)

    s.hit(160.0, CRASH2, 108, dur=1.8)
    s.hit(160.0, BD, 104)

    s.phrase(0.010)
    s.hit(160.0, BD, 0)                      # placeholder keeps rng aligned
    s.hit(161.0, PHH, 60)
    s.hit(161.0, RS, 58)
    s.hit(162.0, SD, 88)
    s.hit(162.5, BD, 72)
    s.hit(163.0, PHH, 56)
    s.hit(163.5, SD, 30)

    s.phrase(0.010)
    s.hit(164.0, BD, 96)
    s.hit(164.5, SD, 28)
    s.hit(165.0, RS, 60)
    s.hit(165.0, TAMB, 52)
    s.hit(166.0, SD, 92)
    s.hit(166.0, PHH, 58)
    s.hit(166.5, BD, 70)
    s.hit(166.75, SD, 32)
    s.hit(167.0, F_LOW, 88)
    s.hit(167.5, F_HI, 84)
    s.hit(167.75, SD, 40)

    s.phrase(0.012)
    for pos, note, vel in [
            (0.0, F_LOW, 88), (0.5, F_LOW, 64), (1.0, T_LOW, 80),
            (1.25, T_LOW, 52), (1.5, T_LOMID, 76), (2.0, T_LOMID, 84),
            (2.5, T_LOMID, 58), (3.0, T_LOW, 78), (3.25, T_LOW, 50),
            (3.5, F_LOW, 86), (3.75, SD, 34)]:
        s.hit(168.0 + pos, note, vel, hum=0.012)

    s.phrase(0.010)
    for pos, note, vel in [
            (0.0, F_LOW, 90), (0.5, F_HI, 62), (1.0, T_LOW, 82),
            (1.5, T_LOMID, 74), (1.75, SD, 30), (2.0, F_LOW, 86),
            (2.5, T_LOW, 66), (3.0, T_LOMID, 80), (3.25, SD, 36),
            (3.5, SPLASH, 74)]:
        s.hit(172.0 + pos, note, vel, hum=0.012)

    # cowbell pickup
    s.phrase(0.006)
    for i in range(8):
        s.hit(176.0 + 0.5 * i, COW, 66 if i % 2 == 0 else 54)
    s.hit(176.0, BD, 84)
    s.hit(177.5, BD, 70)
    s.hit(178.0, SD, 80)
    s.hit(179.0, BD, 76)
    s.hit(179.5, SD, 34)
    s.run(180.0, 8, [SD, SD, SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW],
          step=0.25, v0=70, v1=90)
    s.run(182.0, 8, [T_LOW, F_HI, F_LOW, SD, SD, T_HI, T_HIMID, T_LOMID],
          step=0.25, v0=90, v1=108)
    for k in range(4):
        s.hit(180.0 + k, BD, 88)

    # ==================================================================
    # 6. THE CLIMB (bars 47-54).  Hands-only sixteenths sweep the kit
    #    while the tempo accelerates; the roll resolves on the downbeat.
    # ==================================================================
    s.ramp(184.0, 208.0, 118.0, 148.0, step=0.5, wob=2.0, period=7.0, phase=0.5)
    s.ramp(208.0, 216.0, 148.0, 153.0, step=0.5)
    build_cells = [
        [SD, SD, T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOMID],
        [SD, T_HI, SD, T_HIMID, SD, T_LOMID, SD, T_LOW],
        [T_HI, T_HIMID, T_LOMID, T_LOW, T_LOW, T_LOMID, T_HIMID, T_HI],
        [SD, SD, SD, SD, T_LOW, T_LOW, F_LOW, F_LOW],
        [SD, SD, T_HIMID, T_HIMID, T_LOW, T_LOW, F_HI, F_LOW],
        [SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW, SD],
    ]
    for bar in range(6):
        b0 = 184.0 + 4.0 * bar
        s.phrase(0.005)
        cell = build_cells[bar % len(build_cells)]
        v0 = 62.0 + 5.0 * bar
        v1 = v0 + 14.0
        s.run(b0, 16, cell * 2, step=0.25, v0=v0, v1=v1,
              accent=4, acc_amt=1.20, hum=0.005)
        if bar < 3:
            for k in range(4):
                s.hit(b0 + k, BD, 70 + 6.0 * bar)
        else:
            for k in range(4):
                s.hit(b0 + k, BD, 88 + 5.0 * (bar - 3))
                s.hit(b0 + k + 0.5, PHH, 56)

    # last two bars of the climb: everything swells
    s.phrase(0.004)
    s.run(208.0, 8, [SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW],
          step=0.25, v0=104, v1=116, accent=4)
    s.run(210.0, 8, [F_LOW, T_LOW, T_LOMID, T_HIMID, T_HI, SD, SD, SD],
          step=0.25, v0=108, v1=120, accent=4)
    s.run(212.0, 8, [SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW, SD],
          step=0.25, v0=110, v1=124, accent=4)
    s.run(214.0, 8, [SD, SD, SD, SD, T_HI, T_HIMID, T_LOMID, F_LOW],
          step=0.25, v0=112, v1=126, accent=2, acc_amt=1.12)
    for k in range(4):
        s.hit(212.0 + k, BD, 106)

    # ==================================================================
    # 7. THE MOTIF RETURNS, BIG (bars 55-62).  Motif 1 at full size,
    #    half time for contrast, double time, then a last run up.
    # ==================================================================
    s.ramp(216.0, 240.0, 150.0, 148.0, step=1.0, wob=1.5, period=7.5, phase=1.2)
    s.ramp(240.0, 248.0, 148.0, 152.0, step=1.0)

    for bar in range(8):
        b0 = 216.0 + 4.0 * bar
        s.phrase(0.006)
        if bar == 0:
            s.hit(b0, CRASH, 112, dur=1.5)
            s.hit(b0, BD, 106)
            s.bar(b0, GROOVE_1, 1.10)
        elif bar == 1:
            s.bar(b0, GROOVE_5, 1.08)
        elif bar == 2:
            s.hit(b0, CRASH2, 106, dur=1.4)
            s.bar(b0, GROOVE_2, 1.10)
        elif bar == 3:
            s.bar(b0, [e for e in GROOVE_3 if e[0] < 2.0], 1.12)
            s.fill(b0 + 2.0, 0, 86.0, 116.0)
        elif bar == 4:
            s.hit(b0, CRASH, 112, dur=1.5)
            s.hit(b0, BD, 108)
            s.bar(b0, DT_1, 1.06)
        elif bar == 5:
            s.bar(b0, DT_2, 1.06)
        elif bar == 6:
            s.hit(b0, CRASH2, 110, dur=1.4)
            s.hit(b0, BD, 108)
            s.run(b0, 8, [SD, T_HI, T_HIMID, T_LOMID,
                          T_LOW, F_HI, F_LOW, T_LOW],
                  step=0.25, v0=96, v1=112, accent=4)
            s.run(b0 + 2.0, 8, [T_LOW, F_HI, F_LOW, T_LOW,
                                SD, SD, T_HI, T_HIMID],
                  step=0.25, v0=100, v1=114, accent=4)
        else:
            s.run(b0, 8, [SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW],
                  step=0.25, v0=100, v1=116)
            s.run(b0 + 2.0, 4, [F_LOW, T_LOW, T_LOMID, T_HIMID],
                  step=0.25, v0=108, v1=118)
            s.run(b0 + 3.0, 4, [SD, SD, SD, SD], step=0.25, v0=110, v1=124)

    s.hit(248.0, CRASH, 114, dur=1.6)
    s.hit(248.0, BD, 110)

    # ==================================================================
    # 8. FINALE (bars 63-66).  Roll, tour of the toms, one last push,
    #    and the final hit -- landed, not faded.
    # ==================================================================
    s.ramp(248.0, 262.0, 152.0, 160.0, step=0.5)
    s.ramp(262.0, 264.0, 160.0, 158.0, step=0.5)

    s.phrase(0.005)
    for i in range(16):
        f = i / 15.0
        v = 88 + 22.0 * f
        if i % 4 == 0:
            v *= 1.25
        elif i % 2 == 0:
            v *= 1.08
        s.hit(248.0 + 0.25 * i, SD, v, dur=0.08, hum=0.005)
    for k in range(4):
        s.hit(248.0 + k, BD, 100)

    s.run(252.0, 16, [SD, T_HI, T_HIMID, T_LOMID,
                      T_LOW, F_HI, F_LOW, T_LOW],
          step=0.25, v0=92, v1=106, accent=4)

    s.hit(256.0, CRASH, 112, dur=1.5)
    s.hit(256.0, BD, 108)
    s.bar(256.0, GROOVE_1, 1.12)

    s.run(260.0, 8, [SD, SD, T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW],
          step=0.25, v0=100, v1=112)
    s.run(262.0, 8, [F_LOW, T_LOW, T_LOMID, T_HIMID, T_HI, SD, SD, SD],
          step=0.25, v0=110, v1=124, accent=4, acc_amt=1.06)

    # THE LAST HIT
    s.hit(264.0, CRASH, 122, dur=3.0, hum=0.001)
    s.hit(264.0, CRASH2, 118, dur=3.0, hum=0.001)
    s.hit(264.0, BD, 118, dur=0.20, hum=0.001)

    return s


# --------------------------------------------------------------------------
def write_midi(solo, path="solo.mid"):
    notes, dropped = solo.filtered()

    # ---- tempo map (last event at a given beat wins) ----
    tempo_at = {}
    order = []
    for beat, bpm in solo.tempos:
        key = round(beat, 6)
        if key not in tempo_at:
            order.append(key)
        tempo_at[key] = bpm
    order.sort()

    end_beat = 264.0 + 6.0     # let the last cymbal ring, then stop

    total = 0.0
    cur_beat, cur_bpm = 0.0, (tempo_at[order[0]] if order else 120.0)
    for b in order:
        if b > cur_beat:
            total += (b - cur_beat) * 60.0 / cur_bpm
            cur_beat = b
        cur_bpm = tempo_at[b]
    total += (end_beat - cur_beat) * 60.0 / cur_bpm

    mid = MidiFile(ticks_per_beat=TICKS_PER_BEAT)

    # ---- conductor track ----
    meta = MidiTrack()
    mid.tracks.append(meta)
    meta.append(MetaMessage("track_name", name="Drum Solo", time=0))
    meta.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    last_tick = 0
    for b in order:
        bpm = max(20.0, min(300.0, tempo_at[b]))
        tick = int(round(b * TICKS_PER_BEAT))
        if tick < last_tick:
            continue
        meta.append(MetaMessage("set_tempo",
                                tempo=int(round(60000000.0 / bpm)),
                                time=tick - last_tick))
        last_tick = tick

    # ---- drum track ----
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("track_name", name="Drums", time=0))

    events = []
    for t, note, vel, dur in notes:
        on = int(round(t * TICKS_PER_BEAT))
        off = int(round((t + dur) * TICKS_PER_BEAT))
        if off <= on:
            off = on + 1
        events.append((on, 1, note, vel))
        events.append((off, 0, note, 0))
    events.sort(key=lambda e: (e[0], e[1], e[2]))

    last_tick = 0
    for tick, kind, note, vel in events:
        delta = tick - last_tick
        if delta < 0:
            delta = 0
        last_tick = tick
        if kind:
            track.append(Message("note_on", channel=CH, note=note,
                                 velocity=vel, time=delta))
        else:
            track.append(Message("note_off", channel=CH, note=note,
                                 velocity=0, time=delta))
    track.append(MetaMessage("end_of_track", time=2 * TICKS_PER_BEAT))

    mid.save(path)

    print("wrote %s : %.1f s, %d notes, %d unplayable hits removed"
          % (path, total, len(notes), dropped))


def main():
    solo = compose()
    write_midi(solo, "solo.mid")


if __name__ == "__main__":
    main()
