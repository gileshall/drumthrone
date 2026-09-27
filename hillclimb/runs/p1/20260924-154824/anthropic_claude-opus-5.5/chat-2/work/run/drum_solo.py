#!/usr/bin/env python3
"""
drum_solo.py - generates a ~2 minute General MIDI drum solo (solo.mid, channel 10).

Built around one motif (a clave-like figure on 16th steps 0,3,6,10,12) that is
stated, answered, displaced, compressed, re-orchestrated (toms / cymbals / latin
percussion), used as the kick pattern and as roll accents, and finally augmented
into the ending.  Every note is assigned to a limb (R, L, RF, LF) and a validator
guarantees no limb ever strikes twice at once, so at most two hands and two
feet sound at any instant.  Timing feel is systematic (swing per section, leaning
ahead/behind per section and per voice) and the tempo map breathes.
"""
import math
import random
import bisect
import mido

TPB = 960
SEED = 8675309
rng = random.Random(SEED)

EVENTS = []   # (time_beats, note, velocity, limb, is_grace)
HEAT = []     # tempo push bumps: (beat_start, beat_end, bpm_amount)
FEEL = {'swing': 0.5, 'lean': 0.0, 'dyn': 1.0, 'ramp': None}

# ---------------- General MIDI percussion ----------------
KICK2, KICK = 35, 36
SIDE, SNARE, CLAP, SNARE2 = 37, 38, 39, 40
FLOOR_LO, HH_CL, FLOOR_HI, HH_PED = 41, 42, 43, 44
TOM_LO, HH_OP, TOM_LM, TOM_HM = 45, 46, 47, 48
CRASH, TOM_HI, RIDE, CHINA, BELL = 49, 50, 51, 52, 53
TAMB, SPLASH, COWBELL, CRASH2, VIBRA, RIDE2 = 54, 55, 56, 57, 58, 59
BONGO_HI, BONGO_LO, CONGA_MUTE, CONGA_OPEN, CONGA_LO = 60, 61, 62, 63, 64
TIMB_HI, TIMB_LO, AGOGO_HI, AGOGO_LO = 65, 66, 67, 68
CABASA, MARACAS = 69, 70
CLAVES, WOOD_HI, WOOD_LO = 75, 76, 77
TRI_MUTE, TRI_OPEN = 80, 81

TOMS = [TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO]
CYMBALS = {CRASH, CRASH2, CHINA, SPLASH, RIDE, RIDE2, BELL, HH_CL, HH_OP, COWBELL}

# ---------------- the motif ----------------
MOTIF = [0, 3, 6, 10, 12]
MACC = [1.0, 0.82, 0.88, 0.8, 0.97]
ORCH_TOMS = [(TOM_HI, 'R'), (TOM_HM, 'L'), (TOM_LM, 'R'), (FLOOR_HI, 'R'), (FLOOR_LO, 'R')]
ORCH_LATIN = [(TIMB_HI, 'R'), (CONGA_OPEN, 'L'), (TIMB_LO, 'R'), (CONGA_LO, 'L'), (TIMB_HI, 'R')]
ORCH_DIM = [(CRASH, 'R'), (TOM_HM, 'L'), (TOM_LM, 'R'), (FLOOR_HI, 'L'), (FLOOR_LO, 'R')]
ORCH_DIM_T = [(TOM_HI, 'R'), (TOM_HM, 'L'), (TOM_LM, 'R'), (FLOOR_HI, 'L'), (FLOOR_LO, 'R')]
ORCH_RETRO = [(CHINA, 'R'), (FLOOR_HI, 'L'), (TOM_LO, 'R'), (TOM_HM, 'L'), (TOM_HI, 'R')]
ORCH_RECAP = [(CRASH, 'R'), (TOM_HM, 'L'), (TOM_LM, 'R'), (FLOOR_HI, 'R'), (FLOOR_LO, 'R')]

FINAL_BEAT = 224          # bar 56 downbeat: final hit
TOTAL_BEATS = 57 * 4
TARGET_SECONDS = 117.5    # time of the final hit; ~2.5 s ring after
RING_SECONDS = 2.5


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def T(bar, step=0.0, sub=16):
    return bar * 4.0 + step * 4.0 / sub


def ramp(i, n, a, b):
    return a + (b - a) * (i / (n - 1) if n > 1 else 0.0)


def warp(t, swing):
    """Continuous swing warp of each half beat (16th-note swing)."""
    b = math.floor(t * 2 + 1e-9) / 2.0
    x = max(0.0, t - b)
    if x < 0.25:
        y = x * 2 * swing
    else:
        y = 0.5 * swing + (x - 0.25) * 2 * (1 - swing)
    return b + y


def cur_lean(t):
    r = FEEL.get('ramp')
    if r:
        t0, t1, l0, l1 = r
        x = clamp((t - t0) / (t1 - t0), 0.0, 1.0)
        return l0 + (l1 - l0) * x
    return FEEL['lean']


def hit(t, note, vel, limb, lean=0.0, grace=False, swing=None):
    s = FEEL['swing'] if swing is None else swing
    tt = warp(t, s) + cur_lean(t) + lean + rng.uniform(-0.0025, 0.0025)
    v = vel * FEEL['dyn'] + rng.uniform(-2.5, 2.5)
    EVENTS.append((max(0.0, tt), note, int(round(clamp(v, 1, 127))), limb, grace))


def flam(t, note, vel, limb, lean=0.0, swing=None):
    other = 'L' if limb == 'R' else 'R'
    hit(t, note, vel * 0.42, other, lean - 0.04, grace=True, swing=swing)
    hit(t, note, vel, limb, lean, swing=swing)


LIMB_MAP = {'R': 'R', 'L': 'L', 'K': 'RF', 'F': 'LF'}


def run(t0, n, sub, sticking, note_fn, vel_fn, lean=0.0, swing=None):
    dt = 1.0 / sub
    for i in range(n):
        st = sticking[i % len(sticking)]
        if st == '-':
            continue
        limb = LIMB_MAP[st]
        note = note_fn(i, limb)
        if note is None:
            continue
        hit(t0 + i * dt, note, vel_fn(i), limb, lean, swing=swing)


def motif(t0, orch, vel, unit=0.25, shift=0, kicks=(0, 4), flams=False, lean=0.0):
    for i, s in enumerate(MOTIF):
        t = t0 + (s + shift) * unit
        note, limb = orch[i]
        v = vel * MACC[i]
        if flams and note not in CYMBALS:
            flam(t, note, v, limb, lean)
        else:
            hit(t, note, v, limb, lean)
        if i in kicks:
            hit(t, KICK, min(127, v * 0.95 + 6), 'RF', lean)


def add_heat(b0, b1, amt):
    HEAT.append((b0, b1, amt))


def ride_jazz(bar, v, upto=16):
    for s in (0, 4, 7, 8, 12, 15):
        if s < upto:
            vv = v if s in (4, 12) else (v * 0.82 if s in (0, 8) else v * 0.7)
            hit(T(bar, s), RIDE, vv, 'R')


# =====================================================================
# Sections
# =====================================================================
def section_intro():                       # bars 0-5
    FEEL.update(swing=0.54, lean=0.008, dyn=1.0, ramp=None)
    for bar in range(6):
        for s in (4, 12):
            hit(T(bar, s), HH_PED, 50, 'LF')
    # statement
    motif(T(0), ORCH_TOMS, 90, kicks=(0, 4))
    # answer: ride and ghosts
    ride_jazz(1, 60)
    for s, v in ((2, 28), (6, 32), (10, 30), (13, 36), (14, 44)):
        hit(T(1, s), SNARE, v, 'L', 0.006)
    hit(T(1, 0), KICK, 46, 'RF')
    hit(T(1, 8), KICK, 40, 'RF')
    # statement with ghost fill-in, hand to hand
    motif(T(2), ORCH_TOMS, 98, kicks=(0, 4))
    fs = (1, 2, 4, 5, 7, 8, 9, 11)
    for j, s in enumerate(fs):
        hit(T(2, s), SNARE, ramp(j, len(fs), 26, 44), 'R' if s % 2 == 0 else 'L', 0.006)
    # answer with six-stroke roll
    ride_jazz(3, 62, upto=12)
    for s in (2, 6, 10):
        hit(T(3, s), SNARE, 30, 'L', 0.006)
    hit(T(3, 0), KICK, 48, 'RF')
    hit(T(3, 10), KICK, 62, 'RF')
    for i, st in enumerate("RLLRRL"):
        t = T(3, 12) + i / 6.0
        if i == 0:
            hit(t, SNARE, 96, 'R', swing=0.5)
        elif i == 5:
            hit(t, FLOOR_LO, 102, 'L', swing=0.5)
            hit(t, KICK, 80, 'RF', swing=0.5)
        else:
            hit(t, SNARE, 40 if st == 'L' else 46, st, swing=0.5)
    # displaced motif
    hit(T(4), SPLASH, 88, 'R')
    hit(T(4), KICK, 84, 'RF')
    motif(T(4), ORCH_TOMS, 100, shift=2, kicks=(1, 3))
    for s in (3, 7, 9, 11, 13):
        hit(T(4, s), SNARE, 32, 'L', 0.006)
    hit(T(4, 15), FLOOR_LO, 86, 'L')
    hit(T(4, 8), KICK, 60, 'RF')
    # swelling roll into the groove
    ride_jazz(5, 64, upto=8)
    for s in (2, 6):
        hit(T(5, s), SNARE, 32, 'L', 0.006)
    hit(T(5, 0), KICK, 56, 'RF')
    run(T(5, 8), 16, 8, "RRLL", lambda i, l: SNARE,
        lambda i: ramp(i, 16, 30, 114) + (6 if i % 2 == 0 else 0), swing=0.5)
    hit(T(5, 8), KICK, 50, 'RF')
    hit(T(5, 12), KICK, 72, 'RF')
    add_heat(T(5, 4), T(6), 1.5)


def section_groove():                      # bars 6-15
    FEEL.update(swing=0.57, lean=0.004, dyn=1.0, ramp=None)
    kick_pats = [[0, 3, 6, 10], [0, 3, 6, 10, 11], [0, 3, 6, 10], [0, 3, 6, 10, 14],
                 [0, 3, 8, 10], [0, 3, 8, 10, 13], [0, 3, 6, 10], [0, 3, 6, 10],
                 [0, 3, 6, 10, 11], [0, 3, 6, 10]]
    extra_ghosts = [1, 5, 11, 13]
    for idx in range(10):
        bar = 6 + idx
        ride = 4 <= idx <= 7
        fill_from = {3: 12, 7: 8, 9: 0}.get(idx, 16)
        for s in range(0, fill_from, 2):
            quarter = (s % 4 == 0)
            if s == 0 and idx in (0, 4, 8):
                hit(T(bar, s), CRASH2 if idx == 4 else CRASH, 114, 'R')
                continue
            if ride:
                note = BELL if s == 8 else RIDE
                v = 86 if quarter else 64
            else:
                note = HH_OP if (s == 14 and idx % 2 == 0) else HH_CL
                v = 92 if quarter else 60
                if note == HH_OP:
                    v = 84
            hit(T(bar, s), note, v, 'R')
        if ride:
            for s in (4, 12):
                hit(T(bar, s), HH_PED, 58, 'LF')
        if (not ride) and idx % 2 == 0 and fill_from == 16:
            hit(T(bar + 1, 0), HH_PED, 62, 'LF')     # close the open hat
        for s in (4, 12):
            if s < fill_from:
                hit(T(bar, s), SNARE, 110 if s == 12 else 104, 'L', 0.012)  # laid back
        ghosts = [7, 9, 15] + sorted(rng.sample(extra_ghosts, 1 + idx % 2))
        for s in ghosts:
            if s < fill_from:
                hit(T(bar, s), SNARE, 28 + (8 if s == 15 else 0) + rng.randint(0, 6), 'L', 0.006)
        for s in kick_pats[idx]:
            if s < fill_from:
                hit(T(bar, s), KICK, 102 if s == 0 else 88, 'RF', -0.004)  # kick a hair ahead
    # fill 1: bar 9, beat 4
    run(T(9, 12), 4, 4, "RLRL", lambda i, l: [TOM_HI, TOM_HM, TOM_LO, FLOOR_LO][i],
        lambda i: ramp(i, 4, 88, 106), lean=-0.004)
    hit(T(9, 12), KICK, 90, 'RF')
    hit(T(9, 14), KICK, 84, 'RF')
    add_heat(T(9, 10), T(10), 1.0)
    # fill 2: bar 13, paradiddle around the kit
    pn = [TOM_HI, SNARE, TOM_HM, TOM_LM, SNARE, FLOOR_HI, FLOOR_LO, FLOOR_LO]
    run(T(13, 8), 8, 4, "RLRRLRLL", lambda i, l: pn[i],
        lambda i: ramp(i, 8, 78, 108) + (12 if i % 4 == 0 else 0), lean=-0.004)
    for s in (8, 11, 14):
        hit(T(13, s), KICK, 92, 'RF')
    add_heat(T(13, 8), T(14), 1.5)
    # fill 3: bar 15, motif as fill + 32nd run
    for s in range(12):
        limb = 'R' if s % 2 == 0 else 'L'
        if s in MOTIF:
            i = MOTIF.index(s)
            hit(T(15, s), ORCH_TOMS[i][0], 106 * MACC[i], limb)
            hit(T(15, s), KICK, 96, 'RF')
        else:
            hit(T(15, s), SNARE, ramp(s, 12, 44, 74), limb, 0.004)
    rn = [FLOOR_LO, SNARE, TOM_LO, TOM_LO, FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO]
    run(T(15, 12), 8, 8, "RL", lambda i, l: rn[i], lambda i: ramp(i, 8, 98, 120), swing=0.52)
    hit(T(15, 12), KICK, 104, 'RF')
    hit(T(15, 14), KICK, 96, 'RF')
    add_heat(T(15), T(16), 2.0)


def section_dev():                         # bars 16-25
    FEEL.update(swing=0.52, lean=-0.004, dyn=1.0, ramp=None)
    para = "RLRRLRLL"
    for k, bar in enumerate((16, 17)):
        r_acc = {0: (CRASH if k == 0 else TOM_HI), 3: (TOM_HM if k == 0 else TOM_LM),
                 10: (FLOOR_HI if k == 0 else FLOOR_LO)}
        l_acc = {6: SNARE, 12: (SNARE if k == 0 else TOM_LO)}
        for s in range(16):
            limb = para[s % 8]
            if s in r_acc:
                hit(T(bar, s), r_acc[s], 112 if s == 0 else 104, 'R')
            elif s in l_acc:
                hit(T(bar, s), l_acc[s], 116, 'L')
            elif limb == 'R':
                hit(T(bar, s), HH_CL, 58 if s % 4 == 0 else 48, 'R')
            else:
                hit(T(bar, s), SNARE, 34, 'L', 0.005)
        for s in ((0, 6, 12) if k == 0 else (0, 6, 8, 12, 14)):
            hit(T(bar, s), KICK, 100 if s in MOTIF else 84, 'RF', -0.003)

    # bar 18: R-L-kick triplets around the toms
    def rlk_note(i, l):
        if l == 'RF':
            return KICK
        if l == 'L':
            return SNARE
        if i == 0:
            return CRASH
        return TOMS[(i // 3) % 6]
    run(T(18), 24, 6, "RLK", rlk_note,
        lambda i: ramp(i, 24, 74, 98) + (16 if i % 6 == 0 else 0) - (14 if i % 3 == 1 else 0),
        swing=0.5)

    # bar 19: displaced motif as cymbal/snare/kick unisons over LH 16ths
    crashes = [CRASH, CHINA, CRASH2, CHINA, CRASH]
    disp = [s + 2 for s in MOTIF]
    for s in range(16):
        if s in disp:
            i = disp.index(s)
            hit(T(19, s), crashes[i], 112, 'R')
            hit(T(19, s), SNARE, 118, 'L')
            hit(T(19, s), KICK, 104, 'RF')
        else:
            hit(T(19, s), SNARE, 38 + (6 if s % 4 == 0 else 0), 'L', 0.004)
    hit(T(19, 0), KICK, 90, 'RF')
    for s in (0, 4, 8, 12):
        hit(T(19, s), HH_PED, 54, 'LF')

    # bars 20-21: doubles travelling up and down the kit, crescendo
    path = [SNARE, TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO,
            FLOOR_HI, TOM_LO, TOM_LM, TOM_HM, TOM_HI]
    run(T(20), 32, 4, "RRLL", lambda i, l: path[(i // 2) % len(path)],
        lambda i: ramp(i, 32, 62, 108) + (8 if i % 2 == 0 else -4))
    for bar in (20, 21):
        for s in (0, 4, 8, 12):
            hit(T(bar, s), KICK, 88, 'RF', -0.003)
        for s in (2, 6, 10, 14):
            hit(T(bar, s), HH_PED, 56, 'LF')
    add_heat(T(21), T(22), 1.5)

    # bars 22-23: motif in diminution (32nd grid), flammed
    motif(T(22, 0), ORCH_DIM, 112, unit=0.125, kicks=(0, 2, 4), flams=True)
    motif(T(22, 8), ORCH_DIM_T, 108, unit=0.125, kicks=(0, 2, 4), flams=True)
    for bar in (22, 23):
        for s in (0, 4, 8, 12):
            hit(T(bar, s), HH_PED, 58, 'LF')
    for i, s in enumerate(MOTIF):
        t = T(23) + s * 0.125
        hit(t, COWBELL, 100 * MACC[i], 'R')
        hit(t, KICK, 92, 'RF')
    hit(T(23, 4), SNARE, 100, 'L')
    rn = [TOM_HI, TOM_HM, TOM_HM, TOM_LM, TOM_LO, TOM_LO, FLOOR_HI, FLOOR_LO]
    run(T(23, 8), 8, 4, "RL", lambda i, l: rn[i], lambda i: ramp(i, 8, 86, 110))
    for s in (8, 12, 14):
        hit(T(23, s), KICK, 94, 'RF')

    # bar 24: six-stroke rolls moving down the toms
    acc_r = [TOM_HI, TOM_LM, FLOOR_HI, FLOOR_LO]
    six = "RLLRRL"
    for i in range(24):
        st = six[i % 6]
        beat = i // 6
        j = i % 6
        t = T(24) + i / 6.0
        if j == 0:
            note, v = acc_r[beat], 100 + beat * 4
        elif j == 5:
            note, v = SNARE, 106
        else:
            note, v = SNARE, 42 + (4 if st == 'R' else 0)
        hit(t, note, v, st, swing=0.5)
        if j == 0:
            hit(t, KICK, 96, 'RF', swing=0.5)
        if j == 3:
            hit(t, HH_PED, 58, 'LF', swing=0.5)

    # bar 25: descending run that dies away into a soft buzz (release)
    notes = [CRASH, TOM_HI, TOM_HM, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO]
    run(T(25), 8, 4, "RL", lambda i, l: notes[i], lambda i: ramp(i, 8, 106, 78))
    hit(T(25, 0), KICK, 100, 'RF')
    hit(T(25, 6), KICK, 80, 'RF')
    run(T(25, 8), 16, 8, "RRLL", lambda i, l: SNARE, lambda i: ramp(i, 16, 60, 22))
    for s in (8, 12):
        hit(T(25, s), HH_PED, 50, 'LF')
    add_heat(T(25), T(26), -1.5)


def section_latin():                       # bars 26-33
    FEEL.update(swing=0.5, lean=0.01, dyn=1.0, ramp=None)
    for bar in range(26, 34):
        ks = [0, 3, 8] + ([11] if bar % 2 else [])
        for s in ks:
            hit(T(bar, s), KICK, 72 if s == 0 else 58, 'RF', -0.003)
        for s in (4, 12):
            hit(T(bar, s), HH_PED, 52, 'LF')
    # shaker + motif as clave
    for bar, shaker in ((26, MARACAS), (27, CABASA)):
        for s in range(16):
            v = 58 if s % 4 == 2 else (46 if s % 2 == 0 else 32)
            hit(T(bar, s), shaker, v, 'R')
        for i, s in enumerate(MOTIF):
            hit(T(bar, s), CLAVES, 90 * MACC[i], 'L')
    # cowbell + conga tumbao
    tumbao = [(4, CONGA_MUTE, 64), (6, CONGA_OPEN, 86), (7, CONGA_OPEN, 76),
              (12, CONGA_MUTE, 62), (14, CONGA_LO, 90), (15, CONGA_LO, 80)]
    for bar in (28, 29):
        lim = 12 if bar == 29 else 16
        for s in (0, 4, 6, 8, 12, 14):
            if s < lim:
                hit(T(bar, s), COWBELL, 86 if s % 4 == 0 else 66, 'R')
        for s, n, v in tumbao:
            if s < lim:
                hit(T(bar, s), n, v, 'L')
    run(T(29, 12), 4, 4, "RLRL", lambda i, l: [TIMB_HI, TIMB_HI, TIMB_LO, TIMB_LO][i],
        lambda i: ramp(i, 4, 82, 104))
    # motif on timbales/congas
    motif(T(30), ORCH_LATIN, 104, kicks=())
    hit(T(30, 14), VIBRA, 80, 'R')
    # cascara against the motif on congas
    for s in (0, 2, 4, 5, 7, 8, 10, 11, 13, 15):
        hit(T(31, s), WOOD_LO, 70 if s in (0, 4, 8) else 54, 'R')
    cn = [CONGA_OPEN, CONGA_OPEN, CONGA_LO, CONGA_MUTE, CONGA_LO]
    for i, s in enumerate(MOTIF):
        hit(T(31, s), cn[i], 92 * MACC[i], 'L')
    # agogo plays the displaced motif; bongo ghosts
    ag = [AGOGO_HI, AGOGO_LO, AGOGO_HI, AGOGO_HI, AGOGO_LO]
    for i, s in enumerate(MOTIF):
        hit(T(32, s + 2), ag[i], 86 * MACC[i], 'R')
    hit(T(32, 0), TRI_OPEN, 64, 'L')
    for s, n in ((6, BONGO_HI), (10, BONGO_HI), (15, BONGO_LO)):
        hit(T(32, s), n, 50, 'L')
    # the roll begins, pianissimo
    run(T(33), 16, 4, "RL", lambda i, l: SNARE, lambda i: ramp(i, 16, 22, 50))


def section_build():                       # bars 34-41, accelerating and pushing
    FEEL.update(swing=0.5, lean=0.0, dyn=1.0, ramp=(T(34), T(42), 0.0, -0.012))
    for bar in range(34, 38):
        for s in (0, 4, 8, 12):
            hit(T(bar, s), KICK, 70 + 5 * (bar - 34), 'RF', -0.003)
        for s in (2, 6, 10, 14):
            hit(T(bar, s), HH_PED, 56, 'LF')
    # singles with the motif accented (snare, then toms)
    for k, bar in enumerate((34, 35)):
        for s in range(16):
            limb = 'R' if s % 2 == 0 else 'L'
            if s in MOTIF:
                i = MOTIF.index(s)
                note = SNARE if k == 0 else ORCH_TOMS[i][0]
                v = 108 * MACC[i] + 8
            else:
                note, v = SNARE, 45 + (k * 16 + s) * 25 / 31.0
            hit(T(bar, s), note, v, limb)
    # sextuplets with accents every 4 notes: 3-against-4 tension
    n = 48
    for i in range(n):
        t = T(36) + i / 6.0
        limb = 'R' if i % 2 == 0 else 'L'
        base = 60 + 32 * i / (n - 1)
        if i % 4 == 0:
            note, v = TOMS[(i // 4) % 6], base + 28
        else:
            note, v = SNARE, base - 12
        hit(t, note, v, limb, swing=0.5)
    # doubles around the kit, then with crashes
    path2 = [TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO, SNARE, SNARE]

    def dbl_note(i, l):
        if i >= 16 and i % 4 == 0:
            return CRASH if (i // 4) % 2 == 0 else CRASH2
        return path2[(i // 2) % len(path2)]
    run(T(38), 32, 4, "RRLL", dbl_note, lambda i: ramp(i, 32, 80, 110) + (8 if i % 2 == 0 else -2))
    for s in MOTIF:
        hit(T(38, s), KICK, 96, 'RF')
    for s in range(0, 16, 2):
        hit(T(39, s), KICK, 90 if s % 4 == 0 else 82, 'RF')
    for bar in (38, 39):
        for s in (4, 12):
            hit(T(bar, s), HH_PED, 60, 'LF')
    # the big swelling roll
    run(T(40), 56, 8, "RRLL", lambda i, l: SNARE,
        lambda i: ramp(i, 56, 58, 122) + (6 if i % 8 == 0 else 0))
    for s in range(0, 16, 2):
        hit(T(40, s), KICK, ramp(s, 16, 78, 94), 'RF')
    for s in range(12):
        hit(T(41, s), KICK, ramp(s, 12, 94, 110), 'RF')
    for s in (0, 4, 8, 12):
        hit(T(40, s), HH_PED, 60, 'LF')
    for s in (0, 4, 8):
        hit(T(41, s), HH_PED, 60, 'LF')
    for j, nn in enumerate([TOM_HI, TOM_LM, FLOOR_HI, FLOOR_LO]):
        flam(T(41, 12 + j), nn, 116 + j * 2, 'R')
        hit(T(41, 12 + j), KICK, 110, 'RF')
    add_heat(T(40), T(42), 2.5)


def section_climax():                      # bars 42-51
    FEEL.update(swing=0.5, lean=-0.008, dyn=1.0, ramp=None)
    crashes = [CRASH, CRASH2, CHINA, CRASH2, CRASH]
    tp = [TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO]
    # motif as full-kit unisons over double bass
    for k, bar in enumerate((42, 43)):
        c = 0
        for s in range(16):
            acc = s in MOTIF
            if s % 2 == 0:
                hit(T(bar, s), KICK, 104 if acc else 86, 'RF')
            else:
                hit(T(bar, s), KICK2, 102 if acc else 80, 'LF')
            if acc:
                i = MOTIF.index(s)
                hit(T(bar, s), crashes[i], 118, 'R')
                hit(T(bar, s), SNARE, 122, 'L')
            elif k == 1 or (s - 1) not in MOTIF:
                hit(T(bar, s), tp[c % 6], 80 + k * 8, 'R' if s % 2 == 0 else 'L')
                c += 1
    # half-time: motif on the ride bell, double bass underneath
    for k, bar in enumerate((44, 45)):
        lim = 12 if k == 1 else 16
        for s in range(16):
            if s % 2 == 0:
                hit(T(bar, s), KICK, 92 if s % 4 == 0 else 84, 'RF')
            else:
                hit(T(bar, s), KICK2, 80, 'LF')
        for s in range(lim):
            if s in MOTIF:
                note = CRASH if (k == 0 and s == 0) else BELL
                hit(T(bar, s), note, 104 if s == 0 else 96, 'R')
            elif s % 2 == 0:
                hit(T(bar, s), RIDE, 70, 'R')
        for s, v in ((5, 40), (8, 122), (13, 42), (15, 46)):
            if s < lim:
                hit(T(bar, s), SNARE, v, 'L')
        if k == 1:
            run(T(bar, 12), 4, 4, "RLRL", lambda i, l: [TOM_HI, TOM_LM, FLOOR_HI, FLOOR_LO][i],
                lambda i: ramp(i, 4, 100, 116))

    # hand-hand-hand-hand-foot-foot triplets
    def herta(i, l):
        g, j = i // 6, i % 6
        if l == 'RF':
            return KICK
        if l == 'LF':
            return KICK2
        if i == 0:
            return CRASH
        if i == 24:
            return CHINA
        return tp[(g + j) % 6]
    run(T(46), 48, 6, "RLRLKF", herta,
        lambda i: ramp(i, 48, 90, 114) + (10 if i % 6 == 0 else 0), swing=0.5)
    # diminished motif, then retrograde
    motif(T(48), ORCH_DIM, 114, unit=0.125, kicks=(0, 1, 2, 3, 4), flams=True)
    r48 = [CRASH, TOM_HI, SNARE, TOM_HM, SNARE, TOM_LM, FLOOR_HI, FLOOR_LO]
    run(T(48, 8), 8, 4, "RL", lambda i, l: r48[i], lambda i: ramp(i, 8, 104, 116))
    motif(T(49), ORCH_RETRO, 114, unit=0.125, kicks=(0, 1, 2, 3, 4), flams=True)
    r49 = [FLOOR_LO, FLOOR_LO, FLOOR_HI, FLOOR_HI, TOM_LO, TOM_LO, TOM_LM, TOM_LM,
           TOM_HM, TOM_HM, TOM_HI, TOM_HI, SNARE, SNARE, SNARE, SNARE]
    run(T(49, 8), 16, 8, "RL", lambda i, l: r49[i], lambda i: ramp(i, 16, 90, 120))
    for bar in (48, 49):
        for s in range(8, 16):
            if s % 2 == 0:
                hit(T(bar, s), KICK, 92, 'RF')
            else:
                hit(T(bar, s), KICK2, 86, 'LF')
        for s in (0, 4):
            hit(T(bar, s), HH_PED, 60, 'LF')
    # peak: 32nd singles down the kit
    p50 = [TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO, SNARE, FLOOR_LO]
    run(T(50), 32, 8, "RL", lambda i, l: CRASH if i == 0 else p50[i // 4],
        lambda i: ramp(i, 32, 94, 116) + (12 if i % 4 == 0 else 0))
    for s in range(16):
        if s % 2 == 0:
            hit(T(50, s), KICK, 96, 'RF')
        else:
            hit(T(50, s), KICK2, 88, 'LF')
    run(T(51), 16, 8, "RRLL", lambda i, l: SNARE if i < 12 else FLOOR_LO,
        lambda i: ramp(i, 16, 96, 122))
    for s in range(8):
        if s % 2 == 0:
            hit(T(51, s), KICK, 100, 'RF')
        else:
            hit(T(51, s), KICK2, 94, 'LF')
    # quarter-note triplet unisons across the barline tension
    for k in range(3):
        t = T(51, 8) + k * (2.0 / 3.0)
        hit(t, [CRASH, CHINA, CRASH2][k], 124, 'R', swing=0.5)
        hit(t, SNARE, 124, 'L', swing=0.5)
        hit(t, KICK, 120, 'RF', swing=0.5)
        hit(t, KICK2, 116, 'LF', swing=0.5)
    for dt, nn, l in ((3.5, TOM_LO, 'R'), (11.0 / 3.0, FLOOR_HI, 'L'), (23.0 / 6.0, FLOOR_LO, 'R')):
        hit(T(51) + dt, nn, 112, l, swing=0.5)
    hit(T(51) + 11.0 / 3.0, KICK, 104, 'RF', swing=0.5)
    hit(T(51) + 23.0 / 6.0, KICK2, 100, 'LF', swing=0.5)
    add_heat(T(50), T(51, 8), 2.5)


def section_recap():                       # bars 52-56
    FEEL.update(swing=0.54, lean=0.006, dyn=1.0, ramp=None)
    motif(T(52), ORCH_RECAP, 114, kicks=(0, 2, 4))
    fs = (1, 2, 4, 5, 7, 8, 9, 11)
    for j, s in enumerate(fs):
        hit(T(52, s), SNARE, ramp(j, len(fs), 34, 54), 'R' if s % 2 == 0 else 'L', 0.006)
    for bar in (52, 53, 54):
        for s in (4, 12):
            hit(T(bar, s), HH_PED, 54, 'LF')
    # quiet echo on the latin voices
    motif(T(53), ORCH_LATIN, 74, kicks=(0,))
    # augmentation of the motif across two bars
    flam(T(54, 0), TOM_HI, 108, 'R')
    hit(T(54, 0), KICK, 104, 'RF')
    flam(T(54, 6), TOM_HM, 100, 'L')
    hit(T(54, 6), KICK, 96, 'RF')
    flam(T(54, 12), TOM_LM, 104, 'R')
    hit(T(54, 12), KICK, 100, 'RF')
    run(T(54, 13), 14, 8, "RRLL", lambda i, l: SNARE, lambda i: ramp(i, 14, 46, 104))
    flam(T(55, 4), FLOOR_HI, 110, 'L')
    hit(T(55, 4), KICK, 104, 'RF')
    run(T(55, 5), 6, 8, "LR", lambda i, l: SNARE, lambda i: ramp(i, 6, 70, 100))
    hit(T(55, 8), CRASH, 124, 'R')
    hit(T(55, 8), SNARE, 124, 'L')
    hit(T(55, 8), KICK, 120, 'RF')
    hit(T(55, 8), KICK2, 112, 'LF')
    fn = [TOM_HI, TOM_HM, TOM_LM, TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_LO]
    run(T(55, 9), 7, 4, "LR", lambda i, l: fn[i], lambda i: ramp(i, 7, 96, 120))
    for s in (10, 12, 14):
        hit(T(55, s), KICK, 104, 'RF')
    # final hit: all four limbs
    hit(T(56), CRASH, 127, 'R')
    hit(T(56), CRASH2, 127, 'L')
    hit(T(56), KICK, 127, 'RF')
    hit(T(56), KICK2, 124, 'LF')


# =====================================================================
# Tempo map
# =====================================================================
KEYS = [(0, 96), (6, 101), (12, 105), (16, 108), (24, 114), (26, 110), (30, 98),
        (34, 97), (42, 122), (46, 125), (51, 128), (52, 118), (54, 106), (56, 86), (58, 86)]


def base_bpm(beat):
    bar = beat / 4.0
    for (b0, v0), (b1, v1) in zip(KEYS, KEYS[1:]):
        if b0 <= bar <= b1:
            x = (bar - b0) / float(b1 - b0)
            x = 0.5 - 0.5 * math.cos(math.pi * x)
            return v0 + (v1 - v0) * x
    return KEYS[-1][1]


def heat_at(b):
    total = 0.0
    for b0, b1, amt in HEAT:
        if b0 <= b < b1:
            total += amt * (b - b0) / (b1 - b0)
        elif b1 <= b < b1 + 3.0:
            total += amt * (1.0 - (b - b1) / 3.0)
    return total


def tempo_map():
    n = TOTAL_BEATS + 8
    raw = [base_bpm(k + 0.5) + heat_at(k + 0.5) for k in range(n)]
    sm = []
    for k in range(n):
        a = raw[max(0, k - 1)]
        c = raw[min(n - 1, k + 1)]
        sm.append(0.25 * a + 0.5 * raw[k] + 0.25 * c)
    secs = sum(60.0 / x for x in sm[:FINAL_BEAT])
    f = secs / TARGET_SECONDS
    return [x * f for x in sm]


# =====================================================================
# Validation and MIDI output
# =====================================================================
MIN_GAP = 0.06  # beats between strokes of the same limb


def validate():
    main = sorted([e for e in EVENTS if not e[4]], key=lambda e: (e[0], e[1], e[3]))
    graces = sorted([e for e in EVENTS if e[4]], key=lambda e: (e[0], e[1], e[3]))
    per_limb = {l: [] for l in ('R', 'L', 'RF', 'LF')}
    kept = []
    for e in main:
        lst = per_limb[e[3]]
        if lst and e[0] - lst[-1] < MIN_GAP:
            continue
        lst.append(e[0])
        kept.append(e)
    for e in graces:
        lst = per_limb[e[3]]
        idx = bisect.bisect_left(lst, e[0])
        ok = (idx == 0 or e[0] - lst[idx - 1] >= MIN_GAP) and \
             (idx == len(lst) or lst[idx] - e[0] >= MIN_GAP)
        if ok:
            lst.insert(idx, e[0])
            kept.append(e)
    return kept


def write_midi(path):
    evs = validate()
    bpms = tempo_map()

    notes = {}
    for t, n, v, l, g in evs:
        tick = int(round(t * TPB))
        key = (tick, n)
        notes[key] = max(notes.get(key, 0), v)

    items = []   # (tick, prio, seq, msg)
    seq = 0

    def add(tick, prio, msg):
        nonlocal seq
        items.append((tick, prio, seq, msg))
        seq += 1

    add(0, -1, mido.MetaMessage('track_name', name='Drum Solo', time=0))
    add(0, -1, mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    add(0, -1, mido.Message('program_change', channel=9, program=0, time=0))
    add(0, -1, mido.Message('control_change', channel=9, control=7, value=118, time=0))
    add(0, -1, mido.Message('control_change', channel=9, control=10, value=64, time=0))
    add(0, -1, mido.Message('control_change', channel=9, control=91, value=40, time=0))

    ring_beats = RING_SECONDS * bpms[FINAL_BEAT] / 60.0
    end_tick = int(round((FINAL_BEAT + ring_beats) * TPB))
    last_tempo_beat = int(math.ceil(FINAL_BEAT + ring_beats))
    for k in range(min(last_tempo_beat + 1, len(bpms))):
        add(k * TPB, 0, mido.MetaMessage('set_tempo', tempo=int(round(60000000.0 / bpms[k])), time=0))

    by_note = {}
    for (tick, n), v in notes.items():
        by_note.setdefault(n, []).append((tick, v))
    for n in sorted(by_note):
        lst = sorted(by_note[n])
        for j, (tick, v) in enumerate(lst):
            off = tick + TPB // 8
            if j + 1 < len(lst):
                off = min(off, lst[j + 1][0] - 1)
            off = max(off, tick + 1)
            add(tick, 2, mido.Message('note_on', channel=9, note=n, velocity=v, time=0))
            add(off, 1, mido.Message('note_off', channel=9, note=n, velocity=0, time=0))

    items.sort(key=lambda x: (x[0], x[1], x[2]))
    end_tick = max(end_tick, items[-1][0] + 1)

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    now = 0
    for tick, prio, s, msg in items:
        track.append(msg.copy(time=tick - now))
        now = tick
    track.append(mido.MetaMessage('end_of_track', time=end_tick - now))
    mid.save(path)


def main():
    section_intro()
    section_groove()
    section_dev()
    section_latin()
    section_build()
    section_climax()
    section_recap()
    write_midi('solo.mid')


if __name__ == '__main__':
    main()
