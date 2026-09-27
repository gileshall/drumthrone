import mido
import random
import math

# Use a fixed seed to guarantee identical output on every run
random.seed(90210)

TPB = 480  # Ticks per beat

# General MIDI Drum Map
M = {
    'K': (36, 110), 'k': (36, 70),   # Kick
    'S': (38, 115), 's': (38, 45),   # Snare (Accent / Ghost)
    'X': (37, 100), 'x': (37, 65),   # Side stick
    'H': (42, 90),  'h': (42, 55),   # Closed Hihat
    'O': (46, 90),                   # Open Hihat
    'P': (44, 80),                   # Pedal Hihat
    'R': (51, 95),  'r': (51, 60),   # Ride
    'B': (53, 105), 'b': (53, 65),   # Ride Bell
    'C': (49, 115), 'D': (57, 115),  # Crash 1, Crash 2
    'L': (55, 100),                  # Splash
    'W': (56, 100),                  # Cowbell
    '1': (50, 100), '2': (48, 100), '3': (45, 100), '4': (41, 100), # Toms (Normal)
    '!': (50, 120), '@': (48, 120), '#': (45, 120), '$': (41, 120), # Toms (Accented)
    'q': (50, 55),  'w': (48, 55),  'e': (45, 55),  'y': (41, 55),  # Toms (Ghost)
    '-': None, '.': None             # Rests
}

events = []

def tick_for_position(bar, beat, swing, push):
    """
    Translates musical time to absolute MIDI ticks.
    - swing: degree of shuffle (1.0 = full triplet swing).
    - push: moves hits forward/backward in units of 10 ticks.
    """
    base_tick = (bar * 4 + beat) * TPB
    beat_32 = int(round(beat * 8))
    swing_offset = 0
    # Apply swing only to the offbeat 16th notes (e.g. 1e+a -> the 'e' and 'a')
    if beat_32 % 4 == 2:
        swing_offset = swing * 40.0 
    return base_tick + swing_offset + (push * 10)

def hit(bar, beat, note, vel, swing=0.0, push=0.0):
    """Schedules a drum strike with humanized timing and dynamics."""
    t = tick_for_position(bar, beat, swing, push)
    
    # Humanize timing (+/- 4 ticks jitter)
    t += int(random.gauss(0, 4))
    t = max(0, t)
    
    # Humanize velocity
    v = int(vel) + int(random.gauss(0, 5))
    v = max(1, min(127, v))
    
    # Ensure variables are fully integers to prevent mido TypeErrors
    events.append((int(t), int(note), int(v)))

def parse_track(track_str):
    """Parses a space-separated string of drum notation into notes."""
    if not track_str: return []
    res = []
    for token in track_str.split():
        if token in M:
            res.append(M[token])
        else:
            res.append(None)
    return res

def groove(bar, h1_str, h2_str, f1_str, f2_str, swing=0.0, push=0.0):
    """
    Generates a polyphonic drum groove mapped to the 4 limbs.
    h1 = Right Hand, h2 = Left Hand, f1 = Right Foot, f2 = Left Foot.
    Resolves complex polyrhythms natively based on string length (16 tokens = 16ths, 24 = triplets).
    """
    vel_mult = get_vel_mult(bar)
    
    limbs = [parse_track(h1_str), parse_track(h2_str), parse_track(f1_str), parse_track(f2_str)]
    
    for limb in limbs:
        steps = len(limb)
        if steps == 0: continue
        step_len = 4.0 / steps
        for i in range(steps):
            if limb[i]:
                note, vel = limb[i]
                hit(bar, i * step_len, note, vel * vel_mult, swing, push)

def get_vel_mult(bar):
    """Creates a macro dynamic arc over the entire solo."""
    if bar < 8: return 0.75
    if bar < 16: return 0.85
    if bar < 24: return 0.95
    if bar < 32: return 0.85
    if bar < 40: return 0.90
    if bar < 48: return 0.70 + (bar - 40) * (0.4 / 7.0) # Swell from 0.70 to 1.10
    if bar < 56: return 1.05
    if bar < 64: return 1.15
    return 1.25 # Maximum energy for the outro

def compose_solo():
    # --- SECTION 1: Intro (Bars 0-7) ---
    # Syncopated 16th note linear groove with side stick and ghost notes. Mysterious and building.
    for bar in range(4):
        groove(bar,
               "X . . X . X . . X . X . . . X .",
               ". . s . s . . s . s . . s s . s",
               "K . . . K . K . . . . K . . . K",
               ". . P . . . P . . . P . . . P .", swing=0.35)
    for bar in range(4, 7):
        groove(bar,
               "r . R r . R . r R . r R . . R .",
               ". . s . s . . s . s . . s s . s",
               "K . . . K . K . . . . K . . . K",
               ". . P . . . P . . . P . . . P .", swing=0.35)
    groove(7,
           "r . R r . R . . . . . . . . . .",
           ". . s . s . . s ! . @ . # . $ .",
           "K . . . K . K . . K . . K . . .",
           ". . P . . . P . . . . . . . . .", swing=0.35)

    # --- SECTION 2: Development 1 (Bars 8-15) ---
    # Ride bell, cracking center snare. Pushing the time ahead slightly.
    for bar in range(8, 12):
        h1 = "C . B . B . B . B . B . B . B ." if bar == 8 else "B . B . B . B . B . B . B . B ."
        groove(bar, h1,
               ". . s . S . . s . s s . S . . s",
               "K . . K . . K . . . K K . . K .",
               ". P . . . P . . . P . . . P . .", swing=0.35, push=2)
    for bar in range(12, 15):
        h1 = "H h O . H h O . H h O . H h O ." if bar != 12 else "C h O . H h O . H h O . H h O ."
        groove(bar, h1,
               ". . s . S . . s . s s . S . . s",
               "K . . K . . K . . . K K . . K .",
               ". . P P . . P P . . P P . . P P", swing=0.35)
    
    # 32nd note snare roll fill
    groove(15,
           "C . . . . . . . . . . . . . . .",
           "s s s s S S s s S S S S S S S S S S S S s s s s ! ! ! ! ! ! ! !",
           "K . . . . . . . . . . . K . . . K . . . . . . . . . . . K . . .",
           ". . . . . . . . . . . . . . . .", swing=0.0)

    # --- SECTION 3: Tribal Toms (Bars 16-23) ---
    # Heavy, brooding tom motif dropping the spectrum low.
    for bar in range(16, 20):
        h1 = "C . . . ! . . . 1 . . . ! . . ." if bar == 16 else "1 . . . ! . . . 1 . . . ! . . ."
        groove(bar, h1,
               ". . S . . . S . . . S . . . S .",
               "K K . K . K . K K K . K . K . K",
               ". . . . . . . . . . . . . . . .", swing=0.1)
    for bar in range(20, 23):
        h1 = "1 . . . ! . . . 1 . . . ! . . ."
        groove(bar, h1,
               ". . S . . . S . . . S . . . S .",
               "K . . . K K K K K . . . K K K K",
               ". . . . . . . . . . . . . . . .", swing=0.0)
        
    # Massive 16th-note triplet tom fill down the kit
    groove(23,
           "! . . ! ! . @ . . @ @ . # . . # # . $ . . $ $ .",
           ". S S . . S . S S . . S . S S . . S . S S . . S",
           "K . . K . . K . . K . . K . . K . . K . . K . .",
           "", swing=0.0)

    # --- SECTION 4: Ghost-Note Masterclass (Bars 24-31) ---
    # High complexity, dropping the volume and relying on finesse.
    for bar in range(24, 31):
        h1 = "H H H H H H H O H H H H H H H O" if bar != 24 else "C H H H H H H O H H H H H H H O"
        groove(bar, h1,
               ". s s . S . s . s s . . S . s s",
               "K . . K . . . K . . K K . . . .",
               ". . . . . . . . P . . . . . . .", swing=0.40)
    
    # Intricate linear fill (32nd notes)
    groove(31,
           "H . . . H . . . H . . . O . . . 1 . . . 2 . . . 3 . . . 4 . . .",
           ". S s s . S s s . S s s . S s s . s S s . s S s . s S s . s S s",
           "K . . . K . . . K . . . K . . . . . . K . . . K . . . K . . . K",
           ". . P . . . P . . . P . . . P . . . . . . . . . . . . . . . . .")

    # --- SECTION 5: Latin Syncopation (Bars 32-39) ---
    # Introduces cowbell color, dances sharply around the beat.
    for bar in range(32, 39):
        h1 = "W . W . W . W . W . W . W . W ." if bar != 32 else "C . W . W . W . W . W . W . W ."
        groove(bar, h1,
               "x . . x . x . . x . x . . x . .",
               "K . . . K . . K . . K . K . . K",
               ". . P . . . P . . . P . . . P .", swing=0.0)
    groove(39,
           "W . W . W . W . ! . . . @ . . .",
           "x . . x . x . . . S S . . S S .",
           "K . . . K . . K K . . . K . . .",
           ". . P . . . P . . . . . . . . .", swing=0.0)

    # --- SECTION 6: The "Breathe" Polyrhythm (Bars 40-47) ---
    # Trance-like dotted 8ths on the ride. Tempo slows down, settling far behind the beat.
    for bar in range(40, 47):
        h1 = "R . . R . . R . . R . . R . . R ." if bar != 40 else "C . . R . . R . . R . . R . . R ."
        groove(bar, h1,
               ". . S . . . . . S . . . . . S .",
               "K . . . . K . . . . K . . . . K",
               "P . . . P . . . P . . . P . . .", swing=0.20, push=-3)
        
    # Bar 47: Orchestral snare swell (crescendo from whisper to roar)
    groove(47, "C . . . . . . . . . . . . . . .", "", "K . . . . . . . . . . . . . . .", "")
    mult = get_vel_mult(47)
    for i in range(32):
        vel = 20 + i * 3  # Gradual swell up to max
        b = i * (4.0 / 32.0)
        hit(47, b, M['S'][0], vel * mult, swing=0.0, push=0.0)

    # --- SECTION 7: Climax 1 - Punk/Fusion Double-Time (Bars 48-55) ---
    # High energy, bashing open hats. Tempo spikes.
    for bar in range(48, 55):
        h1 = "O . O . O . O . O . O . O . O ." if bar != 48 else "C . O . O . O . O . O . O . O ."
        groove(bar, h1,
               ". S . S . S . S . S . S . S . S",
               "K . K . . K . . K . K . . K . .",
               "", swing=0.0)
    # Machine-gun tom fills
    groove(55,
           "! . . . @ . . . # . . . $ . . . ! . . . @ . . . # . . . $ . . .",
           ". S S S . S S S . S S S . S S S . S S S . S S S . S S S . S S S",
           "K . . . K . . . K . . . K . . . K . . . K . . . K . . . K . . .",
           "")

    # --- SECTION 8: Climax 2 - Half-Time Heavy Metal (Bars 56-63) ---
    # Quarter note crashes, aggressive double kick.
    for bar in range(56, 63):
        h1 = "C . C . C . C . C . C . C . C ." if bar % 2 == 0 else "D . D . D . D . D . D . D . D ."
        groove(bar, h1,
               ". . . . S . . . . . . . S . . .",
               "K K K K . . K K K K K K . . K K",
               "", push=3)
    # Insane unison flam fill playing down the kit twice
    groove(63,
           "! ! . . @ @ . . # # . . $ $ . . ! ! . . @ @ . . # # . . $ $ . .",
           ". . S S . . S S . . S S . . S S . . S S . . S S . . S S . . S S",
           "K . . . K . . . K . . . K . . . K . . . K . . . K . . . K . . .",
           "")

    # --- SECTION 9: The Outro Build (Bars 64-67) ---
    # The ultimate crescendo, filling every subdivision.
    groove(64,
           "C . . . . . . . . . . . . . . .",
           "S S S S S S S S S S S S S S S S",
           "K . K . K . K . K . K . K . K .", "")
    groove(65,
           "! . ! . @ . @ . # . # . $ . $ .",
           ". S . S . S . S . S . S . S . S",
           "K . K . K . K . K . K . K . K .", "")
    groove(66,
           "! ! ! ! @ @ @ @ # # # # $ $ $ $",
           "S S S S S S S S S S S S S S S S",
           "K K K K K K K K K K K K K K K K", "")
    groove(67,
           "C . . . C . . . C . . . C . . . C . . . C . . . C . . . C . . .",
           ". S S S . S S S . S S S . S S S . S S S . S S S . S S S . S S S",
           "K K K K K K K K K K K K K K K K K K K K K K K K K K K K K K K K", "")

    # --- The Final Hit (Bar 68) ---
    hit(68, 0, M['C'][0], 127)
    hit(68, 0, M['D'][0], 127)
    hit(68, 0, M['K'][0], 127)


def main():
    compose_solo()
    
    # Prepare MIDI file
    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    tempo_track = mido.MidiTrack()
    drum_track = mido.MidiTrack()
    mid.tracks.append(tempo_track)
    mid.tracks.append(drum_track)

    # Time signature 4/4
    tempo_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))

    # A living tempo map that breathes with the performance
    tempo_curve = [
        (0, 128),
        (16 * 4 * TPB, 131), # Push into tribal section
        (24 * 4 * TPB, 126), # Pull back for ghost notes
        (32 * 4 * TPB, 134), # Forward push for Latin
        (40 * 4 * TPB, 122), # Lay way back for polyrhythm breathe
        (48 * 4 * TPB, 144), # Adrenaline spike for punk
        (56 * 4 * TPB, 140), # Settle slightly for heavy metal groove
        (64 * 4 * TPB, 148), # Final furious sprint
    ]
    
    current_tick = 0
    for abs_tick, bpm in tempo_curve:
        delta = max(0, int(abs_tick - current_tick))
        tempo_track.append(mido.MetaMessage('set_tempo', tempo=int(mido.bpm2tempo(bpm)), time=delta))
        current_tick = abs_tick

    # Build drum track events
    midi_events = []
    for tick, note, vel in events:
        midi_events.append((tick, 'note_on', note, vel))
        # Ensure clear note_off for synthesizers to prevent voice exhaustion
        midi_events.append((tick + 40, 'note_off', note, 0))

    # Sort strictly by time, making sure note_offs happen before note_ons if times are identical
    midi_events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

    current_tick = 0
    for tick, msg_type, note, vel in midi_events:
        delta = max(0, int(tick - current_tick))
        # Channel 10 is 9 in 0-indexed standard MIDI
        if msg_type == 'note_on':
            drum_track.append(mido.Message('note_on', channel=9, note=int(note), velocity=int(vel), time=delta))
        else:
            drum_track.append(mido.Message('note_off', channel=9, note=int(note), velocity=0, time=delta))
        current_tick = tick

    mid.save('solo.mid')

if __name__ == "__main__":
    main()
