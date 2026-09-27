#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid, a two-minute General MIDI drum solo on channel 10.

The solo is built from a few motifs:
  Motif A : a 3-3-4-2-4 accent cell (son-clave shaped) that is stated, re-orchestrated,
            displaced, diminished (32nds), augmented (8ths), put in triplets, hidden inside
            ghost-note streams, and kept alive on a wood-block pedal in the colour section.
  Motif B : hand-hand-foot triplets travelling down the toms (with RLRK / RRLLK variants).
  Motif C : a six-stroke-roll "signature" fill that carries phrases into the downbeat.

Form, in bars of 4/4:
   0-3   statement       4-11  development      12-19 snare, hemiola, roll swell
  20-27  tom travel     28-35  colour/release   36-43 triplets (motif B)
  44-51  double-bass build                      52-57 climax, final hit on bar 58

Each limb (R, L, RF, LF) strikes one instrument at a time, so no more than two hands and
two feet ever play at once. A final check enforces a minimum re-strike time per limb.
The tempo map surges and settles. Notes are placed by hand with lean, drift and jitter,
and a seeded RNG makes every run write the same file.
"""
import bisect
import math
import random

import mido

PPQ = 960
CH = 9                    # MIDI channel 10
SEED = 7041969
FINAL_BAR = 58
FINAL_HIT_SEC = 116.8
RING_SEC = 3.0
SEG = 0.5                 # tempo-map resolution in beats
LEAD = 480                # short silence before the first stroke (ticks)

# General MIDI percussion
KICK = 36; STICK = 37; SNARE = 38; HH_P = 44
CRASH1 = 49; CRASH2 = 57; CHINA = 52; SPLASH = 55; RIDE = 51; BELL = 53
T1, T2, T3, F1, F2 = 50, 48, 45, 43, 41
COWBELL = 56; TIMB_H = 65; TIMB_L = 66; WB_H = 76; AGOGO_H = 67; AGOGO_L = 68

TOMS = [T1, T2, T3, F1, F2]
KIT = [SNARE, T1, T2, T3, F1, F2]
CYMS = (CRASH1, CRASH2, CHINA, SPLASH, RIDE, BELL)

R, L, RF, LF = 'R', 'L', 'RF', 'LF'
STICK_MAP = {'R': R, 'L': L, 'K': RF, 'k': LF}

CLAVE = [0, 3, 6, 10, 12]          # motif A on a 16-slot bar
TCLAVE = [0, 4, 8, 14, 18]         # motif A in triplets on a 24-slot (sextuplet) bar

# Tempo anchors: (bar, multiplier of base tempo)
ANCHORS = [
    (0.0, 0.95), (2.0, 0.96), (3.5, 0.965), (4.0, 0.975),
    (7.8, 0.995), (8.0, 0.99), (11.0, 1.005), (11.95, 1.03),
    (12.0, 0.965), (16.0, 0.975), (17.9, 0.995), (18.0, 0.98), (19.95, 1.045),
    (20.0, 1.035), (27.0, 1.06), (27.95, 1.05),
    (28.0, 0.975), (35.0, 0.985), (35.95, 1.0),
    (36.0, 1.0), (39.0, 1.025), (39.95, 1.0), (40.0, 1.015), (43.95, 1.055),
    (44.0, 1.04), (48.0, 1.06), (51.95, 1.1),
    (52.0, 1.085), (55.95, 1.115), (56.0, 1.085), (57.0, 1.04), (57.5, 0.95),
    (58.0, 0.8), (62.0, 0.8),
]

SIG = {'a': 0.0045, 'n': 0.0065, 'g': 0.0085, 'f': 0.003, 'x': 0.0015}
BIAS = {'a': -0.0015, 'n': 0.0, 'g': 0.005, 'f': 0.0, 'x': 0.0}
PRI = {'x': 5, 'a': 4, 'n': 3, 'g': 2, 'f': 1}
MIN_GAP = {R: 0.038, L: 0.038, RF: 0.062, LF: 0.062}


def ramp(i, n, a, b):
    return a + (b - a) * (i / (n - 1) if n > 1 else 1.0)


def walk(drums, n, shape='down', group=1):
    """Route n strokes across a list of drums (ordered high -> low)."""
    k = len(drums)
    groups = max(1, -(-n // group))
    out = []
    for i in range(n):
        g = i // group
        x = g / (groups - 1) if groups > 1 else 0.0
        if shape == 'down':
            y = x
        elif shape == 'up':
            y = 1.0 - x
        else:  # wave: high -> low -> high
            y = 0.5 - 0.5 * math.cos(2 * math.pi * x)
        out.append(drums[min(k - 1, int(round(y * (k - 1))))])
    return out


def tempo_mult(beat):
    bar = beat / 4.0
    if bar <= ANCHORS[0][0]:
        m = ANCHORS[0][1]
    elif bar >= ANCHORS[-1][0]:
        m = ANCHORS[-1][1]
    else:
        m = ANCHORS[-1][1]
        for (b0, m0), (b1, m1) in zip(ANCHORS, ANCHORS[1:]):
            if b0 <= bar < b1:
                x = (bar - b0) / (b1 - b0)
                x = x * x * (3.0 - 2.0 * x)
                m = m0 + (m1 - m0) * x
                break
    w = max(0.0, min(1.0, 57.0 - bar))
    phrase = 0.011 * math.sin(math.pi * ((beat % 16.0) / 16.0))
    wobble = (0.004 * math.sin(2 * math.pi * beat / 6.7 + 1.3)
              + 0.0025 * math.sin(2 * math.pi * beat / 2.9 + 0.4))
    return m * (1.0 + w * (phrase + wobble))


def build_tempo():
    nseg = int(math.ceil((FINAL_BAR * 4 + 16) / SEG))
    mults = [tempo_mult((k + 0.5) * SEG) for k in range(nseg)]
    final_seg = int(FINAL_BAR * 4 / SEG)
    inv = sum(SEG / m for m in mults[:final_seg])
    base_bpm = 60.0 * inv / FINAL_HIT_SEC
    us = [int(round(60e6 / (base_bpm * m))) for m in mults]
    cum = [0.0]
    for u in us:
        cum.append(cum[-1] + SEG * u / 1e6)
    return us, cum


class TempoMap:
    def __init__(self, us, cum):
        self.us = us
        self.cum = cum

    def b2s(self, b):
        k = max(0, min(len(self.us) - 1, int(math.floor(b / SEG))))
        return self.cum[k] + (b - k * SEG) * self.us[k] / 1e6

    def s2b(self, s):
        k = max(0, min(len(self.us) - 1, bisect.bisect_right(self.cum, s) - 1))
        return k * SEG + (s - self.cum[k]) * 1e6 / self.us[k]


class Drummer:
    def __init__(self):
        self.rng = random.Random(SEED)
        self.ev = []
        self.leans = []
        self.swings = [(16.0, 32.0, 0.07), (112.0, 140.0, 0.09)]

    # ---------------------------------------------------------------- primitives
    def hit(self, t, note, vel, limb, kind='n'):
        jit = {'a': 3.0, 'n': 4.0, 'g': 2.5, 'f': 2.0, 'x': 0.0}[kind]
        v = vel + self.rng.gauss(0.0, jit)
        if limb == L and kind in ('n', 'g'):
            v *= 0.96
        v = int(round(max(1, min(127, v))))
        self.ev.append([float(t), note, v, limb, kind])

    def flam(self, t, note, vel, limb):
        other = L if limb == R else R
        self.hit(t, note, max(16, vel * 0.42), other, 'f')
        self.hit(t, note, vel, limb, 'a')

    def kick(self, t, vel, foot=RF, kind='n'):
        self.hit(t, KICK, vel, foot, kind)

    def hat(self, t, vel=50):
        self.hit(t, HH_P, vel, LF, 'n')

    def lean(self, b0, b1, ms0, ms1):
        self.leans.append((b0, b1, ms0, ms1))

    def seq(self, t0, step, items, stick='RL', lead=0):
        for i, it in enumerate(items):
            if it is None:
                continue
            limb = STICK_MAP[stick[(i + lead) % len(stick)]]
            note, vel, kind = it
            t = t0 + i * step
            if kind == 'F':
                self.flam(t, note, vel, limb)
            else:
                self.hit(t, note, vel, limb, kind)

    def six_stroke(self, t, dur, first, last, lo, hi, diddle=SNARE):
        """Motif C: R ll rr L, accented at both ends, carrying into the next downbeat."""
        s = dur / 6.0
        self.hit(t, first, hi * 0.93, R, 'a')
        for j, limb in enumerate((L, L, R, R)):
            self.hit(t + (j + 1) * s, diddle, lo + (hi * 0.62 - lo) * j / 3.0, limb,
                     'g' if j < 2 else 'n')
        self.hit(t + 5 * s, last, hi, L, 'a')

    def double_bass(self, t0, n, v0, v1, accents=()):
        for i in range(n):
            v = ramp(i, n, v0, v1) + (7 if i % 4 == 0 else 0) + (10 if i in accents else 0)
            self.kick(t0 + i * 0.25, v, RF if i % 2 == 0 else LF, 'a' if i in accents else 'n')

    def motif_big(self, t, slots, cyms, base):
        path = walk(TOMS, 16, 'down')
        k = 0
        for s in range(16):
            tt = t + s / 4.0
            if s in slots:
                self.hit(tt, cyms[k], base + 14, R, 'a')
                self.hit(tt, SNARE if k % 2 == 0 else F1, base + 8, L, 'a')
                k += 1
            else:
                self.hit(tt, path[s], base - 30 + 2 * s, R if s % 2 == 0 else L, 'n')

    # ---------------------------------------------------------------- sections
    def sec1(self):
        rng = self.rng
        # bar 0: the motif, bare
        t = 0.0
        it = [None] * 16
        it[0] = (SNARE, 100, 'a'); it[3] = (SNARE, 84, 'a'); it[6] = (SNARE, 94, 'a')
        it[10] = (F1, 92, 'a'); it[12] = (F1, 104, 'a'); it[15] = (SNARE, 28, 'g')
        self.seq(t, 0.25, it)
        self.kick(t, 92, kind='a'); self.kick(t + 3.0, 96, kind='a')
        self.hat(t + 1, 44); self.hat(t + 3, 48)
        # bar 1: answer, contour inverted onto the toms
        t = 4.0
        it = [None] * 16
        it[0] = (F1, 96, 'a'); it[3] = (T2, 86, 'a'); it[6] = (T1, 92, 'a')
        it[7] = (SNARE, 26, 'g'); it[9] = (SNARE, 30, 'g'); it[10] = (SNARE, 98, 'F')
        it[12] = (SNARE, 106, 'a'); it[13] = (SNARE, 32, 'g')
        it[14] = (T1, 60, 'n'); it[15] = (T2, 68, 'n')
        self.seq(t, 0.25, it)
        self.kick(t, 90, kind='a'); self.kick(t + 2.0, 58); self.kick(t + 3.0, 98, kind='a')
        self.hat(t + 1, 46); self.hat(t + 3, 50)
        # bar 2: motif with ghost notes breathing between the accents
        t = 8.0
        acc = {0: (SNARE, 104), 3: (T1, 90), 6: (SNARE, 98), 10: (F1, 96), 12: (F1, 108)}
        it = [None] * 16
        for s in range(16):
            if s in acc:
                it[s] = (acc[s][0], acc[s][1], 'a')
            elif s in (1, 5, 8, 13, 15) or rng.random() < 0.35:
                it[s] = (SNARE, 24 + 1.2 * s, 'g')
        self.seq(t, 0.25, it)
        self.kick(t, 96, kind='a'); self.kick(t + 1.75, 64); self.kick(t + 3.0, 100, kind='a')
        self.hat(t + 1, 48); self.hat(t + 3, 52)
        # bar 3: fragment, then a fill carried by the six-stroke signature
        t = 12.0
        it = [None] * 12
        it[0] = (SNARE, 102, 'a'); it[1] = (SNARE, 28, 'g'); it[3] = (T1, 92, 'a')
        it[4] = (SNARE, 30, 'g'); it[5] = (SNARE, 34, 'g'); it[6] = (SNARE, 98, 'a')
        it[7] = (SNARE, 38, 'g')
        for j, s in enumerate(range(8, 12)):
            it[s] = ([T1, T1, T2, T2][j], 70 + 6 * j, 'n')
        self.seq(t, 0.25, it)
        self.six_stroke(t + 3.0, 1.0, T3, F1, 36, 112)
        self.kick(t, 94, kind='a'); self.kick(t + 2.0, 78); self.kick(t + 3.0, 104, kind='a')
        self.hat(t + 1, 48)
        self.lean(14.0, 16.0, 0, -6)

    def sec2(self):
        rng = self.rng
        kick_pats = [[0, 7, 10], [0, 8, 11, 14], [0, 5, 10], [0, 3, 8, 11]]
        rng.shuffle(kick_pats)
        # bars 4-7: motif over ride time, bell on the motif, left hand talking
        for k, b in enumerate(range(4, 8)):
            t = 4.0 * b
            shift = 2 if b == 6 else 0
            cl = [(s + shift) % 16 for s in CLAVE]
            end = 12 if b == 7 else 16
            for s in range(0, end, 2):
                if b == 4 and s == 0:
                    self.hit(t, CRASH1, 112, R, 'a')
                elif s in cl:
                    self.hit(t + s / 4.0, BELL, 94 + 4 * k, R, 'a')
                else:
                    self.hit(t + s / 4.0, RIDE, 70 if s % 4 == 0 else 54, R, 'n')
            p = 0.3 + 0.12 * k
            for s in range(end):
                if s % 2 == 1:
                    if s in cl:
                        self.hit(t + s / 4.0, SNARE, 96 + 3 * k, L, 'a')
                    elif rng.random() < p:
                        self.hit(t + s / 4.0, SNARE, 26 + rng.random() * 12, L, 'g')
                elif b in (4, 5) and s in (4, 12):
                    self.hit(t + s / 4.0, SNARE, 84, L, 'n')
            for s in kick_pats[k]:
                if s < end:
                    self.kick(t + s / 4.0, 92 if s == 0 else 72)
            if 12 in cl and b != 7:
                self.kick(t + 3.0, 88)
            self.hat(t + 1, 50)
            if b != 7:
                self.hat(t + 3, 54)
        t = 28.0
        notes = [T1, T1, T2, T2, F1, F2]
        for j in range(6):
            self.hit(t + 3.0 + j / 6.0, notes[j], 72 + 7 * j, R if j % 2 == 0 else L,
                     'a' if j in (0, 5) else 'n')
        self.kick(t + 3.0, 92); self.kick(t + 3.5, 96)
        self.lean(30.0, 32.0, 0, -5)

        # bar 8: linear orchestration of the motif
        t = 32.0
        orch = [CRASH1, T1, T2, F1, F2]
        it = [None] * 16
        kicks = [0, 12]
        for s in range(16):
            if s in CLAVE:
                i = CLAVE.index(s)
                it[s] = (orch[i], 112 if i in (0, 4) else 100, 'a')
            else:
                r = rng.random()
                if r < 0.55:
                    it[s] = (SNARE, 28 + rng.random() * 12, 'g')
                elif r < 0.75:
                    kicks.append(s)
                elif r < 0.9:
                    it[s] = (rng.choice([T1, T2]), 58, 'n')
        self.seq(t, 0.25, it)
        for s in sorted(kicks):
            self.kick(t + s / 4.0, 96 if s in (0, 12) else 68)
        for q in range(4):
            self.hat(t + q, 40 if q % 2 == 0 else 52)

        # bar 9: motif diminished to 32nds, then a sextuplet descent
        t = 36.0
        orch = [SNARE, T1, SNARE, F1, F1]
        it = []
        for s in range(16):
            if s in CLAVE:
                it.append((orch[CLAVE.index(s)], 104, 'a'))
            else:
                it.append((SNARE, 30 + s, 'g'))
        self.seq(t, 0.125, it)
        self.kick(t, 94, kind='a'); self.kick(t + 1.5, 90)
        run = walk(TOMS, 12, 'down', 2)
        for j in range(12):
            acc = j % 6 == 0
            self.hit(t + 2.0 + j / 6.0, run[j], 72 + 3 * j + (12 if acc else 0),
                     R if j % 2 == 0 else L, 'a' if acc else 'n')
        self.kick(t + 2.0, 90); self.kick(t + 3.0, 96)
        self.hat(t + 1, 50); self.hat(t + 3, 52)

        # bar 10: paradiddles orchestrated, motif accents on the toms
        t = 40.0
        stick = "RLRRLRLL"
        it = []
        for s in range(16):
            ch = stick[s % 8]
            if s in CLAVE:
                if ch == 'R':
                    note = F1 if s < 8 else F2
                else:
                    note = T1 if s < 8 else T2
                it.append((note, 106, 'a'))
            elif s % 4 == 0:
                it.append((SNARE, 62, 'n'))
            else:
                it.append((SNARE, 32 + rng.random() * 8, 'g'))
        self.seq(t, 0.25, it, stick)
        for s, v in ((0, 94), (7, 70), (12, 92), (14, 74)):
            self.kick(t + s / 4.0, v)
        self.hat(t + 1, 50); self.hat(t + 3, 52)

        # bar 11: accelerating fill into the snare section
        t = 44.0
        self.seq(t, 0.25, [(SNARE, 98, 'a'), (SNARE, 62, 'n'), (T1, 80, 'n'), (T1, 84, 'n')])
        self.seq(t + 1.0, 1 / 6.0, [(T1, 90, 'a'), (T2, 78, 'n'), (T2, 82, 'n'),
                                    (T3, 86, 'n'), (T3, 90, 'n'), (F1, 96, 'n')])
        run = walk(TOMS, 16, 'down', 2)
        items = []
        for j in range(16):
            v = 78 + 2.4 * j
            kind = 'n'
            if j in (4, 8):
                v += 14
                kind = 'a'
            if j >= 12:
                v += 6
            items.append((run[j], v, kind))
        self.seq(t + 2.0, 0.125, items)
        for q in range(4):
            self.kick(t + q, 90 + 4 * q, kind='a')
        self.kick(t + 2.5, 94)
        self.hat(t + 1, 50); self.hat(t + 3, 54)
        self.lean(44.0, 48.0, 0, -7)

    def sec3(self):
        rng = self.rng
        # bar 12: land, let it ring, then whisper
        t = 48.0
        self.hit(t, CRASH1, 114, R, 'a'); self.kick(t, 110, kind='a')
        it = [None] * 16
        for s in range(4, 16):
            if s in (6, 10, 12):
                it[s] = (SNARE, 70, 'a')
            else:
                it[s] = (SNARE, 20 + (s - 4) * 0.9, 'g')
        self.seq(t, 0.25, it)
        for q in (1, 2, 3):
            self.hat(t + q, 40)
        self.kick(t + 3.0, 58)
        # bar 13: continuous singles, the motif hidden in the accents
        t = 52.0
        it = []
        for s in range(16):
            if s in CLAVE:
                it.append((SNARE, 76 + (8 if s in (0, 12) else 0), 'a'))
            else:
                it.append((SNARE, 24 + rng.random() * 10, 'g'))
        self.seq(t, 0.25, it)
        self.kick(t, 72); self.kick(t + 2.75, 60)
        for q in range(4):
            self.hat(t + q, 42)
        # bar 14: paradiddle-diddles, accents stepping onto the toms, inner crescendo
        t = 56.0
        heads = [SNARE, T1, SNARE, F1]
        it = []
        for i in range(24):
            bt, pos = divmod(i, 6)
            if pos == 0:
                it.append((heads[bt], 68 + 10 * bt, 'a'))
            else:
                it.append((SNARE, 26 + 22 * i / 23.0 - (4 if pos in (3, 5) else 0), 'g'))
        self.seq(t, 1 / 6.0, it, "RLRRLL")
        self.kick(t, 70); self.kick(t + 2.0, 74)
        for q in range(4):
            self.hat(t + q, 44)
        # bar 15: the motif in flams, held back, then a gap
        t = 60.0
        it = [None] * 16
        for s in CLAVE:
            it[s] = (SNARE, 94, 'F')
        for s in (1, 2, 4, 5, 8, 9, 11, 13):
            if rng.random() < 0.75:
                it[s] = (SNARE, 26 + rng.random() * 10, 'g')
        it[14] = (F1, 104, 'a')
        self.seq(t, 0.25, it)
        self.kick(t, 80); self.kick(t + 3.5, 100, kind='a')
        for q in range(4):
            self.hat(t + q, 44)
        self.lean(60.0, 64.0, 2, 9)
        # bars 16-17: the motif's 3+3 opening extended into a hemiola across the barline
        t = 64.0
        heads = [T1, SNARE, T2, SNARE, T3, F1, SNARE, T1, T2, F1, F2]
        idx = 0
        for s in range(32):
            x = s / 31.0
            limb = R if s % 2 == 0 else L
            if s % 3 == 0:
                self.hit(t + s / 4.0, heads[idx], 80 + 32 * x, limb, 'a')
                self.kick(t + s / 4.0, 62 + 40 * x)
                idx += 1
            else:
                self.hit(t + s / 4.0, SNARE, 26 + 22 * x, limb, 'g')
        for q in range(8):
            self.hat(t + q, 46)
        self.lean(68.0, 72.0, 0, -4)
        # bars 18-19: subito piano, double-stroke roll swelling, motif poking out, resolve
        t = 72.0
        n = 64
        cl19 = [32 + 2 * s for s in CLAVE]
        fin = [T1, T1, T2, T2, T3, F1, F1, F2]
        for i in range(n):
            x = i / (n - 1.0)
            v = 20 + 96 * (x ** 1.7)
            if i < 56:
                limb = R if (i % 4) < 2 else L
                note = SNARE
                if i % 2 == 1:
                    v *= 0.9
                kind = 'g' if v < 42 else 'n'
                if i in cl19:
                    v += 16
                    kind = 'a'
            else:
                limb = R if (i - 56) % 2 == 0 else L
                note = fin[i - 56]
                v += 4
                kind = 'a' if i in (56, 63) else 'n'
            self.hit(t + i * 0.125, note, v, limb, kind)
        for q in range(4):
            self.hat(t + q, 38 + 3 * q)
        for e in range(8):
            self.hat(t + 4 + e * 0.5, 50 + 4 * e)
        self.kick(t + 2.0, 50); self.kick(t + 3.0, 58)
        for q in range(4):
            self.kick(t + 4 + q, 70 + 10 * q)
        self.kick(t + 7.5, 110)
        self.lean(72.0, 80.0, 0, -8)

    def sec4(self):
        # bar 20: 16th singles around the kit, motif accents with the bass drum
        t = 80.0
        path = [CRASH1, SNARE, T1, T1, T2, T2, T3, T3, F1, F1, F2, F2, F1, F1, T3, T3]
        it = []
        for s in range(16):
            if s in CLAVE:
                it.append((path[s], 116 if s == 0 else 106, 'a'))
            else:
                it.append((path[s], 70 + s, 'n'))
        self.seq(t, 0.25, it)
        for s in CLAVE:
            self.kick(t + s / 4.0, 104 if s == 0 else 92, kind='a')
        self.hat(t + 1, 56); self.hat(t + 3, 60)
        # bar 21: sextuplet singles in groups of three, travelling
        t = 84.0
        groups = [T1, T2, T3, F1, T2, T3, F1, F2]
        for g in range(8):
            for j in range(3):
                i = g * 3 + j
                v = 104 if j == 0 else 70 + 6 * j + 4 * (g % 2)
                self.hit(t + i / 6.0, groups[g], v, R if i % 2 == 0 else L, 'a' if j == 0 else 'n')
        for q in range(4):
            self.kick(t + q, 96, kind='a')
        self.hat(t + 1.5, 52); self.hat(t + 3.5, 58)
        # bar 22: 32nd doubles down the toms, then the motif's second half answers
        t = 88.0
        pairs = [(R, SNARE), (L, T1), (R, T1), (L, T2), (R, T2), (L, T3), (R, T3), (L, F1)]
        for p, (limb, note) in enumerate(pairs):
            for d in range(2):
                i = 2 * p + d
                self.hit(t + i * 0.125, note, 70 + 2.2 * i - (8 if d == 1 else 0), limb, 'n')
        resp = [(F2, 108, 'a'), (SNARE, 34, 'g'), (F1, 104, 'a'), (SNARE, 38, 'g'),
                (CRASH1, 114, 'a'), (SNARE, 36, 'g'), (SNARE, 44, 'g'), (T1, 74, 'n')]
        self.seq(t + 2.0, 0.25, resp)
        self.kick(t, 88); self.kick(t + 1.0, 84)
        for s in (0, 2, 4):
            self.kick(t + 2.0 + s / 4.0, 100, kind='a')
        self.hat(t + 1, 54)
        # bar 23: linear hand-hand-foot-foot, six-stroke into the downbeat
        t = 92.0
        hands = [T1, SNARE, T3, T2, F2, F1]
        hi = 0
        for i in range(12):
            ch = "RLKk"[i % 4]
            tt = t + i * 0.25
            if ch in 'RL':
                self.hit(tt, hands[hi], 104 if ch == 'R' else 90, STICK_MAP[ch],
                         'a' if ch == 'R' else 'n')
                hi += 1
            else:
                self.kick(tt, 96 if ch == 'K' else 88, STICK_MAP[ch])
        self.six_stroke(t + 3.0, 1.0, T2, F1, 44, 114)
        self.kick(t + 3.0, 100, kind='a')
        # bar 24: motif in 32nds inside a travelling run, then orchestrated paradiddle-diddles
        t = 96.0
        orch = [CRASH1, SPLASH, F1, T1, F2]
        path = walk([SNARE, T1, T2, T3, F1], 16, 'wave', 2)
        it = []
        for s in range(16):
            if s in CLAVE:
                it.append((orch[CLAVE.index(s)], 110, 'a'))
            else:
                it.append((path[s], 52 + s * 1.2, 'n'))
        self.seq(t, 0.125, it)
        self.kick(t, 108, kind='a'); self.kick(t + 0.75, 88); self.kick(t + 1.5, 94)
        stick = "RLRRLL"
        pdd = []
        for i in range(12):
            ch = stick[i % 6]
            low = F1 if i < 6 else F2
            if i % 6 == 0:
                pdd.append((low, 106, 'a'))
            elif ch == 'R':
                pdd.append((low, 70, 'n'))
            else:
                pdd.append((T1 if i < 6 else T2, 66 + 2 * i, 'n'))
        self.seq(t + 2.0, 1 / 6.0, pdd, stick)
        self.kick(t + 2.0, 96); self.kick(t + 3.0, 100)
        self.hat(t + 1, 54); self.hat(t + 3, 56)
        # bar 25: 16th doubles travelling up and down, motif accents
        t = 100.0
        pr = walk([SNARE, T1, T2, T3, F1, F2, F1, T3], 16, 'down', 2)
        it = []
        for s in range(16):
            if s in CLAVE:
                it.append((pr[s], 108, 'a'))
            else:
                it.append((pr[s], 60 + 1.5 * s - (6 if s % 2 else 0), 'n'))
        self.seq(t, 0.25, it, "RRLL")
        for s in CLAVE:
            self.kick(t + s / 4.0, 94, kind='a')
        self.kick(t + 3.5, 80)
        self.hat(t + 1, 54); self.hat(t + 3, 56)
        # bar 26: subdivisions accelerate (16ths -> sextuplets -> 32nds) along a wave
        t = 104.0
        times = ([t + i * 0.25 for i in range(4)] + [t + 1 + i / 6.0 for i in range(6)]
                 + [t + 2 + i * 0.125 for i in range(16)])
        n = len(times)
        path = walk(KIT, n, 'wave')
        for i, tt in enumerate(times):
            acc = i in (0, 4, 10, 18)
            self.hit(tt, path[i], 72 + 36 * i / (n - 1.0) + (14 if acc else 0),
                     R if i % 2 == 0 else L, 'a' if acc else 'n')
        self.kick(t, 96); self.kick(t + 1, 90)
        for i in range(8):
            self.kick(t + 2 + i * 0.25, 76 + 3 * i, RF if i % 2 == 0 else LF)
        self.lean(104.0, 108.0, 0, -6)
        # bar 27: motif as unison hits with swelling 32nd ghosts between, then a breath
        t = 108.0
        uni = [(F1, T1), (F1, T2), (F2, T1), (F1, SNARE), (CHINA, SNARE)]
        for k, s in enumerate(CLAVE):
            rn, ln = uni[k]
            v = 100 + 5 * k
            tt = t + s / 4.0
            self.hit(tt, rn, v, R, 'a'); self.hit(tt, ln, v - 8, L, 'a')
            self.kick(tt, v, kind='a')
            if k < 4:
                m = 2 * (CLAVE[k + 1] - s) - 1
                for j in range(1, m + 1):
                    vv = 30 + 44 * j / float(m)
                    self.hit(tt + j * 0.125, SNARE, vv, R if j % 2 == 1 else L,
                             'g' if vv < 45 else 'n')

    def sec5(self):
        rng = self.rng
        casc = [0, 2, 3, 5, 7, 8, 10, 11, 13, 15]
        # feet: motif A on a wood-block pedal (left), tumbao-like bass drum (right)
        for b in range(28, 36):
            t = 4.0 * b
            clv = CLAVE if b < 35 else [0, 3, 6]
            for j, s in enumerate(clv):
                self.hit(t + s / 4.0, WB_H, 82 if j == 0 else 70, LF, 'n')
            for s in ([6, 12] if b % 2 == 0 else [6, 12, 15]):
                if b == 35 and s > 6:
                    continue
                self.kick(t + s / 4.0, 70 if s == 12 else 62)
        # bar 28
        t = 112.0
        self.hit(t, CRASH1, 108, R, 'a'); self.kick(t, 96, kind='a')
        for s in casc[1:]:
            self.hit(t + s / 4.0, BELL, 60 + (12 if s == 8 else 0) + rng.random() * 6, R, 'n')
        self.hit(t + 3.0, STICK, 62, L, 'n')
        # bar 29
        t = 116.0
        for s in casc:
            acc = s in (0, 8)
            self.hit(t + s / 4.0, BELL, 62 + (14 if acc else 0) + rng.random() * 6, R,
                     'a' if acc else 'n')
        for s, note, v in ((4, STICK, 58), (9, T3, 50), (11, F1, 58), (12, STICK, 66)):
            self.hit(t + s / 4.0, note, v, L, 'n')
        # bar 30
        t = 120.0
        for s in (0, 4, 6, 8, 12, 14):
            acc = s in (0, 8)
            self.hit(t + s / 4.0, COWBELL, (80 if acc else 60) + rng.random() * 5, R,
                     'a' if acc else 'n')
        for s, note, v in ((3, TIMB_H, 72), (7, TIMB_L, 44), (10, TIMB_L, 40),
                           (12, STICK, 64), (15, TIMB_H, 56)):
            self.hit(t + s / 4.0, note, v, L, 'n')
        # bar 31: ends with a little timbale roll (abanico)
        t = 124.0
        for s in (0, 4, 6, 8, 12):
            acc = s in (0, 8)
            self.hit(t + s / 4.0, COWBELL, (80 if acc else 60) + rng.random() * 5, R,
                     'a' if acc else 'n')
        for s, note, v in ((3, TIMB_H, 76), (7, TIMB_L, 48), (10, TIMB_L, 44)):
            self.hit(t + s / 4.0, note, v, L, 'n')
        for j in range(4):
            self.hit(t + 3.5 + j * 0.125, TIMB_H, 46 + 14 * j, R if j % 2 == 0 else L, 'n')
        # bar 32: hands interlock with the foot (they fill exactly the motif's gaps)
        t = 128.0
        self.hit(t, TIMB_H, 108, R, 'a')
        for s in range(16):
            if s in CLAVE:
                continue
            limb = R if s % 2 == 0 else L
            note = TIMB_H if limb == R else TIMB_L
            if s in (8, 14):
                self.hit(t + s / 4.0, note, 96, limb, 'a')
            else:
                self.hit(t + s / 4.0, note, 44 + rng.random() * 18, limb, 'n')
        # bar 33: hands join the foot on the motif, in flams; agogo pickup
        t = 132.0
        fl = {0: (TIMB_H, R), 3: (TIMB_L, L), 6: (TIMB_H, R), 10: (T3, R), 12: (F1, R)}
        for s in CLAVE:
            note, limb = fl[s]
            self.flam(t + s / 4.0, note, 108 if s == 12 else 100, limb)
        for s in (1, 5, 7, 9, 11):
            if rng.random() < 0.7:
                self.hit(t + s / 4.0, SNARE, 30 + rng.random() * 10, L, 'g')
        self.hit(t + 3.5, AGOGO_H, 84, R, 'n'); self.hit(t + 3.75, AGOGO_L, 80, L, 'n')
        # bar 34: timbale sextuplets swelling, then toms with the motif tail
        t = 136.0
        for i in range(12):
            limb = R if i % 2 == 0 else L
            acc = i % 6 == 0
            self.hit(t + i / 6.0, TIMB_H if limb == R else TIMB_L,
                     50 + 36 * i / 11.0 + (12 if acc else 0), limb, 'a' if acc else 'n')
        path = [T1, T1, T2, T2, T3, T3, F1, F1]
        for j, s in enumerate(range(8, 16)):
            acc = s in (10, 12)
            self.hit(t + s / 4.0, path[j], 80 + 3 * j + (18 if acc else 0),
                     R if s % 2 == 0 else L, 'a' if acc else 'n')
        # bar 35: build back up, timbale roll, triplet foreshadowing
        t = 140.0
        path = [SNARE, T1, T1, T2, T2, T3, T3, F1]
        for s in range(8):
            acc = s in (0, 3, 6)
            self.hit(t + s / 4.0, path[s], 64 + 4.5 * s + (10 if acc else 0),
                     R if s % 2 == 0 else L, 'a' if acc else 'n')
        for i in range(8):
            self.hit(t + 2 + i * 0.125, TIMB_H if i % 2 == 0 else TIMB_L, 50 + 7 * i,
                     R if i % 2 == 0 else L, 'n')
        six = [T1, T1, T2, T3, F1, F2]
        for j in range(6):
            self.hit(t + 3 + j / 6.0, six[j], 98 + 3 * j, R if j % 2 == 0 else L,
                     'a' if j in (0, 5) else 'n')
        self.hat(t + 3.0, 56)
        self.kick(t + 3.0, 96); self.kick(t + 3.5, 100)
        self.lean(112.0, 140.0, 6, 6)
        self.lean(140.0, 144.0, 4, -4)

    def sec6(self):
        rng = self.rng
        s6 = 1 / 6.0
        # bar 36: motif A in triplets, ghost triplets between
        t = 144.0
        orch = [CRASH1, T1, SNARE, F1, F2]
        for i in range(24):
            limb = R if i % 2 == 0 else L
            if i in TCLAVE:
                self.hit(t + i * s6, orch[TCLAVE.index(i)], 112 if i == 0 else 100, limb, 'a')
            elif rng.random() < 0.6:
                self.hit(t + i * s6, SNARE, 26 + rng.random() * 14, limb, 'g')
        self.kick(t, 108, kind='a'); self.kick(t + 8 * s6, 70); self.kick(t + 14 * s6, 90)
        for q in range(4):
            self.hat(t + q, 50)
        # bar 37: motif B (hand-hand-foot down the toms) + triplet motif answer
        t = 148.0
        drums = [SNARE, T1, T3, F1]
        for g in range(4):
            base = t + g * 3 * s6
            self.hit(base, drums[g], 108, R, 'a')
            self.hit(base + s6, drums[g], 82, L, 'n')
            self.kick(base + 2 * s6, 96)
        for i in range(12, 24):
            tt = t + i * s6
            limb = R if i % 2 == 0 else L
            if i == 14:
                self.hit(tt, F1, 108, limb, 'a'); self.kick(tt, 100, kind='a')
            elif i == 18:
                self.hit(tt, CRASH2, 114, limb, 'a'); self.kick(tt, 104, kind='a')
            elif i in (22, 23):
                self.hit(tt, [T1, T2][i - 22], 80, limb, 'n')
            elif rng.random() < 0.55:
                self.hit(tt, SNARE, 28 + rng.random() * 10, limb, 'g')
        for q in range(4):
            self.hat(t + q, 50)
        # bar 38: RLRK groups of four against the triplet pulse
        t = 152.0
        heads = [T1, T2, T3, F1, F2, SNARE]
        for i in range(24):
            g, pos = divmod(i, 4)
            tt = t + i * s6
            x = i / 23.0
            if pos == 3:
                self.kick(tt, 90 + 10 * x)
            elif pos == 0:
                self.hit(tt, heads[g], 100 + 12 * x, R, 'a')
            elif pos == 1:
                self.hit(tt, heads[g], 64 + 12 * x, L, 'n')
            else:
                self.hit(tt, heads[(g + 1) % 6], 70 + 12 * x, R, 'n')
        for q in range(4):
            self.hat(t + q, 50)
        # bar 39: motif B down, two groups up, one big hit and space
        t = 156.0
        dd = [T1, T2, T3, F1]
        for g in range(4):
            base = t + g * 3 * s6
            self.hit(base, dd[g], 106 + 2 * g, R, 'a')
            self.hit(base + s6, dd[g], 84, L, 'n')
            self.kick(base + 2 * s6, 98)
        for g, note in enumerate([F2, T2]):
            base = t + 2.0 + g * 3 * s6
            self.hit(base, note, 108, R, 'a')
            self.hit(base + s6, note, 86, L, 'n')
            self.kick(base + 2 * s6, 100)
        self.hit(t + 3.0, CRASH1, 118, R, 'a'); self.hit(t + 3.0, SNARE, 112, L, 'a')
        self.kick(t + 3.0, 112, kind='a')
        for q in range(3):
            self.hat(t + q, 50)
        self.lean(159.0, 160.0, 5, 8)
        # bar 40: triplet motif on cymbals over a triplet double-bass bed
        t = 160.0
        for i in range(24):
            self.kick(t + i * s6, 52 + 30 * i / 23.0 + (10 if i in TCLAVE else 0),
                      RF if i % 2 == 0 else LF)
        cy = [CRASH1, CRASH2, CHINA, CRASH2, CRASH1]
        for k, i in enumerate(TCLAVE):
            self.hit(t + i * s6, cy[k], 104 + 3 * k, R, 'a')
            self.hit(t + i * s6, SNARE, 98 + 3 * k, L, 'a')
        self.hit(t + 22 * s6, T1, 86, R, 'n'); self.hit(t + 23 * s6, T2, 92, L, 'n')
        # bar 41: RRLLK groups of five across the pulse
        t = 164.0
        pairs = [(SNARE, T1), (T1, T2), (T2, T3), (T3, F1)]
        for g in range(4):
            base = g * 5
            a, bn = pairs[g]
            x = g / 3.0
            self.hit(t + base * s6, a, 100 + 8 * x, R, 'a')
            self.hit(t + (base + 1) * s6, a, 72 + 8 * x, R, 'n')
            self.hit(t + (base + 2) * s6, bn, 84 + 8 * x, L, 'n')
            self.hit(t + (base + 3) * s6, bn, 76 + 8 * x, L, 'n')
            self.kick(t + (base + 4) * s6, 94 + 6 * x)
        for j, note in enumerate([F1, F1, F2, F2]):
            self.hit(t + (20 + j) * s6, note, 96 + 5 * j, R if j % 2 == 0 else L, 'n')
        for q in range(4):
            self.hat(t + q, 48)
        # bar 42: continuous sextuplets on a wave, triplet motif accents with the foot
        t = 168.0
        path = walk(KIT, 24, 'wave')
        for i in range(24):
            limb = R if i % 2 == 0 else L
            if i in TCLAVE:
                self.hit(t + i * s6, CRASH1 if i == 0 else path[i], 110, limb, 'a')
                self.kick(t + i * s6, 100, kind='a')
            else:
                self.hit(t + i * s6, path[i], 58 + 26 * i / 23.0, limb, 'n')
        self.hat(t + 1, 52); self.hat(t + 3, 56)
        # bar 43: RLKK in sextuplets (four over three), six-stroke into the build
        t = 172.0
        hands = [T1, SNARE, T2, T1, T3, T2, F1, T3, F2, F1]
        hi = 0
        for i in range(18):
            ch = "RLKk"[i % 4]
            tt = t + i * s6
            x = i / 17.0
            if ch in 'RL':
                self.hit(tt, hands[hi], (100 if ch == 'R' else 84) + 12 * x, STICK_MAP[ch],
                         'a' if ch == 'R' else 'n')
                hi += 1
            else:
                self.kick(tt, 86 + 14 * x, STICK_MAP[ch])
        self.six_stroke(t + 3.0, 1.0, T1, F2, 50, 118)
        self.kick(t + 3.0, 104, kind='a'); self.kick(t + 3.5, 100)
        self.lean(172.0, 176.0, 0, -7)

    def sec7(self):
        rng = self.rng
        acc = {44: (0, 6, 12), 45: (4, 8), 46: (0, 4, 8, 12), 47: tuple(CLAVE),
               48: tuple(CLAVE), 49: tuple(CLAVE), 50: (0, 3, 6, 8, 12), 51: (0, 4, 8, 12)}
        for b in range(44, 52):
            x0 = (b - 44) / 8.0
            x1 = (b - 43) / 8.0
            self.double_bass(4.0 * b, 16, 58 + 40 * x0, 58 + 40 * x1, acc[b])
        # bars 44-45: augmented motif, hands sparse over busy feet
        t = 176.0
        aug = [0.0, 1.5, 3.0, 5.0, 6.0]
        cyms = [CRASH1, CHINA, CRASH2, CHINA, CRASH1]
        for k, a in enumerate(aug):
            self.hit(t + a, cyms[k], 108 + 3 * k, R, 'a')
            self.hit(t + a, SNARE, 100 + 3 * k, L, 'a')
        for a in (0.75, 2.25, 2.5, 4.0, 4.5, 5.5):
            self.hit(t + a, SNARE, 30 + rng.random() * 10, L, 'g')
        for j, note in enumerate([T1, T2, T3, F1]):
            self.hit(t + 7.0 + j * 0.25, note, 84 + 8 * j, R if j % 2 == 0 else L, 'n')
        # bar 46: sextuplets over the 16th feet (three against two)
        t = 184.0
        shapes = [walk(KIT, 6, 'down'), walk([T1, T2, T3, F1], 6, 'down'),
                  walk(KIT, 6, 'up'), walk([T1, T3, F1, F2], 6, 'down')]
        for q in range(4):
            for j in range(6):
                i = q * 6 + j
                self.hit(t + i / 6.0, shapes[q][j], (104 if j == 0 else 70 + 4 * j) + 2 * q,
                         R if i % 2 == 0 else L, 'a' if j == 0 else 'n')
        # bar 47: 16ths locked with the feet, motif accents on cymbals
        t = 188.0
        cy = {0: CRASH1, 3: CRASH2, 6: CHINA, 10: CRASH1, 12: CRASH2}
        path = walk([SNARE, T1, T2, SNARE, T3, F1], 16, 'down', 2)
        for s in range(16):
            limb = R if s % 2 == 0 else L
            if s in cy:
                self.hit(t + s / 4.0, cy[s], 112, limb, 'a')
            else:
                self.hit(t + s / 4.0, path[s], 48 + 30 * s / 15.0, limb, 'g' if s < 5 else 'n')
        # bar 48: 32nd doubles, snare then toms, motif accents
        t = 192.0
        cl = [2 * s for s in CLAVE]
        acc_notes = [T1, T2, F1, T3, F2]
        for i in range(32):
            limb = R if (i % 4) < 2 else L
            note = SNARE if i < 16 else [T1, T2, T3, F1][(i - 16) // 4]
            v = 50 + 56 * i / 31.0 - (7 if i % 2 else 0)
            kind = 'n'
            if i in cl:
                note = acc_notes[cl.index(i)]
                v += 18
                kind = 'a'
            self.hit(t + i * 0.125, note, v, limb, kind)
        # bar 49: hands drop out, the feet finish the motif
        t = 196.0
        for s in (0, 3, 6, 12):
            self.hit(t + s / 4.0, CRASH2 if s == 3 else CRASH1, 110, R, 'a')
            self.hit(t + s / 4.0, SNARE, 100, L, 'a')
        for j, note in enumerate([T1, T2, F1]):
            self.hit(t + (13 + j) / 4.0, note, 90 + 8 * j, L if j % 2 == 0 else R, 'n')
        # bar 50: motif in 32nds, sextuplet descent
        t = 200.0
        orch = [CRASH1, T1, F1, T2, CRASH2]
        path = walk([SNARE, T1, T2], 16, 'wave')
        it = []
        for s in range(16):
            if s in CLAVE:
                it.append((orch[CLAVE.index(s)], 112, 'a'))
            else:
                it.append((path[s], 50 + 2 * s, 'n'))
        self.seq(t, 0.125, it)
        run = walk(TOMS, 12, 'down', 2)
        for j in range(12):
            a = j % 6 == 0
            self.hit(t + 2.0 + j / 6.0, run[j], 84 + 2.4 * j + (10 if a else 0),
                     R if j % 2 == 0 else L, 'a' if a else 'n')
        # bar 51: a full bar of 32nd singles swelling down the kit
        t = 204.0
        path = walk(KIT, 24, 'wave', 2)
        for i in range(32):
            if i < 24:
                note = path[i]
            else:
                note = F2 if i % 2 == 0 else F1
            v = 64 + 56 * (i / 31.0) ** 1.3 + (10 if i % 8 == 0 else 0)
            self.hit(t + i * 0.125, note, v, R if i % 2 == 0 else L, 'a' if i % 8 == 0 else 'n')
        self.lean(204.0, 208.0, 0, -7)

    def sec8(self):
        # feet
        self.double_bass(208.0, 16, 88, 96, tuple(CLAVE))
        self.double_bass(212.0, 16, 92, 100, (2, 5, 8, 12, 14))
        self.double_bass(216.0, 32, 72, 116, tuple(16 + s for s in CLAVE))
        # bars 52-53: the motif in full, then displaced by an eighth
        self.motif_big(208.0, CLAVE, [CRASH1, CRASH2, CHINA, CRASH1, CRASH2], 102)
        self.motif_big(212.0, [2, 5, 8, 12, 14], [CHINA, CRASH1, CRASH2, CHINA, CRASH1], 108)
        # bars 54-55: single-stroke roll swell, snare into the toms
        t = 216.0
        path55 = walk(KIT, 32, 'wave', 2)
        cl = [32 + 2 * s for s in CLAVE]
        for i in range(64):
            v = 58 + 66 * (i / 63.0) ** 1.4
            note = SNARE if i < 32 else path55[i - 32]
            kind = 'n'
            if i in cl:
                v += 12
                kind = 'a'
            self.hit(t + i * 0.125, note, v, R if i % 2 == 0 else L, kind)
        self.lean(216.0, 224.0, 0, -6)
        # bars 56-57: augmented motif, rolls swelling into every hit
        t = 224.0
        aug = [0.0, 1.5, 3.0, 5.0, 6.0]
        hits = [(CRASH1, CRASH2), (CHINA, SNARE), (CRASH1, SNARE), (CRASH2, SNARE), (CRASH1, CRASH2)]
        rolls = [[SNARE, T1, T2, T3], [T1, T2, T3, F1], KIT, [SNARE]]
        self.double_bass(t, 25, 78, 104, (0, 6, 12, 20, 24))
        for k, a in enumerate(aug):
            rn, ln = hits[k]
            self.hit(t + a, rn, 120, R, 'a')
            self.hit(t + a, ln, 114, L, 'a')
            if k < 4:
                start = a + 0.25
                n = int(round((aug[k + 1] - start) / 0.125))
                notes = walk(rolls[k], n, 'down')
                for i in range(n):
                    hand = L if (n - 1 - i) % 2 == 0 else R
                    v = 42 + 62 * (i / max(1.0, n - 1.0)) ** 1.3
                    self.hit(t + start + i * 0.125, notes[i], v, hand, 'g' if v < 46 else 'n')
        # motif B returns to carry the last phrase
        rl = [(T1, T1), (T3, T3), (F1, F2)]
        for g in range(3):
            base = t + 6.5 + g * 0.5
            self.hit(base, rl[g][0], 108 + 4 * g, R, 'a')
            self.hit(base + 1 / 6.0, rl[g][1], 96 + 4 * g, L, 'n')
            self.kick(base + 2 / 6.0, 104 + 5 * g)
        # the final hit
        T = FINAL_BAR * 4.0
        self.hit(T, CRASH1, 127, R, 'x')
        self.hit(T, CRASH2, 127, L, 'x')
        self.kick(T, 127, kind='x')
        self.lean(231.4, 232.5, 4, 12)

    def compose(self):
        self.sec1(); self.sec2(); self.sec3(); self.sec4()
        self.sec5(); self.sec6(); self.sec7(); self.sec8()


def lean_ms(leans, t):
    v = 0.0
    for b0, b1, m0, m1 in leans:
        if b0 <= t < b1:
            v += m0 + (m1 - m0) * (t - b0) / (b1 - b0)
    return v


def swing_shift(swings, t):
    q = t * 4.0
    if abs(q - round(q)) > 1e-6 or int(round(q)) % 2 == 0:
        return 0.0
    for b0, b1, amt in swings:
        if b0 <= t < b1:
            return amt * 0.25
    return 0.0


def render(d):
    us, cum = build_tempo()
    tm = TempoMap(us, cum)
    rng = random.Random(SEED + 1)

    evs = sorted(d.ev, key=lambda e: (e[0], e[3], e[1], e[2], e[4]))
    ideal = []
    for e in evs:
        s = tm.b2s(e[0] + swing_shift(d.swings, e[0]))
        if e[4] == 'f':
            s -= 0.024
        ideal.append(s)

    # distance to the neighbouring stroke of the same limb: fast passages stay tight
    ioi = [1.0] * len(evs)
    for limb in (R, L, RF, LF):
        idxs = sorted([i for i, e in enumerate(evs) if e[3] == limb], key=lambda i: (ideal[i], i))
        for j, i in enumerate(idxs):
            dmin = 1.0
            if j > 0:
                dmin = min(dmin, ideal[i] - ideal[idxs[j - 1]])
            if j + 1 < len(idxs):
                dmin = min(dmin, ideal[idxs[j + 1]] - ideal[i])
            ioi[i] = max(0.0, dmin)

    hits = []
    drift = 0.0
    for i, e in enumerate(evs):
        t, note, vel, limb, kind = e
        drift = 0.8 * drift + rng.gauss(0.0, 0.0013)
        tight = min(1.0, ioi[i] / 0.15)
        sig = SIG[kind] * tight * (0.75 if limb in (RF, LF) else 1.0)
        off = (drift + BIAS[kind]) * tight + rng.gauss(0.0, sig) + lean_ms(d.leans, t) / 1000.0
        hits.append({'s': ideal[i] + off, 'ideal': ideal[i], 'note': note, 'vel': vel,
                     'limb': limb, 'kind': kind})

    # playability: one stroke per limb at a time, with a minimum re-strike time
    kept_all = []
    dropped = 0
    for limb in (R, L, RF, LF):
        items = sorted([h for h in hits if h['limb'] == limb], key=lambda h: (h['s'], h['note']))
        kept = []
        mg = MIN_GAP[limb]
        for h in items:
            cur = h
            while cur is not None:
                if not kept:
                    kept.append(cur)
                    cur = None
                    continue
                p = kept[-1]
                if cur['s'] - p['s'] >= mg:
                    kept.append(cur)
                    cur = None
                elif cur['ideal'] - p['ideal'] >= mg - 1e-9:
                    cur['s'] = p['s'] + mg
                    kept.append(cur)
                    cur = None
                else:
                    dropped += 1
                    if (PRI[cur['kind']], cur['vel']) > (PRI[p['kind']], p['vel']):
                        kept.pop()
                    else:
                        cur = None
        kept_all.extend(kept)

    notes_out = []
    for h in kept_all:
        on = LEAD + max(0, int(round(tm.s2b(h['s']) * PPQ)))
        if h['kind'] == 'x':
            dur = 2.8
        elif h['note'] in CYMS:
            dur = 0.5
        else:
            dur = 0.09
        off = LEAD + max(0, int(round(tm.s2b(h['s'] + dur) * PPQ)))
        notes_out.append([on, max(off, on + 1), h['note'], h['vel']])

    by_note = {}
    for n in sorted(notes_out, key=lambda x: (x[2], x[0], -x[3], x[1])):
        by_note.setdefault(n[2], []).append(n)
    final = []
    for note in sorted(by_note):
        merged = []
        for n in by_note[note]:
            if merged and merged[-1][0] == n[0]:
                merged[-1][3] = max(merged[-1][3], n[3])
                merged[-1][1] = max(merged[-1][1], n[1])
                continue
            merged.append(n)
        for a, b in zip(merged, merged[1:]):
            a[1] = min(a[1], b[0])
        for a in merged:
            if a[1] <= a[0]:
                a[1] = a[0] + 1
        final.extend(merged)

    msgs = []
    for on, off, note, vel in final:
        msgs.append((on, 1, note, vel))
        msgs.append((off, 0, note, 0))
    msgs.sort()

    end_tick = LEAD + int(round(tm.s2b(tm.b2s(FINAL_BAR * 4.0) + RING_SEC) * PPQ))
    if msgs:
        end_tick = max(end_tick, msgs[-1][0] + 1)

    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    meta = mido.MidiTrack()
    mid.tracks.append(meta)
    meta.append(mido.MetaMessage('track_name', name='Tempo', time=0))
    meta.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                 clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    meta.append(mido.MetaMessage('set_tempo', tempo=us[0], time=0))
    last = 0
    current = us[0]
    for k, u in enumerate(us):
        tick = LEAD + int(round(k * SEG * PPQ))
        if tick >= end_tick:
            break
        if u == current:
            continue
        meta.append(mido.MetaMessage('set_tempo', tempo=u, time=tick - last))
        last = tick
        current = u
    meta.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - last)))

    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.Message('program_change', channel=CH, program=0, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=7, value=110, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=10, value=64, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=91, value=40, time=0))
    last = 0
    for tick, kind, note, vel in msgs:
        if kind == 1:
            tr.append(mido.Message('note_on', channel=CH, note=note, velocity=vel, time=tick - last))
        else:
            tr.append(mido.Message('note_off', channel=CH, note=note, velocity=0, time=tick - last))
        last = tick
    tr.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - last)))
    return mid, len(final), dropped


def main():
    d = Drummer()
    d.compose()
    mid, count, dropped = render(d)
    mid.save('solo.mid')
    print("wrote solo.mid: %d strokes, %.1f s (%d unplayable strokes removed)"
          % (count, mid.length, dropped))


if __name__ == '__main__':
    main()
