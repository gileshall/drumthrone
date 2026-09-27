import mido
import random
import math

class DrumSolo:
    def __init__(self):
        self.hits = []
        random.seed(42) # Deterministic on every run
        self.ppq = 480
        
        # General MIDI Percussion Key Map
        self.K = 36    # Bass Drum 1
        self.S = 38    # Acoustic Snare
        self.CH = 42   # Closed Hi-Hat
        self.PH = 44   # Pedal Hi-Hat
        self.OH = 46   # Open Hi-Hat
        self.R1 = 51   # Ride 1
        self.RB = 53   # Ride Bell
        self.C1 = 49   # Crash 1
        self.C2 = 57   # Crash 2
        self.T1 = 50   # High Tom
        self.T2 = 48   # Hi-Mid Tom
        self.T3 = 45   # Low Tom
        self.T4 = 43   # High Floor Tom
        self.T5 = 41   # Low Floor Tom
        self.SPL = 55  # Splash
        self.CHN = 52  # China Cymbal
        self.CB = 56   # Cowbell

    def add_hit(self, beat, note, vel, timing_slop=0.015, vel_slop=5):
        # Micro-timing and humanized velocity
        h_beat = beat + random.gauss(0, timing_slop)
        h_vel = int(vel + random.gauss(0, vel_slop))
        h_vel = max(1, min(127, h_vel))
        self.hits.append((h_beat, note, h_vel))

    def char_to_vel(self, c):
        # Map character symbols to base velocities for step sequencing
        v = {'1':30, '2':40, '3':50, '4':60, '5':70, '6':80, '7':90, '8':100, '9':110,
             'X':80, 'O':100, 'V':127, 'x':45, 'b':25, 'c':15}
        return v.get(c, 0)

    def play_seq(self, start_beat, step, seq_dict):
        # Play a dict of drum pattern strings (step sequencer style)
        steps = max(len(v) for v in seq_dict.values())
        for i in range(steps):
            b = start_beat + i * step
            for note, pattern in seq_dict.items():
                if i < len(pattern):
                    char = pattern[i]
                    if char != '.' and char != ' ':
                        vel = self.char_to_vel(char)
                        if vel > 0:
                            self.add_hit(b, note, vel)

    def swell(self, start, duration, note, start_vel, end_vel):
        # Gradual roll/swell on a cymbal
        steps = int(duration * 8)
        for i in range(steps):
            b = start + i * 0.125
            v = start_vel + (end_vel - start_vel) * (i / max(1, steps - 1))
            self.add_hit(b, note, int(v), timing_slop=0.03)

    def rumbling(self, start, duration):
        # Abstract tom rumbling to build tension
        for i in range(int(duration * 4)):
            b = start + i * 0.25
            if random.random() > 0.3:
                t_note = random.choice([self.T5, self.T4, self.T3, self.T2, self.T1])
                v = random.randint(30, 60)
                self.add_hit(b, t_note, v, timing_slop=0.02)

    def linear_fill(self, start_beat, phrase, step=0.25):
        # Drummer linear chops parsed from a string of limb markers (R, L, K)
        hands = [self.S, self.T1, self.T2, self.T4, self.S]
        hand_idx = 0
        for i, char in enumerate(phrase):
            b = start_beat + i * step
            
            # Massive crescendo at the tail end of the phrase
            if i >= len(phrase) - 16:
                crescendo_factor = (i - (len(phrase) - 16)) / 15.0
                vel_base = int(40 + 70 * crescendo_factor)
                if char in 'Kk':
                    self.add_hit(b, self.K, 110)
                else:
                    self.add_hit(b, self.S, vel_base + (10 if char=='R' else 0))
                continue

            # Route standard phrase
            if char == 'K':
                self.add_hit(b, self.K, 110)
            elif char == 'k':
                self.add_hit(b, self.K, 70)
            elif char in 'RL':
                if char == 'R' and i % 4 == 0:
                    hand_idx = (hand_idx + 1) % len(hands)
                note = hands[hand_idx]
                vel = 95 if char == 'R' else 85
                if i == 0 or (i > 0 and phrase[i-1] in 'Kk'):
                    vel = 110 # Accent right after kicks
                self.add_hit(b, note, vel)

    def sweep_rolls(self, start_beat):
        # Flowing 32nd note runs traveling around the kit utilizing six-stroke rolls (RLLRRL)
        pattern = "RLLRRL"
        rolls_len = 128 # 4 bars of 32nd notes
        
        for i in range(rolls_len):
            b = start_beat + i * 0.125
            char = pattern[i % 6]
            
            if i < 32:
                accent_drum, ghost_drum = self.T1, self.S
            elif i < 64:
                accent_drum, ghost_drum = self.T3, self.T1
            elif i < 96:
                accent_drum, ghost_drum = self.T4, self.K
            else:
                accent_drum = random.choice([self.S, self.T1, self.T2, self.T3, self.T4, self.C1])
                ghost_drum = self.S
                
            vel = 110 + random.randint(-10, 10) if char in 'RL' and (i%6==0 or i%6==5) else 60 + random.randint(-5, 5)
            
            if i >= 96:
                vel = 70 + (i - 96) * 1.5 # final bar resolves with heavy volume surge
                
            drum = accent_drum if (i%6==0 or i%6==5) else ghost_drum
            if drum == self.K and char in 'RL': drum = self.K 
            self.add_hit(b, drum, int(vel))
            
            if i % 8 == 0: self.add_hit(b, self.PH, 100) # Pedal keep time
            if i % 32 == 0: self.add_hit(b, self.SPL, 110) # Splash accent on beat 1

    def grand_roll(self, start, length):
        # The immense final showcase roll 
        steps = int(length * 8)
        for i in range(steps):
            b = start + i * 0.125
            drum = self.S
            if i > steps * 0.5: drum = self.T1
            if i > steps * 0.75: drum = self.T3
            
            vel = 60 + (i / steps) * 67
            self.add_hit(b, drum, int(vel))
            
            if i % 8 == 0:
                self.add_hit(b, self.K, 127)
                self.add_hit(b, self.C1, 110)

    def generate(self):
        # Section A (0:00 - 0:08 / Beats 0-16): Abstract intro, swells and rumbles
        self.swell(0, 8, self.C1, 10, 90)
        self.swell(4, 8, self.R1, 10, 80)
        self.swell(8, 8, self.C2, 10, 100)
        self.rumbling(8, 8)
        self.add_hit(16, self.C1, 110)
        self.add_hit(16, self.K, 110)
        
        # Section B (0:08 - 0:16 / Beats 16-32): Introduce linear motif
        seq_groove_1 = {
            self.CH: "7.4.4.7...4.4...",
            self.OH: "........7.......",
            self.S:  "..4..8....4..844",
            self.K:  "8..8...88..8...."
        }
        seq_groove_1_fill = {
            self.CH: "7.4.4.7.........",
            self.S:  "..4..8..8844....",
            self.T1: "............88..",
            self.T3: "..............88",
            self.K:  "8..8...8........"
        }
        for i in range(4):
            if i == 3:
                self.play_seq(16 + i * 4, 0.25, seq_groove_1_fill)
            else:
                self.play_seq(16 + i * 4, 0.25, seq_groove_1)
            for b_idx in range(4):
                if b_idx % 2 != 0:
                    self.add_hit(16 + i * 4 + b_idx, self.PH, 80)
                    
        # Section C (0:16 - 0:32 / Beats 32-64): Ride cymbal development
        seq_groove_2 = {
            self.R1: "7.4.7.4.7.4.7.4.",
            self.RB: "..7...7...7...7.",
            self.S:  "..4..8..b.4..8.4",
            self.K:  "8..8...8.8..8...",
            self.T1: ".......4........",
            self.T2: "..............4."
        }
        for i in range(8):
            if i % 4 == 3:
                if i == 7:
                    seq = {self.S: "4444555566667777", self.K: "8...8...8...8...", self.C1: "8..............."}
                else:
                    seq = {
                        self.R1: "7...6...........", self.S: "..3..8.38844....",
                        self.T2: "............88..", self.T4: "..............88",
                        self.K: "8..8...8........", self.C1: "8..............."
                    }
            else:
                seq = seq_groove_2.copy()
                if i == 0 or i == 4: seq[self.C1] = "8..............."
            self.play_seq(32 + i * 4, 0.25, seq)

        # Section D (0:32 - 0:40 / Beats 64-80): Intense Metric Modulation & Polyrhythm (Cowbell + Kick)
        cb_str = ["."] * 64; s_str = ["."] * 64; k_str = ["."] * 64
        for i in range(0, 64, 3): cb_str[i] = "8" # 3 against 4 on cowbell
        for i in range(4, 64, 8): s_str[i] = "8"
        for i in range(0, 64, 8): k_str[i] = "8"
        self.play_seq(64, 0.25, {self.CB: "".join(cb_str), self.S: "".join(s_str), self.K: "".join(k_str), self.PH: "".join(s_str)})
        
        # Section E (0:40 - 0:48 / Beats 80-96): Gospel Chops linear fills (Hands & Feet flow)
        phrase_80_96 = (
            "RLKKRLKKRLKKRLKK" 
            "RLRLKKRLRLKKRLKK" 
            "RLLKRRKLRLLKRRKL" 
            "RLRLRLRLRLRLRLRL" 
        )
        self.linear_fill(80, phrase_80_96, 0.25)
        self.add_hit(80, self.C1, 100); self.add_hit(84, self.C2, 100); self.add_hit(88, self.C1, 100)

        # Section F (0:48 - 1:04 / Beats 96-128): Heavy Half-time Groove 
        seq_heavy = {self.CHN: "8...8...8...8...", self.S: "........9.......", self.K: "9..9..9...99..9.", self.PH: "..7...7...7...7."}
        seq_heavy_2 = {self.CHN: "8...8...8...8...", self.S: "........9..9..9.", self.K: "9..9..9...9..9..", self.PH: "..7...7...7...7."}
        for i in range(8):
            if i % 4 == 3:
                if i == 7:
                    seq = {self.S: "8888....8888....", self.T1: "....8888........", self.T3: "............8888", self.K: "8...8...8...8...", self.CHN:"8...8...8...8..."}
                else:
                    seq = {self.CHN: "8...8...........", self.S: "........9.99.99.", self.K: "9..9..9........."}
            elif i % 4 == 1: seq = seq_heavy_2
            else: seq = seq_heavy
            
            if i % 4 == 0:
                seq = seq.copy()
                seq[self.C1] = "9..............."
            self.play_seq(96 + i * 4, 0.25, seq)

        # Section G (1:04 - 1:12 / Beats 128-144): Motif returned as dense snare drum march
        seq_motif_snare = {self.S: "8.448.448..48..4", self.K: "8.......8.8.....", self.PH:"7...7...7...7..."}
        seq_motif_snare_fill = {self.S: "8.448.4488888888", self.K: "8.......8.8.8.8.", self.PH:"7...7...7...7..."}
        for i in range(4):
            self.play_seq(128 + i * 4, 0.25, seq_motif_snare_fill if i == 3 else seq_motif_snare)

        # Section H (1:12 - 1:20 / Beats 144-160): The 32nd Note Sweeps (Around the kit)
        self.sweep_rolls(144)

        # Section I (1:20 - 1:36 / Beats 160-192): Double Bass Drum Climax
        seq_double_kick = {self.C1: "9.......9.......", self.C2: "....9.......9...", self.S: "....9.......9...", self.K: "9999999999999999"}
        seq_double_kick_fill = {self.C1: "9...............", self.T1: "....9999........", self.T2: "........9999....", self.T4: "............9999", self.K: "9999999999999999"}
        seq_double_kick_syncopated = {self.R1: "9.9.9.9.9.9.9.9.", self.S: "..9...9...9...9.", self.K: "9999999999999999"}
        
        for i in range(8):
            if i >= 4:
                self.play_seq(160 + i * 4, 0.25, seq_double_kick_fill if i % 4 == 3 else seq_double_kick_syncopated)
            else:
                self.play_seq(160 + i * 4, 0.25, seq_double_kick_fill if i % 4 == 3 else seq_double_kick)

        # Section J (1:36 - 1:44 / Beats 192-208): Sudden drop to a funky ghost-note groove to build tension
        seq_funky_soft = {self.CH: "3.1.3.1.5.1.3.1.", self.OH: "........5.......", self.S: "..b.4..b..b.4..b", self.K: "5......55.5....."}
        for i in range(4): self.play_seq(192 + i * 4, 0.25, seq_funky_soft)

        # Section K (1:44 - 1:52 / Beats 208-224): Explode into volume before finale
        seq_funky_build = {self.CH: "7.4.7.4.9.4.7.4.", self.OH: "........9.......", self.S: "..4.8..4..4.8.44", self.K: "9......99.9....."}
        for i in range(4):
            if i == 3:
                self.play_seq(208 + i * 4, 0.25, {self.S: "8888888899999999", self.K: "8...8...8...8...", self.C1: "9.......9.......", self.C2: "....9.......9..."})
            else: self.play_seq(208 + i * 4, 0.25, seq_funky_build)

        # Section L (1:52 - 2:00 / Beats 224-240): The Grand Finale!
        seq_finale_1 = {self.C1: "9.......9.......", self.C2: "....9.......9...", self.T1: "..99..99........", self.T3: "..........99..99", self.K: "9.9.9.9.9.9.9.9."}
        for i in range(2): self.play_seq(224 + i * 4, 0.25, seq_finale_1)

        self.grand_roll(232, 6) # Massive crescendo roll across kit

        # Land the final hit resoundingly after a split second rest (Beat 239)
        self.add_hit(239, self.C1, 127, timing_slop=0, vel_slop=0)
        self.add_hit(239, self.C2, 127, timing_slop=0, vel_slop=0)
        self.add_hit(239, self.K, 127, timing_slop=0, vel_slop=0)
        self.add_hit(239, self.S, 127, timing_slop=0, vel_slop=0)

    def export_midi(self, filename):
        self.hits.sort(key=lambda x: x[0])
        mid = mido.MidiFile(ticks_per_beat=self.ppq)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        # Lock in at 120 BPM base
        track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
        
        last_tick = 0
        for beat, note, vel in self.hits:
            # Macro-timing: The pulse pushes and pulls musically
            warped_beat = beat - 0.02 * math.sin(beat * math.pi / 4)
            # Grand ritardando starting at beat 224 for dramatic heavy final hits
            if beat > 224:
                warped_beat += 0.02 * ((beat - 224) ** 2)
                
            tick = int(warped_beat * self.ppq)
            if tick < last_tick:
                tick = last_tick
            
            delta = tick - last_tick
            track.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=delta))
            track.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=0))
            last_tick = tick
            
        mid.save(filename)

if __name__ == '__main__':
    solo = DrumSolo()
    solo.generate()
    solo.export_midi('solo.mid')
