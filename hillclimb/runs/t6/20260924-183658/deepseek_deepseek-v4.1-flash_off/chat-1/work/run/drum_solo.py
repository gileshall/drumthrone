#!/usr/bin/env python3
"""drum_solo.py — generate a ~2 minute General MIDI drum solo on channel 10.

Only mido + stdlib.  Deterministic (fixed seed).  Writes solo.mid.

Design:
  * Motifs: A (kick/snare backbeat + ride pattern), B (16th ride run + ghost snares),
    C (double-bass burst + china accents), D (toms melodic motif).
  * Structure: Intro A A' B A'' C B' D C' A''' Outro (final downbeat).
  * Humanize: micro-timing jitter, velocity phrasing, ghost notes, accents,
    slight rush/drag of the pulse per phrase.
  * Playability: at most 4 simultaneous notes; hands/feet mapped mentally.
"""

import random
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

# ----------------------------------------------------------------------------
# Kit (General MIDI, channel 10)
# ----------------------------------------------------------------------------
KICK      = 36
SNARE     = 38
GSNARE    = 40   # ghost rim/cross-stick-ish
SIDE_ST   = 37   # side stick
CLAP      = 39
HAT       = 42
HAT_OPEN  = 46
HAT_PED   = 44
RIDE      = 51
RIDE_BELL = 53
CRASH     = 49
CRASH2    = 57
SPLASH    = 55
CHINA     = 52
T1        = 50   # high tom
T2        = 48   # mid tom
T3        = 47   # low-mid tom
T4        = 45   # floor tom
T5        = 43   # low floor tom
TAMB      = 54   # tambourine
COWBELL   = 56
SHAKER    = 82   # not GM drum but in range; ok
TRI       = 81   # open triangle (perc color)
CABASA    = 69   # cabasa
WHISTLE   = 71
CLAVES    = 75   # claves (perc color)
MARACAS   = 70
TIMBALE_H = 65
TIMBALE_L = 66
AGOGO_H   = 67
AGOGO_L   = 68

# ----------------------------------------------------------------------------
# Timing
# ----------------------------------------------------------------------------
PPQ = 480
BEAT = PPQ                       # 1 beat = quarter
SIX  = PPQ // 4                  # 16th
THIRT = PPQ // 3                 # 8th-triplet
SIXT  = PPQ // 6                 # 16th-triplet
THIRT2 = PPQ * 2 // 3            # quarter-triplet

def ppq(n): return int(round(n))
def b(n):   return ppq(n * BEAT)

# ----------------------------------------------------------------------------
# Global random
# ----------------------------------------------------------------------------
rng = random.Random(0xDEADBEEF)

# ----------------------------------------------------------------------------
# Humanization helpers — per-note timing and velocity
# ----------------------------------------------------------------------------
def jitter(amount=0.010):
    """seconds-level jitter expressed in ticks. 0.010 beat = ~1/100 beat."""
    return int(rng.gauss(0, amount * BEAT))

def vcurve(v, base=90, span=30, accent=False, ghost=False):
    if ghost:
        v = base - span + rng.randint(-4, 4)
    elif accent:
        v = base + span + rng.randint(-4, 6)
    else:
        v = base + rng.randint(-8, 8)
    return max(1, min(127, int(v)))

# ----------------------------------------------------------------------------
# Event list:  (time_ticks, channel, note, velocity, dur_ticks)
# We collect absolute times then convert.
# ----------------------------------------------------------------------------
events = []

def hit(t, note, vel=100, dur=30, ch=9):
    events.append((int(round(t)), ch, note, int(vel), int(dur)))

def flam(t, note, vel=105, spread=8, dur=30):
    """grace-note flam: softer pre-hit then main."""
    hit(t - spread, note, max(1, vel - 30), dur, ch=9)
    hit(t, note, vel, dur, ch=9)

def drag(t, note, vel=100, spread=10, dur=30):
    """two soft grace notes."""
    hit(t - spread, note, max(1, vel - 35), dur, ch=9)
    hit(t - spread // 2, note, max(1, vel - 22), dur, ch=9)
    hit(t, note, vel, dur, ch=9)

def roll(t0, length, note, vel_start=70, vel_end=115, step=SIX // 2, curve="lin", dur=20):
    """Snare/hat roll occupying [t0, t0+length)."""
    n = max(1, int(round(length / step)))
    for i in range(n):
        if curve == "lin":
            v = vel_start + (vel_end - vel_start) * i / max(1, n - 1)
        elif curve == "exp":
            v = vel_start + (vel_end - vel_start) * (i / max(1, n - 1)) ** 1.7
        elif curve == "updown":
            u = i / max(1, n - 1)
            v = vel_start + (vel_end - vel_start) * (u if u < 0.5 else 1 - u) * 2 * 0.5 + (vel_end - vel_start) * 0.5 * (u < 0.5)
            # simpler: mountain
        else:
            v = (vel_start + vel_end) / 2
        # mountain curve
        if curve == "updown":
            u = i / max(1, n - 1)
            shape = 1 - abs(2 * u - 1)
            v = vel_start + (vel_end - vel_start) * shape
        t = t0 + i * step + jitter(0.006)
        hit(t, note, vcurve(int(v), 90, 20), dur)

# ----------------------------------------------------------------------------
# Motif builders.  Each takes an absolute start time and a phrase pulse
# offset ("feel": fraction of beat we push/pull).
# ----------------------------------------------------------------------------

def pulse(t0, feel=0.0):
    """Global pulse offset for a phrase — in beats."""
    return ppq(feel * BEAT)

# --- Motif A: laid-back backbeat with ride --------------
def motif_A(t0, bars=2, feel=0.0, dynam=0.0):
    t = t0
    p = pulse(t0, feel)
    for bar in range(bars):
        barbase = t + bar * 4 * BEAT + p
        # ride pattern: 1, 2 &, 3, 4 -- with a swung & on 2 and 4 sometimes
        ride_pts = [0, 1.0, 1.5, 2.0, 3.0]
        for k, bp in enumerate(ride_pts):
            v = 90
            if k in (0, 3):
                v = 100
            hit(barbase + b(bp) + jitter(0.008), RIDE, vcurve(v, 88, 18, accent=(bp in (0, 2.0))))
        # kick on 1 and 3
        hit(barbase + jitter(0.006), KICK, vcurve(112, 100, 15, accent=True), 40)
        hit(barbase + b(2) + jitter(0.006), KICK, vcurve(104, 100, 12))
        # snare backbeat 2 and 4
        hit(barbase + b(1) + jitter(0.006), SNARE, vcurve(112, 100, 15, accent=True), 35)
        hit(barbase + b(3) + jitter(0.006), SNARE, vcurve(112, 100, 15, accent=True), 35)
        # ghost snares
        for gb in (0.75, 1.75, 2.75, 3.25):
            if rng.random() < 0.7:
                hit(barbase + b(gb) + jitter(0.010), GSNARE,
                    vcurve(0, 68, 22, ghost=True), 20)
        # hat foot on 2 and 4
        hit(barbase + b(1) - 2, HAT_PED, 60, 20)
        hit(barbase + b(3) - 2, HAT_PED, 60, 20)
    return t + bars * 4 * BEAT

# --- Motif B: 16th ride run with ghost snare chatter -----
def motif_B(t0, bars=2, feel=0.0):
    p = pulse(t0, feel)
    for bar in range(bars):
        barbase = t0 + bar * 4 * BEAT + p
        # 16th ride, uneven dynamics "ta-ka-ta-ka"
        for i in range(16):
            bp = i / 4.0
            if i % 4 == 0:
                v = 104
            elif i % 4 == 2:
                v = 92
            else:
                v = 82 + rng.randint(-4, 4)
            # last 16th of bars 2 & 4 opens
            n = RIDE
            if (bar % 2 == 1) and i == 15:
                n = RIDE_BELL
                v = 108
            hit(barbase + b(bp) + jitter(0.006), n, v, 18)
        # kick 1, and "&" of 3
        hit(barbase + jitter(0.006), KICK, 110, 40)
        hit(barbase + b(2.5) + jitter(0.006), KICK, 100, 40)
        # snare backbeat and ghost fill chatter
        hit(barbase + b(1) + jitter(0.006), SNARE, 112, 30)
        hit(barbase + b(3) + jitter(0.006), SNARE, 112, 30)
        for gb in (0.5, 1.5, 2.5, 3.5):
            if rng.random() < 0.55:
                hit(barbase + b(gb) + jitter(0.012), GSNARE, 62 + rng.randint(-6, 6), 18)
        hit(barbase + b(1) - 2, HAT_PED, 58, 20)
        hit(barbase + b(3) - 2, HAT_PED, 58, 20)
    return t0 + bars * 4 * BEAT

# --- Motif C: double-bass burst + china accents -------------
def motif_C(t0, bars=2, feel=0.0):
    p = pulse(t0, feel)
    for bar in range(bars):
        barbase = t0 + bar * 4 * BEAT + p
        # china on 1, splash on & of 2 and 4
        flam(barbase + jitter(0.004), CHINA, 118, 10, 60)
        hit(barbase + b(1.5), SPLASH, 96, 40)
        hit(barbase + b(3.5), SPLASH, 92, 40)
        # ride bell 8ths
        for i in range(8):
            bp = i / 2.0
            v = 100 if i % 2 == 0 else 84
            hit(barbase + b(bp) + jitter(0.006), RIDE_BELL, v, 18)
        # double-bass: 16th bursts
        for i in range(16):
            if i % 2 == 0 or rng.random() < 0.5:
                # skip a few for feel
                if i in (6, 7, 14):
                    continue
                v = 104 if i % 4 == 0 else 88 + rng.randint(-4, 4)
                hit(barbase + b(i / 4.0) + jitter(0.004), KICK, v, 26)
        # snare backbeats
        hit(barbase + b(1) + jitter(0.004), SNARE, 114, 28)
        hit(barbase + b(3) + jitter(0.004), SNARE, 114, 28)
        # occasional open hat
        if bar % 2 == 1:
            hit(barbase + b(3.75) + jitter(0.006), HAT_OPEN, 100, 60)
    return t0 + bars * 4 * BEAT

# --- Motif D: melodic toms motif --------------
def motif_D(t0, bars=2, feel=0.0, low=False):
    """A singable tom melody; 'low' transposes one tom down."""
    p = pulse(t0, feel)
    # base pattern in 16ths over 4 beats: T1 T2 T3 T2 | T4 T3 T2 T1 ...
    if low:
        seq = [T5, T4, T3, T4,  T2, T3, T4, T3,
               T5, T4, T3, T2,  T1, T2, T3, T4]
    else:
        seq = [T1, T2, T3, T2,  T3, T4, T3, T2,
               T1, T3, T2, T4,  T3, T1, T2, T3]
    for bar in range(bars):
        barbase = t0 + bar * 4 * BEAT + p
        for i, n in enumerate(seq):
            bp = i / 4.0
            if i % 4 == 0:
                v = 106
            elif i % 4 == 2:
                v = 92
            else:
                v = 80
            # little knock on kik under
            hit(barbase + b(bp) + jitter(0.006), n, vcurve(v, 92, 16), 22)
        hit(barbase + jitter(0.006), KICK, 108, 40)
        hit(barbase + b(2.5) + jitter(0.006), KICK, 98, 40)
        # hat foot anchors
        hit(barbase + b(1) - 2, HAT_PED, 58, 18)
        hit(barbase + b(3) - 2, HAT_PED, 58, 18)
    return t0 + bars * 4 * BEAT

# --- Fill helpers ---
def fill_16(t0, length, end_land=SNARE):
    """Descending 16th tom fill, ending on a flam on end_land."""
    n = int(round(length / (BEAT / 4)))
    pitches = [T1, T2, T3, T4, T3, T2, T1, T4, T3, T5, T4, T2]
    for i in range(n - 1):
        bp = i * (BEAT / 4)
        n_ = pitches[i % len(pitches)]
        v = 92 + (i * 2 % 20)
        hit(t0 + bp + jitter(0.006), n_, vcurve(v, 92, 14), 18)
    # land
    flam(t0 + length - jitter(0.004), end_land, 118, 8, 30)

def fill_triplets(t0, length, end_land=RIDE):
    n = max(1, int(round(length / THIRT)))
    seq = [T1, T2, T3, T2]
    for i in range(n - 1):
        bp = i * THIRT
        n_ = seq[i % 4]
        v = 84 + (i * 3 % 25)
        hit(t0 + bp + jitter(0.008), n_, v, 16)
    flam(t0 + length - jitter(0.004), end_land, 110, 8, 30)

def fill_rush(t0, length, end_land=CHINA):
    """Fill that accelerates — subdividing finer as it goes."""
    t = t0
    while t < t0 + length - BEAT / 4:
        remain = (t0 + length) - t
        if remain > BEAT:
            step = THIRT   # 8th-triplet
        elif remain > BEAT / 2:
            step = SIX     # 16th
        else:
            step = SIX // 2  # 32nd
        n_ = [T1, T2, T3, T4, T3, T2][int((t - t0) / SIX) % 6]
        v = 86 + int(60 * (t - t0) / max(1, length))
        hit(t + jitter(0.006), n_, vcurve(min(v, 120), 96, 18), 16)
        t += step
    flam(t0 + length - jitter(0.003), end_land, 122, 10, 70)

# ----------------------------------------------------------------------------
# Compose the solo.  ~2 minutes at 96 BPM: 2 min = 120 s.
# 96 BPM -> 1 beat = 0.625 s.  120 s / 0.625 = 192 beats = 48 bars of 4/4.
# We'll keep tempo around 96, vary slightly with phrase feel.
# ----------------------------------------------------------------------------
BPM = 96
TEMPO = bpm2tempo(BPM)
beat_ms = 60_000 / BPM

# Build sections by absolute time.
t = 0

# --- Intro (4 bars, 16 beats): solo snare & hat, quiet, builds. ---
intro_len = 16 * BEAT
# count-in on hat foot and side stick
for i in range(16):
    bp = i * BEAT
    if i % 2 == 0:
        hit(t + bp + jitter(0.008), HAT, 62 + i * 2, 18)
    else:
        hit(t + bp + jitter(0.008), HAT, 58 + i * 2, 14)
for i in range(4):
    # side stick on 2 and 4 of each bar, growing
    hit(t + i * 4 * BEAT + BEAT + jitter(0.006), SIDE_ST, 70 + i * 4, 24)
    hit(t + i * 4 * BEAT + 3 * BEAT + jitter(0.006), SIDE_ST, 70 + i * 4, 24)
# little pickup before A
roll(t + 14 * BEAT, 2 * BEAT, SNARE, 70, 120, step=SIX, curve="lin", dur=16)
t += intro_len

# --- A: state the theme (4 bars) ---
t = motif_A(t, bars=2, feel=-0.004, dynam=0.0)
t = motif_A(t, bars=2, feel=0.0)

# --- A' : vary with open hat and ghost notes (4 bars) ---
def motif_A_var(t0, bars=2, feel=0.0):
    p = pulse(t0, feel)
    for bar in range(bars):
        barbase = t0 + bar * 4 * BEAT + p
        ride_pts = [0, 1.0, 1.5, 2.0, 2.5, 3.0]
        for k, bp in enumerate(ride_pts):
            n = RIDE_BELL if bp in (0, 2.0) else RIDE
            v = 100 if k in (0, 3) else 88
            hit(barbase + b(bp) + jitter(0.008), n, vcurve(v, 90, 16), 18)
        hit(barbase + jitter(0.006), KICK, 112, 40)
        hit(barbase + b(2.5) + jitter(0.006), KICK, 100, 40)
        hit(barbase + b(1) + jitter(0.005), SNARE, 114, 30)
        hit(barbase + b(3) + jitter(0.005), SNARE, 114, 30)
        # more ghost chatter
        for gb in (0.5, 0.75, 1.5, 1.75, 2.75, 3.5, 3.75):
            if rng.random() < 0.6:
                hit(barbase + b(gb) + jitter(0.012), GSNARE, 60 + rng.randint(-6, 8), 16)
        hit(barbase + b(1) - 2, HAT_PED, 60, 20)
        hit(barbase + b(3) - 2, HAT_PED, 60, 20)
    return t0 + bars * 4 * BEAT

t = motif_A_var(t, bars=2, feel=0.004)
# small fill to set up B
fill_16(t, 4 * BEAT, end_land=SNARE)
t += 4 * BEAT

# --- B: 16th ride run (4 bars) ---
t = motif_B(t, bars=2, feel=0.008)
t = motif_B(t, bars=2, feel=0.004)

# --- A'' : theme returns with heavier backbeat (4 bars) ---
def motif_A_heavy(t0, bars=2, feel=0.0):
    p = pulse(t0, feel)
    for bar in range(bars):
        barbase = t0 + bar * 4 * BEAT + p
        # crash on 1 of first bar only
        if bar == 0 and p == 0:
            hit(barbase + jitter(0.004), CRASH, 120, 200)
        for k, bp in enumerate([0, 1.0, 2.0, 2.5, 3.0]):
            v = 100 if bp in (0, 2.0) else 88
            hit(barbase + b(bp) + jitter(0.006), RIDE, v, 20)
        hit(barbase + jitter(0.005), KICK, 118, 40)
        hit(barbase + b(2) + jitter(0.005), KICK, 108, 40)
        hit(barbase + b(1) + jitter(0.004), SNARE, 118, 30)
        hit(barbase + b(3) + jitter(0.004), SNARE, 118, 30)
        # open hat & of 4
        hit(barbase + b(3.5) + jitter(0.006), HAT_OPEN, 96, 60)
        for gb in (0.75, 2.75):
            if rng.random() < 0.7:
                hit(barbase + b(gb) + jitter(0.010), GSNARE, 64, 16)
    return t0 + bars * 4 * BEAT

t = motif_A_heavy(t, bars=2, feel=0.0)
# fill into C: escalating triplets
fill_triplets(t, 4 * BEAT, end_land=CHINA)
t += 4 * BEAT

# --- C: double-bass burst + chinas (4 bars) ---
t = motif_C(t, bars=2, feel=-0.006)
t = motif_C(t, bars=2, feel=0.0)

# --- B' : 16th run returns, with toms trading (4 bars) ---
def motif_B_toms(t0, bars=2, feel=0.0):
    p = pulse(t0, feel)
    for bar in range(bars):
        barbase = t0 + bar * 4 * BEAT + p
        # alternating ride and toms
        for i in range(16):
            bp = i / 4.0
            if i % 4 == 0:
                n = RIDE; v = 104
            elif i % 4 == 1:
                n = T1; v = 94
            elif i % 4 == 2:
                n = RIDE; v = 92
            else:
                n = T2 if bar % 2 == 0 else T3; v = 88
            hit(barbase + b(bp) + jitter(0.006), n, vcurve(v, 92, 12), 18)
        hit(barbase + jitter(0.006), KICK, 110, 40)
        hit(barbase + b(1) + jitter(0.005), SNARE, 112, 30)
        hit(barbase + b(2.5) + jitter(0.005), KICK, 98, 40)
        hit(barbase + b(3) + jitter(0.005), SNARE, 112, 30)
    return t0 + bars * 4 * BEAT

t = motif_B_toms(t, bars=2, feel=0.006)
# Snare roll that swells into D
roll(t, 2 * BEAT, SNARE, 72, 112, step=SIX // 2, curve="exp", dur=14)
# crash into D
hit(t + 2 * BEAT, CRASH, 122, 240)
t += 2 * BEAT
# little drum break rest / crash tail — D starts on next downbeat
# So we effectively use the 2nd half of the 4-bar block for the roll + crash.
t += 2 * BEAT

# --- D: melodic toms motif (4 bars) ---
t = motif_D(t, bars=1, feel=0.004, low=False)
t = motif_D(t, bars=1, feel=0.0, low=True)
t = motif_D(t, bars=1, feel=0.006, low=False)
# 4th bar: fill into C'
fill_rush(t, 4 * BEAT, end_land=CHINA)
t += 4 * BEAT

# --- C' : double-bass, but faster and with splash/tambourine color (4 bars) ---
def motif_C_prime(t0, bars=2, feel=0.0):
    p = pulse(t0, feel)
    for bar in range(bars):
        barbase = t0 + bar * 4 * BEAT + p
        hit(barbase + jitter(0.003), CHINA, 120, 70)
        hit(barbase + b(1.5) + jitter(0.005), TAMB, 92, 30)
        hit(barbase + b(3.5) + jitter(0.005), TAMB, 92, 30)
        hit(barbase + b(2.0) + jitter(0.004), SPLASH, 98, 50)
        for i in range(8):
            bp = i / 2.0
            for k in (0, 0.5):
                # 8th + 16th double bass around
                pass
        # double bass 16th with accents
        for i in range(16):
            bp = i / 4.0
            v = 108 if i % 4 == 0 else 88
            if rng.random() < 0.85:
                hit(barbase + b(bp) + jitter(0.004), KICK, vcurve(v, 96, 14), 22)
        # snare with flams on 2 & 4
        flam(barbase + b(1) + jitter(0.004), SNARE, 118, 9, 26)
        flam(barbase + b(3) + jitter(0.004), SNARE, 118, 9, 26)
        # ride bell 8ths
        for i in range(4):
            bp = i + 0.5
            if bp < 4:
                hit(barbase + b(bp) + jitter(0.006), RIDE_BELL, 96, 16)
    return t0 + bars * 4 * BEAT

t = motif_C_prime(t, bars=2, feel=-0.005)
t = motif_C_prime(t, bars=2, feel=0.003)

# --- A''' : final statement of theme, big and wide (4 bars) ---
t = motif_A_heavy(t, bars=2, feel=0.0)
# Final bar: monster fill — hands and feet together
fill_rush(t, 2 * BEAT, end_land=SNARE)
t += 2 * BEAT
# last two beats: two big flams and a crash land
flam(t + jitter(0.003), SNARE, 124, 12, 40)
hit(t + BEAT + jitter(0.004), KICK, 120, 60)
hit(t + BEAT + jitter(0.004), SNARE, 124, 40)
t += 2 * BEAT

# --- Outro: final hit and one breath ---
# downbeat with crash + kick + snare together
hit(t + jitter(0.002), CRASH, 127, 480)
hit(t + jitter(0.002), KICK, 122, 60)
hit(t + jitter(0.002), SNARE, 126, 60)
# a chinese accent ringing out
hit(t + jitter(0.003), CHINA, 118, 400)

# ----------------------------------------------------------------------------
# Sort events, ensure playability (<= 4 simultaneous), build MIDI
# ----------------------------------------------------------------------------
events.sort(key=lambda e: (e[0], e[2]))

# Enforce max simultaneity (safety net; our writing already respects it).
# Only for very close times (within a few ticks).  Drop extras beyond 4.
active = []
filtered = []
for ev in events:
    t_ev = ev[0]
    active = [a for a in active if a[0] > t_ev]
    if len(active) < 4:
        filtered.append(ev)
        active.append((t_ev + max(4, ev[4]), ev[2]))

events = filtered

# Build one track.
mid = MidiFile(ticks_per_beat=PPQ)
track = MidiTrack()
mid.tracks.append(track)

# Track name
track.append(MetaMessage('track_name', name='Drum Solo', time=0))
# Set tempo
track.append(MetaMessage('set_tempo', tempo=TEMPO, time=0))
# Time signature 4/4
track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
# Channel for percussion
track.append(MetaMessage('midi_port', port=0, time=0))

# Convert absolute ticks -> delta times with note on/off pairs.
sched = []  # (time, order, msg_bytes)
for (t_abs, ch, note, vel, dur) in events:
    sched.append((t_abs, 0, (0x90 | ch, note, vel)))
    off = t_abs + max(1, dur)
    sched.append((off, 1, (0x80 | ch, note, 0)))

sched.sort(key=lambda x: (x[0], x[1]))

prev = 0
for (t_abs, _order, msg) in sched:
    dt = max(0, t_abs - prev)
    prev = t_abs
    status, d1, d2 = msg
    track.append(Message.from_bytes([status, d1, d2], time=dt))

mid.save('solo.mid')
print("Wrote solo.mid with", len(events), "drum hits,",
      "length ~", prev / PPQ * (60 / BPM), "s")
