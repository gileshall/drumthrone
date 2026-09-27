#!/usr/bin/env python3
"""
drum_solo.py

Writes ``solo.mid``: a two minute General MIDI drum solo on channel 10,
played back by a GM synthesizer.

The performance is generated deterministically from a fixed random seed,
so running the script twice produces a byte identical file.

Musical plan (beats, 4/4):

    0- 24  statement of the motif, sparse, the feet join, first fill
   24- 56  the motif developed over a full groove with ghost notes
   56- 80  the same motif translated onto the toms (call and response)
   80- 96  arrival crash, sudden drop, then a swelling roll
   96-144  up-tempo ride feature, single strokes around the kit, doubles
  144-168  contrast: half time, space, cowbell / congas / bongos, re-build
  168-236  reprise at full voice, alternating groove and fills, big build,
           final fill and a landing hit instead of a fade out.
"""

import math
import random

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

# ----------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------
TPB = 960                    # ticks per quarter note
CH = 9                       # MIDI channel 10 (zero based)
SEED = 20240613              # fixed seed -> identical file every run
END_BEAT = 236.0             # beat of the final downbeat
TARGET_END = 116.5           # seconds at that downbeat (tail -> ~120 s)

rng = random.Random(SEED)

# GM percussion map (notes 35..81)
KICK, KICK2 = 36, 35
STICK, SNARE, CLAP = 37, 38, 39
HAT, OHAT, PHT = 42, 46, 44
RIDE, RIDE2, BELL = 51, 59, 53
CRASH, CRASH2, SPLASH, CHINA = 49, 57, 55, 52
T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR = 50, 48, 47, 45, 43, 41
COWBELL, TAMB, CLAVES, WB_HI, WB_LO = 56, 54, 75, 76, 77
CONGA_HI, CONGA_LO, BONGO_HI, BONGO_LO = 63, 64, 60, 61
TRI_OPEN, TRI_MUTE = 81, 80

HAND_NOTES = frozenset([
    STICK, SNARE, CLAP, HAT, OHAT, RIDE, RIDE2, BELL, CRASH, CRASH2,
    SPLASH, CHINA, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR,
    COWBELL, TAMB, CLAVES, WB_HI, WB_LO, CONGA_HI, CONGA_LO,
    BONGO_HI, BONGO_LO, TRI_OPEN, TRI_MUTE,
])
FOOT_NOTES = frozenset([KICK, KICK2, PHT])

# ----------------------------------------------------------------------
# event collection
# ----------------------------------------------------------------------
EV = []          # (beat, note, velocity, duration_in_beats, kind)


def hit(beat, note, vel, dur=0.08, kind='norm'):
    if beat < 0.0:
        beat = 0.0
    EV.append((float(beat), int(note), int(round(vel)), float(dur), kind))


# short hands for the kit ------------------------------------------------
def K(b, v=96, d=0.10):        hit(b, KICK, v, d, 'foot')
def S(b, v=100, d=0.07):       hit(b, SNARE, v, d, 'acc')
def G(b, v=26):                hit(b, SNARE, v, 0.05, 'ghost')
def H(b, v=62, d=0.05):        hit(b, HAT, v, d, 'norm')
def OH(b, v=66, d=0.28):       hit(b, OHAT, v, d, 'norm')
def P(b, v=60, d=0.08):        hit(b, PHT, v, d, 'foot')
def R(b, v=66, sw=0.0, d=0.13): hit(b + sw, RIDE, v, d, 'norm')
def RB(b, v=80, sw=0.0):       hit(b + sw, BELL, v, 0.15, 'norm')
def CR(b, v=104, d=1.8):       hit(b, CRASH, v, d, 'acc')
def T(n, b, v=84, d=0.12):     hit(b, n, v, d, 'norm')
def X(n, b, v=70, d=0.10):     hit(b, n, v, d, 'norm')


def fill_run(t0, notes, step=0.25, v0=76, v1=104, dur=0.07):
    """A single line of strokes travelling around the kit."""
    n = len(notes)
    for i, nm in enumerate(notes):
        u = i / (n - 1) if n > 1 else 0.0
        v = v0 + (v1 - v0) * u
        hit(t0 + i * step, nm, v, dur, 'acc' if v >= 92 else 'norm')


def strokes(t0, notes, step=0.25, vacc=104, vnorm=58,
            acc=(0, 4, 8, 12), dur=0.07):
    """Even hand work with accents on chosen indices."""
    for i, nm in enumerate(notes):
        if i in acc:
            hit(t0 + i * step, nm, vacc, dur, 'acc')
        else:
            v = vnorm + ((i * 5) % 3) * 3
            hit(t0 + i * step, nm, v, dur, 'norm')


def roll(t0, t1, note=SNARE, v0=40, v1=118, rates=(4, 6, 8),
         curve=1.0, dur=0.05):
    """Accelerating single-stroke roll with an internal crescendo."""
    nseg = len(rates)
    for si, rate in enumerate(rates):
        s0 = t0 + (t1 - t0) * si / nseg
        s1 = t0 + (t1 - t0) * (si + 1) / nseg
        step = 1.0 / rate
        n = max(1, int(round((s1 - s0) / step)))
        for k in range(n):
            b = s0 + k * step
            if b >= t1 - 1e-9:
                break
            u = (si + (k + 0.5) / n) / nseg
            v = v0 + (v1 - v0) * (u ** curve)
            hit(b, note, v, dur, 'norm' if v < 92 else 'acc')


# ----------------------------------------------------------------------
# bar vocabulary - the motif and its relatives
# ----------------------------------------------------------------------
KICK_CELLS = [
    [(0.0, 100), (2.0, 86), (2.75, 76)],
    [(0.0, 102), (1.5, 78), (2.5, 88), (3.75, 72)],
    [(0.0, 100), (0.75, 74), (2.0, 84), (3.25, 78)],
    [(0.0, 104), (2.0, 88), (3.5, 80)],
    [(0.0, 98), (1.75, 70), (2.5, 86), (3.0, 76)],
    [(0.0, 102), (1.25, 72), (2.75, 80), (3.25, 74)],
    [(0.0, 102), (2.0, 86), (3.5, 74)],
    [(0.0, 100), (1.0, 64), (2.0, 88), (3.75, 76)],
]

SNARE_CELLS = [
    [(1.0, 100), (3.0, 104)],
    [(1.0, 98), (3.0, 102), (3.75, 62)],
    [(1.0, 100), (2.75, 60), (3.0, 104)],
    [(1.0, 102), (3.0, 100), (3.5, 56)],
    [(1.0, 96), (2.5, 58), (3.0, 104)],
    [(1.0, 100), (3.0, 102), (3.25, 54)],
]

GHOST_CELLS = [
    [(0.75, 26), (1.75, 24), (2.25, 22), (3.5, 28)],
    [(0.5, 22), (1.5, 26), (2.75, 24), (3.25, 22)],
    [(0.25, 20), (0.75, 28), (1.75, 22), (3.75, 26)],
    [(1.25, 24), (1.75, 28), (2.25, 22), (3.5, 24)],
    [(0.5, 20), (0.75, 26), (2.0, 20), (3.75, 22)],
    [(1.5, 20), (2.25, 24), (2.75, 22), (3.25, 20)],
]


def near(a, seq):
    return any(abs(a - s) < 1e-6 for s in seq)


def play_bar(t0, kcell=(), scell=(), gcell=(), vscale=1.0, gscale=1.0,
             hat_sub=0.5, hat_note=HAT, hat_base=60, hat_acc=8,
             hat_skip=(), ohat=(), pedal=(), crash=(), extra=()):
    """Play one bar.  Hand instruments: cymbal line + snare line; feet: K+PHT."""
    if hat_sub:
        n = int(round(4.0 / hat_sub))
        for i in range(n):
            off = round(i * hat_sub, 6)
            if near(off, hat_skip):
                continue
            if near(off, ohat):
                OH(t0 + off, hat_base + 8)
            else:
                v = hat_base + (hat_acc if i % 2 == 0 else 0)
                hit(t0 + off, hat_note, v, 0.05, 'norm')
    for off, v in pedal:
        P(t0 + off, v)
    for off, v in crash:
        CR(t0 + off, v)
    for off, v in kcell:
        K(t0 + off, v * vscale)

    slots = {}
    for off, v in gcell:
        slots[off] = ['ghost', v * gscale]
    for off, v in scell:
        slots[off] = ['acc', v * vscale]
    for off in sorted(slots):
        kind, v = slots[off]
        hit(t0 + off, SNARE, v, 0.07, kind)

    for off, note, v, kind in extra:
        hit(t0 + off, note, v, 0.10, kind)


def mutate(kc, sc, gc):
    """Small deterministic variations so no bar is a copy of another."""
    kc, sc, gc = list(kc), list(sc), list(gc)

    def used():
        u = set()
        for cell in (kc, sc, gc):
            for off, _ in cell:
                u.add(round(off, 3))
        return u

    if rng.random() < 0.50:
        u = used()
        free = [i * 0.25 for i in range(16) if round(i * 0.25, 3) not in u]
        if free:
            kc.append((rng.choice(free), rng.randint(64, 88)))
    if rng.random() < 0.40:
        u = used()
        free = [i * 0.25 for i in range(1, 16) if round(i * 0.25, 3) not in u]
        if free:
            gc.append((rng.choice(free), rng.randint(18, 30)))
    if rng.random() < 0.30 and sc:
        off, v = sc[-1]
        if off < 3.5:
            sc[-1] = (off + 0.25, v)
    return kc, sc, gc


# ======================================================================
# sections
# ======================================================================
def sec_intro():
    # bar 1 - walk in on the hats
    t = 0.0
    for i in range(8):
        H(t + 0.5 * i, 54 + (8 if i % 2 == 0 else 0))
    K(t + 0.0, 94); S(t + 1.0, 90); K(t + 2.0, 74)
    S(t + 3.0, 94); G(t + 3.5, 26)

    # bar 2 - the motif, stated plainly
    t = 4.0
    for i in range(8):
        H(t + 0.5 * i, 58 + (8 if i % 2 == 0 else 0))
    K(t + 0.0, 100); G(t + 0.75, 26); S(t + 1.0, 100); G(t + 1.75, 24)
    K(t + 2.0, 86); K(t + 2.75, 74); S(t + 3.0, 104); G(t + 3.5, 24)

    # bar 3 - same shape, the feet join in
    t = 8.0
    for i in range(8):
        H(t + 0.5 * i, 60 + (8 if i % 2 == 0 else 0))
    P(t + 2.0, 58); P(t + 3.5, 52)
    K(t + 0.0, 102); S(t + 1.0, 100); G(t + 1.75, 26); K(t + 2.25, 80)
    S(t + 3.0, 104); G(t + 3.75, 24)

    # bar 4 - first fill
    t = 12.0
    for i in range(6):
        H(t + 0.5 * i, 62 + (8 if i % 2 == 0 else 0))
    K(t + 0.0, 102); S(t + 1.0, 102); G(t + 1.75, 28)
    K(t + 2.0, 86); S(t + 2.5, 96)
    fill_run(t + 3.0, [T_MID, T_LO, T_LOW, T_FLOOR], 0.25, 80, 96)

    # bar 5 - crash and keep rolling
    t = 16.0
    CR(t + 0.0, 104)
    K(t + 0.0, 104)
    for i in range(1, 8):
        H(t + 0.5 * i, 60 + (7 if i % 2 == 0 else 0))
    G(t + 0.75, 26); S(t + 1.0, 100); K(t + 2.0, 86)
    G(t + 2.75, 24); S(t + 3.0, 104); K(t + 3.5, 74)

    # bar 6 - pickup into the main groove
    t = 20.0
    for i in range(6):
        H(t + 0.5 * i, 62 + (8 if i % 2 == 0 else 0))
    K(t + 0.0, 104); G(t + 0.5, 24); S(t + 1.0, 102); G(t + 1.5, 26)
    K(t + 2.0, 88); G(t + 2.25, 24); S(t + 2.5, 96)
    fill_run(t + 3.0, [SNARE, T_HI, T_MIDHI, SNARE], 0.25, 74, 100)


def sec_groove_a():
    for bar in range(8):
        t = 24.0 + 4.0 * bar
        crash = ()
        skip = ()
        if bar in (0, 4):
            crash = [(0.0, 102 if bar == 0 else 96)]
            skip = (0.0,)

        if bar == 7:
            # last bar: groove for two beats, then a run into the toms
            play_bar(t, [(0.0, 104), (1.5, 78)], [(1.0, 102)], [(0.75, 26)],
                     hat_sub=0.5, hat_base=62, hat_skip=(2.0, 2.5, 3.0, 3.5))
            fill_run(t + 2.0,
                     [T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_LOW, SNARE],
                     0.25, 82, 110)
            continue

        vscale = 0.95 + 0.10 * ((bar % 4) / 3.0)
        kc = KICK_CELLS[(bar * 3 + 1) % len(KICK_CELLS)]
        sc = SNARE_CELLS[(bar * 2 + 1) % len(SNARE_CELLS)]
        gc = GHOST_CELLS[(bar * 4 + 2) % len(GHOST_CELLS)]
        kc, sc, gc = mutate(kc, sc, gc)
        ohat = (3.5,) if bar % 3 == 1 else ()
        pedal = [(3.5, 54)] if bar % 2 else []
        play_bar(t, kc, sc, gc, vscale=vscale, gscale=0.95,
                 hat_sub=0.5, hat_base=58 + 3 * (bar % 3), ohat=ohat,
                 pedal=pedal, crash=crash, hat_skip=skip)


def sec_toms():
    # bar 1 - the motif moved onto the toms, ride underneath
    t = 56.0
    CR(t + 0.0, 102); K(t + 0.0, 104)
    for i in range(1, 8):
        R(t + 0.5 * i, 64 + (8 if i % 2 == 0 else 0),
          0.04 if i % 2 else 0.0)
    G(t + 0.75, 26)
    T(T_HI, t + 1.0, 100)
    K(t + 2.0, 88)
    T(T_MID, t + 2.5, 86); T(T_MID, t + 2.75, 74)
    T(T_MIDHI, t + 3.0, 104); G(t + 3.5, 24)

    # bar 2 - answer: a run down the toms
    t = 60.0
    for i in range(4):
        R(t + 0.5 * i, 62 + (6 if i % 2 == 0 else 0))
    K(t + 0.0, 96)
    T(T_HI, t + 1.0, 98)
    fill_run(t + 2.0,
             [T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_FLOOR, SNARE],
             0.25, 82, 106)

    # bar 3 - motif with ride bell accents
    t = 64.0
    for i in range(8):
        b = t + 0.5 * i
        if i % 4 == 0:
            RB(b, 82)
        else:
            R(b, 62 + (8 if i % 2 == 0 else 0), 0.04 if i % 2 else 0.0)
    K(t + 0.0, 104); G(t + 0.75, 24)
    T(T_MIDHI, t + 1.0, 102)
    K(t + 2.0, 90); K(t + 2.75, 76)
    T(T_MID, t + 3.0, 104); G(t + 3.5, 26)

    # bar 4 - answer with paired strokes
    t = 68.0
    for i in range(4):
        R(t + 0.5 * i, 62)
    K(t + 0.0, 98)
    T(T_HI, t + 1.0, 100)
    fill_run(t + 2.0,
             [T_MIDHI, T_MIDHI, T_MID, T_MID, T_LO, T_LO, T_LOW, T_FLOOR],
             0.25, 84, 104)

    # bar 5 - motif, bigger, kick pushing
    t = 72.0
    for i in range(8):
        b = t + 0.5 * i
        if i % 4 == 0:
            RB(b, 84)
        else:
            R(b, 64, 0.04 if i % 2 else 0.0)
    K(t + 0.0, 106); G(t + 0.5, 26)
    T(T_HI, t + 1.0, 104)
    K(t + 1.75, 84); K(t + 2.0, 96); G(t + 2.5, 24)
    T(T_MID, t + 3.0, 106); G(t + 3.25, 26)

    # bar 6 - build that lands on the next crash
    t = 76.0
    K(t + 0.0, 104); K(t + 2.0, 104); K(t + 3.0, 108)
    fill_run(t + 0.0,
             [T_HI, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_FLOOR,
              T_LOW, T_LO, T_MID, T_MIDHI, T_HI, T_MIDHI, SNARE, SNARE],
             0.25, 84, 116)


def sec_roll():
    # bar 1 - arrival, then sudden half time
    t = 80.0
    CR(t + 0.0, 108)
    K(t + 0.0, 100)
    for i in range(4):
        P(t + i, 56 + (6 if i % 2 == 0 else 0))
    X(STICK, t + 1.0, 86); X(STICK, t + 3.0, 92); G(t + 3.75, 22)

    # bar 2 - creeping back in
    t = 84.0
    for i in range(4):
        P(t + i, 58)
    K(t + 0.0, 94); K(t + 2.0, 88)
    X(STICK, t + 1.0, 88)
    fill_run(t + 2.0,
             [SNARE, SNARE, SNARE, SNARE, T_HI, T_MIDHI, T_MID, T_LO],
             0.25, 54, 78)

    # bars 3-4 - the roll that swells and resolves
    roll(88.0, 94.0, SNARE, 46, 100, (4, 6, 8), curve=1.3)
    roll(94.0, 96.0, SNARE, 100, 120, (8,), curve=1.0, dur=0.045)
    K(94.0, 96)
    K(95.0, 106)
    K(95.5, 110)


def sec_fast():
    # ---- bars 1-4 (96-112): ride cymbal and a talking snare
    ride_bars = [
        ([(0.0, 100), (2.5, 84)],
         [(1.0, 100), (3.0, 104)],
         [(0.75, 26), (2.75, 30)]),
        ([(0.0, 102), (1.5, 80), (3.5, 78)],
         [(1.0, 98), (3.0, 102)],
         [(2.25, 24), (3.75, 26)]),
        ([(0.0, 104), (2.0, 88)],
         [(1.0, 102), (2.75, 60), (3.0, 104)],
         [(1.75, 26), (3.25, 22)]),
        ([(0.0, 100), (1.75, 74), (2.5, 86)],
         [(1.0, 100), (3.0, 102)],
         [(0.5, 22), (3.75, 28)]),
    ]
    for bar, (kc, sc, gc) in enumerate(ride_bars):
        t = 96.0 + 4.0 * bar
        base = 68 + (4 if bar % 2 else 0)
        for i in range(8):
            sw = 0.04 if i % 2 else 0.0
            R(t + 0.5 * i, base + (10 if i % 2 == 0 else 0), sw)
        P(t + 1.0, 58); P(t + 3.0, 62)
        for off, v in kc:
            K(t + off, v)
        for off, v in gc:
            G(t + off, v)
        for off, v in sc:
            S(t + off, v)

    # ---- bars 5-8 (112-128): single strokes around the kit
    kit = [
        [SNARE, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_FLOOR,
         T_FLOOR, T_LOW, T_LO, T_MID, T_MIDHI, T_HI, SNARE, SNARE],
        [T_FLOOR, T_FLOOR, T_LOW, T_LOW, T_LO, T_LO, T_MID, T_MID,
         T_MIDHI, T_MIDHI, T_HI, T_HI, SNARE, SNARE, SNARE, SNARE],
        [SNARE, SNARE, T_HI, SNARE, T_MIDHI, T_MIDHI, SNARE, SNARE,
         T_MID, T_MID, T_LO, T_LO, T_LOW, T_FLOOR, T_LOW, SNARE],
        [SNARE, T_HI, SNARE, T_MIDHI, SNARE, T_MID, SNARE, T_LO,
         SNARE, T_LOW, SNARE, T_FLOOR, T_LOW, T_LO, T_MID, SNARE],
    ]
    for bar, pat in enumerate(kit):
        t = 112.0 + 4.0 * bar
        strokes(t, pat, vacc=104, vnorm=56)
        K(t + 0.0, 100)
        K(t + 2.0, 92)
        P(t + 1.0, 56)
        P(t + 3.0, 58)

    # ---- bars 9-10 (128-136): motif on the toms with the ride
    for bar in range(2):
        t = 128.0 + 4.0 * bar
        for i in range(8):
            R(t + 0.5 * i, 68 + (10 if i % 2 == 0 else 0),
              0.04 if i % 2 else 0.0)
        K(t + 0.0, 102); K(t + 2.5, 88)
        T(T_HI, t + 1.0, 100); G(t + 1.75, 26)
        if bar == 0:
            T(T_MID, t + 3.0, 104); G(t + 3.5, 24)
        else:
            T(T_MID, t + 2.5, 96)
            fill_run(t + 2.75, [T_MID, T_LO, T_LOW, T_FLOOR, T_LOW, SNARE],
                     0.25, 90, 112)

    # ---- bar 11 (136-140): doubled hand work
    t = 136.0
    seq = [SNARE, SNARE, T_HI, T_HI, T_MIDHI, T_MIDHI, T_MID, T_MID,
           T_LO, T_LO, T_LOW, T_LOW, T_FLOOR, T_FLOOR, SNARE, SNARE]
    strokes(t, seq, vacc=100, vnorm=70,
            acc=(0, 2, 4, 6, 8, 10, 12, 14))
    K(t + 0.0, 102); K(t + 2.0, 98)
    P(t + 1.0, 56); P(t + 3.0, 58)

    # ---- bar 12 (140-144): the fill out of the section
    t = 140.0
    K(t + 0.0, 100); K(t + 2.0, 104)
    fill_run(t,
             [SNARE, SNARE, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR],
             0.25, 80, 98)
    fill_run(t + 2.0,
             [T_FLOOR, T_LOW, T_LO, T_MID, T_MIDHI, T_HI, SNARE, SNARE],
             0.25, 98, 118)


def sec_contrast():
    # bar 1 - crash, then air
    t = 144.0
    CR(t + 0.0, 98, 2.2)
    K(t + 0.0, 96)
    for i in range(4):
        P(t + i, 52 + (6 if i % 2 == 0 else 0))
    X(STICK, t + 1.0, 84)
    X(STICK, t + 3.0, 88)

    # bar 2 - cowbell answers
    t = 148.0
    for i in range(4):
        P(t + i, 52)
    K(t + 0.0, 90)
    X(STICK, t + 1.0, 82); X(STICK, t + 3.0, 86)
    X(COWBELL, t + 2.0, 70); X(COWBELL, t + 2.5, 60)
    G(t + 3.75, 20)

    # bar 3 - congas and bongos for colour
    t = 152.0
    for i in range(4):
        P(t + i, 54)
    K(t + 0.0, 92); K(t + 2.5, 74)
    X(BONGO_HI, t + 1.0, 78); X(BONGO_LO, t + 1.5, 68)
    X(CONGA_HI, t + 3.0, 80); X(CONGA_LO, t + 3.5, 70)

    # bar 4 - waking up
    t = 156.0
    for i in range(4):
        P(t + i, 56)
    K(t + 0.0, 94); K(t + 2.0, 88)
    for i in range(8):
        v = 40 + 14 * i
        hit(t + 0.5 * i, SNARE, v, 0.06, 'ghost' if v < 70 else 'norm')
    X(COWBELL, t + 2.0, 72)

    # bar 5 - sixteen notes, growing
    t = 160.0
    K(t + 0.0, 100); K(t + 2.0, 96)
    P(t + 1.0, 58); P(t + 3.0, 60)
    for i in range(16):
        v = 52 + i * 3.4
        hit(t + 0.25 * i, SNARE, v, 0.06, 'norm' if v < 92 else 'acc')

    # bar 6 - fill into the reprise
    t = 164.0
    K(t + 0.0, 104); K(t + 2.0, 106)
    fill_run(t,
             [T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_LOW, T_LO,
              T_MID, T_MIDHI, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR],
             0.25, 90, 118)


def sec_finale():
    # ---- bars 1-4 (168-184): the motif at full voice
    for bar in range(4):
        t = 168.0 + 4.0 * bar
        if bar == 3:
            play_bar(t, [(0.0, 104), (1.0, 72)], [(1.0, 100)], [(0.75, 26)],
                     hat_sub=0.5, hat_base=64,
                     hat_skip=(2.0, 2.5, 3.0, 3.5))
            fill_run(t + 2.0,
                     [SNARE, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_LOW],
                     0.25, 92, 116)
            continue
        kc = KICK_CELLS[(bar * 5 + 2) % len(KICK_CELLS)]
        sc = SNARE_CELLS[(bar * 3 + 1) % len(SNARE_CELLS)]
        gc = GHOST_CELLS[(bar * 5 + 3) % len(GHOST_CELLS)]
        kc, sc, gc = mutate(kc, sc, gc)
        crash = [(0.0, 106)] if bar % 2 == 0 else ()
        skip = (0.0,) if crash else ()
        play_bar(t, kc, sc, gc, vscale=1.03, gscale=1.0, hat_sub=0.5,
                 hat_base=64, crash=crash, hat_skip=skip,
                 pedal=[(2.0, 62)])

    # ---- bars 5-8 (184-200): call and response
    t = 184.0
    play_bar(t, KICK_CELLS[0], SNARE_CELLS[1], GHOST_CELLS[2],
             vscale=1.05, hat_base=64, crash=[(0.0, 104)], hat_skip=(0.0,))

    t = 188.0
    K(t + 0.0, 104); K(t + 2.0, 100)
    fill_run(t,
             [SNARE, SNARE, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR,
              T_FLOOR, T_LOW, T_LO, T_MID, T_MIDHI, T_HI, SNARE, SNARE],
             0.25, 88, 110)

    t = 192.0
    play_bar(t, KICK_CELLS[3], SNARE_CELLS[2], GHOST_CELLS[4],
             vscale=1.05, hat_base=64)

    t = 196.0
    K(t + 0.0, 106); K(t + 1.5, 96); K(t + 2.0, 104)
    fill_run(t,
             [T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_LOW, T_LO,
              T_MID, T_MIDHI, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR],
             0.25, 90, 112)

    # ---- bars 9-12 (200-216): denser call and response
    t = 200.0
    play_bar(t, KICK_CELLS[4], SNARE_CELLS[0], GHOST_CELLS[1],
             vscale=1.06, hat_base=64, hat_note=HAT,
             crash=[(0.0, 106)], hat_skip=(0.0,))

    t = 204.0
    seq = [SNARE, SNARE, T_HI, T_HI, T_MIDHI, T_MIDHI, T_MID, T_MID,
           T_LO, T_LO, T_LOW, T_LOW, T_FLOOR, T_FLOOR, T_LOW, SNARE]
    strokes(t, seq, vacc=106, vnorm=72, acc=(0, 2, 4, 6, 8, 10, 12, 14))
    K(t + 0.0, 104); K(t + 2.0, 102)

    t = 208.0
    play_bar(t, KICK_CELLS[6], SNARE_CELLS[4], GHOST_CELLS[3],
             vscale=1.06, hat_base=64, pedal=[(3.5, 58)])

    t = 212.0
    K(t + 0.0, 106); K(t + 2.0, 106); K(t + 3.5, 100)
    fill_run(t,
             [SNARE, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_LOW,
              T_LO, T_MID, T_MIDHI, T_HI, SNARE, T_HI, SNARE, SNARE],
             0.25, 96, 118)

    # ---- bars 13-16 (216-232): the build
    t = 216.0
    roll(t, t + 4.0, SNARE, 56, 78, (4,), curve=1.0)
    K(t + 0.0, 100); K(t + 2.0, 96)

    t = 220.0
    roll(t, t + 4.0, SNARE, 74, 94, (6,), curve=1.0)
    K(t + 0.0, 102); K(t + 2.0, 100)
    P(t + 1.0, 56); P(t + 3.0, 58)

    t = 224.0
    roll(t, t + 4.0, SNARE, 90, 108, (8,), curve=1.0, dur=0.045)
    K(t + 0.0, 104); K(t + 2.0, 104)

    t = 228.0
    seq = ([T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR] * 5 + [T_LOW, T_LO])
    fill_run(t, seq, 0.125, 104, 118, dur=0.05)
    K(t + 0.0, 106)

    # ---- bar 17 (232-236): final fill and the landing
    t = 232.0
    K(t + 0.0, 104); K(t + 2.0, 108)
    fill_run(t,
             [T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR, T_LOW, T_LO,
              T_MID, T_MIDHI, T_HI, T_MIDHI, T_MID, T_LO, T_LOW, T_FLOOR],
             0.25, 96, 120)

    CR(END_BEAT, 116, 6.0)
    K(END_BEAT, 118, 0.5)
    S(END_BEAT, 112, 0.5)


# ======================================================================
# playability guard: never more than two hands and two feet at once
# ======================================================================
def enforce_playability():
    idx = sorted(range(len(EV)), key=lambda i: (EV[i][0], EV[i][1]))
    clusters = []
    cur = []
    for i in idx:
        if cur and EV[i][0] - EV[cur[-1]][0] > 0.045:
            clusters.append(cur)
            cur = []
        cur.append(i)
    if cur:
        clusters.append(cur)

    drop = set()
    for cl in clusters:
        hands = [i for i in cl if EV[i][1] in HAND_NOTES]
        if len(hands) > 2:
            hands.sort(key=lambda i: -EV[i][2])
            drop.update(hands[2:])
        feet = [i for i in cl if EV[i][1] in FOOT_NOTES]
        kicks = [i for i in feet if EV[i][1] in (KICK, KICK2)]
        pedal = [i for i in feet if EV[i][1] == PHT]
        if len(kicks) > 1:
            kicks.sort(key=lambda i: -EV[i][2])
            drop.update(kicks[1:])
        if len(pedal) > 1:
            pedal.sort(key=lambda i: -EV[i][2])
            drop.update(pedal[1:])

    return [e for i, e in enumerate(EV) if i not in drop]


# ======================================================================
# tempo map: the pulse surges and settles with the music
# ======================================================================
TEMPO_MAP = [
    (0.0, 106), (16.0, 114), (32.0, 119), (48.0, 122),
    (80.0, 117), (88.0, 125), (96.0, 131), (128.0, 129),
    (144.0, 110), (160.0, 114), (168.0, 121), (216.0, 126),
    (232.0, 121),
]


def seconds_at(beat, tmap):
    s = 0.0
    for i, (pos, bpm) in enumerate(tmap):
        if beat <= pos:
            break
        nxt = tmap[i + 1][0] if i + 1 < len(tmap) else beat
        end = min(beat, nxt)
        s += (end - pos) * 60.0 / bpm
    return s


def bpm_at(beat, tmap):
    bpm = tmap[0][1]
    for pos, val in tmap:
        if beat >= pos:
            bpm = val
        else:
            break
    return bpm


# ======================================================================
# performance humanisation
# ======================================================================
JITTER_SIGMA = {'acc': 3.0, 'norm': 6.0, 'ghost': 9.5, 'foot': 5.0}


def humanise(beat, kind, tmap):
    bpm = bpm_at(beat, tmap)
    ticks_per_ms = bpm / 60.0 * TPB / 1000.0

    # slow expressive drift of the whole phrase (push / pull)
    ms = 5.0 * math.sin(beat / 21.0 + 0.7) + 3.2 * math.sin(beat / 7.3 + 2.1)
    # section rubato: hold back into the contrast, push the finale
    if 144.0 <= beat < 168.0:
        ms -= 4.0 * math.sin((beat - 144.0) / 24.0 * math.pi)
    elif beat >= 216.0:
        ms += 3.0 * math.sin((beat - 216.0) / 20.0 * math.pi)
    # individual hand placement
    ms += rng.gauss(0.0, JITTER_SIGMA[kind])
    if kind == 'ghost':
        ms -= 2.0                      # ghosts tend to sit a hair early
    if kind == 'acc':
        ms += 1.0                      # accents sit into the beat
    return ms * ticks_per_ms


def realise(events, tmap):
    out = []
    for beat, note, vel, dur, kind in events:
        tick = int(round(beat * TPB + humanise(beat, kind, tmap)))
        if tick < 0:
            tick = 0
        if kind == 'ghost':
            v = vel + rng.gauss(0.0, 2.5)
        elif kind == 'acc':
            v = vel + rng.gauss(0.0, 3.5)
        else:
            v = vel + rng.gauss(0.0, 4.5)
        v = max(1, min(126, int(round(v))))
        d = max(24, int(round(dur * TPB)))
        out.append((tick, note, v, d))
    return out


# ======================================================================
# MIDI file
# ======================================================================
def write_midi(path, events, tmap):
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    trk = MidiTrack()
    mid.tracks.append(trk)

    items = []
    items.append((0, 0, MetaMessage('track_name', name='Drum Solo')))
    items.append((0, 0, MetaMessage('time_signature', numerator=4,
                                    denominator=4, clocks_per_click=24,
                                    notated_32nd_notes_per_beat=8)))
    for pos, bpm in tmap:
        tick = int(round(pos * TPB))
        items.append((tick, 0, MetaMessage('set_tempo',
                                           tempo=bpm2tempo(bpm))))
    for tick, note, vel, dur in events:
        items.append((tick, 2, Message('note_on', channel=CH,
                                       note=note, velocity=vel)))
        items.append((tick + dur, 1, Message('note_off', channel=CH,
                                             note=note, velocity=0)))

    items.sort(key=lambda x: (x[0], x[1]))

    last = 0
    for tick, _pri, msg in items:
        if tick < last:
            tick = last
        msg.time = tick - last
        last = tick
        trk.append(msg)

    mid.save(path)


# ======================================================================
# main
# ======================================================================
def main():
    # 1. compose the whole solo in beats
    sec_intro()
    sec_groove_a()
    sec_toms()
    sec_roll()
    sec_fast()
    sec_contrast()
    sec_finale()

    # 2. make sure one drummer can play it
    events = enforce_playability()

    # 3. scale the tempo map so the last downbeat lands where we want it
    raw = seconds_at(END_BEAT, TEMPO_MAP)
    k = raw / TARGET_END
    tmap = [(pos, bpm * k) for pos, bpm in TEMPO_MAP]

    # 4. humanise timing and velocity
    events = realise(events, tmap)

    # 5. write it out
    write_midi('solo.mid', events, tmap)

    total = seconds_at(END_BEAT + 6.0, tmap)
    print('solo.mid written: %d notes, %.1f s, %.1f - %.1f BPM'
          % (len(events), total,
             min(b for _, b in tmap), max(b for _, b in tmap)))


if __name__ == '__main__':
    main()
