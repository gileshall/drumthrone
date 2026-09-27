#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid, a two-minute General MIDI drum solo on channel 10.

Motif A (one bar of sixteenths): three tresillo accents (3+3+2), a four-note run down
the toms, and a floor-tom landing on beat four.  The solo states it, answers it, ghosts
it, inverts it, whispers it, displaces it, compresses it, stretches it, sets it in
sextuplets, hides it in the feet and the hi-hats, and finally lands on its last note.

  I    bars 0-7    Statement and answers, a first roll, a paradiddle fill.
  II   bars 8-15   Foot ostinato on the tresillo; cowbell and timbale colour; linear
                   R-L-K groups drifting over the bar line; paradiddle-diddles; the motif
                   in diminution; Bonham triplets.
  III  bars 16-23  Triplet fire: sextuplet motif, 4:3 and 5:6 groupings, double-stroke
                   roll from a whisper into the crash.
  IV   bars 24-31  Breakdown: side stick and wood blocks, swung ghost notes, a funk groove
                   with the tresillo in the open hats, a long crescendo.
  V    bars 32-41  Build: five-note linear groups, cymbal motif, 32nd bursts, displaced
                   diminution over the bar line, double bass enters.
  VI   bars 42-49  Climax: accents in threes over double bass, heavy sextuplet motif,
                   call and response, 3-3-2 accents inside 32nds, RLRLKK around the kit.
  VII  bars 50-54  Finale: motif augmented, motif as first stated but huge, a single-
                   stroke swell, the tresillo stabs and the landing as the final hit.

Timing lives in a tempo map (the pulse surges and settles) plus per-note micro-timing.
Every note is assigned to a limb (R, L hands; RF, LF feet) and a playability pass keeps
each limb to one stroke at a time, so at most two hands and two feet strike at once.
Everything is seeded, so solo.mid is identical on every run.
"""

import math
import random

import mido

PPQ = 960
CHANNEL = 9                 # MIDI channel 10
SEED = 1964
LEAD = 0.5                  # beats before the first stroke (room for the first flam)
TARGET_FINAL_SEC = 116.6    # final hit lands here
RING_SEC = 3.4              # let it ring, then the file ends (~120 s total)
SEG = 0.5                   # tempo-map resolution in beats

# General MIDI percussion
KICK_B, KICK, SIDE, SNARE = 35, 36, 37, 38
TOM_LF, HH_C, TOM_HF, HH_P, TOM_L, HH_O = 41, 42, 43, 44, 45, 46
TOM_LM, TOM_HM, CRASH, TOM_H, RIDE, CHINA, BELL = 47, 48, 49, 50, 51, 52, 53
SPLASH, COWBELL, CRASH2 = 55, 56, 57
TIMB_H, TIMB_L = 65, 66
BLOCK_H, BLOCK_L = 76, 77

KIT = [SNARE, TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_HF, TOM_LF]   # index 0..6, high to low
LOUD = (CRASH, CRASH2, CHINA, SPLASH)
FEET_NOTES = (KICK_B, KICK, HH_P)

HAND_MAP = {
    's': SNARE, 'g': SNARE, 'x': SIDE,
    '1': TOM_H, '2': TOM_HM, '3': TOM_LM, '4': TOM_L, '5': TOM_HF, '6': TOM_LF,
    'h': HH_C, 'o': HH_O, 'r': RIDE, 'b': BELL, 'w': COWBELL,
    'c': CRASH, 'v': CRASH2, 'z': CHINA, 'p': SPLASH,
    't': TIMB_H, 'u': TIMB_L, 'k': BLOCK_H, 'l': BLOCK_L,
}

# (bar, bpm) anchors; smoothstep between them.  Scaled globally to hit the target length.
TEMPO_ANCHORS = [
    (0.0, 104), (3.5, 107), (4.0, 108), (7.9, 111), (8.0, 110), (12.0, 113), (15.9, 116),
    (16.0, 116), (19.9, 119), (20.0, 118), (23.9, 121), (24.2, 110), (26.0, 105), (28.0, 107),
    (30.0, 109), (31.9, 114), (32.0, 114), (35.9, 118), (36.0, 118), (39.9, 121), (40.0, 122),
    (43.9, 125), (44.0, 125), (48.0, 128), (49.9, 129), (50.0, 126), (51.9, 121), (52.0, 122),
    (53.0, 123), (53.95, 126), (54.0, 120), (54.55, 112), (54.75, 106), (60.0, 106),
]


class Note:
    __slots__ = ('t', 'pitch', 'vel', 'limb', 'pri', 'ms', 'dur', 'tick', 'off', 'sec')

    def __init__(self, t, pitch, vel, limb, pri, ms, dur):
        self.t = t
        self.pitch = pitch
        self.vel = vel
        self.limb = limb
        self.pri = pri
        self.ms = ms
        self.dur = dur
        self.tick = 0
        self.off = 0
        self.sec = 0.0


def route_at(route, x):
    if len(route) == 1:
        return route[0]
    x = min(1.0, max(0.0, x))
    p = x * (len(route) - 1)
    a = int(p)
    if a >= len(route) - 1:
        return route[-1]
    f = p - a
    return int(round(route[a] + (route[a + 1] - route[a]) * f))


def _is_acc(acc, i):
    if acc is None:
        return False
    if isinstance(acc, str):
        return acc[i % len(acc)] == '>'
    return i in acc


def _level(a, base, ghost, accamt):
    if a == ',':
        return ghost, 0
    if a == '~':
        return base * 0.72, 1
    if a == '>':
        return base + accamt, 2
    if a == '^':
        return base + accamt + 12, 3
    return base, 1


def gesture_value(g, mb):
    b0, b1, amt, kind = g
    if mb < b0 or mb >= b1:
        return 0.0
    x = (mb - b0) / (b1 - b0)
    if kind == 'ramp':
        return amt * (x / 0.8 if x < 0.8 else (1.0 - x) / 0.2)
    return amt * math.sin(math.pi * x)


def base_bpm(mb):
    bar = mb / 4.0
    A = TEMPO_ANCHORS
    if bar <= A[0][0]:
        return float(A[0][1])
    for (b0, v0), (b1, v1) in zip(A, A[1:]):
        if bar <= b1:
            x = (bar - b0) / (b1 - b0)
            x = x * x * (3.0 - 2.0 * x)
            return v0 + (v1 - v0) * x
    return float(A[-1][1])


def desired_dur_sec(p):
    if p in (CRASH, CRASH2, CHINA):
        return 3.0
    if p == SPLASH:
        return 1.6
    if p in (RIDE, BELL):
        return 1.5
    if p == HH_O:
        return 0.8
    if p in (HH_C, HH_P):
        return 0.25
    return 0.9


class Solo:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.notes = []
        self.gest = []

    # ---- primitive strokes -------------------------------------------------
    def hit(self, t, pitch, vel, limb, pri=1, ms=0.0, dur=None):
        vel = max(1, min(127, int(round(vel))))
        self.notes.append(Note(t, pitch, vel, limb, pri, ms, dur))

    def kick(self, t, vel, foot='RF', ms=0.0, pitch=KICK):
        self.hit(t, pitch, vel, foot, 2, ms)

    def pedal(self, t, vel, ms=0.0):
        self.hit(t, HH_P, vel, 'LF', 1, ms)

    def cym(self, t, pitch, vel, hand='R', ms=0.0, dur=None):
        self.hit(t, pitch, vel, hand, 4, ms, dur)

    def flam(self, t, pitch, vel, hand='R', ms=0.0):
        other = 'L' if hand == 'R' else 'R'
        self.hit(t, pitch, vel * self.rng.uniform(0.32, 0.42), other, 0,
                 ms - self.rng.uniform(26.0, 34.0))
        self.hit(t, pitch, vel, hand, 3, ms)

    # ---- tempo gestures ----------------------------------------------------
    def push(self, b0, b1, amt):
        self.gest.append((b0, b1, amt, 'ramp'))

    def bump(self, b0, b1, amt):
        self.gest.append((b0, b1, amt, 'bump'))

    # ---- drum-tab style bar -----------------------------------------------
    def tab(self, t0, sub, hands='', acc='', stick='', cym='', cstick='', kick='', hat='',
            dyn=80, cresc=(1.0, 1.0), ghost=30, accamt=24, flams='', rush=0.0, swing=0.0,
            start='R'):
        n = max(len(hands), len(cym), len(kick), len(hat), 1)

        def tt(i):
            return t0 + (i + (swing if i % 2 == 1 else 0.0)) / float(sub)

        def msf(i):
            return -rush * i / float(max(1, n - 1))

        def sc(i):
            return cresc[0] + (cresc[1] - cresc[0]) * i / float(max(1, n - 1))

        auto = start
        used = {}
        for i, ch in enumerate(hands):
            if ch in '. ':
                continue
            if i < len(stick) and stick[i] in 'RL':
                h = stick[i]
            else:
                h = auto
            auto = 'L' if h == 'R' else 'R'
            used[i] = h
            pitch = HAND_MAP[ch.lower()]
            a = acc[i] if i < len(acc) else '.'
            if a in '. ':
                a = ',' if ch == 'g' else ('>' if ch.isupper() else '-')
            v, pri = _level(a, dyn * sc(i), ghost, accamt)
            if i < len(flams) and flams[i] == 'f':
                self.flam(tt(i), pitch, v, h, ms=msf(i))
            else:
                self.hit(tt(i), pitch, v, h, pri, msf(i))
        for i, ch in enumerate(cym):
            if ch in '. ':
                continue
            if i < len(cstick) and cstick[i] in 'RL':
                h = cstick[i]
            elif i in used:
                h = 'L' if used[i] == 'R' else 'R'
            else:
                h = 'R'
            pitch = HAND_MAP[ch.lower()]
            base = dyn * sc(i)
            loud = pitch in LOUD
            if ch.isupper():
                v = base + accamt + (6 if loud else 0)
            else:
                v = base + (12 if loud else -4)
            self.hit(tt(i), pitch, v, h, 4 if loud else 2, msf(i))
        for i, ch in enumerate(kick):
            if ch in '. ':
                continue
            foot = 'LF' if ch in 'fF' else 'RF'
            v = dyn * sc(i) + (14 if ch.isupper() else -6)
            self.kick(tt(i), v, foot, msf(i))
        for i, ch in enumerate(hat):
            if ch in '. ':
                continue
            self.pedal(tt(i), 70 if ch.isupper() else 50, msf(i))

    # ---- flowing sticking phrase around the kit -----------------------------
    def phrase(self, t0, n, sub, stick, route, v0, v1, accents=None, mode='follow', per=1,
               ghost=30, accamt=20, kickv=None, rush=0.0, curve=1.0):
        step = 1.0 / sub
        L = len(stick)
        hands = [i for i in range(n) if stick[i % L] in 'RL']
        nh = len(hands)
        denom = max(1, nh - per)
        pos = {}
        for j, i in enumerate(hands):
            q = (j // per) * per
            pos[i] = route_at(route, q / float(denom))
        prev = None
        for i in range(n):
            s = stick[i % L]
            t = t0 + i * step
            x = i / float(max(1, n - 1))
            ms = -rush * x
            base = v0 + (v1 - v0) * (x ** curve)
            acc = _is_acc(accents, i)
            if s in 'KF':
                kv = kickv if kickv is not None else base * 0.92
                self.kick(t, kv + (8 if acc else 0), 'RF' if s == 'K' else 'LF', ms)
                prev = s
                continue
            drum = KIT[pos[i]]
            if acc:
                v, pri = base + accamt, 2
            elif mode == 'split' or (mode == 'semi' and s == 'L'):
                drum, v, pri = SNARE, ghost + (base - v0) * 0.22, 0
            else:
                v, pri = base, 1
                if prev == s:
                    v *= 0.9
            self.hit(t, drum, v, s, pri, ms)
            prev = s

    # ---- rolls --------------------------------------------------------------
    def roll(self, t0, beats, v0, v1, drums=(SNARE,), sub=8, kind='double', curve=1.7,
             start='R', rush=0.0):
        n = int(round(beats * sub))
        other = 'L' if start == 'R' else 'R'
        for i in range(n):
            if kind == 'double':
                h = start if (i // 2) % 2 == 0 else other
            else:
                h = start if i % 2 == 0 else other
            x = i / float(max(1, n - 1))
            v = v0 + (v1 - v0) * (x ** curve)
            if kind == 'double' and i % 2 == 1:
                v *= 0.9
            d = drums[min(len(drums) - 1, int(x * len(drums)))]
            self.hit(t0 + i / float(sub), d, v, h, 1, -rush * x)

    # ---- the motif ------------------------------------------------------------
    def motif_a(self, t0, u=0.25, top=(SNARE, SNARE, SNARE), th=('R', 'L', 'R'),
                run=(TOM_H, TOM_HM, TOM_L, TOM_HF), land=TOM_LF, dyn=84, accamt=24,
                cyms=None, land_cym=None, flam=False, ghosts=False,
                kicks=((0, 1.0), (6, 0.8), (12, 1.0), (14, 0.7)), runsub=1, tail=False,
                ghost=28, pedal=True, cresc=8.0, rush=0.0):
        def T(s):
            return t0 + s * u

        for k, s in enumerate((0, 3, 6)):
            v = dyn + accamt + (4 if k == 0 else (-3 if k == 1 else 0))
            if cyms and cyms[k]:
                self.cym(T(s), cyms[k], v + 6, 'R')
                self.hit(T(s), top[k], v, 'L', 3)
            elif flam:
                self.flam(T(s), top[k], v, th[k])
            else:
                self.hit(T(s), top[k], v, th[k], 3)
        if ghosts and not cyms:
            for s, h in ((1, 'L'), (2, 'R'), (4, 'R'), (5, 'L'), (7, 'L')):
                self.hit(T(s), SNARE, ghost + self.rng.uniform(-3, 4), h, 0)
        nrun = 4 * runsub
        for i in range(nrun):
            h = 'R' if i % 2 == 0 else 'L'
            v = dyn - 4 + cresc * i / float(max(1, nrun - 1))
            self.hit(T(8) + i * u / runsub, run[i // runsub], v, h, 1, -rush * i / float(nrun))
        vl = dyn + accamt + 6
        self.hit(T(12), land, vl, 'R', 3)
        if land_cym:
            self.cym(T(12), land_cym, vl + 4, 'L')
        for s, f in kicks:
            self.kick(T(s), (dyn + 12) * f)
        if pedal:
            self.pedal(T(4), 54)
            self.pedal(T(12), 54)
        if tail:
            for j, s in enumerate((13, 14, 15)):
                self.hit(T(s), SNARE, ghost + 6 * j, 'L' if s % 2 == 1 else 'R', 0)

    def motif_a6(self, t0, top=(SNARE, SNARE, SNARE),
                 run=(TOM_H, TOM_HM, TOM_LM, TOM_L, TOM_HF, TOM_LF), land=TOM_LF, dyn=90,
                 accamt=24, cyms=None, land_cym=None, ghosts=False,
                 kicks=((0, 1.0), (8, 0.85), (18, 1.0), (21, 0.7)), ghost=28, extra_kicks=()):
        def T(s):
            return t0 + s / 6.0

        for k, s in enumerate((0, 4, 8)):
            v = dyn + accamt + (3 if k == 0 else 0)
            if cyms and cyms[k]:
                self.cym(T(s), cyms[k], v + 6, 'R')
                self.hit(T(s), top[k], v, 'L', 3)
            else:
                self.hit(T(s), top[k], v, 'R', 3)
        if ghosts and not cyms:
            for s in (1, 2, 3, 5, 6, 7, 9, 10, 11):
                self.hit(T(s), SNARE, ghost + self.rng.uniform(-3, 5),
                         'R' if s % 2 == 0 else 'L', 0)
        for i, d in enumerate(run):
            self.hit(T(12 + i), d, dyn - 2 + 2.5 * i, 'R' if i % 2 == 0 else 'L', 1)
        self.hit(T(18), land, dyn + accamt + 6, 'R', 3)
        if land_cym:
            self.cym(T(18), land_cym, dyn + accamt + 8, 'L')
        for s, f in kicks:
            self.kick(T(s), (dyn + 12) * f)
        for s, f, foot in extra_kicks:
            self.kick(T(s), (dyn + 4) * f, foot)


def compose(S):
    r = S.rng

    def B(b):
        return 4.0 * b

    def pedal24(b, v=52):
        S.pedal(B(b) + 1.0, v)
        S.pedal(B(b) + 3.0, v)

    def feet_ost(b, var, dyn=76):
        ks = [(0, 12), (3, 0), (6, 4), (10, 0)]
        if var == 1:
            ks.append((14, -8))
        elif var == 2:
            ks.append((11, -10))
        elif var == 3:
            ks = [(0, 12), (3, 0), (6, 4), (8, -6), (10, 0), (13, -10), (15, -4)]
        for s, dv in ks:
            S.kick(B(b) + s / 4.0, dyn + dv + r.uniform(-3, 3))
        pedal24(b, 54)

    # ================= I. STATEMENT (bars 0-7) =================
    S.motif_a(B(0), dyn=80, flam=True)
    S.tab(B(1), 4,
          hands="..g6.g5..g42S.gg",
          acc="..,-.,>..,->>.,,",
          stick="..LR.LR..LRLR.LR",
          kick="K.......k.....k.",
          hat="....h.......h...", dyn=74)
    S.motif_a(B(2), dyn=82, ghosts=True, run=(TOM_H, TOM_HM, TOM_HM, TOM_L), tail=True)
    S.tab(B(3), 4, cym="B..b..b.", hands=".gg.gg.g", stick=".LL.LL.L",
          kick="k..k..k.", hat="....h...", dyn=74, ghost=27)
    S.phrase(B(3) + 2, 12, 6, "RL", [0, 1, 2, 4, 5, 6], 66, 100, accents=(0, 6), per=2, rush=5.0)
    S.kick(B(3) + 2, 76)
    S.kick(B(3) + 3, 88)
    S.pedal(B(3) + 3, 50)
    S.push(B(3) + 2, B(4), 0.03)
    S.motif_a(B(4), dyn=84, cyms=(CRASH, None, None), top=(SNARE, TOM_HF, TOM_LM),
              th=('R', 'R', 'L'), run=(TOM_L, TOM_LM, TOM_HM, TOM_H), land=SNARE)
    S.tab(B(5), 4, cym="h.h.h.o.h.h.", hands=".g.gS..g.g.g", stick="LLLLLLLLLLLL",
          kick="K..k....K.k.", dyn=72, ghost=28, swing=0.08)
    S.roll(B(5) + 3, 1.0, 34, 94, sub=8, kind='double', curve=1.5)
    S.kick(B(5) + 3.5, 58)
    S.motif_a(B(6), dyn=86, top=(SNARE, SNARE, TOM_H), runsub=2, tail=True)
    S.phrase(B(7), 12, 4, "RLRRLRLL", [1, 2, 3, 4], 62, 92, accents=">...", mode='semi', ghost=30)
    S.phrase(B(7) + 3, 6, 6, "RL", [5, 6], 94, 112, accents=(0,), per=3, rush=4.0)
    S.kick(B(7), 70)
    S.kick(B(7) + 2, 74)
    S.kick(B(7) + 3, 86)
    S.pedal(B(7) + 1, 48)
    S.push(B(7), B(8), 0.035)

    # ================= II. OSTINATO AND COLOUR (bars 8-15) =================
    feet_ost(8, 0)
    S.tab(B(8), 4,
          cym="C.wWw.W.w.W.W.w.",
          hands=".g...g.S.g.1.g.2",
          acc="...........>...-",
          stick="LLLLLLLLLLLLLLLL", dyn=70, accamt=22, ghost=28)
    feet_ost(9, 1)
    S.tab(B(9), 4,
          cym="W.wW.wW.w.Ww.Ww.",
          hands=".gt..g2.g.u.g1.S",
          acc="..>...>...>..-..",
          stick="LLLLLLLLLLLLLLLL", dyn=70, accamt=22, ghost=28)
    # bars 10-11: linear R-L-K sixteenths, groups of three drifting across the bar line
    rp = {0: (BELL, True), 3: (BELL, False), 6: (BELL, False), 9: (TOM_H, True),
          12: (TOM_HM, False), 15: (TOM_L, False), 18: (TOM_HF, True), 21: (TOM_LF, False),
          24: (TOM_HF, True), 27: (TOM_L, False), 30: (TOM_HM, True)}
    for i in range(32):
        t = B(10) + i / 4.0
        x = i / 31.0
        base = 68 + 28 * x
        role = i % 3
        if role == 2:
            S.kick(t, base - 2 + r.uniform(-3, 3))
        elif role == 1:
            if i in (4, 28, 31):
                S.hit(t, SNARE, base + 22, 'L', 2)
            else:
                S.hit(t, SNARE, 28 + 12 * x + r.uniform(-3, 3), 'L', 0)
        else:
            p, a = rp[i]
            S.hit(t, p, base + (20 if a else 0) - (8 if p == BELL else 0), 'R', 2 if a else 1)
    for q in (1, 3, 5, 7):
        S.pedal(B(10) + q, 52)
    feet_ost(12, 2)
    feet_ost(13, 3)
    S.phrase(B(12), 32, 4, "RLRRLL", [1, 3, 5, 6, 4, 2, 1], 70, 100, accents=">.....",
             mode='semi', ghost=30, accamt=22)
    S.motif_a(B(14), u=0.125, dyn=90, cyms=(CRASH, None, None),
              kicks=((0, 1.0), (12, 1.0)), pedal=False)
    S.motif_a(B(14) + 2, u=0.125, dyn=92, top=(TOM_LF, TOM_HF, TOM_L), th=('R', 'R', 'L'),
              run=(TOM_L, TOM_LM, TOM_HM, TOM_H), land=SNARE, land_cym=CRASH2,
              kicks=((0, 1.0), (6, 0.8), (12, 1.0)), pedal=False)
    S.pedal(B(14) + 1, 50)
    S.pedal(B(14) + 3, 50)
    S.phrase(B(15), 18, 6, "RLK", [1, 2, 3, 4, 5, 6], 78, 100, accents=(0, 6, 12), per=2)
    S.phrase(B(15) + 3, 6, 6, "RL", [6, 5, 4, 2, 1, 0], 96, 114, accents=(5,), rush=4.0)
    S.pedal(B(15) + 1, 50)
    S.push(B(14) + 2, B(16), 0.03)

    # ================= III. TRIPLET FIRE (bars 16-23) =================
    S.cym(B(16), CRASH, 112, 'R')
    S.kick(B(16), 104)
    S.phrase(B(16), 24, 6, "RLK", [1, 3, 5, 6, 4, 2], 80, 98, accents=(0, 6, 12, 18), per=2)
    for q in range(4):
        S.pedal(B(16) + q, 46)
    S.cym(B(17), SPLASH, 100, 'R')
    S.phrase(B(17), 24, 6, "RLRLKF", [1, 3, 5, 6, 5, 3, 1, 0], 84, 108,
             accents=(0, 6, 12, 18), per=2)
    S.motif_a6(B(18), dyn=90, cyms=(CRASH, SPLASH, CRASH2),
               kicks=((0, 1.0), (4, 0.8), (8, 0.9), (18, 1.0), (21, 0.7)))
    S.pedal(B(18) + 1, 50)
    for j, s in enumerate((20, 22, 23)):
        S.hit(B(18) + s / 6.0, SNARE, 34 + 12 * j, 'L' if s % 2 else 'R', 0)
    S.phrase(B(19), 24, 6, "RL", [1, 2, 4, 5, 6, 5, 3, 1], 66, 102, accents=">...",
             mode='split', ghost=32, accamt=24)
    for q in range(4):
        S.kick(B(19) + q, 84 + 4 * q)
        S.pedal(B(19) + q + 0.5, 44)
    S.phrase(B(20), 48, 6, "RLRLK", [1, 2, 3, 4, 5, 6, 4, 2, 1, 3, 5, 6], 66, 108,
             accents=">....", mode='semi', ghost=32, accamt=22)
    for q in (1, 3, 5, 7):
        S.pedal(B(20) + q, 48)
    S.push(B(21), B(22), 0.03)
    S.cym(B(22), CRASH2, 116, 'L')
    S.motif_a6(B(22), dyn=88, top=(SNARE, TOM_H, TOM_HM), ghosts=True)
    S.pedal(B(22) + 1, 46)
    S.roll(B(23), 3.0, 26, 100, sub=8, kind='double', curve=1.8)
    S.phrase(B(23) + 3, 8, 8, "RL", [1, 6], 104, 122, rush=4.0)
    for q in range(8):
        S.kick(B(23) + q / 2.0, 40 + 10 * q)
    S.push(B(23), B(24), 0.04)

    # ================= IV. BREAKDOWN (bars 24-31) =================
    S.cym(B(24), CRASH, 124, 'R')
    S.cym(B(24), CRASH2, 118, 'L')
    S.kick(B(24), 118)
    for q in (1, 2, 3):
        S.pedal(B(24) + q, 40 + 2 * q)
    S.kick(B(24) + 2.5, 38)
    for j, s in enumerate((13, 14, 15)):
        S.hit(B(24) + s / 4.0, SNARE, 24 + 5 * j, 'R' if j % 2 == 0 else 'L', 0)
    S.motif_a(B(25), dyn=56, accamt=16, top=(SIDE, SIDE, SIDE),
              run=(BLOCK_H, BLOCK_H, BLOCK_L, BLOCK_L), land=TOM_LF,
              kicks=((0, 0.8), (12, 0.9)), cresc=4.0)
    mel = {2: (TOM_L, 60), 6: (TOM_HM, 64), 10: (TOM_H, 66), 12: (TOM_HF, 62), 14: (TOM_LF, 70)}
    for i in range(16):
        h = 'R' if i % 2 == 0 else 'L'
        t = B(26) + (i + (0.12 if i % 2 == 1 else 0.0)) / 4.0
        if i in mel:
            p, v = mel[i]
            S.hit(t, p, v, 'R', 2)
        else:
            gv = 22 + 4 * math.sin(i * 0.9) + (7 if i in (4, 8) else 0)
            S.hit(t, SNARE, gv, h, 0)
    S.kick(B(26), 52)
    S.kick(B(26) + 2.0, 46)
    S.kick(B(26) + 3.5, 50)
    pedal24(26, 48)
    S.motif_a(B(27) + 0.5, dyn=62, accamt=18, top=(SIDE, SIDE, SIDE),
              run=(BLOCK_H, BLOCK_L, TOM_L, TOM_HF), land=TOM_LF,
              kicks=((0, 0.8), (12, 0.95)), pedal=False, flam=True, cresc=6.0)
    S.hit(B(27) + 3.75, SNARE, 30, 'L', 0)
    pedal24(27, 50)
    S.bump(B(25), B(28), -0.02)
    S.tab(B(28), 4,
          cym="H.hO.hO.h.h.h.h.",
          hands=".g..S..g.g..S.gg",
          stick="LLLLLLLLLLLLLLLL",
          kick="K.k....k..K..k..", dyn=70, ghost=27, swing=0.1)
    S.tab(B(29), 4,
          cym="H.h.hOh.H.hO",
          hands="..g.S..g.gg.",
          stick="LLLLLLLLLLLL",
          kick="K...k..K..k.",
          hat="............H", dyn=72, ghost=28, swing=0.1)
    S.phrase(B(29) + 3, 8, 8, "RL", [0, 0, 1, 2], 40, 96, accents=(7,), curve=1.3)
    S.phrase(B(30), 28, 4, "RL", [6, 5, 4, 3, 2, 1], 52, 104, accents=">..", mode='split',
             ghost=30, accamt=22, curve=1.2)
    S.phrase(B(31) + 3, 6, 6, "RL", [1, 2, 4, 6], 104, 118, accents=(0,), rush=4.0)
    for q in range(8):
        S.kick(B(30) + q, 56 + 6 * q)
    for q in (1, 3, 5):
        S.pedal(B(30) + q, 46)
    S.push(B(30), B(32), 0.035)

    # ================= V. BUILD (bars 32-41) =================
    S.cym(B(32), CRASH, 114, 'R')
    S.kick(B(32), 106)
    S.phrase(B(32), 32, 4, "RLRLK", [1, 3, 5, 6, 4, 2, 1, 2, 4, 6], 72, 102, accents=">....",
             mode='semi', ghost=32, accamt=22)
    for q in (1, 3, 5, 7):
        S.pedal(B(32) + q, 48)
    S.push(B(33), B(34), 0.025)
    S.motif_a(B(34), dyn=94, accamt=22, cyms=(CRASH, SPLASH, CHINA), runsub=2, land_cym=CRASH2,
              kicks=((0, 1.0), (3, 0.9), (6, 1.0), (12, 1.0), (14, 0.7)))
    S.phrase(B(35), 16, 8, "RL", [0, 1, 2, 3, 4, 5, 6], 80, 108, accents=(0, 8), per=2)
    S.hit(B(35) + 2, TOM_LF, 116, 'R', 3)
    S.hit(B(35) + 2, TOM_HF, 110, 'L', 3)
    S.kick(B(35) + 2, 112)
    S.kick(B(35) + 2.75, 76)
    S.flam(B(35) + 3, SNARE, 104, 'R')
    S.kick(B(35) + 3, 90)
    S.hit(B(35) + 3.5, TOM_H, 88, 'R', 2)
    S.hit(B(35) + 3.75, TOM_HM, 92, 'L', 2)
    S.pedal(B(35) + 1, 48)
    S.phrase(B(36), 24, 6, "RLRRLL", [1, 2, 3, 4, 5, 6], 72, 96, accents=">.....",
             mode='semi', ghost=30)
    S.phrase(B(37), 18, 6, "RLRRLL", [6, 4, 2, 1, 0], 80, 104, accents=">...",
             mode='semi', ghost=32)
    S.phrase(B(37) + 3, 6, 6, "RLRLKF", [1, 3], 100, 116, accents=(0,))
    for q in range(8):
        S.kick(B(36) + q, 78 + 3 * q)
    for q in range(7):
        S.pedal(B(36) + q + 0.5, 44)
    S.push(B(37) + 2, B(38), 0.03)
    S.motif_a(B(38), u=0.125, dyn=94, accamt=20, cyms=(CRASH, None, None),
              kicks=((0, 1.0), (6, 0.8), (12, 1.0)), pedal=False)
    S.kick(B(38) + 1.75, 80)
    S.kick(B(38) + 1.875, 84, 'LF')
    # displaced diminution: lands on the next downbeat
    S.motif_a(B(38) + 2.5, u=0.125, dyn=96, accamt=20, top=(TOM_HF, TOM_L, TOM_HM),
              th=('R', 'L', 'R'), land=TOM_LF, land_cym=CRASH2,
              kicks=((0, 1.0), (12, 1.1)), pedal=False)
    S.phrase(B(39) + 0.5, 10, 4, "RRLL", [1, 2, 3, 4, 5], 74, 100, accents=(0, 4, 8), per=2)
    S.flam(B(39) + 3, TOM_LF, 108, 'R')
    S.kick(B(39) + 3, 96)
    S.kick(B(39) + 3.25, 84)
    S.flam(B(39) + 3.5, SNARE, 112, 'L')
    S.kick(B(39) + 3.75, 92)
    for i in range(32):
        S.kick(B(40) + i / 4.0, 76 + 14 * i / 31.0 + r.uniform(-3, 3), 'RF' if i % 2 == 0 else 'LF')
    S.motif_a(B(40), dyn=96, accamt=20, cyms=(CRASH, CHINA, CRASH), runsub=2,
              run=(TOM_LF, TOM_HF, TOM_L, TOM_HM), land=SNARE, land_cym=CRASH2,
              kicks=(), pedal=False, tail=True)
    S.phrase(B(41), 24, 6, "RL", [1, 2, 3, 4, 5, 6, 6, 5, 3, 1, 0], 84, 112, accents=">.....")
    S.push(B(41), B(42), 0.03)

    # ================= VI. CLIMAX (bars 42-49) =================
    for i in range(32):
        S.kick(B(42) + i / 4.0, 80 + 14 * i / 31.0 + r.uniform(-4, 4), 'RF' if i % 2 == 0 else 'LF')
    route = [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1, 0]
    racc = [CRASH, TOM_LF, CHINA, TOM_HF]
    lacc = [SNARE, CRASH2, SNARE, SPLASH]
    kr = 0
    kl = 0
    for i in range(32):
        h = 'R' if i % 2 == 0 else 'L'
        t = B(42) + i / 4.0
        x = i / 31.0
        if i % 3 == 0:
            if h == 'R':
                p = racc[kr % 4]
                kr += 1
            else:
                p = lacc[kl % 4]
                kl += 1
            if p in LOUD:
                S.cym(t, p, 104 + 16 * x, h)
            else:
                S.hit(t, p, 100 + 18 * x, h, 3)
        else:
            S.hit(t, KIT[route_at(route, x)], 70 + 22 * x + r.uniform(-4, 4), h, 1)
    S.motif_a6(B(44), dyn=96, accamt=20, cyms=(CHINA, CRASH, CRASH2), land_cym=CRASH,
               kicks=((0, 1.0), (4, 1.0), (8, 1.0), (18, 1.1)),
               extra_kicks=((2, 0.8, 'RF'), (3, 0.85, 'LF'), (6, 0.8, 'RF'), (7, 0.85, 'LF'),
                            (10, 0.8, 'RF'), (11, 0.85, 'LF'), (20, 0.8, 'RF'),
                            (21, 0.85, 'LF'), (22, 0.9, 'RF'), (23, 0.95, 'LF')))
    S.phrase(B(45), 16, 8, "RL", [1, 2, 3, 4, 5, 6], 88, 114, accents=(0, 4, 8, 12), per=2)
    S.cym(B(45) + 2, CRASH, 118, 'R')
    S.hit(B(45) + 2, SNARE, 112, 'L', 3)
    S.kick(B(45) + 2, 114)
    S.cym(B(45) + 2.5, CHINA, 116, 'R')
    S.kick(B(45) + 2.5, 110)
    S.hit(B(45) + 2.75, TOM_HF, 96, 'L', 2)
    S.flam(B(45) + 3, SNARE, 114, 'R')
    S.kick(B(45) + 3, 108)
    S.hit(B(45) + 3.5, TOM_LF, 104, 'R', 2)
    S.kick(B(45) + 3.5, 100)
    S.hit(B(45) + 3.75, TOM_HF, 108, 'L', 2)
    S.kick(B(45) + 3.75, 96, 'LF')
    S.push(B(45), B(46), 0.02)
    for s, c in ((0, CRASH), (3, CHINA), (6, CRASH)):
        S.cym(B(46) + s / 4.0, c, 120, 'R')
        S.hit(B(46) + s / 4.0, SNARE, 112, 'L', 3)
        S.kick(B(46) + s / 4.0, 116)
    S.kick(B(46) + 1.75, 88, 'LF')
    S.phrase(B(46) + 2, 16, 8, "RLRLRRLL", [0, 1, 2, 4, 5, 6], 86, 114, accents=">.......", per=2)
    for i in range(8):
        S.kick(B(46) + 2 + i / 4.0, 84 + 3 * i, 'RF' if i % 2 == 0 else 'LF')
    for j, d in enumerate((TOM_H, TOM_HM, TOM_L, TOM_HF)):
        hand = 'L' if j % 2 == 0 else 'R'
        t = B(47) + 0.5 * j
        S.flam(t, d, 104 + 4 * j, hand)
        S.hit(t + 0.25, d, 62 + 3 * j, hand, 1)
    for i in range(8):
        S.kick(B(47) + i / 4.0, 82 + 2 * i, 'RF' if i % 2 == 0 else 'LF')
    S.phrase(B(47) + 2, 12, 6, "RLRLKF", [1, 3, 5, 6], 96, 116, accents=(0, 6))
    for i in range(16):
        S.kick(B(48) + i / 4.0, 86 + 18 * i / 15.0 + r.uniform(-3, 3), 'RF' if i % 2 == 0 else 'LF')
    S.phrase(B(48), 32, 8, "RL", [0, 1, 2, 3, 4, 5, 6, 4, 2, 0], 80, 112, accents=">..>..>.",
             mode='split', ghost=38, accamt=22)
    S.phrase(B(49), 24, 6, "RLRLKF", [1, 2, 3, 4, 5, 6, 6], 92, 120, accents=(0, 6, 12, 18), per=2)
    S.push(B(49), B(50), 0.035)

    # ================= VII. FINALE (bars 50-54) =================
    S.motif_a(B(50), u=0.5, dyn=98, accamt=20, cyms=(CRASH, CHINA, CRASH), runsub=2,
              land_cym=CRASH2, kicks=((0, 1.0), (3, 1.0), (6, 1.0), (12, 1.05)),
              pedal=False, cresc=14.0)
    for a, b_ in ((0.25, 1.25), (1.75, 2.75), (3.25, 3.75)):
        cnt = int(round((b_ - a) * 4)) + 1
        for j in range(cnt):
            S.hit(B(50) + a + 0.25 * j, SNARE, 30 + 26.0 * j / max(1, cnt - 1),
                  'L' if j % 2 == 0 else 'R', 0)
    S.kick(B(50) + 3.5, 84)
    S.kick(B(50) + 3.75, 90, 'LF')
    S.phrase(B(51) + 3, 6, 6, "RL", [6, 5, 4, 2, 1, 0], 90, 116, accents=(5,), rush=3.0)
    S.kick(B(51) + 3, 96)
    S.kick(B(51) + 3.5, 100)
    S.bump(B(50), B(52), -0.015)
    S.motif_a(B(52), dyn=100, accamt=18, cyms=(CRASH, None, None), flam=True, runsub=2,
              land_cym=CHINA, kicks=((0, 1.0), (3, 0.9), (6, 1.0), (12, 1.05)), pedal=False)
    for i, s in enumerate((13, 14, 15)):
        S.kick(B(52) + s / 4.0, 90 + 5 * i, 'RF' if i % 2 == 0 else 'LF')
        S.hit(B(52) + s / 4.0, SNARE, 50 + 12 * i, 'L' if i % 2 == 0 else 'R', 1)
    S.roll(B(53), 2.0, 64, 100, sub=8, kind='single', curve=1.2)
    S.phrase(B(53) + 2, 16, 8, "RL", [1, 2, 3, 4, 5, 6], 100, 124, accents=(0, 8), per=2)
    for i in range(16):
        S.kick(B(53) + i / 4.0, 80 + 36 * i / 15.0, 'RF' if i % 2 == 0 else 'LF')
    S.push(B(53), B(54), 0.04)
    for s in (0, 3, 6):
        t = B(54) + s / 4.0
        S.cym(t, CRASH, 124, 'R')
        S.cym(t, CHINA, 118, 'L')
        S.kick(t, 124)
    S.kick(B(54) + 1.75, 96, 'LF')
    S.phrase(B(54) + 2, 8, 8, "RL", [1, 2, 4, 5], 100, 124, per=2)
    fin = B(54) + 3.0
    S.cym(fin, CRASH, 127, 'R', dur=RING_SEC - 0.1)
    S.cym(fin, CRASH2, 127, 'L', dur=RING_SEC - 0.1)
    S.kick(fin, 127, 'RF')
    S.kick(fin, 124, 'LF', pitch=KICK_B)
    return fin


def humanize(notes, seed):
    rng = random.Random(seed)
    last_beat = int(max(n.t for n in notes)) + 3
    drift = [rng.gauss(0.0, 2.2) for _ in range(last_beat + 2)]
    for n in notes:
        b = int(n.t)
        f = n.t - b
        slow = drift[b] * (1.0 - f) + drift[b + 1] * f
        grace = n.pri == 0 and n.ms < -15.0
        hand = n.limb in ('R', 'L')
        if grace:
            j = rng.gauss(0.0, 1.2)
        else:
            j = max(-12.0, min(12.0, rng.gauss(0.0, 4.2 if hand else 3.2)))
            if n.vel < 45:
                j += 3.0          # ghost notes sit back
            elif n.vel > 108:
                j -= 2.0          # big accents dig in early
        if n.limb == 'L':
            j += 1.2
        n.ms += j + slow
        if n.vel < 45:
            dv = rng.gauss(0.0, 2.5)
        else:
            dv = rng.gauss(0.0, 4.0) - (2.5 if n.limb == 'L' else 0.0)
        n.vel = max(1, min(127, int(round(n.vel + dv))))


def resolve(notes):
    kept = []
    for limb in ('R', 'L', 'RF', 'LF'):
        gap = 0.035 if limb in ('R', 'L') else 0.075
        lst = sorted((n for n in notes if n.limb == limb),
                     key=lambda n: (n.tick, -n.pri, -n.vel, n.pitch))
        out = []
        for n in lst:
            if out and n.sec - out[-1].sec < gap:
                o = out[-1]
                if (n.pri, n.vel) > (o.pri, o.vel):
                    out[-1] = n
                continue
            out.append(n)
        kept.extend(out)
    kept.sort(key=lambda n: (n.pitch, n.tick, -n.vel))
    uniq = []
    for n in kept:
        if uniq and uniq[-1].pitch == n.pitch and n.sec - uniq[-1].sec < 0.012:
            if n.vel > uniq[-1].vel:
                uniq[-1] = n
            continue
        uniq.append(n)
    uniq.sort(key=lambda n: (n.sec, n.pitch))
    # safety net: never more than two hand strokes or two foot strokes inside 25 ms
    final = []
    window = []
    for n in uniq:
        window = [m for m in window if n.sec - m.sec < 0.025]
        is_foot = n.pitch in FEET_NOTES
        same = [m for m in window if (m.pitch in FEET_NOTES) == is_foot]
        if len(same) >= 2:
            continue
        window.append(n)
        final.append(n)
    final.sort(key=lambda n: (n.tick, n.pitch))
    return final


def render(S, final_mb, path):
    brng = random.Random(SEED + 7)
    nblocks = int(final_mb // 8) + 8
    breath = [brng.uniform(-0.010, 0.016) for _ in range(nblocks)]

    def raw(mb):
        f = 1.0
        for g in S.gest:
            f += gesture_value(g, mb)
        blk = int(mb // 8)
        if 0 <= blk < nblocks:
            f += breath[blk] * math.sin(math.pi * ((mb % 8.0) / 8.0))
        return base_bpm(mb) * f

    final_fb = final_mb + LEAD
    nseg = int(final_fb / SEG) + 64
    bpms = [raw(max(0.0, (i + 0.5) * SEG - LEAD)) for i in range(nseg)]
    full = int(final_fb / SEG)
    sec = sum(SEG * 60.0 / bpms[i] for i in range(full))
    sec += (final_fb - full * SEG) * 60.0 / bpms[full]
    k = sec / TARGET_FINAL_SEC
    us = [int(round(60e6 / (b * k))) for b in bpms]
    seg_ticks = int(round(SEG * PPQ))
    cum = [0.0]
    for u in us:
        cum.append(cum[-1] + seg_ticks * u / 1e6 / PPQ)

    def seg_index(tick):
        return max(0, min(tick // seg_ticks, len(us) - 1))

    def sec_of(tick):
        i = seg_index(tick)
        return cum[i] + (tick - i * seg_ticks) * us[i] / 1e6 / PPQ

    for n in S.notes:
        fb = n.t + LEAD
        u = us[seg_index(int(fb * PPQ))]
        n.tick = max(0, int(round(fb * PPQ + n.ms * 1000.0 * PPQ / u)))
        n.sec = sec_of(n.tick)

    notes = resolve(S.notes)

    final_tick = int(round(final_fb * PPQ))
    end_sec = sec_of(final_tick) + RING_SEC
    end_tick = final_tick
    while sec_of(end_tick) < end_sec:
        end_tick += 8

    by_pitch = {}
    for n in notes:
        by_pitch.setdefault(n.pitch, []).append(n)
    for p in sorted(by_pitch):
        lst = sorted(by_pitch[p], key=lambda n: n.tick)
        for idx, a in enumerate(lst):
            nxt = lst[idx + 1] if idx + 1 < len(lst) else None
            ds = a.dur if a.dur else desired_dur_sec(p)
            u = us[seg_index(a.tick)]
            d = int(ds * 1e6 * PPQ / u)
            lim = (nxt.tick - 1) if nxt is not None else (end_tick - 1)
            lim = min(lim, end_tick - 1)
            a.off = max(a.tick + 1, min(a.tick + d, lim))

    track = mido.MidiTrack()
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                  clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    track.append(mido.Message('program_change', channel=CHANNEL, program=0, time=0))
    track.append(mido.Message('control_change', channel=CHANNEL, control=7, value=112, time=0))
    track.append(mido.Message('control_change', channel=CHANNEL, control=10, value=64, time=0))
    track.append(mido.Message('control_change', channel=CHANNEL, control=91, value=40, time=0))
    track.append(mido.Message('control_change', channel=CHANNEL, control=93, value=0, time=0))

    evs = []
    seq = 0
    prev_u = None
    for i, u in enumerate(us):
        tk = i * seg_ticks
        if tk >= end_tick:
            break
        if u == prev_u:
            continue
        prev_u = u
        evs.append((tk, 0, seq, mido.MetaMessage('set_tempo', tempo=u, time=0)))
        seq += 1
    for n in notes:
        evs.append((n.tick, 2, seq, mido.Message('note_on', channel=CHANNEL, note=n.pitch,
                                                 velocity=n.vel, time=0)))
        seq += 1
        evs.append((n.off, 1, seq, mido.Message('note_off', channel=CHANNEL, note=n.pitch,
                                                velocity=64, time=0)))
        seq += 1
    evs.sort(key=lambda e: (e[0], e[1], e[2]))
    last = 0
    for tk, _, _, msg in evs:
        msg.time = tk - last
        last = tk
        track.append(msg)
    track.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - last)))

    mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
    mid.tracks.append(track)
    mid.save(path)


def main():
    S = Solo(SEED)
    final_mb = compose(S)
    humanize(S.notes, SEED + 1)
    render(S, final_mb, 'solo.mid')


if __name__ == '__main__':
    main()
