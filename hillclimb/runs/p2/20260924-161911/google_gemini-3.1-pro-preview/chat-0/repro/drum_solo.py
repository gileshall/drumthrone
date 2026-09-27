import mido
import random

# Ensure identical generation on every run
random.seed(42)

# --- GM Percussion Key Map (Channel 10) ---
K   = 36 # Kick (Bass Drum 1)
SS  = 37 # Side Stick
S   = 38 # Acoustic Snare
RS  = 40 # Electric Snare (Rimshot)
T6  = 41 # Low Floor Tom
CH  = 42 # Closed Hi-Hat
T5  = 43 # High Floor Tom
PH  = 44 # Pedal Hi-Hat
T4  = 45 # Low Tom
OH  = 46 # Open Hi-Hat
T3  = 47 # Low-Mid Tom
T2  = 48 # Hi-Mid Tom
CR1 = 49 # Crash Cymbal 1
T1  = 50 # High Tom
RC  = 51 # Ride Cymbal 1
CHN = 52 # Chinese Cymbal
RB  = 53 # Ride Bell
SPL = 55 # Splash Cymbal
CB  = 56 # Cowbell
CR2 = 57 # Crash Cymbal 2

events = []

def get_tick(beat):
    """Converts a beat number (float) to absolute MIDI ticks with micro-timing."""
    tick = int(beat * 480)
    frac = beat % 0.5
    
    # Micro-timing: swing the 16th note offbeats slightly by pushing them late
    if abs(frac - 0.25) < 0.05:
        tick += 20 
        
    # Add a tiny bit of humanizing jitter
    jitter = int(random.uniform(-3, 3))
    return max(0, tick + jitter)

# Base velocity mappings for dynamic layers
v_map = {'FF': 127, 'F': 110, 'A': 100, 'MF': 85, 'MP': 75, 'P': 60, 'PP': 40, 'G': 28}

def get_vel(v_type, dyn_mult=1.0):
    """Gets randomized human velocity based on musical marking."""
    base = v_map.get(v_type, 80) * dyn_mult
    val = int(base + random.uniform(-5, 5))
    return max(1, min(127, val))

def hit(beat, note, v_type, limb, dyn_mult=1.0):
    """Registers a drum hit. Limb: 0=Hand, 1=Foot."""
    tick = get_tick(beat)
    vel = get_vel(v_type, dyn_mult)
    events.append((tick, note, vel, limb))

def parse_grid(start_beat, step_size, grid, dyn_mult=1.0):
    """Parses visual grid strings into musical events."""
    for note, pattern in grid.items():
        chars = pattern.replace(' ', '').replace('|', '')
        for i, char in enumerate(chars):
            if char != '.':
                v_type = 'MF'
                if char == 'A': v_type = 'A'
                elif char == '^': v_type = 'FF'
                elif char == 'x': v_type = 'MF'
                elif char == 'p': v_type = 'P'
                elif char == 'g': v_type = 'G'
                
                limb = 1 if note in [K, PH] else 0
                b = start_beat + i * step_size
                hit(b, note, v_type, limb, dyn_mult)

# =====================================================================
# COMPOSE THE DRUM SOLO (68 Bars @ 135 BPM = ~2 minutes)
# =====================================================================

for bar in range(68):
    b = bar * 4.0 
    
    # --- BARS 0-7: The Intro (Sparse, establishing the pocket) ---
    if 0 <= bar < 8:
        if bar < 4:
            parse_grid(b, 0.25, {
                PH: ". . . . x . . . . . . . x . . . ",
                SS: ". . . . . . x . . . x . . . . . "
            })
        else:
            parse_grid(b, 0.25, {
                PH: ". . . . x . . . . . . . x . . . ",
                SS: "p . . . . . x . . p x . . . x . ",
                K:  "A . . . . . . . x . . . . . . . "
            })
            if bar == 7: # Tom fill into the groove
                hit(b+3.00, T1, 'F', 0); hit(b+3.25, T2, 'F', 0)
                hit(b+3.50, T3, 'F', 0); hit(b+3.75, T4, 'F', 0)

    # --- BARS 8-15: Motif A - Funky Groove ---
    elif 8 <= bar < 16:
        if bar == 8: hit(b, CR1, 'F', 0) 
        
        if bar % 4 != 3:
            parse_grid(b, 0.25, {
                CH: "A p x p A p x p A p x p A p x p ", # Push-pull 16th hi-hats
                S:  ". . g . A . g g . g g . A . g . ",
                K:  "A . . g . . . . A . g . . . . . "
            })
        else: # Fill variations
            parse_grid(b, 0.25, {
                CH: "A p x p A p x p . . . . . . . . ",
                S:  ". . g . A . g g A g A g . . . . ",
                K:  "A . . g . . . . . . . . . . . . ",
                T1: ". . . . . . . . . . . . A g . . ",
                T2: ". . . . . . . . . . . . . . A g "
            })
            if bar == 15: # Lead-in to Ride section (32nd notes)
                parse_grid(b+2, 0.125, {
                    S:  "A g g g A g g g . . . . . . . . ",
                    T2: ". . . . . . . . A g g g . . . . ",
                    T4: ". . . . . . . . . . . . A g g g "
                })

    # --- BARS 16-23: Ride Cymbal Groove & Syncopations ---
    elif 16 <= bar < 24:
        if bar in [16, 20]: hit(b, CR2, 'F', 0)
        
        if bar % 4 != 3:
            parse_grid(b, 0.25, {
                RC: "x . x x x . x x x . x x x . x x ",
                RB: ". . . . . . A . . . . . . . A . ",
                S:  ". g g . A . . g . g g . A . g . ",
                K:  "A . . . . g . . A . . g . . . g "
            })
        else:
            parse_grid(b, 0.25, {
                RC: "x . x x x . x x . . . . . . . . ",
                S:  ". g g . A . . g . . . . . . . . ",
                K:  "A . . . . g . . . . . . . . . . "
            })
            # Syncopated setup hits
            hit(b+2.00, S, 'F', 0); hit(b+2.00, CR1, 'F', 0); hit(b+2.00, K, 'F', 1)
            hit(b+2.75, S, 'F', 0); hit(b+2.75, CR2, 'F', 0); hit(b+2.75, K, 'F', 1)
            hit(b+3.50, S, 'F', 0); hit(b+3.50, CR1, 'F', 0); hit(b+3.50, K, 'F', 1)

    # --- BARS 24-31: Linear Drumming / Gospel Chops Section ---
    elif 24 <= bar < 32:
        if bar == 24: hit(b, CR1, 'F', 0)
        
        if bar % 2 == 0:
            parse_grid(b, 0.25, {
                RC: "A . x . A . x . A . x . A . x . ",
                S:  ". g . g A . g . . g . g A . g . ",
                K:  "A . A . . g . A A . A . . g . A "
            })
        else:
            parse_grid(b, 0.25, { RC: "x . x . ", S: ". g A . ", K: "A . . g " })
            # 32nd note linear fill (R L K K R L K K...)
            for i in range(6):
                t = b + 1.0 + (i * 0.5)
                # Orchestrating hands around the kit
                hit(t + 0.000, T1 if i%3==0 else (S if i%3==1 else T3), 'F', 0)
                hit(t + 0.125, T2 if i%3==0 else (T1 if i%3==1 else T4), 'MF', 0)
                hit(t + 0.250, K, 'F', 1)
                hit(t + 0.375, K, 'F', 1)

    # --- BARS 32-35: Latin/Percussion Interplay (Cascara / Tumbao) ---
    elif 32 <= bar < 36:
        if bar == 32: hit(b, CR2, 'F', 0)
        
        if bar % 4 != 3:
            parse_grid(b, 0.25, {
                CB: "A . x . A . x x A . x . A . x x ", 
                SS: ". . . x . . x . . . x . . x . . ", 
                K:  "A . . . . . A . . . A . . . . . ", 
                PH: ". . x . . . x . . . x . . . x . "
            })
        else:
            parse_grid(b, 0.25, {
                CB: "A . x . A . x x . . . . . . . . ",
                SS: ". . . x . . x . . . . . . . . . ",
                K:  "A . . . . . A . . . . . . . . . ",
                T3: ". . . . . . . . A . . A . . . . ",
                T5: ". . . . . . . . . A . . A . . . ",
                T6: ". . . . . . . . . . A . . A . A "
            })

    # --- BARS 36-39: Motif B - Tribal Tom Groove (Building density) ---
    elif 36 <= bar < 40:
        if bar == 36: hit(b, CR1, 'F', 0)
        
        dyn = 0.9 + (bar-36)*0.1 # Crescendo through the section
        parse_grid(b, 0.25, {
            T4: "A . x . A . x . A . x . A . x . ",
            T6: ". x . x . x . x . x . x . x . x ",
            K:  "A . . . A . . . A . . . A . . . "
        }, dyn_mult=dyn)

    # --- BARS 40-47: Polyrhythmic Tension Build & Heavy Sweeps ---
    elif 40 <= bar < 48:
        if bar < 44:
            # 3-over-4 Polyrhythm: Snare -> Kick -> Kick
            for i in range(16):
                t = b + i * 0.25
                dyn = 0.6 + 0.4 * (((bar-40)*16 + i) / 64.0)
                
                if i % 3 == 0: hit(t, S, 'A', 0, dyn_mult=dyn)
                else: hit(t, K, 'A', 1, dyn_mult=dyn)
                
                # Crash anchor on downbeats
                if i % 4 == 0: hit(t, CR1 if (bar%2==0) else CR2, 'MF', 0, dyn_mult=dyn)
        else:
            # 16th Note Heavy Tom Sweeps with Syncopated Double Kicks
            for i in range(16):
                t = b + i * 0.25
                dyn = 0.8 + 0.4 * (((bar-44)*16 + i) / 64.0)
                
                if i % 2 == 0: hit(t, K, 'A', 1, dyn_mult=dyn)
                if i % 4 == 3: hit(t, K, 'F', 1, dyn_mult=dyn)

                cycle = i % 8
                if cycle < 2: n = S
                elif cycle < 4: n = T1
                elif cycle < 6: n = T3
                else: n = T5
                
                hit(t, n, 'F', 0, dyn_mult=dyn)

    # --- BARS 48-51: The Drop / Breakdown (Extreme Dynamics Contrast) ---
    elif 48 <= bar < 52:
        if bar == 48: hit(b, SPL, 'MF', 0) # Splash drop
        
        parse_grid(b, 0.25, {
            CH: "p . p . p . p . p . p . p . p . ",
            S:  "g g g g A g g g g g g g A g g g ",
            K:  "p . . . . . . . p . . . . . . . "
        }, dyn_mult=0.45) # Keep it extremely quiet

    # --- BARS 52-55: The Roll Build-Up ---
    elif 52 <= bar < 56:
        # Fast 32nd note snare crescendo
        for i in range(32):
            t = b + i * 0.125
            dyn = 0.4 + 0.8 * (((bar - 52)*32 + i) / 128.0) 
            hit(t, S, 'MF', 0, dyn_mult=dyn)
            if i % 4 == 0: hit(t, K, 'F', 1, dyn_mult=dyn)
            if i % 8 == 0: hit(t, CH, 'MF', 0, dyn_mult=dyn)

    # --- BARS 56-63: The Climax (Shredding & Half-time Blast) ---
    elif 56 <= bar < 64:
        dyn = 1.15
        if bar % 2 == 0:
            parse_grid(b, 0.25, {
                CR1: "A . . . A . . . A . . . A . . . ",
                CHN: ". . A . . . A . . . A . . . A . ", # Interplay with China
                S:   ". . . . A . . . . . . . A . . . ",
                K:   "A . x . A . x . A x x . A . x . "
            }, dyn_mult=dyn)
        else:
            if bar != 63:
                parse_grid(b, 0.25, {
                    CR1: "A . . . A . . . A . . . A . . . ",
                    S:   ". . . . A . . . . g g . A . g g ",
                    K:   "A x x . A . x . A . . . A . . . "
                }, dyn_mult=dyn)
            else:
                # 16th-note Triplet fill shredding into finale
                for i in range(24): 
                    t = b + i * (4.0 / 24.0) # Triplet timing
                    n = S if i < 6 else (T1 if i < 12 else (T3 if i < 18 else T5))
                    hit(t, n, 'A', 0, dyn_mult=1.2)
                    if i % 2 == 0: hit(t, K, 'A', 1, dyn_mult=1.2)

    # --- BARS 64-67: The Grand Finale (Heavy Rolls & Shots) ---
    elif 64 <= bar < 68:
        if bar < 66:
            # 32nd note chaotic thunder
            for i in range(32):
                t = b + i * 0.125
                if i % 8 == 0: 
                    hit(t, CR1, 'A', 0, dyn_mult=1.25) 
                    hit(t, S, 'A', 0, dyn_mult=1.25)   
                else:
                    hit(t, S if i%2==0 else T6, 'A', 0, dyn_mult=1.25)
                if i % 4 == 0: hit(t, K, 'A', 1, dyn_mult=1.25) 
        elif bar == 66:
            # Broken accented shots
            hit(b+0.0, CR1, 'F', 0); hit(b+0.0, S, 'F', 0); hit(b+0.0, K, 'F', 1)
            hit(b+1.5, CR2, 'F', 0); hit(b+1.5, S, 'F', 0); hit(b+1.5, K, 'F', 1)
            hit(b+3.0, CR1, 'F', 0); hit(b+3.0, S, 'F', 0); hit(b+3.0, K, 'F', 1)
        elif bar == 67:
            # The ultimate fast descending sweep
            for i in range(16):
                t = b + i * 0.25
                n = S if i < 4 else (T1 if i < 8 else (T3 if i < 12 else T5))
                hit(t, n, 'FF', 0, dyn_mult=1.3)
                hit(t, K, 'FF', 1, dyn_mult=1.3)

# --- BAR 68: The Final Hit (Land with energy!) ---
b_final = 68 * 4.0
hit(b_final, CR1, 'FF', 0, dyn_mult=1.5)
hit(b_final, CR2, 'FF', 0, dyn_mult=1.5)
hit(b_final, K, 'FF', 1, dyn_mult=1.5)

# Add a silent ghost note a bit later to let the crash ring out completely
events.append((get_tick(b_final + 8.0), K, 0, 1))

# =====================================================================
# PLAYABILITY ENGINE (Strictly enforce max 2 hands + 2 feet per hit)
# =====================================================================

# Sort events strictly by absolute tick time
events.sort(key=lambda x: x[0])

# Group events that occur simultaneously (within a 10-tick window)
grouped_events = []
if events:
    current_group = [events[0]]
    for e in events[1:]:
        if e[0] - current_group[0][0] <= 10:
            current_group.append(e)
        else:
            grouped_events.append(current_group)
            current_group = [e]
    if current_group:
        grouped_events.append(current_group)

filtered_events = []
for group in grouped_events:
    hands = [e for e in group if e[3] == 0]
    feet  = [e for e in group if e[3] == 1]
    
    # If the composition demands >2 hands or >2 feet at once, 
    # keep the ones with the highest velocity (musical priority)
    hands.sort(key=lambda x: x[2], reverse=True)
    feet.sort(key=lambda x: x[2], reverse=True)
    
    filtered_events.extend(hands[:2])
    filtered_events.extend(feet[:2])

# =====================================================================
# MIDI GENERATION
# =====================================================================

mid = mido.MidiFile(ticks_per_beat=480)
track = mido.MidiTrack()
mid.tracks.append(track)

# 135 BPM High Energy Tempo
tempo = mido.bpm2tempo(135)
track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))

# Convert absolute filtered ticks to Note On/Off messages
midi_events = []
for e in filtered_events:
    tick, note, vel, limb = e
    midi_events.append((tick, 'note_on', note, vel))
    # Give all hits a uniform ~32nd note duration (60 ticks)
    midi_events.append((tick + 60, 'note_off', note, 0))

# Sort: first by tick, then ensure note_offs happen BEFORE note_ons if sharing a tick
midi_events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

last_tick = 0
for tick, msg_type, note, vel in midi_events:
    delta = tick - last_tick
    if msg_type == 'note_on':
        # Channel 9 in mido corresponds to General MIDI Channel 10
        track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
    else:
        track.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=delta))
    last_tick = tick

mid.save('solo.mid')
