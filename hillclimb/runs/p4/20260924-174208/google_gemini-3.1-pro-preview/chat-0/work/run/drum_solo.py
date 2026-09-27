import mido
import math
import random

class Drummer:
    def __init__(self):
        self.hits = []
        self.tempo_events = []
        random.seed(42)  # Ensure reproducibility
        self.swing = 0.0

    def hit(self, beat, pitch, vel, feel="center"):
        # Apply 16th note swing
        fraction = beat % 0.5
        if self.swing > 0:
            if 0.20 < fraction < 0.30:
                beat += self.swing * 0.05 

        # Apply micro-timing feel
        if feel == "laid_back":
            beat += 0.015
        elif feel == "pushing":
            beat -= 0.015

        # Humanize timing
        beat += random.uniform(-0.005, 0.005)

        # Humanize velocity
        vel = int(max(1, min(127, vel + random.gauss(0, 3))))
        
        self.hits.append((beat, pitch, vel))

    def set_tempo(self, beat, bpm):
        self.tempo_events.append((beat, bpm))

    # Standard Kit Mapping
    def kick(self, b, v=100, f="center"): self.hit(b, 36, v, f)
    def snare(self, b, v=100, f="center"): self.hit(b, 38, v, f)
    def ghost(self, b, f="center"): self.hit(b, 38, random.randint(30, 45), f)
    def rim(self, b, v=80, f="center"): self.hit(b, 37, v, f)
    def hihat_c(self, b, v=90, f="center"): self.hit(b, 42, v, f)
    def hihat_o(self, b, v=90, f="center"): self.hit(b, 46, v, f)
    def hihat_p(self, b, v=80, f="center"): self.hit(b, 44, v, f)
    def ride(self, b, v=90, f="center"): self.hit(b, 51, v, f)
    def ride_bell(self, b, v=100, f="center"): self.hit(b, 53, v, f)
    def crash1(self, b, v=110, f="center"): self.hit(b, 49, v, f)
    def crash2(self, b, v=110, f="center"): self.hit(b, 57, v, f)
    def tom_h(self, b, v=90, f="center"): self.hit(b, 50, v, f)
    def tom_hm(self, b, v=90, f="center"): self.hit(b, 48, v, f)
    def tom_lm(self, b, v=90, f="center"): self.hit(b, 47, v, f)
    def tom_l(self, b, v=90, f="center"): self.hit(b, 45, v, f)
    def tom_f(self, b, v=90, f="center"): self.hit(b, 41, v, f)


def intro(dr):
    # Measures 1-4 (Beats 0-16): Sparse atmosphere, swelling cymbals, rhythmic hints
    for i in range(32):
        b = i * 0.5
        v = int(30 + (i/32) * 50)
        dr.ride(b, v)
        if i % 8 == 0:
            dr.crash1(b, int(40 + (i/32)*40))
            dr.kick(b, 60)
            
    dr.rim(2, 60); dr.rim(3.5, 70); dr.rim(6, 75)
    dr.tom_f(7.5, 70); dr.tom_f(7.75, 60)
    dr.rim(10, 80); dr.rim(11.5, 85)
    dr.tom_h(12.5, 70); dr.tom_hm(13, 75); dr.tom_lm(13.5, 80)
    dr.kick(14, 80)
    dr.hit(14.5, 55, 80) # Splash cymbal color
    dr.rim(15, 90)


def intro_build(dr):
    # Measures 5-8 (Beats 16-32): Marching snare rudiments establishing the groove
    base = 16
    for i in range(16):
        dr.hihat_p(base + i) # Steady foot
        
    for i in range(8):
        b = base + i*0.5
        dr.snare(b, 50 + i*2)
        if i % 2 == 1:
            dr.snare(b - 0.25, 40 + i*2) 
            
    for i in range(16):
        b = base + 4 + i*0.25
        dr.snare(b, 60 + i*2)
        if i % 4 == 0:
            dr.kick(b, 70)
            
    for i in range(16):
        b = base + 8 + i*0.25
        if i % 4 == 0:
            dr.tom_h(b, 80 + i*2)
            dr.kick(b, 80)
        else:
            dr.snare(b, 70 + i*2)

    # 16th note triplets swell into the groove
    for i in range(24):
        b = base + 12 + i*(1/6)
        v = 80 + int(i * 1.5)
        if i < 6: dr.snare(b, v)
        elif i < 12: dr.tom_h(b, v)
        elif i < 18: dr.tom_hm(b, v)
        else: dr.tom_f(b, v)
        if i % 6 == 0: dr.kick(b, 100)


def funk_groove(dr, base, variation=0):
    dr.kick(base + 0, 100, "pushing")
    
    if variation == 0:
        dr.kick(base + 1.5, 90, "pushing")
        dr.kick(base + 2.5, 90, "pushing")
    elif variation == 1:
        dr.kick(base + 1.25, 80); dr.kick(base + 1.5, 90)
        dr.kick(base + 2.75, 80); dr.kick(base + 3.5, 90)
    elif variation == 2:
        dr.kick(base + 1.5, 90); dr.kick(base + 3.5, 90); dr.kick(base + 3.75, 90)
        
    dr.snare(base + 1, 110, "laid_back")
    dr.snare(base + 3, 110, "laid_back")
    
    # Intricate ghost note placement
    if variation % 2 == 0:
        for offset in [0.75, 1.25, 1.75, 2.25, 3.25]:
            dr.ghost(base + offset, "laid_back")
    else:
        for offset in [0.75, 1.75, 2.25, 2.75]:
            dr.ghost(base + offset, "laid_back")

    if variation < 2:
        for i in range(8):
            b = i * 0.5
            v = 90 if i % 2 == 0 else 60
            if variation == 1 and i == 3:
                dr.hihat_o(base + b, 80)
            else:
                dr.hihat_c(base + b, v)
    else:
        # Move to Ride + Cowbell (Color)
        for i in range(8):
            b = i * 0.5
            v = 100 if i % 2 == 0 else 75
            if i % 4 == 0:
                dr.ride_bell(base + b, 110)
                dr.hit(base + b, 56, 90) # Cowbell!
            else:
                dr.ride(base + b, v)
        dr.hihat_p(base + 1); dr.hihat_p(base + 3)


def composed_fill_1(dr, base):
    for i in range(4):
        b = base + i
        if i < 2:
            dr.snare(b, 100 + i*5)
            dr.snare(b + 0.333, 80 + i*5)
        elif i == 2:
            dr.tom_h(b, 100)
            dr.tom_h(b + 0.333, 90)
        else:
            dr.tom_lm(b, 100)
            dr.tom_lm(b + 0.333, 90)
        dr.kick(b + 0.666, 100)


def composed_fill_2(dr, base):
    dr.crash1(base); dr.kick(base)
    dr.hihat_c(base + 0.5)
    dr.snare(base + 1, 110)
    dr.kick(base + 1.5); dr.kick(base + 1.75)
    
    # Blazing 32nd note snare sweep into the toms
    for i in range(8):
        dr.snare(base + 2 + i*0.125, 90 + i*4)
    dr.tom_h(base + 3, 110); dr.tom_h(base + 3.125, 100)
    dr.tom_hm(base + 3.25, 110); dr.tom_hm(base + 3.375, 100)
    dr.tom_lm(base + 3.5, 110); dr.tom_lm(base + 3.625, 100)
    dr.tom_f(base + 3.75, 110); dr.tom_f(base + 3.875, 110)


def section_groove_A(dr):
    # Measures 9-24 (Beats 32-96)
    dr.crash1(32, 110); dr.crash2(32, 110)
    funk_groove(dr, 32, 0); funk_groove(dr, 36, 0)
    funk_groove(dr, 40, 1); funk_groove(dr, 44, 1) 
    
    dr.crash1(48, 110)
    funk_groove(dr, 48, 0); funk_groove(dr, 52, 1); funk_groove(dr, 56, 0)
    composed_fill_1(dr, 60) 
    
    dr.crash2(64, 110)
    funk_groove(dr, 64, 2); funk_groove(dr, 68, 2); funk_groove(dr, 72, 2)
    funk_groove(dr, 76, 2)
    dr.snare(79.5, 110); dr.tom_h(79.75, 110) # Tiny phrase lick
    
    dr.crash1(80, 110)
    funk_groove(dr, 80, 2); funk_groove(dr, 84, 2); funk_groove(dr, 88, 2)
    composed_fill_2(dr, 92)


def linear_section(dr, base=96):
    # Measures 25-32 (Beats 96-128): Travelling around the kit linearly
    dr.crash1(base, 110)
    
    def linear_measure(dr, m_base, m_index):
        # 16th note linear phrasing: R L K R L K K R L K R L K K R L
        pattern = ['R', 'L', 'K', 'R', 'L', 'K', 'K', 'R', 'L', 'K', 'R', 'L', 'K', 'K', 'R', 'L']
        for i, hit in enumerate(pattern):
            b = m_base + i*0.25
            if hit == 'R':
                if i == 0:
                    if m_index in (1, 5): dr.hit(b, 55, 110) # Splash
                    else: dr.ride_bell(b, 105)
                elif i == 7: dr.tom_h(b, 100)
                elif i == 14: dr.tom_f(b, 100)
                else: dr.hihat_c(b, 90)
            elif hit == 'L':
                if i == 15: dr.snare(b, 115) 
                elif i in (4, 11): dr.snare(b, 110) 
                else: dr.ghost(b)
            elif hit == 'K':
                dr.kick(b, 100)
                
    for m in range(7):
        if m == 4: dr.crash2(base + m*4, 110)
        linear_measure(dr, base + m*4, m)
        
    # Linear Fill (Beats 124-128)
    chops = [
        [('snare', 110), ('snare', 60), ('kick', 100), ('kick', 100)],
        [('tom_h', 100), ('tom_hm', 100), ('kick', 100), ('kick', 100)],
        [('tom_lm', 100), ('tom_f', 100), ('kick', 100), ('kick', 100)],
        [('snare', 110), ('tom_h', 100), ('tom_f', 100), ('kick', 100)]
    ]
    fill_base = base + 28
    current_chop = chops[0]
    for i in range(16):
        if i % 4 == 0:
            current_chop = random.choice(chops)
            if i >= 12: current_chop = [('snare', 120), ('tom_h', 115), ('tom_hm', 110), ('tom_f', 110)]
        drum, vel = current_chop[i % 4]
        vel = min(127, int(vel * (1.0 + (i/16)*0.2)))
        b = fill_base + i * 0.25
        if drum == 'snare': dr.snare(b, vel)
        elif drum == 'kick': dr.kick(b, vel)
        elif drum == 'tom_h': dr.tom_h(b, vel)
        elif drum == 'tom_hm': dr.tom_hm(b, vel)
        elif drum == 'tom_lm': dr.tom_lm(b, vel)
        elif drum == 'tom_f': dr.tom_f(b, vel)


def chop_section(dr, base=128):
    # Measures 33-40 (Beats 128-160): Metric modulation / Sextuplet chops
    dr.crash1(base, 115); dr.crash2(base, 115); dr.kick(base, 110)
    
    for m in range(2):
        m_base = base + m*4
        if m > 0: dr.hihat_o(m_base, 100)
        dr.kick(m_base, 110)
        dr.hihat_c(m_base + 0.5, 90)
        dr.snare(m_base + 1, 120); dr.hihat_c(m_base + 1, 100)
        dr.kick(m_base + 1.5, 100); dr.kick(m_base + 1.75, 100)
        
        for i in range(12):
            b = m_base + 2 + i*(1/6)
            rem = i % 3
            if rem == 0:
                if i < 6: dr.tom_h(b, 110)
                else: dr.tom_hm(b, 110)
            elif rem == 1: dr.snare(b, 90)
            elif rem == 2: dr.kick(b, 100)
                
    for m in range(2, 4):
        m_base = base + m*4
        dr.crash1(m_base, 110); dr.kick(m_base, 110)
        dr.hihat_c(m_base + 0.5, 90)
        dr.snare(m_base + 1, 120); dr.hihat_c(m_base + 1, 100)
        dr.kick(m_base + 1.5, 100)
        
        for i in range(12):
            b = m_base + 2 + i*(1/6)
            rem = i % 6
            if rem in (0, 1):
                if i < 6: dr.tom_h(b, 110)
                else: dr.tom_f(b, 110)
            elif rem in (2, 3): dr.snare(b, 100)
            elif rem in (4, 5): dr.kick(b, 110)
                
    # Poly-rhythmic build up
    for i in range(8):
        b = 144 + i*0.5
        dr.snare(b, 90 + i*2); dr.tom_f(b, 90 + i*2); dr.kick(b, 100)
    for i in range(16):
        b = 148 + i*0.25
        dr.snare(b, 90 + i)
        if i % 4 == 0: dr.crash1(b, 100); dr.kick(b, 100)
    for i in range(24):
        b = 152 + i*(1/6)
        dr.snare(b, 100 + int(i*0.5))
        if i % 6 == 0: dr.crash2(b, 110); dr.kick(b, 100)
    for i in range(32):
        dr.snare(156 + i*0.125, 100 + int(i*0.5))
    dr.kick(156, 110); dr.kick(157, 110); dr.kick(158, 110); dr.kick(159, 110)


def heavy_climax(dr, base=160):
    # Measures 41-48 (Beats 160-192): Pounding rock showcase
    for m in range(8):
        m_base = base + m*4
        dr.crash1(m_base, 120); dr.kick(m_base, 110)
        dr.crash2(m_base + 1, 115)
        dr.snare(m_base + 1, 127)
        dr.kick(m_base + 1.75, 100)
        
        if m in (3, 7):
            dr.kick(m_base + 2, 110); dr.kick(m_base + 3, 110)
            for i in range(8):
                b = m_base + 2 + i*0.25
                if i < 2: dr.tom_h(b, 120)
                elif i < 4: dr.tom_hm(b, 120)
                elif i < 6: dr.tom_lm(b, 120)
                else: dr.tom_f(b, 120)
        else:
            dr.crash1(m_base + 2, 115)
            dr.crash2(m_base + 3, 115)
            dr.snare(m_base + 3, 127)
            dr.kick(m_base + 2, 110)
            dr.kick(m_base + 2.75, 100)
            dr.kick(m_base + 3.5, 110)
            dr.kick(m_base + 3.75, 100)


def ostinato_solo(dr, base=192):
    # Measures 49-56 (Beats 192-224): Double bass pedal ostinato with hands soling over top
    for i in range(128): 
        b = base + i*0.25
        if i % 2 == 0: dr.hit(b, 36, 110) 
        else: dr.hit(b, 35, 105) 
            
    punches = [0, 1.5, 2.75, 4, 5.5, 6.75]
    for m in [0, 2, 4, 6]:
        m_base = base + m*4
        for p in punches:
            if m == 6 and p >= 2: continue
            if m == 2 and (p == 3 or p == 3.5): continue
            if m_base + p < 224:
                dr.hit(m_base + p, 52, 120) # China Cymbal
                dr.snare(m_base + p, 127)
                
        if m == 2:
            dr.tom_h(m_base + 3, 120); dr.tom_hm(m_base + 3.5, 120)
        if m == 6:
            toms = [50, 48, 47, 45]
            for i in range(8):
                dr.hit(m_base + 2 + i*0.25, toms[i%4], 120)


def outro(dr, base=224):
    # Measures 57-60 (Beats 224-240): Massive descending drum roll
    for i in range(64): 
        b = base + i*0.25
        vel = int(30 + (i/64) * 97)
        if i < 16: dr.snare(b, vel)
        elif i < 32: dr.tom_h(b, vel)
        elif i < 48: dr.tom_lm(b, vel)
        else: dr.tom_f(b, vel)
        if i % 4 == 0: dr.kick(b, vel)
            
    # Measures 61-64 (Beats 240-256): Ritardando, big definitive hits
    dr.crash1(240, 127); dr.crash2(240, 127); dr.kick(240, 127)
    dr.snare(241.5, 127); dr.kick(241.5, 127)
    dr.tom_h(242.5, 127); dr.tom_f(242.5, 127); dr.kick(242.5, 127)
    
    dr.crash1(244, 127); dr.crash2(244, 127); dr.kick(244, 127)
    dr.snare(245.333, 127); dr.kick(245.333, 127)
    dr.snare(246.666, 127); dr.kick(246.666, 127)
    
    dr.crash1(248, 127); dr.crash2(248, 127); dr.kick(248, 127)
    
    # Giant Flam Roll climax
    for i in range(8):
        b = 250 + i*0.25
        dr.snare(b, 100 + i*3)
        dr.snare(b + 0.03, 80 + i*3) # Flam grace note
        dr.kick(b, 110)
        
    # The Final Hit!
    dr.crash1(252, 127); dr.crash2(252, 127); dr.kick(252, 127); dr.kick(252.25, 100)


def generate_midi():
    dr = Drummer()
    dr.swing = 0.0
    
    # Generate Musical Sections
    intro(dr)
    intro_build(dr)
    
    dr.swing = 1.0 # Add a heavy swing feel to the funk groove
    section_groove_A(dr)
    
    dr.swing = 0.0 # Straight ahead for linear patterns
    linear_section(dr)
    chop_section(dr)
    heavy_climax(dr)
    ostinato_solo(dr)
    outro(dr)
    
    # Dynamic Tempo Map
    dr.set_tempo(0, 110)
    dr.set_tempo(16, 115)
    dr.set_tempo(32, 120)
    dr.set_tempo(96, 122)
    dr.set_tempo(128, 118)
    dr.set_tempo(160, 125)
    dr.set_tempo(192, 128)
    dr.set_tempo(224, 120)
    
    # Ritardando effect at the end
    for i in range(16):
        dr.set_tempo(240 + i, 120 - i*4) 
        
    # Let the final hit ring out
    dr.set_tempo(260, 60)

    # Convert beats to MIDI ticks (480 Ticks Per Quarter Note)
    event_list = []
    
    def bpm2tempo(bpm):
        return int(60_000_000 // bpm)

    event_list.append((0, 'time_signature', 4, 4))
    
    for te in dr.tempo_events:
        b, bpm = te
        abs_tick = int(b * 480)
        event_list.append((abs_tick, 'set_tempo', bpm2tempo(bpm)))
        
    for hit in dr.hits:
        b, pitch, vel = hit
        abs_tick = int(b * 480)
        event_list.append((abs_tick, 'note_on', pitch, vel))
        event_list.append((abs_tick + 10, 'note_off', pitch, 0)) # Very short duration
        
    # Sort events
    def sort_key(ev):
        priority = 0
        if ev[1] == 'time_signature': priority = 0
        elif ev[1] == 'set_tempo': priority = 1
        elif ev[1] == 'note_off': priority = 2
        elif ev[1] == 'note_on': priority = 3
        return (ev[0], priority)
        
    event_list.sort(key=sort_key)
    
    # Write to File
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('track_name', name='Showcase Drum Solo', time=0))
    
    last_tick = 0
    for ev in event_list:
        abs_tick = ev[0]
        delta = max(0, abs_tick - last_tick)
            
        if ev[1] == 'note_on':
            track.append(mido.Message('note_on', channel=9, note=ev[2], velocity=ev[3], time=delta))
        elif ev[1] == 'note_off':
            track.append(mido.Message('note_off', channel=9, note=ev[2], velocity=0, time=delta))
        elif ev[1] == 'set_tempo':
            track.append(mido.MetaMessage('set_tempo', tempo=ev[2], time=delta))
        elif ev[1] == 'time_signature':
            track.append(mido.MetaMessage('time_signature', numerator=ev[2], denominator=ev[3], time=delta))
            
        last_tick = abs_tick

    mid.save('solo.mid')

if __name__ == '__main__':
    generate_midi()
