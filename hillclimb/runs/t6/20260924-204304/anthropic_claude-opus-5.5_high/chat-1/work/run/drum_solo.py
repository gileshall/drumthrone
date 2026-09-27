#!/usr/bin/env python3
"""
drum_solo.py - generates solo.mid, a two-minute General MIDI drum solo on channel 10.

Musical plan (4/4, about 98 bpm nominal, with a tempo curve that breathes):
  bars  0-3   Intro: motif A (3-3-3-3-2-2 accent grouping) stated in open space, then answered
  bars  4-9   Groove development: motif A as snare/kick/bell accents over the ride, with ghost notes
  bars 10-17  Linear singles around the kit, RLL cross-rhythm, paradiddle-diddles, hand-foot
              combinations, hands-versus-feet unisons, and sextuplet doubles
  bars 18-21  Contrast: quiet colour section (cowbell, woodblocks, side stick) that grows back
  bars 22-27  Motif B (a triplet tom call), hemiola, traveling doubles over double-bass triplets
  bars 28-31  A snare roll that swells from pp with the motif A accents poking through
  bars 32-39  Climax: double bass, cymbal stabs, call and response, and big fills
  bars 40-41  Breakdown: space, then a ghost-note crescendo
  bars 42-47  Recap of both motifs, 32nd-note doubles, a final roll and stops, then the last hit

Every note has an explicit limb (RH, LH, RF, LF), and each limb strikes one note at a time.
Timing is humanised with a smooth tempo curve (phrase surges, fills that push, settling after
downbeats), with per-note micro-timing that places ghosts behind and accents ahead.
The tempo map is written into the file, so the MIDI beat grid follows the performance.
The random generator is seeded, so every run produces the same file.
"""
import bisect
import math
import random

import mido

rng = random.Random(1964)

# ---------------------------------------------------------------- GM percussion
KICK, KICK_B = 36, 35
SNARE, STICK = 38, 37
HH_CLOSED, HH_PEDAL, HH_OPEN = 42, 44, 46
TOM_HI, TOM_HMID, TOM_LMID, TOM_LO, FLOOR_HI, FLOOR_LO = 50, 48, 47, 45, 43, 41
CRASH1, CRASH2, RIDE, BELL, CHINA, SPLASH = 49, 57, 51, 53, 52, 55
COWBELL, TAMB, WB_HI, WB_LO, CLAVES = 56, 54, 76, 77, 75

TOMS = [TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO]
CYMBALS = {CRASH1, CRASH2, CHINA, SPLASH, RIDE, BELL}
RH, LH, RF, LF = 'RH', 'LH', 'RF', 'LF'
FEET = (RF, LF)

END_BEAT = 192          # the final hit (bar 48, beat 1)
FINAL_TIME = 117.0      # seconds at which the final hit lands
RING = 3.0

EV = []  # [beat, note, vel, limb, offset_sec, dur]


def hit(beat, note, vel, limb, off=0.0, dur=None):
    EV.append([float(beat), note, float(vel), limb, off, dur])


def kick(beat, vel, foot=RF, dur=None):
    hit(beat, KICK, vel, foot, 0.0, dur)


def other(h):
    return LH if h == RH else RH


def flam(beat, note, vel, limb, grace=None):
    hit(beat, grace if grace else note, vel * 0.42, other(limb), -0.028)
    hit(beat, note, vel, limb)


def B16(bar, p):
    return bar * 4 + p / 4.0


def lerp(a, b, x):
    return a + (b - a) * x


def starts(groups):
    out, p = [], 0
    for g in groups:
        out.append(p)
        p += g
    return out


def travel(path, n):
    return [path[min(len(path) - 1, int(i * len(path) / n))] for i in range(n)]


def hh_foot(bar, beats=(1, 3), vel=50):
    for q in beats:
        hit(bar * 4 + q, HH_PEDAL, vel, LF)


def land(bar, vel=112, cym=CRASH1, lh=None):
    hit(bar * 4, cym, vel, RH)
    kick(bar * 4, vel)
    if lh:
        hit(bar * 4, lh, vel - 6, LH)


def run(beat0, n, step, sticking, notes, v0, v1, accents=(), acc_boost=16, curve=1.0):
    for i in range(n):
        ch = sticking[i % len(sticking)].upper()
        x = i / max(1, n - 1)
        v = lerp(v0, v1, x ** curve)
        if i in accents:
            v += acc_boost
        if ch == 'K':
            kick(beat0 + i * step, v)
            continue
        hand = RH if ch == 'R' else LH
        note = notes(i, hand) if callable(notes) else notes[i % len(notes)]
        hit(beat0 + i * step, note, v, hand)


def dbl_bass(bar, b0, b1, v0, v1, per_beat=4):
    n = int(round((b1 - b0) * per_beat))
    for i in range(n):
        v = lerp(v0, v1, i / max(1, n - 1)) + (6 if i % per_beat == 0 else 0)
        kick(bar * 4 + b0 + i / per_beat, v, RF if i % 2 == 0 else LF)


MOTIF_A = [3, 3, 3, 3, 2, 2]
A_PERMS = [[3, 3, 3, 3, 2, 2], [3, 3, 2, 3, 3, 2], [2, 3, 3, 3, 3, 2],
           [3, 3, 3, 2, 3, 2], [3, 3, 2, 2, 3, 3]]


# ---------------------------------------------------------------- motif B
def motif_b(bar, beat_off, variant='orig', v=1.0, feet=True):
    """Triplet tom call over two beats: BOOM . ta TA-ka-DUM"""
    t0 = bar * 4 + beat_off

    def s(k):
        return t0 + k / 3.0

    if variant == 'cym':
        hit(s(0), rng.choice([CRASH1, CRASH2]), 114 * v, RH)
        hit(s(0), FLOOR_HI, 106 * v, LH)
    else:
        flam(s(0), FLOOR_HI, 110 * v, RH)
    if feet:
        kick(s(0), 108 * v)
    hit(s(2), SNARE, 44 * v, LH)
    if variant == 'double':
        run(s(3), 6, 1 / 6.0, 'RLRLRL',
            [TOM_HI, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO],
            86 * v, 106 * v, accents=(0,), acc_boost=10)
        if feet:
            kick(s(5), 96 * v)
    else:
        seq = [FLOOR_HI, TOM_LO, TOM_HI] if variant == 'up' else [TOM_HI, TOM_HMID, FLOOR_HI]
        hit(s(3), seq[0], 102 * v, RH)
        hit(s(4), seq[1], 84 * v, LH)
        hit(s(5), seq[2], 100 * v, RH)
        if feet:
            kick(s(4) if variant == 'up' else s(5), 94 * v)


# ---------------------------------------------------------------- bar builders
def groove_bar(bar, groups, ghost_p, fill_from=16, crash=False, cym=RIDE):
    acc = [p for p in starts(groups) if p < fill_from]
    rh, lh = set(), set()
    kick(B16(bar, 0), 98 if crash else 90)
    if crash:
        hit(B16(bar, 0), CRASH1, 108, RH)
        rh.add(0)
    accent_voice = BELL if cym == RIDE else HH_OPEN
    for p in acc[1:]:
        r = rng.random()
        if r < 0.3:
            kick(B16(bar, p), rng.uniform(90, 100))
            hit(B16(bar, p), accent_voice, rng.uniform(92, 104), RH)
            rh.add(p)
        elif r < 0.45:
            hit(B16(bar, p), rng.choice([TOM_HMID, TOM_LO, FLOOR_HI]), rng.uniform(96, 106), LH)
            lh.add(p)
        else:
            hit(B16(bar, p), SNARE, rng.uniform(98, 114), LH)
            lh.add(p)
    for p in range(0, fill_from, 2):
        if p in rh:
            continue
        hit(B16(bar, p), cym, (80 if p % 4 == 0 else 62) + rng.uniform(-4, 4), RH)
    for p in range(1, fill_from, 2):
        if p not in rh and rng.random() < 0.12:
            hit(B16(bar, p), cym, 50, RH)
    for p in range(1, fill_from):
        if p in lh:
            continue
        if rng.random() < ghost_p:
            hit(B16(bar, p), SNARE, rng.uniform(24, 40), LH)
    for p in (6, 7, 10, 11, 14):
        if p < fill_from and rng.random() < 0.25:
            kick(B16(bar, p), rng.uniform(70, 88))
    hh_foot(bar, vel=52)


def linear_bar(bar, groups, path, filler, v_acc, v_gh, lead=RH):
    acc = starts(groups)
    for p in range(16):
        hand = lead if p % 2 == 0 else other(lead)
        x = p / 15.0
        if p in acc:
            k = acc.index(p)
            n = path[k % len(path)]
            v = lerp(v_acc[0], v_acc[1], x)
            hit(B16(bar, p), n, v, hand)
            if n in CYMBALS or k == 0:
                kick(B16(bar, p), v - 4)
        else:
            n = filler[hand] if isinstance(filler, dict) else filler
            hit(B16(bar, p), n, lerp(v_gh[0], v_gh[1], x) + rng.uniform(-3, 3), hand)
    hh_foot(bar, beats=(0, 1, 2, 3), vel=44)


def unison_bar(bar, groups, rh_notes, lh_notes, v_acc=112, v_feet=(72, 92)):
    acc = starts(groups)
    for p in range(16):
        beat = B16(bar, p)
        foot = RF if p % 2 == 0 else LF
        if p in acc:
            k = acc.index(p)
            hit(beat, rh_notes[k % len(rh_notes)], v_acc + rng.uniform(-3, 4), RH)
            hit(beat, lh_notes[k % len(lh_notes)], v_acc - 5 + rng.uniform(-3, 3), LH)
            kick(beat, v_acc - 4, foot)
        else:
            kick(beat, lerp(v_feet[0], v_feet[1], p / 15.0), foot)


def climax_bar(bar, groups, cyms, feet=True, fill_from=16, vfeet=(84, 96)):
    acc = starts(groups)
    if feet:
        dbl_bass(bar, 0, 4, vfeet[0], vfeet[1])
    for k, (p, g) in enumerate(zip(acc, groups)):
        if p >= fill_from:
            break
        beat = B16(bar, p)
        hit(beat, cyms[k % len(cyms)], rng.uniform(110, 118), RH)
        hit(beat, SNARE, rng.uniform(104, 112), LH)
        if not feet:
            kick(beat, 110)
        if g >= 3:
            if p + 1 < fill_from:
                hit(B16(bar, p + 1), rng.choice([TOM_HI, TOM_HMID, TOM_LO]), rng.uniform(66, 78), RH)
            if p + 2 < fill_from:
                hit(B16(bar, p + 2), rng.choice([TOM_LO, FLOOR_HI, FLOOR_LO]), rng.uniform(78, 90), LH)
                if not feet:
                    kick(B16(bar, p + 2), rng.uniform(78, 88))
            if g == 4 and p + 3 < fill_from:
                hit(B16(bar, p + 3), FLOOR_LO, 84, RH)
        elif p + 1 < fill_from and rng.random() < 0.6:
            hit(B16(bar, p + 1), FLOOR_LO, rng.uniform(72, 84), LH)


def roll(bar, b0, b1, v0, v1, acc16=(), acc_notes=None, acc_boost=24, base=SNARE, curve=1.0):
    n = int(round((b1 - b0) * 8))
    acc16 = list(acc16)
    for i in range(n):
        beat = bar * 4 + b0 + i / 8.0
        hand = RH if i % 2 == 0 else LH
        x = i / max(1, n - 1)
        v = lerp(v0, v1, x ** curve) + rng.uniform(-3, 3)
        note = base
        p16 = b0 * 4 + i / 2.0
        if i % 2 == 0 and int(p16) in acc16:
            k = acc16.index(int(p16))
            if acc_notes:
                note = acc_notes[k % len(acc_notes)]
            v += acc_boost
        hit(beat, note, v, hand)


# ---------------------------------------------------------------- sections
def intro():
    b = 0  # the bare statement of motif A
    land(b, 100)
    hit(B16(b, 3), SNARE, 92, LH)
    hit(B16(b, 6), SNARE, 99, RH)
    hit(B16(b, 9), TOM_HMID, 96, RH)
    hit(B16(b, 12), FLOOR_HI, 104, RH)
    kick(B16(b, 12), 96)
    flam(B16(b, 14), SNARE, 110, RH)
    hh_foot(b, vel=48)

    b = 1  # a quiet answer
    kick(B16(b, 0), 78)
    hit(B16(b, 3), STICK, 58, LH)
    hit(B16(b, 6), STICK, 64, LH)
    kick(B16(b, 8), 70)
    for i, p in enumerate((9, 10, 11)):
        hit(B16(b, p), SNARE, 30 + 7 * i, RH if i % 2 == 0 else LH)
    for i, (p, n) in enumerate(zip((12, 13, 14, 15), (TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI))):
        hit(B16(b, p), n, 62 + 10 * i, RH if i % 2 == 0 else LH)
    hh_foot(b, vel=46)

    b = 2  # motif A on the toms, with ghost doubles
    notes = [SNARE, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO]
    for k, (p, g) in enumerate(zip(starts(MOTIF_A), MOTIF_A)):
        hit(B16(b, p), notes[k], 96 + 2 * k, RH)
        if k in (0, 4):
            kick(B16(b, p), 94)
        for j in range(1, g):
            if rng.random() < 0.6:
                hit(B16(b, p + j), SNARE, 32 + 6 * j + rng.uniform(-3, 3), LH)
    hh_foot(b, vel=50)

    b = 3  # motif A filled in, into a sextuplet cascade
    acc = starts(MOTIF_A)
    path = [SNARE, TOM_HI, TOM_HMID, TOM_LO]
    hand = RH
    for p in range(12):
        if p in acc:
            k = acc.index(p)
            hand = RH
            hit(B16(b, p), path[k], 100 + 2 * k, RH)
            if k == 0:
                kick(B16(b, p), 96)
        else:
            hand = other(hand)
            hit(B16(b, p), SNARE, 34 + 2.5 * p, hand)
    kick(B16(b, 9), 88)
    run(b * 4 + 3, 6, 1 / 6.0, 'RLRLRL',
        [TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_LO], 76, 112)
    kick(b * 4 + 3, 90)
    hh_foot(b, beats=(1,), vel=50)


def section_groove():
    groove_bar(4, MOTIF_A, 0.35, crash=True)
    groove_bar(5, A_PERMS[1], 0.45)
    groove_bar(6, A_PERMS[3], 0.5, fill_from=12)
    run(6 * 4 + 3, 6, 1 / 6.0, 'RLRLRL', travel([SNARE, TOM_HI, TOM_HMID, TOM_LO], 6), 58, 92)
    groove_bar(7, A_PERMS[2], 0.55, cym=HH_CLOSED)
    groove_bar(8, MOTIF_A, 0.6, crash=True)
    groove_bar(9, A_PERMS[4], 0.6, fill_from=8)
    run(9 * 4 + 2, 4, 0.25, 'RLRL', [SNARE, SNARE, TOM_HI, TOM_HI], 70, 86, accents=(0,))
    run(9 * 4 + 3, 8, 1 / 8.0, 'RLRLRLRL',
        travel([TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO], 8), 88, 116)
    for bt in (2, 3, 3.5):
        kick(9 * 4 + bt, 90 + 6 * (bt - 2))


def section_linear():
    linear_bar(10, MOTIF_A, [CRASH1, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, SNARE],
               SNARE, (96, 108), (30, 48))
    linear_bar(11, A_PERMS[1], [SNARE, TOM_LO, TOM_HI, FLOOR_LO, FLOOR_HI, CRASH2],
               {RH: HH_CLOSED, LH: SNARE}, (98, 110), (40, 56))
    # bars 12-13: R-l-l groups of three against the 4/4 pulse
    path = [TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO, SNARE,
            CRASH1, TOM_HMID, TOM_LO, FLOOR_LO, CHINA]
    for g in range(11):
        p = 3 * g
        x = p / 31.0
        va = lerp(88, 116, x)
        hit(12 * 4 + p / 4.0, path[g], va, RH)
        kick(12 * 4 + p / 4.0, va - 10)
        for j in (1, 2):
            if p + j < 32:
                hit(12 * 4 + (p + j) / 4.0, SNARE, lerp(30, 58, x) + 5 * (j - 1), LH)
    for q in range(8):
        hit(48 + q + 0.5, HH_PEDAL, 44, LF)
    # bar 14: paradiddle-diddles traveling down
    b = 14
    toms = [TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI]
    for q in range(4):
        for i, ch in enumerate('RLRRLL'):
            beat = b * 4 + q + i / 6.0
            hand = RH if ch == 'R' else LH
            if i == 0:
                n, v = toms[q], 104
            elif hand == RH:
                n, v = toms[q], 66
            else:
                n = SNARE if q % 2 == 0 else toms[min(q + 1, 3)]
                v = 46 + 4 * q
            hit(beat, n, v + 3 * q, hand)
        kick(b * 4 + q, 92)
        hit(b * 4 + q + 0.5, HH_PEDAL, 48, LF)
    # bar 15: R-L-K hand/foot sextuplets cascading down
    b = 15
    pairs = [(TOM_HI, TOM_HMID), (TOM_HMID, TOM_LO), (TOM_LO, FLOOR_HI), (FLOOR_HI, FLOOR_LO)]
    for i in range(24):
        beat = b * 4 + i / 6.0
        v = lerp(70, 116, i / 23.0)
        q, m = i // 6, i % 3
        if m == 0:
            hit(beat, pairs[q][0], v + (8 if i % 6 == 0 else 0), RH)
        elif m == 1:
            hit(beat, pairs[q][1], v - 4, LH)
        else:
            kick(beat, v - 6)
    # bar 16: hands play motif A in unison, feet fill every gap
    unison_bar(16, MOTIF_A, [CRASH1, CHINA, CRASH2, CRASH1, SPLASH, CRASH2],
               [SNARE, SNARE, FLOOR_HI, SNARE, FLOOR_LO, SNARE])
    # bar 17: sextuplet doubles traveling around the kit
    b = 17
    path = [SNARE, SNARE, TOM_HI, TOM_HI, TOM_HMID, TOM_HMID, TOM_LO,
            FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, SNARE]
    for i in range(24):
        pair = i // 2
        hand = RH if pair % 2 == 0 else LH
        v = lerp(52, 112, i / 23.0) + (10 if i % 2 == 0 else -4)
        hit(b * 4 + i / 6.0, path[pair], v, hand)
    for q in range(4):
        kick(b * 4 + q, 80 + 8 * q)


def section_quiet():
    perms = [A_PERMS[0], A_PERMS[1], A_PERMS[0], A_PERMS[2]]
    for k, b in enumerate(range(18, 22)):
        acc = starts(perms[k])
        if k == 0:
            land(b, 106, CRASH2)
        for p in (0, 6, 8, 14):
            if k == 0 and p == 0:
                continue
            if k == 3 and p == 14:
                continue
            kick(B16(b, p), rng.uniform(56, 66) + (6 if p == 0 else 0))
        if k >= 2 and rng.random() < 0.6:
            kick(B16(b, 11), 54)
        hh_foot(b, vel=46)
        lh_used = {0} if k == 0 else set()
        if k < 3:
            for p in (4, 12):
                hit(B16(b, p), STICK, 58 + 3 * k, LH)
                lh_used.add(p)
        last = 16 if k < 3 else 12
        for i, p in enumerate(acc):
            if (k == 0 and p == 0) or p >= last:
                continue
            if k < 2:
                n = COWBELL
            elif k == 2:
                n = WB_HI if i % 2 == 0 else WB_LO
            else:
                n = [SNARE, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO][i]
            hit(B16(b, p), n, 64 + 3 * i + (10 if k == 3 else 0), RH)
        if k == 1:
            for p in range(0, 16, 2):
                if p not in acc:
                    hit(B16(b, p), RIDE, 44, RH)
        if k == 2:
            for p in (2, 10):
                if p not in acc:
                    hit(B16(b, p), CLAVES, 50, RH)
        prob = [0.35, 0.45, 0.5, 0.95][k]
        for p in range(last):
            if p in lh_used:
                continue
            if rng.random() < prob:
                v = rng.uniform(20, 30) if k < 3 else lerp(26, 70, p / 11.0)
                hit(B16(b, p), SNARE, v, LH)
        if k == 3:
            run(b * 4 + 3, 3, 1 / 3.0, 'RLR', [SNARE, TOM_HI, TOM_HMID], 84, 104)
            kick(b * 4 + 3, 80)


def section_triplets():
    motif_b(22, 0, 'cym')
    motif_b(22, 2, 'up')
    hh_foot(22)
    motif_b(23, 0, 'double')
    for i in range(6):  # quarter-note-triplet hemiola
        beat = 23 * 4 + 2 + i / 3.0
        if i % 2 == 0:
            hit(beat, [TOM_HI, TOM_LO, FLOOR_LO][i // 2], 98 + 5 * (i // 2), RH)
            kick(beat, 96)
        else:
            hit(beat, SNARE, 44 + 6 * i, LH)
    hh_foot(23)
    # bars 24-25: RRLL doubles in sextuplets, accenting every four notes (4 against 6)
    tour = [SNARE, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_HI, TOM_LO, TOM_HMID]
    n = 36
    for i in range(n):
        g, pair = i // 4, i // 2
        hand = RH if pair % 2 == 0 else LH
        drum = tour[g % len(tour)]
        if hand == LH and g % 2 == 0:
            drum = SNARE
        v = lerp(58, 96, i / (n - 1.0))
        if i % 4 == 0:
            v += 18
        elif i % 2 == 1:
            v -= 6
        hit(24 * 4 + i / 6.0, drum, v, hand)
    for i in range(18):
        kick(24 * 4 + i / 3.0, lerp(66, 84, i / 17.0) + (6 if i % 3 == 0 else 0),
             RF if i % 2 == 0 else LF)
    motif_b(25, 2, 'cym')
    motif_b(26, 0, 'orig')
    motif_b(26, 2, 'double')
    hh_foot(26)
    # bar 27: R-L-K climbing up the kit
    b = 27
    pairs = [(FLOOR_LO, FLOOR_HI), (FLOOR_HI, TOM_LO), (TOM_LO, TOM_HMID), (TOM_HMID, TOM_HI)]
    for i in range(24):
        beat = b * 4 + i / 6.0
        v = lerp(62, 118, i / 23.0)
        q, m = i // 6, i % 3
        if m == 0:
            hit(beat, pairs[q][1], v + (8 if i % 6 == 0 else 0), RH)
        elif m == 1:
            hit(beat, pairs[q][0], v - 4, LH)
        else:
            kick(beat, v - 6)


def section_build():
    land(28, 110, CRASH2)
    roll(28, 1, 4, 22, 48)
    for q in (1, 2, 3):
        kick(28 * 4 + q, 48 + 4 * q)
    for q in range(4):
        hit(28 * 4 + q + 0.5, HH_PEDAL, 40, LF)
    roll(29, 0, 4, 48, 72, acc16=starts(MOTIF_A), acc_boost=26)
    for q in range(4):
        kick(29 * 4 + q, 60 + 3 * q)
        hit(29 * 4 + q + 0.5, HH_PEDAL, 44, LF)
    acc30 = starts(A_PERMS[1])
    roll(30, 0, 4, 70, 94, acc16=acc30,
         acc_notes=[TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO, CRASH1], acc_boost=22)
    for p in acc30:
        kick(B16(30, p), 90)
    for q in range(4):
        hit(30 * 4 + q + 0.5, HH_PEDAL, 48, LF)
    roll(31, 0, 2, 96, 110, acc16=(0, 3, 6), acc_notes=[CRASH1, TOM_HI, TOM_LO], acc_boost=12)
    for p in (0, 3, 6):
        kick(B16(31, p), 100)
    run(31 * 4 + 2, 16, 1 / 8.0, 'RL',
        travel([TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO], 16), 100, 122)
    for k in range(4):
        kick(31 * 4 + 2 + k * 0.5, 96 + 4 * k)


def section_climax():
    climax_bar(32, MOTIF_A, [CRASH1, CHINA, CRASH2, CRASH1, SPLASH, CHINA])
    climax_bar(33, A_PERMS[2], [CHINA, CRASH2, CRASH1, CHINA, CRASH2], fill_from=12)
    run(33 * 4 + 3, 8, 1 / 8.0, 'RLRLRLRL', travel([SNARE, TOM_HI, TOM_LO, FLOOR_LO], 8), 92, 118)

    # bar 34: call (hands) and response (feet plus stabs)
    b = 34
    path = travel([TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO], 8)
    for p in range(8):
        hit(B16(b, p), path[p], 112 if p in (0, 3, 6) else 74, RH if p % 2 == 0 else LH)
    kick(B16(b, 0), 100)
    dbl_bass(b, 2, 4, 88, 100)
    for p in (8, 11, 14):
        hit(B16(b, p), CHINA if p == 11 else CRASH2, 116, RH)
        hit(B16(b, p), SNARE, 112, LH)
    # bar 35: the same exchange turned around
    b = 35
    dbl_bass(b, 0, 2, 90, 100)
    for p in (0, 3, 6):
        hit(B16(b, p), CRASH1 if p != 3 else SPLASH, 116, RH)
        hit(B16(b, p), SNARE if p != 3 else FLOOR_HI, 110, LH)
    run(b * 4 + 2, 12, 1 / 6.0, 'RLRLRL',
        travel([FLOOR_LO, FLOOR_HI, TOM_LO, TOM_HMID, TOM_HI, SNARE], 12),
        80, 112, accents=(0, 3, 6, 9), acc_boost=10)
    kick(b * 4 + 2, 96)
    kick(b * 4 + 3, 104)

    # bars 36-37: motif B over double-bass triplets
    dbl_bass(36, 0, 4, 80, 92, per_beat=3)
    motif_b(36, 0, 'cym', feet=False)
    motif_b(36, 2, 'up', feet=False)
    dbl_bass(37, 0, 2, 88, 96, per_beat=3)
    motif_b(37, 0, 'double', feet=False)
    for i in range(6):
        beat = 37 * 4 + 2 + i / 3.0
        if i % 2 == 0:
            hit(beat, [CRASH1, CHINA, CRASH2][i // 2], 116, RH)
            hit(beat, [FLOOR_HI, SNARE, FLOOR_LO][i // 2], 110, LH)
            kick(beat, 112)
        else:
            hit(beat, SNARE, 50 + 10 * i, LH)

    # bar 38: motif A stabs with 32nd-note singles running between them
    b = 38
    rot = [TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO]
    for k, (p, g) in enumerate(zip(starts(MOTIF_A), MOTIF_A)):
        beat = B16(b, p)
        hit(beat, [CRASH1, CRASH2, CHINA][k % 3], 116, RH)
        hit(beat, SNARE, 110, LH)
        kick(beat, 110)
        m = 2 * g - 1
        for j in range(m):
            nb = b * 4 + (p + 0.5 * (j + 1)) / 4.0
            hand = LH if j % 2 == 0 else RH
            drum = rot[(k + j) % len(rot)]
            hit(nb, drum, lerp(60, 92, j / max(1, m - 1)), hand)
    # bar 39: R-L-R-L-K-K sextuplets down the kit
    b = 39
    hand_path = travel([SNARE, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO], 16)
    hi = 0
    for i in range(24):
        ch = 'RLRLKK'[i % 6]
        beat = b * 4 + i / 6.0
        v = lerp(74, 120, i / 23.0)
        if ch == 'K':
            kick(beat, v - 4, RF if i % 6 == 4 else LF)
        else:
            hit(beat, hand_path[hi], v + (8 if i % 6 == 0 else 0), RH if ch == 'R' else LH)
            hi += 1


def section_breakdown():
    b = 40
    hit(160, CRASH1, 124, RH)
    hit(160, CHINA, 116, LH)
    kick(160, 124)
    for q in (1, 2, 3):
        hit(160 + q, HH_PEDAL, 40, LF)
    hit(B16(b, 9), FLOOR_LO, 66, RH)
    hit(B16(b, 12), FLOOR_LO, 74, RH)
    kick(B16(b, 12), 58)
    hit(B16(b, 14), STICK, 62, LH)
    hit(B16(b, 15), STICK, 48, LH)
    b = 41
    acc = starts(MOTIF_A)
    for p in range(12):
        x = p / 11.0
        v = lerp(22, 60, x)
        if p in acc:
            v += lerp(12, 40, x)
        hit(B16(b, p), SNARE, v, RH if p % 2 == 0 else LH)
    run(b * 4 + 3, 8, 1 / 8.0, 'RLRLRLRL',
        [SNARE, SNARE, TOM_HI, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO], 72, 112)
    kick(B16(b, 0), 66)
    kick(B16(b, 8), 72)
    kick(b * 4 + 3, 88)
    kick(b * 4 + 3.5, 96)
    hh_foot(b, vel=44)


def section_final():
    climax_bar(42, MOTIF_A, [CRASH1, CRASH2, CHINA, CRASH1, CRASH2, CHINA], feet=False)
    hh_foot(42, vel=54)
    unison_bar(43, A_PERMS[1], [TOM_HI, TOM_HMID, TOM_HI, TOM_LO, TOM_HMID, CRASH1],
               [FLOOR_HI, FLOOR_LO, FLOOR_HI, FLOOR_LO, FLOOR_HI, SNARE], v_acc=110)
    # bar 44: 32nd-note doubles traveling, with motif accents
    b = 44
    tour = [SNARE, TOM_HI, TOM_HMID, TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_HI, TOM_LO,
            SNARE, TOM_HI, TOM_LO, FLOOR_LO, SNARE, TOM_HMID, FLOOR_HI, FLOOR_LO]
    acc = starts(A_PERMS[3])
    for i in range(32):
        pair = i // 2
        hand = RH if pair % 2 == 0 else LH
        v = lerp(64, 96, i / 31.0)
        if i % 2 == 0 and pair in acc:
            v = 112 + rng.uniform(-2, 4)
            kick(b * 4 + i / 8.0, 104)
        elif i % 2 == 1:
            v -= 8
        hit(b * 4 + i / 8.0, tour[pair], v, hand)
    hh_foot(b, beats=(1, 3), vel=50)
    # bar 45: motif B over double-bass sextuplets
    dbl_bass(45, 0, 4, 70, 88, per_beat=6)
    motif_b(45, 0, 'cym', feet=False)
    motif_b(45, 2, 'double', feet=False)
    # bar 46: the last swell, with motif A crashing through the roll
    roll(46, 0, 4, 64, 114, acc16=starts(MOTIF_A),
         acc_notes=[CRASH1, SNARE, CRASH2, SNARE, CHINA, CRASH1], acc_boost=14, curve=1.3)
    for k in range(8):
        kick(46 * 4 + k * 0.5, lerp(86, 112, k / 7.0))
    # bar 47: stops, then the cascade into the final hit
    b = 47
    stabs = [(0, CRASH1, SNARE), (3, CHINA, FLOOR_HI), (6, CRASH2, SNARE), (9, CRASH1, FLOOR_LO)]
    for k, (p, rc, lc) in enumerate(stabs):
        beat = B16(b, p)
        if k > 0:
            hit(B16(b, p - 1), SNARE, 46 + 6 * k, RH)
            hit(B16(b, p - 0.5), SNARE, 56 + 6 * k, LH)
        hit(beat, rc, 120, RH)
        hit(beat, lc, 116, LH)
        kick(beat, 118)
    run(b * 4 + 3, 8, 1 / 8.0, 'RLRLRLRL',
        [TOM_HI, TOM_HI, TOM_HMID, TOM_LO, TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_LO], 94, 124)
    kick(b * 4 + 3, 104)
    kick(b * 4 + 3.5, 112)
    hit(END_BEAT, CRASH1, 127, RH, dur=RING)
    hit(END_BEAT, CRASH2, 124, LH, dur=RING)
    kick(END_BEAT, 127, dur=1.0)


# ---------------------------------------------------------------- tempo
TEMPO_PTS = [(0, 0.94), (14, 0.96), (16, 0.97), (34, 0.99), (40, 0.99), (56, 1.0), (66, 1.02),
             (72, 1.03), (73, 0.97), (86, 0.95), (88, 0.98), (104, 1.0), (110, 1.03), (112, 1.0),
             (113, 0.97), (124, 1.05), (128, 1.07), (152, 1.07), (158, 1.09), (160, 1.05),
             (161, 0.95), (166, 0.96), (168, 1.0), (180, 1.03), (184, 1.05), (188, 1.08),
             (189, 1.04), (191, 0.97), (192, 0.93), (210, 0.93)]


def rel_tempo(b):
    if b <= TEMPO_PTS[0][0]:
        base = TEMPO_PTS[0][1]
    elif b >= TEMPO_PTS[-1][0]:
        base = TEMPO_PTS[-1][1]
    else:
        base = TEMPO_PTS[-1][1]
        for (b0, r0), (b1, r1) in zip(TEMPO_PTS, TEMPO_PTS[1:]):
            if b0 <= b < b1:
                base = lerp(r0, r1, (b - b0) / (b1 - b0))
                break
    if b >= 188:          # the last bar broadens freely, without phrase surges
        return base
    phase = (b % 8) / 8.0
    surge = 1 + 0.012 * math.sin(2 * math.pi * (phase - 0.55))
    drift = 1 + 0.007 * math.sin(2 * math.pi * b / 37.0 + 1.3) + 0.004 * math.sin(2 * math.pi * b / 11.0 + 0.4)
    return base * surge * drift


RES = 48
TABLE_END = END_BEAT + 12
_cum = [0.0]
for _i in range(TABLE_END * RES):
    _cum.append(_cum[-1] + 1.0 / (RES * rel_tempo((_i + 0.5) / RES)))


def S(b):
    if b <= 0:
        return b / rel_tempo(0.0)
    x = b * RES
    i = int(x)
    if i >= len(_cum) - 1:
        return _cum[-1] + (x - (len(_cum) - 1)) / RES / rel_tempo(TABLE_END)
    return _cum[i] + (_cum[i + 1] - _cum[i]) * (x - i)


PRE = 1.0 / rel_tempo(0.0)          # one silent count-in beat
BPM0 = 60.0 * (S(END_BEAT) + PRE) / FINAL_TIME


def sec(b):
    return 60.0 / BPM0 * (S(b) + PRE)


# ---------------------------------------------------------------- render
def render():
    notes = []
    for b, n, v, limb, off, dur in EV:
        t = sec(b) + off
        if limb in FEET:
            assert n in (KICK, KICK_B, HH_PEDAL)
            t += rng.gauss(-0.002, 0.004)
        else:
            assert n not in (KICK, KICK_B, HH_PEDAL)
            t += rng.gauss(0.0, 0.0055)
            if v < 50:
                t += 0.004      # ghosts sit back
            elif v >= 100:
                t -= 0.003      # accents lean forward
            if limb == LH:
                t += 0.0015
        if b >= END_BEAT:
            t = sec(b)          # the final hit lands squarely
        vv = v + rng.gauss(0, 2.5 if v >= 100 else 3.5)
        vv = int(round(max(1, min(127, vv))))
        notes.append([t, n, vv, limb, dur, True])
    notes.sort(key=lambda x: (x[0], x[1], x[3]))

    # playability: each limb strikes one note at a time, with a physical minimum gap
    MIN_GAP = 0.040
    last = {}
    for nt in notes:
        l = nt[3]
        if l in last and nt[0] - last[l][0] < MIN_GAP:
            if nt[2] > last[l][2]:
                last[l][5] = False
                last[l] = nt
            else:
                nt[5] = False
        else:
            last[l] = nt
    notes = [x for x in notes if x[5]]
    # no two limbs hitting the same note at virtually the same moment
    lastn = {}
    for nt in notes:
        p = lastn.get(nt[1])
        if p is not None and nt[0] - p[0] < 0.015:
            if nt[2] > p[2]:
                p[5] = False
                lastn[nt[1]] = nt
            else:
                nt[5] = False
        else:
            lastn[nt[1]] = nt
    notes = [x for x in notes if x[5]]

    # durations, clipped so a note is never re-struck while it is still held
    nxt = {}
    out = []
    for nt in reversed(notes):
        t, n, v, limb, dur, _ = nt
        if dur is None:
            dur = 1.2 if n in CYMBALS else (0.35 if n in TOMS or n in (SNARE, KICK) else 0.25)
        if n in nxt:
            dur = min(dur, nxt[n] - t - 0.003)
        dur = max(dur, 0.005)
        nxt[n] = t
        out.append((t, n, v, dur))
    out.reverse()
    return out


def write(notes, filename='solo.mid'):
    TPB = 960
    first_beat, last_beat = -1, TABLE_END
    beat_secs = [sec(k) for k in range(first_beat, last_beat + 1)]   # index i -> beat i-1

    def t2tick(t):
        i = bisect.bisect_right(beat_secs, t) - 1
        i = max(0, min(len(beat_secs) - 2, i))
        frac = (t - beat_secs[i]) / (beat_secs[i + 1] - beat_secs[i])
        return max(0, int(round((i + frac) * TPB)))

    evs = []
    for i in range(len(beat_secs) - 1):
        us = int(round((beat_secs[i + 1] - beat_secs[i]) * 1e6))
        evs.append((i * TPB, -1, 0, us))
    end_tick = 0
    for t, n, v, dur in notes:
        on = t2tick(t)
        off = max(on + 1, t2tick(t + dur))
        evs.append((on, 1, n, v))
        evs.append((off, 0, n, 0))
        end_tick = max(end_tick, off)
    evs = [e for e in evs if e[0] <= end_tick]
    evs.sort()

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=112, time=0))
    tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
    now = 0
    for tick, kind, n, v in evs:
        dt = tick - now
        now = tick
        if kind == -1:
            tr.append(mido.MetaMessage('set_tempo', tempo=v, time=dt))
        elif kind == 1:
            tr.append(mido.Message('note_on', channel=9, note=n, velocity=v, time=dt))
        else:
            tr.append(mido.Message('note_off', channel=9, note=n, velocity=0, time=dt))
    tr.append(mido.MetaMessage('end_of_track', time=TPB // 4))
    mid.save(filename)


def main():
    intro()
    section_groove()
    section_linear()
    section_quiet()
    section_triplets()
    section_build()
    section_climax()
    section_breakdown()
    section_final()
    write(render())


if __name__ == '__main__':
    main()
