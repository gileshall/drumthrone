#!/usr/bin/env python3
"""A deterministic, two-minute solo for one drummer and a GM percussion kit."""

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction

import mido


PPQ = 960
TEMPO = 468750                  # 128 BPM; 64 measures = exactly 120 seconds
BAR = 4 * PPQ
END = 64 * BAR
CHANNEL = 9                     # MIDI channel 10

# R/L are hands; K is the bass-drum foot; H is the hi-hat foot.
LIMBS = ("R", "L", "K", "H")


@dataclass
class Hit:
    bar: int
    pos: Fraction              # Position in sixteenth-note units
    limb: str
    note: int
    velocity: int
    swing: bool = True


score = [{limb: {} for limb in LIMBS} for _ in range(64)]


def put(bar, pos, limb, note, velocity, swing=True):
    pos = Fraction(pos)
    assert 0 <= bar < 64 and 0 <= pos < 16
    assert limb in LIMBS and 35 <= note <= 81
    assert limb != "K" or note in (35, 36)
    assert limb != "H" or note == 44
    # Replacing a limb's stroke is intentional: a crash replaces a ride stroke,
    # for example; it never adds a third hand.
    score[bar][limb][pos] = Hit(
        bar, pos, limb, note, max(1, min(127, round(velocity))), swing
    )


def erase(bar, start=0, stop=16, limbs=("R", "L")):
    for limb in limbs:
        for pos in list(score[bar][limb]):
            if start <= pos < stop:
                del score[bar][limb][pos]


def feet(bar, kicks, hats=(), strength=94):
    """Kick entries may be positions or (position, relative velocity) pairs."""
    for item in kicks:
        pos, delta = item if isinstance(item, tuple) else (item, 0)
        put(bar, pos, "K", 36, strength + delta)
    for pos in hats:
        put(bar, pos, "H", 44, 47 if pos in (4, 12) else 40)


def crash(bar, pos=0, velocity=108, note=49):
    put(bar, pos, "R", note, velocity)


def signature(bar, level=96, color="kit", ghosts=True):
    """The recurring 3+3+2 figure, twice, with a quiet inner conversation."""
    if color == "kit":
        voices = (38, 38, 50, 38, 38, 45)
        ghost = 38
    elif color == "toms":
        voices = (50, 47, 45, 48, 45, 43)
        ghost = 38
    elif color == "wood":
        voices = (76, 77, 60, 76, 77, 61)
        ghost = 37
    else:
        voices = (37, 37, 50, 37, 37, 45)
        ghost = 37

    for pos, limb, note, delta in zip(
        (0, 3, 6, 8, 11, 14),
        ("R", "L", "R", "R", "L", "R"),
        voices,
        (0, -16, -5, 4, -12, -1),
    ):
        put(bar, pos, limb, note, level + delta)
    if ghosts:
        for pos, delta in ((2, -59), (7, -52), (10, -62), (15, -49)):
            put(bar, pos, "L", ghost, level + delta)


KICK_PATTERNS = (
    (0, (6, -9), (8, -2), (14, -11)),
    (0, (7, -13), (10, -5)),
    (0, (3, -15), (8, -1), (11, -10), (14, -6)),
    (0, (6, -8), (10, -5), (15, -16)),
)


def groove(bar, level=96, ride=42, variation=0, busy=False):
    phrase = (0, -2, 1, -1)[variation % 4]
    for pos in range(0, 16, 2):
        velocity = level - (22 if pos % 8 == 0 else
                            33 if pos % 4 == 0 else 43)
        put(bar, pos, "R", ride, velocity + phrase)

    for pos in (4, 12):
        put(bar, pos, "L", 38, level + (3 if pos == 12 else 0))
    ghosts = ((3, -62), (7, -54), (10, -66), (15, -56))
    if not busy:
        ghosts = ghosts[:2] if variation % 2 == 0 else ghosts[2:]
    for pos, delta in ghosts:
        put(bar, pos, "L", 38, level + delta)

    if ride == 42 and variation % 4 == 2:
        put(bar, 14, "R", 46, level - 29)
        put(bar, 15, "H", 44, 46)
    if ride == 51 and variation % 4 in (1, 3):
        put(bar, 6, "R", 53, level - 18)
        put(bar, 14, "R", 53, level - 12)

    feet(bar, KICK_PATTERNS[variation % 4],
         (4, 12) if ride != 42 else (),
         level - 3)


def fill(bar, start=8, kind=0, level=100):
    """Alternating-hand phrases, not extra strokes laid over the groove."""
    erase(bar, start)
    count = 16 - start
    orchestrations = (
        (38, 38, 50, 50, 47, 47, 45, 43),
        (38, 50, 38, 47, 38, 45, 43, 38),
        (50, 38, 47, 38, 45, 38, 43, 43),
        (38, 38, 38, 50, 38, 47, 45, 43),
    )
    notes = orchestrations[kind % len(orchestrations)]
    for i in range(count):
        pos = start + i
        accent = i % 8 in (0, 3, 6)
        velocity = level - (0 if accent else 24)
        if i == count - 1:
            velocity = level - 7
        put(bar, pos, "R" if i % 2 == 0 else "L",
            notes[i % 8], velocity)


def triplet_fill(bar, start=8, beats=2, level=103, toms=True):
    erase(bar, start, start + 4 * beats)
    notes = (38, 38, 50, 50, 47, 47, 45, 45, 43, 43, 38, 38)
    for i in range(beats * 6):
        pos = Fraction(start) + Fraction(2 * i, 3)
        note = notes[i % len(notes)] if toms else 38
        put(bar, pos, "R" if i % 2 == 0 else "L", note,
            level - (0 if i % 3 == 0 else 23 if i % 3 == 1 else 14),
            swing=False)


def roll(bar, start, stop, low, high):
    """A short, played single-stroke crescendo: two hands, no MIDI buzz."""
    erase(bar, start, stop)
    count = int((stop - start) * 2)
    for i in range(count):
        velocity = low + (high - low) * i / max(1, count - 1)
        velocity += 3 if i % 4 == 0 else -5 if i % 2 else 0
        put(bar, Fraction(start) + Fraction(i, 2),
            "R" if i % 2 == 0 else "L", 38, velocity)


# I. An audible identity, with room around it.
signature(0, 88, ghosts=False)
feet(0, (0, 8), strength=84)

for pos, limb, note, vel in (
    (0, "R", 42, 57), (4, "L", 37, 67), (6, "R", 50, 73),
    (8, "R", 42, 54), (11, "L", 37, 53), (14, "R", 45, 80),
):
    put(1, pos, limb, note, vel)
feet(1, (0, (10, -10)), (4, 12), 84)

signature(2, 92)
feet(2, (0, (6, -12), 8, (14, -8)), (4, 12), 86)

groove(3, 88, variation=1)
fill(3, 12, 0, 87)

signature(4, 97)
feet(4, (0, (6, -12), 8, (14, -7)), (4, 12), 90)
groove(5, 92, variation=2)
signature(6, 97, "toms")
feet(6, (0, 8), (4, 12), 90)
groove(7, 95, variation=3)
fill(7, 8, 1, 96)

# II. Pocket: the motif becomes bass-drum placement and snare punctuation.
for bar in range(8, 16):
    groove(bar, 99 + (bar % 4 == 2) * 3, variation=bar - 8,
           busy=bar in (10, 12, 14))
crash(8, velocity=108)
fill(11, 12, 3, 98)

# A brief interruption of the expected backbeat quotes the opening.
erase(14, 8)
for pos, limb, note, vel in (
    (8, "R", 38, 103), (10, "L", 38, 35),
    (11, "L", 38, 82), (14, "R", 45, 101),
    (15, "L", 38, 42),
):
    put(14, pos, limb, note, vel)
triplet_fill(15, 8, 2, 104)

# III. Travel around the toms; the left foot keeps the room oriented.
for bar in range(16, 24):
    feet(bar, (0, (6, -12), (10, -8)), (0, 4, 8, 12), 95)
    if bar % 2 == 0:
        signature(bar, 101 + (bar - 16), "toms")
    else:
        for i, pos in enumerate(range(0, 16, 2)):
            note = (43, 45, 47, 45)[i % 4]
            put(bar, pos, "R", note, 78 + (10 if pos % 8 == 0 else 0))
        for pos, note, vel in ((3, 38, 42), (4, 38, 101),
                               (7, 38, 45), (11, 38, 37),
                               (12, 38, 105), (15, 38, 49)):
            put(bar, pos, "L", note, vel)
crash(16, velocity=110)
fill(19, 8, 2, 104)
# Phrase 22 expands the opening rhythm across the entire kit.
erase(22)
for i in range(16):
    note = (50, 38, 38, 47, 38, 38, 45, 38,
            48, 38, 38, 45, 38, 38, 43, 38)[i]
    put(22, i, "R" if i % 2 == 0 else "L", note,
        108 if i in (0, 3, 6, 8, 11, 14) else 52)
triplet_fill(23, 8, 2, 109)

# IV. Contrast: mounted bell, woodblocks and a small pair of bongos.
# The feet still belong to the same player, not an overdubbed percussionist.
bell_pattern = (0, 3, 6, 8, 10, 13)
for bar in range(24, 32):
    feet(bar, (0, (6, -14), (10, -9)), (4, 12), 82)
    for pos in bell_pattern:
        put(bar, pos, "R", 56, 83 if pos in (0, 6, 10) else 65)
    for pos, note, vel in ((2, 60, 56), (4, 61, 81),
                           (7, 60, 64), (11, 60, 49),
                           (12, 61, 85), (15, 60, 59)):
        put(bar, pos, "L", note, vel)
    if bar % 2:
        put(bar, 14, "R", 77, 74)

# Return the rhythm in a different accent and register.
erase(26)
signature(26, 91, "wood")
erase(28)
signature(28, 95, "wood")
erase(29, 8)
for i, pos in enumerate((8, 9, 11, 12, 14, 15)):
    put(29, pos, "R" if i % 2 == 0 else "L",
        (60, 61, 76, 77, 60, 61)[i], (88, 58, 82, 65, 92, 69)[i])
erase(30)
for i in range(16):
    put(30, i, "R" if i % 2 == 0 else "L",
        (60, 61, 60, 77, 60, 61, 76, 61)[i % 8],
        88 if i in (0, 3, 6, 8, 11, 14) else 51)

erase(31, 8, limbs=LIMBS)
put(31, 8, "R", 77, 85)
put(31, 8, "K", 36, 82)
# Nearly two beats of genuine silence before the quiet chapter.

# V. Close-up: side-stick, dry hat, sparse bass, and low ghosts.
for bar in range(32, 40):
    level = (65, 68, 70, 66, 72, 75, 80, 85)[bar - 32]
    for pos in (0, 4, 8, 12):
        put(bar, pos, "R", 42, level - (18 if pos % 8 == 0 else 25))
    for pos in (4, 12):
        put(bar, pos, "L", 37, level + (3 if pos == 12 else 0))
    feet(bar, (0, (10 if bar % 2 else 8, -12)), strength=level + 4)
    if bar in (33, 35, 37, 38, 39):
        put(bar, 7, "L", 38, 28 + bar - 33)
        put(bar, 15, "L", 38, 31 + bar - 33)
    if bar >= 36:
        for pos in (2, 6, 10, 14):
            put(bar, pos, "R", 42, level - 34)

erase(34)
signature(34, 70, "quiet", ghosts=False)
erase(38, 8)
for pos, limb, note, vel in (
    (8, "R", 37, 81), (10, "L", 38, 28), (11, "L", 37, 63),
    (14, "R", 45, 76), (15, "L", 38, 34),
):
    put(38, pos, limb, note, vel)
fill(39, 12, 3, 87)

# VI. Open up the sound and gradually increase the internal motion.
for bar in range(40, 48):
    level = (91, 94, 98, 97, 102, 104, 108, 109)[bar - 40]
    groove(bar, level, ride=51, variation=bar - 40, busy=bar >= 42)
crash(40, velocity=102, note=55)
fill(43, 12, 1, 102)
crash(44, velocity=113, note=49)
fill(45, 12, 2, 106)
# A three-over-four accent cycle while the backbeat remains audible.
for pos in (0, 3, 6, 9, 12, 15):
    put(46, pos, "R", 53, 99 if pos in (0, 6, 12) else 84)
# Remove the intervening ride taps: this is a phrase, not a random spray.
for pos in (2, 4, 8, 10, 14):
    score[46]["R"].pop(Fraction(pos), None)
triplet_fill(47, 8, 2, 113)

# VII. Peak. Fast hands are used in short phrases, with answers and air.
groove(48, 114, ride=51, variation=0, busy=True)
crash(48, velocity=120, note=57)
groove(49, 112, ride=51, variation=1, busy=True)
fill(49, 12, 3, 110)

feet(50, (0, (6, -10), 8, (14, -7)), (4, 12), 108)
fill(50, 0, 1, 115)
# The peak's accents still say 3+3+2.
for limb in ("R", "L"):
    for pos, hit in score[50][limb].items():
        hit.velocity = 116 if pos in (0, 3, 6, 8, 11, 14) else 65

signature(51, 111, "toms", ghosts=False)
feet(51, (0, 8), (4, 12), 103)
erase(51, 12, limbs=("R", "L", "K"))
put(51, 15, "L", 38, 57)

groove(52, 116, ride=51, variation=2, busy=True)
crash(52, velocity=121)
fill(53, 0, 2, 115)
feet(53, (0, (7, -9), 10, (14, -7)), (0, 4, 8, 12), 109)

groove(54, 115, ride=53, variation=3, busy=True)
roll(54, 12, 16, 72, 118)

feet(55, (0, 6, 8), (4,), 110)
fill(55, 0, 0, 116)
erase(55, 8, limbs=LIMBS)
put(55, 8, "R", 49, 119)
put(55, 8, "L", 38, 116)
put(55, 8, "K", 36, 116)
# Stop, breathe, then a quiet triplet pickup into the reprise.
triplet_fill(55, 12, 1, 84, toms=False)

# VIII. Recognizable homecoming, then a concise final statement.
signature(56, 107)
feet(56, (0, (6, -11), 8, (14, -8)), (4, 12), 104)
signature(57, 101)
feet(57, (0, 8), (4, 12), 99)
groove(58, 106, variation=0, busy=False)
groove(59, 110, variation=1, busy=True)
fill(59, 8, 1, 108)

signature(60, 114, "toms")
feet(60, (0, (6, -8), 8, (14, -6)), (4, 12), 108)

# A last swell, growing out of the motif rather than starting a new idea.
signature(61, 104, ghosts=False)
feet(61, (0, 8), (4, 12), 104)
roll(61, 8, 16, 49, 116)

fill(62, 0, 0, 116)
feet(62, (0, 4, 8, 12), (4, 12), 111)
for limb in ("R", "L"):
    for pos, hit in score[62][limb].items():
        hit.velocity = 119 if pos in (0, 3, 6, 8, 11, 14) else 77

# One final compact flourish; the last chord has almost a second to ring.
triplet_fill(63, 0, 1, 116)
feet(63, (0,), strength=112)
for pos, limb, note, velocity in (
    (4, "R", 50, 112), (5, "L", 47, 96),
    (6, "R", 45, 111), (7, "L", 43, 104),
    (8, "R", 49, 124), (8, "L", 43, 119),
):
    put(63, pos, limb, note, velocity)
put(63, 8, "K", 36, 122)


def performed_tick(hit):
    """Shared light sixteenth swing plus deliberate limb/articulation placement."""
    pos = hit.pos
    if hit.swing:
        pair = pos // 2
        within = pos - 2 * pair
        # 54.6:45.4 sixteenths. Quarter/eighth anchors do not move.
        if within <= 1:
            local = pair * 480 + within * 262
        else:
            local = pair * 480 + 262 + (within - 1) * 218
    else:
        local = pos * 240

    if hit.limb == "K":
        placement = -6           # Bass drum leans into the beat.
    elif hit.limb == "H":
        placement = 3
    elif hit.note in (38, 37) and hit.pos in (4, 12):
        placement = 15           # A relaxed, consistent backbeat.
    elif hit.note == 38 and hit.velocity < 60:
        placement = -3           # Ghosts lead into the accented notes.
    elif hit.note in (42, 46, 51, 53, 56):
        placement = 2
    else:
        placement = 0

    # Final ensemble chord lands together rather than smearing the release.
    if hit.bar == 63 and hit.pos == 8:
        placement = 0
    return max(0, hit.bar * BAR + round(local) + placement)


performed = []
for measure in score:
    for limb in LIMBS:
        for hit in measure[limb].values():
            performed.append((performed_tick(hit), hit))
performed.sort(key=lambda item: (item[0], LIMBS.index(item[1].limb)))

# Check the actual performed score, including across measure boundaries.
# No limb can double-book itself or play impossibly close duplicate strokes.
last_by_limb = {}
simultaneous = defaultdict(list)
for tick, hit in performed:
    if hit.limb in last_by_limb:
        gap = tick - last_by_limb[hit.limb]
        assert gap >= (110 if hit.limb in ("R", "L") else 150), (
            "Unplayable limb spacing", hit, gap
        )
    last_by_limb[hit.limb] = tick
    simultaneous[tick].append(hit.limb)

for limbs in simultaneous.values():
    assert len(set(limbs)) == len(limbs)
    assert sum(limb in ("R", "L") for limb in limbs) <= 2
    assert sum(limb in ("K", "H") for limb in limbs) <= 2


def duration(note):
    if note in (49, 52, 55, 57):
        return 3200
    if note in (51, 53, 59):
        return 650
    if note == 46:
        return 600
    if note in (41, 43, 45, 47, 48, 50):
        return 330
    if note in (60, 61, 62, 63, 64):
        return 210
    return 90


# Avoid overlapping note lifetimes for repeated notes, and explicitly shorten
# an open hat at the next closed-hat or pedal stroke.
next_same = {}
next_hat_close = None
lifetimes = []
for tick, hit in reversed(performed):
    end = min(END, tick + duration(hit.note))
    if hit.note in next_same:
        end = min(end, next_same[hit.note] - 1)
    if hit.note == 46 and next_hat_close is not None:
        end = min(end, next_hat_close)
    if hit.note in (42, 44):
        next_hat_close = tick
    next_same[hit.note] = tick
    lifetimes.append((tick, max(tick + 1, end), hit))


midi = mido.MidiFile(type=1, ticks_per_beat=PPQ)

conductor = mido.MidiTrack()
midi.tracks.append(conductor)
conductor.append(mido.MetaMessage(
    "track_name", name="Three, Three, Two - a solo for one drummer", time=0))
conductor.append(mido.MetaMessage("set_tempo", tempo=TEMPO, time=0))
conductor.append(mido.MetaMessage(
    "time_signature", numerator=4, denominator=4,
    clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))

sections = (
    (0, "I - State the idea"),
    (8, "II - In the pocket"),
    (16, "III - Around the toms"),
    (24, "IV - Wood and bell"),
    (32, "V - Bring the room closer"),
    (40, "VI - Open the sound"),
    (48, "VII - Over the top, then breathe"),
    (56, "VIII - Home"),
)
previous = 0
for bar, label in sections:
    tick = bar * BAR
    conductor.append(mido.MetaMessage("marker", text=label, time=tick - previous))
    previous = tick
conductor.append(mido.MetaMessage("end_of_track", time=END - previous))

drums = mido.MidiTrack()
midi.tracks.append(drums)
drums.append(mido.MetaMessage("track_name", name="One drummer - GM standard kit"))
drums.append(mido.Message("sysex", data=(0x7E, 0x7F, 0x09, 0x01), time=0))
drums.append(mido.Message("program_change", channel=CHANNEL, program=0, time=0))
for control, value in ((7, 105), (10, 64), (11, 127), (91, 24), (93, 0)):
    drums.append(mido.Message(
        "control_change", channel=CHANNEL, control=control, value=value, time=0))

events = []
for start, end, hit in lifetimes:
    events.append((start, 1, hit.note, mido.Message(
        "note_on", channel=CHANNEL, note=hit.note, velocity=hit.velocity)))
    events.append((end, 0, hit.note, mido.Message(
        "note_off", channel=CHANNEL, note=hit.note, velocity=0)))

events.sort(key=lambda item: (item[0], item[1], item[2]))
previous = 0
for tick, _, _, message in events:
    drums.append(message.copy(time=tick - previous))
    previous = tick
drums.append(mido.MetaMessage("end_of_track", time=END - previous))

midi.save("solo.mid")
