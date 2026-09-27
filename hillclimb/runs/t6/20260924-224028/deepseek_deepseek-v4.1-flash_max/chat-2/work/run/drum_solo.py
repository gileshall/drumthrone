#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid: a two minute General MIDI drum solo on MIDI channel 10.

Pure Python 3 + mido.  Everything (including all human timing jitter) comes
from a fixed random seed, so the file is byte-for-byte identical every run.

Musical shape:
    bars  1- 4  motif A stated, answered with a pickup
    bars  5- 8  same motif on the ride, more ghost notes
    bars  9-12  motif with the backbeat moved onto the toms
    bars 13-16  density/dynamics climb, hands fall down the toms
    bars 17-18  single stroke fill into the downbeat
    bars 19-26  development: toms, syncopation, big fill
    bars 27-30  sudden drop: rim clicks, pedal hat, whisper motif
    bars 31-34  long snare roll that swells and resolves on a crash
    bars 35-42  singles and doubles travelling around the kit
    bars 43-50  climax: full kit groove, crashes, flams
    bars 51-54  space and tension: half time, floor tom pulse
    bars 55-62  final climb, motif A returns, roll
    bars 63-66  last fill and the final hit
"""

import random
import mido

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------
OUT_FILE = "solo.mid"
TPQ = 480                 # ticks per quarter note
BPM = 132.0               # 66 bars of 4/4 == 120 seconds
CHANNEL = 9               # zero based -> MIDI channel 10
SEED = 20240517

# --------------------------------------------------------------------------
# General MIDI percussion map
# --------------------------------------------------------------------------
KICK, KICK2 = 36, 35
SNARE, RIM = 38, 37
HATP, HAT, HATOP = 44, 42, 46
RIDE, BELL, RIDE2 = 51, 53, 59
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
FLOOR, FLOOR2 = 41, 43
TOM_L, TOM_LM, TOM_M, TOM_H = 45, 47, 48, 50

CYMBALS = frozenset((CRASH, CRASH2, SPLASH, CHINA, RIDE, RIDE2, BELL))
HATS = frozenset((HAT, HATOP, HATP))

rnd = random.Random(SEED)
events = []                       # [beat_time, note, velocity]

RIDE8 = [i * 0.5 for i in range(8)]
RIDE8_SKIP = [0.5 + i * 0.5 for i in range(7)]
RIDE16 = [i * 0.25 for i in range(16)]
RIDE16_SKIP = [0.5 + i * 0.25 for i in range(14)]

# micro timing feel: the "e" a shade early, the "&" laid back, the "a" neutral
_MICRO = (0.0, -0.007, 0.010, 0.004)


def _micro(t):
    frac = t - int(t)
    return _MICRO[int(round(frac * 4.0)) % 4]


def hit_at(t, note, vel, jitter=0.008):
    """Place a single stroke at absolute beat `t` with human timing/velocity."""
    tt = t + _micro(t) + rnd.uniform(-jitter, jitter)
    v = int(round(vel * rnd.uniform(0.95, 1.05)))
    events.append([tt, note, min(127, max(1, v))])


def hit(bar, pos, note, vel, jitter=0.008):
    """Place a stroke at `pos` beats into bar `bar` (bar is zero based)."""
    hit_at(bar * 4.0 + pos, note, vel, jitter)


# --------------------------------------------------------------------------
# small pattern helpers
# --------------------------------------------------------------------------
def hats(bar, base, note=HAT, positions=None, accent=1.16, soft=0.85, jitter=0.006):
    """Cymbal / hi-hat pattern; downbeats get the accent multiplier."""
    if positions is None:
        positions = RIDE8
    for p in positions:
        a = accent if (p - round(p)) == 0.0 else soft
        hit(bar, p, note, base * a, jitter)


def kicks(bar, pairs):
    for p, v in pairs:
        hit(bar, p, KICK, v, 0.006)


def snares(bar, pairs):
    for p, v in pairs:
        hit(bar, p, SNARE, v, 0.007)


def ghosts(bar, pairs):
    """Ghost notes - quiet snare taps that fill in the pulse."""
    for p, v in pairs:
        hit(bar, p, SNARE, v, 0.012)


def run_notes(bar, notes, start=0.0, step=0.25, v0=92.0, v1=104.0,
              accent_every=4, accent=1.16):
    n = len(notes)
    for i, nt in enumerate(notes):
        f = i / max(1, n - 1)
        v = v0 + (v1 - v0) * f
        if accent_every and i % accent_every == 0:
            v *= accent
        hit(bar, start + i * step, nt, v, 0.007)


# ==========================================================================
# the solo, section by section
# ==========================================================================
def sec_statement():
    """Bars 1-4: motif A, stated then answered."""
    for b in (0, 1):
        hats(b, 70)

    # --- bars 1-2: the motif, straight and plain
    kicks(0, [(0.0, 100), (2.5, 86)])
    snares(0, [(1.0, 101), (3.0, 105)])
    ghosts(0, [(1.75, 30), (3.75, 34)])

    kicks(1, [(0.0, 100), (1.75, 80), (2.5, 90)])
    snares(1, [(1.0, 101), (3.0, 105)])
    ghosts(1, [(2.25, 29), (3.5, 33)])

    # --- bars 3-4: answer phrase, opens up, ends in a pickup
    hats(2, 72)
    kicks(2, [(0.0, 100), (1.5, 78), (2.5, 88)])
    snares(2, [(1.0, 102), (3.0, 106)])
    ghosts(2, [(2.75, 32), (3.75, 36)])

    hats(3, 72, positions=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5])
    kicks(3, [(0.0, 102), (2.5, 88)])
    snares(3, [(1.0, 104)])
    hit(3, 3.5, SNARE, 92)
    hit(3, 3.75, TOM_H, 100)


def sec_variation():
    """Bars 5-8: motif A on the ride with heavier ghost note work."""
    hit(4, 0.0, CRASH, 112)
    hats(4, 78, note=RIDE, positions=RIDE8_SKIP)
    hats(5, 78, note=RIDE)
    hats(6, 78, note=RIDE)
    hats(7, 76, note=RIDE, positions=[0.0, 0.5, 1.0, 1.5, 2.0])

    kicks(4, [(0.0, 104), (2.5, 88)])
    snares(4, [(1.0, 102), (3.0, 106)])
    ghosts(4, [(1.75, 32), (3.75, 36)])

    kicks(5, [(0.0, 104), (1.75, 82), (2.5, 90), (3.5, 86)])
    snares(5, [(1.0, 102), (3.0, 106)])
    ghosts(5, [(0.75, 27), (1.75, 33), (2.25, 29), (3.75, 37)])

    kicks(6, [(0.0, 104), (1.75, 82), (3.25, 78)])
    snares(6, [(1.0, 102), (3.0, 106)])
    ghosts(6, [(0.5, 26), (1.5, 30), (2.75, 31), (3.5, 34)])

    # bar 8: pickup that hands the motif to the toms
    kicks(7, [(0.0, 104), (2.5, 90)])
    snares(7, [(1.0, 104)])
    for i, (n, v) in enumerate([(SNARE, 98), (TOM_H, 96), (TOM_M, 100),
                                (TOM_LM, 102), (TOM_L, 106), (FLOOR, 110)]):
        hit(7, 2.5 + i * 0.25, n, v)


def sec_tom_motif():
    """Bars 9-12: the same motif, backbeat played on the toms."""
    hit(8, 0.0, CRASH, 116)
    hats(8, 76, note=RIDE, positions=RIDE8_SKIP)
    hats(9, 76, note=RIDE)
    hats(10, 76, note=RIDE)
    hats(11, 76, note=RIDE, positions=[0.0, 0.5, 1.0, 1.5, 2.0])

    kicks(8, [(0.0, 106), (2.5, 90)])
    hit(8, 1.0, TOM_H, 100)
    hit(8, 3.0, TOM_M, 106)
    ghosts(8, [(1.75, 30), (3.75, 34)])

    kicks(9, [(0.0, 104), (1.75, 82), (2.5, 90)])
    hit(9, 1.0, TOM_M, 100)
    hit(9, 3.0, TOM_LM, 106)
    ghosts(9, [(2.25, 28), (3.75, 34)])

    kicks(10, [(0.0, 104), (2.5, 90)])
    snares(10, [(1.0, 104), (3.0, 108)])
    ghosts(10, [(0.75, 28), (2.75, 32), (3.5, 34)])

    kicks(11, [(0.0, 104), (2.5, 90)])
    snares(11, [(1.0, 104)])
    for i, (n, v) in enumerate([(SNARE, 100), (TOM_H, 98), (TOM_M, 102),
                                (TOM_LM, 104), (TOM_L, 108), (FLOOR, 112)]):
        hit(11, 2.5 + i * 0.25, n, v)


def sec_build():
    """Bars 13-16: density and dynamics climb."""
    dyn = (0.86, 0.95, 1.04, 1.12)
    for i, b in enumerate((12, 13, 14)):
        d = dyn[i]
        hats(b, 66 * d, note=RIDE, positions=RIDE16)
        kicks(b, [(0.0, 100 * d), (2.5, 88 * d)])
        snares(b, [(1.0, 102 * d), (3.0, 106 * d)])
        ghosts(b, [(0.75, 30), (1.75, 32), (2.25, 30), (3.75, 36)])
    kicks(13, [(1.5, 84), (3.5, 86)])
    kicks(14, [(0.75, 78), (1.5, 84), (2.75, 88)])

    # bar 16: hands fall down the toms into the fill
    hats(15, 68 * dyn[3], note=RIDE,
         positions=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75])
    kicks(15, [(0.0, 104), (2.5, 94)])
    snares(15, [(1.0, 108)])
    run_notes(15, [TOM_H, TOM_M, TOM_H, TOM_LM, TOM_L, FLOOR, FLOOR2, FLOOR],
              start=2.0, v0=104, v1=118, accent_every=0)


def sec_fill_one():
    """Bars 17-18: single stroke fill carrying into the downbeat."""
    # bar 17: 16th singles on the snare, crescendo with accents
    for i in range(16):
        v = 72 + i * 2.2
        if i % 4 == 0:
            v += 20
        elif i % 4 == 2:
            v += 6
        hit(16, i * 0.25, SNARE, v)
    kicks(16, [(0.0, 104), (2.0, 100)])

    # bar 18: hand to hand around the kit, sextuplets on the last beat
    seq = [TOM_H, SNARE, TOM_H, SNARE, TOM_M, SNARE,
           TOM_M, SNARE, TOM_LM, SNARE, TOM_LM, SNARE]
    for i, n in enumerate(seq):
        hit(17, i * 0.25, n, 94 + (i % 4) * 6)
    for i in range(6):
        hit(17, 3.0 + i / 6.0, SNARE, 100 + i * 5)
    kicks(17, [(0.0, 106), (2.5, 96)])
    hit(18, 0.0, CRASH, 120)


def sec_development():
    """Bars 19-26: the motif develops, hands visit every drum."""
    # --- bars 19-20: driving groove
    hit(18, 0.0, CRASH, 118)
    hats(18, 74, note=RIDE, positions=RIDE8_SKIP)
    kicks(18, [(0.0, 106), (2.5, 92)])
    snares(18, [(1.0, 104), (3.0, 108)])
    ghosts(18, [(0.75, 32), (1.75, 34), (3.75, 36)])

    hats(19, 74, note=RIDE)
    kicks(19, [(0.0, 106), (1.5, 84), (2.5, 92)])
    snares(19, [(1.0, 104), (3.0, 108)])
    ghosts(19, [(0.75, 32), (2.25, 30), (3.75, 36)])

    # --- bars 21-22: backbeat on the toms
    for b in (20, 21):
        hats(b, 74, note=RIDE)
        kicks(b, [(0.0, 106), (2.5, 92)])
    hit(20, 1.0, TOM_H, 104)
    hit(20, 3.0, TOM_M, 108)
    ghosts(20, [(1.75, 32), (2.75, 30), (3.75, 34)])
    kicks(20, [(1.75, 84)])

    hit(21, 1.0, TOM_M, 104)
    hit(21, 3.0, TOM_LM, 108)
    ghosts(21, [(0.75, 30), (2.25, 32), (3.75, 34)])
    kicks(21, [(1.5, 86), (3.5, 88)])

    # --- bars 23-24: syncopated interplay
    hats(22, 74, note=RIDE)
    kicks(22, [(0.0, 106), (0.75, 82), (2.5, 94)])
    snares(22, [(0.5, 88), (1.0, 104), (2.75, 94), (3.0, 108)])
    ghosts(22, [(1.5, 30), (2.25, 32), (3.5, 34)])

    hats(23, 74, note=RIDE)
    kicks(23, [(0.0, 106), (1.75, 84), (2.5, 94)])
    snares(23, [(1.0, 104), (2.25, 90), (3.0, 108)])
    ghosts(23, [(0.5, 28), (1.5, 32), (3.75, 36)])

    # --- bar 25: full, sixteenth ride
    hats(24, 74, note=RIDE, positions=RIDE16)
    kicks(24, [(0.0, 108), (2.5, 96)])
    snares(24, [(1.0, 108), (3.0, 112)])
    ghosts(24, [(0.75, 34), (1.75, 36), (2.75, 34)])

    # --- bar 26: long fill that suddenly drops away
    kicks(25, [(0.0, 106)])
    seq = [SNARE, TOM_H, TOM_M, TOM_LM, TOM_L, FLOOR, FLOOR2, FLOOR,
           TOM_L, TOM_LM, TOM_M, TOM_H, SNARE, SNARE, TOM_H, SNARE]
    for i, n in enumerate(seq):
        hit(25, i * 0.25, n, 104 + (i % 4) * 6)


def sec_quiet():
    """Bars 27-30: sudden drop.  Rim clicks, pedal hat, whispers."""
    for b in (26, 27):
        hit(b, 0.0, HATP, 58)
        hit(b, 2.0, HATP, 54)
        hit(b, 0.0, KICK, 68)
        hit(b, 2.5, KICK, 56)
        hit(b, 1.0, RIM, 72)
        hit(b, 3.0, RIM, 76)
        ghosts(b, [(0.75, 24), (1.75, 28), (2.75, 26), (3.75, 30)])

    # bar 29: the motif, whispered
    hats(28, 44, note=RIDE, positions=[0.0, 1.0, 2.0, 3.0])
    hit(28, 0.0, KICK, 72)
    hit(28, 2.5, KICK, 60)
    hit(28, 1.0, SNARE, 80)
    hit(28, 3.0, SNARE, 84)
    ghosts(28, [(0.75, 26), (1.5, 28), (2.25, 26),
                (2.75, 30), (3.5, 32), (3.75, 34)])

    # bar 30: hands start moving, the swell is born
    for i in range(16):
        v = 38 + i * 1.5
        hit(29, i * 0.25, SNARE if i % 2 == 0 else TOM_H, v)
    hit(29, 0.0, KICK, 74)
    hit(29, 2.0, KICK, 68)


def sec_roll():
    """Bars 31-34: a long roll that swells and resolves on a crash."""
    n = 60                                  # 16ths through bar 33 beat 3
    for i in range(n):
        f = i / (n - 1.0)
        v = 52 + 62 * (f ** 1.4)
        if i % 4 == 0:
            v += 7
        if i % 8 == 6:
            v -= 5
        hit_at(30 * 4 + i * 0.25, SNARE, v, 0.006)

    kicks(30, [(0.0, 92)])
    kicks(31, [(0.0, 96), (2.0, 90)])
    kicks(32, [(0.0, 100), (2.0, 94)])
    kicks(33, [(0.0, 104), (2.0, 98)])

    for i in range(8):                      # double stroke burst into the crash
        hit(33, 3.0 + i * 0.125, SNARE, 104 + i * 3)

    hit(34, 0.0, CRASH, 124)
    hit(34, 0.0, KICK, 112)


def sec_runs():
    """Bars 35-42: singles and doubles travelling around the kit."""
    # --- bar 35: crash, then singles off the snare
    hit(34, 0.0, CRASH, 122)
    hit(34, 0.0, KICK, 112)
    seq = [SNARE, SNARE, TOM_H, SNARE, TOM_H, TOM_M, SNARE, TOM_M,
           TOM_LM, SNARE, TOM_LM, TOM_L, SNARE, FLOOR]
    for i, nt in enumerate(seq):
        hit(34, 0.5 + i * 0.25, nt, 94 + (i % 4) * 6)

    # --- bar 36: doubles all the way down
    seq = [SNARE, SNARE, TOM_H, TOM_H, TOM_M, TOM_M, TOM_LM, TOM_LM,
           TOM_L, TOM_L, FLOOR, FLOOR, FLOOR2, FLOOR2, FLOOR, TOM_L]
    for i, nt in enumerate(seq):
        v = 96 + (i % 4) * 6 + (8 if i % 8 == 0 else 0)
        hit(35, i * 0.25, nt, v)
    kicks(35, [(0.0, 106), (2.0, 100)])

    # --- bar 37: singles up and back down
    seq = [TOM_L, TOM_LM, TOM_M, TOM_H, SNARE, TOM_H, TOM_M, TOM_LM,
           TOM_L, FLOOR, FLOOR2, FLOOR, TOM_L, TOM_LM, TOM_M, SNARE]
    for i, nt in enumerate(seq):
        hit(36, i * 0.25, nt, 98 + (i % 3) * 5)
    kicks(36, [(0.0, 104), (1.5, 96), (2.5, 104)])

    # --- bar 38: hands off the beat, feet doubling
    for i in range(8):
        hit(37, i * 0.5 + 0.25, TOM_H if i % 2 == 0 else SNARE, 96 + (i % 3) * 6)
    kicks(37, [(0.0, 100), (0.25, 88), (1.0, 100), (1.25, 88),
               (2.0, 100), (2.25, 88), (3.0, 100), (3.25, 88)])

    # --- bar 39: sextuplets falling down the toms
    seq = [SNARE, TOM_H, TOM_M, TOM_LM, TOM_L, FLOOR] * 4
    for i, nt in enumerate(seq):
        hit(38, i / 6.0, nt, 92 + (i % 6) * 4)
    kicks(38, [(0.0, 106), (2.0, 100)])

    # --- bar 40: accents displaced, ghosts in between
    hats(39, 70, note=RIDE)
    kicks(39, [(0.0, 106), (1.5, 92), (2.5, 98)])
    snares(39, [(0.75, 104), (1.75, 96), (3.0, 110)])
    ghosts(39, [(1.25, 30), (2.75, 32), (3.5, 34)])
    hit(39, 2.0, TOM_H, 100)

    # --- bar 41: rising tom figure, tension
    seq = [TOM_L, TOM_L, TOM_LM, TOM_LM, TOM_M, TOM_M, TOM_H, TOM_H,
           SNARE, SNARE, TOM_H, TOM_H, TOM_M, TOM_M, TOM_LM, TOM_LM]
    for i, nt in enumerate(seq):
        hit(40, i * 0.25, nt, 94 + i * 1.5)
    kicks(40, [(0.0, 108), (2.0, 104)])

    # --- bar 42: fill into the peak
    seq = [SNARE, TOM_H, SNARE, TOM_M, SNARE, TOM_LM, SNARE, TOM_L,
           SNARE, FLOOR, TOM_H, TOM_M, TOM_L, FLOOR, FLOOR2, FLOOR]
    for i, nt in enumerate(seq):
        hit(41, i * 0.25, nt, 100 + i * 1.5)
    kicks(41, [(0.0, 108), (2.0, 106)])


def sec_climax():
    """Bars 43-50: full kit groove at the peak."""
    hit(42, 0.0, CRASH, 126)
    hats(42, 80, note=RIDE, positions=RIDE8_SKIP)
    kicks(42, [(0.0, 112), (2.5, 98)])
    snares(42, [(1.0, 110), (3.0, 114)])
    ghosts(42, [(0.75, 34), (1.75, 36), (3.75, 38)])

    hats(43, 80, note=RIDE)
    kicks(43, [(0.0, 112), (1.5, 92), (2.5, 98)])
    snares(43, [(1.0, 110), (3.0, 114)])
    ghosts(43, [(0.75, 34), (2.25, 32), (3.75, 38)])

    hats(44, 76, note=RIDE, positions=RIDE16_SKIP)
    kicks(44, [(0.0, 112), (2.5, 98)])
    snares(44, [(1.0, 110), (3.0, 116)])
    ghosts(44, [(0.75, 34), (1.75, 36), (2.75, 34)])
    hit(44, 2.0, TOM_H, 106)
    hit(44, 3.5, TOM_M, 104)

    hats(45, 80, note=RIDE)
    kicks(45, [(0.0, 112), (1.75, 90), (2.5, 98)])
    snares(45, [(1.0, 110), (3.0, 116)])
    hit(45, 2.94, SNARE, 46)                     # flam grace note
    ghosts(45, [(0.75, 34), (3.75, 38)])

    hat(46) if False else None                   # (kept explicit below)
    hit(46, 0.0, CRASH, 124)
    hats(46, 78, note=RIDE, positions=RIDE8_SKIP)
    kicks(46, [(0.0, 112), (2.5, 98)])
    hit(46, 1.0, TOM_H, 108)
    hit(46, 3.0, TOM_M, 112)
    ghosts(46, [(1.75, 32), (2.75, 32), (3.75, 36)])

    hats(47, 78, note=RIDE)
    kicks(47, [(0.0, 112), (0.75, 90), (2.5, 100)])
    snares(47, [(0.5, 96), (1.0, 110), (2.75, 100), (3.0, 114)])
    ghosts(47, [(1.5, 32), (2.25, 34), (3.5, 36)])

    hats(48, 76, note=RIDE, positions=RIDE16_SKIP)
    kicks(48, [(0.0, 112), (2.5, 100)])
    snares(48, [(1.0, 110), (3.0, 116)])
    ghosts(48, [(0.75, 34), (1.75, 36), (2.75, 34), (3.75, 36)])

    seq = [SNARE, TOM_H, TOM_M, TOM_LM, TOM_L, FLOOR, FLOOR2, FLOOR,
           TOM_L, TOM_LM, TOM_M, TOM_H, SNARE, TOM_H, TOM_M, TOM_LM]
    for i, nt in enumerate(seq):
        hit(49, i * 0.25, nt, 106 + i * 1.5)
    kicks(49, [(0.0, 108), (2.0, 104)])


def sec_break():
    """Bars 51-54: space and tension."""
    for b in (50, 51):
        hit(b, 0.0, KICK, 86)
        hit(b, 2.0, SNARE, 92)
        hit(b, 2.0, HATP, 62)
        hit(b, 0.5, RIDE, 58)
        hit(b, 1.5, RIDE, 54)
        hit(b, 3.0, RIDE, 56)
        hit(b, 3.5, FLOOR, 74)
        ghosts(b, [(1.75, 28), (3.75, 30)])

    for i, b in enumerate((52, 53)):
        d = 0.92 + i * 0.12
        for j in range(8):
            v = (80 if j % 2 == 0 else 64) * d
            hit(b, j * 0.5, FLOOR if j < 5 else FLOOR2, v)
        kicks(b, [(0.0, 94 * d), (2.0, 86 * d)])
        snares(b, [(1.5, 96 * d), (3.5, 100 * d)])
        ghosts(b, [(0.75, 26 * d), (2.75, 28 * d)])


def sec_final_build():
    """Bars 55-62: the last climb."""
    # --- bars 55-56: motif A returns, big
    hit(54, 0.0, CRASH, 122)
    hats(54, 80, note=RIDE, positions=RIDE8_SKIP)
    hats(55, 80, note=RIDE)
    for b in (54, 55):
        kicks(b, [(0.0, 110), (2.5, 98)])
        snares(b, [(1.0, 110), (3.0, 114)])
        ghosts(b, [(1.75, 34), (3.75, 38)])
    kicks(55, [(1.75, 90)])

    # --- bar 57: sixteenth ride, syncopated kick
    hats(56, 78, note=RIDE, positions=RIDE16_SKIP)
    kicks(56, [(0.0, 110), (1.5, 94), (2.5, 100)])
    snares(56, [(1.0, 110), (3.0, 114)])
    ghosts(56, [(0.75, 34), (1.75, 36), (2.75, 34), (3.75, 36)])

    # --- bar 58: backbeat on toms
    hats(57, 78, note=RIDE)
    kicks(57, [(0.0, 110), (2.5, 100)])
    hit(57, 1.0, TOM_H, 108)
    hit(57, 3.0, TOM_M, 112)
    ghosts(57, [(1.75, 34), (2.75, 32), (3.75, 36)])

    # --- bar 59: sixteenth tom pattern
    seq = [TOM_L, TOM_LM, TOM_M, TOM_H] * 4
    for i, nt in enumerate(seq):
        v = 92 + (12 if i % 4 == 0 else 0)
        hit(58, i * 0.25, nt, v)
    kicks(58, [(0.0, 108), (2.0, 104)])

    # --- bar 60: hands ascend, crescendo
    seq = [TOM_L, TOM_LM, TOM_M, TOM_H, SNARE, TOM_H, TOM_M, TOM_LM] * 2
    for i, nt in enumerate(seq):
        hit(59, i * 0.25, nt, 96 + i * 1.6)
    kicks(59, [(0.0, 110), (2.0, 106)])

    # --- bar 61: snare roll, still climbing
    for i in range(16):
        v = 76 + i * 2.0
        if i % 4 == 0:
            v += 12
        elif i % 4 == 2:
            v += 5
        hit(60, i * 0.25, SNARE, v)
    kicks(60, [(0.0, 106), (2.0, 102)])

    # --- bar 62: the motif, one last time and loud
    hit(61, 0.0, CRASH, 124)
    hats(61, 84, note=RIDE, positions=RIDE8_SKIP)
    kicks(61, [(0.0, 112), (1.75, 92), (2.5, 100)])
    snares(61, [(1.0, 112), (3.0, 116)])
    ghosts(61, [(1.75, 36), (3.75, 40)])


def sec_finale():
    """Bars 63-66: the last fill, and the final hit."""
    # --- bar 63: toms fall
    seq = [SNARE, TOM_H, TOM_M, TOM_LM, TOM_L, FLOOR, FLOOR2, FLOOR,
           TOM_L, TOM_LM, TOM_M, TOM_H, SNARE, SNARE, TOM_H, SNARE]
    for i, nt in enumerate(seq):
        hit(62, i * 0.25, nt, 106 + i * 1.4)
    kicks(62, [(0.0, 110), (2.0, 106)])

    # --- bar 64: around the kit again
    seq = [TOM_L, TOM_LM, SNARE, TOM_M, TOM_H, SNARE, TOM_H, TOM_M,
           TOM_LM, TOM_L, SNARE, FLOOR, FLOOR2, FLOOR, TOM_L, FLOOR2]
    for i, nt in enumerate(seq):
        hit(63, i * 0.25, nt, 106 + (i % 4) * 5)
    kicks(63, [(0.0, 110), (1.0, 104), (2.0, 108), (3.0, 104)])

    # --- bar 65: thirty-second roll, final crescendo
    n = 29                                   # 0.0 .. 3.5
    for i in range(n):
        f = i / (n - 1.0)
        v = 90 + 34 * f
        if i % 8 == 0:
            v += 5
        hit_at(64 * 4 + i * 0.125, SNARE, v, 0.005)
    hit(64, 3.75, SNARE, 127)
    hit(64, 3.75, KICK, 122)

    # --- final hit
    hit(65, 0.0, CRASH, 127)
    hit(65, 0.0, KICK, 126)
    hit(65, 0.0, SNARE, 124)


# ==========================================================================
# rendering
# ==========================================================================
def _note_len(note):
    if note in CYMBALS:
        return 1.2
    if note in HATS:
        return 0.10
    return 0.20


def shape_events():
    """Sort, deduplicate and keep the part playable by one drummer."""
    global events
    events.sort(key=lambda e: (e[0], e[1], e[2]))

    kept = []
    for t, n, v in events:
        ok = True
        recent = kept[-16:]
        for k in reversed(recent):
            if t - k[0] > 0.04:
                break
            if k[1] == n and t - k[0] < 0.012:
                ok = False                    # same drum struck twice at once
                break
        if ok:
            near = 0
            for k in recent:
                if t - k[0] <= 0.035:
                    near += 1
            if near >= 4:                     # two hands + two feet, no more
                ok = False
        if ok:
            kept.append([t, n, v])
    events = kept


def write_midi():
    # note lengths, trimmed so a drum is never re-struck while still ringing
    by_note = {}
    for i, (t, n, v) in enumerate(events):
        by_note.setdefault(n, []).append(i)
    ends = {}
    for n, idxs in by_note.items():
        length = _note_len(n)
        for k, i in enumerate(idxs):
            t = events[i][0]
            end = t + length
            if k + 1 < len(idxs):
                nxt = events[idxs[k + 1]][0]
                if end > nxt - 0.005:
                    end = nxt - 0.005
            if end < t + 0.02:
                end = t + 0.02
            ends[i] = end

    msgs = []
    for i, (t, n, v) in enumerate(events):
        on = int(round(t * TPQ))
        off = int(round(ends[i] * TPQ))
        if off <= on:
            off = on + 10
        msgs.append((on, 1, n, v))
        msgs.append((off, 0, n, 0))
    msgs.sort(key=lambda m: (m[0], m[1]))

    mid = mido.MidiFile(ticks_per_beat=TPQ)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("track_name", name="Drum Solo", time=0))
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4,
                                  denominator=4, time=0))
    track.append(mido.Message("program_change", channel=CHANNEL,
                              program=0, time=0))

    last = 0
    for tick, kind, note, vel in msgs:
        delta = tick - last
        if delta < 0:
            delta = 0
        last = tick
        if kind:
            track.append(mido.Message("note_on", channel=CHANNEL,
                                      note=note, velocity=vel, time=delta))
        else:
            track.append(mido.Message("note_off", channel=CHANNEL,
                                      note=note, velocity=0, time=delta))

    mid.save(OUT_FILE)
    return len(events)


def main():
    sec_statement()
    sec_variation()
    sec_tom_motif()
    sec_build()
    sec_fill_one()
    sec_development()
    sec_quiet()
    sec_roll()
    sec_runs()
    sec_climax()
    sec_break()
    sec_final_build()
    sec_finale()

    shape_events()
    count = write_midi()
    print("wrote %s: %d strokes, %.1f s" % (OUT_FILE, count, 264 * 60.0 / BPM))


if __name__ == "__main__":
    main()
