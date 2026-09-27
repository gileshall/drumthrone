#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid, a two-minute General MIDI drum solo on channel 10.

Musical plan (about 54 bars; the tempo breathes between roughly 102 and 118 BPM):
  Intro      bars  0-3   Motif A stated with space; answered; varied; first fill
  Groove     bars  4-11  Hi-hat and ride grooves; the kick outlines motif A; fills
  Develop    bars 12-19  Motif A inside 16th ghost-note streams, displaced,
                         compressed to triplets, fragmented; motif B (RLK) and
                         paradiddle-diddles; the fill dies away
  Quiet      bars 20-27  Left-foot woodblock clave, feathered kick, motif A
                         augmented and whispered, 4-over-3, then a long swelling roll
  Build      bars 28-35  Unisons, linear fives, doubles, 32nd bursts, big fills
  Peak       bars 36-43  Double bass, motif A in unison, sextuplets, stop-time
  Recap      bars 44-47  Motif A returns bare and loud, then echoes in a whisper
  Finale     bars 48-53  Grooves, a roll swell over the double bass, tom runs,
                         a broadening unison statement of motif A, and the final hit

The output is deterministic because every random choice uses a fixed seed.
"""
import bisect
import math
import random

import mido

R = random.Random(19650411)

# ---------------------------------------------------------------- GM notes
KICK = 36
STICK, SNARE = 37, 38
HH_C, HH_P, HH_O = 42, 44, 46
T1, T2, T3, T4, F1, F2 = 50, 48, 47, 45, 43, 41      # high -> low
CRASH, CRASH2, CHINA, SPLASH = 49, 57, 52, 55
RIDE, BELL = 51, 53
COWBELL, WOOD_L = 56, 77
TOMS = (T1, T2, T3, T4, F1, F2)

LIMB = {'R': 'RH', 'L': 'LH', 'K': 'RF', 'F': 'LF'}

# Motif A: a 3+3+2+2+2+2+1+1 sixteenth-note cell (position, role, weight)
MOTIF_A = [(0, 'S', 1.0), (3, 'H', 0.86), (6, 'M', 0.9), (8, 'F', 0.97),
           (10, 'F', 0.74), (12, 'S', 1.0), (14, 'K', 0.82), (15, 'K', 0.64)]


def B(bar):
    return bar * 4.0


def cr(v, i, n, p=1.0):
    t = i / float(n - 1) if n > 1 else 1.0
    return v[0] + (v[1] - v[0]) * (t ** p)


def displace(m, d, length=16):
    return sorted(((p + d) % length, r, w) for p, r, w in m)


def augment(m, f=2):
    return [(p * f, r, w) for p, r, w in m]


class Perf:
    def __init__(self):
        self.ev = []
        self.bumps = []

    def hit(self, beat, limb, note, vel, kind='n', dt=0.0):
        self.ev.append((float(beat), float(dt), limb, int(note), float(vel), kind))

    def flam(self, beat, hand, note, vel):
        other = 'LH' if hand == 'RH' else 'RH'
        self.hit(beat, other, note, vel * 0.42, 'grace', dt=-0.030)
        self.hit(beat, hand, note, vel, 'a')

    def drag(self, beat, hand, note, vel):
        other = 'LH' if hand == 'RH' else 'RH'
        self.hit(beat, other, note, vel * 0.34, 'grace', dt=-0.060)
        self.hit(beat, other, note, vel * 0.38, 'grace', dt=-0.031)
        self.hit(beat, hand, note, vel, 'a')

    def push(self, b0, b1, amt, shape='ramp'):
        self.bumps.append((b0, b1, amt, shape))

    def land(self, beat, vel=118, cym=CRASH, hand='RH', kick=True):
        self.hit(beat, hand, cym, vel, 'a')
        if kick:
            self.hit(beat, 'RF', KICK, vel * 0.95, 'a')


P = Perf()

# ---------------------------------------------------------------- building blocks


def motif_sparse(P, start, motif, orch, vbase, flam_pos=(), drag_pos=(),
                 hand_over=None, override=None, kick_unison=False, unit=0.25):
    hand_over = hand_over or {}
    override = override or {}
    for p, role, w in motif:
        t = start + p * unit
        v = vbase * w
        if role == 'K':
            P.hit(t, 'RF', KICK, v * 0.92, 'a' if w > 0.75 else 'n')
            continue
        note = override.get(p, orch[role])
        hand = hand_over.get(p, 'RH' if p % 2 == 0 else 'LH')
        if p in flam_pos:
            P.flam(t, hand, note, v)
        elif p in drag_pos:
            P.drag(t, hand, note, v)
        else:
            P.hit(t, hand, note, v, 'a')
        if kick_unison:
            P.hit(t, 'RF', KICK, v * 0.9, 'a')


def accent_stream(P, start, sub, n, motif, orch, ghost=SNARE, vA=(100, 108),
                  vG=(26, 34), sticking=None, ghost_prob=1.0, kick_under=False,
                  force=None, flams=(), note_over=None, kick_vel=0.9):
    """Continuous strokes: accents on motif positions, ghost notes in between."""
    acc = {p: (r, w) for p, r, w in motif if 0 <= p < n}
    force = force or {}
    note_over = note_over or {}
    for i in range(n):
        t = start + i / float(sub)
        hand = sticking[i % len(sticking)] if sticking else ('R' if i % 2 == 0 else 'L')
        limb = force.get(i, LIMB[hand])
        gv = cr(vG, i, n) * R.uniform(0.86, 1.12)
        if i in acc:
            role, w = acc[i]
            v = cr(vA, i, n) * w
            if role == 'K':
                prevk = (i - 1) in acc and acc[i - 1][0] == 'K'
                P.hit(t, 'LF' if prevk else 'RF', KICK, v * kick_vel, 'a')
                if R.random() < ghost_prob:
                    P.hit(t, LIMB[hand], ghost, gv, 'g')
                continue
            note = note_over.get(i, orch[role])
            if i in flams:
                P.flam(t, limb, note, v)
            else:
                P.hit(t, limb, note, v, 'a')
            if kick_under:
                P.hit(t, 'RF', KICK, v * kick_vel, 'a')
        elif R.random() < ghost_prob:
            P.hit(t, LIMB[hand], ghost, gv, 'g')


def linear(P, start, sub, n, sticking, rv, lv, vAcc=(90, 112), vOth=(55, 72),
           vK=(80, 96), acc_idx=(0,)):
    """Linear sticking patterns such as RLK, RLRLK, RLRRLL, RLRLKF."""
    grp = len(sticking)
    for i in range(n):
        ch = sticking[i % grp]
        g, j = i // grp, i % grp
        t = start + i / float(sub)
        if ch == '-':
            continue
        if ch in 'KF':
            P.hit(t, LIMB[ch], KICK, cr(vK, i, n) * R.uniform(0.94, 1.04), 'n')
            continue
        note = rv(g) if ch == 'R' else lv(g)
        if j in acc_idx:
            P.hit(t, LIMB[ch], note, cr(vAcc, i, n), 'a')
        else:
            P.hit(t, LIMB[ch], note, cr(vOth, i, n) * R.uniform(0.9, 1.08), 'n')


def tom_run(P, start, sub, n, route, sticking='RL', v=(80, 110), group=2,
            acc_every=None, p=1.0):
    """Singles or doubles travelling around the kit along a route."""
    L = len(sticking)
    for i in range(n):
        ch = sticking[i % L]
        t = start + i / float(sub)
        if ch in 'KF':
            P.hit(t, LIMB[ch], KICK, cr(v, i, n, p) * 0.9, 'n')
            continue
        note = route[(i // group) % len(route)]
        vel = cr(v, i, n, p)
        kind = 'n'
        if acc_every:
            if i % acc_every == 0:
                vel *= 1.1
                kind = 'a'
            else:
                vel *= 0.88
        if i > 0 and sticking[(i - 1) % L] == ch:
            vel *= 0.93
        P.hit(t, LIMB[ch], note, vel, kind)


def roll(P, start, beats, v, note=SNARE, sub=8, p=1.4, beat_pulse=6, tail_route=None):
    """Double-stroke roll that swells and can resolve onto the toms."""
    n = int(round(beats * sub))
    tail = len(tail_route) * 2 if tail_route else 0
    for i in range(n):
        ch = 'RRLL'[i % 4]
        t = start + i / float(sub)
        vel = cr(v, i, n, p)
        if i % 4 in (1, 3):
            vel *= 0.92
        if i % sub == 0:
            vel += beat_pulse
        nt = note
        if tail_route and i >= n - tail:
            nt = tail_route[(i - (n - tail)) // 2]
        P.hit(t, LIMB[ch], nt, vel, 'g' if vel < 40 else 'n')


def dbl_bass(P, start, beats, v=(80, 94)):
    n = int(beats * 4)
    for i in range(n):
        vel = cr(v, i, n) * (1.08 if i % 4 == 0 else 0.95)
        P.hit(start + i * 0.25, 'RF' if i % 2 == 0 else 'LF', KICK, vel, 'n')


def groove(P, bar, cym='hh', kicks=(0, 3, 6, 10), snare=(4, 12), ghosts=3,
           open_hat=(), hat16=False, beats=4, crash0=False, vs=1.0, bell=False,
           lf_chick=False):
    s = B(bar)
    n = int(beats * 4)
    for i in range(n):
        t = s + i * 0.25
        if crash0 and i == 0:
            P.hit(t, 'RH', CRASH, 114 * vs, 'a')
            continue
        if cym == 'hh':
            if (i - 1) in open_hat:
                continue
            if i % 2 == 0 or hat16:
                note = HH_O if i in open_hat else HH_C
                v = (90 if i % 4 == 0 else 70 if i % 2 == 0 else 50) * vs
                P.hit(t, 'RH', note, v * R.uniform(0.93, 1.05))
                if i in open_hat:
                    P.hit(t + 0.5, 'LF', HH_P, 64)
        elif cym == 'ride':
            if i % 2 == 0:
                note = BELL if (bell and i % 4 == 0) else RIDE
                v = (92 if i % 4 == 0 else 74) * vs
                P.hit(t, 'RH', note, v * R.uniform(0.93, 1.05))
        elif cym == 'cow':
            if i % 2 == 0:
                if i % 4 == 0:
                    P.hit(t, 'RH', COWBELL, 80 * vs * R.uniform(0.94, 1.04))
                else:
                    P.hit(t, 'RH', RIDE, 72 * vs * R.uniform(0.94, 1.04))
    for i in snare:
        if i < n:
            P.hit(s + i * 0.25, 'LH', SNARE, R.uniform(100, 110) * vs, 'bb')
    cands = [i for i in (1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15) if i < n and i not in snare]
    for i in R.sample(cands, min(ghosts, len(cands))):
        P.hit(s + i * 0.25, 'LH', SNARE, R.uniform(22, 36), 'g')
    for i in kicks:
        if i < n:
            P.hit(s + i * 0.25, 'RF', KICK, (96 if i % 4 == 0 else 84) * vs * R.uniform(0.95, 1.04))
    if lf_chick and cym != 'hh':
        for i in (4, 12):
            if i < n:
                P.hit(s + i * 0.25, 'LF', HH_P, 58)

# ---------------------------------------------------------------- sections


def sec_intro(P):
    for bar in range(4):
        for i in (4, 12):
            P.hit(B(bar) + i * 0.25, 'LF', HH_P, R.uniform(48, 58))
    P.push(0, 4, -0.02, 'bump')
    orch = dict(S=SNARE, H=T1, M=T3, F=F1)
    # bar 0: plain statement with space
    motif_sparse(P, B(0), MOTIF_A, orch, 98, flam_pos=(12,))
    # bar 1: the answer, with ghost notes swelling into the floor tom
    s = B(1)
    accent_stream(P, s, 4, 8, [], {}, vG=(20, 52))
    P.hit(s + 2.0, 'RH', F1, 100, 'a')
    P.hit(s + 2.0, 'RF', KICK, 90, 'a')
    P.hit(s + 2.5, 'LH', T3, 80)
    P.hit(s + 2.75, 'RH', T1, 68)
    P.hit(s + 3.5, 'RF', KICK, 58)
    # bar 2: varied statement (drag, new tom voicing, ghost notes)
    orch2 = dict(S=SNARE, H=T1, M=T2, F=F2)
    motif_sparse(P, B(2), MOTIF_A, orch2, 102, flam_pos=(12,), drag_pos=(0,), override={10: F1})
    for p in (1, 2, 9, 11, 13):
        P.hit(B(2) + p * 0.25, 'RH' if p % 2 == 0 else 'LH', SNARE, R.uniform(24, 34), 'g')
    # bar 3: fragment, then a sextuplet run down the toms
    s = B(3)
    frag = [(0, 'H', 1.0), (3, 'M', 0.9), (6, 'L', 0.95)]
    accent_stream(P, s, 4, 8, frag, dict(H=T1, M=T2, L=T4), vA=(92, 100), vG=(26, 42))
    P.hit(s, 'RF', KICK, 86, 'a')
    P.hit(s + 1.5, 'RF', KICK, 70)
    tom_run(P, s + 2, 6, 12, list(TOMS), v=(72, 112), group=2)
    P.hit(s + 2, 'RF', KICK, 80)
    P.hit(s + 3, 'RF', KICK, 92)
    P.push(s + 1.5, s + 4.5, 0.03, 'ramp')


def sec_groove(P):
    groove(P, 4, kicks=(0, 3, 6, 10), ghosts=2, crash0=True)
    groove(P, 5, kicks=(0, 3, 6, 10, 11), ghosts=3, open_hat=(14,))
    groove(P, 6, kicks=(0, 3, 6, 8, 10, 14), ghosts=4, hat16=True, vs=1.03)
    groove(P, 7, kicks=(0, 3, 6), ghosts=2, beats=2)
    linear(P, B(7) + 2, 4, 8, 'RLK', rv=lambda g: [T1, T3, F1][g % 3], lv=lambda g: SNARE,
           vAcc=(92, 112), vOth=(58, 76), vK=(82, 96))
    P.push(B(7) + 1.5, B(8) + 0.5, 0.025, 'ramp')
    groove(P, 8, cym='ride', kicks=(0, 3, 6, 10), ghosts=3, crash0=True, lf_chick=True)
    groove(P, 9, cym='ride', kicks=(0, 8, 10, 14), snare=(3, 6, 12), ghosts=2, lf_chick=True, bell=True)
    groove(P, 10, cym='ride', kicks=(0, 3, 6, 10, 14, 15), ghosts=4, lf_chick=True, bell=True)
    s = B(11)
    roll(P, s, 1.0, (52, 90), sub=8, p=1.0, beat_pulse=4)
    tom_run(P, s + 1, 6, 6, [T1, T2, T3], v=(88, 100), group=2)
    tom_run(P, s + 2, 6, 12, [T3, T4, F1, F2], v=(96, 120), group=3, acc_every=3)
    P.hit(s + 2, 'RF', KICK, 90, 'a')
    P.hit(s + 3, 'RF', KICK, 96, 'a')
    P.hit(s + 3.5, 'RF', KICK, 100, 'a')
    P.push(s + 1, B(12) + 0.5, 0.03, 'ramp')


def sec_dev(P):
    s = B(12)
    P.land(s, 114)
    accent_stream(P, s, 4, 16, MOTIF_A, dict(S=SNARE, H=T1, M=T3, F=F2),
                  vA=(100, 108), vG=(24, 34), flams=(12,), force={0: 'LH'})
    s = B(13)
    accent_stream(P, s, 4, 16, displace(MOTIF_A, 2), dict(S=T1, H=T2, M=T4, F=F1),
                  vA=(98, 106), vG=(24, 36), ghost_prob=0.8, flams=(14,))
    # motif B: RLK hemiola walking down the toms
    linear(P, B(14), 4, 16, 'RLK', rv=lambda g: TOMS[g % 6], lv=lambda g: SNARE,
           vAcc=(90, 110), vOth=(52, 68), vK=(80, 94))
    s = B(15)
    tom_run(P, s, 4, 8, [SNARE, T1, T2, T3], sticking='RRLL', v=(72, 96), group=2)
    linear(P, s + 2, 6, 12, 'RLK', rv=lambda g: [T3, T4, F1, F2][g % 4],
           lv=lambda g: [T2, T3, T4, F1][g % 4], vAcc=(96, 118), vOth=(70, 90), vK=(86, 100))
    P.push(s + 1, B(16) + 0.5, 0.028, 'ramp')
    # motif A compressed into sixteenth-note triplets, one and a half times
    s = B(16)
    P.land(s, 116)
    dim = MOTIF_A + [(16, 'S', 1.0), (19, 'H', 0.9), (22, 'M', 0.95)]
    accent_stream(P, s, 6, 24, dim, dict(S=SNARE, H=T2, M=T4, F=F1),
                  vA=(98, 110), vG=(26, 38), force={0: 'LH'}, ghost_prob=0.9)
    # fragment: the three-note cell repeated
    s = B(17)
    frag = [(0, 'H', 1.0), (3, 'M', 0.9), (6, 'F', 0.95), (9, 'X', 0.9),
            (12, 'H', 1.0), (14, 'K', 0.8), (15, 'K', 0.7)]
    accent_stream(P, s, 4, 16, frag, dict(H=T1, M=T3, F=F2, X=SPLASH),
                  force={9: 'RH'}, vA=(100, 110), vG=(26, 36))
    for p in (0, 6, 12):
        P.hit(s + p * 0.25, 'RF', KICK, 88, 'a')
    # paradiddle-diddles climbing the kit
    s = B(18)
    route = [F2, F1, T3, T1]
    linear(P, s, 6, 24, 'RLRRLL', rv=lambda g: route[g % 4], lv=lambda g: SNARE,
           vAcc=(92, 114), vOth=(48, 72))
    for b in range(4):
        P.hit(s + b, 'RF', KICK, 82 + 4 * b)
    # flams, a five-stroke roll, then a run that dies away
    s = B(19)
    P.flam(s, 'RH', SNARE, 104)
    P.hit(s, 'RF', KICK, 90, 'a')
    P.flam(s + 0.5, 'RH', T1, 100)
    for k, ch in enumerate('RRLL'):
        P.hit(s + 1 + k * 0.125, LIMB[ch], SNARE, 60 + 6 * k)
    P.hit(s + 1.5, 'RH', T2, 106, 'a')
    P.hit(s + 1.5, 'RF', KICK, 88)
    P.flam(s + 1.75, 'LH', T3, 96)
    tom_run(P, s + 2, 6, 12, list(TOMS), v=(104, 58), group=2, p=0.8)
    P.hit(s + 2, 'RF', KICK, 70)
    P.hit(s + 3, 'RF', KICK, 56)
    P.push(s, B(20) + 0.5, -0.02, 'bump')


def sec_quiet(P):
    s = B(20)
    P.hit(s, 'RH', F2, 72, 'a')
    P.hit(s, 'RF', KICK, 66, 'a')
    # left-foot woodblock son clave and feathered kick
    for bar in range(20, 26):
        pos = (0, 6, 12) if (bar - 20) % 2 == 0 else (4, 8)
        for p in pos:
            P.hit(B(bar) + p * 0.25, 'LF', WOOD_L, R.uniform(56, 64))
        for b in range(4):
            P.hit(B(bar) + b, 'RF', KICK, R.uniform(32, 40), 'g')
    # motif A augmented over two bars, cross-stick and toms
    aug = augment(MOTIF_A, 2)
    motif_sparse(P, s, [m for m in aug if m[1] != 'K'], dict(S=STICK, H=T2, M=T4, F=F2),
                 66, hand_over={0: 'LH'})
    for p in (28, 30):
        P.hit(s + p * 0.25, 'RF', KICK, 58)
    for p in R.sample(list(range(1, 32, 2)), 6):
        P.hit(s + p * 0.25, 'RH' if p % 4 == 1 else 'LH', SNARE, R.uniform(14, 22), 'g')
    # whisper streams carrying the motif
    accent_stream(P, B(22), 4, 16, MOTIF_A, dict(S=SNARE, H=T1, M=T3, F=F1),
                  vA=(56, 64), vG=(14, 22), ghost_prob=0.75)
    accent_stream(P, B(23), 4, 16, displace(MOTIF_A, 3), dict(S=T1, H=T2, M=T4, F=F2),
                  vA=(62, 80), vG=(16, 28), ghost_prob=0.85)
    # four-over-three polyrhythm in eighth-note triplets
    s = B(24)
    tomcycle = [T2, T4, T1, F1, T3, F2]
    n = 24
    for i in range(n):
        t = s + i / 3.0
        hand = 'RH' if i % 2 == 0 else 'LH'
        if i % 4 == 0:
            P.hit(t, hand, tomcycle[(i // 4) % 6], cr((58, 88), i, n), 'a')
        else:
            P.hit(t, hand, SNARE, cr((22, 42), i, n) * R.uniform(0.9, 1.1), 'g')
    # the long roll swell (accelerando comes from the tempo map)
    s = B(26)
    roll(P, s, 8, (24, 116), sub=8, p=1.7, beat_pulse=5, tail_route=[T1, T2, T3, F1])
    for b in range(4):
        P.hit(s + b, 'RF', KICK, cr((44, 66), b, 4))
        P.hit(s + b, 'LF', HH_P, cr((46, 54), b, 4))
    for i in range(8):
        P.hit(s + 4 + i * 0.5, 'RF', KICK, cr((70, 100), i, 8))
    for b in range(4):
        P.hit(s + 4 + b, 'LF', HH_P, cr((54, 62), b, 4))


def sec_build(P):
    s = B(28)
    P.land(s, 120)
    accent_stream(P, s, 4, 16, MOTIF_A, dict(S=SNARE, H=T1, M=T3, F=F1),
                  vA=(104, 112), vG=(28, 38), kick_under=True, force={0: 'LH'}, flams=(12,))
    for bar in range(28, 32):
        for b in range(4):
            P.hit(B(bar) + b, 'LF', HH_P, R.uniform(48, 58))
    # linear fives across the barline pulse
    r5 = [T1, T3, F1, F2]
    linear(P, B(29), 4, 16, 'RLRLK', rv=lambda g: r5[g % 4], lv=lambda g: SNARE,
           vAcc=(96, 110), vOth=(44, 60), vK=(80, 92))
    # motif A with double strokes filling the gaps
    s = B(30)
    P.land(s, 116)
    accent_stream(P, s, 4, 16, MOTIF_A, dict(S=SNARE, H=T2, M=T4, F=F2), sticking='RRLL',
                  vA=(100, 110), vG=(34, 46), force={0: 'LH'})
    P.hit(s + 2, 'RF', KICK, 84)
    s = B(31)
    route = [F2, F1, T4, T3, T2, T1, T1, T2, T3, T4, F1, F2]
    tom_run(P, s, 6, 24, route, v=(78, 120), group=2, acc_every=3)
    for b in (0, 1, 2, 3, 3.5):
        P.hit(s + b, 'RF', KICK, 80 + 8 * b)
    P.push(s + 1, B(32) + 0.5, 0.03, 'ramp')
    # motif B in sextuplets
    s = B(32)
    P.land(s, 120, hand='LH')
    rt = [T1, T2, T3, T4, F1, F2, F1, T4]
    linear(P, s, 6, 24, 'RLK', rv=lambda g: rt[g % 8], lv=lambda g: SNARE,
           vAcc=(96, 116), vOth=(56, 72), vK=(84, 100))
    # displaced motif with china and crash colors
    s = B(33)
    accent_stream(P, s, 4, 16, displace(MOTIF_A, 1), dict(S=SNARE, H=T1, M=T3, F=F1),
                  vA=(104, 114), vG=(30, 40), note_over={1: CHINA, 13: CRASH},
                  force={1: 'RH', 13: 'RH'}, kick_under=True)
    # 32nd bursts and punches
    s = B(34)
    tom_run(P, s, 8, 8, [SNARE], v=(50, 100), group=1)
    P.flam(s + 1, 'LH', T1, 110)
    P.hit(s + 1, 'RF', KICK, 96, 'a')
    P.hit(s + 1.5, 'LH', T3, 100, 'a')
    P.hit(s + 1.75, 'RF', KICK, 84)
    tom_run(P, s + 2, 8, 8, [T2, T3], v=(60, 105), group=4)
    P.hit(s + 3, 'RH', F1, 112, 'a')
    P.hit(s + 3, 'RF', KICK, 100, 'a')
    P.hit(s + 3.25, 'LH', F2, 96, 'a')
    P.hit(s + 3.5, 'RH', CRASH, 116, 'a')
    P.hit(s + 3.5, 'RF', KICK, 104, 'a')
    P.flam(s + 3.75, 'LH', SNARE, 108)
    # big descending fill
    s = B(35)
    tom_run(P, s, 6, 24, list(TOMS), v=(90, 124), group=2, acc_every=6)
    for b in range(4):
        P.hit(s + b, 'RF', KICK, 90 + 6 * b, 'a')
    P.hit(s + 3.5, 'LF', KICK, 100)
    P.push(s + 1, B(36) + 0.5, 0.035, 'ramp')


def sec_peak(P):
    s = B(36)
    dbl_bass(P, s, 8, (82, 96))
    pairs = dict(S=(CRASH, SNARE), H=(T1, T2), M=(T3, T4), F=(F1, F2))
    for p, role, w in MOTIF_A:
        t = s + p * 0.25
        if role == 'K':
            P.hit(t, 'RH' if p % 2 == 0 else 'LH', SNARE, 100 * w, 'a')
            continue
        a, b = pairs[role]
        if p == 12:
            a = CRASH2
        P.hit(t, 'RH', a, 116 * w, 'a')
        P.hit(t, 'LH', b, 112 * w, 'a')
    s = B(37)
    accent_stream(P, s, 4, 16, displace(MOTIF_A, 2), dict(S=CRASH, H=T1, M=T3, F=F1),
                  vA=(108, 116), vG=(44, 58), force={2: 'RH', 14: 'RH'})
    s = B(38)
    tom_run(P, s, 6, 24, [SNARE, T1, T2, T3, T4, F1, F2, F1], v=(94, 114), group=3, acc_every=3)
    for b in range(4):
        P.hit(s + b, 'RF', KICK, 96, 'a')
        P.hit(s + b + 0.5, 'LF', HH_P, 60)
    s = B(39)
    rh = [T1, T2, T3, F1]
    lh = [SNARE, T1, T2, T4]
    linear(P, s, 6, 24, 'RLRLKF', rv=lambda g: rh[g % 4], lv=lambda g: lh[g % 4],
           vAcc=(98, 120), vOth=(70, 90), vK=(88, 104))
    P.push(s + 2, B(40) + 0.2, 0.02, 'ramp')
    # stop-time: motif A in unison with space between the hits
    s = B(40)

    def uni(p, rh=None, lh=None, v=120, kick=True, lf=False):
        t = s + p * 0.25
        if rh:
            P.hit(t, 'RH', rh, v, 'a')
        if lh:
            P.hit(t, 'LH', lh, v * 0.96, 'a')
        if kick:
            P.hit(t, 'LF' if lf else 'RF', KICK, v * 0.95, 'a')
    uni(0, CRASH, SNARE, 124)
    uni(3, T1, None, 112)
    uni(6, None, T3, 114)
    uni(8, F1, F2, 118)
    uni(10, F1, F2, 100)
    uni(12, CRASH2, SNARE, 122)
    uni(14, None, None, 100)
    uni(15, None, None, 96, lf=True)
    P.push(s, s + 4, -0.015, 'bump')
    # held breath, then a 32nd-note burst
    s = B(41)
    for b in range(4):
        P.hit(s + b, 'LF', HH_P, R.uniform(56, 64))
    tom_run(P, s + 1, 6, 6, [SNARE], v=(18, 40), group=1)
    tom_run(P, s + 2, 8, 16, [SNARE, T1, T2, T3], v=(40, 118), group=4, p=1.3)
    P.hit(s + 3, 'RF', KICK, 96)
    P.push(s + 2, B(42) + 0.5, 0.03, 'ramp')
    s = B(42)
    P.land(s, 122)
    dbl_bass(P, s, 4, (86, 100))
    frag = [(0, 'C', 1.0), (3, 'H', 0.9), (6, 'M', 0.92), (9, 'F', 0.95),
            (12, 'D', 1.0), (14, 'S', 0.9), (15, 'S', 0.85)]
    accent_stream(P, s, 4, 16, frag, dict(C=CRASH, H=T1, M=T3, F=F1, D=CRASH2, S=SNARE),
                  vA=(108, 116), vG=(46, 56), force={0: 'RH', 12: 'RH'})
    s = B(43)
    route = [SNARE, T1, T2, T3, T4, F1, F2, F1, T4, T3, T2, T1]
    tom_run(P, s, 6, 24, route, sticking='RRLL', v=(86, 124), group=2)
    for b in range(4):
        P.hit(s + b, 'RF', KICK, 92 + 6 * b, 'a')
    P.push(s + 1, B(44) + 0.5, 0.03, 'ramp')


def sec_recap(P):
    s = B(44)
    P.land(s, 124)
    for i in (4, 12):
        P.hit(s + i * 0.25, 'LF', HH_P, 56)
    motif_sparse(P, s, MOTIF_A, dict(S=SNARE, H=T1, M=T3, F=F1), 112, flam_pos=(12,),
                 hand_over={0: 'LH'}, override={8: F2})
    P.push(s, s + 4, -0.025, 'bump')
    # echo in a whisper, then swell
    s = B(45)
    accent_stream(P, s, 4, 12, MOTIF_A, dict(S=SNARE, H=T1, M=T3, F=F1), vA=(42, 50), vG=(14, 20))
    tom_run(P, s + 3, 4, 4, [T1, T2, T3, F1], v=(62, 100), group=1)
    P.hit(s + 3.5, 'RF', KICK, 70)
    groove(P, 46, kicks=(0, 3, 6, 10, 14), ghosts=4, hat16=True, open_hat=(6,), crash0=True, vs=1.06)
    groove(P, 47, kicks=(0, 3, 6), ghosts=2, beats=2, hat16=True, vs=1.06)
    linear(P, B(47) + 2, 6, 12, 'RLK', rv=lambda g: [T1, T2, T3, T4][g % 4], lv=lambda g: SNARE,
           vAcc=(96, 118), vOth=(60, 78), vK=(88, 100))
    P.push(B(47) + 1, B(48) + 0.5, 0.025, 'ramp')


def sec_finale(P):
    groove(P, 48, cym='ride', bell=True, kicks=(0, 3, 6, 10, 11, 14), ghosts=4,
           crash0=True, lf_chick=True, vs=1.08)
    groove(P, 49, cym='cow', kicks=(0, 3, 6, 8, 10), ghosts=3, beats=3, lf_chick=True, vs=1.08)
    tom_run(P, B(49) + 3, 8, 8, [SNARE, T1, T2, T3], v=(74, 112), group=2)
    P.hit(B(49) + 3, 'RF', KICK, 92, 'a')
    P.push(B(49) + 2.5, B(50) + 0.5, 0.02, 'ramp')
    # roll swell over accelerating feet
    s = B(50)
    P.land(s, 118, cym=CRASH2, hand='LH')
    roll(P, s, 8, (40, 122), p=1.5, beat_pulse=8, tail_route=[T1, T2, T3, F1])
    for i in range(8):
        P.hit(s + i * 0.5, 'RF', KICK, cr((70, 94), i, 8))
    dbl_bass(P, s + 4, 4, (96, 116))
    # tom runs down and back up
    s = B(52)
    P.land(s, 124, hand='LH')
    route = [T1, T2, T3, T4, F1, F2, F2, F1, T4, T3, T2, T1]
    tom_run(P, s, 6, 24, route, v=(100, 124), group=2, acc_every=3)
    for b in range(4):
        P.hit(s + b, 'RF', KICK, 96 + 5 * b, 'a')
        P.hit(s + b + 0.5, 'LF', KICK, 88 + 5 * b)
    P.push(s + 1, s + 4.2, 0.02, 'ramp')
    # final broadening statement of motif A
    s = B(53)

    def uni(p, rh=None, lh=None, v=122, foot='RF'):
        t = s + p * 0.25
        if rh:
            P.hit(t, 'RH', rh, v, 'a')
        if lh:
            P.hit(t, 'LH', lh, v * 0.96, 'a')
        P.hit(t, foot, KICK, v * 0.95, 'a')
    uni(0, CRASH, SNARE, 124)
    uni(3, T1, None, 114)
    uni(6, None, T3, 116)
    uni(8, F1, F2, 120)
    uni(10, F1, F2, 108)
    uni(12, CRASH2, SNARE, 124)
    pick = [SNARE, SNARE, T1, T2, F1, F2]
    for k, ch in enumerate('RLRLRL'):
        P.hit(s + 3.25 + k * 0.125, LIMB[ch], pick[k], cr((92, 122), k, 6), 'a')
    P.hit(s + 3.5, 'RF', KICK, 100)
    P.hit(s + 3.75, 'LF', KICK, 110)
    # the last hit, placed a hair late for weight
    P.hit(B(54), 'RH', CRASH, 127, 'final', dt=0.03)
    P.hit(B(54), 'LH', CRASH2, 127, 'final', dt=0.03)
    P.hit(B(54), 'RF', KICK, 127, 'final', dt=0.03)


def compose(P):
    sec_intro(P)
    sec_groove(P)
    sec_dev(P)
    sec_quiet(P)
    sec_build(P)
    sec_peak(P)
    sec_recap(P)
    sec_finale(P)

# ---------------------------------------------------------------- tempo


ANCHORS = [(0, 102), (2, 104), (3, 106), (4, 108), (11, 110), (12, 111), (19, 110),
           (20, 103), (25, 102), (26, 104), (28, 111), (31, 112), (35, 115), (36, 116),
           (43.8, 117), (44.3, 108), (45, 108), (46, 111), (48, 114), (50, 115),
           (52, 118), (53, 117), (53.5, 108), (54, 94), (70, 94)]


def base_bpm(bar):
    if bar <= ANCHORS[0][0]:
        return float(ANCHORS[0][1])
    for (b0, v0), (b1, v1) in zip(ANCHORS, ANCHORS[1:]):
        if b0 <= bar <= b1:
            t = (bar - b0) / float(b1 - b0)
            s = (1 - math.cos(math.pi * t)) / 2
            return v0 + (v1 - v0) * s
    return float(ANCHORS[-1][1])


def tempo_at(beat):
    bpm = base_bpm(beat / 4.0)
    m = 1.0 + 0.006 * math.sin(2 * math.pi * beat / 14.0 + 0.6) \
        + 0.003 * math.sin(2 * math.pi * beat / 5.0 + 1.9)
    for b0, b1, amt, shape in P.bumps:
        if b0 <= beat < b1:
            t = (beat - b0) / (b1 - b0)
            if shape == 'ramp':
                s = (t / 0.8) ** 1.5 if t < 0.8 else (1.0 - t) / 0.2
            else:
                s = math.sin(math.pi * t)
            m += amt * s
    return bpm * m

# ---------------------------------------------------------------- performance


def perform(beat_to_sec):
    H = random.Random(4242)
    drift = {'RH': 0.0, 'LH': 0.0, 'RF': 0.0, 'LF': 0.0}
    out = []
    for beat, dt, limb, note, vel, kind in sorted(P.ev, key=lambda e: (e[0], e[1], e[2], e[3])):
        drift[limb] = 0.8 * drift[limb] + H.gauss(0, 0.0024)
        sd = {'g': 0.0055, 'grace': 0.0025, 'a': 0.0035, 'bb': 0.004}.get(kind, 0.0045)
        off = H.gauss(0, sd) + drift[limb]
        if kind == 'g':
            off += 0.004          # ghosts sit a touch behind
        elif kind == 'bb':
            off += 0.009          # laid-back backbeat
        elif kind == 'a':
            off -= 0.002          # accents lean forward
        if limb == 'RF':
            off -= 0.002
        t = beat_to_sec(beat) + dt + off
        v = vel + H.gauss(0, 2.0 if kind in ('g', 'grace') else 3.0)
        if limb == 'LH' and kind not in ('a', 'bb', 'final'):
            v *= 0.96
        if kind == 'final':
            v = 127
        v = int(round(max(1, min(127, v))))
        out.append((t, limb, note, v, kind))
    return out


def enforce(notes):
    """One stroke per limb at a time, with a physically possible gap."""
    by = {}
    for n in sorted(notes):
        by.setdefault(n[1], []).append(n)
    mg = {'RH': 0.045, 'LH': 0.045, 'RF': 0.07, 'LF': 0.075}
    kept = []
    for limb in ('RH', 'LH', 'RF', 'LF'):
        cur = []
        for n in by.get(limb, []):
            if cur:
                p = cur[-1]
                gap = n[0] - p[0]
                lim = 0.018 if ('grace' in (n[4], p[4])) else mg[limb]
                if gap < lim:
                    if n[3] > p[3]:
                        cur[-1] = n
                    continue
            cur.append(n)
        kept += cur
    return sorted(kept)


def dur_sec(note, kind):
    if kind == 'final':
        return 3.4
    if note in (CRASH, CRASH2, CHINA, SPLASH):
        return 2.5
    if note in (RIDE, BELL):
        return 1.2
    if note == HH_O:
        return 0.45
    if note in TOMS:
        return 0.6
    if note in (COWBELL, WOOD_L):
        return 0.3
    return 0.2


def main():
    compose(P)
    LEAD = 1.0
    END_BEAT = 216.0
    TARGET = 116.8
    NSEG = int((LEAD + END_BEAT + 12) * 2)
    tempos = [tempo_at((j + 0.5) / 2.0 - LEAD) for j in range(NSEG)]
    raw = sum(30.0 / tempos[j] for j in range(int((LEAD + END_BEAT) * 2)))
    k = raw / TARGET
    us = [int(round(60e6 / (bpm * k))) for bpm in tempos]
    cum = [0.0]
    for u in us:
        cum.append(cum[-1] + 0.5 * u / 1e6)

    def beat_to_sec(b):
        x = (b + LEAD) * 2.0
        j = max(0, min(NSEG - 1, int(math.floor(x))))
        return cum[j] + (x - j) * 0.5 * us[j] / 1e6

    def sec_to_tick(s):
        if s <= 0:
            return 0.0
        j = bisect.bisect_right(cum, s) - 1
        j = max(0, min(NSEG - 1, j))
        return j * 480 + (s - cum[j]) / (us[j] / 1e6) * 960.0

    notes = enforce(perform(beat_to_sec))

    items = []
    for t, limb, note, v, kind in notes:
        on = int(round(sec_to_tick(t)))
        off = int(round(sec_to_tick(t + dur_sec(note, kind))))
        items.append((on, note, v, max(off, on + 1)))
    items.sort()

    by_note = {}
    for it in items:
        by_note.setdefault(it[1], []).append(it)

    events = []
    for note in sorted(by_note):
        cleaned = []
        for it in by_note[note]:
            if cleaned and it[0] <= cleaned[-1][0]:
                if it[2] > cleaned[-1][2]:
                    cleaned[-1] = it
                continue
            cleaned.append(it)
        for idx, (on, nt, v, off) in enumerate(cleaned):
            if idx + 1 < len(cleaned):
                off = min(off, cleaned[idx + 1][0] - 1)
            off = max(off, on + 1)
            events.append((on, 2, nt, mido.Message('note_on', channel=9, note=nt, velocity=v)))
            events.append((off, 1, nt, mido.Message('note_off', channel=9, note=nt, velocity=0)))

    for j, u in enumerate(us):
        if j == 0 or u != us[j - 1]:
            events.append((j * 480, 0, 0, mido.MetaMessage('set_tempo', tempo=u)))

    events.sort(key=lambda e: (e[0], e[1], e[2]))

    mid = mido.MidiFile(type=1, ticks_per_beat=960)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.Message('program_change', channel=9, program=0, time=0))
    tr.append(mido.Message('control_change', channel=9, control=7, value=118, time=0))
    tr.append(mido.Message('control_change', channel=9, control=10, value=64, time=0))
    tr.append(mido.Message('control_change', channel=9, control=91, value=40, time=0))
    last = 0
    for tick, _, _, msg in events:
        tr.append(msg.copy(time=tick - last))
        last = tick
    tr.append(mido.MetaMessage('end_of_track', time=240))
    mid.save('solo.mid')


if __name__ == '__main__':
    main()
