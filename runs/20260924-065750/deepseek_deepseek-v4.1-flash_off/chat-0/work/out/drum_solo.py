#!/usr/bin/env python3
"""Two-minute General MIDI drum solo (channel 10) using mido only.

Deterministic: no random, no time(), no os.  Fixed tempo and fixed note
events, so solo.mid is identical on every run.

Design:
  - Motif A:  "boom-bap" kick/snare cell, stated, varied, recalled.
  - Motif B:  tom/bell melodic cell over an ostinato.
  - Motif C:  half-time backbeat with open hat/splash (release).
  - Dynamics: explicit accents vs ghosts; swung 16ths via fixed offsets.
  - Playability: <= 4 simultaneous strikes per tick (2 hands + 2 feet).
"""

import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

PPQ = 480
TPB = 4                              # beats per bar (4/4)
TEMPO_US = int(60_000_000 / 92)      # 92 BPM

# ----------------------------------------------------------------------
# General MIDI percussion note numbers (channel 10).
# ----------------------------------------------------------------------
KICK   = 35
SNARE  = 38
SNARE2 = 40
LOTOM  = 41
CLHH   = 42
HTFT   = 43
OPHH   = 46
MTFT   = 47
HITOM  = 48
CRASH1 = 49
HITOM2 = 50
RIDE1  = 51
CHINA  = 52
RIDEB  = 53
TAMB   = 54
SPLASH = 55
COWBELL= 56
CRASH2 = 57
RIDE2  = 59

# ----------------------------------------------------------------------
# Velocity character (deterministic, expressive).
# ----------------------------------------------------------------------
V_GHOST  = 18
V_SOFT   = 34
V_ACCENT = 100
V_MED    = 62
V_HARD   = 112
V_LAST   = 88

SWING = PPQ // 8        # 60 ticks: swing offset for offbeat 16ths
PUSH  = -18             # push ahead
LAY   = 24              # laid back

# Swung 16th grid within one beat.
S16_A = 0
S16_B = SWING
S16_C = PPQ // 2
S16_D = PPQ // 2 + SWING

# ----------------------------------------------------------------------
# Notation infrastructure.
# ----------------------------------------------------------------------
class Solo:
    def __init__(self):
        self.notes = []      # (abs_tick, note, vel, dur)

    def add(self, bar, beat, extra=0, note=SNARE, vel=V_MED, dur=10):
        t = int(bar * TPB * PPQ + beat * PPQ + extra)
        if t < 0:
            t = 0
        self.notes.append((t, note, vel, dur))

    def add_raw(self, tick, note, vel, dur=10):
        self.notes.append((max(0, int(tick)), note, vel, dur))

# ----------------------------------------------------------------------
# Strike-limit guard: at most 4 simultaneous strikes per tick.
# ----------------------------------------------------------------------
def enforce_playable(notes):
    by_tick = {}
    for t, n, v, d in notes:
        by_tick.setdefault(t, []).append((n, v, d))
    out = []
    for t in sorted(by_tick):
        lst = sorted(by_tick[t], key=lambda x: -x[1])   # loudest survive
        keep = lst[:4]
        out.extend((t, n, v, d) for n, v, d in keep)
    return out

# ----------------------------------------------------------------------
# Convenience wrappers.
# ----------------------------------------------------------------------
def add_kick(s, bar, beat, off=0, vel=96, dur=8):
    s.add(bar, beat, off, KICK, vel, dur)

def add_snare(s, bar, beat, off=0, vel=V_ACCENT, dur=8):
    s.add(bar, beat, off, SNARE, vel, dur)

def add_hat(s, bar, beat, off=0, vel=V_MED, open_h=False, dur=6):
    s.add(bar, beat, off, OPHH if open_h else CLHH, vel, dur)

def add_ghost(s, bar, beat, off=0, vel=V_GHOST, voice=SNARE2):
    s.add(bar, beat, off, voice, vel, 6)

def add_ride(s, bar, beat, off=0, vel=V_MED, bell=False, dur=8):
    s.add(bar, beat, off, RIDEB if bell else RIDE2, vel, dur)

def add_crash(s, bar, beat, off=0, vel=V_HARD, c=CRASH1, dur=PPQ * 2):
    s.add(bar, beat, off, c, vel, dur)

def add_tom(s, bar, beat, off=0, note=LOTOM, vel=V_MED, dur=10):
    s.add(bar, beat, off, note, vel, dur)

def add_aux(s, bar, beat, off=0, note=TAMB, vel=V_MED, dur=8):
    s.add(bar, beat, off, note, vel, dur)

# ----------------------------------------------------------------------
# Motif A — "boom-bap" cell: K . S . / K . S S with ghosted snare.
# ----------------------------------------------------------------------
def motif_A(s, bar, lead_in=True):
    add_kick(s, bar, 0, 0, V_ACCENT)
    add_kick(s, bar, 2, 0, V_HARD)
    add_snare(s, bar, 1, 0, V_ACCENT)
    add_snare(s, bar, 3, 0, V_LAST)
    add_ghost(s, bar, 0, S16_B)
    add_ghost(s, bar, 0, S16_D)
    add_ghost(s, bar, 2, S16_B)
    add_ghost(s, bar, 2, S16_D)
    if lead_in:
        for b in range(4):
            add_hat(s, bar, b, 0, V_MED)
            add_hat(s, bar, b, S16_C, V_SOFT)

# ----------------------------------------------------------------------
# Motif B — tom/bell melodic cell over a kick ostinato.
# ----------------------------------------------------------------------
def motif_B(s, bar):
    add_tom(s, bar, 0, 0, LOTOM, V_ACCENT, 14)
    add_tom(s, bar, 1, 0, MTFT, V_MED, 12)
    add_tom(s, bar, 2, S16_B, HITOM, V_MED, 12)
    add_ride(s, bar, 3, 0, V_ACCENT, bell=True)
    add_kick(s, bar, 1, S16_C, V_MED)
    add_kick(s, bar, 3, S16_D, V_SOFT)

# ----------------------------------------------------------------------
# Motif C — half-time backbeat with open hat / splash, laid back.
# ----------------------------------------------------------------------
def motif_C(s, bar, openhat=True):
    add_kick(s, bar, 0, LAY // 2, V_HARD)
    add_snare(s, bar, 2, 0, V_ACCENT)
    if openhat:
        add_hat(s, bar, 1, S16_C, V_MED, open_h=True)
    add_aux(s, bar, 3, S16_B, SPLASH, V_SOFT)
    add_ghost(s, bar, 0, S16_D)

# ----------------------------------------------------------------------
# Ride pattern for velocity contrast.
# ----------------------------------------------------------------------
def ride_pattern(s, bar, swing=True, bell=False, base=V_MED, push=0):
    for b in range(4):
        if swing:
            offs = [0, S16_B, S16_C, PPQ - SWING]
        else:
            offs = [0, PPQ // 2]
        for i, off in enumerate(offs):
            v = base if i == 0 else max(V_GHOST, base - 20)
            add_ride(s, bar, b, off + push, v, bell=bell)

# ----------------------------------------------------------------------
# Fill helpers.
# ----------------------------------------------------------------------
def fill_ruff(s, bar, beat, base_vel=V_MED):
    s.add(bar, beat, 0, SNARE, base_vel + 18, 8)
    s.add(bar, beat, S16_B, SNARE2, base_vel, 6)
    s.add(bar, beat, S16_C, SNARE, base_vel + 10, 8)
    s.add(bar, beat, S16_D, SNARE2, base_vel - 6, 6)

def fill_toms(s, bar, beat, up=True):
    notes = [LOTOM, MTFT, HITOM, HITOM2] if up else [HITOM2, HITOM, MTFT, LOTOM]
    for i, n in enumerate(notes):
        off = i * (PPQ // 4)
        add_tom(s, bar, beat, off, n, V_MED + i * 6, 10)

# ======================================================================
# Build the piece.
# ======================================================================
s = Solo()

# --- INTRO (bars 0-3): motif A stated plainly, building confidence. ----
motif_A(s, 0)
motif_A(s, 1)
# Variation: displacement and ghost density
add_kick(s, 2, 0, 0, V_ACCENT)
add_snare(s, 2, 1, 0, V_ACCENT)
add_kick(s, 2, 2, S16_B, V_HARD)
add_snare(s, 2, 3, 0, V_LAST)
add_ghost(s, 2, 0, S16_D)
add_ghost(s, 2, 1, S16_B)
add_ghost(s, 2, 3, S16_C)
for b in range(4):
    for off in (0, S16_C, PPQ - SWING):
        add_hat(s, 2, b, off, V_MED - 8)
# Bar 3: A + crash on 1 and open hat lift
add_crash(s, 3, 0, 0, V_HARD, CRASH1)
motif_A(s, 3, lead_in=False)
add_hat(s, 3, 1, S16_C, V_SOFT, open_h=True)
add_hat(s, 3, 3, S16_C, V_SOFT, open_h=True)

# --- GROOVE 1 (bars 4-11): develop A with more ghost interplay. -------
for bar in range(4, 8):
    motif_A(s, bar)
    if bar % 2 == 0:
        add_kick(s, bar, 3, S16_B, V_MED)
    else:
        add_kick(s, bar, 1, S16_D, V_SOFT)
    add_ghost(s, bar, 1, PPQ - SWING)
    add_ghost(s, bar, 3, S16_B)

for bar in range(8, 12):
    if bar % 2 == 0:
        motif_A(s, bar)
        add_hat(s, bar, 1, 0, V_SOFT, open_h=True)
    else:
        add_kick(s, bar, 0, 0, V_ACCENT)
        add_snare(s, bar, 1, 0, V_ACCENT)
        add_kick(s, bar, 2, S16_B, V_HARD)
        add_snare(s, bar, 3, 0, V_LAST)
        for b in range(4):
            for off in (0, S16_B, S16_C, PPQ - SWING):
                add_hat(s, bar, b, off, V_SOFT)

# --- MOTIF B (bars 12-19): anthemic tom/bell melody. ----------------
add_crash(s, 12, 0, 0, V_HARD, CRASH2)
for bar in range(12, 16):
    motif_B(s, bar)
    if bar % 2 == 1:
        add_ride(s, bar, 1, S16_B, V_ACCENT, bell=True)
        add_tom(s, bar, 2, 0, HITOM, V_MED, 12)
        add_tom(s, bar, 3, S16_C, HITOM2, V_SOFT, 12)
for bar in range(16, 20):
    motif_A(s, bar, lead_in=False)
    ride_pattern(s, bar, swing=True, bell=False, base=V_MED - 10)
    add_ghost(s, bar, 2, S16_D, V_GHOST)

# --- RELEASE (bars 20-23): Motif C, half-time, laid back. -------------
add_aux(s, 20, 0, 0, SPLASH, V_MED, PPQ)
for bar in range(20, 24):
    motif_C(s, bar, openhat=(bar != 23))
    add_ghost(s, bar, 2, PPQ - LAY, V_GHOST)
    add_ghost(s, bar, 3, S16_B + LAY, V_GHOST)
add_crash(s, 23, 3, S16_C, V_MED, SPLASH, PPQ * 2)

# --- BUILD (bars 24-31): Motif A pushed, dynamic ramp. ---------------
add_crash(s, 24, 0, 0, V_HARD, CRASH1)
for i, bar in enumerate(range(24, 32)):
    push = PUSH + i
    add_kick(s, bar, 0, push, V_ACCENT + i * 2)
    add_snare(s, bar, 1, push, V_ACCENT + i * 2)
    add_kick(s, bar, 2, push, V_HARD + i * 2)
    add_snare(s, bar, 3, push, min(127, V_LAST + i))
    n_hits = 2 + (i // 2)
    step = PPQ // max(1, n_hits)
    for j in range(n_hits):
        add_hat(s, bar, 0, j * step + push, max(V_GHOST, V_MED - 10 + i * 3))
    if i >= 4:
        add_ghost(s, bar, 1, S16_B, V_GHOST + i)
        add_ghost(s, bar, 3, S16_D, V_GHOST + i)

# --- DEVELOPMENT (bars 32-45): motives interleaved. ------------------
for bar in range(32, 36):
    motif_B(s, bar)
    add_kick(s, bar, 0, 0, V_HARD)
    add_kick(s, bar, 2, S16_C, V_MED)
    add_snare(s, bar, 3, S16_B, V_ACCENT)
    if bar == 35:
        fill_ruff(s, bar, 3, V_MED)
for bar in range(36, 40):
    ride_pattern(s, bar, swing=True, bell=True, base=V_MED, push=LAY // 2)
    add_kick(s, bar, 0, LAY // 2, V_HARD)
    add_snare(s, bar, 2, LAY // 2, V_ACCENT)
    add_ghost(s, bar, 1, S16_D, V_GHOST)
    if bar == 39:
        fill_toms(s, bar, 3, up=True)
for bar in range(40, 44):
    motif_C(s, bar, openhat=(bar % 2 == 0))
    add_kick(s, bar, 1, LAY // 2, V_MED)
    add_ghost(s, bar, 0, S16_B + LAY, V_GHOST)
add_kick(s, 44, 0, 0, V_ACCENT)
add_snare(s, 44, 1, 0, V_ACCENT)
add_tom(s, 44, 2, 0, LOTOM, V_MED, 12)
add_ride(s, 44, 2, S16_C, V_MED, bell=True)
add_kick(s, 44, 3, 0, V_HARD)
add_snare(s, 44, 3, S16_C, V_LAST)
fill_toms(s, 45, 1, up=True)
add_crash(s, 45, 3, S16_C, V_HARD, CRASH2)

# --- DENSE PEAK (bars 46-53). ----------------------------------------
add_crash(s, 46, 0, 0, V_HARD, CRASH1)
for bar in range(46, 54):
    add_kick(s, bar, 0, 0, V_HARD)
    add_kick(s, bar, 1, S16_D, V_MED)
    add_kick(s, bar, 2, 0, V_HARD)
    add_kick(s, bar, 3, S16_B, V_MED)
    add_snare(s, bar, 1, 0, V_ACCENT)
    add_snare(s, bar, 3, 0, V_LAST)
    for b in range(4):
        for off in (0, S16_B, S16_C, PPQ - SWING):
            if off == 0:
                add_hat(s, bar, b, off, V_MED)
            else:
                add_hat(s, bar, b, off, V_GHOST + 4)
    if bar % 2 == 0:
        add_ghost(s, bar, 0, S16_C)
        add_ghost(s, bar, 2, S16_C)
    else:
        add_ghost(s, bar, 1, S16_B)
        add_ghost(s, bar, 3, S16_D)

# --- BREAK (bars 54-55): sudden space, tension. ----------------------
add_crash(s, 54, 0, 0, V_HARD, CHINA)
add_kick(s, 54, 0, 0, V_HARD)
add_tom(s, 54, 1, S16_C, LOTOM, V_MED, 12)
add_ghost(s, 54, 2, 0, V_GHOST, SNARE2)
add_snare(s, 54, 3, S16_B, V_SOFT)
add_tom(s, 55, 0, 0, MTFT, V_SOFT, 12)
add_snare(s, 55, 1, S16_C, V_SOFT)
add_tom(s, 55, 2, 0, HITOM, V_MED, 12)
add_snare(s, 55, 3, S16_B, V_SOFT)
add_ghost(s, 55, 3, S16_D, V_GHOST)

# --- RECAP (bars 56-63): Motif A returns, grand. ---------------------
add_crash(s, 56, 0, 0, V_HARD, CRASH1)
for bar in range(56, 64):
    motif_A(s, bar, lead_in=(bar % 2 == 0))
    if bar % 2 == 1:
        ride_pattern(s, bar, swing=True, bell=False, base=V_MED)
        add_ghost(s, bar, 1, S16_C, V_GHOST)
        add_ghost(s, bar, 3, S16_C, V_GHOST)
    if bar == 60:
        add_crash(s, bar, 2, 0, V_HARD, CRASH2)
    if bar == 63:
        fill_ruff(s, bar, 3, V_MED + 8)

# --- DEVELOPMENT 2 (bars 64-77). -------------------------------------
for bar in range(64, 72):
    motif_B(s, bar)
    if bar % 2 == 1:
        fill_toms(s, bar, 3, up=(bar % 4 == 1))
        add_kick(s, bar, 3, S16_D, V_SOFT)
    else:
        add_kick(s, bar, 1, S16_D, V_MED)
for bar in range(72, 78):
    add_kick(s, bar, 0, 0, V_HARD)
    add_snare(s, bar, 1, 0, V_ACCENT)
    add_kick(s, bar, 2, S16_B, V_HARD)
    add_snare(s, bar, 3, 0, V_LAST)
    if bar % 2 == 0:
        add_hat(s, bar, 0, S16_C, V_SOFT, open_h=True)
    else:
        add_aux(s, bar, 2, S16_C, SPLASH, V_SOFT)
    add_ghost(s, bar, 0, S16_D, V_GHOST)
    if bar == 77:
        fill_ruff(s, bar, 3, V_MED + 12)

# --- QUIET CONTRAST (bars 78-83). ------------------------------------
for bar in range(78, 84):
    add_kick(s, bar, 0, LAY // 2, V_MED)
    add_snare(s, bar, 2, LAY // 2, V_MED)
    for b in range(4):
        for off in (S16_B, S16_D):
            add_ghost(s, bar, b, off + LAY // 2, V_GHOST)
    if bar % 2 == 0:
        add_aux(s, bar, 3, S16_C, SPLASH, V_SOFT)

# --- RISE (bars 84-87). ----------------------------------------------
for i, bar in enumerate(range(84, 88)):
    add_kick(s, bar, 0, PUSH + i, V_HARD)
    add_snare(s, bar, 1, PUSH + i, V_ACCENT)
    add_kick(s, bar, 2, PUSH + i, V_HARD)
    add_snare(s, bar, 3, PUSH + i, V_LAST)
    for b in range(4):
        for off in (0, S16_C, PPQ - SWING):
            add_hat(s, bar, b, off, V_MED)
    if bar % 2 == 1:
        fill_toms(s, bar, 3, up=True)

# --- CLIMAX (bars 88-103). -------------------------------------------
add_crash(s, 88, 0, 0, V_HARD, CRASH1)
add_crash(s, 88, 0, S16_B, V_MED, CRASH2)
for bar in range(88, 104):
    add_kick(s, bar, 0, 0, V_HARD)
    add_kick(s, bar, 2, 0, V_HARD)
    add_kick(s, bar, 1, S16_C, V_MED)
    add_kick(s, bar, 3, S16_D, V_MED)
    add_snare(s, bar, 1, 0, V_ACCENT)
    add_snare(s, bar, 3, 0, V_LAST)
    for b in range(4):
        for off in (0, S16_C, PPQ - SWING):
            add_hat(s, bar, b, off, V_MED if off == 0 else V_GHOST + 6)
    if bar % 4 == 3:
        fill_toms(s, bar, 3, up=(bar % 8 == 3))
    if bar == 95:
        add_crash(s, bar, 2, 0, V_HARD, CRASH2)
        add_aux(s, bar, 3, S16_C, SPLASH, V_MED)

# --- FINAL RECAP & ENDING (bars 104-109). ----------------------------
add_crash(s, 104, 0, 0, V_HARD, CRASH1)
for bar in range(104, 108):
    motif_A(s, bar)
    add_ghost(s, bar, 1, S16_C, V_GHOST + 6)
    add_ghost(s, bar, 3, S16_C, V_GHOST + 6)

add_kick(s, 108, 0, 0, V_HARD)
add_snare(s, 108, 0, 0, V_HARD)
add_crash(s, 108, 0, 0, V_HARD, CRASH1)
add_crash(s, 108, 0, S16_B, V_MED, CRASH2)
add_tom(s, 108, 1, 0, HITOM2, V_MED, 20)
add_tom(s, 108, 2, 0, MTFT, V_MED, 20)
add_tom(s, 108, 3, 0, LOTOM, V_SOFT, PPQ * 2)
add_aux(s, 108, 3, S16_C, SPLASH, V_MED, PPQ * 2)

add_ride(s, 109, 0, 0, V_HARD, bell=True, dur=PPQ * 2)
add_ride(s, 109, 0, S16_B, V_MED, bell=True, dur=PPQ * 2)
add_crash(s, 109, 0, 0, V_HARD, CHINA, PPQ * 3)
add_tom(s, 109, 1, 0, HITOM, V_MED, PPQ)
add_tom(s, 109, 2, 0, MTFT, V_SOFT, PPQ)
add_kick(s, 109, 3, 0, V_HARD)

# ======================================================================
# Normalize, enforce playability, convert to delta-time events.
# ======================================================================
notes = enforce_playable(s.notes)
notes.sort(key=lambda x: (x[0], x[1]))

events = []   # (tick, is_on, note, vel)
for tick, note, vel, dur in notes:
    if vel <= 0:
        continue
    vel = max(1, min(127, int(vel)))
    events.append((tick, True, note, vel))
    events.append((tick + max(1, int(dur)), False, note, 0))

# At same tick, note-offs before note-ons for clean retrigger.
events.sort(key=lambda e: (e[0], e[1], e[2]))

mid = MidiFile(type=1, ticks_per_beat=PPQ)
track = MidiTrack()
mid.tracks.append(track)

track.append(MetaMessage('track_name', name='Drum Solo', time=0))
track.append(MetaMessage('time_signature', numerator=4, denominator=4,
                         clocks_per_click=24, notated_32nd_notes_per_beat=8,
                         time=0))
track.append(MetaMessage('set_tempo', tempo=TEMPO_US, time=0))

CH = 9  # channel 10

last_tick = 0
for tick, is_on, note, vel in events:
    delta = max(0, tick - last_tick)
    last_tick = tick
    if is_on:
        track.append(Message('note_on', channel=CH, note=note,
                             velocity=vel, time=delta))
    else:
        track.append(Message('note_off', channel=CH, note=note,
                             velocity=0, time=delta))

track.append(MetaMessage('end_of_track', time=PPQ * 2))

mid.save('solo.mid')
print("Wrote solo.mid: %d note events, %.1fs at 92 BPM"
      % (len(notes), mid.length))
