import math
import random
import mido

R = random.Random(20240611)
TPB = 480
ev = []            # [beat, note, vel, limb, push]
fill_beats = set()

MOTIF = [0, 3, 6, 10, 12]
TOMS = [50, 48, 47, 45, 43, 41]
CRASHES = [49, 57]
_crash_i = [0]


def hit(t, n, v, limb, push=0.0):
    ev.append([t, n, v, limb, push])


def crash():
    _crash_i[0] += 1
    return CRASHES[_crash_i[0] % 2]


def is_beat(x):
    return abs(x - round(x)) < 1e-6


# ---------------------------------------------------------------- fills
def fill(t0, beats, style, v0=60, v1=110, rot=0):
    for b in range(int(t0), int(math.ceil(t0 + beats - 1e-6))):
        fill_beats.add(b)
    sub, stick = {
        'toms16': (0.25, 'RL'),
        'sext': (1 / 6, 'RL'),
        'rlk': (1 / 6, 'RLK'),
        'roll': (0.125, 'RRLL'),
        'para': (0.25, 'RLRRLRLL'),
        'five': (1 / 6, 'RLRLK'),
    }[style]
    n = int(round(beats / sub))
    up = R.random() < 0.3
    start = R.randint(0, 1)
    for i in range(n):
        t = t0 + i * sub
        p = i / max(1, n - 1)
        h = stick[(i + rot) % len(stick)]
        v = v0 + (v1 - v0) * p
        push = -0.012 * p
        pos = min(5, start + int(p * (6 - start) - 1e-9))
        if up:
            pos = 5 - pos
        if h == 'K':
            hit(t, 36, v * 0.85 + 12, 'RF', push)
            continue
        if style == 'toms16':
            acc = (i % 4 == 0)
            note = 38 if (acc and pos < 2) else TOMS[pos]
            vv = v + (14 if acc else -10)
        elif style == 'sext':
            acc = (i % 3 == 0)
            note = TOMS[pos] if h == 'R' else TOMS[max(0, pos - 1)]
            vv = v + (14 if acc else -8)
        elif style == 'rlk':
            note = TOMS[pos] if h == 'R' else 38
            vv = v + (10 if h == 'R' else -12)
        elif style == 'five':
            note = TOMS[pos] if h == 'R' else 38
            vv = v + (12 if i % 5 == 0 else -6)
        elif style == 'para':
            acc = (i % 4 == 0)
            note = TOMS[(i // 4 + rot + start) % 6] if acc else 38
            vv = v + 12 if acc else v * 0.55
        else:  # roll
            if p < 0.8:
                note = 38
            else:
                note = TOMS[min(5, 2 + int((p - 0.8) * 20))]
            second = (i % 2 == 1)
            vv = v * (0.88 if second else 1.0)
        hit(t, note, vv, h, push)
        if style in ('toms16', 'sext', 'para') and is_beat(i * sub):
            hit(t, 36, 70 + 30 * p, 'RF', push)
        if style in ('roll', 'para') and is_beat(i * sub):
            hit(t, 44, 50, 'LF', push)


# ---------------------------------------------------------------- bars
def groove(bar, rot=0, ride=False, ghost=0.4, kick=(0, 7, 8, 10), land=False,
           fill_at=16, dyn=1.0, mv='snare'):
    acc = set((a + rot) % 16 for a in MOTIF)
    for s in range(fill_at):
        t = bar * 4 + s / 4
        # right hand
        if s == 0 and land:
            hit(t, crash(), 108 * dyn, 'R')
        elif s % 2 == 0:
            if ride:
                hit(t, 53 if (s == 0 and bar % 2) else 51,
                    (82 if s % 4 == 0 else 62) * dyn, 'R')
            elif s == 14 and R.random() < 0.5:
                hit(t, 46, 78 * dyn, 'R')
            else:
                hit(t, 42, (80 if s % 4 == 0 else 56) * dyn, 'R')
        # left hand
        if mv == 'snare':
            if s in acc:
                hit(t, 38, (100 + R.randint(0, 12)) * dyn, 'L', -0.004)
            elif R.random() < ghost:
                hit(t, 38, R.randint(18, 34) * dyn, 'L')
        else:
            if s in (4, 12):
                hit(t, 38, 108 * dyn, 'L')
            elif R.random() < ghost:
                hit(t, 38, R.randint(18, 34) * dyn, 'L')
        # feet
        if mv == 'kick':
            if s in acc or s == 0:
                hit(t, 36, (105 if s in acc else 90) * dyn, 'RF')
        elif s in kick:
            hit(t, 36, (100 if s % 4 == 0 else 82) * dyn, 'RF')
        if (ride or mv == 'kick') and s % 8 == 4:
            hit(t, 44, 58 * dyn, 'LF')


def tommotif(bar, rot=0, land=False, fill_at=16):
    acc = sorted((a + rot) % 16 for a in MOTIF)
    for s in range(fill_at):
        t = bar * 4 + s / 4
        h = 'R' if s % 2 == 0 else 'L'
        if s == 0 and land:
            hit(t, crash(), 110, 'R')
            hit(t, 36, 105, 'RF')
            continue
        if s in acc:
            k = acc.index(s)
            hit(t, TOMS[(k + rot) % 6], 100 + R.randint(0, 14), h, -0.004)
            if R.random() < 0.5:
                hit(t, 36, 95, 'RF')
        else:
            hit(t, 38, R.randint(22, 42), h)
        if s % 8 == 0 and not (s == 0 and land):
            hit(t, 36, 80, 'RF')
        if s % 8 == 4:
            hit(t, 44, 55, 'LF')


def sparse(bar, color, rot=0, land=False):
    acc = set((a + rot) % 16 for a in MOTIF)
    for s in range(16):
        t = bar * 4 + s / 4
        if s == 0 and land:
            hit(t, crash(), 90, 'R')
        elif s % 4 == 0 or s == 14:
            hit(t, 53 if (s == 0 and bar % 2) else 51, 58 if s % 4 == 0 else 46, 'R')
        if s in acc:
            if color == 'side':
                hit(t, 37, 58 + R.randint(-5, 8), 'L')
            elif color == 'block':
                hit(t, 76 if s % 2 == 0 else 77, 62, 'L')
            else:
                hit(t, 63 if s < 8 else 64, 66, 'L')
        if s % 4 == 0:
            hit(t, 44, 45, 'LF')
        if s == 0:
            hit(t, 36, 64, 'RF')
        elif s == 10:
            hit(t, 36, 46, 'RF')


def climax(bar, rot=0, land=False):
    acc = set(2 * ((a + rot) % 16) for a in MOTIF)
    if land:
        acc.add(0)
    accl = sorted(acc)
    cyms = [49, 57, 52, 55]
    for s in range(32):
        t = bar * 4 + s / 8
        if s in acc:
            hit(t, cyms[accl.index(s) % 4] if s else crash(), 112, 'R', -0.003)
            hit(t, 43 if s % 4 else 41, 106, 'L', -0.003)
            hit(t, 36, 112, 'RF')
        else:
            nxt = min([a for a in accl if a > s] + [32])
            prv = max([a for a in accl if a < s] + [0])
            d = nxt - s
            span = max(1, nxt - prv)
            v = 34 + 55 * (1 - d / span)
            h = 'RRLL'[s % 4]
            note = 38 if (h == 'L' or (s // 4) % 2 == 0) else TOMS[(s // 4 + rot) % 4]
            hit(t, note, v, h)
            if s % 8 == 4:
                hit(t, 36, 72, 'RF')
            if s % 8 == 0:
                hit(t, 44, 55, 'LF')


# ---------------------------------------------------------------- the solo
# 1. statement
groove(0, land=True, ghost=0.25, dyn=0.9)
groove(1, ghost=0.3)
groove(2, ghost=0.35, kick=(0, 7, 8, 11))
groove(3, ghost=0.35, fill_at=12); fill(15, 1, 'toms16', 70, 105)
groove(4, land=True, rot=2, ghost=0.4)
groove(5, rot=2, ride=True, ghost=0.45)
groove(6, ride=True, ghost=0.45, kick=(0, 3, 8, 11))
groove(7, fill_at=8, ride=True); fill(30, 2, 'sext', 55, 112)
# 2. development
tommotif(8, land=True, rot=0)
groove(9, rot=0, ghost=0.5)
tommotif(10, rot=1)
groove(11, fill_at=8, ghost=0.5); fill(46, 2, 'para', 50, 100)
tommotif(12, land=True, rot=3)
tommotif(13, rot=5, fill_at=8); fill(54, 2, 'five', 60, 105)
groove(14, land=True, rot=4, ride=True, ghost=0.5, fill_at=12); fill(59, 1, 'toms16', 70, 100)
fill(60, 4, 'sext', 50, 118)
# 3. contrast
sparse(16, 'side', land=True)
sparse(17, 'side')
sparse(18, 'block', rot=2)
sparse(19, 'block', rot=2)
sparse(20, 'conga', rot=4)
sparse(21, 'conga', rot=1)
fill(88, 8, 'roll', 15, 115)
# 4. build
groove(24, land=True, ghost=0.55, rot=1)
groove(25, fill_at=8, rot=1, ghost=0.55); fill(102, 2, 'rlk', 60, 105)
tommotif(26, land=True, rot=2)
fill(108, 4, 'para', 55, 105, rot=2)
tommotif(28, land=True, rot=6)
groove(29, rot=6, ghost=0.6, fill_at=8); fill(118, 2, 'rlk', 70, 110)
fill(120, 4, 'rlk', 60, 110, rot=1)
fill(124, 2, 'toms16', 75, 110); fill(126, 2, 'roll', 50, 120)
# 5. motif on the kick
groove(32, land=True, mv='kick', ghost=0.4)
groove(33, mv='kick', fill_at=12); fill(135, 1, 'sext', 70, 110)
groove(34, land=True, mv='kick', rot=3, ride=True)
groove(35, mv='kick', rot=3, ride=True, fill_at=8); fill(142, 2, 'toms16', 65, 112)
tommotif(36, land=True, rot=4)
groove(37, mv='kick', rot=4, fill_at=8); fill(150, 2, 'five', 60, 110)
tommotif(38, land=True, rot=7, fill_at=8); fill(154, 2, 'para', 60, 110, rot=1)
fill(156, 4, 'rlk', 70, 118)
# 6. climax
climax(40, 0, True); climax(41, 0); climax(42, 2, True)
climax(43, 5); climax(44, 3, True); climax(45, 1)
fill(184, 4, 'sext', 80, 120)
fill(188, 4, 'roll', 40, 120)
# 7. release: motif returns
groove(48, land=True, ghost=0.3, dyn=0.75)
groove(49, ghost=0.4, dyn=0.8)
groove(50, ghost=0.5, dyn=0.9, fill_at=12); fill(203, 1, 'toms16', 60, 95)
tommotif(51, land=True, rot=0, fill_at=12); fill(207, 1, 'sext', 70, 108)
# 8. final run
tommotif(52, land=True, rot=1)
climax(53, 0, True)
fill(216, 4, 'rlk', 70, 120)
fill(220, 2, 'sext', 80, 120)
fill(222, 2, 'roll', 60, 125)
END = 224
hit(END, 49, 127, 'R', 0.01)
hit(END, 57, 124, 'L', 0.01)
hit(END, 36, 127, 'RF', 0.01)

# ---------------------------------------------------------------- tempo map
def sect_mult(bar):
    if bar < 16: return 1.0
    if bar < 22: return 0.965
    if bar < 24: return 0.97 + 0.03 * (bar - 22)
    if bar < 32: return 1.0 + 0.03 * (bar - 24) / 7
    if bar < 40: return 1.03
    if bar < 48: return 1.05
    if bar < 52: return 0.99
    return 1.03

bpm = []
for b in range(END + 4):
    m = sect_mult(min(b // 4, 55))
    if b in fill_beats:
        m *= 1.015
    m *= 1 + 0.01 * math.sin(b * 0.37)
    if b == 222: m *= 0.94
    if b == 223: m *= 0.88
    if b >= END: m = 0.85
    bpm.append(112 * m)
secs = sum(60 / x for x in bpm[:END])
k = secs / 118.0
bpm = [x * k for x in bpm]

# ---------------------------------------------------------------- render
msgs = []
for b in range(END + 4):
    msgs.append((b * TPB, 0, mido.MetaMessage('set_tempo', tempo=int(round(60e6 / bpm[b])))))
ev.sort(key=lambda e: (e[0], e[1], e[3]))
for t, n, v, limb, push in ev:
    off = R.gauss(0, 0.007) + push
    if limb == 'L': off += 0.003
    if v < 40: off += 0.006
    if v > 100: off -= 0.003
    tick = max(0, int(round((t + off) * TPB)))
    vel = int(round(v + R.gauss(0, 3.5)))
    vel = max(1, min(127, vel))
    dur = 960 if t >= END else 30
    msgs.append((tick, 2, mido.Message('note_on', channel=9, note=n, velocity=vel)))
    msgs.append((tick + dur, 1, mido.Message('note_off', channel=9, note=n, velocity=0)))

msgs.sort(key=lambda x: (x[0], x[1]))
mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
tr = mido.MidiTrack()
mid.tracks.append(tr)
tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
last = 0
for tick, _, m in msgs:
    tr.append(m.copy(time=tick - last))
    last = tick
tr.append(mido.MetaMessage('end_of_track', time=TPB))
mid.save('solo.mid')
