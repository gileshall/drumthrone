import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage
import random

# Seed for deterministic generation on every run
random.seed(808)

# General MIDI Drum Map constants (Channel 10)
KICK = 36
RIM = 37
SNARE = 38
TOM4 = 41  # Low Floor Tom
HAT_C = 42 # Closed Hi-Hat
HAT_P = 44 # Pedal Hi-Hat
TOM3 = 45  # Low Tom
HAT_O = 46 # Open Hi-Hat
TOM2 = 48  # Hi-Mid Tom
CRASH1 = 49
TOM1 = 50  # High Tom
RIDE = 51
CHINA = 52
RIDE_BELL = 53
SPLASH = 55
CRASH2 = 57

notes = []

def h_beat(b):
    # Humanize timing (±0.012 beats is ~±6ms at 120bpm)
    return b + random.uniform(-0.012, 0.012)

def h_vel(v):
    # Humanize velocity
    shift = int(random.uniform(-5, 6))
    return max(1, min(127, int(v) + shift))

def add_hit(beat, pitch, vel):
    b = max(0.0, h_beat(beat))
    notes.append((b, int(pitch), h_vel(vel)))

def add_flam(beat, pitch, vel):
    add_hit(max(0.0, beat - 0.03), pitch, vel // 2)
    add_hit(beat, pitch, vel)

def add_roll(start_beat, end_beat, pitch, base_vel, end_vel, step=0.125):
    cur = start_beat
    while cur < end_beat - 0.01:
        prog = (cur - start_beat) / (end_beat - start_beat)
        v = base_vel + (end_vel - base_vel) * prog
        add_hit(cur, pitch, v)
        cur += step

# --- Phrases and Motifs ---

def section_0_to_8():
    add_hit(0, CRASH2, 80)
    add_hit(0, KICK, 70)
    add_roll(2, 4, CRASH1, 20, 90, 0.125) 
    add_hit(4, CRASH1, 100)
    add_hit(4, KICK, 80)
    add_hit(4.5, SNARE, 40)
    add_hit(4.75, SNARE, 50)
    add_hit(5, TOM1, 60)
    add_hit(6, HAT_P, 70)
    add_hit(7, HAT_P, 70)
    add_hit(7.75, KICK, 80)

def play_motif_a(start, var_level=0):
    # Clavé-inspired core motif spanning 2 bars (8 beats)
    hits = [0.0, 1.5, 2.5, 4.0, 5.5, 6.0, 7.0]
    
    for b in [1, 3, 5, 7]:
        add_hit(start + b, HAT_P, 80)
        
    step = 0.25
    for i in range(32):
        b = i * step
        beat_time = start + b
        
        is_motif = any(abs(b - h) < 0.01 for h in hits)
                
        if is_motif:
            if var_level == 0:
                add_hit(beat_time, RIM, 90)
            elif var_level == 1:
                add_hit(beat_time, SNARE, 100)
                add_hit(beat_time, KICK, 90)
            elif var_level == 2:
                add_hit(beat_time, CRASH1 if b == 0.0 else SPLASH, 110)
                add_hit(beat_time, KICK, 100)
            elif var_level == 3:
                tom = [TOM1, TOM2, TOM3, TOM4][int(b) % 4]
                add_hit(beat_time, tom, 110)
                add_hit(beat_time, KICK, 100)
        else:
            if var_level == 0:
                if random.random() < 0.1: add_hit(beat_time, SNARE, 30)
            elif var_level == 1:
                if i % 2 == 0: add_hit(beat_time, HAT_C, 60)
                elif random.random() < 0.3: add_hit(beat_time, KICK, 70)
            elif var_level >= 2:
                if random.random() < 0.5:
                    add_hit(beat_time, KICK, 80)
                else:
                    add_hit(beat_time, SNARE, 40)

def groove_linear(start, bars):
    for bar in range(bars):
        bar_start = start + bar * 4
        for step in range(16):
            cur = bar_start + step * 0.25
            
            if step == 0:
                add_hit(cur, KICK, 110)
                add_hit(cur, RIDE, 90)
            elif step in [4, 12]:
                add_hit(cur, SNARE, 110)
                add_hit(cur, RIDE, 90)
            elif step == 8:
                add_hit(cur, KICK, 100)
                add_hit(cur, RIDE, 90)
            else:
                r = random.random()
                if step % 2 == 0:
                    add_hit(cur, RIDE, 70)
                    if r < 0.2: add_hit(cur, KICK, 80)
                else:
                    if r < 0.4: add_hit(cur, SNARE, random.randint(30, 50))
                    elif r < 0.6: add_hit(cur, KICK, random.randint(60, 80))

def play_motif_b(start):
    insts = [SNARE, SNARE, SNARE, TOM1, TOM1, TOM1, TOM2, TOM2, TOM2, TOM3, TOM3, TOM4]
    step = 0.333333
    for i in range(12):
        beat_time = start + i * step
        vel = 50 + (i / 11) * 60 
        add_hit(beat_time, insts[i], vel)
        if i % 3 == 0: add_hit(beat_time, KICK, vel + 10)
    add_hit(start + 4, CRASH1, 120)
    add_hit(start + 4, KICK, 120)

def fill_linear(start, beats, density_step):
    cur = start
    hands = [SNARE, TOM1, TOM2, TOM3, TOM4]
    patterns = [
        [('K', KICK), ('R', None), ('L', None)],
        [('R', None), ('L', None), ('K', KICK)],
        [('R', None), ('L', None), ('R', None), ('L', None), ('K', KICK), ('K', KICK)],
        [('R', None), ('K', KICK), ('L', None), ('K', KICK)],
        [('R', None), ('L', None)]
    ]
    
    while cur < start + beats - 0.01:
        pat = random.choice(patterns)
        r_inst, l_inst = random.choice(hands), random.choice(hands)
        
        for stroke, fixed_inst in pat:
            if cur >= start + beats - 0.01: break
            
            if fixed_inst:
                inst = fixed_inst
                vel = random.randint(90, 110)
            else:
                inst = r_inst if stroke == 'R' else l_inst
                vel = 100 if random.random() < 0.3 else 50
                if inst == SNARE and vel < 70: inst = SNARE 
            
            add_hit(cur, inst, vel)
            cur += density_step

def rudiment_fill(start, beats, rudiment="paradiddle"):
    step = 0.25 if beats > 2 else 0.125
    if rudiment == "paradiddle":
        base = "RLRRLRLL"
    elif rudiment == "six_stroke":
        base = "RLLRRL"
        step = 0.166666
        
    full_sticking = ""
    while len(full_sticking) * step < beats:
        full_sticking += base
        
    r_inst, l_inst = random.choice([SNARE, TOM1, TOM2]), random.choice([SNARE, TOM3, TOM4])
    
    for i, s in enumerate(full_sticking):
        cur = start + i * step
        if cur >= start + beats - 0.01: break
        
        inst = r_inst if s == 'R' else l_inst
        vel = 110 if (i % len(base)) == 0 else random.randint(50, 70)
        
        add_hit(cur, inst, vel)
        if (i % len(base)) == 0:
            add_hit(cur, KICK, 90)

def tribal_toms(start, bars):
    for i in range(bars * 16):
        cur = start + i * 0.25
        if i % 16 in [0, 6, 10]:
            add_hit(cur, TOM4, 110)
            add_hit(cur, TOM3, 100)
            add_hit(cur, KICK, 110)
        elif i % 16 in [4, 12]:
            add_hit(cur, SNARE, 110)
        else:
            if random.random() < 0.4:
                add_hit(cur, TOM1 if random.random() < 0.5 else TOM2, 70)
        if i % 4 == 0:
            add_hit(cur, HAT_P, 80)

def poly_3_over_4(start, bars):
    for i in range(bars * 16):
        cur = start + i * 0.25
        pos = i % 3
        if pos == 0:
            add_hit(cur, CHINA if (i % 6 == 0) else CRASH1, 100)
            add_hit(cur, KICK, 110)
        else:
            add_hit(cur, SNARE, 50)
            
        if (i % 16) == 4 or (i % 16) == 12:
            add_hit(cur, HAT_P, 80)

def climax_build(start, bars):
    total = bars * 32
    for i in range(total):
        cur = start + i * 0.125
        prog = i / total
        vel = int(40 + prog * 70)
        add_hit(cur, SNARE, vel)
        if i % 2 == 0:
            add_hit(cur, KICK, vel + 10)
        if i % 32 == 0:
            add_hit(cur, CRASH1, vel + 20)

def play_motif_b_ext(start, beats):
    step = 0.333333
    total_notes = int(beats / step)
    toms = [SNARE, TOM1, TOM2, TOM3, TOM4]
    
    for i in range(total_notes):
        cur = start + i * step
        prog = i / total_notes
        tom_idx = min(len(toms) - 1, int(prog * len(toms)))
        vel = int(60 + prog * 60)
        
        add_hit(cur, toms[tom_idx], vel)
        if i % 3 == 0:
            add_hit(cur, KICK, vel + 10)
            if prog > 0.5:
                add_hit(cur, CRASH2, vel)

def showcase_chops(start, beats):
    for i in range(int(beats / 0.125)):
        cur = start + i * 0.125
        pos = i % 4
        if pos == 0:
            add_hit(cur, random.choice([SNARE, CRASH1, CRASH2]), 120)
        elif pos == 1:
            add_hit(cur, random.choice([TOM1, TOM2, TOM3]), 100)
        else:
            add_hit(cur, KICK, 110)

def breakdown(start, bars):
    for b in range(bars * 4):
        cur = start + b
        add_hit(cur, RIDE_BELL, 90)
        if b % 2 == 0:
            add_hit(cur, KICK, 100)
        else:
            add_hit(cur, SNARE, 110)
        if b % 4 == 3:
            add_hit(cur + 0.5, HAT_O, 80)
            add_hit(cur + 0.75, HAT_P, 90)
            add_hit(cur + 0.875, SNARE, 60)

def big_finish(start):
    add_flam(start, SNARE, 127)
    add_hit(start, KICK, 127)
    
    add_flam(start + 1, TOM1, 120)
    add_hit(start + 1, KICK, 120)
    add_flam(start + 1.5, TOM2, 120)
    
    add_hit(start + 2, TOM3, 120)
    add_hit(start + 2.333, TOM4, 120)
    add_hit(start + 2.666, KICK, 127)
    
    # Silence on 239, land final massive hit on 240
    add_hit(start + 4, CRASH1, 127)
    add_hit(start + 4, CRASH2, 127)
    add_hit(start + 4, KICK, 127)

# --- Construct the 2-Minute Timeline (240 Beats) ---

section_0_to_8()                         # 0 - 8
play_motif_a(8, var_level=0)             # 8 - 16
play_motif_a(16, var_level=1)            # 16 - 24
groove_linear(24, 2)                     # 24 - 32
play_motif_a(32, var_level=2)            # 32 - 40

add_hit(40, KICK, 80)
add_hit(40, CRASH2, 90)
add_hit(41.5, KICK, 80)
add_hit(42, SNARE, 100)
add_hit(42, KICK, 80); add_hit(42.5, HAT_O, 90); add_hit(43, HAT_P, 90)
play_motif_b(44)                         # 40 - 48

groove_linear(48, 2)                     # 48 - 56
fill_linear(56, 4, 0.25)                 # 56 - 60
rudiment_fill(60, 4, "six_stroke")       # 60 - 64

tribal_toms(64, 4)                       # 64 - 80
play_motif_a(80, var_level=3)            # 80 - 88
play_motif_a(88, var_level=3)            # 88 - 96
poly_3_over_4(96, 4)                     # 96 - 112
climax_build(112, 4)                     # 112 - 128
fill_linear(128, 8, 0.166666)            # 128 - 136
rudiment_fill(136, 8, "paradiddle")      # 136 - 144
play_motif_a(144, var_level=2)           # 144 - 152
play_motif_a(152, var_level=2)           # 152 - 160
play_motif_b_ext(160, 16)                # 160 - 176
showcase_chops(176, 16)                  # 176 - 192
breakdown(192, 4)                        # 192 - 208
poly_3_over_4(208, 4)                    # 208 - 224
showcase_chops(224, 12)                  # 224 - 236
big_finish(236)                          # 236 - 240

# --- File Generation ---

ticks_per_beat = 480
events = []

for b, pitch, vel in notes:
    tick = int(b * ticks_per_beat)
    events.append({'type': 'note_on', 'tick': tick, 'pitch': pitch, 'vel': vel})
    events.append({'type': 'note_off', 'tick': tick + int(0.03 * ticks_per_beat), 'pitch': pitch, 'vel': 0})

tempos = {
    0: 120, 24: 122, 48: 120, 80: 124, 112: 128, 
    160: 132, 192: 118, 208: 126, 236: 110, 239: 90
}

for b, bpm in tempos.items():
    events.append({'type': 'tempo', 'tick': int(b * ticks_per_beat), 'tempo': mido.bpm2tempo(bpm)})

# Tempo first, Note Off clears existing voice, Note On takes voice
priority = {'tempo': 0, 'note_off': 1, 'note_on': 2}
events.sort(key=lambda x: (x['tick'], priority[x['type']]))

mid = MidiFile(ticks_per_beat=ticks_per_beat)
track = MidiTrack()
mid.tracks.append(track)

track.append(MetaMessage('track_name', name='Drum Solo', time=0))
track.append(Message('program_change', program=0, channel=9, time=0))

prev_tick = 0
for ev in events:
    delta = ev['tick'] - prev_tick
    if delta < 0: delta = 0
    
    if ev['type'] == 'tempo':
        track.append(MetaMessage('set_tempo', tempo=ev['tempo'], time=delta))
    elif ev['type'] == 'note_on':
        track.append(Message('note_on', channel=9, note=ev['pitch'], velocity=ev['vel'], time=delta))
    elif ev['type'] == 'note_off':
        track.append(Message('note_off', channel=9, note=ev['pitch'], velocity=ev['vel'], time=delta))
        
    prev_tick += delta

mid.save('solo.mid')
