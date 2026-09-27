import random
from mido import Message, MidiFile, MidiTrack, MetaMessage

# ---------- deterministic randomness ----------
random.seed(20240517)

TPB = 480  # ticks per beat

# Note numbers (GM percussion)
KICK, SNARE, STICK, CLAP = 36, 38, 37, 39
SNARE2, TOM_F, HTOM, TOM_M = 40, 41, 47, 45
TOM_L, HAT, PEDAL_HAT, RIDE = 43, 42, 44, 51
RIDE_BELL, CRASH, CRASH2 = 53, 49, 57
SPLASH, CHINA, RIDE2 = 55, 52, 59
TAMB, COWBELL, TRI_HI, TOM2_BONGO = 54, 56, 81, 60

events = []  # (tick, note, velocity)

def hit(tick, note, vel):
    t = int(round(tick))
    v = int(round(vel))
    if v < 1: v = 1
    if v > 127: v = 127
    if t < 0: t = 0
    events.append((t, note, v))

def empty_set(n):
    s = set()
    for e in n:
        s.add(e[1])
    return s

def can_play(active, note):
    # hands: snare/hat/ride/crash/toms count as hand hits; feet: kick/pedal hat
    # We'll enforce: at most 2 hands total sounding, at most 2 feet.
    feet_notes = {KICK, PEDAL_HAT}
    hands = [x for x in active if x not in feet_notes]
    feet = [x for x in active if x in feet_notes]
    is_foot = note in feet_notes
    if is_foot:
        return True  # allow polyphony to be limited by other logic
    return True

def place(tick, note, vel, lookahead=6):
    # crude collision check: don't exceed 2 sounding hands at once
    t = int(round(tick))
    feet_notes = {KICK, PEDAL_HAT}
    # gather notes within small decay window (nobody sustains > ~50 ms in drum terms)
    recent = set()
    for (et, en, ev) in events:
        if abs(et - t) < lookahead and en not in feet_notes:
            recent.add(en)
    if note not in feet_notes and len(recent) >= 2 and note not in recent:
        return False
    hit(tick, note, vel)
    return True

def jitter_grid(beat, subdivision, off=0.0, jit=0.012):
    # beat: float beats. subdivision: notes per beat (e.g. 4 for 16ths)
    return (beat + off) * TPB + random.uniform(-jit, jit) * TPB

def swing_off(beat):
    # subtle swing feel for off-16ths
    return 0.02

def dyn(base, spread=10):
    return max(1, min(127, base + random.randint(-spread, spread)))

# ---------- motifs ----------

def motif_A(t0, bars=1, accent=True):
    """Downbeat kick, backbeat snare, ghost 16ths on snare, hats."""
    for b in range(bars):
        bt = t0 + b * 4.0
        # hats throughout with dynamic shape
        for i in range(16):
            pos = i / 4.0
            vel = 38 + (14 if i % 4 == 0 else 0) + random.randint(-6, 6)
            if i == 0:
                vel += 10
            hit(jitter_grid(bt, 4, pos), HAT, vel)
        # kick pattern
        hit(jitter_grid(bt, 4, 0.0), KICK, dyn(108, 6))
        hit(jitter_grid(bt, 4, 1.75 + swing_off(bt)), KICK, dyn(88, 8))
        hit(jitter_grid(bt, 4, 2.5), KICK, dyn(78, 8))
        # backbeat snare with ghosts
        hit(jitter_grid(bt, 4, 1.0), SNARE, dyn(112 if accent else 100, 6))
        hit(jitter_grid(bt, 4, 3.0), SNARE, dyn(114 if accent else 102, 5))
        # ghost notes
        for g in (0.5, 1.25, 2.25, 3.5):
            if random.random() < 0.7:
                hit(jitter_grid(bt, 4, g), SNARE, dyn(32, 6))
        # crash on bar start sometimes
        if b == 0 and random.random() < 0.5:
            hit(jitter_grid(bt, 4, 0.0), CRASH, dyn(86, 5))

def motif_B(t0, bars=1):
    """Ride pattern with accents and kick snare interplay."""
    for b in range(bars):
        bt = t0 + b * 4.0
        for i in range(8):  # 8ths
            pos = i / 2.0
            vel = 58 + (12 if i % 2 == 0 else 0) + random.randint(-6, 6)
            ride_note = RIDE if i % 2 == 0 else RIDE2
            hit(jitter_grid(bt, 2, pos), ride_note, vel)
        # snare backbeats
        hit(jitter_grid(bt, 4, 1.0), SNARE, dyn(110, 5))
        hit(jitter_grid(bt, 4, 3.0), SNARE, dyn(112, 5))
        # kick
        hit(jitter_grid(bt, 4, 0.0), KICK, dyn(100, 8))
        hit(jitter_grid(bt, 4, 2.75), KICK, dyn(84, 8))
        if random.random() < 0.5:
            hit(jitter_grid(bt, 4, 1.5), KICK, dyn(70, 10))
        # occasional ghost
        if random.random() < 0.5:
            hit(jitter_grid(bt, 4, 2.25), SNARE, dyn(30, 5))

def motif_C_down(t0, bars=1):
    """Dense tom motif descending."""
    for b in range(bars):
        bt = t0 + b * 4.0
        for i in range(16):
            pos = i / 4.0
            # descend across toms
            n = [HTOM, TOM_M, TOM_F, TOM_L][i % 4]
            vel = 60 + (25 if i % 2 == 0 else 0) + random.randint(-8, 8)
            hit(jitter_grid(bt, 4, pos), n, vel)
        # snare on backbeats strong
        hit(jitter_grid(bt, 4, 1.0), SNARE, dyn(105, 6))
        hit(jitter_grid(bt, 4, 3.0), SNARE, dyn(108, 6))
        hit(jitter_grid(bt, 4, 0.0), KICK, dyn(102, 6))

def roll_sweep(t0, beats=2.0, start_vel=40, end_vel=118, note_list=None):
    """Even sweep roll with crescendo across kits."""
    if note_list is None:
        note_list = [SNARE, TOM_F, TOM_M, HTOM, TOM_L]
    n_notes = int(beats * 8)  # 32nd notes
    for i in range(n_notes):
        pos = i / 8.0
        frac = i / max(1, n_notes - 1)
        vel = start_vel + (end_vel - start_vel) * frac + random.uniform(-6, 6)
        n = note_list[(i // 2) % len(note_list)]
        hit(jitter_grid(t0, 8, pos), n, vel)

def double_stroke_run(t0, beats=2.0, base=75, notes=None):
    if notes is None:
        notes = [SNARE, TOM_F, TOM_M, TOM_L, HTOM]
    n = int(beats * 4)
    for i in range(n):
        pos = i / 4.0
        nn = notes[i % len(notes)]
        # doubles: two hits, first accent, second softer
        hit(jitter_grid(t0, 4, pos), nn, base + random.randint(-5, 8))
        hit(jitter_grid(t0, 4, pos + 0.0625), nn, base - 18 + random.randint(-5, 6))

def fill_one_beat(t0, style=0):
    bt = t0
    if style == 0:
        # 16th triplets snare->toms
        for i in range(6):
            pos = i / 6.0 * 1.0
            nn = [SNARE, SNARE, TOM_F, TOM_M, TOM_L, HTOM][i]
            hit(jitter_grid(bt, 6, pos), nn, 80 + i * 5 + random.randint(-6, 6))
    elif style == 1:
        for i in range(8):
            pos = i / 4.0
            nn = [SNARE, SNARE, SNARE, TOM_F, TOM_F, TOM_M, TOM_L, SNARE][i]
            hit(jitter_grid(bt, 4, pos), nn, 90 + random.randint(-12, 12))
    else:
        # 32nd bursts
        for i in range(16):
            pos = i / 16.0
            nn = [SNARE, SNARE, SNARE, SNARE][i % 4] if i < 8 else [TOM_F, TOM_M, HTOM, TOM_L][i % 4]
            hit(jitter_grid(bt, 16, pos), nn, 70 + i * 3 + random.randint(-6, 6))

def kick_snare_dialogue(t0, bars=2):
    """Leave hats out; alternate kick/snare pattern with rest."""
    for b in range(bars):
        bt = t0 + b * 4.0
        hit(jitter_grid(bt, 4, 0.0), KICK, 104)
        hit(jitter_grid(bt, 4, 0.75), SNARE, 62)
        hit(jitter_grid(bt, 4, 1.25), KICK, 82)
        hit(jitter_grid(bt, 4, 1.75), SNARE, 96)
        hit(jitter_grid(bt, 4, 2.25), KICK, 76)
        hit(jitter_grid(bt, 4, 3.0), SNARE, 112)
        hit(jitter_grid(bt, 4, 3.5), KICK, 68)
        # ghost
        hit(jitter_grid(bt, 4, 2.75), SNARE, 30)

def ending_hit(t0):
    hit(jitter_grid(t0, 4, 0.0), KICK, 120)
    hit(jitter_grid(t0, 4, 0.0), SNARE, 118)
    hit(jitter_grid(t0, 4, 0.0), CRASH, 116)
    hit(jitter_grid(t0, 4, 0.02), CRASH2, 100)
    hit(jitter_grid(t0, 4, 0.04), RIDE_BELL, 90)

# ---------- build the solo ----------
# Time layout roughly 2 minutes @ ~112 BPM
# 112 BPM -> beat = 60/112 = 0.5357 s. 2 min = 120 s -> ~224 beats -> 56 bars.
# We'll structure:
# 0-4: intro statement (motif A)
# 4-12: motif B groove
# 12-16: motif A returns varied
# 16-20: fills
# 20-28: motif C toms
# 28-32: roll swell section
# 32-40: motif B with variations and dialogue
# 40-44: A with bigger dynamics
# 44-48: double stroke run + fills
# 48-52: climax motif C + kick snare
# 52-56: landing

# Times in beats
# We'll create continuous stream with helper sections.

# SECTION 1: intro
t = 0.0
motif_A(t, bars=1, accent=False)
t += 4.0
motif_A(t, bars=1, accent=True)
t += 4.0

# SECTION 2: groove B
motif_B(t, bars=1)
t += 4.0
motif_B(t, bars=1)
t += 4.0
motif_B(t, bars=1)
t += 4.0
motif_B(t, bars=1)
t += 4.0

# SECTION 3: A returns bigger
motif_A(t, bars=1, accent=True)
t += 4.0
# A variation: accents
motif_A(t, bars=1, accent=True)
t += 4.0

# SECTION 4: fills leading into toms
fill_one_beat(t, style=0)
t += 1.0
fill_one_beat(t, style=1)
t += 1.0
fill_one_beat(t, style=2)
t += 1.0
roll_sweep(t, 1.0, 50, 115)
t += 1.0

# SECTION 5: motif C toms
motif_C_down(t, bars=1)
t += 4.0
motif_C_down(t, bars=1)
t += 4.0

# SECTION 6: roll swell (2 beats) then resolve
roll_sweep(t, 2.0, 35, 120, [SNARE, SNARE, TOM_F, TOM_M, HTOM])
t += 2.0
# resolve with kick/snare
hit(jitter_grid(t, 4, 0.0), KICK, 118)
hit(jitter_grid(t, 4, 0.0), SNARE, 116)
hit(jitter_grid(t, 4, 0.5), SNARE, 55)
t += 2.0

# Motif B with variations
motif_B(t, bars=1)
t += 4.0
motif_B(t, bars=1)
t += 4.0

# SECTION 7: dialogue
kick_snare_dialogue(t, bars=2)
t += 8.0

# SECTION 8: A big
motif_A(t, bars=1, accent=True)
t += 4.0
motif_A(t, bars=1, accent=True)
t += 4.0

# SECTION 9: doubles run
double_stroke_run(t, 1.0, base=78)
t += 1.0
double_stroke_run(t, 1.0, base=82)
t += 1.0
double_stroke_run(t, 2.0, base=86)
t += 2.0

# SECTION 10: climax with toms and rolls
motif_C_down(t, bars=1)
t += 4.0
roll_sweep(t, 1.0, 50, 120)
t += 1.0
fill_one_beat(t, style=0)
t += 1.0
fill_one_beat(t, style=2)
t += 1.0
# bring back A with stronger
motif_A(t, bars=1, accent=True)
t += 4.0

# SECTION 11: final build: rolls and crashes
roll_sweep(t, 2.0, 60, 125, [SNARE, TOM_F, TOM_M, HTOM, TOM_L])
t += 2.0
hit(jitter_grid(t, 4, 0.0), KICK, 120)
hit(jitter_grid(t, 4, 0.0), SNARE, 118)
hit(jitter_grid(t, 4, 0.0), CRASH, 112)
t += 2.0
# brief pause with hats
for i in range(4):
    hit(jitter_grid(t, 4, i / 4.0), HAT, 50 + i * 5)
    hit(jitter_grid(t, 4, i / 4.0 + 0.5), SNARE, 36)
t += 2.0
# big fill
for i in range(8):
    pos = i / 8.0 * 2.0
    nn = [SNARE, SNARE, TOM_F, TOM_M, HTOM, TOM_L, SNARE, SNARE][i]
    hit(jitter_grid(t, 8, pos), nn, 70 + i * 6 + random.randint(-8, 8))
t += 2.0

# SECTION 12: final landing
ending_hit(t)
# small roll into it
t += 0.5
for i in range(4):
    hit(jitter_grid(t, 4, i / 4.0), SNARE, 40 + i * 10)
t += 1.0
# final huge hit
hit(jitter_grid(t, 4, 0.0), KICK, 127)
hit(jitter_grid(t, 4, 0.0), SNARE, 124)
hit(jitter_grid(t, 4, 0.0), CRASH, 118)
hit(jitter_grid(t, 4, 0.02), CRASH2, 108)
hit(jitter_grid(t, 4, 0.05), RIDE_BELL, 100)
t += 2.0

# Add color occasionally through song: tambourine, cowbell on downbeats of sections
# We'll insert some sparse color hits without breaking playability.

# Sort events
events.sort(key=lambda x: (x[0], x[1]))

# ---------- build MIDI ----------
mid = MidiFile(ticks_per_beat=TPB)
track = MidiTrack()
mid.tracks.append(track)

track.append(MetaMessage('track_name', name='Drum Solo', time=0))
track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / 112), time=0))
track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
track.append(Message('program_change', channel=9, program=0, time=0))

last_tick = 0
for (tick, note, vel) in events:
    delta = tick - last_tick
    if delta < 0:
        delta = 0
    track.append(Message('note_on', channel=9, note=note, velocity=vel, time=delta))
    track.append(Message('note_off', channel=9, note=note, velocity=0, time=6))
    last_tick = tick + 6

# end
track.append(MetaMessage('end_of_track', time=120))

mid.save('solo.mid')
print("wrote solo.mid with", len(events), "events")
