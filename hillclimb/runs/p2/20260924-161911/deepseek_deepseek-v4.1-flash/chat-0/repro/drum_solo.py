#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid: a two minute solo for General MIDI percussion
(MIDI channel 10, notes 35-81).  The output is deterministic -- running
the script always produces a byte identical file.
"""

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage
from collections import defaultdict

# ----------------------------------------------------------------------
#  basic setup
# ----------------------------------------------------------------------
PPQ = 480
BPM = 120.0
CHANNEL = 9                      # MIDI channel 10, zero based

# ----------------------------------------------------------------------
#  General MIDI percussion map
# ----------------------------------------------------------------------
ABD, KICK, STICK, SNARE, CLAP, ESNARE   = 35, 36, 37, 38, 39, 40
LFT, HHCL, HFT, HHPED, LTM, HHOP        = 41, 42, 43, 44, 45, 46
LMT, HMT, CRASH, HTOM, RIDE, CHINA      = 47, 48, 49, 50, 51, 52
BELL, TAMB, SPLASH, COWB, CRASH2, RIDE2 = 53, 54, 55, 56, 57, 59
BONGOH, BONGOL, CONGAM, CONGAO, CONGAL  = 60, 61, 62, 63, 64
TIMBH, TIMBL, AGOGOH, AGOGOL, CABASA, MARACAS = 65, 66, 67, 68, 69, 70
WHISTLE_S, WHISTLE_L, GUIRO_S, GUIRO_L, CLAVE = 71, 72, 73, 74, 75
WOODH, WOODL, CUICAM, CUICAI, TRI_M, TRI_O = 76, 77, 78, 79, 80, 81

# instruments played by a foot (kick drums and the hi-hat pedal)
FOOT_NOTES = frozenset((ABD, KICK, HHPED))

# ----------------------------------------------------------------------
#  score buffer
# ----------------------------------------------------------------------
EV = []          # (beat, note, velocity, duration_in_beats)


def add(beat, note, vel, dur=0.12):
    EV.append((float(beat), int(note), float(vel), float(dur)))


def add_bar(s, seq, vscale=1.0):
    for pos, note, vel, dur in seq:
        add(s + pos, note, vel * vscale, dur)


# ----------------------------------------------------------------------
#  the motif  (call = funky backbeat figure, answer = tom descent)
# ----------------------------------------------------------------------
MOTIF_A = [                       # call
    (0.00, KICK,  112, 0.22),
    (0.50, SNARE,  30, 0.10),     # ghost
    (1.00, SNARE, 116, 0.10),     # beat 2
    (1.50, KICK,   78, 0.22),
    (1.75, SNARE,  40, 0.10),     # ghost
    (2.00, KICK,  104, 0.22),     # beat 3
    (2.75, SNARE,  34, 0.10),     # ghost
    (3.00, SNARE, 120, 0.10),     # beat 4
    (3.50, KICK,   86, 0.22),
    (3.75, SNARE,  44, 0.10),     # ghost
]

MOTIF_A2 = [                      # call, varied ending
    (0.00, KICK,  114, 0.22),
    (0.50, SNARE,  30, 0.10),
    (1.00, SNARE, 118, 0.10),
    (1.50, KICK,   76, 0.22),
    (1.75, SNARE,  42, 0.10),
    (2.00, KICK,  106, 0.22),
    (2.50, KICK,   66, 0.22),
    (2.75, SNARE,  34, 0.10),
    (3.00, SNARE, 122, 0.10),
    (3.25, KICK,   88, 0.22),
    (3.50, SNARE,  38, 0.10),
    (3.75, SNARE,  52, 0.10),
]

MOTIF_B = [                       # answer, toms descend
    (0.00, KICK,  108, 0.22),
    (0.50, SNARE,  32, 0.10),
    (1.00, SNARE, 118, 0.10),
    (1.50, HMT,   100, 0.20),
    (1.75, LMT,    94, 0.20),
    (2.00, LTM,   102, 0.20),
    (2.25, HFT,    94, 0.20),
    (2.50, LFT,   100, 0.20),
    (2.75, LFT,    58, 0.20),
    (3.00, SNARE, 122, 0.10),
    (3.00, KICK,  106, 0.22),
    (3.75, SNARE,  40, 0.10),
]

MOTIF_B2 = [                      # answer, toms ascend
    (0.00, KICK,  110, 0.22),
    (0.50, SNARE,  32, 0.10),
    (1.00, SNARE, 118, 0.10),
    (1.50, LFT,    96, 0.20),
    (1.75, HFT,    98, 0.20),
    (2.00, LTM,   100, 0.20),
    (2.25, LMT,   100, 0.20),
    (2.50, HMT,   100, 0.20),
    (2.75, HTOM,   96, 0.20),
    (3.00, SNARE, 122, 0.10),
    (3.00, KICK,  106, 0.22),
    (3.25, SNARE,  44, 0.10),
    (3.50, KICK,   82, 0.22),
    (3.75, SNARE,  38, 0.10),
]

MOTIF_TOM = [                     # the call, played on toms
    (0.00, KICK,  112, 0.22),
    (0.50, HMT,    60, 0.15),
    (1.00, HMT,   112, 0.15),
    (1.50, KICK,   78, 0.22),
    (1.75, LMT,    60, 0.15),
    (2.00, KICK,  104, 0.22),
    (2.75, LTM,    56, 0.15),
    (3.00, LTM,   116, 0.15),
    (3.50, KICK,   86, 0.22),
    (3.75, HFT,    62, 0.15),
]

TUMBAO = [                        # conga tumbao, one hand only
    (0.00, CONGAL, 88),
    (0.75, CONGAM, 56),
    (1.50, CONGAO, 96),
    (2.00, CONGAM, 54),
    (2.50, CONGAL, 84),
    (3.25, CONGAM, 52),
    (3.50, CONGAO, 92),
]

CLIMAX_KICKS = [
    [(0.00, KICK, 118), (0.75, KICK,  86), (1.50, KICK,  98),
     (2.00, KICK, 114), (2.75, KICK,  88), (3.25, KICK,  92),
     (3.75, KICK,  80)],
    [(0.00, KICK, 116), (0.50, KICK,  82), (1.25, KICK,  96),
     (2.00, KICK, 112), (2.50, KICK,  90), (3.00, KICK,  96),
     (3.50, KICK,  86)],
]

CLIMAX_SNARES = [
    [(1.00, SNARE, 118), (1.75, SNARE, 42), (2.50, SNARE, 48),
     (3.50, SNARE,  46)],
    [(1.00, SNARE, 116), (1.75, SNARE, 44), (2.25, SNARE, 40),
     (3.00, SNARE, 120), (3.75, SNARE, 50)],
]

TOM_CASCADE_A = [HTOM, HTOM, HMT, HMT, LMT, LMT, LTM, LTM,
                 HFT, HFT, LFT, LFT, HFT, LTM, LMT, HMT]
TOM_CASCADE_B = [LFT, LFT, HFT, HFT, LTM, LTM, LMT, LMT,
                 HMT, HMT, HTOM, HTOM, HMT, LMT, LTM, HFT]
FILL_CLIMAX_A = [SNARE, HMT, SNARE, LMT, SNARE, LTM, SNARE, HFT,
                 SNARE, LFT, HMT, LMT, LTM, HFT, LFT, SNARE]
FILL_CLIMAX_B = [SNARE, SNARE, HMT, HMT, LMT, LMT, LTM, LTM,
                 HFT, HFT, LFT, LFT, SNARE, SNARE, LFT, LFT]


# ----------------------------------------------------------------------
#  one bar of groove: hats/ride + hi-hat pedal + a motif
# ----------------------------------------------------------------------
def groove_bar(s, seq, hat_even=HHCL, hat_odd=HHCL, v_even=74, v_odd=56,
               pedal=(74, 78), crash=None, crash_vel=0, vscale=1.0,
               hat_dur=0.14):
    if crash is not None and crash_vel:
        add(s, crash, crash_vel, 2.5)
    for k in range(8):
        note = hat_even if k % 2 == 0 else hat_odd
        vel = (v_even if k % 2 == 0 else v_odd) * vscale
        add(s + 0.5 * k, note, vel, hat_dur)
    add(s + 1.0, HHPED, pedal[0] * vscale, 0.25)
    add(s + 3.0, HHPED, pedal[1] * vscale, 0.25)
    add_bar(s, seq, vscale)


# ----------------------------------------------------------------------
#  1. intro -- quiet ride, ghosts, slow crescendo            (bars  0- 7)
# ----------------------------------------------------------------------
def build_intro():
    for k, v in enumerate((52, 44, 54, 46)):            # bar 0
        add(k, RIDE, v, 0.55)
    add(1, HHPED, 36, 0.25)
    add(3, HHPED, 38, 0.25)

    s = 4                                               # bar 1
    for k, v in enumerate((54, 46, 56, 48)):
        add(s + k, RIDE, v, 0.55)
    add(s + 1, HHPED, 38, 0.25)
    add(s + 3, HHPED, 40, 0.25)
    add(s + 2, KICK, 66, 0.22)

    s = 8                                               # bar 2
    for k, v in enumerate((56, 48, 58, 50)):
        add(s + k, RIDE, v, 0.55)
    add(s + 1, HHPED, 40, 0.25)
    add(s + 3, HHPED, 42, 0.25)
    add(s + 0, KICK, 72, 0.22)
    add(s + 2.5, KICK, 58, 0.22)
    add(s + 1.5, SNARE, 30, 0.10)
    add(s + 3.5, SNARE, 32, 0.10)

    s = 12                                              # bar 3
    for k, v in enumerate((58, 50, 60, 52)):
        add(s + k, RIDE, v, 0.55)
    add(s + 1, HHPED, 42, 0.25)
    add(s + 3, HHPED, 44, 0.25)
    add(s + 0, KICK, 74, 0.22)
    add(s + 2.5, KICK, 60, 0.22)
    add(s + 1.5, SNARE, 32, 0.10)
    add(s + 3.5, SNARE, 34, 0.10)

    s = 16                                              # bar 4
    for k in range(8):
        add(s + 0.5 * k, RIDE, 60 if k % 2 == 0 else 46, 0.30)
    add(s + 1, HHPED, 42, 0.25)
    add(s + 3, HHPED, 44, 0.25)
    add(s + 0, KICK, 76, 0.22)
    add(s + 2.75, KICK, 60, 0.22)
    add(s + 1.5, SNARE, 32, 0.10)
    add(s + 3.25, SNARE, 30, 0.10)
    add(s + 3.75, SNARE, 36, 0.10)

    s = 20                                              # bar 5
    for k in range(8):
        add(s + 0.5 * k, RIDE, 62 if k % 2 == 0 else 48, 0.30)
    add(s + 1, HHPED, 44, 0.25)
    add(s + 3, HHPED, 46, 0.25)
    add(s + 0, KICK, 78, 0.22)
    add(s + 2, KICK, 66, 0.22)
    add(s + 3.5, KICK, 58, 0.22)
    add(s + 1.25, SNARE, 30, 0.10)
    add(s + 1.75, SNARE, 34, 0.10)
    add(s + 3.75, SNARE, 34, 0.10)

    s = 24                                              # bar 6
    for k in range(8):
        add(s + 0.5 * k, RIDE, 68 if k % 2 == 0 else 50, 0.30)
    add(s + 1, HHPED, 46, 0.25)
    add(s + 3, HHPED, 48, 0.25)
    add(s + 0, KICK, 82, 0.22)
    add(s + 2.5, KICK, 68, 0.22)
    add(s + 1, SNARE, 78, 0.10)
    add(s + 3, SNARE, 86, 0.10)
    add(s + 1.75, SNARE, 34, 0.10)
    add(s + 3.75, SNARE, 38, 0.10)

    s = 28                                              # bar 7 - fill
    add(s + 0, KICK, 88, 0.22)
    add(s + 2, KICK, 82, 0.22)
    add(s + 1, HHPED, 48, 0.25)
    add(s + 3, HHPED, 50, 0.25)
    for i in range(5):
        add(s + 0.75 + 0.25 * i, SNARE, 56 + 8 * i, 0.09)
    run = [(2.00, HMT, 84), (2.25, LMT, 88), (2.50, LTM, 92),
           (2.75, HFT, 96), (3.00, LFT, 100), (3.25, LFT, 104),
           (3.50, LFT, 70), (3.75, SNARE, 96)]
    for pos, note, vel in run:
        add(s + pos, note, vel, 0.10 if note == SNARE else 0.18)


# ----------------------------------------------------------------------
#  2. the motif stated                                     (bars  8-15)
# ----------------------------------------------------------------------
def build_statement():
    s = 32
    groove_bar(s + 0,  MOTIF_A,  crash=CRASH, crash_vel=104)
    groove_bar(s + 4,  MOTIF_B)
    groove_bar(s + 8,  MOTIF_A,  v_even=76, v_odd=58)
    groove_bar(s + 12, MOTIF_B2)
    groove_bar(s + 16, MOTIF_B)                 # answer first: retrograde
    groove_bar(s + 20, MOTIF_A2)

    b = s + 24                                  # bar 14 - sixteenth build
    for k in range(16):
        v = 88 if k % 4 == 0 else (66 if k % 2 == 0 else 52)
        add(b + 0.25 * k, SNARE, v, 0.09)
    add(b + 0, KICK, 98, 0.22)
    add(b + 2, KICK, 92, 0.22)
    add(b + 1, HHPED, 70, 0.25)
    add(b + 3, HHPED, 72, 0.25)

    b = s + 28                                  # bar 15 - tom fill
    add(b + 0, KICK, 100, 0.22)
    toms = [HMT, LMT, LTM, HFT, LFT, LFT]
    for i in range(12):
        pos = 0.5 + 0.25 * i
        note = toms[min(i // 2, 5)]
        add(b + pos, note, 78 + i * 3, 0.16)
    add(b + 2.5, KICK, 96, 0.22)
    add(b + 3.5, SNARE, 108, 0.10)
    add(b + 3.75, LFT, 110, 0.16)


# ----------------------------------------------------------------------
#  3. developing the motif                                 (bars 16-23)
# ----------------------------------------------------------------------
def build_development():
    s = 64
    groove_bar(s + 0,  MOTIF_A, hat_even=RIDE, hat_odd=RIDE,
               v_even=78, v_odd=58, crash=CRASH, crash_vel=100)
    groove_bar(s + 4,  MOTIF_B, hat_even=RIDE, hat_odd=RIDE,
               v_even=78, v_odd=58)
    groove_bar(s + 8,  MOTIF_TOM, hat_even=RIDE, hat_odd=RIDE,
               v_even=80, v_odd=60)
    groove_bar(s + 12, MOTIF_B, hat_even=RIDE, hat_odd=RIDE,
               v_even=80, v_odd=60)

    b = s + 16                                  # bar 20 - dense
    for k in range(16):
        add(b + 0.25 * k, HHCL,
            86 if k % 4 == 0 else (64 if k % 2 == 0 else 52), 0.09)
    add(b + 0, KICK, 110, 0.22)
    add(b + 0.75, KICK, 80, 0.22)
    add(b + 1.5, KICK, 96, 0.22)
    add(b + 2.0, KICK, 108, 0.22)
    add(b + 2.75, KICK, 84, 0.22)
    add(b + 3.5, KICK, 92, 0.22)
    add(b + 1.0, SNARE, 112, 0.10)
    add(b + 2.5, SNARE, 44, 0.10)
    add(b + 3.0, SNARE, 118, 0.10)
    add(b + 3.75, SNARE, 46, 0.10)

    b = s + 20                                  # bar 21 - space + answer
    add(b + 1.5, SNARE, 104, 0.10)
    add(b + 1.5, KICK, 100, 0.22)
    add(b + 2.5, LFT, 100, 0.20)
    add(b + 3.0, SNARE, 118, 0.10)
    add(b + 3.0, KICK, 108, 0.22)
    add(b + 3.75, SNARE, 40, 0.10)

    b = s + 24                                  # bar 22 - tom groove
    toms8 = [HMT, HMT, LMT, LMT, LTM, LTM, HFT, LFT]
    for k in range(8):
        add(b + 0.5 * k, toms8[k], 92 if k % 2 == 0 else 70, 0.18)
    add(b + 0, KICK, 100, 0.22)
    add(b + 2, KICK, 96, 0.22)
    add(b + 1, HHPED, 72, 0.25)
    add(b + 3, HHPED, 74, 0.25)

    b = s + 28                                  # bar 23 - fill
    seq = ([SNARE] * 4 + [HMT, LMT, LTM, HFT] +
           [LFT, LFT, SNARE, LFT] + [SNARE, HMT, LMT, SNARE])
    for k in range(16):
        add(b + 0.25 * k, seq[k], 70 + k * 3, 0.11)
    add(b + 0, KICK, 104, 0.22)
    add(b + 2, KICK, 100, 0.22)


# ----------------------------------------------------------------------
#  4. crescendo build                                      (bars 24-31)
# ----------------------------------------------------------------------
def build_build():
    s = 96
    accent_modes = [
        lambda k: k % 4 == 0,
        lambda k: k % 4 == 2,
        lambda k: k % 2 == 1,
        lambda k: k % 4 in (0, 2),
    ]
    for i in range(4):                          # bars 24-27
        b = s + i * 4
        base = 58 + i * 6
        for k in range(16):
            v = base + 26 if accent_modes[i](k) else \
                (base + 8 if k % 2 == 0 else base)
            add(b + 0.25 * k, SNARE, v, 0.09)
        add(b + 0, KICK, 96 + 4 * i, 0.22)
        add(b + 2, KICK, 92 + 4 * i, 0.22)
        add(b + 1, HHPED, 70, 0.25)
        add(b + 3, HHPED, 72, 0.25)

    for i, b in enumerate((s + 16, s + 20)):    # bars 28-29, open hats
        base = 76 + i * 6
        for k in range(16):
            v = base + 26 if k % 4 == 0 else \
                (base + 10 if k % 2 == 0 else base)
            add(b + 0.25 * k, SNARE, v, 0.09)
        add(b + 0, KICK, 108, 0.22)
        add(b + 2, KICK, 104, 0.22)
        add(b + 3.5, KICK, 96, 0.22)
        add(b + 1.5, HHOP, 72, 0.35)
        add(b + 3.5, HHOP, 76, 0.35)

    b = s + 24                                  # bar 30
    seq = [HTOM, HMT, HMT, LMT, LMT, LTM, LTM, HFT,
           HFT, LFT, LFT, HFT, LTM, LMT, HMT, LFT]
    for k in range(16):
        add(b + 0.25 * k, seq[k], 84 + k * 2, 0.12)
    add(b + 0, KICK, 110, 0.22)
    add(b + 2, KICK, 108, 0.22)

    b = s + 28                                  # bar 31
    seq = [HMT, HMT, LMT, LMT, LTM, LTM, HFT, HFT,
           LFT, LFT, SNARE, SNARE, HMT, LTM, HFT, SNARE]
    for k in range(16):
        add(b + 0.25 * k, seq[k], 90 + k * 2, 0.12)
    add(b + 0, KICK, 112, 0.22)
    add(b + 2, KICK, 110, 0.22)
    add(b + 3.5, KICK, 106, 0.22)


# ----------------------------------------------------------------------
#  5. release: crash, air, latin percussion                (bars 32-39)
# ----------------------------------------------------------------------
def build_breakdown():
    s = 128
    add(s + 0, CRASH, 116, 3.0)                 # bar 32 - crash and space
    add(s + 0, KICK, 112, 0.5)

    for i in range(4):                          # bars 33-36 - cabasa + congas
        b = s + 4 + i * 4
        for k in range(16):
            v = 50 if k % 4 == 0 else (40 if k % 2 == 0 else 32)
            add(b + 0.25 * k, CABASA, v + i * 3, 0.10)
        for pos, note, vel in TUMBAO:
            add(b + pos, note, vel + i * 3, 0.18)
        add(b + 1, HHPED, 44, 0.25)
        add(b + 3, HHPED, 46, 0.25)

    for i in range(2):                          # bars 37-38 - clave + bongos
        b = s + 20 + i * 4
        for pos in ((0.0, 1.5, 3.0) if i == 0 else (1.0, 2.0)):
            add(b + pos, CLAVE, 98, 0.12)
        for k in range(8):
            add(b + 0.5 * k, BONGOH, 84 if k % 2 == 0 else 68, 0.12)
        for k in range(4):
            add(b + 0.75 + k, BONGOL, 60, 0.12)

    b = s + 28                                  # bar 39 - timbales + cowbell
    for k in range(4):
        add(b + k, COWB, 88 + k * 3, 0.15)
    for i, pos in enumerate((0.5, 0.75, 1.5, 1.75, 2.5, 2.75, 3.5, 3.75)):
        add(b + pos, TIMBH if i % 2 == 0 else TIMBL, 84 + i * 4, 0.12)


# ----------------------------------------------------------------------
#  6. the motif returns, bigger                           (bars 40-47)
# ----------------------------------------------------------------------
def build_return():
    s = 160
    groove_bar(s + 0,  MOTIF_A, hat_even=RIDE, hat_odd=RIDE,
               v_even=82, v_odd=62, crash=CRASH, crash_vel=112, vscale=1.05)
    groove_bar(s + 4,  MOTIF_B, hat_even=RIDE, hat_odd=RIDE,
               v_even=82, v_odd=62, vscale=1.05)
    groove_bar(s + 8,  MOTIF_A2, hat_even=BELL, hat_odd=RIDE,
               v_even=88, v_odd=64, vscale=1.05)
    groove_bar(s + 12, MOTIF_B2, hat_even=BELL, hat_odd=RIDE,
               v_even=88, v_odd=64, vscale=1.05)

    for i, b in enumerate((s + 16, s + 20)):    # bars 44-45 - half time
        for k in range(8):
            add(b + 0.5 * k, HHCL, 78 if k % 2 == 0 else 60, 0.14)
        add(b + 0, KICK, 112, 0.22)
        add(b + 1.5, KICK, 84, 0.22)
        add(b + 2.0, SNARE, 122, 0.10)
        add(b + 2.0, KICK, 108, 0.22)
        add(b + 2.75, SNARE, 40, 0.10)
        add(b + 3.5, SNARE, 46, 0.10)
        add(b + 1, HHPED, 78, 0.25)
        add(b + 3, HHPED, 80, 0.25)
        if i == 0:
            add(b + 0, CRASH2, 100, 2.0)

    b = s + 24                                  # bar 46
    for k in range(16):
        v = 84 if k % 4 == 0 else (70 if k % 2 == 0 else 56)
        add(b + 0.25 * k, SNARE, v, 0.09)
    add(b + 0, KICK, 112, 0.22)
    add(b + 2, KICK, 108, 0.22)

    b = s + 28                                  # bar 47
    seq = [HMT, LMT, LTM, HFT, LFT, LFT, HFT, LTM,
           LMT, HMT, HTOM, HMT, LMT, LTM, HFT, SNARE]
    for k in range(16):
        add(b + 0.25 * k, seq[k], 88 + k * 2, 0.12)
    add(b + 0, KICK, 116, 0.22)
    add(b + 2, KICK, 112, 0.22)


# ----------------------------------------------------------------------
#  7. climax, double time                                  (bars 48-57)
# ----------------------------------------------------------------------
def build_climax():
    s = 192
    for i in range(4):                          # bars 48-51
        b = s + i * 4
        for k in range(16):
            if k % 4 == 0:
                note, v = BELL, 92
            elif k % 2 == 0:
                note, v = RIDE, 72
            else:
                note, v = RIDE, 58
            add(b + 0.25 * k, note, v, 0.09)
        for pos, note, vel in CLIMAX_KICKS[i % 2]:
            add(b + pos, note, vel, 0.22)
        for pos, note, vel in CLIMAX_SNARES[i % 2]:
            add(b + pos, note, vel, 0.10)
        add(b + 1, HHPED, 80, 0.25)
        add(b + 3, HHPED, 82, 0.25)
        if i == 0:
            add(b, CRASH, 112, 2.0)
        elif i == 2:
            add(b, CRASH2, 106, 2.0)

    for i in range(2):                          # bars 52-53 - tom cascades
        b = s + 16 + i * 4
        seq = TOM_CASCADE_A if i == 0 else TOM_CASCADE_B
        for k in range(16):
            add(b + 0.25 * k, seq[k], 86 + (k % 4) * 8, 0.12)
        add(b + 0, KICK, 120, 0.22)
        add(b + 1.0, KICK, 100, 0.22)
        add(b + 2.0, KICK, 118, 0.22)
        add(b + 3.0, KICK, 104, 0.22)
        add(b + 0, CRASH if i == 0 else CRASH2, 110, 1.6)

    for i in range(2):                          # bars 54-55 - dense groove
        b = s + 24 + i * 4
        for k in range(16):
            add(b + 0.25 * k, HHCL,
                84 if k % 4 == 0 else (62 if k % 2 == 0 else 50), 0.09)
        for pos, note, vel in CLIMAX_KICKS[(i + 1) % 2]:
            add(b + pos, note, vel, 0.22)
        for pos, note, vel in CLIMAX_SNARES[i]:
            add(b + pos, note, vel, 0.10)
        add(b + 0, CHINA, 104, 1.5)

    for i in range(2):                          # bars 56-57 - climactic fill
        b = s + 32 + i * 4
        seq = FILL_CLIMAX_A if i == 0 else FILL_CLIMAX_B
        for k in range(16):
            add(b + 0.25 * k, seq[k], 94 + k * 2, 0.12)
        add(b + 0, KICK, 118, 0.22)
        add(b + 2, KICK, 116, 0.22)
        add(b + 3.5, KICK, 110, 0.22)
        if i == 0:
            add(b + 0, CRASH, 108, 1.5)


# ----------------------------------------------------------------------
#  8. finale -- fill and one huge landing                  (bars 58-61)
# ----------------------------------------------------------------------
def build_finale():
    b = 232                                     # bar 58 - half time, loud
    add(b + 0, CRASH, 120, 3.0)
    add(b + 0, KICK, 122, 0.30)
    add(b + 0, SNARE, 124, 0.15)
    add(b + 1, HHPED, 86, 0.30)
    add(b + 1.5, KICK, 96, 0.25)
    add(b + 2.0, KICK, 118, 0.25)
    add(b + 2.0, SNARE, 126, 0.15)
    add(b + 3, HHPED, 88, 0.30)
    add(b + 3.5, SNARE, 46, 0.10)

    b = 236                                     # bar 59 - tom run
    seq = [HTOM, HTOM, HMT, HMT, LMT, LMT, LTM, LTM,
           HFT, HFT, LFT, LFT, HFT, HFT, LTM, LTM]
    for k in range(16):
        add(b + 0.25 * k, seq[k], 94 + k, 0.12)
    add(b + 0, KICK, 118, 0.22)
    add(b + 2, KICK, 116, 0.22)

    b = 240                                     # bar 60 - final roll
    seq = [SNARE, SNARE, HMT, SNARE, SNARE, LMT, SNARE, SNARE,
           LTM, LTM, HFT, HFT, LFT, LFT, SNARE, SNARE]
    for k in range(16):
        add(b + 0.25 * k, seq[k], 100 + (k % 4) * 5, 0.11)
    add(b + 0, KICK, 120, 0.22)
    add(b + 1, KICK, 112, 0.22)
    add(b + 2, KICK, 118, 0.22)
    add(b + 3, KICK, 114, 0.22)

    b = 244                                     # bar 61 - the landing
    add(b + 0, KICK, 127, 0.40)
    add(b + 0, SNARE, 127, 0.20)
    add(b + 0, CRASH, 127, 3.50)


# ----------------------------------------------------------------------
#  human feel: deliberate timing, tiny deterministic variation
# ----------------------------------------------------------------------
SWING = 0.045

OFFSETS = {
    KICK: -0.004, ABD: -0.004,
    SNARE: 0.011, STICK: 0.009, ESNARE: 0.011, CLAP: 0.010,
    LFT: 0.007, HFT: 0.007, LTM: 0.007, LMT: 0.007,
    HMT: 0.007, HTOM: 0.007,
    HHCL: -0.007, HHOP: -0.007, HHPED: 0.0,
    RIDE: -0.006, RIDE2: -0.006, BELL: -0.005,
    CRASH: 0.0, CRASH2: 0.0, CHINA: 0.0, SPLASH: 0.0,
    CONGAM: -0.004, CONGAO: -0.004, CONGAL: -0.004,
    BONGOH: -0.004, BONGOL: -0.004,
    TIMBH: -0.004, TIMBL: -0.004,
    CLAVE: 0.006, CABASA: -0.002, COWB: -0.003,
}


def timing_offset(note, beat):
    """Deliberate placement: swing on the off sixteenths plus a fixed
    push/pull per instrument (snare lays back, cymbals push)."""
    off = OFFSETS.get(note, 0.0)
    x = beat * 4.0
    k = round(x)
    if abs(x - k) < 1e-6 and (k % 4) in (1, 3):
        off += SWING
    return off


def _hash(a, b):
    h = (a * 2654435761 + b * 40503 + 12345) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return (h >> 8) & 0x7FFFFF


def jitter_time(note, beat):
    return ((_hash(int(round(beat * 960)), note) % 2001) - 1000) / 1000.0 * 0.004


def jitter_vel(note, beat):
    return (_hash(int(round(beat * 960)) + 7777, note) % 7) - 3


# ----------------------------------------------------------------------
#  voice limiter: never more than two hands and two feet at one instant
# ----------------------------------------------------------------------
def limit_voices(evs):
    out = []
    for e in evs:
        t = e[0]
        hands = feet = 0
        for o in reversed(out):
            if t - o[0] > 0.015:
                break
            if o[1] in FOOT_NOTES:
                feet += 1
            else:
                hands += 1
        if e[1] in FOOT_NOTES:
            if feet >= 2:
                continue
        else:
            if hands >= 2:
                continue
        out.append(e)
    return out


# ----------------------------------------------------------------------
#  render to a mido file
# ----------------------------------------------------------------------
def prepare():
    evs = []
    for beat, note, vel, dur in EV:
        t = max(0.0, beat + timing_offset(note, beat) + jitter_time(note, beat))
        v = max(1, min(127, int(round(vel + jitter_vel(note, beat)))))
        evs.append([t, note, v, dur])
    evs.sort(key=lambda e: e[0])
    evs = limit_voices(evs)

    by_note = defaultdict(list)
    for e in evs:
        by_note[e[1]].append(e)

    final = []
    for note, lst in by_note.items():
        lst.sort(key=lambda e: e[0])
        for i, e in enumerate(lst):
            off = e[0] + e[3]
            if i + 1 < len(lst):
                off = min(off, lst[i + 1][0] - 0.01)
            off = max(off, e[0] + 0.02)
            final.append((e[0], note, e[2], off))
    final.sort(key=lambda e: (e[0], e[1]))
    return final


def write_midi(path="solo.mid"):
    events = prepare()

    msgs = []
    for t, note, vel, off in events:
        msgs.append((t, 1, note, vel))
        msgs.append((off, 0, note, 0))
    msgs.sort(key=lambda m: (m[0], m[1]))

    mid = MidiFile(type=1, ticks_per_beat=PPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage("track_name", name="Drum Solo", time=0))
    track.append(MetaMessage("set_tempo", tempo=int(round(60000000.0 / BPM)),
                             time=0))
    track.append(MetaMessage("time_signature", numerator=4, denominator=4,
                             time=0))

    last_tick = 0
    for t, kind, note, vel in msgs:
        tick = int(round(t * PPQ))
        if tick < last_tick:
            tick = last_tick
        delta = tick - last_tick
        last_tick = tick
        if kind:
            track.append(Message("note_on", channel=CHANNEL,
                                 note=note, velocity=vel, time=delta))
        else:
            track.append(Message("note_off", channel=CHANNEL,
                                 note=note, velocity=0, time=delta))

    mid.save(path)


# ----------------------------------------------------------------------
#  assemble the solo
# ----------------------------------------------------------------------
def main():
    build_intro()        # bars  0- 7   quiet, growing
    build_statement()    # bars  8-15   motif stated
    build_development()  # bars 16-23   motif developed
    build_build()        # bars 24-31   crescendo
    build_breakdown()    # bars 32-39   release, latin percussion
    build_return()       # bars 40-47   motif returns
    build_climax()       # bars 48-57   double time climax
    build_finale()       # bars 58-61   fill and final landing
    write_midi("solo.mid")


if __name__ == "__main__":
    main()
