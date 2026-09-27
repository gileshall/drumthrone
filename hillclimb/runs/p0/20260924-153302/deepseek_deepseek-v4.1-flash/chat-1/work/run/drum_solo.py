#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid: a two minute General MIDI drum solo on MIDI channel 10
(GM percussion, notes 35-81), playable by one drummer (two hands, two feet).

Form  (48 bars of 4/4 at 96 bpm  ->  exactly 120.0 seconds)

    1- 6   intro      motif A stated quietly, laid back
    7-14   A          the groove: backbeat, swing ride, ghost notes
   15-22   A'         variation: ride bell, hi-hat, cowbell, tom answer
   23-30   build      motif B (descending toms), density and volume rise
   31-36   peak       loudest statement of motif A + motif B
   37-40   breakdown  drops to rim clicks and pedal hat, pushed way back
   41-46   return     motif A at full power
   47-48   outro      final fill and one big hit

Only mido is used.  Every random-looking detail comes from a fixed-seed
integer LCG, so the file is byte-for-byte identical on every run.
"""

import mido

# --------------------------------------------------------------------------
# time base
# --------------------------------------------------------------------------
TPB      = 480                 # ticks per quarter note
BAR      = TPB * 4             # 4/4
N_BARS   = 48                  # 48 bars at 96 bpm == 120.0 s
TEMPO    = 625000              # microseconds per quarter -> 96 bpm
END_TICK = N_BARS * BAR

# --------------------------------------------------------------------------
# General MIDI percussion (35..81)
# --------------------------------------------------------------------------
BASS    = 35
KICK    = 36
RIM     = 37
SNARE   = 38
CLAP    = 39
SNARE2  = 40
FLOOR_L = 41
HAT     = 42
FLOOR_H = 43
PEDAL   = 44
TOM_LO  = 45
HAT_OP  = 46
TOM_MID = 47
TOM_HI  = 48
CRASH   = 49
TOM_HH  = 50
RIDE    = 51
CHINA   = 52
BELL    = 53
TAMB    = 54
SPLASH  = 55
COWBELL = 56
CRASH2  = 57
VIBRA   = 58
RIDE2   = 59
BONGO_H = 60
BONGO_L = 61
CONGA_M = 62
CONGA_H = 63
CONGA_L = 64
TIMB_H  = 65
TIMB_L  = 66
CLAVES  = 75
WOOD_H  = 76
WOOD_L  = 77
TRI_MU  = 80
TRI_OP  = 81

# --------------------------------------------------------------------------
# rhythmic grids.  positions are in tenths of a beat inside the bar
# --------------------------------------------------------------------------
# swung eighths (60/40):  1, &(late), 2, &(late) ...
SW8 = (0, 6, 10, 16, 20, 26, 30, 36)

# even sixteenth notes, used for fills (a real drummer straightens out fills
# even while the ride keeps swinging)
ST16 = (0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5,
        20.0, 22.5, 25.0, 27.5, 30.0, 32.5, 35.0, 37.5)

# --------------------------------------------------------------------------
# event store and the single place where a strike is created
# --------------------------------------------------------------------------
EVENTS = []          # [tick, voice, gm note, velocity, duration]
FEEL   = 0           # per-section placement offset (ticks)
DYN    = 1.0         # per-section dynamic scale

# deliberate micro-placement of the four limbs
V_OFF = {'RH': 0, 'LH': 4, 'RF': -3, 'LF': 2}

_seed = 987654321


def _rnd():
    """tiny deterministic LCG, only used for a couple of ticks of breathing"""
    global _seed
    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return ((_seed >> 7) & 0xFFFFF) / float(0x100000)


def hit(bar, p, voice, note, vel, dur=70):
    """One strike.  `p` is the position in tenths of a beat inside the bar."""
    t = (bar - 1) * BAR + int(round(p * 48)) + FEEL + V_OFF[voice]
    t += int(round((_rnd() - 0.5) * 4.0))
    v = int(round(vel * DYN + (_rnd() - 0.5) * 4.0))
    EVENTS.append((t, voice, note, max(1, min(127, v)), dur))


# --------------------------------------------------------------------------
# building blocks
# --------------------------------------------------------------------------
def swing_ride(bar, vel, accent=8, skip=(), note=RIDE, dur=60, bell=False):
    """The right hand: eight swung eighths with accented downbeats."""
    for p in SW8:
        if p in skip:
            continue
        n = BELL if (bell and p in (0, 20)) else note
        v = vel + (accent if p in (0, 20) else 0)
        hit(bar, p, 'RH', n, v, dur)


def groove(bar, rvel=74, svel=104, kvel=100, kick=(0, 20), snare=(10, 30),
           ghosts=(), pedal=(10, 30), crash=None, ride=True, skip=(),
           rnote=RIDE, ped_vel=70, bell=False, ride_accent=8):
    """Motif A: swinging ride, kick on 1 & 3, backbeat on 2 & 4, ghost notes."""
    sk = set(skip)
    if crash is not None:
        hit(bar, 0, 'RH', crash, 118, 380)
        sk.add(0)
    if ride:
        swing_ride(bar, rvel, accent=ride_accent, skip=tuple(sorted(sk)),
                   note=rnote, bell=bell)
    for p in kick:
        hit(bar, p, 'RF', KICK, kvel, 60)
    for p in snare:
        hit(bar, p, 'LH', SNARE, svel, 60)
    for p in ghosts:
        hit(bar, p, 'LH', SNARE, 32, 40)
    for p in pedal:
        hit(bar, p, 'LF', PEDAL, ped_vel, 50)


def motifB(bar, start, vel, notes=(TOM_HI, TOM_MID, TOM_LO, FLOOR_H), dur=70):
    """Motif B: four tom strokes in swung eighths -- the 'descending run'."""
    hands = ('RH', 'LH', 'RH', 'LH')
    offs  = (0, 6, 10, 16)
    for i in range(4):
        p = start + offs[i]
        if p < 40:
            hit(bar, p, hands[i], notes[i], vel + i * 2, dur)


def fill16(bar, drums, base=80, step=1.0, accent=32, dur=55,
           kick=(0, 20), kvel=112):
    """A straight sixteenth-note fill, alternating hands, with accents."""
    for i, p in enumerate(ST16):
        h = 'RH' if i % 2 == 0 else 'LH'
        v = base + i * step + (accent if i % 4 == 0 else 0)
        hit(bar, p, h, drums[i], v, dur)
    for p in kick:
        hit(bar, p, 'RF', KICK, kvel, 60)


# --------------------------------------------------------------------------
# the solo
# --------------------------------------------------------------------------
def compose():
    global FEEL, DYN

    # ======================================================================
    # 1) INTRO -- bars 1-6.  Laid back, quiet, motif A is uncovered.
    # ======================================================================
    FEEL, DYN = 10, 0.82

    # bar 1: only the left foot and a rim click
    for p in (0, 10, 20, 30):
        hit(1, p, 'LF', PEDAL, 60, 50)
    hit(1, 30, 'LH', RIM, 74, 55)

    # bar 2: the ride enters
    swing_ride(2, 56)
    hit(2, 10, 'LF', PEDAL, 58, 50)
    hit(2, 30, 'LF', PEDAL, 58, 50)
    hit(2, 30, 'LH', RIM, 80, 55)

    # bars 3-6: the groove assembles, ghosts appear, one small fill
    groove(3, rvel=60, svel=86, kvel=82, kick=(0,), snare=(10, 30),
           pedal=(10, 30), ped_vel=58)

    groove(4, rvel=64, svel=90, kvel=88, kick=(0, 20), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30), ped_vel=60)

    groove(5, rvel=68, svel=94, kvel=92, kick=(0, 20, 36), snare=(10, 30),
           ghosts=(3, 23, 28), pedal=(10, 30), ped_vel=62)

    groove(6, rvel=72, svel=98, kvel=96, kick=(0,), snare=(10,),
           ghosts=(3,), pedal=(10,), skip=(20, 26, 30, 36), ped_vel=64)
    hit(6, 20, 'LH', SNARE, 100, 55)
    hit(6, 25, 'LH', TOM_HI, 102, 70)
    hit(6, 30, 'RH', TOM_MID, 106, 70)
    hit(6, 32.5, 'LH', TOM_LO, 108, 70)
    hit(6, 35, 'RH', TOM_HI, 110, 70)
    hit(6, 37.5, 'LH', FLOOR_H, 112, 70)

    # ======================================================================
    # 2) A -- bars 7-14.  Motif A, clear and confident.
    # ======================================================================
    FEEL, DYN = 3, 0.92

    groove(7, rvel=74, svel=104, kvel=100, kick=(0, 20), snare=(10, 30),
           pedal=(10, 30), crash=CRASH, ride_accent=10)

    groove(8, rvel=74, svel=104, kvel=100, kick=(0, 16, 20), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30))

    groove(9, rvel=76, svel=106, kvel=102, kick=(0, 20, 36), snare=(10, 30),
           ghosts=(3, 23, 28), pedal=(10, 30))

    groove(10, rvel=76, svel=106, kvel=102, kick=(0, 16, 20), snare=(10, 30),
           ghosts=(3, 13, 23, 28), pedal=(10, 30))

    groove(11, rvel=78, svel=108, kvel=104, kick=(0, 20, 26), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30))
    hit(11, 36, 'LH', SNARE, 90, 45)

    groove(12, rvel=78, svel=110, kvel=106, kick=(0, 16, 20, 26),
           snare=(10, 30), ghosts=(3, 23), pedal=(10, 30), ride_accent=10)

    # bars 13-14: two bar fill, ends on a downbeat crash at bar 15
    swing_ride(13, 78, skip=(20, 26, 30, 36))
    hit(13, 0, 'RF', KICK, 106, 60)
    hit(13, 10, 'LH', SNARE, 108, 55)
    d13 = (TOM_HI, TOM_HI, TOM_MID, TOM_MID, TOM_LO, TOM_LO, FLOOR_H, FLOOR_L)
    for i, p in enumerate(ST16[8:]):
        hit(13, p, 'RH' if i % 2 == 0 else 'LH', d13[i], 104 + i * 2, 60)

    d14 = (TOM_HH, TOM_HI, TOM_HI, TOM_MID,
           TOM_MID, TOM_LO, TOM_LO, FLOOR_H,
           FLOOR_H, FLOOR_L, FLOOR_L, FLOOR_H,
           TOM_LO, TOM_MID, TOM_HI, SNARE)
    fill16(14, d14, base=86, step=1.0, accent=26, kvel=110)

    # ======================================================================
    # 3) A' -- bars 15-22.  Same motif, new colours.
    # ======================================================================
    FEEL, DYN = 2, 0.96

    groove(15, rvel=76, svel=108, kvel=104, kick=(0, 20), snare=(10, 30),
           pedal=(10, 30), crash=CRASH, ride_accent=10)

    groove(16, rvel=76, svel=108, kvel=104, kick=(0, 16, 20), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30))
    hit(16, 36, 'LH', TOM_MID, 96, 70)

    groove(17, rvel=78, svel=108, kvel=104, kick=(0, 20, 36), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30), bell=True, ride_accent=4)

    # bar 18: right hand moves to the hi-hat, opens on the 'and' of 4
    swing_ride(18, 76, note=HAT, skip=(36,))
    hit(18, 36, 'RH', HAT_OP, 92, 150)
    hit(18, 0, 'RF', KICK, 104, 60)
    hit(18, 16, 'RF', KICK, 100, 60)
    hit(18, 20, 'RF', KICK, 104, 60)
    hit(18, 10, 'LH', SNARE, 106, 55)
    hit(18, 30, 'LH', SNARE, 108, 55)
    hit(18, 3, 'LH', SNARE, 60, 40)
    hit(18, 23, 'LH', SNARE, 58, 40)
    hit(18, 10, 'LF', PEDAL, 68, 50)
    hit(18, 30, 'LF', PEDAL, 68, 50)

    groove(19, rvel=78, svel=108, kvel=104, kick=(0, 20), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30))
    hit(19, 20, 'LH', COWBELL, 88, 55)

    groove(20, rvel=80, svel=110, kvel=106, kick=(0, 16, 20), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30), ride_accent=10)
    hit(20, 32.5, 'LH', SNARE, 76, 40)
    hit(20, 35, 'LH', SNARE, 84, 40)

    swing_ride(21, 80, skip=(20, 26, 30, 36))
    hit(21, 0, 'RF', KICK, 108, 60)
    hit(21, 10, 'LH', SNARE, 110, 55)
    for i, p in enumerate(ST16[8:]):
        hit(21, p, 'RH' if i % 2 == 0 else 'LH', d13[i], 106 + i * 2, 60)

    d22 = (TOM_HH, TOM_HI, TOM_HI, TOM_MID,
           TOM_MID, TOM_LO, TOM_LO, FLOOR_H,
           FLOOR_H, FLOOR_L, FLOOR_L, SNARE,
           SNARE, SNARE, SNARE, SNARE)
    fill16(22, d22, base=94, step=1.0, accent=28, kvel=114)

    # ======================================================================
    # 4) BUILD -- bars 23-30.  Motif B arrives, everything tightens up.
    # ======================================================================
    FEEL, DYN = 0, 1.00

    groove(23, rvel=80, svel=108, kvel=106, kick=(0, 20), snare=(10, 30),
           pedal=(10, 30), crash=CRASH2, ride_accent=10, skip=(20, 30))
    motifB(23, 20, 104)

    groove(24, rvel=82, svel=110, kvel=108, kick=(0, 16, 20), snare=(10,),
           ghosts=(3, 23), pedal=(10, 30), skip=(20, 30))
    motifB(24, 20, 108)

    # bars 25-26: motif B fills the whole bar, then inverted
    motifB(25, 0, 104)
    motifB(25, 20, 110)
    hit(25, 0, 'RF', KICK, 110, 60)
    hit(25, 20, 'RF', KICK, 112, 60)
    hit(25, 0, 'LF', PEDAL, 72, 50)
    hit(25, 20, 'LF', PEDAL, 72, 50)

    motifB(26, 0, 106, notes=(FLOOR_H, TOM_LO, TOM_MID, TOM_HI))
    motifB(26, 20, 112, notes=(FLOOR_H, TOM_LO, TOM_MID, TOM_HI))
    hit(26, 0, 'RF', KICK, 112, 60)
    hit(26, 20, 'RF', KICK, 112, 60)

    # bars 27-28: rolling swung eighths, snare against toms, crescendo
    roll = (SNARE, TOM_HI, SNARE, TOM_MID, SNARE, TOM_LO, SNARE, FLOOR_H)
    for i, p in enumerate(SW8):
        hit(27, p, 'RH' if i % 2 == 0 else 'LH', roll[i], 96 + i * 3, 55)
    hit(27, 0, 'RF', KICK, 110, 60)
    hit(27, 20, 'RF', KICK, 112, 60)
    hit(27, 0, 'LF', PEDAL, 74, 50)
    hit(27, 20, 'LF', PEDAL, 74, 50)

    for i, p in enumerate(SW8):
        hit(28, p, 'RH' if i % 2 == 0 else 'LH', roll[i], 102 + i * 2, 55)
    hit(28, 0, 'RF', KICK, 112, 60)
    hit(28, 20, 'RF', KICK, 114, 60)

    # bars 29-30: straight sixteenths, accents on the downbeats
    d29 = (SNARE,) * 4 + (TOM_HH,) * 4 + (TOM_MID,) * 4 + (TOM_LO,) * 4
    fill16(29, d29, base=78, step=1.0, accent=32, kvel=112)

    d30 = (TOM_HH, TOM_HI, TOM_HI, TOM_MID,
           TOM_MID, TOM_LO, TOM_LO, FLOOR_H,
           FLOOR_H, FLOOR_L, FLOOR_L, FLOOR_H,
           TOM_LO, TOM_MID, TOM_HI, SNARE)
    fill16(30, d30, base=82, step=1.2, accent=30, kvel=116)

    # ======================================================================
    # 5) PEAK -- bars 31-36.  Pushing ahead, loudest.
    # ======================================================================
    FEEL, DYN = -5, 1.00

    groove(31, rvel=86, svel=116, kvel=112, kick=(0, 20), snare=(10, 30),
           pedal=(10, 30), crash=CRASH, ride_accent=12, ped_vel=76)

    groove(32, rvel=86, svel=116, kvel=112, kick=(0, 16, 20), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30), skip=(20, 30), ride_accent=12)
    motifB(32, 20, 112)

    groove(33, rvel=88, svel=116, kvel=114, kick=(0, 20), snare=(10, 30),
           pedal=(10, 30), crash=CRASH2, bell=True, ride_accent=6)

    groove(34, rvel=88, svel=116, kvel=114, kick=(0, 16, 20, 26),
           snare=(10, 30), ghosts=(3, 23), pedal=(10, 30), ride_accent=12)
    hit(34, 32.5, 'LH', SNARE, 78, 40)
    hit(34, 35, 'LH', SNARE, 86, 40)

    d35 = (SNARE, SNARE, TOM_HH, TOM_HI,
           TOM_HI, TOM_MID, TOM_MID, TOM_LO,
           TOM_MID, TOM_LO, FLOOR_H, FLOOR_H,
           FLOOR_L, FLOOR_L, FLOOR_H, SNARE)
    fill16(35, d35, base=78, step=1.0, accent=34, kvel=116)

    d36 = (FLOOR_L, FLOOR_H, FLOOR_H, TOM_LO,
           TOM_LO, TOM_MID, TOM_MID, TOM_HI,
           TOM_HI, TOM_HH, SNARE, SNARE,
           SNARE, SNARE, SNARE, SNARE)
    fill16(36, d36, base=82, step=1.0, accent=32, kvel=118)

    # ======================================================================
    # 6) BREAKDOWN -- bars 37-40.  Sudden space, way behind the beat.
    # ======================================================================
    FEEL, DYN = 14, 0.72

    hit(37, 0, 'LH', RIM, 84, 55)
    hit(37, 10, 'LF', PEDAL, 62, 50)
    hit(37, 20, 'LH', RIM, 88, 55)
    hit(37, 30, 'LF', PEDAL, 62, 50)

    hit(38, 0, 'LH', RIM, 86, 55)
    hit(38, 16, 'LH', RIM, 82, 55)
    hit(38, 20, 'LF', PEDAL, 64, 50)
    hit(38, 26, 'LH', RIM, 90, 55)
    hit(38, 36, 'RF', KICK, 70, 60)

    swing_ride(39, 52, note=HAT, skip=(16, 36))
    hit(39, 36, 'RH', HAT_OP, 78, 150)
    hit(39, 0, 'LH', RIM, 88, 55)
    hit(39, 10, 'LH', RIM, 84, 55)
    hit(39, 16, 'LH', TOM_LO, 76, 70)
    hit(39, 26, 'LH', RIM, 90, 55)
    hit(39, 10, 'LF', PEDAL, 64, 50)
    hit(39, 30, 'LF', PEDAL, 64, 50)

    # bar 40: crescendo back up, straight into the return
    FEEL, DYN = 8, 1.0
    d40 = (SNARE, SNARE, TOM_HH, TOM_HH,
           TOM_HI, TOM_HI, TOM_MID, TOM_MID,
           TOM_MID, TOM_LO, TOM_LO, FLOOR_H,
           FLOOR_H, FLOOR_L, FLOOR_L, SNARE)
    fill16(40, d40, base=62, step=2.0, accent=20, kvel=110)

    # ======================================================================
    # 7) RETURN -- bars 41-46.  Motif A again, biggest yet.
    # ======================================================================
    FEEL, DYN = 0, 1.04

    groove(41, rvel=88, svel=116, kvel=114, kick=(0, 20), snare=(10, 30),
           pedal=(10, 30), crash=CRASH, ride_accent=12, ped_vel=78)

    groove(42, rvel=88, svel=116, kvel=114, kick=(0, 16, 20), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30), ride_accent=12)

    groove(43, rvel=90, svel=116, kvel=116, kick=(0, 20, 36), snare=(10, 30),
           ghosts=(3, 23), pedal=(10, 30), crash=CRASH2, bell=True,
           ride_accent=6)

    groove(44, rvel=88, svel=116, kvel=116, kick=(0, 16, 20), snare=(10,),
           ghosts=(3, 23), pedal=(10, 30), skip=(20, 30))
    motifB(44, 20, 116)

    d45 = (SNARE, SNARE, TOM_HH, TOM_HI,
           TOM_HI, TOM_MID, TOM_MID, TOM_LO,
           TOM_MID, TOM_LO, FLOOR_H, FLOOR_H,
           FLOOR_L, FLOOR_L, FLOOR_H, SNARE)
    fill16(45, d45, base=80, step=1.0, accent=34, kvel=118)

    d46 = (TOM_HH, TOM_HI, TOM_HI, TOM_MID,
           TOM_MID, TOM_LO, TOM_LO, FLOOR_H,
           FLOOR_H, FLOOR_L, FLOOR_L, FLOOR_H,
           TOM_LO, TOM_MID, TOM_HI, SNARE)
    fill16(46, d46, base=84, step=1.0, accent=32, kvel=118)

    # ======================================================================
    # 8) OUTRO -- bars 47-48.  Last fill, one big hit, let it ring.
    # ======================================================================
    FEEL, DYN = 0, 1.04

    d47 = (SNARE, SNARE, TOM_HH, TOM_HI,
           TOM_HI, TOM_MID, TOM_MID, TOM_LO,
           FLOOR_H, FLOOR_H, FLOOR_L, FLOOR_L,
           TOM_LO, TOM_MID, TOM_HI, SNARE)
    fill16(47, d47, base=80, step=1.0, accent=34, kvel=120)

    hit(48, 0, 'RH', CRASH, 120, 1700)     # rings out to the end
    hit(48, 0, 'LH', SNARE, 118, 60)
    hit(48, 0, 'RF', KICK, 120, 60)
    hit(48, 0, 'LF', PEDAL, 84, 50)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def build():
    compose()

    # a limb can only strike one thing at a time: collapse true duplicates
    picked = {}
    for e in EVENTS:
        k = (e[0], e[1])
        cur = picked.get(k)
        if cur is None or e[3] > cur[3]:
            picked[k] = e
    evs = sorted(picked.values(), key=lambda e: (e[0], e[1]))

    # turn every strike into a note on / note off pair, shortening a note
    # whenever the same percussion sound is struck again before it ends
    by_note = {}
    for e in evs:
        by_note.setdefault(e[2], []).append(e)

    msgs = []
    for note, lst in by_note.items():
        lst.sort(key=lambda x: x[0])
        for i, e in enumerate(lst):
            t, _voice, n, vel, dur = e
            off = t + dur
            if i + 1 < len(lst):
                off = min(off, lst[i + 1][0] - 1)
            if off <= t:
                off = t + 1
            msgs.append((t, 1, n, vel))
            msgs.append((off, 0, n, 0))

    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    track = mido.MidiTrack()
    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('set_tempo', tempo=TEMPO, time=0))
    track.append(mido.MetaMessage('time_signature', numerator=4,
                                  denominator=4, time=0))

    last = 0
    for t, is_on, n, vel in msgs:
        d = t - last
        if d < 0:
            d = 0
        if is_on:
            track.append(mido.Message('note_on', channel=9, note=n,
                                      velocity=vel, time=d))
        else:
            track.append(mido.Message('note_off', channel=9, note=n,
                                      velocity=0, time=d))
        last = t

    track.append(mido.MetaMessage('end_of_track',
                                  time=max(0, END_TICK - last)))

    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(track)
    mid.save('solo.mid')

    # small report (stdout only, the .mid is unaffected)
    peak = {}
    for e in evs:
        peak[e[0]] = peak.get(e[0], 0) + 1
    print('wrote solo.mid : %d strikes, %d messages, max %d simultaneous '
          'strikes, length %.2f s'
          % (len(evs), len(msgs), max(peak.values()),
             END_TICK / float(TPB) * (TEMPO / 1000000.0)))


if __name__ == '__main__':
    build()
