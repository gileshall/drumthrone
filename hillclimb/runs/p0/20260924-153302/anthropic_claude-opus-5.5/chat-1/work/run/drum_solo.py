#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

The solo runs 60 bars of 4/4 at 120 BPM, which is exactly 120 seconds.

Motif A, the hook, is a 16th-note cell: onsets 0, 3, 6, 10, 12, with a tom
contour of high-mid-low-lowmid-high. It is stated in the intro and hidden in
the groove's kick and backbeat. It is then displaced, diminished, augmented,
inverted and filled, played on congas and timbales, whispered on side stick,
and shouted in the climax. The piece closes by quoting the intro.

Feel:
- The 16th notes are swung. The amount changes by section on purpose.
- The snare lays back, cymbals and bells push, and ghost notes sit lazier still.
- Every note is assigned to a limb (R, L, RF, LF). A final pass enforces one
  strike per limb at a time, so at most two hands and two feet sound at once.

The random generator has a fixed seed, so the output is identical on every run.
"""
import math
import random
import mido

PPQ = 480
S16 = PPQ // 4
BPM = 120
BARS = 60
CH = 9  # MIDI channel 10

# General MIDI percussion
KICK2, KICK, STICK, SNARE, CLAP, ESNARE = 35, 36, 37, 38, 39, 40
FT_LO, HH, FT_HI, HHP, TOM_LO, HHO = 41, 42, 43, 44, 45, 46
TOM_LM, TOM_HM, CRASH, TOM_HI, RIDE, CHINA = 47, 48, 49, 50, 51, 52
BELL, TAMB, SPLASH, COWBELL, CRASH2, VIBRA, RIDE2 = 53, 54, 55, 56, 57, 58, 59
BONGO_HI, BONGO_LO, CONGA_MUTE, CONGA_HI, CONGA_LO = 60, 61, 62, 63, 64
TIMB_HI, TIMB_LO, AGOGO_HI, AGOGO_LO, CABASA, MARACAS = 65, 66, 67, 68, 69, 70
CLAVES, WB_HI, WB_LO = 75, 76, 77

TOM_SET = {TOM_HI, TOM_HM, TOM_LM, TOM_LO, FT_HI, FT_LO}
R, L, RF, LF = "R", "L", "RF", "LF"

ACC = {0: 34, 1: 80, 2: 116, 3: 127}

# Motif A: (16th step, contour level 0..3, accent 0 ghost / 1 normal / 2 accent)
MOTIF_A = [(0, 3, 2), (3, 2, 1), (6, 0, 2), (10, 1, 1), (12, 3, 2)]
PICKUP = [(14, 2, 1), (15, 1, 1)]


def shift(seq, d):
    return [(s + d, l, a) for s, l, a in seq]


def scale(seq, k, d=0):
    return [(s * k + d, l, a) for s, l, a in seq]


def invert(seq):
    return [(s, 3 - l, a) for s, l, a in seq]


TOMS4 = {3: TOM_HI, 2: TOM_HM, 1: TOM_LO, 0: FT_LO}
KIT4 = {3: SNARE, 2: TOM_HM, 1: TOM_LO, 0: FT_LO}
LAT4 = {3: TIMB_HI, 2: BONGO_HI, 1: CONGA_HI, 0: CONGA_LO}
STICK4 = {3: STICK, 2: STICK, 1: STICK, 0: STICK}


def tom_run(st):
    return [TOM_HI, TOM_HM, TOM_LO, FT_LO][int(st) // 4 % 4]


def hand(st, res=1.0):
    idx = int(round(st / res))
    return R if idx % 2 == 0 else L


def feel(note, vel):
    """Deliberate placement in ticks (about 1 ms per tick at 120 BPM)."""
    if note in (SNARE, ESNARE, STICK, CLAP):
        o = 14          # snare lays back
    elif note in (HH, HHO, RIDE, RIDE2, BELL, COWBELL, CHINA):
        o = -8          # time-keeping cymbals push ahead
    elif note in TOM_SET:
        o = 3
    elif note in (KICK, KICK2, HHP, CLAVES, TAMB, CRASH, CRASH2, SPLASH):
        o = 0
    else:
        o = 5           # hand percussion sits a little behind
    if vel < 50:
        o += 6          # ghost notes are lazier
    return o


# Dynamic envelope: (bar position, level)
DYN = [(0, 0.62), (3.5, 0.72), (4, 0.8), (11, 0.86), (12, 0.84), (19.8, 0.98),
       (20, 0.68), (27, 0.84), (28, 0.74), (35.8, 1.0), (36, 0.62), (42.5, 0.66),
       (44, 0.88), (48, 0.95), (50, 0.92), (55.8, 1.0), (56, 0.62), (58, 0.7),
       (59, 1.0), (60, 1.0)]


class Solo:
    def __init__(self):
        self.ev = []
        self.rng = random.Random(1971)
        self.swing = 0.58

    def level(self, x):
        if x <= DYN[0][0]:
            return DYN[0][1]
        for (x0, y0), (x1, y1) in zip(DYN, DYN[1:]):
            if x0 <= x <= x1:
                return y1 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return DYN[-1][1]

    def tick(self, bar, step):
        pair = math.floor(step / 2.0)
        f = step - 2 * pair
        r = self.swing
        x = f * 2 * r if f <= 1 else 2 * r + (f - 1) * 2 * (1 - r)
        return (bar * 16 + 2 * pair + x) * S16

    def hit(self, bar, step, note, vel, limb, dt=0.0, raw=False, dur=40):
        t = self.tick(bar, step) + dt + feel(note, vel) + self.rng.gauss(0, 1.2)
        if raw:
            v = vel
        else:
            lv = self.level(bar + step / 16.0)
            v = vel * lv if vel >= 60 else vel * (0.5 + 0.5 * lv)
            v += self.rng.uniform(-3, 3)
        v = int(round(max(1, min(127, v))))
        self.ev.append((t, note, v, limb, dur))

    def play(self, bar, seq, mapping, vel_scale=1.0, force=None, accent_kick=False):
        res = 0.5 if any(abs(x - round(x)) > 1e-6 for x, _, _ in seq) else 1.0
        for st, l, a in seq:
            h = force or hand(st, res)
            self.hit(bar, st, mapping[l], ACC[a] * vel_scale, h)
            if accent_kick and a == 2:
                self.hit(bar, st, KICK, ACC[a] * 0.9, RF)

    def filled(self, bar, seq, mapping, fill_note, fill_vel, start=0, end=16,
               accent_kick=False):
        self.play(bar, seq, mapping, accent_kick=accent_kick)
        occ = [x for x, _, _ in seq]
        for st in range(start, end):
            if all(abs(st - x) > 0.01 for x in occ):
                n = fill_note(st) if callable(fill_note) else fill_note
                self.hit(bar, st, n, fill_vel, hand(st))

    def power(self, bar, seq, mapping, crash=CRASH, unison=True, fill=None,
              fill_vel=62, kick=True):
        occ = []
        for st, l, a in seq:
            h = hand(st)
            occ.append(st)
            if a == 2:
                self.hit(bar, st, crash if h == R else CRASH2, 122, h)
                if kick:
                    self.hit(bar, st, KICK, 118, RF)
                if unison:
                    self.hit(bar, st, SNARE, 108, L if h == R else R)
            else:
                self.hit(bar, st, mapping[l], ACC[a] + 10, h)
        if fill:
            for st in range(16):
                if all(abs(st - x) > 0.01 for x in occ):
                    n = fill(st) if callable(fill) else fill
                    self.hit(bar, st, n, fill_vel, hand(st))

    def chicks(self, bar, steps=(4, 12), vel=62, note=HHP):
        for st in steps:
            self.hit(bar, st, note, vel, LF)

    def double_bass(self, bar, vel=84):
        for st in range(16):
            if st % 2 == 0:
                self.hit(bar, st, KICK, vel + (10 if st % 4 == 0 else 0), RF)
            else:
                self.hit(bar, st, KICK2, vel - 8, LF)

    # ---- validation: one strike per limb at a time ----
    def clean(self, min_gap=45):
        ev = sorted(self.ev, key=lambda e: (e[0], e[3], -e[2], e[1]))
        kept = []
        last = {}
        for e in ev:
            l = e[3]
            if l in last and e[0] - last[l][0] < min_gap:
                prev = last[l]
                if e[2] > prev[2]:
                    kept.remove(prev)
                    kept.append(e)
                    last[l] = e
                continue
            kept.append(e)
            last[l] = e
        return kept


# ---------------------------------------------------------------- sections
def intro(s):
    s.swing = 0.58
    for b in range(4):
        s.chicks(b, vel=60)
    s.play(0, MOTIF_A, TOMS4)
    s.hit(0, 0, KICK, 96, RF)
    s.hit(0, 6, KICK, 84, RF)
    s.hit(0, 12, KICK, 70, RF)
    # answer: space, whispers, pickup
    s.hit(1, 0, KICK, 80, RF)
    for st in (5, 7, 9):
        s.hit(1, st, SNARE, 30, L)
    s.hit(1, 8, BELL, 66, R)
    s.play(1, PICKUP, TOMS4)
    # restatement with inner notes
    var = [(0, 3, 2), (3, 2, 1), (6, 0, 2), (8, 0, 0), (10, 1, 1), (11, 1, 0),
           (12, 3, 2), (14, 2, 1)]
    s.play(2, var, TOMS4)
    for k in (0, 6, 12):
        s.hit(2, k, KICK, 90, RF)
    # fill into the groove
    s.play(3, MOTIF_A[:3], TOMS4)
    s.hit(3, 0, KICK, 90, RF)
    s.hit(3, 6, KICK, 90, RF)
    for i, st in enumerate(range(8, 16)):
        s.hit(3, st, SNARE, 48 + i * 10, hand(st))
    s.hit(3, 8, KICK, 80, RF)
    s.hit(3, 12, KICK, 95, RF)


def groove_bar(s, b, ghosts, kicks, open_at=None, crash=False, upto=16):
    for st in range(0, upto, 2):
        if st == 0 and crash:
            s.hit(b, 0, CRASH, 118, R)
        elif open_at == st:
            s.hit(b, st, HHO, 90, R)
        else:
            s.hit(b, st, HH, 92 if st % 4 == 0 else 62, R)
    for st in (4, 12):
        if st < upto:
            s.hit(b, st, SNARE, 112, L)
    for g in ghosts:
        if g < upto:
            s.hit(b, g, SNARE, 32, L)
    for k in kicks:
        s.hit(b, k, KICK, 100 if k % 4 == 0 else 84, RF)
    if open_at is not None:
        s.hit(b, open_at + 2, HHP, 70, LF)


def groove(s):
    s.swing = 0.58
    GA, GB, GC = [7, 9, 15], [2, 7, 10, 15], [7, 9, 11, 14]
    KA, KB, KC = [0, 6, 10], [0, 3, 6, 10], [0, 6, 8, 10, 13]
    plan = [(4, GA, KA, None, True), (5, GB, KB, 14, False), (6, GA, KA, None, False),
            (8, GC, KB, None, True), (9, GA, KC, 14, False), (10, GB, KA, None, False)]
    for b, g, k, o, c in plan:
        groove_bar(s, b, g, k, o, c)
    # bar 7: half groove, then the motif's head as a fill
    groove_bar(s, 7, [7], [0, 6], None, False, upto=8)
    s.filled(7, shift(MOTIF_A[:3], 8), TOMS4, SNARE, 36, start=8, end=16)
    s.hit(7, 8, KICK, 96, RF)
    s.hit(7, 14, KICK, 104, RF)
    # bar 11: the whole motif with every gap filled
    s.filled(11, MOTIF_A + PICKUP, TOMS4, SNARE, 40, accent_kick=True)
    s.chicks(11)


def develop(s):
    s.swing = 0.58
    for b in range(12, 19):
        s.chicks(b)
    # 12: motif on the kit with ghosts
    s.hit(12, 0, CRASH, 120, R)
    s.hit(12, 0, KICK, 110, RF)
    s.play(12, MOTIF_A[1:], KIT4)
    for st in (1, 5, 7, 9, 11, 13, 15):
        s.hit(12, st, SNARE, 30, L)
    s.hit(12, 6, KICK, 90, RF)
    s.hit(12, 12, KICK, 96, RF)
    # 13: motif + pickup
    s.play(13, MOTIF_A + PICKUP, KIT4, accent_kick=True)
    for st in (1, 5, 9):
        s.hit(13, st, SNARE, 30, L)
    # 14: displaced by an eighth
    d = shift(MOTIF_A, 2)
    s.filled(14, d, TOMS4, SNARE, 30)
    s.hit(14, 0, KICK, 96, RF)
    for st, _, a in d:
        if a == 2:
            s.hit(14, st, KICK, 100, RF)
    # 15: displaced by a dotted eighth, contour inverted
    d = invert(shift(MOTIF_A, 3))
    s.filled(15, d, TOMS4, SNARE, 30)
    s.hit(15, 0, KICK, 96, RF)
    for st, _, a in d:
        if a == 2:
            s.hit(15, st, KICK, 104, RF)
    # 16-17: diminution, twice per bar
    seq16 = scale(MOTIF_A, 0.5) + scale(invert(MOTIF_A), 0.5, 8)
    s.play(16, seq16, TOMS4, accent_kick=True)
    for st in (7, 15):
        s.hit(16, st, SNARE, 34, L)
    seq17 = scale(MOTIF_A, 0.5) + scale(MOTIF_A, 0.5, 8)
    s.play(17, seq17[:5], TOMS4, accent_kick=True)
    s.play(17, seq17[5:], KIT4, accent_kick=True)
    s.hit(17, 15, SNARE, 60, L)
    # 18: inverted motif with crash accents, dense tom fill
    s.power(18, invert(MOTIF_A), TOMS4, unison=False, fill=tom_run, fill_vel=58)
    # 19: crescendo 32nd roll into a stop
    for i in range(24):
        s.hit(19, i * 0.5, SNARE, 40 + i * 3.3, R if i % 2 == 0 else L)
    for k in (0, 4, 8):
        s.hit(19, k, KICK, 90, RF)
    s.hit(19, 12, CRASH, 127, R)
    s.hit(19, 12, KICK, 127, RF)
    s.hit(19, 12, KICK2, 120, LF)


def tumbao(s, b, variant):
    for st in (0, 2, 6, 8, 10):
        s.hit(b, st, CONGA_MUTE, 40 if st % 4 == 0 else 48, L)
    s.hit(b, 4, CONGA_MUTE, 105, R)
    s.hit(b, 12, CONGA_HI, 96, R)
    s.hit(b, 14, CONGA_LO if variant % 2 else CONGA_HI, 90, R)
    if variant == 3:
        s.hit(b, 9, BONGO_HI, 70, R)
        s.hit(b, 11, BONGO_LO, 74, R)


def latin(s):
    s.swing = 0.54
    for i, b in enumerate(range(20, 28)):
        for st in ([0, 6, 12] if i % 2 == 0 else [4, 8]):   # son clave 3-2, left foot block
            s.hit(b, st, CLAVES, 84, LF)
        s.hit(b, 6, KICK, 82, RF)
        if b < 27:
            s.hit(b, 12, KICK, 88, RF)
    for b in range(20, 24):
        tumbao(s, b, b - 20)
    s.filled(24, MOTIF_A, LAT4, CONGA_MUTE, 38)
    for st in (0, 4, 6, 8, 12, 14):
        s.hit(25, st, COWBELL, 100 if st in (0, 8) else 74, R)
    s.play(25, MOTIF_A, LAT4, force=L)
    s.filled(26, shift(MOTIF_A, 2), LAT4, CONGA_MUTE, 38)
    s.play(27, scale(MOTIF_A, 0.5), LAT4)
    for i in range(16):
        st = 8 + i * 0.5
        s.hit(27, st, TIMB_HI if i % 4 < 2 else TIMB_LO, 50 + i * 4.5,
              R if i % 2 == 0 else L)


def build(s):
    s.swing = 0.58
    for b in range(28, 35):
        s.chicks(b)
    # 28-29: 3-over-4 linear cell (ride, snare, kick)
    s.hit(28, 0, CRASH, 118, R)
    s.hit(28, 0, KICK, 110, RF)
    for i in range(1, 32):
        b, st, k = 28 + i // 16, i % 16, i % 3
        if k == 0:
            s.hit(b, st, RIDE if b == 28 else BELL, 100 if (i // 3) % 2 == 0 else 84, R)
        elif k == 1:
            s.hit(b, st, SNARE, 42, L)
        else:
            s.hit(b, st, KICK, 86, RF)
    # 30-31: same cell moved to the toms, louder
    s.hit(30, 0, SPLASH, 116, R)
    s.hit(30, 0, KICK, 110, RF)
    for i in range(1, 32):
        b, st, k = 30 + i // 16, i % 16, i % 3
        g = i // 3
        if k == 0:
            s.hit(b, st, TOM_HI if g % 2 == 0 else TOM_HM, 100, R)
        elif k == 1:
            s.hit(b, st, SNARE, 60, L)
        else:
            s.hit(b, st, KICK, 96, RF)
    # 32-33: motif returns with crash accents and a tom fill
    s.power(32, MOTIF_A, TOMS4, unison=False, fill=tom_run, fill_vel=64)
    s.power(33, invert(MOTIF_A) + PICKUP, TOMS4, crash=CHINA, unison=False,
            fill=tom_run, fill_vel=66)
    # 34: 16ths on snare, the motif as accents in the roll
    acc = {st for st, _, _ in MOTIF_A}
    for st in range(16):
        s.hit(34, st, SNARE, 118 if st in acc else 46, hand(st))
    for st in range(0, 16, 2):
        s.hit(34, st, KICK, 92, RF)
    # 35: 32nd tom descent into a hit, then silence
    order = [TOM_HI, TOM_HI, TOM_HM, TOM_HM, TOM_LO, TOM_LO, FT_LO, FT_LO]
    for i in range(24):
        s.hit(35, i * 0.5, order[i % 8], 70 + i * 2.2, R if i % 2 == 0 else L)
    for k in (0, 4, 8):
        s.hit(35, k, KICK, 100, RF)
    s.hit(35, 12, CHINA, 127, R)
    s.hit(35, 12, KICK, 127, RF)
    s.hit(35, 12, KICK2, 120, LF)


def breakdown(s):
    s.swing = 0.62
    for b in range(36, 44):
        for st in (0, 4, 6, 8, 12, 14):
            if b == 43 and st >= 12:
                continue
            s.hit(b, st, RIDE, 74 if st % 4 == 0 else 54, R)
        foot = TAMB if b >= 40 else HHP
        if b < 43:
            s.chicks(b, vel=64, note=foot)
        else:
            s.chicks(b, steps=(4,), vel=64, note=foot)
        s.hit(b, 0, KICK, 40, RF)
        s.hit(b, 8, KICK, 36, RF)
    s.play(36, MOTIF_A, STICK4, force=L)
    for st in (7, 9):
        s.hit(37, st, SNARE, 32, L)
    s.hit(37, 14, WB_HI, 66, L)
    s.hit(37, 15, WB_LO, 70, L)
    s.play(38, shift(MOTIF_A, 2), STICK4, force=L)
    s.play(39, MOTIF_A, TOMS4, vel_scale=0.75, force=L)
    # 40-41: augmentation (turns into a clave)
    s.play(40, scale(MOTIF_A, 2), STICK4, force=L)
    for st in (3, 9, 15):
        s.hit(40, st, SNARE, 30, L)
    for st in (11, 14):
        s.hit(41, st, SNARE, 30, L)
    s.hit(41, 8, KICK, 70, RF)
    # 42: call on side stick, response on toms
    s.play(42, scale(MOTIF_A, 0.5), STICK4, force=L)
    s.play(42, scale(MOTIF_A, 0.5, 8), TOMS4, vel_scale=0.8, force=L)
    # 43: ghost crescendo, then a tom pickup into the climax
    for i, st in enumerate(range(1, 12, 2)):
        s.hit(43, st, SNARE, 30 + i * 8, L)
    for st, n in zip((12, 13, 14, 15), (TOM_HI, TOM_HM, TOM_LO, FT_LO)):
        s.hit(43, st, n, 90 + (st - 12) * 10, hand(st))
    s.hit(43, 14, KICK, 100, RF)


def tom16(s, b, seq):
    acc = {int(st): a for st, _, a in seq}
    for st in range(16):
        h = hand(st)
        if st in acc and acc[st] == 2:
            s.hit(b, st, CRASH if h == R else CRASH2, 120, h)
        elif st in acc:
            s.hit(b, st, FT_LO, 110, h)
        else:
            s.hit(b, st, tom_run(st), 60, h)


def climax(s):
    s.swing = 0.55
    for b in range(44, 48):
        s.double_bass(b)
    s.power(44, MOTIF_A, TOMS4, unison=True)
    s.hit(44, 8, CHINA, 100, R)
    tom16(s, 45, shift(MOTIF_A, 2))
    s.power(46, invert(MOTIF_A), TOMS4, crash=CHINA, unison=True)
    s.hit(46, 8, CRASH, 96, R)
    tom16(s, 47, shift(MOTIF_A, 3))
    # 48-49: half-time on the china
    for b in (48, 49):
        s.chicks(b)
        for st in range(0, 16, 2):
            if b == 49 and st >= 12:
                continue
            s.hit(b, st, CHINA, 105 if st % 8 == 0 else 78, R)
        s.hit(b, 8, SNARE, 127, L)
        for st in (3, 5, 11):
            s.hit(b, st, SNARE, 34, L)
    for k in (0, 3, 6, 10):
        s.hit(48, k, KICK, 110, RF)
    s.hit(48, 13, SNARE, 34, L)
    for k in (0, 6, 10, 14):
        s.hit(49, k, KICK, 110, RF)
    for st, n in zip((12, 13, 14, 15), (TOM_HI, TOM_HM, TOM_LO, FT_LO)):
        s.hit(49, st, n, 110, hand(st))
    # 50-51: diminished motif with flams
    for b, seq in ((50, scale(MOTIF_A, 0.5) + scale(MOTIF_A, 0.5, 8)),
                   (51, scale(invert(MOTIF_A), 0.5) + scale(invert(MOTIF_A), 0.5, 8))):
        s.chicks(b)
        for st in range(0, 16, 2):
            s.hit(b, st, KICK, 86, RF)
        s.play(b, seq, TOMS4)
        for st, l, a in seq:
            if a == 2:
                h = hand(st, 0.5)
                s.hit(b, st, TOMS4[l], 48, L if h == R else R, dt=-20)
    # 52-53: 32nd runs around the kit, a cymbal on every beat
    down = [None, TOM_HI, TOM_HI, TOM_HM, TOM_HM, TOM_LO, FT_LO, FT_LO]
    up = [None, FT_LO, FT_LO, TOM_LO, TOM_HM, TOM_HM, TOM_HI, TOM_HI]
    for b in (52, 53):
        for beat in range(4):
            base = beat * 4
            ascending = (b == 53 and beat % 2 == 1)
            seqn = up if ascending else down
            s.hit(b, base, CHINA if ascending else CRASH, 122, R)
            s.hit(b, base, KICK, 118, RF)
            for i in range(1, 8):
                s.hit(b, base + i * 0.5, seqn[i], 72 + i * 5, R if i % 2 == 0 else L)
            s.hit(b, base + 2, KICK, 96, RF)
            s.hit(b, base + 1, KICK2, 84, LF)
            s.hit(b, base + 3, KICK2, 84, LF)
    # 54: the motif at full power over double bass
    s.double_bass(54, vel=90)
    s.power(54, MOTIF_A + PICKUP, TOMS4, unison=False, fill=tom_run, fill_vel=70)
    # 55: stop-time tutti on the motif, then silence
    for st, l, a in MOTIF_A:
        if a == 2:
            s.hit(55, st, CRASH, 127, R)
            s.hit(55, st, SNARE, 124, L)
            s.hit(55, st, KICK, 127, RF)
            s.hit(55, st, KICK2, 124, LF)
        else:
            s.hit(55, st, TOMS4[l], 118, hand(st))
            s.hit(55, st, KICK, 118, RF)


def ending(s):
    s.swing = 0.58
    s.play(56, MOTIF_A, TOMS4)
    s.hit(56, 0, KICK, 80, RF)
    s.chicks(56, vel=58)
    s.play(57, MOTIF_A + PICKUP, TOMS4, accent_kick=True)
    s.chicks(57, vel=62)
    for i in range(28):
        s.hit(58, i * 0.5, SNARE, 40 + i * 3.1, R if i % 2 == 0 else L)
    for k in (0, 4, 8, 12):
        s.hit(58, k, KICK, 70 + k * 3, RF)
    for st in (2, 6, 10):
        s.hit(58, st, HHP, 70, LF)
    s.hit(58, 14, FT_LO, 120, R)
    s.hit(58, 15, FT_LO, 124, L)
    s.hit(58, 15, KICK2, 110, LF)
    for n, limb in ((CRASH, R), (CRASH2, L), (KICK, RF), (KICK2, LF)):
        s.hit(59, 0, n, 127, limb, raw=True, dur=1800)


# ---------------------------------------------------------------- render
def render(events, path):
    evs = sorted(((max(0, int(round(t))), n, v, l, d) for t, n, v, l, d in events),
                 key=lambda e: (e[0], e[1], -e[2]))
    by = {}
    for e in evs:
        by.setdefault(e[1], []).append(e)
    msgs = []
    for n in sorted(by):
        filt = []
        for e in by[n]:
            if filt and e[0] == filt[-1][0]:
                continue
            filt.append(e)
        for i, e in enumerate(filt):
            off = e[0] + e[4]
            if i + 1 < len(filt):
                off = min(off, filt[i + 1][0] - 1)
            off = max(off, e[0] + 1)
            msgs.append((e[0], 1, n, e[2]))
            msgs.append((off, 0, n, 0))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("track_name", name="Drum Solo", time=0))
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    tr.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    tr.append(mido.Message("program_change", channel=CH, program=0, time=0))
    now = 0
    for t, kind, n, v in msgs:
        dt = t - now
        now = t
        if kind == 1:
            tr.append(mido.Message("note_on", channel=CH, note=n, velocity=v, time=dt))
        else:
            tr.append(mido.Message("note_off", channel=CH, note=n, velocity=0, time=dt))
    end = max(BARS * 16 * S16, now)
    tr.append(mido.MetaMessage("end_of_track", time=end - now))
    mid.save(path)


def main():
    s = Solo()
    intro(s)
    groove(s)
    develop(s)
    latin(s)
    build(s)
    breakdown(s)
    climax(s)
    ending(s)
    render(s.clean(), "solo.mid")


if __name__ == "__main__":
    main()
