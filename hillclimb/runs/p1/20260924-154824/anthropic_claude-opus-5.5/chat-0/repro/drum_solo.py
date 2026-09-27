#!/usr/bin/env python3
# drum_solo.py - generates solo.mid, a ~2 minute General MIDI drum solo (channel 10).
import math
import random
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

PPQ = 480
CH = 9                 # MIDI channel 10
TARGET_LAST = 117.5    # seconds at which the final hit lands
TAIL = 2.5             # seconds of ring after the final hit
rng = random.Random(1969)

# ---------------- GM percussion ----------------
KICK, KICK2 = 36, 35
SNARE, STICK = 38, 37
HHC, HHP, HHO = 42, 44, 46
CRASH, CRASH2, CHINA, SPLASH = 49, 57, 52, 55
RIDE, BELL = 51, 53
T1, T2, T3, T4, F1, F2 = 50, 48, 47, 45, 43, 41
TOMS = [T1, T2, T3, T4, F1, F2]
COWBELL = 56
HI_BONGO, LO_BONGO = 60, 61
MUTE_CONGA, OPEN_CONGA, LO_CONGA = 62, 63, 64
HI_TIMB, LO_TIMB = 65, 66
HI_AGOGO, LO_AGOGO = 67, 68
CLAVES, HI_WOOD, LO_WOOD = 75, 76, 77
OPEN_TRI = 81

MOTIF = [0, 3, 6, 10, 12]           # the core idea: 3+3+4+2(+4) in 16ths
MOTIF_D = [2, 5, 8, 12, 14]         # displaced by an eighth
A3 = [0, 2, 4, 7, 9]                # the motif mapped onto an 8th-triplet grid

events = []


def s(bar, p):
    return bar * 4 + p / 4.0


def h(grid, note, vel, limb, st=False, off=0.0):
    events.append({'g': grid, 'o': off, 'n': note, 'v': vel, 'l': limb, 'st': st})


def pick(path, i, n):
    if callable(path):
        return path(i)
    return path[min(len(path) - 1, int(i * len(path) / n))]


def run(start, n, sub, sticking, path, v0, v1, st=None, ghost_scale=0.45):
    """A sticking run travelling along 'path'. R/L accented, r/l softer, K/F feet."""
    if st is None:
        st = sub not in (1, 2, 4)
    for i in range(n):
        c = sticking[i % len(sticking)]
        b = start + i / float(sub)
        v = v0 + (v1 - v0) * (i / float(max(1, n - 1)))
        if c == 'K':
            h(b, KICK, v * 0.92, 'RF', st)
        elif c == 'F':
            h(b, KICK2, v * 0.9, 'LF', st)
        elif c.islower():
            h(b, pick(path, i, n), v * ghost_scale, c.upper(), st)
        else:
            h(b, pick(path, i, n), v, c, st)


def roll(start, beats, note, v0, v1, sub=8, path=None):
    """Hand-to-hand roll that swells."""
    n = int(round(beats * sub))
    for i in range(n):
        f = i / float(max(1, n - 1))
        v = v0 + (v1 - v0) * (f ** 1.3)
        limb = 'R' if i % 2 == 0 else 'L'
        if limb == 'L':
            v *= 0.94
        nt = pick(path, i, n) if path else note
        h(start + i / float(sub), nt, v, limb, True)


# ---------------- building blocks ----------------
def groove(bar, ride=False, crash=False, dens=0.3, disp=False, open_hat=False,
           fill_at=16, dyn=0):
    lim = fill_at
    for p in range(lim):
        b = s(bar, p)
        if p == 0 and crash:
            h(b, CRASH, 112 + dyn, 'R')
            continue
        if ride:
            if p % 2 == 0:
                h(b, RIDE, (86 if p % 4 == 0 else 68) + dyn, 'R')
            elif dens > 0.6 and p % 4 == 3:
                h(b, RIDE, 50 + dyn, 'R')
        else:
            if open_hat and p == 14:
                h(b, HHO, 84 + dyn, 'R')
                continue
            if open_hat and p == 15:
                continue
            v = 86 if p % 4 == 0 else (68 if p % 2 == 0 else 44)
            h(b, HHC, v + dyn, 'R')
    for p in (4, 12):
        if p < lim:
            h(s(bar, p), SNARE, 104 + dyn, 'L')
    ghosts = [7, 15, 9, 2, 13][:int(round(dens * 5))]
    for p in ghosts:
        if p < lim:
            h(s(bar, p), SNARE, 29 + (p % 3) * 3, 'L')
    kicks = list(MOTIF_D if disp else MOTIF)
    if crash and 0 not in kicks:
        kicks = [0] + kicks
    for p in kicks:
        if p < lim:
            h(s(bar, p), KICK, (98 if p == 0 else 86) + dyn, 'RF')
    if open_hat and lim == 16:
        h(s(bar + 1, 0), HHP, 70, 'LF')      # foot closes the open hat
    if ride:
        for p in (4, 12):
            if p < lim:
                h(s(bar, p), HHP, 58, 'LF')


def feet(bar, kick_pos=(0, 10), hat=(4, 12), kv=70, hv=55):
    for p in kick_pos:
        h(s(bar, p), KICK, kv, 'RF')
    for p in hat:
        h(s(bar, p), HHP, hv, 'LF')


PARA = "RLRRLRLL"


def para_bar(bar, accents, rnote, lnote, av, gv=32, first_crash=False):
    for p in range(16):
        hand = PARA[p % 8]
        if p == 0 and first_crash:
            h(s(bar, p), CRASH, 112, 'R')
            continue
        if p in accents:
            h(s(bar, p), rnote if hand == 'R' else lnote, av + (8 if p == 0 else 0), hand)
        else:
            h(s(bar, p), SNARE, gv, hand)


def wall(bar, accents, cyms, tom_path, av=114, tv=76):
    for p in range(16):
        b = s(bar, p)
        if p % 2 == 0:
            h(b, KICK, 92 if p in accents else 78, 'RF')
        else:
            h(b, KICK2, 88 if p in accents else 74, 'LF')
        if p in accents:
            h(b, cyms[accents.index(p) % len(cyms)], av, 'R')
            h(b, SNARE, av - 2, 'L')
        else:
            hand = 'R' if p % 2 == 0 else 'L'
            h(b, tom_path[p // 4], tv + (6 if p % 4 == 0 else 0), hand)


def accent_bar(bar, sub, accents, fn, av, gv, ghost=SNARE):
    st = sub not in (1, 2, 4)
    for i in range(4 * sub):
        hand = 'R' if i % 2 == 0 else 'L'
        b = bar * 4 + i / float(sub)
        if i in accents:
            h(b, fn(i, hand), av, hand, st)
        else:
            h(b, ghost, gv, hand, st)


def perc_a(bar, rh='agogo', fill=False):
    lim = 12 if fill else 16
    h(s(bar, 0), KICK, 62, 'RF')
    h(s(bar, 10), KICK, 54, 'RF')
    h(s(bar, 4), HHP, 52, 'LF')
    h(s(bar, 12), HHP, 52, 'LF')
    if rh == 'agogo':
        for p in MOTIF:
            if p < lim:
                h(s(bar, p), HI_AGOGO, 78 if p == 0 else 66, 'R')
        for p in (8, 14):
            if p < lim:
                h(s(bar, p), LO_AGOGO, 60, 'R')
    else:
        h(s(bar, 0), COWBELL, 62, 'R')
        for p in MOTIF_D:
            if p < lim:
                h(s(bar, p), CLAVES, 72, 'R')
    for p, n, v in ((1, MUTE_CONGA, 42), (5, MUTE_CONGA, 40), (7, OPEN_CONGA, 80),
                    (9, MUTE_CONGA, 42), (11, LO_CONGA, 84), (13, MUTE_CONGA, 40),
                    (15, OPEN_CONGA, 82)):
        if p < lim:
            h(s(bar, p), n, v, 'L')


def perc_b(bar, rh='wood', lim=16, dyn=0):
    h(s(bar, 0), KICK, 64 + dyn, 'RF')
    h(s(bar, 10), KICK, 56 + dyn, 'RF')
    h(s(bar, 4), HHP, 52, 'LF')
    h(s(bar, 12), HHP, 52, 'LF')
    if rh == 'wood':
        for p in (0, 2, 5, 6, 8, 11, 12, 14):
            if p < lim:
                h(s(bar, p), HI_WOOD if p in (0, 6, 12) else LO_WOOD,
                  (76 if p in (0, 6, 12) else 58) + dyn, 'R')
    else:
        for p in range(0, 16, 2):
            if p < lim:
                h(s(bar, p), COWBELL, (84 if p % 4 == 0 else 60) + dyn, 'R')
    tim = {0: LO_TIMB, 3: HI_TIMB, 6: HI_TIMB, 10: LO_TIMB, 12: LO_TIMB}
    for p, n in tim.items():
        if p < lim:
            h(s(bar, p), n, (88 if p in (0, 12) else 78) + dyn, 'L')
    if 14 < lim:
        h(s(bar, 14), HI_TIMB, 36, 'L')


def build_feet(bar, kv, eighths=False, until=16):
    step = 2 if eighths else 4
    for p in range(0, 16, step):
        if p < until:
            h(s(bar, p), KICK, kv, 'RF')
    for p in (2, 6, 10, 14):
        if p < until:
            h(s(bar, p), HHP, 54, 'LF')


def trip_groove(bar, crash=False, china=False, lim=12, dyn=0):
    for t in range(lim):
        b = bar * 4 + t / 3.0
        if t == 0 and crash:
            h(b, CRASH, 116, 'R')
        elif china and t in A3:
            h(b, CHINA, 108, 'R')
        else:
            h(b, BELL if t % 3 == 0 else RIDE, (92 if t % 3 == 0 else 66) + dyn, 'R')
        if t in A3:
            h(b, KICK, 100 if t == 0 else 90, 'RF')
    for t, v in ((3, 112), (9, 114), (5, 30), (8, 34), (11, 36)):
        if t < lim:
            h(bar * 4 + t / 3.0, SNARE, v, 'L')
    if lim == 12:
        for t in (3, 9):
            h(bar * 4 + t / 3.0, HHP, 56, 'LF')


# ================= THE SOLO =================
def compose():
    # ---- 1. Intro: the motif, alone (bars 0-3)
    for bar in range(4):
        h(s(bar, 4), HHP, 52, 'LF')
        h(s(bar, 12), HHP, 50, 'LF')
    for p in MOTIF:
        h(s(0, p), T4 if p == 12 else F1, 76 if p == 0 else 66, 'R')
    for p in MOTIF:
        h(s(1, p), T4 if p == 12 else F1, 78 if p == 0 else 68, 'R')
    for p in (2, 5, 8, 14):
        h(s(1, p), SNARE, 26, 'L')
    h(s(1, 0), KICK, 58, 'RF')
    for p, nt, hd in zip(MOTIF, [T2, T3, T4, F1, F2], "RLRLR"):
        h(s(2, p), nt, 80 if p == 0 else 72, hd)
    for p in (1, 8, 14):
        h(s(2, p), SNARE, 28, 'L')
    h(s(2, 0), KICK, 64, 'RF')
    h(s(2, 10), KICK, 60, 'RF')
    for p, v in ((0, 84), (3, 74), (6, 78)):
        h(s(3, p), F1, v, 'R')
    h(s(3, 0), KICK, 72, 'RF')
    for p in (2, 5):
        h(s(3, p), SNARE, 28, 'L')
    run(s(3, 8), 8, 4, "RLKRLKRL", [SNARE, T1, T1, T2, T3, T4, F1, F1], 62, 98)

    # ---- 2. Groove: motif moves to the feet (bars 4-11)
    groove(4, crash=True, dens=0.2)
    groove(5, dens=0.4)
    groove(6, dens=0.6, open_hat=True)
    groove(7, dens=0.6, fill_at=8)
    run(s(7, 8), 8, 4, "RLKRLKRL", [T1, T1, T2, T3, T3, T4, F1, F1], 72, 104)
    groove(8, ride=True, crash=True, dens=0.6, disp=True)
    groove(9, ride=True, dens=0.8, disp=True)
    groove(10, ride=True, dens=0.8, disp=True, fill_at=12)
    run(s(10, 12), 8, 8, "RLRLRLRL", [SNARE, SNARE, SNARE, SNARE, T1, T2, T3, T4], 66, 100)
    groove(11, ride=True, dens=0.6, fill_at=4)
    run(s(11, 4), 18, 6, "RLRLKF", [T1, T2, T3, T4, F1, F2], 70, 114)

    # ---- 3. Hands travel the kit (bars 12-19)
    para_bar(12, MOTIF, F1, T1, 90, first_crash=True)
    feet(12, kv=86)
    para_bar(13, MOTIF_D, T4, T2, 94)
    feet(13, kv=74)
    run(s(14, 0), 16, 4, "RrLl", [SNARE, T1, T2, T3], 72, 88, ghost_scale=0.75)
    feet(14, kv=74)
    run(s(15, 0), 12, 4, "RrLl", [T4, F1, F2], 86, 96, ghost_scale=0.78)
    run(s(15, 12), 8, 8, "RrLl", [SNARE, SNARE, T1, T1, T2, T2, T3, T3], 90, 108,
        ghost_scale=0.8)
    feet(15, kv=78)
    for i in range(24):                       # 4 against 6
        hand = 'R' if i % 2 == 0 else 'L'
        b = s(16, 0) + i / 6.0
        if i == 0:
            h(b, CRASH, 110, 'R', True)
        elif i % 4 == 0:
            h(b, TOMS[(i // 4) % 6], 94 + i * 0.5, hand, True)
        else:
            h(b, SNARE, 34, hand, True)
    feet(16, kick_pos=(0, 8), kv=88)
    for i in range(24):                       # 3 against 6, descending
        hand = 'R' if i % 2 == 0 else 'L'
        b = s(17, 0) + i / 6.0
        if i % 3 == 0:
            h(b, TOMS[min(5, i * 6 // 24)], 92 + i * 0.7, hand, True)
        else:
            h(b, SNARE, 36, hand, True)
    feet(17, kick_pos=(0, 8), kv=84)
    for p, nt in zip(MOTIF, [T2, T3, T4, F1, F2]):   # motif as flams
        h(s(18, p), nt, 50, 'L', off=-0.04)
        h(s(18, p), nt, 108, 'R')
        h(s(18, p), KICK, 100, 'RF')
    for p in range(16):
        if p in MOTIF:
            continue
        h(s(18, p), SNARE, 30, 'R' if p % 2 == 0 else 'L')
    for p in (4, 12):
        h(s(18, p), HHP, 56, 'LF')
    roll(s(19, 0), 3, SNARE, 32, 104)
    for k, p in enumerate((0, 4, 8)):
        h(s(19, p), KICK, 70 + k * 10, 'RF')
    run(s(19, 12), 6, 6, "RLRLRL", [T1, T2, T3, T4, F1, F2], 104, 118)

    # ---- 4. First peak (bars 20-23)
    wall(20, MOTIF, [CRASH, CHINA], [T1, T2, T3, F1])
    wall(21, MOTIF_D, [CHINA, CRASH2], [T2, T3, T4, F2])
    wall(22, [0, 3, 6, 10, 12, 14, 15], [CRASH, CHINA, CRASH2], [T1, T3, T4, F1], tv=82)
    for p, c in ((0, CRASH), (3, CRASH2), (6, CHINA)):
        h(s(23, p), c, 120, 'R')
        h(s(23, p), SNARE, 118, 'L')
        h(s(23, p), KICK, 112, 'RF')
    h(s(23, 10), CRASH, 124, 'R')
    h(s(23, 10), CRASH2, 120, 'L')
    h(s(23, 10), KICK, 118, 'RF')
    # ...silence...

    # ---- 5. Release: hand percussion, laid back and swung (bars 24-31)
    h(s(24, 0), OPEN_TRI, 70, 'L')
    perc_a(24, 'agogo')
    perc_a(25, 'agogo')
    perc_a(26, 'claves')
    perc_a(27, 'agogo', fill=True)
    run(s(27, 12), 4, 4, "RLRL", [HI_BONGO, HI_BONGO, LO_BONGO, LO_BONGO], 60, 82)
    perc_b(28, 'wood')
    perc_b(29, 'wood', dyn=3)
    perc_b(30, 'bell', dyn=6)
    perc_b(31, 'bell', lim=4, dyn=8)
    run(s(31, 4), 8, 4, "RLRL", [HI_TIMB, HI_TIMB, LO_TIMB, LO_TIMB], 58, 80)
    roll(s(31, 12), 1, HI_TIMB, 62, 100)

    # ---- 6. The build (bars 32-39)
    accent_bar(32, 4, MOTIF, lambda i, hd: SPLASH if i == 0 else SNARE, 84, 28)
    build_feet(32, 58)
    accent_bar(33, 4, MOTIF, lambda i, hd: SNARE, 90, 30)
    build_feet(33, 64)
    accent_bar(34, 4, MOTIF,
               lambda i, hd: (T1 if i < 8 else F1) if hd == 'R' else T2, 96, 30)
    build_feet(34, 70)
    accent_bar(35, 4, MOTIF_D,
               lambda i, hd: (T3 if i < 8 else F1) if hd == 'R' else T2, 100, 32)
    build_feet(35, 76)
    accent_bar(36, 6, list(range(0, 24, 3)), lambda i, hd: TOMS[(i // 3) % 4], 100, 34)
    build_feet(36, 82)
    accent_bar(37, 6, list(range(0, 24, 3)), lambda i, hd: TOMS[min(5, i // 4)], 108, 36)
    build_feet(37, 88)
    roll(s(38, 0), 6, SNARE, 40, 116)
    build_feet(38, 92, eighths=True)
    build_feet(39, 100, eighths=True, until=8)
    run(s(39, 8), 12, 6, "RLRLKF", [T1, T2, T3, T4, F1, F2], 98, 120)

    # ---- 7. Second peak: motif in triplets, then in 32nds (bars 40-47)
    trip_groove(40, crash=True)
    trip_groove(41, dyn=2)
    trip_groove(42, china=True, dyn=4)
    trip_groove(43, lim=6, dyn=4)
    run(s(43, 8), 12, 6, "RLKRLK", [T1, T2, T3, T4, F1, F2], 96, 118)
    tomseq = [T1, T2, T3, T4, F1, T2, T3, T4, F1, F2]
    acc = sorted(set(MOTIF) | {p + 16 for p in MOTIF})
    for i in range(32):
        hand = 'R' if i % 2 == 0 else 'L'
        b = s(44, 0) + i / 8.0
        if i in acc:
            k = acc.index(i)
            nt = CRASH if i == 0 else (CHINA if i == 16 else tomseq[k])
            h(b, nt, 112, hand, True)
            h(b, KICK, 100, 'RF', True)
        else:
            h(b, SNARE, 38, hand, True)
    wall(45, MOTIF, [CRASH, CHINA], [T1, T2, T4, F1], av=118, tv=84)
    zig = [T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1, SNARE]
    run(s(46, 0), 24, 6, "RLRLKF",
        lambda i: CRASH if i == 0 else zig[i * 12 // 24], 96, 116)
    for p, c in ((0, CRASH), (3, CRASH2), (6, CHINA)):
        h(s(47, p), c, 120, 'R')
        h(s(47, p), SNARE, 118, 'L')
        h(s(47, p), KICK, 112, 'RF')
    roll(s(47, 8), 2, SNARE, 64, 122)
    for p in range(8, 16):
        h(s(47, p), KICK if p % 2 == 0 else KICK2, 70 + (p - 8) * 5,
          'RF' if p % 2 == 0 else 'LF')

    # ---- 8. Statement, callback, farewell (bars 48-52)
    for p, c in zip(MOTIF, [CRASH, CRASH2, CHINA, CRASH2, CRASH]):
        h(s(48, p), c, 122, 'R')
        h(s(48, p), SNARE, 120, 'L')
        h(s(48, p), KICK, 118, 'RF')
    for p in MOTIF:
        h(s(49, p), T4 if p == 12 else F1, 74 if p == 0 else 64, 'R')
    for p in (2, 5, 8, 14):
        h(s(49, p), SNARE, 26, 'L')
    feet(49, kick_pos=(0,), kv=60, hv=50)
    for p in (0, 3, 6, 10):
        h(s(50, p), F1, 72 if p == 0 else 64, 'R')
    for p in (2, 5, 8):
        h(s(50, p), SNARE, 26, 'L')
    run(s(50, 12), 4, 4, "RLRL", [T2, T3, T4, F1], 62, 80)
    feet(50, kick_pos=(0,), kv=62, hv=50)
    roll(s(51, 0), 3, SNARE, 30, 112)
    h(s(51, 8), KICK, 80, 'RF')
    h(s(51, 10), KICK, 90, 'RF')
    run(s(51, 12), 6, 6, "RLRLRL", [T1, T2, T3, T4, F1, F2], 108, 122)
    h(s(52, 0), CRASH, 127, 'R')
    h(s(52, 0), CRASH2, 124, 'L')
    h(s(52, 0), KICK, 127, 'RF')
    h(s(52, 0), KICK2, 120, 'LF')


FINAL_BEAT = 208  # bar 52, beat 1

# tempo shape (bar, multiplier of base tempo)
TEMPO_KEYS = [(0, 0.95), (4, 0.97), (8, 0.99), (12, 1.0), (16, 1.02), (19, 1.04),
              (20, 1.06), (23, 1.08), (23.75, 1.08), (24, 0.94), (31, 0.95),
              (32, 0.95), (38, 1.03), (40, 1.07), (47, 1.10), (47.75, 1.10),
              (48, 1.06), (49, 0.99), (50.5, 0.95), (52, 0.85)]
# feel (bar, swing fraction of a 16th, lean ms: + = ahead of the beat)
FEEL_KEYS = [(0, .08, -5), (4, .12, -3), (12, .06, 0), (19, .04, 4), (20, 0.0, 6),
             (23.9, 0.0, 6), (24, .22, -7), (31.9, .20, -6), (32, .10, -3),
             (39, .04, 6), (40, .03, 7), (48, .06, 2), (49, .08, -5), (52, .05, -6)]


def interp(keys, x):
    if x <= keys[0][0]:
        return tuple(keys[0][1:])
    for k0, k1 in zip(keys, keys[1:]):
        x0, x1 = k0[0], k1[0]
        if x0 <= x <= x1:
            f = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
            return tuple(a + (b - a) * f for a, b in zip(k0[1:], k1[1:]))
    return tuple(keys[-1][1:])


def mult(beat_index):
    return interp(TEMPO_KEYS, beat_index / 4.0)[0]


def note_offset(e):
    n, v = e['n'], e['v']
    if n in (KICK, KICK2):
        return -3.0
    if n == HHP:
        return 1.0
    if n in (CRASH, CRASH2, CHINA, SPLASH):
        return -1.0
    if v < 45:
        return 3.0
    if n == SNARE and v >= 95:
        return 5.0
    return 0.0


def main():
    compose()
    S = sum(1.0 / mult(i) for i in range(FINAL_BEAT))
    base = 60.0 * S / TARGET_LAST

    def bpm_at(beat):
        return base * mult(int(math.floor(max(0.0, beat))))

    # --- humanize with a consistent feel
    for e in events:
        grid = e['g']
        b = grid + e['o']
        sw, lean = interp(FEEL_KEYS, grid / 4.0)
        frac = grid - math.floor(grid)
        if not e['st'] and (abs(frac - 0.25) < 1e-6 or abs(frac - 0.75) < 1e-6):
            b += sw * 0.25
        jit = max(-4.0, min(4.0, rng.gauss(0, 1.5)))
        ms = note_offset(e) - lean + jit
        tick = b * PPQ + ms / 1000.0 * bpm_at(b) / 60.0 * PPQ
        e['t'] = max(0, int(round(tick)))
        v = e['v'] + rng.gauss(0, 1.5 if e['v'] < 50 else 2.5)
        e['vel'] = max(1, min(127, int(round(v))))

    # --- playability: one stroke per limb at a time, >= 40 ms apart
    by_limb = {}
    for e in events:
        by_limb.setdefault(e['l'], []).append(e)
    keep = []
    for limb in sorted(by_limb):
        lst = sorted(by_limb[limb], key=lambda e: (e['t'], -e['vel'], e['n']))
        kept = []
        for e in lst:
            if kept:
                p = kept[-1]
                gap_ms = (e['t'] - p['t']) / PPQ * 60.0 / bpm_at(e['t'] / PPQ) * 1000.0
                if gap_ms < 40.0:
                    if e['vel'] > p['vel']:
                        kept[-1] = e
                    continue
            kept.append(e)
        keep.extend(kept)

    LIMB_ORDER = {'RF': 0, 'LF': 1, 'R': 2, 'L': 3}
    keep.sort(key=lambda e: (e['t'], LIMB_ORDER[e['l']], e['n']))
    # remove same note on same tick (keep loudest)
    dedup = {}
    for e in keep:
        k = (e['t'], e['n'])
        if k not in dedup or e['vel'] > dedup[k]['vel']:
            dedup[k] = e
    keep = sorted(dedup.values(), key=lambda e: (e['t'], LIMB_ORDER[e['l']], e['n']))

    DUR = 36
    nxt_limb, nxt_note = {}, {}
    for e in reversed(keep):
        d = DUR
        if e['l'] in nxt_limb:
            d = min(d, nxt_limb[e['l']] - e['t'] - 2)
        if e['n'] in nxt_note:
            d = min(d, nxt_note[e['n']] - e['t'] - 1)
        e['d'] = max(1, d)
        nxt_limb[e['l']] = e['t']
        nxt_note[e['n']] = e['t']

    end_tick = FINAL_BEAT * PPQ + int(round(TAIL * bpm_at(FINAL_BEAT) / 60.0 * PPQ))
    end_tick = max(end_tick, max(e['t'] + e['d'] for e in keep) + 1)

    msgs = []
    seq = 0

    def add(tick, order, msg):
        nonlocal seq
        msgs.append((tick, order, seq, msg))
        seq += 1

    add(0, -3, MetaMessage('track_name', name='Drum Solo', time=0))
    add(0, -3, MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    add(0, -2, Message('program_change', channel=CH, program=0, time=0))
    add(0, -2, Message('control_change', channel=CH, control=7, value=112, time=0))
    add(0, -2, Message('control_change', channel=CH, control=10, value=64, time=0))
    add(0, -2, Message('control_change', channel=CH, control=91, value=40, time=0))
    last = None
    i = 0
    while i * PPQ < end_tick:
        tempo = int(round(60000000.0 / (base * mult(i))))
        if tempo != last:
            add(i * PPQ, -1, MetaMessage('set_tempo', tempo=tempo, time=0))
            last = tempo
        i += 1
    for e in keep:
        add(e['t'], 1, Message('note_on', channel=CH, note=e['n'], velocity=e['vel'], time=0))
        add(e['t'] + e['d'], 0, Message('note_off', channel=CH, note=e['n'], velocity=0, time=0))

    msgs.sort(key=lambda m: (m[0], m[1], m[2]))
    mid = MidiFile(type=0, ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)
    now = 0
    for tick, _, _, msg in msgs:
        track.append(msg.copy(time=tick - now))
        now = tick
    track.append(MetaMessage('end_of_track', time=max(0, end_tick - now)))
    mid.save('solo.mid')


if __name__ == '__main__':
    main()
