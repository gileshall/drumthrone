#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

Uses only mido and involves no randomness, so every run writes the same file.

Musical plan (122 BPM, 4/4, 60 bars plus a final hit, about 2:00 total):
  Motif A : a 3+3+2 accent cell in 16ths (positions 0,3,6 | 8,11,14).
  Motif B : an "answer" bar with ghost notes, then a triplet tom descent
            that lands on beat 4.
  Motif A is stated, reorchestrated (toms, cowbell, timbales, woodblocks,
  crashes), displaced by a 16th, augmented to 8ths, compressed into a
  hemiola, and stated in full before the final hit.

Feel is placed deliberately, with no random jitter:
  - swung 16ths, with a swing amount set per section;
  - snare laid back, ghost notes a little later still;
  - cymbals and hi-hat slightly ahead of the beat;
  - kick sits right on the beat.

Every note belongs to one limb (R hand, L hand, F right foot, H left foot).
Each limb can strike only one thing at a time.
"""
import mido

PPQ = 480
BPM = 122
BAR = 4 * PPQ
S = PPQ // 4  # one 16th note

# General MIDI percussion notes
K, K2, RIM, SN, CLAP, SN2 = 36, 35, 37, 38, 39, 40
T_LF, HH, T_HF, HHP, T_LM, HHO, T_HM, T_HI = 41, 42, 43, 44, 45, 46, 47, 48
CR, T_H, RIDE, CHINA, BELL, TAMB, SPL, CB, CR2 = 49, 50, 51, 52, 53, 54, 55, 56, 57
VIBRA, RIDE2 = 58, 59
BON_H, BON_L, CON_M, CON_O, CON_L = 60, 61, 62, 63, 64
TIM_H, TIM_L, AGO_H, AGO_L, CAB, MAR = 65, 66, 67, 68, 69, 70
CLV, WB_H, WB_L, TRI_M, TRI_O = 75, 76, 77, 80, 81

TOMS = {41, 43, 45, 47, 48, 50}
CYMS = {CR, CR2, CHINA, SPL, RIDE, BELL, RIDE2, TRI_O, VIBRA}
LATIN = {CB, TIM_H, TIM_L, AGO_H, AGO_L, BON_H, BON_L, CON_M, CON_O, CON_L,
         CLV, WB_H, WB_L, CAB, MAR, TAMB}

MOTIF = [0, 3, 6, 8, 11, 14]
MOTIF_W = [1.0, 0.8, 0.87, 0.96, 0.84, 1.0]

EV = []


def hit(bar, pos, note, vel, limb, dur=None, swing=True, extra=0):
    t = int(round(bar * BAR + pos * S))
    EV.append((t, note, float(vel), limb, dur, extra, swing))


def ramp(i, n, a, b):
    return a + (b - a) * (i / max(1, n - 1))


def flam(bar, pos, note, vel, lead='R', grace=None):
    other = 'L' if lead == 'R' else 'R'
    hit(bar, pos, grace or note, vel * 0.42, other, extra=-24)
    hit(bar, pos, note, vel, lead)


def roll(bar, p0, p1, note, v0, v1, step=0.5, lead='R'):
    n = int(round((p1 - p0) / step))
    for k in range(n):
        limb = lead if k % 2 == 0 else ('L' if lead == 'R' else 'R')
        hit(bar, p0 + k * step, note, ramp(k, n, v0, v1), limb)


def hf(bar, positions, vel=55):
    for p in positions:
        hit(bar, p, HHP, vel * (1.08 if (p // 4) % 2 else 0.92), 'H')


def motif(bar, voices, vel, shift=0, scale=1):
    for i, p in enumerate(MOTIF):
        pos = p * scale + shift
        for (n, l) in voices[i]:
            hit(bar, pos, n, vel * MOTIF_W[i], l)


def answer(bar, vel, ghosts=True, crash=False):
    if crash:
        hit(bar, 0, CR, vel, 'R')
    hit(bar, 0, K, vel * 0.8, 'F')
    if ghosts:
        for p, v in ((1, 22), (2, 28), (5, 24), (7, 32)):
            hit(bar, p, SN, v, 'L')
    toms = (T_H, T_LM, T_LF)
    stick = ('R', 'L', 'R')
    for i, n in enumerate(toms):
        hit(bar, 8 + i * 4 / 3, n, vel * (0.78 + 0.1 * i), stick[i], swing=False)
    hit(bar, 12, K, vel, 'F')
    hit(bar, 12, SN, vel * 1.05, 'L')
    hit(bar, 14, K, vel * 0.7, 'F')
    hit(bar, 15, SN, vel * 0.33, 'L')


def grooveA(bar, f=1.0, ride=False, end=16, kicks=None, open14=True):
    if ride:
        for p in [0, 2, 3, 4, 6, 8, 10, 11, 12, 14]:
            if p >= end:
                continue
            if p in MOTIF:
                hit(bar, p, BELL, (94 if p in (0, 8) else 80) * f, 'R')
            else:
                hit(bar, p, RIDE, (64 if p % 4 == 0 else 52) * f, 'R')
        hf(bar, [p for p in (4, 12) if p < end], 58)
    else:
        for p in range(0, end, 2):
            if p == 14 and open14:
                hit(bar, p, HHO, 78 * f, 'R')
            else:
                hit(bar, p, HH, (88 if p % 4 == 0 else 60) * f, 'R')
        if open14 and end > 14:
            hit(bar, 16, HHP, 58, 'H')
    for p, v in ((4, 108), (12, 112)):
        if p < end:
            hit(bar, p, SN, v * f, 'L')
    for p, v in ((7, 30), (9, 24), (11, 36), (15, 32)):
        if p < end:
            hit(bar, p, SN, v, 'L')
    for p, v in (kicks or [(0, 100), (3, 76), (6, 90), (10, 86)]):
        if p < end:
            hit(bar, p, K, v * f, 'F')


def halftime(bar, f=1.0, end=16, china8=False, kicks=None):
    for p in range(0, end, 2):
        if p in (0, 8):
            hit(bar, p, BELL, 95 * f, 'R')
        else:
            hit(bar, p, RIDE, (70 if p % 4 == 0 else 55) * f, 'R')
    if china8 and end > 8:
        hit(bar, 8, CHINA, 112 * f, 'R')
    if end > 8:
        hit(bar, 8, SN, 122 * f, 'L')
    for p, v in ((3, 26), (5, 30), (11, 28), (13, 34), (15, 42)):
        if p < end:
            hit(bar, p, SN, v, 'L')
    for p, v in (kicks or [(0, 110), (3, 72), (10, 86), (13, 70)]):
        if p < end:
            hit(bar, p, K, v * f, 'F')
    hf(bar, [p for p in (4, 12) if p < end], 60)


def accent_stream(bar, shift, gv0, gv1, av, acc_notes, stream=SN,
                  kick_idx=(0, 3), stream_notes=None):
    acc = {}
    for i, p in enumerate(MOTIF):
        if p + shift < 16:
            acc[p + shift] = i
    for p in range(16):
        limb = 'R' if p % 2 == 0 else 'L'
        if p in acc:
            i = acc[p]
            hit(bar, p, acc_notes[i], av * MOTIF_W[i], limb)
            if i in kick_idx:
                hit(bar, p, K, av * 0.95, 'F')
        else:
            n = stream if stream_notes is None else stream_notes[p]
            hit(bar, p, n, ramp(p, 16, gv0, gv1), limb)


def shots(bar, shift, cyms, fv0, fv1):
    acc = {p + shift: i for i, p in enumerate(MOTIF) if p + shift < 16}
    for p in range(16):
        if p in acc:
            i = acc[p]
            hit(bar, p, cyms[i], 116 * MOTIF_W[i], 'R')
            hit(bar, p, K, 112 * MOTIF_W[i], 'F')
        else:
            hit(bar, p, SN, ramp(p, 16, fv0, fv1), 'L')


def sext(bar, beat0, pairs, v0, v1):
    n = len(pairs) * 6
    for k in range(n):
        bi, j = k // 6, k % 6
        pos = (beat0 + bi) * 4 + j * 2 / 3
        v = ramp(k, n, v0, v1)
        a, b = pairs[bi]
        if j == 0:
            hit(bar, pos, a, v * 1.08, 'R', swing=False)
        elif j == 1:
            hit(bar, pos, b, v * 0.78, 'L', swing=False)
        elif j == 2:
            hit(bar, pos, a, v * 0.9, 'R', swing=False)
        elif j == 3:
            hit(bar, pos, b, v * 0.82, 'L', swing=False)
        elif j == 4:
            hit(bar, pos, K, v * 0.95, 'F', swing=False)
        else:
            hit(bar, pos, K2, v * 0.85, 'H', swing=False)


def trip_run(bar, beat0, notes, v0, v1):
    n = len(notes)
    for k, nt in enumerate(notes):
        pos = beat0 * 4 + k * 2 / 3
        v = ramp(k, n, v0, v1) * (1.1 if k % 3 == 0 else 0.92)
        hit(bar, pos, nt, v, 'R' if k % 2 == 0 else 'L', swing=False)
    for b in range(n // 6):
        hit(bar, (beat0 + b) * 4, K, ramp(b * 6, n, v0, v1), 'F')


def dbass(bar, v=70, acc=(), start=0, end=16):
    for p in range(start, end):
        vv = v * (1.35 if p in acc else 1.0) + (8 if p % 4 == 0 else 0)
        if p % 2 == 0:
            hit(bar, p, K, vv, 'F')
        else:
            hit(bar, p, K2, vv * 0.92, 'H')


def bell(bar, acc_note=CB, other=CB, f=1.0):
    for p in [0, 2, 3, 4, 6, 8, 10, 11, 12, 14]:
        if p in MOTIF:
            hit(bar, p, acc_note, 100 * f, 'R')
        else:
            hit(bar, p, other, 62 * f, 'R')


def tumbao(bar, f=1.0):
    for p, v in ((0, 58), (6, 92), (12, 86)):
        hit(bar, p, K, v * f, 'F')
    hf(bar, (4, 12), 60)


# ---------------------------------------------------------------- sections
def intro():
    for b in range(4):
        hf(b, (0, 4, 8, 12), 52 + b * 3)
    V0 = [[(K, 'F')], [(SN, 'L')], [(T_LF, 'R')], [(K, 'F'), (SN, 'L')],
          [(T_LM, 'R')], [(SN, 'L')]]
    motif(0, V0, 80)
    answer(1, 82)
    V2 = [[(K, 'F'), (T_H, 'R')], [(T_HI, 'L')], [(T_LM, 'R')],
          [(K, 'F'), (T_LF, 'R')], [(T_HM, 'L')], [(SN, 'L')]]
    motif(2, V2, 88)
    for p in (1, 5, 9):
        hit(2, p, SN, 24, 'L')
    hit(3, 0, K, 92, 'F'); hit(3, 0, T_LF, 92, 'R')
    hit(3, 3, SN, 72, 'L'); hit(3, 6, T_LF, 82, 'R'); hit(3, 7, K, 70, 'F')
    notes = [SN, SN, T_H, T_H, T_HI, T_HM, T_LM, T_LF]
    for i, n in enumerate(notes):
        hit(3, 8 + i, n, ramp(i, 8, 55, 114), 'R' if i % 2 == 0 else 'L')
    hit(3, 8, K, 72, 'F'); hit(3, 12, K, 92, 'F')


def groove_section():
    hit(4, 0, CR, 114, 'R'); grooveA(4)
    grooveA(5, kicks=[(0, 100), (3, 76), (6, 90), (10, 86), (13, 64)])
    grooveA(6, f=1.04)
    grooveA(7, end=8)
    hf(7, (8, 12), 56)
    fill = [(8, T_H, 'R', 72), (9, T_H, 'L', 60), (10, T_HI, 'R', 82),
            (11, T_LM, 'L', 66), (12, T_LF, 'R', 102), (13, SN, 'L', 88),
            (14, T_LF, 'R', 110)]
    for p, n, l, v in fill:
        hit(7, p, n, v, l)
    hit(7, 12, K, 96, 'F'); hit(7, 15, K, 90, 'F')
    hit(8, 0, CR, 116, 'R'); grooveA(8, ride=True)
    grooveA(9, ride=True, kicks=[(0, 100), (3, 80), (6, 88), (8, 72), (11, 84), (14, 80)])
    grooveA(10, ride=True, f=1.05)
    grooveA(11, ride=True, end=8)
    trip_run(11, 2, [T_H, T_H, T_HI, T_HI, T_HM, T_HM, T_LM, T_LM, T_HF, T_HF, T_LF, T_LF], 60, 116)


def latin_section():
    hit(12, 0, CR, 112, 'R')
    for b in (12, 13):
        bell(b)
        tumbao(b)
        for p in ((0, 6, 12) if b == 12 else (4, 8)):
            hit(b, p, CLV, 88, 'L')
    for b in (14, 15):
        bell(b, AGO_H, AGO_L)
        tumbao(b)
        congas = [(2, CON_M, 48), (6, CON_O, 80), (7, CON_O, 88), (10, CON_M, 46),
                  (14, CON_L, 90), (15, CON_L, 80)]
        if b == 15:
            congas = [(2, CON_M, 50), (6, CON_O, 82), (7, CON_O, 90), (10, CON_M, 52),
                      (11, CON_O, 76), (13, CON_O, 92), (15, CON_L, 104)]
        for p, n, v in congas:
            hit(b, p, n, v, 'L')

    def timb_stream(bar, shift, v0, v1):
        acc = {p + shift: i for i, p in enumerate(MOTIF) if p + shift < 16}
        accn = [TIM_L, TIM_H, CB, TIM_L, TIM_H, CB]
        for p in range(16):
            limb = 'R' if p % 2 == 0 else 'L'
            if p in acc:
                i = acc[p]
                hit(bar, p, accn[i], 110 * MOTIF_W[i], limb)
            else:
                hit(bar, p, BON_H if p % 2 == 0 else BON_L, ramp(p, 16, v0, v1), limb)

    timb_stream(16, 0, 36, 60); tumbao(16)
    timb_stream(17, 2, 42, 70); tumbao(17)
    # bar 18: abanico roll into a timbale/crash accent
    hit(18, 0, TIM_L, 106, 'R'); hit(18, 3, TIM_H, 90, 'L'); hit(18, 6, CB, 96, 'R')
    for p in (1, 2, 5):
        hit(18, p, BON_L, 34, 'L')
    roll(18, 8, 12, TIM_H, 40, 100)
    hit(18, 12, CR, 116, 'R'); hit(18, 12, TIM_H, 120, 'L')
    hit(18, 14, CB, 92, 'R'); hit(18, 15, TIM_L, 86, 'L')
    tumbao(18)
    notes = [TIM_H, TIM_H, TIM_L, TIM_L, T_H, T_H, T_HI, T_HM,
             T_HM, T_LM, T_LM, T_HF, T_HF, T_LF, T_LF, SN]
    for i, n in enumerate(notes):
        v = ramp(i, 16, 62, 118) + (10 if i % 4 == 0 else 0)
        hit(19, i, n, v, 'R' if i % 2 == 0 else 'L')
    for p in (0, 4, 8, 12, 15):
        hit(19, p, K, 70 + p * 3, 'F')


def build_section():
    accent_stream(20, 0, 28, 46, 106, [CR, T_HI, T_LF, T_H, T_LM, T_LF])
    accent_stream(21, 0, 40, 60, 108, [T_LF, T_HI, T_LF, T_H, T_LM, SN])
    for b in (20, 21):
        hf(b, (4, 12), 58)
    accent_stream(22, 1, 36, 56, 110, [CR, T_HI, T_LF, T_H, T_LM, T_LF])
    accent_stream(23, 1, 50, 72, 114, [CHINA, T_HI, T_LF, CR, T_LM, T_LF])
    for b in (22, 23):
        hit(b, 0, K, 82, 'F')
        hf(b, (4, 8, 12), 60)
    hit(24, 0, CR, 116, 'R')
    sext(24, 0, [(T_H, T_HI), (T_H, T_HI), (T_HI, T_HM), (T_HI, T_HM)], 64, 100)
    sext(25, 0, [(T_HM, T_LM), (T_LM, T_HF), (T_HF, T_LF), (T_LF, T_LF)], 88, 118)
    shots(26, 0, [CR, CHINA, CR2, CR, CHINA, CR2], 40, 82)
    for i, (p, n) in enumerate([(0, SN), (2, T_H), (4, T_HI), (6, T_LF)]):
        flam(27, p, n, 96 + i * 5, 'R')
        hit(27, p, K, 90, 'F')
    roll(27, 8, 16, SN, 40, 122)
    for p in (8, 10, 12, 14):
        hit(27, p, K, 70 + p * 3, 'F')


def break_section():
    hit(28, 0, CR, 124, 'R', dur=1400); hit(28, 0, CR2, 112, 'L', dur=1400)
    hit(28, 0, K, 122, 'F')
    hit(28, 10, TRI_O, 72, 'R', dur=900)
    hit(28, 14, SN, 26, 'L'); hit(28, 15, SN, 36, 'L')
    hf(28, (4, 8, 12), 46)
    # bar 29: motif whispered on side stick
    hf(29, (0, 4, 8, 12), 46)
    for i, p in enumerate(MOTIF):
        hit(29, p, RIM, 74 * MOTIF_W[i], 'L')
    for p, v in ((1, 18), (2, 24), (5, 20), (9, 22), (10, 26), (13, 24)):
        hit(29, p, SN, v, 'R')
    hit(29, 0, K, 56, 'F'); hit(29, 8, K, 50, 'F')
    # bar 30: motif on woodblocks
    hf(30, (0, 4, 8, 12), 48)
    wb = [WB_L, WB_H, WB_H, WB_L, WB_H, WB_L]
    for i, p in enumerate(MOTIF):
        hit(30, p, wb[i], 90 * MOTIF_W[i], 'R' if i % 2 == 0 else 'L')
    hit(30, 15, WB_H, 62, 'R')
    hit(30, 0, K, 62, 'F'); hit(30, 8, K, 58, 'F')
    # bar 31: vibraslap, then a roll that builds from nothing
    hit(31, 0, VIBRA, 96, 'R', dur=900); hit(31, 0, K, 62, 'F')
    hf(31, (4,), 50)
    roll(31, 6, 16, SN, 22, 120)
    hit(31, 8, K, 60, 'F'); hit(31, 12, K, 82, 'F'); hit(31, 14, K, 98, 'F')


def halftime_section():
    hit(32, 0, CR, 122, 'R'); hit(32, 0, CHINA, 104, 'L')
    halftime(32)
    halftime(33)
    aug = [(0, [(CR, 'R'), (K, 'F')]), (6, [(T_LF, 'R'), (K, 'F')]), (12, [(SN, 'L')]),
           (16, [(CHINA, 'R'), (K, 'F')]), (22, [(T_LF, 'R'), (K, 'F')]),
           (28, [(SN, 'L'), (CR, 'R'), (K, 'F')])]
    accpos = {p for p, _ in aug}
    for i, (p, vs) in enumerate(aug):
        for n, l in vs:
            hit(34, p, n, 120 * MOTIF_W[i], l)
    for p in range(32):
        if p not in accpos:
            hit(34, p, SN, ramp(p, 32, 22, 72), 'L')
            if p % 2 == 0:
                hit(34, p, HH, 52, 'R')
    hf(34, (4, 12, 20), 58)
    halftime(36, china8=True)
    halftime(37, china8=True, kicks=[(0, 110), (3, 74), (6, 80), (10, 88), (13, 72)])
    halftime(38)
    halftime(39, end=8)
    flam(39, 8, T_H, 104, 'R'); hit(39, 9, K, 86, 'F')
    hit(39, 10, SN, 44, 'L')
    flam(39, 11, T_HI, 110, 'R'); hit(39, 12, K, 92, 'F')
    hit(39, 13, SN, 54, 'L')
    flam(39, 14, T_LF, 120, 'R'); hit(39, 14, K, 110, 'F')
    hit(39, 15, K, 90, 'F')


LIN = [(0, K, 'F', 100), (1, HH, 'R', 72), (2, SN, 'L', 30), (3, HH, 'R', 56),
       (4, SN, 'L', 112), (5, HH, 'R', 62), (6, K, 'F', 90), (7, SN, 'L', 34),
       (8, HH, 'R', 84), (9, K, 'F', 84), (10, HH, 'R', 60), (11, SN, 'L', 40),
       (12, SN, 'L', 115), (13, HH, 'R', 62), (14, K, 'F', 88), (15, HHO, 'R', 82)]


def linear_section():
    hit(40, 0, CR, 118, 'R')
    for p, n, l, v in LIN:
        hit(40, p, n, v, l)
    hit(40, 16, HHP, 60, 'H')
    for p, n, l, v in LIN:
        if p == 10:
            n, v = T_HI, 84
        if p == 13:
            n, v = T_LF, 94
        hit(41, p, n, v, l)
    v42 = [[(CR, 'R'), (SN, 'L')], [(T_HI, 'R')], [(T_LM, 'L')],
           [(CR2, 'R'), (SN, 'L')], [(T_LF, 'R')], [(CHINA, 'R'), (SN, 'L')]]
    motif(42, v42, 116)
    dbass(42, 68, acc=set(MOTIF))
    hem = [CR, T_HI, CHINA, T_LM, CR2, T_LF]
    for i, p in enumerate((0, 3, 6, 9, 12, 15)):
        hit(43, p, hem[i], 104 + i * 3, 'R')
        if p in (0, 6, 12):
            hit(43, p, SN, 100 + i * 3, 'L')
    dbass(43, 72, acc={0, 3, 6, 9, 12, 15})
    hit(44, 0, CR, 118, 'R')
    sext(44, 0, [(T_H, T_HI), (T_HI, T_HM), (T_HM, T_LM), (T_LM, T_LF)], 72, 104)
    sext(45, 0, [(SN, T_H), (SN, T_HI), (SN, T_LM), (T_LF, T_HF)], 82, 116)
    V46 = [[(CR, 'R'), (SN, 'L'), (K, 'F')], [(T_LF, 'R'), (K, 'F')],
           [(CHINA, 'R'), (SN, 'L'), (K, 'F')], [(CR2, 'L'), (T_LF, 'R'), (K, 'F')],
           [(T_LM, 'R'), (K, 'F')], [(CR, 'R'), (SN, 'L'), (K, 'F')]]
    motif(46, V46, 120)
    hf(47, (0, 4), 60)
    sext(47, 2, [(T_H, T_HI), (T_LM, T_LF)], 60, 122)
    return V46


def climax_section(V46):
    hit(48, 0, CR, 120, 'R'); grooveA(48, f=1.1, ride=True)
    grooveA(49, f=1.1, ride=True,
            kicks=[(0, 104), (3, 84), (6, 92), (8, 76), (11, 88), (14, 84)])
    shots(50, 0, [CR, CHINA, CR2, CR, CHINA, CR2], 40, 72)
    shots(51, 1, [CR2, CHINA, CR, CR2, CHINA, CR], 60, 96)
    hit(52, 0, CR, 118, 'R')
    v52 = [[(T_H, 'R'), (K, 'F')], [(T_HI, 'L')], [(T_HM, 'R')],
           [(T_LM, 'R'), (K, 'F')], [(T_HF, 'L')], [(T_LF, 'R')]]
    motif(52, v52, 118, shift=1)
    dbass(52, 64, acc={1, 4, 7, 9, 12, 15})
    answer(53, 116, ghosts=True, crash=True)
    hit(54, 0, CR, 118, 'R')
    bell(54, f=1.06)
    tumbao(54, 1.1)
    for p, n, v in ((2, TIM_H, 60), (4, TIM_L, 96), (7, TIM_H, 82), (10, TIM_L, 62),
                    (12, SN, 112), (15, TIM_H, 74)):
        hit(54, p, n, v, 'L')
    stream = [T_H] * 4 + [T_HI] * 4 + [T_LM] * 4 + [T_LF] * 4
    accent_stream(55, 0, 62, 106, 120, [CR, SN, CHINA, CR, SN, CR2],
                  kick_idx=(0, 2, 3, 5), stream_notes=stream)


def finale(V46):
    motif(56, V46, 122)
    for p in range(16):
        if p not in MOTIF:
            hit(56, p, SN, ramp(p, 16, 44, 86), 'L')
    dbass(56, 62)
    hem = [CR, CHINA, CR2, CR, CHINA, CR2]
    acc = (0, 3, 6, 9, 12, 15)
    for i, p in enumerate(acc):
        hit(57, p, hem[i], 108 + i * 3, 'R')
        hit(57, p, K, 106 + i * 3, 'F')
    for p in range(16):
        if p not in acc:
            hit(57, p, SN, ramp(p, 16, 50, 98), 'L')
    hit(58, 0, CR, 122, 'R')
    sext(58, 0, [(T_H, T_HI), (T_HM, T_LM), (T_HF, T_LF), (SN, T_LF)], 88, 124)
    for i, (p, n) in enumerate([(0, SN), (2, T_H), (4, T_HM), (6, T_LF)]):
        flam(59, p, n, 104 + i * 5, 'R')
        hit(59, p, K, 104, 'F')
    hit(59, 3, K2, 86, 'H'); hit(59, 7, K2, 92, 'H')
    roll(59, 8, 14, SN, 62, 124)
    for p in (8, 10, 12):
        hit(59, p, K, 90 + (p - 8) * 5, 'F')
    hit(59, 14, T_LF, 126, 'R'); hit(59, 14, T_HF, 124, 'L'); hit(59, 14, K, 127, 'F')
    # position 15 is left silent on purpose: a breath before the last hit
    hit(60, 0, CR, 127, 'R', dur=1900)
    hit(60, 0, CR2, 127, 'L', dur=1900)
    hit(60, 0, K, 127, 'F', dur=600)
    hit(60, 0, K2, 118, 'H', dur=600)


# ---------------------------------------------------------------- feel
def swing_amount(bar):
    table = [(0, 16), (4, 18), (12, 0), (20, 12), (28, 20), (32, 20),
             (40, 8), (48, 18), (54, 0), (55, 10)]
    s = 0
    for b, v in table:
        if bar >= b:
            s = v
    return s


def swing(t, sw):
    if sw == 0:
        return t
    base, u = t - (t % 240), t % 240
    if u < 120:
        u2 = u * (120 + sw) / 120
    else:
        u2 = 120 + sw + (u - 120) * (120 - sw) / 120
    return base + int(round(u2))


def micro(note, vel):
    if note in (SN, SN2, RIM, CLAP):
        return 7 + (5 if vel < 50 else 0)   # laid back, ghosts later still
    if note in TOMS:
        return 3
    if note in (HH, HHO, RIDE, BELL, RIDE2):
        return -4                            # cymbals push ahead
    if note == HHP:
        return -2
    if note in LATIN:
        return -3
    return 0


def render():
    out = []
    for (t, note, vel, limb, dur, extra, swok) in EV:
        t2 = swing(t, swing_amount(t // BAR)) if swok else t
        t2 += micro(note, vel) + extra
        v = int(max(1, min(127, round(vel))))
        out.append([max(0, t2), note, v, limb, dur])

    # One stroke per limb at a time: keep the louder stroke when two collide.
    limb_order = {'R': 0, 'L': 1, 'F': 2, 'H': 3}
    out.sort(key=lambda e: (e[0], limb_order[e[3]], -e[2], e[1]))
    bylimb = {}
    for e in out:
        lst = bylimb.setdefault(e[3], [])
        if lst and e[0] - lst[-1][0] < 45:
            if e[2] > lst[-1][2]:
                lst[-1] = e
            continue
        lst.append(e)
    kept = [e for l in ('R', 'L', 'F', 'H') for e in bylimb.get(l, [])]

    # Never let two limbs hit the very same sound at the same moment.
    kept.sort(key=lambda e: (e[1], e[0], -e[2]))
    final = []
    for e in kept:
        if final and final[-1][1] == e[1] and e[0] - final[-1][0] < 12:
            if e[2] > final[-1][2]:
                final[-1] = e
            continue
        final.append(e)

    # Note lengths, clipped so a note ends before its next strike.
    bynote = {}
    for e in final:
        bynote.setdefault(e[1], []).append(e)
    msgs = []
    for note in sorted(bynote):
        lst = sorted(bynote[note], key=lambda e: e[0])
        for i, e in enumerate(lst):
            t, _, v, _, dur = e
            if dur is None:
                dur = 600 if note in CYMS else 90
            off = t + dur
            if i + 1 < len(lst):
                off = min(off, lst[i + 1][0] - 1)
            off = max(off, t + 1)
            msgs.append((t, 1, note, v))
            msgs.append((off, 0, note, 0))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                               clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
    now = 0
    for t, kind, note, v in msgs:
        dt = t - now
        now = t
        if kind == 1:
            tr.append(mido.Message('note_on', channel=9, note=note, velocity=v, time=dt))
        else:
            tr.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=dt))
    tr.append(mido.MetaMessage('end_of_track', time=60))
    mid.save('solo.mid')


def main():
    intro()
    groove_section()
    latin_section()
    build_section()
    break_section()
    halftime_section()
    V46 = linear_section()
    climax_section(V46)
    finale(V46)
    render()


if __name__ == '__main__':
    main()
