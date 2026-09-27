#!/usr/bin/env python3
"""
drum_solo.py -- writes solo.mid, a two-minute drum solo for a General MIDI
synthesizer. Every stroke is on MIDI channel 10. The only dependency is mido.
The script uses no randomness, so every run writes the same bytes.

Two ideas from the first bar drive the whole piece:
  motif A, "the call":      DOOM . . dum . . DAH .   (3+3+2 sixteenths)
  motif B, "the response":  ta-ka TAK                (two ghosts, then an accent)

Form (100 bpm, 4/4; numbers are bars):
  1-4    Call         A and B on toms and snare, with lots of space.
                      Bar 2 rotates bar 1 by two beats. Paradiddles fill A in.
                      B is chained in threes (3 against 4) as a crescendo.
  5-10   Pocket       Swung-16th groove with ghost notes and a laid-back
                      backbeat. A hides in the kick drum, returns as a fill
                      ending on a splash, then appears in 32nd-note diminution.
  11-18  Development  A tom groove on 3+3+2, then displaced by a sixteenth.
                      Son-clave shots use B as their pickups. 3+3+...+3+2
                      spans two bars. 32nd-note sequences go up, then down.
  19-20  Climax I     A as full-kit unisons, a sextuplet fill and one big hit.
                      Then silence, and A whispered on woodblocks.
  21-28  Cascara      Quiet Latin section: cowbell cascara, woodblock clave
                      (its 3-side is A augmented), tumbao kick. Bars 1-2
                      return on timbales, B answers on bongos, an abanico
                      roll, then A as quarter-note triplets ...
  29-36  12/8         ... which is also how the agogo bell pattern begins.
                      Half-time backbeat, A and B in triplets, a 4-over-3
                      grouping, sextuplets, hands and feet rolling together.
  37-42  Climax II    Double bass under 3+3+2 cymbal shots. Groups of five
                      cross the bar line. A 32nd-note torrent accents the clave.
  43-47  Return       One hit and a breath. The opening four bars return,
                      from pianissimo (B on side stick) back up to fortissimo.
  48-50  Coda         A as a tutti, a last fill, then A resolving onto the
                      final downbeat under a ritardando.

Feel: sixteenths swing at 58% in the grooves. The Latin bars swing more
lightly, and triplet and 32nd passages are straight. Each stroke has a role,
and each role has a fixed placement:
  - cymbal and bell time rides 5 ms ahead of the beat;
  - backbeats sit 10 ms behind it;
  - ghost notes relax 4 ms late;
  - kick and fills sit on the grid.

Playability: every stroke is written for a limb (R, L, RF, LF). A final pass
still enforces the physical limits. No limb strikes again faster than it can,
and at no instant do more than two hand strokes and two foot strokes (notes
35, 36, 44) begin.
"""
import math
from fractions import Fraction as Fr

import mido

OUT_FILE = "solo.mid"
TPB = 960                    # ticks per quarter note
BPM = 100.0
BEAT_MS = 60000.0 / BPM
LEAD = 240                   # a short silence before the first stroke
CHANNEL = 9                  # mido channel 9 == MIDI channel 10

# ------------------------------------------------------------ GM percussion
KICK2, KICK = 35, 36         # left and right bass drum pedals (feet)
SSTK, SN = 37, 38            # side stick, snare
HHC, HHP, HHO = 42, 44, 46   # hi-hat closed, pedal (foot), open
F2, F1, T4, T3, T2, T1 = 41, 43, 45, 47, 48, 50   # toms, low to high
CR, CH, RD, BELL, SPL, C2 = 49, 52, 51, 53, 55, 57
CB = 56                      # cowbell
BGH, BGL = 60, 61            # bongos
TBH, TBL = 65, 66            # timbales
AGH, AGL = 67, 68            # agogo bells
WBH, WBL = 76, 77            # wood blocks

FOOT_NOTES = (35, 36, 44)
LONG_NOTES = (46, 49, 51, 52, 53, 55, 57, 59, 67, 68, 81)

NAMES = {
    'SN': SN, 'SS': SSTK, 'HC': HHC, 'HO': HHO,
    'F2': F2, 'F1': F1, 'T4': T4, 'T3': T3, 'T2': T2, 'T1': T1,
    'CR': CR, 'C2': C2, 'CH': CH, 'SP': SPL, 'RD': RD, 'BL': BELL,
    'CB': CB, 'TH': TBH, 'TL': TBL, 'BH': BGH, 'BG': BGL,
    'AH': AGH, 'AL': AGL, 'WH': WBH, 'WL': WBL,
}

# dynamics: 2 = ghost note ... 8 = accent, X = everything
VEL = {'1': 24, '2': 34, '3': 46, '4': 58, '5': 70,
       '6': 82, '7': 94, '8': 104, '9': 116, 'X': 127}

# deliberate placement per role, in milliseconds (negative = ahead)
ROLE_MS = {'time': -5.0, 'back': 10.0, 'ghost': 4.0}


def swing_of(bar):
    """Swing ratio of sixteenth pairs used in each bar."""
    if 21 <= bar <= 28:
        return 0.54          # lighter lilt for the Latin section
    if 29 <= bar <= 36:
        return 0.5           # triplet section (the swing is in the grid)
    if 37 <= bar <= 40:
        return 0.53
    if 41 <= bar <= 42:
        return 0.5           # 32nd-note torrent: dead straight
    return 0.58


EV = []
SCALE = [1.0]                # dynamic scaling for recapitulations


def N(text):
    return [NAMES.get(tok) for tok in text.split()]


def at(bar, step, grid=16):
    """Absolute position in beats of `step` on a grid of `grid` per bar."""
    return Fr((bar - 1) * 4) + Fr(step * 4, grid)


def hit(t, note, vel, limb, role='auto', sw=None, off=0.0, dur=None):
    if note is None:
        return
    base = VEL.get(vel, 80) if isinstance(vel, str) else int(vel)
    if role == 'auto':
        role = 'ghost' if base <= 40 else 'n'
    v = int(round(20.0 + (base - 20.0) * SCALE[0]))
    v = max(1, min(127, v))
    EV.append({'t': Fr(t), 'note': note, 'vel': v, 'limb': limb,
               'off': ROLE_MS.get(role, 0.0) + off, 'sw': sw, 'dur': dur})


def tab(bar, pattern, note, limb, role='auto', grid=16, sw=None):
    """Drum-tab line: one character per grid step, '.' is a rest."""
    cells = pattern.replace(' ', '').replace('|', '')
    if sw is None and grid % 3 == 0:
        sw = 0.5
    for i, c in enumerate(cells):
        if c in VEL:
            hit(at(bar, i, grid), note, c, limb, role, sw)


def run(bar, start, grid, sticks, notes, vels, sw=None, role='auto'):
    """A sticking line: sticks (R/L/.), drums and dynamics, step by step."""
    sticks = sticks.replace(' ', '')
    vels = vels.replace(' ', '')
    if sw is None and (grid % 3 == 0 or grid >= 32):
        sw = 0.5
    for i, (s, n, c) in enumerate(zip(sticks, notes, vels)):
        if s in ('R', 'L') and n is not None and c in VEL:
            hit(at(bar, start + i, grid), n, c, s, role, sw)


# ================================================================ motifs
def call_bar(bar, tak=SN):
    """Motif A (the call), then motif B (the response) landing on 4."""
    run(bar, 0, 16, 'R..R..R', N('F2 - - F1 - - T3'), '7..6..7')
    run(bar, 10, 16, 'LR', N('SN SN'), '22')
    hit(at(bar, 12), tak, '7', 'L', 'back')
    tab(bar, '7... .... .... ..5.', KICK, 'RF')
    tab(bar, '.... 4... .... 4...', HHP, 'LF')


def answer_bar(bar, tak=SN):
    """The same bar rotated by two beats: response first, then the call."""
    run(bar, 2, 16, 'LR', N('SN SN'), '22')
    hit(at(bar, 4), tak, '7', 'L', 'back')
    run(bar, 8, 16, 'R..R..R', N('F2 - - F1 - - T3'), '7..6..7')
    tab(bar, '6... .... 7... ....', KICK, 'RF')
    tab(bar, '.... 4... .... 4...', HHP, 'LF')


def paradiddle_bar(bar):
    """The call twice, filled in with paradiddles; the second one climbs."""
    run(bar, 0, 16, 'RLRR LRLL RLRR LRLL',
        N('F2 SN SN F1 SN SN T3 SN F1 SN SN T3 SN SN T1 SN'),
        '7227 2272 7337 3383')
    tab(bar, '7... .... 7... ..6.', KICK, 'RF')
    tab(bar, '.... 4... .... 4...', HHP, 'LF')


def threes_bar(bar, big=False):
    """Motif B chained in groups of three sixteenths: 3 against 4."""
    if big:
        notes = N('SN SN CR SN SN T2 SN SN C2 SN SN T4 SN SN CH SN')
    else:
        notes = N('SN SN T1 SN SN T2 SN SN T3 SN SN T4 SN SN F1 SN')
    run(bar, 0, 16, 'RLRL RLRL RLRL RLRL', notes, '2273 3733 8348 4495')
    tab(bar, '5.6. .6.. 7..7 ..8.', KICK, 'RF')
    tab(bar, '.... 4... .... 4...', HHP, 'LF')


# ================================================================ sections
def intro():
    SCALE[0] = 0.82
    call_bar(1)
    SCALE[0] = 0.86
    answer_bar(2)
    SCALE[0] = 0.92
    paradiddle_bar(3)
    SCALE[0] = 1.0
    threes_bar(4)


def groove():
    # bar 5: the pocket arrives with a crash
    hit(at(5, 0), CR, '9', 'R')
    tab(5, '..5. 6.5. 7.5. 6...', HHC, 'R', 'time')
    tab(5, '.... .... .... ..6.', HHO, 'R', 'time')
    tab(5, '...2 ...2 .2.. ...2', SN, 'L')
    tab(5, '.... 8... .... 8...', SN, 'L', 'back')
    tab(5, '8... ..6. ..6. ....', KICK, 'RF')
    # bar 6: motif A hides in the kick (1, 1a, 2&)
    tab(6, '7.5. 6.5. 7.5. 6.5.', HHC, 'R', 'time')
    tab(6, '5... .... .... ....', HHP, 'LF')
    tab(6, '.2.. ...2 .2.. .2..', SN, 'L')
    tab(6, '.... 8... .... 8...', SN, 'L', 'back')
    tab(6, '8..6 ..7. ..6. ....', KICK, 'RF')
    # bar 7: open hat on 2&, foot closes it on 3
    tab(7, '7.5. 6... 7.5. 6.5.', HHC, 'R', 'time')
    tab(7, '.... ..6. .... ....', HHO, 'R', 'time')
    tab(7, '.... .... 5... ....', HHP, 'LF')
    tab(7, '...2 .... .2.2 ...2', SN, 'L')
    tab(7, '.... 8... .... 8...', SN, 'L', 'back')
    tab(7, '8... ..7. ..6. ..6.', KICK, 'RF')
    # bar 8: the call returns as a paradiddle fill, ending on a splash
    tab(8, '7.5. 6.5. .... ....', HHC, 'R', 'time')
    tab(8, '...2 ...2 .... ....', SN, 'L')
    tab(8, '.... 8... .... ....', SN, 'L', 'back')
    run(8, 8, 16, 'RLRR LRLL', N('F2 SN SN F1 SN SN SP SN'), '7337 3383')
    tab(8, '8... ..6. 7..6 ..7.', KICK, 'RF')
    tab(8, '.... .... .... 5...', HHP, 'LF')
    # bar 9: move to the ride, denser ghost notes, hi-hat foot on 2 and 4
    hit(at(9, 0), CR, '9', 'R')
    tab(9, '..5. 6.5. 6.5. 6...', RD, 'R', 'time')
    tab(9, '.... .... .... ..6.', BELL, 'R', 'time')
    tab(9, '...2 ..22 .22. ...3', SN, 'L')
    tab(9, '.... 8... .... 8...', SN, 'L', 'back')
    tab(9, '8... ..7. ..66 ....', KICK, 'RF')
    tab(9, '.... 5... .... 5...', HHP, 'LF')
    # bar 10: the call in 32nd-note diminution around the toms
    tab(10, '6.5. 6.5. .... ....', RD, 'R', 'time')
    tab(10, '...2 ...2 .... ....', SN, 'L')
    tab(10, '.... 8... .... ....', SN, 'L', 'back')
    run(10, 16, 32, 'RLRR LRLL RLRR LRLL',
        N('T1 SN SN T2 SN SN T3 SN F1 SN SN F2 SN SN T4 SN'),
        '7337 3373 8448 4484')
    tab(10, '8... ..6. 7... 7...', KICK, 'RF')
    tab(10, '.... 5... .... 5...', HHP, 'LF')


def development():
    # bars 11-12: a tom groove on 3+3+2, then displaced by one sixteenth
    run(11, 0, 16, 'RLLR LLRL RLLR LLRL',
        N('CR SN SN F1 SN SN T3 SN F2 SN SN F1 SN SN T2 SN'),
        '9227 2372 8227 2373')
    run(12, 0, 16, 'LRLL RLLR LRLL RLLR',
        N('SN F2 SN SN F1 SN SN T3 SN F2 SN SN F1 SN SN T1'),
        '3822 7237 3822 7348')
    for b in (11, 12):
        tab(b, '8... 6... 7... 6...', KICK, 'RF')
        tab(b, '.... 5... .... 5...', HHP, 'LF')

    # bars 13-14: son-clave shots, each approached by motif B, with space
    def shot(b, p, cym):
        t = at(b, p)
        hit(t, cym, '9', 'R')
        hit(t, SN, '8', 'L')
        hit(t, KICK, '9', 'RF')

    shot(13, 0, CR)
    run(13, 4, 16, 'LR', N('SN SN'), '23')
    shot(13, 6, C2)
    run(13, 10, 16, 'LR', N('SN SN'), '23')
    shot(13, 12, CH)
    run(14, 2, 16, 'LR', N('SN SN'), '23')
    shot(14, 4, CR)
    run(14, 6, 16, 'LR', N('SN SN'), '23')
    shot(14, 8, C2)
    run(14, 9, 16, 'RLRLRLR', N('T1 T1 T2 T2 T3 T3 F1'), '4556677')
    tab(14, '.... .... .... 6...', KICK, 'RF')
    for b in (13, 14):
        tab(b, '.... 4... .... 4...', HHP, 'LF')

    # bars 15-16: 3+3+3+3+3+3+3+3+3+3+2 -- the tresillo stretched to two bars
    acc = [CR, F1, T4, F2, F1, T3, C2, F1, T3, T2, T1]
    for q in range(32):
        b, p = 15 + q // 16, q % 16
        g, r = divmod(q, 3)
        prog = q / 31.0
        t = at(b, p)
        if r == 0:
            v = 96 + int(round(18 * prog))
            if acc[g] in (CR, C2):
                v += 12
            hit(t, acc[g], v, 'R')
            hit(t, KICK, 86 + int(round(20 * prog)), 'RF')
        else:
            hit(t, SN, 30 + int(round(24 * prog)), 'L')
    for b in (15, 16):
        tab(b, '.... 5... .... 5...', HHP, 'LF')

    # bars 17-18: the call in 32nds, sequenced up the toms, then down
    up = [F2, F1, T4, T3, T2, T1]
    down = [T1, T2, T3, T4, F1, F2]
    stick8 = 'RLLRLLRL'
    for k in range(63):           # the very last 32nd is a breath
        b, i = 17 + k // 32, k % 32
        beat, j = divmod(i, 8)
        prog = k / 62.0
        if j in (0, 3, 6):
            line = up if b == 17 else down
            note = line[beat + (0, 3, 6).index(j)]
            v = 94 + int(round(28 * prog))
            if k == 0:
                note, v = CR, 118
        else:
            note, v = SN, 44 + int(round(26 * prog))
        hit(at(b, i, 32), note, v, stick8[j], sw=0.5)
    tab(17, '8... 7... 7... 8...', KICK, 'RF')
    tab(18, '8... 8... 8... 9...', KICK, 'RF')
    for b in (17, 18):
        tab(b, '.... 5... .... 5...', HHP, 'LF')


def climax_one():
    # bar 19: motif A as full-kit unisons, then a sextuplet run down the toms
    t = at(19, 0)
    hit(t, CR, 'X', 'L'); hit(t, C2, 'X', 'R'); hit(t, KICK, 'X', 'RF')
    t = at(19, 3)
    hit(t, CH, 'X', 'R'); hit(t, SN, '9', 'L'); hit(t, KICK, 'X', 'RF')
    t = at(19, 6)
    hit(t, CR, 'X', 'L'); hit(t, C2, 'X', 'R'); hit(t, KICK, 'X', 'RF')
    run(19, 12, 24, 'LRLR LRLR LRLR',
        N('T1 T1 T2 T2 T3 T3 T4 T4 F1 F1 F2 F2'), '7788 8999 XXXX')
    for p in (12, 15, 18, 21):
        hit(at(19, p, 24), KICK, '9', 'RF', sw=0.5)
    # bar 20: release -- one hit, silence, the call whispered on woodblocks
    t = at(20, 0)
    hit(t, C2, 'X', 'R', dur=1900); hit(t, SN, 'X', 'L')
    hit(t, KICK, 'X', 'RF')
    run(20, 8, 16, 'L..L..L', N('WL - - WL - - WH'), '4..3..4')
    tab(20, '.... .... .... 3...', HHP, 'LF')


def cascara():
    three = '5... 4... 5.4. ..4.'     # cascara, 3-side
    two = '5... 4.4. ..4. ..4.'       # cascara, 2-side
    tumbao = '.... ..6. .... 6...'
    # 21-22: four-way ostinato; the clave's 3-side is motif A augmented
    tab(21, three, CB, 'R', 'time')
    tab(21, '5... ..5. .... 5...', WBH, 'L')
    tab(21, '5... ..6. .... 6...', KICK, 'RF')
    tab(22, two, CB, 'R', 'time')
    tab(22, '.... 5... 5... ....', WBH, 'L')
    tab(22, tumbao, KICK, 'RF')
    # 23-24: bars 1-2 return on timbales over the ostinato
    tab(23, three, CB, 'R', 'time')
    run(23, 0, 16, 'L..L..L...LLL',
        N('TL - - TL - - TH - - - TL TL TH'), '6..5..7...237')
    tab(23, tumbao, KICK, 'RF')
    tab(24, two, CB, 'R', 'time')
    run(24, 2, 16, 'LLL...L..L..L',
        N('TL TL TH - - - TL - - TL - - TH'), '237...6..5..7')
    tab(24, tumbao, KICK, 'RF')
    # 25: the call on timbales, the response on bongos
    tab(25, '5... 4... 5... ..4.', CB, 'R', 'time')
    run(25, 0, 16, 'L..L..L', N('TL - - TL - - TH'), '7..6..8')
    run(25, 10, 16, 'RLR', N('BH BG BH'), '557')
    tab(25, tumbao, KICK, 'RF')
    # 26: response, a fragment of the call, abanico roll into 27
    tab(26, '5... 5.4. ..4. ....', CB, 'R', 'time')
    run(26, 2, 16, 'LLL...L..L', N('TL TL TH - - - TL - - TL'), '338...6..6')
    run(26, 24, 32, 'RLRLRLRL', [TBH] * 8, '33445567')
    tab(26, tumbao, KICK, 'RF')
    # 27: rimshot + crash landing, the build begins
    t = at(27, 0)
    hit(t, CR, '9', 'R'); hit(t, TBH, 'X', 'L')
    tab(27, '.... 6... 6.5. ..5.', CB, 'R', 'time')
    tab(27, '..22 .2.2 .2.3 .3.3', SN, 'L')
    hit(at(27, 6), T3, '7', 'L')
    hit(at(27, 12), T2, '7', 'L')
    tab(27, '8... ..7. .... 7...', KICK, 'RF')
    # 28: the call as quarter-note triplets pivots into 12/8
    tab(28, '6... 6.5. .... ....', CB, 'R', 'time')
    tab(28, '.22. .... .... ....', SN, 'L')
    hit(at(28, 4), T2, '8', 'L')
    hit(at(28, 7), SN, '3', 'L')
    tab(28, '6... ..7. .... ....', KICK, 'RF')
    run(28, 6, 12, 'RLRLRL', N('F2 SN F1 SN T3 SN'), '838495')
    tab(28, '... ... 8.8 .8.', KICK, 'RF', grid=12)
    for b in range(21, 28):
        tab(b, '.... 4... .... 4...', HHP, 'LF')
    tab(28, '.... 4... .... ....', HHP, 'LF')
    tab(28, '... ... ... 5..', HHP, 'LF', grid=12)


def twelve_eight():
    # 29-32: 12/8 bell on agogo (low bell marks the one), half-time backbeat
    for b in range(29, 33):
        tab(b, '6.. ... ... ...', AGL, 'R', 'time', grid=12)
        tab(b, '..5 .56 .5. 6.5', AGH, 'R', 'time', grid=12)
        tab(b, '... 5.. ... 5..', HHP, 'LF', grid=12)
    for b in (29, 30):
        tab(b, '.2. .2. ... ...', SN, 'L', grid=12)
        tab(b, '... ... 8.. ...', SN, 'L', 'back', grid=12)
    tab(29, '... ... ... .2.', SN, 'L', grid=12)
    tab(29, '8.. ... ..5 ..4', KICK, 'RF', grid=12)
    run(30, 9, 12, 'LLL', N('T1 T2 T3'), '347')
    tab(30, '8.. ... ..5 ..7', KICK, 'RF', grid=12)
    # 31-32: bars 1-2 again, translated into triplets
    run(31, 0, 12, 'L.L.L..LLL', N('T4 - T3 - T2 - - SN SN SN'), '7.6.7..237')
    tab(31, '8.. ... 6.. ..4', KICK, 'RF', grid=12)
    run(32, 1, 12, 'LLL..L.L.L', N('SN SN SN - - T4 - T3 - T2'), '237..7.6.7')
    tab(32, '7.. ... 8.. ..6', KICK, 'RF', grid=12)
    # 33-34: accents every four triplets -- a slower pulse, 4 over 3
    run(33, 0, 12, 'RLRLRLRLRLRL',
        N('CR SN T3 SN F2 SN T3 SN F1 SN T3 SN'), '9243 8343 8354')
    run(34, 0, 12, 'RLRLRLRLRLRL',
        N('C2 SN T3 SN F2 SN T3 SN F1 SN T3 SN'), '9354 8454 9465')
    for b in (33, 34):
        tab(b, '8.. .8. ..8 ...', KICK, 'RF', grid=12)
        tab(b, '5.. 5.. 5.. 5..', HHP, 'LF', grid=12)
    # 35: sextuplets accented every four = quarter-note triplets (A's shape)
    acc = [CR, T1, T2, T3, T4, F1]
    soft = [T1, T1, T2, T3, T4, F1]
    for k in range(24):
        g, r = divmod(k, 4)
        t = at(35, k, 24)
        if r == 0:
            hit(t, acc[g], 100 + 3 * g + (12 if g == 0 else 0), 'R', sw=0.5)
            hit(t, KICK, 92 + 3 * g, 'RF', sw=0.5)
        elif r == 2:
            hit(t, soft[g], 58 + 3 * g, 'R', sw=0.5)
        else:
            hit(t, SN, 40 + 3 * g, 'L', sw=0.5)
    tab(35, '5.....' * 4, HHP, 'LF', grid=24)
    # 36: cymbals on that pulse, then hands and both feet roll together
    accs = [C2, CH, C2]
    lows = [F1, F2, F1]
    for k in range(12):
        g, r = divmod(k, 4)
        t = at(36, k, 24)
        if r == 0:
            hit(t, accs[g], 124, 'R', sw=0.5)
            hit(t, KICK, 116, 'RF', sw=0.5)
        elif r == 2:
            hit(t, lows[g], 78, 'R', sw=0.5)
        else:
            hit(t, SN, 62, 'L', sw=0.5)
    tab(36, '5.....5.....', HHP, 'LF', grid=24)
    for k in range(12, 24):
        prog = (k - 12) / 11.0
        t = at(36, k, 24)
        hand = 'R' if k % 2 == 0 else 'L'
        hit(t, SN, 64 + int(round(60 * prog)), hand, sw=0.5)
        if k % 2 == 0:
            hit(t, KICK, 72 + int(round(40 * prog)), 'RF', sw=0.5)
        else:
            hit(t, KICK2, 72 + int(round(40 * prog)), 'LF', sw=0.5)


def climax_two():
    def shot(b, p, kind):
        t = at(b, p)
        if kind == 'L':                  # left crash, right hand on snare
            hit(t, CR, 'X', 'L'); hit(t, SN, '9', 'R')
        elif kind == 'C':                # china
            hit(t, CH, 'X', 'R'); hit(t, SN, '9', 'L')
        else:                            # right crash
            hit(t, C2, 'X', 'R'); hit(t, SN, '9', 'L')

    def double_bass(b, upto=16, accents=()):
        for p in range(upto):
            v = 108 if p in accents else 84
            if p % 2 == 0:
                hit(at(b, p), KICK, v, 'RF')
            else:
                hit(at(b, p), KICK2, v, 'LF')

    # 37-38: double bass under 3+3+2 cymbal shots
    for p, kind in ((0, 'L'), (3, 'C'), (6, 'R'), (8, 'L'), (11, 'C'), (14, 'R')):
        shot(37, p, kind)
    double_bass(37, accents=(0, 3, 6, 8, 11, 14))
    for p, kind in ((0, 'L'), (3, 'C'), (6, 'R')):
        shot(38, p, kind)
    run(38, 8, 16, 'RLRL RLRL', N('F2 SN T3 T2 T3 SN F1 SN'), '9569 6697')
    double_bass(38, upto=15, accents=(0, 3, 6, 8, 11, 14))

    # 39-40: groups of five across the bar line (5 x 6 + 2 = 32)
    acc5 = [C2, CR, CH, CR, C2, CR, CH]
    toms = [T2, T3, F1, F2]
    for q in range(32):
        b, p = 39 + q // 16, q % 16
        hand = 'R' if q % 2 == 0 else 'L'
        prog = q / 31.0
        t = at(b, p)
        if q % 5 == 0:
            hit(t, acc5[q // 5], 112 + int(round(15 * prog)), hand)
            hit(t, KICK, 100 + int(round(24 * prog)), 'RF')
        elif hand == 'R':
            hit(t, toms[(q // 2) % 4], 72 + int(round(24 * prog)), 'R')
        else:
            hit(t, SN, 50 + int(round(34 * prog)), 'L')
    tab(39, '.... 6... 6... 6...', HHP, 'LF')
    tab(40, '6... 6... 6... 6...', HHP, 'LF')

    # 41-42: 32nd-note torrent over double bass, cymbals mark the son clave
    sweep = [T1, T2, T3, T4, F1, F2, F1, T4, T3, T2]
    marks = {(41, 0): C2, (41, 12): CH, (41, 24): C2, (42, 8): CH, (42, 16): C2}
    for k in range(64):
        b, i = 41 + k // 32, k % 32
        hand = 'R' if k % 2 == 0 else 'L'
        prog = k / 63.0
        t = at(b, i, 32)
        if (b, i) in marks:
            hit(t, marks[(b, i)], 127, hand, sw=0.5)
        elif b == 42 and i >= 24:
            if i < 31:                   # last 32nd left open before the hit
                hit(t, SN, 78 + int(round(46 * (i - 24) / 6.0)), hand, sw=0.5)
        else:
            hit(t, sweep[(k // 2) % 10], 80 + int(round(24 * prog)), hand, sw=0.5)
    for b in (41, 42):
        for p in range(16):
            prog = ((b - 41) * 16 + p) / 31.0
            v = 86 + int(round(18 * prog))
            if (b == 41 and p in (0, 6, 12)) or (b == 42 and p in (4, 8)):
                v = 120
            if p % 2 == 0:
                hit(at(b, p), KICK, v, 'RF', sw=0.5)
            else:
                hit(at(b, p), KICK2, v, 'LF', sw=0.5)


def return_and_coda():
    # 43: the biggest hit, then a breath
    t = at(43, 0)
    hit(t, CR, 'X', 'L', dur=3600); hit(t, C2, 'X', 'R', dur=3600)
    hit(t, KICK, 'X', 'RF'); hit(t, KICK2, 'X', 'LF')
    tab(43, '.... .... .... 3...', HHP, 'LF')

    # 44-47: the opening returns, pianissimo (B on side stick) to fortissimo
    SCALE[0] = 0.55
    call_bar(44, tak=SSTK)
    SCALE[0] = 0.65
    answer_bar(45, tak=SSTK)
    SCALE[0] = 0.85
    paradiddle_bar(46)
    SCALE[0] = 1.05
    threes_bar(47, big=True)
    SCALE[0] = 1.0

    def tutti(b, p, cym, snare_v='9'):
        tt = at(b, p)
        hit(tt, cym, 'X', 'R'); hit(tt, SN, snare_v, 'L')
        hit(tt, KICK, 'X', 'RF')

    # 48: the call as a full-kit statement, the response as a shout
    tutti(48, 0, C2)
    tutti(48, 3, CH)
    t = at(48, 6)
    hit(t, C2, 'X', 'R'); hit(t, CR, 'X', 'L'); hit(t, KICK, 'X', 'RF')
    run(48, 10, 16, 'LR', N('SN SN'), '67')
    tutti(48, 12, CH, 'X')
    tab(48, '.... .... .... 6...', HHP, 'LF')
    tab(48, '.... .... .... ..8.', KICK, 'RF')

    # 49: last fill; the call resolves onto the final downbeat (ritardando)
    run(49, 0, 24, 'LRLR LRLR LRLR',
        N('T1 T1 T2 T2 T3 T3 T4 T4 F1 F1 F2 F2'), '6778 8899 9XXX')
    for p, n, limb in ((0, KICK, 'RF'), (3, KICK2, 'LF'),
                       (6, KICK, 'RF'), (9, KICK2, 'LF')):
        hit(at(49, p, 24), n, '8', limb, sw=0.5)
    tutti(49, 8, C2, 'X')
    tutti(49, 11, CH, 'X')
    tutti(49, 14, C2, 'X')

    # 50: final downbeat, both hands on crashes, both feet, let it ring
    t = at(50, 0)
    hit(t, C2, 'X', 'R', dur=3000); hit(t, CR, 'X', 'L', dur=3000)
    hit(t, KICK, 'X', 'RF', dur=3000); hit(t, KICK2, 'X', 'LF', dur=3000)


def compose():
    intro()
    groove()
    development()
    climax_one()
    cascara()
    twelve_eight()
    climax_two()
    return_and_coda()


# ================================================================ render
TEMPOS = [((1, 0), 100.0), ((49, 0), 98.0), ((49, 4), 95.0),
          ((49, 8), 90.0), ((49, 12), 85.0), ((50, 0), 80.0)]

MARKERS = [(1, 'I. Call and response'), (5, 'II. Pocket'),
           (11, 'III. Development'), (19, 'IV. First climax'),
           (21, 'V. Cascara'), (29, 'VI. Twelve-eight'),
           (37, 'VII. Second climax'), (43, 'VIII. Breath and return'),
           (48, 'IX. Coda')]


def warp(beats, s):
    """Swing: the first sixteenth of every eighth takes the ratio s."""
    if abs(s - 0.5) < 1e-9:
        return beats
    e = math.floor(beats * 2.0 + 1e-9) / 2.0
    f = (beats - e) * 2.0
    if f <= 1e-12:
        return beats
    if f <= 0.5:
        g = f * 2.0 * s
    else:
        g = s + (f - 0.5) * 2.0 * (1.0 - s)
    return e + g / 2.0


def beat_tick(bar, step=0):
    return LEAD + int(at(bar, step) * TPB)


def enforce_instant(notes, is_foot, window):
    """Never more than two strokes of one class starting within `window`."""
    dropped = 0
    recent = []
    for n in notes:
        if not n[5] or ((n[1] in FOOT_NOTES) != is_foot):
            continue
        recent = [m for m in recent if m[5] and n[0] - m[0] <= window]
        if len(recent) >= 2:
            weakest = min(recent, key=lambda m: (m[2], m[0]))
            dropped += 1
            if n[2] > weakest[2]:
                weakest[5] = False
                recent.remove(weakest)
                recent.append(n)
            else:
                n[5] = False
        else:
            recent.append(n)
    return dropped


def render():
    # note record: [tick, note, vel, limb, fixed_dur, alive, dur]
    notes = []
    for ev in EV:
        bar = int(ev['t'] // 4) + 1
        s = ev['sw'] if ev['sw'] is not None else swing_of(bar)
        beats = warp(float(ev['t']), s)
        tick = LEAD + int(round(beats * TPB + ev['off'] * TPB / BEAT_MS))
        notes.append([max(0, tick), ev['note'], ev['vel'], ev['limb'],
                      ev['dur'], True, 0])
    notes.sort(key=lambda n: (n[0], n[1], -n[2]))

    adjusted = 0
    # one sound per drum per instant
    seen = set()
    for n in notes:
        key = (n[0], n[1])
        if key in seen:
            n[5] = False
            adjusted += 1
        else:
            seen.add(key)
    # every limb needs time to travel (40 ms hands, 60 ms feet)
    min_gap = {'R': 64, 'L': 64, 'RF': 96, 'LF': 96}
    last = {}
    for n in notes:
        if not n[5]:
            continue
        prev = last.get(n[3])
        if prev is not None and n[0] - prev[0] < min_gap.get(n[3], 64):
            adjusted += 1
            if n[2] > prev[2]:
                prev[5] = False
                last[n[3]] = n
            else:
                n[5] = False
        else:
            last[n[3]] = n
    # two hands, two feet: at most two strokes of each class at any instant
    adjusted += enforce_instant(notes, True, 20)
    adjusted += enforce_instant(notes, False, 20)

    alive = [n for n in notes if n[5]]
    by_note = {}
    for n in alive:
        by_note.setdefault(n[1], []).append(n)
    for seq in by_note.values():
        for idx, n in enumerate(seq):
            if n[4] is not None:
                want = n[4]
            elif n[1] in LONG_NOTES:
                want = 1500
            else:
                want = 190
            if idx + 1 < len(seq):
                want = min(want, seq[idx + 1][0] - n[0] - 8)
            n[6] = max(1, want)

    msgs = []
    for n in alive:
        msgs.append((n[0], 1, n[1], n[2]))
        msgs.append((n[0] + n[6], 0, n[1], 0))
    msgs.sort()

    drums = mido.MidiTrack()
    drums.append(mido.MetaMessage('track_name', name='Drum solo', time=0))
    drums.append(mido.Message('program_change', channel=CHANNEL, program=0, time=0))
    for ctl, val in ((7, 112), (10, 64), (11, 127), (91, 40), (93, 0)):
        drums.append(mido.Message('control_change', channel=CHANNEL,
                                  control=ctl, value=val, time=0))
    now = 0
    for tick, kind, note, vel in msgs:
        delta = tick - now
        now = tick
        if kind:
            drums.append(mido.Message('note_on', channel=CHANNEL, note=note,
                                      velocity=vel, time=delta))
        else:
            drums.append(mido.Message('note_off', channel=CHANNEL, note=note,
                                      velocity=0, time=delta))
    drums.append(mido.MetaMessage('end_of_track', time=120))

    meta = []
    for (bar, step), bpm in TEMPOS:
        tick = 0 if (bar, step) == (1, 0) else beat_tick(bar, step)
        meta.append((tick, 0, 'tempo', int(round(60000000.0 / bpm))))
    for bar, text in MARKERS:
        meta.append((beat_tick(bar), 1, 'marker', text))
    meta.sort(key=lambda m: (m[0], m[1]))

    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage('track_name', name='drum_solo.py', time=0))
    conductor.append(mido.MetaMessage('time_signature', numerator=4,
                                      denominator=4, time=0))
    now = 0
    for tick, _, kind, value in meta:
        delta = tick - now
        now = tick
        if kind == 'tempo':
            conductor.append(mido.MetaMessage('set_tempo', tempo=value, time=delta))
        else:
            conductor.append(mido.MetaMessage('marker', text=value, time=delta))
    conductor.append(mido.MetaMessage('end_of_track', time=0))

    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(conductor)
    mid.tracks.append(drums)
    return mid, adjusted, len(alive)


def main():
    compose()
    mid, adjusted, count = render()
    mid.save(OUT_FILE)
    try:
        secs = mid.length
    except Exception:
        secs = float('nan')
    print('wrote %s: %d strokes, %.1f seconds, playability adjustments: %d'
          % (OUT_FILE, count, secs, adjusted))


if __name__ == '__main__':
    main()
