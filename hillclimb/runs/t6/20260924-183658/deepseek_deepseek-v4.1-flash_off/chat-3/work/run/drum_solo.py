import random
import math
from mido import Message, MidiFile, MidiTrack, MetaMessage

# ---------------------------------------------------------------------------
# Deterministic RNG so every run produces the identical solo.mid
# ---------------------------------------------------------------------------
rng = random.Random(20240517)

# ---------------------------------------------------------------------------
# General MIDI percussion key map (channel 10)
# ---------------------------------------------------------------------------
KICK        = 36
SNARE       = 38
STICK       = 37
CLAP        = 39
SNARE_GHOST = 40
TOM_LO      = 45
TOM_MID     = 47
TOM_HI      = 50
HH_CLOSED   = 42
HH_PEDAL    = 44
HH_OPEN     = 46
CRASH       = 49
CRASH2      = 57
RIDE        = 51
RIDE_BELL   = 53
CHINA       = 52
SPLASH      = 55
CABASA      = 69
TAMB        = 54
COWBELL     = 56
TRI_MUTE    = 80
TRI_OPEN    = 81
WOODBLOCK_H = 76
WOODBLOCK_L = 77
CONGA_H     = 62
CONGA_L     = 63
SHAKER      = 70

PIANO = 0
STICKS = 1
BRUSH = 2
TRIANGLE = 3
TAIKO = 4
SYNTH = 5
CLAPPY = 6

TICKS_PER_BEAT = 480
TICKS_PER_BAR = TICKS_PER_BEAT * 4

# ---------------------------------------------------------------------------
# A note event with a human (non-quantized) placement in beats-from-start
# ---------------------------------------------------------------------------
class Hit:
    __slots__ = ("beat", "note", "vel", "dur", "ch")

    def __init__(self, beat, note, vel=100, dur=0.1, ch=9):
        self.beat = beat
        self.note = note
        self.vel = max(1, min(127, int(vel)))
        self.dur = dur
        self.ch = ch

# ---------------------------------------------------------------------------
# Human timing helpers
# ---------------------------------------------------------------------------
def jitter(amount=0.012):
    """Return a small random timing offset in beats."""
    return rng.gauss(0.0, amount)

def humanize(hits, amount=0.010):
    for h in hits:
        h.beat += jitter(amount)

# ---------------------------------------------------------------------------
# Voicing utilities — pick a drum voice for "singles traveling"
# ---------------------------------------------------------------------------
TOM_CYCLE = [SNARE, TOM_HI, TOM_MID, TOM_LO]

def accent(vel, amount=20):
    return vel + amount + int(rng.gauss(0, 4))

def ghost(vel, amount=18):
    return vel - amount - int(rng.gauss(0, 3))

# ---------------------------------------------------------------------------
# Core pattern generators — each returns list of Hit
# ---------------------------------------------------------------------------

def pattern_groove(bar, base_vel=98, ornament=0.0, hat="ride",
                   kick_extra=False, ride_ride=True):
    """A rock/fusion groove: kick, snare backbeat, ride/hat 8ths."""
    hits = []
    t0 = bar * 4.0
    hat_note = RIDE if hat == "ride" else HH_CLOSED
    # Ride or hi-hat eighths with a swung feel
    swing = 0.045  # swing the offbeat 8ths
    for i in range(8):
        beat = i * 0.5
        vel = base_vel - (12 if i % 2 else 0)
        if i % 2 == 1:
            beat += swing
        hits.append(Hit(t0 + beat, hat_note, accent(vel, 8), 0.08))
    # Snare backbeat on 2 and 4
    hits.append(Hit(t0 + 1.0, SNARE, accent(base_vel, 24), 0.05))
    hits.append(Hit(t0 + 3.0, SNARE, accent(base_vel, 26), 0.05))
    # Kick pattern
    hits.append(Hit(t0 + 0.0, KICK, accent(base_vel, 14), 0.08))
    hits.append(Hit(t0 + 2.5, KICK, accent(base_vel, 6), 0.08))
    if kick_extra:
        hits.append(Hit(t0 + 3.75, KICK, base_vel - 4, 0.08))
        hits.append(Hit(t0 + 1.75, KICK, base_vel - 2, 0.08))
    # Ornamental ghost snare
    if ornament > 0:
        n = int(ornament * 4)
        for _ in range(n):
            b = rng.uniform(0, 4)
            # avoid the backbeats
            if abs(b - 1.0) < 0.1 or abs(b - 3.0) < 0.1:
                continue
            hits.append(Hit(t0 + b, SNARE_GHOST, ghost(base_vel), 0.03))
    return hits


def pattern_ride_bell(bar, base_vel=100):
    hits = []
    t0 = bar * 4.0
    for i in range(8):
        beat = i * 0.5
        note = RIDE_BELL if i in (0, 3, 6) else RIDE
        vel = accent(base_vel, 10) if i in (0, 3, 6) else base_vel - 8
        hits.append(Hit(t0 + beat, note, vel, 0.08))
    hits.append(Hit(t0 + 1.0, SNARE, accent(base_vel, 20), 0.05))
    hits.append(Hit(t0 + 3.0, SNARE, accent(base_vel, 22), 0.05))
    hits.append(Hit(t0 + 0.0, KICK, accent(base_vel, 12), 0.08))
    hits.append(Hit(t0 + 2.75, KICK, base_vel - 4, 0.08))
    return hits


def pattern_halftime(bar, base_vel=104):
    hits = []
    t0 = bar * 4.0
    hits.append(Hit(t0 + 0.0, KICK, accent(base_vel, 12), 0.10))
    hits.append(Hit(t0 + 2.0, SNARE, accent(base_vel, 28), 0.06))
    hits.append(Hit(t0 + 2.0, CRASH, accent(base_vel, 10), 0.30))
    for i in range(4):
        hits.append(Hit(t0 + i * 1.0, HH_CLOSED, base_vel - 20, 0.08))
        if i in (1, 3):
            hits.append(Hit(t0 + i * 1.0 + 0.5, HH_CLOSED, base_vel - 30, 0.08))
    hits.append(Hit(t0 + 3.5, SNARE_GHOST, ghost(base_vel, 26), 0.03))
    hits.append(Hit(t0 + 3.75, SNARE_GHOST, ghost(base_vel, 20), 0.03))
    return hits


def pattern_buildup(bar, prog=0.0, base_vel=90):
    """March-like accumulating single strokes — crescendo in a phrase."""
    hits = []
    t0 = bar * 4.0
    count = 8
    for i in range(count):
        beat = i * 0.5
        vel = int(base_vel + prog * 22 + (i % 2) * 6 + rng.gauss(0, 3))
        note = SNARE if i % 2 == 0 else TOM_MID
        hits.append(Hit(t0 + beat, note, vel, 0.05))
    hits.append(Hit(t0 + 0.0, KICK, 90, 0.10))
    return hits


def fill_run(start_bar, length_bars, base_vel=96, direction="up",
             subdivision=0.25, strong_cycle=4, use_flams=False,
             add_kick=True):
    """A run of singles/doubles across toms and snare."""
    hits = []
    t0 = start_bar * 4.0
    total_steps = int(length_bars * 4 / subdivision)
    order = [SNARE, TOM_HI, TOM_MID, TOM_LO, SNARE_GHOST, TOM_LO, TOM_MID, TOM_HI]
    if direction == "down":
        order = order[::-1]
    for i in range(total_steps):
        beat = t0 + i * subdivision
        # Slight swing / human push
        beat += jitter(0.012)
        v = base_vel
        if i % strong_cycle == 0:
            v = accent(base_vel, 22)
        else:
            v += int(rng.gauss(0, 6))
        note = order[i % len(order)]
        if use_flams and i % strong_cycle == 0 and rng.random() < 0.4:
            hits.append(Hit(beat - 0.02, note, ghost(v, 28), 0.03))
        hits.append(Hit(beat, note, v, 0.05))
        if add_kick and strong_cycle and i % (strong_cycle * 2) == 0:
            hits.append(Hit(beat, KICK, accent(base_vel, 6), 0.08))
    return hits


def double_stroke_roll(start_bar, length_bars, note=SNARE, base_vel=88,
                       accel=True, steps_per_beat=4):
    """Buzz-like double-stroke run with velocity swell."""
    hits = []
    t0 = start_bar * 4.0
    total = int(length_bars * 4 * steps_per_beat)
    for i in range(total):
        beat = t0 + i / steps_per_beat
        base = base_vel + int(20 * math.sin(math.pi * i / max(1, total)))
        if i % 4 == 0:
            base = accent(base, 18)
        elif i % 4 == 2:
            base = accent(base, 8)
        base += int(rng.gauss(0, 4))
        hits.append(Hit(beat, note, base, 0.04))
    return hits


def roll_swell(start_bar, length_beats, from_vel=40, to_vel=118,
               steps_per_beat=4, note=SNARE, add_cymbal_at=None):
    hits = []
    t0 = start_bar * 4.0
    total = int(length_beats * steps_per_beat)
    for i in range(total):
        frac = i / max(1, total - 1)
        beat = t0 + i / steps_per_beat
        v = int(from_vel + (to_vel - from_vel) * frac)
        v += int(rng.gauss(0, 3))
        hits.append(Hit(beat, note, v, 0.04))
    if add_cymbal_at is not None:
        hits.append(Hit(t0 + length_beats, add_cymbal_at, 120, 0.6))
    return hits


def tom_melody(start_bar, notes, base_vel=100, subdivision=0.5, accents=None):
    """Play a little melodic figure on toms."""
    hits = []
    t0 = start_bar * 4.0
    for i, n in enumerate(notes):
        beat = t0 + i * subdivision
        v = base_vel
        if accents and i in accents:
            v = accent(base_vel, 22)
        hits.append(Hit(beat, n, v, 0.06))
    return hits

# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def section_intro():
    """Sparse, atmospheric opening. Establishes motif A."""
    hits = []
    hits.append(Hit(0.0, CRASH, 96, 0.9))
    hits.append(Hit(0.0, KICK, 100, 0.12))
    # Motif A: kick-snare-kick-kick figure in a slow half-time field
    hits.append(Hit(1.5, SNARE_GHOST, 40, 0.05))
    hits.append(Hit(2.0, SNARE, 88, 0.08))
    hits.append(Hit(2.5, KICK, 84, 0.10))
    hits.append(Hit(3.0, SNARE_GHOST, 44, 0.05))
    hits.append(Hit(3.5, SNARE_GHOST, 52, 0.05))
    hits.append(Hit(4.0, TOM_LO, 90, 0.10))
    hits.append(Hit(4.5, TOM_MID, 86, 0.10))
    hits.append(Hit(5.0, TOM_HI, 92, 0.10))
    hits.append(Hit(5.5, SNARE, 100, 0.08))
    hits.append(Hit(6.0, KICK, 100, 0.10))
    hits.append(Hit(6.75, SNARE_GHOST, 46, 0.04))
    hits.append(Hit(7.0, SNARE, 104, 0.08))
    hits.append(Hit(7.5, CRASH2, 100, 0.7))
    hits.append(Hit(8.0, CRASH2, 102, 0.7))
    hits.append(Hit(8.0, KICK, 104, 0.12))
    # Gentle triplet roll into the next section
    for i in range(12):
        beat = 10.0 + i * (2.0 / 12)
        v = 48 + i * 4 + int(rng.gauss(0, 3))
        hits.append(Hit(beat, SNARE, v, 0.03))
    hits.append(Hit(12.0, KICK, 106, 0.12))
    hits.append(Hit(12.0, CRASH, 108, 0.9))
    hits.append(Hit(12.0, RIDE_BELL, 100, 0.2))
    return hits


def section_main_A():
    """Groove, forward motion, Motif A at tempo. Tension held."""
    hits = []
    hits += pattern_groove(3, base_vel=100, ornament=1.5, kick_extra=True)
    hits += pattern_groove(4, base_vel=98, ornament=0.6)
    hits += pattern_ride_bell(5, base_vel=102)
    hits += pattern_groove(6, base_vel=104, ornament=2.0, kick_extra=True)
    # Bar 7: break into a quick tag with tom voice
    hits += tom_melody(7, [SNARE, SNARE_GHOST, SNARE, TOM_HI, TOM_MID, SNARE,
                           SNARE_GHOST, SNARE], base_vel=100, subdivision=0.5,
                       accents={0, 3})
    hits.append(Hit(7.0, KICK, accent(100, 8), 0.10))
    hits.append(Hit(7.5, KICK, 84, 0.10))
    hits.append(Hit(8.0, CRASH, 112, 0.9))
    return hits


def section_fill_1():
    """First big fill: singles and doubles traveling down and back."""
    hits = []
    hits += fill_run(8, 1.0, base_vel=100, direction="down",
                     subdivision=0.25, strong_cycle=4, use_flams=True,
                     add_kick=False)
    hits.append(Hit(8.0, KICK, accent(100, 12), 0.10))
    hits.append(Hit(8.5, KICK, 90, 0.10))
    hits += fill_run(9, 1.0, base_vel=104, direction="up",
                     subdivision=0.125, strong_cycle=4, use_flams=False,
                     add_kick=False)
    hits.append(Hit(9.0, KICK, accent(104, 10), 0.10))
    hits.append(Hit(9.0, HH_PEDAL, 70, 0.05))
    hits.append(Hit(9.75, KICK, accent(100, 6), 0.10))
    # Bar 10: tom melody with accents
    hits += tom_melody(10, [TOM_LO, TOM_LO, TOM_MID, TOM_MID, TOM_HI, TOM_HI,
                            SNARE, SNARE], base_vel=102, subdivision=0.5,
                       accents={0, 2, 4, 6})
    hits.append(Hit(10.0, KICK, 104, 0.10))
    hits.append(Hit(11.0, KICK, 100, 0.10))
    hits.append(Hit(11.5, SNARE, 78, 0.05))
    hits.append(Hit(11.75, SNARE, 82, 0.05))
    return hits


def section_break_A():
    """Motif A returns: the K S K K figure, but more syncopated, ghost-y."""
    hits = []
    t0 = 12.0
    # Bar 12: state Motif A at full intensity
    hits.append(Hit(t0 + 0.0, CRASH, 108, 0.8))
    hits.append(Hit(t0 + 0.0, KICK, accent(104, 12), 0.12))
    hits.append(Hit(t0 + 0.5, SNARE_GHOST, ghost(100, 28), 0.03))
    hits.append(Hit(t0 + 1.5, SNARE, accent(100, 26), 0.06))
    hits.append(Hit(t0 + 1.75, SNARE_GHOST, ghost(100, 34), 0.03))
    hits.append(Hit(t0 + 2.0, KICK, accent(104, 10), 0.10))
    hits.append(Hit(t0 + 2.75, KICK, 90, 0.10))
    hits.append(Hit(t0 + 3.0, SNARE, accent(100, 26), 0.06))
    hits.append(Hit(t0 + 3.5, SNARE_GHOST, ghost(100, 26), 0.03))
    hits.append(Hit(t0 + 3.75, SNARE_GHOST, ghost(100, 34), 0.03))
    # Bar 13: ride-driven
    hits += [Hit(13.0 + i * 0.5, RIDE if i % 2 else RIDE_BELL,
                 96 + (i % 4) * 4 + int(rng.gauss(0, 3)), 0.08)
             for i in range(8)]
    hits.append(Hit(13.0, KICK, 104, 0.10))
    hits.append(Hit(13.5, SNARE_GHOST, ghost(96, 24), 0.03))
    hits.append(Hit(14.0, SNARE, accent(100, 24), 0.06))
    hits.append(Hit(14.5, KICK, 92, 0.10))
    hits.append(Hit(15.0, SNARE, accent(100, 24), 0.06))
    # Bar 14: Motif A on toms
    hits += tom_melody(14, [TOM_LO, TOM_MID, TOM_HI, SNARE, SNARE,
                            TOM_HI, TOM_MID, TOM_LO], base_vel=102,
                       subdivision=0.5, accents={0, 3})
    hits.append(Hit(14.0, KICK, 106, 0.10))
    hits.append(Hit(14.75, KICK, 90, 0.10))
    # Bar 15: accelerating build into a crash
    for i in range(8):
        beat = 15.0 + i * 0.5
        v = 80 + i * 5 + int(rng.gauss(0, 4))
        note = SNARE if i % 2 == 0 else TOM_MID
        hits.append(Hit(beat, note, v, 0.05))
    hits.append(Hit(15.0, KICK, accent(100, 6), 0.10))
    hits.append(Hit(15.5, KICK, 96, 0.10))
    hits.append(Hit(16.0, CRASH, 118, 1.0))
    hits.append(Hit(16.0, KICK, 118, 0.14))
    return hits


def section_main_B():
    """A new phrase: syncopated funk-rock. Density contrast."""
    hits = []
    # Bar 16: displaced backbeat
    hits += [Hit(16.0 + i * 0.25,
                 [KICK, HH_CLOSED, SNARE_GHOST, HH_CLOSED,
                  KICK, KICK, HH_CLOSED, SNARE_GHOST,
                  SNARE, HH_CLOSED, KICK, HH_CLOSED,
                  SNARE_GHOST, HH_CLOSED, KICK, HH_CLOSED][i],
                 90 + (i % 4) * 8 + int(rng.gauss(0, 4)), 0.05)
             for i in range(16)]
    hits.append(Hit(16.0, CRASH, 104, 0.6))
    # Bar 17: linear drumming — no two limbs at once sometimes
    hits += tom_melody(17, [KICK, SNARE, TOM_HI, KICK, SNARE, TOM_MID,
                            KICK, SNARE], base_vel=98, subdivision=0.5,
                       accents={0, 3})
    hits.append(Hit(17.5, SNARE_GHOST, ghost(96, 28), 0.03))
    hits.append(Hit(17.75, SNARE_GHOST, ghost(96, 30), 0.03))
    # Bar 18: ride driven with doubled kick
    hits += pattern_ride_bell(18, base_vel=104)
    hits.append(Hit(18.5, KICK, 98, 0.10))
    hits.append(Hit(18.75, KICK, 92, 0.10))
    # Bar 19: contrasting low tom groove
    hits.append(Hit(19.0, KICK, 110, 0.12))
    hits.append(Hit(19.0, CRASH2, 100, 0.6))
    for i in range(8):
        hits.append(Hit(19.0 + 0.25 + i * 0.5, TOM_LO,
                        88 + (i % 2) * 10 + int(rng.gauss(0, 4)), 0.06))
    hits.append(Hit(19.0 + 0.5, SNARE, accent(100, 22), 0.06))
    hits.append(Hit(19.0 + 2.5, SNARE, accent(100, 22), 0.06))
    return hits


def section_roll_and_release():
    """The big roll: swells, then resolves to a downbeat. Release."""
    hits = []
    # Bar 20: build
    hits += roll_swell(20, 4.0, from_vel=44, to_vel=112, steps_per_beat=4,
                       note=SNARE, add_cymbal_at=None)
    hits.append(Hit(20.0, KICK, 100, 0.10))
    hits.append(Hit(20.0, HH_PEDAL, 76, 0.05))
    # Bar 21: even more intense, longer notes, buzz
    hits += double_stroke_roll(21, 1.0, note=SNARE, base_vel=100,
                               steps_per_beat=4, accel=True)
    hits += fill_run(22, 1.0, base_vel=104, direction="down",
                     subdivision=0.125, strong_cycle=4, use_flams=False,
                     add_kick=False)
    hits.append(Hit(22.0, KICK, accent(104, 10), 0.10))
    hits.append(Hit(22.0, RIDE_BELL, 96, 0.15))
    hits.append(Hit(22.5, SNARE_GHOST, ghost(104, 26), 0.03))
    # Bar 23: giant crescendo on toms into the climax
    for i in range(16):
        beat = 23.0 + i * 0.25
        v = 78 + int(i * 2.5) + int(rng.gauss(0, 3))
        note = TOM_CYCLE[i % 4]
        hits.append(Hit(beat, note, v, 0.05))
        if i in (0, 8, 12, 15):
            hits.append(Hit(beat, KICK, accent(v, 8), 0.08))
    # The release: crash + downbeat into the final scene
    hits.append(Hit(24.0, CRASH, 126, 1.2))
    hits.append(Hit(24.0, KICK, 122, 0.14))
    hits.append(Hit(24.0, SNARE, 118, 0.06))
    return hits


def section_finale():
    """The last statement: Motif A acknowledged, then a virtuoso close."""
    hits = []
    # Bar 24: Motif A restated assertively
    hits.append(Hit(24.0, KICK, 120, 0.12))
    hits.append(Hit(24.0, CRASH, 116, 0.9))
    hits.append(Hit(24.5, SNARE_GHOST, ghost(112, 24), 0.03))
    hits.append(Hit(24.75, SNARE_GHOST, ghost(112, 22), 0.03))
    hits.append(Hit(25.0, SNARE, accent(112, 22), 0.06))
    hits.append(Hit(25.5, KICK, 106, 0.10))
    hits.append(Hit(25.75, KICK, 96, 0.10))
    hits.append(Hit(26.0, SNARE, accent(112, 22), 0.06))
    # Bar 25: singles traveling around the kit
    hits += fill_run(25, 1.0, base_vel=108, direction="down",
                     subdivision=0.25, strong_cycle=3, use_flams=False,
                     add_kick=False)
    hits.append(Hit(25.0, KICK, 112, 0.10))
    hits.append(Hit(26.0, KICK, 108, 0.10))
    hits.append(Hit(26.75, KICK, 100, 0.10))
    # Bar 26: alternating hand/foot pattern — very drummery
    hits += [Hit(26.0 + i * 0.25,
                 [SNARE, KICK, SNARE_GHOST, KICK,
                  TOM_HI, KICK, TOM_MID, KICK,
                  SNARE, KICK, SNARE_GHOST, KICK,
                  TOM_LO, KICK, TOM_LO, KICK][i],
                 100 + (i % 3) * 8 + int(rng.gauss(0, 4)), 0.05)
             for i in range(16)]
    hits.append(Hit(26.0, CRASH2, 102, 0.6))
    # Bar 27: last expressive tom figure, slowing slightly
    notes = [TOM_HI, TOM_HI, TOM_MID, TOM_MID, TOM_LO, TOM_LO, SNARE, SNARE,
             TOM_LO, TOM_MID, TOM_HI, SNARE, SNARE, SNARE_GHOST, SNARE,
             SNARE_GHOST]
    for i, n in enumerate(notes):
        beat = 27.0 + i * 0.25
        # slow down at the end
        if i > 10:
            beat += (i - 10) * 0.02
        v = 104 - (i // 4) * 4 + (10 if i % 4 == 0 else 0)
        v += int(rng.gauss(0, 4))
        hits.append(Hit(beat, n, v, 0.05))
    hits.append(Hit(27.0, KICK, 112, 0.12))
    hits.append(Hit(27.5, KICK, 100, 0.10))
    # Final crash — hit and hold
    hits.append(Hit(28.0, CRASH, 127, 1.6))
    hits.append(Hit(28.0, CRASH2, 110, 1.4))
    hits.append(Hit(28.0, KICK, 124, 0.16))
    hits.append(Hit(28.0, SNARE, 120, 0.08))
    hits.append(Hit(28.0, TOM_LO, 108, 0.20))
    # A little tick on the ride for ping after the crash
    hits.append(Hit(28.25, RIDE_BELL, 90, 0.10))
    return hits


def section_color_interlude():
    """Color from the rest of the GM percussion set, lightly."""
    hits = []
    t0 = 28.0
    hits.append(Hit(t0 + 0.5, CABASA, 70, 0.05))
    hits.append(Hit(t0 + 1.0, CABASA, 62, 0.05))
    hits.append(Hit(t0 + 1.5, TRI_OPEN, 80, 0.30))
    hits.append(Hit(t0 + 2.0, TRI_MUTE, 60, 0.10))
    hits.append(Hit(t0 + 2.25, COWBELL, 68, 0.08))
    hits.append(Hit(t0 + 3.0, TAMB, 72, 0.20))
    hits.append(Hit(t0 + 3.5, SHAKER, 58, 0.05))
    return hits


# ---------------------------------------------------------------------------
# Build the whole solo, then pad to ~two minutes
# ---------------------------------------------------------------------------

def build_solo():
    hits = []
    hits += section_intro()                 # 0 - 12
    hits += section_main_A()                # 12 - 16
    hits += section_fill_1()                # 16 - 20
    hits += section_break_A()               # 20 - 28 (wait, let's use bars carefully)
    # NOTE: I laid sections in bar numbers above; let me be careful.
    # Recompute explicitly by bar positions:

    # Because I use absolute bar numbers above, I should just build linearly
    # by calling each section with no ambiguity. Review:

    # section_intro:    beats 0..12     (bars 0-2, ending crash at 12)
    # section_main_A:   bars 3..7 -> beats 12..32
    # section_fill_1:   bars 8..11 -> beats 32..48
    # section_break_A:  bars 12..15 -> beats 48..64
    # section_main_B:   bars 16..19 -> beats 64..80
    # section_roll_and_release: bars 20..23 -> beats 80..96
    # section_finale:   bars 24..28 -> beats 96..112
    # section_color_interlude: bars 28..29 -> beats 112..116

    # All fine. Let me just collect.
    hits = []
    hits += section_intro()               # 0..12
    hits += section_main_A()              # 12..32
    hits += section_fill_1()              # 32..48
    hits += section_break_A()             # 48..64
    hits += section_main_B()              # 64..80
    hits += section_roll_and_release()    # 80..96
    hits += section_finale()              # 96..112
    hits += section_color_interlude()     # 112..116

    # Add a few extra sparkle hits and human touches
    for i in range(6):
        b = rng.uniform(0, 116)
        if rng.random() < 0.5:
            hits.append(Hit(b, HH_PEDAL, 66 + int(rng.gauss(0, 5)), 0.05))
        else:
            hits.append(Hit(b, SNARE_GHOST, ghost(94, 28), 0.03))
    for i in range(8):
        b = 60 + i * 7 + rng.uniform(-1, 1)
        hits.append(Hit(b, RIDE_BELL, 80 + int(rng.gauss(0, 6)), 0.08))

    # Humanize everything a little, but preserve relative placement
    humanize(hits, amount=0.010)

    return hits

# ---------------------------------------------------------------------------
# Render to MIDI
# ---------------------------------------------------------------------------

def render(hits, filename="solo.mid"):
    # Convert beats to ticks, and handle simultaneous notes on channel 9.
    # Sort by beat then note.
    for h in hits:
        h.beat = max(0.0, h.beat)
    hits.sort(key=lambda h: (h.beat, h.note))

    # Build message list: (tick, order_key, message)
    events = []
    for h in hits:
        start = int(round(h.beat * TICKS_PER_BEAT))
        end = start + max(1, int(round(h.dur * TICKS_PER_BEAT)))
        events.append((start, 0, Message("note_on", channel=h.ch,
                                         note=h.note, velocity=h.vel)))
        events.append((end, 1, Message("note_off", channel=h.ch,
                                       note=h.note, velocity=0)))

    # Stable sort: note_offs before note_ons at the same tick to avoid cut.
    events.sort(key=lambda e: (e[0], e[1]))

    mid = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    mid.tracks.append(track)

    # Tempo: around 132 BPM, with a detectable human "push and pull" by
    # inserting subtle tempo variations at natural section boundaries.
    base_bpm = 132
    microseconds = int(60_000_000 / base_bpm)
    track.append(MetaMessage("set_tempo", tempo=microseconds, time=0))
    track.append(MetaMessage("time_signature", numerator=4, denominator=4,
                             time=0))

    # Tempo variation table (in beats): (beat, relative multiplier)
    # <1.0 faster, >1.0 slower.
    tempo_points = [
        (0.0,  1.00),
        (12.0, 1.00),
        (31.9, 0.99),   # push before big fill
        (32.0, 1.00),
        (47.9, 0.985),
        (48.0, 1.00),
        (63.9, 0.99),
        (64.0, 1.00),
        (79.9, 0.975),  # pull back before huge roll
        (80.0, 1.00),
        (88.0, 0.99),   # push during roll
        (96.0, 1.02),   # sit back for finale
        (108.0, 1.04),  # ritardando at the last figure
        (116.0, 1.06),
    ]

    cur_tick = 0
    last_beat = 0.0
    # We'll insert tempo change metas as we emit events.
    pending_tempo = list(tempo_points)
    tempo_tick = 0

    # Instead of merging tempo metas into the event stream, build a complete
    # (tick, priority, msg) list including tempo changes, then emit as deltas.
    all_events = list(events)
    for i, (b, mult) in enumerate(tempo_points):
        t = int(round(b * TICKS_PER_BEAT))
        usec = int(microseconds * mult)
        all_events.append((t, -1, MetaMessage("set_tempo", tempo=usec)))

    all_events.sort(key=lambda e: (e[0], e[1], _tiebreak(e[2])))

    prev = 0
    for tick, _, msg in all_events:
        delta = max(0, tick - prev)
        msg.time = delta
        track.append(msg)
        prev = tick

    # End of track
    end = MetaMessage("end_of_track", time=0)
    track.append(end)

    mid.save(filename)


def _tiebreak(msg):
    """Return a sort key so messages at the same tick are emitted sensibly."""
    if msg.type == "set_tempo":
        return (-2, 0)
    if msg.type == "note_off":
        return (0, msg.note)
    if msg.type == "note_on":
        return (1, msg.note)
    return (2, 0)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    hits = build_solo()
    # Pad to at least ~2 minutes (120s @ 132 BPM = 264 beats) if needed
    total_beats = max((h.beat for h in hits), default=0.0)
    # We already span ~120 beats. Two minutes is 264 beats at 132 BPM? No:
    # 2 min at 132 BPM = 264 beats. We only have ~120 beats -> ~55 seconds.
    # So extend: repeat the map for a second pass with variations.
    # To keep the "once through" feel, and given the sections are dense and
    # two minutes is a long solo, we add a middle development pass.

    solo = build_solo()

    # The above build is ~120 beats = ~54s. To reach ~2 min we insert a
    # development section between break_A and main_B (around beat 64).

    # Actually easier: build a longer linear plan from scratch:
    hits = []

    hits += section_intro()               # 0..12
    hits += section_main_A()              # 12..32
    hits += section_fill_1()              # 32..48
    hits += section_break_A()             # 48..64

    # Development section: same motifs, higher intensity, variation
    # 64..104
    hits += pattern_groove(16, base_vel=104, ornament=2.5, kick_extra=True)
    hits += pattern_ride_bell(17, base_vel=106)
    hits += fill_run(18, 1.0, base_vel=106, direction="down",
                     subdivision=0.25, strong_cycle=3, use_flams=True,
                     add_kick=False)
    hits.append(Hit(18.0, KICK, 112, 0.10))
    hits.append(Hit(18.75, KICK, 100, 0.10))
    hits += fill_run(19, 1.0, base_vel=108, direction="up",
                     subdivision=0.125, strong_cycle=4, use_flams=False,
                     add_kick=False)
    hits.append(Hit(19.0, KICK, 110, 0.10))
    hits.append(Hit(19.5, KICK, 104, 0.10))
    hits.append(Hit(20.0, CRASH, 116, 0.9))

    hits += pattern_groove(20, base_vel=102, ornament=2.0, kick_extra=True)
    hits += pattern_halftime(21, base_vel=108)  # contrasts, half-time
    hits += pattern_groove(22, base_vel=106, ornament=3.0, kick_extra=True)
    hits += pattern_ride_bell(23, base_vel=108)
    hits.append(Hit(23.0, SNARE, accent(108, 24), 0.06))
    hits.append(Hit(23.5, SNARE, accent(108, 26), 0.06))
    hits.append(Hit(24.0, CRASH, 116, 0.9))
    hits.append(Hit(24.0, KICK, 118, 0.12))

    # Motif A on toms — a real drum-set melody
    hits += tom_melody(24, [TOM_LO, TOM_LO, TOM_MID, SNARE,
                            TOM_HI, TOM_HI, TOM_MID, SNARE,
                            TOM_LO, TOM_LO, TOM_MID, SNARE,
                            TOM_HI, SNARE, TOM_MID, TOM_LO],
                       base_vel=104, subdivision=0.5,
                       accents={0, 4, 8, 12})
    hits.append(Hit(24.0, KICK, 112, 0.10))
    hits.append(Hit(25.0, KICK, 108, 0.10))
    hits.append(Hit(26.0, KICK, 106, 0.10))
    hits.append(Hit(27.0, KICK, 104, 0.10))

    hits += fill_run(28, 1.0, base_vel=110, direction="down",
                     subdivision=0.125, strong_cycle=3, use_flams=False,
                     add_kick=False)
    hits.append(Hit(28.0, KICK, 112, 0.10))
    hits.append(Hit(28.5, KICK, 104, 0.10))
    # roll into a crash
    hits += roll_swell(29, 4.0, from_vel=50, to_vel=116,
                       steps_per_beat=4, note=SNARE, add_cymbal_at=CRASH)
    hits.append(Hit(29.0, KICK, 108, 0.10))
    hits.append(Hit(33.0, KICK, 118, 0.14))
    hits.append(Hit(33.0, CRASH, 122, 1.0))

    # Build the climax
    hits += section_main_B()              # 16..20 -> but we are at 33
    # Wait, section_main_B has hard-coded bar 16+ — need to offset. Simpler:
    # let's not reuse sections with absolute bar numbers. Build linearly.

    # I'll rebuild the rest cleanly.
    hits = []
    hits += section_intro()               # 0..12

    # 12..48 : main A + fill (as before)
    hits += section_main_A()              # 12..32
    hits += section_fill_1()              # 32..48

    # 48..64 : break_A (Motif A with toms)
    hits += section_break_A()             # 48..64

    # 64..96 : big development
    dev_hits = []
    dev_hits += pattern_groove(16, base_vel=104, ornament=2.5, kick_extra=True)
    dev_hits += pattern_ride_bell(17, base_vel=106)
    dev_hits += fill_run(18, 1.0, base_vel=106, direction="down",
                         subdivision=0.25, strong_cycle=3, use_flams=True,
                         add_kick=False)
    dev_hits.append(Hit(18.0, KICK, 112, 0.10))
    dev_hits.append(Hit(18.75, KICK, 100, 0.10))
    dev_hits += fill_run(19, 1.0, base_vel=108, direction="up",
                         subdivision=0.125, strong_cycle=4, use_flams=False,
                         add_kick=False)
    dev_hits.append(Hit(19.0, KICK, 110, 0.10))
    dev_hits.append(Hit(19.5, KICK, 104, 0.10))
    dev_hits.append(Hit(20.0, CRASH, 116, 0.9))

    dev_hits += tom_melody(20, [TOM_LO, TOM_MID, TOM_HI, SNARE,
                                TOM_LO, TOM_MID, TOM_HI, SNARE,
                                TOM_LO, TOM_MID, TOM_HI, SNARE,
                                TOM_HI, TOM_MID, TOM_LO, SNARE],
                           base_vel=104, subdivision=0.5,
                           accents={0, 2, 4, 6, 8, 10, 12})
    dev_hits.append(Hit(20.0, KICK, 112, 0.10))
    dev_hits.append(Hit(21.0, KICK, 108, 0.10))
    dev_hits.append(Hit(22.0, KICK, 106, 0.10))
    dev_hits.append(Hit(23.0, KICK, 104, 0.10))

    dev_hits += fill_run(24, 1.0, base_vel=110, direction="down",
                         subdivision=0.125, strong_cycle=3, use_flams=False,
                         add_kick=False)
    dev_hits.append(Hit(24.0, KICK, 112, 0.10))
    dev_hits.append(Hit(24.5, KICK, 104, 0.10))
    dev_hits += roll_swell(25, 4.0, from_vel=46, to_vel=118,
                           steps_per_beat=4, note=SNARE, add_cymbal_at=CRASH)
    dev_hits.append(Hit(25.0, KICK, 108, 0.10))
    dev_hits.append(Hit(29.0, KICK, 118, 0.14))
    dev_hits.append(Hit(29.0, CRASH, 122, 1.0))

    for h in dev_hits:
        h.beat += 64.0
    hits += dev_hits

    # 96..128: climax roll, finale
    tail = section_roll_and_release()
    for h in tail:
        h.beat += 64.0  # section_roll_and_release is 80..96, shift by 32
    # Hmm, that would put it at 144. Let me recompute.

    # section_roll_and_release has bars 20..24 -> beats 80..96.
    # We want it at 96..112, so shift by 16.
    tail = section_roll_and_release()
    for h in tail:
        h.beat += 16.0
    hits += tail

    # section_finale has bars 24..29 -> beats 96..116; shift to 112..132
    fin = section_finale()
    for h in fin:
        h.beat += 16.0
    hits += fin

    # section_color_interlude at 112..116 -> shift to 128..132 (interlude
    # after finale? no—put before finale). Let's just place it at 132 as a
    # quiet postlude. Actually the task says end with a hit, so skip or
    # move before the finale.

    # Place color interlude as a quiet bridge between development and
    # the giant roll: 92..96.
    color = section_color_interlude()
    for h in color:
        h.beat += 64.0  # 28 -> 92... hmm section_color uses bars ~28 = beat 112
    # Let's not bother—cut the color interlude and just put the sparkles.

    # Final time check:
    total_beats = max((h.beat for h in hits), default=0.0)
    # If less than ~240 beats (about 2 min at 132), pad with a coda.
    # 2 min at 132 BPM = 264 beats. We may be around 148 -> ~67 seconds.
    # Add a second, extended development pass.

    # Extend: add another chorus-like section from 132
    ext = []
    ext += pattern_groove(0, base_vel=106, ornament=2.5, kick_extra=True)
    ext += pattern_ride_bell(1, base_vel=108)
    ext += pattern_halftime(2, base_vel=110)
    ext += pattern_groove(3, base_vel=108, ornament=3.0, kick_extra=True)
    ext += tom_melody(4, [SNARE, TOM_HI, TOM_MID, TOM_LO,
                          SNARE, TOM_HI, TOM_MID, TOM_LO,
                          SNARE, TOM_HI, TOM_MID, TOM_LO,
                          TOM_LO, TOM_MID, TOM_HI, SNARE],
                      base_vel=106, subdivision=0.5,
                      accents={0, 4, 8, 12})
    ext.append(Hit(4.0, KICK, 110, 0.10))
    ext.append(Hit(5.0, KICK, 108, 0.10))
    ext.append(Hit(6.0, KICK, 106, 0.10))
    ext.append(Hit(7.0, KICK, 104, 0.10))
    ext += fill_run(8, 1.0, base_vel=110, direction="down",
                    subdivision=0.125, strong_cycle=3, use_flams=False,
                    add_kick=False)
    ext.append(Hit(8.0, KICK, 114, 0.10))
    ext.append(Hit(8.5, KICK, 108, 0.10))
    ext += roll_swell(9, 4.0, from_vel=44, to_vel=120,
                      steps_per_beat=4, note=SNARE, add_cymbal_at=CRASH)
    ext.append(Hit(9.0, KICK, 108, 0.10))
    ext.append(Hit(13.0, KICK, 122, 0.14))
    ext.append(Hit(13.0, CRASH, 124, 1.0))

    # Extend roll / finale: an even bigger climax
    ext += double_stroke_roll(13, 1.0, note=SNARE, base_vel=104,
                              steps_per_beat=4, accel=True)
    ext += fill_run(14, 1.0, base_vel=110, direction="up",
                    subdivision=0.125, strong_cycle=4, use_flams=False,
                    add_kick=False)
    ext.append(Hit(14.0, KICK, 114, 0.10))
    ext.append(Hit(15.0, KICK, 110, 0.10))
    # giant final build
    for i in range(16):
        beat = 15.0 + i * 0.25
        v = 80 + int(i * 2.6) + int(rng.gauss(0, 3))
        note = TOM_CYCLE[i % 4]
        ext.append(Hit(beat, note, v, 0.05))
        if i in (0, 8, 12, 15):
            ext.append(Hit(beat, KICK, accent(v, 8), 0.08))

    for h in ext:
        h.beat += 132.0
    hits += ext

    # final crash
    hits.append(Hit(148.0, CRASH, 127, 1.6))
    hits.append(Hit(148.0, CRASH2, 112, 1.4))
    hits.append(Hit(148.0, KICK, 126, 0.16))
    hits.append(Hit(148.0, SNARE, 122, 0.08))
    hits.append(Hit(148.0, TOM_LO, 110, 0.20))
    hits.append(Hit(148.25, RIDE_BELL, 92, 0.10))
    hits.append(Hit(149.0, HH_PEDAL, 78, 0.05))

    # Add subtle color hits sprinkled around (sparingly)
    for i in range(14):
        b = rng.uniform(0, 148)
        if rng.random() < 0.5:
            hits.append(Hit(b, CABASA, 62 + int(rng.gauss(0, 5)), 0.05))
        else:
            hits.append(Hit(b, TAMB, 58 + int(rng.gauss(0, 5)), 0.10))

    # Humanize slightly once more
    humanize(hits, amount=0.009)

    # Limit to 2 hands + 2 feet: at most 4 simultaneous strikes.
    # Enforce by detecting near-simultaneous events and pruning extras.
    hits = prune_simultaneous(hits)

    render(hits, "solo.mid")


def prune_simultaneous(hits, window=0.035, max_simultaneous=4):
    """Keep at most `max_simultaneous` hits within a small time window.

    Prioritize: kicks and snare accents first, then toms, then hats/cymbals,
    then ghost notes. This mimics a drummer's limb budget.
    """
    priority = {
        KICK: 10, SNARE: 9, TOM_LO: 7, TOM_MID: 7, TOM_HI: 7,
        CRASH: 6, CRASH2: 6, RIDE: 5, RIDE_BELL: 5, HH_CLOSED: 4,
        HH_OPEN: 4, HH_PEDAL: 3, SNARE_GHOST: 1,
        CHINA: 5, SPLASH: 5, CABASA: 2, TAMB: 2,
        TRI_MUTE: 2, TRI_OPEN: 2, COWBELL: 2,
        WOODBLOCK_H: 2, WOODBLOCK_L: 2, CONGA_H: 4, CONGA_L: 4,
        SHAKER: 1,
    }
    hits = sorted(hits, key=lambda h: (h.beat, -priority.get(h.note, 0),
                                       -h.vel))
    result = []
    # Use a simple sliding window over the sorted list.
    i = 0
    n = len(hits)
    while i < n:
        h = hits[i]
        # gather all within `window` beats after h
        j = i
        cluster = []
        while j < n and hits[j].beat - h.beat <= window:
            cluster.append(hits[j])
            j += 1
        # sort by priority desc, vel desc
        cluster.sort(key=lambda x: (-priority.get(x.note, 0), -x.vel))
        chosen = cluster[:max_simultaneous]
        result.extend(chosen)
        i = j
    return result


if __name__ == "__main__":
    main()
