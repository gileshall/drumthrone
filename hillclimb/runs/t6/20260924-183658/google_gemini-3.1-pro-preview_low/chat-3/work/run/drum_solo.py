import mido
import random
import math

def generate_drum_solo():
    random.seed(42)
    
    # MIDI settings
    ticks_per_beat = 480
    tempo_bpm = 140
    # 2 minutes at 140 BPM = 280 beats = 70 bars of 4/4
    total_bars = 70
    
    events = [] # (time_ticks, note, velocity, duration)
    
    # GM Drum notes
    KICK = 36
    SNARE = 38
    SNARE_GHOST = 38
    SNARE_RIM = 37
    CHH = 42
    OHH = 46
    PHH = 44
    RIDE = 51
    RIDE_BELL = 53
    CRASH1 = 49
    CRASH2 = 57
    TOMS = [50, 48, 47, 45, 43, 41] # High to low
    
    def add_note(beat, note, vel):
        # Humanize timing (-15 to +15 ticks) and velocity (-10 to +10)
        t_offset = int(random.gauss(0, 5))
        t_offset = max(-20, min(20, t_offset))
        time_ticks = int(beat * ticks_per_beat) + t_offset
        
        v_offset = int(random.gauss(0, 5))
        velocity = max(1, min(127, vel + v_offset))
        
        events.append((time_ticks, note, velocity))
    
    # Section generators
    def play_groove(start_bar, num_bars, cymbal=CHH, intensity=1.0):
        for bar in range(start_bar, start_bar + num_bars):
            base_beat = bar * 4
            # Ride/Hat pattern
            for eighth in range(8):
                b = base_beat + eighth * 0.5
                vel = int(80 * intensity) if eighth % 2 == 0 else int(60 * intensity)
                # occasional open hat on the 'and'
                if cymbal == CHH and eighth == 7 and random.random() < 0.2:
                    add_note(b, OHH, vel)
                    add_note(b + 0.5, PHH, 80) # close on next downbeat
                else:
                    add_note(b, cymbal, vel)
            
            # Kick
            add_note(base_beat, KICK, int(100 * intensity))
            add_note(base_beat + 2.5, KICK, int(90 * intensity))
            if random.random() < 0.3:
                add_note(base_beat + 3.5, KICK, int(85 * intensity))
                
            # Snare
            add_note(base_beat + 1, SNARE, int(105 * intensity))
            add_note(base_beat + 3, SNARE, int(105 * intensity))
            
            # Ghost notes
            if random.random() < 0.7:
                add_note(base_beat + 1.75, SNARE_GHOST, int(40 * intensity))
            if random.random() < 0.5:
                add_note(base_beat + 2.25, SNARE_GHOST, int(35 * intensity))
            if random.random() < 0.4:
                add_note(base_beat + 3.75, SNARE_GHOST, int(45 * intensity))
                
            # Occasional crash
            if bar % 4 == 0:
                add_note(base_beat, CRASH1, int(110 * intensity))

    def play_fill(start_bar, num_bars):
        for bar in range(start_bar, start_bar + num_bars):
            base_beat = bar * 4
            # 16th note linear fill
            notes = [SNARE, KICK, TOMS[0], TOMS[1], SNARE, KICK, TOMS[2], TOMS[3],
                     SNARE, SNARE, TOMS[4], TOMS[4], TOMS[5], TOMS[5], KICK, KICK]
            for i in range(16):
                b = base_beat + i * 0.25
                n = notes[i % len(notes)]
                if n == SNARE:
                    vel = 90 + int(i * 1.5)
                elif n == KICK:
                    vel = 110
                else:
                    vel = 85 + int(i * 2)
                add_note(b, n, min(127, vel))
            add_note(base_beat + 4, CRASH1, 120)
            add_note(base_beat + 4, KICK, 110)

    def play_snare_crescendo(start_bar, num_bars):
        start_beat = start_bar * 4
        total_beats = num_bars * 4
        for i in range(total_beats * 4): # 16th notes
            b = start_beat + i * 0.25
            vel = int(30 + (97 * (i / (total_beats * 4))))
            add_note(b, SNARE, vel)
            if i % 8 == 0:
                add_note(b, KICK, 80)
        add_note(start_beat + total_beats, CRASH2, 127)
        add_note(start_beat + total_beats, KICK, 127)

    # Structure
    # 0-3: Intro roll
    play_snare_crescendo(0, 4)
    # 4-19: Groove A
    play_groove(4, 15, CHH, 0.8)
    play_fill(19, 1)
    # 20-35: Groove B (Ride)
    play_groove(20, 15, RIDE, 0.95)
    play_fill(35, 1)
    # 36-43: Tom solo / Fills
    for i in range(36, 44, 2):
        play_fill(i, 1)
        play_groove(i+1, 1, RIDE_BELL, 1.1)
    # 44-59: High intensity groove
    play_groove(44, 15, OHH, 1.1)
    play_fill(59, 1)
    # 60-67: Snare crescendo into massive fill
    play_snare_crescendo(60, 4)
    play_fill(64, 4)
    # 68-69: Final hits
    add_note(68 * 4, CRASH1, 127)
    add_note(68 * 4, CRASH2, 127)
    add_note(68 * 4, KICK, 127)
    add_note(68 * 4 + 2, SNARE, 127)
    add_note(68 * 4 + 2, TOMS[5], 127)
    add_note(69 * 4, CRASH1, 127)
    add_note(69 * 4, KICK, 127)
    
    # Process events
    events.sort(key=lambda x: x[0])
    
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Tempo track
    tempo = mido.bpm2tempo(tempo_bpm)
    track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    
    # Convert absolute times to delta times
    last_time = 0
    for e in events:
        time_ticks, note, velocity = e
        delta = max(0, time_ticks - last_time)
        track.append(mido.Message('note_on', channel=9, note=note, velocity=velocity, time=delta))
        # Note off immediately after (since they are drums)
        track.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=10))
        last_time = time_ticks + 10
        
    mid.save('solo.mid')

if __name__ == '__main__':
    generate_drum_solo()
