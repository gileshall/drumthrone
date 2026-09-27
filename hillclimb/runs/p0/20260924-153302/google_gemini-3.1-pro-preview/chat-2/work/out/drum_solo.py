import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack
import random

# Fix random seed for exact reproducibility
random.seed(42)

# General MIDI Drum Map (Channel 10)
KICK = 36         # Bass Drum 1
SNARE = 38        # Acoustic Snare
SNARE_RIM = 37    # Side Stick / Rim Click
HAT_CLOSED = 42
HAT_PEDAL = 44
HAT_OPEN = 46
TOM_L = 43        # High Floor Tom
TOM_M = 47        # Low-Mid Tom
TOM_H = 50        # High Tom
RIDE = 51         # Ride Cymbal 1
RIDE_BELL = 53
CRASH_1 = 49
CRASH_2 = 57
SPLASH = 55
COWBELL = 56
TIMB_H = 65
TIMB_L = 66

# Global Timeline to collect events
timeline = []

def apply_feel(tick, swing):
    """Applies swing to exact 16th notes (multiples of 120 ticks)"""
    pos = tick % 120
    if pos != 0:
        return tick
    sixteenth_idx = (tick // 120) % 4
    if sixteenth_idx % 2 == 1:
        return tick + swing
    return tick

def add(tick, note, vel):
    """Adds a note event with subtle deterministic velocity humanization."""
    vel = int(vel)
    vel_jitter = random.randint(-3, 3)
    vel = max(1, min(127, vel + vel_jitter))
    timeline.append((int(tick), note, vel))

def intro_tribal(start_bar, num_bars):
    """Driving tribal toms building tension."""
    for b in range(num_bars):
        bar_tick = (start_bar + b) * 1920
        # Floor tom pulse on 8th notes
        for i in range(8):
            vel = 70 + (i % 2) * 10 + (b * 5)
            if i % 4 == 0: vel += 20
            add(bar_tick + i * 240, TOM_L, min(127, vel))
        
        # Syncopated accents on Mid and High toms
        accents = [360, 840, 1320, 1560]
        for a in accents:
            add(bar_tick + a, TOM_M if a % 3 == 0 else TOM_H, 90 + b * 5)
        
        # Kick on 1 and 3
        add(bar_tick + 0, KICK, 110)
        add(bar_tick + 960, KICK, 110)
        
        # Hats with foot on 2 and 4
        add(bar_tick + 480, HAT_PEDAL, 90)
        add(bar_tick + 1440, HAT_PEDAL, 90)
        
        if b == num_bars - 1:
            # Snare Fill leading into the next section
            for i in range(4):
                add(bar_tick + 1440 + i * 120, SNARE, 100 + i * 5)

def purdie_shuffle(start_bar, num_bars, intensity=1.0, ride=False):
    """Classic Half-Time Shuffle Groove."""
    inst = RIDE if ride else HAT_CLOSED
    for b in range(num_bars):
        bar_tick = (start_bar + b) * 1920
        
        for beat in range(4):
            is_fill = (b == num_bars - 1 and beat >= 2)
            if not is_fill:
                beat_tick = bar_tick + beat * 480
                add(beat_tick, inst, int(90 * intensity))
                add(beat_tick + 320, inst, int(70 * intensity))  # 3rd triplet
                
                if beat != 2:
                    add(beat_tick + 160, SNARE, int(40 * intensity)) # Ghost snare
                else:
                    # Lay back slightly on the heavy backbeat (beat 3)
                    add(beat_tick + 10, SNARE, int(115 * intensity))
                    add(beat_tick + 160, SNARE, int(45 * intensity))
                    
        # Kick pattern
        add(bar_tick, KICK, int(100 * intensity))
        add(bar_tick + 800, KICK, int(90 * intensity)) # 'a' of 2
        if b % 2 == 1:
            add(bar_tick + 1760, KICK, int(85 * intensity))
            
        # Hat pedal on 2 and 4 (beats 1 and 3 in 0-index)
        if ride:
            add(bar_tick + 480, HAT_PEDAL, int(80 * intensity))
            add(bar_tick + 1440, HAT_PEDAL, int(80 * intensity))
            
        # Fill on last bar
        if b == num_bars - 1:
            for i in range(6):
                note = TOM_H if i < 2 else (TOM_M if i < 4 else TOM_L)
                add(bar_tick + 960 + i * 160, note, int((80 + i * 5) * intensity))
        
        # Crash downbeat
        if b == 0:
            add(bar_tick, CRASH_1, int(110 * intensity))

def linear_groove(start_bar, num_bars):
    """Motif A: Syncopated 16th-note linear drum pattern."""
    pattern = [
        (0, KICK, 110), (1, HAT_CLOSED, 60), (2, SNARE, 50), (3, KICK, 90),
        (4, SNARE, 115), (5, HAT_CLOSED, 60), (6, KICK, 90), (7, SNARE, 50),
        (8, HAT_CLOSED, 70), (9, KICK, 100), (10, SNARE, 115), (11, HAT_CLOSED, 60),
        (12, KICK, 90), (13, SNARE, 50), (14, HAT_OPEN, 90), (15, HAT_PEDAL, 90)
    ]
    
    for b in range(num_bars):
        bar_tick = (start_bar + b) * 1920
        is_fill = (b == num_bars - 1)
        
        if is_fill:
            p = pattern[:8] + [
                (8, SNARE, 100), (9, SNARE, 100), (10, TOM_H, 110), (11, TOM_H, 110),
                (12, TOM_M, 115), (13, TOM_M, 115), (14, TOM_L, 120), (15, TOM_L, 120)
            ]
        elif b % 2 == 1:
            p = pattern[:12] + [
                (12, TOM_H, 100), (13, TOM_H, 90), (14, TOM_M, 100), (15, TOM_L, 110)
            ]
        else:
            p = pattern
            
        for step, note, vel in p:
            tick = bar_tick + step * 120
            # Lay back backbeats
            if note == SNARE and step in (4, 12):
                tick += 12
            else:
                tick = apply_feel(tick, swing=18)
            
            if step == 15 and note == HAT_PEDAL:
                add(bar_tick + 1920, HAT_PEDAL, vel)
            else:
                add(tick, note, vel)
                
        if b == 0:
            add(bar_tick, CRASH_1, 110)

def linear_groove_dev(start_bar, num_bars):
    """Motif A Developed: Orchestrated across ride, bell, and toms."""
    pattern = [
        (0, KICK, 115), (1, RIDE, 70), (2, TOM_H, 60), (3, KICK, 95),
        (4, SNARE, 120), (5, RIDE, 70), (6, KICK, 95), (7, TOM_M, 60),
        (8, RIDE_BELL, 85), (9, KICK, 105), (10, SNARE, 120), (11, RIDE, 70),
        (12, KICK, 95), (13, TOM_L, 60), (14, HAT_OPEN, 95), (15, HAT_PEDAL, 95)
    ]
    
    for b in range(num_bars):
        bar_tick = (start_bar + b) * 1920
        is_fill = (b == num_bars - 1)
        
        if is_fill:
            p = pattern[:8] + [
                (8, SNARE, 105), (9, SNARE, 105), (10, TOM_H, 115), (11, TOM_H, 115),
                (12, TOM_M, 120), (13, TOM_M, 120), (14, TOM_L, 125), (15, TOM_L, 125)
            ]
        elif b % 2 == 1:
            p = pattern[:12] + [
                (12, TOM_H, 105), (13, TOM_H, 95), (14, TOM_M, 105), (15, TOM_L, 115)
            ]
        else:
            p = pattern
            
        for step, note, vel in p:
            tick = bar_tick + step * 120
            if note == SNARE and step in (4, 12):
                tick += 12
            else:
                tick = apply_feel(tick, swing=18)
            
            if step == 15 and note == HAT_PEDAL:
                add(bar_tick + 1920, HAT_PEDAL, vel)
            else:
                add(tick, note, vel)
                
        if b == 0:
            add(bar_tick, CRASH_1, 120)

def latin_break(start_bar, num_bars):
    """Percussive Songo/Cascara break using cowbell, timbales and rim clicks."""
    cascara = [0, 3, 4, 7, 8, 11, 12, 14] 
    tumbao_kick = [6, 12]
    lh_steps = [2, 7, 10, 15] 
    
    for b in range(num_bars):
        bar_tick = (start_bar + b) * 1920
        is_fill = (b == num_bars - 1)
        inst = COWBELL if b < num_bars // 2 else RIDE_BELL
        
        if not is_fill:
            for step in cascara:
                add(bar_tick + step * 120, inst, 100)
            for step in tumbao_kick:
                # Push the beat slightly ahead for Latin momentum
                add(bar_tick + step * 120 - 10, KICK, 110)
            for step in lh_steps:
                note = SNARE_RIM if step != 15 else TOM_H
                add(bar_tick + step * 120, note, 90)
            for beat in range(4):
                add(bar_tick + beat * 480, HAT_PEDAL, 80)
                
            if b == 0:
                add(bar_tick, CRASH_2, 115)
            elif b % 2 == 1:
                add(bar_tick, SPLASH, 100)
        else:
            # Huge timbale/snare fill
            for i in range(16):
                note = TIMB_H if i % 2 == 0 else TIMB_L
                if i >= 12: note = SNARE 
                add(bar_tick + i * 120, note, min(127, 80 + i * 3))
            add(bar_tick, KICK, 110)

def climax(start_bar, num_bars):
    """Peak intensity: fast double bass, heavy half-time snare, sweeping crashes."""
    for b in range(num_bars):
        bar_tick = (start_bar + b) * 1920
        is_fill = ((b + 1) % 4 == 0)
        
        # Heavy cymbal wall
        for i in range(8):
            if is_fill and i >= 6: continue 
            # Slight push ahead of beat for aggressive feel
            tick = bar_tick + i * 240 - 5
            add(tick, CRASH_1 if i % 2 == 0 else CRASH_2, 115)
            
        # Half-time backbeat
        add(bar_tick + 960 - 5, SNARE, 127)
        if not is_fill:
            add(bar_tick + 1680 - 5, SNARE, 120)
        
        # Intense double bass drumming
        if b % 2 == 0:
            for i in range(12): # 16th note triplets for beats 1 & 2
                add(bar_tick + i * 80, KICK, 115)
            if not is_fill:
                add(bar_tick + 1440, KICK, 110)
                add(bar_tick + 1560, KICK, 110)
        else:
            kicks = [0, 120, 240, 360, 480, 720, 840, 1200, 1320, 1440, 1560]
            for k in kicks:
                if is_fill and k >= 1440: continue
                add(bar_tick + k, KICK, 115)
                
        if is_fill:
            # 32nd note barrage on last beat
            for i in range(8):
                note = TOM_H if i < 2 else (TOM_M if i < 4 else (TOM_L if i < 6 else SNARE))
                add(bar_tick + 1440 + i * 60, note, 125)

def outro(start_bar, num_bars):
    """Dramatic drum fills leading to final ritardando and crash."""
    for b in range(num_bars):
        bar_tick = (start_bar + b) * 1920
        if b < num_bars - 1:
            # Huge syncopated band hits
            hits = [0, 360, 840, 1200, 1560]
            for h in hits:
                add(bar_tick + h, CRASH_1, 120)
                add(bar_tick + h, KICK, 120)
                add(bar_tick + h, SNARE, 120)
            
            # Melodic tom responses
            add(bar_tick + 600, TOM_H, 110)
            add(bar_tick + 720, TOM_M, 110)
            add(bar_tick + 1320, TOM_M, 110)
            add(bar_tick + 1440, TOM_L, 110)
        else:
            # Final massive snare/kick roll peaking precisely into beat 4
            for i in range(18): # Covers ticks 0 to 1360
                add(bar_tick + i * 80, SNARE, min(127, 80 + int(i * 2.5)))
                add(bar_tick + i * 80, KICK, 100)
            
            # The Final Hit! (Beat 4)
            add(bar_tick + 1440, CRASH_1, 127)
            add(bar_tick + 1440, CRASH_2, 127)
            add(bar_tick + 1440, KICK, 127)
            add(bar_tick + 1440, HAT_PEDAL, 127)

def is_foot(note):
    return note in (35, 36, 44)

def finalize_events():
    """Ensures absolute playability: max 2 hands and 2 feet at any instant."""
    by_tick = {}
    for tick, note, vel in timeline:
        by_tick.setdefault(tick, []).append((note, vel))
        
    final_events = []
    for tick in sorted(by_tick.keys()):
        notes = by_tick[tick]
        hands, feet = [], []
        for n, v in notes:
            if is_foot(n): feet.append((n, v))
            else: hands.append((n, v))
                
        # Deduplicate identical instruments on exact same tick
        def deduplicate(n_list):
            d = {}
            for n, v in n_list:
                d[n] = max(d.get(n, 0), v)
            return list(d.items())
            
        hands = deduplicate(hands)
        feet = deduplicate(feet)
        
        # Retain only the hardest hits if over limits
        hands.sort(key=lambda x: x[1], reverse=True)
        feet.sort(key=lambda x: x[1], reverse=True)
        
        for n, v in hands[:2]: final_events.append((tick, n, v))
        for n, v in feet[:2]: final_events.append((tick, n, v))
            
    return final_events

def bpm_to_tempo(bpm):
    return int(60_000_000 / bpm)

def write_midi(final_events, filename="solo.mid"):
    mid = MidiFile(ticks_per_beat=480)
    
    # Tempo track
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tempo_track.append(MetaMessage('set_tempo', tempo=bpm_to_tempo(120), time=0))
    
    # Smooth musical ritardando across the final 3 bars
    last_tempo_tick = 0
    rit_start = 57 * 1920
    for b in range(12): 
        tick = rit_start + b * 480
        delta = int(tick - last_tempo_tick)
        tempo_bpm = 120 - (b * 3) # Drops smoothly to ~84 BPM
        tempo_track.append(MetaMessage('set_tempo', tempo=bpm_to_tempo(tempo_bpm), time=delta))
        last_tempo_tick = tick

    # Note track
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    
    # Generate Note On / Note Off pairings (fixed percussion duration)
    midi_events = []
    for tick, note, vel in final_events:
        midi_events.append({'type': 'on', 'time': tick, 'note': note, 'vel': vel})
        midi_events.append({'type': 'off', 'time': tick + 60, 'note': note, 'vel': 0})
        
    # Order Offs before Ons to ensure cleanly triggered resonances
    midi_events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))
    
    last_time = 0
    for ev in midi_events:
        delta = int(ev['time'] - last_time)
        msg_type = 'note_on' if ev['type'] == 'on' else 'note_off'
        track.append(Message(msg_type, channel=9, note=ev['note'], velocity=ev['vel'], time=delta))
        last_time = ev['time']
        
    # Allow cymbals to ring out naturally by padding silence at track end
    track.append(MetaMessage('text', text='End', time=1920))
    
    mid.save(filename)

if __name__ == '__main__':
    # Constructing a structured, deeply composed 60-bar drum solo (~2 minutes)
    intro_tribal(0, 4)
    purdie_shuffle(4, 8)
    linear_groove(12, 8)
    purdie_shuffle(20, 8, intensity=1.08, ride=True)
    linear_groove_dev(28, 8)
    latin_break(36, 8)
    climax(44, 12)
    outro(56, 4)
    
    events = finalize_events()
    write_midi(events, "solo.mid")
