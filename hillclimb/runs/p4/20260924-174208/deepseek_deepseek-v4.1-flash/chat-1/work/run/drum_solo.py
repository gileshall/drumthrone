#!/usr/bin/env python3
"""
drum_solo.py

Writes solo.mid -- a ~2 minute General MIDI drum solo on MIDI channel 10
(percussion), using mido only.

Structure (4/4, bar numbers 1-based):

    A  bars  1- 6   108 bpm   intro: ride bell, ghost notes, first fill
    B  bars  7-16   126 bpm   the theme is stated, varied, restated on hats
    C  bars 17-26   132 bpm   variation I: doubles travelling around the kit
    D  bars 27-32   104 bpm   break: laid back, rim clicks, space, swell
    E  bars 33-44   136 bpm   development: accent singles, flams, tom rolls
    F  bars 45-58   146 bpm   climax: dense, pushing, singles and doubles
    G  bars 59-64   150 bpm   finale: theme returns, accelerando, last hit

The tempo map breathes (small accels into the climax and the final fill),
the pulse leans ahead in the hot passages and lays back in the break,
and every dynamic shape is made of accents, ghost notes and swells.
"""

import sys

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

PPQ = 480          # ticks per quarter note
CH = 9             # MIDI channel 10 (0-indexed)

# --------------------------------------------------------------- GM drums
KICK     = 36
KICK2    = 35
RIM      = 37
SNARE    = 38
ESNARE   = 40
FLOOR_LO = 41
FLOOR_HI = 43
TOM_LO   = 45
TOM_MID  = 47
TOM_MID2 = 48
TOM_HI   = 50
HAT      = 42
PHAT     = 44
OHAT     = 46
CRASH1   = 49
CRASH2   = 57
SPLASH   = 55
CHINA    = 52
RIDE     = 51
RIDE2    = 59
BELL     = 53
TAMB     = 54
COWBELL  = 56


class Solo(object):
    """Collects note events (in beats) and the tempo map (in beats)."""

    def __init__(self):
        self.ev = []           # [beat, note, velocity, duration_in_beats]
        self.tempos = []       # (beat, bpm)
        self.swing = 0.5       # 0.5 = straight, 0.66 = full triplet shuffle
        self.drift = 0.0       # + = lay back, - = push ahead (in beats)

    # ------------------------------------------------------------- feel
    def tempo(self, beat, bpm):
        self.tempos.append((float(beat), float(bpm)))

    def feel(self, swing=None, drift=None):
        if swing is not None:
            self.swing = swing
        if drift is not None:
            self.drift = drift

    def _shape(self, t, swing, drift):
        """Deliberate placement: swing plus a constant push / lay-back."""
        sw = self.swing if swing is None else swing
        dr = self.drift if drift is None else drift
        if abs(sw - 0.5) > 1e-9:
            frac = t - float(int(t))          # position inside the beat
            q = int(round(frac * 8.0))        # 32nd-note cell 0..7
            d = sw - 0.5
            if q == 4:                        # offbeat eighth
                t += d
            elif q in (2, 6):                 # offbeat sixteenth
                t += d * 0.5
            elif q in (1, 3, 5, 7):           # offbeat thirty-second
                t += d * 0.25
        return t + dr

    # ------------------------------------------------------------- notes
    def hit(self, bar, pos16, note, vel, dur16=1.0, swing=None, drift=None):
        """Strike `note` at sixteenth-note position `pos16` of `bar`."""
        t = (bar - 1) * 4.0 + pos16 * 0.25
        self.ev.append([self._shape(t, swing, drift), note,
                        int(round(min(127.0, max(1.0, vel)))),
                        dur16 * 0.25])

    def hitb(self, bar, beatpos, note, vel, dur=0.25, swing=None, drift=None):
        """Strike `note` at an arbitrary beat offset inside `bar`."""
        t = (bar - 1) * 4.0 + beatpos
        self.ev.append([self._shape(t, swing, drift), note,
                        int(round(min(127.0, max(1.0, vel)))), dur])


# ------------------------------------------------------------ figure helpers
def cym8(s, bar, note=RIDE, base=70, acc=96, accents=(0, 8), skip=(), dur=1.0):
    """A ride / hi-hat line of eighth notes with accents and rests."""
    for i in range(8):
        p = i * 2
        if p in skip:
            continue
        s.hit(bar, p, note, acc if p in accents else base, dur)


def theme(s, bar, cym=RIDE, base=72, acc=98,
          kicks=((0, 106), (6, 92), (10, 98)),
          snares=((4, 108), (12, 112)),
          ghosts=((3, 30), (7, 36), (15, 40)),
          cym_skip=(), cym_accents=(0, 8), extras=()):
    """One bar of the main motif: cymbal time + backbeat + ghost notes."""
    cym8(s, bar, cym, base=base, acc=acc, accents=cym_accents, skip=cym_skip)
    for p, v in kicks:
        s.hit(bar, p, KICK, v, 1.0)
    for p, v in snares:
        s.hit(bar, p, SNARE, v, 1.0)
    for p, v in ghosts:
        s.hit(bar, p, SNARE, v, 0.5)
    for p, n, v in extras:
        s.hit(bar, p, n, v, 0.75)


def run(s, bar, seq, dur16=0.5):
    """A hand-to-hand run: seq is a list of (pos16, note, velocity)."""
    for p, n, v in seq:
        s.hit(bar, p, n, v, dur16)


def roll(s, bar, start, stop, note, v0, v1, step=0.5, dur16=0.3):
    """A swelling roll from `start` to `stop` (sixteenth positions)."""
    n = int(round((stop - start) / step))
    for k in range(n):
        v = v0 + (v1 - v0) * (k / float(max(1, n - 1)))
        s.hit(bar, start + k * step, note, v, dur16)


# ===========================================================================
def compose(s):
    # =====================================================================
    # A -- INTRO (bars 1-6, 108 bpm): alone on the kit
    # =====================================================================
    s.tempo(0, 108)
    s.feel(swing=0.58, drift=0.0)

    # bar 1 -- ride-bell quarters, hi-hat foot on 2 and 4
    for i, v in enumerate((84, 72, 78, 70)):
        s.hit(1, i * 4, BELL, v, 1.0)
    s.hit(1, 4, PHAT, 72, 1.0)
    s.hit(1, 12, PHAT, 74, 1.0)
    s.hit(1, 0, KICK, 96, 2.0)

    # bar 2 -- the first ghost notes appear
    for i, v in enumerate((84, 70, 80, 72)):
        s.hit(2, i * 4, BELL, v, 1.0)
    s.hit(2, 4, PHAT, 72, 1.0)
    s.hit(2, 12, PHAT, 74, 1.0)
    s.hit(2, 0, KICK, 98, 2.0)
    s.hit(2, 7, SNARE, 30, 0.5)
    s.hit(2, 15, SNARE, 36, 0.5)

    # bar 3 -- the backbeat arrives
    cym8(s, 3, RIDE, base=70, acc=98, accents=(0, 8))
    s.hit(3, 0, KICK, 104, 1.0)
    s.hit(3, 10, KICK, 94, 1.0)
    s.hit(3, 4, SNARE, 104, 1.0)
    s.hit(3, 12, SNARE, 108, 1.0)
    s.hit(3, 4, PHAT, 70, 1.0)
    s.hit(3, 12, PHAT, 70, 1.0)
    s.hit(3, 7, SNARE, 34, 0.5)

    # bar 4 -- the motif in full
    cym8(s, 4, RIDE, base=72, acc=100, accents=(0, 6, 8, 14))
    for p, v in ((0, 106), (6, 92), (10, 98)):
        s.hit(4, p, KICK, v, 1.0)
    s.hit(4, 4, SNARE, 106, 1.0)
    s.hit(4, 12, SNARE, 110, 1.0)
    for p, v in ((3, 30), (7, 36), (15, 40)):
        s.hit(4, p, SNARE, v, 0.5)

    # bar 5 -- the swell starts, open hat, pickup tom
    cym8(s, 5, RIDE, base=74, acc=102, accents=(0, 8), skip=(14,))
    s.hit(5, 0, KICK, 108, 1.0)
    s.hit(5, 6, KICK, 96, 1.0)
    s.hit(5, 10, KICK, 100, 1.0)
    s.hit(5, 4, SNARE, 108, 1.0)
    s.hit(5, 12, SNARE, 112, 1.0)
    s.hit(5, 3, SNARE, 34, 0.5)
    s.hit(5, 7, SNARE, 38, 0.5)
    s.hit(5, 14, OHAT, 88, 1.0)
    s.hit(5, 15, TOM_HI, 94, 0.75)

    # bar 6 -- crescendo fill, hands travel down the kit
    s.hit(6, 0, KICK, 108, 1.0)
    s.hit(6, 8, KICK, 104, 1.0)
    run(s, 6, ((0, SNARE, 58), (1, SNARE, 66), (2, SNARE, 74), (3, SNARE, 82),
               (4, TOM_HI, 88), (5, TOM_HI, 92), (6, TOM_MID2, 96), (7, TOM_MID2, 100),
               (8, TOM_MID, 102), (9, TOM_MID, 106), (10, TOM_LO, 108), (11, TOM_LO, 112),
               (12, FLOOR_HI, 112), (13, FLOOR_LO, 116), (14, SNARE, 120)), 0.75)

    # =====================================================================
    # B -- THEME (bars 7-16, 126 bpm)
    # =====================================================================
    s.tempo(24, 126)
    s.feel(swing=0.55, drift=0.0)

    # bar 7 -- crash, the theme is stated
    s.hit(7, 0, CRASH1, 112, 8.0)
    theme(s, 7, cym_skip=(0,), cym_accents=(8,),
          kicks=((0, 112), (6, 94), (10, 98)),
          ghosts=((7, 34), (15, 38)))

    # bar 8 -- repeat of the statement
    theme(s, 8)

    # bar 9 -- varied kick, more ghosts
    theme(s, 9, kicks=((0, 108), (3, 88), (6, 94), (10, 100)),
          ghosts=((7, 36), (11, 30), (15, 42)))

    # bar 10 -- the answer phrase: open hat and a tom pickup
    theme(s, 10, cym_skip=(14,), extras=((14, OHAT, 90), (15, TOM_HI, 96)))

    # bars 11-14 -- the theme returns in another colour (hi-hat), ghosts fill
    theme(s, 11, cym=HAT, base=64, acc=92,
          ghosts=((3, 30), (7, 34), (11, 28), (15, 36)))
    theme(s, 12, cym=HAT, base=64, acc=92,
          kicks=((0, 108), (3, 86), (6, 94), (10, 100)),
          ghosts=((7, 34), (15, 38)))
    theme(s, 13, cym=HAT, base=66, acc=94,
          ghosts=((3, 30), (7, 36), (15, 40)),
          extras=((14, RIM, 84),))
    theme(s, 14, cym=HAT, base=66, acc=96,
          ghosts=((3, 30), (7, 36)), cym_skip=(14,),
          extras=((13, FLOOR_HI, 88), (14, FLOOR_LO, 94), (15, SNARE, 58)))

    # bar 15 -- build
    cym8(s, 15, RIDE, base=78, acc=104, accents=(0, 8))
    s.hit(15, 0, KICK, 110, 1.0)
    s.hit(15, 6, KICK, 98, 1.0)
    s.hit(15, 10, KICK, 102, 1.0)
    s.hit(15, 4, SNARE, 110, 1.0)
    s.hit(15, 12, SNARE, 114, 1.0)
    s.hit(15, 7, SNARE, 36, 0.5)
    s.hit(15, 15, SNARE, 44, 0.5)

    # bar 16 -- fill up the kit and into section C
    s.hit(16, 0, KICK, 112, 1.0)
    s.hit(16, 8, KICK, 108, 1.0)
    run(s, 16, ((0, FLOOR_LO, 92), (1, FLOOR_LO, 96), (2, FLOOR_HI, 98), (3, FLOOR_HI, 102),
                (4, TOM_LO, 104), (5, TOM_LO, 108), (6, TOM_MID, 108), (7, TOM_MID, 112),
                (8, TOM_MID2, 112), (9, TOM_MID2, 114), (10, TOM_HI, 114), (11, TOM_HI, 116),
                (12, SNARE, 118), (13, SNARE, 112), (14, SNARE, 122)), 0.75)

    # =====================================================================
    # C -- VARIATION I (bars 17-26, 132 bpm): doubles around the kit
    # =====================================================================
    s.tempo(64, 132)
    s.feel(swing=0.53, drift=-0.01)          # leaning forward a little

    # bar 17 -- crash, theme louder
    s.hit(17, 0, CRASH1, 116, 8.0)
    theme(s, 17, cym_skip=(0,), cym_accents=(8,), base=74, acc=104,
          kicks=((0, 114), (6, 98), (10, 104)))

    # bar 18 -- the kick pushes
    theme(s, 18, base=74, acc=104,
          kicks=((0, 110), (6, 96), (11, 90), (12, 102)),
          ghosts=((3, 34), (7, 38), (15, 42)))

    # bar 19
    theme(s, 19, base=74, acc=104,
          kicks=((0, 110), (3, 88), (6, 98), (10, 104), (14, 92)),
          ghosts=((7, 38), (11, 32), (15, 44)))

    # bar 20
    theme(s, 20, cym_skip=(14,), base=76, acc=106,
          kicks=((0, 112), (6, 100), (10, 104)),
          ghosts=((3, 34), (7, 40), (11, 32)),
          extras=((14, OHAT, 92), (15, TOM_HI, 98)))

    # bar 21 -- doubles travel down the toms and back
    s.hit(21, 0, KICK, 108, 1.0)
    s.hit(21, 8, KICK, 106, 1.0)
    s.hit(21, 4, PHAT, 74, 1.0)
    s.hit(21, 12, PHAT, 74, 1.0)
    dn = (TOM_HI, TOM_HI, TOM_MID2, TOM_MID2, TOM_MID, TOM_MID, TOM_LO, TOM_LO,
          FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, SNARE, SNARE, SNARE, SNARE)
    for i, n in enumerate(dn):
        v = 104 if i % 2 == 0 else 72
        if i >= 12:
            v = 96 + (i - 12) * 6
        s.hit(21, i, n, v, 0.5)
    s.hit(21, 14, KICK, 100, 1.0)

    # bar 22 -- doubles again, accents on the second note (displaced)
    s.hit(22, 0, KICK, 108, 1.0)
    s.hit(22, 10, KICK, 104, 1.0)
    s.hit(22, 4, SNARE, 110, 1.0)
    s.hit(22, 12, SNARE, 114, 1.0)
    up = (FLOOR_LO, FLOOR_LO, FLOOR_HI, FLOOR_HI, TOM_LO, TOM_LO, TOM_MID, TOM_MID,
          TOM_MID2, TOM_MID2, TOM_HI, TOM_HI, SNARE, SNARE, SNARE, SNARE)
    for i, n in enumerate(up):
        if i in (4, 12):
            continue
        v = 100 if i % 2 == 1 else 70
        if i >= 13:
            v = 92 + (i - 13) * 8
        s.hit(22, i, n, v, 0.5)

    # bar 23 -- singing singles around the kit
    s.hit(23, 0, KICK, 108, 1.0)
    s.hit(23, 8, KICK, 106, 1.0)
    s.hit(23, 4, PHAT, 74, 1.0)
    s.hit(23, 12, PHAT, 74, 1.0)
    cyc = (TOM_HI, TOM_MID2, TOM_MID, TOM_LO, FLOOR_HI, FLOOR_LO, TOM_LO, TOM_MID2)
    for i in range(16):
        s.hit(23, i, cyc[i % 8], 104 if i % 4 == 0 else 76, 0.5)

    # bar 24 -- toms, then the snare gathers
    s.hit(24, 0, KICK, 108, 1.0)
    s.hit(24, 8, KICK, 110, 1.0)
    s.hit(24, 4, PHAT, 74, 1.0)
    s.hit(24, 12, PHAT, 74, 1.0)
    for i, n in enumerate((FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MID, TOM_MID2, TOM_HI,
                           SNARE, SNARE)):
        s.hit(24, i, n, 96 + i * 3, 0.5)
    for i, v in enumerate((80, 84, 88, 92, 96, 100, 108, 116)):
        s.hit(24, 8 + i, SNARE, v, 0.5)

    # bar 25 -- the roll swells, sixteenths into thirty-seconds
    s.hit(25, 0, KICK, 108, 1.0)
    s.hit(25, 8, KICK, 110, 1.0)
    s.hit(25, 4, PHAT, 74, 1.0)
    s.hit(25, 12, PHAT, 74, 1.0)
    for i in range(8):
        s.hit(25, i, SNARE, 60 + i * 4, 0.5)
    roll(s, 25, 8.0, 16.0, SNARE, 92, 122, 0.5, 0.35)

    # bar 26 -- landing, then air
    s.hit(26, 0, CRASH1, 118, 8.0)
    s.hit(26, 0, KICK, 116, 1.0)
    s.hit(26, 4, PHAT, 70, 1.0)
    s.hit(26, 8, KICK, 96, 1.0)
    s.hit(26, 12, SNARE, 92, 1.0)
    s.hit(26, 12, PHAT, 70, 1.0)

    # =====================================================================
    # D -- BREAK (bars 27-32, 104 bpm): laid back, space
    # =====================================================================
    s.tempo(104, 104)
    s.feel(swing=0.62, drift=0.025)          # settling behind the beat

    # bar 27 -- splash, ride bell, rim clicks
    for p, n, v in ((0, RIDE, 66), (2, RIDE, 60), (4, BELL, 78), (6, RIDE, 60),
                    (8, BELL, 76), (10, RIDE, 62), (12, BELL, 80), (14, RIDE, 64)):
        s.hit(27, p, n, v, 1.0)
    s.hit(27, 0, SPLASH, 86, 6.0)
    s.hit(27, 0, KICK, 92, 2.0)
    s.hit(27, 4, RIM, 74, 0.5)
    s.hit(27, 12, RIM, 78, 0.5)
    s.hit(27, 4, PHAT, 66, 1.0)
    s.hit(27, 12, PHAT, 68, 1.0)

    # bar 28 -- half-time feel, ghost notes in the cracks
    cym8(s, 28, HAT, base=58, acc=76, accents=(0, 8))
    s.hit(28, 0, KICK, 94, 1.0)
    s.hit(28, 8, SNARE, 100, 1.0)
    s.hit(28, 4, PHAT, 66, 1.0)
    s.hit(28, 12, PHAT, 66, 1.0)
    s.hit(28, 3, SNARE, 26, 0.5)
    s.hit(28, 11, SNARE, 28, 0.5)
    s.hit(28, 15, SNARE, 30, 0.5)

    # bar 29 -- the feet answer
    cym8(s, 29, HAT, base=58, acc=78, accents=(0, 8))
    s.hit(29, 0, KICK, 96, 1.0)
    s.hit(29, 10, KICK, 86, 1.0)
    s.hit(29, 8, SNARE, 100, 1.0)
    s.hit(29, 4, PHAT, 66, 1.0)
    s.hit(29, 12, PHAT, 66, 1.0)
    s.hit(29, 3, SNARE, 26, 0.5)
    s.hit(29, 7, SNARE, 28, 0.5)
    s.hit(29, 14, TOM_HI, 84, 0.75)
    s.hit(29, 15, TOM_MID, 88, 0.75)

    # bar 30 -- alone again, with a cowbell for colour
    for p, n, v in ((0, BELL, 78), (4, RIDE, 66), (8, BELL, 80), (12, RIDE, 68)):
        s.hit(30, p, n, v, 1.0)
    s.hit(30, 0, KICK, 92, 1.0)
    s.hit(30, 4, PHAT, 64, 1.0)
    s.hit(30, 12, PHAT, 64, 1.0)
    s.hit(30, 6, COWBELL, 72, 1.0)
    s.hit(30, 14, COWBELL, 68, 1.0)
    s.hit(30, 7, SNARE, 30, 0.5)
    s.hit(30, 15, SNARE, 34, 0.5)
    s.hit(30, 12, RIM, 72, 0.5)

    # bar 31 -- building back up
    cym8(s, 31, HAT, base=62, acc=84, accents=(0, 8))
    s.hit(31, 0, KICK, 100, 1.0)
    s.hit(31, 6, KICK, 92, 1.0)
    s.hit(31, 10, KICK, 96, 1.0)
    s.hit(31, 4, SNARE, 100, 1.0)
    s.hit(31, 12, SNARE, 104, 1.0)
    s.hit(31, 3, SNARE, 30, 0.5)
    s.hit(31, 7, SNARE, 34, 0.5)
    s.hit(31, 15, SNARE, 40, 0.5)

    # bar 32 -- buzz-roll swell, and the tempo starts to lift
    s.tempo(124, 106)
    s.tempo(126, 120)
    roll(s, 32, 0.0, 8.0, SNARE, 48, 93, 0.5, 0.35)
    for i in range(8):
        s.hit(32, 8 + i, SNARE, 96 + i * 3, 0.5)
    s.hit(32, 0, KICK, 100, 1.0)
    s.hit(32, 8, KICK, 104, 1.0)
    s.hit(32, 12, PHAT, 70, 1.0)

    # =====================================================================
    # E -- DEVELOPMENT (bars 33-44, 136 bpm)
    # =====================================================================
    s.tempo(128, 136)
    s.feel(swing=0.52, drift=-0.015)

    # bar 33 -- crash, the theme in full voice
    s.hit(33, 0, CRASH1, 116, 8.0)
    theme(s, 33, cym_skip=(0,), cym_accents=(8,), base=76, acc=104,
          kicks=((0, 114), (6, 98), (10, 104)),
          ghosts=((3, 32), (7, 38), (15, 44)))

    # bars 34-36 -- the theme with more air in it
    theme(s, 34, base=76, acc=104, ghosts=((3, 32), (7, 38), (11, 30), (15, 44)))
    theme(s, 35, base=76, acc=104,
          kicks=((0, 110), (3, 90), (6, 96), (10, 102), (14, 92)),
          ghosts=((7, 38), (15, 44)))
    theme(s, 36, cym_skip=(14,), base=78, acc=106,
          kicks=((0, 112), (6, 100), (10, 104)),
          ghosts=((3, 34), (7, 40), (11, 32)),
          extras=((14, OHAT, 94), (15, TOM_HI, 100)))

    # bar 37 -- accent singles, left foot marking eighths
    for i in range(16):
        v = 110 if i % 4 == 0 else 48 + (i % 4) * 4
        s.hit(37, i, SNARE, v, 0.5)
    for i in range(8):
        s.hit(37, i * 2, PHAT, 74 if i % 2 == 0 else 62, 0.5)
    s.hit(37, 0, KICK, 108, 1.0)
    s.hit(37, 11, KICK, 100, 1.0)

    # bar 38 -- accents displaced, flams on the strong beats
    for i in range(16):
        v = 112 if i in (0, 3, 6, 10, 13) else 46 + (i % 3) * 4
        s.hit(38, i, SNARE, v, 0.5)
    s.hit(38, -0.25, SNARE, 58, 0.3)
    s.hit(38, 2.75, SNARE, 58, 0.3)
    s.hit(38, 9.75, SNARE, 58, 0.3)
    for i in range(8):
        s.hit(38, i * 2, PHAT, 72 if i % 2 == 0 else 60, 0.5)
    s.hit(38, 0, KICK, 108, 1.0)
    s.hit(38, 8, KICK, 106, 1.0)

    # bars 39-40 -- doubles and singles travelling the kit
    s.hit(39, 0, KICK, 108, 1.0)
    s.hit(39, 8, KICK, 106, 1.0)
    s.hit(39, 4, PHAT, 74, 1.0)
    s.hit(39, 12, PHAT, 74, 1.0)
    run(s, 39, ((0, SNARE, 108), (1, SNARE, 66), (2, SNARE, 104), (3, SNARE, 64),
                (4, TOM_HI, 100), (5, TOM_HI, 62), (6, TOM_MID2, 98), (7, TOM_MID2, 60),
                (8, SNARE, 110), (9, SNARE, 68), (10, TOM_MID, 100), (11, TOM_MID, 62),
                (12, TOM_LO, 104), (13, TOM_LO, 64), (14, SNARE, 112), (15, SNARE, 70)))

    s.hit(40, 0, KICK, 110, 1.0)
    s.hit(40, 8, KICK, 108, 1.0)
    s.hit(40, 4, PHAT, 74, 1.0)
    s.hit(40, 12, PHAT, 74, 1.0)
    run(s, 40, ((0, SNARE, 96), (1, TOM_HI, 92), (2, TOM_HI, 70), (3, TOM_MID2, 96),
                (4, TOM_MID2, 72), (5, TOM_MID, 100), (6, TOM_MID, 74), (7, TOM_LO, 104),
                (8, TOM_LO, 76), (9, FLOOR_HI, 106), (10, FLOOR_HI, 78), (11, FLOOR_LO, 108),
                (12, FLOOR_LO, 80), (13, SNARE, 110), (14, SNARE, 116), (15, SNARE, 122)))

    # bars 41-42 -- rolls swell and resolve
    s.hit(41, 0, KICK, 106, 1.0)
    s.hit(41, 8, KICK, 104, 1.0)
    s.hit(41, 4, PHAT, 72, 1.0)
    s.hit(41, 12, PHAT, 72, 1.0)
    roll(s, 41, 0.0, 16.0, SNARE, 44, 96, 1.0, 0.6)

    s.hit(42, 0, KICK, 106, 1.0)
    s.hit(42, 8, KICK, 104, 1.0)
    for i in range(8):
        n = (SNARE, TOM_HI, TOM_MID2, TOM_MID, TOM_LO, FLOOR_HI, FLOOR_LO, SNARE)[i]
        s.hit(42, i * 2, n, 104 if i % 2 == 0 else 92, 0.75)
        s.hit(42, i * 2 + 1, SNARE, 44, 0.4)

    # bars 43-44 -- the roll takes the toms and lands
    s.hit(43, 0, KICK, 108, 1.0)
    s.hit(43, 8, KICK, 106, 1.0)
    s.hit(43, 4, PHAT, 72, 1.0)
    s.hit(43, 12, PHAT, 72, 1.0)
    for i in range(16):
        n = (TOM_HI if i < 4 else TOM_MID2 if i < 8 else
             TOM_MID if i < 12 else TOM_LO)
        s.hit(43, i, n, 60 + i * 4, 0.5)

    s.hit(44, 0, KICK, 110, 1.0)
    s.hit(44, 8, KICK, 108, 1.0)
    for p, n in ((0, TOM_HI), (1, TOM_HI), (2, TOM_MID2), (3, TOM_MID2),
                 (4, TOM_MID), (5, TOM_MID), (6, TOM_LO), (7, TOM_LO),
                 (8, FLOOR_HI), (9, FLOOR_HI), (10, FLOOR_LO), (11, FLOOR_LO),
                 (12, SNARE), (13, SNARE), (14, SNARE), (15, SNARE)):
        s.hit(44, p, n, 96 + p * 2, 0.5)

    # =====================================================================
    # F -- CLIMAX (bars 45-58, 146 bpm)
    # =====================================================================
    s.tempo(176, 146)
    s.feel(swing=0.5, drift=-0.02)           # pushing the time

    # bar 45 -- crash, theme at full power
    s.hit(45, 0, CRASH1, 118, 8.0)
    theme(s, 45, cym_skip=(0,), base=80, acc=108,
          kicks=((0, 118), (6, 102), (10, 108)),
          ghosts=((3, 34), (7, 40), (15, 46)))

    # bar 46 -- double kick pushes into the backbeat
    theme(s, 46, base=80, acc=108,
          kicks=((0, 112), (6, 100), (11, 94), (12, 106)),
          ghosts=((3, 34), (7, 40), (15, 46)))

    # bar 47 -- second crash
    s.hit(47, 0, CRASH2, 114, 8.0)
    theme(s, 47, cym_skip=(0,), base=80, acc=108,
          kicks=((0, 116), (6, 102), (10, 108)),
          ghosts=((7, 40), (15, 46)))

    # bar 48
    theme(s, 48, cym_skip=(14,), base=80, acc=108,
          kicks=((0, 112), (6, 102), (10, 106)),
          ghosts=((3, 36), (7, 40)),
          extras=((14, OHAT, 96), (15, TOM_HI, 102)))

    # bars 49-52 -- singles and doubles racing around the kit
    cyc = (TOM_HI, TOM_MID2, TOM_MID, TOM_LO, FLOOR_HI, TOM_LO, TOM_MID, TOM_MID2)
    s.hit(49, 0, KICK, 110, 1.0)
    s.hit(49, 8, KICK, 108, 1.0)
    s.hit(49, 4, PHAT, 76, 1.0)
    s.hit(49, 12, PHAT, 76, 1.0)
    for i in range(16):
        s.hit(49, i, cyc[i % 8], 104 if i % 4 == 0 else 80, 0.5)

    cyc2 = (FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MID, TOM_MID2, TOM_HI, TOM_MID2, TOM_MID)
    s.hit(50, 0, KICK, 110, 1.0)
    s.hit(50, 8, KICK, 108, 1.0)
    s.hit(50, 4, PHAT, 76, 1.0)
    s.hit(50, 12, PHAT, 76, 1.0)
    for i in range(16):
        s.hit(50, i, cyc2[i % 8], 106 if i in (2, 6, 10, 14) else 78, 0.5)

    dbl = (TOM_HI, TOM_HI, TOM_MID2, TOM_MID2, TOM_MID, TOM_MID, TOM_LO, TOM_LO,
           FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, SNARE, SNARE, SNARE, SNARE)
    s.hit(51, 0, KICK, 110, 1.0)
    s.hit(51, 8, KICK, 108, 1.0)
    s.hit(51, 4, PHAT, 76, 1.0)
    s.hit(51, 12, PHAT, 76, 1.0)
    for i, n in enumerate(dbl):
        v = 108 if i % 2 == 0 else 74
        if i >= 12:
            v = 100 + (i - 12) * 6
        s.hit(51, i, n, v, 0.5)

    up2 = (FLOOR_LO, FLOOR_LO, FLOOR_HI, FLOOR_HI, TOM_LO, TOM_LO, TOM_MID, TOM_MID,
           TOM_MID2, TOM_MID2, TOM_HI, TOM_HI, SNARE, SNARE, SNARE, SNARE)
    s.hit(52, 0, KICK, 110, 1.0)
    s.hit(52, 10, KICK, 106, 1.0)
    s.hit(52, 4, SNARE, 112, 1.0)
    s.hit(52, 12, SNARE, 116, 1.0)
    for i, n in enumerate(up2):
        if i in (4, 12):
            continue
        v = 102 if i % 2 == 1 else 72
        if i >= 13:
            v = 96 + (i - 13) * 8
        s.hit(52, i, n, v, 0.5)

    # bars 53-54 -- back to the theme, driving
    s.hit(53, 0, CRASH1, 118, 8.0)
    theme(s, 53, cym_skip=(0,), base=82, acc=110,
          kicks=((0, 118), (6, 104), (10, 110), (14, 100)),
          ghosts=((3, 36), (7, 42), (11, 34), (15, 48)))
    theme(s, 54, base=82, acc=110,
          kicks=((0, 114), (3, 92), (6, 104), (10, 110), (14, 100)),
          ghosts=((7, 42), (15, 48)))

    # bars 55-56 -- the feet drive eighths, the hands answer on the toms
    for bar in (55, 56):
        for i in range(8):
            s.hit(bar, i * 2, KICK, 112 if i % 2 == 0 else 96, 1.0)
        for p, n, v in ((1, SNARE, 104), (3, SNARE, 78), (5, TOM_HI, 104),
                        (7, TOM_MID2, 82), (9, TOM_MID, 106), (11, TOM_MID, 80),
                        (13, SNARE, 108), (15, SNARE, 84)):
            s.hit(bar, p, n, v, 0.5)
    # bar 56 turns up the heat
    for p, n, v in ((1, SNARE, 110), (3, SNARE, 84), (5, TOM_HI, 110),
                    (7, TOM_MID2, 88), (9, TOM_MID, 112), (11, TOM_MID, 86),
                    (13, SNARE, 114), (15, SNARE, 92)):
        s.hit(56, p, n, v, 0.5)
    s.hit(56, 15, KICK, 112, 1.0)

    # bar 57 -- the peak
    s.hit(57, 0, CRASH1, 122, 8.0)
    theme(s, 57, cym_skip=(0,), base=84, acc=112,
          kicks=((0, 120), (6, 106), (10, 112)),
          ghosts=((3, 38), (7, 44), (15, 50)))

    # bar 58 -- fill that launches the finale
    s.hit(58, 0, KICK, 116, 1.0)
    s.hit(58, 8, KICK, 112, 1.0)
    run(s, 58, ((0, SNARE, 96), (1, SNARE, 100), (2, TOM_HI, 104), (3, TOM_HI, 106),
                (4, TOM_MID2, 108), (5, TOM_MID2, 110), (6, TOM_MID, 110), (7, TOM_MID, 112),
                (8, TOM_LO, 112), (9, TOM_LO, 114), (10, FLOOR_HI, 114), (11, FLOOR_HI, 116),
                (12, FLOOR_LO, 116), (13, FLOOR_LO, 118), (14, SNARE, 120),
                (15, SNARE, 122)))

    # =====================================================================
    # G -- FINALE (bars 59-64) and the last hit
    # =====================================================================
    s.tempo(232, 150)
    s.feel(swing=0.5, drift=-0.01)

    # bar 59 -- the theme, one last time
    s.hit(59, 0, CRASH2, 120, 8.0)
    theme(s, 59, cym_skip=(0,), base=84, acc=112,
          kicks=((0, 120), (6, 106), (10, 112)),
          ghosts=((3, 36), (7, 44), (15, 50)))

    # bar 60 -- heavier backbeat, kick answers
    theme(s, 60, base=84, acc=112,
          kicks=((0, 116), (6, 106), (11, 96), (12, 108)),
          snares=((4, 114), (12, 118)),
          ghosts=((3, 36), (7, 42), (15, 48)))

    # bar 61 -- a melody on the toms
    s.hit(61, 0, KICK, 116, 1.0)
    s.hit(61, 8, KICK, 112, 1.0)
    s.hit(61, 4, PHAT, 78, 1.0)
    s.hit(61, 12, PHAT, 78, 1.0)
    run(s, 61, ((0, TOM_HI, 112), (1, TOM_MID2, 88), (2, TOM_MID2, 108), (3, TOM_MID, 86),
                (4, TOM_MID, 110), (5, TOM_LO, 88), (6, TOM_LO, 112), (7, FLOOR_HI, 90),
                (8, FLOOR_HI, 110), (9, FLOOR_LO, 88), (10, FLOOR_LO, 112), (11, SNARE, 90),
                (12, SNARE, 108), (13, SNARE, 92), (14, SNARE, 114), (15, SNARE, 118)))

    # bar 62 -- the fill starts to run and the tempo lifts
    s.tempo(248, 156)
    s.hit(62, 0, KICK, 118, 1.0)
    s.hit(62, 8, KICK, 114, 1.0)
    seq62 = (TOM_HI, TOM_HI, TOM_MID2, TOM_MID2, TOM_MID, TOM_MID, TOM_LO, TOM_LO,
             FLOOR_HI, FLOOR_HI, FLOOR_LO, FLOOR_LO, SNARE, SNARE, SNARE, SNARE)
    for i, n in enumerate(seq62):
        s.hit(62, i, n, 88 + i * 2, 0.5)

    # bar 63 -- buzz roll under the kick, getting hotter
    s.tempo(250, 164)
    roll(s, 63, 0.0, 16.0, SNARE, 60, 110, 0.5, 0.3)
    for p in (0, 4, 8, 12):
        s.hit(63, p, KICK, 110, 1.0)

    # bar 64 -- last rush: toms, then thirty-seconds up to the hit
    s.tempo(252, 172)
    seq64 = (FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MID, TOM_MID2, TOM_HI, TOM_MID2, TOM_MID)
    for i in range(8):
        s.hit(64, i, seq64[i], 104 + i * 2, 0.5)
    roll(s, 64, 8.0, 16.0, SNARE, 100, 122, 0.5, 0.3)
    for p in (0, 4, 8, 12):
        s.hit(64, p, KICK, 116, 1.0)

    # bar 65 -- the final hit, left to ring
    s.tempo(256, 176)
    s.feel(swing=0.5, drift=0.0)
    s.hit(65, 0, CRASH1, 127, 24.0)
    s.hit(65, 0, CHINA, 120, 24.0)
    s.hit(65, 0, KICK, 124, 2.0)
    s.hit(65, 4, KICK2, 104, 1.0)


# ===========================================================================
def check_limbs(s):
    """Warn (never fail) if more than two hands / two feet ever coincide."""
    feet = frozenset((KICK, KICK2, PHAT))
    buckets = {}
    for t, note, vel, dur in s.ev:
        buckets.setdefault(int(round(t * PPQ)), set()).add(note)
    bad = 0
    for tick in sorted(buckets):
        notes = buckets[tick]
        nf = len(notes & feet)
        nh = len(notes - feet)
        if nf > 2 or nh > 2:
            bad += 1
            sys.stderr.write("warning: %d hands / %d feet at tick %d\n"
                             % (nh, nf, tick))
    return bad


def build(solo, path):
    mid = MidiFile(type=1, ticks_per_beat=PPQ)

    # ---------------------------------------------------- tempo / meta track
    meta = MidiTrack()
    mid.tracks.append(meta)
    meta.append(MetaMessage('track_name', name='Drum Solo', time=0))
    meta.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))

    last = 0
    for beat, bpm in sorted(solo.tempos):
        tick = int(round(beat * PPQ))
        if tick < last:
            tick = last
        meta.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm),
                                time=tick - last))
        last = tick
    meta.append(MetaMessage('end_of_track', time=0))

    # ------------------------------------------------------------ drum track
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Drums', time=0))

    evs = []
    for t, note, vel, dur in solo.ev:
        on = int(round(t * PPQ))
        off = int(round((t + dur) * PPQ))
        if off <= on:
            off = on + 12
        evs.append((on, 1, note, vel))
        evs.append((off, 0, note, 0))
    evs.sort(key=lambda e: (e[0], e[1]))     # note-offs before note-ons

    prev = 0
    for tick, kind, note, vel in evs:
        delta = tick - prev
        if delta < 0:
            delta = 0
        prev = tick
        if kind:
            track.append(Message('note_on', channel=CH, note=note,
                                 velocity=vel, time=delta))
        else:
            track.append(Message('note_off', channel=CH, note=note,
                                 velocity=0, time=delta))
    track.append(MetaMessage('end_of_track', time=PPQ * 2))

    mid.save(path)


def main():
    s = Solo()
    compose(s)
    check_limbs(s)
    build(s, 'solo.mid')
    last_beat = max(t + d for t, n, v, d in s.ev)
    sys.stdout.write("wrote solo.mid  (%d note events, %.1f beats, %.1f s)\n"
                     % (len(s.ev), last_beat, 0.0))


if __name__ == '__main__':
    main()
