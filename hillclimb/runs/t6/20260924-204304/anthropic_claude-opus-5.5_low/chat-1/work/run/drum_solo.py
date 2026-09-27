import random, math
import mido

rng = random.Random(20240607)
TPB = 960
BASE_BPM = 112.0
TOTAL_SEC = 120.0

KICK, SNARE, RIM, HHC, HHP, HHO = 36, 38, 37, 42, 44, 46
T1, T2, T3, T4 = 50, 48, 45, 43  # high -> floor
CRASH, RIDE, BELL, CHINA, SPLASH, CRASH2 = 49, 51, 53, 52, 55, 57
COWBELL, CLAVE, TAMB, WOOD_H, WOOD_L = 56, 75, 54, 76, 77
TIMB_H, TIMB_L, AGOGO_H = 65, 66, 67

LIMB = {}
for n in (KICK, 35): LIMB[n] = 'RF'
LIMB[HHP] = 'LF'

events = []  # (beat_position, note, velocity, hand) hand in R/L/F/P

class Phrase:
    pass

def hit(pos, note, vel, limb):
    events.append([pos, note, max(1, min(127, int(vel))), limb])

def sticking_singles(n, start='R'):
    s = []
    c = start
    for _ in range(n):
        s.append(c); c = 'L' if c == 'R' else 'R'
    return s

def sticking_paradiddle(n):
    pat = list("RLRRLRLL")
    return [pat[i % 8] for i in range(n)]

def sticking_doubles(n):
    pat = list("RRLL")
    return [pat[i % 4] for i in range(n)]

# ---------- motif ----------
# motif: 1 bar in 16ths: list of (step, voice, accent)
MOTIF = [(0, 'K', 1), (2, 'S', 0.4), (3, 'S', 1), (6, 'T1', 0.8), (7, 'T2', 0.8),
         (8, 'K', 0.9), (10, 'S', 1), (11, 'T3', 0.6), (13, 'T4', 1), (14, 'K', 0.7)]
VOICE = {'K': KICK, 'S': SNARE, 'T1': T1, 'T2': T2, 'T3': T3, 'T4': T4}

def play_motif(bar, intensity, variant=0):
    b0 = bar * 4
    for step, v, acc in MOTIF:
        note = VOICE[v]
        if variant == 1 and v.startswith('T'):
            note = [T1, T2, T3, T4][(step // 2) % 4]
        if variant == 2 and v == 'S' and acc > 0.9:
            note = RIM if rng.random() < 0.5 else SNARE
        limb = 'RF' if note == KICK else ('R' if step % 2 == 0 else 'L')
        hit(b0 + step / 4, note, 50 + 70 * acc * intensity, limb)
    # ghosts in the gaps
    used = {s for s, _, _ in MOTIF}
    for s in range(16):
        if s not in used and rng.random() < 0.55 * intensity:
            hit(b0 + s / 4, SNARE, rng.randint(18, 34), 'L' if s % 2 else 'R')
    # hat foot on 2 and 4
    hit(b0 + 1, HHP, 55, 'LF'); hit(b0 + 3, HHP, 55, 'LF')

def fill(bar, beats, rate, kit_path, start_vel, end_vel, sticking='single', kick_every=0, land=True):
    b0 = bar * 4 + (4 - beats)
    n = int(beats * rate)
    st = {'single': sticking_singles, 'para': sticking_paradiddle,
          'double': sticking_doubles}[sticking](n)
    for i in range(n):
        frac = i / max(1, n - 1)
        drum = kit_path[min(len(kit_path) - 1, int(frac * len(kit_path)))]
        v = start_vel + (end_vel - start_vel) * frac
        if i % int(rate) == 0: v += 12
        elif st[i] == st[i - 1] if i else False: v -= 10
        hit(b0 + i / rate, drum, v + rng.uniform(-5, 5), st[i])
        if kick_every and i % kick_every == kick_every - 1:
            hit(b0 + i / rate, KICK, v - 10, 'RF')
    if land:
        hit((bar + 1) * 4, CRASH, 118, 'R'); hit((bar + 1) * 4, KICK, 115, 'RF')

def groove_bar(bar, style, intensity):
    b0 = bar * 4
    for s in range(16):
        p = b0 + s / 4
        if style == 'ride':
            if s % 2 == 0:
                hit(p, BELL if s % 8 == 0 else RIDE, 70 + 25 * intensity * (s % 4 == 0), 'R')
            if s in (4, 12): hit(p, SNARE, 100 * intensity + 15, 'L')
            elif rng.random() < 0.3: hit(p, SNARE, rng.randint(15, 32), 'L')
            if s in (0, 7, 10) or (s == 14 and rng.random() < 0.5): hit(p, KICK, 95, 'RF')
            if s in (4, 12): hit(p, HHP, 50, 'LF')
        elif style == 'latin':
            if s in (0, 3, 6, 10, 12): hit(p, COWBELL if s != 12 else CLAVE, 75 + 20 * intensity, 'R')
            elif s % 2 == 0: hit(p, T4 if s == 8 else RIDE, 60, 'R')
            if s in (2, 5, 9, 13, 15): hit(p, [TIMB_H, TIMB_L, RIM][s % 3], 55 + rng.randint(0, 30), 'L')
            if s % 4 == 0: hit(p, KICK, 85, 'RF')
            if s % 4 == 2: hit(p, HHP, 45, 'LF')
        elif style == 'hat':
            hand = 'R' if s % 2 == 0 else 'L'
            if s in (4, 12): hit(p, SNARE, 112, 'L')
            else:
                acc = s % 4 == 0
                hit(p, HHO if s == 14 else HHC, (95 if acc else 55) + rng.randint(-6, 6), hand)
            if s in (0, 6, 8, 11): hit(p, KICK, 100, 'RF')

bar = 0
# 1. statement (bars 0-3)
hit(0, CRASH, 110, 'R')
for i in range(4):
    play_motif(bar, 0.7, 0); bar += 1
fill(bar - 1, 1, 4, [T1, T2, T3, T4], 60, 95, land=False)
# 2. variation (4-9)
for i in range(6):
    play_motif(bar, 0.8 + 0.03 * i, [0, 1, 2][i % 3])
    if i % 2 == 1: fill(bar, 1 + (i // 2) % 2, 6, [SNARE, T1, T2, T3, T4][i % 3:], 55, 100, 'single', land=False)
    bar += 1
fill(bar - 1, 2, 4, [SNARE, T1, T2, T4], 60, 110)
# 3. sparse toms with ghosts, low density (10-15)
for i in range(6):
    b0 = bar * 4
    for s in range(16):
        if rng.random() < 0.35:
            hit(b0 + s / 4, rng.choice([T3, T4, T2]), rng.randint(60, 100), 'R' if s % 2 == 0 else 'L')
        elif rng.random() < 0.3:
            hit(b0 + s / 4, SNARE, rng.randint(14, 28), 'L' if s % 2 else 'R')
    hit(b0, KICK, 90, 'RF'); hit(b0 + 2.5, KICK, 75, 'RF')
    hit(b0 + 1, HHP, 50, 'LF'); hit(b0 + 3, HHP, 50, 'LF')
    if i == 2: hit(b0 + 3.5, SPLASH, 85, 'R')
    bar += 1
# 4. long linear run around kit (16-23)
path_cycle = [SNARE, T1, T2, T3, T4, T3, T2, T1]
for i in range(8):
    b0 = bar * 4
    rate = 6 if i < 4 else 8
    st = sticking_paradiddle(rate * 4) if i % 2 else sticking_singles(rate * 4)
    for k in range(rate * 4):
        drum = path_cycle[(k // (2 if i < 4 else 3) + i) % 8]
        if k % rate == 0: drum = SNARE if i % 2 else drum
        v = 40 + 55 * ((k % (rate * 2)) / (rate * 2)) + (18 if k % rate == 0 else 0)
        if st[k] == 'L' and k % rate: v -= 8
        hit(b0 + k / rate, drum, v, st[k])
        if k % (rate // 2 if i >= 4 else rate) == 0: hit(b0 + k / rate, KICK, 80, 'RF')
    hit(b0 + 1, HHP, 45, 'LF'); hit(b0 + 3, HHP, 45, 'LF')
    bar += 1
hit(bar * 4, CHINA, 120, 'R'); hit(bar * 4, KICK, 120, 'RF')
# 5. swelling roll (24-27)
for i in range(4):
    b0 = bar * 4
    for k in range(32):
        frac = (i * 32 + k) / 128
        hit(b0 + k / 8, SNARE, 25 + 90 * frac ** 1.5 + rng.uniform(-4, 4), 'R' if (k // 2) % 2 == 0 else 'L')
    hit(b0, KICK, 60 + 15 * i, 'RF'); hit(b0 + 2, KICK, 60 + 15 * i, 'RF')
    bar += 1
hit(bar * 4, CRASH, 125, 'R'); hit(bar * 4, CRASH2, 120, 'L'); hit(bar * 4, KICK, 125, 'RF')
# 6. groove/color release (28-39)
for i in range(12):
    groove_bar(bar, 'latin' if i < 6 else 'ride', 0.6 + 0.04 * i)
    if i in (5, 11): fill(bar, 1.5, 4, [T1, T2, T4, T3, T4], 70, 110, 'single', land=(i == 11))
    bar += 1
# 7. motif returns, displaced and orchestrated (40-47)
for i in range(8):
    play_motif(bar, 0.9, [1, 2, 0, 1][i % 4])
    if i % 2 == 1:
        fill(bar, 1, [6, 8][i % 2 == 3], [T1, T2, T3, T4], 70, 115, 'double' if i == 5 else 'single', land=False)
    bar += 1
hit(bar * 4, CRASH, 118, 'R'); hit(bar * 4, KICK, 118, 'RF')
# 8. climax: hat groove with fills, then double-kick blasts (48 - until time)
target_bars = int(TOTAL_SEC / (60 / BASE_BPM) / 4) - 1
climax_start = bar
while bar < target_bars - 1:
    j = bar - climax_start
    if j % 4 < 2:
        groove_bar(bar, 'hat', 1.0)
    else:
        b0 = bar * 4
        st = sticking_singles(24)
        for k in range(24):
            drum = [SNARE, T1, T2, T3, T4, CRASH if k % 6 == 5 else T4][k % 6]
            hit(b0 + k / 6, drum, 70 + 45 * (k % 6 == 0) + k, st[k])
            hit(b0 + k / 6, KICK, 70 + k, 'RF' if k % 2 == 0 else 'LF')
    if j % 4 == 3:
        hit((bar + 1) * 4, CRASH2, 120, 'L')
    bar += 1
# 9. final: rolling crescendo to last hit
b0 = bar * 4
for k in range(24):
    hit(b0 + k / 6, [SNARE, T1, T2, T3, T4][min(4, k // 5)], 60 + 2.5 * k, 'R' if k % 2 == 0 else 'L')
    if k % 3 == 0: hit(b0 + k / 6, KICK, 80 + k, 'RF')
end = (bar + 1) * 4
hit(end, CRASH, 127, 'R'); hit(end, CHINA, 127, 'L'); hit(end, KICK, 127, 'RF')
hit(end + 0.02, 35, 110, 'LF')

# ---------- humanize: tempo curve & microtiming ----------
def bpm_at(beat):
    bars = beat / 4
    return BASE_BPM * (1 + 0.035 * math.sin(bars / 5.0) + 0.02 * math.sin(bars / 1.7)
                       + 0.03 * (bars > climax_start) )

beat_to_sec = {}
def sec_of(beat):
    # numerical integration
    t, b, step = 0.0, 0.0, 0.05
    while b + step <= beat:
        t += step * 60 / bpm_at(b); b += step
    t += (beat - b) * 60 / bpm_at(b)
    return t

cache = {}
events.sort(key=lambda e: e[0])
maxb = events[-1][0]
grid = [0.0]
for i in range(int(maxb / 0.05) + 3):
    grid.append(grid[-1] + 0.05 * 60 / bpm_at(i * 0.05))
def fast_sec(b):
    i = int(b / 0.05); f = b / 0.05 - i
    return grid[i] + f * (grid[i + 1] - grid[i])

phrase_push = {}
out = []
for pos, note, vel, limb in events:
    t = fast_sec(pos)
    bar_i = int(pos // 4)
    if bar_i not in phrase_push: phrase_push[bar_i] = rng.gauss(0, 0.006)
    t += phrase_push[bar_i]
    t += {'R': 0.0, 'L': 0.004, 'RF': -0.002, 'LF': 0.003}.get(limb, 0)
    t += rng.gauss(0, 0.004 if vel > 60 else 0.007)
    if vel < 40: t += 0.003
    vel = max(1, min(127, int(vel + rng.gauss(0, 3))))
    out.append([max(0.0, t), note, vel, limb])
if out:
    scale = TOTAL_SEC / max(e[0] for e in out)
    for e in out: e[0] *= scale

# ---------- playability: one note per limb per instant, limb recovery ----------
out.sort(key=lambda e: (e[0], -e[2]))
last = {}
final = []
MIN_GAP = {'R': 0.045, 'L': 0.045, 'RF': 0.06, 'LF': 0.06}
for t, note, vel, limb in out:
    if limb in ('R', 'L'):
        other = 'L' if limb == 'R' else 'R'
        if t - last.get(limb, -1) < MIN_GAP[limb]:
            if t - last.get(other, -1) >= MIN_GAP[other]:
                limb = other
            else:
                continue
    elif t - last.get(limb, -1) < MIN_GAP[limb]:
        other = 'LF' if limb == 'RF' else 'RF'
        if note in (KICK, 35) and t - last.get(other, -1) >= MIN_GAP[other]:
            limb = other
        else:
            continue
    last[limb] = t
    final.append((t, note, vel))

# ---------- write ----------
mid = mido.MidiFile(ticks_per_beat=TPB)
tr = mido.MidiTrack(); mid.tracks.append(tr)
tempo = mido.bpm2tempo(120)
tr.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
tpsec = TPB * 2
msgs = []
for t, note, vel in final:
    tk = int(round(t * tpsec))
    msgs.append((tk, 1, note, vel))
    msgs.append((tk + int(0.08 * tpsec), 0, note, 0))
msgs.sort(key=lambda m: (m[0], m[1]))
cur = 0
for tk, on, note, vel in msgs:
    tr.append(mido.Message('note_on' if on else 'note_off', channel=9, note=note,
                           velocity=vel, time=tk - cur))
    cur = tk
tr.append(mido.MetaMessage('end_of_track', time=int(tpsec)))
mid.save('solo.mid')
