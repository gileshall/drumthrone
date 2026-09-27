from collections import defaultdict

import mido

# drum_solo.py — deterministic, two-minute GM percussion solo.
OUTPUT = "solo.mid"
BPM = 96
BARS = 48
PPQ = 480
STEP = PPQ // 4
BAR_TICKS = 4 * PPQ
CHANNEL = 9  # General MIDI channel 10, zero-indexed.

KICK = 36
SNARE = 38
SIDE_STICK = 37
CLOSED_HAT = 42
PEDAL_HAT = 44
OPEN_HAT = 46
LOW_TOM = 41
MID_TOM = 45
HIGH_TOM = 48
FLOOR_TOM = 43
CRASH = 49
RIDE = 51
RIDE_BELL = 53
COWBELL = 56
LOW_CONGA = 64
HIGH_CONGA = 63
SHAKER = 70
CLAVES = 75
HIGH_WOODBLOCK = 76
TRIANGLE = 81

# Each onset has a designated limb; only one hit per limb is retained.
onsets = defaultdict(dict)


def swing_offset(step):
    position = step % 4
    return (0, 5, 24, 13)[position]


def add(bar, step, note, velocity, limb, duration=68, shift=0):
    if not (0 <= bar < BARS and 0 <= step < 16):
        return
    tick = max(0, bar * BAR_TICKS + step * STEP + swing_offset(step) + shift)
    key = (tick, limb)
    hit = (note, max(1, min(127, velocity)), duration)
    old = onsets[key].get("hit")
    if old is None or hit[1] > old[1]:
        onsets[key]["hit"] = hit


def kick(bar, step, vel=92, shift=0):
    add(bar, step, KICK, vel, "right_foot", 96, shift)


def snare(bar, step, vel=102, shift=12, note=SNARE):
    add(bar, step, note, vel, "left_hand", 76, shift)


def ghost(bar, step, vel=37):
    add(bar, step, SNARE, vel, "left_hand", 51, 12)


def hat(bar, step, vel=57, open_hat=False):
    add(
        bar, step, OPEN_HAT if open_hat else CLOSED_HAT,
        vel, "right_hand", 155 if open_hat else 57
    )


def pedal(bar, step, vel=49):
    add(bar, step, PEDAL_HAT, vel, "left_foot", 52)


def hand(bar, step, note, vel, limb="right_hand", duration=78, shift=0):
    add(bar, step, note, vel, limb, duration, shift)


def basic_hats(bar, dense=False, ride=False, energy=0):
    positions = range(16) if dense else range(0, 16, 2)
    for step in positions:
        if dense and step % 2:
            velocity = 35 + energy // 5
        elif step % 4 == 0:
            velocity = 65 + energy // 3
        else:
            velocity = 47 + energy // 4
        if ride:
            note = RIDE_BELL if step == 0 and energy >= 15 else RIDE
            hand(bar, step, note, velocity + 3)
        else:
            hat(bar, step, velocity)
    for step in (4, 12):
        pedal(bar, step, 43 + energy // 4)


def motif_a(bar, variant=0, energy=0, ride=False):
    """Syncopated kick answers a laid-back backbeat."""
    basic_hats(bar, dense=energy >= 17, ride=ride, energy=energy)
    for step, velocity in ((0, 99), (7, 78), (10, 89), (14, 73)):
        if variant == 1 and step == 14:
            step = 15
        if variant == 2 and step == 7:
            step = 6
        kick(bar, step, velocity + energy // 3,
             -10 if step in (7, 15) else 0)
    for step in (4, 12):
        snare(bar, step, 101 + energy // 2)
    for step in ((3, 11) if variant == 1 else (3, 10)):
        ghost(bar, step, 33 + energy // 5)
    if variant == 2:
        ghost(bar, 15, 43)


def motif_b(bar, variant=0, energy=0, ride=False):
    """More space after beat one, then an accented offbeat answer."""
    basic_hats(bar, dense=energy >= 15, ride=ride, energy=energy)
    for step, velocity in ((0, 100), (6, 76), (11, 87), (15, 72)):
        if variant == 1 and step == 6:
            step = 7
        kick(bar, step, velocity + energy // 3,
             -13 if step in (11, 15) else 0)
    snare(bar, 4, 99 + energy // 2)
    snare(bar, 12, 108 + energy // 2)
    ghost(bar, 2, 34)
    ghost(bar, 9 if variant != 2 else 10, 40 + energy // 5)
    if variant == 2:
        hand(bar, 14, OPEN_HAT, 72, duration=175)


def tom_answer(bar, size=0):
    for step, note, velocity, limb in (
        (8, HIGH_TOM, 76 + size, "right_hand"),
        (10, MID_TOM, 79 + size, "left_hand"),
        (12, LOW_TOM, 87 + size, "right_hand"),
        (14, FLOOR_TOM, 92 + size, "left_hand"),
        (15, SNARE, 95 + size, "right_hand"),
    ):
        hand(bar, step, note, velocity, limb, 82)
    kick(bar, 12, 94 + size)
    kick(bar, 15, 87 + size, -7)


def phrase_bar(bar, phrase, local):
    if phrase == 0:  # Opening statement.
        if local % 2 == 0:
            motif_a(bar, variant=local // 2)
        else:
            motif_b(bar)
        if local == 0:
            hand(bar, 0, CRASH, 86, "right_hand", 420)
        if local == 3:
            tom_answer(bar)

    elif phrase == 1:  # First variation.
        (motif_a if local % 2 == 0 else motif_b)(
            bar, variant=(local + 1) % 3, energy=10
        )
        if local == 0:
            hand(bar, 0, CRASH, 93, "right_hand", 400)
        if local == 2:
            hand(bar, 14, OPEN_HAT, 76, duration=170)
        if local == 3:
            tom_answer(bar, 3)

    elif phrase == 2:  # Sparse, dry percussion break.
        for step in (0, 6, 10):
            kick(bar, step, 83 if step == 0 else 71)
        for step in (4, 12):
            snare(bar, step, 71, note=SIDE_STICK)
            pedal(bar, step, 44)
        for step in (2, 8, 14):
            hand(bar, step, HIGH_CONGA if step == 8 else LOW_CONGA,
                 68 if step == 8 else 59)
        if local in (1, 3):
            hand(bar, 11, HIGH_WOODBLOCK, 56)
        if local == 3:
            hand(bar, 15, LOW_TOM, 76)

    elif phrase == 3:  # Build on the ride.
        if local % 2 == 0:
            motif_a(bar, variant=2, energy=19, ride=True)
        else:
            motif_b(bar, variant=1, energy=21, ride=True)
        if local == 0:
            hand(bar, 0, CRASH, 91, "left_hand", 470)
        for step in (5, 13):
            hand(bar, step, SHAKER, 39, "left_hand")
        if local == 3:
            tom_answer(bar, 5)

    elif phrase == 4:  # First peak.
        (motif_b if local in (0, 2) else motif_a)(
            bar, variant=local % 3, energy=25, ride=True
        )
        if local in (0, 2):
            hand(bar, 0, CRASH, 100, "left_hand", 470)
        if local == 1:
            hand(bar, 14, HIGH_TOM, 82, "left_hand")
        if local == 3:
            tom_answer(bar, 8)

    elif phrase == 5:  # Breathing room.
        for step, velocity in ((0, 86), (7, 73), (10, 79)):
            kick(bar, step, velocity)
        snare(bar, 4, 80, note=SIDE_STICK)
        snare(bar, 12, 88)
        for step in (0, 4, 8, 12):
            pedal(bar, step, 48)
        for step, note, velocity in (
            (2, LOW_CONGA, 57), (6, HIGH_CONGA, 67),
            (9, LOW_CONGA, 54), (14, HIGH_CONGA, 71)
        ):
            hand(bar, step, note, velocity)
        if local in (1, 3):
            hand(bar, 0, TRIANGLE, 53, "right_hand", 530)
        if local == 3:
            hand(bar, 15, SNARE, 83)

    elif phrase == 6:  # Motif A returns, displaced.
        motif_a(bar, variant=(local + 1) % 3, energy=14)
        if local == 0:
            hand(bar, 0, CRASH, 95, "left_hand", 470)
        if local == 2:
            hand(bar, 6, COWBELL, 60, "left_hand")
        if local == 3:
            tom_answer(bar, 5)

    elif phrase == 7:  # Tom conversation.
        for step in (0, 8, 14):
            kick(bar, step, 91 if step == 0 else 78)
        for step, note, velocity, limb in (
            (0, HIGH_TOM, 77, "right_hand"),
            (2, MID_TOM, 70, "left_hand"),
            (4, SNARE, 103, "left_hand"),
            (6, HIGH_TOM, 76, "right_hand"),
            (8, MID_TOM, 81, "right_hand"),
            (10, LOW_TOM, 85, "left_hand"),
            (12, SNARE, 107, "left_hand"),
            (14, FLOOR_TOM, 88, "right_hand"),
        ):
            hand(bar, step, note, velocity, limb)
        for step in (4, 12):
            pedal(bar, step)
        if local == 0:
            hand(bar, 0, CRASH, 93, "left_hand", 450)
        if local == 3:
            kick(bar, 15, 90)
            hand(bar, 15, SNARE, 96, "left_hand")

    elif phrase == 8:  # Quiet pocket before the final climb.
        for step in (0, 8 if local % 2 == 0 else 10):
            kick(bar, step, 79 if step == 0 else 69)
        snare(bar, 4, 74)
        snare(bar, 12, 83)
        ghost(bar, 11, 31)
        for step in range(0, 16, 2):
            hat(bar, step, 51 if step % 4 == 0 else 42)
        if local >= 2:
            hand(bar, 7, CLAVES, 43, "left_hand")
        if local == 3:
            hand(bar, 15, OPEN_HAT, 65, duration=160)

    elif phrase == 9:  # Motif B intensifies.
        motif_b(bar, variant=local % 3, energy=17 + local * 3, ride=True)
        if local in (0, 2):
            hand(bar, 0, CRASH, 98 + local, "left_hand", 470)
        if local >= 2:
            hand(bar, 13, MID_TOM, 74 + local * 2, "left_hand")
        if local == 3:
            tom_answer(bar, 8)

    elif phrase == 10:  # Climax.
        motif_a(bar, variant=local % 3, energy=28, ride=True)
        if local in (0, 2):
            hand(bar, 0, CRASH, 110, "left_hand", 500)
        if local == 1:
            for step in (9, 11, 13, 15):
                hand(bar, step, SNARE if step == 15 else MID_TOM,
                     65 + step * 2, "left_hand")
        if local == 3:
            tom_answer(bar, 12)
            hand(bar, 0, CRASH, 104, "left_hand", 470)

    else:  # Reprise and resolved ending.
        if local < 2:
            motif_a(bar, energy=13)
            if local == 0:
                hand(bar, 0, CRASH, 103, "left_hand", 490)
        elif local == 2:
            motif_b(bar, energy=12)
            hand(bar, 0, CRASH, 96, "left_hand", 450)
        else:
            for step, velocity in ((0, 105), (6, 84), (12, 116)):
                kick(bar, step, velocity)
            snare(bar, 4, 107)
            for step, note, limb, velocity in (
                (0, RIDE, "right_hand", 72),
                (2, HIGH_TOM, "right_hand", 84),
                (6, MID_TOM, "right_hand", 88),
                (8, LOW_TOM, "left_hand", 93),
                (10, FLOOR_TOM, "right_hand", 101),
                (12, SNARE, "left_hand", 120),
                (12, CRASH, "right_hand", 119),
            ):
                hand(bar, step, note, velocity, limb,
                     540 if step == 12 else 92)
            pedal(bar, 12, 72)


for bar_number in range(BARS):
    phrase_bar(bar_number, bar_number // 4, bar_number % 4)

midi = mido.MidiFile(type=1, ticks_per_beat=PPQ)
track = mido.MidiTrack()
midi.tracks.append(track)
track.append(mido.MetaMessage("track_name", name="Motifs in Motion - Drum Solo"))
track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM)))
track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4))

events = []
for (tick, _limb), entry in onsets.items():
    note, velocity, duration = entry["hit"]
    events.append((tick, 1, note, velocity))
    events.append((tick + duration, 0, note, 0))

previous_tick = 0
for tick, kind, note, velocity in sorted(events):
    track.append(
        mido.Message(
            "note_on" if kind else "note_off",
            channel=CHANNEL,
            note=note,
            velocity=velocity,
            time=tick - previous_tick,
        )
    )
    previous_tick = tick

# The musical form is exactly 48 bars at 96 BPM: 120 seconds. The final
# crash's note-off may occur beyond the barline, so never place end-of-track
# earlier than the last event.
end_tick = max(BARS * BAR_TICKS, previous_tick)
track.append(mido.MetaMessage("end_of_track", time=end_tick - previous_tick))
midi.save(OUTPUT)
