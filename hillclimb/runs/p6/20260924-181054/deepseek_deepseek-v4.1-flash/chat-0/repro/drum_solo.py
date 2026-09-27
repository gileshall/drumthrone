#!/usr/bin/env python3
"""
drum_solo.py

Writes "solo.mid": a two-minute General MIDI drum solo for channel 10.

The solo is composed as a drummer would play it: a theme is stated, varied,
displaced, brought back, and pushed to a climax, with fills, rolls and dynamic
shaping inside every phrase.  Nothing is quantized to a grid - each stroke is
placed and weighted by hand.  Every stroke is finally assigned to one of a
drummer's four limbs, and any physically impossible collision is removed, so
the result stays playable by one person.

Running this script writes solo.mid in the current directory.  The output is
fully deterministic (fixed random seed).
"""

import math
import random

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

PPQ = 960            # ticks per quarter note
CH = 9               # General MIDI channel 10 (zero based)
SEED = 424242

rng = random.Random(SEED)

# --- how close together one limb may strike (seconds) ------------------------
MIN_HAND = 0.075     # one hand: ~13 strokes / second is the fast end
MIN_FOOT = 0.085

# --- tempo map: a slow burn from 92 to 131 and a pull back at the end --------
TEMPO_POINTS = [
    (0, 92), (8, 96), (16, 100), (24, 104), (32, 107), (48, 110),
    (64, 113), (80, 117), (96, 121), (112, 125), (128, 129),
    (160, 131), (184, 131), (200, 128), (216, 124), (232, 117), (240, 110),
]

HAND_RH = {42, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 59}
HAND_LH = {37, 38, 39, 40, 41, 43, 45, 47}
FEET_KICK = {35, 36}
FEET_PEDAL = {44}


def bpm_at(beat):
    """Tempo (BPM) at a (possibly fractional) beat position."""
    pts = TEMPO_POINTS
    if beat <= pts[0][0]:
        return float(pts[0][1])
    for (b0, v0), (b1, v1) in zip(pts, pts[1:]):
        if beat <= b1:
            f = (beat - b0) / float(b1 - b0)
            return v0 + (v1 - v0) * f
    return float(pts[-1][1])


def sec_at(beat):
    """Seconds elapsed at a beat position, matching the tempo events written."""
    t = 0.0
    n = int(math.floor(beat))
    if n < 0:
        return 0.0
    for k in range(n):
        t += 60.0 / bpm_at(k)
    t += (beat - n) * 60.0 / bpm_at(n)
    return t


# --- the kit ----------------------------------------------------------------
# kind -> (note, velocity, duration in beats, humanising class)
KIT = {
    'K': (36, 106, 0.25, 'kick'),    # bass drum, accent
    'k': (36,  84, 0.25, 'kick'),    # bass drum, soft
    'S': (38, 112, 0.20, 'accent'),  # snare, accent
    's': (38,  90, 0.20, 'mid'),
    'g': (38,  30, 0.15, 'ghost'),   # ghost note
    'X': (37,  88, 0.15, 'mid'),     # side stick
    'T': (50, 106, 0.22, 'tom'),     # high tom
    't': (50,  84, 0.22, 'tom'),
    'M': (47, 108, 0.24, 'tom'),     # low-mid tom
    'm': (47,  84, 0.24, 'tom'),
    'L': (43, 106, 0.26, 'tom'),     # high floor tom
    'l': (43,  84, 0.26, 'tom'),
    'F': (41, 110, 0.30, 'tom'),     # low floor tom
    'f': (41,  86, 0.30, 'tom'),
    'H': (42,  92, 0.12, 'time'),    # closed hi-hat, accent
    'h': (42,  62, 0.12, 'time'),
    'O': (46,  96, 0.80, 'time'),    # open hi-hat
    'o': (46,  74, 0.80, 'time'),
    'R': (51,  96, 0.40, 'time'),    # ride
    'r': (51,  70, 0.40, 'time'),
    'B': (53, 106, 0.40, 'time'),    # ride bell
    'C': (49, 118, 2.00, 'crash'),   # crash 1
    'D': (57, 110, 2.00, 'crash'),   # crash 2
    'Z': (52, 116, 2.00, 'crash'),   # chinese cymbal (colour)
    'W': (55, 100, 1.20, 'crash'),   # splash (colour)
    'P': (44,  84, 0.15, 'foot'),    # pedal hi-hat
}

EVENTS = []          # [beat, note, velocity, duration_beats, class]


def hit(beat, kind, dyn=1.0):
    note, vel, dur, cls = KIT[kind]
    EVENTS.append([beat, note, vel * dyn, dur, cls])


def play(bar, items, dyn=1.0):
    """items: list of (16th-step, kind[, extra dynamic multiplier])."""
    for it in items:
        step = it[0]
        kind = it[1]
        m = it[2] if len(it) > 2 else 1.0
        hit(bar * 4.0 + step * 0.25, kind, dyn * m)


def run(bar, s0, s1, drums, div=4, d0=0.8, d1=1.0, curve=1.0):
    """
    A hand-to-hand run of singles between 16th steps s0 and s1.
    div   : strokes per beat (4 = 16ths, 8 = 32nds)
    d0/d1 : velocity envelope
    curve : <1 lets the run rush slightly toward its end
    """
    t0 = bar * 4.0 + s0 * 0.25
    t1 = bar * 4.0 + s1 * 0.25
    span = t1 - t0
    if span <= 0:
        return
    n = int(round(span * div))
    if n < 1:
        return
    for i in range(n):
        f = (i / float(n)) ** curve
        v = d0 + (d1 - d0) * (i / float(max(1, n - 1)))
        hit(t0 + span * f, drums[i % len(drums)], v)


def pedal(bar, beats=(1.0, 3.0), dyn=1.0):
    """Left-foot hi-hat on the backbeats."""
    for b in beats:
        hit(bar * 4.0 + b, 'P', dyn)


def eighths(a='H', b='h'):
    return [(i, a if i % 4 == 0 else b) for i in range(0, 16, 2)]


def sixteenths(a='H', b='h'):
    return [(i, a if i % 4 == 0 else b) for i in range(0, 16)]


def vary(cell, subst=None, remove=(), add=(), shift=0):
    subst = subst or {}
    out = []
    for s, k in cell:
        if s in remove:
            continue
        out.append(((s + shift) % 16, subst.get(k, k)))
    out.extend(add)
    return sorted(out, key=lambda x: x[0])


# --- motifs -----------------------------------------------------------------
# The hook: kick on 1 and 3, snare answers on 2 and on the "a" of 3,
# ghost notes filling the corners.
T_A = [(0, 'K'), (2, 'g'), (4, 'S'), (6, 'g'), (8, 'K'),
       (10, 'g'), (11, 'S'), (13, 'g'), (14, 'k')]

# Denser reading of the same idea.
T_A2 = [(0, 'K'), (2, 'g'), (4, 'S'), (6, 'g'), (7, 'k'), (8, 'K'),
        (10, 'g'), (11, 'S'), (13, 'g'), (14, 'k'), (15, 'g')]

# The answering phrase: toms take over the melodic role.
T_B = [(0, 'K'), (2, 'M'), (4, 'S'), (6, 'g'), (7, 'k'),
       (8, 'F'), (10, 'M'), (12, 'S'), (13, 'g'), (14, 'k')]


def compose():
    EVENTS.clear()

    # =====================================================================
    # 1. Statement (bars 0-7): the hook, plainly, then growing
    # =====================================================================
    play(0, [(0, 'C', 1.05), (0, 'K', 1.05), (2, 'h'), (4, 'S'), (6, 'h'),
             (8, 'K'), (10, 'h'), (12, 'S'), (14, 'h')])
    play(1, T_A + eighths('H', 'h'), 0.95)
    pedal(1)
    play(2, vary(T_A, add=[(15, 'g')]) + eighths('H', 'h'), 0.98)
    pedal(2)
    play(3, vary(T_A, subst={'S': 'M'}, add=[(15, 's')]) + eighths('H', 'h'), 1.0)
    pedal(3)
    play(4, vary(T_A, add=[(7, 'g')]) + eighths('R', 'r'), 1.0)
    play(5, T_A2 + eighths('R', 'r'), 1.02)
    pedal(5)
    play(6, [x for x in T_A if x[0] < 8] + eighths('R', 'r'))
    run(6, 10, 16, ['S', 'T', 'M', 'F'], div=4, d0=0.55, d1=0.92)
    play(7, [(0, 'K'), (0, 'F')])
    run(7, 2, 16, ['S', 'T', 'M', 'F', 'M', 'T'], div=4, d0=0.60, d1=1.0, curve=0.95)

    # =====================================================================
    # 2. Development (bars 8-15): the hook re-voiced, an answer phrase,
    #    a half-time breath, then a fill that lifts into the build
    # =====================================================================
    play(8, [(0, 'C'), (0, 'K', 1.05)] + T_A + eighths('R', 'r'), 1.05)
    pedal(8)
    play(9, T_A2 + eighths('R', 'r'), 1.02)
    pedal(9)
    play(10, vary(T_A, subst={'S': 'T'}, add=[(14, 'O')]) + eighths('R', 'r'), 1.0)
    play(11, [x for x in T_A if x[0] < 4] + eighths('R', 'r'))
    run(11, 4, 16, ['S', 'T', 'M', 'F'], div=8, d0=0.50, d1=0.95, curve=0.94)
    pedal(11)
    play(12, T_B + eighths('H', 'h'), 1.0)
    pedal(12)
    play(13, vary(T_B, subst={'M': 'T'}, add=[(15, 'S')]) + eighths('H', 'h'), 1.0)
    play(14, [(0, 'K'), (0, 'O'), (4, 'g'), (8, 'S'), (8, 'W'),
              (11, 'g'), (12, 'o'), (14, 'g')], 0.95)
    play(15, [(0, 'K')])
    run(15, 1, 16, ['S', 'T', 'M', 'F', 'L', 'F'], div=8, d0=0.55, d1=1.0, curve=0.90)

    # =====================================================================
    # 3. Build (bars 16-23): density rises, then a hole before the peak
    # =====================================================================
    play(16, [(0, 'C', 1.10), (0, 'K', 1.10)] + T_A2 + eighths('B', 'R'), 1.08)
    play(17, vary(T_A2, remove={14}, add=[(13, 'k'), (15, 'k')])
         + eighths('B', 'R'), 1.05)
    pedal(17)
    play(18, sixteenths('H', 'h') + [(0, 'K'), (3, 'g'), (4, 'S'), (7, 'g'),
                                     (8, 'K'), (11, 'g'), (12, 'S'), (15, 'g')], 0.95)
    pedal(18)
    play(19, [(0, 'K'), (2, 'S'), (3, 'g'), (4, 'g'), (5, 'S'), (6, 'g'), (7, 'K'),
              (8, 'K'), (10, 'S'), (11, 'g'), (12, 'S'), (13, 'g'), (14, 'K'),
              (15, 'S')] + eighths('R', 'r'), 1.05)
    play(20, T_A + eighths('R', 'r'), 1.05)
    pedal(20)
    play(21, [x for x in T_A if x[0] < 8] + eighths('R', 'r')[:4], 1.0)
    run(21, 8, 16, ['S', 'T', 'M', 'F'], div=4, d0=0.70, d1=0.95, curve=0.95)
    run(22, 0, 16, ['S', 'T', 'M', 'F'], div=4, d0=0.75, d1=1.05, curve=0.97)
    # the hole: one soft kick and a whisper into the crash
    play(23, [(0, 'k'), (12, 'g'), (13, 'g'), (14, 'g'), (15, 'S', 0.85)])

    # =====================================================================
    # 4. Peak 1 (bars 24-31): full kit, then a roll that swells
    # =====================================================================
    play(24, [(0, 'C', 1.12), (0, 'K', 1.12), (0, 'F')] + T_A + eighths('B', 'R'), 1.12)
    play(25, T_A2 + eighths('B', 'R'), 1.10)
    pedal(25)
    play(26, [(0, 'K'), (2, 'K'), (3, 'g'), (4, 'S'), (6, 'g'), (7, 'K'), (8, 'K'),
              (10, 'g'), (11, 'S'), (12, 'g'), (13, 'K'), (14, 'K'),
              (15, 'g')] + eighths('R', 'B'), 1.10)
    play(27, [(0, 'K'), (2, 'T'), (3, 'T'), (4, 'S'), (6, 'M'), (7, 'M'), (8, 'K'),
              (10, 'F'), (11, 'F'), (12, 'S'), (14, 'L'), (15, 'L')]
         + eighths('R', 'r'), 1.08)
    play(28, T_A2 + eighths('R', 'r'), 1.05)
    pedal(28)
    run(29, 0, 16, ['S', 'S'], div=4, d0=0.55, d1=0.80, curve=0.97)
    run(30, 0, 16, ['S', 'S'], div=8, d0=0.75, d1=1.00, curve=0.94)
    play(31, [(0, 'K')])
    run(31, 1, 16, ['S', 'S'], div=8, d0=1.00, d1=1.25, curve=0.90)

    # =====================================================================
    # 5. Hands (bars 32-39): singles and doubles travelling the kit
    # =====================================================================
    play(32, [(0, 'C', 1.15), (0, 'K', 1.15)])
    run(32, 2, 16, ['S', 'T', 'M', 'F'], div=4, d0=0.85, d1=1.05, curve=0.97)
    play(33, [(0, 'K'), (0, 'F')])
    run(33, 1, 16, ['S', 'S', 'T', 'T', 'M', 'M', 'F', 'F'],
        div=4, d0=0.80, d1=1.00, curve=0.97)
    play(34, [(0, 'K')])
    run(34, 1, 16, ['F', 'M', 'T', 'S'], div=4, d0=0.90, d1=1.08, curve=0.97)
    run(35, 0, 8, ['S', 'T', 'M', 'F'], div=8, d0=0.90, d1=1.08, curve=0.95)
    play(35, [(8, 'C'), (8, 'K', 1.10)])
    run(35, 9, 16, ['S', 'T', 'M', 'F'], div=4, d0=0.90, d1=1.05, curve=0.95)
    play(36, [(0, 'K'), (0, 'F')])
    run(36, 1, 16, ['S', 'S'], div=8, d0=0.50, d1=0.78, curve=0.90)
    run(37, 0, 12, ['S', 'S'], div=8, d0=0.78, d1=1.05, curve=0.90)
    play(37, [(12, 'C'), (12, 'K', 1.15)])
    run(37, 13, 16, ['S', 'T'], div=8, d0=0.90, d1=1.10, curve=0.95)
    play(38, T_A2 + eighths('B', 'R'), 1.12)
    pedal(38)
    play(39, vary(T_A2, add=[(15, 'F')]) + eighths('B', 'R'), 1.12)

    # =====================================================================
    # 6. Climax (bars 40-47)
    # =====================================================================
    play(40, [(0, 'C', 1.15), (0, 'K', 1.15), (0, 'F')] + T_A + eighths('B', 'R'), 1.15)
    play(41, T_A2 + eighths('B', 'R'), 1.12)
    pedal(41)
    play(42, [(0, 'K'), (2, 'K'), (4, 'S'), (6, 'K'), (7, 'K'), (8, 'S'),
              (10, 'K'), (11, 'g'), (12, 'S'), (13, 'K'), (14, 'K'),
              (15, 'g')] + eighths('B', 'R'), 1.12)
    play(43, [(0, 'Z', 1.10), (0, 'S', 1.10), (0, 'K', 1.10), (2, 'g'), (4, 'K'),
              (6, 'g'), (8, 'S'), (8, 'K'), (10, 'g'), (12, 'K'), (13, 'g'),
              (14, 'F'), (15, 'K')], 1.12)
    run(44, 0, 16, ['S', 'T', 'M', 'F'], div=4, d0=1.00, d1=1.15, curve=0.95)
    run(45, 0, 8, ['S', 'T', 'M', 'F'], div=8, d0=0.95, d1=1.10, curve=0.93)
    play(45, [(8, 'C', 1.15), (8, 'K', 1.15)])
    run(45, 9, 16, ['S', 'T', 'M', 'F', 'L'], div=4, d0=0.95, d1=1.10, curve=0.95)
    play(46, [(0, 'C', 1.10), (0, 'K', 1.10)])
    run(46, 2, 14, ['T', 'M', 'F', 'L'], div=4, d0=0.95, d1=1.10, curve=0.95)
    play(46, [(14, 'K'), (15, 'S', 1.05)])
    run(47, 0, 16, ['S', 'S'], div=8, d0=0.85, d1=1.20, curve=0.90)

    # =====================================================================
    # 7. The hook comes back (bars 48-55)
    # =====================================================================
    play(48, [(0, 'C', 1.20), (0, 'K', 1.20), (0, 'F')] + T_A + eighths('B', 'R'), 1.18)
    play(49, T_A2 + eighths('B', 'R'), 1.15)
    pedal(49)
    play(50, vary(T_A, subst={'S': 'M'}, add=[(15, 'g')]) + eighths('B', 'R'), 1.12)
    play(51, T_B + eighths('B', 'R'), 1.12)
    pedal(51)
    play(52, [(0, 'K'), (0, 'O'), (4, 'g'), (8, 'S'), (10, 'g'),
              (12, 'o'), (14, 'g')], 0.90)
    run(53, 0, 16, ['S', 'T', 'M', 'F'], div=4, d0=0.78, d1=1.00, curve=0.95)
    play(54, [(0, 'C', 1.15), (0, 'K', 1.15), (0, 'F')] + T_A2 + eighths('R', 'r'), 1.15)
    play(55, [(0, 'K'), (2, 'K'), (4, 'S'), (6, 'K'), (8, 'S'), (10, 'K'),
              (12, 'S'), (13, 'K'), (14, 'K'), (15, 'S')] + eighths('B', 'R'), 1.15)

    # =====================================================================
    # 8. Finale (bars 56-59): everything accelerates into one landing
    # =====================================================================
    run(56, 0, 16, ['S', 'T', 'M', 'F'], div=4, d0=0.90, d1=1.10, curve=0.95)
    run(57, 0, 8, ['S', 'S', 'T', 'T', 'M', 'M', 'F', 'F'],
        div=4, d0=0.90, d1=1.05, curve=0.96)
    run(57, 8, 16, ['S', 'T', 'M', 'F'], div=8, d0=0.95, d1=1.12, curve=0.93)
    run(58, 0, 16, ['S', 'T', 'M', 'F', 'L', 'F', 'M', 'T'],
        div=8, d0=1.00, d1=1.15, curve=0.90)
    run(59, 0, 15.5, ['S', 'S'], div=8, d0=1.00, d1=1.30, curve=0.88)

    # the landing: both hands and the foot together, nothing after it
    hit(240.0, 'C', 1.30)
    hit(240.0, 'F', 1.20)
    hit(240.0, 'K', 1.30)


# --- performance shaping -----------------------------------------------------
def humanize():
    """Push and pull the time, and shape every stroke's weight."""
    for e in EVENTS:
        beat, note, vel, dur, cls = e

        if cls == 'ghost':
            sig = 0.014
        elif cls == 'time':
            sig = 0.007
        elif cls == 'kick':
            sig = 0.007
        elif cls == 'foot':
            sig = 0.008
        elif cls == 'crash':
            sig = 0.005
        else:
            sig = 0.009

        off = rng.gauss(0.0, sig)

        pos = beat % 4.0
        if note in (38, 40) and (abs(pos - 1.0) < 0.08 or abs(pos - 3.0) < 0.08):
            off += 0.013                      # the backbeat sits a hair late
        if note in (35, 36) and pos < 0.08:
            off -= 0.006                      # the downbeat kick pushes
        off += 0.006 * math.sin(beat * 0.15)  # the pulse surges and settles

        nb = beat + off
        if nb < 0.0:
            nb = 0.0
        e[0] = nb

        v = vel * (1.0 + rng.gauss(0.0, 0.05))
        if cls == 'ghost':
            v += rng.gauss(0.0, 2.5)
        e[2] = max(1, min(127, int(round(v))))


def filter_limbs():
    """Keep only what two hands and two feet can actually play."""
    ev = sorted(EVENTS, key=lambda e: (sec_at(e[0]), e[1]))
    lh = rh = lf = rf = -1e9
    last_note = None
    last_hand = None
    out = []

    for e in ev:
        t = sec_at(e[0])
        n = e[1]

        if n in FEET_KICK:
            if t - rf < MIN_FOOT:
                continue
            rf = t
        elif n in FEET_PEDAL:
            if t - lf < MIN_FOOT:
                continue
            lf = t
        else:
            if n in HAND_RH:
                order = ['RH', 'LH']
            elif n in HAND_LH:
                order = ['LH', 'RH']
            else:
                order = ['LH', 'RH']

            # repeated strokes on the same drum alternate between the hands
            if last_note == n and last_hand == order[0]:
                order = [order[1], order[0]]

            chosen = None
            for h in order:
                if h == 'LH' and t - lh >= MIN_HAND:
                    chosen = 'LH'
                    lh = t
                    break
                if h == 'RH' and t - rh >= MIN_HAND:
                    chosen = 'RH'
                    rh = t
                    break
            if chosen is None:
                continue
            last_note = n
            last_hand = chosen

        out.append(e)

    return out


def clamp_durations(ev):
    """A drum can't still be ringing from the previous stroke of the same pad."""
    by_note = {}
    for e in ev:
        by_note.setdefault(e[1], []).append(e)
    for lst in by_note.values():
        lst.sort(key=lambda e: e[0])
        for i in range(len(lst) - 1):
            gap = lst[i + 1][0] - lst[i][0]
            if lst[i][3] > gap - 1e-3:
                lst[i][3] = max(0.015, gap - 1e-3)
    return ev


# --- file writing ------------------------------------------------------------
def write_midi(notes, path='solo.mid'):
    mid = MidiFile(type=1, ticks_per_beat=PPQ)

    # track 0: tempo / time feel
    meta = MidiTrack()
    mid.tracks.append(meta)
    meta.append(MetaMessage('track_name', name='Drum Solo', time=0))
    meta.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    meta.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm_at(0)), time=0))
    prev = 0
    for b in range(1, 245):
        tick = int(round(b * PPQ))
        meta.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm_at(b)), time=tick - prev))
        prev = tick
    meta.append(MetaMessage('end_of_track', time=0))

    # track 1: the drums
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Drums', time=0))

    msgs = []
    for beat, note, vel, dur, cls in notes:
        on = int(round(beat * PPQ))
        if on < 0:
            on = 0
        off = int(round((beat + dur) * PPQ))
        if off <= on:
            off = on + 12
        msgs.append((on, 1, note, int(vel)))
        msgs.append((off, 0, note, 0))

    # note-offs sort before note-ons at the same tick
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    prev = 0
    for tick, kind, note, vel in msgs:
        delta = tick - prev
        if delta < 0:
            delta = 0
        prev = tick
        if kind:
            track.append(Message('note_on', channel=CH, note=note,
                                 velocity=vel, time=delta))
        else:
            track.append(Message('note_off', channel=CH, note=note,
                                 velocity=0, time=delta))
    track.append(MetaMessage('end_of_track', time=0))

    mid.save(path)


def main():
    compose()
    humanize()
    notes = filter_limbs()
    notes = clamp_durations(notes)
    write_midi(notes, 'solo.mid')


if __name__ == '__main__':
    main()
