#!/usr/bin/env python3
"""Write a two-minute, swung drum solo to solo.mid using mido."""

from collections import defaultdict

import mido

BPM = 104
TPB = 960
BAR_TICKS = 4 * TPB
BARS = 52
CHANNEL = 9  # General MIDI channel 10, zero-indexed

# A beat is divided into twelve parts. An upbeat at part 8 gives the solo
# its consistent two-to-one swing.
events = {}


def hit(bar, beat, sub, note, velocity, limb, priority=2, duration=105):
    """Place a strike, allowing at most one strike per limb at a grid position."""
    if not (0 <= bar < BARS and 0 <= velocity <= 127):
        return
    position = 12 * beat + sub
    if not (0 <= position < 48):
        return
    key = (bar, position, limb)
    candidate = (priority, note, velocity, duration)
    if key not in events or priority >= events[key][0]:
        events[key] = candidate


def kick(bar, beat, sub=0, velocity=92, note=36):
    hit(bar, beat, sub, note, velocity, "RF", 3, 115)


def snare(bar, beat, sub=0, velocity=96, note=38, priority=3):
    hit(bar, beat, sub, note, velocity, "LH", priority, 130)


def ghost(bar, beat, sub=0, velocity=39):
    snare(bar, beat, sub, velocity, priority=1)


def cym(bar, beat, sub=0, note=42, velocity=60, priority=1):
    duration = 300 if note == 46 else 135
    hit(bar, beat, sub, note, velocity, "RH", priority, duration)


def tom(bar, beat, sub, note, velocity, limb):
    hit(bar, beat, sub, note, velocity, limb, 3, 145)


def pedal(bar, beat, sub=0, velocity=52):
    hit(bar, beat, sub, 44, velocity, "LF", 2, 80)


def accent(bar, velocity=99, note=49):
    cym(bar, 0, 0, note, velocity, 5)
    kick(bar, 0, 0, min(116, velocity + 8))


def clear_hands_from(bar, beat):
    """Make room for a two-handed fill without extra cymbal strikes."""
    cutoff = beat * 12
    for key in list(events):
        if key[0] == bar and key[1] >= cutoff and key[2] in ("LH", "RH"):
            del events[key]


# Opening: a quiet call, then the answer that previews the main groove.
for bar in range(4):
    strength = (0, 3, 5, 9)[bar]
    for beat in (0, 2):
        kick(bar, beat, velocity=67 + strength)
    for beat in (1, 3):
        snare(bar, beat, velocity=55 + strength, note=37)
    for beat in range(4):
        if beat == 0 or (bar >= 2 and beat == 2):
            cym(bar, beat, note=42, velocity=42 + strength)
    if bar == 1:
        tom(bar, 3, 8, 45, 54, "RH")
    if bar == 2:
        kick(bar, 3, 8, 73)
        cym(bar, 3, 8, 56, 59)  # Cowbell: a small signature call.
    if bar == 3:
        ghost(bar, 2, 8, 38)
        snare(bar, 3, velocity=83)
        tom(bar, 3, 8, 43, 70, "RH")


# Main eight-bar idea. Its kick on the swung upbeat of beat two, ghost-note
# pickup, and occasional open hat are recognizable on each return.
def main_groove(bar, phrase_index, mode):
    local = phrase_index % 8
    level = {"A": 0, "A2": 5, "RETURN": 10}[mode]
    snares = (91, 94, 92, 97, 91, 95, 94, 99)
    hats = 54 if mode != "RETURN" else 63

    for beat in range(4):
        cym(bar, beat, note=51 if mode == "RETURN" else 42,
            velocity=hats + (8 if beat in (0, 2) else 1))
        if mode == "A2" or (mode == "RETURN" and local in (2, 3, 6)):
            cym(bar, beat, 8, note=51 if mode == "RETURN" else 42,
                velocity=hats - 15)
        elif beat in (0, 1, 3) or local in (1, 5):
            cym(bar, beat, 8, velocity=hats - 14)

    kick(bar, 0, velocity=96 + level // 2)
    kick(bar, 1, 8, velocity=76 + level // 2)
    if local in (1, 2, 4, 6, 7) or mode != "A":
        kick(bar, 2, 8, velocity=79 + level // 2)
    if local in (3, 7) or mode == "RETURN":
        kick(bar, 3, 8, velocity=76 + level // 2)

    snare(bar, 1, velocity=snares[local] + level)
    snare(bar, 3, velocity=min(116, snares[local] + level + 4))
    ghost(bar, 0, 8, 35 + level // 2)
    if local in (1, 3, 5, 7) or mode != "A":
        ghost(bar, 2, 8, 40 + level // 2)
    if mode != "A" and local in (2, 5):
        ghost(bar, 2, 4, 34)

    if local in (3, 7) and mode != "RETURN":
        cym(bar, 3, 8, note=46, velocity=67 + level)
    if mode == "A2" and local in (2, 6):
        pedal(bar, 2, velocity=48)


for bar in range(4, 12):
    main_groove(bar, bar - 4, "A")
accent(4, 94)

for bar in range(12, 20):
    main_groove(bar, bar - 12, "A2")
accent(12, 101, 57)

# Contrasting, roomy half-time passage: toms answer a single heavy backbeat.
for bar in range(20, 28):
    local = bar - 20
    kick(bar, 0, velocity=91)
    kick(bar, 1, 8, velocity=70)
    if local % 2:
        kick(bar, 3, velocity=86)
    else:
        kick(bar, 2, 8, velocity=78)

    snare(bar, 2, velocity=101 + (local % 4) * 2)
    ghost(bar, 1, 8, 37)
    for beat in (0, 2):
        cym(bar, beat, note=51, velocity=65)
    cym(bar, 3, 8, note=51, velocity=48)

    tom(bar, 1, 0, 45 if local % 2 == 0 else 47, 72, "RH")
    tom(bar, 3, 0, 43 if local % 2 == 0 else 41, 78, "RH")
    if local in (2, 6):
        cym(bar, 0, 8, note=53, velocity=69)  # Ride bell.
    if local in (3, 7):
        hit(bar, 3, 8, 64, 55, "LH", 2, 120)  # Low conga.

accent(20, 96)

# The original idea returns on the ride, brighter and more assertive.
for bar in range(28, 36):
    main_groove(bar, bar - 28, "RETURN")
accent(28, 108)


# Development: recognizable backbeats remain while triplet subdivisions,
# bass-drum replies, and tom answers accumulate.
for bar in range(36, 44):
    local = bar - 36
    intensity = local // 2
    for beat in range(4):
        cym(bar, beat, note=51 if local < 4 else 42,
            velocity=63 + 3 * intensity + (7 if beat in (0, 2) else 0))
        cym(bar, beat, 8, note=51 if local < 4 else 42,
            velocity=46 + 3 * intensity)
        if local >= 4:
            cym(bar, beat, 4, velocity=39 + 3 * intensity)
    kick(bar, 0, velocity=98 + intensity)
    kick(bar, 1, 8, velocity=80 + intensity)
    kick(bar, 2, 8, velocity=83 + intensity)
    if local >= 2:
        kick(bar, 3, 8, velocity=79 + intensity)
    snare(bar, 1, velocity=100 + intensity)
    snare(bar, 3, velocity=106 + intensity)
    ghost(bar, 0, 8, 40 + intensity)
    ghost(bar, 2, 4, 38 + intensity)
    if local in (1, 2, 4, 5):
        tom(bar, 2, 8, 47 if local % 2 else 45, 66 + intensity, "RH")
    if local >= 5:
        ghost(bar, 3, 4, 44 + intensity)
    if local in (3, 7):
        pedal(bar, 2, velocity=54)

accent(36, 104)
accent(40, 109, 57)


# Fill vocabulary. Clearing the hands first means every roll is physically
# playable; kick and hi-hat pedal remain available to the feet.
def fill(bar, start, strikes, bass=()):
    clear_hands_from(bar, start)
    for beat, sub, note, velocity, limb in strikes:
        tom(bar, beat, sub, note, velocity, limb)
    for beat, sub, velocity in bass:
        kick(bar, beat, sub, velocity)


fill(11, 2, [
    (2, 0, 38, 97, "LH"), (2, 8, 47, 76, "RH"),
    (3, 0, 45, 84, "LH"), (3, 4, 43, 77, "RH"),
    (3, 8, 41, 93, "LH"),
], [(3, 8, 88)])

fill(19, 2, [
    (2, 0, 38, 104, "LH"), (2, 4, 38, 47, "LH"),
    (2, 8, 50, 81, "RH"), (3, 0, 47, 88, "LH"),
    (3, 4, 45, 81, "RH"), (3, 8, 43, 94, "LH"),
], [(3, 0, 83), (3, 8, 95)])

fill(27, 2, [
    (2, 0, 38, 107, "LH"), (2, 8, 45, 82, "RH"),
    (3, 0, 43, 88, "LH"), (3, 4, 41, 83, "RH"),
    (3, 8, 38, 105, "LH"),
], [(2, 8, 82), (3, 8, 91)])

fill(35, 2, [
    (2, 0, 38, 109, "LH"), (2, 4, 38, 50, "LH"),
    (2, 8, 50, 86, "RH"), (3, 0, 47, 93, "LH"),
    (3, 4, 45, 87, "RH"), (3, 8, 41, 101, "LH"),
], [(3, 0, 91), (3, 8, 102)])

fill(43, 2, [
    (2, 0, 38, 111, "LH"), (2, 4, 38, 54, "LH"),
    (2, 8, 47, 88, "RH"), (3, 0, 45, 94, "LH"),
    (3, 4, 43, 89, "RH"), (3, 8, 41, 109, "LH"),
], [(2, 8, 88), (3, 8, 106)])


# Four-bar crest: strong backbeats, a rolling cymbal pulse, and short,
# composed answers rather than an indiscriminate wall of notes.
for bar in range(44, 48):
    local = bar - 44
    for beat in range(4):
        cym(bar, beat, note=51, velocity=77 + (7 if beat % 2 == 0 else 0))
        cym(bar, beat, 8, note=51, velocity=57)
        if beat in (1, 3):
            cym(bar, beat, 4, note=51, velocity=45)
    kick(bar, 0, velocity=110)
    kick(bar, 1, 8, velocity=89)
    kick(bar, 2, 8, velocity=91)
    kick(bar, 3, 8, velocity=86)
    snare(bar, 1, velocity=111)
    snare(bar, 3, velocity=116)
    ghost(bar, 0, 8, 46)
    ghost(bar, 2, 4, 47)
    pedal(bar, 2, velocity=58)
    if local in (1, 2):
        tom(bar, 2, 8, 47 if local == 1 else 45, 83, "RH")

accent(44, 116, 57)
accent(46, 108)

fill(47, 2, [
    (2, 0, 38, 113, "LH"), (2, 4, 38, 57, "LH"),
    (2, 8, 50, 92, "RH"), (3, 0, 47, 99, "LH"),
    (3, 4, 45, 92, "RH"), (3, 8, 41, 112, "LH"),
], [(2, 8, 92), (3, 8, 108)])


# Release: expose the opening call again, then land together and leave air.
accent(48, 105)
for bar in (48, 49):
    kick(bar, 0, velocity=93 if bar == 48 else 78)
    kick(bar, 2, velocity=81 if bar == 48 else 70)
    snare(bar, 1, velocity=94 if bar == 48 else 79)
    snare(bar, 3, velocity=96 if bar == 48 else 77)
    for beat in (0, 2):
        cym(bar, beat, note=42, velocity=61 if bar == 48 else 48)
    cym(bar, 1, 8, velocity=42)
    if bar == 48:
        ghost(bar, 2, 8, 39)

kick(50, 0, velocity=79)
snare(50, 1, velocity=67, note=37)
kick(50, 2, velocity=75)
hit(50, 3, 0, 56, 61, "RH", 2, 135)
snare(50, 3, velocity=72, note=37)

kick(51, 0, velocity=82)
snare(51, 0, velocity=77)
cym(51, 0, note=51, velocity=70)
ghost(51, 1, 8, 38)
# The final ensemble hit is on beat three, followed by a full beat of decay.
kick(51, 2, velocity=116)
snare(51, 2, velocity=119)
cym(51, 2, note=49, velocity=115, priority=5)
pedal(51, 2, velocity=65)


def timing_offset(limb, note, velocity):
    """Deliberate, consistent pocket—not random timing jitter."""
    if limb == "RF":
        return -8                         # Bass drum leans forward.
    if limb == "LH" and note in (38, 40):
        return 17 if velocity >= 65 else 7  # Backbeats sit behind.
    if limb == "LH":
        return 9
    if limb == "RH":
        return 2
    return 0


midi = mido.MidiFile(type=1, ticks_per_beat=TPB)
track = mido.MidiTrack()
midi.tracks.append(track)

track.append(mido.MetaMessage("track_name", name="Two-Minute Drum Solo", time=0))
track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
track.append(mido.MetaMessage(
    "time_signature", numerator=4, denominator=4, time=0
))

messages = []
for (bar, position, limb), (_, note, velocity, duration) in events.items():
    when = max(0, bar * BAR_TICKS + position * (TPB // 12)
               + timing_offset(limb, note, velocity))
    messages.append((when, 1, mido.Message(
        "note_on", channel=CHANNEL, note=note, velocity=velocity
    )))
    messages.append((when + duration, 0, mido.Message(
        "note_off", channel=CHANNEL, note=note, velocity=0
    )))

last_tick = 0
for tick, _, message in sorted(messages, key=lambda item: (item[0], item[1])):
    message.time = tick - last_tick
    track.append(message)
    last_tick = tick

track.append(mido.MetaMessage(
    "end_of_track", time=BARS * BAR_TICKS - last_tick
))
midi.save("solo.mid")
