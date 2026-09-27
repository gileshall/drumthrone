#!/usr/bin/env python3
"""
drum_solo.py

Generates "solo.mid": a ~2 minute General MIDI drum solo on channel 10
(GM percussion).  Deterministic: identical bytes on every run.

Musical design
--------------
* Motif A : the 3-3-2 cell (hits on 0, 0.75, 1.5 in a 2-beat unit) -
  stated on rim/snare/floor tom, then moved around the kit, inverted,
  augmented, and brought back at the climax.
* Motif B : 16th-note single-stroke runs that travel down the toms.
* Motif C : snare rolls that swell from pp to ff and resolve on a crash.
* Sections: intro, groove, fill, breakdown (soft), roll build (with
  accelerando), full groove, tom feature, climax, finale.
* Timing is humanised note-by-note plus a slow phrase-level push/drag,
  so nothing sits on the quantised grid.
* Voices are always <= 2 hands and <= 2 feet at any instant.
"""

import math
import random

import mido

random.seed(20240517)

TPB = 480           # ticks per quarter note
CH = 9              # MIDI channel 10 (zero based)

# ------------------------------------------------------------------
# General MIDI percussion
# ------------------------------------------------------------------
KICK   = 36
SNARE  = 38
RIM    = 37
HH     = 42         # closed hi-hat
HHO    = 46         # open hi-hat
HHP    = 44         # pedal hi-hat
RIDE   = 51
BELL   = 53
CRASH  = 49
CRASH2 = 57
SPLASH = 55
CHINA  = 52
T_HI   = 50
T_MHI  = 48
T_MID  = 47
T_LO   = 45
T_FLH  = 43
T_FLL  = 41
TAMB   = 54
COW    = 56
CG_H   = 63
CG_L   = 64
CLAVE  = 75
WB_H   = 76
WB_L   = 77

TOMS = [T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL]

# ------------------------------------------------------------------
# event buffer
# ------------------------------------------------------------------
EV = []


def add(t, n, v, d=0.12, limb='h'):
    EV.append([float(t), int(n), int(max(1, min(127, round(v)))),
               float(d), limb])


def H(t, n, v, d=0.12):
    add(t, n, v, d, 'h')


def F(t, n, v, d=0.12):
    add(t, n, v, d, 'f')


# ==================================================================
# tempo map -- one entry per bar (4/4).  The pulse surges and settles.
# ==================================================================
tempos = (
    [112] * 8                                   # bars  0- 7  intro
    + [120] * 8                                 # bars  8-15  groove A
    + [124] * 4                                 # bars 16-19  big fill
    + [116, 116, 117, 118, 118, 119, 120, 120]  # bars 20-27  breakdown
    + [120, 121, 123, 125, 127, 129, 131, 132]  # bars 28-35  roll build
    + [132, 132, 133, 134, 134, 135, 136, 136]  # bars 36-43  groove B
    + [138, 138, 140, 140]                      # bars 44-47  tom feature
    + [144] * 8                                 # bars 48-55  climax
    + [138] * 7 + [138]                         # bars 56-63  finale
)

bar_t = []
_t = 0.0
for _bpm in tempos:
    bar_t.append(_t)
    _t += 4.0 * 60.0 / _bpm
TOTAL_SEC = _t

# ==================================================================
# helper grooves / figures
# ==================================================================
KICK_PATS = [
    (0.0, 1.5, 2.5),
    (0.0, 0.75, 2.5),
    (0.0, 1.5, 2.0, 3.5),
    (0.0, 0.75, 2.25, 3.0),
    (0.0, 2.0, 2.75),
    (0.0, 1.25, 2.0, 3.25),
    (0.0, 1.5, 3.0, 3.75),
    (0.0, 0.75, 1.5, 2.5, 3.5),
]

GHOST_PATS = [
    (2.75,),
    (1.75, 3.75),
    (2.5, 3.25),
    (0.75, 2.75),
    (1.75,),
    (2.75, 3.75),
    (0.5, 3.25),
    (1.25, 3.5),
]


def groove(bb, energy=1.0, ki=0, gi=0, open_hat=None, crash=None):
    """One bar of time: hats, kick pattern, backbeat and ghost notes."""
    if crash is not None:
        H(bb, crash, 102 * energy, 1.8)
    for i in range(8):
        n = HH
        v = (74 if i % 2 == 0 else 52) * energy
        if open_hat is not None and i == open_hat:
            n = HHO
            v = 74 * energy
        H(bb + i * 0.5, n, v, 0.1)
    for k in KICK_PATS[ki]:
        F(bb + k, KICK, 96 * energy)
    H(bb + 1.0, SNARE, 90 * energy)
    H(bb + 3.0, SNARE, 94 * energy)
    for g in GHOST_PATS[gi]:
        H(bb + g, SNARE, 30 * energy + random.uniform(-3, 6))


def snare_roll(t0, dur, v0, v1, step=0.125, drum=SNARE):
    """A swelling roll; light double-stroke accent on every other stroke."""
    n = int(round(dur / step))
    for i in range(n):
        u = i / max(1, n - 1)
        v = v0 + (v1 - v0) * u
        if i % 2 == 0:
            v += 4
        H(t0 + i * step, drum, v, step * 0.9)


# ==================================================================
# 1. INTRO -- bars 0-7
# ==================================================================
# bar 0 : space
H(0.0, BELL, 76, 1.2)
F(0.0, KICK, 88)
H(1.0, RIDE, 52)
H(2.0, BELL, 66, 0.6)
F(2.0, KICK, 70)
H(3.0, SNARE, 48)
H(3.5, RIDE, 46)

# bar 1 : ride quarters
bb = 4.0
for i in range(4):
    H(bb + i, RIDE, 58 if i % 2 == 0 else 46)
F(bb, KICK, 86)
F(bb + 2.5, KICK, 74)
H(bb + 1.0, SNARE, 64)
H(bb + 2.75, SNARE, 30)
H(bb + 3.0, SNARE, 68)

# bar 2 : 8th hats arrive
bb = 8.0
for i in range(8):
    H(bb + i * 0.5, HH, 64 if i % 2 == 0 else 46, 0.1)
F(bb, KICK, 90)
F(bb + 0.75, KICK, 62)
F(bb + 2.5, KICK, 76)
H(bb + 1.0, SNARE, 84)
H(bb + 3.0, SNARE, 88)
H(bb + 2.75, SNARE, 32)

# bar 3 : variation of bar 2
bb = 12.0
for i in range(8):
    H(bb + i * 0.5, HH, 68 if i % 2 == 0 else 48, 0.1)
F(bb, KICK, 92)
F(bb + 1.5, KICK, 66)
F(bb + 2.0, KICK, 78)
H(bb + 1.0, SNARE, 88)
H(bb + 3.0, SNARE, 92)
H(bb + 1.75, SNARE, 30)
H(bb + 3.5, SNARE, 34)
H(bb + 3.75, SNARE, 50)

# bars 4-5 : MOTIF A stated (3-3-2) with ride underneath
for b in (4, 5):
    bb = 4.0 * b
    for i in range(8):
        H(bb + i * 0.5, RIDE, 56 if i % 2 == 0 else 42, 0.1)
    F(bb, KICK, 90)
    F(bb + 2.0, KICK, 80)
    for k in (0.0, 2.0):
        add(bb + k, RIM, 80)
        add(bb + k + 0.75, SNARE, 44)
        add(bb + k + 1.5, T_LO if b == 4 else T_MID, 94)

# bar 6 : motif A moved to the toms
bb = 24.0
for i in range(4):
    H(bb + i, RIDE, 56)
F(bb, KICK, 92)
F(bb + 2.0, KICK, 84)
add(bb + 0.0, RIM, 84)
add(bb + 0.75, SNARE, 48)
add(bb + 1.5, T_MID, 98)
add(bb + 2.0, RIM, 82)
add(bb + 2.75, SNARE, 50)
add(bb + 3.5, T_FLH, 100)
H(bb + 3.75, SNARE, 56)

# bar 7 : single strokes run down the kit, crescendo
bb = 28.0
fill = [SNARE, SNARE, T_HI, T_HI, T_MHI, T_MHI, T_MID, T_MID,
        T_LO, T_LO, T_FLH, T_FLH, T_FLL, T_FLL, SNARE, T_LO]
for i, n in enumerate(fill):
    H(bb + i * 0.25, n, 58 + 58 * i / 15.0, 0.1)
F(bb, KICK, 94)
F(bb + 2.0, KICK, 88)

# ==================================================================
# 2. GROOVE A -- bars 8-15
# ==================================================================
groove(32.0, 1.00, ki=0, gi=0, crash=CRASH)
groove(36.0, 1.00, ki=1, gi=1)
groove(40.0, 1.02, ki=2, gi=2)
groove(44.0, 1.02, ki=3, gi=3, open_hat=7)
groove(48.0, 1.04, ki=4, gi=4)
groove(52.0, 1.06, ki=5, gi=5, crash=CRASH2)

# bar 14 : motif A threaded through the groove
bb = 56.0
for i in range(8):
    H(bb + i * 0.5, HH, 76 if i % 2 == 0 else 54, 0.1)
F(bb, KICK, 98)
F(bb + 2.5, KICK, 88)
H(bb + 1.0, SNARE, 90)
H(bb + 3.0, SNARE, 94)
add(bb + 0.75, T_MID, 86)
add(bb + 1.5, T_HI, 90)
add(bb + 2.0, T_HI, 80)
add(bb + 2.75, SNARE, 36)
add(bb + 3.25, T_MID, 92)
add(bb + 3.75, T_LO, 88)

# bar 15 : fill carrying into bar 16
bb = 60.0
fill = [SNARE, SNARE, T_HI, T_HI, T_MHI, T_MHI, T_MID, T_MID,
        T_LO, T_LO, T_FLH, T_FLH, T_FLL, T_FLL, T_FLH, T_MID]
for i, n in enumerate(fill):
    H(bb + i * 0.25, n, 70 + 45 * i / 15.0, 0.1)
F(bb, KICK, 98)
F(bb + 1.0, KICK, 82)
F(bb + 2.0, KICK, 90)

# ==================================================================
# 3. BIG FILL -- bars 16-19
# ==================================================================
bb = 64.0
H(bb, CRASH2, 92, 1.5)
seq = [T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL, T_FLH, T_LO]
for i, n in enumerate(seq):
    H(bb + i * 0.5, n, 82 + 20 * i / 7.0)
F(bb, KICK, 98)
F(bb + 2.0, KICK, 92)

bb = 68.0
seq = [SNARE, SNARE, SNARE, SNARE, T_MID, T_MID, T_LO, T_LO,
       T_FLH, T_FLH, T_FLL, T_FLL, T_FLH, T_LO, T_MID, T_HI]
for i, n in enumerate(seq):
    H(bb + i * 0.25, n, 74 + 40 * i / 15.0, 0.1)
F(bb, KICK, 98)
F(bb + 2.0, KICK, 90)

bb = 72.0
seq2 = [T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL, SNARE, SNARE] * 2
for i, n in enumerate(seq2):
    H(bb + i * 0.25, n, 78 + 32 * (i % 8) / 7.0, 0.1)
F(bb, KICK, 100)
F(bb + 1.5, KICK, 86)
F(bb + 3.0, KICK, 92)

bb = 76.0
for i in range(32):
    u = i / 31.0
    H(bb + i * 0.125, SNARE, 56 + 62 * u, 0.09)
    if i % 8 == 0:
        F(bb + i * 0.125, KICK, 84 + 24 * u)

# ==================================================================
# 4. BREAKDOWN -- bars 20-27
# ==================================================================
# bar 20 : crash, then air
bb = 80.0
H(bb, CRASH, 110, 2.5)
F(bb, KICK, 104)
H(bb + 2.0, RIM, 56)
H(bb + 3.0, RIM, 50)
F(bb + 3.0, HHP, 58)

# bars 21-23 : ride bell and side stick, quietly growing
for j, b in enumerate(range(21, 24)):
    bb = 4.0 * b
    e = 0.80 + 0.06 * j
    for i in range(4):
        H(bb + i, BELL, (68 if i % 2 == 0 else 54) * e, 0.5)
    F(bb + 1.0, HHP, 58 * e)
    F(bb + 3.0, HHP, 58 * e)
    H(bb + 1.0, RIM, 64 * e)
    H(bb + 3.0, RIM, 68 * e)
    if j >= 1:
        H(bb + 2.75, SNARE, 30 * e)
        F(bb + 2.5, KICK, 62 * e)
    if j >= 2:
        H(bb + 1.75, SNARE, 28 * e)
        H(bb + 3.5, SNARE, 32 * e)
        F(bb + 0.75, KICK, 60 * e)

# colour: a soft wood block answer
H(90.0 + 2.0, WB_H, 50, 0.4)
H(98.0 + 3.5, CLAVE, 46, 0.3)

# bars 24-26 : the pulse comes back
for j, b in enumerate(range(24, 27)):
    bb = 4.0 * b
    e = 0.90 + 0.10 * j
    for i in range(8):
        H(bb + i * 0.5, HH, (68 if i % 2 == 0 else 46) * e, 0.1)
    H(bb + 1.0, SNARE, 74 * e)
    H(bb + 3.0, SNARE, 78 * e)
    F(bb + 0.0, KICK, 84 * e)
    F(bb + 2.5, KICK, 76 * e)
    H(bb + 2.75, SNARE, 30 * e)
    H(bb + 3.75, SNARE, 36 * e)

# bar 27 : crescendo singles into the roll section
bb = 108.0
for i in range(16):
    u = i / 15.0
    H(bb + i * 0.25, SNARE, 54 + 56 * u, 0.1)
    if i % 4 == 0:
        F(bb + i * 0.25, KICK, 78 + 26 * u)

# ==================================================================
# 5. ROLL BUILD (accelerando) -- bars 28-35
# ==================================================================
# bar 28
bb = 112.0
for i in range(8):
    H(bb + i * 0.5, HH, 72 if i % 2 == 0 else 50, 0.1)
F(bb, KICK, 96)
F(bb + 1.5, KICK, 84)
H(bb + 1.0, SNARE, 88)
snare_roll(bb + 2.0, 2.0, 62, 92)
F(bb + 3.0, KICK, 88)

# bar 29
bb = 116.0
F(bb, KICK, 96)
H(bb + 0.0, SNARE, 94)
H(bb + 0.5, SNARE, 52)
H(bb + 1.0, SNARE, 88)
H(bb + 1.5, SNARE, 50)
snare_roll(bb + 2.0, 2.0, 66, 100)
F(bb + 3.5, KICK, 86)

# bars 30-33 : rolls growing, feet pulsing
for j, bb in enumerate([120.0, 124.0, 128.0, 132.0]):
    lo = 56 + 8 * j
    hi = 92 + 8 * j
    snare_roll(bb, 4.0, lo, hi)
    F(bb + 0.0, KICK, 92 + 4 * j)
    F(bb + 2.0, KICK, 88 + 4 * j)
    if j >= 1:
        F(bb + 3.0, KICK, 84 + 4 * j)
    if j >= 2:
        H(bb + 1.25, T_MID, 96)
        H(bb + 3.25, T_LO, 98)

# bar 34
bb = 136.0
snare_roll(bb, 3.0, 74, 112)
F(bb, KICK, 100)
F(bb + 2.0, KICK, 96)
H(bb + 3.0, T_FLL, 104)
H(bb + 3.5, T_FLH, 104)

# bar 35 : the big swell
bb = 140.0
snare_roll(bb, 3.5, 70, 120)
F(bb, KICK, 104)
F(bb + 2.0, KICK, 100)
H(bb + 3.5, T_LO, 110)
H(bb + 3.75, T_FLL, 112)

# ==================================================================
# 6. GROOVE B -- bars 36-43
# ==================================================================
groove(144.0, 1.10, ki=2, gi=1, crash=CRASH)
groove(148.0, 1.10, ki=5, gi=5)
groove(152.0, 1.12, ki=3, gi=6, open_hat=3)
H(156.0 + 3.75, TAMB, 62, 0.4)          # colour
groove(156.0, 1.12, ki=7, gi=2)
groove(160.0, 1.14, ki=1, gi=3, crash=CRASH2)
groove(164.0, 1.14, ki=6, gi=7)

bb = 168.0
seq = [T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL, T_FLH, T_LO]
for i, n in enumerate(seq):
    H(bb + i * 0.5, n, 88 + 20 * i / 7.0)
F(bb, KICK, 100)
F(bb + 2.0, KICK, 92)
H(bb + 1.0, SNARE, 96)
H(bb + 3.0, SNARE, 100)

bb = 172.0
for i in range(16):
    n = [SNARE, T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL, T_FLH][i % 8]
    H(bb + i * 0.25, n, 84 + 30 * (i % 8) / 7.0, 0.1)
F(bb, KICK, 102)
F(bb + 1.5, KICK, 92)
F(bb + 3.0, KICK, 96)

# ==================================================================
# 7. TOM FEATURE -- bars 44-47
# ==================================================================
bb = 176.0
order = [T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL, T_FLH, T_MID]
for i in range(16):
    n = order[i % 8]
    H(bb + i * 0.25, n, 92 - 6 * (i % 2), 0.1)
F(bb, KICK, 100)
F(bb + 1.5, KICK, 88)
F(bb + 3.0, KICK, 94)

bb = 180.0
ord8 = [T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL, T_FLH, T_MID]
t = bb
for r in range(2):
    for n in ord8:
        H(t, n, 92 - 4 * r)
        H(t + 0.125, n, 70 - 4 * r)
        t += 0.25
F(bb, KICK, 102)
F(bb + 2.0, KICK, 96)

bb = 184.0
for i in range(16):
    if i % 4 == 0:
        n = SNARE
    elif i % 2 == 0:
        n = T_HI
    else:
        n = T_MID
    H(bb + i * 0.25, n, 84 + (18 if i % 4 == 0 else 0), 0.1)
F(bb, KICK, 102)
F(bb + 2.0, KICK, 96)

bb = 188.0
for i in range(32):
    u = i / 31.0
    H(bb + i * 0.125, SNARE, 66 + 52 * u, 0.09)
    if i % 8 == 0:
        F(bb + i * 0.125, KICK, 90 + 20 * u)

# ==================================================================
# 8. CLIMAX -- bars 48-55
# ==================================================================
groove(192.0, 1.18, ki=2, gi=1, crash=CRASH)
groove(196.0, 1.18, ki=7, gi=5)
groove(200.0, 1.20, ki=3, gi=6, open_hat=3)
groove(204.0, 1.20, ki=1, gi=2, crash=CRASH2)
groove(208.0, 1.22, ki=4, gi=4)
groove(212.0, 1.22, ki=5, gi=7)

# bar 54 : motif A back, at full voice
bb = 216.0
for i in range(8):
    H(bb + i * 0.5, HH, 82 if i % 2 == 0 else 58, 0.1)
F(bb, KICK, 104)
F(bb + 2.5, KICK, 96)
H(bb + 1.0, SNARE, 100)
H(bb + 3.0, SNARE, 104)
add(bb + 0.75, T_MID, 94)
add(bb + 1.75, SNARE, 36)
add(bb + 2.25, T_HI, 92)
add(bb + 2.75, SNARE, 38)
add(bb + 3.25, T_LO, 96)
add(bb + 3.75, T_FLL, 98)

# bar 55 : tumble down the toms into the finale
bb = 220.0
for i in range(16):
    n = [T_HI, T_MHI, T_MID, T_LO, T_FLH, T_FLL, T_FLH, T_MID][i % 8]
    H(bb + i * 0.25, n, 96 - 8 * (i % 2), 0.1)
F(bb, KICK, 106)
F(bb + 2.0, KICK, 100)
H(bb + 1.0, SNARE, 104)
H(bb + 3.0, SNARE, 108)

# ==================================================================
# 9. FINALE -- bars 56-63
# ==================================================================
bb = 224.0
H(bb, CRASH, 116, 2.0)
F(bb, KICK, 112)
H(bb + 1.0, SNARE, 108)
H(bb + 2.0, RIM, 70)
H(bb + 2.5, SNARE, 40)
H(bb + 3.0, SNARE, 104)
F(bb + 2.0, KICK, 100)
H(bb + 3.75, T_MID, 88)

groove(228.0, 1.15, ki=5, gi=5)
groove(232.0, 1.18, ki=7, gi=2, crash=CRASH2)
H(236.0 + 1.75, TAMB, 66, 0.4)
groove(236.0, 1.18, ki=3, gi=6, open_hat=3)
groove(240.0, 1.20, ki=1, gi=1)

bb = 244.0
seq = [SNARE, SNARE, T_HI, T_HI, T_MHI, T_MHI, T_MID, T_MID,
       T_LO, T_LO, T_FLH, T_FLH, T_FLL, T_FLL, T_HI, T_MID]
for i, n in enumerate(seq):
    H(bb + i * 0.25, n, 88 + 32 * i / 15.0, 0.1)
F(bb, KICK, 108)
F(bb + 2.0, KICK, 102)

bb = 248.0
for i in range(16):
    u = i / 15.0
    n = SNARE if i % 2 == 0 else T_MID
    H(bb + i * 0.25, n, 84 + 40 * u, 0.1)
F(bb, KICK, 108)
F(bb + 2.0, KICK, 104)
F(bb + 3.0, KICK, 100)

# ---- the last hit, landed, not faded ------------------------------
FINAL = 252.0
H(FINAL - 0.07, SNARE, 58, 0.06)     # flam grace
H(FINAL, CRASH, 120, 3.0)
H(FINAL, SNARE, 112, 0.5)
F(FINAL, KICK, 116)

# ==================================================================
# humanise: phrase-level push/drag + per-note jitter + dynamics
# ==================================================================
for e in EV:
    t = e[0]
    drift = (0.018 * math.sin(t * 0.11) +
             0.010 * math.sin(t * 0.037 + 1.2))
    t = t + drift + random.uniform(-0.017, 0.017)
    if t < 0.0:
        t = 0.0
    e[0] = t
    e[2] = int(max(1, min(127, e[2] * random.uniform(0.93, 1.07))))

# ==================================================================
# write the MIDI file
# ==================================================================
mid = mido.MidiFile(ticks_per_beat=TPB)
track = mido.MidiTrack()
mid.tracks.append(track)

msgs = []
counter = 0


def push(tick, kind, msg):
    global counter
    msgs.append((int(tick), kind, counter, msg))
    counter += 1


push(0, -1, mido.MetaMessage('track_name', name='Drum Solo'))
push(0, -1, mido.MetaMessage('time_signature', numerator=4, denominator=4))

prev_bpm = None
for b, bpm in enumerate(tempos):
    if bpm != prev_bpm:
        push(4 * b * TPB, -1,
             mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
        prev_bpm = bpm

for (t, n, v, d, limb) in EV:
    on = int(round(t * TPB))
    if on < 0:
        on = 0
    off = on + max(8, int(round(d * TPB)))
    push(on, 2, mido.Message('note_on', channel=CH, note=n, velocity=v))
    push(off, 1, mido.Message('note_off', channel=CH, note=n, velocity=0))

msgs.sort(key=lambda x: (x[0], x[1], x[2]))

last_tick = 0
for tick, _kind, _idx, msg in msgs:
    delta = tick - last_tick
    if delta < 0:
        delta = 0
    msg.time = delta
    track.append(msg)
    last_tick = tick

mid.save('solo.mid')

print("wrote solo.mid : %d events, %.1f seconds, %d bars"
      % (len(EV), TOTAL_SEC, len(tempos)))
