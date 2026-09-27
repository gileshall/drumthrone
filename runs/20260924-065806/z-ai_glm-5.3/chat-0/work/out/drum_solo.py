#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drum_solo.py -- generate solo.mid, a two-minute General MIDI drum solo on
MIDI channel 10 (the GM percussion channel).

    python drum_solo.py        -> writes solo.mid in the current directory

THE PIECE
---------
One figure runs through the whole solo, the 3-2 clave:

    X..X..X. ..X.X...      (16th-note slots 0 3 6 10 12)

It is stated alone on claves, restated on side stick, snare and toms,
buried in the kick pattern of a funk groove, quoted in straight 16ths
across a half-time shuffle, handed to cowbell, congas and timbales in a
Latin section, split between wood blocks and snare while trading twos,
and finally stamped out fortissimo by kick, toms and cymbals.

    bars  1- 4  the figure, alone, then layered         statement
    bars  5-12  funk groove; the clave in the kick      motif in context
    bars 13-20  the motif travels; texture thickens     development
    bars 21-28  half-time shuffle, laid back, ghosts    contrast / space
    bars 29-36  Latin: cowbell clave, congas, timbales  color
    bars 37-44  the groove returns, bigger              recapitulation
    bars 45-52  trading twos, each pair louder          tension
    bars 53-58  climax: rolls, tom runs, one naked      release
                statement on claves, then the last push
    bars 59-61  the big hit; the figure once more,      cadence
                laid back and slowing, final downbeat

FEEL
----
Placement is deliberate, never random:
  * the kick plays ~3 ms on top of the beat; backbeats and ghost notes
    lay back; whole sections push ahead of or sit behind the pulse;
  * the shuffle swings through a warped triplet grid (2/3 -> 0.64 of the
    beat), and the motif is deliberately quoted in straight 16ths against
    that swing;
  * flams are real flams (a grace note ~23 ms ahead of the stroke).

PLAYABILITY
-----------
Every strike is tagged hand or foot, and the finished score is scanned so
that no instant (12 ms window) asks for more than two hands or two feet;
any accidental pile-up would be nudged into a flam.

Everything is deterministic, so the MIDI file is identical on every run.
"""

import math
import sys

import mido

# ----------------------------------------------------------------- constants

PPQ = 480                                # ticks per quarter note
BPM = 120.0                              # tempo; a gentle ritard ends it
TICKS_PER_MS = PPQ * BPM / 60000.0       # 0.96 ticks per ms at 120 bpm

# General MIDI percussion note numbers
KICK, SNARE, SIDE = 36, 38, 37                       # kick, snare, side stick
HH_C, HH_P, HH_O = 42, 44, 46                        # hat: closed/pedal/open
RIDE, BELL = 51, 53
CRASH, CRASH2, SPLASH = 49, 57, 55
TOM_H, TOM_MH, TOM_M, TOM_L, TOM_F, TOM_FL = 50, 48, 47, 45, 43, 41
TOMS = (TOM_H, TOM_MH, TOM_M, TOM_L, TOM_F)
CLAVES, COWBELL, TAMB = 75, 56, 54
WB_H, WB_L = 76, 77                                  # wood blocks
TIM_H, TIM_L = 65, 66                                # timbales
CG_M, CG_O = 62, 63                                  # conga: mute, open

CYMBALS = frozenset((CRASH, CRASH2, SPLASH, RIDE, BELL))

CLAVE = (0, 3, 6, 10, 12)                # the motif, as 16th-note slots
CLAVE23 = (2, 4, 8, 11, 14)              # the same figure, 2-3 side

MARKERS = (
    (0, 'the figure, alone'),
    (4, 'groove'),
    (12, 'development'),
    (20, 'half-time shuffle'),
    (28, 'latin'),
    (36, 'recapitulation'),
    (44, 'trading twos'),
    (52, 'climax'),
    (58, 'cadence'),
)

# deliberate placement per role, milliseconds (+ = early, - = late)
ROLE_MS = {
    'kick': +3.0,    # the foot plays on top of the beat
    'snare': 0.0,
    'back': -4.0,    # backbeats drag
    'ghost': -5.5,   # ghost notes drag more
    'ride': -2.0,
    'crash': +1.0,
    'hat': +1.5,
    'tom': -1.0,
    'perc': 0.0,
}


# -------------------------------------------------------------- feel, events

def sb(slot):
    """16th-note slot -> beats."""
    return slot / 4.0


def swing_phase(phase, a, b):
    """Warp the phase of a beat so triplet positions land on (a, b)."""
    if phase <= 0.0:
        return phase
    third = 1.0 / 3.0
    if phase < third:
        return phase * (a / third)
    if phase < 2.0 * third:
        return a + (phase - third) * ((b - a) / third)
    return b + (phase - 2.0 * third) * ((1.0 - b) / third)


def rubato(beats):
    """A smooth, deterministic breath of a few milliseconds."""
    return 2.2 * math.sin(beats * 0.71) + 1.5 * math.sin(beats * 0.191 + 1.2)


def vel_wobble(beats, note):
    """Small fixed velocity wobble (-3..+3) per note and position."""
    return ((int(round(beats * 48)) * 31 + note * 17) % 7) - 3


class Feel(object):
    def __init__(self, push=0.0, swing=None, lay=0.0, dyn=1.0):
        self.push = push        # section placement (ms; <0 = behind)
        self.swing = swing      # None, or (a, b) triplet warp
        self.lay = lay          # extra lay-back for backbeats (ms)
        self.dyn = dyn          # dynamic scale for the passage


class Score(object):
    def __init__(self):
        self.events = []
        self.feel = Feel()

    def set_feel(self, **kw):
        self.feel = Feel(**kw)

    def hit(self, bar, beat, note, vel, limb='H', role='perc',
            straight=False):
        """Place one strike.  bar is 0-based, beat lies in [0, 4)."""
        musical = bar * 4.0 + beat            # position before any feel
        f = self.feel
        beats = musical
        if f.swing is not None and not straight:
            whole = math.floor(beats)
            beats = whole + swing_phase(beats - whole, f.swing[0], f.swing[1])
        ms = f.push + ROLE_MS.get(role, 0.0)
        if role == 'back':
            ms += f.lay
        ms += rubato(musical)
        tick = int(round(beats * PPQ + ms * TICKS_PER_MS))
        if tick < 0:
            tick = 0
        v = int(round(vel * f.dyn)) + vel_wobble(musical, note)
        if v < 1:
            v = 1
        elif v > 127:
            v = 127
        dur = 600 if note in CYMBALS else 46
        self.events.append({'tick': tick, 'note': note, 'vel': v,
                            'limb': limb, 'dur': dur})


# ------------------------------------------------------------ pattern pieces

def hat8(sc, bar, base=62, skip=(), upto=16):
    """Closed hi-hat in 8ths with a small breathing accent pattern."""
    vels = (base + 4, base - 10, base - 2, base - 10,
            base + 2, base - 10, base - 2, base - 12)
    for i, slot in enumerate(range(0, 16, 2)):
        if slot in skip or slot >= upto:
            continue
        sc.hit(bar, sb(slot), HH_C, vels[i], 'H', 'hat')


def fill(sc, bar, pattern, kicks=()):
    """A single-line fill: (slot, note, vel, role) tuples, plus kicks."""
    for slot, note, v, role in pattern:
        sc.hit(bar, sb(slot), note, v, 'H', role)
    for slot, v in kicks:
        sc.hit(bar, sb(slot), KICK, v, 'F', 'kick')


def groove(sc, bar, dyn, kicks=(0, 6, 10), ghosts=(), crash=None,
           back=(4, 12), open_ands=False, hat_upto=16):
    """One bar of the funk groove; the clave lives in the kick."""
    sc.set_feel(push=3.0, swing=None, lay=-3.0, dyn=dyn)
    if crash is not None:
        sc.hit(bar, 0.0, crash, 120, 'H', 'crash')
    skip0 = (0,) if crash is not None else ()
    if open_ands:
        for slot in (0, 4, 8, 12):
            if slot in skip0 or slot >= hat_upto:
                continue
            sc.hit(bar, sb(slot), HH_C, 60, 'H', 'hat')
        for slot in (2, 6, 10, 14):
            if slot >= hat_upto:
                continue
            sc.hit(bar, sb(slot), HH_O, 72, 'H', 'hat')
    else:
        hat8(sc, bar, base=62, skip=skip0, upto=hat_upto)
    for slot, v in zip(back, (110, 116)):
        sc.hit(bar, sb(slot), SNARE, v, 'H', 'back')
    kv = {0: 106, 3: 90, 6: 92, 10: 98, 13: 86, 15: 84}
    for k in kicks:
        sc.hit(bar, sb(k), KICK, kv.get(k, 94), 'F', 'kick')
    for slot in ghosts:
        sc.hit(bar, sb(slot), SNARE, 30, 'H', 'ghost')


def shuffle_bar(sc, bar, dyn, bell=False, flam=False, kicks=(0.0, 8 / 3),
                ghosts=(2 / 3, 5 / 3, 7 / 3, 11 / 3), crash=False, gvel=30):
    """One bar of half-time shuffle: swung ride, backbeat on 3, ghosts."""
    sc.set_feel(push=-5.0, swing=(0.30, 0.64), lay=-9.0, dyn=dyn)
    pos = (0.0, 2 / 3, 1.0, 5 / 3, 2.0, 8 / 3, 3.0, 11 / 3)
    rvel = (76, 54, 66, 54, 72, 54, 66, 56)
    for p, v in zip(pos, rvel):
        if crash and p == 0.0:
            continue
        if bell and p == 0.0:
            sc.hit(bar, p, BELL, 90, 'H', 'ride')
        else:
            sc.hit(bar, p, RIDE, v, 'H', 'ride')
    if crash:
        sc.hit(bar, 0.0, CRASH, 112, 'H', 'crash')
    for k in kicks:
        sc.hit(bar, k, KICK, 96 if k == 0.0 else 88, 'F', 'kick')
    if flam:
        sc.hit(bar, 2.0 - 0.048, SNARE, 42, 'H', 'ghost')
    sc.hit(bar, 2.0, SNARE, 112, 'H', 'back')
    for p in ghosts:
        sc.hit(bar, p, SNARE, gvel, 'H', 'ghost')


def quote_bar(sc, bar, on_snare):
    """The motif quoted in straight 16ths over the shuffle (a cross-feel)."""
    shuffle_bar(sc, bar, 0.90, bell=True, flam=True)
    vels = (96, 78, 84, 88, 100) if on_snare else (100, 84, 88, 92, 104)
    for i, slot in enumerate(CLAVE):
        note = SNARE if on_snare else TOMS[i]
        role = 'snare' if on_snare else 'tom'
        sc.hit(bar, sb(slot), note, vels[i], 'H', role, straight=True)


def latin_bar(sc, bar, dyn, cow=CLAVE, crash=False, congas=False,
              side=(4, 12), extras=()):
    """One bar of the Latin groove: the clave on cowbell, kit underneath."""
    sc.set_feel(push=2.0, swing=None, lay=0.0, dyn=dyn)
    if crash:
        sc.hit(bar, 0.0, CRASH, 116, 'H', 'crash')
    for slot, v in zip(cow, (96, 74, 80, 86, 92)):
        if crash and slot == 0:
            continue
        sc.hit(bar, sb(slot), COWBELL, v, 'H', 'perc')
    for slot, v in zip(side, (90, 96)):
        sc.hit(bar, sb(slot), SIDE, v, 'H', 'perc')
    for slot, v in ((0, 104), (6, 90), (10, 96)):
        sc.hit(bar, sb(slot), KICK, v, 'F', 'kick')
    if congas:
        for slot, note, v in ((3, CG_M, 64), (6, CG_O, 84),
                              (11, CG_M, 68), (14, CG_O, 90)):
            sc.hit(bar, sb(slot), note, v, 'H', 'perc')
    for slot, note, v, role, limb in extras:
        sc.hit(bar, sb(slot), note, v, limb, role)


def recap_bar(sc, bar, dyn, crash=None, ghosts=(), kicks=(0, 6, 10),
              back=(4, 12), hat_upto=16):
    """The recapitulated groove: ride in 8ths, tambourine on the ands."""
    sc.set_feel(push=4.0, swing=None, lay=-3.0, dyn=dyn)
    rv = (78, 58, 68, 58, 74, 58, 68, 60)
    for i, slot in enumerate(range(0, 16, 2)):
        if slot >= hat_upto or (crash is not None and slot == 0):
            continue
        sc.hit(bar, sb(slot), RIDE, rv[i], 'H', 'ride')
    if crash is not None:
        sc.hit(bar, 0.0, crash, 122, 'H', 'crash')
    for slot in (2, 6, 10, 14):
        if slot >= hat_upto:
            continue
        sc.hit(bar, sb(slot), TAMB, 70, 'H', 'perc')
    for slot, v in zip(back, (112, 118)):
        sc.hit(bar, sb(slot), SNARE, v, 'H', 'back')
    kv = {0: 108, 3: 92, 6: 94, 10: 100, 13: 88}
    for k in kicks:
        sc.hit(bar, sb(k), KICK, kv.get(k, 94), 'F', 'kick')
    for slot in ghosts:
        sc.hit(bar, sb(slot), SNARE, 30, 'H', 'ghost')


# ---------------------------------------------------------------- the sections

def intro(sc):
    """Bars 1-4: state the figure, then dress it."""
    sc.set_feel(push=0.0, swing=None, lay=0.0, dyn=0.92)
    # bar 1: the figure, alone, on claves
    for slot, v in zip(CLAVE, (102, 72, 82, 88, 96)):
        sc.hit(0, sb(slot), CLAVES, v, 'H', 'perc')
    sc.hit(0, 0.0, KICK, 60, 'F', 'kick')
    # bar 2: on the side stick, with a pedal-hat pulse
    for slot, v in zip(CLAVE, (96, 68, 78, 84, 90)):
        sc.hit(1, sb(slot), SIDE, v, 'H', 'perc')
    for q in range(4):
        sc.hit(1, float(q), HH_P, 42, 'F', 'hat')
    sc.hit(1, 0.0, KICK, 54, 'F', 'kick')
    sc.hit(1, 2.5, KICK, 50, 'F', 'kick')
    # bar 3: on the snare, ghosts and hats filling the space
    for slot, v in zip(CLAVE, (104, 76, 86, 92, 106)):
        sc.hit(2, sb(slot), SNARE, v, 'H', 'snare')
    for slot in (2, 8, 14):
        sc.hit(2, sb(slot), SNARE, 30, 'H', 'ghost')
    hat8(sc, 2, base=60)
    sc.hit(2, 0.0, KICK, 96, 'F', 'kick')
    sc.hit(2, 2.5, KICK, 88, 'F', 'kick')
    # bar 4: handed to the toms, with a pickup into the groove
    for i, slot in enumerate(CLAVE):
        sc.hit(3, sb(slot), TOMS[i], (98, 84, 88, 92, 102)[i], 'H', 'tom')
    for slot in (0, 4, 8, 12):
        sc.hit(3, sb(slot), HH_C, 54, 'H', 'hat')
    sc.hit(3, 0.0, KICK, 94, 'F', 'kick')
    sc.hit(3, 3.0, KICK, 86, 'F', 'kick')
    sc.hit(3, 3.5, SNARE, 72, 'H', 'snare')
    sc.hit(3, 3.75, SNARE, 88, 'H', 'snare')


def section_groove_a(sc):
    """Bars 5-12: the funk groove, clave hidden in the kick, growing."""
    groove(sc, 4, 0.95, crash=CRASH)
    groove(sc, 5, 0.96, ghosts=(3,))
    groove(sc, 6, 0.97, ghosts=(3, 11), kicks=(0, 6, 10, 13))
    groove(sc, 7, 0.98, kicks=(0, 6), back=(4,), hat_upto=8)
    fill(sc, 7, ((8, SNARE, 92, 'snare'), (9, SNARE, 56, 'snare'),
                 (10, SNARE, 64, 'snare'), (11, SNARE, 96, 'snare'),
                 (12, TOM_MH, 100, 'tom'), (13, SNARE, 58, 'snare'),
                 (14, TOM_L, 102, 'tom'), (15, TOM_F, 96, 'tom')),
         kicks=((8, 90), (12, 94)))
    groove(sc, 8, 1.00, crash=CRASH2, ghosts=(3, 7))
    groove(sc, 9, 1.01, ghosts=(3, 11), open_ands=True, kicks=(0, 6, 10, 15))
    groove(sc, 10, 1.02, ghosts=(3, 7, 11), open_ands=True,
           kicks=(0, 6, 10, 13))
    groove(sc, 11, 1.03, kicks=(0, 6), back=(4,), hat_upto=8)
    fill(sc, 11, ((8, TOM_H, 96, 'tom'), (9, TOM_H, 62, 'tom'),
                  (10, TOM_MH, 100, 'tom'), (11, TOM_MH, 66, 'tom'),
                  (12, TOM_M, 104, 'tom'), (13, TOM_M, 68, 'tom'),
                  (14, TOM_L, 108, 'tom'), (15, TOM_F, 102, 'tom')),
         kicks=((8, 92), (12, 96)))


def section_dev(sc):
    """Bars 13-20: the motif migrates; density and weight increase."""
    # bar 13: toms take the motif
    sc.set_feel(push=4.0, swing=None, lay=-2.0, dyn=1.05)
    sc.hit(12, 0.0, CRASH, 122, 'H', 'crash')
    for i, slot in enumerate(CLAVE):
        sc.hit(12, sb(slot), TOMS[i], (104, 88, 92, 96, 108)[i], 'H', 'tom')
    hat8(sc, 12, base=58, skip=(0,))
    for slot, v in ((0, 106), (6, 92), (10, 98)):
        sc.hit(12, sb(slot), KICK, v, 'F', 'kick')
    # bar 14: the snare takes it back, hats open on the ands
    sc.set_feel(push=4.0, swing=None, lay=-2.0, dyn=1.06)
    for i, slot in enumerate(CLAVE):
        sc.hit(13, sb(slot), SNARE, (106, 78, 88, 94, 110)[i], 'H', 'snare')
    for slot in (0, 4, 8, 12):
        sc.hit(13, sb(slot), HH_C, 58, 'H', 'hat')
    for slot in (2, 6, 10, 14):
        sc.hit(13, sb(slot), HH_O, 72, 'H', 'hat')
    for slot in (8, 14):
        sc.hit(13, sb(slot), SNARE, 30, 'H', 'ghost')
    for slot, v in ((0, 104), (6, 92), (10, 98)):
        sc.hit(13, sb(slot), KICK, v, 'F', 'kick')
    # bars 15-16: the motif sinks into kick and floor tom
    for bar, dyn, ghosts in ((14, 1.06, ()), (15, 1.10, (2, 8, 14))):
        sc.set_feel(push=4.0, swing=None, lay=-2.0, dyn=dyn)
        if bar == 14:
            sc.hit(bar, 0.0, SPLASH, 96, 'H', 'crash')
        for i, slot in enumerate(CLAVE):
            sc.hit(bar, sb(slot), KICK, (112, 96, 102, 104, 108)[i], 'F',
                   'kick')
        for slot in (0, 10, 12):
            sc.hit(bar, sb(slot), TOM_F, 100 if slot == 0 else 96, 'H', 'tom')
        sc.hit(bar, 1.0, SNARE, 106, 'H', 'back')
        for slot in ghosts:
            sc.hit(bar, sb(slot), SNARE, 32, 'H', 'ghost')
    # bar 17: every 16th filled in; the accents still mark the motif
    sc.set_feel(push=4.0, swing=None, lay=-2.0, dyn=1.08)
    acc = dict(zip(CLAVE, (102, 80, 86, 92, 106)))
    for slot in range(16):
        if slot in acc:
            sc.hit(16, sb(slot), SNARE, acc[slot], 'H', 'snare')
        else:
            sc.hit(16, sb(slot), SNARE, 28 + (slot % 3) * 3, 'H', 'ghost')
    for slot, v in ((0, 104), (8, 96)):
        sc.hit(16, sb(slot), KICK, v, 'F', 'kick')
    for slot in (2, 10):
        sc.hit(16, sb(slot), HH_O, 66, 'H', 'hat')
    # bar 18: the toms answer
    sc.set_feel(push=4.0, swing=None, lay=-2.0, dyn=1.10)
    for i, slot in enumerate(CLAVE):
        sc.hit(17, sb(slot), TOMS[i], (102, 86, 90, 94, 106)[i], 'H', 'tom')
    for slot in (2, 6, 10, 14):
        sc.hit(17, sb(slot), HH_O, 74, 'H', 'hat')
    sc.hit(17, 2.0, SNARE, 30, 'H', 'ghost')
    for slot, v in ((0, 104), (6, 92), (10, 98)):
        sc.hit(17, sb(slot), KICK, v, 'F', 'kick')
    # bar 19: the roll that revs the engine
    sc.set_feel(push=4.0, swing=None, lay=-2.0, dyn=1.10)
    for slot in range(16):
        v = 38 + slot * 4.6
        if slot in CLAVE:
            v += 12
        sc.hit(18, sb(slot), SNARE, v, 'H', 'snare')
    for slot, v in ((0, 102), (8, 96), (12, 100)):
        sc.hit(18, sb(slot), KICK, v, 'F', 'kick')
    # bar 20: down the toms, into the shuffle
    sc.set_feel(push=4.0, swing=None, lay=-2.0, dyn=1.12)
    fill(sc, 19, ((0, SNARE, 104, 'snare'), (2, SNARE, 60, 'snare'),
                  (3, SNARE, 96, 'snare'), (4, TOM_H, 98, 'tom'),
                  (6, TOM_MH, 96, 'tom'), (7, SNARE, 64, 'snare'),
                  (8, TOM_M, 100, 'tom'), (10, TOM_L, 102, 'tom'),
                  (11, SNARE, 66, 'snare'), (12, TOM_F, 106, 'tom'),
                  (13, TOM_F, 72, 'tom'), (14, TOM_F, 96, 'tom'),
                  (15, TOM_FL, 104, 'tom')),
         kicks=((0, 102), (8, 96), (12, 100)))


def section_shuffle(sc):
    """Bars 21-28: half-time shuffle, laid way back, ghost-note texture."""
    shuffle_bar(sc, 20, 0.82, crash=True, ghosts=(2 / 3, 7 / 3, 11 / 3))
    shuffle_bar(sc, 21, 0.84)
    shuffle_bar(sc, 22, 0.86, flam=True, kicks=(0.0, 5 / 3, 8 / 3))
    shuffle_bar(sc, 23, 0.88, flam=True, ghosts=(2 / 3, 5 / 3, 7 / 3))
    for p, note, v, role in ((3.0, SNARE, 72, 'snare'),
                             (10 / 3, SNARE, 86, 'snare'),
                             (11 / 3, TOM_F, 102, 'tom')):
        sc.hit(23, p, note, v, 'H', role)
    # bars 25-26: the motif quotes itself in straight 16ths across the swing
    quote_bar(sc, 24, True)
    quote_bar(sc, 25, False)
    shuffle_bar(sc, 26, 0.92, bell=True, flam=True, kicks=(0.0, 5 / 3, 8 / 3))
    # bar 28: triplet fill out of the section
    sc.set_feel(push=-5.0, swing=(0.30, 0.64), lay=-9.0, dyn=0.94)
    for p, v in ((0.0, 78), (2 / 3, 56), (1.0, 68), (5 / 3, 56)):
        sc.hit(27, p, RIDE, v, 'H', 'ride')
    sc.hit(27, 0.0, KICK, 96, 'F', 'kick')
    sc.hit(27, 2.0 - 0.048, SNARE, 42, 'H', 'ghost')
    sc.hit(27, 2.0, SNARE, 110, 'H', 'back')
    for p, note, v, role in ((7 / 3, SNARE, 74, 'snare'),
                             (8 / 3, TOM_MH, 86, 'tom'),
                             (3.0, SNARE, 84, 'snare'),
                             (10 / 3, TOM_L, 96, 'tom'),
                             (11 / 3, TOM_F, 108, 'tom')):
        sc.hit(27, p, note, v, 'H', role)
    sc.hit(27, 3.0, KICK, 90, 'F', 'kick')


def section_latin(sc):
    """Bars 29-36: the clave moves to the cowbell; congas and timbales."""
    latin_bar(sc, 28, 1.02, crash=True)
    latin_bar(sc, 29, 1.04, congas=True)
    latin_bar(sc, 30, 1.06, congas=True)
    latin_bar(sc, 31, 1.06, side=(4,), extras=(
        (8, TIM_H, 88, 'perc', 'H'), (9, TIM_L, 66, 'perc', 'H'),
        (10, TIM_H, 92, 'perc', 'H'), (11, TIM_L, 84, 'perc', 'H'),
        (12, TIM_H, 96, 'perc', 'H'), (13, TIM_L, 74, 'perc', 'H'),
        (14, TIM_H, 100, 'perc', 'H'), (15, TIM_L, 108, 'perc', 'H')))
    latin_bar(sc, 32, 1.08, crash=True, congas=True)
    latin_bar(sc, 33, 1.10, cow=CLAVE23, congas=True, extras=(
        (0, TIM_H, 94, 'perc', 'H'), (8, TIM_H, 90, 'perc', 'H')))
    latin_bar(sc, 34, 1.12, cow=CLAVE23, congas=True, extras=(
        (0, TIM_H, 96, 'perc', 'H'), (8, TIM_H, 92, 'perc', 'H'),
        (12, TIM_L, 94, 'perc', 'H'), (3, SNARE, 32, 'ghost', 'H')))
    # bar 36: the timbale roll
    sc.set_feel(push=2.0, swing=None, lay=0.0, dyn=1.14)
    for slot in range(16):
        note = TIM_H if slot % 2 == 0 else TIM_L
        v = 58 + slot * 4.0
        if slot in (0, 6, 10, 12):
            v += 10
        sc.hit(35, sb(slot), note, v, 'H', 'perc')
    for slot, v in ((0, 106), (8, 100), (12, 104)):
        sc.hit(35, sb(slot), KICK, v, 'F', 'kick')
    for slot in (4, 12):
        sc.hit(35, sb(slot), SNARE, 104, 'H', 'back')


def section_recap(sc):
    """Bars 37-44: the groove returns, bigger; then a drop and a build."""
    recap_bar(sc, 36, 1.08, crash=CRASH, ghosts=(3, 11))
    recap_bar(sc, 37, 1.10, ghosts=(3, 7, 11, 15), kicks=(0, 6, 10, 13))
    recap_bar(sc, 38, 1.10, ghosts=(3, 11), kicks=(0, 3, 6, 10, 13))
    recap_bar(sc, 39, 1.10, ghosts=(3,), kicks=(0, 6), back=(4,), hat_upto=8)
    fill(sc, 39, ((8, SNARE, 96, 'snare'), (9, SNARE, 60, 'snare'),
                  (10, SNARE, 70, 'snare'), (11, SNARE, 100, 'snare'),
                  (12, TOM_MH, 104, 'tom'), (13, SNARE, 64, 'snare'),
                  (14, TOM_L, 108, 'tom'), (15, TOM_F, 104, 'tom')),
         kicks=((8, 92), (12, 98)))
    recap_bar(sc, 40, 1.12, crash=CRASH2, ghosts=(3, 7, 11))
    recap_bar(sc, 41, 1.14, ghosts=(3, 7, 11, 15), kicks=(0, 3, 6, 10, 13))
    # bar 43: the drop-out -- claves again, as at the very start
    sc.set_feel(push=0.0, swing=None, lay=0.0, dyn=0.92)
    for slot, v in zip(CLAVE, (94, 70, 80, 86, 96)):
        sc.hit(42, sb(slot), CLAVES, v, 'H', 'perc')
    for slot, v in ((0, 96), (6, 84), (10, 90)):
        sc.hit(42, sb(slot), KICK, v, 'F', 'kick')
    for slot in (8, 12):
        sc.hit(42, sb(slot), HH_P, 44, 'F', 'hat')
    # bar 44: the big build into the trading
    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.12)
    for slot in range(12):
        v = 44 + slot * 5.6
        if slot in (0, 6):
            v += 12
        sc.hit(43, sb(slot), SNARE, v, 'H', 'snare')
    for slot, note, v in ((12, TOM_MH, 104), (13, TOM_M, 100),
                          (14, TOM_L, 106), (15, TOM_F, 112)):
        sc.hit(43, sb(slot), note, v, 'H', 'tom')
    for slot, v in ((0, 100), (8, 96), (12, 102)):
        sc.hit(43, sb(slot), KICK, v, 'F', 'kick')


def section_trading(sc):
    """Bars 45-52: trading twos with ourselves, each pair louder."""
    # pair 1: motif on snare, answered by toms
    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.06)
    sc.hit(44, 0.0, CRASH, 116, 'H', 'crash')
    for i, slot in enumerate(CLAVE):
        sc.hit(44, sb(slot), SNARE, (102, 76, 86, 92, 106)[i], 'H', 'snare')
    for slot in (2, 8, 14):
        sc.hit(44, sb(slot), SNARE, 30, 'H', 'ghost')
    sc.hit(44, 2.0, HH_C, 60, 'H', 'hat')
    for slot, v in ((0, 104), (6, 92), (10, 98)):
        sc.hit(44, sb(slot), KICK, v, 'F', 'kick')

    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.08)
    for i, slot in enumerate(CLAVE):
        sc.hit(45, sb(slot), TOMS[i], (100, 84, 90, 94, 104)[i], 'H', 'tom')
    for slot in (2, 6, 10):
        sc.hit(45, sb(slot), HH_O, 72, 'H', 'hat')
    for slot, v in ((0, 104), (6, 92), (10, 98)):
        sc.hit(45, sb(slot), KICK, v, 'F', 'kick')

    # pair 2: the motif with all its spaces filled; then to the kick
    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.12)
    acc = dict(zip(CLAVE, (104, 80, 86, 92, 108)))
    for slot in range(16):
        if slot in acc:
            sc.hit(46, sb(slot), SNARE, acc[slot], 'H', 'snare')
        else:
            sc.hit(46, sb(slot), SNARE, 30, 'H', 'ghost')
    for slot, v in ((0, 104), (6, 92), (10, 98)):
        sc.hit(46, sb(slot), KICK, v, 'F', 'kick')

    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.14)
    sc.hit(47, 0.0, CRASH, 118, 'H', 'crash')
    for i, slot in enumerate(CLAVE):
        sc.hit(47, sb(slot), KICK, (110, 94, 100, 102, 106)[i], 'F', 'kick')
    for slot, v in ((4, 108), (12, 112)):
        sc.hit(47, sb(slot), SNARE, v, 'H', 'back')
    for slot in (2, 6):
        sc.hit(47, sb(slot), HH_O, 74, 'H', 'hat')
    for slot in (8, 14):
        sc.hit(47, sb(slot), SNARE, 30, 'H', 'ghost')

    # pair 3: wood blocks against the snare, answered by toms and crash
    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.16)
    for slot, note, v in ((0, WB_H, 98), (3, WB_H, 78), (6, WB_L, 86),
                          (10, SNARE, 100), (12, SNARE, 108)):
        sc.hit(48, sb(slot), note, v, 'H',
               'snare' if note == SNARE else 'perc')
    for slot in (2, 8, 14):
        sc.hit(48, sb(slot), SNARE, 28, 'H', 'ghost')
    for slot, v in ((0, 104), (6, 92), (10, 98)):
        sc.hit(48, sb(slot), KICK, v, 'F', 'kick')

    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.18)
    sc.hit(49, 0.0, CRASH, 120, 'H', 'crash')
    for i, slot in enumerate(CLAVE):
        sc.hit(49, sb(slot), TOMS[i], (106, 88, 94, 98, 110)[i], 'H', 'tom')
    sc.hit(49, 2.0, SNARE, 30, 'H', 'ghost')
    for slot, note, v, role in ((13, SNARE, 62, 'snare'),
                                (14, SNARE, 78, 'snare'),
                                (15, TOM_H, 96, 'tom')):
        sc.hit(49, sb(slot), note, v, 'H', role)
    for slot, v in ((0, 106), (6, 94), (10, 100)):
        sc.hit(49, sb(slot), KICK, v, 'F', 'kick')

    # pair 4: the send-up -- crescendo roll, then around the toms
    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.20)
    for slot in range(16):
        v = 42 + slot * 5.0
        if slot in CLAVE:
            v += 12
        sc.hit(50, sb(slot), SNARE, v, 'H', 'snare')
    for slot, v in ((0, 100), (8, 96)):
        sc.hit(50, sb(slot), KICK, v, 'F', 'kick')

    sc.set_feel(push=5.0, swing=None, lay=-2.0, dyn=1.22)
    sc.hit(51, 0.0, CRASH, 120, 'H', 'crash')
    run = ((TOM_H, 104), (TOM_H, 66), (TOM_MH, 100), (TOM_MH, 68),
           (TOM_M, 104), (TOM_M, 70), (TOM_L, 106), (TOM_L, 72),
           (TOM_F, 110), (TOM_F, 74), (TOM_FL, 112), (TOM_FL, 78),
           (TOM_F, 114), (TOM_F, 80), (TOM_F, 108), (TOM_F, 118))
    for slot, (note, v) in enumerate(run):
        sc.hit(51, sb(slot), note, v, 'H', 'tom')
    for slot, v in ((0, 104), (8, 100), (12, 104)):
        sc.hit(51, sb(slot), KICK, v, 'F', 'kick')


def section_climax(sc):
    """Bars 53-58: everything out, one naked statement, then the push."""
    # bar 53: everything out
    sc.set_feel(push=3.0, swing=None, lay=-2.0, dyn=1.26)
    sc.hit(52, 0.0, CRASH, 126, 'H', 'crash')
    rv = (78, 58, 68, 58, 74, 58, 68, 60)
    for i, slot in enumerate(range(2, 16, 2)):
        sc.hit(52, sb(slot), RIDE, rv[i + 1], 'H', 'ride')
    for slot in (2, 6, 10, 14):
        sc.hit(52, sb(slot), TAMB, 74, 'H', 'perc')
    for slot, v in ((4, 116), (12, 122)):
        sc.hit(52, sb(slot), SNARE, v, 'H', 'back')
    for slot, v in ((0, 112), (6, 98), (10, 104), (13, 92)):
        sc.hit(52, sb(slot), KICK, v, 'F', 'kick')
    for slot in (3, 7, 11, 15):
        sc.hit(52, sb(slot), SNARE, 34, 'H', 'ghost')

    # bar 54: the motif, fortissimo, split between kick and toms
    sc.set_feel(push=3.0, swing=None, lay=-2.0, dyn=1.28)
    sc.hit(53, 0.0, CRASH2, 124, 'H', 'crash')
    for i, slot in enumerate(CLAVE):
        sc.hit(53, sb(slot), KICK, (114, 98, 104, 106, 110)[i], 'F', 'kick')
        sc.hit(53, sb(slot), TOMS[i], (110, 92, 96, 102, 114)[i], 'H', 'tom')
    sc.hit(53, 1.0, SNARE, 112, 'H', 'back')

    # bar 55: a 32nd-note single-stroke roll; the motif rides on top
    sc.set_feel(push=3.0, swing=None, lay=-2.0, dyn=1.28)
    sc.hit(54, 0.0, CRASH, 120, 'H', 'crash')
    for i in range(32):
        v = 52 + i * 1.6
        if i in (0, 6, 12, 20, 24):      # 2 x the clave slots
            v += 16
        sc.hit(54, i * 0.125, SNARE, v, 'H', 'snare')
    for slot, v in ((0, 108), (8, 100)):
        sc.hit(54, sb(slot), KICK, v, 'F', 'kick')

    # bar 56: around the kit, kick doubling the accents
    sc.set_feel(push=3.0, swing=None, lay=-2.0, dyn=1.28)
    run = ((TOM_H, 108), (TOM_MH, 74), (TOM_MH, 104), (TOM_M, 78),
           (TOM_M, 106), (TOM_L, 80), (TOM_L, 108), (TOM_F, 84),
           (TOM_F, 110), (TOM_FL, 82), (TOM_FL, 112), (TOM_F, 86),
           (TOM_F, 114), (TOM_F, 88), (TOM_F, 116), (TOM_FL, 120))
    for slot, (note, v) in enumerate(run):
        sc.hit(55, sb(slot), note, v, 'H', 'tom')
    for slot, v in ((0, 108), (4, 100), (8, 104), (12, 106)):
        sc.hit(55, sb(slot), KICK, v, 'F', 'kick')

    # bar 57: sudden air -- the motif, naked, on claves, as it began
    sc.set_feel(push=0.0, swing=None, lay=0.0, dyn=0.88)
    for slot, v in zip(CLAVE, (96, 70, 80, 86, 96)):
        sc.hit(56, sb(slot), CLAVES, v, 'H', 'perc')
    sc.hit(56, 0.0, KICK, 84, 'F', 'kick')
    sc.hit(56, 2.5, KICK, 76, 'F', 'kick')
    for b in (1.0, 3.0):
        sc.hit(56, b, HH_P, 40, 'F', 'hat')

    # bar 58: the final push
    sc.set_feel(push=3.0, swing=None, lay=-2.0, dyn=1.28)
    sc.hit(57, 0.0, CRASH, 124, 'H', 'crash')
    line = ((0, SNARE, 114, 'snare'), (1, SNARE, 72, 'snare'),
            (2, SNARE, 84, 'snare'), (3, SNARE, 102, 'snare'),
            (4, TOM_H, 108, 'tom'), (6, TOM_MH, 106, 'tom'),
            (7, SNARE, 70, 'snare'), (8, TOM_M, 110, 'tom'),
            (10, TOM_L, 112, 'tom'), (11, SNARE, 74, 'snare'),
            (12, TOM_F, 116, 'tom'), (13, TOM_F, 84, 'tom'),
            (14, TOM_F, 104, 'tom'), (15, TOM_FL, 120, 'tom'))
    for slot, note, v, role in line:
        sc.hit(57, sb(slot), note, v, 'H', role)
    for slot, v in ((0, 112), (4, 100), (8, 102), (12, 104)):
        sc.hit(57, sb(slot), KICK, v, 'F', 'kick')


def section_ending(sc):
    """Bar 59: the big hit, then air.  Bar 60: the figure once more."""
    sc.set_feel(push=0.0, swing=None, lay=0.0, dyn=1.30)
    sc.hit(58, 0.0, CRASH2, 127, 'H', 'crash')
    sc.hit(58, 0.0, SNARE, 124, 'H', 'snare')
    sc.hit(58, 0.0, KICK, 120, 'F', 'kick')
    sc.hit(58, 3.0, SNARE, 32, 'H', 'ghost')
    sc.hit(58, 3.5, SNARE, 46, 'H', 'ghost')

    # bar 60 (ritard begins): the figure one last time, laid back
    sc.set_feel(push=-6.0, swing=None, lay=0.0, dyn=0.90)
    for slot, v in zip(CLAVE, (92, 66, 76, 82, 92)):
        sc.hit(59, sb(slot), CLAVES, v, 'H', 'perc')
    sc.hit(59, 0.0, KICK, 80, 'F', 'kick')
    sc.hit(59, 2.5, KICK, 72, 'F', 'kick')
    for b in (1.0, 3.0):
        sc.hit(59, b, HH_P, 38, 'F', 'hat')
    # a soft flam picks the final downbeat up
    sc.hit(59, 3.5 - 0.048, SNARE, 36, 'H', 'ghost')
    sc.hit(59, 3.5, SNARE, 56, 'H', 'snare')

    # the last word: the downbeat of the (unwritten) next bar
    sc.set_feel(push=0.0, swing=None, lay=0.0, dyn=1.28)
    sc.hit(60, 0.0, CRASH, 124, 'H', 'crash')
    sc.hit(60, 0.0, SNARE, 120, 'H', 'snare')
    sc.hit(60, 0.0, KICK, 116, 'F', 'kick')


def build_score():
    sc = Score()
    intro(sc)
    section_groove_a(sc)
    section_dev(sc)
    section_shuffle(sc)
    section_latin(sc)
    section_recap(sc)
    section_trading(sc)
    section_climax(sc)
    section_ending(sc)
    return sc.events


# ----------------------------------------------------------------- clean-up

def dedupe(events):
    """Never trigger the same note twice on the same tick."""
    events.sort(key=lambda e: (e['tick'], e['note'], -e['vel']))
    out = []
    for e in events:
        if out and out[-1]['tick'] == e['tick'] \
                and out[-1]['note'] == e['note']:
            continue
        out.append(e)
    events[:] = out


def enforce_limbs(events, window=12, nudge=14):
    """At most two hands and two feet strike at any instant.

    Anything piled up inside the window is nudged later, which turns an
    accidental chord into a flam -- still something a drummer can play.
    """
    for _ in range(400):
        moved = False
        for limb in ('H', 'F'):
            evs = sorted((e for e in events if e['limb'] == limb),
                         key=lambda e: e['tick'])
            n = len(evs)
            for i in range(n):
                j = i + 1
                while j < n and evs[j]['tick'] - evs[i]['tick'] <= window:
                    j += 1
                if j - i > 2:
                    for k in range(i + 2, j):
                        evs[k]['tick'] += nudge
                    moved = True
                    break
            if moved:
                break
        if not moved:
            return True
    return False


def fix_durations(events):
    """Every note is off before the same note is struck again."""
    events.sort(key=lambda e: (e['tick'], e['note']))
    nxt = {}
    for e in reversed(events):
        if e['note'] in nxt:
            gap = nxt[e['note']] - e['tick']
            e['dur'] = max(3, min(e['dur'], gap - 1))
        nxt[e['note']] = e['tick']


# -------------------------------------------------------------------- MIDI

def ritard():
    """Tempo map for the close: beat 232.5 onward, 120 bpm easing to ~85."""
    out = []
    for i in range(1, 16):
        beat = 232.0 + i * 0.5
        t = (beat - 232.0) / 8.0
        out.append((beat, 120.0 - 38.0 * (t ** 1.25)))
    return out


def total_seconds(last_tick):
    end = last_tick / float(PPQ)
    sec = 0.0
    cur_beat, cur_bpm = 0.0, BPM
    for beat, bpm in ritard():
        if beat >= end:
            break
        sec += (beat - cur_beat) * 60.0 / cur_bpm
        cur_beat, cur_bpm = beat, bpm
    sec += (end - cur_beat) * 60.0 / cur_bpm
    return sec


def emit_track(track, items):
    """items: (tick, priority, message); lower priority first at a tick."""
    items = sorted(items, key=lambda x: (x[0], x[1]))
    last = 0
    for tick, _prio, msg in items:
        dt = tick - last
        if dt < 0:
            dt = 0
        track.append(msg.copy(time=dt))
        last = tick


def write_midi(events, path):
    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)

    meta_track = mido.MidiTrack()
    note_track = mido.MidiTrack()
    mid.tracks.append(meta_track)
    mid.tracks.append(note_track)

    metas = [(0, 0, mido.MetaMessage('track_name',
                                     name='Two Minutes of Drums', time=0)),
             (0, 1, mido.MetaMessage('time_signature', numerator=4,
                                     denominator=4, time=0)),
             (0, 2, mido.MetaMessage('set_tempo',
                                     tempo=mido.bpm2tempo(BPM), time=0))]
    for bar, text in MARKERS:
        metas.append((bar * 4 * PPQ, 3,
                      mido.MetaMessage('marker', text=text, time=0)))
    for beat, bpm in ritard():
        metas.append((int(round(beat * PPQ)), 2,
                      mido.MetaMessage('set_tempo',
                                       tempo=mido.bpm2tempo(bpm), time=0)))
    emit_track(meta_track, metas)

    notes = [(0, 0, mido.MetaMessage('track_name', name='drums', time=0))]
    for e in events:
        notes.append((e['tick'], 4,
                      mido.Message('note_on', channel=9, note=e['note'],
                                   velocity=e['vel'], time=0)))
        notes.append((e['tick'] + e['dur'], 1,
                      mido.Message('note_off', channel=9, note=e['note'],
                                   velocity=0, time=0)))
    emit_track(note_track, notes)

    mid.save(path)


def main():
    events = build_score()
    dedupe(events)
    converged = enforce_limbs(events)
    if not converged:
        sys.stderr.write('warning: limb collisions were not fully resolved\n')
    dedupe(events)
    fix_durations(events)
    # let the very last cymbal ring
    for e in events:
        if e['note'] in CYMBALS and e['tick'] >= 60 * 4 * PPQ - 10:
            e['dur'] = 1440
    events.sort(key=lambda e: e['tick'])
    write_midi(events, 'solo.mid')
    last = max(e['tick'] + e['dur'] for e in events)
    print('wrote solo.mid: %d strikes on channel 10, %.1f s of music'
          % (len(events), total_seconds(last)))


if __name__ == '__main__':
    main()
