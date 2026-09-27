#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid, a two minute General MIDI drum solo
on MIDI channel 10 (mido only).

Design notes
------------
* Tempo is a constant 120 BPM, 4/4, 60 bars == exactly 120.0 seconds.
* A two-beat motif ("A": hi tom, mid tom, low tom, mid tom, floor tom) is
  stated, answered on congas / wood blocks / timbales / bongos, turned
  retrograde, augmented, displaced onto the feet, and brought back loud in
  the climax and the finale.
* Feel is deliberate and consistent: shuffle swing on the eighth-note ride /
  hat patterns, kick slightly ahead of the beat, snare and hats slightly
  behind it, and quiet ghost notes written against the accents.
* Dynamics are shaped inside phrases (crescendos across bars, accents on the
  beat, ghosts in the gaps) rather than by making whole blocks louder.
* Everything is playable by one drummer: never more than two hands or two
  feet striking at the same instant (verified and enforced before writing).
"""

import mido

TPQ = 480
BPM = 120.0
TEMPO_US = int(60_000_000 / BPM)          # 500000
TOTAL_TICKS = 240 * TPQ                   # 60 bars of 4/4 = 120.0 s
SWING = 2.0 / 3.0                         # eighth-note swing ratio

# --------------------------------------------------------------------------
# General MIDI percussion (notes 35-81)
# --------------------------------------------------------------------------
KICK = 36
KICK2 = 35
SNARE = 38
STICK = 37
CLAP = 39
ESNARE = 40
FL_LOW = 41
CH = 42          # closed hi-hat
FL_HI = 43
PH = 44          # pedal hi-hat
T_LOWMID = 45
OH = 46          # open hi-hat
T_LOW = 47
T_MID = 48
CRASH = 49
T_HI = 50
RIDE = 51
CHINA = 52
BELL = 53        # ride bell
TAMB = 54
SPLASH = 55
COWBELL = 56
CRASH2 = 57
VIBRA = 58
RIDE2 = 59
BONGO_H = 60
BONGO_L = 61
CONGA_MUTE = 62
CONGA_OPEN = 63
CONGA_LOW = 64
TIMB_H = 65
TIMB_L = 66
AGOGO_H = 67
AGOGO_L = 68
CABASA = 69
MARACAS = 70
WHISTLE_S = 71
WHISTLE_L = 72
GUIRO_S = 73
GUIRO_L = 74
CLAVES = 75
WB_HI = 76
WB_LO = 77
CUICA_M = 78
CUICA_O = 79
TRI_M = 80
TRI = 81

FEET = frozenset((KICK, KICK2, PH))

# Micro-timing: the kick pushes a hair, the snare and cymbals lay back a
# hair.  Consistent from first note to last, so the solo has one pocket.
FEEL = {
    KICK: -4, KICK2: -4,
    SNARE: 4, STICK: 4, ESNARE: 4, CLAP: 4,
    CH: 5, OH: 5, PH: 3,
    RIDE: 1, RIDE2: 1, BELL: 1,
}

events = []          # (tick, note, velocity, duration_ticks)


def hit(pos, note, vel, dur=0.10):
    """Add a stroke at `pos` beats (quarter notes) from the start."""
    tick = int(round(pos * TPQ)) + FEEL.get(note, 0)
    if tick < 0:
        tick = 0
    v = int(round(vel))
    v = 1 if v < 1 else (127 if v > 127 else v)
    d = int(round(dur * TPQ))
    events.append((tick, note, v, d if d > 10 else 10))


# --------------------------------------------------------------------------
# The motif and its orchestrations
# --------------------------------------------------------------------------
MOTIF_OFF = (0.0, 0.5, 0.75, 1.5, 1.75)
MOTIF_ACC = (1.00, 0.78, 0.90, 0.72, 0.94)

V_TOMS = (T_HI, T_MID, T_LOW, T_MID, FL_HI)
V_TOMS_R = (FL_LOW, FL_HI, T_LOW, T_LOWMID, T_HI)
V_CONGA = (CONGA_OPEN, CONGA_MUTE, CONGA_LOW, CONGA_MUTE, CONGA_LOW)
V_BONGO = (BONGO_H, BONGO_L, BONGO_H, BONGO_L, BONGO_H)
V_TIMB = (TIMB_H, TIMB_L, TIMB_H, TIMB_L, TIMB_H)
V_WOOD = (WB_HI, WB_LO, WB_HI, WB_LO, WB_HI)
V_COW = (COWBELL, COWBELL, COWBELL, COWBELL, COWBELL)


def motif(pos, voices, vel=100, dur=0.22):
    for off, acc in zip(MOTIF_OFF, MOTIF_ACC):
        i = MOTIF_OFF.index(off)
        hit(pos + off, voices[i], vel * acc, dur)


def hats_run(pos0, n, vel=72, cresc=0.0, voice=CH, open_last=False,
             accent_last=False):
    """n swung eighths (shuffle feel) starting at integer beat pos0."""
    for k in range(n):
        if k % 2:
            p = pos0 + (k // 2) + SWING
        else:
            p = pos0 + (k // 2)
        v = vel * (1.0 + cresc * (k / max(1, n - 1)))
        if k % 2 == 0:
            v *= 1.10
        if open_last and k == n - 1:
            hit(p, OH, v * 1.15, dur=0.5)
        elif accent_last and k == n - 1:
            hit(p, voice, v * 1.20)
        else:
            hit(p, voice, v)


def fill16(bar, start, notes, v0, v1, spacing=0.25):
    """A run of 16ths (or other spacing) across a bar with a crescendo."""
    n = len(notes)
    for i, note in enumerate(notes):
        p = bar * 4 + start + i * spacing
        v = v0 + (v1 - v0) * (i / max(1, n - 1))
        hit(p, note, v)


def groove_bar(bar, i=1.0, hat_vel=74, hat_cresc=0.0, kick=(0.0, 2.5),
               ghost=True, open4=False, crash=False, snare_vel=106):
    """One bar of the shuffling main groove."""
    b = bar * 4
    if crash:
        hit(b + 0.0, CRASH, 112 * i, dur=2.0)
    hats_run(b, 8, vel=hat_vel * i, cresc=hat_cresc, open_last=open4)
    for kp in kick:
        hit(b + kp, KICK, 98 * i)
    hit(b + 1.0, SNARE, snare_vel * i)
    hit(b + 3.0, SNARE, min(121.0, snare_vel * 1.04) * i)
    if ghost:
        hit(b + 1.25, SNARE, 26 * i)
        hit(b + 3.25, SNARE, 32 * i)


def groove16(bar, ride_vel=80, kicks=(0.0, 2.0), snares=(1.0, 3.0),
             snare_vel=110, ghost=True, crash=False, ph=(), accent=16):
    """One bar of the straight driving sixteenth-note ride groove."""
    b = bar * 4
    if crash:
        hit(b + 0.0, CRASH, 122, dur=2.2)
    for k in range(16):
        v = ride_vel + (accent if k % 4 == 0 else 0) - (6 if k % 2 else 0)
        hit(b + k * 0.25, RIDE, v)
    for kp in kicks:
        hit(b + kp, KICK, 108)
    for sb in snares:
        hit(b + sb, SNARE, snare_vel)
    if ghost:
        hit(b + 1.75, SNARE, 30)
        hit(b + 3.75, SNARE, 34)
    for p in ph:
        hit(b + p, PH, 62)


# --------------------------------------------------------------------------
# The solo
# --------------------------------------------------------------------------
def build():
    # ===================== S1  INTRO  (bars 0-5, 0:00-0:12) ===============
    hit(0.0, CRASH, 114, dur=2.2)
    hit(0.0, KICK, 112)
    motif(0.0, V_TOMS, 104)                    # motif A: statement
    hit(2.0, KICK, 98)
    motif(2.0, V_TOMS, 94)                     # A again, softer

    hit(4.0, KICK, 92)
    motif(4.0, V_CONGA, 88)                    # A on congas
    hit(5.0, PH, 66)
    motif(6.0, V_WOOD, 74)                     # A whispered on wood blocks
    hit(7.0, PH, 62)

    # bar 2: a hole, then a low pickup into the groove
    hit(10.0, KICK, 104)
    hit(10.75, SNARE, 34)
    hit(11.0, SNARE, 100)
    hit(11.5, CH, 62)
    hit(11.75, SNARE, 28)

    groove_bar(3, 0.94, hat_vel=68, kick=(0.0, 2.5))
    groove_bar(4, 1.00, hat_vel=72, kick=(0.0, 2.5, 3.5), open4=True)

    # bar 5: half groove then a rising tom fill into the chorus
    hats_run(20.0, 4, vel=74)
    hit(20.0, KICK, 104)
    hit(21.0, SNARE, 106)
    hit(21.25, SNARE, 30)
    hit(22.0, KICK, 102)
    fill16(5, 2.0, [T_HI, T_HI, T_MID, T_MID,
                    T_LOW, T_LOW, FL_HI, FL_HI], 72, 104)

    # ===================== S2  GROOVE  (bars 6-17, 0:12-0:36) =============
    # phrase 1
    groove_bar(6, 1.00, hat_vel=76, kick=(0.0, 2.5), crash=True)
    groove_bar(7, 1.00, hat_vel=74, kick=(0.0, 2.5))
    groove_bar(8, 1.02, hat_vel=76, kick=(0.0, 2.5, 3.5), open4=True)
    # bar 9: groove, then motif A as the fill
    hats_run(36.0, 4, vel=78)
    hit(36.0, KICK, 106)
    hit(37.0, SNARE, 108)
    hit(37.25, SNARE, 30)
    hit(38.0, KICK, 100)
    motif(38.0, V_TOMS, 100)

    # phrase 2
    groove_bar(10, 1.02, hat_vel=78, kick=(0.0, 1.5, 2.5), crash=True)
    groove_bar(11, 1.03, hat_vel=78, kick=(0.0, 2.5))
    # bar 12: snare sings the motif, with ghosts under the accents
    hats_run(44.0, 4, vel=80)
    hit(44.0, KICK, 106)
    hit(45.0, SNARE, 110)
    hit(45.25, SNARE, 32)
    hit(46.0, KICK, 102)
    for off, v in ((0.0, 108), (0.5, 40), (0.75, 62), (1.5, 36), (1.75, 96)):
        hit(46.0 + off, SNARE, v, dur=0.16)
    # bar 13: timbale fill with a splash
    hats_run(52.0, 4, vel=80)
    hit(52.0, KICK, 106)
    hit(52.0, SPLASH, 88, dur=1.0)
    hit(53.0, SNARE, 110)
    hit(53.25, SNARE, 34)
    hit(54.0, KICK, 102)
    fill16(13, 2.0, [TIMB_H, TIMB_L, TIMB_H, TIMB_L,
                     TIMB_H, TIMB_L, SNARE, SNARE], 76, 112)

    # phrase 3 -- the groove section peaks
    groove_bar(14, 1.06, hat_vel=82, kick=(0.0, 2.5), crash=True)
    groove_bar(15, 1.06, hat_vel=82, kick=(0.0, 1.5, 2.5), open4=True)
    groove_bar(16, 1.08, hat_vel=84, kick=(0.0, 2.5))
    for k in range(4):                       # sixteenth-note foot burst
        hit(64.0 + 3.0 + k * 0.25, KICK, 62 + k * 10)
    # bar 17: big fill into the development
    hats_run(68.0, 4, vel=84)
    hit(68.0, KICK, 108)
    hit(69.0, SNARE, 112)
    hit(70.0, KICK, 104)
    fill16(17, 2.0, [T_HI, T_MID, T_LOW, FL_HI,
                     FL_LOW, SNARE, SNARE, SNARE], 84, 118)

    # ================ S3  DEVELOPMENT  (bars 18-31, 0:36-1:04) ============
    hit(72.0, CRASH, 116, dur=2.0)
    hit(72.0, KICK, 110)
    motif(72.0, V_TOMS, 106)
    hit(74.0, KICK, 104)
    motif(74.0, V_TOMS, 100)

    # bar 19: A in retrograde, landing on the backbeat
    motif(76.0, V_TOMS_R, 100)
    hit(76.0, KICK, 104)
    hit(77.0, PH, 68)
    hit(78.0, KICK, 100)
    hit(78.0 + SWING, CH, 72)
    hit(79.0, SNARE, 106)
    hit(79.75, SNARE, 32)

    # bar 20: A traded between congas and bongos
    motif(80.0, V_CONGA, 96)
    hit(80.0, KICK, 100)
    hit(81.0, PH, 66)
    motif(82.0, V_BONGO, 92)
    hit(82.0, KICK, 96)
    hit(83.0, PH, 62)

    # bar 21: the feet answer with the motif while the hands keep time
    for off, v in ((0.0, 100), (0.5, 80), (0.75, 92), (1.5, 72), (1.75, 96)):
        hit(84.0 + off, KICK, v)
    hats_run(84.0, 8, vel=76, cresc=0.12)
    hit(85.0, SNARE, 92)
    hit(87.0, SNARE, 96)
    hit(85.25, SNARE, 28)
    hit(87.25, SNARE, 30)

    # bar 22: A augmented (half time), big and open
    for off, note, v in ((0.0, T_HI, 108), (1.0, T_MID, 88), (1.5, T_LOW, 96),
                         (3.0, FL_HI, 84), (3.5, FL_LOW, 104)):
        hit(88.0 + off, note, v)
    hit(88.0, KICK, 108)
    hit(90.0, KICK, 100)
    hit(91.0, PH, 72)

    # bar 23: straight sixteenths -- the feel doubles
    for k in range(16):
        hit(92.0 + k * 0.25, CH,
            66 + (12 if k % 4 == 0 else 0) - (6 if k % 2 else 0))
    for off in (0.0, 0.75, 2.5, 3.25):
        hit(92.0 + off, KICK, 100)
    hit(93.0, SNARE, 108)
    hit(95.0, SNARE, 112)
    hit(93.75, SNARE, 30)
    hit(95.75, SNARE, 34)

    # bar 24: hands call (accent grid on the snare)
    for k in range(16):
        v = 104 if k % 4 == 0 else (58 if k % 2 == 0 else 34)
        hit(96.0 + k * 0.25, SNARE, v, dur=0.12)
    hit(96.0, KICK, 106)
    hit(98.0, KICK, 106)
    hit(96.0, PH, 60)

    # bar 25: feet answer (sixteenth kick burst under the hats)
    hats_run(100.0, 8, vel=74)
    for k in range(8):
        hit(100.0 + k * 0.25, KICK, 96 if k % 4 == 0 else 74)
    hit(101.0, SNARE, 96)
    hit(103.0, SNARE, 102)
    hit(101.25, SNARE, 30)
    hit(103.25, SNARE, 32)

    # bars 26-27: full sixteenth ride, displaced backbeats
    groove16(26, ride_vel=78, kicks=(0.0, 0.75, 2.0, 2.5),
             snares=(1.0, 3.0), crash=True)
    groove16(27, ride_vel=80, kicks=(0.0, 1.0, 2.0, 3.0),
             snares=(1.5, 3.5), ghost=False)

    # bar 28: motif doubled by the bass drum, then hands/feet trade
    hit(112.0, CRASH, 112, dur=2.0)
    for off, note, v, kd in ((0.0, T_HI, 106, True), (0.5, T_MID, 82, False),
                             (0.75, T_LOW, 92, True), (1.5, T_MID, 76, False),
                             (1.75, FL_HI, 98, True)):
        hit(112.0 + off, note, v)
        if kd:
            hit(112.0 + off, KICK, 104)
    for off, note, v in ((2.0, T_LOWMID, 96), (2.5, SNARE, 108),
                         (2.75, T_LOW, 86), (3.0, SNARE, 110),
                         (3.25, T_HI, 80), (3.5, SNARE, 104),
                         (3.75, SNARE, 88)):
        hit(112.0 + off, note, v)
    hit(114.0, KICK, 100)
    hit(115.0, KICK, 96)

    # bar 29
    hats_run(116.0, 4, vel=80)
    hit(116.0, KICK, 108)
    hit(117.0, SNARE, 110)
    hit(117.25, SNARE, 30)
    hit(118.0, KICK, 104)
    fill16(29, 2.0, [T_HI, T_MID, T_LOW, FL_HI,
                     FL_LOW, FL_LOW, SNARE, SNARE], 88, 118)

    # bar 30: peak statement of the development
    hit(120.0, CRASH, 120, dur=2.2)
    hit(120.0, KICK, 114)
    motif(120.0, V_TOMS, 110)
    hit(122.0, KICK, 108)
    hit(122.0, CHINA, 106, dur=1.2)
    motif(122.0, V_TOMS_R, 106)

    # bar 31: subito piano -- space before the breakdown
    hit(124.0, KICK, 80)
    hit(125.0, PH, 58)
    hit(126.0, STICK, 66)
    hit(126.0, KICK, 74)
    hit(127.0, PH, 54)

    # ================= S4  BREAKDOWN  (bars 32-39, 1:04-1:20) =============
    for bar in (32, 33, 34, 35):
        b = bar * 4
        for k in range(4):
            hit(b + k, BELL, 76 + (8 if k % 2 == 0 else 0), dur=0.35)
        hit(b + 0.0, KICK, 86)
        hit(b + 2.0, SNARE, 92)
        hit(b + 2.25, SNARE, 26)
        hit(b + 1.0, PH, 60)
        hit(b + 3.0, PH, 56)
    # the theme whispered back on wood blocks
    for off, note, v in ((0.0, WB_HI, 60), (0.5, WB_LO, 48), (0.75, WB_HI, 54)):
        hit(33 * 4 + 3.0 + off, note, v)
    hit(32 * 4 + 3.5, TRI, 62, dur=0.6)
    hit(34 * 4 + 3.5, TRI, 66, dur=0.6)
    for off, note, v in ((0.0, WB_HI, 64), (0.5, WB_LO, 52), (0.75, WB_HI, 58)):
        hit(35 * 4 + 3.0 + off, note, v)

    # bars 36-37: rebuild, hats return with a crescendo
    for bar in (36, 37):
        b = bar * 4
        hats_run(b, 8, vel=70 + 6 * (bar - 36), cresc=0.25)
        hit(b + 0.0, KICK, 98)
        hit(b + 2.0, PH, 62)
        hit(b + 2.5, KICK, 90)
        hit(b + 1.0, SNARE, 102)
        hit(b + 3.0, SNARE, 106)
        hit(b + 1.25, SNARE, 28)
        hit(b + 3.25, SNARE, 32)

    # bars 38-39: roll crescendo landing on the climax downbeat
    for k in range(16):
        hit(152.0 + k * 0.25, SNARE, min(112.0, 46 + k * 3), dur=0.09)
    for k in range(32):
        hit(156.0 + k * 0.125, SNARE, min(126.0, 92 + k), dur=0.07)
    hit(152.0, KICK, 100)
    hit(156.0, KICK, 104)
    hit(158.0, KICK, 108)

    # =================== S5  CLIMAX  (bars 40-53, 1:20-1:48) ==============
    groove16(40, kicks=(0.0, 0.75, 2.0, 2.5), crash=True, ph=(3.0,))
    groove16(41, kicks=(0.0, 0.75, 2.0))
    groove16(42, kicks=(0.0, 0.75, 1.5, 2.0, 3.5))

    # bar 43: snare sixteenths then a tom run
    for k in range(8):
        v = 108 if k % 4 == 0 else (58 if k % 2 == 0 else 36)
        hit(172.0 + k * 0.25, SNARE, v, dur=0.12)
    hit(172.0, KICK, 108)
    hit(173.0, KICK, 100)
    hit(174.0, KICK, 104)
    hit(175.0, KICK, 108)
    fill16(43, 2.0, [T_HI, T_HI, T_MID, T_MID,
                     T_LOW, T_LOW, FL_HI, FL_HI], 88, 112)

    # bar 44: displaced backbeat over the ride, motif on the feet
    groove16(44, kicks=(0.0, 0.75, 2.0, 2.5), crash=True)

    # bar 45: hands swap -- motif on the toms, ghosts on the snare
    b = 180.0
    hit(b, CRASH, 116, dur=2.0)
    hit(b, KICK, 112)
    for off, note, v in zip(MOTIF_OFF, V_TOMS, (106, 84, 94, 78, 100)):
        hit(b + off, note, v)
    for off, note, v in ((2.0, SNARE, 110), (2.25, SNARE, 44),
                         (2.5, T_MID, 92), (2.75, SNARE, 40),
                         (3.0, SNARE, 112), (3.25, T_LOW, 88),
                         (3.5, SNARE, 42), (3.75, SNARE, 100)):
        hit(b + off, note, v)
    hit(b + 2.0, KICK, 108)
    hit(b + 3.0, KICK, 110)

    # bar 46: sixteenth ride plus a sixteenth kick burst
    b = 184.0
    for k in range(16):
        hit(b + k * 0.25, RIDE,
            82 + (14 if k % 4 == 0 else 0) - (8 if k % 2 else 0))
    for k in range(8):
        hit(b + k * 0.25, KICK, 98 if k % 4 == 0 else 78)
    hit(b + 1.0, SNARE, 108)
    hit(b + 3.0, SNARE, 112)
    hit(b + 1.75, SNARE, 30)
    hit(b + 3.75, SNARE, 34)
    hit(b + 2.25, KICK, 96)
    hit(b + 2.5, KICK, 104)
    hit(b + 3.5, KICK, 100)

    # bar 47: fill with a china accent
    b = 188.0
    hit(b, KICK, 110)
    hit(b, SNARE, 108)
    hit(b, CHINA, 104, dur=1.2)
    fill16(47, 0.5, [SNARE, SNARE, T_HI, T_HI, T_MID, T_MID, T_LOW, T_LOW,
                     FL_HI, FL_HI, FL_LOW, FL_LOW, SNARE, SNARE], 84, 118)
    for k in (1.0, 2.0, 3.0):
        hit(b + k, KICK, 106)

    # bars 48-49: the peak chorus
    groove16(48, kicks=(0.0, 0.75, 2.0, 2.5), crash=True, snare_vel=114)
    groove16(49, kicks=(0.0, 0.75, 1.5, 2.0, 3.5), snare_vel=114)

    # bar 50: motif A back in full voice, then inverted
    b = 200.0
    hit(b, CRASH, 122, dur=2.4)
    hit(b, KICK, 116)
    motif(b, V_TOMS, 112)
    hit(b + 2.0, KICK, 112)
    motif(b + 2.0, V_TOMS_R, 108)

    # bar 51: half ride then a rising snare pickup
    b = 204.0
    for k in range(8):
        hit(b + k * 0.25, RIDE,
            82 + (14 if k % 4 == 0 else 0) - (8 if k % 2 else 0))
    hit(b + 0.0, KICK, 112)
    hit(b + 0.75, KICK, 100)
    hit(b + 1.0, SNARE, 114)
    for k in range(8):
        hit(b + 2.0 + k * 0.25, SNARE, 66 + k * 8, dur=0.10)
    hit(b + 2.0, KICK, 110)
    hit(b + 3.0, KICK, 112)

    # bars 52-53: the last big fill
    b = 208.0
    hit(b, KICK, 112)
    hit(b, SNARE, 110)
    fill16(52, 0.5, [SNARE, SNARE, SNARE, SNARE, T_HI, T_HI, T_MID, T_MID,
                     T_LOW, T_LOW, FL_HI, FL_HI, FL_LOW, FL_LOW], 86, 118)
    hit(b + 1.0, KICK, 106)
    hit(b + 2.0, KICK, 110)
    hit(b + 3.0, KICK, 110)

    b = 212.0
    fill16(53, 0.0, [FL_LOW, FL_LOW, FL_HI, FL_HI, T_LOW, T_LOW, T_MID, T_MID,
                     T_HI, T_HI, T_MID, T_MID, T_LOW, T_LOW, SNARE, SNARE],
           92, 124)
    hit(b + 0.0, KICK, 112)
    hit(b + 1.0, KICK, 108)
    hit(b + 2.0, KICK, 112)
    hit(b + 3.0, KICK, 110)

    # ==================== S6  FINALE  (bars 54-59, 1:48-2:00) =============
    # bar 54: last chorus of the theme
    b = 216.0
    hit(b, CRASH, 124, dur=2.4)
    hit(b, KICK, 118)
    motif(b, V_TOMS, 116)
    hit(b + 2.0, KICK, 112)
    motif(b + 2.0, V_TOMS_R, 112)

    # bar 55: theme doubled by the bass drum, then snare/tom trade
    b = 220.0
    for off, note, v, kd in ((0.0, T_HI, 118, True), (0.5, T_MID, 92, False),
                             (0.75, T_LOW, 104, True), (1.5, T_MID, 86, False),
                             (1.75, FL_HI, 110, True)):
        hit(b + off, note, v)
        if kd:
            hit(b + off, KICK, 112)
    for off, note, v in ((2.0, SNARE, 116), (2.5, T_LOW, 100),
                         (3.0, SNARE, 118), (3.5, SNARE, 104),
                         (3.75, SNARE, 112)):
        hit(b + off, note, v)
    hit(b + 2.0, KICK, 112)
    hit(b + 3.0, KICK, 112)

    # bar 56: descending tom run
    b = 224.0
    fill16(56, 0.0, [T_HI, T_HI, T_MID, T_MID, T_LOW, T_LOW, FL_HI, FL_HI,
                     FL_LOW, FL_LOW, FL_LOW, FL_LOW, T_LOW, T_LOW,
                     SNARE, SNARE], 96, 124)
    hit(b + 0.0, KICK, 112)
    hit(b + 1.0, KICK, 110)
    hit(b + 2.0, KICK, 112)
    hit(b + 3.0, KICK, 112)

    # bar 57: thirty-second roll, crescendo to the final hit
    b = 228.0
    for k in range(32):
        hit(b + k * 0.125, SNARE, min(126.0, 96 + k), dur=0.07)
    hit(b + 0.0, KICK, 116)
    hit(b + 2.0, KICK, 118)

    # bar 58: LAND IT -- crash, snare and kick together, then ring out
    b = 232.0
    hit(b + 0.0, CRASH, 127, dur=7.5)
    hit(b + 0.0, KICK, 127)
    hit(b + 0.0, SNARE, 122, dur=0.25)


# --------------------------------------------------------------------------
# Playability guard + MIDI writing
# --------------------------------------------------------------------------
def tidy(raw):
    """Merge duplicates, keep at most two hands and two feet per instant."""
    per_tick = {}
    for tick, note, vel, dur in raw:
        slot = per_tick.setdefault(tick, {})
        old = slot.get(note)
        if old is None or old[0] < vel:
            slot[note] = (vel, dur)

    out = []
    for tick in sorted(per_tick):
        slot = per_tick[tick]
        hands = [(n, v) for n, v in slot.items() if n not in FEET]
        feet = [(n, v) for n, v in slot.items() if n in FEET]
        if len(hands) > 2:
            hands.sort(key=lambda item: -item[1][0])
            for note, _ in hands[2:]:
                del slot[note]
        if len(feet) > 2:
            feet.sort(key=lambda item: -item[1][0])
            for note, _ in feet[2:]:
                del slot[note]
        for note, (vel, dur) in slot.items():
            out.append((tick, note, vel, dur))
    out.sort(key=lambda e: (e[0], e[1]))
    return out


def write_midi(evts, path='solo.mid'):
    mid = mido.MidiFile(type=0, ticks_per_beat=TPQ)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4,
                                  time=0))
    track.append(mido.MetaMessage('set_tempo', tempo=TEMPO_US, time=0))

    msgs = []
    for tick, note, vel, dur in evts:
        msgs.append((tick, 1,
                     mido.Message('note_on', channel=9, note=note,
                                  velocity=vel, time=0)))
        msgs.append((tick + dur, 0,
                     mido.Message('note_off', channel=9, note=note,
                                  velocity=0, time=0)))
    msgs.sort(key=lambda item: (item[0], item[1]))

    last = 0
    for tick, _kind, msg in msgs:
        msg.time = tick - last
        last = tick
        track.append(msg)

    # force an exact 120.0 second file
    track.append(mido.MetaMessage('end_of_track', time=TOTAL_TICKS - last))
    mid.save(path)


def main():
    build()
    write_midi(tidy(events))


if __name__ == '__main__':
    main()
