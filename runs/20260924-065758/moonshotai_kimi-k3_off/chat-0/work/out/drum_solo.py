import mido
import random

# Set a fixed seed for deterministic output
random.seed(42)

# Initialize MIDI file and track
mid = mido.MidiFile(ticks_per_beat=480)
track = mido.MidiTrack()
mid.tracks.append(track)

# Constants
TICKS_PER_BEAT = 480
BPM = 120
MICROSECONDS_PER_BEAT = int(60_000_000 / BPM)
CHANNEL = 9  # MIDI channel 10 (0-indexed)
TOTAL_BEATS = 240  # 2 minutes at 120 BPM
TOTAL_TICKS = TOTAL_BEATS * TICKS_PER_BEAT

# General MIDI drum note mappings
KICK = 36
SNARE = 38
HIHAT_CLOSED = 42
HIHAT_OPEN = 46
CRASH = 49
RIDE = 51
TOM_HIGH = 48
TOM_MID = 47
TOM_LOW = 45

# Set tempo
track.append(mido.MetaMessage('set_tempo', tempo=MICROSECONDS_PER_BEAT, time=0))

# Motif definitions
def motif_a(start_tick, velocity=100):
    """Motif A: Basic rock pattern"""
    events = []
    for i in range(4):
        tick = start_tick + i * TICKS_PER_BEAT
        events.append((tick, KICK, velocity))
        events.append((tick + TICKS_PER_BEAT // 2, SNARE, velocity))
        events.append((tick, HIHAT_CLOSED, velocity // 2))
        events.append((tick + TICKS_PER_BEAT // 2, HIHAT_CLOSED, velocity // 2))
    return events

def motif_b(start_tick, velocity=100):
    """Motif B: Syncopated pattern"""
    events = []
    for i in range(4):
        tick = start_tick + i * TICKS_PER_BEAT
        events.append((tick, KICK, velocity))
        events.append((tick + TICKS_PER_BEAT // 4, SNARE, velocity))
        events.append((tick + TICKS_PER_BEAT // 2, KICK, velocity))
        events.append((tick + 3 * TICKS_PER_BEAT // 4, SNARE, velocity))
    return events

def motif_c(start_tick, velocity=100):
    """Motif C: Tom-based fill"""
    events = []
    for i in range(4):
        tick = start_tick + i * TICKS_PER_BEAT
        events.append((tick, TOM_HIGH, velocity))
        events.append((tick + TICKS_PER_BEAT // 4, TOM_MID, velocity))
        events.append((tick + TICKS_PER_BEAT // 2, TOM_LOW, velocity))
        events.append((tick + 3 * TICKS_PER_BEAT // 4, SNARE, velocity))
    return events

def add_swing(events, swing_amount=0.1):
    """Add swing to events"""
    swung_events = []
    for tick, note, velocity in events:
        if (tick // (TICKS_PER_BEAT // 2)) % 2 == 1:  # Off-beat
            tick += int(TICKS_PER_BEAT * swing_amount)
        swung_events.append((tick, note, velocity))
    return swung_events

def add_ghost_notes(events, ghost_probability=0.3, ghost_velocity=30):
    """Add ghost notes to snare"""
    ghost_events = []
    for tick, note, velocity in events:
        if note == SNARE and random.random() < ghost_probability:
            ghost_tick = tick - TICKS_PER_BEAT // 8
            if ghost_tick >= 0:  # Ensure non-negative tick
                ghost_events.append((ghost_tick, SNARE, ghost_velocity))
    return events + ghost_events

def add_dynamics(events, min_velocity=70, max_velocity=127):
    """Add dynamic variation"""
    dynamic_events = []
    for tick, note, velocity in events:
        new_velocity = random.randint(min_velocity, max_velocity)
        dynamic_events.append((tick, note, new_velocity))
    return dynamic_events

def ensure_playability(events):
    """Ensure at most 4 simultaneous strikes"""
    events.sort()
    playable_events = []
    current_strikes = []
    for event in events:
        tick, note, velocity = event
        current_strikes = [e for e in current_strikes if e[0] == tick]
        if len(current_strikes) < 4:
            playable_events.append(event)
            current_strikes.append(event)
    return playable_events

# Generate the drum solo
all_events = []
current_tick = 0

# Section 1: Introduce Motif A
all_events.extend(motif_a(current_tick))
current_tick += 4 * TICKS_PER_BEAT

# Section 2: Vary Motif A with swing and ghost notes
section_events = add_swing(motif_a(current_tick))
section_events = add_ghost_notes(section_events)
all_events.extend(section_events)
current_tick += 4 * TICKS_PER_BEAT

# Section 3: Introduce Motif B
all_events.extend(motif_b(current_tick))
current_tick += 4 * TICKS_PER_BEAT

# Section 4: Combine Motif A and B with dynamics
section_events = motif_a(current_tick) + motif_b(current_tick + 2 * TICKS_PER_BEAT)
section_events = add_dynamics(section_events)
all_events.extend(section_events)
current_tick += 4 * TICKS_PER_BEAT

# Section 5: Introduce Motif C (fill)
all_events.extend(motif_c(current_tick))
current_tick += 4 * TICKS_PER_BEAT

# Section 6: Recapitulate Motif A with variations
section_events = add_swing(motif_a(current_tick))
section_events = add_ghost_notes(section_events)
section_events = add_dynamics(section_events)
all_events.extend(section_events)
current_tick += 4 * TICKS_PER_BEAT

# Section 7: Final fill and crash
all_events.extend(motif_c(current_tick))
all_events.append((current_tick + 4 * TICKS_PER_BEAT, CRASH, 127))
current_tick += 5 * TICKS_PER_BEAT

# Ensure playability
all_events = ensure_playability(all_events)

# Sort events by tick
all_events.sort()

# Add events to track
last_tick = 0
for tick, note, velocity in all_events:
    delta = tick - last_tick
    if delta < 0:
        delta = 0  # Ensure non-negative delta
    track.append(mido.Message('note_on', note=note, velocity=velocity, time=delta, channel=CHANNEL))
    track.append(mido.Message('note_off', note=note, velocity=0, time=TICKS_PER_BEAT // 4, channel=CHANNEL))
    last_tick = tick + TICKS_PER_BEAT // 4

# Save the MIDI file
mid.save('solo.mid')
