#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

The solo is built on two motifs:
  Motif A - a 3-3-3-3-2-2 sixteenth-note accent figure that travels around the kit.
  Motif B - a six-stroke-roll cell (R l l r r L) in sixteenth-note triplets.

Each stroke is assigned to one limb (R, L, RF, LF), so at most two hands and
two feet strike at any instant.  After the notes are generated, the timing is
humanized.  The tempo map breathes, fills rush and the final bars broaden into
the last hit.  The random generator is seeded, so every run writes the same file.
"""
import math
import random
import mido

PPQ = 960
rng = random.Random(1964)

# ---------------- General MIDI percussion ----------------
KICK, KICK2 = 36, 35
SNARE, RIM = 38, 37
FT_LO, FT_HI, T_LO, T_LM, T_HM, T_HI = 41, 43, 45, 47, 48, 50
HH_C, HH_P, HH_O = 42, 44, 46
CRASH, CRASH2, RIDE, BELL, CHINA, SPLASH = 49, 57, 51, 53, 52, 55
COWBELL, WB_HI, WB_LO, CLAVES, TRI_O = 56, 76, 77, 75, 81

KIT = [SNARE, T_HI, T_HM, T_LM, T_LO, FT_HI, FT_LO]

notes = []      # [pos_beats, pitch, vel, limb, dt_ms, dur_beats, alive]
bumps = []      # tempo surges (start_beat, end_beat, amount)


def hit(pos, pitch, vel, limb, dt=0.0, dur=None):
    v = int(round(max(1, min(127, vel))))
    notes.append([float(pos), int(pitch), v, limb, float(dt), dur, True])


def other(h):
    return 'L' if h == 'R' else 'R'


def B(bar, beat=0.0):
    return bar * 4.0 + beat


def jit(a=4.0):
    return rng.uniform(-a, a)


def surge(b0, b1, amt):
    bumps.append((b0, b1, amt))


def flam(pos, pitch, vel, hand, ratio=0.42):
    hit(pos, pitch, vel, hand)
    hit(pos, pitch, vel * ratio, other(hand), dt=-24)


def land(pos, vel=118, cym=CRASH, hand='R', kick=True):
    hit(pos, cym, vel + jit(3), hand)
    if kick:
        hit(pos, KICK, vel - 6 + jit(3), 'RF')


def walk(n, start=1, bias=1, groups=(1, 2, 2, 3), lo=0, hi=6):
    """Random walk around the kit, staying on each drum for a small group of strokes."""
    out = []
    idx = start
    while len(out) < n:
        g = rng.choice(groups)
        out.extend([KIT[idx]] * g)
        step = bias * rng.choice((1, 1, 1, 2))
        if rng.random() < 0.12:
            step = -step
        nxt = idx + step
        if nxt > hi or nxt < lo:
            bias = -bias
            nxt = idx + bias
        idx = max(lo, min(hi, nxt))
    return out[:n]


def run(start, n, grid, sticking, voice, vel, rush=0.0):
    """Sticking letters: R/L = hands, K = right-foot kick, F = left-foot kick, H = hat pedal."""
    for i in range(n):
        s = sticking[i % len(sticking)]
        pos = start + i * grid
        dt = -rush * (i / max(1, n - 1))
        v = vel(i)
        if s in 'RL':
            p = voice(i, s)
            if p is not None:
                hit(pos, p, v, s, dt)
        elif s == 'K':
            hit(pos, KICK, v, 'RF', dt)
        elif s == 'F':
            hit(pos, KICK, v, 'LF', dt)
        elif s == 'H':
            hit(pos, HH_P, v * 0.7, 'LF', dt)


# ---------------- Motifs ----------------
A_STEPS = [0, 3, 6, 9, 12, 14]


def motif_a(bar, voices, base=100, cresc=0, density=0.0, ghost_voice=SNARE, shift=0,
            kick_under=(), crash_on=(), ghost_vel=32, flams=(), start_step=0,
            end_step=16, rush=0.0):
    start = B(bar)
    acc = {}
    for i, s in enumerate(A_STEPS):
        t = s + shift
        if 0 <= t < 16:
            acc[t] = i
    for step in range(start_step, end_step):
        pos = start + step * 0.25
        hand = 'R' if step % 2 == 0 else 'L'
        dt = -rush * step / 15.0
        if step in acc:
            i = acc[step]
            v = base + cresc * step / 15.0 + jit(4)
            p = voices[i]
            if i in crash_on:
                p = CRASH if hand == 'R' else CRASH2
            if i in flams:
                hit(pos, p, v * 0.42, other(hand), dt=dt - 24)
            hit(pos, p, v, hand, dt)
            if i in kick_under:
                hit(pos, KICK, v - 6, 'RF', dt)
        elif density > 0 and rng.random() < density:
            v = ghost_vel + cresc * step / 15.0 * 0.4 + jit(6)
            gv = ghost_voice(step) if callable(ghost_voice) else ghost_voice
            hit(pos, gv, v, hand, dt)


def motif_b(pos, acc1, acc2, base=104, lead='R', tap=SNARE, grid=1.0 / 6, rush=0.0,
            kick=True, crash_first=False, tapboost=0, kick2=False):
    o = other(lead)
    st = [lead, o, o, lead, lead, o]
    vels = [base + 8, 40 + tapboost, 46 + tapboost, 52 + tapboost, 58 + tapboost, base]
    for i in range(6):
        p = acc1 if i == 0 else (acc2 if i == 5 else tap)
        if i == 0 and crash_first:
            p = CRASH if lead == 'R' else CRASH2
        hit(pos + i * grid, p, vels[i] + jit(3), st[i], dt=-rush * i / 5.0)
    if kick:
        hit(pos, KICK, base, 'RF')
    if kick2:
        hit(pos + 5 * grid, KICK, base - 8, 'LF')


# ---------------- Building blocks ----------------
KICK_PATS = [[0, 10], [0, 7, 10], [0, 3, 10, 13], [0, 6, 10], [0, 8, 11],
             [0, 2, 10, 14], [0, 7, 9, 14], [0, 6, 8, 11]]


def groove(bar, until=16, cym='hat', ghost=0.3, base=90, kick=None, open_at=(),
           bell_at=(), snare_acc=(), crash_down=False):
    start = B(bar)
    kp = list(kick if kick is not None else rng.choice(KICK_PATS))
    if rng.random() < 0.5:
        kp.append(rng.choice([2, 5, 7, 11, 13, 15]))
    for step in range(until):
        pos = start + step * 0.25
        sub = step % 4
        if sub % 2 == 0:
            if step == 0 and crash_down:
                hit(pos, CRASH, 116 + jit(4), 'R')
            elif cym == 'ride':
                p = BELL if step in bell_at else RIDE
                v = (base - 4 if sub == 0 else base - 16) + (16 if step in bell_at else 0)
                hit(pos, p, v + jit(4), 'R')
            else:
                if step in open_at:
                    hit(pos, HH_O, base + 6 + jit(3), 'R')
                    hit(pos + 0.5, HH_P, 60 + jit(4), 'LF')
                else:
                    hit(pos, HH_C, (base - 6 if sub == 0 else base - 20) + jit(5), 'R')
        if step in (4, 12):
            hit(pos, SNARE, base + 22 + jit(3), 'L')
        elif step in snare_acc:
            hit(pos, SNARE, base + 14 + jit(4), 'L')
        elif sub != 0 and rng.random() < ghost:
            hit(pos, SNARE, 26 + rng.uniform(0, 14), 'L')
        if step in kp:
            hit(pos, KICK, base + 8 + (8 if step == 0 else 0) + jit(4), 'RF')
        if cym == 'ride' and step in (4, 12):
            hit(pos, HH_P, 62 + jit(4), 'LF')


def fill_singles(start, beats, v0, v1, grid=0.25, startidx=1, accent_every=4, rush=5.0, kicks=()):
    n = int(round(beats / grid))
    path = walk(n, start=startidx)

    def vel(i):
        x = i / max(1, n - 1)
        v = v0 + (v1 - v0) * x
        if accent_every and i % accent_every == 0:
            v += 10
        return v + jit(3)

    run(start, n, grid, 'RL', lambda i, h: path[i], vel, rush)
    for k in kicks:
        hit(start + k, KICK, v1 - 8, 'RF')


def fill_flams(start, beats, v0, v1, walkstart=1):
    n = int(round(beats * 3))
    path = walk(n, start=walkstart, groups=(3,))
    for i in range(n):
        pos = start + i / 3.0
        g = i // 3
        lead = 'R' if g % 2 == 0 else 'L'
        x = i / max(1, n - 1)
        v = v0 + (v1 - v0) * x
        j = i % 3
        if j == 0:
            flam(pos, path[i], v + 8, lead)
            hit(pos, KICK, v - 4, 'RF')
        elif j == 1:
            hit(pos, SNARE, v - 40 + jit(4), other(lead))
        else:
            hit(pos, SNARE, v - 32 + jit(4), lead)


def fill_sextuplets(start, beats, v0, v1, rush=6.0, crash_idx=()):
    n = int(round(beats * 6))
    path = walk(n, start=1, groups=(2, 4))
    for i in range(n):
        pos = start + i / 6.0
        c = 'RLRLKF'[i % 6]
        x = i / max(1, n - 1)
        v = v0 + (v1 - v0) * x + jit(3)
        dt = -rush * x
        if c in 'RL':
            p = path[i]
            if i % 6 == 0:
                v += 10
            if i in crash_idx:
                p = CRASH
            hit(pos, p, v, c, dt)
        else:
            hit(pos, KICK, v - 4, 'RF' if c == 'K' else 'LF', dt)


def fill_doubles(start, beats, v0, v1, rush=6.0, walkstart=0):
    n = int(round(beats * 8))
    path = walk(n, start=walkstart, groups=(4,))
    for i in range(n):
        h = 'RRLL'[i % 4]
        x = i / max(1, n - 1)
        v = v0 + (v1 - v0) * x - (7 if i % 2 else 0) + jit(3)
        hit(start + i / 8.0, path[i], v, h, dt=-rush * x)


def dkicks(bar, s0=0, s1=16, base=88):
    for step in range(s0, s1):
        foot = 'RF' if step % 2 == 0 else 'LF'
        v = base + (12 if step % 4 == 0 else 0) + jit(5)
        hit(B(bar, step * 0.25), KICK, v, foot)


CELLS = ['RLKL', 'RKLR', 'LKRL', 'RLLK', 'KRLR', 'RKRL', 'LRKL', 'RLRK', 'KLRL', 'RKLL']


def linear_bar(bar, rvoice='hat', beats=4, boost=0):
    prev = None
    hit(B(bar), KICK, 106 + jit(3), 'RF')
    lastk, lastfoot = 0, 'RF'
    for beat in range(beats):
        cell = rng.choice([c for c in CELLS if c != prev])
        prev = cell
        for j, c in enumerate(cell):
            step = beat * 4 + j
            pos = B(bar, step * 0.25)
            acc = step in A_STEPS
            if c == 'R':
                if rvoice == 'cow':
                    p, v = COWBELL, (98 if acc else 60)
                else:
                    p = HH_O if (acc and step in (6, 14)) else HH_C
                    v = 104 if acc else 64
                hit(pos, p, v + boost + jit(4), 'R')
                if p == HH_O:
                    hit(pos + 0.5, HH_P, 60, 'LF')
            elif c == 'L':
                hit(pos, SNARE, (112 + boost) if acc else 32 + rng.uniform(0, 12), 'L')
            else:
                if step == 0:
                    continue
                foot = 'LF' if (step - lastk == 1 and lastfoot == 'RF') else 'RF'
                hit(pos, KICK, (110 if acc else 86) + boost + jit(4), foot)
                lastk, lastfoot = step, foot


# ---------------- Sections ----------------
def intro():                                    # bars 0-3
    surge(B(0), B(2), -0.012)
    motif_a(0, [SNARE, T_HI, T_LM, FT_LO, SNARE, FT_HI], base=94, cresc=12,
            kick_under=(0, 5), flams=(0,))
    # answer: the hat foot keeps time while the tail of the motif echoes
    for b in range(4):
        hit(B(1, b), HH_P, 55 + jit(4), 'LF')
    hit(B(1, 1.0), RIM, 72, 'L')
    hit(B(1, 1.75), SNARE, 34, 'L')
    hit(B(1, 2.0), T_HM, 82, 'R')
    hit(B(1, 2.5), T_LO, 88, 'L')
    hit(B(1, 3.0), SNARE, 92, 'R')
    hit(B(1, 3.5), FT_HI, 100, 'R')
    hit(B(1, 3.5), KICK, 92, 'RF')
    # restatement with a few ghost notes
    motif_a(2, [SNARE, T_HM, T_LO, FT_LO, T_HI, FT_HI], base=100, cresc=14, density=0.35,
            kick_under=(0, 3, 5))
    for b in range(4):
        hit(B(2, b), HH_P, 56 + jit(4), 'LF')
    # head of the motif, then a fill into the groove
    motif_a(3, [SNARE, T_HI, T_LM, FT_LO, SNARE, FT_HI], base=104, cresc=6, density=0.5,
            end_step=8, kick_under=(0,))
    fill_singles(B(3, 2), 2.0, 72, 116, startidx=1, rush=7, kicks=(0, 1))
    surge(B(3), B(4, 1), 0.022)


def groove_sec():                               # bars 4-11
    groove(4, crash_down=True, base=90, kick=[0, 6, 10], ghost=0.25)
    groove(5, until=12, base=92, ghost=0.3)
    fill_singles(B(5, 3), 1.0, 80, 108, startidx=1, rush=4)
    surge(B(5, 2.5), B(6, 0.5), 0.012)
    groove(6, base=92, ghost=0.3, snare_acc=(3, 9), open_at=(6,), kick=[0, 12, 14])
    groove(7, until=8, base=94, ghost=0.35)
    path = walk(8, start=1)
    run(B(7, 2), 8, 0.25, 'RL', lambda i, h: path[i],
        lambda i: (110 if i % 3 == 0 else 70) + i * 2 + jit(3), rush=5)
    hit(B(7, 2), KICK, 96, 'RF')
    hit(B(7, 3.5), KICK, 100, 'RF')
    groove(8, cym='ride', crash_down=True, base=92, ghost=0.3)
    groove(9, cym='ride', until=12, base=94, ghost=0.35)
    flam(B(9, 3), SNARE, 108, 'R')
    run(B(9, 3.25), 3, 0.25, 'LRL', lambda i, h: [T_HI, T_LM, FT_LO][i],
        lambda i: 96 + i * 6 + jit(3), rush=3)
    hit(B(9, 3.5), KICK, 98, 'RF')
    groove(10, cym='ride', bell_at=(0, 6, 12), snare_acc=(3, 9), base=96, ghost=0.35)
    motif_a(11, [SNARE, T_HI, T_LM, FT_LO, T_HM, FT_HI], base=104, cresc=16, density=0.9,
            ghost_vel=45, kick_under=(0, 3, 5), rush=8)
    surge(B(11), B(12, 1), 0.02)


def development():                              # bars 12-19
    motif_a(12, [SNARE, T_HI, T_LM, FT_LO, SNARE, FT_HI], base=104, cresc=10, density=0.85,
            ghost_vel=38, kick_under=(0, 3, 5), crash_on=(0,))
    for b in range(4):
        hit(B(12, b), HH_P, 58 + jit(4), 'LF')
    # 13: travelling singles with 3-3-2 accents over the kick
    path = walk(16, start=0)
    acc = {0, 3, 6, 8, 11, 14}
    run(B(13), 16, 0.25, 'RL',
        lambda i, h: path[i] if (i in acc or h == 'R') else SNARE,
        lambda i: (108 if i in acc else 48 + i * 1.5) + jit(4), rush=3)
    for i in sorted(acc):
        hit(B(13, i * 0.25), KICK, 96 + jit(4), 'RF')
    # 14: motif displaced by an eighth note
    hit(B(14), KICK, 100, 'RF')
    motif_a(14, [T_HI, T_HM, FT_HI, SNARE, T_LO, FT_LO], base=102, cresc=8, density=0.4,
            shift=2, kick_under=(1, 4))
    for s in (2, 6, 10, 14):
        hit(B(14, s * 0.25), HH_P, 56 + jit(4), 'LF')
    # 15: double-stroke swell, then down the toms
    run(B(15), 16, 1 / 8.0, 'RRLL', lambda i, h: SNARE,
        lambda i: 40 + 60 * i / 15.0 - (6 if i % 2 else 0) + jit(3))
    hit(B(15), KICK, 70, 'RF')
    fill_singles(B(15, 2), 2.0, 84, 118, startidx=1, rush=7, kicks=(0, 1))
    surge(B(15, 1), B(16, 1), 0.02)
    # 16: paradiddles orchestrated, four-limb coordination
    st = 'RLRRLRLL'
    for step in range(16):
        h = st[step % 8]
        pos = B(16, step * 0.25)
        if step % 4 == 0:
            if step == 0:
                p = CRASH
            else:
                p = rng.choice([FT_LO, FT_HI]) if h == 'R' else rng.choice([T_HI, T_HM, SNARE])
            v = 108
            hit(pos, KICK, 92 + jit(4), 'RF')
        else:
            p = RIDE if h == 'R' else SNARE
            v = 62 if h == 'R' else 34
        hit(pos, p, v + jit(4), h)
        if step % 4 == 2:
            hit(pos, HH_P, 60 + jit(4), 'LF')
    # 17-18: motif A augmented over two bars with tom chatter between
    acc_steps = {0: CRASH, 6: FT_LO, 12: T_HI, 18: CRASH, 24: SNARE, 28: FT_HI}
    path = walk(32, start=2)
    for step in range(32):
        pos = B(17) + step * 0.25
        h = 'R' if step % 2 == 0 else 'L'
        if step in acc_steps:
            p = acc_steps[step]
            v = 112 + jit(4)
            if p == SNARE:
                flam(pos, p, v, h)
            else:
                hit(pos, p, v, h)
            hit(pos, KICK, 100 + jit(3), 'RF')
        else:
            hit(pos, path[step], 52 + step * 0.8 + jit(6), h)
        if step % 4 == 0:
            hit(pos, HH_P, 58 + jit(4), 'LF')
    # 19: diminuendo run into space
    path = walk(18, start=0, groups=(2, 3))
    run(B(19), 18, 1 / 6.0, 'RL', lambda i, h: path[i],
        lambda i: 104 - 68 * i / 17.0 + (8 if i % 6 == 0 else 0) + jit(3))
    hit(B(19), KICK, 100, 'RF')
    hit(B(19, 1.5), KICK, 70, 'RF')
    hit(B(19, 3.0), SNARE, 28, 'L')
    hit(B(19, 3.5), SNARE, 24, 'R')
    surge(B(19, 2), B(22), -0.02)


def quiet():                                    # bars 20-25
    # 20: triangle, ride, whispered motif on the cross-stick
    hit(B(20), TRI_O, 76, 'L')
    hit(B(20), KICK, 70, 'RF')
    for s in (0, 4, 7, 8, 12, 15):
        hit(B(20, s * 0.25), RIDE, (62 if s % 4 == 0 else 50) + jit(3), 'R')
    for s in (3, 6, 9, 12, 14):
        hit(B(20, s * 0.25), RIM, 60 + s + jit(3), 'L')
    for b in range(1, 4):
        hit(B(20, b), KICK, 32 + jit(3), 'RF')
    for b in (1, 3):
        hit(B(20, b), HH_P, 58, 'LF')
    # 21: the motif on woodblocks and cowbell
    motif_a(21, [RIM, WB_HI, WB_LO, WB_HI, COWBELL, WB_LO], base=72, cresc=6, density=0.3,
            ghost_vel=24)
    for b in range(4):
        hit(B(21, b), HH_P, 54 + jit(3), 'LF')
    hit(B(21), KICK, 48, 'RF')
    hit(B(21, 2), KICK, 44, 'RF')
    # 22: ghost chatter under the ride, a fragment answered on the toms
    for s in (0, 4, 7, 8, 12, 15):
        hit(B(22, s * 0.25), RIDE, 56 + jit(3), 'R')
    for s in range(1, 16, 2):
        if rng.random() < 0.55 and s not in (11,):
            hit(B(22, s * 0.25), SNARE, 22 + rng.uniform(0, 12), 'L')
    hit(B(22, 2.0), T_HM, 64, 'R')
    hit(B(22, 2.75), T_LO, 68, 'L')
    hit(B(22, 3.5), FT_LO, 72, 'R')
    hit(B(22), KICK, 42, 'RF')
    hit(B(22, 2), KICK, 40, 'RF')
    for b in (1, 3):
        hit(B(22, b), HH_P, 56, 'LF')
    # 23: brush-like sixteenths with the motif whispered as accents
    for s in range(16):
        h = 'R' if s % 2 == 0 else 'L'
        v = (54 + s) if s in A_STEPS else 22 + s * 0.6 + rng.uniform(0, 12)
        hit(B(23, s * 0.25), SNARE, v, h)
    hit(B(23), KICK, 46, 'RF')
    hit(B(23, 2.5), KICK, 50, 'RF')
    for b in range(4):
        hit(B(23, b), HH_P, 52, 'LF')
    # 24-25: floor-tom roll that swells and resolves
    n = 48
    sweep = [T_HI, T_HM, T_LM, T_LO, FT_HI, FT_LO]
    for i in range(n):
        pos = B(24) + i / 6.0
        h = 'R' if i % 2 == 0 else 'L'
        x = i / (n - 1.0)
        v = 28 + 88 * x ** 1.6 + (6 if i % 6 == 0 else 0) + jit(3)
        p = sweep[i - 42] if i >= 42 else (FT_LO if h == 'R' else FT_HI)
        hit(pos, p, v, h, dt=-6 * x)
    hit(B(24), KICK, 45, 'RF')
    hit(B(24, 2), KICK, 55, 'RF')
    for b in range(4):
        hit(B(24, b), HH_P, 50, 'LF')
        hit(B(25, b), KICK, 70 + b * 10, 'RF')
    hit(B(25, 3.5), KICK, 104, 'RF')
    surge(B(24), B(26, 1), 0.03)


def shuffle(bar, b0=0, b1=4, base=90, cym='ride', ghost=0.35):
    for beat in range(b0, b1):
        for t in range(3):
            pos = B(bar, beat + t / 3.0)
            if t in (0, 2):
                p = RIDE if cym == 'ride' else HH_C
                hit(pos, p, (base - 6 if t == 0 else base - 18) + jit(4), 'R')
            if t == 0 and beat in (1, 3):
                hit(pos, SNARE, base + 20 + jit(3), 'L')
            elif t > 0 and rng.random() < ghost:
                hit(pos, SNARE, 28 + rng.uniform(0, 12), 'L')
            if t == 0 and beat in (0, 2):
                hit(pos, KICK, base + 8, 'RF')
            elif t == 2 and rng.random() < 0.3:
                hit(pos, KICK, base - 10, 'RF')
            if t == 0 and beat in (1, 3) and cym == 'ride':
                hit(pos, HH_P, 60, 'LF')


def triplets():                                 # bars 26-33
    land(B(26), 118)
    shuffle(26, 0, 3, base=92)
    motif_b(B(26, 3), T_HI, SNARE, base=104)
    motif_b(B(27, 0), T_HM, SNARE, base=102)
    motif_b(B(27, 1), T_LO, SNARE, base=100)
    shuffle(27, 2, 4, base=92)
    # 28: quarter-note triplets against the quarter-note pulse
    path = [T_HI, T_HM, T_LM, T_LO, FT_HI, FT_LO]
    for k in range(6):
        pos = B(28) + k * 2 / 3.0
        hit(pos, path[k], 100 + k * 3 + jit(3), 'R')
        hit(pos + 1 / 3.0, SNARE, 32 + k * 2 + jit(5), 'L')
    for b in range(4):
        hit(B(28, b), KICK, 94 + jit(3), 'RF')
        if b in (1, 3):
            hit(B(28, b), HH_P, 60, 'LF')
    # 29: motif B walking down the toms
    for b in range(4):
        motif_b(B(29, b), [T_HI, T_HM, T_LO, FT_LO][b], SNARE, base=100 + b * 4)
        if b in (1, 3):
            hit(B(29, b), HH_P, 60, 'LF')
    surge(B(29), B(31), 0.015)
    # 30: sixteenth-triplet singles, accents every four (hemiola)
    path = walk(24, start=1)
    run(B(30), 24, 1 / 6.0, 'RL',
        lambda i, h: path[i] if (i % 4 == 0 or h == 'R') else SNARE,
        lambda i: (112 if i % 4 == 0 else 56) + i * 0.6 + jit(4))
    for i in range(0, 24, 4):
        hit(B(30, i / 6.0), KICK, 100 + jit(3), 'RF')
    # 31: mirrored motif B, then flam accents
    motif_b(B(31, 0), T_HI, FT_LO, base=106, lead='L', crash_first=True)
    motif_b(B(31, 1), T_LM, SNARE, base=104, lead='R')
    fill_flams(B(31, 2), 2.0, 96, 114, walkstart=2)
    # 32: motif B augmented to eighth-note triplets
    motif_b(B(32, 0), CRASH, SNARE, base=110, grid=1 / 3.0, crash_first=True, tap=T_LM, tapboost=22)
    motif_b(B(32, 2), FT_LO, SNARE, base=112, grid=1 / 3.0, tap=T_HM, tapboost=26, kick2=True)
    for b in (1, 3):
        hit(B(32, b), HH_P, 60, 'LF')
    # 33: sextuplet fill with both feet
    fill_sextuplets(B(33), 4.0, 72, 118, rush=8)
    surge(B(33), B(34, 1), 0.02)


def linear_sec():                               # bars 34-37
    land(B(34), 118)
    linear_bar(34, 'hat')
    linear_bar(35, 'cow')
    linear_bar(36, 'hat', boost=4)
    linear_bar(37, 'cow', beats=2, boost=6)
    fill_doubles(B(37, 2), 2.0, 78, 118, rush=6, walkstart=0)
    hit(B(37, 2), KICK, 98, 'RF')
    hit(B(37, 3), KICK, 104, 'RF')
    surge(B(37, 1), B(38, 1), 0.015)


def double_kick():                              # bars 38-43
    dkicks(38, base=80)
    land(B(38), 118)
    for s in range(2, 16, 2):
        hit(B(38, s * 0.25), BELL, (100 if s % 4 == 0 else 78) + jit(3), 'R')
    for s in range(16):
        if s in (4, 12):
            hit(B(38, s * 0.25), SNARE, 112 + jit(3), 'L')
        elif s % 2 == 1 and rng.random() < 0.3:
            hit(B(38, s * 0.25), SNARE, 34 + jit(5), 'L')
    dkicks(39, base=84)
    motif_a(39, [T_HI, T_HM, T_LM, FT_LO, SNARE, CHINA], base=108, cresc=8)
    dkicks(40, 0, 12, base=86)
    for s in range(0, 12, 2):
        hit(B(40, s * 0.25), CHINA, (98 if s % 4 == 0 else 80) + jit(3), 'R')
    for s in range(12):
        if s == 8:
            hit(B(40, 2), SNARE, 116, 'L')
        elif s % 2 == 1 and rng.random() < 0.4:
            hit(B(40, s * 0.25), SNARE, 34 + jit(5), 'L')
    fill_singles(B(40, 3), 1.0, 90, 114, startidx=2, rush=4)
    hit(B(40, 3.5), KICK, 104, 'RF')
    dkicks(41, base=88)
    motif_a(41, [SNARE, T_HI, T_LO, FT_LO, T_HM, FT_HI], base=110, cresc=8, density=0.6,
            ghost_voice=lambda s: [T_HI, T_HM, T_LM][s % 3], ghost_vel=55, crash_on=(0, 3))
    dkicks(42, base=92)
    path = walk(24, start=0, groups=(3, 6))
    for i in range(24):
        h = 'R' if i % 2 == 0 else 'L'
        x = i / 23.0
        p = CRASH if i in (0, 12) else path[i]
        hit(B(42, i / 6.0), p, 84 + 32 * x + (10 if i % 6 == 0 else 0) + jit(3), h, dt=-5 * x)
    surge(B(42), B(43, 2), 0.015)
    dkicks(43, 0, 8, base=96)
    fill_flams(B(43), 2.0, 100, 118, walkstart=1)
    land(B(43, 2), 120, cym=CHINA)
    hit(B(43, 3.5), SNARE, 92, 'L')
    hit(B(43, 3.75), SNARE, 104, 'R')
    surge(B(43, 2), B(44, 0.5), -0.02)


def motif_return():                             # bars 44-47
    motif_a(44, [SNARE, T_HI, T_LO, FT_LO, SNARE, FT_HI], base=112, cresc=8, density=0.5,
            ghost_vel=40, kick_under=(0, 1, 2, 3, 4, 5), crash_on=(0,))
    for b in range(4):
        hit(B(44, b), HH_P, 60, 'LF')
    hit(B(45), CHINA, 110, 'R')
    hit(B(45), KICK, 104, 'RF')
    motif_a(45, [SNARE, T_HM, FT_HI, T_HI, SNARE, FT_LO], base=110, cresc=10, density=0.45,
            shift=1, crash_on=(3,), kick_under=(0, 2, 4))
    gpath = walk(16, start=1)
    motif_a(46, [SNARE, T_HI, T_LM, FT_LO, SNARE, FT_HI], base=112, cresc=8, density=0.9,
            ghost_voice=lambda s: gpath[s], ghost_vel=52, flams=(0, 1, 2, 3, 4, 5),
            kick_under=(0, 5))
    for b in range(4):
        hit(B(46, b), HH_P, 60, 'LF')
    # 47: compressed motif, then the tail falls away into the roll
    accv = {0: CRASH, 3: T_HI, 6: FT_LO, 9: CRASH2, 12: CHINA}
    tail = {13: (T_HI, 88), 14: (T_LM, 68), 15: (FT_LO, 50)}
    for step in range(16):
        h = 'R' if step % 2 == 0 else 'L'
        pos = B(47, step * 0.25)
        dt = -5 * step / 15.0
        if step in accv:
            hit(pos, accv[step], 116 + jit(3), h, dt)
            hit(pos, KICK, 110 + jit(3), 'RF', dt)
        elif step in tail:
            hit(pos, tail[step][0], tail[step][1] + jit(3), h, dt)
        else:
            hit(pos, SNARE, 60 + jit(6), h, dt)
    surge(B(47), B(48), 0.012)


def roll_build():                               # bars 48-49
    n = 64
    toms = [T_HI, T_HM, T_LM, T_LO, FT_HI, FT_LO]
    for i in range(n):
        x = i / (n - 1.0)
        h = 'R' if i % 2 == 0 else 'L'
        v = 26 + 92 * x ** 1.8
        p = SNARE
        if i >= 48:
            k = i - 48
            if k % 3 == 0:
                v += 14
                p = toms[min(5, k // 3)]
        hit(B(48) + i / 8.0, p, v + jit(2), h, dt=-4 * x)
    hit(B(48), KICK, 50, 'RF')
    hit(B(48, 2), KICK, 60, 'RF')
    for b in range(4):
        hit(B(48, b), HH_P, 50, 'LF')
    hit(B(49), KICK, 78, 'RF')
    hit(B(49, 1), KICK, 86, 'RF')
    for j, t in enumerate((2, 2.5, 3, 3.5)):
        hit(B(49, t), KICK, 92 + j * 5, 'RF')


def climax():                                   # bars 50-53 + final hit
    fill_sextuplets(B(50), 4.0, 96, 116, rush=0, crash_idx=(0, 12))
    gpath = walk(16, start=1)
    motif_a(51, [SNARE, T_HI, T_LO, FT_LO, SNARE, FT_HI], base=118, cresc=6, density=1.0,
            ghost_voice=lambda s: gpath[s], ghost_vel=68, kick_under=(0, 1, 2, 3, 4, 5),
            crash_on=(0, 3))
    for b in range(4):
        hit(B(51, b), HH_P, 62, 'LF')
    for b in range(4):
        motif_b(B(52, b), T_HI, [FT_LO, SNARE, FT_HI, FT_LO][b], base=108 + b * 3,
                tap=[T_HI, T_HM, T_LM, T_LO][b], crash_first=(b % 2 == 0), tapboost=16,
                kick2=True)
    surge(B(52), B(53, 2), 0.015)
    # final fill
    fill_flams(B(53), 2.0, 104, 118, walkstart=0)
    fill_doubles(B(53, 2), 1.0, 92, 118, rush=3, walkstart=0)
    hit(B(53, 2), KICK, 104, 'RF')
    hit(B(53, 2.5), KICK, 108, 'RF')
    for t in range(3):
        pos = B(53, 3 + t / 3.0)
        hit(pos, FT_LO, 108 + 6 * t, 'R')
        hit(pos, T_LO, 106 + 6 * t, 'L')
        hit(pos, KICK, 108 + 6 * t, 'RF')
    # the final hit
    hit(B(54), CRASH, 127, 'R', dur=3.0)
    hit(B(54), CRASH2, 124, 'L', dur=3.0)
    hit(B(54), KICK, 127, 'RF', dur=3.0)
    hit(B(54), KICK2, 122, 'LF', dur=3.0)


# ---------------- Tempo & feel ----------------
SEG = [(0, 4, 96, 100), (4, 12, 103, 106), (12, 20, 107, 110), (20, 24, 106, 100),
       (24, 26, 100, 106), (26, 34, 106, 109), (34, 38, 108, 111), (38, 44, 111, 116),
       (44, 48, 116, 116), (48, 50, 114, 122), (50, 53.5, 122, 125), (53.5, 54, 125, 112),
       (54, 70, 112, 112)]


def base_bpm(beat):
    bar = beat / 4.0
    for s, e, a, b in SEG:
        if s <= bar < e:
            x = (bar - s) / (e - s)
            return a + (b - a) * x
    return SEG[-1][3]


def bpm_raw(beat):
    f = 1.0 + 0.006 * math.sin(2 * math.pi * beat / 16.0 + 0.7)
    for s, e, a in bumps:
        if s <= beat <= e:
            f += a * math.sin(math.pi * (beat - s) / (e - s))
    return base_bpm(beat) * f


def feel(pos):
    bar = pos / 4.0
    f = 3.0 * math.sin(2 * math.pi * pos / 32.0)
    if 20 <= bar < 24:
        f += 5.0      # laid back in the quiet section
    if 50 <= bar < 54:
        f -= 3.0      # on top of the beat at the climax
    return f


def dedup(ns):
    """Keep each limb to one stroke at a time and respect a minimum gap between its strokes."""
    ns = sorted(ns, key=lambda n: (n[0], -n[2]))
    ming = {'R': 0.1, 'L': 0.1, 'RF': 0.2, 'LF': 0.2}
    last = {}
    for n in ns:
        lb = n[3]
        pr = last.get(lb)
        if pr is not None and n[0] - pr[0] < ming[lb] - 1e-9:
            if n[2] > pr[2]:
                pr[6] = False
                last[lb] = n
            else:
                n[6] = False
            continue
        last[lb] = n
    return [n for n in ns if n[6]]


def render(path='solo.mid'):
    alive = dedup(notes)
    final_beat = B(54)
    nh = int(round(final_beat * 2))
    S = sum(30.0 / bpm_raw(j * 0.5 + 0.25) for j in range(nh))
    k = S / 118.0                      # the final hit lands at 118 s

    def bpm(b):
        return bpm_raw(b) * k

    extra = 2.0 * bpm(final_beat + 1) / 60.0
    end_beat = final_beat + extra
    end_tick = int(round(end_beat * PPQ))

    per = {}
    for n in alive:
        pos, p, v, lb, dt, dur = n[:6]
        sd = 3.5 if v >= 90 else (5.0 if v >= 55 else 7.0)
        bias = feel(pos)
        if v < 55:
            bias += 4.0
        if lb in ('RF', 'LF'):
            bias -= 1.5
        if dur is not None:
            sd, bias = 1.0, 0.0
        ms = dt + rng.gauss(0, sd) + bias
        tick = int(round(pos * PPQ + ms / 1000.0 * bpm(pos) / 60.0 * PPQ))
        tick = max(0, tick)
        vel = int(max(1, min(127, round(v + rng.uniform(-2, 2)))))
        per.setdefault(lb, []).append([pos, tick, p, vel, dur])

    allev = []
    for lb in per:
        lst = sorted(per[lb], key=lambda x: (x[0], x[1]))
        for i in range(1, len(lst)):
            if lst[i][1] < lst[i - 1][1] + 20:
                lst[i][1] = lst[i - 1][1] + 20
        for i, e in enumerate(lst):
            d = int(round(e[4] * PPQ)) if e[4] else int(PPQ * 0.1)
            if i + 1 < len(lst):
                d = min(d, lst[i + 1][1] - e[1] - 8)
            e.append(max(8, d))
            allev.append(e)

    bypitch = {}
    for e in allev:
        bypitch.setdefault(e[2], []).append(e)
    msgs = []
    for p in sorted(bypitch):
        lst = sorted(bypitch[p], key=lambda x: (x[1], -x[3]))
        out = []
        for e in lst:
            if out and e[1] == out[-1][1]:
                continue
            out.append(e)
        for i, e in enumerate(out):
            d = e[5]
            if i + 1 < len(out):
                d = min(d, out[i + 1][1] - e[1] - 2)
            d = max(1, d)
            off = min(e[1] + d, end_tick - 1)
            msgs.append((e[1], 1, p, e[3]))
            msgs.append((off, 0, p, 0))
    msgs.sort()

    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    t0 = mido.MidiTrack()
    mid.tracks.append(t0)
    t0.append(mido.MetaMessage('track_name', name='Tempo', time=0))
    t0.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                               clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    last = 0
    nhalf_total = int(math.ceil(end_beat * 2))
    for j in range(nhalf_total):
        tick = j * (PPQ // 2)
        if tick >= end_tick:
            break
        tempo = int(round(60000000.0 / bpm(j * 0.5 + 0.25)))
        t0.append(mido.MetaMessage('set_tempo', tempo=tempo, time=tick - last))
        last = tick
    t0.append(mido.MetaMessage('end_of_track', time=end_tick - last))

    t1 = mido.MidiTrack()
    mid.tracks.append(t1)
    t1.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    t1.append(mido.Message('control_change', channel=9, control=7, value=115, time=0))
    t1.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
    t1.append(mido.Message('control_change', channel=9, control=91, value=45, time=0))
    last = 0
    for tick, kind, p, v in msgs:
        if kind == 1:
            m = mido.Message('note_on', channel=9, note=p, velocity=v, time=tick - last)
        else:
            m = mido.Message('note_off', channel=9, note=p, velocity=0, time=tick - last)
        t1.append(m)
        last = tick
    t1.append(mido.MetaMessage('end_of_track', time=max(0, end_tick - last)))
    mid.save(path)


def main():
    intro()          # bars 0-3
    groove_sec()     # bars 4-11
    development()    # bars 12-19
    quiet()          # bars 20-25
    triplets()       # bars 26-33
    linear_sec()     # bars 34-37
    double_kick()    # bars 38-43
    motif_return()   # bars 44-47
    roll_build()     # bars 48-49
    climax()         # bars 50-53, final hit at bar 54
    render('solo.mid')


if __name__ == '__main__':
    main()
