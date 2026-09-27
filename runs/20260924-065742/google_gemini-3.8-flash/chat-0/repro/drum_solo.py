"""
drum_solo.py - A two-minute virtuosic General MIDI drum solo.
Outputs solo.mid on MIDI Channel 10 (mido channel=9).
"""

import math
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

# --- General MIDI Drum Map ---
BASS_DRUM_ACOUSTIC = 35
BASS_DRUM_1 = 36
SIDE_STICK = 37
SNARE_ACOUSTIC = 38
HAND_CLAP = 39
SNARE_ELECTRIC = 40
LOW_FLOOR_TOM = 41
CLOSED_HIHAT = 42
HIGH_FLOOR_TOM = 43
PEDAL_HIHAT = 44
LOW_TOM = 45
OPEN_HIHAT = 46
LOW_MID_TOM = 47
HI_MID_TOM = 48
CRASH_1 = 49
HIGH_TOM = 50
RIDE_1 = 51
CHINESE_CYMBAL = 52
RIDE_BELL = 53
TAMBOURINE = 54
SPLASH_CYMBAL = 55
COWBELL = 56
CRASH_2 = 57
HIGH_TIMBALE = 65
LOW_TIMBALE = 66
HIGH_CONGA_OPEN = 63
LOW_CONGA = 64

TPB = 480  # Ticks per beat (quarter note)
BAR_TICKS = 4 * TPB  # 1920 ticks per bar in 4/4
BPM = 112  # 56 bars at 112 BPM = exactly 120.0 seconds


class DrumSequencer:
    def __init__(self):
        self.events = []  # (tick, note, velocity, duration)

    def hit(self, tick, note, vel, dur=90):
        vel = max(1, min(127, int(vel)))
        self.events.append((int(tick), note, vel, int(dur)))

    def flam(self, tick, note, vel, grace_note=None, hand_spread=25):
        """Play a flam: grace note just before the primary stroke."""
        gn = grace_note if grace_note else note
        grace_vel = max(20, int(vel * 0.45))
        self.hit(tick - hand_spread, gn, grace_vel, dur=40)
        self.hit(tick, note, vel, dur=90)

    def roll_32nd(self, start_tick, num_hits, note, start_vel, end_vel):
        step = TPB // 8  # 60 ticks per 32nd note
        for i in range(num_hits):
            t = start_tick + i * step
            frac = i / max(1, num_hits - 1)
            v = start_vel + frac * (end_vel - start_vel)
            self.hit(t, note, v, dur=45)

    def generate_solo(self):
        # 56 bars total (Bar 0 to 55)

        # -------------------------------------------------------------
        # THEMATIC MOTIFS
        # Core rhythmic theme: 3-3-2 syncopation [dotted 8th, dotted 8th, 8th]
        # Motif A: Kick & Snare syncopated funk call
        # Motif B: Melodic descending toms
        # Motif C: Bell and timbale Latin-inflected cascara
        # -------------------------------------------------------------

        # Persistent steady foot keeping time where appropriate:
        # Left foot hi-hat chick on beats 2 and 4 during certain sections
        for bar in range(0, 16):
            b_tick = bar * BAR_TICKS
            self.hit(b_tick + TPB, PEDAL_HIHAT, 68)
            self.hit(b_tick + 3 * TPB, PEDAL_HIHAT, 74)

        # =============================================================
        # SECTION 1: THE INCEPTION & MOTIF STATEMENT (Bars 0 - 7)
        # Quiet, mysterious, establishing the ride & ghost notes,
        # unveiling the core 3-3-2 rhythmic motif.
        # =============================================================
        for bar in range(0, 8):
            b_tick = bar * BAR_TICKS
            dyn = 50 + bar * 6  # Gradual dynamic rise pp -> mf

            # Ride cymbal pulse with subtle jazz-funk swing
            for beat in range(4):
                t_beat = b_tick + beat * TPB
                self.hit(t_beat, RIDE_1, dyn + 10)
                # swung upbeat
                self.hit(t_beat + int(TPB * 0.62), RIDE_1, dyn - 12)

            # Bar-specific phrasing
            if bar in (0, 1):
                # Delicate ghosted snare and kick stating the motif quietly
                # 3-3-2 placement: 0, 360, 720 ticks
                self.hit(b_tick, BASS_DRUM_1, dyn + 15)
                self.hit(b_tick + 360, SIDE_STICK, dyn + 5)
                self.hit(b_tick + 720, BASS_DRUM_1, dyn + 10)
                self.hit(b_tick + 960, SIDE_STICK, dyn + 2)
                self.hit(b_tick + 1440, SIDE_STICK, dyn - 5)

            elif bar in (2, 3):
                # Introduce toms responding to the side stick
                self.hit(b_tick, BASS_DRUM_1, dyn + 20)
                self.hit(b_tick + 360, HIGH_TOM, dyn + 10)
                self.hit(b_tick + 720, LOW_TOM, dyn + 8)
                self.hit(b_tick + 1200, HIGH_FLOOR_TOM, dyn + 12)
                self.hit(b_tick + 1440, SIDE_STICK, dyn + 2)
                # Ghost note tapers on snare
                self.hit(b_tick + 1680, SNARE_ACOUSTIC, 35)
                self.hit(b_tick + 1800, SNARE_ACOUSTIC, 40)

            elif bar in (4, 5):
                # Transition from side-stick to full snare ghost notes & accents
                self.hit(b_tick, BASS_DRUM_1, dyn + 22)
                self.flam(b_tick + TPB * 2, SNARE_ACOUSTIC, dyn + 25)
                self.hit(b_tick + 360, SNARE_ACOUSTIC, 38)
                self.hit(b_tick + 720, BASS_DRUM_1, dyn + 15)
                self.hit(b_tick + 1320, SNARE_ACOUSTIC, 42)
                self.hit(b_tick + 1440, OPEN_HIHAT, dyn + 10)
                self.hit(b_tick + 1680, PEDAL_HIHAT, 85)  # Hi-hat foot snap close

            elif bar == 6:
                # Tom run across the stereo field
                self.hit(b_tick, BASS_DRUM_1, 90)
                self.hit(b_tick + 240, HIGH_TOM, 80)
                self.hit(b_tick + 480, HI_MID_TOM, 82)
                self.hit(b_tick + 720, LOW_MID_TOM, 85)
                self.hit(b_tick + 960, LOW_TOM, 88)
                self.hit(b_tick + 1200, HIGH_FLOOR_TOM, 92)
                self.hit(b_tick + 1440, LOW_FLOOR_TOM, 98)
                self.hit(b_tick + 1680, BASS_DRUM_1, 100)

            elif bar == 7:
                # Dramatic setup: ghost roll into punchy stop
                self.roll_32nd(b_tick, 8, SNARE_ACOUSTIC, 40, 85)
                self.flam(b_tick + TPB * 2, SNARE_ACOUSTIC, 110)
                self.hit(b_tick + TPB * 2, CRASH_1, 105)
                self.hit(b_tick + TPB * 2, BASS_DRUM_1, 110)
                # Rest on beats 3 and 4 with just ticking hi-hat pedal
                self.hit(b_tick + 3 * TPB, PEDAL_HIHAT, 80)

        # =============================================================
        # SECTION 2: FUNK GROOVE VARIATIONS & GHOST NOTES (Bars 8 - 15)
        # Deep pocket, intense micro-dynamics, call-and-response.
        # =============================================================
        for bar in range(8, 16):
            b_tick = bar * BAR_TICKS

            # Hi-hat patterns: crisp 16th variations with accents
            for step in range(16):
                t_step = b_tick + step * 120
                if step in (0, 4, 8, 12):
                    self.hit(t_step, CLOSED_HIHAT, 88)
                elif step in (2, 6, 10, 14):
                    self.hit(t_step, CLOSED_HIHAT, 60)
                elif step == 15 and bar % 2 == 1:
                    self.hit(t_step, OPEN_HIHAT, 85)
                else:
                    self.hit(t_step, CLOSED_HIHAT, 45)

            # Bass drum and Snare call-response
            if bar % 2 == 0:
                self.hit(b_tick, BASS_DRUM_1, 108)
                self.hit(b_tick + 360, BASS_DRUM_1, 95)
                self.flam(b_tick + TPB, SNARE_ACOUSTIC, 112)  # Backbeat on 2
                self.hit(b_tick + 720, BASS_DRUM_1, 102)
                self.hit(b_tick + 1080, SNARE_ACOUSTIC, 42)  # Ghost
                self.flam(b_tick + 3 * TPB, SNARE_ACOUSTIC, 115)  # Backbeat on 4
                self.hit(b_tick + 1680, BASS_DRUM_1, 96)
                self.hit(b_tick + 1800, SNARE_ACOUSTIC, 45)
            else:
                self.hit(b_tick, BASS_DRUM_1, 112)
                self.flam(b_tick + TPB, SNARE_ACOUSTIC, 115)
                self.hit(b_tick + 600, SNARE_ACOUSTIC, 44)
                self.hit(b_tick + 720, BASS_DRUM_1, 100)
                self.hit(b_tick + 840, BASS_DRUM_1, 95)
                self.flam(b_tick + 3 * TPB, SNARE_ACOUSTIC, 118)

                # Linear fill at the end of odd bars
                if bar in (9, 13):
                    self.hit(b_tick + 1560, HIGH_TOM, 95)
                    self.hit(b_tick + 1680, LOW_TOM, 100)
                    self.hit(b_tick + 1800, HIGH_FLOOR_TOM, 105)
                elif bar == 11:
                    # Snare triplet break
                    trip = TPB // 3  # 160 ticks
                    self.hit(b_tick + 3 * TPB + trip, SNARE_ACOUSTIC, 95)
                    self.hit(b_tick + 3 * TPB + 2 * trip, HIGH_TOM, 102)
                elif bar == 15:
                    # Transition fill into Section 3
                    self.hit(b_tick + 1440, SPLASH_CYMBAL, 100)
                    self.hit(b_tick + 1440, BASS_DRUM_1, 105)
                    self.hit(b_tick + 1560, SNARE_ACOUSTIC, 85)
                    self.hit(b_tick + 1680, LOW_TOM, 98)
                    self.hit(b_tick + 1800, LOW_FLOOR_TOM, 108)

        # =============================================================
        # SECTION 3: POLYRHYTHMIC EXPLORATION (Bars 16 - 23)
        # Ride bell accents in dotted-quarter (3/8 cross-rhythm over 4/4)
        # Left foot maintains steady 8th notes on pedal hi-hat.
        # =============================================================
        for bar in range(16, 24):
            b_tick = bar * BAR_TICKS

            # Hi-hat foot keeps steady 8th pulse
            for eighth in range(8):
                self.hit(b_tick + eighth * (TPB // 2), PEDAL_HIHAT, 72)

            # Dotted quarter ride bell pattern: every 360 ticks
            # Across 2 bars, 360 ticks creates an exciting 8-against-3 cycle
            bar_offset = (bar - 16) * BAR_TICKS
            for t_rel in range(0, BAR_TICKS, 360):
                self.hit(b_tick + t_rel, RIDE_BELL, 106)
                # Kick occasionally joins the bell
                if t_rel in (0, 720, 1440):
                    self.hit(b_tick + t_rel, BASS_DRUM_1, 108)

            # Left hand answers on snare and toms in between the bell strikes
            if bar in (16, 17, 18):
                self.hit(b_tick + 180, SNARE_ACOUSTIC, 45)
                self.flam(b_tick + 540, SNARE_ACOUSTIC, 95)
                self.hit(b_tick + 900, HIGH_TOM, 88)
                self.hit(b_tick + 1260, SNARE_ACOUSTIC, 48)
                self.flam(b_tick + 1620, LOW_TOM, 100)

            elif bar in (19, 20):
                # Faster interplay with double strokes
                self.hit(b_tick + 180, HI_MID_TOM, 92)
                self.hit(b_tick + 240, HI_MID_TOM, 85)
                self.hit(b_tick + 540, LOW_TOM, 98)
                self.hit(b_tick + 900, HIGH_FLOOR_TOM, 102)
                self.hit(b_tick + 1260, SNARE_ACOUSTIC, 90)
                self.hit(b_tick + 1380, BASS_DRUM_1, 95)
                self.flam(b_tick + 1620, LOW_FLOOR_TOM, 108)

            elif bar == 21:
                # Dynamic drop: whisper snare buzz/rolls
                self.roll_32nd(b_tick, 16, SNARE_ACOUSTIC, 32, 70)
                self.roll_32nd(b_tick + TPB * 2, 16, SNARE_ACOUSTIC, 70, 35)

            elif bar == 22:
                # Creeping back up with syncopated tom dialogue
                self.hit(b_tick, HIGH_TOM, 55)
                self.hit(b_tick + 240, HIGH_TOM, 65)
                self.hit(b_tick + 480, LOW_TOM, 75)
                self.hit(b_tick + 720, HIGH_FLOOR_TOM, 85)
                self.hit(b_tick + 960, LOW_FLOOR_TOM, 95)
                self.hit(b_tick + 1200, BASS_DRUM_1, 105)
                self.flam(b_tick + 1440, SNARE_ACOUSTIC, 112)
                self.hit(b_tick + 1680, BASS_DRUM_1, 110)

            elif bar == 23:
                # Climax of Section 3: massive crash punctuation
                self.hit(b_tick, CRASH_1, 118)
                self.hit(b_tick, BASS_DRUM_1, 118)
                # Rapid descending triplet run
                trip_step = TPB // 3
                toms = [HIGH_TOM, HI_MID_TOM, LOW_MID_TOM, LOW_TOM, HIGH_FLOOR_TOM, LOW_FLOOR_TOM]
                for idx, t_note in enumerate(toms):
                    self.hit(b_tick + TPB + idx * trip_step, t_note, 95 + idx * 4)

        # =============================================================
        # SECTION 4: AFRO-CUBAN / LATIN FUSION BREAKDOWN (Bars 24 - 31)
        # Cascara rhythm on Cowbell & Timbale, Conga tones, syncopated kick.
        # =============================================================
        # Cascara rhythm pattern over 2 bars (16 sixteenths per bar):
        # Bar 1: X . X X . X . X . X X . X . X .
        cascara_1 = [0, 2, 3, 5, 7, 9, 10, 12, 14]
        # Bar 2: X . X . X X . X . X . X X . X .
        cascara_2 = [0, 2, 4, 5, 7, 9, 11, 12, 14]

        for bar in range(24, 32):
            b_tick = bar * BAR_TICKS
            is_odd = (bar % 2 == 1)
            pattern = cascara_2 if is_odd else cascara_1

            # Right hand plays cowbell / timbale cascara
            for step in pattern:
                t_step = b_tick + step * 120
                inst = COWBELL if step in (0, 7, 12) else HIGH_TIMBALE
                self.hit(t_step, inst, 92 + (step % 5) * 4)

            # Left foot keeps hi-hat chick on 2 and 4
            self.hit(b_tick + TPB, PEDAL_HIHAT, 78)
            self.hit(b_tick + 3 * TPB, PEDAL_HIHAT, 82)

            # Left hand plays conga rhythms and snare ghost/slaps
            self.hit(b_tick + 120, HIGH_CONGA_OPEN, 80)
            self.hit(b_tick + 480, LOW_CONGA, 85)
            self.hit(b_tick + 600, HIGH_CONGA_OPEN, 88)
            self.hit(b_tick + 1080, HIGH_CONGA_OPEN, 85)
            self.hit(b_tick + 1320, LOW_CONGA, 90)
            self.flam(b_tick + 1560, SNARE_ACOUSTIC, 95)

            # Right foot: Tumbao kick pattern (pulse on beat 1 and upbeat of 2 and 4)
            self.hit(b_tick, BASS_DRUM_ACOUSTIC, 98)
            self.hit(b_tick + 720, BASS_DRUM_ACOUSTIC, 104)
            self.hit(b_tick + 1680, BASS_DRUM_ACOUSTIC, 106)

            # Bar 31 build-up out of Latin section
            if bar == 31:
                # Timbales roll into Chinese Cymbal hit
                self.roll_32nd(b_tick + TPB * 2, 8, HIGH_TIMBALE, 70, 110)
                self.roll_32nd(b_tick + TPB * 3, 8, LOW_TIMBALE, 85, 118)

        # =============================================================
        # SECTION 5: LINEAR DRUMMING & SIX-STROKE ROLLS (Bars 32 - 39)
        # Intricate, hyper-articulated linear phrases: no two limbs hit
        # at the same instant (pure single-note melody across the kit).
        # =============================================================
        linear_patterns = [
            # 16-note linear sequence: (note, velocity)
            # R=Right Hand, L=Left Hand, K=Kick
            [(HIGH_TOM, 100), (SNARE_ACOUSTIC, 45), (BASS_DRUM_1, 105), (SNARE_ACOUSTIC, 42),
             (RIDE_BELL, 98), (SNARE_ACOUSTIC, 48), (BASS_DRUM_1, 102), (HI_MID_TOM, 96),
             (SNARE_ACOUSTIC, 112), (BASS_DRUM_1, 100), (LOW_TOM, 98), (BASS_DRUM_1, 104),
             (HIGH_FLOOR_TOM, 105), (SNARE_ACOUSTIC, 45), (LOW_FLOOR_TOM, 110), (BASS_DRUM_1, 108)],

            [(RIDE_1, 102), (SNARE_ACOUSTIC, 45), (BASS_DRUM_1, 105), (HIGH_TOM, 98),
             (SNARE_ACOUSTIC, 114), (BASS_DRUM_1, 102), (BASS_DRUM_1, 98), (HI_MID_TOM, 100),
             (RIDE_BELL, 105), (SNARE_ACOUSTIC, 44), (BASS_DRUM_1, 108), (LOW_TOM, 104),
             (SNARE_ACOUSTIC, 116), (HIGH_FLOOR_TOM, 106), (LOW_FLOOR_TOM, 110), (BASS_DRUM_1, 112)],
        ]

        for bar in range(32, 40):
            b_tick = bar * BAR_TICKS

            # Hi-hat foot chick firmly marking quarter-notes
            for q in range(4):
                self.hit(b_tick + q * TPB, PEDAL_HIHAT, 78)

            if bar < 36:
                # Linear 16th-note phrasing
                pat = linear_patterns[bar % 2]
                for step, (note, vel) in enumerate(pat):
                    t_step = b_tick + step * 120
                    self.hit(t_step, note, vel)

            elif bar in (36, 37):
                # Sextuplet / Triplet flurries (6-stroke roll pattern: R l l r r L)
                # Accent on 1, ghost middle, accent on 6
                sub_step = TPB // 6  # 80 ticks
                for beat in range(4):
                    t_beat = b_tick + beat * TPB
                    notes_vels = [
                        (SNARE_ACOUSTIC, 112),
                        (SNARE_ACOUSTIC, 45),
                        (SNARE_ACOUSTIC, 42),
                        (HIGH_TOM if beat % 2 == 0 else HI_MID_TOM, 50),
                        (LOW_TOM if beat % 2 == 0 else HIGH_FLOOR_TOM, 52),
                        (CRASH_1 if beat == 0 else (BASS_DRUM_1 if beat == 2 else LOW_FLOOR_TOM), 115)
                    ]
                    for s_idx, (sn, sv) in enumerate(notes_vels):
                        self.hit(t_beat + s_idx * sub_step, sn, sv)

            elif bar in (38, 39):
                # Metric modulation illusion: dotted-8th kick-crash punches
                # cutting against furious snare rolls
                for s in range(16):
                    t_step = b_tick + s * 120
                    # Continuous rapid snare undercurrent
                    self.hit(t_step, SNARE_ACOUSTIC, 50 + (s % 4) * 6)

                # Accents across the bar line
                punches = [0, 360, 720, 1080, 1440, 1800]
                for p in punches:
                    self.hit(b_tick + p, BASS_DRUM_1, 118)
                    cym = CRASH_2 if p % 720 == 0 else SPLASH_CYMBAL
                    self.hit(b_tick + p, cym, 112)

        # =============================================================
        # SECTION 6: THE APEX / THUNDERING CADENZA (Bars 40 - 47)
        # Full dynamic power: alternating double-kick drive, sweeping
        # tom runs, china cymbal explosions, tension reaching peak.
        # =============================================================
        for bar in range(40, 48):
            b_tick = bar * BAR_TICKS

            if bar in (40, 41):
                # Double-bass driving groove with half-time snare
                for s in range(16):
                    t_step = b_tick + s * 120
                    # Fast alternating feet: RF (Bass Drum 1) / LF (Acoustic Bass Drum)
                    k_note = BASS_DRUM_1 if s % 2 == 0 else BASS_DRUM_ACOUSTIC
                    self.hit(t_step, k_note, 104 + (s % 2) * 8)

                    # Riding on the China and Crash
                    if s % 2 == 0:
                        self.hit(t_step, CHINESE_CYMBAL if s % 4 == 0 else RIDE_BELL, 108)

                # Giant snare backbeats on beats 2 and 4
                self.flam(b_tick + TPB, SNARE_ACOUSTIC, 126)
                self.hit(b_tick + TPB, CRASH_1, 118)
                self.flam(b_tick + 3 * TPB, SNARE_ACOUSTIC, 127)
                self.hit(b_tick + 3 * TPB, CRASH_2, 120)

            elif bar in (42, 43):
                # Quad fills (2 hands on toms, 2 feet on kicks) - classic gospel/fusion chops
                # 4-note grouping: Hand, Hand, Foot, Foot
                quad_step = 120  # 16th notes
                for q_grp in range(4):
                    t_grp = b_tick + q_grp * 480
                    tom_pair = [
                        (HIGH_TOM, HI_MID_TOM),
                        (LOW_MID_TOM, LOW_TOM),
                        (HIGH_FLOOR_TOM, LOW_FLOOR_TOM),
                        (SNARE_ACOUSTIC, LOW_FLOOR_TOM)
                    ][q_grp]

                    self.hit(t_grp, tom_pair[0], 115)
                    self.hit(t_grp + quad_step, tom_pair[1], 118)
                    self.hit(t_grp + 2 * quad_step, BASS_DRUM_1, 116)
                    self.hit(t_grp + 3 * quad_step, BASS_DRUM_ACOUSTIC, 114)

            elif bar in (44, 45):
                # Rhythmic displacement: 5-note grouping over 16ths
                # Accent pattern shifts across the beat
                notes_5 = [
                    (CRASH_1, BASS_DRUM_1, 120),
                    (SNARE_ACOUSTIC, None, 50),
                    (SNARE_ACOUSTIC, None, 55),
                    (HIGH_TOM, None, 105),
                    (LOW_FLOOR_TOM, BASS_DRUM_1, 115)
                ]
                for s in range(16):
                    t_step = b_tick + s * 120
                    item = notes_5[s % 5]
                    self.hit(t_step, item[0], item[2])
                    if item[1]:
                        self.hit(t_step, item[1], item[2])

            elif bar == 46:
                # Sudden dramatic silence on beats 3 and 4!
                self.flam(b_tick, SNARE_ACOUSTIC, 127)
                self.hit(b_tick, CRASH_1, 125)
                self.hit(b_tick, BASS_DRUM_1, 125)
                self.hit(b_tick + 240, HIGH_TOM, 112)
                self.hit(b_tick + 480, LOW_FLOOR_TOM, 118)
                self.hit(b_tick + 720, BASS_DRUM_1, 120)
                self.flam(b_tick + 960, SNARE_ACOUSTIC, 127)
                self.hit(b_tick + 960, CRASH_2, 124)
                # Rest of bar 46 is SILENCE (dramatic pregnant pause)

            elif bar == 47:
                # Breaking the silence: whisper ghost notes swelling into a storm
                self.roll_32nd(b_tick + TPB * 2, 16, SNARE_ACOUSTIC, 25, 125)
                # Left foot hi-hat splashing
                self.hit(b_tick + TPB * 2, OPEN_HIHAT, 70)
                self.hit(b_tick + TPB * 3, PEDAL_HIHAT, 90)

        # =============================================================
        # SECTION 7: GRAND CLIMAX, CODA & RESOLUTION (Bars 48 - 55)
        # Bring back the opening motif (Theme Recap) at maximum power,
        # followed by an epic ritardando cascade and final ring.
        # =============================================================
        # Bars 48-49: Motif recapitulation with full kit orchestration
        for bar in range(48, 50):
            b_tick = bar * BAR_TICKS
            # Theme: 3-3-2 in giant crashes and kick unisons
            motif_hits = [0, 360, 720, 1200, 1560]
            for h in motif_hits:
                self.hit(b_tick + h, BASS_DRUM_1, 126)
                self.hit(b_tick + h, CRASH_1 if h % 720 == 0 else CRASH_2, 122)

            # Blazing snare rolls between theme statements
            self.roll_32nd(b_tick + 120, 3, SNARE_ACOUSTIC, 85, 105)
            self.roll_32nd(b_tick + 480, 3, HIGH_TOM, 90, 110)
            self.roll_32nd(b_tick + 840, 5, LOW_FLOOR_TOM, 95, 115)

        # Bar 50: Blistering 32nd-note descending tom run across all 6 toms
        b_tick_50 = 50 * BAR_TICKS
        all_toms = [HIGH_TOM, HI_MID_TOM, LOW_MID_TOM, LOW_TOM, HIGH_FLOOR_TOM, LOW_FLOOR_TOM]
        for i in range(24):  # 24 hits across beats 1, 2, 3
            t_hit = b_tick_50 + i * (BAR_TICKS * 3 // 4 // 24)
            tom_idx = min(5, i // 4)
            self.hit(t_hit, all_toms[tom_idx], 105 + (i % 4) * 4)
            if i % 4 == 0:
                self.hit(t_hit, BASS_DRUM_1, 115)

        # Beat 4 of bar 50: Slamming stop
        self.flam(b_tick_50 + 3 * TPB, SNARE_ACOUSTIC, 127)
        self.hit(b_tick_50 + 3 * TPB, CRASH_1, 125)
        self.hit(b_tick_50 + 3 * TPB, BASS_DRUM_1, 125)

        # Bars 51-52: Call and Response breakdown (Funk / Jazz phrasing)
        for bar in (51, 52):
            b_tick = bar * BAR_TICKS
            # Call: Hi-hat and Snare
            self.hit(b_tick, CLOSED_HIHAT, 95)
            self.hit(b_tick + 160, CLOSED_HIHAT, 70)
            self.hit(b_tick + 320, OPEN_HIHAT, 105)
            self.hit(b_tick + 480, PEDAL_HIHAT, 100)
            self.flam(b_tick + 480, SNARE_ACOUSTIC, 120)

            # Response: Syncopated toms & bass drum
            self.hit(b_tick + 720, BASS_DRUM_1, 115)
            self.hit(b_tick + 960, HIGH_TOM, 110)
            self.hit(b_tick + 1200, LOW_TOM, 112)
            self.hit(b_tick + 1440, HIGH_FLOOR_TOM, 116)
            self.hit(b_tick + 1680, LOW_FLOOR_TOM, 120)

        # Bars 53-54: Grand Ritardando Setup (Massive syncopated unison hits)
        # Expanding interval between hits to create a physical ritardando
        b_tick_53 = 53 * BAR_TICKS
        rit_offsets = [0, 360, 760, 1220, 1740, 2340, 3040]
        cymbals = [CRASH_1, CRASH_2, CHINESE_CYMBAL, CRASH_1, CRASH_2, CHINESE_CYMBAL, CRASH_1]

        for idx, offset in enumerate(rit_offsets):
            t_hit = b_tick_53 + offset
            if t_hit < 55 * BAR_TICKS:
                self.hit(t_hit, cymbals[idx], 122)
                self.hit(t_hit, BASS_DRUM_1, 125)
                self.flam(t_hit, SNARE_ACOUSTIC, 125)

        # Bar 54 end into Bar 55: Final thundering roll leading to the final crash
        b_tick_55 = 55 * BAR_TICKS
        # 16-note double-stroke roll across floor toms and snare accelerating into beat 1
        roll_start = b_tick_55 - 960
        for r_step in range(16):
            t_r = roll_start + r_step * 60
            drum = LOW_FLOOR_TOM if r_step < 6 else (HIGH_FLOOR_TOM if r_step < 10 else SNARE_ACOUSTIC)
            self.hit(t_r, drum, 85 + r_step * 2)

        # =============================================================
        # THE FINAL HIT: Beat 1 of Bar 55 (Tick 55 * BAR_TICKS = 105600)
        # At 112 BPM, Bar 55 Beat 1 lands at 117.8 seconds!
        # The crash, ride bell, and bass drum ring out through second 120.
        # =============================================================
        final_tick = b_tick_55
        self.hit(final_tick, BASS_DRUM_1, 127, dur=1920)
        self.hit(final_tick, CRASH_1, 127, dur=3840)
        self.hit(final_tick, CRASH_2, 125, dur=3840)
        self.flam(final_tick, SNARE_ACOUSTIC, 127)

        # Final delicate ride cymbal shimmer after the explosion, fading into black
        self.hit(final_tick + TPB * 2, RIDE_BELL, 75, dur=1440)
        self.hit(final_tick + TPB * 3, RIDE_1, 55, dur=1440)
        self.hit(final_tick + TPB * 4 - 120, PEDAL_HIHAT, 45, dur=480)

    def write_midi(self, filename="solo.mid"):
        # Sort events chronologically: note-offs and note-ons
        # Each event: (tick, type, note, velocity)
        raw_midi = []
        for tick, note, vel, dur in self.events:
            raw_midi.append((tick, "note_on", note, vel))
            raw_midi.append((tick + dur, "note_off", note, 0))

        # Sort primarily by tick; note_off before note_on if same tick and note
        raw_midi.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))

        mid = MidiFile(ticks_per_beat=TPB)
        track = MidiTrack()
        mid.tracks.append(track)

        # Track Meta Information
        track.append(MetaMessage("track_name", name="Drum Solo", time=0))
        # Tempo: 112 BPM -> 535714 microseconds per beat
        tempo_mpqn = mido.bpm2tempo(BPM)
        track.append(MetaMessage("set_tempo", tempo=tempo_mpqn, time=0))
        track.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))

        last_tick = 0
        for tick, msg_type, note, vel in raw_midi:
            delta = max(0, tick - last_tick)
            last_tick = tick
            track.append(
                Message(
                    msg_type,
                    channel=9,  # MIDI Channel 10 is index 9 in mido
                    note=note,
                    velocity=vel,
                    time=delta,
                )
            )

        track.append(MetaMessage("end_of_track", time=TPB))
        mid.save(filename)
        print(f"Successfully generated {filename} (Duration: ~120s at {BPM} BPM)")


if __name__ == "__main__":
    sequencer = DrumSequencer()
    sequencer.generate_solo()
    sequencer.write_midi("solo.mid")
