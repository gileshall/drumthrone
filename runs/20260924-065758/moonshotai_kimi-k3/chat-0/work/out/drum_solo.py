#!/usr/bin/env python3
"""
drum_solo.py -- "Two Minutes at the Kit"

Writes solo.mid: a ~2 minute General MIDI drum solo on channel 10,
built deterministically with mido (no other MIDI libraries).

Form (50 bars of 4/4 at 98 BPM):
  bars  0- 3  Statement      motif A on snare, then re-orchestrated to toms
  bars  4-11  Groove         swung funk pocket; motif fragments creep in
  bars 12-19  Build          motif A fragmented/sequenced on toms, 3-over-4
                             hemiola accents, release into sparse shots
  bars 20-27  Peak groove    heavy backbeat, china color, motif A recap (bar 26)
  bars 28-33  Breakdown      motif B (son clave): claves -> congas -> cross-stick
  bars 34-41  Double-time    16th-note rolls with shifting accent groups,
                             then motif A in rhythmic augmentation (bars 40-41)
  bars 42-47  Climax         shout shots, hemiola fills, stop-time tension,
                             ritardando up the final climb
  bars 48-49  Finale         one fortissimo unison hit, cymbal ring-out

Playability: every stroke is assigned to a limb (RH/LH/RF/LF) and a limb may
not re-strike faster than a minimum interval, so at most two hands and two
feet ever sound at once.  Swing ratios, lay-back/push offsets and ghost vs.
accent velocities are deliberate per-section feels, not random jitter (the
tiny humanization noise is seeded, so the file is identical on every run).
"""

import math
import random

import mido

# ============================ engine =======================================

TPQ = 480
STEP = TPQ // 4          # one 16th note
BAR_T = TPQ * 4
BPM = 98.0
CH = 9                   # MIDI channel 10 (zero-based)

rng = random.Random(20110522)

# General MIDI percussion map
KICK = 36
XSTK = 37
SNR = 38
T_LF, T_HF, T_LO, T_LM, T_HM, T_HI = 41, 43, 45, 47, 48, 50
HAT_C, HAT_P, HAT_O = 42, 44, 46
CR1, RIDE, CHINA, BELL, SPL, CR2 = 49, 51, 52, 53, 55, 57
CG_H, CG_L, MAR, CLAV, TRI = 63, 64, 70, 75, 81

TOMS = (T_LF, T_HF, T_LO, T_LM, T_HM, T_HI)
CYMS = (HAT_C, HAT_O, RIDE, BELL, CR1, CR2, CHINA, SPL, TRI)

events = []              # (on_tick, off_tick, note, velocity)
limb_free = {}           # limb -> tick of its last stroke
MIN_GAP = {'RH': 70, 'LH': 70, 'RF': 60, 'LF': 140}   # ticks
_last_auto = ['LH']

PREF = {RIDE: 'RH', BELL: 'RH', HAT_C: 'RH', HAT_O: 'RH', CHINA: 'RH',
        CR1: 'LH', CR2: 'LH', SPL: 'LH', TRI: 'LH', CLAV: 'LH',
        MAR: 'RH', XSTK: 'RH'}


def role_of(note):
    if note == KICK:
        return 'kick'
    if note in (SNR, XSTK):
        return 'snr'
    if note in TOMS:
        return 'tom'
    if note in CYMS:
        return 'cym'
    return 'perc'


def S(bar, step):
    """Absolute 16th-step index."""
    return bar * 16 + step


def base_tick(s):
    return (s // 4) * TPQ + (s % 4) * STEP


def auto_limb(note, accent, t):
    if note == KICK:
        return 'RF'
    if note == HAT_P:
        return 'LF'
    p = PREF.get(note)
    if p:
        return p
    # generic hand-to-hand sticking; accents prefer the strong hand
    h = 'RH' if _last_auto[0] == 'LH' else 'LH'
    if accent and t - limb_free.get('RH', -100000) >= MIN_GAP['RH']:
        h = 'RH'
    _last_auto[0] = h
    return h


def hit(s, note, vel, dur, feel, limb=None, accent=False, gap=None):
    """Schedule one stroke; returns False if no limb could play it."""
    t = base_tick(s)
    r = s % 4
    if r == 2:            # "&" of a beat: 8th-note swing
        t += feel['sw8']
    elif r % 2 == 1:      # "e"/"a": 16th-note swing
        t += feel['sw16']
    t += feel[role_of(note)]                     # deliberate push/lay-back
    t += int(round(rng.gauss(0.0, feel['hum'])))  # seeded micro-humanization
    if t < 0:
        t = 0
    v = int(round(vel + rng.gauss(0.0, 3.0)))
    v = 1 if v < 1 else (127 if v > 127 else v)
    if limb is None:
        limb = auto_limb(note, accent, t)
    need = MIN_GAP[limb] if gap is None else gap
    if t - limb_free.get(limb, -100000) < need:
        if limb in ('RH', 'LH'):
            alt = 'LH' if limb == 'RH' else 'RH'
            need_a = MIN_GAP[alt] if gap is None else gap
            if t - limb_free.get(alt, -100000) >= need_a:
                limb = alt
            else:
                return False
        else:
            return False
    limb_free[limb] = t
    events.append((t, t + dur, note, v))
    return True


# Per-section feels: swing amounts (ticks) and role micro-timing.
#   snr > 0 lays the backbeat behind the beat; snr < 0 drives on top.
F_STMT = dict(sw8=30, sw16=18, kick=-6, snr=8,  tom=4,  cym=0,  perc=0, hum=2.5)
F_GR = dict(sw8=55, sw16=31, kick=-6, snr=12, tom=6,  cym=2,  perc=2, hum=2.5)
F_PK = dict(sw8=26, sw16=12, kick=-8, snr=-2, tom=0,  cym=-2, perc=0, hum=2.2)
F_BR = dict(sw8=72, sw16=45, kick=0,  snr=16, tom=8,  cym=4,  perc=6, hum=3.0)
F_DT = dict(sw8=10, sw16=0,  kick=-8, snr=-4, tom=-4, cym=-2, perc=0, hum=2.0)

# Motif A: syncopated one-bar phrase (step, dynamic)
MA = [(0, 'A'), (3, 'g'), (4, 'm'), (6, 'g'), (10, 'A'), (11, 'g'), (14, 'm')]
# Motif B: 3-2 son clave
MB = [(0, 'A'), (3, 'm'), (6, 'A'), (10, 'm'), (12, 'A')]

MARKERS = [(0, 'Statement'), (4, 'Groove'), (12, 'Build'), (20, 'Peak Groove'),
           (28, 'Breakdown'), (34, 'Double-Time'), (42, 'Climax'), (48, 'Finale')]

# ============================ sections =====================================


def statement():
    """Bars 0-3: motif A stated, varied, fragmented; fill into the groove."""
    F = F_STMT
    for b in (0, 1):
        for st, d in MA:
            hit(S(b, st), SNR, {'A': 102, 'm': 82, 'g': 34}[d], 90, F)
        for st in (0, 8):
            hit(S(b, st), KICK, 96, 90, F)
        for st in (4, 12):
            hit(S(b, st), HAT_P, 56, 60, F)
    hit(S(0, 0), TRI, 64, 2400, F)          # opening shimmer
    hit(S(1, 10), KICK, 96, 90, F)          # variation: kick doubles accent

    for st, d in MA:                        # accents move to the toms
        if d == 'A':
            hit(S(2, st), {0: T_HI, 10: T_HM}[st], 104, 100, F)
        else:
            hit(S(2, st), SNR, {'m': 82, 'g': 34}[d], 90, F)
    for st in (0, 8):
        hit(S(2, st), KICK, 96, 90, F)
    for st in (4, 12):
        hit(S(2, st), HAT_P, 56, 60, F)

    for st, d in MA[:4]:                    # fragmentation: first half only
        hit(S(3, st), SNR, {'A': 104, 'm': 84, 'g': 36}[d], 90, F)
    for st in (0, 8):
        hit(S(3, st), KICK, 98, 90, F)
    for st in (4, 12):
        hit(S(3, st), HAT_P, 56, 60, F)
    fill_v = [64, 72, 80, 88, 96, 104, 112]
    for i, st in enumerate(range(8, 15)):   # crescendo fill, ends on beat "a"
        note = T_HF if st == 14 else SNR
        hit(S(3, st), note, fill_v[i], 90, F,
            limb=('RH' if i % 2 == 0 else 'LH'))


def groove_bar(b, kicks, F, crash=None, ride_skip=(), texture='ride',
               openhat=False, ghosts=(7, 11, 14), bb_vel=112, kick_vel=100):
    """One bar of pocket: RH rides and plays backbeats, LH ghosts, feet."""
    skip = set(ride_skip)
    bell_steps = (0, 8) if texture == 'hh' else ()
    for st in range(0, 16, 2):
        if st in (4, 12) or st in skip or st in bell_steps:
            continue
        if openhat and st == 14:
            continue
        if texture == 'ride':
            hit(S(b, st), RIDE, 84 if st % 4 == 0 else 70, 420, F, limb='RH')
        else:
            hit(S(b, st), HAT_C, 70, 70, F, limb='RH')
    for st in bell_steps:
        if st not in skip:
            hit(S(b, st), BELL, 80, 300, F, limb='RH')
    for st in (4, 12):                      # backbeat, laid back by feel
        hit(S(b, st), SNR, bb_vel, 100, F, limb='RH')
    for st in ghosts:                       # whisper ghosts against it
        hit(S(b, st), SNR, 36, 80, F, limb='LH')
    for st in kicks:
        hit(S(b, st), KICK, kick_vel, 90, F)
    for st in (4, 12):
        hit(S(b, st), HAT_P, 52, 60, F)
    if crash is not None:
        hit(S(b, 0), crash, 112, 1800, F, limb='RH')
    if openhat:
        hit(S(b, 15), HAT_O, 74, 340, F, limb='RH')


def groove():
    """Bars 4-11: swung funk; texture opens up; motif fragments appear."""
    F = F_GR
    KA = (0, 6, 10)
    KB = (0, 6, 10, 13)
    groove_bar(4, KA, F, crash=CR1, ride_skip=(0,))
    groove_bar(5, KB, F, openhat=True)
    groove_bar(6, (0, 6), F)
    hit(S(6, 10), SNR, 102, 100, F, limb='RH')       # answered accent
    groove_bar(7, KB, F, ghosts=(7, 11), ride_skip=(14,))
    hit(S(7, 14), SNR, 90, 90, F, limb='RH')         # pickup
    hit(S(7, 15), SNR, 102, 90, F, limb='LH')
    groove_bar(8, KA, F, crash=CR2, ride_skip=(0,), texture='hh')
    groove_bar(9, KB, F, texture='hh', ride_skip=(10, 14))
    hit(S(9, 10), T_HM, 100, 100, F, limb='RH')      # motif A fragment
    hit(S(9, 14), T_HI, 92, 100, F, limb='RH')
    groove_bar(10, (0, 6), F, texture='hh', ride_skip=(10,))
    hit(S(10, 10), SNR, 102, 100, F, limb='RH')
    groove_bar(11, KA, F, texture='hh', ghosts=(7, 11), ride_skip=(14,))
    hit(S(11, 13), T_LO, 102, 100, F, limb='LH')     # send-off fill
    hit(S(11, 14), T_HF, 108, 100, F, limb='RH')
    hit(S(11, 15), KICK, 106, 90, F)


def build():
    """Bars 12-19: motif A developed on toms; hemiola; tension and release."""
    F = F_PK
    hit(S(12, 0), CR1, 114, 1800, F, limb='LH')
    for st, d in MA:
        hit(S(12, st), SNR, {'A': 110, 'm': 88, 'g': 36}[d], 90, F,
            limb=('RH' if d == 'A' else None))
    for st in (0, 8):
        hit(S(12, st), KICK, 102, 90, F)
    for st in (4, 12):
        hit(S(12, st), HAT_P, 52, 60, F)

    orch13 = {0: T_HM, 4: T_LM, 10: T_LO, 14: T_HF}   # descend the drums
    for st, d in MA:
        if d == 'g':
            hit(S(13, st), SNR, 36, 80, F)
        else:
            hit(S(13, st), orch13[st], {'A': 110, 'm': 96}[d], 100, F)
    for st in (0, 8):
        hit(S(13, st), KICK, 102, 90, F)
    for st in (4, 12):
        hit(S(13, st), HAT_P, 52, 60, F)

    frag = MA[:4]                                     # sequence the fragment
    for shift, drum_a, drum_m, base in ((0, SNR, SNR, 100), (8, T_LO, T_HF, 106)):
        for st, d in frag:
            if d == 'g':
                hit(S(14, st + shift), SNR, 36, 80, F)
            elif d == 'A':
                hit(S(14, st + shift), drum_a, base, 100, F)
            else:
                hit(S(14, st + shift), drum_m, base - 12, 100, F)
    for st in (0, 8):
        hit(S(14, st), KICK, 104, 90, F)
    for st in (4, 12):
        hit(S(14, st), HAT_P, 54, 60, F)

    seq = ((0, T_LO, 104), (4, T_LM, 102), (8, T_HM, 108), (12, T_HI, 112))
    stick = {0: 'RH', 3: 'LH', 4: 'RH', 6: 'LH',
             8: 'RH', 11: 'LH', 12: 'RH', 14: 'LH'}
    for st, note, v in seq:
        hit(S(15, st), note, v, 100, F, limb=stick[st])
    for st in (3, 6, 11, 14):
        hit(S(15, st), SNR, 38, 80, F, limb=stick[st])
    for st in (0, 8):
        hit(S(15, st), KICK, 106, 90, F)
    for st in (4, 12):
        hit(S(15, st), HAT_P, 54, 60, F)

    acc16 = {0: SNR, 3: T_HI, 6: T_HM, 9: T_LO, 12: T_HF, 15: T_LF}
    for st in range(16):                              # groups of 3 over 4/4
        limb = 'RH' if st % 2 == 0 else 'LH'
        if st in acc16:
            hit(S(16, st), acc16[st], 104 + (st // 3) * 2, 100, F, limb=limb)
        else:
            hit(S(16, st), SNR, 62 + st, 80, F, limb=limb)
    for st in (0, 8):
        hit(S(16, st), KICK, 104, 90, F)
    for st in (4, 12):
        hit(S(16, st), HAT_P, 54, 60, F)

    acc17 = {2: T_LF, 5: T_HF, 8: T_LO, 11: T_HM, 14: T_HI}   # displaced
    for st in range(16):
        limb = 'RH' if st % 2 == 0 else 'LH'
        if st in acc17:
            hit(S(17, st), acc17[st], 108 + (st // 3) * 2, 100, F, limb=limb)
        elif st == 15:
            hit(S(17, st), T_HI, 118, 100, F, limb=limb)
        else:
            hit(S(17, st), SNR, 78 + st // 2, 80, F, limb=limb)
    for st in (0, 8, 14):
        hit(S(17, st), KICK, 106, 90, F)
    for st in (4, 12):
        hit(S(17, st), HAT_P, 54, 60, F)

    hit(S(18, 0), CR2, 118, 1800, F, limb='RH')       # release: loud space
    hit(S(18, 0), SNR, 116, 100, F, limb='LH')
    hit(S(18, 0), KICK, 112, 90, F)
    for st in (7, 10):
        hit(S(18, st), SNR, 112, 100, F)
        hit(S(18, st), KICK, 112, 90, F)
    for st in (4, 12):
        hit(S(18, st), HAT_P, 50, 60, F)

    for st in (0, 4, 8, 12):                          # four-on-floor build
        hit(S(19, st), KICK, 106, 90, F)
    for st in (4, 12):
        hit(S(19, st), HAT_P, 54, 60, F)
    for i, st in enumerate(range(4, 16)):
        note = T_HF if st == 14 else (T_LF if st == 15 else SNR)
        hit(S(19, st), note, 72 + i * 4, 90, F,
            limb=('RH' if i % 2 == 0 else 'LH'))


def peak():
    """Bars 20-27: the shout groove; motif A recapitulated on toms."""
    F = F_PK
    K = (0, 6, 8, 10)
    groove_bar(20, K, F, crash=CR1, ride_skip=(0,), bb_vel=116, kick_vel=104)
    groove_bar(21, K, F, bb_vel=116, kick_vel=104)
    groove_bar(22, K + (13,), F, openhat=True, bb_vel=116, kick_vel=104)
    groove_bar(23, K, F, ghosts=(7,), bb_vel=116, kick_vel=104,
               ride_skip=(14,))
    hit(S(23, 13), T_LO, 104, 100, F, limb='LH')
    hit(S(23, 14), T_HF, 110, 100, F, limb='RH')
    hit(S(23, 15), KICK, 108, 90, F)
    groove_bar(24, K, F, crash=CR2, ride_skip=(0,), bb_vel=116, kick_vel=106)
    groove_bar(25, K + (13,), F, bb_vel=116, kick_vel=106, ride_skip=(8,))
    hit(S(25, 8), CHINA, 110, 1600, F, limb='RH')

    for st in range(0, 16, 2):                        # bar 26: recap of motif A
        hit(S(26, st), HAT_P, 50, 60, F)
    orch26 = {0: T_HM, 4: T_LM, 10: T_LO, 14: T_HF}
    for st, d in MA:
        if d == 'g':
            hit(S(26, st), SNR, 38, 80, F)
        else:
            hit(S(26, st), orch26[st], {'A': 112, 'm': 100}[d], 100, F)
    for st in (0, 6, 10):
        hit(S(26, st), KICK, 106, 90, F)

    for st in (0, 4, 8, 12):                          # bar 27: cascade down
        hit(S(27, st), KICK, 108, 90, F)
    drums = [SNR, SNR, T_HI, T_HI, T_HM, T_HM, T_LM, T_LM,
             T_LO, T_LO, T_HF, T_HF, T_LF, T_LF, T_LF, T_LF]
    vs = [100, 102, 104, 106, 106, 108, 108, 110,
          112, 114, 116, 118, 120, 122, 124, 126]
    for st in range(16):
        hit(S(27, st), drums[st], vs[st], 90, F,
            limb=('LH' if st % 2 == 0 else 'RH'))


def breakdown():
    """Bars 28-33: pianissimo.  Motif B travels claves -> congas -> cross-stick."""
    F = F_BR
    MBV = {'A': 88, 'm': 76}
    for b in (28, 29):
        for st in range(16):                          # shaker 16ths, swung hard
            hit(S(b, st), MAR, 64 if st % 4 == 0 else 42, 60, F,
                limb='RH', gap=55)
        for st, d in MB:
            hit(S(b, st), CLAV, MBV[d], 120, F, limb='LH')
        for st in (0, 8):
            hit(S(b, st), KICK, 62, 90, F)
        for st in (4, 12):
            hit(S(b, st), HAT_P, 54, 60, F)
    hit(S(29, 14), TRI, 60, 2400, F, limb='LH')

    conga_map = {0: ('RH', CG_H), 3: ('LH', CG_H), 6: ('RH', CG_L),
                 10: ('LH', CG_H), 12: ('RH', CG_L)}
    for b in (30, 31):
        for st, d in MB:
            limb, note = conga_map[st]
            hit(S(b, st), note, {'A': 92, 'm': 82}[d], 220, F, limb=limb)
        for st in (0, 8):
            hit(S(b, st), KICK, 66, 90, F)
        for st in (4, 12):
            hit(S(b, st), HAT_P, 56, 60, F)
    hit(S(31, 14), CG_L, 86, 220, F, limb='RH')
    hit(S(31, 15), CG_H, 92, 220, F, limb='LH')

    for st in range(0, 16, 2):                        # cross-stick clave
        hit(S(32, st), MAR, 56 if st % 4 == 0 else 46, 60, F,
            limb='LH', gap=55)
    for st, d in MB:
        hit(S(32, st), XSTK, {'A': 84, 'm': 72}[d], 90, F, limb='RH')
    for st in (0, 8):
        hit(S(32, st), KICK, 70, 90, F)
    for st in (4, 12):
        hit(S(32, st), HAT_P, 56, 60, F)
    hit(S(32, 14), TRI, 62, 2400, F, limb='RH')

    for st, d in MB[:3]:                              # rebuild
        hit(S(33, st), XSTK, {'A': 86, 'm': 74}[d], 90, F, limb='RH')
    hit(S(33, 0), KICK, 72, 90, F)
    for i, st in enumerate(range(8, 16)):
        hit(S(33, st), SNR, 58 + i * 6, 90, F,
            limb=('RH' if i % 2 == 0 else 'LH'))
    for st in (8, 12):
        hit(S(33, st), KICK, 76, 90, F)
    hit(S(33, 4), HAT_P, 56, 60, F)


def double_time():
    """Bars 34-41: 16th-note machinery; motif A in augmentation."""
    F = F_DT
    acc_pats = {34: (0, 4, 8, 12), 35: (0, 3, 6, 9, 12, 15),
                36: (0, 2, 5, 8, 11, 14), 37: (0, 4, 8)}
    for b in (34, 35, 36, 37):
        accs = set(acc_pats[b])
        for st in range(16):
            limb = 'RH' if st % 2 == 0 else 'LH'
            if b == 37 and st >= 12:
                hit(S(b, st), SNR, 114 + (st - 12) * 3, 90, F, limb=limb)
            elif st in accs:
                hit(S(b, st), SNR, 106 + (b - 34) * 2, 90, F, limb=limb)
            else:
                hit(S(b, st), SNR, 74 + (b - 34) * 3, 80, F, limb=limb)
        for st in (0, 4, 8, 12):
            hit(S(b, st), KICK, 106, 90, F)
        for st in (2, 6, 10, 14):
            hit(S(b, st), HAT_P, 62, 60, F)

    tom_beats = {38: (T_HI, T_HM, T_LO, T_HF), 39: (T_HM, T_LO, T_HF, T_LF)}
    for b in (38, 39):
        tb = tom_beats[b]
        for st in range(16):
            limb = 'RH' if st % 2 == 0 else 'LH'
            v = (114 if b == 38 else 118) if st % 4 == 0 else (84 if b == 38 else 88)
            if b == 39 and st == 15:
                v = 124
            hit(S(b, st), tb[st // 4], v, 100, F, limb=limb)
        for st in (0, 4, 8, 12):
            hit(S(b, st), KICK, 110 if b == 38 else 112, 90, F)

    # motif A augmented to 8th notes across bars 40-41, in unison with kick
    hit(S(40, 0), CR1, 122, 1800, F, limb='LH')
    for st, v, uni in ((0, 122, True), (6, 74, False), (8, 110, True), (12, 76, False)):
        hit(S(40, st), SNR, v, 100, F, limb=('RH' if uni else 'LH'))
        if uni:
            hit(S(40, st), KICK, 118 if st == 0 else 112, 90, F)
    hit(S(41, 4), CHINA, 118, 1600, F, limb='LH')
    hit(S(41, 4), SNR, 118, 100, F, limb='RH')
    hit(S(41, 4), KICK, 114, 90, F)
    hit(S(41, 6), SNR, 78, 90, F, limb='LH')
    hit(S(41, 12), SNR, 112, 100, F, limb='LH')
    hit(S(41, 12), KICK, 112, 90, F)


def climax():
    """Bars 42-47: shots, hemiola fills, stop-time, the final climb."""
    F = F_PK
    hit(S(42, 0), CR2, 122, 1800, F, limb='RH')
    hit(S(42, 0), SNR, 122, 100, F, limb='LH')
    hit(S(42, 0), KICK, 118, 90, F)
    for st, v in ((6, 108), (10, 114), (15, 116)):
        hit(S(42, st), SNR, v, 100, F, limb='RH')
        hit(S(42, st), KICK, 110, 90, F)
    hit(S(42, 10), CHINA, 112, 1600, F, limb='LH')

    for st in (0, 4, 8, 12):
        hit(S(43, st), KICK, 108, 90, F)
    drums = [SNR] * 8 + [T_HM] * 2 + [T_LO] * 2 + [T_HF] * 2 + [T_LF] * 2
    for st in range(16):
        hit(S(43, st), drums[st], 104 + st, 90, F,
            limb=('RH' if st % 2 == 0 else 'LH'))

    hit(S(44, 0), CR1, 120, 1800, F, limb='LH')
    hit(S(44, 0), SNR, 120, 100, F, limb='RH')
    hit(S(44, 0), KICK, 116, 90, F)
    for st, v in ((6, 110), (14, 112), (15, 106)):
        hit(S(44, st), SNR, v, 100, F, limb='RH')
        hit(S(44, st), KICK, 110, 90, F)
    hit(S(44, 8), CHINA, 116, 1600, F, limb='LH')
    hit(S(44, 8), SNR, 116, 100, F, limb='RH')
    hit(S(44, 8), KICK, 112, 90, F)
    hit(S(44, 12), SPL, 100, 900, F, limb='LH')

    acc = {0: SNR, 3: T_HI, 6: T_HM, 9: T_LO, 12: T_HF, 15: T_LF}
    for st in range(16):
        limb = 'RH' if st % 2 == 0 else 'LH'
        if st in acc:
            hit(S(45, st), acc[st], 116 + st // 6, 100, F, limb=limb)
        else:
            hit(S(45, st), SNR, 92, 80, F, limb=limb)
    for st in (0, 4, 8, 12, 14):
        hit(S(45, st), KICK, 112, 90, F)

    hit(S(46, 0), CR2, 120, 1800, F, limb='RH')       # stop-time tension
    hit(S(46, 0), SNR, 120, 100, F, limb='LH')
    hit(S(46, 0), KICK, 116, 90, F)
    for st in (6, 10):
        hit(S(46, st), SNR, 112, 100, F, limb='RH')
        hit(S(46, st), KICK, 110, 90, F)
    hit(S(46, 14), SNR, 30, 80, F, limb='LH')         # ...a whisper

    for st in (0, 4, 8, 12, 14):                      # final climb (ritard.)
        hit(S(47, st), KICK, 114, 90, F)
    drums = [SNR] * 8 + [T_LO] * 2 + [T_HF] * 2 + [T_LF] * 4
    vs = [108, 110, 112, 112, 114, 116, 118, 118,
          120, 122, 122, 124, 124, 126, 126, 127]
    for st in range(16):
        hit(S(47, st), drums[st], vs[st], 90, F,
            limb=('RH' if st % 2 == 0 else 'LH'))


def finale():
    """Bar 48: one fortissimo unison -- crash, snare, kick, foot chick."""
    t = S(48, 0)
    hit(t, CR1, 127, 3000, F_PK, limb='LH')
    hit(t, SNR, 127, 240, F_PK, limb='RH')
    hit(t, KICK, 124, 200, F_PK)
    hit(t, HAT_P, 72, 80, F_PK)


# ============================ post-processing ==============================

def clamp_overlaps():
    """Clip each note so it ends just before the same drum is restruck."""
    by_note = {}
    for e in events:
        by_note.setdefault(e[2], []).append(e)
    fixed = []
    for lst in by_note.values():
        lst.sort(key=lambda e: e[0])
        for i, (on, off, n, v) in enumerate(lst):
            if i + 1 < len(lst) and off > lst[i + 1][0] - 1:
                off = lst[i + 1][0] - 1
            if off <= on:
                off = on + 20
            fixed.append((on, off, n, v))
    events[:] = fixed


def cap_voices():
    """Safety net: never more than four simultaneous strokes."""
    from collections import defaultdict
    at = defaultdict(list)
    for i, e in enumerate(events):
        at[e[0]].append(i)
    drop = set()
    for idxs in at.values():
        if len(idxs) > 4:
            keep = sorted(idxs, key=lambda i: events[i][3], reverse=True)[:4]
            drop.update(i for i in idxs if i not in keep)
    if drop:
        events[:] = [e for i, e in enumerate(events) if i not in drop]


def validate():
    from collections import defaultdict
    per_tick = defaultdict(int)
    for on, _off, _n, _v in events:
        per_tick[on] += 1
    mx = max(per_tick.values())
    assert mx <= 4, f"too many simultaneous strokes: {mx}"
    return mx


def write_file():
    mid = mido.MidiFile(type=0, ticks_per_beat=TPQ)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    msgs = []

    def meta(t, m):
        msgs.append((t, 0, m))

    meta(0, mido.MetaMessage('track_name', name='GM Drum Solo'))
    meta(0, mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
    meta(0, mido.MetaMessage('time_signature', numerator=4, denominator=4))
    for bar, name in MARKERS:
        meta(bar * BAR_T, mido.MetaMessage('marker', text=name))

    # ritardando through the last two beats of bar 47 into the final hit
    t0, t1 = base_tick(S(47, 8)), base_tick(S(48, 0))
    for k in range(8):
        meta(t0 + k * (t1 - t0) // 8,
             mido.MetaMessage('set_tempo',
                              tempo=mido.bpm2tempo(BPM - (k + 1) * 14.0 / 8)))
    meta(t1, mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM - 14.0)))

    for on, off, n, v in events:
        msgs.append((on, 2, mido.Message('note_on', channel=CH,
                                         note=n, velocity=v)))
        msgs.append((off, 1, mido.Message('note_off', channel=CH,
                                          note=n, velocity=0)))
    msgs.sort(key=lambda x: (x[0], x[1]))

    last = 0
    for t, _o, m in msgs:
        m.time = t - last
        tr.append(m)
        last = t
    end_t = 50 * BAR_T
    tr.append(mido.MetaMessage('end_of_track', time=max(0, end_t - last)))
    mid.save('solo.mid')


def approx_seconds():
    t_rit = base_tick(S(47, 8))
    t_hit = base_tick(S(48, 0))
    end = 50 * BAR_T
    b0, b1 = BPM, BPM - 14.0
    sec = (t_rit / TPQ) * 60.0 / b0
    sec += ((t_hit - t_rit) / TPQ) * 60.0 * math.log(b0 / b1) / (b0 - b1)
    sec += ((end - t_hit) / TPQ) * 60.0 / b1
    return sec


def main():
    statement()
    groove()
    build()
    peak()
    breakdown()
    double_time()
    climax()
    finale()
    clamp_overlaps()
    cap_voices()
    mx = validate()
    write_file()
    print(f"solo.mid written: {len(events)} notes, "
          f"max {mx} simultaneous strokes, ~{approx_seconds():.0f}s "
          f"(last hit ~{approx_seconds() - 8 * 60.0 / (BPM - 14.0):.0f}s)")


if __name__ == '__main__':
    main()
