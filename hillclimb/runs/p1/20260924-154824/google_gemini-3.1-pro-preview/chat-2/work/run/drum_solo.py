import mido
import math

# GM Percussion Key Map
KICK = 36
SNARE = 38
SNARE_SIDE = 37
HAT_CLOSED = 42
HAT_PEDAL = 44
HAT_OPEN = 46
TOM_HI = 50
TOM_MID_HI = 48
TOM_MID_LOW = 47
TOM_LOW = 45
FLOOR_HI = 43
FLOOR_LOW = 41
CRASH_1 = 49
CRASH_2 = 57
RIDE = 51
RIDE_BELL = 53
SPLASH = 55
CHINA = 52
COWBELL = 56
TAMBOURINE = 54

cmap = {
    'K': KICK, 'S': SNARE, 'X': SNARE_SIDE,
    'H': HAT_CLOSED, 'O': HAT_OPEN, 'P': HAT_PEDAL,
    'T': TOM_HI, 'M': TOM_MID_LOW, 'F': FLOOR_LOW,
    'C': CRASH_1, 'R': RIDE, 'B': RIDE_BELL,
    'L': SPLASH, 'W': COWBELL
}

class Sequencer:
    def __init__(self):
        self.notes = []
        self.tempo_changes = []

    def add_note(self, beat, pitch, vel, dur=0.1):
        vel = max(1, min(127, int(vel)))
        self.notes.append({'beat': beat, 'pitch': pitch, 'vel': vel, 'dur': dur})
        
    def add_tempo(self, beat, bpm):
        self.tempo_changes.append({'beat': beat, 'bpm': bpm})

def apply_swing(beat, swing_amt):
    sixteenth_idx = math.floor(beat * 4 + 0.001)
    is_offbeat = sixteenth_idx % 2 == 1
    if is_offbeat:
        return beat + swing_amt * 0.125
    return beat

def parse_grid(seq, start_beat, grid_str, char_to_pitch, vels, swing=0, step=0.25):
    lines = grid_str.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        strokes = line.split()
        for i, st in enumerate(strokes):
            if st == '.' or st == '-': continue
            b = start_beat + i * step
            pitch = char_to_pitch.get(st.upper())
            if pitch is None: continue
            
            is_accent = st.isupper()
            vel = vels.get('accent', 100) if is_accent else vels.get('ghost', 40)
            if st.upper() == 'K':
                vel = vels.get('kick', 110) if is_accent else vels.get('ghost', 40) + 15
            
            # Deterministic, musical phrasing (accent downbeats slightly)
            sixteenth = int(round(b * 4)) % 16
            if sixteenth % 4 == 0:
                vel += 3
            elif sixteenth % 2 == 1:
                vel -= 3
                
            vel = max(1, min(127, int(vel)))
            warped_b = apply_swing(b, swing)
            seq.add_note(warped_b, pitch, vel)

def add_groove(seq, start_beat, grids, vels, swing=0):
    b = start_beat
    for grid in grids:
        parse_grid(seq, b, grid, cmap, vels, swing)
        b += 4
    return b

def roll(seq, start, end, pitch, vel_start, vel_end, step=0.125):
    b = start
    while b < end - 0.01:
        progress = (b - start) / (end - start)
        vel = vel_start + (vel_end - vel_start) * progress
        # Emulate alternating hands (left hand slightly weaker)
        stroke_idx = int(round((b - start) / step))
        if stroke_idx % 2 == 1:
            vel -= 5 
        vel = max(1, min(127, int(vel)))
        seq.add_note(b, pitch, vel)
        b += step

intro_grids = [
    """
    K . . . . . K . K . . . . . K .
    F . F . . . . . . . F . . . . .
    . . s . . s . . . . s . s s . .
    """,
    """
    K . . . . . K . K . . . . . K .
    F . F . . . . . . . F . . . F .
    . . s . . s . . . . s . S . . .
    """,
    """
    K . . . . . K . K . . . K . K .
    F . F . . . . . . . F . . . . .
    . . s . . s . . . . s . s s . .
    """,
    """
    K . . . . . K . K . . . K . . .
    F . F . . . . . . . F . . . . .
    . . s . . s . . . S . S . S S S
    """
]

intro_grids_2 = [
    """
    C . . . . . . . . . . . . . . .
    K . . . . . K . K . . . . . K .
    F . F . . . . . . . F . . . . .
    . . s . . s . . . . s . s s . .
    """,
    """
    K . . . . . K . K . . . . . K .
    F . F . . . . . . . F . F . . .
    . . s . . s . . . . s . . . S .
    """,
    """
    K . . . . . K . K . . . K . K .
    F . F . . . . . . . F . . . . .
    . . s . . s . . . . s . s s . .
    """,
    """
    K . . . K . . . K . . . K . . .
    S S S S . . . . . . . . . . . .
    . . . . T T T T . . . . . . . .
    . . . . . . . . M M M M . . . .
    . . . . . . . . . . . . F F F F
    """
]

groove1_grids = [
    """
    H H h H H h H O . h H h H h H h
    . . . . S . . s . . . s S . . .
    K . K . . . . . K . . . . . . .
    """,
    """
    H H h H H h H h H h H O . h H h
    . . s . S . . . . s . . S . s .
    K . K . . . . . K . . . . K . .
    """,
    """
    H H h H H h H O . h H h H h H h
    . . . . S . . s . . . s S . . .
    K . K . . . . . K . . . . . . .
    """,
    """
    H H h H H h H h H h H h . . . .
    . . s . S . . . . s . . S S s S
    K . K . . . . . K . . . . . . .
    """,
    """
    C . . . . . . . . . . . . . . .
    . h h H H h H O . h H h H h H h
    . . . . S . . s . . . s S . . .
    K . K . . . . . K . . . . . . .
    """,
    """
    H H h H H h H h H h H O . h H h
    . . s . S . . . . s . . S . s S
    K . K . . . . . K . . . . K . .
    """,
    """
    H H h H H h H O . h H h H h H h
    . . . . S . . s . . . s S . . .
    K . K . . . . . K . . . . . . .
    """,
    """
    K . . . K . . . K . K . K . . .
    . . S S . S S S . S . S . . . .
    . . . . . . . . . . . . . T T .
    . . . . . . . . . . . . . . . M
    """
]

dev1_grids = [
    """
    C . . . . . . . . . . . . . . .
    R s R R s R s s R s R R s R s s
    K . . . . . K . . . . . K . . .
    P . . . P . . . P . . . P . . .
    """,
    """
    B s R R s B s s B s R R s R s s
    K . . . . . K . . . . . K . . .
    P . . . P . . . P . . . P . . .
    """,
    """
    B s R R s R s s R s B R s B s s
    K . . . . . K . . . . . K . . .
    P . . . P . . . P . . . P . . .
    """,
    """
    R s R R s R s s . . . . . . . .
    . . . . . . . . S S S . S S S .
    K . . . . . K . K . . . K . . .
    P . . . P . . . . . . . . . . .
    """,
    """
    C . . . . . . . . . . . . . . .
    R s B R s B s s B s R R s R s s
    K . . . . . . . . K . . . . . .
    P . . . P . . . P . . . P . . .
    """,
    """
    R s R R s R s s R s B R s B s s
    K . . . . . K . . . . . K . . .
    P . . . P . . . P . . . P . . .
    """,
    """
    R s B R s B s s B s R R s R s s
    K . . . K . . . K . . . K . . .
    P . . . P . . . P . . . P . . .
    """,
    """
    S . . S . . S . . S . . S . . .
    T . . T . . T . . T . . T . . .
    K K . . K K . . K K . . K K . .
    """
]

interlude_grids = [
    """
    C . . . . . . . . . . . . . . .
    X . x x X . x x X . x x X . x x
    K . . . . . . . K . . . . . . .
    P . P . P . P . P . P . P . P .
    """,
    """
    W . . . . . W . . . . . W . . .
    X . x x X . x x X . x x X . x x
    K . . . . . . . K . . . . . . .
    P . P . P . P . P . P . P . P .
    """,
    """
    W . . . W . . . W . . . W . . .
    X . x x X . x x X . x x X . x x
    K . . . . . . . K . . . . . . .
    P . P . P . P . P . P . P . P .
    """,
    """
    X . x x X . x x X . x x X . . .
    L . . . . . . . . . . . . . L .
    . . . . . . . . . . t t . . . .
    K . . . . . . . K . . . . . K .
    """,
    """
    X . x x X . x x X . x x X . x x
    W . . . . . . . W . . . . . W .
    K . . . . . . . K . . . . . . .
    P . P . P . P . P . P . P . P .
    """,
    """
    X . x x X . x x X . x x X . x x
    W . . W . . W . . . W . . . W .
    K . . . . . . . K . . . . . . .
    P . P . P . P . P . P . P . P .
    """,
    """
    X . x x X . x x X . x x X . x x
    K . . . . . . . K . . . . . . .
    P . P . P . P . P . P . P . P .
    """,
    """
    S . K T . K M . K F . K S S S S
    K . . . . . . . . . . . . . . .
    """
]

groove2_grids = [
    """
    C . . . . . . . C . . . . . . .
    H . H . H . H . H . H . H . H .
    . . . . S . . . . . . . S . . .
    K k K k . . K k K k K k . . K k
    """,
    """
    H . H . H . H . H . H . H . H .
    . . . . S . . . . . . . S . . s
    K k K k . . K k K k K k . . K k
    """,
    """
    C . . . . . . . C . . . . . . .
    H . H . H . H . H . H . H . H .
    . . . . S . . . . . . . S . . .
    K k K k . . K k K k K k . . K k
    """,
    """
    H . H . H . H . H . . . . . . .
    . . . . S . . . . . S S S S S S
    K k K k . . K k K k . . . . . .
    """,
    """
    C . . . . . . . . . . . . . . .
    R . r R . r R . R . r R . r R .
    . . . . S . . . . . . . S . . .
    K . . . . . K . K . . . . . K .
    """,
    """
    R . r R . r R . R . r R . r R .
    . . . . S . . . . . S . . S . .
    K . K . . . K . K . . . . . K .
    """,
    """
    C . . . . . . . C . . . . . . .
    R . r R . r R . R . r R . r R .
    . . . . S . . . . . . . S . . .
    K . . . . . K . K . . . . . K .
    """,
    """
    S S S S S S S S . . . . . . . .
    . . . . . . . . T T T T . . . .
    . . . . . . . . . . . . F F F F
    K . . . . . . . K . . . K . . .
    """
]

outro_grids = [
    """
    C . . . . . C . C . . . . . C .
    K . . . . . K . K . . . . . K .
    F . F . . . . . . . F . . . . .
    . . s . . s . . . . s . S S . .
    """,
    """
    C . . . . . C . C . . . . . C .
    K . . . . . K . K . . . . . K .
    F . F . . . . . . . F . . . F .
    . . s . . s . . . . s . S . . .
    """,
    """
    C . . . . . C . C . . . C . C .
    K . . . . . K . K . . . K . K .
    F . F . . . . . . . F . . . . .
    . . s . . s . . . . s . S S . .
    """,
    """
    C . . . . . . . . . . . . . . .
    K . . . K . . . K . . . K . . .
    F . F . . . F . . . F . . . . .
    . . s . . s . . S . S . S S S S
    """
]

def build_climax(seq, start_beat):
    b = start_beat
    
    for i in range(4):
        seq.add_note(b + i, CRASH_1, 120)
        seq.add_note(b + i, KICK, 110)
        for j in range(4):
            if not (i == 0 and j == 0):
                vel = 100 if j == 0 else (80 if j % 2 == 1 else 90)
                seq.add_note(b + i + j*0.25, SNARE, vel)
    b += 4
    
    seq.add_note(b, CRASH_2, 120)
    seq.add_note(b, KICK, 110)
    roll(seq, b, b+4, SNARE, 40, 120, 0.125)
    b += 4
    
    roll(seq, b, b+1, SNARE, 100, 110, 0.125)
    roll(seq, b+1, b+2, TOM_HI, 100, 110, 0.125)
    roll(seq, b+2, b+3, TOM_MID_LOW, 100, 110, 0.125)
    roll(seq, b+3, b+4, FLOOR_LOW, 100, 110, 0.125)
    for i in range(4):
        seq.add_note(b + i, KICK, 110)
    b += 4
    
    for i in range(16):
        time = b + i * 0.25
        if i % 3 == 0:
            seq.add_note(time, CRASH_1, 120)
            seq.add_note(time, KICK, 110)
        else:
            seq.add_note(time, SNARE, 80)
    b += 4
    
    for i in range(32):
        time = b + i * 0.125
        pitch = TOM_HI if (i // 2) % 2 == 0 else TOM_MID_LOW
        vel = 110 if i % 2 == 0 else 95
        seq.add_note(time, pitch, vel)
        if i % 8 == 0:
            seq.add_note(time, KICK, 110)
    b += 4
    
    chop = [KICK, SNARE, SNARE, KICK, TOM_HI, TOM_HI, KICK, FLOOR_LOW, FLOOR_LOW, KICK, SNARE, SNARE, KICK, KICK, SNARE, SNARE]
    for i in range(32):
        time = b + i * 0.125
        pitch = chop[i % 16]
        vel = 120 if pitch == KICK else (110 if pitch != SNARE else 115)
        if i % 4 == 0: vel = 127
        seq.add_note(time, pitch, vel)
    b += 4
    
    for i in range(16):
        time = b + i * 0.25
        vel = 70 + (i * 3)
        seq.add_note(time, SNARE, vel)
        seq.add_note(time, FLOOR_LOW, vel)
        seq.add_note(time, KICK, vel)
    b += 4
    
    roll(seq, b, b+4, SNARE, 90, 127, 0.125)
    for i in range(16):
        time = b + i * 0.25
        seq.add_note(time, KICK, 100 + i)
        seq.add_note(time, FLOOR_LOW, 100 + i)
    b += 4
    
    return b

def build_ending(seq, start_beat):
    b = start_beat
    
    seq.add_note(b, CRASH_1, 127)
    seq.add_note(b, CRASH_2, 127)
    seq.add_note(b, KICK, 127)
    b += 4
    
    roll(seq, b, b+2, TOM_HI, 120, 100, 0.125)
    roll(seq, b+2, b+4, TOM_LOW, 120, 100, 0.125)
    b += 4
    
    seq.add_note(b, CRASH_1, 127)
    seq.add_note(b, KICK, 127)
    seq.add_note(b+2, CRASH_2, 127)
    seq.add_note(b+2, KICK, 127)
    b += 4
    
    roll(seq, b, b+3, SNARE, 60, 127, 0.125)
    seq.add_note(b+3, CRASH_1, 127)
    seq.add_note(b+3, CRASH_2, 127)
    seq.add_note(b+3, KICK, 127)
    b += 4
    
    for i in range(16):
        time = b + i
        if i % 2 == 1:
            seq.add_note(time, HAT_PEDAL, 50)
            
    end_b = b + 12
    seq.add_note(end_b, CRASH_1, 127)
    seq.add_note(end_b, CRASH_2, 127)
    seq.add_note(end_b, KICK, 127)
    seq.add_note(end_b, SNARE, 127)

def generate_tempo_map(seq):
    for b in range(0, 32):
        bpm = 105 + (10 * (b / 32))
        seq.add_tempo(b, bpm)
    for b in range(32, 64):
        bpm = 115 + (5 * ((b-32) / 32)) + math.sin((b / 4) * math.pi) * 2
        seq.add_tempo(b, bpm)
    for b in range(64, 96):
        seq.add_tempo(b, 120)
    for b in range(96, 128):
        bpm = 120 - (30 * ((b-96) / 32))
        seq.add_tempo(b, bpm)
    for b in range(128, 160):
        bpm = 130 + (10 * ((b-128) / 32))
        seq.add_tempo(b, bpm)
    for b in range(160, 192):
        bpm = 140 + (5 * ((b-160) / 32))
        seq.add_tempo(b, bpm)
    for b in range(192, 224):
        bpm = 145 - (45 * ((b-192) / 32))
        seq.add_tempo(b, bpm)
    for b in range(224, 256):
        bpm = 100 - (40 * ((b-224) / 32))
        seq.add_tempo(b, bpm)

def build_solo(seq):
    vels_intro = {'accent': 105, 'ghost': 50, 'kick': 110}
    add_groove(seq, 0, intro_grids, vels_intro, swing=0.1)
    add_groove(seq, 16, intro_grids_2, vels_intro, swing=0.1)
    
    vels_g1 = {'accent': 100, 'ghost': 45, 'kick': 115}
    add_groove(seq, 32, groove1_grids, vels_g1, swing=0.2)
    
    vels_dev1 = {'accent': 110, 'ghost': 55, 'kick': 110}
    add_groove(seq, 64, dev1_grids, vels_dev1, swing=0.0)
    
    vels_inter = {'accent': 90, 'ghost': 35, 'kick': 90}
    add_groove(seq, 96, interlude_grids, vels_inter, swing=0.15)
    
    vels_g2 = {'accent': 115, 'ghost': 65, 'kick': 120}
    add_groove(seq, 128, groove2_grids, vels_g2, swing=0.05)
    
    build_climax(seq, 160)
    
    vels_outro = {'accent': 120, 'ghost': 60, 'kick': 127}
    add_groove(seq, 192, outro_grids * 2, vels_outro, swing=0.1)
    
    build_ending(seq, 224)

def export_midi(seq, filename='solo.mid'):
    mid = mido.MidiFile(type=0)
    mid.ticks_per_beat = 480
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.Message('program_change', channel=9, program=0, time=0))
    
    events = []
    for t in seq.tempo_changes:
        tempo = mido.bpm2tempo(t['bpm'])
        events.append({'beat': t['beat'], 'type': 'tempo', 'tempo': tempo})
        
    for n in seq.notes:
        events.append({'beat': n['beat'], 'type': 'note_on', 'pitch': n['pitch'], 'vel': n['vel']})
        events.append({'beat': n['beat'] + n['dur'], 'type': 'note_off', 'pitch': n['pitch'], 'vel': 0})
        
    def sort_key(e):
        order = {'tempo': 0, 'note_off': 1, 'note_on': 2}
        return (e['beat'], order[e['type']])
        
    events.sort(key=sort_key)
    
    last_ticks = 0
    for e in events:
        abs_ticks = int(round(e['beat'] * mid.ticks_per_beat))
        delta_ticks = abs_ticks - last_ticks
        if delta_ticks < 0: delta_ticks = 0
        
        if e['type'] == 'tempo':
            track.append(mido.MetaMessage('set_tempo', tempo=e['tempo'], time=delta_ticks))
        elif e['type'] == 'note_on':
            track.append(mido.Message('note_on', channel=9, note=e['pitch'], velocity=e['vel'], time=delta_ticks))
        elif e['type'] == 'note_off':
            track.append(mido.Message('note_off', channel=9, note=e['pitch'], velocity=0, time=delta_ticks))
            
        last_ticks = abs_ticks
        
    track.append(mido.MetaMessage('text', text='End', time=mid.ticks_per_beat * 4))
    mid.save(filename)

if __name__ == '__main__':
    seq = Sequencer()
    generate_tempo_map(seq)
    build_solo(seq)
    export_midi(seq, 'solo.mid')
