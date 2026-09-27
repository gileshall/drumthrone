import mido
import random
import math

# Seed for deterministic identical output on every run
random.seed(4242)

mid = mido.MidiFile(type=0)
ticks_per_beat = 480
mid.ticks_per_beat = ticks_per_beat
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))

events = []

def add_tempo_event(beat, bpm):
    tempo = int(60000000 / bpm)
    abs_tick = int(beat * ticks_per_beat)
    events.append((abs_tick, 'meta', 'set_tempo', tempo, 0))

def hit(b, note, vel, swing=0.0, push=0.0):
    beat_frac = b % 1.0
    # Swing for 8ths and 16ths
    if 0.4 < beat_frac < 0.6:
        b += swing * 0.166
    elif (0.2 < beat_frac < 0.3) or (0.7 < beat_frac < 0.8):
        b += swing * 0.08
    
    # Global macro tempo pulling (breathes back and forth)
    macro_pull = math.sin(b * math.pi / 16) * 0.02
    
    # Humanize velocity
    v = vel + random.randint(-4, 4)
    v = max(1, min(127, int(v)))
    
    # Micro-timing jitter
    jitter = random.uniform(-0.01, 0.01)
    
    actual_b = b + macro_pull + push + jitter
    if actual_b < 0: actual_b = 0
    
    tick = int(actual_b * ticks_per_beat)
    
    events.append((tick, 'note', 'on', int(note), v))
    events.append((tick + 30, 'note', 'off', int(note), 0))

# General MIDI Percussion Map
kit = {
    'K': (36, 110), 'k': (36, 70),  
    'S': (38, 110), 's': (38, 70), 'g': (38, 40), 'r': (37, 100), 
    'H': (42, 100), 'h': (42, 70),  
    'O': (46, 100),                 
    'P': (44, 90),                  
    'R': (51, 90), 'b': (53, 110),  
    'C': (49, 110), 'c': (57, 110), 
    '1': (50, 100), '2': (48, 100), '3': (47, 100), '4': (45, 100), '5': (43, 100), '6': (41, 100), 
    'W': (56, 100), 'w': (56, 70),  
    'm': (62, 90), 'o': (63, 90), 'l': (64, 90), 
    'B': (60, 90), 'q': (61, 90),
    'X': (52, 110),
    'L': (55, 100), 'p': (55, 100)
}

def play_seq(start_beat, step, lines, swing=0.0, push=0.0, dyn_start=1.0, dyn_end=1.0):
    length = max(len(line) for line in lines)
    for i in range(length):
        b = start_beat + i * step
        dyn = dyn_start + (dyn_end - dyn_start) * (i / max(1, length - 1))
        for line in lines:
            if i < len(line):
                c = line[i]
                if c in kit:
                    note, base_vel = kit[c]
                    accent = 1.0
                    # Simulate stick dynamics for fast alternating strokes
                    if step <= 0.17 and i % 2 == 1:
                        accent = 0.85
                    vel = int(base_vel * dyn * accent)
                    hit(b, note, vel, swing=swing, push=push)

def roll(start_beat, end_beat, note, vel_start, vel_end, subdivision=0.125):
    steps = int((end_beat - start_beat) / subdivision)
    for i in range(steps):
        b = start_beat + i * subdivision
        vel = vel_start + (vel_end - vel_start) * (i / max(1, steps - 1))
        if abs(b % 1.0) < 0.01:
            vel += 15
        accent = 1.0
        if i % 2 == 1: accent = 0.85
        hit(b, note, int(vel * accent))

# === TEMPO MAP ===
add_tempo_event(0, 110)
add_tempo_event(32, 115)
add_tempo_event(48, 105)
add_tempo_event(64, 120)
for i in range(16):
    add_tempo_event(80 + i, 120 + i) # Swell up to 135
add_tempo_event(96, 135)
add_tempo_event(112, 140)
add_tempo_event(128, 120)
add_tempo_event(144, 120)
add_tempo_event(160, 135)
for i in range(16):
    add_tempo_event(192 + i, 135 + (i * 10 / 16)) # Swell up to 145
add_tempo_event(208, 145)
add_tempo_event(224, 150)
add_tempo_event(236, 110)
add_tempo_event(237, 90)
add_tempo_event(238, 70)

# === 0-16: Intro (Establishing Motif) ===
motif_a = [
    "r.r.r..g.r.g....",
    "K......K..K.....",
    "P...P...P...P..."
]
motif_a_var = [
    "r.r.r..g.r.g.r..",
    "K......K..K..K..",
    "P...P...P...P..."
]
for bar in range(4):
    b = bar * 4
    play_seq(b, 0.25, motif_a_var if bar == 3 else motif_a)

# === 16-32: Groove 1 (Hi-Hats and Ghost Notes) ===
groove_1 = [
    "HhHhHhHhHhHOHhHh",
    "....S..g.g..S..g",
    "K.k.....K.K.....",
    "..............P."
]
groove_1_var = [
    "HhHhHhHhHhHOHhHh",
    "....S..g.g..S.gg",
    "K.k.....K.K..K..",
    "..............P."
]
for bar in range(4):
    b = 16 + bar * 4
    play_seq(b, 0.25, groove_1_var if bar % 2 == 1 else groove_1, swing=0.1)

# === 32-48: Groove 2 (Ride Cymbal Variation) ===
groove_2 = [
    "R.bR.bR.R.bR.bR.",
    "....S..g.g..S..g",
    "K......KK.......",
    "P.P.P.P.P.P.P.P."
]
groove_2_fill = [
    "R.bR.bR.........",
    "....S..gS.ggS.S.",
    "K......K.K.K.K.K",
    "P.P.P.P........."
]
for bar in range(4):
    b = 32 + bar * 4
    play_seq(b, 0.25, groove_2_fill if bar == 3 else groove_2, swing=0.15)

# === 48-64: Tribal Tom Groove ===
tom_groove = [
    "6.6.6.6.6.6.6.6.",
    "..1...2...3...4.",
    "K..K.K..K..K.K..",
    "P...P...P...P..."
]
tom_groove_var = [
    "6.6.6.6.6.6.6.6.",
    "..1...2...3.4.5.",
    "K..K.K..K..K.K.K",
    "P...P...P...P..."
]
hit(48, 49, 110) # Crash
for bar in range(4):
    b = 48 + bar * 4
    play_seq(b, 0.25, tom_groove_var if bar == 3 else tom_groove)

# === 64-80: Gospel Chops (Linear Drumming) ===
for bar in range(4):
    b = 64 + bar * 4
    if bar == 0: hit(b, 57, 110)
    if bar % 2 == 0:
        play_seq(b, 0.25, [
            "H.k.S.k.H.k.S.k.1.k.S.k.K.K.S...",
            "............................H.H."
        ])
    else:
        play_seq(b, 0.25, [
            "H.k.S.k.H.k.S.k.3.4.k.k.S.S.5.6."
        ])

# === 80-96: The Tension Swell (Snare Roll & Triplets) ===
hit(80, 49, 110)
roll(80, 92, 38, 40, 110, subdivision=0.125) 
for i in range(12): 
    hit(80 + i, 36, 80 + i * 2)
    hit(80 + i + 0.5, 42, 60 + i * 2)

play_seq(92, 4/24, ["SS112233445566KKSS112233"])

# === 96-112: The Heavy Halftime Drop ===
halftime = [
    "X...X...X...X...X...X...X...X...", 
    "................S...............", 
    "K..K..K.....K.k.K..K........K...", 
]
halftime_fill = [
    "X...X...X...X...X...X...........",
    "................S.......S.S.S.S.",
    "K..K..K.....K.k.K..K...K.K.K.K.K",
]
for bar in range(4):
    b = 96 + bar * 4
    play_seq(b, 0.125, halftime_fill if bar == 3 else halftime)

# === 112-128: Blast Beat / Double Bass ===
db_groove = [
    "C.......C.......C.......C.......",
    "....S.......S.......S.......S...",
    "KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK"
]
db_fill = [
    "C.......C.......................",
    "....S.......S...1111222233334444",
    "KKKKKKKKKKKKKKKK................"
]
for bar in range(4):
    b = 112 + bar * 4
    play_seq(b, 0.125, db_fill if bar == 3 else db_groove)

# === 128-144: Latin Percussion Break ===
perc_groove = [
    "W...W...W...W...",
    "..m.o...l.....o.",  
    "......B...q.....",  
    "K.......K.......",
    "P.P.P.P.P.P.P.P."
]
perc_fill = [
    "W...W...........",
    "..m.o...l.l.o.o.",  
    "......B.........",  
    "K.......K.K.K.K.",
    "P.P.P.P.P.P.P.P."
]
for bar in range(4):
    b = 128 + bar * 4
    play_seq(b, 0.25, perc_fill if bar == 3 else perc_groove, swing=0.1)

# === 144-160: 3 Over 4 Polyrhythm ===
poly_groove = [
    "b..b..b..b..b..b",
    ".g..g..g..g..g..",
    "..K..K..K..K..K.",
    "P...P...P...P..."
]
poly_resolve = [
    "b..b..b..b......",
    ".g..g..g..S.S.S.",
    "..K..K..K..K.K.K",
    "P...P...P...P..."
]
for bar in range(4):
    b = 144 + bar * 4
    play_seq(b, 0.25, poly_resolve if bar == 3 else poly_groove)

# === 160-192: Jazz Swing & Snare Comping ===
jazz_ride = "R..R.RR..R.R"
jazz_pedal ="...P......P."
comps = [
    "..S......K..", "K......S...S", "...K..S..K..", "S.S.K.S.1.2.",
    "S..S..K..S..", ".S..K..S..K.", "S...S.S...S.", "111222333444"
]
for bar in range(8):
    b = 160 + bar * 4
    ride = "C..........." if bar == 7 else jazz_ride
    play_seq(b, 1/3, [ride, jazz_pedal, comps[bar]], dyn_start=0.8, dyn_end=0.9)

# === 192-208: The Big Build ===
build_1 = [
    "S.S.S.S.S.S.S.S.",
    "6.6.6.6.6.6.6.6.",
    "K...K...K...K..."
]
for bar in range(2):
    b = 192 + bar * 4
    play_seq(b, 0.25, build_1, dyn_start=0.5 + bar * 0.1, dyn_end=0.5 + (bar + 1) * 0.1)

build_2 = [
    "SSSSSSSSSSSSSSSS",
    "6666666666666666",
    "K.K.K.K.K.K.K.K."
]
for bar in range(2):
    b = 200 + bar * 4
    play_seq(b, 0.25, build_2, dyn_start=0.7 + bar * 0.15, dyn_end=0.7 + (bar + 1) * 0.15)

# === 208-224: The Climax (Motif Re-envisioned) ===
climax_groove = [
    "C.C.C..C.C.C.C..",
    "....S.......S...",
    "K.K.K..K.K.K.K..",
]
climax_fill = [
    "C.C.C...........",
    "....S.SS11223344",
    "K.K.K.KK........"
]
for bar in range(4):
    b = 208 + bar * 4
    play_seq(b, 0.25, climax_fill if bar == 3 else climax_groove)

# === 224-236: The Frenzy (Moving Around The Kit) ===
frenzy_1 = [
    "C.......C.......C.......C.......",
    "K.......K.......K.......K.......",
    ".S112233.S334455.S556611.S223344"
]
frenzy_2 = [
    "C.......C.......C.......C.......",
    "K.K.K.K.K.K.K.K.K.K.K.K.K.K.K.K.",
    ".S..S..S.S..S..S.S..S..S.S..S..S"
]
frenzy_3 = [
    "C.......C.......C.......C.......",
    "K...K...K...K...K...K...K...K...",
    "SSSS111122223333444455556666SSSS"
]
play_seq(224, 0.125, frenzy_1)
play_seq(228, 0.125, frenzy_2)
play_seq(232, 0.125, frenzy_3)

# === 236-240: The Grand Finale ===
hit(236, 49, 120)
hit(236, 36, 120)
hit(237, 57, 120)
hit(237, 36, 120)
hit(238, 49, 127)
hit(238, 36, 127)
hit(239, 49, 127)
hit(239, 57, 127)
hit(239, 36, 127)

# Padding to let the final hits decay naturally
events.append((int(244 * ticks_per_beat), 'note', 'off', 36, 0))

# === Sorting & Deduplication ===
def get_sort_key(e):
    if e[1] == 'meta':
        priority = 0
    else:
        priority = 1 if e[2] == 'off' else 2
    return (e[0], priority)

events.sort(key=get_sort_key)

unique_events = []
seen = set()
for e in events:
    if e[1] == 'note':
        sig = (e[0], e[1], e[2], e[3]) 
        if sig in seen:
            continue
        seen.add(sig)
    unique_events.append(e)

# === Write to Track ===
last_tick = 0
for e in unique_events:
    abs_tick = e[0]
    delta = abs_tick - last_tick
    last_tick = abs_tick
    
    if e[1] == 'meta':
        track.append(mido.MetaMessage(e[2], tempo=e[3], time=delta))
    elif e[1] == 'note':
        msg_type = 'note_on' if e[2] == 'on' else 'note_off'
        # Channel 9 maps to MIDI Channel 10
        track.append(mido.Message(msg_type, note=e[3], velocity=e[4], time=delta, channel=9))

mid.save('solo.mid')
