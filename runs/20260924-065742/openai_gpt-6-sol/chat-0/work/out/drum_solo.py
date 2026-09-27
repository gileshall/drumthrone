"""Generate a deterministic, two-minute General MIDI drum solo."""

from collections import defaultdict

import mido

OUTFILE = "solo.mid"
CHANNEL = 9                 # MIDI channel 10, numbered from zero
TPB = 480
TEMPO = 625000              # 96 BPM: 48 bars last exactly 120 seconds
BAR_TICKS = 4 * TPB
END_TICK = 48 * BAR_TICKS

# General MIDI percussion notes
KICK, SNARE, RIM = 36, 38, 37
CLOSED, PEDAL, OPEN = 42, 44, 46
RIDE, BELL, CRASH, CRASH2 = 51, 53, 49, 57
COWBELL = 56
LOW_TOM, FLOOR_TOM, MID_TOM, HIGH_TOM = 41, 43, 47, 50

events = []
limbs = defaultdict(lambda: {"hand": 0, "foot": 0})


def hit(bar, sixteenth, note, velocity, limb="hand"):
    """Place a stroke, checking the available limbs at its grid position."""
    assert 0 <= bar < 48 and 35 <= note <= 81
    assert limb in ("hand", "foot")
    key = (bar, sixteenth)
    limbs[key][limb] += 1
    assert limbs[key][limb] <= 2, f"Too many {limb}s at {key}"

    position = bar * BAR_TICKS + round(sixteenth * (TPB / 4))

    # A consistent laid-back subdivision, with forward kicks and
    # backbeat snares slightly behind it.
    if sixteenth % 2 == 0 and sixteenth % 4 != 0:
        position += 13
    elif sixteenth % 2:
        position += 5

    if note == KICK:
        position -= 4
    elif note == SNARE:
        position += 9 if velocity >= 75 else 2
    elif note in (CLOSED, OPEN, RIDE, BELL, CRASH, CRASH2):
        position -= 3

    position = max(0, position)
    duration = (
        540 if note in (CRASH, CRASH2) else
        160 if note in (RIDE, BELL, OPEN) else
        85 if note in (SNARE, RIM, LOW_TOM, FLOOR_TOM, MID_TOM, HIGH_TOM) else
        58
    )

    # In particular, the final crash must end within the two-minute
    # track. Most GM synthesizers let its sampled tail continue ringing.
    end = min(position + duration, END_TICK)
    assert position < end

    events.append((position, True, note, max(1, min(127, velocity))))
    events.append((end, False, note, 0))


def kick(bar, pos, vel=95):
    hit(bar, pos, KICK, vel, "foot")


def snare(bar, pos, vel=105):
    hit(bar, pos, SNARE, vel)


def ghost(bar, pos, vel=35):
    hit(bar, pos, SNARE, vel)


def cymbal(bar, pos, note=CRASH, vel=101):
    hit(bar, pos, note, vel)


def hats(bar, positions, strength=0, open_at=None):
    for pos in positions:
        note = OPEN if pos == open_at else CLOSED
        vel = (67 if pos % 4 == 0 else 48) + strength
        if note == OPEN:
            vel += 9
        hit(bar, pos, note, vel)
    if open_at is not None:
        hit(bar, open_at + 1, PEDAL, 64, "foot")


# I. State the two-bar kick/ghost-note motif. Four-bar phrases end in
# increasingly assertive tom answers.
for bar in range(8):
    fill = bar % 4 == 3
    lift = (0, 3, -2, 5, 2, 5, 3, 8)[bar]
    if bar in (0, 4):
        cymbal(bar, 0, CRASH if bar == 0 else CRASH2, 93 + lift)

    hat_positions = [
        p for p in range(0, 16, 2)
        if not (p == 0 and bar in (0, 4))
        and not (fill and p >= 8)
    ]
    hats(bar, hat_positions, lift, 14 if bar in (1, 5) else None)

    for p in ((0, 6, 8, 11) if bar % 2 == 0
              else (0, 3, 8, 10, 14)):
        kick(bar, p, 91 + lift if p in (0, 8) else 76 + lift)
    snare(bar, 4, 101 + lift)
    snare(bar, 12, 106 + lift)
    ghost(bar, 3, 30 + lift)
    if not fill:
        ghost(bar, 10 if bar % 2 == 0 else 7, 33 + lift)
        if bar % 2:
            ghost(bar, 15, 29 + lift)
    else:
        for p, note, vel in zip(
            (9, 10, 11, 13, 14, 15),
            (HIGH_TOM, HIGH_TOM, MID_TOM, MID_TOM, FLOOR_TOM, LOW_TOM),
            (57, 64, 68, 74, 79, 87),
        ):
            hit(bar, p, note, vel + lift)


# II. Move the motif onto the ride, with a 3+3+2 bass-drum
# syncopation and occasional cowbell responses.
for bar in range(8, 16):
    fill = bar % 4 == 3
    lift = (0, 2, 3, 5, 2, 5, 7, 9)[bar - 8]
    if bar in (8, 12):
        cymbal(bar, 0, CRASH2, 98 + lift)

    for p in range(0, 16, 2):
        if (p == 0 and bar in (8, 12)) or (fill and p >= 8):
            continue
        instrument = BELL if p in (0, 8) and bar in (10, 14) else RIDE
        hit(bar, p, instrument, (75 if p in (0, 6, 8, 14) else 56) + lift)
    if bar in (10, 14):
        for p in (3, 11):
            hit(bar, p, COWBELL, 53 + lift)

    for p in (0, 3, 6, 8, 11, 14):
        kick(bar, p, (96 if p in (0, 8) else 78) + lift)
    snare(bar, 4, 100 + lift)
    snare(bar, 12, 108 + lift)
    ghost(bar, 2, 32 + lift)
    if not fill:
        ghost(bar, 10, 36 + lift)
        if bar in (9, 13):
            ghost(bar, 15, 32 + lift)
    else:
        for p, note in zip(
            (9, 10, 13, 14, 15),
            (HIGH_TOM, MID_TOM, MID_TOM, FLOOR_TOM, LOW_TOM),
        ):
            hit(bar, p, note, 67 + lift + (p - 9) * 2)


# III. Half-time space: foot-operated hat, rim clicks, and a quiet
# cowbell answer. The backbeat returns in the last two bars.
for bar in range(16, 24):
    rise = max(0, bar - 20) * 5
    if bar == 16:
        cymbal(bar, 0, CRASH, 78)
    for p in (0, 4, 8, 12):
        hit(bar, p, PEDAL, 48 + rise, "foot")
    hat_positions = (2, 6, 10, 14) if bar < 22 else (2, 4, 6, 10, 12, 14)
    hats(bar, hat_positions, -17 + rise)

    for p in ((0, 7, 10) if bar % 2 == 0 else (0, 8, 14)):
        kick(bar, p, (77 if p == 0 else 62) + rise)
    hit(bar, 8, RIM, 69 + rise)
    ghost(bar, 7 if bar % 2 else 11, 27 + rise)
    if bar in (17, 19, 21):
        hit(bar, 3, COWBELL, 43 + rise)
        hit(bar, 11, COWBELL, 40 + rise)
    if bar in (18, 20):
        hit(bar, 14, LOW_TOM, 49 + rise)
    if bar >= 22:
        snare(bar, 4, 82 + rise)
        ghost(bar, 15, 40 + rise)


# IV. Back in the pocket, alternating the familiar syncopation
# with short melodic tom answers.
for bar in range(24, 32):
    fill = bar % 2 == 1
    lift = (0, 2, 4, 5, 5, 7, 8, 10)[bar - 24]
    if bar in (24, 28):
        cymbal(bar, 0, CRASH, 99 + lift)
    hat_positions = [
        p for p in range(0, 16, 2)
        if not (p == 0 and bar in (24, 28))
        and not (fill and p >= 8)
    ]
    hats(bar, hat_positions, lift)
    for p in (0, 3, 6, 8, 11, 14):
        kick(bar, p, (93 if p in (0, 8) else 77) + lift)
    snare(bar, 4, 103 + lift)
    snare(bar, 12, 108 + lift)
    ghost(bar, 2, 34 + lift)
    ghost(bar, 7, 34 + lift)
    if not fill:
        ghost(bar, 10, 38 + lift)
        ghost(bar, 15, 32 + lift)
    else:
        answer = (HIGH_TOM, HIGH_TOM, MID_TOM,
                  MID_TOM, FLOOR_TOM, LOW_TOM)
        for i, (p, note) in enumerate(zip(
            (9, 10, 11, 13, 14, 15), answer
        )):
            hit(bar, p, note, 59 + i * 5 + lift)


# V. Peak: flowing sixteenths followed by increasingly long tom
# cascades. The kick figure keeps the original motif recognizable.
for bar in range(32, 40):
    lift = (0, 2, 4, 6, 7, 9, 10, 12)[bar - 32]
    if bar in (32, 36, 39):
        cymbal(bar, 0, CRASH2 if bar == 39 else CRASH, 104 + lift)

    if bar < 36:
        for p in (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15):
            if p == 0 and bar == 32:
                continue
            hit(
                bar, p, CLOSED,
                (66 if p % 4 == 0 else 43 if p % 2 else 53) + lift,
            )
        ghost(bar, 3, 38 + lift)
        ghost(bar, 10, 41 + lift)
    else:
        start = (10, 8, 6, 4)[bar - 36]
        for p in range(0, start, 2):
            if p != 0 or bar not in (36, 39):
                hit(bar, p, BELL if p in (0, 8) else RIDE, 71 + lift)
        toms = (HIGH_TOM, MID_TOM, HIGH_TOM,
                MID_TOM, FLOOR_TOM, LOW_TOM)
        for i, p in enumerate(range(start, 16)):
            if p == 12:
                continue
            hit(bar, p, toms[i % len(toms)], 68 + min(i, 5) * 5 + lift)

    for p in (0, 3, 6, 8, 11, 14):
        kick(bar, p, (96 if p in (0, 8) else 79) + lift)
    snare(bar, 4, 105 + lift)
    snare(bar, 12, 109 + lift)


# VI. Release: return to the original motif, initially relaxed.
for bar in range(40, 46):
    lift = (-6, -4, -2, 0, 3, 6)[bar - 40]
    if bar in (40, 44):
        cymbal(bar, 0, CRASH, 95 + lift)
    positions = [
        p for p in range(0, 16, 2)
        if not (p == 0 and bar in (40, 44))
    ]
    hats(bar, positions, lift, 14 if bar in (41, 45) else None)
    for p in ((0, 6, 8, 11) if bar % 2 == 0
              else (0, 3, 8, 10, 14)):
        kick(bar, p, (92 if p in (0, 8) else 76) + lift)
    snare(bar, 4, 101 + lift)
    snare(bar, 12, 107 + lift)
    ghost(bar, 3, 32 + lift)
    ghost(bar, 10 if bar % 2 == 0 else 7, 34 + lift)
    if bar % 2:
        ghost(bar, 15, 31 + lift)


# A rising pickup and a resolved final cadence.
bar = 46
cymbal(bar, 0, CRASH2, 105)
for p in (2, 4, 6):
    hit(bar, p, CLOSED, 63 if p != 4 else 70)
for p in (0, 6, 8, 11, 14):
    kick(bar, p, 89 if p in (0, 8) else 78)
snare(bar, 4, 110)
snare(bar, 12, 113)
ghost(bar, 3, 37)
for p, note, vel in zip(
    (8, 9, 10, 11, 13, 14, 15),
    (HIGH_TOM, HIGH_TOM, MID_TOM, MID_TOM,
     FLOOR_TOM, FLOOR_TOM, LOW_TOM),
    (69, 72, 76, 79, 84, 88, 94),
):
    hit(bar, p, note, vel)

bar = 47
cymbal(bar, 0, CRASH, 114)
kick(bar, 0, 112)
snare(bar, 0, 111)
ghost(bar, 3, 43)
hit(bar, 4, HIGH_TOM, 92)
kick(bar, 6, 96)
hit(bar, 6, MID_TOM, 96)
cymbal(bar, 8, CRASH2, 116)
snare(bar, 8, 117)
kick(bar, 8, 112)
hit(bar, 10, FLOOR_TOM, 96)
hit(bar, 11, LOW_TOM, 101)
cymbal(bar, 12, CRASH, 120)
snare(bar, 12, 120)
kick(bar, 12, 119)

midi = mido.MidiFile(type=0, ticks_per_beat=TPB)
track = mido.MidiTrack()
midi.tracks.append(track)
track.append(mido.MetaMessage("track_name", name="The Long Way Home", time=0))
track.append(mido.MetaMessage("set_tempo", tempo=TEMPO, time=0))
track.append(mido.MetaMessage(
    "time_signature", numerator=4, denominator=4, time=0
))

previous = 0
for tick, is_on, note, velocity in sorted(
    events, key=lambda event: (event[0], event[1], event[2])
):
    assert tick <= END_TICK
    track.append(mido.Message(
        "note_on" if is_on else "note_off",
        channel=CHANNEL,
        note=note,
        velocity=velocity,
        time=tick - previous,
    ))
    previous = tick

track.append(mido.MetaMessage("end_of_track", time=END_TICK - previous))
midi.save(OUTFILE)
