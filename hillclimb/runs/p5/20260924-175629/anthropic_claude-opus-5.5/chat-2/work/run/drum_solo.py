#!/usr/bin/env python3
"""drum_solo.py - generates solo.mid: a two-minute General MIDI drum solo (channel 10).

Deterministic: fixed random seed, no external state.  Only dependency: mido.
"""
import bisect
import math
import random

import mido

rng = random.Random(1964)

# ---------------------------------------------------------------- GM notes
K1, K2 = 35, 36
STICK, SN = 37, 38
FT_LO, FT_HI = 41, 43
HHC, HHP, HHO = 42, 44, 46
T_LO, T_LM, T_HM, T_HI = 45, 47, 48, 50
CR1, CR2, RIDE, RBELL, CHINA, SPLASH = 49, 57, 51, 53, 52, 55
COWBELL = 56
CONGA_MH, CONGA_OH, CONGA_L = 62, 63, 64
TIMB_H, TIMB_L = 65, 66
AGOGO_H, AGOGO_L = 67, 68
CLAVES = 75
TRI_O = 81

FEET_NOTES = {35, 36, 44}

# ---------------------------------------------------------------- event store
EV = []  # (beat, note, vel, limb, kind, dt_seconds)


def hit(beat, note, vel, limb=None, kind='n', dt=0.0):
    if note in FEET_NOTES:
        if limb not in ('RF', 'LF'):
            limb = 'LF' if note == HHP else 'RF'
    else:
        if limb not in ('R', 'L'):
            limb = 'R'
    vel = max(1, min(127, int(round(vel))))
    EV.append((beat, note, vel, limb, kind, dt))


def B(bar, s=0.0):
    return bar * 4.0 + s / 4.0


def other(h):
    return 'L' if h == 'R' else 'R'


def hv(v, sd=3.5):
    return v + rng.gauss(0, sd)


def ramp(i, n, a, b, c=1.0):
    t = i / (n - 1) if n > 1 else 1.0
    return a + (b - a) * (t ** c)


def flam(beat, note, vel, main='R', kind='a'):
    hit(beat, note, vel, main, kind)
    hit(beat, note, hv(42, 4), other(main), 'f', dt=-0.034)


_cr = [0]


def next_crash():
    seq = [CR1, CR2, CR1, CHINA, CR2]
    n = seq[_cr[0] % len(seq)]
    _cr[0] += 1
    return n


# ---------------------------------------------------------------- the motif
# (sixteenth, role, level) roles: 0 high voice, 1 mid, 2 low, 3 ghost voice
MOTIF = [(0, 0, 'A'), (1, 3, 'g'), (2, 3, 'g'), (3, 0, 'A'), (5, 3, 'g'),
         (6, 1, 'A'), (8, 3, 'g'), (9, 3, 'g'), (10, 2, 'A'), (12, 2, 'N'),
         (13, 3, 'g'), (14, 1, 'A'), (15, 0, 'A')]
MOTIF_KICK = [0, 6, 10]

ORCH_TOMS = [T_HI, T_LM, FT_HI, SN]
ORCH_SN = [SN, T_HM, FT_LO, SN]
ORCH_LATIN = [TIMB_H, TIMB_L, CONGA_L, CONGA_MH]
ORCH_BIG = [T_HI, T_LM, FT_LO, SN]


def play_motif(start, span=4.0, orch=ORCH_TOMS, dyn=1.0, rotate=0, ghosts=True,
               kick=True, flams=False, crash=False, lo=0, hi=16,
               extra_ghosts=False, first='R'):
    items = []
    for s, r, k in MOTIF:
        if lo <= s < hi and (ghosts or k != 'g'):
            items.append((s, r, k))
    if extra_ghosts:
        used = {s for s, _, _ in items}
        for s in range(lo, hi):
            if s not in used:
                items.append((s, 3, 'g'))
    items = sorted(((s + rotate) % 16, s, r, k) for s, r, k in items)
    hand = first
    for pos, s0, r, k in items:
        b = start + pos * span / 16.0
        shape = 0.9 + 0.2 * pos / 15.0          # phrase swells to its end
        if k == 'A':
            v, kind = hv(108 * dyn * shape), 'a'
        elif k == 'N':
            v, kind = hv(86 * dyn * shape), 'n'
        else:
            v, kind = hv(24 + 8 * dyn, 3), 'g'
        note = orch[r]
        if crash and k == 'A' and r == 0:
            hit(b, next_crash(), v + 6, hand, 'a')
            if kick and s0 not in MOTIF_KICK:
                hit(b, K2, hv(100 * dyn), 'RF', 'a')
        else:
            hit(b, note, v, hand, kind)
            if flams and k == 'A':
                hit(b, note, hv(44, 4), other(hand), 'f', dt=-0.034)
        hand = other(hand)
    if kick:
        for s in MOTIF_KICK:
            if lo <= s < hi:
                hit(start + ((s + rotate) % 16) * span / 16.0, K2,
                    hv(98 * dyn), 'RF', 'a')


# ---------------------------------------------------------------- helpers
def hhp_quarters(bar, v=50, skip=()):
    for s in (0, 4, 8, 12):
        if s not in skip:
            hit(B(bar, s), HHP, hv(v), 'LF', 'n')


def groove_bar(bar, dyn=1.0, crash_first=False, opens=(), ghosts=(3, 7, 9, 15),
               kicks=(0, 6, 10), half_motif=False):
    top = 8 if half_motif else 16
    for s in range(0, top, 2):
        b = B(bar, s)
        if s == 0 and crash_first:
            hit(b, CR1, hv(114 * dyn), 'R', 'a')
        elif s in opens:
            hit(b, HHO, hv(90 * dyn), 'R', 'a')
            hit(B(bar, s + 2), HHP, hv(64), 'LF', 'n')
        else:
            v = 86 if s % 4 == 0 else (70 if s in (6, 14) else 60)
            hit(b, HHC, hv(v * dyn), 'R', 'a' if s % 4 == 0 else 'n')
    for s in (4, 12):
        if s < top:
            hit(B(bar, s), SN, hv(112 * dyn), 'L', 'a')
    for s in ghosts:
        if s < top:
            hit(B(bar, s), SN, hv(27, 4), 'L', 'g')
    for s in kicks:
        if s < top:
            hit(B(bar, s), K2, hv((98 if s % 4 == 0 else 86) * dyn), 'RF',
                'a' if s % 4 == 0 else 'n')
    if half_motif:
        play_motif(B(bar), orch=ORCH_TOMS, dyn=dyn, lo=8, hi=16, kick=True)


def samba_feet(bar, dyn=1.0, hi=16):
    for s in (0, 3, 4, 7, 8, 11, 12, 15):
        if s < hi:
            hit(B(bar, s), K2, hv((92 if s % 4 == 0 else 68) * dyn), 'RF', 'n')
    for s in (2, 6, 10, 14):
        if s < hi:
            hit(B(bar, s), HHP, hv(55), 'LF', 'n')


def dbl_feet(bar, lo=0, hi=16, v0=80, v1=96):
    n = hi - lo
    for k, s in enumerate(range(lo, hi)):
        limb = 'RF' if s % 2 == 0 else 'LF'
        v = ramp(k, n, v0, v1) + (14 if s % 4 == 0 else 0)
        hit(B(bar, s), K2, hv(v, 3), limb, 'n')


def latin_feet(bar):
    hit(B(bar, 6), K2, hv(84), 'RF', 'n')
    hit(B(bar, 12), K2, hv(94), 'RF', 'a')
    hit(B(bar, 4), HHP, hv(50), 'LF', 'n')
    hit(B(bar, 12), HHP, hv(50), 'LF', 'n')


CASCARA = [(0, 4, 8, 10, 14), (2, 4, 8, 12)]


def cowbell_bar(bar, idx, dyn=1.0):
    for s in range(0, 16, 2):
        acc = s in CASCARA[idx]
        hit(B(bar, s), COWBELL, hv((96 if acc else 58) * dyn), 'R',
            'a' if acc else 'n')


DESC6 = [SN, T_HI, T_HM, T_LM, FT_HI, FT_LO]
ASC6 = [FT_LO, FT_HI, T_LM, T_HM, T_HI, SN]


# ---------------------------------------------------------------- sections
def sec_intro():
    for bar in range(4):
        for s in (4, 12):
            hit(B(bar, s), HHP, hv(52), 'LF', 'n')
    play_motif(B(0), orch=ORCH_TOMS, dyn=0.8, ghosts=False)
    b = 1
    hit(B(b, 0), SN, hv(100), 'R', 'a'); hit(B(b, 0), K2, hv(92), 'RF', 'a')
    hit(B(b, 3), SN, hv(28), 'L', 'g')
    hit(B(b, 6), FT_HI, hv(92), 'R', 'a')
    hit(B(b, 7), SN, hv(26), 'L', 'g')
    hit(B(b, 10), FT_LO, hv(104), 'R', 'a'); hit(B(b, 10), K2, hv(96), 'RF', 'a')
    hit(B(b, 13), SN, hv(30), 'L', 'g')
    hit(B(b, 14), SN, hv(46), 'R', 'g')
    hit(B(b, 15), SN, hv(62), 'L', 'n')
    play_motif(B(2), orch=ORCH_TOMS, dyn=0.9, ghosts=True)
    play_motif(B(3), orch=ORCH_TOMS, dyn=0.95, hi=8)
    seq = [T_HI, T_HI, T_HM, T_HM, T_LM, T_LM, T_LO, T_LO, FT_HI, FT_HI, FT_LO, FT_LO]
    for i, n in enumerate(seq):
        h = 'R' if i % 2 == 0 else 'L'
        v = ramp(i, 12, 68, 110, 1.3) + (8 if i % 2 == 0 else 0)
        hit(B(3, 8) + i / 6.0, n, hv(v), h, 'a' if i % 2 == 0 else 'n')
    hit(B(3, 8), K2, hv(88), 'RF', 'n')
    hit(B(3, 12), K2, hv(96), 'RF', 'n')
    hit(B(3, 15), K2, hv(104), 'RF', 'a')


def sec_groove():
    groove_bar(4, dyn=0.92, crash_first=True)
    hit(B(4, 0), K2, hv(108), 'RF', 'a')
    groove_bar(5, dyn=0.95, opens=(14,), ghosts=(3, 7, 9, 10, 15), kicks=(0, 6, 10, 11))
    groove_bar(6, dyn=0.97, ghosts=(3, 7), half_motif=True)
    groove_bar(7, dyn=1.0, opens=(6,), kicks=(0, 3, 6, 10, 14), ghosts=(2, 7, 9, 11, 15))
    play_motif(B(8), orch=ORCH_SN, dyn=0.95, rotate=2)
    hhp_quarters(8, 52)
    play_motif(B(9), orch=ORCH_TOMS, dyn=1.0, rotate=2, flams=True, extra_ghosts=True)
    hhp_quarters(9, 54)
    groove_bar(10, dyn=1.02, opens=(6, 14), kicks=(0, 6, 10, 13))
    # bar 11: fill carrying into the downbeat
    seq = [SN, SN, SN, SN, T_HI, T_HI, T_HM, T_HM]
    for i, n in enumerate(seq):
        acc = i % 4 == 0
        v = ramp(i, 8, 55, 86) + (18 if acc else 0)
        hit(B(11, i), n, hv(v), 'R' if i % 2 == 0 else 'L', 'a' if acc else 'n')
    rtoms = [T_HI, T_LM, FT_HI, FT_LO]
    for i in range(12):
        b = B(11, 8) + i / 6.0
        if i % 3 == 0:
            hit(b, rtoms[i // 3], hv(ramp(i, 12, 95, 118)), 'R', 'a')
            hit(b, K2, hv(ramp(i, 12, 88, 110)), 'RF', 'a')
        else:
            hit(b, SN, hv(ramp(i, 12, 42, 70)), 'L', 'g')
    hit(B(11, 0), K2, hv(90), 'RF', 'a')
    hit(B(11, 4), K2, hv(84), 'RF', 'n')


def sec_rudiments():
    pd = 'RLRRLRLL'
    hit(B(12, 0), CR1, hv(116), 'R', 'a'); hit(B(12, 0), K2, hv(108), 'RF', 'a')
    for bar in range(12, 16):
        hhp_quarters(bar, 48, skip=(0,) if bar == 12 else ())
    for i in range(12):
        acc = i % 4 == 0
        v = ramp(i, 12, 40, 62) if acc else ramp(i, 12, 18, 28)
        hit(B(12, 4 + i), SN, hv(v, 2.5), pd[i % 8], 'a' if acc else 'g')
    atoms = [T_HI, T_HM, T_LM, FT_HI]
    for i in range(16):
        acc = i % 4 == 0
        if acc:
            hit(B(13, i), atoms[i // 4], hv(ramp(i, 16, 70, 96)), pd[i % 8], 'a')
        else:
            hit(B(13, i), SN, hv(ramp(i, 16, 26, 38), 2.5), pd[i % 8], 'g')
    hit(B(13, 0), K2, hv(70), 'RF', 'n'); hit(B(13, 8), K2, hv(76), 'RF', 'n')
    acc_drums = [T_HI, T_HM, T_LM, FT_HI, FT_LO, T_HM]
    st = 'RRLL'
    for i in range(24):
        b = B(14) + i / 6.0
        if i % 4 == 0:
            hit(b, acc_drums[i // 4], hv(ramp(i, 24, 70, 110)), st[i % 4], 'a')
        else:
            hit(b, SN, hv(ramp(i, 24, 30, 60)), st[i % 4], 'g')
    for s in (0, 4, 8, 12):
        hit(B(14, s), K2, hv(ramp(s, 13, 80, 100)), 'RF', 'n')
    # bar 15: roll that swells, then flams resolve it
    for i in range(22):
        hit(B(15) + i / 8.0, SN, hv(ramp(i, 22, 22, 118, 1.6), 2.5), st[i % 4],
            'g' if i < 10 else 'n')
    hit(B(15, 8), K2, hv(90), 'RF', 'n')
    for j, (s, n) in enumerate([(12, T_HI), (13, T_LM), (14, FT_HI), (15, FT_LO)]):
        flam(B(15, s), n, hv(108 + 4 * j), 'R' if j % 2 == 0 else 'L')
    for s in (12, 14, 15):
        hit(B(15, s), K2, hv(104), 'RF', 'a')


def sec_toms():
    # bar 16
    samba_feet(16)
    hit(B(16), CR1, hv(118), 'R', 'a'); hit(B(16), K2, hv(110), 'RF', 'a')
    for i in range(1, 12):
        acc = i % 3 == 0
        v = ramp(i, 12, 72, 94) + (16 if acc else 0)
        hit(B(16) + i / 6.0, DESC6[i % 6], hv(v), 'R' if i % 2 == 0 else 'L',
            'a' if acc else 'n')
    hit(B(16, 8), FT_LO, hv(112), 'R', 'a')
    hit(B(16, 10), T_HI, hv(96), 'L', 'a')
    hit(B(16, 11), SN, hv(30), 'R', 'g')
    for i in range(6):
        hit(B(16, 12) + i / 6.0, ASC6[i], hv(ramp(i, 6, 80, 110)),
            'R' if i % 2 == 0 else 'L', 'n')
    # bar 17
    samba_feet(17)
    snake = [T_HI, SN, T_HM, SN, T_LM, SN, FT_HI, SN]
    for i, n in enumerate(snake):
        if i % 2 == 0:
            hit(B(17, i), n, hv(ramp(i, 8, 92, 108)), 'R', 'a')
        else:
            hit(B(17, i), n, hv(34, 4), 'L', 'g')
    for i in range(12):
        acc = i % 3 == 0
        v = ramp(i, 12, 70, 100) + (18 if acc else 0)
        hit(B(17, 8) + i / 6.0, ASC6[i % 6], hv(v), 'R' if i % 2 == 0 else 'L',
            'a' if acc else 'n')
    # bar 18: motif over samba feet
    samba_feet(18)
    play_motif(B(18), orch=ORCH_TOMS, dyn=1.0, kick=False)
    # bar 19: doubles travelling
    samba_feet(19)
    st = 'RRLL'
    pairs = [SN, T_HI, T_HM, T_LM, FT_HI, FT_LO]
    for i in range(24):
        acc = i % 4 == 0
        v = ramp(i, 24, 60, 104) + (16 if acc else 0)
        hit(B(19) + i / 6.0, pairs[(i // 2) % 6], hv(v), st[i % 4], 'a' if acc else 'n')
    # bar 20: hand-hand-foot triplets
    rt = [T_HI, T_HI, T_HM, T_HM, T_LM, T_LM, FT_HI, FT_LO]
    for g in range(8):
        b = B(20) + g * 0.5
        hit(b, rt[g], hv(ramp(g, 8, 100, 116)), 'R', 'a')
        hit(b + 1 / 6.0, SN, hv(ramp(g, 8, 62, 84)), 'L', 'n')
        hit(b + 2 / 6.0, K2, hv(ramp(g, 8, 86, 104)), 'RF', 'n')
    hit(B(20, 4), HHP, hv(52), 'LF', 'n'); hit(B(20, 12), HHP, hv(52), 'LF', 'n')
    # bar 21: groups of four across sextuplets (4 against 6)
    rr = [FT_LO, FT_HI, T_LM, T_HM, T_HI, SN]
    ll = [FT_HI, T_LM, T_HM, T_HI, SN, T_HI]
    for g in range(6):
        b = B(21) + g * 4 / 6.0
        hit(b, rr[g], hv(ramp(g, 6, 104, 120)), 'R', 'a')
        hit(b + 1 / 6.0, ll[g], hv(ramp(g, 6, 70, 92)), 'L', 'n')
        hit(b + 2 / 6.0, K2, hv(ramp(g, 6, 88, 108)), 'RF', 'n')
        hit(b + 3 / 6.0, K1, hv(ramp(g, 6, 84, 104)), 'LF', 'n')
    # bar 22: motif, dense with ghosts
    samba_feet(22)
    play_motif(B(22), orch=ORCH_TOMS, dyn=1.02, kick=False, extra_ghosts=True)
    # bar 23: up-and-down run into the Latin section
    ud = [FT_LO, FT_HI, T_LM, T_HM, T_HI, SN, SN, T_HI, T_HM, T_LM, FT_HI, FT_LO]
    for i in range(24):
        acc = i % 3 == 0
        v = ramp(i, 24, 68, 112) + (12 if acc else 0)
        hit(B(23) + i / 6.0, ud[i % 12], hv(v), 'R' if i % 2 == 0 else 'L',
            'a' if acc else 'n')
    for s in (0, 4, 8, 10, 12, 14, 15):
        hit(B(23, s), K2, hv(ramp(s, 16, 86, 112)), 'RF', 'n')
    hit(B(23, 2), HHP, hv(52), 'LF', 'n'); hit(B(23, 6), HHP, hv(52), 'LF', 'n')


def sec_latin():
    for bar in range(24, 29):
        latin_feet(bar)
    hit(B(24), CR2, hv(118), 'L', 'a'); hit(B(24), K2, hv(110), 'RF', 'a')
    cowbell_bar(24, 0)
    for s in (4, 8):
        hit(B(24, s), CLAVES, hv(88), 'L', 'a')
    cowbell_bar(25, 1)
    for s in (0, 6, 12):
        hit(B(25, s), CLAVES, hv(90), 'L', 'a')
    play_motif(B(26), orch=ORCH_LATIN, dyn=0.95, kick=False)
    agogo = [(0, AGOGO_H, 96), (2, AGOGO_L, 70), (4, AGOGO_H, 80), (7, AGOGO_H, 90),
             (8, AGOGO_L, 76), (10, AGOGO_H, 82), (12, AGOGO_L, 90), (14, AGOGO_H, 84)]
    for s, n, v in agogo:
        hit(B(27, s), n, hv(v), 'R', 'a' if v > 85 else 'n')
    congas = [(2, CONGA_MH, 38, 'g'), (6, CONGA_OH, 92, 'a'), (7, CONGA_OH, 84, 'n'),
              (10, CONGA_MH, 40, 'g'), (14, CONGA_L, 96, 'a'), (15, CONGA_L, 88, 'n')]
    for s, n, v, k in congas:
        hit(B(27, s), n, hv(v), 'L', k)
    play_motif(B(28), orch=ORCH_LATIN, dyn=1.05, rotate=8, flams=True, kick=False)
    # bar 29: timbale abanico and a hit that leaves silence
    st = 'RRLL'
    for i in range(16):
        hit(B(29) + i / 8.0, TIMB_H, hv(ramp(i, 16, 30, 108, 1.5)), st[i % 4],
            'g' if i < 6 else 'n')
    hit(B(29, 8), TIMB_H, hv(118), 'R', 'a'); hit(B(29, 8), K2, hv(104), 'RF', 'a')
    hit(B(29, 10), TIMB_L, hv(100), 'L', 'a')
    hit(B(29, 11), TIMB_L, hv(105), 'R', 'a')
    hit(B(29, 12), CR1, hv(122), 'R', 'a')
    hit(B(29, 12), TIMB_L, hv(115), 'L', 'a')
    hit(B(29, 12), K2, hv(118), 'RF', 'a')
    hit(B(29, 12), K1, hv(110), 'LF', 'a')


def sec_space():
    for bar in (30, 31, 32):
        hhp_quarters(bar, 48)
    hit(B(30, 0), TRI_O, hv(62), 'R', 'n')
    hit(B(30, 6), STICK, hv(45), 'L', 'n')
    hit(B(30, 7), SN, hv(22, 2), 'R', 'g')
    hit(B(30, 10), FT_LO, hv(76), 'R', 'a'); hit(B(30, 10), K2, hv(70), 'RF', 'n')
    hit(B(30, 14), STICK, hv(40), 'L', 'n')
    play_motif(B(31), orch=ORCH_SN, dyn=0.45)
    # bar 32: call and response
    hit(B(32, 0), CR1, hv(120), 'R', 'a'); hit(B(32, 0), K2, hv(115), 'RF', 'a')
    hit(B(32, 1), SN, hv(105), 'L', 'a')
    hit(B(32, 2), SN, hv(30), 'R', 'g')
    flam(B(32, 3), T_HI, hv(118), 'L')
    hit(B(32, 10), SN, hv(24, 2), 'L', 'g')
    hit(B(32, 11), SN, hv(28, 2), 'R', 'g')
    hit(B(32, 13), SN, hv(30, 2), 'L', 'g')
    hit(B(32, 14), FT_LO, hv(92), 'R', 'a'); hit(B(32, 14), K2, hv(88), 'RF', 'a')
    # bar 33: build
    accn = {9: T_HI, 12: T_LM, 15: FT_LO}
    for i in range(16):
        acc = i % 3 == 0
        base = ramp(i, 16, 20, 92, 1.4)
        note = accn.get(i, SN) if acc else SN
        hit(B(33, i), note, hv(base + (22 if acc else 0), 2.5),
            'R' if i % 2 == 0 else 'L', 'a' if acc else ('g' if base < 45 else 'n'))
    for s, v in ((0, 60), (4, 70), (8, 82), (10, 88), (12, 96), (14, 104), (15, 112)):
        hit(B(33, s), K2, hv(v), 'RF', 'n')
    for s in (0, 4, 8):
        hit(B(33, s), HHP, hv(50), 'LF', 'n')


def sec_double_bass():
    dbl_feet(34, v0=78, v1=90)
    hit(B(34, 0), CR1, hv(118), 'R', 'a')
    for s in (4, 8, 12):
        hit(B(34, s), CHINA, hv(98), 'R', 'a')
    hit(B(34, 8), SN, hv(118), 'L', 'a')
    hit(B(34, 14), SN, hv(34), 'L', 'g')
    hit(B(34, 15), SN, hv(52), 'L', 'n')
    dbl_feet(35, v0=82, v1=94)
    for s in range(0, 14, 2):
        hit(B(35, s), CHINA, hv(100 if s % 4 == 0 else 78), 'R', 'a' if s % 4 == 0 else 'n')
    hit(B(35, 3), SN, hv(30), 'L', 'g')
    hit(B(35, 8), SN, hv(118), 'L', 'a')
    hit(B(35, 11), SN, hv(30), 'L', 'g')
    hit(B(35, 14), T_LM, hv(108), 'R', 'a')
    hit(B(35, 15), FT_HI, hv(112), 'L', 'a')
    dbl_feet(36, v0=84, v1=96)
    play_motif(B(36), orch=ORCH_BIG, dyn=1.0, crash=True, kick=False)
    dbl_feet(37, v0=86, v1=100)
    play_motif(B(37), orch=ORCH_BIG, dyn=1.03, rotate=4, crash=True, flams=True, kick=False)
    # bar 38: triplets over sixteenth feet
    dbl_feet(38, v0=88, v1=104)
    toms = [T_HI, T_HM, T_LM, FT_HI, FT_LO, T_HI]
    for i in range(12):
        b = B(38) + i / 3.0
        if i % 2 == 0:
            n = CR1 if i == 0 else toms[i // 2]
            hit(b, n, hv(ramp(i, 12, 96, 120)), 'R', 'a')
        else:
            hit(b, SN, hv(ramp(i, 12, 50, 80)), 'L', 'n')
    # bar 39: 32nd run, then a break into the downbeat
    dbl_feet(39, 0, 12, 90, 106)
    path = [SN, SN, T_HI, T_HI, T_HM, T_HM, T_LM, T_LM, FT_HI, FT_HI, FT_LO, FT_LO]
    for i in range(24):
        acc = i % 4 == 0
        v = ramp(i, 24, 60, 106) + (14 if acc else 0)
        hit(B(39) + i / 8.0, path[i % 12], hv(v), 'R' if i % 2 == 0 else 'L',
            'a' if acc else 'n')
    flam(B(39, 12), SN, hv(120), 'L')
    hit(B(39, 12), K2, hv(112), 'RF', 'a')
    hit(B(39, 14), FT_HI, hv(115), 'R', 'a'); hit(B(39, 14), K2, hv(110), 'RF', 'a')
    hit(B(39, 15), FT_LO, hv(122), 'L', 'a')
    hit(B(39, 15), K2, hv(118), 'RF', 'a'); hit(B(39, 15), K1, hv(114), 'LF', 'a')


def sec_climax():
    play_motif(B(40), orch=ORCH_BIG, dyn=1.08, crash=True, flams=True)
    hit(B(40, 4), HHP, hv(56), 'LF', 'n'); hit(B(40, 12), HHP, hv(56), 'LF', 'n')
    play_motif(B(41), orch=ORCH_BIG, dyn=1.08, rotate=8, crash=True, flams=True,
               extra_ghosts=True)
    # bar 42: diminution - the motif twice as fast, twice
    hit(B(42), CR2, hv(118), 'L', 'a')
    play_motif(B(42), span=2.0, orch=ORCH_BIG, dyn=1.0)
    play_motif(B(42, 8), span=2.0, orch=[T_HM, FT_HI, FT_LO, SN], dyn=1.05)
    # bar 43: 32nd run around the kit, accents in threes
    path = [SN, T_HI, T_HM, T_LM, FT_HI, FT_LO, FT_HI, T_LM, T_HM, T_HI]
    foot = 'RF'
    for i in range(32):
        b = B(43) + i / 8.0
        acc = i % 3 == 0
        h = 'R' if i % 2 == 0 else 'L'
        if acc:
            v = ramp(i, 32, 92, 122)
            n = CR1 if i == 0 else path[i % 10]
            hit(b, n, hv(v), h, 'a')
            hit(b, K2, hv(v - 6), foot, 'a')
            foot = 'LF' if foot == 'RF' else 'RF'
        else:
            hit(b, path[i % 10], hv(ramp(i, 32, 55, 82)), h, 'n')
    # bar 44: stop-time hits echoing the motif's accents
    hit(B(44, 0), CR1, hv(124), 'R', 'a'); hit(B(44, 0), CR2, hv(120), 'L', 'a')
    hit(B(44, 0), K2, hv(120), 'RF', 'a'); hit(B(44, 0), K1, hv(112), 'LF', 'a')
    hit(B(44, 3), CHINA, hv(116), 'R', 'a'); hit(B(44, 3), K2, hv(110), 'RF', 'a')
    hit(B(44, 6), CR2, hv(118), 'L', 'a'); hit(B(44, 6), K2, hv(112), 'RF', 'a')
    flam(B(44, 10), SN, hv(118), 'L')
    hit(B(44, 11), T_HI, hv(106), 'R', 'a')
    hit(B(44, 12), CR1, hv(120), 'R', 'a'); hit(B(44, 12), K2, hv(118), 'RF', 'a')
    flam(B(44, 14), FT_LO, hv(118), 'L')
    hit(B(44, 15), FT_LO, hv(110), 'R', 'a')
    hit(B(44, 15), K2, hv(116), 'RF', 'a'); hit(B(44, 15), K1, hv(115), 'LF', 'a')
    # bar 45: swelling doubles with double bass
    dbl_feet(45, v0=80, v1=112)
    st = 'RRLL'
    cyc = [T_HI, T_HM, T_LM, FT_HI, FT_LO, SN]
    for i in range(24):
        acc = i % 2 == 0
        v = ramp(i, 24, 60, 112) + (10 if acc else 0)
        hit(B(45) + i / 6.0, cyc[(i // 2) % 6], hv(v), st[i % 4], 'a' if acc else 'n')


def sec_ending():
    play_motif(B(46), orch=ORCH_BIG, dyn=1.1, crash=True, flams=True)
    hit(B(46, 4), HHP, hv(58), 'LF', 'n'); hit(B(46, 12), HHP, hv(58), 'LF', 'n')
    # bar 47: six-stroke rolls, then a held-back 32nd descent
    six = 'RLLRRL'
    accR = [T_HI, T_LM]
    accL = [T_HM, FT_HI]
    for i in range(12):
        b = B(47) + i / 6.0
        g, k = divmod(i, 6)
        if k == 0:
            hit(b, accR[g], hv(116), 'R', 'a'); hit(b, K2, hv(108), 'RF', 'a')
        elif k == 5:
            hit(b, accL[g], hv(118), 'L', 'a'); hit(b, K1, hv(108), 'LF', 'a')
        else:
            hit(b, SN, hv(ramp(i, 12, 42, 64)), six[k], 'g')
    path = [T_HI, T_HI, T_HM, T_HM, T_LM, T_LM, FT_HI, FT_HI,
            FT_LO, FT_LO, T_LM, FT_HI, SN, SN, FT_LO, FT_LO]
    for i, n in enumerate(path):
        acc = i % 4 == 0 or i == 15
        v = ramp(i, 16, 78, 124) + (6 if acc else 0)
        hit(B(47, 8) + i / 8.0, n, hv(v), 'R' if i % 2 == 0 else 'L', 'a' if acc else 'n')
    dbl_feet(47, 8, 16, 92, 118)
    # bar 48: the final hit
    hit(B(48), CR1, 127, 'R', 'f')
    hit(B(48), CR2, 125, 'L', 'f')
    hit(B(48), K2, 127, 'RF', 'f')
    hit(B(48), K1, 122, 'LF', 'f')


sec_intro()
sec_groove()
sec_rudiments()
sec_toms()
sec_latin()
sec_space()
sec_double_bass()
sec_climax()
sec_ending()

FINAL_BEAT = 192.0
FINAL_SEC = 117.6
END_SEC = 120.0

# ---------------------------------------------------------------- tempo map
KEYS = [(0, 94), (12, 95), (16, 97), (44, 99), (48, 98), (60, 101), (64, 101),
        (92, 103), (96, 99), (119.5, 99), (120.5, 91), (132, 92), (136, 96),
        (156, 104), (160, 106), (184, 107), (188, 106), (190, 103), (192, 86),
        (400, 86)]
FILL_BARS = {3, 11, 15, 23, 29, 33, 39, 45}


def base_bpm(b):
    for (b0, v0), (b1, v1) in zip(KEYS, KEYS[1:]):
        if b0 <= b <= b1:
            return v0 + (v1 - v0) * (b - b0) / (b1 - b0)
    return KEYS[-1][1]


def micro(beat):
    bar = int(beat // 4)
    pos = beat - bar * 4
    f = 1.0
    if bar in FILL_BARS and pos >= 1.5:          # rush into the downbeat
        f += 0.022 * ((pos - 1.5) / 2.5)
    if (bar - 1) in FILL_BARS and pos < 2.0:     # settle after landing
        f -= 0.008 * (1 - pos / 2.0)
    f += 0.006 * math.sin(2 * math.pi * beat / 16.0)  # phrase breathing
    return f


SEG = 0.25
TPB = 960
TOTAL_BEATS = 208
NSEG = int(TOTAL_BEATS / SEG)
raw = [base_bpm((i + 0.5) * SEG) * micro((i + 0.5) * SEG) for i in range(NSEG)]
dur_final = sum(SEG * 60.0 / raw[i] for i in range(int(FINAL_BEAT / SEG)))
scale = dur_final / FINAL_SEC
US = [int(round(60e6 / (r * scale))) for r in raw]
CUM = [0.0]
for u in US:
    CUM.append(CUM[-1] + u * SEG / 1e6)


def beat_to_sec(b):
    i = max(0, min(NSEG - 1, int(b / SEG)))
    return CUM[i] + (b - i * SEG) * US[i] / 1e6


def sec_to_beat(t):
    i = max(0, min(NSEG - 1, bisect.bisect_right(CUM, t) - 1))
    return i * SEG + (t - CUM[i]) / (US[i] / 1e6)


def sec_to_tick(t):
    return int(round(sec_to_beat(t) * TPB))


# ---------------------------------------------------------------- humanize
def human(kind, limb):
    if kind == 'f':
        return rng.gauss(0, 0.002)
    if limb in ('RF', 'LF'):
        m, sd = -0.001, 0.004
    elif kind == 'a':
        m, sd = -0.002, 0.004
    elif kind == 'g':
        m, sd = 0.005, 0.006
    else:
        m, sd = 0.0, 0.005
    if limb == 'L':
        m += 0.0015
    return max(-0.018, min(0.018, rng.gauss(m, sd)))


EV.sort(key=lambda e: (e[0], e[1], e[3], e[5]))
notes = []
for beat, note, vel, limb, kind, dt in EV:
    t = beat_to_sec(beat) + dt + human(kind, limb)
    notes.append([max(0.0, t), note, vel, limb])
notes.sort(key=lambda n: (n[0], n[1], n[3]))


def enforce(ns, key, gap):
    out, last = [], {}
    for n in ns:
        k = key(n)
        j = last.get(k)
        if j is not None and out[j] is not None and n[0] - out[j][0] < gap(n):
            if n[2] > out[j][2]:
                out[j] = None
                out.append(n)
                last[k] = len(out) - 1
            continue
        out.append(n)
        last[k] = len(out) - 1
    return [n for n in out if n is not None]


# one stroke per limb at a time (=> never more than 2 hands + 2 feet)
notes = enforce(notes, lambda n: n[3], lambda n: 0.06 if n[3] in ('RF', 'LF') else 0.04)
notes = enforce(notes, lambda n: n[1], lambda n: 0.015)
notes.sort(key=lambda n: (n[0], n[1]))

# ---------------------------------------------------------------- write MIDI
CH = 9
end_tick = sec_to_tick(END_SEC)
msgs = []
for i, u in enumerate(US):
    tick = int(i * SEG * TPB)
    if tick > end_tick:
        break
    if i == 0 or u != US[i - 1]:
        msgs.append((tick, 0, 0, mido.MetaMessage('set_tempo', tempo=u)))

by_pitch = {}
for n in notes:
    by_pitch.setdefault(n[1], []).append(n[0])
for p in by_pitch:
    by_pitch[p].sort()

for t, p, v, limb in notes:
    lst = by_pitch[p]
    k = bisect.bisect_right(lst, t)
    nxt = lst[k] if k < len(lst) else t + 10.0
    on = sec_to_tick(t)
    off = max(on + 1, sec_to_tick(min(t + 0.03, nxt - 0.003)))
    msgs.append((on, 2, p, mido.Message('note_on', channel=CH, note=p, velocity=v)))
    msgs.append((off, 1, p, mido.Message('note_off', channel=CH, note=p, velocity=0)))

msgs.sort(key=lambda m: (m[0], m[1], m[2]))

mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
track.append(mido.Message('program_change', channel=CH, program=0, time=0))
track.append(mido.Message('control_change', channel=CH, control=7, value=112, time=0))
track.append(mido.Message('control_change', channel=CH, control=10, value=64, time=0))
now = 0
for tick, _, _, m in msgs:
    track.append(m.copy(time=tick - now))
    now = tick
track.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - now)))
mid.save('solo.mid')
print('wrote solo.mid: %d notes, %.1f s' % (len(notes), mid.length))
