#!/usr/bin/env python3
"""
drum_solo.py - generates a two-minute General MIDI drum solo (solo.mid) on channel 10.

How the solo is organized
  * Motif A: a 3+3+2 sixteenth-note cell (the "tresillo"). Its contour runs from the
    snare to the high tom to the floor tom, with ghost notes and kick in between.
  * Motif B: a triplet answer. Floor tom, then a snare flam, then a tom descent, then a cymbal.
  * Both motifs are stated, re-orchestrated around the kit, augmented, diminished,
    displaced into other subdivisions, turned into unison stabs and played on
    cowbell, woodblocks and agogo in a quiet valley. They come back at the climax.
  * Timing is rendered in real time. A tempo curve surges and settles, fills rush
    into downbeats and the breakdown holds back. Every note also gets
    per-stroke micro-timing: ghost notes lay back, accents sit forward and flams
    get grace notes.
  * Every stroke belongs to one limb (RH, LH, RF, LF). A final pass removes any
    stroke a single limb could not physically play, so at most two hands and two
    feet ever strike at once.
The output is deterministic because every random choice comes from one fixed seed.
"""
import math
import random
import mido

OUTFILE = "solo.mid"
rng = random.Random(7071)

# ---------------------------------------------------------------- GM drum map
KICK, KICK_AC = 36, 35
SNARE, STICK = 38, 37
HH_C, HH_P, HH_O = 42, 44, 46
TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2 = 50, 48, 47, 45, 43, 41
CRASH, CRASH2, RIDE, BELL, CHINA, SPLASH = 49, 57, 51, 53, 52, 55
COWBELL, AGOGO_H, AGOGO_L, WOOD_H, WOOD_L, TRI_O = 56, 67, 68, 76, 77, 81

TOMS = [TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2]
DOWN = [SNARE, TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2]

LIMB = {'R': 'RH', 'L': 'LH', 'K': 'RF', 'P': 'LF', 'H': 'LF'}
OTHER = {'RH': 'LH', 'LH': 'RH'}

# (step, role, limb, kind)   kinds: A accent, n normal, g ghost, F flam accent
MOTIF_A = [(0, 'sn', 'R', 'A'), (1, 'g', 'L', 'g'), (2, 'k', 'K', 'n'),
           (3, 'hi', 'R', 'A'), (4, 'g', 'L', 'g'), (5, 'k', 'K', 'n'),
           (6, 'lo', 'R', 'A'), (6, 'k', 'K', 'n'), (7, 'lo', 'L', 'n')]
MOTIF_B = [(0, 'lo', 'R', 'A'), (0, 'k', 'K', 'n'), (2, 'lo', 'L', 'n'),
           (3, 'sn', 'R', 'F'), (4, 'g', 'L', 'g'), (5, 'g', 'R', 'g'),
           (6, 'hi', 'R', 'A'), (7, 'mid', 'L', 'n'), (8, 'lo', 'R', 'n'),
           (9, 'cym', 'R', 'A'), (9, 'k', 'K', 'n'), (10, 'g', 'L', 'g'),
           (11, 'g', 'L', 'g')]
DEFAULT_ORCH = {'sn': SNARE, 'g': SNARE, 'hi': TOM1, 'mid': TOM3, 'lo': FTOM2,
                'k': KICK, 'cym': CRASH}
KIND_VEL = {'A': 112, 'F': 114, 'n': 80, 'g': 32}

KICK_PATS = [[0, 8, 10], [0, 3, 6, 8], [0, 6, 8, 11], [0, 3, 6, 10, 14],
             [0, 7, 8, 13], [0, 2, 8, 11], [0, 3, 8, 10, 14], [0, 6, 9, 12],
             [0, 3, 6, 8, 11, 14]]


def spread(lst, k):
    """Pick k drums spread evenly along lst (high to low)."""
    if k <= 1:
        return [lst[len(lst) // 2]]
    return [lst[int(round(i * (len(lst) - 1) / (k - 1)))] for i in range(k)]


class Solo:
    def __init__(self):
        self.notes = []
        self.bumps = []

    # ------------------------------------------------------------ primitives
    def hit(self, pos, note, vel, limb, kind='n', dt=0.0, dur=None):
        self.notes.append({'pos': pos, 'note': note, 'vel': vel, 'limb': limb,
                           'kind': kind, 'dt': dt, 'dur': dur})

    def flam(self, pos, note, vel, limb='RH'):
        self.hit(pos, note, vel, limb, 'A')
        self.hit(pos, note, vel * 0.42, OTHER[limb], 'grace',
                 dt=-rng.uniform(0.018, 0.030))

    def push(self, a, b, frac, settle=1.0):
        """Tempo surge (frac>0) or hold-back (frac<0) peaking at b, settling after."""
        if b > a:
            self.bumps.append((a, b, b + settle, frac))

    def land(self, pos, v=118, cym=CRASH, lh=None, feet2=False):
        self.hit(pos, cym, v, 'RH', 'A')
        self.hit(pos, KICK, v * 0.95, 'RF', 'k')
        if lh is not None:
            self.hit(pos, lh, v * 0.92, 'LH', 'A')
        if feet2:
            self.hit(pos, KICK_AC, v * 0.9, 'LF', 'k')

    def stab(self, pos, cym, drum, v=118):
        self.hit(pos, cym, v, 'RH', 'A')
        self.hit(pos, drum, v * 0.95, 'LH', 'A')
        self.hit(pos, KICK, v * 0.95, 'RF', 'k')

    # ---------------------------------------------------------------- motifs
    def motif(self, m, pos, step, orch=None, dyn=1.0, displace=0, ghost_keep=1.0,
              swap=False, cresc=0.0, kick=True):
        o = dict(DEFAULT_ORCH)
        if orch:
            o.update(orch)
        n_steps = max(ev[0] for ev in m) + 1
        for (st, role, lc, kind) in m:
            if role == 'k' and not kick:
                continue
            if kind == 'g' and rng.random() >= ghost_keep:
                continue
            if swap and lc in 'RL':
                lc = 'L' if lc == 'R' else 'R'
            limb = LIMB[lc]
            note = o[role]
            frac = st / (n_steps - 1)
            shape = 1.0 + cresc * (frac - 0.5)
            p = pos + (st + displace) * step
            if role == 'k':
                self.hit(p, note, 92 * dyn * shape, limb, 'k')
            elif kind == 'g':
                self.hit(p, note, 32 * (0.75 + 0.25 * dyn), limb, 'g')
            elif kind == 'F':
                self.flam(p, note, 114 * dyn * shape, limb)
            else:
                self.hit(p, note, KIND_VEL[kind] * dyn * shape, limb, kind)
        return pos + n_steps * step

    # ------------------------------------------------------------------ runs
    def run(self, pos, n, step, sticking, path, group=None, lpath=None, accents=(0,),
            cycle=None, v_lo=74, v_hi=108, cresc=(1.0, 1.0), acc_path=None,
            acc_kick=False, ghosts=False, first=None):
        L = len(sticking)
        cyc = cycle or L
        acc_count = 0
        for i in range(n):
            ch = sticking[i % L]
            p = pos + i * step
            prog = i / (n - 1) if n > 1 else 1.0
            d = cresc[0] + (cresc[1] - cresc[0]) * prog
            acc = (i % cyc) in accents
            if ch in 'KP':
                self.hit(p, KICK, (104 if acc else 86) * d, LIMB[ch], 'k')
                continue
            if ch == 'H':
                self.hit(p, HH_P, 66 * d, 'LF', 'n')
                continue
            pth = lpath if (ch == 'L' and lpath) else path
            if group:
                note = pth[(i // group) % len(pth)]
            else:
                note = pth[min(len(pth) - 1, int(prog * len(pth)))]
            if acc:
                if acc_path:
                    note = acc_path[acc_count % len(acc_path)]
                acc_count += 1
                v = v_hi * d
                kind = 'A'
            else:
                if ghosts:
                    v = v_lo * 0.42 * (0.7 + 0.3 * d)
                    kind = 'g'
                else:
                    v = v_lo * d
                    kind = 'n'
                if i > 0 and sticking[(i - 1) % L] == ch:
                    v *= 0.88
            if i == 0 and first is not None:
                note = first
                v = max(v, v_hi * d)
                kind = 'A'
            self.hit(p, note, v, LIMB[ch], kind)
            if acc and acc_kick:
                self.hit(p, KICK, 100 * d, 'RF', 'k')
        return pos + n * step

    def roll(self, pos, beats, notes, v0, v1, kind='double', curve=1.5, step=None,
             lead='R', accent_every=None):
        if kind == 'double':
            st, step = 'RRLL', step or 0.125
        elif kind == 'buzz':
            st, step = 'RL', step or 1.0 / 12
        else:
            st, step = 'RL', step or 0.125
        if lead == 'L':
            st = st.translate(str.maketrans('RL', 'LR'))
        n = int(round(beats / step))
        for i in range(n):
            prog = i / (n - 1) if n > 1 else 1.0
            v = v0 + (v1 - v0) * (prog ** curve)
            if kind == 'double' and i % 2 == 1:
                v *= 0.9
            if kind == 'buzz':
                v *= rng.uniform(0.86, 1.04)
            if accent_every and i % accent_every == 0:
                v *= 1.12
            note = notes[min(len(notes) - 1, int(prog * len(notes)))]
            self.hit(pos + i * step, note, v, LIMB[st[i % len(st)]],
                     'g' if v < 48 else 'n')
        return pos + n * step

    # ----------------------------------------------------------------- feet
    def feet(self, pos, beats, mode, dyn=(1.0, 1.0)):
        def d(p):
            prog = (p - pos) / beats if beats else 1.0
            return dyn[0] + (dyn[1] - dyn[0]) * prog
        if mode == 'k13h24':
            for bt in range(beats):
                p = pos + bt
                if bt % 2 == 0:
                    self.hit(p, KICK, 86 * d(p), 'RF', 'k')
                else:
                    self.hit(p, HH_P, 62 * d(p), 'LF', 'n')
        elif mode == 'kq':
            for bt in range(beats):
                self.hit(pos + bt, KICK, 90 * d(pos + bt), 'RF', 'k')
        elif mode == 'hq':
            for bt in range(beats):
                self.hit(pos + bt, HH_P, 60 * d(pos + bt), 'LF', 'n')
        elif mode == 'h24':
            for bt in range(beats):
                if bt % 2 == 1:
                    self.hit(pos + bt, HH_P, 60 * d(pos + bt), 'LF', 'n')
        elif mode == 'kh8':
            for bt in range(beats):
                p = pos + bt
                self.hit(p, KICK, 88 * d(p), 'RF', 'k')
                self.hit(p + 0.5, HH_P, 60 * d(p + 0.5), 'LF', 'n')
        elif mode == 'dbl16':
            for k in range(beats * 4):
                p = pos + k * 0.25
                limb = 'RF' if k % 2 == 0 else 'LF'
                base = 96 if k % 4 == 0 else (78 if k % 2 == 0 else 72)
                self.hit(p, KICK, base * d(p) * rng.uniform(0.95, 1.03), limb, 'k')

    # -------------------------------------------------------------- grooves
    def groove(self, bar, top='hat', beats=4, dyn=1.0, ghost_p=0.3, kick_pat=None,
               open_p=0.18, crash=False):
        b0 = bar * 4
        kp = kick_pat if kick_pat is not None else rng.choice(KICK_PATS)
        tn = HH_C if top == 'hat' else RIDE
        for e in range(beats * 2):
            p = b0 + e * 0.5
            on = (e % 2 == 0)
            if crash and e == 0:
                self.hit(p, CRASH, 116 * dyn, 'RH', 'A')
                continue
            note = tn
            v = (90 if on else 62) * dyn * rng.uniform(0.93, 1.05)
            if top == 'ride' and on and rng.random() < 0.18:
                note = BELL
                v *= 0.95
            if top == 'hat' and not on and e < beats * 2 - 1 and rng.random() < open_p:
                note = HH_O
                self.hit(p + 0.5, HH_P, 58 * dyn, 'LF', 'n')
            self.hit(p, note, v, 'RH', 'n')
        for bt in (1, 3):
            if bt < beats:
                self.hit(b0 + bt, SNARE, 110 * dyn * rng.uniform(0.96, 1.03), 'LH', 'A')
        for st in range(beats * 4):
            if st % 4 == 0:
                continue
            pr = ghost_p * (1.3 if st % 4 == 3 else (1.0 if st % 2 == 1 else 0.6))
            if rng.random() < pr:
                self.hit(b0 + st * 0.25, SNARE, rng.uniform(24, 40), 'LH', 'g')
        for st in kp:
            if st < beats * 4:
                self.hit(b0 + st * 0.25, KICK, (98 if st % 4 == 0 else 84) * dyn, 'RF', 'k')
        if top == 'ride':
            for bt in (1, 3):
                if bt < beats:
                    self.hit(b0 + bt, HH_P, 60 * dyn, 'LF', 'n')

    def groove_trip(self, pos, beats, dyn=1.0, crash=False, ghost_p=0.35):
        for bt in range(beats):
            p = pos + bt
            if crash and bt == 0:
                self.hit(p, CRASH, 114 * dyn, 'RH', 'A')
            else:
                note = BELL if (bt % 2 == 0 and rng.random() < 0.3) else RIDE
                self.hit(p, note, 88 * dyn, 'RH', 'n')
            self.hit(p + 2.0 / 3, RIDE, 62 * dyn, 'RH', 'n')
            if bt % 2 == 1:
                self.hit(p, SNARE, 110 * dyn, 'LH', 'A')
            for t in (1.0 / 3, 2.0 / 3):
                if rng.random() < ghost_p:
                    self.hit(p + t, SNARE, rng.uniform(24, 38), 'LH', 'g')
            if bt % 2 == 0:
                self.hit(p, KICK, 94 * dyn, 'RF', 'k')
                if rng.random() < 0.5:
                    self.hit(p + 2.0 / 3, KICK, 78 * dyn, 'RF', 'k')
            else:
                self.hit(p, HH_P, 60 * dyn, 'LF', 'n')

    def halftime(self, pos, beats, dyn=1.0, crash=False):
        kp = rng.choice([[0, 0.75, 2.5], [0, 1.75, 2.75, 3.25],
                         [0, 0.75, 1.5, 3.5], [0, 2.25, 2.75]])
        for bt in range(beats):
            p = pos + bt
            if crash and bt == 0:
                self.hit(p, CRASH, 118 * dyn, 'RH', 'A')
            else:
                self.hit(p, CHINA, (100 if bt % 2 == 0 else 82) * dyn, 'RH',
                         'A' if bt % 2 == 0 else 'n')
            self.hit(p + 0.5, HH_P, 52 * dyn, 'LF', 'n')
        if beats > 2:
            self.hit(pos + 2, SNARE, 118 * dyn, 'LH', 'A')
        for st in range(beats * 4):
            if st == 8 or st % 4 == 0:
                continue
            if rng.random() < 0.38:
                self.hit(pos + st * 0.25, SNARE, rng.uniform(22, 38), 'LH', 'g')
        for k in kp:
            if k < beats:
                self.hit(pos + k, KICK, (102 if k == 0 else 88) * dyn, 'RF', 'k')

    # ----------------------------------------------------------------- fills
    def fill(self, pos, beats, style, dyn=1.0, shape=None, push=0.025):
        if push:
            self.push(pos, pos + beats, push)
        cr = shape if shape else (0.86 * dyn, 1.06 * dyn)
        if style == 'desc16':
            n = int(round(beats * 4))
            return self.run(pos, n, 0.25, 'RL', spread(DOWN, max(1, n // 2)), group=2,
                            accents=(0,), cycle=4, v_lo=86, v_hi=110, cresc=cr)
        if style == 'sext_linear':
            n = int(round(beats * 6))
            return self.run(pos, n, 1.0 / 6, 'RLK', spread(TOMS, max(1, n // 3)), group=3,
                            accents=(0,), cycle=3, v_lo=78, v_hi=108, cresc=cr)
        if style == 'sixstroke':
            n = int(round(beats * 6))
            return self.run(pos, n, 1.0 / 6, 'RLLRRL', spread(DOWN, max(1, n // 3)),
                            group=3, accents=(0, 5), cycle=6, v_lo=70, v_hi=112, cresc=cr)
        if style == 'linear4':
            n = int(round(beats * 4))
            return self.run(pos, n, 0.25, 'RLLK', spread(TOMS, max(1, n // 4)), group=4,
                            lpath=[SNARE], ghosts=True, accents=(0,), cycle=4,
                            v_lo=80, v_hi=110, cresc=cr)
        if style == 'flamtrip':
            n = int(round(beats * 3))
            path = spread(DOWN, n)
            for i in range(n):
                prog = i / (n - 1) if n > 1 else 1.0
                v = 108 * (cr[0] + (cr[1] - cr[0]) * prog)
                self.flam(pos + i / 3.0, path[i], v, 'RH' if i % 2 == 0 else 'LH')
            return pos + n / 3.0
        if style == 'doubles32':
            return self.roll(pos, beats, spread(DOWN, 5), 68 * cr[0], 116 * cr[1],
                             kind='double', curve=1.2, accent_every=4)
        raise ValueError(style)


# ======================================================================= score
def compose():
    s = Solo()

    def B(bar, beat=0.0):
        return bar * 4 + beat

    # ---------- 1. Statement (bars 0-3): motif A, alone, with space
    s.hit(B(0), KICK, 98, 'RF', 'k')
    s.motif(MOTIF_A, B(0), 0.25, dyn=1.0, cresc=0.12)
    s.hit(B(0, 2), HH_P, 60, 'LF')
    s.hit(B(0, 3), HH_P, 56, 'LF')
    s.hit(B(0, 3.5), SNARE, 30, 'LH', 'g')
    s.hit(B(0, 3.75), SNARE, 40, 'RH', 'g')

    s.hit(B(1), KICK, 98, 'RF', 'k')
    s.motif(MOTIF_A, B(1), 0.25, orch={'hi': TOM2, 'lo': FTOM1}, dyn=1.02)
    s.fill(B(1, 2), 2, 'desc16', dyn=0.95)

    s.motif(MOTIF_A, B(2), 0.5, orch={'sn': FTOM2, 'hi': TOM3, 'lo': TOM1},
            dyn=0.95, cresc=0.2)                      # augmented, contour reversed
    for k in range(1, 16, 2):
        if rng.random() < 0.5:
            s.hit(B(2, k * 0.25), SNARE, rng.uniform(20, 34),
                  'LH' if k % 4 == 1 else 'RH', 'g')
    s.hit(B(2, 1), HH_P, 58, 'LF')
    s.hit(B(2, 3), HH_P, 58, 'LF')

    s.hit(B(3), KICK, 100, 'RF', 'k')
    s.motif(MOTIF_A, B(3), 0.25, dyn=1.05, cresc=0.15)
    s.fill(B(3, 2), 2, 'sixstroke', dyn=1.0)

    # ---------- 2. Groove with call & response (bars 4-11)
    for i, bar in enumerate(range(4, 12)):
        top = 'hat' if bar < 8 else 'ride'
        crash = (bar % 2 == 0)
        gp = 0.22 + 0.035 * i
        dyn = 0.94 + 0.012 * i
        if bar == 5:
            s.groove(bar, top, beats=2, dyn=dyn, ghost_p=gp)
            s.motif(MOTIF_A, B(5, 2), 0.25, orch={'hi': TOM2, 'lo': FTOM2}, dyn=1.0)
            s.push(B(5, 2), B(6), 0.015)
        elif bar == 7:
            s.groove(bar, top, beats=2, dyn=dyn, ghost_p=gp)
            s.fill(B(7, 2), 2, 'linear4')
        elif bar == 9:
            s.groove(bar, top, beats=3, dyn=dyn, ghost_p=gp)
            s.fill(B(9, 3), 1, 'flamtrip')
        elif bar == 11:
            s.groove(bar, top, beats=2, dyn=dyn, ghost_p=gp)
            s.fill(B(11, 2), 2, 'sext_linear', dyn=1.05)
        else:
            s.groove(bar, top, dyn=dyn, ghost_p=gp, crash=crash)

    # ---------- 3. Travelling hands (bars 12-19)
    s.run(B(12), 32, 0.25, 'RLRRLRLL',
          [TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2, FTOM1, TOM3],
          group=4, lpath=[SNARE], accents=(0, 4), cycle=8, v_lo=60, v_hi=106,
          cresc=(0.88, 1.05), first=CRASH)
    s.feet(B(12), 8, 'k13h24')
    s.push(B(13, 2), B(14), 0.02)

    s.hit(B(14), KICK, 96, 'RF', 'k')
    orchs = [{'sn': TOM1, 'hi': TOM2, 'lo': TOM3}, {'sn': TOM2, 'hi': TOM3, 'lo': TOM4},
             {'sn': TOM3, 'hi': TOM4, 'lo': FTOM1}, {'sn': SNARE, 'hi': FTOM1, 'lo': FTOM2}]
    for k, o in enumerate(orchs):
        s.motif(MOTIF_A, B(14, 2 * k), 0.25, orch=o, dyn=0.84 + 0.07 * k, cresc=0.1)
    s.feet(B(14), 8, 'h24')
    s.push(B(15, 2), B(16), 0.02)

    s.run(B(16), 24, 1.0 / 6, 'RLLRRL', [SNARE, TOM2, TOM4, FTOM2], group=6,
          accents=(0, 5), cycle=6, v_lo=64, v_hi=110, cresc=(0.9, 1.0), first=CRASH2)
    s.feet(B(16), 4, 'kq')
    s.run(B(17), 16, 0.25, 'RL', [SNARE], ghosts=True, v_lo=78, v_hi=112,
          accents=(0,), cycle=3, acc_path=[TOM1, TOM3, FTOM1, FTOM2, TOM2, CRASH],
          acc_kick=True, cresc=(0.9, 1.08))           # 3 over 4
    s.push(B(17), B(18), 0.025)

    s.hit(B(18), KICK, 104, 'RF', 'k')
    s.motif(MOTIF_A, B(18), 0.25, orch={'sn': CRASH}, dyn=1.08)
    s.hit(B(18, 2), HH_P, 60, 'LF')
    s.hit(B(18, 3), HH_P, 56, 'LF')
    s.run(B(18, 3), 3, 1.0 / 3, 'RLR', [SNARE], accents=(), ghosts=True, v_lo=70,
          cresc=(0.8, 1.2))
    s.hit(B(19), KICK, 100, 'RF', 'k')
    end = s.motif(MOTIF_A, B(19), 1.0 / 3, orch={'hi': TOM2, 'lo': FTOM2},
                  dyn=1.0, cresc=0.15)                # motif in triplets
    s.run(end, 8, 1.0 / 6, 'RL', [TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2],
          accents=(0,), cycle=3, v_lo=84, v_hi=106, cresc=(0.95, 1.12))
    s.push(B(19, 2), B(20), 0.03)

    # ---------- 4. Triplet world, motif B (bars 20-25)
    s.hit(B(20), CRASH2, 112, 'LH', 'A')
    s.motif(MOTIF_B, B(20), 1.0 / 3, dyn=1.0)
    s.feet(B(20), 4, 'hq')
    s.groove_trip(B(21), 3, dyn=0.98, crash=True)
    s.fill(B(21, 3), 1, 'sext_linear')
    s.hit(B(22), SPLASH, 104, 'LH', 'A')
    s.motif(MOTIF_B, B(22), 1.0 / 3,
            orch={'lo': TOM4, 'hi': TOM1, 'mid': TOM2, 'cym': CHINA},
            dyn=1.02, ghost_keep=0.7)
    s.feet(B(22), 4, 'hq')
    s.run(B(23), 12, 1.0 / 3, 'RLLK', [SNARE], ghosts=True, v_lo=80, v_hi=114,
          accents=(0,), cycle=4, acc_path=[CRASH, TOM2, FTOM1], cresc=(0.95, 1.05))
    s.feet(B(23), 4, 'hq')                            # pulse against the hemiola
    end = s.motif(MOTIF_B, B(24), 0.25, orch={'cym': CRASH2}, dyn=1.02)  # B in 16ths
    s.fill(end, 1, 'linear4')
    s.groove_trip(B(25), 2, crash=True)
    s.fill(B(25, 2), 2, 'flamtrip', shape=(1.0, 0.5), push=-0.03)

    # ---------- 5. The valley: colour, clave, swell (bars 26-31)
    s.feet(B(26), 16, 'k13h24', dyn=(0.6, 0.66))
    clave = [0, 3, 6, 10, 12]                         # son clave: motif A + answer
    for j, st in enumerate(clave):
        s.hit(B(26, st * 0.25), COWBELL, 80 if j == 0 else 70, 'RH', 'n')
    for st in range(16):
        if rng.random() < 0.42:
            s.hit(B(26, st * 0.25), SNARE, rng.uniform(16, 30), 'LH', 'g')
    wood = [WOOD_H, WOOD_L, WOOD_H, WOOD_L, WOOD_H]
    for st, note in zip(clave, wood):
        s.hit(B(27, st * 0.25), note, 76, 'RH', 'n')
    for st in range(14):
        if rng.random() < 0.38:
            s.hit(B(27, st * 0.25), SNARE, rng.uniform(16, 30), 'LH', 'g')
    s.hit(B(27, 3.5), TOM4, 50, 'LH', 'n')
    s.hit(B(27, 3.75), FTOM1, 56, 'LH', 'n')
    s.motif(MOTIF_A, B(28), 0.25, orch={'sn': TOM2, 'hi': TOM1, 'lo': FTOM1}, dyn=0.55)
    s.run(B(28, 2), 4, 0.5, 'RL', [TOM4, TOM2, FTOM1, TOM3], group=1, accents=(),
          v_lo=54, cresc=(0.9, 1.15))
    s.hit(B(28, 3.75), TRI_O, 58, 'RH', 'n')
    s.motif(MOTIF_A, B(29), 0.25, orch={'sn': AGOGO_L, 'hi': AGOGO_H, 'lo': AGOGO_L},
            dyn=0.62)
    s.motif(MOTIF_A, B(29, 2), 0.25, orch={'sn': STICK, 'hi': TOM2, 'lo': FTOM2},
            dyn=0.7, cresc=0.3)
    s.roll(B(30), 6, [SNARE], 16, 110, kind='buzz', curve=2.2)
    s.feet(B(30), 6, 'kh8', dyn=(0.42, 1.05))
    s.push(B(30, 3), B(31, 2), 0.03)
    s.fill(B(31, 2), 2, 'desc16', shape=(1.02, 1.15), push=0.02)

    # ---------- 6. Double-kick climb (bars 32-39)
    s.feet(B(32), 8, 'dbl16', dyn=(0.85, 1.0))
    orchs = [{'sn': CRASH, 'hi': TOM1, 'lo': FTOM2}, {'sn': SNARE, 'hi': TOM3, 'lo': FTOM1},
             {'sn': CHINA, 'hi': TOM2, 'lo': FTOM2}, {'sn': SNARE, 'hi': TOM4, 'lo': CRASH2}]
    for k, o in enumerate(orchs):
        s.motif(MOTIF_A, B(32, 2 * k), 0.25, orch=o, dyn=0.95 + 0.04 * k, kick=False)
    s.feet(B(34), 8, 'dbl16', dyn=(0.9, 1.1))
    s.run(B(34), 32, 0.25, 'RL', [SNARE, SNARE, TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2],
          accents=(0,), cycle=3, acc_path=[CRASH, FTOM2, CHINA, TOM2, CRASH2, FTOM1],
          v_lo=70, v_hi=114, cresc=(0.85, 1.06))
    s.push(B(35, 2), B(36), 0.02)
    s.halftime(B(36), 4, crash=True)
    s.halftime(B(37), 2)
    s.fill(B(37, 2), 2, 'doubles32')
    s.feet(B(38), 4, 'dbl16', dyn=(0.95, 1.05))
    s.motif(MOTIF_A, B(38), 0.5, orch={'sn': CRASH, 'hi': CHINA, 'lo': CRASH2},
            dyn=1.05, kick=False)
    s.hit(B(38, 1), SNARE, 108, 'LH', 'A')
    s.hit(B(38, 3), SNARE, 112, 'LH', 'A')
    s.feet(B(39), 2, 'dbl16')
    s.feet(B(39, 2), 2, 'kq')
    s.fill(B(39), 2, 'sixstroke', push=0.012)
    s.fill(B(39, 2), 2, 'flamtrip', shape=(1.0, 1.15), push=0.02)

    # ---------- 7. Breakdown: space and stabs (bars 40-43)
    s.land(B(40), 124, cym=CRASH, lh=CHINA, feet2=True)
    s.push(B(40, 0.5), B(40, 3), -0.05)
    s.run(B(40, 2.5), 3, 1.0 / 6, 'RLR', [SNARE], accents=(), ghosts=True, v_lo=68)
    s.hit(B(40, 3), HH_P, 56, 'LF')
    s.hit(B(40, 3.5), HH_P, 50, 'LF')
    s.hit(B(41), KICK, 104, 'RF', 'k')
    s.hit(B(41), CRASH2, 108, 'LH', 'A')
    s.motif(MOTIF_A, B(41), 0.5, orch={'hi': TOM1, 'lo': FTOM2}, dyn=1.06, ghost_keep=0.0)
    stabs = [(B(42, 0), CRASH, SNARE), (B(42, 0.75), CHINA, TOM2),
             (B(42, 1.5), CRASH2, FTOM2), (B(42, 2.5), CRASH, SNARE),
             (B(42, 3.25), CHINA, TOM1), (B(43, 0), CRASH2, FTOM2)]
    for j, (p, c, d) in enumerate(stabs):
        s.stab(p, c, d, 112 + 2 * j)
    s.hit(B(42, 2), HH_P, 54, 'LF')
    s.push(B(42), B(43), -0.045)
    s.roll(B(43, 1), 3, [SNARE] * 5 + [TOM1, TOM3, FTOM2], 26, 118, kind='double',
           curve=1.8)
    s.feet(B(43, 1), 3, 'kq', dyn=(0.4, 1.0))
    s.push(B(43, 1), B(44), 0.04)

    # ---------- 8. Final build (bars 44-53) and the last hit
    s.hit(B(44), KICK, 108, 'RF', 'k')
    s.motif(MOTIF_A, B(44), 0.25, orch={'sn': CRASH}, dyn=1.08)
    s.motif(MOTIF_A, B(44, 2), 0.25, dyn=1.05, cresc=0.1)
    s.feet(B(44), 4, 'h24')
    s.hit(B(45), CRASH2, 110, 'LH', 'A')
    end = s.motif(MOTIF_B, B(45), 0.25, orch={'cym': CHINA}, dyn=1.05)
    s.fill(end, 1, 'sext_linear', dyn=1.05)

    s.feet(B(46), 4, 'dbl16', dyn=(0.95, 1.05))
    for e in range(8):
        p = B(46, e * 0.5)
        if e == 0:
            s.hit(p, CRASH, 118, 'RH', 'A')
        elif e % 2 == 0:
            s.hit(p, BELL, 100, 'RH', 'A')
        else:
            s.hit(p, RIDE, 70, 'RH', 'n')
    s.hit(B(46, 1), SNARE, 114, 'LH', 'A')
    s.hit(B(46, 3), SNARE, 116, 'LH', 'A')
    for st in range(16):
        if st % 4 != 0 and rng.random() < 0.45:
            s.hit(B(46, st * 0.25), SNARE, rng.uniform(24, 40), 'LH', 'g')

    s.run(B(47), 24, 1.0 / 6, 'RLRRLL', [TOM1, TOM2, TOM3, FTOM1], group=6,
          lpath=[SNARE], accents=(0,), cycle=6, v_lo=70, v_hi=112,
          cresc=(0.9, 1.08), first=CRASH)
    s.feet(B(47), 4, 'kq')
    s.push(B(47, 2), B(48), 0.02)

    orchs = [{'sn': CRASH, 'hi': TOM4, 'lo': TOM2}, {'sn': FTOM1, 'hi': TOM3, 'lo': TOM1},
             {'sn': FTOM2, 'hi': TOM2, 'lo': CHINA}]
    p = B(48)
    for k, o in enumerate(orchs):
        p = s.motif(MOTIF_A, p, 1.0 / 6, orch=o, dyn=1.0 + 0.04 * k)   # sextuplet stretto

    s.feet(B(49), 4, 'dbl16', dyn=(1.0, 1.08))
    s.motif(MOTIF_A, B(49), 0.25, orch={'sn': CRASH, 'hi': TOM2, 'lo': FTOM2},
            dyn=1.05, kick=False)
    s.motif(MOTIF_A, B(49, 2), 0.25, orch={'sn': CHINA, 'hi': TOM1, 'lo': FTOM1},
            dyn=1.1, kick=False)

    s.run(B(50), 16, 0.25, 'RL', [SNARE], accents=(0,), cycle=3,
          acc_path=[CRASH, TOM1, CHINA, FTOM2, CRASH2, TOM3],
          v_lo=66, v_hi=114, cresc=(0.9, 1.05))
    s.feet(B(50), 4, 'kh8')

    s.roll(B(51), 4, [SNARE, SNARE, TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2], 58, 122,
           kind='double', curve=1.3, accent_every=4)
    s.feet(B(51), 4, 'dbl16', dyn=(0.85, 1.12))
    s.push(B(51), B(52), 0.035)

    for p, c, d in [(B(52), CRASH, SNARE), (B(52, 0.75), CHINA, TOM2),
                    (B(52, 1.5), CRASH2, FTOM2)]:
        s.stab(p, c, d, 122)
    s.run(B(52, 2), 12, 1.0 / 6, 'RL', [TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2], group=2,
          accents=(0,), cycle=6, v_lo=88, v_hi=114, cresc=(0.9, 1.1))
    s.feet(B(52, 2), 2, 'kq')
    s.push(B(52, 2), B(53), 0.02)

    s.fill(B(53), 2, 'flamtrip', shape=(1.0, 1.1), push=0.015)
    s.feet(B(53), 2, 'kq')
    s.fill(B(53, 2), 1, 'linear4', shape=(1.05, 1.12), push=0.0)
    s.run(B(53, 3), 8, 0.125, 'RL', [SNARE, TOM1, TOM2, TOM3, TOM4, FTOM1, FTOM2, FTOM2],
          accents=(0,), cycle=4, v_lo=96, v_hi=116, cresc=(1.0, 1.12))
    s.push(B(53, 3), B(54), -0.06, settle=0.5)        # broaden into the last hit

    fb = B(54)
    s.hit(fb, CRASH, 127, 'RH', 'A', dur=3.0)
    s.hit(fb, CHINA, 124, 'LH', 'A', dur=3.0)
    s.hit(fb, KICK, 127, 'RF', 'k', dur=3.0)
    s.hit(fb, KICK_AC, 120, 'LF', 'k', dur=3.0)
    return s, fb


# ====================================================================== render
TPB = 960
TPS = TPB * 2              # ticks per second at the file tempo of 120 bpm
TARGET = 116.8             # final hit lands here (seconds after the lead-in)
LEAD = 0.25
MIN_GAP = {'RH': 0.040, 'LH': 0.040, 'RF': 0.070, 'LF': 0.070}
KIND_TIMING = {'A': (-0.002, 0.0035), 'F': (-0.002, 0.0035), 'n': (0.0, 0.005),
               'g': (0.006, 0.0065), 'k': (-0.003, 0.004), 'grace': (0.0, 0.002)}
TEMPO_KEYS = [(0, 104), (1, 108), (4, 112), (12, 114), (16, 116), (20, 112),
              (25.5, 110), (26, 103), (30, 105), (32, 114), (36, 112),
              (39.75, 118), (40.25, 106), (43, 108), (44, 114), (48, 118),
              (52, 122), (54, 120), (70, 120)]


def base_bpm(bar):
    if bar <= TEMPO_KEYS[0][0]:
        return TEMPO_KEYS[0][1]
    for (b0, v0), (b1, v1) in zip(TEMPO_KEYS, TEMPO_KEYS[1:]):
        if bar <= b1:
            return v0 + (v1 - v0) * (bar - b0) / (b1 - b0)
    return TEMPO_KEYS[-1][1]


def bump_val(b, a, pk, e, fr):
    if b < a or b >= e:
        return 0.0
    if b < pk:
        x = (b - a) / (pk - a)
        return fr * (0.5 - 0.5 * math.cos(math.pi * x))
    x = (b - pk) / (e - pk)
    return fr * (0.5 + 0.5 * math.cos(math.pi * x))


def render(s, final_beat):
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(3)]
    res = 1.0 / 96
    total = final_beat + 8
    n = int(total / res) + 2
    times = [0.0] * (n + 1)
    for k in range(n):
        b = (k + 0.5) * res
        f = (1.0 + 0.010 * math.sin(2 * math.pi * b / 17.0 + ph[0])
             + 0.006 * math.sin(2 * math.pi * b / 6.5 + ph[1]))
        for (a, pk, e, fr) in s.bumps:
            if a <= b < e:
                f += bump_val(b, a, pk, e, fr)
        bpm = base_bpm(b / 4.0) * f
        times[k + 1] = times[k] + 60.0 / bpm * res

    def tof(b):
        x = b / res
        i = max(0, min(n - 1, int(math.floor(x))))
        fr = x - i
        return times[i] + (times[i + 1] - times[i]) * fr

    scale = TARGET / tof(final_beat)

    evs = []
    for nt in s.notes:
        t = tof(nt['pos']) * scale + LEAD
        mu, sd = KIND_TIMING.get(nt['kind'], (0.0, 0.005))
        if nt['dur'] is None:
            t += rng.gauss(mu, sd)
            if nt['limb'] in ('RH', 'LH'):
                t += 0.0025 * math.sin(2 * math.pi * t / 4.7 + ph[2])
        t += nt['dt']
        jit = 2.0 if nt['kind'] in ('g', 'grace') else 3.0
        v = nt['vel'] + rng.gauss(0, jit)
        v = int(max(1, min(127, round(v))))
        evs.append({'t': max(0.0, t), 'note': nt['note'], 'vel': v, 'limb': nt['limb'],
                    'kind': nt['kind'], 'dur': nt['dur']})

    # physical playability: one stroke per limb within its minimum gap
    kept = []
    for limb in ('RH', 'LH', 'RF', 'LF'):
        lst = sorted([e for e in evs if e['limb'] == limb], key=lambda e: (e['t'], -e['vel']))
        out = []
        for e in lst:
            if out and e['t'] - out[-1]['t'] < MIN_GAP[limb]:
                if e['vel'] > out[-1]['vel']:
                    if len(out) < 2 or e['t'] - out[-2]['t'] >= MIN_GAP[limb]:
                        out[-1] = e
                continue
            out.append(e)
        kept.extend(out)

    for e in kept:
        e['tick'] = int(round(e['t'] * TPS))
    kept.sort(key=lambda e: (e['tick'], e['note'], -e['vel']))
    dedup, seen = [], set()
    for e in kept:
        key = (e['tick'], e['note'])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(e)

    nxt_limb, nxt_note = {}, {}
    for e in reversed(dedup):
        e['nl'] = nxt_limb.get(e['limb'])
        e['nn'] = nxt_note.get(e['note'])
        nxt_limb[e['limb']] = e['tick']
        nxt_note[e['note']] = e['tick']

    msgs = []
    for e in dedup:
        dur = int(round((e['dur'] if e['dur'] else 0.03) * TPS))
        for nx in (e['nl'], e['nn']):
            if nx is not None:
                dur = min(dur, nx - e['tick'] - 1)
        dur = max(1, dur)
        msgs.append((e['tick'], 1, e['note'], 'on', e['vel']))
        msgs.append((e['tick'] + dur, 0, e['note'], 'off', 0))
    msgs.sort()

    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
    tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
    last = 0
    for tick, order, note, typ, vel in msgs:
        delta = tick - last
        last = tick
        if typ == 'on':
            tr.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
        else:
            tr.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=delta))
    tr.append(mido.MetaMessage('end_of_track', time=0))
    mid.save(OUTFILE)
    return len(dedup), last / TPS


def main():
    solo, final_beat = compose()
    count, length = render(solo, final_beat)
    print("wrote %s: %d strokes, %.1f seconds" % (OUTFILE, count, length))


if __name__ == "__main__":
    main()
