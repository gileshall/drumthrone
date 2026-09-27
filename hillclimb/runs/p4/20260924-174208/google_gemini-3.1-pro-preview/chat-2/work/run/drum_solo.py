import mido
import random

# Ensure reproducible generation identical on every run
random.seed(42)

# General MIDI Drum Map
KICK = 36
SNARE = 38
RIM = 37
HAT_C = 42
HAT_P = 44
HAT_O = 46
RIDE = 51
RIDE_BELL = 53
CRASH1 = 49
CRASH2 = 57
SPLASH = 55
CHINA = 52
T1 = 50
T2 = 48
T3 = 45
T4 = 43

# Mapping string characters to notes and base velocities
char_to_note = {
    'K': (KICK, 110),
    'k': (KICK, 70),
    'S': (SNARE, 115),
    's': (SNARE, 45),
    'R': (RIM, 100),
    'r': (RIM, 50),
    'H': (HAT_C, 90),
    'h': (HAT_P, 70),
    'O': (HAT_O, 95),
    'd': (RIDE, 85),
    'D': (RIDE_BELL, 105),
    '1': (T1, 105),
    '2': (T2, 105),
    '3': (T3, 110),
    '4': (T4, 110),
    'C': (CRASH1, 115),
    'c': (CRASH2, 115),
    'p': (SPLASH, 100),
    'X': (CHINA, 110),
}

# Categorize instruments for playability constraint (2 hands, 2 feet max)
hands = {SNARE, RIM, HAT_C, HAT_O, RIDE, RIDE_BELL, CRASH1, CRASH2, SPLASH, CHINA, T1, T2, T3, T4}
feet = {KICK, HAT_P}

def parse_layer(layer_str, start_beat, beats_per_char=0.25):
    """Parses a drum notation string into hits. Allows bracketed chords e.g. [CK]."""
    hits = []
    layer_str = layer_str.replace(" ", "").replace("|", "")
    beat = start_beat
    i = 0
    while i < len(layer_str):
        char = layer_str[i]
        if char == '[':
            i += 1
            chord_chars = []
            while layer_str[i] != ']':
                chord_chars.append(layer_str[i])
                i += 1
            for c in chord_chars:
                if c in char_to_note:
                    n, v = char_to_note[c]
                    v = max(1, min(127, int(v * random.uniform(0.9, 1.1))))
                    hits.append({'b': beat, 'n': n, 'v': v})
            beat += beats_per_char
        else:
            if char in char_to_note:
                n, v = char_to_note[char]
                v = max(1, min(127, int(v * random.uniform(0.9, 1.1))))
                hits.append({'b': beat, 'n': n, 'v': v})
            beat += beats_per_char
        i += 1
    return hits, beat

def make_roll(start_beat, duration, note, start_vel, end_vel, note_value=0.125):
    """Creates a roll (crescendo/decrescendo) with realistic accentuation."""
    hits = []
    num_hits = int(duration / note_value)
    for i in range(num_hits):
        v = start_vel + (end_vel - start_vel) * i / max(1, num_hits - 1)
        if i % 2 == 1:
            v *= 0.85 # Accent odd strokes slightly less for sticking realism
        v = max(1, min(127, int(v + random.randint(-3, 3))))
        hits.append({'b': start_beat + i * note_value, 'n': note, 'v': v})
    return hits

def generate_linear_chops(start_beat, num_beats, bpc=0.16666666666666666):
    """Generates continuous linear combinations moving organically around the kit."""
    hits = []
    beat = start_beat
    end_beat = start_beat + num_beats
    patterns = [
        ['R', 'L', 'K'],
        ['R', 'L', 'R', 'K'],
        ['R', 'L', 'K', 'K'],
        ['K', 'R', 'L'],
        ['R', 'L', 'R', 'L', 'K', 'K']
    ]
    while beat < end_beat - 0.01:
        pat = random.choice(patterns)
        r_drum = random.choice(['S', '1', '2', '3', '4'])
        l_drum = random.choice(['s', 's', 'S', '2', '3']) # Left hand often plays ghosts
        for stroke in pat:
            if beat >= end_beat - 0.01:
                break
            if stroke == 'R':
                hits.extend(parse_layer(r_drum, beat, bpc)[0])
            elif stroke == 'L':
                hits.extend(parse_layer(l_drum, beat, bpc)[0])
            elif stroke == 'K':
                hits.extend(parse_layer('K', beat, bpc)[0])
            beat += bpc
    return hits

all_hits = []
def add_hits(new_hits):
    all_hits.extend(new_hits)

current_beat = 0.0

# ---------------------------------------------------------
# COMPOSITION (Total 2 Minutes = 240 Beats at 120 BPM)
# ---------------------------------------------------------

# Section 1: Intro (32 Beats) - Tribal tom build up and establishing motif
for i in range(8):
    b = i * 4
    if i % 4 == 3:
        if i == 3:
            add_hits(parse_layer("[C1K] . s s [3K] . s . 1 1 2 2 3 3 4 4", b, 0.25)[0])
        else:
            add_hits(parse_layer("[C1K] . s . 1 1 2 2 3 3 4 4 S S S S", b, 0.25)[0])
    else:
        add_hits(parse_layer("[1K] . s s [3K] . s s [4K] s s s [2K] . s s", b, 0.25)[0])
        add_hits(parse_layer("h . . . h . . . h . . . h . . .", b, 0.25)[0])
current_beat += 32

# Section 2: Groove A (48 Beats) - Syncopated funk groove with hi-hat variations
for i in range(12):
    b = current_beat + i * 4
    if i % 4 == 3:
        add_hits(parse_layer("[cK] s H s [SH] s [kH] s", b, 0.25)[0])
        add_hits(parse_layer(". . . . h . . .", b, 0.25)[0])
        if i == 3:
            add_hits(parse_layer("S S 1 1 2 2 3 3", b + 2, 0.25)[0])
        elif i == 7:
            add_hits(parse_layer("S S S 1 1 1 2 2 2 3 3 3", b + 2, 1/6)[0]) # Triplet fill
            add_hits(parse_layer("K . . K . . K . . K . .", b + 2, 1/6)[0])
        elif i == 11:
            fill_str = "S S 1 K 1 1 2 K 2 2 3 3 K K K K"
            add_hits(parse_layer(fill_str, b + 2, 0.125)[0])
    else:
        var = i % 4
        if var == 0:
            hands_str = "[cK] s H s [SH] s [kH] s k s H s [SH] s k s"
        elif var == 1:
            hands_str = "[HK] s H s [SH] s [kH] s k [sH] s [kH] [SH] s k s"
        elif var == 2:
            hands_str = "[HK] s H s [SH] s [kH] s k s [HK] O [SH] s [kH] s" # Open hat choke
        add_hits(parse_layer(hands_str, b, 0.25)[0])
        add_hits(parse_layer(". . . . h . . . . . . . h . . .", b, 0.25)[0])
current_beat += 48

# Section 3: Groove B (48 Beats) - Ride cymbal development, tension building
for i in range(12):
    b = current_beat + i * 4
    if i % 4 == 3:
        add_hits(parse_layer("[DK] d d d [Sd] d d d", b, 0.25)[0])
        add_hits(parse_layer(". . . . h . . .", b, 0.25)[0])
        if i == 3:
            add_hits(parse_layer("S s s S s s S s s S s s", b + 2, 1/6)[0])
        elif i == 7:
            add_hits(parse_layer("S s s 1 s s 2 s s 3 s s", b + 2, 1/6)[0])
        elif i == 11:
            add_hits(make_roll(b + 2, 2, SNARE, 40, 120, 0.125)) # Heavy snare build
            add_hits(make_roll(b + 2, 2, KICK, 80, 110, 0.25))
    else:
        var = i % 4
        if var == 0:
            hands_str = "[DK] d s d [Sd] d [kd] d [kD] d s d [Sd] d k d"
        elif var == 1:
            hands_str = "[DK] d s d [Sd] d [kd] d k [dD] s [kd] [Sd] d k d"
        elif var == 2:
            hands_str = "[dK] d s d [Sd] d [kd] d [kD] s [Dd] s [Sd] d [kd] s"
        add_hits(parse_layer(hands_str, b, 0.25)[0])
        add_hits(parse_layer(". . . . h . . . . . . . h . . .", b, 0.25)[0])
current_beat += 48

# Section 4: Dynamic Drop (32 Beats) - Fast linear ghosts, low dynamics
for i in range(8):
    b = current_beat + i * 4
    if i % 4 == 3:
        if i == 3:
            add_hits(generate_linear_chops(b, 4, 1/6))
        else:
            add_hits(generate_linear_chops(b, 4, 0.125))
    else:
        add_hits(parse_layer("h . . . h . . . h . . . h . . .", b, 0.25)[0])
        add_hits(parse_layer("[pK] s k s s k [Hs] s k [sH] k s s k s s", b, 0.25)[0])
current_beat += 32

# Section 5: Swell (16 Beats) - Huge orchestrated crescendo up the kit
for i in range(4):
    b = current_beat + i * 4
    add_hits(make_roll(b, 4, KICK, 70 + i*10, 80 + i*10, 0.25))
    if i == 0:
        add_hits(make_roll(b, 4, SNARE, 40, 60, 0.125))
    elif i == 1:
        add_hits(make_roll(b, 4, T1, 60, 80, 0.125))
    elif i == 2:
        add_hits(make_roll(b, 4, T2, 80, 100, 0.125))
    elif i == 3:
        add_hits(make_roll(b, 2, T3, 100, 115, 0.125))
        add_hits(make_roll(b+2, 2, T4, 115, 127, 0.125))
current_beat += 16

# Section 6: Climax (48 Beats) - Heavy double bass, explosive crashes and fast runs
for i in range(12):
    b = current_beat + i * 4
    if i % 4 == 3:
        add_hits(make_roll(b, 1, SNARE, 110, 127, 0.125))
        add_hits(make_roll(b+1, 1, T1, 110, 127, 0.125))
        add_hits(make_roll(b+2, 1, T2, 110, 127, 0.125))
        add_hits(make_roll(b+3, 1, T4, 110, 127, 0.125))
        add_hits(parse_layer("K . . . K . . . K . . . K . . .", b, 0.25)[0])
    else:
        add_hits(parse_layer("K K K K K K K K K K K K K K K K", b, 0.25)[0]) # Double bass
        var = i % 4
        if var == 0:
            add_hits(parse_layer("C . . . S . . . c . . . S . . .", b, 0.25)[0])
        elif var == 1:
            add_hits(parse_layer("X . c . S . . . X . c . S . . .", b, 0.25)[0])
        elif var == 2:
            add_hits(parse_layer("C . p . S . [1X] . [2c] . . . S . . .", b, 0.25)[0])
current_beat += 48

# Section 7: Outro (16 Beats) - Polyrhythmic syncopation resolving to big finish
for i in range(4):
    b = current_beat + i * 4
    if i == 0:
        add_hits(parse_layer("[CK] . . [CK] . . [CK] . . [cK] . . [cK] . . .", b, 0.25)[0]) # Dotted 8ths pattern
        add_hits(parse_layer(". . S . . S . . S . . S . . S .", b, 0.25)[0])
    elif i == 1:
        add_hits(parse_layer("[CK] . . [CK] . . [CK] . . [cK] . . [cK] . . .", b, 0.25)[0])
        add_hits(parse_layer(". . 1 . . 2 . . 3 . . 4 . . S .", b, 0.25)[0])
    elif i == 2:
        add_hits(generate_linear_chops(b, 4, 1/6))
    elif i == 3:
        add_hits(make_roll(b, 3.5, SNARE, 100, 127, 0.125))
        add_hits(make_roll(b, 3.5, KICK, 100, 127, 0.25))
        # Land the final hit!
        add_hits([
            {'b': 240.0, 'n': CRASH1, 'v': 127}, 
            {'b': 240.0, 'n': CRASH2, 'v': 127}, 
            {'b': 240.0, 'n': KICK, 'v': 127}, 
            {'b': 240.0, 'n': SNARE, 'v': 127}
        ])
current_beat += 16

# ---------------------------------------------------------
# HUMANIZATION (Swing and Breathing Tempo)
# ---------------------------------------------------------
time_map = [0.0] * 24001
current_warped = 0.0

def get_tempo(b):
    """Time-warp multiplier to simulate humans leaning forward and settling back."""
    if b < 32: return 1.0 + (b / 32.0) * 0.02           # Build up
    elif b < 80: return 1.02                            # Groove steady forward
    elif b < 128: return 1.02 + ((b - 80) / 48.0)*0.03  # Push forward
    elif b < 160: return 1.05 - ((b - 128) / 32.0)*0.07 # Relax into ghost notes
    elif b < 224: return 0.98 + ((b - 160) / 64.0)*0.10 # Hard push through climax
    else: return 1.08 - ((b - 224) / 16.0) * 0.08       # Settle down to finish

# Precompute time mapping array (numerical integration)
for i in range(1, 24001):
    beat_time = i / 100.0
    dt = 0.01 / get_tempo(beat_time)
    current_warped += dt
    time_map[i] = current_warped

def get_warped_beat(b):
    if b < 0: return 0.0
    if b >= 240:
        extra = b - 240
        return time_map[24000] + extra / get_tempo(240)
    idx = int(b * 100)
    frac = (b * 100) - idx
    if idx < 24000:
        return time_map[idx] + frac * (time_map[idx+1] - time_map[idx])
    return time_map[idx]

for hit in all_hits:
    b = hit['b']
    # Add slight swing to 16th notes only
    sixteenth_pos = b % 0.25
    if abs(sixteenth_pos) < 0.01 or abs(sixteenth_pos - 0.25) < 0.01:
        if abs((b % 0.5) - 0.25) < 0.01:
            b += 0.025 # Delay off-beats

    bw = get_warped_beat(b)
    hit['bw'] = bw

# ---------------------------------------------------------
# PHYSICAL PLAYABILITY & MIDI EVENT GENERATION
# ---------------------------------------------------------
def sanitize_hits(hits):
    """Ensure a maximum of two hands and two feet per moment, avoiding impossibilities."""
    from collections import defaultdict
    groups = defaultdict(list)
    for hit in hits:
        t_key = round(hit['bw'] * 200) # Group notes within ~5ms
        groups[t_key].append(hit)
        
    sanitized = []
    for t_key in sorted(groups.keys()):
        group = groups[t_key]
        group.sort(key=lambda x: x['v'], reverse=True) # Prioritize accents if dropping notes
        h_count = 0
        f_count = 0
        seen_notes = set()
        for hit in group:
            n = hit['n']
            if n in seen_notes:
                continue # Never duplicate identical hits in the same instant
            if n in hands:
                if h_count < 2:
                    sanitized.append(hit)
                    h_count += 1
                    seen_notes.add(n)
            elif n in feet:
                if f_count < 2:
                    sanitized.append(hit)
                    f_count += 1
                    seen_notes.add(n)
            else:
                sanitized.append(hit)
                seen_notes.add(n)
    return sanitized

final_hits = sanitize_hits(all_hits)
final_hits.sort(key=lambda x: x['bw'])

events = []
for hit in final_hits:
    abs_tick = int(round(hit['bw'] * 480))
    events.append({'type': 'on', 'tick': abs_tick, 'note': hit['n'], 'vel': hit['v']})
    events.append({'type': 'off', 'tick': abs_tick + 60, 'note': hit['n'], 'vel': 0}) # ~1/32nd beat dur

# Note Offs must process exactly before Note Ons if landing on identical tick to avoid choked polyphony
events.sort(key=lambda x: (x['tick'], 0 if x['type'] == 'off' else 1))

mid = mido.MidiFile(ticks_per_beat=480)
track = mido.MidiTrack()
mid.tracks.append(track)

track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
track.append(mido.Message('program_change', program=0, channel=9, time=0)) # Kit 0

last_tick = 0
for ev in events:
    delta = ev['tick'] - last_tick
    if delta < 0: 
        delta = 0
    if ev['type'] == 'on':
        track.append(mido.Message('note_on', note=ev['note'], velocity=ev['vel'], time=delta, channel=9))
    else:
        track.append(mido.Message('note_off', note=ev['note'], velocity=0, time=delta, channel=9))
    last_tick += delta

mid.save('solo.mid')
