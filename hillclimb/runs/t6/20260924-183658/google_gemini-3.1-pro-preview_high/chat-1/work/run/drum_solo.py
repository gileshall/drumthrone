import mido
import math
import random

# Deterministic seed for reproducible solos
random.seed(42)

# --- General MIDI Drum Kit Mapping ---
KICK = 36
SNARE = 38
RIM = 37
TOM1 = 50
TOM2 = 48
TOM3 = 47
TOM4 = 45
TOM5 = 43
TOM6 = 41
HAT_C = 42
HAT_P = 44
HAT_O = 46
RIDE = 51
RIDE_BELL = 53
CRASH1 = 49
CRASH2 = 57
SPLASH = 55
CHINA = 52
COWBELL = 56

HAND_DRUMS = {SNARE, RIM, TOM1, TOM2, TOM3, TOM4, TOM5, TOM6, HAT_C, HAT_O, RIDE, RIDE_BELL, CRASH1, CRASH2, SPLASH, CHINA, COWBELL}
FOOT_DRUMS = {KICK, HAT_P}

hits = []

# --- Core Hit Generators ---
def h(beat, drum, vel):
    hits.append((beat, drum, vel))

def h_flam(beat, drum, vel):
    h(beat - 0.03, drum, max(1, int(vel * 0.4)))
    h(beat, drum, vel)

def h_drag(beat, drum, vel):
    h(beat - 0.06, drum, max(1, int(vel * 0.3)))
    h(beat - 0.03, drum, max(1, int(vel * 0.3)))
    h(beat, drum, vel)

def clear_hits(start_beat, end_beat):
    """Scoop out timeline space for a fill, allowing for timing jitter."""
    global hits
    hits = [hit for hit in hits if not (start_beat - 0.1 <= hit[0] < end_beat + 0.1)]

# --- Pattern Players ---
def play_sticking(start_beat, subdivision, pattern, drum_map, vel_normal=50, vel_accent=110):
    beat = start_beat
    for char in pattern:
        if char == ' ':
            continue
        if char.lower() in drum_map:
            drum = drum_map[char.lower()]
            vel = vel_accent if char.isupper() else vel_normal
            vel = max(1, min(127, int(vel + random.gauss(0, 4))))
            t = beat + random.gauss(0, 0.01)
            h(t, drum, vel)
        beat += subdivision
    return beat

def play_layer(start_beat, subdivision, pattern, drum, vel_normal, vel_accent):
    beat = start_beat
    for char in pattern:
        if char == ' ':
            continue
        if char.lower() == 'x':
            vel = vel_accent if char.isupper() else vel_normal
            vel = max(1, min(127, int(vel + random.gauss(0, 4))))
            t = beat + random.gauss(0, 0.01)
            h(t, drum, vel)
        beat += subdivision

def play_crash(beat, crash=CRASH1, kick=True):
    h(beat, crash, random.randint(110, 127))
    if kick:
        h(beat, KICK, random.randint(100, 127))

# --- Motif & Section Generators ---
def intro(start_bar):
    beat = start_bar * 4
    # Cymbal textures
    play_layer(beat, 1.0, "x . x . x . x .", RIDE, 30, 40)
    play_layer(beat+8, 1.0, "x . x . x . x .", SPLASH, 40, 50)
    
    # Sparse rudiments and exploration
    play_sticking(beat + 2, 0.125, "l r l r", {'l':SNARE, 'r':SNARE}, 20, 30)
    play_sticking(beat + 4.5, 0.125, "R l r l L", {'l':SNARE, 'r':SNARE, 'R':TOM1, 'L':TOM2}, 30, 60)
    h_drag(beat + 7, RIM, 80)
    h(beat + 7, KICK, 60)
    play_sticking(beat + 10, 1/6, "R l l R l l", {'l':SNARE, 'r':SNARE, 'R':TOM4}, 40, 70)
    h_flam(beat + 13, SNARE, 90)
    h(beat + 13, HAT_O, 80)
    h(beat + 13.5, HAT_P, 70)
    make_fill(beat + 14, 2, 'low')

def make_groove(start_bar, num_bars, style='funk', intensity=0.5):
    for i in range(num_bars):
        bar_beat = start_bar * 4 + i * 4
        if style == 'funk':
            # Evolving hi-hat intensity
            if intensity < 0.3:
                play_layer(bar_beat, 0.25, "X.x. X.x. X.x. X.x.", HAT_C, 40, 70)
            elif intensity < 0.7:
                play_layer(bar_beat, 0.25, "XxX. x.x. Xxx. x.x.", HAT_C, 45, 80)
            else:
                play_layer(bar_beat, 0.25, "Xxxx Xxxx Xxxx XxxX", HAT_O, 60, 95)
            
            s_acc = int(90 + intensity*30)
            play_layer(bar_beat, 0.25, ".... X... .... X...", SNARE, 35, s_acc)
            
            k_vel = int(80 + intensity*30)
            if i % 2 == 0:
                play_layer(bar_beat, 0.25, "X... ..X. ..X. ....", KICK, k_vel-10, k_vel)
            else:
                play_layer(bar_beat, 0.25, "X... ..X. X... .X..", KICK, k_vel-10, k_vel)
                
            if intensity > 0.4:
                play_layer(bar_beat, 0.25, "..x. .x.. .x.. .x..", SNARE, 25, 40)
                
        elif style == 'jazz':
            r_vel = int(70 + intensity*20)
            play_layer(bar_beat, 1/3, "X.. X.x X.. X.x", RIDE, r_vel-20, r_vel)
            play_layer(bar_beat, 1/3, "... X.. ... X..", HAT_P, 60, 70)
            comp_vel = int(40 + intensity*30)
            comp = "".join(random.choice([".", ".", ".", "x", "X"]) for _ in range(12))
            play_layer(bar_beat, 1/3, comp, SNARE, comp_vel-15, comp_vel)
            k_comp = "".join(random.choice([".", ".", ".", ".", "x"]) for _ in range(12))
            play_layer(bar_beat, 1/3, k_comp, KICK, comp_vel-10, comp_vel+10)

        elif style == 'tribal':
            t_vel = int(80 + intensity*30)
            play_layer(bar_beat, 0.25, "X.xx X.xx X.X. X.xx", TOM6, t_vel-20, t_vel)
            play_layer(bar_beat, 0.25, ".... .... .X.. ....", TOM4, t_vel-10, t_vel)
            play_layer(bar_beat, 0.25, "X... X... X... X...", KICK, t_vel, t_vel+10)
            if intensity > 0.6:
                play_layer(bar_beat, 0.25, "..x. ..x. .... ..x.", SNARE, 60, 80)
            
        elif style == 'halftime':
            h_vel = int(80 + intensity*30)
            play_layer(bar_beat, 0.25, "X.x. X.x. X.x. X.x.", RIDE_BELL, h_vel-10, h_vel+10)
            play_layer(bar_beat, 0.25, ".... .... X... ....", SNARE, 110, 127)
            play_layer(bar_beat, 0.25, "X..X .X.. .... .XX.", KICK, 100, 120)
            play_layer(bar_beat, 0.25, ".... .... .x.x x...", SNARE, 30, 50)
            if i % 4 == 0:
                h(bar_beat, CRASH1, 110)

def make_fill(start_beat, num_beats, density='medium'):
    beat = start_beat
    if density == 'low': subs = [0.5, 0.25]
    elif density == 'medium': subs = [0.25, 1/6]
    elif density == 'high': subs = [0.25, 1/6, 0.125]
    else: subs = [1/6, 0.125, 1/8]
    
    for i in range(int(num_beats)):
        sub = random.choice(subs)
        notes_in_beat = int(round(1.0 / sub))
        
        if notes_in_beat == 4:
            pattern = random.choice(["R l R l", "R l r r", "R l l K", "K K R l", "R l K K", "R R L L"])
        elif notes_in_beat == 6:
            pattern = random.choice(["R l r l r l", "R l r r l l", "R l K R l K", "R l r l K K", "K R l r l r"])
        elif notes_in_beat == 8:
            pattern = random.choice(["R l r l R l r l", "R l r r L r l l", "R l r l K K K K"])
        elif notes_in_beat == 2:
            pattern = random.choice(["R l", "R K", "K R", "R ."])
        else:
            pattern = "R" * notes_in_beat
            
        d_map = {'k': KICK, 'K': KICK}
        main_drum = random.choice([SNARE, SNARE, TOM1, TOM2, TOM3, TOM4, TOM6])
        sec_drum = random.choice([SNARE, TOM2, TOM4, TOM6])
        d_map['r'] = main_drum
        d_map['R'] = main_drum
        d_map['l'] = sec_drum
        d_map['L'] = sec_drum
        
        vel_acc = random.randint(90, 120)
        vel_norm = random.randint(50, 80)
        
        # Crescendo towards end of big fills
        if i >= int(num_beats) - 2:
            vel_acc = 127
            vel_norm = 90
            
        play_sticking(beat, sub, pattern, d_map, vel_norm, vel_acc)
        beat += 1.0

def snare_roll(start_beat, num_beats, start_vel, end_vel):
    beat = start_beat
    sub = 0.125
    steps = int(num_beats / sub)
    for i in range(steps):
        progress = i / steps
        v = start_vel + (end_vel - start_vel) * progress
        if i % 8 == 0: v += 20
        v = max(1, min(127, int(v + random.gauss(0, 5))))
        t = beat + random.gauss(0, 0.01)
        h(t, SNARE, v)
        beat += sub

def tom_roll(start_beat, num_beats, start_vel, end_vel):
    beat = start_beat
    sub = 0.125
    steps = int(num_beats / sub)
    drums = [TOM1, TOM2, TOM3, TOM4, TOM6]
    for i in range(steps):
        progress = i / steps
        vel = start_vel + (end_vel - start_vel) * progress
        drum_idx = int(progress * len(drums))
        if drum_idx >= len(drums): drum_idx = len(drums)-1
        
        v = vel
        if i % 8 == 0: v += 20
        v = max(1, min(127, int(v + random.gauss(0, 5))))
        t = beat + random.gauss(0, 0.01)
        h(t, drums[drum_idx], v)
        beat += sub

def grand_finale(start_beat):
    beat = start_beat
    for i in range(4):
        if i == 0:
            play_sticking(beat, 0.125, "R l R l R l R l R l R l R l R l", {'R':SNARE, 'l':SNARE}, 90, 120)
            play_sticking(beat+2, 0.125, "R l R l R l R l R l R l R l R l", {'R':TOM1, 'l':TOM2}, 100, 127)
        elif i == 1:
            play_sticking(beat, 0.125, "R l R l R l R l", {'R':TOM3, 'l':TOM4}, 110, 127)
            play_sticking(beat+1, 0.125, "R l R l R l R l", {'R':TOM5, 'l':TOM6}, 110, 127)
            play_sticking(beat+2, 0.125, "K K R l K K R l K K R l K K R l", {'K':KICK, 'R':TOM6, 'l':TOM4}, 110, 127)
        elif i == 2:
            play_sticking(beat, 0.25, "R . L . R . L .", {'R':CRASH1, 'L':CRASH2}, 120, 127)
            play_sticking(beat, 0.25, "K . K . K . K .", {'K':KICK}, 120, 127)
            make_fill(beat+2, 2, 'insane')
        elif i == 3:
            snare_roll(beat, 3, 100, 127)
            play_layer(beat, 0.25, "x.x. x.x. xxxx", KICK, 100, 127)
        beat += 4

# --- Sequence Timeline (60 Bars / 240 Beats) ---

# Bar 1-4 (Beats 0-16): Spacey Intro
intro(0)

# Bar 5-8 (Beats 16-32): Low Funk
play_crash(16, CRASH1, True)
make_groove(4, 4, 'funk', 0.2)
clear_hits(30, 32)
make_fill(30, 2, 'medium')

# Bar 9-12 (Beats 32-48): Building Funk
play_crash(32, CRASH2, True)
make_groove(8, 4, 'funk', 0.5)
clear_hits(46, 48)
make_fill(46, 2, 'high')

# Bar 13-16 (Beats 48-64): Tribal Floor Toms
play_crash(48, CHINA, True)
make_groove(12, 4, 'tribal', 0.6)
clear_hits(62, 64)
make_fill(62, 2, 'medium')

# Bar 17-20 (Beats 64-80): Ride Jazz Swing
play_crash(64, RIDE, True)
make_groove(16, 4, 'jazz', 0.4)
clear_hits(78, 80)
play_sticking(78, 1/3, "R l K R l K R l K R l K", {'R':TOM1, 'l':SNARE, 'K':KICK}, 70, 110)

# Bar 21-24 (Beats 80-96): Heavy Halftime
play_crash(80, CRASH1, True)
make_groove(20, 4, 'halftime', 0.6)
clear_hits(94, 96)
make_fill(94, 2, 'high')

# Bar 25-28 (Beats 96-112): Syncopated Linear 16ths
play_crash(96, CRASH2, True)
for b in range(96, 112, 4):
    play_sticking(b, 0.25, "R l l K R l l K R l K R l K R l", {'R': HAT_C, 'l': SNARE, 'K': KICK}, 50, 90)
clear_hits(108, 112)
make_fill(108, 4, 'insane')

# Bar 29-32 (Beats 112-128): Snare/Tom Roll Build
play_crash(112, SPLASH, True)
snare_roll(112, 8, 30, 90)
for b in range(112, 120):
    if b % 2 == 0:
        h(b, KICK, int(60 + (b-112)*5))
tom_roll(120, 6, 90, 127)
make_fill(126, 2, 'insane')

# Bar 33-40 (Beats 128-160): Climax Double Kick / Long Fills
play_crash(128, CRASH1, True)
play_crash(128, CRASH2, True)
for b in range(128, 144, 2):
    play_layer(b, 0.25, "Xxxx Xxxx Xxxx Xxxx", KICK, 90, 110)
    play_layer(b, 1.0, "X X X X", CRASH1, 110, 120)
    play_layer(b+0.5, 1.0, "X X X X", CHINA, 110, 120)
    play_layer(b, 0.25, ".... X... .... X...", SNARE, 120, 127)

make_fill(144, 4, 'insane')
play_sticking(148, 0.25, "R l r l L r l r R l r l L r l r", {'R':HAT_C, 'L':HAT_O, 'r':SNARE, 'l':SNARE}, 30, 60)
tom_roll(152, 4, 60, 110)
make_fill(156, 4, 'insane')

# Bar 41-48 (Beats 160-192): Frantic Grooves
play_crash(160, CRASH1, True)
make_groove(40, 4, 'funk', 0.9)
clear_hits(174, 176)
make_fill(174, 2, 'high')

make_groove(44, 4, 'jazz', 0.9)
clear_hits(190, 192)
make_fill(190, 2, 'insane')

# Bar 49-54 (Beats 192-216): Accents and Silence
play_crash(192, CRASH2, True)
for b in range(192, 208, 4):
    play_sticking(b, 0.5, "K . K . . K . .", {'K':KICK}, 110, 127)
    play_sticking(b, 0.5, "R . L . . R . .", {'R':CRASH1, 'L':CRASH2}, 110, 127)
    play_sticking(b, 0.25, ". r . r r . l l", {'r':SNARE, 'l':SNARE}, 30, 40)
make_fill(208, 8, 'high')

# Bar 55-60 (Beats 216-240): The Grand Finale Flurry
grand_finale(216)

play_crash(232, CRASH1, True)
play_crash(232.5, CRASH2, True)
play_crash(233, SPLASH, True)
play_crash(234, CHINA, True)
h(234, KICK, 127)

make_fill(235, 4, 'insane')

# Land the final note
play_crash(239, CRASH1, True)
play_crash(239, CRASH2, True)
h(239, KICK, 127)
h(239, SNARE, 127)

# --- Post-Processing ---

def clean_duplicates(raw_hits):
    """Retains the loudest hit if the exact same drum is struck near-simultaneously."""
    raw_hits.sort(key=lambda x: (x[0], x[1]))
    cleaned = []
    for hit in raw_hits:
        if not cleaned:
            cleaned.append(hit)
            continue
        last_beat, last_drum, last_vel = cleaned[-1]
        if hit[1] == last_drum and (hit[0] - last_beat) < 0.05:
            if hit[2] > last_vel:
                cleaned[-1] = (last_beat, last_drum, hit[2])
        else:
            cleaned.append(hit)
    return cleaned

def enforce_human_limits(raw_hits):
    """Filters timeline to ensure at most 2 hand and 2 foot notes occur in any tight window."""
    raw_hits.sort(key=lambda x: x[0])
    cleaned = []
    window = []
    
    def process_window(w):
        if not w: return []
        hands = [x for x in w if x[1] in HAND_DRUMS]
        feet = [x for x in w if x[1] in FOOT_DRUMS]
        hands.sort(key=lambda x: x[2], reverse=True)
        feet.sort(key=lambda x: x[2], reverse=True)
        return hands[:2] + feet[:2]
        
    for hit in raw_hits:
        if not window:
            window.append(hit)
        else:
            if hit[0] - window[0][0] < 0.03:
                window.append(hit)
            else:
                cleaned.extend(process_window(window))
                window = [hit]
    if window:
        cleaned.extend(process_window(window))
    return cleaned

def apply_tempo_curve(raw_hits):
    """Simulates organic phrasing: rushing fills and dragging heavy spaces."""
    new_hits = []
    for beat, drum, vel in raw_hits:
        # Subtle global pocket shifting
        warp = math.sin(beat * math.pi / 4) * 0.04
        # Accelerando in the heavy crescendo
        if 144 <= beat <= 160:
            warp -= math.sin((beat - 144) / 16 * math.pi) * 0.1
        # Heavy layback during silence & accent breaks
        if 192 <= beat <= 208:
            warp += math.sin((beat - 192) / 16 * math.pi) * 0.15
            
        warped_beat = beat + warp
        new_hits.append((warped_beat, drum, vel))
    return new_hits

hits = clean_duplicates(hits)
hits = enforce_human_limits(hits)
warped_hits = apply_tempo_curve(hits)

# --- MIDI Generation ---

mid = mido.MidiFile(ticks_per_beat=480)
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))

events = []
for w_beat, drum, vel in warped_hits:
    events.append({'beat': w_beat, 'type': 'note_on', 'note': drum, 'vel': vel})
    events.append({'beat': w_beat + 0.1, 'type': 'note_off', 'note': drum, 'vel': 0})

# Sort by logical time, strictly ordering note_off before note_on for safety if equal
events.sort(key=lambda x: (x['beat'], 0 if x['type'] == 'note_off' else 1))

current_tick = 0
for ev in events:
    abs_tick = int(round(ev['beat'] * mid.ticks_per_beat))
    if abs_tick < 0: 
        abs_tick = 0
        
    delta = abs_tick - current_tick
    if delta < 0:
        delta = 0
    else:
        current_tick = abs_tick
        
    track.append(mido.Message(ev['type'], channel=9, note=ev['note'], velocity=ev['vel'], time=delta))

mid.save('solo.mid')
