#!/usr/bin/env python3
"""
drum_solo.py
============

Writes ``solo.mid``: a two minute drum solo for a General MIDI
synthesizer, on the GM percussion channel (10).

The solo is *composed bar by bar* (motif -> variation -> contrast ->
build -> payoff), then passed through two performance stages:

  * a humanising stage: phrase level push/pull, micro timing, a little
    swing on the off sixteenths and ghost note "slop", velocity jitter;
  * a physical stage: at most two hands and two feet are ever asked to
    strike at the same moment (each limb has a minimum re-strike time),
    so one drummer can actually play it.

Deterministic: every run writes identical bytes.
"""

import bisect
import math
import random

from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

PPQ = 480
TOTAL_SECONDS = 120.0
rng = random.Random(0xD0D0)

# ------------------------------------------------------------------ kit map
KICK, KICK2 = 36, 35
SNARE, RIM = 38, 37
FLOOR_LO, FLOOR_HI = 41, 43
TOM_LO, TOM_LOMID, TOM_HIMID, TOM_HI = 45, 47, 48, 50
HAT, HAT_PED, HAT_OPEN = 42, 44, 46
CRASH1, CRASH2, RIDE, RIDE_BELL = 49, 57, 51, 53
SPLASH, CHINA = 55, 52
TAMB, COWBELL = 54, 56
BONGO_HI, BONGO_LO = 60, 61
CONGA_HI, CONGA_MH, CONGA_LO = 63, 62, 64

DOWN_TOMS = (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO, FLOOR_HI, FLOOR_LO)
UP_TOMS = tuple(reversed(DOWN_TOMS))

# ------------------------------------------------------- form and tempo map
# (first bar, how many bars, bpm at first bar, bpm at last bar,
#  phrase feel at first bar, phrase feel at last bar)   feel in ticks
SECTIONS = (
    (1, 8, 118.0, 126.0, 3.0, -2.0),      # alone on the kit / motif stated
    (9, 8, 126.0, 132.0, -2.0, -4.0),     # hands travel, doubles
    (17, 8, 132.0, 127.0, 4.0, 2.0),      # melodic toms, the tumble
    (25, 8, 127.0, 121.0, 6.0, 3.0),      # breakdown, space, colour
    (33, 8, 121.0, 138.0, 2.0, -6.0),     # build, rolls, swell
    (41, 12, 138.0, 146.0, -3.0, -5.0),   # linear runs, chops
    (53, 12, 146.0, 153.0, -4.0, -7.0),   # climax
    (65, 4, 153.0, 147.0, -2.0, 1.0),     # final statement
)
LAST_BAR = 68


def tempo_at_bar(bar):
    for b0, n, t0, t1, _f0, _f1 in SECTIONS:
        if b0 <= bar < b0 + n:
            return t0 + (t1 - t0) * (bar - b0) / max(1, n - 1)
    return SECTIONS[-1][2]


def feel_at(beat):
    for b0, n, _t0, _t1, f0, f1 in SECTIONS:
        start = (b0 - 1) * 4.0
        if start <= beat < start + n * 4.0:
            frac = (beat - start) / (n * 4.0)
            return f0 + (f1 - f0) * frac
    return 0.0


def beat_to_sec(b):
    bar = int(b // 4)
    sec = 0.0
    for i in range(bar):
        sec += 240.0 / tempo_at_bar(i + 1)
    sec += (b - bar * 4) * 60.0 / tempo_at_bar(min(bar + 1, LAST_BAR))
    return sec


# ------------------------------------------------------------- note store
NOTES = []
LIMB_T = {"RH": [], "LH": [], "RF": [], "LF": []}


def bb(bar):
    """first beat of a bar (bar is 1 based)"""
    return (bar - 1) * 4.0


def limb_busy(limb, t, gap=0.06):
    lst = LIMB_T[limb]
    i = bisect.bisect_left(lst, t)
    if i < len(lst) and lst[i] - t < gap:
        return True
    if i > 0 and t - lst[i - 1] < gap:
        return True
    return False


def add(t, note, vel, dur=0.09, limb="RH", kind="normal"):
    v = int(max(1, min(127, round(vel))))
    NOTES.append({"t": float(t), "note": int(note), "vel": v,
                  "dur": float(dur), "limb": limb, "kind": kind})
    bisect.insort(LIMB_T[limb], float(t))


def hit(bar, off, note, vel, dur=0.09, limb="RH", kind="normal"):
    add(bb(bar) + off, note, vel, dur, limb, kind)


# ------------------------------------------------------------------ figures
GHOST_SETS = (
    (0.75, 2.5, 3.75),
    (0.5, 1.75, 2.75, 3.75),
    (0.75, 2.25, 3.25, 3.75),
    (0.25, 0.75, 2.5, 3.5),
    (0.75, 3.5, 3.75),
    (0.25, 1.75, 2.5, 3.25),
)


def hat_bar(bar, vel=54.0, accent=8, skip=(), cut=4.0, start=0.0,
            sub=0.5, note=HAT, limb="RH", kind="normal"):
    n = int(round((cut - start) / sub))
    for i in range(n):
        off = start + i * sub
        if any(abs(off - s) < 1e-6 for s in skip):
            continue
        on_beat = abs(off % 1.0) < 1e-6
        add(bb(bar) + off, note, vel + (accent if on_beat else 0),
            0.05, limb, kind)


def ride_bar(bar, vel=50.0, accent=8, skip=(), cut=4.0, bell=False):
    for i in range(8):
        off = i * 0.5
        if off >= cut - 1e-9 or any(abs(off - s) < 1e-6 for s in skip):
            continue
        on_beat = abs(off % 1.0) < 1e-6
        note = RIDE_BELL if (bell and on_beat) else RIDE
        add(bb(bar) + off, note, vel + (accent if on_beat else 0),
            0.06, "RH", "cym")


def groove(bar, vel=1.0, cym="hat", ghost=0, open_end=False, bell=False,
           cut=4.0, skip_snare=(), skip_cym=(), kick_extra=(), pedal=()):
    """The solo's rhythmic motif: a pocket with ghosts and a lift."""
    kv = 94.0 * vel
    sv = 108.0 * vel
    for off, v in ((0.0, kv), (1.5, kv - 16), (2.0, kv - 6), (3.5, kv - 20)):
        if off < cut:
            hit(bar, off, KICK, v, 0.12, "RF",
                "down" if off % 2.0 == 0.0 else "normal")
    for off, v in ((1.0, sv), (3.0, sv - 6)):
        if off < cut and off not in skip_snare:
            hit(bar, off, SNARE, v, 0.10, "LH", "accent")
    for g in GHOST_SETS[ghost % len(GHOST_SETS)]:
        if g < cut:
            hit(bar, g, SNARE,
                24 + (12 if g > 3.0 else 0) + rng.randint(0, 7),
                0.06, "LH", "ghost")
    skip = set(skip_cym)
    if open_end:
        skip.add(3.5)
    skip = tuple(sorted(skip))
    if cym == "hat":
        hat_bar(bar, vel=52.0 * vel, accent=9, skip=skip, cut=cut)
        if open_end and cut > 3.5:
            hit(bar, 3.5, HAT_OPEN, 76.0 * vel, 0.7, "RH", "cym")
    elif cym == "ride":
        ride_bar(bar, vel=50.0 * vel, accent=8, skip=skip, cut=cut, bell=bell)
    for off in kick_extra:
        hit(bar, off, KICK, kv - 12, 0.10, "RF", "normal")
    for off in pedal:
        hit(bar, off, HAT_PED, 58.0 * vel, 0.07, "LF", "normal")


def tom_run(bar, start, drums, step, v0, v1, first="RH", tag="roll"):
    n = len(drums)
    for i, d in enumerate(drums):
        t = bb(bar) + start + i * step
        v = v0 + (v1 - v0) * (i / max(1, n - 1))
        limb = first if i % 2 == 0 else ("LH" if first == "RH" else "RH")
        add(t, d, v, min(0.16, step * 0.85), limb,
            "accent" if v >= 88 else tag)


def roll(bar, start, span, step, v0, v1, note=SNARE, first="RH",
         accent_every=4, tag="roll"):
    n = int(round(span / step))
    for i in range(n):
        t = bb(bar) + start + i * step
        v = v0 + (v1 - v0) * (i / max(1, n - 1))
        if accent_every and i % accent_every == 0:
            v += 8
        limb = first if i % 2 == 0 else ("LH" if first == "RH" else "RH")
        add(t, note, v, step * 0.85, limb, tag)


def linear(bar, seq, start=0.0, step=0.25, strong=94, weak=74, first="RH"):
    """Linear drumming: one note per limb slot, none at the same time."""
    for i, d in enumerate(seq):
        t = bb(bar) + start + i * step
        v = strong if i % 4 == 0 else weak
        if d == KICK or d == KICK2:
            add(t, d, v, 0.10, "RF", "normal")
        else:
            limb = first if i % 2 == 0 else ("LH" if first == "RH" else "RH")
            add(t, d, v, 0.10, limb, "normal")


# ============================================================== 1. INTRO ===
def sec_intro():
    # bars 1-2 : the drummer sits down, ride quarters and the foot
    for bar in (1, 2):
        for q in range(4):
            hit(bar, q, RIDE, 50 + (12 if q == 0 else 0), 0.10, "RH", "cym")
        hit(bar, 0.0, KICK, 88, 0.14, "RF", "down")
        hit(bar, 2.0, KICK, 82, 0.14, "RF", "down")
        hit(bar, 1.0, HAT_PED, 62, 0.07, "LF", "normal")
        hit(bar, 3.0, HAT_PED, 58, 0.07, "LF", "normal")
    hit(2, 0.75, SNARE, 28, 0.07, "LH", "ghost")
    hit(2, 3.75, SNARE, 34, 0.07, "LH", "ghost")

    # bars 3-8 : the motif, stated then nudged
    groove(3, vel=0.94, cym="hat", ghost=0)
    groove(4, vel=0.98, cym="hat", ghost=1, open_end=True)
    groove(5, vel=1.00, cym="hat", ghost=2)
    groove(6, vel=1.00, cym="ride", ghost=3, cut=3.0)
    tom_run(6, 3.0, (TOM_HIMID, TOM_LOMID, FLOOR_HI), 0.25, 78, 100)
    groove(7, vel=1.02, cym="ride", ghost=0, bell=True, cut=3.0)
    tom_run(7, 3.0, (TOM_HI, TOM_LOMID, FLOOR_LO), 0.25, 82, 104)
    groove(8, vel=1.04, cym="hat", ghost=1, cut=3.0)
    tom_run(8, 3.0, (TOM_HI, TOM_HIMID, TOM_LOMID, FLOOR_HI), 0.25, 80, 112)
    hit(9, 0.0, CRASH1, 112, 1.8, "LH", "cym")
    hit(9, 0.0, KICK, 108, 0.12, "RF", "down")


# ============================================================== 2. TRAVEL ==
def sec_travel():
    groove(9, vel=1.05, cym="hat", ghost=1)

    # 10 : flam on the second backbeat (both hands, so the hat lifts)
    groove(10, vel=1.05, cym="hat", ghost=2,
           skip_cym=(3.0,), skip_snare=(3.0,))
    hit(10, 2.93, SNARE, 52, 0.05, "LH", "ghost")
    hit(10, 3.0, SNARE, 112, 0.10, "RH", "accent")

    # 11 : the backbeat moves out to the toms
    groove(11, vel=1.02, cym="hat", ghost=0, skip_snare=(1.0, 3.0))
    hit(11, 1.0, TOM_HIMID, 104, 0.12, "LH", "accent")
    hit(11, 3.0, TOM_LO, 100, 0.12, "LH", "accent")
    hit(11, 3.5, TOM_LOMID, 72, 0.08, "LH", "normal")

    # 12 : the tumble answers
    groove(12, vel=1.02, cym="hat", ghost=1, cut=2.5, skip_cym=(2.0,))
    tom_run(12, 2.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO),
            0.25, 76, 108)

    # 13-14 : sixteenth pairs travel down, then back up
    for bar, drums in ((13, (SNARE, TOM_HI, TOM_LOMID, TOM_LO)),
                       (14, (FLOOR_LO, FLOOR_HI, TOM_LOMID, TOM_HI))):
        hit(bar, 0.0, KICK, 102, 0.12, "RF", "down")
        hit(bar, 2.0, KICK, 98, 0.12, "RF", "down")
        hit(bar, 1.5, KICK, 76, 0.10, "RF", "normal")
        hit(bar, 3.5, KICK, 78, 0.10, "RF", "normal")
        for i, d in enumerate(drums):
            hit(bar, float(i), d, 100 - 5 * i, 0.09, "RH", "accent")
            hit(bar, i + 0.25, d, 58 - 4 * i, 0.07, "LH", "normal")
        for off in (0.5, 1.5, 2.5):
            hit(bar, off, HAT, 54, 0.05, "RH", "normal")

    # 15 : single strokes, accents every beat
    hit(15, 0.0, KICK, 104, 0.12, "RF", "down")
    hit(15, 2.0, KICK, 100, 0.12, "RF", "down")
    roll(15, 0.0, 4.0, 0.25, 62, 96)

    # 16 : the tumble at speed, right into the crash
    tom_run(16, 0.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, TOM_LO), 0.25, 80, 98)
    tom_run(16, 2.0, DOWN_TOMS, 0.125, 84, 100)
    tom_run(16, 3.0, (FLOOR_LO, FLOOR_HI, TOM_LO, TOM_LOMID,
                      TOM_HIMID, TOM_HI, TOM_HIMID, TOM_HI), 0.125, 92, 118)
    hit(16, 3.5, KICK, 106, 0.10, "RF", "normal")
    hit(17, 0.0, CRASH1, 114, 1.8, "LH", "cym")
    hit(17, 0.0, KICK, 110, 0.12, "RF", "down")


# ============================================================= 3. MELODIC ==
def sec_melodic():
    groove(17, vel=1.00, cym="ride", ghost=0)

    groove(18, vel=0.98, cym="ride", ghost=3, cut=3.0, skip_cym=(3.0,))
    tom_run(18, 3.0, (TOM_HI, TOM_HIMID, TOM_LOMID, FLOOR_HI), 0.25, 74, 104)

    # 19 : call and answer - toms take the backbeat
    groove(19, vel=1.00, cym="hat", ghost=1, skip_snare=(1.0, 3.0))
    hit(19, 1.0, TOM_HIMID, 102, 0.12, "LH", "accent")
    hit(19, 3.0, TOM_LO, 98, 0.12, "LH", "accent")

    # 20 : motif stretched - a slow tumble, then the same idea rising
    hit(20, 0.0, KICK, 100, 0.12, "RF", "down")
    hit(20, 1.0, SNARE, 102, 0.10, "LH", "accent")
    hit(20, 2.0, KICK, 96, 0.12, "RF", "down")
    tom_run(20, 0.5, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO), 0.25, 66, 84)
    tom_run(20, 2.0, (TOM_LO, TOM_LOMID, TOM_HIMID, TOM_HI), 0.25, 86, 106)

    hit(21, 0.0, CRASH2, 108, 1.6, "LH", "cym")
    hit(21, 0.0, KICK, 104, 0.12, "RF", "down")
    groove(21, vel=1.00, cym="hat", ghost=2)
    groove(22, vel=1.00, cym="ride", ghost=1, cut=2.5, skip_cym=(2.0,))
    tom_run(22, 2.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO), 0.25, 72, 96)

    # 23 : swell
    hit(23, 0.0, KICK, 100, 0.12, "RF", "down")
    hit(23, 2.0, KICK, 96, 0.12, "RF", "down")
    hit(23, 0.0, RIDE_BELL, 94, 0.10, "RH", "cym")
    roll(23, 0.5, 3.5, 0.25, 54, 80)

    # 24 : soft turnaround - everything lets go into the breakdown
    hit(24, 0.0, KICK, 88, 0.12, "RF", "down")
    hit(24, 1.0, SNARE, 78, 0.10, "LH", "accent")
    hit(24, 2.0, KICK, 74, 0.12, "RF", "normal")
    hat_bar(24, vel=44, accent=6, cut=3.0)
    tom_run(24, 3.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO), 0.25, 66, 84)
    hit(24, 3.75, SPLASH, 52, 0.5, "RH", "cym")


# ============================================================ 4. BREAKDOWN ==
def sec_breakdown():
    # 25-26 : space
    for i, bar in enumerate((25, 26)):
        hit(bar, 0.0, KICK, 82, 0.14, "RF", "down")
        hit(bar, 1.5, KICK, 58, 0.12, "RF", "normal")
        hit(bar, 2.0, RIM, 74, 0.10, "LH", "accent")
        hit(bar, 3.5, KICK, 62, 0.12, "RF", "normal")
        hat_bar(bar, vel=40, accent=6, skip=(2.0,))
        if i == 0:
            hit(bar, 2.75, SNARE, 24, 0.06, "LH", "ghost")
            hit(bar, 3.75, SNARE, 28, 0.06, "LH", "ghost")
        else:
            hit(bar, 0.75, SNARE, 22, 0.06, "LH", "ghost")
            hit(bar, 2.75, SNARE, 26, 0.06, "LH", "ghost")
            hit(bar, 3.0, HAT_PED, 54, 0.07, "LF", "normal")

    # 27-28 : hand drums for colour, the motif hides inside them
    for i, bar in enumerate((27, 28)):
        hit(bar, 0.0, KICK, 80, 0.14, "RF", "down")
        hit(bar, 2.0, RIM, 68, 0.10, "LH", "accent")
        hat_bar(bar, vel=38, accent=6, cut=2.0)
        pat = ((BONGO_HI, BONGO_LO, CONGA_HI, CONGA_LO) if i == 0 else
               (COWBELL, BONGO_HI, CONGA_LO, CONGA_HI))
        for j in range(8):
            d = pat[j % 4]
            t = 2.0 + j * 0.25
            add(bb(bar) + t, d,
                46 + (10 if j % 4 == 0 else 0) + rng.randint(0, 4),
                0.09, "RH" if j % 2 == 0 else "LH", "normal")

    # 29-30 : the kit comes back, still soft, ghosts everywhere
    for bar in (29, 30):
        hit(bar, 0.0, KICK, 88, 0.14, "RF", "down")
        hit(bar, 1.0, SNARE, 68, 0.10, "LH", "accent")
        hit(bar, 2.0, KICK, 80, 0.12, "RF", "normal")
        hit(bar, 3.0, SNARE, 72, 0.10, "LH", "accent")
        hat_bar(bar, vel=46, accent=6)
        for g in GHOST_SETS[(bar + 2) % len(GHOST_SETS)][:3]:
            hit(bar, g, SNARE, 22 + rng.randint(0, 8), 0.06, "LH", "ghost")

    # 31 : the swell starts at nothing
    hit(31, 0.0, KICK, 86, 0.12, "RF", "down")
    hit(31, 2.0, KICK, 90, 0.12, "RF", "down")
    roll(31, 0.0, 2.0, 0.25, 38, 62)
    roll(31, 2.0, 2.0, 0.25, 64, 96)

    # 32 : and lets go
    tom_run(32, 0.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO), 0.25, 84, 106)
    tom_run(32, 2.0, (FLOOR_LO, FLOOR_HI, TOM_LO, TOM_LOMID,
                      TOM_HIMID, TOM_HI, TOM_HIMID, TOM_HI), 0.125, 92, 118)
    hit(32, 3.0, KICK, 112, 0.12, "RF", "normal")
    hit(33, 0.0, CRASH1, 118, 2.0, "LH", "cym")
    hit(33, 0.0, KICK, 112, 0.12, "RF", "down")


# ================================================================ 5. BUILD ==
def sec_build():
    groove(33, vel=1.08, cym="ride", ghost=1)
    groove(34, vel=1.08, cym="ride", ghost=2, kick_extra=(0.25, 2.25))

    # 35 : sixteenths on the snare, accents leading
    hit(35, 0.0, KICK, 106, 0.12, "RF", "down")
    hit(35, 2.0, KICK, 102, 0.12, "RF", "down")
    roll(35, 0.0, 3.0, 0.25, 68, 94)
    hit(35, 3.0, HAT, 70, 0.05, "RH", "accent")
    hit(35, 3.5, HAT, 62, 0.05, "RH", "normal")
    hit(35, 3.0, SNARE, 96, 0.10, "LH", "accent")
    hit(35, 3.75, SNARE, 40, 0.06, "LH", "ghost")

    # 36 : the tumble, answered
    groove(36, vel=1.06, cym="hat", ghost=0, cut=2.0, skip_cym=(2.0,))
    tom_run(36, 2.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO), 0.25, 82, 108)

    # 37 : a long snare swell, rolling with the hands
    hit(37, 0.0, KICK, 106, 0.12, "RF", "down")
    hit(37, 2.0, KICK, 100, 0.12, "RF", "down")
    roll(37, 0.0, 4.0, 0.25, 54, 90)

    # 38 : the swell walks round the toms
    hit(38, 0.0, KICK, 108, 0.12, "RF", "down")
    hit(38, 2.0, KICK, 104, 0.12, "RF", "down")
    tom_run(38, 0.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO) * 2,
            0.25, 78, 102)

    # 39 : singles travel
    tom_run(39, 0.0, (SNARE, TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI,
                      SNARE, TOM_HI, TOM_HIMID, TOM_LOMID,
                      TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_HI),
            0.25, 74, 98, first="LH")

    # 40 : everything, into the top
    hit(40, 0.0, KICK, 110, 0.12, "RF", "down")
    hit(40, 2.0, KICK, 112, 0.12, "RF", "down")
    tom_run(40, 0.0, DOWN_TOMS, 0.125, 88, 104)
    tom_run(40, 1.0, UP_TOMS, 0.125, 96, 110)
    tom_run(40, 2.0, DOWN_TOMS, 0.125, 104, 116)
    tom_run(40, 3.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO), 0.125, 108, 122)
    hit(41, 0.0, CRASH1, 116, 2.0, "LH", "cym")
    hit(41, 0.0, KICK, 112, 0.12, "RF", "down")


# ================================================================= 6. RUNS ==
LIN_A = (KICK, SNARE, TOM_HI, SNARE, KICK, TOM_LOMID, TOM_LO, SNARE,
         KICK, SNARE, TOM_HI, TOM_LO, KICK, FLOOR_HI, TOM_LO, SNARE)
LIN_B = (SNARE, KICK, TOM_HIMID, TOM_LO, SNARE, KICK, FLOOR_HI, TOM_LOMID,
         SNARE, TOM_HI, KICK, FLOOR_LO, SNARE, TOM_LOMID, KICK, TOM_HI)


def sec_runs():
    linear(41, LIN_A)
    linear(42, LIN_B)

    # 43 : the motif again, right in the middle of the storm
    groove(43, vel=1.06, cym="ride", ghost=0, bell=True)

    # 44 : short fill
    groove(44, vel=1.06, cym="hat", ghost=3, cut=2.0, skip_cym=(2.0,))
    tom_run(44, 2.0, (TOM_LO, TOM_LOMID, TOM_HIMID, TOM_HI,
                      TOM_HIMID, TOM_LOMID, TOM_LO, FLOOR_HI), 0.25, 88, 110)

    # 45 : thirty-second bursts against the groove
    hit(45, 0.0, KICK, 108, 0.12, "RF", "down")
    roll(45, 0.0, 1.0, 0.125, 92, 104)
    hit(45, 1.0, SNARE, 116, 0.10, "LH", "accent")
    hit(45, 1.0, KICK, 100, 0.12, "RF", "normal")
    hit(45, 1.5, HAT, 66, 0.05, "RH", "normal")
    hit(45, 2.0, KICK, 104, 0.12, "RF", "down")
    roll(45, 2.0, 1.0, 0.125, 90, 100)
    hit(45, 3.0, SNARE, 112, 0.10, "LH", "accent")
    hit(45, 3.5, HAT, 68, 0.05, "RH", "normal")
    hit(45, 3.75, SNARE, 44, 0.06, "LH", "ghost")

    # 46 : doubles travel
    hit(46, 0.0, KICK, 104, 0.12, "RF", "down")
    hit(46, 2.0, KICK, 102, 0.12, "RF", "down")
    for i, d in enumerate((SNARE, TOM_HI, TOM_LOMID, TOM_LO)):
        hit(46, float(i), d, 98 - 4 * i, 0.09, "RH", "accent")
        hit(46, i + 0.25, d, 56, 0.07, "LH", "normal")
        hit(46, i + 0.5, d, 62, 0.07, "RH", "normal")

    # 47 : rim and snare talk
    hit(47, 0.0, KICK, 106, 0.12, "RF", "down")
    for j, (off, d, v) in enumerate(((0.0, RIM, 86), (0.5, SNARE, 104),
                                     (1.0, RIM, 80), (1.5, SNARE, 100),
                                     (2.0, RIM, 84), (2.5, SNARE, 108),
                                     (3.0, RIM, 78), (3.25, SNARE, 96))):
        add(bb(47) + off, d, v, 0.08, "LH" if j % 2 == 0 else "RH", "accent")
    roll(47, 3.5, 0.5, 0.125, 84, 104)

    # 48 : big fill
    tom_run(48, 0.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO), 0.25, 84, 96)
    tom_run(48, 1.0, (FLOOR_HI, FLOOR_LO, FLOOR_HI, TOM_LO), 0.25, 90, 104)
    tom_run(48, 2.0, DOWN_TOMS, 0.125, 92, 108)
    tom_run(48, 3.0, UP_TOMS, 0.125, 100, 118)

    # 49-50 : motif returns, now with answers
    hit(49, 0.0, CRASH2, 114, 1.8, "LH", "cym")
    hit(49, 0.0, KICK, 110, 0.12, "RF", "down")
    groove(49, vel=1.08, cym="ride", ghost=1, bell=True)
    hit(50, 0.0, KICK, 108, 0.12, "RF", "down")
    hit(50, 1.0, SNARE, 110, 0.10, "LH", "accent")
    tom_run(50, 1.5, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO), 0.25, 76, 92)
    hit(50, 2.5, KICK, 104, 0.12, "RF", "normal")
    hit(50, 3.0, SNARE, 108, 0.10, "LH", "accent")
    tom_run(50, 3.5, (FLOOR_HI, FLOOR_LO), 0.25, 80, 92)

    # 51 : one long run round the kit
    tom_run(51, 0.0, (SNARE, TOM_HI, TOM_HIMID, TOM_LOMID,
                      TOM_LO, FLOOR_HI, FLOOR_LO, SNARE,
                      TOM_HI, TOM_LOMID, TOM_LO, FLOOR_HI,
                      TOM_HIMID, TOM_LO, FLOOR_LO, SNARE), 0.25, 76, 104)

    # 52 : the biggest tumble so far
    hit(52, 0.0, KICK, 110, 0.12, "RF", "down")
    hit(52, 2.0, KICK, 112, 0.12, "RF", "down")
    tom_run(52, 0.0, DOWN_TOMS, 0.125, 90, 104)
    tom_run(52, 1.0, DOWN_TOMS, 0.125, 96, 108)
    tom_run(52, 2.0, UP_TOMS, 0.125, 100, 112)
    tom_run(52, 3.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO), 0.125, 106, 122)
    hit(53, 0.0, CRASH1, 120, 2.0, "LH", "cym")
    hit(53, 0.0, KICK, 116, 0.12, "RF", "down")


# ============================================================== 7. CLIMAX ==
def sec_climax():
    groove(53, vel=1.10, cym="ride", ghost=0, bell=True, pedal=(1.0, 3.0))
    groove(54, vel=1.10, cym="ride", ghost=2, kick_extra=(0.25, 2.25))

    # 55 : hats and snare, full tilt
    groove(55, vel=1.08, cym="hat", ghost=1, skip_snare=(1.0, 3.0),
           skip_cym=(0.0,))
    hit(55, 0.0, CRASH2, 112, 1.6, "LH", "cym")
    hit(55, 1.0, SNARE, 116, 0.10, "LH", "accent")
    hit(55, 3.0, SNARE, 114, 0.10, "LH", "accent")

    # 56 : tumble out of the groove
    groove(56, vel=1.08, cym="hat", ghost=3, cut=2.5)
    tom_run(56, 2.0, DOWN_TOMS, 0.25, 88, 108)
    tom_run(56, 3.0, (FLOOR_LO, FLOOR_HI, TOM_LO, TOM_LOMID), 0.25, 96, 118)

    # 57-58 : statement again
    hit(57, 0.0, CRASH1, 118, 1.8, "LH", "cym")
    hit(57, 0.0, KICK, 112, 0.12, "RF", "down")
    groove(57, vel=1.10, cym="ride", ghost=1, bell=True)
    groove(58, vel=1.08, cym="ride", ghost=0, cut=2.0, skip_cym=(2.0,))
    linear(58, LIN_B, start=2.0, step=0.25, strong=96, weak=78)

    # 59 : singles with accents
    hit(59, 0.0, KICK, 108, 0.12, "RF", "down")
    hit(59, 2.0, KICK, 106, 0.12, "RF", "down")
    roll(59, 0.0, 3.0, 0.25, 76, 98)
    hit(59, 3.0, HAT_OPEN, 92, 0.6, "RH", "cym")
    hit(59, 3.0, SNARE, 104, 0.10, "LH", "accent")
    hit(59, 3.75, SNARE, 50, 0.06, "LH", "ghost")

    # 60 : fill
    tom_run(60, 0.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO), 0.25, 90, 102)
    tom_run(60, 1.0, DOWN_TOMS, 0.125, 94, 108)
    tom_run(60, 2.0, (FLOOR_LO, FLOOR_HI, TOM_LO, TOM_LOMID,
                      TOM_HIMID, TOM_HI, TOM_HIMID, TOM_HI), 0.25, 98, 112)
    hit(60, 3.5, KICK, 110, 0.12, "RF", "normal")

    # 61-62 : the motif in half time, enormous, crashing on every downbeat
    for bar, d1, d2 in ((61, TOM_HI, TOM_LO), (62, TOM_HIMID, FLOOR_HI)):
        hit(bar, 0.0, CRASH1 if bar == 61 else CRASH2, 118, 2.0, "LH", "cym")
        hit(bar, 0.0, KICK, 114, 0.12, "RF", "down")
        hit(bar, 1.0, d1, 110, 0.14, "RH", "accent")
        hit(bar, 2.0, KICK, 104, 0.12, "RF", "down")
        hit(bar, 2.0, SNARE, 112, 0.10, "LH", "accent")
        hit(bar, 3.0, d2, 106, 0.14, "RH", "accent")
        hit(bar, 3.5, KICK, 96, 0.10, "RF", "normal")
        hit(bar, 3.75, SNARE, 46, 0.06, "LH", "ghost")

    # 63 : accel
    hit(63, 0.0, KICK, 110, 0.12, "RF", "down")
    hit(63, 2.0, KICK, 112, 0.12, "RF", "down")
    roll(63, 0.0, 2.0, 0.25, 80, 92)
    roll(63, 2.0, 2.0, 0.125, 92, 112)

    # 64 : the last big tumble
    tom_run(64, 0.0, DOWN_TOMS, 0.125, 100, 110)
    tom_run(64, 1.0, UP_TOMS, 0.125, 104, 112)
    tom_run(64, 2.0, DOWN_TOMS, 0.125, 108, 116)
    tom_run(64, 3.0, (TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO,
                      FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO), 0.125, 112, 124)


# =============================================================== 8. FINAL ==
def sec_final():
    # 65 : the motif, half time and singing
    hit(65, 0.0, CRASH1, 120, 2.0, "LH", "cym")
    hit(65, 0.0, KICK, 116, 0.12, "RF", "down")
    hit(65, 1.0, SNARE, 112, 0.10, "LH", "accent")
    hit(65, 2.0, KICK, 104, 0.12, "RF", "down")
    hit(65, 2.5, SNARE, 46, 0.06, "LH", "ghost")
    hit(65, 3.0, SNARE, 110, 0.10, "LH", "accent")
    hit(65, 3.5, KICK, 92, 0.12, "RF", "normal")
    hat_bar(65, vel=58, accent=8, skip=(0.0,))

    # 66 : same shape, new detail
    hit(66, 0.0, KICK, 108, 0.12, "RF", "down")
    hit(66, 1.0, SNARE, 112, 0.10, "LH", "accent")
    hit(66, 2.0, KICK, 100, 0.12, "RF", "down")
    hit(66, 2.75, SNARE, 40, 0.06, "LH", "ghost")
    hit(66, 3.0, SNARE, 108, 0.10, "LH", "accent")
    hat_bar(66, vel=56, accent=8)
    hit(66, 3.5, HAT_OPEN, 84, 0.5, "RH", "cym")

    # 67 : last crescendo
    hit(67, 0.0, KICK, 106, 0.12, "RF", "down")
    hit(67, 2.0, KICK, 108, 0.12, "RF", "down")
    roll(67, 0.0, 2.0, 0.25, 60, 84)
    roll(67, 2.0, 2.0, 0.125, 88, 120)

    # 68 : land it - four limbs, then the last punch
    hit(68, 0.0, CRASH1, 124, 2.0, "RH", "cym")
    hit(68, 0.0, CRASH2, 118, 2.0, "LH", "cym")
    hit(68, 0.0, KICK, 122, 0.12, "RF", "down")
    hit(68, 0.0, HAT_PED, 96, 0.07, "LF", "normal")
    hit(68, 1.5, SNARE, 118, 0.10, "LH", "accent")
    hit(68, 1.5, KICK, 112, 0.12, "RF", "normal")
    hit(68, 2.0, CRASH2, 116, 2.0, "RH", "cym")
    hit(68, 2.0, KICK, 118, 0.12, "RF", "down")
    hit(68, 2.0, HAT_PED, 88, 0.07, "LF", "normal")


# ==================================================== performance shaping ===
def humanize(notes):
    out = []
    for n in notes:
        t = n["t"]
        kind = n["kind"]
        if kind == "down":
            sig, lay, sw = 1.7, 0.0, 0.0
        elif kind == "accent":
            sig, lay, sw = 2.4, 3.0, 0.10
        elif kind == "ghost":
            sig, lay, sw = 5.2, 5.0, 0.55
        elif kind == "roll":
            sig, lay, sw = 2.0, 0.0, 0.0
        elif kind == "cym":
            sig, lay, sw = 2.2, 0.0, 0.0
        else:
            sig, lay, sw = 3.4, 1.0, 0.30

        feel = feel_at(t) + 2.0 * math.sin(2.0 * math.pi * t / 16.0)
        jit = rng.gauss(0.0, sig)
        swing = 0.0
        if sw and ((t * 4.0) % 2.0) > 0.5:
            swing = sw * 9.0
        tick = int(round(t * PPQ + feel + lay + jit + swing))
        if tick < 0:
            tick = 0
        vel = n["vel"] + rng.gauss(0.0, 2.0 if kind == "ghost" else 3.0)
        out.append({"tick": tick,
                    "note": n["note"],
                    "vel": int(max(1, min(127, round(vel)))),
                    "dur": max(10, int(round(n["dur"] * PPQ))),
                    "limb": n["limb"]})
    return out


def resolve(notes):
    """No limb strikes twice faster than a human hand or foot can."""
    out = []
    for limb, gap in (("RH", 0.055), ("LH", 0.055), ("RF", 0.09), ("LF", 0.09)):
        kept = []
        for n in sorted((x for x in notes if x["limb"] == limb),
                        key=lambda x: x["tick"]):
            if kept and n["tick"] - kept[-1]["tick"] < gap * PPQ:
                if n["vel"] > kept[-1]["vel"]:
                    kept[-1] = n
                continue
            kept.append(n)
        out.extend(kept)
    return out


def clamp_overlaps(notes):
    """A drum can't be re-struck while its previous note is still sounding."""
    last = {}
    for n in sorted(notes, key=lambda x: x["tick"]):
        p = n["note"]
        prev = last.get(p)
        if prev is not None and prev["tick"] + prev["dur"] > n["tick"]:
            prev["dur"] = max(10, n["tick"] - prev["tick"] - 1)
        last[p] = n


# ================================================================ MIDI out ==
def write_midi(path, notes, scale):
    raw = []
    for bar in range(1, LAST_BAR + 1):
        raw.append(((bar - 1) * 4 * PPQ, 0,
                    ("tempo", tempo_at_bar(bar) * scale)))
    for n in notes:
        raw.append((n["tick"], 2, ("on", n["note"], n["vel"])))
        raw.append((n["tick"] + n["dur"], 1, ("off", n["note"])))
    raw.sort(key=lambda e: (e[0], e[1]))

    mid = MidiFile(type=1, ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("track_name", name="Drum Solo", time=0))
    track.append(MetaMessage("text", text="solo drum kit, GM channel 10", time=0))

    prev = 0
    for tick, kind, data in raw:
        delta = tick - prev
        if delta < 0:
            delta = 0
        prev = tick
        if kind == 0:
            track.append(MetaMessage("set_tempo",
                                     tempo=bpm2tempo(data[1]), time=delta))
        elif kind == 2:
            track.append(Message("note_on", channel=9, note=data[1],
                                 velocity=data[2], time=delta))
        else:
            track.append(Message("note_off", channel=9, note=data[1],
                                 velocity=0, time=delta))
    track.append(MetaMessage("end_of_track", time=0))
    mid.save(path)


def main():
    sec_intro()
    sec_travel()
    sec_melodic()
    sec_breakdown()
    sec_build()
    sec_runs()
    sec_climax()
    sec_final()

    notes = resolve(humanize(NOTES))
    clamp_overlaps(notes)
    notes.sort(key=lambda n: (n["tick"], n["note"]))

    end_beat = max((n["tick"] + n["dur"]) for n in notes) / float(PPQ)
    scale = beat_to_sec(end_beat) / TOTAL_SECONDS

    write_midi("solo.mid", notes, scale)


if __name__ == "__main__":
    main()
