#!/usr/bin/env python3
"""
Generate a deterministic two-minute General MIDI drum solo.

Writes solo.mid in the current directory.
- MIDI channel 10 (mido channel 9)
- 120 BPM, 60 bars of 4/4 = exactly 120 seconds
- Deterministic: no randomness, same file on every run
"""

from collections import defaultdict
from mido import Message, MidiFile, MidiTrack, MetaMessage

# Timing: 120 BPM, 240 quarter notes = 120 seconds
TPQ = 480
BAR = 4 * TPQ
S16 = TPQ // 4
TOTAL_BEATS = 240
TOTAL_TICKS = TPQ * TOTAL_BEATS
CH = 9  # General MIDI drums: channel 10 in 1-based terms

# General MIDI percussion notes used
BD = 36       # Bass Drum 1
SD = 38       # Acoustic Snare
SS = 37       # Side Stick
ESN = 40      # Electric Snare
CHH = 42      # Closed Hi-Hat
PHH = 44      # Pedal Hi-Hat
OHH = 46      # Open Hi-Hat
LFT = 41      # Low Floor Tom
HFT = 43      # High Floor Tom
LT = 45       # Low Tom
LMT = 47      # Low-Mid Tom
HMT = 48      # High-Mid Tom
HT = 50       # High Tom
CR1 = 49      # Crash Cymbal 1
CR2 = 57      # Crash Cymbal 2
RIDE = 51     # Ride Cymbal 1
BELL = 53     # Ride Bell
SPL = 55      # Splash Cymbal
COW = 56      # Cowbell
HTIM = 65     # High Timbale
LTIM = 66     # Low Timbale
OHC = 63      # Open Hi Conga
MHC = 62      # Mute Hi Conga
LC = 64       # Low Conga
WH = 76       # High Wood Block
CLB = 75      # Claves
MAR = 70      # Maracas
TAM = 54      # Tambourine

CYM = {CR1, CR2, RIDE, BELL, SPL, 52, 59}
HAT = {CHH, PHH, OHH}
KICK = {35, BD}
SNARE = {SD, SS, ESN}
TOM = {LFT, HFT, LT, LMT, HMT, HT}
FOOT = {35, BD, PHH}

events = []


def default_dur(note):
    """Default note lengths for cleaner note_off placement."""
    if note in (CR1, CR2):
        return 900
    if note in CYM:
        return 320
    if note in HAT:
        return 80
    if note in KICK:
        return 160
    if note in SNARE:
        return 120
    if note in TOM:
        return 180
    return 120


def add(t, note, vel, dur=None):
    """Add a percussion hit, clamped to valid GM range and file length."""
    if vel is None or vel <= 0:
        return
    t = int(t)
    if t < 0:
        t = 0
    if t >= TOTAL_TICKS:
        return
    if note < 35 or note > 81:
        return

    vel = int(max(1, min(127, vel)))
    if dur is None:
        dur = default_dur(note)
    dur = int(dur)
    if dur < 1:
        dur = 1
    if t + dur > TOTAL_TICKS:
        dur = TOTAL_TICKS - t

    events.append([t, note, vel, dur])


def add_steps(bar, steps, note, vel, dur=None):
    """Add hits on 16th-note steps within a bar."""
    for s in steps:
        add(bar * BAR + s * S16, note, vel, dur)


def add_motif_bar(bar, note, accent=100, ghost=40, dur=None):
    """
    Core rhythmic motif: 0, 3, 6, 10, 12.
    This cell is stated, varied, and recalled throughout the solo.
    """
    for s, v in (
        (0, accent),
        (3, ghost),
        (6, max(ghost, accent - 8)),
        (10, ghost + 6),
        (12, accent),
    ):
        add(bar * BAR + s * S16, note, v, dur)


# -----------------------------------------------------------------------------
# Sections
# -----------------------------------------------------------------------------

def intro():
    """Bars 0-3: sparse statement of motif."""
    motif = [(0, 100), (3, 38), (6, 92), (10, 45), (12, 100)]

    # Bar 0: bell motif, sparse bass drum
    for s, v in motif:
        add(0 * BAR + s * S16, BELL, v, 260)
    add(0, BD, 100, 180)
    add(12 * S16, BD, 80, 160)

    # Bar 1: snare states the motif
    for s, v in motif:
        add(1 * BAR + s * S16, SD, v, 120)
    add(1 * BAR + 8 * S16, SS, 55, 90)

    # Bar 2: high-mid tom version
    for s, v in motif:
        add(2 * BAR + s * S16, HMT, v, 170)
    add(2 * BAR, BD, 105, 160)
    add(2 * BAR + 10 * S16, BD, 90, 160)

    # Bar 3: low-mid tom answer, small fill into groove
    for s, v in motif:
        add(3 * BAR + s * S16, LMT, max(20, v - 6), 170)
    add(3 * BAR, BD, 105, 160)
    add(3 * BAR + 13 * S16, HMT, 84, 120)
    add(3 * BAR + 14 * S16, SD, 92, 120)
    add(3 * BAR + 15 * S16, CR1, 98, 960)


def theme_a():
    """Bars 4-11: main funk groove, kick motif 0-7-10."""
    for bar in range(4, 12):
        local = bar - 4
        base = bar * BAR
        fill = (local == 7)

        # Hi-hat eighths
        for step in range(0, 16, 2):
            if fill and step >= 14:
                continue
            if local == 6 and step == 14:
                add(base + step * S16, OHH, 90, 300)
            else:
                hat_vel = 84 if step in (4, 12) else 62
                add(base + step * S16, CHH, hat_vel, 70)

        # Pedal hi-hat on beats 2 and 4
        if not fill:
            add_steps(bar, [4, 12], PHH, 66, 70)

        # Backbeats
        sd_vel = 110 if local % 2 == 0 else 103
        add_steps(bar, [4, 12], SD, sd_vel, 120)

        # Ghost notes
        ghosts = [(7, 30)]
        if local in (1, 3, 5):
            ghosts.append((15, 26))
        if local in (2, 6):
            ghosts.extend([(2, 24), (10, 28)])
        if local == 4:
            ghosts.append((11, 30))
        for s, v in ghosts:
            add(base + s * S16, SD, v, 70)

        # Bass drum motif and variations
        if local in (0, 4, 7):
            kicks = [0, 7, 10]
        elif local in (1, 5):
            kicks = [0, 6, 10, 13]
        elif local == 2:
            kicks = [0, 7, 10, 14]
        elif local == 3:
            kicks = [0, 3, 10]
        elif local == 6:
            kicks = [0, 7, 10, 13, 14]
        else:
            kicks = [0, 7, 10]

        for s in kicks:
            add(base + s * S16, BD, 114 if s in (0, 7, 10) else 98, 150)

        # Fill at the end of the phrase
        if fill:
            add(base + 13 * S16, HMT, 88, 110)
            add(base + 14 * S16, LMT, 94, 110)
            add(base + 15 * S16, SD, 104, 110)


def variation_a():
    """Bars 12-19: motif orchestrated around the kit over ride time."""
    for bar in range(12, 20):
        local = bar - 12
        base = bar * BAR
        fill = (local == 7)

        # Ride quarters
        for step in (0, 4, 8, 12):
            if fill and step == 12:
                continue
            add(base + step * S16, RIDE, 86 + local * 2, 300)

        # Pedal hi-hat
        if not fill:
            add_steps(bar, [4, 12], PHH, 62, 70)

        # Kick variations
        if local in (0, 2, 4):
            kicks = [0, 7, 10]
        elif local in (1, 5):
            kicks = [0, 3, 6, 10]
        elif local == 3:
            kicks = [0, 6, 10, 13]
        elif local == 6:
            kicks = [0, 7, 10, 14]
        else:
            kicks = [0, 10]

        for s in kicks:
            add(base + s * S16, BD, 108, 150)

        # Comping / motif orchestration
        if local in (0, 1):
            add_steps(bar, [4, 12], SD, 106, 120)
            if local == 1:
                add(base + 7 * S16, SD, 32, 70)
                add(base + 15 * S16, SD, 26, 70)
            else:
                add(base + 10 * S16, SD, 30, 70)

        elif local in (2, 3):
            add_motif_bar(bar, HMT if local == 2 else LMT, accent=102, ghost=38, dur=170)
            add(base + 15 * S16, SD, 26, 70)

        elif local in (4, 5):
            add(base + 2 * S16, SD, 56, 100)
            add(base + 4 * S16, SD, 108, 120)
            add(base + 10 * S16, SD, 64, 100)
            add(base + 12 * S16, SD, 108, 120)
            if local == 5:
                add(base + 7 * S16, ESN, 44, 90)
                add(base + 14 * S16, SD, 36, 80)

        elif local == 6:
            add(base + 0 * S16, HMT, 100, 170)
            add(base + 3 * S16, LMT, 38, 150)
            add(base + 6 * S16, HMT, 94, 170)
            add(base + 10 * S16, LMT, 44, 150)
            add(base + 12 * S16, SD, 106, 120)

        else:
            # Ending fill
            seq = [HMT, HMT, HMT, LMT, LMT, SD, SD, SD]
            vels = [70, 76, 82, 88, 94, 100, 106, 112]
            for i, step in enumerate(range(8, 16)):
                add(base + step * S16, seq[i], vels[i], 110)


def latin_b():
    """Bars 20-27: contrasting Latin texture, still motif-based."""
    # Bar 20: wood block motif
    b = 20
    base = b * BAR
    for s, v in [(0, 100), (3, 42), (6, 92), (10, 48), (12, 100)]:
        add(base + s * S16, WH, v, 120)
    add(base + 8 * S16, LC, 70, 130)
    add(base + 14 * S16, OHC, 60, 130)
    add(base, BD, 100, 160)
    add(base + 10 * S16, BD, 88, 160)
    add_steps(b, [4, 12], PHH, 58, 80)

    # Bar 21: claves answer
    b = 21
    base = b * BAR
    for s, v in [(2, 96), (6, 90), (12, 100)]:
        add(base + s * S16, CLB, v, 120)
    add(base, MHC, 68, 130)
    add(base + 4 * S16, OHC, 74, 130)
    add(base + 8 * S16, LC, 80, 130)
    add(base + 10 * S16, OHC, 58, 130)
    add(base + 14 * S16, LC, 66, 130)
    add(base, BD, 100, 160)
    add(base + 10 * S16, BD, 86, 160)
    add_steps(b, [4, 12], PHH, 58, 80)

    # Bars 22-23: congas lead
    for b in (22, 23):
        base = b * BAR
        pattern = [
            (0, OHC, 92),
            (3, MHC, 44),
            (6, OHC, 88),
            (8, LC, 70),
            (10, OHC, 58),
            (12, LC, 96),
            (14, MHC, 52),
        ]
        for s, note, v in pattern:
            add(base + s * S16, note, v, 140)

        add(base, BD, 100, 160)
        add(base + 10 * S16, BD, 86, 160)
        add_steps(b, [4, 12], PHH, 56, 80)

        if b == 23:
            add(base + 13 * S16, HTIM, 62, 110)
            add(base + 15 * S16, LTIM, 72, 110)

    # Bar 24: cowbell quarters with timbales
    b = 24
    base = b * BAR
    add_steps(b, [0, 4, 8, 12], COW, 92, 150)
    add(base + 3 * S16, HTIM, 78, 130)
    add(base + 6 * S16, LTIM, 70, 130)
    add(base + 10 * S16, HTIM, 84, 130)
    add(base + 14 * S16, LTIM, 76, 130)
    add(base, BD, 102, 160)
    add(base + 10 * S16, BD, 88, 160)
    add_steps(b, [4, 12], PHH, 58, 80)

    # Bar 25: cowbell motif
    b = 25
    base = b * BAR
    for s, v in [(0, 96), (3, 42), (6, 88), (10, 48), (12, 98)]:
        add(base + s * S16, COW, v, 150)
    add(base + 8 * S16, HTIM, 74, 130)
    add(base + 13 * S16, LTIM, 66, 120)
    add(base + 15 * S16, HTIM, 82, 120)
    add(base, BD, 102, 160)
    add(base + 10 * S16, BD, 88, 160)
    add_steps(b, [4, 12], PHH, 58, 80)

    # Bar 26: cowbell eighths, timbale responses
    b = 26
    base = b * BAR
    for step in range(0, 16, 2):
        add(base + step * S16, COW, 88 if step % 4 == 0 else 70, 130)
    for s, note, v in [(3, HTIM, 54), (7, HTIM, 70), (11, LTIM, 76), (15, HTIM, 88)]:
        add(base + s * S16, note, v, 120)
    add(base, BD, 104, 160)
    add(base + 7 * S16, BD, 84, 150)
    add(base + 10 * S16, BD, 94, 150)
    add_steps(b, [4, 12], PHH, 60, 80)

    # Bar 27: build fill
    b = 27
    base = b * BAR
    seq = [HTIM, LTIM, HTIM, LTIM, SD, HMT, SD, LMT,
           HTIM, LTIM, SD, HMT, SD, SD, SD, SD]
    for step, note in enumerate(seq):
        vel = 62 + step * 3
        add(base + step * S16, note, vel, 110)
    add(base, BD, 100, 160)
    add(base + 10 * S16, BD, 92, 150)


def build():
    """Bars 28-35: funk/Latin build, cowbell replaces hi-hat."""
    for bar in range(28, 36):
        local = bar - 28
        base = bar * BAR

        if local in (0, 4):
            add(base, CR1, 116, 1200)
            add(base, BD, 118, 170)

        # Cowbell eighths
        for step in range(0, 16, 2):
            if local in (0, 4) and step == 0:
                continue
            vel = 92 if step in (4, 12) else 74
            if local >= 4:
                vel += 4
            add(base + step * S16, COW, vel, 130)

        # Backbeats
        add_steps(bar, [4, 12], SD, 112 if local >= 4 else 106, 120)

        # Ghosts
        ghosts = [(7, 30)]
        if local % 2 == 1:
            ghosts.append((15, 28))
        if local >= 2:
            ghosts.extend([(2, 24), (10, 30)])
        if local == 7:
            ghosts = []
        for s, v in ghosts:
            add(base + s * S16, SD, v, 70)

        # Increasingly active kicks
        if local in (0, 1):
            kicks = [0, 7, 10]
        elif local in (2, 3):
            kicks = [0, 6, 10, 13]
        elif local in (4, 5):
            kicks = [0, 3, 7, 10, 14]
        elif local == 6:
            kicks = [0, 6, 7, 10, 13, 14]
        else:
            kicks = [0, 7, 10]

        for s in kicks:
            if s == 0 and local in (0, 4):
                continue
            add(base + s * S16, BD, 110 if s in (0, 7, 10) else 96, 150)

        # Pedal hi-hat except final fill bar
        if local != 7:
            add_steps(bar, [4, 12], PHH, 64, 80)

        # Fill
        if local == 7:
            add(base + 13 * S16, HMT, 90, 110)
            add(base + 14 * S16, LMT, 96, 110)
            add(base + 15 * S16, SD, 108, 110)


def peak():
    """Bars 36-43: high-density single-stroke peak."""
    for bar in range(36, 44):
        local = bar - 36
        base = bar * BAR

        if local in (0, 4):
            add(base, CR1, 120, 1500)
            add(base, BD, 120, 170)

        if local == 7:
            add(base + 12 * S16, CR2, 114, 1200)
            add(base + 12 * S16, BD, 108, 150)

        # Single-stroke pitch contour
        if local < 2:
            seq = [SD, SD, HMT, HMT, LMT, LMT, LT, LT]
        elif local < 4:
            seq = [HMT, SD, HMT, SD, LMT, SD, LMT, SD]
        elif local < 6:
            seq = [SD, HMT, SD, LMT, SD, LT, SD, LFT]
        else:
            seq = [SD, SD, SD, HMT, LMT, LT, LFT, SD]

        for step in range(16):
            if local in (0, 4) and step == 0:
                continue
            if local == 7 and step == 12:
                continue

            note = seq[step % len(seq)]
            accent = step in (0, 3, 6, 10, 12)
            if 2 <= local < 6 and step % 3 == 0:
                accent = True

            if local == 7:
                vel = 64 + step * 4
            else:
                vel = 118 if accent else 62 + local * 4

            add(base + step * S16, note, vel, 100)

        # Kick accents
        if local < 4:
            kicks = [0, 6, 10] if local % 2 == 0 else [0, 7, 10, 13]
        else:
            kicks = [0, 3, 6, 10, 12] if local < 6 else [0, 6, 10, 14]

        for s in kicks:
            if s == 0 and local in (0, 4):
                continue
            if s == 12 and local == 7:
                continue
            add(base + s * S16, BD, 112, 150)

        # Pedal hi-hat
        if local != 7:
            add_steps(bar, [4, 12], PHH, 66, 80)
        else:
            add(base + 4 * S16, PHH, 66, 80)


def recap():
    """Bars 44-51: return of main groove, with swung ride flavor."""
    for bar in range(44, 52):
        local = bar - 44
        base = bar * BAR

        if local in (0, 4):
            add(base, CR1, 118, 1200)
            add(base, BD, 118, 170)

        # Right hand: bell motif in bars 2-3, otherwise swung ride
        if local in (2, 3):
            for s, v in [(0, 104), (3, 40), (6, 94), (10, 46), (12, 104)]:
                add(base + s * S16, BELL, v, 240)
        else:
            for beat in range(4):
                t0 = base + beat * TPQ
                if not (local in (0, 4) and beat == 0):
                    add(t0, RIDE, 96 + local * 2, 300)
                if beat in (1, 3):
                    # Swung offbeat: deliberately delayed, then nudged more in adjust_tick
                    add(t0 + 320, RIDE, 80 + local * 2, 220)

        if local != 7:
            add_steps(bar, [4, 12], PHH, 64, 80)

        # Backbeats
        add_steps(bar, [4, 12], SD, 112, 120)

        # Ghosts
        ghosts = [(7, 32)]
        if local in (1, 3, 5):
            ghosts.append((15, 28))
        if local in (2, 6):
            ghosts.extend([(2, 26), (10, 30)])
        if local == 7:
            ghosts = []
        for s, v in ghosts:
            add(base + s * S16, SD, v, 70)

        # Kick motif returns
        if local in (0, 4, 7):
            kicks = [0, 7, 10]
        elif local in (1, 5):
            kicks = [0, 6, 10, 13]
        elif local == 2:
            kicks = [0, 7, 10, 14]
        elif local == 3:
            kicks = [0, 3, 10]
        elif local == 6:
            kicks = [0, 7, 10, 13, 14]
        else:
            kicks = [0, 7, 10]

        for s in kicks:
            if s == 0 and local in (0, 4):
                continue
            add(base + s * S16, BD, 114 if s in (0, 7, 10) else 98, 150)

        # Final fill of the section
        if local == 7:
            add(base + 13 * S16, HMT, 94, 110)
            add(base + 14 * S16, LMT, 100, 110)
            add(base + 15 * S16, SD, 110, 110)


def outro():
    """Bars 52-59: release, motif recall, final chord."""
    # Bars 52-55: fading bell motif
    for bar in range(52, 56):
        local = bar - 52
        base = bar * BAR
        dec = local * 10

        for s, v in [(0, 92), (3, 38), (6, 84), (10, 44), (12, 92)]:
            vv = v - dec
            if vv > 0:
                add(base + s * S16, BELL, vv, 260)

        add(base, BD, max(40, 96 - dec), 160)
        if local < 3:
            add(base + 10 * S16, BD, max(35, 82 - dec), 150)
            add(base + 4 * S16, SD, 30, 70)
            add(base + 12 * S16, SD, max(20, 36 - dec), 70)

    # Bar 56: low floor tom recall
    b = 56
    base = b * BAR
    for s, v in [(0, 88), (3, 36), (6, 80), (10, 40), (12, 88)]:
        add(base + s * S16, LFT, v, 180)
    add(base, BD, 98, 160)

    # Bar 57: snare recall
    b = 57
    base = b * BAR
    for s, v in [(0, 92), (3, 36), (6, 86), (10, 42), (12, 96)]:
        add(base + s * S16, SD, v, 120)
    add(base + 8 * S16, BD, 84, 150)

    # Bar 58: quiet build into final chord
    b = 58
    base = b * BAR
    seq = [SD, SD, HMT, LMT, SD, SD, HMT, SD]
    for i, step in enumerate(range(8, 16)):
        add(base + step * S16, seq[i], 56 + i * 8, 100)
    add(base, BD, 90, 160)

    # Bar 59: final chord
    base = 59 * BAR
    add(base, CR1, 127, TOTAL_TICKS - base)
    add(base, SD, 118, 480)
    add(base, BD, 127, 480)


# -----------------------------------------------------------------------------
# Human feel and playability
# -----------------------------------------------------------------------------

def section_name(bar):
    if bar < 4:
        return 'intro'
    if bar < 12:
        return 'A'
    if bar < 20:
        return 'Avar'
    if bar < 28:
        return 'B'
    if bar < 36:
        return 'build'
    if bar < 44:
        return 'peak'
    if bar < 52:
        return 'recap'
    return 'outro'


def adjust_tick(t, note, vel):
    """
    Deterministic microtiming:
    - Kick pushed slightly ahead.
    - Backbeat snare laid back.
    - Offbeat hats/cowbells laid back.
    - Swung ride offbeats nudged later.
    """
    if t <= 0:
        return 0

    bar = t // BAR
    if bar >= 59:
        return t

    sec = section_name(bar)
    pos = t % BAR
    beat = pos // TPQ
    sub = pos % TPQ
    off = 0

    if sec in ('A', 'Avar', 'build', 'peak', 'recap'):
        if note == BD:
            off -= 5 if sub == 0 else 3

        if note in (SD, ESN) and vel >= 90 and beat in (1, 3) and sub == 0:
            off += 8

        if note == SD and vel < 50:
            off += 2

        if note in (CHH, COW) and sub == 2 * S16:
            off += 4

    if sec == 'recap' and note == RIDE and sub == 320:
        off += 6

    if sec == 'B':
        if note in (OHC, MHC, LC, HTIM, LTIM):
            off += 3

    if sec == 'peak' and vel >= 100:
        off -= 2

    if sec in ('intro', 'outro') and note in (SD, BELL):
        off += 3

    return max(0, min(TOTAL_TICKS - 1, t + off))


def playable(evlist):
    """
    Enforce one-drummer limits:
    - at most two hand strikes at the same instant
    - at most two foot strikes at the same instant

    Feet are bass drums and pedal hi-hat. Everything else is treated as hands.
    If more than two events collide in a limb category, keep the loudest.
    """
    by_tick = defaultdict(list)
    for ev in evlist:
        by_tick[ev[0]].append(ev)

    kept = []
    for t, evs in by_tick.items():
        evs.sort(key=lambda e: (-e[2], e[1]))
        hands = []
        feet = []

        for ev in evs:
            if ev[1] in FOOT:
                if len(feet) < 2:
                    feet.append(ev)
            else:
                if len(hands) < 2:
                    hands.append(ev)

        kept.extend(hands)
        kept.extend(feet)

    return kept


def main():
    # Compose all sections
    intro()
    theme_a()
    variation_a()
    latin_b()
    build()
    peak()
    recap()
    outro()

    # Apply deliberate microtiming
    shifted = []
    for t, note, vel, dur in events:
        shifted.append([adjust_tick(t, note, vel), note, vel, dur])

    # Enforce playability
    final_events = playable(shifted)

    # Build MIDI messages
    msgs = []
    for t, note, vel, dur in final_events:
        off_t = t + dur
        if off_t > TOTAL_TICKS:
            off_t = TOTAL_TICKS
        if off_t <= t:
            off_t = t + 1

        msgs.append((t, 1, Message('note_on', channel=CH, note=note, velocity=vel, time=0)))
        msgs.append((off_t, 0, Message('note_off', channel=CH, note=note, velocity=0, time=0)))

    # Note-offs before note-ons at the same tick
    msgs.sort(key=lambda x: (x[0], x[1], x[2].note))

    # Assemble MIDI file
    mid = MidiFile(type=0, ticks_per_beat=TPQ)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('set_tempo', tempo=500000, time=0))  # 120 BPM
    track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                             clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))

    last = 0
    for tick, _, msg in msgs:
        msg.time = tick - last
        track.append(msg)
        last = tick

    # Ensure the file is exactly 120 seconds long
    if last < TOTAL_TICKS:
        track.append(MetaMessage('end_of_track', time=TOTAL_TICKS - last))
    else:
        track.append(MetaMessage('end_of_track', time=0))

    mid.save('solo.mid')


if __name__ == '__main__':
    main()
