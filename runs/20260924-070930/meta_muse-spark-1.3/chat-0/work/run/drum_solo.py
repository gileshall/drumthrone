import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage
from collections import defaultdict

TPB = 480
TICKS_PER_BAR = 1920
TEMPO = 500000  # 120 BPM
CHANNEL = 9  # MIDI channel 10

# GM percussion notes
KICK2 = 35
KICK = 36
RIM = 37
SNARE = 38
CLAP = 39
ESNARE = 40
FLOOR_LO = 41
HAT_C = 42
FLOOR_HI = 43
HAT_PED = 44
TOM_LO = 45
HAT_O = 46
TOM_MLO = 47
TOM_MHI = 48
CRASH1 = 49
TOM_HI = 50
RIDE1 = 51
CHINA = 52
RIDE_BELL = 53
TAMB = 54
SPLASH = 55
COWBELL = 56
CRASH2 = 57
VIBRA = 58
RIDE2 = 59
BONGO_HI = 60
BONGO_LO = 61
CONGA_MUTE = 62
CONGA_OPEN = 63
CONGA_LO = 64
TIMB_HI = 65
TIMB_LO = 66
AGOGO_HI = 67
AGOGO_LO = 68
CABASA = 69
MARACAS = 70
WHIST_S = 71
GUIRO_S = 73
GUIRO_L = 74
CLAVES = 75
WOOD_HI = 76
WOOD_LO = 77
CUICA_M = 78
CUICA_O = 79
TRI_M = 80
TRI_O = 81

hits = []  # (tick, note, vel, dur)

def swing_adj(base, mode, amt):
    if mode is None or amt == 0:
        return 0
    if base % 120 != 0:
        return 0  # triplets / 32nds: no swing
    if mode == "16":
        if (base // 120) % 2 == 1:
            return amt
    elif mode == "8":
        if base % 480 == 240:
            return amt
    return 0

def P(bar, base, note, vel, dur=110, swing_mode=None, swing_amt=0, feel=0):
    s = swing_adj(base, swing_mode, swing_amt)
    micro = ((bar * 197 + base * 13 + note * 29) % 7) - 3  # -3..+3 deterministic
    vhuman = ((bar * 11 + base * 7 + note) % 5) - 2  # -2..+2
    tick = bar * TICKS_PER_BAR + base + s + feel + micro
    if tick < 0:
        tick = 0
    v = int(vel + vhuman)
    if v < 1:
        v = 1
    if v > 127:
        v = 127
    hits.append((int(tick), int(note), int(v), int(dur)))

def flam(bar, base, note, vel, dur=110, swing_mode=None, swing_amt=0, feel=0):
    P(bar, base, note, vel, dur, swing_mode, swing_amt, feel)
    gv = vel - 55
    if gv < 30:
        gv = 30
    # grace note 22 ticks before, no swing
    P(bar, base - 22, note, gv, 60, None, 0, feel)

MOTIF = [0, 360, 720, 1200, 1440, 1680]  # steps 0,3,6,10,12,14

# ---------------- Intro bars 0-3 : state motif A, dry and laid back ----------------
# bar 0 : low version
P(0, 0, KICK, 112, 120); P(0, 0, FLOOR_LO, 108, 140)
P(0, 360, RIM, 96, 90)
P(0, 720, TOM_LO, 100, 140); P(0, 720, KICK, 88, 120)
P(0, 1200, RIM, 97, 90)
P(0, 1440, TOM_MLO, 103, 140); P(0, 1440, KICK, 92, 120)
flam(0, 1680, RIM, 102, 90)
P(0, 480, HAT_PED, 52, 80, feel=0)
P(0, 960, MARACAS, 34, 90)
P(0, 1440 + 0, HAT_PED, 50, 80)  # coincides: kick+tom+pedal = 3 limbs ok (merged tick differs by micro, still <=4)

# bar 1 : answer higher, with ghost
P(1, 0, KICK, 110, 120); P(1, 0, FLOOR_HI, 106, 140)
P(1, 360, RIM, 42, 80)
P(1, 720, TOM_MHI, 101, 140)
P(1, 1200, RIM, 96, 90)
P(1, 1440, TOM_HI, 104, 140); P(1, 1440, KICK, 90, 120)
P(1, 1560, RIM, 40, 70)
flam(1, 1680, RIM, 104, 90)
P(1, 480, HAT_PED, 54, 80)
P(1, 960, HAT_PED, 52, 80)

# bar 2 : sparse fragmentation, space
P(2, 0, KICK, 100, 120); P(2, 0, FLOOR_LO, 98, 200)
P(2, 720, RIM, 90, 90, feel=10)
P(2, 1440, TOM_MLO, 92, 200); P(2, 1440, KICK, 84, 120)
P(2, 480, HAT_PED, 50, 80)
P(2, 960, CABASA, 44, 120)
P(2, 1200, WOOD_LO, 66, 90)
P(2, 1680, RIM, 44, 70, feel=10)

# bar 3 : fill into groove (8ths then 16ths)
P(3, 0, RIM, 88, 90); P(3, 240, RIM, 90, 90)
P(3, 480, TOM_LO, 94, 130); P(3, 720, TOM_LO, 96, 130)
P(3, 960, TOM_MLO, 98, 130); P(3, 1200, TOM_MLO, 100, 130)
P(3, 1440, TOM_MHI, 104, 120); P(3, 1560, TOM_MHI, 106, 120)
P(3, 1680, TOM_HI, 108, 120); P(3, 1800, TOM_HI, 110, 120)
P(3, 1440, KICK, 90, 120)

# ---------------- Groove A bars 4-11 : funk, light swung 16ths, laid-back snare ----------------
for bar in range(4, 12):
    sw = "16"
    sa = 14
    # crash on section start
    if bar == 4:
        P(bar, 0, CRASH1, 114, 1600, sw, sa, feel=-4)
    if bar == 8:
        P(bar, 0, CRASH1, 110, 1500, sw, sa, feel=-4)
        P(bar, 0, RIDE_BELL, 100, 300, sw, sa, feel=-4)
    # hats: continuous 16ths, accents on quarters
    for s in range(16):
        base = s * 120
        if s % 4 == 0:
            v = 96 if s % 8 == 0 else 92
        elif s % 2 == 0:
            v = 82
        else:
            v = 60
        # open hat on bar 7 and 11 offbeat
        if bar in (7, 11) and s == 14:
            P(bar, base, HAT_O, 92, 500, sw, sa, feel=-5)
        else:
            P(bar, base, HAT_C, v, 100, sw, sa, feel=-5)
    # kick syncopated
    if bar % 4 == 3:
        kicks = [0, 360, 720, 1200, 1680]
    elif bar % 2 == 1:
        kicks = [0, 720, 1200, 1560]
    else:
        kicks = [0, 720, 1200]
    for kb in kicks:
        P(bar, kb, KICK, 108 if kb == 0 else 102, 120, sw, sa, feel=-2)
    # snare backbeat laid back + ghosts pushed slightly
    P(bar, 480, SNARE, 118, 120, sw, sa, feel=12)
    P(bar, 1440, SNARE, 120, 120, sw, sa, feel=12)
    P(bar, 840, SNARE, 38, 70, sw, sa, feel=4)
    P(bar, 1320, SNARE, 42, 70, sw, sa, feel=4)
    if bar % 2 == 1:
        P(bar, 1800, SNARE, 36, 70, sw, sa, feel=4)
    # foot hats on 2 & 4 (coincides with snare+hat hand = 3 limbs)
    P(bar, 480, HAT_PED, 55, 80, sw, sa, feel=0)
    P(bar, 1440, HAT_PED, 55, 80, sw, sa, feel=0)

# ---------------- Development bars 12-19 : call (ride groove) / response (tom motif) ----------------
for bar in range(12, 20):
    if bar in (12, 13, 16, 17):  # call : ride groove straight
        for i, base in enumerate([0, 240, 480, 720, 960, 1200, 1440, 1680]):
            v = 100 if base == 0 else (94 if base % 480 == 0 else 86)
            P(bar, base, RIDE1, v, 250, feel=-3)
        if bar in (12, 16):
            P(bar, 0, RIDE_BELL, 104, 300, feel=-3)
        kicks = [0, 720, 1200] if bar % 2 == 0 else [0, 600, 1200, 1560]
        # keep kicks on grid multiples of 120 except 600 (triplet-ish push) -> keep musical push
        for kb in kicks:
            P(bar, kb, KICK, 106, 120, feel=-2)
        P(bar, 480, SNARE, 117, 120, feel=10)
        P(bar, 1440, SNARE, 119, 120, feel=10)
        P(bar, 840, SNARE, 40, 70, feel=4)
        P(bar, 1680 if bar % 2 == 0 else 1800, SNARE, 38, 70, feel=4)
        P(bar, 480, HAT_PED, 56, 80)
        P(bar, 1440, HAT_PED, 56, 80)
        if bar == 12:
            P(bar, 0, CRASH2, 112, 1500, feel=-4)
    else:  # response : motif rhythm on toms + cowbell ostinato (motivic variation)
        # cowbell 8ths
        for base in [0, 240, 480, 720, 960, 1200, 1440, 1680]:
            P(bar, base, COWBELL, 84, 110, feel=0)
        # tom melody: same MOTIF rhythm, pitch contour varies per bar
        if bar == 14:
            orch = [(0, FLOOR_HI), (360, RIM), (720, TOM_LO), (1200, RIM), (1440, TOM_MLO), (1680, TOM_MHI)]
        elif bar == 15:
            orch = [(0, TOM_LO), (360, TOM_MLO), (720, TOM_MHI), (1200, TOM_HI), (1440, SNARE), (1680, TOM_MHI)]
        elif bar == 18:
            orch = [(0, FLOOR_LO), (360, COWBELL), (720, FLOOR_HI), (1200, TOM_LO), (1440, TOM_MLO), (1680, RIM)]
            # avoid triple cowbell overlap: skip duplicate cowbell at motif points by lower vel (still <=4)
        else:  # 19 fill bar
            orch = [(0, TOM_HI), (360, TOM_MHI), (720, TOM_MLO), (1200, TOM_LO), (1440, FLOOR_HI), (1680, SNARE)]
        for base, nn in orch:
            if nn == COWBELL:
                continue
            v = 108 if base in (0, 1440) else 100
            P(bar, base, nn, v, 140, feel=0)
            if base in (0, 720, 1440):
                P(bar, base, KICK, 102, 120, feel=-2)
        if bar in (15, 19):
            # 16th descending fill last beat
            P(bar, 1440, TOM_HI, 108, 110)
            P(bar, 1560, TOM_MHI, 110, 110)
            P(bar, 1680, TOM_MLO, 112, 110)
            P(bar, 1800, FLOOR_HI, 114, 130)
        if bar == 14:
            P(bar, 0, SPLASH, 100, 900, feel=-4)

# ---------------- Breakdown bars 20-23 : sparse, woody, low dynamics ----------------
CLAVE_PATT = [0, 360, 720, 1200, 1440]
for bar in range(20, 24):
    for cb in CLAVE_PATT:
        P(bar, cb, CLAVES, 88, 100, feel=6)
    # shaker 8ths soft
    for base in [0, 240, 480, 720, 960, 1200, 1440, 1680]:
        P(bar, base, MARACAS, 46, 90, feel=4)
        if base % 480 == 240:
            P(bar, base, CABASA, 40, 90, feel=4)
    P(bar, 0, KICK, 78, 120, feel=0)
    P(bar, 960, KICK, 74, 120, feel=0)
    P(bar, 480, HAT_PED, 48, 80)
    P(bar, 1440, HAT_PED, 48, 80)
    P(bar, 480, RIM, 62, 80, feel=10)
    if bar % 2 == 1:
        P(bar, 1440, TAMB, 66, 150, feel=0)
        P(bar, 720, WOOD_HI, 70, 90, feel=4)
        P(bar, 1560, WOOD_LO, 68, 90, feel=4)
    else:
        P(bar, 1440, RIM, 64, 80, feel=10)
        P(bar, 1080, WOOD_HI, 66, 90, feel=4)
    if bar == 23:
        # soft crescendo snare 8ths into build
        for i, base in enumerate([0, 240, 480, 720, 960, 1200, 1440, 1680]):
            P(bar, base, SNARE, 55 + i * 5, 90, feel=6)
        P(bar, 1680, KICK, 88, 120)

# ---------------- Build bars 24-31 : pushing ahead, rising density + dynamics ----------------
for bar in range(24, 32):
    idx = bar - 24  # 0..7
    cresc = 78 + idx * 5  # 78..113
    feel_push = -6
    # hats: 8ths first 4 bars, 16ths last 4
    if idx < 4:
        for base in [0, 240, 480, 720, 960, 1200, 1440, 1680]:
            v = cresc if base % 480 == 0 else cresc - 10
            P(bar, base, HAT_C, v, 100, feel=feel_push)
        if idx >= 2:
            P(bar, 1200 + 120, HAT_C, cresc - 20, 80, feel=feel_push)  # extra 16th push, no clash (offset 1320 vs snare ghost avoided)
    else:
        for s in range(16):
            base = s * 120
            if s % 4 == 0:
                v = cresc
            elif s % 2 == 0:
                v = cresc - 8
            else:
                v = cresc - 22
            P(bar, base, HAT_C, v, 90, feel=feel_push)
    # open hat offbeats last 4 bars
    if idx >= 4 and bar % 2 == 0:
        P(bar, 720, HAT_O, cresc - 4, 400, feel=feel_push)
    # kick: quarters + growing syncopation
    for qb in [0, 480, 960, 1440]:
        P(bar, qb, KICK, cresc, 120, feel=-3)
    if idx >= 2:
        P(bar, 720, KICK, cresc - 4, 120, feel=-3)
    if idx >= 5:
        P(bar, 1680, KICK, cresc - 2, 120, feel=-3)
    # snare backbeat + increasing ghosts
    P(bar, 480, SNARE, cresc + 10, 120, feel=-2)
    P(bar, 1440, SNARE, cresc + 12, 120, feel=-2)
    P(bar, 840, SNARE, 40 + idx * 3, 70, feel=0)
    if idx >= 3:
        P(bar, 1320, SNARE, 42 + idx * 3, 70, feel=0)
    if idx >= 6:
        P(bar, 1800, SNARE, 44 + idx * 2, 70, feel=0)
    # crash every 2 bars
    if bar % 2 == 0:
        P(bar, 0, CRASH1, cresc + 8, 1400, feel=-4)
    if bar == 31:
        # bar 31 fill: ascending toms 16ths last 2 beats
        for i, base in enumerate([960, 1080, 1200, 1320, 1440, 1560, 1680, 1800]):
            nn = [FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MLO, TOM_MHI, TOM_HI, TOM_MHI, SNARE][i]
            P(bar, base, nn, 108 + i, 110, feel=-2)

# ---------------- Peak bars 32-39 : loud driving, straight ----------------
for bar in range(32, 40):
    if bar == 32:
        P(bar, 0, CRASH1, 124, 1800, feel=-4)
    if bar == 34:
        P(bar, 0, CRASH2, 122, 1700, feel=-4)
    if bar == 36:
        P(bar, 0, CRASH1, 124, 1800, feel=-4)
        P(bar, 0, CHINA, 110, 1500, feel=-4)  # crash+china+kick = 2 hands+foot? china+crash=2 hands ok
    if bar == 38:
        P(bar, 0, SPLASH, 118, 1200, feel=-4)
        P(bar, 0, CRASH2, 122, 1700, feel=-4)
    # ride 8ths (right hand)
    for base in [0, 240, 480, 720, 960, 1200, 1440, 1680]:
        v = 104 if base % 480 == 0 else 94
        P(bar, base, RIDE1, v, 250, feel=-4)
    # china accent
    if bar % 4 == 3:
        P(bar, 720, CHINA, 112, 1200, feel=-4)
    # kick
    kicks = [0, 720, 960, 1200] if bar % 2 == 0 else [0, 480 + 120, 960, 1320, 1680 - 120]
    # normalize 600->600 etc keep on grid: use 600? keep 600 as push (not on 16th) musical
    for kb in kicks:
        P(bar, kb, KICK, 116, 120, feel=-3)
    # snare backbeat loud
    P(bar, 480, SNARE, 124, 120, feel=6)
    P(bar, 1440, SNARE, 126, 120, feel=6)
    P(bar, 840, SNARE, 48, 70, feel=2)
    if bar % 2 == 1:
        P(bar, 1800, SNARE, 46, 70, feel=2)
    P(bar, 480, HAT_PED, 60, 80)
    P(bar, 1440, HAT_PED, 60, 80)
    # fills every 2 bars last beat linear
    if bar % 2 == 1:
        P(bar, 1440, TOM_HI, 118, 110, feel=0)
        P(bar, 1560, TOM_MHI, 120, 110, feel=0)
        P(bar, 1680, TOM_MLO, 122, 110, feel=0)
        P(bar, 1800, FLOOR_HI, 124, 130, feel=0)

# ---------------- Latin interlude bars 40-43 : contrasting timbres ----------------
for bar in range(40, 44):
    # son clave 3-2
    for cb in CLAVE_PATT:
        P(bar, cb, CLAVES if bar % 2 == 0 else WOOD_HI, 102, 100, feel=0)
    # conga tumbao + bongos
    P(bar, 0, CONGA_LO, 100, 150)
    P(bar, 240, CONGA_MUTE, 82, 100)
    P(bar, 480, CONGA_OPEN, 98, 150)
    P(bar, 720, CONGA_MUTE, 84, 100)
    P(bar, 960, CONGA_LO, 96, 150)
    P(bar, 1200, CONGA_OPEN, 100, 150)
    P(bar, 1440, CONGA_MUTE, 86, 100)
    P(bar, 1680, CONGA_OPEN, 96, 150)
    # timbale / bongo answers alternate bars
    if bar % 2 == 0:
        P(bar, 360, BONGO_HI, 90, 110)
        P(bar, 840, BONGO_LO, 92, 110)
        P(bar, 1320, TIMB_HI, 94, 130)
        P(bar, 1560, TIMB_LO, 92, 130)
        P(bar, 720, AGOGO_HI, 88, 110)
        P(bar, 1440, AGOGO_LO, 88, 110)
    else:
        P(bar, 360, TIMB_HI, 92, 130)
        P(bar, 600, TIMB_LO, 90, 130)
        P(bar, 1080, BONGO_HI, 90, 110)
        P(bar, 1560, BONGO_LO, 92, 110)
        P(bar, 480, COWBELL, 90, 110)
        P(bar, 1320, COWBELL, 90, 110)
    # feet keep pulse
    for qb in [0, 480, 960, 1440]:
        P(bar, qb, KICK, 84, 120, feel=0)
    for ob in [240, 720, 1200, 1680]:
        P(bar, ob, HAT_PED, 58, 80)
    if bar == 40:
        P(bar, 0, SPLASH, 104, 1000, feel=-4)

# ---------------- Virtuoso bars 44-51 : rudiments, triplets, rolls ----------------
# bar 44-45 paradiddles orchestrated linear (1 note per tick => always playable)
para_seq_44 = [SNARE, RIM, TOM_MHI, SNARE, SNARE, TOM_MLO, SNARE, RIM,
               SNARE, TOM_MHI, RIM, SNARE, SNARE, RIM, TOM_MLO, TOM_LO]
for s, nn in enumerate(para_seq_44):
    v = 112 if s % 4 == 0 else (96 if s % 2 == 0 else 62)
    P(44, s * 120, nn, v, 100, feel=0)
P(44, 0, KICK, 106, 120)
P(44, 960, KICK, 104, 120)

para_seq_45 = [TOM_HI, SNARE, TOM_MHI, TOM_MHI, SNARE, TOM_MLO, SNARE, SNARE,
               FLOOR_HI, SNARE, TOM_MLO, TOM_MLO, SNARE, FLOOR_LO, SNARE, SNARE]
for s, nn in enumerate(para_seq_45):
    v = 114 if s % 4 == 0 else (98 if s % 2 == 0 else 64)
    P(45, s * 120, nn, v, 110, feel=0)
P(45, 0, KICK, 108, 120)
P(45, 1440, KICK, 106, 120)

# bar 46 flam accents
for base in [0, 480, 960, 1440]:
    flam(46, base, SNARE, 122, 120, feel=4)
    P(46, base, KICK, 110, 120, feel=-2)
P(46, 240, HAT_C, 80, 90, feel=-4)
P(46, 720, HAT_C, 82, 90, feel=-4)
P(46, 1200, HAT_C, 84, 90, feel=-4)
P(46, 1680, HAT_C, 86, 90, feel=-4)
P(46, 360, SNARE, 44, 70)
P(46, 1320, SNARE, 46, 70)

# bar 47 triplet tom melody (12 triplet 8ths, 160 ticks)
tri_orch_47 = [FLOOR_LO, TOM_LO, TOM_MLO, TOM_MHI, TOM_HI, TOM_MHI, TOM_MLO, TOM_LO, FLOOR_HI, TOM_MLO, SNARE, RIM]
for i, nn in enumerate(tri_orch_47):
    base = i * 160
    v = 112 if i % 3 == 0 else 100
    P(47, base, nn, v, 130, feel=0)
P(47, 0, KICK, 108, 120)
P(47, 960, KICK, 106, 120)

# bar 48 press / double-stroke roll: 32nd snare roll first 2 beats + groove last 2 beats
for k in range(16):  # 2 beats * 8 32nds (60 ticks)
    base = k * 60
    v = 60 + k * 3
    P(48, base, SNARE, v, 60, feel=0)
P(48, 0, KICK, 108, 120)
P(48, 480, KICK, 106, 120)
P(48, 960, SNARE, 120, 120, feel=6)
P(48, 960, KICK, 110, 120)
P(48, 1200, TOM_MLO, 110, 130)
P(48, 1440, SNARE, 122, 120, feel=6)
P(48, 1440, KICK, 110, 120)
P(48, 1560, SNARE, 50, 70)
P(48, 1680, TOM_HI, 112, 120)
P(48, 1800, TOM_MHI, 114, 120)

# bar 49 sextuplets (6 per beat, 80 ticks) descending then ascending
for k in range(24):
    base = k * 80
    seq = [TOM_HI, TOM_MHI, TOM_MLO, TOM_LO, FLOOR_HI, FLOOR_LO]
    nn = seq[k % 6] if k < 12 else seq[5 - (k % 6)]
    v = 104 + (k % 6) * 3
    P(49, base, nn, v, 90, feel=0)
P(49, 0, KICK, 110, 120)
P(49, 960, CRASH1, 116, 1400, feel=-4)

# bar 50 odd grouping 3+3+2 over 16ths (accents every 3)
accents_50 = [0, 360, 720, 1080, 1440, 1680]
for s in range(16):
    base = s * 120
    if base in accents_50:
        P(50, base, SNARE, 120, 120, feel=4)
        P(50, base, KICK, 108, 120, feel=-2)
    else:
        P(50, base, HAT_C, 66, 80, feel=-4)
        if s % 3 == 1:
            P(50, base, RIM, 48, 70, feel=4)

# bar 51 fill into finale: 16ths + last-beat sextuplets
for s in range(12):
    base = s * 120
    nn = [TOM_LO, TOM_MLO, TOM_MHI, TOM_HI][s % 4]
    P(51, base, nn, 106 + s, 110, feel=0)
for k in range(6):
    base = 1440 + k * 80
    P(51, base, SNARE, 112 + k * 2, 90, feel=4)
P(51, 0, KICK, 110, 120)
P(51, 480, KICK, 108, 120)
P(51, 960, KICK, 110, 120)

# ---------------- Finale build bars 52-57 : motif A ascending + subdivision increase ----------------
asc_toms = [FLOOR_LO, FLOOR_HI, TOM_LO, TOM_MLO, TOM_MHI, TOM_HI]
for bar in range(52, 58):
    idx = bar - 52
    vbase = 96 + idx * 5  # 96..121
    tom = asc_toms[idx]
    # motif rhythm on ascending tom + kick
    for mb in MOTIF:
        P(bar, mb, tom, vbase + 6, 140, feel=-4)
        if mb in (0, 720, 1440):
            P(bar, mb, KICK, vbase + 4, 120, feel=-3)
    # subdivision layer grows
    if idx < 2:
        for base in [0, 480, 960, 1440]:
            P(bar, base, CRASH1 if base == 0 else HAT_C, vbase if base == 0 else vbase - 12, 1400 if base == 0 else 90, feel=-4)
    elif idx < 4:
        for base in [0, 240, 480, 720, 960, 1200, 1440, 1680]:
            nn = CRASH1 if (base == 0 and bar % 2 == 0) else HAT_C
            P(bar, base, nn, vbase if base == 0 else vbase - 8, 1200 if base == 0 else 90, feel=-4)
        P(bar, 480, SNARE, vbase + 8, 120, feel=4)
        P(bar, 1440, SNARE, vbase + 10, 120, feel=4)
    else:
        for s in range(16):
            base = s * 120
            P(bar, base, HAT_C, vbase - 6, 80, feel=-5)
        P(bar, 0, CRASH1, 122, 1500, feel=-4)
        P(bar, 480, SNARE, 122, 120, feel=4)
        P(bar, 1440, SNARE, 124, 120, feel=4)
        P(bar, 840, SNARE, 70, 70)
        P(bar, 1320, SNARE, 74, 70)
    if bar == 57:
        # last beat 32nd snare roll crescendo to outro
        for k in range(8):
            base = 1440 + k * 60
            P(bar, base, SNARE, 100 + k * 3, 60, feel=0)
        P(bar, 1440, KICK, 118, 120)

# ---------------- Outro bars 58-59 : big hit, motif recall, final stinger ----------------
# bar 58 huge downbeat: crash + snare + kick + pedal = 2 hands + 2 feet (playable max)
P(58, 0, CRASH1, 127, 1800, feel=0)
P(58, 0, SNARE, 124, 150, feel=6)
P(58, 0, KICK, 127, 150, feel=0)
P(58, 0, HAT_PED, 70, 100, feel=0)
# silence .. then soft recall fragment
P(58, 960, RIM, 70, 90, feel=8)
P(58, 1200, WOOD_LO, 66, 90, feel=8)
P(58, 1440, TOM_MLO, 72, 140, feel=8)
P(58, 1680, RIM, 64, 80, feel=8)
P(58, 1800, TRI_O, 60, 600, feel=8)

# bar 59 final motif A whisper then stinger on beat 4
P(59, 0, FLOOR_LO, 78, 160, feel=8)
P(59, 360, RIM, 66, 90, feel=8)
P(59, 720, TOM_LO, 80, 140, feel=8)
# final stinger at beat 4 (1440): crash + kick + snare + pedal
P(59, 1440, CRASH1, 127, 2200, feel=0)
P(59, 1440, CRASH2, 120, 2200, feel=0)  # would be 3 hands with snare -> filter will keep musical subset
P(59, 1440, KICK, 127, 150, feel=0)
P(59, 1440, SNARE, 126, 150, feel=6)
P(59, 1440, HAT_PED, 70, 100, feel=0)
P(59, 1440, TRI_O, 90, 1800, feel=0)
# let ring: a soft triangle ping after for decay tail
P(59, 1680, TRI_M, 50, 900, feel=0)

# ---------------- enforce playability: dedup + max 2 hands + 2 feet (<=4) ----------------
FOOT = {KICK2, KICK, HAT_PED}
dedup = {}
for tick, note, vel, dur in hits:
    key = (tick, note)
    if key not in dedup or vel > dedup[key][2] or (vel == dedup[key][2] and dur > dedup[key][3]):
        dedup[key] = (tick, note, vel, dur)
hits = list(dedup.values())

grouped = defaultdict(list)
for h in hits:
    grouped[h[0]].append(h)

final_hits = []
for tick in sorted(grouped.keys()):
    lst = grouped[tick]
    if len(lst) <= 4:
        hands = [x for x in lst if x[1] not in FOOT]
        feet = [x for x in lst if x[1] in FOOT]
        if len(hands) > 2:
            hands = sorted(hands, key=lambda x: -x[2])[:2]
        if len(feet) > 2:
            feet = sorted(feet, key=lambda x: -x[2])[:2]
        # if still >4 (2+2=4 max) fine
        kept = hands + feet
        # if originally <=4 but hands trimmed, kept < original (good)
        final_hits.extend(kept)
    else:
        hands = sorted([x for x in lst if x[1] not in FOOT], key=lambda x: -x[2])[:2]
        feet = sorted([x for x in lst if x[1] in FOOT], key=lambda x: -x[2])[:2]
        final_hits.extend(hands + feet)
# deterministic order
final_hits.sort(key=lambda x: (x[0], x[1], -x[2]))

# ---------------- write MIDI ----------------
events = []  # (tick, order, note, vel) order 0=off,1=on
for tick, note, vel, dur in final_hits:
    off = tick + dur
    events.append((tick, 1, note, vel, dur))
    events.append((off, 0, note, 0, 0))
events.sort(key=lambda e: (e[0], e[1], e[2]))

mid = MidiFile(ticks_per_beat=TPB, type=1)
track = MidiTrack()
mid.tracks.append(track)
track.append(MetaMessage('track_name', name='Drum Solo', time=0))
track.append(MetaMessage('set_tempo', tempo=TEMPO, time=0))
track.append(MetaMessage('time_signature', numerator=4, denominator=4, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))

last = 0
for tick, order, note, vel, _ in events:
    delta = tick - last
    last = tick
    if order == 1:
        track.append(Message('note_on', channel=CHANNEL, note=note, velocity=vel, time=delta))
    else:
        track.append(Message('note_off', channel=CHANNEL, note=note, velocity=0, time=delta))

track.append(MetaMessage('end_of_track', time=0))
mid.save('solo.mid')
