import mido
import random
import math

def generate_drum_solo():
    # Setup
    random.seed(90210)  # Fixed seed for reproducibility
    ticks_per_beat = 480
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # 120 BPM default, but we'll simulate tempo drift via micro-timing
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
    
    # Drum map (GM)
    KICK = 36
    SNARE = 38
    CH = 42
    OH = 46
    PH = 44
    RIDE = 51
    BELL = 53
    CRASH1 = 49
    CRASH2 = 57
    T1 = 50 # High Tom
    T2 = 48 # Hi-Mid Tom
    T3 = 45 # Low Tom
    T4 = 41 # Floor Tom
    
    events = []
    
    def hit(pitch, vel, tick, dur=60):
        # Playability check: very minor micro-randomization for limbs 
        # offset depends slightly on pitch to simulate different limb delays
        limb_offset = (pitch % 5) - 2 
        
        # Humanize timing (gauss)
        t = tick + int(random.gauss(0, 8)) + limb_offset
        t = max(0, t)
        
        # Humanize velocity
        v = int(max(1, min(127, vel + random.gauss(0, 6))))
        
        events.append((t, 'on', pitch, v))
        events.append((t + dur, 'off', pitch, 0))

    # Master timeline tracking
    total_bars = 64
    bar_ticks = ticks_per_beat * 4
    
    # Drummer state / motifs
    # We will build the solo in sections
    
    for bar in range(total_bars):
        # Global pacing: surge and settle
        # Negative push means rushing ahead, positive means laying back
        push_pull = math.sin(bar / total_bars * math.pi) * -20 
        
        bar_start = bar * bar_ticks
        
        # SECTION 1: Establish the Groove (Bars 0 - 15)
        if 0 <= bar < 16:
            # Building up from hi-hat and kick
            density = bar / 16.0 
            
            for beat in range(4):
                for semi in range(4):
                    tick = bar_start + beat * ticks_per_beat + semi * 120
                    tick += int(push_pull)
                    
                    # Right hand on Ride or Hat
                    if bar < 4:
                        if semi % 2 == 0:
                            hit(CH, 70 if beat in (0,2) else 50, tick)
                    else:
                        # Move to ride, syncopated bell
                        if semi == 0 or semi == 2:
                            hit(RIDE, 75, tick)
                        elif semi == 3 and random.random() < 0.3:
                            hit(BELL, 90, tick)
                            
                    # Left hand snare
                    if beat in (1, 3) and semi == 0:
                        hit(SNARE, 110, tick) # Backbeat
                    elif semi != 0 and random.random() < (0.2 + density*0.3):
                        # Ghost notes
                        hit(SNARE, random.randint(25, 45), tick)
                        
                    # Kick drum pattern (Motif A)
                    if beat == 0 and semi == 0:
                        hit(KICK, 100, tick)
                    elif beat == 2 and semi == (1 if bar % 2 == 0 else 0):
                        hit(KICK, 90, tick)
                    elif semi == 3 and random.random() < 0.2:
                        hit(KICK, 75, tick)

            # End of 4-bar phrase fill
            if bar % 4 == 3:
                for i in range(4):
                    tick = bar_start + 3 * ticks_per_beat + i * 120
                    if i < 2:
                        hit(SNARE, 100, tick)
                    else:
                        hit(T1 if bar < 8 else T2, 90, tick)
                        hit(KICK, 90, tick)

        # SECTION 2: Motif Development & Linear Fills (Bars 16 - 31)
        elif 16 <= bar < 32:
            # Broken up, funkier, moving around the kit
            for beat in range(4):
                # 8th note triplets feel mapped to 16ths in places
                if bar % 4 == 3 and beat >= 2:
                    # Linear fill R L K R L K
                    for i, triplet_tick in enumerate(range(0, ticks_per_beat, 160)):
                        t = bar_start + beat * ticks_per_beat + triplet_tick + int(push_pull)
                        if i % 3 == 0: hit(SNARE, 100, t)
                        elif i % 3 == 1: hit(T2, 90, t)
                        else: hit(KICK, 100, t)
                else:
                    for semi in range(4):
                        tick = bar_start + beat * ticks_per_beat + semi * 120 + int(push_pull)
                        
                        # Displaced backbeat
                        if beat == 1 and semi == 1:
                            hit(SNARE, 115, tick)
                        elif beat == 3 and semi == 0:
                            hit(SNARE, 110, tick)
                        
                        # Ghosting
                        if random.random() < 0.3 and not (beat == 1 and semi == 1):
                            hit(SNARE, 30, tick)
                            
                        # Busy kick
                        if beat == 0 and semi == 0: hit(KICK, 105, tick)
                        if beat == 2 and semi == 2: hit(KICK, 95, tick)
                        if beat == 3 and semi == 3: hit(KICK, 85, tick)
                        
                        # Hi-hat pedal on 8ths
                        if semi % 2 == 0:
                            hit(PH, 60, tick)
                        
                        # Random tom punctuations
                        if random.random() < 0.1:
                            hit(random.choice([T1, T3]), 80, tick)

        # SECTION 3: The Build-Up (Bars 32 - 47)
        elif 32 <= bar < 48:
            progress = (bar - 32) / 16.0
            base_vel = int(30 + progress * 80)
            
            for beat in range(4):
                for semi in range(4):
                    tick = bar_start + beat * ticks_per_beat + semi * 120 + int(push_pull)
                    
                    # Snare crescendo (alternating hands)
                    vel = base_vel
                    if semi == 0: vel += 15 # Accent on downbeats
                    hit(SNARE, min(127, vel), tick)
                    
                    # Adding Floor tom with right hand later in the build
                    if progress > 0.5 and semi % 2 == 0:
                        hit(T4, min(127, base_vel + 10), tick)
                        
                    # Double kick sweeping in
                    if progress > 0.25:
                        if semi % 2 == 0:
                            hit(KICK, min(127, base_vel + 20), tick)
                        elif progress > 0.75: # 16th note kicks at the end
                            hit(KICK, min(127, base_vel), tick)
                            
            # Crash to reset phrases during build
            if bar % 4 == 0:
                hit(CRASH1, min(127, base_vel + 40), bar_start)

        # SECTION 4: Climax & Showcase Chops (Bars 48 - 59)
        elif 48 <= bar < 60:
            # Full energy, cymbals, massive fills
            if bar % 2 == 0:
                # Heavy groove
                for beat in range(4):
                    for semi in range(4):
                        tick = bar_start + beat * ticks_per_beat + semi * 120 + int(push_pull)
                        # Washy ride or crash
                        if semi == 0 or semi == 2:
                            hit(CRASH2 if beat % 2 == 0 else OH, 110, tick)
                        # Snare
                        if beat in (1, 3) and semi == 0:
                            hit(SNARE, 127, tick)
                        elif semi != 0 and random.random() < 0.4:
                            hit(SNARE, 50, tick)
                        # Kick
                        if beat == 0 and semi == 0: hit(KICK, 120, tick)
                        if beat == 2 and semi == 0: hit(KICK, 120, tick)
                        if beat == 2 and semi == 3: hit(KICK, 100, tick)
            else:
                # 32nd note runs around the kit (Blushdas, sweeps)
                for beat in range(4):
                    if beat < 3:
                        for i in range(8): # 32nd notes
                            tick = bar_start + beat * ticks_per_beat + i * 60 + int(push_pull)
                            drum = SNARE
                            vel = 110
                            if i in (0, 4): drum = KICK; vel = 127
                            elif i in (1, 5): drum = T1
                            elif i in (2, 6): drum = T2
                            elif i in (3, 7): drum = T4
                            
                            # Ghost note dynamics
                            if i not in (0, 4): vel = random.randint(70, 95)
                            
                            hit(drum, vel, tick)
                    else:
                        # Big flam and gap
                        tick = bar_start + beat * ticks_per_beat + int(push_pull)
                        hit(SNARE, 127, tick)
                        hit(SNARE, 100, tick + 15) # Flam grace note
                        hit(KICK, 127, tick)
                        
        # SECTION 5: Grand Finale (Bars 60 - 63)
        elif 60 <= bar < 64:
            if bar == 60:
                # Massive triplet hits
                for beat in range(4):
                    for i in range(3):
                        tick = bar_start + beat * ticks_per_beat + i * 160
                        hit(SNARE, 120, tick)
                        hit(KICK, 120, tick)
                        hit(CRASH1 if i == 0 else CRASH2, 110, tick)
            elif bar == 61:
                # Fast snare roll slowing down
                for i in range(16):
                    tick = bar_start + int(i * 120 * (1 + i * 0.05))
                    hit(SNARE, max(40, 120 - i*4), tick)
            elif bar == 62:
                # The Final Hit on beat 1
                tick = bar_start
                hit(KICK, 127, tick)
                hit(SNARE, 127, tick)
                hit(CRASH1, 127, tick)
                hit(CRASH2, 127, tick)
                # Let ring...

    # Sort events by absolute time
    events.sort(key=lambda x: x[0])
    
    # Ensure playability (max 4 concurrent hits per limb limit abstraction)
    # We will just drop hits if more than 4 happen at the exact same millisecond window
    filtered_events = []
    window = 10
    current_window = []
    
    for ev in events:
        t, ev_type, pitch, vel = ev
        if ev_type == 'off':
            filtered_events.append(ev)
            continue
            
        # Clean old from window
        current_window = [w for w in current_window if abs(w - t) <= window]
        
        if len(current_window) < 4:
            current_window.append(t)
            filtered_events.append(ev)
    
    # Re-sort after filtering
    filtered_events.sort(key=lambda x: x[0])
    
    # Convert absolute times to deltas and write to track
    last_time = 0
    for ev in filtered_events:
        t, ev_type, pitch, vel = ev
        delta = max(0, t - last_time)
        last_time = t
        
        msg = mido.Message(ev_type, channel=9, note=pitch, velocity=vel, time=delta)
        track.append(msg)
        
    mid.save('solo.mid')

if __name__ == '__main__':
    generate_drum_solo()
