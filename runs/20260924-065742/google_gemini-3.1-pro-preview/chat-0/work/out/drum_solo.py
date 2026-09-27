import mido

# A simple deterministic random number generator to ensure identical runs
class RNG:
    def __init__(self, seed):
        self.state = seed
    def random(self):
        self.state = (self.state * 1103515245 + 12345) & 0x7fffffff
        return self.state / 0x7fffffff
    def randint(self, a, b):
        return a + int(self.random() * (b - a + 1))
    def choice(self, seq):
        return seq[self.randint(0, len(seq)-1)]

rng = RNG(808)

# GM Percussion Note Map
KICK = 36
SNARE_RIM = 37
SNARE = 38
SNARE_GHOST = 38
TOM4 = 41
HH_CLOSED = 42
TOM3 = 43
HH_PEDAL = 44
HH_OPEN = 46
TOM2 = 47
CRASH1 = 49
TOM1 = 50
RIDE = 51
CHINA = 52
RIDE_BELL = 53
SPLASH = 55
COWBELL = 56
CRASH2 = 57
CONGA_HI_MUTE = 62
CONGA_HI_OPEN = 63
CONGA_LO = 64
TIMBALE_HI = 65
TIMBALE_LO = 66

# Dynamics
GHOST = 35
SOFT = 55
MED = 85
HARD = 110
CRASH_VEL = 120

hits = []

def get_tick(measure, sixteenth):
    """Convert a measure and 16th note position into absolute MIDI ticks, applying a natural swing."""
    integer_part = int(sixteenth)
    fraction = sixteenth - integer_part
    
    # 120 ticks per 16th note at 480 PPQ
    tick = measure * 1920 + integer_part * 120 + fraction * 120
    
    # Apply a subtle 16th-note swing (pushing the 'e' and 'a' slightly late)
    swing_amount = 12
    if integer_part % 2 == 1:
        tick += swing_amount * (1 - fraction)
    elif fraction > 0:
        tick += swing_amount * fraction
        
    return int(tick)

def add_hit(measure, sixteenth, note, vel):
    """Add a drum hit with micro-timing and velocity humanization."""
    tick = get_tick(measure, sixteenth)
    
    # Humanize velocity (+/- 4)
    vel = max(1, min(127, int(vel) + rng.randint(-4, 4)))
    
    # "Lay back" the backbeats (beats 2 and 4, which are 16ths 4.0 and 12.0)
    # Also half-time backbeat on 8.0
    if note == SNARE and vel > 90:
        if abs(sixteenth - 4.0) < 0.1 or abs(sixteenth - 12.0) < 0.1 or abs(sixteenth - 8.0) < 0.1:
            tick += 8 # Delayed by 8 ticks for a deeper pocket
            
    # Micro-humanize timing
    tick += rng.randint(-2, 2)
    
    hits.append((tick, note, vel))

def intro_groove(start_m, num_m):
    """A syncopated, linear hi-hat/snare/kick groove building up the main motif."""
    for m in range(start_m, start_m + num_m):
        is_last = (m == start_m + num_m - 1)
        
        # Downbeat crash marking the phrasing
        if m == start_m:
            add_hit(m, 0, CRASH1, HARD)
            add_hit(m, 0, KICK, HARD)
        else:
            add_hit(m, 0, HH_CLOSED, MED)
            add_hit(m, 0, KICK, HARD)
            
        add_hit(m, 1, HH_CLOSED, SOFT)
        add_hit(m, 2, HH_CLOSED, MED)
        add_hit(m, 3, KICK, MED)
        
        add_hit(m, 4, SNARE, HARD)
        add_hit(m, 4, HH_CLOSED, MED)
        
        add_hit(m, 5, HH_CLOSED, SOFT)
        add_hit(m, 6, KICK, MED)
        add_hit(m, 7, HH_CLOSED, MED)
        
        if m % 2 == 0: 
            add_hit(m, 8, HH_CLOSED, SOFT)
            add_hit(m, 9, KICK, SOFT)
            add_hit(m, 10, SNARE, GHOST)
            add_hit(m, 11, HH_CLOSED, MED)
            add_hit(m, 12, SNARE, HARD)
            add_hit(m, 12, HH_CLOSED, MED)
            add_hit(m, 13, HH_CLOSED, SOFT)
            add_hit(m, 14, KICK, MED)
            add_hit(m, 15, HH_OPEN, MED)
            add_hit(m+1, 0, HH_PEDAL, MED) # Snaps shut on next downbeat
        else: 
            add_hit(m, 8, KICK, MED)
            add_hit(m, 9, HH_CLOSED, SOFT)
            add_hit(m, 10, KICK, MED)
            add_hit(m, 11, HH_OPEN, MED)
            add_hit(m, 12, SNARE, HARD)
            add_hit(m, 12, HH_PEDAL, MED)
            
            if not is_last:
                add_hit(m, 13, SNARE, GHOST)
                add_hit(m, 14, SNARE, GHOST)
                add_hit(m, 15, SNARE, MED)
            else:
                # Setup fill
                add_hit(m, 12.5, TOM1, MED)
                add_hit(m, 13, TOM1, MED)
                add_hit(m, 13.5, TOM2, MED)
                add_hit(m, 14, TOM2, HARD)
                add_hit(m, 14.5, TOM3, MED)
                add_hit(m, 15, TOM3, HARD)
                add_hit(m, 15.5, TOM4, HARD)

def motif_a(start_m, num_m):
    """Tribal tom groove playing around a 3-2 son clave mapped to the ride bell."""
    clave = [0, 3, 6, 10, 12]
    for m in range(start_m, start_m + num_m):
        is_last = (m == start_m + num_m - 1)
        
        for i in [0, 4, 8, 12]:
            add_hit(m, i, HH_PEDAL, SOFT)
            
        for c in clave:
            if c == 0 and (m == start_m or m == start_m + 4):
                inst = CRASH2 if m == start_m else SPLASH
                add_hit(m, 0, inst, HARD)
                add_hit(m, 0, KICK, HARD)
            else:
                add_hit(m, c, RIDE_BELL, HARD)
                add_hit(m, c, KICK, MED)
            
        if not is_last:
            add_hit(m, 1, TOM3, SOFT)
            add_hit(m, 2, TOM4, MED)
            add_hit(m, 4, SNARE, GHOST)
            add_hit(m, 5, TOM1, MED)
            add_hit(m, 7, TOM2, MED)
            add_hit(m, 8, SNARE, MED)
            add_hit(m, 9, TOM3, SOFT)
            add_hit(m, 11, TOM4, MED)
            add_hit(m, 13, SNARE, GHOST)
            add_hit(m, 14, TOM1, MED)
            add_hit(m, 15, TOM2, SOFT)
        else:
            for i in range(8):
                add_hit(m, i, SNARE, MED + i*4)
            for i in range(8, 16):
                add_hit(m, i, TOM4 if i%2==0 else TOM3, HARD)
                add_hit(m, i, KICK, MED)

def motif_b(start_m, num_m):
    """Afro-Cuban inspired section using the GM Percussion set."""
    cascara = [0, 2, 3, 5, 7, 8, 10, 11, 13, 15]
    for m in range(start_m, start_m + num_m):
        is_last = (m == start_m + num_m - 1)
        
        if not is_last:
            for c in cascara:
                if c == 0 and m == start_m:
                    add_hit(m, 0, CRASH1, HARD)
                else:
                    add_hit(m, c, COWBELL, MED if c in [2,5,10,13] else HARD)
                
            for k in [0, 6, 8, 14]:
                add_hit(m, k, KICK, HARD)
                
            for h in [4, 12]:
                add_hit(m, h, HH_PEDAL, MED)
                
            # Left Hand weaving through congas and timbales
            add_hit(m, 1, CONGA_HI_MUTE, MED)
            add_hit(m, 4, CONGA_LO, HARD)
            add_hit(m, 6, TIMBALE_HI, HARD)
            add_hit(m, 9, CONGA_HI_OPEN, MED)
            add_hit(m, 12, CONGA_LO, HARD)
            add_hit(m, 14, TIMBALE_LO, HARD)
        else:
            # Huge timbale/snare roll fill
            for i in range(16):
                vel = 50 + i * 4
                add_hit(m, i, TIMBALE_HI if i < 8 else SNARE, vel)
                if i % 4 == 0:
                    add_hit(m, i, KICK, HARD)

def build_up(start_m, num_m):
    """Tension building: starts with quiet linear patterns, erupts into heavy rolls."""
    for m in range(start_m, start_m + 4):
        vel_base = 40 + (m - start_m) * 15
        for b in range(4):
            base_16 = b * 4
            rh_inst = [SNARE_RIM, HH_CLOSED, TOM1, TOM2][b % 4]
            lh_inst = [SNARE_GHOST, SNARE_GHOST, TOM2, TOM3][b % 4]
            
            if m == start_m + 3:
                rh_inst, lh_inst = TOM3, TOM4
                vel_base += 10
            
            add_hit(m, base_16 + 0, rh_inst, vel_base + 10)
            add_hit(m, base_16 + 1, lh_inst, vel_base)
            add_hit(m, base_16 + 2, KICK, vel_base + 20)
            add_hit(m, base_16 + 3, KICK, vel_base + 20)
            
    for m in range(start_m + 4, start_m + 8):
        is_last = (m == start_m + 7)
        vel_base = 90 + (m - start_m - 4) * 8
        for i in range(16):
            if not is_last:
                if i % 2 == 0:
                    add_hit(m, i, CRASH1 if (i//2)%2==0 else CHINA, vel_base)
                else:
                    add_hit(m, i, SNARE, vel_base)
                
                if i % 4 == 0:
                    add_hit(m, i, KICK, HARD)
            else:
                if i < 8:
                    add_hit(m, i, SNARE, vel_base)
                    add_hit(m, i + 0.5, SNARE, vel_base) # 32nd note roll
                    if i % 4 == 0:
                        add_hit(m, i, KICK, HARD)
                elif i == 8 or i == 12:
                    add_hit(m, i, SNARE, CRASH_VEL)
                    add_hit(m, i, CRASH1 if i == 8 else CRASH2, CRASH_VEL)
                    add_hit(m, i, KICK, HARD)

def climax(start_m, num_m):
    """The solo peak: intricate hand phrasing over a relentless Samba foot ostinato."""
    samba_kick = [0, 3, 4, 7, 8, 11, 12, 15]
    samba_hh = [2, 6, 10, 14]
    
    for m in range(start_m, start_m + num_m):
        is_last = (m == start_m + num_m - 1)
        
        if not is_last:
            for k in samba_kick:
                add_hit(m, k, KICK, HARD if k%4==0 else MED)
            for h in samba_hh:
                add_hit(m, h, HH_PEDAL, HARD)
            
        if m == start_m:
            add_hit(m, 0, CRASH1, CRASH_VEL)
            
        phrase_group = (m - start_m) // 4
        
        if is_last:
            for i in range(16):
                inst = [TOM1, TOM2, TOM3, TOM4][i // 4]
                vel = HARD if i % 2 == 0 else MED
                add_hit(m, i, inst, vel)
                if not (i == 15):
                    add_hit(m, i + 0.5, inst, vel - 10)
            continue
            
        if phrase_group == 0:
            # 3-over-4 polyrhythm phrasing (R-L-R-rest)
            for i in range(16):
                pos = i % 4
                if pos < 3:
                    inst = SNARE if pos == 1 else RIDE_BELL
                    add_hit(m, i, inst, HARD if pos == 0 else MED)
        elif phrase_group == 1:
            # Fragmented syncopations jumping around the kit
            for i in range(16):
                if rng.random() > 0.5:
                    inst = rng.choice([SNARE, TOM1, TOM2, CRASH1])
                    add_hit(m, i, inst, HARD if inst == CRASH1 else MED)
                else:
                    if rng.random() > 0.7:
                        add_hit(m, i, SNARE_GHOST, SOFT)
        elif phrase_group == 2:
            # Sudden explosive 32nd note linear sweeps
            for beat in range(4):
                if rng.random() > 0.5:
                    inst = [SNARE, TOM1, TOM2, TOM3, TOM4][rng.randint(0, 4)]
                    for sub in [0, 0.5, 1, 1.5]:
                        vel_hit = HARD if sub == 0 else SOFT + 10
                        add_hit(m, beat*4 + sub, inst, vel_hit)
                else:
                    add_hit(m, beat*4 + 1.5, CHINA, HARD)
                    add_hit(m, beat*4 + 3.5, SPLASH, HARD)
        elif phrase_group == 3:
            # Crushing double stops
            for i in range(16):
                vel = 60 + i * 3
                if i % 2 == 0:
                    add_hit(m, i, SNARE, vel)
                    add_hit(m, i, TOM4, vel)
                else:
                    add_hit(m, i, TOM1, vel)
                    add_hit(m, i, TOM2, vel)

def outro(start_m, num_m):
    """Half-time feel breakdown, ending with a thunderous tom/crash roll and final hit."""
    for m in range(start_m, start_m + num_m):
        is_last = (m == start_m + num_m - 1)
        is_second_to_last = (m == start_m + num_m - 2)
        
        if not is_last and not is_second_to_last:
            for i in range(0, 16, 2):
                if i == 0 and m == start_m:
                    add_hit(m, 0, CRASH1, CRASH_VEL)
                elif i == 0 and (m - start_m) % 2 == 1:
                    add_hit(m, 0, CRASH2, HARD)
                else:
                    add_hit(m, i, RIDE, MED)
            
            add_hit(m, 0, KICK, HARD)
            add_hit(m, 3, KICK, MED) 
            add_hit(m, 8, SNARE, HARD)
            add_hit(m, 10, KICK, MED)
            add_hit(m, 14, SNARE_GHOST, SOFT)
            
            add_hit(m, 4, HH_PEDAL, MED)
            add_hit(m, 12, HH_PEDAL, MED)
            
            if (m - start_m) % 2 == 1:
                add_hit(m, 8, CRASH2, HARD)
                
        elif is_second_to_last:
            for i in range(16):
                vel = 70 + i * 3
                if i % 4 == 0:
                    add_hit(m, i, CRASH1, HARD)
                else:
                    add_hit(m, i, TOM4, vel)
                    
                add_hit(m, i+0.5, TOM3, vel) 
                add_hit(m, i, KICK, HARD)
        else:
            add_hit(m, 0, CRASH1, CRASH_VEL)
            add_hit(m, 0, CRASH2, CRASH_VEL)
            add_hit(m, 0, KICK, HARD)

# Compose the 60 measures (exactly 2 mins at 120 BPM)
intro_groove(0, 8)
motif_a(8, 8)
motif_b(16, 8)
build_up(24, 8)
climax(32, 16)
outro(48, 12)

# Generate MIDI
mid = mido.MidiFile(ticks_per_beat=480)
track = mido.MidiTrack()
mid.tracks.append(track)

track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))

events = []
for (tick, note, vel) in hits:
    events.append({'tick': tick, 'type': 'note_on', 'note': note, 'vel': vel})
    # 60 ticks is roughly a 32nd note duration
    events.append({'tick': tick + 60, 'type': 'note_off', 'note': note, 'vel': 0})

events.sort(key=lambda e: (e['tick'], 0 if e['type'] == 'note_off' else 1))

current_tick = 0
for e in events:
    delta = max(0, e['tick'] - current_tick)
    if e['type'] == 'note_on':
        track.append(mido.Message('note_on', channel=9, note=e['note'], velocity=e['vel'], time=delta))
    else:
        track.append(mido.Message('note_off', channel=9, note=e['note'], velocity=0, time=delta))
    current_tick += delta

# Force track length to exactly 60 measures
end_tick = 60 * 1920
if end_tick > current_tick:
    track.append(mido.MetaMessage('text', text='end', time=end_tick - current_tick))

mid.save('solo.mid')
