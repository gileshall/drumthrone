#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

Only mido is used. The output is identical on every run because the random
generator uses a fixed seed.

Main motif "A" is a 3-3-2 / 3-3-2 sixteenth-note figure:
    DA . . da . . DA . (K) . . DA . . DA .
The solo states it, reorchestrates it, displaces it, fragments it (3-over-4),
augments it (half-time), compresses it (32nds), hides it inside a roll,
turns it into stop-time stabs, and brings it home at the end.

Every note is assigned to one limb: R, L (hands), RF (kick) or LF (hi-hat
pedal / second kick). A final pass enforces one stroke per limb at a time,
so no more than two hands and two feet ever strike together.
"""
import bisect
import math
import random

import mido

rng = random.Random(1964)

BPM = 114.0
TPB = 480
TARGET_FINAL_SEC = 117.6

# ---------------- General MIDI percussion ----------------
K2, K1, SS, SN = 35, 36, 37, 38
HHC, HHP, HHO = 42, 44, 46
F2, F1, T4, T3, T2, T1 = 41, 43, 45, 47, 48, 50
CR1, CHI, RIDE, BELLN, SPL, CR2 = 49, 52, 51, 53, 55, 57
COW, HTIMB, LTIMB, WBH = 56, 65, 66, 76

PATH = [SN, T1, T2, T3, T4, F1, F2]

events = []  # [beat, note, vel, limb, kind]
PUSH = []    # (start_beat, end_beat, tempo_factor_amount)


def B(bar, beat=0.0):
    return bar * 4.0 + beat


def hit(t, note, vel, limb, kind='n'):
    events.append([float(t), int(note), float(vel), limb, kind])


def push(a, b, amt):
    PUSH.append((a, b, amt))


def hand_for(t, unit):
    return 'R' if int(round(t / unit)) % 2 == 0 else 'L'


def other(h):
    return 'L' if h == 'R' else 'R'


def pidx(d):
    return PATH.index(d) if d in PATH else 0


def rand_path(n, start=None):
    idx = rng.randrange(0, 3) if start is None else start
    d = 1
    out = []
    for _ in range(n):
        out.append(PATH[idx])
        if rng.random() < 0.28:
            d = -d
        idx += d
        if idx >= len(PATH):
            idx = len(PATH) - 2
            d = -1
        if idx < 0:
            idx = 1
            d = 1
    return out


# ---------------- building blocks ----------------
def crash(t, vel=116, hand='R', note=None, kick=True, both=False):
    n = note if note else (CR1 if hand == 'R' else CR2)
    hit(t, n, vel, hand, 'a')
    if both:
        hit(t, CR2 if hand == 'R' else CR1, vel * 0.95, other(hand), 'a')
    if kick:
        hit(t, K1, min(127, vel), 'RF', 'a')


def flam(t, note, vel, hand='R'):
    hit(t, note, vel, hand, 'a')
    hit(t, note, vel * 0.4, other(hand), 'g')


def feet(t0, span, mode, vel=80):
    if not mode:
        return
    if mode == 'dbl':
        n = int(round(span / 0.25))
        for i in range(n):
            t = t0 + i * 0.25
            v = vel * (1.0 if i % 4 == 0 else 0.84)
            if i % 2 == 0:
                hit(t, K1, v, 'RF', 'n')
            else:
                hit(t, K2, v * 0.95, 'LF', 'n')
        return
    n = int(round(span))
    for i in range(n):
        t = t0 + i
        beatno = int(round(t)) % 4
        if mode in ('q', 'qhh', 'q_hh24'):
            hit(t, K1, vel * (1.0 if beatno == 0 else 0.9), 'RF', 'n')
        if mode in ('hh', 'qhh'):
            hit(t, HHP, vel * 0.72, 'LF', 'n')
        if mode in ('q_hh24', 'hh24') and beatno in (1, 3):
            hit(t, HHP, vel * 0.75, 'LF', 'n')


KICK_PATS = [[0, 3, 8, 10], [0, 6, 10], [0, 7, 10, 11], [0, 3, 6, 10, 13],
             [0, 8, 9, 14], [0, 2, 7, 10], [0, 6, 8, 11, 14], [0, 3, 10, 15],
             [0, 7, 8, 14]]
GHOST_SLOTS = [1, 3, 6, 7, 9, 10, 11, 14, 15]
_kp = [0]


def groove(bar, s=0.0, e=4.0, cym='hh', ghosts=0.45, sn=108, motif_kick=False,
           busy=False, kick_vel=96):
    b0 = B(bar)
    if motif_kick:
        pat = [0, 3, 6, 10, 11] if rng.random() < 0.5 else [0, 3, 6, 11, 14]
    else:
        pat = KICK_PATS[_kp[0] % len(KICK_PATS)]
        _kp[0] += rng.choice([1, 2, 3])
    extra_acc = rng.choice([None, None, 7, 15, 13])
    for slot in range(16):
        pos = slot * 0.25
        if pos < s - 1e-9 or pos >= e - 1e-9:
            continue
        t = b0 + pos
        lift = 1.0 + 0.07 * (slot / 15.0)
        if cym == 'hh':
            if slot % 2 == 0 or busy:
                if slot % 4 == 0:
                    v = 86
                elif slot % 2 == 0:
                    v = 64
                else:
                    v = 46
                note = HHC
                if slot == 14 and rng.random() < 0.4:
                    note, v = HHO, 78
                hit(t, note, v * lift, 'R', 'a' if slot % 4 == 0 else 'n')
        else:
            if slot % 2 == 0:
                v = 88 if slot % 4 == 0 else 66
                note = BELLN if (slot in (0, 8) and rng.random() < 0.3) else RIDE
                hit(t, note, v * lift, 'R', 'n')
            if slot in (4, 12):
                hit(t, HHP, 62, 'LF', 'n')
        if slot in (4, 12):
            hit(t, SN, sn * (0.96 + 0.06 * rng.random()), 'L', 'a')
        elif extra_acc is not None and slot == extra_acc:
            hit(t, SN, 90, 'L', 'a')
        elif slot in GHOST_SLOTS and rng.random() < ghosts:
            hit(t, SN, rng.uniform(24, 42) * lift, 'L', 'gh')
        if slot in pat:
            hit(t, K1, kick_vel if slot == 0 else kick_vel * 0.88, 'RF', 'n')


MOTIF = [(0, 'S', 2), (3, 'S', 1), (6, 'H', 2), (8, 'K', 1), (11, 'M', 2), (14, 'F', 2)]
ORCH = {
    'std': {'S': SN, 'H': T1, 'M': T3, 'F': F1},
    'toms': {'S': T1, 'H': T2, 'M': T4, 'F': F2},
    'low': {'S': T3, 'H': T4, 'M': F1, 'F': F2},
}


def motif(t0, unit=0.25, orch='std', fill=None, fill_p=1.0, crash_acc=False,
          vel=100, feet_mode=None, feet_vel=78, slots=16, shift=0, notes=None,
          cresc=(0.9, 1.1), fill_unit=None, kick_double=True):
    notes = notes if notes is not None else MOTIF
    o = ORCH[orch]
    m = {}
    for s, role, lev in notes:
        ss = s + shift
        if 0 <= ss < slots:
            m[ss] = (role, lev)
    keys = sorted(m)
    occupied = set()
    prev = SN
    for i in range(slots):
        t = t0 + i * unit
        g = cresc[0] + (cresc[1] - cresc[0]) * i / max(1, slots - 1)
        h = hand_for(t, unit)
        if i in m:
            role, lev = m[i]
            v = vel * g * (1.0 if lev == 2 else 0.8)
            kind = 'a' if lev == 2 else 'n'
            occupied.add(round(t, 6))
            if role == 'K':
                hit(t, K1, v, 'RF', kind)
                continue
            if crash_acc and lev == 2:
                hit(t, CR1 if h == 'R' else CR2, v * 1.04, h, 'a')
                hit(t, K1, v, 'RF', 'a')
                prev = SN
            else:
                d = o[role]
                hit(t, d, v, h, kind)
                prev = d
                if kick_double and lev == 2 and role in ('F', 'M'):
                    hit(t, K1, v * 0.85, 'RF', 'n')
            continue
        if fill and fill_unit is None and rng.random() < fill_p:
            if fill == 'ghost':
                hit(t, SN, rng.uniform(24, 42) * g, h, 'gh')
            elif fill == 'toms':
                nxt = None
                for k in keys:
                    if k > i:
                        nxt = k
                        break
                if nxt is None:
                    tgt, dist = PATH[-1], 3
                else:
                    r = m[nxt][0]
                    tgt = PATH[-1] if r == 'K' else o[r]
                    dist = nxt - i
                a, b = pidx(prev), pidx(tgt)
                if a < b:
                    a += 1
                elif a > b:
                    a -= 1
                else:
                    a = min(len(PATH) - 1, a + 1) if rng.random() < 0.5 else max(0, a - 1)
                d = PATH[a]
                prev = d
                v = vel * g * (0.70 - 0.07 * min(dist, 3))
                hit(t, d, v, h, 'n')
            elif fill == 'kick':
                hit(t, K1, vel * g * 0.6, 'RF', 'n')
    if fill == 'ghost' and fill_unit:
        n = int(round(slots * unit / fill_unit))
        for j in range(n):
            t = t0 + j * fill_unit
            if round(t, 6) in occupied:
                continue
            if rng.random() < fill_p:
                hit(t, SN, rng.uniform(22, 40), hand_for(t, fill_unit), 'gh')
    if feet_mode:
        feet(t0, slots * unit, feet_mode, feet_vel)


STICK = {'single': 'RL', 'double': 'RRLL', 'para': 'RLRRLRLL', 'pdd': 'RLRRLL'}


def run(t0, n, unit, sticking='single', groups=(4,), path=None, v0=60, v1=110,
        acc=16, feet_mode=None, feet_vel=80, split=False, kick_on_group=False,
        shape=1.0):
    path = path or PATH
    st = STICK[sticking]
    gsz = list(groups)
    gi = gc = pi = 0
    for i in range(n):
        t = t0 + i * unit
        limb = st[i % len(st)]
        frac = i / max(1, n - 1)
        v = v0 + (v1 - v0) * (frac ** shape)
        first = gc == 0
        drum = path[pi % len(path)]
        if split and limb == 'L':
            drum = SN
        kind = 'n'
        if first:
            v += acc
            kind = 'a'
        elif i > 0 and st[(i - 1) % len(st)] == limb:
            v -= 9
        hit(t, drum, v, limb, kind)
        if first and kick_on_group:
            hit(t, K1, min(v, 115) * 0.9, 'RF', 'n')
        gc += 1
        if gc >= gsz[gi % len(gsz)]:
            gc = 0
            gi += 1
            pi += 1
    if feet_mode:
        feet(t0, n * unit, feet_mode, feet_vel)


def linear(t0, n, unit, pattern='RLK', path=None, v0=70, v1=110):
    path = path or PATH
    L = len(pattern)
    for i in range(n):
        c = pattern[i % L]
        cyc = i // L
        t = t0 + i * unit
        v = v0 + (v1 - v0) * i / max(1, n - 1)
        if c == 'K':
            hit(t, K1, v * 0.95, 'RF', 'n')
        elif c == 'k':
            hit(t, K2, v * 0.9, 'LF', 'n')
        else:
            first = (i % L == 0)
            hit(t, path[cyc % len(path)], v + (12 if first else 0), c,
                'a' if first else 'n')


def roll(t0, dur, unit=0.125, drum=SN, drum_l=None, v0=35, v1=110, accents=(),
         shape=1.5, accent_kick=False):
    n = int(round(dur / unit))
    for i in range(n):
        t = t0 + i * unit
        limb = 'R' if i % 2 == 0 else 'L'
        frac = i / max(1, n - 1)
        v = v0 + (v1 - v0) * (frac ** shape)
        d = drum_l if (drum_l and limb == 'L') else drum
        kind = 'gh' if v < 46 else 'n'
        if i in accents:
            v = min(127, v + 32)
            kind = 'a'
            if accent_kick:
                hit(t, K1, v * 0.9, 'RF', 'a')
        hit(t, d, v, limb, kind)


def stabs(t0, slots, kinds, vel):
    for s, k in zip(slots, kinds):
        t = t0 + s * 0.25
        h = hand_for(t, 0.25)
        if k == 'CC':
            hit(t, CR1, vel, 'R', 'a')
            hit(t, CR2, vel * 0.96, 'L', 'a')
        elif k == 'C':
            hit(t, CR1 if h == 'R' else CR2, vel, h, 'a')
        elif k == 'X':
            hit(t, CHI, vel * 0.9, h, 'a')
        elif k == 'F':
            hit(t, F1, vel, h, 'a')
            hit(t, F2, vel * 0.9, other(h), 'a')
        elif k == 'S':
            flam(t, SN, vel, h)
        hit(t, K1, vel, 'RF', 'a')


BELL = [0, 2, 4, 5, 7, 9, 11]
LH_SLOTS = [1, 3, 6, 8, 10]
TOM_MEL = [T1, T2, T1, T3, T4, F1, T3]


def sixeight(bar, mode, energy, lh_note=SS):
    b0 = B(bar)
    u = 1.0 / 3.0
    if mode == 'trip':
        path = rand_path(7, start=1)
        for i in range(12):
            t = b0 + i * u
            h = hand_for(t, u)
            sh = 0.85 + 0.3 * i / 11.0
            if i in BELL:
                hit(t, path[BELL.index(i)], (70 + 40 * energy) * sh, h, 'a')
            else:
                hit(t, SN, rng.uniform(26, 42) * sh, h, 'gh')
        for i in (0, 3, 6, 9):
            hit(b0 + i * u, K1, 70 + 22 * energy, 'RF', 'n')
        return
    lhp = 0.4 + 0.4 * energy
    for i in range(12):
        t = b0 + i * u
        sh = 0.88 + 0.22 * i / 11.0
        if i in BELL:
            j = BELL.index(i)
            acc = i in (0, 7)
            if mode == 'ride':
                n, v = BELLN, 56 + 30 * energy
            elif mode == 'cow':
                n, v = COW, 52 + 30 * energy
            else:
                n, v = TOM_MEL[j], 64 + 36 * energy
            v *= 1.14 if acc else 0.9
            hit(t, n, v * sh, 'R', 'a' if acc else 'n')
        if mode == 'toms' and i in (3, 9):
            hit(t, lh_note, (62 + 24 * energy) * sh, 'L', 'n')
        elif i in LH_SLOTS and rng.random() < lhp:
            if mode == 'ride':
                if i in (6, 10) and rng.random() < 0.5:
                    hit(t, rng.choice([T3, F1]), (58 + 30 * energy) * sh, 'L', 'n')
                else:
                    hit(t, SN, rng.uniform(24, 40), 'L', 'gh')
            elif mode == 'cow':
                hit(t, rng.choice([HTIMB, HTIMB, LTIMB]), (56 + 34 * energy) * sh, 'L', 'n')
            else:
                hit(t, SN, rng.uniform(24, 38), 'L', 'gh')
    kicks = [0, 6]
    if energy > 0.7:
        kicks.append(9)
    if rng.random() < 0.4:
        kicks.append(rng.choice([5, 11]))
    for i in kicks:
        hit(b0 + i * u, K1, (68 + 22 * energy) * (1.0 if i == 0 else 0.88), 'RF', 'n')
    for i in (3, 9):
        hit(b0 + i * u, HHP, 50 + 10 * energy, 'LF', 'n')


def improv_fill(t0, beats, energy):
    t = t0
    end = t0 + beats
    last = None
    kinds = ['cell', 'sext', 'linear', 'flams', 'dbl', 'unison', 'para']
    while t < end - 1e-9:
        rem = end - t
        opts = [k for k in kinds if k != last and (k != 'cell' or rem >= 2 - 1e-9)]
        k = rng.choice(opts)
        frac = (t - t0) / beats
        base = 70 + 20 * energy + 25 * frac
        ln = 1
        if k == 'cell':
            path = rand_path(3)
            for i in range(8):
                tt = t + i * 0.25
                h = hand_for(tt, 0.25)
                if i in (0, 3, 6):
                    hit(tt, path[(0, 3, 6).index(i)], base + 16 + 2 * i, h, 'a')
                    hit(tt, K1, base, 'RF', 'n')
                else:
                    hit(tt, SN, rng.uniform(26, 44), h, 'gh')
            ln = 2
        elif k == 'sext':
            run(t, 6, 1 / 6, 'single', groups=(rng.choice([2, 3]),),
                path=rand_path(4), v0=base, v1=base + 12, acc=10, kick_on_group=True)
        elif k == 'linear':
            linear(t, 6, 1 / 6, rng.choice(['RLK', 'RKL']), path=rand_path(2),
                   v0=base, v1=base + 12)
        elif k == 'flams':
            path = rand_path(3)
            for j in range(3):
                flam(t + j / 3.0, path[j], base + 14, 'R' if j % 2 == 0 else 'L')
            hit(t, K1, base, 'RF', 'n')
        elif k == 'dbl':
            run(t, 8, 0.125, 'double', groups=(2,), path=rand_path(4),
                v0=base - 5, v1=base + 10, acc=10)
            hit(t, K1, base, 'RF', 'n')
            hit(t + 0.5, K1, base, 'RF', 'n')
        elif k == 'unison':
            hit(t, CR1, base + 25, 'R', 'a')
            hit(t, K1, base + 20, 'RF', 'a')
            hit(t + 0.25, SN, 40, 'L', 'gh')
            hit(t + 0.5, F1, base + 10, 'R', 'a')
            hit(t + 0.5, K1, base + 10, 'RF', 'n')
            hit(t + 0.75, SN, base, 'L', 'n')
        elif k == 'para':
            run(t, 8, 0.125, 'para', groups=(4,), path=rand_path(2),
                v0=base - 8, v1=base + 6, acc=20, split=True)
            hit(t, K1, base, 'RF', 'n')
        for b in range(ln):
            hit(t + b, HHP, 55, 'LF', 'n')
        t += ln
        last = k


# ---------------- the solo ----------------
def compose():
    # Intro: state the motif, answer it, reorchestrate, fill it in
    motif(B(0), orch='std', vel=96, feet_mode='hh', feet_vel=62, cresc=(0.9, 1.05))
    motif(B(1), notes=MOTIF[:3], slots=8, fill='ghost', fill_p=0.5, vel=98,
          feet_mode='hh', feet_vel=62)
    run(B(1, 2), 8, 0.25, 'single', groups=(2,), path=[SN, T1, T2, T3],
        v0=50, v1=84, acc=10)
    feet(B(1, 2), 2, 'hh', 62)
    motif(B(2), orch='toms', fill='ghost', fill_p=0.6, vel=102, feet_mode='hh', feet_vel=64)
    motif(B(3), orch='std', fill='toms', vel=106, cresc=(0.8, 1.15),
          feet_mode='qhh', feet_vel=70)
    push(B(3), B(4), 0.025)

    # Groove with motif kicks
    crash(B(4), 112)
    groove(4, motif_kick=True)
    groove(5, ghosts=0.5)
    groove(6, motif_kick=True, ghosts=0.55)
    groove(7, e=2.0, ghosts=0.5)
    run(B(7, 2), 8, 0.25, 'double', groups=(2,), path=[SN, T1, T2, T3, T4, F1, F2, F1],
        v0=72, v1=104, acc=12, feet_mode='q', feet_vel=82)
    push(B(7, 2), B(8), 0.02)
    crash(B(8), 115)
    groove(8, cym='ride', ghosts=0.45)
    groove(9, cym='ride', ghosts=0.55)
    groove(10, cym='ride', motif_kick=True, ghosts=0.5)
    groove(11, cym='ride', e=1.0)
    linear(B(11, 1), 18, 1 / 6, 'RLK', path=rand_path(6), v0=72, v1=114)
    feet(B(11, 1), 3, 'hh', 58)
    push(B(11, 1), B(12), 0.03)

    # Development
    crash(B(12), 116)
    motif(B(12), orch='std', fill='toms', fill_p=0.7, vel=104, feet_mode='hh', feet_vel=66)
    motif(B(13), orch='low', shift=2, fill='ghost', fill_p=0.8, vel=106,
          feet_mode='q', feet_vel=80)
    path3 = [T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1]
    for i in range(32):  # motif fragment as 3-over-4
        t = B(14) + i * 0.25
        h = hand_for(t, 0.25)
        frac = i / 31.0
        if i % 3 == 0:
            hit(t, path3[(i // 3) % len(path3)], 84 + 32 * frac, h, 'a')
        else:
            hit(t, SN, 26 + 22 * frac + rng.uniform(-4, 4), h, 'gh')
    feet(B(14), 8, 'qhh', 80)
    run(B(16), 32, 0.25, 'para', groups=(4,), path=[F1, T3, T1, F2, T4, T2, F1, F2],
        v0=78, v1=100, acc=22, split=True, feet_mode='q', feet_vel=84)
    run(B(17), 24, 1 / 6, 'pdd', groups=(6,), path=[SN, T1, T2, T3, T4, F1],
        v0=80, v1=110, acc=18, feet_mode='q', feet_vel=86)
    push(B(17), B(18), 0.015)
    crash(B(18), 118)
    run(B(18), 48, 1 / 6, 'single', groups=[3] * 16, path=rand_path(16, start=0),
        v0=62, v1=120, acc=14, feet_mode='qhh', feet_vel=82)
    push(B(18), B(19, 3), 0.03)
    push(B(19, 3), B(20), -0.02)

    # Contrast: 12/8 bell motif, color percussion
    crash(B(20), 108)
    sixeight(20, 'ride', 0.5)
    sixeight(21, 'ride', 0.6)
    crash(B(22), 90, note=SPL)
    sixeight(22, 'cow', 0.6)
    sixeight(23, 'cow', 0.72)
    crash(B(24), 96, note=SPL)
    sixeight(24, 'toms', 0.65, lh_note=SS)
    sixeight(25, 'toms', 0.78, lh_note=WBH)
    sixeight(26, 'trip', 0.85)
    roll(B(27), 4, unit=1 / 6, drum=F1, drum_l=T4, v0=48, v1=120, shape=1.3)
    feet(B(27), 4, 'q', 88)
    push(B(26), B(28), 0.025)

    # Half-time: motif augmented
    hit(B(28), CR2, 112, 'L', 'a')
    motif(B(28), unit=0.5, crash_acc=True, vel=118, fill='ghost', fill_unit=0.25,
          fill_p=0.55, feet_mode='hh', feet_vel=64, cresc=(1.0, 1.0))
    groove(30, cym='ride', motif_kick=True, ghosts=0.6)
    motif(B(31), unit=0.125, orch='std', fill='toms', fill_p=0.9, vel=104,
          feet_mode='q', feet_vel=86, cresc=(0.85, 1.0))
    motif(B(31, 2), unit=0.125, orch='low', fill='toms', fill_p=1.0, vel=112,
          cresc=(0.95, 1.15))
    feet(B(31, 2), 2, 'q', 90)
    push(B(31), B(32), 0.03)

    # Trading: groove / improvised fills
    crash(B(32), 116)
    groove(32, cym='ride', ghosts=0.5)
    groove(33, cym='ride', e=3.0, ghosts=0.55)
    flam(B(33, 3), SN, 104, 'R')
    hit(B(33, 3), K1, 96, 'RF')
    flam(B(33, 3.5), F1, 108, 'L')
    hit(B(33, 3.5), K1, 96, 'RF')
    improv_fill(B(34), 8, 0.8)
    push(B(34), B(36), 0.02)
    crash(B(36), 118, both=True)
    groove(36, cym='hh', busy=True, ghosts=0.4)
    groove(37, cym='hh', motif_kick=True, e=2.0, ghosts=0.5)
    run(B(37, 2), 12, 1 / 6, 'single', groups=(3,), path=rand_path(4),
        v0=78, v1=108, acc=14, kick_on_group=True)
    feet(B(37, 2), 2, 'hh', 60)
    improv_fill(B(38), 8, 1.0)
    push(B(38), B(40), 0.025)

    # Build: swelling roll with the motif hidden inside it
    crash(B(40), 104)
    acc = [32 + 2 * s for s, _, _ in MOTIF]
    roll(B(40), 8, unit=0.125, drum=SN, v0=30, v1=104, accents=acc, shape=1.6,
         accent_kick=True)
    feet(B(40), 8, 'q_hh24', 76)
    push(B(40), B(42), 0.02)
    orchs = ['std', 'toms', 'low', 'std']
    crash(B(42), 120, both=True)
    for r in range(4):
        motif(B(42, 2 * r), unit=0.125, orch=orchs[r], fill='toms',
              fill_p=0.55 + 0.1 * r, crash_acc=(r % 2 == 1), vel=108 + 3 * r,
              cresc=(0.9, 1.1))
    feet(B(42), 8, 'qhh', 88)
    crash(B(44), 122, both=True)
    motif(B(44), crash_acc=True, fill='ghost', fill_p=0.6, vel=112, orch='std')
    motif(B(45), shift=2, orch='toms', crash_acc=True, fill='toms', fill_p=0.5, vel=114)
    feet(B(44), 8, 'dbl', 92)
    push(B(44), B(46), 0.01)
    run(B(46), 48, 1 / 6, 'single', groups=[6] * 6 + [3] * 4,
        path=rand_path(10, start=0), v0=74, v1=124, acc=12, kick_on_group=True,
        feet_mode='hh', feet_vel=62)
    push(B(46), B(48), 0.035)

    # Stop-time: the motif as stabs, with space
    stabs(B(48), [0, 3, 6], ['CC', 'C', 'F'], 124)
    feet(B(48), 4, 'hh', 58)
    push(B(48, 2), B(49), -0.02)
    roll(B(48, 3.5), 0.5, unit=0.125, drum=SN, v0=60, v1=100, shape=1.0)
    stabs(B(49), [2, 5, 8], ['C', 'C', 'S'], 122)
    feet(B(49), 4, 'hh', 58)
    run(B(49, 3), 6, 1 / 6, 'single', groups=(2,), path=rand_path(3, start=1),
        v0=80, v1=112, acc=10)
    push(B(49, 3), B(50), 0.02)
    stabs(B(50), [0, 3, 6, 8, 11, 14], ['CC', 'F', 'C', 'S', 'F', 'X'], 124)
    feet(B(50), 4, 'hh', 60)
    linear(B(51), 24, 1 / 6, 'RLKk', path=rand_path(6, start=0), v0=80, v1=122)
    push(B(51), B(52), 0.03)

    # Finale
    crash(B(52), 124, both=True)
    motif(B(52), crash_acc=True, fill='toms', fill_p=0.8, vel=116)
    motif(B(53), orch='toms', crash_acc=True, fill='toms', fill_p=0.9, vel=118)
    feet(B(52), 8, 'dbl', 96)
    linear(B(54), 24, 1 / 6, 'RLRLKk', path=rand_path(4, start=0), v0=96, v1=124)
    push(B(54), B(55), 0.02)
    roll(B(55), 1.875, unit=0.125, drum=SN, v0=86, v1=122, shape=1.2)
    feet(B(55), 2, 'q', 100)
    for j, d in enumerate([T1, T2, T3, F1]):
        tt = B(55, 2 + 0.5 * j)
        flam(tt, d, 112 + 4 * j, 'R' if j % 2 == 0 else 'L')
        hit(tt, K1, 110 + 4 * j, 'RF', 'a')
    t = B(56)
    hit(t, CR1, 127, 'R', 'fin')
    hit(t, CR2, 127, 'L', 'fin')
    hit(t, K1, 127, 'RF', 'fin')
    hit(t, K2, 127, 'LF', 'fin')


# ---------------- tempo & performance ----------------
SECT = [(0, 0.965), (4, 1.0), (12, 1.015), (18, 1.035), (20, 0.965), (26, 0.985),
        (28, 0.975), (30, 0.99), (32, 1.005), (40, 0.995), (42, 1.015), (44, 1.03),
        (46, 1.045), (48, 1.03), (52, 1.05)]


def sect_f(b):
    bar = b / 4.0
    f = SECT[0][1]
    for s, v in SECT:
        if bar >= s:
            f = v
    return f


def build_time_map(end_beat):
    step = 1.0 / 48.0
    n = int(end_beat / step) + 2
    raw = []
    for k in range(n):
        b = k * step
        f = sect_f(b)
        for a, e, amt in PUSH:
            if a <= b < e:
                f += amt * (b - a) / (e - a)
        raw.append(f)
    w = 24
    pre = [0.0]
    for x in raw:
        pre.append(pre[-1] + x)
    ph1 = rng.uniform(0, 2 * math.pi)
    ph2 = rng.uniform(0, 2 * math.pi)
    fac = []
    for k in range(n):
        lo = max(0, k - w)
        hi = min(n, k + w + 1)
        f = (pre[hi] - pre[lo]) / (hi - lo)
        b = k * step
        f *= 1 + 0.007 * math.sin(2 * math.pi * b / 29.0 + ph1) \
               + 0.005 * math.sin(2 * math.pi * b / 11.5 + ph2)
        rs = B(55, 1.5)
        if b >= rs:
            x = min(1.0, (b - rs) / 2.5)
            f *= 1 - 0.2 * x ** 1.5
        fac.append(f)
    cum = [0.0]
    for f in fac:
        cum.append(cum[-1] + step * 60.0 / (BPM * f))

    def b2s(b):
        x = b / step
        k = min(int(x), len(cum) - 2)
        fr = x - k
        return cum[k] + (cum[k + 1] - cum[k]) * fr
    return b2s


def main():
    compose()
    end_beat = B(56) + 8
    b2s_raw = build_time_map(end_beat)
    sc = TARGET_FINAL_SEC / b2s_raw(B(56))

    def b2s(b):
        return sc * b2s_raw(b)

    # humanize
    events.sort(key=lambda e: (e[0], e[3], e[1]))
    drift = {'R': 0.0, 'L': 0.0, 'RF': 0.0, 'LF': 0.0}
    notes = []
    for t, note, vel, limb, kind in events:
        base = b2s(t)
        drift[limb] = max(-0.009, min(0.009, 0.8 * drift[limb] + rng.gauss(0, 0.0022)))
        if kind == 'fin':
            off = 0.0
        elif kind == 'g':
            off = -0.024 + rng.gauss(0, 0.003)
        elif kind == 'gh':
            off = 0.004 + rng.gauss(0, 0.006)
        elif kind == 'a':
            off = -0.003 + rng.gauss(0, 0.004)
        else:
            off = rng.gauss(0, 0.005)
        if limb in ('RF', 'LF'):
            off *= 0.7
        s = base + off + (drift[limb] if kind != 'fin' else 0.0)
        s = max(0.0, s)
        v = vel
        if kind != 'fin':
            v *= math.exp(rng.gauss(0, 0.05))
            if limb == 'L' and kind != 'gh':
                v *= 0.97
        if kind == 'gh':
            v = min(v, 52)
        v = int(round(max(8, min(127, v))))
        notes.append([s, note, v, limb, kind])

    # playability: one stroke per limb at a time
    final = []
    for limb in ['R', 'L', 'RF', 'LF']:
        lst = sorted([n for n in notes if n[3] == limb], key=lambda n: (n[0], -n[2], n[1]))
        gap = 0.045 if limb in ('R', 'L') else 0.075
        kept = []
        for n in lst:
            if kept and n[0] - kept[-1][0] < gap:
                if n[2] > kept[-1][2]:
                    kept[-1] = n
                continue
            kept.append(n)
        for i, n in enumerate(kept):
            nxt = kept[i + 1][0] if i + 1 < len(kept) else n[0] + 1.0
            if n[4] == 'fin':
                dur = 3.0
            else:
                dur = min(0.05, 0.8 * (nxt - n[0]))
            final.append([n[0], n[1], n[2], limb, dur, n[4]])

    # limit duration by next onset of same pitch
    final.sort(key=lambda n: (n[0], n[1], n[3]))
    by_pitch = {}
    for n in final:
        by_pitch.setdefault(n[1], []).append(n)
    for p in sorted(by_pitch):
        lst = by_pitch[p]
        for i in range(len(lst) - 1):
            g = lst[i + 1][0] - lst[i][0]
            lst[i][4] = max(0.005, min(lst[i][4], 0.85 * g))

    # tempo map (one set_tempo per beat) and seconds->ticks
    nb = int(end_beat)
    S = [b2s(i) for i in range(nb + 1)]
    tempos = [max(1, int(round((S[i + 1] - S[i]) * 1e6))) for i in range(nb)]
    S_act = [0.0]
    for tp in tempos:
        S_act.append(S_act[-1] + tp / 1e6)

    def s2t(s):
        i = bisect.bisect_right(S_act, s) - 1
        i = max(0, min(i, nb - 1))
        return int(round(TPB * (i + (s - S_act[i]) * 1e6 / tempos[i])))

    msgs = []
    seq = 0
    msgs.append((0, 0, 0, seq, mido.MetaMessage('track_name', name='Drum Solo')))
    seq += 1
    msgs.append((0, 0, 0, seq, mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                                  clocks_per_click=24,
                                                  notated_32nd_notes_per_beat=8)))
    seq += 1
    last_sec = max(n[0] + n[4] for n in final)
    last_beat = min(nb - 1, bisect.bisect_right(S_act, last_sec) + 1)
    for i in range(last_beat + 1):
        msgs.append((i * TPB, 1, 0, seq, mido.MetaMessage('set_tempo', tempo=tempos[i])))
        seq += 1
    msgs.append((0, 2, 0, seq, mido.Message('control_change', channel=9, control=7, value=118)))
    seq += 1
    for s, note, v, limb, dur, kind in final:
        on = s2t(s)
        off = s2t(s + dur)
        if off <= on:
            off = on + 1
        msgs.append((on, 4, note, seq, mido.Message('note_on', channel=9, note=note, velocity=v)))
        seq += 1
        msgs.append((off, 3, note, seq, mido.Message('note_off', channel=9, note=note, velocity=0)))
        seq += 1
    msgs.sort(key=lambda m: (m[0], m[1], m[2], m[3]))

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    now = 0
    for tick, _, _, _, msg in msgs:
        track.append(msg.copy(time=tick - now))
        now = tick
    track.append(mido.MetaMessage('end_of_track', time=TPB))
    mid.save('solo.mid')


if __name__ == '__main__':
    main()
