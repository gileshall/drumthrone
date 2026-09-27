#!/usr/bin/env python3
"""
drum_solo.py -- composes and performs a two-minute drum solo and writes it to solo.mid,
a General MIDI file with every stroke on channel 10.

Only the standard library and mido are used. Every random choice comes from seeded
generators, so running the script always produces a byte-identical solo.mid.

How it is built
  * The solo is written as strokes (beat, drum, velocity, limb). Every stroke belongs to
    one limb: right hand, left hand, right foot or left foot. A limb strikes one thing at
    a time and no faster than a human limb can, so at most two hands and two feet sound
    at any instant.
  * Motif A ("the call") is a 3-3-2 figure: three hits stepping down the kit, a flam, two
    ghost notes and a crash. It is
      - stated bare,
      - hidden in the groove's kick drum,
      - turned into accents inside runs,
      - played on wood blocks and cowbell,
      - squeezed into sextuplets and 32nds, and stretched into dotted quarters,
      - recast in 12/8 and set over double bass,
      - recapitulated, and finally used as the stop-time hits before the last crash.
  * The performance is elastic:
      - a tempo map built from section tempos, phrase arcs, fills that rush and breaths
        that hold back;
      - per-limb micro-timing: laid-back backbeats, lazy ghost notes, early kicks, slow
        limb drift, and human scatter that shrinks in fast passages;
      - a little swing in the color section, plus velocity scatter.
"""

import bisect
import math
import random

import mido

OUTFILE = "solo.mid"
SEED = 1971
TPB = 960                # ticks per quarter note
CH = 9                   # MIDI channel 10 (zero-based 9) = GM percussion
LEAD = 0.5               # beats of silence before the first downbeat
SEG = 0.25               # resolution of the tempo map, in beats
FINAL_TIME = 117.0       # the last hit lands here (seconds)
END_TIME = 120.6         # the file ends here, after the cymbals ring out

# General MIDI percussion keys used by the kit
KICK2, KICK, STICK, SNARE = 35, 36, 37, 38
F2, HH, F1, HHP, T4, HHO = 41, 42, 43, 44, 45, 46
T3, T2, CRASH, T1, RIDE, CHINA, BELL = 47, 48, 49, 50, 51, 52, 53
SPLASH, COWBELL, CRASH2 = 55, 56, 57
TIMB_HI, TIMB_LO, WB_HI, WB_LO = 65, 66, 76, 77

TOMS = [T1, T2, T3, T4, F1, F2]        # high to low, left to right around the kit
HANDS = ("R", "L")
FEET = ("RF", "LF")
LIMB_ORDER = {"RF": 0, "LF": 1, "R": 2, "L": 3}
LIMB_BIAS = {"R": 0.0, "L": 0.002, "RF": -0.003, "LF": 0.003}   # seconds
MIN_IOI = {"R": 0.036, "L": 0.036, "RF": 0.07, "LF": 0.075}     # fastest repeat per limb


class Note(object):
    __slots__ = ("beat", "key", "vel", "limb", "dt", "tag", "t", "gap", "on", "off")

    def __init__(self, beat, key, vel, limb, dt=0.0, tag=""):
        self.beat = float(beat)
        self.key = int(key)
        self.vel = float(vel)
        self.limb = limb
        self.dt = float(dt)
        self.tag = tag
        self.t = 0.0
        self.gap = 0.5
        self.on = 0
        self.off = 0


def P(bar, step, div=4):
    """Position in beats of `step` (in 1/div beat units) inside 4/4 bar `bar`."""
    return bar * 4.0 + step / float(div)


def ramp(i, n, a, b, curve=1.0):
    if n <= 1:
        return float(b)
    x = float(i) / float(n - 1)
    return a + (b - a) * (x ** curve)


def smooth(x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x * x * (3.0 - 2.0 * x)


def spread(path, n, per=None):
    """Lay a path of drums over n strokes (optionally `per` strokes on each drum)."""
    if per:
        return [path[min(len(path) - 1, i // per)] for i in range(n)]
    return [path[min(len(path) - 1, (i * len(path)) // n)] for i in range(n)]


def hand16(step):
    """Natural hand-to-hand sticking on a sixteenth grid."""
    return "R" if int(round(step)) % 2 == 0 else "L"


def alt(i, first="R"):
    if i % 2 == 0:
        return first
    return "L" if first == "R" else "R"


class Solo(object):
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.notes = []
        self.anchors = []
        self.pushes = []
        self.swings = []

    # ----------------------------------------------------------------- primitives
    def u(self, a, b):
        return self.rng.uniform(a, b)

    def hit(self, beat, key, vel, limb, dt=0.0, tag=""):
        self.notes.append(Note(beat, key, vel, limb, dt, tag))

    def push(self, start, end, amt, release=1.0, shape="ramp"):
        """Register a local tempo surge (amt > 0) or hold-back (amt < 0)."""
        self.pushes.append((float(start), float(end), float(amt), float(release), shape))

    def flam(self, beat, key, vel, main="R", grace_key=None, kick=None):
        other = "L" if main == "R" else "R"
        self.hit(beat, key, vel, main, tag="acc")
        g = key if grace_key is None else grace_key
        self.hit(beat, g, vel * self.u(0.30, 0.42), other, dt=-self.u(0.020, 0.032), tag="grace")
        if kick:
            self.hit(beat, KICK, kick, "RF")

    def hat_foot(self, bar, steps, v=54):
        for s in steps:
            self.hit(P(bar, s), HHP, v + self.u(-5, 5), "LF")

    def kicks(self, bar, steps, v=88):
        for s in steps:
            self.hit(P(bar, s), KICK, v + self.u(-5, 5) + (8 if s == 0 else 0), "RF")

    def dbass(self, start, n, step, v0=82, v1=92, accents=(), acc=12, first="RF"):
        other = "LF" if first == "RF" else "RF"
        for i in range(n):
            pos = start + i * step
            v = ramp(i, n, v0, v1) + self.u(-4, 4)
            for a in accents:
                if abs(pos - a) < 1e-6:
                    v += acc
            self.hit(pos, KICK, v, first if i % 2 == 0 else other)

    def roll(self, start, end, key, v0, v1, r0=6.0, r1=8.0, vcurve=1.0, first="R"):
        """Double-stroke roll that accelerates from r0 to r1 strokes per beat and swells.
        It ends on the second stroke of a double so the lead hand is free at `end`."""
        length = end - start
        n = max(4, int(round(length * (r0 + r1) / 8.0)) * 4)
        ratio = r1 / r0
        a = (ratio - 1.0) / (ratio + 1.0)
        other = "L" if first == "R" else "R"
        for i in range(n):
            x = i / float(n)
            g = (1.0 - a) * x + a * (1.0 - (1.0 - x) ** 2)
            v = v0 + (v1 - v0) * ((i / float(n - 1)) ** vcurve)
            if i % 2 == 1:
                v *= 0.92
            limb = first if (i // 2) % 2 == 0 else other
            self.hit(start + length * g, key, v, limb, tag="roll")

    def accent_stream(self, start, step, n, accents, acc_keys, acc_v=(98, 112),
                      tap_v=(28, 48), tap_key=SNARE, first="R", acc_list=None):
        """Alternating singles: accents pop out on toms/cymbals, taps stay soft on the snare."""
        order = sorted(accents)
        for i in range(n):
            limb = alt(i, first)
            pos = start + i * step
            if i in accents:
                ai = order.index(i)
                if acc_list is not None:
                    v = acc_list[ai % len(acc_list)]
                else:
                    v = ramp(ai, len(order), acc_v[0], acc_v[1])
                self.hit(pos, acc_keys[ai % len(acc_keys)], v + self.u(-3, 3), limb, tag="acc")
            else:
                self.hit(pos, tap_key, ramp(i, n, tap_v[0], tap_v[1]) + self.u(-3, 3), limb,
                         tag="ghost")

    # ----------------------------------------------------------------- grooves & fills
    def groove(self, bar, until=16, tk="hat", hat16=False, ghost_p=0.3, kick=(0, 3, 6, 10),
               open_at=None, crash0=None, bell=False, lf_steps=(), diddle=None, gmax=40):
        b = bar
        if crash0:
            self.hit(P(b, 0), crash0, self.u(108, 116), "R", tag="acc")
        for s in range(0, until, 1 if hat16 else 2):
            if s == 0 and crash0:
                continue
            if tk == "ride":
                key = BELL if (bell and s % 4 == 0) else RIDE
                v = 88 if s % 4 == 0 else (70 if s % 2 == 0 else 52)
                if key == BELL:
                    v -= 8
            else:
                key = HHO if s == open_at else HH
                v = 92 if s % 4 == 0 else (70 if s % 2 == 0 else 50)
                if key == HHO:
                    v = 84
            self.hit(P(b, s), key, v + self.u(-5, 4), "R", tag="time")
        for s in (4, 12):
            if s < until:
                self.hit(P(b, s), SNARE, self.u(104, 114), "L", tag="backbeat")
        banned = set()
        if diddle is not None:
            banned.update((diddle - 1, diddle))
        for s in (1, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15):
            if s >= until - 1 or s in banned:
                continue
            p = ghost_p * (1.35 if s in (3, 7, 11, 13) else 0.75)
            if self.rng.random() < p:
                v = 22 + (gmax - 22) * self.u(0.25, 1.0)
                if s + 1 in (4, 12):
                    v += 4
                self.hit(P(b, s), SNARE, v, "L", tag="ghost")
        if diddle is not None and diddle < until - 1:
            self.hit(P(b, diddle - 0.5), SNARE, self.u(26, 32), "L", tag="ghost")
            self.hit(P(b, diddle), SNARE, self.u(32, 38), "L", tag="ghost")
        for s in kick:
            if s < until:
                self.hit(P(b, s), KICK, (100 if s == 0 else self.u(78, 92)), "RF")
        for s in lf_steps:
            if s < until:
                self.hit(P(b, s), HHP, self.u(48, 60), "LF")

    def fill_tail(self, bar):
        """The tail of motif A as a two-beat fill: flam, ghost pair, three toms."""
        b = bar
        toms = self.rng.choice([(T1, T2, F1), (T2, T3, F2), (T1, T3, F1), (T1, T4, F2)])
        self.flam(P(b, 8), SNARE, self.u(104, 112), "R", kick=92)
        self.hit(P(b, 9), SNARE, self.u(28, 34), "L", tag="ghost")
        self.hit(P(b, 10), SNARE, self.u(36, 42), "R", tag="ghost")
        self.hit(P(b, 11), SNARE, self.u(48, 56), "L", tag="ghost")
        self.hit(P(b, 12), toms[0], self.u(100, 108), "R", tag="acc")
        self.hit(P(b, 12), KICK, 90, "RF")
        self.hit(P(b, 13), toms[1], self.u(84, 92), "L")
        self.hit(P(b, 14), toms[2], self.u(104, 112), "R", tag="acc")
        self.hit(P(b, 14), KICK, 96, "RF")
        self.hit(P(b, 15), toms[2], self.u(72, 80), "L")
        self.push(P(b, 8), P(b, 16), 0.025, release=1.0)

    def fill_ripple(self, bar, s0=12, n=6, v0=78, v1=110, desc=True):
        """Motif B: a ripple of singles down (or up) the toms into the next downbeat."""
        b = bar
        start = P(b, s0)
        length = (16 - s0) / 4.0
        keys = spread(TOMS if desc else TOMS[::-1], n)
        for i in range(n):
            self.hit(start + i * length / n, keys[i], ramp(i, n, v0, v1), alt(i),
                     tag="acc" if i == 0 else "")
        self.hit(start, KICK, 88, "RF")
        self.hit(start + length / 2.0, KICK, 94, "RF")
        self.push(start, P(b, 16), 0.03, release=1.0)

    def fill_head(self, bar, s0=8, keys=(T1, T3, F1)):
        """The head of motif A displaced to beat three, inside ghost-note sixteenths."""
        b = bar
        acc = {s0: keys[0], s0 + 3: keys[1], s0 + 6: keys[2]}
        for s in range(s0, 16):
            if s in acc:
                self.hit(P(b, s), acc[s], self.u(100, 110), hand16(s), tag="acc")
                self.hit(P(b, s), KICK, 88, "RF")
            else:
                self.hit(P(b, s), SNARE, ramp(s - s0, 16 - s0, 30, 62), hand16(s), tag="ghost")
        self.push(P(b, s0), P(b, 16), 0.025, release=1.0)

    def fill_run12(self, bar, s0=8, path=(SNARE, T1, T2, T3, F1, F2), v0=70, v1=116):
        b = bar
        start = P(b, s0)
        keys = spread(list(path), 12, per=2)
        for i in range(12):
            v = ramp(i, 12, v0, v1, 1.3) + (6 if i % 2 == 0 else 0)
            self.hit(start + i / 6.0, keys[i], v, alt(i), tag="acc" if i % 2 == 0 else "")
        self.hit(start, KICK, 86, "RF")
        self.hit(start + 1.0, KICK, 96, "RF")
        self.push(start, P(b, 16), 0.035, release=1.0)

    # ----------------------------------------------------------------- the plan
    def tempo_plan(self):
        for beat, bpm in (
                (0, 94), (4, 97), (8, 100), (12, 103), (15, 107), (16, 110),
                (32, 112), (44, 113), (48, 114), (64, 116), (76, 118), (79.5, 118),
                (80.5, 107), (96, 108), (100, 108), (104, 111), (116, 113), (132, 116),
                (136, 116), (152, 119), (166, 122), (167.5, 122), (168.5, 110),
                (176, 111), (184, 117), (190, 123), (191.6, 124), (192.4, 118),
                (199.5, 119), (201, 121), (203.5, 118), (204.5, 108), (207, 100),
                (208, 96)):
            self.anchors.append((float(beat), float(bpm)))
        # every four-bar phrase leans forward toward its third bar, then settles
        for start_bar in (4, 8, 12, 16, 26, 30, 34, 38):
            self.push(P(start_bar, 0), P(start_bar + 4, 0), 0.012, shape="arc")

    def sec_intro(self):
        # bar 0 -- the call: motif A stated bare, with space around it
        b = 0
        self.hit(P(b, 0), T2, 100, "R", tag="acc")
        self.hit(P(b, 0), KICK, 96, "RF")
        self.hit(P(b, 3), T4, 95, "L", tag="acc")
        self.hit(P(b, 3), KICK, 86, "RF")
        self.hit(P(b, 6), F2, 108, "R", tag="acc")
        self.hit(P(b, 6), KICK, 102, "RF")
        self.flam(P(b, 8), SNARE, 110, "R")
        self.hit(P(b, 10), SNARE, 30, "R", tag="ghost")
        self.hit(P(b, 11), SNARE, 46, "L", tag="ghost")
        self.hit(P(b, 12), CRASH, 117, "R", tag="acc")
        self.hit(P(b, 12), KICK, 108, "RF")
        self.push(P(b, 6.5), P(b, 7.8), -0.07, release=0.4, shape="flat")

        # bar 1 -- a whispered answer that echoes the head, then a ripple down the toms
        b = 1
        self.hit(P(b, 0), KICK, 62, "RF")
        self.hat_foot(b, (4, 12), 50)
        for s, v in ((2, 22), (3, 42), (5, 25), (6, 50), (7, 30), (9, 31), (10, 38), (11, 47)):
            self.hit(P(b, s), T1 if s == 6 else SNARE, v + self.u(-3, 3), hand16(s),
                     tag="ghost" if v < 40 else "")
        for k in range(6):
            self.hit(P(b, 12) + k / 6.0, TOMS[k], 60 + 7.2 * k, alt(k))
        self.hit(P(b, 12), KICK, 72, "RF")
        self.push(P(b, 12), P(b, 16), 0.035, release=1.0)

        # bar 2 -- the call again, now as accents inside a stream of ghost notes
        b = 2
        head = {0: T1, 3: T3, 6: F1}
        for s in range(8):
            if s in head:
                self.hit(P(b, s), head[s], 103 + s, hand16(s), tag="acc")
                self.hit(P(b, s), KICK, 92, "RF")
            else:
                self.hit(P(b, s), SNARE, 28 + 3 * s, hand16(s), tag="ghost")
        self.flam(P(b, 8), SNARE, 110, "R", kick=90)
        self.hit(P(b, 9), SNARE, 34, "L", tag="ghost")
        self.hit(P(b, 10), SNARE, 42, "R", tag="ghost")
        self.hit(P(b, 11), SNARE, 54, "L", tag="ghost")
        self.hit(P(b, 12), CRASH2, 114, "R", tag="acc")
        self.hit(P(b, 12), KICK, 104, "RF")
        self.hit(P(b, 13), SNARE, 30, "L", tag="ghost")
        self.hit(P(b, 14), KICK, 64, "RF")

        # bar 3 -- a double-stroke roll swells from nothing and spills down the toms
        b = 3
        self.hat_foot(b, (4, 12), 52)
        self.roll(P(b, 0), P(b, 12), SNARE, 14, 102, r0=6.0, r1=8.5, vcurve=1.7)
        for k in range(6):
            self.hit(P(b, 12) + k / 6.0, TOMS[k], 98 + 3.6 * k, alt(k),
                     tag="acc" if k == 0 else "")
        self.hit(P(b, 12), KICK, 98, "RF")
        self.hit(P(b, 14), KICK, 104, "RF")
        self.push(P(b, 0), P(b, 12), 0.06, release=2.0)

    def sec_groove(self):
        # the home groove: its kick drum quietly plays the 3-3-2 of the call
        kick_pats = [(0, 3, 6, 10), (0, 3, 6, 10, 14), (0, 3, 6, 8, 11), (0, 3, 6, 9, 10),
                     (0, 2, 6, 10), (0, 3, 7, 10, 13), (0, 3, 6, 11, 14)]
        self.groove(4, crash0=CRASH, kick=kick_pats[0], ghost_p=0.22, open_at=14)
        self.groove(5, until=8, kick=kick_pats[1], ghost_p=0.28)
        self.fill_tail(5)
        self.groove(6, crash0=CRASH2, kick=kick_pats[2], ghost_p=0.34, diddle=11, open_at=6)
        self.groove(7, until=12, hat16=True, kick=kick_pats[3], ghost_p=0.36)
        self.fill_ripple(7, s0=12, desc=True)
        self.groove(8, tk="ride", crash0=CRASH, kick=kick_pats[4], ghost_p=0.40,
                    lf_steps=(4, 12))
        self.groove(9, until=8, tk="ride", kick=kick_pats[5], ghost_p=0.42, lf_steps=(4,))
        self.fill_head(9, keys=(T2, T4, F2))
        self.groove(10, tk="ride", bell=True, crash0=CRASH2, kick=kick_pats[6], ghost_p=0.46,
                    lf_steps=(4, 12), diddle=3, gmax=44)
        self.groove(11, until=8, tk="ride", kick=kick_pats[1], ghost_p=0.45, lf_steps=(4,))
        self.fill_run12(11)

    def sec_around(self):
        # bar 12: landing crash, singles with 3-3-3-3-2-2 accents stepping down the toms
        b = 12
        self.kicks(b, (0, 8), 90)
        self.hat_foot(b, (4, 12), 56)
        self.accent_stream(P(b, 0), 0.25, 16, {0, 3, 6, 9, 12, 14},
                           [CRASH, T1, T2, T3, T4, F1], acc_list=[116, 100, 103, 106, 109, 112],
                           tap_v=(28, 46))

        # bar 13: doubles walking round the kit, sixteenths opening into 32nds
        b = 13
        self.kicks(b, (0, 8), 86)
        self.hat_foot(b, (4, 12), 56)
        keys16 = [SNARE, SNARE, T1, T1, T2, T2, SNARE, SNARE]
        for i in range(8):
            limb = "R" if (i // 2) % 2 == 0 else "L"
            v = 62 + 3 * i + (10 if i % 2 == 0 else 0)
            self.hit(P(b, i), keys16[i], v, limb, tag="acc" if i % 2 == 0 else "")
        keys32 = spread([T1, T2, T3, T4, F1, F2, F1, F2], 16, per=2)
        for i in range(16):
            limb = "R" if (i // 2) % 2 == 0 else "L"
            v = ramp(i, 16, 70, 106) + (9 if i % 2 == 0 else -2)
            self.hit(P(b, 8) + i * 0.125, keys32[i], v, limb, tag="acc" if i % 2 == 0 else "")
        self.push(P(b, 8), P(b, 16), 0.02, release=1.0)

        # bar 14: paradiddles -- accents on floor tom and snare, inner strokes on hat/snare
        b = 14
        self.hat_foot(b, (4, 12), 54)
        pd = "RLRRLRLL"
        acc = {0: F1, 4: SNARE, 8: T3, 12: SNARE}
        for s in range(16):
            limb = pd[s % 8]
            if s in acc:
                key = acc[s]
                self.hit(P(b, s), key, (108 if key == SNARE else 104) + self.u(-3, 3), limb,
                         tag="backbeat" if key == SNARE else "acc")
            elif limb == "R":
                self.hit(P(b, s), HH, 58 + self.u(-5, 5), "R")
            else:
                self.hit(P(b, s), SNARE, 32 + self.u(-4, 4), "L", tag="ghost")
        self.kicks(b, (0, 6, 8, 14), 88)

        # bar 15: the 3-3-2 squeezed into sextuplets -- three cycles across the bar
        b = 15
        self.hat_foot(b, (4, 12), 56)
        groups = [(T1, T3, F1), (T2, T4, F2), (T1, T3, F2)]
        acc = {}
        for g in range(3):
            for j, off in enumerate((0, 3, 6)):
                acc[g * 8 + off] = groups[g][j]
        for i in range(24):
            pos = P(b, i, 6)
            if i in acc:
                self.hit(pos, acc[i], 96 + i * 0.8 + self.u(-3, 3), alt(i), tag="acc")
            else:
                self.hit(pos, SNARE, ramp(i, 24, 30, 58), alt(i), tag="ghost")
        for g in range(3):
            self.hit(P(b, g * 8, 6), KICK, 92 + 3 * g, "RF")
        self.hit(P(b, 22, 6), KICK, 96, "RF")
        self.push(P(b, 8), P(b, 16), 0.03, release=1.0)

        # bar 16: the head stretched to dotted quarters, each hit set up by a five-stroke ruff
        b = 16
        o = P(b, 0)
        self.hat_foot(b, (4, 12), 56)
        self.hit(o, CRASH2, 114, "R", tag="acc")
        self.hit(o, KICK, 104, "RF")
        self.hit(o + 0.5, SNARE, 30, "L", tag="ghost")
        self.hit(o + 0.75, SNARE, 34, "R", tag="ghost")
        for j, (off, limb) in enumerate(((1.0, "R"), (1.125, "R"), (1.25, "L"), (1.375, "L"))):
            self.hit(o + off, SNARE, 40 + 8 * j, limb, tag="ghost")
        self.hit(o + 1.5, T2, 108, "R", tag="acc")
        self.hit(o + 1.5, KICK, 96, "RF")
        self.hit(o + 1.75, SNARE, 32, "L", tag="ghost")
        self.hit(o + 2.0, SNARE, 30, "R", tag="ghost")
        for j, (off, limb) in enumerate(((2.5, "R"), (2.625, "R"), (2.75, "L"), (2.875, "L"))):
            self.hit(o + off, T3 if j >= 2 else SNARE, 48 + 9 * j, limb)
        self.hit(o + 3.0, F1, 112, "R", tag="acc")
        self.hit(o + 3.0, KICK, 100, "RF")
        for j in range(6):
            self.hit(o + 3.25 + j * 0.125, TOMS[j], 80 + 6 * j, alt(j, "L"))

        # bars 17-18: groups of three sixteenths sail across the bar line, resolved by a two
        acc_steps = [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30]
        acc_keys = [CRASH, F2, F1, T4, T3, T2, T1, T2, T3, F1, F2]
        accs = dict(zip(acc_steps, acc_keys))
        for s in range(32):
            bar, st = 17 + s // 16, s % 16
            pos = P(bar, st)
            if s in accs:
                v = 112 if s == 0 else ramp(acc_steps.index(s), len(acc_steps), 98, 118)
                self.hit(pos, accs[s], v + self.u(-3, 3), hand16(st), tag="acc")
            else:
                self.hit(pos, SNARE, ramp(s, 32, 28, 56, 1.3) + self.u(-3, 3), hand16(st),
                         tag="ghost")
        for bar in (17, 18):
            self.kicks(bar, (0, 8), 88)
            self.hat_foot(bar, (4, 12), 56)
        self.push(P(17, 0), P(19, 0), 0.03, release=1.5, shape="arc")

        # bar 19: the resolution crashes in, sextuplets climb and 32nds tumble down
        b = 19
        self.hit(P(b, 0), CRASH2, 116, "R", tag="acc")
        self.hit(P(b, 0), KICK, 106, "RF")
        up = spread([F2, F1, T4, T3, T2, T1], 12, per=2)
        for i in range(1, 12):
            self.hit(P(b, i, 6), up[i], ramp(i, 12, 70, 96) + (6 if i % 2 == 0 else 0), alt(i))
        down = spread([T1, T2, T3, T4, F1, F2, F1, F2], 16, per=2)
        for i in range(16):
            self.hit(P(b, 8) + i * 0.125, down[i], ramp(i, 16, 88, 122, 1.2), alt(i),
                     tag="acc" if i % 4 == 0 else "")
        for s in (4, 8, 12, 14):
            self.hit(P(b, s), KICK, 92 + s * 0.8, "RF")
        self.hat_foot(b, (4,), 54)
        self.push(P(b, 0), P(b, 16), 0.04, release=1.2)

    def sec_colors(self):
        # a laid-back, lightly swung corner of the kit: baiao-style feet, bells and blocks
        self.swings.append((P(20, 0), P(26, 0), 0.57, 3.0))
        for b in range(20, 26):
            ks = (0, 3, 8, 11) if b != 25 else (0, 3)
            for s in ks:
                v = (72 if s in (0, 8) else 56) + self.u(-4, 4)
                if b == 20 and s == 0:
                    v = 108
                self.hit(P(b, s), KICK, v, "RF")
            if b != 25:
                self.hat_foot(b, (4, 12), 50)

        # bar 20: land, then drop to cowbell and a cross-stick clave (the call's rhythm)
        b = 20
        self.hit(P(b, 0), CRASH, 114, "R", tag="acc")
        for s in (3, 6, 10, 12):
            self.hit(P(b, s), STICK, 72 + self.u(-4, 5), "L")
        for s in (4, 6, 8, 10, 12, 14):
            self.hit(P(b, s), COWBELL, (72 if s % 4 == 0 else 56) + self.u(-4, 4), "R")

        # bar 21
        b = 21
        for s in range(0, 16, 2):
            self.hit(P(b, s), COWBELL, (74 if s % 4 == 0 else 56) + self.u(-4, 4), "R")
        self.hit(P(b, 7), COWBELL, 48, "R")
        for s in (0, 3, 6, 10, 12):
            self.hit(P(b, s), STICK, 74 + self.u(-4, 5), "L")
        self.hit(P(b, 14), WB_HI, 66, "L")
        self.hit(P(b, 15), WB_LO, 72, "L")

        # bar 22: motif A on wood blocks, its tail on the timbales and a splash
        b = 22
        self.hit(P(b, 0), WB_HI, 96, "R", tag="acc")
        self.hit(P(b, 3), WB_LO, 88, "L", tag="acc")
        self.hit(P(b, 5), STICK, 44, "L")
        self.hit(P(b, 6), WB_LO, 96, "R", tag="acc")
        self.flam(P(b, 8), TIMB_HI, 100, "R", grace_key=TIMB_LO)
        self.hit(P(b, 10), TIMB_LO, 42, "R", tag="ghost")
        self.hit(P(b, 11), TIMB_LO, 54, "L", tag="ghost")
        self.hit(P(b, 12), SPLASH, 98, "R", tag="acc")
        self.hit(P(b, 12), KICK, 84, "RF")
        self.hit(P(b, 14), STICK, 62, "L")
        self.hit(P(b, 15), TIMB_HI, 70, "R")

        # bar 23: cowbell and timbale conversation, then a timbale ripple
        b = 23
        for s in (0, 4, 6, 8, 10):
            self.hit(P(b, s), COWBELL, (74 if s % 4 == 0 else 56) + self.u(-4, 4), "R")
        for s in (1, 3, 5, 7, 9, 11):
            if s == 7:
                self.hit(P(b, s), TIMB_HI, 86, "L", tag="acc")
            else:
                self.hit(P(b, s), TIMB_LO, 34 + 2 * s + self.u(-3, 3), "L", tag="ghost")
        rip = (TIMB_HI, TIMB_HI, TIMB_LO, TIMB_LO, T3, F1)
        for k in range(6):
            self.hit(P(b, 12) + k / 6.0, rip[k], 66 + 7 * k, alt(k))

        # bar 24: the head as cowbell/timbale unisons, the tail answered on the toms
        b = 24
        for s, kl in ((0, TIMB_LO), (3, TIMB_HI), (6, TIMB_LO)):
            self.hit(P(b, s), COWBELL, 86 + self.u(-3, 3), "R", tag="acc")
            self.hit(P(b, s), kl, 92 + self.u(-3, 3), "L", tag="acc")
        self.flam(P(b, 8), T2, 104, "R")
        self.hit(P(b, 10), SNARE, 40, "R", tag="ghost")
        self.hit(P(b, 11), SNARE, 52, "L", tag="ghost")
        self.hit(P(b, 12), T4, 106, "R", tag="acc")
        self.hit(P(b, 12), KICK, 92, "RF")
        self.hit(P(b, 13), T4, 70, "L")
        self.hit(P(b, 14), F2, 110, "R", tag="acc")
        self.hit(P(b, 14), KICK, 96, "RF")
        self.hit(P(b, 15), SNARE, 58, "L")

        # bar 25: timbale sixteenths swell into sextuplets rolling down the toms
        b = 25
        for s in range(8):
            self.hit(P(b, s), TIMB_HI if s % 2 == 0 else TIMB_LO, ramp(s, 8, 44, 84), hand16(s))
        path = spread(TOMS, 12, per=2)
        for i in range(12):
            self.hit(P(b, 8) + i / 6.0, path[i], ramp(i, 12, 84, 118, 1.2), alt(i),
                     tag="acc" if i % 2 == 0 else "")
        self.hit(P(b, 8), KICK, 92, "RF")
        self.hit(P(b, 12), KICK, 100, "RF")
        self.hat_foot(b, (4,), 52)
        self.push(P(b, 4), P(b, 16), 0.04, release=1.2)

    def sec_triplets(self):
        # bar 26: hand-hand-foot sextuplets tumbling down the kit
        b = 26
        self.hit(P(b, 0), CRASH, 116, "R", tag="acc")
        self.hit(P(b, 0), KICK, 104, "RF")
        self.hat_foot(b, (4, 12), 54)
        pairs = [(CRASH, T1), (T1, T2), (T2, T3), (T3, T4), (T4, F1), (F1, F2), (F2, F1),
                 (F1, F2)]
        for g in range(8):
            base = g * 3
            rk, lk = pairs[g]
            if g > 0:
                self.hit(P(b, base, 6), rk, 92 + 2.5 * g + self.u(-3, 3), "R", tag="acc")
            self.hit(P(b, base + 1, 6), lk, 70 + 2.5 * g + self.u(-3, 3), "L")
            if g < 7:
                self.hit(P(b, base + 2, 6), KICK, 82 + 1.5 * g + self.u(-3, 3), "RF")

        # bar 27: motif A translated into 12/8 -- the head as quarter-note triplets
        b = 27
        self.hat_foot(b, (4, 12), 54)
        head = {0: T1, 2: T3, 4: F1}
        for k in range(6):
            pos = P(b, k, 3)
            if k in head:
                self.hit(pos, head[k], 104 + 2 * k, "R", tag="acc")
                self.hit(pos, KICK, 92, "RF")
            else:
                self.hit(pos, SNARE, 34 + 3 * k, "L", tag="ghost")
        self.flam(P(b, 6, 3), SNARE, 110, "R", kick=90)
        self.hit(P(b, 7, 3), SNARE, 38, "L", tag="ghost")
        self.hit(P(b, 8, 3), SNARE, 50, "R", tag="ghost")
        self.hit(P(b, 9, 3), CRASH2, 114, "R", tag="acc")
        self.hit(P(b, 9, 3), KICK, 100, "RF")
        self.hit(P(b, 10, 3), SNARE, 44, "L", tag="ghost")
        self.hit(P(b, 11, 3), SNARE, 60, "R")

        # bar 28: flam accents stepping down the toms over four-on-the-floor
        b = 28
        self.hat_foot(b, (4, 12), 52)
        keys = (T1, T2, T3, F1)
        for q in range(4):
            main = "R" if q % 2 == 0 else "L"
            other = "L" if main == "R" else "R"
            base = q * 3
            self.flam(P(b, base, 3), keys[q], 100 + 4 * q, main)
            self.hit(P(b, base + 1, 3), SNARE, 46 + 3 * q, other, tag="ghost")
            self.hit(P(b, base + 2, 3), SNARE, 52 + 3 * q, main)
            self.hit(P(b, 4 * q), KICK, 88 + 3 * q, "RF")

        # bar 29: six-stroke rolls, each sweeping between two drums
        b = 29
        self.hat_foot(b, (4, 12), 52)
        accs = [(T1, T2), (T3, T4), (F1, F2), (CRASH, SNARE)]
        for q in range(4):
            base = q * 6
            ra, la = accs[q]
            self.hit(P(b, base, 6), ra, 100 + 4 * q, "R", tag="acc")
            self.hit(P(b, base + 1, 6), SNARE, 44 + 3 * q, "L", tag="ghost")
            self.hit(P(b, base + 2, 6), SNARE, 40 + 3 * q, "L", tag="ghost")
            self.hit(P(b, base + 3, 6), SNARE, 46 + 3 * q, "R", tag="ghost")
            self.hit(P(b, base + 4, 6), SNARE, 42 + 3 * q, "R", tag="ghost")
            self.hit(P(b, base + 5, 6), la, 90 + 4 * q, "L", tag="acc")
            self.hit(P(b, base, 6), KICK, 90 + 3 * q, "RF")

        # bar 30: five-note linear groupings (R L R L kick) rolling across the beat
        b = 30
        self.hat_foot(b, (4, 12), 52)
        groups = [(0, "RLRLK"), (5, "RLRLK"), (10, "RLRLK"), (15, "RLRLK"), (20, "RLRK")]
        acc_toms = [T1, T2, T3, F1, F2]
        for gi, (st, pat) in enumerate(groups):
            for j, c in enumerate(pat):
                pos = P(b, st + j, 6)
                if c == "K":
                    self.hit(pos, KICK, 86 + 2 * gi, "RF")
                elif j == 0:
                    self.hit(pos, acc_toms[gi], 100 + 3 * gi, "R", tag="acc")
                elif c == "L":
                    self.hit(pos, SNARE, 50 + 4 * gi + 2 * j, "L", tag="ghost" if gi < 2 else "")
                else:
                    self.hit(pos, TOMS[min(5, gi + 1)], 66 + 4 * gi, "R")
        self.hit(P(b, 0), KICK, 96, "RF")
        self.push(P(b, 0), P(b, 16), 0.02, release=1.0)

        # bar 31: the head as quarter-note-triplet cymbal hits, then sextuplets pour down
        b = 31
        cym = {0: CRASH, 2: CHINA, 4: CRASH2}
        for k in range(6):
            pos = P(b, k, 3)
            if k in cym:
                self.hit(pos, cym[k], 114 + k, "R", tag="acc")
                self.hit(pos, KICK, 100, "RF")
            else:
                self.hit(pos, SNARE, 50 + 4 * k, "L")
        path = spread(TOMS, 12, per=2)
        for i in range(12):
            self.hit(P(b, 8) + i / 6.0, path[i], ramp(i, 12, 86, 112), alt(i),
                     tag="acc" if i % 2 == 0 else "")
        self.hit(P(b, 8), KICK, 94, "RF")
        self.hit(P(b, 12), KICK, 98, "RF")
        self.hat_foot(b, (12,), 54)

        # bar 32: hands-and-feet sextuplets (R L R L + both feet) marching round the toms
        b = 32
        hand_pairs = [(T1, T2), (T3, T4), (F1, F2), (T2, F1)]
        for q in range(4):
            base = q * 6
            a, c = hand_pairs[q]
            self.hit(P(b, base, 6), a, 102 + 3 * q, "R", tag="acc")
            self.hit(P(b, base + 1, 6), a, 78 + 3 * q, "L")
            self.hit(P(b, base + 2, 6), c, 92 + 3 * q, "R")
            self.hit(P(b, base + 3, 6), c, 76 + 3 * q, "L")
            self.hit(P(b, base + 4, 6), KICK, 90 + 2 * q, "RF")
            self.hit(P(b, base + 5, 6), KICK, 86 + 2 * q, "LF")
        self.push(P(b, 0), P(b, 16), 0.02, release=1.0)

        # bar 33: sextuplets down the kit, then quarter-note-triplet flams climbing home
        b = 33
        path = spread(TOMS, 12, per=2)
        for i in range(12):
            v = ramp(i, 12, 92, 108) + (8 if i % 6 == 0 else 0)
            self.hit(P(b, i, 6), path[i], v, alt(i), tag="acc" if i % 6 == 0 else "")
        self.hit(P(b, 0), KICK, 96, "RF")
        self.hit(P(b, 4), KICK, 92, "RF")
        for k, key, main in ((6, F1, "R"), (8, T3, "L"), (10, T1, "R")):
            self.flam(P(b, k, 3), key, 106 + (k - 6) * 2, main, kick=96 + (k - 6))
        self.hit(P(b, 7, 3), T4, 70, "R")
        self.hit(P(b, 9, 3), T2, 76, "L")
        self.hit(P(b, 11, 3), SNARE, 86, "L")
        self.push(P(b, 0), P(b, 16), 0.035, release=1.0)

    def sec_thunder(self):
        # bar 34: motif A in full over a double-bass rumble
        b = 34
        self.dbass(P(b, 0), 16, 0.25, 84, 94, accents=[P(b, s) for s in (0, 3, 6, 8, 12)],
                   acc=14)
        self.hit(P(b, 0), CRASH, 120, "R", tag="acc")
        self.hit(P(b, 0), SNARE, 112, "L", tag="acc")
        self.hit(P(b, 3), CHINA, 112, "R", tag="acc")
        self.hit(P(b, 3), T3, 104, "L", tag="acc")
        self.hit(P(b, 6), CRASH2, 116, "R", tag="acc")
        self.hit(P(b, 6), F1, 108, "L", tag="acc")
        self.flam(P(b, 8), SNARE, 112, "R")
        self.hit(P(b, 10), SNARE, 44, "R", tag="ghost")
        self.hit(P(b, 11), SNARE, 56, "L", tag="ghost")
        self.hit(P(b, 12), CRASH, 120, "R", tag="acc")
        self.hit(P(b, 12), SNARE, 110, "L", tag="acc")
        self.hit(P(b, 14), T1, 100, "R")
        self.hit(P(b, 15), T2, 96, "L")

        # bar 35: accent/tap sixteenths over the feet, the accents stepping round the kit
        b = 35
        self.dbass(P(b, 0), 16, 0.25, 82, 92,
                   accents=[P(b, s) for s in (0, 3, 6, 9, 12, 14)], acc=12)
        self.accent_stream(P(b, 0), 0.25, 16, {0, 3, 6, 9, 12, 14},
                           [CHINA, T1, T3, F1, T2, F2], acc_v=(104, 116), tap_v=(34, 54))

        # bar 36: half-time weight -- china and crash on half-note triplets, heavy backbeats
        b = 36
        self.dbass(P(b, 0), 16, 0.25, 72, 84, accents=[P(b, 0), P(b, 8)], acc=14)
        for j, key in enumerate((CHINA, CRASH, CHINA)):
            self.hit(P(b, 0) + j * 4.0 / 3.0, key, 112 - 4 * j, "R", tag="acc")
        self.hit(P(b, 4), SNARE, 112, "L", tag="backbeat")
        self.hit(P(b, 12), SNARE, 115, "L", tag="backbeat")
        for s, v in ((7, 30), (9, 34), (10, 30)):
            self.hit(P(b, s), SNARE, v, "L", tag="ghost")
        for j, key in enumerate((T1, T1, T2, T3)):
            self.hit(P(b, 14) + j * 0.125, key, 88 + 5 * j, alt(j))

        # bar 37: 32nd-note diddles on the snare, a tom accent on every beat
        b = 37
        self.dbass(P(b, 0), 16, 0.25, 82, 96)
        toms = (T1, T2, T3, F1)
        for q in range(4):
            for j in range(8):
                i = q * 8 + j
                limb = "R" if (j // 2) % 2 == 0 else "L"
                pos = P(b, 0) + q + j * 0.125
                if j == 0:
                    self.hit(pos, toms[q], 104 + 3 * q, limb, tag="acc")
                else:
                    self.hit(pos, SNARE, ramp(i, 32, 40, 74) - (4 if j % 2 else 0), limb,
                             tag="ghost")

        # bar 38: the feet switch to sextuplets, the hands pull 3-against-2 down the toms
        b = 38
        self.dbass(P(b, 0), 24, 1.0 / 6.0, 76, 90)
        for k in range(12):
            pos = P(b, k, 3)
            if k % 2 == 0:
                self.hit(pos, TOMS[k // 2], 100 + k, "R", tag="acc")
            else:
                self.hit(pos, SNARE, 50 + 2 * k, "L")

        # bar 39: the head displaced by a beat -- crash/snare, china/tom, crash/floor
        b = 39
        self.dbass(P(b, 0), 16, 0.25, 84, 96,
                   accents=[P(b, s) for s in (4, 7, 10, 12, 14)], acc=12)
        for s in range(4):
            self.hit(P(b, s), TOMS[s], 86 + 4 * s, hand16(s))
        self.hit(P(b, 4), CRASH, 118, "R", tag="acc")
        self.hit(P(b, 4), SNARE, 108, "L", tag="acc")
        self.hit(P(b, 7), CHINA, 112, "R", tag="acc")
        self.hit(P(b, 7), T3, 100, "L", tag="acc")
        self.hit(P(b, 10), CRASH2, 116, "R", tag="acc")
        self.hit(P(b, 10), F2, 104, "L", tag="acc")
        self.flam(P(b, 12), SNARE, 112, "R")
        self.hit(P(b, 13), SNARE, 50, "L", tag="ghost")
        self.hit(P(b, 14), CRASH, 118, "R", tag="acc")
        self.hit(P(b, 14), SNARE, 104, "L", tag="acc")
        self.hit(P(b, 15), T1, 92, "R")

        # bar 40: hands-and-feet sextuplets, then 32nds climbing into the downbeat
        b = 40
        pairs = [(SNARE, T1), (T2, T3), (T4, F1)]
        for q in range(3):
            base = q * 6
            a, c = pairs[q]
            self.hit(P(b, base, 6), a, 104 + 3 * q, "R", tag="acc")
            self.hit(P(b, base + 1, 6), a, 82 + 3 * q, "L")
            self.hit(P(b, base + 2, 6), c, 96 + 3 * q, "R")
            self.hit(P(b, base + 3, 6), c, 80 + 3 * q, "L")
            self.hit(P(b, base + 4, 6), KICK, 96, "RF")
            self.hit(P(b, base + 5, 6), KICK, 92, "LF")
        up = [F2, F1, T4, T3, T2, T1, SNARE, SNARE]
        for i in range(8):
            self.hit(P(b, 12) + i * 0.125, up[i], 98 + 3 * i, alt(i),
                     tag="acc" if i % 2 == 0 else "")
        self.dbass(P(b, 12), 4, 0.25, 96, 104)
        self.push(P(b, 0), P(b, 16), 0.03, release=1.0)

        # bar 41: cymbal-and-snare unisons every three sixteenths, then a dead stop
        b = 41
        self.dbass(P(b, 0), 15, 0.25, 86, 100,
                   accents=[P(b, s) for s in (0, 3, 6, 9, 12)], acc=12)
        cyms = (CRASH, CHINA, CRASH2, CHINA, CRASH)
        for j, s in enumerate((0, 3, 6, 9, 12)):
            self.hit(P(b, s), cyms[j], 114 + 2 * j, "R", tag="acc")
            self.hit(P(b, s), SNARE, 102 + 2 * j, "L", tag="acc")
            if s + 1 < 15:
                self.hit(P(b, s + 1), TOMS[(j + 1) % 6], 62 + 3 * j, "L")
            if s + 2 < 15:
                self.hit(P(b, s + 2), TOMS[(j + 2) % 6], 66 + 3 * j, "R")
        self.push(P(b, 14.5), P(b, 16), -0.14, release=0.3, shape="flat")

    def sec_build(self):
        # bar 42: the landing -- then a subito whisper of sixteenth ghost notes
        b = 42
        self.hit(P(b, 0), CRASH, 122, "R", tag="acc")
        self.hit(P(b, 0), CRASH2, 110, "L", tag="acc")
        self.hit(P(b, 0), KICK, 112, "RF")
        self.hat_foot(b, (4, 8, 12), 40)
        for s in range(2, 16):
            self.hit(P(b, s), SNARE, 16 + s * 0.55 + self.u(-2, 2), hand16(s), tag="ghost")

        # bar 43: the head murmured on the snare, still hushed
        b = 43
        self.hat_foot(b, (0, 4, 8, 12), 44)
        self.hit(P(b, 0), KICK, 52, "RF")
        accents = {0: 46, 3: 50, 6: 55}
        for s in range(16):
            v = accents.get(s, 20 + s * 0.6)
            self.hit(P(b, s), SNARE, v + self.u(-2, 2), hand16(s),
                     tag="" if s in accents else "ghost")

        # bar 44: the head moves onto the toms, 32nd diddles creep in
        b = 44
        self.hat_foot(b, (4, 12), 46)
        self.kicks(b, (0, 8), 60)
        acc = {0: T1, 3: T2, 6: T3, 8: T3, 11: T4, 14: F1}
        for s in range(16):
            limb = hand16(s)
            if s in acc:
                self.hit(P(b, s), acc[s], 58 + 1.6 * s, limb, tag="acc")
            else:
                self.hit(P(b, s), SNARE, 26 + s * 0.9, limb, tag="ghost")
                if s in (5, 13):
                    self.hit(P(b, s + 0.5), SNARE, 24 + s, limb, tag="ghost")

        # bar 45: sextuplets, accents every fourth note -- a 3-against-2 tug down the toms
        b = 45
        self.hat_foot(b, (4, 12), 50)
        self.kicks(b, (0, 8), 72)
        for i in range(24):
            pos = P(b, i, 6)
            if i % 4 == 0:
                self.hit(pos, TOMS[i // 4], 70 + i * 1.3, alt(i), tag="acc")
            else:
                self.hit(pos, SNARE, 34 + i * 0.9, alt(i), tag="ghost")
        self.push(P(b, 0), P(b, 16), 0.02, release=0.5)

        # bar 46: the head shrunk to one beat of 32nds, four times, stepping down the kit
        b = 46
        self.hat_foot(b, (4, 12), 50)
        heads = [(T1, T2, T3), (T2, T3, T4), (T3, T4, F1), (T4, F1, F2)]
        for q in range(4):
            for j in range(8):
                pos = P(b, 0) + q + j * 0.125
                if j in (0, 3, 6):
                    self.hit(pos, heads[q][(0, 3, 6).index(j)], 84 + 6 * q + j, alt(j),
                             tag="acc")
                else:
                    self.hit(pos, SNARE, 44 + 5 * q + j * 0.5, alt(j), tag="ghost")
            self.hit(P(b, 0) + q, KICK, 84 + 4 * q, "RF")
            self.hit(P(b, 0) + q + 0.5, KICK, 80 + 4 * q, "RF")

        # bar 47: a full bar of 32nd singles around the kit over double bass -- the peak
        b = 47
        self.dbass(P(b, 0), 16, 0.25, 88, 104)
        path = [T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1, SNARE, SNARE, T1, T2, T3]
        for i in range(32):
            v = ramp(i, 32, 86, 124, 1.3) + (8 if i % 4 == 0 else 0)
            self.hit(P(b, 0) + i * 0.125, path[i // 2], v, alt(i),
                     tag="acc" if i % 4 == 0 else "")
        self.push(P(b, 0), P(b, 14), 0.035, release=1.0)

        # bar 48: RECAP -- motif A at full force, cymbals over both bass drums, held back
        b = 48
        self.hit(P(b, 0), CRASH, 124, "R", tag="acc")
        self.hit(P(b, 0), CRASH2, 118, "L", tag="acc")
        self.hit(P(b, 0), KICK, 118, "RF")
        self.hit(P(b, 0), KICK2, 110, "LF")
        self.hit(P(b, 3), CHINA, 118, "R", tag="acc")
        self.hit(P(b, 3), T4, 110, "L", tag="acc")
        self.hit(P(b, 3), KICK, 112, "RF")
        self.hit(P(b, 6), CRASH2, 120, "R", tag="acc")
        self.hit(P(b, 6), F2, 114, "L", tag="acc")
        self.hit(P(b, 6), KICK, 114, "RF")
        self.flam(P(b, 8), SNARE, 118, "R", kick=104)
        self.hit(P(b, 10), SNARE, 52, "R", tag="ghost")
        self.hit(P(b, 11), SNARE, 66, "L", tag="ghost")
        self.hit(P(b, 12), CRASH, 124, "R", tag="acc")
        self.hit(P(b, 12), SNARE, 112, "L", tag="acc")
        self.hit(P(b, 12), KICK, 116, "RF")
        for j, key in enumerate((T1, T2, T3, F1)):
            self.hit(P(b, 14) + j * 0.125, key, 100 + 4 * j, alt(j))
        self.push(P(b, 0), P(b, 8), -0.05, release=1.0, shape="flat")

        # bar 49: the head again on toms under cymbals, its tail exploding into 32nds
        b = 49
        self.hit(P(b, 0), CRASH2, 122, "R", tag="acc")
        self.hit(P(b, 0), T1, 112, "L", tag="acc")
        self.hit(P(b, 0), KICK, 116, "RF")
        self.hit(P(b, 3), CRASH, 118, "R", tag="acc")
        self.hit(P(b, 3), T3, 110, "L", tag="acc")
        self.hit(P(b, 3), KICK, 112, "RF")
        self.hit(P(b, 6), CHINA, 120, "R", tag="acc")
        self.hit(P(b, 6), F1, 114, "L", tag="acc")
        self.hit(P(b, 6), KICK, 114, "RF")
        self.flam(P(b, 8), SNARE, 116, "R", kick=106)
        path = spread([SNARE, T1, T2, T3, T4, F1, F2], 14, per=2)
        for i in range(14):
            self.hit(P(b, 9) + i * 0.125, path[i], ramp(i, 14, 90, 122, 1.2), alt(i, "L"),
                     tag="acc" if i % 2 == 0 else "")
        self.dbass(P(b, 9), 7, 0.25, 94, 108, first="LF")
        self.push(P(b, 8), P(b, 16), 0.03, release=1.0)

    def sec_finale(self):
        # bar 50: the showcase -- singles around the whole kit, crashes on the beats
        b = 50
        self.hit(P(b, 0), CRASH, 124, "R", tag="acc")
        self.hit(P(b, 0), KICK, 116, "RF")
        down = spread(TOMS, 12, per=2)
        for i in range(1, 12):
            if i == 6:
                self.hit(P(b, i, 6), CRASH2, 118, "R", tag="acc")
                self.hit(P(b, i, 6), KICK, 110, "RF")
                continue
            self.hit(P(b, i, 6), down[i], ramp(i, 12, 92, 110) + (6 if i % 2 == 0 else 0),
                     alt(i))
        up = spread([F2, F1, T4, T3, T2, T1, SNARE, SNARE], 16, per=2)
        for i in range(16):
            self.hit(P(b, 8) + i * 0.125, up[i], ramp(i, 16, 96, 124, 1.2), alt(i),
                     tag="acc" if i % 4 == 0 else "")
        self.dbass(P(b, 8), 8, 0.25, 96, 110)
        self.push(P(b, 0), P(b, 16), 0.03, release=1.0)

        # bar 51: the last word -- the head as stop-time hits, the flam, a swelling roll,
        # a held-back breath...
        b = 51
        for s, cym, tom, lf in ((0, CRASH, T1, KICK2), (3, CHINA, T3, None),
                                (6, CRASH2, F1, KICK2)):
            self.hit(P(b, s), cym, 124, "R", tag="acc")
            self.hit(P(b, s), tom, 116, "L", tag="acc")
            self.hit(P(b, s), KICK, 118, "RF")
            if lf:
                self.hit(P(b, s), lf, 110, "LF")
        self.flam(P(b, 8), SNARE, 120, "R", kick=110)
        self.roll(P(b, 9), P(b, 16), SNARE, 82, 124, r0=7.0, r1=9.0, vcurve=1.2, first="R")
        self.hit(P(b, 12), KICK, 104, "RF")
        self.hit(P(b, 14), KICK, 112, "RF")
        self.push(P(b, 14.8), P(b, 16), -0.30, release=0.35, shape="flat")

        # ...and the final hit: both crashes, both bass drums
        f = P(52, 0)
        self.hit(f, CRASH, 127, "R", tag="final")
        self.hit(f, CRASH2, 127, "L", tag="final")
        self.hit(f, KICK, 127, "RF", tag="final")
        self.hit(f, KICK2, 124, "LF", tag="final")
        return f

    def compose(self):
        self.tempo_plan()
        self.sec_intro()
        self.sec_groove()
        self.sec_around()
        self.sec_colors()
        self.sec_triplets()
        self.sec_thunder()
        self.sec_build()
        return self.sec_finale()


class TempoMap(object):
    """Elastic pulse: section tempos + phrase arcs + rushes/holds + slow drift, rendered as
    a dense MIDI tempo map and scaled so the final hit lands at FINAL_TIME."""

    def __init__(self, solo, final_beat):
        self.pushes = list(solo.pushes)
        anchors = sorted(solo.anchors)
        self.ax = [a[0] for a in anchors]
        self.ay = [a[1] for a in anchors]
        rng = random.Random(SEED * 7 + 3)
        self.ph = [rng.uniform(0.0, 2.0 * math.pi) for _ in range(3)]
        k_final = int(round((final_beat + LEAD) / SEG))
        self.k_total = k_final + int(round(14.0 / SEG))
        raw = [SEG * 60.0 / self.bpm((k + 0.5) * SEG - LEAD) for k in range(self.k_total)]
        self.scale = sum(raw[:k_final]) / FINAL_TIME
        self.us = [int(round(d / self.scale / SEG * 1e6)) for d in raw]
        self.d = [us * SEG / 1e6 for us in self.us]
        self.T = [0.0]
        for d in self.d:
            self.T.append(self.T[-1] + d)

    def base(self, x):
        ax, ay = self.ax, self.ay
        if x <= ax[0]:
            return ay[0]
        if x >= ax[-1]:
            return ay[-1]
        i = bisect.bisect_right(ax, x) - 1
        x0, x1 = ax[i], ax[i + 1]
        return ay[i] + (ay[i + 1] - ay[i]) * smooth((x - x0) / (x1 - x0))

    def push_at(self, x):
        tot = 0.0
        for s, e, amt, rel, shape in self.pushes:
            if shape == "arc":
                if s < x < e:
                    tot += amt * math.sin(math.pi * (x - s) / (e - s))
            elif shape == "flat":
                if s <= x <= e:
                    tot += amt
                elif s - rel < x < s:
                    tot += amt * smooth((x - (s - rel)) / rel)
                elif e < x < e + rel:
                    tot += amt * (1.0 - smooth((x - e) / rel))
            else:
                if s <= x <= e:
                    tot += amt * smooth((x - s) / (e - s))
                elif e < x < e + rel:
                    tot += amt * (1.0 - smooth((x - e) / rel))
        return tot

    def bpm(self, x):
        drift = (0.005 * math.sin(2.0 * math.pi * x / 11.3 + self.ph[0]) +
                 0.003 * math.sin(2.0 * math.pi * x / 4.7 + self.ph[1]) +
                 0.002 * math.sin(2.0 * math.pi * x / 2.3 + self.ph[2]))
        return self.base(x) * (1.0 + self.push_at(x)) * (1.0 + drift)

    def time_at(self, fb):
        """Seconds at file beat fb (musical beat + LEAD)."""
        if fb <= 0.0:
            return fb * self.d[0] / SEG
        k = min(int(fb / SEG), self.k_total - 1)
        return self.T[k] + (fb - k * SEG) / SEG * self.d[k]

    def tick_at(self, t):
        if t <= 0.0:
            return 0
        k = min(bisect.bisect_right(self.T, t) - 1, self.k_total - 1)
        frac = (t - self.T[k]) / self.d[k]
        return int(round((k + frac) * SEG * TPB))


def swing_pos(x, swings):
    """Delay off-beat sixteenths inside swing regions (fading in and out)."""
    for s, e, ratio, fade in swings:
        if s <= x < e:
            q = x * 4.0
            if abs(q - round(q)) > 1e-6 or int(round(q)) % 2 == 0:
                return x
            w = max(0.0, min(1.0, (x - s) / fade, (e - x) / fade))
            r = 0.5 + (ratio - 0.5) * w
            return (x - 0.25) + 0.5 * r
    return x


def perform_timing(notes, tm, swings, rng):
    phase = {}
    for limb in ("R", "L", "RF", "LF"):
        phase[limb] = (rng.uniform(0.0, 2.0 * math.pi), rng.uniform(0.0, 2.0 * math.pi))
    for n in notes:
        n.t = tm.time_at(swing_pos(n.beat, swings) + LEAD) + n.dt
    notes.sort(key=lambda n: (n.t, LIMB_ORDER[n.limb], n.key))
    # how crowded each stroke is: human scatter must shrink in fast passages
    for group in (HANDS, FEET):
        sub = [n for n in notes if n.limb in group]
        ts = [n.t for n in sub]
        for i, n in enumerate(sub):
            g = 0.5
            j = i - 1
            while j >= 0 and ts[i] - ts[j] < 0.012:
                j -= 1
            if j >= 0:
                g = min(g, ts[i] - ts[j])
            j = i + 1
            while j < len(sub) and ts[j] - ts[i] < 0.012:
                j += 1
            if j < len(sub):
                g = min(g, ts[j] - ts[i])
            n.gap = g
    for n in notes:
        if n.tag == "final":
            continue
        sd = {"ghost": 0.0075, "grace": 0.003, "acc": 0.0045, "backbeat": 0.0045,
              "roll": 0.004}.get(n.tag, 0.0055)
        sd = min(sd, 0.1 * n.gap)
        jit = max(-2.2 * sd, min(2.2 * sd, rng.gauss(0.0, sd)))
        bias = LIMB_BIAS[n.limb]
        if n.tag == "backbeat":
            bias += 0.006          # laid-back backbeat
        elif n.tag == "ghost":
            bias += 0.003          # ghost notes sit a touch late
        elif n.tag == "acc":
            bias -= 0.0015         # accents are driven slightly forward
        ph = phase[n.limb]
        drift = (0.0035 * math.sin(2.0 * math.pi * n.t / 6.1 + ph[0]) +
                 0.002 * math.sin(2.0 * math.pi * n.t / 2.9 + ph[1]))
        n.t += jit + (bias + drift) * min(1.0, n.gap / 0.09)


def perform_dynamics(notes, rng):
    for n in notes:
        v = n.vel
        if n.tag != "final":
            if n.limb == "L":
                v -= 2.0
            v += rng.gauss(0.0, 2.5 if n.tag in ("ghost", "grace", "roll") else 3.5)
        lo = 8 if n.tag in ("ghost", "grace", "roll") else 20
        n.vel = int(round(max(lo, min(127, v))))


def merge_unisons(notes):
    notes.sort(key=lambda n: (n.key, n.t))
    out = []
    for n in notes:
        if out and out[-1].key == n.key and n.t - out[-1].t < 0.008:
            if n.vel > out[-1].vel:
                out[-1] = n
            continue
        out.append(n)
    out.sort(key=lambda n: (n.t, LIMB_ORDER[n.limb], n.key))
    return out


def enforce_limbs(notes):
    """Safety net: a limb can never strike twice faster than it physically can."""
    keep = []
    last = {}
    dropped = 0
    for n in notes:
        p = last.get(n.limb)
        if p is not None and n.t - p.t < MIN_IOI[n.limb]:
            dropped += 1
            if n.vel > p.vel:
                keep.remove(p)
                keep.append(n)
                last[n.limb] = n
            continue
        keep.append(n)
        last[n.limb] = n
    keep.sort(key=lambda n: (n.t, LIMB_ORDER[n.limb], n.key))
    return keep, dropped


def dur_cap(n):
    k = n.key
    if n.tag == "final":
        return 3.3
    if k in (CRASH, CRASH2, CHINA, SPLASH):
        return 1.6
    if k in (RIDE, BELL):
        return 0.9
    if k == HHO:
        return 0.45
    if k in (KICK, KICK2):
        return 0.3
    if k in TOMS:
        return 0.45
    if k == SNARE:
        return 0.22
    return 0.18


def assign_ticks(notes, tm, end_tick):
    """Note-offs never outlast the limb's next stroke or the same drum's next note."""
    for n in notes:
        n.on = tm.tick_at(n.t)
    next_limb = {}
    next_key = {}
    last_limb = {}
    last_key = {}
    for idx, n in enumerate(notes):
        if n.limb in last_limb:
            next_limb[last_limb[n.limb]] = n.t
        last_limb[n.limb] = idx
        if n.key in last_key:
            next_key[last_key[n.key]] = n.on
        last_key[n.key] = idx
    for idx, n in enumerate(notes):
        end_t = n.t + dur_cap(n)
        if idx in next_limb:
            end_t = min(end_t, next_limb[idx] - 0.002)
        off = tm.tick_at(max(end_t, n.t + 0.01))
        if idx in next_key:
            off = min(off, next_key[idx] - 1)
        n.off = min(max(off, n.on + 1), end_tick)


def write_midi(notes, tm, end_tick, path):
    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)

    ev0 = [(0, 0, 0, mido.MetaMessage("track_name", name="Drum Solo", time=0)),
           (0, 1, 1, mido.MetaMessage("time_signature", numerator=4, denominator=4,
                                      clocks_per_click=24, notated_32nd_notes_per_beat=8,
                                      time=0))]
    prev = None
    seg_ticks = int(SEG * TPB)
    for k, us in enumerate(tm.us):
        tick = k * seg_ticks
        if tick > end_tick:
            break
        if us != prev:
            ev0.append((tick, 2, k + 2, mido.MetaMessage("set_tempo", tempo=us, time=0)))
            prev = us

    ev1 = [(0, 0, 0, mido.MetaMessage("track_name", name="Drums", time=0)),
           (0, 1, 1, mido.Message("sysex", data=[0x7E, 0x7F, 0x09, 0x01], time=0)),
           (8, 2, 2, mido.Message("program_change", channel=CH, program=0, time=0))]
    for i, (cc, val) in enumerate(((7, 112), (10, 64), (11, 127), (91, 46), (93, 0))):
        ev1.append((8, 3, 3 + i,
                    mido.Message("control_change", channel=CH, control=cc, value=val, time=0)))
    seq = 100
    for n in notes:
        seq += 1
        ev1.append((n.off, 10, seq,
                    mido.Message("note_off", channel=CH, note=n.key, velocity=0, time=0)))
        seq += 1
        ev1.append((n.on, 20, seq,
                    mido.Message("note_on", channel=CH, note=n.key, velocity=n.vel, time=0)))

    for events in (ev0, ev1):
        track = mido.MidiTrack()
        events.sort(key=lambda e: (e[0], e[1], e[2]))
        now = 0
        for tick, _, _, msg in events:
            track.append(msg.copy(time=tick - now))
            now = tick
        track.append(mido.MetaMessage("end_of_track", time=max(0, end_tick - now)))
        mid.tracks.append(track)
    mid.save(path)


def main():
    solo = Solo(SEED)
    final_beat = solo.compose()
    tm = TempoMap(solo, final_beat)
    rng = random.Random(SEED * 31 + 7)
    notes = solo.notes
    perform_timing(notes, tm, solo.swings, rng)
    perform_dynamics(notes, rng)
    notes = merge_unisons(notes)
    notes, dropped = enforce_limbs(notes)
    end_tick = tm.tick_at(END_TIME)
    assign_ticks(notes, tm, end_tick)
    write_midi(notes, tm, end_tick, OUTFILE)
    print("wrote %s: %d strokes, %.1f s, tempo scale %.3f, %d strokes thinned"
          % (OUTFILE, len(notes), END_TIME, tm.scale, dropped))


if __name__ == "__main__":
    main()
