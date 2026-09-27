#!/usr/bin/env python3
# drum_solo.py -- generates solo.mid, a ~2 minute General MIDI drum solo (channel 10)
import random
import mido

SEED = 1973

# ---- General MIDI percussion ----
K1 = 36; SN = 38; SS = 37; FT2 = 41; HHC = 42; FT1 = 43; PED = 44; LT = 45
HHO = 46; LMT = 47; HMT = 48; CR1 = 49; HT = 50; RD = 51; CHN = 52; BELL = 53
COW = 56; CR2 = 57; TRI = 81
CYMBALS = {CR1, CR2, CHN, RD, BELL, HHO, TRI}

MA = [0, 3, 6, 10, 12]          # motif A rhythm (16th positions in a 4/4 bar)

# tempo keyframes (bar, bpm at start of bar); linear in between
KEYS = [(0, 104), (3, 107), (11, 109), (19, 113), (20, 110), (22, 105), (24, 104),
        (26, 106), (33, 116), (36, 118), (41, 115), (42, 111), (44, 108), (47, 107),
        (49, 109), (50, 110), (52, 113), (53, 111), (54, 104), (60, 104)]


def lerp(a, b, x):
    return a + (b - a) * x


def clamp(v):
    return max(1, min(127, int(round(v))))


def build_bpm():
    bpm = []
    for bar in range(61):
        for k in range(len(KEYS) - 1):
            b0, v0 = KEYS[k]
            b1, v1 = KEYS[k + 1]
            if b0 <= bar <= b1:
                bpm.append(lerp(v0, v1, (bar - b0) / float(b1 - b0)))
                break
    return bpm


BPM = build_bpm()


def bpm_at(beat):
    bar = int(beat // 4)
    f = (beat - bar * 4) / 4.0
    return lerp(BPM[bar], BPM[bar + 1], f)


def B(bar, beat):
    return bar * 4 + beat


def path(drums):
    n = len(drums)
    return lambda i, p, c: drums[min(n - 1, int(p * n))]


def cyc(drums, per):
    return lambda i, p, c: drums[(i // per) % len(drums)]


def cres(a, b, acc=(), boost=16, every=0, curve=1.0):
    acc = set(acc)

    def f(i, p, c):
        v = lerp(a, b, p ** curve)
        if i in acc or (every and i % every == 0):
            v += boost
        return v
    return f


class Solo:
    def __init__(self):
        self.ev = []
        self.swing = 0.5
        self.rng = random.Random(SEED)
        self.feel = dict(hat=0, bb=0, ghost=0, kick=0, acc=0)

    # ---------- primitives ----------
    def hit(self, t, note, vel, limb, ms=0.0, dur=None):
        if dur is None:
            dur = 1.0 if note in CYMBALS else 0.1
        self.ev.append((t, note, clamp(vel), limb, ms, dur))

    def g(self, bar, x):
        """absolute beat of 16th position x in bar, with swing"""
        beat = bar * 4 + (x // 4)
        sub = x % 4
        if sub == 1:
            frac = self.swing * 0.5
        elif sub == 3:
            frac = 0.5 + self.swing * 0.5
        else:
            frac = sub * 0.25
        return beat + frac

    def flam(self, t, note, vel, main):
        other = 'L' if main == 'R' else 'R'
        self.hit(t, note, vel, main, self.feel['acc'])
        self.hit(t, note, 38, other, self.feel['acc'] - 26)

    def ped(self, bar, xs, vs):
        for x, v in zip(xs, vs):
            self.hit(self.g(bar, x), PED, v, 'LF', 0)

    def run(self, start, n, sub, sticking, voice, vel, push=0.0, swing=False):
        for i in range(n):
            c = sticking[i % len(sticking)]
            if c == '-':
                continue
            t = start + i / float(sub)
            if swing and sub == 4 and i % 2 == 1:
                t += (self.swing - 0.5) * 0.5
            p = i / float(max(1, n - 1))
            ms = -push * p
            if c == 'K':
                self.hit(t, K1, vel(i, p, c), 'RF', ms)
            else:
                self.hit(t, voice(i, p, c), vel(i, p, c), c, ms)

    def stream(self, start, n, sub, sticking, accents, ghost=SN, gv=(35, 55),
               kick=True, swing=False, push=0.0, fill_voice=None):
        for i in range(n):
            c = sticking[i % len(sticking)]
            t = start + i / float(sub)
            if swing and sub == 4 and i % 2 == 1:
                t += (self.swing - 0.5) * 0.5
            p = i / float(max(1, n - 1))
            ms = -push * p
            if i in accents:
                note, v = accents[i]
                self.hit(t, note, v, c, ms + self.feel['acc'])
                if kick:
                    self.hit(t, K1, v - 8, 'RF', ms + self.feel['kick'])
            else:
                note = fill_voice(i, p, c) if fill_voice else ghost
                v = lerp(gv[0], gv[1], p)
                if (i + 1) in accents:
                    v += 8          # ghost leans into the accent
                self.hit(t, note, v, c, ms + self.feel['ghost'])

    def sixstroke(self, start, groups, Rv, Lv, va=(104, 122), vg=(54, 74)):
        def voice(i, p, c):
            k = i % 6
            gi = i // 6
            if k == 0:
                return Rv[gi % len(Rv)]
            if k == 5:
                return Lv[gi % len(Lv)]
            return SN

        def vel(i, p, c):
            return lerp(va[0], va[1], p) if i % 6 in (0, 5) else lerp(vg[0], vg[1], p)
        self.run(start, groups * 6, 6, "RLLRRL", voice, vel)

    # ---------- grooves ----------
    def groove(self, bar, ride=False, crash=False, open_at=None, upto=16,
               kick=(0, 3, 6, 10), extra=(), offacc=False, ghosts=None):
        f = self.feel
        for x in range(0, upto, 2):
            t = self.g(bar, x)
            if x == 0 and crash:
                self.hit(t, CR1, 114, 'R', f['acc'])
                continue
            if ride:
                self.hit(t, RD, 86 if x % 4 == 0 else 64, 'R', f['hat'])
            else:
                if offacc:
                    v = 92 if x % 4 == 2 else 70
                else:
                    v = 88 if x % 4 == 0 else 58
                v += x * 0.4                      # slight lift across the bar
                note = HHC
                if x == open_at:
                    note, v = HHO, 96
                self.hit(t, note, v, 'R', f['hat'])
        if open_at is not None and not ride:
            self.hit(self.g(bar, open_at + 2), PED, 62, 'LF', 0)
        for x in (4, 12):
            if x < upto:
                self.hit(self.g(bar, x), SN, 110, 'L', f['bb'])
        if ghosts is None:
            ghosts = [7, 9, 15] + self.rng.sample([1, 2, 3, 11, 14], 2)
        for x in ghosts:
            if x < upto and x not in (4, 12):
                v = 30 + (10 if x in (3, 11) else 0) + self.rng.randint(0, 6)
                self.hit(self.g(bar, x), SN, v, 'L', f['ghost'])
        for x in kick:
            if x < upto:
                self.hit(self.g(bar, x), K1, 104 if x == 0 else 90, 'RF', f['kick'])
        for (x, note, v, limb) in extra:
            self.hit(self.g(bar, x), note, v, limb, f['acc'])

    def tomgroove(self, bar, crash=False, upto=16):
        f = self.feel
        for x in range(0, upto, 2):
            t = self.g(bar, x)
            if x == 0 and crash:
                self.hit(t, CR1, 118, 'R', f['acc'])
            elif x == 14:
                self.hit(t, CHN, 100, 'R', f['acc'])
            else:
                self.hit(t, FT2, 102 if x % 4 == 0 else 76, 'R', f['hat'])
        for x in (4, 12):
            if x < upto:
                self.hit(self.g(bar, x), SN, 116, 'L', f['bb'])
        for x, v in ((2, 36), (7, 40), (9, 34), (15, 46)):
            if x < upto:
                self.hit(self.g(bar, x), SN, v, 'L', f['ghost'])
        for x in MA + [8]:
            if x < upto:
                self.hit(self.g(bar, x), K1, 104 if x == 0 else 96, 'RF', f['kick'])

    # ---------- sections ----------
    def intro(self):
        self.swing = 0.56
        self.feel = dict(hat=-2, bb=10, ghost=5, kick=0, acc=0)
        for bar in range(4):
            self.ped(bar, (0, 4, 8, 12), (50, 68, 50, 68))
        g = self.g
        # bar 0: motif A stated plainly
        self.hit(g(0, 0), FT2, 112, 'R'); self.hit(g(0, 0), K1, 108, 'RF')
        self.flam(g(0, 3), SN, 100, 'L')
        self.hit(g(0, 6), FT2, 106, 'R'); self.hit(g(0, 6), K1, 96, 'RF')
        self.flam(g(0, 10), SN, 104, 'L')
        self.hit(g(0, 12), FT1, 118, 'R'); self.hit(g(0, 12), SN, 112, 'L')
        self.hit(g(0, 12), K1, 116, 'RF')
        # bar 1: answer with motif B down and up
        self.hit(g(1, 0), K1, 84, 'RF')
        for x, n, v, h in ((4, HT, 98, 'R'), (5, HMT, 84, 'L'), (6, LT, 90, 'R'), (7, FT2, 104, 'L')):
            self.hit(g(1, x), n, v, h)
        self.hit(g(1, 8), K1, 92, 'RF')
        self.hit(g(1, 10), SN, 34, 'R'); self.hit(g(1, 11), SN, 46, 'L')
        for x, n, v, h in ((12, FT2, 92, 'R'), (13, LT, 82, 'L'), (14, HMT, 90, 'R'), (15, HT, 106, 'L')):
            self.hit(g(1, x), n, v, h)
        self.hit(g(1, 12), K1, 78, 'RF')
        # bar 2: motif A as accents inside a stream of singles
        self.stream(B(2, 0), 16, 4, "RL",
                    {0: (FT2, 114), 3: (SN, 102), 6: (FT2, 108), 10: (LT, 106), 12: (FT2, 120)},
                    gv=(28, 46), swing=True)
        # bar 3: paradiddles into triplet run
        self.run(B(3, 0), 8, 4, "RLRRLRLL",
                 lambda i, p, c: {0: HT, 4: HMT}.get(i, SN),
                 lambda i, p, c: (100 if i == 0 else 104) if i in (0, 4) else lerp(44, 62, p),
                 swing=True)
        self.hit(B(3, 0), K1, 90, 'RF')
        self.run(B(3, 2), 12, 6, "RLK", path([HT, HMT, LT, FT1, FT2]),
                 cres(72, 116, every=3, boost=10), push=8)

    def groove_a(self):
        self.swing = 0.58
        self.feel = dict(hat=-2, bb=12, ghost=6, kick=0, acc=0)
        self.groove(4, crash=True)
        self.groove(5)
        self.groove(6, open_at=14)
        self.groove(7, upto=8)
        seq = [SN, SN, HT, HMT, LT, LT, FT1, FT2]
        self.run(B(7, 2), 8, 4, "RLRLRLRL", lambda i, p, c: seq[i],
                 cres(72, 110, acc=(0, 4), boost=12), swing=True, push=6)
        self.hit(self.g(7, 11), K1, 92, 'RF'); self.hit(self.g(7, 15), K1, 100, 'RF')
        self.groove(8, crash=True)
        self.groove(9)
        self.groove(10, kick=(0, 6, 8, 14), extra=((3, SN, 96, 'L'), (10, SN, 100, 'L')),
                    ghosts=[7, 9, 15, 1])
        self.stream(B(11, 0), 8, 4, "RL", {0: (HT, 104), 3: (HMT, 98), 6: (LT, 104)},
                    gv=(40, 58), swing=True)
        self.run(B(11, 2), 12, 6, "RLRLRL", path([HT, HMT, LT, FT1, FT2, FT2]),
                 cres(80, 120, every=3, boost=10), push=10)
        self.hit(B(11, 2), K1, 96, 'RF'); self.hit(B(11, 3), K1, 104, 'RF')

    def development(self):
        self.swing = 0.57
        self.feel = dict(hat=-2, bb=9, ghost=5, kick=-1, acc=0)
        for bar in (12, 13, 14, 15, 18):
            self.ped(bar, (4, 12), (66, 66))
        # motif on kick + ride bell
        self.groove(12, ride=True, crash=True, kick=MA,
                    extra=((3, BELL, 100, 'R'), (6, BELL, 104, 'R'),
                           (10, BELL, 102, 'R'), (12, BELL, 110, 'R')))
        # motif displaced by a 16th, paradiddle stream
        self.stream(B(13, 0), 16, 4, "RLRRLRLL",
                    {1: (SN, 104), 4: (HT, 100), 7: (HMT, 102), 11: (LT, 106), 13: (FT2, 112)},
                    gv=(32, 50), swing=True)
        self.groove(14, ride=True, upto=12, kick=(0, 3, 6, 10))
        mb = [HT, HMT, LT, FT2]
        self.run(B(14, 3), 4, 4, "RLRL", lambda i, p, c: mb[i], cres(92, 110), swing=True)
        self.hit(self.g(14, 12), K1, 94, 'RF'); self.hit(self.g(14, 15), K1, 98, 'RF')
        # motif on double strokes
        self.stream(B(15, 0), 16, 4, "RRLL",
                    {0: (FT2, 110), 3: (HT, 100), 6: (HMT, 104), 10: (LT, 106), 12: (FT2, 118)},
                    gv=(36, 56), swing=True)
        # 3 over 4 linear phrase, two bars
        self.swing = 0.55
        toms = [HT, HMT, LT, FT1, FT2, FT1, LT, HMT, HT, HMT, LT]

        def v16(i, p, c):
            if c == 'R':
                return lerp(92, 118, p)
            if c == 'L':
                return lerp(50, 80, p)
            return lerp(84, 108, p)
        self.run(B(16, 0), 32, 4, "RLK",
                 lambda i, p, c: toms[(i // 3) % len(toms)] if c == 'R' else SN,
                 v16, swing=True, push=4)
        for bar in (16, 17):
            self.ped(bar, (0, 4, 8, 12), (60, 72, 60, 72))
        # motif compressed into 16th triplets
        self.swing = 0.57
        acc = {0: (HT, 104), 2: (HMT, 98), 4: (LT, 102), 7: (FT1, 100), 9: (FT2, 110),
               12: (SN, 106), 14: (HT, 102), 16: (LT, 106), 19: (FT2, 112), 21: (FT2, 118)}
        self.stream(B(18, 0), 24, 6, "RL", acc, gv=(40, 62))
        # big fill, zig-zag around the kit
        zig = [SN, FT2, HT, FT1, HMT, LT]
        self.run(B(19, 0), 18, 6, "RL", lambda i, p, c: zig[(i // 3) % len(zig)],
                 cres(62, 106, every=3, boost=14), push=6)
        for k in range(3):
            self.hit(B(19, k), K1, 90 + 6 * k, 'RF')
        self.run(B(19, 3), 6, 6, "RLKRLK", lambda i, p, c: FT1 if i < 3 else FT2,
                 cres(108, 122), push=10)

    def breakdown(self):
        self.swing = 0.60
        self.feel = dict(hat=0, bb=14, ghost=8, kick=2, acc=0)
        g = self.g
        for bar in range(20, 26):
            self.ped(bar, (0, 4, 8, 12), (46, 62, 46, 62))
        self.hit(B(20, 0), CR1, 118, 'R'); self.hit(B(20, 0), K1, 112, 'RF')
        self.hit(B(20, 0), SN, 100, 'L')
        for x, v in ((3, 70), (6, 64), (10, 68), (12, 80)):
            self.hit(g(20, x), SS, v, 'L', 8)
        for x in (4, 8, 12):
            self.hit(g(20, x), K1, 34, 'RF', 2)
        # bar 21: side stick motif, floor tom heartbeat
        for x, v in zip(MA, (74, 62, 68, 66, 78)):
            self.hit(g(21, x), SS, v, 'L', 8)
        for x, v in ((0, 66), (7, 42), (8, 58), (14, 50)):
            self.hit(g(21, x), FT2, v, 'R', 4)
        for bar in (21, 22, 23):
            for x in (0, 4, 8, 12):
                self.hit(g(bar, x), K1, 36, 'RF', 2)
        # bar 22: motif on cowbell, triangle color
        for x, v in zip(MA, (74, 60, 66, 68, 80)):
            self.hit(g(22, x), COW, v, 'R', 0)
        self.hit(g(22, 8), TRI, 58, 'R', 0)
        for x, v in ((4, 70), (12, 74)):
            self.hit(g(22, x), SS, v, 'L', 10)
        for x, v in ((2, 28), (9, 32), (14, 30)):
            self.hit(g(22, x), SN, v, 'L', 8)
        # bar 23: soft tom melody
        mel = [HT, HMT, LT, FT2, FT2, LT, HMT, HT]
        vv = [58, 50, 54, 62, 60, 56, 64, 76]
        for k in range(8):
            self.hit(g(23, 2 * k), mel[k], vv[k], 'R' if k % 2 == 0 else 'L', 4)
        # bars 24-25: roll swell
        self.swing = 0.5
        self.run(B(24, 0), 56, 8, "RRLL", lambda i, p, c: SN,
                 lambda i, p, c: lerp(22, 112, p ** 1.5) - (5 if i % 2 == 1 else 0), push=6)
        for k in range(7):
            self.hit(B(24, 0) + k, K1, lerp(36, 92, k / 6.0), 'RF')
        for x, n, v, h in ((12, SN, 114, 'R'), (13, HT, 108, 'L'), (14, LT, 112, 'R'), (15, FT2, 120, 'L')):
            self.hit(g(25, x), n, v, h)
        self.hit(g(25, 12), K1, 96, 'RF'); self.hit(g(25, 15), K1, 104, 'RF')

    def build(self):
        self.swing = 0.53
        self.feel = dict(hat=-3, bb=4, ghost=2, kick=-3, acc=-2)
        KB = (0, 3, 6, 8, 10, 14)
        self.groove(26, crash=True, kick=KB, offacc=True)
        self.groove(27, upto=12, kick=KB, offacc=True)
        up = [FT2, LT, HMT, HT]
        self.run(B(27, 3), 4, 4, "RLRL", lambda i, p, c: up[i], cres(96, 114), swing=True)
        self.hit(self.g(27, 12), K1, 98, 'RF')
        # paradiddle-diddles around the kit
        tm = [HT, HMT, LT, FT2]
        self.run(B(28, 0), 24, 6, "RLRRLL",
                 lambda i, p, c: tm[(i // 6) % 4] if i % 6 == 0 else SN,
                 lambda i, p, c: lerp(96, 120, p) if i % 6 == 0 else lerp(44, 70, p))
        for k in range(4):
            self.hit(B(28, k), K1, 96, 'RF')
        self.ped(28, (4, 12), (70, 70))
        # motif shouted on crashes
        self.stream(B(29, 0), 16, 4, "RL",
                    {0: (CR1, 122), 3: (CR2, 112), 6: (CR1, 116), 10: (CR1, 114), 12: (CR1, 124)},
                    gv=(44, 66), swing=True)
        self.hit(self.g(29, 12), SN, 116, 'L')
        self.groove(30, kick=(0, 2, 3, 6, 8, 10, 11, 14), offacc=True, open_at=14)
        # groups of five over sextuplets
        t5 = [HT, HMT, LT, FT1, FT2]

        def v31(i, p, c):
            if i % 5 == 0:
                return lerp(98, 120, p)
            if c == 'K':
                return lerp(86, 104, p)
            return lerp(52, 76, p)
        self.run(B(31, 0), 24, 6, "RLRLK",
                 lambda i, p, c: t5[(i // 5) % 5] if c == 'R' else SN, v31)
        self.ped(31, (0, 4, 8, 12), (62, 74, 62, 74))
        self.groove(32, upto=8, kick=(0, 3, 6), offacc=True)
        self.sixstroke(B(32, 2), 2, [HT, LT], [HMT, FT2])
        self.hit(B(32, 2), K1, 100, 'RF'); self.hit(B(32, 3), K1, 104, 'RF')
        # 32nds up the kit, triplets down
        self.run(B(33, 0), 16, 8, "RL", path([FT2, FT1, LT, HMT, HT, SN]),
                 cres(70, 110, every=4, boost=12), push=4)
        self.hit(B(33, 0), K1, 96, 'RF'); self.hit(B(33, 1), K1, 102, 'RF')
        self.run(B(33, 2), 12, 6, "RLK", path([HT, HMT, LT, FT1, FT2]),
                 cres(100, 122, every=3, boost=4), push=10)

    def climax(self):
        self.swing = 0.52
        self.feel = dict(hat=-4, bb=3, ghost=1, kick=-4, acc=-3)
        g = self.g
        self.tomgroove(34, crash=True)
        self.tomgroove(35, upto=12)
        d6 = [HT, HMT, LT, LT, FT1, FT2]
        self.run(B(35, 3), 6, 6, "RLRLRL", lambda i, p, c: d6[i], cres(96, 120))
        self.hit(g(35, 12), K1, 100, 'RF')
        fillt = [HT, HMT, LT, FT1, FT2, LT, HMT, HT]
        self.stream(B(36, 0), 24, 6, "RL",
                    {0: (CR1, 124), 4: (CR1, 114), 9: (CR2, 116), 15: (CR2, 118), 18: (CHN, 122)},
                    gv=(56, 82), fill_voice=lambda i, p, c: fillt[(i // 3) % 8])
        self.sixstroke(B(37, 0), 4, [HT, HMT, LT, FT1], [HMT, LT, FT1, FT2])
        for k in range(4):
            self.hit(B(37, k), K1, 102, 'RF')
        self.ped(37, (4, 12), (72, 72))
        self.stream(B(38, 0), 16, 4, "RL",
                    {2: (CR1, 118), 5: (CR2, 112), 8: (CR1, 116), 12: (CR1, 120), 14: (CHN, 118)},
                    gv=(50, 72), fill_voice=cyc([SN, HT, SN, HMT, SN, LT, SN, FT2], 2), swing=True)
        bz = [HT, HMT, LT, FT1, FT2, FT1, LT, HMT]
        self.run(B(39, 0), 24, 6, "RLK", lambda i, p, c: bz[(i // 3) % 8],
                 cres(92, 120, every=3, boost=6), push=6)
        # bar 40: bursts and space
        self.run(B(40, 0), 8, 8, "RL", lambda i, p, c: SN, cres(58, 104))
        self.hit(B(40, 1), CR1, 122, 'R'); self.hit(B(40, 1), K1, 118, 'RF')
        self.hit(B(40, 1), SN, 110, 'L')
        self.ped(40, (6, 10), (64, 64))
        self.run(B(40, 2), 8, 8, "RL", path([HT, HMT, LT, FT2]), cres(82, 112), push=3)
        for x, n, v, h in ((12, HT, 112, 'R'), (13, HMT, 108, 'L'), (14, FT2, 118, 'R'), (15, SN, 112, 'L')):
            self.hit(g(40, x), n, v, h)
        for x, v in ((12, 100), (14, 108), (15, 110)):
            self.hit(g(40, x), K1, v, 'RF')
        # bar 41: motif hits, huge unison, then a beat of silence
        b = 41
        self.hit(g(b, 0), CR1, 124, 'R'); self.hit(g(b, 0), CR2, 118, 'L'); self.hit(g(b, 0), K1, 122, 'RF')
        self.hit(g(b, 3), CR2, 116, 'L'); self.hit(g(b, 3), FT2, 112, 'R'); self.hit(g(b, 3), K1, 116, 'RF')
        self.hit(g(b, 6), CR1, 118, 'R'); self.hit(g(b, 6), SN, 114, 'L'); self.hit(g(b, 6), K1, 116, 'RF')
        self.hit(g(b, 7), HT, 70, 'L'); self.hit(g(b, 8), HMT, 76, 'R'); self.hit(g(b, 9), LT, 84, 'L')
        self.hit(g(b, 10), CHN, 120, 'R'); self.hit(g(b, 10), K1, 118, 'RF')
        self.hit(g(b, 11), FT1, 94, 'L')
        self.hit(g(b, 12), CR1, 127, 'R', 0, 1.6); self.hit(g(b, 12), CR2, 124, 'L', 0, 1.6)
        self.hit(g(b, 12), K1, 127, 'RF')
        self.ped(41, (14,), (66,))

    def ret(self):
        self.swing = 0.58
        self.feel = dict(hat=-2, bb=12, ghost=6, kick=0, acc=0)
        self.groove(42, crash=True)
        self.groove(43)
        self.groove(44, open_at=14)
        self.groove(45, upto=12)
        mb = [HT, HMT, LT, FT2]
        self.run(B(45, 3), 4, 4, "RLRL", lambda i, p, c: mb[i], cres(90, 112), swing=True)
        self.hit(self.g(45, 12), K1, 92, 'RF'); self.hit(self.g(45, 15), K1, 100, 'RF')
        self.stream(B(46, 0), 16, 4, "RL",
                    {0: (FT2, 116), 3: (SN, 106), 6: (FT2, 110), 10: (LT, 108), 12: (FT2, 122)},
                    gv=(32, 52), swing=True)
        self.ped(46, (0, 4, 8, 12), (56, 70, 56, 70))
        self.groove(47, kick=(0, 6, 8, 14), extra=((3, SN, 98, 'L'), (10, SN, 102, 'L')),
                    ghosts=[7, 9, 15, 1])
        self.stream(B(48, 0), 16, 4, "RRLL",
                    {0: (CR1, 118), 3: (HT, 104), 6: (HMT, 106), 10: (LT, 108), 12: (FT2, 120)},
                    gv=(40, 60), swing=True)
        self.ped(48, (4, 12), (66, 66))
        # recall of the intro fill, hotter
        self.run(B(49, 0), 8, 4, "RLRRLRLL",
                 lambda i, p, c: {0: HT, 4: HMT}.get(i, SN),
                 lambda i, p, c: 108 if i in (0, 4) else lerp(50, 70, p), swing=True)
        self.hit(B(49, 0), K1, 96, 'RF')
        self.run(B(49, 2), 12, 6, "RLK", path([HT, HMT, LT, FT1, FT2]),
                 cres(84, 122, every=3, boost=8), push=8)

    def finale(self):
        self.swing = 0.53
        self.feel = dict(hat=-4, bb=3, ghost=1, kick=-4, acc=-3)
        g = self.g
        fillt = [HT, HMT, LT, FT1, FT2, LT, HMT, HT]
        self.stream(B(50, 0), 24, 6, "RL",
                    {0: (CR1, 124), 4: (CR1, 116), 9: (CR2, 118), 15: (CR2, 120), 18: (CHN, 124)},
                    gv=(60, 86), fill_voice=lambda i, p, c: fillt[(i // 3) % 8])
        bz = [HT, HMT, LT, FT2]
        self.run(B(51, 0), 12, 6, "RLK", lambda i, p, c: bz[(i // 3) % 4],
                 cres(96, 116, every=3, boost=6))
        self.sixstroke(B(51, 2), 2, [HT, LT], [HMT, FT2], va=(110, 124), vg=(60, 80))
        self.hit(B(51, 2), K1, 104, 'RF'); self.hit(B(51, 3), K1, 108, 'RF')
        # roll swell
        self.run(B(52, 0), 24, 8, "RRLL", lambda i, p, c: SN,
                 lambda i, p, c: lerp(48, 118, p ** 1.3) - (5 if i % 2 else 0), push=5)
        for k in range(3):
            self.hit(B(52, k), K1, lerp(70, 100, k / 2.0), 'RF')
        self.ped(52, (4, 12), (70, 70))
        d6 = [HT, HMT, LT, LT, FT1, FT2]
        self.run(B(52, 3), 6, 6, "RLRLRL", lambda i, p, c: d6[i], cres(112, 124))
        self.hit(B(52, 3), K1, 108, 'RF'); self.hit(B(52, 3) + 5 / 6.0, K1, 112, 'RF')
        # final motif statement with space, a last run, then the landing
        b = 53
        for x, (rn, rv), (ln, lv), kv in ((0, (CR1, 125), (SN, 118), 124),
                                         (3, (FT2, 116), (CR2, 120), 120),
                                         (6, (CR1, 122), (SN, 116), 120),
                                         (10, (CHN, 124), (SN, 118), 122)):
            self.hit(g(b, x), rn, rv, 'R', -3)
            self.hit(g(b, x), ln, lv, 'L', -3)
            self.hit(g(b, x), K1, kv, 'RF', -3)
        self.run(B(53, 3), 8, 8, "RL", path([SN, HT, HMT, LT, FT1, FT2]), cres(92, 124), push=4)
        self.hit(B(53, 3.5), K1, 100, 'RF')
        self.hit(B(54, 0), CR1, 127, 'R', 0, 4.0)
        self.hit(B(54, 0), CR2, 127, 'L', 0, 4.0)
        self.hit(B(54, 0), K1, 127, 'RF', 0, 1.0)

    # ---------- rendering ----------
    def render(self, fname="solo.mid"):
        STEP = 96
        nbeats = (len(BPM) - 2) * 4
        cum = [0.0]
        for k in range(nbeats * STEP):
            beat = (k + 0.5) / STEP
            cum.append(cum[-1] + 60.0 / bpm_at(beat) / STEP)

        def sec(b):
            x = b * STEP
            i = int(x)
            fr = x - i
            return cum[i] + (cum[i + 1] - cum[i]) * fr

        LEAD = 0.3
        LIMBS = ['RF', 'LF', 'R', 'L']
        GAP = {'R': 0.045, 'L': 0.045, 'RF': 0.075, 'LF': 0.09}
        jr = random.Random(SEED + 1)
        evs = []
        for (t, note, vel, limb, ms, dur) in self.ev:
            j = max(-3.0, min(3.0, jr.gauss(0.0, 1.2)))
            tt = LEAD + sec(t) + (ms + j) / 1000.0
            evs.append([tt, note, clamp(vel + jr.randint(-2, 2)), limb, dur])
        evs.sort(key=lambda e: (e[0], LIMBS.index(e[3]), e[1]))

        # playability: one stroke per limb at a time, with a minimum gap
        last = {}
        keep = []
        for e in evs:
            L = e[3]
            p = last.get(L)
            if p is not None and e[0] - p[0] < GAP[L]:
                if e[2] > p[2]:
                    p[2] = 0
                    last[L] = e
                    keep.append(e)
                continue
            last[L] = e
            keep.append(e)
        keep = [e for e in keep if e[2] > 0]

        TPB = 960
        TPS = TPB * 2  # 120 bpm file tempo -> 1920 ticks per second
        notes = {}
        for tt, note, vel, limb, dur in keep:
            tk = max(0, int(round(tt * TPS)))
            key = (tk, note)
            if key not in notes or notes[key][0] < vel:
                notes[key] = (vel, dur)
        by_pitch = {}
        for (tk, note), (vel, dur) in notes.items():
            by_pitch.setdefault(note, []).append((tk, vel, dur))
        msgs = []
        for note in sorted(by_pitch):
            lst = sorted(by_pitch[note])
            for i, (tk, vel, dur) in enumerate(lst):
                off = tk + int(dur * TPS)
                if i + 1 < len(lst):
                    off = min(off, lst[i + 1][0])
                off = max(off, tk + 1)
                msgs.append((tk, 1, note, vel))
                msgs.append((off, 0, note, 0))
        msgs.sort()

        mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
        tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
        tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
        tr.append(mido.Message('control_change', channel=9, control=7, value=118, time=0))
        tr.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
        tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
        prev = 0
        for tk, typ, note, vel in msgs:
            delta = tk - prev
            prev = tk
            if typ == 1:
                tr.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
            else:
                tr.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=delta))
        tr.append(mido.MetaMessage('end_of_track', time=TPS // 2))
        mid.save(fname)


def main():
    s = Solo()
    s.intro()        # bars 0-3
    s.groove_a()     # bars 4-11
    s.development()  # bars 12-19
    s.breakdown()    # bars 20-25
    s.build()        # bars 26-33
    s.climax()       # bars 34-41
    s.ret()          # bars 42-49
    s.finale()       # bars 50-53, final hit at bar 54
    s.render("solo.mid")


if __name__ == "__main__":
    main()
