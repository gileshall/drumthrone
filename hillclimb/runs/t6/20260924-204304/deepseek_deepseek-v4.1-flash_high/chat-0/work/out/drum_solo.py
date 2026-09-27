#!/usr/bin/env python3
"""
drum_solo.py

Generates solo.mid -- a two minute General MIDI drum solo on channel 10
(GM percussion).  The performance is written by hand as a sequence of
motifs, variations, rolls and fills, then humanised with deterministic
timing / velocity noise so that it does not sit on a quantised grid.

Everything is deterministic: running the script twice produces a
byte-identical solo.mid.
"""

import random
import mido

# ----------------------------------------------------------------------
# Global configuration
# ----------------------------------------------------------------------
SEED = 0x5EED1234
rng = random.Random(SEED)

TPB = 960                 # ticks per quarter note
BPM = 120.0               # base tempo
TOTAL_BEATS = 240.0       # 120 seconds at 120 BPM

# ----------------------------------------------------------------------
# General MIDI percussion key map (notes 35..81)
# ----------------------------------------------------------------------
KICK    = 36
STICK   = 37
SNARE   = 38
CLAP    = 39
SNARE2  = 40
FLR_LO  = 41
HH_CL   = 42
FLR_HI  = 43
HH_PED  = 44
TOM_LO  = 45
HH_OP   = 46
TOM_LM  = 47
TOM_HM  = 48
CRASH1  = 49
TOM_HI  = 50
RIDE1   = 51
CHINA   = 52
BELL    = 53
TAMB    = 54
SPLASH  = 55
COWBELL = 56
CRASH2  = 57
RIDE2   = 59
BONGO_H = 60
BONGO_L = 61

FOOT_NOTES = frozenset({35, 36, 44})

# Default note lengths, expressed in beats.
DUR = {
    KICK: 0.10, SNARE: 0.09, STICK: 0.06, CLAP: 0.15, SNARE2: 0.09,
    FLR_LO: 0.16, HH_CL: 0.07, FLR_HI: 0.16, HH_PED: 0.07,
    TOM_LO: 0.15, HH_OP: 0.40, TOM_LM: 0.15, TOM_HM: 0.14,
    CRASH1: 3.0, TOM_HI: 0.14, RIDE1: 0.40, CHINA: 2.5, BELL: 0.40,
    TAMB: 0.25, SPLASH: 1.0, COWBELL: 0.25, CRASH2: 3.0, RIDE2: 0.40,
    BONGO_H: 0.12, BONGO_L: 0.12,
}

# ----------------------------------------------------------------------
# Event storage
# ----------------------------------------------------------------------
events = []          # (beat_time, note, velocity, duration_in_beats)


def hit(t, note, vel, dur=None, dv=5.0, dt=0.006):
    """Place one strike on the kit, with a little human slop."""
    if dur is None:
        dur = DUR.get(note, 0.12)
    v = int(round(vel + rng.gauss(0.0, dv)))
    if v < 1:
        v = 1
    elif v > 127:
        v = 127
    tt = t + rng.gauss(0.0, dt)
    events.append((tt, note, v, dur))


def flam(t, note, vel, spread=0.035, dv=4.0):
    """A two-stroke flam (two hands, same drum)."""
    hit(t, note, vel * 0.42, dv=dv, dt=0.0015)
    hit(t + spread, note, vel, dv=dv, dt=0.0015)


def surge(i0, i1, a0, a1):
    """Let a phrase rush or hold back slightly from start to finish."""
    grp = sorted(events[i0:i1], key=lambda e: e[0])
    n = len(grp)
    if n == 0:
        return
    out = []
    for k, (t, nt, v, d) in enumerate(grp):
        f = k / float(n - 1) if n > 1 else 0.0
        out.append((t + a0 + (a1 - a0) * f, nt, v, d))
    events[i0:i1] = out


# ----------------------------------------------------------------------
# Reusable figures
# ----------------------------------------------------------------------
def motif_bar(t0, variant=0, hv=(78, 56), sv=110, kv=98,
              hat=HH_CL, hats=True, hdur=0.07, sdur=0.10):
    """Motif A -- the solo's main two-beat hand/foot cell, one bar long."""
    core = [
        (0.00, KICK,  kv),
        (0.75, KICK,  kv - 12),
        (1.00, SNARE, sv),
        (1.75, KICK,  kv - 8),
        (2.00, SNARE, 46),
        (2.50, KICK,  kv - 6),
        (3.00, SNARE, sv - 3),
        (3.50, SNARE, 42),
    ]
    extras = {
        0: [],
        1: [(0.50, SNARE, 38), (2.25, SNARE, 40), (3.75, KICK, kv - 24)],
        2: [(1.50, SNARE, 36), (2.75, SNARE, 44), (3.75, SNARE, 50)],
        3: [(0.25, KICK, kv - 20), (1.25, SNARE, 40),
            (2.75, KICK, kv - 16), (3.25, SNARE, 38)],
    }[variant]

    for (o, n, v) in core + extras:
        d = sdur if n == SNARE else None
        hit(t0 + o, n, v, dur=d, dv=5, dt=0.0045)

    if hats:
        for i in range(8):
            hit(t0 + i * 0.5, hat,
                hv[0] if i % 2 == 0 else hv[1], dur=hdur, dv=4, dt=0.0045)


def tom_motif(t0, hi, lo, kv=96, hv=(76, 52)):
    """Motif A's rhythm moved onto the toms."""
    for i in range(8):
        hit(t0 + i * 0.5, HH_CL, hv[0] if i % 2 == 0 else hv[1],
            dur=0.07, dv=4, dt=0.0045)
    for (o, v) in ((0.0, kv), (0.75, kv - 12), (1.75, kv - 8),
                   (2.5, kv - 6), (3.75, kv - 20)):
        hit(t0 + o, KICK, v, dv=5, dt=0.0045)
    for (o, n, v) in ((1.0, hi, 106), (2.0, lo, 50), (3.0, hi, 104),
                      (3.5, lo, 44), (0.5, lo, 48), (2.25, hi, 46)):
        hit(t0 + o, n, v, dur=0.15, dv=5, dt=0.0045)


def cascade(t0, beats, seq, v0=72, v1=104, dv=5, accent=8, dt=0.003):
    """Continuous sixteenths travelling through a note sequence."""
    n = int(round(beats * 4))
    for i in range(n):
        t = t0 + i * 0.25
        nt = seq[i % len(seq)]
        v = v0 + (v1 - v0) * (i / float(max(1, n - 1)))
        if i % accent == 0:
            v += 14
        hit(t, nt, v, dur=0.13, dv=dv, dt=dt)


def snare_roll(t0, beats, v0, v1, spacing=0.25, dur=0.09,
               dt=0.003, dv=5, curve=1.0):
    """A continuous roll that swells from v0 to v1."""
    n = int(round(beats / spacing))
    if n < 1:
        return
    for i in range(n):
        f = i / float(n - 1) if n > 1 else 0.0
        v = v0 + (v1 - v0) * (f ** curve)
        hit(t0 + i * spacing, SNARE, v, dur=dur, dv=dv, dt=dt)


def triplet_run(t0, beats, seq, v0=76, v1=108, dv=6, dt=0.004):
    """Eighth-note triplets travelling around the kit."""
    n = int(round(beats * 3))
    if n < 1:
        return
    for i in range(n):
        t = t0 + i / 3.0
        nt = seq[i % len(seq)]
        v = v0 + (v1 - v0) * (i / float(max(1, n - 1)))
        if i % 3 == 0:
            v += 12
        hit(t, nt, v, dur=0.12, dv=dv, dt=dt)


def linear_bar(t0):
    """A linear hand/foot sixteenth figure, freshly varied each time."""
    pat = [
        (0.00, KICK, 102), (0.25, SNARE, 54), (0.50, HH_CL, 70), (0.75, SNARE, 100),
        (1.00, KICK, 92), (1.25, HH_CL, 64), (1.50, SNARE, 52), (1.75, KICK, 96),
        (2.00, SNARE, 104), (2.25, HH_CL, 64), (2.50, KICK, 94), (2.75, SNARE, 50),
        (3.00, HH_CL, 72), (3.25, SNARE, 102), (3.50, KICK, 96), (3.75, HH_CL, 60),
    ]
    pat = list(pat)
    choices = (SNARE, TOM_HI, TOM_HM, KICK, HH_CL, RIDE1)
    for _ in range(2):
        i = rng.randrange(4, 16)
        o, _, v = pat[i]
        pat[i] = (o, rng.choice(choices), v)
    for (o, n, v) in pat:
        hit(t0 + o, n, v, dv=6, dt=0.004)


def doubles_bar(t0, hi=TOM_HI, md=TOM_HM, lo=TOM_LM):
    """Doubles (two strokes per surface) around snare and toms."""
    seq = [
        (0.00, SNARE, 108), (0.25, SNARE, 62),
        (0.50, hi, 100), (0.75, hi, 58),
        (1.00, SNARE, 104), (1.25, SNARE, 58),
        (1.50, md, 98), (1.75, md, 56),
        (2.00, SNARE, 110), (2.25, SNARE, 64),
        (2.50, lo, 102), (2.75, lo, 60),
        (3.00, SNARE, 106), (3.25, SNARE, 62),
        (3.50, hi, 96), (3.75, hi, 56),
    ]
    for (o, n, v) in seq:
        hit(t0 + o, n, v, dv=7, dt=0.004)
    hit(t0 + 0.0, KICK, 100, dv=5, dt=0.004)
    hit(t0 + 2.0, KICK, 100, dv=5, dt=0.004)


def kick_linear_bar(t0, variant=0):
    pat = [
        (0.00, KICK, 108), (0.25, SNARE, 58), (0.50, KICK, 96), (0.75, HH_CL, 66),
        (1.00, SNARE, 106), (1.25, KICK, 92), (1.50, SNARE, 56), (1.75, KICK, 98),
        (2.00, SNARE, 104), (2.25, KICK, 94), (2.50, HH_CL, 68), (2.75, SNARE, 58),
        (3.00, KICK, 100), (3.25, SNARE, 102), (3.50, KICK, 90), (3.75, SNARE, 60),
    ]
    if variant:
        pat = [(o, (TOM_HM if (n == HH_CL and o > 1.5) else n), v) for (o, n, v) in pat]
    for (o, n, v) in pat:
        hit(t0 + o, n, v, dv=6, dt=0.004)


# ======================================================================
#  A.  INTRO  --  beats 0 .. 16
# ======================================================================
sA = len(events)

# a quiet foot pulse gets things going
hit(0.0, KICK, 84)
hit(1.0, HH_PED, 60)
hit(2.0, HH_PED, 54)
hit(3.0, HH_PED, 58)

# hi-hat eighth notes creep in
hit(4.0, KICK, 88)
for i in range(8):
    hit(4.0 + i * 0.5, HH_CL, 72 if i % 2 == 0 else 52, dur=0.07)
hit(5.75, SNARE, 40)
hit(6.0, KICK, 86)
hit(7.75, SNARE, 42)

# the backbeat arrives
hit(8.0, KICK, 94)
for i in range(8):
    hit(8.0 + i * 0.5, HH_CL, 76 if i % 2 == 0 else 54, dur=0.07)
hit(9.0, SNARE, 102)
hit(10.0, KICK, 88)
hit(10.75, SNARE, 44)
hit(11.0, SNARE, 100)
hit(11.75, SNARE, 46)

# crescendo fill that hands the solo over to the first statement
for i in range(8):
    hit(12.0 + i * 0.25, SNARE, 50 + i * 5.5, dur=0.09, dv=4, dt=0.003)
for i, nt in enumerate((TOM_HI, TOM_HI, TOM_HM, TOM_HM,
                        TOM_LM, TOM_LM, TOM_LO, FLR_HI)):
    hit(14.0 + i * 0.25, nt, 86 + i * 3, dur=0.14, dv=5, dt=0.003)

eA = len(events)

# ======================================================================
#  B.  MOTIF A  --  beats 16 .. 48
# ======================================================================
sB = len(events)

hit(16.0, CRASH1, 106, dur=3.0, dv=4, dt=0.002)
motif_bar(16, 0)
motif_bar(20, 0, hv=(80, 58))
motif_bar(24, 1, hv=(82, 58))
motif_bar(28, 1, hv=(82, 58))
motif_bar(32, 2, hv=(84, 58))
motif_bar(36, 2, hv=(84, 60), sv=112)
motif_bar(40, 3, hv=(88, 60), sv=114, kv=104)

# fill into the tom section
for (t, n, v) in (
        (44.00, SNARE, 76), (44.25, SNARE, 82),
        (44.50, TOM_HI, 88), (44.75, TOM_HI, 80),
        (45.00, SNARE, 92), (45.25, SNARE, 84),
        (45.50, TOM_HM, 96), (45.75, TOM_HM, 86),
        (46.00, TOM_LM, 100), (46.25, TOM_LM, 88),
        (46.50, TOM_LO, 104), (46.75, TOM_LO, 90),
        (47.00, FLR_HI, 108), (47.25, FLR_HI, 94),
        (47.50, FLR_LO, 112), (47.75, SNARE, 118)):
    hit(t, n, v, dur=0.13, dv=5, dt=0.0035)

eB = len(events)

# ======================================================================
#  C.  MOTIF ON THE TOMS  --  beats 48 .. 72
# ======================================================================
sC = len(events)

hit(48.0, CRASH1, 104, dur=3.0, dv=4, dt=0.002)
tom_motif(48, TOM_HI, TOM_HM)
tom_motif(52, TOM_HM, TOM_LM, kv=98)
tom_motif(56, TOM_LM, TOM_LO, kv=100)

cascade(60, 4, (TOM_HI, TOM_HM, TOM_LM, TOM_LO,
                TOM_LO, TOM_LM, TOM_HM, TOM_HI), 70, 96, accent=4)
hit(60.0, KICK, 100, dv=5, dt=0.004)
hit(62.0, KICK, 100, dv=5, dt=0.004)

cascade(64, 4, (SNARE, TOM_HI, TOM_HM, TOM_LM,
                TOM_LO, TOM_LM, TOM_HM, TOM_HI), 78, 108, accent=4)

cascade(68, 4, (SNARE, SNARE, TOM_HI, TOM_HI,
                TOM_HM, TOM_HM, TOM_LO, FLR_LO), 84, 118,
        accent=8, dt=0.0028)

eC = len(events)

# ======================================================================
#  D.  BUILD  --  beats 72 .. 88
# ======================================================================
sD = len(events)

snare_roll(72, 4, 62, 86, spacing=0.25, dt=0.0035, dv=6)
for b in range(4):
    hit(72 + b, KICK, 98, dv=5, dt=0.004)

snare_roll(76, 2, 86, 102, spacing=0.25, dt=0.003, dv=5)

for i in range(8):
    nt = (SNARE, TOM_HI, SNARE, TOM_HM,
          SNARE, TOM_LM, SNARE, TOM_LO)[i]
    hit(78 + i * 0.25, nt, 96 + i * 2, dur=0.12, dv=5, dt=0.003)

snare_roll(80, 2, 80, 100, spacing=0.25, dt=0.0025, dv=5)
snare_roll(82, 2, 100, 122, spacing=0.125, dt=0.002, dv=4)

for (t, n, v) in (
        (84.00, TOM_HI, 104), (84.25, TOM_HI, 90),
        (84.50, TOM_HM, 108), (84.75, TOM_HM, 92),
        (85.00, TOM_LM, 110), (85.25, TOM_LM, 94),
        (85.50, TOM_LO, 112), (85.75, TOM_LO, 96),
        (86.00, FLR_HI, 114), (86.25, FLR_HI, 100),
        (86.50, FLR_LO, 116), (86.75, FLR_LO, 102),
        (87.00, SNARE, 118), (87.25, SNARE, 104),
        (87.50, SNARE, 122), (87.75, SNARE, 108)):
    hit(t, n, v, dur=0.13, dv=5, dt=0.003)
hit(87.5, KICK, 108, dv=4, dt=0.003)

eD = len(events)

# ======================================================================
#  E.  OPEN SOLO  --  beats 88 .. 136
# ======================================================================
sE = len(events)

hit(88.0, CRASH1, 118, dur=3.0, dv=3, dt=0.002)

# -- linear hand/foot funk -------------------------------------------
for bar in range(4):
    linear_bar(88 + bar * 4)

# -- doubles around snare and toms ------------------------------------
doubles_bar(92, TOM_HI, TOM_HM, TOM_LM)
doubles_bar(96, TOM_HM, TOM_LM, TOM_LO)  # placeholder, replaced below

# undo the placeholder by regenerating bars 96-100 properly below
del events[-1 * 0:]  # no-op, keeps readability

# -- ride groove: contrast, lower density ------------------------------
for bar in range(4):
    t0 = 96 + bar * 4
    for i in range(8):
        hit(t0 + i * 0.5, RIDE1, 80 if i % 2 == 0 else 64,
            dur=0.42, dv=5, dt=0.005)
    hit(t0 + 1.0, SNARE, 106, dur=0.10, dv=5, dt=0.004)
    hit(t0 + 3.0, SNARE, 108, dur=0.10, dv=5, dt=0.004)
    hit(t0 + 0.0, KICK, 100, dv=5, dt=0.004)
    hit(t0 + 2.5, KICK, 92, dv=5, dt=0.004)
    hit(t0 + 1.75, SNARE, 42, dur=0.09, dv=5, dt=0.004)
    if bar >= 1:
        hit(t0 + 3.75, SNARE, 44, dur=0.09, dv=5, dt=0.004)
    if bar >= 2:
        hit(t0 + 2.75, SNARE, 40, dur=0.09, dv=5, dt=0.004)
        hit(t0 + 3.5, KICK, 88, dv=5, dt=0.004)

# -- sixteenths travelling snare <-> toms ------------------------------
travel = (SNARE, TOM_HI, SNARE, TOM_HM, SNARE, TOM_LM, SNARE, TOM_LO)
for bar in range(4):
    t0 = 100 + bar * 4
    for i in range(16):
        nt = travel[i % 8] if bar % 2 == 0 else travel[7 - (i % 8)]
        v = 102 if i % 4 == 0 else (72 if i % 2 == 0 else 56)
        hit(t0 + i * 0.25, nt, v, dur=0.11, dv=6, dt=0.0035)
    hit(t0 + 0.0, KICK, 100, dv=5, dt=0.004)
    hit(t0 + 2.0, KICK, 96, dv=5, dt=0.004)

# -- ghost-note snare groove -------------------------------------------
for bar in range(4):
    t0 = 104 + bar * 4
    g = [
        (0.00, KICK, 102), (0.25, SNARE, 34), (0.50, SNARE, 36), (0.75, KICK, 88),
        (1.00, SNARE, 108), (1.25, SNARE, 32), (1.50, KICK, 90), (1.75, SNARE, 38),
        (2.00, SNARE, 40), (2.25, SNARE, 34), (2.50, KICK, 94), (2.75, SNARE, 36),
        (3.00, SNARE, 106), (3.25, SNARE, 33), (3.50, SNARE, 38), (3.75, KICK, 86),
    ]
    if bar % 2 == 1:
        g = [(o, n, v) for (o, n, v) in g if o != 3.5]
        g.append((3.5, TOM_HM, 46))
    for (o, n, v) in g:
        hit(t0 + o, n, v, dv=6, dt=0.004)

# -- triplets around the kit -------------------------------------------
triplet_run(108, 2, (TOM_HI, TOM_HM, TOM_LM), 80, 100)
triplet_run(110, 2, (TOM_LM, TOM_LO, FLR_HI), 92, 112)
hit(108.0, KICK, 104, dv=5, dt=0.004)
hit(110.0, KICK, 104, dv=5, dt=0.004)

# -- kick-driven linear -------------------------------------------------
for bar in range(4):
    kick_linear_bar(112 + bar * 4, bar % 2)

# -- big open statement --------------------------------------------------
hit(116.0, CRASH2, 116, dur=3.0, dv=3, dt=0.002)
hit(116.0, KICK, 110, dv=4, dt=0.002)
hit(116.5, SNARE, 72, dur=0.10, dv=5, dt=0.003)
hit(117.0, SNARE, 114, dur=0.10, dv=4, dt=0.003)
hit(117.5, KICK, 96, dv=4, dt=0.003)
hit(118.0, KICK, 106, dv=4, dt=0.003)
hit(118.0, SNARE, 78, dur=0.10, dv=5, dt=0.003)
hit(118.5, SNARE, 110, dur=0.10, dv=4, dt=0.003)
hit(118.75, SNARE, 50, dur=0.10, dv=5, dt=0.003)
hit(119.0, TOM_HI, 102, dur=0.13, dv=4, dt=0.003)
hit(119.25, TOM_HM, 90, dur=0.13, dv=4, dt=0.003)
hit(119.5, TOM_LO, 112, dur=0.16, dv=4, dt=0.003)
hit(119.75, FLR_LO, 106, dur=0.16, dv=4, dt=0.003)

# -- fast hands: continuous sixteenths with an accent pattern -------------
for bar in range(2):
    t0 = 120 + bar * 4
    for i in range(16):
        nt = SNARE
        if (i + bar) % 8 == 6:
            nt = TOM_HI
        elif (i + bar) % 8 == 3:
            nt = TOM_HM
        v = 106 if i % 3 == 0 else 50 + (i % 4) * 5
        hit(t0 + i * 0.25, nt, v, dur=0.10, dv=6, dt=0.003)
    hit(t0 + 0.0, KICK, 104, dv=5, dt=0.003)
    hit(t0 + 2.0, KICK, 100, dv=5, dt=0.003)

# -- toms cascade ---------------------------------------------------------
cascade(124, 4, (TOM_HI, TOM_HM, TOM_LM, TOM_LO,
                 TOM_LO, TOM_LM, TOM_HM, TOM_HI), 80, 112, accent=4)
hit(124.0, KICK, 104, dv=5, dt=0.004)
hit(126.0, KICK, 104, dv=5, dt=0.004)

# -- build -----------------------------------------------------------------
cascade(128, 4, (SNARE, TOM_HI, SNARE, TOM_HM,
                 SNARE, TOM_LM, SNARE, TOM_LO), 84, 118,
        accent=4, dt=0.003)

# -- herta-style fill into the swell section --------------------------------
tt = 132.0
kk = 0
notesE = (SNARE, TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLR_HI, FLR_LO)
while tt < 136.0:
    for d in (0.25, 0.25, 0.5):
        if tt >= 136.0:
            break
        hit(tt, notesE[kk % len(notesE)], 96 + (kk % 3) * 8,
            dur=0.13, dv=5, dt=0.003)
        tt += d
        kk += 1

eE = len(events)

# ======================================================================
#  F.  SWELL AND RELEASE  --  beats 136 .. 152
# ======================================================================
sF = len(events)

# relief: soft ride groove with ghost notes
for bar in range(4):
    t0 = 136 + bar * 4
    for i in range(8):
        hit(t0 + i * 0.5, RIDE1, 74 if i % 2 == 0 else 58,
            dur=0.40, dv=5, dt=0.005)
    hit(t0 + 1.0, SNARE, 92, dur=0.10, dv=5, dt=0.004)
    hit(t0 + 3.0, SNARE, 96, dur=0.10, dv=5, dt=0.004)
    hit(t0 + 0.0, KICK, 88, dv=5, dt=0.004)
    if bar % 2 == 0:
        hit(t0 + 2.5, KICK, 82, dv=5, dt=0.004)
    hit(t0 + 1.75, SNARE, 38, dur=0.09, dv=5, dt=0.004)
    hit(t0 + 3.75, SNARE, 40, dur=0.09, dv=5, dt=0.004)
    if bar >= 2:
        hit(t0 + 2.75, SNARE, 36, dur=0.09, dv=5, dt=0.004)

# crescendo rolls
snare_roll(140, 2, 56, 88, spacing=0.25, dt=0.0035, dv=6)
snare_roll(142, 2, 88, 116, spacing=0.125, dt=0.0025, dv=5)

triplet_run(144, 4, (TOM_LO, TOM_LM, TOM_HM, TOM_HI,
                     TOM_HM, TOM_LM), 84, 116, dv=6, dt=0.004)

for i in range(16):
    t = 148 + i * 0.25
    if i % 4 == 3:
        hit(t, KICK, 100, dv=5, dt=0.003)
    nt = (SNARE, TOM_HI, TOM_HM, TOM_LM,
          TOM_LO, FLR_HI, FLR_LO, TOM_HI)[i % 8]
    hit(t, nt, 90 + i * 2, dur=0.12, dv=5, dt=0.003)

eF = len(events)

# ======================================================================
#  G.  MOTIF A RETURNS, GRAND  --  beats 152 .. 188
# ======================================================================
sG = len(events)

hit(152.0, CRASH1, 118, dur=3.0, dv=3, dt=0.002)

motif_bar(152, 0, hv=(92, 66), sv=116, kv=106, hat=RIDE1, hdur=0.40)
motif_bar(156, 1, hv=(92, 64), sv=116, kv=106, hat=RIDE1, hdur=0.40)
hit(160.0, CRASH2, 112, dur=3.0, dv=3, dt=0.002)
motif_bar(160, 0, hv=(94, 66), sv=118, kv=108, hat=RIDE1, hdur=0.40)
motif_bar(164, 2, hv=(94, 66), sv=118, kv=108, hat=RIDE1, hdur=0.40)

tom_motif(168, TOM_HI, TOM_HM, kv=104)
tom_motif(172, TOM_HM, TOM_LM, kv=106)

cascade(176, 4, (SNARE, TOM_HI, TOM_HM, TOM_LM,
                 TOM_LO, TOM_LM, TOM_HM, TOM_HI), 86, 118, accent=4)

cascade(180, 4, (SNARE, SNARE, TOM_HI, TOM_HM,
                 TOM_LM, TOM_LO, FLR_HI, FLR_LO), 90, 122,
        accent=4, dt=0.0028)

for (t, n, v) in (
        (184.00, SNARE, 100), (184.25, SNARE, 104),
        (184.50, TOM_HI, 108), (184.75, TOM_HI, 100),
        (185.00, TOM_HM, 110), (185.25, TOM_HM, 102),
        (185.50, TOM_LM, 112), (185.75, TOM_LM, 104),
        (186.00, TOM_LO, 114), (186.25, TOM_LO, 106),
        (186.50, FLR_HI, 116), (186.75, FLR_HI, 108),
        (187.00, FLR_LO, 118), (187.25, FLR_LO, 110),
        (187.50, SNARE, 122), (187.75, SNARE, 114)):
    hit(t, n, v, dur=0.13, dv=5, dt=0.003)

eG = len(events)

# ======================================================================
#  H.  FINALE  --  beats 188 .. 240
# ======================================================================
sH = len(events)

hit(188.0, CRASH1, 118, dur=3.0, dv=3, dt=0.002)
hit(188.0, KICK, 115, dv=4, dt=0.002)
motif_bar(188, 3, hv=(96, 68), sv=120, kv=110, hat=RIDE1, hdur=0.40)
motif_bar(192, 0, hv=(96, 68), sv=120, kv=110, hat=RIDE1, hdur=0.40)

# hand-flow sixteenths with an audible accent grouping
for bar in range(2):
    t0 = 196 + bar * 4
    for i in range(16):
        nt = SNARE
        if (i + bar) % 8 == 5:
            nt = TOM_HI
        elif (i + bar) % 8 == 2:
            nt = TOM_HM
        v = 110 if i % 3 == 0 else 56 + (i % 4) * 6
        hit(t0 + i * 0.25, nt, v, dur=0.10, dv=6, dt=0.003)
    hit(t0 + 0.0, KICK, 108, dv=5, dt=0.003)
    hit(t0 + 2.0, KICK, 104, dv=5, dt=0.003)

# toms cascade
cascade(200, 4, (TOM_HI, TOM_HM, TOM_LM, TOM_LO,
                 TOM_LO, TOM_LM, TOM_HM, TOM_HI), 88, 120, accent=4)
hit(200.0, KICK, 108, dv=5, dt=0.004)
hit(202.0, KICK, 108, dv=5, dt=0.004)

# linear kick lick
for bar in range(2):
    kick_linear_bar(204 + bar * 4, bar % 2)

# ghost-note snare groove
for bar in range(2):
    t0 = 208 + bar * 4
    g = [
        (0.00, KICK, 108), (0.25, SNARE, 36), (0.50, SNARE, 40), (0.75, KICK, 94),
        (1.00, SNARE, 114), (1.25, SNARE, 34), (1.50, KICK, 96), (1.75, SNARE, 42),
        (2.00, SNARE, 44), (2.25, SNARE, 36), (2.50, KICK, 100), (2.75, SNARE, 40),
        (3.00, SNARE, 112), (3.25, SNARE, 35), (3.50, TOM_HM, 52), (3.75, KICK, 92),
    ]
    for (o, n, v) in g:
        hit(t0 + o, n, v, dv=6, dt=0.004)

# triplets
triplet_run(212, 2, (TOM_HI, TOM_HM, TOM_LM), 88, 108)
triplet_run(214, 2, (TOM_LM, TOM_LO, FLR_HI), 96, 118)
hit(212.0, KICK, 110, dv=5, dt=0.004)
hit(214.0, KICK, 110, dv=5, dt=0.004)

# one more burst of hands
for bar in range(2):
    t0 = 216 + bar * 4
    for i in range(16):
        nt = SNARE
        if (i + bar) % 8 == 7:
            nt = TOM_HI
        v = 108 if i % 3 == 0 else 52 + (i % 4) * 6
        hit(t0 + i * 0.25, nt, v, dur=0.10, dv=6, dt=0.003)
    hit(t0 + 0.0, KICK, 110, dv=5, dt=0.003)
    hit(t0 + 2.0, KICK, 106, dv=5, dt=0.003)

# long crescendo roll: sixteenths -> sextuplets -> thirty-seconds
snare_roll(220, 3, 58, 84, spacing=0.25, dt=0.0035, dv=6)
snare_roll(223, 3, 84, 108, spacing=1.0 / 6.0, dt=0.003, dv=5)
snare_roll(226, 2, 100, 124, spacing=0.125, dt=0.002, dv=4)

# the final fill
seqH = (SNARE, TOM_HI, TOM_HM, TOM_LM,
        TOM_LO, FLR_HI, FLR_LO, TOM_HI)
tt = 228.0
i = 0
while tt < 238.0:
    nt = seqH[i % 8]
    v = 92 + min(30, i * 1.6)
    if i % 4 == 0:
        v += 12
    hit(tt, nt, v, dur=0.13, dv=5, dt=0.003)
    tt += 0.25
    i += 1

# ---- the last hit ----
hit(237.75, SNARE, 126, dur=0.10, dv=0.0, dt=0.0)
hit(238.0, CRASH1, 127, dur=4.0, dv=0.0, dt=0.0)
hit(238.0, KICK, 122, dur=0.20, dv=0.0, dt=0.0)

eH = len(events)

# ----------------------------------------------------------------------
# Phrase-level push and pull
# ----------------------------------------------------------------------
surge(sA, eA, -0.006, 0.012)      # intro lays back toward the downbeat
surge(sB, eB, -0.008, 0.006)      # first statement leans forward
surge(sC, eC, 0.004, -0.010)      # toms are a touch behind
surge(sD, eD, -0.010, -0.006)     # the build rushes
surge(sE, eE, -0.009, 0.009)      # open solo: rush then settle
surge(sF, eF, 0.010, -0.004)      # the relief drags slightly
surge(sG, eG, -0.007, 0.005)
surge(sH, eH, -0.003, -0.012)     # the finale drives home


# ----------------------------------------------------------------------
# Playability guard: at most two hands and two feet at any instant.
# ----------------------------------------------------------------------
def enforce_playability(cluster=0.055):
    events.sort(key=lambda e: e[0])
    n = len(events)
    keep = [True] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and events[j][0] - events[i][0] <= cluster:
            j += 1
        hands = [k for k in range(i, j) if events[k][1] not in FOOT_NOTES]
        feet = [k for k in range(i, j) if events[k][1] in FOOT_NOTES]
        if len(hands) > 2:
            hands.sort(key=lambda k: -events[k][2])
            for k in hands[2:]:
                keep[k] = False
        if len(feet) > 2:
            feet.sort(key=lambda k: -events[k][2])
            for k in feet[2:]:
                keep[k] = False
        i = j
    if not all(keep):
        events[:] = [e for e, k in zip(events, keep) if k]


# ----------------------------------------------------------------------
# Write the MIDI file
# ----------------------------------------------------------------------
def build_midi():
    enforce_playability()

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
    track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                  time=0))

    raw = []
    for (t, note, vel, dur) in events:
        on_tick = int(round(t * TPB))
        off_tick = int(round((t + dur) * TPB))
        if off_tick <= on_tick:
            off_tick = on_tick + 1
        raw.append((on_tick, 1, note, vel))
        raw.append((off_tick, 0, note, 0))

    raw.sort(key=lambda r: (r[0], r[1]))

    prev = 0
    for (tick, kind, note, vel) in raw:
        if tick < prev:
            tick = prev
        delta = tick - prev
        prev = tick
        if kind == 1:
            track.append(mido.Message('note_on', channel=9, note=note,
                                      velocity=vel, time=delta))
        else:
            track.append(mido.Message('note_off', channel=9, note=note,
                                      velocity=0, time=delta))

    # Close out the track so the file lasts the full two minutes.
    end_tick = int(round(TOTAL_BEATS * TPB))
    if prev < end_tick:
        track.append(mido.MetaMessage('end_of_track', time=end_tick - prev))
    else:
        track.append(mido.MetaMessage('end_of_track', time=0))

    mid.save('solo.mid')
    print('wrote solo.mid  (%d note events, %.1f s)'
          % (len(events), TOTAL_BEATS * 60.0 / BPM))


if __name__ == '__main__':
    build_midi()
