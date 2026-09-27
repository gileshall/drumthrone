#!/usr/bin/env python3
"""Two-minute swing drum solo for General MIDI channel 10.

54 bars at 108 BPM = 120 seconds exactly. Swing is a fixed triplet grid
(not random jitter): ride lays back, kick sits slightly ahead, ghosts sit
late of the accent. Motifs are stated, varied, and brought back.
"""

from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

TICKS = 480
BPM = 108
BARS = 54
CHANNEL = 9  # GM percussion channel 10
SWING_OFF = 160  # 2/3 of an eighth-note (triplet swing)
STRAIGHT_OFF = 120
CLUSTER = 18  # ~20 ms: strikes this close count as the same instant

# Limb families. One drummer: two hands, two feet.
FEET = {35, 36, 44}

# Nudges (ticks). Consistent within a role, never random.
LAY_BACK = 12
KICK_PUSH = -6
SNARE_POCKET = 4
GHOST_LATE = 10
AHEAD = -28

events = []  # (tick, note, vel, dur, priority, limb)


def clamp_vel(v):
    return max(1, min(127, int(v)))


def pos_ticks(bar, sixteenth, swing=True, nudge=0):
    while sixteenth >= 16:
        sixteenth -= 16
        bar += 1
    while sixteenth < 0:
        sixteenth += 16
        bar -= 1
    if bar < 0 or bar >= BARS:
        return None
    eighth = sixteenth // 2
    off = sixteenth % 2
    base = bar * 4 * TICKS + eighth * (TICKS // 2)
    if off:
        base += SWING_OFF if swing else STRAIGHT_OFF
    return max(0, base + int(nudge))


def add(bar, sixteenth, note, vel, swing=True, nudge=0, dur=None, priority=50):
    tick = pos_ticks(bar, sixteenth, swing, nudge)
    if tick is None:
        return
    if not 35 <= note <= 81:
        return
    if dur is None:
        if note in (49, 51, 52, 53, 55, 57, 59, 81):
            dur = 720
        elif note in (46, 42, 44):
            dur = 160
        else:
            dur = 70
    limb = "F" if note in FEET else "H"
    events.append((tick, note, clamp_vel(vel), dur, int(priority), limb))


def resolve(raw):
    """Drop strikes that would need a third hand or third foot at one instant."""
    raw = sorted(raw, key=lambda e: (e[0], -e[4], e[1]))
    accepted = []
    i = 0
    n = len(raw)
    while i < n:
        t0 = raw[i][0]
        j = i
        cluster = []
        while j < n and raw[j][0] - t0 <= CLUSTER:
            cluster.append(raw[j])
            j += 1
        cluster.sort(key=lambda e: (-e[4], e[1], e[0]))
        hands = feet = 0
        used = set()
        for e in cluster:
            note = e[1]
            if note in used:
                continue
            if e[5] == "H":
                if hands >= 2:
                    continue
                hands += 1
            else:
                if feet >= 2:
                    continue
                feet += 1
            used.add(note)
            accepted.append(e)
        i = j
    return accepted


def phrase_scale(bar):
    """Long-form dynamic arc: statement, build, release, peak, cadence."""
    if bar < 4:
        return 0.72
    if bar < 8:
        return 0.82
    if bar < 16:
        return 0.88
    if bar < 24:
        return 0.92 + 0.08 * ((bar - 16) / 8)
    if bar < 30:
        return 0.48
    if bar < 40:
        return 0.78 + 0.18 * ((bar - 30) / 10)
    if bar < 46:
        return 1.05
    if bar < 50:
        return 0.7
    if bar < 52:
        return 0.55
    return 1.0


def v(bar, base):
    return clamp_vel(base * phrase_scale(bar))


# --- Motif A: ride ostinato, backbeat, ghost strand -------------------------
# Hook: ride bell on the "&" of 2 and the "&" of 4 (sixteenths 6 and 14).

KICKS = {
    "a": (0, 8),
    "b": (0, 6, 10),
    "c": (0, 8, 11),
    "d": (0, 10),
    "e": (0, 3, 8, 14),
    "f": (0, 7, 10),  # groups of 3 against the bar
}


def motif_a(bar, kick="a", push_snare=False, bell=True, hat_instead=False,
            ghost="sparse", swing=True, ride_nudge=LAY_BACK, hat_nudge=0,
            skip_from=16, extra_crash=False):
    sc = phrase_scale(bar)
    cym = 42 if hat_instead else 51
    nudge_c = hat_nudge if hat_instead else ride_nudge
    for s in range(0, skip_from, 2):
        accent = s in (0, 8)
        secondary = s in (4, 12)
        base = 96 if accent else (84 if secondary else 70)
        if s == 0 and bar % 4 == 0:
            base += 8
        add(bar, s, cym, base * sc, swing=swing, nudge=nudge_c, priority=72)
    if bell and not hat_instead:
        add(bar, 6, 53, 88 * sc, swing=swing, nudge=ride_nudge, priority=78)
        add(bar, 14, 53, 80 * sc, swing=swing, nudge=ride_nudge, priority=74)
    for s in KICKS[kick]:
        if s >= skip_from:
            continue
        add(bar, s, 36, (104 if s == 0 else 86) * sc, swing=swing,
            nudge=KICK_PUSH, priority=88 if s == 0 else 76)
    snare_nudge = AHEAD if push_snare else SNARE_POCKET
    if 4 < skip_from:
        add(bar, 4, 38, 114 * sc, swing=swing, nudge=snare_nudge, priority=96)
    if 12 < skip_from:
        add(bar, 12, 38, 108 * sc, swing=swing, nudge=snare_nudge, priority=96)
    # Foot chick under the backbeat, never a third hand.
    if 4 < skip_from:
        add(bar, 4, 44, 42 * sc, swing=swing, nudge=0, priority=24)
    if 12 < skip_from:
        add(bar, 12, 44, 38 * sc, swing=swing, nudge=0, priority=24)
    if ghost == "sparse":
        ghosts = (3, 11, 15)
    elif ghost == "dense":
        ghosts = (3, 7, 9, 11, 15)
    elif ghost == "off":
        ghosts = ()
    else:
        ghosts = (3, 7, 11, 15)
    for s in ghosts:
        if s >= skip_from:
            continue
        add(bar, s, 38, (34 + (s % 3) * 3) * sc, swing=swing,
            nudge=GHOST_LATE, priority=36)
    if extra_crash and skip_from > 0:
        add(bar, 0, 49, 112 * sc, swing=swing, nudge=0, priority=92)


# --- Motif B: tom call, then inverted answer --------------------------------

TOM_CALL = (
    (0, 41, 102, 80),
    (2, 43, 78, 60),
    (3, 45, 90, 64),
    (4, 38, 114, 96),
    (6, 47, 86, 62),
    (7, 50, 98, 70),
    (10, 50, 84, 60),
    (11, 47, 76, 58),
    (12, 38, 110, 96),
    (14, 43, 88, 62),
    (15, 41, 100, 72),
)
INVERT = {41: 50, 43: 48, 45: 47, 47: 45, 48: 43, 50: 41, 38: 38, 36: 36}


def motif_b(bar, invert=False, swing=True, scale=1.0):
    sc = phrase_scale(bar) * scale
    for s, note, vel, pri in TOM_CALL:
        n = INVERT[note] if invert else note
        add(bar, s, n, vel * sc, swing=swing, nudge=SNARE_POCKET if note == 38 else 0,
            priority=pri)
    add(bar, 0, 36, 100 * sc, swing=swing, nudge=KICK_PUSH, priority=86)
    add(bar, 8, 36, 90 * sc, swing=swing, nudge=KICK_PUSH, priority=80)
    add(bar, 4, 44, 36 * sc, swing=swing, priority=22)
    add(bar, 12, 44, 34 * sc, swing=swing, priority=22)


# --- Motif L: single-stroke linear line (one hand at a time) + kick --------

LINE_UP = (38, 38, 50, 48, 45, 45, 47, 50, 38, 37, 41, 43, 45, 47, 48, 50)
LINE_DN = (50, 50, 48, 47, 45, 45, 43, 41, 38, 37, 43, 45, 47, 48, 50, 38)


def motif_l(bar, invert=False, start=0, flam=False, kick="f"):
    sc = phrase_scale(bar)
    notes = LINE_DN if invert else LINE_UP
    accents = {0, 4, 8, 12}
    ghosts = {1, 5, 9}
    for i, note in enumerate(notes):
        if i < start:
            continue
        if i in ghosts:
            vel, pri, nudge = 36, 34, GHOST_LATE
        elif i in accents:
            vel, pri, nudge = 112, 94, 0
        else:
            vel, pri, nudge = 78, 55, 0
        add(bar, i, note, vel * sc, nudge=nudge, priority=pri)
        if flam and i in accents:
            # Grace rim just before the accent: sequential, not a third hand.
            add(bar, i, 37, 64 * sc, nudge=-24, priority=48)
    for s in KICKS[kick]:
        if s < start:
            continue
        add(bar, s, 36, (100 if s == 0 else 84) * sc, nudge=KICK_PUSH,
            priority=84 if s == 0 else 70)
    add(bar, 4, 44, 36 * sc, priority=20)
    add(bar, 12, 44, 34 * sc, priority=20)


def bell_against_three(bar, origin):
    """Dotted-quarter bell (3 over 4) — development of the motif-A bell hook."""
    sc = phrase_scale(bar)
    base = (bar - origin) * 8
    for eighth in range(8):
        if (base + eighth) % 3 == 0:
            add(bar, eighth * 2, 53, 96 * sc, nudge=LAY_BACK, priority=76)


def fill_into(bar, kind):
    sc = phrase_scale(bar)
    if kind == "short":
        spec = ((12, 47, 88), (13, 47, 78), (14, 45, 100), (15, 43, 112))
    elif kind == "long":
        spec = (
            (8, 50, 80), (9, 48, 84), (10, 47, 90), (11, 45, 96),
            (12, 43, 102), (13, 41, 108), (14, 41, 114), (15, 38, 120),
        )
    elif kind == "up":
        spec = (
            (8, 41, 86), (9, 43, 90), (10, 45, 94), (11, 47, 100),
            (12, 48, 106), (13, 50, 112), (14, 50, 118), (15, 49, 122),
        )
    elif kind == "straight_roll":
        # Straightens on purpose: the fill leaves the swing grid, then we return.
        for s in range(8, 16):
            note = 38 if s < 12 else (47 if s < 14 else 50)
            add(bar, s, note, (70 + (s - 8) * 7) * sc, swing=False, priority=80)
        add(bar, 15, 49, 120 * sc, swing=False, priority=90)
        return
    else:
        return
    swing = kind != "straight_roll"
    for s, note, vel in spec:
        add(bar, s, note, vel * sc, swing=swing, priority=84)


def color_break():
    """Half-time release. One hand on metal or clave, one on conga, feet on time."""
    # Son clave 3-2 across bars 27-28, in straight sixteenths.
    clave = {
        27: (0, 6, 12),
        28: (4, 8),
    }
    for bar in range(24, 30):
        sc = phrase_scale(bar)
        add(bar, 0, 36, 78 * sc, swing=False, nudge=KICK_PUSH, priority=86)
        add(bar, 8, 36, 64 * sc, swing=False, nudge=KICK_PUSH, priority=70)
        # Half-time backbeat on 3.
        add(bar, 8, 37, 96 * sc, swing=False, priority=90)
        add(bar, 8, 44, 40 * sc, swing=False, priority=24)
        if bar < 27:
            for s, vel in ((0, 72), (4, 52), (8, 64), (12, 50)):
                add(bar, s, 56, vel * sc, swing=False, priority=60)
            # Conga tumbao in the other hand (shares quarters with cowbell: 2 hands).
            add(bar, 0, 62, 58 * sc, swing=False, priority=50)
            add(bar, 3, 62, 48 * sc, swing=False, priority=40)
            add(bar, 6, 63, 92 * sc, swing=False, priority=68)
            add(bar, 10, 64, 80 * sc, swing=False, priority=62)
            add(bar, 14, 63, 84 * sc, swing=False, priority=64)
            if bar == 26:
                add(bar, 12, 69, 50 * sc, swing=False, priority=30)
        elif bar in clave:
            for s in clave[bar]:
                add(bar, s, 75, 100 * sc, swing=False, priority=78)
            add(bar, 2, 62, 50 * sc, swing=False, priority=42)
            add(bar, 7, 63, 86 * sc, swing=False, priority=64)
            add(bar, 11, 64, 74 * sc, swing=False, priority=58)
            add(bar, 15, 62, 46 * sc, swing=False, priority=40)
        else:
            # Bar 29: leave the percussion episode, ramp back toward the kit.
            add(bar, 0, 76, 70 * sc, swing=False, priority=55)
            add(bar, 4, 77, 64 * sc, swing=False, priority=50)
            add(bar, 8, 76, 80 * sc, swing=False, priority=55)
            add(bar, 10, 45, 90 * sc, swing=False, priority=70)
            add(bar, 12, 47, 100 * sc, swing=False, priority=74)
            add(bar, 13, 48, 104 * sc, swing=False, priority=74)
            add(bar, 14, 50, 112 * sc, swing=False, priority=80)
            add(bar, 15, 58, 96 * sc, swing=False, priority=66)


def coda():
    # Fragment of motif A — space is the variation.
    for bar, kick in ((46, "d"), (47, "a")):
        motif_a(bar, kick=kick, bell=(bar == 46), ghost="sparse", skip_from=8)
        add(bar, 10, 50, v(bar, 70), priority=50)
        add(bar, 12, 47, v(bar, 78), priority=54)
        add(bar, 14, 43, v(bar, 86), priority=58)
    # Quote of motif B, quieter, as a memory of the tom conversation.
    motif_b(48, invert=False, scale=0.85)
    motif_b(49, invert=True, scale=0.8)
    # Near-silence: heartbeat kicks, one side-stick, then nothing.
    add(50, 0, 36, 60, nudge=KICK_PUSH, priority=80)
    add(50, 8, 36, 48, nudge=KICK_PUSH, priority=70)
    add(50, 8, 37, 42, priority=40)
    add(50, 0, 80, 36, priority=30)  # muted triangle, a breath
    # Crescendo roll, straight sixteenths, moving up the toms.
    for s in range(16):
        if s < 6:
            note = 38
        elif s < 10:
            note = 45
        elif s < 13:
            note = 47
        else:
            note = 50
        add(51, s, note, 36 + s * 5, swing=False, priority=70)
    add(51, 0, 36, 70, swing=False, nudge=KICK_PUSH, priority=80)
    add(51, 8, 36, 90, swing=False, nudge=KICK_PUSH, priority=82)
    # Penultimate bar: motif A at full voice, crash included, no fill clutter.
    motif_a(52, kick="b", bell=True, ghost="mid", extra_crash=True)
    add(52, 0, 52, v(52, 100), priority=88)  # china with the crash — wait, that's 3 hands
    # china would be a third hand with ride+crash. Don't add it; crash already marked.
    # Final bar: one strike. Kick, snare, crash, hat chick — two feet, two hands.
    add(53, 0, 36, 120, nudge=0, priority=100, dur=960)
    add(53, 0, 38, 122, nudge=0, priority=100, dur=480)
    add(53, 0, 49, 124, nudge=0, priority=99, dur=1440)
    add(53, 0, 44, 70, nudge=0, priority=40, dur=200)
    # A quiet open-triangle afterbeat, after the hands are free.
    add(53, 6, 81, 42, nudge=LAY_BACK, priority=30, dur=960)


def compose():
    # Bars 0-3: motif A stated, medium, ride laid back. Kick pattern "a".
    for bar in range(0, 4):
        motif_a(bar, kick="a", bell=True, ghost="sparse")

    # Bars 4-7: variation — denser ghosts, kick develops, one pushed backbeat.
    for bar, kick in ((4, "a"), (5, "b"), (6, "b"), (7, "a")):
        motif_a(
            bar,
            kick=kick,
            push_snare=(bar == 6),
            bell=True,
            ghost="dense" if bar in (5, 6) else "mid",
            skip_from=12 if bar == 7 else 16,
        )
    fill_into(7, "short")

    # Bars 8-11: motif B call / inverted answer / call displaced in shape / fill.
    motif_b(8, invert=False)
    motif_b(9, invert=True)
    motif_b(10, invert=False)
    motif_a(11, kick="d", bell=False, ghost="sparse", skip_from=8)
    fill_into(11, "long")

    # Bars 12-15: motif A returns (recap 1), bell hook intact, new kick "c".
    for bar, kick in ((12, "a"), (13, "c"), (14, "b"), (15, "e")):
        motif_a(
            bar,
            kick=kick,
            bell=True,
            ghost="mid",
            extra_crash=(bar == 12),
            skip_from=8 if bar == 15 else 16,
        )
    fill_into(15, "up")

    # Bars 16-23: same rhythmic motif, hats instead of ride, time pushed ahead.
    # Density grows; bar 22 restates the pushed-snare variation from bar 6.
    for bar in range(16, 24):
        kick = ("a", "b", "c", "e", "b", "f", "b", "a")[bar - 16]
        motif_a(
            bar,
            kick=kick,
            push_snare=(bar == 22),
            bell=False,
            hat_instead=True,
            ghost="dense" if bar >= 19 else "mid",
            ride_nudge=0,
            hat_nudge=AHEAD // 2,
            skip_from=8 if bar == 23 else 16,
            extra_crash=(bar in (16, 20)),
        )
        # Open-hat barks on the hook sixteenths (where the bell used to be).
        if bar != 23:
            add(bar, 6, 46, v(bar, 90), nudge=AHEAD // 2, priority=68)
            add(bar, 14, 46, v(bar, 84), nudge=AHEAD // 2, priority=64)
    fill_into(23, "straight_roll")
    add(23, 0, 57, v(23, 110), priority=90)  # second crash on the downbeat only

    # Bars 24-29: release. Percussion, half-time, straight feel.
    color_break()

    # Bars 30-33: motif A returns softly (the release resolves), then opens up.
    for bar, kick, g in ((30, "a", "sparse"), (31, "a", "mid"),
                         (32, "b", "mid"), (33, "c", "dense")):
        motif_a(bar, kick=kick, bell=True, ghost=g, extra_crash=(bar == 32))

    # Bars 34-39: linear solo. Motif L stated, inverted, flammed, then grouped in 3s.
    motif_l(34, invert=False, flam=False, kick="f")
    motif_l(35, invert=True, flam=False, kick="f")
    motif_l(36, invert=False, flam=True, kick="a")
    motif_l(37, invert=True, flam=True, start=2, kick="d")
    # 38-39: bell in 3-over-4 over a simplified snare/kick — motif A hook stretched.
    for bar in (38, 39):
        bell_against_three(bar, 38)
        add(bar, 4, 38, v(bar, 112), nudge=SNARE_POCKET, priority=95)
        add(bar, 12, 38, v(bar, 108), nudge=SNARE_POCKET, priority=95)
        add(bar, 0, 36, v(bar, 100), nudge=KICK_PUSH, priority=86)
        add(bar, 10, 36, v(bar, 88), nudge=KICK_PUSH, priority=74)
        add(bar, 3, 38, v(bar, 36), nudge=GHOST_LATE, priority=32)
        add(bar, 7, 38, v(bar, 34), nudge=GHOST_LATE, priority=32)
        add(bar, 11, 38, v(bar, 38), nudge=GHOST_LATE, priority=32)
        add(bar, 15, 38, v(bar, 32), nudge=GHOST_LATE, priority=32)
        add(bar, 4, 44, v(bar, 40), priority=22)
        add(bar, 12, 44, v(bar, 36), priority=22)

    # Bars 40-45: climax. Motif A forte, push-variation recalled, china downbeats
    # only when the ride hand is free (china replaces ride on beat 1).
    for bar, kick in ((40, "b"), (41, "e"), (42, "b"), (43, "f"), (44, "c"), (45, "a")):
        motif_a(
            bar,
            kick=kick,
            push_snare=(bar == 42),
            bell=True,
            ghost="dense",
            extra_crash=(bar in (40, 44)),
            skip_from=8 if bar == 45 else 16,
        )
        if bar in (40, 44):
            # Replace nothing: crash already added. Splash as a late tag on beat 4
            # of the non-fill bars, one hand after the ride eighth.
            pass
        if bar in (41, 43):
            add(bar, 14, 55, v(bar, 70), priority=40)
    fill_into(45, "long")
    add(45, 0, 52, v(45, 114), priority=93)

    coda()


def render():
    compose()
    # The china on bar 52 was intentionally not added (would be a third hand
    # beside crash + ride). Bar 45 beat 1 is crash-free in motif_a except the
    # explicit china, and ride is also there — drop china if the resolver must,
    # by giving ride higher priority already (72 vs 93). China wins and ride
    # drops: one hand on china, other free for a floor-tom punch.
    add(45, 0, 41, v(45, 100), priority=70)

    accepted = resolve(events)
    timeline = []
    for tick, note, vel, dur, _pri, _limb in accepted:
        timeline.append((tick, 1, note, vel))
        timeline.append((tick + dur, 0, note, 0))
    timeline.sort(key=lambda item: (item[0], item[1], item[2]))

    mid = MidiFile(type=1, ticks_per_beat=TICKS)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("track_name", name="Drum Solo", time=0))
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(BPM), time=0))
    track.append(MetaMessage(
        "time_signature",
        numerator=4,
        denominator=4,
        clocks_per_click=24,
        notated_32nd_notes_per_beat=8,
        time=0,
    ))
    track.append(Message("control_change", channel=CHANNEL, control=7, value=127, time=0))

    last = 0
    for tick, kind, note, vel in timeline:
        delta = tick - last
        last = tick
        track.append(Message(
            "note_on",
            channel=CHANNEL,
            note=note,
            velocity=vel if kind == 1 else 0,
            time=delta,
        ))
    end_tick = BARS * 4 * TICKS
    track.append(MetaMessage("end_of_track", time=max(0, end_tick - last)))
    mid.save("solo.mid")


if __name__ == "__main__":
    render()
