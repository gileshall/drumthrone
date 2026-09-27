#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a roughly two-minute General MIDI drum solo on channel 10.

The solo is built around one motif: a 3+3+2+3+3+2 accent cell (motif A), answered by a
flammed call-and-response bar (motif B). It moves through these sections:
statement -> groove -> development -> Latin interlude -> build -> climax ->
breakdown -> finale, and ends on a single final hit.

Every note is assigned to a limb (R, L, RF, LF). A limb can strike only one note at a
time, so at most two hands and two feet sound at any instant.

The tempo breathes through a tempo map. The feel comes from fixed swing and push or
lay-back offsets, plus a very small seeded humanisation, so every run writes the same file.
"""
import random
import mido

TPB = 480
BAR = 4 * TPB
S16 = TPB // 4      # 120
S32 = TPB // 8      # 60
SEXT = TPB // 6     # 80
TRIP = TPB // 3     # 160
MIN_GAP = 50        # minimum ticks between two strokes of the same limb

# General MIDI percussion
KICK, KICK2 = 36, 35
SN, XSTK = 38, 37
HHC, HHP, HHO = 42, 44, 46
T1, T2, T3, T4, F1, F2 = 50, 48, 47, 45, 43, 41
TOMS = [T1, T2, T3, T4, F1, F2]
CRASH, CRASH2, CHINA, SPLASH = 49, 57, 52, 55
RIDE, BELL = 51, 53
COWBELL, TIMB_H, TIMB_L = 56, 65, 66
AGO_H, AGO_L, CLAVES = 67, 68, 75
CONGA_MH, CONGA_OH, CONGA_L = 62, 63, 64

ACC = [0, 3, 6, 8, 11, 14]          # motif A: 3+3+2+3+3+2 in sixteenths
LIMB = {'R': 'R', 'L': 'L', 'K': 'RF', 'F': 'LF'}

# tempo anchors (bar position, bpm) - leans forward in the heat, settles in release
ANCH = [(0, 100), (4, 102), (8, 104), (16, 107), (23, 113), (24, 112), (25, 107),
        (31, 106), (32, 105), (36, 112), (38, 117), (44, 121), (46, 118),
        (47, 106), (49, 106), (50, 110), (54, 116)]
PUSH_BARS = {3, 7, 11, 15, 19, 23, 31, 37, 45, 49, 53}

FEEL = [(0, 8, dict(swing=10, push=0, lay=6)),
        (8, 16, dict(swing=18, push=-3, lay=10)),
        (16, 24, dict(swing=8, push=-5, lay=4)),
        (24, 32, dict(swing=0, push=-2, lay=0)),
        (32, 38, dict(swing=0, push=-6, lay=0)),
        (38, 46, dict(swing=0, push=-8, lay=0)),
        (46, 50, dict(swing=14, push=4, lay=10)),
        (50, 999, dict(swing=10, push=-4, lay=6))]

FINAL_BAR = 54
TARGET_FINAL_SEC = 117.0
RING_SEC = 3.0


def interp(anchors, x):
    if x <= anchors[0][0]:
        return anchors[0][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return anchors[-1][1]


def feel_for(bar):
    for a, b, f in FEEL:
        if a <= bar < b:
            return f
    return FEEL[-1][2]


class Solo:
    def __init__(self):
        self.ev = []

    # ---------- primitives ----------
    def hit(self, t, note, vel, limb, pri=1, sw=False, kind='n'):
        self.ev.append({'t': int(t), 'note': note,
                        'vel': max(1, min(127, int(round(vel)))),
                        'limb': limb, 'pri': pri, 'sw': sw, 'kind': kind})

    def flam(self, t, note, vel, lead='R'):
        other = 'L' if lead == 'R' else 'R'
        self.hit(t - 24, note, vel * 0.42, other, 0, False, 'grace')
        self.hit(t, note, vel, lead, 2, False, 'acc')

    def land(self, t, vel=118, cym=CRASH, cym2=None, kick=True, kick2=False):
        self.hit(t, cym, vel, 'R', 3, False, 'acc')
        if cym2:
            self.hit(t, cym2, vel - 4, 'L', 3, False, 'acc')
        if kick:
            self.hit(t, KICK, vel, 'RF', 3, False, 'kick')
        if kick2:
            self.hit(t, KICK2, vel - 6, 'LF', 3, False, 'kick')

    # ---------- bar vocabularies ----------
    def motif(self, b, voices, taps='all', tap=SN, tap_vel=32, acc=(100, 112),
              kick=True, hatfoot=True, shift=0, start=0, end=16, sw=True):
        t0 = b * BAR
        for p in range(start, end):
            q = (p - shift) % 16
            limb = 'R' if p % 2 == 0 else 'L'
            t = t0 + p * S16
            x = p / 15.0
            if q in ACC:
                k = ACC.index(q)
                v = acc[0] + (acc[1] - acc[0]) * x + (6 if q == 0 else 0)
                self.hit(t, voices[k], v, limb, 2, sw, 'acc')
                if kick:
                    self.hit(t, KICK, v - 10, 'RF', 1, sw, 'kick')
            elif taps == 'all' or (taps == 'some' and q % 2 == 1):
                note = tap(p, limb) if callable(tap) else tap
                v = tap_vel + (8 if (q + 1) % 16 in ACC else 0) + 6 * x
                self.hit(t, note, v, limb, 0, sw, 'ghost')
            if hatfoot and p in (4, 12):
                self.hit(t, HHP, 58, 'LF', 1, sw, 'foot')

    def answer(self, b, dyn=1.0, var=0):
        t0 = b * BAR
        if var == 0:
            seq = [(2, 'R', SN, 26), (3, 'L', SN, 34), (6, 'R', T1, 100, 1),
                   (7, 'L', SN, 30), (9, 'L', T2, 92), (10, 'R', T4, 98),
                   (11, 'L', SN, 30), (13, 'L', SN, 38), (14, 'R', F2, 108, 1)]
            kicks = [0, 10, 14]
        else:
            seq = [(1, 'L', SN, 28), (2, 'R', SN, 34), (5, 'L', SN, 30),
                   (6, 'R', T2, 102, 1), (8, 'R', T3, 94), (9, 'L', SN, 30),
                   (10, 'R', F1, 100, 1), (12, 'R', SN, 112, 1), (13, 'L', SN, 40),
                   (14, 'R', F2, 110), (15, 'L', F2, 96)]
            kicks = [0, 6, 10, 14]
        for item in seq:
            p, l, n, v = item[:4]
            t = t0 + p * S16
            if len(item) > 4:
                self.flam(t, n, v * dyn, l)
            else:
                strong = v > 80
                self.hit(t, n, v * dyn, l, 2 if strong else 0, True,
                         'acc' if strong else 'ghost')
        for p in kicks:
            self.hit(t0 + p * S16, KICK, (94 if p == 0 else 86) * dyn, 'RF', 1, True, 'kick')
        for p in (4, 12):
            self.hit(t0 + p * S16, HHP, 56, 'LF', 1, True, 'foot')

    GK = [[0, 3, 6, 10], [0, 6, 8, 11], [0, 3, 6, 11, 14], [0, 3, 8, 10, 13]]
    GG = [[7, 9, 15], [1, 7, 10, 15], [3, 7, 9, 13, 15], [2, 7, 9, 11, 14]]

    def groove(self, b, var, dyn=1.0, until=16, ride=False, crash0=False):
        t0 = b * BAR
        for p in range(until):
            t = t0 + p * S16
            if p % 2 == 0:
                if p == 0 and crash0:
                    self.hit(t, CRASH, 116 * dyn, 'R', 3, True, 'acc')
                elif ride:
                    if p % 4 == 0:
                        self.hit(t, BELL, 84 * dyn, 'R', 1, True, 'hat')
                    else:
                        self.hit(t, RIDE, 70 * dyn, 'R', 1, True, 'hat')
                else:
                    note = HHO if (var % 2 == 1 and p == 14) else HHC
                    v = 88 if p % 4 == 0 else 64
                    self.hit(t, note, v * dyn, 'R', 1, True, 'hat')
            if p in (4, 12):
                self.hit(t, SN, (110 if p == 12 else 104) * dyn, 'L', 2, True, 'bb')
            elif p in self.GG[var]:
                v = 28 + (8 if (p + 1) % 16 in (4, 12) else 0)
                self.hit(t, SN, v, 'L', 0, True, 'ghost')
            if p in self.GK[var]:
                self.hit(t, KICK, (104 if p == 0 else 88) * dyn, 'RF', 1, True, 'kick')
            if ride and p in (4, 12):
                self.hit(t, HHP, 62, 'LF', 1, True, 'foot')

    def latin(self, b, cyc, alt=False, until=16):
        CASC = [[0, 4, 8, 10, 14], [0, 4, 6, 10, 14]]
        CLAVE = [[0, 6, 12], [4, 8]]
        LG = {2: (CONGA_MH, 46), 10: (CONGA_OH, 68), 14: (CONGA_L, 60)}
        t0 = b * BAR
        for p in range(until):
            t = t0 + p * S16
            if p in CASC[cyc]:
                if alt:
                    note = AGO_H if p in (0, 6) else AGO_L
                else:
                    note = COWBELL
                self.hit(t, note, 96 if p == 0 else 78, 'R', 1, False, 'hat')
            if p in CLAVE[cyc]:
                self.hit(t, CLAVES, 84, 'L', 1, False, 'n')
            elif p in LG:
                n, v = LG[p]
                self.hit(t, n, v, 'L', 0, False, 'ghost')
            if p in (6, 12) or (p == 0 and cyc == 0):
                self.hit(t, KICK, 82 if p else 70, 'RF', 1, False, 'kick')
            if p % 4 == 0:
                self.hit(t, HHP, 50 if p % 8 else 58, 'LF', 1, False, 'foot')

    def aug(self, b, voices, v0=30, v1=64):
        ACC2 = [0, 6, 12, 16, 22, 28]
        for p in range(32):
            t = b * BAR + p * S16
            limb = 'R' if p % 2 == 0 else 'L'
            x = p / 31.0
            if p in ACC2:
                k = ACC2.index(p)
                self.hit(t, voices[k], 104 + 12 * x, limb, 2, True, 'acc')
                self.hit(t, KICK, 96, 'RF', 1, True, 'kick')
            else:
                v = v0 + (v1 - v0) * x + (10 if (p + 1) in ACC2 else 0)
                self.hit(t, SN, v, limb, 0, True, 'ghost')
            if p % 4 == 0 and p not in ACC2:
                self.hit(t, HHP, 55, 'LF', 1, True, 'foot')

    def stops(self, b, toms=False, end=16):
        t0 = b * BAR
        for k, q in enumerate(ACC):
            if q >= end:
                continue
            t = t0 + q * S16
            limb = 'R' if q % 2 == 0 else 'L'
            if limb == 'R':
                note = TOMS[k] if toms else (CRASH if q in (0, 8) else CHINA)
                self.hit(t, note, 118, 'R', 2, False, 'acc')
                if q == 0:
                    self.hit(t, SN, 116, 'L', 2, False, 'acc')
            else:
                self.flam(t, TOMS[k] if toms else SN, 116, 'L')
            self.hit(t, KICK, 112, 'RF', 2, False, 'kick')
        for p in (4, 12):
            if p < end:
                self.hit(t0 + p * S16, HHP, 50, 'LF', 1, False, 'foot')

    def dbl(self, b, v=90, start=0, end=16):
        for p in range(start, end):
            t = b * BAR + p * S16
            limb = 'RF' if p % 2 == 0 else 'LF'
            note = KICK if limb == 'RF' else KICK2
            self.hit(t, note, v + (12 if p % 4 == 0 else 0), limb, 1, False, 'kick')

    def hemi(self, b, v0=30, v1=72, a0=86, a1=114):
        t0 = b * BAR
        for i in range(24):
            ch = 'R' if i % 2 == 0 else 'L'
            x = i / 23.0
            t = t0 + i * SEXT
            if i % 4 == 0:
                note = TOMS[min(5, (i // 4) * 6 // 6)]
                self.hit(t, note, a0 + (a1 - a0) * x, ch, 2, False, 'acc')
            else:
                self.hit(t, SN, v0 + (v1 - v0) * x, ch, 0, False, 'ghost')
            if i % 6 == 0:
                self.hit(t, KICK, 78 + 20 * x, 'RF', 1, False, 'kick')
            if i in (6, 18):
                self.hit(t, HHP, 60, 'LF', 1, False, 'foot')

    def pdd(self, b, v0=55, v1=105, a0=90, a1=122):
        # paradiddle-diddle sextuplets travelling down the toms
        st = 'RLRRLL'
        t0 = b * BAR
        for i in range(24):
            ch = st[i % 6]
            x = i / 23.0
            t = t0 + i * SEXT
            if i % 6 == 0:
                note = TOMS[min(5, (i // 6) * 6 // 4)]
                self.hit(t, note, a0 + (a1 - a0) * x, ch, 2, False, 'acc')
                self.hit(t, KICK, 84 + 16 * x, 'RF', 1, False, 'kick')
            else:
                note = F1 if i % 6 in (2, 3) else SN
                self.hit(t, note, (v0 + (v1 - v0) * x) * 0.6, ch, 0, False, 'ghost')
            if i in (6, 18):
                self.hit(t, HHP, 60, 'LF', 1, False, 'foot')

    # ---------- fills ----------
    def down16(self, t, n, path, v0, v1, kick=True):
        for i in range(n):
            x = i / max(1, n - 1)
            v = v0 + (v1 - v0) * x + (8 if i % 4 == 0 else 0)
            note = path[min(len(path) - 1, i * len(path) // n)]
            tt = t + i * S16
            self.hit(tt, note, v, 'R' if i % 2 == 0 else 'L', 1, False, 'run')
            if kick and i % 4 == 0:
                self.hit(tt, KICK, v * 0.85, 'RF', 1, False, 'kick')

    def sext_linear(self, t, n, pat, path, v0, v1):
        hand_total = sum(1 for i in range(n) if pat[i % len(pat)] in 'RL')
        h = 0
        for i in range(n):
            ch = pat[i % len(pat)]
            x = i / max(1, n - 1)
            v = v0 + (v1 - v0) * x + (10 if i % len(pat) == 0 else 0)
            tt = t + i * SEXT
            if ch in 'RL':
                note = path[min(len(path) - 1, h * len(path) // max(1, hand_total))]
                h += 1
                self.hit(tt, note, v, ch, 1, False, 'run')
            elif ch == 'K':
                self.hit(tt, KICK, v * 0.9, 'RF', 1, False, 'kick')
            else:
                self.hit(tt, KICK2, v * 0.9, 'LF', 1, False, 'kick')

    def roll32(self, t, n, note, v0, v1, acc=None, stick='RRLL', kick_acc=True):
        acc = acc or {}
        for i in range(n):
            ch = stick[i % len(stick)]
            x = i / max(1, n - 1)
            v = v0 + (v1 - v0) * (x ** 1.3)
            if i % 2 == 1:
                v *= 0.9
            tt = t + i * S32
            if i in acc:
                self.hit(tt, acc[i], min(127, v + 30), ch, 2, False, 'acc')
                if kick_acc:
                    self.hit(tt, KICK, min(127, v + 15), 'RF', 1, False, 'kick')
            else:
                self.hit(tt, note, v, ch, 1, False, 'roll')

    def para16(self, t, n, path, v0, v1):
        st = 'RLRRLRLL'
        groups = (n + 3) // 4
        for i in range(n):
            ch = st[i % 8]
            x = i / max(1, n - 1)
            v = v0 + (v1 - v0) * x
            tt = t + i * S16
            if i % 4 == 0:
                note = path[min(len(path) - 1, (i // 4) * len(path) // groups)]
                self.hit(tt, note, v + 10, ch, 2, False, 'acc')
                self.hit(tt, KICK, v * 0.85, 'RF', 1, False, 'kick')
            else:
                self.hit(tt, SN, v * 0.5, ch, 0, False, 'ghost')

    def flam_trip(self, t, n, path, v0, v1, kick=True):
        for i in range(n):
            lead = 'R' if i % 2 == 0 else 'L'
            note = path[min(len(path) - 1, i * len(path) // n)]
            x = i / max(1, n - 1)
            v = v0 + (v1 - v0) * x
            tt = t + i * TRIP
            self.flam(tt, note, v, lead)
            if kick and i % 3 == 0:
                self.hit(tt, KICK, v * 0.9, 'RF', 1, False, 'kick')

    # ---------- the composition ----------
    def compose(self):
        B = lambda b: b * BAR

        # I. Statement (0-7): motif A, answer B, travel it around the kit
        self.motif(0, [CRASH, SN, F2, SN, F1, F2], taps='none', acc=(108, 116))
        self.answer(1, 0.9, 0)
        self.motif(2, TOMS, taps='some', acc=(90, 108))
        self.motif(3, [T1, SN, T3, SN, F1, F2], taps='all', acc=(95, 105), end=8)
        self.down16(B(3) + 8 * S16, 8, TOMS, 74, 112)
        self.motif(4, [CRASH, SN, T3, SN, F1, F2], taps='all', acc=(102, 114))
        self.answer(5, 1.0, 1)
        self.motif(6, TOMS, taps='all', shift=2, acc=(98, 112))
        self.motif(7, [CRASH2, SN, T2, SN, T4, F2], taps='all', acc=(100, 110), end=8)
        self.sext_linear(B(7) + 8 * S16, 12, 'RLK', TOMS, 72, 116)

        # II. Groove (8-15): motif A lives in the kick, ghost notes against backbeat
        self.groove(8, 0, crash0=True)
        self.groove(9, 1)
        self.groove(10, 0)
        self.groove(11, 2, until=8)
        self.roll32(B(11) + 8 * S16, 16, SN, 40, 108)
        self.groove(12, 2, ride=True, crash0=True)
        self.groove(13, 3, ride=True)
        self.groove(14, 2, ride=True)
        self.groove(15, 3, ride=True, until=8)
        self.para16(B(15) + 8 * S16, 8, [T1, T2, T4, F2], 75, 115)

        # III. Development (16-23): displacement, sextuplets, augmentation
        self.motif(16, [CRASH, T1, T3, SN, T4, F2], taps='all', acc=(100, 112))
        self.motif(17, TOMS, taps='all', shift=2, acc=(98, 114))
        self.pdd(18)
        self.motif(19, [CRASH, SN, T2, SN, T4, F2], taps='all', acc=(100, 112), end=8)
        self.flam_trip(B(19) + 8 * S16, 6, TOMS, 82, 118)
        self.aug(20, [CRASH, F2, T1, CRASH2, F1, T2])
        self.sext_linear(B(22), 12, 'RLK', TOMS, 80, 105)
        self.sext_linear(B(22) + 2 * TPB, 12, 'RLRK', TOMS, 95, 118)
        acc = {p * 2: TOMS[k] for k, p in enumerate(ACC)}
        self.roll32(B(23), 32, SN, 45, 98, acc)

        # IV. Latin interlude (24-31): release, different colours, motif on timbales
        self.land(B(24), 112, CRASH)
        for b in range(24, 30):
            if b == 27:
                self.latin(27, 1, until=12)
                self.roll32(B(27) + 12 * S16, 8, TIMB_H, 50, 104, kick_acc=False)
            else:
                self.latin(b, (b - 24) % 2, alt=(b >= 28))
        self.hit(B(28), TIMB_H, 112, 'L', 3, False, 'acc')
        self.motif(30, [COWBELL, TIMB_H, TIMB_L, COWBELL, TIMB_H, TIMB_L],
                   taps='some', tap=CONGA_MH, tap_vel=40, acc=(92, 108), sw=False)
        self.roll32(B(31), 8, TIMB_H, 55, 100, kick_acc=False)
        self.hit(B(31) + 4 * S16, TIMB_L, 112, 'R', 2, False, 'acc')
        self.hit(B(31) + 4 * S16, KICK, 100, 'RF', 1, False, 'kick')
        self.hit(B(31) + 6 * S16, TIMB_H, 92, 'L', 2, False, 'acc')
        self.hit(B(31) + 4 * S16, HHP, 55, 'LF', 1, False, 'foot')
        self.down16(B(31) + 8 * S16, 8, TOMS, 78, 116)

        # V. Build (32-37): taps thicken 16ths -> sextuplets -> 32nds -> swell
        self.motif(32, [CRASH, SN, SN, SN, SN, SN], taps='all', tap_vel=26, acc=(80, 92))
        self.motif(33, [T1, SN, T3, SN, F1, SN], taps='all', tap_vel=30, acc=(86, 100))
        self.hemi(34)
        acc = {p * 2: TOMS[k] for k, p in enumerate(ACC)}
        self.roll32(B(35), 32, SN, 45, 92, acc)
        self.roll32(B(36), 32, SN, 20, 116)
        for q in range(4):
            self.hit(B(36) + q * TPB, KICK, 50 + 17 * q, 'RF', 1, False, 'kick')
        for q in (1, 3):
            self.hit(B(36) + q * TPB, HHP, 58, 'LF', 1, False, 'foot')
        self.land(B(37), 122, CRASH, cym2=CRASH2)
        self.sext_linear(B(37) + 4 * S16, 12, 'RLK', TOMS, 88, 114)
        self.flam_trip(B(37) + 12 * S16, 3, [F1, F2, F2], 110, 122)

        # VI. Climax (38-45): double bass, cymbal motif, linear hemiola, stop-time
        rl_tap = lambda p, l: T4 if l == 'R' else SN
        self.dbl(38, 90)
        self.motif(38, [CRASH, SN, CRASH, CHINA, SN, CRASH], taps='all', tap=rl_tap,
                   tap_vel=46, acc=(110, 120), kick=False, hatfoot=False, sw=False)
        self.dbl(39, 92)
        self.motif(39, TOMS, taps='all', tap=lambda p, l: TOMS[min(5, p * 6 // 16)],
                   tap_vel=50, acc=(104, 118), kick=False, hatfoot=False, sw=False)
        self.dbl(40, 94)
        self.motif(40, [CHINA, SN, CRASH, CHINA, SN, CRASH2], taps='all', tap=rl_tap,
                   tap_vel=50, acc=(112, 122), kick=False, hatfoot=False, sw=False)
        self.sext_linear(B(41), 24, 'RLKF', TOMS, 95, 120)
        self.stops(42)
        self.stops(43, toms=True, end=12)
        self.roll32(B(43) + 12 * S16, 8, SN, 70, 120, kick_acc=False)
        UPDN = [F2, F2, F1, F1, T4, T4, T3, T3, T2, T2, T1, T1, T2, T3, T4, F1]
        self.dbl(44, 96)
        self.motif(44, [CRASH, UPDN[3], UPDN[6], UPDN[8], UPDN[11], UPDN[14]],
                   taps='all', tap=lambda p, l: UPDN[p], tap_vel=54, acc=(108, 122),
                   kick=False, hatfoot=False, sw=False)
        self.flam_trip(B(45), 12, TOMS, 90, 124)

        # VII. Breakdown (46-49): breath, motif returns quiet, answer returns
        self.land(B(46), 112, CRASH, cym2=CRASH2)
        for p, v in ((4, 55), (8, 50), (12, 46)):
            self.hit(B(46) + p * S16, HHP, v, 'LF', 1, True, 'foot')
        self.hit(B(46) + 14 * S16, SN, 26, 'R', 0, True, 'ghost')
        self.hit(B(46) + 15 * S16, SN, 32, 'L', 0, True, 'ghost')
        self.motif(47, [BELL, XSTK, BELL, BELL, XSTK, BELL], taps='some', tap_vel=22,
                   acc=(62, 76), kick=False)
        self.hit(B(47), KICK, 60, 'RF', 1, True, 'kick')
        self.hit(B(47) + 8 * S16, KICK, 56, 'RF', 1, True, 'kick')
        self.answer(48, 0.75, 1)
        self.groove(49, 1, dyn=0.85, until=8)
        self.sext_linear(B(49) + 8 * S16, 12, 'RLK', TOMS, 62, 112)

        # VIII. Finale (50-54): recap, full-kit motif, final fill, the last hit
        self.groove(50, 2, ride=True, crash0=True)
        self.motif(51, [CRASH, SN, CRASH2, CHINA, SN, CRASH], taps='all', tap_vel=40,
                   acc=(110, 122))
        self.motif(52, TOMS, shift=2, end=8, taps='all', acc=(104, 116))
        self.sext_linear(B(52) + 8 * S16, 12, 'RLRK', TOMS, 96, 118)
        self.down16(B(53), 8, TOMS, 100, 118)
        self.roll32(B(53) + 8 * S16, 16, SN, 55, 125)
        t = B(FINAL_BAR)
        self.hit(t, CRASH, 127, 'R', 4, False, 'final')
        self.hit(t, CHINA, 122, 'L', 4, False, 'final')
        self.hit(t, KICK, 127, 'RF', 4, False, 'final')
        self.hit(t, KICK2, 120, 'LF', 4, False, 'final')

    # ---------- performance rendering ----------
    def render(self, path='solo.mid'):
        rng = random.Random(1964)
        # micro-timing: deliberate feel plus tiny, seeded humanisation
        for e in self.ev:
            bar = e['t'] // BAR
            f = feel_for(bar)
            off = 0
            pos = e['t'] % TPB
            if e['sw'] and pos in (S16, 3 * S16):
                off += f['swing']
            if e['limb'] in ('R', 'L') and e['kind'] != 'final':
                off += f['push']
            if e['kind'] == 'bb':
                off += f['lay']
            elif e['kind'] == 'ghost':
                off += 3
            if e['kind'] != 'final':
                off += int(round(max(-4.0, min(4.0, rng.gauss(0, 1.6)))))
                e['vel'] = max(1, min(127, e['vel'] + int(round(rng.gauss(0, 2)))))
            e['tick'] = max(0, e['t'] + off)

        # playability: one stroke per limb, minimum spacing per limb
        evs = sorted(self.ev, key=lambda e: (e['tick'], -e['pri'], e['note'], e['limb']))
        last = {}
        for e in evs:
            e['dead'] = False
            prev = last.get(e['limb'])
            if prev is not None and e['tick'] - prev['tick'] < MIN_GAP:
                if e['pri'] > prev['pri']:
                    prev['dead'] = True
                else:
                    e['dead'] = True
                    continue
            last[e['limb']] = e
        alive = [e for e in evs if not e['dead']]
        # dedupe same note on same tick
        seen = {}
        for e in alive:
            k = (e['tick'], e['note'])
            if k in seen:
                if e['vel'] > seen[k]['vel']:
                    seen[k] = e
            else:
                seen[k] = e
        alive = sorted(seen.values(), key=lambda e: (e['tick'], e['note']))

        # tempo map
        nbeats = FINAL_BAR * 4
        bpms = []
        for i in range(nbeats):
            bar, beat = divmod(i, 4)
            bpm = interp(ANCH, i / 4.0)
            if bar in PUSH_BARS and beat >= 2:
                bpm += 1.5 * (beat - 1)
            bpms.append(bpm)
        raw = sum(60.0 / b for b in bpms)
        k = raw / TARGET_FINAL_SEC
        bpms = [b * k for b in bpms]
        final_bpm = interp(ANCH, FINAL_BAR) * k
        final_tick = nbeats * TPB
        end_tick = final_tick + int(RING_SEC * final_bpm / 60.0 * TPB)

        msgs = []
        prev_tempo = None
        for i, bpm in enumerate(bpms + [final_bpm]):
            tempo = int(round(60000000.0 / bpm))
            if tempo != prev_tempo:
                msgs.append((i * TPB, 0, 0, mido.MetaMessage('set_tempo', tempo=tempo, time=0)))
                prev_tempo = tempo

        by_note = {}
        for e in alive:
            by_note.setdefault(e['note'], []).append(e['tick'])
        for n in by_note:
            by_note[n].sort()
        for e in alive:
            ticks = by_note[e['note']]
            idx = ticks.index(e['tick'])
            if e['kind'] == 'final':
                off = end_tick - 5
            else:
                off = e['tick'] + 90
                if idx + 1 < len(ticks):
                    off = min(off, ticks[idx + 1] - 1)
                off = max(e['tick'] + 1, off)
            msgs.append((e['tick'], 2, e['note'],
                         mido.Message('note_on', channel=9, note=e['note'],
                                      velocity=e['vel'], time=0)))
            msgs.append((off, 1, e['note'],
                         mido.Message('note_off', channel=9, note=e['note'],
                                      velocity=0, time=0)))
        msgs.sort(key=lambda m: (m[0], m[1], m[2]))

        mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
        tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                   clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
        tr.append(mido.Message('program_change', channel=9, program=0, time=0))
        tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
        tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
        now = 0
        for tick, _, _, m in msgs:
            tr.append(m.copy(time=tick - now))
            now = tick
        tr.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - now)))
        mid.save(path)


def main():
    s = Solo()
    s.compose()
    s.render('solo.mid')


if __name__ == '__main__':
    main()
