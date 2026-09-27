#!/usr/bin/env python3
"""
drum_solo.py - a two-minute General MIDI drum solo written with mido.

The script writes solo.mid in the current directory. All drum notes are on
MIDI channel 10 (mido channel 9).

Form: 48 bars of 4/4 at 96 BPM, which is exactly 120 seconds.
  bars  0-3   Intro: the motif is stated on the toms over a hi-hat foot pulse.
  bars  4-11  Swung hi-hat groove with ghost notes. The motif returns as fills.
  bars 12-19  Ride groove. The motif is sequenced, augmented and built to a peak.
  bars 20-27  Latin colour: the dynamics drop, with a foot clave on woodblock,
              cowbell and agogo, and the motif on timbales and congas.
  bars 28-35  Tom solo in triplets and sextuplets. It uses linear hand-hand-foot
              figures and flam accents.
  bars 36-39  Release: a soft jazz ride with the motif on side stick. A roll
              leads out of it.
  bars 40-46  Climax: ride bell, double bass and the motif with crashes.
  bar  47     Final unison hit, left to ring.

Feel: swung sixteenths. Cymbals push slightly ahead of the beat, backbeats lay
back, and ghost notes sit just behind. Every note belongs to one limb (R, L,
RF, LF). A resolver keeps each limb to one stroke at a time, so no more than
two hands and two feet ever strike at once.
"""
import random
import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

TPB = 480
BPM = 96
BAR = 4 * TPB
CH = 9
TOTAL_TICKS = int(round(120 * BPM / 60 * TPB))  # 92160 ticks = 120 s

# General MIDI percussion notes
KICK2, KICK, SIDE, SNARE = 35, 36, 37, 38
F_LO, HHC, F_HI, HHP, T_LO, HHO, T_LM, T_HM = 41, 42, 43, 44, 45, 46, 47, 48
CRASH, T_HI, RIDE, CHINA, BELL, SPLASH, COWBELL, CRASH2 = 49, 50, 51, 52, 53, 55, 56, 57
HI_BONGO, LO_BONGO, MUTE_CONGA, OPEN_CONGA, LO_CONGA = 60, 61, 62, 63, 64
HI_TIMB, LO_TIMB, HI_AGOGO, LO_AGOGO = 65, 66, 67, 68
WOOD_HI, WOOD_LO, TRI_OPEN = 76, 77, 81

TOMS = [T_HI, T_HM, T_LO, F_LO]
ORCH6 = [SNARE, T_HI, T_HM, T_LO, F_HI, F_LO]
TIMB = [HI_TIMB, HI_BONGO, LO_BONGO, LO_TIMB]
CONGAS = [OPEN_CONGA, MUTE_CONGA, LO_CONGA, LO_TIMB]

rng = random.Random(19640527)
events = []  # [tick, note, vel, limb, role, dyn]
SW = 0.56    # swing ratio for sixteenths

# Deliberate placement per role, in ticks (480 per beat).
ROLE_OFF = {'hat': -6, 'ride': -6, 'back': 9, 'ghost': 3, 'kick': 0,
            'tom': 0, 'perc': -3, 'cym': 0, 'foot': 4, 'roll': 0}
MIN_GAP = 55  # minimum ticks between two strokes of the same limb


def other(h):
    return 'L' if h == 'R' else 'R'


def gt(bar, idx, div=4):
    """Tick position of grid index idx (div steps per beat) within a bar."""
    beat, sub = divmod(idx, div)
    base = bar * BAR + beat * TPB
    if div == 4:
        off = [0, SW * 240, 240, 240 + SW * 240][sub]
    else:
        off = sub * TPB / div
    return base + off


def add(tick, note, vel, limb, role, dyn=True):
    events.append([tick, note, vel, limb, role, dyn])


def hit(bar, s, note, vel, limb, role, div=4, dyn=True):
    add(gt(bar, s, div), note, vel, limb, role, dyn)


# ---------------------------------------------------------------- motif
# The motif "DUM . . da da . DUM" as (offset, contour 0=high..3=low, accent).
MOTIF = [(0, 0, 2), (3, 1, 1), (4, 1, 1), (6, 3, 2)]
MOTIF_T = [(0, 0, 2), (2, 1, 1), (3, 1, 1), (5, 3, 2)]  # triplet reading
ACCV = {2: 118, 1: 94, 0: 76}
_crash = [0]


def next_crash():
    _crash[0] += 1
    return CRASH if _crash[0] % 2 else CRASH2


def motif(bar, start, orch, div=4, shape=None, aug=1, invert=False, shift=0,
          level=1.0, kick=True, crash=False, ghostfill=False, ghost_note=SNARE,
          hand='R', flam=False):
    shape = shape or MOTIF
    last = shape[-1][0]
    notes = []
    for off, c, acc in shape:
        cc = 3 - c if invert else c
        cc = max(0, min(len(orch) - 1, cc + shift))
        notes.append((start + off * aug, acc, orch[cc]))
    occ = {p for p, _, _ in notes}
    hits = list(notes)
    if ghostfill:
        for p in range(start + 1, start + last * aug):
            if p not in occ:
                hits.append((p, -1, ghost_note))
    hits.sort()
    h = hand
    for p, acc, note in hits:
        t = gt(bar, p, div)
        if acc < 0:
            add(t, note, 26 + (5 if (p - start) % 2 == 0 else 0), h, 'ghost')
            h = other(h)
            continue
        v = min(127, ACCV[acc] * level)
        if note in (KICK, KICK2):
            add(t, note, v, 'RF', 'kick')
            continue
        if crash and acc == 2:
            add(t, next_crash(), min(127, v + 6), 'R', 'cym')
            add(t, note, v, 'L', 'tom')
            if kick:
                add(t, KICK, v, 'RF', 'kick')
            h = 'R'
            continue
        if flam and acc == 2:
            add(t - 24, note, 44, other(h), 'tom')
        add(t, note, v, h, 'tom')
        if kick and acc == 2:
            add(t, KICK, v, 'RF', 'kick')
        h = other(h)


def tom_run(bar, i0, i1, drums, div=4, v0=80, v1=110, hand='R'):
    n = i1 - i0
    h = hand
    for k in range(n):
        d = drums[min(len(drums) - 1, k * len(drums) // n)]
        v = v0 + (v1 - v0) * k / max(1, n - 1)
        add(gt(bar, i0 + k, div), d, v, h, 'tom')
        h = other(h)


def roll(bar, i0, i1, note, div, v0, v1, hand='R'):
    n = i1 - i0
    h = hand
    for k in range(n):
        v = v0 + (v1 - v0) * k / max(1, n - 1)
        add(gt(bar, i0 + k, div), note, v, h, 'roll')
        h = other(h)


# ---------------------------------------------------------------- grooves
def groove_hat(bar, kicks, ghosts, hand_end=16, sixteenths=False,
               open_last=False, crash_first=False, cym_at=None):
    cym_at = cym_at or {}
    step = 1 if sixteenths else 2
    for s in range(0, 16, step):
        if s >= hand_end:
            break
        if s == 0 and crash_first:
            hit(bar, 0, CRASH, 112, 'R', 'cym')
        elif s in cym_at:
            hit(bar, s, cym_at[s][0], cym_at[s][1], 'R', 'cym')
        elif open_last and s == 14:
            hit(bar, 14, HHO, 84, 'R', 'hat')
        elif open_last and s == 15:
            continue
        else:
            v = 90 if s % 4 == 0 else (68 if s % 2 == 0 else 46)
            hit(bar, s, HHC, v, 'R', 'hat')
    if open_last:
        hit(bar + 1, 0, HHP, 64, 'LF', 'foot')
    for s in (4, 12):
        if s < hand_end:
            hit(bar, s, SNARE, 106, 'L', 'back')
    for s in ghosts:
        if s < hand_end:
            hit(bar, s, SNARE, 30, 'L', 'ghost')
    for s in kicks:
        if s < hand_end:
            hit(bar, s, KICK, 104 if s == 0 else 92, 'RF', 'kick')


def groove_ride(bar, kicks, ghosts, hand_end=16, bell=False, crash_first=False):
    for s in range(0, 16, 2):
        if s >= hand_end:
            break
        if s == 0 and crash_first:
            hit(bar, 0, CRASH2, 112, 'R', 'cym')
            continue
        if s % 4 == 0:
            n, v = (BELL, 92) if bell else (RIDE, 90)
        else:
            n, v = RIDE, 66
        hit(bar, s, n, v, 'R', 'ride')
    if not bell:
        for s in (7, 11):
            if s < hand_end:
                hit(bar, s, RIDE, 52, 'R', 'ride')
    for s in (4, 12):
        hit(bar, s, HHP, 62, 'LF', 'foot')
        if s < hand_end:
            hit(bar, s, SNARE, 108, 'L', 'back')
    for s in ghosts:
        if s < hand_end:
            hit(bar, s, SNARE, 32, 'L', 'ghost')
    for s in kicks:
        if s < hand_end:
            hit(bar, s, KICK, 104 if s == 0 else 90, 'RF', 'kick')


CLAVE32 = [0, 3, 6, 10, 12]
TUMBAO = [(2, MUTE_CONGA, 46), (4, MUTE_CONGA, 38), (6, OPEN_CONGA, 86),
          (7, OPEN_CONGA, 78), (10, MUTE_CONGA, 46), (12, MUTE_CONGA, 38),
          (14, LO_CONGA, 90), (15, LO_CONGA, 84)]
BONGO = [(0, HI_BONGO, 70), (2, HI_BONGO, 50), (4, LO_BONGO, 62), (6, HI_BONGO, 80),
         (8, HI_BONGO, 70), (10, HI_BONGO, 50), (12, LO_BONGO, 62), (14, LO_BONGO, 86)]
AGOGO = [(0, HI_AGOGO, 88), (2, LO_AGOGO, 64), (3, HI_AGOGO, 70), (6, HI_AGOGO, 80),
         (8, LO_AGOGO, 84), (10, HI_AGOGO, 66), (11, LO_AGOGO, 62), (14, HI_AGOGO, 80)]


def latin(bar, hand_end=16, rh='bell', lh=None, kick_extra=False):
    for s in CLAVE32:
        hit(bar, s, WOOD_HI, 74, 'LF', 'perc')
    for s in [6, 12] + ([14] if kick_extra else []):
        hit(bar, s, KICK, 86, 'RF', 'kick')
    if rh == 'bell':
        for s in range(0, 16, 2):
            if s < hand_end:
                hit(bar, s, COWBELL, 84 if s % 4 == 0 else 58, 'R', 'perc')
    else:
        for s, n, v in AGOGO:
            if s < hand_end:
                hit(bar, s, n, v, 'R', 'perc')
    pat = TUMBAO if lh == 'conga' else BONGO if lh == 'bongo' else []
    for s, n, v in pat:
        if s < hand_end:
            hit(bar, s, n, v, 'L', 'perc')


def feet_ost(bar, rf=True, lf=True):
    """Triplet-feel foot ostinato for the tom solo."""
    if rf:
        for b in range(4):
            hit(bar, b * 3, KICK, 78, 'RF', 'kick', div=3)
        hit(bar, 11, KICK, 60, 'RF', 'kick', div=3)
    if lf:
        for i in (3, 9):
            hit(bar, i, HHP, 66, 'LF', 'foot', div=3)


def jazz_ride(bar, beats, vel=58):
    for b in beats:
        hit(bar, b * 3, RIDE, vel, 'R', 'ride', div=3)
        if b in (1, 3):
            hit(bar, b * 3 + 2, RIDE, vel - 16, 'R', 'ride', div=3)


def climax_groove(bar, hand_end=16, crash_first=False, dk_beats=(),
                  kicks=(0, 3, 6, 8, 10, 14), cym_at=None):
    cym_at = cym_at or {}
    for s in range(0, 16, 2):
        if s >= hand_end:
            break
        if s == 0 and crash_first:
            hit(bar, 0, CRASH, 118, 'R', 'cym')
        elif s in cym_at:
            hit(bar, s, cym_at[s][0], cym_at[s][1], 'R', 'cym')
        else:
            hit(bar, s, BELL if s % 4 == 0 else RIDE,
                100 if s % 4 == 0 else 76, 'R', 'ride')
    for s in (4, 12):
        if s < hand_end:
            hit(bar, s, SNARE, 118, 'L', 'back')
    for s in (3, 7, 9, 15):
        if s < hand_end:
            hit(bar, s, SNARE, 34, 'L', 'ghost')
    for s in kicks:
        if s // 4 not in dk_beats:
            hit(bar, s, KICK, 104, 'RF', 'kick')
    for b in dk_beats:
        for k in range(4):
            s = b * 4 + k
            if k % 2 == 0:
                hit(bar, s, KICK, 98, 'RF', 'kick')
            else:
                hit(bar, s, KICK2, 92, 'LF', 'kick')
    for s in (4, 12):
        if s // 4 not in dk_beats:
            hit(bar, s, HHP, 70, 'LF', 'foot')


# ================================================================ the solo
# ---- Intro (bars 0-3)
SW = 0.56
for b in range(4):
    for beat in range(4):
        hit(b, beat * 4, HHP, 56 if beat % 2 else 46, 'LF', 'foot')
motif(0, 0, TOMS, level=0.85)
hit(0, 10, KICK, 60, 'RF', 'kick')
hit(0, 12, SIDE, 72, 'L', 'back')
hit(0, 15, SNARE, 28, 'R', 'ghost')
motif(1, 0, TOMS, level=0.9)
motif(1, 8, [SNARE, T_HI, T_HM, T_LO], invert=True, level=0.9)  # rising answer
motif(2, 0, TOMS, ghostfill=True)
motif(2, 8, ORCH6, shift=2, ghostfill=True)
motif(3, 0, ORCH6, level=1.0)
tom_run(3, 8, 16, TOMS, v0=70, v1=112, hand='R')
hit(3, 8, KICK, 70, 'RF', 'kick')
hit(3, 12, KICK, 80, 'RF', 'kick')

# ---- Groove A (bars 4-11)
KP_A = [[0, 6, 10], [0, 3, 8, 10], [0, 6, 8, 11], [0, 7, 10, 13], [0, 2, 6, 10]]
GP_A = [(7, 9, 15), (3, 7, 9), (7, 11, 15), (2, 7, 9, 14)]
groove_hat(4, KP_A[0], GP_A[0], crash_first=True)
groove_hat(5, KP_A[1], GP_A[1], open_last=True)
groove_hat(6, KP_A[0], GP_A[2])
groove_hat(7, KP_A[2], GP_A[0], hand_end=8)
motif(7, 8, TOMS)
groove_hat(8, KP_A[0], GP_A[0], sixteenths=True, crash_first=True)
groove_hat(9, KP_A[3], GP_A[3], sixteenths=True, open_last=True)
groove_hat(10, KP_A[4], GP_A[2], sixteenths=True, cym_at={14: (SPLASH, 96)})
groove_hat(11, KP_A[1], GP_A[1], sixteenths=True, hand_end=9)
motif(11, 9, TOMS, flam=True)  # displaced by a sixteenth

# ---- Ride build (bars 12-19)
SW = 0.58
KP_B = [[0, 3, 6, 10, 11], [0, 6, 8, 10, 14], [0, 2, 7, 10, 13], [0, 3, 8, 11, 14]]
GP_B = [(2, 7, 9, 11, 15), (3, 6, 9, 14, 15), (7, 9, 11, 15)]
groove_ride(12, KP_B[0], GP_B[0], crash_first=True)
groove_ride(13, KP_B[1], GP_B[1])
groove_ride(14, KP_B[0], GP_B[2])
groove_ride(15, [], [], hand_end=0)
motif(15, 0, ORCH6, shift=1)
motif(15, 8, ORCH6, shift=2, invert=True)
groove_ride(16, KP_B[2], GP_B[0], bell=True, crash_first=True)
groove_ride(17, KP_B[3], GP_B[1], bell=True, hand_end=8)
motif(17, 8, TOMS, crash=True)
for beat in range(4):
    hit(18, beat * 4, HHP, 64, 'LF', 'foot')
motif(18, 0, TOMS, aug=2, crash=True, ghostfill=True)  # augmentation
hit(18, 14, SNARE, 90, 'L', 'tom')
hit(18, 15, SNARE, 96, 'R', 'tom')
hit(18, 14, KICK, 88, 'RF', 'kick')
tom_run(19, 0, 12, [T_HI, T_HM, T_LO, F_HI, F_LO], div=6, v0=85, v1=110)
hit(19, 0, KICK, 96, 'RF', 'kick', div=6)
hit(19, 6, KICK, 96, 'RF', 'kick', div=6)
roll(19, 16, 32, SNARE, 8, 60, 122)
hit(19, 4, HHP, 60, 'LF', 'foot')
hit(19, 8, KICK, 90, 'RF', 'kick')
hit(19, 12, KICK, 100, 'RF', 'kick')
hit(19, 14, KICK, 105, 'RF', 'kick')
hit(19, 15, KICK2, 108, 'LF', 'kick')

# ---- Latin contrast (bars 20-27)
SW = 0.5
hit(20, 0, CRASH, 116, 'R', 'cym', dyn=False)
hit(20, 0, KICK, 110, 'RF', 'kick', dyn=False)
latin(20)
latin(21, hand_end=12)
for i, n in enumerate([HI_TIMB, HI_TIMB, LO_TIMB, LO_TIMB]):
    hit(21, 12 + i, n, 70 + 8 * i, 'R' if i % 2 == 0 else 'L', 'tom')
latin(22, lh='conga')
latin(23, lh='conga', hand_end=8)
motif(23, 8, TIMB)
latin(24, rh='agogo', lh='conga')
latin(25, rh='agogo', lh='conga', hand_end=8)
motif(25, 8, CONGAS)
latin(26, rh='agogo', lh='bongo', kick_extra=True)
latin(27, hand_end=0, kick_extra=True)
motif(27, 0, TIMB, ghostfill=True, ghost_note=HI_TIMB)
motif(27, 8, TIMB, invert=True, flam=True)

# ---- Tom solo (bars 28-35)
for b in range(28, 34):
    feet_ost(b)
motif(28, 0, TOMS, div=3, shape=MOTIF_T, crash=True)
tom_run(28, 6, 12, TOMS, div=3, v0=80, v1=105, hand='R')
motif(29, 0, TOMS, div=3, shape=MOTIF_T, invert=True)
h = 'R'
for i in range(6, 12):
    if i in (8, 11):
        hit(29, i, F_LO, 112, h, 'tom', div=3)
    else:
        hit(29, i, SNARE, 50, h, 'ghost', div=3)
    h = other(h)
motif(30, 0, ORCH6, div=3, shape=MOTIF_T)
motif(30, 6, ORCH6, div=3, shape=MOTIF_T, shift=2)
motif(31, 0, TOMS, div=3, shape=MOTIF_T, ghostfill=True)
motif(31, 6, ORCH6, div=3, shape=MOTIF_T, shift=2, ghostfill=True)
motif(32, 0, TOMS, div=6, shape=MOTIF_T, aug=2, ghostfill=True)
motif(32, 12, TOMS, div=6, shape=MOTIF_T, aug=2, ghostfill=True, shift=0)
motif(33, 0, ORCH6, div=6, shape=MOTIF_T, aug=2, shift=1, invert=True, ghostfill=True)
motif(33, 12, ORCH6, div=6, shape=MOTIF_T, aug=2, shift=2, ghostfill=True)
feet_ost(34, rf=False)
feet_ost(35, rf=False)
PAIRS = [(T_HI, T_HM), (T_HM, T_LO), (T_LO, F_HI), (F_HI, F_LO)]
for g in range(8):  # linear R-L-foot figure in sextuplets
    a, b2 = PAIRS[g % 4]
    v = 72 + 40 * g / 7
    hit(34, 3 * g, a, v + 8, 'R', 'tom', div=6)
    hit(34, 3 * g + 1, b2, v, 'L', 'tom', div=6)
    hit(34, 3 * g + 2, KICK, v, 'RF', 'kick', div=6)
for g in range(8):  # the same figure at double speed
    a, b2 = PAIRS[(3 - g) % 4]
    if 3 * g in (0, 12):
        hit(35, 3 * g, CRASH if g == 0 else CRASH2, 120, 'R', 'cym', div=12)
        hit(35, 3 * g, KICK, 115, 'RF', 'kick', div=12)
    else:
        hit(35, 3 * g, a, 104, 'R', 'tom', div=12)
    hit(35, 3 * g + 1, b2, 96, 'L', 'tom', div=12)
    hit(35, 3 * g + 2, KICK, 100, 'RF', 'kick', div=12)
lead = 'L'
for i, n, fl in [(6, T_HI, True), (7, T_HM, False), (8, T_LO, True),
                 (9, F_HI, True), (10, F_LO, False), (11, SNARE, True)]:
    t = gt(35, i, 3)
    if fl:
        add(t - 24, n, 46, other(lead), 'tom')
        add(t, n, 116, lead, 'tom')
        add(t, KICK, 112, 'RF', 'kick')
    else:
        add(t, n, 92, lead, 'tom')
    lead = other(lead)

# ---- Release (bars 36-39)
SW = 0.62
hit(36, 0, CRASH, 108, 'R', 'cym', dyn=False)
hit(36, 0, KICK, 100, 'RF', 'kick', dyn=False)
hit(36, 0, TRI_OPEN, 72, 'L', 'perc', dyn=False)
for b in range(36, 40):
    for i in (3, 9):
        hit(b, i, HHP, 60, 'LF', 'foot', div=3)
    for i in (0, 3, 6, 9):
        if not (b == 36 and i == 0):
            hit(b, i, KICK, 34, 'RF', 'kick', div=3)
jazz_ride(36, [1, 2, 3])
hit(36, 9, SIDE, 58, 'L', 'back', div=3)
jazz_ride(37, [0, 1])
motif(37, 6, [SIDE, T_HM, T_LO, F_LO], div=3, shape=MOTIF_T,
      level=0.55, kick=False, hand='L')
jazz_ride(38, [0, 1, 2, 3])
hit(38, 2, SNARE, 24, 'L', 'ghost', div=3)
hit(38, 5, SNARE, 26, 'L', 'ghost', div=3)
hit(38, 8, SNARE, 52, 'L', 'back', div=3)
hit(38, 9, SIDE, 58, 'L', 'back', div=3)
hit(38, 11, KICK, 70, 'RF', 'kick', div=3)
jazz_ride(39, [0, 1])
roll(39, 12, 24, SNARE, 6, 28, 112)
hit(39, 6, KICK, 70, 'RF', 'kick', div=3)
hit(39, 9, KICK, 90, 'RF', 'kick', div=3)

# ---- Climax (bars 40-46)
SW = 0.54
climax_groove(40, crash_first=True, dk_beats=(3,))
climax_groove(41, hand_end=8, kicks=(0, 3, 6))
motif(41, 8, TOMS, crash=True, flam=True)
climax_groove(42, crash_first=True, dk_beats=(1, 3), cym_at={14: (CHINA, 110)})
climax_groove(43, hand_end=0, dk_beats=(0, 1, 2, 3), kicks=())
motif(43, 0, ORCH6, shift=1, crash=True)
motif(43, 8, ORCH6, shift=1, invert=True, crash=True)
climax_groove(44, hand_end=0, dk_beats=(0, 1, 2, 3), kicks=())
motif(44, 0, TOMS, aug=2, crash=True)
motif(45, 0, ORCH6, aug=2, invert=True, shift=1, crash=True, ghostfill=True)
for beat in range(4):
    hit(45, beat * 4, KICK, 100, 'RF', 'kick')
for s in (4, 12):
    hit(45, s, HHP, 70, 'LF', 'foot')
tom_run(45, 13, 16, [F_HI, F_LO, F_LO], v0=100, v1=115, hand='R')
tom_run(46, 0, 12, [T_HI, T_HM, T_LO, F_HI, F_LO], div=6, v0=92, v1=122)
for i in (0, 3, 6, 9):
    hit(46, i, KICK, 104, 'RF', 'kick', div=6)
motif(46, 8, ORCH6, shift=1, crash=True, flam=True)  # the motif, one last time
hit(46, 10, KICK2, 96, 'LF', 'kick')

# ---- Final hit (bar 47)
hit(47, 0, CRASH, 127, 'R', 'cym', dyn=False)
hit(47, 0, CRASH2, 127, 'L', 'cym', dyn=False)
hit(47, 0, KICK, 127, 'RF', 'kick', dyn=False)
hit(47, 0, KICK2, 120, 'LF', 'kick', dyn=False)
hit(47, 8, TRI_OPEN, 48, 'L', 'perc', dyn=False)

# ================================================================ render
ENV = [(0, 0.72), (3.99, 0.9), (4, 0.9), (11.99, 1.0), (12, 0.92), (19.99, 1.08),
       (20, 0.72), (27.99, 0.9), (28, 0.82), (33.99, 0.95), (35.99, 1.1),
       (36, 0.55), (39, 0.6), (40, 1.0), (48, 1.1)]


def env(tick):
    b = tick / BAR
    for (b0, m0), (b1, m1) in zip(ENV, ENV[1:]):
        if b0 <= b <= b1:
            return m0 + (m1 - m0) * (b - b0) / (b1 - b0)
    return ENV[-1][1]


final = []
for t, n, v, limb, role, dyn in events:
    t2 = t + ROLE_OFF.get(role, 0) + rng.gauss(0, 1.5)
    t2 = max(0, min(TOTAL_TICKS - 200, int(round(t2))))
    vv = v * (env(t) if dyn else 1.0) + rng.randint(-3, 3)
    lo = 18 if role == 'ghost' else 8
    vv = int(max(lo, min(127, round(vv))))
    final.append((t2, n, vv, limb))

# Playability: each limb gets one stroke at a time. Louder notes win.
final.sort(key=lambda e: (-e[2], e[0], e[1], e[3]))
per_limb = {}
kept = []
for e in final:
    lst = per_limb.setdefault(e[3], [])
    if any(abs(e[0] - x) < MIN_GAP for x in lst):
        continue
    lst.append(e[0])
    kept.append(e)

kept.sort(key=lambda e: (e[0], e[1]))
uniq, seen = [], set()
for e in kept:
    k = (e[0], e[1])
    if k not in seen:
        seen.add(k)
        uniq.append(e)

vel_of = {(t, n): v for t, n, v, _ in uniq}
times = {}
for t, n, v, _ in uniq:
    times.setdefault(n, []).append(t)

DUR = 90
out = []
for n in sorted(times):
    ts = sorted(times[n])
    for i, t in enumerate(ts):
        off = t + DUR
        if i + 1 < len(ts) and off >= ts[i + 1]:
            off = ts[i + 1] - 1
        out.append((off, 0, n, 0))
        out.append((t, 1, n, vel_of[(t, n)]))
out.sort()

mid = MidiFile(type=0, ticks_per_beat=TPB)
tr = MidiTrack()
mid.tracks.append(tr)
tr.append(MetaMessage('track_name', name='Drum Solo', time=0))
tr.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
tr.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
tr.append(Message('control_change', channel=CH, control=7, value=110, time=0))
tr.append(Message('control_change', channel=CH, control=10, value=64, time=0))
tr.append(Message('control_change', channel=CH, control=91, value=45, time=0))

prev = 0
for tick, typ, n, v in out:
    dt = tick - prev
    prev = tick
    if typ == 1:
        tr.append(Message('note_on', channel=CH, note=n, velocity=v, time=dt))
    else:
        tr.append(Message('note_off', channel=CH, note=n, velocity=0, time=dt))
tr.append(MetaMessage('end_of_track', time=max(0, TOTAL_TICKS - prev)))

mid.save('solo.mid')
