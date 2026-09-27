#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid: a two-minute General MIDI drum solo on channel 10.

The solo is written as a score (beats, limbs, drums, dynamics), then performed:
a living tempo map (surges, settles, breaths before arrivals), micro-timing per limb
(ghost notes lay back, accents push, runs rush, flams spread), velocity humanization,
and strict one-drummer limb limits (2 hands + 2 feet).  Every random choice uses a
fixed seed, so the output file is identical on every run.
"""
import bisect
import math
import random

import mido

OUT_FILE = 'solo.mid'
SEED = 1975
TPB = 960
CH = 9                    # MIDI channel 10 (0-based 9)
LEAD = 1.0                # one-beat pickup measure (1/4) before bar 0
FINAL_BAR = 57            # the last hit lands on beat 1 of this bar
TARGET_FINAL_SEC = 116.8  # when the last hit lands
TAIL_SEC = 3.2            # let it ring; file ends at ~120 s

# ---- General MIDI percussion map
KICK2, KICK, SIDESTICK, SNARE = 35, 36, 37, 38
F2, HHC, F1, HHP, T4, HHO, T3, T2 = 41, 42, 43, 44, 45, 46, 47, 48
CRASH, T1, RIDE, CHINA, BELL, SPLASH, COWBELL, CRASH2 = 49, 50, 51, 52, 53, 55, 56, 57
TIMB_H, TIMB_L, WB_H, WB_L = 65, 66, 76, 77
FOOT_NOTES = {KICK, KICK2, HHP}
TOMRING = [SNARE, T1, T2, T3, T4, F1, F2]

rnd = random.Random(SEED)


def P(bar, beat=0.0):
    return LEAD + bar * 4.0 + beat


def S16(bar, n):
    return LEAD + bar * 4.0 + n / 4.0


class Score:
    def __init__(self):
        self.ev = []
        self._fid = 0

    def hit(self, pos, limb, note, vel, grace=False, run=None, dur=None, fid=None):
        vel = max(1.0, min(127.0, float(vel)))
        self.ev.append({'pos': float(pos), 'limb': limb, 'note': int(note), 'vel': vel,
                        'grace': grace, 'run': run, 'dur': dur, 'fid': fid})

    def flam(self, pos, limb, note, vel, gnote=None):
        self._fid += 1
        other = 'L' if limb == 'R' else 'R'
        self.hit(pos, limb, note, vel, fid=self._fid)
        self.hit(pos, other, note if gnote is None else gnote, vel * 0.42,
                 grace=True, fid=self._fid)


# ---------------------------------------------------------------- voicing helpers
def spread(path, n):
    L = len(path)
    return lambda i, limb: path[min(L - 1, i * L // max(1, n))]


def toms_of(path):
    t = [p for p in path if p != SNARE]
    return t if t else [T1, F1]


def run(s, start, n, sub, sticking, voice, v0, v1, acc=18, tap=1.0, curve=1.0, kv=0.9):
    """Sticking: R/L hands (upper = accent), K right-foot kick, B left-foot kick, H hat pedal."""
    st = sticking.replace(' ', '')
    m = len(st)
    for i in range(n):
        ch = st[i % m]
        if ch == '.':
            continue
        pos = start + i / float(sub)
        p = i / float(max(1, n - 1))
        base = v0 + (v1 - v0) * (p ** curve)
        up = ch.isupper()
        c = ch.upper()
        if c in 'KB':
            v = base * kv + (acc * 0.6 if up else 0.0)
            s.hit(pos, 'RF' if c == 'K' else 'LF', KICK, v)
        elif c == 'H':
            s.hit(pos, 'LF', HHP, base * 0.6)
        else:
            note = voice(i, c)
            if note is None:
                continue
            v = base + acc if up else base * tap
            s.hit(pos, c, note, v, run=p)


def roll(s, start, beats, note, v0, v1, sub=8, curve=1.4, lead='R', note_l=None):
    """Double-stroke roll (RRLL) with a dynamic swell."""
    n = int(round(beats * sub))
    other = 'L' if lead == 'R' else 'R'
    for i in range(n):
        limb = lead if (i // 2) % 2 == 0 else other
        p = i / float(max(1, n - 1))
        v = v0 + (v1 - v0) * (p ** curve)
        if i % 2 == 1:
            v *= 0.9
        nt = note_l if (note_l is not None and limb == other) else note
        s.hit(start + i / float(sub), limb, nt, v, run=p)


def dbass(s, start, n, sub, v0, v1, accent_every=None):
    for i in range(n):
        limb = 'RF' if i % 2 == 0 else 'LF'
        p = i / float(max(1, n - 1))
        v = v0 + (v1 - v0) * p
        if accent_every and i % accent_every == 0:
            v += 10
        s.hit(start + i / float(sub), limb, KICK, v)


def hat_foot(s, bar, beats=(1, 3), vel=50):
    for b in beats:
        s.hit(P(bar, b), 'LF', HHP, vel + rnd.uniform(-5, 5))


# ---------------------------------------------------------------- the motif
# Motif A: X..X..X.XXX.X.X.  (3+3+2 head, "ta-ka" answer, flam tag)
MOTIF_A = [(0, 'low', 3), (3, 'high', 3), (6, 'low', 3), (8, 'sn', 1), (9, 'sn', 1),
           (10, 'mid', 2), (12, 'low', 3), (14, 'top', 3)]

ORCH = {
    'toms':  {'low': (F2, True), 'high': (T1, False), 'mid': (T3, False), 'sn': (SNARE, False), 'top': (SNARE, False)},
    'toms2': {'low': (F1, True), 'high': (T2, False), 'mid': (T4, False), 'sn': (SNARE, False), 'top': (T1, False)},
    'snare': {'low': (SNARE, True), 'high': (T1, False), 'mid': (F1, False), 'sn': (SNARE, False), 'top': (F2, True)},
    'cym':   {'low': (CRASH, True), 'high': (SNARE, False), 'mid': (F2, False), 'sn': (SNARE, False), 'top': (CHINA, True)},
    'metal': {'low': (CHINA, False), 'high': (SNARE, False), 'mid': (T3, False), 'sn': (SNARE, False), 'top': (F1, False)},
    'latin': {'low': (TIMB_L, True), 'high': (COWBELL, False), 'mid': (TIMB_H, False), 'sn': (TIMB_H, False), 'top': (TIMB_L, False)},
}


def motif_a(s, bar, orch='toms', fill=0.0, vs=1.0, crash_one=False, shift=0, double=None,
            flam_top=True, top_note=None, kick=True, kick_from=0, ghost_notes=(SNARE,),
            gv=(24, 36), upto=16, skip_ghost=()):
    o = ORCH[orch]
    used = set()
    for (p, role, lev) in MOTIF_A:
        if p >= upto:
            continue
        q = p + shift
        pos = S16(bar, q)
        limb = 'R' if q % 2 == 0 else 'L'
        note, k = o[role]
        if role == 'top' and top_note is not None:
            note = top_note
        v = {3: 112.0, 2: 90.0, 1: 64.0}[lev]
        if role == 'sn':
            v = 58.0 if p == 8 else 72.0
        if p == 0 and crash_one:
            note = CRASH
            k = True
        v *= vs
        if role == 'top' and flam_top and not double:
            s.flam(pos, limb, note, v + 4)
        else:
            s.hit(pos, limb, note, v)
        if double and lev == 3 and role in double:
            other = 'L' if limb == 'R' else 'R'
            s.hit(pos, other, double[role], v - 3)
        if k and kick and p >= kick_from:
            s.hit(pos, 'RF', KICK, min(124.0, v * 0.96))
        used.add(p)
    if fill > 0:
        lo, hi = gv
        for p in range(0, upto):
            if p in used or p in skip_ghost:
                continue
            if rnd.random() < fill:
                q = p + shift
                limb = 'R' if q % 2 == 0 else 'L'
                s.hit(S16(bar, q), limb, rnd.choice(ghost_notes), rnd.uniform(lo, hi) * vs)


# ---------------------------------------------------------------- groove
def groove(s, bar, kicks, ghosts=(), back=(4, 12), top='hh', opens=(), bells=(), upto=16,
           first=None, vs=1.0, hat16=False):
    for q in range(upto):
        pos = S16(bar, q)
        if (hat16 or q % 2 == 0) and not (q - 1 in opens):
            if q == 0 and first is not None:
                note, v = first, 112
            elif q in opens:
                note, v = HHO, 86
            elif top == 'ride':
                if q in bells:
                    note, v = BELL, 96
                else:
                    note, v = RIDE, (84 if q % 4 == 0 else 64)
            else:
                note, v = HHC, (90 if q % 4 == 0 else (66 if q % 2 == 0 else 46))
            s.hit(pos, 'R', note, v * vs + rnd.uniform(-3, 3))
        if q in back:
            s.hit(pos, 'L', SNARE, 114 * vs)
        elif q in ghosts:
            s.hit(pos, 'L', SNARE, rnd.uniform(24, 36) * vs)
        if q in kicks:
            s.hit(pos, 'RF', KICK, (104 if q == 0 else 88) * vs)
    if top == 'ride':
        for q in (4, 12):
            if q < upto:
                s.hit(S16(bar, q), 'LF', HHP, 56)
    for q in opens:
        if q < upto:
            s.hit(S16(bar, q + 2), 'LF', HHP, 60)


# ---------------------------------------------------------------- fill vocabulary
PATHS_DOWN = [[SNARE, T1, T2, T3, T4, F1, F2], [SNARE, T1, T3, F1, F2], [T1, T2, T3, T4, F1, F2],
              [SNARE, T2, T4, F2], [T1, SNARE, T3, SNARE, F1, F2]]
PATHS_UP = [[F2, F1, T4, T3, T2, T1], [F2, T4, T2, SNARE], [F1, T3, T1, SNARE], [F2, F1, T3, T1, SNARE]]
PATHS_ZIG = [[SNARE, T1, SNARE, T3, SNARE, F1, F2], [T1, T3, T2, T4, T3, F1, T4, F2],
             [F2, T1, F1, T2, T4, SNARE]]
ALL_PATHS = PATHS_DOWN + PATHS_UP + PATHS_ZIG


def fill(s, start, beats, kind, v0, v1, path=None):
    if path is None:
        path = rnd.choice(ALL_PATHS)
    if kind == 'singles16':
        n = int(round(beats * 4))
        st = rnd.choice(['Rlrl', 'RlrLrlRl', 'rlRl', 'RlRl'])
        run(s, start, n, 4, st, spread(path, n), v0, v1, acc=16)
    elif kind == 'singles32':
        n = int(round(beats * 8))
        st = rnd.choice(['Rlrlrlrl', 'RlrLrlRl', 'Rlrlrl'])
        run(s, start, n, 8, st, spread(path, n), v0, v1, acc=14)
    elif kind == 'sixes_kick':
        n = int(round(beats * 6))
        st = rnd.choice(['Rlrlkb', 'Rlrlkk', 'Rlkbrl'])
        run(s, start, n, 6, st, spread(path, n), v0, v1, acc=16)
    elif kind == 'doubles_toms':
        half = beats / 2.0
        mid = (v0 + v1) / 2.0
        roll(s, start, half, SNARE, v0 * 0.7, mid, curve=1.2)
        n = int(round(half * 4))
        run(s, start + half, n, 4, 'Rlrl', spread(toms_of(path), n), mid, v1, acc=14)
    elif kind == 'paradiddle':
        n = int(round(beats * 4))
        tl = toms_of(path)
        run(s, start, n, 4, 'RlrrLrll',
            lambda i, l: tl[(i // 4) % len(tl)] if i % 4 == 0 else SNARE,
            v0, v1, acc=24, tap=0.6)
        for i in range(0, n, 4):
            s.hit(start + i / 4.0, 'RF', KICK, v0 + (v1 - v0) * i / float(n))
    elif kind == 'flam_tri':
        nb = int(round(beats))
        tl = toms_of(path)
        for b in range(nb):
            t = start + b
            p = b / float(max(1, nb - 1))
            vv = v0 + (v1 - v0) * p
            lead = 'R' if b % 2 == 0 else 'L'
            other = 'L' if lead == 'R' else 'R'
            s.flam(t, lead, tl[min(len(tl) - 1, b * len(tl) // nb)], vv + 10)
            s.hit(t + 1.0 / 3.0, other, SNARE, vv * 0.55, run=p)
            s.hit(t + 2.0 / 3.0, lead, SNARE, vv * 0.68, run=p)
            s.hit(t, 'RF', KICK, vv * 0.95)
    elif kind == 'rlk6':
        n = int(round(beats * 6))
        tl = toms_of(path)
        run(s, start, n, 6, 'Rlk',
            lambda i, l: tl[min(len(tl) - 1, i * len(tl) // n)] if l == 'R' else SNARE,
            v0, v1, acc=14, tap=0.75)
    elif kind == 'tresillo':
        n = int(round(beats * 4))
        tl = toms_of(path)
        accs = [i for i in range(n) if i % 8 in (0, 3, 6)]
        amap = {a: tl[min(len(tl) - 1, j * len(tl) // len(accs))] for j, a in enumerate(accs)}
        run(s, start, n, 4, 'RlrLrlRl', lambda i, l: amap.get(i, SNARE), v0, v1, acc=26, tap=0.55)
        for a in accs:
            s.hit(start + a / 4.0, 'RF', KICK, 84)
    elif kind == 'five':
        n = int(round(beats * 4))
        run(s, start, n, 4, 'Rlrlk', spread(path, n), v0, v1, acc=20, tap=0.8)
    elif kind == 'quint':
        n = int(round(beats * 5))
        run(s, start, n, 5, 'Rlrlk', spread(path, n), v0, v1, acc=18, tap=0.85)


# ---------------------------------------------------------------- the solo
def compose():
    s = Score()

    # ===== pickup: a quick four-stroke launch into the first hit
    run(s, P(-1, 3.5), 4, 8, 'rlrl', lambda i, l: (SNARE, SNARE, T1, T2)[i], 44, 88)

    # ===== 1. STATEMENT (bars 0-7): motif stated, answered, restated, developed
    s.hit(P(0), 'L', CRASH, 110)
    motif_a(s, 0, 'toms')
    hat_foot(s, 0)

    accs = rnd.choice([(3, 6, 10), (2, 7, 11), (3, 7, 10), (1, 6, 11)])
    for q in range(12):
        limb = 'R' if q % 2 == 0 else 'L'
        if q in accs:
            s.hit(S16(1, q), limb, SNARE, rnd.uniform(96, 106))
        elif rnd.random() < 0.8:
            s.hit(S16(1, q), limb, SNARE, rnd.uniform(22, 34))
    s.hit(S16(1, 0), 'RF', KICK, 80)
    s.hit(S16(1, rnd.choice([6, 8, 9])), 'RF', KICK, 66)
    hat_foot(s, 1)
    run(s, S16(1, 12), 4, 4, 'Rlrl', lambda i, l: (T1, T2, T3, F1)[i], 70, 94, acc=10)

    motif_a(s, 2, 'toms', fill=0.45, vs=0.96, top_note=T1)
    hat_foot(s, 2)

    for q in range(8):
        limb = 'R' if q % 2 == 0 else 'L'
        if q in (0, 3, 6):
            s.hit(S16(3, q), limb, SNARE, 104)
            if q != 3:
                s.hit(S16(3, q), 'RF', KICK, 90)
        elif rnd.random() < 0.7:
            s.hit(S16(3, q), limb, SNARE, rnd.uniform(22, 32))
    hat_foot(s, 3, beats=(1,))
    fill(s, S16(3, 8), 2, 'singles16', 62, 102, path=[SNARE, T1, T2, T3, T4, F1, F2])

    motif_a(s, 4, 'toms2', fill=0.6, crash_one=True)
    hat_foot(s, 4)

    six_toms = rnd.choice([(T1, T2), (T2, T3), (T1, T3)])
    run(s, P(5), 12, 6, 'RllrrL',
        lambda i, l: six_toms[i // 6] if i % 6 in (0, 5) else SNARE, 56, 80, acc=30, tap=0.72)
    s.hit(P(5), 'RF', KICK, 92)
    s.hit(P(5, 1), 'RF', KICK, 78)
    hat_foot(s, 5)
    fill(s, P(5, 2), 2, 'rlk6', 72, 106, path=[T1, T2, T3, T4, F1, F2])

    motif_a(s, 6, 'snare', fill=0.35)
    s.hit(S16(6, 3), 'R', SPLASH, 92)
    hat_foot(s, 6)

    s.hit(S16(7, 0), 'R', F2, 106)
    s.hit(S16(7, 0), 'RF', KICK, 100)
    s.hit(S16(7, 3), 'L', T1, 102)
    s.hit(S16(7, 6), 'R', F2, 106)
    s.hit(S16(7, 6), 'RF', KICK, 96)
    for q in (1, 2, 4, 5, 7):
        if rnd.random() < 0.55:
            s.hit(S16(7, q), 'R' if q % 2 == 0 else 'L', SNARE, rnd.uniform(22, 34))
    roll(s, S16(7, 8), 2, SNARE, 30, 112, curve=1.6)
    for q, v in ((8, 48), (12, 70), (14, 88)):
        s.hit(S16(7, q), 'RF', KICK, v)
    hat_foot(s, 7)

    # ===== 2. GROOVE AND GROWING FILLS (bars 8-15)
    KICK_POOL = [(0, 3, 6, 10), (0, 6, 10), (0, 3, 6, 8, 11), (0, 7, 10, 14), (0, 3, 10, 13),
                 (0, 6, 8, 14), (0, 2, 6, 10, 11), (0, 3, 6, 9, 14), (0, 8, 10, 13)]
    GHOST_POOL = [(2, 7, 9, 15), (3, 6, 11, 14), (1, 7, 10, 15), (2, 6, 9, 11, 14), (7, 9, 15),
                  (1, 3, 6, 11, 13), (6, 7, 9, 14, 15)]
    FIRSTS = {8: CRASH, 10: CRASH2, 12: CRASH, 14: CHINA}
    prev = None
    for bar in range(8, 16):
        top = 'hh' if bar < 12 else 'ride'
        kicks = rnd.choice([k for k in KICK_POOL if k != prev])
        prev = kicks
        ghosts = tuple(q for q in rnd.choice(GHOST_POOL) if q not in (4, 12))
        opens = ()
        if top == 'hh' and rnd.random() < 0.65:
            opens = (rnd.choice([6, 10, 14]),)
        bells = rnd.choice([(0, 6), (0, 10), (6, 12), (0, 6, 12)]) if top == 'ride' else ()
        first = FIRSTS.get(bar)
        hat16 = (top == 'hh' and rnd.random() < 0.4)
        if bar % 2 == 0:
            groove(s, bar, kicks, ghosts, top=top, opens=opens, bells=bells,
                   first=first, hat16=hat16)
        else:
            fl = {9: 1, 11: 2, 13: 3, 15: 4}[bar]
            upto = 16 - 4 * fl
            if upto > 0:
                groove(s, bar, kicks, ghosts, top=top, bells=bells, upto=upto, hat16=hat16)
            start = S16(bar, upto)
            if fl == 1:
                fill(s, start, 1, rnd.choice(['singles16', 'sixes_kick', 'rlk6']), 70, 100)
            elif fl == 2:
                fill(s, start, 2, rnd.choice(['paradiddle', 'doubles_toms', 'tresillo']), 64, 104)
            elif fl == 3:
                fill(s, start, 3, rnd.choice(['sixes_kick', 'five', 'singles16']), 62, 106)
            else:
                fill(s, start, 2, 'tresillo', 70, 96)
                fill(s, start + 2, 2, 'singles32', 74, 112)

    # ===== 3. AROUND THE KIT (bars 16-23)
    tp = rnd.choice([[T1, T2, T3, T4, F1, F2], [F2, F1, T4, T3, T2, T1], [T1, T3, F1, T2, T4, F2]])
    run(s, P(16), 16, 4, 'Rlk',
        lambda i, l: CRASH if i == 0 else (tp[(i // 3) % 6] if l == 'R' else SNARE),
        80, 98, acc=18, tap=0.6, kv=0.95)
    s.hit(P(16), 'RF', KICK, 112)
    hat_foot(s, 16)

    at = rnd.choice([[F2, F1, T3, T1], [T1, T3, F1, F2], [F1, T2, F2, T1]])

    def v17(i, l):
        k = i % 5
        if k == 0:
            return at[(i // 5) % 4]
        return T2 if k == 2 else SNARE
    run(s, P(17), 16, 4, 'Rlrlk', v17, 80, 98, acc=22, tap=0.55, kv=1.0)
    hat_foot(s, 17)

    fill(s, P(18), 4, 'sixes_kick', 64, 106, path=rnd.choice(PATHS_DOWN))

    motif_a(s, 19, 'toms2', fill=1.0, crash_one=True,
            ghost_notes=(SNARE, SNARE, T1, T2), gv=(30, 46))
    hat_foot(s, 19)

    mel = rnd.choice([[F2, T1, F1, T3, T2, F2], [T1, F1, T2, F2, T3, F1], [F1, T3, T1, F2, T4, T2]])
    accs20 = [0, 3, 6, 8, 11, 14]
    amap20 = dict(zip(accs20, mel))
    run(s, P(20), 16, 4, 'RlrLrlRlRlrLrlRl', lambda i, l: amap20.get(i, SNARE),
        74, 92, acc=26, tap=0.5)
    for a in accs20:
        s.hit(S16(20, a), 'RF', KICK, 90)
    hat_foot(s, 20)

    fill(s, P(21), 4, 'flam_tri', 72, 106, path=rnd.choice(PATHS_DOWN))
    hat_foot(s, 21)

    path22 = [SNARE, T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1]
    run(s, P(22), 32, 8, rnd.choice(['Rlrlrlrl', 'Rlrlrl']), spread(path22, 32),
        54, 108, acc=16, curve=1.2)
    for b in range(4):
        s.hit(P(22, b), 'RF', KICK, 72 + b * 10)
    hat_foot(s, 22)

    motif_a(s, 23, 'cym', double={'low': SNARE, 'high': CRASH2, 'top': SNARE}, vs=1.04)

    # ===== 4. BREAKDOWN: clave conversation, then the build (bars 24-31)
    CLAVE = ((0, 6, 12), (4, 8))
    for bi, bar in enumerate(range(24, 28)):
        side = bi % 2
        cl = CLAVE[side]
        rnote = BELL if bar < 26 else COWBELL
        answer = (side == 1)
        for q in range(0, 16, 2):
            if answer and q >= 12:
                continue
            if q in cl:
                v = 94 if rnote == BELL else 82
            else:
                v = 46 if rnote == BELL else 38
            s.hit(S16(bar, q), 'R', rnote, v + rnd.uniform(-3, 3))
        acc_slots = rnd.sample([1, 3, 5, 7, 9, 11], 2)
        for q in range(1, 16, 2):
            if answer and q >= 12:
                continue
            if q in acc_slots:
                if bar < 26:
                    note = rnd.choice([SIDESTICK, SIDESTICK, SNARE])
                else:
                    note = rnd.choice([TIMB_H, TIMB_L, WB_L])
                s.hit(S16(bar, q), 'L', note, rnd.uniform(76, 92))
            elif rnd.random() < 0.55:
                s.hit(S16(bar, q), 'L', SNARE if bar < 26 else TIMB_H, rnd.uniform(20, 32))
        if answer:
            if bar < 26:
                ans = rnd.choice([(T2, T3, F1, F2), (T1, T3, T4, F1)])
            else:
                ans = rnd.choice([(TIMB_H, TIMB_L, T3, F2), (TIMB_H, TIMB_H, TIMB_L, F1)])
            run(s, S16(bar, 12), 4, 4, 'rLrL', lambda i, l, a=ans: a[i], 58, 80, acc=12)
        s.hit(S16(bar, 0), 'RF', KICK, 64)
        if rnd.random() < 0.7:
            s.hit(S16(bar, rnd.choice([10, 11, 14])), 'RF', KICK, 50)
        hat_foot(s, bar, vel=46)

    for bi, bar in enumerate((28, 29)):
        cl = CLAVE[bi]
        for q in range(0, 16, 2):
            if bar == 29 and q >= 12:
                continue
            v = 88 if q in cl else 50 + 8 * bi
            s.hit(S16(bar, q), 'R', COWBELL, v + rnd.uniform(-3, 3))
        for q in range(1, 16, 2):
            if bar == 29 and q >= 12:
                continue
            p = (bi * 8 + q // 2) / 15.0
            if p < 0.55:
                note = rnd.choice([SNARE, SNARE, T2, T3])
            else:
                note = rnd.choice([T1, T3, F1, SNARE])
            acc = 14 if rnd.random() < 0.25 else 0
            s.hit(S16(bar, q), 'L', note, 32 + 52 * p + acc + rnd.uniform(-3, 3))
        for q in (0, 6, 12):
            s.hit(S16(bar, q), 'RF', KICK, 68 + 14 * bi)
        hat_foot(s, bar, vel=52)
    run(s, S16(29, 12), 4, 4, 'RlRl', lambda i, l: (F1, T1, F2, T3)[i], 84, 100, acc=12)

    motif_a(s, 30, 'latin', fill=0.5, ghost_notes=(TIMB_H, SNARE), gv=(26, 38))
    hat_foot(s, 30, vel=55)

    roll(s, P(31), 2.75, SNARE, 24, 106, curve=1.7)
    for j in range(6):
        s.hit(P(31, j * 0.5), 'RF', KICK, 42 + j * 11)
    hat_foot(s, 31, beats=(1,), vel=50)
    fl31 = rnd.choice([(T1, T2, F1, F2), (T1, T3, F1, F2), (SNARE, T1, T3, F2)])
    for k in range(4):
        s.flam(S16(31, 12 + k), 'R' if k % 2 == 0 else 'L', fl31[k], 106 + 4 * k)
    s.hit(S16(31, 12), 'RF', KICK, 104)
    s.hit(S16(31, 14), 'RF', KICK, 110)

    # ===== 5. DOUBLE BASS AND TOM MELODIES (bars 32-39)
    dbass(s, P(32), 16, 4, 82, 92, accent_every=4)
    motif_a(s, 32, 'metal', crash_one=True, kick=False, fill=0.25, gv=(30, 42))

    dbass(s, P(33), 8, 4, 80, 90)
    t33 = rnd.choice([(T1, T3, F1), (T2, T4, F2), (F1, T2, T1)])
    run(s, P(33), 8, 4, 'RlrLrlRl',
        lambda i, l: {0: t33[0], 3: t33[1], 6: t33[2]}.get(i, SNARE), 76, 92, acc=24, tap=0.55)
    for q, rn, ln in ((8, CRASH2, SNARE), (11, F2, SNARE), (14, CHINA, F1)):
        s.hit(S16(33, q), 'R', rn, 116)
        s.hit(S16(33, q), 'L', ln, 108)
        s.hit(S16(33, q), 'RF', KICK, 114)

    fill(s, P(34), 4, 'rlk6', 78, 106, path=rnd.choice(PATHS_ZIG + PATHS_DOWN))
    hat_foot(s, 34)

    dbass(s, P(35), 8, 4, 78, 90)
    motif_a(s, 35, 'toms', fill=0.5, kick_from=8)

    s.hit(P(36), 'R', CRASH, 116)
    dbass(s, P(36), 16, 4, 84, 98, accent_every=4)
    motif_a(s, 36, 'metal', shift=2, kick=False, top_note=F2)

    s.hit(P(37), 'RF', KICK, 110)
    fill(s, P(37, 1), 3, 'sixes_kick', 72, 108, path=rnd.choice(PATHS_UP))

    p38 = rnd.choice([[T1, T2, T3, T4, F1, F2, F1, T3, T1, SNARE],
                      [SNARE, T1, SNARE, T2, SNARE, T3, T4, F1, F2]])
    v38 = spread(p38, 32)
    run(s, P(38), 32, 8, rnd.choice(['Rlrlrlrl', 'Rlrlrl']),
        lambda i, l: CRASH if i == 0 else v38(i, l), 66, 104, acc=14)
    for b in range(4):
        s.hit(P(38, b), 'RF', KICK, 100 if b == 0 else 80)
    hat_foot(s, 38)

    fill(s, P(39), 2, 'sixes_kick', 78, 102, path=rnd.choice(PATHS_DOWN))
    fl39 = rnd.choice([(T1, T2, T3, T4, F1, F1, F2, F2), (SNARE, T1, SNARE, T3, SNARE, F1, F2, F2),
                       (T1, T1, T3, T3, F1, F1, F2, F2)])
    for k in range(8):
        s.flam(S16(39, 8 + k), 'R' if k % 2 == 0 else 'L', fl39[k], 100 + 3 * k)
    dbass(s, P(39, 2), 8, 4, 86, 104)

    # ===== 6. OVER THE BARLINE (bars 40-47)
    ct = rnd.choice([[T1, T3, F1, F2], [F2, T2, F1, T1], [T1, F1, T3, F2]])
    k = 0
    for q in range(32):
        bar, qq = 40 + q // 16, q % 16
        limb = 'R' if q % 2 == 0 else 'L'
        pos = S16(bar, qq)
        if q % 3 == 0:
            if q == 0:
                s.hit(pos, 'R', CRASH, 114)
                s.hit(pos, 'RF', KICK, 108)
            else:
                s.hit(pos, limb, ct[k % 4], 98 + q * 0.4 + rnd.uniform(-3, 4))
                s.hit(pos, 'RF', KICK, 78 + q * 0.4)
                k += 1
        else:
            s.hit(pos, limb, SNARE, rnd.uniform(24, 34) + q * 0.35)
    hat_foot(s, 40, beats=(0, 1, 2, 3), vel=58)
    hat_foot(s, 41, beats=(0, 1, 2, 3), vel=58)

    fill(s, P(42), 4, 'quint', 66, 104, path=rnd.choice(PATHS_UP))
    hat_foot(s, 42, beats=(0, 1, 2, 3), vel=54)

    AUG = [(0, 'low'), (6, 'high'), (12, 'low'), (16, 'sn'), (18, 'sn'), (20, 'mid'),
           (24, 'low'), (28, 'top')]
    SHOT = {'low': (CRASH, SNARE, True), 'high': (SPLASH, T1, False), 'sn': (SNARE, T2, True),
            'mid': (F1, T3, True), 'top': (CHINA, SNARE, True)}
    for idx, (q, role) in enumerate(AUG):
        rn, ln, kk = SHOT[role]
        pos = S16(43, q)
        vv = 112 if role in ('low', 'top') else 100
        s.hit(pos, 'R', rn, vv + 4)
        s.hit(pos, 'L', ln, vv)
        if kk:
            s.hit(pos, 'RF', KICK, vv)
        if idx + 1 < len(AUG):
            nq = AUG[idx + 1][0]
            gap = nq - q
            if gap >= 4:
                nset = 3 if gap >= 6 else 2
                su = rnd.choice([[SNARE, SNARE, T1], [T1, T2, T3], [SNARE, T2, F1], [T3, T4, F1]])
                for j in range(nset):
                    sq = nq - nset + j
                    limb = 'R' if sq % 2 == 0 else 'L'
                    s.hit(S16(43, sq), limb, su[j], 48 + 16 * j + rnd.uniform(-3, 3))
    hat_foot(s, 43)
    hat_foot(s, 44)

    for q in range(16):
        limb = 'R' if q % 2 == 0 else 'L'
        if q in (7, 10):
            s.hit(S16(45, q), limb, SNARE, rnd.uniform(90, 100))
        elif rnd.random() < 0.85:
            s.hit(S16(45, q), limb, SNARE, rnd.uniform(17, 29))
    s.hit(S16(45, 0), 'RF', KICK, 54)
    s.hit(S16(45, rnd.choice([8, 11])), 'RF', KICK, 46)
    hat_foot(s, 45, beats=(0, 1, 2, 3), vel=42)

    tm46 = rnd.choice([[T1, T2, T3, F1], [F1, T3, T2, T1], [T2, T1, F1, F2]])
    run(s, P(46), 24, 6, 'Rlrrll', lambda i, l: tm46[i // 6] if i % 6 == 0 else SNARE,
        30, 96, acc=22, tap=0.8, curve=1.3)
    for b in range(4):
        s.hit(P(46, b), 'RF', KICK, 46 + 15 * b)
    hat_foot(s, 46, vel=50)

    fill(s, P(47), 3, 'flam_tri', 92, 112, path=rnd.choice(PATHS_DOWN))
    run(s, P(47, 3), 8, 8, 'Rlrlrlrl', spread([T1, T2, T3, F1, F2], 8), 96, 118, acc=8)
    s.hit(P(47, 3), 'RF', KICK, 104)
    s.hit(P(47, 3.5), 'RF', KICK, 112)
    hat_foot(s, 47, beats=(1,), vel=54)

    # ===== 7. CLIMAX (bars 48-53)
    dbass(s, P(48), 16, 4, 86, 98, accent_every=4)
    amap48 = {0: CRASH, 3: T1, 6: F2, 10: T3, 12: F2, 14: CRASH2}
    st48 = ''.join(('R' if q % 2 == 0 else 'L') if q in amap48 else ('r' if q % 2 == 0 else 'l')
                   for q in range(16))
    run(s, P(48), 16, 4, st48, lambda i, l: amap48.get(i, SNARE if l == 'L' else T2),
        72, 86, acc=32, tap=0.62)

    p49 = rnd.choice([[SNARE, T1, T2, T3, T4, F1, F2], [T1, SNARE, T2, SNARE, T3, F1, F2, F1],
                      [F2, F1, T4, T3, T2, T1, SNARE]])
    run(s, P(49), 32, 8, rnd.choice(['Rlrlrlrl', 'RlrLrlRl']), spread(p49, 32), 74, 108, acc=16)
    dbass(s, P(49), 8, 2, 92, 102)

    cy50 = [CRASH, CHINA, CRASH2, CHINA]
    v50 = spread(rnd.choice(PATHS_DOWN), 24)
    run(s, P(50), 24, 6, 'Rlrlkb', lambda i, l: cy50[i // 6] if i % 6 == 0 else v50(i, l),
        86, 112, acc=14)

    dbass(s, P(51), 16, 4, 90, 102, accent_every=4)
    motif_a(s, 51, 'toms', double={'high': T2, 'low': F1, 'top': T1}, kick=False,
            crash_one=True, fill=0.4, gv=(32, 44), skip_ghost=(15,))

    fl52 = rnd.choice([(T1, T1, T2, T2, T3, T3, F1, F2), (SNARE, T1, T2, T3, T4, F1, F2, F2),
                       (T1, T2, T1, T3, T2, F1, T3, F2)])
    for k in range(8):
        s.flam(S16(52, k), 'R' if k % 2 == 0 else 'L', fl52[k],
               100 + 2.5 * k + (8 if k % 4 == 0 else 0))
    dbass(s, P(52), 8, 4, 92, 104)
    up52 = rnd.choice(PATHS_UP)
    v52 = spread(up52, 12)
    run(s, P(52, 2), 12, 6, 'Rlk',
        lambda i, l: CRASH2 if i == 0 else (v52(i, l) if l == 'R' else SNARE), 96, 116, acc=12)

    run(s, P(53), 24, 8, 'Rlrlrlrl', spread([T1, T2, T3, T4, F1, F2], 24), 82, 116, acc=12)
    dbass(s, P(53), 12, 4, 94, 108)
    s.hit(S16(53, 12), 'R', F2, 122)
    s.hit(S16(53, 12), 'L', SNARE, 120)
    s.hit(S16(53, 12), 'RF', KICK, 122)

    # ===== 8. FINALE (bars 54-57): the motif, full kit, then the swell and the last hit
    motif_a(s, 54, 'toms', double={'low': CRASH, 'high': CRASH2, 'top': CHINA}, vs=1.06)
    s.hit(S16(54, 14), 'RF', KICK, 118)

    motif_a(s, 55, 'toms2', double={'low': CRASH2, 'high': CRASH}, vs=1.06, upto=8)
    fill(s, P(55, 2), 2, 'sixes_kick', 94, 120, path=[SNARE, T1, T2, T3, T4, F1, F2])

    s.hit(P(56), 'R', CRASH, 122)
    s.hit(P(56), 'L', SNARE, 116)
    s.hit(P(56), 'RF', KICK, 120)
    roll(s, P(56, 1), 2, SNARE, 46, 96, curve=1.3)
    roll(s, P(56, 3), 1, F2, 98, 124, curve=1.0, note_l=SNARE)
    for b, v in ((1, 72), (2, 86), (3, 100), (3.5, 112)):
        s.hit(P(56, b), 'RF', KICK, v)

    fin = P(FINAL_BAR)
    s.hit(fin, 'R', CRASH, 127, dur=3.0)
    s.hit(fin, 'L', CRASH2, 125, dur=3.0)
    s.hit(fin, 'RF', KICK, 127, dur=1.5)
    s.hit(fin, 'LF', KICK2, 124, dur=1.5)
    return s


# ---------------------------------------------------------------- never the same bar twice
def bar_sig(evs, b0):
    return tuple(sorted((int(round((e['pos'] - b0) * 120)), e['note'],
                         0 if e['vel'] < 45 else (1 if e['vel'] < 95 else 2), e['grace'])
                        for e in evs))


def ensure_novelty(s):
    nr = random.Random(SEED + 7)
    bars = {}
    for e in s.ev:
        b = int(math.floor((e['pos'] - LEAD) / 4.0 + 1e-9))
        bars.setdefault(b, []).append(e)
    seen = set()
    for b in sorted(bars):
        evs = bars[b]
        b0 = LEAD + 4.0 * b
        sig = bar_sig(evs, b0)
        tries = 0
        while sig in seen and tries < 16:
            cands = [e for e in evs if e['limb'] in ('R', 'L') and e['note'] in TOMRING
                     and not e['grace']]
            if cands:
                e = nr.choice(cands)
                i = TOMRING.index(e['note'])
                j = i + 1 if i + 1 < len(TOMRING) else i - 1
                e['note'] = TOMRING[j]
            else:
                e = nr.choice(evs)
                e['vel'] = max(1.0, e['vel'] * 0.8)
            sig = bar_sig(evs, b0)
            tries += 1
        seen.add(sig)


# ---------------------------------------------------------------- living pulse
TEMPO_PTS = [
    (-0.25, 106.0), (0.0, 108.0), (7.0, 111.0),
    (8.0, 112.0), (15.0, 114.0),
    (16.0, 115.0), (22.5, 118.0), (23.0, 117.0), (24.0, 109.0), (25.0, 106.5), (27.5, 106.0),
    (29.0, 109.0), (31.0, 112.5),
    (32.0, 116.0), (39.5, 120.0),
    (40.0, 117.0), (41.0, 115.0), (42.0, 114.0), (44.5, 113.0), (45.25, 108.5), (46.0, 110.0),
    (47.5, 116.0),
    (48.0, 120.0), (53.0, 125.0),
    (54.0, 122.0), (55.5, 119.0), (56.0, 115.0), (57.0, 98.0), (60.0, 98.0),
]
HOLDS = [(8, 0.975), (16, 0.975), (24, 0.965), (32, 0.975), (40, 0.975), (48, 0.97),
         (54, 0.93), (57, 0.95)]


def base_bpm(barf):
    pts = TEMPO_PTS
    if barf <= pts[0][0]:
        return pts[0][1]
    for (b0, t0), (b1, t1) in zip(pts, pts[1:]):
        if b0 <= barf <= b1:
            if b1 == b0:
                return t1
            u = (barf - b0) / (b1 - b0)
            u = u * u * (3.0 - 2.0 * u)
            return t0 + (t1 - t0) * u
    return pts[-1][1]


class TempoMap:
    """Tempo per half-beat segment, in integer microseconds per beat."""

    def __init__(self, us):
        self.us = us
        self.pref = [0.0]
        for u in us:
            self.pref.append(self.pref[-1] + 0.5 * u / 1e6)

    def bpm_at(self, beat):
        k = min(len(self.us) - 1, max(0, int(math.floor(beat * 2.0))))
        return 60e6 / self.us[k]

    def sec(self, beat):
        if beat <= 0:
            return beat * self.us[0] / 1e6
        k = int(math.floor(beat * 2.0))
        if k >= len(self.us):
            return self.pref[-1] + (beat - len(self.us) / 2.0) * self.us[-1] / 1e6
        return self.pref[k] + (beat - k / 2.0) * self.us[k] / 1e6

    def beat(self, sec):
        if sec <= 0:
            return sec * 1e6 / self.us[0]
        k = bisect.bisect_right(self.pref, sec) - 1
        if k >= len(self.us):
            return len(self.us) / 2.0 + (sec - self.pref[-1]) * 1e6 / self.us[-1]
        return k / 2.0 + (sec - self.pref[k]) * 1e6 / self.us[k]


def build_tempo(s):
    trng = random.Random(SEED + 3)
    ph1 = trng.uniform(0, 2 * math.pi)
    ph2 = trng.uniform(0, 2 * math.pi)
    positions = sorted(e['pos'] for e in s.ev if not e['grace'])
    final_pos = P(FINAL_BAR)
    nseg = int(math.ceil((final_pos + 8.0) * 2))
    raw = []
    for k in range(nseg):
        mid = (k + 0.5) / 2.0
        barf = (mid - LEAD) / 4.0
        b = base_bpm(barf)
        lo = bisect.bisect_left(positions, mid - 1.0)
        hi = bisect.bisect_left(positions, mid + 1.0)
        d = (hi - lo) / 2.0
        fd = 1.0 + 0.026 * max(-0.4, min(1.0, (d - 6.0) / 8.0))   # dense passages push ahead
        drift = (1.0 + 0.007 * math.sin(2 * math.pi * mid / 41.0 + ph1)
                 + 0.004 * math.sin(2 * math.pi * mid / 15.0 + ph2))
        raw.append(b * fd * drift)
    sm = [0.25 * raw[max(0, k - 1)] + 0.5 * raw[k] + 0.25 * raw[min(nseg - 1, k + 1)]
          for k in range(nseg)]
    for bar, amt in HOLDS:                     # breathe before big arrivals
        A = P(bar)
        k = int(round(A * 2)) - 1
        if 0 <= k < nseg:
            sm[k] *= amt
        if 0 <= k - 1 < nseg:
            sm[k - 1] *= (1.0 + amt) / 2.0
    nfin = int(round(final_pos * 2))
    raw_sec = sum(30.0 / sm[k] for k in range(nfin))
    factor = raw_sec / TARGET_FINAL_SEC
    us = [int(round(60e6 / (b * factor))) for b in sm]
    return TempoMap(us)


# ---------------------------------------------------------------- the performance
SWING = {}
for _b in range(8, 16):
    SWING[_b] = 0.08
for _b in range(24, 31):
    SWING[_b] = 0.10

BIAS = {'R': -0.0015, 'L': 0.0025, 'RF': 0.0005, 'LF': 0.004}


def make_perf(e, sec, hr):
    v = e['vel']
    sd = 2.2 if v < 45 else (4.5 if v < 95 else 3.5)
    vv = v + hr.gauss(0.0, sd)
    if e['limb'] == 'L' and v > 60:
        vv -= 2.0
    vv = int(round(max(1.0, min(127.0, vv))))
    return {'sec': sec, 'limb': e['limb'], 'note': e['note'], 'v': vv, 'dur': e['dur']}


def perform(s, tm):
    hr = random.Random(SEED + 11)
    ar = {'R': 0.0, 'L': 0.0, 'RF': 0.0, 'LF': 0.0}
    mains = {}
    out = []
    order = sorted(range(len(s.ev)), key=lambda i: (s.ev[i]['pos'], s.ev[i]['grace'], i))
    for i in order:
        e = s.ev[i]
        if e['grace']:
            continue
        lim = e['limb']
        ar[lim] = 0.65 * ar[lim] + hr.gauss(0.0, 0.0032)
        off = BIAS[lim] + ar[lim] + hr.gauss(0.0, 0.0015)
        v = e['vel']
        if v < 45:
            off += 0.0045          # ghost notes sit back
        elif v >= 100:
            off -= 0.0025          # accents drive
        if e['run'] is not None:
            off -= 0.004 * e['run']  # runs lean forward
        bar = int(math.floor((e['pos'] - LEAD) / 4.0 + 1e-9))
        sw = SWING.get(bar, 0.0)
        if sw and e['run'] is None:
            x = (e['pos'] - LEAD) * 4.0
            xr = int(round(x))
            if abs(x - xr) < 1e-6 and xr % 2 == 1:
                off += sw * 15.0 / tm.bpm_at(e['pos'])
        sec = max(0.0, tm.sec(e['pos']) + off)
        if e['fid'] is not None:
            mains[e['fid']] = sec
        out.append(make_perf(e, sec, hr))
    for i in order:
        e = s.ev[i]
        if not e['grace']:
            continue
        base = mains.get(e['fid'], tm.sec(e['pos']))
        sec = max(0.0, base - hr.uniform(0.018, 0.032))
        out.append(make_perf(e, sec, hr))
    return out


GAP = {'R': 0.042, 'L': 0.042, 'RF': 0.07, 'LF': 0.07}


def enforce_limbs(evs):
    by = {}
    for e in evs:
        by.setdefault(e['limb'], []).append(e)
    out = []
    for limb in ('R', 'L', 'RF', 'LF'):
        lst = sorted(by.get(limb, []), key=lambda e: (e['sec'], e['note']))
        kept = []
        for e in lst:
            if kept and e['sec'] - kept[-1]['sec'] < GAP[limb]:
                if e['v'] > kept[-1]['v']:
                    kept[-1] = e
            else:
                kept.append(e)
        out.extend(kept)
    out.sort(key=lambda e: (e['sec'], e['note']))
    return out


def enforce_class_window(evs, win=0.03):
    evs = sorted(evs, key=lambda e: (e['sec'], e['note']))
    out = []
    recent = {'hand': [], 'foot': []}
    for e in evs:
        cls = 'foot' if e['note'] in FOOT_NOTES else 'hand'
        r = [x for x in recent[cls] if e['sec'] - x['sec'] < win]
        if len(r) >= 2:
            continue
        r.append(e)
        recent[cls] = r
        out.append(e)
    return out


# ---------------------------------------------------------------- MIDI output
DUR = {CRASH: 2.4, CRASH2: 2.4, CHINA: 1.8, SPLASH: 1.0, RIDE: 1.0, BELL: 1.0,
       HHO: 0.45, HHC: 0.1, HHP: 0.12, KICK: 0.3, KICK2: 0.3, SNARE: 0.22, SIDESTICK: 0.12,
       T1: 0.4, T2: 0.4, T3: 0.45, T4: 0.45, F1: 0.5, F2: 0.55, COWBELL: 0.25,
       TIMB_H: 0.3, TIMB_L: 0.35, WB_H: 0.15, WB_L: 0.15}


def emit(track, items, end_tick):
    now = 0
    for it in items:
        tick, msg = it[0], it[-1]
        track.append(msg.copy(time=tick - now))
        now = tick
    track.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - now)))


def write_midi(evs, tm, final_sec):
    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    end_tick = int(round(tm.beat(final_sec + TAIL_SEC) * TPB))

    cond = [(0, mido.MetaMessage('track_name', name='Tempo map', time=0)),
            (0, mido.MetaMessage('time_signature', numerator=1, denominator=4,
                                 clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))]
    last = None
    for k, u in enumerate(tm.us):
        tick = k * TPB // 2
        if tick > end_tick:
            break
        if u != last:
            cond.append((tick, mido.MetaMessage('set_tempo', tempo=u, time=0)))
            last = u
    cond.append((int(LEAD * TPB), mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                                   clocks_per_click=24,
                                                   notated_32nd_notes_per_beat=8, time=0)))
    cond.sort(key=lambda x: x[0])
    t0 = mido.MidiTrack()
    emit(t0, cond, end_tick)
    mid.tracks.append(t0)

    for e in evs:
        e['tick'] = max(0, int(round(tm.beat(e['sec']) * TPB)))
    by_note = {}
    for e in evs:
        by_note.setdefault(e['note'], []).append(e)
    notes = []
    for note in sorted(by_note):
        lst = sorted(by_note[note], key=lambda e: (e['tick'], -e['v']))
        merged = []
        for e in lst:
            if merged and e['tick'] == merged[-1]['tick']:
                continue
            merged.append(e)
        for i, e in enumerate(merged):
            dur = e['dur'] if e['dur'] is not None else DUR.get(note, 0.2)
            off = int(round(tm.beat(e['sec'] + dur) * TPB))
            if i + 1 < len(merged):
                off = min(off, merged[i + 1]['tick'])
            off = max(off, e['tick'] + 1)
            off = min(off, end_tick)
            notes.append((e['tick'], off, note, e['v']))

    items = [(0, 0, mido.MetaMessage('track_name', name='Drum Solo', time=0)),
             (0, 1, mido.Message('program_change', channel=CH, program=0, time=0)),
             (0, 2, mido.Message('control_change', channel=CH, control=7, value=112, time=0)),
             (0, 2, mido.Message('control_change', channel=CH, control=11, value=127, time=0)),
             (0, 2, mido.Message('control_change', channel=CH, control=10, value=64, time=0)),
             (0, 2, mido.Message('control_change', channel=CH, control=91, value=46, time=0)),
             (0, 2, mido.Message('control_change', channel=CH, control=93, value=0, time=0))]
    for on, off, note, v in notes:
        items.append((on, 4, mido.Message('note_on', channel=CH, note=note, velocity=v, time=0)))
        items.append((off, 3, mido.Message('note_off', channel=CH, note=note, velocity=0, time=0)))
    items.sort(key=lambda x: (x[0], x[1]))
    t1 = mido.MidiTrack()
    emit(t1, items, end_tick)
    mid.tracks.append(t1)
    mid.save(OUT_FILE)


def main():
    s = compose()
    ensure_novelty(s)
    tm = build_tempo(s)
    evs = perform(s, tm)
    evs = enforce_limbs(evs)
    evs = enforce_class_window(evs)
    final_sec = tm.sec(P(FINAL_BAR))
    write_midi(evs, tm, final_sec)


if __name__ == '__main__':
    main()
