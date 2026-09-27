import mido
import random

def build_solo():
    rng = random.Random(42)
    events = []
    
    # GM Drum Map
    KICK = 36
    SNARE = 38
    RIM = 37
    HAT_C = 42
    HAT_O = 46
    HAT_P = 44
    TOM1 = 50
    TOM2 = 48
    TOM3 = 45
    TOM4 = 43
    CRASH1 = 49
    CRASH2 = 57
    RIDE = 51
    BELL = 53
    SPLASH = 55
    CHINA = 52
    
    # Tick resolutions (480 ticks per quarter note)
    TICK_Q = 480
    TICK_8 = 240
    TICK_16 = 120
    TICK_32 = 60
    TICK_8T = 160
    TICK_16T = 80
    
    current_tick = 0
    
    def add_hit(tick, note, vel):
        # Humanize timing and velocity
        t = max(0, tick + int(rng.gauss(0, 5)))
        v = max(1, min(127, vel + int(rng.gauss(0, 5))))
        events.append((t, note, v))

    def play_intro(start_tick, bars):
        tick = start_tick
        for b in range(bars):
            for beat in range(4):
                add_hit(tick, HAT_C, 60)
                add_hit(tick + TICK_8, HAT_C, 45)
                
                if beat == 0:
                    add_hit(tick, KICK, 75)
                elif beat == 1:
                    add_hit(tick, RIM, 85)
                    add_hit(tick + TICK_8 + TICK_16, KICK, 55)
                elif beat == 2:
                    add_hit(tick, KICK, 65)
                    add_hit(tick + TICK_8, KICK, 65)
                elif beat == 3:
                    add_hit(tick, RIM, 85)
                    if b % 2 == 1 and beat == 3:
                        add_hit(tick + TICK_8, TOM1, 60)
                        add_hit(tick + TICK_8 + TICK_16, TOM2, 60)
                tick += TICK_Q
        return tick

    def play_groove(start_tick, bars):
        tick = start_tick
        for b in range(bars):
            for beat in range(4):
                # Ride cymbal ostinato
                add_hit(tick, RIDE, 75)
                add_hit(tick + TICK_8, RIDE, 55)
                
                # Snare ghost notes and kick
                if beat in [0, 2]:
                    add_hit(tick + TICK_16, SNARE, 25)
                    add_hit(tick + TICK_8 + TICK_16, SNARE, 30)
                    add_hit(tick, KICK, 85)
                    if beat == 2 and b % 2 == 0:
                        add_hit(tick + TICK_8, KICK, 75)
                elif beat in [1, 3]:
                    add_hit(tick, SNARE, 105) # Backbeat
                    add_hit(tick + TICK_16, SNARE, 30)
                    add_hit(tick + TICK_8 + TICK_16, KICK, 65)
                
                # Fill at end of phrases
                if (b + 1) % 4 == 0 and beat == 3:
                    add_hit(tick, SNARE, 95)
                    add_hit(tick + TICK_16, TOM1, 85)
                    add_hit(tick + TICK_8, TOM2, 90)
                    add_hit(tick + TICK_8 + TICK_16, TOM4, 95)
                    
                tick += TICK_Q
        return tick

    def play_linear_fills(start_tick, bars):
        tick = start_tick
        for b in range(bars):
            if b % 2 == 0:
                for beat in range(4):
                    if beat < 3:
                        # Sextuplets around the kit: R L K K R L
                        add_hit(tick, TOM1, 95)
                        add_hit(tick + TICK_16T, TOM2, 85)
                        add_hit(tick + 2*TICK_16T, KICK, 95)
                        add_hit(tick + 3*TICK_16T, KICK, 85)
                        add_hit(tick + 4*TICK_16T, TOM3, 95)
                        add_hit(tick + 5*TICK_16T, TOM4, 85)
                    else:
                        add_hit(tick, SNARE, 115)
                        add_hit(tick + TICK_8, CRASH1, 115)
                        add_hit(tick + TICK_8, KICK, 105)
                    tick += TICK_Q
            else:
                for beat in range(4):
                    if beat < 2:
                        # 32nd note snare build
                        for i in range(8):
                            add_hit(tick + i*TICK_32, SNARE, 50 + i*5)
                    elif beat == 2:
                        # Flams on toms
                        add_hit(tick, TOM1, 105)
                        add_hit(tick + 15, TOM2, 85) 
                        add_hit(tick + TICK_8, TOM3, 105)
                        add_hit(tick + TICK_8 + 15, TOM4, 85)
                    else:
                        add_hit(tick, KICK, 115)
                        add_hit(tick, CRASH2, 115)
                        add_hit(tick + TICK_8, SNARE, 115)
                    tick += TICK_Q
        return tick

    def play_breakdown(start_tick, bars):
        tick = start_tick
        for b in range(bars):
            for beat in range(4):
                # Paradiddle groove: R L R R L R L L
                hits = [
                    (BELL, KICK), (SNARE, None), (BELL, None), (BELL, None)
                ] if beat % 2 == 0 else [
                    (SNARE, None), (BELL, KICK), (SNARE, None), (SNARE, None)
                ]
                
                for i, (hand, foot) in enumerate(hits):
                    t = tick + i*TICK_16
                    if hand == SNARE:
                        vel = 115 if (beat in [1, 3] and i == 0) else 35
                    else:
                        vel = 85
                    add_hit(t, hand, vel)
                    if foot:
                        add_hit(t, foot, 95)
                tick += TICK_Q
        return tick

    def play_tribal(start_tick, bars):
        tick = start_tick
        for b in range(bars):
            for beat in range(4):
                # Heavy floor tom driving groove
                add_hit(tick, TOM4, 105)
                add_hit(tick + TICK_16, TOM3, 75)
                add_hit(tick + TICK_8, TOM4, 95)
                add_hit(tick + TICK_8 + TICK_16, TOM3, 75)
                
                if beat in [1, 3]:
                    add_hit(tick, SNARE, 115)
                
                if beat == 0:
                    add_hit(tick, KICK, 115)
                if beat == 2 and b % 2 == 1:
                    add_hit(tick + TICK_8, KICK, 95)
                    
                if b == bars - 1 and beat == 3:
                    for i in range(4):
                        add_hit(tick + i*TICK_16, SNARE, 85 + i*10)
                tick += TICK_Q
        return tick
        
    def play_climax(start_tick, bars):
        tick = start_tick
        for b in range(bars):
            for beat in range(4):
                add_hit(tick, CRASH1 if beat % 2 == 0 else CHINA, 115)
                add_hit(tick, KICK, 115)
                add_hit(tick + TICK_16, KICK, 95)
                add_hit(tick + TICK_8, KICK, 115)
                add_hit(tick + TICK_8 + TICK_16, KICK, 95)
                
                add_hit(tick + TICK_8, SNARE, 120)
                
                if b == bars - 1 and beat >= 2:
                    # 32nd note roll round the toms
                    for i in range(8):
                        t = tick + i*TICK_32
                        if i < 2: n = TOM1
                        elif i < 4: n = TOM2
                        elif i < 6: n = TOM3
                        else: n = TOM4
                        add_hit(t, n, 105 + i*3)
                tick += TICK_Q
        return tick

    def play_ending(start_tick):
        tick = start_tick
        # Big triplet crescendo build up
        for beat in range(4):
            for i in range(6):
                t = tick + i*TICK_16T
                vol = 70 + int((beat*6 + i) * (50/24))
                add_hit(t, SNARE, vol)
                if i % 2 == 0:
                    add_hit(t, KICK, vol)
            tick += TICK_Q
            
        # The final hit
        add_hit(tick, CRASH1, 127)
        add_hit(tick, CRASH2, 127)
        add_hit(tick, KICK, 127)
        add_hit(tick, SNARE, 127)
        
        return tick + TICK_Q * 4

    # Sequence of the solo (total ~2 mins at 120bpm)
    t = play_intro(current_tick, 8)
    t = play_groove(t, 16)
    t = play_linear_fills(t, 8)
    t = play_breakdown(t, 8)
    t = play_tribal(t, 10)
    t = play_climax(t, 10)
    t = play_ending(t)
    
    # Sort absolute events
    events.sort(key=lambda x: x[0])
    
    mid = mido.MidiFile(ticks_per_beat=TICK_Q)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # 120 BPM
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    
    # Generate NoteOn and NoteOff events
    midi_events = []
    for tick, note, vel in events:
        midi_events.append((tick, 'note_on', note, vel))
        midi_events.append((tick + 40, 'note_off', note, 0)) # Slight sustain for realism
        
    midi_events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))
    
    last_tick = 0
    for tick, msg_type, note, vel in midi_events:
        delta = tick - last_tick
        if msg_type == 'note_on':
            track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
        else:
            track.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=delta))
        last_tick = tick

    mid.save('solo.mid')

if __name__ == '__main__':
    build_solo()
