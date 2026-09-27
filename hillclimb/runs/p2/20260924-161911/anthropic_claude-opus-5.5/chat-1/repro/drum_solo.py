#!/usr/bin/env python3
"""
drum_solo.py - writes solo.mid: a two-minute General MIDI drum solo on channel 10.

120 BPM, 4/4. 59 bars of playing, a final hit on the downbeat of bar 60,
and the crash rings to exactly 2:00.

Every note is assigned to a limb (RH, LH, RF, LF). A final pass checks that
no limb strikes faster than it physically can, so at most two hands and two
feet ever play at once.

Feel (fixed placement, no randomness):
  * light 16th-note swing in the funk sections
  * backbeats laid back behind the beat
  * ghost notes placed slightly late
  * kicks pushed ahead of the beat in the climax
  * shuffle and triplet sections written on a real triplet grid

Motif A is the accent grouping 3-3-3-3-2-2 across a bar of 16ths. It is
stated, displaced, recast in triplets, moved to timbales, grown out of a
roll, augmented in the kick, turned into ensemble stabs and brought back
at the climax.

Motif B is a six-stroke linear figure (R L K R L K). It runs across the
barline against a quarter-note hi-hat foot, which creates tension.
"""
import mido

TPB = 480
S16 = TPB // 4
BAR = TPB * 4
BPM = 120
CH = 9  # MIDI channel 10

# ---- General MIDI percussion ----
K2, K, SS, SN = 35, 36, 37, 38
F2, CHH, F1, PHH, T4, OHH, T3, T2, CR1, T1 = 41, 42, 43, 44, 45, 46, 47, 48, 49, 50
RIDE, CHINA, BELL, TAMB, SPLASH, COW, CR2, VIBRA = 51, 52, 53, 54, 55, 56, 57, 58
HBONGO, LBONGO, MCONGA, OCONGA, LCONGA, HTIMB, LTIMB = 60, 61, 62, 63, 64, 65, 66
OTRI = 81

RH, LH, RF, LF = 'RH', 'LH', 'RF', 'LF'
KICKS = (K, K2)
GHOSTABLE = {SN, SS, T1, T2, T3, T4, F1, F2, HBONGO, LBONGO,
             MCONGA, OCONGA, LCONGA, HTIMB, LTIMB}

FEEL = {}


def set_feel(swing=0, ghost=6, kick=0, back=0):
    FEEL.update(swing=swing, ghost=ghost, kick=kick, back=back)


set_feel()
events = []  # (tick, note, velocity, limb)


def vclamp(v):
    return max(1, min(127, int(round(v))))


def other(h):
    return LH if h == RH else RH


def hit(bar, pos, note, vel, limb, off=0):
    """pos in 16th notes (floats allowed for triplets / 32nds)."""
    nominal = bar * BAR + int(round(pos * S16))
    t = nominal
    if nominal % TPB in (S16, 3 * S16):
        t += FEEL['swing']
    v = vclamp(vel)
    if note in KICKS:
        t += FEEL['kick']
    elif v < 50 and note in GHOSTABLE:
        t += FEEL['ghost']
    t += off
    t = max(0, t)
    events.append((t, note, v, limb))
    return t


def flam(bar, pos, note, vel, hand, grace=None):
    t = hit(bar, pos, note, vel, hand)
    events.append((max(0, t - 22), grace or note, vclamp(vel * 0.32), other(hand)))


def run(bar, start, n, step, voices, v0, v1, accents=(), boost=18, first=RH):
    for i in range(n):
        p = start + i * step
        hand = first if i % 2 == 0 else other(first)
        v = v0 + (v1 - v0) * i / max(1, n - 1)
        if any(abs(p - a) < 1e-6 for a in accents):
            v += boost
        note = voices[i * len(voices) // n]
        hit(bar, p, note, v, hand)


# ---- Motif A: 3-3-3-3-2-2 accents ----
MA = (0, 3, 6, 9, 12, 14)
A_VOICES = [SN, T1, T2, F1, SN, F2]


def motif_A(bar, voices, acc=110, ghost=None, kicks=(), shift=0, cresc=0,
            ghost_note=SN, crashes=()):
    accpos = []
    for i, p0 in enumerate(MA):
        p = p0 + shift
        if p >= 16:
            continue
        accpos.append(p)
        hand = RH if p % 2 == 0 else LH
        v = acc + cresc * p / 15.0
        note = voices[i]
        if i in crashes:
            note = CR1 if hand == RH else CR2
        hit(bar, p, note, v, hand)
        if i in kicks:
            hit(bar, p, K, v - 8, RF)
    if ghost is not None:
        for p in range(16):
            if p in accpos:
                continue
            hand = RH if p % 2 == 0 else LH
            g = ghost + cresc * 0.4 * p / 15.0 + (8 if (p + 1) in accpos else 0)
            hit(bar, p, ghost_note, g, hand)


# Motif A recast on 16th-note triplets (24 per bar): 3-3-3-3-3-3-2-2-2
MT = (0, 3, 6, 9, 12, 15, 18, 20, 22)


def motif_T(bar, voices, acc, ghost, kicks=(), cresc=0, crashes=(), ghost_note=SN):
    for i in range(24):
        p = i * 2.0 / 3.0
        hand = RH if i % 2 == 0 else LH
        if i in MT:
            j = MT.index(i)
            note = voices[j]
            if j in crashes:
                note = CR1 if hand == RH else CR2
            v = acc + cresc * i / 23.0
            hit(bar, p, note, v, hand)
            if j in kicks:
                hit(bar, p, K, v - 8, RF)
        elif ghost is not None:
            hit(bar, p, ghost_note,
                ghost + cresc * 0.4 * i / 23.0 + (8 if (i + 1) in MT else 0), hand)


# ---- Motif B: six-stroke linear group R L K R L K ----
def six_groups(bar, start, ngroups, acc_voices, a0, a1, g0, g1, k0, k1, mid_voice=T1):
    for g in range(ngroups):
        f = g / max(1, ngroups - 1)
        a = a0 + (a1 - a0) * f
        gv = g0 + (g1 - g0) * f
        kv = k0 + (k1 - k0) * f
        b = start + 6 * g
        hit(bar, b, acc_voices[g % len(acc_voices)], a, RH)
        hit(bar, b + 1, SN, gv, LH)
        hit(bar, b + 2, K, kv, RF)
        hit(bar, b + 3, SN, gv + 6, RH)
        hit(bar, b + 4, mid_voice, (a + gv) / 2.0, LH)
        hit(bar, b + 5, K, kv - 8, RF)


def herta(bar, i0, i1, rhv, lhv, v0, v1):
    n = i1 - i0
    for i in range(i0, i1):
        p = i * 2.0 / 3.0
        beat = i // 6
        r = i % 3
        v = v0 + (v1 - v0) * (i - i0) / max(1, n - 1)
        if r == 0:
            hit(bar, p, rhv[beat % len(rhv)], v + 8, RH)
        elif r == 1:
            hit(bar, p, lhv[beat % len(lhv)], v, LH)
        else:
            hit(bar, p, K, v - 6, RF)


# ---- grooves ----
KA = (0, 3, 10)
KB = (0, 6, 10, 11)


def groove_funk(bar, kicks, open_hat=False, crash=False, ghosts=(7, 9, 15), upto=16):
    set_feel(swing=14, ghost=6, back=8)
    hat_v = (92, 44, 68, 50)
    for p in range(upto):
        if p == 0 and crash:
            hit(bar, 0, CR1, 114, RH)
            continue
        if open_hat and p == 14:
            hit(bar, 14, OHH, 86, RH)
            continue
        if open_hat and p == 15:
            continue
        v = 80 if p in (4, 12) else hat_v[p % 4]
        hit(bar, p, CHH, v, RH)
    for p in (4, 12):
        if p < upto:
            hit(bar, p, SN, 112, LH, off=FEEL['back'])
    gv = (30, 36, 40)
    for i, p in enumerate(ghosts):
        if p < upto:
            hit(bar, p, SN, gv[i % 3], LH)
    for p in kicks:
        if p < upto:
            hit(bar, p, K, 104 if p == 0 else 86, RF)
    if open_hat and upto == 16:
        hit(bar, 16, PHH, 64, LF)


CASCARA = {0: (0, 4, 8, 10, 14), 1: (0, 4, 6, 10, 14)}
CLAVE = {0: (0, 6, 12), 1: (4, 8)}
CONGA = {0: [(0, MCONGA, 34), (4, MCONGA, 78), (8, MCONGA, 34),
             (12, OCONGA, 88), (14, OCONGA, 84)],
         1: [(0, MCONGA, 34), (4, MCONGA, 78), (8, MCONGA, 34), (11, LCONGA, 62),
             (12, OCONGA, 88), (14, LCONGA, 84)]}


def latin_bar(bar, which, rh='cow', lh='clave', stop=16):
    set_feel(swing=0, ghost=5)
    for p in CASCARA[which]:
        if p >= stop:
            continue
        if rh == 'cow':
            hit(bar, p, COW, 72 if p % 4 == 0 else 54, RH)
        else:
            hit(bar, p, BELL, 80 if p % 4 == 0 else 60, RH)
    if lh == 'clave':
        for p in CLAVE[which]:
            hit(bar, p, SS, 84, LH)
    else:
        for p, n, v in CONGA[which]:
            hit(bar, p, n, v, LH)
    hit(bar, 6, K, 72, RF)
    hit(bar, 12, K, 88, RF)
    hit(bar, 4, PHH, 46, LF)
    hit(bar, 12, PHH, 46, LF)


KHA = [(0, RF, 118), (1, LF, 92), (2, RF, 100), (6, RF, 110), (12, RF, 108), (13, LF, 88)]
KHB = [(2, RF, 112), (8, RF, 104), (12, RF, 112), (14, LF, 92), (15, RF, 100)]


def heavy_bar(bar, kpat, rh=CHINA, open_crash=False, kick_until=16):
    set_feel(swing=0, ghost=6, kick=0, back=10)
    vels = (118, 92, 104, 92)
    for q, p in enumerate((0, 4, 8, 12)):
        if p == 0 and open_crash:
            hit(bar, 0, CR1, 124, RH)
            hit(bar, 0, CR2, 118, LH)
        else:
            hit(bar, p, rh, vels[q], RH)
    hit(bar, 8, SN, 124, LH, off=FEEL['back'])
    for p in (3, 11, 15):
        hit(bar, p, SN, 30 + (8 if p == 15 else 0), LH)
    for p, limb, v in kpat:
        if p < kick_until:
            hit(bar, p, K if limb == RF else K2, v, limb)


SKA = [(0, 104), (20.0 / 3.0, 78), (32.0 / 3.0, 88)]
SKB = [(0, 104), (8.0 / 3.0, 74), (32.0 / 3.0, 88), (44.0 / 3.0, 80)]


def shuffle_bar(bar, kpat, ride=False, crash=False, open_hat=False):
    set_feel(swing=0, ghost=5, kick=0, back=8)
    cym = RIDE if ride else CHH
    for b in range(4):
        t0 = 4 * b
        t1 = 4 * b + 4.0 / 3.0
        t2 = 4 * b + 8.0 / 3.0
        if b == 0 and crash:
            hit(bar, 0, CR1, 114, RH)
        else:
            hit(bar, t0, cym, 90 if b % 2 == 0 else 76, RH)
        if open_hat and b == 3 and not ride:
            hit(bar, t2, OHH, 82, RH)
        else:
            hit(bar, t2, cym, 58, RH)
        hit(bar, t1, SN, 28 + (6 if b == 3 else 0), LH)
    hit(bar, 20.0 / 3.0, SN, 24, LH)  # drag into the backbeat
    hit(bar, 8, SN, 114, LH, off=FEEL['back'])
    for p, v in kpat:
        hit(bar, p, K, v, RF)
    if open_hat and not ride:
        hit(bar, 16, PHH, 62, LF)
    if ride:
        hit(bar, 4, PHH, 52, LF)
        hit(bar, 12, PHH, 52, LF)


def pedal(bar, positions=(4, 12), v=56):
    for p in positions:
        hit(bar, p, PHH, v, LF)


# =====================================================================
def compose():
    # ---------- I. Intro: statement of motif A (bars 0-3) ----------
    set_feel(swing=0, ghost=6)
    hit(0, 0, CR1, 118, RH)
    hit(0, 0, K, 112, RF)
    hit(0, 3, T1, 104, LH)
    hit(0, 6, T2, 108, RH)
    hit(0, 6, K, 80, RF)
    hit(0, 9, F1, 110, LH)
    flam(0, 12, SN, 118, RH)
    hit(0, 12, K, 96, RF)
    hit(0, 14, F2, 112, RH)
    hit(0, 14, K, 104, RF)
    pedal(0, v=58)

    # answer: space, then a ghost crescendo into toms
    hit(1, 0, K, 95, RF)
    hit(1, 2, SS, 70, LH)
    for i, p in enumerate(range(8, 12)):
        hit(1, p, SN, 28 + i * 9, LH if p % 2 == 0 else RH)
    hit(1, 12, T4, 106, RH)
    hit(1, 12, K, 96, RF)
    hit(1, 13, SN, 34, LH)
    hit(1, 14, F1, 104, RH)
    hit(1, 15, F2, 96, LH)
    hit(1, 15, K, 90, RF)
    pedal(1, v=58)

    motif_A(2, A_VOICES, acc=108, ghost=26, kicks=(0, 2, 5), cresc=10)
    pedal(2, v=58)

    for p in range(8):
        hand = RH if p % 2 == 0 else LH
        if p == 0:
            hit(3, 0, F2, 110, RH)
            hit(3, 0, K, 100, RF)
        elif p == 3:
            hit(3, 3, T1, 106, LH)
        elif p == 6:
            hit(3, 6, T2, 108, RH)
            hit(3, 6, K, 86, RF)
        else:
            hit(3, p, SN, 28 + 4 * p + (8 if (p + 1) in (3, 6) else 0), hand)
    run(3, 8, 8, 1, [T1, T1, T2, T2, T3, T4, F1, F2], 70, 116, accents=(9, 12, 14), boost=10)
    hit(3, 12, K, 96, RF)
    hit(3, 14, K, 104, RF)
    pedal(3, v=58)

    # ---------- II. Funk groove with motif quotes (bars 4-11) ----------
    groove_funk(4, KA, crash=True)
    groove_funk(5, KB)
    groove_funk(6, KA, open_hat=True)
    groove_funk(7, KA, upto=8)
    run(7, 8, 8, 1, [SN, SN, T1, T1, T2, T3, F1, F2], 62, 108, accents=(9, 12, 14), boost=14)
    hit(7, 12, K, 96, RF)
    hit(7, 14, K, 100, RF)
    groove_funk(8, KB, crash=True)
    groove_funk(9, KA, open_hat=True)
    groove_funk(10, KB, ghosts=(2, 7, 9, 15))
    set_feel(swing=14, ghost=6)
    motif_A(11, A_VOICES, acc=106, ghost=30, kicks=(0, 2, 4, 5), cresc=16)

    # ---------- III. Development (bars 12-19) ----------
    set_feel(swing=10, ghost=6)
    motif_A(12, A_VOICES, acc=112, ghost=30, kicks=(0, 4, 5), cresc=8, crashes=(0,))
    pedal(12)
    motif_A(13, [SN, T1, T2, F1, F2, F2], acc=110, ghost=32, kicks=(0, 2, 4), shift=2, cresc=10)
    pedal(13)
    motif_T(14, [SN, T1, T2, T3, T4, F1, SN, F2, F2], acc=108, ghost=30,
            kicks=(0, 4, 6, 8), cresc=12)
    pedal(14)
    set_feel(swing=0, ghost=6)
    hit(15, 0, F2, 116, RH)
    hit(15, 0, K, 108, RF)
    hit(15, 3, SN, 112, LH)
    hit(15, 6, K, 90, RF)
    hit(15, 6, SS, 60, RH)
    run(15, 8, 16, 0.5, [SN], 30, 112)
    hit(15, 12, K, 90, RF)
    hit(15, 14, K, 100, RF)
    pedal(15)
    # motif B: six-stroke groups over a quarter-note hi-hat foot (6 against 4)
    set_feel(swing=10, ghost=6)
    six_groups(16, 0, 8, [T1, T2, T3, T4, F1, F2, T3, T1], 96, 120, 30, 52, 80, 104)
    for b in (16, 17, 18):
        pedal(b, (0, 4, 8, 12), 56)
    motif_A(19, [CR1, T1, T2, F1, SN, F2], acc=116, ghost=None,
            kicks=(0, 1, 2, 3, 4, 5), cresc=6, crashes=(0,))
    events.append((19 * BAR + 12 * S16 - 22, SN, 40, LH))  # flam grace on beat 4
    pedal(19)

    # ---------- IV. Afro-Cuban contrast (bars 20-27) ----------
    latin_bar(20, 0, 'cow', 'clave')
    latin_bar(21, 1, 'cow', 'clave')
    latin_bar(22, 0, 'bell', 'conga')
    latin_bar(23, 1, 'bell', 'conga')
    # motif A comes back on timbales
    set_feel(swing=0, ghost=5)
    motif_A(24, [HTIMB, HTIMB, LTIMB, LTIMB, HTIMB, LTIMB], acc=100, ghost=30,
            ghost_note=HBONGO, cresc=14)
    hit(24, 6, K, 72, RF)
    hit(24, 12, K, 88, RF)
    pedal(24, v=46)
    motif_A(25, [HTIMB, LTIMB, HTIMB, LTIMB, LTIMB, LTIMB], acc=104, ghost=32,
            ghost_note=MCONGA, shift=2, cresc=12)
    hit(25, 6, K, 72, RF)
    hit(25, 12, K, 88, RF)
    pedal(25, v=46)
    latin_bar(26, 0, 'cow', 'clave', stop=14)
    flam(26, 14, HTIMB, 108, RH)
    set_feel(swing=0, ghost=5)
    run(27, 0, 8, 1, [HTIMB, LTIMB, HTIMB, LTIMB, HTIMB, LTIMB, HTIMB, LTIMB],
        48, 100, accents=(3, 6), boost=12)
    hit(27, 8, CR1, 112, RH)
    hit(27, 8, LTIMB, 118, LH)
    hit(27, 8, K, 110, RF)
    hit(27, 11, HTIMB, 90, LH)
    hit(27, 12, VIBRA, 108, RH)
    hit(27, 12, K, 80, RF)
    pedal(27, v=46)

    # ---------- V. The build (bars 28-35) ----------
    set_feel(swing=0, ghost=0, kick=0)
    for k, bar in enumerate(range(28, 32)):
        for p in range(16):
            g = (k * 16 + p) / 63.0
            base = 22 + 40 * g
            hand = RH if p % 2 == 0 else LH
            if p in MA:
                note = SN if k < 2 else A_VOICES[MA.index(p)]
                v = base + 12 + 34 * g
                hit(bar, p, note, v, hand)
                if k >= 2:
                    hit(bar, p, K, v - 10, RF)
            else:
                hit(bar, p, SN, base, hand)
        if k < 2:
            hit(bar, 0, K, 60 + 8 * k, RF)
            hit(bar, 8, K, 56 + 8 * k, RF)
        pedal(bar, (0, 4, 8, 12), 48 + 5 * k)
    tri_toms = [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F2, F2, T1, T2, F1, F2]
    for k, bar in enumerate((32, 33)):
        for i in range(24):
            gi = (k * 24 + i) / 47.0
            p = i * 2.0 / 3.0
            hand = RH if i % 2 == 0 else LH
            if i % 3 == 0:
                hit(bar, p, tri_toms[k * 8 + i // 3], 86 + 30 * gi, hand)
            else:
                hit(bar, p, SN, 52 + 34 * gi, hand)
        for q, p in enumerate((0, 4, 8, 12)):
            hit(bar, p, K, 88 + 10 * k + 2 * q, RF)
            hit(bar, p, PHH, 60, LF)
    set_feel(swing=0, ghost=0, kick=-5)
    for i in range(32):
        p = i * 0.5
        hand = RH if i % 2 == 0 else LH
        acc = 14 if (i % 2 == 0 and int(p) in MA) else 0
        hit(34, p, SN, 50 + 64 * i / 31.0 + acc, hand)
    for i in range(16):
        if i % 2 == 0:
            hit(34, i, K, 72 + 36 * i / 15.0, RF)
        else:
            hit(34, i, K2, 72 + 36 * i / 15.0, LF)
    run(35, 0, 16, 0.5, [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F1, F1, F2, F2, F2, F2], 92, 122)
    for i in range(8):
        if i % 2 == 0:
            hit(35, i, K, 100 + 2 * i, RF)
        else:
            hit(35, i, K2, 98 + 2 * i, LF)
    hit(35, 8, CR1, 124, RH)
    hit(35, 8, SN, 120, LH)
    hit(35, 8, K, 124, RF)
    hit(35, 11, CR2, 118, RH)
    hit(35, 11, SN, 110, LH)
    hit(35, 11, K, 118, RF)
    hit(35, 14, F2, 120, RH)
    hit(35, 14, SN, 122, LH)
    hit(35, 14, K, 122, RF)

    # ---------- VI. Half-time heavy: motif A augmented in the feet (36-43) ----------
    heavy_bar(36, KHA, open_crash=True)
    heavy_bar(37, KHB)
    heavy_bar(38, KHA, rh=F2)
    heavy_bar(39, KHA, rh=F2, kick_until=8)
    for i in range(8):
        v = 80 + 42 * i / 7.0
        if i % 2 == 0:
            hit(39, 8 + i, K, v, RF)
        else:
            hit(39, 8 + i, K2, v - 4, LF)
    heavy_bar(40, KHA, open_crash=True)
    heavy_bar(41, KHB)
    set_feel(swing=0, ghost=6, kick=0)
    cym = [CR1, CHINA, CR2, CHINA, CR1, CR2]
    for i, p in enumerate(MA):
        v = 112 + 2 * i
        hit(42, p, cym[i], v, RH)
        hit(42, p, SN if i % 2 == 0 else F2, v, LH)
        hit(42, p, K, v, RF)
    herta(43, 0, 24, [T1, T3, F1, F2], [T2, T4, F2, F1], 70, 118)

    # ---------- VII. Shuffle, trading twos (44-51) ----------
    shuffle_bar(44, SKA, crash=True)
    shuffle_bar(45, SKB, open_hat=True)
    set_feel(swing=0, ghost=5)
    motif_T(46, [SN, T1, T2, T3, F1, F2, SN, T1, F2], acc=108, ghost=30,
            kicks=(0, 3, 5, 7, 8), cresc=12)
    pedal(46, v=54)
    herta(47, 0, 12, [T2, F1], [T3, F2], 72, 96)
    for i in range(12, 24):
        p = i * 2.0 / 3.0
        hand = RH if i % 2 == 0 else LH
        hit(47, p, SN, 64 + 50 * (i - 12) / 11.0 + (14 if i % 3 == 0 else 0), hand)
    hit(47, 8, K, 96, RF)
    hit(47, 12, K, 108, RF)
    pedal(47, v=54)
    shuffle_bar(48, SKA, ride=True, crash=True)
    shuffle_bar(49, SKB, ride=True)
    set_feel(swing=0, ghost=5)
    motif_T(50, [SN, T1, T2, T3, SN, F1, T2, F2, F2], acc=116, ghost=40,
            kicks=tuple(range(9)), cresc=8, crashes=(0, 4))
    pedal(50, v=56)
    for i in range(18):
        p = i * 2.0 / 3.0
        hand = RH if i % 2 == 0 else LH
        note = [SN, T1, T2, T3, T4, F1][i // 3]
        hit(51, p, note, 78 + 34 * i / 17.0 + (12 if i % 3 == 0 else 0), hand)
    run(51, 12, 8, 0.5, [SN], 90, 124)
    for p in (0, 4, 8):
        hit(51, p, K, 100, RF)
    hit(51, 12, K2, 100, LF)
    hit(51, 13, K, 108, RF)
    hit(51, 14, K2, 112, LF)
    hit(51, 15, K, 118, RF)

    # ---------- VIII. Climax: everything returns (52-58) ----------
    set_feel(swing=0, ghost=4, kick=-4)
    motif_A(52, A_VOICES, acc=118, ghost=46, kicks=(0, 1, 2, 3, 4, 5),
            crashes=(0, 4), cresc=6)
    pedal(52, v=62)
    motif_A(53, [T1, T2, F1, SN, F2, F2], acc=116, ghost=48, kicks=(0, 1, 2, 3, 4),
            shift=2, crashes=(2,), cresc=8)
    pedal(53, v=62)
    six_groups(54, 0, 4, [CR1, F1, CR2, F2], 112, 124, 44, 58, 96, 112)
    pedal(54, v=60)
    run(55, 8, 16, 0.5, [T1, T1, T2, T2, T3, T3, T4, T4, F1, F1, F1, F1, F2, F2, F2, F2], 88, 122)
    hit(55, 8, K, 110, RF)
    hit(55, 10, K2, 108, LF)
    hit(55, 12, K, 118, RF)
    hit(55, 14, K2, 116, LF)
    # stabs with space; the hi-hat foot keeps time through the silence
    cym = [CR1, CHINA, CR2, CHINA, CR1, CR2]
    lhn = [SN, F2, SN, F2, SN, SN]
    for i, p in enumerate(MA):
        v = 110 + 3 * i
        hit(56, p, cym[i], v, RH)
        hit(56, p, lhn[i], v, LH)
        hit(56, p, K, v, RF)
    pedal(56, (0, 4, 8, 12), 52)
    hit(56, 15, SN, 42, LH)
    run(57, 0, 24, 2.0 / 3.0, [SN, T1, T2, T3, T4, F1, F2, F2], 72, 116,
        accents=tuple(range(0, 16, 2)), boost=12)
    for q, p in enumerate((0, 4, 8, 12)):
        hit(57, p, K, 100 + 6 * q, RF)
        hit(57, p + 2, K2, 84 + 6 * q, LF)
    flam(58, 0, T1, 122, RH)
    hit(58, 0, K, 118, RF)
    flam(58, 3, T2, 122, LH)
    hit(58, 3, K, 118, RF)
    flam(58, 6, F1, 124, RH)
    hit(58, 6, K, 120, RF)
    run(58, 8, 16, 0.5, [SN], 78, 127)
    for i in range(8):
        v = 90 + 32 * i / 7.0
        if i % 2 == 0:
            hit(58, 8 + i, K, v, RF)
        else:
            hit(58, 8 + i, K2, v, LF)

    # ---------- The final hit ----------
    set_feel(swing=0, ghost=0, kick=0)
    hit(59, 0, CR1, 127, RH)
    hit(59, 0, CR2, 127, LH)
    hit(59, 0, K, 127, RF)
    hit(59, 0, K2, 122, LF)


def make_playable(evs):
    """Enforce physical limits per limb: earlier (then louder) strokes win."""
    mingap = {RH: 50, LH: 50, RF: 90, LF: 90}
    evs = sorted(evs, key=lambda e: (e[0], -e[2], e[1], e[3]))
    last = {}
    out = []
    for e in evs:
        t, n, v, limb = e
        if limb in last and t - last[limb] < mingap[limb]:
            continue
        last[limb] = t
        out.append(e)
    return out


def write_midi(evs, path='solo.mid'):
    merged = {}
    for t, n, v, _ in evs:
        key = (t, n)
        merged[key] = max(merged.get(key, 0), v)
    by_note = {}
    for (t, n), v in merged.items():
        by_note.setdefault(n, []).append((t, v))
    msgs = []
    for n, lst in by_note.items():
        lst.sort()
        for i, (t, v) in enumerate(lst):
            off = t + 60
            if i + 1 < len(lst):
                off = min(off, lst[i + 1][0] - 1)
            off = max(off, t + 1)
            msgs.append((t, 1, n, v))
            msgs.append((off, 0, n, 0))
    msgs.sort(key=lambda m: (m[0], m[1], m[2]))

    mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name='Drum Solo', time=0))
    tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
    tr.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tr.append(mido.Message('program_change', channel=CH, program=0, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=7, value=112, time=0))
    tr.append(mido.Message('control_change', channel=CH, control=10, value=64, time=0))
    now = 0
    for tick, kind, n, v in msgs:
        delta = tick - now
        now = tick
        if kind == 1:
            tr.append(mido.Message('note_on', channel=CH, note=n, velocity=v, time=delta))
        else:
            tr.append(mido.Message('note_off', channel=CH, note=n, velocity=0, time=delta))
    end = 60 * BAR
    tr.append(mido.MetaMessage('end_of_track', time=max(0, end - now)))
    mid.save(path)


if __name__ == '__main__':
    compose()
    write_midi(make_playable(events))
