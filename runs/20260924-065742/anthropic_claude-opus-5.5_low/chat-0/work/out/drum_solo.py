#!/usr/bin/env python3
"""drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

The same seed is used on every run, so solo.mid is identical each time.
"""
import random
import mido

PPQ = 480
S16 = PPQ // 4          # ticks per 16th note
BAR = PPQ * 4
BPM = 110               # 55 bars of 4/4 at 110 BPM = exactly 120 s
SWING = 18              # delay applied to off-beat 16ths
rng = random.Random(1234)

# General MIDI percussion note numbers
KICK, SNARE, RIM, HAT, PEDAL, OPEN = 36, 38, 37, 42, 44, 46
RIDE, BELL, CRASH, CRASH2, SPLASH, CHINA = 51, 53, 49, 57, 55, 52
T_HI, T_HM, T_LM, T_LO, F_HI, F_LO = 50, 48, 47, 45, 43, 41
COWBELL, TIMB_HI, TIMB_LO = 56, 65, 66
CONGA_M, CONGA_O, CONGA_LO = 62, 63, 64
CLAVES, WB_HI, WB_LO, AGOGO_HI, AGOGO_LO = 75, 76, 77, 67, 68

# Consistent placement for each limb: the hat foot pushes slightly ahead
# of the beat, the snare hand lays back.
LIMB_OFFSET = {'RH': -3, 'LH': 7, 'RF': 0, 'LF': -5}

# (tick, limb) -> (note, velocity). One entry per limb per instant, so at
# most two hands and two feet ever strike together.
events = {}


def hit(bar, step, note, vel, limb, extra=0):
    t = bar * BAR + int(step * S16)
    if int(step) % 2 == 1:
        t += SWING
    t += LIMB_OFFSET[limb] + extra
    t = max(0, t)
    vel = max(1, min(127, int(vel + rng.randint(-3, 3))))
    key = (t, limb)
    if key not in events or events[key][1] < vel:
        events[key] = (note, vel)


# The motif: a one-bar syncopated cell (16th-note step, accent weight).
MOTIF = [(0, 1.0), (3, 0.9), (6, 0.8), (10, 0.95), (11, 0.7), (14, 1.0)]


def motif(bar, voices, dyn, shift=0, kick=True):
    """Play the motif, orchestrating each hit onto the given voices."""
    for i, (st, acc) in enumerate(MOTIF):
        s = (st + shift) % 16
        note = voices[i % len(voices)]
        limb = 'RH' if i % 2 == 0 else 'LH'
        hit(bar, s, note, dyn * acc, limb)
        if kick and acc >= 0.9:
            hit(bar, s, KICK, dyn * 0.9, 'RF')


def groove(bar, dyn, cym=HAT, ghosts=0.5, kick_pat=(0, 7, 8, 10), dens16=False,
           pedal=False, motif_kicks=False):
    """Backbeat groove: cymbal in the right hand, snare with ghosts in the left."""
    for s in range(16):
        if s % 2 == 0 or dens16:
            acc = 1.0 if s % 4 == 0 else (0.8 if s % 2 == 0 else 0.55)
            n = cym
            if cym == HAT and s == 14 and bar % 2 == 1:
                n = OPEN
            hit(bar, s, n, dyn * 0.75 * acc, 'RH')
    for s in (4, 12):
        hit(bar, s, SNARE, dyn * 1.05, 'LH')
    for s in (3, 6, 9, 11, 15):
        if rng.random() < ghosts:
            hit(bar, s, SNARE, 28 + rng.randint(0, 10), 'LH')
    kp = [st for st, _ in MOTIF if st not in (4, 12)] if motif_kicks else kick_pat
    for s in kp:
        hit(bar, s, KICK, dyn * (0.95 if s % 4 == 0 else 0.8), 'RF')
    if pedal or cym != HAT:
        for s in (4, 12) if not pedal else (0, 4, 8, 12):
            hit(bar, s, PEDAL, dyn * 0.55, 'LF')


def fill(bar, start, dyn, toms=(T_HI, T_HM, T_LM, T_LO, F_HI, F_LO), triplet=False,
         crescendo=True):
    """Alternating-hand fill from `start` to the end of the bar, descending the toms."""
    if triplet:
        steps = [start + i * 4 / 3 for i in range(int((16 - start) * 3 / 4))]
    else:
        steps = list(range(start, 16))
    n = len(steps)
    for i, s in enumerate(steps):
        note = toms[min(len(toms) - 1, i * len(toms) // n)]
        v = dyn * (0.7 + 0.35 * i / max(1, n - 1)) if crescendo else dyn
        if i % 3 == 0:
            v *= 1.1
        hit(bar, s, note, v, 'RH' if i % 2 == 0 else 'LH')
        if i % 3 == 0:
            hit(bar, s, KICK, v * 0.85, 'RF')


def crash(bar, dyn, note=CRASH):
    hit(bar, 0, note, dyn, 'RH')
    hit(bar, 0, KICK, dyn, 'RF')


def latin(bar, dyn, busy=False):
    """Cowbell / timbale / conga groove with the feet holding time underneath."""
    for s in (0, 3, 6, 8, 10, 12, 14) if busy else (0, 3, 6, 10, 12):
        hit(bar, s, COWBELL, dyn * (0.9 if s in (0, 6, 12) else 0.65), 'RH')
    for s in (2, 7, 11, 15):
        hit(bar, s, TIMB_HI if s != 11 else TIMB_LO, dyn * 0.8, 'LH')
    for s in (4, 13):
        hit(bar, s, CONGA_O, dyn * 0.7, 'LH')
    for s in (1, 9):
        hit(bar, s, CONGA_M, 30, 'LH')
    for s in (0, 6, 8, 14):
        hit(bar, s, KICK, dyn * 0.85, 'RF')
    for s in (4, 12):
        hit(bar, s, PEDAL, dyn * 0.6, 'LF')


# ---------------------------------------------------------------- arrangement
b = 0
# 1) Intro, bars 0-3: state the motif alone on toms, sparse, with the hat foot keeping time.
for i in range(4):
    motif(b, [F_LO, T_LM, SNARE, F_HI, T_HM, SNARE], 72 + i * 6,
          kick=(i >= 2))
    for s in (0, 4, 8, 12):
        hit(b, s, PEDAL, 50, 'LF')
    if i == 3:
        fill(b, 12, 88)
    b += 1

# 2) Groove A, bars 4-11: the motif lives in the kick drum, ghost notes on the snare.
for i in range(8):
    if i == 0:
        crash(b, 110)
    groove(b, 88, ghosts=0.55, motif_kicks=True, pedal=False)
    if i == 3:
        fill(b, 13, 90)
    if i == 7:
        fill(b, 8, 98)
    b += 1

# 3) Latin section, bars 12-19: the motif is recast on cowbell and timbales.
for i in range(8):
    if i == 0:
        crash(b, 105, SPLASH)
    if i % 4 == 3:
        motif(b, [TIMB_HI, TIMB_LO, COWBELL, TIMB_LO, TIMB_HI, TIMB_LO], 100)
        for s in (4, 12):
            hit(b, s, PEDAL, 55, 'LF')
    else:
        latin(b, 82 + i * 2, busy=(i >= 4))
        if i % 2 == 1:
            hit(b, 14, CLAVES, 70, 'LH', 0)
    b += 1

# 4) Build, bars 20-27: ride cymbal, rising density, the motif displaced by an 8th.
for i in range(8):
    if i == 0:
        crash(b, 112, CHINA)
    groove(b, 90 + i * 2, cym=RIDE, ghosts=0.6 + i * 0.04, dens16=(i >= 4),
           kick_pat=(0, 6, 8, 11), pedal=True)
    if i in (1, 5):
        motif(b, [SNARE, T_HI, SNARE, F_HI, T_LM, SNARE], 100, shift=2, kick=False)
    if i == 3:
        fill(b, 12, 100, triplet=True)
    if i == 7:
        fill(b, 4, 108)
    b += 1

# 5) Breakdown, bars 28-33: quiet cross-stick and ride bell, lots of ghosts; release.
for i in range(6):
    if i == 0:
        hit(b, 0, CRASH2, 90, 'RH')
        hit(b, 0, KICK, 90, 'RF')
    for s in range(0, 16, 2):
        hit(b, s, BELL if s % 4 == 0 else RIDE, 58 if s % 4 == 0 else 42, 'RH')
    hit(b, 4, RIM, 70, 'LH')
    hit(b, 12, RIM, 70, 'LH')
    for s in (2, 7, 9, 15):
        hit(b, s, SNARE, 24 + rng.randint(0, 8), 'LH')
    for s in (0, 10):
        hit(b, s, KICK, 60, 'RF')
    for s in (4, 12):
        hit(b, s, PEDAL, 45, 'LF')
    if i >= 3:
        hit(b, 6, WB_HI, 55, 'LH')
        hit(b, 14, WB_LO, 55, 'LH')
    if i == 5:
        motif(b, [T_HI, T_HM, T_LM, T_LO, F_HI, F_LO], 70)
    b += 1

# 6) Climax, bars 34-45: 16th-note hats, double kick, trading groove and tom fills.
for i in range(12):
    dyn = 96 + i * 2
    if i % 4 == 0:
        crash(b, 120, CRASH if i % 8 == 0 else CRASH2)
    if i % 4 == 3:
        # full-bar solo phrase: motif then triplet fill
        motif(b, [SNARE, F_LO, SNARE, T_HI, F_HI, SNARE], dyn)
        fill(b, 12, dyn + 8, triplet=True)
        for s in range(0, 12, 2):
            hit(b, s, KICK, dyn * 0.7, 'RF')
        for s in (0, 4, 8):
            hit(b, s, PEDAL, 60, 'LF')
    else:
        groove(b, dyn, cym=HAT if i < 6 else RIDE, ghosts=0.7, dens16=True,
               kick_pat=(0, 3, 6, 8, 10, 11, 14) if i >= 6 else (0, 7, 8, 10))
        if i == 10:
            fill(b, 8, 112)
    b += 1

# 7) Return, bars 46-52: Groove A comes back, the motif stated on the full kit.
for i in range(7):
    if i == 0:
        crash(b, 118)
    if i == 3:
        motif(b, [CRASH, F_LO, SNARE, CRASH2, F_HI, SNARE], 112)
        for s in (4, 12):
            hit(b, s, PEDAL, 60, 'LF')
    else:
        groove(b, 94, ghosts=0.55, motif_kicks=True, pedal=False)
    if i == 5:
        fill(b, 12, 100)
    if i == 6:
        fill(b, 0, 115)
    b += 1

# 8) Ending, bars 53-54: final statement of the motif in unison hits, then one big hit.
motif(b, [CRASH, SNARE, CRASH2, SNARE, F_LO, CHINA], 120)
b += 1
hit(b, 0, CRASH, 127, 'RH')
hit(b, 0, CRASH2, 127, 'LH')
hit(b, 0, KICK, 127, 'RF')
b += 1

# ---------------------------------------------------------------- write MIDI
mid = mido.MidiFile(ticks_per_beat=PPQ)
tr = mido.MidiTrack()
mid.tracks.append(tr)
tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))

msgs = []
end_tick = (b - 1) * BAR
for (t, limb), (note, vel) in events.items():
    dur = PPQ * 2 if t >= end_tick else 60
    msgs.append((t, 1, note, vel))
    msgs.append((t + dur, 0, note, 0))
msgs.sort(key=lambda m: (m[0], m[1], m[2]))

now = 0
for t, on, note, vel in msgs:
    if on:
        tr.append(mido.Message('note_on', channel=9, note=note, velocity=vel, time=t - now))
    else:
        tr.append(mido.Message('note_off', channel=9, note=note, velocity=0, time=t - now))
    now = t
tr.append(mido.MetaMessage('end_of_track', time=PPQ))
mid.save('solo.mid')
