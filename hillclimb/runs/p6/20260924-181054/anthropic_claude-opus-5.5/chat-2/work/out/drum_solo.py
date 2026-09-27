#!/usr/bin/env python3
"""drum_solo.py - generates a two-minute General MIDI drum solo (solo.mid) on channel 10."""
import math
import random
import bisect
import mido

rng = random.Random(20240607)     # musical choices
trng = random.Random(777)         # tempo / phrasing
hrng = random.Random(4242)        # micro-timing

TPB = 480
CH = 9  # MIDI channel 10

# ---- GM percussion ----
KICK, KICK2 = 36, 35
SN, XSTK = 38, 37
HHC, HHP, HHO = 42, 44, 46
TOMS = [50, 48, 47, 45, 43, 41]           # high -> low
CR1, CR2, RIDE, BELL, SPL, CHN = 49, 57, 51, 53, 55, 52
COW, WBH, WBL, CONL, TRIO = 56, 76, 77, 64, 81
CYMBALS = {CR1, CR2, CHN, SPL, RIDE, BELL, TRIO}


def T(k):
    return TOMS[k]


def clamp(v, lo=1, hi=127):
    return max(lo, min(hi, int(round(v))))


def vj(v, j=4.0):
    return clamp(v + rng.gauss(0, j))


notes = []  # [t_beats, note, vel, limb, off_ms, dur_sec]


def hit(t, n, v, limb, off=0.0, dur=None):
    notes.append([t, n, clamp(v), limb, off, dur])


def kick(t, v, off=0.0):
    hit(t, KICK, vj(v, 3), 'RF', off)


def pedal(t, v=50):
    hit(t, HHP, vj(v, 3), 'LF')


def pedals(tb, beats=(0, 1, 2, 3), v=50):
    for k in beats:
        pedal(tb + k, v)


def crash(t, v=115, n=CR1, hand='R', with_kick=True, kv=110):
    hit(t, n, vj(v, 3), hand, dur=2.5)
    if with_kick:
        kick(t, kv)


def flam(t, n, v, hand, off=0.0):
    other = 'L' if hand == 'R' else 'R'
    hit(t, n, vj(v * 0.32, 3), other, off - 26)
    hit(t, n, vj(v, 3), hand, off)


# ---- Motif A: (slot, voice, accent level, hand) over 8 slots ----
MOTIF_A = [(0, 'S', 2, 'R'), (0, 'K', 2, 'F'), (1, 'S', 0, 'L'), (2, 't0', 1, 'R'),
           (3, 't0', 1, 'L'), (4, 't2', 2, 'R'), (5, 'K', 1, 'F'), (6, 't4', 1, 'R'),
           (7, 't5', 2, 'L')]


def motif(start, unit=0.25, shift=0, dyn=1.0, orch=None, rot=0, fill=False,
          crash_first=False, flams=False, rush=0.0):
    orch = orch or {}
    toms = orch.get('toms', TOMS)
    sn = orch.get('S', SN)
    hand_slots = set()
    for s, voice, acc, hand in MOTIF_A:
        slot = (s + rot) % 8
        t = start + slot * unit
        off = -rush * slot / 7.0
        base = {2: 112, 1: 88, 0: 34}[acc]
        if acc:
            base *= dyn
        if voice == 'K':
            kick(t, base * 0.92, off)
            continue
        hand_slots.add(slot)
        if voice == 'S':
            if crash_first and acc == 2:
                hit(t, CR1, vj(base + 6), 'R', off, dur=2.2)
                hit(t, sn, vj(base * 0.9), 'L', off)
                continue
            n = sn
        else:
            k = int(voice[1:])
            n = toms[max(0, min(len(toms) - 1, k + shift))]
        if flams and acc == 2:
            flam(t, n, base, hand, off)
        else:
            hit(t, n, vj(base), hand, off)
    if fill:
        for slot in range(8):
            if slot not in hand_slots:
                hit(start + slot * unit, sn, vj(30, 3), 'L' if slot % 2 else 'R',
                    -rush * slot / 7.0)


# ---- sticking runs ----
def run(start, count, unit, sticking, route, v0, v1, accent=None, boost=24,
        kick_acc=True, rush=0.0, kv=None, arch=False):
    L = len(sticking)
    for i in range(count):
        hand = sticking[i % L]
        t = start + i * unit
        p = i / (count - 1) if count > 1 else 1.0
        if arch:
            v = v0 + (v1 - v0) * math.sin(math.pi * p)
        else:
            v = v0 + (v1 - v0) * p
        acc = accent(i) if accent else False
        if i > 0 and sticking[(i - 1) % L] == hand and not acc:
            v -= 5
        if acc:
            v += boost
        note = route(i, hand, acc)
        hit(t, note, vj(v, 3.5), hand, -rush * p)
        if acc and kick_acc:
            kick(t, kv if kv else min(120, v), -rush * p)


def path(drums, count):
    return lambda i, h, a: drums[min(len(drums) - 1, i * len(drums) // count)]


def cyc(drums, per=1):
    return lambda i, h, a: drums[(i // per) % len(drums)]


def split(rd, ld, count):
    def r(i, h, a):
        d = rd if h == 'R' else ld
        return d[min(len(d) - 1, i * len(d) // count)]
    return r


def acc_route(accd, other):
    c = [0]

    def r(i, h, a):
        if a:
            d = accd[c[0] % len(accd)]
            c[0] += 1
            return d
        return other
    return r


# =================== SECTIONS ===================
def sec_intro(b0):
    motif(b0, dyn=0.85)
    pedals(b0, (2, 3))
    hit(b0 + 3.0, T(5), vj(70), 'R')
    kick(b0 + 3.5, 72)
    hit(b0 + 3.75, SN, vj(30, 3), 'L')
    b = b0 + 4
    motif(b, dyn=0.9)
    run(b + 2, 6, 0.25, 'RLRLRL', path([T(2), T(3), T(4), T(5)], 6), 88, 58, kick_acc=False)
    pedals(b, (2, 3), 48)
    kick(b + 3.5, 80)
    b = b0 + 8
    motif(b + 0.5, dyn=0.95, shift=1)
    pedals(b, (1, 2))
    hit(b + 2.75, SN, vj(34, 3), 'L')
    kick(b + 3.0, 85)
    hit(b + 3.25, T(0), vj(92), 'R')
    hit(b + 3.5, T(1), vj(96), 'L')
    kick(b + 3.75, 80)
    b = b0 + 12
    motif(b, dyn=1.0, fill=True, flams=True)
    run(b + 2, 8, 0.25, 'RLRLRLRL', path([SN, T(0), T(1), T(2), T(3), T(5)], 8), 72, 116,
        accent=lambda i: i in (0, 3, 6), boost=10, rush=8)
    pedals(b, (2, 3))


CELLS = ['RLK', 'RLLK', 'RK', 'RLRK', 'RKLK', 'RLKL', 'RRLK', 'RKK']


def linear_bar(tb, length, first_crash):
    seq = [None] * length
    starts = set()
    i = 0
    while i < length:
        c = rng.choice(CELLS)
        starts.add(i)
        for ch in c:
            if i < length:
                seq[i] = ch
                i += 1
    for s in (4, 12):
        if s < length:
            seq[s] = 'S'
    for s, ch in enumerate(seq):
        t = tb + s * 0.25
        ramp = s / 16.0
        if ch == 'R':
            acc = s in starts
            if s == 0 and first_crash:
                crash(t, 112)
                continue
            if acc and rng.random() < 0.22 and s + 1 < length and seq[s + 1] != 'R':
                hit(t, HHO, vj(92), 'R', dur=0.3)
                pedal(t + 0.5, 55)
            else:
                hit(t, HHC, vj(94 if acc else 58 + 10 * ramp), 'R')
        elif ch == 'L':
            hit(t, SN, vj(28 + 12 * ramp, 3), 'L')
        elif ch == 'K':
            kick(t, 96 if s % 4 == 0 else 82)
        elif ch == 'S':
            hit(t, SN, vj(108), 'L')


def sec_linear(b0):
    for bar in range(8):
        tb = b0 + 4 * bar
        if bar == 3:
            linear_bar(tb, 8, False)
            motif(tb + 2, shift=rng.choice([0, 1]), dyn=0.95, fill=True)
        elif bar == 7:
            linear_bar(tb, 8, False)
            run(tb + 2, 12, 1 / 6, 'RLRLRL',
                path([SN, SN, T(0), T(1), T(2), T(3), T(4), T(5)], 12), 66, 118,
                accent=lambda i: i % 3 == 0, boost=12, rush=10)
        elif bar in (1, 5):
            linear_bar(tb, 12, False)
            flam(tb + 3, T(1), 100, 'R')
            hit(tb + 3.25, T(2), vj(92), 'L')
            kick(tb + 3.5, 94)
            hit(tb + 3.75, T(4) if bar == 1 else T(5), vj(104), 'R')
        else:
            linear_bar(tb, 16, bar in (0, 4))


def sec_around(b0):
    b = b0
    motif(b, crash_first=True, flams=True, dyn=1.0)
    run(b + 2, 8, 0.25, 'RLRRLRLL', split([T(1), T(2), T(3), T(4)], [SN], 8), 60, 80,
        accent=lambda i: i % 4 == 0, boost=30)
    pedals(b, (1, 2, 3))
    b = b0 + 4
    cycle = [T(0), T(1), T(2), T(3), T(4), T(5), T(4), SN]
    run(b, 16, 0.25, 'RL', cyc(cycle, 2), 58, 108, accent=lambda i: i % 4 == 0, boost=14,
        arch=True)
    pedals(b)
    b = b0 + 8
    run(b, 16, 0.125, 'RRLL', lambda i, h, a: SN, 40, 104)
    kick(b, 80)
    kick(b + 1, 88)
    motif(b + 2, crash_first=True, shift=1, dyn=1.02)
    pedals(b)
    b = b0 + 12
    run(b, 24, 1 / 6, 'RLRRLL',
        split([T(0), T(1), T(2), T(3), T(4), T(5)], [SN, SN, T(1), T(2), T(3), T(4)], 24),
        62, 112, accent=lambda i: i % 6 == 0, boost=18, rush=8)
    pedals(b)
    b = b0 + 16
    crash(b, 112)
    motif(b + 0.25, fill=True, dyn=0.95)
    run(b + 2.25, 7, 0.25, 'RLRLRLR', acc_route([T(1), T(3), T(5), T(2)], SN), 34, 38,
        accent=lambda i: i % 3 == 0, boost=66)
    pedals(b, (1, 2, 3))
    b = b0 + 20
    rt = [T(0), T(1), T(2), T(3), T(4), T(5)]
    for s in range(16):
        t = b + s * 0.25
        g, ph = divmod(s, 3)
        v = 70 + 30 * s / 15.0
        if ph == 0:
            hit(t, rt[g % 6], vj(v + 14), 'R')
        elif ph == 1:
            hit(t, rt[min(5, g % 6 + 1)], vj(v), 'L')
        else:
            kick(t, v)
    pedals(b, (1, 3))
    b = b0 + 24
    motif(b, shift=1, crash_first=True)
    motif(b + 2, shift=2, dyn=1.05, fill=True)
    pedals(b)
    b = b0 + 28
    run(b, 16, 0.125, 'RL', path(TOMS, 16), 60, 100, kick_acc=False)
    kick(b, 84)
    kick(b + 1, 90)
    for k in range(4):
        t = b + 2 + k * 0.5
        flam(t, [T(0), T(2), T(4), T(5)][k], 100 + 6 * k, 'R')
        kick(t, 96 + 4 * k)
        hit(t + 0.25, SN, vj(40 + 6 * k, 3), 'L')
    kick(b + 3.75, 100)


def ride_bar(tb, ks, bell_p=0.15):
    for k in ks:
        t = tb + k * 0.5
        on = k % 2 == 0
        if not on and rng.random() < bell_p:
            hit(t, BELL, vj(62), 'R')
        else:
            hit(t, RIDE, vj(66 if on else 48), 'R')


def quiet_ghosts(tb):
    for s in (1, 3, 6, 7, 10, 11, 13, 14, 15):
        if rng.random() < 0.33:
            hit(tb + s * 0.25, SN, vj(24, 3), 'L')
    for s in (6, 10, 14):
        if rng.random() < 0.4:
            kick(tb + s * 0.25, 60)


def sec_quiet(b0):
    b = b0
    crash(b, 108, kv=96)
    ride_bar(b, range(1, 8))
    hit(b + 2, XSTK, vj(74), 'L')
    quiet_ghosts(b)
    pedal(b + 1, 46)
    pedal(b + 3, 46)
    b = b0 + 4
    kick(b, 70)
    ride_bar(b, range(0, 8), 0.3)
    hit(b + 2, XSTK, vj(76), 'L')
    quiet_ghosts(b)
    hit(b + 3.5, TRIO, vj(52), 'L', dur=2.0)
    pedal(b + 1, 46)
    pedal(b + 3, 46)
    b = b0 + 8
    motif(b, dyn=0.55, orch={'S': XSTK})
    ride_bar(b, range(4, 8))
    hit(b + 2, XSTK, vj(72), 'L')
    hit(b + 3.25, SN, vj(24, 3), 'L')
    pedal(b + 1, 46)
    pedal(b + 3, 46)
    b = b0 + 12
    kick(b, 66)
    motif(b + 0.5, dyn=0.6, orch={'S': XSTK, 'toms': [WBH, WBH, WBL, WBL, CONL, CONL]})
    hit(b + 2, XSTK, vj(70), 'L')
    ride_bar(b, range(5, 8), 0.4)
    pedal(b + 1, 46)
    pedal(b + 3, 46)
    b = b0 + 16
    run(b, 16, 0.25, 'RL', lambda i, h, a: SN, 24, 50, accent=lambda i: i % 3 == 0,
        boost=22, kick_acc=False)
    for k in range(4):
        kick(b + k, 58 + 4 * k)
    pedal(b + 1, 48)
    pedal(b + 3, 48)
    b = b0 + 20
    run(b, 16, 0.125, 'RL', lambda i, h, a: SN, 40, 92, kick_acc=False)
    kick(b, 70)
    kick(b + 1, 76)
    seq = [('R', T(0)), ('L', T(1)), ('K', None), ('R', T(2)), ('L', T(4)), ('K', None)]
    for j, (h, n) in enumerate(seq):
        t = b + 2 + j / 3.0
        v = 90 + 22 * j / 5.0
        if h == 'K':
            kick(t, v, -2 * j)
        else:
            hit(t, n, vj(v), h, -2 * j)


U3 = 1 / 3.0
BEMBE = (0, 2, 4, 5, 7, 9, 11)


def rlk_bar(tb, rr, rl, v0, v1, first_crash=False):
    for s in range(12):
        t = tb + s * U3
        ph = s % 3
        v = v0 + (v1 - v0) * s / 11.0
        if ph == 0:
            if s == 0 and first_crash:
                crash(t, 114)
                continue
            hit(t, rr(s // 3), vj(v + 12), 'R')
        elif ph == 1:
            hit(t, rl(s // 3), vj(v - 4), 'L')
        else:
            kick(t, v)


def sec_trip(b0):
    b = b0
    rlk_bar(b, lambda g: [T(0), T(1), T(3), T(4)][g], lambda g: [SN, T(2), T(3), T(5)][g],
            70, 104, first_crash=True)
    b = b0 + 4
    motif(b, unit=U3, dyn=0.95)
    run(b + 8 * U3, 4, U3, 'RLRL', path([T(3), T(4), T(5), T(5)], 4), 90, 112,
        kick_acc=False, rush=6)
    kick(b + 8 * U3, 90)
    kick(b + 10 * U3, 96)
    pedals(b, (1, 3))
    for bar in (2, 3):
        tb = b0 + 4 * bar
        for s in range(12):
            t = tb + s * U3
            if s in BEMBE:
                hit(t, COW, vj(86 if s in (0, 7) else 68), 'R')
            else:
                r = rng.random()
                if bar == 2:
                    if r < 0.55:
                        hit(t, SN, vj(30, 3), 'L')
                    elif r < 0.85:
                        hit(t, rng.choice([T(0), T(1)]), vj(88), 'L')
                else:
                    if r < 0.35:
                        hit(t, SN, vj(32, 3), 'L')
                    elif r < 0.92:
                        hit(t, rng.choice([T(1), T(2), T(3)]), vj(94), 'L')
            if s % 3 == 0:
                kick(t, 88 if s == 0 else 74)
        pedal(tb + 1, 50)
        pedal(tb + 3, 50)
    b = b0 + 16
    crash(b, 112)
    motif(b + U3, unit=U3)
    hit(b + 9 * U3, T(2), vj(100), 'R')
    hit(b + 10 * U3, T(4), vj(104), 'L')
    kick(b + 11 * U3, 100)
    pedals(b, (1, 2))
    b = b0 + 20
    run(b, 12, U3, 'RRLL', cyc(TOMS, 2), 76, 104, accent=lambda i: i % 4 == 0, boost=22)
    pedals(b)
    b = b0 + 24
    for j in range(3):
        motif(b + j * 8 * U3, unit=U3, shift=j, dyn=0.9 + 0.1 * j, crash_first=(j == 0),
              flams=(j == 2), rush=8 if j == 2 else 0)
    pedals(b, (1, 2, 3, 4, 5, 6, 7))


def sec_build(b0):
    TC = [T(0), T(2), T(4), T(1), T(3), T(5)]
    b = b0
    k = 0
    for i in range(32):
        t = b + i * 0.25
        hand = 'RL'[i % 2]
        acc = (i % 8) in (0, 3, 6)
        p = i / 31.0
        if acc:
            if i == 0:
                crash(t, 116)
            else:
                hit(t, TC[k % 6], vj(92 + 18 * p), hand)
                kick(t, 90 + 15 * p)
                k += 1
        else:
            hit(t, SN, vj(28 + 18 * p, 3), hand)
    pedals(b, (1, 2, 3, 4, 5, 6, 7))
    b = b0 + 8
    k = 0
    for i in range(32):
        t = b + i * 0.25
        hand = 'RL'[i % 2]
        p = i / 31.0
        if i >= 28:
            flam(t, [T(2), T(3), T(4), T(5)][i - 28], 104 + 5 * (i - 28), hand)
            if i % 2 == 0:
                kick(t, 108)
            continue
        if i % 3 == 0:
            if hand == 'R' and k % 2 == 0:
                hit(t, CHN if k % 4 == 0 else CR2, vj(100 + 12 * p), 'R', dur=1.4)
            else:
                hit(t, TC[k % 6], vj(96 + 14 * p), hand)
            kick(t, 92 + 14 * p)
            k += 1
        else:
            hit(t, SN, vj(32 + 16 * p, 3), hand)
    pedals(b, (1, 2, 3, 4, 5, 6))
    b = b0 + 16
    motif(b, crash_first=True, flams=True)
    motif(b + 2, fill=True, shift=1, dyn=1.02)
    pedals(b, (1, 2, 3))
    b = b0 + 20
    for j in range(3):
        motif(b + j * 8 / 6.0, unit=1 / 6.0, shift=j, dyn=0.95 + 0.07 * j, rush=4 * j)
    pedals(b)
    b = b0 + 24
    run(b, 32, 0.125, 'RL', lambda i, h, a: SN, 30, 118, kick_acc=False)
    for q in range(4):
        kick(b + q, 70 + 11 * q)
    pedal(b + 1, 50)
    pedal(b + 3, 56)
    b = b0 + 28
    tl = [T(0), T(1), T(2), T(3), T(4), T(5)]
    run(b, 24, 1 / 6.0, 'RLLRLL',
        lambda i, h, a: CR1 if i == 0 else tl[min(5, (i - 1) * 6 // 23)],
        82, 118, accent=lambda i: i % 3 == 0, boost=8, rush=12)


def sec_climax(b0):
    b = b0
    motif(b, crash_first=True, flams=True, dyn=1.08)
    tres = {0: T(2), 3: T(4), 6: T(5)}
    for i in range(8):
        t = b + 2 + i * 0.25
        hand = 'RL'[i % 2]
        if i in tres:
            hit(t, tres[i], vj(112), hand)
            kick(t, 110)
        else:
            hit(t, SN, vj(38, 3), hand)
    pedals(b, (1, 2, 3))
    b = b0 + 4
    HP = [('R', CR1), ('L', SN), ('R', T(0)), ('L', T(1)), ('R', CHN), ('L', SN),
          ('R', T(3)), ('L', T(5))]
    for k, (h, n) in enumerate(HP):
        hit(b + k * 0.5, n, vj(112 if k % 2 == 0 else 104), h,
            dur=1.2 if n in (CR1, CHN) else None)
    for s in range(16):
        t = b + s * 0.25
        if s % 2 == 0:
            hit(t, KICK, vj(96 if s % 4 == 0 else 84, 3), 'RF')
        else:
            hit(t, KICK2, vj(80 + s, 3), 'LF')
    b = b0 + 8
    motif(b, shift=1, crash_first=True, dyn=1.05)
    run(b + 2, 16, 0.125, 'RRLL', path([T(1), T(2), T(3), T(4), T(5)], 16), 70, 116,
        accent=lambda i: i % 4 == 0, boost=10, rush=6)
    pedals(b)
    b = b0 + 12
    kick(b, 96)
    motif(b + 0.25, fill=True, dyn=1.0)
    run(b + 2.25, 4, 0.25, 'RLRL', path([T(2), T(3), T(4), T(5)], 4), 96, 112,
        kick_acc=False)
    hit(b + 3.25, SN, vj(40, 3), 'L')
    hit(b + 3.5, CR2, vj(122), 'R', dur=2.5)
    hit(b + 3.5, SN, vj(118), 'L')
    kick(b + 3.5, 118)
    pedals(b, (0, 1, 2, 3))
    b = b0 + 16  # stop-time: space as tension
    pedals(b, (0, 1, 2), 54)
    for x in (0.5, 0.75, 2.25, 2.5):
        hit(b + x, SN, vj(24, 3), 'L')
    hit(b + 1.5, CR1, vj(120), 'R', dur=2.0)
    hit(b + 1.5, SN, vj(116), 'L')
    kick(b + 1.5, 116)
    hit(b + 3.0, CHN, vj(118), 'R', dur=1.5)
    hit(b + 3.0, T(5), vj(114), 'L')
    kick(b + 3.0, 114)
    hit(b + 3.0, KICK2, vj(108), 'LF')
    hit(b + 3.5, T(1), vj(100), 'R')
    hit(b + 3.75, T(2), vj(108), 'L')
    b = b0 + 20
    for j in range(3):
        motif(b + j * 8 / 6.0, unit=1 / 6.0, shift=j, dyn=1.0 + 0.06 * j,
              crash_first=(j == 0), rush=3 * j)
    pedals(b)
    b = b0 + 24
    drums = [SN, T(0), T(1), T(2), T(3), T(4), T(5)]

    def r6(i, h, a):
        if a and i % 12 == 0 and h == 'R':
            return CR1
        idx = min(6, i * 7 // 24)
        return drums[idx] if h == 'R' else drums[max(0, idx - 1)]
    run(b, 24, 1 / 6.0, 'RLRRLL', r6, 76, 120, accent=lambda i: i % 6 == 0, boost=14,
        kick_acc=False, rush=6)
    for s in range(16):
        t = b + s * 0.25
        v = 84 + 20 * s / 15.0
        if s % 2 == 0:
            hit(t, KICK, vj(v, 3), 'RF')
        else:
            hit(t, KICK2, vj(v - 4, 3), 'LF')
    b = b0 + 28
    motif(b, unit=0.5, crash_first=True, flams=True, dyn=1.1, fill=True)
    for k in range(8):
        hit(b + k * 0.5 + 0.25, SN, vj(36 + 4 * k, 3), 'L')
    pedals(b, (0, 1))
    for s in range(8):
        t = b + 2 + s * 0.25
        v = 90 + 25 * s / 7.0
        if s % 2 == 0:
            hit(t, KICK, vj(v, 3), 'RF')
        else:
            hit(t, KICK2, vj(v - 4, 3), 'LF')


def sec_finale(b0):
    crash(b0, 120)
    run(b0 + 0.5, 44, 0.125, 'RL', lambda i, h, a: SN, 34, 124, kick_acc=False)
    for q in range(1, 6):
        kick(b0 + q, 70 + 9 * q)
    for q in (1, 3, 5):
        pedal(b0 + q, 54)
    run(b0 + 6, 12, 1 / 6.0, 'RLRLRL', path(TOMS, 12), 110, 124,
        accent=lambda i: i % 3 == 0, boost=4, kick_acc=True)
    t = b0 + 8
    hit(t, CR1, 127, 'R', off=12, dur=5.5)
    hit(t, CR2, 127, 'L', off=12, dur=5.5)
    hit(t, KICK, 127, 'RF', off=12, dur=1.0)
    hit(t, KICK2, 122, 'LF', off=12, dur=1.0)


SECTIONS = [  # name, bars, bpm start, bpm end, feel ms, generator
    ('intro', 4, 104, 108, 0, sec_intro),
    ('linear', 8, 110, 111, 3, sec_linear),
    ('around', 8, 113, 118, -2, sec_around),
    ('quiet', 6, 100, 102, 7, sec_quiet),
    ('trip', 8, 106, 110, 2, sec_trip),
    ('build', 8, 114, 124, -5, sec_build),
    ('climax', 8, 126, 128, -3, sec_climax),
    ('finale', 3, 124, 120, -2, sec_finale),
]


def main():
    starts = []
    b = 0
    for s in SECTIONS:
        starts.append(b)
        b += s[1] * 4
    total = b
    final_beat = starts[-1] + 8
    for st, s in zip(starts, SECTIONS):
        s[5](st)

    # ---- tempo map: sections, phrase surges, drift, final ritard ----
    NB = total + 16

    def sec_idx(beat):
        return max(0, bisect.bisect_right(starts, beat) - 1)
    base = []
    for i in range(NB):
        si = sec_idx(i)
        _, bars, b0_, b1_, _, _ = SECTIONS[si]
        frac = min(1.0, max(0.0, (i - starts[si]) / (bars * 4.0)))
        base.append(b0_ + (b1_ - b0_) * frac)
    sm = []
    for i in range(NB):
        w = base[max(0, i - 2):i + 3]
        sm.append(sum(w) / len(w))
    tempo = []
    walk = 0.0
    for i in range(NB):
        walk = 0.85 * walk + trng.gauss(0, 0.004)
        rel = ((i - starts[sec_idx(i)]) % 16) / 15.0
        tempo.append(sm[i] * (1 + 0.022 * rel * rel + walk))
    for d, f in ((3, 0.95), (2, 0.88), (1, 0.80)):
        tempo[final_beat - d] *= f
    secs = sum(60.0 / tempo[i] for i in range(final_beat))
    scale = secs / 116.5
    tempo = [x * scale for x in tempo]
    cum = [0.0]
    for i in range(NB):
        cum.append(cum[-1] + 60.0 / tempo[i])

    # ---- humanize timing ----
    nbars = NB // 4 + 2
    drift_raw = [trng.gauss(0, 3.0) for _ in range(nbars)]
    drift = [(drift_raw[max(0, i - 1)] + drift_raw[i] + drift_raw[min(nbars - 1, i + 1)]) / 3
             for i in range(nbars)]
    evs = []
    for t, n, v, limb, off, dur in notes:
        si = sec_idx(t)
        o = off + SECTIONS[si][4] + drift[int(t // 4)]
        if abs(t - final_beat) < 1e-6:
            o = off
        else:
            o += hrng.gauss(0, 5.0) if limb in ('R', 'L') else hrng.gauss(0, 3.5)
            if limb == 'L':
                o += 2
            if limb == 'RF':
                o -= 1.5
            if v < 45:
                o += 4
            elif v > 105:
                o -= 2
        bi = min(NB - 1, int(math.floor(t)))
        sec = cum[bi] + (t - bi) * 60.0 / tempo[bi] + o / 1000.0
        evs.append({'t': t, 'n': n, 'v': v, 'limb': limb, 'o': o, 'dur': dur,
                    'sec': sec, 'bi': bi, 'keep': True})

    # ---- playability: one stroke per limb within a minimum gap ----
    GAP = {'R': 0.04, 'L': 0.04, 'RF': 0.07, 'LF': 0.07}
    for limb in GAP:
        lst = sorted([e for e in evs if e['limb'] == limb], key=lambda e: (e['sec'], -e['v'], e['n']))
        last = None
        for e in lst:
            if last is not None and e['sec'] - last['sec'] < GAP[limb]:
                if e['v'] > last['v']:
                    last['keep'] = False
                    last = e
                else:
                    e['keep'] = False
                continue
            last = e
    evs = [e for e in evs if e['keep']]

    # ---- to ticks ----
    for e in evs:
        rate = TPB * tempo[e['bi']] / 60.0
        e['tick'] = max(0, int(round(e['t'] * TPB + e['o'] / 1000.0 * rate)))
        d = e['dur']
        if d is None:
            d = 1.8 if e['n'] in CYMBALS else (0.3 if e['n'] == HHO else 0.1)
        e['dtick'] = max(1, int(round(d * rate)))
    # remove same-pitch same-tick duplicates, keep louder
    byp = {}
    for e in evs:
        byp.setdefault(e['n'], []).append(e)
    msgs = []
    for n in sorted(byp):
        lst = sorted(byp[n], key=lambda e: (e['tick'], -e['v']))
        ded = []
        for e in lst:
            if ded and ded[-1]['tick'] == e['tick']:
                continue
            ded.append(e)
        for j, e in enumerate(ded):
            on = e['tick']
            offt = on + e['dtick']
            if j + 1 < len(ded):
                offt = min(offt, ded[j + 1]['tick'] - 1)
            offt = max(on + 1, offt)
            msgs.append((on, 1, n, e['v']))
            msgs.append((offt, 0, n, 0))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    tt = mido.MidiTrack()
    dt = mido.MidiTrack()
    mid.tracks.append(tt)
    mid.tracks.append(dt)
    tt.append(mido.MetaMessage('track_name', name='Tempo', time=0))
    tt.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    last = 0
    for i in range(NB):
        tick = i * TPB
        tt.append(mido.MetaMessage('set_tempo', tempo=int(round(60000000.0 / tempo[i])),
                                   time=tick - last))
        last = tick
    tt.append(mido.MetaMessage('end_of_track', time=0))

    dt.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    dt.append(mido.Message('control_change', channel=CH, control=7, value=115, time=0))
    dt.append(mido.Message('control_change', channel=CH, control=10, value=64, time=0))
    dt.append(mido.Message('control_change', channel=CH, control=91, value=40, time=0))
    last = 0
    for tick, kind, n, v in msgs:
        if kind == 1:
            m = mido.Message('note_on', channel=CH, note=n, velocity=v, time=tick - last)
        else:
            m = mido.Message('note_off', channel=CH, note=n, velocity=0, time=tick - last)
        dt.append(m)
        last = tick
    dt.append(mido.MetaMessage('end_of_track', time=TPB // 2))
    mid.save('solo.mid')


if __name__ == '__main__':
    main()
