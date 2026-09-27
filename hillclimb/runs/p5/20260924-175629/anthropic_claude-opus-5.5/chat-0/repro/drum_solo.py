#!/usr/bin/env python3
"""
drum_solo.py - generates a ~2 minute General MIDI drum solo (solo.mid, channel 10).

Design:
  * One motif (a 3-3-4-2-4 sixteenth-note accent cell) is stated, varied
    (re-orchestrated, displaced, flammed, diminished to 32nds, augmented to 8ths,
    cast as cowbell/timbale clave, used as accent grouping in runs) and brought back.
  * Music is written on a beat grid.  A tempo map with surges and settles, fill
    pushes, per-limb drift and per-note humanisation turn it into real time.
  * Each stroke belongs to a limb (R, L, right foot, left foot).  A final pass
    guarantees that no limb strikes faster than it physically can, so at most
    two hands and two feet sound at any instant.
  * Fully deterministic: seeded RNG, so every run writes an identical file.
"""
import math
import random
import mido

R = random.Random(20240917)

NOTE = dict(KA=35, K=36, SS=37, S=38, SX=40, F2=41, HH=42, F1=43, HP=44, T4=45,
            HO=46, T3=47, T2=48, CR=49, T1=50, RD=51, CH=52, RB=53, SP=55, CB=56,
            CR2=57, BH=60, BL=61, TH=65, TL=66, AH=67, AL=68, CL=75, WH=76, WL=77,
            TRM=80, TRO=81)
CYM = {'CR', 'CR2', 'RD', 'RB', 'SP', 'CH', 'HH', 'HO', 'CB'}
LONG = {'CR', 'CR2', 'CH', 'SP', 'RD', 'RB'}
FEET = {'K': 'RF', 'KA': 'RF', 'HP': 'LF'}
VEL = {'X': 116, 'x': 90, 'o': 68, 'm': 52, 'g': 36, 'q': 24}
MOT = [0, 3, 6, 10, 12]                 # the motif: 3-3-4-2-4 accents
G_MOT24 = [3, 3, 4, 2, 4, 3, 3, 2]      # motif grouping stretched over 24 notes
KIT = ['S', 'T1', 'T2', 'T4', 'F1', 'F2']


class Solo:
    def __init__(self):
        self.ev = []
        self.push = []

    def hit(self, b, v, vel, hand=None, grace=0.0, dur=None):
        if vel <= 0:
            return
        if v in FEET:
            limb = FEET[v]
        elif hand in ('R', 'L'):
            limb = hand
        elif v in CYM:
            limb = 'R'
        else:
            limb = 'R' if int(round(b * 4)) % 2 == 0 else 'L'
        self.ev.append(dict(b=b, v=v, vel=float(vel), limb=limb, grace=grace, dur=dur))

    def flam(self, b, v, vel, hand='R'):
        other = 'L' if hand == 'R' else 'R'
        self.hit(b, v, vel, hand)
        self.hit(b, v, max(22, vel * 0.38), other, grace=0.028)

    def bump(self, s, e, amt):
        self.push.append((s, e, amt))

    def pat(self, bar, spec, step=0.25, off=0.0, dyn=(1.0, 1.0)):
        b0 = bar * 4 + off
        n = max(len(s) for s in spec.values())
        for v, s in spec.items():
            for i, c in enumerate(s):
                if c in VEL:
                    m = dyn[0] + (dyn[1] - dyn[0]) * (i / (n - 1) if n > 1 else 0)
                    self.hit(b0 + i * step, v, VEL[c] * m)

    def line(self, b0, step, voices, vels, stick="RL"):
        for i, v in enumerate(voices):
            if v is None:
                continue
            self.hit(b0 + i * step, v, vels[i], stick[i % len(stick)])


def ramp(n, a, b, curve=1.0):
    if n == 1:
        return [b]
    return [a + (b - a) * ((i / (n - 1)) ** curve) for i in range(n)]


def travel(n, path, per):
    return [path[(i // per) % len(path)] for i in range(n)]


def group_starts(n, groups):
    st, i, k = [], 0, 0
    while i < n:
        st.append(i)
        i += groups[k % len(groups)]
        k += 1
    return st


def motif(S, bar, orch, disp=0, ghost='S', gp=0.6, g=(24, 40),
          acc=(108, 96, 100, 94, 112), kick=(), kv=86, hp=(4, 12), hv=54,
          dyn=1.0, flam=False, step=0.25, off=0.0, glim=None, length=16):
    b0 = bar * 4 + off
    slots = [(m + disp) % length for m in MOT]
    for k, sl in enumerate(slots):
        vs = orch[k] if isinstance(orch[k], tuple) else (orch[k],)
        par = 'R' if sl % 2 == 0 else 'L'
        used = []
        for v in vs:
            vel = acc[k] * dyn
            if v in FEET:
                S.hit(b0 + sl * step, v, vel * 0.92)
                continue
            if v in CYM:
                h = 'R' if 'R' not in used else 'L'
            else:
                h = par if par not in used else ('L' if par == 'R' else 'R')
            used.append(h)
            if flam and v not in CYM:
                S.flam(b0 + sl * step, v, vel, h)
            else:
                S.hit(b0 + sl * step, v, vel, h)
    gl = length if glim is None else glim
    for sl in range(gl):
        if sl in slots:
            continue
        if ghost and R.random() < gp:
            vel = g[0] + (g[1] - g[0]) * sl / max(1, length - 1)
            S.hit(b0 + sl * step, ghost, vel, 'R' if sl % 2 == 0 else 'L')
    for sl in kick:
        S.hit(b0 + sl * step, 'K', kv * dyn)
    for sl in hp:
        S.hit(b0 + sl * step, 'HP', hv)


def grouped_run(S, b0, step, n, groups, path, lo, hi, acc_add=24, kick=True,
                acc_voice=None, kv=0.85):
    starts = set(group_starts(n, groups))
    gi = -1
    for i in range(n):
        if i in starts:
            gi += 1
        base = lo + (hi - lo) * i / max(1, n - 1)
        v = path[gi % len(path)]
        h = 'R' if i % 2 == 0 else 'L'
        if i in starts:
            vel = base + acc_add
            if acc_voice:
                av = acc_voice(gi)
                if av:
                    v = av
            S.hit(b0 + i * step, v, vel, h)
            if kick:
                S.hit(b0 + i * step, 'K', vel * kv)
        else:
            S.hit(b0 + i * step, v, base, h)


def sticking_run(S, b0, n, step, st, glen, toms, acc=104, rv=72, gh=34,
                 kick=True, cres=(1.0, 1.0)):
    for i in range(n):
        h = st[i % len(st)]
        first = (i % glen) == 0
        m = cres[0] + (cres[1] - cres[0]) * i / max(1, n - 1)
        if h == 'R':
            v = toms[(i // glen) % len(toms)]
            vel = acc if first else rv
        else:
            v = 'S'
            vel = acc if first else gh
        S.hit(b0 + i * step, v, vel * m, h)
        if first and kick:
            S.hit(b0 + i * step, 'K', 80 * m)


def six_stroke(S, b0, beats, toms, lo, hi):
    p = [('R', 1.0, 'T'), ('L', 0.40, 'S'), ('L', 0.45, 'S'),
         ('R', 0.50, 'S'), ('R', 0.55, 'S'), ('L', 0.95, 'S')]
    n = beats * 6
    for i in range(n):
        h, m, w = p[i % 6]
        base = lo + (hi - lo) * i / (n - 1)
        v = toms[(i // 6) % len(toms)] if w == 'T' else 'S'
        S.hit(b0 + i / 6, v, base * m, h)
        if i % 6 == 0:
            S.hit(b0 + i / 6, 'K', base * 0.85)


def cells(S, bar, path, acc0=98, step_acc=2, gp=0.7, kick_quarters=True,
          kick_acc=False, hp=True):
    b0 = bar * 4
    for i in range(16):
        b = b0 + i * 0.25
        if i % 3 == 0:
            vs = path[i // 3]
            vs = vs if isinstance(vs, tuple) else (vs,)
            for v in vs:
                S.hit(b, v, acc0 + step_acc * (i // 3))
            if kick_acc:
                S.hit(b, 'K', acc0 - 8)
        elif R.random() < gp:
            S.hit(b, 'S', 26 + i * 1.2)
        if kick_quarters and i % 4 == 0:
            S.hit(b, 'K', 84)
    if hp:
        S.hit(b0 + 1, 'HP', 52)
        S.hit(b0 + 3, 'HP', 52)


def latin_feet(S, bar):
    S.pat(bar, {'K': "x.....x...x...x.", 'HP': "....m.......m..."}, dyn=(0.86, 0.86))


def latin_hands(S, bar, half=False):
    cb = "X..X..X.m.X.X.m."
    if half:
        cb = cb[:8]
    S.pat(bar, {'CB': cb}, dyn=(0.9, 0.9))
    b0 = bar * 4
    for sl in (1, 5, 7, 9, 11, 13, 15):
        if half and sl > 7:
            break
        r = R.random()
        if r < 0.35:
            v = 'TH'
        elif r < 0.62:
            v = 'TL'
        elif r < 0.82:
            v = 'S'
        else:
            continue
        if sl in (7, 15):
            vel = 86 + R.random() * 16
        else:
            vel = 36 + R.random() * 22
        S.hit(b0 + sl * 0.25, v, vel, 'L')


def compose():
    S = Solo()
    # ---------------- I. Statement (bars 0-3)
    S.pat(0, {'S': "X..X..X...X.X.gg", 'K': "x.........x.....",
              'HP': "....m.......m..."}, dyn=(0.8, 0.9))
    S.pat(1, {'S': ".gg.Xg.g.gXg.g..", 'K': "x..x......x.....",
              'T1': "..............xo", 'HP': "....m.......m..."}, dyn=(0.8, 0.95))
    S.pat(2, {'S': "XggXggXgg.Xg.gog", 'F1': "............X...",
              'K': "x.....x...x.x...", 'HP': "....m.......m..."}, dyn=(0.88, 0.98))
    S.pat(3, {'T1': "X...............", 'T2': "...X............",
              'T4': "......X.......x.", 'F1': "..........X....x",
              'F2': "............X...", 'S': ".gg.gg.gg..g.x..",
              'K': "x.........x.x...", 'HP': "....m..........."}, dyn=(0.9, 1.05))
    S.bump(13, 16, 3)

    # ---------------- II. Development (bars 4-11)
    motif(S, 4, [('CR', 'K'), 'T1', 'T2', ('F1', 'K'), 'S'], gp=0.55)
    S.pat(5, {'HH': "x..x.x..x..x.x..", 'S': "..g.X.g..g..X.gg",
              'K': ".x.....x..x....."})
    motif(S, 6, [('S', 'K')] * 5, disp=2, gp=0.5)
    sticking_run(S, 28, 8, 0.25, "RLRRLRLL", 4, ['T1', 'T2'], acc=100, rv=70, gh=32)
    S.line(30, 1 / 6, travel(12, KIT, 2), ramp(12, 64, 112), "RL")
    S.hit(30, 'K', 80)
    S.hit(31, 'K', 92)
    S.bump(29, 32, 3)
    motif(S, 8, [('CR', 'K'), 'S', 'S', ('S', 'K'), 'S'], flam=True, gp=0.7, g=(26, 44))
    cells(S, 9, ['T1', 'T2', 'T4', 'F1', 'F2', 'S'])
    motif(S, 10, ['S', 'T1', 'S', 'T2', 'F1'], step=0.125, gp=1.0, g=(30, 48),
          kick=(0, 8), hp=(8,), acc=(100, 90, 96, 90, 104))
    motif(S, 10, ['T1', 'T2', 'T4', 'F1', ('F2', 'K')], step=0.125, off=2.0, gp=1.0,
          g=(40, 60), kick=(0, 8), hp=(8,), acc=(104, 96, 100, 98, 114))
    grouped_run(S, 44, 1 / 6, 24, G_MOT24, ['S', 'T1', 'T2', 'T4', 'F1', 'F2', 'T4', 'F2'],
                58, 100, acc_add=18)
    S.bump(44, 48, 4)

    # ---------------- III. Hush / texture (bars 12-17)
    S.hit(48, 'CR', 118)
    S.hit(48, 'K', 108)
    S.pat(12, {'SS': "....o.......o...", 'S': "......q..q....qg",
               'HP': "....m...m...m..."})
    S.bump(48, 56, -2.5)
    motif(S, 13, ['WH', 'WL', 'WH', 'WL', 'WH'], gp=0.35, g=(18, 30),
          acc=(74, 60, 70, 58, 78), kick=(0,), kv=56, hp=(0, 4, 8, 12), hv=46)
    motif(S, 14, ['SS', 'WH', 'SS', 'WL', 'SS'], disp=2, gp=0.45, g=(20, 34),
          acc=(66, 72, 70, 62, 78), kick=(0, 10), kv=58, hp=(0, 4, 8, 12), hv=46)
    S.pat(15, {'S': ".qg.qg.qgq.g.qgo", 'WH': "x.....x.........",
               'WL': "...x......x.x...", 'K': "o.......o.......",
               'HP': "m...m...m...m..."}, dyn=(0.75, 1.1))
    S.line(64, 0.25, ['S'] * 16, ramp(16, 22, 60), "RL")
    for i, v in enumerate([46, 52, 58, 66]):
        S.hit(64 + i, 'K', v)
    S.hit(65, 'HP', 44)
    S.hit(67, 'HP', 44)
    S.line(68, 0.125, ['S'] * 24, ramp(24, 58, 104), "RRLL")
    S.line(71, 0.125, ['T1', 'T1', 'T2', 'T2', 'T4', 'F1', 'F1', 'F2'], ramp(8, 100, 118), "RL")
    for i, v in enumerate([72, 82, 92, 104]):
        S.hit(68 + i, 'K', v)
    S.bump(66, 72, 4)

    # ---------------- IV. Latin: cowbell clave of the motif (bars 18-25)
    for bar in range(18, 26):
        latin_feet(S, bar)
    S.hit(72, 'CR', 112)
    latin_hands(S, 18)
    latin_hands(S, 19)
    latin_hands(S, 20)
    latin_hands(S, 21, half=True)
    S.line(86, 1 / 6, ['TH', 'TH', 'TL', 'TL'] * 3, ramp(12, 60, 108), "RL")
    # timbale solo over the foot ostinato
    grouped_run(S, 88, 0.25, 16, [3, 3, 4, 2, 4], ['TH', 'TL', 'TH', 'T2', 'TL'],
                55, 70, acc_add=45, kick=False)
    S.hit(88, 'SP', 100, 'L')
    for i in range(18):
        b = 92 + i / 6
        h = 'R' if i % 2 == 0 else 'L'
        if i % 4 == 0:
            S.hit(b, 'TL', 104, h)
        else:
            S.hit(b, 'TH', 40 + i, h)
    S.line(95, 0.125, ['TH'] * 8, ramp(8, 44, 104), "RL")
    S.bump(93, 96, 3)
    motif(S, 24, [('TH', 'SP'), 'TL', 'TH', 'TL', ('TH', 'CB')], ghost='TL', gp=0.45,
          g=(28, 44), hp=())
    S.pat(25, {'CB': "X..X..X."}, dyn=(0.9, 0.9))
    S.hit(100.25, 'TH', 40, 'L')
    S.hit(101.25, 'TH', 46, 'L')
    S.line(102, 0.25, ['T1', 'T1', 'T2', 'T2', 'T4', 'T4', 'F1', 'F1'], ramp(8, 80, 112), "RL")
    S.bump(98, 104, 3.5)

    # ---------------- V. Around the kit (bars 26-33)
    for bar in range(26, 34):
        if bar != 31:
            S.hit(bar * 4 + 1, 'HP', 50)
            S.hit(bar * 4 + 3, 'HP', 50)
    S.hit(104, 'CR', 116)
    S.hit(104, 'K', 108)
    for i in range(1, 24):
        b = 104 + i / 6
        v = KIT[i % 6]
        h = 'R' if i % 2 == 0 else 'L'
        if i % 4 == 0:
            S.hit(b, v, 104, h)
            S.hit(b, 'K', 92)
        else:
            S.hit(b, v, 62 + i * 0.9, h)
    S.line(108, 0.125, ['S', 'S', 'T1', 'T1', 'T2', 'T2', 'T4', 'T4', 'F1', 'F1', 'F2', 'F2',
                        'T4', 'T4', 'T2', 'T2'], ramp(16, 50, 100), "RRLL")
    S.hit(108, 'K', 70)
    S.hit(109, 'K', 84)
    for sl, vs, vel in ((8, ('CR', 'K'), 114), (11, ('F1', 'K'), 110), (14, ('CR2', 'K'), 118)):
        for v in vs:
            S.hit(108 + sl * 0.25, v, vel)
    for sl in (9, 10, 12, 13, 15):
        S.hit(108 + sl * 0.25, 'S', 30 + sl * 1.2)
    sticking_run(S, 112, 16, 0.25, "RLRRLRLL", 4, ['T1', 'T2', 'T4', 'F1'], cres=(0.9, 1.05))
    sticking_run(S, 116, 24, 1 / 6, "RLRRLL", 6, ['F1', 'T4', 'T2', 'T1'], acc=108, rv=74,
                 gh=38, cres=(0.95, 1.1))
    S.bump(117, 120, 2.5)
    six_stroke(S, 120, 4, ['T1', 'T2', 'T4', 'F1'], 80, 112)
    motif(S, 31, [('CR', 'K'), ('F1', 'K'), ('CR2', 'K'), ('F2', 'K'), ('CR', 'S', 'K')],
          gp=0.8, g=(30, 50), hp=())
    grouped_run(S, 128, 1 / 6, 42, [5], ['S', 'T1', 'T2', 'T4', 'F1', 'F2', 'T4', 'T2'],
                60, 106, acc_add=22)
    S.line(135, 0.125, ['S'] * 8, ramp(8, 80, 118), "RRLL")
    S.hit(135, 'K', 96)
    S.bump(132, 136, 4)

    # ---------------- VI. Breakdown: space, augmentation, roll (bars 34-37)
    S.hit(136, 'CR', 124, 'R')
    S.hit(136, 'CH', 118, 'L')
    S.hit(136, 'K', 118)
    for b in (137, 138, 139):
        S.hit(b, 'HP', 44)
    for b, v in ((139.25, 20), (139.5, 26), (139.75, 32)):
        S.hit(b, 'S', v)
    aug = [(0, 'F2', 84), (1.5, 'F1', 78), (3, 'T4', 86), (5, 'F1', 90), (6, 'F2', 100)]
    acc_pos = set()
    for p, v, vel in aug:
        S.hit(140 + p, v, vel)
        acc_pos.add(round(p * 4))
    for p in (0, 3, 6):
        S.hit(140 + p, 'K', 80)
    for sl in range(26):
        if sl in acc_pos:
            continue
        if R.random() < 0.3:
            S.hit(140 + sl * 0.25, 'S', 18 + sl * 0.5)
    for i in range(8):
        S.hit(140 + i, 'HP', 44)
    S.line(146.75, 0.25, ['S', 'T1', 'T2', 'S', 'T4'], [40, 62, 66, 50, 70], "LRLRL")
    S.bump(140, 146, -2)
    S.line(148, 0.125, ['S'] * 32, ramp(32, 22, 116, 1.4), "RRLL")
    for i, v in enumerate([50, 65, 80, 95]):
        S.hit(148 + i, 'K', v)
    S.bump(148, 152, 6)

    # ---------------- VII. Recapitulation (bars 38-45)
    motif(S, 38, [('CR', 'K'), 'T1', 'T2', ('F1', 'K'), ('CR2', 'S', 'K')], gp=0.6, g=(28, 46))
    motif(S, 39, ['S', 'S', ('CH', 'K'), 'T4', ('CR', 'K')], gp=0.5, glim=12, hp=(4,))
    S.line(159.25, 0.125, ['T1', 'T1', 'T2', 'T2', 'F1', 'F1'], ramp(6, 70, 104), "RRLL")
    motif(S, 40, [('CH', 'K'), 'T2', 'F1', ('CH', 'K'), ('CR', 'K')], disp=4, gp=0.5, hp=())
    for i in range(24):
        b = 164 + i / 6
        base = 70 + 40 * i / 23
        r = i % 3
        if r == 0:
            S.hit(b, ['T1', 'T2', 'T4', 'F1', 'F2', 'F1', 'T4', 'T2'][(i // 3) % 8], base + 18, 'R')
        elif r == 1:
            S.hit(b, 'S', base * 0.55, 'L')
        else:
            S.hit(b, 'K', base)
    S.bump(165, 168, 3)
    S.pat(42, {'CR': "X..X..X...X.X...", 'S': "..g.X...g..gX.g.",
               'K': "x.x...x.x.x.x.xx"})
    cells(S, 43, [('CR', 'K'), 'F1', 'T4', 'T2', 'T1', ('CH', 'K')], acc0=104,
          kick_quarters=False, kick_acc=True)
    motif(S, 44, ['S', 'T1', 'T2', 'T4', 'F1'], step=0.125, gp=1.0, g=(40, 62),
          kick=(0, 8), hp=(8,))
    motif(S, 44, ['T1', 'T2', 'T4', 'F1', ('F2', 'K')], step=0.125, off=2.0, gp=1.0,
          g=(46, 66), kick=(0, 8), hp=(8,), acc=(108, 100, 104, 100, 118))
    S.line(180, 0.125, travel(32, KIT, 2), ramp(32, 60, 118), "RRLL")
    for i, v in enumerate([70, 80, 90, 100]):
        S.hit(180 + i, 'K', v)
    S.bump(180, 184, 4)

    # ---------------- VIII. Finale (bars 46-49) and the final hit
    grouped_run(S, 184, 1 / 6, 24, G_MOT24, ['T1', 'T2', 'T4', 'F1', 'F2', 'T4', 'F1', 'F2'],
                70, 100, acc_add=22, acc_voice=lambda gi: 'CR' if gi == 0 else None)
    grouped_run(S, 188, 1 / 6, 24, G_MOT24, ['F2', 'F1', 'T4', 'T2', 'T1', 'S', 'T1', 'T2'],
                76, 108, acc_add=18, acc_voice=lambda gi: 'CR' if gi % 2 == 0 else None)
    S.line(192, 0.125, ['F1', 'F2'] * 16, ramp(32, 50, 122, 1.3), "RL")
    for i in range(8):
        S.hit(192 + i * 0.5, 'K', 60 + i * 7)
    S.bump(192, 196, 5)
    for pos, vs, vel in ((0, ('CR', 'K'), 120), (0.75, ('CR2', 'K'), 116), (1.5, ('CH', 'K'), 122)):
        for v in vs:
            S.hit(196 + pos, v, vel)
    for pos, vel in ((0.25, 36), (0.5, 42), (1.0, 40), (1.25, 48), (1.75, 56)):
        S.hit(196 + pos, 'S', vel)
    S.line(198, 0.125, ['S', 'S', 'T1', 'T1', 'T2', 'T2', 'T4', 'T4', 'F1', 'F1', 'F2', 'F2',
                        'F1', 'F1', 'F2', 'F2'], ramp(16, 72, 124, 0.8), "RL")
    S.hit(198, 'K', 90)
    S.hit(199, 'K', 104)
    S.hit(199.5, 'K', 110)
    S.hit(200, 'CR', 127, 'R', dur=3.2)
    S.hit(200, 'CR2', 124, 'L', dur=3.2)
    S.hit(200, 'K', 127, dur=2.0)
    return S


# ---------------------------------------------------------------- time map
CTRL = [(0, 95), (12, 99), (16, 101), (40, 102), (48, 100), (52, 96), (60, 97), (64, 99),
        (72, 104), (88, 105), (104, 107), (128, 109), (136, 108), (137, 98), (140, 94),
        (148, 94), (152, 104), (168, 106), (184, 109), (192, 112), (196, 112), (198, 103),
        (200, 88), (210, 88)]
RES = 64


def interp_ctrl(b):
    for i in range(len(CTRL) - 1):
        b0, v0 = CTRL[i]
        b1, v1 = CTRL[i + 1]
        if b0 <= b <= b1:
            f = (b - b0) / (b1 - b0)
            f = 0.5 - 0.5 * math.cos(math.pi * f)
            return v0 + (v1 - v0) * f
    return CTRL[-1][1]


def build_time_map(S, end_beat=206):
    wob = [R.uniform(-0.9, 0.9) for _ in range(60)]

    def bpm(b):
        t = interp_ctrl(b)
        for s, e, a in S.push:
            if s <= b <= e:
                t += a * math.sin(math.pi * (b - s) / (e - s))
        bar = int(b // 4)
        if bar < len(wob):
            t += wob[bar] * math.sin(math.pi * ((b % 4) / 4.0))
        return max(40.0, t)

    n = end_beat * RES
    T = [0.0] * (n + 1)
    for i in range(n):
        T[i + 1] = T[i] + 60.0 / bpm((i + 0.5) / RES) / RES

    def tb(b):
        x = b * RES
        i = int(x)
        if i >= n:
            i = n - 1
        if i < 0:
            i = 0
        return T[i] + (T[i + 1] - T[i]) * (x - i)
    return tb


# ---------------------------------------------------------------- render
def render(S):
    tb = build_time_map(S)
    final_beat = 200
    scale = 116.8 / tb(final_beat)
    lead = 0.3
    phase = {l: (R.uniform(0, 6.28), R.uniform(0, 6.28)) for l in ('R', 'L', 'RF', 'LF')}

    def drift(l, t):
        p = phase[l]
        return 0.0025 * math.sin(t * 0.9 + p[0]) + 0.0015 * math.sin(t * 2.3 + p[1])

    notes = []
    for e in S.ev:
        t = tb(e['b']) * scale + lead
        v = e['vel']
        limb = e['limb']
        ghost = v < 48
        accent = v >= 100
        if abs(e['b'] - final_beat) < 1e-9:
            off = R.gauss(0, 0.002)
        else:
            sd = 0.0045 if limb in ('R', 'L') else 0.006
            off = R.gauss(0, sd)
            if ghost:
                off += 0.005
            if accent:
                off -= 0.002
            if limb == 'RF':
                off += 0.002
            off += drift(limb, t)
        off -= e['grace']
        vel = v + R.gauss(0, 3.5)
        if limb == 'L' and not accent:
            vel *= 0.95
        vel = int(max(1, min(127, round(vel))))
        if e['dur'] is not None:
            dur = e['dur']
        elif e['v'] in LONG:
            dur = 1.4
        elif e['v'] in FEET:
            dur = 0.1
        else:
            dur = 0.12
        notes.append([max(0.0, t + off), NOTE[e['v']], vel, limb, dur])
    final_time = tb(final_beat) * scale + lead
    return resolve(notes), final_time


def resolve(notes):
    """Guarantee physical playability: each limb one stroke at a time,
    with a minimum interval between strokes of the same limb."""
    gap = {'R': 0.035, 'L': 0.035, 'RF': 0.085, 'LF': 0.1}
    notes.sort(key=lambda n: (n[0], -n[2], n[1]))
    out = []
    last = {'R': None, 'L': None, 'RF': None, 'LF': None}

    def free(h, t):
        li = last[h]
        return li is None or t - out[li][0] >= gap[h]

    for n in notes:
        limb = n[3]
        t = n[0]
        if limb in ('RF', 'LF'):
            if free(limb, t):
                out.append(n)
                last[limb] = len(out) - 1
            elif n[2] > out[last[limb]][2]:
                out[last[limb]] = None
                out.append(n)
                last[limb] = len(out) - 1
            continue
        other = 'L' if limb == 'R' else 'R'
        if free(limb, t):
            h = limb
        elif free(other, t):
            h = other
        else:
            h = min(('R', 'L'), key=lambda x: out[last[x]][2])
            if n[2] > out[last[h]][2] + 4:
                out[last[h]] = None
            else:
                continue
        n[3] = h
        out.append(n)
        last[h] = len(out) - 1
    return [n for n in out if n is not None]


def write_midi(notes, final_time, path='solo.mid'):
    tps = 960  # ticks per second at 120 bpm, 480 tpb
    mid = mido.MidiFile(ticks_per_beat=480, type=0)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=115, time=0))
    tr.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
    tr.append(mido.Message('control_change', channel=9, control=91, value=48, time=0))

    by_pitch = {}
    for n in notes:
        by_pitch.setdefault(n[1], []).append(n)
    evs = []
    for p in sorted(by_pitch):
        lst = sorted(by_pitch[p], key=lambda n: n[0])
        for i, n in enumerate(lst):
            on = n[0]
            off = on + n[4]
            if i + 1 < len(lst):
                off = min(off, lst[i + 1][0] - 0.002)
            on_t = int(round(on * tps))
            off_t = max(on_t + 1, int(round(off * tps)))
            if i + 1 < len(lst):
                nxt = int(round(lst[i + 1][0] * tps))
                if off_t > nxt:
                    off_t = nxt
                if off_t <= on_t:
                    off_t = on_t
            evs.append((on_t, 1, p, n[2]))
            evs.append((off_t, 0, p, 0))
    evs.sort(key=lambda e: (e[0], e[1], e[2]))
    cur = 0
    for tick, kind, p, vel in evs:
        d = tick - cur
        cur = tick
        if kind == 1:
            tr.append(mido.Message('note_on', channel=9, note=p, velocity=vel, time=d))
        else:
            tr.append(mido.Message('note_off', channel=9, note=p, velocity=0, time=d))
    end_tick = int(round((final_time + 2.9) * tps))
    tr.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - cur)))
    mid.save(path)


def main():
    S = compose()
    notes, final_time = render(S)
    write_midi(notes, final_time)


if __name__ == '__main__':
    main()
