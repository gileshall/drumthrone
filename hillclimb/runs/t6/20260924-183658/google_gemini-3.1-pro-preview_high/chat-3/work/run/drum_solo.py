import mido
import random

# Ensure identical output on every run
random.seed(1337)

# General MIDI Drum Map Constants
KICK = 36
SNARE = 38
HH_CLOSED = 42
HH_PEDAL = 44
HH_OPEN = 46
TOM_HI = 50
TOM_MID_HI = 48
TOM_MID_LOW = 47
TOM_LOW = 45
TOM_FLOOR = 43
TOM_LOW_FLOOR = 41
RIDE = 51
RIDE_BELL = 53
CRASH_1 = 49
CRASH_2 = 57
SPLASH = 55
CHINA = 52

# Global State
current_beat = 0.0
all_hits = []
TICKS_PER_BEAT = 480

def parse_pattern(pattern_str):
    """Parses a pattern string into a list of steps. Bracketed notes happen simultaneously."""
    steps = []
    in_bracket = False
    current_step = []
    for char in pattern_str:
        if char == '[':
            in_bracket = True
        elif char == ']':
            in_bracket = False
            if current_step:
                steps.append(current_step)
            current_step = []
        elif char in ' |':
            continue
        else:
            if in_bracket:
                current_step.append(char)
            else:
                steps.append([char])
    return steps

def add_crash(pat):
    """Intelligently adds a crash to the downbeat of a pattern string."""
    steps = parse_pattern(pat)
    if steps:
        first = steps[0]
        if first != ['-'] and not any(c.upper() == 'C' for c in first):
            first.append('C')
    out = []
    for s in steps:
        if s == ['-']: out.append('-')
        elif len(s) == 1: out.append(s[0])
        else: out.append('[' + "".join(s) + ']')
    return " ".join(out)

def generate_hits(start_beat, pattern, step_dur, r_seq, l_seq, k_seq, c_seq, v_base, v_var, cresc, swing):
    """Generates playable MIDI drum hits from a parsed sticking pattern."""
    hits = []
    steps = parse_pattern(pattern)
    r_i, l_i, k_i, c_i = 0, 0, 0, 0
    
    for i, step in enumerate(steps):
        beat = start_beat + i * step_dur
        # Apply slight swing to offbeats (indices 1, 3, 5...)
        if i % 2 == 1:
            beat += swing * step_dur
            
        # Base velocity for this specific step (handling crescendos)
        v = v_base + cresc * (i / max(1, len(steps)-1))
        
        for char in step:
            if char == '-': continue
            
            is_accent = char.isupper()
            c_low = char.lower()
            
            # Dynamic shaping for accents and ghost notes
            if is_accent:
                vel = min(127, int(v * 1.3))
            else:
                vel = min(127, int(v * 0.65))
            
            # Humanize velocity
            vel = min(127, max(1, vel + random.randint(-v_var, v_var)))
            
            drum = None
            if c_low == 'r':
                if r_seq: drum = r_seq[r_i % len(r_seq)]
                r_i += 1
            elif c_low == 'l':
                if l_seq: drum = l_seq[l_i % len(l_seq)]
                l_i += 1
            elif c_low == 'k':
                if k_seq: drum = k_seq[k_i % len(k_seq)]
                k_i += 1
            elif c_low == 'c':
                if c_seq: drum = c_seq[c_i % len(c_seq)]
                c_i += 1
            elif c_low == 'h': drum = HH_PEDAL
            elif c_low == 'o': drum = HH_OPEN
            elif c_low == 'x': drum = HH_CLOSED
            elif c_low == 's': drum = SNARE
            elif c_low == 'b': drum = RIDE_BELL
                
            if drum:
                # Humanize timing (simulate a human playing slightly off grid)
                human_beat = beat + random.gauss(0, 0.015)
                hits.append((human_beat, drum, vel))
                
    return hits, len(steps)

def add(pat, dur, r, l, k, c, v, v_var, cresc, swing=0.0):
    """Appends a generated pattern to the global timeline."""
    global current_beat, all_hits
    hits, steps_count = generate_hits(current_beat, pat, dur, r, l, k, c, v, v_var, cresc, swing)
    all_hits.extend(hits)
    current_beat += steps_count * dur

def play_groove(measures, grooves, fills, r_seq, l_seq, k_seq, c_seq, v, v_var, swing):
    """Plays a specified number of measures, choosing grooves and ending phrases with fills."""
    for m in range(measures):
        is_last = (m == measures - 1)
        is_fill = (m % 4 == 3) # Fills every 4th measure
        
        if is_last or is_fill:
            pat = random.choice(fills)
            # Fills move around the toms dynamically
            add(pat, 0.25, toms_down, toms_down, k_seq, c_seq, v+15, v_var, 10, swing)
        else:
            pat = random.choice(grooves)
            if m % 4 == 0:
                pat = add_crash(pat)
            add(pat, 0.25, r_seq, l_seq, k_seq, c_seq, v, v_var, 0, swing)

# --- Drum Sequences for moving around the kit ---
toms_down = [TOM_HI, TOM_HI, TOM_MID_HI, TOM_MID_HI, TOM_LOW, TOM_LOW, TOM_FLOOR, TOM_FLOOR]
toms_up = [TOM_FLOOR, TOM_FLOOR, TOM_LOW, TOM_LOW, TOM_MID_HI, TOM_MID_HI, TOM_HI, TOM_HI]
toms_rand = [TOM_HI, TOM_MID_HI, TOM_LOW, TOM_FLOOR, SNARE, TOM_HI]

# ==============================================================================
# STRUCTURE THE 2-MINUTE DRUM SOLO
# ==============================================================================

# Section 1: The Walk-In (Measures 1-4)
intro_grooves = [
    "r - h - r - h - R - h - r l h -",
    "r - h - r - h - R - h l r - h -",
    "r - h - r - h - R - h - r - h l",
    "r - h - r - h - R - h - r l h l"
]
play_groove(4, intro_grooves, intro_grooves, [RIDE], [SNARE], [KICK], [CRASH_1], 50, 5, 0.05)

# Section 2: Building the Ride Groove (Measures 5-12)
ride_grooves_1 = [
    "[RK] - r l [RLh] l r l [RK] - r l [RLh] l r l",
    "[RK] l r k [RLh] l r l k [RK] r l [RLh] l r l",
    "[RK] - r l [RLh] l r l r k [RK] l [RLh] l r l",
    "[RK] - r l [RLh] k r l [RK] - r k [RLh] l r l",
]
ride_fills = [
    "R L R L R L R L R L R L R L R L",
    "[RK] l r l R L R L R L K K R L R L",
    "R L K R L K R L R L K K R L R L",
    "R - R - R L R L R - R - R L R L"
]
play_groove(8, ride_grooves_1, ride_fills, [RIDE], [SNARE], [KICK], [CRASH_1], 65, 8, 0.04)

# Section 3: Hi-Hat Funk Syncopation (Measures 13-20)
hh_grooves = [
    "[xK] l x l [XL] l x l [xK] l x l [XL] l x l",
    "[xK] l x k [XL] l x l k [xK] x l [XL] l x l",
    "[xK] l x l [XL] l [xK] l x l x k [XL] l x l",
    "[xK] x x k [XL] l x l [xK] l x l [XL] k x l",
    "[xK] l O l [XL] l x l [xK] l O l [XL] l x l",
]
hh_fills = [
    "R L R L K K R L R L K K R L R L",
    "R L R L R L K K R L R L R L K K",
    "R L K K R L K K R L R L R L R L",
    "[CK] l r l [CK] l r l R L R L R L R L"
]
play_groove(8, hh_grooves, hh_fills, [HH_CLOSED], [SNARE], [KICK], [CRASH_2, SPLASH], 75, 10, 0.06)

# Section 4: Tribal Floor Toms (Measures 21-28)
tribal_grooves = [
    "[RK] l r l R l r l [RK] l r l R l r l",
    "[RK] l R l [RK] l R l [RK] l R l R l R l",
    "[RK] l r k R l r l [RK] k r l R l r l",
    "[RK] L R L [RK] L R L [RK] L R L [RK] L R L",
]
tribal_fills = [
    "R L R L R L R L R L R L R L R L",
    "R L R L R L R L K K K K R L R L",
    "R L R L K K K K R L R L K K K K",
    "[RK] L R L [RK] L R L R L R L R L R L"
]
play_groove(8, tribal_grooves, tribal_fills, [TOM_LOW_FLOOR, TOM_FLOOR], [SNARE, TOM_HI], [KICK], [CRASH_1], 85, 12, 0.0)

# Section 5: Linear Triplet Show-Off (Measures 29-32)
triplet_fills = [
    "R L K R L K R L K R L K R L K R L K R L K R L K",
    "R L R L K K R L R L K K R L R L K K R L R L K K",
    "R L R L R L R L R L R L R L R L R L R L R L R L",
    "[CK] - - [CK] - - [CK] - - [CK] - - [CK] - - [CK] - - [CK] - - [CK] - -",
]
for i in range(4):
    pat = triplet_fills[i]
    # 24 strokes spanning 4 beats = 16th note triplets
    add(pat, 4.0/24.0, toms_rand, toms_rand, [KICK], [CRASH_1, CRASH_2], 90, 10, 5, 0.0)

# Section 6: Driving Ride Bell Climax (Measures 33-40)
climax_grooves = [
    "[bK] l b l [BL] l b l [bK] l b l [BL] l b l",
    "[bK] k b l [BL] l b l [bK] k b l [BL] k b l",
    "[CK] l x l [XL] l x l [CK] l x l [XL] l x l",
    "[bK] l b l [BL] k b l [bK] l b k [BL] l b l",
]
climax_fills = [
    "R L R L R L R L R L R L R L R L R L R L R L R L R L R L R L R L ", # 32nd note snare/tom sweep
    "R L R L K K K K R L R L K K K K R L R L K K K K R L R L K K K K ",
    "R L K K R L K K R L K K R L K K R L K K R L K K R L K K R L K K ",
]
for m in range(8):
    if m % 4 == 3:
        pat = random.choice(climax_fills)
        add(pat, 0.125, toms_down, toms_down, [KICK], [CRASH_1, CRASH_2], 100, 12, 10, 0.0)
    else:
        pat = random.choice(climax_grooves)
        if m % 4 == 0: pat = add_crash(pat)
        add(pat, 0.25, [RIDE_BELL], [SNARE], [KICK], [CRASH_1], 95, 12, 0, 0.0)

# Section 7: The Breakdown Snare Roll (Measures 41-48)
breakdown_pats = [
    "r l r l r l r l r l r l r l r l", # M41 piano
    "r l r l r l r l r l r l r l r l", # M42
    "R l r l R l r l R l r l R l r l", # M43 introducing accents
    "R l r l R l r l R l r l R l r l", # M44
    "R l R l R l R l R l R l R l R l", # M45
    "R l R l R l R l R l k k R l k k", # M46 adding kicks
]
for i, pat in enumerate(breakdown_pats):
    v = 30 + (i/6) * 75 # Massive crescendo from ghost notes to cracking accents
    add(pat, 0.25, [SNARE], [SNARE], [KICK], [CRASH_1], int(v), 5, 10, 0.0)
    
roll_32 = "R L R L R L R L R L R L R L R L R L R L R L R L R L R L R L R L "
add(roll_32, 0.125, [SNARE], [SNARE], [KICK], [CRASH_1], 105, 10, 10, 0.0) # M47
add(roll_32, 0.125, toms_down, toms_up, [KICK], [CRASH_1], 115, 10, 10, 0.0) # M48

# Section 8: Heavy Double-Kick Finale (Measures 49-56)
heavy_grooves = [
    "[CK] K K K L K K K [CK] K K K L K K K",
    "[CK] K [CK] K L K K K [CK] K K K L K K K",
    "[CK] K K K L K K K [CK] K [CK] K L K K K",
    "[CK] l r l [CK] l r l [CK] l r l [CK] l r l",
]
for m in range(8):
    pat = random.choice(heavy_grooves)
    add(pat, 0.25, [TOM_HI, TOM_MID_HI, TOM_LOW, TOM_FLOOR], [SNARE], [KICK], [CRASH_1, CRASH_2, CHINA], 115, 8, 0, 0.0)

# Section 9: The Climax Fills (Measures 57-60)
final_fills = [
    "R L R L K K K K R L R L K K K K",
    "R L K K R L K K R L K K R L K K",
    "R L R L R L R L R L R L R L R L",
    "[CK] - - - - - - - [CK] - - - - - - - "
]
for i in range(4):
    pat = final_fills[i]
    add(pat, 0.25, toms_rand, toms_rand, [KICK], [CRASH_1, CRASH_2, CHINA], 120, 5, 0, 0.0)

# Section 10: The Big Ending Hits (Measures 61-64)
add("[CK] - [CK] - [CK] - [CK] - [CK] - - - - - - -", 0.25, [SNARE], [SNARE], [KICK], [CRASH_1, CHINA], 127, 0, 0, 0.0)
add("- - - - - - - - - - - - - - - -", 0.25, [SNARE], [SNARE], [KICK], [CRASH_1], 0, 0, 0, 0.0)
add("[CK] l r l R L R L K K K K K K K K", 0.25, toms_down, toms_up, [KICK], [CRASH_1, CRASH_2], 127, 0, 0, 0.0)
add("[CK] - - - - - - - - - - - - - - -", 0.25, [SNARE], [SNARE], [KICK], [CRASH_1, CRASH_2], 127, 0, 0, 0.0) # Final ringing hit

# ==============================================================================
# MIDI GENERATION
# ==============================================================================

mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
track = mido.MidiTrack()
mid.tracks.append(track)

# 125 BPM places the 256 beats perfectly at ~2:02 duration
tempo = int(60_000_000 / 125)
track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))

# Prepare absolute ticks and pair note_on and note_off
events = []
for beat_time, note, vel in all_hits:
    abs_tick = int(beat_time * TICKS_PER_BEAT)
    events.append((abs_tick, 'note_on', note, vel))
    # Give drum notes a short 20-tick duration to strictly avoid overlapping MIDI note conflicts
    events.append((abs_tick + 20, 'note_off', note, 0))

# Sort chronologically. On tie, evaluate 'note_off' before 'note_on'
events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

# Write delta times to track (General MIDI Drum Channel is 9 in 0-indexed formats)
last_tick = 0
for abs_tick, msg_type, note, vel in events:
    delta = max(0, abs_tick - last_tick)
    if msg_type == 'note_on':
        track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
    else:
        track.append(mido.Message('note_off', channel=9, note=note, velocity=vel, time=delta))
    last_tick = max(last_tick, abs_tick)

mid.save('solo.mid')
