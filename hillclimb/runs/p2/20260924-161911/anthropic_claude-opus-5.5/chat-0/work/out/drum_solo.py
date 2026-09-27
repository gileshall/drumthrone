#!/usr/bin/env python3
# drum_solo.py - generates a two-minute General MIDI drum solo (solo.mid) on channel 10.
import math
import random
import mido

PPQ = 480
BPM = 120            # 1 bar = 2 s ; 60 bars = 120 s
SWING = 0.58         # 16th off-beats placed at 58% of the 8th
GAP = 0.07           # minimum spacing (beats) between strokes of one limb

rng = random.Random(20240601)

# ---- General MIDI percussion ----
KICK2, KICK, SS, SN, CLAP, ESN = 35, 36, 37, 38, 39, 40
FT_L, HH, FT_H, PHH, T_L, OHH, T_LM, T_HM = 41, 42, 43, 44, 45, 46, 47, 48
CR, T_H, RIDE, CHINA, BELL, TAMB, SPL, COW = 49, 50, 51, 52, 53, 54, 55, 56
CR2, VIB, RIDE2 = 57, 58, 59
BONGO_H, BONGO_L, CONGA_MH, CONGA_H, CONGA_L = 60, 61, 62, 63, 64
TIMB_H, TIMB_L, AGO_H, AGO_L = 65, 66, 67, 68
WB_H, WB_L, TRI_M, TRI_O = 76, 77, 80, 81

FEET = {KICK2, KICK, PHH}
CYMBALS = {OHH, CR, RIDE, CHINA, BELL, SPL, CR2, VIB, RIDE2, TRI_O}

EV = []  # [beat_time, note, velocity, limb, duration_ticks_or_None]


def B(bar, beat=0.0):
    return bar * 4 + beat


def swing(t):
    whole = math.floor(t + 1e-9)
    f = t - whole
    for base in (0.0, 0.5):
        if abs(f - (base + 0.25)) < 1e-6:
            return whole + base + 0.5 * SWING
    return t


LEVEL = {'X': 1.0, 'x': 0.8, 'o': 0.62, 'G': 0.42, 'g': 0.3}


def vel(c, dyn):
    v = int(round(dyn * LEVEL[c])) + rng.randint(-2, 2)
    lo = 12 if c in 'gG' else 1
    return max(lo, min(127, v))


def hit(t, note, v, limb, sw=True, dur=None):
    assert (limb in 'KF') == (note in FEET), (t, note, limb)
    if sw:
        t = swing(t)
    EV.append([t, note, v, limb, dur])


def line(t0, span, pat, notes, stick=None, d0=100, d1=None, sw=None):
    pat = pat.replace(' ', '')
    n = len(pat)
    step = span / n
    if d1 is None:
        d1 = d0
    if sw is None:
        sw = abs(step - 0.25) < 1e-9 or abs(step - 0.5) < 1e-9 or abs(step - 1.0) < 1e-9
    if isinstance(notes, int):
        notes = [notes]
    hand = 'R'
    k = 0
    si = 0
    for i, c in enumerate(pat):
        if c == '.':
            continue
        t = t0 + i * step
        dyn = d0 + (d1 - d0) * (i / (n - 1) if n > 1 else 0)
        note = notes[k % len(notes)]
        k += 1
        if stick:
            limb = stick[si % len(stick)]
            si += 1
            if note in FEET and limb in 'RL':
                limb = 'K'
        elif note in FEET:
            limb = 'K'
        else:
            limb = hand
            hand = 'L' if hand == 'R' else 'R'
        hit(t, note, vel(c, dyn), limb, sw)


def hhfoot(bar, beats=(1, 3), dyn=66, c='x'):
    for b in beats:
        hit(B(bar, b), PHH, vel(c, dyn), 'F')


def unison(t, rn, ln, dyn, c='X', kick=True, sw=True):
    hit(t, rn, vel(c, dyn), 'R', sw)
    if ln:
        hit(t, ln, vel(c, dyn), 'L', sw)
    if kick:
        hit(t, KICK, vel(c, dyn), 'K', sw)


def dbl(t, span, d0, d1=None):
    n = int(round(span * 4))
    line(t, span, ('xo' * n)[:n], KICK, stick='KF', d0=d0, d1=d1)


# ---- MOTIF A: 3+3+2 accent cell with ghost fill, two beats ----
def motifA(t, n1, n2, n3, dyn=105, kick=True, ghost=SN):
    line(t, 2, "XggXggXg", [n1, ghost, ghost, n2, ghost, ghost, n3, ghost],
         stick="RLLRLLRL", d0=dyn)
    if kick:
        hit(t, KICK, vel('X', dyn), 'K')
        hit(t + 1.5, KICK, vel('x', dyn), 'K')


# ---- MOTIF A expanded: 3+3+3+3+4 over a bar ----
def motif_long(t, accs, dyn, d1=None, ghost=SN, shift=0, acc_hand='R',
               ghost_hand='L', kick=True, ghosts=True):
    pat = ['g' if ghosts else '.'] * 16
    pos = sorted((p + shift) % 16 for p in (0, 3, 6, 9, 12))
    for p in pos:
        pat[p] = 'X'
    for p in pos:
        q = (p - 1) % 16
        if pat[q] == 'g':
            pat[q] = '.'
    notes = []
    stick = ''
    ai = 0
    for c in pat:
        if c == 'X':
            notes.append(accs[ai % len(accs)])
            ai += 1
            stick += acc_hand
        elif c == 'g':
            notes.append(ghost)
            stick += ghost_hand
    line(t, 4, ''.join(pat), notes, stick=stick, d0=dyn, d1=d1)
    times = [t + p * 0.25 for p in pos]
    if kick:
        for tt in times:
            hit(tt, KICK, vel('x', dyn), 'K')
    return times


def acc_line(t, span, pat, accs, ghost, d0, d1=None, stick=None, kick_acc=False, kd=None):
    pat = pat.replace(' ', '')
    notes = []
    ai = 0
    for c in pat:
        if c == '.':
            continue
        if c == 'X':
            notes.append(accs[ai % len(accs)])
            ai += 1
        else:
            notes.append(ghost)
    line(t, span, pat, notes, stick, d0, d1)
    if kick_acc:
        step = span / len(pat)
        for i, c in enumerate(pat):
            if c == 'X':
                hit(t + i * step, KICK, vel('x', kd or d0), 'K', sw=abs(step - 0.25) < 1e-9)


def rlk(t, beats, hands, d0, d1=None, acc_every=3):
    n = int(round(beats * 6))
    notes = []
    pat = ''
    hi = 0
    for i in range(n):
        if i % 3 == 2:
            notes.append(KICK)
        else:
            notes.append(hands[hi % len(hands)])
            hi += 1
        pat += 'X' if i % acc_every == 0 else 'x'
    line(t, beats, pat, notes, stick='RLK', d0=d0, d1=d1)


def six(t, beats, hands, d0, d1=None, kick_beats=True):
    if d1 is None:
        d1 = d0
    n = int(round(beats * 6))
    pat = ''.join('X' if i % 6 == 0 else 'x' for i in range(n))
    line(t, beats, pat, hands, d0=d0, d1=d1)
    if kick_beats:
        for b in range(int(beats)):
            hit(t + b, KICK, vel('x', d0 + (d1 - d0) * b / beats), 'K', sw=False)


KICKPATS = ["X..x..X...x.....", "X..x..X...x..x..", "X..x..X.x.x.....", "X..x..X...x...x."]


def grooveA(bar, var=0, dyn=100, upto=4, top=HH, crash=False):
    t = B(bar)
    n = int(upto * 4)
    hat = "XgogXgogXgogXgog" if top == HH else "X.x.X.x.X.x.X.x."
    line(t, upto, hat[:n], top, stick='R', d0=dyn * 0.85)
    line(t, upto, "....X..g.g..X..g"[:n], SN, stick='L', d0=dyn)
    line(t, upto, KICKPATS[var % 4][:n], KICK, stick='K', d0=dyn * 0.95)
    if var % 4 == 1 and upto >= 4 and top == HH:
        hit(t + 3.5, OHH, vel('x', dyn), 'R')
    if crash:
        hit(t, CR, vel('X', dyn + 10), 'R')


def linear(t, rnotes, dyn, d1=None):
    pat = "XgxXXxXgxXgxXgxX"
    stick = "RLKRLKRLKRLKRLKL"
    notes = []
    ri = 0
    for s in stick:
        if s == 'R':
            notes.append(rnotes[ri % len(rnotes)])
            ri += 1
        elif s == 'L':
            notes.append(SN)
        else:
            notes.append(KICK)
    line(t, 4, pat, notes, stick=stick, d0=dyn, d1=d1)


def whisper(t, beats, acc=HH, dyn=62):
    n = int(beats * 4)
    pat = ("XggXggXg" * 2)[:n]
    st = ("RLLRLLRL" * 2)[:n]
    notes = [(acc if s == 'R' else SN) for s in st]
    line(t, beats, pat, notes, stick=st, d0=dyn)


# =====================================================================
# INTRO (bars 0-3): state motif A
for bar in range(0, 4):
    hhfoot(bar, (1, 3), 62)
motifA(B(0), SN, T_H, FT_L, 98)
hit(B(0, 3), FT_L, vel('x', 100), 'R')
hit(B(0, 3), KICK, vel('x', 100), 'K')
motifA(B(1), SN, T_H, FT_L, 102)
line(B(1, 2), 2, "xxxxxxxX", [T_H, T_H, T_HM, T_HM, T_LM, T_LM, FT_H, FT_L], d0=78, d1=112)
hit(B(1, 3), KICK, vel('x', 100), 'K')
motifA(B(2), SN, T_HM, FT_H, 104)
motifA(B(2, 2), T_HM, T_LM, FT_L, 110)
line(B(3), 3, "gggGGGoooxxx", SN, d0=80, d1=112)
line(B(3, 3), 1, "XxXX", [T_H, T_LM, FT_H, FT_L], d0=116)
hit(B(3, 3), KICK, vel('x', 105), 'K')

# GROOVE A (bars 4-11): motif lives in the kick
for i, bar in enumerate(range(4, 12)):
    ph = i % 4
    dyn = 94 + 3 * ph
    if bar == 7:
        grooveA(bar, var=3, dyn=dyn, upto=3)
        line(B(7, 3), 1, "XgxX", [SN, SN, T_H, FT_L], d0=112)
    elif bar == 11:
        grooveA(bar, var=2, dyn=dyn, upto=2)
        rlk(B(11, 2), 2, [T_H, T_HM, T_HM, T_LM, T_LM, T_L, FT_H, FT_L], 88, 120)
    else:
        grooveA(bar, var=ph, dyn=dyn, crash=(bar in (4, 8)))

# DEVELOPMENT (bars 12-15): ride + expanded / displaced motif in left hand
for i, bar in enumerate(range(12, 16)):
    t = B(bar)
    dyn = [94, 100, 103, 110][i]
    if i in (0, 3):
        hit(t, CR, vel('X', dyn + 8), 'R')
        hit(t, KICK, vel('X', dyn), 'K')
    line(t, 4, "X..xX..xX..xX..x", RIDE, stick='R', d0=dyn * 0.82)
    hhfoot(bar, (1, 3), 70)
    line(t, 4, "g...g...g...g...", KICK, stick='K', d0=dyn)
    accs = [[SN] * 5, [SN, T_H, SN, T_HM, FT_L], [SN] * 5, [T_H, T_HM, T_LM, FT_H, FT_L]][i]
    shift = [0, 0, 1, 0][i]
    motif_long(t, accs, dyn, d1=dyn + 6, shift=shift, acc_hand='L', ghost_hand='L')

# LINEAR 3-over-4 (bars 16-19)
linear(B(16), [BELL], 100, 106)
hit(B(16), CR, vel('X', 110), 'R')
hhfoot(16, (1, 3), 68)
linear(B(17), [BELL, BELL, COW, BELL, COW], 104, 110)
hhfoot(17, (1, 3), 70)
linear(B(18), [T_H, T_HM, T_LM, FT_H, FT_L], 106, 116)
hhfoot(18, (1, 3), 72)
rlk(B(19), 2, [T_H, SN, T_HM, SN, T_LM, SN, FT_L, SN], 100, 118)
unison(B(19, 2), CR, SN, 124)
hhfoot(19, (3,), 60)

# CONTRAST (bars 20-23): percussion colours, clave, motif on timbales/congas
for i, bar in enumerate(range(20, 24)):
    t = B(bar)
    d0 = 66 + 6 * i
    d1 = d0 + 8
    line(t, 4, "X.xX.xX.X.xX.xx.", COW, stick='R', d0=d0, d1=d1)
    if bar == 20:
        line(t, 4, "....X...X.......", SS, stick='L', d0=d0 + 16)
    elif bar == 21:
        line(t, 4, "X.....X.....X...", SS, stick='L', d0=d0 + 16)
    elif bar == 22:
        line(t, 4, "X..X..X...x.x...", [TIMB_H, TIMB_L, CONGA_L, SS, SS], stick='L', d0=88, d1=96)
    else:
        line(t, 4, "X..X..X..X..X...", [TIMB_H, TIMB_L, CONGA_H, CONGA_L, TIMB_L],
             stick='L', d0=92, d1=104)
        hit(B(23, 3.5), VIB, vel('x', 92), 'L')
    line(t, 4, "......x.....X...", KICK, stick='K', d0=d0 + 10)
    line(t, 4, "G...G...G...G...", PHH, stick='F', d0=d0 + 20)

# MOTIF B (bars 24-27): four-note groups over triplets
for bar in range(24, 28):
    hhfoot(bar, (0, 1, 2, 3), 64, 'o')
line(B(24), 8, "Xxxo" * 6, [TIMB_H, TIMB_L, CONGA_L, KICK], stick='RLRK', d0=76, d1=100)
line(B(26), 4, "Xxxo" * 3, [T_H, SN, FT_L, KICK], stick='RLRK', d0=96, d1=110)
line(B(27), 2, "Xxxo" * 3, [T_HM, SN, FT_H, KICK], stick='RLRK', d0=106, d1=114)
six(B(27, 2), 2, [SN, SN, T_H, T_H, T_HM, T_HM, T_LM, T_LM, FT_H, FT_H, FT_L, FT_L], 100, 125)

# BUILD (bars 28-35)
for bar in range(28, 32):
    hhfoot(bar, (0, 1, 2, 3), 66)
hit(B(28), CR, vel('X', 112), 'R')
acc_line(B(28), 4, "XggXggXgXggXggXg", [SN], SN, 90, 96)
line(B(28), 4, "X.......X.......", KICK, stick='K', d0=96)
acc_line(B(29), 4, "XggXggXgXggXgXgX", [SN], SN, 92, 104)
line(B(29), 4, "X.......X...x...", KICK, stick='K', d0=98)
acc_line(B(30), 4, "XggXggXgXggXggXg", [T_H, T_HM, FT_L, T_H, T_LM, FT_L], SN, 96, 106, kick_acc=True)
acc_line(B(31), 4, "XggXggXgXgXgXXXX",
         [T_H, T_HM, FT_L, T_HM, T_LM, T_H, T_HM, T_LM, FT_L], SN, 102, 118, kick_acc=True)
for bar in (32, 33):
    t = B(bar)
    dyn = 104 if bar == 32 else 108
    dbl(t, 4, dyn * 0.9, dyn)
    line(t, 4, "X.x.X.x.X.x.X.x.", [BELL, RIDE], stick='R', d0=dyn * 0.85)
    line(t, 4, "....X..g.g..X..g", SN, stick='L', d0=dyn)
hit(B(32), CR, vel('X', 118), 'R')
line(B(33, 3), 1, "XxXx", [T_H, T_HM, T_LM, FT_L], d0=114)
hit(B(34), CR, vel('X', 120), 'R')
acc_line(B(34), 4, "XggXggXgXggXggXg", [SN, SN, T_H, SN, SN, FT_L], SN, 104, 116)
dbl(B(34), 4, 100, 112)
six(B(35), 4, [SN, T_H] * 3 + [T_H, T_HM] * 3 + [T_HM, T_LM] * 3 + [FT_H, FT_L] * 3, 96, 127)

# CLIMAX (bars 36-43)
t = B(36)
unison(t, CR, SN, 124)
unison(t + 0.75, CHINA, SN, 120)
unison(t + 1.5, CR2, FT_L, 124)
dbl(t, 2, 90, 100)
line(t + 2, 2, "xxxxxxxX", [T_H, T_H, T_HM, T_HM, T_LM, T_LM, FT_H, FT_L], d0=100, d1=124)
line(t + 2, 2, "x.x.x.x.", KICK, stick='K', d0=106)
t = B(37)
unison(t, CR, SN, 124)
unison(t + 0.75, CHINA, T_HM, 118)
unison(t + 1.5, CR2, FT_L, 122)
unison(t + 2, CR, SN, 120)
unison(t + 2.75, CHINA, T_LM, 118)
unison(t + 3.5, CR2, FT_L, 124)
dbl(t, 4, 92, 108)
hit(B(38), CR, vel('X', 122), 'R')
rlk(B(38), 4, [SN, T_H, SN, T_HM, SN, T_LM, SN, FT_L], 100, 118)
rlk(B(39), 4, [T_H, T_HM, T_HM, T_LM, T_LM, FT_H, FT_H, FT_L], 92, 124, acc_every=4)
for bar in (40, 41):
    t = B(bar)
    upto = 4 if bar == 40 else 3
    n = upto * 4
    line(t, upto, "X.x.X.x.X.x.X.x."[:n], [BELL, RIDE], stick='R', d0=100)
    line(t, upto, "...g....X...g..g"[:n], SN, stick='L', d0=118)
    line(t, upto, ("X..x..X...X.x.x." if bar == 40 else "X..x..X...x.")[:n], KICK, stick='K', d0=112)
hit(B(40), CR, vel('X', 124), 'R')
line(B(41, 3), 1, "xxxxxxxx", SN, d0=92, d1=124)
hit(B(41, 3), KICK, vel('x', 110), 'K')
t = B(42)
rn = [CR, CHINA, CR2, CHINA, CR]
ln = [SN, T_HM, SN, T_LM, FT_L]
for k, p in enumerate([0, 3, 6, 9, 12]):
    unison(t + p * 0.25, rn[k], ln[k], 116 + 2 * k)
dbl(t, 4, 88, 104)
line(B(42, 3.25), 0.75, "xxX", SN, stick="LRL", d0=104, d1=124)
unison(B(43), CR, SN, 127)
hit(B(43), CR2, vel('X', 120), 'L') if False else None
hhfoot(43, (1, 2, 3), 60, 'o')
line(B(43, 2.5), 1.5, "gggggg", SN, d0=74)

# BREAKDOWN (bars 44-47): whispered call, thunderous response
whisper(B(44), 2)
hhfoot(44, (0, 1), 60, 'o')
motifA(B(44, 2), CR, T_LM, FT_L, 122)
whisper(B(45), 2, acc=SS)
hhfoot(45, (0, 1), 60, 'o')
motifA(B(45, 2), CHINA, T_HM, FT_H, 122)
whisper(B(46), 1)
rlk(B(46, 1), 1, [T_H, T_HM, T_LM, FT_L], 110, 122)
whisper(B(46, 2), 1, acc=SS)
rlk(B(46, 3), 1, [T_HM, T_LM, FT_H, FT_L], 112, 126)
acc_line(B(47), 4, "XggXggXgXggXgXgX", [SN], SN, 60, 124)
line(B(47), 4, "x.x.x.x.x.x.x.x.", KICK, stick='K', d0=70, d1=118)

# RETURN (bars 48-55): the groove and motifs come back, bigger
grooveA(48, var=0, dyn=110, crash=True)
grooveA(49, var=1, dyn=112)
motifA(B(50), SN, T_HM, FT_H, 112)
motifA(B(50, 2), T_HM, T_LM, FT_L, 118)
hhfoot(50, (1, 3), 70)
grooveA(51, var=2, dyn=112, upto=2)
rlk(B(51, 2), 2, [T_H, T_HM, T_HM, T_LM, T_LM, T_L, FT_H, FT_L], 96, 124)
specs = [(0, [SN] * 5, 106, [CR, CHINA, CR2, CHINA, CR]),
         (1, [SN] * 5, 110, [CR2, SPL, CR, SPL, CHINA]),
         (0, [T_H, T_HM, T_LM, FT_H, FT_L], 114, [CR, CHINA, CR2, CHINA, CR])]
for k, (sh, accs, dyn, cy) in enumerate(specs):
    t = B(52 + k)
    times = motif_long(t, accs, dyn, d1=dyn + 6, shift=sh, acc_hand='L', ghost_hand='L')
    for j, tt in enumerate(times):
        hit(tt, cy[j], vel('X', dyn + 6), 'R')
    dbl(t, 4, dyn * 0.8, dyn * 0.9)
t = B(55)
unison(t, CR, SN, 120)
unison(t + 0.75, CHINA, SN, 118)
unison(t + 1.5, CR2, FT_L, 122)
line(t + 2, 2, "xxxxxxxX", [SN, SN, T_H, T_H, T_LM, T_LM, FT_L, FT_L], d0=100, d1=124)
line(t + 2, 2, "x.x.x.x.", KICK, stick='K', d0=106)

# FINAL BUILD (bars 56-58) and the last hit (bar 59)
hit(B(56), CR, vel('X', 124), 'R')
acc_line(B(56), 4, "XggXggXgXggXggXg", [T_H, T_HM, FT_L, T_H, T_LM, FT_L], SN, 100, 114, kick_acc=True)
dbl(B(56), 4, 92, 108)
hit(B(57), CR, vel('X', 122), 'R')
six(B(57), 4, [SN, T_H] * 3 + [T_H, T_HM] * 3 + [T_HM, T_LM] * 3 + [FT_H, FT_L] * 3, 98, 122)
t = B(58)
unison(t, CR, SN, 126)
unison(t + 0.75, CHINA, T_HM, 122)
unison(t + 1.5, CR2, FT_L, 126)
dbl(t, 2, 96, 110)
rlk(t + 2, 1, [T_H, T_HM, T_LM, FT_L], 108, 118)
line(t + 3, 1, "xxxxxxxx", SN, d0=100, d1=127)
line(t + 3, 1, "x.x.", KICK, stick='K', d0=112)
FINAL_DUR = 4 * PPQ - 10
hit(B(59), CR, 127, 'R', dur=FINAL_DUR)
hit(B(59), CR2, 127, 'L', dur=FINAL_DUR)
hit(B(59), KICK, 127, 'K', dur=FINAL_DUR)
hit(B(59), KICK2, 122, 'F', dur=FINAL_DUR)


# =====================================================================
def feel(note, v):
    if note in (SN, ESN, SS, CLAP):
        return 12 if v < 55 else 7          # snare lays back, ghosts even more
    if note in (HH, OHH, RIDE, BELL, RIDE2, COW, AGO_H, AGO_L, PHH):
        return -5                            # time-keepers push slightly ahead
    if note in (T_H, T_HM, T_LM, T_L, FT_H, FT_L):
        return 3
    return 0


def dedupe(evs, keyf):
    evs = sorted(evs, key=lambda e: (e[0], -e[2], e[1]))
    out = []
    last = {}
    for e in evs:
        k = keyf(e)
        p = last.get(k)
        if p is not None and e[0] - p[0] < GAP:
            if e[2] > p[2]:
                p[:] = e
            continue
        e = list(e)
        out.append(e)
        last[k] = e
    return out


def write():
    evs = dedupe(EV, lambda e: e[3])     # one stroke per limb at a time
    evs = dedupe(evs, lambda e: e[1])    # no doubled identical notes
    evs.sort(key=lambda e: (e[0], e[1]))
    ons = []
    for t, note, v, limb, dur in evs:
        tick = max(0, int(round(t * PPQ)) + feel(note, v))
        ons.append([tick, note, v, dur])
    ons.sort(key=lambda o: (o[0], o[1]))
    by_note = {}
    for o in ons:
        by_note.setdefault(o[1], []).append(o)
    msgs = []
    for note in sorted(by_note):
        lst = by_note[note]
        for i, (tick, n, v, dur) in enumerate(lst):
            d = dur if dur else (2 * PPQ if n in CYMBALS else PPQ // 4)
            if i + 1 < len(lst):
                d = min(d, lst[i + 1][0] - tick - 1)
            d = max(d, 5)
            msgs.append((tick, 1, n, v))
            msgs.append((tick + d, 0, n, 0))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    now = 0
    for tick, kind, n, v in msgs:
        dt = tick - now
        now = tick
        if kind:
            tr.append(mido.Message('note_on', channel=9, note=n, velocity=v, time=dt))
        else:
            tr.append(mido.Message('note_off', channel=9, note=n, velocity=0, time=dt))
    end = max(now, 60 * 4 * PPQ)
    tr.append(mido.MetaMessage('end_of_track', time=end - now))
    mid.save('solo.mid')


if __name__ == '__main__':
    write()
