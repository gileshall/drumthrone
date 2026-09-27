import mido

class PRNG:
    def __init__(self, seed=1337):
        self.state = seed
    def random(self):
        self.state = (1103515245 * self.state + 12345) & 0x7fffffff
        return self.state / 0x7fffffff
    def randint(self, a, b):
        return a + int(self.random() * (b - a + 1))
    def uniform(self, a, b):
        return a + self.random() * (b - a)

MAP = {
    'K': 36, 'k': 36,  # Kick
    'X': 37, 'x': 37,  # Sidestick
    'S': 38, 's': 38,  # Snare
    'H': 42, 'h': 42,  # Closed Hat
    'P': 44, 'p': 44,  # Pedal Hat
    'O': 46, 'o': 46,  # Open Hat
    'R': 51, 'r': 51,  # Ride
    'B': 53, 'b': 53,  # Ride Bell
    'C': 49,           # Crash 1
    'D': 57,           # Crash 2
    'Y': 55,           # Splash
    'Z': 52,           # China
    'T': 50, '1': 50,  # Tom 1
    'U': 48, '2': 48,  # Tom 2
    'V': 47, '3': 47,  # Tom 3
    'W': 45, '4': 45,  # Tom 4
    'F': 43, '5': 43,  # Tom 5
    'E': 41, '6': 41,  # Tom 6
}

def get_velocity(char, prng):
    if char in ['C', 'D', 'Z', 'Y']: base = 120 
    elif char in ['K']: base = 110 
    elif char in ['k']: base = 75  
    elif char in ['S']: base = 115 
    elif char in ['s']: base = 40  
    elif char in ['H']: base = 95  
    elif char in ['h']: base = 55  
    elif char in ['O']: base = 105 
    elif char in ['P', 'p']: base = 90 
    elif char in ['T', 'U', 'V', 'W', 'F', 'E']: base = 110 
    elif char in ['1', '2', '3', '4', '5', '6']: base = 105 
    elif char in ['R']: base = 95  
    elif char in ['r']: base = 65  
    elif char in ['B']: base = 115 
    elif char in ['b']: base = 90  
    else: base = 90 if char.isupper() else 50
    
    vel = base + prng.randint(-6, 6)
    return max(1, min(127, vel))

def get_swung_tick(tick, swing_amount):
    rem = tick % 480
    shift = 0
    if rem < 240:
        if rem <= 120:
            shift = (rem / 120.0) * (swing_amount * 120)
        else:
            shift = ((240 - rem) / 120.0) * (swing_amount * 120)
    else:
        rem2 = rem - 240
        if rem2 <= 120:
            shift = (rem2 / 120.0) * (swing_amount * 120)
        else:
            shift = ((240 - rem2) / 120.0) * (swing_amount * 120)
    return tick + int(shift)

def parse_grid(grid_str, start_tick, prng, swing=0.0):
    lines = [line.strip() for line in grid_str.strip().split('\n') if line.strip()]
    if not lines: return []
    length = max(len(line) for line in lines)
    
    if length == 16: step_ticks = 120
    elif length == 32: step_ticks = 60
    elif length == 24: step_ticks = 80 
    elif length == 12: step_ticks = 160
    elif length == 48: step_ticks = 40 
    elif length == 8: step_ticks = 240
    else: step_ticks = int(1920 / length)
    
    events = []
    for i in range(length):
        base_tick = start_tick + i * step_ticks
        tick = get_swung_tick(base_tick, swing)
        tick += prng.randint(-3, 3)
        tick = max(0, tick)
        
        for line in lines:
            if i < len(line):
                char = line[i]
                if char in MAP:
                    note = MAP[char]
                    vel = get_velocity(char, prng)
                    events.append((tick, 'note_on', note, vel))
                    events.append((tick + int(step_ticks * 0.8), 'note_off', note, 0))
    return events

def process_crescendo(events, start_tick, end_tick, min_vel, max_vel, notes_to_affect, prng):
    for i, event in enumerate(events):
        tick = event[0]
        msg_type = event[1]
        if msg_type == 'note_on':
            note = event[2]
            if notes_to_affect is None or note in notes_to_affect:
                if start_tick <= tick <= end_tick:
                    progress = (tick - start_tick) / max(1, (end_tick - start_tick))
                    new_vel = int(min_vel + (max_vel - min_vel) * progress)
                    new_vel = max(1, min(127, new_vel + prng.randint(-3, 3)))
                    events[i] = (tick, 'note_on', note, new_vel)

def compile_track(events):
    events.sort(key=lambda x: (x[0], 0 if x[1] == 'set_tempo' else 1))
    
    track = mido.MidiTrack()
    track.append(mido.Message('program_change', program=0, channel=9, time=0))
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    
    last_tick = 0
    for event in events:
        tick = event[0]
        delta = int(tick - last_tick)
        last_tick = tick
        msg_type = event[1]
        
        if msg_type == 'set_tempo':
            track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(event[2]), time=delta))
        elif msg_type == 'note_on':
            track.append(mido.Message('note_on', channel=9, note=event[2], velocity=event[3], time=delta))
        elif msg_type == 'note_off':
            track.append(mido.Message('note_off', channel=9, note=event[2], velocity=0, time=delta))
    return track

def main():
    prng = PRNG(4242)
    
    grids = {}
    
    # 0-7: Intro (Establishing the linear funky motif)
    grids[0] = "C...h...S...h...h...O...S...h...\nK...K.......K...K.......K......."
    grids[1] = "H...h...S...h...h...h...S...h...\nK...K.......K...K.......K......."
    grids[2] = "H...h...S...h...h...O...S...h...\nK...K.......K...K.......K......."
    grids[3] = "H...h...S...h...s.s.S...11112222\nK...K.......K...K..............."
    grids[4] = "C...h...S...h...h...O...S...h...\nK...K.......K...K.......K......."
    grids[5] = "H...h...S...h...h...h...S...h.h.\nK...K.......K...K.......K......."
    grids[6] = "H...h...S...h...h...O...S...h...\nK...K.......K...K.......K......."
    grids[7] = "H...h...S...h...S...S...S.......\nK...K.......K...K...K...K......."
    
    # 8-15: Development 1 (Syncopated toms)
    grids[8]  = "C.s.1.s.2.s.3.s.\nK.K.K.K.K.K.K.K."
    grids[9]  = "H.s.1.s.2.s.3.s.\nK...K.K.K.K.K..."
    grids[10] = "H.s.1.s.2.s.3.s.\nK.K...K...K.K.K."
    grids[11] = "H.s.1.s.22334455\nK...K.K........." 
    grids[12] = "C.s.1.s.2.s.3.s.\nK.K.K.K.K.K.K.K."
    grids[13] = "H.s.1.s.2.s.3.s.\nK...K.K.K.K.K..."
    grids[14] = "H.s.1.s.2.s.3.s.\nK.K...K...K.K.K."
    grids[15] = "11111111222222223333333344445555\nK.......K.......K.......K......." # 32 cols
    
    # 16-23: Groove 2 (Ride Cymbal, Double Kicks)
    grids[16] = "CrrrSrrrbrrrSrrr\nKK.K..KK.K.K..KK"
    grids[17] = "RrrrSrrrbrrrSrrr\nKK.K..KK.K.K..KK"
    grids[18] = "RrrrSrrrbrrrSrrr\nKK.K..KK.K.K..KK"
    grids[19] = "RrrrSrrrb.S.s.s.\nKK.K..KK.K.K.K.K"
    grids[20] = "CrrrSrrrbrrrSrrr\nKK.K..KK.K.K..KK"
    grids[21] = "RrrrSrrrbrrrSrrr\nKK.K..KK.K.K..KK"
    grids[22] = "RrrrSrrrbrrrSrrr\nKK.K..KK.K.K..KK"
    grids[23] = "C.r.r.r.S.......1111222233334444\nK.K...K...K....................." # 32 cols
    
    # 24-31: Breakdown (Ghost notes & Half-time)
    grids[24] = "H.h.h.s.S.h.s.s.\nK.....K.P......." 
    grids[25] = "H.h.s.s.S.h.h.s.\nK.......P.....K." 
    grids[26] = "H.h.h.s.S.h.s.s.\nK.....K.P......." 
    grids[27] = "H.h.s.s.S.s.1.2.\nK.......P......." 
    grids[28] = "H.h.h.s.S.h.s.s.\nK.....K.P......." 
    grids[29] = "H.h.s.s.S.h.h.s.\nK.......P.....K." 
    grids[30] = "H.h.h.s.S.h.s.s.\nK.....K.P......." 
    grids[31] = "ssssssssssssssssssssssssssssssss\nK.......K.......K.......K......." # 32 cols
    
    # 32-39: Climax 1 (Aggressive Crashes)
    for m in range(32, 35):
        grids[m] = "C...D...C...D...\n....S.......S...\nK.K...K.K.K...K."
    grids[35] = "11111111222222223333333344445555\n................................\nK...K...K...K...K...K...K...K..." # 32 cols
    for m in range(36, 39):
        grids[m] = "C.C.D.D.C.C.D.D.\n....S.......S...\nK.K...K.K.K...K."
    grids[39] = "SSSSSS111111222222333333\nK.....K.....K.....K....." # 24 cols (Sextuplets)
    
    # 40-47: Motif Return / Heavy Groove (China & Bells)
    for m in range(40, 43):
        grids[m] = "Z...b...Z...b...\n....S.......S...\nK..K..K..K.K..K."
    grids[43] = "Z...b...Z.......\n....S.....S.S.S.\nK..K..K........."
    for m in range(44, 47):
        grids[m] = "Z...b...Z...b...\n....S.......S...\nK..K..K..K.K..K."
    grids[47] = "Z...............................\nSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS\nK...K...K...K...K...K...K...K..." # 32 cols
    
    # 48-55: Climax 2 (The Big Solo - Fast Linear Patterns & Rolls)
    grids[48] = "SS1SS1SS2SS2SS3SS3SS4SS4\nK.....K.....K.....K....." # 24 cols
    grids[49] = "112112223223334334445445\nK.....K.....K.....K....." # 24 cols
    grids[50] = "S1.S2.S.S1.S2.S.S1.S2.S.S1.S2.S.\n..K..K.K..K..K.K..K..K.K..K..K.K" # 32 cols (Linear chops)
    grids[51] = "S1.S2.S.S1.S2.S.1111222233334444\n..K..K.K..K..K.K................" # 32 cols
    grids[52] = "C.......D.......C.......D.......\n....ssss....ssss....ssss....ssss\nK.......K.......K.......K......." # 32 cols
    grids[53] = "C.......D.......C...............\n....ssss....ssss........SSSSSSSS\nK.......K.......K..............." # 32 cols
    grids[54] = "11111111222222223333333344444444\nK.K.K.K.K.K.K.K.K.K.K.K.K.K.K.K." # 32 cols
    grids[55] = "5555555566666666SSSSSSSSSSSSSSSS\nK.K.K.K.K.K.K.K.K.K.K.K.K.K.K.K." # 32 cols
    
    # 56-59: Finale (Unisons and the Final Hit)
    grids[56] = "C.C.C.C.C.C.C.C.\nS.S.S.S.S.S.S.S.\nK.K.K.K.K.K.K.K." 
    grids[57] = "C...C...C.......\nS...S...S.......\nK...K...K......." 
    grids[58] = "............P..h\n...............s\n................" 
    grids[59] = "C...............\nD...............\nS...............\nK..............." 

    tempos = {
        0: 115, 8: 118, 15: 120, 16: 122, 24: 112, 
        31: 118, 32: 125, 40: 118, 47: 122, 48: 128, 
        56: 115, 57: 105, 58: 90, 59: 115
    }

    swings = {}
    for m in range(0, 16): swings[m] = 0.04
    for m in range(16, 24): swings[m] = 0.01
    for m in range(24, 32): swings[m] = 0.07
    for m in range(32, 60): swings[m] = 0.0
    
    all_events = []
    
    # Generate Time Map
    current_bpm = 120
    for m in range(60):
        if m in tempos:
            current_bpm = tempos[m]
        measure_bpm = max(1, current_bpm + prng.uniform(-1.5, 1.5))
        all_events.append((m * 1920, 'set_tempo', int(measure_bpm)))

    # Generate Notes
    for m in range(60):
        swing_val = swings.get(m, 0.0)
        if m in grids:
            evs = parse_grid(grids[m], m * 1920, prng, swing_val)
            all_events.extend(evs)
            
    # Expressive Crescendos
    process_crescendo(all_events, 31 * 1920, 32 * 1920 - 1, 30, 115, [38], prng)
    process_crescendo(all_events, 31 * 1920, 32 * 1920 - 1, 70, 115, [36], prng)
    
    process_crescendo(all_events, 47 * 1920, 48 * 1920 - 1, 50, 120, [38], prng)
    process_crescendo(all_events, 47 * 1920, 48 * 1920 - 1, 80, 120, [36], prng)
    
    process_crescendo(all_events, 55 * 1920 + 960, 56 * 1920 - 1, 90, 127, None, prng)

    # Compile and Save
    track = compile_track(all_events)
    mid = mido.MidiFile(ticks_per_beat=480)
    mid.tracks.append(track)
    mid.save('solo.mid')

if __name__ == '__main__':
    main()
