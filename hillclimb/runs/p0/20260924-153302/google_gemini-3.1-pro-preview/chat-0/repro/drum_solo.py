import mido
import random

def generate_drum_solo():
    # Enforce determinism
    random.seed(42)
    
    # GM Percussion Note Map
    KICK = 36
    KICK2 = 35
    SNARE = 38
    RIM = 37
    HAT_C = 42
    HAT_O = 46
    HAT_P = 44
    RIDE = 51
    RIDE_BELL = 53
    CRASH1 = 49
    CRASH2 = 57
    TOM_1 = 50
    TOM_2 = 48
    TOM_3 = 45
    TOM_4 = 41
    COWBELL = 56
    
    TICKS_PER_BEAT = 480
    TICKS_PER_STEP = 20  # 24 steps per beat (allows 16ths, 8th triplets, 16th triplets)
    
    notes = []
    
    def add(m, step, note, vel):
        notes.append({'m': m, 'step': step, 'n': note, 'v': vel})
        
    def gen_intro_measure(m):
        # Sparse, laying down the foundation
        for b in range(4):
            add(m, b*24, HAT_C, random.randint(60, 70))
            if b != 3 or m % 2 == 0:
                add(m, b*24 + 12, HAT_C, random.randint(40, 50))
        add(m, 0, KICK, 80)
        add(m, 24, RIM, 90)
        add(m, 72, RIM, 90)
        
        if m == 1: add(m, 66, KICK, 75)
        if m == 3:
            add(m, 72 + 12, SNARE, 60)
            add(m, 72 + 18, SNARE, 65)
            add(m, 72 + 21, SNARE, 70)

    def measure_groove_a(m):
        # Funky main motif, highly syncopated
        for b in range(4):
            if not (m in [7, 11] and b == 3):
                add(m, b*24, HAT_C, 85)
                add(m, b*24 + 6, HAT_C, 45)
                add(m, b*24 + 12, HAT_C, 65)
                if m % 2 == 1 and b == 3:
                    add(m, b*24 + 18, HAT_O, 85)
                else:
                    add(m, b*24 + 18, HAT_C, 45)
    
        add(m, 24, SNARE, 110)
        if not (m in [7, 11]): add(m, 72, SNARE, 110)
    
        add(m, 0, KICK, 100)
        add(m, 18, KICK, 85)
        add(m, 36, KICK, 90)
        
        if m % 2 == 0:
            add(m, 66, KICK, 85)
        else:
            add(m, 48, KICK, 100)
            if not (m in [7, 11]): add(m, 78, KICK, 80)
    
        # Snare ghost notes
        add(m, 6, SNARE, 40)
        add(m, 42, SNARE, 45)
    
        if m == 7:
            add(m, 72, SNARE, 100)
            add(m, 72 + 6, SNARE, 60)
            add(m, 72 + 12, TOM_1, 90)
            add(m, 72 + 18, TOM_2, 95)
        elif m == 11:
            add(m, 72, SNARE, 105)
            add(m, 76, SNARE, 80)
            add(m, 80, TOM_1, 95)
            add(m, 84, TOM_1, 85)
            add(m, 88, TOM_2, 100)
            add(m, 92, TOM_4, 105)

    def measure_groove_a1(m):
        # Motif developed onto the ride cymbal
        if m == 12: add(m, 0, CRASH1, 110)
        
        for b in range(4):
            if not (m in [15, 19] and b >= 2):
                add(m, b*24, RIDE, 85)
                add(m, b*24 + 12, RIDE, 70)
            if b == 1 or b == 3:
                add(m, b*24, HAT_P, 80)
    
        if not (m in [15, 19]):
            add(m, 24, SNARE, 115)
            add(m, 72, SNARE, 115)
            add(m, 0, KICK, 100)
            add(m, 12, KICK, 80)
            add(m, 36, KICK, 90)
            add(m, 48, KICK, 95)
            add(m, 66, KICK, 85)
            
            # Intricate ghosting
            add(m, 18, SNARE, 45)
            add(m, 30, SNARE, 50)
            add(m, 54, SNARE, 45)
            add(m, 78, SNARE, 50)
            add(m, 84, SNARE, 55)
    
        if m == 15: # Quick descending fill
            add(m, 48, TOM_1, 100)
            add(m, 54, TOM_1, 80)
            add(m, 60, TOM_2, 95)
            add(m, 66, TOM_2, 85)
            add(m, 72, SNARE, 110)
            add(m, 78, KICK, 100)
            add(m, 84, TOM_4, 110)
            add(m, 90, KICK, 100)
    
        if m == 19: # Linear syncopated fill
            add(m, 48, SNARE, 110)
            add(m, 54, KICK, 90)
            add(m, 60, TOM_1, 105)
            add(m, 66, KICK, 90)
            add(m, 72, TOM_2, 110)
            add(m, 78, KICK, 90)
            add(m, 84, TOM_4, 115)
            add(m, 90, CRASH2, 110)

    def measure_transition(m):
        # Afro-Cuban inspired tom groove build up
        if m == 20:
            add(m, 0, CRASH1, 110)
            add(m, 0, KICK, 100)
        
        for step in range(0, 96, 6):
            if m == 23 and step >= 48: continue
            
            if step % 24 == 0:
                add(m, step, TOM_4, 110)
                if step != 0 or m != 20: add(m, step, KICK, 100)
            elif step % 12 == 0:
                add(m, step, TOM_3, 90)
            else:
                add(m, step, TOM_3, 70)
                
        if m != 23:
            add(m, 12, COWBELL, 100)
            add(m, 30, COWBELL, 100)
            add(m, 48, COWBELL, 105)
            add(m, 78, COWBELL, 100)
    
        if m == 23:
            for step in range(48, 96, 6):
                add(m, step, SNARE, 70 + (step-48))
                add(m, step, KICK, 80 + (step-48)//2)

    def measure_groove_b(m):
        # Half-time heavy feel (snare on beat 3)
        if m == 24:
            add(m, 0, CRASH1, 115)
            add(m, 0, KICK, 110)
            
        for b in range(4):
            if m == 31 and b >= 2: continue
            if m % 2 == 0:
                if b == 1:
                    for s in range(0, 24, 3): add(m, b*24 + s, HAT_C, 80 + s)
                else:
                    for s in range(0, 24, 6): add(m, b*24 + s, HAT_C, 90 if s==0 else 60)
            else:
                for s in range(0, 24, 6): add(m, b*24 + s, HAT_C, 90 if s==0 else 60)
                if b == 3: add(m, b*24 + 18, HAT_O, 95)
                    
        if not (m == 31):
            add(m, 48, SNARE, 120)
            add(m, 48, KICK, 100)
            
        add(m, 0, KICK, 110)
        add(m, 30, KICK, 90)
        if m != 31:
            add(m, 66, KICK, 100)
            add(m, 84, KICK, 95)
        
        if m == 31:
            for s in range(48, 72, 4): add(m, s, SNARE, 100 + (s-48))
            for s in range(72, 96, 4): add(m, s, TOM_2, 110)
            add(m, 48, CRASH2, 110)

    def measure_groove_b1(m):
        # Double-time fusion ride pattern
        if m == 32: add(m, 0, CRASH2, 115)
            
        for s in range(0, 96, 12):
            if m == 39 and s >= 72: continue
            add(m, s, RIDE, 95)
            
        if m != 39:
            for s in range(12, 96, 24): add(m, s, SNARE, 115)
            for s in range(0, 96, 24):
                add(m, s, KICK, 110)
                add(m, s + 18, KICK, 90)
        else:
            add(m, 0, SNARE, 115)
            add(m, 0, CRASH1, 115)
            add(m, 0, KICK, 110)
            for s in range(72, 84, 3): add(m, s, SNARE, 110 + (s-72))
            for s in range(84, 96, 3): add(m, s, TOM_1, 115 + (s-84))

    def measure_break(m):
        # Drum break: heavy syncopation vs silence, then explosive 32nd/triplet runs
        if m == 40 or m == 44:
            for s in [0, 18, 36]:
                add(m, s, CRASH1 if s != 18 else CRASH2, 120)
                add(m, s, SNARE, 120 if s != 18 else 115)
                add(m, s, KICK, 120 if s != 18 else 115)
        elif m == 41 or m == 45:
            for s in range(0, 96, 4):
                idx = s // 4
                vel = 90 + random.randint(0, 20)
                if idx % 6 == 0: add(m, s, TOM_1, 120)
                elif idx % 6 == 1: add(m, s, TOM_2, 110)
                elif idx % 6 in [2, 3]: add(m, s, KICK, 115)
                else: add(m, s, SNARE, vel)
        elif m == 42 or m == 46:
            for s in [6, 24, 54, 72]:
                add(m, s, CRASH2, 115)
                add(m, s, TOM_4, 115)
                add(m, s, KICK, 115)
        elif m == 43:
            for b in range(4):
                base = b * 24
                add(m, base, TOM_3, 115)
                add(m, base + 3, SNARE, 100)
                add(m, base + 6, SNARE, 110)
                add(m, base + 12, KICK, 110)
                add(m, base + 18, KICK, 110)
        elif m == 47:
            for s in range(0, 96, 3):
                vel = 70 + (s * 50 // 96)
                if s < 24: add(m, s, SNARE, vel)
                elif s < 48: add(m, s, TOM_1, vel)
                elif s < 72: add(m, s, TOM_2, vel)
                else: add(m, s, TOM_4, vel)
            for s in range(0, 96, 12):
                add(m, s, KICK, 100 + (s * 20 // 96))

    def measure_climax(m):
        # Full intensity, double bass, crashes on quarters
        for b in range(4):
            if m == 55: break
            if m % 2 == 0: add(m, b*24, CRASH1, 120)
            else: add(m, b*24, CRASH2, 120)
                
        if m != 55:
            add(m, 24, SNARE, 127)
            add(m, 72, SNARE, 127)
            for s in range(0, 96, 6):
                kick_note = KICK if (s // 6) % 2 == 0 else KICK2
                add(m, s, kick_note, 115)
                
        if m == 55: # Final massive fill
            for s in range(0, 24, 4):
                add(m, s, TOM_1, 120)
                add(m, s, KICK, 110)
            for s in range(24, 48, 4):
                add(m, s, TOM_2, 120)
                add(m, s, KICK, 110)
            for s in range(48, 72, 4):
                add(m, s, TOM_3, 120)
                add(m, s, KICK, 110)
            for s in range(72, 96, 4):
                add(m, s, TOM_4, 120)
                add(m, s, KICK, 110)

    def measure_outro(m):
        # Dissolve back into the initial sparse motif and fade out
        if m == 56: add(m, 0, CRASH1, 110)
        fade = max(40, 100 - (m - 56) * 15)
        for b in range(4):
            if m < 59:
                add(m, b*24, HAT_C, fade)
                if m < 58: add(m, b*24 + 12, HAT_C, max(30, fade - 20))
        if m < 59: add(m, 0, KICK, fade + 10)
        if m < 58:
            add(m, 24, RIM, fade + 10)
            add(m, 72, RIM, fade + 10)
            add(m, 48, KICK, fade)
        elif m == 58:
            add(m, 24, RIM, fade)
        if m == 59:
            add(m, 0, CRASH1, 100)
            add(m, 0, KICK, 100)

    # 1. Assemble the sequence timeline (60 measures = 2 minutes @ 120 BPM)
    for m in range(60):
        if m < 4: gen_intro_measure(m)
        elif m < 12: measure_groove_a(m)
        elif m < 20: measure_groove_a1(m)
        elif m < 24: measure_transition(m)
        elif m < 32: measure_groove_b(m)
        elif m < 40: measure_groove_b1(m)
        elif m < 48: measure_break(m)
        elif m < 56: measure_climax(m)
        else: measure_outro(m)

    # 2. Enforce physical playability: Max 2 hands, 2 feet active per exact step division.
    HAND_NOTES = set(range(35, 82)) - {35, 36, 44}
    by_pos = {}
    for note in notes:
        pos = (note['m'], note['step'])
        if pos not in by_pos:
            by_pos[pos] = []
        by_pos[pos].append(note)
        
    playable_notes = []
    for pos, evts in by_pos.items():
        # Keep highest velocity events first (ensures accents aren't dropped)
        evts.sort(key=lambda x: x['v'], reverse=True)
        hands, feet = 0, 0
        for evt in evts:
            if evt['n'] in HAND_NOTES:
                if hands < 2:
                    hands += 1
                    playable_notes.append(evt)
            else:
                if feet < 2:
                    feet += 1
                    playable_notes.append(evt)

    # 3. Apply micro-timing (swing, pushing/pulling) and calculate absolute ticks
    for note in playable_notes:
        base_tick = note['m'] * 4 * TICKS_PER_BEAT + note['step'] * TICKS_PER_STEP
        n = note['n']
        step_in_beat = note['step'] % 24
        offset = 0
        
        # Snare lays back slightly on backbeats for a deep pocket
        if n in [SNARE, RIM] and note['step'] % 96 in [24, 72]:
            offset = 12
        # Kick drives dead-on or pushes slightly on downbeats
        if n in [KICK, KICK2] and note['step'] % 96 in [0, 48]:
            offset = 0
            
        # Subtle 16th note swing
        if step_in_beat == 6: offset += 4
        elif step_in_beat == 12: offset += 8
        elif step_in_beat == 18: offset += 12
            
        # Cymbals naturally lay back a tiny bit more
        if n in [HAT_C, HAT_O, HAT_P, RIDE, CRASH1, CRASH2]: offset += 5
            
        # Add a tiny pinch of human jitter
        offset += random.randint(-2, 2)
        if base_tick + offset < 0: offset = -base_tick
            
        # Humanize velocity
        v = max(1, min(127, note['v'] + random.randint(-4, 4)))
        
        note['tick'] = int(base_tick + offset)
        note['v'] = int(v)

    # 4. Generate MIDI events (matching Note On with short Note Off)
    events = []
    for note in playable_notes:
        tick = note['tick']
        events.append({'tick': tick, 'type': 'note_on', 'n': note['n'], 'v': note['v']})
        events.append({'tick': tick + 100, 'type': 'note_off', 'n': note['n'], 'v': 0})

    # Sort sequentially (ensure note_off precedes note_on at identical ticks to avoid choking notes)
    events.sort(key=lambda x: (x['tick'], x['type'] == 'note_on'))

    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # 120 BPM establishes exactly 2 minutes (60 bars * 4 beats)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120)))

    last_tick = 0
    for evt in events:
        delta = evt['tick'] - last_tick
        if delta < 0: delta = 0
        
        msg_type = evt['type']
        # Channel 9 (0-indexed) is standard MIDI Channel 10 for percussion
        track.append(mido.Message(msg_type, channel=9, note=evt['n'], velocity=evt['v'], time=delta))
        last_tick = evt['tick']
        
    mid.save('solo.mid')

if __name__ == '__main__':
    generate_drum_solo()
