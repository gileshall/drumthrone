import mido
import random
from collections import defaultdict

# --- GENERATION SETTINGS ---
BPM = 112
TICKS_PER_BEAT = 480
VELOCITIES = {
    'O': 127,
    'X': 110,
    'x': 85,
    'g': 55,
    's': 35,
}

events = []

def add_pattern(start_beat, step_size, pitch, pattern):
    for i, char in enumerate(pattern):
        beat = start_beat + i * step_size
        if char in VELOCITIES:
            events.append((beat, pitch, VELOCITIES[char]))
        elif char == 'f':  # Flam
            events.append((beat - 0.05, pitch, 50))
            events.append((beat, pitch, 105))
        elif char == 'd':  # Drag
            events.append((beat - 0.1, pitch, 40))
            events.append((beat - 0.05, pitch, 45))
            events.append((beat, pitch, 85))
        elif char == 'r':  # Roll / Buzz
            events.append((beat, pitch, 60))
            events.append((beat + step_size/3, pitch, 50))
            events.append((beat + 2*step_size/3, pitch, 40))

def make_bars(start_bar, count, patterns, step=0.25):
    if count == 0: return
    for pitch, pat in patterns.items():
        if isinstance(pat, str):
            req_len = int(count * 4 / step)
            repeats = (req_len // len(pat)) + 1
            full_pat = (pat * repeats)[:req_len]
            add_pattern(start_bar * 4, step, pitch, full_pat)

def make_build(start_bar, num_bars, pitch, step, start_vel, end_vel):
    steps = int(num_bars * 4 / step)
    for i in range(steps):
        beat = start_bar * 4 + i * step
        vel = int(start_vel + (end_vel - start_vel) * i / max(1, steps - 1))
        events.append((beat, pitch, vel))

def make_triplet_fill(start_bar):
    beat = start_bar * 4
    events.append((beat, 49, 127))
    events.append((beat, 36, 127))
    for i in range(1, 6):
        events.append((beat + i/6.0, 38, 100))
    for i in range(6):
        events.append((beat + 1 + i/6.0, 50, 110))
    for i in range(6):
        events.append((beat + 2 + i/6.0, 48, 115))
    for i in range(6):
        events.append((beat + 3 + i/6.0, 45, 120))
        events.append((beat + 3 + i/6.0, 36, 120))

# --- COMPOSITION (56 BARS) ---

# 0-6: Intro Motif (Tribal floor tom groove)
intro_pat = {
    36: "X..x.x..X..x.x..X..x.x..X..x.X..", # Kick drum gallop
    43: "..X...x...X...x...X...x...X...x.", # Floor tom
    37: "....X.......X.......X.......x.x.", # Snare cross-stick rim
    44: "X.......X.......X.......X.......", # Pedal Hi-Hat on 1 and 3
}
make_bars(0, 6, intro_pat)

# 6-8: Intro fill transitioning to main groove
fill_1 = {
    36: "X..x.x..X..x.x..X...............",
    43: "..X...x...X...x.................",
    37: "....X.......X...................",
    50: "....................xxxx........",
    48: "........................xxxx....",
    45: "............................xxxx",
}
make_bars(6, 2, fill_1)

# 8-15: Groove 1 (Classic ride and snare)
groove_1 = {
    51: "X.x.X.x.X.x.X...",
    53: "..............X.",
    38: "....X.......X...",
    36: "X.......X.x.....",
    44: "x...x...x...x...",
}
make_bars(8, 7, groove_1)

# 15-16: Fill 2
fill_2 = {
    49: "X...............",
    51: "..x.X.x.........", 
    38: "....X...d.d.X.X.", # Snare drags
    36: "X...............",
    44: "x...x...x...x...",
}
make_bars(15, 1, fill_2)

# 16-23: Groove 1 Variation (Density & ghost notes)
groove_1_var = {
    51: "X.x.X.x.X.x.X...X.x.X.x.X.x.X...",
    53: "..............X...............X.",
    38: "....X..g.g..X..g..g.X..g.g..X..g",
    36: "X.......X.X.....X..x....X.x.....",
    44: "x...x...x...x...x...x...x...x...",
}
make_bars(16, 7, groove_1_var)

# 23-24: Fill 3 (Fast linear triplet-style Gospel fill)
fill_3 = {
    55: "X...............", # Splash cymbal
    38: "....X..g..XX....", 
    36: "X.......XX....XX",
    50: "............X...",
    48: ".............X..",
    45: "..............X.",
    44: "x...x...x...x...",
}
make_bars(23, 1, fill_3)

# 24-31: Groove Hat (Funky disco-style hats with choking)
groove_hat = {
    42: "X.x.X.x.X.x.X...X.x.X.x.X.x.X...",
    46: "..............O...............O.", # Open hat
    38: "....X..g..g.X.......X..g..g.X..g",
    36: "X.x.....X.......X.x.....X.......",
}
make_bars(24, 7, groove_hat)

# 31-32: Fill 4 
fill_4 = {
    49: "X...............",
    42: "....x.x.x.x.....",
    38: "............f.f.",
    55: "..............X.", 
    36: "X...X...X...X...",
}
make_bars(31, 1, fill_4)

# 32-37: Latin/Afro-Cuban Groove (Building tension)
latin_groove = {
    56: "X...x.x.X...x.x.X...x.x.X...x.x.", # Cowbell
    62: "..x.......x.......x.......x.....", # High Conga
    64: "......x.......x.......x.......x.", # Low Conga
    36: "X.......X.......X.......X.......",
    44: "....X.......X.......X.......X...",
    37: "....X..g....X..g....X..g....X..g",
}
make_bars(32, 5, latin_groove)

# 37-38: Latin Fill (Open snare roll interrupting)
latin_fill = {
    56: "X...x.x.X.......",
    62: "..x.......x.....",
    64: "......x.........",
    36: "X.......X.......",
    44: "....X.......X...",
    38: "............OOOO",
}
make_bars(37, 1, latin_fill)

# 38-40: Linear Stadium Build Up
add_pattern(38*4, 4.0, 49, "X") # Initial crash
add_pattern(39*4, 4.0, 57, "X") # Alternating crash
make_build(38, 2, 38, 0.25, 40, 127) # Snare crescendo
make_build(38, 2, 36, 0.25, 60, 127) # Kick crescendo
make_build(38, 2, 43, 0.25, 60, 127) # Floor tom crescendo

# 40-47: Climax Groove (Washing cymbals and double kick gallop)
climax_groove = {
    49: "X.......X.......X.......X.......", # Crash 1
    57: "....X.......X.......X.......X...", # Crash 2 alternating
    38: "....X.......X.......X.......X...",
    36: "X.xxX.xxX.xxX.xxX.xxX.xxX.X.X.X.", # 16th double kick gallop
}
make_bars(40, 7, climax_groove)

# 47-48: Triplet Fill (Massive tumbling sextuplets around the kit)
make_triplet_fill(47)

# 48-54: Outro Groove (Return to original motif for release)
outro_groove = {
    36: "X.......X.......X.......X.......",
    43: "..X.......X.......X.......X.....",
    37: "....X.......X.......X.......x.x.",
    44: "X.......X.......X.......X.......",
}
make_bars(48, 6, outro_groove)

# 54-55: Sparse Outro
outro_sparse = {
    36: "X...............X...............",
    43: "..x...............x.............",
    37: "....X...............X...........",
    44: "X.......X.......X.......X.......",
}
make_bars(54, 1, outro_sparse)

# 55-56: Final Swell
make_build(55, 1, 49, 0.125, 20, 110)
make_build(55, 1, 43, 0.125, 30, 90)

# 56: Final Crash
events.append((56 * 4, 49, 110))
events.append((56 * 4, 57, 110))
events.append((56 * 4, 36, 110))


# --- POST-PROCESSING ---

FOOT_PITCHES = {36, 44}

def enforce_playability(evs):
    """Ensure the solo is playable by one drummer (max 2 hands, 2 feet)."""
    grouped = defaultdict(list)
    for e in evs:
        t = round(e[0], 3)
        grouped[t].append(e)
    
    playable = []
    for t in sorted(grouped.keys()):
        hits = grouped[t]
        hits.sort(key=lambda x: x[2], reverse=True)
        
        hands = 0
        feet = 0
        used_pitches = set()
        
        for e in hits:
            pitch = e[1]
            if pitch in used_pitches:
                continue
                
            if pitch in FOOT_PITCHES:
                if feet < 2:
                    feet += 1
                    used_pitches.add(pitch)
                    playable.append(e)
            else:
                if hands < 2:
                    hands += 1
                    used_pitches.add(pitch)
                    playable.append(e)
    return playable

def apply_swing(beat, amount=0.025):
    """Pushes the 2nd and 4th 16th notes to give a natural funk swing."""
    frac = beat % 0.5
    if 0.15 < frac < 0.35: 
        return beat + amount
    return beat

def humanize(evs):
    """Adds swing, consistent micro-timing jitter, and velocity fluctuations."""
    random.seed(42)  # Fixed seed to ensure exact deterministic output every run
    humanized = []
    for beat, pitch, vel in evs:
        b = apply_swing(beat, 0.025)
        b += random.uniform(-0.005, 0.005)
        b = max(0.0, b)
        v = vel + random.randint(-5, 5)
        v = max(1, min(127, int(v)))
        humanized.append((b, pitch, v))
    return humanized

playable_events = enforce_playability(events)
final_events = humanize(playable_events)


# --- MIDI EXPORT ---

mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
track = mido.MidiTrack()
mid.tracks.append(track)

tempo = mido.bpm2tempo(BPM)
track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))

midi_events = []
for beat, pitch, vel in final_events:
    abs_tick = int(round(beat * TICKS_PER_BEAT))
    midi_events.append((abs_tick, 'note_on', pitch, vel))
    midi_events.append((abs_tick + 10, 'note_off', pitch, 0)) # Very short duration

midi_events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

last_tick = 0
for abs_tick, msg_type, pitch, vel in midi_events:
    delta = abs_tick - last_tick
    if delta < 0: delta = 0
    track.append(mido.Message(msg_type, channel=9, note=pitch, velocity=vel, time=delta))
    last_tick = abs_tick

mid.save('solo.mid')
