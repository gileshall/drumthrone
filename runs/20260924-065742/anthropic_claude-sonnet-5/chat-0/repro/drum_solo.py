"""
drum_solo.py

Generates a deterministic ~2 minute General MIDI drum solo (channel 10 / index 9)
as solo.mid.

Structure (60 bars @ 120 BPM, 4/4 = 2s/bar = 120s, plus a short ritardando tail):
  1. Statement        (bars  0- 7)  - Motif A introduced, sparse -> building
  2. Development 1    (bars  8-15)  - Busier hats/ghosts, small fills
  3. Tension Build    (bars 16-23)  - Ride cymbal enters, crescendo
  4. Climax 1         (bars 24-29)  - Full kit, double kick, sudden stop
  5. Breakdown        (bars 30-35)  - Quiet recall of Motif A (ghost notes)
  6. Latin Interlude  (bars 36-43)  - Auxiliary percussion motif (contrast)
  7. Combine & Build  (bars 44-51)  - Kit + cowbell/ride merge, crescendo
  8. Climax 2         (bars 52-57)  - Grand finale, double bass drum
  9. Coda             (bars 58-59)  - Final statement + big descending fill,
                                      ritardando, unison ending chord.

Design notes:
  - At most two "hand" strikes and two "foot" strikes are ever placed at the
    exact same tick (enforced by fix_collisions as a safety net, but the
    patterns are hand-built to already respect this).
  - Feel: deliberate micro-timing (kicks pushed ahead, snares laid back,
    optional swing on off-beat 16ths) instead of random jitter.
  - Ghost notes (low velocity) are placed on the grid *between* accents,
    never colliding with them, to keep dynamics clear and intentional.
  - The whole GM percussion map is available; toms, cymbals, cowbell,
    congas, timbale, claves and woodblock are used for color/contrast.
"""

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack
from collections import defaultdict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PPQ = 480
SIXTEENTH = PPQ // 4          # 120 ticks
BAR = 4 * PPQ                 # 1920 ticks (4/4)

# GM percussion note numbers
KICK = 36
KICK_ALT = 35
SNARE = 38
RIMSHOT = 37
HH_CLOSED = 42
HH_PEDAL = 44
HH_OPEN = 46
TOM_HI = 50
TOM_MID = 45
TOM_LOW = 41
CRASH1 = 49
CRASH2 = 57
RIDE = 51
RIDE_BELL = 53
CHINA = 52
SPLASH = 55
COWBELL = 56
MUTE_CONGA = 62
OPEN_CONGA = 63
LOW_CONGA = 64
HI_TIMBALE = 65
CLAVES = 75
WOODBLOCK_HI = 76

FOOT_NOTES = {KICK, KICK_ALT, HH_PEDAL}

SUSTAIN_DUR = {HH_OPEN: 220, CRASH1: 700, RIDE: 350, CHINA: 600,
               RIDE_BELL: 300, SPLASH: 450, CRASH2: 700}


def role_of(note):
    return 'F' if note in FOOT_NOTES else 'H'


def get_dur(note):
    return SUSTAIN_DUR.get(note, 45)


# ---------------------------------------------------------------------------
# Feel (micro-timing) definitions
# ---------------------------------------------------------------------------

FEEL_SOFT = {'swing': 0, 'kick': -4, 'snare': 7, 'hat': 0, 'cymbal': -3, 'perc': 0}
FEEL_DEV = {'swing': 10, 'kick': -4, 'snare': 8, 'hat': 2, 'cymbal': -3, 'perc': 0}
FEEL_BUILD = {'swing': 0, 'kick': -6, 'snare': 8, 'hat': -2, 'cymbal': -4, 'perc': 0}
FEEL_CLIMAX = {'swing': 0, 'kick': -8, 'snare': 10, 'hat': -3, 'cymbal': -5, 'perc': 0}
FEEL_BREAK = {'swing': 0, 'kick': -2, 'snare': 4, 'hat': 0, 'cymbal': 0, 'perc': 0}
FEEL_LATIN = {'swing': 14, 'kick': -3, 'snare': 5, 'hat': 0, 'cymbal': -3, 'perc': -3}
FEEL_SWUNG = {'swing': 16, 'kick': -4, 'snare': 9, 'hat': 1, 'cymbal': -3, 'perc': 0}


def timing_offset(note, slot, feel):
    off = 0.0
    if feel.get('swing', 0):
        if abs(slot - round(slot)) < 1e-6 and int(round(slot)) % 2 == 1:
            off += feel['swing']
    if note in (KICK, KICK_ALT):
        off += feel.get('kick', 0)
    elif note in (SNARE, RIMSHOT):
        off += feel.get('snare', 0)
    elif note in (HH_CLOSED, HH_PEDAL, HH_OPEN):
        off += feel.get('hat', 0)
    elif note in (CRASH1, CRASH2, CHINA, SPLASH, RIDE, RIDE_BELL):
        off += feel.get('cymbal', 0)
    else:
        off += feel.get('perc', 0)
    return off


# ---------------------------------------------------------------------------
# Global hit list & bar writer
# ---------------------------------------------------------------------------

all_hits = []  # (tick, note, velocity)


def add_bar(bar_no, hits, feel):
    bar_start = bar_no * BAR
    for (slot, note, vel) in hits:
        off = timing_offset(note, slot, feel)
        tick = int(round(bar_start + slot * SIXTEENTH + off))
        if tick < 0:
            tick = 0
        v = max(1, min(127, int(round(vel))))
        all_hits.append((tick, note, v))


# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------

def groove_bar(kicks=(), snares=(), ghosts=(), hats=(), hat_note=HH_CLOSED,
               kick_vel=95, snare_vel=105, ghost_vel=38, hat_vel=68,
               hat_accents=None, fill_from=None, kick_note=KICK):
    hat_accents = hat_accents or {}
    hits = []
    for s in hats:
        if fill_from is not None and s >= fill_from:
            continue
        v = hat_accents.get(s, hat_vel)
        hits.append((s, hat_note, v))
    for s in kicks:
        if fill_from is not None and s >= fill_from:
            continue
        hits.append((s, kick_note, kick_vel))
    for s in snares:
        if fill_from is not None and s >= fill_from:
            continue
        hits.append((s, SNARE, snare_vel))
    for s in ghosts:
        if fill_from is not None and s >= fill_from:
            continue
        hits.append((s, SNARE, ghost_vel))
    return hits


def ride_bar(pattern_slots, note=RIDE, vel=75, bell_slots=None, bell_vel=95,
             kicks=None, kick_vel=90, snares=None, snare_vel=100,
             ghosts=None, ghost_vel=40):
    bell_slots = bell_slots or []
    hits = []
    for s in pattern_slots:
        if s in bell_slots:
            hits.append((s, RIDE_BELL, bell_vel))
        else:
            hits.append((s, note, vel))
    for s in (kicks or []):
        hits.append((s, KICK, kick_vel))
    for s in (snares or []):
        hits.append((s, SNARE, snare_vel))
    for s in (ghosts or []):
        hits.append((s, SNARE, ghost_vel))
    return hits


def latin_bar(variant=0, vel_scale=1.0):
    hits = []
    cowbell_slots = [0, 3, 6, 10, 12]
    for s in cowbell_slots:
        hits.append((s, COWBELL, int(70 * vel_scale)))
    conga_pattern = [(2, MUTE_CONGA, 60), (5, OPEN_CONGA, 90), (8, MUTE_CONGA, 60),
                      (11, OPEN_CONGA, 95), (14, LOW_CONGA, 100)]
    for s, n, v in conga_pattern:
        hits.append((s, n, int(v * vel_scale)))
    hits.append((0, KICK, int(80 * vel_scale)))
    hits.append((8, KICK, int(78 * vel_scale)))
    hits.append((4, HH_PEDAL, int(60 * vel_scale)))
    hits.append((12, HH_PEDAL, int(60 * vel_scale)))
    if variant == 1:
        hits.append((15, CLAVES, int(85 * vel_scale)))
    else:
        hits.append((9, WOODBLOCK_HI, int(70 * vel_scale)))
    return hits


def fill_toms_desc(start=12, notes=(TOM_HI, TOM_MID, TOM_LOW), vels=(95, 100, 105),
                    step=1.0, end=(SNARE, 110)):
    hits = []
    slot = start
    for n, v in zip(notes, vels):
        hits.append((slot, n, v))
        slot += step
    if end:
        hits.append((slot, end[0], end[1]))
    return hits


def fill_roll(start, count, step, note, vel_start, vel_end):
    hits = []
    for i in range(count):
        t = i / (count - 1) if count > 1 else 0.0
        v = int(round(vel_start + (vel_end - vel_start) * t))
        hits.append((start + i * step, note, v))
    return hits


def fill_double_kick(start, count, step, vel=100):
    hits = []
    for i in range(count):
        n = KICK if i % 2 == 0 else KICK_ALT
        hits.append((start + i * step, n, vel))
    return hits


HATS16 = list(range(16))


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def generate():
    # ---- Section 1: Statement (bars 0-7) -----------------------------
    kicks_A = [0, 6, 10]
    snares_A = [4, 12]
    hats_A = list(range(0, 16, 2))

    for i in range(8):
        t = i / 7.0
        kick_vel = 78 + int(10 * t)
        snare_vel = 96 + int(10 * t)
        hat_vel = 56 + int(8 * t)
        ghost_opts = [[], [], [9], [9], [7, 9], [7, 9], [7, 9, 11], []]
        ghosts = ghost_opts[i]
        if i == 7:
            hits = groove_bar(kicks_A, snares_A, ghosts, hats_A,
                               kick_vel=kick_vel, snare_vel=snare_vel,
                               ghost_vel=34, hat_vel=hat_vel, fill_from=12)
            hits += fill_toms_desc(12, (TOM_HI, TOM_MID, TOM_LOW), (92, 96, 100),
                                    1.0, (SNARE, 108))
        else:
            hits = groove_bar(kicks_A, snares_A, ghosts, hats_A,
                               kick_vel=kick_vel, snare_vel=snare_vel,
                               ghost_vel=34, hat_vel=hat_vel)
        add_bar(i, hits, FEEL_SOFT)

    # ---- Section 2: Development 1 (bars 8-15) ------------------------
    base = 8
    for i in range(8):
        bar_no = base + i
        t = i / 7.0
        kick_vel = 90 + int(14 * t)
        snare_vel = 104 + int(12 * t)
        ghost_vel = 36 + int(10 * t)
        hat_base = 52 + int(8 * t)
        hat_accent_v = 72 + int(10 * t)
        accents = {s: hat_accent_v for s in range(0, 16, 2)}
        ghosts = [3, 7, 11, 15] if i % 2 == 0 else [3, 9, 11]
        kicks = [0, 6, 10] if i % 4 != 3 else [0, 3, 6, 10, 13]
        snares = [4, 12]
        if i in (3, 7):
            hits = groove_bar(kicks, snares, ghosts, HATS16, hat_vel=hat_base,
                               hat_accents=accents, kick_vel=kick_vel,
                               snare_vel=snare_vel, ghost_vel=ghost_vel, fill_from=12)
            if i == 3:
                hits += fill_roll(12, 8, 0.5, SNARE, 50, 100)
            else:
                hits += fill_toms_desc(12, (TOM_HI, TOM_MID, TOM_LOW), (100, 104, 108),
                                        1.0, (CRASH1, 112))
                hits += [(12, KICK, 100)]
        else:
            hits = groove_bar(kicks, snares, ghosts, HATS16, hat_vel=hat_base,
                               hat_accents=accents, kick_vel=kick_vel,
                               snare_vel=snare_vel, ghost_vel=ghost_vel)
        add_bar(bar_no, hits, FEEL_DEV)

    # ---- Section 3: Tension Build (bars 16-23) -----------------------
    base = 16
    for i in range(8):
        bar_no = base + i
        t = i / 7.0
        kick_vel = 96 + int(20 * t)
        snare_vel = 108 + int(16 * t)
        ghost_vel = 40 + int(14 * t)
        hat_vel = 60 + int(14 * t)
        accent_v = 80 + int(20 * t)
        accents = {s: accent_v for s in (0, 4, 8, 12)}
        kicks = [0, 3, 6, 8, 10, 14] if i % 2 == 0 else [0, 2, 6, 9, 10, 13]
        snares = [4, 12]
        ghosts = [1, 7, 9, 11, 15]
        if i >= 5:
            hits = ride_bar(list(range(0, 16, 2)), vel=hat_vel + 10, bell_slots=[0, 8],
                             bell_vel=accent_v + 10, kicks=kicks, kick_vel=kick_vel,
                             snares=snares, snare_vel=snare_vel, ghosts=ghosts,
                             ghost_vel=ghost_vel)
        else:
            hits = groove_bar(kicks, snares, ghosts, HATS16, hat_vel=hat_vel,
                               hat_accents=accents, kick_vel=kick_vel,
                               snare_vel=snare_vel, ghost_vel=ghost_vel)
        if i % 2 == 1:
            hits = [h for h in hits if h[0] < 14]
            hits += fill_roll(14, 4, 0.5, SNARE, 70 + int(20 * t), 110 + int(10 * t))
        if i == 7:
            hits += [(15, CHINA, 120), (15, KICK, 118)]
        add_bar(bar_no, hits, FEEL_BUILD)

    # ---- Section 4: Climax 1 (bars 24-29) ----------------------------
    base = 24
    for i in range(6):
        bar_no = base + i
        t = i / 5.0
        kick_vel = 108 + int(16 * t)
        snare_vel = 116 + int(10 * t)
        hat_vel = 70 + int(10 * t)
        crash_note = CRASH1 if i % 2 == 0 else CHINA
        if i == 5:
            hits = [(0, crash_note, 127), (0, KICK, 122), (0, SNARE, 118),
                    (0, HH_PEDAL, 100), (8, RIMSHOT, 30)]
        else:
            kicks = [0, 3, 6, 8, 10, 13] if i % 2 == 0 else [0, 2, 4, 7, 10, 12, 14]
            hits = groove_bar(kicks, [4, 12], [1, 9, 11], HATS16, hat_vel=hat_vel,
                               hat_accents={s: hat_vel + 15 for s in (0, 4, 8)},
                               kick_vel=kick_vel, snare_vel=snare_vel, ghost_vel=50,
                               fill_from=12)
            hits.append((0, crash_note, 118))
            hits.append((14, HH_OPEN, hat_vel + 8))
            if i % 3 == 2:
                hits += fill_double_kick(12, 8, 0.5, vel=112)
                hits += fill_roll(12, 8, 0.5, TOM_MID, 90, 120)
            else:
                hits += fill_toms_desc(12, (TOM_HI, TOM_MID, TOM_LOW, TOM_HI),
                                        (105, 108, 112, 116), 1.0, (CRASH2, 120))
        add_bar(bar_no, hits, FEEL_CLIMAX)

    # ---- Section 5: Breakdown (bars 30-35) ---------------------------
    base = 30
    for i in range(6):
        bar_no = base + i
        t = i / 5.0
        kick_vel = 44 + int(6 * t)
        ghost_vel = 28 + int(10 * t)
        hat_vel = 34 + int(8 * t)
        kicks = [0, 10] if i % 2 == 0 else [0, 6]
        ghosts = [4, 9, 12] if i % 2 == 0 else [3, 9, 14]
        hits = groove_bar(kicks, [], ghosts, [0, 4, 8, 12], hat_note=HH_CLOSED,
                           hat_vel=hat_vel, kick_vel=kick_vel, ghost_vel=ghost_vel)
        hits.append((7, RIMSHOT, 26 + int(8 * t)))
        if i == 5:
            hits.append((14, TOM_LOW, 50))
            hits.append((15, KICK, 60))
        add_bar(bar_no, hits, FEEL_BREAK)

    # ---- Section 6: Latin Interlude (bars 36-43) ---------------------
    base = 36
    for i in range(8):
        bar_no = base + i
        t = i / 7.0
        vel_scale = 0.7 + 0.3 * t
        variant = i % 2
        hits = latin_bar(variant=variant, vel_scale=vel_scale)
        if i == 7:
            hits.append((15, CLAVES, int(100 * vel_scale)))
            hits.append((15, HI_TIMBALE, int(100 * vel_scale)))
        add_bar(bar_no, hits, FEEL_LATIN)

    # ---- Section 7: Combine & Build (bars 44-51) ---------------------
    base = 44
    for i in range(8):
        bar_no = base + i
        t = i / 7.0
        kick_vel = 92 + int(20 * t)
        snare_vel = 104 + int(18 * t)
        ghost_vel = 40 + int(14 * t)
        ride_vel = 64 + int(20 * t)
        cowbell_vel = 60 + int(20 * t)
        feel = FEEL_SWUNG if i < 4 else FEEL_BUILD
        kicks = [0, 6, 10] if i % 2 == 0 else [0, 3, 6, 10, 13]
        snares = [4, 12]
        ghosts = [9] if i < 4 else [7, 9, 11]
        ride_pattern = list(range(0, 16, 2)) if i < 6 else HATS16
        hits = ride_bar(ride_pattern, vel=ride_vel, bell_slots=[0, 8],
                         bell_vel=ride_vel + 20, kicks=kicks, kick_vel=kick_vel,
                         snares=snares, snare_vel=snare_vel, ghosts=ghosts,
                         ghost_vel=ghost_vel)
        if i >= 2:
            hits += [(s, COWBELL, cowbell_vel) for s in (2, 6, 10, 14)]
        if i % 4 == 3:
            hits = [h for h in hits if h[0] < 12]
            hits += fill_toms_desc(12, (TOM_HI, TOM_MID, TOM_LOW),
                                    (100 + int(10 * t), 104 + int(10 * t), 108 + int(10 * t)),
                                    1.0, (CRASH1, 110 + int(15 * t)))
        add_bar(bar_no, hits, feel)

    # ---- Section 8: Climax 2 - Grand Finale (bars 52-57) -------------
    base = 52
    for i in range(6):
        bar_no = base + i
        t = i / 5.0
        kick_vel = 112 + int(15 * t)
        snare_vel = 120 + int(7 * t)
        crash_note = CHINA if i % 2 == 0 else CRASH2
        if i == 5:
            foot_hits = fill_double_kick(0, 24, 0.5, vel=kick_vel)
            hand_hits = []
            for s in (0, 4, 8):
                hand_hits.append((s, crash_note if s == 0 else SNARE,
                                   127 if s == 0 else snare_vel))
            for s in (2, 6, 10):
                hand_hits.append((s, SNARE, 70))
            hits = foot_hits + hand_hits
            hits += fill_roll(12, 6, 0.5, TOM_HI, 100, 127)
            hits += [(15, CRASH1, 127), (15, CRASH2, 127),
                     (15, KICK, 127), (15, HH_PEDAL, 110)]
        else:
            density_count = 16 if i < 2 else 32
            density_step = 1.0 if i < 2 else 0.5
            foot_hits = fill_double_kick(0, density_count, density_step, vel=kick_vel)
            hand_hits = []
            for s in (0, 4, 8, 12):
                hand_hits.append((s, crash_note if s == 0 else SNARE,
                                   127 if s == 0 else snare_vel))
            for s in (2, 6, 10, 14):
                hand_hits.append((s, SNARE, 55 + int(25 * t)))
            hits = foot_hits + hand_hits
        add_bar(bar_no, hits, FEEL_CLIMAX)

    # ---- Section 9: Coda (bars 58-59) --------------------------------
    base = 58
    hits58 = groove_bar([0, 6, 10], [4, 12], [7, 9], HATS16, hat_vel=80,
                         kick_vel=118, snare_vel=124, ghost_vel=55, fill_from=12)
    hits58 += fill_toms_desc(12, (TOM_HI, TOM_MID, TOM_LOW), (115, 118, 122),
                              1.0, (SNARE, 126))
    add_bar(base, hits58, FEEL_CLIMAX)

    final_fill_notes = [TOM_HI, TOM_HI, TOM_MID, TOM_MID, TOM_LOW, TOM_LOW,
                         SNARE, SNARE, TOM_HI, TOM_MID, TOM_LOW, SNARE,
                         TOM_MID, TOM_LOW, SNARE]
    hits59 = []
    for idx, note in enumerate(final_fill_notes):
        vel = min(95 + idx * 2, 124)
        hits59.append((idx, note, vel))
    hits59 += [(15, CRASH1, 127), (15, CRASH2, 127),
               (15, KICK, 127), (15, HH_PEDAL, 115)]
    add_bar(base + 1, hits59, FEEL_CLIMAX)


# ---------------------------------------------------------------------------
# Collision safety net: enforce <=2 hand hits and <=2 foot hits per tick
# ---------------------------------------------------------------------------

def fix_collisions(hits):
    by_tick = defaultdict(list)
    for h in hits:
        by_tick[h[0]].append(h)
    result = []
    for t in sorted(by_tick.keys()):
        events = by_tick[t]
        hand = sorted([e for e in events if role_of(e[1]) == 'H'], key=lambda e: -e[2])
        foot = sorted([e for e in events if role_of(e[1]) == 'F'], key=lambda e: -e[2])
        result.extend(hand[:2])
        result.extend(foot[:2])
        overflow = hand[2:] + foot[2:]
        for i, e in enumerate(overflow):
            nt = t + 2 * (i + 1)
            result.append((nt, e[1], e[2]))
    return result


# ---------------------------------------------------------------------------
# MIDI file assembly
# ---------------------------------------------------------------------------

def build_midi(hits, tempo_events):
    mid = MidiFile(ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    events = []
    events.append((0, 0, MetaMessage('track_name', name='Drum Solo', time=0)))
    events.append((0, 0, MetaMessage('time_signature', numerator=4, denominator=4,
                                      clocks_per_click=24,
                                      notated_32nd_notes_per_beat=8, time=0)))
    for tick, tempo in tempo_events:
        events.append((tick, 0, MetaMessage('set_tempo', tempo=tempo, time=0)))
    events.append((0, 1, Message('program_change', program=0, channel=9, time=0)))

    for tick, note, vel in hits:
        dur = get_dur(note)
        events.append((tick, 2, Message('note_on', note=note, velocity=vel,
                                         channel=9, time=0)))
        events.append((tick + dur, 3, Message('note_off', note=note, velocity=0,
                                               channel=9, time=0)))

    events.sort(key=lambda e: (e[0], e[1]))

    cur = 0
    for tick, pr, msg in events:
        delta = tick - cur
        if delta < 0:
            delta = 0
        msg.time = delta
        track.append(msg)
        cur = tick

    track.append(MetaMessage('end_of_track', time=0))
    return mid


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    generate()

    tempo_events = [
        (0, mido.bpm2tempo(120)),
        (58 * BAR, mido.bpm2tempo(112)),
        (59 * BAR, mido.bpm2tempo(96)),
        (59 * BAR + 12 * SIXTEENTH, mido.bpm2tempo(74)),
    ]

    hits = fix_collisions(all_hits)
    midi = build_midi(hits, tempo_events)
    midi.save('solo.mid')


if __name__ == '__main__':
    main()
