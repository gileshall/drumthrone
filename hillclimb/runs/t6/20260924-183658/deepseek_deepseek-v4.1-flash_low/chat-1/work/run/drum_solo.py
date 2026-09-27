#!/usr/bin/env python3
"""
drum_solo.py

Generates "solo.mid" -- a two minute solo drum performance for a General MIDI
synthesizer, played on MIDI channel 10.

Design notes
------------
* A tempo map rides with the music: it starts relaxed, surges through the
  climax and settles again, so the pulse itself breathes.
* Everything is written on a 16th-note grid but then humanised: a smooth
  per-bar timing drift (phrases lean forward or hold back) plus a few
  milliseconds of random placement per note, and per-note velocity spread.
* Two motifs are stated, varied, moved around the kit and brought back.
  Density and dynamics are shaped *inside* phrases (accents, ghost notes,
  crescendos) rather than by simply turning whole sections up or down.
* At most two hands and two feet can strike at any instant; a final pass
  enforces that as a hard guarantee.
"""

import random
from collections import defaultdict

from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
PPQ = 480                 # ticks per quarter note
CH = 9                    # MIDI channel 10 (zero based)
NBARS = 58                # 58 bars of 4/4

# --- General MIDI percussion map (relevant subset) -------------------------
KICK, KICK2 = 36, 35
SNARE, RIM = 38, 37
HH, HHP, HHO = 42, 44, 46
RIDE, BELL = 51, 53
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL = 50, 48, 47, 45, 43, 41
TOM_DESC = [TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL]
TOM_ASC = TOM_DESC[::-1]

HANDS = {SNARE, RIM, HH, HHO, RIDE, BELL, CRASH, CRASH2, SPLASH, CHINA}
HANDS |= set(TOM_DESC)
FEET = {KICK, KICK2, HHP}

rng = random.Random(0xD00D1E)

NOTES = []                 # (absolute_beat, note, velocity)


def h(t, note, vel):
    """Register one drum stroke at absolute beat position ``t``."""
    NOTES.append((float(t), int(note), int(round(max(1.0, min(127.0, vel))))))


# --------------------------------------------------------------------------
# pattern helpers
# --------------------------------------------------------------------------
def motifA(tb, v=78, ride_note=RIDE, kicks=(0.0, 1.75, 2.5),
           ghosts=(2.75, 3.75), accent=10, ride=True):
    """
    Motif A -- the solo's main one-bar idea.
    Ride/hat on 8ths with quarter-note accents, kick on 1, the '&' of 2 and
    the '&' of 3, backbeat snare on 2 and 4, and a pair of ghost notes that
    push into the next bar.  Every parameter is fair game for variation.
    """
    if ride:
        for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
            a = accent if p in (0.0, 1.0, 2.0, 3.0) else 0
            h(tb + p, ride_note, v - 4 + a + rng.uniform(-2.5, 2.5))
    for k in kicks:
        h(tb + k, KICK, v + 16 + rng.uniform(-3.0, 3.0))
    for s in (1.0, 3.0):
        h(tb + s, SNARE, v + 24 + rng.uniform(-3.0, 3.0))
    for g in ghosts:
        h(tb + g, SNARE, v - 42 + rng.uniform(-4.0, 4.0))


def run16(tb, seq, v0=80, v1=100, kick_beats=(), kv=95):
    """A run of consecutive 16th notes through ``seq``, with a velocity ramp."""
    n = len(seq)
    for j, nt in enumerate(seq):
        f = j / max(1, n - 1)
        h(tb + j * 0.25, nt, v0 + (v1 - v0) * f + rng.uniform(-2.0, 2.0))
    for kb in kick_beats:
        h(tb + kb, KICK, kv + rng.uniform(-3.0, 3.0))


# ==========================================================================
# 1.  INTRO  (bars 0-3)  -- the pulse, stated quietly
# ==========================================================================
for i in range(4):
    tb = i * 4.0
    h(tb + 0.0, HHP, 56 + 3 * i)
    h(tb + 2.0, HHP, 50 + 3 * i)
    if i >= 1:
        h(tb + 1.0, RIM, 64 + 4 * i)
        h(tb + 3.0, RIM, 66 + 4 * i)
    if i >= 2:
        h(tb + 0.5, HH, 50)
        h(tb + 1.75, SNARE, 28 + 2 * i)
        h(tb + 3.75, SNARE, 30 + 2 * i)
    if i == 3:
        h(tb + 0.0, KICK, 62)
        h(tb + 2.5, HH, 46)
        h(tb + 2.75, SNARE, 26)

# ==========================================================================
# 2.  MOTIF A IS STATED  (bars 4-7)
# ==========================================================================
motifA(16.0, v=72, ride_note=RIDE, kicks=(0.0, 1.75, 2.5), ghosts=(2.75, 3.75))
motifA(20.0, v=74, ride_note=BELL, kicks=(0.0, 1.5, 2.5), ghosts=(2.75,))
motifA(24.0, v=78, ride_note=RIDE, kicks=(0.0, 1.75, 2.5, 3.25), ghosts=(2.75, 3.75))

# bar 7 -- first descent around the kit, carrying into the next downbeat
tb = 28.0
fill = [(0.00, SNARE, 86), (0.25, SNARE, 68), (0.50, SNARE, 90), (0.75, SNARE, 70),
        (1.00, TOM_H, 92), (1.25, TOM_H, 74), (1.50, TOM_HM, 94), (1.75, TOM_HM, 76),
        (2.00, TOM_LM, 96), (2.25, TOM_LM, 78), (2.50, TOM_L, 98), (2.75, TOM_L, 80),
        (3.00, TOM_FH, 102), (3.25, TOM_FH, 84), (3.50, TOM_FL, 106), (3.75, TOM_FL, 88)]
for p, nt, v in fill:
    h(tb + p, nt, v)
h(tb + 0.0, KICK, 100)
h(tb + 2.0, KICK, 96)

# ==========================================================================
# 3.  DEVELOPMENT  (bars 8-13) -- variations of A, then motif B
# ==========================================================================
h(32.0, CRASH, 106)
h(32.0, KICK, 108)
motifA(32.0, v=84, ride_note=RIDE, kicks=(1.75, 2.5), ghosts=(2.75, 3.75))

motifA(36.0, v=82, ride_note=BELL, kicks=(0.0, 1.25, 2.5), ghosts=(2.75, 3.5))

# bar 10 -- motif B: same kit, different accent placement.
tb = 40.0
for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
    h(tb + p, HH, 72 + (8 if p in (0.0, 1.0, 2.0, 3.0) else 0))
h(tb + 0.0, KICK, 100)
h(tb + 1.5, KICK, 92)
h(tb + 3.0, KICK, 94)
h(tb + 0.75, SNARE, 104)
h(tb + 2.25, SNARE, 106)
h(tb + 1.75, SNARE, 32)
h(tb + 3.25, SNARE, 34)
h(tb + 3.75, SNARE, 30)

motifA(44.0, v=82, ride_note=RIDE, kicks=(0.0, 1.75, 2.75), ghosts=(3.75,))
h(47.00, SNARE, 96)
h(47.25, SNARE, 76)
h(47.50, SNARE, 100)
h(47.75, SNARE, 80)

# bar 12 -- groove then toms
tb = 48.0
h(tb + 0.0, HH, 84); h(tb + 0.5, HH, 68)
h(tb + 1.0, HH, 86); h(tb + 1.5, HH, 70)
h(tb + 0.0, KICK, 104)
h(tb + 1.0, SNARE, 108)
h(tb + 1.75, SNARE, 34)
h(tb + 2.0, TOM_H, 96);  h(tb + 2.5, TOM_HM, 98)
h(tb + 3.0, TOM_LM, 100); h(tb + 3.5, TOM_L, 102)
h(tb + 2.0, KICK, 92)

# bar 13 -- 16ths down and back up, crescendo
run16(52.0, [TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, TOM_FL, TOM_FH,
             TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE, TOM_LM, TOM_FL],
      v0=88, v1=116, kick_beats=(0.0, 1.0, 2.0, 3.0), kv=92)

# ==========================================================================
# 4.  TOMS AND DOUBLE STROKES  (bars 14-19)
# ==========================================================================
# bar 14 -- crash and a low call/response
tb = 56.0
h(tb + 0.0, CRASH2, 102)
h(tb + 0.0, KICK, 106)
h(tb + 0.5, SNARE, 80)
h(tb + 1.0, TOM_FL, 98)
h(tb + 1.5, SNARE, 66)
h(tb + 2.0, TOM_FH, 100)
h(tb + 2.5, SNARE, 68)
h(tb + 3.0, TOM_L, 102)
h(tb + 3.5, SNARE, 72)
h(tb + 2.0, KICK, 92)
h(tb + 3.5, KICK, 88)

# bar 15 -- double strokes falling down the toms
run16(60.0, [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM, TOM_L, TOM_L,
             TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_FL, TOM_FH, TOM_LM, TOM_HM],
      v0=84, v1=110, kick_beats=(0.0, 2.0), kv=96)

# bar 16 -- snare / tom interleave
run16(64.0, [SNARE, TOM_H, SNARE, TOM_HM, SNARE, TOM_LM, SNARE, TOM_L,
             SNARE, TOM_FH, SNARE, TOM_FL, SNARE, SNARE, TOM_LM, TOM_FL],
      v0=86, v1=112, kick_beats=(0.0, 2.0), kv=98)

# bar 17 -- same idea, backwards, feet busier
run16(68.0, [TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE,
             TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, SNARE, SNARE],
      v0=88, v1=114, kick_beats=(0.0, 1.0, 2.0, 3.0), kv=94)

# bar 18 -- hi-hat groove with syncopated snare
tb = 72.0
for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
    h(tb + p, HH, 76 + (6 if p in (0.0, 1.0, 2.0, 3.0) else 0))
h(tb + 0.0, KICK, 102)
h(tb + 1.0, SNARE, 106)
h(tb + 2.0, SNARE, 104)
h(tb + 2.5, KICK, 94)
h(tb + 3.0, SNARE, 108)
h(tb + 3.5, KICK, 92)
h(tb + 1.75, SNARE, 30)
h(tb + 0.75, SNARE, 34)

# bar 19 -- double strokes, big crescendo
run16(76.0, [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM, TOM_L, TOM_L,
             TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_FL, TOM_FL, TOM_FH, TOM_FH],
      v0=90, v1=118, kick_beats=(0.0, 2.0), kv=100)

# ==========================================================================
# 5.  SNARE FEATURE  (bars 20-21)
# ==========================================================================
# bar 20 -- accented 16ths with a long crescendo
tb = 80.0
acc = {0, 3, 4, 7, 8, 11, 12, 15}
for j in range(16):
    h(tb + j * 0.25, SNARE, (104 if j in acc else 62) + j)
h(tb + 0.0, KICK, 104)
h(tb + 2.0, KICK, 102)

# bar 21 -- the accents migrate down the toms
tb = 84.0
acc = {0, 2, 5, 6, 8, 10, 13, 14}
for j in range(16):
    nt = SNARE if j < 8 else TOM_DESC[(j - 8) // 2]
    h(tb + j * 0.25, nt, (106 if j in acc else 66) + j)
h(tb + 0.0, KICK, 106)
h(tb + 2.0, KICK, 104)

# ==========================================================================
# 6.  THE BUILD  (bars 22-29)
# ==========================================================================
# bar 22 -- 8ths, backbeat accented
tb = 88.0
for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
    h(tb + p, SNARE, 100 if p in (1.0, 3.0) else 62)
h(tb + 0.0, KICK, 104)
h(tb + 2.0, KICK, 102)

# bar 23 -- full 16ths
tb = 92.0
for j in range(16):
    h(tb + j * 0.25, SNARE, (104 if j % 4 == 0 else 66) + j)
h(tb + 0.0, KICK, 106)
h(tb + 2.0, KICK, 104)

# bar 24 -- accents shifting off the beat
tb = 96.0
for j in range(16):
    v = 76 + 1.6 * j + (16 if j % 4 in (0, 2) else 0)
    h(tb + j * 0.25, SNARE, v)
h(tb + 0.0, KICK, 108)
h(tb + 1.0, KICK, 96)
h(tb + 2.0, KICK, 106)
h(tb + 3.0, KICK, 98)

# bar 25 -- snare / tom double strokes rising in volume
tb = 100.0
seq = [SNARE, SNARE, TOM_H, TOM_H, SNARE, SNARE, TOM_HM, TOM_HM,
       TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_FH, TOM_FH, TOM_FL, TOM_FL]
for j, nt in enumerate(seq):
    h(tb + j * 0.25, nt, 84 + 2 * j)
h(tb + 0.0, KICK, 108)
h(tb + 2.0, KICK, 106)

# bar 26 -- singles out and back
run16(104.0, [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, SNARE,
              TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE],
      v0=96, v1=112, kick_beats=(0.0, 1.0, 2.0, 3.0), kv=106)

# bar 27 -- a straight cascade with the feet answering
tb = 108.0
for j in range(16):
    nt = TOM_DESC[j % 6] if j < 12 else SNARE
    h(tb + j * 0.25, nt, 90 + 2 * j)
h(tb + 0.0, KICK, 110)
h(tb + 2.0, KICK, 108)

# bar 28 -- surge
run16(112.0, [TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE,
              SNARE, SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL],
      v0=100, v1=118, kick_beats=(0.0, 1.0, 2.0, 3.0), kv=108)

# bar 29 -- last push into the climax
tb = 116.0
fill = [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, TOM_FL,
        TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE, TOM_FL]
for j, nt in enumerate(fill):
    h(tb + j * 0.25, nt, 96 + 2 * j)
h(tb + 0.0, KICK, 114)
h(tb + 2.0, KICK, 112)

# ==========================================================================
# 7.  FIRST CLIMAX  (bars 30-35)
# ==========================================================================
h(120.0, CRASH, 112)
h(120.0, KICK, 116)
motifA(120.0, v=90, ride_note=RIDE, kicks=(1.75, 2.5), ghosts=(2.75, 3.75))

run16(124.0, [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, TOM_FL,
              TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE, TOM_FL],
      v0=94, v1=116, kick_beats=(0.0, 1.0, 2.0, 3.0), kv=104)

# bar 32 -- bell-led with displaced snare
tb = 128.0
for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
    h(tb + p, BELL, 88 + (8 if p in (0.0, 2.0) else 0))
for p in (0.75, 1.5, 2.25, 3.0):
    h(tb + p, SNARE, 100)
h(tb + 3.5, SNARE, 34)
h(tb + 0.0, KICK, 112)
h(tb + 2.5, KICK, 106)

# bar 33 -- doubles down the kit
run16(132.0, [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM, TOM_L, TOM_L,
              TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM],
      v0=94, v1=116, kick_beats=(0.0, 2.0), kv=108)

# bar 34 -- snare/tom see-saw, rising
tb = 136.0
for j in range(16):
    nt = SNARE if (j % 2 == 0) else TOM_H
    h(tb + j * 0.25, nt, 78 + 2.5 * j + (14 if j % 4 == 0 else 0))
h(tb + 0.0, KICK, 112)
h(tb + 2.0, KICK, 110)

# bar 35 -- tumble into the breath
tb = 140.0
fill = [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM,
        TOM_L, TOM_L, TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_FH, TOM_FL]
for j, nt in enumerate(fill):
    h(tb + j * 0.25, nt, 92 + 2 * j)
h(tb + 0.0, KICK, 112)
h(tb + 1.0, KICK, 106)
h(tb + 2.0, KICK, 110)
h(tb + 3.0, KICK, 108)

# ==========================================================================
# 8.  BREATH  (bars 36-39) -- space, then a roll that rebuilds
# ==========================================================================
tb = 144.0
h(tb + 0.0, SPLASH, 88); h(tb + 0.0, KICK, 92)
h(tb + 1.0, RIM, 70)
h(tb + 2.0, HHP, 60)
h(tb + 3.0, RIM, 74)
h(tb + 3.5, SNARE, 30)

tb = 148.0
h(tb + 0.0, HHP, 62)
h(tb + 0.5, HH, 52)
h(tb + 1.0, RIM, 72)
h(tb + 2.0, SNARE, 88)
h(tb + 2.75, SNARE, 32)
h(tb + 3.0, KICK, 78)

tb = 152.0
h(tb + 0.0, RIDE, 74)
h(tb + 1.0, SNARE, 92)
h(tb + 1.5, RIM, 60)
h(tb + 2.0, RIDE, 78)
h(tb + 3.0, SNARE, 96)
h(tb + 3.25, SNARE, 40)
h(tb + 3.5, SNARE, 44)
h(tb + 3.75, SNARE, 60)

# bar 39 -- crescendo roll back up to the peak
tb = 156.0
for j in range(16):
    h(tb + j * 0.25, SNARE, 60 + 3 * j)
h(tb + 0.0, KICK, 90)
h(tb + 2.0, KICK, 96)

# ==========================================================================
# 9.  PEAK  (bars 40-47)
# ==========================================================================
h(160.0, CRASH, 114)
h(160.0, KICK, 118)
motifA(160.0, v=92, ride_note=RIDE, kicks=(1.75, 2.5), ghosts=(2.75, 3.75))

run16(164.0, [SNARE, TOM_H, SNARE, TOM_HM, SNARE, TOM_LM, SNARE, TOM_L,
              SNARE, TOM_FH, SNARE, TOM_FL, TOM_FL, TOM_FH, TOM_L, TOM_LM],
      v0=96, v1=118, kick_beats=(0.0, 2.0), kv=110)

# bar 42 -- bell and snare dialogue
tb = 168.0
for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
    h(tb + p, BELL, 90 + (8 if p in (0.0, 2.0) else 0))
for p in (0.75, 1.25, 2.75, 3.25):
    h(tb + p, SNARE, 98)
for p in (0.25, 1.75, 3.75):
    h(tb + p, SNARE, 32)
h(tb + 0.0, KICK, 108)
h(tb + 2.5, KICK, 102)

run16(172.0, [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM, TOM_L, TOM_L,
              TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_FH, TOM_FH, TOM_L, TOM_L],
      v0=96, v1=120, kick_beats=(0.0, 2.0), kv=110)

h(176.0, CRASH2, 110)
h(176.0, KICK, 116)
motifA(176.0, v=94, ride_note=BELL, kicks=(1.5, 2.5), ghosts=(2.75, 3.5))

# bar 45 -- ride with ghost snare filling every hole
tb = 180.0
for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
    h(tb + p, RIDE, 86 + (8 if p in (0.0, 1.0, 2.0, 3.0) else 0))
for p in (0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75):
    h(tb + p, SNARE, 58)
h(tb + 1.0, SNARE, 108)
h(tb + 3.0, SNARE, 110)
h(tb + 0.0, KICK, 110)
h(tb + 1.5, KICK, 100)
h(tb + 2.5, KICK, 104)

run16(184.0, [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, SNARE, SNARE,
              TOM_LM, TOM_LM, TOM_L, TOM_L, TOM_FH, TOM_FH, TOM_FL, TOM_FL],
      v0=100, v1=122, kick_beats=(0.0, 1.0, 2.0, 3.0), kv=108)

# bar 47 -- big fill that resolves onto the restatement
tb = 188.0
fill = [TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE,
        TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, TOM_FL, TOM_FL]
for j, nt in enumerate(fill):
    h(tb + j * 0.25, nt, 96 + 2 * j)
h(tb + 0.0, KICK, 112)
h(tb + 2.0, KICK, 110)

# ==========================================================================
# 10. MOTIF A RETURNS  (bars 48-53) -- home, but with new clothes
# ==========================================================================
h(192.0, CRASH, 104)
h(192.0, KICK, 108)
motifA(192.0, v=84, ride_note=RIDE, kicks=(1.75, 2.5), ghosts=(2.75, 3.75))

motifA(196.0, v=82, ride_note=RIDE, kicks=(0.0, 1.25, 2.5), ghosts=(3.75,))

# bar 50 -- hat groove, snare on every beat
tb = 200.0
for p in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
    h(tb + p, HH, 78 + (8 if p in (0.0, 1.0, 2.0, 3.0) else 0))
h(tb + 0.0, KICK, 104)
h(tb + 1.0, SNARE, 108)
h(tb + 2.0, SNARE, 106)
h(tb + 3.0, SNARE, 110)
h(tb + 2.5, KICK, 96)
h(tb + 3.5, KICK, 98)
h(tb + 1.75, SNARE, 34)
h(tb + 0.75, SNARE, 32)

motifA(204.0, v=80, ride_note=BELL, kicks=(0.0, 1.75, 2.5), ghosts=(2.75, 3.75))
h(207.00, SNARE, 92)
h(207.25, SNARE, 74)
h(207.50, SNARE, 96)
h(207.75, SNARE, 76)

# bar 52 -- groove then toms
tb = 208.0
h(tb + 0.0, HH, 80); h(tb + 0.5, HH, 66)
h(tb + 1.0, HH, 82); h(tb + 1.5, HH, 68)
h(tb + 0.0, KICK, 102)
h(tb + 1.0, SNARE, 106)
h(tb + 2.0, TOM_H, 96);  h(tb + 2.5, TOM_HM, 98)
h(tb + 3.0, TOM_LM, 100); h(tb + 3.5, TOM_L, 102)
h(tb + 2.0, KICK, 96)

run16(212.0, [TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL, TOM_FL, TOM_FH,
              TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE, TOM_LM, TOM_FL],
      v0=92, v1=112, kick_beats=(0.0, 2.0), kv=104)

# ==========================================================================
# 11. FINALE  (bars 54-57) -- the last run, and a hit that lands
# ==========================================================================
run16(216.0, [SNARE, TOM_H, SNARE, TOM_HM, SNARE, TOM_LM, SNARE, TOM_L,
              SNARE, TOM_FH, SNARE, TOM_FL, SNARE, SNARE, TOM_LM, TOM_FL],
      v0=88, v1=108, kick_beats=(0.0, 1.0, 2.0, 3.0), kv=100)

run16(220.0, [TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, TOM_HM, TOM_LM,
              TOM_L, TOM_FH, TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H],
      v0=92, v1=112, kick_beats=(0.0, 2.0), kv=104)

# bar 56 -- the fill that gives the last bar its weight
tb = 224.0
for p, nt, v in [(0.00, SNARE, 96), (0.50, SNARE, 80),
                 (1.00, TOM_H, 100), (1.50, TOM_H, 84),
                 (2.00, TOM_HM, 104), (2.25, TOM_HM, 86),
                 (2.50, TOM_LM, 106), (2.75, TOM_LM, 88),
                 (3.00, TOM_L, 108), (3.25, TOM_L, 90),
                 (3.50, TOM_FH, 112), (3.75, TOM_FL, 120)]:
    h(tb + p, nt, v)
h(tb + 0.0, KICK, 110)
h(tb + 2.0, KICK, 112)

# bar 57 -- THE hit.  Crash flam over the bass drum, then let it ring.
h(228.000, CRASH, 127)
h(228.000, KICK, 127)
h(228.125, CRASH2, 112)
h(228.125, RIDE, 96)

# ==========================================================================
# 12. HUMANISE  -- the hands, not the grid
# ==========================================================================
# smooth per-bar drift: phrases lean forward / hold back, never by much
drift = [0.0] * NBARS
for b in range(1, NBARS):
    drift[b] = max(-14.0, min(14.0, drift[b - 1] * 0.55 + rng.uniform(-7.0, 7.0)))

events = []   # (absolute_tick, Message)
for t_beats, note, vel in NOTES:
    bar = min(NBARS - 1, int(t_beats // 4))
    tick = t_beats * PPQ + drift[bar] + rng.uniform(-4.0, 4.0)
    tick = max(0, int(round(tick)))
    v = int(round(max(1.0, min(127.0, vel + rng.uniform(-5.0, 5.0)))))
    events.append((tick, Message('note_on', channel=CH, note=note, velocity=v)))

# --- hard guarantee: two hands, two feet -----------------------------------
groups = defaultdict(list)
for tick, msg in events:
    groups[tick].append(msg)

final = []
for tick in sorted(groups):
    seen = set()
    uniq = []
    for m in groups[tick]:
        if m.note in seen:
            continue
        seen.add(m.note)
        uniq.append(m)
    hands = sorted((m for m in uniq if m.note in HANDS), key=lambda m: -m.velocity)[:2]
    feet = sorted((m for m in uniq if m.note in FEET), key=lambda m: -m.velocity)[:2]
    for m in sorted(hands + feet, key=lambda m: m.note):
        final.append((tick, m))

# ==========================================================================
# 13. TEMPO MAP  -- shaped so the whole solo lasts exactly two minutes
# ==========================================================================
BAR_BPM = [
    # bars 0-7   intro
    96, 97, 98, 99, 100, 100, 101, 102,
    # bars 8-13  development
    104, 104, 105, 105, 106, 106,
    # bars 14-21 toms / doubles / snare feature
    108, 108, 109, 110, 110, 111, 112, 112,
    # bars 22-29 build
    113, 114, 115, 116, 117, 118, 119, 120,
    # bars 30-35 climax
    122, 124, 126, 128, 130, 132,
    # bars 36-39 breath
    132, 126, 120, 116,
    # bars 40-47 peak
    120, 124, 128, 132, 136, 138, 140, 142,
    # bars 48-53 restatement
    140, 136, 132, 128, 124, 120,
    # bars 54-57 finale
    116, 112, 108, 96,
]
assert len(BAR_BPM) == NBARS

_total = sum(4 * 60.0 / b for b in BAR_BPM)
_scale = _total / 120.0                     # normalise to exactly 2:00
BAR_BPM = [b * _scale for b in BAR_BPM]

# ==========================================================================
# 14. WRITE THE FILE
# ==========================================================================
mid = MidiFile(type=1, ticks_per_beat=PPQ)

conductor = MidiTrack()
mid.tracks.append(conductor)
conductor.append(MetaMessage('track_name', name='Conductor', time=0))
conductor.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
t_last = 0
for b, bpm in enumerate(BAR_BPM):
    tick = b * 4 * PPQ
    conductor.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm), time=tick - t_last))
    t_last = tick
conductor.append(MetaMessage('end_of_track', time=NBARS * 4 * PPQ - t_last))

drums = MidiTrack()
mid.tracks.append(drums)
drums.append(MetaMessage('track_name', name='Drum Solo', time=0))

last = 0
for tick, msg in final:
    msg.time = tick - last
    last = tick
    drums.append(msg)

# keep the file exactly two minutes long even after the last stroke
end_tick = NBARS * 4 * PPQ
drums.append(MetaMessage('text', text='', time=end_tick - last))
drums.append(MetaMessage('end_of_track', time=0))

mid.save('solo.mid')

print('wrote solo.mid  (%.1f s, %d strokes)' % (_total, len(NOTES)))
