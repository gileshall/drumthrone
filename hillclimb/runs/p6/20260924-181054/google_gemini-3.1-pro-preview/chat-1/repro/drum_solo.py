import mido
import random
import math

def generate_solo():
    # Set a fixed seed for deterministic output
    random.seed(1337)
    
    TICKS_PER_BEAT = 480
    BPM = 112
    events = []
    
    # Standard General MIDI Percussion Map (Channel 10)
    KICK = 36
    SNARE = 38
    HAT_C = 42
    HAT_O = 46
    HAT_P = 44
    RIDE = 51
    RIDE_BELL = 53
    CRASH1 = 49
    CRASH2 = 57
    CHINA = 52
    TOM1 = 50 
    TOM2 = 48 
    TOM3 = 47 
    TOM4 = 45 
    TOM5 = 43 
    TOM6 = 41
    COWBELL = 56
    VIBRASLAP = 58
    
    # Event scheduler with humanization (microtiming and velocity variance)
    def hit(b, p, v):
        beat_in_measure = b % 4
        # Add a subtle push/pull groove
        timing_offset = math.sin(b * math.pi / 8) * 0.015
        
        # Drummers naturally lay back slightly on the backbeat
        if p in [SNARE, 40] and (abs(beat_in_measure - 1.0) < 0.1 or abs(beat_in_measure - 3.0) < 0.1):
            timing_offset += 0.015
            
        actual_b = max(0, b + timing_offset + random.gauss(0, 0.005))
        actual_v = int(max(1, min(127, v + random.gauss(0, 4))))
        
        events.append({'b': actual_b, 'p': p, 'v': actual_v})

    # ==========================================
    # Section 1: Intro Groove (Beats 0 - 32)
    # Sparse, hi-hat driven, establishing a pocket
    # ==========================================
    for bar in range(8):
        b0 = bar * 4
        
        # Transition fill to the next section
        if bar == 7:
            for i in range(16):
                pos = i * 0.25
                if pos < 2.0:
                    if i % 2 == 0: hit(b0 + pos, HAT_C, 80)
                    if pos == 0.0: hit(b0, KICK, 90)
                    if pos == 1.0: hit(b0 + 1.0, SNARE, 100)
                else:
                    if i % 2 == 0:
                        hit(b0 + pos, SNARE, 90 + i)
                        hit(b0 + pos, KICK, 90)
                    else:
                        hit(b0 + pos, TOM1 if pos < 3.0 else TOM3, 100)
            continue
            
        # Hi-hat pattern
        for i in range(8):
            v = 80 if i % 2 == 0 else 50
            if bar % 2 == 1 and i == 7:
                hit(b0 + i * 0.5, HAT_O, 85)
                hit(b0 + 4.0, HAT_P, 60) # Foot choke on next downbeat
            else:
                hit(b0 + i * 0.5, HAT_C, v)
        
        # Kick pattern
        hit(b0, KICK, 90)
        hit(b0 + 2.5, KICK, 80)
        if random.random() < 0.5:
            hit(b0 + 3.5, KICK, 75)
            
        # Snare backbeats
        hit(b0 + 1.0, SNARE, 100)
        hit(b0 + 3.0, SNARE, 105)
        
        # Ghost notes filling the space
        for i in range(16):
            pos = i * 0.25
            if pos not in [1.0, 3.0]:
                if random.random() < 0.2 + (0.1 if bar > 3 else 0):
                    hit(b0 + pos, SNARE, random.randint(30, 45))
                    
        if bar == 0 or bar == 4:
            hit(b0, CRASH1, 110)

    # ==========================================
    # Section 2: Syncopated Motif (Beats 32 - 64)
    # Interplay across barlines (3-3-3-3-2-2)
    # ==========================================
    motif_b0 = 32
    for bar in range(8):
        b0 = motif_b0 + bar * 4
        
        # Foot hat keeping the pulse
        for i in range(4):
            hit(b0 + i, HAT_P, 70)
            
        if bar == 7:
            groupings = [4, 4, 4, 4]
        else:
            groupings = [3, 3, 3, 3, 2, 2] if bar % 2 == 0 else [3, 3, 2, 3, 3, 2]
            
        vol_mod = 0.8 + (bar / 8) * 0.4
        pos = 0.0
        
        for g in groupings:
            if g == 3:
                hit(b0 + pos, SNARE, int(90 * vol_mod) if pos not in [1.0, 3.0] else int(110 * vol_mod))
                hit(b0 + pos + 0.25, SNARE, int(40 * vol_mod))
                hit(b0 + pos + 0.5, KICK, int(85 * vol_mod))
            elif g == 2:
                hit(b0 + pos, SNARE, int(85 * vol_mod))
                hit(b0 + pos + 0.25, SNARE, int(45 * vol_mod))
            elif g == 4:
                # Flowing tom fill
                hit(b0 + pos, TOM1 if pos < 2 else TOM3, 100)
                hit(b0 + pos + 0.25, TOM1 if pos < 2 else TOM3, 70)
                hit(b0 + pos + 0.5, TOM2 if pos < 2 else TOM4, 95)
                hit(b0 + pos + 0.75, TOM2 if pos < 2 else TOM4, 65)
                
            if g != 4:
                hit(b0 + pos, COWBELL, int(85 * vol_mod))
                
            pos += g * 0.25

    # ==========================================
    # Section 3: Tom Exploration (Beats 64 - 96)
    # Heavy, tribal polyrhythmic feel
    # ==========================================
    tom_b0 = 64
    for bar in range(8):
        b0 = tom_b0 + bar * 4
        is_fill = (bar % 4 == 3)
        
        for i in range(4):
            hit(b0 + i, RIDE_BELL if is_fill else RIDE, 95 if is_fill else 85)
            
        for i in range(16):
            pos = i * 0.25
            
            if is_fill and pos >= 2.0:
                tom_idx = int((pos - 2.0) * 4)
                toms = [TOM1, TOM1, TOM2, TOM2, TOM3, TOM3, TOM4, TOM4]
                hit(b0 + pos, toms[tom_idx], 100 + tom_idx * 3)
                if tom_idx % 2 == 1:
                    hit(b0 + pos, KICK, 90)
                continue
                
            if pos == 1.0 or pos == 3.0:
                hit(b0 + pos, SNARE, 110)
                continue
                
            cycle = i % 3
            if cycle == 0:
                hit(b0 + pos, TOM5 if bar < 4 else TOM6, 95)
            elif cycle == 1:
                hit(b0 + pos, KICK, 95)
            elif cycle == 2:
                hit(b0 + pos, TOM4 if bar < 4 else TOM5, 80)

    # ==========================================
    # Section 4: Build Up (Beats 96 - 128)
    # Accelerating linear chops (16ths to sextuplets)
    # ==========================================
    build_b0 = 96
    for bar in range(8):
        b0 = build_b0 + bar * 4
        
        if bar == 0:
            hit(b0, CRASH1, 115)
            hit(b0, KICK, 100)
            
        if bar < 4:
            # 16th note linear patterns
            for i in range(16):
                pos = i * 0.25
                cycle = i % 4
                v = 80 + bar * 5 + cycle * 2
                
                if cycle == 0: hit(b0 + pos, SNARE, v + 10)
                elif cycle == 1: hit(b0 + pos, TOM1 if bar % 2 == 0 else TOM2, v)
                elif cycle == 2: hit(b0 + pos, TOM3 if bar % 2 == 0 else TOM4, v)
                elif cycle == 3: hit(b0 + pos, KICK, v + 15)
        else:
            # Sextuplet linear patterns
            for i in range(24):
                pos = i / 6.0
                cycle = i % 6
                v = int(90 + (bar - 4) * 8 + (i / 24) * 10)
                
                if bar == 4:
                    if cycle == 0: hit(b0 + pos, SNARE, v+10)
                    elif cycle == 1: hit(b0 + pos, TOM1, v)
                    elif cycle == 2: hit(b0 + pos, TOM2, v)
                    elif cycle == 3: hit(b0 + pos, TOM3, v)
                    elif cycle in [4,5]: hit(b0 + pos, KICK, v+10)
                elif bar == 5:
                    if cycle in [0, 3]: hit(b0 + pos, SNARE, v+10)
                    elif cycle == 1: hit(b0 + pos, TOM4, v)
                    elif cycle == 4: hit(b0 + pos, TOM5, v)
                    elif cycle in [2, 5]: hit(b0 + pos, KICK, v+10)
                elif bar == 6:
                    hit(b0 + pos, SNARE, v + (10 if i%2==0 else 0))
                    if i % 6 == 0: hit(b0 + pos, KICK, 100)
                elif bar == 7:
                    # R L K R L K cascading down toms
                    insts = [TOM1, TOM1, KICK, TOM2, TOM2, KICK, TOM3, TOM3, KICK, TOM4, TOM4, KICK, 
                             TOM5, TOM5, KICK, SNARE, SNARE, KICK, SNARE, SNARE, KICK, CRASH1, KICK, CRASH2]
                    if insts[i] == KICK:
                        hit(b0 + pos, KICK, 110)
                    else:
                        hit(b0 + pos, insts[i], 115)

    # ==========================================
    # Section 5: Heavy Groove (Beats 128 - 160)
    # Wide, half-time feel with heavy backbeat
    # ==========================================
    groove_b0 = 128
    for bar in range(8):
        b0 = groove_b0 + bar * 4
        cymbal = CRASH1 if bar >= 4 else RIDE
        
        for i in range(8):
            v = 110 if i % 2 == 0 else 90
            is_fill_beat = ((bar == 3 or bar == 7) and (i * 0.5) >= 3.0)
            if not is_fill_beat:
                hit(b0 + i * 0.5, cymbal, v)
                if bar >= 4 and i % 2 == 0 and (i * 0.5) != 2.0:
                    hit(b0 + i * 0.5, CHINA, 90)
                
        hit(b0 + 2.0, SNARE, 120)
        
        for i in range(16):
            pos = i * 0.25
            if (bar == 3 or bar == 7) and pos >= 3.0:
                continue
            if pos != 2.0:
                if random.random() < 0.3:
                    hit(b0 + pos, SNARE, random.randint(30, 50))
                    
        hit(b0, KICK, 110)
        hit(b0 + 0.75, KICK, 100)
        if bar % 2 == 0:
            hit(b0 + 1.5, KICK, 95)
            if bar != 3 and bar != 7:
                hit(b0 + 3.25, KICK, 100)
        else:
            hit(b0 + 1.25, KICK, 95)
            if bar != 3 and bar != 7:
                hit(b0 + 3.5, KICK, 100)
                
        if bar % 4 == 3:
            hit(b0 + 3.0, VIBRASLAP, 110)
            
        if bar == 3:
            hit(b0 + 3.0, TOM1, 110); hit(b0 + 3.25, TOM2, 110)
            hit(b0 + 3.5, TOM3, 110); hit(b0 + 3.75, TOM4, 110)
            hit(b0 + 3.0, KICK, 100); hit(b0 + 3.5, KICK, 100)
        if bar == 7:
            for i in range(6):
                pos = 3.0 + i / 6.0
                hit(b0 + pos, SNARE if i < 3 else TOM4, 110 + i * 2)
                if i % 2 == 0:
                    hit(b0 + pos, KICK, 110)

    # ==========================================
    # Section 6: Climax (Beats 160 - 208)
    # Shredding fast runs, chops, and swelling rolls
    # ==========================================
    climax_b0 = 160
    for bar in range(12):
        b0 = climax_b0 + bar * 4
        
        if bar % 2 == 0:
            hit(b0, CRASH1, 115)
        else:
            hit(b0, CRASH2, 115)
            
        for i in range(4):
            hit(b0 + i, HAT_P, 90)
            
        if bar < 4:
            # 32nd note runs (R L K K repeating)
            for i in range(32):
                pos = i * 0.125
                cycle = i % 4
                if cycle in [0, 1]:
                    hit(b0 + pos, SNARE, 100 + cycle * 10)
                else:
                    hit(b0 + pos, KICK, 110)
        elif bar < 8:
            # 32nd notes moving around the toms
            for i in range(32):
                pos = i * 0.125
                cycle = i % 4
                group = (i // 4) % 4
                toms = [TOM1, TOM2, TOM3, TOM4]
                if cycle in [0, 1]:
                    hit(b0 + pos, toms[group], 115 if cycle == 0 else 100)
                else:
                    hit(b0 + pos, KICK, 115)
        else:
            if bar < 10:
                # Sextuplet sweeps
                for i in range(24):
                    pos = i / 6.0
                    v = 110 if i % 2 == 0 else 85
                    inst = SNARE
                    if i % 6 == 0: inst = TOM1
                    if i % 6 == 2: inst = TOM2
                    if i % 6 == 4: inst = TOM3
                    hit(b0 + pos, inst, v)
                    if i % 3 == 0:
                        hit(b0 + pos, KICK, 100)
            else:
                # Massive 32nd note single stroke roll swelling up
                for i in range(32):
                    pos = i * 0.125
                    overall_progress = ((bar - 10) * 32 + i) / 64
                    v = int(90 + overall_progress * 37)
                    if i % 8 == 0: v = min(127, v + 10)
                    
                    if i % 8 == 0: hit(b0 + pos, KICK, 115)
                    
                    inst = SNARE
                    if overall_progress > 0.5:
                        tom_idx = int((overall_progress - 0.5) * 2 * 5)
                        toms = [TOM1, TOM2, TOM3, TOM4, TOM5]
                        inst = toms[min(4, tom_idx)]
                        
                    hit(b0 + pos, inst, v)

    # ==========================================
    # Section 7: Big Finish (Beats 208 - 224)
    # Explosive syncopations and the final hit
    # ==========================================
    finish_b0 = 208
    for bar in range(4):
        b0 = finish_b0 + bar * 4
        
        if bar == 0 or bar == 1:
            accents = [0.0, 1.5, 2.5, 3.5]
            for a in accents:
                hit(b0 + a, CRASH1 if bar==0 else CRASH2, 120)
                hit(b0 + a, KICK, 120)
                hit(b0 + a, CHINA, 110)
            
            # Machine gun snare rolls between the hits
            for i in range(32):
                pos = i * 0.125
                if not any(abs(pos - a) < 0.1 for a in accents):
                    hit(b0 + pos, SNARE, 100 + random.randint(-10, 10))
                    
        elif bar == 2:
            # Huge final tom run
            for i in range(24):
                pos = i / 6.0
                toms = [TOM1, TOM1, TOM2, TOM2, TOM3, TOM3, TOM4, TOM4, TOM5, TOM5, TOM6, TOM6]
                tom_idx = i // 2
                hit(b0 + pos, toms[tom_idx % 12], 110 + i)
                if i % 2 == 0:
                    hit(b0 + pos, KICK, 110 + i)
                    
        elif bar == 3:
            # Landing the final hits solidly
            hit(b0, CRASH1, 127) 
            hit(b0, CRASH2, 127) 
            hit(b0, KICK, 127)   
            hit(b0, HAT_P, 127)  
            
            hit(b0 + 2.0, CRASH1, 127)
            hit(b0 + 2.0, SNARE, 127)
            hit(b0 + 2.0, KICK, 127)

    # ==========================================
    # Export to MIDI
    # ==========================================
    midi_events = []
    for e in events:
        abs_tick = int(round(e['b'] * TICKS_PER_BEAT))
        dur_ticks = int(0.1 * TICKS_PER_BEAT)
        midi_events.append({'tick': abs_tick, 'type': 'note_on', 'p': e['p'], 'v': e['v']})
        midi_events.append({'tick': abs_tick + dur_ticks, 'type': 'note_off', 'p': e['p'], 'v': 0})

    # Sort strictly by time, resolving ties by making note-offs happen before note-ons
    midi_events.sort(key=lambda x: (x['tick'], 0 if x['type'] == 'note_off' else 1))

    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
    track.append(mido.Message('program_change', program=0, channel=9)) # Channel 10 Standard GM Kit
    
    last_tick = 0
    for me in midi_events:
        delta = me['tick'] - last_tick
        if delta < 0: delta = 0
        
        if me['type'] == 'note_on':
            track.append(mido.Message('note_on', note=me['p'], velocity=me['v'], time=delta, channel=9))
        else:
            track.append(mido.Message('note_off', note=me['p'], velocity=0, time=delta, channel=9))
            
        last_tick += delta
        
    mid.save('solo.mid')

if __name__ == '__main__':
    generate_solo()
