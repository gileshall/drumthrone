#!/usr/bin/env python3
"""Write solo.mid: a deterministic, two-minute solo for one GM drummer.

64 bars of 4/4 at 128 BPM. MIDI channel 10 throughout.
The score is assigned to individual limbs before it is rendered.
Requires only mido and the Python standard library.
"""

from collections import defaultdict
from dataclasses import dataclass
import mido


PPQ = 960
BAR = 4 * PPQ
BARS = 64
END = BARS * BAR
CHANNEL = 9                       # MIDI channel 10, zero-based
TEMPO = mido.bpm2tempo(128)         # Exactly 468750 microseconds/quarter

KICK = 36
SIDE = 37
SNARE = 38
FLOOR = 41
HAT = 42
LOW = 43
PEDAL = 44
MID = 45
OPEN = 46
HIGH = 47
HIGHER = 48
CRASH = 49
TOP = 50
RIDE = 51
CHINA = 52
BELL = 53
TAMBOURINE = 54
SPLASH = 55
COWBELL = 56
CONGA_SLAP = 62
CONGA = 63
LOW_CONGA = 64
HIGH_BLOCK = 76
LOW_BLOCK = 77

CYMBALS = {CRASH, CHINA, SPLASH, RIDE, BELL, OPEN}
HANDS = {"R", "L"}
LIMBS = ("R", "L", "K", "P")


@dataclass(frozen=True)
class Stroke:
    bar: int
    step: float                  # Sixteenth-note units; .5 gives a 32nd
    limb: str
    note: int
    velocity: int
    priority: int = 2
    feel: str = "pocket"


score = {}


def hit(bar, step, limb, note, velocity, priority=2, feel="pocket"):
    """Place or deliberately replace a stroke in one limb's score."""
    assert 0 <= bar < BARS and 0 <= step < 16
    assert limb in LIMBS and 35 <= note <= 81
    assert abs(step * 2 - round(step * 2)) < 1e-8
    if limb == "K":
        assert note == KICK
    if limb == "P":
        assert note == PEDAL
    velocity = max(1, min(127, int(round(velocity))))
    key = (bar, int(round(step * 2)), limb)
    score[key] = Stroke(bar, step, limb, note, velocity, priority, feel)


def clear_hands(bar, start=0, stop=16):
    for key, stroke in list(score.items()):
        if (stroke.bar == bar and stroke.limb in HANDS
                and start <= stroke.step < stop):
            del score[key]


def feet(bar, kicks=(0, 8), hats=(4, 12), level=78):
    for i, step in enumerate(kicks):
        hit(bar, step, "K", KICK,
            level + (5 if step in (0, 8) else -5) + (i % 2) * 2)
    for step in hats:
        hit(bar, step, "P", PEDAL, 43 if step in (4, 12) else 35)


def time_hand(bar, voice=HAT, level=63, steps=range(0, 16, 2)):
    # Strong quarters and light offbeats: a wrist motion, not random jitter.
    for step in steps:
        v = level + (7 if step % 4 == 0 else -9)
        if step == 14:
            v -= 3
        hit(bar, step, "R", voice, v, 1)


def backbeat(bar, level=99, ghosts=(3, 7, 10, 15), side=False):
    voice = SIDE if side else SNARE
    for step in (4, 12):
        hit(bar, step, "L", voice, level + (3 if step == 12 else 0), 3)
    for i, step in enumerate(ghosts):
        hit(bar, step, "L", SNARE, 30 + (i % 3) * 5, 1)


# The solo's identifying sentence: four accents separated by two little
# pickups. Its rhythm survives changes of orchestration, register and dynamics.
SIGNATURE = ((0, 1.00), (3, .38), (6, .91),
             (10, .96), (12, .35), (14, 1.04))


def signature(bar, level=96, voice=SNARE, displacement=0, hand="L"):
    for step, weight in SIGNATURE:
        step = (step + displacement) % 16
        note = voice if weight > .5 else SNARE
        hit(bar, step, hand, note, level * weight,
            3 if weight > .5 else 1)


def answer(bar, level=94, voice=SNARE):
    for step, weight in ((2, .80), (4, 1.0), (7, .38),
                         (9, .72), (12, 1.04), (15, .43)):
        hit(bar, step, "L", voice, level * weight,
            3 if weight > .7 else 1)


def crash(bar, step=0, level=106, voice=CRASH):
    hit(bar, step, "R", voice, level, 4)
    hit(bar, step, "K", KICK, min(116, level - 4), 3)


def fill(bar, start=12, stop=16, level=93, kind="down", fine=False):
    """Replace, rather than add to, the two-hand part."""
    clear_hands(bar, start, stop)
    if kind == "down":
        notes = (SNARE, SNARE, TOP, HIGH, MID, MID, LOW, FLOOR)
    elif kind == "up":
        notes = (FLOOR, LOW, MID, MID, HIGH, TOP, SNARE, SNARE)
    elif kind == "snare":
        notes = (SNARE,) * 8
    else:
        notes = (SNARE, HIGH, SNARE, MID, SNARE, LOW, FLOOR, FLOOR)

    increment = .5 if fine else 1
    count = int(round((stop - start) / increment))
    for i in range(count):
        step = start + i * increment
        limb = "R" if i % 2 == 0 else "L"
        note = notes[min(7, int(i * 8 / max(1, count)))]
        # A shaped phrase, not a machine-gun line of identical strokes.
        accent = (i % 4 == 0 or i == count - 1)
        v = level + (8 if accent else -20) + 5 * i / max(1, count - 1)
        hit(bar, step, limb, note, v, 3 if accent else 1,
            "roll" if fine else "pocket")


def tom_signature(bar, level=96, shift=0):
    voices = (FLOOR, SNARE, HIGH, MID, SNARE, LOW)
    for i, (step, weight) in enumerate(SIGNATURE):
        step = (step + shift) % 16
        limb = "R" if i % 2 == 0 else "L"
        hit(bar, step, limb, voices[i], level * weight,
            3 if weight > .5 else 1)


# ---------------------------------------------------------------------------
# I. An invitation: air, cross-stick, then the first complete statement.
# ---------------------------------------------------------------------------

feet(0, (0,), (4, 12), 67)
for s, v in ((0, 66), (6, 60), (10, 64), (14, 70)):
    hit(0, s, "L", SIDE, v, 3)
for s in (0, 8):
    hit(0, s, "R", HAT, 46)

feet(1, (0, 7, 10), (4, 12), 69)
time_hand(1, HAT, 49, (0, 4, 8, 12))
answer(1, 70, SIDE)

feet(2, (0, 8), (4, 12), 73)
time_hand(2, HAT, 54)
signature(2, 81, SIDE)

feet(3, (0, 6, 10), (4, 12), 75)
time_hand(3, HAT, 56)
answer(3, 78, SIDE)
fill(3, 14, level=68, kind="snare")

feet(4, (0, 7, 8), (4, 12), 78)
time_hand(4, HAT, 59)
signature(4, 88)

feet(5, (0, 6, 10, 14), (4, 12), 78)
time_hand(5, HAT, 60)
backbeat(5, 91, (3, 9, 15))

feet(6, (0, 8, 11), (4, 12), 79)
time_hand(6, HAT, 61)
signature(6, 92)
hit(6, 14, "R", OPEN, 72)

feet(7, (0, 7, 10), (4, 12), 80)
time_hand(7, HAT, 62)
answer(7, 89)
fill(7, 10, level=85, kind="down")

# ---------------------------------------------------------------------------
# II. The pocket: two-bar conversations and increasingly confident answers.
# ---------------------------------------------------------------------------

kick_patterns = ((0, 6, 8, 11), (0, 7, 10),
                 (0, 3, 8, 14), (0, 6, 10, 15))

for b in range(8, 16):
    j = b - 8
    feet(b, kick_patterns[j % 4], (4, 12), 87)
    time_hand(b, HAT, 66 + j // 3)
    if j % 4 == 0:
        signature(b, 100)
    elif j % 4 == 2:
        signature(b, 97, displacement=2)
    else:
        backbeat(b, 102, (2, 7, 9, 15))
    if j in (1, 5):
        hit(b, 14, "R", OPEN, 77)
    if j == 3:
        fill(b, 12, level=88, kind="snare")
    if j == 7:
        fill(b, 8, level=99, kind="down")

crash(8, level=106, voice=SPLASH)

# ---------------------------------------------------------------------------
# III. Move the same sentence around the toms; pedal hat keeps the listener
# oriented while the hands briefly suggest a different downbeat.
# ---------------------------------------------------------------------------

for b in range(16, 24):
    j = b - 16
    feet(b, (0, 8) if j % 2 == 0 else (0, 7, 10),
         (0, 4, 8, 12), 83)
    if j % 2 == 0:
        tom_signature(b, 98 + j, 2 if j == 4 else 0)
        for s in (4, 8):
            hit(b, s, "R", RIDE, 56, 1)
        for s in (5, 13):
            hit(b, s, "L", SNARE, 32, 1)
    else:
        time_hand(b, RIDE, 64, (0, 4, 8))
        backbeat(b, 101, (3, 7))
        fill(b, 10 if j != 7 else 8, level=94 + j, kind="around")

crash(16, level=110)
# A one-bar descending answer, followed by a genuine breath.
clear_hands(22, 8, 16)
for s, note, limb, vel in (
        (8, HIGH, "R", 94), (9, MID, "L", 68),
        (10, LOW, "R", 89), (12, FLOOR, "L", 103)):
    hit(22, s, limb, note, vel, 3)

# ---------------------------------------------------------------------------
# IV. Change the color, not the drummer: nearby cowbell and mounted congas.
# The hands alternate conversationally; the feet remain a quiet kit ostinato.
# ---------------------------------------------------------------------------

for b in range(24, 32):
    j = b - 24
    feet(b, (0, 8) if j < 6 else (0, 6, 8, 14),
         (4, 12), 64 + j)
    if j % 2 == 0:
        for i, (s, w) in enumerate(SIGNATURE):
            note = (LOW_CONGA if i in (0, 5) else
                    CONGA_SLAP if w > .5 else CONGA)
            hit(b, s, "L", note, (87 + j) * (w if w > .5 else .66),
                3 if w > .5 else 1)
        for s, v in ((0, 64), (4, 56), (8, 67), (12, 54)):
            hit(b, s, "R", COWBELL, v, 1)
    else:
        for s, note, v in ((0, LOW_CONGA, 84), (3, CONGA, 54),
                           (4, CONGA_SLAP, 94), (7, CONGA, 50),
                           (10, LOW_CONGA, 82), (12, CONGA_SLAP, 97),
                           (15, CONGA, 48)):
            hit(b, s, "L", note, v, 2)
        for s, note, v in ((2, HIGH_BLOCK, 67), (6, LOW_BLOCK, 74),
                           (8, HIGH_BLOCK, 66), (14, LOW_BLOCK, 72)):
            hit(b, s, "R", note, v, 2)

# A little two-hand conga answer; no extra kit hands are hiding underneath.
clear_hands(27, 12, 16)
for i, note in enumerate((CONGA_SLAP, CONGA, LOW_CONGA, CONGA)):
    hit(27, 12 + i, "R" if i % 2 == 0 else "L",
        note, (91, 56, 82, 50)[i])

clear_hands(30, 12, 16)
hit(30, 12, "R", COWBELL, 87, 3)
hit(30, 14, "L", LOW_CONGA, 83, 3)

clear_hands(31, 8, 16)
for s, limb, note, v in (
        (8, "R", HIGH_BLOCK, 79), (10, "L", CONGA_SLAP, 88),
        (11, "R", CONGA, 53), (12, "L", LOW_CONGA, 89)):
    hit(31, s, limb, note, v)
# The last three sixteenths are intentionally empty.

# ---------------------------------------------------------------------------
# V. Release: small sounds and negative space. The motif is almost whispered.
# ---------------------------------------------------------------------------

feet(32, (0,), (4, 12), 53)
hit(32, 0, "R", SPLASH, 52, 3)
hit(32, 6, "L", SIDE, 48)
hit(32, 14, "L", SIDE, 55)

feet(33, (0, 10), (4, 12), 55)
for s in (0, 8):
    hit(33, s, "R", HAT, 39, 1)
answer(33, 56, SIDE)

feet(34, (0, 8), (4, 12), 58)
time_hand(34, HAT, 43, (0, 4, 8, 12))
signature(34, 62, SIDE)

feet(35, (0,), (4, 12), 56)
hit(35, 4, "L", SIDE, 65, 3)
hit(35, 7, "L", SNARE, 25, 1)
hit(35, 12, "R", TAMBOURINE, 47, 2)

for b in (36, 37, 38, 39):
    j = b - 36
    feet(b, (0, 8) if j < 2 else (0, 7, 10), (4, 12), 62 + j * 5)
    time_hand(b, HAT, 46 + j * 5)
    if j % 2 == 0:
        signature(b, 69 + j * 7)
    else:
        backbeat(b, 75 + j * 5, (3, 7, 10, 15))
fill(39, 12, level=75, kind="snare", fine=True)

# ---------------------------------------------------------------------------
# VI. Rudimental development. Alternating singles, then a paradiddle-derived
# sticking. Accent groups of three lean across the bar without losing time.
# ---------------------------------------------------------------------------

PARADIDDLE = ("R", "L", "R", "R", "L", "R", "L", "L")

for b in range(40, 48):
    j = b - 40
    feet(b, (0, 8) if j < 4 else (0, 6, 8, 14),
         (0, 4, 8, 12), 78 + j * 3)

    if j in (0, 2):
        time_hand(b, HAT, 58 + j * 2)
        signature(b, 89 + j * 3)
        fill(b, 8, level=81 + j * 3, kind="snare")
    elif j in (1, 3, 4, 5):
        for s in range(16):
            limb = PARADIDDLE[s % 8]
            accented = ((s + (2 if j == 3 else 0)) % 3 == 0)
            if s == 0:
                accented = True
            note = SNARE
            if accented and j >= 4:
                note = HIGH if limb == "R" else LOW
            v = (91 + j * 3) if accented else (38 + j * 3 + (s % 2) * 5)
            hit(b, s, limb, note, v, 3 if accented else 1)
    elif j == 6:
        fill(b, 0, 8, level=104, kind="around")
        fill(b, 8, 16, level=100, kind="snare", fine=True)
    else:
        fill(b, 0, 8, level=107, kind="down")
        # Silence before the return is more emphatic than another full bar.
        hit(b, 8, "R", CHINA, 112, 4)
        hit(b, 8, "L", SNARE, 111, 4)
        hit(b, 8, "K", KICK, 113, 4)
        # Remove the later bass-drum pickup, too.
        for key, stroke in list(score.items()):
            if stroke.bar == b and stroke.limb == "K" and stroke.step > 8:
                del score[key]

# ---------------------------------------------------------------------------
# VII. Recapitulation: the opening sentence, now with ride and full backbeats.
# ---------------------------------------------------------------------------

for b in range(48, 56):
    j = b - 48
    feet(b, kick_patterns[j % 4], (4, 12), 97)
    time_hand(b, RIDE, 79 if j < 4 else 74)
    for s in (0, 8):
        hit(b, s, "R", BELL, 88 if j < 4 else 80, 2)
    if j in (0, 2, 4, 6):
        signature(b, 113 if j < 4 else 106)
    else:
        backbeat(b, 114 if j < 4 else 108, (3, 7, 9, 15))

    if j == 3:
        fill(b, 12, level=102, kind="down")
    elif j == 5:
        # Half-time answer: leave the second half open.
        clear_hands(b, 0, 16)
        time_hand(b, RIDE, 69, (0, 4, 8, 12))
        hit(b, 8, "L", SNARE, 113, 3)
        hit(b, 7, "L", SNARE, 34, 1)
        hit(b, 14, "L", SNARE, 40, 1)
    elif j == 7:
        fill(b, 10, level=109, kind="up")

crash(48, level=119)
crash(52, level=105, voice=SPLASH)

# ---------------------------------------------------------------------------
# VIII. Final ascent, one last unmistakable statement, and a short coda.
# ---------------------------------------------------------------------------

for b in range(56, 60):
    j = b - 56
    feet(b, (0, 3, 6, 8, 11, 14) if j % 2 else (0, 6, 8, 14),
         (0, 4, 8, 12), 102 + j * 2)
    if j == 0:
        time_hand(b, BELL, 88)
        signature(b, 117)
        crash(b, level=121)
    elif j == 1:
        time_hand(b, RIDE, 84, (0, 2, 4, 6))
        backbeat(b, 116, (3, 7))
        fill(b, 8, level=112, kind="around")
    elif j == 2:
        fill(b, 0, 8, level=110, kind="snare", fine=True)
        fill(b, 8, 16, level=115, kind="down")
    else:
        fill(b, 0, 8, level=113, kind="up")
        fill(b, 8, 14, level=112, kind="snare", fine=True)
        hit(b, 14, "R", CHINA, 120, 4)
        hit(b, 14, "L", FLOOR, 117, 4)

feet(60, (0, 6, 8, 11), (4, 12), 108)
time_hand(60, BELL, 88)
signature(60, 119)
crash(60, level=122)

feet(61, (0, 7, 10), (4, 12), 106)
time_hand(61, RIDE, 82)
answer(61, 116)
fill(61, 8, level=115, kind="down")

# Stop-time version of the motif. Both hands are explicitly accounted for.
for i, s in enumerate((0, 6, 10, 14)):
    hit(62, s, "R", (CRASH, HIGH, MID, FLOOR)[i],
        (118, 112, 115, 120)[i], 4)
    hit(62, s, "L", SNARE if i in (0, 3) else LOW,
        (118, 101, 106, 121)[i], 4)
    hit(62, s, "K", KICK, 114 + i, 4)
hit(62, 3, "L", SNARE, 36, 1)
hit(62, 12, "L", SNARE, 39, 1)

# Last downbeat at 118.125 seconds, with the remaining bar left to decay.
hit(63, 0, "R", CRASH, 125, 4)
hit(63, 0, "L", SNARE, 121, 4)
hit(63, 0, "K", KICK, 120, 4)


# ---------------------------------------------------------------------------
# Performance and MIDI rendering.
# ---------------------------------------------------------------------------

def performance_tick(stroke):
    """A shared swung grid, with consistent roles relative to that grid."""
    s = stroke.step
    whole = int(s)
    fraction = s - whole

    if stroke.feel == "roll":
        swing = 0
    else:
        # 56.7:43.3 sixteenth swing. Interpolate any intervening 32nds.
        a = 32 if whole % 2 else 0
        b = 32 if (whole + 1) % 2 else 0
        swing = a + (b - a) * fraction

    if stroke.feel == "roll":
        placement = 0
    elif stroke.limb == "K":
        placement = -8             # Bass drum gently leads.
    elif stroke.limb == "P":
        placement = 3
    elif stroke.note == SNARE:
        placement = 15 if stroke.velocity >= 65 else 22
    elif stroke.note == SIDE:
        placement = 17
    elif stroke.note in (CONGA, CONGA_SLAP, LOW_CONGA, HIGH_BLOCK, LOW_BLOCK):
        placement = 7
    else:
        placement = -2

    if 32 <= stroke.bar < 40 and stroke.limb in HANDS:
        placement += 7             # The quiet passage sits farther back.
    if 40 <= stroke.bar < 48 and stroke.limb in HANDS:
        placement -= 5             # The build leans gently forward.

    # The ending is a unified ensemble gesture, not a loose flam.
    if stroke.bar == 63:
        placement = 0

    return max(0, int(round(stroke.bar * BAR + s * PPQ / 4
                            + swing + placement)))


def playable_performance():
    """Resolve transition pickups without moving accents off their grid.

    Each limb has a minimum recovery time of about 90 ms. This also prevents
    a last 32nd of a fill from demanding an impossible same-hand next downbeat.
    Within that window, a main accent takes precedence over a grace stroke.
    """
    by_limb = defaultdict(list)
    for stroke in score.values():
        by_limb[stroke.limb].append((performance_tick(stroke), stroke))

    result = []
    minimum_recovery = 184          # 89.84 ms at this tempo

    for limb in LIMBS:
        ordered = sorted(by_limb[limb], key=lambda item: (
            item[0], -item[1].priority, -item[1].velocity))
        accepted = []
        for item in ordered:
            tick, stroke = item
            if accepted and tick - accepted[-1][0] < minimum_recovery:
                previous = accepted[-1][1]
                old_rank = (previous.priority, previous.velocity)
                new_rank = (stroke.priority, stroke.velocity)
                if new_rank > old_rank:
                    accepted[-1] = item
            else:
                accepted.append(item)
        assert all(accepted[i][0] - accepted[i - 1][0] >= minimum_recovery
                   for i in range(1, len(accepted)))
        result.extend(accepted)

    result.sort(key=lambda item: (item[0], item[1].limb, item[1].note))

    # Verify the explicit two-hand/two-foot contract at every sounding onset.
    simultaneous = defaultdict(list)
    for tick, stroke in result:
        simultaneous[tick].append(stroke)
    for strokes in simultaneous.values():
        assert len({s.limb for s in strokes}) == len(strokes)
        assert sum(s.limb in HANDS for s in strokes) <= 2
        assert sum(s.limb not in HANDS for s in strokes) <= 2
    return result


def write_midi():
    midi = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    conductor = mido.MidiTrack()
    drums = mido.MidiTrack()
    midi.tracks.extend((conductor, drums))

    conductor.append(mido.MetaMessage(
        "track_name", name="Small Hours / a solo for four limbs", time=0))
    conductor.append(mido.MetaMessage("set_tempo", tempo=TEMPO, time=0))
    conductor.append(mido.MetaMessage(
        "time_signature", numerator=4, denominator=4,
        clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    conductor.append(mido.MetaMessage(
        "text", text="64 bars; 128 BPM; swung sixteenths; exactly 120 seconds",
        time=0))

    sections = (
        (0, "I - Invitation"),
        (8, "II - The pocket"),
        (16, "III - Around the drums"),
        (24, "IV - Wood and skin"),
        (32, "V - Small hours"),
        (40, "VI - Crossing the barline"),
        (48, "VII - Home, louder"),
        (56, "VIII - Ascent and farewell"),
        (62, "Coda"),
    )
    previous = 0
    for bar, title in sections:
        tick = bar * BAR
        conductor.append(mido.MetaMessage(
            "marker", text=title, time=tick - previous))
        previous = tick
    conductor.append(mido.MetaMessage("end_of_track", time=END - previous))

    events = []
    serial = 0

    def event(tick, order, message):
        nonlocal serial
        events.append((tick, order, serial, message))
        serial += 1

    event(0, -10, mido.MetaMessage(
        "track_name", name="One drummer - GM percussion channel 10"))
    event(0, -9, mido.Message(
        "sysex", data=(0x7E, 0x7F, 0x09, 0x01)))  # General MIDI System On
    for control, value in ((7, 105), (11, 127)):
        event(0, -8, mido.Message(
            "control_change", channel=CHANNEL, control=control, value=value))

    performance = playable_performance()

    # Avoid a preceding note-off cutting a newer attack of the same pitch.
    next_onset = {}
    release = {}
    for index in range(len(performance) - 1, -1, -1):
        tick, stroke = performance[index]
        if stroke.note in (CRASH, CHINA, SPLASH):
            gate = 3400
        elif stroke.note in (RIDE, BELL):
            gate = 1400
        elif stroke.note == OPEN:
            gate = 720
        elif stroke.note in (HAT, PEDAL):
            gate = 80
        else:
            gate = 160
        off = min(END, tick + gate)
        if stroke.note in next_onset:
            off = min(off, next_onset[stroke.note] - 1)
        release[index] = max(tick + 1, off)
        next_onset[stroke.note] = tick

    for index, (tick, stroke) in enumerate(performance):
        event(tick, 1, mido.Message(
            "note_on", channel=CHANNEL, note=stroke.note,
            velocity=stroke.velocity))
        event(release[index], 0, mido.Message(
            "note_off", channel=CHANNEL, note=stroke.note, velocity=0))

    event(END, 10, mido.MetaMessage("end_of_track"))
    events.sort(key=lambda e: (e[0], e[1], e[2]))

    previous = 0
    for tick, _, _, message in events:
        drums.append(message.copy(time=tick - previous))
        previous = tick

    # All time, including the final breath, is represented in the file.
    assert END * TEMPO == 120 * 1_000_000 * PPQ
    midi.save("solo.mid")


if __name__ == "__main__":
    write_midi()
