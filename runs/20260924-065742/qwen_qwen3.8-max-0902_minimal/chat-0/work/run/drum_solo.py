#!/usr/bin/env python3
"""
drum_solo.py – Generates a 2-minute General MIDI drum solo (solo.mid).

Structure (60 bars at 120 BPM = 120 seconds):
  Bars  1– 4  Intro: sparse ride, building
  Bars  5–12  Groove A: main funk motif established
  Bars 13–20  Groove B: variation, more syncopation
  Bars 21–28  Latin contrast: congas, timbales, clave
  Bars 29–36  Build: increasing density and dynamics
  Bars 37–44  Climax: full power
  Bars 45–48  Breakdown: space, tension
  Bars 49–56  Rebuild: motif returns, varied
  Bars 57–60  Outro: final statement, big ending
"""

import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

def main():
    TPB = 480
    CHANNEL = 9  # MIDI channel 10
    TEMPO = 500000  # 120 BPM

    Q = TPB          # quarter = 480
    E = TPB // 2     # eighth = 240
    S = TPB // 4     # sixteenth = 120
    T = TPB // 3     # triplet = 160
    SW = T * 2       # swung "and" offset = 320

    # Micro-timing offsets for human feel
    LAY_BACK = 12    # snare laid back
    PUSH = 8         # hi-hat pushed ahead
    GHOST_LAG = 6    # ghost notes slightly behind

    # GM Percussion notes
    BD = 36; SD = 38; SS = 37
    HH_C = 42; HH_O = 46; HH_P = 44
    RIDE = 51; RIDE_BELL = 53; RIDE2 = 59
    CR1 = 49; CR2 = 57; SPLASH = 55; CHINESE = 52
    T_HI = 50; T_HIMID = 48; T_LOMID = 47; T_LO = 45
    T_FHI = 43; T_FLO = 41
    COWBELL = 56; TAMBOURINE = 54
    CONGA_HI = 63; CONGA_LO = 64; CONGA_MUTE = 62
    TIMB_HI = 65; TIMB_LO = 66
    CLAVES = 75; WOOD_HI = 76; WOOD_LO = 77
    AGOGO_HI = 67; AGOGO_LO = 68
    BONGO_HI = 60; BONGO_LO = 61

    events = []

    def add(tick, note, vel):
        if tick >= 0 and vel > 0:
            events.append((int(tick), note, min(vel, 127)))

    def ms(m):
        """Start tick of measure m (0-indexed)."""
        return m * 4 * Q

    # ──────────────────────────────────────────────
    # SECTION 1: INTRO (bars 0–3)
    # ──────────────────────────────────────────────
    for m in range(4):
        t = ms(m)
        # Swung ride, gradually louder
        rv = 45 + m * 10
        for b in range(4):
            bt = t + b * Q
            add(bt, RIDE, rv)
            add(bt + SW - PUSH, RIDE, rv - 18)
        # Hi-hat pedal on 2 and 4 (foot)
        add(t + Q, HH_P, 50 + m * 5)
        add(t + 3 * Q, HH_P, 50 + m * 5)
        # Bass drum enters gradually
        if m >= 1:
            add(t, BD, 60 + m * 8)
        if m >= 2:
            add(t + 2 * Q, BD, 55 + m * 5)
        if m == 3:
            # Fill into groove
            add(t + 3 * Q + S, T_HI, 60)
            add(t + 3 * Q + 2 * S, T_HIMID, 70)
            add(t + 3 * Q + 3 * S, T_LO, 80)

    # ──────────────────────────────────────────────
    # SECTION 2: GROOVE A – Main Motif (bars 4–11)
    # Motif: BD on 1, "e" of 2, 3 | SD on 2 & 4
    # ──────────────────────────────────────────────
    for m in range(4, 12):
        t = ms(m)
        p = (m - 4) % 4

        # Hi-hat: swung eighths, pushed slightly
        for b in range(4):
            bt = t + b * Q
            hv = 72 if b % 2 == 0 else 56
            add(bt, HH_C, hv)
            add(bt + SW - PUSH, HH_C, 38)

        # Bass drum motif
        add(t, BD, 95)
        add(t + Q + S, BD, 72)
        add(t + 2 * Q, BD, 85)
        if p in (1, 3):
            add(t + 3 * Q + 3 * S, BD, 68)

        # Snare backbeat, laid back
        add(t + Q + LAY_BACK, SD, 102)
        add(t + 3 * Q + LAY_BACK, SD, 106)

        # Ghost notes (quiet, slightly behind)
        if p >= 1:
            add(t + 3 * S + GHOST_LAG, SD, 24)
            add(t + Q + 3 * S + GHOST_LAG, SD, 22)
            add(t + 2 * Q + S + GHOST_LAG, SD, 27)
        if p == 2:
            add(t + 3 * Q + S + GHOST_LAG, SD, 28)
            add(t + 3 * Q + 2 * S + GHOST_LAG, SD, 24)

        # End-of-phrase fill
        if p == 3:
            if m < 10:
                add(t + 3 * Q + 2 * S, T_HIMID, 62)
                add(t + 3 * Q + 3 * S, T_LO, 72)
            else:
                add(t + 2 * Q + 2 * S, T_HI, 65)
                add(t + 2 * Q + 3 * S, T_HIMID, 72)
                add(t + 3 * Q, T_LOMID, 78)
                add(t + 3 * Q + S, T_LO, 84)
                add(t + 3 * Q + 2 * S, T_FHI, 90)
                add(t + 3 * Q + 3 * S, T_FLO, 96)

    # ──────────────────────────────────────────────
    # SECTION 3: GROOVE B – Variation (bars 12–19)
    # More syncopation, ride bell, open hi-hat
    # ──────────────────────────────────────────────
    for m in range(12, 20):
        t = ms(m)
        p = (m - 12) % 4

        # Ride with bell on beat 1
        for b in range(4):
            bt = t + b * Q
            add(bt, RIDE_BELL if b == 0 else RIDE, 78 if b == 0 else 62)
            add(bt + SW - PUSH, RIDE, 38)

        # Bass drum – more active
        add(t, BD, 96)
        add(t + Q + S, BD, 70)
        add(t + 2 * Q, BD, 86)
        add(t + 2 * Q + 3 * S, BD, 62)
        if p in (0, 2):
            add(t + 3 * Q + S, BD, 68)
        else:
            add(t + 3 * Q + 3 * S, BD, 74)

        # Snare
        add(t + Q + LAY_BACK, SD, 104)
        add(t + 3 * Q + LAY_BACK, SD, 108)

        # Ghosts
        add(t + S + GHOST_LAG, SD, 22)
        add(t + 2 * S + GHOST_LAG, SD, 25)
        add(t + Q + 3 * S + GHOST_LAG, SD, 20)
        add(t + 2 * Q + S + GHOST_LAG, SD, 26)
        add(t + 3 * Q + S + GHOST_LAG, SD, 22)

        # Open hi-hat accents
        if p == 1:
            add(t + 2 * Q + SW, HH_O, 72)
        elif p == 3:
            add(t + 3 * Q + SW, HH_O, 78)
            add(t + 3 * Q + 2 * S, T_HI, 70)
            add(t + 3 * Q + 3 * S, CR1, 92)

    # ──────────────────────────────────────────────
    # SECTION 4: LATIN CONTRAST (bars 20–27)
    # Straight feel, congas, timbales, clave
    # ──────────────────────────────────────────────
    for m in range(20, 28):
        t = ms(m)
        p = (m - 20) % 4

        if m < 24:
            # 3-2 Son Clave
            if p == 0:
                add(t, CLAVES, 88)
                add(t + Q + E, CLAVES, 82)  # "and" of 2 (straight)
                add(t + 3 * Q, CLAVES, 88)
            elif p == 1:
                add(t + Q, CLAVES, 82)
                add(t + 2 * Q, CLAVES, 88)

            # Tumbao (conga)
            for b in range(4):
                add(t + b * Q + 3 * S, CONGA_HI, 52)
            add(t + 3 * Q, CONGA_LO, 78)
            add(t + 2 * Q + E, CONGA_MUTE, 45)

            # Bass drum (soft, anchoring)
            add(t, BD, 58)
            add(t + 2 * Q, BD, 52)

            # Cowbell (cascara-like)
            if p in (0, 2):
                add(t + Q, COWBELL, 58)
                add(t + 3 * Q, COWBELL, 52)
            # Wood block
            add(t + E, WOOD_HI, 42)
            add(t + 2 * Q + E, WOOD_HI, 38)
        else:
            # Intenser Latin (bars 24–27)
            add(t, TIMB_HI, 86)
            add(t + Q, TIMB_LO, 74)
            add(t + 2 * Q, TIMB_HI, 80)
            add(t + 3 * Q, TIMB_LO, 86)

            if p == 0:
                add(t, CLAVES, 92)
                add(t + Q + E, CLAVES, 86)
                add(t + 3 * Q, CLAVES, 92)
            elif p == 1:
                add(t + Q, CLAVES, 86)
                add(t + 2 * Q, CLAVES, 92)

            # Active congas
            add(t, CONGA_HI, 64)
            add(t + 2 * S, CONGA_HI, 52)
            add(t + Q, CONGA_LO, 74)
            add(t + Q + 3 * S, CONGA_HI, 58)
            add(t + 2 * Q, CONGA_HI, 64)
            add(t + 2 * Q + 2 * S, CONGA_HI, 52)
            add(t + 3 * Q, CONGA_LO, 84)

            # Bass drum
            add(t, BD, 68)
            add(t + Q + 2 * S, BD, 58)
            add(t + 2 * Q, BD, 64)
            add(t + 3 * Q + 2 * S, BD, 58)

            # Agogo
            add(t + E, AGOGO_HI, 48)
            add(t + 2 * Q + E, AGOGO_LO, 44)

            # Transition crash
            if m == 27:
                add(t + 3 * Q, CR1, 96)
                add(t + 3 * Q, BD, 100)
                add(t + 3 * Q + S, T_HI, 72)
                add(t + 3 * Q + 2 * S, T_HIMID, 80)
                add(t + 3 * Q + 3 * S, T_LO, 88)

    # ──────────────────────────────────────────────
    # SECTION 5: BUILD (bars 28–35)
    # Increasing density and velocity
    # ──────────────────────────────────────────────
    for m in range(28, 36):
        t = ms(m)
        frac = (m - 28) / 7.0
        bv = int(68 + frac * 42)

        # Hi-hat: 8ths → 16ths
        for b in range(4):
            bt = t + b * Q
            add(bt, HH_C, bv)
            if frac > 0.3:
                add(bt + S, HH_C, bv - 22)
            add(bt + E, HH_C, bv - 12)
            if frac > 0.55:
                add(bt + 3 * S, HH_C, bv - 26)

        # Bass drum
        add(t, BD, bv + 12)
        add(t + Q + S, BD, bv - 8)
        add(t + 2 * Q, BD, bv + 2)
        if frac > 0.4:
            add(t + 3 * Q, BD, bv - 4)
        if frac > 0.7:
            add(t + Q + 3 * S, BD, bv - 14)

        # Snare
        add(t + Q + LAY_BACK, SD, bv + 16)
        add(t + 3 * Q + LAY_BACK, SD, bv + 16)

        # Ghosts
        if frac > 0.25:
            add(t + 3 * S + GHOST_LAG, SD, 26)
            add(t + 2 * Q + S + GHOST_LAG, SD, 28)
        if frac > 0.55:
            add(t + S + GHOST_LAG, SD, 22)
            add(t + Q + 3 * S + GHOST_LAG, SD, 24)
            add(t + 3 * Q + S + GHOST_LAG, SD, 30)

        # Fills on odd bars
        if m % 2 == 1:
            fs = t + 3 * Q
            if frac < 0.5:
                add(fs + S, T_HI, bv - 8)
                add(fs + 2 * S, T_HIMID, bv)
                add(fs + 3 * S, T_LO, bv + 6)
            else:
                add(fs, T_HI, bv)
                add(fs + S, T_HIMID, bv + 4)
                add(fs + 2 * S, T_LOMID, bv + 8)
                add(fs + 3 * S, T_FLO, bv + 14)

    # ──────────────────────────────────────────────
    # SECTION 6: CLIMAX (bars 36–43)
    # Full power, crashes, driving ride
    # ──────────────────────────────────────────────
    for m in range(36, 44):
        t = ms(m)
        p = (m - 36) % 4

        # Crash accents
        if p == 0:
            add(t, CR1, 122)
            add(t, BD, 112)
        elif p == 2:
            add(t, CR2, 116)
            add(t, BD, 106)

        # Driving ride
        for b in range(4):
            bt = t + b * Q
            add(bt, RIDE, 92)
            add(bt + SW - PUSH, RIDE, 58)
            if p in (1, 3):
                add(bt + E, RIDE, 48)

        # Bass drum
        add(t, BD, 112)
        add(t + Q + S, BD, 84)
        add(t + 2 * Q, BD, 100)
        add(t + 3 * Q, BD, 92)
        if p in (1, 3):
            add(t + 2 * Q + 3 * S, BD, 78)

        # Snare
        add(t + Q + LAY_BACK, SD, 116)
        add(t + 3 * Q + LAY_BACK, SD, 120)

        # Ghosts
        add(t + 3 * S + GHOST_LAG, SD, 30)
        add(t + Q + 3 * S + GHOST_LAG, SD, 28)
        add(t + 2 * Q + S + GHOST_LAG, SD, 32)

        # Fills
        if p == 3:
            if m < 42:
                add(t + 2 * Q + 2 * S, T_HI, 92)
                add(t + 2 * Q + 3 * S, T_HIMID, 96)
                add(t + 3 * Q, T_LOMID, 100)
                add(t + 3 * Q + S, T_LO, 104)
                add(t + 3 * Q + 2 * S, T_FHI, 110)
                add(t + 3 * Q + 3 * S, T_FLO, 114)
            else:
                # Big fill into breakdown
                for i, (off, n, v) in enumerate([
                    (Q, T_HI, 100), (Q + S, T_HI, 106),
                    (Q + 2*S, T_HIMID, 102), (Q + 3*S, T_HIMID, 108),
                    (2*Q, T_LOMID, 110), (2*Q + S, T_LOMID, 106),
                    (2*Q + 2*S, T_LO, 112), (2*Q + 3*S, T_LO, 116),
                    (3*Q, T_FHI, 118), (3*Q + S, T_FLO, 122),
                    (3*Q + 2*S, CR1, 126), (3*Q + 3*S, CR2, 120),
                ]):
                    add(t + off, n, v)

    # ──────────────────────────────────────────────
    # SECTION 7: BREAKDOWN (bars 44–47)
    # Sudden space, tension
    # ──────────────────────────────────────────────
    t = ms(44)
    add(t, CR1, 98)
    add(t, BD, 88)
    add(t + 2 * Q, SS, 38)
    add(t + 3 * Q + SW, SS, 32)

    t = ms(45)
    add(t, SS, 44)
    add(t + Q + SW, SS, 34)
    add(t + 2 * Q, BD, 48)
    add(t + 3 * Q, SS, 40)

    t = ms(46)
    add(t, SS, 50)
    add(t + Q, BD, 54)
    add(t + 2 * Q, SS, 44)
    add(t + 2 * Q + SW, SD, 24)
    add(t + 3 * Q, BD, 58)
    add(t + 3 * Q + SW, SS, 38)

    t = ms(47)
    add(t, BD, 68)
    add(t + Q, SD, 58)
    add(t + 2 * Q, BD, 74)
    add(t + 2 * Q + SW, HH_C, 48)
    add(t + 3 * Q, SD, 78)
    add(t + 3 * Q + S, T_HI, 58)
    add(t + 3 * Q + 2 * S, T_HIMID, 68)
    add(t + 3 * Q + 3 * S, T_LO, 78)

    # ──────────────────────────────────────────────
    # SECTION 8: REBUILD (bars 48–55)
    # Motif returns, varied, building
    # ──────────────────────────────────────────────
    for m in range(48, 56):
        t = ms(m)
        p = (m - 48) % 4

        # Ride swing
        for b in range(4):
            bt = t + b * Q
            add(bt, RIDE, 72)
            add(bt + SW - PUSH, RIDE, 44)

        # Main motif
        add(t, BD, 100)
        add(t + Q + S, BD, 80)
        add(t + 2 * Q, BD, 92)
        if p in (0, 2):
            add(t + 3 * Q + 3 * S, BD, 74)
        else:
            add(t + 3 * Q + S, BD, 68)
            add(t + 3 * Q + 2 * S, BD, 74)

        # Snare
        add(t + Q + LAY_BACK, SD, 106)
        add(t + 3 * Q + LAY_BACK, SD, 110)

        # Ghosts
        add(t + 3 * S + GHOST_LAG, SD, 28)
        add(t + Q + 3 * S + GHOST_LAG, SD, 24)
        add(t + 2 * Q + S + GHOST_LAG, SD, 30)

        # Extra hi-hat in second half
        if m >= 52:
            add(t + E, HH_C, 52)
            add(t + 2 * Q + E, HH_C, 52)

        # Fills
        if p == 3:
            if m < 54:
                add(t + 3 * Q + S, T_HIMID, 74)
                add(t + 3 * Q + 2 * S, T_LO, 80)
                add(t + 3 * Q + 3 * S, T_FHI, 86)
            else:
                add(t + 2 * Q, T_HI, 86)
                add(t + 2 * Q + S, T_HIMID, 92)
                add(t + 2 * Q + 2 * S, T_LOMID, 96)
                add(t + 2 * Q + 3 * S, T_LO, 102)
                add(t + 3 * Q, T_FHI, 106)
                add(t + 3 * Q + S, T_FLO, 112)
                add(t + 3 * Q + 2 * S, CR1, 116)
                add(t + 3 * Q + 3 * S, CR2, 112)

    # ──────────────────────────────────────────────
    # SECTION 9: OUTRO (bars 56–59)
    # Final statement, big ending
    # ──────────────────────────────────────────────
    t = ms(56)
    add(t, CR1, 122)
    add(t, BD, 112)
    add(t + Q + LAY_BACK, SD, 112)
    add(t + 2 * Q, BD, 102)
    add(t + 2 * Q, CR2, 100)
    add(t + 3 * Q + LAY_BACK, SD, 116)

    t = ms(57)
    add(t, BD, 116)
    add(t + Q + LAY_BACK, SD, 116)
    add(t + Q + S, BD, 90)
    add(t + 2 * Q, BD, 110)
    add(t + 3 * Q + LAY_BACK, SD, 120)
    add(t + 3 * Q + 2 * S, BD, 100)
    add(t + 3 * Q + 3 * S, BD, 112)

    t = ms(58)
    for i, (off, n, v) in enumerate([
        (0, T_HI, 102), (S, T_HI, 106),
        (2*S, T_HIMID, 102), (3*S, T_HIMID, 108),
        (Q, T_LOMID, 110), (Q+S, T_LOMID, 106),
        (Q+2*S, T_LO, 112), (Q+3*S, T_LO, 116),
        (2*Q, T_FHI, 116), (2*Q+S, T_FLO, 120),
        (2*Q+2*S, CR1, 126), (2*Q+3*S, CR2, 122),
    ]):
        add(t + off, n, v)

    t = ms(59)
    add(t, CR1, 127)
    add(t, BD, 127)
    add(t + Q, CR2, 122)
    add(t + Q, BD, 122)
    add(t + 2 * Q, CR1, 126)
    add(t + 2 * Q, BD, 126)
    add(t + 3 * Q, CR1, 127)
    add(t + 3 * Q, CR2, 126)
    add(t + 3 * Q, BD, 127)
    add(t + 3 * Q + 2 * S, CR1, 127)
    add(t + 3 * Q + 2 * S, BD, 127)

    # ──────────────────────────────────────────────
    # BUILD MIDI FILE
    # ──────────────────────────────────────────────
    events.sort(key=lambda e: (e[0], e[1]))

    # Remove exact duplicates (same tick, same note)
    seen = set()
    unique = []
    for ev in events:
        key = (ev[0], ev[1])
        if key not in seen:
            seen.add(key)
            unique.append(ev)
    events = unique

    NOTE_DUR = 80  # ticks for note_off (percussive, short)

    midi_msgs = []
    for tick, note, vel in events:
        midi_msgs.append((tick, 1, note, vel))       # note_on
        midi_msgs.append((tick + NOTE_DUR, 0, note, 0))  # note_off

    # Sort: by tick, then note_off before note_on at same tick
    midi_msgs.sort(key=lambda x: (x[0], x[1], x[2]))

    mid = MidiFile(ticks_per_beat=TPB)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('track_name', name='Drum Solo', time=0))
    track.append(MetaMessage('set_tempo', tempo=TEMPO, time=0))
    track.append(MetaMessage('time_signature',
                             numerator=4, denominator=4,
                             clocks_per_click=24,
                             notated_32nd_notes_per_beat=8, time=0))

    prev_tick = 0
    for tick, is_on, note, vel in midi_msgs:
        delta = max(0, tick - prev_tick)
        if is_on:
            track.append(Message('note_on', channel=CHANNEL,
                                 note=note, velocity=vel, time=delta))
        else:
            track.append(Message('note_off', channel=CHANNEL,
                                 note=note, velocity=0, time=delta))
        prev_tick = tick

    track.append(MetaMessage('end_of_track', time=0))
    mid.save('solo.mid')
    print("solo.mid written successfully.")


if __name__ == '__main__':
    main()
