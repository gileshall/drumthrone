#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drum_solo.py  --  writes  solo.mid : a two-minute General MIDI drum solo.

Everything is sounded on MIDI channel 10 (0-based channel 9) and is written for
ONE drummer: at any instant at most two hands and two feet are striking, and no
single hand or foot is asked to strike twice inside a 16th note (the fastest
sensible repeat for one limb).  Limbs are assigned explicitly and the result is
verified before the file is written.

FORM -- 60 bars of 4/4 at 120 bpm = 2:00.000 exactly
    bars  1- 4  Intro     the motif bare: side stick, wood blocks, pedal hi-hat
    bars  5-12  A         the motif stated on the kit, swing ride answers
    bars 13-20  A'        developed: ghost 16ths, displaced accents, 32nd pairs
    bars 21-28  B         contrast: linear playing, cowbell / timbale / bongo
    bars 29-36  Build     one cell repeated: density, volume and speed rising
    bars 37-40  Climax I  full kit ... then a hard stop
    bars 41-46  Whisper   pedal hat, claves, wood blocks, cuica, shaker
    bars 47-52  Rebuild   the motif back in the toms, 32nd doubles, crescendo
    bars 53-58  Climax II the summit: crashes, double kick, triplet flams
    bars 59-60  Coda      the opening motif recalled bare, one last unison hit

MOTIFS
    A  (call)     BOOM- . -TAK . TUM- -TUM . .        kick / snare / tom descent
    A' (answer)   the same cell reversed, run upwards  floor tom -> high tom
    B             linear cell: cowbell - kick - snare - tom, one limb at a time
    The intro and the coda state A bare (side stick and wood blocks), so the
    solo opens and closes with the same tune.

FEEL -- placement is deliberate, never random (the script uses no random data,
so the file is byte-identical on every run):
  * swing   the 8th offbeat sits between 53.5% and 64.5% of the beat.  The
            shuffle is widest in the quiet, sparse passages and straightens out
            as the playing gets dense and loud - what a drummer really does.
  * push / lay back   every section carries a constant offset in front of or
            behind the beat (intro and coda +14 ms, build and climaxes -8/-12 ms).
  * micro timing   each voice keeps a fixed few-millisecond fingerprint: the
            kick a touch early, the snare and floor toms a touch late, the
            cowbell and timbales early so they cut, cymbals just before the beat.

Usage:   python drum_solo.py        (writes ./solo.mid)
"""

import sys
from collections import Counter
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

# --------------------------------------------------------------------------
#  parameters
# --------------------------------------------------------------------------
BPM          = 120
TPB          = 480              # ticks per quarter note
UPB          = 24               # composition units per beat
                                #   12 = 8th   6 = 16th   3 = 32nd
                                #    8 = 8th-triplet   4 = 16th-triplet
BAR_UNITS    = 4 * UPB          # 96 units per bar
BARS         = 60               # 60 bars * 4 beats / 120 bpm = 120.000 s
END_TICKS    = BARS * 4 * TPB   # 115200 ticks = 120.000 s
MIDI_CH      = 9                # General MIDI channel 10 (0-based 9)
MIN_LIMB_GAP = 6                # units = one 16th note
WINDOW       = 20               # ticks used by the "any instant" test

# --------------------------------------------------------------------------
#  General MIDI percussion:  name, hand/foot, ring (beats), micro timing (ticks)
# --------------------------------------------------------------------------
PERC = {
    35: ("Acoustic Bass Drum", 'F', 1.0, -5),
    36: ("Bass Drum 1",        'F', 1.0, -5),
    37: ("Side Stick",         'H', 0.5,  4),
    38: ("Acoustic Snare",     'H', 1.0,  3),
    41: ("Low Floor Tom",      'H', 2.0,  5),
    42: ("Closed Hi-Hat",      'H', 0.5,  1),
    43: ("High Floor Tom",     'H', 2.0,  4),
    44: ("Pedal Hi-Hat",       'F', 0.5,  2),
    45: ("Low Tom",            'H', 2.0,  4),
    46: ("Open Hi-Hat",        'H', 1.5,  0),
    47: ("Low-Mid Tom",        'H', 2.0,  3),
    48: ("Hi-Mid Tom",         'H', 2.0,  3),
    49: ("Crash Cymbal 1",     'H', 6.0, -2),
    50: ("High Tom",           'H', 2.0,  2),
    51: ("Ride Cymbal 1",      'H', 3.0,  1),
    52: ("Chinese Cymbal",     'H', 6.0, -3),
    53: ("Ride Bell",          'H', 3.0,  0),
    55: ("Splash Cymbal",      'H', 4.0, -2),
    56: ("Cowbell",            'H', 0.7, -3),
    57: ("Crash Cymbal 2",     'H', 6.0, -2),
    58: ("Vibraslap",          'H', 3.0,  0),
    60: ("Hi Bongo",           'H', 0.6,  2),
    61: ("Low Bongo",          'H', 0.6,  3),
    63: ("Open Hi Conga",      'H', 1.2,  2),
    65: ("High Timbale",       'H', 1.5, -2),
    66: ("Low Timbale",        'H', 1.5, -1),
    67: ("High Agogo",         'H', 0.7, -2),
    68: ("Low Agogo",          'H', 0.7, -1),
    69: ("Cabasa",             'H', 0.4,  1),
    70: ("Maracas",            'H', 0.4,  1),
    75: ("Claves",             'H', 0.4,  0),
    76: ("Hi Wood Block",      'H', 0.4,  0),
    77: ("Low Wood Block",     'H', 0.4,  1),
    78: ("Mute Cuica",         'H', 0.5,  1),
    79: ("Open Cuica",         'H', 1.0,  1),
    80: ("Mute Triangle",      'H', 2.0,  0),
    81: ("Open Triangle",      'H', 6.0,  0),
}

MICRO = dict((n, PERC[n][3]) for n in PERC)     # fixed voice fingerprints (ticks)

POOL = {'H': ('HR', 'HL'), 'F': ('FR', 'FL')}
PREF = {35: ('FR', 'FL'), 36: ('FR', 'FL'), 44: ('FL', 'FR')}

# --------------------------------------------------------------------------
#  note aliases
# --------------------------------------------------------------------------
K, K2, RS, SN = 36, 35, 37, 38           # bass drum, deep bass drum, side stick, snare
F1, F2 = 41, 43                          # low floor tom, high floor tom
T1, T2, T3, T4 = 45, 47, 48, 50          # low, low-mid, hi-mid, high tom
HC, HO, HP = 42, 46, 44                  # closed hat, open hat, pedal hat
C1, C2, CN, SP = 49, 57, 52, 55          # crash 1, crash 2, china, splash
RD, RB = 51, 53                          # ride, ride bell
CB, VS = 56, 58                          # cowbell, vibraslap
BH, BL = 60, 61                          # bongos
CG = 63                                  # open hi conga
TH, TL = 65, 66                          # timbales
AH, AL = 67, 68                          # agogo
CA, MA = 69, 70                          # cabasa, maracas
CV = 75                                  # claves
WH, WL = 76, 77                          # wood blocks
MU, OU = 78, 79                          # cuica
TM, TO = 80, 81                          # triangles

# --------------------------------------------------------------------------
#  THE SOLO -- one entry per bar:  (unit, note, velocity)
#  unit 0..95, 24 per beat.   A 4th field 'H'/'F' may force the limb class.
# --------------------------------------------------------------------------
SPEC = [
# ---------------- bars 1-4   INTRO : motif A bare ------------------------
[(0,K2,52),(0,RS,54),(6,SN,24),(12,SN,28),(24,WH,58),(24,HP,42),(36,SN,24),
 (48,WL,62),(66,K2,44),(72,HP,40),(84,SN,22)],                                    # 1
[(0,K2,54),(6,SN,22),(12,RS,56),(24,WL,56),(24,HP,42),(36,WH,60),(48,RS,58),
 (54,SN,22),(72,WH,56),(72,HP,40),(84,WL,54)],                                    # 2
[(0,K,78),(0,SN,30),(6,SN,26),(12,SN,32),(24,T4,72),(24,HP,44),(36,SN,26),
 (48,T2,76),(66,F2,70),(72,K,58),(72,HP,44),(84,SN,24)],                          # 3
[(0,K,80),(6,SN,26),(12,SN,74),(24,F1,74),(24,HP,46),(30,T1,48),(36,T3,78),
 (48,SN,82),(54,SN,26),(60,K,66),(72,T4,76),(72,HP,46),(78,SN,26),(84,T2,72),
 (90,F2,68)],                                                                      # 4

# ---------------- bars 5-12  A : motif on the kit, ride answers ----------
[(0,K,100),(0,SN,38),(6,SN,30),(12,SN,34),(24,T4,90),(24,HP,52),(36,SN,32),
 (48,T2,94),(66,F2,88),(72,K,62),(72,HP,50),(84,SN,30),(90,SN,28)],               # 5  call
[(0,RD,84),(0,K,92),(12,SN,32),(24,RD,78),(24,HP,52),(36,RD,72),(48,SN,88),
 (48,K,82),(54,SN,30),(60,K,60),(72,RD,80),(72,HP,52),(84,RD,74),(90,SN,32)],     # 6  answer
[(0,K,102),(0,SN,38),(6,SN,28),(12,SN,34),(18,SN,28),(24,T4,92),(24,HP,52),
 (30,SN,30),(36,SN,34),(48,T2,94),(48,K,66),(54,SN,28),(66,F2,88),(72,HP,50),
 (78,SN,28),(84,SN,32),(90,SN,30)],                                                # 7  call + ghosts
[(0,RD,86),(0,K,94),(12,SN,32),(24,RD,78),(24,HP,52),(36,SN,86),(48,RD,74),
 (54,SN,32),(60,K,70),(66,T4,84),(72,T2,88),(72,HP,50),(72,K,76),(78,F2,86),
 (84,SN,90),(90,SN,34)],                                                           # 8  answer + fill
[(0,K,106),(0,SN,86),(6,SN,32),(12,T4,86),(18,T2,80),(24,F1,96),(24,HP,54),
 (30,SN,32),(36,SN,36),(42,K,74),(48,T4,98),(54,T2,82),(60,SN,90),(66,K,80),
 (72,F2,94),(72,HP,52),(78,SN,30),(84,SN,34),(90,K,64)],                          # 9  call, descending
[(0,RD,88),(0,K,102),(12,SN,34),(18,SN,30),(24,RD,80),(24,HP,54),(30,SN,32),
 (36,RD,74),(42,K,68),(48,SN,94),(48,K,88),(54,SN,32),(60,T4,88),(66,T2,84),
 (72,F1,92),(72,HP,54),(72,K,72),(78,SN,30),(84,SN,84),(90,SN,34)],               # 10 answer, ascending
[(0,K,100),(0,SN,36),(6,SN,32),(12,T4,88),(18,SN,32),(24,T2,92),(24,HP,54),
 (30,SN,34),(36,SN,38),(42,K,74),(48,F2,96),(54,SN,34),(60,SN,90),(66,K,78),
 (72,T4,92),(72,HP,52),(78,T2,86),(84,F2,90),(90,SN,94)],                         # 11
[(0,K,106),(0,SN,94),(6,SN,36),(12,SN,32),(18,T4,92),(24,T2,94),(24,HP,54),
 (30,F2,90),(36,SN,38),(42,K,82),(48,SN,98),(54,T4,94),(60,T2,96),(66,F2,98),
 (72,F1,100),(72,K,86),(72,HP,54),(78,SN,92),(84,SN,40),(90,SN,34),(90,K,78)],    # 12 fill

# ---------------- bars 13-20  A' : developed, displaced, pushing ----------
[(0,C1,116),(0,K,110),(6,SN,34),(12,SN,38),(18,K,76),(24,T4,96),(24,HP,54),
 (30,SN,34),(36,T2,98),(42,SN,34),(48,F1,100),(48,K,82),(54,SN,36),(60,SN,94),
 (66,SN,34),(72,T4,96),(72,HP,52),(78,SN,34),(84,T2,92),(90,K,76)],               # 13
[(0,RD,86),(0,K,100),(12,SN,36),(24,RD,78),(24,HP,54),(36,SN,92),(42,SN,32),
 (48,RD,76),(48,K,92),(54,SN,34),(60,K,70),(66,SN,36),(72,RD,82),(72,HP,54),
 (78,SN,88),(84,SN,34),(90,K,80)],                                                # 14
[(0,K,106),(0,SN,38),(6,SN,32),(12,T4,98),(18,T2,92),(24,F1,104),(24,HP,54),
 (30,K,78),(36,SN,96),(42,SN,34),(48,HO,100),(48,K,90),(54,SN,34),(60,T4,94),
 (66,SN,36),(72,T2,98),(72,HP,52),(78,SN,34),(84,F2,96),(90,SN,100)],             # 15
[(0,K,110),(0,SN,100),(6,SN,36),(12,T4,96),(18,K,82),(24,T2,98),(24,HP,54),
 (30,SN,38),(36,F2,100),(42,K,86),(48,SN,102),(54,T4,94),(60,SN,38),(66,T2,96),
 (72,F1,100),(72,K,88),(72,HP,52),(78,SN,36),(84,SN,98),(90,SN,40)],              # 16
[(0,C2,114),(0,K,112),(6,SN,34),(12,SN,38),(18,T4,92),(24,T4,98),(24,HP,54),
 (30,T2,90),(36,T2,96),(42,SN,36),(48,F2,102),(48,K,88),(54,SN,34),(60,SN,96),
 (66,K,84),(72,F1,100),(72,HP,52),(78,SN,34),(84,SN,94),(90,K,82)],               # 17
[(0,K,108),(0,SN,40),(6,SN,32),(12,SN,96),(18,SN,36),(24,T4,100),(24,HP,54),
 (30,SN,34),(36,SN,38),(42,K,84),(48,T2,102),(54,SN,36),(60,F2,100),(66,K,88),
 (72,F1,104),(72,HP,54),(78,SN,40),(81,T4,88),(84,SN,96),(87,T2,92),
 (90,SN,104)],                                                                    # 18 32nd pair
[(0,SN,44),(6,K,88),(12,SN,102),(18,T4,94),(24,SN,40),(24,HP,54),(30,K,82),
 (36,SN,104),(42,T2,96),(48,SN,42),(48,K,90),(54,SN,40),(60,SN,106),(66,F2,98),
 (72,SN,42),(72,HP,54),(78,K,86),(84,SN,108),(90,T4,100)],                        # 19 accents on the &s

# ---------------- bars 21-28  B : linear, Latin colour, laid back --------
[(0,CB,98),(6,K,86),(12,SN,34),(18,T4,84),(24,K,94),(24,HP,44),(30,SN,92),
 (36,CB,60),(48,T2,88),(54,K,82),(60,SN,34),(66,F1,86),(72,CB,96),(72,HP,44),
 (78,K,86),(84,SN,94),(90,T4,82)],                                                # 20 motif B
[(0,TH,96),(6,K,84),(12,SN,36),(18,TL,84),(24,K,92),(24,HP,44),(30,SN,90),
 (36,CB,58),(42,SN,34),(48,T2,90),(54,K,80),(60,TH,88),(66,F1,84),(72,CB,96),
 (72,HP,44),(78,K,84),(84,SN,92),(90,TL,80)],                                     # 21 on timbales
[(0,CB,98),(6,K,84),(12,SN,36),(18,T4,86),(24,K,94),(24,HP,46),(30,SN,92),
 (36,AH,62),(42,SN,34),(48,T2,90),(54,K,82),(60,SN,34),(66,F1,88),(72,CB,96),
 (72,HP,46),(78,K,84),(84,SN,94),(90,AL,78)],                                     # 22 agogo colour
[(0,CB,100),(3,SN,40),(6,K,88),(9,SN,36),(12,T4,88),(18,K,82),(24,SN,94),
 (24,HP,46),(30,CB,62),(36,T2,90),(42,K,84),(48,SN,96),(54,SN,38),(60,F2,92),
 (66,K,86),(72,CB,98),(72,HP,46),(78,SN,40),(84,SN,96),(90,T4,88)],               # 23 compressed
[(0,CB,102),(6,K,88),(12,SN,40),(18,BL,82),(24,K,96),(24,HP,48),(30,SN,94),
 (36,CB,64),(42,BH,84),(48,T2,92),(54,K,84),(60,SN,40),(66,F1,90),(72,CB,100),
 (72,HP,48),(78,K,86),(84,SN,96),(90,BH,86)],                                     # 24 bongos
[(0,TH,102),(4,TL,88),(8,K,90),(12,SN,42),(18,TH,90),(24,K,98),(24,HP,48),
 (30,SN,96),(36,CB,66),(42,TL,88),(48,T2,94),(54,K,86),(60,SN,42),(66,F1,92),
 (72,CB,102),(72,HP,48),(76,SN,44),(82,CG,88),(86,SN,98),(92,TL,90)],             # 25 timbale flurries
[(0,CB,104),(3,SN,44),(6,K,94),(9,SN,40),(12,T4,92),(15,SN,42),(18,K,88),
 (21,T2,90),(24,SN,98),(24,HP,50),(30,CB,68),(33,SN,44),(36,F2,94),(42,K,90),
 (45,SN,46),(48,SN,100),(54,T4,94),(57,SN,44),(60,T2,96),(66,K,92),(69,SN,46),
 (72,F1,100),(72,HP,50),(78,SN,48),(81,T4,96),(84,SN,102),(87,T2,98),
 (90,SN,104),(93,K,96)],                                                          # 26 chatter
[(0,CB,106),(3,SN,46),(6,K,96),(9,SN,42),(12,T4,96),(18,K,92),(24,SN,100),
 (24,HP,52),(30,T2,96),(36,F2,98),(42,K,94),(48,SN,104),(51,T4,92),(54,SN,46),
 (57,T2,94),(60,F2,98),(63,SN,48),(66,K,96),(72,F1,104),(72,HP,52),(75,SN,50),
 (78,T4,98),(81,T2,100),(84,F2,102),(87,SN,52),(90,F1,104),(93,K,100)],           # 27 fill

# ---------------- bars 29-36  BUILD : one cell, denser and louder --------
[(0,SN,78),(0,K,92),(12,SN,34),(24,SN,82),(24,HP,46),(36,SN,34),(42,K,68),
 (48,SN,84),(60,SN,34),(66,K,72),(72,SN,86),(72,HP,46),(84,SN,34),(90,SN,32)],    # 28
[(0,SN,82),(0,K,94),(6,SN,30),(12,SN,36),(18,SN,30),(24,SN,86),(24,HP,46),
 (30,SN,32),(36,T4,74),(42,SN,32),(42,K,72),(48,SN,88),(54,SN,32),(60,T2,76),
 (66,SN,32),(72,SN,90),(72,HP,46),(78,SN,32),(84,F2,78),(90,SN,34)],              # 29
[(0,SN,44),(0,K,96),(3,SN,36),(6,SN,34),(9,SN,36),(12,T4,82),(15,SN,36),
 (18,SN,34),(18,K,74),(21,T2,80),(24,SN,92),(24,HP,48),(27,SN,36),(30,SN,34),
 (33,F2,82),(36,SN,90),(39,SN,36),(42,SN,34),(42,K,78),(45,T4,84),(48,SN,94),
 (48,K,88),(51,SN,36),(54,SN,34),(57,T2,86),(60,SN,92),(63,SN,36),(66,SN,34),
 (66,K,82),(69,F2,88),(72,SN,96),(72,HP,48),(75,SN,38),(78,SN,36),(81,F1,90),
 (84,SN,98),(87,SN,38),(90,SN,94),(93,K,86)],                                     # 30 32nd chatter
[(0,SN,46),(0,K,98),(3,SN,38),(6,T4,86),(9,SN,38),(12,SN,44),(15,SN,38),
 (18,T2,88),(18,K,80),(21,SN,38),(24,SN,96),(24,HP,50),(27,SN,38),(30,F2,90),
 (33,SN,38),(36,SN,44),(39,SN,38),(42,F1,92),(42,K,84),(45,SN,38),(48,SN,100),
 (48,K,94),(51,SN,38),(54,T4,92),(57,SN,38),(60,SN,46),(63,SN,38),(66,T2,94),
 (66,K,86),(69,SN,38),(72,SN,102),(72,HP,50),(75,SN,38),(78,F2,96),(81,SN,38),
 (84,SN,48),(87,SN,40),(90,F1,98),(93,K,90)],                                     # 31
[(0,C1,112),(0,K,104),(3,SN,46),(6,SN,38),(9,SN,40),(12,T4,92),(15,SN,38),
 (18,SN,36),(18,K,82),(21,T2,92),(24,SN,104),(24,HP,52),(27,SN,38),(30,SN,36),
 (33,F2,94),(36,SN,100),(39,SN,38),(42,SN,36),(42,K,86),(45,T4,96),(48,SN,106),
 (48,K,96),(51,SN,38),(54,SN,36),(57,T2,98),(60,SN,102),(63,SN,38),(66,SN,36),
 (66,K,90),(69,F2,100),(72,SN,108),(72,HP,52),(75,SN,40),(78,SN,38),(81,F1,102),
 (84,SN,110),(87,SN,42),(90,SN,104),(93,K,98)],                                   # 32 forte
[(0,SN,52),(0,K,102),(4,SN,46),(8,T4,96),(12,SN,50),(16,SN,46),(20,T2,98),
 (24,SN,106),(24,HP,54),(28,SN,48),(32,F2,100),(36,SN,52),(40,SN,48),(44,F1,102),
 (48,SN,110),(48,K,98),(52,SN,48),(56,T4,102),(60,SN,54),(64,SN,50),(68,T2,104),
 (72,SN,112),(72,HP,54),(76,SN,50),(80,F2,106),(84,SN,54),(88,SN,50),
 (92,F1,108)],                                                                    # 33 16th-triplets
[(0,C2,118),(0,K,108),(3,SN,54),(6,T4,100),(9,SN,42),(12,SN,108),(15,SN,42),
 (18,T2,102),(18,K,88),(21,SN,42),(24,F2,104),(24,HP,56),(27,SN,42),(30,SN,106),
 (33,SN,44),(36,F1,108),(39,SN,44),(42,SN,110),(42,K,92),(45,SN,44),(48,T4,106),
 (48,K,100),(51,SN,44),(54,T2,108),(57,SN,44),(60,F2,110),(63,SN,46),(66,F1,112),
 (66,K,94),(69,SN,46),(72,SN,114),(72,HP,56),(75,SN,46),(78,T4,108),(81,SN,46),
 (84,T2,110),(87,SN,46),(90,F2,112),(93,F1,114),(93,K,100)],                      # 34
[(0,SN,114),(0,K,106),(3,SN,48),(6,T4,104),(9,SN,48),(12,T2,106),(15,SN,50),
 (18,F2,108),(18,K,98),(21,SN,50),(24,F1,110),(24,HP,58),(27,SN,52),(30,SN,114),
 (33,T4,104),(36,T2,106),(39,F2,108),(42,F1,110),(42,K,102),(45,SN,54),
 (48,SN,116),(54,SN,50),(60,SN,118),(66,SN,52),(72,T4,110),(72,K,106),(72,HP,58),
 (78,T2,112),(84,F2,114),(87,SN,54),(90,F1,116),(93,K,108)],                      # 35 fill

# ---------------- bars 37-40  CLIMAX I : full power, then a hard stop ----
[(0,C1,124),(0,K,118),(0,F1,108),(6,SN,52),(12,SN,52),(18,K,92),(24,SN,118),
 (24,HP,60),(30,SN,52),(36,T4,110),(42,K,96),(48,T2,114),(48,K,108),(54,SN,54),
 (60,F2,116),(66,K,100),(72,F1,118),(72,HP,60),(78,SN,54),(84,SN,114),
 (90,K,104)],                                                                     # 36
[(0,CN,120),(0,K,112),(3,SN,52),(6,K,84),(9,SN,50),(12,T4,112),(15,SN,50),
 (18,K,88),(21,T2,112),(24,F2,116),(24,HP,60),(27,SN,52),(30,K,90),(33,F1,116),
 (36,SN,118),(39,SN,52),(42,K,92),(45,T4,112),(48,T2,114),(48,K,108),(51,SN,54),
 (54,K,94),(57,F2,116),(60,SN,120),(63,SN,54),(66,K,96),(69,F1,118),(72,SN,122),
 (72,HP,60),(75,SN,54),(78,K,98),(81,T4,114),(84,T2,116),(87,F2,118),(90,F1,120),
 (93,K,104)],                                                                     # 37 double kick
[(0,RB,118),(0,K,112),(6,SN,54),(12,SN,50),(18,K,90),(24,RB,112),(24,SN,118),
 (24,HP,60),(30,SN,54),(36,SN,50),(42,K,92),(48,RB,114),(48,K,108),(54,SN,54),
 (60,T4,112),(66,K,94),(72,RB,116),(72,HP,60),(78,SN,56),(84,SN,116),(88,SN,56),
 (92,K,100)],                                                                     # 38 shouting
[(0,C2,122),(0,K,116),(0,SN,56),(6,SN,48),(12,T4,114),(18,T2,116),(24,F2,118),
 (24,HP,60),(30,F1,120),(36,SN,122),(42,K,104),(48,SN,58),(51,T4,112),(54,SN,58),
 (57,T2,114),(60,SN,58),(63,F2,116),(66,SN,58),(72,CN,126),(72,F1,122),
 (72,K,118)],                                                                     # 39 stop

# ---------------- bars 41-46  WHISPER : everything small -----------------
[(0,K2,50),(24,HP,42),(48,RS,46),(72,HP,40)],                                     # 40
[(0,K2,52),(0,RS,52),(6,SN,22),(12,SN,24),(24,WH,58),(24,HP,42),(36,SN,22),
 (48,WL,60),(66,K2,44),(72,HP,40),(84,SN,22)],                                    # 41 motif A bare
[(0,CV,62),(12,MU,48),(24,CV,58),(24,HP,42),(36,SN,22),(48,OU,54),(60,CV,56),
 (72,K2,46),(72,HP,40),(84,CV,54)],                                               # 42 claves / cuica
[(0,CA,56),(0,K2,48),(6,MA,36),(12,RS,60),(18,MA,34),(24,CA,52),(24,HP,42),
 (30,MA,34),(36,SN,24),(42,MA,34),(48,WH,58),(54,MA,36),(60,SN,24),(66,K2,46),
 (72,CA,52),(72,HP,40),(78,MA,34),(84,RS,56),(90,MA,34)],                         # 43 shaker texture
[(0,K2,56),(0,RS,58),(0,SP,44),(6,SN,24),(12,SN,28),(18,WH,54),(24,WL,62),
 (24,HP,44),(30,SN,26),(36,SN,30),(42,K2,50),(48,T4,70),(54,SN,28),(60,T2,72),
 (66,K2,54),(72,F2,74),(72,HP,44),(78,SN,30),(84,SN,34),(90,F1,76)],              # 44 kit returns
[(0,HC,60),(0,K,64),(6,SN,28),(12,HC,56),(18,SN,30),(24,HC,62),(24,HP,46),
 (24,K,56),(30,SN,32),(36,HC,58),(42,SN,34),(48,HO,70),(48,K,68),(54,SN,36),
 (60,HC,62),(66,SN,40),(72,T4,84),(72,HP,48),(78,SN,44),(84,T2,88),(88,SN,46),
 (90,F2,92)],                                                                     # 45 crescendo

# ---------------- bars 47-52  REBUILD : motif in the toms, doubles -------
[(0,VS,88),(0,K,84),(12,SN,40),(24,T4,84),(24,HP,50),(36,SN,40),(48,T2,88),
 (60,SN,40),(66,K,72),(72,F2,88),(72,HP,50),(84,SN,40),(90,SN,36)],               # 46
[(0,K,92),(0,SN,44),(6,SN,36),(12,SN,44),(18,T4,88),(24,T2,90),(24,HP,52),
 (30,SN,38),(36,SN,46),(42,K,76),(48,F2,94),(54,SN,38),(60,SN,92),(66,K,80),
 (72,F1,96),(72,HP,52),(78,SN,40),(84,SN,48),(90,SN,42)],                         # 47
[(0,SN,96),(0,K,96),(3,SN,44),(6,SN,46),(9,SN,44),(12,T4,94),(15,SN,44),
 (18,K,80),(21,T2,94),(24,SN,100),(24,HP,54),(27,SN,44),(30,SN,46),(33,SN,44),
 (36,F2,96),(39,SN,44),(42,K,84),(45,F1,96),(48,SN,104),(48,K,92),(51,SN,46),
 (54,SN,48),(57,SN,46),(60,T4,98),(63,SN,46),(66,K,86),(69,T2,98),(72,SN,108),
 (72,HP,54),(75,SN,46),(78,SN,48),(81,SN,46),(84,F2,100),(87,SN,46),(90,F1,102),
 (93,K,92)],                                                                      # 48 doubles
[(0,C1,118),(0,K,104),(0,F1,100),(6,SN,48),(12,SN,50),(18,K,84),(24,SN,106),
 (24,HP,56),(30,SN,48),(36,T4,102),(42,SN,50),(48,T2,106),(48,K,96),(54,SN,50),
 (60,F2,108),(66,K,88),(72,F1,110),(72,HP,56),(78,SN,52),(84,SN,112),(90,K,92)],  # 49
[(0,SN,54),(0,K,100),(4,SN,50),(8,T4,104),(12,SN,54),(16,SN,50),(20,T2,106),
 (24,SN,112),(24,HP,58),(28,SN,52),(32,F2,108),(36,SN,54),(40,SN,52),(44,F1,110),
 (48,SN,114),(48,K,104),(52,SN,52),(56,T4,108),(60,SN,56),(64,SN,54),(68,T2,112),
 (72,SN,118),(72,HP,58),(76,SN,54),(80,F2,114),(84,SN,56),(88,SN,54),
 (92,F1,116)],                                                                    # 50 triplets
[(0,SN,118),(0,K,108),(3,SN,56),(6,T4,110),(9,SN,56),(12,T2,112),(15,SN,58),
 (18,F2,114),(18,K,96),(21,SN,58),(24,F1,116),(24,HP,60),(27,SN,58),(30,SN,120),
 (33,T4,112),(36,T2,114),(39,F2,116),(42,F1,118),(42,K,100),(45,SN,60),
 (48,SN,122),(54,SN,56),(60,SN,124),(66,SN,58),(72,T4,114),(72,K,108),(72,HP,60),
 (78,T2,116),(84,F2,118),(87,SN,60),(90,F1,120),(93,K,112)],                      # 51 fill

# ---------------- bars 53-58  CLIMAX II : the summit --------------------
[(0,C1,126),(0,K,120),(0,F1,112),(6,SN,58),(12,SN,56),(18,K,96),(24,T4,116),
 (24,HP,62),(30,SN,58),(36,T2,118),(42,K,100),(48,F2,120),(48,K,114),(54,SN,60),
 (60,F1,122),(66,K,104),(72,SN,120),(72,HP,62),(78,SN,58),(84,T4,116),
 (90,K,106)],                                                                     # 52 motif A, full power
[(0,CN,122),(0,K,118),(3,SN,58),(6,K,92),(9,SN,56),(12,T4,116),(15,SN,56),
 (18,K,94),(21,T2,118),(24,F2,120),(24,HP,62),(27,SN,58),(30,K,96),(33,F1,122),
 (36,SN,122),(39,SN,58),(42,K,98),(45,T4,118),(48,T2,120),(48,K,114),(51,SN,58),
 (54,K,98),(57,F2,122),(60,SN,124),(63,SN,58),(66,K,100),(69,F1,124),(72,SN,126),
 (72,HP,62),(75,SN,60),(78,K,102),(81,T4,120),(84,T2,122),(87,F2,124),(90,F1,126),
 (93,K,112)],                                                                     # 53
[(0,RB,122),(0,K,118),(6,SN,60),(12,SN,56),(18,K,96),(24,RB,116),(24,SN,122),
 (24,HP,62),(30,SN,60),(36,SN,56),(42,K,98),(48,RB,120),(48,K,116),(54,SN,60),
 (60,T4,118),(66,K,100),(72,RB,122),(72,HP,62),(78,SN,62),(84,SN,124),(88,SN,60),
 (92,K,104)],                                                                     # 54
[(0,C2,126),(0,K,120),(4,SN,56),(8,T4,118),(12,SN,120),(12,K,100),(16,SN,56),
 (20,T2,120),(24,F2,122),(24,HP,62),(24,K,112),(28,SN,56),(32,F1,124),(36,SN,122),
 (36,K,104),(40,SN,56),(44,T4,120),(48,T2,124),(48,K,118),(52,SN,56),(56,F2,124),
 (60,SN,124),(60,K,104),(64,SN,56),(68,F1,126),(72,SN,126),(72,HP,62),(72,K,118),
 (76,SN,56),(80,T4,122),(84,SN,124),(84,K,106),(88,SN,56),(92,F2,126)],           # 55 triplet flams
[(0,SN,126),(0,K,122),(3,SN,60),(6,T4,122),(9,SN,60),(12,T2,124),(15,SN,60),
 (18,F2,126),(18,K,104),(21,SN,60),(24,F1,127),(24,HP,62),(27,SN,60),(30,SN,124),
 (33,T4,120),(36,T2,122),(39,F2,124),(42,F1,126),(42,K,108),(45,SN,62),
 (48,SN,126),(48,K,124),(51,SN,62),(54,T4,122),(57,SN,62),(60,T2,124),(63,SN,62),
 (66,F2,126),(66,K,110),(69,SN,62),(72,F1,127),(72,HP,62),(75,SN,62),(78,T4,124),
 (81,T2,126),(84,F2,127),(87,SN,64),(90,F1,127),(93,K,124)],                      # 56 the descent
[(0,C2,127),(0,K,124),(0,F1,120),(12,SN,122),(12,K,116),(24,T4,124),(24,HP,64),
 (24,K,112),(36,SN,124),(36,K,116),(48,T2,126),(48,K,120),(54,SN,60),(60,F2,124),
 (66,SN,62),(72,F1,126),(72,K,122),(72,HP,64),(76,SN,62),(80,T4,124),(84,SN,64),
 (88,T2,126),(92,F2,127)],                                                        # 57 unison stabs

# ---------------- bars 59-60  CODA : the opening motif, one last hit -----
[(0,K2,54),(0,RS,54),(6,SN,24),(12,SN,26),(24,WH,52),(24,HP,40),(36,SN,22),
 (48,WL,54),(60,SN,22),(66,K2,44),(72,HP,38),(84,SN,22),(90,SN,20)],             # 58
[(0,CN,118),(0,F1,112),(0,K,116),(0,HP,56),(48,TO,52)],                          # 59
]

# --------------------------------------------------------------------------
#  FEEL : (bar0, barN, swing0, swing1, feel0, feel1)   feel in ticks, + = back
# --------------------------------------------------------------------------
FEEL = [
    ( 0,  4, 0.630, 0.630,  14.0,  14.0),   # Intro     wide shuffle, laid back
    ( 4, 12, 0.605, 0.585,  10.0,   4.0),   # A
    (12, 20, 0.585, 0.560,   2.0,  -8.0),   # A'        begins to push
    (20, 28, 0.595, 0.585,   9.0,   7.0),   # B         greasy, sitting back
    (28, 36, 0.565, 0.535,   0.0, -12.0),   # Build     straightening, rushing
    (36, 40, 0.545, 0.545,  -8.0,  -8.0),   # Climax I
    (40, 46, 0.645, 0.645,  16.0,  16.0),   # Whisper   widest, furthest back
    (46, 52, 0.605, 0.555,  10.0,  -6.0),   # Rebuild
    (52, 58, 0.550, 0.550,  -6.0,  -6.0),   # Climax II
    (58, 60, 0.635, 0.635,  12.0,  12.0),   # Coda
]

MARKERS = [
    (0,  "Intro - motif A bare"),
    (4,  "A - motif on the kit"),
    (12, "A' - developed, pushing"),
    (20, "B - linear / Latin colour"),
    (28, "Build"),
    (36, "Climax I"),
    (40, "Whisper"),
    (46, "Rebuild"),
    (52, "Climax II"),
    (58, "Coda"),
]


def warn(msg):
    sys.stderr.write("drum_solo: %s\n" % msg)


# --------------------------------------------------------------------------
#  timing:  swing warp of the beat + per-section push/lay-back + voice offsets
# --------------------------------------------------------------------------
def swing_pos(f, swing):
    """Map a straight position f in [0,1) of a beat onto the swung position."""
    s = min(max(swing, 0.5), 2.0 / 3.0)
    if f < 0.5:
        return f * (2.0 * s)              # the long half of the shuffle
    return s + (f - 0.5) * 2.0 * (1.0 - s)


def hit_tick(bar, u, swing, feel):
    beat = u / float(UPB)
    b = int(beat + 1e-9)
    f = beat - b
    if f < 0.0:
        f = 0.0
    pos = b + swing_pos(f, swing)
    return int(round((bar * 4.0 + pos) * TPB + feel))


def compute_feel():
    out = []
    for bar in range(BARS):
        for (a, b, s0, s1, f0, f1) in FEEL:
            if a <= bar < b:
                t = (bar - a) / float(b - a)
                out.append((s0 + (s1 - s0) * t, f0 + (f1 - f0) * t))
                break
        else:
            out.append((FEEL[-1][2], FEEL[-1][4]))
    return out


FEEL_BY_BAR = compute_feel()


# --------------------------------------------------------------------------
#  hits
# --------------------------------------------------------------------------
class Hit(object):
    __slots__ = ('bar', 'u', 'note', 'vel', 'cls', 'limb', 'tick', 'off', 'used_gap')

    def __init__(self, bar, u, note, vel, cls):
        self.bar = bar
        self.u = u
        self.note = note
        self.vel = int(vel)
        self.cls = cls
        self.limb = None
        self.tick = 0
        self.off = 0
        self.used_gap = MIN_LIMB_GAP

    @property
    def hu(self):
        return self.bar * BAR_UNITS + self.u


def compose():
    hits = []
    for bar, spec in enumerate(SPEC):
        for item in spec:
            u, note, vel = item[0], item[1], item[2]
            if note not in PERC:
                raise SystemExit("unknown percussion note %d" % note)
            cls = PERC[note][1]
            if len(item) > 3 and item[3] in ('H', 'F'):
                cls = item[3]
            hits.append(Hit(bar, u, note, vel, cls))
    hits.sort(key=lambda h: (h.bar, h.u, h.note))
    resolve_clashes(hits)
    hits.sort(key=lambda h: (h.hu, h.note))
    assign_limbs(hits)
    stamp_time(hits)
    return hits


def resolve_clashes(hits):
    """Never let more than two hands (or two feet) share an instant."""
    used = {}
    kept = []
    for h in hits:
        key = (h.bar, h.u)
        d = used.setdefault(key, {'H': 0, 'F': 0})
        if d[h.cls] < 2:
            d[h.cls] += 1
            kept.append(h)
            continue
        for delta in (1, -1, 2, -2, 3, -3):
            u2 = h.u + delta
            if not (0 <= u2 < BAR_UNITS):
                continue
            d2 = used.setdefault((h.bar, u2), {'H': 0, 'F': 0})
            if d2[h.cls] < 2:
                d2[h.cls] += 1
                h.u = u2
                kept.append(h)
                warn("bar %d: %s nudged by %d unit(s) to keep two hands/two feet"
                     % (h.bar + 1, PERC[h.note][0], delta))
                break
        else:
            warn("bar %d: dropped an impossible %s" % (h.bar + 1, PERC[h.note][0]))
    hits[:] = kept


def assign_limbs(hits):
    """One sticking that respects a 16th-note refractory time for every limb."""
    last = dict((L, -10 ** 9) for L in ('HR', 'HL', 'FR', 'FL'))
    relaxed = 0
    for h in hits:
        p = PREF.get(h.note, POOL[h.cls])
        cands = list(p) + [L for L in POOL[h.cls] if L not in p]
        if h.cls == 'H':
            cands.sort(key=lambda L: (last[L], p.index(L)))   # alternate sticks
        else:
            cands.sort(key=lambda L: (p.index(L), last[L]))   # one foot owns it
        chosen = None
        for gap in (MIN_LIMB_GAP, 4, 3, 2):
            for L in cands:
                if h.hu - last[L] >= gap:
                    chosen = L
                    h.used_gap = gap
                    break
            if chosen is not None:
                break
        if chosen is None:
            raise SystemExit("no limb free at bar %d unit %d" % (h.bar + 1, h.u))
        if h.used_gap < MIN_LIMB_GAP:
            relaxed += 1
        last[chosen] = h.hu
        h.limb = chosen
    if relaxed:
        warn("%d strike(s) needed a double-stroke (slightly under a 16th apart)"
             % relaxed)


def stamp_time(hits):
    for h in hits:
        swing, feel = FEEL_BY_BAR[h.bar]
        h.tick = hit_tick(h.bar, h.u, swing, feel) + MICRO.get(h.note, 0)
        if h.tick < 0:
            h.tick = 0


def validate(hits):
    """Prove: at most two hands and two feet at any instant, and playable limbs."""
    problems = 0

    # (a) composition grid
    per_unit = Counter((h.bar, h.u, h.cls) for h in hits)
    for k, n in per_unit.items():
        if n > 2:
            warn("grid: %d limbs of one kind at bar %d unit %d" % (n, k[0] + 1, k[1]))
            problems += 1

    # (b) real time: no instant may carry more than four strikes
    ts = sorted(hits, key=lambda h: (h.tick, h.limb))
    for i, h in enumerate(ts):
        tot = hands = feet = 0
        for j in range(i, len(ts)):
            if ts[j].tick - h.tick > WINDOW:
                break
            tot += 1
            if ts[j].cls == 'H':
                hands += 1
            else:
                feet += 1
        if tot > 4 or hands > 2 or feet > 2:
            warn("tick %d: %d strikes (%d hands, %d feet)" % (h.tick, tot, hands, feet))
            problems += 1

    # (c) one limb never strikes twice inside a 16th
    per_limb = {}
    for h in ts:
        per_limb.setdefault(h.limb, []).append(h)
    fastest = None
    for L, lst in sorted(per_limb.items()):
        for a, b in zip(lst, lst[1:]):
            dt_ms = (b.tick - a.tick) * 1000.0 * BPM / (60.0 * TPB)
            if fastest is None or dt_ms < fastest:
                fastest = dt_ms
            if b.hu - a.hu < MIN_LIMB_GAP:
                warn("%s strikes twice in %.0f ms" % (L, dt_ms))
                problems += 1

    if problems:
        warn("%d playability problem(s)" % problems)
    return problems, fastest


# --------------------------------------------------------------------------
#  MIDI output   (messages are built with their final delta time)
# --------------------------------------------------------------------------
def meta(kind, **kw):
    return lambda t: MetaMessage(kind, time=t, **kw)


def chanmsg(kind, **kw):
    return lambda t: Message(kind, time=t, **kw)


def write_midi(hits, path='solo.mid'):
    # note-offs: ring as long as the voice wants, but never past a re-strike
    by_note = {}
    for h in sorted(hits, key=lambda h: (h.tick, h.note)):
        by_note.setdefault(h.note, []).append(h)
    for note, lst in by_note.items():
        for i, h in enumerate(lst):
            off = h.tick + int(round(PERC[note][2] * TPB))
            if i + 1 < len(lst) and lst[i + 1].tick > h.tick:
                off = min(off, lst[i + 1].tick - 1)
            off = min(off, END_TICKS)
            h.off = max(off, h.tick + 1)

    mid = MidiFile(type=1, ticks_per_beat=TPB)

    # ---- track 0: tempo map, meter, form markers ------------------------
    t0 = MidiTrack()
    mid.tracks.append(t0)
    ev = [
        (0, 0, meta('track_name', name='Drum Solo - General MIDI, channel 10')),
        (0, 0, meta('copyright', text='generated by drum_solo.py')),
        (0, 0, meta('set_tempo', tempo=bpm2tempo(BPM))),
        (0, 0, meta('time_signature', numerator=4, denominator=4,
                    clocks_per_click=24, notated_32nd_notes_per_beat=8)),
    ]
    for bar, text in MARKERS:
        ev.append((bar * 4 * TPB, 1, meta('marker', text=text)))
    ev.append((END_TICKS, 2, meta('end_of_track')))
    flush(t0, ev)

    # ---- track 1: the drummer ------------------------------------------
    t1 = MidiTrack()
    mid.tracks.append(t1)
    ev = [
        (0, 1, chanmsg('control_change', channel=MIDI_CH, control=0, value=0)),
        (0, 1, chanmsg('control_change', channel=MIDI_CH, control=32, value=0)),
        (0, 1, chanmsg('program_change', channel=MIDI_CH, program=0)),
    ]
    for h in hits:
        vel = max(1, min(127, int(h.vel)))
        ev.append((h.tick, 3,
                   chanmsg('note_on', channel=MIDI_CH, note=h.note, velocity=vel)))
        ev.append((h.off, 0,
                   chanmsg('note_off', channel=MIDI_CH, note=h.note, velocity=0)))
    ev.append((END_TICKS, 4, meta('end_of_track')))
    flush(t1, ev)

    mid.save(path)


def flush(track, ev):
    ev.sort(key=lambda e: (e[0], e[1]))
    prev = 0
    for tick, _order, build in ev:
        track.append(build(tick - prev))
        prev = tick


# --------------------------------------------------------------------------
def main():
    hits = compose()
    problems, fastest = validate(hits)
    write_midi(hits, 'solo.mid')
    voices = sorted(set(h.note for h in hits))
    seconds = END_TICKS / float(TPB) * 60.0 / BPM
    print("solo.mid written: %d bars of 4/4 at %d bpm = %.3f s" % (BARS, BPM, seconds))
    print("  %d strikes, %d GM percussion voices (%s)"
          % (len(hits), len(voices),
             ", ".join("%d %s" % (n, PERC[n][0]) for n in voices)))
    print("  fastest single-limb repeat: %.0f ms   playability problems: %d"
          % (fastest if fastest else 0.0, problems))
    print("  output is deterministic: no random data is used anywhere")


if __name__ == '__main__':
    main()
