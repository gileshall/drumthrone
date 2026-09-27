import random, math
import mido

random.seed(20240607)
TPB = 960
BPM_REF = 120.0  # file tempo; we place notes in absolute seconds
events = []  # (time_sec, note, vel, limb)

KICK, SNARE, SIDE, RIM = 36, 38, 37, 40
HH_C, HH_P, HH_O = 42, 44, 46
CRASH, CRASH2, RIDE, BELL, CHINA, SPLASH = 49, 57, 51, 53, 52, 55
T_HI, T_HM, T_LM, T_LO, F_HI, F_LO = 50, 48, 47, 45, 43, 41
COWBELL, TIMB_H, TIMB_L, WB_H, WB_L, TAMB = 56, 65, 66, 76, 77, 54
TOMS = [T_HI, T_HM, T_LM, T_LO, F_HI, F_LO]

# ---- tempo curve: beat -> seconds, with surges ----
def bpm_at(b):
    base = 112 + 10 * (b / 240.0)             # gradual rise
    base += 3 * math.sin(b / 16.0 * math.pi)   # phrase surge
    if 150 <= b < 200: base += 6               # climax push
    if b >= 232: base -= 10 * ((b - 232) / 8)  # broaden at end
    return base

beat_time = [0.0]
for i in range(1, 400 * 12 + 1):
    b = (i - 1) / 12.0
    beat_time.append(beat_time[-1] + (60.0 / bpm_at(b)) / 12.0)

def t_of(beat):
    i = beat * 12
    lo = int(i); fr = i - lo
    return beat_time[lo] + fr * (beat_time[lo + 1] - beat_time[lo])

def hit(beat, note, vel, limb, jitter=0.008):
    t = t_of(beat) + random.gauss(0, jitter)
    if vel > 95: t -= 0.004  # accents slightly ahead
    vel = max(1, min(127, int(vel + random.gauss(0, 4))))
    events.append((max(0, t), note, vel, limb))

def cresc(i, n, a, b):
    return a + (b - a) * (i / max(1, n - 1))

# ---- motif: syncopated figure over one bar (beat offsets, voice, accent)
MOTIF = [(0, 'S', 1), (0.75, 'T1', 0), (1.5, 'S', 1), (2.0, 'T2', 0),
         (2.5, 'F', 1), (3.25, 'S', 0), (3.5, 'F', 1)]

def motif(bar, var=0, level=1.0):
    b0 = bar * 4
    toms = random.sample(TOMS[:4], 2)
    for k, (o, v, acc) in enumerate(MOTIF):
        if var >= 1 and random.random() < 0.25: o += 0.25
        note = {'S': SNARE, 'T1': toms[0], 'T2': toms[1], 'F': F_LO}[v]
        if var >= 2 and v == 'S' and random.random() < 0.4: note = RIM
        vel = (112 if acc else 80) * level
        hit(b0 + o, note, vel, 'R' if k % 2 == 0 else 'L')
        if acc: hit(b0 + o, KICK, 95 * level, 'K')
    for g in [0.25, 1.0, 1.25, 2.75, 3.0]:
        if random.random() < 0.6:
            hit(b0 + g, SNARE, random.randint(22, 38), 'L')

def groove(bar, level=1.0, ride=False):
    b0 = bar * 4
    cym = RIDE if ride else HH_C
    for i in range(8):
        v = 90 if i % 2 == 0 else 60
        n = cym
        if not ride and i == 7 and random.random() < 0.4: n = HH_O
        if ride and i % 2 == 0 and random.random() < 0.2: n = BELL
        hit(b0 + i * 0.5, n, v * level, 'R')
    for b in (1, 3): hit(b0 + b, SNARE, 108 * level, 'L')
    kp = random.choice([[0, 2.5], [0, 1.75, 2.5], [0, 0.75, 2, 2.5], [0, 2, 3.75]])
    for k in kp: hit(b0 + k, KICK, 96 * level, 'K')
    for g in random.sample([0.75, 1.5, 2.25, 3.25, 3.75], 2):
        hit(b0 + g, SNARE, random.randint(20, 35), 'L')
    if ride:
        for b in (1, 3): hit(b0 + b, HH_P, 60, 'H')

STICKINGS = ["RLRL", "RLLR", "RRLL", "RLRR", "LRLL", "RLRLRR", "RLLRLL"]

def run(start, beats, sub, lo, hi, path='down', sticking=None):
    n = int(beats * sub)
    st = sticking or random.choice(STICKINGS)
    for i in range(n):
        hand = st[i % len(st)]
        pos = i / max(1, n - 1)
        if path == 'down':
            idx = min(5, int(pos * 6))
        elif path == 'up':
            idx = 5 - min(5, int(pos * 6))
        else:
            idx = int((math.sin(pos * math.pi * 3) + 1) * 2.99)
        note = TOMS[idx]
        if hand == 'L' and idx < 2 and random.random() < 0.5: note = SNARE
        acc = (i % len(st) == 0)
        v = cresc(i, n, lo, hi) + (18 if acc else -8)
        hit(start + i / sub, note, v, hand, 0.006)
        if sub >= 4 and i % sub == 0 and random.random() < 0.5:
            hit(start + i / sub, KICK, v * 0.8, 'K')

def roll(start, beats, lo, hi, note=SNARE, sub=8):
    n = int(beats * sub)
    for i in range(n):
        hand = 'R' if (i // 2) % 2 == 0 else 'L'
        v = cresc(i, n, lo, hi) * (1 if i % 2 == 0 else 0.85)
        hit(start + i / sub, note, v, hand, 0.004)

def crash(beat, v=118, note=CRASH):
    hit(beat, note, v, 'R'); hit(beat, KICK, v, 'K')

bar = 0
# 1: intro — ride + ghosts, quiet, 4 bars
for i in range(4):
    groove(bar, 0.6 + 0.08 * i, ride=True); bar += 1
roll(bar * 4 - 1, 1, 40, 90)
# 2: motif statement, 8 bars
for i in range(8):
    crash(bar * 4, 110) if i == 0 else None
    if i % 2 == 0: motif(bar, 0, 0.9)
    else: groove(bar, 0.85)
    bar += 1
run(bar * 4 - 2, 2, 4, 60, 110, 'down')
# 3: development with variations, 12 bars
for i in range(12):
    if i % 4 == 0: crash(bar * 4, 115, random.choice([CRASH, CRASH2]))
    if i % 3 == 2:
        run(bar * 4, 4, random.choice([4, 6]), 55, 105, random.choice(['down', 'up', 'wave']))
    elif i % 2 == 0: motif(bar, min(2, i // 3), 1.0)
    else: groove(bar, 0.95)
    bar += 1
# 4: valley — sparse, colored
crash(bar * 4, 100, SPLASH)
for i in range(8):
    b0 = bar * 4
    for j in range(16):
        if random.random() < 0.55:
            hit(b0 + j * 0.25, SNARE, random.randint(15, 40), 'L' if j % 2 else 'R')
    hit(b0, KICK, 70, 'K'); hit(b0 + 2.5, KICK, 60, 'K')
    for b in range(4): hit(b0 + b + 0.5, HH_P, 55, 'H')
    if i % 2 == 1:
        hit(b0 + 3, random.choice([COWBELL, WB_H, WB_L]), 70, 'R')
        hit(b0 + 3.5, random.choice([WB_L, TIMB_H]), 60, 'R')
    if i == 5: motif(bar, 1, 0.55)
    bar += 1
# 5: build — sticking runs rising
for i in range(12):
    lvl = 50 + i * 5
    run(bar * 4, 4, 6 if i % 3 else 4, lvl, lvl + 30,
        ['down', 'wave', 'up'][i % 3])
    if i % 4 == 3: motif(bar, 2, 1.0)
    bar += 1
# 6: climax with double bass
for i in range(10):
    b0 = bar * 4
    crash(b0, 120, [CRASH, CHINA, CRASH2][i % 3])
    for j in range(16):
        hit(b0 + j * 0.25, KICK, 85 + (10 if j % 4 == 0 else 0), 'K' if j % 2 == 0 else 'H')
    if i % 2 == 0:
        motif(bar, 2, 1.1)
    else:
        run(b0 + 0.5, 3.5, 6, 90, 120, random.choice(['down', 'wave']))
    if i == 6:
        for j, n in enumerate([TIMB_H, TIMB_H, TIMB_L, COWBELL]):
            hit(b0 + 3 + j * 0.25, n, 110, 'L')
    bar += 1
# 7: swelling roll
roll(bar * 4, 8, 30, 125); bar += 2
run(bar * 4, 2, 6, 100, 127, 'down', "RLRLRR")
# 8: final hit
fb = bar * 4 + 2
hit(fb, CRASH, 127, 'R'); hit(fb, CRASH2, 127, 'L')
hit(fb, KICK, 127, 'K')

# ---- enforce max two hands, two feet: dedupe per limb ----
events.sort()
last = {}
final = []
for t, n, v, limb in events:
    if limb in last and t - last[limb] < 0.01:
        final[-1 if final and final[-1][3] == limb else 0]  # keep earlier
        continue
    last[limb] = t
    final.append((t, n, v, limb))

mid = mido.MidiFile(ticks_per_beat=TPB)
tr = mido.MidiTrack(); mid.tracks.append(tr)
tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM_REF)))
tr.append(mido.MetaMessage('track_name', name='Drum Solo'))
msgs = []
for t, n, v, _ in final:
    tick = int(round(t * TPB * BPM_REF / 60))
    dur = int(TPB * (2.0 if n in (CRASH, CRASH2, CHINA) else 0.2))
    msgs.append((tick, 1, n, v)); msgs.append((tick + dur, 0, n, 0))
msgs.sort()
cur = 0
for tick, on, n, v in msgs:
    tr.append(mido.Message('note_on' if on else 'note_off', channel=9,
                           note=n, velocity=v if on else 0, time=tick - cur))
    cur = tick
tr.append(mido.MetaMessage('end_of_track', time=TPB))
mid.save('solo.mid')
