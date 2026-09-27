#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid -- a two minute unaccompanied drum solo for General MIDI
percussion (MIDI channel 10).

The performance is composed bar by bar (56 bars of 4/4 at roughly 112 bpm),
humanised in timing and velocity, and performed with two hands and two feet
(max four limbs sounding at once).  Everything is deterministic: the same
file is produced on every run.
"""

import math
import random

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

# ---------------------------------------------------------------------------
# General MIDI percussion map
# ---------------------------------------------------------------------------
KICK = 36        # bass drum 1
KICK2 = 35       # acoustic bass drum
SNARE = 38       # acoustic snare
RIM = 37         # side stick
CLAP = 39
HAT = 42         # closed hi-hat
HAT_PED = 44     # pedal hi-hat
HAT_OPEN = 46
TOM_HF = 43      # high floor tom
TOM_L = 41       # low floor tom
TOM_LOW = 45
TOM_MID = 47
TOM_HIMID = 48
TOM_HIGH = 50
CRASH = 49
CRASH2 = 57
RIDE = 51
BELL = 53
SPLASH = 55
CHINA = 52
TAMB = 54
COWBELL = 56

TPB = 480                 # ticks per beat
CH = 9                    # MIDI channel 10 (zero based)
BARS = 56
BEATS = BARS * 4          # 224 beats
TARGET_SECONDS = 120.0

rng = random.Random(0x5EEDBEEF)

# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------
EV = []                   # [time in beats, note, velocity, hand hint]


def add(t, note, vel, hand=None):
    EV.append([float(t), int(note), int(round(vel)), hand])


def run(t0, seq, step, v0, v1, accent_every=0, accent_vel=112, hands=None):
    """A string of strokes travelling over the kit."""
    n = len(seq)
    for i, drum in enumerate(seq):
        v = v1 if n == 1 else v0 + (v1 - v0) * i / (n - 1)
        if accent_every and i % accent_every == 0:
            v = accent_vel
        add(t0 + step * i, drum, v, hands[i] if hands else None)


def hats8(t0, v_strong=68, v_weak=52, count=8):
    for i in range(count):
        add(t0 + 0.5 * i, HAT, v_strong if i % 2 == 0 else v_weak)


# ---------------------------------------------------------------------------
# The solo
# ---------------------------------------------------------------------------
def compose():
    # ===================== bars 1-4 : INTRO (beats 0-16) ==================
    # The motif: kick, ghost-snare, snare accent, tom, tom, snare, kick.

    # bar 1 -- motif stated quietly
    add(0.00, KICK, 104)
    add(0.50, SNARE, 42)
    add(0.75, SNARE, 112)
    add(1.00, TOM_MID, 92)
    add(1.25, TOM_HIGH, 88)
    add(1.50, SNARE, 72)
    add(1.75, KICK, 78)
    add(2.00, KICK, 100)
    add(2.00, HAT_PED, 60)
    add(2.50, SNARE, 44)
    add(2.75, SNARE, 110)
    add(3.00, TOM_LOW, 92)
    add(3.25, TOM_MID, 88)
    add(3.50, TOM_HIGH, 74)
    add(3.75, KICK, 80)

    # bar 2 -- answered on the upper toms
    add(4.00, KICK, 106)
    add(4.00, HAT_PED, 62)
    add(4.50, SNARE, 46)
    add(4.75, SNARE, 114)
    add(5.00, TOM_HIGH, 94)
    add(5.25, TOM_MID, 90)
    add(5.50, TOM_LOW, 82)
    add(5.75, KICK, 84)
    add(6.00, KICK, 106)
    add(6.00, HAT_PED, 62)
    add(6.50, SNARE, 48)
    add(6.75, SNARE, 116)
    add(7.00, TOM_HIGH, 96)
    add(7.25, TOM_MID, 92)
    add(7.50, SNARE, 88)
    add(7.75, KICK, 90)

    # bar 3 -- straight time enters on the hi-hat
    hats8(8.0, 68, 52)
    add(8.00, KICK, 108)
    add(9.00, SNARE, 104)
    add(9.50, SNARE, 38)
    add(10.00, KICK, 102)
    add(11.00, SNARE, 106)
    add(11.50, SNARE, 40)
    add(11.75, KICK, 84)

    # bar 4 -- single strokes swell into the first downbeat
    add(12.00, KICK, 108)
    for i in range(15):
        drum = SNARE if i < 8 else (TOM_HIGH if i < 12 else TOM_MID)
        add(12.25 + 0.25 * i, drum, 54 + 2.6 * i)
    add(13.00, KICK, 92)
    add(14.00, KICK, 96)
    add(15.50, KICK, 90)

    # ===================== bars 5-8 : development (beats 16-32) ===========
    # bar 5 -- crash, then the motif over a light hi-hat pulse
    add(16.00, KICK, 112)
    add(16.00, CRASH, 106)
    add(16.00, SNARE, 98)
    add(16.50, HAT, 54)
    add(17.00, SNARE, 102)
    add(17.00, HAT, 52)
    add(17.50, HAT, 54)
    add(18.00, KICK, 104)
    add(18.00, HAT, 62)
    add(18.50, HAT, 54)
    add(19.00, SNARE, 104)
    add(19.00, HAT, 54)
    add(19.50, HAT, 52)
    add(19.75, KICK, 80)

    # bar 6 -- time, then the motif answers in the second half
    add(20.00, KICK, 106)
    add(20.00, HAT, 62)
    add(20.50, HAT, 54)
    add(21.00, SNARE, 104)
    add(21.00, HAT, 52)
    add(21.50, HAT, 54)
    add(22.00, KICK, 100)
    add(22.00, HAT, 62)
    add(22.50, SNARE, 44)
    add(22.75, SNARE, 110)
    add(23.00, TOM_MID, 94)
    add(23.25, TOM_HIGH, 90)
    add(23.50, SNARE, 78)
    add(23.75, KICK, 84)

    # bar 7 -- ghost note groove, holding back
    add(24.00, KICK, 100)
    add(24.00, HAT, 58)
    add(24.25, SNARE, 34)
    add(24.50, HAT, 48)
    add(24.75, SNARE, 36)
    add(25.00, SNARE, 92)
    add(25.00, HAT, 50)
    add(25.25, SNARE, 32)
    add(25.50, HAT, 48)
    add(25.75, SNARE, 34)
    add(26.00, KICK, 96)
    add(26.00, HAT, 56)
    add(26.25, SNARE, 30)
    add(26.50, HAT, 48)
    add(26.75, SNARE, 32)
    add(27.00, SNARE, 94)
    add(27.00, HAT, 50)
    add(27.25, SNARE, 36)
    add(27.50, TOM_HIGH, 52)
    add(27.75, TOM_MID, 56)

    # bar 8 -- build
    add(28.00, KICK, 104)
    add(28.00, SNARE, 86)
    add(28.50, SNARE, 72)
    add(29.00, SNARE, 80)
    add(29.00, KICK, 92)
    add(29.50, SNARE, 74)
    add(30.00, SNARE, 86)
    add(30.25, SNARE, 80)
    add(30.50, TOM_HIGH, 90)
    add(30.75, TOM_HIGH, 84)
    add(31.00, TOM_MID, 94)
    add(31.25, TOM_MID, 88)
    add(31.50, SNARE, 100)
    add(31.75, SNARE, 96)

    # ===================== bars 9-12 : singles run (beats 32-48) ==========
    # bar 9
    add(32.00, KICK, 110)
    add(32.00, CRASH, 104)
    run(32.0, [SNARE, SNARE, SNARE, SNARE,
               TOM_HIGH, TOM_HIGH, TOM_HIGH, TOM_HIGH,
               TOM_MID, TOM_MID, TOM_MID, TOM_MID,
               TOM_LOW, TOM_LOW, TOM_LOW, TOM_HIGH],
        0.25, 76, 92, accent_every=4, accent_vel=100)
    add(34.00, KICK, 94)
    add(35.50, KICK, 88)

    # bar 10 -- down the toms and back up
    add(36.00, KICK, 104)
    run(36.0, [TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID,
               TOM_LOW, TOM_LOW, TOM_HF, TOM_HF,
               TOM_LOW, TOM_LOW, TOM_MID, TOM_MID,
               TOM_HIMID, TOM_HIMID, TOM_HIGH, TOM_HIGH],
        0.25, 74, 88, accent_every=4, accent_vel=100)
    add(37.00, KICK, 92)
    add(39.00, KICK, 96)
    add(39.50, KICK, 86)
    add(39.75, KICK, 90)

    # bar 11
    add(40.00, KICK, 106)
    add(40.00, SNARE, 100)
    run(40.0, [SNARE, SNARE, TOM_HIGH, SNARE,
               SNARE, TOM_HIGH, SNARE, TOM_MID,
               SNARE, SNARE, TOM_MID, SNARE,
               TOM_HIGH, TOM_MID, TOM_LOW, TOM_HF],
        0.25, 78, 96, accent_every=4, accent_vel=106)
    add(41.00, KICK, 94)
    add(42.00, KICK, 96)
    add(42.75, KICK, 88)
    add(43.00, KICK, 100)

    # bar 12 -- thirty-second burst into the downbeat
    add(44.00, KICK, 108)
    run(44.0, [SNARE] * 4 + [TOM_HIGH] * 4, 0.125, 76, 92)
    add(45.00, KICK, 96)
    run(45.0, [TOM_HIGH] * 4 + [TOM_MID] * 4, 0.125, 84, 98)
    add(46.00, KICK, 98)
    run(46.0, [TOM_MID, TOM_LOW, TOM_HF, TOM_LOW], 0.25, 88, 96)
    add(47.00, KICK, 104)
    run(47.0, [TOM_MID, TOM_HIMID, TOM_HIGH, TOM_HIGH], 0.25, 92, 104)

    # ===================== bars 13-20 : doubles & rolls (48-80) ===========
    # bar 13 -- double strokes on the snare, then the toms
    add(48.00, KICK, 110)
    add(48.00, CRASH, 106)
    add(48.50, SNARE, 72, 'RH')
    add(48.75, SNARE, 78, 'RH')
    add(49.00, SNARE, 84, 'LH')
    add(49.25, SNARE, 88, 'LH')
    add(49.50, SNARE, 92, 'RH')
    add(49.75, SNARE, 96, 'RH')
    add(50.00, TOM_HIGH, 92, 'LH')
    add(50.25, TOM_HIGH, 88, 'LH')
    add(50.50, TOM_MID, 96, 'RH')
    add(50.75, TOM_MID, 92, 'RH')
    add(51.00, TOM_LOW, 98, 'LH')
    add(51.25, TOM_LOW, 94, 'LH')
    add(51.50, TOM_HF, 102, 'RH')
    add(51.75, SNARE, 106, 'LH')

    # bar 14 -- the motif comes back, louder
    add(52.00, KICK, 106)
    add(52.00, SNARE, 102)
    add(52.50, HAT, 52)
    add(52.75, KICK, 78)
    add(53.00, SNARE, 44)
    add(53.25, SNARE, 106)
    add(53.50, TOM_MID, 90)
    add(53.75, TOM_HIGH, 86)
    add(54.00, KICK, 102)
    add(54.00, HAT, 58)
    add(54.50, SNARE, 40)
    add(54.75, SNARE, 108)
    add(55.00, TOM_HIGH, 88)
    add(55.25, TOM_MID, 84)
    add(55.50, SNARE, 74)
    add(55.75, KICK, 84)

    # bar 15 -- double strokes marching down the toms
    add(56.00, KICK, 102)
    run(56.0, [TOM_HIGH] * 4 + [TOM_MID] * 4 + [TOM_LOW] * 4 + [TOM_HF] * 4,
        0.25, 78, 96, accent_every=4, accent_vel=104,
        hands=['RH', 'RH', 'LH', 'LH'] * 4)
    add(58.00, KICK, 92)

    # bar 16 -- press roll swelling into the crash
    add(60.00, KICK, 104)
    for i in range(32):
        add(60.0 + 0.125 * i, SNARE, 56 + 1.7 * i)

    # bar 17 -- crash, ride pattern with syncopated kick
    add(64.00, KICK, 110)
    add(64.00, CRASH, 108)
    for i in range(8):
        add(64.0 + 0.5 * i, RIDE, 74 if i % 2 == 0 else 60)
    add(65.00, SNARE, 100)
    add(66.00, KICK, 98)
    add(67.00, SNARE, 102)
    add(67.50, KICK, 88)
    add(67.75, SNARE, 46)

    # bar 18 -- eighth note triplets over the toms
    add(68.00, KICK, 100)
    run(68.0, [TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW,
               TOM_MID, TOM_HIMID, TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW],
        1.0 / 3.0, 80, 88, accent_every=3, accent_vel=100)
    add(70.00, KICK, 96)

    # bar 19
    add(72.00, KICK, 104)
    run(72.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID, TOM_LOW, TOM_LOW,
               TOM_HF, TOM_HF, TOM_LOW, TOM_LOW, TOM_MID, TOM_MID, TOM_HIMID, TOM_HIGH],
        0.25, 80, 100, accent_every=4, accent_vel=108)
    add(74.00, KICK, 96)

    # bar 20 -- heavy run, big crash lands on bar 21
    add(76.00, KICK, 106)
    add(76.00, SNARE, 104)
    run(76.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID, TOM_LOW, TOM_LOW,
               TOM_HF, TOM_HF, TOM_LOW, TOM_LOW, TOM_MID, TOM_MID, TOM_HIMID, TOM_HIGH],
        0.25, 84, 104, accent_every=4, accent_vel=110)

    # ===================== bars 21-24 : quiet statement (80-96) ===========
    # bar 21 -- subito piano: ghost notes, pedal hat, side stick
    add(80.00, KICK, 108)
    add(80.00, CRASH, 104)
    add(80.50, SNARE, 32)
    add(81.00, HAT_PED, 52)
    add(81.50, SNARE, 30)
    add(82.00, KICK, 56)
    add(82.50, SNARE, 34)
    add(83.00, HAT_PED, 50)
    add(83.50, RIM, 44)
    add(83.75, RIM, 38)

    # bar 22
    add(84.00, HAT_PED, 56)
    add(84.25, SNARE, 30)
    add(84.50, SNARE, 32)
    add(85.00, SNARE, 46)
    add(85.25, SNARE, 28)
    add(85.50, HAT_PED, 50)
    add(85.75, SNARE, 30)
    add(86.00, KICK, 60)
    add(86.25, SNARE, 28)
    add(86.50, SNARE, 32)
    add(87.00, RIM, 48)
    add(87.50, SNARE, 34)
    add(87.75, SNARE, 30)

    # bar 23 -- a splash for colour
    add(88.00, KICK, 64)
    add(88.00, HAT_PED, 54)
    add(88.25, SNARE, 32)
    add(88.50, SNARE, 36)
    add(88.75, SNARE, 34)
    add(89.00, SNARE, 50)
    add(89.50, SPLASH, 54)
    add(90.00, KICK, 62)
    add(90.25, SNARE, 34)
    add(90.50, SNARE, 36)
    add(90.75, SNARE, 38)
    add(91.00, SNARE, 54)
    add(91.50, TOM_HIGH, 44)
    add(91.75, TOM_MID, 48)

    # bar 24 -- swell out of the quiet
    add(92.00, KICK, 70)
    add(92.00, RIM, 52)
    for i in range(8):
        add(92.25 + 0.25 * i, SNARE, 40 + 2.8 * i)
    run(94.0, [TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID,
               TOM_LOW, TOM_LOW, TOM_HF, TOM_HF],
        0.25, 62, 80)

    # ===================== bars 25-32 : rebuild (96-128) ==================
    # bar 25 -- crash and the motif in full voice
    add(96.00, KICK, 112)
    add(96.00, CRASH, 108)
    add(96.00, SNARE, 96)
    add(96.50, HAT, 54)
    add(97.00, SNARE, 104)
    add(97.00, HAT, 52)
    add(97.50, HAT, 54)
    add(98.00, KICK, 106)
    add(98.00, HAT, 62)
    add(98.50, SNARE, 42)
    add(98.75, SNARE, 110)
    add(99.00, TOM_MID, 96)
    add(99.25, TOM_HIGH, 92)
    add(99.50, SNARE, 80)
    add(99.75, KICK, 86)

    # bar 26 -- ghost notes against the accents
    add(100.00, KICK, 108)
    add(100.00, HAT, 62)
    add(100.25, SNARE, 38)
    add(100.50, HAT, 52)
    add(100.75, SNARE, 40)
    add(101.00, SNARE, 106)
    add(101.00, HAT, 54)
    add(101.25, SNARE, 42)
    add(101.50, HAT, 52)
    add(101.75, SNARE, 44)
    add(102.00, KICK, 104)
    add(102.00, HAT, 62)
    add(102.50, SNARE, 46)
    add(102.75, SNARE, 112)
    add(103.00, TOM_HIGH, 98)
    add(103.25, TOM_MID, 94)
    add(103.50, TOM_LOW, 88)
    add(103.75, KICK, 90)

    # bar 27 -- sixteenths on the snare with kick punches
    add(104.00, KICK, 108)
    for i in range(16):
        v = 106 if i % 4 == 0 else 44 + (i % 4) * 4
        add(104.0 + 0.25 * i, SNARE, v)
    add(105.00, KICK, 96)
    add(106.00, KICK, 100)
    add(107.00, KICK, 104)
    add(107.50, KICK, 96)
    add(107.75, KICK, 92)

    # bar 28 -- toms answering
    add(108.00, KICK, 106)
    add(108.00, SNARE, 100)
    run(108.0, [TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIMID,
                TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_LOW],
        0.25, 86, 100, accent_every=4, accent_vel=110)
    add(110.00, KICK, 100)

    # bar 29 -- thirty-seconds
    add(112.00, KICK, 110)
    add(112.00, CRASH2, 100)
    run(112.0, [SNARE] * 8, 0.125, 70, 88)
    add(113.00, KICK, 96)
    run(113.0, [SNARE] * 4 + [TOM_HIGH] * 4, 0.125, 80, 96)
    add(114.00, KICK, 100)
    run(114.0, [TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIMID, TOM_HIGH, TOM_MID],
        0.25, 90, 104)
    add(115.00, KICK, 104)
    run(115.0, [TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW], 0.25, 94, 108)

    # bar 30 -- syncopation with ghost notes
    add(116.00, KICK, 110)
    add(116.00, SNARE, 104)
    add(116.50, SNARE, 46)
    add(116.75, KICK, 96)
    add(117.00, SNARE, 100)
    add(117.25, KICK, 90)
    add(117.50, SNARE, 44)
    add(117.75, SNARE, 108)
    add(118.00, KICK, 100)
    add(118.00, HAT_PED, 62)
    add(118.50, SNARE, 42)
    add(118.75, SNARE, 110)
    add(119.00, TOM_MID, 98)
    add(119.25, TOM_HIGH, 94)
    add(119.50, SNARE, 84)
    add(119.75, KICK, 92)

    # bar 31
    add(120.00, KICK, 108)
    run(120.0, [SNARE, SNARE, TOM_HIGH, TOM_MID, SNARE, SNARE, TOM_HIGH, TOM_MID,
                SNARE, TOM_HIGH, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIGH],
        0.25, 88, 104, accent_every=4, accent_vel=112)
    add(121.00, KICK, 96)
    add(122.50, KICK, 100)
    add(123.00, KICK, 98)

    # bar 32 -- fill into the peak
    add(124.00, KICK, 110)
    add(124.00, CRASH, 104)
    run(124.0, [TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIMID,
                TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_LOW],
        0.25, 90, 108)
    add(126.00, KICK, 104)
    run(126.0, [SNARE] * 8, 0.125, 84, 104)
    add(127.00, KICK, 108)
    run(127.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH], 0.25, 100, 112)

    # ===================== bars 33-40 : climax (128-160) ==================
    # bar 33
    add(128.00, KICK, 112)
    add(128.00, CRASH, 110)
    add(128.00, SNARE, 104)
    add(128.50, SNARE, 46)
    add(128.75, SNARE, 112)
    add(129.00, TOM_MID, 100)
    add(129.25, TOM_HIGH, 96)
    add(129.50, SNARE, 82)
    add(129.75, KICK, 96)
    add(130.00, KICK, 106)
    add(130.00, HAT_PED, 62)
    add(130.50, SNARE, 44)
    add(130.75, SNARE, 110)
    add(131.00, TOM_LOW, 100)
    add(131.25, TOM_MID, 96)
    add(131.50, TOM_HIGH, 92)
    add(131.75, KICK, 100)

    # bar 34
    add(132.00, KICK, 108)
    run(132.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID, TOM_HIGH, TOM_HIGH,
                TOM_LOW, TOM_LOW, TOM_MID, TOM_MID, TOM_HF, TOM_HF, TOM_LOW, TOM_MID],
        0.25, 88, 104, accent_every=4, accent_vel=112)
    add(133.00, KICK, 96)
    add(135.00, KICK, 100)
    add(135.50, KICK, 92)

    # bar 35
    add(136.00, KICK, 110)
    add(136.00, SNARE, 106)
    add(136.75, KICK, 92)
    add(137.00, SNARE, 102)
    add(137.50, SNARE, 44)
    add(137.75, SNARE, 110)
    add(138.00, KICK, 106)
    add(138.00, CRASH2, 100)
    add(138.50, SNARE, 46)
    add(138.75, TOM_HIGH, 104)
    add(139.00, TOM_MID, 98)
    add(139.25, TOM_LOW, 94)
    add(139.50, TOM_HF, 100)
    add(139.75, SNARE, 108)

    # bar 36
    add(140.00, KICK, 110)
    run(140.0, [SNARE] * 8, 0.125, 78, 96)
    add(141.00, KICK, 98)
    run(141.0, [TOM_HIGH] * 4 + [TOM_MID] * 4, 0.125, 88, 104)
    add(142.00, KICK, 100)
    run(142.0, [TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIMID, TOM_HIGH, TOM_HIMID, TOM_MID],
        0.25, 92, 106)
    add(143.00, KICK, 106)
    run(143.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH], 0.25, 104, 114)

    # bar 37 -- heavy syncopated statement
    add(144.00, KICK, 114)
    add(144.00, CRASH, 108)
    add(144.00, SNARE, 104)
    add(144.75, KICK, 100)
    add(145.00, SNARE, 110)
    add(145.25, SNARE, 46)
    add(145.50, KICK, 94)
    add(145.75, SNARE, 48)
    add(146.00, KICK, 106)
    add(146.00, SNARE, 112)
    add(146.75, KICK, 98)
    add(147.00, SNARE, 114)
    add(147.50, SNARE, 52)
    add(147.75, SNARE, 58)

    # bar 38
    add(148.00, KICK, 110)
    add(148.00, SNARE, 106)
    add(148.50, HAT_PED, 66)
    add(148.75, KICK, 96)
    add(149.00, SNARE, 108)
    add(149.25, SNARE, 44)
    add(149.50, KICK, 92)
    add(149.75, SNARE, 46)
    add(150.00, KICK, 108)
    add(150.00, SNARE, 104)
    add(150.50, TOM_HIGH, 96)
    add(150.75, TOM_MID, 94)
    add(151.00, TOM_LOW, 100)
    add(151.25, TOM_HF, 98)
    add(151.50, SNARE, 104)
    add(151.75, SNARE, 100)

    # bar 39
    add(152.00, KICK, 110)
    add(152.00, SNARE, 104)
    for i in range(8):
        add(152.5 + 0.5 * i, HAT, 64 if i % 2 == 0 else 54)
    add(153.00, SNARE, 108)
    add(153.50, SNARE, 46)
    add(154.00, KICK, 106)
    add(154.00, SNARE, 104)
    add(154.50, SNARE, 44)
    add(154.75, SNARE, 110)
    add(155.00, TOM_MID, 98)
    add(155.25, TOM_HIGH, 94)
    add(155.50, TOM_LOW, 90)
    add(155.75, KICK, 96)

    # bar 40 -- fill into the breakdown
    add(156.00, KICK, 108)
    run(156.0, [SNARE] * 8, 0.125, 80, 100)
    add(157.00, KICK, 100)
    run(157.0, [TOM_HIGH] * 4 + [TOM_MID] * 4, 0.125, 88, 104)
    add(158.00, KICK, 102)
    run(158.0, [TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIMID, TOM_HIGH, TOM_MID],
        0.25, 92, 104)
    add(159.00, SNARE, 106)
    add(159.25, SNARE, 100)
    add(159.50, TOM_HIGH, 108)
    add(159.75, TOM_HIGH, 104)

    # ===================== bars 41-44 : breakdown (160-176) ===============
    # bar 41 -- wide open, heavy
    add(160.00, KICK, 116)
    add(160.00, SNARE, 112)
    add(160.00, CHINA, 96)
    add(161.00, SNARE, 116)
    add(161.50, SNARE, 50)
    add(162.00, KICK, 110)
    add(162.00, HAT_PED, 66)
    add(163.00, SNARE, 114)
    add(163.50, SNARE, 52)
    add(163.75, KICK, 100)

    # bar 42 -- side stick colours
    add(164.00, KICK, 112)
    add(164.00, RIM, 88)
    add(165.00, SNARE, 110)
    add(165.25, RIM, 54)
    add(165.50, KICK, 100)
    add(166.00, SNARE, 112)
    add(166.00, TAMB, 62)
    add(166.50, TOM_LOW, 100)
    add(166.75, TOM_HF, 98)
    add(167.00, SNARE, 114)
    add(167.50, SNARE, 52)
    add(167.75, KICK, 104)

    # bar 43
    add(168.00, KICK, 114)
    add(168.00, SNARE, 110)
    add(168.50, SNARE, 48)
    add(168.75, SNARE, 112)
    add(169.00, KICK, 104)
    add(169.50, SNARE, 46)
    add(169.75, TOM_MID, 100)
    add(170.00, KICK, 110)
    add(170.00, SNARE, 108)
    add(170.50, TOM_HIGH, 96)
    add(170.75, TOM_HIMID, 94)
    add(171.00, SNARE, 112)
    add(171.50, SNARE, 50)
    add(171.75, KICK, 102)

    # bar 44 -- build out of the breakdown
    add(172.00, KICK, 108)
    run(172.0, [SNARE] * 8, 0.125, 82, 104)
    add(173.00, KICK, 104)
    run(173.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID, TOM_LOW, TOM_LOW],
        0.125, 90, 108)
    add(174.00, KICK, 106)
    run(174.0, [TOM_HF, TOM_HF, TOM_LOW, TOM_LOW, TOM_MID, TOM_MID, TOM_HIMID, TOM_HIMID],
        0.125, 94, 110)
    add(175.00, KICK, 110)
    run(175.0, [SNARE, SNARE, SNARE, SNARE], 0.25, 108, 118)

    # ===================== bars 45-52 : final push (176-208) ==============
    # bar 45 -- motif in full voice
    add(176.00, KICK, 114)
    add(176.00, CRASH2, 106)
    add(176.50, SNARE, 48)
    add(176.75, SNARE, 116)
    add(177.00, TOM_MID, 104)
    add(177.25, TOM_HIGH, 100)
    add(177.50, TOM_LOW, 96)
    add(177.75, KICK, 104)
    add(178.00, KICK, 112)
    add(178.00, SNARE, 108)
    add(178.50, SNARE, 50)
    add(178.75, SNARE, 118)
    add(179.00, TOM_HIGH, 106)
    add(179.25, TOM_MID, 102)
    add(179.50, TOM_HF, 98)
    add(179.75, KICK, 106)

    # bar 46
    add(180.00, KICK, 110)
    run(180.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID, TOM_HIMID, TOM_HIMID,
                TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID, TOM_LOW, TOM_LOW, TOM_HF, TOM_HF],
        0.25, 96, 112, accent_every=4, accent_vel=118)
    add(181.00, KICK, 104)
    add(182.00, KICK, 108)
    add(183.00, KICK, 106)
    add(183.50, KICK, 100)
    add(183.75, KICK, 96)

    # bar 47 -- double strokes
    add(184.00, KICK, 110)
    add(184.00, SNARE, 106)
    run(184.0, [TOM_HIGH] * 4 + [TOM_MID] * 4 + [TOM_LOW] * 4 + [TOM_HF] * 4,
        0.25, 96, 112, accent_every=4, accent_vel=120,
        hands=['RH', 'RH', 'LH', 'LH'] * 4)
    add(186.00, KICK, 106)
    add(187.00, KICK, 110)
    add(187.50, KICK, 102)

    # bar 48 -- fill
    add(188.00, KICK, 112)
    run(188.0, [SNARE] * 8, 0.125, 92, 112)
    add(189.00, KICK, 108)
    run(189.0, [TOM_HIGH] * 4 + [TOM_MID] * 4, 0.125, 96, 114)
    add(190.00, KICK, 110)
    run(190.0, [TOM_MID] * 2 + [TOM_LOW] * 2 + [TOM_HF] * 2 + [TOM_LOW] * 2, 0.125, 100, 116)
    add(191.00, KICK, 112)
    run(191.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH], 0.25, 108, 120)

    # bar 49 -- peak
    add(192.00, KICK, 116)
    add(192.00, CRASH, 112)
    add(192.00, SNARE, 110)
    run(192.5, [SNARE] * 4, 0.125, 90, 100)
    add(193.00, KICK, 108)
    run(193.0, [TOM_HIGH, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIMID, TOM_HIGH],
        0.125, 96, 112)
    add(194.00, KICK, 110)
    run(194.0, [SNARE] * 2 + [TOM_HIGH] * 2 + [TOM_MID] * 2 + [TOM_LOW] * 2, 0.125, 100, 112)
    add(195.00, KICK, 112)
    run(195.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH], 0.25, 108, 118)

    # bar 50
    add(196.00, KICK, 114)
    add(196.00, SNARE, 112)
    add(196.75, KICK, 104)
    add(197.00, SNARE, 114)
    add(197.25, SNARE, 52)
    add(197.50, KICK, 100)
    add(197.75, SNARE, 54)
    add(198.00, KICK, 112)
    add(198.00, SNARE, 110)
    add(198.50, SNARE, 48)
    add(198.75, SNARE, 116)
    add(199.00, TOM_MID, 106)
    add(199.25, TOM_HIGH, 102)
    add(199.50, TOM_LOW, 98)
    add(199.75, KICK, 108)

    # bar 51 -- singles all over the kit
    add(200.00, KICK, 112)
    run(200.0, [SNARE, SNARE, TOM_HIGH, TOM_MID, TOM_LOW, TOM_MID, TOM_HIGH, TOM_HIMID,
                TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIGH],
        0.25, 100, 114, accent_every=4, accent_vel=120)
    add(201.00, KICK, 106)
    add(203.00, KICK, 110)

    # bar 52 -- double bass and accents
    add(204.00, KICK, 114)
    add(204.00, CRASH2, 108)
    add(204.00, SNARE, 110)
    for i in range(16):
        foot = 'RF' if i % 2 == 0 else 'LF'
        add(204.5 + 0.125 * i, KICK, 92 if i % 2 == 0 else 78, foot)
    add(206.50, SNARE, 112)
    add(206.75, SNARE, 54)
    add(207.00, KICK, 110)
    add(207.00, SNARE, 108)
    add(207.50, TOM_HIGH, 112)
    add(207.75, TOM_HIGH, 108)

    # ===================== bars 53-56 : ending (208-224) ==================
    # bar 53 -- thirty-second roll swelling
    add(208.00, KICK, 112)
    for i in range(16):
        add(208.0 + 0.125 * i, SNARE, 66 + 2.0 * i)
    add(210.00, KICK, 108)
    run(210.0, [TOM_HIGH, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW, TOM_MID, TOM_HIMID, TOM_HIGH],
        0.25, 100, 112)

    # bar 54 -- triplets
    add(212.00, KICK, 110)
    add(212.00, SNARE, 106)
    run(212.0, [TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW, TOM_HF, TOM_LOW,
                TOM_MID, TOM_HIMID, TOM_HIGH, TOM_HIMID, TOM_MID, TOM_LOW],
        1.0 / 3.0, 88, 104, accent_every=3, accent_vel=112)
    add(214.00, KICK, 108)
    run(214.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID,
                TOM_LOW, TOM_LOW, TOM_HF, TOM_HF, TOM_LOW, TOM_LOW],
        1.0 / 3.0, 92, 108, accent_every=3, accent_vel=116)

    # bar 55 -- the last fill
    add(216.00, KICK, 112)
    run(216.0, [SNARE] * 8, 0.125, 88, 108)
    add(217.00, KICK, 106)
    run(217.0, [SNARE, SNARE, TOM_HIGH, TOM_HIGH, TOM_MID, TOM_MID, TOM_LOW, TOM_LOW],
        0.125, 92, 112)
    add(218.00, KICK, 110)
    run(218.0, [TOM_HF, TOM_HF, TOM_LOW, TOM_LOW, TOM_MID, TOM_MID, TOM_HIMID, TOM_HIMID],
        0.125, 96, 114)
    add(219.00, KICK, 112)
    run(219.0, [TOM_HIGH, TOM_HIGH, TOM_MID, TOM_HIGH, TOM_HIGH, SNARE, SNARE, SNARE],
        0.125, 100, 122)

    # bar 56 -- one last hit, left ringing
    add(220.00, KICK, 118)
    add(220.00, CRASH, 116)
    add(220.00, CRASH2, 110)
    add(220.00, HAT_PED, 64)


# ---------------------------------------------------------------------------
# Two hands, two feet
# ---------------------------------------------------------------------------
def assign_limbs(events):
    """Give every stroke to a limb.  Strokes needing the same limb inside
    ~30 ms are moved to the free limb (or, if there is none, dropped)."""
    ev = sorted(events, key=lambda e: e[0])
    last = {'RH': -1e9, 'LH': -1e9, 'RF': -1e9, 'LF': -1e9}
    MIN = 0.055                       # beats, ~30 ms at 112 bpm
    out = []
    for t, note, vel, hand in ev:
        if note in (KICK, KICK2):
            cands = ['RF']
        elif note == HAT_PED:
            cands = ['LF']
        else:
            cands = ['RH', 'LH']

        if hand in ('RH', 'LH') and hand in cands:
            cands = [hand] + [c for c in cands if c != hand]
        elif hand in ('RF', 'LF') and note in (KICK, KICK2):
            cands = [hand] + [c for c in ('RF', 'LF') if c != hand]

        pick = None
        for c in cands:
            if t - last[c] >= MIN and (pick is None or t - last[c] > t - last[pick]):
                pick = c
        if pick is None:                       # try the limb that is not a candidate
            for c in ('RH', 'LH', 'RF', 'LF'):
                if c not in cands and t - last[c] >= MIN:
                    pick = c
                    break
        if pick is None:                       # physically impossible: skip
            continue
        last[pick] = t
        out.append((t, note, vel, pick))
    return out


# ---------------------------------------------------------------------------
# Human timing
# ---------------------------------------------------------------------------
def jitter(scale):
    """Symmetric triangular noise, deterministic."""
    return (rng.random() + rng.random() - 1.0) * scale


def humanize(t, vel, limb):
    off = (80 - vel) * 0.00008            # ghosts a hair late, accents a hair early
    off += jitter(0.013)
    if limb == 'LH':
        off += 0.0015                     # the left hand trails a touch
    elif limb == 'RH':
        off -= 0.0008
    # slow leaning across the performance: phrases push, then hold back
    off += 0.006 * math.sin(2.0 * math.pi * t / 64.0)
    off += 0.004 * math.sin(2.0 * math.pi * t / 23.0 + 1.3)
    return t + off


# ---------------------------------------------------------------------------
# Note lengths
# ---------------------------------------------------------------------------
DUR = {
    KICK: 0.5, KICK2: 0.5,
    SNARE: 0.45, RIM: 0.15, CLAP: 0.4,
    HAT: 0.18, HAT_OPEN: 1.2, HAT_PED: 0.25,
    TOM_L: 0.7, TOM_HF: 0.7, TOM_LOW: 0.7, TOM_MID: 0.7, TOM_HIMID: 0.7, TOM_HIGH: 0.7,
    CRASH: 3.0, CRASH2: 3.0, CHINA: 2.6, RIDE: 2.0, BELL: 1.5, SPLASH: 1.2,
    TAMB: 0.5, COWBELL: 0.4,
}


def make_messages(assigned):
    ons = []
    for t, note, vel, limb in assigned:
        tick = max(0, int(round(humanize(t, vel, limb) * TPB)))
        ons.append((tick, note, max(1, min(127, vel))))
    ons.sort(key=lambda x: (x[0], x[1]))

    by_note = {}
    for i, (tick, note, vel) in enumerate(ons):
        by_note.setdefault(note, []).append(i)

    offs = []
    for note, idx in by_note.items():
        length = int(round(DUR.get(note, 0.4) * TPB))
        for k, i in enumerate(idx):
            tick = ons[i][0]
            end = tick + length
            if k + 1 < len(idx):
                nxt = ons[idx[k + 1]][0]
                end = tick + 10 if nxt - tick <= 10 else min(end, nxt - 5)
            offs.append((end, note))

    msgs = [(t, True, n, v) for (t, n, v) in ons]
    msgs += [(t, False, n, 0) for (t, n) in offs]
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))   # note-offs first at equal ticks
    return msgs


# ---------------------------------------------------------------------------
# Tempo map: the pulse surges and settles
# ---------------------------------------------------------------------------
TEMPO_ANCHORS = [
    (0.0, 0.965), (8.0, 0.985), (16.0, 1.000), (28.0, 0.995),
    (32.0, 1.015), (44.0, 1.030), (48.0, 1.005), (60.0, 0.995),
    (64.0, 1.000), (76.0, 1.015), (80.0, 0.930), (92.0, 0.950),
    (96.0, 1.000), (112.0, 1.035), (124.0, 1.050), (128.0, 1.055),
    (144.0, 1.040), (160.0, 0.985), (168.0, 0.995), (176.0, 1.020),
    (192.0, 1.055), (208.0, 1.035), (216.0, 1.070), (220.0, 0.985),
    (224.0, 0.975),
]


def tempo_mod(beat):
    n = len(TEMPO_ANCHORS)
    if beat <= TEMPO_ANCHORS[0][0]:
        base = TEMPO_ANCHORS[0][1]
    elif beat >= TEMPO_ANCHORS[-1][0]:
        base = TEMPO_ANCHORS[-1][1]
    else:
        base = TEMPO_ANCHORS[-1][1]
        for i in range(n - 1):
            b0, m0 = TEMPO_ANCHORS[i]
            b1, m1 = TEMPO_ANCHORS[i + 1]
            if b0 <= beat <= b1:
                u = 0.0 if b1 == b0 else (beat - b0) / (b1 - b0)
                base = m0 + (m1 - m0) * u
                break
    wave = 0.008 * math.sin(2.0 * math.pi * beat / 16.0)
    wave += 0.004 * math.sin(2.0 * math.pi * beat / 23.0 + 1.3)
    return base * (1.0 + wave)


MODS = [tempo_mod(b) for b in range(BEATS)]
BASE_BPM = 60.0 * sum(1.0 / m for m in MODS) / TARGET_SECONDS


def bpm_at_beat(b):
    return BASE_BPM * MODS[min(b, BEATS - 1)]


# ---------------------------------------------------------------------------
# File assembly
# ---------------------------------------------------------------------------
def main():
    compose()

    assigned = assign_limbs(EV)
    msgs = make_messages(assigned)

    mid = MidiFile(type=1, ticks_per_beat=TPB)

    # --- conductor track
    cond = MidiTrack()
    mid.tracks.append(cond)
    cond.append(MetaMessage('track_name', name='Drum Solo', time=0))
    cond.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    prev = 0
    for b in range(BEATS + 1):
        tick = b * TPB
        cond.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm_at_beat(b)),
                                time=tick - prev))
        prev = tick
    cond.append(MetaMessage('end_of_track', time=0))

    # --- drums
    trk = MidiTrack()
    mid.tracks.append(trk)
    trk.append(MetaMessage('track_name', name='Drums', time=0))
    prev = 0
    for tick, is_on, note, vel in msgs:
        delta = tick - prev
        if delta < 0:
            delta = 0
        prev = tick
        if is_on:
            trk.append(Message('note_on', note=note, velocity=vel,
                               channel=CH, time=delta))
        else:
            trk.append(Message('note_off', note=note, velocity=0,
                               channel=CH, time=delta))
    trk.append(MetaMessage('end_of_track', time=max(0, BEATS * TPB - prev)))

    mid.save('solo.mid')


main()
