import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage
import random
import math

# Set deterministic seed for reproducible identical output on every run
random.seed(42)

# Drum Map (General MIDI)
KICK = 36
SNARE = 38
RIM = 37
CHH = 42      # Closed Hi-Hat
PHH = 44      # Pedal Hi-Hat
OHH = 46      # Open Hi-Hat
RIDE = 51
BELL = 53
CRASH1 = 49
CRASH2 = 57
SPLASH = 55
CHINA = 52
TOM1 = 50     # High Tom
TOM2 = 48     # Mid Tom
TOM3 = 45     # Low Tom
TOM4 = 43     # Floor Tom
COWBELL = 56

events = []

def add_hit(beat, pitch, vel):
    events.append((beat, pitch, vel))

def add_flam(beat, pitch, vel, hand_delay=0.03):
    add_hit(beat - hand_delay, pitch, max(1, vel - 30))
    add_hit(beat, pitch, vel)

def add_drag(beat, pitch, vel):
    add_hit(beat - 0.06, pitch, max(1, vel - 40))
    add_hit(beat - 0.03, pitch, max(1, vel - 40))
    add_hit(beat, pitch, vel)

# -- Sections of the Solo --

def intro_groove(bar):
    """Bars 0-15: Funky linear groove, building dynamics and ghost notes."""
    b = bar * 4
    base_vel = 70 + (bar * 2)
    
    # Crashes on phrase downbeats
    if bar % 4 == 0 and bar > 0:
        add_hit(b, CRASH1, 100)
    elif bar % 4 == 2 and bar > 7:
        add_hit(b, SPLASH, 90)
    else:
        add_hit(b, CHH, base_vel)
        
    add_hit(b, KICK, 90)
        
    # Dynamically varying hi-hat
    for i in range(8):
        if i == 0: continue
        pos = b + i * 0.5
        # Stop hihat during the fill at end of phrase
        if bar % 4 == 3 and pos >= b + 2.5: continue
        
        # Don't play straight hi-hat where specific syncopations happen
        if pos not in [b, b+1.0, b+1.5, b+2.0, b+3.0]:
            add_hit(pos, CHH, base_vel - 10 + random.randint(-5, 5))
            
    # Ghost notes development
    if bar >= 4:
        add_hit(b + 0.5, SNARE, 30)
        add_hit(b + 0.75, CHH, 50)
        add_hit(b + 2.25, SNARE, 35)
    
    # Backbeats
    add_hit(b + 1.0, SNARE, 100)
    
    # Kick syncopations
    if bar >= 8:
        add_hit(b + 1.25, CHH, 50)
        add_hit(b + 1.5, KICK, 80)
        add_hit(b + 1.75, KICK, 80)
    else:
        add_hit(b + 1.5, KICK, 80)
    
    add_hit(b + 2.0, CHH, base_vel)
    add_hit(b + 2.5, CHH, base_vel - 10)
    
    if bar % 4 == 3: # Phrase Fill
        add_hit(b + 2.75, KICK, 80)
        add_hit(b + 3.0, SNARE, 90)
        
        if bar < 8:
            add_hit(b + 3.5, TOM1, 80)
            add_hit(b + 3.75, TOM2, 85)
        else:
            # Subtle snare drag into the toms
            add_hit(b + 3.25, SNARE, 40)
            add_hit(b + 3.375, SNARE, 50)
            add_hit(b + 3.5, TOM1, 80)
            add_hit(b + 3.75, TOM4, 95)
    else:
        add_hit(b + 3.0, SNARE, 105)
        add_hit(b + 3.25, KICK, 80)
        
        if bar >= 12 and bar % 2 == 1:
            add_hit(b + 3.5, OHH, 80)
            add_hit(b + 3.75, KICK, 80)
        else:
            add_hit(b + 3.5, CHH, 60)
            add_hit(b + 3.75, KICK, 80)

def ride_groove(bar):
    """Bars 16-31: Ride cymbal, introducing bell accents and snare flurries."""
    b = bar * 4
    rel_bar = bar - 16
    
    if bar == 16:
        add_hit(b, CRASH2, 110)
        add_hit(b, KICK, 110)
    else:
        if rel_bar % 4 == 0:
            add_hit(b, CRASH1, 100)
            add_hit(b, KICK, 100)
        else:
            add_hit(b, RIDE, 80)
            add_hit(b, KICK, 90)

    # Ride pattern
    for i in range(8):
        if i == 0 and rel_bar % 4 == 0: continue
        if i == 0 and bar == 16: continue
        pos = b + i * 0.5
        if rel_bar % 4 == 3 and pos >= b + 3.0: continue # Stop ride for fill
        
        vel = 90 if i % 4 == 0 else (70 if i % 2 == 0 else 50)
        use_bell = (rel_bar >= 4 and i in [4, 6])
        add_hit(pos, BELL if use_bell else RIDE, vel)
        
        if i == 2 or i == 6: # Hi-hat pedal on 2 and 4
            add_hit(pos, PHH, 80)

    add_hit(b + 1.0, SNARE, 105)
    
    add_hit(b + 1.5, KICK, 80)
    if rel_bar >= 8:
        add_hit(b + 1.75, KICK, 85)
        add_hit(b + 2.5, KICK, 85)
    
    # Snare ghosting
    if rel_bar >= 12:
        add_hit(b + 2.25, SNARE, 40)
        add_drag(b + 2.75, SNARE, 50)
    else:
        add_hit(b + 2.75, SNARE, 40)
    
    if rel_bar % 4 == 3: # Tom sweep fills
        add_hit(b + 3.0, SNARE, 110)
        if rel_bar < 8:
            add_hit(b + 3.5, TOM1, 100)
            add_hit(b + 3.75, TOM4, 110)
        else:
            # 16th note triplets on kick and toms
            add_hit(b + 3.0 + 1/6, KICK, 90)
            add_hit(b + 3.0 + 2/6, KICK, 90)
            add_hit(b + 3.5, TOM1, 100)
            add_hit(b + 3.5 + 1/6, TOM2, 100)
            add_hit(b + 3.5 + 2/6, TOM4, 110)
    else:
        add_hit(b + 3.0, SNARE, 105)
        add_hit(b + 3.5, KICK, 85)
        if rel_bar >= 12:
            add_hit(b + 3.75, SNARE, 45)

def latin_groove(bar):
    """Bars 32-47: Shift feel completely to Afro-Cuban/Songo feel, syncopated cowbell."""
    b = bar * 4
    rel_bar = bar - 32
    
    if bar == 32:
        add_hit(b, CRASH1, 110)
        
    for i in range(4):
        add_hit(b + i, PHH, 70) # Keeping time with left foot
        
    cb_pattern = [0, 0.5, 1.0, 1.5, 2.25, 2.75, 3.25, 3.75]
    for p in cb_pattern:
        if rel_bar % 4 == 3 and p >= 2.0:
            continue # Clear right hand cowbell for tom fill
        acc = 100 if p in [0, 1.0, 2.25, 3.25] else 75
        acc += rel_bar * 2 
        add_hit(b + p, COWBELL, min(127, acc))
        
    kick_pattern = [0.5, 1.5, 2.5, 3.5] if bar % 2 == 0 else [0.25, 1.5, 2.5, 3.75]
    for p in kick_pattern:
        add_hit(b + p, KICK, min(127, 90 + rel_bar))
        
    if rel_bar % 4 == 3:
        # Linear gospel-style fill (Tom, Kick, Tom)
        for i in range(8):
            pos = b + 2.0 + i * 0.25
            pitch = TOM1 if i < 2 else (TOM2 if i < 4 else (TOM3 if i < 6 else TOM4))
            add_hit(pos, pitch, 90 + i*4)
            if i % 2 == 0:
                add_hit(pos + 0.125, KICK, 90)
    else:
        # Left hand moving from cross-stick to open toms as tension builds
        acc_pitch = RIM if rel_bar < 8 else TOM1
        ghost_pitch = SNARE if rel_bar < 8 else TOM2
            
        add_hit(b + 0.75, acc_pitch, 90 + rel_bar)
        add_hit(b + 1.25, ghost_pitch, 50 + rel_bar)
        add_hit(b + 1.75, acc_pitch, 90 + rel_bar)
        add_hit(b + 2.0, ghost_pitch, 40 + rel_bar)
        add_hit(b + 3.0, acc_pitch, 100 + rel_bar)

def climax_groove(bar):
    """Bars 48-59: High energy rock climax, open hi-hats, massive 16th note triplet fills."""
    b = bar * 4
    
    if bar == 48:
        add_hit(b, CRASH2, 115)
        
    fill_start = 2.0 if bar % 4 == 3 else 4.0
        
    for i in range(8):
        pos = b + i * 0.5
        if pos < b + fill_start:
            if i == 0 and bar % 2 == 0:
                add_hit(pos, CRASH1, 110)
            elif i == 4 and bar % 2 == 0:
                add_hit(pos, CHINA, 110)
            else:
                if bar != 48 or i != 0:
                    add_hit(pos, OHH, 95)
                
    add_hit(b + 1.0, SNARE, 120)
    if fill_start > 3.0:
        add_hit(b + 3.0, SNARE, 120)
        
    # Heavy snare drags
    if fill_start > 1.5:
        add_drag(b + 1.5, SNARE, 50)
        add_hit(b + 1.75, SNARE, 60)
    if fill_start > 3.5:
        add_drag(b + 3.5, SNARE, 50)
        add_hit(b + 3.75, SNARE, 60)
        
    # Aggressive kick
    add_hit(b + 0.0, KICK, 110)
    add_hit(b + 0.25, KICK, 100)
    add_hit(b + 0.75, KICK, 100)
    
    if fill_start > 2.0:
        add_hit(b + 2.0, KICK, 110)
        add_hit(b + 2.125, KICK, 100) # double kick burst
        add_hit(b + 2.25, KICK, 100)
        add_hit(b + 2.5, KICK, 100)
        
    if bar % 4 == 3:
        # Huge descending 16th-note triplet sweep
        for i in range(12): 
            pos = b + 2.0 + i * (1.0 / 6.0)
            pitch = SNARE if i < 3 else (TOM1 if i < 6 else (TOM2 if i < 9 else TOM4))
            add_hit(pos, pitch, 110 + i)
            if i % 3 == 0:
                add_hit(pos, KICK, 110)

def outro_groove(bar):
    """Bars 60-63: Synchronized ensemble hits, continuous double-kick swell, final massive fill."""
    b = bar * 4
    vol = 80 + (bar - 60) * 10
    
    if bar < 63:
        for i in range(16):
            pos = b + i * 0.25
            k_vel = vol + (10 if i % 4 == 0 else 0)
            add_hit(pos, KICK, k_vel)
    else:
        # Stop the double kick rumble before the fill begins
        for i in range(10): 
            pos = b + i * 0.25
            k_vel = vol + (10 if i % 4 == 0 else 0)
            add_hit(pos, KICK, k_vel)

    # Shifting accent motifs to build tension
    if bar == 60:
        accents = [0, 1.5, 2.75, 3.5]
    elif bar == 61:
        accents = [0, 1.5, 2.75, 3.5, 4.0] 
    elif bar == 62:
        accents = [0.5, 1.5, 2.5, 3.5] 
    elif bar == 63:
        accents = [0, 0.75, 1.5] 
        
    for acc in accents:
        pitch = CRASH1 if acc % 1 == 0 else CRASH2
        add_hit(b + acc, pitch, 120)
        add_hit(b + acc, SNARE, 120)
        
    if bar == 63:
        add_hit(b + 2.5, CRASH1, 120)
        add_hit(b + 2.5, SNARE, 120)
        # Final blistering 32nd note drum fill covering the remaining 1.5 beats
        for i in range(12):
            pos = b + 2.5 + i * 0.125
            pitch = SNARE if i < 3 else (TOM1 if i < 6 else (TOM2 if i < 9 else TOM4))
            add_hit(pos, pitch, 112 + i)
            if i % 3 == 0:
                add_hit(pos, KICK, 120)


# Generate the 64 bars
for bar_idx in range(64):
    if bar_idx < 16:
        intro_groove(bar_idx)
    elif bar_idx < 32:
        ride_groove(bar_idx)
    elif bar_idx < 48:
        latin_groove(bar_idx)
    elif bar_idx < 60:
        climax_groove(bar_idx)
    else:
        outro_groove(bar_idx)

# Final Hit (End of 2 minutes)
add_hit(64 * 4, CRASH1, 127)
add_hit(64 * 4, CRASH2, 127)
add_hit(64 * 4, KICK, 127)


def humanize(events):
    """Applies realistic timing variations: swing, laid-back snare, and subtle tempo drifting."""
    new_events = []
    for beat, pitch, vel in events:
        shift = 0
        rem = beat % 0.5
        # Subtle 16th note swing
        if 0.2 < rem < 0.3:
            shift += 0.015 
            
        # Lay back the backbeat slightly
        measure_beat = beat % 4.0
        if pitch == SNARE and (abs(measure_beat - 1.0) < 0.1 or abs(measure_beat - 3.0) < 0.1):
            shift += 0.012 
            
        # Overall tempo drift
        shift += math.sin(beat / 10.0) * 0.005
        
        vel_mod = int(math.sin(beat * 7) * 4) + int(math.cos(beat * 11) * 3)
        new_vel = max(1, min(127, int(vel + vel_mod)))
        
        new_events.append((max(0.0, beat + shift), pitch, new_vel))
    return new_events

def deduplicate_and_sort(events):
    """Sorts events and removes duplicate notes physically impossible to hit twice at the exact same instant."""
    events.sort(key=lambda x: x[0])
    cleaned = []
    last_hit = {}
    for beat, pitch, vel in events:
        if pitch in last_hit:
            # Drop hits of the identical pitch if within ~9ms
            if beat - last_hit[pitch] < 0.02:
                continue
        last_hit[pitch] = beat
        cleaned.append((beat, pitch, vel))
    return cleaned

cleaned_events = deduplicate_and_sort(humanize(events))

# Setup MIDI
ticks_per_beat = 480
mid = MidiFile(ticks_per_beat=ticks_per_beat)
track = MidiTrack()
mid.tracks.append(track)

# 128 BPM -> exactly 2 minutes for 256 beats
track.append(MetaMessage('set_tempo', tempo=468750, time=0))
track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
track.append(Message('program_change', program=0, channel=9, time=0))
track.append(Message('control_change', channel=9, control=7, value=127, time=0)) # Max volume

# Translate to absolute MIDI ticks
midi_events = []
for beat, pitch, vel in cleaned_events:
    abs_tick = int(beat * ticks_per_beat)
    midi_events.append((abs_tick, 'note_on', pitch, vel))
    # Send note_off slightly after to keep MIDI compliant
    midi_events.append((abs_tick + 60, 'note_off', pitch, 0)) 

# Sort carefully: absolute tick first, and note_off before note_on if simultaneous
midi_events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

# Write delta times
current_tick = 0
for abs_tick, msg_type, pitch, vel in midi_events:
    delta = abs_tick - current_tick
    track.append(Message(msg_type, channel=9, note=pitch, velocity=vel, time=delta))
    current_tick = abs_tick

mid.save('solo.mid')
