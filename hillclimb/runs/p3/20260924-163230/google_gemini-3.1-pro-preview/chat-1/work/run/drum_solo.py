import mido
import math
import random

# Ensure identical output on every run
random.seed(42)

class SoloGenerator:
    def __init__(self):
        self.ticks_per_beat = 480
        self.events = []
        
    def get_warped_beat(self, beat):
        # Humanize tempo: slight push and pull breathing effect
        warp = math.sin(beat * (2 * math.pi / 16)) * 0.03
        
        # Ritardando at the very end
        if beat > 232:
            delay = ((beat - 232) ** 2) * 0.02
            return beat + warp + delay
            
        return beat + warp

    def add_hit(self, beat, note, velocity, feel_offset=0):
        # Deliberate placement: 16th note swing
        fraction = beat % 1.0
        swing = 10 if (fraction == 0.25 or fraction == 0.75) else 0
        
        # Ghost notes laid back, accents pushed ahead
        dynamics_offset = 0
        if velocity <= 50:
            dynamics_offset = 4 
        elif velocity >= 110:
            dynamics_offset = -3 
            
        warped_beat = self.get_warped_beat(beat)
        tick = int(warped_beat * self.ticks_per_beat) + feel_offset + swing + dynamics_offset
        
        if velocity > 0:
            velocity = max(1, min(127, int(velocity)))
            self.events.append((tick, note, velocity))

    def add_flam(self, beat, note, velocity, offset=-15):
        self.add_hit(beat, note, velocity * 0.4, feel_offset=offset)
        self.add_hit(beat, note, velocity)

    def add_drag(self, beat, note, velocity):
        self.add_hit(beat - 0.125, note, velocity * 0.3)
        self.add_hit(beat - 0.0625, note, velocity * 0.3)
        self.add_hit(beat, note, velocity)
        
    def play_linear_lick(self, start_beat, duration, notes, vels):
        step = duration / len(notes)
        for i, (n, v) in enumerate(zip(notes, vels)):
            self.add_hit(start_beat + i * step, n, v)

    def export(self, filename):
        # Shift all events so minimum tick is >= 0
        min_tick = min([e[0] for e in self.events]) if self.events else 0
        if min_tick < 0:
            self.events = [(t - min_tick, n, v) for t, n, v in self.events]
            
        self.events.sort(key=lambda x: x[0])
        
        midi_events = []
        active_notes = {}
        
        # Ensure Note Offs are dispatched properly to avoid overlaps
        for tick, note, vel in self.events:
            if note in active_notes:
                prev_tick = active_notes[note]
                dur = min(30, max(1, tick - prev_tick - 1))
                midi_events.append((prev_tick + dur, 'note_off', note, 0))
            active_notes[note] = tick
            midi_events.append((tick, 'note_on', note, vel))
            
        for note, prev_tick in active_notes.items():
            midi_events.append((prev_tick + 30, 'note_off', note, 0))
            
        midi_events.sort(key=lambda x: (x[0], 0 if x[1]=='note_on' else 1))
        
        mid = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
        
        last_time = 0
        for tick, ev_type, note, vel in midi_events:
            if tick < last_time: tick = last_time
            delta = tick - last_time
            # GM Percussion channel is 10 (index 9)
            if ev_type == 'note_on':
                track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
            else:
                track.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=delta))
            last_time = tick
            
        mid.save(filename)

def section_A(gen):
    # The Snare Awakening (Bars 1-8)
    for b in range(0, 16, 4):
        gen.add_hit(b, 38, 70)
        gen.add_hit(b + 0.5, 38, 40)
        gen.add_hit(b + 1.0, 38, 80)
        gen.add_hit(b + 1.5, 38, 40)
        
        gen.add_hit(b + 2.0, 38, 50)
        gen.add_hit(b + 2.25, 38, 50)
        gen.add_hit(b + 2.5, 38, 70)
        gen.add_hit(b + 2.75, 38, 40)
        
        gen.add_flam(b + 3.0, 38, 90)
        if b == 12:
            for i in range(4):
                gen.add_hit(b + 3.5 + i*0.125, 38, 50 + i*10)
        else:
            gen.add_drag(b + 3.75, 38, 70)

    for b in range(16, 32, 4):
        if b < 28:
            gen.add_hit(b + 2.0, 36, 80)
            gen.add_hit(b + 3.0, 44, 90)
        gen.add_hit(b, 36, 80)
        gen.add_hit(b + 1.0, 44, 90)
        
        gen.add_hit(b, 38, 50)
        gen.add_hit(b + 0.5, 38, 85)
        gen.add_hit(b + 0.75, 38, 40)
        gen.add_hit(b + 1.25, 38, 50)
        gen.add_hit(b + 1.5, 38, 90)
        gen.add_hit(b + 2.0, 38, 40)
        gen.add_hit(b + 2.5, 38, 85)
        
        if b < 28:
            gen.add_flam(b + 3.0, 38, 100)
            gen.add_hit(b + 3.5, 38, 50)
            gen.add_hit(b + 3.75, 38, 60)
        else:
            for i in range(8):
                gen.add_hit(b + 2.0 + i*0.25, 38, 60 + i*5)
                if i % 2 == 0:
                    gen.add_hit(b + 2.0 + i*0.25, 36, 80)

def section_B(gen):
    # The Groove Establishes (Bars 9-16)
    gen.add_hit(32, 49, 110)
    for b in range(32, 64, 4):
        for i in range(8):
            if b == 60 and i >= 4:
                continue
            if i == 6 and b % 8 == 4:
                gen.add_hit(b + i*0.5, 46, 90)
                gen.add_hit(b + i*0.5 + 0.5, 44, 80)
            elif not (i == 7 and b % 8 == 4):
                gen.add_hit(b + i*0.5, 42, 75 + (15 if i%2==0 else 0), feel_offset=2)
                
        gen.add_hit(b, 36, 100)
        gen.add_hit(b + 0.75, 36, 80)
        gen.add_hit(b + 1.0, 38, 105, feel_offset=5)
        
        if b != 60:
            gen.add_hit(b + 1.75, 38, 40)
            gen.add_hit(b + 2.25, 36, 90)
            gen.add_hit(b + 2.5, 36, 85)
            if b % 8 == 0:
                gen.add_hit(b + 3.0, 38, 105, feel_offset=5)
                gen.add_hit(b + 3.5, 38, 40)
                gen.add_hit(b + 3.75, 38, 40)
            else:
                gen.add_hit(b + 3.0, 38, 105, feel_offset=5)
                gen.add_hit(b + 3.75, 36, 90)
        else:
            gen.play_linear_lick(b + 2.0, 2.0, 
                [38, 38, 50, 50, 48, 48, 47, 47, 45, 45, 36, 36], 
                [100, 90, 95, 85, 90, 80, 85, 75, 80, 70, 100, 100])

def section_C(gen):
    # Latin / Tom Tribal Groove (Bars 17-24)
    gen.add_hit(64, 57, 110)
    for b in range(64, 96, 4):
        is_fill = (b % 16 == 12)
        for i in range(8):
            if is_fill and i >= 6:
                continue
            if i % 2 == 0:
                gen.add_hit(b + i*0.5, 36, 100)
            else:
                gen.add_hit(b + i*0.5, 43, 90)
                
        cb_offsets = [0.0, 0.5, 1.5, 2.0, 2.5, 3.5]
        for off in cb_offsets:
            if is_fill and off >= 3.0:
                continue
            gen.add_hit(b + off, 56, 95, feel_offset=3)
            
        if not is_fill:
            gen.add_hit(b + 0.75, 38, 60)
            gen.add_hit(b + 1.25, 50, 100)
            gen.add_hit(b + 2.75, 38, 60)
            gen.add_hit(b + 3.25, 50, 100)
        else:
            gen.add_hit(b + 0.75, 38, 60)
            gen.add_hit(b + 1.25, 50, 100)
            gen.add_hit(b + 2.0, 49, 110)
            gen.add_hit(b + 2.0, 36, 110)
            gen.play_linear_lick(b + 2.5, 1.5,
                [38, 38, 50, 50, 47, 47, 43, 43, 36, 36, 49, 36],
                [100]*12)

def section_D(gen):
    # Dynamic Drop & Polyrhythm (Bars 25-32)
    gen.add_hit(96, 49, 110)
    gen.add_hit(96, 57, 110)
    gen.add_hit(96, 36, 110)
    
    for b in range(96, 112, 4):
        for i in range(16):
            if i % 4 == 0:
                if not (b == 96 and i == 0):
                    gen.add_hit(b + i*0.25, 51, 80)
            else:
                gen.add_hit(b + i*0.25, 38, random.randint(25, 45))
                
        gen.add_hit(b + 1.0, 38, 95, feel_offset=5)
        gen.add_hit(b + 3.0, 38, 95, feel_offset=5)
        gen.add_hit(b + 0.0, 36, 80)
        gen.add_hit(b + 1.75, 36, 75)
        gen.add_hit(b + 2.5, 36, 75)
        
    for b in range(112, 128, 4):
        for i in range(4):
            gen.add_hit(b + i, 44, 100)
            
        is_last = (b == 124)
        for i in range(16 if not is_last else 8):
            pos = b + i*0.25
            if i % 3 == 0:
                gen.add_hit(pos, 53, 100)
                gen.add_hit(pos, 36, 100)
            elif i % 3 == 1:
                gen.add_hit(pos, 38, 60)
            else:
                gen.add_hit(pos, 38, 65)
                
        if is_last:
            gen.play_linear_lick(b + 2.0, 2.0,
                [38, 38, 50, 50, 36, 36, 48, 48, 47, 47, 36, 36, 45, 45, 43, 43],
                [110]*16)

def section_E(gen):
    # The Linear Showcase / Chops (Bars 33-40)
    gen.add_hit(128, 49, 115)
    for b in range(128, 144, 4):
        for i in range(4):
            beat_start = b + i
            if i == 0 or i == 2:
                if not (b == 128 and i == 0):
                    gen.add_hit(beat_start, 36, 100)
                gen.add_hit(beat_start, 46, 95)
                gen.add_hit(beat_start + 0.25, 42, 70)
                gen.add_hit(beat_start + 0.5, 38, 110)
                gen.add_hit(beat_start + 0.75, 36, 90)
            elif i == 1:
                gen.add_hit(beat_start, 42, 80)
                gen.add_hit(beat_start + 0.25, 38, 80)
                gen.add_hit(beat_start + 0.5, 36, 100)
                gen.add_hit(beat_start + 0.75, 36, 100)
            elif i == 3:
                if b == 140:
                    gen.play_linear_lick(beat_start, 1.0, [50, 48, 47, 45, 43, 36], [110]*6)
                else:
                    gen.add_hit(beat_start, 42, 80)
                    gen.add_hit(beat_start + 0.25, 38, 110)
                    gen.add_hit(beat_start + 0.5, 38, 50)
                    gen.add_hit(beat_start + 0.75, 36, 90)

    for b in range(144, 160, 4):
        if b < 156:
            notes = [38, 50, 36, 36, 48, 47,   36, 36, 45, 43, 36, 36]
            vels = [110, 100, 110, 110, 100, 100,   110, 110, 100, 100, 110, 110]
            if b == 144:
                notes[0] = 57
                gen.add_hit(b, 36, 110)
            gen.play_linear_lick(b, 2.0, notes, vels)
            
            gen.add_hit(b + 2.0, 49, 110)
            gen.add_hit(b + 2.0, 38, 110)
            gen.add_hit(b + 2.0, 36, 110)
            
            gen.add_hit(b + 2.5, 46, 90)
            gen.add_hit(b + 3.0, 38, 100)
            gen.add_hit(b + 3.5, 36, 90)
            gen.add_hit(b + 3.75, 36, 90)

    for i in range(32):
        vol = int(40 + (i / 31.0) * 75)
        gen.add_hit(156 + i*0.125, 49, vol)
        gen.add_hit(156 + i*0.125, 57, vol)
        if i % 4 == 0:
            gen.add_hit(156 + i*0.125, 36, vol)

def section_F(gen):
    # The Climax (Bars 41-52)
    for b in range(160, 176, 4):
        gen.add_hit(b, 49, 120)
        gen.add_hit(b, 57, 120)
        
        for i in range(16):
            beat = b + i*0.25
            if b == 172 and i >= 8:
                continue
            if i != 8:
                gen.add_hit(beat, 36, 100 + random.randint(-10, 10))
                
        for i in range(8):
            if b == 172 and i >= 4:
                continue
            gen.add_hit(b + i*0.5, 52, 110)
            
        if b != 172:
            gen.add_hit(b + 2.0, 38, 120)
        else:
            gen.play_linear_lick(b + 2.0, 2.0,
                [38, 38, 50, 50, 48, 48, 47, 47, 45, 45, 43, 43, 36, 36, 36, 36],
                [115]*16)

    for b in range(176, 192, 4):
        gen.add_hit(b, 49, 115)
        for i in range(8):
            gen.add_hit(b + i*0.5, 53, 110)
            
        hits = [
            (0.0, 36), (0.25, 36), (0.75, 38), 
            (1.25, 36), (1.5, 36), (2.0, 38),
            (2.5, 36), (2.75, 36), (3.25, 38),
            (3.75, 36)
        ]
        if b == 188:
            gen.play_linear_lick(b, 4.0,
                [50, 50, 50, 50, 48, 48, 48, 48, 47, 47, 47, 47, 45, 45, 43, 43]*2,
                [110]*32)
        else:
            for offset, note in hits:
                vel = 115 if note == 38 else 105
                gen.add_hit(b + offset, note, vel)

    for b in range(192, 208, 4):
        gen.add_hit(b, 49, 120)
        if b % 8 == 0:
            gen.add_hit(b + 1.5, 55, 110)
            gen.add_hit(b + 2.5, 55, 110)
            
        if b == 204:
            for i in range(32):
                vel = 80 + int((i/31)*40)
                gen.add_hit(b + i*0.125, 38, vel)
                if i % 4 == 0:
                    gen.add_hit(b + i*0.125, 36, vel)
        else:
            for i in range(16):
                pos = b + i*0.25
                if random.random() < 0.4:
                    gen.add_hit(pos, 38, random.randint(80, 115))
                else:
                    gen.add_hit(pos, 36, random.randint(90, 115))
                if i % 2 == 0:
                    gen.add_hit(pos, 49 if i%4==0 else 57, 105)

def section_G(gen):
    # The Grand Finale (Bars 53-60)
    hits = [208.0, 209.5, 211.0, 212.5]
    for i, h in enumerate(hits):
        gen.add_hit(h, 49, 120)
        if i % 2 == 0:
            gen.add_hit(h, 57, 120)
        else:
            gen.add_hit(h, 38, 120)
        gen.add_hit(h, 36, 120)
        
    gen.play_linear_lick(214.0, 2.0,
        [50, 50, 48, 48, 47, 47, 43, 43], [110]*8)
        
    hits2 = [216.0, 217.0, 218.0]
    for h in hits2:
        gen.add_hit(h, 49, 120)
        gen.add_hit(h, 57, 120)
        gen.add_hit(h, 36, 120)
        
    gen.play_linear_lick(218.5, 1.5,
        [38, 36, 36, 43, 38, 36, 36, 43], [115]*8)
        
    for i in range(16):
        gen.add_hit(220 + i*0.25, 38, 80 + i*2)
        gen.add_hit(220 + i*0.25, 36, 90)
        
    for i in range(24):
        beat = 224 + i*(1/6.0)
        tom = 50 if i < 6 else 48 if i < 12 else 47 if i < 18 else 43
        gen.add_hit(beat, tom, 100 + i)
        if i % 2 == 0:
            gen.add_hit(beat, 36, 110)
            
    for i in range(32):
        beat = 228 + i*0.125
        vel = 110 + int((i/31)*17)
        if i % 2 == 0:
            gen.add_hit(beat, 43, vel)
        else:
            gen.add_hit(beat, 38, vel)
        if i % 2 == 0:
            gen.add_hit(beat, 36, 110)
            
    # Final hits
    for h in [232, 234, 236, 238]:
        gen.add_hit(h, 49, 127)
        gen.add_hit(h, 57, 127)
        gen.add_hit(h, 36, 127)

def generate_solo():
    gen = SoloGenerator()
    section_A(gen)
    section_B(gen)
    section_C(gen)
    section_D(gen)
    section_E(gen)
    section_F(gen)
    section_G(gen)
    
    # Let cymbals ring out
    gen.events.append((int(242 * gen.ticks_per_beat), 36, 0))
    gen.export("solo.mid")

if __name__ == "__main__":
    generate_solo()
