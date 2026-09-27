import mido
import random

class Tracker:
    def __init__(self):
        self.notes = []
        # Use a fixed seed for deterministic output on every run
        self.random = random.Random(42)

    def add_note(self, beat, note, vel, duration=0.1, swing=0.0):
        # 16th note swing logic: delay the off-beat 16ths
        frac = beat % 0.5
        if 0.15 < frac < 0.35:
            beat += swing
            
        # Subtle humanization in timing (push/pull +/- ~7 ticks at 120bpm)
        timing_shift = self.random.uniform(-0.015, 0.015)
        beat += timing_shift
        
        # Subtle humanization in velocity
        vel_shift = self.random.randint(-8, 8)
        vel = max(1, min(127, vel + vel_shift))

        self.notes.append({
            'beat': beat,
            'note': note,
            'vel': vel,
            'dur': duration
        })

# General MIDI Drum Map Definitions
MAP = {
    'K': (36, 115),  # Kick hard
    'k': (36, 75),   # Kick soft (ghost)
    'S': (38, 115),  # Snare hard
    's': (38, 55),   # Snare ghost
    'R': (37, 105),  # Rim click
    'H': (42, 95),   # Closed Hi-Hat
    'h': (42, 60),   # Closed Hi-Hat soft
    'O': (46, 95),   # Open Hi-Hat
    'P': (44, 90),   # Pedal Hi-Hat
    'C': (49, 115),  # Crash 1
    'D': (57, 115),  # Crash 2
    'Z': (55, 110),  # Splash Cymbal
    'Q': (52, 115),  # Chinese Cymbal
    'T': (50, 110),  # High Tom
    't': (50, 75),   # High Tom soft
    'U': (47, 110),  # Low-Mid Tom
    'u': (47, 75),   # Low-Mid Tom soft
    'V': (43, 110),  # High Floor Tom
    'v': (43, 75),   # High Floor Tom soft
    'W': (41, 110),  # Low Floor Tom
    'w': (41, 75),   # Low Floor Tom soft
    'I': (51, 95),   # Ride Cymbal
    'i': (51, 65),   # Ride Cymbal soft
    'B': (53, 105),  # Ride Bell
    'b': (53, 75),   # Ride Bell soft
    'L': (56, 100),  # Cowbell
    'M': (65, 105),  # High Timbale
    'N': (66, 105),  # Low Timbale
    'X': (63, 90),   # Open High Conga
    'Y': (64, 90),   # Low Conga
    '.': None        # Rest
}

class DrumSolo:
    def __init__(self):
        self.tracker = Tracker()
        self.beat = 0
    
    def phrase(self, step_size, **tracks):
        """Sequences a phrase based on text tracks, ensuring realistic hand/foot placement."""
        max_len = max(len(s) for s in tracks.values())
        # Less swing on fast 32nd note runs to keep the chops clean
        current_swing = 0.04 if step_size >= 0.25 else 0.01 
        
        for name, pattern in tracks.items():
            for i, char in enumerate(pattern):
                if char in MAP and MAP[char] is not None:
                    note, vel = MAP[char]
                    self.tracker.add_note(self.beat + i * step_size, note, vel, swing=current_swing)
        self.beat += max_len * step_size

    def crescendo_roll(self, beats, note, start_vel, end_vel, step_size, bass_drum_step=1.0):
        """Generates an intense swelling roll."""
        start_beat = self.beat
        end_beat = start_beat + beats
        cur_beat = start_beat
        while cur_beat < end_beat - 0.001:
            progress = (cur_beat - start_beat) / beats
            vel = int(start_vel + (end_vel - start_vel) * progress)
            self.tracker.add_note(cur_beat, note, vel, swing=0.0)
            
            # Anchor the roll with bass drum pulses
            epsilon = 1e-5
            rem = cur_beat % bass_drum_step
            if rem < epsilon or (bass_drum_step - rem) < epsilon:
                self.tracker.add_note(cur_beat, MAP['K'][0], MAP['K'][1], swing=0.0)
                
            cur_beat += step_size
        self.beat += beats

def compose_solo():
    solo = DrumSolo()

    # Section 1: Intro (Bars 1-4) - Waking up the kit, sparse rim clicks and hi-hat splashes
    solo.phrase(0.25, cym="C...............", kik="K...............", hat="..........P...P.")
    solo.phrase(0.25, cym="Z...............", hat="P...P...P...P...", snr="....R.......R...", kik="K.......K.k.K...")
    solo.phrase(0.25, hat="H.h.H.h.H.h.O...", snr="....R.......R...", kik="K.......K.k.K...")
    solo.phrase(0.25, hat="H.h.H.h.H.h.O...", snr="....R.......S.ss", kik="K.......K.k.K...")

    # Section 2: Motif A (Bars 5-8) - Funk groove heavily utilizing snare ghost notes
    solo.phrase(0.25, cym="C...............", hat="..h.H.h.H.h.H.h.", snr="....S.......S...", kik="K.......k.K.....")
    solo.phrase(0.25, hat="H.h.H.h.H.h.O...", snr="..s.S..s..s.S.ss", kik="K.......k.K.....")
    solo.phrase(0.25, hat="H.h.H.h.H.h.H.h.", snr="....S.......S...", kik="K.......k.K...k.")
    solo.phrase(0.25, hat="H.h.H.h.H.......", snr="..s.S..s..S.S.ss", kik="K.......k.K.....", tom="............V.W.")

    # Section 3: Ride Development (Bars 9-16) - Moving to the ride bell, pushing the kick pattern
    solo.phrase(0.25, cym="C...............", rid="..i.I.i.B.i.I.i.", snr="....S.......S...", kik="K.......k.K.....")
    solo.phrase(0.25, rid="I.i.I.i.B.i.I.i.", snr="..s.S..s..s.S.ss", kik="K..k....k.K.....", hat="P.......P.......")
    solo.phrase(0.25, rid="I.i.I.i.B.i.I.i.", snr="....S.......S...", kik="K.k.....k.K...k.", hat="P.......P.......")
    solo.phrase(0.25, rid="I.i.I.i.........", snr="..s.S..sS.ss....", tom="............T.U.", kik="K.......K.K.K.K.")
    solo.phrase(0.25, cym="D...............", rid="..i.I.i.B.i.I.i.", snr="....S.......S...", kik="K..k..k.K..k..k.", hat="P.......P.......")
    solo.phrase(0.25, rid="I.i.I.i.B.i.I.i.", snr="..s.S..s..s.S.ss", kik="K.......k.K.....", hat="P.......P.......")
    solo.phrase(0.25, rid="I.i.I.i.B.i.I.i.", snr="....S.......S...", kik="K.k...k.K.k...k.", hat="P.......P.......")
    solo.phrase(0.25, snr="S.ssS.ssS.......", tom="........U.UUW.WW", kik="K.K.K.K.K.K.K.K.")

    # Section 4: Percussion Feature (Bars 17-24) - Incorporating Latin elements with GM percussion
    solo.phrase(0.25, cym="C...............", cwb="..L...L...L...L.", tmh="M...M...M...M...", kik="K.......k.......", hat="....P.......P...")
    solo.phrase(0.25, cwb="..L...L...L...L.", tmh="M..MM...M..MM...", tml="......N.......N.", kik="K.......k.......", hat="....P.......P...")
    solo.phrase(0.25, cwb="..L...L...L...L.", con="X.Y.X.Y.X.Y.X.Y.", kik="K.......k.......", hat="....P.......P...")
    solo.phrase(0.25, cwb="..L...L...L...L.", con="X..Y..X..Y..X..Y", kik="K.......k.......", hat="....P.......P...")  # Polyrhythm feel
    solo.phrase(0.25, cym="Z...............", rid="B.b.B.b.B.b.B.b.", snr="....R.......R...", kik="K.......K.k.K...")
    solo.phrase(0.25, rid="B.b.B.b.B.b.B.b.", snr="....R.......R...", kik="K..k....K.k.K...")
    solo.phrase(0.25, rid="B.b.B.b.B.b.B.b.", snr="....R.......R...", kik="K.k...k.K.k.K...")
    solo.phrase(0.125, snr="S.s.s.s.S.s.s.s.S.s.s.s.........", tom="........................T.t.U.u.", kik="K.......K.......K.......K.......") # 32nd notes

    # Section 5: The Build-up (Bars 25-32) - Jungle/tribal tom groove building density
    solo.phrase(0.25, cym="C...............", tom="..W.W.W.W.W.W.W.", snr="....S.......S...", kik="K.......K.K.....")
    solo.phrase(0.25, tom="W.W.W.W.W.W.W.W.", snr="..s.S..s..s.S.ss", kik="K.......K.K.....")
    solo.phrase(0.25, tom="W.W.W.W.W.W.W.W.", snr="....S.......S...", kik="K..K....K.K...K.")
    solo.phrase(0.25, tom="W.W.W.W.........", snr="..s.S...ssssssss", kik="K.......K.K.K.K.")
    solo.phrase(0.25, cym="C.......D.......", tom="..W.W.W...W.W.W.", snr="....S.......S...", kik="K.K.K.K.K.K.K.K.")
    solo.phrase(0.25, tom="W.W.W.W.W.W.W.W.", snr="..s.S..s..s.S.ss", kik="K.K.K.K.K.K.K.K.")
    solo.phrase(0.25, tom="W.W.W.W.W.W.W.W.", snr="....S.......S...", kik="K.K.K.K.K.K.K.K.")
    solo.phrase(0.125, snr="S.S.S.S.s.s.s.s.................", t1="................T.T.T.T.........", t2="........................U.U.U.U.", kik="K...K...K...K...K...K...K...K...")

    # Section 6: Climax (Bars 33-40) - Heavy half-time groove, double bass, chinas
    solo.phrase(0.25, cym="C.......C.......", snr="........S.......", kik="K.k.K.k.K.k.K.k.")
    solo.phrase(0.25, cym="C...C...C...C...", snr="........S.......", kik="K.K.K.K.K.K.K.K.")
    solo.phrase(0.25, cym="C.......C.......", snr="........S.......", kik="K.k.K.k.K.k.K.k.", tom="..............W.")
    solo.phrase(0.25, cym="C...Q...C.......", snr="........S.ssS.ss", kik="K.K.K.K.K.K.K.K.")
    solo.phrase(0.25, cym="C.......C.......", snr="........S.......", kik="K.k.K.k.K.k.K.k.")
    solo.phrase(0.25, cym="C...Q...C...C...", snr="........S.......", kik="K.K.K.K.K.K.K.K.")
    solo.phrase(0.25, cym="C.......C.......", snr="........S.......", kik="K.k.K.k.K.k.K.k.")
    solo.phrase(0.125, snr="S.s.s.s.S.s.s.s.S.s.s.s.S.s.s.s.", kik="K.......K.......K.......K.......")

    # Section 7: The Drummer's Showcase (Bars 41-48) - Linear gospel chops & massive snare swell
    solo.phrase(0.25, cym="C...............D...............", hat="..H.h...H.h.......H.h...H.O.....", snr="......S.....S.........S.....S...", kik="K...K.....K...K.K...K.....K...K.", tom="..............U...............W.")
    solo.phrase(0.25, cym="C.......Z.......C...C...C.......", snr="..S..S......S.....S...S...S.S.S.", kik="K..K..K.K..K..K.K...K...K.......", tom="............................U.W.")
    solo.phrase(0.25, tom="T.t.t.t.U.u.u.u.V.v.v.v.W.w.w.w.", kik="K.......K.......K.......K.......", snr="................................")
    solo.crescendo_roll(8, MAP['S'][0], 50, 127, 0.125, bass_drum_step=1.0) # 8 beats = 2 bars of intense snare roll

    # Section 8: Tension Release (Bars 49-56) - A massive, fat, laying-back return to the motif
    solo.phrase(0.25, cym="C...............", hat="..P...P...P...P.", snr="................", kik="K...............")
    solo.phrase(0.25, cym="Z...............", hat="..P...P...P...P.", snr="........R.......", kik="K...........K...")
    solo.phrase(0.25, hat="H.H.H.H.H.H.H.H.", snr="........S.......", kik="K...........K...")
    solo.phrase(0.25, hat="H.H.H.H.O.......", snr="........S.ssS.ss", kik="K...........K...")
    solo.phrase(0.25, cym="C...............D...............", hat="..H.H.H.H.H.O.....H.H.H.H.H.O...", snr="....S.......S.......S.......S...", kik="K.......K.K.....K.......K.K.....")
    solo.phrase(0.25, cym="C...............Z.......Z.......", snr="....S.ssS.ssS.......S.......S...", tom="..............U...............W.", kik="K.K.....K.K.....K.......K.......")

    # Section 9: Outro (Bars 57-60) - Deconstructive fading
    solo.phrase(0.25, cym="C...............", kik="K...............", hat="..........P...P.")
    solo.phrase(0.25, cym="Z...............", kik="K...............", hat="P...P...P...P...")
    solo.phrase(0.25, kik="K...............", snr="....R...........", hat="P.......P.......")
    solo.phrase(0.25, cym="C...............", kik="K...............", snr="S...............") # Final hit

    return solo

def create_midi(solo, filename="solo.mid"):
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    track0 = mido.MidiTrack()
    track1 = mido.MidiTrack()
    mid.tracks.append(track0)
    mid.tracks.append(track1)

    # Let the tempo breathe: leaning forward in intense sections, laying back in grooves
    tempo_map = [
        (0, 118),   # Intro: relaxed
        (16, 122),  # Motif A: slightly pushed
        (32, 122),  # Development
        (64, 125),  # Percussion/Latin: energetic
        (96, 124),  # Build-up
        (128, 126), # Climax half-time (heavy pushing)
        (160, 128), # Chops (fast)
        (192, 118), # Release/Drop
        (224, 114), # Outro start
        (228, 108), 
        (232, 100),
        (236, 90),  # Final bar ritardando
        (238, 80), 
        (239, 70)
    ]

    tempo_events = []
    tempo_events.append({
        'abs_tick': 0,
        'msg': mido.MetaMessage('time_signature', numerator=4, denominator=4)
    })
    
    for beat, bpm in tempo_map:
        tempo_events.append({
            'abs_tick': int(beat * 480),
            'msg': mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm))
        })

    tempo_events.sort(key=lambda x: x['abs_tick'])
    last_tick = 0
    for ev in tempo_events:
        delta = ev['abs_tick'] - last_tick
        ev['msg'].time = max(0, delta)
        track0.append(ev['msg'])
        last_tick = ev['abs_tick']
        
    note_events = []
    for n in solo.tracker.notes:
        start_tick = int(n['beat'] * 480)
        end_tick = int((n['beat'] + n['dur']) * 480)
        
        note_events.append({
            'abs_tick': start_tick,
            'msg': mido.Message('note_on', channel=9, note=n['note'], velocity=n['vel'])
        })
        note_events.append({
            'abs_tick': end_tick,
            'msg': mido.Message('note_off', channel=9, note=n['note'], velocity=0)
        })

    # Sort chronologically. Note Offs before Note Ons if they land on the exact same tick.
    note_events.sort(key=lambda x: (x['abs_tick'], 0 if x['msg'].type == 'note_off' else 1))
    
    last_tick = 0
    for ev in note_events:
        delta = ev['abs_tick'] - last_tick
        ev['msg'].time = max(0, delta)
        track1.append(ev['msg'])
        last_tick = ev['abs_tick']

    mid.save(filename)

if __name__ == "__main__":
    solo = compose_solo()
    create_midi(solo)
