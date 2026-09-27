import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

# Deterministic, through-composed ~2-minute GM drum solo.
# 4/4, 120 BPM, 60 bars = exactly 120 seconds.
# MIDI channel 10 is zero-based channel 9 in mido.

TPB = 480
BEAT = TPB
BAR = 4 * BEAT
BARS = 60
TEMPO = 500000  # 120 BPM

# General MIDI percussion notes
BD1, BD2 = 36, 35
RIM, SN, CLAP = 37, 38, 39
ESN = 40
FT2, FT1, LT, LMT, HMT, HT = 41, 43, 45, 47, 48, 50
CH, PH, OH = 42, 44, 46
CR1, CR2 = 49, 57
RIDE, BELL = 51, 53
TAMB, SPLASH, COW = 54, 55, 56
CHINA = 52
RBELL = 59
BONGO_H, BONGO_L = 60, 61
CONGA_M, CONGA_H, CONGA_L = 62, 63, 64
TIM_H, TIM_L = 65, 66
AGO_H, AGO_L = 67, 68
CABASA, MARACAS = 69, 70
WHISTLE_S, WHISTLE_L = 71, 72
GUIRO_S, GUIRO_L = 73, 74
CLAVES = 75
WB_H, WB_L = 76, 77
CUICA_M, CUICA_O = 78, 79
TRI_M, TRI_O = 80, 81

events = []
order = 0

def hit(bar, pos, note, vel, dur=45):
    """Add one drum strike. pos is in quarter-note beats within a bar."""
    global order
    t = int(round(bar * BAR + pos * BEAT))
    events.append((t, 1, order, note, max(1, min(127, int(vel)))))
    order += 1
    events.append((t + dur, 0, order, note, 0))
    order += 1

def flam(bar, pos, note, vel, spread=0.055):
    # Two hand strokes, deliberately separated rather than simultaneous.
    hit(bar, pos - spread, note, max(25, vel - 32))
    hit(bar, pos, note, vel)

def hh_swing(bar, density=2, base=61, accent=18, open_last=False, laidback=0.018):
    """Swinging eighths or sixteenths; swung off-eighth is ~2/3 through beat."""
    for q in range(4):
        hit(bar, q, CH, base + (accent if q in (0, 2) else 3))
        hit(bar, q + 2/3 + laidback, OH if (open_last and q == 3) else CH,
            base - 12)
        if density >= 4:
            # Quiet inner notes give the hands a triplet/sixteenth hybrid feel.
            hit(bar, q + 1/3, CH, base - 23)
            hit(bar, q + 5/6 + laidback, CH, base - 27)

def ride_swing(bar, base=68, bell=False):
    for q in range(4):
        n = BELL if bell and q in (0, 2) else RIDE
        hit(bar, q, n, base + (13 if q in (0, 2) else 1))
        hit(bar, q + 2/3 + 0.012, RIDE, base - 17)

def motif(bar, variation=0, power=0):
    """Core motif: kick statement, ghost-to-snare answer, syncopated kick."""
    k = 93 + power
    s = 105 + power
    hit(bar, 0, BD1, k)
    hit(bar, 0.68, SN, 34 + power // 3)     # ghost, laid back
    hit(bar, 1.0 + .025, SN, s)
    hit(bar, 1.72, BD1, 76 + power)
    hit(bar, 2.0, BD1, 88 + power)
    hit(bar, 2.34, SN, 31)
    hit(bar, 2.69, SN, 43)
    hit(bar, 3.0 + .03, SN, s + 3)
    if variation == 0:
        hit(bar, 3.72, BD1, 82 + power)
    elif variation == 1:
        hit(bar, 3.38, BD1, 72 + power)
        hit(bar, 3.72, BD1, 91 + power)
    else:
        hit(bar, 3.34, LT, 73 + power)
        hit(bar, 3.67, FT1, 86 + power)

def tom_answer(bar, strong=False):
    v = 83 if strong else 71
    seq = [(0.0, HT), (.36, HMT), (.68, LMT), (1.0, LT),
           (1.34, HMT), (1.68, LMT), (2.0, FT1), (2.34, LT),
           (2.68, FT2), (3.0, SN), (3.34, FT1), (3.68, FT2)]
    for i, (p, n) in enumerate(seq):
        hit(bar, p, n, v + (16 if i in (0, 3, 6, 9, 11) else 0))

def triplet_roll(bar, start=0, beats=4, base=60, crescendo=25):
    toms = [SN, SN, LT, SN, FT1, SN]
    count = beats * 3
    for i in range(count):
        p = start + i / 3
        vel = base + int(crescendo * i / max(1, count - 1))
        hit(bar, p, toms[i % len(toms)], vel + (8 if i % 3 == 0 else 0))

# Bars 1-4: sparse invocation; establish the vocabulary and room.
for b in range(4):
    if b == 0:
        hit(b, 0, CR1, 105)
        hit(b, 0, BD1, 93)
        hit(b, 1.02, SN, 96)
        hit(b, 1.68, SN, 30)
        hit(b, 2.0, BD1, 81)
        hit(b, 3.03, SN, 103)
        hit(b, 3.69, BD1, 75)
    elif b == 1:
        hit(b, 0, CH, 54); hit(b, 2/3, CH, 40)
        motif(b, 0, -8)
    elif b == 2:
        for p, n, v in [(0, HT, 76), (.67, HMT, 58), (1, SN, 93),
                        (2, LT, 75), (2.67, FT1, 67), (3, SN, 101),
                        (3.67, FT2, 84)]:
            hit(b, p, n, v)
    else:
        hit(b, 0, CR1, 96); motif(b, 1, -2)

# 5-12: motif stated and developed over a recognizable swung pulse.
for b in range(4, 12):
    hh_swing(b, 2, 59 + (b - 4), open_last=(b in (7, 11)))
    if b in (4, 8):
        hit(b, 0, CR1, 102 + (b - 4))
    motif(b, (b - 4) % 3, (b - 4) // 2)
    if b in (7, 11):
        # Short answer after the backbeat without turning into randomness.
        hit(b, 3.34, HMT, 72); hit(b, 3.67, FT1, 88)

# 13-16: contrast: hand-percussion dialogue, feet continue the motif's outline.
for b in range(12, 16):
    hit(b, 0, BD1, 76)
    hit(b, 2.0, BD1, 68)
    for q in range(4):
        hit(b, q, COW if q in (0, 2) else CONGA_L, 70 + (8 if q == 0 else 0))
        hit(b, q + 2/3, CONGA_H if q % 2 == 0 else BONGO_H, 55)
    hit(b, 1.34, CONGA_M, 43)
    hit(b, 3.0, CLAVES, 77)
    if b == 15:
        hit(b, 3.34, TIM_H, 69); hit(b, 3.67, TIM_L, 83)

# 17-24: ride section, wider dynamics; motif returns clearly.
for b in range(16, 24):
    ride_swing(b, 67 + (b - 16), bell=(b >= 20))
    if b in (16, 20):
        hit(b, 0, CR2, 108)
    motif(b, 1 if b % 2 else 0, 3 + b - 16)
    if b in (19, 23):
        hit(b, 3.35, LT, 78); hit(b, 3.69, FT2, 94)

# 25-28: tom-feature response, still phrased in four-bar sentences.
for b in range(24, 28):
    hit(b, 0, BD1, 88 + (b - 24) * 3)
    if b % 2:
        hit(b, 2, BD1, 77)
    tom_answer(b, strong=b >= 26)
    if b == 27:
        hit(b, 3.68, CR1, 105)

# 29-32: release: brushes aren't in GM, so imply them with soft closed hat,
# rim/side-stick and ghosts. Noticeably lower dynamic.
for b in range(28, 32):
    for q in range(4):
        hit(b, q, CH, 43 + (5 if q == 0 else 0))
        hit(b, q + 2/3 + .025, CH, 30)
    hit(b, 0, BD1, 58)
    hit(b, 1.035, RIM, 61)
    hit(b, 2.68, SN, 27)
    hit(b, 3.035, RIM, 66)
    if b == 31:
        hit(b, 3.67, OH, 55)

# 33-40: rebuild, with tambourine/cabasa coloring but only as one hand when used.
for b in range(32, 40):
    if b < 36:
        hh_swing(b, 2, 56 + 2 * (b - 32))
    else:
        ride_swing(b, 68 + 2 * (b - 36), bell=b >= 38)
    motif(b, (b + 1) % 3, 1 + 2 * (b - 32))
    # Place auxiliary percussion in gaps, not atop hand strokes.
    hit(b, 2.50, TAMB if b % 2 == 0 else CABASA, 49 + (b - 32) * 2)
    if b in (36, 39):
        hit(b, 0, SPLASH if b == 36 else CHINA, 104)

# 41-44: call-and-response using Latin/tuned colors from the GM set.
for b in range(40, 44):
    if b % 2 == 0:
        for p, n, v in [(0, BONGO_H, 82), (.5, BONGO_L, 62),
                        (1, CONGA_H, 86), (1.67, CONGA_L, 70),
                        (2, TIM_H, 89), (2.67, TIM_L, 75),
                        (3, WB_H, 81), (3.67, WB_L, 88)]:
            hit(b, p, n, v)
        hit(b, 0, BD1, 74); hit(b, 2, BD1, 69)
    else:
        hit(b, 0, BD1, 91)
        for p, n, v in [(0, HT, 84), (.34, HMT, 69), (.67, LMT, 73),
                        (1, SN, 102), (1.67, LT, 80), (2, FT1, 90),
                        (2.67, SN, 55), (3, SN, 108), (3.67, FT2, 96)]:
            hit(b, p, n, v)

# 45-48: increasingly tight triplet passage.
for b in range(44, 48):
    if b == 44:
        hit(b, 0, CR1, 111)
    triplet_roll(b, base=58 + 5 * (b - 44), crescendo=15)
    # Bass drum marks large-scale accents in spaces occupied by only one hand.
    hit(b, 0, BD1, 89 + (b - 44) * 5)
    hit(b, 2, BD1, 81 + (b - 44) * 5)

# 49-52: peak groove. Hands on ride/snare; foot hat omitted to keep limb logic clear.
for b in range(48, 52):
    ride_swing(b, 79, bell=True)
    motif(b, b % 3, 13)
    hit(b, 0, CR2 if b % 2 else CHINA, 113)
    # Crash+ride at t=0 would be two hands plus motif snare/kick; motif has only kick
    # there, so two hand strikes + foot remains physically feasible.
    if b in (49, 51):
        hit(b, 3.34, FT1, 94)
        hit(b, 3.68, FT2, 106)

# 53-56: dramatic drop, then the original idea emerges from near silence.
for b in range(52, 56):
    if b == 52:
        hit(b, 0, CR1, 88)
        hit(b, 0, BD1, 66)
        hit(b, 2.02, RIM, 54)
        hit(b, 3.68, SN, 29)
    elif b == 53:
        hit(b, 0, BD1, 61); hit(b, .68, SN, 25)
        hit(b, 1.03, SN, 70); hit(b, 3.03, SN, 76)
    elif b == 54:
        hh_swing(b, 2, 45)
        motif(b, 0, -15)
    else:
        hh_swing(b, 2, 53, open_last=True)
        motif(b, 1, -6)

# 57-59: final ascent, each bar denser and louder.
for b in range(56, 59):
    ride_swing(b, 72 + 5 * (b - 56), bell=True)
    motif(b, 2, 7 + 5 * (b - 56))
    hit(b, 0, [CR1, CR2, CHINA][b - 56], 108 + 5 * (b - 56))
    if b >= 57:
        hit(b, 2.34, FT1, 83 + 5 * (b - 57))
    hit(b, 3.67, FT2, 98 + 4 * (b - 56))

# Bar 60: concise cadenza and a hard final signature.
b = 59
hit(b, 0, CR1, 120); hit(b, 0, BD1, 120)
for p, n, v in [
    (.34, HT, 78), (.67, HMT, 82), (1.0, SN, 111),
    (1.34, LMT, 86), (1.67, LT, 91), (2.0, FT1, 105),
    (2.34, SN, 84), (2.67, FT2, 108), (3.0, SN, 119),
    (3.34, HT, 91), (3.55, LMT, 97), (3.76, FT1, 112)
]:
    hit(b, p, n, v)
# Final chord uses exactly two hands (crash + snare) and one foot (kick).
hit(b, 3.96, CR2, 127)
hit(b, 3.96, SN, 124)
hit(b, 3.96, BD1, 127)

mid = MidiFile(type=1, ticks_per_beat=TPB)

meta = MidiTrack()
mid.tracks.append(meta)
meta.append(MetaMessage('track_name', name='Two Minute Drum Solo'))
meta.append(MetaMessage('time_signature', numerator=4, denominator=4,
                        clocks_per_click=24, notated_32nd_notes_per_beat=8))
meta.append(MetaMessage('set_tempo', tempo=TEMPO))
meta.append(MetaMessage('end_of_track', time=BARS * BAR))

drums = MidiTrack()
mid.tracks.append(drums)
drums.append(MetaMessage('track_name', name='GM Drums - Channel 10', time=0))

# Sort note-offs before note-ons at the same tick; stable order makes output identical.
events.sort(key=lambda e: (e[0], e[1], e[2]))
last = 0
for t, kind, _, note, vel in events:
    delta = t - last
    if kind == 1:
        drums.append(Message('note_on', channel=9, note=note, velocity=vel, time=delta))
    else:
        drums.append(Message('note_off', channel=9, note=note, velocity=0, time=delta))
    last = t

# Hold the track to precisely 60 bars (120 seconds at 120 BPM).
drums.append(MetaMessage('end_of_track', time=max(0, BARS * BAR - last)))

mid.save('solo.mid')
