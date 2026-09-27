#!/usr/bin/env python3
"""
drum_solo.py
============

Writes ``solo.mid``: a two minute General MIDI drum solo for one drummer,
on channel 10, using the full GM percussion set (notes 35-81).

The whole piece grows out of a two beat cell -- kick, ghost tap, accent,
off beat kick -- which is stated, varied, fragmented and finally re-stated.
Density and dynamics are shaped in long arcs, the tempo map leans forward
in the hot passages and settles back when the music relaxes, and every
groove carries a deliberate placement (light swing plus per-instrument
push / lay-back) rather than random jitter.

Everything is deterministic: running it twice gives the same file.
"""

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

# ----------------------------------------------------------------- constants
PPQ = 480
CH = 9              # MIDI channel 10 -> GM percussion
SW = 0.56           # swung offbeat eighth (sits a touch behind the middle)

KICK, SNARE, STICK = 36, 38, 37
HATP, HAT, HATO = 44, 42, 46
RIDE, BELL = 51, 53
CRASH, CRASH2 = 49, 57
SPLASH, CHINA = 55, 52
TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_FH, TOM_FL = 50, 48, 47, 45, 43, 41
COWBELL, WBH, WBL, CLAVES, TAMB = 56, 76, 77, 75, 54
CABASA, MARACAS = 69, 70
CONGAH, CONGAM, CONGAL = 63, 62, 64
BONGOH, BONGOL = 60, 61
TIMBH, TIMBL = 65, 66
TRI, AGOGOH, AGOGOL = 81, 67, 68

FOOT_NOTES = (35, 36, 44)

# ------------------------------------------------------------------- events
events = []


def add(beat, note, vel):
    """Place one stroke.  'H' = a hand, 'F' = a foot."""
    events.append((int(round(beat * PPQ)), note,
                   int(max(1, min(127, round(vel)))),
                   'F' if note in FOOT_NOTES else 'H'))


def sw(p):
    """Swing an offbeat eighth a little late."""
    f = p - int(p)
    return int(p) + SW if abs(f - 0.5) < 1e-9 else p


def run(b, start, seq, step=0.25, v0=80, v1=104, accent=0):
    """A rolled-out run of singles that walks along the kit."""
    n = len(seq)
    for i, note in enumerate(seq):
        v = v0 if n == 1 else v0 + (v1 - v0) * i / (n - 1.0)
        if accent and i % 4 == 0:
            v += accent
        add(b + start + i * step, note, v)


def roll(b, start, dur, v0, v1, inst=SNARE, step=0.125):
    """A double stroke roll that swells from v0 to v1."""
    n = max(1, int(round(dur / step)))
    for i in range(n):
        v = v0 if n == 1 else v0 + (v1 - v0) * i / (n - 1.0)
        add(b + start + i * step, inst, v)


def swing_ride(b, vel=62, push=0.0, inst=RIDE, no_first=False):
    """The spang-a-lang: quarters with swung offbeats after 2 and 4."""
    pts = ((0.0, 6), (1.0, 0), (2.0, 2), (2.0 + SW, -9), (3.0, 0), (3.0 + SW, -9))
    for i, (p, dv) in enumerate(pts):
        if no_first and i == 0:
            continue
        add(b + p + push, inst, vel + dv)


# -------------------------------------------------------------------- bars
def theme_bar(b, base=90, crash=False, ride_inst=RIDE, push=-0.010, var=0):
    """One bar of the main groove -- the motif twice, second one varied."""
    if crash:
        add(b + push, CRASH, base + 20)
    swing_ride(b, base - 26, push=push, inst=ride_inst, no_first=crash)
    # motif: kick - ghost - accent - offbeat kick
    add(b + 0.0, KICK, base - 8)
    add(b + 0.75, SNARE, base * 0.42)
    add(b + 1.0, SNARE, base + 2)
    add(b + 1.5, KICK, base - 16)
    # second half of the bar
    add(b + 2.0, KICK, base - 8)
    if var == 0:
        add(b + 2.75, SNARE, base * 0.44)
        add(b + 3.0, SNARE, base - 2)
        add(b + 3.5, KICK, base - 18)
    elif var == 1:
        add(b + 2.5, SNARE, base * 0.50)
        add(b + 2.75, SNARE, base * 0.62)
        add(b + 3.0, SNARE, base - 2)
        add(b + 3.5, SNARE, base * 0.46)
    elif var == 2:
        add(b + 2.5, KICK, base - 14)
        add(b + 3.0, SNARE, base - 2)
        add(b + 3.25, SNARE, base * 0.50)
        add(b + 3.5, TOM_LM, base - 18)
    else:
        add(b + 2.75, SNARE, base * 0.46)
        add(b + 3.0, SNARE, base - 2)
        add(b + 3.5, HATO, base - 26)
    add(b + 1.0, HATP, 50)
    add(b + 3.0, HATP, 50)


def rolling_bar(b, base=96, crash=False, push=-0.014, kick=0, open_at=(), snare_acc=True):
    """Driving bar: sixteenths on the hi-hat with a syncopated kick."""
    if crash:
        add(b + push, CRASH, base + 12)
    for i in range(16):
        p = i * 0.25
        v = base - 30
        if i % 4 == 0:
            v += 16
        elif i % 2 == 0:
            v += 5
        if i in open_at:
            add(b + p + push, HATO, v + 10)
        else:
            add(b + p + push, HAT, v)
    if snare_acc:
        add(b + 1.0 + push * 0.5, SNARE, base + 6)
        add(b + 3.0 + push * 0.5, SNARE, base + 2)
        add(b + 1.75, SNARE, base * 0.38)
        add(b + 3.25, SNARE, base * 0.34)
    if kick == 0:
        add(b + 0.0, KICK, base - 8)
        add(b + 1.75, KICK, base - 16)
        add(b + 2.5, KICK, base - 14)
    elif kick == 1:
        add(b + 0.0, KICK, base - 8)
        add(b + 2.25, KICK, base - 14)
        add(b + 3.5, KICK, base - 12)
    else:
        add(b + 0.0, KICK, base - 6)
        add(b + 1.5, KICK, base - 16)
        add(b + 2.75, KICK, base - 12)
        add(b + 3.5, KICK, base - 14)
    add(b + 1.0, HATP, 52)
    add(b + 3.0, HATP, 52)


def halftime_bar(b, base=104, crash=False, push=0.0):
    """A breath: half time, bell of the ride, one big backbeat."""
    if crash:
        add(b + push, CRASH, base + 8)
    for i in range(8):
        if i == 0 and crash:
            continue
        p = sw(i * 0.5)
        inst = BELL if i % 4 == 0 else RIDE
        v = base - 34 + (10 if i % 2 == 0 else 0)
        add(b + p + push, inst, v)
    add(b + 2.0, SNARE, base + 8)
    add(b + 2.75, SNARE, base - 46)
    add(b + 0.0, KICK, base - 12)
    add(b + 3.5, KICK, base - 16)
    add(b + 2.0, HATP, 52)


def fill_bar(b, base=94, big=False):
    """A one bar fill that carries into the next downbeat."""
    add(b + 0.0, KICK, base - 16)
    run(b, 0.0, [SNARE] * 4, 0.25, base - 32, base - 12)
    add(b + 1.5, SNARE, base - 22)
    add(b + 1.75, SNARE, base - 10)
    run(b, 2.0, [TOM_HM, TOM_HM, TOM_LM, TOM_LM], 0.25, base - 8, base)
    if big:
        run(b, 3.0, [TOM_L, TOM_FH, TOM_FH, TOM_FL], 0.25, base + 2, base + 16)
    else:
        add(b + 3.0, TOM_L, base)
        add(b + 3.25, TOM_FH, base + 4)
        add(b + 3.5, TOM_FH, base + 8)
        add(b + 3.75, TOM_FL, base + 14)


def tom_groove_bar(b, base=100, push=-0.012):
    """Groove that moves around the toms."""
    run(b, 0.0, [TOM_H, TOM_H, TOM_HM, TOM_HM], 0.25, base - 24, base - 14)
    run(b, 1.0, [TOM_LM, TOM_LM, TOM_L, TOM_L], 0.25, base - 18, base - 8)
    add(b + 2.0, SNARE, base)
    add(b + 2.25, SNARE, base - 40)
    run(b, 2.5, [TOM_LM, TOM_L, TOM_FH, TOM_FL], 0.25, base - 16, base - 4)
    add(b + 3.5, SNARE, base - 6)
    add(b + 3.75, SNARE, base - 30)
    add(b + 0.0, KICK, base - 10)
    add(b + 2.5, KICK, base - 16)
    add(b + 1.0, HATP, 54)
    add(b + 3.0, HATP, 54)


def build_bar(b, base=100):
    """A bar that crescendos into the next section."""
    add(b + 0.0, KICK, base - 14)
    add(b + 0.0, SPLASH, base - 40)
    run(b, 0.0, [STICK, STICK, SNARE, SNARE], 0.25, base - 34, base - 14)
    run(b, 1.0, [SNARE] * 4, 0.25, base - 10, base + 2)
    run(b, 2.0, [TOM_H, TOM_HM, TOM_LM, TOM_L], 0.25, base, base + 8)
    run(b, 3.0, [TOM_L, TOM_FH, TOM_FH, TOM_FL], 0.25, base + 6, base + 16)


# ---------------------------------------------------------------- sections
def sec_intro():
    # bar 1 -- the pulse alone
    add(0.0, RIDE, 62)
    add(1.0, RIDE, 54)
    add(2.0, RIDE, 56)
    add(3.0, RIDE, 52)
    add(1.0, HATP, 46)
    add(3.0, HATP, 46)
    # bar 2 -- first snare, ghosts around it
    swing_ride(4.0, 56, push=0.012)
    add(4.75, SNARE, 26)
    add(5.0, SNARE, 76)
    add(5.25, SNARE, 22)
    add(7.0, SNARE, 68)
    add(5.0, HATP, 46)
    add(7.0, HATP, 46)
    # bar 3 -- the bass drum arrives
    swing_ride(8.0, 60, push=0.004)
    add(8.0, KICK, 78)
    add(10.0 + SW, KICK, 66)
    add(9.0, SNARE, 82)
    add(11.0, SNARE, 78)
    add(8.75, SNARE, 26)
    add(10.25, SNARE, 24)
    add(11.75, SNARE, 30)
    add(9.0, HATP, 50)
    add(11.0, HATP, 50)
    # bar 4 -- fill to the top
    add(12.0, KICK, 78)
    run(12.0, 0.0, [SNARE] * 6, 0.25, 58, 84)
    run(12.0, 1.5, [SNARE, SNARE], 0.25, 88, 96)
    run(12.0, 2.0, [TOM_HM, TOM_HM, TOM_LM, TOM_LM], 0.25, 88, 98)
    run(12.0, 3.0, [TOM_L, TOM_FH, TOM_FH, TOM_FL], 0.25, 96, 110)
    add(16.0, CRASH, 112)
    add(16.0, KICK, 100)
    add(16.0, SNARE, 62)


def sec_theme():
    theme_bar(16, base=88, crash=True, var=0)
    theme_bar(20, base=88, var=1)
    theme_bar(24, base=90, var=2)
    fill_bar(28, base=92)
    theme_bar(32, base=92, crash=True, var=0)
    theme_bar(36, base=92, var=3, ride_inst=BELL)
    rolling_bar(40, base=94, kick=0)
    fill_bar(44, base=98, big=True)
    theme_bar(48, base=94, crash=True, var=1)
    build_bar(52, base=100)


def sec_build1():
    rolling_bar(56, base=100, crash=True, kick=0)
    rolling_bar(60, base=102, kick=2, open_at=(15,))
    tom_groove_bar(64, base=102)
    tom_groove_bar(68, base=106)
    # 72-76 -- last push before the hot chorus
    add(72.0, COWBELL, 92)
    add(72.0, KICK, 102)
    run(72, 0.0, [SNARE] * 4, 0.25, 74, 92)
    run(72, 1.0, [SNARE] * 4, 0.25, 88, 102)
    run(72, 2.0, [TOM_H, TOM_HM, TOM_LM, TOM_L], 0.25, 94, 106)
    run(72, 3.0, [TOM_L, TOM_FH, TOM_FL, TOM_FL], 0.25, 98, 112)
    roll(74.0, 0.0, 1.0, 60, 112)
    run(75.0, 0.0, [TOM_FL, TOM_FH, TOM_L, TOM_LM, TOM_HM, TOM_H, SNARE, SNARE],
        0.125, 72, 122)


def sec_hot():
    rolling_bar(76, base=106, crash=True, kick=0)
    rolling_bar(80, base=106, kick=1, open_at=(15,))
    rolling_bar(84, base=108, kick=2)
    fill_bar(88, base=110, big=True)
    rolling_bar(92, base=108, crash=True, kick=0)
    rolling_bar(96, base=108, kick=2, open_at=(11,))
    halftime_bar(100, base=104)
    halftime_bar(104, base=106, crash=True)
    rolling_bar(108, base=110, kick=1)
    # 112-116 -- a fill that empties out so the next crash lands soft
    add(112.0, CRASH2, 110)
    add(112.0, KICK, 106)
    run(112, 0.0, [SNARE] * 4, 0.25, 84, 96)
    run(112, 1.0, [SNARE, TOM_HM, TOM_LM, TOM_L], 0.25, 92, 104)
    roll(112, 2.0, 1.0, 88, 106)
    run(112, 3.0, [TOM_L, TOM_FH, TOM_FL, TOM_FL], 0.25, 100, 114)
    add(113.5, KICK, 98)


def sec_breathe():
    # 116 -- everything settles back
    add(116.0, CRASH, 98)
    add(116.0, KICK, 78)
    swing_ride(116.0, 54, push=0.016, no_first=True)
    add(117.0, HATP, 46)
    add(119.0, HATP, 46)
    add(119.5, SNARE, 28)
    # 120
    swing_ride(120.0, 54, push=0.016)
    add(121.0, STICK, 76)
    add(123.0, STICK, 70)
    add(120.0, KICK, 64)
    add(122.0 + SW, KICK, 58)
    add(121.0, HATP, 46)
    add(123.0, HATP, 46)
    add(122.75, SNARE, 30)
    # 124
    swing_ride(124.0, 56, push=0.016)
    add(125.0, STICK, 78)
    add(127.0, STICK, 72)
    add(124.0, KICK, 66)
    add(126.0, KICK, 62)
    add(126.75, SNARE, 34)
    add(127.25, SNARE, 30)
    add(125.0, HATP, 48)
    add(127.0, HATP, 48)
    # 128 -- very sparse, woodblock colour
    swing_ride(128.0, 52, push=0.014)
    add(129.0, WBH, 62)
    add(131.0, WBL, 58)
    add(128.0, KICK, 62)
    add(130.0, TOM_LM, 54)
    add(130.5, TOM_L, 52)
    # 132 -- the long swell that resolves into the next section
    add(132.0, KICK, 76)
    roll(132.0, 0.0, 2.0, 34, 92)
    run(134.0, 0.0, [TOM_FL, TOM_FH, TOM_L, TOM_LM], 0.25, 62, 82)
    roll(135.0, 0.0, 1.0, 84, 124)


def sec_build2():
    theme_bar(136, base=92, crash=True, var=0, push=-0.004)
    theme_bar(140, base=94, var=1, push=-0.006)
    rolling_bar(144, base=100, kick=0)
    rolling_bar(148, base=102, kick=1, open_at=(15,))
    rolling_bar(152, base=106, kick=2)
    # 156-160 -- toms and singles, louder
    add(156.0, CRASH2, 104)
    add(156.0, KICK, 100)
    run(156, 0.0, [TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM, TOM_L, TOM_L], 0.25, 84, 104)
    run(156, 2.0, [SNARE] * 4, 0.25, 92, 106)
    run(156, 3.0, [SNARE, SNARE, TOM_HM, TOM_LM], 0.25, 96, 110)
    add(157.0, KICK, 98)
    add(158.0, KICK, 102)
    add(159.0, KICK, 98)
    # 160-164 -- everything the drummer has
    add(160.0, CRASH, 112)
    add(160.0, KICK, 108)
    roll(160.0, 0.0, 2.0, 66, 118)
    run(162.0, 0.0, [TOM_H, TOM_HM, TOM_LM, TOM_L], 0.25, 104, 118)
    roll(163.0, 0.0, 1.0, 108, 126)
    add(162.0, KICK, 108)
    add(163.5, KICK, 104)


def sec_climax():
    rolling_bar(164, base=112, crash=True, kick=0)
    rolling_bar(168, base=112, kick=1, open_at=(15,))
    rolling_bar(172, base=114, kick=2, open_at=(11,))
    fill_bar(176, base=116, big=True)

    # phrase 1 -- single strokes that travel around the kit
    add(180.0, CRASH, 118)
    add(180.0, KICK, 108)
    run(180, 0.0,
        [SNARE, SNARE, TOM_H, TOM_H, TOM_HM, TOM_HM, TOM_LM, TOM_LM,
         TOM_L, TOM_L, TOM_FH, TOM_FH, TOM_FL, TOM_FL, TOM_L, TOM_LM],
        0.25, 78, 112, 16)
    add(181.0, KICK, 98)
    add(182.0, KICK, 102)
    add(183.0, KICK, 98)
    add(182.0, HATP, 54)
    add(183.5, HATP, 54)

    # phrase 2 -- double strokes, hands swapping around the kit
    add(184.0, CRASH2, 116)
    add(184.0, KICK, 106)
    for i, (p, inst) in enumerate([(0.0, SNARE), (0.5, SNARE), (1.0, TOM_HM), (1.5, TOM_HM),
                                   (2.0, TOM_LM), (2.5, TOM_LM), (3.0, TOM_FL), (3.5, TOM_FL)]):
        v = 106 - (i % 4) * 3
        add(184.0 + p, inst, v)
        add(184.0 + p + 0.125, inst, v - 18)
    add(185.0, KICK, 98)
    add(186.0, KICK, 102)
    add(187.0, KICK, 96)
    add(186.0, HATP, 54)

    # phrase 3 -- accented singles
    add(188.0, CRASH, 116)
    add(188.0, KICK, 106)
    run(188, 0.0, [SNARE, TOM_H, SNARE, TOM_HM, SNARE, TOM_HM, SNARE, TOM_LM],
        0.25, 86, 104, 14)
    run(188, 2.0, [TOM_LM, TOM_L, TOM_L, TOM_FH, TOM_FL, TOM_FL, TOM_FH, TOM_L],
        0.25, 92, 112, 12)
    add(189.0, KICK, 98)
    add(190.0, KICK, 102)
    add(191.0, KICK, 100)

    # phrase 4 -- congas, maracas and one last roll into the reprise
    for i in range(8):
        add(192.0 + i * 0.25, MARACAS, 34 + i * 3)
    for i, inst in enumerate([CONGAH, CONGAM, CONGAM, CONGAL]):
        add(192.0 + sw(i * 0.5), inst, 84 + i * 5)
    add(192.0, KICK, 98)
    run(194.0, 0.0, [CONGAL, BONGOL, BONGOH, TIMBL], 0.25, 88, 100)
    add(194.0, KICK, 100)
    roll(195.0, 0.0, 1.0, 80, 124)

    # the motif comes home, full tilt
    theme_bar(196, base=112, crash=True, var=0)
    theme_bar(200, base=112, var=1)
    rolling_bar(204, base=114, kick=2)
    rolling_bar(208, base=114, kick=1, open_at=(15,))

    # the last big fill of the climax
    add(212.0, CRASH2, 112)
    add(212.0, KICK, 108)
    roll(212.0, 0.0, 2.0, 70, 120)
    run(214.0, 0.0, [TOM_H, TOM_HM, TOM_LM, TOM_L], 0.25, 104, 116)
    run(215.0, 0.0, [TOM_L, TOM_FH, TOM_FL, TOM_FL], 0.25, 108, 122)
    add(214.0, KICK, 106)
    add(215.0, KICK, 104)


def sec_outro():
    add(216.0, CRASH, 120)
    add(216.0, KICK, 110)
    add(216.0, SNARE, 66)
    add(217.0, RIDE, 72)
    add(218.0, RIDE, 64)
    add(219.0, RIDE, 68)
    add(218.0, HATP, 50)
    add(219.5, SNARE, 30)
    theme_bar(220, base=96, var=0, push=0.014, ride_inst=BELL)
    # the last fill, settling
    add(224.0, KICK, 88)
    run(224, 0.0, [SNARE] * 4, 0.25, 58, 76)
    run(224, 1.0, [SNARE] * 4, 0.25, 68, 84)
    run(224, 2.0, [TOM_HM, TOM_HM, TOM_LM, TOM_LM], 0.25, 72, 88)
    run(224, 3.0, [TOM_L, TOM_FH, TOM_FH, TOM_FL], 0.25, 76, 96)
    # and the last word
    add(228.0, CRASH, 122)
    add(228.0, KICK, 112)


# -------------------------------------------------------------------- tempo
TEMPO = [
    (0, 96), (8, 100), (16, 104), (32, 106), (48, 108), (56, 110),
    (64, 114), (72, 118), (76, 122), (96, 123), (116, 124),
    (118, 118), (120, 110), (124, 104), (128, 100), (136, 98),
    (144, 108), (152, 116), (160, 126), (164, 132), (190, 134),
    (216, 134), (220, 126), (224, 112), (228, 96),
]

END_BEAT = 230


def tempo_map(points):
    out = []
    for i in range(len(points) - 1):
        b0, t0 = points[i]
        b1, t1 = points[i + 1]
        span = b1 - b0
        if span <= 0:
            continue
        steps = max(1, int(round(span / 2.0)))
        for k in range(steps):
            frac = k / float(steps)
            out.append((b0 + span * frac, t0 + (t1 - t0) * frac))
    out.append(points[-1])
    return out


# ---------------------------------------------------------------- assembly
def sanitize(evs):
    """One drummer: never more than two hands and two feet at one instant."""
    buckets = {}
    for e in evs:
        buckets.setdefault(e[0], []).append(e)
    out = []
    for t in sorted(buckets):
        hands = [e for e in buckets[t] if e[3] == 'H']
        feet = [e for e in buckets[t] if e[3] == 'F']
        hands.sort(key=lambda e: (-e[2], e[1]))
        feet.sort(key=lambda e: (-e[2], e[1]))
        out.extend(hands[:2])
        out.extend(feet[:2])
    out.sort(key=lambda e: (e[0], e[1]))
    return out


def write_midi(evs, tempo_points, end_beat):
    mid = MidiFile(type=1, ticks_per_beat=PPQ)

    cond = MidiTrack()
    mid.tracks.append(cond)
    cond.append(MetaMessage('track_name', name='Drum Solo', time=0))
    last = 0
    for beat, bpm in tempo_map(tempo_points):
        tick = int(round(beat * PPQ))
        if tick < last:
            continue
        cond.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm), time=tick - last))
        last = tick
    cond.append(MetaMessage('end_of_track', time=max(0, int(end_beat * PPQ) - last)))

    tr = MidiTrack()
    mid.tracks.append(tr)
    tr.append(MetaMessage('track_name', name='Drums', time=0))
    tr.append(Message('program_change', channel=CH, program=0, time=0))

    raw = []
    for tick, note, vel, _kind in evs:
        raw.append((tick, 0, note, vel))        # note on
        raw.append((tick + 1, 1, note, 0))      # note off
    raw.sort(key=lambda x: (x[0], x[1], x[2]))

    last = 0
    for tick, is_off, note, vel in raw:
        dt = tick - last
        if is_off:
            tr.append(Message('note_off', channel=CH, note=note, velocity=0, time=dt))
        else:
            tr.append(Message('note_on', channel=CH, note=note, velocity=vel, time=dt))
        last = tick
    tr.append(MetaMessage('end_of_track', time=max(0, int(end_beat * PPQ) - last)))

    mid.save('solo.mid')


def main():
    sec_intro()
    sec_theme()
    sec_build1()
    sec_hot()
    sec_breathe()
    sec_build2()
    sec_climax()
    sec_outro()
    write_midi(sanitize(events), TEMPO, END_BEAT)


if __name__ == '__main__':
    main()
