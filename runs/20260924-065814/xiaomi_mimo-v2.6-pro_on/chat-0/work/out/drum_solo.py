#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drum_solo.py  ->  writes  'solo.mid'
====================================================================
A two minute drum solo for ONE drummer on a General MIDI sound module,
on MIDI channel 10.  Deterministic: byte-identical output every run.

FORM   50 bars of 4/4 at 100 bpm  =  120.000 s exactly
--------------------------------------------------------------------
   I   bars  1- 4  Invocation     theme skeleton: side stick, hats, feet
  II   bars  5-12  Theme          Motif A (clave hook + ghost notes)
 III   bars 13-20  Contrast       Motif B (linear sextuplet lines),
                                  then a hand-percussion interlude
  IV   bars 21-28  Build          Motif A ground down into ghost 16ths,
                                  accents stack up over 4 limbs, big fill
   V   bars 29-32  Break          near silence, motif in wood/clave,
                                  accelerating roll -> climax
  VI   bars 33-44  Climax         Motif A returns huge, Motif B sweeps,
                                  germ in stretto, peak, then a hole
 VII   bars 45-50  Coda           Motif A augmented, thinning to a
                                  whisper: ghost-ghost-TAP + triangle

FEEL   one consistent shuffle: the grid is 12 units per beat, so the
   swung "and" sits at 8/12 and the "a" at 10/12 of every beat.
   Placement is deliberate, never jittery:
       * ghost notes  always slightly AHEAD of the grid   (-6 ticks)
       * accents      always slightly BEHIND the grid     (+8 ticks)
   and the whole pocket drifts on a smooth curve: laid back in the
   intro/theme, pushing ahead through the build and climax (-2 to
   -12 ticks), laid way back again for the break and coda (+14..+18).

MOTIFS
   GERMA  "ghost - ghost - ACCENT" (u-4, u-2, u) - every accent in the
          piece is prepared by a double-stroke ghost pair, so accents
          and ghosts are always in ratio, never decoration.
   A      3-2 clave (u = 0,20,36 | 12,24) with the germ hung on every
          accent; contour snare - floor tom - snare / low tom - snare.
          Stated, varied by pitch contour, put under a 16th ghost
          stream, stretched in the break and coda, always recognizable.
   B      a six note rising sextuplet sweep through the whole kit
          (T1..T6), answered by its inversion; enlarged and swept
          through the climax.

LIMBS   LH/RH hands, LF (hi-hat foot) and RF (bass drum).  No two hits
   share a limb within 30 ms and no instant has more than one hit per
   limb, so at most four strikes at any instant - playable by one
   person with two hands and two feet.

SOUND   the whole GM percussion map 35-81 is used where it earns its
   place: kit (35-53,55-57,59), timbales/bongos/congas/agogo/cabasa/
   maracas/guiro/claves/whistles in the percussion interlude (54,
   60-75), wood blocks and cowbell as echoes in the coda (56,76,77),
   cuica and vibraslap as voices in the silence of the break (58,78,79)
   and triangle opening and closing the piece (80,81).
"""

from mido import MidiFile, MidiTrack, Message, MetaMessage

# ----------------------------------------------------------------------
# 1.  Musical frame
# ----------------------------------------------------------------------
TEMPO = 100                 # bpm: 1 bar = 2.400 s, 50 bars = 120.000 s
TPB   = 480                 # ticks per beat
BEAT  = TPB
BAR   = 4 * BEAT            # 1920
U     = TPB // 12           # 40 ticks = 1/12 beat (shuffle grid unit)
NBARS = 50
TOTAL = NBARS * BAR         # 96000 ticks = 200 beats = 120 s

MIN_LIMB_GAP = 24           # 30 ms: two strikes, same limb, must be apart

# ----------------------------------------------------------------------
# 2.  GM percussion map (35-81)
# ----------------------------------------------------------------------
BD  = 35   # Acoustic Bass Drum
KCK = 36   # Bass Drum 1
RIM = 37   # Side Stick
SNR = 38   # Acoustic Snare
CLP = 39   # Hand Clap
ESN = 40   # Electric Snare
T1  = 41   # Low  Floor Tom
HHC = 42   # Closed Hi-Hat
T2  = 43   # High Floor Tom
HHP = 44   # Pedal Hi-Hat
T3  = 45   # Low Tom
HHO = 46   # Open Hi-Hat
T4  = 47   # Low-Mid Tom
T5  = 48   # Hi-Mid  Tom
CR1 = 49   # Crash Cymbal 1
T6  = 50   # High Tom
RID = 51   # Ride Cymbal 1
CHN = 52   # Chinese Cymbal
RBL = 53   # Ride Bell
TAM = 54   # Tambourine
SPL = 55   # Splash Cymbal
CWB = 56   # Cowbell
CR2 = 57   # Crash Cymbal 2
VIB = 58   # Vibraslap
RD2 = 59   # Ride Cymbal 2
BGH = 60   # Hi Bongo
BGL = 61   # Low Bongo
CGM = 62   # Mute Hi Conga
CGO = 63   # Open Hi Conga
CGL = 64   # Low Conga
TAH = 65   # High Timbale
TAL = 66   # Low Timbale
AGH = 67   # High Agogo
AGL = 68   # Low Agogo
CAB = 69   # Cabasa
MAR = 70   # Maracas
WHS = 71   # Short Whistle
WHL = 72   # Long Whistle
GUS = 73   # Short Guiro
GUL = 74   # Long Guiro
CLV = 75   # Claves
WBH = 76   # Hi Wood Block
WBL = 77   # Low Wood Block
CUM = 78   # Mute Cuica
CUO = 79   # Open Cuica
TRM = 80   # Mute Triangle
TRO = 81   # Open Triangle

# limbs:  two hands, two feet
LH, RH, LF, RF = 'LH', 'RH', 'LF', 'RF'

# ----------------------------------------------------------------------
# 3.  Role -> (intensity 0..100, placement in ticks)
#     ghosts ride ahead of the pocket, accents trail behind it.
# ----------------------------------------------------------------------
ROLES = {
    'gho': (14, -6),
    'tap': (30, -3),
    'sft': (45,  0),
    'med': (62,  2),
    'str': (80,  5),
    'acc': (91,  8),
    'max': (100, 8),
}


def vel_of(intensity):
    x = max(0.0, min(100.0, intensity)) / 100.0
    return max(1, min(127, int(round(22 + 105 * (x ** 1.2)))))


# ----------------------------------------------------------------------
# 4.  Form -> placement curve and dynamics per bar
#     (bar_lo, bar_hi, push_lo, push_hi, dyn_lo, dyn_hi, name)
# ----------------------------------------------------------------------
FORM = [
    ( 1,  4,  12,  12, 0.50, 0.58, 'I    Invocation'),
    ( 5, 12,   6,   6, 0.80, 0.88, 'II   Theme - Motif A'),
    (13, 20,   3,   3, 0.70, 0.88, 'III  Contrast - Motif B / percussion'),
    (21, 28,  -2, -12, 0.90, 1.28, 'IV   Build'),
    (29, 32,  14,  14, 0.50, 0.62, 'V    Break'),
    (33, 44,  -6, -10, 1.15, 1.30, 'VI   Climax'),
    (45, 50,  14,  18, 0.95, 0.42, 'VII  Coda'),
]

FEEL = {}
MARKS = []
for (lo, hi, p0, p1, d0, d1, name) in FORM:
    MARKS.append((lo, name))
    n = hi - lo + 1
    for i, b in enumerate(range(lo, hi + 1)):
        t = i / (n - 1) if n > 1 else 0.0
        FEEL[b] = (int(round(p0 + (p1 - p0) * t)), d0 + (d1 - d0) * t)

# ----------------------------------------------------------------------
# 5.  Notation helpers  (u = 1/12 of a beat; a bar is u = 0..47)
#     beat 1 = u 0,4,8,10 | beat 2 = 12,16,20,22 | ...
# ----------------------------------------------------------------------
RAW = []                                   # (bar, u, note, role, limb, micro)


def hit(u, note, role='med', limb=RH, micro=0):
    """One strike.  u is in shuffle-grid units (40 ticks each)."""
    return (u, note, role, limb, micro)


def fig(u, note, role='str', limb=RH, ghost=True, gnote=SNR, groot='gho'):
    """THE GERM: ghost-ghost-ACCENT.  Every accent in the piece has it."""
    out = []
    if ghost:
        gh = LH if limb != LH else RH          # ghosts on the other stick
        out.append(hit(u - 4, gnote, groot, gh))
        out.append(hit(u - 2, gnote, groot, gh))
    out.append(hit(u, note, role, limb))
    return out


def put(bar, *items):
    for it in items:
        if isinstance(it, tuple):
            RAW.append((bar,) + it)
        else:
            for sub in it:
                RAW.append((bar,) + sub)


# swung 16th positions inside a bar
U16 = (0, 4, 8, 10, 12, 16, 20, 22, 24, 28, 32, 34, 36, 40, 44, 46)


def stream16(accents=(), gcycle=(SNR,), groot='gho', stacks=None):
    """Continuous swung 16ths ('inner voice') with accents on the clave."""
    out, gi = [], 0
    for i, u in enumerate(U16):
        limb = RH if i % 2 == 0 else LH
        a = next((x for x in accents if x[0] == u), None)
        if a:
            out.append(hit(a[0], a[1], a[2], limb))
        else:
            out.append(hit(u, gcycle[gi % len(gcycle)], groot, limb))
            gi += 1
        if stacks and u in stacks:
            for (n, r, l) in stacks[u]:
                out.append(hit(u, n, r, l))
    return out


def run24(notes, roles='sft', stacks=None):
    """Motif B material: 24 sextuplets over a whole bar, hands alternating."""
    out = []
    for i in range(24):
        u = 2 * i
        if notes[i] is None:
            continue
        limb = LH if i % 2 == 0 else RH
        r = roles[i] if isinstance(roles, (list, tuple)) else roles
        out.append(hit(u, notes[i], r, limb))
        if stacks and u in stacks:
            for (n, rr, l) in stacks[u]:
                out.append(hit(u, n, rr, l))
    return out


# ======================================================================
# 6.  THE SOLO
# ======================================================================

# ---------------- I.  Invocation (1-4) ------------------------------
put(1,
    hit(0, TRO, 'sft', LH), hit(0, RIM, 'med', RH), hit(0, BD, 'sft', RF),
    hit(12, HHP, 'sft', LF),
    fig(20, RIM, 'str', RH), hit(20, BD, 'sft', RF),
    fig(36, RIM, 'str', RH), hit(36, HHP, 'med', LF),
)
put(2,
    fig(12, RIM, 'str', RH), hit(12, BD, 'sft', RF), hit(12, HHP, 'med', LF),
    fig(24, RIM, 'med', RH),
    hit(36, HHP, 'med', LF), hit(36, BD, 'sft', RF),
)
put(3,
    hit(0, CLV, 'med', LH), hit(0, BD, 'sft', RF),
    fig(0, RIM, 'str', RH),
    hit(12, HHP, 'sft', LF),
    fig(20, T2, 'str', RH), hit(20, BD, 'sft', RF),
    fig(36, RIM, 'str', RH), hit(36, HHP, 'med', LF),
)
put(4,
    fig(12, T1, 'str', RH), hit(12, BD, 'med', RF), hit(12, HHP, 'med', LF),
    fig(24, SNR, 'acc', RH), hit(24, BD, 'med', RF),
    hit(36, HHP, 'sft', LF),
    # five stroke pickup, crescendo into the theme
    hit(38, SNR, 'gho', LH), hit(40, SNR, 'gho', RH), hit(42, SNR, 'tap', LH),
    hit(44, SNR, 'tap', RH), hit(46, SNR, 'sft', LH),
)

# ---------------- II.  Theme: Motif A (5-12) ------------------------
put(5,
    fig(0, SNR, 'acc', RH, ghost=False), hit(0, CR1, 'med', LH), hit(0, KCK, 'med', RF),
    hit(12, HHP, 'sft', LF),
    fig(20, T2, 'str', RH), hit(20, KCK, 'med', RF),
    fig(36, SNR, 'acc', RH), hit(36, HHP, 'med', LF),
)
put(6,
    fig(12, T3, 'str', RH), hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    fig(24, SNR, 'acc', RH), hit(24, KCK, 'med', RF),
    hit(36, KCK, 'med', RF), hit(36, HHP, 'med', LF),
    hit(40, SNR, 'gho', LH), hit(42, SNR, 'gho', RH),
)
put(7,
    fig(0, SNR, 'acc', RH), hit(0, KCK, 'med', RF),
    hit(8, T3, 'tap', LH),
    hit(12, HHP, 'sft', LF),
    fig(20, T5, 'str', RH), hit(20, KCK, 'med', RF),
    hit(28, T4, 'tap', LH),
    fig(36, T6, 'acc', RH), hit(36, KCK, 'sft', RF), hit(36, HHP, 'med', LF),
)
put(8,
    fig(12, T1, 'str', RH), hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    fig(24, SNR, 'acc', RH), hit(24, KCK, 'med', RF),
    hit(36, HHP, 'med', LF),
    hit(36, T3, 'sft', LH), hit(38, T4, 'sft', RH), hit(40, T5, 'sft', LH),
    hit(42, T6, 'sft', RH), hit(44, SNR, 'tap', LH), hit(46, SNR, 'med', RH),
)
#   groove relief: ride + a steady ghost line on the swung 16ths
put(9,
    hit(0, RBL, 'med', RH), hit(0, KCK, 'med', RF),
    hit(8, RID, 'tap', RH),
    hit(12, RID, 'tap', RH), hit(12, HHP, 'med', LF),
    hit(20, RID, 'tap', RH), hit(20, KCK, 'sft', RF),
    hit(24, RBL, 'med', RH),
    hit(32, RID, 'tap', RH), hit(32, KCK, 'med', RF),
    hit(36, RID, 'tap', RH), hit(36, HHP, 'med', LF),
    hit(44, RID, 'tap', RH),
    hit(4, SNR, 'gho', LH), hit(10, SNR, 'gho', LH), hit(16, SNR, 'gho', LH),
    hit(22, SNR, 'gho', LH), hit(28, SNR, 'gho', LH), hit(34, SNR, 'gho', LH),
    hit(40, SNR, 'gho', LH), hit(46, SNR, 'gho', LH),
)
put(10,
    hit(0, RBL, 'med', RH),
    hit(8, RID, 'tap', RH), hit(8, KCK, 'sft', RF),
    hit(12, RID, 'tap', RH), hit(12, HHP, 'med', LF),
    hit(20, RID, 'tap', RH),
    hit(24, RBL, 'med', RH), hit(24, KCK, 'med', RF),
    hit(32, RID, 'tap', RH),
    hit(36, RID, 'tap', RH), hit(36, HHP, 'med', LF),
    hit(44, RID, 'tap', RH), hit(44, KCK, 'sft', RF),
    hit(2, SNR, 'gho', LH), hit(10, SNR, 'gho', LH), hit(18, SNR, 'gho', LH),
    hit(22, SNR, 'gho', LH), hit(26, SNR, 'gho', LH), hit(34, SNR, 'gho', LH),
    hit(38, SNR, 'gho', LH), hit(40, SNR, 'gho', LH),
)
put(11,
    fig(0, SNR, 'acc', RH), hit(0, CR2, 'sft', LH), hit(0, KCK, 'med', RF),
    hit(8, T4, 'tap', LH),
    hit(12, HHP, 'sft', LF),
    fig(20, T2, 'str', RH), hit(20, KCK, 'med', RF),
    hit(28, T5, 'tap', LH),
    fig(36, SNR, 'acc', RH), hit(36, HHP, 'med', LF),
)
put(12,
    fig(12, SNR, 'acc', RH), hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    fig(24, T1, 'str', RH), hit(24, KCK, 'med', RF),
    hit(32, T6, 'med', LH), hit(34, T5, 'med', RH), hit(36, T4, 'med', LH),
    hit(38, T3, 'med', RH), hit(40, T2, 'med', LH), hit(42, T1, 'med', RH),
    hit(44, SNR, 'str', LH), hit(46, SNR, 'tap', RH),
    hit(36, HHP, 'med', LF),
)

# ---------------- III.  Contrast: Motif B (13-20) -------------------
put(13,
    hit(0, T1, 'sft', LH), hit(2, T2, 'sft', RH), hit(4, T3, 'sft', LH),
    hit(6, T4, 'sft', RH), hit(8, T5, 'sft', LH), hit(10, T6, 'sft', RH),
    hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    hit(24, T6, 'sft', RH), hit(26, T5, 'sft', LH), hit(28, T4, 'sft', RH),
    hit(30, T3, 'sft', LH), hit(32, T2, 'sft', RH), hit(34, T1, 'sft', LH),
    hit(36, KCK, 'med', RF), hit(36, HHP, 'med', LF),
    hit(44, SNR, 'gho', LH), hit(46, SNR, 'gho', RH),
)
put(14,
    hit(0, SNR, 'sft', RH), hit(2, T3, 'sft', LH), hit(4, T4, 'sft', RH),
    hit(6, T5, 'sft', LH), hit(8, T6, 'sft', RH), hit(10, SNR, 'sft', LH),
    hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    hit(16, T6, 'sft', LH), hit(18, T5, 'sft', RH), hit(20, T4, 'sft', LH),
    hit(22, T3, 'sft', RH), hit(24, T2, 'sft', LH), hit(26, T1, 'sft', RH),
    hit(28, SNR, 'tap', LH), hit(30, KCK, 'med', RF),
    hit(36, HHP, 'med', LF), hit(36, KCK, 'sft', RF),
    hit(40, SNR, 'gho', LH), hit(42, SNR, 'gho', RH), hit(44, SNR, 'gho', LH),
    hit(46, SNR, 'gho', RH),
)
notes15 = [T1, T2, T3, T4, T5, T6, SNR, T6, T5, T4, SNR, T3,
           T2, T1, SNR, T1, T2, T3, SNR, T4, T5, T6, SNR, T6]
roles15 = ['acc'] + ['sft'] * 9 + ['str'] + ['sft'] * 7 + ['acc'] + ['sft'] * 5
put(15, run24(notes15, roles15),
    hit(0, KCK, 'med', RF), hit(20, KCK, 'med', RF), hit(36, KCK, 'med', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
notes16 = [T1, T2, T3, T4, T5, T6, SNR, SNR, T6, T5, T4, T3,
           T2, T1, SNR, SNR, T1, T2, T3, T4, T5, T6, SNR, SNR]
roles16 = ['sft'] * 6 + ['tap'] * 2 + ['med'] * 8 + ['str'] * 8
put(16, run24(notes16, roles16),
    hit(12, KCK, 'med', RF), hit(20, KCK, 'med', RF), hit(36, KCK, 'med', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
#   hand percussion: the motif's clave in claves, ghosts become shaker
put(17,
    fig(0, CLV, 'str', RH, ghost=False),
    fig(20, CLV, 'str', RH, ghost=False),
    fig(36, CLV, 'acc', RH, ghost=False),
    hit(0, WHS, 'sft', LH),
    hit(4, CAB, 'gho', LH), hit(8, CGO, 'sft', LH),
    hit(16, CAB, 'gho', LH), hit(18, CAB, 'gho', LH),
    hit(22, CGM, 'sft', LH), hit(28, CGO, 'med', LH),
    hit(32, CAB, 'gho', LH), hit(34, CAB, 'gho', LH),
    hit(40, GUS, 'sft', LH), hit(44, CGM, 'gho', LH),
    hit(0, BD, 'med', RF), hit(20, BD, 'sft', RF), hit(32, BD, 'med', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
put(18,
    fig(12, CLV, 'str', RH, ghost=False),
    fig(24, CLV, 'str', RH, ghost=False),
    hit(0, WHL, 'sft', LH),
    hit(4, BGL, 'sft', LH), hit(8, BGH, 'sft', LH), hit(10, BGL, 'gho', LH),
    hit(16, BGH, 'sft', LH), hit(20, BGL, 'sft', LH), hit(22, BGH, 'gho', LH),
    hit(24, CLP, 'med', LH),
    hit(28, AGH, 'sft', LH), hit(30, AGL, 'gho', LH), hit(34, MAR, 'gho', LH),
    hit(36, TAH, 'sft', RH), hit(38, TAL, 'sft', LH), hit(40, TAH, 'sft', RH),
    hit(42, TAL, 'sft', LH), hit(44, TAH, 'tap', RH), hit(46, TAL, 'tap', LH),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
    hit(12, BD, 'med', RF), hit(24, BD, 'med', RF),
)
put(19,
    hit(0, T1, 'sft', LH), hit(4, T2, 'sft', RH), hit(8, T3, 'sft', LH),
    hit(12, T4, 'sft', RH), hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    hit(16, T5, 'sft', LH), hit(20, T6, 'sft', RH),
    hit(24, SNR, 'med', LH), hit(24, KCK, 'med', RF),
    hit(28, T3, 'sft', RH), hit(32, T4, 'med', LH), hit(36, T5, 'med', RH),
    hit(36, HHP, 'med', LF),
    hit(40, T6, 'med', LH), hit(44, SNR, 'str', RH), hit(44, KCK, 'med', RF),
)
notes20 = [T1, T2, T3, T4, T5, T6, SNR, None, T6, T5, T4, T3,
           T2, T1, SNR, SNR, T6, T5, T4, T3, T2, T1, SNR, SNR]
roles20 = ['sft'] * 6 + ['str'] + ['med'] * 7 + ['str'] * 10
put(20, run24(notes20, roles20),
    hit(0, KCK, 'med', RF), hit(14, KCK, 'med', RF), hit(36, KCK, 'str', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)

# ---------------- IV.  Build (21-28) --------------------------------
put(21,
    stream16([(0, SNR, 'acc'), (20, SNR, 'acc'), (36, SNR, 'acc')], (SNR,)),
    hit(0, KCK, 'med', RF), hit(20, KCK, 'med', RF), hit(32, KCK, 'sft', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
put(22,
    stream16([(12, T2, 'acc'), (24, T3, 'acc')], (SNR, SNR, SNR, T1)),
    hit(12, KCK, 'med', RF), hit(24, KCK, 'med', RF), hit(40, KCK, 'sft', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
put(23,
    stream16([(0, SNR, 'acc'), (20, T5, 'acc'), (36, T6, 'acc')],
             (SNR, SNR, T4, SNR, SNR, T5)),
    hit(0, HHP, 'med', LF), hit(20, HHP, 'med', LF), hit(36, HHP, 'med', LF),
    hit(12, KCK, 'med', RF), hit(24, KCK, 'med', RF), hit(44, KCK, 'sft', RF),
)
put(24,
    stream16([(12, T6, 'acc'), (24, HHO, 'acc')], (SNR, SNR, SNR, T2)),
    hit(12, HHP, 'med', LF), hit(24, HHP, 'med', LF),
    hit(0, KCK, 'med', RF), hit(20, KCK, 'med', RF),
    hit(36, KCK, 'str', RF), hit(44, KCK, 'sft', RF),
)
put(25,
    stream16([(0, SNR, 'acc'), (20, SNR, 'acc'), (36, SNR, 'acc')],
             (SNR, SNR, T3, SNR),
             stacks={0: [(CR1, 'str', LH)], 20: [(CWB, 'str', LH)],
                     36: [(CR2, 'str', LH)]}),
    hit(0, KCK, 'str', RF), hit(20, KCK, 'str', RF), hit(32, KCK, 'med', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
put(26,
    stream16([(12, T1, 'acc'), (24, SNR, 'acc')], (SNR, SNR, T4, SNR),
             stacks={12: [(SPL, 'str', LH)], 24: [(CR1, 'str', LH)]}),
    hit(12, KCK, 'str', RF), hit(24, KCK, 'str', RF), hit(40, KCK, 'med', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
#   bar 27: 16ths over two beats, then a 32nd burst over two
burst = []
CYC27 = (SNR, T6, T5, T4, T3, T2)
for i in range(24):
    u = 24 + i
    limb = LH if i % 2 == 0 else RH
    r = 'gho' if i < 6 else 'tap' if i < 12 else 'sft' if i < 18 else 'med'
    n = CYC27[i % 6]
    if u == 36:
        n, r, limb = CR2, 'str', LH
    burst.append(hit(u, n, r, limb))
put(27,
    hit(0, SNR, 'acc', RH), hit(0, CR1, 'str', LH), hit(0, KCK, 'str', RF),
    hit(4, SNR, 'gho', LH), hit(8, SNR, 'gho', RH), hit(10, T3, 'gho', LH),
    hit(12, SNR, 'gho', RH), hit(12, HHP, 'med', LF),
    hit(16, SNR, 'gho', LH), hit(20, T5, 'acc', RH), hit(20, CWB, 'str', LH),
    hit(20, KCK, 'str', RF),
    hit(22, SNR, 'gho', LH),
    burst,
    hit(36, KCK, 'str', RF), hit(36, HHP, 'med', LF),
)
#   bar 28: the fill, one enormous hit, then a beat of silence
fill28 = [(0, T6), (4, T5), (8, T4), (10, T3), (12, T2), (16, T1),
          (20, SNR), (22, SNR),
          (24, T1), (26, T2), (28, T3), (30, T4), (32, T5), (34, T6)]
put(28,
    [hit(u, n, 'str' if u < 24 else 'acc', LH if i % 2 == 0 else RH)
     for i, (u, n) in enumerate(fill28)],
    hit(0, KCK, 'str', RF), hit(12, KCK, 'str', RF), hit(24, KCK, 'str', RF),
    hit(12, HHP, 'med', LF), hit(24, HHP, 'med', LF),
    hit(36, CHN, 'max', LH), hit(36, SNR, 'max', RH),
    hit(36, KCK, 'max', RF), hit(36, HHP, 'med', LF),
)

# ---------------- V.  Break (29-32) ---------------------------------
put(29,
    hit(0, VIB, 'tap', RH),
    hit(12, HHP, 'sft', LF),
    hit(20, BD, 'sft', RF),
    hit(28, RIM, 'gho', LH), hit(30, RIM, 'gho', LH),
    hit(36, HHP, 'sft', LF), hit(36, RIM, 'sft', RH),
    hit(44, SNR, 'gho', LH), hit(46, SNR, 'gho', RH),
)
put(30,
    hit(0, CUM, 'gho', LH),
    hit(12, HHP, 'sft', LF),
    hit(20, CUO, 'sft', RH),
    hit(28, CUM, 'gho', LH),
    hit(36, HHP, 'sft', LF),
)
put(31,
    fig(0, CLV, 'med', RH), hit(0, BD, 'sft', RF),
    hit(12, HHP, 'sft', LF),
    fig(20, WBH, 'tap', LH), hit(20, BD, 'sft', RF),
    fig(36, RIM, 'med', RH), hit(36, HHP, 'med', LF),
)
roll = []
u, i = 0, 0
while u < 47:
    frac = u / 47.0
    r = ('gho', 'tap', 'sft', 'med', 'str', 'acc', 'max')[min(6, int(frac * 7))]
    roll.append(hit(u, SNR, r, LH if i % 2 == 0 else RH))
    i += 1
    u += 2 if u < 24 else 1                    # accelerating roll
put(32, roll,
    hit(12, HHP, 'tap', LF), hit(24, HHP, 'tap', LF), hit(36, HHP, 'med', LF),
)

# ---------------- VI.  Climax (33-44) -------------------------------
put(33,
    fig(0, SNR, 'max', RH, ghost=False), hit(0, CR1, 'str', LH), hit(0, KCK, 'str', RF),
    hit(12, HHP, 'med', LF),
    fig(20, T2, 'str', RH), hit(20, KCK, 'str', RF),
    fig(36, SNR, 'acc', RH), hit(36, CR2, 'str', LH),
    hit(36, KCK, 'str', RF), hit(36, HHP, 'med', LF),
)
put(34,
    fig(12, T1, 'acc', RH), hit(12, KCK, 'str', RF), hit(12, HHP, 'med', LF),
    fig(24, SNR, 'max', RH), hit(24, CR1, 'str', LH), hit(24, KCK, 'str', RF),
    hit(36, HHP, 'med', LF), hit(36, KCK, 'sft', RF),
    hit(40, SNR, 'gho', LH), hit(42, SNR, 'gho', RH),
)
put(35,
    fig(0, T6, 'acc', RH), hit(0, CR2, 'med', LH), hit(0, KCK, 'str', RF),
    hit(8, T4, 'tap', LH),
    hit(12, HHP, 'med', LF),
    fig(20, T5, 'str', RH), hit(20, KCK, 'str', RF),
    hit(28, T2, 'tap', LH),
    fig(36, T3, 'acc', RH), hit(36, KCK, 'str', RF), hit(36, HHP, 'med', LF),
)
put(36,
    fig(12, T4, 'acc', RH), hit(12, KCK, 'str', RF), hit(12, HHP, 'med', LF),
    fig(24, SNR, 'max', RH), hit(24, CR1, 'str', LH), hit(24, KCK, 'str', RF),
    hit(32, T6, 'str', LH), hit(34, T5, 'str', RH), hit(36, T4, 'str', LH),
    hit(38, T3, 'str', RH), hit(40, T2, 'str', LH), hit(42, T1, 'str', RH),
    hit(44, SNR, 'acc', LH), hit(46, SNR, 'acc', RH),
    hit(36, HHP, 'med', LF),
)
notes37 = [T1, T2, T3, T4, T5, T6, CR1, T1, T2, T3, T4, T5,
           T6, T5, T4, T3, T2, T1, CR2, T1, T2, T3, T4, T5]
put(37, run24(notes37, ['med'] * 12 + ['str'] * 12),
    hit(12, KCK, 'str', RF), hit(36, KCK, 'str', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
notes38 = [T6, T5, T4, T3, T2, T1, CR1, T6, T5, T4, T3, T2,
           T1, T2, T3, T4, T5, T6, CR2, T6, T5, T4, T3, T2]
put(38, run24(notes38, ['med'] * 6 + ['str'] * 12 + ['acc'] * 6),
    hit(0, KCK, 'str', RF), hit(12, KCK, 'str', RF),
    hit(24, KCK, 'str', RF), hit(36, KCK, 'str', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
#   the germ in stretto: right hand every beat, left hand one half beat behind
for k, u in enumerate((0, 12, 24, 36)):
    put(39, fig(u, (T2, T3, T4, T5)[k], 'str', RH, ghost=(u != 0)))
for u in (6, 18, 30, 42):
    put(39, fig(u, SNR, 'med', LH))
put(39,
    hit(0, KCK, 'str', RF), hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    hit(24, KCK, 'str', RF), hit(36, KCK, 'med', RF), hit(36, HHP, 'med', LF),
)
for k, u in enumerate((0, 12, 24, 36)):
    put(40, fig(u, (T6, T5, T4, T3)[k], 'acc', LH))
for u in (6, 18, 30, 42):
    put(40, fig(u, SNR, 'str', RH))
put(40,
    hit(0, KCK, 'str', RF), hit(12, KCK, 'str', RF), hit(12, HHP, 'med', LF),
    hit(24, KCK, 'str', RF), hit(36, KCK, 'str', RF), hit(36, HHP, 'med', LF),
)
put(41,
    stream16([(0, SNR, 'max'), (20, T6, 'acc'), (36, SNR, 'max')],
             (SNR, SNR, T3, T4),
             stacks={0: [(CR1, 'str', LH), (KCK, 'str', RF)],
                     20: [(CWB, 'str', LH), (KCK, 'str', RF)],
                     36: [(CR2, 'str', LH), (KCK, 'str', RF), (HHP, 'med', LF)]}),
    hit(12, HHP, 'med', LF), hit(44, KCK, 'med', RF),
)
put(42,
    stream16([(12, T6, 'max'), (24, SNR, 'acc')], (SNR, SNR, T4, T5),
             stacks={12: [(CR1, 'str', LH), (KCK, 'str', RF), (HHP, 'med', LF)],
                     24: [(CR2, 'str', LH), (KCK, 'str', RF)],
                     36: [(KCK, 'str', RF), (HHP, 'med', LF)]}),
    hit(44, KCK, 'med', RF),
)
notes43 = [T1, T2, T3, T4, T5, T6, T1, T2, T3, T4, T5, T6,
           T6, T5, T4, T3, T2, T1, ESN, SNR, ESN, SNR, SNR, SNR]
roles43 = ['str'] * 12 + ['acc'] * 6 + ['max'] * 6
put(43, run24(notes43, roles43),
    hit(0, KCK, 'str', RF), hit(12, KCK, 'str', RF),
    hit(24, KCK, 'str', RF), hit(36, KCK, 'str', RF),
    hit(12, HHP, 'med', LF), hit(36, HHP, 'med', LF),
)
put(44,
    hit(0, CHN, 'max', LH), hit(0, SNR, 'max', RH),
    hit(0, KCK, 'max', RF), hit(0, HHP, 'med', LF),
    hit(24, SPL, 'sft', RH),
)                                            # beat 4 left open: germ returns

# ---------------- VII.  Coda (45-50) --------------------------------
put(45,
    fig(0, SNR, 'max', RH), hit(0, CR1, 'str', LH), hit(0, KCK, 'str', RF),
    hit(12, HHP, 'med', LF),
    fig(20, T2, 'str', RH), hit(20, KCK, 'med', RF),
    fig(36, SNR, 'acc', RH), hit(36, HHP, 'med', LF),
)
put(46,
    fig(12, T1, 'str', RH), hit(12, KCK, 'med', RF), hit(12, HHP, 'med', LF),
    fig(24, SNR, 'acc', RH), hit(24, KCK, 'med', RF),
    hit(36, HHP, 'med', LF),
    hit(40, CWB, 'tap', LH),
)
put(47,
    fig(0, RIM, 'med', RH), hit(0, BD, 'sft', RF),
    hit(12, HHP, 'sft', LF),
    fig(20, WBH, 'tap', LH), hit(20, BD, 'sft', RF),
    fig(36, RIM, 'med', RH), hit(36, HHP, 'med', LF),
)
put(48,
    fig(12, RIM, 'med', RH), hit(12, BD, 'sft', RF), hit(12, HHP, 'med', LF),
    fig(24, WBL, 'tap', LH), hit(24, BD, 'sft', RF),
    hit(36, HHP, 'sft', LF),
)
put(49,
    fig(0, SNR, 'acc', RH), hit(0, TRO, 'sft', LH), hit(0, BD, 'med', RF),
    hit(12, HHP, 'sft', LF),
    fig(24, RIM, 'sft', RH),
    hit(36, HHP, 'sft', LF),
)
put(50,
    fig(0, RIM, 'str', RH), hit(0, BD, 'sft', RF), hit(0, TRO, 'sft', LH),
    hit(12, HHP, 'sft', LF),
)

# ======================================================================
# 7.  Resolve: placement, velocities, playability, MIDI events
# ======================================================================
def note_len(n):
    if n in (CR1, CR2, CHN, SPL, RID, RBL, RD2, TRO, HHO):
        return 3 * BEAT
    if n in (VIB, CUO, GUL, WHS, WHL, TRM, CUM):
        return 2 * BEAT
    return BEAT


def resolve():
    hits = []
    skipped = 0
    for (bar, u, note, role, limb, micro) in RAW:
        push, dyn = FEEL[bar]
        tick = (bar - 1) * BAR + int(round(u * U)) + push + ROLES[role][1] + micro
        if tick < 0:
            skipped += 1
            continue
        hits.append([tick, note, vel_of(ROLES[role][0] * dyn), limb, note_len(note)])

    hits.sort(key=lambda h: (h[0], h[1], h[3]))

    # playability: one strike per limb at a time, and a limb must have time
    # to get back (flam distance).  Anything closer is nudged, never dropped.
    last, moved = {}, 0
    for h in hits:
        prev = last.get(h[3])
        if prev is not None and h[0] < prev + MIN_LIMB_GAP:
            h[0] = prev + MIN_LIMB_GAP
            moved += 1
        last[h[3]] = h[0]

    # note-off delays: never overlap the next strike of the same key
    nxt = {}
    for i in range(len(hits) - 1, -1, -1):
        n = hits[i][1]
        gap = nxt.get(n)
        if gap is not None:
            hits[i][4] = min(hits[i][4], max(12, gap - hits[i][0] - 1))
        nxt[n] = hits[i][0]

    # hard check of "two hands, two feet"
    at = {}
    for (tick, note, vel, limb, dur) in hits:
        s = at.setdefault(tick, set())
        assert limb not in s, 'two strikes on one limb at tick %d' % tick
        s.add(limb)
        assert len(s) <= 4, 'more than four limbs at tick %d' % tick
    return hits, skipped, moved


def build_midi(hits):
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    meta, drums = MidiTrack(), MidiTrack()
    mid.tracks.append(meta)
    mid.tracks.append(drums)

    meta.append(MetaMessage('track_name', name='drum_solo.py - form', time=0))
    meta.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    meta.append(MetaMessage('set_tempo', tempo=60000000 // TEMPO, time=0))
    prev = 0
    for (bar, name) in MARKS:
        t = (bar - 1) * BAR
        meta.append(MetaMessage('marker', text=name, time=t - prev))
        prev = t
    meta.append(MetaMessage('end_of_track', time=TOTAL - prev))

    drums.append(MetaMessage('track_name',
                            name='Drum Solo - GM percussion, channel 10', time=0))
    ev = []
    for (tick, note, vel, limb, dur) in hits:
        ev.append((tick, 1, 'on', note, vel))
        ev.append((tick + dur, 0, 'off', note, 0))
    ev.sort(key=lambda e: (e[0], e[1]))
    prev = 0
    for (tick, _o, kind, note, vel) in ev:
        d = tick - prev
        if kind == 'on':
            drums.append(Message('note_on', channel=9, note=note,
                                 velocity=vel, time=d))
        else:
            drums.append(Message('note_off', channel=9, note=note,
                                 velocity=0, time=d))
        prev = tick
    end = max(TOTAL, prev)
    drums.append(MetaMessage('end_of_track', time=end - prev))
    return mid


def main():
    hits, skipped, moved = resolve()
    build_midi(hits).save('solo.mid')
    print('solo.mid written: %d bars, %.3f s, %d strikes (%d germs), '
          '%d nudged for the hands' %
          (NBARS, TOTAL / (TPB * TEMPO / 60.0), len(hits), len(RAW), moved))
    if skipped:
        print('(%d pre-roll strikes dropped)' % skipped)


if __name__ == '__main__':
    main()
