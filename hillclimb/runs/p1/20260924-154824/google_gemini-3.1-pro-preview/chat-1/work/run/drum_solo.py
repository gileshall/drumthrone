import mido
import random
import math

def generate_solo():
    # Set a fixed seed to guarantee identical output on every run
    random.seed(42)
    PPQ = 480
    
    # General MIDI Drum Map (Channel 10)
    MAP = {
        'K': 36, 'K2': 35,
        'S': 38, 'S_rim': 37,
        'H_c': 42, 'H_o': 46, 'H_p': 44,
        'T1': 50, 'T2': 48, 'T3': 45, 'T4': 41,
        'C1': 49, 'C2': 57, 'Spl': 55, 'Chin': 52,
        'R1': 51, 'R_bell': 53,
        'Cow': 56, 'Tim1': 65, 'Tim2': 66
    }
    
    hits = []
    
    def add_hit(beat, instr, vel):
        hits.append((beat, instr, int(vel)))

    def cymbal_swell(start_beat, length_beats, instr='C1', max_vel=90):
        step = 1.0 / 8 # 32nd notes
        num_notes = int(length_beats * 8)
        for i in range(num_notes):
            beat = start_beat + i * step
            progress = i / max(1, (num_notes - 1))
            vel = max_vel * (math.exp(progress) - 1) / (math.e - 1)
            if vel > 5:
                add_hit(beat, instr, vel)

    def play_rudiment(b, pattern, dur, orchestration, vel_accent, vel_tap):
        notes = pattern.split()
        step = dur / len(notes)
        for i, n in enumerate(notes):
            time = b + i * step
            is_accent = n.isupper()
            limb = n.upper()
            instr = orchestration.get(limb)
            if not instr: continue
            vel = vel_accent if is_accent else vel_tap
            vel += random.randint(-4, 4) # micro-dynamics
            add_hit(time, instr, vel)
            
    def main_groove_measure(b, intensity=0, fill=False):
        fill_start = 3 if fill else 4
        
        # Hi-hats with micro-timing (swing on the offbeats)
        for i in range(8):
            hb = b + i * 0.5
            if hb >= b + fill_start: break
            if i % 2 == 1: hb += 0.03 # lay back the 'and'
            vel = 70 + intensity * 10 if i % 2 == 0 else 50 + intensity * 5
            hat = 'H_o' if (i == 3 and random.random() < 0.3) else 'H_c'
            add_hit(hb, hat, vel)
            # occasional 16th note drag
            if i % 2 == 0 and random.random() < (0.2 + intensity*0.1):
                add_hit(hb + 0.25, 'H_c', vel - 15)
                
        # Kick drum with syncopation
        add_hit(b, 'K', 100 + intensity * 5)
        if b + 1.5 < b + fill_start: add_hit(b + 1.5, 'K', 90 + intensity * 5)
        if b + 2.5 < b + fill_start: add_hit(b + 2.5, 'K', 95 + intensity * 5)
        if random.random() > 0.5 and b + 3.5 < b + fill_start:
            add_hit(b + 3.5, 'K', 90 + intensity * 5)
            
        # Backbeat snare
        add_hit(b + 1, 'S', 105 + intensity * 5)
        if b + 3 < b + fill_start: add_hit(b + 3, 'S', 105 + intensity * 5)
        
        # Snare ghost notes against accents
        ghosts = [1.25, 1.75, 2.25, 2.75, 3.25, 3.75]
        for g in ghosts:
            if b + g < b + fill_start and random.random() < 0.6:
                add_hit(b + g, 'S', random.randint(25, 45) + intensity * 5)
                
        if fill:
            if random.random() < 0.5:
                # 16th triplets down the toms
                step = 1.0 / 6
                for i in range(6):
                    add_hit(b + 3 + i*step, ['S', 'T1', 'T2', 'T3', 'T4', 'K'][i], 90 + i*3)
            else:
                # Linear 32nds incorporating kick
                for i, instr in enumerate(['S', 'K', 'T1', 'K', 'T2', 'K', 'T4', 'K']):
                    add_hit(b + 3 + i/8.0, instr, 100)

    def ride_groove_measure(b, intensity=1, fill=False):
        fill_start = 2 if fill else 4
        
        for i in range(8):
            hb = b + i * 0.5
            if hb >= b + fill_start: break
            if i % 2 == 1: hb += 0.04
            instr = 'R_bell' if i in [0, 4] and random.random() < 0.5 else 'R1'
            vel = 85 if i % 2 == 0 else 65
            add_hit(hb, instr, vel)
            if i % 2 == 1 and random.random() < 0.5:
                add_hit(hb + 0.33, 'R1', vel - 15) # Jazz triplet skip
                
        if b + 1 < b + fill_start: add_hit(b + 1, 'H_p', 80)
        if b + 3 < b + fill_start: add_hit(b + 3, 'H_p', 80)
        
        add_hit(b, 'K', 105)
        if b + 2.5 < b + fill_start: add_hit(b + 2.5, 'K', 100)
        if random.random() < 0.5 and b + 3.25 < b + fill_start: add_hit(b + 3.25, 'K', 95)
        
        add_hit(b + 1, 'S', 110)
        if b + 3 < b + fill_start: add_hit(b + 3, 'S', 110)
        
        for g in [0.75, 1.25, 2.25, 2.75, 3.25]:
            if b + g < b + fill_start and random.random() < 0.7:
                add_hit(b + g, 'S', random.randint(30, 50))
                
        if fill:
            # 2-beat linear fill (Gospel chops style)
            pattern = ['S', 'T1', 'K', 'T2', 'T3', 'K', 'T4', 'S', 'T1', 'T2', 'K', 'K']
            step = 2.0 / 12
            for i, p in enumerate(pattern):
                add_hit(b + 2 + i*step, p, 105)

    def latin_percussion(b):
        # 3-over-4 Cascara cross-rhythm on cowbell
        cascara = [0, 0.75, 1.5, 2.25, 3, 3.75]
        for c in cascara:
            add_hit(b + c, 'Cow', 90)
        # Clave variations on rim click
        clave = [0.5, 1.75, 3]
        for cl in clave:
            add_hit(b + cl, 'S_rim', 105)
        # Timbale shell hits
        add_hit(b + 1, 'Tim1', 80)
        add_hit(b + 2.5, 'Tim2', 85)
        add_hit(b + 3.5, 'Tim2', 80)
        # Tumbao bass drum
        add_hit(b + 1.5, 'K2', 90)
        add_hit(b + 2.5, 'K2', 95)
        add_hit(b + 1, 'H_p', 80)
        add_hit(b + 3, 'H_p', 80)

    def double_bass_groove(b):
        # Rolling 16th notes on the kick
        for i in range(16):
            kb = b + i * 0.25
            vel = 115 if i % 4 == 0 else 95
            add_hit(kb, 'K', vel)
        for i in range(4):
            add_hit(b + i, 'Chin', 110)
        add_hit(b + 1, 'S', 120)
        add_hit(b + 3, 'S', 120)
        if random.random() < 0.3:
            add_hit(b + 2.5, 'C1', 115)
            add_hit(b + 2.5, 'S', 110)

    def heavy_groove(b):
        # Halftime heavy pocket
        add_hit(b, 'C1', 110)
        add_hit(b, 'K', 120)
        add_hit(b + 1, 'H_o', 100)
        add_hit(b + 2, 'S', 127); add_hit(b + 2, 'C2', 110)
        add_hit(b + 3, 'H_o', 100)
        add_hit(b + 1.5, 'K', 110)
        add_hit(b + 3.5, 'K', 110)
        if random.random() < 0.5:
            add_hit(b + 2.75, 'K', 100)
        add_hit(b + 1.75, 'S', 60)
        add_hit(b + 2.25, 'S', 60)

    def tribal_groove(b):
        # Syncopated tom groove
        add_hit(b, 'T4', 120); add_hit(b, 'K', 120)
        add_hit(b + 0.5, 'T3', 100)
        add_hit(b + 1, 'T4', 110); add_hit(b + 1, 'S', 120); add_hit(b+1, 'C1', 110)
        add_hit(b + 1.5, 'T3', 100)
        add_hit(b + 2, 'T4', 120); add_hit(b + 2, 'K', 120)
        add_hit(b + 2.75, 'T2', 110)
        add_hit(b + 3, 'S', 127); add_hit(b + 3, 'C2', 110)
        add_hit(b + 3.5, 'T1', 110)

    # ------------------ COMPOSITION TIMELINE ------------------
    # Measures 1-4 (beats 0-16): Intro - Spatial swells and heavy kicks
    cymbal_swell(0, 4, 'R1', 80)
    add_hit(0, 'K', 100)
    cymbal_swell(4, 4, 'C1', 90)
    add_hit(4, 'K', 100); add_hit(6, 'K', 90)
    cymbal_swell(8, 4, 'C2', 100)
    add_hit(8, 'K', 100); add_hit(10.5, 'K', 90); add_hit(11.5, 'K', 100)
    add_hit(12, 'T1', 110); add_hit(12, 'T2', 110)
    add_hit(12.75, 'T3', 100); add_hit(13.5, 'T4', 110); add_hit(13.5, 'K', 100)
    add_hit(14.25, 'T2', 100); add_hit(14.75, 'T1', 110)
    add_hit(15, 'S', 110); add_hit(15.03, 'S', 90) # Flam
    add_hit(15.5, 'K', 110); add_hit(15.75, 'K', 110)

    # Measures 5-12 (beats 16-48): Motif Statement - Main Groove
    for m in range(8):
        b = 16 + m * 4
        if m == 0: add_hit(b, 'C1', 100)
        main_groove_measure(b, intensity=0, fill=(m % 4 == 3))

    # Measures 13-16 (beats 48-64): Development - Ride Cymbal Groove
    for m in range(4):
        b = 48 + m * 4
        if m == 0: add_hit(b, 'C2', 105)
        ride_groove_measure(b, intensity=1, fill=(m == 3))

    # Measures 17-24 (beats 64-96): First Solo (Hands Focus & Syncopation)
    orch1 = {'R': 'R1', 'L': 'S'}
    play_rudiment(64, "R l r r L r l l R l r r L r l l", 4.0, orch1, 105, 45)
    for i in range(4): add_hit(64 + i, 'H_p', 80)
    add_hit(64, 'K', 100); add_hit(65.5, 'K', 95); add_hit(66.5, 'K', 95)
    
    orch2 = {'R': 'T2', 'L': 'T1'}
    play_rudiment(68, "R l r r L r l l R l r r L r l l", 4.0, orch2, 105, 65)
    add_hit(68, 'K', 100); add_hit(69.5, 'K', 95)
    for i in range(4): add_hit(68 + i, 'H_p', 80)

    play_rudiment(72, "R l K K R l K K R l K K R l K K", 2.0, {'R': 'S', 'L': 'S', 'K': 'K'}, 110, 60)
    play_rudiment(74, "R l r l R l r l R l r l R l r l", 2.0, {'R': 'T3', 'L': 'T4'}, 110, 80)

    # Displaced accents over rudiments
    play_rudiment(76, "R l r l L r l r R l r l L r l r", 2.0, {'R':'S', 'L':'S'}, 105, 45)
    add_hit(76, 'C1', 110); add_hit(76, 'K', 110)
    add_hit(76.75, 'C2', 110); add_hit(76.75, 'K', 110)
    add_hit(77.5, 'C1', 110); add_hit(77.5, 'K', 110)
    play_rudiment(78, "R l r l L r l r R l r l L r l r", 2.0, {'R':'T1', 'L':'T2'}, 110, 80)

    # Six-stroke rolls traveling
    play_rudiment(80, "R l l r r L R l l r r L R l l r r L R l l r r L", 4.0, {'R': 'S', 'L': 'S'}, 110, 50)
    add_hit(80, 'K', 100); add_hit(81.5, 'K', 100); add_hit(83, 'K', 100)
    for i in range(4): add_hit(80 + i, 'H_p', 85)
    play_rudiment(84, "R l l r r L R l l r r L R l l r r L R l l r r L", 4.0, {'R': 'T1', 'L': 'T3'}, 110, 70)
    add_hit(84, 'K', 100); add_hit(85.5, 'K', 100); add_hit(87, 'K', 100)

    # Tension build-up (8th note triplets)
    for i in range(24):
        b = 88 + i / 3.0
        vel = 60 + i * 2
        add_hit(b, ['S', 'T1', 'T2', 'T3'][i % 4], vel)
        if i % 3 == 0: add_hit(b, 'K', vel)

    # Measures 25-32 (beats 96-128): Breakdown - Latin / Percussion focus
    for m in range(7):
        b = 96 + m * 4
        if m == 0: add_hit(b, 'Spl', 90)
        latin_percussion(b)
    
    b = 124
    add_hit(b, 'S_rim', 100); add_hit(b+1, 'S_rim', 100)
    play_rudiment(126, "R l r l R l r l R l r l R l r l", 2.0, {'R':'T1', 'L':'T2'}, 105, 75)

    # Measures 33-40 (beats 128-160): Marching Snare Build Up
    for m in range(4):
        b = 128 + m * 4
        # Polyrhythmic rudiments
        play_rudiment(b, "R r l l R", 1.0, {'R':'S', 'L':'S'}, 100 + m*5, 50 + m*5)
        play_rudiment(b + 1, "L l r r L", 1.0, {'R':'S', 'L':'S'}, 100 + m*5, 50 + m*5)
        play_rudiment(b + 2, "R l r L r l", 1.0, {'R':'S', 'L':'S'}, 100 + m*5, 50 + m*5)
        play_rudiment(b + 3, "R l R l", 1.0, {'R':'S', 'L':'S'}, 105 + m*5, 80 + m*5)
        add_hit(b, 'K', 90 + m*5); add_hit(b + 2, 'K', 90 + m*5)
        add_hit(b + 1, 'H_p', 90); add_hit(b + 3, 'H_p', 90)

    # Orchestrating rudiments around the kit
    for m in range(4):
        b = 144 + m * 4
        if m < 3:
            play_rudiment(b, "R r l l R", 1.0, {'R':'T1', 'L':'S'}, 110, 70)
            play_rudiment(b + 1, "L l r r L", 1.0, {'R':'S', 'L':'T2'}, 110, 70)
            play_rudiment(b + 2, "R l r L r l", 1.0, {'R':'T3', 'L':'S'}, 110, 70)
            play_rudiment(b + 3, "R l R l", 1.0, {'R':'T4', 'L':'T4'}, 115, 90)
            add_hit(b, 'K', 105); add_hit(b + 1.5, 'K', 105)
            add_hit(b + 2, 'K', 105); add_hit(b + 3.5, 'K', 105)
        else:
            # Huge final fill entering climax
            play_rudiment(b, "R l r l R l r l", 1.0, {'R':'S', 'L':'S'}, 120, 110)
            play_rudiment(b+1, "R l r l R l r l", 1.0, {'R':'T1', 'L':'T2'}, 120, 110)
            play_rudiment(b+2, "R l r l R l r l", 1.0, {'R':'T3', 'L':'T4'}, 120, 110)
            play_rudiment(b+3, "K K K K K K K K", 1.0, {'K':'K'}, 120, 120)
            add_hit(b+3, 'C1', 120); add_hit(b+3.5, 'C2', 120)

    # Measures 41-48 (beats 160-192): Climax - Double Bass 
    for m in range(7):
        b = 160 + m * 4
        if m == 0: add_hit(b, 'C1', 127); add_hit(b, 'C2', 127)
        double_bass_groove(b)
        
    play_rudiment(188, "R l r l R l r l R l r l R l r l", 2.0, {'R':'S', 'L':'S'}, 120, 110)
    add_hit(188, 'C1', 120)
    play_rudiment(190, "R l r l R l r l R l r l R l r l", 2.0, {'R':'T1', 'L':'T2'}, 120, 115)
    play_rudiment(190, "K K K K K K K K", 2.0, {'K':'K'}, 120, 120) # Overlay kicks

    # Measures 49-56 (beats 192-224): Heavy Reprise
    for m in range(7):
        heavy_groove(192 + m * 4)
        
    # Polyrhythmic (groups of 3) fill
    b = 220; add_hit(b, 'C1', 120); add_hit(b, 'K', 120)
    for i in range(5):
        t = b + i * 0.75
        if t >= b + 4: break
        add_hit(t, 'S', 115); add_hit(t, 'C2', 110)
        add_hit(t + 0.25, 'K', 100); add_hit(t + 0.50, 'K', 100)

    # Measures 57-60 (beats 224-240): The Finale
    for m in range(2):
        tribal_groove(224 + m * 4)

    # Descending 32nd note runs with constant kicks
    play_rudiment(232, "R l r l R l r l", 1.0, {'R':'S', 'L':'S'}, 120, 110)
    play_rudiment(233, "R l r l R l r l", 1.0, {'R':'T1', 'L':'T1'}, 120, 110)
    play_rudiment(234, "R l r l R l r l", 1.0, {'R':'T2', 'L':'T2'}, 120, 110)
    play_rudiment(235, "R l r l R l r l", 1.0, {'R':'T4', 'L':'T4'}, 120, 110)
    for i in range(16):
        add_hit(232 + i*0.25, 'K', 110)

    # Syncopated Big Band ending hits
    add_hit(236, 'C1', 127); add_hit(236, 'C2', 127); add_hit(236, 'S', 127); add_hit(236, 'K', 127)
    add_hit(237.5, 'C1', 127); add_hit(237.5, 'S', 127); add_hit(237.5, 'K', 127)
    add_hit(238.5, 'C2', 127); add_hit(238.5, 'T4', 127); add_hit(238.5, 'K', 127)
    add_hit(239.5, 'C1', 127); add_hit(239.5, 'C2', 127); add_hit(239.5, 'S', 127); add_hit(239.5, 'K', 127)

    # ------------------ MIDI GENERATION ------------------
    note_events = {}
    for h in hits:
        beat, instr, vel = h
        note = MAP[instr]
        vel = max(1, min(127, int(vel)))
        # Humanize timing (+/- 4 ticks = ~8ms error margin)
        tick = max(0, int(beat * PPQ) + random.randint(-4, 4))
        note_events.setdefault(note, []).append((tick, vel))

    events = []
    events.append((0, mido.MetaMessage('time_signature', numerator=4, denominator=4)))

    # Tempo Map to let the solo "breathe" dynamically
    for b in range(240):
        if b < 16: bpm = 110 + (b / 16.0) * 5
        elif b < 48: bpm = 115 + math.sin(b * math.pi / 8) * 2
        elif b < 64: bpm = 117 + (b - 48)/16.0 * 5
        elif b < 96: bpm = 122 + math.sin(b * math.pi / 4) * 3
        elif b < 128: bpm = 122 - ((b - 96) / 32.0) * 12
        elif b < 160: bpm = 110 + ((b - 128) / 32.0) * 25
        elif b < 192: bpm = 135 + math.sin(b * math.pi / 2) * 2
        elif b < 224: bpm = 125
        else:
            bpm = 130
            if b >= 236: bpm = 130 - (b - 236) * 15 # Ritardando finale
                
        tick = int(b * PPQ)
        tempo = mido.bpm2tempo(bpm)
        events.append((tick, mido.MetaMessage('set_tempo', tempo=tempo)))

    # Eliminate overlapping Note-Ons and ensure clean Note-Offs
    for note, occs in note_events.items():
        occs.sort(key=lambda x: x[0])
        for i in range(len(occs)):
            tick, vel = occs[i]
            events.append((tick, mido.Message('note_on', channel=9, note=note, velocity=vel)))
            
            off_tick = tick + 20
            if i + 1 < len(occs):
                next_tick = occs[i+1][0]
                if off_tick >= next_tick:
                    off_tick = next_tick - 1
            events.append((off_tick, mido.Message('note_off', channel=9, note=note, velocity=0)))

    # Empty event at the end to let the final crash ring out
    events.append((int(244 * PPQ), mido.Message('note_off', channel=9, note=36, velocity=0)))

    # Stable sorting: Meta events first, then Note Offs, then Note Ons
    def sort_key(x):
        tick = x[0]
        if x[1].is_meta: priority = 0
        elif x[1].type == 'note_off': priority = 1
        else: priority = 2
        return (tick, priority)

    events.sort(key=sort_key)

    mid = mido.MidiFile(ticks_per_beat=PPQ)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    last_tick = 0
    for tick, msg in events:
        delta = tick - last_tick
        msg.time = max(0, delta)
        track.append(msg)
        last_tick = tick
        
    mid.save('solo.mid')

if __name__ == '__main__':
    generate_solo()
