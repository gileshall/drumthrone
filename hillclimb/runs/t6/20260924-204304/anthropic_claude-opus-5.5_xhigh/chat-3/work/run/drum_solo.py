#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a two-minute drum solo for a General MIDI
synthesizer. Every note is on MIDI channel 10.

Form (4/4, roughly 110-128 bpm on a tempo map that follows the playing):
   0-7   Statement   Motif A, a 3+3+2 accent cell, is stated on snare and
                     toms, answered, displaced, and pushed around the kit.
   8-15  Tom song    Motif C, a triplet-feel tom melody, is sung, answered
                     higher, ornamented, fragmented, doubled and inverted.
  16-23  Hands       Singles, paradiddles, hemiolas, doubles and 32nd runs
                     that travel the kit; motif A shrinks into 32nds.
  24-31  Interlude   Quiet colour: bell, cowbell, side stick, woodblocks and
                     hi-hat barks built from motif A, then a long roll swells.
  32-41  Triplets    Linear RLK triplets, double-bass groupings, six-stroke
                     rolls and flam accents; motif A is rebuilt from triplets.
  42-51  Recap       Motifs A and C return big: displaced, in fives and threes.
  52-57  Finale      32nd circles, paradiddle-diddles, motif A augmented, a
                     held-back last roll, and the final hit.

Every note belongs to a limb (R, L, K = right foot, H = left foot). A cleanup
pass enforces that each limb plays one stroke at a time with realistic spacing.
The output is deterministic because all randomness comes from fixed seeds.
"""
import bisect
import math
import random

import mido

PPQ = 960
SEED = 1969
CH = 9                      # MIDI channel 10 (zero-based 9)
FINAL_BAR = 57              # the final hit lands on this bar's downbeat
TARGET_FINAL_SEC = 117.3    # time of the final hit
TOTAL_SEC = 120.0           # length of the file
SEG = 0.5                   # tempo-map resolution in beats
LEAD = 0.03                 # small lead-in so early notes never go negative

NOTE = {
    'k': 36, 'S': 38, 'r': 37,
    '1': 50, '2': 48, '3': 47, '4': 45, '5': 43, '6': 41,
    'p': 44, 'h': 42, 'o': 46,
    'C': 49, 'D': 57, 'R': 51, 'B': 53, 'X': 52, 'Z': 55,
    'Q': 56, 'W': 76, 'w': 77, 'T': 65, 't': 66,
}
TOM_NOTES = {41, 43, 45, 47, 48, 50, 65, 66}
LEVELS = {'g': 30, 'q': 56, 'n': 80, '!': 106, '^': 120}
PRIO = {'grace': 0, 'g': 1, 'q': 2, 'n': 2, '!': 3, '^': 4, 'end': 9}
HANDS = ('R', 'L')
FEET = ('K', 'H')
LIMB_ORDER = {'R': 0, 'L': 1, 'K': 2, 'H': 3}
CAP = {49: 1.9, 57: 1.9, 52: 1.6, 55: 1.1, 51: 1.2, 53: 0.9, 46: 0.5,
       76: 0.2, 77: 0.2, 56: 0.3}
VCLAMP = {'grace': (12, 70), 'g': (8, 56), 'q': (28, 92), 'n': (40, 116),
          '!': (80, 127), '^': (96, 127), 'end': (127, 127)}

TEMPO_KEYS = [
    (0.0, 110.0), (1.0, 111.0), (3.8, 114.5), (4.0, 113.5), (7.5, 117.0),
    (8.0, 115.0), (11.0, 116.0), (12.0, 117.5), (14.0, 117.0), (15.7, 120.0),
    (16.0, 118.5), (19.6, 121.5), (20.0, 120.5), (23.7, 124.0), (24.3, 116.5),
    (26.0, 114.0), (29.0, 114.5), (30.0, 115.0), (31.9, 120.5), (32.2, 119.5),
    (35.0, 121.0), (37.0, 121.5), (40.0, 123.5), (41.9, 126.0), (42.2, 124.0),
    (46.0, 125.5), (48.6, 127.5), (49.2, 124.5), (50.0, 126.5), (52.0, 128.5),
    (53.8, 128.0), (54.5, 125.0), (55.5, 119.0), (56.0, 113.0), (56.5, 104.0),
    (57.0, 94.0), (61.0, 94.0),
]

# Motif C: (slot, contour index, dynamic) over 12 slots.
C_EVENTS = ((0, 0, '!'), (2, 1, 'n'), (3, 0, '!'), (5, 1, 'n'),
            (6, 2, '!'), (7, 1, 'q'), (8, 0, 'n'), (9, 3, '^'))
C_STICK = ('R', 'L', 'R', 'L', 'L', 'R', 'R', 'R')


def T(bar, beat=0.0):
    return 4.0 * bar + beat


class Hit:
    __slots__ = ('beat', 'note', 'vel', 'limb', 'kind', 'dt', 'tag', 'parent',
                 'sd', 'sec', 'on', 'off')

    def __init__(self, beat, note, vel, limb, kind, dt, tag, parent=None, sd=None):
        self.beat = beat
        self.note = note
        self.vel = vel
        self.limb = limb
        self.kind = kind
        self.dt = dt
        self.tag = tag
        self.parent = parent
        self.sd = sd
        self.sec = 0.0
        self.on = 0
        self.off = 0

    @property
    def prio(self):
        return PRIO[self.kind] - (0.5 if self.tag == 'ost' else 0.0)


class Solo:
    def __init__(self):
        self.rng = random.Random(SEED)
        self.hits = []

    def add(self, beat, code, vel, limb, kind='n', dt=0.0, tag='', sd=None):
        note = NOTE[code] if isinstance(code, str) else code
        h = Hit(beat, note, float(vel), limb, kind, dt, tag, None, sd)
        self.hits.append(h)
        return h

    def grace(self, main, style='flam'):
        other = 'L' if main.limb == 'R' else 'R'
        if style == 'flam':
            off = -(0.022 + 0.012 * self.rng.random())
            self.hits.append(Hit(main.beat, main.note, 16 + 0.30 * main.vel,
                                 other, 'grace', off, main.tag, main))
        else:
            off = -(0.056 + 0.010 * self.rng.random())
            gap = 0.024 + 0.005 * self.rng.random()
            for j, o in enumerate((off, off + gap)):
                self.hits.append(Hit(main.beat, main.note,
                                     14 + (0.24 + 0.05 * j) * main.vel,
                                     other, 'grace', o, main.tag, main))

    def pat(self, start, div, lanes, vs=1.0, cresc=None, tag='pat'):
        parsed = {}
        length = 1
        for limb, text in lanes.items():
            toks = [t for t in text.split() if t != '|']
            parsed[limb] = toks
            length = max(length, len(toks))
        span = length / div
        for limb, toks in parsed.items():
            for i, tok in enumerate(toks):
                if tok == '.':
                    continue
                code, mods = tok[0], tok[1:]
                kind = 'n'
                for c in mods:
                    if c in LEVELS:
                        kind = c
                vel = LEVELS[kind] * (1.0 if kind == 'g' else vs)
                pos = i / div
                if cresc:
                    a, b = cresc
                    vel += (a + (b - a) * pos / span) * (0.35 if kind == 'g' else 1.0)
                h = self.add(start + pos, code, vel, limb, kind, 0.0, tag)
                if '~' in mods:
                    self.grace(h, 'flam')
                elif '%' in mods:
                    self.grace(h, 'drag')

    def feet(self, bar0, bar1, div, kick=(), hat=(), kv=82, hv=52):
        for bar in range(bar0, bar1):
            for item in kick:
                sl, v = item if isinstance(item, tuple) else (item, kv)
                self.add(T(bar) + sl / div, 'k', v, 'K', 'n', 0.0, 'ost')
            for sl in hat:
                self.add(T(bar) + sl / div, 'p', hv + (5 if sl == 0 else 0),
                         'H', 'n', 0.0, 'ost')

    def run(self, start, unit, path, sticking='RL', v=(70, 90), acc=(), av=None,
            kicks=(), kv=94, flams=(), curve=1.0, rush=0.008, tag='run'):
        n = len(path)
        if av is None:
            av = (min(127, v[0] + 30), min(127, v[1] + 20))
        sd = 0.0024 if unit <= 0.13 else (0.0033 if unit <= 0.17 else None)
        prev_limb = None
        for i, code in enumerate(path):
            st = sticking[i % len(sticking)]
            if code == '.' or st == '.':
                prev_limb = None
                continue
            shape = (i / (n - 1)) ** curve if n > 1 else 1.0
            limb = st.upper()
            dt = -rush * shape
            if limb in FEET:
                note = code if code in ('k', 'p') else 'k'
                vel = (kv + 10 * shape) if st.isupper() else (kv - 24)
                self.add(start + i * unit, note, vel, limb, 'n', dt, tag, sd)
            else:
                if i in acc:
                    vel = av[0] + (av[1] - av[0]) * shape
                    kind = '^' if vel >= 116 else '!'
                else:
                    vel = v[0] + (v[1] - v[0]) * shape
                    if st.islower():
                        vel *= 0.55
                    if prev_limb == limb:
                        vel -= 4
                    kind = 'g' if vel < 46 else ('q' if vel < 68 else 'n')
                h = self.add(start + i * unit, code, vel, limb, kind, dt, tag, sd)
                if i in flams:
                    self.grace(h, 'flam')
            if i in kicks:
                self.add(start + i * unit, 'k', kv + 6 + 8 * shape, 'K', 'n', dt, tag, sd)
            prev_limb = limb

    def roll(self, start, beats, unit, codes, v0, v1, curve=1.5, lead='R', acc=None,
             kicks=(), kv=(60, 90), rush=0.004, tag='roll'):
        n = int(round(beats / unit))
        other = 'L' if lead == 'R' else 'R'
        stick = (lead, lead, other, other)
        acc = acc or {}
        for i in range(n):
            frac = i / max(1, n - 1)
            shape = frac ** curve
            code = codes[min(len(codes) - 1, int(i * len(codes) / n))]
            vel = v0 + (v1 - v0) * shape - (4 if i % 2 else 0)
            kind = 'g' if vel < 46 else ('q' if vel < 68 else 'n')
            if i in acc:
                code = acc[i]
                vel = max(vel + 24, 100)
                kind = '^' if vel >= 116 else '!'
            self.add(start + i * unit, code, vel, stick[i % 4], kind,
                     -rush * shape, tag, 0.0022)
            if i in kicks:
                self.add(start + i * unit, 'k', kv[0] + (kv[1] - kv[0]) * shape,
                         'K', 'n', -rush * shape, tag)

    def cellA(self, start, unit, acc='S25', fill='ghost', lead='R', flams=(), kicks=(),
              av=(106, 102, 112), gv=30, fnote='S', tag='A'):
        lh = 'L' if lead == 'R' else 'R'
        sd = 0.0026 if unit <= 0.13 else None
        for j, sl in enumerate((0, 3, 6)):
            b = start + sl * unit
            h = self.add(b, acc[j], av[j], lead, '^' if av[j] >= 116 else '!', 0.0, tag, sd)
            if j in flams:
                self.grace(h, 'flam')
            if j in kicks:
                self.add(b, 'k', 100, 'K', 'n', 0.0, tag)
        if fill == 'ghost':
            for sl in (1, 2, 4, 5, 7):
                self.add(start + sl * unit, fnote, gv + (5 if sl in (2, 5) else 0),
                         lh, 'g', 0.0, tag, sd)
        elif fill == 'lin':
            for sl in (1, 4):
                self.add(start + sl * unit, fnote, gv + 4, lh, 'g', 0.0, tag, sd)
            for sl in (2, 5, 7):
                self.add(start + sl * unit, 'k', 76 + 2 * sl, 'K', 'n', 0.0, tag)
        elif fill == 'taps':
            for sl in (1, 2, 4, 5, 7):
                self.add(start + sl * unit, fnote, 50 + 3 * sl, lh, 'q', 0.0, tag, sd)

    def cellC(self, start, unit, toms='5326', ghosts=(1, 4, 10, 11), flams=(), drags=(),
              kicks=(), crash=None, stick=None, ghost_hand='L', vs=1.0, gv=28, tag='C'):
        fast = unit < 0.3
        sd = 0.003 if fast else None
        for j, (sl, idx, dyn) in enumerate(C_EVENTS):
            if fast:
                limb = 'R' if sl % 2 == 0 else 'L'
            else:
                limb = (stick or C_STICK)[j]
            h = self.add(start + sl * unit, toms[idx], LEVELS[dyn] * vs, limb, dyn, 0.0, tag, sd)
            if j in flams:
                self.grace(h, 'flam')
            elif j in drags:
                self.grace(h, 'drag')
            if j in kicks:
                self.add(start + sl * unit, 'k', 98, 'K', 'n', 0.0, tag)
        if crash:
            self.add(start, crash, 118, 'L', '^', 0.0, tag)
        for sl in ghosts:
            limb = ('R' if sl % 2 == 0 else 'L') if fast else ghost_hand
            self.add(start + sl * unit, 'S', gv + (4 if sl >= 10 else 0), limb, 'g', 0.0, tag, sd)


# ---------------------------------------------------------------- sections
def section_statement(s):
    s.feet(0, 8, 4, hat=(4, 12), hv=50)
    # 0: motif A plainly, then answered by kick and snare
    s.cellA(T(0), 0.25, acc='S25', fill='ghost', av=(102, 98, 110))
    s.pat(T(0, 2), 4, {
        'R': ". . S! . | . . 5 .",
        'L': ". . . Sg | Sg . . Sg",
        'K': "k . . . | k . . .",
    })
    # 1: the answer, cell displaced by an eighth and moved up the toms
    s.pat(T(1), 4, {
        'R': ". . 1! . | . 2! . . | 4! . S!~ . | 5! . . Sq",
        'L': "Sg . . Sg | Sg . Sg Sg | . Sg . . | . Sg Sq .",
        'K': "k . . . | . . . . | k . . . | k . . .",
    })
    # 2: flammed, linear with the kick
    s.cellA(T(2), 0.25, acc='S34', fill='lin', flams=(0,), av=(110, 100, 106))
    s.pat(T(2, 2), 4, {
        'R': "6^ . . . | . 5 . 5q",
        'L': ". Sg . S! | . . Sg .",
        'K': "k . . . | k . . .",
    })
    # 3: on the toms, then a run down into the crash
    s.cellA(T(3), 0.25, acc='124', fill='ghost', av=(98, 104, 110))
    s.run(T(3, 2), 0.25, '22445566', 'RL', v=(76, 104), kicks=(7,), rush=0.010)
    # 4: displaced by two sixteenths
    s.pat(T(4), 4, {
        'R': "D^ . S! . | . 2! . . | S!~ . . . | 5! . . .",
        'L': ". . . Sg | Sg . Sg Sg | . Sg . Sg | . Sg . S",
        'K': "k . . . | . . . k | . . k . | k . . .",
    })
    # 5: two cells back to back, denser
    s.cellA(T(5), 0.25, acc='S24', fill='ghost', kicks=(0,), av=(108, 102, 106), gv=32)
    s.cellA(T(5, 2), 0.25, acc='5S1', fill='lin', kicks=(0,), av=(110, 106, 114), gv=34)
    # 6: space
    s.pat(T(6), 4, {
        'R': "C^ . . . | . . S!~ . | . . . . | 5! . . .",
        'L': ". . Sg . | Sg . . Sg | . Sg . Sg | . Sg Sg Sg",
        'K': "k . . . | . . . . | . . k . | k . . .",
    }, cresc=(0, 10))
    # 7: fill
    s.run(T(7), 0.25, 'SSSSSSSS', 'RL', v=(50, 76), acc=(0, 3, 6), av=(90, 104), rush=0.004)
    s.run(T(7, 2), 1 / 6, '112233445566', 'LR', v=(84, 112), kicks=(0, 6), rush=0.010)


def section_tom_song(s):
    s.feet(8, 15, 3, kick=((0, 88), (6, 74)), hat=(3, 9), hv=52)
    s.feet(15, 16, 3, hat=(3, 9), hv=54)
    s.cellC(T(8), 1 / 3, toms='5326', crash='C', kicks=(0,))
    s.cellC(T(9), 1 / 3, toms='4215', ghosts=(1, 4, 10))
    s.add(T(9, 11 / 3), 'k', 70, 'K')
    s.cellC(T(10), 1 / 3, toms='5326', drags=(0, 4), gv=32)
    s.pat(T(11), 3, {
        'R': "5! . . 5! . . 4! . . . . .",
        'L': ". Sg 3 . Sg 3 . Sg 2 . . .",
    })
    s.run(T(11, 3), 1 / 6, '223355', 'RL', v=(78, 100), acc=(0,), av=(100, 100), kicks=(3,))
    s.cellC(T(12), 1 / 6, toms='5326', ghosts=(1, 4, 10, 11))
    s.cellC(T(12, 2), 1 / 6, toms='4215', ghosts=(1, 4, 10, 11), kicks=(7,))
    s.cellC(T(13), 1 / 3, toms='2451', stick=('L', 'R', 'L', 'R', 'R', 'L', 'L', 'L'),
            ghost_hand='R', ghosts=(1, 4))
    s.pat(T(13, 3), 3, {'R': "Z! Sg Sg", 'K': "k . ."})
    s.cellC(T(14), 1 / 3, toms='5326', flams=(2,), kicks=(0, 2, 4, 7), gv=30)
    s.run(T(15), 1 / 6, '112233445566554433', 'LR', v=(70, 102), acc=(0, 6, 12),
          av=(100, 112), kicks=(0, 6, 12), rush=0.008)
    s.run(T(15, 3), 1 / 6, '5Sk6Sk', 'RLK', v=(98, 110), acc=(0, 3), av=(112, 118), kv=98)


def section_hands(s):
    s.feet(16, 24, 4, hat=(0, 4, 8, 12), hv=48)
    s.add(T(16), 'C', 118, 'L', '^')
    s.run(T(16), 0.25, '5SS1SS4S5SS2SS6S', 'RL', v=(50, 64), acc=(0, 3, 6, 8, 11, 14),
          av=(104, 112), kicks=(0, 6, 8, 14), rush=0.004)
    s.run(T(17), 0.25, '5SSS1SSS4SSS2SSS', 'RLRRLRLL', v=(46, 60), acc=(0, 4, 8, 12),
          av=(100, 112), kicks=(0, 8), rush=0.004)
    s.run(T(18), 0.25, '4SS1SS5SS2SS6SSS', 'RL', v=(52, 72), acc=(0, 3, 6, 9, 12),
          av=(102, 116), kicks=(0, 6, 12), rush=0.006)
    s.run(T(19), 1 / 6, 'SS11SS223322443355446655', 'RRLL', v=(58, 90),
          acc=(0, 4, 8, 12, 16, 20), av=(96, 116), kicks=(0, 6, 12, 18), rush=0.008)
    s.run(T(20), 0.25, 'CSk52kZSk41kCSkk', 'RLKRLKRLKRLKRLKK', v=(74, 92),
          acc=(0, 3, 6, 9, 12), av=(108, 118), kv=94, rush=0.004)
    s.run(T(21), 0.125, 'S' * 16, 'RL', v=(38, 76), acc=(0, 3, 6, 8, 11, 14),
          av=(80, 104), rush=0.005)
    s.run(T(21, 2), 0.125, '1111222244445555', 'RL', v=(84, 108), acc=(0, 4, 8, 12),
          av=(106, 118), kicks=(0, 8), rush=0.008)
    s.run(T(22), 0.125, '6666555544442222', 'RRLL', v=(72, 100), acc=(0, 4, 8, 12),
          av=(100, 114), kicks=(0, 8), rush=0.006)
    s.pat(T(22, 2), 4, {
        'R': "C^ . . . | . . S!~ .",
        'L': ". . Sg . | Sg . . Sg",
        'K': "k . . . | . . . k",
    })
    s.cellA(T(23, 0), 0.125, acc='S12', fill='ghost', gv=42, kicks=(0,), av=(100, 104, 108))
    s.cellA(T(23, 1), 0.125, acc='234', fill='ghost', gv=46, kicks=(0,), av=(104, 108, 112))
    s.cellA(T(23, 2), 0.125, acc='456', fill='ghost', gv=50, kicks=(0,), av=(108, 112, 118))
    s.pat(T(23, 3), 4, {'R': "5!~ . 6^~ .", 'L': ". S . Sq", 'K': "k . k ."})


def section_interlude(s):
    s.feet(24, 28, 4, kick=((6, 64), (12, 70)), hat=(4, 12), hv=50)
    s.feet(30, 32, 4, hat=(4, 12), hv=52)
    s.pat(T(24), 4, {
        'R': "C^ . Bq . | B Bq . Bq | . Bq . Bq | B . Bq .",
        'L': "r . . Sg | . . r . | . Sg . . | r . . Sg",
        'K': "k",
    })
    s.pat(T(25), 4, {
        'R': "Q . Qq . | Q Qq . Qq | Q . Qq . | Q Qq . Qq",
        'L': ". Sg . . | r . Sg . | r . . Sg | . Sg . .",
    }, vs=0.8)
    s.pat(T(26), 4, {
        'R': "B . Bq . | B Bq . Bq",
        'L': "r . . Sg | . . r .",
    })
    s.cellA(T(26, 2), 0.25, acc='456', fill='ghost', av=(86, 90, 98), gv=26)
    s.pat(T(27), 4, {
        'R': "Bq . B . | Bq B . Bq",
        'L': ". Sg . . | r . Sg .",
    })
    s.cellA(T(27, 2), 0.25, acc='Ww5', fill='ghost', av=(82, 78, 100), gv=28)
    s.add(T(27, 3.75), 'k', 70, 'K')
    s.pat(T(28), 4, {
        'R': "o! hg hq o! | hq hg o! hg | hq hg hq hg | hq hg hq hg",
        'L': "Sg . . . | S! . . Sg | . Sg . . | S! . . Sg",
        'K': "k . . k | . . . . | k . k . | . . . k",
    })
    s.pat(T(29), 4, {
        'R': "hq hg o! hg | hq o! hg hq | o! hg hq hg | . . . .",
        'L': ". Sg . Sg | S! . . Sg | . . Sg . | . . . .",
        'K': "k . . . | . . k . | . k . . | . . . .",
    })
    s.run(T(29, 3), 0.125, 'TTTTTTT', 'LR', v=(46, 96), curve=1.4, rush=0.006)
    s.pat(T(30), 4, {'R': "T^", 'L': "Z!", 'K': "k"})
    s.roll(T(30, 0.5), 3.5, 0.125, 'S', 22, 68, curve=1.3, lead='R',
           kicks=(4, 12, 20), kv=(52, 76))
    s.roll(T(31), 3.0, 0.125, 'S', 70, 112, curve=1.2, lead='R',
           acc={0: '4', 12: '5'}, kicks=(0, 12), kv=(96, 108))
    s.run(T(31, 3), 0.25, '6S42', 'RL', v=(104, 116), acc=(0,), av=(118, 118), kicks=(0,))


def section_triplets(s):
    for bar in (32, 36, 37, 38, 39, 41):
        s.feet(bar, bar + 1, 6, hat=(6, 18), hv=52)
    s.feet(35, 36, 6, hat=(3, 9, 15, 21), hv=50)
    s.run(T(32), 1 / 6, 'CSk5Sk51k51k42k42k63k63k', 'RLK', v=(76, 92),
          acc=(0, 6, 12, 18), av=(110, 118), kv=90, rush=0.004)
    s.run(T(33), 1 / 6, '4141kk5252kk6S6SkkDS5Skk', 'RLRLKH', v=(78, 96),
          acc=(0, 6, 12, 18), av=(106, 118), kv=88, rush=0.004)
    s.run(T(34), 1 / 6, '5Skk41kk62kk5SkkC1kk62kk', 'RLKH', v=(80, 98),
          acc=(0, 4, 8, 12, 16, 20), av=(104, 118), kv=90, rush=0.005)
    s.run(T(35), 1 / 6, '5SSSS14SSSS26SSSS1CSSSS2', 'RllrrL', v=(86, 102),
          acc=(0, 5, 6, 11, 12, 17, 18, 23), av=(100, 116), kicks=(0, 6, 12, 18),
          kv=92, rush=0.004)
    s.run(T(36), 1 / 6, '4Sk52k6kCSk51k4k62k5SkDk', 'RLKRLKRK', v=(72, 94),
          acc=(0, 3, 6, 8, 11, 14, 16, 19, 22), av=(100, 120), kv=90, rush=0.004)
    s.pat(T(37), 6, {
        'R': "C^ . . . . . | 5 . . 5 . . | S!~ . . . . . | 4 . . 4! . .",
        'L': ". . . . . . | . 2 . . 2 . | . . . . Sg . | . 1 . . 1 .",
        'K': "k . . . . . | . . k . . k | k . . . . . | . . k . . k",
    }, cresc=(0, 14))
    s.pat(T(38), 3, {
        'R': "5!~ . Sq | . Sq .",
        'L': ". Sq . | 1!~ . Sq",
        'K': "k . . | k . .",
    })
    s.pat(T(38, 2), 6, {
        'R': "4!~ . Sq . Sq . | 6!~ . Sq . Sq .",
        'L': ". Sq . 2!~ . Sq | . Sq . 1!~ . Sq",
        'K': "k . . . . . | k . . . . .",
    }, cresc=(0, 10))
    s.run(T(39), 1 / 6, '665544332211112233445566', 'RL', v=(70, 108),
          acc=(0, 6, 12, 18), av=(100, 118), kicks=(0, 6, 12, 18), rush=0.006)
    s.run(T(40), 1 / 6, 'CSk52k4SkD1k5Sk62kCSk51k', 'RLK', v=(78, 96),
          acc=(0, 9, 18), av=(114, 120), kv=90, rush=0.004)
    for sl in (0, 9, 18):
        s.add(T(40) + sl / 6, 'k', 104, 'H', 'n')
    s.roll(T(41), 2.0, 0.125, 'S', 50, 100, lead='R', curve=1.2)
    s.run(T(41, 2), 1 / 6, '112233445566', 'RL', v=(96, 118), acc=(0, 6),
          av=(110, 118), kicks=(0, 6), rush=0.010)


def section_recap(s):
    for bar in (42, 43, 44, 45, 47, 48, 49, 50, 51):
        s.feet(bar, bar + 1, 4, hat=(0, 4, 8, 12), hv=48)
    s.run(T(42), 0.25, 'CSSSSS5SXSSSSSDS', 'RllRllRlRllRllRl', v=(74, 86),
          acc=(0, 3, 6, 8, 11, 14), av=(114, 122), kicks=(0, 6, 8, 14), rush=0.004)
    s.cellC(T(43), 0.25, toms='5326', ghosts=(1, 4), kicks=(0, 2, 4, 7))
    s.run(T(43, 2.5), 0.25, '445566', 'RL', v=(88, 112), kicks=(5,), rush=0.006)
    s.pat(T(44), 4, {
        'R': "C^ S! . . | 2! . . 4! | . 5! . . | S! . 6! .",
        'L': ". . Sg Sg | . Sg Sg . | Sg . Sg Sg | . Sg . Sg",
        'K': "k . . . | k . . k | . k . . | . . k .",
    })
    s.pat(T(45), 4, {'R': "D^", 'K': "k"})
    s.cellA(T(45, 0.5), 0.25, acc='CS5', fill='taps', kicks=(0, 2), av=(114, 108, 116))
    s.run(T(45, 2.5), 0.125, '112233445566', 'RL', v=(80, 116), acc=(0, 4, 8),
          av=(104, 118), kicks=(0, 8), rush=0.010)
    s.run(T(46), 0.25, 'CS5kkX24kkDS6kk5', 'RLRKHRLRKHRLRKHR', v=(84, 100),
          acc=(0, 5, 10, 15), av=(112, 122), kv=94, rush=0.004)
    s.cellC(T(47), 1 / 6, toms='5326', ghosts=(4, 10, 11), flams=(0,), kicks=(0, 4, 7), vs=1.05)
    s.cellC(T(47, 2), 1 / 6, toms='4215', ghosts=(4, 10), flams=(0, 4), kicks=(0, 4, 7), vs=1.08)
    s.run(T(48), 0.25, 'CSSXSSDSSCSS6SSk', 'RllRllRllRllRllK', v=(76, 92),
          acc=(0, 3, 6, 9, 12), av=(114, 124), kicks=(0, 3, 6, 9), kv=100, rush=0.004)
    s.pat(T(49), 4, {
        'R': "C^ . . . | . . X! . | . . . . | 5!~ . 5 .",
        'L': ". Sg . Sg | . . . Sg | . Sg . Sg | . . Sg Sg",
        'K': "k . . . | . . k . | . . . . | k . . k",
    }, cresc=(0, 8))
    s.run(T(50), 0.125, 'SSSSSSSS11112222333344445555' + '6666', 'RL', v=(56, 112),
          acc=(0, 3, 6, 8, 11, 14, 16, 19, 22, 24, 27, 30), av=(84, 124),
          kicks=(0, 8, 16, 24), curve=1.3, rush=0.010)
    s.run(T(51), 1 / 6, 'SS11SS223322443355', 'RRLL', v=(72, 104),
          acc=(0, 4, 8, 12, 16), av=(100, 116), kicks=(0, 6, 12), rush=0.006)
    s.pat(T(51, 3), 4, {'R': "6!~ . . 5^~", 'L': ". S S .", 'K': "k . . k"})


def section_finale(s):
    s.feet(52, 54, 4, hat=(0, 4, 8, 12), hv=50)
    s.feet(54, 57, 4, hat=(4, 12), hv=54)
    s.run(T(52), 0.125, 'CS1122334455665544332211SS112233', 'RL', v=(80, 108),
          acc=(0, 3, 6, 8, 11, 14, 16, 19, 22, 24, 27, 30), av=(104, 122),
          kicks=(0, 8, 16, 24), rush=0.008)
    s.run(T(53), 1 / 6, 'CS4422' + '6S5511' + 'DS4422' + '6S66SS', 'RLRRLL',
          v=(82, 110), acc=(0, 6, 12, 18), av=(110, 122), kicks=(0, 6, 12, 18), rush=0.008)
    # motif A augmented: 3+3+2 in eighths, rolls swelling between the hits
    s.pat(T(54), 8, {'R': "C^", 'K': "k"})
    s.roll(T(54, 0.25), 1.125, 0.125, 'S', 44, 92, lead='L')
    s.pat(T(54, 1.5), 8, {'R': "D^", 'K': "k"})
    s.roll(T(54, 1.75), 1.125, 0.125, 'S', 54, 102, lead='L')
    s.pat(T(54, 3), 4, {'R': "X^ . 6! .", 'L': ". S . S!", 'K': "k . k ."})
    s.pat(T(55), 4, {
        'R': "5^ . . . | . . C^ .",
        'L': "1^ . Sg Sg | Sg Sg . .",
        'K': "k . . . | . . k .",
    })
    s.run(T(55, 2), 1 / 6, '112233445566', 'RL', v=(92, 118), acc=(0, 6),
          av=(108, 122), kicks=(0, 6, 9), rush=0.006)
    # last bar: hold back, swell, motif A with flams, and land it
    s.pat(T(56), 4, {'R': "C^", 'K': "k"})
    s.roll(T(56, 0.25), 1.75, 0.125, 'S', 34, 112, curve=1.6, lead='L',
           kicks=(6, 12), kv=(70, 100))
    s.cellA(T(56, 2), 0.25, acc='356', fill='taps', flams=(0, 1, 2), kicks=(0, 1, 2),
            av=(112, 116, 122))
    s.add(T(FINAL_BAR), 'C', 127, 'R', 'end', 0.0, 'end')
    s.add(T(FINAL_BAR), 'D', 127, 'L', 'end', 0.003, 'end')
    s.add(T(FINAL_BAR), 'k', 127, 'K', 'end', -0.002, 'end')


# ---------------------------------------------------------------- variety
def bar_print(s, bar):
    lo = 4.0 * bar
    return tuple(sorted((int(round((h.beat - lo) * 24)), h.note) for h in s.hits
                        if lo - 1e-9 <= h.beat < lo + 4.0 - 1e-9
                        and h.kind != 'grace' and h.tag != 'ost'))


def ensure_unique_bars(s):
    seen = set()
    for bar in range(FINAL_BAR):
        lo = 4.0 * bar
        for attempt in range(8):
            if bar_print(s, bar) not in seen:
                break
            added = False
            for k in range(16):
                sl = (3 + 5 * (attempt + k)) % 16
                b = lo + sl / 4.0
                if all(abs(h.beat - b) > 0.2 for h in s.hits
                       if h.limb in HANDS and abs(h.beat - b) < 1.0):
                    s.add(b, 'S', 24, 'L', 'g', 0.0, 'var')
                    added = True
                    break
            if not added:
                break
        seen.add(bar_print(s, bar))


# ---------------------------------------------------------------- time
class TempoMap:
    def __init__(self, tempos):
        self.tempos = tempos
        self.spb = [t / 1e6 for t in tempos]
        self.start = [0.0]
        for x in self.spb:
            self.start.append(self.start[-1] + x * SEG)

    def sec(self, beat):
        i = int(math.floor(beat / SEG))
        i = max(0, min(i, len(self.spb) - 1))
        return self.start[i] + (beat - i * SEG) * self.spb[i]

    def tick(self, sec):
        if sec <= 0:
            return 0
        i = bisect.bisect_right(self.start, sec) - 1
        i = max(0, min(i, len(self.spb) - 1))
        beat = i * SEG + (sec - self.start[i]) / self.spb[i]
        return int(round(beat * PPQ))


def key_bpm(bar):
    keys = TEMPO_KEYS
    if bar <= keys[0][0]:
        return keys[0][1]
    for (b0, v0), (b1, v1) in zip(keys, keys[1:]):
        if b0 <= bar <= b1:
            f = (bar - b0) / (b1 - b0)
            f = 0.5 - 0.5 * math.cos(math.pi * f)
            return v0 + (v1 - v0) * f
    return keys[-1][1]


def build_tempo(solo):
    nseg = int((FINAL_BAR * 4 + 12) / SEG)
    final_seg = int(FINAL_BAR * 4 / SEG)
    counts = [0.0] * nseg
    for h in solo.hits:
        if h.kind == 'grace' or h.tag == 'ost':
            continue
        i = int(h.beat // SEG)
        if 0 <= i < nseg:
            counts[i] += 1.0 + (0.6 if h.kind in ('!', '^') else 0.0)
    look = []
    for i in range(nseg):
        w = counts[max(0, i - 1): i + 3]
        look.append(sum(w) / len(w))
    body = look[:final_seg]
    mean = sum(body) / len(body)
    std = math.sqrt(sum((x - mean) ** 2 for x in body) / len(body)) or 1.0
    raw = [math.tanh((x - mean) / (1.5 * std)) for x in look]
    sm = []
    for i in range(nseg):
        w = raw[max(0, i - 2): i + 3]
        sm.append(sum(w) / len(w))
    bpm = []
    for i in range(nseg):
        bar = (i + 0.5) * SEG / 4.0
        weight = 1.0 if bar < 54.0 else 0.25
        bpm.append(key_bpm(bar) * (1.0 + 0.016 * weight * sm[i]))
    t = sum(60.0 / b * SEG for b in bpm[:final_seg])
    k = t / (TARGET_FINAL_SEC - LEAD)
    tempos = [int(round(60e6 / (b * k))) for b in bpm]
    return TempoMap(tempos)


def humanize(solo, tm):
    rng = random.Random(SEED * 7 + 3)
    mains = sorted((h for h in solo.hits if h.kind != 'grace'),
                   key=lambda h: (h.beat, LIMB_ORDER[h.limb], h.note))
    ar = {l: 0.0 for l in LIMB_ORDER}
    bias = {'R': -0.0015, 'L': 0.0020, 'K': 0.0010, 'H': 0.0030}
    for h in mains:
        if h.kind == 'end':
            h.sec = LEAD + tm.sec(h.beat) + h.dt
            h.vel = 127
            continue
        if h.kind in ('!', '^'):
            sd, kb = 0.0028, -0.0012
        elif h.kind == 'g':
            sd, kb = 0.0055, 0.0035
        else:
            sd, kb = 0.0040, 0.0
        if h.limb in FEET:
            sd = 0.0038
        if h.sd is not None:
            sd = min(sd, h.sd)
        ar[h.limb] = 0.55 * ar[h.limb] + rng.gauss(0.0, sd)
        e = max(-0.016, min(0.016, ar[h.limb]))
        h.sec = LEAD + tm.sec(h.beat) + e + bias[h.limb] + kb + h.dt
        v = h.vel
        if h.kind in ('n', 'q'):
            fb = h.beat % 1.0
            if min(fb, 1.0 - fb) < 1e-6:
                v += 4
            elif abs(fb - 0.5) < 1e-6:
                v += 1
            else:
                v -= 2
        if h.limb == 'L' and h.kind not in ('!', '^'):
            v -= 3
        v += rng.gauss(0.0, 2.5 if h.kind == 'g' else 3.5)
        lo, hi = VCLAMP[h.kind]
        h.vel = max(lo, min(hi, v))
    for g in solo.hits:
        if g.kind == 'grace':
            g.sec = g.parent.sec + g.dt + rng.gauss(0.0, 0.0022)
            g.vel = max(12, min(70, g.vel + rng.gauss(0.0, 3.0)))


# ---------------------------------------------------------------- playability
def min_gap(a, b, limb):
    if limb in FEET:
        return 0.060
    if a.kind == 'grace' or b.kind == 'grace':
        return 0.014
    return 0.035


def enforce_playable(hits):
    alive = list(hits)
    while True:
        dead = set()
        by_note = {}
        for h in alive:
            by_note.setdefault(h.note, []).append(h)
        for note in sorted(by_note):
            lst = sorted(by_note[note], key=lambda h: h.sec)
            for a, b in zip(lst, lst[1:]):
                if id(a) in dead or id(b) in dead:
                    continue
                if b.sec - a.sec < 0.015:
                    lo, hi = (a, b) if a.prio < b.prio else (b, a)
                    dead.add(id(lo))
                    hi.vel = min(127, hi.vel + 4)
        by_limb = {}
        for h in alive:
            if id(h) not in dead:
                by_limb.setdefault(h.limb, []).append(h)
        for limb in ('R', 'L', 'K', 'H'):
            lst = sorted(by_limb.get(limb, []), key=lambda h: h.sec)
            for a, b in zip(lst, lst[1:]):
                if id(a) in dead or id(b) in dead:
                    continue
                if b.sec - a.sec < min_gap(a, b, limb):
                    dead.add(id(a) if a.prio < b.prio else id(b))
        hand = sorted((h for h in alive if h.limb in HANDS and id(h) not in dead),
                      key=lambda h: h.sec)
        for i in range(len(hand) - 2):
            trio = hand[i:i + 3]
            if any(id(x) in dead for x in trio):
                continue
            if trio[2].sec - trio[0].sec < 0.040:
                dead.add(id(min(trio, key=lambda h: h.prio)))
        for h in alive:
            if h.kind == 'grace' and id(h.parent) in dead:
                dead.add(id(h))
        if not dead:
            return alive
        alive = [h for h in alive if id(h) not in dead]


def assign_durations(hits, tm):
    end_sec = TOTAL_SEC
    order = sorted(hits, key=lambda h: (h.sec, h.note))
    nxt_limb, nxt_note = {}, {}
    for h in reversed(order):
        if h.kind == 'end':
            cap = end_sec - 0.08 - h.sec
        else:
            cap = CAP.get(h.note, 0.32 if h.note in TOM_NOTES else 0.2)
        off = min(h.sec + cap, nxt_limb.get(h.limb, 1e9) - 0.004,
                  nxt_note.get(h.note, 1e9) - 0.004, end_sec - 0.05)
        off = max(off, h.sec + 0.010)
        h.on = tm.tick(h.sec)
        h.off = max(h.on + 1, tm.tick(off))
        nxt_limb[h.limb] = h.sec
        nxt_note[h.note] = h.sec


# ---------------------------------------------------------------- output
def write_midi(hits, tm, path='solo.mid'):
    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    meta = mido.MidiTrack()
    mid.tracks.append(meta)
    meta.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    meta.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                 clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    end_tick = tm.tick(TOTAL_SEC)
    last, prev = 0, None
    step = int(SEG * PPQ)
    for i, tempo in enumerate(tm.tempos):
        tick = i * step
        if tick >= end_tick:
            break
        if tempo == prev:
            continue
        meta.append(mido.MetaMessage('set_tempo', tempo=tempo, time=tick - last))
        last, prev = tick, tempo
    meta.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - last)))

    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drums', time=0))
    tr.append(mido.Message('sysex', data=[0x7E, 0x7F, 0x09, 0x01], time=0))
    tr.append(mido.Message('program_change', channel=CH, program=0, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=7, value=112, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=10, value=64, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=91, value=48, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=93, value=0, time=0))
    events = []
    for h in hits:
        vel = max(1, min(127, int(round(h.vel))))
        events.append((h.on, 1, h.note, 'note_on', vel))
        events.append((h.off, 0, h.note, 'note_off', 0))
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    cur = 0
    for tick, _, note, typ, vel in events:
        tr.append(mido.Message(typ, channel=CH, note=note, velocity=vel, time=tick - cur))
        cur = tick
    tr.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - cur)))
    mid.save(path)
    return mid


def main():
    s = Solo()
    section_statement(s)
    section_tom_song(s)
    section_hands(s)
    section_interlude(s)
    section_triplets(s)
    section_recap(s)
    section_finale(s)
    ensure_unique_bars(s)
    tm = build_tempo(s)
    humanize(s, tm)
    hits = enforce_playable(s.hits)
    assign_durations(hits, tm)
    mid = write_midi(hits, tm)
    print("wrote solo.mid: %d notes, %.1f s" % (len(hits), mid.length))


if __name__ == '__main__':
    main()
