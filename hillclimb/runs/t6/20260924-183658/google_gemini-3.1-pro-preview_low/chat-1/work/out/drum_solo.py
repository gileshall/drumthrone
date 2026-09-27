import mido
import random
import math

def generate_solo():
    # Set seed for determinism
    random.seed(4242)
    events = []
    
    # Helper to add notes with humanization
    def add_note(time_b, note, vel):
        # Unquantized feel: slight random offset (swing/rush/drag)
        time_human = time_b + random.uniform(-0.02, 0.02)
        # Dynamics: slightly vary velocity
        vel_human = max(1, min(127, int(vel + random.uniform(-5, 5))))
        events.append((time_human, note, vel_human))

    # General MIDI Drum Map
    KICK = 36
    SNARE = 38
    SNARE_RIM = 37
    HAT_C = 42
    HAT_O = 46
    HAT_P = 44
    RIDE = 51
    RIDE_BELL = 53
    CRASH1 = 49
    CRASH2 = 57
    SPLASH = 55
    TOMS = [50, 48, 47, 45, 43, 41] # High to low
    
    # Sections to build a 2-minute solo at ~125 BPM
    # 2 minutes = 120 seconds * (125/60) = 250 beats
    
    # 0-32: Intro - Sparse, motif establishment
    for b in range(0, 32):
        add_note(b, KICK, 80)
        add_note(b + 0.5, HAT_C, 60)
        add_note(b + 1.0, SNARE_RIM, 90)
        add_note(b + 1.5, HAT_C, 60)
        
        # Ghost notes and syncopation
        if random.random() < 0.3:
            add_note(b + 1.75, KICK, 75)
        if random.random() < 0.2:
            add_note(b + 0.75, SNARE, 40)
        if b % 8 == 7:
            add_note(b + 1.5, HAT_O, 80)
            add_note(b + 2.0, HAT_P, 70)

    # 32-64: Groove Building - Ride cymbal and snare interaction
    for b in range(32, 64):
        add_note(b, KICK, 95)
        if b % 8 == 0:
            add_note(b, CRASH1, 105)
        elif b % 4 == 0:
            add_note(b, SPLASH, 95)
        else:
            add_note(b, RIDE, 85)
            
        add_note(b + 0.5, RIDE, 70)
        add_note(b + 1.0, SNARE, 100)
        add_note(b + 1.0, RIDE, 85)
        add_note(b + 1.5, RIDE, 70)
        
        if random.random() < 0.4:
            add_note(b + 1.25, SNARE, 45) # Ghost note
        if random.random() < 0.3:
            add_note(b + 1.75, KICK, 80)
            if random.random() < 0.5:
                add_note(b + 1.875, KICK, 80)

    # 64-100: Tom Groove - Tribal feel, moving around the kit
    for b in range(64, 100):
        if b % 2 == 0:
            add_note(b, KICK, 105)
            if b % 4 == 0:
                add_note(b, CRASH2, 110)
        
        add_note(b + 1.0, SNARE, 110)
        
        for frac in [0.25, 0.5, 0.75, 1.25, 1.5, 1.75]:
            r = random.random()
            if r < 0.4:
                add_note(b + frac, random.choice(TOMS), random.randint(70, 100))
            elif r < 0.6:
                add_note(b + frac, KICK, 90)

    # 100-160: The Solo - Linear phrasing and rudiments
    for b in range(100, 160):
        if b % 4 == 0:
            add_note(b, CRASH1, 115)
            add_note(b, KICK, 115)
            
        # 16th note linear phrasing
        for i in range(4):
            t = b + i * 0.25
            r = random.random()
            if i == 0 and b % 4 != 0:
                add_note(t, SNARE, 115)
            elif r < 0.25:
                add_note(t, KICK, 105)
            elif r < 0.6:
                add_note(t, SNARE, random.randint(40, 85))
            elif r < 0.8:
                add_note(t, random.choice(TOMS), random.randint(80, 110))
            else:
                add_note(t, HAT_O, 95)
                
        # Occasional 32nd note doubles
        if random.random() < 0.3:
            add_note(b + 0.875, KICK, 100)

    # 160-220: Climax - High density, rolls, heavy crashes
    for b in range(160, 220):
        if b % 2 == 0:
            add_note(b, CRASH1, 120)
            add_note(b+1, CRASH2, 120)
            
        for i in range(8): # 32nd notes
            t = b + i * 0.125
            vel = 60 + i * 6
            if i in [0, 4]:
                vel = 125
            
            r = random.random()
            if r < 0.4:
                add_note(t, SNARE, vel)
            elif r < 0.7:
                add_note(t, KICK, vel)
            else:
                add_note(t, random.choice(TOMS[:4]), vel)

    # 220-244: Big Ending Fill - Massive crescendo sextuplets
    for b in range(220, 244):
        base_vel = 80 + (b - 220) * 1.5
        for i in range(6): # Sextuplets
            t = b + i * (1.0/6.0)
            vel = int(base_vel + i * 3)
            vel = min(127, vel)
            
            # Orchestration: Snare -> Toms -> Kick
            if i < 2:
                add_note(t, SNARE, vel)
            elif i < 4:
                add_note(t, random.choice(TOMS), vel)
            else:
                add_note(t, KICK, vel)
                
    # 244-248: Final Setup
    for b in range(244, 248):
        add_note(b, SNARE, 127)
        add_note(b, KICK, 127)
        add_note(b + 0.5, SNARE, 127)
        add_note(b + 0.5, KICK, 127)

    # 248: Final Hit
    add_note(248, CRASH1, 127)
    add_note(248, CRASH2, 127)
    add_note(248, KICK, 127)
    add_note(248, SNARE, 127)

    # Sort events by time
    events.sort(key=lambda x: x[0])
    return events

def main():
    ticks_per_beat = 480
    tempo = 480000 # 125 BPM (500000 = 120 BPM)
    
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    
    events = generate_solo()
    
    last_time = 0.0
    for time_b, note, vel in events:
        # Prevent negative times from unquantized offsets at the start
        time_b = max(0.0, time_b)
        
        delta_beats = time_b - last_time
        if delta_beats < 0:
            delta_beats = 0
            
        delta_ticks = int(round(delta_beats * ticks_per_beat))
        
        # Note on
        track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta_ticks))
        # Note off immediately (drums don't typically need long durations)
        track.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=1))
        
        last_time = time_b + (1.0 / ticks_per_beat) # Account for the 1 tick note_off

    track.append(mido.MetaMessage('end_of_track', time=ticks_per_beat * 2))
    
    mid.save('solo.mid')

if __name__ == '__main__':
    main()
