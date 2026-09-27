import mido
import random

# Ensure identical output on every run
random.seed(42)

TICKS_PER_BEAT = 480
BPM = 120

# Dictionary to map visual characters to velocities
VEL = {
    'X': 110, 'x': 80, 'O': 105, 'o': 45, 'v': 25,
    '^': 127, '.': 0, '-': 0,
    'S': 60,
    '1': 50, '2': 65, '3': 80, '4': 95, '5': 110,
    '#': 120
}

# General MIDI Percussion Key Map (Channel 10)
K = 36          # Bass Drum 1
S = 38          # Acoustic Snare
CHH = 42        # Closed Hi-Hat
PHH = 44        # Pedal Hi-Hat
OHH = 46        # Open Hi-Hat
R = 51          # Ride Cymbal 1
RB = 53         # Ride Bell
C1 = 49         # Crash Cymbal 1
C2 = 57         # Crash Cymbal 2
SP = 55         # Splash Cymbal
CHINA = 52      # Chinese Cymbal
T1 = 50         # High Tom
T2 = 48         # Hi-Mid Tom
T3 = 45         # Low Tom
T4 = 41         # Low Floor Tom

CB = 56         # Cowbell
HI_BONG = 60    # High Bongo
LO_BONG = 61    # Low Bongo
OPEN_HI_CONGA = 63
LO_CONGA = 64
HI_TIMB = 65    # High Timbale
LO_TIMB = 66    # Low Timbale

notes = []

def add_note(tick, pitch, velocity, duration=60):
    if velocity <= 0:
        return
    # Subtle humanization in timing and dynamics
    tick_shift = random.randint(-4, 4)
    vel_shift = random.randint(-4, 4)
    vel = max(1, min(127, velocity + vel_shift))
    t = max(0, int(tick) + tick_shift)
    notes.append((t, pitch, vel, duration))

def play_bar(bar_idx, pattern_dict, swing=0):
    """
    Parses a dictionary of instrument patterns and adds them to the timeline.
    Patterns can be 16 steps (16th notes) or 32 steps (32nd notes).
    """
    for pitch, pat in pattern_dict.items():
        pat = pat.replace(' ', '').replace('|', '')
        steps = len(pat)
        if steps == 0: 
            continue
        ticks_per_step = int((4 * TICKS_PER_BEAT) / steps)
        for i, char in enumerate(pat):
            if char in VEL and VEL[char] > 0:
                tick = bar_idx * 4 * TICKS_PER_BEAT + i * ticks_per_step
                
                # Apply swing to offbeat 16th notes
                if swing > 0:
                    if steps == 16 and i % 2 == 1:
                        tick += swing
                    elif steps == 32 and (i % 8 in [2, 3, 6, 7]):
                        tick += swing

                add_note(tick, pitch, VEL[char])

# --- Pattern Definitions ---

# Intro (Bars 0-3): Establishing the groove
intro_0 = {K:"X...........X...", CHH:"x.x.x.x.x.x.x.x.", S:"..............o."}
intro_1 = {K:"X.....X...X.....", CHH:"x.x.x.x.x.x.x.x.", S:"....X.......X..o"}
intro_2 = {K:"X.....X...X..X..", CHH:"xxxxxxxxxxxxxxxx", S:"..o.X..oo..oX..o"}
intro_3 = {K:"X.....X.........", CHH:"xxxxxxxxxx......", OHH:"..........O.....", S:"..o.X..oo.XXooOO"}

# Motif A (Bars 4-11): Syncopated linear funk groove
g1_a = {K:"X.o...X...X.....", CHH:"xxxxxxxOxxxxxxxx", S:"....X...oo..X.oo"}
g1_b = {K:"X.o...X...X..X..", CHH:"xxxxxxxOxxxOxxxx", S:"....X...oo..X.oo"}
g1_c = {K:"X.o...X...X.....", CHH:"xxxxxxxOxxxxxxxx", S:"....X...oo..X...", T1:"..............O.", T2:"...............O"}
g1_f = {K:"X.......X.......", S:"O.ooO.ooOoooOoOo", C1:"X..............."}
g1_d = {K:"X.o...X...X..X..", OHH:"x.x.x.x.x.x.x.x.", S:"..o.X..oo.o.X.oo", C1:"X..............."}
g1_e = {K:"X.X...X...X..X..", OHH:"x.x.x.x.x.x.x.x.", S:"..o.X..oo.o.X.oo"}
g1_f2 = {K:"X.X...X.........", OHH:"x.x.x.x.........", S:"..o.X...OOOO....", T2:"............OO..", T4:"..............OO", C2:"X..............."}

# Tribal Toms Break (Bars 12-15)
tom_a = {K:"X...X...X...X...", T4:"..O...O...O...O.", T3:"....O.......O...", S:"........O.......", C1:"X..............."}
tom_b = {K:"X...X...X...X...", T4:"..O...O...O...O.", T3:"....O.......O...", S:"..o.....O.....o."}
tom_c = {K:"X...X...X...X...", T4:"..O...O...O...O.", T3:"....O.......O...", S:"..o.....O.oooooo"}
tom_f = {K:"X.X.X.X.X.X.X.X.", T1:"OOOO............", T2:"....OOOO........", T3:"........OOOO....", T4:"............OOOO"}

# Ride Cymbal Climax 1 (Bars 16-23)
ride_a = {K:"X......XX..X....", R:"xxxxxxxxxxxxxxxx", S:"....X.......X..o", C1:"X..............."}
ride_b = {K:"X......XX..X..X.", R:"xxxxxxxxxxxxxxxx", S:"..o.X..oo..oX..o"}
ride_c = {K:"X......XX..X....", R:"xxxxxxxxxxxxxxxx", S:"....X.......X.oo", C2:"...........X...."}
ride_d = {K:"X...X...X...X...", R:"x.x.x.x.x.x.x.x.", RB:"..x...x...x...x.", S:"....X.......X..."}
ride_e = {K:"X..XX..XX..XX...", R:"xxxxxxxxxxxxxxxx", S:"..o.X..oo..oX..o", C1:"X..............."}
ride_f = {K:"X...X...X...X...", S:"X.ooX.ooX.......", T1:"..O...O.........", T2:"........OOOO....", T3:"............OOOO", C1:"X..............."}

# Latin Percussion Breakdown (Bars 24-31)
perc_a = {
    K:  "X.......X.......",
    CB: "X..X..X...X.X...",
    HI_BONG: "..o...o...o.....",
    LO_CONGA: "....O.......O...",
    PHH: "....X.......X..."
}
perc_b = {
    K:  "X...X...X...X...",
    CB: "X..X..X...X.X...",
    OPEN_HI_CONGA: "..O...O...O...O.",
    LO_CONGA: "O...O...O...O...",
    PHH: "....X.......X..."
}
perc_f = {
    HI_TIMB: "OOOOOOOO........",
    LO_TIMB: "........OOOOOOOO",
    K: "X.X.X.X.X.X.X.X.",
    SP: "X..............."
}

# Ghost Note / Purdie Shuffle Build (Bars 32-39)
b2_a = {
    K: "X.......X.......",
    CHH: "..x.x.x.x.x.x.x.",
    S: "..o.O..o..o.O..o",
    C1: "X..............."
}
b2_b = {
    K: "X...X...X...X...",
    CHH: "x.x.x.x.x.x.x.x.",
    S: "..o.O..o..o.O..o"
}
b2_c = {
    K: "X..X....X..X....",
    CHH: "x.x.x...x.x.x...",
    S: "..o.O..o..o.O..o",
    OHH: "......O.......O."
}
b2_f = {
    K: "X.X.X.X.X.X.X.X.",
    S: "1122334455XXXXXX",
    C1: "X..............."
}

# Second Climax: Heavy Crashes (Bars 40-47)
c2_a = {
    K: "X..X..X.X..X..X.",
    C1:"X.X.X.X.X.X.X.X.",
    S: "....X.......X..."
}
c2_b = {
    K: "X..X..X.X..X..X.",
    C1:"X.X.X.X.X.X.X.X.",
    S: "..o.X..oo..oX..o"
}
c2_c = {
    K: "X.X.X.X.X.X.X.X.",
    C1:"X.X.X.X.X.X.X.X.",
    S: "....X.......X..."
}

# The Shred: Linear fills and 32nd notes (Bars 48-55)
shred_g1 = {
    K:  "X..X....X.X...X.",
    R:  "xxxxxxxxxxxxxxxx",
    S:  "..X...XX....X...",
    C1: "X..............."
}
shred_g2 = {
    K:  "X.X...X.X.X...X.",
    CHH:"..x.....x...x...",
    S:  "..X.XX..X.XX..X.",
    C2: "X..............."
}
shred_1 = {
    K: "X...X...X...X...",
    S: "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", # 32 steps
    CHINA: "X...............",
    SP: "........X......."
}
shred_2 = {
    K:  "X...X...X...X...",
    S:  "OOOO................OOOO........", # 32 steps
    T1: "....OOOO................OOOO....",
    T2: "........OOOO................OOOO",
    T4: "............OOOO............OOOO"
}
shred_3 = {
    K:  "X...X...X...X...",
    S:  "..XX..XX..XX..XX..XX..XX..XX..XX", # 32nd note off-beats
    C1: "X.......X......."
}
shred_f1 = {
    K:  "X...X...X...X...",
    S:  "O.o.O.o.O.o.O.o.OOOOOOOOOOOOOOOO", # 16ths into 32nds
    C1: "X..............."
}
shred_f2 = {
    K:  "X.X.X.X.X.X.X.X.",
    S:  ".1111111.2222222.3333333.XXXXXXX", # 32nd crescendo rolls resolving on beat
    C1: "X...X...X...X..."
}

# Outro: Huge ensemble hits and final space (Bars 56-59)
outro_1 = {
    K:  "X.......X...X...X.......X...X...",
    C1: "X.......X...X...X.......X...X...",
    S:  "X.......X...X...X.......X...X..."
}
outro_2 = {
    K:  "X.....X.....X...X.X.X.X.X.X.X.X.",
    C1: "X.....X.....X...................",
    S:  "X.....X.....X...O.O.O.O.O.O.O.O."
}
outro_3 = {
    K:  "X...X...X...X...",
    C1: "X...X...X...X...",
    S:  "X.ooX.ooX.ooX.oo"
}
outro_4 = {
    K:  "X...X...X.......",
    C1: "X...X...X.......",
    S:  "X...X...X.......",
    T4: "........................OOOOOOOO" # Massive tom roll at the end of the bar
}

# The Final Hit (Bar 60 - exact 2:00 mark)
final_hit = {
    K: "X", C1: "X", C2: "X", S: "X"
}

# Assemble the 60-bar solo
song = [
    # 0-3
    intro_0, intro_1, intro_2, intro_3,
    # 4-11
    g1_a, g1_b, g1_a, g1_f,
    g1_d, g1_e, g1_d, g1_f2,
    # 12-15
    tom_a, tom_b, tom_c, tom_f,
    # 16-23
    ride_a, ride_b, ride_c, ride_d,
    ride_e, ride_b, ride_c, ride_f,
    # 24-31
    perc_a, perc_b, perc_a, perc_f,
    perc_b, perc_a, perc_b, b2_f,
    # 32-39
    b2_a, b2_b, b2_c, b2_b,
    b2_a, b2_b, b2_c, c2_a,
    # 40-47
    c2_a, c2_b, c2_c, c2_b,
    c2_a, c2_b, c2_c, shred_f1,
    # 48-55
    shred_g1, shred_g2, shred_1, shred_g2,
    shred_g1, shred_2, shred_3, shred_f2,
    # 56-59
    outro_1, outro_2, outro_3, outro_4
]

# Process all bars
for i, bar_dict in enumerate(song):
    play_bar(i, bar_dict, swing=15) # 15 ticks of 16th note swing provides a deep pocket

# Strike the final pose right at the beginning of bar 60
play_bar(60, final_hit, swing=0)

# Build the MIDI File
notes.sort(key=lambda x: x[0])

mid = mido.MidiFile(type=0, ticks_per_beat=TICKS_PER_BEAT)
track = mido.MidiTrack()
mid.tracks.append(track)

track.append(mido.MetaMessage('track_name', name='Showcase Drum Solo'))
track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))

events = []
for (tick, pitch, vel, dur) in notes:
    events.append((tick, 'note_on', pitch, vel))
    events.append((tick + dur, 'note_off', pitch, 0))

# Ensure note_off comes before note_on if they happen on the exact same tick
events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

prev_tick = 0
for tick, msg_type, pitch, vel in events:
    delta = tick - prev_tick
    # Channel 9 in mido is MIDI Channel 10 (0-indexed)
    track.append(mido.Message(msg_type, channel=9, note=pitch, velocity=vel, time=int(delta)))
    prev_tick = tick

mid.save('solo.mid')
