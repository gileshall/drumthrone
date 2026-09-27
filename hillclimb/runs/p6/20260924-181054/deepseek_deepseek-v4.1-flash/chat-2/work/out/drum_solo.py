#!/usr/bin/env python3
"""
drum_solo.py -- write solo.mid, a ~two minute General MIDI drum solo.

Everything lives on MIDI channel 10 (the GM percussion channel).  The
script is completely deterministic: run it twice and you get two
byte-identical files.

Musical plan (66 bars of 4/4)

    bars  0- 3   intro      - one crash, motif A stated plainly
    bars  4-11   groove A   - the hook, then four variations of it
    bars 12-19   development- 16th hi-hat, ride bell, first big fills
    bars 20-27   motif B    - same rhythmic DNA voiced on the toms
    bars 28-33   build      - snare rolls that swell, tempo accelerates
    bars 34-41   climax     - motif A at full voice
    bars 42-47   breakdown  - space, cowbell / congas / splash, then a build
    bars 48-55   run        - single strokes and doubles all round the kit
    bars 56-63   finale     - everything, biggest version of motif A
    bars 64-65   landing    - the final hit, then let it ring
"""

import random
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

# ----------------------------------------------------------------------
# General MIDI percussion key map
# ----------------------------------------------------------------------
KICK, KICK2         = 36, 35
SNARE, STICK        = 38, 37
HH, HHPED, HHO      = 42, 44, 46
RIDE, BELL          = 51, 53
CRASH, CRASH2       = 49, 57
SPLASH, CHINA       = 55, 52
TMH, TM2, TM3       = 50, 48, 47      # high, hi-mid, low-mid tom
TM4, TF1, TF2       = 45, 43, 41      # low tom, high floor, low floor
TAMB, COW           = 54, 56
CONGAH, CONGAL      = 63, 64
BONGOH, BONGOL      = 60, 61

FEET = frozenset((KICK, KICK2, HHPED))

PPQ  = 960
CHAN = 9                              # MIDI channel 10, zero based

rng = random.Random(0x5EED1234)

# every scheduled stroke: (time in beats, note, velocity, duration in beats)
EV = []


def hit(t, note, vel, dur=0.07):
    """Schedule one stroke.  t is measured in quarter notes from the start."""
    v = int(round(max(1.0, min(127.0, vel))))
    EV.append((float(t), int(note), v, float(dur)))


# ----------------------------------------------------------------------
# pattern helpers
# ----------------------------------------------------------------------
def _hat_steps(kind):
    if kind == '4':
        return [0.0, 1.0, 2.0, 3.0]
    if kind == '8':
        return [i * 0.5 for i in range(8)]
    if kind == '16':
        return [i * 0.25 for i in range(16)]
    return []


def groove_bar(t, v=1.0, kick=(0.0, 2.5), snare=(1.0, 3.0), ghosts=(),
               hats='8', hat_note=HH, hho=(), ride=False, bell=(),
               crash=None, sidestick=False, toms=(), tamb=(),
               kick_acc=104.0, kick_vel=92.0, snare_acc=106.0, snare_vel=96.0,
               hat_acc=74.0, hat_vel=56.0):
    """Emit one bar of groove starting at beat `t`."""
    # --- feet -------------------------------------------------------
    for i, x in enumerate(kick):
        hit(t + x, KICK, (kick_acc if i == 0 else kick_vel) * v, 0.08)

    # --- snare / backbeat -------------------------------------------
    sn = STICK if sidestick else SNARE
    for i, x in enumerate(snare):
        hit(t + x, sn, (snare_acc if i % 2 == 0 else snare_vel) * v, 0.08)

    # --- ghost notes -------------------------------------------------
    for x in ghosts:
        hit(t + x, SNARE, rng.uniform(26.0, 42.0) * v, 0.06)

    # --- cymbal / hi-hat layer ---------------------------------------
    for x in _hat_steps(hats):
        if x in hho:
            hit(t + x, RIDE if ride else HHO, (hat_acc - 6.0) * v, 0.55)
            continue
        accent = abs(x * 2.0 - round(x * 2.0)) < 1e-9
        note = RIDE if ride else hat_note
        vel = hat_acc if accent else hat_vel
        if ride and x in bell:
            note, vel = BELL, hat_acc + 8.0
        hit(t + x, note, vel * v, 0.07)

    # --- extras --------------------------------------------------------
    for (x, n, vv) in toms:
        hit(t + x, n, vv * v, 0.10)
    for x in tamb:
        hit(t + x, TAMB, rng.uniform(52.0, 68.0) * v, 0.10)

    if crash is not None:
        hit(t + crash, CRASH, 114.0 * v, 1.2)


def fill16(t0, start, notes, v0=85.0, v1=115.0, spb=0.25):
    """A fill of equal-spaced strokes beginning at `start` inside the bar."""
    n = len(notes)
    for i, nt in enumerate(notes):
        f = (i / (n - 1)) if n > 1 else 1.0
        hit(t0 + start + i * spb, nt, v0 + (v1 - v0) * f, 0.08)


def singles(t0, notes, spb=0.25, base=90.0, accent=14.0, ramp=0.0):
    """A run of single strokes, accenting whatever lands on a quarter."""
    for i, nt in enumerate(notes):
        tt = t0 + i * spb
        on_beat = abs(tt - round(tt)) < 1e-9
        hit(tt, nt, base + (accent if on_beat else 0.0) + ramp * i, 0.08)


def roll(t0, dur, notes, v0, v1, spb=0.125, cycle=False):
    """A swelling roll."""
    n = max(1, int(round(dur / spb)))
    for i in range(n):
        f = (i / (n - 1)) if n > 1 else 1.0
        nt = notes[i % len(notes)] if cycle else notes[0]
        hit(t0 + i * spb, nt, v0 + (v1 - v0) * f, 0.06)


def motifB(t, v=1.0, crash=None, ghost=(), extra=()):
    """Motif B - motif A's rhythm, re-voiced on the toms."""
    hit(t + 0.00, KICK, 104.0 * v)
    hit(t + 0.00, TM3,   92.0 * v)
    hit(t + 0.75, TM2,   84.0 * v)
    hit(t + 1.00, SNARE,100.0 * v)
    hit(t + 1.00, HHPED, 74.0 * v)
    hit(t + 1.50, TF1,   86.0 * v)
    hit(t + 2.00, KICK, 100.0 * v)
    hit(t + 2.00, TM3,   92.0 * v)
    hit(t + 2.75, TM2,   84.0 * v)
    hit(t + 3.00, SNARE,100.0 * v)
    hit(t + 3.00, HHPED, 74.0 * v)
    hit(t + 3.50, TF2,   88.0 * v)
    for x in ghost:
        hit(t + x, SNARE, rng.uniform(28.0, 42.0) * v, 0.06)
    for (x, n, vv) in extra:
        hit(t + x, n, vv * v, 0.09)
    if crash is not None:
        hit(t + crash, CRASH2, 110.0 * v, 1.3)


# ======================================================================
# 1.  INTRO  -  bars 0-3 : state motif A, unhurried
# ======================================================================
hit(0.0, KICK,  106)
hit(0.0, CRASH, 110, 2.0)
hit(1.0, SNARE, 106)
hit(2.0, KICK,   94)
hit(2.5, HH,     62)
hit(3.0, SNARE, 108)
hit(3.5, HH,     58)

# bar 1 - hats appear
groove_bar(4.0, kick=(0.0, 2.5), snare=(1.0, 3.0), hats='8', ghosts=(3.75,))

# bar 2 - the kick pattern of motif A
groove_bar(8.0, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 3.25))

# bar 3 - a pick-up fill carries into the hook
groove_bar(12.0, kick=(0.0, 2.5), snare=(1.0,), hats='4', ghosts=(1.5,))
fill16(12.0, 2.0, [SNARE, SNARE, TMH, TM2, TM3, TM4, TF1, SNARE], 68.0, 110.0)

# ======================================================================
# 2.  GROOVE A  -  bars 4-11 : the hook, then four ways of varying it
# ======================================================================
groove_bar(16.0, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 2.75, 3.25), crash=0.0)

groove_bar(20.0, kick=(0.0, 2.5), snare=(1.0, 3.0), hats='8', ride=True,
           bell=(0.0, 2.0), ghosts=(1.75, 3.75))

groove_bar(24.0, kick=(0.0, 1.5, 2.5), snare=(1.0, 3.0), hats='8',
           hho=(3.5,), ghosts=(0.75, 2.75))

groove_bar(28.0, kick=(0.0, 2.5), snare=(1.0,), hats='4', ghosts=(1.5,))
fill16(28.0, 2.0, [TM2, TM2, TM3, TM3, TM4, TF1, TF2, SNARE], 78.0, 116.0)

groove_bar(32.0, v=1.04, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 3.25, 3.75), crash=0.0)

groove_bar(36.0, kick=(0.0, 2.5, 3.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.25, 2.75))

groove_bar(40.0, kick=(0.0, 0.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(1.5, 3.5))

groove_bar(44.0, kick=(0.0, 2.5), snare=(1.0,), hats='4')
fill16(44.0, 1.5, [SNARE, TMH, TM2, TM3, TM2, TMH, SNARE, TM3, TM4, SNARE],
       72.0, 118.0)

# ======================================================================
# 3.  DEVELOPMENT  -  bars 12-19
# ======================================================================
groove_bar(48.0, v=1.05, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 2.25, 3.25, 3.75), crash=0.0)

groove_bar(52.0, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='16',
           ghosts=(1.5, 3.75), hat_acc=70.0, hat_vel=48.0)

groove_bar(56.0, kick=(0.0, 2.5, 3.75), snare=(1.0, 3.0), hats='8', ride=True,
           bell=(0.0, 1.0, 2.0, 3.0), ghosts=(1.5, 2.75))

groove_bar(60.0, kick=(0.0, 2.5), snare=(1.0,), hats='8', ghosts=(1.75,))
fill16(60.0, 2.0, [TMH, TMH, TM2, TM3, TM4, TF1, TF2, SNARE], 82.0, 120.0)

groove_bar(64.0, v=1.05, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 2.25, 3.25), crash=0.0)

groove_bar(68.0, kick=(0.0, 0.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(1.5, 2.75, 3.5))

groove_bar(72.0, kick=(0.0, 2.5, 3.5), snare=(1.0, 3.0), hats='16',
           ghosts=(2.75,), hat_acc=72.0, hat_vel=50.0)

groove_bar(76.0, kick=(0.0, 2.5), snare=(1.0,), hats='4')
fill16(76.0, 1.5, [SNARE, TMH, TM2, TM3, TM2, TMH, SNARE, TM4, TF1, SNARE],
       74.0, 120.0)

# ======================================================================
# 4.  MOTIF B  -  bars 20-27 : the rhythm moves onto the toms
# ======================================================================
motifB(80.0,  crash=0.0)
motifB(84.0,  ghost=(2.25, 3.75))
motifB(88.0,  ghost=(1.25,))

# bar 22 - a leaner variant
hit(88.0, KICK,  104.0)
hit(88.0, TM2,    92.0)
hit(88.5, TM3,    82.0)
hit(88.75, TM4,   78.0)
hit(89.0, SNARE, 102.0)
hit(89.5, TF1,    84.0)
hit(90.0, KICK,  100.0)
hit(90.0, TM2,    92.0)
hit(90.5, TM3,    82.0)
hit(91.0, SNARE, 102.0)
hit(91.5, TF2,    86.0)
hit(91.75, SNARE, 34.0)

# bar 23 - fill
hit(92.0, KICK, 104.0)
hit(92.0, CRASH, 102.0, 1.2)
fill16(92.0, 1.0, [TMH, TM2, TM3, TM4, TF1, TF2, TM4, TM3, TM2, TMH,
                   SNARE, SNARE], 78.0, 116.0)

# bar 24 - motif B, doubled toms
hit(96.0, KICK, 106.0)
hit(96.0, CRASH, 110.0, 1.4)
hit(96.0, TM3,   94.0)
hit(96.5, TM2,   86.0)
hit(97.0, SNARE, 102.0)
hit(97.0, HHPED,  74.0)
hit(97.5, TF1,    88.0)
hit(97.75, TM4,   78.0)
hit(98.0, KICK, 102.0)
hit(98.0, TM3,    94.0)
hit(98.5, TM2,    86.0)
hit(99.0, SNARE, 102.0)
hit(99.0, HHPED,  74.0)
hit(99.5, TF2,    88.0)
hit(99.75, TM4,   80.0)

# bar 25
hit(100.0, KICK,  104.0)
hit(100.0, TM3,    92.0)
hit(100.5, TM2,    84.0)
hit(100.75, TMH,   80.0)
hit(101.0, SNARE, 100.0)
hit(101.0, HHPED,  74.0)
hit(101.5, TF1,    86.0)
hit(102.0, KICK,  100.0)
hit(102.0, TM3,    92.0)
hit(102.5, TM2,    84.0)
hit(102.75, TMH,   80.0)
hit(103.0, SNARE, 100.0)
hit(103.0, HHPED,  74.0)
hit(103.5, TF2,    88.0)
hit(103.75, SNARE, 36.0)

# bar 26 - eighths on the toms, swelling
for i, n in enumerate([TMH, TM2, TM3, TM4, TF1, TF2, TF1, TM4]):
    hit(104.0 + i * 0.5, n, 72.0 + i * 5.0, 0.09)

# bar 27 - sixteenths, handing over to the build
for i, n in enumerate([TMH, TM2, TM3, TM2, TMH, TM2, TM3, TM4,
                       TF1, TF2, TF1, TM4, TM3, SNARE, SNARE, SNARE]):
    hit(108.0 + i * 0.25, n, 82.0 + i * 2.8, 0.08)

# ======================================================================
# 5.  BUILD  -  bars 28-33 : rolls that swell, tempo accelerating
# ======================================================================
roll(112.0, 4.0, [SNARE], 36.0, 62.0, spb=0.25)
hit(112.0, KICK, 92.0)

roll(116.0, 4.0, [SNARE], 54.0, 80.0, spb=0.25)
hit(116.0, KICK, 96.0)
hit(118.0, KICK, 98.0)

roll(120.0, 4.0, [SNARE], 72.0, 96.0, spb=0.25)
hit(120.0, KICK, 98.0)
hit(122.0, KICK, 102.0)

roll(124.0, 4.0, [SNARE], 88.0, 112.0, spb=0.125)
hit(124.0, KICK, 102.0)
hit(126.0, KICK, 106.0)

roll(128.0, 4.0, [SNARE], 100.0, 122.0, spb=0.125)
hit(128.0, KICK, 106.0)
hit(130.0, KICK, 108.0)

for i, n in enumerate([SNARE, TMH, TM2, TM3, TM4, TF1, TF2, TM4,
                       TF1, TM3, TM2, TMH, TM2, TM3, SNARE, SNARE]):
    hit(132.0 + i * 0.25, n, 98.0 + i * 1.8, 0.08)
hit(132.0, KICK, 110.0)
hit(134.0, KICK, 112.0)

# ======================================================================
# 6.  CLIMAX  -  bars 34-41 : motif A at full voice
# ======================================================================
groove_bar(136.0, v=1.08, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 2.25, 3.25, 3.75), crash=0.0)

groove_bar(140.0, v=1.06, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='16',
           ghosts=(1.5, 3.75), hat_acc=72.0, hat_vel=50.0)

groove_bar(144.0, v=1.08, kick=(0.0, 0.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(1.5, 2.25, 3.5))

groove_bar(148.0, v=1.06, kick=(0.0, 2.5), snare=(1.0,), hats='4',
           ghosts=(1.75,))
fill16(148.0, 2.0, [TMH, TM2, TM3, TM4, TF1, TF2, TF2, SNARE], 88.0, 122.0)

groove_bar(152.0, v=1.08, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 2.25, 3.25), crash=0.0)

groove_bar(156.0, v=1.06, kick=(0.0, 2.5, 3.5), snare=(1.0, 3.0), hats='8',
           ghosts=(1.25, 2.75))

groove_bar(160.0, v=1.08, kick=(0.0, 0.75, 2.5), snare=(1.0, 3.0), hats='16',
           ghosts=(2.75,), hat_acc=74.0, hat_vel=52.0)

groove_bar(164.0, v=1.06, kick=(0.0, 2.5), snare=(1.0,), hats='4')
fill16(164.0, 1.5, [SNARE, TMH, TM2, TM3, TM4, TF1, SNARE, SNARE], 86.0, 122.0)

# ======================================================================
# 7.  BREAKDOWN  -  bars 42-47 : space, colour, tension
# ======================================================================
hit(168.0, KICK, 100.0)
hit(168.0, COW,   86.0, 0.2)
hit(169.0, STICK, 94.0)
hit(170.0, KICK,  92.0)
hit(170.0, COW,   84.0, 0.2)
hit(170.5, HHPED, 72.0)
hit(171.0, STICK, 96.0)
hit(171.5, HHPED, 70.0)

hit(172.0, KICK,   100.0)
hit(172.0, CONGAL,  92.0)
hit(172.5, BONGOH,  76.0)
hit(173.0, STICK,   92.0)
hit(173.5, BONGOL,  74.0)
hit(173.75, CONGAH, 72.0)
hit(174.0, KICK,    94.0)
hit(174.0, CONGAL,  90.0)
hit(174.5, BONGOH,  76.0)
hit(175.0, STICK,   96.0)
hit(175.5, CONGAL,  76.0)
hit(175.75, STICK,  36.0)

hit(176.0, KICK,   98.0)
hit(176.0, SPLASH, 88.0, 1.0)
hit(177.0, STICK,  90.0)
hit(178.0, KICK,   92.0)
hit(178.0, HHPED,  68.0)
hit(179.0, STICK,  92.0)
hit(179.5, STICK,  34.0)

# bar 45 - a soft ghost-note groove, holding back
for i in range(8):
    hit(180.0 + i * 0.5, HH, (58.0 if i % 2 == 0 else 48.0), 0.07)
hit(180.0, KICK,  98.0)
hit(181.0, SNARE, 90.0)
hit(182.0, KICK,  94.0)
hit(183.0, SNARE, 94.0)
hit(183.25, SNARE, 30.0)
hit(183.75, SNARE, 34.0)

# bar 46 - crescendo on the snare
for i in range(8):
    hit(184.0 + i * 0.5, SNARE, 58.0 + i * 4.5, 0.07)
hit(184.0, KICK, 102.0)
hit(186.0, KICK, 102.0)

# bar 47 - start the run
for i in range(16):
    hit(188.0 + i * 0.25, SNARE, 76.0 + i * 2.6, 0.07)
hit(188.0, KICK, 106.0)
hit(190.0, KICK, 106.0)

# ======================================================================
# 8.  RUN  -  bars 48-55 : singles and doubles all round the kit
# ======================================================================
hit(192.0, KICK, 108.0)
hit(192.0, CRASH, 114.0, 1.5)
singles(192.0, [SNARE, TMH, TM2, TM3, TM4, TF1, TF2, TF1,
                TM4, TM3, TM2, TMH, SNARE, STICK, SNARE, SNARE],
        0.25, base=88.0, accent=14.0)

singles(196.0, [SNARE, TMH, TM2, TM3, TM4, TF1, TF2, SNARE,
                SNARE, TMH, TM2, TM3, TM4, TF1, TF2, SNARE],
        0.25, base=86.0, accent=18.0)
hit(196.0, KICK, 104.0)
hit(198.0, KICK, 104.0)

singles(200.0, [TMH, TM2, TM3, TM4, TF1, TF2, TF1, TM4,
                TM3, TM2, TMH, TM2, TM3, TM4, TM3, SNARE],
        0.25, base=84.0, accent=16.0)

# bar 51 - eighths on the toms with a flick at the end
for i, n in enumerate([TMH, TM2, TM3, TM4, TF1, TF2]):
    hit(204.0 + i * 0.5, n, 88.0 + (12.0 if i % 2 == 0 else 0.0), 0.09)
for i, n in enumerate([TMH, TM2, TF1, SNARE]):
    hit(207.0 + i * 0.25, n, 96.0 + i * 8.0, 0.08)

singles(208.0, [SNARE, TMH, SNARE, TM2, SNARE, TM3, SNARE, TM4,
                SNARE, TF1, SNARE, TF2, SNARE, TM4, SNARE, SNARE],
        0.25, base=88.0, accent=14.0)

# bar 53 - a snare buzz that resolves
for i in range(24):
    hit(212.0 + i * 0.125, SNARE, 80.0 + i * 1.6, 0.055)
hit(215.0, SNARE, 110.0)
hit(215.5, SNARE, 112.0)
hit(215.75, SNARE, 114.0)
hit(212.0, KICK, 106.0)
hit(214.0, KICK, 106.0)

singles(216.0, [TMH, TM2, TM3, TM2, TMH, TM2, TM3, TM4,
                TF1, TF2, TF1, TM4, TM3, SNARE, TM3, SNARE],
        0.25, base=92.0, accent=16.0, ramp=0.7)

# bar 55 - the last big run of the section
singles(220.0, [SNARE, TMH, TM2, TM3, TM4, TF1, TF2, TM4,
                TF1, TM3, TM2, SNARE],
        0.25, base=94.0, accent=18.0, ramp=0.7)
for i in range(8):
    hit(223.0 + i * 0.125, SNARE, 104.0 + i * 3.0, 0.05)
hit(220.0, KICK, 108.0)
hit(222.0, KICK, 110.0)

# ======================================================================
# 9.  FINALE  -  bars 56-63
# ======================================================================
groove_bar(224.0, v=1.10, kick=(0.0, 1.75, 2.5, 3.5), snare=(1.0, 3.0),
           hats='8', ghosts=(0.75, 1.5, 2.25, 3.25), crash=0.0)

groove_bar(228.0, v=1.10, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='16',
           ghosts=(3.75,), hat_acc=76.0, hat_vel=54.0)

groove_bar(232.0, v=1.10, kick=(0.0, 0.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(1.5, 2.25, 3.5))

groove_bar(236.0, v=1.06, kick=(0.0, 2.5), snare=(1.0,), hats='4')
fill16(236.0, 2.0, [TMH, TM2, TM3, TM4, TF1, TF2, TF2, SNARE], 92.0, 124.0)

groove_bar(240.0, v=1.12, kick=(0.0, 1.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(0.75, 1.5, 2.25, 3.25, 3.75), crash=0.0)

groove_bar(244.0, v=1.12, kick=(0.0, 2.5, 3.5), snare=(1.0, 3.0), hats='16',
           ghosts=(1.5, 2.75), hat_acc=78.0, hat_vel=56.0)

groove_bar(248.0, v=1.12, kick=(0.0, 0.75, 2.5), snare=(1.0, 3.0), hats='8',
           ghosts=(1.5, 2.25, 3.25))

singles(252.0, [SNARE, TMH, TM2, TM3, TM4, TF1, TF2, TM4,
                TF1, TM3, TM2, TMH, SNARE, TMH, TM2, SNARE],
        0.25, base=100.0, accent=20.0, ramp=1.0)
hit(252.0, KICK, 112.0)

# ======================================================================
# 10. LANDING  -  bars 64-65 : the final hit
# ======================================================================
hit(256.0, KICK,  122.0)
hit(256.0, CRASH, 127.0, 5.0)
hit(256.0, SNARE, 120.0)
hit(257.0, SNARE,  92.0)
hit(257.5, SNARE,  58.0)
hit(258.0, KICK,  114.0)
hit(258.0, TMH,   102.0)
hit(258.5, TM2,    96.0)
hit(259.0, TM3,   102.0)
hit(259.5, SNARE, 108.0)

hit(260.0, KICK,   127.0)
hit(260.0, CRASH,  127.0, 6.0)
hit(260.0, CRASH2, 122.0, 6.0)


# ======================================================================
# tempo map - one tempo per bar, phrases push and settle
# ======================================================================
TEMPO = []


def _seg(n, a, b):
    if n <= 1:
        TEMPO.append(float(a))
        return
    for i in range(n):
        TEMPO.append(a + (b - a) * i / (n - 1))


_seg(4, 116, 122)     # intro
_seg(8, 128, 128)     # groove A
_seg(8, 130, 128)     # development
_seg(8, 126, 120)     # motif B settles
_seg(6, 120, 136)     # build accelerates
_seg(8, 138, 140)     # climax
_seg(6, 120, 116)     # breakdown holds back
_seg(8, 128, 144)     # run accelerates
_seg(8, 146, 148)     # finale
_seg(2, 150, 148)     # landing

# a whisper of tempo noise so no two bars feel metronomic
TEMPO = [round(bpm + rng.uniform(-0.6, 0.6), 4) for bpm in TEMPO]

assert len(TEMPO) == 66, len(TEMPO)


# ======================================================================
# playability pass - never more than two hands and two feet at once
# ======================================================================
def enforce_playable(events):
    groups = {}
    for e in events:
        groups.setdefault(int(round(e[0] * 8.0)), []).append(e)
    out = []
    for key in sorted(groups):
        g = groups[key]
        feet = sorted([e for e in g if e[1] in FEET], key=lambda e: -e[2])
        hands = sorted([e for e in g if e[1] not in FEET], key=lambda e: -e[2])
        out.extend(feet[:2])
        out.extend(hands[:2])
    out.sort(key=lambda e: (e[0], e[1]))
    return out


# ======================================================================
# humanise - accents lean forward, ghosts drag, nothing on the grid
# ======================================================================
def humanize(events):
    out = []
    for (t, note, vel, dur) in events:
        if vel >= 100:
            dt = rng.gauss(-0.007, 0.010)
        elif vel <= 48:
            dt = rng.gauss(0.013, 0.013)
        else:
            dt = rng.gauss(0.0, 0.011)
        dv = int(round(max(1.0, min(127.0, vel + rng.gauss(0.0, 3.2)))))
        out.append((max(0.0, t + dt), note, dv, dur))
    return out


# ======================================================================
# render
# ======================================================================
def build_midi(events, tempos, path):
    mid = MidiFile(type=0, ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    msgs = []
    msgs.append((0, 0, MetaMessage('track_name', name='Drum Solo', time=0)))
    msgs.append((0, 0, MetaMessage('time_signature', numerator=4,
                                   denominator=4, clocks_per_click=24,
                                   notated_32nd_notes_per_beat=8, time=0)))

    for i, bpm in enumerate(tempos):
        msgs.append((int(round(i * 4.0 * PPQ)), 0,
                     MetaMessage('set_tempo', tempo=bpm2tempo(bpm), time=0)))

    for (t, note, vel, dur) in events:
        on = int(round(t * PPQ))
        off = int(round((t + max(dur, 0.02)) * PPQ))
        if off <= on:
            off = on + 5
        msgs.append((on, 2, Message('note_on', channel=CHAN, note=note,
                                    velocity=vel, time=0)))
        msgs.append((off, 1, Message('note_off', channel=CHAN, note=note,
                                     velocity=0, time=0)))

    msgs.sort(key=lambda x: (x[0], x[1]))

    prev = 0
    for tick, _prio, msg in msgs:
        msg.time = tick - prev
        prev = tick
        track.append(msg)

    track.append(MetaMessage('end_of_track', time=PPQ))
    mid.save(path)


def main():
    clean = enforce_playable(EV)
    performed = humanize(clean)
    performed.sort(key=lambda e: (e[0], e[1]))
    build_midi(performed, TEMPO, 'solo.mid')


if __name__ == '__main__':
    main()
