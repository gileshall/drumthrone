#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid -- a two minute solo for one drummer, General MIDI,
percussion channel 10 (notes 35..81).  Only mido is used.

Musical shape (56 bars of 4/4, tempo-mapped to 120 seconds):

   1- 4   statement of the motif: funk groove, ghost notes, one fill
   5- 8   the motif grows: ride bell, kick diddles, double strokes
   9-12   the same rhythm moves onto the toms
  13-16   half-time release, big and open, then a build
  17-20   bass drum eighths, snare chatter, into double time
  21-24   double-time ride energy
  25-28   high-energy development, syncopated hits, run down the kit
  29-32   near silence: side stick, pedal hat, congas, clave, then a
          snare roll that swells and resolves on the downbeat of bar 33
  33-36   the motif returns, loud and confident
  37-40   the motif in new clothes (toms, open hat, cowbell, doubles)
  41-44   question and answer between feet and hands, hands win
  45-48   long single-stroke runs travelling around the kit
  49-52   climax: fast singles and doubles, crashes on the downbeats
  53-56   final push; the fill carries into the last downbeat and the
          solo lands on a flam with cymbal and bass drum

Every note is placed with a little human timing and velocity scatter,
the tempo map surges and settles with the phrases, phrases lean forward
or hold back, and the whole thing is limited to two hands and two feet
at any instant.  Output is deterministic (fixed RNG seed).
"""

import random

from mido import Message, MidiFile, MidiTrack, MetaMessage

# ----------------------------------------------------------------------
# General MIDI percussion
# ----------------------------------------------------------------------
PPQ = 480
CHANNEL = 9                        # MIDI channel 10

BD, BD2 = 36, 35                   # bass drum 1, acoustic bass drum
SD, SS = 38, 37                    # snare, side stick
HHC, HHP, HHO = 42, 44, 46         # closed / pedal / open hi-hat
TOM1, TOM2, TOM3, TOM4 = 50, 48, 47, 45
FT1, FT2 = 43, 41                  # high / low floor tom
CR1, CR2, SPL, CHI = 49, 57, 55, 52
RIDE, BELL = 51, 53
TAMB, COW = 54, 56
CB_MUTE, CB_OPEN, CB_LOW = 62, 63, 64
CLAVE, WB_H, WB_L = 75, 76, 77
TRI_MUTE, TRI_OPEN = 80, 81
AG_H, AG_L = 67, 68
VIBRA = 58

FOOT = frozenset((BD, BD2, HHP))   # what the two feet can be doing

ROLE = {
    'K': BD, 'H': HHC, 'A': SD, 'A2': SD, 'g': SD, 'C': CR1,
    'P': HHP, 'S': SS,
    'T1': TOM1, 'T2': TOM2, 'T3': TOM3, 'T4': TOM4,
}

# ----------------------------------------------------------------------
# performance engine
# ----------------------------------------------------------------------
_rng = random.Random(20240601)     # fixed -> identical file every run
_events = []                       # (time in beats, note, velocity)
_phrase = [0.0, 1.0, 0.0, 0.0]     # start, end, rush at start, rush at end


def set_phrase(start, end, rush_start=0.0, rush_end=0.0):
    """A phrase can lean ahead of the beat or hold back, gradually."""
    _phrase[:] = [float(start), float(end), rush_start, rush_end]


def _time_shift(t):
    a, b, ra, rb = _phrase
    if b <= a:
        return 0.0
    x = (t - a) / (b - a)
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
    return ra + (rb - ra) * x


def _playable(t, note):
    """One drummer: never more than two hands and two feet at a time."""
    hands = total = 0
    for (t0, n, _v) in _events[-160:]:
        if -0.02 <= t0 - t <= 0.02:
            total += 1
            if n not in FOOT:
                hands += 1
    if total >= 4:
        return False
    if hands >= 2 and note not in FOOT:
        return False
    return True


def add(t, note, vel, jitter=0.007):
    """One drum hit: human timing, human velocity, human ghosting."""
    t = t + _time_shift(t)
    if jitter:
        t += _rng.uniform(-jitter, jitter)
    if vel < 45.0:                       # ghosts sit a hair behind
        t += 0.003 + _rng.uniform(0.0, 0.004)
    v = int(round(vel + _rng.uniform(-2.5, 2.5)))
    v = 1 if v < 1 else (127 if v > 127 else v)
    if t < 0.0:
        t = 0.0
    if not _playable(t, note):
        return
    _events.append((t, note, v))


def play(pattern, t, v=1.0, g=1.0, voices=None, start=0.0, span=99.0,
         skip=()):
    """Play a pattern (a list of (offset, role, velocity)) at beat t."""
    for off, role, vel in pattern:
        if off < start or off >= span or (off, role) in skip:
            continue
        if isinstance(role, int):
            note = role
        else:
            note = (voices or {}).get(role)
            if note is None:
                note = ROLE[role]
        if note is None:
            continue
        vv = vel * v
        if role == 'g':
            vv *= g
            if vv > 54.0:
                vv = 54.0
        add(t + off, note, vv)


# ----------------------------------------------------------------------
# the figures
# ----------------------------------------------------------------------
# The solo's motif: a syncopated funk/rock bar.  Backbeats on 2 and 4,
# a soft kick diddle after 3, ghost notes on the sixteenths.
MOTIF_A = [
    (0.00, 'K', 104), (0.00, 'H', 72),
    (0.50, 'H', 60),
    (0.75, 'g', 30),
    (1.00, 'A', 100), (1.00, 'H', 68),
    (1.50, 'H', 62),
    (1.75, 'g', 32),
    (2.00, 'K', 96), (2.00, 'H', 70),
    (2.25, 'K', 58),
    (2.50, 'H', 58), (2.50, 'g', 28),
    (3.00, 'A2', 102), (3.00, 'H', 66),
    (3.50, 'H', 56), (3.50, 'g', 30),
    (3.75, 'g', 34),
]

# Half-time feel: snare only on beat 3, cymbal keeping the pulse.
HALFTIME = [
    (0.00, 'C', 104), (0.00, 'K', 108),
    (0.75, 'g', 28),
    (1.00, 'H', 66),
    (1.50, 'H', 58), (1.50, 'g', 32),
    (1.75, 'g', 30),
    (2.00, 'A', 108), (2.00, 'K', 92),
    (2.50, 'H', 60), (2.50, 'g', 30),
    (3.00, 'H', 68),
    (3.50, 'H', 58), (3.50, 'g', 34),
    (3.75, 'g', 38),
]

# Double-time comping played under eighths on the ride.
DT = [
    (0.00, 'K', 104),
    (0.75, 'A', 94),
    (1.25, 'K', 74),
    (1.75, 'g', 34),
    (2.00, 'K', 96),
    (2.75, 'A2', 98),
    (3.25, 'K', 72),
    (3.50, 'g', 30),
    (3.75, 'g', 36),
]

# The quiet bar: side stick, pedal hat, lots of air.
QUIET = [
    (0.00, 'P', 76), (0.00, 'S', 96),
    (0.75, 'S', 38),
    (1.00, 'P', 66),
    (1.50, 'S', 88),
    (1.75, 'S', 36),
    (2.00, 'P', 72), (2.00, 'K', 82),
    (2.50, 'S', 34),
    (3.00, 'P', 68), (3.00, 'S', 92),
    (3.50, 'S', 34),
    (3.75, 'K', 64),
]


# ----------------------------------------------------------------------
# hands and feet idioms
# ----------------------------------------------------------------------
def run(t, span, notes, v0=80, v1=110, step=0.25):
    """A run of single strokes travelling over 'notes', with a swell."""
    n = len(notes)
    if n == 0:
        return
    pos = t
    for i, note in enumerate(notes):
        if pos >= t + span - 1e-9:
            break
        v = v0 + (v1 - v0) * (i / (n - 1.0))
        add(pos, note, v)
        pos += step


def doubles(t, drums, v0=80, v1=112, step=0.25):
    """Double strokes: every drum gets two hits before the next one."""
    seq = [d for d in drums for _ in (0, 1)]
    run(t, len(seq) * step, seq, v0, v1, step)


def ride_8ths(t, span, hat=RIDE, on=78, off=60, skip_first=False):
    n = int(round(span / 0.5))
    for i in range(n):
        if i == 0 and skip_first:
            continue
        add(t + 0.5 * i, hat, on if i % 2 == 0 else off)


def roll(t, span, drum=SD, v0=54, v1=120, step0=0.25, step1=0.083):
    """A roll that accelerates and swells, then resolves."""
    pos = t
    while pos < t + span - 1e-9:
        f = (pos - t) / span
        v = v0 + (v1 - v0) * (f ** 1.25)
        add(pos, drum, v)
        pos += step0 + (step1 - step0) * f


def build_bar(t, v=1.0, k0=74, k1=96):
    """Bass drum eighths under a backbeat and light hats: the build."""
    for i in range(8):
        add(t + 0.5 * i, BD, k0 + (k1 - k0) * i / 7.0)
    for b in (0.0, 1.0, 2.0, 3.0):
        add(t + b, HHC, 64.0 * v)
    add(t + 1.0, SD, 96.0 * v)
    add(t + 3.0, SD, 100.0 * v)
    add(t + 1.75, SD, 34.0 * v)
    add(t + 3.75, SD, 38.0 * v)


# ----------------------------------------------------------------------
# the solo
# ----------------------------------------------------------------------
def compose():
    # ==================================================================
    # 1.  bars 1-4  (beats 0-16)   the statement
    # ==================================================================
    set_phrase(0, 16, 0.008, -0.006)

    add(0.0, CR1, 102)
    add(0.0, BD, 106)
    play(MOTIF_A, 0.0, v=0.85, g=0.80, skip=((0.0, 'K'), (0.0, 'H')))

    play(MOTIF_A, 4.0, v=0.90, g=1.00)
    add(6.5, BD, 58)

    play(MOTIF_A, 8.0, v=0.94, g=1.15, skip=((3.5, 'H'),))
    add(11.5, HHO, 82)

    play(MOTIF_A, 12.0, v=0.96, g=1.20, span=2.0)
    run(14.0, 2.0, [SD, SD, SD, TOM1, TOM1, TOM2, TOM2, TOM3], 66, 108)

    # ==================================================================
    # 2.  bars 5-8  (16-32)  development: ride bell, kick doubles
    # ==================================================================
    set_phrase(16, 32, 0.000, -0.010)

    add(16.0, CR1, 108)
    add(16.0, BD, 110)
    play(MOTIF_A, 16.0, v=0.96, g=1.20, skip=((0.0, 'K'), (0.0, 'H')))

    play(MOTIF_A, 20.0, v=0.98, g=1.25, voices={'H': BELL})
    add(22.875, BD, 58)

    play(MOTIF_A, 24.0, v=0.97, g=1.30, voices={'H': RIDE, 'A2': TOM2})
    add(25.25, SD, 42)
    add(27.25, SD, 38)

    play(MOTIF_A, 28.0, v=1.00, g=1.30, voices={'H': RIDE}, span=2.0)
    doubles(30.0, [TOM1, TOM2, TOM3, TOM4], 76, 114)

    # ==================================================================
    # 3.  bars 9-12  (32-48)  the motif moves onto the toms
    # ==================================================================
    set_phrase(32, 48, -0.006, 0.008)

    add(32.0, CR2, 98)
    add(32.0, BD, 104)
    play(MOTIF_A, 32.0, v=0.94, g=1.10,
         voices={'H': RIDE, 'A': TOM1, 'A2': TOM2},
         skip=((0.0, 'K'), (0.0, 'H')))

    play(MOTIF_A, 36.0, v=0.96, g=1.10,
         voices={'H': RIDE, 'A': TOM2, 'A2': TOM3})
    add(38.0, FT2, 86)

    add(40.0, CR1, 106)
    add(40.0, BD, 106)
    play(MOTIF_A, 40.0, v=1.00, g=1.30, voices={'H': RIDE},
         skip=((0.0, 'K'), (0.0, 'H')))
    add(42.75, SD, 40)

    play(MOTIF_A, 44.0, v=0.98, g=1.20, voices={'H': RIDE}, span=2.0)
    run(46.0, 2.0, [TOM1, TOM2, TOM3, TOM4, FT1, FT2, SD, SD], 82, 116)

    # ==================================================================
    # 4.  bars 13-16  (48-64)  half-time release, then a build
    # ==================================================================
    set_phrase(48, 64, 0.010, 0.004)

    play(HALFTIME, 48.0, v=1.00, g=0.90, voices={'H': RIDE})
    add(50.5, FT1, 70)

    play(HALFTIME, 52.0, v=1.00, g=1.00, voices={'H': RIDE, 'A': TOM4},
         skip=((0.0, 'C'),))
    add(52.0, SPL, 86)

    play(HALFTIME, 56.0, v=0.98, g=1.00, voices={'H': RIDE}, span=2.0)
    play(HALFTIME, 56.0, v=1.00, g=1.10, voices={'H': RIDE, 'A': TOM3},
         start=2.0)
    add(59.5, FT1, 76)

    play(HALFTIME, 60.0, v=0.95, g=1.00, voices={'H': RIDE}, span=2.0)
    ride_8ths(62.0, 2.0, hat=RIDE, on=80, off=62)
    add(62.0, BD, 102)
    add(63.0, BD, 98)
    add(62.5, SD, 88)
    add(63.75, SD, 96)

    # ==================================================================
    # 5.  bars 17-20  (64-80)  building on bass drum eighths
    # ==================================================================
    set_phrase(64, 80, 0.006, -0.012)

    add(64.0, CR1, 108)
    build_bar(64.0, v=0.95, k0=72, k1=92)
    build_bar(68.0, v=1.00, k0=80, k1=102)
    add(69.75, SD, 46)

    add(72.0, CR2, 100)
    play(DT, 72.0, v=1.00, g=1.00)
    ride_8ths(72.0, 4.0, on=78, off=58, skip_first=True)

    play(DT, 76.0, v=1.00, g=1.10, voices={'A2': TOM2})
    ride_8ths(76.0, 4.0, hat=BELL, on=82, off=62)

    # ==================================================================
    # 6.  bars 21-24  (80-96)  double-time energy
    # ==================================================================
    set_phrase(80, 96, -0.008, 0.006)

    add(80.0, CR1, 112)
    add(80.0, BD, 108)
    play(DT, 80.0, v=1.00, g=1.00)
    ride_8ths(80.0, 4.0, on=80, off=60, skip_first=True)

    play(DT, 84.0, v=1.00, g=1.10, voices={'A': TOM1, 'A2': TOM3})
    ride_8ths(84.0, 4.0, on=80, off=60)

    play(DT, 88.0, v=1.00, g=1.20)
    ride_8ths(88.0, 4.0, on=82, off=62)

    play(DT, 92.0, v=1.00, g=1.10, span=2.0)
    ride_8ths(92.0, 2.0, on=80, off=60)
    doubles(94.0, [TOM1, TOM2, TOM3, TOM4], 84, 118)

    # ==================================================================
    # 7.  bars 25-28  (96-112)  high-energy development
    # ==================================================================
    set_phrase(96, 112, -0.010, 0.004)

    add(96.0, CR1, 114)
    add(96.0, BD, 110)
    play(DT, 96.0, v=1.00, g=1.20)
    ride_8ths(96.0, 4.0, on=84, off=64, skip_first=True)

    play(DT, 100.0, v=1.00, g=1.20, voices={'A2': TOM3})
    ride_8ths(100.0, 4.0, on=84, off=64)

    play(DT, 104.0, v=1.00, g=1.30, voices={'A': TOM2, 'A2': TOM4})
    ride_8ths(104.0, 4.0, on=82, off=62)
    add(107.5, SD, 54)

    play(MOTIF_A, 108.0, v=1.00, g=1.30, voices={'H': RIDE}, span=2.0)
    run(110.0, 2.0, [SD, TOM1, TOM2, TOM3, TOM4, FT1, SD, SD], 92, 122)

    # ==================================================================
    # 8.  bars 29-32  (112-128)  near silence, then a swelling roll
    # ==================================================================
    set_phrase(112, 128, 0.012, -0.004)

    play(QUIET, 112.0, v=1.00)
    add(113.25, CB_OPEN, 60)
    add(114.25, CB_MUTE, 56)

    play(QUIET, 116.0, v=0.70, voices={'S': SD})
    add(117.25, CLAVE, 70)
    add(118.25, CB_LOW, 62)

    for i in range(16):                      # crescendo on the snare
        add(120.0 + 0.25 * i, SD, 32 + i * 2.0)
    add(120.0, BD, 66)
    add(122.0, BD, 70)

    add(124.0, BD, 68)
    add(126.0, BD, 76)
    roll(124.0, 3.8, SD, 62, 122, 0.25, 0.090)

    # ==================================================================
    # 9.  bars 33-36  (128-144)  the motif returns, bigger
    # ==================================================================
    set_phrase(128, 144, -0.006, 0.010)

    add(128.0, CR1, 118)
    add(128.0, BD, 114)
    play(MOTIF_A, 128.0, v=1.04, g=1.30, skip=((0.0, 'K'), (0.0, 'H')))

    play(MOTIF_A, 132.0, v=1.04, g=1.35, voices={'H': BELL})
    add(134.0, SPL, 96)

    play(MOTIF_A, 136.0, v=1.00, g=1.30, voices={'A2': TOM2})
    add(138.0, FT1, 82)

    play(MOTIF_A, 140.0, v=1.04, g=1.30, voices={'H': RIDE}, span=2.0)
    run(142.0, 2.0, [SD, SD, TOM1, TOM2, TOM3, TOM4, FT1, FT2], 92, 122)

    # ==================================================================
    # 10. bars 37-40  (144-160)  the motif in new clothes
    # ==================================================================
    set_phrase(144, 160, 0.008, -0.006)

    add(144.0, CR2, 100)
    play(MOTIF_A, 144.0, v=1.00, g=1.30,
         voices={'A': TOM1, 'A2': TOM4}, skip=((0.0, 'H'),))

    play(MOTIF_A, 148.0, v=1.00, g=1.40, skip=((3.5, 'H'),))
    add(151.5, HHO, 84)
    add(151.75, SD, 44)

    play(MOTIF_A, 152.0, v=1.00, g=1.30, voices={'H': RIDE})
    add(154.75, BD, 60)
    add(155.25, BD, 66)
    add(155.25, COW, 78)

    play(MOTIF_A, 156.0, v=1.00, g=1.30, span=2.0)
    run(158.0, 2.0, [TOM4, TOM3, TOM2, TOM1, SD, TOM3, TOM4, SD], 90, 120)

    # ==================================================================
    # 11. bars 41-44  (160-176)  question and answer, hands vs feet
    # ==================================================================
    set_phrase(160, 176, -0.008, 0.004)

    add(160.0, CR2, 104)
    add(160.0, BD, 112)
    add(160.5, BD, 74)
    add(161.0, BD, 90)
    add(161.5, BD, 82)
    run(162.0, 1.0, [TOM1, TOM2, TOM3, TOM4], 88, 106)
    add(163.0, SD, 98)
    add(163.25, SD, 44)
    add(163.5, TOM4, 88)
    add(163.75, SD, 48)

    add(164.0, BD, 108)
    add(164.5, BD, 84)
    run(165.0, 1.0, [TOM1, TOM2, TOM3, TOM4], 90, 108)
    add(166.0, BD, 110)
    add(166.5, BD, 86)
    run(167.0, 1.0, [SD, TOM2, TOM3, TOM4], 92, 110)

    bd_v = [104, 92, 100, 94, 106, 96, 108, 100]
    sd_v = [62, 68, 74, 80, 86, 92, 98, 104]
    for i in range(8):
        add(168.0 + 0.5 * i, BD, bd_v[i])
        add(168.25 + 0.5 * i, SD, sd_v[i])

    run(172.0, 2.0, [SD, TOM1, SD, TOM2, SD, TOM3, SD, TOM4], 86, 114)
    doubles(174.0, [TOM4, TOM3, TOM2, TOM1], 90, 118)

    # ==================================================================
    # 12. bars 45-48  (176-192)  long runs around the kit
    # ==================================================================
    set_phrase(176, 192, -0.012, -0.002)

    add(176.0, CR1, 116)
    add(176.0, BD, 112)
    run(176.0, 4.0, [SD, TOM1, TOM2, TOM3, TOM4, FT1, FT2, SD] * 2, 88, 118)

    run(180.0, 2.0, [FT2, FT1, TOM4, TOM3, TOM2, TOM1, SD, SD], 92, 118)
    run(182.0, 2.0, [TOM1, TOM1, TOM2, TOM2, TOM3, TOM3, TOM4, TOM4],
        96, 120)

    doubles(184.0, [TOM1, TOM2, TOM3, TOM4], 94, 118)
    doubles(186.0, [FT1, FT2, TOM4, TOM2], 98, 122)

    add(188.0, BD, 112)
    add(188.0, CR2, 108)
    run(188.0, 1.0, [SD, SD, TOM1, TOM1], 100, 110)
    run(189.0, 1.0, [TOM2, TOM2, TOM3, TOM3], 104, 112)
    roll(190.0, 2.0, SD, 70, 124, 0.20, 0.085)

    # ==================================================================
    # 13. bars 49-52  (192-208)  climax
    # ==================================================================
    set_phrase(192, 208, -0.014, 0.006)

    add(192.0, CR1, 122)
    add(192.0, CR2, 112)
    add(192.0, BD, 118)
    play(MOTIF_A, 192.0, v=1.08, g=1.40, skip=((0.0, 'K'), (0.0, 'H')))

    add(196.0, CHI, 100)
    play(DT, 196.0, v=1.05, g=1.30)
    ride_8ths(196.0, 4.0, on=86, off=66, skip_first=True)

    play(DT, 200.0, v=1.05, g=1.30, voices={'A': TOM1, 'A2': TOM2})
    ride_8ths(200.0, 4.0, on=86, off=66)

    play(DT, 204.0, v=1.05, g=1.30, span=2.0)
    ride_8ths(204.0, 2.0, on=86, off=66)
    run(206.0, 2.0, [SD, SD, SD, TOM1, TOM2, TOM3, TOM4, FT2], 100, 126)

    # ==================================================================
    # 14. bars 53-56  (208-224)  final push and the last hit
    # ==================================================================
    set_phrase(208, 224, 0.008, -0.012)

    play(HALFTIME, 208.0, v=1.05, g=1.00, voices={'H': RIDE})
    add(210.0, FT2, 88)

    add(212.0, CR1, 110)
    build_bar(212.0, v=1.00, k0=88, k1=108)

    run(216.0, 4.0, [SD, TOM1, TOM2, TOM3, TOM4, FT1, FT2, FT2] * 2,
        96, 126)

    doubles(220.0, [TOM1, TOM2, TOM3, TOM4], 100, 124)
    doubles(222.0, [FT1, FT2, TOM4, SD], 104, 126)

    add(223.93, SD, 56)          # grace note of the final flam
    add(224.0, SD, 122)
    add(224.0, CR1, 127)
    add(224.0, BD, 120)


# ----------------------------------------------------------------------
# tempo: the pulse surges and settles with the phrases
# ----------------------------------------------------------------------
END_BEAT = 224.0                    # 56 bars of 4/4
TAIL_BEATS = 2.0                    # the last hit rings out

TEMPO_POINTS = [
    (0, 100.0), (8, 102.0), (16, 105.0), (24, 107.0),
    (32, 106.0), (40, 108.0),
    (48, 100.0), (56, 99.0), (60, 98.0),
    (64, 103.0), (68, 105.0), (72, 108.0), (80, 112.0),
    (88, 111.0), (96, 114.0), (104, 113.0), (108, 116.0),
    (112, 100.0), (120, 98.0), (124, 100.0),
    (128, 108.0), (136, 112.0), (144, 110.0), (152, 113.0),
    (160, 112.0), (168, 114.0), (176, 116.0), (184, 118.0),
    (192, 120.0), (200, 119.0), (208, 118.0), (216, 122.0),
    (220, 120.0), (224, 116.0),
]


def tempo_at(beat):
    pts = TEMPO_POINTS
    if beat <= pts[0][0]:
        return pts[0][1]
    for i in range(len(pts) - 1):
        b0, t0 = pts[i]
        b1, t1 = pts[i + 1]
        if beat <= b1:
            if b1 == b0:
                return t1
            return t0 + (t1 - t0) * (beat - b0) / (b1 - b0)
    return pts[-1][1]


def seconds_upto(beats):
    total = 0.0
    b = 0
    while b < beats:
        total += 60.0 / tempo_at(b)
        b += 1
    return total


# ----------------------------------------------------------------------
# note lengths (a few players honour note-offs on percussion)
# ----------------------------------------------------------------------
def note_len(note):
    if note in (CR1, CR2, SPL, CHI):
        return 2.5
    if note == HHO:
        return 0.55
    if note in (HHC, RIDE, BELL):
        return 0.30
    if note == HHP:
        return 0.25
    if note in (TRI_MUTE, TRI_OPEN, VIBRA):
        return 1.5
    return 0.45


# ----------------------------------------------------------------------
# render
# ----------------------------------------------------------------------
def write_midi(path):
    scale = seconds_upto(END_BEAT) / 120.0     # exactly 120 s of content

    notes = [[t, n, v, t + note_len(n)] for (t, n, v) in _events]

    # never leave a note ringing under the next hit on the same drum
    by_note = {}
    for e in notes:
        by_note.setdefault(e[1], []).append(e)
    for lst in by_note.values():
        lst.sort(key=lambda e: e[0])
        for i in range(len(lst) - 1):
            if lst[i][3] > lst[i + 1][0]:
                lst[i][3] = lst[i + 1][0] - 0.005
        for e in lst:
            if e[3] - e[0] < 0.03:
                e[3] = e[0] + 0.03

    msgs = []                                  # (tick, order, kind, a, b)
    for (t, note, vel, end) in notes:
        msgs.append((int(round(t * PPQ)), 2, 'on', note, vel))
        msgs.append((int(round(end * PPQ)), 0, 'off', note, 0))
    for b in range(0, int(END_BEAT) + 1):
        bpm = tempo_at(b) * scale
        msgs.append((int(round(b * PPQ)), 1, 'tempo',
                     int(round(60000000.0 / bpm)), 0))
    msgs.sort(key=lambda m: (m[0], m[1]))

    track = MidiTrack()
    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             clocks_per_click=24,
                             notated_32nd_notes_per_beat=8, time=0))

    last = 0
    for (tick, _order, kind, a, b) in msgs:
        delta = tick - last
        if delta < 0:
            delta = 0
        last = tick
        if kind == 'on':
            track.append(Message('note_on', channel=CHANNEL, note=a,
                                 velocity=b, time=delta))
        elif kind == 'off':
            track.append(Message('note_off', channel=CHANNEL, note=a,
                                 velocity=0, time=delta))
        else:
            track.append(MetaMessage('set_tempo', tempo=a, time=delta))

    track.append(MetaMessage('end_of_track', time=int(TAIL_BEATS * PPQ)))

    mid = MidiFile(type=1)
    mid.tracks.append(track)
    mid.save(path)


def main():
    compose()
    write_midi('solo.mid')


if __name__ == '__main__':
    main()
