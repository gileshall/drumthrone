import mido
import random
import math

# Set fixed seed for identical output on every run
random.seed(42)

# General MIDI Drum notes
KICK = 36
SNARE = 38
SNARE_RIM = 37
HAT_CLOSED = 42
HAT_PEDAL = 44
HAT_OPEN = 46
TOM_HI = 50
TOM_MID = 47
TOM_LOW = 43
CRASH_1 = 49
CRASH_2 = 57
RIDE = 51
RIDE_BELL = 53
SPLASH = 55

events = []

def add_hit(time, note, vel):
    events.append((time, note, vel))

def humanize(time, vel):
    # Add slight imperfections to timing and velocity
    t_wobble = random.gauss(0, 0.015)
    v_wobble = int(random.gauss(0, 4))
    return time + t_wobble, max(1, min(127, vel + v_wobble))

def play_roll(start_beat, length_beats, rate, start_vel, end_vel, note):
    num_hits = int(length_beats / rate)
    for i in range(num_hits):
        t = start_beat + i * rate
        progress = i / max(1, num_hits - 1)
        # Exponential curve for more natural swell
        curve = progress ** 1.5 
        v = start_vel + (end_vel - start_vel) * curve
        th, vh = humanize(t, int(v))
        add_hit(th, note, vh)

def linear_fill(start_beat, length_beats, rate, notes, base_vel=90):
    num_hits = int(length_beats / rate)
    for i in range(num_hits):
        t = start_beat + i * rate
        note = random.choice(notes)
        # Occasional accents
        is_accent = (i % int(1/rate) == 0) or random.random() < 0.15
        vel = min(127, base_vel + 25) if is_accent else max(1, base_vel - 25)
        th, vh = humanize(t, vel)
        add_hit(th, note, vh)

def play_groove(start_measure, end_measure, ride_note, snare_type, complexity):
    for m in range(start_measure, end_measure):
        m_start = m * 4
        # Ride/Hat pattern
        for b in range(8):
            t = m_start + b * 0.5
            vel = 65 if b % 2 == 1 else 90
            if b == 0: vel = 105 
            th, vh = humanize(t, vel)
            add_hit(th, ride_note, vh)
            
        # Kick
        kicks = [0, 2.5] if complexity < 1 else [0, 1.5, 2.5, 3.75]
        if random.random() < 0.3 * complexity:
            kicks.append(random.choice([1.25, 2.75, 3.25]))
        for k in kicks:
            th, vh = humanize(m_start + k, 100)
            add_hit(th, KICK, vh)
            
        # Snare backbeat
        snares = [1, 3]
        for s in snares:
            th, vh = humanize(m_start + s, 115)
            add_hit(th, snare_type, vh)
            
        # Ghost notes on snare
        num_ghosts = int(complexity * random.randint(1, 4))
        ghost_positions = [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75]
        random.shuffle(ghost_positions)
        for i in range(min(num_ghosts, len(ghost_positions))):
            gp = ghost_positions[i]
            if gp not in kicks:
                th, vh = humanize(m_start + gp, random.randint(30, 50))
                add_hit(th, SNARE, vh)

        # Occasional fill at end of measure
        if random.random() < 0.25 * complexity:
            fill_len = random.choice([0.5, 1.0])
            fill_start = m_start + 4 - fill_len
            linear_fill(fill_start, fill_len, 0.25, [SNARE, TOM_HI, TOM_MID, TOM_LOW, KICK], 85)

def phrase_paradiddle(start_beat, beats, rate=0.25, vel_accent=110, vel_ghost=45):
    # R L R R L R L L
    hands = ['R', 'L', 'R', 'R', 'L', 'R', 'L', 'L']
    notes = {'R': RIDE_BELL, 'L': SNARE}
    
    num_hits = int(beats / rate)
    for i in range(num_hits):
        hand = hands[i % 8]
        t = start_beat + i * rate
        is_accent = (i % 4 == 0)
        v = vel_accent if is_accent else vel_ghost
        th, vh = humanize(t, v)
        add_hit(th, notes[hand], vh)
        if is_accent and hand == 'R':
            tk, vk = humanize(t, vel_accent)
            add_hit(tk, KICK, vk)

def phrase_3_over_4(start_beat, beats):
    # Motif: Polyrhythmic tension, playing dotted-quarters over straight 4/4
    for i in range(int(beats / 1.5)):
        t = start_beat + i * 1.5
        th, vh = humanize(t, 115)
        add_hit(th, CRASH_1 if i % 2 == 0 else CRASH_2, vh)
        tk, vk = humanize(t, 115)
        add_hit(tk, KICK, vk)
    
    # Fill gaps dynamically
    for i in range(int(beats / 0.25)):
        t = start_beat + i * 0.25
        if abs((t - start_beat) % 1.5) > 0.1: # Avoid masking the accents
            note = random.choice([SNARE, TOM_HI, TOM_MID, TOM_LOW])
            th, vh = humanize(t, random.randint(65, 90))
            add_hit(th, note, vh)

# --- Construct the Drum Solo ---

# Section 1: Intro build-up on snare and toms (0-16 beats)
play_roll(0, 8, 0.5, 30, 85, TOM_LOW)
play_roll(8, 8, 0.25, 45, 105, SNARE)
add_hit(*humanize(16, 115), CRASH_1)
add_hit(*humanize(16, 115), KICK)

# Section 2: Groove establishment & development (16-48 beats)
play_groove(4, 12, HAT_CLOSED, SNARE, complexity=1.3)

# Section 3: Paradiddle variations traveling around the kit (48-80 beats)
for m in range(12, 20):
    start = m * 4
    if m % 2 == 0:
        phrase_paradiddle(start, 4, rate=0.25)
    else:
        # Move right hand to Toms
        num_hits = int(4 / 0.25)
        hands = ['R', 'L', 'R', 'R', 'L', 'R', 'L', 'L']
        tom_map = [TOM_HI, TOM_MID, TOM_LOW, TOM_MID]
        for i in range(num_hits):
            hand = hands[i % 8]
            t = start + i * 0.25
            is_accent = (i % 4 == 0)
            v = 110 if is_accent else 55
            th, vh = humanize(t, v)
            if hand == 'R':
                note = tom_map[(i // 8) % 4]
                add_hit(th, note, vh)
                if is_accent:
                    add_hit(*humanize(t, v), KICK)
            else:
                add_hit(th, SNARE, vh)

# Section 4: 3-over-4 tension build-up (80-112 beats)
for m in range(20, 28):
    phrase_3_over_4(m * 4, 4)

# Section 5: Soft, breathing jazzy transition (112-144 beats)
for m in range(28, 36):
    start = m * 4
    for b in range(4):
        # Jazz swing ride
        add_hit(*humanize(start + b, 70), RIDE)
        add_hit(*humanize(start + b + 0.66, 50), RIDE)
        add_hit(*humanize(start + b + 0.83, 60), RIDE)
        # Hat pedal on beats 2 and 4
        if b == 1 or b == 3:
            add_hit(*humanize(start + b, 85), HAT_PEDAL)
        # Whispering ghost snares
        if random.random() < 0.6:
            add_hit(*humanize(start + b + random.choice([0.33, 0.66]), random.randint(25, 45)), SNARE)
        # Sparse kicks
        if random.random() < 0.25:
            add_hit(*humanize(start + b + random.choice([0.0, 0.5]), random.randint(40, 60)), KICK)

# Section 6: Huge crescendo roll into the climax (144-152 beats)
play_roll(144, 8, 1/6, 20, 127, SNARE)
play_roll(144, 8, 0.5, 30, 120, KICK)
add_hit(*humanize(152, 127), CRASH_1)
add_hit(*humanize(152, 127), CRASH_2)

# Section 7: Heavy rock groove climax (152-176 beats)
play_groove(38, 44, RIDE_BELL, SNARE, complexity=2.0)

# Section 8: Rapid linear fills around the kit (176-208 beats)
for m in range(44, 52):
    start = m * 4
    notes = [SNARE, TOM_HI, TOM_MID, TOM_LOW, KICK, CRASH_1]
    linear_fill(start, 4, 1/6, notes, base_vel=105)

# Section 9: Frenetic finale soloing (208-236 beats)
for m in range(52, 59):
    start = m * 4
    phrase_3_over_4(start, 2)
    linear_fill(start + 2, 2, 0.125, [SNARE, KICK, TOM_HI, TOM_LOW], base_vel=115)

# Section 10: The big ending hits (236-240 beats)
add_hit(*humanize(236, 120), CRASH_1)
add_hit(*humanize(236, 120), KICK)
add_hit(*humanize(237.5, 120), CRASH_2)
add_hit(*humanize(237.5, 120), KICK)
add_hit(*humanize(238.5, 127), SNARE)
add_hit(*humanize(238.5, 127), TOM_LOW)
play_roll(239, 1, 0.125, 100, 127, TOM_HI)
add_hit(*humanize(240, 127), CRASH_1)
add_hit(*humanize(240, 127), CRASH_2)
add_hit(*humanize(240, 127), KICK)

# Pad end to let ring out
add_hit(244, KICK, 1)

# --- Compile to MIDI ---
ticks_per_beat = 480
mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
track = mido.MidiTrack()
mid.tracks.append(track)

# 120 BPM = 500,000 microseconds per beat
track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))

# Convert beats to absolute ticks
tick_events = []
for ev in events:
    t_beats, note, vel = ev
    abs_tick = max(0, int(t_beats * ticks_per_beat))
    tick_events.append((abs_tick, note, vel))

# Sort chronologically
tick_events.sort(key=lambda x: x[0])

# Write delta times
last_tick = 0
for abs_tick, note, vel in tick_events:
    delta = abs_tick - last_tick
    last_tick = abs_tick
    # MIDI channel 9 is GM Channel 10
    track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
    track.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=0))

mid.save('solo.mid')
