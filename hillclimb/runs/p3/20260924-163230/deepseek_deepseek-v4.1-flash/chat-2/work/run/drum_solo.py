#!/usr/bin/env python3
"""
drum_solo.py

Generates ``solo.mid``: a deterministic (~2 minute) General MIDI drum solo
for MIDI channel 10.  Only mido is used.

Structure:
    intro   - soft ride/rim statement, crescendo fill
    A       - the hook (motif) stated
    A'      - the hook moved to toms, displaced, halved
    B       - chorus: crash accents, ride bell, heavier kick
    C       - hands: 16th singles / doubles travelling around the kit
    break   - sparse breakdown on the whole GM percussion palette
    build   - rolls and cascades, accelerando
    climax  - the hook returns full force
    finale  - cascades, unison hits, breath, final hit that rings out
"""

import math

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
TPB = 480                  # ticks per quarter note
S16 = TPB // 4             # one sixteenth note, in ticks
CH = 9                     # MIDI channel 10 (zero based)
TARGET_SECONDS = 120.0     # length of the solo

# ---- General MIDI percussion (35..81)
K, K2 = 36, 35
S, RIM, ES = 38, 37, 40
HH, HHO, HHP = 42, 46, 44
RIDE, BELL, RIDE2 = 51, 53, 59
CR, CR2, SPL, CHI = 49, 57, 55, 52
T1, T2, T3, T4, T5, T6 = 50, 48, 47, 45, 43, 41          # high .. floor tom
BONGO_H, BONGO_L = 60, 61
CONGA_H, CONGA_M, CONGA_L = 63, 62, 64
TIMB_H, TIMB_L = 65, 66
AGOGO_H, AGOGO_L = 67, 68
COW, CLAV, WB_H, WB_L, TRI, TAMB, CAB, MAR = 56, 75, 76, 77, 81, 54, 69, 70
GUIRO_S, GUIRO_L = 73, 74
VIBRA = 58

# notes played with a foot (for the "two hands / two feet" rule)
FOOT = {K, K2, HHP}

# how long each sound is held (in beats)
DUR = {
    CR: 1.6, CR2: 1.6, CHI: 1.2, SPL: 0.8,
    RIDE: 0.45, RIDE2: 0.45, BELL: 0.35,
    HH: 0.12, HHO: 0.6, HHP: 0.12,
    S: 0.12, ES: 0.12, RIM: 0.10,
    K: 0.14, K2: 0.14,
    TRI: 1.0, VIBRA: 0.7, COW: 0.30, CLAV: 0.16,
    WB_H: 0.16, WB_L: 0.16, TAMB: 0.20, CAB: 0.20, MAR: 0.20,
    CONGA_H: 0.20, CONGA_M: 0.20, CONGA_L: 0.25,
    BONGO_H: 0.16, BONGO_L: 0.18,
}


def dur_of(note):
    return DUR.get(note, 0.22)


# deliberate placement per instrument (ticks, +/-), not random jitter
INST_FEEL = {
    HH: -3, HHO: -2, HHP: 0, RIDE: -2, RIDE2: -2, BELL: 0,
    CR: 1, CR2: 1, SPL: 0, CHI: 1,
    S: 1, ES: 1, RIM: 0, K: 0, K2: 0,
}

TOTAL_BEATS = 264.0        # 66 bars of 4/4


# --------------------------------------------------------------------------
# timing feel
# --------------------------------------------------------------------------
def feel_offset(slot, note, sec, abs_beat):
    """Deterministic micro placement: section lean, swing, drift, instrument."""
    off = sec['feel']
    if note not in FOOT:
        swing = sec['swing'] * S16
        if abs(slot - round(slot)) < 1e-6:
            s = int(round(slot))
            if s % 4 == 2:          # offbeat eighth
                off += swing * 0.55
            elif s % 2 == 1:        # 'e' and 'a' sixteenths
                off += swing
    off += INST_FEEL.get(note, 0)
    # slow breathing drift across the whole solo
    off += 2.5 * math.sin(2.0 * math.pi * (abs_beat / TOTAL_BEATS) * 1.7 + 0.4)
    # tiny systematic variation so nothing is machine gun tight
    off += ((note * 7 + int(round(slot * 4)) * 13) % 5) - 2
    return off


def no_slot(patterns, slot, notes):
    """Drop given notes from a slot (e.g. stop the ride when a crash lands)."""
    return [p for p in patterns
            if not (abs(p[0] - slot) < 1e-9 and p[1] in notes)]


# --------------------------------------------------------------------------
# bar building blocks
# --------------------------------------------------------------------------
def motif_bar(sn=S, hats=HH, accent=108, ghost=1.0, hat_v=0, kick=K):
    """The hook: syncopated kick, backbeats, ghost notes, steady eighths."""
    p = []
    hv = [70, 50, 64, 48, 68, 50, 64, 52]
    for j, v in enumerate(hv):
        p.append((2 * j, hats, v + hat_v))
    p += [(0, kick, 108), (4, sn, accent), (12, sn, accent + 2),
          (6, kick, 86), (8, kick, 74),
          (2, sn, 34 * ghost), (3, sn, 30 * ghost),
          (10, sn, 42 * ghost), (11, sn, 28 * ghost)]
    return p


def groove16(hats=HH, sn=S, hat_v=58):
    """Busier sixteenth variant of the hook."""
    p = []
    for j in range(16):
        v = hat_v + (10 if j % 4 == 0 else (0 if j % 2 == 0 else -8))
        p.append((j, hats, v))
    p += [(0, K, 106), (4, sn, 106), (12, sn, 110),
          (6, sn, 42), (10, K, 86), (14, sn, 46), (7, K, 74)]
    return p


def halftime(tom=T2, hats=HH):
    """Wide half-time feel - a big breath inside a busy stretch."""
    p = []
    for j in (0, 2, 4, 6, 8, 10, 12, 14):
        p.append((j, hats, 58 + (6 if j % 4 == 0 else 0)))
    p += [(0, K, 112), (6, K, 88), (8, S, 112), (11, S, 44), (14, tom, 96)]
    return p


def fill_desc(v=1.0):
    """Classic descending sixteenth fill that carries into the next downbeat."""
    p = [(0, K, 104), (8, K, 92)]
    seq = [(0, S, 78), (1, S, 60), (2, S, 70), (3, S, 56),
           (4, T1, 96), (5, T1, 64), (6, T2, 90), (7, T2, 62),
           (8, T3, 86), (9, T4, 66), (10, T5, 82), (11, T6, 64),
           (12, S, 104), (13, S, 70), (14, S, 92), (15, S, 58)]
    for (s, n, vel) in seq:
        p.append((s, n, vel * v))
    return p


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------
def gen_intro(i):
    p = []
    if i < 3:
        rv = [64, 50, 56, 48, 62, 50, 56, 52]
        for j, v in enumerate(rv):
            p.append((2 * j, RIDE, v + 3 * i))
        p += [(0, K, 82 + 3 * i), (8, K, 70 + 5 * i)]
        if i >= 1:
            p += [(4, RIM, 78 + 5 * i), (12, RIM, 82 + 5 * i),
                  (3, S, 30), (11, S, 32)]
        if i == 2:
            p += [(7, S, 36), (10, S, 44), (15, HHO, 66)]
    else:
        for j in range(16):
            if j < 12:
                p.append((j, S, min(56 + j * 3.6, 106)))
            else:
                p.append((j, [T2, T3, T5, T6][j - 12],
                          min(100 + (j - 12) * 7, 124)))
        p += [(0, K, 96), (8, K, 88)]
    return p


def gen_A(i):
    """Hook stated, with small variations, then a fill."""
    if i == 7:
        return fill_desc(0.95)
    if i == 6:
        p = motif_bar(sn=T2, hats=RIDE, accent=104, hat_v=-8)
        p += [(14, T1, 88), (15, T2, 72)]
        return p
    p = motif_bar(accent=104 + 2 * i, ghost=1.0 + 0.05 * i)
    if i == 0:
        p = no_slot(p, 0, {HH, RIDE})
        p.append((0, CR, 100))
    if i % 2 == 1:
        p.append((14, S, 46))
    if i == 3:
        p.append((15, HHO, 64))
    if i == 5:
        p += [(6, K, 94), (7, K, 78)]
    return p


def gen_A2(i):
    """Hook developed: toms, sixteenths, half time, then a fill."""
    if i == 0:
        p = motif_bar(sn=T2, hats=RIDE, accent=102, hat_v=-10)
        p = no_slot(p, 0, {RIDE, HH})
        p += [(0, CR, 100), (14, T1, 90)]
        return p
    if i == 1:
        p = motif_bar(sn=T3, hats=RIDE, accent=104, hat_v=-8)
        p += [(14, T1, 88), (15, T2, 76)]
        return p
    if i == 2:
        return groove16(hats=HH, sn=T2, hat_v=58)
    if i == 3:
        p = groove16(hats=HH, sn=S, hat_v=62)
        p.append((15, HHO, 68))
        return p
    if i == 4:
        return halftime(T2)
    if i == 5:
        p = halftime(T3)
        p += [(14, T1, 92), (15, S, 50)]
        return p
    if i == 6:
        order = [T6, T5, T4, T3, T2, T1, S, T1]
        p = [(0, K, 104), (8, K, 96)]
        for j in range(16):
            n = order[j % 8]
            vel = 104 if j % 4 == 0 else (82 if j % 2 == 0 else 68)
            p.append((j, n, vel))
        return p
    return fill_desc(1.0)


def gen_B(i):
    """Chorus: bigger, ride/hats, crash accents, heavier kick."""
    if i == 7:
        p = fill_desc(1.05)
        p.append((8, CR2, 104))
        return p
    hats = RIDE if i % 2 == 0 else HH
    p = []
    rv = [72, 54, 66, 50, 70, 54, 66, 56]
    for j, v in enumerate(rv):
        p.append((2 * j, hats, v + 4 * (i // 4)))
    p += [(0, K, 112), (4, S, 112), (12, S, 114), (6, K, 92), (10, K, 86),
          (2, S, 36), (7, S, 32), (11, S, 38), (14, S, 48)]
    if i in (0, 4):
        p = no_slot(p, 0, {RIDE, HH})
        p.append((0, CR if i == 0 else CR2, 114))
    if i in (1, 3, 5):
        p.append((15, K, 84))
    if i == 6:
        p = no_slot(p, 10, {RIDE, HH})
        p.append((10, BELL, 104))
    return p


RUN_UP = [S, T1, T2, T3, T4, T5, T6, T1]
RUN_DN = [T6, T5, T4, T3, T2, T1, S, T2]


def gen_C(i):
    """Hands: long strings of singles and doubles around the kit."""
    p = []
    if i < 2:
        order = RUN_UP if i == 0 else RUN_DN
        for j in range(16):
            n = order[j % 8]
            vel = 106 if j % 4 == 0 else (82 if j % 2 == 0 else 68)
            p.append((j, n, vel))
        p += [(0, K, 102), (8, K, 96)]
    elif i == 2:
        order = [T1, T1, T2, T2, T3, T3, T4, T4]
        for j in range(16):
            p.append((j, order[j % 8],
                      104 if j % 4 == 0 else (78 if j % 2 == 0 else 66)))
        p += [(0, K, 104), (8, K, 98)]
    elif i == 3:
        order = [S, S, T1, T1, S, S, T2, T2]
        for j in range(16):
            p.append((j, order[j % 8],
                      106 if j % 4 == 0 else (76 if j % 2 == 0 else 64)))
        p += [(4, K, 94), (12, K, 92)]
    elif i == 4:
        order = [T2, T3, T2, T2, T4, T5, T4, T4]
        for j in range(16):
            p.append((j, order[j % 8],
                      102 if j % 4 == 0 else (80 if j % 2 == 0 else 68)))
        p += [(0, K, 102), (6, K, 90), (8, K, 98), (14, K, 88)]
    elif i == 5:
        order = [S, T1, S, T2, S, T3, S, T4]
        for j in range(16):
            p.append((j, order[j % 8], 104 if j % 4 == 0 else 74))
        p += [(2, K, 86), (6, K, 86), (10, K, 86), (14, K, 86)]
    elif i == 6:
        for j in range(16):
            n = S if j % 4 != 2 else T1
            p.append((j, n, min(int(62 + j * 3.6), 118)))
        p += [(0, K, 104), (8, K, 100)]
    else:
        p = fill_desc(1.1)
    return p


def gen_break(i):
    """Breakdown: quiet, sparse, whole percussion palette, then a swell."""
    p = []
    if i == 0:
        p += [(0, CR, 88), (0, K, 92), (8, S, 78), (12, RIM, 84),
              (4, HHP, 70), (12, HHP, 70), (14, S, 40), (15, S, 34)]
    elif i == 1:
        p += [(0, RIM, 76), (4, HHP, 70), (8, RIM, 80), (12, HHP, 70),
              (2, S, 30), (6, S, 32), (10, S, 30), (14, S, 34), (3, TRI, 70)]
    elif i == 2:
        p += [(0, COW, 84), (2, COW, 60), (3, COW, 66), (4, COW, 78),
              (6, COW, 58), (8, COW, 82), (10, COW, 60), (11, COW, 68),
              (12, COW, 76), (14, COW, 58),
              (0, K, 88), (8, K, 84), (4, S, 36), (12, S, 38)]
    elif i == 3:
        p += [(0, WB_H, 82), (1, WB_L, 60), (2, WB_H, 66), (4, WB_L, 78),
              (6, WB_H, 64), (8, WB_H, 80), (10, WB_L, 62), (12, WB_H, 78),
              (14, WB_L, 60), (5, S, 30), (7, S, 32), (11, S, 30), (13, S, 34),
              (0, K, 84), (8, K, 80)]
    elif i == 4:
        p += [(0, CONGA_L, 86), (2, CONGA_M, 66), (3, CONGA_H, 74),
              (4, CONGA_M, 80), (6, CONGA_L, 62), (8, CONGA_L, 84),
              (10, CONGA_M, 64), (11, CONGA_H, 76), (12, CONGA_M, 82),
              (14, CONGA_H, 68), (0, HHP, 66), (8, HHP, 66)]
    elif i == 5:
        p += [(0, BONGO_L, 84), (2, BONGO_H, 70), (3, BONGO_L, 62),
              (4, BONGO_H, 82), (6, BONGO_L, 60), (8, BONGO_L, 80),
              (10, BONGO_H, 68), (11, BONGO_L, 60), (12, BONGO_H, 84),
              (14, BONGO_H, 66), (0, K, 80), (8, K, 78), (15, S, 40)]
    elif i == 6:
        for j in range(16):
            n = S if j % 2 == 0 else RIM
            p.append((j, n, min(int(52 + j * 3.0), 100)))
        p += [(0, K, 88), (8, K, 86)]
    else:
        for j in range(16):
            p.append((j, S, min(int(64 + j * 3.4), 118)))
        p += [(0, K, 96), (8, K, 92),
              (12, T2, 90), (13, T3, 92), (14, T4, 96), (15, T5, 100)]
    return p


def gen_build(i):
    """Accelerando: swelling rolls and cascades, then a giant fill."""
    p = []
    if i == 0:
        p.append((0, SPL, 96))
        for j, v in enumerate([70, 60, 66, 58, 72, 62, 68, 60]):
            p.append((2 * j, T3 if j % 2 == 0 else T4, v))
        p += [(0, K, 100), (8, K, 96)]
    elif i == 1:
        for j in range(16):
            p.append((j, T4 if j % 2 == 0 else T5, 66 + j * 2.0))
        p += [(0, K, 104), (8, K, 100)]
    elif i == 2:
        for j in range(16):
            n = T5 if j % 4 < 2 else T6
            p.append((j, n, 70 + j * 2.4))
        p += [(0, K, 106), (4, K, 96), (8, K, 100), (12, K, 94)]
    elif i == 3:
        for j in range(16):
            n = S if j % 4 != 3 else T1
            p.append((j, n, min(int(72 + j * 2.6), 116)))
        p += [(0, K, 108), (8, K, 104)]
    elif i == 4:
        order = [T1, T1, T2, T2, T3, T3, T4, T4]
        for j in range(16):
            p.append((j, order[j % 8], 90 if j % 4 == 0 else 70))
        p += [(0, K, 108), (6, K, 92), (8, K, 100), (14, K, 88)]
    elif i == 5:
        for j in range(16):
            n = [S, T1, S, T2, S, T3, S, T4][j % 8]
            p.append((j, n, 98 if j % 4 == 0 else 72))
        p += [(2, K, 84), (6, K, 84), (10, K, 84), (14, K, 84)]
    elif i == 6:
        for j in range(16):
            p.append((j, S, min(int(80 + j * 2.4), 116)))
            p.append((j + 0.5, S, min(int(68 + j * 2.4), 108)))
        p += [(0, K, 106), (8, K, 104)]
    else:
        seq = [T1, T1, T2, T2, T3, T3, T4, T4, T5, T5, T6, T6, S, S, S, S]
        p = [(0, K, 112), (8, K, 108)]
        for j, n in enumerate(seq):
            p.append((j, n, min(int(84 + j * 2.6), 124)))
    return p


def gen_climax(i):
    """The hook comes back at full force."""
    if i == 7:
        return fill_desc(1.15)
    hats = RIDE if i % 2 == 0 else HH
    p = motif_bar(sn=S, hats=hats, accent=114, hat_v=4)
    p += [(10, K, 92), (14, K, 86)]
    if i in (0, 4):
        p = no_slot(p, 0, {RIDE, HH})
        p.append((0, CR if i == 0 else CR2, 118))
    if i in (2, 6):
        p.append((15, HHO, 74))
    if i == 5:
        p += [(6, S, 46), (7, S, 40)]
    return p


def gen_finale(i):
    """Cascades, unison hits, a breath, then the last hit."""
    if i == 0:
        seq = [S, T1, T2, T3, T4, T5, T6, T5, T4, T3, T2, T1, S, T1, S, T2]
        p = [(j, n, 110 if j % 4 == 0 else 80) for j, n in enumerate(seq)]
        p += [(0, K, 112), (8, K, 108)]
        return p
    if i == 1:
        return [(0, K, 118), (0, S, 112), (0, CR, 110),
                (4, S, 96), (4, K, 100), (6, S, 40), (7, S, 36),
                (8, S, 100), (8, K, 104),
                (12, T4, 90), (14, T5, 96), (15, T6, 100)]
    if i == 2:
        seq = [S, S, T1, T1, S, S, T2, T2, S, S, T3, T3, S, S, T4, T4]
        return [(j, n, 108 if j % 4 == 0 else 74) for j, n in enumerate(seq)]
    if i == 3:
        p = [(0, K, 108), (8, K, 104)]
        for j in range(16):
            p.append((j, S, min(int(70 + j * 3.2), 120)))
        return p
    if i == 4:
        return [(0, K, 112), (8, K, 108),
                (0, S, 108), (2, S, 56), (3, S, 50), (4, S, 96),
                (6, T1, 88), (7, T1, 62), (8, T2, 92), (10, T3, 88),
                (11, T3, 64), (12, T4, 96), (13, T5, 92), (14, T6, 98),
                (15, S, 104)]
    # final bar: land the hit, let it ring
    return [(0, K, 120), (0, S, 118), (0, CR, 122)]


SECTIONS = [
    dict(name='intro',  bars=4, bpm0=100, bpm1=104, swing=0.16, feel=2.0,
         gen=gen_intro),
    dict(name='A',      bars=8, bpm0=120, bpm1=120, swing=0.10, feel=0.0,
         gen=gen_A),
    dict(name='A2',     bars=8, bpm0=124, bpm1=128, swing=0.08, feel=-1.0,
         gen=gen_A2),
    dict(name='B',      bars=8, bpm0=132, bpm1=132, swing=0.06, feel=-2.0,
         gen=gen_B),
    dict(name='C',      bars=8, bpm0=136, bpm1=136, swing=0.03, feel=-3.0,
         gen=gen_C),
    dict(name='break',  bars=8, bpm0=110, bpm1=114, swing=0.20, feel=4.0,
         gen=gen_break),
    dict(name='build',  bars=8, bpm0=118, bpm1=146, swing=0.02, feel=-2.0,
         gen=gen_build),
    dict(name='climax', bars=8, bpm0=140, bpm1=140, swing=0.05, feel=-4.0,
         gen=gen_climax),
    dict(name='finale', bars=6, bpm0=144, bpm1=144, swing=0.05, feel=-3.0,
         gen=gen_finale),
]


# --------------------------------------------------------------------------
# timing
# --------------------------------------------------------------------------
def section_seconds(sec, scale):
    """Exact integral of 60/bpm over a section whose bpm ramps linearly."""
    beats = sec['bars'] * 4
    a = sec['bpm0'] * scale
    c = sec['bpm1'] * scale
    if abs(c - a) < 1e-9:
        return 60.0 * beats / a
    return 60.0 * beats * math.log(c / a) / (c - a)


def total_seconds(scale):
    return sum(section_seconds(s, scale) for s in SECTIONS)


SCALE = total_seconds(1.0) / TARGET_SECONDS


def build_tempos():
    """(tick, tempo) list; ramps are stepped once per beat."""
    out = []
    beat = 0.0
    for sec in SECTIONS:
        beats = sec['bars'] * 4
        steps = beats if abs(sec['bpm1'] - sec['bpm0']) > 1e-6 else 1
        for k in range(steps):
            frac = k / float(steps)
            bpm = (sec['bpm0'] + (sec['bpm1'] - sec['bpm0']) * frac) * SCALE
            out.append((int(round((beat + beats * k / steps) * TPB)),
                        mido.bpm2tempo(bpm)))
        beat += beats
    return out


# --------------------------------------------------------------------------
# note generation
# --------------------------------------------------------------------------
def build_notes():
    notes = []
    abs_bar = 0
    for sec in SECTIONS:
        for i in range(sec['bars']):
            bar_beat = abs_bar * 4.0
            for (slot, note, vel) in sec['gen'](i):
                beat = bar_beat + slot / 4.0
                tick = int(round(beat * TPB + feel_offset(slot, note, sec, beat)))
                tick = max(0, tick)
                vel = max(1, min(127, int(round(vel))))
                d = max(24, int(round(dur_of(note) * TPB)))
                notes.append([tick, note, vel, d])
            abs_bar += 1
    return notes


VOICE_WINDOW = 12          # ticks; anything closer is "the same instant"


def limit_voices(notes):
    """Never more than two hands and two feet at the same instant."""
    notes = sorted(notes, key=lambda n: n[0])
    out = []
    i, n = 0, len(notes)
    while i < n:
        j = i
        while j < n and notes[j][0] - notes[i][0] <= VOICE_WINDOW:
            j += 1
        group = notes[i:j]
        hands = sorted([x for x in group if x[1] not in FOOT],
                       key=lambda x: -x[2])
        feet = sorted([x for x in group if x[1] in FOOT],
                      key=lambda x: -x[2])
        out.extend(hands[:2])
        out.extend(feet[:2])
        i = j
    return out


def ring_out(notes):
    """Give the last chord room to ring."""
    if not notes:
        return notes
    last = max(n[0] for n in notes)
    for n in notes:
        if n[0] >= last - VOICE_WINDOW:
            n[3] = max(n[3], int(3.5 * TPB))
    return notes


def fix_overlaps(notes):
    """Same pitch re-struck: shorten the earlier note so it is not choked."""
    by_note = {}
    for n in notes:
        by_note.setdefault(n[1], []).append(n)
    for lst in by_note.values():
        lst.sort(key=lambda x: x[0])
        for a, b in zip(lst, lst[1:]):
            if a[0] + a[3] > b[0] - 6:
                a[3] = max(24, b[0] - 6 - a[0])
    return notes


# --------------------------------------------------------------------------
# file assembly
# --------------------------------------------------------------------------
def write_midi(path, notes, tempos):
    mid = MidiFile(type=1, ticks_per_beat=TPB)

    meta = MidiTrack()
    mid.tracks.append(meta)
    meta_events = [(0, MetaMessage('track_name', name='Drum Solo', time=0)),
                   (0, MetaMessage('time_signature', numerator=4,
                                   denominator=4, time=0))]
    meta_events += [(t, MetaMessage('set_tempo', tempo=tp, time=0))
                    for (t, tp) in tempos]
    last = 0
    for tick, msg in sorted(meta_events, key=lambda e: e[0]):
        msg.time = max(0, tick - last)
        meta.append(msg)
        last = tick
    meta.append(MetaMessage('end_of_track', time=0))

    track = MidiTrack()
    mid.tracks.append(track)
    events = []
    for (tick, note, vel, dur) in notes:
        events.append((tick, 1,
                       Message('note_on', channel=CH, note=note,
                               velocity=vel, time=0)))
        events.append((tick + dur, 0,
                       Message('note_off', channel=CH, note=note,
                               velocity=0, time=0)))
    events.sort(key=lambda e: (e[0], e[1]))
    last = 0
    for tick, _prio, msg in events:
        msg.time = max(0, tick - last)
        track.append(msg)
        last = tick
    track.append(MetaMessage('end_of_track', time=0))

    mid.save(path)


def main():
    notes = build_notes()
    notes = limit_voices(notes)
    notes = ring_out(notes)
    notes = fix_overlaps(notes)
    write_midi('solo.mid', notes, build_tempos())

    length = total_seconds(SCALE)
    print('solo.mid written: %d notes, %.1f s, %d bars'
          % (len(notes), length, sum(s['bars'] for s in SECTIONS)))


if __name__ == '__main__':
    main()
