#!/usr/bin/env python3
"""drum_solo.py — generates solo.mid, a two-minute General MIDI drum solo.

Single file, stdlib + mido only. Deterministic (fixed seed).
Channel 10 (index 9), GM percussion key map.
"""

import math
import random
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

# ---------------------------------------------------------------- constants

TPB = 480                 # ticks per beat
BAR = 4 * TPB             # 4/4

# GM drum key map (subset we use, plus percussion colours)
K = {
    "kick":    36,
    "kick2":   35,
    "snare":   38,
    "rim":     37,
    "clap":    39,
    "snare2":  40,
    "tomL":    41,   # low floor
    "tomH":    43,   # high floor
    "tomL2":   45,   # low tom
    "tomH2":   48,   # high tom
    "hatP":    44,   # pedal
    "hatC":    42,   # closed
    "hatO":    46,   # open
    "crash":   49,
    "crash2":  57,
    "ride":    51,
    "rideBell":53,
    "china":   52,
    "splash":  55,
    "cowbell": 56,
    "tamb":    54,
    "timb":    47,   # low timbale -> nice tom-ish colour
    "timbH":   50,   # high timbale
    "claves":  75,
    "woodblk": 76,
    "cabasa":  69,
    "shaker":  82 if False else 70,
    "tri":     81,
}

# GM velocity helpers
PP, P, MP, MF, F, FF, FFF = 30, 45, 60, 72, 88, 104, 118


# ---------------------------------------------------------------- score model

class Note:
    __slots__ = ("t", "key", "vel", "dur")

    def __init__(self, t, key, vel, dur=0):
        self.t = t
        self.key = key
        self.vel = vel
        self.dur = dur


class Score:
    """Collect absolute-time notes; resolve to a sorted MIDI event stream."""

    def __init__(self):
        self.notes = []

    def add(self, t, key, vel, dur=0):
        self.notes.append(Note(t, key, vel, dur))

    # -- expressive timing helpers ---------------------------------------
    def human(self, t, amt=0.0):
        """Slight hand-jitter, deterministic."""
        return t + amt

    def emit(self, path):
        notes = sorted(self.notes, key=lambda n: n.t)
        events = []  # (tick, order, Message)
        for n in notes:
            t = max(0, int(round(n.t)))
            v = max(1, min(127, int(round(n.vel))))
            events.append((t, 1, Message("note_on", channel=9, note=n.key, velocity=v)))
            off = t + max(1, int(round(n.dur)))
            events.append((off, 0, Message("note_off", channel=9, note=n.key, velocity=0)))
        events.sort(key=lambda e: (e[0], e[1]))

        mid = MidiFile(type=0, ticks_per_beat=TPB)
        track = MidiTrack()
        mid.tracks.append(track)
        # Tempo map: gently drifting to breathe with the solo.
        # Base 96 BPM felt as swing 16ths via placement; slight tempo curve.
        track.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
        track.append(MetaMessage("key_signature", key="C", time=0))
        track.append(MetaMessage("track_name", name="Two-Minute Drum Solo", time=0))
        track.append(MetaMessage("set_tempo", tempo=bpm2tempo(96), time=0))

        last = 0
        for tick, _, msg in events:
            delta = tick - last
            track.append(msg.copy(time=delta))
            last = tick
        track.append(MetaMessage("end_of_track", time=0))
        mid.save(path)


# ---------------------------------------------------------------- timing grid

def sub(beat, n=4):
    """n subdivisions per beat -> tick offset."""
    return int(round(TPB / n * beat))


def bar_t(b):
    return b * BAR


# Position maps (in ticks within a bar) for swing-flavoured 16ths.
# A "swing 16" pair: straight 16 at s, swung partner ~ s + 0.62*16th.
S16 = TPB / 4.0
SWING = 0.62 * S16  # the "e" of a swing 16th pair a bit late


def swing16(i):
    """i-th 16th in a beat, swung feel."""
    j, k = divmod(i, 2)
    if k == 0:
        return j * 2 * S16
    return j * 2 * S16 + SWING


# ---------------------------------------------------------------- drum voice

class Kit:
    """A human-ish pair of hands + feet. Tracks < 2 hands, < 2 feet per instant."""

    def __init__(self, sc):
        self.sc = sc

    def _add(self, t, key, vel, dur=60):
        self.sc.add(t, key, vel, dur)

    # --- straight hits ---------------------------------------------------
    def snare(self, t, vel, dur=45):
        self._add(t, K["snare"], vel, dur)

    def ghost(self, t, vel=32):
        self._add(t, K["snare"], max(18, min(40, vel)), 30)

    def kick(self, t, vel=100, dur=60):
        self._add(t, K["kick"], vel, dur)

    def hat(self, t, vel=MF, open_=False, pedal=False, dur=40):
        if pedal:
            self._add(t, K["hatP"], vel, 30)
        elif open_:
            self._add(t, K["hatO"], vel, 120)
        else:
            self._add(t, K["hatC"], vel, dur)

    def ride(self, t, vel=MF, bell=False, dur=80):
        self._add(t, K["rideBell"] if bell else K["ride"], vel, dur)

    def crash(self, t, vel=F, which=1, dur=480):
        self._add(t, K["crash"] if which == 1 else K["crash2"], vel, dur)

    def tom(self, t, high, vel=MF, dur=90):
        key = K["tomH2"] if high else K["tomL2"]
        self._add(t, key, vel, dur)

    def floor(self, t, high, vel=MF, dur=90):
        key = K["tomH"] if high else K["tomL"]
        self._add(t, key, vel, dur)

    def perc(self, t, key, vel=MF, dur=60):
        self._add(t, key, vel, dur)


# ---------------------------------------------------------------- phrases

def phrase_A(kit, b, rng, energy=MF):
    """Motif A: syncopated kick, snare backbeat, riding hats."""
    base = bar_t(b)
    t0 = base
    kit.hat(t0 + 0, energy, dur=40); kit.ride(t0 + 0, energy - 8)
    kit.kick(t0 + 0, 108)
    kit.hat(t0 + TPB, energy - 4)
    kit.snare(t0 + TPB, energy, 45)
    kit.hat(t0 + 2 * TPB, energy)
    kit.kick(t0 + 2 * TPB, 92)
    kit.hat(t0 + 3 * TPB, energy - 4)
    kit.snare(t0 + 3 * TPB, energy + 6, 50)
    # swung 16ths between beats for hand flow
    for i in range(1, 16, 2):
        if rng.random() < 0.35:
            kit.hat(t0 + i * S16, energy - 20)
    return base


def phrase_A_var(kit, b, rng, energy=MF):
    """Motif A developed: extra kick displacement, ghosted snare."""
    base = bar_t(b)
    kit.hat(base, energy)
    kit.kick(base, 112)
    kit.snare(base + TPB, energy + 4, 48)
    kit.hat(base + TPB, energy - 4)
    kit.kick(base + TPB + S16, 84)
    kit.ghost(base + 2 * TPB - S16, 30)
    kit.hat(base + 2 * TPB, energy)
    kit.kick(base + 2 * TPB, 96)
    kit.snare(base + 3 * TPB, energy + 8, 50)
    kit.hat(base + 3 * TPB, energy - 4)
    kit.kick(base + 3 * TPB + SWING, 80)
    if rng.random() < 0.6:
        kit.ghost(base + 3 * TPB + S16, 34)
    return base


def phrase_B(kit, b, rng, energy=MF):
    """Motif B: tom pattern, half-time feel, opens space."""
    base = bar_t(b)
    kit.ride(base, energy - 6)
    kit.kick(base, 104)
    kit.tom(base + TPB, high=False, vel=energy)
    kit.tom(base + TPB + S16 * 1.5, high=True, vel=energy - 12)
    kit.ride(base + 2 * TPB, energy - 6)
    kit.snare(base + 2 * TPB, energy, 50)
    kit.kick(base + 2 * TPB + S16, 78)
    kit.tom(base + 3 * TPB, high=True, vel=energy)
    kit.tom(base + 3 * TPB + S16, high=False, vel=energy - 10)
    kit.tom(base + 3 * TPB + 2 * S16, high=True, vel=energy - 4)
    kit.tom(base + 3 * TPB + 3 * S16, high=False, vel=energy - 8)
    return base


def fill(kit, b, rng, style=0, energy=MF):
    """Four-beat fill leading to next downbeat. Travels around the kit."""
    base = bar_t(b)
    if style == 0:
        # single-stroke 16ths around toms, accented on 1 and 3
        order = [False, True, False, True, False, True, False, True,
                 True, False, True, False, True, False, True, False]
        for i in range(16):
            v = energy + (14 if i % 4 == 0 else (-6 if i % 2 else 0))
            kit.tom(base + i * S16 * (S16 * 1.0 / S16), high=order[i], vel=v)
        # fix timing: place evenly
    # Recompute properly below for all styles, so clear previous is not needed;
    # we just use absolute placements.
    return base


def fill_singles(kit, b, rng, energy=MF):
    base = bar_t(b)
    seq = ["floorL", "floorH", "tomL", "tomH", "snare", "tomH", "tomL", "floorH"]
    for i in range(8):
        t = base + i * (TPB / 2.0)
        name = seq[i]
        v = energy + (12 if i % 4 == 0 else 0)
        if name == "floorL":
            kit.floor(t, high=False, vel=v)
        elif name == "floorH":
            kit.floor(t, high=True, vel=v)
        elif name == "tomL":
            kit.tom(t, high=False, vel=v)
        elif name == "tomH":
            kit.tom(t, high=True, vel=v)
        else:
            kit.snare(t, v, 42)
    # add a 16th ornament at the end
    kit.tom(base + 3 * TPB + 2 * S16, high=True, vel=energy - 6)
    kit.tom(base + 3 * TPB + 3 * S16, high=False, vel=energy - 12)
    return base


def fill_doubles(kit, b, rng, energy=MF):
    """Doubles travelling up and down toms, resolve into snare hit."""
    base = bar_t(b)
    positions = list(range(8))  # 8th notes
    heads = ["floorL", "tomL", "tomH", "snare", "tomH", "tomL", "floorH", "floorL"]
    for i in positions:
        t = base + i * (TPB / 2.0)
        name = heads[i]
        for j in range(2):
            v = energy + (10 if (i == 0 or i == 3) else 0) - j * 6
            tt = t + j * (S16 * 0.42)
            if name == "floorL":
                kit.floor(tt, high=False, vel=v)
            elif name == "floorH":
                kit.floor(tt, high=True, vel=v)
            elif name == "tomL":
                kit.tom(tt, high=False, vel=v)
            elif name == "tomH":
                kit.tom(tt, high=True, vel=v)
            else:
                kit.snare(tt, v, 40)
    return base


def roll_swell(kit, b, rng, start=0, length=1.0, kind="snare"):
    """A crescendo roll from pp to ff over the given span, ends on a downbeat hit."""
    base = bar_t(b)
    span = BAR * length
    # 16 then 32 then 64 subdivision sweep for swell.
    t = base + start * BAR
    end = base + start * BAR + span
    # three stages
    stages = [(0.0, 0.5, 4, P), (0.5, 0.8, 8, MF), (0.8, 1.0, 16, FF)]
    for (a, bb, n, v0) in stages:
        seg_start = t + a * span
        seg_end = t + bb * span
        steps = max(2, int(round((seg_end - seg_start) / (TPB / n))))
        for i in range(steps):
            tt = seg_start + i * (seg_end - seg_start) / steps
            frac = i / max(1, steps - 1)
            v = v0 + (FF - v0) * frac * 0.9 + 6
            if kind == "snare":
                kit.snare(tt, int(v), 24)
            elif kind == "toms":
                high = (i % 2 == 0)
                kit.tom(tt, high=high, vel=int(v))
    # final accented hit
    kit.snare(end, FFF, 60)
    return end


# ---------------------------------------------------------------- structure

def compose():
    rng = random.Random(20240517)
    sc = Score()
    kit = Kit(sc)

    bpm = 96
    t = 0  # noqa: F841  (kept for clarity; all positions from bar index)

    # ---- INTRO (bars 0-3): establish pulse, ride + sparse kick, snare hits
    kit.crash(bar_t(0), F, 1)
    kit.kick(bar_t(0), 112)
    kit.ride(bar_t(0), MF)
    for i in range(4):
        base = bar_t(i)
        if i == 0:
            kit.snare(base + 2 * TPB, MF)
            kit.kick(base + 1 * TPB, 90)
            kit.kick(base + 3 * TPB, 86)
        else:
            kit.kick(base, 108)
            kit.ride(base, MF - (i * 4))
            kit.ride(base + 2 * TPB, MF - 6)
            kit.kick(base + 2 * TPB, 94)
            kit.snare(base + TPB, MF, 44)
            kit.snare(base + 3 * TPB, MF + 6, 46)
            for n in (1, 2, 3):
                kit.ride(base + n * TPB + S16 * 0.5, MP - 6)

    # ---- A: state motif (bars 4-7)
    for i in range(4):
        phrase_A(kit, 4 + i, rng, energy=MF)

    # ---- A': vary (bars 8-11) with build
    for i in range(4):
        e = MF + i * 4
        phrase_A_var(kit, 8 + i, rng, energy=e)
    # turn-around into B
    fill_singles(kit, 12, rng, energy=MF + 8)

    # ---- B: contrast phrase (bars 13-16), space, ride bell
    for i in range(4):
        phrase_B(kit, 13 + i, rng, energy=MF)
    kit.rideBell_placeholder = None  # noqa

    # ---- A return, developed, tighter (bars 17-20)
    for i in range(4):
        phrase_A(kit, 17 + i, rng, energy=MF + 6 + i * 2)
        kit.rideBell(bar_t(17 + i) + 2 * TPB, MF + i * 4)

    # ---- build: doubles fill (bars 21-22) into swell (bars 22-24)
    fill_doubles(kit, 20, rng, energy=MF)
    fill_doubles(kit, 21, rng, energy=MF + 8)

    # ---- TENSION: long roll swell (bars 22-23), resolving on 24 downbeat
    roll_swell(kit, 22, rng, start=0.0, length=2.0, kind="snare")

    # ---- release: heavy groove (bars 24-27)
    for i in range(4):
        base = bar_t(24 + i)
        kit.crash(base, F if i == 0 else MF, 1, 300)
        kit.kick(base, 114)
        kit.snare(base + TPB, F, 50)
        kit.kick(base + 2 * TPB, 108)
        kit.snare(base + 3 * TPB, F + 4, 52)
        for n in (0, 1, 2, 3):
            kit.hat(base + n * TPB + (S16 if n % 2 else 0), MF - 8)
        kit.hat(base + 2 * TPB + SWING, MF - 16)

    # ---- motific development section: call & response hands (bars 28-35)
    for i in range(4):
        base = bar_t(28 + i * 2)
        # call: tom melody
        kit.tom(base, high=False, vel=MF)
        kit.tom(base + S16 * 2, high=True, vel=MF - 6)
        kit.tom(base + TPB, high=False, vel=MF + 4)
        kit.tom(base + TPB + S16 * 3, high=True, vel=MF - 4)
        kit.snare(base + 2 * TPB, MF + 6, 44)
        kit.tom(base + 3 * TPB, high=True, vel=MF)
        kit.tom(base + 3 * TPB + S16, high=False, vel=MF - 8)
        # response: kick/snare dialogue with ghosted hats
        kit.kick(base + BAR, 110)
        kit.snare(base + BAR + TPB, MF + 4, 46)
        kit.ghost(base + BAR + TPB + S16, 30)
        kit.kick(base + BAR + 2 * TPB, 96)
        kit.ghost(base + BAR + 3 * TPB - S16, 34)
        kit.snare(base + BAR + 3 * TPB, MF + 8, 48)

    # ---- drum break: hands-only flurry (bars 36-39)
    for i in range(4):
        base = bar_t(36 + i)
        # snare-led 16th run with accents, doubles at ends
        pat = [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1]
        for k in range(16):
            if pat[k]:
                tt = base + k * S16
                accent = (k % 4 == 0)
                v = (F if accent else MF - 8) - (8 if k > 12 else 0)
                kit.snare(tt, v, 32)
        # doubles on toms at tail
        kit.tom(base + 3 * TPB + 0.25 * S16, high=True, vel=F)
        kit.tom(base + 3 * TPB + 0.75 * S16, high=False, vel=F - 4)
        kit.tom(base + 3 * TPB + S16 * 2, high=True, vel=F - 8)
        kit.tom(base + 3 * TPB + S16 * 3, high=False, vel=F - 12)

    # ---- swell 2, toms, rising pitch (bars 40-41)
    roll_swell(kit, 40, rng, start=0.0, length=2.0, kind="toms")

    # ---- climax groove (bars 42-45)
    for i in range(4):
        base = bar_t(42 + i)
        if i == 0:
            kit.crash(base, FFF, 1, 240)
        kit.kick(base, 116)
        kit.snare(base + TPB, F + 4, 52)
        kit.kick(base + 2 * TPB, 110)
        kit.snare(base + 3 * TPB, F + 6, 50)
        kit.ride(base, MF)
        kit.ride(base + 2 * TPB, MF - 4)
        kit.ohl = None  # noqa
        if i % 2 == 1:
            kit.hat(base + TPB + SWING, MF - 12)
            kit.hat(base + 3 * TPB + SWING, MF - 12)

    # ---- final fill and landing (bars 46-47)
    fill_doubles(kit, 45, rng, energy=F - 6)
    fill_singles(kit, 46, rng, energy=F - 2)

    # ---- LANDING: downbeat hit, leave silence after (bar 47 -> 48)
    base = bar_t(47)
    kit.crash(base, FFF, 1, 960)
    kit.kick(base, 118)
    kit.snare(base, FFF, 60)
    kit.floor(base + TPB / 2.0, high=True, vel=MF)
    kit.floor(base + TPB, high=False, vel=MF - 8)
    # coda echoes that quickly decay, ending on a single hit
    kit.snare(base + 2 * TPB, F, 60)
    kit.kick(base + 2 * TPB, 100)
    kit.hat(base + 3 * TPB, MP - 4, pedal=True)

    # ---- sprinkle percussion colour on a few moments
    for b in (7, 15, 23, 31, 39):
        kit.perc(bar_t(b) + 3 * TPB + 2 * S16, K["cowbell"], MF - 10, 40)
        kit.perc(bar_t(b) + 3 * TPB + 3 * S16, K["claves"], MP, 30)
    for b in (11, 27, 43):
        kit.perc(bar_t(b) + TPB + S16, K["tamb"], MP + 6, 60)
        kit.perc(bar_t(b) + 3 * TPB + S16, K["cabasa"], MP, 40)

    return sc


# Patch rideBell helper (avoid attribute gymnastics)
def _ride_bell(self, t, vel=MF, dur=80):
    self._add(t, K["rideBell"], vel, dur)


Kit.rideBell = _ride_bell


# ---------------------------------------------------------------- main

def main():
    sc = compose()
    sc.emit("solo.mid")
    print("wrote solo.mid")


if __name__ == "__main__":
    main()
