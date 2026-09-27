import mido
import random

def generate_solo():
    # Fix the random seed so the script is completely deterministic and outputs an identical file every run.
    random.seed(42)

    notes = []

    # This function adds an event to our timeline, applying subtle micro-timing and velocity variations
    # to humanize the performance, making it groove naturally around the strict grid.
    def add_note(beat, note, vel):
        actual_beat = beat + random.uniform(-0.015, 0.015)
        actual_beat = max(0.0, actual_beat)
        vel += random.randint(-5, 5)
        vel = max(1, min(127, int(vel)))
        notes.append((actual_beat, int(note), vel))

    def paradiddle(start_beat, duration, note_r, note_l, vel_accent, vel_ghost):
        step = duration / 8
        stickings = ['R', 'L', 'R', 'R', 'L', 'R', 'L', 'L']
        for i, s in enumerate(stickings):
            t = start_beat + i * step
            vel = vel_accent if i in [0, 4] else vel_ghost
            note = note_r if s == 'R' else note_l
            add_note(t, note, vel)

    # Section 1: Intro Motif. Establishes a heavy tribal floor/snare rhythm with dense ghost notes.
    def motif_a(start_beat):
        # Measure 1
        add_note(start_beat + 0.0, 38, 110) # Snare accent
        add_note(start_beat + 0.0, 36, 100) # Bass Drum
        add_note(start_beat + 0.5, 38, 40)  # Snare ghost
        add_note(start_beat + 0.75, 38, 45) # Snare ghost
        add_note(start_beat + 1.0, 50, 90)  # High tom
        add_note(start_beat + 1.5, 38, 40)  
        add_note(start_beat + 2.0, 45, 95)  # Low tom
        add_note(start_beat + 2.5, 36, 90)  
        add_note(start_beat + 3.0, 38, 115) 
        add_note(start_beat + 3.25, 38, 40) 
        add_note(start_beat + 3.5, 41, 100) # Floor tom
        add_note(start_beat + 3.75, 36, 90) 
        
        # Measure 2
        add_note(start_beat + 4.0, 49, 110) # Crash
        add_note(start_beat + 4.0, 36, 100) 
        add_note(start_beat + 4.5, 38, 40)
        add_note(start_beat + 4.75, 38, 45)
        add_note(start_beat + 5.0, 48, 90)  # Hi-Mid tom
        add_note(start_beat + 5.25, 47, 90) # Low-Mid tom
        add_note(start_beat + 5.5, 36, 90)  
        add_note(start_beat + 5.75, 36, 90) 
        add_note(start_beat + 6.0, 38, 115) 
        add_note(start_beat + 6.5, 41, 100) 
        add_note(start_beat + 6.75, 41, 90) 
        add_note(start_beat + 7.0, 36, 100)
        add_note(start_beat + 7.25, 38, 40)
        add_note(start_beat + 7.5, 38, 50)
        add_note(start_beat + 7.75, 38, 60)

    # Paradiddle sweeps and a sextuplet build up to pivot to the next section.
    def fill_1(start_beat):
        paradiddle(start_beat, 2, 38, 38, 100, 40)
        paradiddle(start_beat+2, 2, 50, 38, 100, 40)
        paradiddle(start_beat+4, 2, 45, 38, 100, 40)
        for i in range(12):
            t = start_beat + 6 + i * (1/6)
            if i < 4: note = 38
            elif i < 8: note = 48
            elif i < 10: note = 45
            else: note = 41
            vel = 90 + i * 2
            add_note(t, note, vel)
        add_note(start_beat+6, 36, 100)
        add_note(start_beat+7, 36, 100)

    # Section 2: Latin Groove. Explores GM auxiliary percussion (congas, cascara, clave).
    # Structured to be strictly playable by two hands and two feet.
    def latin_section(start_beat):
        for bar in range(3): 
            b = start_beat + bar * 8
            # Cascara on ride cymbal edge and bell
            cascara_offsets = [0, 0.75, 1.5, 2.0, 2.75, 3.5, 4.0, 4.5, 5.25, 6.0, 6.5, 7.25]
            for off in cascara_offsets:
                note = 53 if off in [0, 2.0, 4.0, 6.0] else 51
                add_note(b + off, note, random.randint(85, 105))
            # 2-3 Son Clave on Side Stick
            clave_offsets = [1.0, 2.0, 4.0, 5.5, 7.0]
            for off in clave_offsets:
                add_note(b + off, 37, 110)
            # Tumbao bass drum pattern
            kick_offsets = [1.5, 3.5, 5.5, 7.5]
            for off in kick_offsets:
                add_note(b + off, 36, 100)
            # Conga pattern carefully interleaved so the left hand never overlaps clave hits
            conga_offsets = [(0.5, 64), (2.5, 63), (3.0, 62), (5.0, 62), (6.5, 63)]
            for off, note in conga_offsets:
                add_note(b + off, note, random.randint(70, 90))
            # Pedal hi-hat keeping time
            for off in [1.0, 3.0, 5.0, 7.0]:
                add_note(b + off, 44, 90)
                
        # Fill leading out of the Latin section on Timbales
        b = start_beat + 24
        for i in range(16): 
            t = b + i * 0.5
            note = 65 if i % 4 < 2 else 66 # High Timbale / Low Timbale
            vel = 60 + i * 3
            add_note(t, note, vel)
            if i % 2 == 0:
                add_note(t, 36, 90 + i*2)
                add_note(t, 44, 90)

    # Section 3: Aggressive heavy double bass and China cymbal pattern.
    def heavy_groove(start_beat):
        for bar in range(8):
            b = start_beat + bar * 4
            is_fill = (bar == 3 or bar == 7)
            if not is_fill:
                for i in range(4): add_note(b + i, 52, 110) # China Cymbal
                add_note(b + 1, 38, 120) # Heavy Snare
                add_note(b + 3, 38, 120)
                # Dense broken double bass 16ths
                kick_16ths = [0, 0.25, 0.5, 0.75, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.25, 3.5, 3.75]
                for off in kick_16ths: add_note(b + off, 36, 105)
            else:
                if bar == 3:
                    # 32nd note snare roll crescendo
                    for i in range(32):
                        t = b + i * 0.125
                        vel = 40 + int(i * 2.5)
                        add_note(t, 38, vel)
                        if i % 4 == 0: add_note(t, 36, 110)
                if bar == 7:
                    # Ripping 16th triplet tom fill
                    for i in range(24):
                        t = b + i * (1/6)
                        if i < 6: note = 38
                        elif i < 12: note = 50
                        elif i < 18: note = 45
                        else: note = 41
                        vel = 90 + (i%6)*5
                        add_note(t, note, vel)
                        if i % 3 == 0: add_note(t, 36, 110)

    # Section 4: Purely linear, funky groove. Drops dynamics dynamically to create an intense whisper.
    def linear_breakdown(start_beat):
        add_note(start_beat, 58, 110) # Vibraslap kicks off the breakdown!
        for bar in range(8):
            b = start_beat + bar * 4
            beats_to_play = 8 if bar == 7 else 16
                
            for i in range(beats_to_play):
                t = b + i * 0.25
                is_kick = (i in [0, 6, 11])
                is_snare_accent = (i in [4, 12])
                is_snare_ghost = (i in [3, 7, 9, 14])
                
                # Each limb has specific assigned hits that never overlap with other limbs
                if is_kick: add_note(t, 36, 100 if i==0 else 80)
                if is_snare_accent: add_note(t, 38, 110)
                if is_snare_ghost: add_note(t, 38, random.randint(30, 40))
                    
                if not is_kick and not is_snare_accent and not is_snare_ghost:
                    if i in [2, 10]: add_note(t, 46, 85) # Open hi-hat bark
                    else: add_note(t, 42, 60 + (20 if i%2==0 else 0))
                        
                if i in [3, 11]: add_note(t, 44, 70) # Pedal closes immediately after bark
                
            if bar == 7:
                # Minimal linear fill
                for j in range(8):
                    t = b + 2 + j * 0.25
                    if j % 3 == 2:
                        add_note(t, 36, 100)
                    else:
                        note = 38 if j < 4 else 50 
                        vel = 90 + j*4
                        add_note(t, note, vel)

    # Section 5: Complex 4-over-3 Polyrhythm on the ride bell built over a laid back funk pulse.
    def polyrhythm_groove(start_beat):
        for i in range(37): 
            t = start_beat + i * 0.75 # Dotted eighth notes
            add_note(t, 53, 105) # Ride Bell
            
        for bar in range(8):
            b = start_beat + bar * 4
            if bar < 7:
                add_note(b + 1.0, 38, 115)
                add_note(b + 3.0, 38, 115)
                add_note(b + 1.0, 44, 80)
                add_note(b + 3.0, 44, 80)
                kicks = [0, 1.75, 2.5]
                for k in kicks: add_note(b + k, 36, 100)
                ghosts = [0.5, 1.25, 2.75, 3.25]
                for g in ghosts: add_note(b + g, 38, random.randint(35, 45))
            else:
                # Snare & Kick strict unison crescendo roll
                for i in range(16):
                    t = b + i * 0.25
                    vel = min(127, 40 + int(i * 5.3))
                    note = 38 if i < 8 else 41
                    add_note(t, note, vel)
                    add_note(t, 36, vel)

    # Section 6: Freeform soloing on top of a driving quarter note kick pulse.
    def climax_solo(start_beat):
        for bar in range(12):
            b = start_beat + bar * 4
            for i in range(4):
                add_note(b + i, 44, 90)
                if bar % 4 != 2: 
                    add_note(b + i, 36, 110) # Drop kick pulse specifically on sextuplet bars
                    
            if bar % 4 == 0: # Sweeping tom runs
                add_note(b, 49, 120)
                add_note(b, 57, 120)
                for i in range(8, 32):
                    t = b + i * 0.125
                    if i < 16: note = 38
                    elif i < 20: note = 50
                    elif i < 24: note = 45
                    elif i < 28: note = 41
                    else: note = 38
                    add_note(t, note, 100 + random.randint(-10, 10))
            elif bar % 4 == 1: # Syncopated crashes and snare bombs
                crashes = [0, 1.5, 2.75]
                for c in crashes:
                    add_note(b + c, 55 if c == 1.5 else 49, 115) # Splashes
                    add_note(b + c, 38, 120)
                for i in range(16):
                    if i * 0.25 not in crashes:
                        add_note(b + i * 0.25, 38, random.randint(50, 70))
            elif bar % 4 == 2: # Linear sextuplets crossing between limbs
                for i in range(24):
                    t = b + i * (1/6)
                    if i % 3 == 2:
                        add_note(t, 36, 105)
                    else:
                        note = 38 if (i // 6) % 2 == 0 else 45
                        add_note(t, note, 95 + random.randint(-5, 5))
            elif bar % 4 == 3: # Driving build up to the next explosive bar
                for i in range(16):
                    t = b + i * 0.25
                    vel = 70 + int(i * 3.5)
                    add_note(t, 38, vel)
                    add_note(t, 41, vel)

    # Section 7: The climax starts moving towards the finish line. Heavy flam beats.
    def finale_build(start_beat):
        for bar in range(4):
            b = start_beat + bar * 4
            for i in range(8):
                add_note(b + i * 0.5, 59, 115) # Ride Crash
            # Massive flams on the 2 and 4
            add_note(b + 1.0, 38, 127)
            add_note(b + 0.95, 38, 80) # Flam Grace note
            add_note(b + 3.0, 38, 127)
            add_note(b + 2.95, 38, 80)
            # Galloping kick pattern
            kicks = [0, 0.5, 0.75, 1.5, 2.0, 2.5, 2.75, 3.5]
            for k in kicks:
                add_note(b + k, 36, 110)

    # Pure density and tension. Ending on a massive unison 1.
    def finale_fill(start_beat):
        b = start_beat
        for i in range(24): # Fast triplet sweep around the kit
            t = b + i * (1/6)
            if i < 6: note = 50
            elif i < 12: note = 48
            elif i < 18: note = 45
            else: note = 41
            add_note(t, note, 100 + i)
            if i % 3 == 0: add_note(t, 36, 110)
            
        b = start_beat + 4
        for beat_idx in range(4): # Hertas down the snare
            t = b + beat_idx
            add_note(t, 38, 110)
            add_note(t + 0.125, 38, 110)
            add_note(t + 0.25, 38, 120)
            add_note(t + 0.5, 38, 100)
            add_note(t, 36, 110)
            add_note(t + 0.5, 36, 110)
            
        b = start_beat + 8
        for i in range(32): # Piercing continuous snare roll over pulsing crashes
            t = b + i * 0.125
            vel = 70 + int(i * 1.5)
            add_note(t, 38, vel)
            if i % 8 == 0:
                add_note(t, 49, 120)
                add_note(t, 36, 120)
                
        b = start_beat + 12
        for i in range(24): # The "Blizzard" sextuplet pattern: R-L-R-L-Kick-Kick
            t = b + i * (1/6)
            pos = i % 6
            vel = min(127, 100 + i)
            if pos == 0: add_note(t, 38, vel)
            elif pos == 1: add_note(t, 50, vel)
            elif pos == 2: add_note(t, 45, vel)
            elif pos == 3: add_note(t, 41, vel)
            elif pos == 4: add_note(t, 36, vel) # Right Foot
            elif pos == 5: add_note(t, 35, vel) # Left Foot
            
        # Beat 240: The Final Hit lands without a fadeout
        b = start_beat + 16
        add_note(b, 49, 127) # Crash 1
        add_note(b, 57, 127) # Crash 2
        add_note(b, 36, 127) # Kick
        add_note(b, 38, 127) # Snare

    # --- Combine Sections ---
    # The sum of sections runs perfectly for 240 beats, matching roughly 2 minutes.
    motif_a(0)
    motif_a(8)
    motif_a(16)
    fill_1(24)
    
    latin_section(32)
    heavy_groove(64)
    linear_breakdown(96)
    polyrhythm_groove(128)
    climax_solo(160)
    finale_build(208)
    finale_fill(224)

    # Provide a mapped tempo envelope so the groove pushes, breathes, and settles
    # naturally matching the energy levels of the written sections.
    tempos = [
        (0, 118),
        (32, 122),
        (64, 116),
        (96, 115),
        (112, 120),
        (128, 118),
        (160, 124),
        (208, 126),
        (224, 128),
        (236, 120)
    ]

    # Map our structured note events and tempo into absolute MIDI ticks
    events = []
    
    for beat, note, vel in notes:
        tick_on = int(beat * 480)
        # We give percussion hits a very short note_off delta so that rolls and
        # rapid flams don't step on their own Note-Off releases.
        tick_off = int((beat + 0.02) * 480) 
        events.append((tick_on, 'note_on', note, vel))
        events.append((tick_off, 'note_off', note, 0))
        
    for beat, bpm in tempos:
        tick = int(beat * 480)
        events.append((tick, 'set_tempo', int(mido.bpm2tempo(bpm))))

    # Sort strictly by absolute ticks to handle overlaps elegantly
    def event_sort_key(e):
        tick = e[0]
        type_val = 0
        if e[1] == 'set_tempo': type_val = 1
        elif e[1] == 'note_off': type_val = 2
        elif e[1] == 'note_on': type_val = 3
        return (tick, type_val)

    events.sort(key=event_sort_key)

    # Initialize standard MIDI File
    mid = mido.MidiFile(ticks_per_beat=480)
    track0 = mido.MidiTrack()
    track1 = mido.MidiTrack()
    
    mid.tracks.append(track0)
    mid.tracks.append(track1)
    
    track0.append(mido.MetaMessage('track_name', name='Tempo Track', time=0))
    track1.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    # Program change 0 on GM Channel 10 acts as default mapping setup
    track1.append(mido.Message('program_change', program=0, channel=9, time=0))

    last_tick_0 = 0
    last_tick_1 = 0

    # Write events to tracks, converting to relative delta times
    for e in events:
        tick = e[0]
        if e[1] == 'set_tempo':
            delta = max(0, tick - last_tick_0)
            track0.append(mido.MetaMessage('set_tempo', tempo=e[2], time=delta))
            last_tick_0 = tick
        else:
            delta = max(0, tick - last_tick_1)
            # Send message to Channel 9 (which is mapped to Channel 10 via 0-indexing)
            track1.append(mido.Message(e[1], note=e[2], velocity=e[3], channel=9, time=delta))
            last_tick_1 = tick

    # Allow the very last hit to ring out fully before file end
    track1.append(mido.Message('note_off', note=49, velocity=0, channel=9, time=1920))

    mid.save('solo.mid')

if __name__ == '__main__':
    generate_solo()
