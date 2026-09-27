import mido
from collections import defaultdict
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TICKS_PER_BEAT = 480
TEMPO = 144                     # BPM – gives exactly 120 s for 72 bars of 4/4
BEATS_PER_BAR = 4
TICKS_PER_BAR = TICKS_PER_BEAT * BEATS_PER_BAR
TOTAL_BARS = 72
TOTAL_TICKS = TOTAL_BARS * TICKS_PER_BAR

# General MIDI drum notes (channel 10)
KICK        = 36
KICK2       = 35
SNARE       = 38
SIDE_STICK  = 37
CLOSED_HH   = 42
PEDAL_HH    = 44
OPEN_HH     = 46
RIDE        = 51
RIDE_BELL   = 53
CRASH       = 49
CRASH2      = 57
TOM_LOW     = 41
TOM_HIGH    = 50
TOM_MID     = 47
TOM_FLOOR   = 43
COWBELL     = 56

# ---------------------------------------------------------------------------
# Time feel
# ---------------------------------------------------------------------------
def apply_feel(beat, feel):
    """Apply swing and a small constant offset to a beat position."""
    swing = feel.get('swing', 0.0)
    offset = feel.get('offset', 0.0)

    if swing > 0.0:
        frac = beat - math.floor(beat)
        if abs(frac - 0.5) < 0.01:      # off‑beat 8th gets delayed
            beat += swing

    return beat + offset

# ---------------------------------------------------------------------------
# Pattern generators
# ---------------------------------------------------------------------------
def pattern_groove(variation=0, use_ride=False):
    """Basic rock/funk groove.  Variation 0 = simple, 1 = more kick & ghosts,
       2 = syncopated kick with extra ghost notes."""
    events = []
    cymbal = RIDE if use_ride else CLOSED_HH

    # cymbal (8th notes, accented on downbeats)
    for i in range(8):
        beat = i * 0.5
        vel = 90 if i % 2 == 0 else 70
        events.append((beat, cymbal, vel))

    # kick
    events.append((0, KICK, 95))
    events.append((2, KICK, 95))
    if variation >= 1:
        events.append((2.5, KICK, 85))
        events.append((3.5, KICK, 75))
    if variation >= 2:
        events.append((0.75, KICK, 80))
        events.append((1.5, KICK, 75))

    # snare
    events.append((1, SNARE, 100))
    events.append((3, SNARE, 100))
    if variation >= 1:
        events.append((1.5, SNARE, 35))      # ghost
        events.append((2.5, SNARE, 35))      # ghost
    if variation >= 2:
        events.append((0.5, SNARE, 30))
        events.append((3.5, SNARE, 30))

    # pedal hi‑hat
    events.append((1, PEDAL_HH, 60))
    events.append((3, PEDAL_HH, 60))
    return events

def pattern_ride(variation=0):
    """Ride cymbal pattern – variation 1 adds bell accents and extra kick."""
    events = []

    for i in range(8):
        beat = i * 0.5
        vel = 90 if i % 2 == 0 else 70
        events.append((beat, RIDE, vel))

    if variation >= 1:
        events.append((0, RIDE_BELL, 100))
        events.append((2, RIDE_BELL, 100))

    events.append((0, KICK, 95))
    events.append((2, KICK, 95))
    if variation >= 1:
        events.append((3, KICK, 80))

    events.append((1, SNARE, 100))
    events.append((3, SNARE, 100))
    if variation >= 2:
        events.append((1.5, SNARE, 40))
        events.append((2.5, SNARE, 40))

    events.append((1, PEDAL_HH, 55))
    events.append((3, PEDAL_HH, 55))
    return events

def pattern_half_time():
    """Sparse half‑time feel with cowbell colour."""
    events = []
    for i in range(4):
        events.append((i, RIDE_BELL, 70))
    events.append((0, KICK, 80))
    events.append((2, SNARE, 85))
    events.append((1.5, SNARE, 30))          # ghost
    events.append((3.5, SNARE, 30))          # ghost
    events.append((1, PEDAL_HH, 50))
    events.append((3, PEDAL_HH, 50))
    events.append((0, COWBELL, 60))
    events.append((2, COWBELL, 60))
    return events

def pattern_tom_fill(start_beat=2, direction='down'):
    """16th‑note tom fill."""
    events = []
    toms = ([TOM_HIGH, TOM_MID, TOM_LOW, TOM_FLOOR]
            if direction == 'down'
            else [TOM_FLOOR, TOM_LOW, TOM_MID, TOM_HIGH])
    num_notes = int((4 - start_beat) * 4)
    for i in range(num_notes):
        beat = start_beat + i * 0.25
        tom = toms[i % len(toms)]
        vel = min(80 + i * 5, 110)
        events.append((beat, tom, vel))
    return events

def pattern_snare_roll(start_beat=2, subdivision=16):
    """Snare roll with a steady crescendo."""
    events = []
    num_notes = int((4 - start_beat) * subdivision / 4) if subdivision == 16 else int((4 - start_beat) * 8)
    for i in range(num_notes):
        beat = start_beat + i * (4.0 / subdivision)
        vel = int(50 + (i / max(1, num_notes - 1)) * 50)
        events.append((beat, SNARE, min(vel, 110)))
    return events

def pattern_double_stroke(start_beat=0):
    """Simulated double‑stroke roll on snare – two hits close together."""
    events = []
    for i in range(16):
        beat = start_beat + i * 0.25
        vel = 70 + (i % 4) * 5
        events.append((beat, SNARE, vel))
        events.append((beat - 0.05, SNARE, max(vel - 20, 30)))
    return events

def pattern_climax_run(start_beat=0):
    """Fast linear run around snare and toms with kick on downbeats."""
    events = []
    sequence = [SNARE, TOM_HIGH, SNARE, TOM_MID, SNARE, TOM_LOW, SNARE, TOM_FLOOR]
    for i in range(16):
        beat = start_beat + i * 0.25
        note = sequence[i % len(sequence)]
        vel = min(90 + (i % 4) * 8, 120)
        events.append((beat, note, vel))
    for i in range(4):
        events.append((i, KICK, 100))
    return events

def pattern_linear_run(start_beat=0, end_beat=4, direction='up'):
    """16th‑note linear run around the kit."""
    events = []
    if direction == 'up':
        seq = [SNARE, TOM_HIGH, TOM_MID, TOM_LOW, TOM_FLOOR, TOM_LOW, TOM_MID, TOM_HIGH]
    else:
        seq = [TOM_FLOOR, TOM_LOW, TOM_MID, TOM_HIGH, SNARE, TOM_HIGH, TOM_MID, TOM_LOW]
    num_notes = int((end_beat - start_beat) * 4)
    for i in range(num_notes):
        beat = start_beat + i * 0.25
        note = seq[i % len(seq)]
        vel = 80 + (i % 4) * 5
        events.append((beat, note, vel))
    return events

# ---------------------------------------------------------------------------
# Solo construction
# ---------------------------------------------------------------------------
def generate_solo():
    solo_events = []

    def add_bar(bar_index, events, feel, dynamics_scale):
        bar_start_tick = bar_index * TICKS_PER_BAR
        for beat, note, vel in events:
            adj_beat = apply_feel(beat, feel)
            tick = bar_start_tick + int(round(adj_beat * TICKS_PER_BEAT))
            v = int(vel * dynamics_scale)
            v = max(1, min(127, v))
            solo_events.append((tick, note, v, 9))      # channel 9 = MIDI 10

    # --- feels per section -------------------------------------------------
    feel_intro    = {'swing': 0.00, 'offset':  0.00}
    feel_main     = {'swing': 0.05, 'offset':  0.00}
    feel_dev      = {'swing': 0.10, 'offset': -0.01}
    feel_contrast = {'swing': 0.00, 'offset':  0.03}
    feel_build    = {'swing': 0.00, 'offset': -0.02}
    feel_climax   = {'swing': 0.00, 'offset': -0.03}
    feel_res      = {'swing': 0.05, 'offset':  0.04}
    feel_final    = {'swing': 0.00, 'offset':  0.00}

    # --- per‑bar dynamics envelope ----------------------------------------
    bar_dynamics = [1.0] * TOTAL_BARS
    for i in range(0, 4):          bar_dynamics[i] = 0.60 + i * 0.05
    for i in range(4, 12):         bar_dynamics[i] = 0.80 + (i - 4) * 0.02
    for i in range(12, 20):        bar_dynamics[i] = 0.90 + (i - 12) * 0.01
    for i in range(20, 28):        bar_dynamics[i] = 0.50 - (i - 20) * 0.02
    for i in range(28, 44):        bar_dynamics[i] = 0.60 + (i - 28) * 0.025
    for i in range(44, 60):        bar_dynamics[i] = 1.00
    for i in range(60, 68):        bar_dynamics[i] = 0.80 - (i - 60) * 0.025
    for i in range(68, 72):        bar_dynamics[i] = 0.70 + (i - 68) * 0.10

    # -----------------------------------------------------------------------
    #  Intro (bars 0–3)
    # -----------------------------------------------------------------------
    for bar in range(0, 4):
        events = []
        if bar == 0:
            for i in range(4):
                events.append((i, PEDAL_HH, 60))
            events.append((0, KICK, 70))
            events.append((2, KICK, 70))
            events.append((1, SNARE, 50))
            events.append((3, SNARE, 50))
        elif bar == 1:
            for i in range(4):
                events.append((i, RIDE, 70))
            events.append((0, KICK, 80))
            events.append((2, KICK, 80))
            events.append((1, SNARE, 60))
            events.append((3, SNARE, 60))
        elif bar == 2:
            events = pattern_groove(variation=0)
        else:   # bar 3 – fill into the main groove
            events = pattern_groove(variation=0)
            events += pattern_snare_roll(start_beat=2, subdivision=16)
        add_bar(bar, events, feel_intro, bar_dynamics[bar])

    # -----------------------------------------------------------------------
    #  Main groove (bars 4–11)
    # -----------------------------------------------------------------------
    for bar in range(4, 12):
        if bar < 8:
            events = pattern_groove(variation=0)
        else:
            events = pattern_groove(variation=1)
        if bar == 11:
            events += pattern_tom_fill(start_beat=2, direction='down')
        add_bar(bar, events, feel_main, bar_dynamics[bar])

    # -----------------------------------------------------------------------
    #  Development (bars 12–19)
    # -----------------------------------------------------------------------
    for bar in range(12, 20):
        if bar < 16:
            events = pattern_ride(variation=1)
        else:
            events = pattern_groove(variation=2)
        if bar == 12:
            events.append((0, CRASH, 110))
        if bar == 19:
            events += pattern_snare_roll(start_beat=2, subdivision=16)
        add_bar(bar, events, feel_dev, bar_dynamics[bar])

    # -----------------------------------------------------------------------
    #  Contrast – sparse, laid back (bars 20–27)
    # -----------------------------------------------------------------------
    for bar in range(20, 28):
        if bar < 24:
            events = pattern_half_time()
        else:
            events = []
            events.append((0, KICK, 60))
            events.append((2, SIDE_STICK, 50))
            for i in range(4):
                events.append((i, PEDAL_HH, 40))
            if bar == 27:
                events += pattern_snare_roll(start_beat=2, subdivision=16)
        add_bar(bar, events, feel_contrast, bar_dynamics[bar])

    # -----------------------------------------------------------------------
    #  Build‑up (bars 28–43)
    # -----------------------------------------------------------------------
    for bar in range(28, 44):
        if bar < 32:                # snare roll crescendo
            events = pattern_snare_roll(start_beat=0, subdivision=16)
            events.append((0, KICK, 80))
            events.append((2, KICK, 80))
        elif bar < 36:              # tom fills
            events = pattern_tom_fill(start_beat=0,
                                      direction='down' if bar % 2 == 0 else 'up')
            events.append((0, KICK, 90))
            events.append((2, KICK, 90))
        elif bar < 40:              # double‑stroke rolls
            events = pattern_double_stroke(start_beat=0)
            events.append((0, KICK, 95))
            events.append((2, KICK, 95))
        else:                       # linear runs
            events = pattern_linear_run(start_beat=0, end_beat=4, direction='up')
        if bar == 28:
            events.append((0, CRASH, 100))
        if bar == 43:
            events.append((0, CRASH, 120))
        add_bar(bar, events, feel_build, bar_dynamics[bar])

    # -----------------------------------------------------------------------
    #  Climax (bars 44–59)
    # -----------------------------------------------------------------------
    for bar in range(44, 60):
        if bar < 48:                # heavy ride groove
            events = pattern_ride(variation=2)
            events.append((0, CRASH, 115))
            events.append((0, KICK, 110))
            events.append((2, KICK, 110))
            events.append((1, SNARE, 115))
            events.append((3, SNARE, 115))
        elif bar < 52:              # fast linear runs
            events = pattern_climax_run(start_beat=0)
            events.append((0, CRASH, 115))
        elif bar < 56:              # flams + fast runs
            events = pattern_climax_run(start_beat=0)
            for i in range(4):
                beat = i
                events.append((beat - 0.05, SNARE, 60))   # grace note
                events.append((beat, SNARE, 110))
            events.append((0, KICK, 110))
            events.append((2, KICK, 110))
        else:                       # maximum intensity
            events = pattern_climax_run(start_beat=0)
            events.append((0, CRASH, 120))
            events.append((0, KICK, 115))
            events.append((0, SNARE, 115))
        if bar % 4 == 0:
            events.append((0, CRASH, 110))
        add_bar(bar, events, feel_climax, bar_dynamics[bar])

    # -----------------------------------------------------------------------
    #  Resolution (bars 60–67)
    # -----------------------------------------------------------------------
    for bar in range(60, 68):
        if bar < 64:
            events = pattern_groove(variation=0, use_ride=True)
        else:
            events = []
            events.append((0, KICK, 70))
            events.append((2, SNARE, 60))
            for i in range(4):
                events.append((i, RIDE, 60))
            if bar == 67:
                events += pattern_snare_roll(start_beat=2, subdivision=16)
        add_bar(bar, events, feel_res, bar_dynamics[bar])

    # -----------------------------------------------------------------------
    #  Final bars 68–71 – build to a single strong hit
    # -----------------------------------------------------------------------
    for bar in range(68, 72):
        if bar < 71:
            events = []
            events.append((0, KICK, 80))
            events.append((2, KICK, 80))
            events.append((1, SNARE, 70))
            events.append((3, SNARE, 70))
            for i in range(4):
                events.append((i, RIDE, 70))
            if bar == 70:
                events += pattern_snare_roll(start_beat=2, subdivision=16)
        else:
            # final hit – let it ring for the whole bar
            events = []
            events.append((0, CRASH, 127))
            events.append((0, KICK, 127))
            events.append((0, SNARE, 127))
        add_bar(bar, events, feel_final, bar_dynamics[bar])

    return solo_events

# ---------------------------------------------------------------------------
# Playability guard – at most 2 hands and 2 feet per tick
# ---------------------------------------------------------------------------
def enforce_playability(events):
    events.sort(key=lambda x: x[0])
    tick_groups = defaultdict(list)
    for ev in events:
        tick_groups[ev[0]].append(ev)

    foot_notes = {KICK, KICK2, PEDAL_HH}
    hand_notes = set(range(35, 82)) - foot_notes

    final_events = []
    for tick in sorted(tick_groups.keys()):
        group = tick_groups[tick]
        hands = [ev for ev in group if ev[1] in hand_notes]
        feet  = [ev for ev in group if ev[1] in foot_notes]
        # keep the two loudest of each limb
        hands.sort(key=lambda x: x[2], reverse=True)
        hands = hands[:2]
        feet.sort(key=lambda x: x[2], reverse=True)
        feet = feet[:2]
        final_events.extend(hands + feet)
    return final_events

# ---------------------------------------------------------------------------
# MIDI file output
# ---------------------------------------------------------------------------
def write_midi(events, filename='solo.mid'):
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)

    # tempo & track name
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(TEMPO), time=0))
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))

    # build timestamped messages
    messages = []
    for tick, note, vel, channel in events:
        messages.append((tick, 'note_on',  note, vel, channel))
        messages.append((tick + 10, 'note_off', note, 0,   channel))

    # note_off before note_on at the same tick
    messages.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

    last_tick = 0
    for tick, msg_type, note, vel, channel in messages:
        delta = tick - last_tick
        if msg_type == 'note_on':
            msg = mido.Message('note_on',  channel=channel, note=note,
                               velocity=vel, time=delta)
        else:
            msg = mido.Message('note_off', channel=channel, note=note,
                               velocity=0, time=delta)
        track.append(msg)
        last_tick = tick

    # pad to exactly 120 seconds
    if last_tick < TOTAL_TICKS:
        track.append(mido.MetaMessage('end_of_track',
                                      time=TOTAL_TICKS - last_tick))

    mid.save(filename)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    events = generate_solo()
    events = enforce_playability(events)
    write_midi(events, 'solo.mid')
