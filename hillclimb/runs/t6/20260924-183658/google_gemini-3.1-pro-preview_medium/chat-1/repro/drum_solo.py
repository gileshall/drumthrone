import mido
import random

# Fixed seed for deterministic output
random.seed(42)

# Drum kit mapping (General MIDI)
K = 36      # Kick
S = 38      # Snare
CH = 42     # Closed Hi-Hat
OH = 46     # Open Hi-Hat
R = 51      # Ride Cymbal
RB = 53     # Ride Bell
C1 = 49     # Crash 1
C2 = 57     # Crash 2
T1 = 48     # High Tom
T2 = 45     # Mid Tom
T3 = 43     # Low Tom
T4 = 41     # Floor Tom
SPL = 55    # Splash
CHN = 52    # China

events = []

def hit(beat, note, vel, duration=0.1):
    if vel <= 0:
        return
    # Humanize timing and velocity
    tick = beat * 480
    tick += random.gauss(0, 6)
    tick = max(0, int(tick))
    
    vel = max(1, min(127, int(vel + random.gauss(0, 5))))
    
    events.append((tick, 'on', note, vel))
    events.append((tick + int(duration * 480), 'off', note, 0))

def flam(beat, note, vel):
    hit(beat - 0.04, note, vel * 0.5)
    hit(beat, note, vel)

def roll(start_beat, end_beat, note, start_vel, end_vel, notes_per_beat=8):
    total_beats = end_beat - start_beat
    num_hits = int(total_beats * notes_per_beat)
    for i in range(num_hits):
        b = start_beat + i / notes_per_beat
        v = start_vel + (end_vel - start_vel) * (i / max(1, num_hits - 1))
        # Alternating accent to mimic double strokes or strong singles
        if i % 2 == 1: 
            v *= 0.85
        hit(b, note, v)

def play_groove(bar, type='hh'):
    sb = bar * 4
    cymbal = CH if type == 'hh' else (R if type == 'ride' else C1)
    
    # Hand 1: Cymbals
    for i in range(8):
        v = 90 if i % 2 == 0 else 65
        if type == 'crash':
            cymbal = C1 if i % 2 == 0 else C2
            v = 110
        hit(sb + i * 0.5, cymbal, v)
        
    # Hand 2: Snare backbeat & ghosts
    hit(sb + 1, S, 115)
    hit(sb + 3, S, 115)
    
    if type != 'crash':
        ghosts = [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75]
        for g in ghosts:
            if random.random() < 0.35:
                hit(sb + g, S, random.randint(30, 45))

    # Foot: Kicks
    hit(sb, K, 105)
    k_pattern = random.choice([
        [1.5], [2.5], [1.5, 2.5], [1.5, 3.5], [2.5, 3.5], [1.75, 2.5], [2.5, 3.75]
    ])
    for k in k_pattern:
        hit(sb + k, K, 105)

def linear_fill(sb, length_beats):
    patterns = [
        [(S, 110), (S, 50), (K, 110)], 
        [(S, 110), (T1, 100), (T2, 100), (K, 110)], 
        [(T1, 110), (T3, 100), (K, 110), (K, 100)], 
        [(S, 110), (S, 50), (S, 60), (S, 50), (K, 110), (K, 100)],
        [(T2, 100), (T4, 100), (K, 110)]
    ]
    t = sb
    end = sb + length_beats
    while t < end - 0.05:
        pat = random.choice(patterns)
        dur = 0.25 # 16th notes
        if random.random() < 0.3: 
            dur = 1/6 # sextuplets
        for note, vel in pat:
            if t >= end - 0.05: 
                break
            hit(t, note, vel)
            t += dur

def generate_solo():
    for bar in range(60):
        sb = bar * 4
        
        if bar < 4:
            # Intro: cymbal swells, sparse kick heartbeat
            hit(sb, K, 60 + bar * 10)
            hit(sb + 2, K, 50 + bar * 10)
            if bar % 2 == 1:
                roll(sb + 2, sb + 4, C1, 30, 80 + bar * 10, 8)
        
        elif bar < 8:
            # Snare build up
            roll(sb, sb + 4, S, 40 + (bar - 4) * 15, 60 + (bar - 4) * 15, notes_per_beat=random.choice([4, 6, 8]))
            hit(sb, K, 90)
            hit(sb + 2, K, 90)
            if bar == 7:
                roll(sb + 2, sb + 4, T2, 80, 110, 8)
        
        elif bar < 16:
            # Motif A: Hi-hat Groove
            if bar == 8 or bar == 12: 
                hit(sb, C1, 110)
            if bar % 4 == 3:
                play_groove(bar, type='hh')
                linear_fill(sb + 2, 2)
            else:
                play_groove(bar, type='hh')
        
        elif bar < 24:
            # Motif A varied: Ride Cymbal Groove
            if bar == 16 or bar == 20: 
                hit(sb, C2, 110)
            if bar % 4 == 3:
                play_groove(bar, type='ride')
                linear_fill(sb + 2, 2)
            else:
                play_groove(bar, type='ride')
        
        elif bar < 32:
            # Motif B: Tribal toms
            if bar == 24: 
                hit(sb, C1, 110)
            for i in range(16):
                b = sb + i * 0.25
                if i % 4 == 0: 
                    hit(b, K, 115)
                    hit(b, T4, 110)
                elif i % 2 == 0: 
                    hit(b, T2, 95)
                else: 
                    hit(b, T1, 85)
            if bar % 4 == 3:
                linear_fill(sb + 2, 2)
        
        elif bar < 40:
            # Motif A extreme: Heavy Crash groove
            if bar == 32: 
                hit(sb, SPL, 110)
            if bar % 4 == 3:
                linear_fill(sb, 4)
            else:
                play_groove(bar, type='crash')
                
        elif bar < 48:
            # Complex syncopation / Breaks
            if bar == 40: 
                hit(sb, CHN, 110)
            for i in range(16):
                b = sb + i * 0.25
                r = random.random()
                if r < 0.15:
                    flam(b, S, 110)
                    hit(b, K, 105)
                    if r < 0.05: 
                        hit(b, random.choice([C1, C2]), 105)
                elif r < 0.4:
                    hit(b, S, random.randint(30, 50))
                
                if random.random() < 0.2:
                    hit(b, K, 95)
                    
        elif bar < 56:
            # Climax rolls around the kit
            if bar == 48: 
                hit(sb, C1, 110)
                hit(sb, C2, 110)
            target = [S, T1, T2, T3, T4][(bar - 48) % 5]
            roll(sb, sb + 3, target, 85, 120, notes_per_beat=8)
            linear_fill(sb + 3, 1)
            # Four on the floor to drive it
            for i in range(4):
                hit(sb + i, K, 110)
                
        elif bar < 59:
            # Fast singles & full kit chaos
            for i in range(4):
                b = sb + i
                hit(b, C1 if i % 2 == 0 else C2, 115)
                hit(b, K, 115)
                hit(b + 0.5, K, 115)
            linear_fill(sb, 4)
            
        elif bar == 59:
            # The Final Landing
            roll(sb, sb + 2, S, 100, 127, 8)
            
            # Big syncopated hits to close
            hit(sb + 2, S, 127)
            hit(sb + 2, C1, 120)
            hit(sb + 2, K, 120)
            
            hit(sb + 2.5, S, 127)
            hit(sb + 2.5, C2, 120)
            hit(sb + 2.5, K, 120)
            
            # Downbeat of imaginary bar 61
            hit(sb + 3, S, 127)
            hit(sb + 3, C1, 127)
            hit(sb + 3, C2, 127)
            hit(sb + 3, K, 127)

def main():
    generate_solo()
    
    # Sort events by tick, then note_off before note_on for same tick
    events.sort(key=lambda x: (x[0], x[1] == 'on'))
    
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Tempo 120 BPM
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    
    last_tick = 0
    for ev in events:
        tick, msg_type, note, vel = ev
        delta = tick - last_tick
        last_tick = tick
        
        # Channel 9 in mido is MIDI Channel 10
        if msg_type == 'on':
            track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
        else:
            track.append(mido.Message('note_off', channel=9, note=note, velocity=vel, time=delta))
            
    mid.save('solo.mid')

if __name__ == '__main__':
    main()
