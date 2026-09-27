#!/usr/bin/env python3
"""drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

The solo grows from one motif, "A". It is a 3+3+2 tom call (floor, high, mid),
answered by a snare flam, ghost notes, a kick and a two-tom pickup into the next
downbeat. The motif is:
  - stated and answered;
  - shrunk to 32nds;
  - turned into hemiolas and sextuplet cross-rhythms;
  - whispered on woodblocks and recast in 12/8;
  - blown up into cymbal hits and recapitulated;
  - finally used as the last three hits before the closing crash.

Every stroke belongs to a limb: R/L hands, K right foot, F left foot. A physical
pass keeps each limb to one stroke at a time, with travel time between
instruments. So at most two hands and two feet ever strike together.

A tempo map makes the pulse surge and settle. Micro-timing, flams, ghosts,
accents and crescendos make it a performance.

The output is deterministic: a fixed seed, no clock, no hash order.
"""
import bisect
import math
import random

import mido

SEED = 1959
rng = random.Random(SEED)

PPQ = 960
BEAT = PPQ
BAR = 4 * PPQ
S16, S8, T8, SX, S32, T32 = PPQ // 4, PPQ // 2, PPQ // 3, PPQ // 6, PPQ // 8, PPQ // 12

K1, K2 = 36, 35                       # right / left bass drum
SN = 38
HHC, HHP, HHO = 42, 44, 46
T1, T2, T3, T4, T5, T6 = 50, 48, 47, 45, 43, 41   # toms, high -> low
CR1, CR2, CHINA, SPLASH = 49, 57, 52, 55
RIDE, BELL, COWBELL = 51, 53, 56
WBH, WBL, TIMH, TIML = 76, 77, 65, 66
LINE = [SN, T1, T2, T3, T4, T5, T6]

FINAL_BAR = 54
TARGET_FINAL_SEC = 117.4
RING_SEC = 2.55
LEAD_SEC = 0.06

POS = {SN: (-0.30, 0.10), HHC: (-0.90, 0.30), HHO: (-0.90, 0.30),
       T1: (-0.25, 0.65), T2: (0.15, 0.72), T3: (0.45, 0.62), T4: (0.70, 0.30),
       T5: (0.85, 0.00), T6: (1.00, -0.30), CR1: (-0.80, 0.90), SPLASH: (-0.45, 1.00),
       CR2: (0.55, 1.00), RIDE: (1.05, 0.55), BELL: (1.00, 0.50), CHINA: (1.25, 0.90),
       COWBELL: (0.80, 0.85), WBH: (0.85, 0.75), WBL: (0.85, 0.70),
       TIMH: (-1.10, 0.55), TIML: (-1.10, 0.35)}
RIGHT_SIDE = (T4, T5, T6, RIDE, BELL, CR2, CHINA, COWBELL, WBH, WBL)
LEFT_SIDE = (T1, HHC, HHO, CR1, SPLASH, TIMH, TIML)

# ------------------------------------------------------------------ events
EV = []


def put(t, n, v, limb, kind='N', off=0.0):
    """kind: X hit, A accent, N normal, G ghost, g grace, R roll, T time. off in ms."""
    EV.append({'t': int(round(t)), 'n': int(n), 'v': float(v), 'limb': limb,
               'kind': kind, 'off': float(off), 'alive': True})


def oth(h):
    return 'L' if h == 'R' else 'R'


def B(bar, pos16=0.0):
    return int(round(bar * BAR + pos16 * S16))


def kick(t, v=96.0, kind='N', off=0.0, foot='K'):
    put(t, K1 if foot == 'K' else K2, v, foot, kind, off)


def hatfoot(t, v=54.0):
    put(t, HHP, v, 'F', 'T')


def flam(t, n, v, hand='R', gn=None, gv=None, kind='A'):
    put(t, n if gn is None else gn, (0.34 * v + 8.0) if gv is None else gv,
        oth(hand), 'g', -rng.uniform(17.0, 29.0))
    put(t, n, v, hand, kind)


def drag(t, n, v, hand='R', kind='A'):
    o, gv, gap = oth(hand), 0.30 * v + 8.0, rng.uniform(30.0, 36.0)
    put(t, n, gv, o, 'g', -(2.0 * gap + 4.0))
    put(t, n, gv * 0.92, o, 'g', -(gap + 4.0))
    put(t, n, v, hand, kind)


# ------------------------------------------------------------ tempo shape
TEMPO_KEYS, PUSHES, ARCS = [], [], []


def tkey(bar, bpm):
    TEMPO_KEYS.append((float(bar), float(bpm)))


def push(t0, t1, pct, release=BEAT):
    """Rush (pct > 0) or hold back (pct < 0) over [t0, t1), then settle."""
    PUSHES.append((int(t0), int(t1), float(pct), int(max(1, release))))


def arc(t0, t1, pct):
    ARCS.append((int(t0), int(t1), float(pct)))


# --------------------------------------------------------------- patterns
def expand(stick, n, start='R'):
    s = [c for c in stick if c in 'RLKF']
    out = [s[i % len(s)] for i in range(n)]
    if start == 'L':
        out = [oth(c) if c in 'RL' else c for c in out]
    return out


def ramp(n, v0, v1, curve=1.0):
    if n <= 1:
        return [float(v1)]
    return [v0 + (v1 - v0) * (i / (n - 1.0)) ** curve for i in range(n)]


def line_path(n, i0, i1, per=2):
    segs = max(1, (n + per - 1) // per)
    out = []
    for i in range(n):
        x = 0.0 if segs == 1 else (i // per) / (segs - 1.0)
        out.append(LINE[int(round(i0 + (i1 - i0) * x))])
    return out


def side_of(n):
    if n in RIGHT_SIDE:
        return 'R'
    if n in LEFT_SIDE:
        return 'L'
    return None


def run(t0, step, n, stick='RL', start='R', drums=None, v=(60.0, 90.0), curve=1.0,
        acc=None, acc_drums=None, boost=26.0, kick_acc=False, kick_v=100.0,
        rush=0.0, double_drop=6.0, kind='N'):
    """Sticking-driven run; 'K'/'F' strokes go to the bass drums."""
    st = expand(stick, n, start)
    vel = ramp(n, v[0], v[1], curve)
    cnt = {'R': 0, 'L': 0, '*': 0}
    for i in range(n):
        t = t0 + i * step
        off = -rush * i / max(1.0, n - 1.0)
        h = st[i]
        if h in ('K', 'F'):
            foot = 'F' if (h == 'F' or (i > 0 and st[i - 1] == 'K')) else 'K'
            kick(t, min(118.0, vel[i] + 10.0), 'N', off, foot)
            continue
        d = drums[i] if drums is not None else SN
        vv, k = vel[i], kind
        if acc is not None and acc[i % len(acc)]:
            vv += boost
            k = 'A'
            if acc_drums is not None:
                if isinstance(acc_drums, dict):
                    lst = acc_drums[h]
                    d = lst[cnt[h] % len(lst)]
                    cnt[h] += 1
                else:
                    d = acc_drums[cnt['*'] % len(acc_drums)]
                    cnt['*'] += 1
            if kick_acc:
                kick(t, kick_v, 'N', off)
        elif i > 0 and st[i - 1] == h:
            vv -= double_drop
        if k != 'A' and vv < 44.0:
            k = 'G'
        put(t, d, vv, h, k, off)
    return st


def roll(t0, t1, v0, v1, drum=SN, rate=T32, stick='RRLL', start='R', curve=1.5,
         hand_drums=None, acc_every=None, acc_from=None, boost=16.0, rush=0.0,
         kick_every=None, kick_v=(40.0, 100.0), kick_alt=False):
    """Double-stroke roll that swells; optional accents and kick pulse."""
    n = int((t1 - t0) // rate)
    st = expand(stick, n, start)
    origin = t0 if acc_from is None else acc_from
    for i in range(n):
        t = t0 + i * rate
        x = i / max(1.0, n - 1.0)
        vv = v0 + (v1 - v0) * x ** curve
        d = hand_drums[st[i]] if hand_drums is not None else drum
        k = 'R'
        if i > 0 and st[i] == st[i - 1]:
            vv -= 5.0
        if acc_every and i > 0 and t >= origin and (t - origin) % acc_every == 0:
            vv += boost
            k = 'A'
        put(t, d, vv, st[i], k, -rush * x)
    if kick_every:
        m = int((t1 - t0 + kick_every - 1) // kick_every)
        for j in range(m):
            y = j / max(1.0, m - 1.0)
            kick(t0 + j * kick_every, kick_v[0] + (kick_v[1] - kick_v[0]) * y, 'N',
                 -rush * y, 'F' if (kick_alt and j % 2 == 1) else 'K')


def motif_A(t0, orch=(T6, T1, T3), dyn=1.0, ghosts=0.0, answer='std', crash=False,
            kicks=(0, 12), hats=(), ghost_vel=(22.0, 34.0)):
    """The motif: 3+3+2 call on 16ths 0, 3, 6; answer from beat 3."""
    occ = {}

    def mark(p, hands):
        occ.setdefault(p, set()).update(hands)

    def P(p, n, v, h, kind='A'):
        put(t0 + p * S16, n, v, h, kind)
        mark(p, (h,))

    def PF(p, n, v, h, gn=None):
        flam(t0 + p * S16, n, v, h, gn)
        mark(p, ('R', 'L'))

    def gv():
        return rng.uniform(ghost_vel[0], ghost_vel[1])

    hands = ['R', 'L', 'R']
    for i, n in enumerate(orch):
        if side_of(n) is not None:
            hands[i] = side_of(n)
    for i, (p, n) in enumerate(zip((0, 3, 6), orch)):
        P(p, n, (112.0, 100.0, 105.0)[i] * dyn, hands[i], 'A')
    if crash:
        ch = oth(hands[0])
        P(0, CR1 if ch == 'L' else CR2, 116.0 * dyn, ch, 'X')
    gpos = [1, 2, 4, 5, 7, 9]
    if answer in ('std', 'std2', 'ruff'):
        PF(8, SN, 110.0 * dyn, 'R')
        P(10, SN, gv(), 'L', 'G')
        P(11, SN, gv(), 'R', 'G')
        if answer == 'std':
            P(14, T3, 86.0 * dyn, 'L', 'N')
            P(15, T6, 98.0 * dyn, 'R', 'A')
            gpos.append(13)
        elif answer == 'std2':
            P(14, T5, 96.0 * dyn, 'R', 'A')
            P(15, T3, 88.0 * dyn, 'L', 'N')
            gpos.append(13)
        else:
            for j, (n, h) in enumerate(((T3, 'R'), (T4, 'L'), (T5, 'R'), (T6, 'L'))):
                put(t0 + 14 * S16 + j * S32, n, (80.0 + 8.0 * j) * dyn, h,
                    'A' if j == 3 else 'N', -2.0 * j)
    elif answer == 'sext':
        PF(8, SN, 110.0 * dyn, 'R')
        P(10, SN, gv(), 'L', 'G')
        for j, n in enumerate((T1, T2, T3, T4, T5, T6)):
            put(t0 + 12 * S16 + j * SX, n, (84.0 + 5.0 * j) * dyn,
                'R' if j % 2 == 0 else 'L', 'A' if j in (0, 5) else 'N', -1.5 * j)
    elif answer == 'space':
        PF(8, SN, 108.0 * dyn, 'R')
        P(13, SN, gv(), 'L', 'G')
        gpos.append(11)
    elif answer == 'tomflam':
        PF(8, T3, 108.0 * dyn, 'R', SN)
        P(10, SN, gv(), 'L', 'G')
        P(11, SN, gv(), 'R', 'G')
        P(13, T1, 88.0 * dyn, 'L', 'N')
        PF(14, T5, 104.0 * dyn, 'R', T3)
    for p in kicks:
        kick(t0 + p * S16, (104.0 if p == 0 else 90.0) * dyn, 'A' if p == 0 else 'N')
    for p in hats:
        hatfoot(t0 + p * S16, 52.0)
    if ghosts > 0.0:
        for p in gpos:
            if rng.random() < ghosts:
                used = occ.get(p, set())
                h = 'L' if 'L' not in used else 'R'
                if h not in used:
                    put(t0 + p * S16, SN, gv(), h, 'G')
                    mark(p, (h,))


def response(t0, style, dyn=1.0):
    def P(p, n, v, h, kind='A'):
        put(t0 + p * S16, n, v if kind == 'G' else v * dyn, h, kind)
    if style == 0:
        kick(t0, 98.0 * dyn, 'A')
        P(0, SN, 104.0, 'L')
        P(2, SN, rng.uniform(26, 32), 'R', 'G')
        P(3, SN, rng.uniform(30, 36), 'L', 'G')
        P(4, SN, 100.0, 'R')
        kick(t0 + 6 * S16, 86.0 * dyn)
        P(7, T1, 94.0, 'L')
        P(8, T6, 106.0, 'R')
        kick(t0 + 8 * S16, 94.0 * dyn)
        if rng.random() < 0.7:
            P(11, SN, rng.uniform(24, 30), 'L', 'G')
        kick(t0 + 12 * S16, 72.0 * dyn)
        P(13, SN, rng.uniform(26, 32), 'R', 'G')
    else:
        kick(t0, 100.0 * dyn, 'A')
        P(0, T6, 102.0, 'R')
        P(1, SN, rng.uniform(26, 32), 'L', 'G')
        P(2, SN, rng.uniform(26, 32), 'R', 'G')
        P(3, SN, 102.0, 'L')
        P(5, SN, rng.uniform(26, 32), 'R', 'G')
        kick(t0 + 6 * S16, 90.0 * dyn)
        P(6, SN, rng.uniform(28, 34), 'L', 'G')
        P(7, SN, rng.uniform(30, 36), 'R', 'G')


def groove(t0, cym=HHC, kicks=(0, 3, 6, 10), gprob=0.5, backbeats=(4, 12), opens=(),
           acc=(0, 4, 8, 12), hh16=False, crash0=None, dyn=1.0, lo=0, hi=16,
           hat_pos=(), acc_note=None, swing=7.0,
           gcands=(1, 3, 6, 7, 9, 10, 11, 13, 14, 15)):
    """16th funk groove: R cymbal, L backbeats and ghosts, feet underneath."""
    closes, occL = [], set()
    for p in range(lo, hi, 1 if hh16 else 2):
        t = t0 + p * S16
        off = swing if p % 2 == 1 else 0.0
        if p == 0 and crash0 is not None:
            put(t, crash0, 112.0 * dyn, 'R', 'X')
            continue
        if p in opens:
            put(t, HHO, 82.0 * dyn + rng.uniform(-3, 3), 'R', 'T', off)
            closes.append(p + 2)
            continue
        if p in acc:
            n = acc_note if acc_note is not None else cym
            v = {HHC: 84.0, BELL: 90.0, COWBELL: 74.0}.get(n, 82.0)
        else:
            n = cym
            v = (58.0 if cym == HHC else 66.0) - (6.0 if hh16 and p % 2 == 1 else 0.0)
        put(t, n, v * dyn + rng.uniform(-4, 4), 'R', 'T', off)
    for p in backbeats:
        if lo <= p < hi:
            put(t0 + p * S16, SN, (108.0 + rng.uniform(-3, 3)) * dyn, 'L', 'A')
            occL.add(p)
    for p in gcands:
        if lo <= p < hi and p not in occL and rng.random() < gprob:
            put(t0 + p * S16, SN, rng.uniform(24.0, 38.0), 'L', 'G',
                swing if p % 2 == 1 else 0.0)
            occL.add(p)
    for p in kicks:
        if lo <= p < hi:
            v = 102.0 if p == 0 else (92.0 if p % 4 == 0 else 88.0)
            kick(t0 + p * S16, v * dyn, 'A' if p == 0 else 'N',
                 swing * 0.5 if p % 2 == 1 else 0.0)
    for p in hat_pos:
        if lo <= p < hi:
            hatfoot(t0 + p * S16, 54.0 + rng.uniform(-3, 3))
    for p in closes:
        hatfoot(t0 + p * S16, 60.0)


def hemiola(t0, groups, acc_notes, tap_v=(36.0, 52.0), acc_v=(96.0, 112.0), kick_at=()):
    """Groups of 3 (R-L-L), 2 (R-L), 4 (R-L-R-L); accents travel the kit."""
    strokes, pos = [], 0
    for gi, g in enumerate(groups):
        for j, h in enumerate({2: 'RL', 3: 'RLL', 4: 'RLRL'}[g]):
            strokes.append((pos + j, h, j == 0, gi))
        pos += g
    taps = ramp(len(strokes), tap_v[0], tap_v[1])
    accs = ramp(len(groups), acc_v[0], acc_v[1])
    for idx, (p, h, is_acc, gi) in enumerate(strokes):
        t = t0 + p * S16
        if is_acc:
            put(t, acc_notes[gi % len(acc_notes)], accs[gi], h, 'A')
        else:
            vv = taps[idx] - (4.0 if idx > 0 and strokes[idx - 1][1] == h else 0.0)
            put(t, SN, vv, h, 'G' if vv < 44.0 else 'N')
    for p in kick_at:
        kick(t0 + p * S16, 96.0)


def dim_cells(t0, cells, tap_v=(46.0, 62.0), acc_v=(96.0, 112.0)):
    """The 3+3+2 cell in 32nds, one cell per beat, alternating singles."""
    taps = ramp(8 * len(cells), tap_v[0], tap_v[1])
    accs = ramp(3 * len(cells), acc_v[0], acc_v[1])
    a = 0
    for c, cell in enumerate(cells):
        for j in range(8):
            i = c * 8 + j
            h = 'R' if i % 2 == 0 else 'L'
            if j in (0, 3, 6):
                d = cell[(0, 3, 6).index(j)]
                put(t0 + i * S32, d, accs[a], h, 'X' if d in (CR1, CR2, CHINA) else 'A')
                a += 1
            else:
                put(t0 + i * S32, SN, taps[i], h, 'G' if taps[i] < 44.0 else 'N')
        kick(t0 + c * 8 * S32, 94.0 + 3.0 * c)


def sext_cells(t0, cells, tap_v=(46.0, 68.0), acc_v=(98.0, 114.0), kicks='cells'):
    """The 3+3+2 cell in sextuplets: three cells = one bar, 3 against 4."""
    accp = {}
    for c, cell in enumerate(cells):
        for j, d in zip((0, 3, 6), cell):
            accp[c * 8 + j] = d
    n = 8 * len(cells)
    taps = ramp(n, tap_v[0], tap_v[1])
    order = sorted(accp)
    accs = ramp(len(order), acc_v[0], acc_v[1])
    for i in range(n):
        h = 'R' if i % 2 == 0 else 'L'
        t = t0 + i * SX
        if i in accp:
            k = order.index(i)
            put(t, accp[i], accs[k], h, 'X' if accp[i] in (CR1, CR2, CHINA) else 'A')
            if kicks == 'all':
                kick(t, 104.0 + k, 'N', 0.0, 'K' if k % 2 == 0 else 'F')
        else:
            put(t, SN, taps[i], h, 'G' if taps[i] < 44.0 else 'N')
    if kicks == 'cells':
        for c in range(len(cells)):
            kick(t0 + c * 8 * SX, 100.0 + 2.0 * c)


BELLPAT = (0, 2, 4, 5, 7, 9, 11)          # 12/8 standard bell


def bell(t0, note=COWBELL, lo=0, hi=12):
    base = 70.0 if note == COWBELL else 86.0
    for p in BELLPAT:
        if lo <= p < hi:
            put(t0 + p * T8, note, base + (8.0 if p in (0, 7) else 0.0) + rng.uniform(-4, 4),
                'R', 'T')


def tri_feet(t0, kicks=(0, 6), hats=(3, 9)):
    for p in kicks:
        kick(t0 + p * T8, (98.0 if p == 0 else 90.0) + rng.uniform(-3, 3))
    for p in hats:
        hatfoot(t0 + p * T8, 52.0 + rng.uniform(-3, 3))


def lh(t0, items):
    for p, n, kind, v in items:
        put(t0 + p * T8, n, v + rng.uniform(-3, 3), 'L', kind)


def dbass(t0, t1, step, v=(88.0, 100.0)):
    n = int((t1 - t0) // step)
    for i in range(n):
        t = t0 + i * step
        vv = v[0] + (v[1] - v[0]) * i / max(1.0, n - 1.0) + (8.0 if (t - t0) % BEAT == 0 else 0.0)
        kick(t, vv, 'N', 0.0, 'K' if i % 2 == 0 else 'F')


# --------------------------------------------------------------- sections
def sec1():
    """Bars 0-7: statement, answers, first development, roll into the groove."""
    for bar, bpm in ((0, 103.0), (1.5, 106.0), (4, 109.5), (7.9, 111.0)):
        tkey(bar, bpm)
    arc(B(0), B(4), 0.012)
    arc(B(4), B(8), 0.014)
    motif_A(B(0), orch=(T6, T1, T3), dyn=0.93, answer='std')
    response(B(1), 0, dyn=0.92)
    motif_A(B(2), orch=(T1, T3, T6), dyn=0.97, ghosts=0.18, answer='ruff')
    response(B(3), 1, dyn=0.95)
    run(B(3, 8), S16, 8, stick='LR', drums=line_path(8, 1, 6, 2), v=(72.0, 108.0), rush=5.0)
    kick(B(3, 8), 92.0)
    kick(B(3, 12), 100.0)
    push(B(3, 8), B(4), 0.02)
    motif_A(B(4), orch=(T6, T1, T3), dyn=1.0, ghosts=0.35, answer='sext', crash=True)
    hemiola(B(5), (3, 3, 3, 3, 2, 2), (T1, T2, T3, T4, T5, T6),
            tap_v=(34.0, 50.0), acc_v=(96.0, 110.0), kick_at=(0, 6, 12))
    t0 = B(6)
    dim_cells(t0, [(T6, T1, T3), (T5, T2, T4)], tap_v=(44.0, 58.0), acc_v=(98.0, 108.0))
    flam(t0 + 8 * S16, T3, 106.0, 'R', gn=SN)
    kick(t0 + 8 * S16, 98.0)
    flam(t0 + 10 * S16, T5, 108.0, 'R', gn=T4)
    put(t0 + 12 * S16, SN, 112.0, 'L', 'A')
    kick(t0 + 12 * S16, 94.0)
    put(t0 + 13 * S16, T4, 88.0, 'R', 'N')
    flam(t0 + 14 * S16, T6, 114.0, 'R', gn=T5)
    kick(t0 + 14 * S16, 104.0)
    t0 = B(7)
    roll(t0, t0 + 2 * BEAT, 24.0, 94.0, curve=1.4, kick_every=BEAT, kick_v=(40.0, 56.0))
    run(t0 + 2 * BEAT, SX, 12, stick='RL', drums=line_path(12, 1, 6, 2), v=(84.0, 114.0),
        acc=[1] + [0] * 11, boost=12.0, rush=6.0)
    kick(t0 + 2 * BEAT, 98.0)
    kick(t0 + 3 * BEAT, 106.0)
    push(t0, B(8), 0.025)


def sec2():
    """Bars 8-15: the groove; the motif hides in kick, hi-hat accents and bell."""
    tkey(8, 112.0)
    tkey(15.9, 112.5)
    arc(B(8), B(12), 0.008)
    arc(B(12), B(16), 0.010)
    groove(B(8), kicks=(0, 3, 6, 10), gprob=0.5, crash0=CR2)
    groove(B(9), kicks=(0, 3, 6, 11, 14), gprob=0.55, opens=(14,))
    groove(B(10), hh16=True, acc=(0, 3, 6, 8, 11, 14), kicks=(0, 6, 10), gprob=0.3)
    groove(B(11), kicks=(0, 3, 6), gprob=0.5, hi=8)
    t0 = B(11)
    flam(t0 + 8 * S16, SN, 108.0, 'R')
    kick(t0 + 8 * S16, 96.0)
    for p, n, h, k, v in ((9, SN, 'L', 'G', 30.0), (10, T1, 'R', 'A', 96.0),
                          (11, SN, 'L', 'G', 34.0), (12, T3, 'R', 'A', 100.0),
                          (13, SN, 'L', 'G', 38.0), (14, T5, 'R', 'A', 104.0),
                          (15, SN, 'L', 'A', 106.0)):
        put(t0 + p * S16, n, v, h, k)
    kick(t0 + 12 * S16, 92.0)
    push(t0 + 8 * S16, B(12), 0.018)
    groove(B(12), cym=RIDE, acc=(0, 6, 12), acc_note=BELL, kicks=(0, 7, 10),
           hat_pos=(4, 12), gprob=0.45)
    put(B(12), SPLASH, 96.0, 'L', 'A')
    groove(B(13), cym=RIDE, acc=(0, 6, 12), acc_note=COWBELL, kicks=(0, 3, 6, 10, 13),
           hat_pos=(4, 12), gprob=0.6)
    motif_A(B(14), orch=(T6, T1, T3), ghosts=0.4, answer='tomflam', kicks=(0, 8), hats=(4, 12))
    t0 = B(15)
    run(t0, SX, 12, stick='RLRRLL', v=(48.0, 66.0), acc=[1, 0, 0, 0, 0, 0],
        acc_drums=[T1, T3], boost=40.0)
    kick(t0, 98.0)
    kick(t0 + BEAT, 94.0)
    run(t0 + 2 * BEAT, S32, 16, stick='RL',
        drums=[SN, SN, T1, T1, T2, T2, T3, T3, T4, T4, T5, T5, T6, T6, T5, T6],
        v=(76.0, 112.0), acc=[1, 0, 0, 0], boost=12.0, rush=8.0)
    kick(t0 + 2 * BEAT, 100.0)
    kick(t0 + 3 * BEAT, 106.0)
    push(t0 + BEAT, B(16), 0.022)


def sec3():
    """Bars 16-23: travelling around the kit, density and pulse rising."""
    for bar, bpm in ((16, 113.0), (19.5, 115.5), (23.5, 119.0)):
        tkey(bar, bpm)
    arc(B(16), B(20), 0.010)
    arc(B(20), B(24), 0.012)
    t0 = B(16)
    put(t0, CHINA, 114.0, 'R', 'X')
    kick(t0, 108.0, 'A')
    run(t0 + S16, S16, 15, stick='LR', v=(44.0, 64.0),
        acc=[1 if (i + 1) in (3, 6, 9, 12) else 0 for i in range(15)],
        acc_drums={'L': [T1, T2], 'R': [T5, T6]}, boost=46.0)
    for p, v in ((4, 80.0), (6, 88.0), (8, 84.0), (12, 92.0)):
        kick(t0 + p * S16, v)
    path = [SN, T1, T2, T3, T4, T5, T6, T5]
    run(B(17), S16, 16, stick='RRLL', drums=[d for d in path for _ in (0, 1)],
        v=(56.0, 80.0), acc=[1, 0, 0, 0], boost=28.0, kick_acc=True, kick_v=96.0)
    run(B(18), S16, 16, stick='RLRRLRLL', v=(58.0, 82.0), acc=[1, 0, 0, 0],
        acc_drums={'R': [T6, T5], 'L': [T1, T2]}, boost=32.0, kick_acc=True, kick_v=98.0)
    t0 = B(19)
    run(t0, SX, 12, stick='RL', drums=[T1, T1, T1, T3, T3, T3, T4, T4, T4, T6, T6, T6],
        v=(80.0, 100.0), acc=[1, 0, 0], boost=14.0)
    kick(t0, 100.0)
    kick(t0 + BEAT, 98.0)
    flam(t0 + 8 * S16, T6, 106.0, 'R')
    kick(t0 + 8 * S16, 100.0)
    put(t0 + 9 * S16, SN, 40.0, 'L', 'G')
    put(t0 + 10 * S16, SN, 44.0, 'R', 'G')
    flam(t0 + 11 * S16, T1, 104.0, 'L', gn=T2)
    kick(t0 + 11 * S16, 98.0)
    put(t0 + 12 * S16, SN, 46.0, 'R', 'N')
    put(t0 + 13 * S16, SN, 48.0, 'L', 'N')
    flam(t0 + 14 * S16, T3, 110.0, 'R', gn=SN)
    kick(t0 + 14 * S16, 104.0)
    put(t0 + 15 * S16, SN, 54.0, 'L', 'N')
    tpath = [T2, T3, T4, T5, T6, T5, T4, T3]
    run(B(20), SX, 24, stick='RLK', drums=[tpath[i // 3] if i % 3 == 0 else SN for i in range(24)],
        v=(64.0, 98.0), acc=[1, 0, 0], boost=22.0)
    t0 = B(21)
    run(t0, SX, 18, stick='RLRRLL', v=(56.0, 76.0), acc=[1, 0, 0, 0, 0, 0],
        acc_drums=[T1, T3, T5], boost=40.0)
    for b in range(3):
        kick(t0 + b * BEAT, 96.0 + 3.0 * b)
    run(t0 + 3 * BEAT, S32, 8, stick='RL', drums=[T2, T2, T3, T3, T5, T5, T6, T6],
        v=(84.0, 112.0), rush=6.0)
    kick(t0 + 3 * BEAT, 104.0)
    push(t0 + 2 * BEAT, B(22), 0.02)
    sext_cells(B(22), [(T6, T1, T3), (T5, T2, T4), (T4, SN, T6)],
               tap_v=(46.0, 68.0), acc_v=(98.0, 114.0))
    t0 = B(23)
    drums = [SN, SN, T1, T1, T2, T2, T3, T3, T4, T4, T5, T5, T6, T6, T5, T5,
             T4, T4, T3, T3, T2, T2, T1, T1]
    run(t0, S32, 24, stick='RL', drums=drums, v=(70.0, 110.0), acc=[1] + [0] * 7,
        boost=16.0, rush=8.0)
    for b in range(3):
        kick(t0 + b * BEAT, 100.0 + 4.0 * b)
    flam(t0 + 12 * S16, SN, 114.0, 'R', gn=T1)
    kick(t0 + 12 * S16, 110.0)
    flam(t0 + 14 * S16, T6, 118.0, 'R', gn=T5)
    kick(t0 + 14 * S16, 112.0)
    push(t0, t0 + 3 * BEAT, 0.025, release=S8)
    push(t0 + 3 * BEAT, B(24), -0.03, release=S8)


def sec4():
    """Bars 24-30: the crash rings, subito piano, whispers, a two-bar roll swell."""
    for bar, bpm in ((24, 117.5), (25.5, 110.0), (28.5, 108.5), (30.9, 112.0)):
        tkey(bar, bpm)
    arc(B(25), B(29), 0.008)
    t0 = B(24)
    put(t0, CR1, 122.0, 'L', 'X')
    put(t0, CR2, 124.0, 'R', 'X')
    kick(t0, 122.0, 'X')
    kick(t0, 116.0, 'X', 0.0, 'F')
    hatfoot(t0 + 4 * S16, 44.0)
    hatfoot(t0 + 12 * S16, 46.0)
    acc = [0] * 12
    acc[5] = 1
    run(t0 + 2 * BEAT, SX, 12, stick='RL', v=(20.0, 30.0), acc=acc, boost=34.0)
    kick(t0 + 2 * BEAT, 40.0)
    t0 = B(25)                                   # the motif on woodblocks
    for p, n, v in ((0, WBL, 72.0), (3, WBH, 66.0), (6, WBL, 70.0), (14, WBH, 62.0)):
        put(t0 + p * S16, n, v, 'R', 'A')
    flam(t0 + 8 * S16, SN, 66.0, 'R', gv=28.0)
    for p in (1, 2, 4, 5, 7, 9, 10, 11, 12, 13, 15):
        if rng.random() < 0.75:
            put(t0 + p * S16, SN, rng.uniform(16.0, 28.0), 'L', 'G')
    kick(t0, 46.0)
    kick(t0 + 8 * S16, 40.0)
    hatfoot(t0 + 4 * S16, 46.0)
    hatfoot(t0 + 12 * S16, 48.0)
    t0 = B(26)                                   # ghost sextuplets, accents in 4s
    run(t0, SX, 24, stick='RL', v=(20.0, 30.0), acc=[1, 0, 0, 0], boost=38.0)
    kick(t0, 40.0)
    kick(t0 + 12 * S16, 44.0)
    hatfoot(t0 + 4 * S16, 46.0)
    hatfoot(t0 + 12 * S16, 48.0)
    motif_A(B(27), orch=(T6, T1, T3), dyn=0.58, ghosts=0.6, ghost_vel=(16.0, 26.0),
            answer='space', kicks=(0,), hats=(4, 12))
    t0 = B(28)                                   # drag taps, then woodblock tresillo
    drag(t0, SN, 62.0, 'R')
    put(t0 + 1 * S16, SN, 34.0, 'L', 'G')
    drag(t0 + 2 * S16, SN, 58.0, 'L')
    put(t0 + 3 * S16, SN, 32.0, 'R', 'G')
    drag(t0 + 4 * S16, SN, 66.0, 'R')
    put(t0 + 5 * S16, SN, 36.0, 'L', 'G')
    drag(t0 + 6 * S16, SN, 70.0, 'L')
    put(t0 + 7 * S16, SN, 38.0, 'L', 'G')
    for p, n, v in ((8, WBH, 70.0), (11, WBL, 68.0), (14, WBH, 74.0)):
        put(t0 + p * S16, n, v, 'R', 'A')
    for p in (9, 10, 12, 13, 15):
        put(t0 + p * S16, SN, rng.uniform(22.0, 30.0), 'L', 'G')
    kick(t0, 44.0)
    kick(t0 + 8 * S16, 42.0)
    hatfoot(t0 + 4 * S16, 48.0)
    hatfoot(t0 + 12 * S16, 50.0)
    t0 = B(29)                                   # the long roll swells
    roll(t0, B(30, 14), 22.0, 112.0, curve=1.8, acc_every=3 * S16, acc_from=B(30),
         boost=14.0, kick_every=BEAT, kick_v=(36.0, 104.0))
    for b in (29, 30):
        hatfoot(B(b, 4), 50.0)
        hatfoot(B(b, 12), 54.0)
    flam(B(30, 14), SN, 120.0, 'R')
    kick(B(30, 14), 112.0)
    push(t0, B(30, 12), 0.035, release=S8)
    push(B(30, 12), B(31), -0.035, release=BEAT)


def sec5():
    """Bars 31-38: 12/8 bell groove; the motif becomes quarter-note triplets."""
    tkey(31, 112.5)
    tkey(38.9, 114.0)
    arc(B(31), B(35), 0.009)
    arc(B(35), B(39), 0.011)
    t0 = B(31)
    put(t0, CR2, 116.0, 'R', 'X')
    kick(t0, 112.0, 'A')
    bell(t0, COWBELL, lo=2)
    tri_feet(t0, kicks=(6,))
    lh(t0, [(3, SN, 'G', 30.0), (6, SN, 'A', 94.0), (8, SN, 'G', 28.0), (10, T1, 'N', 72.0)])
    t0 = B(32)
    bell(t0, COWBELL)
    tri_feet(t0)
    lh(t0, [(0, SN, 'A', 90.0), (2, T1, 'A', 86.0), (4, T2, 'A', 90.0), (6, SN, 'G', 30.0),
            (8, SN, 'G', 32.0), (10, SN, 'A', 94.0), (11, SN, 'G', 28.0)])
    t0 = B(33)
    bell(t0, COWBELL)
    tri_feet(t0, kicks=(0, 6, 10))
    lh(t0, [(1, SN, 'A', 94.0), (3, SN, 'G', 28.0), (5, T1, 'A', 90.0), (7, SN, 'G', 30.0),
            (9, SN, 'A', 98.0), (10, SN, 'G', 26.0), (11, T2, 'N', 78.0)])
    t0 = B(34)                                   # motif in triplets, both hands
    put(t0, T6, 106.0, 'R', 'A')
    kick(t0, 104.0, 'A')
    put(t0 + 2 * T8, T1, 96.0, 'L', 'A')
    put(t0 + 4 * T8, T3, 100.0, 'R', 'A')
    flam(t0 + 6 * T8, SN, 108.0, 'R')
    kick(t0 + 6 * T8, 96.0)
    put(t0 + 7 * T8, SN, 32.0, 'L', 'G')
    put(t0 + 8 * T8, SN, 30.0, 'R', 'G')
    kick(t0 + 9 * T8, 92.0)
    put(t0 + 10 * T8, T3, 88.0, 'L', 'N')
    put(t0 + 11 * T8, T6, 100.0, 'R', 'A')
    hatfoot(t0 + 3 * T8, 52.0)
    hatfoot(t0 + 9 * T8, 52.0)
    t0 = B(35)                                   # ride bell and timbales
    bell(t0, BELL)
    tri_feet(t0)
    lh(t0, [(1, TIMH, 'A', 84.0), (3, TIMH, 'G', 40.0), (5, TIML, 'N', 70.0),
            (6, TIML, 'A', 92.0), (8, TIMH, 'N', 66.0), (10, TIML, 'A', 90.0),
            (11, TIMH, 'G', 42.0)])
    t0 = B(36)                                   # six-stroke rolls, bell returns
    run(t0, SX, 12, stick='RLLRRL', v=(46.0, 60.0), acc=[1, 0, 0, 0, 0, 1],
        acc_drums={'R': [T4, T6], 'L': [T1, T2]}, boost=44.0)
    kick(t0, 100.0)
    kick(t0 + BEAT, 96.0)
    bell(t0, BELL, lo=7)
    lh(t0, [(6, T1, 'A', 92.0), (8, SN, 'G', 30.0), (10, T2, 'A', 88.0)])
    tri_feet(t0, kicks=(6,))
    t0 = B(37)
    bell(t0, COWBELL, hi=6)
    lh(t0, [(1, SN, 'G', 30.0), (3, SN, 'A', 92.0), (4, SN, 'G', 28.0)])
    flam(t0 + 6 * T8, T5, 106.0, 'R', gn=T4)
    flam(t0 + 8 * T8, T3, 104.0, 'R', gn=T2)
    flam(t0 + 10 * T8, T1, 102.0, 'L', gn=T2)
    put(t0 + 11 * T8, T6, 108.0, 'R', 'A')
    tri_feet(t0, kicks=(0, 6, 9), hats=(3,))
    t0 = B(38)
    run(t0, SX, 18, stick='RLRRLL', v=(58.0, 80.0), acc=[1, 0, 0, 0, 0, 0],
        acc_drums=[T1, T3, T5], boost=40.0)
    for b in range(3):
        kick(t0 + b * BEAT, 98.0 + 3.0 * b)
    hatfoot(t0 + BEAT, 50.0)
    for j, (n, g) in enumerate(((T4, SN), (T5, T4), (T6, T5))):
        flam(t0 + (9 + j) * T8, n, 110.0 + 4.0 * j, 'R', gn=g)
        kick(t0 + (9 + j) * T8, 106.0 + 2.0 * j)
    push(t0 + 2 * BEAT, B(39), 0.025)


def sec6():
    """Bars 39-46: double bass, the motif in cymbals and cross-rhythms, a break."""
    for bar, bpm in ((39, 116.0), (41.5, 119.0), (44.9, 121.0), (45.5, 119.0), (46.9, 120.0)):
        tkey(bar, bpm)
    arc(B(39), B(42), 0.010)
    arc(B(42), B(45), 0.012)
    t0 = B(39)                                   # 3+3+2 in eighths as cymbal hits
    dbass(t0, t0 + BAR, S16, v=(86.0, 100.0))
    put(t0, CR1, 120.0, 'L', 'X')
    put(t0, CR2, 118.0, 'R', 'X')
    for p, n, h, v in ((2, T1, 'L', 82.0), (3, T1, 'R', 86.0), (4, T2, 'L', 90.0),
                       (5, T2, 'R', 94.0), (8, T3, 'L', 84.0), (9, T3, 'R', 88.0),
                       (10, T4, 'L', 92.0), (11, T4, 'R', 96.0), (15, T3, 'L', 98.0)):
        put(t0 + p * S16, n, v, h, 'N')
    put(t0 + 6 * S16, CHINA, 116.0, 'R', 'X')
    put(t0 + 6 * S16, SN, 112.0, 'L', 'A')
    put(t0 + 12 * S16, CR2, 118.0, 'R', 'X')
    put(t0 + 12 * S16, T5, 104.0, 'L', 'A')
    put(t0 + 14 * S16, T6, 110.0, 'R', 'A')
    t0 = B(40)                                   # triplet flams over double bass
    dbass(t0, t0 + 2 * BEAT, SX, v=(84.0, 96.0))
    for j, n in enumerate((T1, T2, T3, T4, T5, T6)):
        flam(t0 + j * T8, n, 100.0 + 3.0 * j, 'R')
    kick(t0 + 2 * BEAT, 108.0, 'A')
    kick(t0 + 3 * BEAT, 104.0)
    run(t0 + 2 * BEAT, S32, 16, stick='RL',
        drums=[T6, T6, T5, T5, T4, T4, T3, T3, T2, T2, T1, T1, SN, SN, SN, SN],
        v=(76.0, 112.0), acc=[1] + [0] * 7, boost=12.0, rush=6.0)
    t0 = B(41)                                   # linear hands-feet 32nds
    acc_notes, tom_notes = (CR2, T3, T1, T5, CHINA), (T4, T2, T2, T6, T3)
    vel = ramp(32, 74.0, 112.0)
    i = 0
    for gi, g in enumerate((6, 6, 6, 6, 8)):
        pat = 'RLRLKK' if g == 6 else 'RLRLRLKK'
        for j, c in enumerate(pat):
            t = t0 + i * S32
            if c == 'K':
                kick(t, min(118.0, vel[i] + 8.0), 'N', 0.0, 'F' if pat[j - 1] == 'K' else 'K')
            elif c == 'R':
                if j == 0:
                    put(t, acc_notes[gi], vel[i] + 18.0, 'R', 'A')
                else:
                    put(t, tom_notes[gi], vel[i], 'R', 'N')
            else:
                put(t, SN, vel[i] - 8.0, 'L', 'N')
            i += 1
    push(t0, B(42), 0.015)
    motif_A(B(42), orch=(T6, T1, T3), dyn=1.1, ghosts=0.2, answer='ruff', crash=True, kicks=())
    dbass(B(42), B(43), S8, v=(94.0, 104.0))
    sext_cells(B(43), [(CR2, T1, T3), (T6, T2, T4), (CHINA, SN, T6)],
               tap_v=(50.0, 72.0), acc_v=(104.0, 120.0), kicks='all')
    t0 = B(44)
    vel = ramp(24, 80.0, 116.0)
    for b, notes in enumerate(((T1, T1, T2, T2), (T3, T3, T4, T4), (T5, T5, T6, T6),
                               (SN, SN, T6, T6))):
        base = b * 6
        for j in range(4):
            put(t0 + (base + j) * SX, notes[j], vel[base + j] + (10.0 if j == 0 else 0.0),
                'R' if j % 2 == 0 else 'L', 'A' if j == 0 else 'N')
        kick(t0 + (base + 4) * SX, vel[base + 4] + 6.0)
        if b < 3:
            kick(t0 + (base + 5) * SX, vel[base + 5] + 6.0, 'N', 0.0, 'F')
    push(t0, B(45), 0.02)
    t0 = B(45)                                   # the break
    put(t0, CR1, 124.0, 'L', 'X')
    put(t0, CR2, 124.0, 'R', 'X')
    kick(t0, 120.0, 'X')
    kick(t0, 114.0, 'X', 0.0, 'F')
    put(t0 + 6 * S16, CHINA, 120.0, 'R', 'X')
    put(t0 + 6 * S16, SN, 116.0, 'L', 'X')
    kick(t0 + 6 * S16, 118.0, 'X')
    hatfoot(t0 + 8 * S16, 50.0)
    hatfoot(t0 + 12 * S16, 54.0)
    put(t0 + 13 * S16, SN, 34.0, 'L', 'G')
    put(t0 + 14 * S16, SN, 70.0, 'R', 'N')
    put(t0 + 15 * S16, SN, 92.0, 'L', 'A')
    push(t0 + 6 * S16, t0 + 13 * S16, -0.035, release=S8)
    t0 = B(46)                                   # the answer: 32nd doubles around
    path = [SN, T1, T2, T3, T4, T5, T6, T5, T4, T3, T2, T1]
    run(t0, S32, 24, stick='RRLL', drums=[d for d in path for _ in (0, 1)],
        v=(68.0, 106.0), acc=[1] + [0] * 7, boost=14.0, double_drop=5.0, rush=6.0)
    for b in range(3):
        kick(t0 + b * BEAT, 100.0 + 3.0 * b)
    put(t0 + 12 * S16, T6, 112.0, 'R', 'A')
    kick(t0 + 12 * S16, 110.0)
    flam(t0 + 13 * S16, T1, 108.0, 'L', gn=T4)
    flam(t0 + 14 * S16, T5, 116.0, 'R', gn=T3)
    kick(t0 + 14 * S16, 112.0)
    push(t0, B(47), 0.02)


def sec7():
    """Bars 47-53: recapitulation, final roll, motif as the last hits; bar 54: the end."""
    for bar, bpm in ((47, 119.5), (50.9, 120.0), (52.3, 116.0), (53.2, 108.0),
                     (54, 100.0), (56, 100.0)):
        tkey(bar, bpm)
    arc(B(47), B(51), 0.010)
    motif_A(B(47), orch=(T6, T1, T3), dyn=1.12, ghosts=0.3, answer='std2', crash=True)
    t0 = B(48)                                   # the motif in cymbals
    put(t0, CHINA, 118.0, 'R', 'X')
    put(t0, SN, 106.0, 'L', 'A')
    kick(t0, 112.0, 'A')
    put(t0 + 3 * S16, SPLASH, 102.0, 'L', 'A')
    put(t0 + 6 * S16, CR2, 116.0, 'R', 'X')
    kick(t0 + 6 * S16, 106.0)
    flam(t0 + 8 * S16, SN, 112.0, 'R')
    put(t0 + 10 * S16, SN, 34.0, 'L', 'G')
    kick(t0 + 12 * S16, 100.0)
    for j, n in enumerate((T1, T2, T3, T4, T5, T6)):
        put(t0 + 12 * S16 + j * SX, n, 90.0 + 5.0 * j, 'R' if j % 2 == 0 else 'L',
            'A' if j == 0 else 'N', -1.5 * j)
    dim_cells(B(49), [(T6, T1, T3), (T5, T2, T4), (T4, T1, T5), (CR2, SN, T5)],
              tap_v=(52.0, 76.0), acc_v=(100.0, 118.0))
    t0 = B(50)                                   # hemiola with cymbals and kick
    accs = {0: (CR2, 118.0), 3: (CR1, 116.0), 6: (T6, 114.0), 9: (SN, 118.0), 12: (CHINA, 122.0)}
    taps = {13: T1, 14: T3, 15: T5}
    tv = ramp(16, 60.0, 86.0)
    for p in range(16):
        h = 'R' if p % 2 == 0 else 'L'
        if p in accs:
            n, v = accs[p]
            put(t0 + p * S16, n, v, h, 'X' if n in (CR1, CR2, CHINA) else 'A')
            kick(t0 + p * S16, 106.0 + p)
        else:
            put(t0 + p * S16, taps.get(p, SN), tv[p], h, 'N')
    roll(B(51), B(52), 66.0, 100.0, curve=1.2, acc_every=3 * S16, boost=16.0,
         kick_every=BEAT, kick_v=(92.0, 104.0))
    roll(B(52), B(53) - 2 * T32, 98.0, 124.0, hand_drums={'R': T6, 'L': T5}, curve=1.0,
         kick_every=S8, kick_v=(96.0, 118.0), kick_alt=True)
    push(B(51), B(52), 0.02, release=S8)
    t0 = B(53)

    def S(i):
        return t0 + int(round(i * SX))

    for idx, (lnote, rnote) in ((0, (CR1, CR2)), (9, (SN, CHINA)), (18, (SN, CR2))):
        put(S(idx), lnote, 118.0, 'L', 'X')
        put(S(idx), rnote, 124.0, 'R', 'X')
        kick(S(idx), 122.0, 'X')
        kick(S(idx), 116.0, 'X', 0.0, 'F')
    put(S(6), SN, 62.0, 'R', 'N')
    put(S(7), SN, 80.0, 'L', 'N')
    for i, n, h, v in ((12, T6, 'R', 72.0), (13, T5, 'L', 82.0), (14, T6, 'R', 92.0),
                       (15, T5, 'L', 100.0), (16, T6, 'R', 108.0)):
        put(S(i), n, v, h, 'N')
    for i, n, h, v in ((19.0, T1, 'L', 100.0), (19.5, T2, 'R', 104.0), (20.0, T3, 'L', 108.0),
                       (20.5, T4, 'R', 112.0), (21.0, T5, 'L', 116.0), (21.5, T6, 'R', 120.0)):
        put(S(i), n, v, h, 'A')
    tf = B(FINAL_BAR)                            # the final hit: two hands, two feet
    put(tf, CR1, 127.0, 'L', 'X')
    put(tf, CR2, 127.0, 'R', 'X')
    kick(tf, 127.0, 'X')
    kick(tf, 124.0, 'X', 0.0, 'F')


def ensure_unique_bars():
    """A soloist rarely plays the same bar twice: vary any exact repeat."""
    seen = set()
    for b in range(FINAL_BAR + 1):
        lo, hi = B(b), B(b + 1)
        sig = None
        for _ in range(8):
            sig = tuple(sorted((e['t'] - lo, e['n']) for e in EV
                               if lo <= e['t'] < hi and e['kind'] != 'g'))
            if sig not in seen:
                break
            cands = list(range(16))
            rng.shuffle(cands)
            placed = False
            for p in cands:
                tp = lo + p * S16
                if not any(e['limb'] in ('R', 'L') and abs(e['t'] - tp) < S16 for e in EV):
                    put(tp, SN, rng.uniform(22.0, 30.0), 'L', 'G')
                    placed = True
                    break
            if not placed:
                break
        seen.add(sig)


# ------------------------------------------------------------ performance
KT = {'X': (-1.5, 2.2), 'A': (-2.0, 3.0), 'N': (0.0, 4.0), 'G': (4.5, 5.5),
      'g': (0.0, 1.5), 'R': (0.0, 2.0), 'T': (0.5, 3.2)}      # bias ms, jitter sd
LT = {'R': (-0.5, 1.0), 'L': (1.5, 1.2), 'K': (-1.0, 0.9), 'F': (2.0, 1.3)}
VS = {'X': 2.0, 'A': 4.0, 'N': 5.0, 'G': 3.0, 'g': 3.0, 'R': 3.0, 'T': 4.0}
PRIO = {'X': 6, 'A': 5, 'T': 4, 'N': 3, 'R': 3, 'G': 2, 'g': 1}
DUR = {K1: 0.3, K2: 0.3, SN: 0.3, HHC: 0.14, HHP: 0.14, HHO: 0.5, T1: 0.55, T2: 0.6,
       T3: 0.65, T4: 0.7, T5: 0.8, T6: 0.9, CR1: 2.6, CR2: 2.6, CHINA: 2.2, SPLASH: 1.4,
       RIDE: 1.8, BELL: 1.5, COWBELL: 0.4, WBH: 0.2, WBL: 0.2, TIMH: 0.45, TIML: 0.5}


def keyed_bpm(bar_f, keys):
    if bar_f <= keys[0][0]:
        return keys[0][1]
    for i in range(len(keys) - 1):
        a, va = keys[i]
        b, vb = keys[i + 1]
        if bar_f <= b:
            if b - a < 1e-9:
                return vb
            x = (bar_f - a) / (b - a)
            return va + (vb - va) * (0.5 - 0.5 * math.cos(math.pi * x))
    return keys[-1][1]


def tempo_factor(t, noise):
    f = 1.0
    for a, b, pct, rel in PUSHES:
        if a <= t < b:
            f += pct * (0.5 - 0.5 * math.cos(math.pi * (t - a) / float(b - a)))
        elif b <= t < b + rel:
            f += pct * (1.0 - (t - b) / float(rel)) ** 2
    for a, b, pct in ARCS:
        if a <= t < b:
            f += pct * math.sin(math.pi * (t - a) / float(b - a))
    return f + noise(t)


def min_gap(limb, a, b):
    """Seconds a limb needs between two strokes (travel between instruments)."""
    if limb in ('R', 'L'):
        if a['n'] == b['n']:
            return 0.028
        xa, ya = POS.get(a['n'], (0.0, 0.5))
        xb, yb = POS.get(b['n'], (0.0, 0.5))
        return 0.045 + 0.050 * math.hypot(xa - xb, ya - yb)
    if limb == 'K':
        return 0.070
    return 0.080 if a['n'] == b['n'] else 0.200


def render(path):
    keys = sorted(TEMPO_KEYS, key=lambda kv: kv[0])
    nph = [rng.uniform(0.0, 2.0 * math.pi) for _ in range(3)]

    def tnoise(t):
        x = t / float(BAR)
        return (0.004 * math.sin(2.0 * math.pi * x / 5.3 + nph[0])
                + 0.0025 * math.sin(2.0 * math.pi * x / 2.1 + nph[1])
                + 0.0015 * math.sin(2.0 * math.pi * x / 0.93 + nph[2]))

    n_steps = (FINAL_BAR + 2) * 16
    raw = []
    for j in range(n_steps):
        tm = j * S16 + S16 // 2
        raw.append(keyed_bpm(tm / float(BAR), keys) * tempo_factor(tm, tnoise))
    raw_sec = sum(15.0 / raw[j] for j in range(FINAL_BAR * 16))
    scale = raw_sec / (TARGET_FINAL_SEC - LEAD_SEC)
    us = [int(round(60000000.0 / (r * scale))) for r in raw]
    cum = [0.0]
    for j in range(n_steps):
        cum.append(cum[-1] + us[j] / 4.0e6)

    def t2s(t):
        j = int(t // S16)
        if j >= n_steps:
            return cum[n_steps] + (t - n_steps * S16) / float(PPQ) * us[-1] / 1.0e6
        j = max(j, 0)
        return cum[j] + (t - j * S16) / float(PPQ) * us[j] / 1.0e6

    def s2t(s):
        if s <= 0.0:
            return 0.0
        if s >= cum[n_steps]:
            return n_steps * S16 + (s - cum[n_steps]) * 1.0e6 / us[-1] * PPQ
        j = max(0, min(bisect.bisect_right(cum, s) - 1, n_steps - 1))
        return j * S16 + (s - cum[j]) * 1.0e6 / us[j] * PPQ

    ph = [rng.uniform(0.0, 2.0 * math.pi) for _ in range(4)]

    def drift(sec, foot):
        d = (2.6 * math.sin(2.0 * math.pi * sec / 6.9 + ph[0])
             + 1.7 * math.sin(2.0 * math.pi * sec / 3.1 + ph[1])
             + 0.9 * math.sin(2.0 * math.pi * sec / 1.37 + ph[2]))
        if foot:
            d = 0.7 * d + 1.1 * math.sin(2.0 * math.pi * sec / 4.3 + ph[3])
        return d

    for e in sorted(EV, key=lambda x: (x['t'], x['n'], x['limb'])):
        base = t2s(e['t'])
        kb, ksd = KT[e['kind']]
        lb, lsd = LT[e['limb']]
        off = (e['off'] + kb + lb + drift(base, e['limb'] in ('K', 'F'))
               + rng.gauss(0.0, ksd * lsd))
        e['sec'] = LEAD_SEC + max(0.0, base + off / 1000.0)
        v = e['v'] + rng.gauss(0.0, VS[e['kind']])
        if e['limb'] == 'L' and e['kind'] in ('N', 'G', 'R', 'T'):
            v -= 2.5
        e['vel'] = max(1, min(127, int(round(v))))

    # Physical pass: one stroke per limb at a time, with travel time.
    dropped = 0
    for limb in ('R', 'L', 'K', 'F'):
        kept = []
        for e in sorted([x for x in EV if x['limb'] == limb], key=lambda x: (x['sec'], x['n'])):
            ok = True
            while kept and e['sec'] - kept[-1]['sec'] < min_gap(limb, kept[-1], e):
                p = kept[-1]
                dropped += 1
                if (PRIO[e['kind']], e['vel']) > (PRIO[p['kind']], p['vel']):
                    p['alive'] = False
                    kept.pop()
                else:
                    e['alive'] = False
                    ok = False
                    break
            if ok:
                kept.append(e)

    alive = [e for e in EV if e['alive']]
    for e in alive:
        e['tick'] = int(round(s2t(e['sec'])))
    alive.sort(key=lambda x: (x['tick'], x['n'], -x['vel']))
    notes, seen = [], set()
    for e in alive:
        key = (e['tick'], e['n'])
        if key not in seen:
            seen.add(key)
            notes.append(e)
    final_sec = LEAD_SEC + t2s(B(FINAL_BAR))
    by_note = {}
    for e in notes:
        by_note.setdefault(e['n'], []).append(e)
    msgs = []
    for n in sorted(by_note):
        lst = by_note[n]
        for i, e in enumerate(lst):
            dur = RING_SEC - 0.05 if e['t'] >= B(FINAL_BAR) else DUR.get(n, 0.3)
            off = int(round(s2t(e['sec'] + dur)))
            if i + 1 < len(lst):
                off = min(off, lst[i + 1]['tick'])
            off = max(off, e['tick'] + 1)
            msgs.append((e['tick'], 1, n, e['vel']))
            msgs.append((off, 0, n, 0))
    msgs.sort()
    end_tick = max(int(round(s2t(final_sec + RING_SEC))), msgs[-1][0] + 1)

    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    cond = mido.MidiTrack()
    mid.tracks.append(cond)
    cond.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    cond.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                 clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    now, prev = 0, None
    for j in range(n_steps):
        tk = j * S16
        if tk >= end_tick:
            break
        if us[j] != prev:
            cond.append(mido.MetaMessage('set_tempo', tempo=us[j], time=tk - now))
            now, prev = tk, us[j]
    cond.append(mido.MetaMessage('end_of_track', time=end_tick - now))
    trk = mido.MidiTrack()
    mid.tracks.append(trk)
    trk.append(mido.MetaMessage('track_name', name='Drums', time=0))
    trk.append(mido.Message('program_change', channel=9, program=0, time=0))
    for cc, val in ((7, 112), (10, 64), (11, 127), (91, 40), (93, 0)):
        trk.append(mido.Message('control_change', channel=9, control=cc, value=val, time=0))
    now = 0
    for tk, kind, n, v in msgs:
        if kind == 1:
            trk.append(mido.Message('note_on', channel=9, note=n, velocity=v, time=tk - now))
        else:
            trk.append(mido.Message('note_off', channel=9, note=n, velocity=0, time=tk - now))
        now = tk
    trk.append(mido.MetaMessage('end_of_track', time=end_tick - now))
    mid.save(path)
    return mid, len(notes), dropped


def main():
    for section in (sec1, sec2, sec3, sec4, sec5, sec6, sec7):
        section()
    ensure_unique_bars()
    mid, count, dropped = render('solo.mid')
    print('wrote solo.mid: %d notes, %.1f s, %d strokes thinned for playability'
          % (count, mid.length, dropped))


if __name__ == '__main__':
    main()
