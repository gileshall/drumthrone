#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid, a two minute General MIDI drum solo for a
single drummer (two hands, two feet) on MIDI channel 10.

Nothing here is random: a two bar motif is stated, developed, dropped out and
brought back, and the density/dynamics are shaped into a long arc.  Placement
is deliberate -- a swung sixteenth grid, a per-section pocket (laying back or
pushing) and a small kick/snare displacement -- and quiet ghost notes answer
the accents.  The whole GM percussion set (35..81) is used, not just the kit.

Structure (60 bars of 4/4, ~120 bpm):
    1- 4  intro      : the motif, stated quietly, laid back
    5-12  groove     : motif with the full kit, swung, behind the beat
   13-20  develop    : more ghosts, more kick, building
   21-28  build      : sixteenth hats, density and level rising
   29-36  climax     : driving sixteenths, tom groove, big fill
   37-44  contrast   : space / rim clicks, then a percussion interlude
   45-52  return     : the motif again, full voice
   53-60  finale     : drive, fills, final hit
"""

import math
from collections import defaultdict

import mido

# ----------------------------------------------------------------------
TPB = 480                    # ticks per quarter note
CH = 9                       # MIDI channel 10 (zero based)
OUT = 'solo.mid'

# ---- General MIDI percussion names used by this solo -----------------
N = {
    'kick': 36, 'kick2': 35, 'snare': 38, 'rim': 37, 'clap': 39,
    'esnare': 40,
    'hh': 42, 'pedal': 44, 'ohh': 46,
    'ride': 51, 'bell': 53, 'ride2': 59,
    'crash': 49, 'crash2': 57, 'splash': 55, 'china': 52,
    'tom1': 50, 'tom2': 48, 'tom3': 47, 'tom4': 45, 'tom5': 43, 'tom6': 41,
    'cowbell': 56, 'claves': 75, 'tamb': 54, 'wbh': 76, 'wbl': 77,
    'conga_h': 63, 'conga_m': 62, 'conga_l': 64,
    'bongo_h': 60, 'bongo_l': 61,
    'tri': 81, 'agogo_h': 67, 'agogo_l': 68,
    'shaker': 70, 'cabasa': 69, 'vibra': 58,
}
FEET = {35, 36, 44}          # struck with a foot, everything else a hand

# ----------------------------------------------------------------------
# feel: swing grid, pocket, micro displacement
# ----------------------------------------------------------------------
SW = 1.0                     # 0 = straight, 1 = hard triplet swing
PK = 0.0                     # pocket in beats (+ = behind, - = ahead)
_SW_OFF = (0.0, 0.075, 0.115, 0.075)   # swing applied to the 16th grid
MICRO = {36: -0.004, 38: 0.005}        # kick a hair early, snare a hair late

EV = []                      # (beat, grid, note, velocity)


def swung(t):
    """Map a straight 16th-grid position onto the swung grid."""
    if SW <= 0.0:
        return t
    b = math.floor(t + 1e-9)
    i = int(round((t - b) * 4.0))
    if i >= 4:
        b += 1.0
        i = 0
    return b + i * 0.25 + _SW_OFF[i] * SW


def hit(grid, note, vel):
    EV.append((swung(grid) + PK + MICRO.get(note, 0.0), grid, note, vel))


def P(*groups):
    """One bar pattern: four four-character beat groups, '.' = rest."""
    s = ''.join(groups)
    assert len(s) == 16, repr(s)
    return s


def v(level):
    """Level 1..9 -> velocity (1 = ghost, 9 = accent)."""
    return max(1, min(127, 18 + 12 * level))


def bar(n, **layers):
    """Write one bar; layers are instrument=pattern pairs."""
    base = (n - 1) * 4.0
    for name, pat in layers.items():
        note = N[name]
        for i, ch in enumerate(pat):
            if ch != '.':
                hit(base + i * 0.25, note, v(int(ch)))


def fill(n, start, notes, levels, step=1):
    """A run of single strokes starting at 16th step `start`."""
    assert len(notes) == len(levels)
    base = (n - 1) * 4.0
    for k, (nm, lv) in enumerate(zip(notes, levels)):
        note = N[nm] if isinstance(nm, str) else nm
        hit(base + (start + k * step) * 0.25, note, v(lv))


def section(swing, pocket):
    global SW, PK
    SW, PK = swing, pocket


# ----------------------------------------------------------------------
# reusable cells (16 steps = one bar)
# ----------------------------------------------------------------------
RIDE8   = P("8.5.", "7.5.", "8.5.", "7.5.")      # swung eighths
RIDE8B  = P("8.5.", "7.5.", "8.5.", "7.55")      # ... with a 16th pickup
RIDE_CR = P("....", "5.7.", "5.8.", "5.7.")      # after a crash on beat 1
RIDE16  = P("8756", "8756", "8756", "8756")      # driving sixteenths
RIDE16C = P(".756", "8756", "8756", "8756")      # ... after a crash
HH16    = P("8654", "8654", "8654", "8654")      # sixteenth hats
HH16C   = P(".654", "8654", "8654", "8654")

SN_A = P("....", "9..1", "..1.", "9..1")         # backbeat + ghosts
SN_B = P("....", "9..1", "....", "9.11")
SN_C = P("....", "9.11", "1.1.", "9..1")
SN_D = P("....", "9..1", "..1.", "9.11")
SN_F = P("....", "9..1", "..1.", "....")         # no backbeat on 4 (fill)

K_A = P("9...", "...5", "..5.", "....")
K_B = P("9...", "...5", "5...", "..5.")
K_C = P("9..5", "...5", "..5.", "..5.")
K_D = P("9...", "..9.", "....", "..5.")

PED  = P("....", "8...", "....", "8...")         # hi-hat foot on 2 and 4
PED2 = P("....", "..8.", "....", "..8.")

# ======================================================================
# 1-4  intro: the motif, quietly, laid back
# ======================================================================
section(0.55, 0.016)
bar(1, snare=P("....", "7..1", "....", "7.1."),
       kick=P("6...", "....", "..5.", "...."),
       pedal=P("....", "..5.", "....", "..5."))
bar(2, snare=P("....", "7..1", "..1.", "7..1"),
       kick=P("6...", "...5", "....", "..5."),
       pedal=P("....", "..5.", "....", "..5."))
bar(3, hh=P("5.4.", "5.4.", "5.4.", "5.4."),
       snare=P("....", "7..1", "....", "7.1."),
       kick=P("6...", "..5.", "....", "..5."))
bar(4, snare=P("....", "7..1", "....", "...."),
       kick=P("6...", "..5.", "....", "...."),
       pedal=P("....", "....", "....", "..5."))
fill(4, 12, ['tom2', 'tom3', 'tom4', 'tom5'], [4, 5, 6, 7])

# ======================================================================
# 5-12  groove: the motif in full voice, swung, sitting behind the beat
# ======================================================================
section(1.0, 0.012)
bar(5, crash=P("9...", "....", "....", "...."), ride=RIDE_CR,
       snare=SN_A, kick=K_A, pedal=PED)
bar(6, ride=RIDE8, snare=SN_B, kick=K_B, pedal=PED)
bar(7, ride=RIDE8, snare=SN_A, kick=K_A, pedal=PED)
bar(8, ride=P("8.5.", "7.5.", "8.5.", "...."), snare=SN_F, kick=K_A, pedal=PED)
fill(8, 12, ['tom1', 'tom2', 'tom3', 'tom4'], [5, 6, 7, 8])
bar(9, crash=P("9...", "....", "....", "...."), ride=RIDE_CR,
       snare=SN_C, kick=K_C, pedal=PED)
bar(10, ride=RIDE8B, snare=SN_D, kick=K_B, pedal=PED)
bar(11, crash=P("9...", "....", "....", "...."),
       ride=P("....", "5.7.", "5.8.", "7.5."), snare=SN_D, kick=K_A, pedal=PED)
bar(12, ride=P("8.5.", "7.5.", "8.5.", "...."), snare=SN_F, kick=K_A, pedal=PED)
fill(12, 12, ['tom2', 'tom3', 'tom4', 'tom5'], [6, 7, 8, 9])

# ======================================================================
# 13-20  development: more ghosts, more kick, riding bell, open hat
# ======================================================================
section(1.0, 0.008)
bar(13, crash=P("9...", "....", "....", "...."), ride=RIDE_CR,
       snare=SN_A, kick=K_C, pedal=PED)
bar(14, ride=P("8.5.", "7.5.", "....", "5.7."),
       bell=P("....", "....", "8...", "...."),
       snare=SN_D, kick=K_B, pedal=PED)
bar(15, ride=RIDE8, snare=SN_C, kick=K_A, pedal=PED)
bar(16, ride=RIDE8B, snare=SN_B, kick=K_D, pedal=PED)
bar(17, crash=P("9...", "....", "....", "...."), ride=RIDE_CR,
       snare=SN_D, kick=K_C, pedal=PED)
bar(18, ride=P("8.5.", "7...", "8.5.", "7.5."),
       ohh=P("....", "..7.", "....", "...."),
       snare=SN_A, kick=K_B, pedal=P("....", "8...", "8...", "8..."))
bar(19, ride=P("8.5.", "7.5.", "8.5.", "...."), snare=SN_F, kick=K_C, pedal=PED)
fill(19, 12, ['tom1', 'tom2', 'tom3', 'tom4'], [6, 7, 8, 9])
bar(20, ride=P("8.5.", "7.5.", "....", "...."),
       snare=SN_F, kick=K_A, pedal=PED)
fill(20, 8, ['tom2', 'tom3', 'tom4', 'tom5', 'tom4', 'tom3', 'tom2', 'tom1'],
     [5, 6, 7, 7, 8, 8, 7, 9])

# ======================================================================
# 21-28  build: sixteenth hats, density and level rising
# ======================================================================
section(0.85, 0.004)
bar(21, crash=P("9...", "....", "....", "...."), ride=RIDE_CR,
       snare=SN_A, kick=K_C, pedal=PED)
bar(22, ride=RIDE8B, snare=SN_D, kick=K_B, pedal=PED)
bar(23, ride=RIDE8, snare=SN_C, kick=K_C, pedal=PED)
bar(24, ride=P("8.5.", "7.5.", "8.5.", "...."), snare=SN_F, kick=K_A, pedal=PED)
fill(24, 12, ['tom1', 'tom2', 'tom3', 'tom4'], [6, 7, 8, 9])
bar(25, crash=P("9...", "....", "....", "...."), hh=HH16C,
       snare=SN_A, kick=K_C, pedal=PED)
bar(26, hh=HH16, snare=SN_D, kick=K_B, pedal=PED)
bar(27, hh=HH16, snare=SN_C, kick=K_C, pedal=PED)
bar(28, hh=P("8654", "8654", "8654", "...."), snare=SN_F, kick=K_A, pedal=PED)
fill(28, 12, ['tom1', 'tom2', 'tom3', 'tom4'], [7, 8, 8, 9])

# ======================================================================
# 29-36  climax: driving sixteenths, tom groove, big fill
# ======================================================================
section(0.5, -0.010)
bar(29, crash=P("9...", "....", "....", "...."), ride=RIDE16C,
       snare=SN_A, kick=K_C, pedal=PED)
bar(30, ride=RIDE16, snare=SN_D, kick=K_B, pedal=PED)
bar(31, crash=P("9...", "....", "....", "...."), ride=RIDE16C,
       snare=SN_C, kick=K_C, pedal=PED)
bar(32, ride=RIDE16, snare=SN_D, kick=K_B, pedal=PED)
bar(33, crash=P("9...", "....", "....", "...."),
       tom1=P("8.6.", "8.6.", "8.6.", "8.6."),
       tom2=P("..7.", "..7.", "..7.", "..7."),
       kick=P("9...", "....", "9...", "...."), pedal=PED)
bar(34, tom3=P("8.6.", "8.6.", "8.6.", "8.6."),
       tom4=P("..7.", "..7.", "..7.", "..7."),
       kick=P("9...", "..5.", "9...", "..5."), pedal=PED)
fill(35, 0, ['tom1'] * 4 + ['tom2'] * 4 + ['tom3'] * 4 + ['tom4'] * 4,
     [8, 6, 6, 6] * 4)
fill(36, 0, ['snare'] * 8, [4, 4, 5, 5, 6, 6, 7, 7])
fill(36, 8, ['tom1', 'tom2', 'tom3', 'tom4', 'tom5', 'tom6', 'tom5', 'tom4'],
     [7, 7, 8, 8, 9, 9, 9, 9])

# ======================================================================
# 37-44  contrast: space and rim clicks, then a percussion interlude
# ======================================================================
section(1.0, 0.030)
bar(37, crash=P("9...", "....", "....", "...."),
       kick=P("8...", "....", "....", "...."),
       rim=P("....", "....", "6...", "...."),
       pedal=P("....", "....", "....", "..6."))
bar(38, rim=P("....", "6...", "....", "6..."),
       kick=P("8...", "....", "....", "..5."),
       pedal=P("....", "....", "..6.", "...."))

section(1.0, 0.024)
bar(39, bell=P("8...", "....", "6...", "...."),
       snare=P("....", "....", "....", "5..."),
       kick=P("8...", "....", "....", "...."),
       pedal=P("....", "..6.", "....", "..6."))
bar(40, bell=P("8...", "....", "6...", "...."),
       snare=P("....", "5...", "....", "5.1."),
       kick=P("8...", "....", "..5.", "...."),
       pedal=P("....", "..6.", "....", "...."))

section(0.45, 0.022)
bar(41, cowbell=P("8...", "6...", "8...", "6..."),
       conga_h=P("....", "..7.", "....", "..7."),
       conga_l=P("..6.", "....", "..6.", "...."),
       kick=P("9...", "....", "9...", "...."),
       pedal=P("....", "7...", "....", "7..."))
bar(42, cowbell=P("8...", "6...", "8...", "6..."),
       conga_h=P("..6.", "....", "..6.", "...."),
       conga_l=P("....", "..7.", "....", "..7."),
       kick=P("9...", "....", "9...", "..5."),
       pedal=P("....", "7...", "....", "7..."))
bar(43, claves=P("9...", "..8.", "....", "9..."),
       conga_h=P("..6.", "....", "..6.", "...."),
       conga_l=P("....", "....", "....", "..7."),
       bongo_h=P("....", "....", "7...", "...."),
       kick=P("9...", "....", "9...", "...."),
       pedal=P("....", "7...", "....", "7..."))
bar(44, claves=P("....", "9...", "9...", "...."),
       conga_h=P("6...", "..6.", "....", "...."),
       conga_l=P("..5.", "....", "....", "...."),
       kick=P("9...", "....", "....", "...."))
fill(44, 8, ['conga_h', 'conga_m', 'conga_l', 'conga_h',
             'conga_m', 'conga_l', 'conga_h', 'conga_m'],
     [6, 6, 7, 7, 8, 8, 9, 9])

# ======================================================================
# 45-52  the motif returns, full voice
# ======================================================================
section(1.0, 0.008)
bar(45, crash=P("9...", "....", "....", "...."), ride=RIDE_CR,
       snare=SN_A, kick=K_C, pedal=PED)
bar(46, ride=P("8.5.", "7.5.", "....", "5.7."),
       bell=P("....", "....", "8...", "...."),
       snare=SN_D, kick=K_B, pedal=PED)
bar(47, ride=RIDE8, snare=SN_C, kick=K_C, pedal=PED)
bar(48, ride=P("8.5.", "7.5.", "8.5.", "...."), snare=SN_F, kick=K_A, pedal=PED)
fill(48, 12, ['tom1', 'tom2', 'tom3', 'tom4'], [6, 7, 8, 9])
bar(49, crash=P("9...", "....", "....", "...."), ride=RIDE_CR,
       snare=SN_D, kick=K_B, pedal=PED)
bar(50, ride=RIDE16, snare=SN_A, kick=K_C, pedal=PED)
bar(51, ride=RIDE8B, snare=SN_C, kick=K_B, pedal=PED)
bar(52, ride=P("8.5.", "7.5.", "8.5.", "...."), snare=SN_F, kick=K_A, pedal=PED)
fill(52, 12, ['tom2', 'tom3', 'tom4', 'tom5'], [7, 8, 9, 9])

# ======================================================================
# 53-60  finale: drive, fills, final hit
# ======================================================================
section(0.5, -0.006)
bar(53, crash=P("9...", "....", "....", "...."), ride=RIDE16C,
       snare=SN_A, kick=K_C, pedal=PED)
bar(54, ride=RIDE16, snare=SN_D, kick=K_B, pedal=PED)
bar(55, crash=P("9...", "....", "....", "...."),
       tom1=P("8.6.", "8.6.", "8.6.", "8.6."),
       tom2=P("..7.", "..7.", "..7.", "..7."),
       kick=P("9...", "....", "9...", "...."), pedal=PED)
bar(56, tom3=P("8.6.", "8.6.", "8.6.", "8.6."),
       tom4=P("..7.", "..7.", "..7.", "..7."),
       kick=P("9...", "..5.", "9...", "..5."), pedal=PED)
fill(57, 0, ['tom1'] * 4 + ['tom3'] * 4 + ['tom5'] * 4 + ['tom6'] * 4,
     [9, 6, 6, 6] * 4)
fill(58, 0, ['tom5', 'tom4', 'tom3', 'tom2', 'tom3', 'tom4', 'tom5', 'tom6'] * 2,
     [7, 7, 8, 8, 8, 8, 9, 9] * 2)
fill(59, 0, ['snare'] * 16,
     [5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9])
bar(60, crash=P("9...", "....", "....", "...."),
       kick=P("9...", "....", "....", "...."),
       snare=P("....", "....", "8...", "...."),
       crash2=P("....", "....", "....", "9..."),
       kick2=P("....", "....", "....", "9..."))

# ----------------------------------------------------------------------
# render
# ----------------------------------------------------------------------
DUR = {49: 1.6, 57: 1.6, 52: 1.6, 55: 1.0,
       51: 0.42, 53: 0.42, 59: 0.42, 46: 0.5, 42: 0.08, 44: 0.08}
DUR_DEF = 0.10

TEMPO = [(1, 116), (5, 120), (37, 112), (45, 124), (59, 122), (60, 104)]


def enforce(ev):
    """Keep the part playable: at most two hands and two feet at a time."""
    groups = defaultdict(list)
    for t, g, n, vel in ev:
        groups[round(g * 4.0)].append((t, n, vel))
    out = []
    for key in sorted(groups):
        hands = [x for x in groups[key] if x[1] not in FEET]
        feet = [x for x in groups[key] if x[1] in FEET]
        if len(hands) > 2:
            hands.sort(key=lambda x: -x[2])
            del hands[2:]
        if len(feet) > 2:
            feet.sort(key=lambda x: -x[2])
            del feet[2:]
        seen = set()
        for t, n, vel in sorted(hands + feet):
            if n in seen:
                continue
            seen.add(n)
            out.append((t, n, vel))
    return out


def write(path=OUT):
    hits = sorted((int(round(t * TPB)), n, vel) for t, n, vel in enforce(EV))

    by_note = defaultdict(list)
    for tick, n, vel in hits:
        by_note[n].append(tick)

    msgs = []
    for tick, n, vel in hits:
        msgs.append((tick, 2,
                     mido.Message('note_on', channel=CH, note=n, velocity=vel)))
    for n, ticks in by_note.items():
        d = int(DUR.get(n, DUR_DEF) * TPB)
        for i, tick in enumerate(ticks):
            end = tick + d
            if i + 1 < len(ticks):
                end = min(end, ticks[i + 1] - 1)
            if end <= tick:
                end = tick + 1
            msgs.append((end, 0,
                         mido.Message('note_off', channel=CH, note=n,
                                      velocity=0)))
    for bn, bpm in TEMPO:
        msgs.append((int((bn - 1) * 4 * TPB), 1,
                     mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm))))
    msgs.sort(key=lambda x: (x[0], x[1]))

    track = mido.MidiTrack()
    track.append(mido.MetaMessage('track_name', name='Drum Solo'))
    track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
    track.append(mido.Message('program_change', channel=CH, program=0))

    last = 0
    for tick, _order, msg in msgs:
        msg.time = tick - last
        last = tick
        track.append(msg)

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    mid.tracks.append(track)
    mid.save(path)
    return mid


if __name__ == '__main__':
    write(OUT)
    print('wrote', OUT)
