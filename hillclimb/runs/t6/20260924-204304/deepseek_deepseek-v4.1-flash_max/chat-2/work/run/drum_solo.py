#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid -- a two minute General MIDI drum solo on MIDI channel 10
(GM percussion), using mido only.  Deterministic: running this script in an
empty directory always produces exactly the same file.

The solo is composed, not looped:

  * a motif (hi-hat ostinato + backbeat snare + syncopated bass drum) is
    stated, moved onto the toms, broken down into half time, and brought
    back twice with more weight each time,
  * long single stroke runs travel around the kit, rolls swell and resolve,
    fills carry into the next downbeat,
  * phrases push and pull against the grid, off beats sit slightly back,
    and ghost notes answer the accents,
  * at most two hands and two feet strike at any instant,
  * the solo lands on a final flammed crash instead of fading out.
"""

import math
import random

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

# --------------------------------------------------------------- constants
PPQ = 960
CHAN = 9                             # MIDI channel 10, zero based

# General MIDI percussion note numbers used by the kit
BD, BD2 = 36, 35                     # bass drum / acoustic bass drum
SD, STICK = 38, 37                   # snare / side stick
HH, PHH, OHH = 42, 44, 46            # closed / pedal / open hi-hat
RIDE, BELL = 51, 53                  # ride cymbal / ride bell
CRASH, CRASH2 = 49, 57               # crash cymbals
SPLASH, CHINA = 55, 52               # extra cymbals (colour)
T_HI, T_HIMID, T_LOMID, T_LOW = 50, 48, 47, 45
F_HI, F_LOW = 43, 41
TAMB, COWBELL, CLAVES = 54, 56, 75   # colour percussion
WB_HI, WB_LO = 76, 77

FOOT = (BD, BD2, PHH)                # struck with a foot

# how long each instrument is allowed to ring (in beats)
DUR = {
    CRASH: 3.5, CRASH2: 3.0, CHINA: 3.0, SPLASH: 1.5,
    RIDE: 1.5, BELL: 1.0,
    HH: 0.2, OHH: 1.0, PHH: 0.2,
    SD: 0.14, STICK: 0.10, BD: 0.16, BD2: 0.16,
    T_HI: 0.50, T_HIMID: 0.55, T_LOMID: 0.60, T_LOW: 0.65,
    F_HI: 0.75, F_LOW: 0.85,
    TAMB: 0.22, COWBELL: 0.30, CLAVES: 0.15, WB_HI: 0.15, WB_LO: 0.15,
}

EVENTS = []                          # (beat, note, velocity, duration)
RNG = random.Random(0x5EEDD00D)      # fixed seed -> identical output


# ---------------------------------------------------------------- sitting
def add(beat, note, vel, dur=None):
    """Add one stroke at `beat` (floating point beats from the start)."""
    if dur is None:
        dur = DUR.get(note, 0.2)
    v = int(round(vel))
    v = 1 if v < 1 else (127 if v > 127 else v)
    EVENTS.append([float(beat), int(note), v, float(dur)])


def eight(t0, inst, accent=78, off=60, n=8, skip=()):
    """n eighth notes, accented every other one, with a human touch."""
    for i in range(n):
        if i in skip:
            continue
        v = (accent if i % 2 == 0 else off) + RNG.choice((-3, -1, 1, 2))
        add(t0 + 0.5 * i, inst, v)


def sixteenth(t0, inst, accent=82, mid=64, off=54, n=16, skip=()):
    """n sixteenth notes."""
    for i in range(n):
        if i in skip:
            continue
        if i % 4 == 0:
            v = accent
        elif i % 2 == 0:
            v = mid
        else:
            v = off
        v += RNG.choice((-3, -2, 1, 2))
        add(t0 + 0.25 * i, inst, v)


def roll(t0, seq, v0=80, v1=104, step=0.25, accent_every=4, accent_add=16):
    """A run of single strokes, crescendoing, accented on the beat."""
    n = len(seq)
    for i, note in enumerate(seq):
        f = i / float(n - 1) if n > 1 else 0.0
        v = v0 + (v1 - v0) * f
        if accent_every and i % accent_every == 0:
            v += accent_add
        add(t0 + step * i, note, v)


def buzz(t0, note, count, step, v0, v1, accent_every=0, accent_add=0):
    """Evenly spaced strokes (rolls / buzzes) with a velocity ramp."""
    for i in range(count):
        f = i / float(count - 1) if count > 1 else 0.0
        v = v0 + (v1 - v0) * f
        if accent_every and i % accent_every == 0:
            v += accent_add
        add(t0 + step * i, note, v)


# =========================================================== 1. the music
def intro():
    """Bars 0-7: the idea is stated, bare, then answered on the toms."""
    # --- bar 0 : call
    add(0.00, CRASH, 108); add(0.00, BD, 102)
    add(1.00, BELL, 82);   add(1.50, BELL, 70)
    add(2.00, SD, 92)
    add(2.50, BELL, 74);   add(3.00, BELL, 86)
    add(3.50, SD, 34);     add(3.75, BD, 80)
    # --- bar 1 : answer on the toms
    add(4.00, SD, 100)
    add(4.50, SD, 30)
    add(5.00, BD, 88)
    add(5.50, SD, 28)
    add(6.00, SD, 94)
    add(6.50, T_HIMID, 78); add(6.75, T_LOMID, 82)
    add(7.00, T_LOW, 88);   add(7.25, F_HI, 84)
    add(7.50, F_LOW, 90);   add(7.75, F_LOW, 96)

    # --- bar 2 : the call again, altered
    add(8.00, CRASH, 102); add(8.00, BD, 100)
    add(9.00, BELL, 84);   add(9.50, BELL, 72)
    add(10.00, SD, 96);    add(10.00, BD, 70)
    add(10.50, BELL, 76);  add(11.00, BELL, 88)
    add(11.25, SD, 30);    add(11.50, SD, 38); add(11.75, BD, 84)
    # --- bar 3 : snare talk, tom answer
    add(12.00, SD, 102);   add(12.00, BD, 62)
    add(12.50, SD, 32);    add(12.75, SD, 26)
    add(13.00, BD, 92)
    add(13.50, STICK, 44)
    add(14.00, SD, 98);    add(14.25, SD, 30); add(14.50, SD, 44)
    add(15.00, T_HIMID, 86); add(15.25, T_LOMID, 88)
    add(15.50, T_LOW, 92);   add(15.75, F_HI, 96)

    # --- bars 4-5 : the hi-hat joins and the groove states itself
    add(16.00, CRASH, 96); add(16.00, BD, 98)
    add(16.50, HH, 58)
    add(17.00, HH, 76); add(17.00, SD, 94)
    add(17.50, HH, 60)
    add(18.00, HH, 74); add(18.00, BD, 90)
    add(18.50, HH, 58); add(18.75, BD, 78)
    add(19.00, HH, 76); add(19.00, SD, 98)
    add(19.25, SD, 30); add(19.50, HH, 62)
    add(19.75, SD, 36); add(19.75, BD, 82)

    add(20.00, HH, 76); add(20.00, BD, 96)
    add(20.50, HH, 58)
    add(21.00, HH, 74); add(21.00, SD, 92)
    add(21.50, HH, 60)
    add(22.00, T_HI, 88); add(22.00, BD, 86)
    add(22.25, T_HIMID, 84); add(22.50, T_LOMID, 86); add(22.75, T_LOW, 90)
    add(23.00, F_HI, 92);    add(23.25, F_LOW, 94)
    add(23.50, SD, 98)
    add(23.75, SD, 42); add(23.75, BD, 84)

    # --- bars 6-7 : tighten and crescendo into the theme
    add(24.00, CRASH, 92); add(24.00, BD, 100)
    add(24.50, HH, 58)
    add(25.00, HH, 76); add(25.00, SD, 94)
    add(25.50, HH, 60)
    add(26.00, HH, 76); add(26.00, BD, 94)
    add(26.50, HH, 60); add(26.75, BD, 72)
    add(27.00, HH, 78); add(27.00, SD, 100)
    add(27.50, HH, 62); add(27.50, BD, 80)
    add(27.75, SD, 38)

    add(28.00, HH, 74); add(28.00, BD, 98)
    add(28.50, HH, 56)
    add(29.00, HH, 72); add(29.00, SD, 96)
    add(29.50, HH, 58); add(29.50, BD, 78)
    buzz(30.00, SD, 8, 0.25, 60, 99)              # crescendo into bar 8


def statement():
    """Bars 8-15: the main motif, four two-bar phrases, each one different."""
    # --- bar 8 : statement
    t = 32.0
    add(t, CRASH, 104); add(t, BD, 100)
    eight(t, HH, 78, 60)
    add(t + 1.0, SD, 96)
    add(t + 1.5, BD, 86)
    add(t + 2.5, BD, 90)
    add(t + 3.0, SD, 98)
    add(t + 3.75, SD, 34); add(t + 3.75, BD, 80)

    # --- bar 9 : pickup on the toms
    t = 36.0
    add(t, BD, 102)
    eight(t, HH, 78, 60, n=7)
    add(t + 1.0, SD, 96)
    add(t + 1.5, BD, 84)
    add(t + 2.5, BD, 92)
    add(t + 2.75, SD, 30)
    add(t + 3.0, SD, 98)
    add(t + 3.25, T_HI, 86)
    add(t + 3.50, T_HIMID, 88)
    add(t + 3.75, T_LOMID, 94)

    # --- bar 10 : ghost notes and a busier foot
    t = 40.0
    add(t, CRASH2, 100); add(t, BD, 102)
    eight(t, HH, 78, 60)
    add(t + 0.75, SD, 30)
    add(t + 1.0, SD, 96)
    add(t + 1.5, BD, 76)
    add(t + 1.75, SD, 32)
    add(t + 2.0, BD, 88)
    add(t + 2.75, SD, 28)
    add(t + 3.0, SD, 100)
    add(t + 3.5, BD, 84)
    add(t + 3.75, SD, 36)

    # --- bar 11 : the hat opens on the "and" of 4
    t = 44.0
    add(t, BD, 102)
    eight(t, HH, 78, 60, n=6)
    add(t + 1.0, SD, 96)
    add(t + 1.5, BD, 88)
    add(t + 2.5, BD, 92)
    add(t + 2.75, SD, 30)
    add(t + 3.0, SD, 98)
    add(t + 3.5, OHH, 84)
    add(t + 3.75, SD, 34); add(t + 3.75, BD, 82)

    # --- bars 12-13 : same motif, more weight, answering toms
    t = 48.0
    add(t, CRASH, 106); add(t, BD, 104)
    eight(t, HH, 80, 62)
    add(t + 1.0, SD, 100)
    add(t + 1.5, BD, 90)
    add(t + 2.0, BD, 72)
    add(t + 2.5, BD, 94)
    add(t + 3.0, SD, 102)
    add(t + 3.25, SD, 32)
    add(t + 3.5, BD, 86)
    add(t + 3.75, SD, 38)

    t = 52.0
    add(t, BD, 104)
    eight(t, HH, 80, 62, n=7)
    add(t + 1.0, SD, 100)
    add(t + 1.5, BD, 92)
    add(t + 2.25, SD, 30)
    add(t + 2.5, BD, 96)
    add(t + 3.0, SD, 104)
    add(t + 3.25, T_LOW, 88)
    add(t + 3.50, F_HI, 92)
    add(t + 3.75, F_LOW, 98)

    # --- bar 14 : sixteenths on the hat, building
    t = 56.0
    add(t, CRASH2, 96); add(t, BD, 106)
    sixteenth(t, HH, 70, 58, 50)
    add(t + 1.0, SD, 100)
    add(t + 1.5, BD, 92)
    add(t + 2.5, BD, 96)
    add(t + 3.0, SD, 104)
    add(t + 3.5, SD, 40)

    # --- bar 15 : fill down the toms and back to the snare
    t = 60.0
    seq = [SD, SD, SD, SD,
           SD, SD, SD, SD,
           T_HI, T_HIMID, T_LOMID, T_LOW,
           F_HI, F_LOW, T_LOW, SD]
    roll(t, seq, 74, 104, accent_every=4, accent_add=14)


def development():
    """Bars 16-23: the motif moved onto the toms, then half time, then back."""
    # --- bars 16-17 : the motif sung on the toms
    t = 64.0
    add(t, CRASH, 106); add(t, BD, 104)
    add(t + 0.50, T_HI, 82)
    add(t + 1.00, T_HIMID, 92); add(t + 1.00, BD, 82)
    add(t + 1.50, T_LOMID, 84)
    add(t + 2.00, SD, 102)
    add(t + 2.50, T_LOW, 84); add(t + 2.50, BD, 94)
    add(t + 3.00, F_HI, 90)
    add(t + 3.50, F_LOW, 92); add(t + 3.50, BD, 78)
    add(t + 3.75, SD, 38)

    t = 68.0
    add(t, BD, 104)
    add(t + 0.50, F_LOW, 86)
    add(t + 1.00, SD, 104)
    add(t + 1.50, T_LOW, 84); add(t + 1.50, BD, 90)
    add(t + 2.00, F_HI, 92)
    add(t + 2.50, SD, 100); add(t + 2.50, BD, 82)
    add(t + 3.00, T_HIMID, 88)
    add(t + 3.25, T_LOMID, 90)
    add(t + 3.50, T_LOW, 92)
    add(t + 3.75, F_HI, 96)

    # --- bars 18-19 : half time, quiet, space, a little colour
    t = 72.0
    add(t, BD, 96)
    eight(t, HH, 64, 52, n=4)
    add(t + 1.0, SD, 42)
    add(t + 2.0, SD, 104); add(t + 2.0, BD, 84); add(t + 2.0, TAMB, 62)
    add(t + 2.5, HH, 56)
    add(t + 3.0, SD, 36)
    add(t + 3.25, HH, 54)
    add(t + 3.5, OHH, 78)

    t = 76.0
    add(t, BD, 98)
    eight(t, HH, 66, 54, n=2)
    add(t + 1.0, HH, 58); add(t + 1.0, SD, 44)
    add(t + 2.0, SD, 106); add(t + 2.0, BD, 88); add(t + 2.0, TAMB, 64)
    add(t + 2.5, SD, 38)
    add(t + 3.0, T_HIMID, 88)
    add(t + 3.25, T_LOMID, 90)
    add(t + 3.50, F_HI, 94)
    add(t + 3.75, F_LOW, 98)

    # --- bars 20-21 : the motif returns, denser
    t = 80.0
    add(t, CRASH2, 102); add(t, BD, 106)
    eight(t, HH, 80, 62)
    add(t + 1.0, SD, 102)
    add(t + 1.5, BD, 92)
    add(t + 2.0, BD, 76)
    add(t + 2.5, BD, 94)
    add(t + 3.0, SD, 104)
    add(t + 3.25, SD, 32)
    add(t + 3.75, SD, 40); add(t + 3.75, BD, 88)

    t = 84.0
    add(t, BD, 106)
    eight(t, HH, 80, 64, n=7)
    add(t + 1.0, SD, 102)
    add(t + 1.5, BD, 96)
    add(t + 2.0, BD, 78)
    add(t + 2.25, SD, 32)
    add(t + 2.5, BD, 98)
    add(t + 3.0, SD, 106)
    add(t + 3.25, T_HI, 92)
    add(t + 3.50, T_HIMID, 96)
    add(t + 3.75, T_LOMID, 100)

    # --- bar 22 : driving, open hat
    t = 88.0
    add(t, CRASH, 106); add(t, BD, 108)
    eight(t, HH, 82, 64, n=7)
    add(t + 1.0, SD, 104)
    add(t + 1.5, BD, 96)
    add(t + 2.0, BD, 80)
    add(t + 2.5, BD, 98)
    add(t + 3.0, SD, 106)
    add(t + 3.25, SD, 34)
    add(t + 3.50, OHH, 88)
    add(t + 3.75, SD, 42)

    # --- bar 23 : fill into the first peak
    t = 92.0
    add(t, BD, 108)
    seq = [SD, SD, T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOMID,
           T_LOW, T_LOW, F_HI, F_HI, F_LOW, F_LOW, T_LOW, SD]
    roll(t, seq, 80, 108, accent_every=4, accent_add=14)
    add(t + 2.0, BD, 96)


def build_to_peak():
    """Bars 24-31: driving groove, toms, then a long crescendo."""
    # --- bar 24
    t = 96.0
    add(t, CRASH, 112); add(t, BD, 110)
    eight(t, HH, 84, 64)
    add(t + 0.75, BD, 86)
    add(t + 1.0, SD, 106)
    add(t + 1.5, BD, 98)
    add(t + 1.75, SD, 36)
    add(t + 2.0, BD, 88)
    add(t + 2.5, SD, 46)
    add(t + 3.0, SD, 108)
    add(t + 3.25, SD, 34)
    add(t + 3.5, BD, 94)
    add(t + 3.75, SD, 42)

    # --- bar 25
    t = 100.0
    add(t, BD, 110)
    eight(t, HH, 84, 64)
    add(t + 0.75, SD, 34)
    add(t + 1.0, SD, 106)
    add(t + 1.5, BD, 100)
    add(t + 1.75, BD, 76)
    add(t + 2.0, SD, 46)
    add(t + 2.5, BD, 94)
    add(t + 3.0, SD, 108)
    add(t + 3.5, SD, 40)
    add(t + 3.75, SD, 46); add(t + 3.75, BD, 92)

    # --- bar 26 : sixteenths on the hat
    t = 104.0
    add(t, CRASH2, 104); add(t, BD, 112)
    sixteenth(t, HH, 80, 66, 56)
    add(t + 1.0, SD, 108)
    add(t + 1.75, BD, 88)
    add(t + 2.0, BD, 92)
    add(t + 2.75, SD, 38)
    add(t + 3.0, SD, 110)
    add(t + 3.25, SD, 36)
    add(t + 3.5, BD, 96)
    add(t + 3.75, SD, 44)

    # --- bar 27 : sixteenths, then toms
    t = 108.0
    add(t, BD, 112)
    sixteenth(t, HH, 80, 66, 56, n=8)
    add(t + 1.0, SD, 108)
    add(t + 1.5, BD, 96)
    add(t + 2.0, SD, 48)
    add(t + 2.5, BD, 100)
    add(t + 2.75, SD, 34)
    add(t + 3.0, SD, 110)
    add(t + 3.25, T_HI, 94)
    add(t + 3.50, T_HIMID, 98)
    add(t + 3.75, T_LOMID, 102)

    # --- bars 28-29 : the motif in tom colours
    t = 112.0
    add(t, CRASH, 110); add(t, BD, 110)
    add(t + 0.50, T_HI, 84)
    add(t + 1.00, T_HIMID, 96); add(t + 1.00, BD, 88)
    add(t + 1.50, T_HIMID, 80)
    add(t + 2.00, T_LOMID, 98)
    add(t + 2.50, T_LOW, 84); add(t + 2.50, BD, 96)
    add(t + 3.00, F_HI, 100)
    add(t + 3.50, F_LOW, 86)
    add(t + 3.75, F_LOW, 98); add(t + 3.75, BD, 90)

    t = 116.0
    add(t, BD, 112)
    add(t + 0.50, F_LOW, 88)
    add(t + 1.00, F_HI, 96); add(t + 1.00, BD, 92)
    add(t + 1.50, T_LOW, 84)
    add(t + 2.00, T_LOMID, 98)
    add(t + 2.50, T_HIMID, 86); add(t + 2.50, BD, 98)
    add(t + 3.00, SD, 108)
    add(t + 3.25, SD, 40)
    add(t + 3.50, T_HI, 96)
    add(t + 3.75, T_HIMID, 100)

    # --- bar 30 : single strokes around the kit
    t = 120.0
    add(t, CRASH2, 106); add(t, BD, 112)
    seq = [SD, SD, T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOMID,
           T_LOW, T_LOW, F_HI, F_HI, F_LOW, F_LOW, F_LOW, T_LOW]
    roll(t, seq, 86, 108, accent_every=4, accent_add=14)
    add(t + 2.0, BD, 100)
    add(t + 3.0, BD, 104)

    # --- bar 31 : roll that swells into the peak
    t = 124.0
    add(t, BD, 112)
    buzz(t, SD, 8, 0.25, 88, 102)                 # beats 1-2, sixteenths
    buzz(t + 2.0, SD, 16, 0.125, 104, 124)        # beats 3-4, thirtyseconds
    add(t + 2.0, BD, 106)


def peak_one():
    """Bars 32-37: the first real peak, fast and relentless."""
    # --- bar 32 : ride pattern, comping
    t = 128.0
    add(t, CRASH, 114); add(t, BD, 112)
    eight(t, RIDE, 92, 74)
    add(t + 1.0, SD, 110)
    add(t + 1.5, BD, 100)
    add(t + 2.5, BD, 98)
    add(t + 3.0, SD, 112)
    add(t + 3.25, SD, 36)
    add(t + 3.5, BD, 96)
    add(t + 3.75, SD, 44)

    # --- bar 33 : same shape, bell accents
    t = 132.0
    add(t, BD, 112)
    eight(t, RIDE, 92, 76, skip=(2, 5))
    add(t + 1.0, BELL, 100); add(t + 1.0, SD, 110)
    add(t + 1.5, BD, 102)
    add(t + 2.0, SD, 50)
    add(t + 2.5, BELL, 96)
    add(t + 3.0, SD, 112)
    add(t + 3.5, BD, 100)
    add(t + 3.75, SD, 40)

    # --- bars 34-35 : single strokes travelling down and back up
    t = 136.0
    add(t, CRASH2, 108); add(t, BD, 112)
    seq = [SD, SD, SD, SD, SD, SD, SD, SD,
           T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOMID, T_LOW, T_LOW]
    roll(t, seq, 88, 104, accent_every=4, accent_add=14)
    add(t + 2.0, BD, 104)

    t = 140.0
    add(t, BD, 112)
    seq = [F_HI, F_HI, F_LOW, F_LOW, T_LOW, T_LOW, T_LOMID, T_LOMID,
           SD, SD, SD, SD, SD, SD, SD, SD]
    roll(t, seq, 88, 106, accent_every=4, accent_add=14)
    add(t + 2.0, BD, 106)
    add(t + 3.0, BD, 108)

    # --- bar 36 : the bottom drops out, big unison hits
    t = 144.0
    add(t, CRASH, 114); add(t, SD, 110); add(t, BD, 114)
    add(t + 1.0, SD, 102); add(t + 1.0, BD, 100)
    add(t + 1.5, SD, 46)
    add(t + 2.0, CRASH2, 100); add(t + 2.0, SD, 108); add(t + 2.0, BD, 106)
    add(t + 3.0, SD, 104); add(t + 3.0, BD, 104)
    add(t + 3.5, SD, 50); add(t + 3.75, SD, 54)

    # --- bar 37 : long roll, swelling into the break
    t = 148.0
    add(t, BD, 110)
    buzz(t, SD, 4, 0.25, 76, 84)
    buzz(t + 1.0, SD, 4, 0.25, 86, 94)
    buzz(t + 2.0, SD, 8, 0.125, 96, 104)
    buzz(t + 3.0, SD, 8, 0.125, 106, 118)
    add(t + 2.0, BD, 106)


def breakdown():
    """Bars 38-43: the stop, the space, and the quiet rebuild."""
    # --- bar 38 : everything, then air
    t = 152.0
    add(t, CRASH, 120); add(t, BD, 118); add(t, SD, 104)
    add(t + 2.5, SD, 44)
    add(t + 3.0, CLAVES, 62)
    add(t + 3.5, STICK, 54)

    # --- bars 39-40 : quiet half time with a little space
    t = 156.0
    add(t, BD, 88)
    eight(t, HH, 56, 46, skip=(7,))
    add(t + 1.0, SD, 46)
    add(t + 2.0, SD, 94); add(t + 2.0, BD, 76)
    add(t + 3.0, SD, 42)
    add(t + 3.5, OHH, 60)

    t = 160.0
    add(t, BD, 92)
    eight(t, HH, 58, 48)
    add(t + 1.0, SD, 48)
    add(t + 1.5, BD, 74)
    add(t + 2.0, SD, 96); add(t + 2.0, BD, 80)
    add(t + 2.5, SD, 36)
    add(t + 3.0, SD, 52)
    add(t + 3.25, T_LOMID, 72)
    add(t + 3.50, T_LOW, 78)
    add(t + 3.75, F_HI, 84)

    # --- bar 41 : the foot lays down quarter notes
    t = 164.0
    for i in range(4):
        add(t + i, BD, 86 + 2 * i)
    eight(t, HH, 60, 50)
    add(t + 1.0, SD, 50)
    add(t + 2.5, SD, 40)
    add(t + 3.0, SD, 54)

    # --- bar 42 : it fills back in
    t = 168.0
    add(t, BD, 94)
    eight(t, HH, 64, 52)
    add(t + 1.0, SD, 88)
    add(t + 1.5, BD, 82)
    add(t + 2.0, BD, 96)
    add(t + 2.5, SD, 44)
    add(t + 3.0, SD, 94)
    add(t + 3.5, BD, 86)
    add(t + 3.75, SD, 46)

    # --- bar 43 : smooth fill around the kit into the lyrical part
    t = 172.0
    add(t, BD, 96)
    seq = [T_HI, T_HIMID, T_LOMID, T_LOW,
           F_HI, F_LOW, T_LOW, T_LOMID,
           T_HIMID, T_HI, SD, SD, SD, SD, SD, SD]
    roll(t, seq, 76, 96, accent_every=0)
    add(t + 2.0, BD, 92)


def lyrical():
    """Bars 44-47: space, half time, the solo breathes before the last push."""
    # --- bar 44
    t = 176.0
    add(t, CRASH, 100); add(t, BD, 98)
    add(t + 0.50, PHH, 56)
    add(t + 1.00, SD, 90)
    add(t + 1.50, T_LOW, 76)
    add(t + 2.00, BD, 86)
    add(t + 2.50, T_LOMID, 80)
    add(t + 3.00, SD, 94); add(t + 3.00, BD, 72)
    add(t + 3.50, F_HI, 82)
    add(t + 3.75, F_LOW, 88)

    # --- bar 45
    t = 180.0
    add(t, BD, 100)
    add(t + 1.00, T_HI, 84)
    add(t + 1.50, T_HIMID, 86)
    add(t + 2.00, SD, 102); add(t + 2.00, BD, 82)
    add(t + 2.50, SD, 38)
    add(t + 3.00, T_LOW, 88)
    add(t + 3.50, F_LOW, 92)
    add(t + 3.75, F_LOW, 58)

    # --- bar 46
    t = 184.0
    add(t, BD, 100)
    eight(t, HH, 60, 50, n=6)
    add(t + 1.0, SD, 96)
    add(t + 2.0, T_HI, 88); add(t + 2.0, BD, 90)
    add(t + 2.25, T_HIMID, 86)
    add(t + 2.50, T_LOMID, 88)
    add(t + 2.75, T_LOW, 90)
    add(t + 3.00, F_HI, 92)
    add(t + 3.25, F_LOW, 94)
    add(t + 3.50, SD, 98)
    add(t + 3.75, SD, 42); add(t + 3.75, BD, 86)

    # --- bar 47 : roll that grows into the rebuild
    t = 188.0
    add(t, BD, 92)
    buzz(t, SD, 16, 0.25, 72, 108)
    add(t + 2.0, BD, 96)


def rebuild():
    """Bars 48-55: the motif comes home and the bandwagon starts rolling."""
    # --- bar 48 : motif, straight, with a crash
    t = 192.0
    add(t, CRASH, 108); add(t, BD, 106)
    eight(t, HH, 80, 62)
    add(t + 1.0, SD, 104)
    add(t + 1.5, BD, 92)
    add(t + 2.0, BD, 78)
    add(t + 2.5, BD, 96)
    add(t + 3.0, SD, 106)
    add(t + 3.25, SD, 34)
    add(t + 3.75, SD, 40); add(t + 3.75, BD, 90)

    # --- bar 49 : sixteenths appear on the hat
    t = 196.0
    add(t, BD, 106)
    eight(t, HH, 80, 62, n=4)
    add(t + 1.0, SD, 104)
    add(t + 1.5, BD, 94)
    add(t + 2.0, BD, 78)
    sixteenth(t + 2.0, HH, 72, 60, 52, n=6)
    add(t + 2.5, SD, 32)
    add(t + 3.0, SD, 106)
    add(t + 3.5, OHH, 88)
    add(t + 3.75, SD, 42); add(t + 3.75, BD, 92)

    # --- bar 50 : toms take the motif
    t = 200.0
    add(t, CRASH2, 106); add(t, BD, 108)
    add(t + 0.50, T_HI, 86)
    add(t + 1.00, T_HIMID, 98); add(t + 1.00, BD, 90)
    add(t + 1.50, T_LOMID, 88)
    add(t + 2.00, T_LOW, 100)
    add(t + 2.50, F_HI, 90); add(t + 2.50, BD, 98)
    add(t + 3.00, F_LOW, 102)
    add(t + 3.25, F_LOW, 62)
    add(t + 3.50, F_HI, 92)
    add(t + 3.75, T_LOW, 96)

    # --- bar 51 : snare talk into a tom run
    t = 204.0
    add(t, SD, 108); add(t, BD, 110)
    add(t + 0.50, SD, 58)
    add(t + 1.00, SD, 64); add(t + 1.00, BD, 90)
    add(t + 1.25, SD, 66)
    add(t + 1.50, SD, 70)
    add(t + 1.75, SD, 74)
    add(t + 2.00, T_HI, 94); add(t + 2.00, BD, 98)
    add(t + 2.25, T_HIMID, 92)
    add(t + 2.50, T_LOMID, 94)
    add(t + 2.75, T_LOW, 96)
    add(t + 3.00, F_HI, 98)
    add(t + 3.25, F_LOW, 100)
    add(t + 3.50, SD, 106)
    add(t + 3.75, SD, 46); add(t + 3.75, BD, 94)

    # --- bars 52-53 : driving groove
    t = 208.0
    add(t, CRASH, 114); add(t, BD, 112)
    eight(t, HH, 84, 64)
    add(t + 0.75, BD, 88)
    add(t + 1.0, SD, 108)
    add(t + 1.5, BD, 100)
    add(t + 2.0, BD, 90)
    add(t + 2.5, SD, 48)
    add(t + 3.0, SD, 110)
    add(t + 3.25, SD, 36)
    add(t + 3.5, BD, 96)
    add(t + 3.75, SD, 44)

    t = 212.0
    add(t, BD, 112)
    eight(t, HH, 84, 66)
    add(t + 0.75, SD, 34)
    add(t + 1.0, SD, 108)
    add(t + 1.5, BD, 102)
    add(t + 2.0, SD, 48)
    add(t + 2.5, BD, 98)
    add(t + 3.0, SD, 110)
    add(t + 3.5, SD, 52)
    add(t + 3.75, SD, 46); add(t + 3.75, BD, 98)

    # --- bar 54 : sixteenths, wide open
    t = 216.0
    add(t, CRASH2, 110); add(t, BD, 114)
    sixteenth(t, HH, 84, 66, 56)
    add(t + 1.0, SD, 110)
    add(t + 1.75, BD, 92)
    add(t + 2.0, BD, 96)
    add(t + 2.5, SD, 46)
    add(t + 3.0, SD, 112)
    add(t + 3.25, SD, 36)
    add(t + 3.5, BD, 100)
    add(t + 3.75, SD, 48)

    # --- bar 55 : cowbell for colour, then the last push
    t = 220.0
    add(t, BD, 112)
    eight(t, COWBELL, 88, 68, skip=(7,))
    add(t + 1.0, SD, 110)
    add(t + 1.5, BD, 100)
    add(t + 2.5, BD, 104); add(t + 2.5, SD, 50)
    add(t + 3.0, SD, 112)
    add(t + 3.5, OHH, 92)
    add(t + 3.75, SD, 50); add(t + 3.75, BD, 104)


def peak_two():
    """Bars 56-59: the second peak, wider and louder than the first."""
    # --- bar 56 : ride, comping, crashing
    t = 224.0
    add(t, CRASH, 116); add(t, BD, 114)
    eight(t, RIDE, 96, 78)
    add(t + 1.0, SD, 112)
    add(t + 1.5, BD, 104)
    add(t + 2.5, SD, 54)
    add(t + 3.0, SD, 114)
    add(t + 3.25, SD, 38)
    add(t + 3.5, BD, 100)
    add(t + 3.75, SD, 46)

    # --- bar 57 : bell accents
    t = 228.0
    add(t, BD, 114)
    eight(t, RIDE, 96, 78, skip=(2, 5))
    add(t + 1.0, BELL, 104); add(t + 1.0, SD, 112)
    add(t + 1.5, BD, 104)
    add(t + 2.5, BELL, 100); add(t + 2.5, SD, 52)
    add(t + 3.0, SD, 114)
    add(t + 3.5, BD, 102)
    add(t + 3.75, SD, 44)

    # --- bar 58 : singles all the way down the kit
    t = 232.0
    add(t, CRASH2, 112); add(t, BD, 116)
    seq = [T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOMID, T_LOW, T_LOW,
           F_HI, F_HI, F_LOW, F_LOW, T_LOW, T_LOMID, T_HIMID, SD]
    roll(t, seq, 92, 108, accent_every=4, accent_add=16)
    add(t + 2.0, BD, 104)

    # --- bar 59 : snare, then up the toms
    t = 236.0
    add(t, BD, 116)
    seq = [SD, SD, SD, SD, SD, SD, SD, SD,
           SD, SD, T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOW]
    roll(t, seq, 92, 110, accent_every=4, accent_add=16)
    add(t + 2.0, BD, 110)


def finale():
    """Bars 60-63: the last build and the hit that lands it."""
    # --- bar 60 : roll with accents, rising
    t = 240.0
    add(t, BD, 112)
    roll(t, [SD] * 16, 78, 100, accent_every=4, accent_add=14)
    add(t + 2.0, BD, 108)

    # --- bar 61 : around the kit
    t = 244.0
    add(t, BD, 114)
    seq = [T_HI, T_HI, T_HIMID, T_HIMID, T_LOMID, T_LOMID, T_LOW, T_LOW,
           F_HI, F_HI, F_LOW, F_LOW, F_LOW, F_HI, T_LOW, SD]
    roll(t, seq, 92, 110, accent_every=4, accent_add=16)
    add(t + 2.0, BD, 110)

    # --- bar 62 : everything, fortissimo
    t = 248.0
    add(t, CRASH, 118); add(t, BD, 118)
    seq = [SD, SD, T_HI, T_HIMID, SD, SD, T_LOMID, T_LOW,
           SD, SD, F_HI, F_LOW, T_LOW, T_LOMID, T_HIMID, SD]
    roll(t, seq, 96, 114, accent_every=4, accent_add=12)
    add(t + 2.0, BD, 112)

    # --- bar 63 : sixteenths, then a roll that runs into the last hit
    t = 252.0
    roll(t, [T_HI, T_HIMID, T_LOMID, T_LOW, F_HI, F_LOW, T_LOW, SD],
         96, 112)
    add(t + 2.0, BD, 112)
    buzz(t + 2.0, SD, 16, 0.125, 100, 122)

    # --- the last hit: flam on the snare, crash and bass drum together
    add(256.0 - 0.045, SD, 116)
    add(256.0, CRASH, 125)
    add(256.0, BD, 122)


def build_score():
    intro()
    statement()
    development()
    build_to_peak()
    peak_one()
    breakdown()
    lyrical()
    rebuild()
    peak_two()
    finale()


# ==================================================== tempo and human timing
# (beat, bpm) control points -- linearly interpolated and sampled for the
# MIDI tempo map.
TEMPO = [(0.0, 100.0), (32.0, 108.0), (64.0, 116.0), (96.0, 126.0),
         (120.0, 138.0), (128.0, 146.0), (152.0, 146.0), (160.0, 132.0),
         (176.0, 108.0), (192.0, 112.0), (208.0, 128.0), (224.0, 142.0),
         (240.0, 136.0), (248.0, 144.0), (256.0, 152.0)]

# (beat, tick offset, tightness): the phrase level push/drag and how much
# the hands are allowed to breathe.  Negative = pushing ahead.
FEEL = [(0.0, 6.0, 0.80), (32.0, -4.0, 0.90), (64.0, 4.0, 0.90),
        (96.0, -5.0, 1.00), (120.0, -8.0, 1.05), (128.0, -9.0, 1.05),
        (152.0, 3.0, 1.00), (160.0, 9.0, 0.75), (176.0, 14.0, 0.70),
        (192.0, 5.0, 0.85), (208.0, -3.0, 0.95), (224.0, -7.0, 1.00),
        (240.0, -12.0, 1.05), (256.0, -2.0, 1.00)]


def _interp(points, beat):
    if beat <= points[0][0]:
        return points[0][1:]
    for i in range(1, len(points)):
        b1 = points[i][0]
        if beat <= b1:
            b0 = points[i - 1][0]
            k = (beat - b0) / (b1 - b0) if b1 > b0 else 0.0
            return tuple(points[i - 1][j] + (points[i][j] - points[i - 1][j]) * k
                         for j in range(1, len(points[i])))
    return points[-1][1:]


def bpm_at(beat):
    return _interp(TEMPO, beat)[0]


def total_seconds():
    total = 0.0
    for i in range(len(TEMPO) - 1):
        b0, v0 = TEMPO[i]
        b1, v1 = TEMPO[i + 1]
        total += (b1 - b0) * 60.0 / (0.5 * (v0 + v1))
    return total


def humanize():
    """Turn beats into ticks, bending the grid the way hands do."""
    out = []
    for beat, note, vel, dur in EVENTS:
        push, tight = _interp(FEEL, beat)
        frac = beat - math.floor(beat)
        if abs(frac - 0.5) < 1e-6:                       # eighth off beats
            sway = 7.0
        elif abs(frac - 0.25) < 1e-6 or abs(frac - 0.75) < 1e-6:
            sway = 4.5                                   # sixteenth off beats
        else:
            sway = 0.0
        sway *= max(0.0, 1.6 - tight)                    # laid back, not loose
        amp = max(2.5, 16.0 - 12.0 * tight)              # random slop
        jitter = RNG.uniform(-amp, amp)
        if note in FOOT:
            jitter *= 0.45                               # feet are steadier
        tick = int(round(beat * PPQ + push + sway + jitter))
        if tick < 0:
            tick = 0
        out.append((tick, note, vel, dur))
    out.sort(key=lambda e: (e[0], e[1]))
    return out


# ============================================================== drummers' arms
HAND_WINDOW = 32          # ticks; two hands cannot be closer than this twice


def enforce_limbs(events, window=HAND_WINDOW):
    """Keep to at most two hands and two feet at any instant.

    Any stroke that would need a third limb is removed (the quietest of the
    offending strokes first), so the result stays playable by one drummer.
    """
    keep = [True] * len(events)
    dropped = 0
    for want_foot in (False, True):
        idxs = [i for i, e in enumerate(events)
                if (e[1] in FOOT) == want_foot]
        idxs.sort(key=lambda i: events[i][0])
        active = []
        for i in idxs:
            t = events[i][0]
            active = [a for a in active if t - events[a][0] < window]
            active.append(i)
            if len(active) > 2:
                victim = min(active, key=lambda a: events[a][2])
                keep[victim] = False
                active.remove(victim)
                dropped += 1
    return [e for i, e in enumerate(events) if keep[i]], dropped


# ==================================================================== output
def emit(track, msgs):
    """Sort absolute tick messages, write them as delta times."""
    msgs.sort(key=lambda m: (m[0], m[1]))
    prev = 0
    for tick, _prio, msg in msgs:
        if tick < prev:
            tick = prev
        msg.time = tick - prev
        prev = tick
        track.append(msg)


def write_midi(path, events):
    mid = MidiFile(type=1, ticks_per_beat=PPQ)
    conductor = MidiTrack()
    drums = MidiTrack()
    mid.tracks.append(conductor)
    mid.tracks.append(drums)

    # --- conductor: tempo curve, sampled so it glides instead of stepping
    cond = [(0, 0, MetaMessage('track_name', name='drum solo')),
            (0, 0, MetaMessage('time_signature', numerator=4, denominator=4))]
    b = 0.0
    while b <= 260.0:
        cond.append((int(round(b * PPQ)), 0,
                     MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm_at(b)))))
        b += 0.25
    emit(conductor, cond)

    # --- channel 10 percussion
    msgs = []
    for tick, note, vel, dur in events:
        msgs.append((tick, 2, Message('note_on', channel=CHAN,
                                      note=note, velocity=vel)))
        off = tick + max(1, int(round(dur * PPQ)))
        msgs.append((off, 1, Message('note_off', channel=CHAN,
                                     note=note, velocity=0)))
    emit(drums, msgs)

    mid.save(path)


def main():
    build_score()
    events = humanize()
    events, repairs = enforce_limbs(events)
    write_midi('solo.mid', events)
    secs = total_seconds()
    print('wrote solo.mid : %d strokes, %d:%02d long, %d limb repairs'
          % (len(events), int(secs // 60), int(secs % 60), repairs))


if __name__ == '__main__':
    main()
