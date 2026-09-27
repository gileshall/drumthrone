"""
drum_solo.py - A dynamic, musical, two-minute General MIDI drum solo.
Generates 'solo.mid' on MIDI Channel 10 (0-indexed channel 9 in mido).
"""

import math
from mido import Message, MidiFile, MidiTrack, MetaMessage

# Standard GM Drum Map note constants
BASS_DRUM = 36
PEDAL_HH = 44
SNARE = 38
SIDE_STICK = 37
LOW_FLOOR_TOM = 41
HIGH_FLOOR_TOM = 43
LOW_TOM = 45
MID_TOM = 47
HIGH_TOM = 50
CLOSED_HH = 42
OPEN_HH = 46
RIDE_CYMBAL = 51
RIDE_BELL = 53
CRASH_1 = 49
CRASH_2 = 57
SPLASH = 55
CHINESE = 52
TAMBOURINE = 54
COWBELL = 56
HI_BONGO = 60
LOW_BONGO = 61
MUTE_CONGA = 62
OPEN_CONGA = 63
LOW_CONGA = 64
CABASA = 69
CLAVES = 75


class DrumEvent:
    def __init__(self, time_ticks, note, velocity, duration=110):
        self.time = time_ticks
        self.note = note
        self.velocity = max(1, min(127, int(velocity)))
        self.duration = duration


def build_drum_solo():
    events = []

    TPB = 480  # Ticks per quarter note beat (4/4 meter -> 1 bar = 1920 ticks)
    TEMPO_BPM = 118
    # 118 BPM = 1.9667 beats/sec. 60 bars = 240 beats = 122.03 seconds (~2 min)

    # 16th-note swing function (triplet-leaning funk/fusion pocket)
    def swing_offset(step_in_bar):
        # step_in_bar: 0..15 (16th notes)
        pos = step_in_bar % 4
        if pos == 1:
            return 22  # lay back the "e"
        elif pos == 3:
            return 30  # swing the "a" towards the triplet eighth
        return 0

    def add_hit(bar_idx, step_16th, note, vel, micro=0, dur=110):
        bar_start = bar_idx * 4 * TPB
        nominal = bar_start + step_16th * (TPB // 4)
        sw = swing_offset(step_16th)
        t = nominal + sw + micro
        events.append(DrumEvent(t, note, vel, dur))

    def add_triplet_hit(bar_idx, beat_idx, trip_idx, note, vel, micro=0, dur=90):
        # 6 eighth-note triplets per 2 beats (or 3 per beat)
        bar_start = bar_idx * 4 * TPB
        nominal = bar_start + beat_idx * TPB + trip_idx * (TPB // 3)
        t = nominal + micro
        events.append(DrumEvent(t, note, vel, dur))

    def add_32nd_hit(bar_idx, step_32nd, note, vel, micro=0, dur=50):
        bar_start = bar_idx * 4 * TPB
        nominal = bar_start + step_32nd * (TPB // 8)
        events.append(DrumEvent(nominal + micro, note, vel, dur))

    # Continuous Left Foot (Pedal Hi-Hat) timekeeping chick on 2 & 4
    # throughout sections where the hands and right foot groove/improvise
    for bar in range(0, 60):
        if bar not in [23, 31, 47, 54, 55, 56, 57, 58, 59]:
            add_hit(bar, 4, PEDAL_HH, 72)
            add_hit(bar, 12, PEDAL_HH, 76)

    # -------------------------------------------------------------
    # SECTION 1: Bars 0-7 - The Awakening / Theme Statement
    # Afro-Cuban/funk motif: Side-stick, congas, cowbell, subtle kick
    # -------------------------------------------------------------
    for bar in range(0, 8):
        # Kick on 1 and varied pushes
        add_hit(bar, 0, BASS_DRUM, 82)
        if bar % 2 == 0:
            add_hit(bar, 6, BASS_DRUM, 70)
            add_hit(bar, 10, BASS_DRUM, 80)
        else:
            add_hit(bar, 6, BASS_DRUM, 76)
            add_hit(bar, 14, BASS_DRUM, 84)

        # Ride Cymbal / Bell pattern (delicate, jazz-funk feel)
        ride_vel = 70 + (bar * 2)
        add_hit(bar, 0, RIDE_CYMBAL, ride_vel)
        add_hit(bar, 3, RIDE_BELL, ride_vel - 10)
        add_hit(bar, 4, RIDE_CYMBAL, ride_vel)
        add_hit(bar, 6, RIDE_BELL, ride_vel - 5)
        add_hit(bar, 8, RIDE_CYMBAL, ride_vel + 4)
        add_hit(bar, 11, RIDE_BELL, ride_vel - 8)
        add_hit(bar, 12, RIDE_CYMBAL, ride_vel)
        add_hit(bar, 14, RIDE_CYMBAL, ride_vel - 4)

        # Latin hand percussion flavor interlocked with snare side-stick
        add_hit(bar, 4, SIDE_STICK, 78)
        add_hit(bar, 10, SIDE_STICK, 84)

        if bar < 4:
            add_hit(bar, 2, CABASA, 55)
            add_hit(bar, 7, OPEN_CONGA, 68)
            add_hit(bar, 8, MUTE_CONGA, 70)
            add_hit(bar, 13, LOW_CONGA, 66)
            add_hit(bar, 15, CABASA, 50)
        else:
            # Add cowbell counter-rhythm as energy builds
            add_hit(bar, 2, COWBELL, 75)
            add_hit(bar, 7, OPEN_CONGA, 78)
            add_hit(bar, 8, COWBELL, 80)
            add_hit(bar, 11, COWBELL, 72)
            add_hit(bar, 13, LOW_CONGA, 76)
            if bar == 7:
                # Transition fill into Section 2
                add_hit(bar, 12, MID_TOM, 80)
                add_hit(bar, 13, LOW_TOM, 86)
                add_hit(bar, 14, LOW_FLOOR_TOM, 92)
                add_hit(bar, 15, HIGH_FLOOR_TOM, 98)

    # -------------------------------------------------------------
    # SECTION 2: Bars 8-15 - Linear Funk Breakdown & Ghost Note Groove
    # Intricate ghosted snare, displacement, hi-hat barking
    # -------------------------------------------------------------
    for bar in range(8, 16):
        b = bar - 8
        # Downbeat crash on entry
        if b == 0:
            add_hit(bar, 0, CRASH_1, 95)
            add_hit(bar, 0, BASS_DRUM, 100)
        else:
            add_hit(bar, 0, BASS_DRUM, 90)

        # Hi-hat flow
        for s in [0, 2, 4, 6, 8, 10, 12, 14]:
            if s == 10 and b % 2 == 1:
                add_hit(bar, s, OPEN_HH, 88)
            else:
                add_hit(bar, s, CLOSED_HH, 64 + (s % 3) * 6)

        # Main backbeat accents on 4 and 12
        add_hit(bar, 4, SNARE, 96 + b * 2)
        add_hit(bar, 12, SNARE, 100 + b * 2)

        # Ghost notes (delicate 35-48 velocity)
        add_hit(bar, 2, SNARE, 38)
        add_hit(bar, 3, SNARE, 42)
        add_hit(bar, 7, SNARE, 45)
        add_hit(bar, 9, SNARE, 40)
        add_hit(bar, 11, SNARE, 46)
        add_hit(bar, 15, SNARE, 44)

        # Syncopated bass drum kicks
        if b % 2 == 0:
            add_hit(bar, 6, BASS_DRUM, 85)
            add_hit(bar, 10, BASS_DRUM, 88)
            add_hit(bar, 13, BASS_DRUM, 78)
        else:
            add_hit(bar, 3, BASS_DRUM, 82)
            add_hit(bar, 8, BASS_DRUM, 92)
            add_hit(bar, 14, BASS_DRUM, 88)

        # Bar 15 mini-solo release (32nd note snare buzz roll to floor tom)
        if bar == 15:
            for n in range(24, 32):
                add_32nd_hit(bar, n, SNARE if n < 28 else LOW_FLOOR_TOM, 60 + (n - 24) * 8)

    # -------------------------------------------------------------
    # SECTION 3: Bars 16-23 - Melodic Tom-Tom Odyssey & Polymetric Shifts
    # Melodic 3-against-4 phrasing across high, mid, floor toms
    # -------------------------------------------------------------
    tom_seq = [HIGH_TOM, MID_TOM, LOW_TOM, HIGH_FLOOR_TOM, LOW_FLOOR_TOM]
    for bar in range(16, 24):
        b = bar - 16
        add_hit(bar, 0, CRASH_2 if b == 0 else SPLASH, 88)
        add_hit(bar, 0, BASS_DRUM, 96)

        # Dotted-eighth / 3-16th note groupings over 4/4 meter (hemiola)
        # Accenting toms at offsets: 0, 3, 6, 9, 12, 15
        for idx, s in enumerate(range(0, 16, 3)):
            t_note = tom_seq[(b * 3 + idx) % len(tom_seq)]
            add_hit(bar, s, t_note, 88 + (idx * 4))
            # Ghost snare glue between tom pulses
            if s + 1 < 16:
                add_hit(bar, s + 1, SNARE, 44)
            if s + 2 < 16 and (idx % 2 == 1):
                add_hit(bar, s + 2, BASS_DRUM, 82)

        # Four-on-the-floor kick foundation for bars 20-23
        if bar >= 20:
            for beat in range(4):
                add_hit(bar, beat * 4, BASS_DRUM, 96)

        # Bar 23 climax: 6-stroke rolls across toms leading into the half-time
        if bar == 23:
            add_hit(bar, 8, CRASH_1, 102)
            for step in range(8, 16):
                t_note = tom_seq[step % len(tom_seq)]
                add_hit(bar, step, t_note, 90 + (step - 8) * 4)
                add_hit(bar, step, BASS_DRUM if step % 2 == 1 else PEDAL_HH, 88)

    # -------------------------------------------------------------
    # SECTION 4: Bars 24-31 - Half-Time Heavy Bonham Stomp & Call/Response
    # Deep, heavy groove, giant backbeats on beat 3, thunderous fills
    # -------------------------------------------------------------
    for bar in range(24, 32):
        b = bar - 24
        # Huge crash on beat 1
        if b % 2 == 0:
            add_hit(bar, 0, CRASH_1, 108)
        else:
            add_hit(bar, 0, CHINESE, 104)

        # Devastating kick drum placement
        add_hit(bar, 0, BASS_DRUM, 114)
        add_hit(bar, 2, BASS_DRUM, 102)
        add_hit(bar, 10, BASS_DRUM, 110)
        if b % 2 == 1:
            add_hit(bar, 13, BASS_DRUM, 106)

        # Ride wash / accent on quarter notes
        for beat in range(4):
            add_hit(bar, beat * 4, RIDE_CYMBAL, 85 + (beat * 3))

        # Enormous Half-Time Snare on Beat 3 (step 8)
        add_hit(bar, 8, SNARE, 118)

        # Call and response fills on bars 27, 29, 31
        if bar == 27:
            # Triplet explosion (RLKK RLKK)
            for i in range(6):
                add_triplet_hit(bar, 2 + (i // 3), i % 3,
                                HIGH_TOM if i < 3 else LOW_FLOOR_TOM, 100 + i * 3)
        elif bar == 29:
            # Snare flam-like syncopation
            add_hit(bar, 12, SNARE, 112)
            add_hit(bar, 13, HIGH_TOM, 108)
            add_hit(bar, 14, LOW_FLOOR_TOM, 114)
            add_hit(bar, 15, BASS_DRUM, 118)
        elif bar == 31:
            # Dramatic decrescendo into the delicate polyrhythmic section
            add_hit(bar, 8, SNARE, 110)
            add_hit(bar, 10, MID_TOM, 90)
            add_hit(bar, 12, LOW_FLOOR_TOM, 75)
            add_hit(bar, 14, LOW_CONGA, 60)

    # -------------------------------------------------------------
    # SECTION 5: Bars 32-39 - Triplet Polyrhythm & Latin Bongo Dialogue
    # Triplet feel, 3:2 cross-rhythms, dynamic interplay
    # -------------------------------------------------------------
    for bar in range(32, 40):
        b = bar - 32
        add_hit(bar, 0, SPLASH if b % 2 == 0 else RIDE_BELL, 80 + b * 3)

        # Ride cymbal playing jazz-tinged triplet ostinato
        for beat in range(4):
            add_triplet_hit(bar, beat, 0, RIDE_CYMBAL, 80)
            add_triplet_hit(bar, beat, 2, RIDE_CYMBAL, 72)

        # Bongos & Congas conversing against the kick
        add_triplet_hit(bar, 0, 1, HI_BONGO, 75)
        add_triplet_hit(bar, 1, 0, LOW_BONGO, 82)
        add_triplet_hit(bar, 1, 2, OPEN_CONGA, 78)
        add_triplet_hit(bar, 2, 1, HI_BONGO, 86)
        add_triplet_hit(bar, 3, 0, MUTE_CONGA, 84)
        add_triplet_hit(bar, 3, 2, LOW_CONGA, 88)

        # Kick drum polyrhythm: dotted quarter pulses (every 3 eighth triplets)
        add_triplet_hit(bar, 0, 0, BASS_DRUM, 88)
        add_triplet_hit(bar, 1, 1, BASS_DRUM, 84)
        add_triplet_hit(bar, 2, 2, BASS_DRUM, 88)

        # Claves punctuation
        if b % 2 == 1:
            add_triplet_hit(bar, 0, 2, CLAVES, 84)
            add_triplet_hit(bar, 2, 0, CLAVES, 88)

    # -------------------------------------------------------------
    # SECTION 6: Bars 40-47 - The Virtuosic Rhythmic Storm (Rising Action)
    # Double-bass driving under fast linear cascades across the full kit
    # -------------------------------------------------------------
    for bar in range(40, 48):
        b = bar - 40
        dyn = 90 + b * 4  # building from 90 to ~120 velocity

        # Fast alternating kick & pedal hi-hat double pedal simulation
        for s in range(16):
            if s % 2 == 0:
                add_hit(bar, s, BASS_DRUM, dyn - 5)
            else:
                add_hit(bar, s, PEDAL_HH if bar < 44 else BASS_DRUM, dyn - 8)

        # Cymbal punctuations on offbeats
        add_hit(bar, 0, CRASH_1, dyn)
        add_hit(bar, 6, SPLASH, dyn - 4)
        add_hit(bar, 10, CRASH_2, dyn)
        add_hit(bar, 14, CHINESE, dyn - 2)

        # Snare and tom cascading fills over the continuous feet
        add_hit(bar, 2, HIGH_TOM, dyn - 6)
        add_hit(bar, 4, SNARE, dyn + 4)
        add_hit(bar, 8, MID_TOM, dyn - 4)
        add_hit(bar, 12, SNARE, dyn + 5)

        if bar >= 44:
            # 32nd note bursts between hands
            add_32nd_hit(bar, 26, HIGH_TOM, dyn)
            add_32nd_hit(bar, 27, LOW_TOM, dyn + 2)
            add_32nd_hit(bar, 28, HIGH_FLOOR_TOM, dyn + 4)
            add_32nd_hit(bar, 29, LOW_FLOOR_TOM, dyn + 6)

    # -------------------------------------------------------------
    # SECTION 7: Bars 48-55 - Grand Climax & Thematic Recapitulation
    # Full power, motif return, peak density and dynamic explosion
    # -------------------------------------------------------------
    for bar in range(48, 56):
        b = bar - 48
        # Crashes anchoring the bars
        add_hit(bar, 0, CRASH_1, 124)
        add_hit(bar, 8, CRASH_2, 120)

        # Theme recapitulation from Section 1, supercharged at fortissimo
        add_hit(bar, 0, BASS_DRUM, 124)
        add_hit(bar, 2, COWBELL, 116)
        add_hit(bar, 4, SNARE, 125)
        add_hit(bar, 6, BASS_DRUM, 118)
        add_hit(bar, 8, COWBELL, 118)
        add_hit(bar, 10, BASS_DRUM, 122)
        add_hit(bar, 12, SNARE, 126)
        add_hit(bar, 14, BASS_DRUM, 120)

        # Fast 16th ride bell & crash interplay
        for s in [1, 3, 5, 7, 9, 11, 13, 15]:
            add_hit(bar, s, RIDE_BELL if (s % 4 != 3) else CHINESE, 106)

        # Unstoppable fills in bars 52-55
        if bar >= 52:
            add_hit(bar, 14, HIGH_FLOOR_TOM, 120)
            add_hit(bar, 15, LOW_FLOOR_TOM, 124)

    # -------------------------------------------------------------
    # SECTION 8: Bars 56-59 - Dramatic Finale & Final Exclamation
    # Accelerando bursts, fermata-style hits, and definitive final crash
    # -------------------------------------------------------------
    # Bar 56: Ascending quadruplets across every tom and conga
    asc_notes = [LOW_CONGA, OPEN_CONGA, LOW_FLOOR_TOM, HIGH_FLOOR_TOM,
                 LOW_TOM, MID_TOM, HIGH_TOM, SNARE]
    for i, note in enumerate(asc_notes):
        step = i * 2
        add_hit(56, step, note, 100 + i * 3)
        add_hit(56, step + 1, BASS_DRUM, 95 + i * 3)

    # Bar 57: Blistering 32nd-note snare roll with accent swell
    for step_32 in range(32):
        vol = int(70 + 55 * math.sin((step_32 / 31) * (math.pi / 2)))
        add_32nd_hit(57, step_32, SNARE, vol, dur=40)
        if step_32 % 4 == 0:
            add_32nd_hit(57, step_32, BASS_DRUM, vol)

    # Bar 58: Big syncopated stabs with dramatic pauses
    # Hit on 1, & of 2, 4
    add_hit(58, 0, CRASH_1, 126)
    add_hit(58, 0, BASS_DRUM, 126)

    add_hit(58, 6, CRASH_2, 125)
    add_hit(58, 6, SNARE, 125)
    add_hit(58, 6, BASS_DRUM, 125)

    add_hit(58, 12, CHINESE, 127)
    add_hit(58, 12, SNARE, 127)
    add_hit(58, 12, BASS_DRUM, 127)

    # Bar 59: The final flam and definitive sustained crash
    # Grace note just ahead of beat 1
    add_hit(59, 0, SNARE, 70, micro=-25, dur=30)
    # Colossal unison punch on beat 1
    add_hit(59, 0, SNARE, 127, dur=360)
    add_hit(59, 0, CRASH_1, 127, dur=1920)
    add_hit(59, 0, BASS_DRUM, 127, dur=480)

    # Ringing gong/low conga resonance
    add_hit(59, 0, LOW_FLOOR_TOM, 115, dur=960)

    # Sort all events chronologically
    events.sort(key=lambda e: e.time)

    # Convert absolute-time note events into MIDI delta-time messages
    midi_file = MidiFile(ticks_per_beat=TPB)
    track = MidiTrack()
    midi_file.tracks.append(track)

    # Set Track Name and Tempo
    track.append(MetaMessage('track_name', name='GM Drum Solo', time=0))
    tempo_us = int(round(60_000_000 / TEMPO_BPM))
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))

    # Prepare interleaved note_on and note_off actions
    raw_messages = []
    for ev in events:
        raw_messages.append((ev.time, 'note_on', ev.note, ev.velocity))
        raw_messages.append((ev.time + ev.duration, 'note_off', ev.note, 0))

    # Sort by time, ensuring note_off precedes note_on at identical time
    raw_messages.sort(key=lambda m: (m[0], 0 if m[1] == 'note_off' else 1))

    # Write out with delta times on MIDI Channel 10 (channel=9 in zero-indexed mido)
    current_tick = 0
    DRUM_CHANNEL = 9
    for tick, msg_type, note, vel in raw_messages:
        delta = max(0, tick - current_tick)
        current_tick = tick
        if msg_type == 'note_on':
            track.append(Message('note_on', note=note, velocity=vel, time=delta, channel=DRUM_CHANNEL))
        else:
            track.append(Message('note_off', note=note, velocity=0, time=delta, channel=DRUM_CHANNEL))

    # Add end of track marker after final decay
    track.append(MetaMessage('end_of_track', time=TPB * 4))

    midi_file.save('solo.mid')


if __name__ == '__main__':
    build_drum_solo()
