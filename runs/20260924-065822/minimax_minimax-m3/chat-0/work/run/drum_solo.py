#!/usr/bin/env python3
"""
drum_solo.py

Generates a two-minute drum solo as a General MIDI file (solo.mid)
on MIDI channel 10, using the full General MIDI percussion set (notes 35-81).

The solo develops motifs (a tom cascade that is restated and varied),
contrasts sections (Latin hand percussion, cymbal exploration, quiet
interlude, final climax), shapes dynamics from whisper to thunder, and
stays within a single drummer's reach (no more than four simultaneous
limb strikes). It is fully deterministic.
"""

import mido
from mido import Message, MidiTrack, MetaMessage

# ============================================================
# Configuration
# ============================================================
PPQ = 480                  # pulses per quarter note
CHANNEL = 9                # MIDI channel 10 (0-indexed)
BPM = 120
MPQ = int(60_000_000 / BPM)
BAR_TICKS = PPQ * 4        # ticks per bar in 4/4

# ============================================================
# General MIDI percussion pitches (notes 35-81)
# ============================================================
KICK = 36
SNARE = 38
SNARE_RIM = 37
HAT_C = 42
HAT_O = 46
HAT_P = 44
TOM_FL_LO = 41
TOM_FL_HI = 43
TOM_LO = 45
TOM_MID_LO = 47
TOM_MID_HI = 48
TOM_HI = 50
CRASH_1 = 49
RIDE = 51
CHINA = 52
RIDE_BELL = 53
TAMB = 54
SPLASH = 55
COWBELL = 56
CRASH_2 = 57
RIDE_2 = 59
BONGO_HI = 60
BONGO_LO = 61
CONGA_HI_M = 62
CONGA_HI_O = 63
CONGA_LO = 64
TIMB_HI = 65
TIMB_LO = 66
AGOGO_HI = 67
AGOGO_LO = 68
CABASA = 69
SHAKER = 70
WHISTLE = 71
GUIRO_S = 73
GUIRO_L = 74
CLAVES = 75
WOOD_HI = 76
WOOD_LO = 77
CUICA_M = 78
CUICA_O = 79
TRI_M = 80
TRI_O = 81


class Solo:
    """Collects (time, message) events for a drum solo."""

    def __init__(self):
        self.events = []  # list of (absolute_time, mido.Message)

    def hit(self, t, pitch, vel, dur=60):
        """Append a drum hit at absolute time t."""
        self.events.append(
            (t, Message('note_on', channel=CHANNEL,
                        note=pitch, velocity=vel, time=0))
        )
        self.events.append(
            (t + dur, Message('note_off', channel=CHANNEL,
                              note=pitch, velocity=vel, time=0))
        )

    def save(self, filename='solo.mid'):
        """Write the collected events as a General MIDI file."""
        sorted_events = sorted(
            self.events,
            key=lambda e: (e[0], 0 if e[1].is_meta else 1),
        )
        mid = mido.MidiFile(ticks_per_beat=PPQ)
        track = MidiTrack()
        track.append(MetaMessage('track_name', name='Drum Solo', time=0))
        track.append(MetaMessage('time_signature',
                                  numerator=4, denominator=4, time=0))
        track.append(MetaMessage('set_tempo', tempo=MPQ, time=0))
        current = 0
        for t, msg in sorted_events:
            track.append(msg.copy(time=max(0, t - current)))
            current = t
        mid.tracks.append(track)
        mid.save(filename)


# Tick helpers
def B(n):     return n * PPQ          # n beats from bar start
def bar_t(n): return n * BAR_TICKS    # absolute tick of bar n


def compose():
    s = Solo()

    # ============================================================
    # BARS 1-4: establish quarter-note groove (subtle backbeat push)
    # ============================================================
    for n in range(4):
        t0 = bar_t(n)
        for bt in range(4):
            t = t0 + B(bt) - (10 if bt in (1, 3) else 0)
            s.hit(t, HAT_C, 65, 60)
        s.hit(t0 + B(0), KICK, 85, 200)
        s.hit(t0 + B(2), KICK, 80, 200)
        s.hit(t0 + B(1) - 10, SNARE, 88, 120)
        s.hit(t0 + B(3) - 10, SNARE, 88, 120)

    # ============================================================
    # BARS 5-8: add ghost notes on the offbeats
    # ============================================================
    for n in range(4, 8):
        t0 = bar_t(n)
        for bt in range(4):
            t = t0 + B(bt) - (10 if bt in (1, 3) else 0)
            s.hit(t, HAT_C, 65, 60)
        s.hit(t0 + B(0), KICK, 85, 200)
        s.hit(t0 + B(2), KICK, 80, 200)
        s.hit(t0 + B(1) - 10, SNARE, 88, 120)
        s.hit(t0 + B(3) - 10, SNARE, 88, 120)
        s.hit(t0 + B(0) + 240, SNARE, 35, 50)
        s.hit(t0 + B(2) + 240, SNARE, 35, 50)

    # ============================================================
    # BARS 9-12: hi-hat opens to 8ths (with swing)
    # ============================================================
    for n in range(8, 12):
        t0 = bar_t(n)
        for i in range(8):
            t = t0 + i * 240 + (60 if i % 2 == 1 else 0)
            v = 60 + (8 if i in (0, 4) else 0)
            s.hit(t, HAT_C, v, 40)
        s.hit(t0 + B(0), KICK, 85, 200)
        s.hit(t0 + B(2), KICK, 80, 200)
        if n >= 10:
            s.hit(t0 + B(1) + 240, KICK, 75, 100)
        s.hit(t0 + B(1) - 10, SNARE, 88, 120)
        s.hit(t0 + B(3) - 10, SNARE, 88, 120)
        if n == 11:
            s.hit(t0 + B(3), CRASH_1, 75, 400)
            s.hit(t0 + B(3) + 320, HAT_P, 75, 80)

    # ============================================================
    # BARS 13-16: Theme A - tom cascade (the main motif)
    # ============================================================
    cascade = [TOM_HI, TOM_MID_HI, TOM_MID_LO, TOM_LO,
               TOM_FL_LO, TOM_LO, TOM_MID_LO, TOM_MID_HI]
    for n in range(12, 16):
        t0 = bar_t(n)
        for i, drum in enumerate(cascade):
            t = t0 + i * 240 + (40 if i % 2 == 1 else 0)
            v = 80 + (5 if i in (0, 4) else 0)
            s.hit(t, drum, v, 200)
        s.hit(t0 + B(0), KICK, 85, 200)
        s.hit(t0 + B(2), KICK, 80, 200)
        s.hit(t0 + B(1) - 5, SNARE, 80, 100)
        s.hit(t0 + B(3) - 5, SNARE, 80, 100)
        for bt in range(4):
            s.hit(t0 + B(bt) + 240, HAT_P, 70, 50)
        if n == 15:
            s.hit(t0 + B(3), CRASH_1, 80, 400)

    # ============================================================
    # BARS 17-20: theme variation - rim clicks + ride bell
    # ============================================================
    for n in range(16, 20):
        t0 = bar_t(n)
        for bt in range(4):
            t = t0 + B(bt) + 240 + (30 if bt in (1, 3) else 0)
            v = 75 + (5 if bt in (0, 2) else 0)
            s.hit(t, SNARE_RIM, v, 100)
        for bt in range(4):
            s.hit(t0 + B(bt), RIDE_BELL, 75, 250)
        s.hit(t0 + B(1) - 5, SNARE, 80, 120)
        s.hit(t0 + B(3) - 5, SNARE, 80, 120)
        s.hit(t0 + B(0), KICK, 75, 200)
        s.hit(t0 + B(2), KICK, 70, 200)
        if n == 19:
            s.hit(t0 + B(3), CRASH_1, 75, 400)

    # ============================================================
    # BARS 21-24: Latin hand percussion (congas, timbale, shaker)
    # ============================================================
    for n in range(20, 24):
        t0 = bar_t(n)
        if n < 23:
            # tumbao: heel-tone-tip pattern on congas
            s.hit(t0 + B(0), CONGA_LO, 80, 200)
            s.hit(t0 + B(0) + 240, CONGA_HI_O, 85, 150)
            s.hit(t0 + B(1), CONGA_HI_M, 70, 100)
            s.hit(t0 + B(1) + 240, CONGA_LO, 75, 150)
            s.hit(t0 + B(2), CONGA_HI_O, 80, 150)
            s.hit(t0 + B(2) + 240, CONGA_LO, 75, 150)
            s.hit(t0 + B(3), CONGA_HI_M, 70, 100)
        for i in range(8):
            t = t0 + i * 240 + (60 if i % 2 == 1 else 0)
            v = 50 + (5 if i in (0, 4) else 0)
            s.hit(t, SHAKER, v, 40)
        if n == 21:
            s.hit(t0 + B(0) + 120, TIMB_HI, 80, 150)
            s.hit(t0 + B(2) + 120, TIMB_HI, 80, 150)
        elif n == 22:
            s.hit(t0 + B(1) + 120, TIMB_LO, 80, 150)
            s.hit(t0 + B(3) + 120, TIMB_LO, 80, 150)
            s.hit(t0 + B(0) + 360, CLAVES, 70, 100)
        if n == 23:
            # build back to kit
            s.hit(t0 + B(0), CRASH_1, 70, 400)
            s.hit(t0 + B(0), KICK, 80, 200)
            s.hit(t0 + B(2), KICK, 75, 200)
            s.hit(t0 + B(3), TIMB_HI, 90, 200)
            s.hit(t0 + B(2), CONGA_HI_O, 85, 150)
            s.hit(t0 + B(3), CONGA_LO, 80, 200)
        s.hit(t0 + B(1) - 5, SNARE, 50, 80)
        s.hit(t0 + B(3) - 5, SNARE, 50, 80)

    # ============================================================
    # BARS 25-28: cymbal exploration (sparse, tense)
    # ============================================================
    for n in range(24, 28):
        t0 = bar_t(n)
        s.hit(t0 + B(0), KICK, 75, 200)
        s.hit(t0 + B(1) - 5, SNARE, 70, 100)
        s.hit(t0 + B(2), KICK, 70, 200)
        s.hit(t0 + B(3) - 5, SNARE, 70, 100)
        if n == 24:
            s.hit(t0 + B(0), SPLASH, 75, 500)
            for bt in (0, 2):
                s.hit(t0 + B(bt), RIDE_BELL, 75, 300)
                for i in range(2):
                    s.hit(t0 + B(bt) + (i + 1) * 240, RIDE, 65, 200)
        elif n == 25:
            s.hit(t0 + B(0), CHINA, 80, 600)
            for bt in range(4):
                s.hit(t0 + B(bt), RIDE_BELL, 70, 250)
            s.hit(t0 + B(1), COWBELL, 70, 200)
            s.hit(t0 + B(3), COWBELL, 70, 200)
        elif n == 26:
            for bt in range(4):
                t = t0 + B(bt) - (5 if bt in (1, 3) else 0)
                s.hit(t, RIDE_BELL, 70, 300)
            for i in range(4):
                t = t0 + B(2) + i * 120
                v = 50 + i * 5
                s.hit(t, SNARE, v, 50)
        elif n == 27:
            for i in range(8):
                t = t0 + i * 240 + (60 if i % 2 == 1 else 0)
                v = 70 + (5 if i in (0, 4) else 0)
                s.hit(t, RIDE, v, 200)
            s.hit(t0 + B(0), SPLASH, 75, 400)
            s.hit(t0 + B(2), SPLASH, 70, 400)
            s.hit(t0 + B(1), COWBELL, 75, 200)
            s.hit(t0 + B(3), COWBELL, 75, 200)

    # ============================================================
    # BARS 29-32: building back up (crescendo)
    # ============================================================
    for n in range(28, 32):
        t0 = bar_t(n)
        intensity = (n - 28) / 3
        for j in range(8):
            t = t0 + j * 240 + (60 if j % 2 == 1 else 0)
            v = int(60 + 20 * intensity)
            s.hit(t, HAT_C, v, 40)
        s.hit(t0 + B(0), KICK, int(85 + 10 * intensity), 200)
        s.hit(t0 + B(2), KICK, int(80 + 10 * intensity), 200)
        if intensity >= 0.5:
            s.hit(t0 + B(1) + 240, KICK, int(75 + 10 * intensity), 100)
        if intensity >= 1.0:
            s.hit(t0 + B(3) + 240, KICK, int(75 + 10 * intensity), 100)
        s.hit(t0 + B(1) - 10, SNARE, 90, 120)
        s.hit(t0 + B(3) - 10, SNARE, 90, 120)
        if intensity >= 0.5:
            s.hit(t0 + B(3) - 240, SNARE, 40, 50)
        if intensity >= 1.0:
            s.hit(t0 + B(2) + 320, SNARE, 45, 50)
        for bt in range(4):
            s.hit(t0 + B(bt), RIDE, int(70 + 10 * intensity), 60)

    # ============================================================
    # BARS 33-36: first climax
    # ============================================================
    for n in range(32, 36):
        t0 = bar_t(n)
        for i in range(8):
            t = t0 + i * 240 + (50 if i % 2 == 1 else 0)
            v = 70 + (10 if i in (1, 5) else 0)
            s.hit(t, HAT_C, v, 40)
        s.hit(t0 + B(0), KICK, 100, 250)
        s.hit(t0 + B(1) + 240, KICK, 90, 100)
        s.hit(t0 + B(2), KICK, 95, 200)
        s.hit(t0 + B(3) + 240, KICK, 90, 100)
        s.hit(t0 + B(1) - 10, SNARE, 100, 150)
        s.hit(t0 + B(3) - 10, SNARE, 100, 150)
        s.hit(t0 + B(0) + 240, SNARE, 70, 80)
        s.hit(t0 + B(2) + 240, SNARE, 70, 80)
        if n in (33, 35):
            for i in range(4):
                t = t0 + B(3) + i * 60
                v = 60 + i * 10
                s.hit(t, SNARE, v, 50)
        s.hit(t0 + B(0), CRASH_1, 90, 500)
        if n == 35:
            s.hit(t0 + B(3), CRASH_1, 95, 600)

    # ============================================================
    # BARS 37-40: theme return in high register
    # ============================================================
    for n in range(36, 40):
        t0 = bar_t(n)
        high_cascade = [TOM_HI, TOM_MID_HI, TOM_HI, TOM_MID_HI,
                        TOM_HI, TOM_MID_HI, TOM_HI, TOM_MID_HI]
        for i, drum in enumerate(high_cascade):
            t = t0 + i * 240
            v = 85 + (5 if i % 2 == 0 else 0)
            s.hit(t, drum, v, 200)
        s.hit(t0 + B(1) - 10, SNARE, 90, 120)
        s.hit(t0 + B(3) - 10, SNARE, 90, 120)
        s.hit(t0 + B(0), KICK, 90, 200)
        s.hit(t0 + B(2), KICK, 85, 200)
        for bt in range(4):
            s.hit(t0 + B(bt) + 240, HAT_P, 70, 50)

    # ============================================================
    # BARS 41-44: linear 16th-note playing
    # ============================================================
    linear_drums = [
        ([TOM_HI, TOM_MID_HI, TOM_MID_LO, TOM_LO,
          TOM_FL_LO, TOM_LO, TOM_MID_LO, TOM_MID_HI] * 2),
        ([TOM_HI, TOM_MID_HI, TOM_HI, TOM_MID_LO] * 4),
        ([TOM_HI, TOM_MID_HI, TOM_MID_LO, TOM_LO] * 4),
        ([TOM_MID_HI, TOM_MID_LO, TOM_LO, TOM_FL_LO] * 4),
    ]
    for n in range(40, 44):
        t0 = bar_t(n)
        for i, drum in enumerate(linear_drums[n - 40]):
            t = t0 + i * 120
            v = 80 + (5 if i % 4 == 0 else 0)
            s.hit(t, drum, v, 150)
        s.hit(t0 + B(0), KICK, 85, 200)
        s.hit(t0 + B(2), KICK, 80, 200)
        s.hit(t0 + B(1) + 60, SNARE, 85, 100)
        s.hit(t0 + B(3) + 60, SNARE, 85, 100)

    # ============================================================
    # BARS 45-48: peak intensity (16th-note blast)
    # ============================================================
    blast_drums = [TOM_HI, TOM_MID_HI, TOM_MID_LO, TOM_LO,
                   TOM_FL_LO, TOM_LO, TOM_MID_LO, TOM_MID_HI]
    for n in range(44, 48):
        t0 = bar_t(n)
        intensity = (n - 43) / 4
        crash_vel = int(95 + 15 * intensity)
        s.hit(t0, CRASH_1, crash_vel, 600)
        if n >= 46:
            s.hit(t0, CRASH_2, crash_vel - 10, 600)
        for i in range(1, 16):
            t = t0 + i * 120
            if i % 2 == 1:
                drum = blast_drums[(i - 1) // 2]
            else:
                drum = SNARE
            v = int(85 + 15 * intensity)
            s.hit(t, drum, v, 120)
        for bt in range(4):
            s.hit(t0 + B(bt), KICK, int(95 + 20 * intensity), 200)
            if bt < 3:
                s.hit(t0 + B(bt) + 240, KICK, int(85 + 15 * intensity), 100)
        for bt in range(4):
            s.hit(t0 + B(bt) + 240, HAT_P, int(70 + 10 * intensity), 60)
        if n == 47:
            s.hit(t0 + 1860, CRASH_2, 110, 700)

    # ============================================================
    # BARS 49-52: decrescendo (brushy feel via shakers)
    # ============================================================
    for n in range(48, 52):
        t0 = bar_t(n)
        intensity = 1 - (n - 48) / 3
        if intensity > 0.3:
            s.hit(t0 + B(0), KICK, int(85 * intensity), 200)
            s.hit(t0 + B(1) - 10, SNARE, int(85 * intensity), 120)
            s.hit(t0 + B(2), KICK, int(80 * intensity), 200)
            s.hit(t0 + B(3) - 10, SNARE, int(85 * intensity), 120)
        for i in range(16):
            t = t0 + i * 120
            v = int(45 + 10 * intensity)
            s.hit(t, SHAKER, v, 40)
        if intensity > 0.7:
            for i, drum in enumerate([TOM_HI, TOM_MID_HI, TOM_MID_LO]):
                s.hit(t0 + B(2) + i * 120, drum, int(75 * intensity), 200)
        elif intensity > 0.3:
            for i, drum in enumerate([TOM_HI, TOM_MID_HI]):
                s.hit(t0 + B(2) + i * 120, drum, int(70 * intensity), 200)
        if intensity > 0.5:
            s.hit(t0 + B(0), CRASH_1, int(75 * intensity), 400)

    # ============================================================
    # BARS 53-56: quiet interlude
    # ============================================================
    for n in range(52, 56):
        t0 = bar_t(n)
        for i in range(16):
            t = t0 + i * 120
            v = 40 + (5 if i % 4 == 0 else 0)
            s.hit(t, SHAKER, v, 40)
        s.hit(t0 + B(0), KICK, 50, 150)
        s.hit(t0 + B(2), KICK, 50, 150)
        s.hit(t0 + B(0), TRI_O, 60, 400)
        s.hit(t0 + B(2), TRI_O, 55, 400)
        if n == 53:
            s.hit(t0 + B(0), RIDE_BELL, 60, 300)
            s.hit(t0 + B(2), RIDE_BELL, 55, 300)
        elif n == 54:
            s.hit(t0 + B(0), CHINA, 60, 500)
        elif n == 55:
            s.hit(t0 + B(0), SPLASH, 65, 400)
            s.hit(t0 + B(2), SPLASH, 60, 400)
            s.hit(t0 + B(1), SNARE, 50, 100)
            s.hit(t0 + B(3), SNARE, 50, 100)

    # ============================================================
    # BARS 57-60: final build and climactic finish
    # ============================================================
    for n in range(56, 60):
        t0 = bar_t(n)
        intensity = (n - 56) / 3
        s.hit(t0 + B(0), CRASH_1, int(85 + 30 * intensity), 700)
        s.hit(t0 + B(0), KICK, int(95 + 15 * intensity), 250)
        s.hit(t0 + B(2), KICK, int(90 + 15 * intensity), 200)
        if intensity >= 0.5:
            s.hit(t0 + B(1) + 240, KICK, int(80 + 15 * intensity), 100)
        s.hit(t0 + B(1) - 10, SNARE, int(95 + 10 * intensity), 120)
        s.hit(t0 + B(3) - 10, SNARE, int(95 + 10 * intensity), 120)
        for i in range(8):
            t = t0 + i * 240 + (50 if i % 2 == 1 else 0)
            v = int(60 + 20 * intensity)
            s.hit(t, HAT_C, v, 40)
        if n == 58:
            for i in range(8):
                t = t0 + B(2) + i * 120
                drum = [TOM_MID_HI, TOM_MID_LO, TOM_LO, TOM_FL_LO,
                        TOM_FL_LO, TOM_LO, TOM_MID_LO, TOM_MID_HI][i]
                v = 80 + i * 5
                s.hit(t, drum, v, 150)
        elif n == 59:
            # Big final: crash, kick, then a 23-hit 16th blast,
            # then a massive final crash with tom decay.
            s.hit(t0 + 0, CRASH_1, 100, 700)
            s.hit(t0 + 0, KICK, 110, 300)
            for i in range(1, 24):
                t = t0 + i * 60
                if i % 2 == 1:
                    idx = ((i - 1) // 2) % 8
                    drum = blast_drums[idx]
                else:
                    drum = SNARE
                v = 90 + (10 if i >= 12 else 0)
                s.hit(t, drum, v, 100)
            for bt in range(3):
                s.hit(t0 + B(bt), HAT_P, 80, 50)
            s.hit(t0 + B(3), CRASH_1, 120, 900)
            s.hit(t0 + B(3), CRASH_2, 100, 900)
            s.hit(t0 + B(3), KICK, 110, 300)
            for i, drum in enumerate([TOM_FL_LO, TOM_LO, TOM_MID_LO]):
                t = t0 + B(3) + 60 + i * 60
                v = 100 - i * 10
                s.hit(t, drum, v, 200)
            s.hit(t0 + B(3) + 240, SNARE, 100, 200)

    return s


if __name__ == '__main__':
    compose().save('solo.mid')
