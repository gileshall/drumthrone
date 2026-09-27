#!/usr/bin/env python3
"""
drum_solo.py -- writes `solo.mid`: a ~2 minute General MIDI drum solo for
one drummer, on MIDI channel 10 (zero-based channel 9).

The output is byte-for-byte identical on every run: all "human" timing
comes from a small xorshift PRNG that is seeded with a constant.

Musical plan (4/4, tempo in beats):

    bars  0- 3   intro, tempo 100   -- motif A stated quietly
    bars  4-13   groove, tempo 112  -- motif A as a hook, fill out
    bars 14-25   development, 120   -- motif on toms, doubles, runs
    bars 26-37   doubles, 138       -- kit-wide runs, big build
    bars 38-46   climax, 150        -- crashes, motif at full voice
    bars 47-53   breakdown, 108     -- rim clicks, quietly building
    bars 54-60   final build 152->168
    bar  61      final unison hit, cymbals ring out
"""

from collections import defaultdict

from mido import Message, MidiFile, MidiTrack, MetaMessage

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
TPQ = 960                # ticks per quarter note
CH = 9                   # zero based -> MIDI channel 10

# General MIDI percussion note numbers
BD, BD2 = 36, 35                    # bass drum / acoustic bass drum
SD, RS = 38, 37                     # snare / side stick
HH, HHO, HHP = 42, 46, 44           # closed / open / pedal hi-hat
RD, RB = 51, 53                     # ride / ride bell
CR, CR2, SPL, CHN = 49, 57, 55, 52  # crashes, splash, china
T1, T2, T3, T4, F1, F2 = 50, 48, 47, 45, 43, 41   # toms, high -> low
CB, TAMB, CLV = 56, 54, 75          # colour
WBH, WBL = 76, 77

FEET = {35, 36, 44}
HANDS = set(range(35, 82)) - FEET

# ringing time, in beats
DUR = {
    CR: 1.8, CR2: 1.6, SPL: 0.8, CHN: 1.2,
    RD: 0.28, RB: 0.40, HH: 0.10, HHO: 0.55, HHP: 0.10,
    SD: 0.16, RS: 0.10,
    BD: 0.20, BD2: 0.20,
    T1: 0.30, T2: 0.30, T3: 0.30, T4: 0.35, F1: 0.40, F2: 0.45,
    CB: 0.25, TAMB: 0.25, CLV: 0.15, WBH: 0.12, WBL: 0.12,
}


# --------------------------------------------------------------------------
# tiny deterministic PRNG (xorshift64*), so output never depends on
# the platform's random module implementation
# --------------------------------------------------------------------------
class Rng:
    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFFFFFFFFFF or 0x9E3779B97F4A7C15

    def _next(self):
        x = self.s
        x ^= (x >> 12)
        x = (x ^ (x << 25)) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 27)
        self.s = x & 0xFFFFFFFFFFFFFFFF
        return (x * 0x2545F4914F6CDD1D) & 0xFFFFFFFFFFFFFFFF

    def uniform(self):
        return self._next() / 18446744073709551616.0

    def gauss(self, mu=0.0, sigma=1.0):
        # Irwin-Hall approximation of a normal deviate
        s = 0.0
        for _ in range(12):
            s += self.uniform()
        return mu + (s - 6.0) * sigma

    def choice(self, seq):
        return seq[int(self.uniform() * len(seq))]


rng = Rng(0x5EED1A7E)

ev = []          # [tick, note, velocity, duration_ticks]


def hit(t, note, vel, dur=None, push=0.0, sig=6.0):
    """Schedule a stroke at beat position `t`."""
    if vel <= 0:
        return
    tick = t * TPQ + push + rng.gauss(0.0, sig)
    if tick < 0.0:
        tick = 0.0
    if dur is None:
        dur = DUR.get(note, 0.25)
    ev.append([int(round(tick)), note,
               max(1, min(127, int(round(vel)))),
               max(30, int(dur * TPQ))])


# --------------------------------------------------------------------------
# motif A: a one bar sixteenth-note figure
#   1 . a   &   2      a  &
# --------------------------------------------------------------------------
MOTIF = [0.0, 0.75, 1.5, 2.0, 2.75, 3.5]

KICK_PATS = [
    [(0.0, 104), (2.5, 94)],
    [(0.0, 104), (1.5, 90), (2.5, 94)],
    [(0.0, 104), (0.75, 84), (2.5, 94)],
    [(0.0, 102), (2.5, 92), (3.5, 88)],
    [(0.0, 104), (1.75, 86), (2.5, 94)],
]


def groove(base, energy=1.0, hat=HH, bell=(), crash=False, open_hat=(),
           kick_pat=0, ghost=True, sig=6.0, push=0.0):
    """One bar of time keeping with ghost notes and a syncopated bass drum."""
    if crash:
        hit(base, CR, 108 * energy, sig=2.0, push=push)

    for e in range(8):
        off = e * 0.5
        if off in open_hat:
            hit(base + off, HHO, 68 * energy, sig=sig, push=push)
            continue
        n = RB if off in bell else hat
        v = (64 if e % 4 == 0 else 48) * energy
        hit(base + off, n, v, sig=sig, push=push)

    # backbeat, played just a hair behind the click
    hit(base + 1, SD, 100 * energy, sig=7.0, push=push + 2)
    hit(base + 3, SD, 106 * energy, sig=7.0, push=push + 2)

    if ghost:
        for off in (0.75, 2.75):
            hit(base + off, SD, rng.choice([26, 30, 34]) * energy,
                sig=11.0, push=push + 5)

    for off, v in KICK_PATS[kick_pat % len(KICK_PATS)]:
        hit(base + off, BD, v * energy, sig=4.0, push=push)


# ==========================================================================
# A. INTRO -- bars 0-3
# ==========================================================================
hit(0.0, CR, 116, sig=2.0)
hit(0.0, BD, 102, sig=3.0)
hit(1.0, HH, 54)
hit(2.0, HH, 60)
hit(3.0, HH, 52)

# bar 1 -- motif A, stated quietly on the snare
for off, v in zip(MOTIF, [86, 50, 98, 72, 42, 94]):
    hit(4 + off, SD, v, sig=8.0)
for q in (0, 1, 2, 3):
    hit(4 + q, HHP, 48, sig=5.0)

# bar 2 -- same motif, now with the bass drum and the hats
for off, v in zip(MOTIF, [98, 56, 108, 82, 48, 102]):
    hit(8 + off, SD, v, sig=8.0)
for off in (0.0, 1.5, 2.0):
    hit(8 + off, BD, 92, sig=4.0)
for e in range(8):
    hit(8 + e * 0.5, HH, 64 if e % 2 == 0 else 50, sig=5.0)

# bar 3 -- crescendo single strokes into the groove
for k in range(16):
    hit(12 + k * 0.25, SD, 42 + k * 3.5, sig=6.0, push=-4)
hit(12.0, BD, 96, sig=3.0)
hit(14.0, BD, 100, sig=3.0)
hit(15.0, BD, 102, sig=3.0)

# ==========================================================================
# B. GROOVE -- bars 4-13, tempo 112
# ==========================================================================
groove(16, crash=True, kick_pat=0)
groove(20, kick_pat=1)
groove(24, kick_pat=2, open_hat=(3.5,))
groove(28, kick_pat=3)

# bar 8 -- motif A as a hook over the time feel
base = 32
hit(base + 0.0, BD, 102, sig=3.0)
hit(base + 0.75, BD, 86, sig=4.0)
hit(base + 2.5, BD, 92, sig=4.0)
for e in range(8):
    hit(base + e * 0.5, HH, 64 if e % 4 == 0 else 48, sig=5.0)
for off, v in zip(MOTIF, [106, 54, 110, 78, 44, 102]):
    hit(base + off, SD, v, sig=7.0)

groove(36, bell=(0.0, 2.0), kick_pat=4)
groove(40, kick_pat=1, energy=1.03)

# bar 11 -- motif A answered on the toms
base = 44
hit(base + 0.0, BD, 102, sig=3.0)
hit(base + 2.0, BD, 96, sig=4.0)
hit(base + 3.5, BD, 90, sig=4.0)
for e in range(8):
    hit(base + e * 0.5, HH, 62 if e % 4 == 0 else 46, sig=5.0)
for off, n, v in zip(MOTIF, [T1, T1, T2, T1, T3, T2],
                     [102, 60, 108, 80, 52, 100]):
    hit(base + off, n, v, sig=7.0)

# bars 12-13 -- fill that carries into the next downbeat
base = 48
for i, n in enumerate([T1, T2, T3, T4, F1, F2, T4, F2]):
    hit(base + i * 0.5, n, 76 + i * 3, sig=7.0)
hit(base + 0.0, BD, 102, sig=3.0)
hit(base + 1.0, SD, 106, sig=5.0)
hit(base + 2.0, SD, 104, sig=5.0)
hit(base + 3.0, SD, 108, sig=5.0)

base = 52
seq2 = ([SD] * 4 + [T1] * 2 + [T2] * 2 + [T3] * 2 +
        [T4] * 2 + [F1] * 2 + [F2] * 2)
for k, n in enumerate(seq2):
    hit(base + k * 0.25, n, 54 + k * 4.2, sig=6.0, push=-5)
hit(base + 0.0, BD, 104, sig=3.0)
hit(base + 2.0, BD, 106, sig=3.0)

# ==========================================================================
# C. DEVELOPMENT -- bars 14-25, tempo 120
# ==========================================================================
groove(56, crash=True, kick_pat=0)
groove(60, kick_pat=2, energy=1.02)

# bar 16 -- motif A again, this time under the ride
base = 64
hit(base + 0.0, BD, 104, sig=3.0)
hit(base + 1.75, BD, 92, sig=4.0)
hit(base + 2.5, BD, 96, sig=4.0)
for e in range(8):
    hit(base + e * 0.5, RD, 66 if e % 4 == 0 else 50, sig=5.0)
for off, v in zip(MOTIF, [108, 56, 112, 80, 46, 104]):
    hit(base + off, SD, v, sig=7.0)

# bar 17 -- double strokes on the snare
base = 68
for k in range(16):
    v = 106 if k % 4 == 0 else (74 if k % 2 == 0 else 54)
    hit(base + k * 0.25, SD, v, sig=5.0)
hit(base + 0.0, BD, 104, sig=3.0)
hit(base + 2.0, BD, 100, sig=3.0)
hit(base + 3.5, BD, 96, sig=3.0)

groove(72, hat=RD, kick_pat=1)
groove(76, hat=RD, bell=(0.0, 1.5, 2.0, 3.5), kick_pat=3, energy=1.03)

# bars 20-21 -- motif broken into a call and an answer
base = 80
hit(base + 0.0, CR2, 96, sig=3.0)
hit(base + 0.0, BD, 106, sig=3.0)
hit(base + 0.75, SD, 52, sig=9.0)
hit(base + 1.5, T1, 96, sig=7.0)
hit(base + 2.5, BD, 92, sig=4.0)
hit(base + 2.75, SD, 44, sig=9.0)
hit(base + 3.0, SD, 100, sig=7.0)
hit(base + 3.5, HHO, 64, sig=5.0)

base = 84
hit(base + 0.75, SD, 50, sig=9.0)
hit(base + 1.5, T2, 100, sig=7.0)
hit(base + 2.0, BD, 100, sig=3.0)
hit(base + 2.75, SD, 46, sig=9.0)
hit(base + 3.5, T3, 104, sig=7.0)
hit(base + 3.5, BD, 90, sig=3.0)

# bars 22-23 -- singles up, then down, through the toms
base = 88
asc = [F2, F1, T4, T3, T2, T1]
for k in range(16):
    hit(base + k * 0.25, asc[k % 6], 92 if k % 4 == 0 else 68, sig=5.0)
hit(base + 0.0, BD, 104, sig=3.0)
hit(base + 2.0, BD, 100, sig=3.0)

base = 92
desc = [T1, T2, T3, T4, F1, F2]
for k in range(16):
    hit(base + k * 0.25, desc[k % 6], 96 if k % 4 == 0 else 70, sig=5.0)
hit(base + 0.0, BD, 100, sig=3.0)
hit(base + 2.0, BD, 102, sig=3.0)
hit(base + 3.5, BD, 98, sig=3.0)

# bars 24-25 -- fill into the fast section
base = 96
seqA = [SD, SD, T1, T1, T2, T2, T3, T3,
        T3, T4, T4, F1, F1, F2, F2, F2]
for k, n in enumerate(seqA):
    hit(base + k * 0.25, n, 78 + k * 2.5, sig=6.0)
hit(base + 0.0, BD, 102, sig=3.0)
hit(base + 2.0, BD, 104, sig=3.0)

base = 100
for k in range(32):
    n = SD if k < 16 else (T1 if k < 24 else T2)
    hit(base + k * 0.125, n, 60 + k * 2.0, sig=5.0, push=-6)
hit(base + 0.0, BD, 104, sig=3.0)
hit(base + 2.0, BD, 106, sig=3.0)

# ==========================================================================
# D. DOUBLES AND KIT-WIDE RUNS -- bars 26-37, tempo 138
# ==========================================================================
groove(104, crash=True, kick_pat=0, energy=1.03)
groove(108, kick_pat=2, energy=1.03)

# bar 28 -- motif A under the hats
base = 112
hit(base + 0.0, BD, 106, sig=3.0)
hit(base + 1.75, BD, 90, sig=4.0)
hit(base + 2.5, BD, 96, sig=4.0)
for e in range(8):
    hit(base + e * 0.5, HH, 66 if e % 4 == 0 else 50, sig=5.0)
for off, v in zip(MOTIF, [110, 58, 112, 84, 48, 106]):
    hit(base + off, SD, v, sig=7.0)

groove(116, open_hat=(2.5, 3.5), kick_pat=3, energy=1.04)

# bars 30-31 -- double strokes travelling around the kit
base = 120
pat = [SD, SD, T1, T1, T2, T2, T3, T3,
       T2, T2, T3, T3, T4, T4, F1, F1]
for k, n in enumerate(pat):
    hit(base + k * 0.25, n, 96 if k % 4 == 0 else 70, sig=5.0)
hit(base + 0.0, BD, 106, sig=3.0)
hit(base + 2.0, BD, 100, sig=3.0)

base = 124
pat2 = [F1, F1, T4, T4, T3, T3, T2, T2,
        T1, T1, T2, T2, SD, SD, SD, SD]
for k, n in enumerate(pat2):
    hit(base + k * 0.25, n, 98 if k % 4 == 0 else 72, sig=5.0)
hit(base + 0.0, BD, 104, sig=3.0)
hit(base + 3.5, BD, 100, sig=3.0)

groove(128, hat=RD, kick_pat=1, energy=1.05)

# bar 33 -- snare doubles with accents
base = 132
for k in range(16):
    v = 108 if k % 4 == 0 else (80 if k % 2 == 0 else 58)
    hit(base + k * 0.25, SD, v, sig=5.0)
hit(base + 0.0, BD, 106, sig=3.0)
hit(base + 2.0, BD, 102, sig=3.0)
hit(base + 3.0, BD, 98, sig=3.0)

# bars 34-37 -- the build
base = 136
for k in range(16):
    hit(base + k * 0.25, SD, 66 + k * 2.6, sig=5.0, push=-6)
hit(base + 0.0, BD, 106, sig=3.0)
hit(base + 2.0, BD, 108, sig=3.0)

base = 140
seq = [SD] * 4 + [T1] * 4 + [T2] * 4 + [T3] * 4
for k, n in enumerate(seq):
    hit(base + k * 0.25, n, 74 + k * 2.8, sig=5.0, push=-6)
hit(base + 0.0, BD, 108, sig=3.0)
hit(base + 2.0, BD, 108, sig=3.0)

base = 144
seq = [T3] * 2 + [T4] * 4 + [F1] * 4 + [F2] * 6
for k, n in enumerate(seq):
    hit(base + k * 0.25, n, 80 + k * 2.6, sig=5.0, push=-7)
hit(base + 0.0, BD, 108, sig=3.0)
hit(base + 2.0, BD, 108, sig=3.0)
hit(base + 3.0, BD, 110, sig=3.0)

base = 148
for k in range(32):
    hit(base + k * 0.125, SD, 70 + k * 1.7, sig=5.0, push=-7)
hit(base + 2.0, BD, 110, sig=3.0)

# ==========================================================================
# E. CLIMAX -- bars 38-46, tempo 150
# ==========================================================================
groove(152, crash=True, kick_pat=0, energy=1.06)
groove(156, kick_pat=2, energy=1.06)

# bar 40 -- tambourine changes the colour under the crashes
base = 160
hit(base + 0.0, CR, 110, sig=2.0)
hit(base + 2.0, CR2, 106, sig=2.0)
for e in range(8):
    hit(base + e * 0.5, TAMB, 64 if e % 4 == 0 else 54, sig=6.0)
hit(base + 1, SD, 112, sig=5.0)
hit(base + 3, SD, 114, sig=5.0)
for off, v in ((0.0, 110), (2.0, 108), (3.5, 104)):
    hit(base + off, BD, v, sig=3.0)

# bar 41 -- motif A at full voice on the toms
base = 164
hit(base + 0.0, BD, 110, sig=3.0)
hit(base + 2.5, BD, 100, sig=3.0)
for e in range(8):
    hit(base + e * 0.5, RD, 68 if e % 4 == 0 else 52, sig=5.0)
for off, n, v in zip(MOTIF, [T1, T1, T2, T1, T3, T2],
                     [112, 62, 114, 84, 50, 108]):
    hit(base + off, n, v, sig=7.0)

# bar 42 -- kit-wide run
base = 168
seq = [SD, SD, T1, T1, T2, T2, T3, T3,
       T4, T4, F1, F1, F2, F2, F2, F2]
for k, n in enumerate(seq):
    hit(base + k * 0.25, n, 96 if k % 4 == 0 else 74, sig=5.0)
hit(base + 0.0, BD, 108, sig=3.0)
hit(base + 2.0, BD, 106, sig=3.0)

groove(172, crash=True, kick_pat=3, energy=1.06)
groove(176, open_hat=(1.5, 3.5), kick_pat=1, energy=1.06)

base = 180
seq = [T1, T2, T3, T4, F1, F2, T1, T2,
       T3, T4, F1, F2, SD, SD, SD, SD]
for k, n in enumerate(seq):
    hit(base + k * 0.25, n, 102 - k * 1.6, sig=5.0)
hit(base + 0.0, BD, 108, sig=3.0)
hit(base + 2.0, BD, 104, sig=3.0)

# bar 46 -- short punctuation, then air before the breakdown
base = 184
for k, n in enumerate([T1, T2, T3, T4, F1, F2, SD, SD]):
    hit(base + k * 0.25, n, 104 - k * 3.0, sig=5.0)
hit(base + 2.0, CR, 112, sig=2.0)
hit(base + 2.0, BD, 114, sig=3.0)
hit(base + 3.0, SPL, 92, sig=2.0)

# ==========================================================================
# F. BREAKDOWN -- bars 47-53, tempo 108
# ==========================================================================
base = 188
hit(base + 0.0, RS, 72, sig=9.0, push=8)
hit(base + 0.0, HHP, 54, sig=5.0, push=8)
hit(base + 1.0, HHP, 50, sig=5.0, push=8)
hit(base + 1.5, RS, 54, sig=10.0, push=8)
hit(base + 2.0, HHP, 56, sig=5.0, push=8)
hit(base + 2.5, BD, 76, sig=5.0, push=8)
hit(base + 3.0, HHP, 52, sig=5.0, push=8)
hit(base + 3.5, RS, 60, sig=10.0, push=8)

base = 192
for e in range(4):
    hit(base + e, RB, 60 + (6 if e == 0 else 0), sig=6.0, push=6)
hit(base + 1.5, RS, 56, sig=10.0, push=6)
hit(base + 2.75, RS, 48, sig=10.0, push=6)
hit(base + 0.0, BD, 80, sig=5.0, push=6)
hit(base + 2.5, BD, 74, sig=5.0, push=6)

# bar 49 -- motif A, almost whispered
base = 196
for off, v in zip(MOTIF, [64, 42, 76, 58, 36, 72]):
    hit(base + off, SD, v, sig=9.0, push=6)
hit(base + 0.0, BD, 78, sig=5.0, push=6)
hit(base + 2.0, BD, 74, sig=5.0, push=6)
hit(base + 1.0, HHP, 48, sig=5.0, push=6)
hit(base + 3.0, HHP, 50, sig=5.0, push=6)

# bar 50 -- colour from the rest of the percussion set
base = 200
hit(base + 0.0, HHP, 46, sig=5.0, push=4)
hit(base + 0.0, T4, 78, sig=6.0, push=4)
hit(base + 0.0, CB, 58, sig=6.0, push=4)
hit(base + 1.5, T3, 74, sig=6.0, push=4)
hit(base + 2.0, BD, 82, sig=5.0, push=4)
hit(base + 2.5, CB, 50, sig=6.0, push=4)
hit(base + 3.0, T2, 76, sig=6.0, push=4)
hit(base + 3.75, RS, 52, sig=10.0, push=4)

# bars 51-53 -- rolls swell back up
base = 204
for k in range(16):
    hit(base + k * 0.25, SD, 46 + k * 1.6, sig=6.0, push=3)
hit(base + 0.0, BD, 82, sig=5.0, push=3)
hit(base + 2.0, BD, 86, sig=5.0, push=3)

base = 208
for k in range(16):
    hit(base + k * 0.25, SD, 62 + k * 2.2, sig=6.0, push=2)
hit(base + 0.0, BD, 88, sig=5.0, push=2)
hit(base + 2.0, BD, 92, sig=5.0, push=2)

base = 212
for k in range(32):
    hit(base + k * 0.125, SD, 74 + k * 1.6, sig=6.0, push=1)
hit(base + 0.0, BD, 94, sig=5.0, push=1)
hit(base + 2.0, BD, 98, sig=5.0, push=1)

# ==========================================================================
# G. FINAL BUILD -- bars 54-60, tempo 152 -> 168
# ==========================================================================
base = 216
hit(base + 0.0, CR, 116, sig=2.0)
hit(base + 0.0, BD, 114, sig=3.0)
seq = [SD, SD, T1, T1, T2, T2, T3, T3,
       T4, T4, F1, F1, F2, F2, T4, T3]
for k, n in enumerate(seq):
    hit(base + k * 0.25, n, 102 if k % 4 == 0 else 80, sig=5.0)

base = 220
pat = [T1, T1, T2, T2, T3, T3, T4, T4,
       F1, F1, F2, F2, F1, F1, T4, T4]
for k, n in enumerate(pat):
    hit(base + k * 0.25, n, 98 if k % 4 == 0 else 78, sig=5.0)
hit(base + 0.0, BD, 110, sig=3.0)
hit(base + 2.0, BD, 108, sig=3.0)

base = 224
for k in range(16):
    v = 112 if k % 4 == 0 else (82 if k % 2 == 0 else 62)
    hit(base + k * 0.25, SD, v, sig=5.0)
hit(base + 0.0, BD, 110, sig=3.0)
hit(base + 2.5, BD, 104, sig=3.0)

base = 228
asc = [F2, F1, T4, T3, T2, T1, SD, T1, T2, T3, T4, F1, F2, F1, F2, SD]
for k, n in enumerate(asc):
    hit(base + k * 0.25, n, 106 if k % 4 == 0 else 82, sig=5.0)
hit(base + 0.0, BD, 110, sig=3.0)
hit(base + 2.0, BD, 108, sig=3.0)

base = 232                              # tempo picks up to 168 here
for k in range(32):
    hit(base + k * 0.125, SD, 84 + k * 1.3, sig=5.0)
hit(base + 0.0, BD, 112, sig=3.0)
hit(base + 2.0, BD, 110, sig=3.0)

base = 236
pat = [SD] * 8 + [T1] * 8 + [T2] * 8 + [T3] * 8
for k, n in enumerate(pat):
    hit(base + k * 0.125, n, 90 + k * 1.0, sig=5.0)
hit(base + 0.0, BD, 112, sig=3.0)
hit(base + 2.0, BD, 112, sig=3.0)

base = 240
for k in range(32):
    n = SD if k < 16 else (T1 if k < 24 else T2)
    hit(base + k * 0.125, n, 94 + k * 1.05, sig=5.0)
hit(base + 0.0, BD, 112, sig=3.0)
hit(base + 1.0, BD, 110, sig=3.0)
hit(base + 2.0, BD, 112, sig=3.0)
hit(base + 3.0, BD, 110, sig=3.0)

# ==========================================================================
# FINAL HIT -- bar 61, landing instead of fading
# ==========================================================================
hit(244.0, CR, 127, sig=1.0)
hit(244.0, BD, 122, sig=1.0)
hit(244.0, SD, 124, sig=2.0)
hit(244.5, BD, 112, sig=2.0)
hit(245.0, CR2, 122, sig=2.0)
hit(245.0, BD, 116, sig=2.0)
hit(246.0, CR, 118, sig=2.0, dur=3.5)
hit(246.0, BD, 118, sig=2.0)


# --------------------------------------------------------------------------
# playability guard: never more than two hands and two feet at one instant
# --------------------------------------------------------------------------
def clean(events):
    groups = defaultdict(list)
    for e in events:
        groups[e[0]].append(e)

    drop = set()
    for tick, es in groups.items():
        # one stroke per instrument per instant
        by_note = {}
        for e in es:
            n = e[1]
            if n in by_note:
                other = by_note[n]
                loser = other if e[2] > other[2] else e
                drop.add(id(loser))
                if loser is other:
                    by_note[n] = e
                continue
            by_note[n] = e

        for iset, limit in ((HANDS, 2), (FEET, 2)):
            grp = [e for e in es if e[1] in iset and id(e) not in drop]
            while len(grp) > limit:
                quiet = min(grp, key=lambda x: x[2])
                drop.add(id(quiet))
                grp.remove(quiet)

    return [e for e in events if id(e) not in drop]


notes = sorted(clean(ev), key=lambda e: (e[0], e[1]))

# --------------------------------------------------------------------------
# tempo map (beat, bpm)
# --------------------------------------------------------------------------
TEMPO = [
    (0, 100),
    (16, 112),
    (56, 120),
    (104, 138),
    (152, 150),
    (188, 108),
    (216, 152),
    (232, 168),
    (244, 152),
]


def bpm_to_tempo(bpm):
    return int(round(60000000.0 / bpm))


# --------------------------------------------------------------------------
# assemble the file
# --------------------------------------------------------------------------
def main():
    msgs = []
    for beat, bpm in TEMPO:
        msgs.append((int(round(beat * TPQ)), 0,
                     MetaMessage('set_tempo', tempo=bpm_to_tempo(bpm))))

    for tick, note, vel, dur in notes:
        msgs.append((tick, 2,
                     Message('note_on', channel=CH, note=note,
                             velocity=vel, time=0)))
        msgs.append((tick + dur, 1,
                     Message('note_off', channel=CH, note=note,
                             velocity=0, time=0)))

    msgs.sort(key=lambda x: (x[0], x[1]))

    mid = MidiFile(ticks_per_beat=TPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             clocks_per_click=24,
                             notated_32nd_notes_per_beat=8, time=0))

    last = 0
    for tick, _order, msg in msgs:
        msg.time = tick - last
        last = tick
        track.append(msg)

    mid.save('solo.mid')


if __name__ == '__main__':
    main()
