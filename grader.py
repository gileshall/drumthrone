#!/usr/bin/env python3
"""Grade one drum-solo run and print a JSON report to stdout.

Runs inside the sandbox image (Python 3.11, mido). SUBMISSION is the run's
work directory, mounted read-only; the shared script is
SUBMISSION/out/drum_solo.py. REPRO_DIR must be empty: the script runs there,
alone, and must write solo.mid next to itself. A second run in another empty
directory must write the same file. The harness renders REPRO_DIR/solo.mid
itself (render.py), so audio isn't graded.

usage: python grader.py SUBMISSION REPRO_DIR
"""
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import mido

REQUIRED_NOTES = set(range(35, 82))  # GM1 percussion map
DURATION = (110.0, 130.0)  # "two minute" solo, within 10 s
MIN_VEL, MAX_VEL = 30, 127
BANNED = {"music21", "pretty_midi", "midiutil", "miditoolkit", "midi", "mingus", "musicpy"}
MAX_SWEEP = 5  # more than 5 lone hits stepping one semitone in one direction = chromatic sweep
RUN_TIMEOUT = 300

# Every check is listed here so a run that dies early can't score well by
# skipping checks. Weight 0 = informational: the current prompt doesn't
# require it.
WEIGHTS = {
    "script_present": 1,
    "only_mido": 1,
    "runs": 2,
    "midi_parses": 1,
    "drums_on_channel_10": 1,
    "duration": 1,
    "deterministic": 1,
    "gm_coverage": 0,
    "no_chromatic_sweeps": 0,
    "tempo_change": 0,
    "meter_change": 0,
    "velocity_span": 0,
    "humanized": 0,
}

checks = {}


def check(name, value, detail=""):
    checks[name] = {"weight": WEIGHTS[name], "value": round(float(value), 3), "detail": detail}


def run(cmd, timeout=120, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout, **kw)


def clip(s, n=500):
    return s[-n:]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grade_script(path):
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except SyntaxError as e:
        check("only_mido", 0, f"syntax error: {e}")
        return
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            mods.add(node.module.split(".")[0])
    banned = sorted(mods & BANNED)
    detail = f"imports: {sorted(mods)}" + (f"; banned: {banned}" if banned else "")
    check("only_mido", "mido" in mods and not banned, detail)


def run_script(script, cwd):
    """Run the script alone in cwd. Returns (detail, solo.mid or None, exited 0)."""
    shutil.copyfile(script, cwd / "drum_solo.py")
    try:
        p = run([sys.executable, "drum_solo.py"], cwd=cwd, timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"timed out after {RUN_TIMEOUT}s", None, False
    mid = cwd / "solo.mid"
    wrote = mid.is_file() and not mid.is_symlink()
    detail = f"exit {p.returncode}" + ("" if wrote else "; no solo.mid written")
    err = clip(p.stderr).strip()
    if err and (p.returncode or not wrote):
        detail += f": {err}"
    return detail, mid if wrote else None, p.returncode == 0


def longest_sweep(drums, tpb):
    """Longest run of lone hits each one semitone from the last, same direction.
    Hits within a 1/32 beat are grouped as simultaneous (humanization jitter)."""
    tol = max(1, tpb // 32)
    groups = []
    for t, _, n, _ in drums:
        if groups and t - groups[-1][0] <= tol:
            groups[-1][1].append(n)
        else:
            groups.append((t, [n]))
    best = run_len = 1 if drums else 0
    prev = step = None
    for _, ns in groups:
        n = ns[0] if len(ns) == 1 else None
        if n is not None and prev is not None and abs(n - prev) == 1:
            run_len = run_len + 1 if n - prev == step else 2
            step = n - prev
        else:
            run_len, step = 1, None
        prev = n
        best = max(best, run_len)
    return best


def humanization(drums, tpb):
    if not drums:
        return 0.0, "no notes"
    # Finest grid that holds 16ths, 32nds and triplets alike.
    grid = tpb // 24 if tpb % 24 == 0 else tpb // 8 if tpb % 8 == 0 else 1
    off = sum(t % grid != 0 for t, *_ in drums) / len(drums) if grid > 1 else 0.0
    distinct = len({v for *_, v in drums})
    value = 0.5 * (off >= 0.2) + 0.5 * (distinct >= 16)
    return value, f"{off:.0%} of hits off a 1/{tpb // grid}-beat grid; {distinct} distinct velocities"


def grade_midi(mf, stats):
    notes, tempos, sigs = [], set(), set()
    for track in mf.tracks:
        tick = 0
        for m in track:
            tick += m.time
            if m.type == "note_on" and m.velocity:
                notes.append((tick, m.channel, m.note, m.velocity))
            elif m.type == "set_tempo":
                tempos.add(m.tempo)
            elif m.type == "time_signature":
                sigs.add((m.numerator, m.denominator))
    notes.sort()
    drums = [n for n in notes if n[1] == 9]
    try:
        length, length_err = mf.length, ""
    except Exception as e:  # e.g. type 2 files; fails the duration check with the reason
        length, length_err = 0.0, f"{type(e).__name__}: {e}"
    stats.update(
        midi_seconds=round(length, 2),
        notes=len(notes),
        drum_notes=len(drums),
        tempos_bpm=sorted(round(mido.tempo2bpm(t), 1) for t in tempos),
        time_signatures=sorted(f"{a}/{b}" for a, b in sigs),
    )

    check("drums_on_channel_10", bool(drums) and len(drums) / len(notes) >= 0.95,
          f"{len(drums)}/{len(notes)} note-ons on channel 10")
    missing = sorted(REQUIRED_NOTES - {n for _, _, n, _ in drums})
    check("gm_coverage", 1 - len(missing) / len(REQUIRED_NOTES),
          f"missing: {missing}" if missing else "all 47 used")
    sweep = longest_sweep(drums, mf.ticks_per_beat)
    check("no_chromatic_sweeps", sweep <= MAX_SWEEP, f"longest semitone run: {sweep}")
    lo, hi = DURATION
    check("duration", lo <= length <= hi, length_err or f"{length:.1f}s (want {lo:.0f}-{hi:.0f})")
    check("tempo_change", len(tempos) >= 2, f"{stats['tempos_bpm']} bpm")
    check("meter_change", len(sigs) >= 2, f"{stats['time_signatures']}")
    vels = [v for *_, v in drums]
    if vels:
        check("velocity_span", ((min(vels) <= MIN_VEL) + (max(vels) >= MAX_VEL)) / 2,
              f"{min(vels)}-{max(vels)} (want <={MIN_VEL} and {MAX_VEL})")
    check("humanized", *humanization(drums, mf.ticks_per_beat))


def main(work, clean):
    if any(clean.iterdir()):
        sys.exit(f"{clean} must be empty")
    script, stats = work / "out" / "drum_solo.py", {}
    present = script.is_file() and not script.is_symlink() and script.stat().st_size > 0
    check("script_present", present, "out/drum_solo.py" if present else "no out/drum_solo.py shared")
    if present:
        grade_script(script)
        detail, mid, exited_ok = run_script(script, clean)
        check("runs", exited_ok and mid is not None, detail)
        if mid:
            try:
                mf = mido.MidiFile(mid)
            except Exception as e:
                check("midi_parses", 0, f"{type(e).__name__}: {e}")
            else:
                check("midi_parses", 1)
                grade_midi(mf, stats)
            with tempfile.TemporaryDirectory() as tmp:
                detail2, mid2, _ = run_script(script, Path(tmp))
                same = mid2 is not None and sha(mid2) == sha(mid)
                check("deterministic", same, "identical MIDI" if same
                      else "MIDI differs between runs" if mid2 else f"second run: {detail2}")

    for name, w in WEIGHTS.items():
        checks.setdefault(name, {"weight": w, "value": 0.0, "detail": "not reached"})
    total = sum(WEIGHTS.values())
    got = sum(c["weight"] * c["value"] for c in checks.values())
    print(json.dumps({"score": round(100 * got / total, 1), "checks": checks, "stats": stats}, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
