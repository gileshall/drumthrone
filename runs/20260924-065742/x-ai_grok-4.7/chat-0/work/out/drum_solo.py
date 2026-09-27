#!/usr/bin/env python3
"""
Two-minute drum solo for General MIDI channel 10.

Form (4/4, 100 BPM, exactly 120 seconds):
  1-4   Swing statement of Motif A
  5-8   Straight transformation and displacement
  9-12  Tom melody (Motif B)
  13-16 Half-time weight (A's kicks, new backbeat)
  17-20 Latin clave (Motif C); A's kicks hide in the feet
  21-24 Fusion: A and C stacked on the kit
  25-28 Pocket funk (Motif D), then a 3-over-4 exit
  29-32 Linear push, sextuplet roll, silence
  33-36 Whisper release (side stick / brushes)
  37-40 Rebuild
  41-44 Climax: A shouted, B sung, call/response, fill
  45-48 Swing recap with a clave memory
  49-50 Cadence

Feel is sectional and deliberate (triplet swing, pocket layback,
heavy backbeat, on-top Latin, forward push), never random.
At most two hands and two feet strike at once.
Deterministic: no RNG, identical solo.mid every run.
"""

from mido import Message, MetaMessage, MidiFile, MidiTrack

PPQ = 480
BPM = 100
BARS = 50
BAR = PPQ * 4
END = BAR * BARS

# GM percussion
K, KA = 36, 35
SN, SS = 38, 37
CH, PH, OH = 42, 44, 46
LT, HF, FT = 41, 43, 45
LM, HM, HT = 47, 48, 50
CR, RD, CHN, RB = 49, 51, 52, 53
SP, CB, CR2, RC2 = 55, 56, 57, 59
CM, CO, LC = 62, 63, 64
AGH = 67
CAB = 69
WBH, WBL = 76, 77
TRIM, TRI = 80, 81

FOOT = {KA, K, PH}
HATS = {CH, PH, OH}
TOMS = {LT, HF, FT, LM, HM, HT}

# Motif A: kick, ghost, snare, kick, ghost, snare, kick.
STRAIGHT_A = (
    (0, "K"),
    (120, "G"),
    (480, "S"),
    (720, "K"),
    (1320, "G"),
    (1440, "S"),
    (1800, "K"),
)
# Same shape on a triplet/swing grid.
SWING_A = (
    (0, "K"),
    (160, "G"),
    (480, "S"),
    (800, "K"),
    (1120, "G"),
    (1440, "S"),
    (1760, "K"),
)
RIDE_TICKS = (0, 320, 480, 800, 960, 1280, 1440, 1760)
RIDE_DELTA = (6, -24, -8, 4, 2, -26, -6, 0)


def feel_for(bar):
    if bar >= 49 or bar == 43:
        return "grid"
    if bar <= 3 or 44 <= bar <= 48:
        return "swing"
    if 12 <= bar <= 15:
        return "heavy"
    if 16 <= bar <= 19:
        return "latin"
    if 28 <= bar <= 31 or 36 <= bar <= 39:
        return "push"
    if 32 <= bar <= 35:
        return "whisper"
    if 40 <= bar <= 42:
        return "peak"
    return "pocket"


def timing_delta(bar, tick, note, vel):
    """Section pocket. Downbeats stay together; the inside of the bar breathes."""
    if tick == 0:
        return 0
    feel = feel_for(bar)
    if feel == "grid":
        return 0
    if feel == "push":
        return -8
    if feel == "latin":
        return -4
    if feel == "peak":
        if note in (KA, K):
            return -3
        if note in (SN, SS) and vel >= 90:
            return 2
        return 0
    if feel == "whisper":
        if note in (SS, SN):
            return 10
        if note in (KA, K):
            return 4
        return 6
    if feel == "heavy":
        if note in (SN, SS, OH):
            return 20
        if note in (KA, K):
            return 6
        return 10
    if feel == "swing":
        if note in (SN, SS) and vel >= 75:
            return 12
        if note in (SN, SS):
            return 6
        if note in (KA, K):
            return -6
        if note == PH:
            return 4
        return 0
    # pocket: kick ahead, backbeat and ghosts late, hats terraced
    if note in (KA, K):
        return -8
    if note in (SN, SS) and vel >= 75:
        return 14
    if note in (SN, SS):
        return 8
    if note in TOMS:
        return 5
    if note == CH:
        if tick % 480 == 0:
            return -3
        if tick % 240 == 120:
            return 5
        return 2
    if note == OH:
        return 4
    return 0


def default_dur(note):
    if note in (CR, CR2, CHN):
        return 840
    if note == SP:
        return 260
    if note == OH:
        return 300
    if note in (RD, RB, RC2):
        return 180
    if note == TRI:
        return 900
    if note == TRIM:
        return 160
    if note in (KA, K):
        return 64
    if note == PH:
        return 32
    if note == CH:
        return 44
    if note in (CM, CO, LC):
        return 96
    if note in TOMS:
        return 110
    if note == CB:
        return 84
    return 72


def clamp_vel(vel):
    vel = int(vel)
    if vel < 1:
        return 1
    if vel > 124:
        return 124
    return vel


class Score:
    def __init__(self):
        self.events = []

    def add(self, bar, tick, note, vel, dur=None, flam=False, locked=False):
        tick = int(tick)
        if tick < 0 or tick >= BAR:
            return
        if not 35 <= note <= 81:
            return
        vel = clamp_vel(vel)
        delta = 0 if locked else timing_delta(bar, tick, note, vel)
        abs_tick = bar * BAR + tick + delta
        if abs_tick < 0:
            abs_tick = 0
        if abs_tick >= END:
            return
        if dur is None:
            dur = default_dur(note)
        dur = int(dur)
        if dur < 1:
            dur = 1
        if abs_tick + dur > END:
            dur = END - abs_tick
        if flam and vel >= 88:
            grace_at = abs_tick - 18
            if grace_at >= 0:
                grace_vel = vel // 3
                if grace_vel < 32:
                    grace_vel = 32
                if grace_vel > 52:
                    grace_vel = 52
                self.events.append((grace_at, note, grace_vel, 14))
        self.events.append((abs_tick, note, vel, dur))

    def finalize(self):
        notes = resolve_limbs(self.events)
        notes = choke_hats(notes)
        notes = monophonize(notes)
        clean = []
        for tick, note, vel, dur in notes:
            if 0 <= tick < END and 35 <= note <= 81 and 1 <= vel <= 124 and dur >= 1:
                if tick + dur > END:
                    dur = END - tick
                if dur >= 1:
                    clean.append((int(tick), int(note), int(vel), int(dur)))
        clean.sort()
        assert_playable(clean)
        return clean


def resolve_limbs(notes):
    """One drummer: two hands, two feet, one hi-hat."""
    buckets = {}
    for item in notes:
        buckets.setdefault(item[0], []).append(item)
    resolved = []
    for tick in sorted(buckets):
        best = {}
        for item in buckets[tick]:
            note = item[1]
            if note not in best or item[2] > best[note][2]:
                best[note] = item
        group = list(best.values())
        hats = [g for g in group if g[1] in HATS]
        if len(hats) > 1:
            keep = max(hats, key=lambda g: (g[2], -g[1]))[1]
            group = [g for g in group if g[1] not in HATS or g[1] == keep]
        feet = sorted(
            (g for g in group if g[1] in FOOT),
            key=lambda g: (-g[2], g[1]),
        )
        hands = sorted(
            (g for g in group if g[1] not in FOOT),
            key=lambda g: (-g[2], g[1]),
        )
        resolved.extend(feet[:2])
        resolved.extend(hands[:2])
    resolved.sort(key=lambda g: (g[0], g[1], -g[2]))
    return resolved


def choke_hats(notes):
    notes = [list(n) for n in sorted(notes)]
    for i, (tick, note, _vel, dur) in enumerate(notes):
        if note != OH:
            continue
        end = tick + dur
        for tick2, note2, _v2, _d2 in notes[i + 1 :]:
            if tick2 >= end:
                break
            if note2 in HATS and tick2 > tick:
                notes[i][3] = tick2 - tick
                break
    return [tuple(n) for n in notes]


def monophonize(notes):
    by_note = {}
    for tick, note, vel, dur in notes:
        by_note.setdefault(note, []).append((tick, vel, dur))
    out = []
    for note in sorted(by_note):
        lst = sorted(by_note[note], key=lambda x: (x[0], -x[1]))
        deduped = []
        for item in lst:
            if deduped and deduped[-1][0] == item[0]:
                continue
            deduped.append(item)
        for i, (tick, vel, dur) in enumerate(deduped):
            end = tick + dur
            if i + 1 < len(deduped) and deduped[i + 1][0] < end:
                end = deduped[i + 1][0]
            if end > END:
                end = END
            if tick < END and end > tick:
                out.append((tick, note, vel, end - tick))
    out.sort()
    return out


def assert_playable(notes):
    buckets = {}
    for tick, note, _vel, _dur in notes:
        buckets.setdefault(tick, set()).add(note)
    for tick, notes_here in buckets.items():
        feet = [n for n in notes_here if n in FOOT]
        hands = [n for n in notes_here if n not in FOOT]
        if len(feet) > 2 or len(hands) > 2:
            raise RuntimeError(
                "unplayable strike at tick %s: %s" % (tick, sorted(notes_here))
            )


def play_motif(sc, bar, cells, vk, vs, vg, snare=SN, kick=K, flam=False, skip=(), displace=0):
    role_vel = {"K": vk, "S": vs, "G": max(28, vg)}
    role_note = {"K": kick, "S": snare, "G": snare}
    for tick, role in cells:
        at = tick + displace
        if at < 0 or at >= BAR or at in skip:
            continue
        vel = role_vel[role]
        if role == "K" and tick in (720, 800):
            vel = max(30, vk - 8)
        elif role == "K" and tick >= 1760:
            vel = max(30, vk - 14)
        elif role == "S" and tick >= 1440:
            vel = min(124, vs + 2)
        do_flam = flam and role == "S" and vel >= 88
        sc.add(bar, at, role_note[role], vel, flam=do_flam)


def ride_swing(sc, bar, base, bell=False, skip=(), foot=True, ride_note=RD):
    for tick, delta_vel in zip(RIDE_TICKS, RIDE_DELTA):
        if tick in skip:
            continue
        note = RB if bell and tick in (0, 960) else ride_note
        sc.add(bar, tick, note, base + delta_vel, dur=168)
    if foot:
        chick = max(28, base // 2)
        sc.add(bar, 480, PH, chick)
        sc.add(bar, 1440, PH, chick)


def add_hats(sc, bar, indices, accent, medium, soft, accent_phase=(0,), open_at=()):
    for i in indices:
        tick = i * 120
        if i in open_at:
            sc.add(bar, tick, OH, min(124, accent + 8), dur=280)
            continue
        phase = i % 4
        if phase in accent_phase:
            vel = accent
        elif i % 2 == 0:
            vel = medium
        else:
            vel = soft
        sc.add(bar, tick, CH, vel, dur=42)


def funk_groove(sc, bar, kick_vel, snare_vel, hat_accent, variant=0, hat_stop=16):
    open_at = (14,) if variant == 1 else ()
    accent_phase = (1,) if variant == 2 else (0,)
    soft = max(40, hat_accent - 44)
    medium = max(soft + 8, hat_accent - 22)
    add_hats(
        sc,
        bar,
        range(hat_stop),
        accent=hat_accent,
        medium=medium,
        soft=soft,
        accent_phase=accent_phase,
        open_at=open_at,
    )
    limit = hat_stop * 120
    if variant == 2:
        kicks = ((0, 0), (360, -4), (840, -6), (1200, -4))
        snares = ((600, 0), (1560, 4))
        ghosts = (1, 3, 7, 11, 15)
    else:
        kicks = ((0, 0), (720, -8), (1080, -6), (1680, -10))
        snares = ((480, 0), (1440, 2))
        ghosts = (1, 3, 7, 11, 13, 15)
    for tick, delta_vel in kicks:
        if tick < limit:
            sc.add(bar, tick, K, kick_vel + delta_vel)
    for tick, delta_vel in snares:
        if tick < limit:
            sc.add(bar, tick, SN, snare_vel + delta_vel)
    if variant == 1 and 1800 < limit:
        sc.add(bar, 1800, SN, max(40, snare_vel - 10))
    for k, i in enumerate(ghosts):
        if i >= hat_stop:
            continue
        if variant == 1 and i >= 14:
            continue
        sc.add(bar, i * 120, SN, 38 + (k % 3) * 3)


def three_fill(sc, bar, start=960):
    """Accents every third 16th: a short 3-over-4, then a floor-tom cadence."""
    toms = (HT, HM, LM)
    accent_i = 0
    for i in range(7):
        tick = start + i * 120
        if i % 3 == 0:
            sc.add(bar, tick, toms[accent_i], 102 + accent_i * 6)
            if i == 0:
                sc.add(bar, tick, K, 98)
            accent_i += 1
        else:
            sc.add(bar, tick, SN, 40 + (i % 3) * 4)
    sc.add(bar, start + 7 * 120, FT, 116)
    sc.add(bar, start + 7 * 120, K, 102)


def conga_3(sc, bar, vel):
    # Holes on the 3-side clave (0, 720, 1440) so the hands interlock.
    sc.add(bar, 240, CM, vel - 20)
    sc.add(bar, 480, LC, vel - 2)
    sc.add(bar, 960, CO, vel + 6)
    sc.add(bar, 1200, CM, vel - 22)
    sc.add(bar, 1680, CO, vel)


def conga_2(sc, bar, vel):
    sc.add(bar, 0, LC, vel - 6)
    sc.add(bar, 240, CM, vel - 20)
    sc.add(bar, 720, CO, vel + 6)
    sc.add(bar, 1200, CM, vel - 22)
    sc.add(bar, 1440, LC, vel)
    sc.add(bar, 1680, CO, vel + 2)


def pickup(sc, bar, note, vel1, vel2):
    sc.add(bar, 1600, note, vel1, dur=48)
    sc.add(bar, 1760, note, vel2, dur=48)


def section_swing_intro(sc):
    # Bar 1: space. Ride, a kick, side stick foreshadowing beat 4.
    ride_swing(sc, 0, 62)
    sc.add(0, 0, K, 70)
    sc.add(0, 960, K, 56)
    sc.add(0, 1440, SS, 58)

    # Bar 2: Motif A in full, swung.
    ride_swing(sc, 1, 68, bell=True)
    play_motif(sc, 1, SWING_A, vk=78, vs=94, vg=36)

    # Bar 3: same motif, one extra syncopated kick.
    ride_swing(sc, 2, 72, bell=True)
    play_motif(sc, 2, SWING_A, vk=84, vs=100, vg=38)
    sc.add(2, 320, K, 62)

    # Bar 4: motif, then the pickup cell that will return before the ending.
    ride_swing(sc, 3, 74, bell=True, skip={1760})
    play_motif(sc, 3, SWING_A, vk=86, vs=102, vg=40, skip={1760})
    pickup(sc, 3, SN, 50, 66)


def section_straight(sc):
    # Bar 5: same motif, straightened. Splash marks the feel change.
    sc.add(4, 0, SP, 82)
    add_hats(sc, 4, range(16), accent=78, medium=58, soft=40)
    play_motif(sc, 4, STRAIGHT_A, vk=86, vs=100, vg=38)

    # Bar 6: displaced by a 16th. Hat accents follow the displacement.
    add_hats(sc, 5, range(16), accent=74, medium=54, soft=38, accent_phase=(1,))
    play_motif(sc, 5, STRAIGHT_A, vk=80, vs=94, vg=36, displace=120)

    # Bar 7: motif home, a little fuller. Two extra ghosts foreshadow the pocket.
    add_hats(sc, 6, range(16), accent=84, medium=62, soft=42)
    play_motif(sc, 6, STRAIGHT_A, vk=92, vs=108, vg=40)
    sc.add(6, 360, SN, 36)
    sc.add(6, 1080, SN, 34)

    # Bar 8: displaced again, then a tom fill takes the last beat.
    add_hats(sc, 7, range(12), accent=80, medium=58, soft=40, accent_phase=(1,))
    play_motif(sc, 7, STRAIGHT_A, vk=88, vs=102, vg=38, displace=120, skip={1440, 1560})
    sc.add(7, 1440, K, 90)
    sc.add(7, 1440, HT, 98)
    sc.add(7, 1560, HM, 102)
    sc.add(7, 1680, LM, 108)
    sc.add(7, 1800, FT, 114)


def section_toms(sc):
    # Bar 9: Motif B stated. Rests on the "&" of 1 and 3 (foot only).
    sc.add(8, 0, SP, 76)
    sc.add(8, 0, HT, 94)
    sc.add(8, 0, K, 86)
    sc.add(8, 240, PH, 38)
    sc.add(8, 480, HM, 88)
    sc.add(8, 720, HM, 74)
    sc.add(8, 960, LM, 96)
    sc.add(8, 960, K, 78)
    sc.add(8, 1200, PH, 36)
    sc.add(8, 1440, FT, 102)
    sc.add(8, 1680, SN, 86)
    sc.add(8, 1680, PH, 34)

    # Bar 10: the melody answers, more syncopated, rising then falling.
    sc.add(9, 0, HM, 92)
    sc.add(9, 0, K, 84)
    sc.add(9, 0, RB, 80)
    sc.add(9, 240, HT, 90)
    sc.add(9, 480, PH, 36)
    sc.add(9, 600, HT, 78)
    sc.add(9, 720, LM, 84)
    sc.add(9, 960, HM, 98)
    sc.add(9, 960, K, 80)
    sc.add(9, 1200, HT, 76)
    sc.add(9, 1440, SN, 106, flam=True)
    sc.add(9, 1680, SN, 42)
    sc.add(9, 1680, PH, 34)
    sc.add(9, 1800, LM, 80)

    # Bar 11: Motif B pitches on Motif A's rhythm.
    sc.add(10, 0, K, 90)
    sc.add(10, 0, RB, 78)
    sc.add(10, 120, FT, 54)
    sc.add(10, 240, PH, 36)
    sc.add(10, 480, LM, 98)
    sc.add(10, 720, K, 82)
    sc.add(10, 960, RB, 72)
    sc.add(10, 1200, PH, 34)
    sc.add(10, 1320, HM, 60)
    sc.add(10, 1440, HT, 110)
    sc.add(10, 1800, K, 76)

    # Bar 12: sequence down the toms into the half-time.
    sc.add(11, 0, HT, 98)
    sc.add(11, 0, K, 90)
    sc.add(11, 0, RB, 74)
    sc.add(11, 240, HM, 86)
    sc.add(11, 480, LM, 94)
    sc.add(11, 480, K, 78)
    sc.add(11, 720, FT, 90)
    sc.add(11, 960, HF, 98)
    sc.add(11, 1200, LT, 92)
    sc.add(11, 1440, HT, 106)
    sc.add(11, 1440, K, 88)
    sc.add(11, 1560, HM, 102)
    sc.add(11, 1680, LM, 110)
    sc.add(11, 1800, FT, 118)


def section_halftime(sc):
    # Bar 13: A's kicks, snare moved to beat 3. China + floor tom on 1.
    sc.add(12, 0, CHN, 116, dur=700)
    sc.add(12, 0, FT, 108)
    sc.add(12, 0, K, 112)
    for tick in (240, 480, 720, 1200, 1440, 1680):
        sc.add(12, tick, CH, 58 if tick % 960 == 0 else 42)
    sc.add(12, 720, K, 100)
    sc.add(12, 960, OH, 100, dur=280)
    sc.add(12, 960, SN, 118, flam=True)
    sc.add(12, 1800, K, 94)

    # Bar 14: same groove, ghosts, no china.
    sc.add(13, 0, K, 102)
    for tick in (0, 240, 480, 720, 1200, 1440, 1680):
        sc.add(13, tick, CH, 54 if tick % 960 == 0 else 40)
    sc.add(13, 720, K, 92)
    sc.add(13, 960, OH, 92, dur=280)
    sc.add(13, 960, SN, 110, flam=True)
    sc.add(13, 1800, K, 86)
    for tick, vel in ((240, 38), (600, 36), (1200, 40), (1560, 38)):
        sc.add(13, tick, SN, vel)

    # Bar 15: dynamic hole. Cross-stick and ride, still the same kicks.
    sc.add(14, 0, K, 70)
    for tick in (0, 240, 480, 720, 960, 1200, 1440, 1680):
        sc.add(14, tick, RD, 60 if tick % 960 == 0 else 46, dur=160)
    sc.add(14, 720, K, 62)
    sc.add(14, 960, SS, 72)
    sc.add(14, 1800, K, 58)

    # Bar 16: rebuild and hand off to the percussion section.
    sc.add(15, 0, K, 104)
    sc.add(15, 0, RD, 72, dur=160)
    sc.add(15, 480, K, 92)
    sc.add(15, 720, SN, 42)
    sc.add(15, 720, RD, 56, dur=150)
    sc.add(15, 960, SN, 114, flam=True)
    sc.add(15, 960, OH, 98, dur=200)
    fill = ((HT, 90), (HM, 96), (LM, 102), (FT, 108), (SN, 114), (FT, 120))
    for i, (note, vel) in enumerate(fill):
        sc.add(15, 1200 + i * 120, note, vel)
    sc.add(15, 1200, K, 90)
    sc.add(15, 1680, K, 98)


def section_latin(sc):
    # Bars 17-18: 3-2 son clave, conga tumbao in the holes, soft kick.
    for tick, vel in ((0, 102), (720, 92), (1440, 98)):
        sc.add(16, tick, CB, vel)
    conga_3(sc, 16, 74)
    sc.add(16, 0, K, 64)
    sc.add(16, 960, K, 56)

    for tick, vel in ((480, 96), (960, 100)):
        sc.add(17, tick, CB, vel)
    conga_2(sc, 17, 76)
    sc.add(17, 0, K, 62)
    sc.add(17, 960, K, 58)
    sc.add(17, 1800, AGH, 80)

    # Bar 19: clave on woodblock; Motif A is only in the feet.
    for tick, vel in ((0, 98), (720, 90), (1440, 104)):
        sc.add(18, tick, WBH, vel)
    conga_3(sc, 18, 78)
    sc.add(18, 0, K, 84)
    sc.add(18, 720, K, 76)
    sc.add(18, 1800, K, 72)

    # Bar 20: back to the kit.
    sc.add(19, 0, CB, 94)
    sc.add(19, 0, LC, 66)
    sc.add(19, 0, K, 68)
    sc.add(19, 240, CM, 50)
    sc.add(19, 480, CB, 90)
    sc.add(19, 720, CO, 82)
    sc.add(19, 960, SN, 98)
    sc.add(19, 960, K, 80)
    sc.add(19, 1080, SN, 54)
    sc.add(19, 1200, HT, 92)
    sc.add(19, 1320, HM, 96)
    sc.add(19, 1440, LM, 102)
    sc.add(19, 1560, FT, 108)
    sc.add(19, 1680, SN, 114)
    sc.add(19, 1800, K, 98)
    sc.add(19, 1800, SP, 90)


def section_fusion(sc):
    # Bar 21: bell plays the 3-side, snare plays A. Where they coincide, stack them.
    for tick, vel in ((0, 92), (720, 84), (1440, 96)):
        sc.add(20, tick, RB, vel)
    play_motif(sc, 20, STRAIGHT_A, vk=88, vs=102, vg=38)
    for tick, vel in ((240, 36), (1200, 34), (1680, 34)):
        sc.add(20, tick, PH, vel)
    for tick, vel in ((360, 36), (600, 38), (1080, 36), (1560, 40)):
        sc.add(20, tick, SN, vel)

    # Bar 22: 2-side clave.
    sc.add(21, 480, RB, 90)
    sc.add(21, 960, RB, 94)
    play_motif(sc, 21, STRAIGHT_A, vk=90, vs=104, vg=38)
    for tick in (240, 1200, 1680):
        sc.add(21, tick, PH, 36)

    # Bar 23: hats take over, motif plain and loud.
    add_hats(sc, 22, range(16), accent=86, medium=62, soft=42)
    play_motif(sc, 22, STRAIGHT_A, vk=94, vs=110, vg=40)

    # Bar 24: displaced, open hat lifts into the pocket.
    add_hats(
        sc,
        23,
        range(16),
        accent=82,
        medium=60,
        soft=40,
        accent_phase=(1,),
        open_at=(14,),
    )
    play_motif(sc, 23, STRAIGHT_A, vk=88, vs=104, vg=38, displace=120)


def section_pocket(sc):
    # Bars 25-26: sit in it.
    funk_groove(sc, 24, kick_vel=94, snare_vel=106, hat_accent=82, variant=0)
    funk_groove(sc, 25, kick_vel=98, snare_vel=110, hat_accent=86, variant=1)
    # Bar 27: snare accents move off the backbeat.
    funk_groove(sc, 26, kick_vel=96, snare_vel=108, hat_accent=84, variant=2)
    # Bar 28: two beats of groove, then 3-over-4 into the push.
    funk_groove(sc, 27, kick_vel=100, snare_vel=112, hat_accent=88, variant=0, hat_stop=8)
    three_fill(sc, 27, start=960)


def section_push(sc):
    # Bar 29: Motif A inside a linear 16th stream.
    bar28 = (
        (K, 102),
        (CH, 50),
        (SN, 44),
        (CH, 48),
        (SN, 110),
        (CH, 46),
        (K, 96),
        (CH, 48),
        (CH, 54),
        (SN, 42),
        (CH, 50),
        (SN, 46),
        (SN, 114),
        (CH, 52),
        (CH, 48),
        (K, 88),
    )
    assert len(bar28) == 16
    for i, (note, vel) in enumerate(bar28):
        sc.add(28, i * 120, note, vel, dur=40)

    # Bar 30: same rhythm, tom connectors.
    bar29 = (
        (K, 108),
        (HT, 60),
        (SN, 48),
        (HM, 58),
        (SN, 114),
        (HT, 54),
        (K, 102),
        (LM, 60),
        (HT, 66),
        (SN, 46),
        (HM, 62),
        (SN, 50),
        (SN, 118),
        (FT, 64),
        (LM, 68),
        (K, 94),
    )
    assert len(bar29) == 16
    for i, (note, vel) in enumerate(bar29):
        sc.add(29, i * 120, note, vel, dur=42)

    # Bar 31: sextuplets, kick keeps the pulse, crescendo.
    patterns = (
        (SN, HT, SN, HM, SN, LM),
        (HT, SN, HM, SN, LM, SN),
        (SN, HM, SN, FT, SN, HT),
        (LM, SN, FT, SN, HT, SN),
    )
    for beat, pattern in enumerate(patterns):
        for j, note in enumerate(pattern):
            idx = beat * 6 + j
            vel = 78 + idx * 2
            if j == 0:
                vel += 10
                sc.add(30, beat * 480, K, 92 + beat * 6)
            elif j == 3:
                vel += 6
            sc.add(30, beat * 480 + j * 80, note, min(122, vel), dur=40)

    # Bar 32: snare roll for three beats, then stop.
    for beat in range(3):
        for j in range(6):
            idx = beat * 6 + j
            vel = 58 + idx * 4
            if j == 0:
                vel += 14
                sc.add(31, beat * 480, K, 90 + beat * 8)
            elif j == 3:
                vel += 6
            sc.add(31, beat * 480 + j * 80, SN, min(122, vel), dur=34)


def section_whisper(sc):
    # Bar 33: the pause, then a fragment of the swing motif.
    sc.add(32, 480, PH, 36)
    sc.add(32, 960, SS, 50)
    sc.add(32, 1440, SS, 56)
    sc.add(32, 1440, PH, 34)
    sc.add(32, 1760, KA, 44)

    # Bar 34: full Motif A, whispered, triangle on 1.
    sc.add(33, 0, TRI, 60, dur=1100)
    play_motif(sc, 33, SWING_A, vk=54, vs=66, vg=40, snare=SS, kick=KA)
    sc.add(33, 480, PH, 38)
    sc.add(33, 1440, PH, 36)

    # Bar 35: cabasa plays the ride pattern (brushes), side stick plays A.
    for tick, delta_vel in zip(RIDE_TICKS, (0, -8, -2, 2, 0, -8, -2, 2)):
        sc.add(34, tick, CAB, 52 + delta_vel, dur=56)
    play_motif(sc, 34, SWING_A, vk=56, vs=68, vg=42, snare=SS, kick=KA)

    # Bar 36: hats straighten, a small crescendo, pickup into the rebuild.
    for i, tick in enumerate(range(0, 1920, 240)):
        sc.add(35, tick, CH, 50 + i * 3)
    play_motif(sc, 35, STRAIGHT_A, vk=60, vs=70, vg=40, skip={1800})
    pickup(sc, 35, SN, 52, 64)


def section_rebuild(sc):
    # Bar 37: Motif A returns at mezzo-forte. Splash instead of hat on 1.
    sc.add(36, 0, SP, 78)
    for tick in (240, 480, 720, 960, 1200, 1440, 1680):
        sc.add(36, tick, CH, 72 if tick % 960 == 0 else 54)
    play_motif(sc, 36, STRAIGHT_A, vk=90, vs=102, vg=42)

    # Bar 38: motif, then a short tom answer (preview of the climax dialogue).
    sc.add(37, 0, SP, 86)
    for tick in (240, 480, 720, 960, 1200):
        sc.add(37, tick, CH, 76 if tick % 960 == 0 else 56)
    play_motif(sc, 37, STRAIGHT_A, vk=98, vs=112, vg=44, skip={1440, 1800})
    sc.add(37, 1440, HT, 104)
    sc.add(37, 1560, HM, 100)
    sc.add(37, 1680, LM, 108)
    sc.add(37, 1800, FT, 112)
    sc.add(37, 1800, K, 94)

    # Bar 39: the pocket groove, louder, leaning forward.
    funk_groove(sc, 38, kick_vel=110, snare_vel=116, hat_accent=96, variant=0)

    # Bar 40: 8th-note triplets climb into the climax. Splash on the last note.
    phrase = (K, SN, HT, SN, HM, LM, SN, FT, HT, SN, SN)
    assert len(phrase) == 11
    for i, note in enumerate(phrase):
        tick = i * 160
        vel = 90 + i * 3
        sc.add(39, tick, note, min(120, vel), dur=48)
        if i % 3 == 0 and note != K:
            sc.add(39, tick, K, min(116, vel - 8))
    sc.add(39, 1600, SP, 104)


def section_climax(sc):
    # Bar 41: Motif A at full voice. Ghosts remain — that's the point.
    sc.add(40, 0, K, 120, locked=True)
    sc.add(40, 0, CR, 122, dur=880, locked=True)
    sc.add(40, 0, CH, 82, locked=True)
    for tick, vel in ((120, 46), (360, 40), (600, 44), (1080, 42), (1320, 48)):
        sc.add(40, tick, SN, vel)
    for tick in (240, 480, 720, 960, 1200, 1680):
        sc.add(40, tick, CH, 80 if tick % 960 == 0 else 60)
    sc.add(40, 480, SN, 122, flam=True, locked=True)
    sc.add(40, 720, K, 112)
    sc.add(40, 1440, SN, 124, flam=True, locked=True)
    sc.add(40, 1440, OH, 108, dur=260, locked=True)
    sc.add(40, 1800, K, 108)

    # Bar 42: Motif B, sung fortissimo. Space in the rests.
    sc.add(41, 0, HT, 118, locked=True)
    sc.add(41, 0, K, 116, locked=True)
    sc.add(41, 0, CR, 114, dur=700, locked=True)
    sc.add(41, 240, PH, 44)
    sc.add(41, 480, HM, 110)
    sc.add(41, 480, K, 100)
    sc.add(41, 720, HM, 92)
    sc.add(41, 960, LM, 122, locked=True)
    sc.add(41, 960, K, 114, locked=True)
    sc.add(41, 960, CR2, 110, dur=640, locked=True)
    sc.add(41, 1200, PH, 42)
    sc.add(41, 1440, FT, 120)
    sc.add(41, 1440, K, 106)
    sc.add(41, 1680, SN, 120, flam=True, locked=True)

    # Bar 43: call (A) and response (B), china on the answer.
    sc.add(42, 0, K, 116, locked=True)
    sc.add(42, 0, CH, 78, locked=True)
    sc.add(42, 120, SN, 48)
    sc.add(42, 240, CH, 62)
    sc.add(42, 480, SN, 120, flam=True, locked=True)
    sc.add(42, 480, CH, 74, locked=True)
    sc.add(42, 720, K, 106)
    sc.add(42, 720, CH, 60)
    sc.add(42, 960, HT, 118, locked=True)
    sc.add(42, 960, K, 110, locked=True)
    sc.add(42, 960, CHN, 114, dur=520, locked=True)
    sc.add(42, 1080, HM, 98)
    sc.add(42, 1200, LM, 110)
    sc.add(42, 1320, FT, 102)
    sc.add(42, 1440, SN, 122, flam=True, locked=True)
    sc.add(42, 1560, HT, 92)
    sc.add(42, 1680, HM, 106)
    sc.add(42, 1800, K, 112)

    # Bar 44: descending fill, an 8th of air, then home.
    fill = (
        (HT, HT, HM, HM, LM, LM)
        + (LM, FT, FT, HF, HF, LT)
        + (SN, HT, SN, HM, SN, LM)
        + (FT, SN, LT, LT)
    )
    assert len(fill) == 22
    for i, note in enumerate(fill):
        vel = min(122, 100 + i)
        if i % 6 == 0:
            vel = min(124, vel + 6)
            sc.add(43, i * 80, K, min(120, 104 + i // 6), locked=True)
        sc.add(43, i * 80, note, vel, dur=48, locked=True)


def section_recap(sc):
    # Bar 45: crash says "home", then the swing motif at a human volume.
    sc.add(44, 0, K, 114, locked=True)
    sc.add(44, 0, CR, 118, dur=800, locked=True)
    ride_swing(sc, 44, 66, skip={0}, ride_note=RC2)
    play_motif(sc, 44, SWING_A, vk=86, vs=98, vg=38)

    # Bar 46: the theme, relaxed.
    ride_swing(sc, 45, 62, ride_note=RC2)
    play_motif(sc, 45, SWING_A, vk=78, vs=90, vg=36)

    # Bar 47: low woodblock quotes the clave; beat 4 of A is re-orchestrated.
    ride_swing(sc, 46, 60, ride_note=RC2)
    play_motif(sc, 46, SWING_A, vk=72, vs=84, vg=34, skip={1440})
    for tick, vel in ((0, 72), (720, 66), (1440, 78)):
        sc.add(46, tick, WBL, vel)

    # Bar 48: sparer, winding down.
    ride_swing(sc, 47, 58, ride_note=RC2)
    play_motif(sc, 47, SWING_A, vk=68, vs=78, vg=34, skip={1120, 1760})

    # Bar 49: one last swing statement, pickup into the button.
    ride_swing(sc, 48, 60, skip={1760}, ride_note=RC2)
    play_motif(sc, 48, SWING_A, vk=74, vs=84, vg=36, skip={1760})
    pickup(sc, 48, SN, 66, 88)


def section_ending(sc):
    # Stinger, ring, then the side-stick accent of Motif A left unanswered.
    sc.add(49, 0, K, 120, locked=True)
    sc.add(49, 0, KA, 106, locked=True)
    sc.add(49, 0, CR, 124, dur=1900, locked=True)
    sc.add(49, 1440, SS, 54)
    sc.add(49, 1760, TRIM, 44, dur=160)
    sc.add(49, 1880, PH, 36, dur=28)


def compose(sc):
    section_swing_intro(sc)
    section_straight(sc)
    section_toms(sc)
    section_halftime(sc)
    section_latin(sc)
    section_fusion(sc)
    section_pocket(sc)
    section_push(sc)
    section_whisper(sc)
    section_rebuild(sc)
    section_climax(sc)
    section_recap(sc)
    section_ending(sc)


def write_midi(notes, path):
    mid = MidiFile(type=0, ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("track_name", name="Drum Solo", time=0))
    track.append(MetaMessage("set_tempo", tempo=60000000 // BPM, time=0))
    track.append(
        MetaMessage(
            "time_signature",
            numerator=4,
            denominator=4,
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0,
        )
    )
    track.append(Message("control_change", channel=9, control=7, value=127, time=0))
    track.append(Message("control_change", channel=9, control=10, value=64, time=0))
    track.append(Message("control_change", channel=9, control=91, value=36, time=0))
    track.append(Message("control_change", channel=9, control=93, value=0, time=0))

    events = []
    for tick, note, vel, dur in notes:
        end = tick + dur
        if end > END:
            end = END
        if end <= tick or tick >= END:
            continue
        events.append((tick, 1, note, vel))
        events.append((end, 0, note, 0))
    events.sort()

    previous = 0
    for tick, kind, note, vel in events:
        delta = tick - previous
        if delta < 0:
            raise RuntimeError("negative delta")
        previous = tick
        if kind == 0:
            track.append(
                Message("note_off", channel=9, note=note, velocity=0, time=delta)
            )
        else:
            track.append(
                Message("note_on", channel=9, note=note, velocity=vel, time=delta)
            )
    tail = END - previous
    if tail < 0:
        raise RuntimeError("track overran two minutes")
    track.append(MetaMessage("end_of_track", time=tail))
    mid.save(path)


def main():
    assert BARS * 4 * 60 == 120 * BPM
    score = Score()
    compose(score)
    notes = score.finalize()
    if not notes:
        raise RuntimeError("empty score")
    write_midi(notes, "solo.mid")


if __name__ == "__main__":
    main()
