import mido
import random
import math

# Fixed seed for deterministic output
random.seed(42)

ticks_per_beat = 480
hits = []
tempo_track = []

def add_tempo(beat, bpm):
    tempo_track.append((beat, mido.bpm2tempo(bpm)))

def hit(t, inst, vel, human_t=0.012, human_v=8):
    # Apply global push/pull to surge and settle the pulse organically
    t_warped = t + math.sin(t * math.pi / 4) * 0.02 + math.sin(t * math.pi / 16) * 0.04
    # Apply random micro-timing for flam-like realism on unquantized hits
    t_final = t_warped + random.uniform(-human_t, human_t)
    
    # Humanize velocity, shaping accents and ghost notes
    vel_final = int(vel + random.uniform(-human_v, human_v))
    vel_final = max(1, min(127, vel_final))
    
    hits.append((t_final, inst, vel_final))

def flam(t, inst, vel=100):
    hit(t - 0.03, inst, max(1, vel // 2))
    hit(t, inst, vel)

def drag(t, inst, vel=40):
    hit(t - 0.05, inst, vel)
    hit(t - 0.025, inst, vel)

def swell(start, end, inst, start_vel, end_vel):
    dur = end - start
    count = int(dur * 8) # 32nd notes
    for i in range(count):
        t = start + i / 8.0
        vel = start_vel + (end_vel - start_vel) * (i / count)
        # Internal phrasing: accent the downbeats/upbeats
        is_accent = (i % 4 == 0)
        actual_vel = vel if not is_accent else min(127, vel + 10)
        hit(t, inst, actual_vel, human_t=0.02, human_v=5)

def intro(start, bars):
    # Atmospheric intro: cymbal swells, heartbeat kick, scattered rim clicks
    swell(start, start + 4, 51, 30, 70) 
    swell(start + 4, start + 8, 49, 30, 80)
    
    for b in range(bars):
        base = start + b * 4
        hit(base, 36, 60)
        hit(base + 0.5, 36, 40)
        
        if b % 2 == 1:
            hit(base + 2, 37, 75)
            hit(base + 3.5, 37, 65)
            
        if b == 2:
            hit(base + 3, 50, 60)
            hit(base + 3.25, 48, 55)
        if b == 3:
            # Lead into groove
            hit(base + 2.5, 38, 70)
            hit(base + 3.0, 38, 85)
            hit(base + 3.5, 38, 100)
            hit(base + 3.75, 45, 100)

def play_groove(start, bars):
    for b in range(bars):
        base = start + b * 4
        ride_mode = b >= 4
        
        # Ride / Hat pattern
        for i in range(8):
            t = base + i * 0.5
            vel = 80 if i % 2 == 0 else 55
            if ride_mode:
                inst = 51 if i % 4 != 0 else 53
                if b % 4 == 0 and i == 0: inst = 49 # crash on downbeat of phrase
                hit(t, inst, vel)
                if random.random() < 0.4: hit(t + 0.25, 51, 35)
            else:
                inst = 42
                if b % 4 == 0 and i == 0 and b > 0: inst = 49
                if b % 2 == 1 and i == 7: inst = 46 # open hat on the 'and' of 4
                hit(t, inst, vel)
                if random.random() < 0.3: hit(t + 0.25, 42, 30)
                    
        # Kicks
        kicks = [0, 1.5, 2.5]
        if b % 4 == 3: kicks += [3.25]
        if ride_mode: kicks.append(0.75)
        for k in kicks:
            hit(base + k, 36, 100)
            
        # Snares
        hit(base + 1, 38, 110)
        hit(base + 3, 38, 110)
        
        # Dynamic snare ghost notes
        ghosts = [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75]
        for g in ghosts:
            if g not in kicks and g not in [1, 3]:
                if random.random() < (0.6 if ride_mode else 0.4):
                    hit(base + g, 38, 40)
                    
        # Fills
        if b % 4 == 3:
            hit(base + 2.75, 38, 90)
            hit(base + 3.0, 50, 105)
            hit(base + 3.25, 48, 105)
            hit(base + 3.5, 45, 110)
            hit(base + 3.75, 45, 100)

def linear_fill(start, bars):
    for b in range(bars):
        base = start + b * 4
        
        pattern = ['R','L','K','K', 'R','L','K','R', 'L','K','K','R', 'L','R','L','K']
        if b % 2 == 1:
            pattern = ['R','K','L','K', 'R','L','R','L', 'K','K','R','L', 'R','L','R','L']
        if b == bars - 1:
            pattern = ['R','L'] * 8
            
        for i, stroke in enumerate(pattern):
            t = base + i * 0.25
            if stroke == 'K':
                hit(t, 36, 115)
            elif stroke == 'R':
                inst = 42 if b < 4 else 51
                if i % 4 == 0: inst = 46 if b < 4 else 53
                if b == bars - 1: inst = 50 if i < 8 else 48
                if b % 4 == 0 and i == 0: inst = 49 # phrase crash
                vel = 105 if i % 4 == 0 else 75
                hit(t, inst, vel)
            elif stroke == 'L':
                inst = 38
                vel = 110 if i in [4, 12] and b != bars - 1 else 45
                if b == bars - 1: vel = 105
                hit(t, inst, vel)
                
            # Anchor time with hi-hat pedal
            if i % 4 == 0:
                hit(t, 44, 85)

def paradiddle_groove(start, bars):
    p = ['R', 'L', 'R', 'R', 'L', 'R', 'L', 'L']
    for b in range(bars):
        base = start + b * 4
        
        kicks = [0, 1.5, 2, 3.5]
        if b % 2 == 1: kicks.append(2.75)
        for k in kicks: hit(base + k, 36, 110)
        
        hit(base + 1, 44, 85)
        hit(base + 3, 44, 85)
        
        if b % 4 == 2: hit(base, 55, 100) # Splash coloration
        
        for i in range(16):
            t = base + i * 0.25
            stroke = p[i % 8]
            
            if stroke == 'R':
                inst = 53 if b >= 4 and i % 8 == 0 else 51
                if b % 4 == 3 and i >= 8: inst = 48
                if i == 0 and b % 4 == 0: inst = 57 # Crash 2
                vel = 100 if i % 4 == 0 else 65
                hit(t, inst, vel)
            else:
                inst = 38
                vel = 115 if i in [4, 12] else 40
                if i in [4, 12]:
                    flam(t, inst, vel)
                elif vel == 40 and random.random() < 0.2:
                    drag(t, inst, vel)
                else:
                    hit(t, inst, vel)
                    
            if b == bars - 1 and i >= 8:
                # Flowing snare roll into next section
                hit(t, 38, 90 + (i-8)*4)
                if i % 2 == 0:
                    hit(t + 0.125, 38, 85 + (i-8)*4)

def poly_solo_extended(start, bars):
    # Rhythmic displacement: 3 and 5 note groupings mapped to 16th notes
    for b in range(bars):
        base = start + b * 4
        
        hit(base + 1, 44, 95)
        hit(base + 3, 44, 95)
        if b % 2 == 1: hit(base + 2, 56, 105) # Cowbell integration
        
        toms = [50, 48, 45, 41]
        tom_inst = toms[b % 4]
        
        grouping = 3 if b < 4 else 5
        pattern3 = [(tom_inst, 115), (38, 55), (36, 115)]
        pattern5 = [(tom_inst, 115), (38, 55), (36, 115), (36, 105), (38, 65)]
        pat = pattern3 if grouping == 3 else pattern5
        
        for i in range(16):
            t = base + i * 0.25
            
            if b % 4 == 3 and i >= 8:
                t_idx = (i - 8) // 2
                fill_tom = toms[min(t_idx, 3)]
                hit(t, fill_tom, 115)
                hit(t + 0.125, fill_tom, 105)
                continue
                
            inst, vel = pat[i % len(pat)]
            if i == 0 and b % 4 == 0:
                inst, vel = 49, 115 # Phrase crash
            
            if inst == 38 and vel < 70 and random.random() < 0.3:
                drag(t, inst, vel)
            else:
                hit(t, inst, vel)

def fast_singles(start, bars):
    kit = [38, 50, 48, 45, 41]
    for b in range(bars):
        base = start + b * 4
        
        if b % 2 == 0: hit(base, 36, 120)
        if b % 2 == 1: hit(base + 2, 36, 120)
            
        for i in range(8):
            hit(base + i*0.5, 44, 105)
            
        current_inst = 38
        notes = 24 if b != bars - 1 else 18
        for i in range(notes):
            t = base + i * (4.0 / 24.0)
            vel = 120 if i % 6 == 0 else 85
            
            # Hands traveling organically around the toms
            if random.random() < 0.25:
                current_inst = random.choice(kit)
                
            # Intercept with kick for hertas/chops
            if random.random() < 0.15:
                hit(t, 36, 120)
            else:
                # Start on crash naturally for downbeats
                if i == 0 and b % 2 == 0: hit(t, 49, 120)
                elif i == 0 and b % 2 == 1: hit(t, 57, 120)
                else: hit(t, current_inst, vel)
                
        if b == bars - 1:
            # Syncopated lead-in crashes
            for i in range(4):
                t = base + 3 + i * 0.25
                hit(t, 49, 127)
                hit(t, 57, 127)
                hit(t, 36, 127)

def heavy_climax(start, bars):
    # Half-time feel, heavy and loud
    for b in range(bars):
        base = start + b * 4
        
        for i in range(4):
            if b % 4 == 3 and i >= 2: continue # Free hands for fill
            hit(base + i, 49 if i%2==0 else 57, 120)
            if i == 2: hit(base + i, 52, 127) # Aggressive China cymbal
            
        if b % 4 != 3:
            hit(base + 2, 38, 127)
            flam(base + 2, 38, 127)
        
        kicks = [0, 0.75, 1.0, 1.5, 2.5, 3.25, 3.5]
        for k in kicks:
            hit(base + k, 36, 125)
            
        if b % 4 == 3:
            # Huge fills on beats 3 and 4
            for i in range(12):
                t = base + 2 + i * (2.0 / 12.0)
                inst = 38 if i < 4 else (50 if i < 8 else 45)
                hit(t, inst, 115 + i)
                if i % 3 == 0: hit(t, 36, 120)

def crescendo_roll(start, bars):
    total_beats = bars * 4
    total_notes = total_beats * 8 # 32nd notes
    
    for i in range(total_notes):
        t = start + i * 0.125
        progress = i / total_notes
        
        if progress < 0.25: inst = 41
        elif progress < 0.5: inst = 45
        elif progress < 0.75: inst = 50
        else: inst = 38
            
        vel = int(20 + 107 * (progress ** 1.5))
        is_accent = (i % 4 == 0)
        actual_vel = min(127, int(vel * 1.2)) if is_accent else vel
        
        if i % 8 == 0: hit(t, 36, vel)
        hit(t, inst, actual_vel, human_t=0.015, human_v=5)

def finale(start):
    # Dotted-eighth pattern syncopated hits building final tension
    hits_b1 = [0, 0.75, 1.5, 2.25, 3.0, 3.5]
    for k in hits_b1:
        hit(start + k, 49, 127)
        hit(start + k, 38, 127)
        hit(start + k, 36, 127)
        
    for i in range(6):
        t = start + 4 + i * (2.0 / 3.0)
        hit(t, 50 if i < 3 else 45, 127)
        hit(t, 36, 127)
        
    for i in range(8):
        t = start + 6 + i * 0.125
        hit(t, 38, 127)
        if i % 2 == 0: hit(t, 36, 127)
        
    # Keep the pulse alive in the final moment of silence
    hit(start + 7.0, 44, 90)
    hit(start + 7.5, 44, 90)
    
    # Land the definitive final hit
    hit(start + 8 - 0.03, 38, 110) # Heavy flam
    hit(start + 8, 49, 127)
    hit(start + 8, 57, 127)
    hit(start + 8, 36, 127)
    hit(start + 8, 38, 127)


# --- Performance Composition Sequence ---
# Total 240 beats. Tempo adjustments create roughly exactly a 2-minute showcase.

add_tempo(0, 110)
intro(0, 4)                  # Beats 0 - 16
add_tempo(16, 115)
play_groove(16, 8)           # Beats 16 - 48
add_tempo(48, 122)
linear_fill(48, 8)           # Beats 48 - 80
add_tempo(80, 126)
paradiddle_groove(80, 8)     # Beats 80 - 112
add_tempo(112, 130)
poly_solo_extended(112, 8)   # Beats 112 - 144
add_tempo(144, 135)
fast_singles(144, 8)         # Beats 144 - 176
add_tempo(176, 110) 
heavy_climax(176, 8)         # Beats 176 - 208
add_tempo(208, 120) 
crescendo_roll(208, 6)       # Beats 208 - 232
add_tempo(224, 125) 
add_tempo(232, 115)
finale(232)                  # Beats 232 - 240
add_tempo(236, 105) 
add_tempo(238, 90)

# --- Compile to MIDI ---
all_events = []

for t, inst, vel in hits:
    all_events.append((t, 'note_on', inst, vel))
    # Note_offs shortly after (to ensure they process correctly without truncating overlapping rolls)
    all_events.append((t + 0.015, 'note_off', inst, 0))

for t, t_val in tempo_track:
    all_events.append((t, 'tempo', t_val))

# Sorting guarantees strict chronological sequence for delta-time conversion
all_events.sort(key=lambda x: x[0])

mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
track = mido.MidiTrack()
mid.tracks.append(track)

CHANNEL = 9 # General MIDI Percussion channel (0-indexed 10)

last_tick = 0
for ev in all_events:
    t_beats = ev[0]
    abs_tick = int(t_beats * ticks_per_beat)
    abs_tick = max(last_tick, abs_tick)
    delta = abs_tick - last_tick
    last_tick = abs_tick
    
    if ev[1] == 'note_on':
        track.append(mido.Message('note_on', channel=CHANNEL, note=ev[2], velocity=ev[3], time=delta))
    elif ev[1] == 'note_off':
        track.append(mido.Message('note_off', channel=CHANNEL, note=ev[2], velocity=0, time=delta))
    elif ev[1] == 'tempo':
        track.append(mido.MetaMessage('set_tempo', tempo=ev[2], time=delta))

track.append(mido.MetaMessage('end_of_track', time=ticks_per_beat))

mid.save('solo.mid')
