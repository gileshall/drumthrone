# drum_solo.py — generates a ~2 minute composed drum solo as General MIDI (channel 10).
import mido, random

PPQ = 480
SW = 52                 # swing offset in ticks for off-eighths
BART = PPQ * 4          # ticks per bar (16 sixteenth-units)
rng = random.Random(1971)  # deterministic

# ---- GM percussion map (subset) ----
KICK, SNARE, STICK, ESN, CLAP = 36, 38, 37, 40, 39
HH, PEDAL, OPEN, RIDE, BELL = 42, 44, 46, 51, 53
CRASH, CRASH2, SPLASH = 49, 57, 55
TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LOW, TOM_FLOOR, TOM_LOWFLOOR = 50, 48, 47, 45, 43, 41
CONGA_H, CONGA_L, COWBELL, TAMB = 62, 63, 56, 54
TIMB_H, TIMB_L = 65, 66

FEET = {KICK, PEDAL, 35, 44}
DEFAULT_DUR = {CRASH: 220, CRASH2: 220, SPLASH: 180, OPEN: 130, RIDE: 90,
               BELL: 100, CLAP: 70, SNARE: 60}

def swung(t, swing):
    """tick position of 16th-index t within a bar, with swing on off-8ths/16ths."""
    off = 0
    if t % 4 == 2:
        off = swing
    elif t % 2 == 1:
        off = int(swing * 0.55)
    return int(t * PPQ // 4 + off)

class Song:
    def __init__(self):
        self.events = []  # (abs_tick, note, vel, dur)
        self.bar = 0

    def barbase(self):
        return self.bar * BART

    def hit(self, t, note, vel, dur=None, swing=None, feel=0):
        swing = SW if swing is None else swing
        tick = self.barbase() + swung(t, swing) + feel
        if tick < 0:
            tick = 0
        if dur is None:
            dur = DEFAULT_DUR.get(note, 60)
        self.events.append((tick, note, max(1, min(127, int(vel))), dur))

    def note_abs(self, tick, note, vel, dur=None):
        if dur is None:
            dur = DEFAULT_DUR.get(note, 60)
        self.events.append((tick, note, max(1, min(127, int(vel))), dur))

    def next(self):
        self.bar += 1

# ---------------------------------------------------------------- motifs
# Main motif: beat-4 snare triplet-ish figure (16th indices 12,13,14)
MOTIF = [(12, 104), (13, 52), (14, 108)]
MOTIF_TOMS = [(12, TOM_HIMID), (13, TOM_LOW), (14, TOM_FLOOR)]
MOTIF_BIG = [(10, TOM_HI), (11, TOM_LOMID), (12, TOM_LOW), (13, TOM_FLOOR), (14, TOM_LOWFLOOR)]

def play_motif(s, notes, vel_scale=1.0, swing=SW, feel=0):
    for t, v in notes:
        s.hit(t, v if False else None, 0, swing=swing, feel=feel) if False else None
    # (real implementation below — kept simple)
    for t, vel, note in [(n[0], n[1], n[1] if False else None) for n in []]:
        pass

def play_motif_on(s, pairs, vel_scale=1.0, swing=SW, feel=0):
    """pairs: list of (t, note, base_vel)"""
    for t, note, v in pairs:
        s.hit(t, note, int(v * vel_scale), swing=swing, feel=feel)

MOTIF_SNARE = [(12, SNARE, 104), (13, SNARE, 52), (14, SNARE, 108)]
MOTIF_ON_TOMS = [(12, TOM_HIMID, 104), (13, TOM_LOW, 52), (14, TOM_FLOOR, 108)]
MOTIF_BIG_TOMS = [(10, TOM_HI, 100), (11, TOM_LOMID, 102), (12, TOM_LOW, 104),
                  (13, TOM_FLOOR, 106), (14, TOM_LOWFLOOR, 108)]

# ---------------------------------------------------------------- sections
def intro(s, nbars=4):
    dyn, feel, sw = 62, -7, SW
    for b in range(nbars):
        ramp = b / (nbars - 1)          # 0 -> 1
        d = dyn + 26 * ramp
        for t in (0, 4, 8, 12):                       # pedal hat foot
            s.hit(t, PEDAL, d - 18, swing=sw, feel=feel)
        s.hit(0, KICK, d + 6, swing=sw, feel=feel)
        if b >= 1:
            s.hit(6, KICK, d, swing=sw, feel=feel)
            s.hit(8, STICK, d, swing=sw, feel=feel)   # cross-stick backbeat
        if b >= 2:
            s.hit(14, STICK, d - 8, swing=sw, feel=feel)
            s.hit(11, HH, d - 26, swing=sw, feel=feel)  # soft hand hat
        if b == nbars - 1:                            # pickup into groove
            for i, (t, n) in enumerate([(13, TOM_HIMID), (14, TOM_LOMID), (15, TOM_LOW)]):
                s.hit(t, n, d + 6 + 8 * i, swing=sw, feel=feel)
            s.note_abs(s.barbase() + BART, CRASH, 112, 240)  # crash on downbeat
        s.next()

def fill_small(s, d, sw, feel, big=False):
    start = 12 if not big else 8
    for t in range(start, 16):
        v = d - 20 + (t - start) * 9
        if big and t >= 12:
            n = [TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LOW][t % 4]
        else:
            n = SNARE
        if t == 15 and big:
            s.hit(t, TOM_LOWFLOOR, d + 14, swing=sw, feel=feel)
        else:
            s.hit(t, n, v, swing=sw, feel=feel)

def groove_a(s, nbars=10, dyn=94, feel=0, ride=False, crash_every=0):
    """The core groove: stated, then varied with ghosts and fills."""
    sw = SW
    for b in range(nbars):
        d = dyn + (6 if b >= 5 else 0) + rng.choice((-2, 0, 0, 2))
        if crash_every and b % crash_every == 0:
            s.hit(0, CRASH, min(127, d + 16), swing=sw, feel=feel)
        # hats / ride eighths (one hand)
        for t in range(0, 16, 2):
            if ride:
                v = d + (10 if t % 8 == 0 else (6 if t % 8 == 6 else -6))
                s.hit(t, BELL if t in (0, 6) else RIDE, v, swing=sw, feel=feel)
            else:
                v = d + (10 if t % 8 == 0 else -4)
                s.hit(t, HH, v, swing=sw, feel=feel)
        # kick
        for t in (0, 6, 10):
            if t == 10 and b % 2 == 0 and b < 6:
                continue
            s.hit(t, KICK, d + 8 if t == 0 else d, swing=sw, feel=feel)
        if b >= 4 and b % 2 == 1:
            s.hit(15, KICK, d - 6, swing=sw, feel=feel)
        # backbeat
        s.hit(4, SNARE, d + 12, swing=sw, feel=feel)
        s.hit(12, SNARE, d + 14, swing=sw, feel=feel)
        # ghost notes: deliberate, on the swung up-16ths
        if b >= 1:
            ghosts = rng.choice(([7, 11], [11, 15], [7, 15], [7, 11, 15]))
            for t in ghosts:
                s.hit(t, SNARE, d - 46, swing=sw, feel=feel)
        # motif: state it bar 4, vary bars 6 & 8
        if b == 4:
            # avoid clashing with backbeat: motif replaces nothing (12,13,14 vs snare at 12)
            play_motif_on(s, MOTIF_SNARE, 1.0, sw, feel)
        elif b == 6:
            play_motif_on(s, MOTIF_SNARE, 0.75, sw, feel)
        elif b == 8 and not ride:
            play_motif_on(s, MOTIF_ON_TOMS, 1.05, sw, feel)
        # small fill every 4 bars (except where motif just played)
        if b in (3, 7, 9):
            fill_small(s, d, sw, feel, big=(b == 9))
        s.next()

def develop_b(s, nbars=10):
    """Same skeleton, ride, pushed slightly ahead; motif migrates to toms."""
    groove_a(s, nbars, dyn=100, feel=+4, ride=True, crash_every=4)

def breakdown(s, nbars=6):
    """Half-time latin breakdown: cross-stick, congas, cowbell. Quiet, laid back."""
    sw = int(SW * 1.15)
    feel = -8
    for b in range(nbars):
        ramp = 0 if b < 4 else (b - 3) / 2.0
        d = 60 + 34 * ramp
        for t in (0, 4, 8, 12):                          # cowbell quarters (one hand)
            s.hit(t, COWBELL, d - 14 if t % 8 else d - 2, swing=sw, feel=feel)
        s.hit(0, KICK, d + 4, swing=sw, feel=feel)
        s.hit(8, STICK, d + 8, swing=sw, feel=feel)      # half-time backbeat
        s.hit(6, KICK, d - 6, swing=sw, feel=feel)
        # conga conversation (one hand)
        for t, n, v in ((3, CONGA_L, d - 10), (7, CONGA_H, d - 4),
                        (11, CONGA_L, d - 16), (14, CONGA_H, d - 8)):
            if rng.random() < 0.85:
                s.hit(t, n, v, swing=sw, feel=feel)
        s.hit(10, PEDAL, d - 22, swing=sw, feel=feel)    # soft foot hat
        if b >= 3:                                       # tension rising
            s.hit(13, TIMB_L, d, swing=sw, feel=feel)
            s.hit(15, TIMB_H, d + 8, swing=sw, feel=feel)
        if b == nbars - 1:                               # tumble into the build
            for i, t in enumerate(range(10, 16)):
                s.hit(t, [TOM_LOMID, TOM_LOW, TOM_LOMID, TOM_LOW, TOM_FLOOR, TOM_LOWFLOOR][i],
                      d + i * 4, swing=sw, feel=feel)
        s.next()

def build(s, nbars=6):
    sw = SW
    feel = +2
    for b in range(nbars):
        d = 70 + 9 * b
        s.hit(0, KICK, d + 10, swing=sw, feel=feel)
        s.hit(6, KICK, d, swing=sw, feel=feel)
        s.hit(10, KICK, d - 4 if b < 3 else d, swing=sw, feel=feel)
        s.hit(4, SNARE, d + 8, swing=sw, feel=feel)
        s.hit(12, SNARE, d + 10, swing=sw, feel=feel)
        for t in range(0, 16, 2):                        # hats, growing
            s.hit(t, HH, d - 12 + (8 if t % 8 == 0 else 0), swing=sw, feel=feel)
        if b >= 1:                                       # ghosts creep in
            for t in (7, 11, 15):
                s.hit(t, SNARE, d - 44, swing=sw, feel=feel)
        if b >= 2:                                       # single-stroke toms
            s.hit(9, TOM_HI, d - 8, swing=sw, feel=feel)
            s.hit(11, TOM_HIMID, d - 4, swing=sw, feel=feel)
        if b >= 3:                                       # kick doubles
            s.hit(7, KICK, d - 10, swing=sw, feel=feel)
            s.hit(13, KICK, d - 6, swing=sw, feel=feel)
        if b == nbars - 1:                               # roll into climax
            for t in range(8, 16):
                s.hit(t, SNARE, d - 10 + (t - 8) * 8, swing=sw, feel=feel)
            s.note_abs(s.barbase() + BART, CRASH, 127, 260)
        s.next()

def fill_big(s, d, sw, feel, final=False):
    start = 12 if not final else 8
    ladder = [SNARE, SNARE, TOM_HI, TOM_HIMID, TOM_LOMID, TOM_LOW, TOM_FLOOR, TOM_LOWFLOOR]
    for i, t in enumerate(range(start, 16)):
        if final:
            n = ladder[min(i, len(ladder) - 1)]
        else:
            n = ladder[2 + i] if t >= 12 else SNARE
        v = d - 14 + i * 7
        s.hit(t, n, v, swing=sw, feel=feel)

def climax(s, nbars=12):
    sw = SW
    feel = 0
    for b in range(nbars):
        d = 110 + (4 if b >= 6 else 0)
        if b % 2 == 0:
            s.hit(0, CRASH if b % 4 == 0 else CRASH2, 120, swing=sw, feel=feel)
        for t in range(0, 16, 2):
            n = RIDE if b < 8 else (OPEN if t == 6 else HH)
            s.hit(t, BELL if (t in (0, 6) and b < 8) else n,
                  d + (8 if t % 8 == 0 else -6), swing=sw, feel=feel)
        for t in (0, 6, 10, 13):
            s.hit(t, KICK, d + (6 if t == 0 else 0), swing=sw, feel=feel)
        s.hit(4, SNARE, d + 12, swing=sw, feel=feel)
        s.hit(12, SNARE, d + 14, swing=sw, feel=feel)
        for t in (7, 11, 15):
            if rng.random() < 0.8:
                s.hit(t, SNARE, d - 42, swing=sw, feel=feel)
        # motif recap: full, then tossed to the toms, then cascading
        if b == 3:
            play_motif_on(s, MOTIF_SNARE, 1.1, sw, feel)
        elif b == 5:
            play_motif_on(s, MOTIF_ON_TOMS, 1.1, sw, feel)
        elif b == 7:
            play_motif_on(s, MOTIF_BIG_TOMS, 1.05, sw, feel)
        if b in (4, 8, 11):
            fill_big(s, d, sw, feel, final=(b == 11))
        s.next()

def outro(s, nbars=4):
    sw = SW
    feel = -6
    for b in range(nbars):
        d = 92 - 20 * b
        s.hit(0, KICK, d + 6, swing=sw, feel=feel)
        s.hit(6, KICK, d - 8, swing=sw, feel=feel)
        s.hit(4, SNARE, d, swing=sw, feel=feel)
        s.hit(12, SNARE, d + 4, swing=sw, feel=feel)
        for t in range(0, 16, 2):
            if b < 2 or t % 4 == 0:
                s.hit(t, HH, d - 12, swing=sw, feel=feel)
        if b == 0:
            s.hit(0, SPLASH, d + 12, swing=sw, feel=feel)
        if b == 1:
            play_motif_on(s, MOTIF_SNARE, 0.8, sw, feel)  # motif whisper goodbye
        if b == nbars - 1:
            # final unison: kick + crash + snare, ring out
            s.hit(0, KICK, 118, swing=sw, feel=feel)
            s.hit(0, CRASH, 124, dur=600, swing=sw, feel=feel)
            s.hit(0, SNARE, 110, dur=300, swing=sw, feel=feel)
            s.hit(4, TOM_LOWFLOOR, 100, dur=500, swing=sw, feel=feel)
        s.next()

# ---------------------------------------------------------------- playability
def enforce_limits(events):
    events.sort(key=lambda e: (e[0], -e[2]))
    out, i = [], 0
    while i < len(events):
        tick = events[i][0]
        group = []
        while i < len(events) and events[i][0] == tick:
            group.append(events[i]); i += 1
        feet = [e for e in group if e[1] in FEET]
        hands = [e for e in group if e[1] not in FEET]
        out.extend(feet[:2])     # two feet
        out.extend(hands[:2])    # two hands
    return out

# ---------------------------------------------------------------- assemble
def build_song():
    s = Song()
    intro(s, 4)            # statement of feel
    groove_a(s, 10)        # main groove, motif stated/varied
    develop_b(s, 10)       # ride, pushed, motif to toms
    breakdown(s, 6)        # latin half-time, quiet, tension
    build(s, 6)            # layer-by-layer crescendo
    climax(s, 12)          # full energy, motif recap, big fills
    outro(s, 4)            # deconstruct, ritard, final hit
    return s

def write_midi(path="solo.mid", bpm=104):
    s = build_song()
    events = enforce_limits(s.events)
    total_bars = s.bar
    total_ticks = total_bars * BART

    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name="Drum Solo", time=0))
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

    # note ons/offs
    msgs = []
    for tick, note, vel, dur in events:
        msgs.append((tick, mido.Message("note_on", note=note, velocity=vel, channel=9)))
        msgs.append((tick + dur, mido.Message("note_off", note=note, velocity=0, channel=9)))
    msgs.sort(key=lambda m: (m[0], 0 if m[1].type == "note_on" else 1))

    # ritardando in the final bar: stretch its ticks by 1.6x
    final_bar_start = (total_bars - 1) * BART
    last = 0
    for tick, msg in msgs:
        t = tick
        if tick > final_bar_start:
            t = final_bar_start + int((tick - final_bar_start) * 1.6)
        track.append(msg.copy(time=t - last))
        last = t
    track.append(mido.MetaMessage("end_of_track", time=max(0, total_ticks - last) + BART // 4))

    mid = mido.MidiFile(type=0, ticks_per_beat=PPQ)
    mid.tracks.append(track)
    mid.save(path)
    return total_ticks

if __name__ == "__main__":
    ticks = write_midi("solo.mid")
    beats = ticks / PPQ
    print("wrote solo.mid (%.1f seconds of music)" % (beats * 60 / 104))
