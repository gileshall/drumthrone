import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage
import random
import math

def generate_solo():
    random.seed(42)
    
    ticks_per_beat = 480
    bpm = 120
    total_bars = 60 # 60 bars at 120bpm = 2 minutes
    
    # Instruments
    BD = 36
    SD = 38
    CH = 42
    PH = 44
    OH = 46
    CR = 49
    RD = 51
    RB = 53
    T1 = 50
    T2 = 48
    T3 = 45
    T4 = 41
    
    events = [] # (abs_tick, pitch, velocity, duration)
    
    def add_note(tick, pitch, vel, dur=60):
        # Humanize
        t = tick + int(random.gauss(0, 5))
        v = min(127, max(1, vel + int(random.gauss(0, 8))))
        events.append((t, pitch, v, dur))
        
    def add_flam(tick, pitch, vel):
        add_note(tick - 15, pitch, int(vel * 0.4), 30)
        add_note(tick, pitch, vel, 60)
        
    def add_roll(start_tick, end_tick, pitch, start_vel, end_vel, resolution=60):
        # resolution in ticks, e.g. 60 = 32nd note
        curr = start_tick
        while curr < end_tick:
            progress = (curr - start_tick) / (end_tick - start_tick)
            v = int(start_vel + (end_vel - start_vel) * progress)
            add_note(curr, pitch, v, resolution - 5)
            curr += resolution

    # Sections
    for bar in range(total_bars):
        bar_start = bar * ticks_per_beat * 4
        
        # Determine section
        if bar < 8:
            # Intro groove building up
            intensity = bar / 8
            for b in range(4):
                beat_tick = bar_start + b * ticks_per_beat
                add_note(beat_tick, CH, 70 + int(20*intensity))
                add_note(beat_tick + ticks_per_beat//2, CH, 50)
                
                if b in [0, 2]:
                    add_note(beat_tick, BD, 90)
                if b in [1, 3]:
                    add_note(beat_tick, SD, 100)
                    
                # Ghost notes
                if random.random() < 0.3:
                    add_note(beat_tick + int(ticks_per_beat * 0.75), SD, 30)
                    
        elif bar < 24:
            # Syncopated groove
            for b in range(4):
                beat_tick = bar_start + b * ticks_per_beat
                if b == 0:
                    add_note(beat_tick, CR if bar % 4 == 0 else RD, 110 if bar % 4 == 0 else 80)
                    add_note(beat_tick, BD, 100)
                else:
                    add_note(beat_tick, RD, 80)
                    add_note(beat_tick + ticks_per_beat//2, RD, 60)
                
                if b == 1:
                    add_note(beat_tick, SD, 105)
                if b == 3:
                    add_note(beat_tick, SD, 110)
                    
                # Kick variations
                if b == 2 and random.random() < 0.5:
                    add_note(beat_tick + int(ticks_per_beat * 0.5), BD, 85)
                if b == 3 and random.random() < 0.3:
                    add_note(beat_tick + int(ticks_per_beat * 0.75), BD, 80)
                    
        elif bar < 40:
            # Tom rolls and soloing over double kick
            toms = [T1, T2, T3, T4]
            for b in range(4):
                beat_tick = bar_start + b * ticks_per_beat
                # Double kick
                add_note(beat_tick, BD, 90)
                add_note(beat_tick + ticks_per_beat//2, BD, 80)
                
                # Hands
                if random.random() < 0.7:
                    if random.random() < 0.2:
                        add_flam(beat_tick, random.choice(toms), 100)
                    else:
                        div = ticks_per_beat // (4 if random.random() < 0.5 else 3)
                        for i in range(ticks_per_beat // div):
                            add_note(beat_tick + i * div, random.choice(toms + [SD]), 80 + int(random.random()*30))
                else:
                    if b in [1, 3]:
                        add_note(beat_tick, SD, 115)
                        
        elif bar < 56:
            # Climax: Fast rolls and crash hits
            if bar % 2 == 0:
                for b in range(4):
                    beat_tick = bar_start + b * ticks_per_beat
                    add_note(beat_tick, CR if b==0 else CH, 110)
                    if b in [0, 2]: add_note(beat_tick, BD, 110)
                    if b in [1, 3]: add_note(beat_tick, SD, 120)
            else:
                add_roll(bar_start, bar_start + 4 * ticks_per_beat, SD, 70, 127, 60) # 32nd note snare roll
                add_note(bar_start + 4 * ticks_per_beat - 60, BD, 110)
                
        else:
            # Outro
            if bar == 59:
                add_roll(bar_start, bar_start + 3 * ticks_per_beat, SD, 100, 127, 60)
                add_roll(bar_start, bar_start + 3 * ticks_per_beat, BD, 100, 127, 120)
                # Final hit
                add_flam(bar_start + 3 * ticks_per_beat, SD, 127)
                add_note(bar_start + 3 * ticks_per_beat, CR, 127)
                add_note(bar_start + 3 * ticks_per_beat, BD, 127)
            else:
                # Big tom hits
                t = bar_start
                while t < bar_start + 4 * ticks_per_beat:
                    add_note(t, random.choice([T1, T2, T3, T4]), 110, 120)
                    add_note(t, BD, 110, 120)
                    t += int(ticks_per_beat * random.choice([0.5, 0.75, 1.0]))

    # Flatten and sort events
    midi_events = []
    for t, p, v, d in events:
        if t < 0: t = 0
        midi_events.append((t, 'note_on', p, v))
        midi_events.append((t + d, 'note_off', p, 0))
        
    midi_events.sort(key=lambda x: x[0])
    
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)
    
    # Tempo map
    track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm), time=0))
    
    last_tick = 0
    for abs_tick, msg_type, pitch, vel in midi_events:
        delta = abs_tick - last_tick
        track.append(Message(msg_type, channel=9, note=pitch, velocity=vel, time=delta))
        last_tick = abs_tick
        
    mid.save('solo.mid')

if __name__ == "__main__":
    generate_solo()
