#!/usr/bin/env python3
"""
drum_solo.py -- composes and performs a two-minute drum solo and writes it to
solo.mid (Standard MIDI File, General MIDI percussion on channel 10).

Form (54 bars of 4/4 plus the final hit, about 2:00):
  1-8    Theme      the call (a clave-like figure: low, high, mid, flam,
                    pickup, low) stated, answered, displaced, sequenced
  9-16   Snare talk the call in ghost-note language, threes, paradiddles,
                    Swiss triplets, space, a double-stroke roll that swells
 17-26   Travel     sixes, the call on toms, Bonham triplets, fives over the
                    barline, the call on cymbals, linear hi-hat barks
 27-34   12/8       bell patterns, the call in triplets, cowbell, 3-over-2,
                    timbales, a gear-shift fill
 35-40   Breakdown  one hit and air, the call whispered, its skeleton as a
                    woodblock clave, then a long single-stroke swell
 41-50   Climax     the call on cymbals over double bass, runs, sevens,
                    a stop, flurries between punches
 51-55   Home       the call returns as it began, the fastest run, a
                    broadening fill and the final hit

Every stroke belongs to a limb (R, L, RF, LF).  The performance model adds a
breathing tempo map, phrase-level rushing and holding back, per-limb
micro-timing and velocity humanisation, then enforces playability (per-limb
recovery times, never more than two hands and two feet at once).  All
randomness is seeded, so every run writes the same file.
"""

import math
import random
from bisect import bisect_left, bisect_right

import mido

OUTFILE = "solo.mid"
SEED = 8041975
PPQ = 960
CH = 9                 # MIDI channel 10
LEAD = 1.0             # beats of silence before bar 1
TARGET_FINAL = 117.3   # seconds: where the last hit lands
TAIL = 2.7             # seconds of ring after the last hit

# ---------------------------------------------------------------- GM kit ----
K1, K2 = 36, 35                  # bass drum 1 (right foot), acoustic bass drum (left foot)
SN, XS = 38, 37                  # acoustic snare, side stick
HHC, HHP, HHO = 42, 44, 46       # hi-hat closed / pedal / open
T1, T2, T3, T4, F1, F2 = 50, 48, 47, 45, 43, 41
CR1, CR2, CHN, SPL = 49, 57, 52, 55
RIDE, BELL = 51, 53
COW, WBH, WBL, TRI = 56, 76, 77, 81
TIMH, TIML = 65, 66

CRASHES = (CR1, CR2, CHN, SPL)
TOMS = (T1, T2, T3, T4, F1, F2)
HANDS = ('R', 'L')
FEET = ('RF', 'LF')
LIMBS = ('R', 'L', 'RF', 'LF')
PRIO = {'grace': 0, 'ghost': 1, 'hat': 2, 'tap': 3, 'kick': 4, 'acc': 5, 'crash': 6}

GAIN = {HHC: 0.84, HHP: 0.86, HHO: 0.86, RIDE: 0.84, BELL: 0.86, CR1: 0.95,
        CR2: 0.95, CHN: 0.86, SPL: 0.86, COW: 0.72, WBH: 0.74, WBL: 0.74,
        TRI: 0.56, XS: 0.92, TIMH: 0.86, TIML: 0.86}

# (bias ms, spread ms): accents sit, ghosts float, the kick leads the crash
TIMING = {'crash': (2.0, 2.2), 'acc': (1.0, 2.6), 'kick': (-1.2, 2.4),
          'tap': (0.0, 3.3), 'ghost': (1.8, 5.0), 'hat': (1.0, 3.2),
          'grace': (0.0, 0.0)}
LIMB_BIAS = {'R': 0.0, 'L': 1.3, 'RF': -0.6, 'LF': 0.9}

# the call: (16th position, role, dynamic, with kick)
MOTIF_A = [(0, 'LOW', 1.00, True), (3, 'SN', 0.86, False), (6, 'MID', 0.93, True),
           (10, 'FLAM', 0.95, False), (12, 'K', 0.76, True), (13, 'HI', 0.68, False),
           (14, 'LOW', 0.92, True)]
# the call translated to a triplet grid (12 per bar)
MOTIF_A3 = [(0, 'LOW', 1.00, True), (2, 'SN', 0.86, False), (4, 'MID', 0.93, True),
            (7, 'FLAM', 0.95, False), (9, 'K', 0.76, True), (10, 'HI', 0.68, False),
            (11, 'LOW', 0.92, True)]
ORCH = {
    'orig':  {'LOW': (F2, 'R'), 'SN': (SN, 'L'), 'MID': (T4, 'R'), 'FLAM': (SN, 'R'), 'HI': (T1, 'L')},
    'high':  {'LOW': (T3, 'R'), 'SN': (SN, 'L'), 'MID': (T2, 'R'), 'FLAM': (SN, 'R'), 'HI': (T1, 'L')},
    'toms':  {'LOW': (F1, 'R'), 'SN': (T1, 'L'), 'MID': (T3, 'R'), 'FLAM': (T2, 'R'), 'HI': (T1, 'L')},
    'snare': {'LOW': (SN, 'R'), 'SN': (SN, 'L'), 'MID': (SN, 'R'), 'FLAM': (SN, 'R'), 'HI': (SN, 'L')},
    'cym':   {'LOW': (CR2, 'R'), 'SN': (SN, 'L'), 'MID': (CHN, 'R'), 'FLAM': (SN, 'R'), 'HI': (T1, 'L')},
    'soft':  {'LOW': (F1, 'R'), 'SN': (XS, 'L'), 'MID': (T4, 'R'), 'FLAM': (XS, 'L'), 'HI': (T2, 'R')},
}
BELL12 = (0, 2, 4, 5, 7, 9, 11)

# (bar position, bpm): the pulse surges into fills and settles after landings
TEMPO_ANCHORS = (
    (0.0, 106.0), (6.0, 108.5), (7.8, 111.0),
    (8.0, 107.0), (13.0, 107.5), (15.9, 112.0),
    (16.0, 110.0), (21.9, 113.5), (22.0, 112.0), (25.0, 112.0), (25.95, 108.5),
    (26.0, 108.0), (32.0, 110.0), (33.95, 113.0),
    (34.0, 104.0), (37.95, 102.5),
    (38.0, 103.0), (39.95, 114.0),
    (40.0, 115.0), (44.0, 117.0), (47.95, 120.0),
    (48.0, 116.0), (49.95, 119.0),
    (50.0, 117.0), (52.95, 118.5),
    (53.0, 117.5), (53.5, 113.0), (54.0, 90.0), (60.0, 90.0),
)


def other(h):
    return 'L' if h == 'R' else 'R'


def alt(n, first='R'):
    return [first if i % 2 == 0 else other(first) for i in range(n)]


def pairs(drums, n):
    out = []
    for d in drums:
        out += [d, d]
    while len(out) < n:
        out.append(out[-1])
    return out[:n]


# ------------------------------------------------------------ data model ----
class Stroke:
    __slots__ = ('t', 'limb', 'pitch', 'dyn', 'kind', 'main', 'sec', 'vel',
                 'dur', 'dead', 'gap', 'near')

    def __init__(self, t, limb, pitch, dyn, kind):
        self.t = t
        self.limb = limb
        self.pitch = pitch
        self.dyn = dyn
        self.kind = kind
        self.main = None
        self.sec = 0.0
        self.vel = 64
        self.dur = 0.1
        self.dead = False
        self.gap = 0.025
        self.near = 9.0


class Perf:
    """Strokes kept per limb, sorted by nominal beat; one stick per hand."""

    def __init__(self):
        self.times = {l: [] for l in LIMBS}
        self.objs = {l: [] for l in LIMBS}

    def span(self, limb, t, win):
        arr = self.times[limb]
        return bisect_left(arr, t - win), bisect_right(arr, t + win)

    def busy(self, limb, t, win):
        i, j = self.span(limb, t, win)
        return j > i

    def add(self, t, limb, pitch, dyn, kind):
        win = 0.07 if limb in HANDS else 0.1
        i, j = self.span(limb, t, win)
        if j > i:
            existing = self.objs[limb][i:j]
            if any(PRIO[s.kind] >= PRIO[kind] for s in existing):
                return None
            for s in existing:
                s.dead = True
            del self.times[limb][i:j]
            del self.objs[limb][i:j]
        s = Stroke(t, limb, pitch, max(0.04, min(1.0, dyn)), kind)
        k = bisect_left(self.times[limb], t)
        self.times[limb].insert(k, t)
        self.objs[limb].insert(k, s)
        return s

    def strokes(self):
        out = []
        for l in LIMBS:
            out.extend(self.objs[l])
        out.sort(key=lambda s: (s.t, LIMBS.index(s.limb), s.pitch))
        return out


# ------------------------------------------------------------ vocabulary ----
class Solo:
    def __init__(self, seed):
        self.r = random.Random(seed)
        self.P = Perf()
        self.rush = []     # (t0, t1, ms) hands lean ahead toward t1
        self.lean = []     # (t0, t1, ms) hands hold back toward t1
        self.stops = []    # beats where the pulse is re-established
        self.final = None

    def bt(self, bar, beat=0.0):
        return LEAD + 4.0 * bar + beat

    def n(self, t, limb, pitch, dyn, kind='tap'):
        if pitch in CRASHES and kind in ('tap', 'acc'):
            kind = 'crash'
        return self.P.add(t, limb, pitch, dyn, kind)

    def kick(self, t, dyn=0.8, foot='RF'):
        return self.P.add(t, foot, K1 if foot == 'RF' else K2, dyn, 'kick')

    def chick(self, t, dyn=0.5):
        return self.P.add(t, 'LF', HHP, dyn, 'hat')

    def flam(self, t, hand, pitch, dyn, gpitch=None):
        s = self.n(t, hand, pitch, dyn, 'acc')
        if s is None:
            return None
        o = other(hand)
        gt = t - 0.05
        if not self.P.busy(o, gt, 0.11):
            g = self.P.add(gt, o, gpitch or pitch, max(0.16, 0.33 * dyn), 'grace')
            if g is not None:
                g.main = s
        return s

    def push(self, t0, t1, ms):
        self.rush.append((t0, t1, ms))

    def hold(self, t0, t1, ms):
        self.lean.append((t0, t1, ms))

    def hat_foot(self, bar, pattern='24', d=0.5, beats=None):
        pats = {'24': (1, 3), 'q': (0, 1, 2, 3), 'up': (0.5, 1.5, 2.5, 3.5)}
        t = self.bt(bar)
        for b in (beats if beats is not None else pats[pattern]):
            self.P.add(t + b, 'LF', HHP, d * self.r.uniform(0.9, 1.08), 'hat')

    def ghosts(self, t0, t1, sub=4, prob=1.0, d=(0.17, 0.3), pitch=SN,
               hand=None, solo=True, swell=0.0):
        n = int(round((t1 - t0) * sub))
        for i in range(n):
            t = t0 + i / float(sub)
            if self.r.random() > prob:
                continue
            if hand is None:
                h = 'R' if int(round((t - LEAD) * sub)) % 2 == 0 else 'L'
            else:
                h = hand
            if self.P.busy(h, t, 0.55 / sub):
                continue
            if solo and self.P.busy(other(h), t, 0.2 / sub):
                continue
            x = i / float(max(1, n - 1))
            self.n(t, h, pitch, self.r.uniform(d[0], d[1]) + swell * x, 'ghost')

    def run(self, t0, sub, sticking, pitches, d0, d1, acc=(), curve=1.0, acc_add=0.2):
        n = len(sticking)
        prev = None
        for i in range(n):
            st = sticking[i]
            t = t0 + i / float(sub)
            x = i / float(n - 1) if n > 1 else 1.0
            dd = d0 + (d1 - d0) * (x ** curve)
            kind = 'tap'
            if i in acc:
                dd += acc_add
                kind = 'acc'
            elif st == prev:
                dd *= 0.93                      # the rebound of a double is softer
            dd *= self.r.uniform(0.95, 1.04)
            if dd < 0.3 and kind == 'tap':
                kind = 'ghost'
            if st == 'K':
                self.kick(t, min(1.0, dd + 0.04), 'RF')
            elif st == 'F':
                self.kick(t, min(1.0, dd + 0.02), 'LF')
            elif st != '-':
                self.n(t, st, pitches[i], dd, kind)
            prev = st

    def roll(self, t0, t1, pitch, d0, d1, sub0, sub1, double=False, first='R',
             curve=1.0, beat_acc=0.0):
        """A roll whose rate glides from sub0 to sub1 notes per beat."""
        L = t1 - t0
        a = (sub1 - sub0) / (2.0 * L)
        b = float(sub0)
        n = int(b * L + a * L * L + 1e-6)
        for k in range(n):
            x = k / b if abs(a) < 1e-9 else (-b + math.sqrt(b * b + 4.0 * a * k)) / (2.0 * a)
            t = t0 + x
            if double:
                h = first if (k // 2) % 2 == 0 else other(first)
            else:
                h = first if k % 2 == 0 else other(first)
            dd = d0 + (d1 - d0) * (x / L) ** curve
            if double and k % 2 == 1:
                dd *= 0.9
            rate = b + 2.0 * a * x
            if beat_acc and abs((t - LEAD) - round(t - LEAD)) < 0.5 / rate:
                dd += beat_acc
            dd *= self.r.uniform(0.95, 1.04)
            self.n(t, h, pitch, dd, 'ghost' if dd < 0.3 else 'tap')

    def double_bass(self, t0, t1, sub=4, d0=0.7, d1=0.8, first='RF'):
        n = int(round((t1 - t0) * sub))
        for i in range(n):
            t = t0 + i / float(sub)
            if self.P.busy('RF', t, 0.05) or self.P.busy('LF', t, 0.05):
                continue
            foot = first if i % 2 == 0 else ('LF' if first == 'RF' else 'RF')
            x = i / float(max(1, n - 1))
            self.kick(t, (d0 + (d1 - d0) * x) * self.r.uniform(0.93, 1.05), foot)

    def motif(self, bar, orch='orig', level=1.0, shift=0, fill=0.0, kicks=True,
              kick_lv=None, crash=False, skip=(), fill_d=(0.17, 0.3), fill_hand=None,
              grid=4, cell=None):
        o = ORCH[orch]
        t0 = self.bt(bar)
        klv = level if kick_lv is None else kick_lv
        for (p, role, d, kk) in (cell or MOTIF_A):
            if p in skip:
                continue
            t = t0 + (p + shift) / float(grid)
            dd = d * level * self.r.uniform(0.97, 1.03)
            if role == 'K':
                if kicks:
                    self.kick(t, 0.8 * klv)
                continue
            pitch, hand = o[role]
            if role == 'FLAM' and pitch != XS:
                self.flam(t, hand, pitch, dd)
            else:
                self.n(t, hand, pitch, dd, 'acc')
            if kk and kicks:
                self.kick(t, min(1.0, 0.9 * klv + 0.04))
        if crash:
            self.n(t0 + shift / float(grid), 'L', CR1, 0.95 * level, 'crash')
        if fill > 0:
            self.ghosts(t0 + shift / float(grid), t0 + 4.0, grid, fill, d=fill_d,
                        hand=fill_hand)


# ------------------------------------------------------------- the solo -----
def theme(S):
    for b in range(8):
        S.hat_foot(b, '24', 0.52)

    # 1: the call, plainly, crash on the downbeat
    S.motif(0, 'orig', crash=True)

    # 2: answer -- ghosted snare talk spilling down the toms
    t = S.bt(1)
    S.n(t + 1.0, 'R', SN, 0.8, 'acc')
    S.kick(t + 0.5, 0.55)
    S.kick(t + 1.75, 0.58)
    S.ghosts(t + 0.75, t + 2.0, 4, 1.0, d=(0.2, 0.3))
    S.run(t + 2.0, 6, alt(12), pairs((SN, T1, T2, T3, T4, F1), 12), 0.46, 0.86,
          acc=(0, 6), curve=1.2)
    S.kick(t + 2.0, 0.68)
    S.kick(t + 3.0, 0.74)
    S.push(t + 2.0, t + 4.0, 5)

    # 3: the call again, breathing with ghost notes
    S.motif(2, 'orig', fill=0.35)

    # 4: answer -- the right hand sings a 3-3-2 line, the left whispers
    t = S.bt(3)
    for i, (p, dr) in enumerate(((0, T1), (3, T2), (6, T4), (8, T2), (11, T4), (14, F1))):
        S.n(t + p / 4.0, 'R', dr, 0.72 + 0.04 * i, 'acc')
    for p, d in ((0, 0.7), (6, 0.6), (8, 0.74), (14, 0.84)):
        S.kick(t + p / 4.0, d)
    S.ghosts(t, t + 4.0, 4, 0.9, d=(0.17, 0.29), hand='L', swell=0.08)

    # 5: the call displaced by an eighth and lifted up the kit
    t = S.bt(4)
    S.kick(t, 0.62)
    S.chick(t, 0.5)
    S.motif(4, 'high', fill=0.25, shift=2)

    # 6: answer -- the displacement resolves; space, then a burst of 32nds
    t = S.bt(5)
    S.n(t, 'L', CR1, 0.86, 'crash')
    S.n(t + 0.75, 'L', SN, 0.28, 'ghost')
    S.n(t + 1.5, 'R', SN, 0.26, 'ghost')
    S.n(t + 1.75, 'L', SN, 0.34, 'ghost')
    S.n(t + 2.0, 'R', SN, 0.9, 'acc')
    S.kick(t + 2.0, 0.78)
    S.kick(t + 2.75, 0.55)
    S.run(t + 3.0, 8, alt(8), pairs((SN, T1, T2, F1), 8), 0.55, 0.9, curve=1.1)
    S.kick(t + 3.0, 0.7)
    S.push(t + 3.0, t + 4.0, 4)

    # 7: fragments of the call, sequenced up the kit
    t = S.bt(6)
    for p, dr, h, d, kk in ((0, F2, 'R', 0.98, True), (3, SN, 'L', 0.86, False),
                            (6, T4, 'R', 0.92, True), (8, T4, 'R', 0.9, True),
                            (11, SN, 'L', 0.88, False), (14, T2, 'R', 0.95, True)):
        S.n(t + p / 4.0, h, dr, d, 'acc')
        if kk:
            S.kick(t + p / 4.0, 0.84)
    S.n(t + 3.75, 'L', T1, 0.72, 'tap')
    S.ghosts(t, t + 4.0, 4, 0.55, d=(0.18, 0.3))

    # 8: first big fill -- paradiddles, sextuplets, 32nds of floor-snare thunder
    t = S.bt(7)
    for i, (h, p, d) in enumerate((('R', F1, 0.82), ('L', SN, 0.3), ('R', SN, 0.34),
                                   ('R', SN, 0.36), ('L', SN, 0.8), ('R', SN, 0.34),
                                   ('L', SN, 0.36), ('L', SN, 0.4))):
        S.n(t + i / 4.0, h, p, d, 'acc' if d > 0.6 else 'ghost')
    S.run(t + 2.0, 6, alt(6), (T1, T1, T2, T2, T4, T4), 0.62, 0.8, acc=(0,))
    S.run(t + 3.0, 8, alt(8), (F2, SN) * 4, 0.8, 0.98)
    for b in range(4):
        S.kick(t + b, 0.66 + 0.07 * b)
    S.kick(t + 3.5, 0.9)
    S.push(t + 2.0, t + 4.0, 6)


def snare_talk(S):
    r = S.r
    for b in range(8, 14):
        S.hat_foot(b, 'q', 0.45)

    # 9: the call whispered in snare language -- continuous 16ths
    t = S.bt(8)
    S.n(t, 'R', CR2, 0.92, 'crash')
    S.kick(t, 0.9)
    S.motif(8, 'snare', level=0.9, kick_lv=0.72, fill=1.0, fill_d=(0.16, 0.27), skip=(0,))

    # 10: threes against the pulse, feet in dotted quarters
    t = S.bt(9)
    for i in range(16):
        h = 'R' if i % 2 == 0 else 'L'
        if i % 3 == 0:
            S.n(t + i / 4.0, h, T1 if i == 15 else SN, 0.64 + 0.018 * i, 'acc')
        else:
            S.n(t + i / 4.0, h, SN, r.uniform(0.17, 0.28), 'ghost')
    for p in (0, 6, 12):
        S.kick(t + p / 4.0, 0.66)

    # 11: paradiddles, accents walking floor tom -> snare -> toms
    t = S.bt(10)
    accs = {0: F1, 4: SN, 8: T2, 12: T1}
    for i, h in enumerate("RLRRLRLLRLRRLRLL"):
        if i in accs:
            S.n(t + i / 4.0, h, accs[i], 0.78 + 0.03 * (i // 4), 'acc')
        else:
            S.n(t + i / 4.0, h, SN, r.uniform(0.22, 0.34), 'ghost')
    for p in (0, 8, 14):
        S.kick(t + p / 4.0, 0.68)

    # 12: Swiss army triplets -- flammed doubles, then down the toms
    t = S.bt(11)
    for g in range(8):
        tg = t + 0.5 * g
        p = SN if g < 4 else (T1, T2, T4, F1)[g - 4]
        d = 0.72 + 0.03 * g
        S.flam(tg, 'R', p, d, gpitch=SN)
        S.n(tg + 1 / 6.0, 'R', p, d * 0.55, 'tap')
        S.n(tg + 2 / 6.0, 'L', SN, 0.3 + 0.015 * g, 'ghost')
    for b in range(4):
        S.kick(t + b, 0.6 + 0.05 * b)

    # 13: the call with melodic accents over a bed of ghost notes
    S.motif(12, 'orig', level=0.95, fill=0.85, fill_d=(0.16, 0.28))

    # 14: space -- a few words and a lot of air
    t = S.bt(13)
    S.flam(t, 'R', SN, 0.9)
    S.kick(t, 0.8)
    S.n(t + 0.5, 'R', SN, 0.25, 'ghost')
    S.n(t + 0.75, 'L', SN, 0.3, 'ghost')
    S.kick(t + 1.5, 0.58)
    S.n(t + 1.75, 'L', SN, 0.32, 'ghost')
    S.n(t + 2.0, 'R', SN, 0.93, 'acc')
    S.kick(t + 2.0, 0.8)
    S.n(t + 3.5, 'L', SN, 0.2, 'ghost')
    S.n(t + 3.75, 'R', SN, 0.22, 'ghost')

    # 15-16: a double-stroke roll swells from a whisper, then pours down the kit
    t = S.bt(14)
    S.roll(t, t + 6.0, SN, 0.14, 0.72, 6, 8, double=True, curve=1.5, beat_acc=0.05)
    for i in range(6):
        S.kick(t + i, 0.34 + 0.08 * i)
    S.hat_foot(14, 'q', 0.4)
    S.hat_foot(15, beats=(0, 0.5, 1, 1.5), d=0.48)
    S.run(t + 6.0, 8, alt(16), pairs((SN, T1, T2, T3, T4, F1, F2), 16), 0.72, 0.97,
          acc=(0, 8))
    S.kick(t + 6.0, 0.85)
    S.kick(t + 7.0, 0.9)
    S.kick(t + 7.5, 0.92)
    S.push(t + 4.0, t + 8.0, 7)


def travel(S):
    # 17: landing crash, then sixes rolling around the toms
    t = S.bt(16)
    for g, a in enumerate((CR2, T1, T2, T4)):
        tg = t + g
        rp = SN if g == 0 else a
        S.n(tg, 'R', a, 0.95 if g == 0 else 0.82 + 0.05 * g, 'acc')
        S.kick(tg, 0.92 if g == 0 else 0.76)
        S.n(tg + 1 / 6.0, 'L', SN, 0.25, 'ghost')
        S.n(tg + 2 / 6.0, 'L', SN, 0.3, 'ghost')
        S.n(tg + 3 / 6.0, 'R', rp, 0.5, 'tap')
        S.n(tg + 4 / 6.0, 'R', rp, 0.46, 'tap')
        S.n(tg + 5 / 6.0, 'L', SN, 0.72 + 0.05 * g, 'acc')
    S.hat_foot(16, '24', 0.5)

    # 18: the call sung on the toms
    S.motif(17, 'toms', fill=0.55, fill_d=(0.17, 0.3))
    S.hat_foot(17, 'q', 0.46)

    # 19: Bonham triplets -- a wave down the kit and back up
    t = S.bt(18)
    for i in range(8):
        tg = t + 0.5 * i
        if i < 4:
            pr = pl = (T1, T2, T4, F1)[i]
            d = 0.55 + 0.1 * i
        else:
            pr = (F2, T4, T2, SN)[i - 4]
            pl = (F1, T3, T1, SN)[i - 4]
            d = 0.86 - 0.07 * (i - 4)
        S.n(tg, 'R', pr, d + 0.08, 'acc')
        S.n(tg + 1 / 6.0, 'L', pl, d, 'tap')
        if i < 7:
            S.kick(tg + 2 / 6.0, d)
    S.hat_foot(18, 'up', 0.48)

    # 20: paradiddle-diddles on the floor toms, then six notes up the kit
    t = S.bt(19)
    for bi, drum in enumerate((F2, F1, T4)):
        tb = t + bi
        for j, h in enumerate("RLRRLL"):
            tt = tb + j / 6.0
            if h == 'R':
                S.n(tt, 'R', drum, 0.86 if j == 0 else 0.5, 'acc' if j == 0 else 'tap')
            else:
                S.n(tt, 'L', SN, 0.44 if j == 5 else 0.3, 'ghost')
        S.kick(tb, 0.78)
    S.run(t + 3.0, 6, alt(6), (F1, T4, T3, T2, T1, SN), 0.6, 0.86)
    S.hat_foot(19, '24', 0.5)

    # 21-22: fives over the barline while the hi-hat foot holds the pulse
    t = S.bt(20)
    for g, a in enumerate((T1, T2, T4, F1, T2, F2)):
        tg = t + 1.25 * g
        d = 0.7 + 0.045 * g
        S.n(tg, 'R', a, d + 0.12, 'acc')
        S.n(tg + 0.25, 'L', SN, 0.28, 'ghost')
        S.n(tg + 0.5, 'R', SN, 0.4, 'tap')
        S.n(tg + 0.75, 'L', SN, 0.32, 'ghost')
        S.kick(tg + 1.0, 0.6 + 0.05 * g)
    S.n(t + 7.5, 'R', F1, 0.92, 'acc')
    S.kick(t + 7.5, 0.86)
    S.n(t + 7.75, 'L', SN, 0.88, 'acc')
    S.hat_foot(20, 'q', 0.48)
    S.hat_foot(21, 'q', 0.52)
    S.push(t + 6.0, t + 8.0, 5)

    # 23: the call on the cymbals
    S.motif(22, 'cym', fill=0.4)
    S.hat_foot(22, '24', 0.5)

    # 24: space, then double strokes tumbling down
    t = S.bt(23)
    S.kick(t, 0.76)
    S.n(t + 0.5, 'L', SN, 0.28, 'ghost')
    S.n(t + 0.75, 'R', SN, 0.3, 'ghost')
    S.n(t + 1.0, 'L', SN, 0.88, 'acc')
    S.kick(t + 1.5, 0.66)
    S.n(t + 1.75, 'L', SN, 0.32, 'ghost')
    S.run(t + 2.0, 8, list("RRLL") * 4, [SN] * 8 + [T2] * 4 + [F1] * 4, 0.45, 0.92,
          curve=1.2)
    S.kick(t + 2.0, 0.7)
    S.kick(t + 3.0, 0.8)
    S.kick(t + 3.5, 0.84)
    S.hat_foot(23, '24', 0.5)

    # 25: a linear groove, open hi-hat barks closed by the foot
    t = S.bt(24)
    line = (('K', 0, 0.8), ('R', HHC, 0.55), ('L', SN, 0.86), ('R', HHC, 0.5),
            ('K', 0, 0.7), ('R', HHO, 0.8), ('LF', HHP, 0.6), ('L', SN, 0.3),
            ('K', 0, 0.76), ('R', T1, 0.78), ('L', SN, 0.9), ('R', T2, 0.8),
            ('K', 0, 0.82), ('R', HHO, 0.86), ('LF', HHP, 0.66), ('L', SN, 0.42))
    for i, (limb, p, d) in enumerate(line):
        tt = t + i / 4.0
        if limb == 'K':
            S.kick(tt, d)
        elif limb == 'LF':
            S.chick(tt, d)
        else:
            S.n(tt, limb, p, d, 'acc' if d > 0.6 else ('ghost' if d < 0.4 else 'tap'))

    # 26: flam accents stepping down the toms, then a held-back six into 12/8
    t = S.bt(25)
    for g, (p, h) in enumerate(((T1, 'R'), (T2, 'L'), (T4, 'R'))):
        tg = t + g
        S.flam(tg, h, p, 0.84 + 0.03 * g)
        S.n(tg + 1 / 3.0, other(h), SN, 0.34, 'ghost')
        S.n(tg + 2 / 3.0, h, SN, 0.42, 'tap')
    S.run(t + 3.0, 6, alt(6), (T4, T4, F1, F1, F2, F2), 0.7, 0.92)
    for b in range(4):
        S.kick(t + b, 0.7 + 0.05 * b)
    S.hat_foot(25, '24', 0.5)
    S.hold(t + 2.5, t + 4.0, 7)


def triplet_feel(S):
    r = S.r

    def bell(bar, pitch, d, upto=12, acc_pitch=None):
        t = S.bt(bar)
        for p in BELL12:
            if p < upto:
                accent = p in (0, 7)
                dd = (d + (0.12 if accent else 0.0)) * r.uniform(0.94, 1.05)
                S.n(t + p / 3.0, 'R', acc_pitch if (accent and acc_pitch) else pitch, dd, 'tap')

    def talk(bar, dens, accents, start=0, upto=12):
        t = S.bt(bar)
        for p in range(start, upto):
            tt = t + p / 3.0
            if p in accents:
                S.n(tt, 'L', accents[p], 0.7 + r.uniform(-0.04, 0.08), 'acc')
            elif r.random() < dens:
                S.n(tt, 'L', SN, r.uniform(0.16, 0.3), 'ghost')

    def kicks(bar, pos, d=0.72):
        t = S.bt(bar)
        for p in pos:
            S.kick(t + p / 3.0, d * r.uniform(0.94, 1.05))

    for b in range(26, 34):
        S.hat_foot(b, '24', 0.5)

    # 27-28: bell pattern in 12/8, the left hand talking back
    bell(26, BELL, 0.6)
    talk(26, 0.42, {6: SN, 10: SN}, start=1)
    kicks(26, (0, 6, 8))
    bell(27, RIDE, 0.62, acc_pitch=BELL)
    talk(27, 0.5, {3: SN, 9: T1, 10: T2})
    kicks(27, (0, 6, 11), 0.74)

    # 29: the call, translated into triplets
    S.motif(28, 'orig', grid=3, cell=MOTIF_A3, fill=0.55, fill_d=(0.17, 0.3))

    # 30: cowbell colour, left hand on the toms, then six notes up the kit
    bell(29, COW, 0.56, upto=9)
    talk(29, 0.4, {3: T1, 6: SN}, start=1, upto=8)
    kicks(29, (0, 6))
    S.run(S.bt(29, 3.0), 6, alt(6), (F1, T4, T3, T2, T1, SN), 0.62, 0.86)

    # 31: three against two -- quarter-note triplets climbing the toms
    t = S.bt(30)
    for i, p in enumerate((F2, F1, T4, T3, T2, T1)):
        S.n(t + 2 * i / 3.0, 'R', p, 0.76 + 0.03 * i, 'acc')
        S.n(t + (2 * i + 1) / 3.0, 'L', SN, r.uniform(0.2, 0.32), 'ghost')
    for b in range(4):
        S.kick(t + b, 0.7)

    # 32: timbales call, toms answer
    t = S.bt(31)
    S.run(t, 6, alt(6), (TIMH, TIMH, TIML, TIML, TIMH, TIML), 0.56, 0.74)
    S.flam(t + 1.0, 'R', TIMH, 0.9, gpitch=TIML)
    S.kick(t + 1.0, 0.8)
    S.n(t + 1.0 + 2 / 6.0, 'L', TIML, 0.4, 'tap')
    S.n(t + 1.0 + 4 / 6.0, 'R', TIML, 0.5, 'tap')
    S.run(t + 2.0, 6, alt(6), (T1, T1, T2, T2, T4, T4), 0.6, 0.82)
    S.kick(t + 2.0, 0.7)
    S.flam(t + 3.0, 'R', F1, 0.92, gpitch=T4)
    S.kick(t + 3.0, 0.85)
    S.n(t + 3.0 + 1 / 3.0, 'L', SN, 0.5, 'tap')
    S.n(t + 3.0 + 2 / 3.0, 'R', SN, 0.62, 'tap')

    # 33: hands and feet in a line -- R L K triplets, then twice as fast
    t = S.bt(32)
    for i in range(2):
        tb = t + i
        S.n(tb, 'R', (T1, T2)[i], 0.8, 'acc')
        S.n(tb + 1 / 3.0, 'L', SN, 0.52, 'tap')
        S.kick(tb + 2 / 3.0, 0.76)
    for i in range(4):
        tb = t + 2.0 + 0.5 * i
        S.n(tb, 'R', (T4, F1, F2, CR2)[i], 0.8 + 0.04 * i, 'acc')
        S.n(tb + 1 / 6.0, 'L', (SN, SN, F1, SN)[i], 0.55, 'tap')
        S.kick(tb + 2 / 6.0, 0.8, 'LF' if i == 3 else 'RF')

    # 34: shifting gears -- 3, 4, 6 and 8 notes to the beat, into the break
    t = S.bt(33)
    S.run(t, 3, alt(3), (SN, T1, T2), 0.6, 0.66, acc=(0,))
    S.run(t + 1.0, 4, alt(4), (T2, T3, T3, T4), 0.66, 0.72)
    S.run(t + 2.0, 6, alt(6), (T4, T4, F1, F1, SN, SN), 0.72, 0.84)
    S.run(t + 3.0, 8, alt(8), (T1, T1, T2, T2, F1, F1, F2, F2), 0.84, 0.98)
    for b in range(4):
        S.kick(t + b, 0.72 + 0.06 * b)
    S.push(t + 2.0, t + 4.0, 6)


def breakdown(S):
    # 35: one big hit, air, then whispers
    t = S.bt(34)
    S.n(t, 'R', CR2, 0.96, 'crash')
    S.kick(t, 0.96)
    S.kick(t, 0.9, 'LF')
    S.stops.append(t)
    S.n(t + 2.5, 'L', XS, 0.42, 'tap')
    S.chick(t + 3.0, 0.4)
    S.n(t + 3.5, 'R', F2, 0.34, 'tap')
    S.n(t + 3.75, 'L', XS, 0.3, 'ghost')

    # 36: the call, whispered -- side stick and soft toms
    S.motif(35, 'soft', level=0.46, kick_lv=0.42)
    S.hat_foot(35, 'q', 0.38)

    # 37: the call's skeleton is a clave -- woodblock over a bed of ghosts
    t = S.bt(36)
    for i, p in enumerate((0, 3, 6, 10, 12)):
        S.n(t + p / 4.0, 'R', WBH, 0.56 + (0.08 if i in (0, 3) else 0.0), 'tap')
    S.ghosts(t, t + 4.0, 4, 0.8, d=(0.14, 0.26), hand='L', solo=False)
    S.kick(t, 0.42)
    S.kick(t + 1.75, 0.36)
    S.kick(t + 2.5, 0.4)
    S.hat_foot(36, 'q', 0.36)

    # 38: the clave turned around on two woodblocks, a triangle for colour
    t = S.bt(37)
    S.n(t, 'R', TRI, 0.5, 'tap')
    for p, w in ((2, WBL), (4, WBL), (8, WBH), (11, WBH), (14, WBH)):
        S.n(t + p / 4.0, 'R', w, 0.58, 'tap')
    S.ghosts(t, t + 4.0, 4, 0.9, d=(0.16, 0.3), hand='L', solo=False, swell=0.12)
    S.kick(t, 0.44)
    S.kick(t + 2.0, 0.46)
    S.kick(t + 3.5, 0.5)
    S.hat_foot(37, 'q', 0.38)

    # 39-40: the long swell -- single strokes from a whisper to a roar
    t = S.bt(38)
    S.roll(t, t + 6.0, SN, 0.13, 0.84, 4, 8, curve=1.7, beat_acc=0.04)
    for i in range(6):
        S.kick(t + i, 0.3 + 0.1 * i)
    S.hat_foot(38, 'q', 0.4)
    S.hat_foot(39, beats=(0, 0.5, 1, 1.5), d=0.5)
    S.run(t + 6.0, 8, alt(15), pairs((SN, T1, T2, T3, T4, F1, F2), 15), 0.82, 1.0)
    S.double_bass(t + 6.0, t + 8.0, 4, 0.72, 0.95)
    S.push(t + 4.0, t + 8.0, 7)


def climax(S):
    # 41: both crashes, both feet; then the call on the cymbals over thunder
    t = S.bt(40)
    S.n(t, 'L', CR1, 1.0, 'crash')
    S.n(t, 'R', CR2, 1.0, 'crash')
    S.kick(t, 1.0)
    S.kick(t, 0.95, 'LF')
    S.motif(40, 'cym', skip=(0,), fill=0.3, fill_d=(0.2, 0.32))
    S.double_bass(t + 0.25, t + 4.0, 4, 0.66, 0.8, first='LF')

    # 42: sextuplets down the whole kit, 32nds climbing back up
    t = S.bt(41)
    S.run(t, 6, alt(12), pairs(TOMS, 12), 0.7, 0.9, acc=(0, 6))
    S.double_bass(t, t + 2.0, 2, 0.74, 0.8)
    S.run(t + 2.0, 8, alt(16),
          (F2, F2, F1, F1, T4, T4, T3, T3, T2, T2, T1, T1, SN, SN, SN, SN), 0.72, 0.98)
    S.double_bass(t + 2.0, t + 4.0, 4, 0.78, 0.92)
    S.push(t + 2.0, t + 4.0, 6)

    # 43: R L R L K K sextuplets rolling downhill
    t = S.bt(42)
    for g, (a, b) in enumerate(((T1, T2), (T2, T4), (T4, F1), (F1, F2))):
        tg = t + g
        d = 0.74 + 0.06 * g
        S.n(tg, 'R', a, d + 0.12, 'acc')
        S.n(tg + 1 / 6.0, 'L', a, d, 'tap')
        S.n(tg + 2 / 6.0, 'R', b, d, 'tap')
        S.n(tg + 3 / 6.0, 'L', b, d, 'tap')
        S.kick(tg + 4 / 6.0, d + 0.05)
        S.kick(tg + 5 / 6.0, d + 0.05, 'LF')
    S.push(t + 2.0, t + 4.0, 5)

    # 44: cymbal punches, then threes hidden inside a burst of 32nds
    t = S.bt(43)
    S.n(t, 'R', CR2, 0.96, 'crash')
    S.kick(t, 0.95)
    S.n(t + 0.75, 'L', SPL, 0.86, 'crash')
    S.kick(t + 0.75, 0.9, 'LF')
    S.n(t + 1.5, 'R', CHN, 0.92, 'crash')
    S.kick(t + 1.5, 0.92)
    S.n(t + 1.75, 'L', SN, 0.4, 'ghost')
    S.run(t + 2.0, 8, alt(16),
          (SN, SN, SN, T1, T1, T1, T2, T2, T2, T4, T4, T4, F1, F1, F1, F2),
          0.62, 0.95, acc=(0, 3, 6, 9, 12, 15), acc_add=0.16)
    S.double_bass(t + 2.0, t + 4.0, 4, 0.7, 0.9)

    # 45: sixes return -- tom accents, left-hand crashes on the last partial
    t = S.bt(44)
    for g in range(4):
        tg = t + g
        a = (CR2, T1, T2, F1)[g]
        rt = (SN, T1, T2, F1)[g]
        S.n(tg, 'R', a, 0.88 + 0.03 * g, 'acc')
        S.kick(tg, 0.86)
        S.n(tg + 1 / 6.0, 'L', SN, 0.3, 'ghost')
        S.n(tg + 2 / 6.0, 'L', SN, 0.36, 'ghost')
        S.n(tg + 3 / 6.0, 'R', rt, 0.56, 'tap')
        S.n(tg + 4 / 6.0, 'R', rt, 0.52, 'tap')
        if g in (1, 3):
            S.n(tg + 5 / 6.0, 'L', CR1, 0.86, 'crash')
            S.kick(tg + 5 / 6.0, 0.84, 'LF')
        else:
            S.n(tg + 5 / 6.0, 'L', SN, 0.82, 'acc')
    S.double_bass(t, t + 4.0, 2, 0.7, 0.82)

    # 46: the call displaced by a sixteenth, the kick nailing the quarters
    t = S.bt(45)
    for b in range(4):
        S.kick(t + b, 0.82)
    S.motif(45, 'cym', shift=1, fill=0.9, fill_d=(0.2, 0.34), kicks=False)
    S.hat_foot(45, 'up', 0.5)

    # 47-48: sevens across the barline, resolved by a flammed tag
    t = S.bt(46)
    for g, cy in enumerate((CR2, CHN, CR2, CHN)):
        tg = t + 1.75 * g
        d = 0.8 + 0.04 * g
        S.n(tg, 'R', cy, min(1.0, d + 0.1), 'crash')
        S.kick(tg, 0.9)
        S.n(tg + 0.25, 'L', SN, 0.5, 'tap')
        S.n(tg + 0.5, 'R', T2, d - 0.12, 'tap')
        S.n(tg + 0.75, 'L', SN, 0.5, 'tap')
        S.n(tg + 1.0, 'R', F1, d, 'acc')
        S.kick(tg + 1.25, 0.8)
        S.kick(tg + 1.5, 0.8, 'LF')
    tt = t + 7.0
    S.flam(tt, 'R', F1, 0.92, gpitch=SN)
    S.kick(tt, 0.9)
    S.n(tt + 0.25, 'L', SN, 0.88, 'acc')
    S.flam(tt + 0.5, 'R', F2, 0.95, gpitch=SN)
    S.kick(tt + 0.5, 0.92)
    S.n(tt + 0.75, 'L', SN, 0.92, 'acc')
    S.kick(tt + 0.75, 0.9, 'LF')
    S.push(t + 5.25, t + 8.0, 6)

    # 49: the stop -- everything at once, a beat of silence, the rebuild
    t = S.bt(48)
    S.n(t, 'L', CR1, 1.0, 'crash')
    S.n(t, 'R', CR2, 1.0, 'crash')
    S.kick(t, 1.0)
    S.kick(t, 0.96, 'LF')
    S.stops.append(t)
    S.run(t + 2.0, 4, alt(4), (SN, SN, SN, SN), 0.5, 0.82)
    S.run(t + 3.0, 6, alt(6), (T1, T1, T2, T2, F1, F1), 0.8, 0.95)
    S.kick(t + 2.0, 0.7)
    S.kick(t + 3.0, 0.85)

    # 50: flurries of 32nds between cymbal-and-kick punches on the call's rhythm
    t = S.bt(49)
    for p, cy in ((0, CR2), (3, CHN), (6, CR2), (10, CHN), (14, CR2)):
        S.n(t + p / 4.0, 'R', cy, 0.95, 'crash')
        S.kick(t + p / 4.0, 0.95)
    for a, pits in ((0, (T1, T1, T2, T2, T4)), (3, (SN, SN, T1, T1, T2)),
                    (6, (T1, T1, T2, T2, T4, T4, F1)), (10, (SN, T1, T1, T2, T2, F1, F1))):
        k = len(pits)
        for j in range(k):
            h = 'L' if j % 2 == 0 else 'R'
            S.n(t + (a + 0.5 * (j + 1)) / 4.0, h, pits[j], 0.5 + 0.35 * j / (k - 1.0), 'tap')
    S.n(t + 3.75, 'L', SN, 0.8, 'acc')
    for p in (1, 2, 4, 5, 7, 8, 9, 11, 12, 13):
        S.kick(t + p / 4.0, 0.7, 'LF')
    S.push(t + 2.5, t + 4.0, 6)


def finale(S):
    S.hat_foot(50, '24', 0.55)
    S.hat_foot(51, '24', 0.55)
    S.hat_foot(52, beats=(1,), d=0.55)

    # 51: the call comes home, exactly as it began
    S.motif(50, 'orig', crash=True, fill=0.3)

    # 52: the fastest run of the night -- 32nds around the whole kit
    t = S.bt(51)
    S.kick(t, 0.78)
    S.n(t + 0.25, 'L', SN, 0.3, 'ghost')
    S.n(t + 0.5, 'R', SN, 0.86, 'acc')
    S.n(t + 0.75, 'L', SN, 0.34, 'ghost')
    path = [SN] * 4 + [T1] * 4 + [T2] * 4 + [T3] * 4 + [T4] * 4 + [F1, F1, F2, F2]
    S.run(t + 1.0, 8, alt(24), path, 0.55, 0.98, curve=1.1, acc=(0, 8, 16), acc_add=0.12)
    for b in (1, 2, 3):
        S.kick(t + b, 0.75 + 0.05 * b)
    S.push(t + 1.0, t + 4.0, 7)

    # 53: the call on the toms, the feet thundering under its second half
    t = S.bt(52)
    S.motif(52, 'toms', fill=0.5)
    S.double_bass(t + 2.0, t + 4.0, 4, 0.66, 0.86)

    # 54: the last fill -- crash, cascade, three broad flams... and the hit
    t = S.bt(53)
    S.n(t, 'R', CR2, 0.98, 'crash')
    S.n(t, 'L', SN, 0.9, 'acc')
    S.kick(t, 0.98)
    S.kick(t, 0.9, 'LF')
    S.run(t + 0.5, 6, alt(9), (T1, T1, T2, T2, T3, T3, T4, T4, F1), 0.66, 0.92, curve=1.2)
    S.double_bass(t + 0.5, t + 2.0, 4, 0.7, 0.88)
    for i in range(3):
        tt = t + 2.0 + i * 2.0 / 3.0
        d = min(1.0, 0.9 + 0.04 * i)
        if i < 2:
            S.flam(tt, 'R', (F1, F2)[i], d)
        else:
            S.n(tt, 'R', F1, d, 'acc')
            S.n(tt, 'L', SN, d, 'acc')
        S.kick(tt, d)
        S.kick(tt + 1 / 3.0, 0.8, 'LF')
    S.hold(t + 2.0, t + 4.0, 8)

    tf = S.bt(54)
    S.n(tf, 'L', CR1, 1.0, 'crash')
    S.n(tf, 'R', CR2, 1.0, 'crash')
    S.kick(tf, 1.0)
    S.kick(tf, 0.97, 'LF')
    S.final = tf


# ------------------------------------------------- keep inventing: no bar twice
def bar_sig(S, b):
    t0 = S.bt(b)
    t1 = t0 + 4.0
    sig = []
    for limb in LIMBS:
        arr = S.P.times[limb]
        i = bisect_left(arr, t0 - 1e-9)
        j = bisect_left(arr, t1 - 1e-9)
        for s in S.P.objs[limb][i:j]:
            if s.pitch != HHP:
                sig.append((int(round((s.t - t0) * 48)), s.pitch))
    return tuple(sorted(sig))


def ensure_unique(S, nbars):
    seen = set()
    for b in range(nbars):
        sig = bar_sig(S, b)
        tries = 0
        while sig in seen and tries < 24:
            p = S.r.randrange(16)
            t = S.bt(b) + p / 4.0
            h = 'R' if p % 2 == 0 else 'L'
            if not S.P.busy(h, t, 0.14) and not S.P.busy(other(h), t, 0.05):
                S.n(t, h, SN, S.r.uniform(0.16, 0.26), 'ghost')
            sig = bar_sig(S, b)
            tries += 1
        seen.add(sig)


def compose():
    S = Solo(SEED)
    theme(S)
    snare_talk(S)
    travel(S)
    triplet_feel(S)
    breakdown(S)
    climax(S)
    finale(S)
    ensure_unique(S, 54)
    return S


# ------------------------------------------------------------ performance ---
def base_tempo(bp):
    A = TEMPO_ANCHORS
    if bp <= A[0][0]:
        return A[0][1]
    for (x0, y0), (x1, y1) in zip(A, A[1:]):
        if x0 <= bp <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (bp - x0) / (x1 - x0)
    return A[-1][1]


def tempo_map(S, nb):
    rng = random.Random(SEED + 11)
    amps = [rng.uniform(0.003, 0.011) for _ in range(64)]
    noise = [0.0] * nb
    for k in range(1, nb):
        noise[k] = noise[k - 1] * 0.7 + rng.gauss(0.0, 0.0012)
    raw = []
    for k in range(nb):
        bp = (k + 0.5 - LEAD) / 4.0
        bpm = base_tempo(bp)
        if 0.0 <= bp < 53.0:
            ph = bp % 2.0           # two-bar phrases: settle, then press forward
            amp = amps[int(bp // 2.0)]
            bpm *= 1.0 + amp * max(0.0, ph - 1.0) - 0.005 * max(0.0, 0.5 - ph)
            bpm *= 1.0 + noise[k]
        raw.append(bpm)
    cuts = set(int(round(x)) for x in S.stops)
    cuts.add(int(round(S.final)))
    out = []
    for k in range(nb):
        left = raw[k - 1] if (k > 0 and k not in cuts) else raw[k]
        right = raw[k + 1] if (k + 1 < nb and (k + 1) not in cuts) else raw[k]
        out.append(0.25 * left + 0.5 * raw[k] + 0.25 * right)
    return out


def make_converters(spb):
    starts = [0.0]
    for x in spb:
        starts.append(starts[-1] + x)

    def b2s(t):
        k = max(0, min(int(math.floor(t)), len(spb) - 1))
        return starts[k] + (t - k) * spb[k]

    def s2t(sec):
        k = bisect_right(starts, sec) - 1
        k = max(0, min(k, len(spb) - 1))
        return int(round((k + (sec - starts[k]) / spb[k]) * PPQ))

    return b2s, s2t


def humanize(S, strokes, b2s, nb):
    hr = random.Random(SEED * 7 + 3)
    cuts = set(int(round(x)) for x in S.stops)
    drift = [0.0] * (nb + 2)
    for k in range(1, nb + 2):
        drift[k] = 0.0 if k in cuts else drift[k - 1] * 0.82 + hr.gauss(0.0, 1.5)
    for limb in LIMBS:
        seq = [s for s in strokes if s.limb == limb]
        for i, s in enumerate(seq):
            near = 9.0
            if i > 0:
                near = min(near, s.t - seq[i - 1].t)
            if i + 1 < len(seq):
                near = min(near, seq[i + 1].t - s.t)
            s.near = near
    for s in strokes:
        if s.kind == 'grace':
            continue
        bias, sig = TIMING[s.kind]
        if s.near < 0.2:
            sig *= 0.55             # fast passages are played tighter
        off = bias + LIMB_BIAS[s.limb] + hr.gauss(0.0, sig)
        k = int(s.t)
        x = s.t - k
        off += drift[k] * (1.0 - x) + drift[k + 1] * x
        scale = 0.5 if s.limb in FEET else 1.0
        for t0, t1, ms in S.rush:
            if t0 <= s.t < t1:
                off -= scale * ms * ((s.t - t0) / (t1 - t0)) ** 1.4
            elif abs(s.t - t1) < 0.02:
                off += 1.5
        for t0, t1, ms in S.lean:
            if t0 <= s.t < t1:
                off += ms * ((s.t - t0) / (t1 - t0)) ** 1.2
            elif abs(s.t - t1) < 0.02:
                off += 0.75 * ms
        s.sec = b2s(s.t) + off / 1000.0
    for s in strokes:
        if s.kind != 'grace':
            continue
        if s.main is None or s.main.dead:
            s.dead = True
            continue
        s.gap = 0.018 + 0.012 * s.main.dyn + hr.uniform(-0.003, 0.003)
        s.sec = s.main.sec - s.gap


def min_gap(a, b):
    if a.limb in FEET:
        return 0.1
    return 0.052 if a.pitch == b.pitch else 0.08


def enforce_limbs(strokes, nudge):
    for limb in LIMBS:
        seq = sorted((s for s in strokes if s.limb == limb and not s.dead),
                     key=lambda s: s.sec)
        prev = None
        for s in seq:
            if prev is not None:
                need = min_gap(prev, s)
                gap = s.sec - prev.sec
                if gap < need:
                    deficit = need - gap
                    if nudge and deficit <= 0.012 and s.kind != 'grace' and prev.kind != 'grace':
                        s.sec += deficit
                    elif PRIO[s.kind] <= PRIO[prev.kind]:
                        s.dead = True
                        continue
                    else:
                        prev.dead = True
            prev = s


def realign_graces(strokes):
    for s in strokes:
        if s.kind == 'grace' and not s.dead:
            if s.main is None or s.main.dead:
                s.dead = True
            else:
                s.sec = s.main.sec - s.gap


def enforce_pitches(strokes):
    groups = {}
    for s in strokes:
        if not s.dead:
            groups.setdefault(s.pitch, []).append(s)
    for p in sorted(groups):
        seq = sorted(groups[p], key=lambda s: s.sec)
        prev = None
        for s in seq:
            if prev is not None and s.sec - prev.sec < 0.012:
                if PRIO[s.kind] <= PRIO[prev.kind]:
                    s.dead = True
                    continue
                prev.dead = True
            prev = s


def enforce_polyphony(strokes, window=0.05):
    """Never more than two hands and two feet inside any 50 ms window."""
    for group in (HANDS, FEET):
        seq = sorted((s for s in strokes if not s.dead and s.limb in group),
                     key=lambda s: s.sec)
        i = 0
        while i + 2 < len(seq):
            if seq[i + 2].sec - seq[i].sec < window:
                victim = min(seq[i:i + 3], key=lambda s: (PRIO[s.kind], s.dyn))
                victim.dead = True
                seq.remove(victim)
                i = max(0, i - 2)
            else:
                i += 1


def velocities(S, strokes):
    vr = random.Random(SEED * 13 + 5)
    for s in strokes:
        if s.dead:
            continue
        d = s.dyn
        if s.kind == 'ghost' and s.limb == 'L':
            d *= 0.96
        elif s.kind == 'tap' and s.limb == 'R':
            d *= 1.02
        d = max(0.0, min(1.0, d))
        v = (6.0 + 121.0 * d ** 1.08) * GAIN.get(s.pitch, 1.0)
        v += vr.gauss(0.0, 2.2 if s.kind in ('acc', 'crash', 'kick') else 3.0)
        lo = 16 if s.kind in ('ghost', 'grace') else 22
        s.vel = int(max(lo, min(127, round(v))))
        if abs(s.t - S.final) < 1e-6:
            s.vel = 127 if s.limb != 'LF' else 118


def ring_time(p):
    if p in (CR1, CR2, CHN):
        return 2.6
    if p in (SPL, TRI):
        return 1.4
    if p in (RIDE, BELL):
        return 1.5
    if p in TOMS or p in (TIMH, TIML):
        return 0.7
    if p in (K1, K2):
        return 0.4
    if p == HHO:
        return 0.6
    if p in (HHC, HHP):
        return 0.15
    return 0.3


def durations(live, end_sec):
    for s in live:
        s.dur = ring_time(s.pitch)
    for limb in LIMBS:                       # a stick is on one stroke at a time
        seq = sorted((s for s in live if s.limb == limb), key=lambda s: s.sec)
        for a, b in zip(seq, seq[1:]):
            a.dur = min(a.dur, b.sec - a.sec - 0.004)
    groups = {}
    for s in live:
        groups.setdefault(s.pitch, []).append(s)
    for p in sorted(groups):                 # never overlap the same key
        seq = sorted(groups[p], key=lambda s: s.sec)
        for a, b in zip(seq, seq[1:]):
            a.dur = min(a.dur, b.sec - a.sec - 0.004)
    for s in live:
        s.dur = max(0.006, min(s.dur, end_sec - s.sec - 0.01))


def write_midi(path, live, tempos, s2t, end_tick):
    ev = []
    counter = [0]

    def put(tick, group, sub, msg):
        ev.append((tick, group, sub, counter[0], msg))
        counter[0] += 1

    put(0, 0, 0, mido.MetaMessage('track_name', name='Drum Solo'))
    put(0, 0, 1, mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                   clocks_per_click=24, notated_32nd_notes_per_beat=8))
    prev = None
    for k, tp in enumerate(tempos):
        tick = k * PPQ
        if tick >= end_tick:
            break
        if tp != prev:
            put(tick, 0, 2, mido.MetaMessage('set_tempo', tempo=tp))
            prev = tp
    put(0, 1, 0, mido.Message('sysex', data=(0x7E, 0x7F, 0x09, 0x01)))   # GM on
    put(48, 1, 1, mido.Message('program_change', channel=CH, program=0))
    put(48, 1, 2, mido.Message('control_change', channel=CH, control=7, value=100))
    put(48, 1, 3, mido.Message('control_change', channel=CH, control=10, value=64))
    put(48, 1, 4, mido.Message('control_change', channel=CH, control=91, value=40))
    for s in live:
        on = s2t(s.sec)
        off = max(on + 1, s2t(s.sec + s.dur))
        put(on, 3, s.pitch, mido.Message('note_on', channel=CH, note=s.pitch, velocity=s.vel))
        put(off, 2, s.pitch, mido.Message('note_off', channel=CH, note=s.pitch, velocity=0))
    ev.sort(key=lambda e: e[:4])
    track = mido.MidiTrack()
    last = 0
    for tick, _, _, _, msg in ev:
        track.append(msg.copy(time=tick - last))
        last = tick
    track.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - last)))
    mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
    mid.tracks.append(track)
    mid.save(path)


def main():
    S = compose()
    strokes = S.P.strokes()
    nb = int(math.ceil(S.final)) + 10

    bpms = tempo_map(S, nb)
    b2s, _ = make_converters([60.0 / b for b in bpms])
    scale = b2s(S.final) / TARGET_FINAL          # land the last hit on time
    tempos = [int(round(60000000.0 / (b * scale))) for b in bpms]
    b2s, s2t = make_converters([tp / 1e6 for tp in tempos])

    humanize(S, strokes, b2s, nb)
    enforce_limbs(strokes, True)
    realign_graces(strokes)
    enforce_limbs(strokes, False)
    enforce_pitches(strokes)
    enforce_polyphony(strokes)
    realign_graces(strokes)

    live = [s for s in strokes if not s.dead]
    velocities(S, live)
    final_sec = max(s.sec for s in live if abs(s.t - S.final) < 1e-6)
    end_sec = final_sec + TAIL
    live = [s for s in live if s.sec < end_sec - 0.05]
    durations(live, end_sec)
    live.sort(key=lambda s: (s.sec, s.pitch))
    write_midi(OUTFILE, live, tempos, s2t, s2t(end_sec))
    print("wrote %s: %d strokes, %.1f seconds" % (OUTFILE, len(live), end_sec))


if __name__ == "__main__":
    main()
