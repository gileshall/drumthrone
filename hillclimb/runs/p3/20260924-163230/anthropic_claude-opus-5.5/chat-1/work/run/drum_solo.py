#!/usr/bin/env python3
# drum_solo.py -- generates solo.mid: a ~2 minute General MIDI drum solo on channel 10.
# Uses only mido. Deterministic (seeded RNG, fixed arithmetic).

import math
import random
import mido

RNG = random.Random(20240611)

# ---------------- General MIDI percussion ----------------
KICK2 = 35; KICK = 36; SS = 37; SN = 38; HHC = 42; HHF = 44; HHO = 46
F_LO = 41; F_HI = 43; T_LO = 45; T_LM = 47; T_HM = 48; T_HI = 50
CR1 = 49; RIDE = 51; CHINA = 52; BELL = 53; SPL = 55; COWB = 56; CR2 = 57
TIMB_H = 65; TIMB_L = 66; WB_H = 76; WB_L = 77
TOMS = [T_HI, T_HM, T_LM, T_LO, F_HI, F_LO]

MOT = [0, 3, 6, 9, 12]           # the motif: 3+3+3+3+4 accents in a bar of 16ths
GROUPS = [(0, 3), (3, 3), (6, 3), (9, 3), (12, 4)]

# ---------------- tempo map (bar, bpm) ----------------
TEMPO = [(0, 108), (4, 110), (12, 114), (19, 121), (20, 112), (26, 104),
         (28, 112), (35, 118), (36, 118), (43, 126), (44, 126), (51, 128),
         (52, 124), (56, 96), (60, 96)]
FINAL_BAR = 56
TARGET_FINAL_SEC = 117.0
LEAD = 0.25

STATE = {'swing': 0.5, 'push': 0.0}
EV = []


def B(b):
    return 16.0 * b


def other(l):
    return 'L' if l == 'R' else 'R'


def H(t16, p, v, limb, ms=0.0, dur=None):
    EV.append((float(t16), p, float(v), limb, ms, dur, STATE['swing'], STATE['push']))


def flam(t16, p, v, limb):
    H(t16, p, v, limb)
    H(t16, p, max(18, v * 0.38), other(limb), ms=-26.0)


# ---------------- building blocks ----------------
def motif_bar(b, acc_p, acc_v, ghost_p=SN, ghost_v=32, shift=0, skip=(), lead='R',
              ghost_ramp=0, kicks=(), hh=(4, 12), hh_v=58, acc_flam=False, alt_ghost=None):
    t0 = B(b)
    acc = [(m + shift) % 16 for m in MOT]
    for i in range(16):
        limb = lead if i % 2 == 0 else other(lead)
        if i in acc:
            k = acc.index(i)
            if acc_flam:
                flam(t0 + i, acc_p[k], acc_v[k], limb)
            else:
                H(t0 + i, acc_p[k], acc_v[k], limb)
        elif i not in skip:
            if alt_ghost is not None and limb == 'R':
                H(t0 + i, alt_ghost[0], alt_ghost[1], limb)
            else:
                H(t0 + i, ghost_p, ghost_v + ghost_ramp * i / 15.0, limb)
    for pos, v in kicks:
        H(t0 + pos, KICK, v, 'K')
    for pos in hh:
        H(t0 + pos, HHF, hh_v, 'H')


def half_call(t0, accv, fill, fillv_hi=104, fillv_lo=86):
    for i in range(8):
        limb = 'R' if i % 2 == 0 else 'L'
        if i in (0, 3, 6):
            H(t0 + i, SN, accv[(0, 3, 6).index(i)], limb)
        else:
            H(t0 + i, SN, 28 + i * 1.5, limb)
    for j, p in enumerate(fill):
        i = 8 + j
        H(t0 + i, p, (fillv_hi if j % 2 == 0 else fillv_lo) + j * 2, 'R' if i % 2 == 0 else 'L')


def linear_bar(b, rp, rv, lv=46, kv=96):
    t0 = B(b)
    for k, (st, ln) in enumerate(GROUPS):
        H(t0 + st, rp[k], rv[k], 'R')
        H(t0 + st + 1, SN, lv + k * 2, 'L')
        H(t0 + st + 2, KICK, kv, 'K')
        if ln == 4:
            H(t0 + st + 3, KICK, kv - 8, 'K')
    H(t0 + 4, HHF, 55, 'H')
    H(t0 + 12, HHF, 58, 'H')


def unison_bar(b, crashes, snp, between, accv, extra32=False):
    t0 = B(b)
    bi = 0
    for k, a in enumerate(MOT):
        H(t0 + a, crashes[k], accv[k], 'R')
        H(t0 + a, snp[k], accv[k] - 6, 'L')
        H(t0 + a, KICK, accv[k], 'K')
        ln = 4 if a == 12 else 3
        if a == 12 and extra32:
            for j in range(6):
                limb = 'R' if j % 2 == 0 else 'L'
                p = [T_HI, T_HM, T_LO, F_HI, F_LO, F_LO][j]
                H(t0 + 13 + j * 0.5, p, 88 + j * 5, limb)
            continue
        for j in range(1, ln):
            limb = 'R' if j % 2 == 1 else 'L'
            H(t0 + a + j, between[bi % len(between)], 76 + j * 5 + k * 2, limb)
            bi += 1


def para_bar(b, accp, accv, kicks, rh=HHC, rhv=62):
    PARA = "RLRRLRLL"
    t0 = B(b)
    for i in range(16):
        limb = PARA[i % 8]
        if i % 4 == 0:
            H(t0 + i, accp[i // 4], accv[i // 4], limb)
        elif limb == 'R':
            H(t0 + i, rh, rhv + (i % 4) * 2, 'R')
        else:
            H(t0 + i, SN, 28 + (i % 4) * 3 + i * 0.5, 'L')
    for pos, v in kicks:
        H(t0 + pos, KICK, v, 'K')


def tomgroups(b, starts, vbase):
    t0 = B(b)
    for k, (st, ln) in enumerate(GROUPS):
        for j in range(ln):
            pos = st + j
            limb = 'R' if pos % 2 == 0 else 'L'
            p = SN if starts[k] is None else TOMS[min(5, starts[k] + j)]
            v = vbase + 16 if j == 0 else vbase - 10 + j * 3
            H(t0 + pos, p, v, limb)


def feet16(b, v=80, acc=96):
    t0 = B(b)
    for i in range(16):
        if i % 2 == 0:
            H(t0 + i, KICK, acc if i % 4 == 0 else v, 'K')
        else:
            H(t0 + i, KICK2, v - 4, 'F')


def feet8(b, v0, v1):
    t0 = B(b)
    for n, i in enumerate(range(0, 16, 2)):
        v = v0 + (v1 - v0) * n / 7.0 + (6 if i % 4 == 0 else 0)
        H(t0 + i, KICK, v, 'K')


def rlk_bar(b, Rp, Lp, v0, v1):
    t0 = B(b)
    for g in range(8):
        t = t0 + g * 2
        c = v0 + (v1 - v0) * g / 7.0
        H(t, Rp[g], c, 'R')
        H(t + 2.0 / 3, Lp[g], c - 12, 'L')
        H(t + 4.0 / 3, KICK, c - 4, 'K')


def roll32(t0, n, v0, v1, pitch=SN, curve=1.4, acc_from=None):
    for j in range(n):
        x = j / float(n - 1)
        v = v0 + (v1 - v0) * x ** curve
        if acc_from is not None and j >= acc_from and j % 4 == 0:
            v += 8
        H(t0 + j * 0.5, pitch, v, 'R' if j % 2 == 0 else 'L')


# ---------------- sections ----------------
def sec1():  # statement
    STATE['swing'] = 0.52; STATE['push'] = 3
    motif_bar(0, [CR1, SN, SN, SN, SN], [114, 92, 98, 104, 114], skip={1, 2, 4, 5, 7, 8, 10, 11},
              ghost_v=30, ghost_ramp=12, kicks=[(0, 112), (6, 88)])
    motif_bar(1, [SN] * 5, [102, 92, 97, 103, 113], skip={1, 4}, ghost_v=25, ghost_ramp=14,
              kicks=[(0, 96), (6, 84), (12, 90)])
    motif_bar(2, [SN, T_HI, T_HM, T_LO, F_LO], [104, 96, 100, 106, 115], ghost_v=28, ghost_ramp=10,
              kicks=[(0, 98), (9, 86), (12, 100)])
    t0 = B(3)
    half_call(t0, [102, 97, 106], [T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_LO], 100, 82)
    for pos, v in ((0, 96), (6, 84), (11, 82), (15, 106)):
        H(t0 + pos, KICK, v, 'K')
    H(t0 + 4, HHF, 58, 'H'); H(t0 + 12, HHF, 60, 'H')


def sec2():  # development
    STATE['swing'] = 0.53; STATE['push'] = 1
    motif_bar(4, [CR1, T_HI, T_HM, F_HI, SN], [118, 100, 104, 108, 114], ghost_v=30, ghost_ramp=8,
              kicks=[(0, 112), (6, 94), (9, 88), (12, 102)])
    motif_bar(5, [SN, SN, T_LO, F_LO, CR2], [104, 98, 104, 110, 118], ghost_v=30, ghost_ramp=10,
              kicks=[(0, 100), (6, 90), (9, 92), (12, 110)])
    STATE['push'] = 0
    t0 = B(6)
    half_call(t0, [106, 98, 104], [T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_HI, F_LO])
    for pos, v in ((0, 100), (6, 88), (8, 96), (12, 100)):
        H(t0 + pos, KICK, v, 'K')
    H(t0 + 4, HHF, 58, 'H')
    motif_bar(7, [T_HI, T_HM, T_LO, F_HI, SN], [100, 102, 106, 110, 116], shift=2, ghost_v=30,
              ghost_ramp=6, kicks=[(0, 100), (8, 94), (14, 106)])
    para_bar(8, [T_HI, SN, F_HI, SN], [104, 100, 108, 112], [(0, 104), (7, 84), (10, 92)])
    para_bar(9, [T_LO, SN, F_LO, CR2], [106, 102, 112, 118], [(0, 104), (3, 84), (10, 92), (12, 108)])
    motif_bar(10, [CR1, CR2, CR1, CR2, CR1], [110, 106, 112, 110, 120], ghost_v=34, ghost_ramp=10,
              kicks=[(p, 108) for p in MOT], hh=())
    STATE['swing'] = 0.5
    t0 = B(11)
    for j in range(16):  # double-stroke roll swelling
        limb = 'R' if (j // 2) % 2 == 0 else 'L'
        v = 42 + j * 3.6
        if j % 2 == 1:
            v *= 0.9
        H(t0 + j * 0.5, SN, v, limb)
    for j, p in enumerate([T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_LO]):
        i = 8 + j
        H(t0 + i, p, (110 if j % 2 == 0 else 92) + j * 1.5, 'R' if i % 2 == 0 else 'L')
    for pos, v in ((0, 90), (8, 96), (10, 100), (12, 104), (14, 110)):
        H(t0 + pos, KICK, v, 'K')


def sec3():  # linear funk, leaning forward
    STATE['swing'] = 0.55; STATE['push'] = -3
    linear_bar(12, [CR1, SN, T_HI, SN, F_HI], [116, 104, 100, 106, 112])
    linear_bar(13, [SN, T_HM, SN, T_LO, CR2], [106, 100, 108, 104, 118])
    STATE['swing'] = 0.5; STATE['push'] = -4
    SIX = "RLLRRL"
    grpR = [T_HI, T_HM, T_LO, F_HI, T_HM, T_LO, F_HI, F_LO]
    for g in range(8):
        b = 14 + g // 4; beat = g % 4; t0 = B(b) + beat * 4
        c = g / 7.0
        for j in range(6):
            t = t0 + j * (4.0 / 6)
            if j == 0:
                H(t, grpR[g], 100 + 14 * c, 'R')
            elif j == 5:
                H(t, SN, 94 + 20 * c, 'L')
            else:
                H(t, SN, 32 + j * 3 + 22 * c, SIX[j])
        H(t0, KICK, 90 + 16 * c, 'K')
        if beat in (1, 3):
            H(t0, HHF, 56, 'H')
    STATE['swing'] = 0.55; STATE['push'] = -5
    unison_bar(16, [CR1, CR2, CR1, CR2, CR1], [SN] * 5,
               [T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_HI, F_LO, F_LO, F_HI, F_LO],
               [116, 108, 112, 110, 120])
    unison_bar(17, [CR2, CR1, CHINA, CR1, CR2], [SN] * 5,
               [F_LO, F_HI, F_HI, T_LO, T_LO, T_HM, T_HM, T_HI, T_HI, SN, T_HI],
               [118, 110, 114, 112, 122])
    STATE['swing'] = 0.5
    rlk_bar(18, [T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_LO],
            [SN, SN, T_HI, T_HI, T_HM, T_HM, T_LO, F_HI], 94, 116)
    STATE['swing'] = 0.55
    t0 = B(19)
    for i, p in enumerate([SN, SN, T_HI, T_HI, T_HM, T_LO, F_HI, F_LO]):
        limb = 'R' if i % 2 == 0 else 'L'
        v = (114 if i % 4 == 0 else 90) + i * 1.5
        if i % 4 == 0:
            flam(t0 + i, p, v, limb)
        else:
            H(t0 + i, p, v, limb)
    for pos, v in ((0, 106), (4, 100), (7, 96)):
        H(t0 + pos, KICK, v, 'K')
    H(t0 + 8, CR1, 125, 'R', dur=0.35)          # choke ... then space
    H(t0 + 8, SN, 120, 'L')
    H(t0 + 8, KICK, 124, 'K')
    H(t0 + 12, HHF, 50, 'H')


def sec4():  # contrast: quiet, laid back, timbales/cowbell
    STATE['swing'] = 0.58; STATE['push'] = 7
    for b in (20, 21):
        t0 = B(b)
        for q in (0, 4, 8, 12):
            H(t0 + q, BELL, 72 if q == 0 else 58, 'R')
        if b == 21:
            H(t0 + 14, BELL, 54, 'R')
            H(t0 + 15, SN, 26, 'L')
        for k, m in enumerate(MOT):
            H(t0 + m, SS, [80, 64, 70, 72, 86][k] + (b - 20) * 3, 'L')
        H(t0, KICK, 74, 'K'); H(t0 + 10, KICK, 56, 'K')
        H(t0 + 4, HHF, 52, 'H'); H(t0 + 12, HHF, 54, 'H')
    motif_bar(22, [TIMB_H] * 5, [84, 74, 78, 82, 92], ghost_p=TIMB_L, ghost_v=26, ghost_ramp=6,
              skip={2, 5, 8, 11, 14}, kicks=[(0, 72), (8, 60)], hh_v=50)
    motif_bar(23, [TIMB_H, TIMB_L, TIMB_H, COWB, COWB], [86, 78, 82, 88, 96], ghost_p=TIMB_L,
              ghost_v=26, ghost_ramp=8, skip={1, 4, 7, 10, 13}, kicks=[(0, 74), (10, 62)], hh_v=50)
    for b in (24, 25):
        t0 = B(b)
        sh = 0 if b == 24 else 2
        for i in range(0, 16, 2):
            H(t0 + i, COWB, 70 if i % 4 == 0 else 52, 'R')
        pits = [TIMB_H, TIMB_H, TIMB_L, TIMB_H, TIMB_L] if b == 24 else [TIMB_L, TIMB_H, TIMB_H, TIMB_L, TIMB_H]
        vels = [84, 80, 86, 88, 92] if b == 24 else [84, 88, 92, 98, 106]
        acc = [(m + sh) % 16 for m in MOT]
        for k, a in enumerate(acc):
            H(t0 + a, pits[k], vels[k], 'L')
        for g in range(1, 16, 2):
            if g not in acc and all(abs(g - a) > 1 for a in acc):
                H(t0 + g, SN, 24 + g * 0.5, 'L')
        H(t0, KICK, 74, 'K'); H(t0 + 8, KICK, 62, 'K')
        H(t0 + 4, HHF, 52, 'H'); H(t0 + 12, HHF, 54, 'H')
    STATE['swing'] = 0.5; STATE['push'] = 3
    t0 = B(26)
    for i in range(16):
        limb = 'R' if i % 2 == 0 else 'L'
        p = TIMB_L if limb == 'R' else TIMB_H
        H(t0 + i, p, 40 + i * 2.5 + (22 if i in MOT else 0), limb)
    for q in (0, 4, 8, 12):
        H(t0 + q, KICK, 62 + q * 1.5, 'K')
    H(t0 + 4, HHF, 50, 'H'); H(t0 + 12, HHF, 52, 'H')
    STATE['push'] = -1
    t0 = B(27)
    for j in range(24):
        limb = 'R' if j % 2 == 0 else 'L'
        if j < 8:
            p = TIMB_H if j % 2 == 0 else TIMB_L
        elif j < 16:
            p = SN
        else:
            p = [T_HI, T_HM, T_LO, F_HI][(j - 16) // 2]
        H(t0 + j * 0.5, p, 66 + j * 2.2 + (10 if j % 4 == 0 else 0), limb)
    H(t0 + 12, F_HI, 118, 'R')
    H(t0 + 13, F_LO, 108, 'L')
    flam(t0 + 14, SN, 120, 'R')
    H(t0 + 15, F_LO, 112, 'L')
    for i in (0, 2, 4, 6, 8, 10):
        H(t0 + i, KICK, 70 + i * 3, 'K')
    H(t0 + 12, KICK, 112, 'K'); H(t0 + 14, KICK, 114, 'K')


def sec5():  # triplets
    STATE['swing'] = 0.5; STATE['push'] = -2
    T8 = 4.0 / 3
    for b, accp in ((28, [CR1, T_HM, F_HI]), (29, [SN, T_LO, CR2])):
        t0 = B(b)
        for i in range(12):
            limb = 'R' if i % 2 == 0 else 'L'
            if i % 4 == 0:
                H(t0 + i * T8, accp[i // 4], 106 + (i // 4) * 5 + (b - 28) * 3, 'R')
            else:
                H(t0 + i * T8, SN, 30 + (i % 4) * 4 + (b - 28) * 4, limb)
        for q in range(4):
            H(t0 + q * 4, KICK, 92 if q == 0 else 58, 'K')
        H(t0 + 4, HHF, 56, 'H'); H(t0 + 12, HHF, 58, 'H')
    R30 = [T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_LO]
    R31 = [F_LO, F_HI, T_LO, T_LO, T_HM, T_HM, T_HI, CR1]
    for b, rp in ((30, R30), (31, R31)):
        t0 = B(b)
        for g in range(8):
            t = t0 + g * 2
            c = (g + (b - 30) * 8) / 15.0
            H(t, rp[g], 96 + 20 * c, 'R')
            H(t + 2.0 / 3, SN, 32 + 20 * c, 'L')
            H(t + 4.0 / 3, SN, 38 + 22 * c, 'L')
        for q in range(4):
            H(t0 + q * 4, KICK, 80 + 10 * (b - 30) + q * 2, 'K')
    for b, hits in ((32, [F_LO, F_HI, T_LO]), (33, [T_HI, T_HM, T_LO])):
        t0 = B(b)
        for k, p in enumerate(hits):
            t = t0 + k * 8.0 / 3
            flam(t, p, 110 + k * 4, 'R')
            H(t, KICK, 104, 'K')
        resp = [SN] * 12 if b == 32 else [T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_HI, F_LO, F_LO, SN, SN]
        for j in range(12):
            H(t0 + 8 + j * 2.0 / 3, resp[j], 48 + j * 5.5, 'R' if j % 2 == 0 else 'L')
        H(t0 + 12, HHF, 54, 'H'); H(t0 + 12, KICK, 90, 'K')
    STATE['push'] = -3
    t0 = B(34)
    for g in range(4):
        t = t0 + g * 4
        H(t, [CR1, CR2, CR1, CHINA][g], 110 + g * 4, 'R')
        H(t + T8, SN, 96 + g * 5, 'L')
        H(t + 2 * T8, KICK, 100 + g * 4, 'K')
    t0 = B(35)
    for j in range(24):
        x = j / 23.0
        p = SN if j < 18 else [T_HI, T_HM, T_LO, T_LO, F_HI, F_LO][j - 18]
        H(t0 + j * 2.0 / 3, p, 42 + 82 * x ** 1.4, 'R' if j % 2 == 0 else 'L')
    for q in range(4):
        H(t0 + q * 4, KICK, 70 + q * 12, 'K')


def sec6():  # double-bass build
    STATE['swing'] = 0.5; STATE['push'] = -4
    motif_bar(36, [CR1, SN, T_LO, SN, F_HI], [120, 106, 104, 108, 112], ghost_v=30, ghost_ramp=8,
              alt_ghost=(HHC, 64), hh=())
    feet8(36, 84, 96)
    motif_bar(37, [CHINA, SN, F_HI, SN, CR2], [118, 108, 108, 110, 120], ghost_v=32, ghost_ramp=8,
              alt_ghost=(HHC, 66), hh=())
    feet8(37, 88, 102)
    t0 = B(38)
    for q, p in zip((0, 4, 8, 12), (CR1, CHINA, CR1, CHINA)):
        H(t0 + q, p, 116 if q == 0 else 104, 'R')
    for pos in (4, 12):
        H(t0 + pos, SN, 118, 'L')
    for pos in (2, 7, 10, 15):
        H(t0 + pos, SN, 34, 'L')
    feet16(38, 82, 98)
    STATE['push'] = -5
    t0 = B(39)
    for k, m in enumerate(MOT):
        H(t0 + m, CHINA if k < 4 else CR1, [114, 108, 112, 110, 122][k], 'R')
    H(t0 + 4, SN, 118, 'L'); H(t0 + 12, SN, 122, 'L')
    H(t0 + 7, SN, 36, 'L'); H(t0 + 10, SN, 38, 'L')
    H(t0 + 13, F_HI, 100, 'R'); H(t0 + 14, SN, 108, 'L'); H(t0 + 15, F_LO, 112, 'R')
    feet16(39, 84, 100)
    tomgroups(40, [0, 2, 1, 3, 0], 96)
    feet16(40, 74, 92)
    tomgroups(41, [1, 3, 2, 3, None], 102)
    feet16(41, 78, 96)
    STATE['push'] = -6
    roll32(B(42), 56, 26, 120, curve=1.6, acc_from=40)
    for q in range(4):
        H(B(42) + q * 4, KICK, 60 + q * 5, 'K')
    for i in range(0, 12, 2):
        H(B(43) + i, KICK, 86 + i * 2, 'K')
    t1 = B(43)
    H(t1 + 12, F_HI, 118, 'R'); H(t1 + 12, KICK, 114, 'K')
    H(t1 + 13, F_LO, 110, 'L'); H(t1 + 13, KICK2, 110, 'F')
    flam(t1 + 14, SN, 122, 'R'); H(t1 + 14, KICK, 116, 'K')
    H(t1 + 15, F_LO, 116, 'L'); H(t1 + 15, KICK2, 116, 'F')


def sec7():  # climax
    STATE['swing'] = 0.5; STATE['push'] = -6
    unison_bar(44, [CR1, CR2, CR1, CHINA, CR1], [SN] * 5,
               [T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_HI, F_LO, F_LO, F_HI, F_LO],
               [124, 114, 118, 116, 124])
    unison_bar(45, [CR2, CR1, CHINA, CR1, CR2], [SN] * 5,
               [F_LO, F_HI, F_HI, T_LO, T_LO, T_HM, T_HM, T_HI], [120, 114, 118, 116, 124], extra32=True)
    motif_bar(46, [CHINA, SPL, CHINA, SPL, CR1], [118, 108, 120, 110, 124], shift=2, ghost_v=38,
              ghost_ramp=10, kicks=[(0, 110), (2, 110), (8, 112), (14, 118)], hh=(4, 12), hh_v=62)
    t0 = B(47)
    path = [SN, SN, T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_HI, F_LO, F_LO,
            F_LO, F_HI, F_HI, T_LO, T_LO, T_HM, T_HM, T_HI, T_HI, SN, SN, SN]
    for j, p in enumerate(path):
        v = 118 if j % 6 == 0 else 82 + j
        H(t0 + j * 2.0 / 3, p, v, 'R' if j % 2 == 0 else 'L')
    for q in range(4):
        H(t0 + q * 4, KICK, 108 + q * 3, 'K')
    H(t0 + 4, HHF, 60, 'H'); H(t0 + 12, HHF, 62, 'H')

    def doubles_bar(b, accmap):
        t0 = B(b)
        for i in range(16):
            limb = 'R' if i % 2 == 0 else 'L'
            if i in accmap:
                p, v, single = accmap[i]
                H(t0 + i, p, v, limb)
                if not single:
                    H(t0 + i + 0.5, p, v * 0.78, limb)
                H(t0 + i, KICK, 108, 'K')
            else:
                H(t0 + i, SN, 40 + i, limb)
                H(t0 + i + 0.5, SN, 34 + i, limb)

    doubles_bar(48, {0: (T_HI, 116, False), 3: (T_HM, 110, False), 6: (T_LO, 112, False),
                     9: (F_HI, 114, False), 12: (F_LO, 120, False)})
    doubles_bar(49, {0: (F_LO, 116, False), 3: (F_HI, 112, False), 6: (T_LO, 114, False),
                     9: (T_HM, 116, False), 12: (CR1, 124, True)})
    rlk_bar(50, [F_LO, F_HI, T_LO, T_LO, T_HM, T_HM, T_HI, SN],
            [F_HI, T_LO, T_LO, T_HM, T_HM, T_HI, T_HI, SN], 98, 124)
    t0 = B(51)
    seq = [T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, F_HI, F_HI, F_LO, F_LO, F_HI, F_LO]
    for i, p in enumerate(seq):
        limb = 'R' if i % 2 == 0 else 'L'
        if i % 4 == 0:
            flam(t0 + i, p, 118, limb)
        else:
            H(t0 + i, p, 92 + i, limb)
    for pos in (0, 4, 8):
        H(t0 + pos, KICK, 116, 'K')
    for j in range(8):
        H(t0 + 12 + j * 0.5, SN, 78 + j * 6.5, 'R' if j % 2 == 0 else 'L')
    H(t0 + 12, KICK, 92, 'K'); H(t0 + 14, KICK, 104, 'K')


def sec8():  # ending
    STATE['swing'] = 0.5; STATE['push'] = -2
    t0 = B(52)
    Rp = [CR1, CHINA, CR2, CHINA, CR1]
    Lp = [SN, T_HI, T_LO, F_HI, SN]
    for k, m in enumerate(MOT):
        v = [124, 114, 118, 116, 126][k]
        H(t0 + m, Rp[k], v, 'R'); H(t0 + m, Lp[k], v - 4, 'L'); H(t0 + m, KICK, v, 'K')
    H(t0 + 4, HHF, 64, 'H')
    H(t0 + 14, SN, 58, 'L'); H(t0 + 15, SN, 72, 'R')
    STATE['push'] = 0
    motif_bar(53, [T_HI, T_HM, T_LO, F_HI, F_LO], [112, 108, 112, 116, 122], ghost_v=34,
              ghost_ramp=14, acc_flam=True, kicks=[(p, 104) for p in MOT], hh=(4,))
    STATE['push'] = 2
    roll32(B(54), 32, 48, 124, curve=1.3)
    feet8(54, 84, 112)
    STATE['push'] = 3
    t0 = B(55)
    path = [T_HI, T_HI, T_HM, T_HM, T_LO, T_LO, T_LO, F_HI, F_HI, F_HI, F_LO, F_LO,
            SN, SN, T_HI, T_HM, T_LO, F_HI]
    for j, p in enumerate(path):
        v = 122 if j % 6 == 0 else 94 + j
        H(t0 + j * 2.0 / 3, p, v, 'R' if j % 2 == 0 else 'L')
    for q in (0, 4, 8):
        H(t0 + q, KICK, 112, 'K')
    H(t0 + 12, F_HI, 120, 'R'); H(t0 + 12, KICK, 118, 'K')
    H(t0 + 13, F_LO, 114, 'L'); H(t0 + 13, KICK2, 116, 'F')
    flam(t0 + 14, SN, 124, 'R'); H(t0 + 14, KICK, 120, 'K')
    H(t0 + 15, F_LO, 118, 'L'); H(t0 + 15, KICK2, 118, 'F')
    STATE['push'] = 0
    tf = B(FINAL_BAR)
    H(tf, CR1, 127, 'R', dur=3.0)
    H(tf, CR2, 127, 'L', dur=3.0)
    H(tf, KICK, 127, 'K', dur=3.0)
    H(tf, KICK2, 127, 'F', dur=3.0)


# ---------------- time conversion ----------------
def bpm_at(beat):
    bar = beat / 4.0
    for (b0, t0), (b1, t1) in zip(TEMPO, TEMPO[1:]):
        if b0 <= bar <= b1:
            return t0 + (t1 - t0) * (bar - b0) / float(b1 - b0)
    return TEMPO[-1][1]


RES = 96
NBEATS = 4 * 60
N = NBEATS * RES
CUM = [0.0] * (N + 1)
for _n in range(N):
    CUM[_n + 1] = CUM[_n] + 60.0 / bpm_at((_n + 0.5) / RES) / RES


def beat_sec(beat):
    x = max(0.0, beat) * RES
    n = int(math.floor(x))
    if n >= N:
        n = N - 1
    return CUM[n] + (CUM[n + 1] - CUM[n]) * (x - n)


SCALE = TARGET_FINAL_SEC / beat_sec(FINAL_BAR * 4.0)


def warp(t16, s):
    e = math.floor(t16 / 2.0 + 1e-9)
    f = (t16 - 2 * e) / 2.0
    if f < 0:
        f = 0.0
    if f < 0.5:
        g = f * s / 0.5
    else:
        g = s + (f - 0.5) * (1 - s) / 0.5
    return (2 * e + 2 * g) / 4.0


PHYS = {'R': 'R', 'L': 'L', 'K': 'K', 'F': 'LF', 'H': 'LF'}
MINGAP = {'R': 0.045, 'L': 0.045, 'K': 0.075, 'LF': 0.075}


def render():
    evs = []
    for (t16, p, v, limb, ms, dur, sw, push) in EV:
        sec = beat_sec(warp(t16, sw)) * SCALE + LEAD
        off = ms
        if limb in ('R', 'L'):
            off += push
            if v < 50:
                off += 4.0
            elif p == SN and v >= 100:
                off += 3.0
        else:
            off -= 1.5
        off += max(-2.5, min(2.5, RNG.gauss(0.0, 1.1)))
        sec += off / 1000.0
        if v >= 50:
            vv = v + RNG.randint(-3, 3)
        else:
            vv = v + RNG.randint(-2, 2)
        vv = max(1, min(127, int(round(vv))))
        evs.append({'t': sec, 'p': p, 'v': vv, 'l': PHYS[limb], 'dur': dur, 'dead': False})
    order = {'R': 0, 'L': 1, 'K': 2, 'LF': 3}
    evs.sort(key=lambda e: (e['t'], order[e['l']], e['p']))
    # limb physics: one stroke per limb, minimum recovery
    last = {}
    for e in evs:
        pe = last.get(e['l'])
        if pe is not None and e['t'] - pe['t'] < MINGAP[e['l']]:
            if e['v'] > pe['v']:
                pe['dead'] = True
                last[e['l']] = e
            else:
                e['dead'] = True
            continue
        last[e['l']] = e
    evs = [e for e in evs if not e['dead']]
    # no duplicated pitch at (nearly) the same instant
    lastp = {}
    for e in evs:
        pe = lastp.get(e['p'])
        if pe is not None and e['t'] - pe['t'] < 0.012:
            if e['v'] > pe['v']:
                pe['dead'] = True
                lastp[e['p']] = e
            else:
                e['dead'] = True
            continue
        lastp[e['p']] = e
    evs = [e for e in evs if not e['dead']]
    # durations
    nxt_l = {}; nxt_p = {}
    for e in reversed(evs):
        gl = nxt_l.get(e['l']); gp = nxt_p.get(e['p'])
        if e['dur'] is not None:
            d = e['dur']
        else:
            d = 0.08
            if gl is not None:
                d = min(d, 0.85 * (gl - e['t']))
            if gp is not None:
                d = min(d, 0.85 * (gp - e['t']))
            d = max(0.008, d)
        e['d'] = d
        nxt_l[e['l']] = e['t']
        nxt_p[e['p']] = e['t']
    return evs


def write(evs, fname="solo.mid"):
    TPB = 480
    TPS = TPB * 2  # 120 bpm file tempo -> 960 ticks per second
    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
    msgs = []
    for e in evs:
        on = int(round(e['t'] * TPS))
        off = max(on + 1, int(round((e['t'] + e['d']) * TPS)))
        msgs.append((on, 1, e['p'], e['v']))
        msgs.append((off, 0, e['p'], 0))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))
    cur = 0
    for tick, kind, p, v in msgs:
        dt = tick - cur
        cur = tick
        if kind == 1:
            tr.append(mido.Message('note_on', channel=9, note=p, velocity=v, time=dt))
        else:
            tr.append(mido.Message('note_off', channel=9, note=p, velocity=0, time=dt))
    tr.append(mido.MetaMessage('end_of_track', time=int(0.3 * TPS)))
    mid.save(fname)


def main():
    sec1(); sec2(); sec3(); sec4(); sec5(); sec6(); sec7(); sec8()
    write(render())


if __name__ == "__main__":
    main()
