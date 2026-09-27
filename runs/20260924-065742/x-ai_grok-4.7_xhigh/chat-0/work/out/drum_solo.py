#!/usr/bin/env python3
"""Two-minute General MIDI drum solo.

48 bars of 4/4 at 96 BPM = 192 beats = 120.000 seconds.
Channel 10 (mido channel 9). Deterministic: no randomness.

Motifs
  A   pickup, ACCENT on 2, ghost, pickup, accent on 4. The question.
  A'  the answer: accents on 1 and 3, trailing off.
  B   A's rhythm played as a tom melody (50-48-45-43-41 and its rise).
  K   funk kick: 1, a-of-1, 3, a-of-3. Returns under the double-time build.
  C   accents grouped in 3s. Learned on the snare, then orchestrated on toms.
  5s  groups of 5 sixteenths, interrupted by silence before the recap.

Feel (uniform per section, never random jitter). 1 tick = 1.302 ms.
  bars  0-3   +18 ticks  gentle layback
  bars  4-13  +8         settled pocket, slightly behind
  bars 14-19   0         straight funk; kick a further 16 ticks ahead
  bars 20-23  +32        the time floats
  bars 24-27  +4         center, rebuilding
  bars 28-31  -30        pushing
  bars 32-39  -20        on top
  bars 40-43  +8         home pocket (same as the exposition)
  bars 44-47  +22        layback, the opening's family

One drummer: RH, LH, RF (bass drum), LF (hat pedal). At most one note per limb
at a time, so never more than two hands and two feet at once.
"""

from collections import defaultdict

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

TPB = 480
BAR = 1920
N_BARS = 48
CHANNEL = 9  # MIDI channel 10
TEMPO = bpm2tempo(96)
assert TEMPO == 625000

# General MIDI percussion
KICK = 36
BOMB = 35
SIDE = 37
SNARE = 38
CLOSED = 42
PEDAL = 44
OPEN_HAT = 46
TOM_LF = 41
TOM_F = 43
TOM_L = 45
TOM_M = 47
TOM_HM = 48
TOM_H = 50
CRASH = 49
RIDE = 51
CHINA = 52
BELL = 53
SPLASH = 55
COWBELL = 56
CRASH2 = 57
RIDE2 = 59
WOODB_HI = 76
WOODB_LO = 77
TRI_MUTE = 80
TRI_OPEN = 81

FUNK_LO, FUNK_HI = 14, 19
FUNK_KICK_AHEAD = 16


def _build_shifts():
    shifts = [0] * N_BARS
    for start, end, value in (
        (0, 4, 18),
        (4, 14, 8),
        (14, 20, 0),
        (20, 24, 32),
        (24, 28, 4),
        (28, 32, -30),
        (32, 40, -20),
        (40, 44, 8),
        (44, 48, 22),
    ):
        for bar in range(start, end):
            shifts[bar] = value
    return tuple(shifts)


SHIFT = _build_shifts()
assert SHIFT[0] == 18 and SHIFT[6] == 8 and SHIFT[14] == 0
assert SHIFT[20] == 32 and SHIFT[28] == -30 and SHIFT[32] == -20
assert SHIFT[40] == 8 and SHIFT[44] == 22 and len(SHIFT) == 48

events = []
limb_times = {'RH': [], 'LH': [], 'RF': [], 'LF': []}


def add(bar, tick_in_bar, note, vel, limb, extra=0):
    if not 0 <= bar < N_BARS:
        raise RuntimeError(f'bar out of range: {bar}')
    if limb not in limb_times:
        raise RuntimeError(f'bad limb {limb}')
    if not 35 <= note <= 81:
        raise RuntimeError(f'note {note} outside GM percussion')
    vel = int(round(vel))
    vel = 1 if vel < 1 else 127 if vel > 127 else vel
    shift = SHIFT[bar]
    if limb == 'RF' and FUNK_LO <= bar <= FUNK_HI:
        shift -= FUNK_KICK_AHEAD
    abs_tick = bar * BAR + tick_in_bar + shift + extra
    if abs_tick < 0 or abs_tick >= N_BARS * BAR:
        raise RuntimeError(
            f'tick {abs_tick} out of range (bar {bar}, in-bar {tick_in_bar}, extra {extra})'
        )
    for prev in limb_times[limb]:
        gap = abs(abs_tick - prev)
        if gap < 100:
            raise RuntimeError(
                f'{limb} notes {gap} ticks apart at {prev} and {abs_tick} '
                f'(bar {bar}, note {note})'
            )
    limb_times[limb].append(abs_tick)
    events.append((abs_tick, note, vel, limb))


def trip(bar, rows):
    for beat, sub, note, vel, limb in rows:
        add(bar, beat * TPB + sub * 160, note, vel, limb)


def straight(bar, rows):
    for pos, note, vel, limb in rows:
        add(bar, pos * 120, note, vel, limb)


def stack(bar, tick_in_bar, parts):
    for note, vel, limb in parts:
        add(bar, tick_in_bar, note, vel, limb)


def ride(bar, vel, instrument=RIDE, skip=(), bells=()):
    """Jazz ride: spang spang-a lang, skip-beats ghosted. Consistent every bar."""
    pattern = (
        (0, 0, 1.00, True),
        (1, 0, 0.88, True),
        (1, 2, 0.50, False),
        (2, 0, 0.94, True),
        (3, 0, 0.84, True),
        (3, 2, 0.46, False),
    )
    skipped = set(skip)
    bell_beats = set(bells)
    rows = []
    for beat, sub, mult, can_bell in pattern:
        if (beat, sub) in skipped:
            continue
        inst = BELL if can_bell and beat in bell_beats else instrument
        rows.append((beat, sub, inst, int(round(vel * mult)), 'RH'))
    trip(bar, rows)


def motif_a(bar, note, accent, medium, ghost, limb='LH'):
    """Motif A on the swung triplet grid."""
    trip(bar, [
        (0, 2, note, ghost, limb),
        (1, 0, note, accent, limb),
        (1, 1, note, ghost, limb),
        (2, 2, note, max(40, ghost - 4), limb),
        (3, 0, note, medium, limb),
    ])


def motif_ap(bar, note, accent, medium, ghost, limb='LH'):
    """Motif A', the answer."""
    trip(bar, [
        (0, 0, note, accent, limb),
        (0, 2, note, ghost, limb),
        (1, 1, note, ghost, limb),
        (1, 2, note, max(40, ghost - 2), limb),
        (2, 0, note, accent, limb),
        (3, 1, note, medium, limb),
    ])


def flam(bar, beat, sub, note, vel, accent='LH', gap=18):
    """Tight, consistent flam. Grace hand, then the accent. Gap is fixed."""
    grace = 'RH' if accent == 'LH' else 'LH'
    tick = beat * TPB + sub * 160
    add(bar, tick, note, max(40, int(round(vel * 0.42))), grace, extra=-gap)
    add(bar, tick, note, vel, accent)


def chicks(bar, vel, beats):
    trip(bar, [(beat, 0, PEDAL, vel, 'LF') for beat in beats])


def funk_hats(bar, vel, upto=16, open_pos=None):
    rows = []
    for i in range(upto):
        if open_pos is not None and i == open_pos:
            rows.append((i, OPEN_HAT, min(127, vel + 6), 'RH'))
            continue
        if i % 4 == 0:
            v = vel
        elif i % 4 == 2:
            v = vel - 14
        elif i % 4 == 1:
            v = vel - 26
        else:
            v = vel - 22
        rows.append((i, CLOSED, max(32, v), 'RH'))
    straight(bar, rows)


# ---------------------------------------------------------------------------
# Exposition. Motif A is stated, then answered.
# ---------------------------------------------------------------------------

def exposition():
    # Bar 0 — first hearing. Side stick, a heartbeat, a closed hat.
    trip(0, [
        (0, 0, KICK, 56, 'RF'),
        (0, 0, CLOSED, 40, 'RH'),
        (2, 0, CLOSED, 36, 'RH'),
        (1, 0, PEDAL, 30, 'LF'),
        (3, 0, PEDAL, 28, 'LF'),
        (0, 2, SIDE, 44, 'LH'),
        (1, 0, SIDE, 72, 'LH'),
        (1, 1, SIDE, 42, 'LH'),
        (2, 2, SIDE, 40, 'LH'),
        (3, 0, SIDE, 58, 'LH'),
    ])
    # Bar 1 — the skeleton only: pickup and the two accents. Space.
    trip(1, [
        (0, 0, KICK, 50, 'RF'),
        (0, 0, CLOSED, 38, 'RH'),
        (2, 0, CLOSED, 34, 'RH'),
        (1, 0, PEDAL, 28, 'LF'),
        (3, 0, PEDAL, 26, 'LF'),
        (0, 2, SIDE, 42, 'LH'),
        (1, 0, SIDE, 66, 'LH'),
        (3, 0, SIDE, 52, 'LH'),
    ])
    # Bar 2 — the kick joins the accent. The kit starts to assemble.
    trip(2, [
        (0, 0, KICK, 58, 'RF'),
        (1, 0, KICK, 74, 'RF'),
        (0, 0, CLOSED, 40, 'RH'),
        (2, 0, CLOSED, 36, 'RH'),
        (1, 0, PEDAL, 30, 'LF'),
        (3, 0, PEDAL, 28, 'LF'),
        (0, 2, SIDE, 46, 'LH'),
        (1, 0, SIDE, 80, 'LH'),
        (1, 1, SIDE, 44, 'LH'),
        (2, 2, SIDE, 40, 'LH'),
        (3, 0, SIDE, 64, 'LH'),
    ])
    # Bar 3 — A' answers, and fades. Mute triangle as a question mark.
    trip(3, [
        (0, 0, KICK, 48, 'RF'),
        (1, 0, PEDAL, 26, 'LF'),
        (3, 0, PEDAL, 24, 'LF'),
        (0, 0, SIDE, 56, 'LH'),
        (0, 2, SIDE, 42, 'LH'),
        (1, 1, SIDE, 40, 'LH'),
        (1, 2, SIDE, 40, 'LH'),
        (2, 0, SIDE, 50, 'LH'),
        (3, 1, SIDE, 42, 'LH'),
        (3, 2, TRI_MUTE, 48, 'RH'),
    ])

    # Bar 4 — ride enters, snare inherits the motif. Jazz time begins.
    ride(4, 66)
    motif_a(4, SNARE, 86, 70, 44)
    trip(4, [
        (0, 0, KICK, 56, 'RF'),
        (2, 0, KICK, 52, 'RF'),
        (1, 0, PEDAL, 34, 'LF'),
        (3, 0, PEDAL, 32, 'LF'),
    ])
    # Bar 5 — denser ghosts, a soft syncopated kick, bell on 1.
    ride(5, 70, bells=(0,))
    motif_a(5, SNARE, 94, 76, 46)
    trip(5, [
        (2, 0, SNARE, 42, 'LH'),
        (3, 2, SNARE, 40, 'LH'),
        (0, 0, KICK, 58, 'RF'),
        (1, 2, KICK, 44, 'RF'),
        (2, 0, KICK, 54, 'RF'),
        (1, 0, PEDAL, 34, 'LF'),
        (3, 0, PEDAL, 32, 'LF'),
    ])
    # Bar 6 — A displaced by one beat. The phrase leans against the barline.
    ride(6, 62)
    trip(6, [
        (1, 2, SNARE, 44, 'LH'),
        (2, 0, SNARE, 100, 'LH'),
        (2, 1, SNARE, 44, 'LH'),
        (3, 2, SNARE, 42, 'LH'),
        (0, 0, KICK, 54, 'RF'),
        (2, 0, KICK, 80, 'RF'),
        (1, 0, PEDAL, 32, 'LF'),
        (3, 0, PEDAL, 30, 'LF'),
    ])
    # Bar 7 — the displaced phrase resolves onto beat 1, which is also A'.
    ride(7, 64, skip=((3, 2),))
    motif_ap(7, SNARE, 90, 66, 42)
    trip(7, [
        (3, 2, TOM_L, 78, 'RH'),
        (0, 0, KICK, 60, 'RF'),
        (2, 0, KICK, 66, 'RF'),
        (1, 0, PEDAL, 32, 'LF'),
        (3, 0, PEDAL, 30, 'LF'),
    ])


# ---------------------------------------------------------------------------
# Call and response. Motif B is born: A's rhythm, tom melody.
# ---------------------------------------------------------------------------

def conversation():
    # Bar 8 — call.
    ride(8, 64)
    motif_a(8, SNARE, 100, 82, 46)
    trip(8, [
        (0, 0, KICK, 62, 'RF'),
        (1, 0, KICK, 82, 'RF'),
        (3, 0, KICK, 74, 'RF'),
        (1, 0, PEDAL, 36, 'LF'),
        (3, 0, PEDAL, 34, 'LF'),
    ])
    # Bar 9 — response, descending. 50 48 45 43 41.
    trip(9, [
        (0, 2, TOM_H, 76, 'RH'),
        (1, 0, TOM_HM, 100, 'RH'),
        (1, 1, TOM_L, 58, 'RH'),
        (2, 2, TOM_F, 64, 'RH'),
        (3, 0, TOM_LF, 92, 'RH'),
        (0, 0, SNARE, 44, 'LH'),
        (2, 0, SNARE, 40, 'LH'),
        (1, 0, KICK, 74, 'RF'),
        (3, 0, KICK, 68, 'RF'),
        (1, 0, PEDAL, 32, 'LF'),
        (3, 0, PEDAL, 30, 'LF'),
    ])
    # Bar 10 — call, denser, a slow ruff into the accent.
    ride(10, 68, bells=(0,))
    motif_a(10, SNARE, 108, 88, 48)
    trip(10, [
        (0, 1, SNARE, 42, 'LH'),
        (2, 0, SNARE, 44, 'LH'),
        (2, 1, SNARE, 40, 'LH'),
        (0, 0, KICK, 66, 'RF'),
        (1, 0, KICK, 86, 'RF'),
        (2, 2, KICK, 52, 'RF'),
        (3, 0, KICK, 78, 'RF'),
        (1, 0, PEDAL, 36, 'LF'),
        (3, 0, PEDAL, 34, 'LF'),
    ])
    # Bar 11 — response rises: 41 43 45 48 50, splash afterbeat.
    trip(11, [
        (0, 2, TOM_LF, 82, 'RH'),
        (1, 0, TOM_F, 106, 'RH'),
        (1, 1, TOM_L, 62, 'RH'),
        (2, 2, TOM_HM, 70, 'RH'),
        (3, 0, TOM_H, 114, 'RH'),
        (0, 0, SNARE, 46, 'LH'),
        (2, 0, SNARE, 42, 'LH'),
        (3, 2, SPLASH, 68, 'LH'),
        (0, 0, KICK, 62, 'RF'),
        (1, 0, KICK, 82, 'RF'),
        (3, 0, KICK, 88, 'RF'),
        (1, 0, PEDAL, 34, 'LF'),
        (3, 0, PEDAL, 32, 'LF'),
    ])
    # Bar 12 — half-bar dialogue, then a unison accent.
    ride(12, 66, skip=((3, 0), (3, 2)))
    trip(12, [
        (0, 2, SNARE, 44, 'LH'),
        (1, 0, SNARE, 100, 'LH'),
        (1, 1, SNARE, 42, 'LH'),
        (2, 2, TOM_HM, 86, 'RH'),
        (3, 0, TOM_L, 106, 'RH'),
        (3, 0, SNARE, 98, 'LH'),
        (3, 1, TOM_LF, 80, 'RH'),
        (0, 0, KICK, 64, 'RF'),
        (1, 0, KICK, 82, 'RF'),
        (3, 0, KICK, 90, 'RF'),
        (1, 0, PEDAL, 36, 'LF'),
        (3, 0, PEDAL, 36, 'LF'),
    ])
    # Bar 13 — crescendo fill around the kit, landing into the groove.
    trip(13, [
        (0, 0, TOM_H, 76, 'RH'),
        (0, 1, TOM_H, 72, 'LH'),
        (0, 2, TOM_HM, 80, 'RH'),
        (1, 0, TOM_HM, 82, 'LH'),
        (1, 1, TOM_M, 88, 'RH'),
        (1, 2, TOM_M, 86, 'LH'),
        (2, 0, TOM_L, 94, 'RH'),
        (2, 1, TOM_L, 92, 'LH'),
        (2, 2, TOM_F, 100, 'RH'),
        (3, 0, TOM_F, 106, 'LH'),
        (3, 1, TOM_LF, 114, 'RH'),
        (3, 2, SNARE, 122, 'LH'),
        (0, 0, KICK, 72, 'RF'),
        (2, 0, KICK, 86, 'RF'),
        (3, 0, KICK, 98, 'RF'),
        (1, 0, PEDAL, 34, 'LF'),
        (3, 0, PEDAL, 40, 'LF'),
    ])


# ---------------------------------------------------------------------------
# Straight funk. Contrast of grid. Motif K in the feet.
# Then A, translated into straight 16ths, on the cowbell.
# ---------------------------------------------------------------------------

def funk():
    # Bar 14 — the groove, plain, so it can be recognized.
    funk_hats(14, 74)
    straight(14, [
        (3, SNARE, 42, 'LH'),
        (4, SNARE, 104, 'LH'),
        (7, SNARE, 40, 'LH'),
        (9, SNARE, 40, 'LH'),
        (11, SNARE, 42, 'LH'),
        (12, SNARE, 106, 'LH'),
        (14, SNARE, 40, 'LH'),
        (0, KICK, 100, 'RF'),
        (3, KICK, 82, 'RF'),
        (8, KICK, 96, 'RF'),
        (11, KICK, 78, 'RF'),
    ])
    # Bar 15 — open hat on the & of 3, kick variation.
    funk_hats(15, 78, open_pos=10)
    straight(15, [
        (3, SNARE, 44, 'LH'),
        (4, SNARE, 108, 'LH'),
        (7, SNARE, 42, 'LH'),
        (9, SNARE, 40, 'LH'),
        (12, SNARE, 110, 'LH'),
        (14, SNARE, 44, 'LH'),
        (15, SNARE, 40, 'LH'),
        (0, KICK, 102, 'RF'),
        (3, KICK, 84, 'RF'),
        (6, KICK, 80, 'RF'),
        (10, KICK, 90, 'RF'),
    ])
    # Bar 16 — half-time backbeat on 3. Same kick motif, more air.
    straight(16, [
        (0, CLOSED, 72, 'RH'),
        (2, CLOSED, 52, 'RH'),
        (4, CLOSED, 68, 'RH'),
        (6, CLOSED, 50, 'RH'),
        (8, CLOSED, 74, 'RH'),
        (10, CLOSED, 52, 'RH'),
        (12, CLOSED, 66, 'RH'),
        (14, CLOSED, 48, 'RH'),
        (3, SNARE, 40, 'LH'),
        (7, SNARE, 40, 'LH'),
        (8, SNARE, 112, 'LH'),
        (11, SNARE, 42, 'LH'),
        (14, SNARE, 40, 'LH'),
        (0, KICK, 102, 'RF'),
        (3, KICK, 84, 'RF'),
        (8, KICK, 108, 'RF'),
        (11, KICK, 80, 'RF'),
    ])
    # Bar 17 — cowbell states the straight translation of A, quietly.
    straight(17, [
        (3, COWBELL, 48, 'RH'),
        (4, COWBELL, 92, 'RH'),
        (5, COWBELL, 44, 'RH'),
        (11, COWBELL, 46, 'RH'),
        (12, COWBELL, 88, 'RH'),
        (4, SNARE, 84, 'LH'),
        (7, SNARE, 40, 'LH'),
        (9, SNARE, 40, 'LH'),
        (12, SNARE, 82, 'LH'),
        (0, KICK, 96, 'RF'),
        (6, KICK, 78, 'RF'),
        (8, KICK, 90, 'RF'),
        (14, KICK, 74, 'RF'),
        (4, PEDAL, 30, 'LF'),
        (12, PEDAL, 28, 'LF'),
    ])
    # Bar 18 — the same phrase, louder. Now you know you heard it.
    straight(18, [
        (3, COWBELL, 60, 'RH'),
        (4, COWBELL, 104, 'RH'),
        (5, COWBELL, 52, 'RH'),
        (11, COWBELL, 56, 'RH'),
        (12, COWBELL, 100, 'RH'),
        (4, SNARE, 94, 'LH'),
        (7, SNARE, 42, 'LH'),
        (9, SNARE, 40, 'LH'),
        (12, SNARE, 92, 'LH'),
        (0, KICK, 100, 'RF'),
        (6, KICK, 82, 'RF'),
        (8, KICK, 94, 'RF'),
        (13, KICK, 72, 'RF'),
        (4, PEDAL, 32, 'LF'),
        (12, PEDAL, 30, 'LF'),
    ])
    # Bar 19 — two beats of groove, then a fill that gets quieter. The floor drops.
    straight(19, [
        (0, CLOSED, 66, 'RH'),
        (1, CLOSED, 44, 'RH'),
        (2, CLOSED, 58, 'RH'),
        (3, CLOSED, 42, 'RH'),
        (4, CLOSED, 64, 'RH'),
        (5, CLOSED, 42, 'RH'),
        (6, CLOSED, 54, 'RH'),
        (7, CLOSED, 40, 'RH'),
        (3, SNARE, 40, 'LH'),
        (4, SNARE, 96, 'LH'),
        (7, SNARE, 40, 'LH'),
        (0, KICK, 92, 'RF'),
        (3, KICK, 74, 'RF'),
        (8, TOM_HM, 72, 'RH'),
        (9, TOM_M, 64, 'LH'),
        (10, TOM_L, 56, 'RH'),
        (11, TOM_F, 48, 'LH'),
        (12, TOM_LF, 44, 'RH'),
        (13, TOM_LF, 40, 'LH'),
        (14, SNARE, 40, 'RH'),
        (15, SIDE, 40, 'LH'),
    ])


# ---------------------------------------------------------------------------
# The eye. Fragments. The motif survives in other voices.
# ---------------------------------------------------------------------------

def eye():
    # Bar 20 — one accent, then an open triangle that rings into the next bar.
    trip(20, [
        (0, 0, KICK, 44, 'RF'),
        (1, 0, SIDE, 54, 'LH'),
        (1, 1, SIDE, 40, 'LH'),
        (3, 0, PEDAL, 24, 'LF'),
        (3, 2, TRI_OPEN, 48, 'RH'),
    ])
    # Bar 21 — A, almost, with a floor-tom sigh in the hole.
    trip(21, [
        (0, 2, SIDE, 42, 'LH'),
        (1, 0, SIDE, 50, 'LH'),
        (1, 0, PEDAL, 24, 'LF'),
        (2, 0, TOM_LF, 42, 'RH'),
        (2, 2, SIDE, 40, 'LH'),
        (3, 0, SIDE, 44, 'LH'),
        (3, 0, PEDAL, 22, 'LF'),
    ])
    # Bar 22 — wood blocks play A as a two-note melody. Side stick doubles the accents.
    trip(22, [
        (0, 0, KICK, 42, 'RF'),
        (0, 2, WOODB_LO, 42, 'RH'),
        (1, 0, WOODB_HI, 62, 'RH'),
        (1, 0, SIDE, 46, 'LH'),
        (1, 1, WOODB_LO, 40, 'RH'),
        (2, 2, WOODB_HI, 44, 'RH'),
        (3, 0, WOODB_LO, 52, 'RH'),
        (3, 0, SIDE, 42, 'LH'),
        (3, 2, SPLASH, 54, 'LH'),
    ])
    # Bar 23 — one accent, unanswered. Mute triangle closes the open one. Inhale.
    trip(23, [
        (0, 0, KICK, 42, 'RF'),
        (1, 0, SIDE, 52, 'LH'),
        (3, 2, TRI_MUTE, 44, 'RH'),
    ])


# ---------------------------------------------------------------------------
# Rebuild, then double-time. Flams. Groups of 3. Motif K returns.
# ---------------------------------------------------------------------------

def build():
    # Bar 24 — A comes back, the way a theme comes back after a silence.
    ride(24, 62)
    motif_a(24, SNARE, 80, 66, 44)
    trip(24, [
        (0, 0, KICK, 50, 'RF'),
        (1, 0, KICK, 66, 'RF'),
        (3, 0, KICK, 60, 'RF'),
        (1, 0, PEDAL, 32, 'LF'),
        (3, 0, PEDAL, 30, 'LF'),
    ])
    # Bar 25 — bell, and open hats on the skip-beats (choked a triplet later).
    ride(25, 74, bells=(0, 2), skip=((1, 2), (3, 2)))
    motif_a(25, SNARE, 92, 76, 46)
    trip(25, [
        (1, 2, OPEN_HAT, 68, 'RH'),
        (3, 2, OPEN_HAT, 64, 'RH'),
        (2, 0, SNARE, 42, 'LH'),
        (0, 0, KICK, 64, 'RF'),
        (1, 0, KICK, 78, 'RF'),
        (2, 2, KICK, 54, 'RF'),
        (3, 0, KICK, 74, 'RF'),
        (1, 0, PEDAL, 36, 'LF'),
        (2, 0, PEDAL, 42, 'LF'),
        (3, 0, PEDAL, 34, 'LF'),
    ])
    # Bar 26 — flams on the accents. Ride steps aside so the grace hand is free.
    ride(26, 76, bells=(0,), skip=((1, 0), (1, 2), (3, 0), (3, 2)))
    flam(26, 1, 0, SNARE, 106)
    flam(26, 3, 0, SNARE, 102)
    trip(26, [
        (0, 2, SNARE, 46, 'LH'),
        (1, 1, SNARE, 44, 'LH'),
        (2, 2, SNARE, 42, 'LH'),
        (3, 2, TOM_HM, 84, 'RH'),
        (0, 0, KICK, 68, 'RF'),
        (1, 0, KICK, 94, 'RF'),
        (3, 0, KICK, 92, 'RF'),
        (0, 0, PEDAL, 36, 'LF'),
        (1, 0, PEDAL, 40, 'LF'),
        (2, 0, PEDAL, 32, 'LF'),
        (3, 0, PEDAL, 38, 'LF'),
    ])
    # Bar 27 — A' at a shout's doorway. Tom on the last skip-beat leads downhill.
    ride(27, 82, bells=(0, 2), skip=((3, 2),))
    motif_ap(27, SNARE, 110, 90, 48)
    trip(27, [
        (3, 2, TOM_M, 98, 'RH'),
        (0, 0, KICK, 86, 'RF'),
        (2, 0, KICK, 90, 'RF'),
        (1, 0, PEDAL, 38, 'LF'),
        (3, 0, PEDAL, 36, 'LF'),
    ])

    # Bar 28 — straight 8ths on the ride, snare in groups of 3, kick plays motif K.
    straight(28, [
        (0, RIDE, 86, 'RH'),
        (2, RIDE, 62, 'RH'),
        (4, RIDE, 82, 'RH'),
        (6, RIDE, 60, 'RH'),
        (8, RIDE, 84, 'RH'),
        (10, RIDE, 60, 'RH'),
        (12, RIDE, 80, 'RH'),
        (14, RIDE, 56, 'RH'),
        (0, SNARE, 94, 'LH'),
        (3, SNARE, 92, 'LH'),
        (4, SNARE, 42, 'LH'),
        (6, SNARE, 96, 'LH'),
        (7, SNARE, 40, 'LH'),
        (9, SNARE, 98, 'LH'),
        (10, SNARE, 42, 'LH'),
        (12, SNARE, 102, 'LH'),
        (13, SNARE, 44, 'LH'),
        (15, SNARE, 104, 'LH'),
        (0, KICK, 96, 'RF'),
        (3, KICK, 80, 'RF'),
        (8, KICK, 92, 'RF'),
        (11, KICK, 76, 'RF'),
        (4, PEDAL, 36, 'LF'),
        (12, PEDAL, 36, 'LF'),
    ])
    # Bar 29 — the same groups of 3, now a tom line (motif B's pitches) landing on snare.
    straight(29, [
        (0, TOM_H, 104, 'RH'),
        (3, TOM_HM, 108, 'RH'),
        (6, TOM_L, 112, 'RH'),
        (9, TOM_F, 116, 'RH'),
        (12, TOM_LF, 120, 'RH'),
        (15, SNARE, 124, 'LH'),
        (1, SNARE, 46, 'LH'),
        (4, SNARE, 44, 'LH'),
        (7, SNARE, 48, 'LH'),
        (10, SNARE, 46, 'LH'),
        (13, SNARE, 50, 'LH'),
        (0, KICK, 104, 'RF'),
        (3, KICK, 88, 'RF'),
        (8, KICK, 100, 'RF'),
        (11, KICK, 82, 'RF'),
        (4, PEDAL, 38, 'LF'),
        (12, PEDAL, 40, 'LF'),
    ])
    # Bar 30 — both hands, 16ths, accents still in 3s. Ghosts against accents.
    straight(30, [
        (0, TOM_H, 114, 'RH'),
        (1, SNARE, 72, 'LH'),
        (2, TOM_HM, 70, 'RH'),
        (3, SNARE, 110, 'LH'),
        (4, TOM_M, 68, 'RH'),
        (5, SNARE, 66, 'LH'),
        (6, TOM_L, 116, 'RH'),
        (7, SNARE, 74, 'LH'),
        (8, TOM_F, 72, 'RH'),
        (9, SNARE, 118, 'LH'),
        (10, TOM_LF, 76, 'RH'),
        (11, SNARE, 72, 'LH'),
        (12, TOM_HM, 122, 'RH'),
        (13, SNARE, 78, 'LH'),
        (14, TOM_L, 80, 'RH'),
        (15, SNARE, 124, 'LH'),
        (0, KICK, 108, 'RF'),
        (6, KICK, 98, 'RF'),
        (8, KICK, 104, 'RF'),
        (12, KICK, 114, 'RF'),
        (4, PEDAL, 42, 'LF'),
        (12, PEDAL, 46, 'LF'),
    ])
    # Bar 31 — descending 16ths, crescendo, into the crash.
    straight(31, [
        (0, TOM_H, 94, 'RH'),
        (1, TOM_H, 92, 'LH'),
        (2, TOM_HM, 98, 'RH'),
        (3, TOM_HM, 96, 'LH'),
        (4, TOM_M, 102, 'RH'),
        (5, TOM_M, 100, 'LH'),
        (6, TOM_L, 106, 'RH'),
        (7, TOM_L, 104, 'LH'),
        (8, TOM_F, 110, 'RH'),
        (9, TOM_F, 108, 'LH'),
        (10, TOM_LF, 114, 'RH'),
        (11, TOM_LF, 112, 'LH'),
        (12, SNARE, 120, 'RH'),
        (13, SNARE, 118, 'LH'),
        (14, SNARE, 124, 'RH'),
        (15, SNARE, 127, 'LH'),
        (0, KICK, 104, 'RF'),
        (4, KICK, 108, 'RF'),
        (8, KICK, 114, 'RF'),
        (12, KICK, 122, 'RF'),
    ])


# ---------------------------------------------------------------------------
# The storm, the shout, the hole in the time.
# ---------------------------------------------------------------------------

def storm():
    # Bar 32 — lightning, then motif A, loud and readable, inside the weather.
    stack(32, 0, [
        (CRASH, 126, 'RH'),
        (SNARE, 116, 'LH'),
        (BOMB, 127, 'RF'),
        (PEDAL, 56, 'LF'),
    ])
    trip(32, [
        (0, 2, SNARE, 60, 'LH'),
        (1, 0, TOM_HM, 104, 'RH'),
        (1, 0, SNARE, 124, 'LH'),
        (1, 0, KICK, 118, 'RF'),
        (1, 1, SNARE, 56, 'LH'),
        (1, 2, TOM_L, 90, 'RH'),
        (2, 0, BELL, 94, 'RH'),
        (2, 0, KICK, 74, 'RF'),
        (2, 0, PEDAL, 42, 'LF'),
        (2, 2, SNARE, 58, 'LH'),
        (3, 0, TOM_F, 112, 'RH'),
        (3, 0, SNARE, 118, 'LH'),
        (3, 0, KICK, 114, 'RF'),
        (3, 2, SNARE, 74, 'LH'),
    ])
    # Bar 33 — a line, not a machine: down, back up, land on the snare.
    trip(33, [
        (0, 0, TOM_H, 106, 'RH'),
        (0, 1, TOM_HM, 98, 'LH'),
        (0, 2, TOM_M, 102, 'RH'),
        (1, 0, TOM_L, 100, 'LH'),
        (1, 1, TOM_F, 104, 'RH'),
        (1, 2, TOM_L, 102, 'LH'),
        (2, 0, TOM_M, 110, 'RH'),
        (2, 1, TOM_HM, 106, 'LH'),
        (2, 2, TOM_H, 114, 'RH'),
        (3, 0, TOM_HM, 112, 'LH'),
        (3, 1, TOM_L, 118, 'RH'),
        (3, 2, SNARE, 124, 'LH'),
        (0, 0, KICK, 108, 'RF'),
        (2, 0, KICK, 112, 'RF'),
        (1, 0, PEDAL, 40, 'LF'),
        (3, 0, PEDAL, 42, 'LF'),
    ])
    # Bar 34 — A orchestrated: cowbell on the ghosts, china and crash on the accents.
    stack(34, 0, [
        (CHINA, 124, 'RH'),
        (SNARE, 118, 'LH'),
        (KICK, 124, 'RF'),
        (PEDAL, 54, 'LF'),
    ])
    trip(34, [
        (0, 1, SNARE, 72, 'LH'),
        (0, 2, COWBELL, 84, 'RH'),
        (1, 0, CRASH, 122, 'RH'),
        (1, 0, SNARE, 120, 'LH'),
        (1, 0, KICK, 116, 'RF'),
        (1, 1, SNARE, 64, 'LH'),
        (1, 2, TOM_H, 98, 'RH'),
        (2, 0, TOM_M, 104, 'RH'),
        (2, 0, KICK, 82, 'RF'),
        (2, 0, PEDAL, 42, 'LF'),
        (2, 1, SNARE, 66, 'LH'),
        (2, 2, COWBELL, 92, 'RH'),
        (3, 0, CHINA, 127, 'RH'),
        (3, 0, TOM_LF, 114, 'LH'),
        (3, 0, KICK, 122, 'RF'),
        (3, 0, PEDAL, 50, 'LF'),
        (3, 1, SNARE, 78, 'LH'),
        (3, 2, TOM_L, 94, 'RH'),
    ])
    # Bar 35 — snare roll, accents every third 16th, toms turn the corner.
    roll = [(0, CHINA, 124, 'RH'), (0, KICK, 116, 'RF'), (0, PEDAL, 50, 'LF')]
    for i in range(1, 12):
        limb = 'RH' if i % 2 == 0 else 'LH'
        roll.append((i, SNARE, 90 + i * 2, limb))
    roll.extend([
        (12, TOM_HM, 120, 'RH'),
        (12, KICK, 118, 'RF'),
        (13, TOM_L, 116, 'LH'),
        (14, TOM_F, 124, 'RH'),
        (15, TOM_LF, 127, 'LH'),
        (4, KICK, 104, 'RF'),
        (8, KICK, 112, 'RF'),
        (8, PEDAL, 44, 'LF'),
    ])
    straight(35, roll)

    # Bar 36 — THE statement. Crash announces, then A, in the clear, with the bell.
    stack(36, 0, [
        (CRASH, 122, 'RH'),
        (BOMB, 127, 'RF'),
        (PEDAL, 52, 'LF'),
    ])
    ride(36, 98, bells=(1, 2, 3), skip=((0, 0),))
    motif_a(36, SNARE, 124, 110, 58)
    trip(36, [
        (1, 0, KICK, 120, 'RF'),
        (2, 0, KICK, 72, 'RF'),
        (3, 0, KICK, 112, 'RF'),
        (3, 0, PEDAL, 46, 'LF'),
    ])
    # Bar 37 — A' answers the shout. China on the second accent, a falling tom after.
    stack(37, 0, [
        (CRASH2, 120, 'RH'),
        (SNARE, 122, 'LH'),
        (KICK, 124, 'RF'),
        (PEDAL, 52, 'LF'),
    ])
    trip(37, [
        (0, 2, SNARE, 54, 'LH'),
        (1, 0, BELL, 96, 'RH'),
        (1, 0, KICK, 66, 'RF'),
        (1, 1, SNARE, 50, 'LH'),
        (1, 2, SNARE, 48, 'LH'),
        (1, 2, TOM_HM, 86, 'RH'),
        (2, 0, CHINA, 118, 'RH'),
        (2, 0, SNARE, 122, 'LH'),
        (2, 0, KICK, 120, 'RF'),
        (2, 0, PEDAL, 50, 'LF'),
        (3, 0, BELL, 90, 'RH'),
        (3, 0, PEDAL, 38, 'LF'),
        (3, 1, SNARE, 92, 'LH'),
        (3, 1, TOM_F, 88, 'RH'),
        (3, 1, KICK, 62, 'RF'),
    ])
    # Bar 38 — groups of 5. The next accent would fall in bar 39. It doesn't.
    straight(38, [
        (0, CRASH, 126, 'RH'),
        (0, KICK, 122, 'RF'),
        (0, PEDAL, 52, 'LF'),
        (1, SNARE, 82, 'LH'),
        (2, SNARE, 80, 'RH'),
        (3, TOM_M, 84, 'LH'),
        (4, SNARE, 82, 'RH'),
        (5, SNARE, 124, 'LH'),
        (6, TOM_L, 86, 'RH'),
        (7, SNARE, 82, 'LH'),
        (8, SNARE, 88, 'RH'),
        (8, KICK, 104, 'RF'),
        (8, PEDAL, 42, 'LF'),
        (9, TOM_F, 86, 'LH'),
        (10, CHINA, 126, 'RH'),
        (10, KICK, 116, 'RF'),
        (11, SNARE, 88, 'LH'),
        (12, TOM_LF, 90, 'RH'),
        (13, SNARE, 86, 'LH'),
        (14, SNARE, 92, 'RH'),
        (15, SNARE, 124, 'LH'),
    ])
    # Bar 39 — the pattern breaks. A starts, and stops. Two and a half seconds of almost nothing.
    trip(39, [
        (0, 0, KICK, 50, 'RF'),
        (0, 2, SIDE, 42, 'LH'),
        (1, 0, SIDE, 58, 'LH'),
        (3, 0, PEDAL, 26, 'LF'),
    ])


# ---------------------------------------------------------------------------
# Home. A and B together. The opening texture, a canon, one hit, a whisper.
# ---------------------------------------------------------------------------

def home():
    # Bar 40 — recap. Ride 2, so the return isn't a copy. Pocket matches bar 4.
    ride(40, 68, instrument=RIDE2)
    motif_a(40, SNARE, 92, 74, 44)
    trip(40, [
        (0, 0, KICK, 54, 'RF'),
        (2, 0, KICK, 50, 'RF'),
        (1, 0, PEDAL, 32, 'LF'),
        (3, 0, PEDAL, 30, 'LF'),
    ])
    # Bar 41 — A and B at once. Snare and the descending toms, same rhythm.
    trip(41, [
        (0, 2, SNARE, 44, 'LH'),
        (0, 2, TOM_H, 74, 'RH'),
        (1, 0, SNARE, 96, 'LH'),
        (1, 0, TOM_HM, 102, 'RH'),
        (1, 0, KICK, 76, 'RF'),
        (1, 0, PEDAL, 36, 'LF'),
        (1, 1, SNARE, 46, 'LH'),
        (1, 1, TOM_L, 60, 'RH'),
        (2, 2, SNARE, 42, 'LH'),
        (2, 2, TOM_F, 66, 'RH'),
        (3, 0, SNARE, 88, 'LH'),
        (3, 0, TOM_LF, 94, 'RH'),
        (3, 0, KICK, 72, 'RF'),
        (3, 0, PEDAL, 34, 'LF'),
        (0, 0, KICK, 52, 'RF'),
    ])
    # Bar 42 — A' united with a rising line that crests on beat 3 and settles.
    trip(42, [
        (0, 0, SNARE, 80, 'LH'),
        (0, 0, TOM_LF, 84, 'RH'),
        (0, 0, KICK, 62, 'RF'),
        (0, 2, SNARE, 44, 'LH'),
        (0, 2, TOM_F, 50, 'RH'),
        (1, 1, SNARE, 42, 'LH'),
        (1, 1, TOM_L, 46, 'RH'),
        (1, 2, SNARE, 40, 'LH'),
        (1, 2, TOM_M, 44, 'RH'),
        (2, 0, SNARE, 78, 'LH'),
        (2, 0, TOM_H, 82, 'RH'),
        (2, 0, KICK, 66, 'RF'),
        (2, 0, PEDAL, 32, 'LF'),
        (3, 1, SNARE, 54, 'LH'),
        (3, 1, TOM_HM, 58, 'RH'),
        (1, 0, PEDAL, 28, 'LF'),
    ])
    # Bar 43 — time, and a fragment. The weather has passed.
    ride(43, 56, instrument=RIDE2)
    trip(43, [
        (0, 2, SNARE, 42, 'LH'),
        (1, 1, SNARE, 40, 'LH'),
        (2, 2, SNARE, 42, 'LH'),
        (3, 0, SNARE, 66, 'LH'),
        (0, 0, KICK, 44, 'RF'),
        (2, 0, KICK, 40, 'RF'),
        (1, 0, PEDAL, 28, 'LF'),
        (3, 0, PEDAL, 26, 'LF'),
    ])
    # Bar 44 — side stick and a soft ride. The opening, remembered, with time under it.
    ride(44, 50)
    motif_a(44, SIDE, 58, 48, 42)
    trip(44, [
        (0, 0, KICK, 40, 'RF'),
        (1, 0, PEDAL, 24, 'LF'),
        (3, 0, PEDAL, 22, 'LF'),
    ])
    # Bar 45 — canon at one beat. A's rhythm does not overlap itself, so the hands hocket.
    motif_a(45, SIDE, 50, 44, 42)
    trip(45, [
        (1, 2, WOODB_LO, 42, 'RH'),
        (2, 0, WOODB_HI, 58, 'RH'),
        (2, 1, WOODB_LO, 40, 'RH'),
        (3, 2, WOODB_HI, 44, 'RH'),
        (0, 0, KICK, 40, 'RF'),
        (1, 0, PEDAL, 24, 'LF'),
        (3, 0, PEDAL, 22, 'LF'),
    ])
    # Bar 46 — the arrival. Not louder than the storm. Then one memory of the accent.
    stack(46, 0, [
        (CRASH, 116, 'RH'),
        (SNARE, 108, 'LH'),
        (BOMB, 120, 'RF'),
        (PEDAL, 48, 'LF'),
    ])
    trip(46, [
        (3, 0, SIDE, 44, 'LH'),
    ])
    # Bar 47 — A, whispered, complete. A low tom borrows B's last pitch. Heartbeat stops.
    motif_a(47, SIDE, 52, 44, 42)
    trip(47, [
        (2, 0, TOM_LF, 40, 'RH'),
        (2, 0, KICK, 36, 'RF'),
        (3, 0, KICK, 32, 'RF'),
        (3, 0, PEDAL, 24, 'LF'),
    ])


def compose():
    exposition()
    conversation()
    funk()
    eye()
    build()
    storm()
    home()


def validate(rows):
    if len(rows) < 400:
        raise RuntimeError(f'expected a full solo, got {len(rows)} notes')
    by_limb = {'RH': [], 'LH': [], 'RF': [], 'LF': []}
    at_tick = defaultdict(list)
    for tick, note, vel, limb in rows:
        if limb not in by_limb:
            raise RuntimeError(limb)
        if not 35 <= note <= 81:
            raise RuntimeError(note)
        if not 1 <= vel <= 127:
            raise RuntimeError(vel)
        if note in (35, 36) and limb != 'RF':
            raise RuntimeError('bass drum must be the right foot')
        if note == 44 and limb != 'LF':
            raise RuntimeError('hat pedal must be the left foot')
        if limb in ('RF', 'LF') and note not in (35, 36, 44):
            raise RuntimeError('feet only play kick and hat pedal')
        if limb in ('RH', 'LH') and note in (35, 36, 44):
            raise RuntimeError('hands do not play the feet')
        by_limb[limb].append(tick)
        at_tick[tick].append((note, limb))
    for limb, times in by_limb.items():
        times.sort()
        for earlier, later in zip(times, times[1:]):
            if later - earlier < 100:
                raise RuntimeError(f'{limb} gap {later - earlier} at {earlier}')
    for tick, notes in at_tick.items():
        if len(notes) > 4:
            raise RuntimeError(f'{len(notes)} strikes at tick {tick}')
        limbs = [limb for _, limb in notes]
        if len(set(limbs)) != len(limbs):
            raise RuntimeError(f'one limb struck twice at tick {tick}')
        pitches = [note for note, _ in notes]
        if len(set(pitches)) != len(pitches):
            raise RuntimeError(f'duplicate pitch at tick {tick}')
        hands = sum(limb in ('RH', 'LH') for limb in limbs)
        feet = sum(limb in ('RF', 'LF') for limb in limbs)
        if hands > 2 or feet > 2:
            raise RuntimeError(f'unplayable stack at tick {tick}')
    if min(tick for tick, _, _, _ in rows) < 0:
        raise RuntimeError('negative tick')
    if max(tick for tick, _, _, _ in rows) >= N_BARS * BAR:
        raise RuntimeError('note past the end of the two minutes')


def write_midi(note_events, path):
    by_pitch = defaultdict(list)
    for tick, note, vel in note_events:
        by_pitch[note].append((tick, vel))
    for hits in by_pitch.values():
        hits.sort()

    end_at = N_BARS * BAR
    items = []

    def base_dur(note):
        if note in (49, 52, 55, 57, 81):
            return 1440
        if note in (51, 53, 59, 46, 80):
            return 360
        return 48

    for note, hits in by_pitch.items():
        for i, (tick, vel) in enumerate(hits):
            gap = None if i + 1 == len(hits) else hits[i + 1][0] - tick
            dur = base_dur(note) if gap is None else min(base_dur(note), gap - 1)
            if dur < 1:
                dur = 1
            if tick + dur >= end_at:
                dur = max(1, end_at - tick - 1)
            items.append((tick, 1, 'on', note, vel))
            items.append((tick + dur, 0, 'off', note, 0))

    items.append((0, -7, 'track', 0, 0))
    items.append((0, -6, 'tempo', 0, 0))
    items.append((0, -5, 'time', 0, 0))
    items.append((0, -4, 'cc', 0, 0))
    items.append((0, -4, 'cc', 32, 0))
    items.append((0, -3, 'prog', 0, 0))
    items.append((0, -2, 'cc', 7, 127))
    items.append((0, -2, 'cc', 10, 64))
    items.sort()

    mid = MidiFile(type=1, ticks_per_beat=TPB)
    track = MidiTrack()
    mid.tracks.append(track)
    prev = 0
    for tick, _prio, kind, a, b in items:
        delta = tick - prev
        prev = tick
        if kind == 'on':
            track.append(Message('note_on', channel=CHANNEL, note=a, velocity=b, time=delta))
        elif kind == 'off':
            track.append(Message('note_off', channel=CHANNEL, note=a, velocity=0, time=delta))
        elif kind == 'track':
            track.append(MetaMessage('track_name', name='Drum Solo', time=delta))
        elif kind == 'tempo':
            track.append(MetaMessage('set_tempo', tempo=TEMPO, time=delta))
        elif kind == 'time':
            track.append(MetaMessage(
                'time_signature',
                numerator=4,
                denominator=4,
                clocks_per_click=24,
                notated_32nd_notes_per_beat=8,
                time=delta,
            ))
        elif kind == 'prog':
            track.append(Message('program_change', channel=CHANNEL, program=0, time=delta))
        elif kind == 'cc':
            track.append(Message('control_change', channel=CHANNEL, control=a, value=b, time=delta))
        else:
            raise RuntimeError(kind)
    track.append(MetaMessage('end_of_track', time=max(0, end_at - prev)))
    assert mid.ticks_per_beat == TPB
    mid.save(path)


def main():
    events.clear()
    for times in limb_times.values():
        times.clear()
    compose()
    validate(events)
    write_midi([(tick, note, vel) for tick, note, vel, _limb in events], 'solo.mid')


if __name__ == '__main__':
    main()
