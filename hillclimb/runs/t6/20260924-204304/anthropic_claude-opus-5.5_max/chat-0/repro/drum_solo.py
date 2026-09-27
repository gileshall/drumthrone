#!/usr/bin/env python3
"""drum_solo.py - writes solo.mid: a two-minute General MIDI drum solo on channel 10.

It is built around one 3-3-2 motif and a quiet answer phrase. Every stroke is
assigned to a limb (two hands, two feet), and a resolver enforces physical
limits, so no more than two hands and two feet ever strike at once.
The performance has a surging tempo map, phrase rushing and laying back,
micro-timing and shaped velocities.
A fixed seed makes every run write an identical file.
"""
import bisect
import math
import random

import mido

PPQ = 960
SEED = 1971
FINAL_HIT_SEC = 118.0
TAIL_SEC = 2.0
SEG = 0.5
OUTFILE = 'solo.mid'

NOTE = {'K': 36, 'K2': 35, 'S': 38, 'X': 37, 'HH': 42, 'HO': 46, 'HP': 44,
        'T1': 50, 'T2': 48, 'T3': 47, 'T4': 45, 'F1': 43, 'F2': 41,
        'C1': 49, 'C2': 57, 'RD': 51, 'RB': 53, 'CH': 52, 'SP': 55,
        'CB': 56, 'WH': 76, 'WL': 77}
POS = {'HH': -3.0, 'HO': -3.0, 'CH': -2.6, 'SP': -2.5, 'C1': -2.1,
       'S': -1.0, 'X': -1.0, 'T1': -0.6, 'T2': 0.1, 'T3': 0.8, 'T4': 1.3,
       'CB': 1.5, 'WH': 1.6, 'WL': 1.6, 'C2': 1.8, 'F1': 2.0, 'RB': 2.2,
       'RD': 2.5, 'F2': 2.6, 'K': 0.0, 'K2': 0.0, 'HP': 0.0}
GAIN = {'HH': 0.85, 'HO': 0.85, 'RD': 0.86, 'RB': 0.82, 'C1': 0.93, 'C2': 0.93,
        'CH': 0.90, 'SP': 0.88, 'CB': 0.72, 'WH': 0.78, 'WL': 0.80, 'X': 0.95}
CYMBALS = ('C1', 'C2', 'CH', 'SP', 'RD', 'RB', 'HO')
TOMS = ('T1', 'T2', 'T3', 'T4', 'F1', 'F2')
LIMBS = ('R', 'L', 'RF', 'LF')
LIMB_IDX = {'R': 0, 'L': 1, 'RF': 2, 'LF': 3}
MOTIF = (0, 3, 6, 8, 11, 14)


def bar(n):
    return 1.0 + 4.0 * (n - 1)


def lerp(a, b, x):
    return a + (b - a) * x


def smooth(x):
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


def C(voice):
    return lambda i, h, a, x: voice


class Stroke(object):
    __slots__ = ('t', 'limb', 'voice', 'lvl', 'prio', 'tags', 'ms', 'main',
                 'off', 'tick', 'sec', 'vel', 'dur', 'keep', 'idx')

    def __init__(self, t, limb, voice, lvl, prio, tags, ms=0.0, main=None):
        self.t, self.limb, self.voice, self.lvl = t, limb, voice, lvl
        self.prio, self.tags, self.ms, self.main = prio, tags, ms, main
        self.off, self.tick, self.sec, self.vel = 0.0, 0, 0.0, 64
        self.dur, self.keep, self.idx = 1, True, 0


class Drummer(object):
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.strokes = []
        self.times = {}
        for limb in LIMBS:
            self.times[limb] = []
        self.rushes = []
        self.leans = []
        self.anchors = [
            (0.0, 112.0), (bar(1), 113.0), (bar(4) + 2.0, 114.0), (bar(5), 115.5),
            (bar(7), 116.5), (bar(9), 116.5), (bar(13), 117.5), (bar(17), 118.5),
            (bar(21), 120.5), (bar(24), 122.5), (bar(24) + 3.5, 121.0), (bar(25), 113.0),
            (bar(26), 110.0), (bar(29), 110.5), (bar(30), 113.0), (bar(31), 117.0),
            (bar(35), 118.5), (bar(38), 120.5), (bar(39), 120.5), (bar(43), 122.5),
            (bar(46), 124.5), (bar(47), 126.5), (bar(51), 128.0), (bar(53), 128.5),
            (bar(56), 130.5), (bar(57), 130.5), (bar(59), 132.0), (bar(60), 132.0),
            (bar(61), 131.0)]
        self.phase = [self.rng.uniform(0.0, 2.0 * math.pi) for _ in range(3)]
        self.seg_us, self.seg_sec = [], []
        self.seg_ticks = int(PPQ * SEG)
        self.nseg = 0

    # ---------------------------------------------------------------- tempo
    def base_bpm(self, t):
        a = self.anchors
        if t <= a[0][0]:
            return a[0][1]
        for i in range(1, len(a)):
            if t < a[i][0]:
                t0, b0 = a[i - 1]
                t1, b1 = a[i]
                return b0 + (b1 - b0) * smooth((t - t0) / (t1 - t0))
        return a[-1][1]

    def tempo_mult(self, t):
        m = 1.0
        for t0, t1, amt, rel in self.rushes:
            if t0 <= t < t1:
                m *= 1.0 + amt * smooth((t - t0) / (t1 - t0))
            elif rel > 0.0 and t1 <= t < t1 + rel:
                m *= 1.0 + amt * (1.0 - smooth((t - t1) / rel))
        return m

    def drift(self, t):
        p = self.phase
        return (1.0 + 0.0045 * math.sin(2 * math.pi * t / 23.0 + p[0])
                + 0.0030 * math.sin(2 * math.pi * t / 9.7 + p[1])
                + 0.0015 * math.sin(2 * math.pi * t / 4.3 + p[2]))

    def lean_ms(self, t):
        o = 0.0
        for t0, t1, m0, m1 in self.leans:
            if t0 <= t < t1:
                o += lerp(m0, m1, (t - t0) / (t1 - t0))
        return o

    def rush(self, t0, t1, amt, rel=2.0):
        self.rushes.append((t0, t1, amt, rel))

    def lean(self, t0, t1, m0, m1):
        self.leans.append((t0, t1, m0, m1))

    # ----------------------------------------------------------- primitives
    def hit(self, t, limb, voice, lvl, prio=3, tags=(), ms=0.0, main=None):
        s = Stroke(t, limb, voice, lvl, prio, tags, ms, main)
        self.strokes.append(s)
        bisect.insort(self.times[limb], t)
        return s

    def busy(self, limb, t, ms):
        w = ms / 1000.0 * self.base_bpm(t) / 60.0
        lst = self.times[limb]
        i = bisect.bisect_left(lst, t - w)
        return i < len(lst) and lst[i] <= t + w

    def kick(self, t, lvl=0.85, prio=4, limb='RF'):
        if self.busy(limb, t, 95):
            return None
        return self.hit(t, limb, 'K', lvl, prio, ('acc',) if lvl >= 0.7 else ())

    def hat(self, t0, t1, step=1.0, lvl=0.42, prio=2):
        t = t0
        while t < t1 - 1e-6:
            if not self.busy('LF', t, 95):
                self.hit(t, 'LF', 'HP', lvl * self.rng.uniform(0.9, 1.1), prio, ('foot',))
            t += step

    @staticmethod
    def grid(t0, t1, step):
        n = int(round((t1 - t0) / step))
        return [t0 + i * step for i in range(n)]

    def ghosts(self, times, limb, voice, prob, lvl, avoid=(), win=85, prio=2):
        other = 'L' if limb == 'R' else 'R'
        for t in times:
            if self.rng.random() >= prob:
                continue
            if any(abs(t - a) < 0.03 for a in avoid):
                continue
            if self.busy(limb, t, win) or self.busy(other, t, 12):
                continue
            self.hit(t, limb, voice, lvl * self.rng.uniform(0.88, 1.12), prio, ('ghost',))

    def double_bass(self, t0, n, sub, lvl, acc_lvl, step_up=0.0):
        for k in range(n):
            l = (acc_lvl if k % sub == 0 else lvl) + step_up * k
            self.hit(t0 + k / float(sub), 'RF' if k % 2 == 0 else 'LF', 'K', l, 3, ())

    def pat(self, t0, sub, stick, orch, tap=(0.45, 0.45), acc=(0.85, 0.85),
            prio=3, curve=1.0, tags=()):
        """Sticking string: R/L accent, r/l tap, K/k kick, D/d left-foot kick,
        H/h hat pedal, '.' rest. orch(i, hand, accented, progress) -> voice."""
        step = 1.0 / sub
        n = len(stick)
        prev = None
        for i, ch in enumerate(stick):
            if ch == '.':
                prev = None
                continue
            t = t0 + i * step
            x = (i / float(n - 1)) ** curve if n > 1 else 1.0
            a = ch.isupper()
            lt = lerp(tap[0], tap[1], x)
            la = lerp(acc[0], acc[1], x)
            c = ch.upper()
            if c in ('R', 'L'):
                v = orch(i, c, a, x)
                if v is not None:
                    tg = tags + (('acc',) if a else ()) + (('dbl',) if prev == c else ())
                    self.hit(t, c, v, la if a else lt, prio + (1 if a else 0), tg)
                prev = c
            elif c == 'K':
                self.hit(t, 'RF', 'K', (la - 0.04) if a else min(1.0, lt + 0.18), prio,
                         tags + (('acc',) if a else ()))
            elif c == 'D':
                self.hit(t, 'LF', 'K', (la - 0.06) if a else min(1.0, lt + 0.14), prio,
                         tags + (('acc',) if a else ()))
            elif c == 'H':
                self.hit(t, 'LF', 'HP', 0.5 if a else 0.4, max(1, prio - 1), tags + ('foot',))

    def flam(self, t, h, v, lvl, prio=5, gv=None):
        o = 'L' if h == 'R' else 'R'
        g = self.rng.uniform(19.0, 31.0)
        m = self.hit(t, h, v, lvl, prio, ('acc', 'flam'))
        self.hit(t, o, gv if gv is not None else v, 0.1 + 0.26 * lvl, 1, ('grace',), -g, m)
        return m

    def drag(self, t, h, v, lvl, prio=5, gv='S'):
        o = 'L' if h == 'R' else 'R'
        d = self.rng.uniform(36.0, 44.0)
        m = self.hit(t, h, v, lvl, prio, ('acc', 'drag'))
        self.hit(t, o, gv, 0.24, 1, ('grace',), -2.0 * d, m)
        self.hit(t, o, gv, 0.28, 1, ('grace', 'dbl'), -d, m)
        return m

    def motif(self, t0, voices=('S', 'T1', 'T3', 'F2', 'S', 'C1'),
              hands=('R', 'R', 'R', 'R', 'L', 'L'), lv=(0.96, 0.84, 0.8, 0.9, 0.9, 0.95),
              flams=(4,), drags=(), kicks=(0, 3, 5), pos=MOTIF, unit=0.25, prio=5,
              klv=None, scale=1.0):
        times = []
        for k in range(len(pos)):
            t = t0 + pos[k] * unit
            v, h = voices[k], hands[k]
            l = min(1.0, lv[k] * scale)
            if k in flams:
                self.flam(t, h, v, l, prio)
            elif k in drags:
                self.drag(t, h, v, l, prio)
            else:
                self.hit(t, h, v, l, prio, ('acc', 'motif'))
            if k in kicks:
                self.kick(t, (l - 0.04) if klv is None else klv, prio)
            times.append(t)
        return times

    def groove(self, b, cym='HH', cpos=(0, 2, 4, 6, 8, 10, 12, 14), kicks=MOTIF, bb=(4, 12),
               gp=0.5, opens=(), crash=None, bell=(), punches=None, feet=(), drags=(),
               lh=None, span=(0, 16), swing=0.12, glv=0.2, clv=(0.64, 0.5)):
        r = self.rng

        def sw(p):
            return b + (p + (swing if p % 2 else 0.0)) / 4.0
        punches = punches or {}
        for p in cpos:
            if p < span[0] or p >= span[1] or p in drags or p in punches:
                continue
            v, lvl = cym, (clv[0] if p % 4 == 0 else clv[1])
            if crash is not None and p == 0:
                v, lvl = crash, 0.92
            elif p in opens:
                v, lvl = 'HO', 0.6
            elif p in bell:
                v, lvl = 'RB', 0.62
            big = v in ('C1', 'C2')
            self.hit(sw(p), 'R', v, lvl * r.uniform(0.93, 1.07), 4 if big else 3,
                     ('acc',) if big else ())
        for p, v in punches.items():
            self.hit(sw(p), 'R', v, 0.9, 5, ('acc',))
            self.kick(sw(p), 0.88, 5)
        for p in bb:
            if span[0] <= p < span[1]:
                if p in drags:
                    self.drag(sw(p), 'L', 'S', 0.88, 4)
                else:
                    self.hit(sw(p), 'L', 'S', 0.86 * r.uniform(0.95, 1.04), 4, ('acc', 'bb'))
        if lh:
            for p, v in lh.items():
                self.hit(sw(p), 'L', v, 0.66 * r.uniform(0.94, 1.06), 4, ('acc',))
        for p in kicks:
            if span[0] <= p < span[1]:
                self.kick(sw(p), 0.84 if p % 4 == 0 else 0.72)
        for p in opens:
            if not self.busy('LF', sw(p + 2), 95):
                self.hit(sw(p + 2), 'LF', 'HP', 0.5, 2, ('foot',))
        for p in feet:
            if span[0] <= p < span[1] and not self.busy('LF', sw(p), 95):
                self.hit(sw(p), 'LF', 'HP', 0.44, 2, ('foot',))
        self.ghosts([sw(p) for p in range(span[0], span[1])], 'L', 'S', gp, glv,
                    avoid=[sw(p) for p in bb])

    # ------------------------------------------------------------- sections
    def intro(self):
        self.pat(0.5, 6, 'lrl', C('S'), tap=(0.26, 0.5))
        self.motif(bar(1))                                   # the statement
        b = bar(2)                                           # the answer
        self.hat(b + 1, b + 4, 2.0, 0.40)
        self.pat(b + 0.5, 4, 'rlrlrl', C('S'), tap=(0.16, 0.3))
        tv = ('T1', 'T2', 'T3', 'F1')
        self.pat(b + 2.0, 4, 'RlRlRlRl', lambda i, h, a, x: tv[i // 2] if h == 'R' else 'S',
                 tap=(0.2, 0.3), acc=(0.5, 0.74))
        self.kick(b + 2.0, 0.55)
        self.kick(b + 3.5, 0.66)
        b = bar(3)
        self.hat(b + 1, b + 4, 2.0, 0.42)
        mt = self.motif(b, voices=('S', 'T2', 'T4', 'F2', 'S', 'C2'),
                        hands=('R', 'R', 'R', 'R', 'L', 'R'), lv=(0.92, 0.82, 0.8, 0.88, 0.88, 0.93))
        self.ghosts(self.grid(b, b + 4, 0.25), 'L', 'S', 0.5, 0.19, avoid=mt)
        b = bar(4)
        self.hat(b + 1, b + 2, 2.0, 0.40)
        self.pat(b, 4, 'rrllrrll', C('S'), tap=(0.2, 0.38))
        p4 = ('S', 'S', 'T1', 'T1', 'T2', 'T2', 'T3', 'T3', 'F1', 'F1', 'F2', 'F2')
        self.pat(b + 2, 6, 'RlrLrlRlrLrl', lambda i, h, a, x: p4[i], tap=(0.48, 0.72), acc=(0.72, 0.92))
        self.kick(b + 2, 0.72)
        self.kick(b + 3, 0.82)
        self.rush(b + 2, b + 4, 0.02)
        self.lean(b + 2, b + 4, 0.0, -6.0)
        b = bar(5)
        self.hat(b + 1, b + 4, 1.0, 0.42)
        mt = self.motif(b, voices=('C2', 'T1', 'T3', 'F2', 'S', 'C1'),
                        hands=('R', 'L', 'R', 'R', 'L', 'R'), kicks=(0, 2, 3, 5), drags=(2,))
        self.ghosts(self.grid(b, b + 4, 0.25), 'L', 'S', 0.72, 0.21, avoid=mt)
        b = bar(6)
        self.hat(b, b + 4, 1.0, 0.44)
        self.hit(b + 3.75, 'L', 'S', 0.72, 4, ('acc',))
        mt = self.motif(b, voices=('S', 'T1', 'T3', 'F2', 'T4', 'T2'),
                        hands=('R', 'L', 'R', 'R', 'R', 'R'), flams=(), kicks=(0, 3),
                        lv=(0.9, 0.8, 0.8, 0.88, 0.8, 0.84))
        self.ghosts(self.grid(b, b + 4, 0.25), 'L', 'S', 0.75, 0.22, avoid=mt)
        b = bar(7)                                           # diminution in 32nds
        self.hat(b + 0.5, b + 4, 1.0, 0.42)
        t7 = ('T1', 'T2', 'T3', 'F1')
        self.pat(b, 8, 'RllRllRl' * 4, lambda i, h, a, x: t7[i // 8] if h == 'R' else 'S',
                 tap=(0.2, 0.5), acc=(0.6, 0.9))
        for k in range(4):
            self.kick(b + k, 0.62 + 0.08 * k)
        self.rush(b, b + 4, 0.012)
        b = bar(8)                                           # the long fall
        p8 = ('T1',) * 3 + ('T2',) * 3 + ('T3',) * 3 + ('T4',) * 3 + ('F1',) * 3 + ('F2',) * 3
        self.pat(b, 6, 'RlrLrl' * 3, lambda i, h, a, x: p8[i], tap=(0.5, 0.72), acc=(0.75, 0.92))
        for k in range(6):
            self.kick(b + 0.5 * k, 0.7 + 0.03 * k)
        self.pat(b + 3, 8, 'rlrlrlrl', C('S'), tap=(0.45, 0.9))
        self.rush(b, b + 4, 0.025)
        self.lean(b + 2, b + 4, 0.0, -7.0)

    def groove_section(self):
        self.groove(bar(9), crash='C2', opens=(14,), gp=0.45)
        self.groove(bar(10), cpos=(0, 2, 4, 6, 8, 10, 12, 14, 15), kicks=(0, 3, 6, 10, 11),
                    opens=(6,), drags=(12,), gp=0.55)
        self.groove(bar(11), cpos=(0, 2, 4, 6, 8, 10), punches={11: 'C1', 14: 'C2'}, gp=0.5)
        b = bar(12)
        self.groove(b, kicks=(0, 3, 6), bb=(4,), span=(0, 8), gp=0.5)
        t12 = ('T1', 'T2', 'F1', 'F2')
        self.pat(b + 2, 6, 'RlkRlkRlkRl.', lambda i, h, a, x: t12[i // 3],
                 tap=(0.55, 0.7), acc=(0.76, 0.92))
        self.rush(b + 2, b + 4, 0.015)
        self.lean(b + 2, b + 4, 0.0, -5.0)
        self.groove(bar(13), cym='RD', crash='C2', kicks=(0, 3, 6, 10), bell=(14,),
                    feet=(4, 12), gp=0.5)
        self.groove(bar(14), cym='RD', kicks=(0, 8, 14), bb=(12,), feet=(4, 12),
                    lh={3: 'T1', 6: 'S', 9: 'T2'}, gp=0.45)
        self.groove(bar(15), cym='CB', cpos=MOTIF, kicks=(0, 8, 10), feet=(2, 6, 10, 14),
                    gp=0.5, clv=(0.72, 0.62))
        b = bar(16)
        self.groove(b, cym='RD', kicks=(0, 3, 6), bb=(4,), feet=(4,), span=(0, 8), gp=0.5)
        d16 = ('T1',) * 4 + ('T2',) * 4 + ('T4',) * 4 + ('F2',) * 4
        self.pat(b + 2, 8, 'RrLl' * 4, lambda i, h, a, x: d16[i], tap=(0.5, 0.8), acc=(0.62, 0.92))
        self.kick(b + 2, 0.8)
        self.kick(b + 3, 0.86)
        self.rush(b + 2, b + 4, 0.02)
        self.lean(b + 2, b + 4, 0.0, -6.0)

    def travel(self):
        r = self.rng
        b = bar(17)                          # accents every 4 sextuplets, down the kit
        self.hat(b, b + 4, 1.0, 0.42)
        g17 = ('C2', 'T1', 'T2', 'T3', 'F1', 'F2')
        self.pat(b, 6, 'Rlrl' * 6,
                 lambda i, h, a, x: ('C2' if i == 0 else 'S') if i < 4 else g17[i // 4],
                 tap=(0.42, 0.62), acc=(0.84, 0.94))
        for g in range(6):
            self.kick(b + g * 4 / 6.0, 0.8)
        b = bar(18)                          # six-stroke rolls climbing back up
        self.hat(b, b + 4, 1.0, 0.42)
        r18, l18 = ('F2', 'F1', 'T3', 'C2'), ('S', 'T1', 'S', 'T1')
        self.pat(b, 6, 'RllrrL' * 4,
                 lambda i, h, a, x: r18[i // 6] if i % 6 == 0 else (l18[i // 6] if i % 6 == 5 else 'S'),
                 tap=(0.3, 0.5), acc=(0.78, 0.92))
        for k in range(4):
            self.kick(b + k, 0.78)
        b = bar(19)                          # paradiddle-diddles
        self.hat(b, b + 4, 1.0, 0.42)
        opts = (('F1', 'F1'), ('F2', 'F1'), ('C2', 'T3'), ('T3', 'T4'), ('F2', 'F2'), ('C2', 'F1'))
        per = [opts[r.randrange(len(opts))] for _ in range(4)]
        self.pat(b, 6, 'Rlrrll' * 4,
                 lambda i, h, a, x: 'S' if h == 'L' else (per[i // 6][0] if i % 6 == 0 else per[i // 6][1]),
                 tap=(0.38, 0.56), acc=(0.82, 0.9))
        for k in range(4):
            self.kick(b + k, 0.78)
        b = bar(20)                          # paradiddles, then zig-zag doubles
        self.hat(b, b + 2, 1.0, 0.42)
        self.pat(b, 4, 'RlrrLrll', lambda i, h, a, x: ('F1' if h == 'R' else 'T1') if a else 'S',
                 tap=(0.36, 0.48), acc=(0.8, 0.84))
        zr, zl = ('F1', 'F2', 'F1', 'T4'), ('T1', 'T2', 'T1', 'S')
        self.pat(b + 2, 8, 'RrLl' * 4, lambda i, h, a, x: zr[i // 4] if h == 'R' else zl[i // 4],
                 tap=(0.42, 0.8), acc=(0.6, 0.9))
        for t, l in ((b, 0.8), (b + 1, 0.75), (b + 2, 0.78), (b + 3, 0.86)):
            self.kick(t, l)
        self.rush(b + 2, b + 4, 0.02)
        self.lean(b + 2, b + 4, 0.0, -6.0)
        b = bar(21)                          # motif hidden in a river of 16ths
        self.hat(b, b + 4, 1.0, 0.42)
        a21 = {0: 'S', 3: 'T1', 6: 'T3', 8: 'F2', 11: 'S', 14: 'C1'}
        state = {'R': 'S'}

        def o21(i, h, a, x):
            if a:
                v = a21[i]
                if h == 'R':
                    state['R'] = v if v in TOMS else 'S'
                return v
            return state['R'] if h == 'R' else 'S'
        self.pat(b, 4, 'RlrLrlRlRlrLrlRl', o21, tap=(0.3, 0.42), acc=(0.88, 0.95))
        for p in (0, 8, 14):
            self.kick(b + p / 4.0, 0.86)
        b = bar(22)
        self.hat(b, b + 4, 1.0, 0.42)
        mt = self.motif(b, voices=('S', 'T1', 'T4', 'F1', 'S', 'C2'),
                        hands=('R', 'L', 'R', 'R', 'L', 'R'), drags=(1, 2),
                        lv=(0.92, 0.86, 0.84, 0.88, 0.9, 0.95))
        self.ghosts(self.grid(b, b + 4, 0.25), 'L', 'S', 0.8, 0.24, avoid=mt)
        b = bar(23)                          # sextuplet wave down and up
        self.hat(b, b + 4, 1.0, 0.44)
        w23 = ('S', 'T1', 'T2', 'T3', 'T4', 'F1', 'F2', 'F1', 'T4', 'T3', 'T2', 'T1')
        self.pat(b, 6, 'Rlrlrl' * 4, lambda i, h, a, x: w23[i // 2], tap=(0.45, 0.72), acc=(0.8, 0.95))
        for k in range(4):
            self.kick(b + k, 0.8)
        self.kick(b + 3.5, 0.85)
        self.rush(b, b + 4, 0.015)
        b = bar(24)                          # swelling double-stroke roll, a breath
        self.hat(b, b + 4, 1.0, 0.40)
        self.pat(b, 8, 'rrll' * 7 + 'rr..', C('S'), tap=(0.13, 0.98), curve=1.7)
        self.kick(b + 2, 0.6)
        self.kick(b + 3, 0.76)
        self.kick(b + 3.5, 0.86)
        self.rush(b + 3, b + 4, -0.02, 0.5)
        self.lean(b + 3, b + 4, 0.0, 6.0)

    def whisper(self):
        r = self.rng
        b = bar(25)                          # the crash, then space
        self.hit(b, 'R', 'C2', 1.0, 6, ('acc',))
        self.hit(b, 'L', 'C1', 0.95, 6, ('acc',))
        self.kick(b, 0.95, 6)
        self.hat(b + 3, b + 4, 1.0, 0.34)
        self.pat(b + 2.5, 4, 'rlrlrl', C('S'), tap=(0.13, 0.24))
        self.lean(bar(25), bar(29), 5.0, 5.0)
        b = bar(26)                          # motif on wood blocks
        self.hat(b, b + 4, 1.0, 0.34)
        mt = self.motif(b, voices=('WL', 'WH', 'WH', 'WL', 'WH', 'RB'), hands=('R',) * 6,
                        flams=(), kicks=(0, 3), lv=(0.62, 0.5, 0.52, 0.6, 0.5, 0.56), prio=4, klv=0.34)
        self.hit(b + 1, 'L', 'S', 0.42, 3, ('acc',))
        self.hit(b + 3, 'L', 'S', 0.45, 3, ('acc',))
        self.ghosts(self.grid(b, b + 4, 0.25), 'L', 'S', 0.7, 0.15, avoid=mt)
        b = bar(27)                          # motif as a cross-stick clave
        self.hat(b + 1, b + 4, 2.0, 0.36)
        for p in range(0, 16, 2):
            self.hit(b + p / 4.0, 'R', 'RD', (0.42 if p % 4 == 0 else 0.34) * r.uniform(0.93, 1.07), 3, ())
        xl = (0.52, 0.46, 0.48, 0.52, 0.46, 0.5)
        for k, p in enumerate(MOTIF):
            self.hit(b + p / 4.0, 'L', 'X', xl[k], 4, ('acc',))
        for p, l in ((0, 0.42), (6, 0.3), (8, 0.4), (14, 0.3)):
            self.kick(b + p / 4.0, l)
        b = bar(28)                          # bell motif, songo-ish left hand
        self.hat(b, b + 4, 1.0, 0.36)
        bl = (0.56, 0.46, 0.5, 0.54, 0.46, 0.52)
        for k, p in enumerate(MOTIF):
            self.hit(b + p / 4.0, 'R', 'RB', bl[k], 4, ('acc',))
        songo = ((1, 'S', 0.16), (2, 'S', 0.18), (4, 'T1', 0.42), (5, 'S', 0.16), (7, 'S', 0.18),
                 (9, 'S', 0.16), (10, 'T2', 0.44), (12, 'T1', 0.4), (13, 'S', 0.17), (15, 'S', 0.2))
        for p, v, l in songo:
            g = l < 0.3
            self.hit(b + p / 4.0, 'L', v, l * r.uniform(0.9, 1.1), 2 if g else 3,
                     ('ghost',) if g else ('acc',))
        for p, l in ((0, 0.36), (6, 0.34), (14, 0.36)):
            self.kick(b + p / 4.0, l)
        b = bar(29)                          # accents in threes emerge
        self.hat(b, b + 4, 1.0, 0.40)
        rt = ('S', 'S', 'T3', 'T4', 'F1')
        self.pat(b, 4, 'RlrLrlRlrLrlRlrl',
                 lambda i, h, a, x: (rt[i // 3] if h == 'R' else 'T2') if (a and i >= 6) else 'S',
                 tap=(0.15, 0.42), acc=(0.3, 0.82), curve=1.2)
        self.kick(b + 2.25, 0.62)
        self.kick(b + 3.0, 0.74)
        self.rush(b + 2, bar(31), 0.03)
        b = bar(30)                          # the roll travels down the kit
        self.hat(b, b + 2, 0.5, 0.45)
        t30 = ('S', 'S', 'T1', 'T2', 'T3', 'T4', 'F1', 'F2')
        self.pat(b, 8, 'Rrll' * 8, lambda i, h, a, x: t30[i // 4], tap=(0.3, 0.9),
                 acc=(0.48, 1.0), curve=1.3)
        for k in range(4):
            self.kick(b + 2 + 0.5 * k, 0.66 + 0.07 * k)
        self.lean(b, b + 4, 0.0, -8.0)

    def poly(self):
        b = bar(31)                          # hand-hand-foot threes over two bars
        self.hat(b, b + 8, 1.0, 0.44)
        cyc = ('C2', 'T1', 'T3', 'F1', 'RB', 'T2', 'T4', 'F2', 'C1', 'S', 'C2')
        self.pat(b, 4, 'Rlk' * 10 + 'Rl', lambda i, h, a, x: cyc[i // 3] if h == 'R' else 'S',
                 tap=(0.36, 0.5), acc=(0.84, 0.92))
        self.kick(b, 0.9, 5)
        b = bar(33)                          # groups of five climbing the toms
        self.hat(b, b + 8, 1.0, 0.44)
        up5 = ('F2', 'F1', 'T4', 'T3', 'T2', 'T1')
        self.pat(b, 4, 'Rlrlk' * 6 + 'RL',
                 lambda i, h, a, x: ('C2' if h == 'R' else 'S') if i >= 30 else (up5[i // 5] if a else 'S'),
                 tap=(0.26, 0.42), acc=(0.82, 0.92))
        b = bar(35)                          # motif augmented, each hit approached by a swell
        self.hat(b + 0.5, b + 8, 1.0, 0.42)
        self.hit(b, 'R', 'S', 0.92, 5, ('acc',))
        self.hit(b, 'L', 'C1', 0.92, 5, ('acc',))
        self.kick(b, 0.92, 5)
        self.hit(b + 1.5, 'R', 'T1', 0.88, 5, ('acc',))
        self.kick(b + 1.5, 0.85, 5)
        self.hit(b + 3.0, 'R', 'T3', 0.88, 5, ('acc',))
        self.kick(b + 3.0, 0.85, 5)
        self.hit(b + 4.0, 'R', 'F2', 0.94, 5, ('acc',))
        self.hit(b + 4.0, 'L', 'C1', 0.9, 5, ('acc',))
        self.kick(b + 4.0, 0.92, 5)
        self.flam(b + 5.5, 'L', 'S', 0.92)
        self.kick(b + 5.5, 0.86, 5)
        self.hit(b + 7.0, 'R', 'C2', 0.96, 5, ('acc',))
        self.hit(b + 7.0, 'L', 'CH', 0.9, 5, ('acc',))
        self.kick(b + 7.0, 0.95, 5)
        self.pat(b + 0.25, 4, 'lrlrl', C('S'), tap=(0.14, 0.5))
        self.pat(b + 1.75, 4, 'lrlrl', C('S'), tap=(0.16, 0.54))
        self.pat(b + 3.25, 4, 'lrl', lambda i, h, a, x: 'T2' if h == 'L' else 'T4', tap=(0.2, 0.56))
        self.pat(b + 4.25, 4, 'lrlrl', C('S'), tap=(0.15, 0.55))
        self.pat(b + 5.75, 4, 'rlrlr', lambda i, h, a, x: 'T1' if h == 'L' else 'T3', tap=(0.2, 0.62))
        self.pat(b + 7.25, 4, 'rlr', C('S'), tap=(0.45, 0.7))
        b = bar(37)                          # quintuplets down and back
        self.hat(b, b + 4, 1.0, 0.42)
        p37 = ('T1', 'T1', 'T2', 'T2', 'T3', 'T3', 'T4', 'T4', 'F1', 'F1',
               'F2', 'F2', 'F1', 'F1', 'T4', 'T4', 'T3', 'T3', 'T2', 'T2')
        self.pat(b, 5, 'RlrlrLrlrlRlrlrLrlrl', lambda i, h, a, x: p37[i], tap=(0.42, 0.62), acc=(0.8, 0.9))
        for k in range(4):
            self.kick(b + k, 0.8)
        b = bar(38)                          # flam taps tumbling down
        seq = (('R', 'T3'), ('L', 'T1'), ('R', 'F1'), ('L', 'T2'), ('R', 'F2'), ('L', 'S'))
        for k, (h, v) in enumerate(seq):
            t = b + 0.5 * k
            self.flam(t, h, v, 0.84 + 0.02 * k)
            self.hit(t + 0.25, h, v, 0.4 + 0.02 * k, 3, ())
        for k in range(4):
            self.kick(b + k, 0.8)
        self.pat(b + 3, 8, 'rlrlrlr.', C('S'), tap=(0.45, 0.92))
        self.rush(b + 2, b + 4, 0.02)
        self.lean(b + 2, b + 4, 0.0, -6.0)

    def triplets(self):
        r = self.rng
        b = bar(39)                          # motif as quarter-note triplets
        self.hat(b + 1, b + 4, 2.0, 0.42)
        self.hit(b, 'L', 'C1', 0.92, 5, ('acc',))
        mt = self.motif(b, pos=(0, 2, 4, 6, 8, 10), unit=1.0 / 3.0)
        self.ghosts(self.grid(b, b + 4, 1.0 / 3.0), 'L', 'S', 0.7, 0.2, avoid=mt)
        b = bar(40)                          # hand-hand-foot triplets
        self.hat(b, b + 4, 1.0, 0.42)
        t40 = ('T1', 'T1', 'T2', 'T2', 'T3', 'T4', 'F1', 'F2')
        self.pat(b, 6, 'Rlk' * 7 + 'Rl.', lambda i, h, a, x: t40[i // 3], tap=(0.5, 0.72), acc=(0.76, 0.92))
        b = bar(41)                          # 12/8 floor-tom groove
        self.hat(b + 1, b + 4, 2.0, 0.45)
        for k in range(12):
            v = 'F1' if (k // 3) % 2 == 0 else 'F2'
            if k % 3 == 0:
                self.hit(b + k / 3.0, 'R', v, 0.8 * r.uniform(0.95, 1.05), 4, ('acc',))
            else:
                self.hit(b + k / 3.0, 'R', v, (0.5 if k % 3 == 2 else 0.4) * r.uniform(0.92, 1.08), 3, ())
        self.hit(b + 1, 'L', 'S', 0.86, 4, ('acc', 'bb'))
        self.hit(b + 3, 'L', 'S', 0.9, 4, ('acc', 'bb'))
        for t in (b, b + 1 + 2.0 / 3.0, b + 2, b + 3 + 2.0 / 3.0):
            self.kick(t, 0.8)
        self.ghosts(self.grid(b, b + 4, 1.0 / 3.0), 'L', 'S', 0.45, 0.2, avoid=(b + 1, b + 3))
        b = bar(42)                          # triplet doubles climbing twice
        u42 = ('F2', 'F1', 'T4', 'T3', 'T2', 'T1')
        self.pat(b, 6, 'RrLl' * 6, lambda i, h, a, x: u42[(i // 2) % 6], tap=(0.42, 0.8), acc=(0.62, 0.95))
        for k in range(4):
            self.kick(b + k, 0.78 + 0.04 * k)
        self.rush(b + 2, b + 4, 0.02)
        self.lean(b + 2, b + 4, 0.0, -6.0)
        b = bar(43)                          # hemiola motif over double-bass triplets
        mt = self.motif(b, pos=(0, 2, 4, 6, 8, 10), unit=1.0 / 3.0,
                        voices=('C2', 'CH', 'T2', 'F1', 'S', 'C1'), hands=('R', 'L', 'R', 'R', 'L', 'R'),
                        kicks=(), lv=(0.95, 0.88, 0.84, 0.9, 0.9, 0.95))
        self.double_bass(b, 12, 3, 0.6, 0.72)
        self.ghosts(self.grid(b, b + 4, 1.0 / 3.0), 'L', 'S', 0.6, 0.22, avoid=mt)
        b = bar(44)                          # sextuplets accented in fives
        self.hat(b, b + 4, 1.0, 0.42)
        st44 = ''.join((('R' if i % 2 == 0 else 'L') if i % 5 == 0 else ('r' if i % 2 == 0 else 'l'))
                       for i in range(24))
        g44 = ('T1', 'T2', 'F1', 'F2')
        self.pat(b, 6, st44, lambda i, h, a, x: g44[i // 5] if i < 20 else ('C2' if i == 20 else 'S'),
                 tap=(0.44, 0.66), acc=(0.82, 0.94))
        for i in (0, 5, 10, 15, 20):
            self.kick(b + i / 6.0, 0.82)
        b = bar(45)                          # hands-hands-foot-foot
        t45 = ('T1', 'T2', 'T3', 'T4', 'F1', 'F2')
        self.pat(b, 6, 'Rlkd' * 6, lambda i, h, a, x: t45[i // 4], tap=(0.5, 0.74), acc=(0.78, 0.94))
        self.rush(b, bar(47), 0.025)
        b = bar(46)                          # six-stroke rolls, then a dive
        r46, l46 = ('F1', 'F2', 'C2'), ('T1', 'S', 'T2')
        self.pat(b, 6, 'RllrrL' * 3,
                 lambda i, h, a, x: r46[i // 6] if i % 6 == 0 else (l46[i // 6] if i % 6 == 5 else 'S'),
                 tap=(0.36, 0.56), acc=(0.84, 0.94))
        dive = ('T1', 'T1', 'T2', 'T2', 'T3', 'T3', 'F1', 'F1')
        self.pat(b + 3, 8, 'rlrlrlr.', lambda i, h, a, x: dive[i], tap=(0.6, 0.95))
        for t in (b, b + 1, b + 2, b + 3, b + 3.5):
            self.kick(t, 0.84)
        self.lean(b, b + 4, 0.0, -6.0)

    def climax(self):
        b = bar(47)                          # motif over double-bass 16ths
        self.hit(b, 'L', 'C1', 0.92, 6, ('acc',))
        mt = self.motif(b, voices=('C2', 'T1', 'T3', 'F2', 'S', 'CH'),
                        hands=('R', 'L', 'R', 'R', 'L', 'L'), kicks=(),
                        lv=(0.98, 0.88, 0.86, 0.92, 0.92, 0.95))
        self.double_bass(b, 16, 4, 0.62, 0.76)
        self.ghosts(self.grid(b, b + 4, 0.25), 'R', 'S', 0.5, 0.36, avoid=mt)
        self.ghosts(self.grid(b, b + 4, 0.25), 'L', 'S', 0.5, 0.34, avoid=mt)
        b = bar(48)                          # 16th singles, 3-3-2 accents on cymbals
        self.double_bass(b, 16, 4, 0.64, 0.78)
        a48 = {0: 'C2', 3: 'C1', 6: 'F1', 8: 'RB', 11: 'T1', 14: 'C2'}
        self.pat(b, 4, 'RlrLrlRlRlrLrlRl',
                 lambda i, h, a, x: a48[i] if a else (('F1' if i < 8 else 'T3') if h == 'R' else 'S'),
                 tap=(0.4, 0.56), acc=(0.9, 0.96))
        b = bar(49)                          # stabs over sextuplet double bass
        self.double_bass(b, 24, 6, 0.58, 0.7)
        stabs = ((0, (('R', 'C2', 0.96), ('L', 'S', 0.9))), (3, (('L', 'CH', 0.9),)),
                 (6, (('R', 'F1', 0.9), ('L', 'T1', 0.88))), (10, (('R', 'C2', 0.94), ('L', 'S', 0.9))),
                 (12, (('L', 'CH', 0.88),)), (14, (('R', 'T3', 0.9), ('L', 'T2', 0.88))),
                 (15, (('R', 'F2', 0.92),)))
        for p, hs in stabs:
            for h, v, l in hs:
                self.hit(b + p / 4.0, h, v, l, 5, ('acc',))
        b = bar(50)                          # 32nd singles down, sextuplet doubles up
        p50 = ('S', 'S', 'T1', 'T1', 'T2', 'T2', 'T3', 'T3', 'T4', 'T4', 'F1', 'F1',
               'F2', 'F2', 'F2', 'F2')
        self.pat(b, 8, 'RlrlrlrlRlrlrlrl', lambda i, h, a, x: p50[i], tap=(0.55, 0.8), acc=(0.86, 0.94))
        u50 = ('F2', 'F1', 'T4', 'T3', 'T2', 'T1')
        self.pat(b + 2, 6, 'RrLl' * 3, lambda i, h, a, x: u50[i // 2], tap=(0.55, 0.86), acc=(0.72, 0.95))
        for k in range(4):
            self.kick(b + k, 0.84)
            self.hit(b + k + 0.5, 'LF', 'K', 0.7, 3, ())
        self.rush(b, b + 4, 0.015)
        b = bar(51)                          # stop-time
        self.hit(b, 'R', 'C2', 1.0, 6, ('acc',))
        self.hit(b, 'L', 'C1', 0.96, 6, ('acc',))
        self.kick(b, 0.96, 6)
        self.hit(b, 'LF', 'K2', 0.9, 6, ('acc',))
        self.hit(b + 1.5, 'L', 'T1', 0.9, 5, ('acc',))
        self.hit(b + 1.5, 'R', 'F1', 0.92, 5, ('acc',))
        self.kick(b + 1.5, 0.9, 5)
        self.flam(b + 2.75, 'L', 'S', 0.92)
        self.hit(b + 3.0, 'L', 'CH', 0.92, 5, ('acc',))
        self.kick(b + 3.0, 0.9, 5)
        self.hit(b + 3.5, 'L', 'T2', 0.92, 5, ('acc',))
        self.hit(b + 3.5, 'R', 'F2', 0.94, 5, ('acc',))
        self.kick(b + 3.5, 0.92, 5)
        self.rush(b + 0.5, b + 4, -0.025, 1.0)
        b = bar(52)                          # 3-3-2 cell in 32nds explodes around the kit
        f52, n52 = ('C2', 'F1', 'C2', 'F2'), ('T1', 'T2', 'T3', 'T4')
        self.pat(b, 8, 'RllRllRl' * 3 + 'RllRllR.',
                 lambda i, h, a, x: 'S' if h == 'L' else (f52[i // 8] if i % 8 == 0 else n52[i // 8]),
                 tap=(0.42, 0.62), acc=(0.84, 0.97))
        self.double_bass(b, 16, 4, 0.62, 0.76)
        self.rush(b, b + 4, 0.02)
        b = bar(53)                          # call and response
        self.hit(b, 'R', 'C2', 0.95, 5, ('acc',))
        self.hit(b, 'L', 'S', 0.9, 5, ('acc',))
        self.kick(b, 0.9, 5)
        self.hit(b + 0.75, 'L', 'CH', 0.9, 5, ('acc',))
        self.kick(b + 0.75, 0.86, 5)
        self.hit(b + 1.5, 'R', 'RB', 0.88, 5, ('acc',))
        self.hit(b + 1.5, 'L', 'T1', 0.86, 5, ('acc',))
        self.kick(b + 1.5, 0.86, 5)
        self.hit(b + 1.75, 'L', 'SP', 0.72, 4, ('acc',))
        c53 = ('F2', 'F2', 'F1', 'F1', 'T4', 'T4', 'T3', 'T3', 'T2', 'T2', 'T1', 'T1', 'S', 'S', 'S', 'S')
        self.pat(b + 2, 8, 'r' + 'lr' * 7 + 'l', lambda i, h, a, x: c53[i], tap=(0.5, 0.95))
        for t in (b + 2, b + 3):
            self.kick(t, 0.84)
        for t in (b + 2.5, b + 3.5):
            self.hit(t, 'LF', 'K', 0.72, 3, ())
        b = bar(54)                          # four hands, two feet
        g54 = (('T1', 'T1', 'T2', 'T2'), ('T3', 'T3', 'T4', 'T4'), ('F1', 'F1', 'F2', 'F2'),
               ('C2', 'S', 'T1', 'S'))
        self.pat(b, 6, 'Rlrlkd' * 4, lambda i, h, a, x: g54[i // 6][i % 6], tap=(0.55, 0.8), acc=(0.84, 0.96))
        b = bar(55)                          # 32nd doubles zig-zag down and up
        dr, dl = ('T1', 'T2', 'T3', 'F1'), ('S', 'T1', 'T2', 'T4')
        ur, ul = ('F2', 'F1', 'T3', 'T2'), ('F1', 'T4', 'T2', 'T1')

        def o55(i, h, a, x):
            q = (i // 4) % 4
            if i < 16:
                return dr[q] if h == 'R' else dl[q]
            return ur[q] if h == 'R' else ul[q]
        self.pat(b, 8, 'RrLl' * 8, o55, tap=(0.5, 0.86), acc=(0.66, 0.97))
        self.double_bass(b, 16, 4, 0.62, 0.74)
        self.rush(b, bar(57), 0.025)
        self.lean(b, bar(57), 0.0, -6.0)
        b = bar(56)                          # roll swell, three flams
        self.pat(b, 8, 'rrll' * 5 + 'rrl.', lambda i, h, a, x: 'F1' if h == 'R' else 'S',
                 tap=(0.34, 0.9), curve=1.4)
        self.double_bass(b, 12, 4, 0.6, 0.66, step_up=0.02)
        self.flam(b + 3.0, 'L', 'T1', 0.9, gv='T1')
        self.flam(b + 3.0 + 1.0 / 3.0, 'R', 'T3', 0.93, gv='T2')
        self.flam(b + 3.0 + 2.0 / 3.0, 'R', 'F2', 0.97, gv='F1')
        for k in range(3):
            self.kick(b + 3.0 + k / 3.0, 0.9 + 0.02 * k)

    def finale(self):
        b = bar(57)                          # the motif returns at full strength
        self.hit(b, 'L', 'C1', 0.95, 6, ('acc',))
        mt = self.motif(b, scale=1.04, kicks=(0, 1, 2, 3, 5))
        self.hat(b + 1, b + 4, 2.0, 0.5)
        self.ghosts(self.grid(b, b + 4, 0.25), 'L', 'S', 0.6, 0.3, avoid=mt)
        b = bar(58)                          # the answer, no longer a murmur
        self.hat(b + 1, b + 4, 2.0, 0.5)
        self.hit(b, 'L', 'CH', 0.9, 5, ('acc',))
        self.kick(b, 0.9, 5)
        self.pat(b + 0.5, 4, 'rlrlrl', C('S'), tap=(0.42, 0.66))
        t58 = ('T1', 'T2', 'T3', 'F1')
        self.pat(b + 2.0, 4, 'RlRlRlRl', lambda i, h, a, x: t58[i // 2] if h == 'R' else 'S',
                 tap=(0.44, 0.58), acc=(0.86, 0.98))
        for k in range(4):
            self.kick(b + 2.0 + 0.5 * k, 0.86)
        b = bar(59)                          # sextuplet thunder
        w59 = ('S', 'T1', 'T2', 'T3', 'T4', 'F1', 'F2', 'F1', 'T4', 'T3', 'T2', 'T1')
        c59 = ('C2', 'C2', 'RB', 'C2')
        self.pat(b, 6, 'RlrLrl' * 4, lambda i, h, a, x: c59[i // 6] if i % 6 == 0 else w59[i // 2],
                 tap=(0.55, 0.84), acc=(0.88, 1.0))
        self.double_bass(b, 24, 6, 0.6, 0.72, step_up=0.008)
        self.rush(b, b + 2, 0.01)
        b = bar(60)                          # pour down, then broaden under three hits
        r60, l60 = ('T1', 'T2', 'T3', 'F1'), ('S', 'T1', 'T2', 'S')
        self.pat(b, 8, 'RrLl' * 3 + 'RrL.', lambda i, h, a, x: r60[i // 4] if h == 'R' else l60[i // 4],
                 tap=(0.62, 0.86), acc=(0.82, 0.96))
        self.double_bass(b, 8, 4, 0.7, 0.8, step_up=0.015)
        big = ((b + 2.0, 'F1', 'C1'), (b + 2.0 + 2.0 / 3.0, 'T3', 'CH'), (b + 2.0 + 4.0 / 3.0, 'F2', 'S'))
        for k, (t, rv, lv) in enumerate(big):
            self.hit(t, 'R', rv, 0.95 + 0.02 * k, 6, ('acc',))
            self.hit(t, 'L', lv, 0.93 + 0.02 * k, 6, ('acc',))
            self.kick(t, 0.95, 6)
            self.hit(t, 'LF', 'K2', 0.9, 6, ('acc',))
        for t, h, v, l in ((b + 3.5, 'L', 'S', 0.74), (b + 3.0 + 2.0 / 3.0, 'R', 'T3', 0.84),
                           (b + 3.0 + 5.0 / 6.0, 'L', 'S', 0.94)):
            self.hit(t, h, v, l, 5, ('acc',))
        self.rush(b + 2.0, b + 4.0, -0.16, 0.0)
        self.lean(b + 2.0, b + 4.0, 0.0, 8.0)
        b = bar(61)                          # the last hit: all four limbs
        for limb, v in (('R', 'C2'), ('L', 'C1'), ('RF', 'K'), ('LF', 'K2')):
            self.hit(b, limb, v, 1.0, 9, ('acc', 'final'))

    def uniquify(self):
        r = self.rng
        seen = {}
        for n in range(1, 61):
            b0, b1 = bar(n), bar(n) + 4.0
            sig = None
            for attempt in range(16):
                sig = tuple(sorted((int(round((s.t - b0) * 48.0)), NOTE[s.voice])
                                   for s in self.strokes if b0 - 1e-6 <= s.t < b1 - 1e-6))
                if sig not in seen:
                    break
                slots = [b0 + 0.25 * p + (0.125 if attempt % 2 else 0.0) for p in range(16)]
                r.shuffle(slots)
                for t in slots:
                    if not self.busy('L', t, 90) and not self.busy('R', t, 15):
                        self.hit(t, 'L', 'S', 0.17, 2, ('ghost',))
                        break
            seen[sig] = n

    def compose(self):
        self.intro()
        self.groove_section()
        self.travel()
        self.whisper()
        self.poly()
        self.triplets()
        self.climax()
        self.finale()
        self.uniquify()

    # ---------------------------------------------------------- performance
    def build_tempo(self):
        end_beat = bar(61)
        nfin = int(round(end_beat / SEG))
        self.nseg = nfin + 1
        bpms = []
        for i in range(self.nseg):
            tm = min((i + 0.5) * SEG, end_beat - 1e-6)
            bpms.append(self.base_bpm(tm) * self.tempo_mult(tm) * self.drift(tm))
        secs = sum(SEG * 60.0 / v for v in bpms[:nfin])
        k = secs / FINAL_HIT_SEC
        self.seg_us = [int(round(60000000.0 / (v * k))) for v in bpms]
        self.seg_sec = []
        acc = 0.0
        for us in self.seg_us:
            self.seg_sec.append(acc)
            acc += us / 1e6 * SEG

    def bpm_at(self, beat):
        i = min(int(beat / SEG) if beat > 0 else 0, self.nseg - 1)
        return 60000000.0 / self.seg_us[i]

    def tick_sec(self, tick):
        i = min(tick // self.seg_ticks, self.nseg - 1)
        return self.seg_sec[i] + (tick - i * self.seg_ticks) * self.seg_us[i] / 1e6 / PPQ

    def perform(self):
        r = self.rng
        self.build_tempo()
        order = sorted(self.strokes, key=lambda s: (s.t, LIMB_IDX[s.limb], NOTE[s.voice], s.ms, s.prio))
        for n, s in enumerate(order):
            s.idx = n
        dph = {}
        for limb in LIMBS:
            dph[limb] = (r.uniform(0.0, 2 * math.pi), r.uniform(0.0, 2 * math.pi))
        amp = {'R': 2.4, 'L': 2.8, 'RF': 2.0, 'LF': 2.2}
        for s in order:                      # micro-timing in milliseconds
            if 'grace' in s.tags:
                continue
            if 'final' in s.tags:
                s.off = 12.0 if s.limb in ('R', 'RF') else 13.5
                continue
            sd = 4.0 if s.limb in ('R', 'L') else 3.0
            o = 0.0
            if 'ghost' in s.tags or s.lvl < 0.3:
                sd *= 1.3
                o += 2.5
            o += r.gauss(0.0, sd)
            if s.limb == 'L':
                o += 1.2
            elif s.limb == 'RF':
                o -= 1.8
            if 'acc' in s.tags:
                o -= 1.2
            if 'dbl' in s.tags:
                o -= 1.5
            if 'bb' in s.tags:
                o += 4.0
            p1, p2 = dph[s.limb]
            o += amp[s.limb] * (math.sin(2 * math.pi * s.t / 13.0 + p1)
                                + 0.6 * math.sin(2 * math.pi * s.t / 5.3 + p2))
            o += self.lean_ms(s.t)
            s.off = o
        for s in order:
            if 'grace' in s.tags:
                s.off = (s.main.off if s.main is not None else 0.0) + s.ms + r.gauss(0.0, 1.2)
        for s in order:
            bpm = self.bpm_at(s.t)
            s.tick = max(0, int(round((s.t + s.off / 1000.0 * bpm / 60.0) * PPQ)))
            s.sec = self.tick_sec(s.tick)
        for s in order:                      # velocity
            if 'final' in s.tags:
                s.vel = 127
                continue
            l = s.lvl
            if s.limb == 'L' and 'acc' not in s.tags:
                l -= 0.015
            if 'dbl' in s.tags and 'acc' not in s.tags:
                l *= 0.93
            l *= 1.0 + r.gauss(0.0, 0.045)
            s.vel = max(6, min(127, int(round(127.0 * l * GAIN.get(s.voice, 1.0)))))
        self.resolve()
        return self.write()

    @staticmethod
    def min_gap(a, b):
        if a.limb in ('RF', 'LF'):
            return 0.085
        d = abs(POS[a.voice] - POS[b.voice])
        if 'grace' in a.tags or 'grace' in b.tags or 'dbl' in b.tags:
            return 0.030 + 0.012 * d
        return 0.048 + 0.012 * d

    def arms_ok(self, s, secs, objs):
        o = 'L' if s.limb == 'R' else 'R'
        ls, lo = secs[o], objs[o]
        j = bisect.bisect_left(ls, s.sec - 0.07)
        while j < len(ls) and ls[j] <= s.sec + 0.07:
            q = lo[j]
            lx, rx = (POS[s.voice], POS[q.voice]) if s.limb == 'L' else (POS[q.voice], POS[s.voice])
            if lx - rx > 2.3:
                return False
            j += 1
        return True

    def resolve(self):
        """Keep the most important strokes that one human body can play."""
        cand = sorted(self.strokes, key=lambda s: (-s.prio, s.sec, LIMB_IDX[s.limb], NOTE[s.voice], s.idx))
        secs, objs, pitch = {}, {}, {}
        for limb in LIMBS:
            secs[limb], objs[limb] = [], []
        for s in cand:
            s.keep = False
            if s.main is not None and not s.main.keep:
                continue
            ls, lo = secs[s.limb], objs[s.limb]
            i = bisect.bisect_left(ls, s.sec)
            if i > 0 and s.sec - lo[i - 1].sec < self.min_gap(lo[i - 1], s):
                continue
            if i < len(ls) and lo[i].sec - s.sec < self.min_gap(s, lo[i]):
                continue
            pl = pitch.get(NOTE[s.voice])
            if pl:
                j = bisect.bisect_left(pl, s.sec - 0.015)
                if j < len(pl) and pl[j] <= s.sec + 0.015:
                    continue
            if s.limb in ('R', 'L') and not self.arms_ok(s, secs, objs):
                continue
            s.keep = True
            ls.insert(i, s.sec)
            lo.insert(i, s)
            if pl is None:
                pl = []
                pitch[NOTE[s.voice]] = pl
            bisect.insort(pl, s.sec)

    def write(self):
        kept = [s for s in self.strokes if s.keep]
        kept.sort(key=lambda s: (s.tick, LIMB_IDX[s.limb], NOTE[s.voice], s.idx))
        far = 1 << 62
        next_pitch, next_limb = {}, {}
        for s in reversed(kept):
            note = NOTE[s.voice]
            if 'final' in s.tags:
                nominal = 1.9 if s.voice in CYMBALS else 0.6
            else:
                nominal = 1.6 if s.voice in CYMBALS else 0.16
            bpm = 60000000.0 / self.seg_us[min(s.tick // self.seg_ticks, self.nseg - 1)]
            nom = int(nominal * bpm / 60.0 * PPQ)
            lim = min(next_pitch.get(note, far), next_limb.get(s.limb, far)) - s.tick - 2
            s.dur = max(1, min(nom, lim))
            next_pitch[note] = s.tick
            next_limb[s.limb] = s.tick
        events = []

        def add(tick, order, kind, v1=0, v2=0):
            events.append((tick, order, len(events), kind, v1, v2))
        add(0, 0, 'name')
        add(0, 1, 'ts', 1, 4)
        add(PPQ, 1, 'ts', 4, 4)
        prev = None
        for i, us in enumerate(self.seg_us):
            if us != prev:
                add(i * self.seg_ticks, 2, 'tempo', us)
                prev = us
        add(0, 3, 'prog', 0)
        for s in kept:
            add(s.tick, 5, 'on', NOTE[s.voice], s.vel)
            add(s.tick + s.dur, 4, 'off', NOTE[s.voice])
        events.sort(key=lambda e: (e[0], e[1], e[2]))
        end_tick = int(round(bar(61) * PPQ)) + int(round(TAIL_SEC * 1e6 / self.seg_us[-1] * PPQ))
        end_tick = max(end_tick, events[-1][0] + 1)
        mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        now = 0
        for tick, _o, _q, kind, v1, v2 in events:
            dt = tick - now
            now = tick
            if kind == 'name':
                track.append(mido.MetaMessage('track_name', name='Drum Solo', time=dt))
            elif kind == 'ts':
                track.append(mido.MetaMessage('time_signature', numerator=v1, denominator=v2, time=dt))
            elif kind == 'tempo':
                track.append(mido.MetaMessage('set_tempo', tempo=v1, time=dt))
            elif kind == 'prog':
                track.append(mido.Message('program_change', channel=9, program=v1, time=dt))
            elif kind == 'on':
                track.append(mido.Message('note_on', channel=9, note=v1, velocity=v2, time=dt))
            else:
                track.append(mido.Message('note_off', channel=9, note=v1, velocity=0, time=dt))
        track.append(mido.MetaMessage('end_of_track', time=end_tick - now))
        mid.save(OUTFILE)
        return mid


def main():
    drummer = Drummer(SEED)
    drummer.compose()
    mid = drummer.perform()
    kept = sum(1 for s in drummer.strokes if s.keep)
    print('wrote %s: %d strokes, %.1f seconds' % (OUTFILE, kept, mid.length))


if __name__ == '__main__':
    main()
