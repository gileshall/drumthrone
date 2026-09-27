#!/usr/bin/env python3
"""A two-minute, swung drum solo for General MIDI channel 10."""

from collections import defaultdict

import mido


BPM = 104
TICKS_PER_BEAT = 960
BAR_TICKS = 4 * TICKS_PER_BEAT
BAR_COUNT = 52                 # 208 beats at 104 BPM = 120 seconds
END_TICK = BAR_COUNT * BAR_TICKS
DRUM_CHANNEL = 9               # MIDI channels are numbered from zero.

# Each beat has a 60/40 swung eighth note. The intervening sixteenths
# follow the same shape; timing is deliberate rather than randomized.
SIXTEENTH_POSITIONS = (0, 288, 576, 768)

# Phrase-level dynamics. Quiet passages retain audible ghost notes.
GAINS = {}
for first_bar, values in (
    (0, (-12, -10, -6, -3)),
    (4, (0, -2, -1, 2, 3, -2, 1, 4)),
    (12, (-3, -1, 0, 2, 1, -3, 2, 4)),
    (20, (-13, -15, -12, -14, -10, -8, -12, -5)),
    (28, (-9, -7, -5, -2, 0, 1, 3, 5)),
    (36, (5, 3, 5, 7, 8, 5, 7, 9)),
    (44, (2, 0, -2, 1, -5, -8, -3, 0)),
):
    for index, gain in enumerate(values):
        GAINS[first_bar + index] = gain
assert len(GAINS) == BAR_COUNT

# Durations are gates, not substitutes for the synthesizer's drum envelopes.
DURATIONS = {
    35: .16, 36: .16, 37: .15, 38: .18,
    41: .27, 42: .10, 43: .26, 44: .10, 45: .24,
    46: .56, 47: .23, 48: .23, 49: 2.10, 50: .23,
    51: .39, 52: 1.35, 53: .36, 55: .78, 56: .23,
    57: 2.05, 60: .22, 61: .24, 62: .22, 63: .25,
    64: .26, 65: .27, 66: .28, 67: .18, 68: .18,
    75: .11, 76: .12,
}

# R plays hats, ride, cymbals, tom melodies, and mounted percussion.
# L plays snare, rim, and ghost notes. K and P are the two feet.
class DrumScore:
    def __init__(self):
        self.hits = []

    @staticmethod
    def feel(bar, limb, note, raw_velocity):
        if bar < 12:
            kick, snare, ghost, right, pedal = -9, 24, 8, -4, 1
        elif bar < 20:
            kick, snare, ghost, right, pedal = -11, 13, 6, -5, 2
        elif bar < 28:
            kick, snare, ghost, right, pedal = -5, 32, 11, 4, 4
        elif bar < 36:
            kick, snare, ghost, right, pedal = (
                -12, 13 - 3 * (bar - 28), 5, -7, 0
            )
        elif bar < 44:
            kick, snare, ghost, right, pedal = -15, -9, 1, -9, -2
        else:
            kick, snare, ghost, right, pedal = -9, 24, 8, -5, 1

        if limb == "K":
            return kick
        if limb == "P":
            return pedal
        if limb == "L" and note in (37, 38, 39, 40):
            return ghost if raw_velocity < 60 else snare
        return right

    def hit(self, bar, step, spec, limb):
        # A spec is (GM note, velocity[, explicit tick offset[, gate in beats]]).
        assert 0 <= bar < BAR_COUNT and isinstance(step, int) and 0 <= step < 16
        note, raw_velocity = spec[:2]
        assert 35 <= note <= 81 and 1 <= raw_velocity <= 127

        offset = (
            spec[2] if len(spec) > 2
            else self.feel(bar, limb, note, raw_velocity)
        )
        phase = (step // 4) * TICKS_PER_BEAT
        phase += SIXTEENTH_POSITIONS[step % 4]
        start = max(0, bar * BAR_TICKS + phase + offset)

        gain = GAINS[bar]
        if limb == "L" and note in (37, 38, 39, 40) and raw_velocity < 60:
            gain = round(gain * .45)
        elif limb == "P":
            gain = round(gain * .6)
        velocity = max(1, min(126, raw_velocity + gain))

        gate = spec[3] if len(spec) > 3 else DURATIONS.get(note, .20)
        if note == 38 and raw_velocity < 60 and len(spec) <= 3:
            gate = .105
        end = start + max(20, round(gate * TICKS_PER_BEAT))
        assert end <= END_TICK
        self.hits.append((start, end, note, velocity, limb))

    def bar(self, number, k=None, l=None, r=None, p=None, bass=36):
        for step, value in (k or {}).items():
            self.hit(number, step,
                     (bass, value) if isinstance(value, int) else value, "K")
        for step, spec in (l or {}).items():
            self.hit(number, step, spec, "L")
        for step, spec in (r or {}).items():
            self.hit(number, step, spec, "R")
        for step, value in (p or {}).items():
            self.hit(number, step,
                     (44, value) if isinstance(value, int) else value, "P")

    def validate(self):
        # Each limb has only one instrument to strike at a time. Check even
        # the quick flams and fills for plausible successive strokes.
        by_limb = defaultdict(list)
        at_tick = defaultdict(list)
        for start, _, _, _, limb in self.hits:
            by_limb[limb].append(start)
            at_tick[start].append(limb)

        for limb, starts in by_limb.items():
            starts.sort()
            minimum = 76 if limb in ("L", "R") else 95
            for earlier, later in zip(starts, starts[1:]):
                if later - earlier < minimum:
                    raise ValueError(f"Two strokes too close for limb {limb}")

        for limbs in at_tick.values():
            if len(limbs) != len(set(limbs)):
                raise ValueError("A limb is double-booked")
            if sum(limb in ("L", "R") for limb in limbs) > 2:
                raise ValueError("More than two hands")
            if sum(limb in ("K", "P") for limb in limbs) > 2:
                raise ValueError("More than two feet")


HATS_8 = {
    0: (42, 63), 2: (42, 44), 4: (42, 60), 6: (42, 47),
    8: (42, 65), 10: (42, 44), 12: (42, 59), 14: (42, 50),
}
HATS_16 = {
    0: (42, 75), 1: (42, 40), 2: (42, 59), 3: (42, 43),
    4: (42, 71), 5: (42, 41), 6: (42, 61), 7: (42, 43),
    8: (42, 76), 9: (42, 41), 10: (42, 61), 11: (42, 43),
    12: (42, 72), 13: (42, 42), 14: (42, 61), 15: (42, 42),
}


def theme(answer=False):
    """The recurring two-bar idea: a syncopated kick and ghost-to-backbeat."""
    if answer:
        kick = {0: 101, 6: 86, 8: 98, 11: 75, 14: 87}
        left = {
            3: (38, 32), 4: (38, 109), 7: (38, 31),
            10: (38, 35), 12: (38, 115), 15: (38, 33),
        }
    else:
        kick = {0: 104, 3: 77, 6: 89, 8: 98, 14: 85}
        left = {
            2: (38, 33), 4: (38, 109), 10: (38, 36),
            12: (38, 115), 15: (38, 33),
        }
    return kick, left, dict(HATS_8)


def ride_answer(pulled=False):
    kick = {0: 101, 3: 75, 6: 87, 8: 98, 14: 85}
    left = {
        2: (38, 33), 4: (38, 108), 7: (38, 32),
        12: (38, 113), 15: (38, 34),
    }
    right = {
        0: (53, 79), 2: (51, 52), 4: (51, 67), 6: (51, 54),
        8: (53, 80), 10: (51, 51), 12: (51, 65), 14: (51, 56),
    }
    if pulled:
        left.pop(12)
        left[11] = (38, 112)    # Anticipate beat four.
        kick[12] = 82
        right[14] = (56, 75)
    return kick, left, right


def peak_theme(answer=False):
    kick = {0: 108, 3: 82, 6: 95, 8: 105, 11: 80, 14: 91}
    left = {
        3: (38, 39), 4: (38, 114), 7: (38, 39),
        10: (38, 40), 12: (38, 119), 15: (38, 39),
    }
    right = dict(HATS_16)
    if answer:
        kick.pop(3)
        left.pop(3)
        left[2] = (38, 38)
        right[14] = (46, 78)
        right.pop(15)           # Let the open hat lead into the next bar.
    return kick, left, right


def compose():
    s = DrumScore()

    # 0-3: space, cross-stick, then the first full backbeat and tom pickup.
    s.bar(0,
          k={0: 88, 8: 81, 14: 74},
          l={4: (37, 69), 12: (37, 75)},
          r={2: (42, 51), 6: (42, 45),
             10: (42, 53), 14: (46, 64)},
          p={4: 49, 12: 53})
    s.bar(1,
          k={0: 92, 3: 69, 8: 89, 14: 78},
          l={4: (37, 75), 10: (38, 35),
             12: (37, 81), 15: (38, 34)},
          r=dict(HATS_8))
    s.bar(2,
          k={0: 96, 3: 73, 6: 83, 8: 92, 14: 84},
          l={2: (38, 37), 4: (38, 98), 10: (38, 38),
             12: (38, 106), 15: (38, 36)},
          r={**HATS_8, 14: (46, 73)})
    s.bar(3,
          k={0: 99, 6: 84, 8: 94, 14: 95},
          l={2: (38, 37), 4: (38, 104), 9: (38, 42),
             11: (38, 69), 12: (38, 112), 15: (38, 96)},
          r={0: HATS_8[0], 2: HATS_8[2], 4: HATS_8[4],
             6: HATS_8[6], 8: HATS_8[8], 10: (50, 87),
             12: (48, 90), 14: (45, 96)})

    # 4-11: state the hook, answer it, and make each fourth bar a fill.
    k, l, r = theme()
    r[0] = (49, 96)
    s.bar(4, k, l, r)

    k, l, r = theme(True)
    r[14] = (46, 76)
    s.bar(5, k, l, r)

    k, l, r = theme()
    k[11] = 73
    l[7] = (38, 32)
    s.bar(6, k, l, r)

    k, l, r = theme(True)
    r.update({10: (50, 86), 12: (48, 91),
              14: (47, 96), 15: (41, 94)})
    l[11] = (38, 66)
    l[15] = (38, 84)
    s.bar(7, k, l, r)

    k, l, r = theme()
    r[0] = (57, 97)
    s.bar(8, k, l, r)

    k, l, r = theme(True)
    k[3] = 73
    r[6] = (42, 55)
    r[14] = (46, 77)
    s.bar(9, k, l, r)

    k, l, r = theme()
    k[11] = 75
    r[6] = (53, 82)
    r[14] = (53, 84)
    s.bar(10, k, l, r)

    k, l, r = theme(True)
    k[3] = 76
    r.update({8: (50, 91), 10: (48, 93), 12: (45, 99),
              14: (41, 104), 15: (55, 81)})
    l.update({9: (38, 40), 11: (38, 78),
              13: (38, 41), 15: (38, 104)})
    s.bar(11, k, l, r)

    # 12-19: move the hook to ride and bell. The anticipated snare is
    # the answer; cowbell and timbales briefly color its syncopation.
    k, l, r = ride_answer()
    s.bar(12, k, l, r, p={4: 48, 12: 51})

    k, l, r = ride_answer(True)
    s.bar(13, k, l, r, p={4: 47, 12: 50})

    k, l, r = ride_answer()
    k[11] = 76
    r[0] = (51, 69)
    r[6] = (56, 77)
    r[14] = (56, 79)
    s.bar(14, k, l, r, p={4: 49, 12: 51})

    k, l, r = ride_answer(True)
    k[11] = 79
    k.pop(12)
    r.update({8: (50, 89), 10: (48, 92),
              12: (47, 97), 14: (41, 101)})
    l[13] = (38, 41)
    l[15] = (38, 101)
    s.bar(15, k, l, r, p={4: 50, 12: 53})

    k, l, r = ride_answer()
    r[0] = (49, 93)
    s.bar(16, k, l, r, p={4: 48, 12: 52})

    k, l, r = ride_answer(True)
    r[14] = (51, 59)
    s.bar(17, k, l, r, p={4: 48, 12: 50})

    k, l, r = ride_answer()
    k[11] = 78
    l.pop(2)
    l[3] = (38, 39)
    r[6] = (56, 80)
    r[14] = (56, 82)
    s.bar(18, k, l, r, p={4: 50, 12: 53})

    s.bar(19,
          k={0: 103, 3: 79, 6: 89, 8: 101, 14: 94},
          l={2: (38, 36), 4: (38, 111), 7: (38, 40),
             11: (38, 105), 13: (38, 78), 15: (38, 105)},
          r={0: (53, 83), 2: (51, 55), 4: (51, 69),
             6: (51, 55), 8: (50, 90), 10: (65, 92),
             12: (45, 97), 14: (66, 94)},
          p={4: 49, 12: 52})

    # 20-27: sudden half-time drop. The left foot keeps time while one
    # hand alternates cross-stick and snare and the other explores color.
    pulse = {0: 48, 4: 52, 8: 50, 12: 54}
    s.bar(20,
          k={0: 89, 6: 77, 10: 82},
          l={4: (37, 69), 7: (38, 42),
             8: (38, 101), 15: (38, 40)},
          r={0: (64, 74), 3: (62, 59), 6: (63, 69),
             11: (62, 57), 14: (64, 72)},
          p=pulse, bass=35)
    s.bar(21,
          k={0: 91, 6: 76, 10: 83, 14: 72},
          l={4: (37, 71), 7: (38, 42),
             8: (38, 102), 15: (38, 40)},
          r={0: (64, 74), 3: (75, 68), 6: (75, 74),
             11: (75, 67), 14: (64, 73)},
          p=pulse, bass=35)
    s.bar(22,
          k={0: 92, 6: 79, 8: 81, 14: 76},
          l={2: (38, 40), 4: (37, 71), 7: (38, 42),
             8: (38, 103), 11: (38, 40), 15: (38, 39)},
          r={0: (61, 73), 2: (60, 65), 6: (61, 71),
             10: (62, 63), 14: (64, 75)},
          p=pulse, bass=35)
    s.bar(23,
          k={0: 89, 6: 78, 10: 83},
          l={4: (37, 71), 7: (38, 41),
             8: (38, 100), 15: (38, 42)},
          r={0: (56, 72), 6: (56, 75), 10: (56, 72),
             14: (56, 81), 15: (76, 61)},
          p=pulse, bass=35)
    s.bar(24,
          k={0: 94, 6: 79, 10: 86, 14: 77},
          l={2: (38, 39), 4: (37, 71), 7: (38, 42),
             8: (38, 103), 10: (38, 40), 15: (38, 39)},
          r={0: (53, 77), 2: (51, 51), 6: (53, 79),
             8: (43, 81), 11: (45, 78), 14: (53, 82)},
          p=pulse)
    s.bar(25,
          k={0: 94, 6: 81, 10: 85, 14: 79},
          l={2: (38, 39), 4: (37, 72), 7: (38, 40),
             8: (38, 103), 11: (38, 42), 15: (38, 40)},
          r={0: (50, 77), 3: (47, 75), 6: (41, 85),
             11: (62, 62), 14: (56, 82)},
          p=pulse, bass=35)
    s.bar(26,
          k={0: 88, 10: 82},
          l={4: (37, 71), 8: (38, 94), 15: (38, 42)},
          r={2: (68, 67), 6: (67, 74), 14: (76, 66)},
          p={4: 49, 12: 53}, bass=35)
    s.bar(27,
          k={0: 99, 6: 83, 8: 92, 11: 75, 14: 88},
          l={2: (38, 39), 4: (37, 76), 7: (38, 40),
             8: (38, 104), 10: (38, 41), 12: (38, 109),
             15: (38, 84)},
          r={0: (64, 77), 3: (63, 72), 8: (50, 84),
             10: (48, 87), 12: (47, 91), 14: (41, 97)},
          p=pulse)

    # 28-35: the bass-drum motif becomes a descending tom melody;
    # eighths become sixteenths as the backbeat shifts from late to early.
    s.bar(28,
          k={0: 99, 3: 72, 6: 85, 8: 94, 14: 83},
          l={2: (38, 34), 4: (38, 102), 10: (38, 37),
             12: (38, 109), 15: (38, 35)},
          r={0: (50, 81), 3: (48, 73), 6: (47, 85),
             8: (50, 82), 11: (45, 87), 14: (41, 93)},
          p={4: 49, 12: 53})
    s.bar(29,
          k={0: 100, 6: 86, 8: 96, 11: 75, 14: 86},
          l={2: (38, 35), 4: (38, 103), 7: (38, 36),
             10: (38, 38), 12: (38, 110), 15: (38, 35)},
          r={0: (48, 82), 2: (50, 77), 6: (45, 87),
             8: (48, 84), 11: (47, 87), 14: (41, 96)},
          p={4: 50, 12: 54})

    k, l, r = theme()
    r.update({10: (50, 83), 12: (48, 89),
              14: (45, 94), 15: (41, 91)})
    s.bar(30, k, l, r)

    k, l, r = theme(True)
    r.update({9: (50, 79), 10: (48, 85), 11: (47, 89),
              12: (45, 92), 14: (41, 97), 15: (43, 90)})
    l[15] = (38, 87)
    s.bar(31, k, l, r)

    k, l, _ = theme()
    l[7] = (38, 36)
    s.bar(32, k, l, dict(HATS_16))

    k, l, _ = theme(True)
    k[3] = 76
    l[1] = (38, 32)
    r = dict(HATS_16)
    r[14] = (46, 76)
    r.pop(15)
    s.bar(33, k, l, r)

    k, l, _ = theme()
    k[11] = 79
    l.update({1: (38, 36), 7: (38, 38), 13: (38, 42)})
    r = {step: HATS_16[step] for step in range(9)}
    r.update({9: (50, 86), 10: (48, 90), 11: (47, 94),
              12: (45, 97), 13: (43, 94), 14: (41, 103),
              15: (43, 96)})
    s.bar(34, k, l, r)

    # The grace note and accented snare at step 12 are a two-hand flam.
    s.bar(35,
          k={0: 104, 3: 81, 6: 91, 8: 103, 11: 84, 14: 100},
          l={2: (38, 37), 4: (38, 110), 7: (38, 36),
             10: (38, 39), 12: (38, 49, -80, .045),
             13: (38, 79), 15: (38, 114)},
          r={0: (53, 88), 2: (51, 63), 4: (51, 76),
             6: (51, 65), 8: (50, 95), 9: (48, 90),
             10: (47, 94), 11: (45, 98),
             12: (38, 117, -9), 13: (45, 94),
             14: (41, 105), 15: (55, 88)},
          p={4: 52, 12: 56})

    # 36-43: peak. The opening motif returns at full force, interrupted
    # by ride space, a tom break, an anticipated backbeat, and stop-time.
    k, l, r = peak_theme()
    r[0] = (49, 106)
    s.bar(36, k, l, r)

    k, l, r = peak_theme(True)
    s.bar(37, k, l, r)

    k, l, _ = peak_theme()
    r = {0: (53, 89), 2: (51, 62), 4: (51, 74),
         6: (53, 87), 8: (51, 77), 10: (51, 63),
         12: (51, 75), 14: (53, 89)}
    s.bar(38, k, l, r, p={4: 52, 12: 56})

    s.bar(39,
          k={0: 109, 3: 83, 6: 97, 8: 107, 11: 83, 14: 94},
          l={2: (38, 39), 4: (38, 117), 7: (38, 42),
             9: (38, 65), 11: (38, 82), 12: (38, 119),
             15: (38, 116)},
          r={0: (53, 89), 2: (51, 66), 4: (51, 76),
             6: (51, 65), 8: (50, 100), 9: (48, 95),
             10: (47, 99), 11: (45, 102), 12: (43, 106),
             13: (41, 105), 14: (45, 107), 15: (41, 109)})

    k, l, r = peak_theme()
    r[0] = (57, 108)
    r[14] = (46, 82)
    r.pop(15)
    s.bar(40, k, l, r)

    k, l, r = peak_theme()
    l.pop(12)
    l[11] = (38, 118)
    l[13] = (37, 69)
    k[12] = 93
    s.bar(41, k, l, r)

    s.bar(42,
          k={0: 110, 4: 96, 8: 106, 12: 107, 14: 90},
          l={0: (38, 107), 4: (38, 118), 7: (38, 38),
             12: (38, 121), 15: (38, 46)},
          r={0: (52, 106), 2: (42, 46), 4: (42, 78),
             6: (42, 49), 8: (50, 103),
             12: (49, 101), 14: (42, 76)})

    s.bar(43,
          k={0: 110, 3: 85, 6: 98, 8: 108, 11: 87, 14: 100},
          l={2: (38, 42), 4: (38, 117), 7: (38, 53),
             9: (38, 78), 10: (38, 44), 11: (38, 86),
             12: (38, 48, -81, .04), 14: (38, 81),
             15: (38, 119)},
          r={0: (53, 91), 2: (51, 68), 4: (50, 103),
             5: (50, 89), 6: (48, 103), 7: (47, 96),
             8: (45, 108), 9: (43, 101), 10: (41, 111),
             11: (45, 103), 12: (38, 116, -10),
             13: (48, 101), 14: (41, 113), 15: (45, 103)})

    # 44-51: literal return of the theme, then take notes away. One
    # last recognizable turnaround resolves to a single four-limb hit.
    k, l, r = theme()
    r[0] = (49, 96)
    s.bar(44, k, l, r)

    k, l, r = theme(True)
    r[14] = (46, 76)
    s.bar(45, k, l, r)

    k, l, r = theme()
    k.pop(3)
    r[6] = (53, 77)
    s.bar(46, k, l, r)

    k, l, r = theme(True)
    r.update({10: (50, 82), 12: (48, 88), 14: (41, 94)})
    l[11] = (38, 64)
    l[15] = (38, 82)
    s.bar(47, k, l, r)

    k, l, r = theme()
    k.pop(3)
    k[14] = 76
    l.pop(15)
    l[4] = (38, 105)
    l[12] = (38, 108)
    r[14] = (46, 69)
    s.bar(48, k, l, r)

    s.bar(49,
          k={0: 94, 6: 76, 8: 86},
          l={4: (37, 76), 10: (38, 35),
             12: (38, 103), 15: (38, 35)},
          r={0: HATS_8[0], 2: HATS_8[2], 6: HATS_8[6],
             8: HATS_8[8], 10: HATS_8[10], 14: HATS_8[14]},
          p={4: 49, 12: 53})

    s.bar(50,
          k={0: 104, 3: 78, 6: 91, 8: 101,
             11: 85, 14: 102},
          l={2: (38, 38), 4: (38, 109), 9: (38, 39),
             11: (38, 74), 12: (38, 113), 14: (38, 64)},
          r={0: HATS_8[0], 2: HATS_8[2],
             4: HATS_8[4], 6: HATS_8[6], 8: HATS_8[8],
             10: (50, 88), 11: (48, 91), 12: (47, 95),
             13: (45, 97), 14: (41, 104), 15: (43, 97)})

    # Hold the last cymbal almost to the two-minute endpoint.
    s.bar(51,
          k={0: (36, 116, 0, .28)},
          l={0: (38, 125, 0, .25)},
          r={0: (49, 117, 0, 3.88)},
          p={0: (44, 61, 0, .14)})

    s.validate()
    return s


def write_midi(score):
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    conductor = mido.MidiTrack()
    midi.tracks.append(conductor)
    conductor.append(mido.MetaMessage(
        "track_name", name="Drum solo - form and tempo", time=0
    ))
    conductor.append(mido.MetaMessage(
        "set_tempo", tempo=mido.bpm2tempo(BPM), time=0
    ))
    conductor.append(mido.MetaMessage(
        "time_signature", numerator=4, denominator=4, time=0
    ))

    sections = (
        (0, "Intro: the question"),
        (4, "Theme: syncopated kick and ghost-to-backbeat"),
        (12, "Development: ride and anticipated snare"),
        (20, "Half-time: cross-stick and mounted percussion"),
        (28, "Rebuild: tom melody and rising subdivisions"),
        (36, "Peak: theme, variations and stop-time"),
        (44, "Reprise and final cadence"),
        (51, "Final hit"),
    )
    previous = 0
    for bar, label in sections:
        tick = bar * BAR_TICKS
        conductor.append(mido.MetaMessage(
            "marker", text=label, time=tick - previous
        ))
        previous = tick
    conductor.append(mido.MetaMessage(
        "end_of_track", time=END_TICK - previous
    ))

    drums = mido.MidiTrack()
    midi.tracks.append(drums)
    drums.append(mido.MetaMessage(
        "track_name", name="Solo drummer - GM channel 10", time=0
    ))

    events = []
    for sequence, (start, end, note, velocity, _) in enumerate(score.hits):
        events.append((
            start, 1, sequence,
            mido.Message("note_on", channel=DRUM_CHANNEL,
                         note=note, velocity=velocity),
        ))
        events.append((
            end, 0, sequence,
            mido.Message("note_off", channel=DRUM_CHANNEL,
                         note=note, velocity=0),
        ))

    previous = 0
    for tick, _, _, message in sorted(events, key=lambda item: item[:3]):
        drums.append(message.copy(time=tick - previous))
        previous = tick
    drums.append(mido.MetaMessage(
        "end_of_track", time=END_TICK - previous
    ))

    midi.save("solo.mid")


if __name__ == "__main__":
    write_midi(compose())
