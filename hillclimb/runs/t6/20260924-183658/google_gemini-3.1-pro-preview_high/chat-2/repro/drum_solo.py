import math
import random
import mido

STD_MAP = {
    'C': [(49, 115), (36, 110)],  # CRASH 1 + KICK
    'D': [(57, 115), (36, 110)],  # CRASH 2 + KICK
    'R': [(51, 100)],             # RIDE
    'B': [(53, 115)],             # RIDE BELL
    'r': [(51, 70)],              # RIDE weak
    'X': [(46, 100), (36, 100)],  # OPEN HAT + KICK
    'O': [(46, 100)],             # OPEN HAT
    'x': [(42, 90)],              # CLOSED HAT
    'y': [(42, 50)],              # CLOSED HAT ghost
    'P': [(44, 90)],              # PEDAL HAT
    'S': [(38, 120)],             # SNARE accent
    's': [(38, 90)],              # SNARE normal
    'g': [(38, 40)],              # SNARE ghost
    'K': [(36, 115)],             # KICK accent
    'k': [(36, 80)],              # KICK normal/ghost
    '1': [(50, 110)],             # HI TOM
    'q': [(50, 70)],
    '2': [(47, 110)],             # MID TOM
    'w': [(47, 70)],
    '3': [(43, 110)],             # LOW TOM
    'e': [(43, 70)],
    '4': [(41, 110)],             # FLOOR TOM
    'E': [(41, 70)],
    'Z': [(55, 110), (36, 100)],  # SPLASH + KICK
    'F': [(38, 127), (49, 127), (57, 127), (36, 127)],  # FLAM / BIG FINALE HIT
}

def combine_patterns(patterns):
    token_lists = [p.split() for p in patterns]
    length = max(len(t) for t in token_lists)
    
    result = []
    for i in range(length):
        chord = []
        for tl in token_lists:
            if i < len(tl) and tl[i] != '-':
                clean = tl[i].replace('[','').replace(']','')
                chord.extend(list(clean))
        if not chord:
            result.append('-')
        elif len(chord) == 1:
            result.append(chord[0])
        else:
            result.append('[' + "".join(chord) + ']')
    return " ".join(result)


class SoloSequencer:
    def __init__(self):
        self.events = []
        self.current_beat = 0

    def play_string(self, subdivision, pattern, dyn_func=None):
        tokens = pattern.split()
        for i, token in enumerate(tokens):
            if token == '-':
                self.current_beat += subdivision
                continue
            
            dyn = dyn_func(i, len(tokens)) if dyn_func else 1.0
            clean = token.replace('[', '').replace(']', '')
            
            step_pitches = {}
            for char in clean:
                if char in STD_MAP:
                    for pitch, vel in STD_MAP[char]:
                        scaled_vel = vel * dyn
                        if pitch not in step_pitches or step_pitches[pitch] < scaled_vel:
                            step_pitches[pitch] = scaled_vel
            
            # Pulse push/pull, swing on 16ths, and intentional slight human imperfection
            noise = random.uniform(-0.015, 0.015)
            push_pull = math.sin(self.current_beat * 2 * math.pi / 4) * 0.02
            sixteenth = (self.current_beat * 4) % 1
            swing = 0.02 if 0.4 < sixteenth < 0.6 else 0.0
            
            final_beat = self.current_beat + noise + push_pull + swing
            
            for pitch, vel in step_pitches.items():
                limb_variance = random.uniform(-0.003, 0.003)
                final_vel = max(1, min(127, int(vel * random.uniform(0.9, 1.1))))
                self.events.append((final_beat + limb_variance, pitch, final_vel))
                
            self.current_beat += subdivision

    def save(self, filename="solo.mid", tempo_bpm=120):
        mid = mido.MidiFile()
        ticks_per_beat = mid.ticks_per_beat
        
        abs_events = []
        for beat, pitch, vel in self.events:
            abs_tick = int(beat * ticks_per_beat)
            abs_events.append((abs_tick, 'note_on', pitch, vel))
            abs_events.append((abs_tick + 100, 'note_off', pitch, 0))
            
        abs_events.sort(key=lambda e: (e[0], 0 if e[1]=='note_on' else 1))
        
        track = mido.MidiTrack()
        mid.tracks.append(track)
        tempo = mido.bpm2tempo(tempo_bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        
        last_tick = 0
        for tick, msg_type, pitch, vel in abs_events:
            delta = tick - last_tick
            if delta < 0:
                delta = 0
            # Channel 9 (10 in 1-based indexing) is General MIDI drums
            if msg_type == 'note_on':
                track.append(mido.Message('note_on', channel=9, note=pitch, velocity=vel, time=delta))
            else:
                track.append(mido.Message('note_off', channel=9, note=pitch, velocity=0, time=delta))
            last_tick = max(last_tick, tick)
            
        mid.save(filename)


def generate_groove(seq, bars, intensity=1.0):
    for i in range(bars):
        ride_p = []
        snare_p = []
        kick_p = []
        
        for sub in range(16):
            r, s, k = '-', '-', '-'
            
            if sub % 4 == 0:
                r = 'B' if intensity > 1.2 else ('x' if intensity < 1.0 else 'R')
            elif sub % 2 == 0:
                r = 'r' if intensity > 1.2 else 'x'
            elif random.random() < (intensity - 1.0) * 0.5:
                r = 'r' if intensity > 1.2 else 'y'
                
            if sub == 4 or sub == 12:
                s = 'S'
            elif sub != 4 and sub != 12:
                if random.random() < 0.2 * intensity:
                    s = 'g'
            
            if sub == 0:
                k = 'K'
            elif sub == 8 or sub == 10:
                if random.random() < 0.5 * intensity:
                    k = 'K'
            elif random.random() < 0.1 * intensity:
                k = 'k'
                
            # Groove fills at the end of every 4th bar
            if i % 4 == 3 and sub >= 12:
                r = '-'
                s = 'S' if sub % 2 == 0 else 'g'
                k = 'K' if sub % 2 == 1 else '-'
                if intensity > 1.2:
                    s = '1' if sub == 12 else ('2' if sub == 13 else ('3' if sub == 14 else '4'))
            
            # Crash downbeats
            if i % 4 == 0 and sub == 0:
                r = 'C' if i % 8 == 0 else 'D'
                
            ride_p.append(r)
            snare_p.append(s)
            kick_p.append(k)
            
        combined = combine_patterns([" ".join(ride_p), " ".join(snare_p), " ".join(kick_p)])
        seq.play_string(0.25, combined)


if __name__ == "__main__":
    # Deterministic generation
    random.seed(42)
    seq = SoloSequencer()
    
    # ---------------------------------------------------------
    # SECTION 1: Intro - Sparse, motif establishment (32 beats)
    # ---------------------------------------------------------
    seq.play_string(0.25, "C - - - - - - - - - - - - - - -")
    seq.play_string(0.25, "- - - - - - S - - - - - K - - -")
    seq.play_string(0.25, "X - y - - - - - [S1] - - - - g K -")
    seq.play_string(0.25, "X - - K - - - - S - g g K - - -")
    seq.play_string(0.25, "Z - - - - - - - - - 1 2 3 - - -")
    seq.play_string(0.25, "- - - - - - S - g g - - K - - -")
    seq.play_string(0.25, "Z - - - - K - - - - 1 1 2 2 3 -")
    seq.play_string(0.25, "- - - - [SK] - - - - - - - - - - -")
    
    # ---------------------------------------------------------
    # SECTION 2: Groove Evolution (48 beats)
    # ---------------------------------------------------------
    generate_groove(seq, bars=4, intensity=0.8)
    generate_groove(seq, bars=4, intensity=1.1)
    generate_groove(seq, bars=3, intensity=1.3)
    seq.play_string(1/6, "1 1 1 2 2 2 3 3 3 4 4 4 K K K K K K S S S S S S")
    
    # ---------------------------------------------------------
    # SECTION 3: Space and Polyrhythm (32 beats)
    # 3-against-4 phrasing over a kick and ghost-note snare base
    # ---------------------------------------------------------
    for _ in range(2):
        seq.play_string(0.25, "C - g S - K B - g S - K B - g S")
        seq.play_string(0.25, "- K B - g S - K B - g S - K B -")
        seq.play_string(0.25, "g S - K B - g S - K B - g S - K")
        if _ == 0:
            seq.play_string(0.25, "Z - S S K K K K 1 1 2 2 3 3 4 4")
        else:
            seq.play_string(1/6, "S S K S S K S S K S S K 1 1 K 1 1 K 2 2 K 3 3 K")
            
    # ---------------------------------------------------------
    # SECTION 4: Double Kick & Tom Assault (48 beats)
    # ---------------------------------------------------------
    for i in range(3):
        if i == 0:
            seq.play_string(0.25, "C - K K S - K K C - K K S - K K")
            seq.play_string(0.25, "C - K K S - K K 1 - 2 - 3 - 4 -")
        elif i == 1:
            seq.play_string(0.25, "C - K K S - K K C - K K S - K K")
            seq.play_string(0.25, "C - K K S - K K 4 - 3 - 2 - 1 -")
        else:
            seq.play_string(0.25, "C - K K S - K K C - K K S - K K")
            seq.play_string(0.25, "C - K K S - K K [C1] - [D2] - [C3] - [D4] -")
            
        seq.play_string(0.25, "C - K K S - K K C - K K S - K K")
        
        if i < 2:
            seq.play_string(1/6, "1 2 3 4 K K 1 2 3 4 K K 1 2 3 4 K K S S S S S S")
        else:
            seq.play_string(0.125, "S S S S 1 1 1 1 2 2 2 2 3 3 3 3 4 4 4 4 K K K K C - - - - - - -")

    # ---------------------------------------------------------
    # SECTION 5: Breakdown & Crescendo Swell (32 beats)
    # ---------------------------------------------------------
    seq.play_string(0.25, "Z - - - - - - - - - - - - - - -")
    seq.play_string(0.25, "- - - - P - - - P - - - P - - -")
    seq.play_string(0.25, "- - - - - - - - - - - - - - - -")
    seq.play_string(0.25, "- - - - P - - - P - - - P - - -")
    
    pedal_32 = ["P" if j % 8 == 0 else "-" for j in range(32)]
    pedal_str = " ".join(pedal_32)
    toms_swell = ["1"]*8 + ["2"]*8 + ["3"]*8 + ["4"]*8

    seq.play_string(0.125, combine_patterns([" ".join(["S"]*32), pedal_str]), dyn_func=lambda i, t: 0.3 + 0.2*(i/t))
    seq.play_string(0.125, combine_patterns([" ".join(["S"]*32), pedal_str]), dyn_func=lambda i, t: 0.5 + 0.2*(i/t))
    seq.play_string(0.125, combine_patterns([" ".join(["S"]*32), pedal_str]), dyn_func=lambda i, t: 0.7 + 0.3*(i/t))
    seq.play_string(0.125, combine_patterns([" ".join(toms_swell), pedal_str]), dyn_func=lambda i, t: 0.9 + 0.3*(i/t))

    # ---------------------------------------------------------
    # SECTION 6: The Climax and Showcase Fills (32 beats)
    # ---------------------------------------------------------
    generate_groove(seq, bars=4, intensity=1.6)
    seq.play_string(1/6, "C K K C K K C K K C K K C K K C K K C K K C K K")
    seq.play_string(0.125, "S S K K 1 1 K K 2 2 K K 3 3 K K 4 4 K K S S K K 1 2 3 4 K K K K") 
    seq.play_string(1/6, "1 2 3 K K K 1 2 3 K K K 1 2 3 K K K 1 2 3 K K K") 
    seq.play_string(0.125, "S S S S S S S S S S S S S S S S S S S S S S S S S S S S S S S S", dyn_func=lambda i, t: 0.8 + 0.4*(i/t))

    # ---------------------------------------------------------
    # SECTION 7: Grand Finale (16 beats, finishing at exactly 2 mins)
    # ---------------------------------------------------------
    seq.play_string(0.25, "C - - - C - - - C - - - C - - -") 
    seq.play_string(0.25, "C - - - - - C - - - - - C - - -")
    seq.play_string(1/6, "1 1 1 2 2 2 3 3 3 4 4 4 K K K K K K K K K K K K")
    seq.play_string(0.125, "1 1 2 2 3 3 4 4 1 1 2 2 3 3 4 4 S S S S S S S S S S S S S S S S")
    
    # Lands definitively, rings out.
    seq.play_string(4.0, "F")
    
    seq.save("solo.mid", 120)
