#!/usr/bin/env python3
"""
drum_solo.py — generates a two-minute drum solo as a General MIDI file (solo.mid).

Only dependency: mido (plus the standard library).  Fully deterministic — no
random module is used anywhere, all timing is integer tick math, so the file
is byte-identical on every run.

Design
------
* MIDI channel 10 (GM percussion).  Tempo 120 BPM, 4/4 -> 2.0 s/bar, 60 bars
  = exactly 120.0 s.
* Feel: 8th-note swing (58/42, i.e. ±12 ticks of a 480-tick beat) plus a
  per-section placement of "one" (behind / on / ahead) so the solo
  consistently lays back in some passages and pushes in others.
* Motif A (R L R L L . R L, 16ths) is stated early, then varied (doubled,
  ghosted, displaced to the toms, inverted, in 3s) and returned at the end.
* Ghost notes against accents throughout; strong dynamic contrast between
  sections (whisper to shout).
* Playable by one drummer: at most two limbs sound at any instant.  Limbs are
  R (right hand), L (left hand), F (left foot), K (right foot).  Each strike
  is routed to a legal limb for its voice and each limb is in a short
  "refractory" period after a strike.

Uses a broad slice of the GM percussion map (35–81): kit, toms, several
cymbals, and aux voices (cowbell, wood blocks, claves, shaker, triangle,
tambourine, agogo, timbales, congas, bongos, guiro, cuica, whistle...).
"""

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

TPQ = 480                      # ticks per quarter note
BAR = 4 * TPQ                  # 1920 ticks per bar
DIV = TPQ // 4                 # 120 ticks = one 16th (the internal grid)
N_BARS = 60
SWING = 12                     # ±12 ticks -> 58/42 feel
TOTAL = BAR * N_BARS           # 115200 ticks = 120.0 s exactly

# ---------------------------------------------------------------- limbs ----
R = 'R'   # right hand
L = 'L'   # left hand
F = 'F'   # left foot (hi-hat / pedal / light percussion)
K = 'K'   # right foot (bass drum)

LIMB_ORDER = {K: 0, F: 1, L: 2, R: 3}

# ---------------------------------------------------------------- voices ----
# GM percussion keys
KICK    = 36
STICK   = 31   # side stick
SNARE   = 38
RIM     = 37   # hand clap treated as "cross-stick / slap" (we'll use 37 side stick)
# note: 37 = side stick, 31 = sticks, 39 = hand clap

RIDE    = 51
BELL    = 53   # ride bell
CRASH   = 49
CRASH2  = 57   # crash 2
SPLASH  = 55
CHINA   = 52
HAT     = 42   # closed hi-hat
OHAT    = 46   # open hi-hat
PEDAL   = 44   # hi-hat pedal

TOM_L   = 41   # low floor tom
TOM_M   = 43   # high floor tom
TOM_S   = 45   # low tom
TOM_SM  = 47   # low-mid tom
TOM_H   = 48   # hi-mid tom
TOM_HH  = 50   # high tom

COWB    = 56
AGOGO_H = 67
AGOGO_L = 68
CLAVES  = 75
CABASA  = 69
SHAKER  = 82   # shaker
MARACA  = 70
TIMB_H  = 65
TIMB_L  = 64
WOOD    = 76   # hi wood block
WOOD2   = 77   # low wood block
GUIRO_S = 73   # short guiro
GUIRO_L = 74   # long guiro
WHISTLE_H = 71
WHISTLE_L = 72
CUICA_H = 78
CUICA_L = 79
BONGO_H = 60
BONGO_L = 61
CONGA_M = 62   # mute hi conga
CONGA_O = 63   # open hi conga
CONGA_L = 64   # low conga
TRI_OPEN = 80  # open triangle
TRI_MUTE = 81  # mute triangle
TAMB   = 54

TOMS = [TOM_HH, TOM_H, TOM_SM, TOM_S, TOM_M, TOM_L]

# Voices the LEFT hand can play (it's on the snare side).
LEFT_VOICES = {SNARE, RIM, STICK}

# Voices the LEFT FOOT can play (hi-hat pedal / light shaker).
FOOT_VOICES = {HAT, PEDAL, OHAT, SHAKER, MARACA, CABASA, TRI_MUTE, TRI_OPEN}

# Voices the RIGHT FOOT plays (bass drum only).
KICK_VOICES = {KICK}

# Everything else goes on the RIGHT hand (toms, cymbals, aux percussion).
RIGHT_HAND_VOICES = {
    RIDE, BELL, CRASH, CRASH2, SPLASH, CHINA,
    TOM_HH, TOM_H, TOM_SM, TOM_S, TOM_M, TOM_L,
    COWB, AGOGO_H, AGOGO_L, CLAVES, WOOD, WOOD2,
    GUIRO_S, GUIRO_L, WHISTLE_H, WHISTLE_L, CUICA_H, CUICA_L,
    BONGO_H, BONGO_L, CONGA_M, CONGA_O, CONGA_L,
    TIMB_H, TIMB_L, TAMB, TRI_OPEN, TRI_MUTE,
}

ALL_VOICES = (LEFT_VOICES | FOOT_VOICES | KICK_VOICES | RIGHT_HAND_VOICES)


def resolve_limb(key):
    if key in KICK_VOICES:
        return K
    if key in LEFT_VOICES:
        return L
    if key in FOOT_VOICES:
        return F
    return R   # everything else -> right hand


def clamp_tick(t):
    return max(0, min(TOTAL - 1, int(t)))


class Solo:
    """Accumulates strikes and enforces the two-limb constraint."""

    def __init__(self):
        self.ev = []          # (tick, limb_order, velocity, key)
        self.free_at = {}     # limb -> tick when it is free again

    def note(self, limb, key, tick, vel):
        tick = clamp_tick(tick)
        # If the requested limb can't legally play this voice, re-route it.
        legal = (key in KICK_VOICES and limb == K) or \
                (key in LEFT_VOICES and limb == L) or \
                (key in FOOT_VOICES and limb == F) or \
                (key in RIGHT_HAND_VOICES and limb == R)
        if not legal:
            limb = resolve_limb(key)
        leg = self.free_at.get(limb, -10 ** 9)
        if tick < leg:
            return False   # limb is still busy; drop the strike
        self.ev.append((tick, LIMB_ORDER[limb], int(vel), key))
        self.free_at[limb] = tick + DIV // 2   # ~60 ticks of "recovery"
        return True

    def chord(self, strikes, tick, vel):
        """strikes = list of (limb, key).  Each limb is used at most once."""
        ok = False
        for limb, key in strikes:
            ok |= self.note(limb, key, tick, vel)
        return ok


# ------------------------------------------------------------------ feel ----
def swing(n, s=1.0):
    """Swing offset for grid slot n (n even = downbeat of the 8th)."""
    if n % 2 == 0:
        return int(round(SWING * s))
    return -int(round(SWING * s))


# Per-section "placement of one" (ticks) and swing scale.
#   push > 0  -> behind the beat (laying back)
#   push = 0  -> on the beat
#   push < 0  -> ahead of the beat (pushing)
SECTIONS = [
    (0, 4,   "A  motif statement",          4,  1.00),
    (4, 8,   "B  theme (ride + ghosts)",   -2,  1.05),
    (8, 12,  "C  motif doubled",             0,  1.10),
    (12, 16, "D  motif displaced to toms",   2,  0.95),
    (16, 20, "E  half-time, low toms",       6,  0.85),
    (20, 24, "F  sparse, cross-stick",      -3,  1.15),
    (24, 28, "G  build (tom cascade)",       0,  1.05),
    (28, 32, "H  climax (double strokes)",   2,  1.15),
    (32, 36, "I  theme in 3s",               0,  1.00),
    (36, 40, "J  breakdown (hands only)",   -2,  1.00),
    (40, 44, "K  ghost solo (whisper)",      3,  0.95),
    (44, 48, "L  funk, displaced kick",      0,  1.10),
    (48, 52, "M  motif A returns",           4,  1.00),
    (52, 56, "N  theme on ride",            -2,  0.95),
    (56, 60, "O  cadence (build & hit)",     0,  1.05),
]


def feel_for(bar):
    for lo, hi, _name, p, s in SECTIONS:
        if lo <= bar < hi:
            return p, s
    return 0, 1.0


def at(bar, n, extra=0):
    p, s = feel_for(bar)
    return bar * BAR + n * DIV + swing(n, s) + p + int(extra)


# ------------------------------------------------------------ drum voices ---
def _s(sol, bar, n, key, vel, limb=None):
    t = at(bar, n)
    if limb is None:
        limb = resolve_limb(key)
    return sol.note(limb, key, t, vel)


def kick(sol, b, n, v):   return _s(sol, b, n, KICK, v, K)
def sn(sol, b, n, v):     return _s(sol, b, n, SNARE, v, L)
def rim(sol, b, n, v):    return _s(sol, b, n, RIM, v, L)
def stick(sol, b, n, v):  return _s(sol, b, n, STICK, v, L)
def hihat(sol, b, n, v):  return _s(sol, b, n, HAT, v, F)
def ohat(sol, b, n, v):   return _s(sol, b, n, OHAT, v, F)
def pedal(sol, b, n, v):  return _s(sol, b, n, PEDAL, v, F)
def ride(sol, b, n, v):   return _s(sol, b, n, RIDE, v, R)
def bell(sol, b, n, v):   return _s(sol, b, n, BELL, v, R)
def crash(sol, b, n, v, key=CRASH): return _s(sol, b, n, key, v, R)
def tom(sol, b, n, key, v):        return _s(sol, b, n, key, v, R)
def aux(sol, b, n, key, v):        return _s(sol, b, n, key, v, resolve_limb(key))


# --------------------------------------------------------------- patterns --
MOTIF_A = [(0, R), (1, L), (2, R), (3, L), (4, L), (6, R), (7, L)]


def play_motifA(sol, b, key_r=STICK, key_l=SNARE, vel=88,
                ghosts=(4,), accents=(0, 5)):
    for i, (n, limb) in enumerate(MOTIF_A):
        v = vel
        if i in ghosts:
            v = 28
        if i in accents:
            v = min(127, vel + 25)
        key = key_r if limb == R else key_l
        sol.note(limb, key, at(b, n), v)


def groove_bar(sol, b, style, vel=88):
    if style == "ride_rock":
        for n in (0, 2, 4, 6, 8, 10, 12, 14):
            ride(sol, b, n, vel + (10 if n % 8 == 0 else 0))
        sn(sol, b, 4, vel + 18)
        sn(sol, b, 12, vel + 16)
        kick(sol, b, 2, vel + 14)
        kick(sol, b, 10, vel + 12)
    elif style == "ride_swing":
        for n in (0, 2, 4, 6, 8, 10, 12, 14):
            ride(sol, b, n, vel + (12 if n == 0 else 0))
        sn(sol, b, 4, vel + 20)
        sn(sol, b, 12, vel + 16)
        kick(sol, b, 0, vel + 8)
        kick(sol, b, sight := 10, vel + 10)
    elif style == "funk":
        for n in (0, 4, 8, 12):
            hihat(sol, b, n, vel + 4)
        sn(sol, b, 4, vel + 22)
        sn(sol, b, 12, vel + 18)
        kick(sol, b, 0, vel + 12)
        kick(sol, b, 3, vel + 6)
        kick(sol, b, 10, vel + 10)
    elif style == "ghost_funk":
        for n in (0, 2, 4, 6, 8, 10, 12, 14):
            hihat(sol, b, n, vel + (6 if n % 4 == 0 else -4))
        sn(sol, b, 4, vel + 24)
        sn(sol, b, 12, vel + 20)
        for n in (1, 3, 7, 9, 11, 15):
            sn(sol, b, n, 30)
        kick(sol, b, 0, vel + 12)
        kick(sol, b, 6, vel + 8)
        kick(sol, b, 10, vel + 10)
    elif style == "half_time":
        for n in (0, 2, 4, 6, 8, 10, 12, 14):
            hihat(sol, b, n, vel - 6)
        sn(sol, b, 8, vel + 24)
        kick(sol, b, 0, vel + 16)
        kick(sol, b, 6, vel + 10)


def fill_16_bar(sol, b, kind="tomrun", vel=94):
    if kind == "tomrun":
        keys = [TOM_HH, TOM_H, TOM_H, TOM_SM, TOM_SM, TOM_S,
                TOM_S, TOM_M, TOM_M, TOM_L, TOM_L, TOM_L,
                TOM_L, TOM_L, TOM_L, TOM_L]
        for i, n in enumerate(range(16)):
            v = vel + (12 if n == 0 else 0) - (14 if n > 8 else 0)
            tom(sol, b, n, keys[i], v)
    elif kind == "roll":
        for n in range(16):
            v = vel + (18 if n % 4 == 0 else 0) - (18 if n % 2 else 0)
            sn(sol, b, n, max(40, v))


# ------------------------------------------------------------------ build ---
def build():
    sol = Solo()

    # ---- 1 (bars 0–3): A — Motif A stated on stick + snare, minimal kit ----
    for b in (0, 1):
        play_motifA(sol, b, key_r=STICK, key_l=SNARE, vel=88)
        kick(sol, b, 0, 80)

    play_motifA(sol, 2, key_r=STICK, key_l=SNARE, vel=92, ghosts=(2, 4))
    kick(sol, 2, 0, 84)
    ride(sol, 2, 10, 70)
    ride(sol, 2, 14, 62)

    play_motifA(sol, 3, key_r=STICK, key_l=SNARE, vel=86)
    tom(sol, 3, 12, TOM_H, 78)
    tom(sol, 3, 14, TOM_SM, 70)
    crash(sol, 3, 0, 100, SPLASH)

    # ---- 2 (bars 4–7): B — theme on ride + ghost snare ----
    crash(sol, 4, 0, 104, CRASH)
    for b in range(4, 8):
        groove_bar(sol, b, "ride_swing", vel=88)
        for n in (1, 3, 7, 9, 11, 15):
            if (n + b) % 2 == 0:
                sn(sol, b, n, 26 + (n % 3) * 4)
        pedal(sol, b, 4, 55)
        pedal(sol, b, 12, 55)
    tom(sol, 7, 13, TOM_SM, 76)
    tom(sol, 7, 15, TOM_S, 82)

    # ---- 3 (bars 8–11): C — Motif A doubled ----
    crash(sol, 8, 0, 112, CRASH2)
    for b in range(8, 12):
        play_motifA(sol, b, key_r=STICK, key_l=SNARE, vel=100,
                    ghosts=(2, 4), accents=(0, 3, 5))
        kick(sol, b, 0, 92)
        kick(sol, b, 11, 80)
        if b % 2 == 1:
            tom(sol, b, 14, TOM_H, 70)

    # ---- 4 (bars 12–15): D — Motif A displaced to toms ----
    crash(sol, 12, 0, 106, CHINA)
    for b in range(12, 16):
        pat = [(0, TOM_H), (1, TOM_H), (2, TOM_SM), (3, TOM_SM),
               (4, TOM_S), (6, TOM_M), (7, TOM_L), (8, TOM_L)]
        for n, k in pat:
            tom(sol, b, n, k, 88 + (8 if n == 0 else 0))
        kick(sol, b, 0, 86)
        kick(sol, b, 7, 72)
        sn(sol, b, 12, 92)

    # ---- 5 (bars 16–19): E — half-time, low toms ----
    crash(sol, 16, 0, 92, SPLASH)
    for b in range(16, 20):
        groove_bar(sol, b, "half_time", vel=80)
        tom(sol, b, 4, TOM_L, 74)
        tom(sol, b, 14, TOM_M, 66)
        for n in (2, 6, 10):
            sn(sol, b, n, 24)

    # ---- 6 (bars 20–23): F — sparse, cross-stick ----
    for b in range(20, 24):
        for n in (0, 4, 8, 12):
            hihat(sol, b, n, 60 if n % 8 == 0 else 44)
        rim(sol, b, 4, 70)
        rim(sol, b, 12, 66)
        kick(sol, b, 0, 62)
        for n in (2, 6, 10, 14):
            sn(sol, b, n, 22)
        pedal(sol, b, 8, 42)
    stick(sol, 23, 13, 44)
    stick(sol, 23, 15, 56)

    # ---- 7 (bars 24–27): G — build (tom cascade) ----
    crash(sol, 24, 0, 96, CRASH)
    for b in range(24, 28):
        for n in range(16):
            k = TOMS[min(n // 3, 5)]
            tom(sol, b, n, k, 70 + n * 3)
        kick(sol, b, 0, 84)
        kick(sol, b, 8, 76)
        if b == 26:
            for n in (2, 6, 10, 14):
                sn(sol, b, n, 48)

    # ---- 8 (bars 28–31): H — climax, double strokes on snare ----
    crash(sol, 28, 0, 120, CRASH2)
    crash(sol, 30, 8, 110, CHINA)
    for b in range(28, 32):
        for n in range(16):
            v = 112 if n % 4 == 0 else (86 if n % 2 == 0 else 62)
            sn(sol, b, n, v)
        kick(sol, b, 0, 102)
        kick(sol, b, 6, 88)
        kick(sol, b, 10, 92)
        ride(sol, b, 4, 84)
        ride(sol, b, 12, 80)

    # ---- 9 (bars 32–35): I — theme in 3s ----
    crash(sol, 32, 0, 102, CRASH)
    for b in range(32, 36):
        for n in (0, 3, 6, 9, 12, 15):
            sn(sol, b, n, 84 + (16 if n == 0 else 0))
        for n in (2, 5, 8, 11, 14):
            tom(sol, b, n, TOM_SM if n % 2 else TOM_H, 66)
        kick(sol, b, 0, 88)
        kick(sol, b, 9, 80)
        for n in (0, 4, 8, 12):
            ride(sol, b, n, 72)

    # ---- 10 (bars 36–39): J — breakdown (hands only) ----
    stick(sol, 36, 0, 70)
    for b in range(36, 40):
        for n in (0, 2, 4, 6, 8, 10, 12, 14):
            aux(sol, b, n, WOOD if n % 4 == 0 else WOOD2,
                70 if n % 4 == 0 else 52)
        rim(sol, b, 4, 66)
        rim(sol, b, 11, 60)
        rim(sol, b, 15, 54)
    for n, v in ((12, 60), (13, 68), (14, 76), (15, 88)):
        stick(sol, 39, n, v)

    # ---- 11 (bars 40–43): K — ghost solo (whisper) ----
    for b in range(40, 44):
        for n in range(16):
            v = 34 if n % 2 else 24
            if n % 4 == 0:
                v = 52
            sn(sol, b, n, v)
        pedal(sol, b, 4, 30)
        pedal(sol, b, 12, 30)
        if b == 42:
            hihat(sol, b, 0, 36)

    # ---- 12 (bars 44–47): L — funk, displaced kick ----
    crash(sol, 44, 0, 96, CRASH)
    for b in range(44, 48):
        groove_bar(sol, b, "ghost_funk", vel=88)
        kick(sol, b, 14, 72)
        if b == 46:
            tom(sol, b, 13, TOM_S, 70)

    # ---- 13 (bars 48–51): M — Motif A returns over the theme ----
    crash(sol, 48, 0, 110, CRASH2)
    for b in range(48, 52):
        play_motifA(sol, b, key_r=STICK, key_l=SNARE, vel=94, ghosts=(2, 4))
        for n in (0, 4, 8, 12):
            ride(sol, b, n, 78)
        kick(sol, b, 0, 88)
        kick(sol, b, 10, 76)

    # ---- 14 (bars 52–55): N — theme on the ride ----
    for b in range(52, 56):
        groove_bar(sol, b, "ride_rock", vel=82)
        for n in (2, 6, 10, 14):
            sn(sol, b, n, 28)
        kick(sol, b, 3, 72)
    fill_16_bar(sol, 55, "tomrun", vel=94)

    # ---- 15 (bars 56–59): O — cadence ----
    for b in range(56, 59):
        groove_bar(sol, b, "funk", vel=90)
        for n in (0, 8):
            aux(sol, b, n, COWB, 64)
        if b == 57:
            for n in (12, 13, 14, 15):
                sn(sol, b, n, 96 + n)
        if b == 58:
            for n in range(16):
                k = TOMS[min(n // 3, 5)]
                tom(sol, b, n, k, 78 + n * 2)

    # Final hit: crash + kick + snare + china + open hat, all at "one" of bar 59.
    crash(sol, 59, 0, 124, CRASH)
    sol.note(K, KICK,   at(59, 0), 124)
    sol.note(L, SNARE,  at(59, 0), 110)
    sol.note(R, CHINA,  at(59, 0), 108)
    sol.note(F, OHAT,   at(59, 0),  92)

    return sol


# ------------------------------------------------------------------ MIDI ---
def write_midi(sol, path="solo.mid"):
    # Build note-on / note-off stream.
    ons  = [(tick, 1, vel, key) for tick, _o, vel, key in sol.ev]
    offs = [(tick + 60, 0, 0,  key) for tick, _o, vel, key in sol.ev]
    stream = sorted(ons + offs, key=lambda e: (e[0], e[1], e[3]))

    mid = MidiFile(type=1, ticks_per_beat=TPQ)

    meta = MidiTrack()
    meta.append(MetaMessage("track_name", name="Drum Solo", time=0))
    meta.append(MetaMessage("time_signature", numerator=4, denominator=4,
                            clocks_per_click=24,
                            notated_32nd_notes_per_beat=8, time=0))
    meta.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
    meta.append(MetaMessage("end_of_track", time=0))
    mid.tracks.append(meta)

    tr = MidiTrack()
    tr.append(MetaMessage("track_name", name="Drums (ch 10)", time=0))
    tr.append(Message("control_change", channel=9, control=7,
                      value=110, time=0))
    tr.append(Message("control_change", channel=9, control=10,
                      value=64, time=0))
    cur = 0
    for tick, is_on, vel, key in stream:
        delta = max(0, tick - cur)
        if is_on:
            tr.append(Message("note_on", channel=9, note=key,
                              velocity=max(1, min(127, vel)), time=delta))
        else:
            tr.append(Message("note_off", channel=9, note=key,
                              velocity=0, time=delta))
        cur = tick
    tr.append(MetaMessage("end_of_track", time=0))
    mid.tracks.append(tr)

    mid.save(path)


def main():
    sol = build()
    write_midi(sol, "solo.mid")
    print("wrote solo.mid")


if __name__ == "__main__":
    main()
