#!/usr/bin/env python3
"""Render a solo the same way every time and print a JSON report to stdout.

General MIDI defines one drum kit, so program changes and bank selects on
channel 10 are dropped (FluidR3_GM has 31 kits in bank 128); everything else
plays as written. FluidSynth renders FluidR3_GM to float WAV at 44.1 kHz, one
linear gain brings the whole solo to TARGET_LUFS, and ffmpeg encodes a
192 kbps MP3. A solo whose peaks would pass CEILING_DBTP at that loudness is
an error, not limited.

Runs inside the sandbox image (mido, fluidsynth, ffmpeg).

usage: python render.py IN.mid OUT.mp3
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import mido

SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
TARGET_LUFS = -27.0  # measured solos peak 22-24 dB above their loudness
CEILING_DBTP = -1.0


def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if p.returncode:
        raise RuntimeError(f"{cmd[0]} failed (exit {p.returncode}): {p.stderr.strip()[-1500:]}")
    return p


def kit_change(msg):
    return msg.type == "program_change" and msg.channel == 9 or (
        msg.type == "control_change" and msg.channel == 9 and msg.control in (0, 32))


def gm_drums(src, dst):
    """Copy src to dst without channel-10 kit changes; returns how many were dropped."""
    mf, dropped = mido.MidiFile(src), 0
    for i, track in enumerate(mf.tracks):
        out, carry = mido.MidiTrack(), 0
        for msg in track:
            if kit_change(msg):
                carry += msg.time
                dropped += 1
            else:
                out.append(msg.copy(time=msg.time + carry))
                carry = 0
        if carry:  # keep the track's length; mido merges this into the final end_of_track
            out.append(mido.MetaMessage("end_of_track", time=carry))
        mf.tracks[i] = out
    mf.save(dst)
    return dropped


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBTP)."""
    err = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
              "-af", "loudnorm=print_format=json", "-f", "null", "-"]).stderr
    d = json.loads(err[err.rindex("{"):])
    return float(d["input_i"]), float(d["input_tp"])


def main(src, dst):
    if src.is_symlink() or not src.is_file():
        sys.exit(f"{src} is not a regular file")
    with tempfile.TemporaryDirectory() as tmp:
        mid, wav = Path(tmp, "gm.mid"), Path(tmp, "solo.wav")
        dropped = gm_drums(src, mid)
        sh(["fluidsynth", "-ni", "-q", "-g", "0.5", "-r", "44100", "-O", "float", "-T", "wav",
            "-F", str(wav), SF2, str(mid)])
        lufs, peak = loudness(wav)
        if lufs == float("-inf"):
            sys.exit("render is silent")
        gain = TARGET_LUFS - lufs
        if peak + gain > CEILING_DBTP:
            sys.exit(f"peaks would reach {peak + gain:+.1f} dBTP at {TARGET_LUFS} LUFS; "
                     "lower TARGET_LUFS for every solo")
        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
            "-af", f"volume={gain:.2f}dB", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", str(dst)])
    out_lufs, out_peak = loudness(dst)
    seconds = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(dst)]).stdout)
    print(json.dumps({"kit_changes_dropped": dropped, "synth_lufs": lufs, "synth_peak_dbtp": peak,
                      "gain_db": round(gain, 2), "lufs": out_lufs, "peak_dbtp": out_peak,
                      "seconds": round(seconds, 2)}, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
