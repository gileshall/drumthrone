#!/usr/bin/env python3
"""
drum_solo.py -- generate a two minute solo drum piece as a General MIDI file.

The solo is built phrase by phrase on a musical beat grid (tempo map with
surges and settles), then every single note is placed by "hands": timing is
humanised per limb, velocities carry accents / ghost notes / crescendos, and
the piece is validated so that no more than two hands and two feet are ever
striking at the same instant.

Running this script in an empty directory writes solo.mid next to it.
"""

import math
import random

from mido import Message, MidiFile, MetaMessage, MidiTrack

# ---------------------------------------------------------------------------
# GM percussion map
# ---------------------------------------------------------------------------
KICK, KICK2 = 36, 35
SNARE, STICK = 38, 37
CLAP = 39
HAT, PEDAL, OPEN = 42, 44, 46
RIDE, BELL, RIDE2 = 51, 53, 59
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
T1, T2, T3, T4 = 50, 48, 47, 45          # rack toms, high -> low
F1, F2 = 43, 41                          # floor toms
COWBELL = 56
WOODHI, WOODLO = 76, 77
TAMB = 54
CONGA_HI_O, CONGA_HI_M, CONGA_LO = 63, 62, 64
TRI_OPEN = 81

PPQ = 480
TICKS_PER_SEC = 960.0                    # the file's constant 120 BPM tempo
SEED = 20240607

# ---------------------------------------------------------------------------
# Tempo map: (beat, bpm).  The pulse surges and settles with the music.
#   0-16    intro, drifting in
#   16-48   the motif stated
#   48-80   first peak
#   80-96   breakdown
#   96-128  long crescendo build
#   128-160 climax
#   160-192 finale statement
#   192-216 colour / development
#   216-240 last chorus and the final hit
# ---------------------------------------------------------------------------
TEMPO_POINTS = [
    (0.0, 100.0),
    (16.0, 112.0),
    (48.0, 120.0),
    (80.0, 126.0),
    (96.0, 104.0),
    (128.0, 134.0),
    (160.0, 138.0),
    (192.0, 128.0),
    (216.0, 128.0),
    (232.0, 124.0),
    (240.0, 104.0),
]


def _seg_seconds(b0, t0, b1, t1, b):
    """Exact time (seconds) to travel from beat b0 to beat b, BPM linear in b."""
    if abs(t1 - t0) < 1e-9:
        return (b - b0) * 60.0 / t0
    k = (t1 - t0) / (b1 - b0)
    bpm = t0 + k * (b - b0)
    return (60.0 / k) * math.log(bpm / t0)


TEMPO_TIMES = [0.0]
for _i in range(1, len(TEMPO_POINTS)):
    _b0, _t0 = TEMPO_POINTS[_i - 1]
    _b1, _t1 = TEMPO_POINTS[_i]
    TEMPO_TIMES.append(TEMPO_TIMES[-1] + _seg_seconds(_b0, _t0, _b1, _t1, _b1))


def beat_to_time(b):
    """Absolute time in seconds of a (possibly fractional) beat."""
    pts = TEMPO_POINTS
    if b <= pts[0][0]:
        return TEMPO_TIMES[0] + (b - pts[0][0]) * 60.0 / pts[0][1]
    for i in range(1, len(pts)):
        if b <= pts[i][0]:
            b0, t0 = pts[i - 1]
            b1, t1 = pts[i]
            return TEMPO_TIMES[i - 1] + _seg_seconds(b0, t0, b1, t1, b)
    b0, t0 = pts[-1]
    return TEMPO_TIMES[-1] + (b - b0) * 60.0 / t0


# ---------------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------------
def _has(seq, x, eps=1e-6):
    return any(abs(x - s) < eps for s in seq)


def _jit(rng, amp):
    return (rng.random() * 2.0 - 1.0) * amp


class Solo:
    """Collects [beat, note, velocity, limb, duration_seconds]."""

    def __init__(self):
        self.notes = []

    def hit(self, b, note, vel, limb, dur=0.12):
        v = int(max(1, min(127, round(vel))))
        self.notes.append([float(b), int(note), v, limb, float(dur)])


def make_fill(s, b, rng, start, seq, sub=0.25, mode='single',
              v0=84, v1=112, dur=0.13):
    """Run notes around the kit, from beat `start` of the bar to its end."""
    n = int(round((4.0 - start) / sub))
    if n <= 0:
        return
    for i in range(n):
        t = start + i * sub
        note = seq[i % len(seq)]
        f = i / (n - 1) if n > 1 else 0.0
        v = v0 + (v1 - v0) * f + rng.randint(-4, 4)
        if mode == 'double':
            limb = 'RH' if (i // 2) % 2 == 0 else 'LH'
        else:
            limb = 'RH' if i % 2 == 0 else 'LH'
        s.hit(b + t, note, v, limb, dur)


def roll(s, b, start, end, sub, note=SNARE, v0=60, v1=110,
         mode='single', dur=0.10):
    """A swell: evenly spaced notes with a velocity ramp."""
    n = int(round((end - start) / sub))
    if n <= 0:
        return
    for i in range(n):
        t = start + i * sub
        f = i / (n - 1) if n > 1 else 0.0
        v = v0 + (v1 - v0) * f
        if mode == 'double':
            limb = 'RH' if (i // 2) % 2 == 0 else 'LH'
        else:
            limb = 'RH' if i % 2 == 0 else 'LH'
        s.hit(b + t, note, v, limb, dur)


def groove(s, b, rng, cym=HAT, cym_vel=74, kick=(0.0, 2.0), snare=(1.0, 3.0),
           ghosts=(), opens=(), accents=(), fill=None, sub=0.5, crash=False):
    """One bar of the main motif, with optional fill on the back end."""
    fill_start = fill['start'] if fill else 4.0

    t = 0.0
    i = 0
    while t < fill_start - 1e-9:
        if crash and t == 0.0:
            s.hit(b + t, CRASH, cym_vel + 26 + rng.randint(-3, 3), 'RH', 2.2)
            t += sub
            i += 1
            continue
        if _has(opens, t):
            note, dur = OPEN, 0.45
        else:
            note = cym
            dur = 0.07 if cym in (HAT, PEDAL) else 0.9
        v = cym_vel + (8 if i % 2 == 0 else -6)
        if _has(accents, t):
            v += 14
        s.hit(b + t, note, v + rng.randint(-4, 4), 'RH', dur)
        t += sub
        i += 1

    for k in kick:
        if k < fill_start - 1e-9:
            s.hit(b + k, KICK, 100 + rng.randint(-4, 4), 'RF', 0.12)
    for sn in snare:
        if sn < fill_start - 1e-9:
            s.hit(b + sn, SNARE, 106 + rng.randint(-4, 4), 'LH', 0.12)
    for g in ghosts:
        if g < fill_start - 1e-9:
            s.hit(b + g, SNARE, 28 + rng.randint(0, 10), 'LH', 0.09)

    if fill:
        make_fill(s, b, rng, **fill)


FILL_DOWN = [SNARE, SNARE, T1, T1, T2, T2, T3, T4]
FILL_AROUND = [SNARE, T1, T2, T3, T4, F1, F2, SNARE]

# ===========================================================================
#                              THE PERFORMANCE
# ===========================================================================
S = Solo()
rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# INTRO (beats 0-16) -- a pulse emerges, the motif arrives
# ---------------------------------------------------------------------------
S.hit(0.0, KICK, 100, 'RF')
S.hit(0.0, STICK, 74, 'LH', 0.07)
S.hit(1.0, PEDAL, 66, 'LF', 0.08)
S.hit(2.0, KICK, 94, 'RF')
S.hit(3.0, PEDAL, 64, 'LF', 0.08)

S.hit(4.0, KICK, 100, 'RF')
S.hit(4.0, PEDAL, 68, 'LF', 0.08)
S.hit(5.0, SNARE, 94, 'LH')
S.hit(6.0, KICK, 96, 'RF')
S.hit(6.5, KICK, 84, 'RF')
S.hit(7.0, SNARE, 98, 'LH')
S.hit(7.5, SNARE, 32, 'LH', 0.09)

groove(S, 8, rng, cym_vel=66, ghosts=(1.75,))
groove(S, 12, rng, cym_vel=70, ghosts=(1.75, 2.75),
       fill=dict(start=2.0, seq=FILL_DOWN, sub=0.25, v0=80, v1=104))

# ---------------------------------------------------------------------------
# MOTIF SECTION (16-48) -- state it, vary it, grow it
# ---------------------------------------------------------------------------
groove(S, 16, rng, cym_vel=74, ghosts=(1.75, 3.25))
groove(S, 20, rng, cym_vel=76, kick=(0.0, 2.0, 3.5), ghosts=(2.75,),
       opens=(3.5,), accents=(0.0, 2.0))
groove(S, 24, rng, cym=RIDE, cym_vel=76, kick=(0.0, 2.5),
       ghosts=(0.75, 1.75, 2.75, 3.75))
groove(S, 28, rng, cym=RIDE, cym_vel=78, ghosts=(1.75,),
       fill=dict(start=3.0, seq=FILL_AROUND, sub=0.25, v0=88, v1=108))
groove(S, 32, rng, cym_vel=80, ghosts=(1.75, 2.75, 3.25), accents=(0.0, 2.0))
groove(S, 36, rng, cym_vel=80, kick=(0.0, 1.5, 2.0, 3.25), ghosts=(2.75,),
       fill=dict(start=3.5, seq=[SNARE, T1, T2, T3, T4, F1, F2, SNARE],
                 sub=0.125, mode='double', v0=90, v1=112))
groove(S, 40, rng, cym_vel=84, accents=(0.0, 1.0, 2.0, 3.0),
       ghosts=(0.75, 1.25, 1.75),
       fill=dict(start=3.0, seq=FILL_DOWN, sub=0.25, v0=92, v1=114))
groove(S, 44, rng, cym_vel=86, kick=(0.0,), snare=(1.0,),
       fill=dict(start=2.0, seq=[SNARE, SNARE, T1, T2, T3, T4, F1, F2],
                 sub=0.125, mode='double', v0=88, v1=120))

# ---------------------------------------------------------------------------
# FIRST PEAK (48-80)
# ---------------------------------------------------------------------------
groove(S, 48, rng, cym=RIDE, cym_vel=82, accents=(0.0, 2.0),
       ghosts=(1.75, 3.25), crash=True)
groove(S, 52, rng, cym=RIDE, cym_vel=82, kick=(0.0, 1.5, 2.0, 3.5),
       ghosts=(1.75, 2.75),
       fill=dict(start=3.5, seq=[T1, T2, T3, T4, F1, F2], sub=0.125,
                 v0=95, v1=115))
groove(S, 56, rng, cym=HAT, cym_vel=84, sub=0.25, accents=(0.0, 1.0, 2.0, 3.0),
       ghosts=(0.75, 1.75, 2.25, 3.25, 3.75))
groove(S, 60, rng, cym=HAT, cym_vel=84, sub=0.25,
       kick=(0.0, 1.0, 2.5, 3.0), ghosts=(0.5, 1.5, 2.25),
       fill=dict(start=3.0, seq=FILL_DOWN, sub=0.25, v0=92, v1=116))
groove(S, 64, rng, cym=RIDE, cym_vel=86, kick=(0.0,), snare=(2.0,),
       fill=dict(start=0.0,
                 seq=[T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2, SNARE, SNARE, T1, T4],
                 sub=0.25, mode='double', v0=90, v1=118))
groove(S, 68, rng, cym=RIDE, cym_vel=86, kick=(0.0, 1.5, 2.0, 2.5, 3.5),
       ghosts=(1.75, 3.75), accents=(0.0, 2.0))
groove(S, 72, rng, cym=HAT, cym_vel=88, sub=0.25, accents=(0.0, 1.0, 2.0, 3.0),
       ghosts=(0.75, 1.25, 1.75, 2.75, 3.25, 3.75))
groove(S, 76, rng, cym_vel=88, kick=(0.0,), snare=(1.0,),
       fill=dict(start=2.0,
                 seq=[SNARE, SNARE, SNARE, SNARE, T1, T1, T2, T2, T3, T4, F1, F2],
                 sub=1.0 / 6.0, v0=95, v1=120))

# ---------------------------------------------------------------------------
# BREAKDOWN (80-96) -- tension falls away, ghost notes and rim clicks
# ---------------------------------------------------------------------------
for (t, n, v, l, d) in [
    (0.0, KICK, 82, 'RF', 0.12),
    (1.0, STICK, 66, 'LH', 0.08),
    (1.75, STICK, 34, 'LH', 0.06),
    (2.0, KICK, 78, 'RF', 0.12),
    (2.5, PEDAL, 48, 'LF', 0.07),
    (3.0, STICK, 62, 'LH', 0.08),
    (3.5, KICK, 72, 'RF', 0.12),
]:
    S.hit(80 + t, n, v, l, d)

for (t, n, v, l, d) in [
    (0.0, KICK, 84, 'RF', 0.12),
    (0.5, STICK, 36, 'LH', 0.06),
    (1.0, STICK, 68, 'LH', 0.08),
    (1.5, KICK, 70, 'RF', 0.12),
    (2.0, KICK, 80, 'RF', 0.12),
    (2.75, STICK, 38, 'LH', 0.06),
    (3.0, STICK, 66, 'LH', 0.08),
    (3.5, PEDAL, 46, 'LF', 0.07),
]:
    S.hit(84 + t, n, v, l, d)

groove(S, 88, rng, cym=HAT, cym_vel=52, kick=(0.0, 2.0), snare=(1.0, 3.0),
       ghosts=(2.75,))

S.hit(92.0, KICK, 92, 'RF')
roll(S, 92, 2.0, 4.0, 0.25, SNARE, 50, 92)

# ---------------------------------------------------------------------------
# BUILD (96-128) -- a long crescendo made of phrases, not just volume
# ---------------------------------------------------------------------------
groove(S, 96, rng, cym=HAT, cym_vel=62, ghosts=(1.75, 3.25))
groove(S, 100, rng, cym=HAT, cym_vel=68, kick=(0.0, 1.5, 2.0),
       ghosts=(2.75, 3.75))
groove(S, 104, rng, cym=HAT, cym_vel=74, sub=0.25, kick=(0.0, 2.0, 3.25),
       accents=(0.0, 1.0, 2.0, 3.0), ghosts=(1.75, 2.75))
groove(S, 108, rng, cym=RIDE, cym_vel=78, kick=(0.0, 2.0, 2.5),
       ghosts=(1.75, 3.75),
       fill=dict(start=3.5, seq=[T1, T2, T3, T4, F1, F2], sub=0.125,
                 v0=90, v1=112))
groove(S, 112, rng, cym=HAT, cym_vel=80, ghosts=(1.75,),
       fill=dict(start=3.0, seq=[SNARE, T1, T2, T3], sub=0.125,
                 mode='double', v0=86, v1=110))

S.hit(116.0, KICK, 100, 'RF')
roll(S, 116, 0.5, 4.0, 0.25, SNARE, 56, 88)

S.hit(120.0, KICK, 102, 'RF')
roll(S, 120, 1.0, 2.0, 0.25, SNARE, 70, 84)
roll(S, 120, 2.0, 3.0, 0.25, SNARE, 86, 96)
roll(S, 120, 3.0, 4.0, 1.0 / 6.0, SNARE, 96, 108)

S.hit(124.0, KICK, 104, 'RF')
make_fill(S, 124, rng, start=0.0,
          seq=[SNARE, SNARE, T1, T1, T2, T2, T3, T3,
               T4, T4, F1, F1, F2, F2, T3, T1],
          sub=0.25, mode='double', v0=92, v1=120)

# ---------------------------------------------------------------------------
# CLIMAX (128-160)
# ---------------------------------------------------------------------------
groove(S, 128, rng, cym=RIDE, cym_vel=94, kick=(0.0, 2.0, 2.5),
       ghosts=(1.75, 3.25), accents=(0.0, 2.0), crash=True)
groove(S, 132, rng, cym=RIDE, cym_vel=94, kick=(0.0, 1.5, 2.0, 3.5),
       ghosts=(2.75,), accents=(0.0, 2.0),
       fill=dict(start=3.5, seq=[T1, T2, T3, T4, F1, F2], sub=0.125,
                 v0=100, v1=120))
groove(S, 136, rng, cym=HAT, cym_vel=92, sub=0.25,
       kick=(0.0, 2.0, 2.5, 3.0), ghosts=(1.75, 3.75),
       accents=(0.0, 1.0, 2.0, 3.0))
groove(S, 140, rng, cym=HAT, cym_vel=92, sub=0.25,
       kick=(0.0, 0.75, 2.0, 3.5), ghosts=(1.25, 1.75, 2.5, 3.25),
       fill=dict(start=3.0, seq=FILL_DOWN, sub=0.25, v0=100, v1=122))
groove(S, 144, rng, cym=RIDE, cym_vel=96, ghosts=(1.75, 2.75),
       accents=(0.0, 2.0))
groove(S, 148, rng, cym=RIDE, cym_vel=96, kick=(0.0, 1.5, 2.0),
       fill=dict(start=2.0, seq=[T1, T2, T3, T4, T4, T3, T2, T1],
                 sub=0.125, v0=100, v1=122))
groove(S, 152, rng, cym=HAT, cym_vel=94, sub=0.25, kick=(0.0, 2.0, 3.25),
       accents=(0.0, 1.0, 2.0, 3.0), ghosts=(1.75, 2.75))
groove(S, 156, rng, cym_vel=94, kick=(0.0,), snare=(2.0,),
       fill=dict(start=0.0,
                 seq=[SNARE, SNARE, T1, T1, T2, T2, T3, T3,
                      T4, T4, F1, F1, F2, F2, SNARE, SNARE],
                 sub=0.25, mode='double', v0=96, v1=124))

# ---------------------------------------------------------------------------
# FINALE STATEMENT (160-192) -- the motif returns, but it breathes
# ---------------------------------------------------------------------------
groove(S, 160, rng, cym=RIDE, cym_vel=88, ghosts=(1.75, 3.25), crash=True)
groove(S, 164, rng, cym=RIDE, cym_vel=88, kick=(0.0, 2.0, 3.5), snare=(1.0,),
       ghosts=(2.75,),
       fill=dict(start=3.0, seq=[T1, T2, T3, T4], sub=0.25, v0=96, v1=112))

# a breath: one wide hit and space
S.hit(168.0, KICK, 96, 'RF')
S.hit(168.0, CRASH2, 84, 'RH', 2.0)
S.hit(169.0, SNARE, 88, 'LH')
S.hit(170.5, KICK, 84, 'RF')
S.hit(171.0, SNARE, 92, 'LH')

# ghost-note workout with sharp accents
for i in range(16):
    t = i * 0.25
    v = 100 if i % 4 == 0 else 30 + rng.randint(0, 8)
    S.hit(172 + t, SNARE, v, 'RH' if i % 2 == 0 else 'LH', 0.09)
S.hit(172.0, KICK, 92, 'RF')
S.hit(172.5, KICK, 78, 'RF')
S.hit(174.0, KICK, 90, 'RF')

groove(S, 176, rng, cym=RIDE, cym_vel=90, kick=(0.0, 2.0, 2.5),
       ghosts=(1.75, 3.75))
groove(S, 180, rng, cym=RIDE, cym_vel=90, kick=(0.0,), snare=(1.0,),
       fill=dict(start=2.0, seq=FILL_AROUND, sub=0.25, mode='double',
                 v0=94, v1=118))
groove(S, 184, rng, cym=HAT, cym_vel=88, sub=0.25, accents=(0.0, 1.0, 2.0, 3.0),
       ghosts=(1.75, 2.75, 3.75))
groove(S, 188, rng, cym_vel=88, kick=(0.0,), snare=(1.0,),
       fill=dict(start=2.0, seq=FILL_DOWN, sub=0.125, v0=96, v1=120))

# ---------------------------------------------------------------------------
# COLOUR / DEVELOPMENT (192-216)
# ---------------------------------------------------------------------------
groove(S, 192, rng, cym=RIDE, cym_vel=86, ghosts=(1.75, 3.25), crash=True)

# cowbell over the backbeat
for i in range(8):
    t = i * 0.5
    v = 92 if i % 2 == 0 else 70
    S.hit(196 + t, COWBELL, v + rng.randint(-4, 4), 'RH', 0.12)
S.hit(196.0, KICK, 96, 'RF')
S.hit(196.25, KICK, 80, 'RF')
S.hit(196.0 + 1.0, SNARE, 100, 'LH')
S.hit(196.0 + 2.0, KICK, 96, 'RF')
S.hit(196.0 + 2.75, SNARE, 34, 'LH', 0.09)
S.hit(196.0 + 3.0, SNARE, 102, 'LH')

# congas / woodblock -- hands trade the melody
for i, n in enumerate([CONGA_HI_O, CONGA_HI_M, CONGA_HI_O, CONGA_LO,
                       CONGA_HI_O, CONGA_HI_M, WOODHI, WOODLO]):
    t = i * 0.5
    v = 80 + (10 if i % 2 == 0 else 0) + rng.randint(-4, 4)
    S.hit(200 + t, n, v, 'RH' if i % 2 == 0 else 'LH', 0.15)
S.hit(200.0, KICK, 94, 'RF')
S.hit(200.0 + 2.0, KICK, 94, 'RF')
S.hit(200.0 + 3.0, PEDAL, 54, 'LF', 0.07)

groove(S, 204, rng, cym=RIDE, cym_vel=88, kick=(0.0, 2.0, 2.5),
       ghosts=(1.75, 3.75), accents=(0.0, 2.0))
groove(S, 208, rng, cym=RIDE, cym_vel=90, kick=(0.0, 1.5, 2.0), ghosts=(2.75,),
       fill=dict(start=3.0, seq=[T1, T2, T3, T4, F1, F2], sub=0.25,
                 v0=96, v1=116))
groove(S, 212, rng, cym=HAT, cym_vel=90, sub=0.25, accents=(0.0, 1.0, 2.0, 3.0),
       ghosts=(1.75, 3.75),
       fill=dict(start=3.5, seq=[SNARE, SNARE, T1, T2], sub=0.125,
                 mode='double', v0=100, v1=118))

# ---------------------------------------------------------------------------
# LAST CHORUS AND THE FINAL HIT (216-240)
# ---------------------------------------------------------------------------
groove(S, 216, rng, cym=RIDE, cym_vel=92, ghosts=(1.75, 3.25),
       accents=(0.0, 2.0), crash=True)
groove(S, 220, rng, cym=RIDE, cym_vel=92, kick=(0.0, 2.0, 2.5), ghosts=(3.75,),
       accents=(0.0, 2.0))

S.hit(224.0, CRASH, 100, 'RH', 2.0)
S.hit(224.0, KICK, 108, 'RF')
S.hit(225.0, SNARE, 96, 'LH')
S.hit(226.0, KICK, 92, 'RF')
S.hit(227.0, SNARE, 100, 'LH')

groove(S, 228, rng, cym=HAT, cym_vel=64, ghosts=(1.75, 2.75, 3.75))

S.hit(232.0, KICK, 104, 'RF')
roll(S, 232, 0.0, 2.0, 0.25, SNARE, 60, 84)
roll(S, 232, 2.0, 3.0, 0.25, SNARE, 86, 96)
roll(S, 232, 3.0, 4.0, 1.0 / 6.0, SNARE, 98, 108)

S.hit(236.0, KICK, 108, 'RF')
roll(S, 236, 0.0, 2.0, 0.125, SNARE, 70, 92)
roll(S, 236, 2.0, 3.0, 0.125, SNARE, 94, 108)
roll(S, 236, 3.0, 3.875, 0.125, SNARE, 110, 120)

# ... and it lands, hard, on all four limbs.
S.hit(240.0, CRASH, 118, 'RH', 3.0)
S.hit(240.0, SNARE, 112, 'LH', 0.25)
S.hit(240.0, KICK, 118, 'RF', 0.30)
S.hit(240.0, PEDAL, 90, 'LF', 0.10)

# ===========================================================================
#  Realise the performance: human timing per limb, then MIDI
# ===========================================================================
LIMB_BIAS = {'RH': -0.006, 'LH': 0.009, 'RF': -0.004, 'LF': 0.007}


def drift(b):
    """A slow ensemble push / pull; the pulse breathes."""
    return 0.014 * math.sin(b * 0.63 + 1.1) + 0.009 * math.sin(b * 0.21 + 0.4)


scheduled = []
for (b, note, vel, limb, dur) in S.notes:
    bb = b + drift(b) + LIMB_BIAS[limb] + _jit(rng, 0.010)
    if bb < 0.0:
        bb = 0.0
    on = int(round(beat_to_time(bb) * TICKS_PER_SEC))
    length = max(8, int(round(dur * TICKS_PER_SEC)))
    scheduled.append([on, on + length, note, vel, limb])

# one note per limb at a time -> never more than two hands + two feet
scheduled.sort(key=lambda e: (e[0], e[4]))
MIN_GAP = 20                                # ~21 ms, a flam at the tightest
_last = {}
for e in scheduled:
    limb = e[4]
    if limb in _last and e[0] - _last[limb] < MIN_GAP:
        shift = MIN_GAP - (e[0] - _last[limb])
        e[0] += shift
        e[1] += shift
    _last[limb] = e[0]

mid = MidiFile(type=0, ticks_per_beat=PPQ)
track = MidiTrack()
mid.tracks.append(track)
track.append(MetaMessage('track_name', name='Drum Solo', time=0))
track.append(MetaMessage('set_tempo', tempo=500000, time=0))   # 120 BPM grid
track.append(Message('program_change', channel=9, program=0, time=0))

events = []
for (on, off, note, vel, _limb) in scheduled:
    events.append((on, 1, note, vel))
    events.append((off, 0, note, 0))
events.sort(key=lambda e: (e[0], e[1], e[2]))

prev = 0
for (tick, kind, note, vel) in events:
    delta = tick - prev
    if delta < 0:
        delta = 0
    prev = tick
    track.append(Message('note_on' if kind else 'note_off',
                         channel=9, note=note, velocity=vel, time=delta))

mid.save('solo.mid')
