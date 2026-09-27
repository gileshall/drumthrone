#!/usr/bin/env python3
"""How it works: how a performance is turned into numbers, how to read the charts, where the numbers are weak, and how
to replicate everything.

usage: uv run python report_how.py      writes how.html into the site (pipeline.SITE)
"""
import json
from html import escape

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import pipeline
import sound
from report_corpus import (HUMAN_C, MACHINE_C, VIDEO_CSS, audio_src, fig_score_curve, fig_trust, html_of, load, page,
                           video)
from report_solo import SEQ, style

REPO_URL = "https://github.com/gileshall/drumthrone"
MUSCRIPTOR_URL = "https://muscriptor.kyutai.org"
OVERQUALIFIED = ("-UYgORr5Qhg", 0, "When you're overqualified for the job")  # (video id, start in seconds, caption)
# what each scored measurement is, and what moves it
MEANING = {
    "lra_lu": "EBU R128 loudness range of the whole solo. Wide when quiet passages alternate with loud ones.",
    "momentary_spread_lu": "Gap between the loud (95th percentile) and quiet (10th) moments of 400 ms loudness.",
    "level_iqr_db_snare": "Spread of snare hit levels, from the audio. Ghost notes and accents widen it; every "
                          "hit at one level narrows it.",
    "ioi_entropy_bits": "How varied the time between strokes is. One subdivision throughout is low; many is high.",
    "rhythm_vocab_per_block": "Each beat reduced to a 12-step pattern; the number of different patterns in every 64 "
                              "beats. Repeating the same bars lowers it. A solo under 64 beats has no full block to "
                              "count and gets no points for it.",
    "npvi": "How much each gap between strokes differs from the next. Even streams score near 0.",
    "lz_relative": "Compressibility of the sequence of one-beat patterns, compared with a shuffled copy. Loops and repeats "
                   "lower it; 1 is as unpredictable as random order.",
    "stroke_jitter_ms": "Inside steady runs, how far each stroke sits from the midpoint of its neighbors two either "
                        "side, so swing counts as feel and not as error. A quantized solo is near 0.",
    "grid_lock": "How tightly hits sit on a grid of sixteenths and triplets under the tracked beat. 1 is fully "
                 "quantized, 0 is no relation to the grid. Low for every recorded solo, as Reading the charts explains.",
    "local_ibi_cv_median": "Beat-to-beat tempo variation within 8-beat stretches. A drum machine is near 0.",
    "section_median_s": "Typical length of a section, from the boundaries of the self-similarity structure.",
    "intensity_peak_pos": "Where the most intense moment (density and loudness together) falls, as a share of the "
                          "solo.",
    "density_contrast": "How far the busiest stretches outnumber the sparsest in hits per second, relative to the "
                        "average.",
    "rest_time_frac": "Share of the solo spent in silences of half a second or more.",
    "length_s": "The MIDI file's length. Full points from 110 to 130 seconds, the same window the benchmark's grader "
                "uses, 61 points at 10 seconds outside it and 14 at 20 seconds. Scored for generated solos only.",
    "distinct_notes": "How many different drums the transcriber hears.",
    "category_entropy_bits": "How evenly hits spread across kick, snare, toms, hi-hat, ride, crash and the rest.",
    "orchestration_changes_per_min": "How often the leading drum family changes from one 2-second window to the next.",
    "hits_per_s": "Average hits per second.",
    "peak_hits_per_s": "Most hits in any one second.",
    "steady_run_share": "Share of strokes that sit inside long, even runs of singles or doubles.",
    "limb_violations_per_min": "Stroke groups (hits within 30 ms) that need more than two hands, counted in a "
                               "generated solo's own MIDI. Only too many costs points. Recorded solos get full marks on "
                               "it, since a person played them.",
}
CSS = """
table.metrics td{vertical-align:top} table.metrics td.g{font-weight:600;white-space:nowrap}
@media (max-width:700px){
table.metrics,table.metrics tbody,table.metrics tr,table.metrics td{display:block;width:auto}
table.metrics tr:first-child{display:none}
table.metrics tr{padding:8px 0;border-bottom:1px solid #eaeef2}
table.metrics td{border:0;padding:2px 0}
table.metrics td.g:empty{display:none}
table.metrics td.g{margin-top:14px;font-size:13px;text-transform:uppercase;letter-spacing:.4px;color:#57606a}
table.metrics td:nth-child(2){font-weight:600;color:#1f2328}
table.metrics td.num{text-align:left;color:#57606a}
table.metrics td.num::before{content:"Middle half of the recorded solos "}
}
.steps-list li{margin:6px 0}
pre.cmd{white-space:pre;overflow-x:auto}
"""


def pick(scores, group, key, best):
    ss = [s for s in scores["solos"] if s["group"] == group and s["metrics"].get(key) is not None]
    return (max if best == "max" else min)(ss, key=lambda s: s["metrics"][key])


def fig_pair(title_a, title_b, traces_a, traces_b, xtitle, ytitle, height=300):
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=[title_a, title_b])
    for tr in traces_a:
        fig.add_trace(tr, row=1, col=1)
    for tr in traces_b:
        fig.add_trace(tr, row=1, col=2)
    fig.update_xaxes(title_text=xtitle)
    fig.update_yaxes(title_text=ytitle, row=1, col=1)
    style(fig, height, legend=False)
    fig.update_annotations(font=dict(size=12.5))
    return fig


def grid_profile(f, sid, color):
    step = np.array(f["hits"]["step"])
    step = step[step >= 0]
    share = np.bincount(step % 12, minlength=12) / max(len(step), 1)
    return [go.Bar(x=list(range(12)), y=share, marker=dict(color=color), meta=sid,
                   hovertemplate="step %{x} of 12: %{y:.0%} of hits<extra></extra>")]


def ssm(f, sid):
    S = np.array(f["images"]["ssm"]["symbolic"], dtype=float)
    t = np.array(f["windows"]["t"], dtype=float)[:len(S)]
    return [go.Heatmap(z=S, x=t, y=t, colorscale=SEQ, zmin=0, zmax=1, showscale=False, meta=sid,
                       hovertemplate="%{x:.0f} s and %{y:.0f} s<extra></extra>")]


def tempo(f, sid, color, src):
    sb = np.array(f["beats"]["smoothed"])
    meta = {"src": src, "offset": f["clip"]["segment"][0]} if src else sid
    return [go.Scatter(x=sb[1:], y=60 / np.diff(sb), mode="lines", line=dict(width=1.5, color=color), meta=meta,
                       hovertemplate="%{x:.0f} s: %{y:.0f} BPM<extra></extra>")]


def snare_levels(f, sid, color):
    h = f["hits"]
    lv = np.array([l for l, c in zip(h["level_db"], h["cat"]) if c == "snare" and l is not None], dtype=float)
    lv = lv[np.isfinite(lv)]
    lv = lv - lv.max()
    return [go.Histogram(x=lv, xbins=dict(start=-40, end=0, size=1), marker=dict(color=color), meta=sid,
                         hovertemplate="%{x} dB: %{y} hits<extra></extra>")]


def fig_samekit_axes(sk, scores):
    """Median score on each axis: the human recordings, the same hits on the General MIDI kit, the generated solos."""
    axes = list(scores["axes"])
    gen = [s for s in scores["solos"] if s["group"] != "human"]
    fig = go.Figure()
    for name, vals, marker in (
            ("recorded solos", [np.median([r["original_axes"][a] for r in sk.values()]) for a in axes],
             dict(size=11, color=HUMAN_C, line=dict(width=1, color="white"))),
            ("the same hits on the models' kit", [np.median([r["samekit_axes"][a] for r in sk.values()]) for a in axes],
             dict(size=11, color="white", line=dict(width=2, color=HUMAN_C))),
            ("generated solos", [np.median([s["axis_scores"][a] for s in gen]) for a in axes],
             dict(size=11, color=MACHINE_C, symbol="diamond", line=dict(width=1, color="white")))):
        fig.add_trace(go.Scatter(x=vals, y=axes, mode="markers", name=name, marker=marker,
                                 hovertemplate=f"{name}, %{{y}}: median %{{x:.0f}}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=True, gridcolor="#f3f4f6")
    fig.update_xaxes(title_text="median score on the axis", range=[0, 102])
    return style(fig, 330)


def main():
    items = pipeline.snapshot()
    by_id = {it["id"]: it for it in items}
    scores = json.loads((pipeline.OUT / "scores.json").read_text())
    data = load(items)
    val = json.loads((pipeline.OUT / "validation" / "pooled.json").read_text())
    hum = [s for s in scores["solos"] if s["group"] == "human"]
    f = lambda s: data[s["id"]]["f"]
    name = lambda s: escape(s["label"])

    rows = []
    for axis, specs in scores["axes"].items():
        for k, m in enumerate(specs):
            if m["direction"] == "task":
                lo, hi = scores["length"]["window_s"]
                band = f"{lo:.0f} to {hi:.0f} s, asked for"
            else:
                b = scores["bands"][m["key"]]
                band = f"{b['p25']:.3g} to {b['p75']:.3g}"
            rows.append(f"<tr><td class='g'>{escape(axis) if k == 0 else ''}</td><td>{escape(m['label'])}</td>"
                        f"<td>{escape(MEANING[m['key']])}</td><td class='num'>{band}</td></tr>")
    metrics = ("<table class='metrics'><tr><th>group</th><th>measurement</th><th>what it is, and what moves it</th>"
               "<th>middle half of the recorded solos</th></tr>" + "".join(rows) + "</table>")

    grid_g, grid_h = pick(scores, "model", "grid_lock", "max"), pick(scores, "human", "grid_lock", "min")
    rep_g = max([s for s in scores["solos"] if s["group"] != "human"], key=lambda s: f(s)["scalars"]["rhythm_cell_repeat_rate"])
    rep_h = min(hum, key=lambda s: f(s)["scalars"]["rhythm_cell_repeat_rate"])
    tmp_g = pick(scores, "model", "local_ibi_cv_median", "min")
    wob = np.median([s["metrics"]["local_ibi_cv_median"] for s in hum])
    tmp_h = min(hum, key=lambda s: abs(s["metrics"]["local_ibi_cv_median"] - wob))  # a typical human, not an extreme
    dyn_g, dyn_h = pick(scores, "model", "level_iqr_db_snare", "min"), pick(scores, "human", "level_iqr_db_snare", "max")
    fig_grid = fig_pair(f"{name(grid_g)}: grid lock {grid_g['metrics']['grid_lock']:.2f}",
                        f"{name(grid_h)}: grid lock {grid_h['metrics']['grid_lock']:.2f}",
                        grid_profile(f(grid_g), grid_g["id"], MACHINE_C), grid_profile(f(grid_h), grid_h["id"], HUMAN_C),
                        "position in the beat", "share of hits")
    fig_grid.update_xaxes(tickvals=list(range(12)), ticktext=["beat", "", "", "e", "trip", "", "&", "", "trip", "a", "", ""])
    fig_grid.update_yaxes(tickformat=".0%")
    fig_rep = fig_pair(f"{name(rep_g)}: {f(rep_g)['scalars']['rhythm_cell_repeat_rate']:.0%} of beats repeat earlier ones",
                       f"{name(rep_h)}: {f(rep_h)['scalars']['rhythm_cell_repeat_rate']:.0%}",
                       ssm(f(rep_g), rep_g["id"]), ssm(f(rep_h), rep_h["id"]), "seconds", "seconds", height=380)
    fig_rep.update_yaxes(autorange="reversed")
    fig_tmp = fig_pair(f"{name(tmp_g)}: wobble {tmp_g['metrics']['local_ibi_cv_median']:.1%}",
                       f"{name(tmp_h)}: wobble {tmp_h['metrics']['local_ibi_cv_median']:.1%}",
                       tempo(f(tmp_g), tmp_g["id"], MACHINE_C, audio_src(by_id[tmp_g["id"]])),
                       tempo(f(tmp_h), tmp_h["id"], HUMAN_C, audio_src(by_id[tmp_h["id"]])),
                       "seconds", "beats per minute")
    fig_dyn = fig_pair(f"{name(dyn_g)}: snare spread {dyn_g['metrics']['level_iqr_db_snare']:.1f} dB",
                       f"{name(dyn_h)}: {dyn_h['metrics']['level_iqr_db_snare']:.1f} dB",
                       snare_levels(f(dyn_g), dyn_g["id"], MACHINE_C), snare_levels(f(dyn_h), dyn_h["id"], HUMAN_C),
                       "snare hit level, dB below the loudest", "hits")

    sk = json.loads((pipeline.OUT / "samekit.json").read_text())
    gen = [s for s in scores["solos"] if s["group"] != "human"]
    human_grid = [s["metrics"]["grid_lock"] for s in hum]
    step_ms = [60000 / np.median(f(s)["beats"]["ibi_bpm"]) / 12 for s in hum]  # one grid step at each solo's pulse
    drums_heard = [f(s)["scalars"]["distinct_notes"] for s in scores["solos"]]
    typical_drums, most_drums = int(np.median(drums_heard)), max(drums_heard)
    gen_grid = [s["metrics"]["grid_lock"] for s in gen]
    body = f"""<h1>How it works</h1>
<p class="sub">This page covers what gets measured, how to read the charts, the weak spots, and how to rerun
everything. With hover sound on (top right), the charts here play the solo you point at.</p>

<h2>From prompt to sound</h2>
<ol class="note steps-list">
<li>The prompt goes to each model through OpenRouter. The model answers with a Python program that uses mido.</li>
<li>The program runs alone in an empty folder inside a container with no network. If it fails, or the reply has no
program, the error goes back to the model, up to two times.</li>
<li>The MIDI file it writes is played through FluidSynth with the FluidR3 General MIDI soundfont, normalized to -27 LUFS
and saved as MP3. General MIDI fixes which note number is which drum, and a soundfont is the set of recorded samples that
plays them. Every run that produced a MIDI file is scored, whatever its length or kit.</li>
</ol>

<h2>From sound back to drum hits</h2>
<p class="note">Every solo, recorded or generated, is measured from its audio the same way.</p>
<ol class="note steps-list">
<li><b>Transcription.</b> <a href="{MUSCRIPTOR_URL}">MuScriptor</a> transcribes the audio to drum hits. It gives every note the same velocity, so how
hard each hit was comes from the audio, from the energy in that drum's frequency band right after the hit.</li>
<li><b>Timing.</b> Each stroke is snapped to the sharpest onset nearby in the audio. On generated solos, where the true
notes are known, this brings the median timing error from {val['timing_summary']['raw']['median_abs_ms']:.1f} ms to
{val['timing_summary']['refined']['median_abs_ms']:.1f} ms.</li>
<li><b>Beat.</b> A beat tracker finds the pulse. Tempo, beat-to-beat variation and position in the beat come from it.</li>
<li><b>The scored part.</b> Recorded solos often include an introduction, applause or a band. A detector marks the
solo, and the longest stretch without other instruments is scored, or a stretch set by listening where noted.
<a href="detection.html">The scored parts page</a> shows every recording.</li>
</ol>
<p class="note">On generated solos the transcriber finds {val['recall']:.0%} of the hits with the right kind of drum, and
{val['precision']:.0%} of what it reports is right. Live recordings are harder, and have no ground truth to check with.</p>
{html_of(fig_trust(data, items), 'trust')}

<h2>What gets measured</h2>
<p class="note">{sum(len(v) for v in scores['axes'].values())} measurements in seven groups. The last column is the range
covered by the middle half of the recorded solos.</p>
{video(*OVERQUALIFIED)}
{metrics}

<h2>From measurements to a score</h2>
<p class="note">Each measurement is compared with the {len(hum)} recorded solos. A value anywhere in the middle half of
the recorded values (their 25th to 75th percentile) gets 100 points. Outside it, points fall off along this curve, in
either direction, so being unusual costs points whichever way it goes. Two measurements check the task instead of
comparing with the recorded solos. Playability counts strokes that would need more than two hands, and only too many
costs points. Length is scored against the two minutes the prompt asks for. Recorded solos get full marks on both. A
group's score is the average of its measurements, the overall score is the average of the seven groups, in garths
(Groove, Accents, Rhythm, Timing and Hits), and a recorded
solo is compared with the other {len(hum) - 1}, leaving itself out.</p>
{html_of(fig_score_curve(), 'curve')}

<h2>Reading the charts</h2>
<p class="note">Each pair below is two real solos, a generated one and a recorded one, picked to show how the charts on
a solo's page change with one measurement.</p>
<h3>Position in the beat</h3>
<p class="note">Where hits land between beats. A solo locked to the grid puts almost everything on a few positions. A
drummer spreads between them. Grid lock is low for every recorded solo, {min(human_grid):.2f} to {max(human_grid):.2f},
and {min(gen_grid):.2f} to {max(gen_grid):.2f} for the generated solos. With 12 steps per beat, one step is only
{min(step_ms):.0f} to {max(step_ms):.0f} milliseconds at these tempos, so a drummer's normal timing plus a few
milliseconds of beat-tracking error spreads the hits around the grid. In practice this measurement mostly separates
quantized solos from the rest.</p>
{html_of(fig_grid, 'grid')}
<h3>Self-similarity</h3>
<p class="note">Each point compares what was played at two moments. Dark means alike. Dark squares on the diagonal are
sections, and a checkerboard is the same material coming back again and again.</p>
{html_of(fig_rep, 'rep')}
<h3>Tempo</h3>
<p class="note">Tempo beat by beat, with a typical recorded solo on the right. A program keeps exact time, so the steadiest
generated solo should be flat, and the {tmp_g['metrics']['local_ibi_cv_median']:.1%} it shows is roughly the beat
tracker's own error. The middle half of the recorded solos read
{np.percentile([s['metrics']['local_ibi_cv_median'] for s in hum], 25):.1%} to
{np.percentile([s['metrics']['local_ibi_cv_median'] for s in hum], 75):.1%}. That includes the same tracker error, which
is larger in sparse or rubato passages where the beat is hard to follow.</p>
{html_of(fig_tmp, 'tempo')}
<h3>Dynamics</h3>
<p class="note">How loud each snare hit is. Ghost notes and accents spread the hits out. Playing everything at one
velocity piles them into a spike.</p>
{html_of(fig_dyn, 'dyn')}

<h2>Known weak spots</h2>
<ul class="note">
<li><b>Recordings and renders.</b> The recorded solos are live recordings, mixed and mastered, with room sound and
often other instruments in the background. The generated solos are clean General MIDI renders. Dynamics and anything
else read from the audio are not like for like. The same-kit check below tests how much this matters.</li>
<li><b>The transcriber.</b> It misses and invents hits, names about {typical_drums} different drums in a typical solo (up
to {most_drums} of the 47 General MIDI drums), and hears phantom bass and guitar notes in pure drum recordings. The detector is tuned around
that, but not perfectly.</li>
<li><b>Unusual solos.</b> Scoring rewards being typical of these {len(hum)} solos, so an unusual solo, recorded or
generated, scores lower.</li>
<li><b>Teaching to the test.</b> Several measurements reward things a prompt can simply ask for, such as timing off the
grid or more varied rhythms.</li>
<li><b>Few runs.</b> One run per model and thinking setting in the main set, three runs per step in the hill climb, and
at least four per setting in the thinking runs. The same prompt on the same model varies by several points from run to
run.</li>
<li><b>Length.</b> Most measurements are per second or per beat, so length barely moves them. A generated solo far from
two minutes loses points on one structure measurement, and one under 64 beats gets none for rhythmic vocabulary.</li>
</ul>

<h2>Same kit, same measurements</h2>
<p class="note">This tests the first weak spot above. Each recorded solo was rebuilt as MIDI from its transcribed hits,
keeping each hit's drum, timing and loudness. The loudest hits of each drum family were set to full velocity, and a hit
that was 6 dB quieter in the recording plays 6 dB quieter on the kit. The rebuilt solos were rendered on the FluidR3 kit
the same way as a generated solo, then transcribed, measured and scored against the other {len(hum) - 1} recordings.
This removes the room, the mix and the real drums, but keeps the transcriber's mistakes from the original recording, so
it only tests the effect of the sound. The rebuilt solos have a median of
{np.median([r['samekit'] for r in sk.values()]):.0f}, and the recordings {np.median([r['original'] for r in sk.values()]):.0f}.
The chart shows the median of each group of measurements.</p>
{html_of(fig_samekit_axes(sk, scores), 'samekit_axes')}

<h2 id="replicate">Replicate it</h2>
<p class="note">Everything is in <a href="{REPO_URL}">the GitHub repository</a>: the benchmark harness and prompt, every
generated program with its MIDI, grade and transcript, the hill-climb and thinking runs, the analysis and scoring code,
and this site's code. The recordings are not included, since they belong to their owners. The repository's
manifest lists where each one comes from, and each goes in <code>human_solos/</code> as an MP3.</p>
<pre class="cmd">git clone {REPO_URL} && cd drumthrone
docker build -t drumbench .                     # sandbox, grader and renderer
docker run --rm drumbench cat /usr/share/sounds/sf2/FluidR3_GM.sf2 > assets/FluidR3_GM.sf2
cd analysis
uv run python pipeline.py render transcribe bracket features validate score   # the main set and the recorded solos
uv run python hillclimb.py render               # render the hill-climb and thinking runs
uv run python hillclimb.py score                # transcribe, measure and score them
uv run python samekit.py                        # the recorded solos rebuilt on the General MIDI kit
uv run python pipeline.py pages                 # the site, in analysis/out</pre>
<p class="note">New runs need an OpenRouter key. <code>bench.py</code> generates solos
(<code>--mode chat --chat-repairs 2 --max-cost 50</code> matches these runs), and <code>analysis/hillclimb.py gen</code>
runs a prompt or thinking sweep. A recording from another source or encoding can move the recorded solos' numbers slightly.</p>"""
    out = pipeline.SITE / "how.html"
    out.write_text(page("How it works", body, css=VIDEO_CSS + CSS, tail=sound.tags(), here="how.html"))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
