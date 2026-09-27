#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid -- a two minute solo for General MIDI percussion
(channel 10, notes 35-81).  Everything comes from a fixed seed, so the
file is byte-for-byte identical on every run.

The solo is built the way a drummer builds one: a motif is stated, moved
around the kit, displaced, broken apart and brought home again, with the
density and the dynamics shaping tension and release inside each phrase.
"""

import math
import random

import mido

# ---------------------------------------------------------------------------
#  time base
# ---------------------------------------------------------------------------
PPQ = 960                 # ticks per quarter note
T16 = PPQ // 4            # ticks per sixteenth
BEAT = PPQ
BAR = 4 * PPQ
P16_PER_BAR = 16.0

rng = random.Random(0x5EEDBEEF)

# ---------------------------------------------------------------------------
#  General MIDI percussion (35 .. 81)
# ---------------------------------------------------------------------------
BD    = 36    # bass drum 1
BD_AC = 35    # acoustic bass drum
SS    = 37    # side stick
SD    = 38    # acoustic snare
SD2   = 40    # electric snare
F_LO  = 41    # low floor tom
HH    = 42    # closed hi-hat
F_HI  = 43    # high floor tom
HHP   = 44    # pedal hi-hat
T_LO  = 45    # low tom
HHO   = 46    # open hi-hat
T_LM  = 47    # low-mid tom
T_HM  = 48    # hi-mid tom
CR    = 49    # crash cymbal 1
T_HI  = 50    # high tom
RIDE  = 51    # ride cymbal 1
CHINA = 52    # chinese cymbal
BELL  = 53    # ride bell
TAMB  = 54    # tambourine
SPL   = 55    # splash cymbal
COW   = 56    # cowbell
CR2   = 57    # crash cymbal 2
RIDE2 = 59    # ride cymbal 2
BON_H = 60    # hi bongo
BON_L = 61    # low bongo
CON_M = 62    # mute hi conga
CON_H = 63    # open hi conga
CON_L = 64    # low conga
TIM_H = 65    # high timbale
TIM_L = 66    # low timbale
CLAVE = 75    # claves
WB_H  = 76    # hi wood block
WB_L  = 77    # low wood block
TRI   = 81    # open triangle

FEET = frozenset((BD, BD_AC, HHP))

# ---------------------------------------------------------------------------
#  default ring times (ticks)
# ---------------------------------------------------------------------------
DUR = {
    BD: 220, BD_AC: 240, SS: 90, SD: 130, SD2: 130,
    F_LO: 420, HH: 95, F_HI: 340, HHP: 140,
    T_LO: 280, HHO: 640, T_LM: 260, T_HM: 250,
    CR: 1920, T_HI: 230, RIDE: 430, CHINA: 1440,
    BELL: 380, TAMB: 420, SPL: 900, COW: 280,
    CR2: 1760, RIDE2: 430,
    BON_H: 180, BON_L: 200, CON_M: 200, CON_H: 220, CON_L: 240,
    TIM_H: 260, TIM_L: 280, CLAVE: 120, WB_H: 110, WB_L: 130, TRI: 900,
}

EVENTS = []               # (tick, note, velocity, duration)


def default_dur(note):
    return DUR.get(note, 180)


# ---------------------------------------------------------------------------
#  performance / humanising layer
# ---------------------------------------------------------------------------
def human(p16, vel, kind=None):
    """Micro-timing for one stroke, in ticks.

    Accents sit a shade forward, ghost notes a shade behind, and on top of
    that the whole pulse breathes: it leans forward through the first half
    of every eight-bar phrase and settles back through the second half.
    """
    b = p16 / P16_PER_BAR
    o = rng.gauss(0.0, 5.0)
    if kind is None:
        kind = 'ghost' if vel <= 45.0 else ('accent' if vel >= 95.0 else 'mid')
    if kind == 'ghost':
        o += rng.uniform(3.0, 16.0)
    elif kind == 'accent':
        o -= rng.uniform(1.0, 7.0)
    elif kind == 'cymbal':
        o -= rng.uniform(0.0, 5.0)
    o += 12.0 * math.sin(2.0 * math.pi * (b % 8.0) / 8.0)
    return o


def hit_at(p16, note, vel, dur=None, kind=None, tight=False):
    """One stroke at absolute position `p16` (sixteenth notes from bar 0)."""
    tick = p16 * T16 + (0.0 if tight else human(p16, vel, kind))
    v = int(round(vel + rng.gauss(0.0, 2.0)))
    EVENTS.append((int(round(tick)), note, max(1, min(127, v)),
                   int(dur if dur is not None else default_dur(note))))


def hit(bar, pos, note, vel, dur=None, kind=None, tight=False):
    hit_at(bar * P16_PER_BAR + pos, note, vel, dur, kind, tight)


def cyc(seq, n):
    """`seq` repeated (cycled) until it has n items."""
    return [seq[i % len(seq)] for i in range(n)]


# ---------------------------------------------------------------------------
#  motif 1 -- the figure the whole solo is built from
# ---------------------------------------------------------------------------
M1 = [(0.0, 'bd', 106.0), (2.0, 'gh', 26.0),
      (4.0, 'sd', 100.0), (6.0, 'gh', 27.0),
      (8.0, 'bd', 96.0), (10.0, 'gh', 30.0),
      (12.0, 'sd', 104.0), (14.0, 'gh', 27.0)]


def m1(bar, dyn=1.0, ghost=1.0, sd1=None, sd2=None, bd=None, hats=False):
    """State motif 1 in `bar`; `dyn` scales it, `sd1`/`sd2` re-voice the
    backbeats (toms, cross-stick ...), `hats` adds eighth-note hi-hat."""
    for pos, role, vel in M1:
        if role == 'bd':
            hit(bar, pos, bd or BD, vel * dyn)
        elif role == 'sd':
            hit(bar, pos, (sd1 if pos < 8.0 else sd2) or SD, vel * dyn)
        else:
            hit(bar, pos, SD, vel * ghost * (0.55 + 0.45 * dyn))
    if hats:
        for i in range(8):
            hit(bar, i * 2.0, HH, (48.0 if i % 2 == 0 else 36.0) * dyn)


# ---------------------------------------------------------------------------
#  motif 2 -- the ride-driven answer
# ---------------------------------------------------------------------------
def m2(bar, dyn=1.0, cym=RIDE, ghost=True, sd1=SD, sd2=SD):
    for i in range(8):
        hit(bar, i * 2.0, cym, (66.0 if i % 2 == 0 else 55.0) * dyn, dur=340)
    hit(bar, 0.0, BD, 106.0 * dyn)
    hit(bar, 7.0, BD, 86.0 * dyn)
    hit(bar, 14.0, BD, 92.0 * dyn)
    hit(bar, 4.0, sd1, 102.0 * dyn)
    hit(bar, 12.0, sd2, 104.0 * dyn)
    if ghost:
        hit(bar, 6.0, SD, 27.0 * dyn)
        hit(bar, 10.0, SD, 30.0 * dyn)
        hit(bar, 13.0, SD, 25.0 * dyn)


# ===========================================================================
#  A -- bars 0-3 : the motif, stated
# ===========================================================================
hit(0, 0.0, CR, 70, kind='cymbal')
m1(0, dyn=0.78, ghost=0.85)
m1(1, dyn=0.84, ghost=1.00)
m1(2, dyn=0.90, ghost=1.00, hats=True)
# bar 3 -- the last beat is handed to the toms, a pickup into the answer
hit(3, 0.0, BD, 96);   hit(3, 2.0, SD, 24);   hit(3, 4.0, SD, 98)
hit(3, 6.0, SD, 26);   hit(3, 8.0, BD, 94);   hit(3, 10.0, SD, 28)
hit(3, 12.0, SD, 102)
hit(3, 13.0, T_HM, 74)
hit(3, 14.0, T_LO, 82)
hit(3, 15.0, F_HI, 90)

# ===========================================================================
#  B -- bars 4-11 : the motif developed -- moved, displaced, dissolved
# ===========================================================================
hit(4, 0.0, CR, 90, kind='cymbal')
m1(4, dyn=0.94, sd1=T_HI, sd2=T_LM, hats=True)      # same figure, new voices
m1(5, dyn=1.00)                                      # plain again

# bar 6 -- pushed back an eighth: the downbeat disappears
hit(6, 0.0, SD, 26);   hit(6, 2.0, BD, 100)
hit(6, 4.0, SD, 24);   hit(6, 6.0, SD, 98)
hit(6, 8.0, SD, 26);   hit(6, 10.0, BD, 96)
hit(6, 12.0, SD, 28);  hit(6, 14.0, SD, 102)

m1(7, dyn=1.05, hats=True)                           # and it lands
hit(7, 15.0, BD_AC, 92)

m1(8, dyn=0.64, sd1=SS, sd2=SS, ghost=0.70)          # cross-stick release
m1(9, dyn=0.70, sd1=SS, sd2=SS, ghost=0.80, hats=True)

hit(10, 0.0, CR, 104, kind='cymbal')                 # rebuild
m1(10, dyn=1.08, sd1=T_HM)
# bar 11 -- fill out of the section
hit(11, 0.0, BD, 112);      hit(11, 2.0, SD, 26);   hit(11, 4.0, SD, 108)
hit(11, 6.0, SD, 28);       hit(11, 8.0, BD, 106);  hit(11, 10.0, SD, 30)
hit(11, 12.0, T_HI, 104);   hit(11, 13.0, T_HM, 94)
hit(11, 14.0, T_LM, 100);   hit(11, 15.0, T_LO, 106)

# ===========================================================================
#  C -- bars 12-19 : second motif, ride-driven and syncopated
# ===========================================================================
hit(12, 0.0, CR, 96, kind='cymbal')
m2(12)
m2(13)
m2(14, dyn=1.06)
# bar 15 -- motif, then a two beat answer
for i in range(4):
    hit(15, i * 2.0, RIDE, (68.0 if i % 2 == 0 else 56.0), dur=300)
hit(15, 0.0, BD, 108);   hit(15, 2.0, SD, 25)
hit(15, 4.0, SD, 102);   hit(15, 6.0, SD, 27)
hit(15, 8.0, SD, 94);    hit(15, 9.0, SD, 40)
hit(15, 10.0, SD, 98);   hit(15, 11.0, SD, 42)
hit(15, 12.0, T_HI, 100); hit(15, 13.0, T_HM, 92)
hit(15, 14.0, T_LM, 98);  hit(15, 15.0, T_LO, 104)

# bars 16-17 -- the same shape with the hands down on the toms
for b in (16, 17):
    for i in range(8):
        hit(b, i * 2.0, T_HM if i % 2 == 0 else T_LO,
            80.0 if i % 2 == 0 else 58.0)
    hit(b, 0.0, BD, 104)
    hit(b, 4.0, SD, 100)
    hit(b, 12.0, SD, 102)
    hit(b, 6.0, SD, 26)
    hit(b, 10.0, SD, 29)
    hit(b, 14.0, SD, 24)

hit(18, 0.0, CR2, 100, kind='cymbal')
m2(18, dyn=1.08)
# bar 19 -- decrescendo out of the section
for i in range(4):
    hit(19, i * 2.0, RIDE, (68.0 if i % 2 == 0 else 56.0), dur=300)
hit(19, 0.0, BD, 104);   hit(19, 2.0, SD, 26)
hit(19, 4.0, SD, 100);   hit(19, 6.0, SD, 28)
hit(19, 8.0, SD, 92);    hit(19, 10.0, T_HM, 74)
hit(19, 12.0, T_LM, 66); hit(19, 14.0, F_HI, 58)
hit(19, 15.0, F_LO, 52)

# ===========================================================================
#  D -- bars 20-23 : breakdown -- space, low voices, gathering tension
# ===========================================================================
hit(20, 0.0, BD, 104)
hit(20, 0.0, CR2, 92, kind='cymbal')
hit(20, 8.0, SD, 94)
hit(20, 12.0, F_LO, 84, dur=760)
hit(20, 14.0, F_LO, 36)

hit(21, 0.0, BD, 92)
hit(21, 0.0, F_LO, 64)
hit(21, 4.0, F_HI, 68)
hit(21, 8.0, T_LM, 72)
hit(21, 12.0, T_HM, 76)
hit(21, 15.0, WB_L, 58)

for i in range(8):
    hit(22, i * 2.0, F_LO if i % 2 == 0 else F_HI, 52.0 + i * 4.0)
hit(22, 0.0, BD, 92)
hit(22, 8.0, BD, 96)

for i in range(16):
    hit(23, i, SD, 40.0 + i * 3.2)
hit(23, 0.0, BD, 98)
hit(23, 8.0, BD, 92)

# ===========================================================================
#  E -- bars 24-33 : rolls, singles, build
# ===========================================================================
hit(24, 0.0, CR, 112, kind='cymbal')
hit(24, 0.0, BD, 114)
hit(24, 0.0, SD, 104)
hit(24, 6.0, F_LO, 86)
hit(24, 10.0, F_LO, 40)
hit(24, 12.0, BD, 96)
hit(24, 14.0, SD, 28)

# bars 25-26 -- single strokes travelling down the kit and back up
seqA = cyc([T_HI, T_HM, T_LM, T_LO], 16)
for i in range(16):
    hit(25, i, seqA[i], 96.0 if i % 4 == 0 else 74.0)
hit(25, 0.0, BD, 100)
hit(25, 8.0, BD, 94)

seqB = cyc([F_LO, F_HI, T_LO, T_LM, T_HM, T_HI], 16)
for i in range(16):
    hit(26, i, seqB[i], 100.0 if i % 4 == 0 else 78.0)
hit(26, 0.0, BD, 102)
hit(26, 8.0, BD, 100)

# bars 27-28 -- the roll swells
for i in range(16):
    hit(27, i, SD, 46.0 + i * 1.5)
hit(27, 0.0, BD, 96)
hit(27, 8.0, BD, 90)
for i in range(8):
    hit(28, i, SD, 68.0 + i * 2.0)
for i in range(16):
    hit_at(28 * P16_PER_BAR + 8.0 + i * 0.5, SD, 84.0 + i * 1.6)
hit(28, 0.0, BD, 100)

# bars 29-30 -- release: bell chorus (half the notes, full weight)
hit(29, 0.0, CR, 114, kind='cymbal')
for b in (29, 30):
    for i in range(8):
        hit(b, i * 2.0, BELL, (74.0 if i % 2 == 0 else 60.0), dur=380)
    hit(b, 0.0, BD, 106)
    hit(b, 4.0, SD, 104)
    hit(b, 12.0, SD, 106)
    hit(b, 6.0, SD, 27)
    hit(b, 10.0, SD, 30)
    hit(b, 14.0, BD, 92)
hit(30, 15.0, COW, 70)

# bars 31-32 -- double strokes climbing and swelling
ladA = cyc([SD, SD, T_HI, T_HI, T_HM, T_HM, T_LM, T_LM,
            T_LO, T_LO, F_HI, F_HI, F_LO, F_LO, SD, SD], 32)
for i in range(32):
    hit_at(31 * P16_PER_BAR + i * 0.5, ladA[i], 100.0 if i % 8 == 0 else 74.0)
hit(31, 0.0, BD, 104)
hit(31, 8.0, BD, 100)

ladB = cyc([F_LO, F_LO, F_HI, F_HI, T_LO, T_LO, T_LM, T_LM,
            T_HM, T_HM, T_HI, T_HI, SD, SD, T_HI, T_HI], 32)
for i in range(32):
    v = (100.0 + i * 0.4) if i % 8 == 0 else (76.0 + i * 0.3)
    hit_at(32 * P16_PER_BAR + i * 0.5, ladB[i], v)

# bar 33 -- fill into the climax
fill33 = cyc([SD, T_HI, SD, T_HM, SD, T_LM, SD, T_LO], 16)
for i in range(16):
    hit(33, i, fill33[i], 108.0 if i % 4 == 0 else 82.0)
hit(33, 0.0, BD, 106)
hit(33, 8.0, BD, 104)

# ===========================================================================
#  F -- bars 34-43 : climax
# ===========================================================================
hit(34, 0.0, CR, 118, kind='cymbal')
hit(34, 0.0, BD, 116)
hit(34, 0.0, SD, 106)
for b in (34, 35):
    seq = cyc([SD, T_HM, SD, T_HI, SD, T_LM, SD, T_LO,
               SD, F_HI, SD, T_LM, SD, T_HI, SD, T_HM], 16)
    for i in range(16):
        if b == 34 and i == 0:
            continue
        hit(b, i, seq[i], 106.0 if i % 4 == 0 else 78.0)
    hit(b, 8.0, BD, 106)

# bars 36-37 -- accents riding on a bed of doubles
pat36 = cyc([SD, SD, T_HI, T_HI, SD, SD, T_LM, T_LM], 32)
for i in range(32):
    hit_at(36 * P16_PER_BAR + i * 0.5, pat36[i], 108.0 if i % 8 == 0 else 76.0)
hit(36, 0.0, BD, 110)
hit(36, 8.0, BD, 104)

hit(37, 0.0, CR2, 112, kind='cymbal')
pat37 = cyc([T_HM, T_HM, SD, SD, T_LO, T_LO, SD, SD], 32)
for i in range(32):
    hit_at(37 * P16_PER_BAR + i * 0.5, pat37[i], 108.0 if i % 8 == 0 else 78.0)
hit(37, 0.0, BD, 112)

# bars 38-39 -- open and driving, then the hands walk onto the percussion
for b in (38, 39):
    for i in range(8):
        hit(b, i * 2.0, HH, (78.0 if i % 2 == 0 else 62.0), dur=110)
    hit(b, 0.0, BD, 114)
    hit(b, 4.0, SD, 112)
    hit(b, 8.0, BD, 108)
    hit(b, 12.0, SD, 112)
hit(38, 0.0, CR, 116, kind='cymbal')
hit(38, 14.0, HHO, 86, dur=520)

timb = cyc([TIM_H, TIM_L, BON_H, BON_L, CON_H, CON_M, CON_L, CON_M], 8)
for i in range(8):
    hit(39, 8.0 + i, timb[i], 96.0 if i % 2 == 0 else 78.0)

# bars 40-41 -- the floor drops out
hit(40, 0.0, CR, 120, kind='cymbal')
hit(40, 0.0, BD, 118)
hit(40, 6.0, SD, 108)
hit(40, 10.0, F_LO, 96, dur=620)
hit(40, 12.0, SD, 34)
hit(41, 0.0, BD, 116)
hit(41, 0.0, F_LO, 100, dur=580)
hit(41, 4.0, F_HI, 104)
hit(41, 8.0, T_LM, 108)
hit(41, 12.0, T_HM, 112)
hit(41, 14.0, CR2, 106, kind='cymbal')

# bars 42-43 -- charge back up into the return
for i in range(16):
    hit(42, i, cyc([SD, SD, T_HI, T_HM], 16)[i],
        110.0 if i % 4 == 0 else 82.0)
hit(42, 0.0, BD, 112)
hit(42, 8.0, BD, 108)

for i in range(16):
    hit(43, i, cyc([SD, T_LM, SD, T_LO, SD, F_HI, SD, F_LO], 16)[i],
        114.0 if i % 4 == 0 else 88.0)
hit(43, 0.0, BD, 112)
hit(43, 4.0, BD, 106)
hit(43, 8.0, BD, 110)

# ===========================================================================
#  G -- bars 44-51 : the motif comes home
# ===========================================================================
hit(44, 0.0, CR, 116, kind='cymbal')
m1(44, dyn=1.14, hats=True)
m1(45, dyn=1.16, sd1=T_HI, sd2=T_LM)
m1(46, dyn=1.18)
hit(46, 15.0, SD, 42)
# bar 47 -- fill
hit(47, 0.0, BD, 112);      hit(47, 2.0, SD, 26);   hit(47, 4.0, SD, 108)
hit(47, 6.0, SD, 28);       hit(47, 8.0, BD, 106);  hit(47, 10.0, SD, 30)
hit(47, 12.0, T_HI, 106);   hit(47, 13.0, T_HM, 96)
hit(47, 14.0, T_LM, 102);   hit(47, 15.0, T_LO, 108)

m1(48, dyn=0.62, sd1=SS, sd2=SS, ghost=0.60)         # the quiet answer
m1(49, dyn=0.66, sd1=SS, sd2=SS, ghost=0.70, hats=True)
m1(50, dyn=1.00)
# bar 51 -- last fill of the section
hit(51, 0.0, BD, 110)
hit(51, 0.0, CR2, 108, kind='cymbal')
hit(51, 4.0, SD, 110);      hit(51, 6.0, SD, 30)
hit(51, 8.0, SD, 108);      hit(51, 9.0, SD, 40)
hit(51, 10.0, SD, 106);     hit(51, 11.0, SD, 44)
hit(51, 12.0, T_HI, 108);   hit(51, 13.0, T_HM, 100)
hit(51, 14.0, T_LM, 106);   hit(51, 15.0, T_LO, 112)

# ===========================================================================
#  H -- bars 52-55 : last charge and the landing
# ===========================================================================
for b in (52, 53):
    seq = cyc([SD, T_HI, SD, T_HM, SD, T_LM, SD, T_LO,
               SD, F_HI, SD, T_LM, SD, T_HI, SD, T_HM], 16)
    for i in range(16):
        hit(b, i, seq[i], 112.0 if i % 4 == 0 else 86.0)
    hit(b, 0.0, BD, 114)
    hit(b, 8.0, BD, 108)
hit(52, 0.0, CR, 118, kind='cymbal')

# bar 54 -- eighths into sixteenths into thirty-seconds
for i in range(8):
    hit(54, i, SD, 92.0 + i * 2.0)
for i in range(8):
    hit_at(54 * P16_PER_BAR + 4.0 + i * 0.5, SD, 100.0 + i * 1.5)
for i in range(8):
    hit_at(54 * P16_PER_BAR + 8.0 + i * 0.5, SD, 112.0 + i * 1.0)

# bar 55 -- the landing (nothing is timed off it)
hit(55, 0.0, CR, 124, dur=int(4.5 * BEAT), kind='cymbal', tight=True)
hit(55, 0.0, CR2, 120, dur=int(4.5 * BEAT), tight=True)
hit(55, 0.0, BD, 122, dur=BEAT, tight=True)


# ---------------------------------------------------------------------------
#  tidying + assembly
# ---------------------------------------------------------------------------
def fix_overlaps(events):
    """Never let two strokes of the same pitch overlap: a note-off landing
    on top of the next note-on would choke a roll."""
    out = list(events)
    by_note = {}
    for i, ev in enumerate(out):
        by_note.setdefault(ev[1], []).append(i)
    for note, idxs in by_note.items():
        idxs.sort(key=lambda i: out[i][0])
        for a, b in zip(idxs, idxs[1:]):
            t1, n1, v1, d1 = out[a]
            t2 = out[b][0]
            if t1 + d1 > t2 - 1:
                out[a] = (t1, n1, v1, max(10, t2 - t1 - 1))
    return out


def check_playable(events, window=60):
    """A drummer has two hands and two feet.  Anything outside that gets
    reported (the window is ~30 ms at the tempi used here)."""
    ev = sorted(events)
    for i in range(len(ev)):
        hands = feet = 0
        for j in range(i, len(ev)):
            if ev[j][0] - ev[i][0] > window:
                break
            if ev[j][1] in FEET:
                feet += 1
            else:
                hands += 1
        if hands > 2 or feet > 2:
            print("playability note: %d hands / %d feet around tick %d"
                  % (hands, feet, ev[i][0]))


TEMPO = [
    (0, 104),      # bars 0-3    opening statement
    (4, 108),      # bars 4-11   development
    (12, 114),     # bars 12-19  second motif
    (20, 96),      # bars 20-23  breakdown, the pulse pulls back
    (24, 108),     # bars 24-27  release
    (28, 114),     # bars 28-31  roll
    (32, 120),     # bars 32-33  climbing
    (34, 126),     # bars 34-43  climax
    (44, 124),     # bars 44-49  the motif comes home
    (50, 128),     # bars 50-52  last charge
    (53, 130),     # bars 53-54  final roll
    (55, 126),     # bar 55      the landing
]


def build(path="solo.mid"):
    events = fix_overlaps(EVENTS)
    check_playable(events)

    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    msgs = [
        (0, -3, mido.MetaMessage('track_name', name='Drum Solo', time=0)),
        (0, -2, mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                 clocks_per_click=24,
                                 notated_32nd_notes_per_beat=8, time=0)),
    ]
    for tick, bpm in TEMPO:
        msgs.append((tick, -1,
                     mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm),
                                      time=0)))
    for tick, note, vel, dur in events:
        t = max(0, int(tick))
        msgs.append((t, 1, mido.Message('note_on', channel=9, note=note,
                                        velocity=vel, time=0)))
        msgs.append((t + int(dur), 0, mido.Message('note_off', channel=9,
                                                   note=note, velocity=0,
                                                   time=0)))

    msgs.sort(key=lambda m: (m[0], m[1]))

    last = 0
    for tick, _, msg in msgs:
        msg.time = tick - last
        last = tick
        track.append(msg)

    mid.save(path)


if __name__ == '__main__':
    build('solo.mid')
