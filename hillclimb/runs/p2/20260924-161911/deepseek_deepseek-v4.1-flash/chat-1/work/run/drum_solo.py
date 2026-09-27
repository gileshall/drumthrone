"""
drum_solo.py — writes solo.mid, a ~2 minute General MIDI drum solo
on MIDI channel 10 (index 9).  Deterministic: same file every run.

Requires: mido (no other MIDI libraries).
"""

import mido

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------
TPB = 480                       # ticks per quarter note
BAR = TPB * 4                   # ticks per 4/4 bar
S16 = TPB // 4                  # ticks per sixteenth (120)
CH = 9                          # MIDI channel 10 (0-indexed)

# --- General MIDI percussion note numbers -----------------------------------
KICK    = 36    # Acoustic Bass Drum
STICK   = 37    # Side Stick
SNARE   = 38    # Acoustic Snare
CLAP    = 39
HAT     = 42    # Closed Hi-Hat   (hand)
HAT_P   = 44    # Pedal Hi-Hat    (foot)
HAT_O   = 46    # Open Hi-Hat
CRASH   = 49    # Crash Cymbal 1
T_HT    = 50    # High Tom
RIDE    = 51    # Ride Cymbal 1
CHINA   = 52    # Chinese Cymbal
BELL    = 53    # Ride Bell
TAMB    = 54
SPLASH  = 55
COW     = 56    # Cowbell
CRASH2  = 57    # Crash Cymbal 2
RIDE2   = 59
T_LO    = 41    # Low Floor Tom
T_HF    = 43    # High Floor Tom
T_LT    = 45    # Low Tom
T_LMT   = 47    # Low-Mid Tom
T_HMT   = 48    # Hi-Mid Tom
BONGO_H = 60
BONGO_L = 61
CONGA_M = 62
CONGA_O = 63
CONGA_L = 64
TIMB_H  = 65
TIMB_L  = 66
CLAVES  = 75
WOOD_H  = 76
WOOD_L  = 77

FOOT_NOTES = {KICK, HAT_P}

# --- note lengths (ticks) ---------------------------------------------------
DUR = {
    35: 80, 36: 80, 37: 45, 38: 55, 39: 55, 40: 55,
    41: 95, 42: 34, 43: 95, 44: 34, 45: 95, 46: 260, 47: 95,
    48: 95, 49: 900, 50: 95, 51: 100, 52: 1400, 53: 130, 54: 70,
    55: 500, 56: 160, 57: 900, 58: 320, 59: 100,
    60: 130, 61: 130, 62: 130, 63: 180, 64: 180,
    65: 150, 66: 150, 67: 130, 68: 130, 69: 90, 70: 90,
    71: 220, 72: 420, 73: 220, 74: 420, 75: 90, 76: 90, 77: 90,
    78: 320, 79: 420, 80: 420, 81: 900,
}

EV = []          # (tick, note, velocity, duration)


def add(bar, s, note, vel, offset=0, dur=None):
    """Place a strike at `s` sixteenths into bar `bar` (0-based)."""
    tick = int(round(bar * BAR + s * S16)) + offset
    if tick < 0:
        tick = 0
    v = int(round(vel))
    v = 0 if v < 0 else (127 if v > 127 else v)
    if dur is None:
        dur = DUR.get(note, 60)
    EV.append((tick, note, v, dur))


def groove(bar, hat=RIDE, hat_slots=None, hat_vel=86, hat_off=-6,
           snare_slots=(4, 12), snare_vel=104, ghost_slots=(7,), ghost_vel=34,
           kick_slots=(0, 10), kick_vel=106):
    """One bar of the core time feel: hats pushed slightly ahead, backbeat
    snare laid back a touch, ghost notes just behind."""
    if hat_slots is None:
        hat_slots = tuple(range(0, 16, 2))
    for i in hat_slots:
        add(bar, i, hat, hat_vel + (12 if i % 4 == 0 else 0), hat_off)
    for i in snare_slots:
        add(bar, i, SNARE, snare_vel, 8)
    for i in ghost_slots:
        add(bar, i, SNARE, ghost_vel, 4)
    for i in kick_slots:
        add(bar, i, KICK, kick_vel if i == 0 else kick_vel - 26)


# ============================================================================
#  1.  INTRO  (bars 0-3)  --  sparse ride feel that grows into a pickup
# ============================================================================
add(0, 0, RIDE, 72, -6, 200)
add(0, 4, RIDE, 62, -6, 200)
add(0, 8, RIDE, 76, -6, 200)
add(0, 12, RIDE, 64, -6, 200)
add(0, 0, KICK, 74)
add(0, 10, KICK, 58)

for i, v in ((0, 80), (2, 58), (4, 70), (6, 58),
             (8, 82), (10, 60), (12, 72), (14, 60)):
    add(1, i, RIDE, v, -6, 190)
add(1, 0, KICK, 84)
add(1, 4, SNARE, 60, 8)
add(1, 12, SNARE, 62, 8)

for i, v in ((0, 88), (2, 60), (4, 78), (6, 60),
             (8, 90), (10, 62), (12, 80), (14, 62)):
    add(2, i, RIDE, v, -6, 190)
add(2, 0, KICK, 94)
add(2, 10, KICK, 72)
add(2, 4, SNARE, 84, 8)
add(2, 12, SNARE, 88, 8)
add(2, 7, SNARE, 34, 4)
add(2, 15, SNARE, 30, 4)

# bar 3 -- pickup fill, rolling down the toms
add(3, 0, RIDE, 92, -6, 190)
add(3, 0, KICK, 102)
add(3, 4, SNARE, 94, 8)
add(3, 6, SNARE, 40, 4)
add(3, 8, T_HMT, 88)
add(3, 9, T_HMT, 76)
add(3, 10, T_LMT, 92)
add(3, 11, T_LMT, 80)
add(3, 12, T_LT, 96)
add(3, 13, T_LT, 84)
add(3, 14, T_HF, 100)
add(3, 15, T_LO, 106)

# ============================================================================
#  2.  MOTIF STATEMENT  (bars 4-11)  --  the idea is stated plainly
# ============================================================================
add(4, 0, CRASH, 116, -5)
groove(4)
groove(5, ghost_slots=(7, 15))
groove(6, kick_slots=(0, 6, 11), ghost_slots=(3, 7))
groove(7, hat_slots=(0, 2, 4, 6, 8, 10, 12), ghost_slots=(3,), kick_slots=(0, 10))
add(7, 14, HAT_O, 82, -6, 240)

# bars 8-9 : the motif "answered" on the toms over a quarter-note ride
for bar, base in ((8, 104), (9, 107)):
    k = bar - 8
    for i in (0, 4, 8, 12):
        add(bar, i, RIDE, (92 + k * 2) if i in (0, 8) else (78 + k * 2), -6, 190)
    add(bar, 2, T_HMT, 88 + k * 4)
    add(bar, 6, T_LMT, 82 + k * 4)
    add(bar, 10, T_LT, 90 + k * 4)
    add(bar, 14, T_HF, 86 + k * 4)
    add(bar, 0, KICK, base)
    add(bar, 10 if k == 0 else 11, KICK, 78 + k * 2)
add(9, 7, SNARE, 34, 4)
add(9, 15, SNARE, 32, 4)

# bar 10 : sixteenth hats + ghosted snare, rising inside the phrase
add(10, 0, KICK, 108)
for i in range(16):
    add(10, i, HAT, 68 + (16 if i % 4 == 0 else 0) + i, -6)
add(10, 4, SNARE, 106, 8)
add(10, 12, SNARE, 108, 8)
add(10, 7, SNARE, 38, 4)
add(10, 15, SNARE, 36, 4)

# bar 11 : fill
add(11, 0, KICK, 110)
add(11, 0, SNARE, 100, 8)
add(11, 2, SNARE, 58, 4)
add(11, 4, SNARE, 104, 8)
add(11, 6, SNARE, 60, 4)
add(11, 8, SNARE, 108, 8)
add(11, 10, T_HMT, 94)
add(11, 11, T_HMT, 80)
add(11, 12, T_LMT, 98)
add(11, 13, T_LMT, 84)
add(11, 14, T_LT, 102)
add(11, 15, T_HF, 108)

# ============================================================================
#  3.  DEVELOPMENT  (bars 12-19)  --  displacement, half-time, double-time
# ============================================================================
add(12, 0, CRASH, 112, -5)
groove(12, kick_slots=(1, 11), snare_slots=(5, 13), ghost_slots=(8,))
groove(13, kick_slots=(1, 6, 11), snare_slots=(5, 13), ghost_slots=(8, 15))

# bars 14-15 : half-time, wide open
for i, v in ((0, 94), (4, 76), (8, 96), (12, 78)):
    add(14, i, RIDE, v, -6, 210)
add(14, 8, SNARE, 112, 8)
add(14, 0, KICK, 106)
add(14, 6, KICK, 74)
add(14, 15, SNARE, 34, 4)

for i, v in ((0, 96), (4, 78), (8, 98), (12, 80)):
    add(15, i, RIDE, v, -6, 210)
add(15, 8, SNARE, 114, 8)
add(15, 0, KICK, 108)
add(15, 6, KICK, 76)
add(15, 11, KICK, 74)
add(15, 3, SNARE, 34, 4)
add(15, 15, SNARE, 36, 4)

# bars 16-17 : double-time ride
for bar in (16, 17):
    k = bar - 16
    for i in range(16):
        v = (96 + k * 2) if i % 4 == 0 else ((80 + k * 2) if i % 2 == 0 else 68)
        add(bar, i, RIDE, v, -6)
    add(bar, 0, KICK, 108 + k * 2)
    add(bar, 8, KICK, 100 + k * 2)
    add(bar, 4, SNARE, 108 + k * 2, 8)
    add(bar, 12, SNARE, 110 + k * 2, 8)
add(17, 7, SNARE, 40, 4)
add(17, 15, SNARE, 38, 4)

# bar 18 : accented snare sixteenths
add(18, 0, KICK, 112)
add(18, 8, KICK, 96)
for i in range(16):
    v = 108 if i % 4 == 0 else (84 if i % 2 == 0 else 68)
    add(18, i, SNARE, v, 6)

# bar 19 : crescendo roll straight into the tom section
add(19, 0, KICK, 112)
for i in range(16):
    add(19, i, SNARE, 56 + i * 3.5, 5)

# ============================================================================
#  4.  TOMS & CONGAS  (bars 20-27)  --  textural contrast, melodic drumming
# ============================================================================
add(20, 0, CRASH, 110, -5)
add(20, 0, KICK, 108)
add(20, 0, T_HT, 100)
add(20, 2, T_HT, 76)
add(20, 4, T_HMT, 96)
add(20, 6, T_HMT, 74)
add(20, 8, T_LMT, 100)
add(20, 10, T_LMT, 78)
add(20, 12, T_LT, 102)
add(20, 14, T_HF, 98)

add(21, 0, KICK, 108)
add(21, 0, T_HF, 100)
add(21, 2, T_LT, 92)
add(21, 4, T_LMT, 96)
add(21, 6, T_HMT, 92)
add(21, 8, T_HT, 90)
add(21, 10, T_HT, 84)
add(21, 12, T_HMT, 100)
add(21, 14, T_LMT, 96)

add(22, 0, KICK, 104)
for i, (n, v) in enumerate(((CONGA_O, 98), (CONGA_M, 80), (CONGA_L, 92),
                            (CONGA_M, 78), (CONGA_O, 100), (CONGA_M, 82),
                            (CONGA_L, 94), (CONGA_M, 80))):
    add(22, i * 2, n, v, -4, 110)

add(23, 0, KICK, 106)
for i, (n, v) in enumerate(((BONGO_H, 96), (BONGO_L, 80), (CONGA_O, 98),
                            (CONGA_M, 78), (BONGO_H, 100), (BONGO_L, 82),
                            (CONGA_L, 94), (CONGA_M, 80))):
    add(23, i * 2, n, v, -4, 110)

# bars 24-25 : snare phrase, tom answer
add(24, 0, KICK, 106)
add(24, 0, SNARE, 104, 8)
add(24, 2, SNARE, 58, 4)
add(24, 4, SNARE, 100, 8)
add(24, 6, SNARE, 56, 4)
add(24, 8, SNARE, 106, 8)
add(24, 10, SNARE, 60, 4)
add(24, 12, SNARE, 108, 8)
add(24, 14, T_HMT, 88)

add(25, 0, KICK, 108)
add(25, 0, T_HT, 100)
add(25, 2, SNARE, 62, 4)
add(25, 4, T_HMT, 96)
add(25, 6, SNARE, 58, 4)
add(25, 8, T_LMT, 98)
add(25, 10, SNARE, 64, 4)
add(25, 12, T_LT, 100)
add(25, 13, T_HF, 92)
add(25, 14, T_LO, 104)
add(25, 15, T_LO, 96)

# bars 26-27 : build on toms
add(26, 0, KICK, 110)
add(26, 0, T_LT, 100)
add(26, 2, SNARE, 62, 4)
add(26, 4, T_LMT, 96)
add(26, 6, SNARE, 60, 4)
add(26, 8, T_HMT, 94)
add(26, 10, SNARE, 64, 4)
add(26, 12, T_HT, 92)
add(26, 14, SNARE, 66, 4)

add(27, 0, KICK, 112)
add(27, 0, SNARE, 102, 8)
for i, n in enumerate((T_LO, T_HF, T_LT, T_LMT, T_HMT, T_HT,
                       T_HMT, T_LMT, T_LT, T_HF, T_LO, T_HF)):
    add(27, 4 + i, n, 88 + i * 2)

# ============================================================================
#  5.  BUILD  (bars 28-39)  --  from a whisper to a roar, shaped inside phrases
# ============================================================================
# bars 28-29 : side stick + pedal hat, woodblock tick
for bar in (28, 29):
    for i in (0, 4, 8, 12):
        add(bar, i, HAT_P, 52, -4, 60)
    add(bar, 0, KICK, 80)
    add(bar, 8, KICK, 68)
    add(bar, 4, STICK, 74, 8)
    add(bar, 12, STICK, 76, 8)
    add(bar, 6, WOOD_H, 58)
    add(bar, 14, WOOD_H, 62)
    add(bar, 7, SNARE, 26, 4)

# bars 30-31 : closed hats join, snares come up
for bar in (30, 31):
    k = bar - 30
    for i in range(0, 16, 2):
        add(bar, i, HAT, 66 + (12 if i % 4 == 0 else 0) + k * 4, -6, 100)
    add(bar, 0, KICK, 90 + k * 4)
    add(bar, 10, KICK, 72)
    add(bar, 4, SNARE, 78 + k * 4, 8)
    add(bar, 12, SNARE, 80 + k * 4, 8)
    add(bar, 7, SNARE, 30, 4)

# bars 32-35 : the motif comes back, developed a little every bar
groove(32, hat_vel=82, snare_vel=102, ghost_vel=32, ghost_slots=(7,))
groove(33, hat_vel=86, snare_vel=104, ghost_vel=34,
       kick_slots=(0, 3, 10), ghost_slots=(7,))
groove(34, hat_vel=88, snare_vel=106, ghost_vel=36,
       kick_slots=(0, 6, 10), ghost_slots=(7, 15))
groove(35, hat_vel=90, snare_vel=108, ghost_vel=38,
       kick_slots=(0, 3, 10, 13), ghost_slots=(7, 15))

# bars 36-37 : sixteenth hats, driving
for bar in (36, 37):
    k = bar - 36
    for i in range(16):
        v = (98 if i % 4 == 0 else (82 if i % 2 == 0 else 70)) + k * 4
        add(bar, i, HAT, v, -6)
    add(bar, 0, KICK, 110)
    add(bar, 8, KICK, 98)
    add(bar, 4, SNARE, 108 + k * 2, 8)
    add(bar, 12, SNARE, 110 + k * 2, 8)
    add(bar, 14, SNARE, 42, 4)

# bar 38 : snare roll crescendo
add(38, 0, KICK, 110)
for i in range(16):
    add(38, i, SNARE, 58 + i * 3.2, 5)

# bar 39 : tom roll into the climax
add(39, 0, KICK, 112)
for i, n in enumerate((T_HT, T_HT, T_HMT, T_HMT, T_LMT, T_LMT, T_LT, T_LT,
                       T_HF, T_HF, T_LO, T_LO, T_HF, T_LT, T_LMT, T_HMT)):
    add(39, i, n, 80 + i * 1.8)

# ============================================================================
#  6.  CLIMAX  (bars 40-51)
# ============================================================================
add(40, 0, CRASH, 122, -5)
add(40, 0, KICK, 120)
for i in range(0, 16, 2):
    add(40, i, RIDE, 110 if i % 4 == 0 else 92, -6)
add(40, 4, SNARE, 116, 8)
add(40, 12, SNARE, 118, 8)
add(40, 7, SNARE, 46, 4)
add(40, 15, SNARE, 44, 4)
add(40, 10, KICK, 106)

for bar in (41, 42):
    k = bar - 41
    for i in range(0, 16, 2):
        add(bar, i, RIDE, (108 + k * 2) if i % 4 == 0 else 90, -6)
    add(bar, 0, KICK, 118 + k)
    add(bar, 6, KICK, 98)
    add(bar, 10, KICK, 102)
    add(bar, 4, SNARE, 114 + k, 8)
    add(bar, 12, SNARE, 116 + k, 8)
    add(bar, 7, SNARE, 48, 4)
    add(bar, 15, SNARE, 44, 4)

add(43, 0, KICK, 120)
add(43, 0, SNARE, 118, 8)
add(43, 2, SNARE, 70, 4)
add(43, 4, SNARE, 116, 8)
add(43, 6, SNARE, 72, 4)
add(43, 8, T_HMT, 108)
add(43, 9, T_HMT, 90)
add(43, 10, T_LMT, 110)
add(43, 11, T_LMT, 92)
add(43, 12, T_LT, 112)
add(43, 13, T_HF, 104)
add(43, 14, T_LO, 116)
add(43, 15, T_LO, 118)

# bar 44 : four on the floor, snare on the offbeats
add(44, 0, KICK, 118)
add(44, 4, KICK, 112)
add(44, 8, KICK, 116)
add(44, 12, KICK, 110)
add(44, 2, SNARE, 112, 6)
add(44, 6, SNARE, 108, 6)
add(44, 10, SNARE, 114, 6)
add(44, 14, SNARE, 110, 6)

# bar 45 : displaced sixteenth accents
add(45, 0, KICK, 118)
for i in range(16):
    add(45, i, SNARE, 112 if i % 4 == 1 else 62, 5)

# bar 46 : snare / tom trade
add(46, 0, KICK, 118)
add(46, 0, SNARE, 116, 6)
add(46, 2, T_HT, 104)
add(46, 4, SNARE, 112, 6)
add(46, 6, T_HMT, 100)
add(46, 8, SNARE, 118, 6)
add(46, 10, T_LMT, 104)
add(46, 12, SNARE, 114, 6)
add(46, 14, T_LT, 108)
add(46, 15, T_HF, 100)

# bar 47 : roll on the snare then toms
add(47, 0, KICK, 120)
add(47, 0, SNARE, 118, 6)
for i in range(1, 8):
    add(47, i, SNARE, 60 + i * 6, 5)
add(47, 8, T_HMT, 104)
add(47, 9, T_HMT, 90)
add(47, 10, T_LMT, 108)
add(47, 11, T_LMT, 94)
add(47, 12, T_LT, 110)
add(47, 13, T_HF, 102)
add(47, 14, T_LO, 112)
add(47, 15, T_LO, 116)

# bar 48 : crash, full-weight groove
add(48, 0, CRASH, 124, -5)
add(48, 0, KICK, 120)
for i in range(0, 16, 2):
    add(48, i, RIDE, 112 if i % 4 == 0 else 94, -6)
add(48, 4, SNARE, 118, 8)
add(48, 12, SNARE, 120, 8)
add(48, 7, SNARE, 50, 4)
add(48, 10, KICK, 108)

# bar 49 : backbeat with heavy ghosts
add(49, 0, KICK, 120)
add(49, 11, KICK, 100)
add(49, 15, KICK, 104)
add(49, 0, SNARE, 120, 8)
add(49, 2, SNARE, 66, 4)
add(49, 4, SNARE, 116, 8)
add(49, 6, SNARE, 64, 4)
add(49, 8, SNARE, 120, 8)
add(49, 10, SNARE, 68, 4)
add(49, 12, SNARE, 118, 8)
add(49, 14, SNARE, 70, 4)

# bar 50 : sixteenth ride
for i in range(16):
    v = 112 if i % 4 == 0 else (92 if i % 2 == 0 else 78)
    add(50, i, RIDE, v, -6)
add(50, 0, KICK, 120)
add(50, 8, KICK, 112)
add(50, 4, SNARE, 118, 8)
add(50, 12, SNARE, 120, 8)

# bar 51 : roll up into the finale
add(51, 0, KICK, 120)
for i in range(16):
    add(51, i, SNARE, 70 + i * 3, 5)

# ============================================================================
#  7.  FINALE  (bars 52-59)  --  motif returns, then the last hit lands
# ============================================================================
add(52, 0, CRASH, 124, -5)
add(52, 0, KICK, 122)
for i in range(0, 16, 2):
    add(52, i, RIDE, 112 if i % 4 == 0 else 94, -6)
add(52, 4, SNARE, 118, 8)
add(52, 12, SNARE, 120, 8)
add(52, 7, SNARE, 52, 4)
add(52, 15, SNARE, 48, 4)
add(52, 10, KICK, 110)

add(53, 0, KICK, 122)
for i in range(0, 16, 2):
    add(53, i, RIDE, 114 if i % 4 == 0 else 96, -6)
add(53, 4, SNARE, 120, 8)
add(53, 12, SNARE, 122, 8)
add(53, 6, KICK, 104)
add(53, 10, KICK, 106)
add(53, 7, SNARE, 54, 4)

# bar 54 : motif on the toms
add(54, 0, KICK, 122)
add(54, 0, T_HT, 112)
add(54, 2, T_HMT, 100)
add(54, 4, T_LMT, 108)
add(54, 6, T_LT, 102)
add(54, 8, T_HF, 110)
add(54, 10, T_LO, 104)
add(54, 12, T_HF, 112)
add(54, 14, T_LT, 106)

# bar 55 : ascending toms
add(55, 0, KICK, 122)
add(55, 0, T_LO, 112)
add(55, 2, T_HF, 104)
add(55, 4, T_LT, 110)
add(55, 6, T_LMT, 106)
add(55, 8, T_HMT, 112)
add(55, 10, T_HT, 108)
add(55, 12, T_HMT, 114)
add(55, 14, T_HT, 118)

# bar 56 : fill
add(56, 0, KICK, 122)
add(56, 0, SNARE, 120, 6)
add(56, 2, SNARE, 72, 4)
add(56, 4, SNARE, 116, 6)
add(56, 6, SNARE, 74, 4)
add(56, 8, T_HMT, 110)
add(56, 9, T_HMT, 96)
add(56, 10, T_LMT, 112)
add(56, 11, T_LMT, 98)
add(56, 12, T_LT, 114)
add(56, 13, T_HF, 106)
add(56, 14, T_LO, 116)
add(56, 15, T_LO, 120)

# bar 57 : snare roll crescendo
add(57, 0, KICK, 122)
for i in range(16):
    add(57, i, SNARE, 66 + i * 3.4, 5)

# bar 58 : last big fill, toms all the way round
add(58, 0, KICK, 124)
add(58, 0, SNARE, 120, 6)
for i, n in enumerate((T_HT, T_HT, T_HMT, T_HMT, T_LMT, T_LMT, T_LT, T_LT,
                       T_HF, T_HF, T_LO, T_LO, T_HF, T_LT, T_LMT, T_HMT)):
    add(58, i, n, 96 + i * 1.6)

# bar 59 : THE HIT -- two hands, one foot, and hold it
add(59, 0, CRASH, 127, 0, 1800)
add(59, 0, CHINA, 122, 0, 1800)
add(59, 0, KICK, 127, 0, 400)


# ============================================================================
#  Render
# ============================================================================
def build(path='solo.mid'):
    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))   # 120 BPM
    track.append(mido.MetaMessage('time_signature',
                                  numerator=4, denominator=4, time=0))
    track.append(mido.MetaMessage('channel_prefix', channel=CH, time=0))

    msgs = []
    idx = 0
    for tick, note, vel, dur in EV:
        msgs.append((tick, 1, note, idx,
                     mido.Message('note_on', note=note, velocity=vel, channel=CH)))
        idx += 1
        msgs.append((tick + dur, 0, note, idx,
                     mido.Message('note_off', note=note, velocity=0, channel=CH)))
        idx += 1

    # note-offs first at equal ticks, so retriggers behave
    msgs.sort(key=lambda m: (m[0], m[1], m[2], m[3]))

    prev = 0
    for tick, _prio, _note, _idx, msg in msgs:
        msg.time = tick - prev
        prev = tick
        track.append(msg)

    mid.save(path)
    return mid


if __name__ == '__main__':
    build('solo.mid')
