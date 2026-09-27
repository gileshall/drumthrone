import mido
import random
import math

def cymbal_swell(start_beat, length, p1, p2, start_vel, end_vel):
    notes = []
    count = int(length * 12) # 32nd note triplets
    for i in range(count):
        b = start_beat + i / 12.0
        # Quadratic curve for a realistic, surging swell
        curve = (i / count) ** 2
        v = start_vel + (end_vel - start_vel) * curve
        pitch = p1 if i % 2 == 0 else p2
        notes.append((b, pitch, int(v)))
    return notes

def play_rudiment(start_beat, length_beats, subdivision, rudiment_type, kit_mapping, dynamics):
    notes = []
    step = 1.0 / subdivision
    count = int(length_beats * subdivision)
    pattern_len = len(rudiment_type)
    
    for i in range(count):
        b = start_beat + i * step
        stroke = rudiment_type[i % pattern_len]
        
        is_accent = stroke.isupper()
        limb = stroke.upper()
        
        pitch = kit_mapping.get(limb, 38)
        vel_base = dynamics['accent'] if is_accent else dynamics['tap']
        
        notes.append((b, pitch, vel_base))
    return notes

class SoloBuilder:
    def __init__(self):
        self.notes = []
        self.current_beat = 0.0
        
    def add_notes(self, new_notes):
        self.notes.extend(new_notes)
        
    def advance(self, beats):
        self.current_beat += beats
        
    def get_notes(self):
        return self.notes

def humanize_notes(notes):
    humanized = []
    for beat, pitch, vel in notes:
        # Micro-timing (push/pull), max 0.05 beat variance
        beat_offset = random.gauss(0, 0.015)
        beat_offset = max(-0.05, min(0.05, beat_offset))
        
        b = max(0.0, beat + beat_offset)
        
        # Humanize velocity, bounded 1-127
        v = int(round(vel + random.gauss(0, 5)))
        v = max(1, min(127, v))
        
        humanized.append((b, pitch, v))
        
    # Sort strictly by time to avoid sequence errors
    humanized.sort(key=lambda x: x[0])
    return humanized

def main():
    random.seed(42)
    
    KICK = 36
    SNARE = 38
    HAT_CLOSED = 42
    HAT_OPEN = 46
    HAT_PEDAL = 44
    RIDE = 51
    RIDE_BELL = 53
    CRASH1 = 49
    CRASH2 = 57
    SPLASH = 55
    TOM1 = 50 
    TOM2 = 48 
    TOM3 = 47 
    TOM4 = 45 
    TOM5 = 43 
    TOM6 = 41 

    sb = SoloBuilder()
    
    # --- BARS 1-4: Intro (Atmospheric Swells) ---
    sb.add_notes(cymbal_swell(sb.current_beat, 16, CRASH1, CRASH2, 10, 75))
    for b in [0, 2.5, 4, 7, 8, 10.5, 12, 15]:
        sb.add_notes([(sb.current_beat + b, TOM6, 80), (sb.current_beat + b + 0.1, TOM6, 60)])
        sb.add_notes([(sb.current_beat + b, KICK, 80)])
    sb.advance(16)
    
    # --- BARS 5-8: Motif A (Tribal Toms) ---
    for i in range(4):
        kit = {'R': TOM6, 'L': TOM4, 'K': KICK}
        dyn = {'accent': 100 + i*5, 'tap': 60 + i*5}
        sb.add_notes(play_rudiment(sb.current_beat, 3, 4, "RlrrLrll", kit, dyn))
        
        fill = play_rudiment(sb.current_beat + 3, 1, 6, "RlrLrl", {'R': TOM2, 'L': TOM1}, {'accent': 110, 'tap': 80})
        sb.add_notes(fill)
        sb.add_notes([(sb.current_beat + 3, KICK, 100), (sb.current_beat + 3.5, KICK, 100)])
        sb.advance(4)
        
    # --- BARS 9-16: Motif B (Linear Funk Build) ---
    for i in range(8):
        if i == 0:
            sb.add_notes([(sb.current_beat, CRASH1, 110)])
            
        pat = "K s S s K K s S K s S s K s K s " if i < 4 else "K s S h K K s S K h S s K s O P "
        step = 0.25
        for j, char in enumerate(pat.split()):
            b = sb.current_beat + j * step
            if char == 'K': sb.add_notes([(b, KICK, random.randint(90, 110))])
            elif char == 'H': sb.add_notes([(b, HAT_CLOSED, random.randint(80, 100))])
            elif char == 'h': sb.add_notes([(b, HAT_CLOSED, random.randint(40, 60))])
            elif char == 'S': sb.add_notes([(b, SNARE, random.randint(100, 120))])
            elif char == 's': sb.add_notes([(b, SNARE, random.randint(20, 40))])
            elif char == 'O': sb.add_notes([(b, HAT_OPEN, random.randint(80, 100))])
            elif char == 'P': sb.add_notes([(b, HAT_PEDAL, random.randint(70, 90))])
        sb.advance(4)
        
    # --- BARS 17-24: Ride Fusion Groove ---
    for i in range(8):
        if i == 0:
            sb.add_notes([(sb.current_beat, CRASH2, 110)])
            
        ride_hits = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]
        for b in ride_hits:
            if i % 2 == 1 and b in [1.5, 3.5]:
                sb.add_notes([(sb.current_beat + b, RIDE_BELL, 110)])
            else:
                sb.add_notes([(sb.current_beat + b, RIDE, 90 + (10 if b % 1 == 0 else 0))])
                
        sb.add_notes([(sb.current_beat + 1, SNARE, 110), (sb.current_beat + 3, SNARE, 110)])
        sb.add_notes([(sb.current_beat + 1, HAT_PEDAL, 80), (sb.current_beat + 3, HAT_PEDAL, 80)])
        
        for gb in [0.75, 1.25, 2.75, 3.25, 3.75]:
            if random.random() > 0.3:
                sb.add_notes([(sb.current_beat + gb, SNARE, random.randint(30, 50))])
                
        kicks = [0, 2.25]
        if i % 2 == 1: kicks.extend([1.75, 3.5])
        for kb in kicks:
            sb.add_notes([(sb.current_beat + kb, KICK, 100)])
            
        if i % 4 == 3:
            sb.notes = [n for n in sb.notes if not (n[0] >= sb.current_beat + 2 and n[0] < sb.current_beat + 4)]
            fill = play_rudiment(sb.current_beat + 2, 2, 6, "RlrLrl", {'R': TOM1, 'L': TOM3}, {'accent': 110, 'tap': 80})
            sb.add_notes(fill)
            sb.add_notes([(sb.current_beat + 2, KICK, 100)])
        sb.advance(4)
        
    # --- BARS 25-32: Tom Solo (Development) ---
    tom_patterns = [
        ("RlrLrl", {'R': TOM1, 'L': TOM2}, 1, 6),
        ("RlrLrl", {'R': TOM3, 'L': TOM4}, 1, 6),
        ("Rlrlkk", {'R': TOM1, 'L': TOM3, 'K': KICK}, 1, 6),
        ("Rlrlkk", {'R': TOM5, 'L': TOM6, 'K': KICK}, 1, 6),
        ("RllrrL", {'R': SNARE, 'L': TOM1}, 1, 6),
        ("RllrrL", {'R': TOM3, 'L': TOM5}, 1, 6),
        ("RlrkLrlk", {'R': TOM1, 'L': TOM2, 'K': KICK}, 2, 4),
        ("RlrkLrlk", {'R': TOM4, 'L': TOM6, 'K': KICK}, 2, 4),
    ]
    sb.add_notes([(sb.current_beat, CRASH1, 110), (sb.current_beat, KICK, 110)])
    for i in range(8):
        beats_filled = 0
        while beats_filled < 4:
            available = [p for p in tom_patterns if p[2] <= 4 - beats_filled]
            pat = random.choice(available)
            dyn = {'accent': random.randint(100, 120), 'tap': random.randint(60, 80)}
            
            sb.add_notes(play_rudiment(sb.current_beat + beats_filled, pat[2], pat[3], pat[0], pat[1], dyn))
            
            if beats_filled <= 1 and beats_filled + pat[2] > 1:
                sb.add_notes([(sb.current_beat + 1, HAT_PEDAL, 90)])
            if beats_filled <= 3 and beats_filled + pat[2] > 3:
                sb.add_notes([(sb.current_beat + 3, HAT_PEDAL, 90)])
                
            beats_filled += pat[2]
        sb.advance(4)
        
    # --- BARS 33-40: Snare March Crescendo ---
    for i in range(8):
        cf = i / 7.0 
        base_vel, acc_vel = int(40 + cf * 50), int(90 + cf * 30)
        
        for b in range(16):
            beat_offset = b * 0.25
            if b in [4, 12]:
                sb.add_notes([(sb.current_beat + beat_offset, SNARE, acc_vel)])
                if i % 2 == 1:
                    sb.add_notes([(sb.current_beat + beat_offset, CRASH1, acc_vel)])
                    sb.add_notes([(sb.current_beat + beat_offset, KICK, acc_vel)])
            else:
                if random.random() < 0.3 + cf * 0.3:
                    sb.add_notes([(sb.current_beat + beat_offset, SNARE, base_vel)])
                    sb.add_notes([(sb.current_beat + beat_offset + 0.125, SNARE, base_vel)])
                else:
                    sb.add_notes([(sb.current_beat + beat_offset, SNARE, base_vel)])
            if b in [0, 8]:
                sb.add_notes([(sb.current_beat + beat_offset, KICK, acc_vel)])
                
        for b in range(8):
            sb.add_notes([(sb.current_beat + b * 0.5, HAT_PEDAL, int(60 + cf*40))])
        sb.advance(4)
        
    # --- BARS 41-48: Climax (Double Bass & Heavy Crashes) ---
    sb.add_notes([(sb.current_beat, CRASH1, 127), (sb.current_beat, CRASH2, 127)])
    for i in range(8):
        for b in range(16):
            sb.add_notes([(sb.current_beat + b * 0.25, KICK, 110 if b % 2 == 0 else 95)])
            
        sb.add_notes([(sb.current_beat + 1, SNARE, 120), (sb.current_beat + 3, SNARE, 120)])
        sb.add_notes([(sb.current_beat + 1, CRASH1, 110), (sb.current_beat + 3, CRASH2, 110)])
        
        for b in [0, 0.75, 1.5, 2.25, 3.5]:
            if random.random() > 0.5:
                sb.add_notes([(sb.current_beat + b, RIDE_BELL, 120)])
                
        if i % 2 == 1:
            sb.notes = [n for n in sb.notes if not (n[0] >= sb.current_beat + 2 and n[0] < sb.current_beat + 4)]
            tom_run = [SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, KICK]
            for b in range(16):
                sb.add_notes([(sb.current_beat + 2 + b * 0.125, tom_run[b // 2], 110 + random.randint(-10, 10))])
        sb.advance(4)
        
    # --- BARS 49-56: Polymetric Tension ---
    for i in range(8):
        if i == 0:
            sb.add_notes([(sb.current_beat, CRASH1, 120), (sb.current_beat, KICK, 110)])
            
        polymeter = [RIDE_BELL, SNARE, KICK]
        for b in range(16):
            beat_offset = b * 0.25
            if i % 4 == 3 and beat_offset >= 2.0:
                continue
                
            pitch = polymeter[(i * 16 + b) % 3]
            sb.add_notes([(sb.current_beat + beat_offset, pitch, 120 if pitch != KICK else 110)])
            
        for b in range(4):
            sb.add_notes([(sb.current_beat + b, HAT_PEDAL, 100)])
            
        if i % 4 == 3:
            fill = play_rudiment(sb.current_beat + 2, 2, 6, "Rlrlkk", {'R': TOM2, 'L': TOM4, 'K': KICK}, {'accent': 120, 'tap': 100})
            sb.add_notes(fill)
        sb.advance(4)
        
    # --- BARS 57-64: The Final Build (Half-Time Showcases) ---
    for i in range(8):
        if i % 2 == 0:
            sb.add_notes([(sb.current_beat, CRASH1, 120), (sb.current_beat, KICK, 120)])
            sb.add_notes([(sb.current_beat + 1, HAT_OPEN, 100), (sb.current_beat + 1.5, KICK, 110)])
            sb.add_notes([(sb.current_beat + 2, SNARE, 127), (sb.current_beat + 2, CRASH2, 110)])
            sb.add_notes([(sb.current_beat + 3, HAT_OPEN, 100), (sb.current_beat + 3.25, KICK, 110), (sb.current_beat + 3.75, KICK, 110)])
            sb.add_notes([(sb.current_beat + 4, HAT_PEDAL, 90)]) 
        else:
            if i == 1:
                kit = {'R': TOM1, 'L': TOM3, 'K': KICK}
                sb.add_notes(play_rudiment(sb.current_beat, 4, 6, "Rlrlkk", kit, {'accent': 120, 'tap': 100}))
            elif i == 3:
                toms = [SNARE, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, KICK]
                for b in range(32):
                    sb.add_notes([(sb.current_beat + b * 0.125, toms[b // 4], 120)])
            elif i == 5:
                pat = "RllrrL"
                sb.add_notes(play_rudiment(sb.current_beat, 2, 6, pat, {'R': TOM2, 'L': SNARE}, {'accent': 127, 'tap': 80}))
                sb.add_notes(play_rudiment(sb.current_beat+2, 2, 6, pat, {'R': TOM4, 'L': TOM6}, {'accent': 127, 'tap': 80}))
            elif i == 7:
                for b in range(16):
                    sb.add_notes([(sb.current_beat + b * 0.125, SNARE, 90 + b*2)])
                    sb.add_notes([(sb.current_beat + b * 0.125 + 0.0625, KICK, 90 + b*2)])
                sb.add_notes([(sb.current_beat + 2, TOM1, 127), (sb.current_beat + 2, TOM2, 127), (sb.current_beat + 2, KICK, 127)])
                sb.add_notes([(sb.current_beat + 2.5, TOM3, 127), (sb.current_beat + 2.5, TOM4, 127)])
                sb.add_notes([(sb.current_beat + 3, TOM5, 127), (sb.current_beat + 3, TOM6, 127), (sb.current_beat + 3, KICK, 127)])
                sb.add_notes([(sb.current_beat + 3.5, SNARE, 127), (sb.current_beat + 3.5, CRASH1, 127)])
        sb.advance(4)
        
    # --- BARS 65-66: The Final Hit ---
    sb.add_notes([(sb.current_beat, CRASH1, 127), (sb.current_beat, CRASH2, 127), (sb.current_beat, KICK, 127)])
    sb.add_notes([(sb.current_beat + 2, SPLASH, 80)])
    sb.advance(4)
    sb.add_notes([(sb.current_beat, CRASH1, 127), (sb.current_beat, KICK, 127)])
    sb.advance(4) 
    
    # Process notes and prepare MIDI elements
    humanized = humanize_notes(sb.get_notes())
    
    ticks_per_beat = 480
    mid = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)
    
    tempo_track = mido.MidiTrack()
    tempo_track.append(mido.MetaMessage('track_name', name='Tempo Curve', time=0))
    tempo_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    mid.tracks.append(tempo_track)
    
    note_track = mido.MidiTrack()
    note_track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    mid.tracks.append(note_track)
    
    # Build tempo envelope
    tempos = [(0, 125), (64, 130)]
    for i in range(16):
        tempos.append((128 + i * 4, 132 + (i / 15) * 6))
    tempos.extend([(192, 138), (256, 120)])
    
    tempo_events = sorted([(int(b * ticks_per_beat), mido.bpm2tempo(bpm)) for b, bpm in tempos])
    
    last_tick = 0
    for abs_tick, tempo_val in tempo_events:
        delta = abs_tick - last_tick
        tempo_track.append(mido.MetaMessage('set_tempo', tempo=int(tempo_val), time=delta))
        last_tick = abs_tick
    tempo_track.append(mido.MetaMessage('end_of_track', time=0))
    
    # Build note events
    note_events = []
    for b, pitch, vel in humanized:
        tick_on = int(b * ticks_per_beat)
        tick_off = int((b + 0.02) * ticks_per_beat) # Very short gate time for realistic GM handling
        note_events.append((tick_on, 'note_on', pitch, vel))
        note_events.append((tick_off, 'note_off', pitch, 0))
        
    # Sort events by absolute tick; note_off preceding note_on to prevent muting identical pitches
    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))
    
    last_tick = 0
    for abs_tick, msg_type, pitch, vel in note_events:
        delta = abs_tick - last_tick
        if msg_type == 'note_on':
            note_track.append(mido.Message('note_on', channel=9, note=pitch, velocity=vel, time=delta))
        else:
            note_track.append(mido.Message('note_off', channel=9, note=pitch, velocity=vel, time=delta))
        last_tick = abs_tick
    note_track.append(mido.MetaMessage('end_of_track', time=0))
    
    mid.save('solo.mid')

if __name__ == '__main__':
    main()
