#!/usr/bin/env python3
# drum_solo.py - generates solo.mid, a ~2 minute General MIDI drum solo (channel 10)
import math
import random
import mido

rng = random.Random(1964)

# ---------------- General MIDI percussion ----------------
K1 = 35; K = 36; SS = 37; SN = 38; CLAP = 39; SNE = 40
FT2 = 41; HH = 42; FT1 = 43; PED = 44; LT = 45; OH = 46; LMT = 47; HMT = 48
CR = 49; HT = 50; RD = 51; CH = 52; BELL = 53; TAMB = 54; SPL = 55; CB = 56
CR2 = 57; VS = 58; RD2 = 59; HBO = 60; LBO = 61; MCO = 62; OCO = 63; LCO = 64
HTI = 65; LTI = 66; HAG = 67; LAG = 68; CAB = 69; MAR = 70
CLV = 75; HWB = 76; LWB = 77; MTR = 80; OTR = 81
TOMS = [HT, HMT, LMT, LT, FT1, FT2]
CYMS = {CR, CR2, CH, SPL, RD, RD2, BELL, OTR, OH}
FEET = ('RF', 'LF')

EV = []


def hit(beat, note, vel, limb, dur=None, off=0.0):
    EV.append((float(beat), int(note), float(vel), limb, dur, off))


def s16(bar, i): return bar * 4 + i * 0.25
def s6(bar, i): return bar * 4 + i / 6.0
def s32(bar, i): return bar * 4 + i * 0.125


def starts(groups):
    out, a = [], 0
    for g in groups:
        out.append(a); a += g
    return out


MOTIF = [3, 3, 3, 3, 2, 2]
MOT = starts(MOTIF)                       # [0,3,6,9,12,14]
MOT24 = starts([3, 3, 3, 3, 3, 3, 2, 2, 2])


def ramp(i, n, a, b, curve=1.0):
    t = i / max(1, n - 1)
    return a + (b - a) * (t ** curve)


def flam(beat, note, vel, main='R'):
    grace = 'L' if main == 'R' else 'R'
    hit(beat, note, vel * 0.38, grace, off=-0.03)
    hit(beat, note, vel, main)


# ---------------- motif building blocks ----------------
def motif_statement(bar, boost=0, kicks=(9, 14)):
    hit(s16(bar, 0), CR, 112 + boost, 'R', dur=1.5)
    hit(s16(bar, 0), K, 108 + boost, 'RF')
    seq = [(3, HT, 'R', 94), (6, HMT, 'R', 98), (9, SN, 'L', 106),
           (12, FT1, 'R', 104), (14, FT2, 'R', 114)]
    for s, n, l, v in seq:
        hit(s16(bar, s), n, v + boost, l)
    for s in kicks:
        hit(s16(bar, s), K, 98 + boost, 'RF')
    hit(s16(bar, 4), PED, 56, 'LF'); hit(s16(bar, 12), PED, 58, 'LF')


def answer(bar, boost=0):
    for i in range(12):
        limb = 'R' if i % 2 == 0 else 'L'
        v = ramp(i, 12, 28, 46) + boost
        n = SN
        if i == 6: v = 84 + boost
        if i == 10: n = HT; v = 72 + boost
        hit(s16(bar, i), n, v, limb)
    hit(s16(bar, 0), K, 72 + boost, 'RF'); hit(s16(bar, 7), K, 66 + boost, 'RF')
    if boost:
        hit(s16(bar, 10), K, 70 + boost, 'RF')
        hit(s16(bar, 13), SN, 70, 'L'); hit(s16(bar, 14), HT, 88, 'R')
        hit(s16(bar, 15), HMT, 98, 'L')
    hit(s16(bar, 4), PED, 52, 'LF'); hit(s16(bar, 12), PED, 56, 'LF')


def motif_full(bar, boost=0, orch=(SN, HT, HMT, LMT, FT1, FT2), kick=True,
               ghost_note=SN, ped=True):
    acc = dict(zip(MOT, orch))
    for i in range(16):
        limb = 'R' if i % 2 == 0 else 'L'
        if i in acc:
            j = MOT.index(i)
            hit(s16(bar, i), acc[i], 100 + j * 3 + boost, limb)
            if kick and j in (0, 2, 4):
                hit(s16(bar, i), K, 94 + boost, 'RF')
        else:
            hit(s16(bar, i), ghost_note, ramp(i, 16, 30, 48) + boost * 0.5, limb)
    if ped:
        hit(s16(bar, 4), PED, 55, 'LF'); hit(s16(bar, 12), PED, 57, 'LF')


def motif_unison(bar, cyms=(CR, CH, CR2, CH, CR, CR2), toms=(HT, HMT, LMT, LT, FT1, FT2),
                 gl=(40, 80), kick=True, ltom=False):
    idx = 0
    for j, (a, g) in enumerate(zip(MOT, MOTIF)):
        v = 106 + j * 3
        hit(s16(bar, a), cyms[j], v, 'R', dur=0.8)
        hit(s16(bar, a), SN, v, 'L')
        if kick:
            hit(s16(bar, a), K, v - 4, 'RF')
        for k in range(1, g):
            limb = 'L' if k == 1 else 'R'
            if limb == 'L':
                n = toms[j] if ltom else SN
            else:
                n = toms[min(j + 1, 5)] if ltom else toms[j]
            hit(s16(bar, a + k), n, ramp(idx, 10, gl[0], gl[1]), limb)
            idx += 1


def dbl_bass(bar, v_on=90, v_off=76, slots=range(16)):
    for i in slots:
        hit(s16(bar, i), K, v_on if i % 4 == 0 else v_off, 'RF' if i % 2 == 0 else 'LF')


def feet_basic(bar, extra=False, kv=88):
    hit(s16(bar, 0), K, kv, 'RF'); hit(s16(bar, 8), K, kv - 8, 'RF')
    if extra:
        hit(s16(bar, 10), K, kv - 14, 'RF')
    hit(s16(bar, 4), PED, 58, 'LF'); hit(s16(bar, 12), PED, 60, 'LF')


# ---------------- sections ----------------
def sec_intro():                      # bars 0-3
    motif_statement(0)
    answer(1)
    motif_full(2)
    seq16 = [SN, SN, HT, HT, HMT, HMT, LMT, LMT]
    for i, n in enumerate(seq16):
        hit(s16(3, i), n, ramp(i, 8, 62, 92) + (8 if i % 2 == 0 else 0),
            'R' if i % 2 == 0 else 'L')
    seq6 = [LT, LT, FT1, FT1, FT2, FT2, SN, HT, HMT, LMT, FT1, FT2]
    for i, n in enumerate(seq6):
        hit(s6(3, 12 + i), n, ramp(i, 12, 84, 118), 'R' if i % 2 == 0 else 'L')
    hit(s16(3, 0), K, 90, 'RF'); hit(s16(3, 8), K, 96, 'RF'); hit(s16(3, 12), K, 104, 'RF')
    hit(s16(3, 4), PED, 55, 'LF')


KPATS = [[0, 6, 10], [0, 7, 8, 14], [0, 3, 10, 11], [0, 6, 9, 14]]


def groove_bar(bar, ph, upto=16, bell=False, crash=False):
    pos = ph % 4
    for e in range(0, upto, 2):
        if e == 0 and crash:
            hit(s16(bar, 0), CR, 110, 'R', dur=1.2)
            continue
        if bell and e in (6, 14):
            n, v = BELL, 86
        else:
            n, v = RD, (88 if e % 4 == 0 else 66)
        hit(s16(bar, e), n, v, 'R')
    for s in (4, 12):
        if s < upto:
            hit(s16(bar, s), SN, 106 + rng.uniform(-3, 3), 'L')
    for s in (1, 3, 6, 7, 9, 11, 14, 15):
        if s < upto and rng.random() < 0.45 + 0.1 * pos:
            hit(s16(bar, s), SN, 24 + 5 * pos + rng.uniform(0, 8), 'L')
    for s in KPATS[ph % 4]:
        if s < upto:
            hit(s16(bar, s), K, 96 if s == 0 else 84, 'RF')
    for s in (4, 12):
        if s < upto:
            hit(s16(bar, s), PED, 54, 'LF')


def sec_groove():                     # bars 4-11
    for ph in range(8):
        bar = 4 + ph
        if ph == 3:
            groove_bar(bar, ph, upto=8)
            for j, s in enumerate([8, 11, 14]):
                hit(s16(bar, s), [CR, CH, CR][j], 108 + j * 4, 'R', dur=0.8)
                hit(s16(bar, s), SN, 108 + j * 4, 'L')
                hit(s16(bar, s), K, 105, 'RF')
            for k, (s, l) in enumerate([(9, 'L'), (10, 'R'), (12, 'L'), (13, 'R'), (15, 'L')]):
                hit(s16(bar, s), SN, ramp(k, 5, 36, 62), l)
        elif ph == 7:
            motif_unison(bar)
        else:
            groove_bar(bar, ph, bell=(ph >= 4), crash=(ph in (0, 4)))


def sec_flow():                       # bars 12-19
    stick = "RLRRLRLL"
    for b in range(2):
        bar = 12 + b
        feet_basic(bar, extra=(b == 1))
        rt = [HT, HMT, LMT, FT1] if b == 0 else [FT1, LMT, HMT, HT]
        for i in range(16):
            limb = stick[i % 8]
            acc = (i % 4 == 0)
            note = rt[i // 4] if limb == 'R' else SN
            if b == 0 and i == 0:
                note = CR
            v = 100 if acc else ramp(b * 16 + i, 32, 46, 70)
            hit(s16(bar, i), note, v, limb, dur=(1.0 if note == CR else None))
    for b in range(2):
        bar = 14 + b
        rtoms = [HT, HMT, LMT, LT, FT1, FT2] if b == 0 else [CR, HT, CH, LMT, CR2, FT2]
        n = 0
        for j, (a, g) in enumerate(zip(MOT, MOTIF)):
            st = "RLL" if g == 3 else "RL"
            for k in range(g):
                limb = st[k]
                if k == 0:
                    note = rtoms[j]; v = 98 + 4 * j + (6 if b == 1 else 0)
                else:
                    note = SN; v = ramp(b * 10 + n, 20, 40, 66); n += 1
                hit(s16(bar, a + k), note, v, limb, dur=(0.8 if note in CYMS else None))
            if b == 1:
                hit(s16(bar, a), K, 96, 'RF')
        if b == 0:
            feet_basic(bar)
        else:
            hit(s16(bar, 4), PED, 58, 'LF'); hit(s16(bar, 12), PED, 60, 'LF')
    pairs = [(HT, SN), (HMT, HT), (LMT, HMT), (FT1, LMT), (SN, HT), (HMT, SN), (FT1, LT), (FT2, FT1)]
    st = "RLRRLL"
    for bt in range(8):
        R, L = pairs[bt]
        for k in range(6):
            limb = st[k]
            i = bt * 6 + k
            note = R if limb == 'R' else L
            if bt == 0 and k == 0:
                note = CR
            v = ramp(bt, 8, 96, 112) if k == 0 else ramp(i, 48, 48, 86)
            hit(64 + bt + k / 6.0, note, v, limb, dur=(1.0 if note == CR else None))
        hit(64 + bt, K, 86, 'RF')
        if bt % 2 == 1:
            hit(64 + bt, PED, 58, 'LF')
    base = 72
    for i in range(24):
        limb = 'R' if (i // 2) % 2 == 0 else 'L'
        hit(base + i / 6.0, SN, ramp(i, 24, 34, 104, 1.3) + (5 if i % 2 == 0 else 0), limb)
    for bt in range(4):
        hit(base + bt, K, 70 + bt * 8, 'RF')
    hit(base + 1, PED, 55, 'LF'); hit(base + 3, PED, 60, 'LF')
    base = 76
    seq = [HT, HT, HMT, HMT, LMT, LMT, LT, LT, FT1, FT1, FT2, FT2]
    for i, n in enumerate(seq):
        hit(base + i / 6.0, n, ramp(i, 12, 90, 106) + (6 if i % 2 == 0 else 0),
            'R' if i % 2 == 0 else 'L')
    hit(base, K, 96, 'RF'); hit(base + 1, K, 96, 'RF')
    combos = [[('R', HT), ('L', HMT), ('R', LMT), ('L', FT1), ('RF', K), ('LF', K)],
              [('R', SN), ('L', SN), ('R', FT1), ('L', FT2), ('RF', K), ('LF', K)]]
    for bt, cmb in enumerate(combos):
        for k, (limb, n) in enumerate(cmb):
            v = 100 if limb in FEET else ramp(bt * 4 + k, 8, 100, 120)
            hit(base + 2 + bt + k / 6.0, n, v, limb)


def sec_latin():                      # bars 20-27
    hit(s16(20, 0), CR, 116, 'R', dur=2.0); hit(s16(20, 0), K, 114, 'RF')
    hit(s16(20, 0), SN, 104, 'L')
    for bar in range(20, 28):
        for s in (0, 4, 8, 12):
            hit(s16(bar, s), PED, 50 if s == 0 else 43, 'LF')
        if bar < 27:
            for s in (6, 12):
                hit(s16(bar, s), K, 58, 'RF')
    CASC = [0, 2, 3, 5, 6, 8, 10, 11, 13, 14]
    for bar in range(20, 24):
        for s in CASC:
            if bar == 20 and s == 0: continue
            if bar == 23 and s >= 8: continue
            hit(s16(bar, s), HWB, (70 if s % 4 == 0 else 50) + rng.uniform(-3, 3), 'R')
        if bar in (20, 22):
            orch = [LTI, HTI, LTI, HTI, OCO, LCO]
            vels = [78, 70, 76, 72, 84, 88]
            for j, s in enumerate(MOT):
                if bar == 20 and s == 0: continue
                hit(s16(bar, s), orch[j], vels[j], 'L')
        else:
            sl = [1, 3, 6, 7, 10] if bar == 21 else [1, 3, 6, 7]
            for k, s in enumerate(sl):
                hit(s16(bar, s), HBO if k % 2 == 0 else LBO, 45 + rng.uniform(0, 16), 'L')
    for s, n, l, v in [(8, HWB, 'R', 80), (11, LWB, 'L', 78), (14, HWB, 'R', 88)]:
        hit(s16(23, s), n, v, l)
    for bar in (24, 25):
        for e in range(0, 16, 2):
            if bar == 24 and e == 0:
                hit(s16(bar, 0), OTR, 76, 'R', dur=1.5)
                continue
            hit(s16(bar, e), CB, (82 if e % 4 == 0 else 56) + rng.uniform(-3, 3), 'R')
    tumbao = [(0, MCO, 40), (2, MCO, 60), (4, HBO, 45), (6, OCO, 80), (7, OCO, 75),
              (10, MCO, 55), (12, HBO, 45), (14, OCO, 85), (15, LCO, 80)]
    for s, n, v in tumbao:
        hit(s16(24, s), n, v, 'L')
    orch = [OCO, MCO, OCO, LCO, OCO, LCO]
    vels = [70, 62, 74, 80, 86, 92]
    for j, s in enumerate(MOT):
        hit(s16(25, s), orch[j], vels[j], 'L')
    motif_full(26, boost=-6, orch=(HTI, LTI, HTI, LTI, HTI, LTI), kick=False,
               ghost_note=HTI, ped=False)
    base = 27 * 4
    pat = [(HTI, HTI), (LTI, HTI), (LTI, LTI)]
    for i in range(18):
        limb = 'R' if i % 2 == 0 else 'L'
        r, l = pat[i // 6]
        hit(base + i / 6.0, r if limb == 'R' else l, ramp(i, 18, 40, 112, 1.4), limb)
    for bt in range(3):
        hit(base + bt, K, 55 + bt * 17, 'RF')
    hit(base + 3, CR, 120, 'R', dur=0.7); hit(base + 3, LTI, 118, 'L'); hit(base + 3, K, 115, 'RF')


def sec_snare():                      # bars 28-33
    for bar in range(28, 34):
        for s in (0, 4, 8, 12):
            hit(s16(bar, s), PED, 46, 'LF')
    for bar in (28, 29, 30, 31):
        hit(s16(bar, 0), K, 56, 'RF')
    for b in range(2):
        bar = 28 + b
        accs = [(s + 1 + b) % 16 for s in MOT]
        for i in range(16):
            limb = 'R' if i % 2 == 0 else 'L'
            idx = b * 16 + i
            v = ramp(idx, 32, 78, 96) if i in accs else ramp(idx, 32, 20, 34)
            hit(s16(bar, i), SN, v, limb)
    st = "RLRRLL"
    for i in range(48):
        limb = st[i % 6]
        acc = (i % 4 == 0)
        n = SN
        if i == 40: n = HT
        if i == 44: n = HMT
        v = ramp(i, 48, 82, 104) if acc else ramp(i, 48, 26, 46)
        hit(120 + i / 6.0, n, v, limb)
    for i in range(60):
        limb = 'R' if (i // 2) % 2 == 0 else 'L'
        v = 22 + 96 * (i / 59.0) ** 1.7 + (4 if i % 2 == 0 else 0)
        hit(128 + i * 0.125, SN, v, limb)
    for bt in range(8):
        hit(128 + bt, K, 50 + bt * 7, 'RF')
    hit(135.5, HT, 112, 'R'); hit(135.5, K, 104, 'RF')
    hit(135.75, SN, 118, 'L'); hit(135.75, K, 110, 'RF')


def sec_climax():                     # bars 34-45
    for b in range(2):
        bar = 34 + b
        dbl_bass(bar, 90, 76)
        toms = (HT, HMT, LMT, LT, FT1, FT2) if b == 0 else (FT2, FT1, LT, LMT, HMT, HT)
        motif_unison(bar, cyms=(CR, CH, CR2, CH, CR, CH), toms=toms, gl=(60, 84),
                     kick=False, ltom=True)
    pairs = [(HT, SN), (HMT, HT), (LMT, HMT), (FT1, LMT), (FT2, FT1), (LMT, FT1), (HMT, LMT), (HT, HMT)]
    for bt in range(8):
        R, L = pairs[bt]
        base = 36 * 4 + bt
        seq = [('R', R), ('L', L), ('R', R), ('L', L), ('RF', K), ('LF', K)]
        for k, (limb, n) in enumerate(seq):
            if bt == 0 and k == 0:
                n = CR
            if k == 0:
                v = 108
            elif limb in FEET:
                v = 92
            else:
                v = ramp(bt * 6 + k, 48, 72, 96)
            hit(base + k / 6.0, n, v, limb, dur=(1.0 if n == CR else None))
    base = 38 * 4
    cy = [CR, CH, CR2, CH, CR, CR2]
    for j, (a, g) in enumerate(zip(MOT, MOTIF)):
        t0 = base + a * 0.5
        v = 110 + j * 2
        hit(t0, cy[j], v, 'R', dur=1.0); hit(t0, SN, v - 4, 'L'); hit(t0, K, v, 'RF')
        nf = g * 2 - 1
        for k in range(1, g * 2):
            limb = 'L' if k % 2 == 1 else 'R'
            n = TOMS[(j + (k - 1) // 2) % 6]
            hit(t0 + k * 0.25, n, ramp(k - 1, nf, 56, 96), limb)
    for q in range(8):
        hit(base + q, PED, 58, 'LF')
    hit(s16(40, 0), CR, 120, 'R', dur=2.0); hit(s16(40, 0), K, 118, 'RF')
    hit(s16(40, 0), SN, 112, 'L')
    for s in (4, 8, 12):
        hit(s16(40, s), PED, 42, 'LF')
    for s, v in ((8, 52), (11, 56), (14, 62)):
        hit(s16(40, s), SS, v, 'L')
    hit(s16(41, 0), CH, 118, 'R', dur=1.5); hit(s16(41, 0), K, 116, 'RF')
    hit(s16(41, 0), SN, 112, 'L')
    hit(s16(41, 4), PED, 44, 'LF')
    for i in range(12):
        hit(s6(41, 12 + i), SN, ramp(i, 12, 30, 116, 1.5), 'R' if i % 2 == 0 else 'L')
    hit(s16(41, 8), K, 70, 'RF'); hit(s16(41, 12), K, 95, 'RF')
    for b in range(2):
        bar = 42 + b
        dbl_bass(bar, 94, 80)
        cyc = [CR, FT1, CH, FT2, CH, CR2]
        ci = 0
        for i in range(24):
            limb = 'R' if i % 2 == 0 else 'L'
            if i in MOT24:
                if limb == 'R':
                    n = cyc[ci % 6]; ci += 1; v = 112
                else:
                    n = SN; v = 110
            else:
                n = TOMS[(i // 4) % 6]; v = ramp(b * 24 + i, 48, 56, 78)
            hit(s6(bar, i), n, v, limb, dur=(0.8 if n in CYMS else None))
    dbl_bass(44, 86, 76)
    voices = [SN] + TOMS
    for i in range(32):
        hit(s32(44, i), voices[i * 7 // 32], ramp(i, 32, 70, 116), 'R' if i % 2 == 0 else 'L')
    base = 45 * 4
    kc = 0
    for i in range(18):
        p = i % 3
        grp = i // 3
        if p == 2:
            hit(base + i / 6.0, K, 100, 'RF' if kc % 2 == 0 else 'LF'); kc += 1
        else:
            n = TOMS[grp % 6] if p == 0 else TOMS[min(grp + 1, 5)]
            hit(base + i / 6.0, n, ramp(i, 18, 88, 118), 'R' if p == 0 else 'L')
    flam(base + 3, SN, 118, 'R'); hit(base + 3, K, 110, 'RF')
    flam(base + 3.5, FT1, 120, 'R'); hit(base + 3.5, K, 112, 'RF')


def sec_recap():                      # bars 46-53
    motif_statement(46, boost=8, kicks=(3, 6, 9, 12, 14))
    answer(47, boost=18)
    motif_full(48, boost=8)
    orch = [SN, HT, HMT, LMT, LT, FT1, FT2, FT1, FT2]
    idx = 0
    for i in range(24):
        limb = 'R' if i % 2 == 0 else 'L'
        if i in MOT24:
            hit(s6(49, i), orch[idx], 100 + idx * 2, limb)
            hit(s6(49, i), K, 96, 'RF')
            idx += 1
        else:
            hit(s6(49, i), SN, ramp(i, 24, 34, 60), limb)
    hit(s16(50, 0), CR, 120, 'R', dur=2.0); hit(s16(50, 0), K, 118, 'RF')
    hit(s16(50, 0), SN, 110, 'L')
    for s in (4, 8, 12):
        hit(s16(50, s), PED, 44, 'LF')
    for s, v in ((8, 46), (11, 50), (14, 56)):
        hit(s16(50, s), SS, v, 'L')
    for i in range(32):
        limb = 'R' if (i // 2) % 2 == 0 else 'L'
        hit(s32(51, i), SN, ramp(i, 32, 24, 92, 1.4) + (4 if i % 2 == 0 else 0), limb)
    for bt in range(4):
        hit(51 * 4 + bt, K, 60 + bt * 10, 'RF')
        hit(51 * 4 + bt, PED, 50, 'LF')
    for i in range(16):
        limb = 'R' if (i // 2) % 2 == 0 else 'L'
        if i < 8:
            n = HT if limb == 'R' else HMT
        else:
            n = LMT if limb == 'R' else FT1
        hit(s32(52, i), n, ramp(i, 16, 96, 112), limb)
    dbl_bass(52, 92, 82, slots=range(8))
    cmb = [('R', FT1), ('L', FT2), ('R', FT1), ('L', FT2), ('RF', K), ('LF', K)]
    for k, (limb, n) in enumerate(cmb):
        hit(52 * 4 + 2 + k / 6.0, n, 104 if limb in FEET else 108 + k * 3, limb)
    flam(52 * 4 + 3, SN, 120, 'R'); hit(52 * 4 + 3, K, 112, 'RF')
    flam(52 * 4 + 3.5, FT2, 122, 'R'); hit(52 * 4 + 3.5, K, 116, 'RF')
    fb = 53 * 4
    hit(fb, CR, 127, 'R', dur=4.5)
    hit(fb, CH, 124, 'L', dur=4.5)
    hit(fb, K, 127, 'RF', dur=1.0)
    hit(fb, K1, 122, 'LF', dur=1.0)


FINAL_BEAT = 212.0

# ---------------- tempo map ----------------
KEYS = [(0, 98), (16, 101), (16, 104), (48, 107), (48, 110), (80, 113), (80, 105),
        (112, 106), (112, 107), (136, 116), (136, 120), (160, 121), (160, 117),
        (168, 116), (168, 122), (184, 124), (184, 118), (200, 120), (200, 112),
        (204, 112), (211, 124), (212, 113), (240, 113)]


def base_bpm(b):
    for i in range(len(KEYS) - 1):
        b0, v0 = KEYS[i]; b1, v1 = KEYS[i + 1]
        if b0 <= b < b1:
            return v0 + (v1 - v0) * (b - b0) / (b1 - b0)
    return KEYS[-1][1]


def bpm(b):
    p = (b % 16.0) / 16.0
    push = 1.0 + 0.022 * p ** 3          # rush toward phrase end, settle on downbeat
    return base_bpm(b) * push


STEP = 1.0 / 96
NSTEP = int(236 / STEP)
TT = [0.0]
for _k in range(NSTEP):
    TT.append(TT[-1] + STEP * 60.0 / bpm((_k + 0.5) * STEP))


def sec(beat):
    x = beat / STEP
    k = int(math.floor(x))
    f = x - k
    return TT[k] + (TT[k + 1] - TT[k]) * f


# ---------------- render ----------------
LIMB_ORDER = {'RF': 0, 'LF': 1, 'R': 2, 'L': 3}


def render():
    evs = sorted(EV, key=lambda e: (e[0] + e[5] * 0.0, LIMB_ORDER[e[3]], e[1], e[2]))
    scale = 116.0 / sec(FINAL_BEAT)
    nom = [sec(e[0]) * scale + e[5] for e in evs]
    gap = [1.0] * len(evs)
    for limb in ('R', 'L', 'RF', 'LF'):
        ids = sorted([i for i, e in enumerate(evs) if e[3] == limb], key=lambda i: (nom[i], i))
        for a, b in zip(ids, ids[1:]):
            d = nom[b] - nom[a]
            gap[a] = min(gap[a], d); gap[b] = min(gap[b], d)
    hum = []
    drift = 0.0
    for idx, e in enumerate(evs):
        beat, note, vel, limb, dur, off = e
        drift = drift * 0.9 + rng.gauss(0, 0.0015)
        if limb in FEET:
            sd = 0.004; bias = -0.002 if note in (K, K1) else 0.003
        elif vel >= 90:
            sd = 0.004; bias = -0.0015
        elif vel >= 50:
            sd = 0.006; bias = 0.0
        else:
            sd = 0.008; bias = 0.005
        f = min(1.0, gap[idx] / 0.14)
        j = max(-2.5 * sd, min(2.5 * sd, rng.gauss(0, sd)))
        if beat == FINAL_BEAT:
            j = 0.0; bias = 0.0
        t = nom[idx] + drift * f + (j + bias) * f
        v = int(round(vel + rng.gauss(0, 2.5)))
        v = max(1, min(127, v))
        if dur is None:
            dur = 0.5 if note in CYMS else 0.1
        hum.append((t, note, v, limb, dur))
    kept = []
    for limb in ('R', 'L', 'RF', 'LF'):
        items = sorted([h for h in hum if h[3] == limb], key=lambda h: (h[0], h[1]))
        mg = 0.035 if limb in ('R', 'L') else 0.07
        lst = []
        for it in items:
            if lst and it[0] - lst[-1][0] < mg:
                if it[2] > lst[-1][2]:
                    lst[-1] = it
                continue
            lst.append(it)
        kept.extend(lst)
    kept.sort(key=lambda h: (h[0], h[1]))
    LEAD = 0.25
    msgs = []
    bynote = {}
    for h in kept:
        bynote.setdefault(h[1], []).append(h)
    for note in sorted(bynote):
        lst = sorted(bynote[note], key=lambda h: h[0])
        for i, h in enumerate(lst):
            on = h[0] + LEAD
            offt = on + h[4]
            if i + 1 < len(lst):
                offt = min(offt, lst[i + 1][0] + LEAD - 0.003)
            offt = max(offt, on + 0.005)
            ton = int(round(on * 1920)); toff = int(round(offt * 1920))
            if toff <= ton:
                toff = ton + 1
            msgs.append((ton, 1, note, h[2]))
            msgs.append((toff, 0, note, 0))
    msgs.sort()
    mid = mido.MidiFile(type=0, ticks_per_beat=960)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
    last = 0
    for tick, kind, note, vel in msgs:
        d = tick - last
        last = tick
        if kind == 1:
            tr.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=d))
        else:
            tr.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=d))
    tr.append(mido.MetaMessage('end_of_track', time=240))
    mid.save('solo.mid')


def main():
    sec_intro()
    sec_groove()
    sec_flow()
    sec_latin()
    sec_snare()
    sec_climax()
    sec_recap()
    render()


if __name__ == '__main__':
    main()
