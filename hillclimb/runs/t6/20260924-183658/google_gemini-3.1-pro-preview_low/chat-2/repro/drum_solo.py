import mido
import random
import math

class DrumSequencer:
    def __init__(self, ticks_per_beat=480):
        self.ticks_per_beat = ticks_per_beat
        self.events = []
        self.current_beat = 0.0

    def add_note(self, beat, note, velocity, duration=0.1):
        # Humanize timing and velocity
        timing_shift = random.uniform(-0.03, 0.03) if velocity > 0 else 0
        actual_beat = beat + timing_shift
        
        # Humanize velocity
        vel_shift = random.randint(-8, 8) if velocity > 10 else 0
        actual_vel = max(1, min(127, int(velocity + vel_shift)))
        
        start_tick = int(actual_beat * self.ticks_per_beat)
        end_tick = int((actual_beat + duration) * self.ticks_per_beat)
        
        if actual_vel > 0:
            self.events.append((start_tick, 'note_on', note, actual_vel))
            self.events.append((end_tick, 'note_off', note, 0))

    def write_midi(self, filename="solo.mid", tempo_bpm=120):
        mid = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        # Set tempo
        tempo = mido.bpm2tempo(tempo_bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo))
        
        # Sort events by absolute tick
        self.events.sort(key=lambda x: (x[0], x[1] == 'note_off'))
        
        last_tick = 0
        for tick, msg_type, note, vel in self.events:
            delta = tick - last_tick
            if delta < 0:
                delta = 0
            if msg_type == 'note_on':
                track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
            else:
                track.append(mido.Message('note_off', channel=9, note=note, velocity=vel, time=delta))
            last_tick += delta
            
        mid.save(filename)

def generate_solo():
    random.seed(42) # Reproducible output
    seq = DrumSequencer()
    
    # Instruments
    KICK = 36
    SNARE = 38
    HAT_CLOSED = 42
    HAT_OPEN = 46
    HAT_PEDAL = 44
    TOM_HI = 50
    TOM_MID = 47
    TOM_LOW = 43
    TOM_FLOOR = 41
    CRASH_1 = 49
    CRASH_2 = 57
    RIDE = 51
    RIDE_BELL = 53

    toms = [TOM_HI, TOM_MID, TOM_LOW, TOM_FLOOR]
    
    total_beats = 240 # ~2 minutes at 120 BPM
    
    beat = 0.0
    
    # Phase 1: The Setup (0 - 64)
    # Exploring a syncopated groove with ghost notes
    while beat < 64.0:
        bar_start = beat
        for i in range(16): # 16th notes
            pos = i * 0.25
            current = bar_start + pos
            
            # Ride pattern
            if i % 4 == 0:
                seq.add_note(current, RIDE, 70)
            elif i % 4 == 2:
                seq.add_note(current, RIDE, 50)
            
            # Kick
            if i in [0, 7, 10]:
                seq.add_note(current, KICK, 90)
                
            # Snare
            if i in [4, 12]:
                seq.add_note(current, SNARE, 100)
            elif i in [3, 6, 9, 14, 15] and random.random() < 0.6:
                seq.add_note(current, SNARE, random.randint(20, 40)) # Ghost notes
                
            # Random tom accent
            if i == 15 and random.random() < 0.3:
                seq.add_note(current, random.choice(toms), 80)
        
        # Occasional crash
        if beat % 8 == 0:
            seq.add_note(bar_start, CRASH_1, 95)
            seq.add_note(bar_start, KICK, 95)
            
        beat += 4.0
        
    # Phase 2: Tom exploration and rudiments (64 - 128)
    while beat < 128.0:
        bar_start = beat
        is_fill = (beat % 8 >= 6)
        
        if not is_fill:
            # Syncopated tom groove
            for i in range(16):
                pos = i * 0.25
                current = bar_start + pos
                
                if i % 8 == 0:
                    seq.add_note(current, HAT_PEDAL, 60)
                
                if i in [0, 3, 8, 11]:
                    seq.add_note(current, KICK, 85)
                    
                if i in [2, 5, 10, 13]:
                    tom = random.choice([TOM_MID, TOM_LOW])
                    seq.add_note(current, tom, random.randint(60, 85))
                    
                if i in [4, 12]:
                    seq.add_note(current, SNARE, 90)
                elif i % 2 != 0 and random.random() < 0.4:
                    seq.add_note(current, SNARE, 30)
        else:
            # Linear fills around the kit
            num_notes = 32 if random.random() < 0.5 else 16
            step = 4.0 / num_notes
            for i in range(num_notes):
                current = bar_start + i * step
                if i % 4 == 0:
                    seq.add_note(current, KICK, 90)
                else:
                    inst = random.choice([SNARE, TOM_HI, TOM_MID, TOM_LOW, TOM_FLOOR])
                    vel = 60 + int(40 * (i / num_notes)) # Crescendo
                    seq.add_note(current, inst, vel)
                    
        beat += 4.0
        
    # Phase 3: Build up / Snare rolls / Tension (128 - 192)
    while beat < 192.0:
        bar_start = beat
        
        if beat % 8 == 0:
            seq.add_note(bar_start, CRASH_2, 100)
            
        # Paradiddle-like sticking on Snare and Toms
        for i in range(16):
            pos = i * 0.25
            current = bar_start + pos
            
            # Heavy 4-on-the-floor build
            if i % 4 == 0:
                seq.add_note(current, KICK, 100)
                seq.add_note(current, HAT_OPEN, 80)
            elif i % 4 == 2:
                seq.add_note(current, HAT_PEDAL, 70)
                
            # Snare accents and rolls
            accents = [4, 7, 12, 15]
            if i in accents:
                seq.add_note(current, SNARE, 110)
            else:
                # 32nd note doubles
                seq.add_note(current, SNARE, 50)
                seq.add_note(current + 0.125, SNARE, 55)
                
        beat += 4.0
        
    # Phase 4: The Climax (192 - 238)
    while beat < 238.0:
        bar_start = beat
        
        # Heavy crashes on beats
        for i in range(4):
            seq.add_note(bar_start + i, CRASH_1 if i % 2 == 0 else CRASH_2, 115)
            
        # Fast double kick and tom rolls
        for i in range(32): # 32nd notes
            pos = i * 0.125
            current = bar_start + pos
            
            # Double bass
            seq.add_note(current, KICK, 100 + random.randint(-10, 10))
            
            # Sweeping tom rolls
            if i % 8 < 4:
                seq.add_note(current, SNARE, 110)
            else:
                tom_idx = (i // 4) % 4
                seq.add_note(current, toms[tom_idx], 100)
                
        beat += 4.0

    # The Finale (238 - 240)
    # Huge fill leading to final hit
    bar_start = 238.0
    for i in range(16): # 32nd note triplets (6 per beat)
        pos = i * (2.0 / 16.0)
        current = bar_start + pos
        seq.add_note(current, SNARE, 90 + i*2)
        seq.add_note(current, KICK, 90 + i*2)
        seq.add_note(current, random.choice(toms), 90 + i*2)

    # Final Hit at 240
    seq.add_note(240.0, CRASH_1, 127)
    seq.add_note(240.0, CRASH_2, 127)
    seq.add_note(240.0, KICK, 127)
    seq.add_note(240.0, SNARE, 127)
    
    # Ring out
    seq.add_note(244.0, KICK, 0) # Just to pad the ending

    seq.write_midi("solo.mid", tempo_bpm=120)

if __name__ == "__main__":
    generate_solo()
