#!/usr/bin/env python3
"""
drum_solo.py -- generates a two-minute General MIDI drum solo on channel 10.

The solo is built as a continuous performance: a hook motif is stated, moved
around the kit, broken down, rebuilt, restated and finally landed.  Timing is
humanised (per-onset offsets plus a slow phrase sway) and velocities carry
accents, ghost notes and crescendos rather than block-level loudness changes.
At most two hands and two feet ever strike at the same instant.

Output: solo.mid (deterministic).
"""

import math
import random

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

# ---------------------------------------------------------------------------
# General MIDI percussion (channel 10)
# ---------------------------------------------------------------------------
KICK = 36
STICK = 37
SNARE = 38
E_SNARE = 40
T_FL = 41          # low floor tom
HH = 42            # closed hi-hat
T_FH = 43          # high floor tom
PEDAL = 44         # pedal hi-hat
T_L = 45           # low tom
OHH = 46           # open hi-hat
T_ML = 47          # low-mid tom
T_MH = 48          # hi-mid tom
CRASH = 49
T_H = 50           # high tom
RIDE = 51
CHINA = 52
BELL = 53          # ride bell
TAMB = 54
SPLASH = 55
COWBELL = 56
CRASH2 = 57
BONGO_H = 60
CONGA_H = 63
CONGA_L = 64
AGOGO = 67
CABASA = 69
MARACAS = 70
CLAVES = 75
WBLOCK = 76

FEET = {35, KICK, PEDAL}          # struck by a foot, everything else by a hand

TPB = 960                         # ticks per beat
CHANNEL = 9                       # MIDI channel 10 (0-indexed)


# ---------------------------------------------------------------------------
# Event builder
# ---------------------------------------------------------------------------
class Builder:
    """Collects (beat, note, velocity, duration_in_beats) events.

    Enforces the physical limits of one drummer: no more than two hand
    strikes and two foot strikes at any single instant.
    """

    def __init__(self, rng):
        self.rng = rng
        self.events = []
        self._groups = {}

    def hit(self, t, note, vel, dur=0.15):
        if t < -0.001:
            return
        if t < 0.0:
            t = 0.0
        v = int(round(vel))
        v = max(1, min(127, v))

        gk = int(round(t * 96.0))
        is_foot = 1 if note in FEET else 0
        g = self._groups.get(gk)
        if g is None:
            g = [0, 0]
            self._groups[gk] = g
        if g[is_foot] >= 2:
            return
        g[is_foot] += 1
        self.events.append([t, note, v, float(dur)])

    def finalize(self):
        """Sort, then drop hand notes that no pair of hands could play."""
        evs = sorted(self.events, key=lambda e: (int(round(e[0] * 96.0)), e[1]))
        out = []
        last_t = None
        last_g = None
        for t, note, vel, dur in evs:
            if note not in FEET:
                gk = int(round(t * 96.0))
                if last_g is not None and gk != last_g and 0.0 < (t - last_t) < 0.045:
                    continue
                last_t = t
                last_g = gk
            out.append((t, note, vel, dur))
        return out


# ---------------------------------------------------------------------------
# Musical primitives
# ---------------------------------------------------------------------------
def groove_A(b, bar, intensity=1.0, ride=False, ghost=True,
             kick=(0.0, 1.5, 2.5), snare=(1.0, 3.0),
             open_at=None, crash_at=None, extra_ghosts=()):
    """The hook: 8th cymbal, kick 1 / & of 2 / & of 3, backbeats 2 & 4."""
    t0 = bar * 4.0
    for i in range(8):
        t = t0 + i * 0.5
        if open_at is not None and abs(i * 0.5 - open_at) < 1e-9:
            note, vel = OHH, 94.0
        elif ride:
            note, vel = RIDE, (88.0 if i % 2 == 0 else 72.0)
        else:
            note, vel = HH, (92.0 if i % 2 == 0 else 62.0)
        b.hit(t, note, vel * intensity, 0.22)
    for off in kick:
        b.hit(t0 + off, KICK, 104.0 * intensity, 0.2)
    for off in snare:
        b.hit(t0 + off, SNARE, 101.0 * intensity, 0.2)
    if crash_at:
        for off in crash_at:
            b.hit(t0 + off, CRASH, 113, 3.0)
    if ghost:
        for off in (0.75, 2.75) + tuple(extra_ghosts):
            b.hit(t0 + off, SNARE, 24.0 + 10.0 * intensity, 0.15)


def fill_toms(b, t0, t1, seq, rate=0.25, v0=80, v1=100, accent_every=4, dur=0.12):
    """Single strokes stepping through `seq` across the time span."""
    n = int(round((t1 - t0) / rate))
    if n <= 0:
        return
    L = len(seq)
    for i in range(n):
        t = t0 + i * rate
        note = seq[min(L - 1, i * L // n)]
        f = i / max(1, n - 1)
        v = v0 + (v1 - v0) * f
        if accent_every and i % accent_every == 0:
            v += 14
        b.hit(t, note, v, dur)


def doubles_run(b, t0, t1, seq, spacing=0.125, v0=80, v1=104):
    """Double strokes: two hits per drum, travelling through `seq`."""
    nslots = int(round((t1 - t0) / 0.25))
    if nslots <= 0:
        return
    L = len(seq)
    for s in range(nslots):
        note = seq[min(L - 1, s * L // nslots)]
        f = s / max(1, nslots - 1)
        v = v0 + (v1 - v0) * f
        b.hit(t0 + s * 0.25, note, v + 8, 0.12)
        b.hit(t0 + s * 0.25 + spacing, note, v * 0.72, 0.1)


def roll(b, t0, t1, note, r0=0.25, r1=0.125, v0=60, v1=100, dur=0.09):
    """Roll that accelerates and swells from r0/v0 to r1/v1."""
    t = t0
    span = max(1e-9, t1 - t0)
    while t < t1 - 1e-9:
        f = (t - t0) / span
        b.hit(t, note, v0 + (v1 - v0) * f, dur)
        t += r0 + (r1 - r0) * f


# ---------------------------------------------------------------------------
# The solo
# ---------------------------------------------------------------------------
def compose(b, rng):
    # ======================= 1. INTRO (bars 0-3) =======================
    b.hit(0.0, CRASH, 110, 3.0)
    b.hit(0.0, KICK, 106, 0.3)
    b.hit(1.0, RIDE, 84, 0.5)
    b.hit(1.75, KICK, 64, 0.25)
    b.hit(2.0, RIDE, 88, 0.5)
    b.hit(3.0, RIDE, 78, 0.5)
    b.hit(3.5, SNARE, 30, 0.15)
    b.hit(3.75, SNARE, 26, 0.15)

    t0 = 4.0
    for i in range(4):
        b.hit(t0 + i, RIDE, 82 if i % 2 == 0 else 72, 0.45)
    b.hit(t0 + 0.0, KICK, 94, 0.25)
    b.hit(t0 + 1.5, KICK, 66, 0.25)
    b.hit(t0 + 2.0, SNARE, 74, 0.25)
    b.hit(t0 + 3.0, SNARE, 86, 0.25)
    b.hit(t0 + 3.5, SNARE, 30, 0.15)

    groove_A(b, 2, intensity=0.86)
    groove_A(b, 3, intensity=0.92, open_at=3.5, extra_ghosts=(3.75,))

    # =================== 2. HOOK STATEMENT (bars 4-11) ===================
    groove_A(b, 4, intensity=1.02, crash_at=(0.0,))
    groove_A(b, 5, intensity=1.00, open_at=3.5)
    groove_A(b, 6, intensity=1.00, kick=(0.0, 1.5, 2.5, 3.75),
             extra_ghosts=(1.75, 3.75))
    groove_A(b, 7, intensity=1.00, snare=(1.0, 2.75, 3.0))

    for bar in (8, 9):
        t0 = bar * 4.0
        for i in range(8):
            b.hit(t0 + i * 0.5, RIDE, 88 if i % 2 == 0 else 68, 0.4)
        b.hit(t0 + 0.0, KICK, 106, 0.2)
        b.hit(t0 + 1.5, KICK, 92, 0.2)
        b.hit(t0 + 2.5, KICK, 100, 0.2)
        b.hit(t0 + 1.0, SNARE, 102, 0.2)
        b.hit(t0 + 3.0, SNARE, 106, 0.2)
        for off in (0.75, 1.75, 2.75, 3.75):
            if rng.random() < 0.65:
                b.hit(t0 + off, SNARE, rng.randint(20, 34), 0.12)
        if bar == 9:
            b.hit(t0 + 3.5, SNARE, 48, 0.12)

    groove_A(b, 10, intensity=1.06, crash_at=(0.0,), extra_ghosts=(3.75,))

    # bar 11: fill riding into the development
    fill_toms(b, 44.0, 47.5, [SNARE, T_MH, T_ML, T_L, T_FH, T_FL],
              rate=0.25, v0=72, v1=96, accent_every=4)
    b.hit(47.5, SNARE, 58, 0.12)
    b.hit(47.75, SNARE, 46, 0.12)

    # =================== 3. DEVELOPMENT (bars 12-23) ===================
    b.hit(48.0, CRASH, 108, 2.5)
    for bar in (12, 13):
        t0 = bar * 4.0
        for i in range(8):
            b.hit(t0 + i * 0.5, BELL, 94 if i % 2 == 0 else 76, 0.3)
        b.hit(t0 + 0.0, KICK, 108, 0.2)
        b.hit(t0 + 1.5, KICK, 96, 0.2)
        b.hit(t0 + 2.5, KICK, 104, 0.2)
        b.hit(t0 + 1.0, SNARE, 104, 0.2)
        b.hit(t0 + 3.0, SNARE, 108, 0.2)
        b.hit(t0 + 0.75, SNARE, 30, 0.12)
        b.hit(t0 + 2.75, SNARE, 32, 0.12)
        b.hit(t0 + 3.75, SNARE, 42, 0.12)

    # bars 14-15: the hook re-voiced on the toms
    for bar in (14, 15):
        t0 = bar * 4.0
        b.hit(t0 + 0.0, T_FL, 106, 0.3)
        b.hit(t0 + 1.5, T_L, 94, 0.3)
        b.hit(t0 + 2.5, T_ML, 100, 0.3)
        b.hit(t0 + 1.0, T_MH, 102, 0.3)
        b.hit(t0 + 3.0, T_H, 108, 0.3)
        b.hit(t0 + 0.75, SNARE, 30, 0.12)
        b.hit(t0 + 2.75, SNARE, 28, 0.12)
        for i in range(8):
            b.hit(t0 + i * 0.5, HH, 80 if i % 2 == 0 else 58, 0.2)
        if bar == 15:
            b.hit(t0 + 3.5, COWBELL, 74, 0.2)

    # bars 16-17: long single-stroke run down and back up the kit
    fill_toms(b, 64.0, 72.0,
              [SNARE, T_MH, T_ML, T_L, T_FH, T_FL, T_FH, T_L, T_ML, T_MH],
              rate=0.25, v0=74, v1=104, accent_every=4)

    # bars 18-19: crescendo singles into a crash
    fill_toms(b, 72.0, 79.5, [SNARE, T_MH, T_ML, T_L, T_FH],
              rate=0.25, v0=76, v1=112, accent_every=4)
    b.hit(79.5, SNARE, 60, 0.12)
    b.hit(79.75, SNARE, 50, 0.12)

    b.hit(80.0, CRASH, 112, 2.5)
    b.hit(80.0, KICK, 108, 0.3)
    fill_toms(b, 80.5, 83.5, [SNARE, T_MH, T_ML, T_L, T_FH, T_FL],
              rate=0.25, v0=80, v1=98, accent_every=4)
    doubles_run(b, 83.5, 87.5, [T_FL, T_FH, T_L, T_ML, T_MH, SNARE],
                v0=80, v1=96)
    b.hit(87.5, SNARE, 54, 0.12)
    b.hit(87.75, SNARE, 46, 0.12)

    # bar 22: breath / half-time
    t0 = 88.0
    for i in range(4):
        b.hit(t0 + i, RIDE, 84 if i % 2 == 0 else 70, 0.5)
    b.hit(t0 + 0.0, KICK, 104, 0.25)
    b.hit(t0 + 2.0, STICK, 96, 0.2)
    b.hit(t0 + 2.5, KICK, 78, 0.25)
    b.hit(t0 + 3.5, SNARE, 34, 0.12)
    b.hit(t0 + 3.75, SNARE, 30, 0.12)

    # bar 23: roll gathering into the crash
    roll(b, 92.0, 96.0, SNARE, r0=0.25, r1=0.125, v0=60, v1=100)

    # ===================== 4. CONTRAST (bars 24-27) =====================
    b.hit(96.0, CRASH, 118, 4.0)
    b.hit(96.0, KICK, 112, 0.4)
    b.hit(97.5, BELL, 72, 0.5)
    b.hit(98.0, SNARE, 92, 0.3)
    b.hit(98.5, KICK, 80, 0.3)
    b.hit(99.5, SNARE, 32, 0.15)

    t0 = 100.0
    b.hit(t0 + 0.0, KICK, 104, 0.3)
    b.hit(t0 + 1.0, BELL, 78, 0.4)
    b.hit(t0 + 1.5, BELL, 70, 0.4)
    b.hit(t0 + 2.0, SNARE, 100, 0.3)
    b.hit(t0 + 2.5, KICK, 84, 0.3)
    b.hit(t0 + 3.0, BELL, 76, 0.4)
    b.hit(t0 + 3.75, SNARE, 36, 0.15)
    b.hit(t0 + 1.5, COWBELL, 62, 0.2)

    t0 = 104.0
    for i in range(8):
        b.hit(t0 + i * 0.5, HH, 78 if i % 2 == 0 else 54, 0.2)
    b.hit(t0 + 0.0, KICK, 108, 0.3)
    b.hit(t0 + 2.0, SNARE, 104, 0.3)
    b.hit(t0 + 2.5, KICK, 86, 0.3)
    b.hit(t0 + 3.5, SNARE, 34, 0.12)
    b.hit(t0 + 2.0, TAMB, 58, 0.2)

    # bar 27: growing 16ths
    fill_toms(b, 108.0, 112.0,
              [SNARE, T_MH, T_ML, T_L, T_FH, T_FL, T_FH, T_L, T_ML, T_MH],
              rate=0.25, v0=58, v1=92, accent_every=8)

    # ======================= 5. BUILD (bars 28-39) =======================
    for k, bar in enumerate((28, 29, 30, 31)):
        t0 = bar * 4.0
        inten = 0.90 + 0.05 * k
        for i in range(16):
            if i % 4 == 0:
                v = 96.0
            elif i % 2 == 0:
                v = 72.0
            else:
                v = 44.0 + 4.0 * k
            b.hit(t0 + i * 0.25, HH, v * inten, 0.12)
        b.hit(t0 + 0.0, KICK, 108, 0.25)
        b.hit(t0 + 1.5, KICK, 96, 0.25)
        b.hit(t0 + 2.5, KICK, 102, 0.25)
        b.hit(t0 + 1.0, SNARE, 100, 0.2)
        b.hit(t0 + 3.0, SNARE, 106, 0.2)
        b.hit(t0 + 3.75, SNARE, 30.0 + 4.0 * k, 0.12)
        if k == 3:
            b.hit(t0 + 3.5, OHH, 96, 0.3)

    # bars 32-33: double strokes between snare and rack tom
    for k, bar in enumerate((32, 33)):
        t0 = bar * 4.0
        for i in range(16):
            note = SNARE if (i // 2) % 2 == 0 else T_MH
            v = 62.0 + 6.0 * k
            if i % 4 == 0:
                v += 24
            elif i % 2 == 0:
                v += 6
            b.hit(t0 + i * 0.25, note, v, 0.1)
        b.hit(t0 + 0.0, KICK, 104, 0.2)
        b.hit(t0 + 2.0, KICK, 100, 0.2)

    # bars 34-35: flams, open hats, growing weight
    for k, bar in enumerate((34, 35)):
        t0 = bar * 4.0
        for i in range(8):
            note = OHH if i == 7 else HH
            v = 92 if i % 2 == 0 else 62
            b.hit(t0 + i * 0.5, note, v, 0.2)
        for off in (0.0, 2.0):
            b.hit(t0 + off - 0.05, SNARE, 34, 0.08)
            b.hit(t0 + off, SNARE, 106.0 + 2.0 * k, 0.2)
        b.hit(t0 + 1.0, SNARE, 88, 0.2)
        b.hit(t0 + 3.0, SNARE, 92, 0.2)
        b.hit(t0 + 0.0, KICK, 108, 0.2)
        b.hit(t0 + 1.5, KICK, 96, 0.2)
        b.hit(t0 + 2.5, KICK, 104, 0.2)

    # bars 36-37: single strokes sweeping the kit, swelling
    fill_toms(b, 144.0, 152.0,
              [SNARE, T_MH, T_ML, T_L, T_FH, T_FL,
               T_FH, T_L, T_ML, T_MH, T_H, SNARE],
              rate=0.25, v0=72, v1=108, accent_every=4)

    # bars 38-39: accelerating roll, then a jump to the peak
    roll(b, 152.0, 158.0, SNARE, r0=0.25, r1=0.125, v0=68, v1=104)
    fill_toms(b, 158.0, 159.5, [SNARE, T_MH, T_ML, T_L, T_FH, T_FL],
              rate=0.25, v0=100, v1=118, accent_every=4)
    b.hit(159.5, SNARE, 84, 0.12)
    b.hit(159.75, SNARE, 76, 0.12)

    # ======================== 6. PEAK (bars 40-47) ========================
    b.hit(160.0, CRASH, 122, 3.0)
    b.hit(160.0, KICK, 118, 0.4)
    for k, bar in enumerate((40, 41, 42, 43)):
        t0 = bar * 4.0
        if k > 0 and k % 2 == 1:
            b.hit(t0 + 0.0, CRASH, 108, 2.0)
        for i in range(8):
            b.hit(t0 + i * 0.5, BELL, 94 if i % 2 == 0 else 76, 0.3)
        b.hit(t0 + 0.0, KICK, 112, 0.25)
        b.hit(t0 + 1.5, KICK, 100, 0.2)
        b.hit(t0 + 2.5, KICK, 106, 0.2)
        b.hit(t0 + 1.0, SNARE, 108, 0.2)
        b.hit(t0 + 3.0, SNARE, 112, 0.2)
        for off in (0.75, 1.75, 2.75, 3.75):
            if rng.random() < 0.75:
                b.hit(t0 + off, SNARE, rng.randint(24, 42), 0.1)
        if bar == 43:
            b.hit(t0 + 3.5, T_FL, 96, 0.2)
            b.hit(t0 + 3.75, T_FH, 92, 0.2)

    # bars 44-46: peak density, singles then doubles
    b.hit(176.0, CRASH, 118, 3.0)
    b.hit(176.0, KICK, 116, 0.3)
    fill_toms(b, 176.5, 180.0, [SNARE, T_MH, T_ML, T_L, T_FH, T_FL],
              rate=0.25, v0=88, v1=104, accent_every=4)
    fill_toms(b, 180.0, 184.0, [T_FL, T_FH, T_L, T_ML, T_MH, T_H],
              rate=0.25, v0=90, v1=108, accent_every=4)
    doubles_run(b, 184.0, 187.5, [T_H, T_MH, T_ML, T_L, T_FH, T_FL],
                v0=86, v1=104)
    for bar in (44, 45, 46):
        t0 = bar * 4.0
        b.hit(t0 + 0.0, KICK, 112, 0.2)
        b.hit(t0 + 2.0, KICK, 108, 0.2)

    # bar 47: big fill into the return of the hook
    fill_toms(b, 188.0, 190.0, [SNARE, T_MH, T_ML, T_L],
              rate=0.25, v0=84, v1=96, accent_every=4)
    roll(b, 190.0, 191.4, SNARE, r0=0.25, r1=0.125, v0=70, v1=104)
    b.hit(191.5, T_FL, 100, 0.2)
    b.hit(191.75, T_FH, 96, 0.2)

    # ==================== 7. HOOK RETURNS (bars 48-53) ====================
    b.hit(192.0, CRASH, 114, 3.0)
    groove_A(b, 48, intensity=1.05)
    groove_A(b, 49, intensity=1.02, open_at=3.5, extra_ghosts=(1.75,))
    groove_A(b, 50, intensity=0.96, ride=True, extra_ghosts=(3.75,))

    # bar 51: pull back, let the tension gather
    t0 = 204.0
    for i in range(8):
        b.hit(t0 + i * 0.5, RIDE, 76 if i % 2 == 0 else 62, 0.4)
    b.hit(t0 + 0.0, KICK, 96, 0.25)
    b.hit(t0 + 2.0, SNARE, 92, 0.25)
    b.hit(t0 + 2.5, KICK, 78, 0.25)
    b.hit(t0 + 3.5, SNARE, 28, 0.12)
    b.hit(t0 + 3.75, SNARE, 26, 0.12)

    # bar 52: build again
    fill_toms(b, 208.0, 212.0,
              [SNARE, T_MH, T_ML, T_L, T_FH, T_FL, T_FH, T_L, T_ML, T_MH],
              rate=0.25, v0=66, v1=98, accent_every=6)

    # bar 53: roll into the finale
    roll(b, 212.0, 215.5, SNARE, r0=0.25, r1=0.1, v0=72, v1=106)
    b.hit(215.5, T_FL, 92, 0.2)
    b.hit(215.75, T_FH, 88, 0.2)

    # ======================= 8. FINALE (bars 54-57) =======================
    b.hit(216.0, CRASH, 116, 2.5)
    b.hit(216.0, KICK, 112, 0.3)
    doubles_run(b, 216.5, 220.0,
                [SNARE, T_MH, T_ML, T_L, T_FH, T_FL, SNARE, T_MH],
                v0=84, v1=104)
    fill_toms(b, 220.0, 223.5, [T_FL, T_FH, T_L, T_ML, T_MH, T_H],
              rate=0.25, v0=88, v1=112, accent_every=4)

    # bar 56: the final push
    roll(b, 224.0, 227.0, SNARE, r0=0.25, r1=0.125, v0=80, v1=118)
    b.hit(227.0, T_FL, 108, 0.2)
    b.hit(227.25, T_FH, 104, 0.2)
    b.hit(227.5, T_L, 100, 0.2)
    b.hit(227.75, T_ML, 96, 0.2)
    b.hit(225.0, KICK, 110, 0.2)
    b.hit(226.0, KICK, 110, 0.2)

    # the landing
    b.hit(228.0, CRASH, 127, 8.0)
    b.hit(228.0, KICK, 124, 0.5)
    b.hit(228.0, SNARE, 118, 0.4)


# ---------------------------------------------------------------------------
# Tempo map (beat, bpm) -- the pulse surges and settles with the music
# ---------------------------------------------------------------------------
TEMPO_POINTS = [
    (0.0, 100.0),      # laid-back opening
    (8.0, 104.0),
    (16.0, 112.0),     # hook settles in
    (32.0, 116.0),
    (48.0, 112.0),     # development eases back
    (60.0, 118.0),
    (68.0, 120.0),
    (92.0, 118.0),
    (96.0, 98.0),      # contrast pulls way back
    (104.0, 102.0),
    (112.0, 108.0),    # build starts climbing
    (128.0, 116.0),
    (144.0, 124.0),
    (156.0, 130.0),    # rush into the peak
    (160.0, 126.0),
    (176.0, 128.0),
    (188.0, 132.0),
    (192.0, 120.0),    # hook returns, relax
    (208.0, 118.0),
    (216.0, 124.0),    # finale accelerates
    (228.0, 128.0),
    (240.0, 128.0),
]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def write_midi(b, tempo_points, path):
    evs = b.finalize()

    hrng = random.Random(0x5EED1)
    group_off = {}
    notes = []

    for t, note, vel, dur in evs:
        gk = int(round(t * 96.0))
        if gk not in group_off:
            off = hrng.gauss(0.0, 0.0050)
            off += 0.0085 * math.sin(t * 0.41)
            off += 0.0050 * math.sin(t * 1.13 + 1.7)
            off += hrng.uniform(-0.004, 0.004)
            group_off[gk] = off
        tt = t + group_off[gk] + hrng.gauss(0.0, 0.0018)
        if tt < 0.0:
            tt = 0.0
        v = int(round(vel + hrng.gauss(0.0, 3.2)))
        v = max(1, min(127, v))
        tick = int(round(tt * TPB))
        dtick = max(12, int(round(dur * TPB)))
        notes.append((tick, note, v, dtick))

    msgs = []
    for tick, note, v, dtick in notes:
        msgs.append((tick, 1,
                     Message('note_on', channel=CHANNEL, note=note, velocity=v)))
        msgs.append((tick + dtick, 0,
                     Message('note_off', channel=CHANNEL, note=note, velocity=0)))
    for bpos, bpm in tempo_points:
        msgs.append((int(round(bpos * TPB)), -1,
                     MetaMessage('set_tempo', tempo=bpm2tempo(bpm))))

    msgs.sort(key=lambda x: (x[0], x[1]))

    mid = MidiFile(type=1, ticks_per_beat=TPB)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             time=0))

    last = 0
    for tick, _prio, msg in msgs:
        delta = tick - last
        if delta < 0:
            delta = 0
        msg.time = delta
        last = tick
        track.append(msg)

    end_tick = int(round(240.0 * TPB))
    track.append(MetaMessage('end_of_track', time=max(0, end_tick - last)))

    mid.save(path)


def main():
    rng = random.Random(20240517)
    b = Builder(rng)
    compose(b, rng)
    write_midi(b, TEMPO_POINTS, 'solo.mid')


if __name__ == '__main__':
    main()
