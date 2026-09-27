import mido
import random
import math

# General MIDI Percussion Map
KICK = 36
SNARE = 38
RIM = 37
HAT_CLOSED = 42
HAT_PEDAL = 44
HAT_OPEN = 46
RIDE = 51
RIDE_BELL = 53
CRASH1 = 49
CRASH2 = 57
SPLASH = 55
CHINA = 52
T1 = 50
T2 = 48
T3 = 47
T4 = 45
T5 = 43
T6 = 41
TOMS = [T1, T2, T3, T4, T5, T6]

class DrumSoloGenerator:
    def __init__(self, seed=42):
        random.seed(seed)
        self.hits = []
        
    def add_hit(self, t, inst, vel, humanize=True):
        if vel <= 0:
            return
        if humanize:
            # Micro-timing shifts for humanization
            shift = random.gauss(0, 0.015)
            # Velocity variations
            v_shift = int(random.gauss(0, 4))
            vel = max(1, min(127, vel + v_shift))
            # Surge and settle macro-timing (pushes and pulls slightly over 8 beats)
            t_warped = t + shift + 0.02 * math.sin(t * 2 * math.pi / 8)
        else:
            t_warped = t
            vel = max(1, min(127, vel))
            
        self.hits.append((t_warped, inst, vel))

    def generate(self):
        """Generates 64 bars of a progressive, dynamic drum solo at 120 BPM."""
        
        # Section 1: Intro (Bars 1-8) - Sparse groove, developing a motif
        for b in range(8):
            bar_start = b * 4
            for i in range(4):
                self.add_hit(bar_start + i, RIDE, 60 if i % 2 == 1 else 75)
            # Cross stick on the backbeats
            self.add_hit(bar_start + 1.0, RIM, 90)
            self.add_hit(bar_start + 3.0, RIM, 90)
            
            # Syncopated kick motif
            self.add_hit(bar_start + 0.0, KICK, 85)
            self.add_hit(bar_start + 2.5, KICK, 80)
            if b % 2 == 1:
                self.add_hit(bar_start + 3.75, KICK, 75)
                
            # Ghost notes flowing
            self.add_hit(bar_start + 1.75, SNARE, 25)
            self.add_hit(bar_start + 2.25, SNARE, 25)
            
            # Phrasing fills
            if b == 3:
                self.add_hit(bar_start + 3.5, SNARE, 80)
                self.add_hit(bar_start + 3.75, T1, 75)
            elif b == 7:
                self.add_hit(bar_start + 3.0, SNARE, 100)
                self.add_hit(bar_start + 3.25, T1, 90)
                self.add_hit(bar_start + 3.5, T3, 85)
                self.add_hit(bar_start + 3.75, T5, 85)

        # Section 2: Groove Develops (Bars 9-16) - Opening up to the snare and moving cymbals
        for b in range(8, 16):
            bar_start = b * 4
            for i in range(8):
                t = bar_start + i * 0.5
                inst = RIDE_BELL if i in [3, 7] and random.random() > 0.5 else RIDE
                vel = 80 if i % 2 == 0 else 60
                self.add_hit(t, inst, vel)
                
            self.add_hit(bar_start + 1.0, SNARE, 105)
            self.add_hit(bar_start + 3.0, SNARE, 105)
            
            # Anchoring the time with the hi-hat pedal
            self.add_hit(bar_start + 1.0, HAT_PEDAL, 70)
            self.add_hit(bar_start + 3.0, HAT_PEDAL, 70)
            
            self.add_hit(bar_start + 0.0, KICK, 90)
            if b % 2 == 0:
                self.add_hit(bar_start + 1.5, KICK, 85)
                self.add_hit(bar_start + 2.5, KICK, 85)
            else:
                self.add_hit(bar_start + 2.25, KICK, 85)
                self.add_hit(bar_start + 3.5, KICK, 85)
                
            for g in [0.75, 1.25, 2.75, 3.25]:
                if random.random() > 0.3:
                    self.add_hit(bar_start + g, SNARE, random.randint(20, 40))
                    
            if b in [11, 15]:
                self.add_hit(bar_start + 3.25, KICK, 90)
                self.add_hit(bar_start + 3.5, T2, 100)
                self.add_hit(bar_start + 3.75, T4, 100)
                
            if b % 4 == 3:
                self.add_hit(bar_start + 3.5, HAT_OPEN, 85)
                self.add_hit(bar_start + 4.0, HAT_PEDAL, 90)

        # Section 3: Linear Pattern (Bars 17-24) - A polymetric 7/16 phrase over 4/4
        pattern = ['R', 'L', 'K', 'R', 'L', 'R', 'K']
        start_beat = 16 * 4
        for i in range(128): 
            t = start_beat + i * 0.25
            note = pattern[i % 7]
            
            # Resolve the phrasing tension with a fill in the last 2 beats
            if i >= 128 - 8:
                fill_inst = [SNARE, T1, T2, T3, T4, T5, KICK, KICK]
                self.add_hit(t, fill_inst[i - (128-8)], 110)
                continue
                
            is_accent = (i % 7 == 0)
            if note == 'R':
                self.add_hit(t, RIDE_BELL if is_accent else HAT_CLOSED, 95 if is_accent else 65)
            elif note == 'L':
                self.add_hit(t, SNARE, 105 if is_accent else 40)
            elif note == 'K':
                self.add_hit(t, KICK, 100)
                
            if i % 4 == 0:
                self.add_hit(t, HAT_PEDAL, 80)

        # Section 4: Tom Build (Bars 25-32) - Tribal floor toms escalating in subdivision
        start_beat = 24 * 4
        for b in range(8):
            bar_start = start_beat + b * 4
            for i in range(4):
                self.add_hit(bar_start + i, KICK, 90 + b * 3)
                
            if b % 2 == 0 and b < 6:
                self.add_hit(bar_start, SPLASH, 100)
                
            if b < 4:
                # 8th notes
                for i in range(8):
                    t = bar_start + i * 0.5
                    vol = 60 + b * 5 + (15 if i % 2 == 0 else 0)
                    tom = T6 if i % 4 < 2 else T4
                    self.add_hit(t, tom, vol)
            elif b < 6:
                # 16th notes
                for i in range(16):
                    t = bar_start + i * 0.25
                    vol = 80 + (b-4) * 10 + (15 if i % 4 == 0 else 0)
                    tom_opts = [T5, T6, T4, T5]
                    self.add_hit(t, tom_opts[i % 4], vol)
            else:
                # Sextuplets sweeping across the toms
                for i in range(24): 
                    t = bar_start + i * (1/6)
                    vol = 90 + int((i/24) * 30)
                    if b == 7 and i >= 18:
                        self.add_hit(t, SNARE, vol)
                    else:
                        tom_opts = [T1, T2, T3, T4, T5, T6]
                        self.add_hit(t, tom_opts[i % 6], vol)

        # Section 5: Climax Heavy Groove (Bars 33-40) - Bashing cymbals and busy kicks
        start_beat = 32 * 4
        for b in range(8):
            bar_start = start_beat + b * 4
            
            self.add_hit(bar_start + 0.0, CRASH1, 110 + (b%2)*5)
            self.add_hit(bar_start + 2.0, CRASH2, 110 + (b%2)*5)
            if b % 4 == 3:
                self.add_hit(bar_start + 3.0, CHINA, 120)
                
            for i in range(8):
                if i not in [0, 4, 6]: 
                    self.add_hit(bar_start + i * 0.5, RIDE_BELL, 100)
                    
            self.add_hit(bar_start + 1.0, SNARE, 120)
            if b % 2 == 0:
                self.add_hit(bar_start + 3.0, SNARE, 120)
            
            kick_pattern = [0.0, 0.5, 0.75, 1.5, 2.0, 2.25, 2.75]
            if b % 2 == 0:
                kick_pattern.extend([3.0, 3.5])
            for kp in kick_pattern:
                self.add_hit(bar_start + kp, KICK, 110)
                
            # Punishing 32nd note snare rips
            if b % 2 == 1:
                for i in range(8):
                    t = bar_start + 3.0 + i * 0.125
                    self.add_hit(t, SNARE if i < 4 else T3, 115)

        # Section 6: Breakdown (Bars 41-48) - Funk-inspired ghost notes pulling back the dynamics
        start_beat = 40 * 4
        self.add_hit(start_beat, CRASH1, 100)
        
        for b in range(8):
            bar_start = start_beat + b * 4
            
            for i in range(16):
                t = bar_start + i * 0.25
                if b == 0 and i == 0: continue
                if b == 7 and t >= bar_start + 3.0: continue
                
                # Interleaved hi-hat openings
                if i % 4 == 2 and random.random() > 0.5:
                    self.add_hit(t, HAT_OPEN, 80)
                    self.add_hit(t + 0.25, HAT_PEDAL, 90)
                else:
                    vel = 90 if i % 4 == 0 else (60 if i % 2 == 0 else 40)
                    if not (i % 4 == 3 and random.random() > 0.5): 
                        self.add_hit(t, HAT_CLOSED, vel)
                        
            if not (b == 7 and bar_start + 1.0 >= bar_start + 3.0): 
                self.add_hit(bar_start + 1.0, SNARE, 95)
            if b != 7:
                self.add_hit(bar_start + 3.0, SNARE, 95)
            
            for g in [0.5, 0.75, 1.25, 1.75, 2.25, 2.5, 3.25, 3.75]:
                if b == 7 and g >= 3.0: continue
                if random.random() > 0.4:
                    self.add_hit(bar_start + g, SNARE, random.randint(20, 45))
                    
            kicks = [0.0, 1.5, 2.75]
            if b % 2 == 1:
                kicks.extend([3.5, 3.75])
            for k in kicks:
                if b == 7 and k >= 3.0: continue
                if b == 0 and k == 0.0: 
                    pass 
                else:
                    self.add_hit(bar_start + k, KICK, 95)
                    
            if b == 7:
                self.add_hit(bar_start + 3.0, SPLASH, 100)
                self.add_hit(bar_start + 3.25, KICK, 100)
                self.add_hit(bar_start + 3.5, SNARE, 100)
                self.add_hit(bar_start + 3.75, SNARE, 110)

        # Section 7: Rudiment Build (Bars 49-56) - Hands/Feet phrasing combos
        start_beat = 48 * 4
        for b in range(8):
            bar_start = start_beat + b * 4
            hand_insts = [SNARE, T1, T2, T3, T4, T5]
            
            for i in range(4): 
                beat_t = bar_start + i
                if b < 4:
                    # 16th Note Runs (R L K K)
                    for j in range(4):
                        t = beat_t + j * 0.25
                        if j == 0:
                            self.add_hit(t, SNARE if i % 2 == 0 else T1, 100 + b*5)
                        elif j == 1:
                            self.add_hit(t, T2 if i % 2 == 0 else T3, 90 + b*5)
                        elif j in [2, 3]:
                            self.add_hit(t, KICK, 100 + b*5)
                else:
                    # 16th Note Triplet Runs (R L R L K K)
                    for j in range(6):
                        t = beat_t + j * (1/6)
                        if j == 0:
                            self.add_hit(t, hand_insts[(b+i)%6], 115)
                        elif j == 1:
                            self.add_hit(t, hand_insts[(b+i+1)%6], 105)
                        elif j == 2:
                            self.add_hit(t, hand_insts[(b+i+2)%6], 115)
                        elif j == 3:
                            self.add_hit(t, hand_insts[(b+i+3)%6], 105)
                        elif j in [4, 5]:
                            self.add_hit(t, KICK, 115)
                            
            if b % 2 == 0:
                self.add_hit(bar_start, CRASH1, 120)
                self.add_hit(bar_start, KICK, 120)

        # Section 8: Grand Finale (Bars 57-64) - Extreme chops and the ultimate crescendo
        start_beat = 56 * 4
        for b in range(8):
            bar_start = start_beat + b * 4
            
            if b < 3:
                for i in range(4): 
                    if b == 0:
                        for j in range(4):
                            t = bar_start + i + j * 0.25
                            self.add_hit(t, SNARE if j%2==0 else KICK, 110)
                    elif b == 1:
                        for j in range(6):
                            t = bar_start + i + j * (1/6)
                            self.add_hit(t, TOMS[i%6] if j < 4 else KICK, 110)
                    elif b == 2:
                        for j in range(8):
                            t = bar_start + i + j * 0.125
                            inst = TOMS[(j + i)%6] if j < 6 else KICK
                            self.add_hit(t, inst, 115)
                    self.add_hit(bar_start + i, CRASH2 if i%2==0 else SPLASH, 120)
            elif b == 3:
                self.add_hit(bar_start + 0.0, CRASH1, 127)
                self.add_hit(bar_start + 0.0, KICK, 127)
                self.add_hit(bar_start + 2.95, SNARE, 80)
                self.add_hit(bar_start + 3.0, SNARE, 127)
                self.add_hit(bar_start + 3.0, KICK, 127)
            elif b < 7:
                # John Bonham style C K K triplets across cymbals
                for i in range(4):
                    for j in range(2): 
                        t_group = bar_start + i + j * 0.5
                        self.add_hit(t_group, CRASH1 if (i+j)%2==0 else CHINA, 120)
                        self.add_hit(t_group + (1/6), KICK, 115)
                        self.add_hit(t_group + (2/6), KICK, 115)
            elif b == 7:
                # The Final Snare/Tom Roll Crescendo
                for i in range(32): 
                    t = bar_start + i * 0.125
                    vol = 70 + int((i/32) * 57) 
                    if i < 16:
                        self.add_hit(t, SNARE, vol)
                    else:
                        self.add_hit(t, TOMS[(i//4)%6], vol)
                        if i % 2 == 0:
                            self.add_hit(t, KICK, vol) 

        # The Final Hit (Behold, The Glory)
        end_beat = 64 * 4
        self.add_hit(end_beat, CRASH1, 127, humanize=False)
        self.add_hit(end_beat, CRASH2, 127, humanize=False)
        self.add_hit(end_beat, KICK, 127, humanize=False)
        self.add_hit(end_beat, T6, 127, humanize=False)

    def save(self, filename="solo.mid", bpm=120):
        mid = mido.MidiFile(type=0)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        tempo = mido.bpm2tempo(bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
        
        ticks_per_beat = mid.ticks_per_beat 
        events = []
        for hit in self.hits:
            t_beats, inst, vel = hit
            events.append((t_beats, 'note_on', inst, vel))
            # Schedule note off almost instantly so it doesn't accidentally cancel successive hits
            events.append((t_beats + 0.01, 'note_off', inst, 0))
            
        # Ensure note_offs are placed before note_ons if they land on the exact same tick
        events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))
        
        last_tick = 0
        for ev in events:
            t_beats, msg_type, inst, vel = ev
            abs_tick = int(round(t_beats * ticks_per_beat))
            
            if abs_tick < last_tick:
                abs_tick = last_tick
                
            delta = abs_tick - last_tick
            track.append(mido.Message(msg_type, channel=9, note=inst, velocity=vel, time=delta))
            last_tick = abs_tick
            
        # Give the last ring-out some space
        track.append(mido.MetaMessage('end_of_track', time=ticks_per_beat * 2))
        mid.save(filename)

if __name__ == "__main__":
    generator = DrumSoloGenerator(seed=42)
    generator.generate()
    generator.save("solo.mid")
