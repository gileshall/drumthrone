#!/usr/bin/env python3
"""
drum_solo.py

Generates a two minute solo drum performance as a General MIDI file
(solo.mid) on MIDI channel 10.  Everything is deterministic: the same
file is produced on every run.

Musical plan (4/4, 60 bars @ 120 BPM = 2:00):

    bars  0- 3   intro          - crash, ride bell, first fill
    bars  4-11   motif A        - stated, varied, ghost notes
    bars 12-15   breakdown      - half-time toms, quiet, cowbell colour
    bars 16-19   build          - snare roll crescendo
    bars 20-27   A returns      - bigger, denser, tom motif
    bars 28-31   motif B        - toms travelling down and around
    bars 32-35   singles run    - 16ths around the whole kit
    bars 36-39   relief         - quiet side-stick ride groove
    bars 40-47   development    - A + B combined, crashes, splash
    bars 48-51   doubles        - double strokes, crescendo
    bars 52-55   climax         - 32nd bursts, fast singles
    bars 56-59   finale         - fill, landing crash on the last downbeat
"""

import math
import random

from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
TEMPO = 120.0          # BPM
TPB = 480              # ticks per beat
CHANNEL = 9            # MIDI channel 10 (zero based)

# ------------------------------------------------------------ drum numbers
KICK = 36
SNARE = 38
RIM = 37
HH = 42
PEDAL = 44
OPENHH = 46
RIDE = 51
BELL = 53
CRASH = 49
CHINA = 52
SPLASH = 55
T50, T48, T47, T45, T43, T41 = 50, 48, 47, 45, 43, 41
COWBELL = 56
TAMB = 54

# Rows of toms, high to low (used for travelling figures)
TOMS_DOWN = [T50, T48, T47, T45, T43, T41]
TOMS_UP = [T41, T43, T45, T47, T48, T50]

# --------------------------------------------------------------------------
# Event collection.  A beat value is in beats, duration in beats,
# hj is a "humanise" scale (0 = machine tight, 1 = loose hands).
# --------------------------------------------------------------------------
EVENTS = []


def hit(beat, note, vel, dur=0.12, hj=1.0):
    EVENTS.append((float(beat), int(note), float(vel), float(dur), float(hj)))


def flam(beat, note, vel, gap=0.05):
    """Grace note a hair before the main stroke."""
    hit(beat - gap, note, vel * 0.55, 0.10, 0.25)
    hit(beat, note, vel, 0.12, 0.5)


def stream(t0, t1, step, notes, v0, v1, hj=1.0, dur=0.09):
    """Even run of notes from t0 to t1, cycling through `notes`,
    with the velocity ramping from v0 to v1."""
    n = max(1, int(round((t1 - t0) / step)))
    for k in range(n):
        f = k / (n - 1.0) if n > 1 else 0.0
        hit(t0 + k * step, notes[k % len(notes)], v0 + (v1 - v0) * f, dur, hj)


def run(t0, groups, base=84, accent=106, step=0.25, hj=0.8, dur=0.09):
    """Single strokes, `groups` = [(note, count), ...]; first of each
    group is accented.  Returns the beat after the last stroke."""
    t = t0
    for note, count in groups:
        for i in range(count):
            hit(t, note, accent if i == 0 else base, dur, hj)
            t += step
    return t


# --------------------------------------------------------------------------
# Generic groove helper (motif A and its variations)
# --------------------------------------------------------------------------
def groove(bar, ride=RIDE, ride_vel=84, kicks=(0.0, 2.5), snares=(1.0, 3.0),
           ghosts=(0.75, 1.75, 2.75, 3.75), skip=(), crash=None, extra=(),
           kick_vel=100, snare_vel=104):
    b = bar * 4.0
    if crash is not None:
        hit(b, crash, 112, 2.0, 0.4)
    for i in range(8):
        t = i * 0.5
        if t in skip:
            continue
        v = ride_vel * (1.0 if i % 2 == 0 else 0.79)
        hit(b + t, ride, v, 0.45)
    for k in kicks:
        hit(b + k, KICK, kick_vel if k in (0.0, 2.5) else kick_vel - 12)
    for s in snares:
        hit(b + s, SNARE, snare_vel)
    for g in ghosts:
        hit(b + g, SNARE, 42)
    for t, n, v in extra:
        hit(b + t, n, v)


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def sec_intro():
    # bar 0 -- crash, ride bell call
    b = 0.0
    hit(b, CRASH, 112, 2.5, 0.4)
    hit(b, KICK, 104)
    hit(b + 1.0, BELL, 80, 0.5)
    hit(b + 1.5, BELL, 70, 0.5)
    hit(b + 2.0, BELL, 76, 0.5)
    hit(b + 2.5, BELL, 70, 0.5)
    hit(b + 3.0, BELL, 82, 0.5)
    hit(b + 3.5, BELL, 72, 0.5)
    hit(b + 2.5, KICK, 86)
    hit(b + 1.75, SNARE, 40)
    hit(b + 3.75, SNARE, 46)

    # bar 1 -- bell / ride alternating, hi-hat foot
    b = 4.0
    for i in range(8):
        hit(b + i * 0.5, BELL if i % 2 == 0 else RIDE,
            78 if i % 2 == 0 else 64, 0.45)
    hit(b, KICK, 92)
    hit(b + 2.5, KICK, 86)
    hit(b + 1.0, PEDAL, 72)
    hit(b + 3.0, PEDAL, 72)
    hit(b + 1.75, SNARE, 42)
    hit(b + 3.75, SNARE, 48)

    # bar 2 -- backbeat arrives
    b = 8.0
    for i in range(8):
        hit(b + i * 0.5, RIDE, 78 if i % 2 == 0 else 64, 0.45)
    hit(b, KICK, 100)
    hit(b + 2.5, KICK, 90)
    hit(b + 1.0, SNARE, 96)
    hit(b + 3.0, SNARE, 100)
    hit(b + 0.75, SNARE, 44)
    hit(b + 2.75, SNARE, 46)

    # bar 3 -- fill that carries into the first statement
    b = 12.0
    seq = [SNARE, SNARE, SNARE, T50, T48, T48, T47, T45,
           T45, T43, T43, T41, T41, T41, T43, T45]
    for i, n in enumerate(seq):
        hit(b + i * 0.25, n, 72 + i * 2.3, 0.10, 0.9)


def sec_statement():
    """Motif A: ride eighths, backbeat, kick on 1 and the 'and' of 3,
    ghost notes on the 'a' of every beat."""
    groove(4)
    groove(5, kicks=(0.0, 1.5, 2.5), ghosts=(0.75, 1.75, 2.25, 2.75, 3.75))
    groove(6, ride=HH, ride_vel=78, skip=(3.5,), extra=[(3.5, OPENHH, 88)])
    groove(7, kicks=(0.0, 2.5, 3.25), ghosts=(0.75, 1.75, 2.75, 3.25))

    # bar 8 -- ghost-note field under the ride
    b = 32.0
    for i in range(8):
        hit(b + i * 0.5, RIDE, 84 if i % 2 == 0 else 66, 0.45)
    hit(b, KICK, 102)
    hit(b + 2.5, KICK, 92)
    hit(b + 1.0, SNARE, 106)
    hit(b + 3.0, SNARE, 108)
    for i in range(16):
        t = i * 0.25
        if abs(t - 1.0) < 1e-6 or abs(t - 3.0) < 1e-6:
            continue
        hit(b + t, SNARE, 46 if i % 2 else 38)

    # bar 9 -- crash and drive
    groove(9, crash=CRASH, skip=(0.0,), ride_vel=94,
           kick_vel=104, snare_vel=108)

    # bar 10 -- thinning out
    groove(10, ride_vel=70, kicks=(0.0,), snares=(),
           ghosts=(0.75, 2.75), kick_vel=80)

    # bar 11 -- sparse pickup into the breakdown
    b = 44.0
    hit(b, KICK, 78)
    hit(b + 1.0, RIM, 62)
    hit(b + 2.0, RIM, 64)
    hit(b + 3.0, RIM, 66)
    hit(b + 3.5, T43, 70)


def sec_breakdown():
    """Quiet half-time tom figure -- the tension before the build."""
    # bar 12
    b = 48.0
    hit(b, KICK, 88)
    hit(b + 0.0, T48, 78)
    hit(b + 0.5, T47, 72)
    hit(b + 1.0, T45, 70)
    hit(b + 1.75, SNARE, 38)
    hit(b + 2.0, T47, 76)
    hit(b + 2.5, T45, 70)
    hit(b + 3.0, T43, 68)
    hit(b + 3.5, RIM, 58)

    # bar 13
    b = 52.0
    hit(b, KICK, 90)
    hit(b + 0.0, T47, 80)
    hit(b + 0.5, T45, 74)
    hit(b + 1.0, T43, 72)
    hit(b + 2.0, T45, 78)
    hit(b + 2.5, T43, 74)
    hit(b + 3.0, T41, 72)
    hit(b + 3.5, SNARE, 86)

    # bar 14 -- cowbell colour, gentle snare answer
    b = 56.0
    hit(b, KICK, 92)
    hit(b + 0.0, T48, 82)
    hit(b + 0.5, T47, 76)
    hit(b + 1.0, COWBELL, 74)
    hit(b + 2.0, SNARE, 78)
    hit(b + 2.5, T45, 78)
    hit(b + 3.0, COWBELL, 76)
    hit(b + 3.5, T43, 74)

    # bar 15 -- tom roll crescendo into the build
    b = 60.0
    hit(b, KICK, 90)
    hit(b + 2.0, KICK, 92)
    seq = [T41, T43, T45, T47, T48, T50, T48, T47,
           T45, T43, T41, T43, T45, T47, T48, T50]
    stream(b, b + 4.0, 0.25, seq, 66, 108, 0.8)


def sec_build():
    """Snare roll that swells across four bars."""
    # bar 16 -- accents against ghosts
    b = 64.0
    hit(b, KICK, 100)
    hit(b + 2.0, KICK, 96)
    for i in range(16):
        hit(b + i * 0.25, SNARE, 92 if i % 2 == 0 else 54)

    # bar 17
    b = 68.0
    hit(b, KICK, 102)
    hit(b + 2.5, KICK, 98)
    stream(b, b + 4.0, 0.25, [SNARE], 78, 104)

    # bar 18
    b = 72.0
    hit(b, KICK, 104)
    hit(b + 2.0, KICK, 100)
    for i in range(16):
        hit(b + i * 0.25, SNARE, 84 + i * 1.6)

    # bar 19 -- last rush, hands move to the toms on the final beat
    b = 76.0
    hit(b, KICK, 108)
    stream(b, b + 3.0, 0.25, [SNARE], 96, 122)
    hit(b + 3.0, T50, 108)
    hit(b + 3.25, T48, 106)
    hit(b + 3.5, T47, 104)
    hit(b + 3.75, T45, 110)


def sec_return():
    """Motif A comes back, bigger."""
    groove(20, crash=CRASH, skip=(0.0,), ride_vel=96,
           kick_vel=108, snare_vel=112)
    groove(21, ride_vel=92, kicks=(0.0, 1.5, 2.5, 3.25),
           ghosts=(0.75, 1.75, 2.25, 2.75, 3.75))

    # bar 22 -- ride bell accents
    b = 88.0
    for i in range(8):
        n = BELL if i % 2 == 0 else RIDE
        hit(b + i * 0.5, n, 94 if i % 2 == 0 else 72, 0.45)
    hit(b, KICK, 106)
    hit(b + 2.5, KICK, 98)
    flam(b + 1.0, SNARE, 110)
    hit(b + 3.0, SNARE, 112)
    hit(b + 2.75, SNARE, 46)
    hit(b + 3.75, SNARE, 44)

    # bar 23 -- half-time relief, open hat at the end
    groove(23, ride_vel=88, kicks=(0.0,), snares=(2.0,), ghosts=(1.75, 3.75),
           skip=(3.5,), extra=[(3.5, OPENHH, 88)],
           kick_vel=106, snare_vel=112)

    # bar 24 -- syncopated kick
    groove(24, ride_vel=90, kicks=(0.0, 0.75, 2.5), ghosts=(1.75, 2.75, 3.75))

    # bar 25 -- groove with a tom tail
    groove(25, ride_vel=92, skip=(3.0, 3.5), kicks=(0.0, 2.5),
           extra=[(3.0, T48, 98), (3.25, T47, 94),
                  (3.5, T45, 92), (3.75, T43, 90)])

    # bar 26 -- crash plus the 16th ghost field
    b = 104.0
    hit(b, CRASH, 116, 2.0, 0.4)
    hit(b, KICK, 108)
    for i in range(1, 8):
        hit(b + i * 0.5, RIDE, 94 if i % 2 == 0 else 74, 0.45)
    hit(b + 1.0, SNARE, 110)
    hit(b + 3.0, SNARE, 112)
    hit(b + 2.5, KICK, 100)
    for i in range(16):
        t = i * 0.25
        if abs(t - 1.0) < 1e-6 or abs(t - 3.0) < 1e-6:
            continue
        hit(b + t, SNARE, 48 if i % 2 else 40)

    # bar 27 -- fill to the toms
    b = 108.0
    hit(b, KICK, 106)
    hit(b + 2.0, KICK, 104)
    seq = [SNARE, SNARE, T50, T48, T47, T45, T43, T41,
           T41, T43, T45, T47, T48, T50, T48, T45]
    for i, n in enumerate(seq):
        hit(b + i * 0.25, n, 92 + i * 1.4, 0.10, 0.9)


def sec_toms():
    """Motif B: a three-note tom figure walked down and back."""
    # bar 28
    b = 112.0
    hit(b, KICK, 100)
    hit(b + 2.0, KICK, 92)
    hit(b + 0.0, T50, 92)
    hit(b + 0.5, T48, 86)
    hit(b + 1.0, T47, 84)
    hit(b + 1.75, SNARE, 44)
    hit(b + 2.0, T48, 90)
    hit(b + 2.5, T47, 86)
    hit(b + 3.0, T45, 84)
    hit(b + 3.75, SNARE, 46)

    # bar 29
    b = 116.0
    hit(b, KICK, 100)
    hit(b + 2.0, KICK, 94)
    hit(b + 0.0, T47, 94)
    hit(b + 0.5, T45, 88)
    hit(b + 1.0, T43, 86)
    hit(b + 2.0, T45, 92)
    hit(b + 2.5, T43, 88)
    hit(b + 3.0, T41, 86)
    hit(b + 3.5, SNARE, 96)
    hit(b + 3.75, SNARE, 60)

    # bar 30 -- turns upward
    b = 120.0
    hit(b, KICK, 102)
    hit(b + 2.5, KICK, 96)
    hit(b + 0.0, T41, 96)
    hit(b + 0.5, T43, 90)
    hit(b + 1.0, T45, 88)
    hit(b + 1.5, SNARE, 100)
    hit(b + 2.0, T45, 92)
    hit(b + 2.5, T47, 90)
    hit(b + 3.0, T48, 88)
    hit(b + 3.5, T50, 94)

    # bar 31 -- run back down
    b = 124.0
    hit(b, KICK, 106)
    hit(b + 2.0, KICK, 104)
    seq = [T50, T48, T47, T45, T43, T41, T41, T43,
           T45, T47, T48, T50, T47, T45, T43, T41]
    stream(b, b + 4.0, 0.25, seq, 96, 116, 0.8)


def sec_run():
    """Single strokes travelling around the whole kit."""
    b = 128.0
    hit(b, KICK, 104)
    hit(b + 2.0, KICK, 100)
    run(b, [(SNARE, 4), (T50, 4), (T48, 4), (T47, 4)], base=82, accent=104)

    b = 132.0
    hit(b, KICK, 102)
    run(b, [(T45, 4), (T43, 4), (T41, 4), (T43, 4)], base=82, accent=104)

    b = 136.0
    hit(b, KICK, 102)
    run(b, [(T45, 2), (T47, 2), (T48, 2), (T50, 2),
            (T48, 2), (T47, 2), (T45, 2), (T43, 2)], base=84, accent=106)

    # bar 35 -- decrescendo into the quiet section
    b = 140.0
    hit(b, KICK, 96)
    seq = [T41, T43, T45, T47, T48, T50, T48, T47,
           T45, T43, T41, T43, T45, T47, T48, T50]
    stream(b, b + 4.0, 0.25, seq, 88, 62, 0.8)


def sec_quiet():
    """Side-stick ride groove -- the exhale."""
    for bar in (36, 37):
        b = bar * 4.0
        for i in range(8):
            hit(b + i * 0.5, RIDE, 64 if i % 2 == 0 else 52, 0.45)
        hit(b, KICK, 76)
        hit(b + 2.5, KICK, 70)
        hit(b + 1.0, RIM, 60)
        hit(b + 3.0, RIM, 62)
        hit(b + 0.75, SNARE, 34)
        hit(b + 2.75, SNARE, 36)

    # bar 38 -- a little more motion
    b = 152.0
    for i in range(8):
        hit(b + i * 0.5, RIDE, 68 if i % 2 == 0 else 54, 0.45)
    hit(b, KICK, 80)
    hit(b + 2.0, KICK, 74)
    hit(b + 1.0, RIM, 64)
    hit(b + 3.0, SNARE, 84)
    hit(b + 2.75, SNARE, 40)
    hit(b + 3.75, SNARE, 44)

    # bar 39 -- crescendo back into the music
    b = 156.0
    hit(b, KICK, 86)
    stream(b, b + 4.0, 0.25, [SNARE], 62, 110, 0.9)


def sec_development():
    """Motif A and motif B combined at full voice."""
    groove(40, crash=CRASH, skip=(0.0,), ride_vel=98,
           kick_vel=110, snare_vel=114)

    groove(41, ride_vel=96, kicks=(0.0, 0.75, 2.5, 3.25),
           ghosts=(0.75, 1.75, 2.25, 2.75, 3.75),
           kick_vel=106, snare_vel=112)

    # bar 42 -- motif B against a backbeat
    b = 168.0
    hit(b, KICK, 106)
    hit(b + 2.5, KICK, 100)
    hit(b + 0.0, T48, 96)
    hit(b + 0.5, T47, 90)
    hit(b + 1.0, T45, 88)
    hit(b + 1.5, SNARE, 100)
    hit(b + 2.0, T47, 94)
    hit(b + 2.5, T45, 90)
    hit(b + 3.0, T43, 88)
    hit(b + 3.5, SNARE, 104)

    # bar 43 -- lower, pushing
    b = 172.0
    hit(b, KICK, 106)
    hit(b + 2.0, KICK, 102)
    hit(b + 0.0, T45, 98)
    hit(b + 0.5, T43, 92)
    hit(b + 1.0, T41, 90)
    hit(b + 1.5, T41, 86)
    hit(b + 2.0, T43, 92)
    hit(b + 2.5, T45, 94)
    hit(b + 3.0, T47, 96)
    hit(b + 3.5, T48, 100)

    # bar 44 -- hats for a moment
    groove(44, ride=HH, ride_vel=88, skip=(3.5,), kicks=(0.0, 2.5),
           extra=[(3.5, OPENHH, 96)], kick_vel=106, snare_vel=112)

    # bar 45 -- big ghost field
    b = 180.0
    for i in range(8):
        hit(b + i * 0.5, RIDE, 96 if i % 2 == 0 else 76, 0.45)
    hit(b, KICK, 108)
    hit(b + 2.5, KICK, 102)
    hit(b + 1.0, SNARE, 112)
    hit(b + 3.0, SNARE, 114)
    for i in range(16):
        t = i * 0.25
        if abs(t - 1.0) < 1e-6 or abs(t - 3.0) < 1e-6:
            continue
        hit(b + t, SNARE, 50 if i % 2 else 42)

    # bar 46 -- crash accents and a splash
    b = 184.0
    hit(b, CRASH, 118, 2.0, 0.4)
    hit(b, KICK, 112)
    for i in range(1, 7):
        hit(b + i * 0.5, RIDE, 98 if i % 2 == 0 else 78, 0.45)
    flam(b + 1.0, SNARE, 114)
    hit(b + 3.0, SNARE, 116)
    hit(b + 2.5, KICK, 104)
    hit(b + 3.5, SPLASH, 100, 1.0)

    # bar 47 -- rolling fill
    b = 188.0
    hit(b, KICK, 110)
    hit(b + 2.0, KICK, 106)
    seq = [T50, T48, T47, T45, T43, T41, T43, T45,
           T47, T48, T50, T48, T47, T45, T43, T41]
    stream(b, b + 4.0, 0.25, seq, 96, 118, 0.85)


def sec_doubles():
    """Double strokes on the snare, then the toms, swelling."""
    # bar 48 -- strong/weak 16ths
    b = 192.0
    hit(b, KICK, 106)
    hit(b + 2.0, KICK, 102)
    for i in range(16):
        hit(b + i * 0.25, SNARE, 108 if i % 2 == 0 else 62)

    # bar 49 -- doubles travel to the floor toms
    b = 196.0
    hit(b, KICK, 108)
    hit(b + 2.0, KICK, 104)
    for i in range(8):
        hit(b + i * 0.25, SNARE, 106 if i % 2 == 0 else 66)
    for i in range(8):
        n = T43 if i < 4 else T41
        hit(b + 2.0 + i * 0.25, n, 100 if i % 4 == 0 else 78)

    # bar 50 -- double strokes climbing back up the toms
    b = 200.0
    hit(b, KICK, 108)
    hit(b + 2.0, KICK, 104)
    seq = [T41, T41, T43, T43, T45, T45, T47, T47,
           T48, T48, T50, T50, T48, T47, T45, T43]
    for i, n in enumerate(seq):
        hit(b + i * 0.25, n, 102 if i % 2 == 0 else 74)

    # bar 51 -- crescendo into the climax
    b = 204.0
    hit(b, KICK, 110)
    for i in range(16):
        hit(b + i * 0.25, SNARE, 88 + i * 2, 0.09, 0.9)


def sec_climax():
    """Fast hands: 32nd bursts and singles around the kit."""
    # bar 52
    b = 208.0
    hit(b, CRASH, 118, 2.0, 0.4)
    hit(b, KICK, 112)
    run(b + 0.5, [(T50, 2), (T48, 2), (T47, 2), (T45, 2),
                  (T43, 2), (T41, 2), (T43, 2)],
        base=94, accent=114)

    # bar 53 -- bursts of four 32nds
    b = 212.0
    hit(b, KICK, 110)
    hit(b + 2.0, KICK, 106)
    for beat in (0.0, 1.0, 2.0, 3.0):
        for i in range(4):
            hit(b + beat + i * 0.125, SNARE, 110 if i == 0 else 86)

    # bar 54 -- fast singles
    b = 216.0
    hit(b, KICK, 110)
    run(b, [(SNARE, 4), (T50, 4), (T48, 4), (T47, 4)], base=90, accent=112)
    hit(b + 2.0, KICK, 108)

    # bar 55 -- cascading fill
    b = 220.0
    hit(b, KICK, 112)
    hit(b + 2.0, KICK, 108)
    seq = [T50, T48, T47, T45, T43, T41, T41, T43,
           T45, T47, T48, T50, T50, T48, T47, T45]
    stream(b, b + 4.0, 0.25, seq, 100, 120, 0.85)


def sec_finale():
    """Last fill and the landing."""
    # bar 56
    b = 224.0
    hit(b, KICK, 112)
    for i in range(16):
        hit(b + i * 0.25, SNARE, 112 if i % 4 == 0 else 90)

    # bar 57
    b = 228.0
    hit(b, KICK, 112)
    run(b, [(T41, 4), (T43, 4), (T45, 4), (T47, 4)], base=96, accent=116)

    # bar 58 -- accel / crescendo roll into the last downbeat
    b = 232.0
    hit(b, KICK, 114)
    for i in range(8):
        hit(b + i * 0.25, SNARE, 94 + i * 2)
    for i in range(16):
        hit(b + 2.0 + i * 0.125, SNARE, 104 + i, 0.08, 0.6)

    # bar 59 -- land it: crash + china + bass drum, left ringing
    b = 236.0
    hit(b, CRASH, 127, 4.0, 0.15)
    hit(b, CHINA, 120, 4.0, 0.15)
    hit(b, KICK, 122)


def compose():
    sec_intro()
    sec_statement()
    sec_breakdown()
    sec_build()
    sec_return()
    sec_toms()
    sec_run()
    sec_quiet()
    sec_development()
    sec_doubles()
    sec_climax()
    sec_finale()


# --------------------------------------------------------------------------
# Timing: smooth push/pull of the pulse, plus per-note hand jitter
# --------------------------------------------------------------------------
DRIFT_PTS = [
    (0.0, 0.000), (16.0, -0.004), (32.0, 0.005), (48.0, -0.005),
    (64.0, 0.002), (72.0, 0.009), (80.0, 0.015), (96.0, 0.000),
    (112.0, -0.006), (128.0, 0.007), (144.0, 0.003), (152.0, -0.008),
    (160.0, 0.004), (176.0, 0.012), (192.0, 0.017), (208.0, 0.011),
    (224.0, 0.020), (233.0, 0.027), (236.0, 0.008), (240.0, 0.000),
]


def make_drift(points):
    def f(t):
        if t <= points[0][0]:
            return points[0][1]
        if t >= points[-1][0]:
            return points[-1][1]
        for i in range(1, len(points)):
            if t <= points[i][0]:
                t0, v0 = points[i - 1]
                t1, v1 = points[i]
                u = (t - t0) / (t1 - t0)
                return v0 + (v1 - v0) * u
        return points[-1][1]
    return f


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def render(path='solo.mid'):
    rng = random.Random(0xD00D)
    drift = make_drift(DRIFT_PTS)

    raw = []
    for beat, note, vel, dur, hj in EVENTS:
        # slow pulse drift + a gentle wobble
        offset = (drift(beat)
                  + 0.005 * math.sin(2.0 * math.pi * beat / 27.0 + 0.9))
        # loose hands
        jit = rng.gauss(0.0, 0.007 * hj)
        jit = max(-0.022, min(0.022, jit))

        t = beat + offset + jit
        tick = int(round(max(0.0, t) * TPB))

        v = int(round(vel + rng.gauss(0.0, 3.5 * hj)))
        v = max(1, min(127, v))

        off = tick + max(1, int(round(dur * TPB)))
        raw.append((tick, 1, note, v))       # note on
        raw.append((off, 0, note, 0))        # note off

    raw.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = MidiFile(ticks_per_beat=TPB)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('set_tempo', tempo=bpm2tempo(TEMPO), time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             time=0))
    track.append(Message('program_change', channel=CHANNEL, program=0, time=0))

    last = 0
    for tick, kind, note, vel in raw:
        delta = tick - last
        if delta < 0:
            delta = 0
        last = tick
        if kind:
            track.append(Message('note_on', channel=CHANNEL, note=note,
                                 velocity=vel, time=delta))
        else:
            track.append(Message('note_off', channel=CHANNEL, note=note,
                                 velocity=0, time=delta))

    track.append(MetaMessage('end_of_track', time=TPB * 2))
    mid.save(path)


if __name__ == '__main__':
    compose()
    render('solo.mid')
