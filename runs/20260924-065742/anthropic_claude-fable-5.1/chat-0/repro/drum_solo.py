#!/usr/bin/env python3
"""
drum_solo.py  --  writes solo.mid: a two-minute General MIDI drum solo on channel 10.

Form (96 BPM, 4/4, 48 bars = 120 s):
  bars  0-3   Intro     : motif A (tresillo + backbeat, x..x..x...x.x...) stated on cross-stick
                          over a foot hi-hat pulse; the kick gradually takes the motif over.
  bars  4-11  Groove    : A as a swung-16th funk groove with ghost notes; A orchestrated
                          onto open hi-hats; motif B (a 6-tom descending run, 1&a2&a)
                          appears first as an answer, then as a whole-bar fill.
  bars 12-19  Dialogue  : call (A on ride bell) / response (B, then B inverted, then B from
                          the snare); both motifs combined; A on floor tom + kick; roll.
  bars 20-27  Interlude : release. Feet keep a fragment of A while the hands move to
                          claves, wood blocks, congas, bongos, cowbell, foot tambourine,
                          ending with a timbale build.
  bars 28-35  Build     : A augmented (2:1) in half time on the ride, back to tempo,
                          then the tresillo fragment looped as a 3-against-4 hemiola into
                          a crescendo snare roll.
  bars 36-43  Climax    : A with crashes/china, A played on cymbals, B fills,
                          A in diminution (32nds), full-stop tresillo hits.
  bars 44-47  Outro     : the intro texture returns; last tresillo; final crash.

Feel: 16th swing (~61%), backbeats laid back, syncopated kicks pushed, ghost notes lagging
slightly, cymbals leading slightly, plus a per-section lean. No random timing jitter
(only a seeded +-3 velocity shimmer). A limiter guarantees <= 2 hands and <= 2 feet strike
within any 30-tick window. Output is byte-identical on every run.
"""
import math
import random

from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

# ----------------------------------------------------------------------------- constants
BPM = 96
TPB = 480
S16 = TPB // 4              # ticks per sixteenth
CH = 9                      # MIDI channel 10 (zero-based)

SWING = 26                  # 'e' and 'a' sixteenths delayed (~61 % swing)
LAYBACK = 14                # backbeat snares behind the beat
GHOST_LAG = 6               # ghost notes sit a hair late
PUSH = 9                    # syncopated kicks lean forward
CYM_LEAD = 2                # cymbals/hats slightly ahead
FLAM = 24                   # grace-note distance

# General MIDI percussion
KICK2, KICK, SIDE, SNARE, CLAP, ESNARE = 35, 36, 37, 38, 39, 40
FLOOR_LO, HH_CLOSED, FLOOR_HI, HH_PEDAL, TOM_LO, HH_OPEN = 41, 42, 43, 44, 45, 46
TOM_LOMID, TOM_HIMID, CRASH1, TOM_HI, RIDE, CHINA, RIDE_BELL = 47, 48, 49, 50, 51, 52, 53
TAMB, SPLASH, COWBELL, CRASH2, VIBRA, RIDE2 = 54, 55, 56, 57, 58, 59
BONGO_HI, BONGO_LO, CONGA_MUTE, CONGA_HI, CONGA_LO = 60, 61, 62, 63, 64
TIMB_HI, TIMB_LO, AGOGO_HI, AGOGO_LO, CABASA, MARACAS = 65, 66, 67, 68, 69, 70
WHISTLE_S, WHISTLE_L, GUIRO_S, GUIRO_L, CLAVES, WB_HI, WB_LO = 71, 72, 73, 74, 75, 76, 77
CUICA_M, CUICA_O, TRI_MUTE, TRI_OPEN = 78, 79, 80, 81

FEET = {KICK, KICK2, HH_PEDAL}
CYMS = {HH_CLOSED, HH_OPEN, RIDE, RIDE_BELL, RIDE2, CRASH1, CRASH2, CHINA, SPLASH}
LONG_NOTES = {CRASH1, CRASH2, CHINA, SPLASH, RIDE, RIDE_BELL, HH_OPEN, TRI_OPEN}

# motifs
A_KICK = (0, 3, 6, 10)               # tresillo: 3 + 3 + 2 ... then the '&' of 3
A_RHYTHM = (0, 3, 6, 10, 12)         # ... completed by the backbeat on 4
B_RHYTHM = (0, 2, 3, 4, 6, 7)        # "1 & a 2 & a"
DESC = (TOM_HI, TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO, FLOOR_LO)
DESC2 = (TOM_LOMID, TOM_LO, TOM_LO, FLOOR_HI, FLOOR_LO, FLOOR_LO)
ASC = (FLOOR_LO, FLOOR_HI, TOM_LO, TOM_LOMID, TOM_HIMID, TOM_HI)
SN_DESC = (SNARE, SNARE, TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LO)
LOW_TO_SN = (FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, SNARE, SNARE)
DIMIN = (0, 1.5, 3, 5, 6)            # motif A at double speed (32nds)

rng = random.Random(1969)
events = []                          # (tick, note, velocity, limb)
state = {"dyn": 1.0, "lean": 0, "bb": {4, 12}}


# ----------------------------------------------------------------------------- timing
def set_feel(dyn=None, lean=None, bb=None):
    if dyn is not None:
        state["dyn"] = dyn
    if lean is not None:
        state["lean"] = lean
    if bb is not None:
        state["bb"] = set(bb)


def swung(apos):
    """Absolute position in sixteenths -> ticks on the swung grid (32nds interpolate)."""
    lo = math.floor(apos)
    frac = apos - lo

    def grid(p):
        t = p * S16
        if p % 4 in (1, 3):
            t += SWING
        return t

    if frac < 1e-9:
        return grid(lo)
    return grid(lo) + frac * (grid(lo + 1) - grid(lo))


def feel_offset(note, pos, vel):
    ip = int(round(pos)) if abs(pos - round(pos)) < 1e-9 else None
    if ip is not None:
        if note == SNARE and vel >= 85 and (ip % 16) in state["bb"]:
            return LAYBACK
        if note in (SNARE, SIDE) and vel < 60:
            return GHOST_LAG
        if note in (KICK, KICK2) and ip % 4 != 0:
            return -PUSH
    if note in CYMS:
        return -CYM_LEAD
    return 0


def add(bar, pos, note, vel, limb=None, offset=0, feel=True):
    tick = swung(bar * 16 + pos) + state["lean"] + offset
    if feel:
        tick += feel_offset(note, pos, vel)
    v = vel * state["dyn"] + rng.randint(-3, 3)
    v = int(max(18, min(127, round(v))))
    if limb is None:
        limb = "foot" if note in FEET else "hand"
    events.append((int(round(max(0, tick))), note, v, limb))


# ----------------------------------------------------------------------------- vocabulary
def hats(bar, opens=(), skip=(), acc=92, mid=68, low=50, dense=True):
    for i in range(16):
        if i in skip or (not dense and i % 2):
            continue
        v = acc if i % 4 == 0 else (mid if i % 2 == 0 else low)
        if i in opens:
            add(bar, i, HH_OPEN, max(v, 86))
        else:
            add(bar, i, HH_CLOSED, v)


def pedal(bar, positions, vel=62):
    for p in positions:
        add(bar, p, HH_PEDAL, vel)


def kicks(bar, positions=A_KICK, vel=106):
    for p in positions:
        add(bar, p, KICK, vel)


def snares(bar, positions=(4, 12), vel=114):
    for p in positions:
        add(bar, p, SNARE, vel)


def ghosts(bar, positions, vel=42):
    for p in positions:
        add(bar, p, SNARE, vel)


def flam(bar, pos, note=SNARE, vel=116):
    fo = feel_offset(note, pos, vel)
    add(bar, pos, note, vel - 40, offset=fo - FLAM, feel=False)
    add(bar, pos, note, vel)


def cym(bar, pos, note=CRASH1, vel=112, kick=True):
    add(bar, pos, note, vel)
    if kick:
        add(bar, pos, KICK, 112)


def ride(bar, bells=(), skip=(), acc=90, low=70):
    for i in range(0, 16, 2):
        if i in skip or i in bells:
            continue
        add(bar, i, RIDE, acc if i % 4 == 0 else low)
    for b in bells:
        add(bar, b, RIDE_BELL, 104)


def cell(bar, start, notes, vel=100, rhythm=B_RHYTHM, accents=(0, 4)):
    for r, n in zip(rhythm, notes):
        add(bar, start + r, n, vel + 12 if r in accents else vel)


def roll(bar, start, end, v0, v1, note=SNARE, step=0.5):
    n = int(round((end - start) / step))
    for k in range(n):
        v = v0 + (v1 - v0) * (k / max(1, n - 1))
        add(bar, start + k * step, note, v)


# ----------------------------------------------------------------------------- sections
def intro():                                   # bars 0-3
    set_feel(dyn=0.85, lean=2, bb={4, 12})
    for b in (0, 1):                           # motif A alone, cross-stick over foot hat
        pedal(b, (0, 4, 8, 12), 64)
        for p in A_RHYTHM:
            add(b, p, SIDE, 96 if p in (0, 12) else 84)
    ghosts(1, (7, 9, 14))
    pedal(2, (0, 2, 4, 6, 8, 10, 12, 14), 58)  # kick takes the motif
    kicks(2, A_KICK, 100)
    add(2, 4, SIDE, 96)
    add(2, 12, SIDE, 96)
    ghosts(2, (7, 9, 15))
    hats(3, skip=(14, 15), acc=80, mid=60, low=44)   # hats arrive, pickup into groove
    kicks(3, A_KICK, 104)
    snares(3, (4, 12), 108)
    ghosts(3, (7, 9))
    add(3, 14, SNARE, 78)
    add(3, 15, SNARE, 96)


def section_a():                               # bars 4-11
    set_feel(dyn=1.0, lean=0)
    cym(4, 0, CRASH1, 114)
    hats(4, skip=(0,)); kicks(4); snares(4); ghosts(4, (7, 15))
    hats(5, opens=(14,)); kicks(5); snares(5); ghosts(5, (2, 7, 9, 15))
    hats(6); kicks(6, A_KICK + (14,)); snares(6); ghosts(6, (7, 9))
    # half groove, half answer: motif B on the toms
    hats(7, skip=range(8, 16)); kicks(7, A_KICK); snares(7, (4,)); ghosts(7, (2, 7))
    cell(7, 8, DESC, 98)
    add(7, 12, KICK, 100)
    # A orchestrated onto the open hi-hats
    cym(8, 0, CRASH2, 110)
    hats(8, opens=(3, 6, 10), skip=(0,)); kicks(8); snares(8); ghosts(8, (7, 15))
    hats(9, opens=(3, 6, 10)); kicks(9); snares(9); ghosts(9, (2, 7, 9, 15))
    hats(10, skip=(12,)); kicks(10, A_KICK + (14,)); snares(10, (4,))
    flam(10, 12, SNARE, 116); ghosts(10, (2, 7, 9))
    # whole-bar B, feet keeping time
    kicks(11, (0, 4, 8, 12), 104); pedal(11, (2, 6, 10, 14), 60)
    cell(11, 0, SN_DESC, 100); cell(11, 8, DESC2, 104)


def section_b():                               # bars 12-19
    set_feel(dyn=1.0, lean=-3)
    cym(12, 0, CRASH1, 116)                    # call: A on the ride bell
    ride(12, bells=(3, 6, 10), skip=(0, 2)); kicks(12); snares(12); ghosts(12, (7, 15))
    kicks(13, (0, 4, 8, 12), 104); pedal(13, (2, 6, 10, 14))   # response: B, then inverted
    cell(13, 0, DESC, 100); cell(13, 8, ASC, 100)
    cym(14, 0, CRASH2, 112)
    ride(14, bells=(3, 6, 10), skip=(0, 2)); kicks(14, A_KICK + (14,)); snares(14)
    ghosts(14, (2, 7, 9, 15))
    kicks(15, (0, 4, 8, 12), 104); pedal(15, (2, 6, 10, 14))   # response from the snare
    cell(15, 0, SN_DESC, 100); cell(15, 8, LOW_TO_SN, 102)
    cym(16, 0, CRASH1, 116)                    # both motifs in one phrase
    ride(16, bells=(3, 6, 10), skip=(0, 2)); kicks(16); snares(16); ghosts(16, (7, 15))
    ride(17, bells=(3, 6), skip=(2, 8, 10, 12, 14)); kicks(17, A_KICK); snares(17, (4,))
    ghosts(17, (2, 7)); cell(17, 8, DESC2, 104); add(17, 12, KICK, 104)
    # A on floor tom + kick in unison
    for p in A_KICK + (14,):
        add(18, p, FLOOR_LO, 108)
        add(18, p, KICK, 108)
    snares(18, (4, 12), 116); ghosts(18, (7, 9)); pedal(18, (2, 6, 10), 60)
    # fragment, then a roll into the interlude
    for p in (0, 3, 6):
        add(19, p, FLOOR_LO, 112)
        add(19, p, KICK, 112)
    snares(19, (4,), 116)
    add(19, 8, SNARE, 104); add(19, 10, TOM_HI, 100); add(19, 11, TOM_HIMID, 100)
    kicks(19, (8, 12, 14), 108)
    roll(19, 12, 16, 56, 118)
    cym(20, 0, CRASH1, 120)                    # arrival, then sudden quiet


def section_c():                               # bars 20-27: percussion interlude
    set_feel(dyn=0.72, lean=5)
    for b in range(20, 28):                    # feet: fragment of A + backbeat
        if b != 20:
            add(b, 0, KICK, 98)
        add(b, 10, KICK, 92)
        if b >= 26:
            add(b, 3, KICK, 90); add(b, 6, KICK, 90)
        if b < 24 or b == 27:
            pedal(b, (4, 12), 68)
        else:                                  # tambourine on the hi-hat stand
            add(b, 4, TAMB, 80, limb="foot"); add(b, 12, TAMB, 80, limb="foot")

    def clave_a(b):
        for p in A_RHYTHM:
            add(b, p, CLAVES, 102 if p in (0, 12) else 88)

    clave_a(20)
    clave_a(21)
    for p in (7, 9, 14):
        add(21, p, WB_HI, 62)
    clave_a(22); cell(22, 8, (WB_HI, WB_HI, WB_LO, WB_HI, WB_LO, WB_LO), 86)
    clave_a(23); cell(23, 8, (WB_LO, WB_HI, WB_HI, WB_LO, WB_HI, WB_HI), 88)

    def conga_a(b, second_half=True):
        add(b, 0, CONGA_LO, 102); add(b, 3, CONGA_HI, 92); add(b, 6, CONGA_HI, 92)
        add(b, 2, CONGA_MUTE, 58); add(b, 7, CONGA_MUTE, 58)
        if second_half:
            add(b, 10, CONGA_MUTE, 86); add(b, 12, CONGA_HI, 102)
            add(b, 9, CONGA_MUTE, 58); add(b, 14, CONGA_MUTE, 58)

    conga_a(24)
    conga_a(25, False)
    cell(25, 8, (BONGO_HI, BONGO_HI, BONGO_LO, BONGO_HI, BONGO_LO, BONGO_LO), 92)
    set_feel(dyn=0.86, lean=-2)                # cowbell states A, congas answer, timbales build
    for p in A_RHYTHM:
        add(26, p, COWBELL, 104 if p in (0, 12) else 92)
    for p, n, v in ((2, CONGA_MUTE, 58), (4, CONGA_HI, 92), (7, CONGA_MUTE, 58),
                    (8, CONGA_LO, 98), (9, CONGA_MUTE, 58), (14, CONGA_MUTE, 58),
                    (15, CONGA_HI, 84)):
        add(26, p, n, v)
    for p in (0, 3, 6):
        add(27, p, COWBELL, 100)
    add(27, 2, CONGA_MUTE, 58); add(27, 4, CONGA_HI, 94); add(27, 7, CONGA_MUTE, 58)
    roll(27, 8, 14, 66, 100, note=TIMB_HI, step=1)
    roll(27, 14, 16, 104, 120, note=TIMB_HI, step=0.5)
    add(27, 8, TIMB_LO, 98); add(27, 12, TIMB_LO, 110)
    add(27, 12, KICK, 100); add(27, 14, KICK, 104)


def section_d():                               # bars 28-35: build
    set_feel(dyn=0.88, lean=-3, bb={8})
    cym(28, 0, CRASH1, 114)                    # half time, A augmented over two bars
    ride(28, skip=(0,)); snares(28, (8,), 112); kicks(28, (0, 6, 12), 104)
    ghosts(28, (3, 11)); pedal(28, (2, 6, 10, 14), 56)
    ride(29, bells=(12,)); snares(29, (8,), 112); kicks(29, (4, 8), 104)
    ghosts(29, (2, 7, 14)); pedal(29, (2, 6, 10, 14), 56)
    set_feel(dyn=0.92)                         # motif back at tempo under half-time snare
    ride(30, bells=(3, 6, 10), skip=(2,)); snares(30, (8,), 114); kicks(30)
    ghosts(30, (2, 7, 11, 15)); pedal(30, (2, 6, 10, 14), 56)
    ride(31, bells=(3, 6, 10), skip=(2, 12, 14)); snares(31, (8,), 114)
    kicks(31, A_KICK + (14,)); ghosts(31, (2, 7, 11)); pedal(31, (2, 6, 10), 56)
    add(31, 12, TOM_HI, 100); add(31, 14, TOM_HIMID, 100); add(31, 15, TOM_LOMID, 104)
    set_feel(dyn=0.96, bb={4, 12})             # full time again
    cym(32, 0, CRASH2, 112)
    hats(32, opens=(10,), skip=(0,)); kicks(32); snares(32); ghosts(32, (2, 7, 9, 15))
    hats(33, opens=(3, 6), skip=range(8, 16)); kicks(33, A_KICK); snares(33, (4,))
    ghosts(33, (2, 7)); cell(33, 8, DESC, 104); add(33, 12, KICK, 104)
    set_feel(dyn=1.0, lean=-5)                 # hemiola: x..x..x.. against the backbeat
    add(34, 0, CRASH2, 110)
    for k in range(8):
        apos = k * 3
        bar, pos = 34 + apos // 16, apos % 16
        add(bar, pos, FLOOR_LO, 92 + 4 * k)
        add(bar, pos, KICK, 94 + 4 * k)
    snares(34, (4, 12), 116)
    snares(35, (4,), 118)
    flam(35, 8, SNARE, 118)
    add(35, 8, KICK, 116)
    kicks(35, (10, 12, 14), 112)
    roll(35, 8.5, 16, 70, 122)


def section_e():                               # bars 36-43: climax
    set_feel(dyn=1.0, lean=-6, bb={4, 12})
    add(36, 0, CRASH1, 120); add(36, 0, CHINA, 110); add(36, 0, KICK, 120)
    hats(36, opens=(14,), skip=(0,), acc=100, mid=76, low=56)
    kicks(36, A_KICK, 112); snares(36, (4, 12), 120); ghosts(36, (7, 9, 15), 48)
    add(37, 0, CRASH2, 108)
    hats(37, skip=(0, 12), acc=100, mid=76, low=56)
    kicks(37, A_KICK + (14,), 112); snares(37, (4,), 120); flam(37, 12, SNARE, 122)
    ghosts(37, (2, 7, 9), 48)
    for p, n in zip((0, 3, 6), (CRASH1, CRASH2, CHINA)):   # A on the cymbals
        add(38, p, n, 118)
        add(38, p, KICK, 116)
    snares(38, (4,), 118); add(38, 10, SPLASH, 110); add(38, 10, KICK, 112)
    snares(38, (12,), 120); hats(38, skip=range(0, 12), acc=100, mid=76, low=56)
    ghosts(38, (2, 7, 9, 15), 48)
    kicks(39, (0, 4, 8, 12), 110); pedal(39, (2, 6, 10, 14), 64)   # B fill
    cell(39, 0, DESC, 108); cell(39, 8, DESC2, 112)
    add(40, 0, CRASH1, 116); add(40, 0, KICK, 116)      # A diminished (32nds) answers
    hats(40, skip=[0] + list(range(8, 16)), acc=100, mid=76, low=56)
    kicks(40, A_KICK); snares(40, (4,), 120); ghosts(40, (2, 7), 48)
    for d, n in zip(DIMIN, (SNARE, TOM_HI, TOM_HIMID, TOM_LO, SNARE)):
        add(40, 8 + d, n, 112 if d in (0, 6) else 100)
    add(40, 8, KICK, 112); add(40, 12, KICK, 108); add(40, 14, KICK, 106)
    for d, n in zip(DIMIN, (TOM_HI, TOM_HI, TOM_HIMID, TOM_LOMID, FLOOR_LO)):
        add(41, d, n, 108 if d in (0, 6) else 98)
    add(41, 0, KICK, 112); add(41, 4, KICK, 108); add(41, 8, KICK, 110)
    hats(41, opens=(14,), skip=range(0, 8), acc=100, mid=76, low=56)
    kicks(41, (10,)); snares(41, (12,), 120); ghosts(41, (9, 15), 48)
    kicks(42, (0, 4, 8, 12), 112); pedal(42, (2, 6, 10, 14), 64)   # the big fill
    cell(42, 0, SN_DESC, 110); cell(42, 8, LOW_TO_SN, 114)
    for p, n in zip((0, 3, 6), (CRASH1, CRASH2, CHINA)):   # A as full-stop hits
        add(43, p, n, 122)
        add(43, p, KICK, 120)
    add(43, 0, SNARE, 118)
    add(43, 10, SNARE, 122); add(43, 10, KICK, 118)
    add(43, 12, CRASH1, 124); add(43, 12, FLOOR_LO, 118); add(43, 12, KICK, 122)


def outro():                                   # bars 44-47 (+ final hit on bar 48)
    set_feel(dyn=0.8, lean=3, bb={4, 12})
    for b in (44, 45):
        pedal(b, (0, 4, 8, 12), 60)
        for p in A_RHYTHM:
            add(b, p, SIDE, 90 if p in (0, 12) else 78)
    ghosts(45, (7, 9, 14), 40)
    pedal(46, (0, 2, 4, 6, 8, 10, 12, 14), 56)
    kicks(46, A_KICK, 96); add(46, 4, SIDE, 92); add(46, 12, SIDE, 92)
    ghosts(46, (2, 7, 9), 40)
    add(46, 14, TOM_LO, 78); add(46, 15, FLOOR_LO, 88)
    set_feel(dyn=1.0, lean=0)
    for k, p in enumerate((0, 3, 6)):
        add(47, p, FLOOR_LO, 96 + 10 * k)
        add(47, p, KICK, 100 + 8 * k)
    add(47, 10, SNARE, 110); add(47, 10, KICK, 108)
    add(48, 0, CRASH1, 124); add(48, 0, FLOOR_LO, 116); add(48, 0, KICK, 124)


# ----------------------------------------------------------------------------- playability
def enforce_playability(evs, window=30):
    """At most two hand strikes and two foot strikes inside any `window` ticks."""
    evs = sorted(evs, key=lambda e: (e[0], -e[2], e[1]))
    kept = []
    for e in evs:
        t, note, v, limb = e
        if any(k[1] == note and abs(k[0] - t) <= 8 for k in kept):
            continue                                   # duplicate strike, keep the louder
        same = [k for k in kept if k[3] == limb and t - k[0] <= window]
        if len(same) >= 2:
            weakest = min(same, key=lambda k: k[2])
            if weakest[2] < v:
                kept.remove(weakest)
                kept.append(e)
        else:
            kept.append(e)
    return kept


def verify(evs, window=30):
    for limb in ("hand", "foot"):
        ts = sorted(e[0] for e in evs if e[3] == limb)
        for i in range(2, len(ts)):
            assert ts[i] - ts[i - 2] > window, "playability violated"


# ----------------------------------------------------------------------------- output
def write_midi(evs, path="solo.mid"):
    evs = sorted(evs, key=lambda e: (e[0], e[1]))
    final_tick = 48 * 16 * S16
    next_on = {}
    offs = [0] * len(evs)
    for i in range(len(evs) - 1, -1, -1):
        t, note, v, limb = evs[i]
        dur = 960 if note in LONG_NOTES else 60
        if t >= final_tick:
            dur = 4 * TPB * 2
        off = t + dur
        if note in next_on:
            off = min(off, next_on[note] - 1)
        offs[i] = max(off, t + 1)
        next_on[note] = t

    mid = MidiFile(type=1, ticks_per_beat=TPB)
    meta = MidiTrack()
    mid.tracks.append(meta)
    meta.append(MetaMessage("track_name", name="Drum Solo (tresillo)", time=0))
    meta.append(MetaMessage("set_tempo", tempo=bpm2tempo(BPM), time=0))
    meta.append(MetaMessage("time_signature", numerator=4, denominator=4,
                            clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    meta.append(MetaMessage("end_of_track", time=0))

    trk = MidiTrack()
    mid.tracks.append(trk)
    trk.append(MetaMessage("track_name", name="Drums", time=0))
    trk.append(Message("program_change", channel=CH, program=0, time=0))
    trk.append(Message("control_change", channel=CH, control=7, value=112, time=0))
    trk.append(Message("control_change", channel=CH, control=10, value=64, time=0))
    trk.append(Message("control_change", channel=CH, control=91, value=44, time=0))

    msgs = []
    for (t, note, v, limb), off in zip(evs, offs):
        msgs.append((t, 1, note, Message("note_on", channel=CH, note=note, velocity=v, time=0)))
        msgs.append((off, 0, note, Message("note_off", channel=CH, note=note, velocity=0, time=0)))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))
    prev = 0
    for t, _, _, m in msgs:
        trk.append(m.copy(time=t - prev))
        prev = t
    trk.append(MetaMessage("end_of_track", time=TPB))
    mid.save(path)
    return prev


def main():
    intro()
    section_a()
    section_b()
    section_c()
    section_d()
    section_e()
    outro()
    kept = enforce_playability(events)
    verify(kept)
    last = write_midi(kept)
    secs = last / TPB * 60.0 / BPM
    print("wrote solo.mid: %d strikes, %.1f s, %d BPM, channel 10" % (len(kept), secs, BPM))


if __name__ == "__main__":
    main()
