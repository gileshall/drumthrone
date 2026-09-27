#!/usr/bin/env python3
"""
drum_solo.py - composes and performs a two-minute drum solo and writes it to
solo.mid (General MIDI, channel 10).

Motifs
  A  "the call": three strokes in a 3+3+2 sixteenth shape, stated on the toms
     and later filled in, displaced, stretched over the barline, played by
     the feet, and hit as cymbal shots.
  B  "the groove": hi-hat funk with a tresillo kick, backbeat and ghost notes.
  C  "the flow": six-stroke rolls and sextuplet runs that travel the kit.
  D  "the shots": quarter-note-triplet unison hits over the 4/4 pulse.

Each note is written for a specific limb (RH, LH, RF, LF). A final pass
keeps every limb physically possible, so there are never more than two
hands and two feet at once.

Timing comes from a tempo map that surges in fills, settles after landings
and broadens into the last hit, plus per-note human timing (ghosts looser
than accents, laid-back backbeats, flams and a light swing in the Latin
section).

A fixed seed makes every run write the same file.
"""

import bisect
import math
import random

import mido

OUT_FILE = "solo.mid"
SEED = 1964
TPB = 960
CHANNEL = 9                  # MIDI channel 10
SEG = 0.5                    # tempo-map resolution (beats)
SEG_TICKS = int(SEG * TPB)
FINAL_BAR = 60
FINAL_BEAT = FINAL_BAR * 4.0
FINAL_TIME = 117.8           # seconds at which the last hit lands
TAIL = 2.2                   # let it ring

# General MIDI percussion
KICK = 36
XSTICK, SNARE = 37, 38
HHC, HHP, HHO = 42, 44, 46
F2, F1, T4, T3, T2, T1 = 41, 43, 45, 47, 48, 50
CR1, RIDE, CHINA, BELL, SPLASH, COWBELL, CR2 = 49, 51, 52, 53, 55, 56, 57
TOMS = [T1, T2, T3, T4, F1, F2]
CYMBALS = (CR1, CR2, CHINA, SPLASH, RIDE, BELL)
RINGING = CYMBALS + (HHO,)

R = random.Random(SEED)
NOTES = []


class Note:
    __slots__ = ("beat", "limb", "pitch", "dyn", "ms", "prio", "anchor",
                 "dens", "off", "t", "vel", "dur", "dropped", "final",
                 "on_tick", "off_tick")

    def __init__(self, beat, limb, pitch, dyn, ms=0.0, prio=1):
        self.beat = beat
        self.limb = limb
        self.pitch = pitch
        self.dyn = dyn
        self.ms = ms
        self.prio = prio
        self.anchor = None
        self.dens = 1.0
        self.off = 0.0
        self.t = 0.0
        self.vel = 64
        self.dur = 0.05
        self.dropped = False
        self.final = False
        self.on_tick = 0
        self.off_tick = 0


# --------------------------------------------------------------------------
# vocabulary
# --------------------------------------------------------------------------
def add(beat, limb, pitch, dyn, ms=0.0, prio=1):
    n = Note(float(beat), limb, pitch, max(0.04, min(1.0, dyn)), ms, prio)
    NOTES.append(n)
    return n


def other(h):
    return "LH" if h == "RH" else "RH"


def bb(bar, beat=0.0):
    return bar * 4.0 + beat


def jit(a):
    return R.uniform(-a, a)


def kick(b, d=0.7, foot="RF", prio=2):
    return add(b, foot, KICK, d, prio=prio)


def hfoot(b, d=0.4):
    return add(b, "LF", HHP, d)


def cym(b, d=0.95, hand="RH", pitch=CR1, with_kick=True, kd=None):
    add(b, hand, pitch, d, prio=3)
    if with_kick:
        kick(b, d * 0.92 if kd is None else kd, prio=3)


def flam(b, hand, pitch, d, grace=None, prio=2):
    main = add(b, hand, pitch, d, prio=prio)
    g = add(b, other(hand), pitch if grace is None else grace,
            0.1 + 0.27 * d, ms=-R.uniform(17.0, 28.0), prio=0)
    g.anchor = main
    return main


LIMB = {"R": "RH", "L": "LH", "K": "RF", "k": "LF", "H": "LF"}


def seq(start, step, sticking, pitches, dyns, prio=1):
    for i, ch in enumerate(sticking):
        if ch not in LIMB:
            continue
        d = dyns(i) if callable(dyns) else dyns[i]
        if ch in "Kk":
            p = KICK
        elif ch == "H":
            p = HHP
        else:
            p = pitches(i) if callable(pitches) else pitches[i]
        if p is None or d is None:
            continue
        pr = max(prio, 3) if p in CYMBALS else prio
        add(start + i * step, LIMB[ch], p, d, prio=pr)


def roll(start, end, rate, pitch, d0, d1, kind="double", lead="R", curve=1.0, prio=1):
    n = int(round((end - start) * rate))
    hands = ("R", "L") if lead == "R" else ("L", "R")
    for i in range(n):
        f = i / max(1, n - 1)
        d = d0 + (d1 - d0) * (f ** curve)
        if kind == "double":
            h = hands[(i // 2) % 2]
            if i % 2:
                d *= 0.9
        else:
            h = hands[i % 2]
        p = pitch(i, f, h) if callable(pitch) else pitch
        add(start + i / rate, LIMB[h], p, d + jit(0.02), prio=prio)


def dbass(start, end, d=0.5, rate=4, acc=None, cresc=0.0, lead="RF"):
    n = int(round((end - start) * rate))
    feet = (lead, "LF" if lead == "RF" else "RF")
    for i in range(n):
        f = i / max(1, n - 1)
        dd = d + cresc * f + (acc(i) if acc else 0.0) + jit(0.025)
        kick(start + i / rate, dd, foot=feet[i % 2])


def six_stroke(t0, r_acc, l_acc, acc, soft, inner=SNARE, step=1.0 / 6.0):
    add(t0, "RH", r_acc, acc, prio=3 if r_acc in CYMBALS else 1)
    add(t0 + step, "LH", inner, soft + 0.04)
    add(t0 + 2 * step, "LH", inner, soft)
    add(t0 + 3 * step, "RH", inner, soft + 0.05)
    add(t0 + 4 * step, "RH", inner, soft)
    add(t0 + 5 * step, "LH", l_acc, acc * 0.95)


def groove(bar, kicks, ghosts, back=(1.0, 3.0), back_d=0.86, open_at=(), crash=None,
           hat_extra=(), stop=4.0, energy=1.0, hat=HHC):
    b = bb(bar)
    hats = sorted(set([i * 0.5 for i in range(8)] + list(hat_extra)))
    for p in hats:
        if p >= stop:
            continue
        if crash is not None and p == 0.0:
            cym(b, 0.9 * energy, "RH", crash, with_kick=False)
            continue
        if abs(p - round(p)) < 1e-9:
            d = 0.60
        elif abs(p * 2 - round(p * 2)) < 1e-9:
            d = 0.44
        else:
            d = 0.30
        pitch = HHO if p in open_at else hat
        if pitch == HHO:
            d += 0.10
        add(b + p, "RH", pitch, d * energy + jit(0.03))
    for p in back:
        if p < stop:
            add(b + p, "LH", SNARE, back_d * energy + jit(0.02), prio=2)
    for p, d in ghosts:
        if p < stop:
            add(b + p, "LH", SNARE, d + jit(0.02))
    for p, d in kicks:
        if p < stop:
            kick(b + p, d * energy + jit(0.03))


def linear_groove(bar, kicks, crash=None, r_voice=None, open_pos=(), skip=(), energy=1.0):
    b = bb(bar)
    st = "RLRRLRLLRLRRLRLL"
    for i, ch in enumerate(st):
        if i in skip:
            continue
        p = i * 0.25
        if ch == "R":
            if i == 0 and crash is not None:
                cym(b, 0.9 * energy, "RH", crash, with_kick=False)
                continue
            d = 0.58 if i % 4 == 0 else (0.42 if i % 2 == 0 else 0.30)
            pitch = HHC
            if i in open_pos:
                pitch = HHO
                d += 0.12
            if r_voice and i in r_voice:
                pitch, d = r_voice[i]
            add(b + p, "RH", pitch, d * energy + jit(0.03))
        else:
            if i in (4, 12):
                add(b + p, "LH", SNARE, 0.86 * energy + jit(0.02), prio=2)
            else:
                add(b + p, "LH", SNARE, 0.13 + jit(0.03))
    for p, d in kicks:
        kick(b + p, d * energy + jit(0.03))


CASC_A = (0.0, 1.0, 2.0, 2.5, 3.5)
CASC_B = (0.0, 1.0, 1.5, 2.5, 3.5)


def color_rh(bar, pitch, pattern, base=0.46, skip=()):
    b = bb(bar)
    for p in pattern:
        if p in skip:
            continue
        on = abs(p - round(p)) < 1e-9
        add(b + p, "RH", pitch, base + (0.10 if on else 0.0) + jit(0.03))


# --------------------------------------------------------------------------
# the solo
# --------------------------------------------------------------------------
def part_opening():
    # bar 0: motif A stated plainly, with space around it
    b = bb(0)
    add(b, "RH", T1, 0.80); kick(b, 0.60)
    add(b + 0.75, "LH", T3, 0.76)
    add(b + 1.5, "RH", F2, 0.88); kick(b + 1.5, 0.68)
    hfoot(b + 1.0, 0.36); hfoot(b + 3.0, 0.38)
    add(b + 3.5, "LH", SNARE, 0.12); add(b + 3.75, "LH", SNARE, 0.18)

    # bar 1: echo with the contour inverted, then a short answer
    b = bb(1)
    add(b, "RH", F2, 0.78); kick(b, 0.58)
    add(b + 0.75, "LH", T3, 0.70)
    add(b + 1.5, "RH", T1, 0.74)
    hfoot(b + 1.0, 0.34)
    add(b + 2.25, "LH", SNARE, 0.14); add(b + 2.5, "LH", SNARE, 0.19)
    add(b + 2.75, "RH", SNARE, 0.80, prio=2); kick(b + 2.75, 0.60)
    hfoot(b + 3.0, 0.36)
    add(b + 3.25, "LH", SNARE, 0.20)
    add(b + 3.5, "RH", T2, 0.55)
    add(b + 3.75, "LH", T3, 0.62)

    # bar 2: motif A filled in (RLL RLL RL), crescendo down the toms
    b = bb(2)
    st = "RLLRLLRLRLLRLLRL"
    accp = {0: T1, 3: T2, 6: T3, 8: T4, 11: F1, 14: SNARE}
    for i, ch in enumerate(st):
        f = i / 15.0
        if ch == "R":
            add(b + i * 0.25, "RH", accp[i], 0.56 + 0.30 * f)
        else:
            add(b + i * 0.25, "LH", SNARE, 0.11 + 0.17 * f + jit(0.02))
    for p, d in ((0.0, 0.55), (1.5, 0.60), (2.0, 0.64), (3.5, 0.78)):
        kick(b + p, d)
    hfoot(b + 1.0, 0.36); hfoot(b + 3.0, 0.40)

    # bar 3: snare swell that resolves around the toms
    b = bb(3)
    roll(b, b + 2.75, 8, SNARE, 0.10, 0.84, "double", curve=1.7)
    for p, d in ((0.0, 0.34), (1.0, 0.38), (2.0, 0.50)):
        kick(b + p, d)
    hfoot(b + 1.0, 0.30)
    flam(b + 3.0, "RH", SNARE, 0.90); kick(b + 3.0, 0.70)
    add(b + 3.25, "LH", T2, 0.72)
    add(b + 3.5, "RH", F1, 0.86); kick(b + 3.5, 0.75)
    add(b + 3.75, "LH", F2, 0.80)

    # bar 4: motif A as big cymbal statement, then thundering toms
    b = bb(4)
    cym(b, 0.96, "RH", CR1)
    add(b + 0.25, "LH", SNARE, 0.20); add(b + 0.5, "LH", SNARE, 0.26)
    add(b + 0.75, "LH", SNARE, 0.92, prio=2); kick(b + 0.75, 0.84)
    add(b + 1.0, "LH", SNARE, 0.22); add(b + 1.25, "LH", SNARE, 0.28)
    cym(b + 1.5, 0.95, "RH", CR2)
    add(b + 1.75, "LH", SNARE, 0.34)
    seq(b + 2.0, 0.25, "RLLRLLRL", [T1, T1, T1, T3, T3, T3, F2, F2],
        [0.84, 0.42, 0.46, 0.88, 0.48, 0.52, 0.96, 0.60])
    for p, d in ((2.0, 0.78), (2.75, 0.80), (3.5, 0.90)):
        kick(b + p, d)

    # bar 5: sudden whisper - the motif in ghost notes
    b = bb(5)
    for i, ch in enumerate("RLLRLLRL"):
        if ch == "R":
            add(b + i * 0.25, "RH", SNARE, 0.34 + 0.05 * (i // 3))
        else:
            add(b + i * 0.25, "LH", SNARE, 0.09 + 0.012 * i + jit(0.015))
    kick(b, 0.34); kick(b + 1.5, 0.36); kick(b + 2.0, 0.36)
    for p in (1.0, 2.0, 3.0):
        hfoot(b + p, 0.30)
    add(b + 2.75, "RH", F1, 0.34)
    add(b + 3.5, "RH", F2, 0.42); kick(b + 3.5, 0.40)
    add(b + 3.75, "LH", SNARE, 0.22)

    # bar 6: motif displaced by an eighth against a steady hi-hat foot
    b = bb(6)
    for p in (0.0, 1.0, 2.0, 3.0):
        hfoot(b + p, 0.34)
    accp = {0: T1, 3: T3, 6: F2}
    for i, ch in enumerate("RLLRLLRL"):
        t = b + 0.5 + i * 0.25
        if ch == "R":
            add(t, "RH", accp[i], 0.70 + 0.04 * (i // 3))
        else:
            add(t, "LH", SNARE, 0.13 + 0.015 * i + jit(0.02))
    kick(b + 0.5, 0.55); kick(b + 2.0, 0.60); kick(b + 2.5, 0.48)
    flam(b + 2.75, "RH", SNARE, 0.82)
    add(b + 3.25, "LH", SNARE, 0.20)
    add(b + 3.5, "RH", T2, 0.62); kick(b + 3.5, 0.55)
    add(b + 3.75, "LH", T2, 0.58)

    # bar 7: descending singles with 3-over-4 accents into the groove
    b = bb(7)
    add(b, "RH", F2, 0.70); kick(b, 0.66)
    add(b + 0.5, "LH", SNARE, 0.62)
    kick(b + 0.75, 0.56)
    route = [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2]
    for i in range(12):
        f = i / 11.0
        t = b + 1.0 + i * 0.25
        acc = (i % 3 == 0)
        add(t, "RH" if i % 2 == 0 else "LH", route[i],
            (0.62 + 0.30 * f) if acc else (0.34 + 0.25 * f))
        if acc:
            kick(t, 0.55 + 0.30 * f)


def part_groove():
    groove(8, kicks=[(0, 0.80), (0.75, 0.60), (1.5, 0.66), (2.5, 0.60), (2.75, 0.50)],
           ghosts=[(1.75, 0.16), (2.25, 0.14), (3.25, 0.13), (3.75, 0.20)], crash=CR1)
    groove(9, kicks=[(0, 0.76), (0.75, 0.60), (1.5, 0.66), (2.5, 0.60), (3.25, 0.50)],
           ghosts=[(0.75, 0.15), (1.75, 0.17), (2.25, 0.13), (2.75, 0.19), (3.75, 0.16)],
           open_at=(3.5,))
    groove(10, kicks=[(0, 0.76), (0.75, 0.58), (1.5, 0.64), (2.25, 0.55), (2.75, 0.62), (3.5, 0.50)],
           ghosts=[(0.25, 0.14), (1.25, 0.13), (1.75, 0.16), (2.625, 0.17), (2.75, 0.21), (3.75, 0.18)],
           open_at=(1.5,), hat_extra=(3.75,))
    # bar 11: groove, then motif A breaks through on the toms (backbeat kept)
    groove(11, kicks=[(0, 0.76), (0.75, 0.60), (1.5, 0.66)],
           ghosts=[(0.25, 0.13), (1.75, 0.18)], back=(1.0,), stop=2.0)
    b = bb(11)
    seq(b + 2.0, 0.25, "RLLRLLRL", [T1, SNARE, SNARE, T3, SNARE, SNARE, F2, SNARE],
        [0.80, 0.20, 0.24, 0.84, 0.72, 0.26, 0.90, 0.42])
    kick(b + 2.0, 0.72); kick(b + 2.75, 0.74); kick(b + 3.5, 0.80)
    # bars 12-13: linear paradiddle groove
    linear_groove(12, kicks=[(0, 0.82), (0.75, 0.60), (1.5, 0.64), (2.5, 0.60), (3.25, 0.52)],
                  crash=CR2)
    linear_groove(13, kicks=[(0, 0.78), (0.75, 0.60), (1.5, 0.64), (2.25, 0.50), (3.5, 0.64), (3.75, 0.58)],
                  r_voice={10: (T2, 0.56), 11: (T3, 0.52)}, open_pos=(13,), skip=(14, 15))
    # bar 14: open-hat drive, ghost density rising
    b = bb(14)
    for k in range(8):
        f = k / 7.0
        if k % 2 == 0:
            add(b + k * 0.5, "RH", HHC, 0.56 + 0.10 * f + jit(0.03))
        else:
            add(b + k * 0.5, "RH", HHO, 0.52 + 0.14 * f + jit(0.03))
    add(b + 1.0, "LH", SNARE, 0.86, prio=2); add(b + 3.0, "LH", SNARE, 0.92, prio=2)
    for p, d in ((0.25, 0.13), (0.75, 0.15), (1.75, 0.17), (2.25, 0.20), (2.5, 0.22),
                 (2.75, 0.26), (3.25, 0.28), (3.5, 0.32), (3.75, 0.36)):
        add(b + p, "LH", SNARE, d + jit(0.02))
    for p, d in ((0, 0.80), (0.75, 0.60), (1.5, 0.68), (2.0, 0.60), (2.75, 0.64), (3.5, 0.66)):
        kick(b + p, d)
    # bar 15: fill - RLL sextuplets with accents walking down
    b = bb(15)
    add(b, "RH", HHC, 0.62); kick(b, 0.78)
    add(b + 0.25, "LH", SNARE, 0.18)
    add(b + 0.5, "RH", HHO, 0.62)
    kick(b + 0.75, 0.60)
    add(b + 1.0, "LH", SNARE, 0.88, prio=2); hfoot(b + 1.0, 0.45)
    add(b + 1.25, "RH", SNARE, 0.30); add(b + 1.5, "LH", SNARE, 0.36)
    add(b + 1.75, "RH", SNARE, 0.44)
    accs = [T1, T3, F1, F2]
    for i in range(12):
        f = i / 11.0
        t = b + 2.0 + i / 6.0
        if i % 3 == 0:
            add(t, "RH", accs[i // 3], 0.66 + 0.30 * f)
            kick(t, 0.62 + 0.30 * f)
        else:
            add(t, "LH", SNARE, 0.28 + 0.22 * f + jit(0.02))


def part_flow():
    # bar 16: six-stroke rolls walking down the toms (motif C)
    b = bb(16)
    cym(b, 0.94, "RH", CR1)
    add(b + 0.5, "LH", SNARE, 0.15); add(b + 0.75, "LH", SNARE, 0.20)
    for p in (1.5, 2.5, 3.5):
        hfoot(b + p, 0.34)
    for k, (ra, la) in enumerate(((T1, T2), (T3, T4), (F1, F2))):
        f = k / 2.0
        six_stroke(b + 1.0 + k, ra, la, 0.68 + 0.14 * f, 0.20 + 0.07 * f)
        kick(b + 1.0 + k, 0.50 + 0.12 * f)

    # bar 17: motif A filled across the whole bar
    b = bb(17)
    accp = {0: CR2, 3: T1, 6: T2, 8: SNARE, 11: T4, 14: F2}
    for i, ch in enumerate("RLLRLLRLRLLRLLRL"):
        f = i / 15.0
        t = b + i * 0.25
        if ch == "R":
            if accp[i] == CR2:
                cym(t, 0.90, "RH", CR2, with_kick=False)
            else:
                add(t, "RH", accp[i], 0.72 + 0.22 * f)
        else:
            add(t, "LH", SNARE, 0.18 + 0.10 * f + (0.12 if i in (7, 15) else 0.0) + jit(0.02))
    for p in (0.0, 0.75, 1.5, 2.75, 3.5):
        kick(b + p, 0.64 + 0.18 * p / 3.5)
    hfoot(b + 1.0, 0.34); hfoot(b + 3.0, 0.36)

    # bar 18: double-stroke swell, then flam accents down the toms
    b = bb(18)
    roll(b, b + 2.0, 8, SNARE, 0.18, 0.84, "double", curve=1.3)
    kick(b, 0.40); kick(b + 1.0, 0.46)
    hfoot(b + 0.5, 0.28); hfoot(b + 1.5, 0.30)
    flam(b + 2.0, "LH", SNARE, 0.92); kick(b + 2.0, 0.78)
    flam(b + 2.5, "RH", T3, 0.86, grace=T2)
    flam(b + 3.0, "RH", F1, 0.90, grace=T3); kick(b + 3.0, 0.80)
    flam(b + 3.5, "RH", F2, 0.94, grace=F1); kick(b + 3.5, 0.84)

    # bar 19: two beats of groove, then sextuplets climbing up
    b = bb(19)
    for p, d in ((0.0, 0.60), (0.5, 0.44), (1.0, 0.58), (1.5, 0.46)):
        add(b + p, "RH", HHC, d + jit(0.03))
    add(b + 0.25, "LH", SNARE, 0.16); add(b + 0.75, "LH", SNARE, 0.18)
    add(b + 1.0, "LH", SNARE, 0.86, prio=2); add(b + 1.75, "LH", SNARE, 0.20)
    kick(b, 0.78); kick(b + 0.75, 0.60); kick(b + 1.5, 0.64)
    route = [F2, F2, F1, F1, T4, T4, T3, T3, T2, T2, T1, T1]
    for i in range(12):
        f = i / 11.0
        add(b + 2.0 + i / 6.0, "RH" if i % 2 == 0 else "LH", route[i],
            0.42 + 0.46 * f + (0.08 if i % 3 == 0 else 0.0))
    kick(b + 2.0, 0.60); kick(b + 3.0, 0.72)

    # bar 20: doubles travelling the toms, then motif A on the cymbals
    b = bb(20)
    rt = [T1, T2, T3, T4]
    for i in range(16):
        t = b + i / 8.0
        grp = i // 4
        if (i // 2) % 2 == 0:
            add(t, "RH", rt[grp], 0.58 + 0.06 * grp - (0.06 if i % 2 else 0.0))
        else:
            add(t, "LH", SNARE, 0.30 + 0.05 * grp - (0.04 if i % 2 else 0.0))
    for p, d in ((0.0, 0.70), (0.5, 0.55), (1.0, 0.62), (1.5, 0.66)):
        kick(b + p, d)
    seq(b + 2.0, 0.25, "RLLRLLRL", [CR1, SNARE, SNARE, T2, SNARE, SNARE, CR2, SNARE],
        [0.92, 0.24, 0.28, 0.82, 0.30, 0.34, 0.95, 0.50])
    for p, d in ((2.0, 0.86), (2.75, 0.82), (3.5, 0.90)):
        kick(b + p, d)

    # bar 21: pianissimo singles, accents every third note (3 against 4)
    b = bb(21)
    for i in range(16):
        f = i / 15.0
        acc = (i % 3 == 0)
        d = (0.28 + 0.30 * f) if acc else (0.08 + 0.12 * f)
        add(b + i * 0.25, "RH" if i % 2 == 0 else "LH", SNARE, d + jit(0.015))
    kick(b, 0.36); kick(b + 2.0, 0.40)
    for p in (1.0, 2.0, 3.0):
        hfoot(b + p, 0.30)

    # bar 22: the grouping continues over the barline, accents move to toms
    b = bb(22)
    accp = {2: T1, 5: T2, 8: T3, 11: T4, 14: F1}
    for i in range(16):
        f = i / 15.0
        h = "RH" if i % 2 == 0 else "LH"
        t = b + i * 0.25
        if i in accp:
            add(t, h, accp[i], 0.60 + 0.32 * f)
            kick(t, 0.50 + 0.35 * f)
        else:
            add(t, h, SNARE, 0.16 + 0.18 * f + jit(0.02))
    for q in range(4):
        hfoot(b + q, 0.34 + 0.04 * q)

    # bar 23: big fill - sextuplets, triplet flams, a short roll, land
    b = bb(23)
    route = [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2]
    for i in range(12):
        f = i / 11.0
        add(b + i / 6.0, "RH" if i % 2 == 0 else "LH", route[i],
            0.66 + 0.20 * f + (0.06 if i % 3 == 0 else 0.0))
    for p, d in ((0.0, 0.80), (0.5, 0.62), (1.0, 0.80), (1.5, 0.64)):
        kick(b + p, d)
    flam(b + 2.0, "RH", SNARE, 0.90); kick(b + 2.0, 0.80)
    flam(b + 2.0 + 1.0 / 3.0, "RH", T3, 0.86, grace=T2)
    flam(b + 2.0 + 2.0 / 3.0, "RH", F1, 0.90, grace=T4); kick(b + 2.0 + 2.0 / 3.0, 0.78)
    roll(b + 3.0, b + 3.75, 8, SNARE, 0.52, 0.90, "double", lead="L")
    kick(b + 3.0, 0.60)
    add(b + 3.75, "RH", F2, 0.96); kick(b + 3.75, 0.88)


def part_colors():
    # bar 24: land, then drop to a laid-back cascara on the ride bell
    b = bb(24)
    cym(b, 0.95, "RH", CR1)
    color_rh(24, BELL, CASC_A, skip=(0.0,))
    for p, pch, d in ((1.0, XSTICK, 0.52), (1.75, SNARE, 0.12), (2.75, XSTICK, 0.44),
                      (3.5, T4, 0.46), (3.75, T4, 0.40)):
        add(b + p, "LH", pch, d)
    kick(b + 1.5, 0.46); kick(b + 3.0, 0.50)
    hfoot(b + 1.0, 0.32); hfoot(b + 3.0, 0.32)

    b = bb(25)
    color_rh(25, BELL, CASC_B)
    for p, pch, d in ((0.75, SNARE, 0.12), (1.0, XSTICK, 0.52), (2.25, SNARE, 0.12),
                      (2.75, XSTICK, 0.45), (3.25, T3, 0.38), (3.5, T4, 0.50)):
        add(b + p, "LH", pch, d)
    kick(b, 0.50); kick(b + 1.5, 0.46); kick(b + 3.0, 0.50)
    hfoot(b + 1.0, 0.32); hfoot(b + 3.0, 0.32)

    # bar 26: cowbell takes over, left hand hums motif A on the toms
    b = bb(26)
    color_rh(26, COWBELL, CASC_A, base=0.40)
    add(b + 1.0, "LH", XSTICK, 0.50)
    add(b + 1.5, "LH", SNARE, 0.12)
    for p, pch, d in ((2.0, T2, 0.46), (2.75, T3, 0.52), (3.5, T4, 0.58), (3.75, T4, 0.36)):
        add(b + p, "LH", pch, d)
    kick(b, 0.50); kick(b + 1.5, 0.46); kick(b + 3.0, 0.52)
    hfoot(b + 1.0, 0.32); hfoot(b + 3.0, 0.32)

    # bar 27: motif on toms, ghost crescendo up to a splash
    b = bb(27)
    color_rh(27, COWBELL, CASC_B, base=0.42, skip=(3.5,))
    add(b + 3.5, "RH", SPLASH, 0.78, prio=3); kick(b + 3.5, 0.62)
    for p, pch, d in ((0.0, T2, 0.48), (0.75, T3, 0.54), (1.5, T4, 0.60), (2.25, SNARE, 0.20),
                      (2.5, SNARE, 0.26), (2.75, SNARE, 0.34), (3.0, SNARE, 0.44), (3.25, SNARE, 0.54)):
        add(b + p, "LH", pch, d)
    kick(b, 0.50); kick(b + 1.5, 0.50); kick(b + 3.0, 0.52)
    hfoot(b + 1.0, 0.32)

    # bar 28: cowbell in dotted eighths over a four-on-the-floor kick
    b = bb(28)
    for i in range(16):
        f = i / 15.0
        t = b + i * 0.25
        if i % 3 == 0:
            add(t, "RH", COWBELL, 0.40 + 0.30 * f + jit(0.02))
        else:
            add(t, "LH", SNARE, 0.10 + 0.14 * f + jit(0.02))
    for q in range(4):
        kick(b + q, 0.42 + 0.06 * q)
    for p in (0.5, 1.5, 2.5, 3.5):
        hfoot(b + p, 0.30)

    # bar 29: the grouping crosses the barline and walks onto the toms
    b = bb(29)
    accp = {2: (COWBELL, 0.60), 5: (COWBELL, 0.66), 8: (T3, 0.72), 11: (T4, 0.78), 14: (F2, 0.88)}
    for i in range(16):
        f = i / 15.0
        t = b + i * 0.25
        if i in accp:
            add(t, "RH", accp[i][0], accp[i][1])
        else:
            add(t, "LH", SNARE, 0.16 + 0.18 * f + jit(0.02))
    for p, d in ((0.0, 0.46), (1.0, 0.50), (2.0, 0.66), (2.75, 0.70), (3.5, 0.80)):
        kick(b + p, d)
    for q in range(4):
        hfoot(b + q, 0.32)

    # bar 30: melodic toms, then a floor-tom swell
    b = bb(30)
    mel = [("RH", T1, 0.70), ("LH", T1, 0.34), ("RH", T2, 0.50), ("LH", T3, 0.66),
           ("RH", T3, 0.36), ("LH", T4, 0.42), ("RH", F1, 0.76), ("LH", F1, 0.36)]
    for i, (h, p, d) in enumerate(mel):
        add(b + i * 0.25, h, p, d + jit(0.02))
    kick(b, 0.62); kick(b + 0.75, 0.58); kick(b + 1.5, 0.66)
    hfoot(b + 1.0, 0.34)
    for i in range(12):
        f = i / 11.0
        add(b + 2.0 + i / 6.0, "RH" if i % 2 == 0 else "LH", F2 if i % 2 == 0 else F1,
            0.26 + 0.62 * f ** 1.3)
    kick(b + 2.0, 0.42); kick(b + 3.0, 0.62); hfoot(b + 3.0, 0.36)

    # bar 31: hand-hand-foot triplets around the kit
    b = bb(31)
    pairs = [(T1, T2), (T2, T3), (T4, F1), (F1, F2)]
    for beat in range(4):
        rt, lt = pairs[beat]
        for j in range(6):
            t = b + beat + j / 6.0
            f = (beat * 6 + j) / 23.0
            ch = "RLK"[j % 3]
            if ch == "R":
                add(t, "RH", rt, 0.60 + 0.30 * f + (0.06 if j == 0 else 0.0))
            elif ch == "L":
                add(t, "LH", lt, 0.50 + 0.30 * f)
            else:
                foot = "LF" if (beat == 3 and j == 5) else "RF"
                kick(t, 0.55 + 0.32 * f, foot=foot)


def part_feet():
    beats = lambda i: 0.18 if i % 4 == 0 else (0.05 if i % 2 == 0 else 0.0)

    # bar 32: double bass enters under bell and backbeat
    b = bb(32)
    cym(b, 0.95, "RH", CR1, with_kick=False)
    dbass(b, b + 4, d=0.48, acc=beats)
    for p in (1.0, 2.0, 3.0):
        add(b + p, "RH", BELL, 0.64 + jit(0.03))
    for p in (0.5, 1.5, 2.5, 3.5):
        add(b + p, "RH", RIDE, 0.44 + jit(0.03))
    add(b + 1.0, "LH", SNARE, 0.88, prio=2); add(b + 3.0, "LH", SNARE, 0.90, prio=2)
    add(b + 2.5, "LH", SNARE, 0.18); add(b + 3.75, "LH", SNARE, 0.24)

    # bar 33: motif A shots over the feet, then paradiddles on the toms
    b = bb(33)
    dbass(b, b + 4, d=0.50, acc=lambda i: 0.16 if i % 4 == 0 else 0.0)
    cym(b, 0.90, "RH", CR2, with_kick=False)
    add(b + 0.75, "LH", T1, 0.84, prio=2)
    cym(b + 1.5, 0.92, "RH", CR1, with_kick=False)
    for p, d in ((0.25, 0.20), (0.5, 0.24), (1.0, 0.26), (1.25, 0.30), (1.75, 0.34)):
        add(b + p, "LH", SNARE, d)
    seq(b + 2.0, 0.25, "RLRRLRLL", [T1, SNARE, T2, T3, SNARE, T4, SNARE, SNARE],
        [0.82, 0.30, 0.50, 0.55, 0.80, 0.56, 0.34, 0.40])

    # bar 34: motif D - quarter-note-triplet unison shots over sixteenth feet
    b = bb(34)
    dbass(b, b + 4, d=0.48, acc=lambda i: 0.16 if i % 4 == 0 else 0.0)
    cy = [CR1, CR2, CR1, CR2, CR1, CHINA]
    for k in range(6):
        t = b + k * 2.0 / 3.0
        add(t, "RH", cy[k], 0.82 + 0.03 * k, prio=3)
        add(t, "LH", SNARE, 0.80 + 0.03 * k, prio=2)

    # bar 35: feet alone play motif A, hands answer
    b = bb(35)
    for i, ch in enumerate("KHHKHHKH"):
        t = b + i * 0.25
        if ch == "K":
            kick(t, 0.78 + jit(0.03))
        else:
            hfoot(t, 0.42 + (0.08 if i == 7 else 0.0))
    seq(b + 2.0, 0.25, "RLLRLLRL", [T1, SNARE, SNARE, T3, SNARE, SNARE, F2, SNARE],
        [0.82, 0.22, 0.26, 0.86, 0.28, 0.32, 0.92, 0.46])
    kick(b + 2.0, 0.72); kick(b + 2.75, 0.74); kick(b + 3.5, 0.80)

    # bar 36: hands first (paradiddle-diddles), then the feet answer
    b = bb(36)
    kick(b, 0.70); kick(b + 1.0, 0.64)
    rt = [(F2, F1), (T4, T3)]
    for beat in range(2):
        a, c = rt[beat]
        for j, ch in enumerate("RLRRLL"):
            t = b + beat + j / 6.0
            f = (beat * 6 + j) / 11.0
            if ch == "R":
                add(t, "RH", a if j == 0 else c, (0.84 if j == 0 else 0.56) + 0.10 * f)
            else:
                add(t, "LH", SNARE, 0.30 + 0.12 * f + jit(0.02))
    dbass(b + 2.0, b + 4.0, d=0.50, acc=lambda i: 0.30 if i in (0, 3, 6) else 0.0)

    # bar 37: 3+3+2 shots - cymbals, then double stops on the toms
    b = bb(37)
    dbass(b, b + 4, d=0.46, acc=lambda i: 0.14 if i % 4 == 0 else 0.0)
    for p, rp, lp in ((0.0, CR1, SNARE), (0.75, CR2, SNARE), (1.5, CR1, SNARE),
                      (2.0, T1, T2), (2.75, T3, T4), (3.5, F1, F2)):
        add(b + p, "RH", rp, 0.90 + jit(0.03), prio=3 if rp in CYMBALS else 2)
        add(b + p, "LH", lp, 0.84 + jit(0.03), prio=2)

    # bar 38: waves of sixteenths down and up the kit over double bass
    b = bb(38)
    dbass(b, b + 4, d=0.44, cresc=0.2, acc=lambda i: 0.12 if i % 4 == 0 else 0.0)
    wave = [T1, T1, T2, T2, T3, T3, F1, F1, F2, F2, F1, F1, T3, T3, T1, T1]
    for i in range(16):
        f = i / 15.0
        d = (0.80 if i % 4 == 0 else 0.52) + 0.14 * f
        add(b + i * 0.25, "RH" if i % 2 == 0 else "LH", wave[i], d + jit(0.02))

    # bar 39: RLRL-KK sextuplets around the kit
    b = bb(39)
    bt = [(T1, T2), (T3, T4), (F1, F2), (SNARE, SNARE)]
    for beat in range(4):
        a, c = bt[beat]
        for j, ch in enumerate("RLRLKk"):
            t = b + beat + j / 6.0
            f = (beat * 6 + j) / 23.0
            if ch in "RL":
                add(t, LIMB[ch], a if j < 2 else c, (0.78 if j == 0 else 0.58) + 0.22 * f)
            else:
                kick(t, 0.62 + 0.26 * f, foot=LIMB[ch])


def part_build():
    # bars 40-41: motif A stretched over the barline (3x10 + 2 sixteenths)
    acc_route = [CR1, T1, T2, T3, T4, F1, F2, CR2, T2, F1, F2]
    start = bb(40)
    for i in range(32):
        t = start + i * 0.25
        f = i / 31.0
        grp = (i % 3) if i < 30 else (i - 30)
        if grp == 0:
            pitch = acc_route[i // 3]
            cymb = pitch in CYMBALS
            add(t, "RH", pitch, (0.80 if cymb else 0.68) + 0.24 * f, prio=3 if cymb else 1)
            kick(t, 0.60 + 0.30 * f)
        else:
            add(t, "LH", SNARE, 0.16 + 0.18 * f + (0.05 if grp == 2 else 0.0) + jit(0.02))
    for q in range(1, 8):
        hfoot(start + q, 0.36)

    # bar 42: half-time triplet shuffle
    b = bb(42)
    cym(b, 0.92, "RH", CR1)
    for beat in range(4):
        for j in (0, 2):
            if beat == 0 and j == 0:
                continue
            add(b + beat + j / 3.0, "RH", RIDE, (0.60 if j == 0 else 0.44) + jit(0.03))
    add(b + 2.0, "LH", SNARE, 0.92, prio=2)
    for p, d in ((1 / 3.0, 0.16), (4 / 3.0, 0.18), (5 / 3.0, 0.13), (7 / 3.0, 0.15),
                 (10 / 3.0, 0.20), (11 / 3.0, 0.26)):
        add(b + p, "LH", SNARE, d + jit(0.02))
    for p, d in ((2 / 3.0, 0.62), (5 / 3.0, 0.56), (8 / 3.0, 0.64), (10 / 3.0, 0.56)):
        kick(b + p, d)
    hfoot(b + 1.0, 0.40); hfoot(b + 3.0, 0.40)

    # bar 43: sextuplets accented in fours - motif D hidden inside a run
    b = bb(43)
    rt = [T1, T2, T3, T4, F1, F2]
    for i in range(24):
        t = b + i / 6.0
        f = i / 23.0
        h = "RH" if i % 2 == 0 else "LH"
        if i % 4 == 0:
            add(t, h, rt[i // 4], 0.70 + 0.24 * f)
            kick(t, 0.56 + 0.30 * f)
        else:
            add(t, h, SNARE, 0.20 + 0.14 * f + jit(0.02))
    for q in range(4):
        hfoot(b + q, 0.34)

    # bar 44: motif D shots, then doubles down the toms
    b = bb(44)
    for p, c in ((0.0, CR1), (2 / 3.0, CR2), (4 / 3.0, CHINA)):
        add(b + p, "RH", c, 0.92, prio=3)
        add(b + p, "LH", SNARE, 0.88, prio=2)
        kick(b + p, 0.86)
    route = [T1, T2, T3, T4, F1, F2]
    for i in range(12):
        t = b + 2.0 + i / 6.0
        h = "RH" if (i // 2) % 2 == 0 else "LH"
        d = 0.50 + 0.40 * i / 11.0 + (0.08 if i % 2 == 0 else 0.0)
        add(t, h, route[i // 2], d)
    for p in (2.0, 2.0 + 2 / 3.0, 2.0 + 4 / 3.0):
        kick(b + p, 0.70)

    # bar 45: displaced shots, space, then fade to almost nothing
    b = bb(45)
    hfoot(b, 0.44); hfoot(b + 1.0, 0.40); hfoot(b + 3.0, 0.36)
    for p, c in ((0.5, CR1), (1.25, CR2), (2.0, CR1)):
        add(b + p, "RH", c, 0.88, prio=3)
        add(b + p, "LH", SNARE, 0.80, prio=2)
        kick(b + p, 0.84)
    for p, h, d in ((2.75, "LH", 0.30), (3.0, "RH", 0.24), (3.25, "LH", 0.20),
                    (3.5, "RH", 0.16), (3.75, "LH", 0.13)):
        add(b + p, h, SNARE, d)

    # bars 46-47: long double-stroke swell, toms start punching through
    b = bb(46)
    n = 60
    acc_toms = {32: T1, 40: T3, 48: F1, 56: F2}
    for i in range(n):
        t = b + i / 8.0
        f = i / (n - 1.0)
        h = "RH" if (i // 2) % 2 == 0 else "LH"
        d = 0.08 + 0.82 * f ** 1.7
        if i % 2:
            d *= 0.9
        pitch = SNARE
        base_i = i - (i % 2)
        if base_i in acc_toms and h == "RH":
            pitch = acc_toms[base_i]
            d = min(1.0, d + 0.22 - (0.1 if i % 2 else 0.0))
        add(t, h, pitch, d + jit(0.015))
    for q in range(8):
        kick(b + q, 0.30 + 0.55 * q / 7.0)
    hfoot(b + 1.0, 0.30); hfoot(b + 3.0, 0.32)
    b = bb(47)
    flam(b + 3.5, "LH", SNARE, 1.0); kick(b + 3.5, 0.92)
    add(b + 3.75, "RH", F2, 0.95); kick(b + 3.75, 0.90, foot="LF")


def part_climax():
    # bar 48: motif A on three cymbals, then sextuplets with kicks
    b = bb(48)
    cym(b, 1.0, "RH", CR1)
    add(b + 0.25, "LH", SNARE, 0.30); add(b + 0.5, "LH", SNARE, 0.34)
    add(b + 0.75, "LH", CR2, 0.95, prio=3); kick(b + 0.75, 0.90)
    add(b + 1.0, "LH", SNARE, 0.30); add(b + 1.25, "LH", SNARE, 0.36)
    cym(b + 1.5, 0.98, "RH", CHINA)
    route = [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2]
    for i in range(12):
        t = b + 2.0 + i / 6.0
        acc = (i % 3 == 0)
        add(t, "RH" if i % 2 == 0 else "LH", route[i], (0.90 if acc else 0.60) + 0.08 * i / 11.0)
        if acc:
            kick(t, 0.86, foot="RF" if (i // 3) % 2 == 0 else "LF")

    # bar 49: the groove comes back, hot
    groove(49, kicks=[(0, 0.90), (0.75, 0.72), (1.5, 0.78), (2.5, 0.74), (2.75, 0.62), (3.25, 0.60)],
           ghosts=[(0.25, 0.20), (1.75, 0.24), (2.25, 0.22), (3.75, 0.28)],
           open_at=(1.5, 3.5), crash=CR2, energy=1.12)
    # bar 50: groove, then motif A on cymbals
    groove(50, kicks=[(0, 0.88), (0.75, 0.70), (1.5, 0.76)],
           ghosts=[(0.25, 0.20), (0.75, 0.20), (1.75, 0.26)], back=(1.0,), stop=2.0, energy=1.12)
    b = bb(50)
    seq(b + 2.0, 0.25, "RLLRLLRL", [CR1, SNARE, SNARE, T2, SNARE, SNARE, CR2, SNARE],
        [0.96, 0.30, 0.34, 0.90, 0.80, 0.36, 1.0, 0.50])
    kick(b + 2.0, 0.90); kick(b + 2.75, 0.86); kick(b + 3.5, 0.94)

    # bar 51: six-stroke rolls all around, kicks on eighths
    b = bb(51)
    for k, (ra, la) in enumerate(((CR1, T1), (T2, T3), (T4, F1), (F2, SNARE))):
        six_stroke(b + k, ra, la, 0.86 + 0.03 * k, 0.34 + 0.04 * k)
        kick(b + k, 0.80)
        kick(b + k + 0.5, 0.62, foot="LF")

    # bar 52: motif A filled, cymbals and floor toms, kicks under every accent
    b = bb(52)
    accp = {0: CR2, 3: T2, 6: F1, 8: CR1, 11: T3, 14: F2}
    for i, ch in enumerate("RLLRLLRLRLLRLLRL"):
        f = i / 15.0
        t = b + i * 0.25
        if ch == "R":
            p = accp[i]
            add(t, "RH", p, 0.86 + 0.12 * f, prio=3 if p in CYMBALS else 1)
            kick(t, 0.82 + 0.12 * f)
        else:
            add(t, "LH", SNARE, 0.30 + 0.12 * f + (0.12 if i in (7, 15) else 0.0) + jit(0.02))

    # bar 53: everything going - double bass and travelling singles
    b = bb(53)
    dbass(b, b + 4, d=0.54, cresc=0.12, acc=lambda i: 0.14 if i % 4 == 0 else 0.0)
    route = [CR1, T1, T2, T2, T3, T3, T4, T4, CR2, F1, F2, F2, F1, T4, T3, SNARE]
    for i in range(16):
        f = i / 15.0
        p = route[i]
        d = (0.86 if i % 4 == 0 else 0.60) + 0.10 * f
        add(b + i * 0.25, "RH" if i % 2 == 0 else "LH", p, d, prio=3 if p in CYMBALS else 1)

    # bar 54: callback to the opening, fortissimo, then silence
    b = bb(54)
    add(b, "RH", T1, 0.96, prio=2); kick(b, 0.90)
    add(b + 0.75, "LH", T3, 0.94, prio=2)
    add(b + 1.5, "RH", F2, 1.0, prio=2); kick(b + 1.5, 0.94)
    hfoot(b + 2.0, 0.46); hfoot(b + 3.0, 0.48)
    add(b + 3.25, "LH", SNARE, 0.24); add(b + 3.5, "RH", SNARE, 0.34)
    add(b + 3.75, "LH", SNARE, 0.46)

    # bar 55: inverted answer, then hands converge and spread over the toms
    b = bb(55)
    add(b, "RH", F2, 0.96); kick(b, 0.90)
    add(b + 0.75, "LH", T3, 0.92)
    add(b + 1.5, "RH", T1, 0.94); kick(b + 1.5, 0.88)
    pairs = [(F2, T1), (F1, T2), (T4, T3), (T4, T3), (F1, T2), (F2, T1)]
    for i in range(12):
        f = i / 11.0
        pr = pairs[i // 2]
        add(b + 2.0 + i / 6.0, "RH" if i % 2 == 0 else "LH", pr[i % 2],
            0.70 + 0.25 * f + (0.06 if i % 3 == 0 else 0.0))
    kick(b + 2.0, 0.80); kick(b + 3.0, 0.86); kick(b + 3.5, 0.90)


def part_ending():
    # bar 56: stop-time shots in the motif's shape, silence, pickup
    b = bb(56)
    for p, c in ((0.0, CR1), (0.75, CR2), (1.5, CHINA)):
        add(b + p, "RH", c, 0.96, prio=3)
        add(b + p, "LH", SNARE, 0.90, prio=2)
        kick(b + p, 0.90)
    hfoot(b + 2.0, 0.48); hfoot(b + 3.0, 0.50)
    add(b + 3.25, "LH", SNARE, 0.30); add(b + 3.5, "RH", SNARE, 0.56)
    add(b + 3.75, "LH", SNARE, 0.80)

    # bar 57: displaced shots, then a roll into the last run
    b = bb(57)
    hfoot(b, 0.50)
    for p, c in ((0.5, CR2), (1.25, CR1), (2.0, CHINA)):
        add(b + p, "RH", c, 0.95, prio=3)
        add(b + p, "LH", SNARE, 0.90, prio=2)
        kick(b + p, 0.90)
    hfoot(b + 2.5, 0.40)
    roll(b + 3.0, b + 4.0, 8, SNARE, 0.40, 0.92, "double")
    kick(b + 3.0, 0.60); kick(b + 3.5, 0.72)

    # bar 58: the fastest run - around the whole kit twice
    b = bb(58)
    route = [CR1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2,
             SNARE, SNARE, T1, T1, T2, T2, T3, T3, F1, F1, F2, F2]
    for i in range(24):
        t = b + i / 6.0
        f = i / 23.0
        p = route[i]
        acc = (i % 3 == 0)
        add(t, "RH" if i % 2 == 0 else "LH", p, (0.86 if acc else 0.62) + 0.12 * f,
            prio=3 if p in CYMBALS else 1)
        if acc:
            k = i // 3
            kick(t, 0.80 + 0.12 * f, foot="RF" if k % 2 == 0 else "LF")

    # bar 59: last swell over double bass, broad hits, and the landing
    b = bb(59)
    roll(b, b + 2.0, 8, SNARE, 0.42, 0.98, "double", curve=1.2)
    dbass(b, b + 2.0, d=0.50, cresc=0.35)
    add(b + 2.0, "RH", CR1, 0.98, prio=3); add(b + 2.0, "LH", SNARE, 0.96, prio=2); kick(b + 2.0, 0.95)
    add(b + 2.5, "RH", T1, 0.95, prio=2); add(b + 2.5, "LH", T2, 0.92, prio=2); kick(b + 2.5, 0.92)
    add(b + 3.0, "RH", F1, 0.97, prio=2); add(b + 3.0, "LH", F2, 0.95, prio=2); kick(b + 3.0, 0.95)
    flam(b + 3.5, "RH", SNARE, 1.0); kick(b + 3.5, 0.97)
    b = bb(60)
    for hand, p in (("RH", CR1), ("LH", CR2)):
        n = add(b, hand, p, 1.0, prio=5)
        n.final = True
    n = kick(b, 1.0, prio=5)
    n.final = True


def compose():
    part_opening()
    part_groove()
    part_flow()
    part_colors()
    part_feet()
    part_build()
    part_climax()
    part_ending()


# --------------------------------------------------------------------------
# never the same bar twice
# --------------------------------------------------------------------------
def bar_signature(bar):
    lo = bar * 4.0
    return tuple(sorted((int(round((n.beat - lo) * 48)), n.pitch)
                        for n in NOTES if lo - 1e-9 <= n.beat < lo + 4.0 - 1e-9))


def vary_bar(bar):
    lo = bar * 4.0
    slots = [lo + i * 0.25 for i in range(16)]
    R.shuffle(slots)
    for t in slots:
        lh_busy = any(n.limb == "LH" and abs(n.beat - t) < 0.2 for n in NOTES)
        hands = sum(1 for n in NOTES if n.limb in ("RH", "LH") and abs(n.beat - t) < 1e-6)
        if not lh_busy and hands < 2:
            add(t, "LH", SNARE, 0.12)
            return
    toms = [n for n in NOTES if lo <= n.beat < lo + 4 and n.pitch in TOMS]
    if toms:
        n = toms[R.randrange(len(toms))]
        n.pitch = TOMS[(TOMS.index(n.pitch) + 1) % len(TOMS)]


def ensure_unique_bars():
    seen = set()
    for bar in range(FINAL_BAR):
        sig = bar_signature(bar)
        tries = 0
        while sig in seen and tries < 24:
            vary_bar(bar)
            tries += 1
            sig = bar_signature(bar)
        seen.add(sig)


# --------------------------------------------------------------------------
# tempo: surges in fills, settles after landings, broadens into the end
# --------------------------------------------------------------------------
TEMPO_ANCHORS = [
    (0.0, 110.0), (2.0, 113.0), (3.9, 117.0), (4.0, 118.0), (5.0, 115.0),
    (6.0, 116.0), (8.0, 120.0), (15.9, 122.0), (16.0, 123.0), (22.0, 125.0),
    (23.95, 128.0), (24.0, 116.0), (30.0, 118.0), (31.95, 122.0), (32.0, 124.0),
    (39.95, 127.0), (40.0, 125.0), (46.0, 128.0), (47.95, 132.0), (48.0, 132.0),
    (53.95, 135.0), (54.0, 131.0), (56.0, 131.0), (60.0, 132.0),
]
PUSH_BARS = (3, 7, 11, 15, 18, 23, 31, 36, 39, 44, 47, 50, 55, 57, 58)
HOLD_BARS = ((5, 0.015), (21, 0.012), (45, 0.010), (54, 0.020))


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def base_bpm(beat):
    x = beat / 4.0
    A = TEMPO_ANCHORS
    if x <= A[0][0]:
        return A[0][1]
    for (x0, v0), (x1, v1) in zip(A, A[1:]):
        if x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return A[-1][1]


def bpm_at(beat, phase):
    m = 1.0
    for bar in PUSH_BARS:
        s = bar * 4 + 1.5
        e = bar * 4 + 4.0
        if s <= beat < e:
            m += 0.028 * smoothstep((beat - s) / (e - s))
        elif e <= beat < e + 2.0:
            u = beat - e
            m += 0.028 * (1.0 - smoothstep(u / 0.6)) - 0.007 * math.sin(math.pi * u / 2.0)
    for bar, amt in HOLD_BARS:
        s = bar * 4
        if s <= beat < s + 4:
            m -= amt * math.sin(math.pi * (beat - s) / 4.0)
    m += 0.004 * math.sin(2 * math.pi * beat / 29.0 + phase)
    rs = 59 * 4 + 2.5
    if beat > rs:
        m *= 1.0 - 0.2 * smoothstep((beat - rs) / 1.5)
    return base_bpm(beat) * m


class TempoMap:
    def __init__(self):
        phase = R.uniform(0, 2 * math.pi)
        nseg = int((FINAL_BEAT + 12) / SEG)
        raw = []
        for k in range(nseg):
            mid = min((k + 0.5) * SEG, FINAL_BEAT - 0.25)
            raw.append(bpm_at(mid, phase))
        nfin = int(FINAL_BEAT / SEG)
        t_final = sum(SEG * 60.0 / raw[k] for k in range(nfin))
        scale = t_final / FINAL_TIME
        self.tempos = [int(round(60e6 / (v * scale))) for v in raw]
        self.starts = [0.0]
        for us in self.tempos:
            self.starts.append(self.starts[-1] + SEG * us / 1e6)

    def beat_to_sec(self, beat):
        k = int(beat // SEG)
        k = max(0, min(k, len(self.tempos) - 1))
        return self.starts[k] + (beat - k * SEG) * self.tempos[k] / 1e6

    def sec_to_tick(self, t):
        if t <= 0:
            return 0
        k = bisect.bisect_right(self.starts, t) - 1
        k = max(0, min(k, len(self.tempos) - 1))
        beat = k * SEG + (t - self.starts[k]) * 1e6 / self.tempos[k]
        return int(round(beat * TPB))


# --------------------------------------------------------------------------
# performance: human timing and touch
# --------------------------------------------------------------------------
GROOVE_BARS = set(range(8, 15)) | {49, 50}
COLOR_BARS = set(range(24, 30))


def humanize(notes, tmap):
    ph = [R.uniform(0, 2 * math.pi) for _ in range(4)]
    for L in ("RH", "LH", "RF", "LF"):
        lst = sorted((n for n in notes if n.limb == L and n.anchor is None), key=lambda n: n.beat)
        for i, n in enumerate(lst):
            g = 1.0
            if i > 0:
                g = min(g, n.beat - lst[i - 1].beat)
            if i + 1 < len(lst):
                g = min(g, lst[i + 1].beat - n.beat)
            n.dens = max(0.45, min(1.0, g * 0.48 / 0.12))
    for n in notes:
        if n.anchor is not None:
            continue
        bar = int(n.beat // 4)
        pos = n.beat - bar * 4
        d = n.dyn
        sigma = (2.0 + 4.0 * (1.0 - d) ** 1.5) * n.dens
        off = max(-2.5 * sigma, min(2.5 * sigma, R.gauss(0.0, sigma)))
        if n.limb in ("RH", "LH"):
            off += 2.6 * math.sin(2 * math.pi * n.beat / 10.7 + ph[0])
            off += 1.4 * math.sin(2 * math.pi * n.beat / 3.9 + ph[1])
            if n.limb == "LH":
                off += 1.0
        else:
            off += 2.0 * math.sin(2 * math.pi * n.beat / 13.1 + ph[2]) - 1.5
        off -= 1.5 * (d - 0.5)
        if bar in GROOVE_BARS:
            if n.pitch == SNARE and d > 0.7:
                off += 6.0
            elif n.pitch == SNARE and d < 0.3:
                off += 3.0
            if n.pitch in (HHC, HHO):
                e = pos * 2
                if abs(e - round(e)) < 1e-6 and int(round(e)) % 2 == 1:
                    off += 2.5
        if bar in COLOR_BARS:
            q = pos * 4
            if abs(q - round(q)) < 1e-6 and int(round(q)) % 2 == 1:
                off += 11.0 * n.dens
            off += 3.0
        n.off = off + n.ms
        n.t = tmap.beat_to_sec(n.beat) + n.off / 1000.0
    for n in notes:
        if n.anchor is None:
            continue
        n.off = n.anchor.off + n.ms + R.gauss(0.0, 1.2)
        n.t = tmap.beat_to_sec(n.beat) + n.off / 1000.0
    for n in notes:
        v = 8 + 119 * n.dyn + R.gauss(0.0, 1.5 + 3.5 * (1.0 - n.dyn))
        if n.limb == "LH" and n.dyn < 0.8:
            v -= 2
        if n.pitch in CYMBALS and not n.final:
            v = min(v, 120)
        if n.final:
            v = 127
        n.vel = int(max(1, min(127, round(v))))
        n.t = max(0.0, n.t)


# --------------------------------------------------------------------------
# physical limits: one stroke per limb at a time, two hands, two feet
# --------------------------------------------------------------------------
HAND_GAP = 0.034
FOOT_GAP = 0.080
PEDAL_SWITCH = 0.180


def need_gap(limb, prev, n):
    if limb in ("RH", "LH"):
        return HAND_GAP
    if limb == "LF" and prev.pitch != n.pitch:
        return PEDAL_SWITCH
    return FOOT_GAP


def make_playable(notes):
    notes.sort(key=lambda n: (n.t, -n.prio, n.pitch))
    last = {"RH": None, "LH": None, "RF": None, "LF": None}
    for n in notes:
        opts = [n.limb]
        if n.limb in ("RH", "LH"):
            opts.append(other(n.limb))
        elif n.pitch == KICK:
            opts.append("LF" if n.limb == "RF" else "RF")
        chosen = None
        for L in opts:
            p = last[L]
            if p is None or n.t - p.t >= need_gap(L, p, n):
                chosen = L
                break
        if chosen is None:
            L = n.limb
            p = last[L]
            g = need_gap(L, p, n)
            if p.t + g - n.t <= 0.012:
                n.t = p.t + g
                chosen = L
            elif n.prio > p.prio:
                p.dropped = True
                chosen = L
            else:
                n.dropped = True
                continue
        n.limb = chosen
        last[chosen] = n
    kept = [n for n in notes if not n.dropped]
    kept.sort(key=lambda n: (n.t, n.pitch))
    out = []
    lastp = {}
    for n in kept:
        q = lastp.get(n.pitch)
        if q is not None and n.t - q.t < 0.008:
            if n.vel > q.vel:
                q.dropped = True
                lastp[n.pitch] = n
                out.append(n)
            continue
        lastp[n.pitch] = n
        out.append(n)
    res = [n for n in out if not n.dropped]
    res.sort(key=lambda n: (n.t, n.pitch))
    return res


def assign_durations(notes):
    nl = {}
    npch = {}
    for n in reversed(notes):
        base = 2.0 if n.final else (0.30 if n.pitch in RINGING else 0.09)
        lim = base
        a = nl.get(n.limb)
        if a is not None:
            lim = min(lim, 0.85 * (a.t - n.t))
        c = npch.get(n.pitch)
        if c is not None:
            lim = min(lim, 0.85 * (c.t - n.t))
        n.dur = max(0.004, lim)
        nl[n.limb] = n
        npch[n.pitch] = n


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def write_midi(notes, tmap):
    for n in notes:
        n.on_tick = tmap.sec_to_tick(n.t)
        n.off_tick = max(n.on_tick + 1, tmap.sec_to_tick(n.t + n.dur))
    by_pitch = {}
    for n in sorted(notes, key=lambda n: (n.on_tick, n.pitch)):
        by_pitch.setdefault(n.pitch, []).append(n)
    for lst in by_pitch.values():
        for a, b in zip(lst, lst[1:]):
            if a.off_tick > b.on_tick:
                a.off_tick = max(a.on_tick + 1, b.on_tick)

    finals = [n.t for n in notes if n.final]
    final_t = max(finals) if finals else max(n.t for n in notes)
    end_tick = tmap.sec_to_tick(final_t + TAIL)
    end_tick = max(end_tick, max(n.off_tick for n in notes) + 1)

    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)

    tt = mido.MidiTrack()
    mid.tracks.append(tt)
    tt.append(mido.MetaMessage("track_name", name="Tempo", time=0))
    tt.append(mido.MetaMessage("time_signature", numerator=4, denominator=4,
                               clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    last_tick = 0
    last_us = None
    for k, us in enumerate(tmap.tempos):
        tick = k * SEG_TICKS
        if tick >= end_tick:
            break
        if us != last_us:
            tt.append(mido.MetaMessage("set_tempo", tempo=us, time=tick - last_tick))
            last_tick = tick
            last_us = us
    tt.append(mido.MetaMessage("end_of_track", time=max(0, end_tick - last_tick)))

    dt = mido.MidiTrack()
    mid.tracks.append(dt)
    dt.append(mido.MetaMessage("track_name", name="Drum Solo", time=0))
    dt.append(mido.Message("program_change", channel=CHANNEL, program=0, time=0))
    dt.append(mido.Message("control_change", channel=CHANNEL, control=7, value=112, time=0))
    dt.append(mido.Message("control_change", channel=CHANNEL, control=10, value=64, time=0))
    dt.append(mido.Message("control_change", channel=CHANNEL, control=91, value=40, time=0))
    evs = []
    for n in notes:
        evs.append((n.on_tick, 1, n.pitch, n.vel))
        evs.append((n.off_tick, 0, n.pitch, 64))
    evs.sort()
    cur = 0
    for tick, kind, pitch, vel in evs:
        if kind == 1:
            msg = mido.Message("note_on", channel=CHANNEL, note=pitch, velocity=vel, time=tick - cur)
        else:
            msg = mido.Message("note_off", channel=CHANNEL, note=pitch, velocity=vel, time=tick - cur)
        dt.append(msg)
        cur = tick
    dt.append(mido.MetaMessage("end_of_track", time=max(0, end_tick - cur)))
    mid.save(OUT_FILE)


def main():
    compose()
    ensure_unique_bars()
    tmap = TempoMap()
    humanize(NOTES, tmap)
    notes = make_playable(list(NOTES))
    assign_durations(notes)
    write_midi(notes, tmap)


if __name__ == "__main__":
    main()
