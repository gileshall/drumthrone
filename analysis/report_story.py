#!/usr/bin/env python3
"""The main page: is writing a drum solo a good benchmark for language models? Tested by hill climbing its score, with
recorded human solos as reference points.

usage: uv run python report_story.py      writes index.html into the site (pipeline.SITE)
"""
import json
import shutil
import urllib.parse
from html import escape
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import drums
import pipeline
import sound
import report_thinking as thinking
from hillclimb import HC, RESULTS
from report_corpus import (HUMAN_BAND, HUMAN_C, HUMAN_LIGHT, MACHINE_C, VIDEO_CSS, audio_src, html_of, model_name, page,
                           video)
from report_solo import BRONZE, INK, INK2, MUTED, style
from score import AXES

HERE = Path(__file__).resolve().parent
NO_EMBED = set()  # recordings whose uploader blocks embedding (YouTube oEmbed 401): linked, never embedded
MODELS = ["claude-opus-5.5", "gemini-3.1-pro-preview", "deepseek-v4.1-flash"]
# the prompt hill climb in the order tried: (run tag, chart label, what changed)
STEPS = [
    ("p0", "start", "The benchmark prompt, unchanged."),
    ("p1", "flow", "Adds two bullets, one about runs and fills that flow around the kit and one about time that breathes like a live performance."),
    ("p2", "pacing", "Adds two bullets instead, one about pacing it like a showcase solo and landing the ending and one about shaping dynamics inside phrases."),
    ("p3", "flow + pacing", "All four bullets from the two previous steps."),
    ("p4", "+ kit first", "Flow + pacing, with the percussion bullet changed so the drum kit carries the solo and the rest of the "
                          "percussion set is color."),
    ("p5", "+ real-time feel", "Flow + pacing, with the breathing-time and feel bullets replaced by one about playing the way a "
                               "person performs in real time, off the quantized grid."),
    ("p6", "final", "Real-time feel, plus kit first, plus a new bullet about inventing and rarely playing the same bar twice."),
]
ROUND_TWO = 4  # steps from here on start from "flow + pacing"
COLORS = thinking.COLORS
REPO_URL = "https://github.com/gileshall/drumthrone"
MUSCRIPTOR_URL = "https://muscriptor.kyutai.org"
# embedded YouTube players: (video id, start in seconds, caption)
GARTH = ("8Qi3JERmk9E", 68, "Garth likes to play, Wayne's World (1992)")
ANIMAL = ("3AZz9TSjZCM", 22, "Dave Grohl and Animal drum battle, The Muppets")
# measurements that a line added by the hill climb asks for almost word for word, with the words
ASKED = {
    "steady_run_share": "long runs of singles and doubles",
    "orchestration_changes_per_min": "travel around the kit",
    "intensity_peak_pos": "keep the energy alive all the way through and land the final hit",
    "level_iqr_db_snare": "accents, ghost notes and crescendos",
    "local_ibi_cv_median": "the pulse surges and settles",
    "grid_lock": "rather than on a quantized grid",
    "stroke_jitter_ms": "notes land where a drummer's hands put them",
    "rhythm_vocab_per_block": "rarely plays the same bar twice",
    "lz_relative": "rarely plays the same bar twice",
    "category_entropy_bits": "The drum kit carries the solo",
}
CSS = """
h1{font-size:40px;letter-spacing:-0.5px;margin-bottom:0}
.subtitle{font-size:19px;color:#57606a;margin:2px 0 8px}
.byline{font-size:14px;color:#57606a;margin:0 0 6px;letter-spacing:.2px}
.video.break{margin:56px auto 0;max-width:560px}
p.essay{font-size:16.5px;line-height:1.6;color:#1f2328}
.hero{display:grid;grid-template-columns:1fr 340px;gap:28px;align-items:center;margin:0 0 6px}
.hero .video{margin:0}
@media (max-width:760px){.hero{grid-template-columns:1fr}}
.embeds{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin:10px 0}
.embeds figure{margin:0} .embeds iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:8px}
.embeds figcaption{font-size:13px;color:#57606a;margin-top:4px}
.tldr{border-left:4px solid #b8860b;background:#fbf8f1;border-radius:0 8px 8px 0;padding:10px 18px;margin:18px 0 8px;
font-size:15px} .tldr ul{margin:6px 0 2px;padding-left:20px} .tldr li{margin:4px 0}
.caveat{border:1px solid #d4a72c;background:#fff8e5;border-radius:8px;padding:10px 16px;margin:16px 0;font-size:14.5px}
table.listen{width:100%} table.listen td,table.listen th{padding:6px 12px;vertical-align:middle}
table.listen audio{width:230px;height:32px;display:block}
@media (max-width:700px){
table.listen,table.listen tbody,table.listen tr,table.listen td{display:block;width:auto}
table.listen tr:first-child,table.listen td.num{display:none}
table.listen tr{border-bottom:1px solid #eaeef2;padding:10px 0}
table.listen td{border:0;padding:3px 0}
table.listen td[data-label]::before{content:attr(data-label);display:block;font-size:13px;color:#57606a;margin-bottom:2px}
table.listen audio{width:100%}
}
table.steps{width:100%} table.steps td{vertical-align:top}
details{font-size:14px;margin:8px 0}
"""


def load_climb():
    recs = [r for r in json.loads(RESULTS.read_text()) if r["tag"] in {t for t, *_ in STEPS} and not r["error"]]
    for r in recs:
        r["name"] = r["model"].split("/")[1]
    missing = [(t, m) for t, *_ in STEPS for m in MODELS
               if not any(r["tag"] == t and r["name"] == m and not r["failed"] for r in recs)]
    if missing:
        raise SystemExit(f"hill climb steps without a scored run: {missing}")
    return recs


def scored(recs, tag, model):
    return [r for r in recs if r["tag"] == tag and r["name"] == model and not r["failed"]]


def step_mean(recs, tag):
    """The average of the three models' mean scores at one step."""
    return float(np.mean([np.mean([r["overall"] for r in scored(recs, tag, m)]) for m in MODELS]))


def fresh_runs(think, climb):
    """Each model's thinking runs of the final prompt at the setting that thought about as much as the model's default
    did in the climb (median reasoning tokens): a fresh rerun of the climb's last step."""
    out = {}
    for m in MODELS:
        default = np.median([r["reasoning_tokens"] or 0 for r in scored(climb, "p6", m)])
        levels = {lv: [r for r in think if r["name"] == m and r["thinking"] == lv and not r["failed"]]
                  for lv in thinking.LEVELS[m]}
        lv = min(levels, key=lambda v: abs(np.log1p(np.median([r["reasoning_tokens"] or 0 for r in levels[v]]))
                                           - np.log1p(default)))
        out[m] = (lv, levels[lv])
    return out


def fig_climb(recs, human, fresh):
    """Score at each step of the prompt hill climb (every run, each model's mean, the three models' average), then the
    final prompt's fresh runs."""
    fig = go.Figure()
    fig.add_hrect(y0=human[0], y1=human[2], fillcolor=HUMAN_BAND, line_width=0, layer="below")
    fig.add_vline(x=ROUND_TWO - 0.5, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_vline(x=len(STEPS) - 0.5, line=dict(color=MUTED, width=1, dash="dot"))
    for x, text in ((1.5, "round 1: from the start"), (5, "round 2: from flow + pacing")):
        fig.add_annotation(x=x, y=0.99, yref="paper", text=text, showarrow=False, yanchor="top", font=dict(size=11, color=INK2))
    x = list(range(len(STEPS)))
    means, fresh_means = [], []
    for k, m in enumerate(MODELS):
        runs = [scored(recs, t, m) for t, *_ in STEPS] + [fresh[m][1]]
        vals = [[r["overall"] for r in rs] for rs in runs]
        rng = np.random.default_rng(k)
        fig.add_trace(go.Scatter(x=[i + d for i, v in enumerate(vals) for d in rng.uniform(-0.12, 0.12, len(v))],
                                 y=[y for v in vals for y in v], mode="markers", showlegend=False, legendgroup=m,
                                 meta=[sound.run_id(r) for rs in runs for r in rs],
                                 marker=dict(size=7, color=COLORS[m], opacity=0.55),
                                 hovertemplate=f"{m}: %{{y:.0f}}<extra></extra>"))
        mean = [float(np.mean(v)) for v in vals]
        means.append(mean[:-1])
        fresh_means.append(mean[-1])
        fig.add_trace(go.Scatter(x=x, y=mean[:-1], mode="lines+markers", name=m, legendgroup=m,
                                 line=dict(width=2, color=COLORS[m]), marker=dict(size=6, color=COLORS[m]),
                                 hovertemplate=f"{m} mean %{{y:.1f}}<extra></extra>"))
        fig.add_trace(go.Scatter(x=[len(STEPS) - 1, len(STEPS)], y=[mean[-2], mean[-1]], mode="lines+markers",
                                 showlegend=False, legendgroup=m, line=dict(width=2, color=COLORS[m], dash="dot"),
                                 marker=dict(size=[6, 9], color=["rgba(0,0,0,0)"] * 2, line=dict(width=2, color=COLORS[m])),
                                 hovertemplate=f"{m}, fresh runs at {fresh[m][0]} thinking: mean %{{y:.1f}}<extra></extra>"))
    avg = np.mean(means, axis=0)
    fig.add_trace(go.Scatter(x=x, y=avg, mode="lines+markers", name="average of the three",
                             line=dict(width=4, color=INK), marker=dict(size=8, color=INK),
                             hovertemplate="average %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[len(STEPS) - 1, len(STEPS)], y=[avg[-1], np.mean(fresh_means)], mode="lines+markers",
                             showlegend=False, line=dict(width=3, color=INK, dash="dot"),
                             marker=dict(size=[8, 12], color=["rgba(0,0,0,0)"] * 2, line=dict(width=3, color=INK)),
                             hovertemplate="average of the fresh runs %{y:.1f}<extra></extra>"))
    fig.add_annotation(xref="paper", x=0, y=human[2], text="middle half of the recorded solos", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(size=11, color=INK2))
    fig.update_xaxes(tickvals=x + [len(STEPS)], ticktext=[label for _, label, _ in STEPS] + ["final, fresh runs"],
                     range=[-0.5, len(STEPS) + 0.5])
    fig.update_yaxes(title_text="garths", range=[40, 100])
    style(fig, 440)
    fig.update_layout(margin=dict(t=64))
    return fig


def gains(recs):
    """Where the climb's points came from: each measurement's share of the overall score (its points, over the number
    of measured metrics on its axis and the number of axes), from the benchmark prompt to the final one, per model and
    then averaged. The shares add up to the change in the overall score."""
    def share(r, key, axis):
        n = sum(1 for k, *_ in AXES[axis] if k in r["metric_scores"])
        return r["metric_scores"].get(key, 0.0) / n / len(AXES)
    rows = []
    for axis, specs in AXES.items():
        for key, label, *_ in specs:
            d = np.mean([np.mean([share(r, key, axis) for r in scored(recs, "p6", m)])
                         - np.mean([share(r, key, axis) for r in scored(recs, "p0", m)]) for m in MODELS])
            rows.append({"key": key, "label": label, "axis": axis, "change": float(d), "asked": ASKED.get(key)})
    return rows


def fig_gains(rows):
    rows = sorted(rows, key=lambda r: r["change"])
    fig = go.Figure()
    for asked, color, name in ((True, BRONZE, "asked for by a line added in the climb"), (False, HUMAN_LIGHT, "not asked for")):
        rs = [r for r in rows if bool(r["asked"]) == asked]
        fig.add_trace(go.Bar(x=[r["change"] for r in rs], y=[r["label"] for r in rs], orientation="h", name=name,
                             marker=dict(color=color),
                             customdata=[[r["axis"], f"asked for: “{r['asked']}”" if r["asked"] else ""] for r in rs],
                             hovertemplate="%{customdata[0]}: %{x:+.1f} points<br>%{customdata[1]}<extra></extra>"))
    fig.update_yaxes(categoryorder="array", categoryarray=[r["label"] for r in rows], showgrid=False)
    fig.update_xaxes(title_text="garths gained from the start to the final prompt", zeroline=True,
                     zerolinecolor=MUTED)
    style(fig, 90 + 22 * len(rows))
    fig.update_layout(barmode="overlay")
    return fig


def median_run(recs, tag, model):
    rs = sorted(scored(recs, tag, model), key=lambda r: r["overall"])
    return rs[len(rs) // 2]


def publish(src, rel):
    dst = pipeline.SITE / rel
    if pipeline.stale(dst, src):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return rel


def listening(recs):
    """Each model's middle run of three on the start prompt and on the final prompt, copied into the site."""
    rows = []
    for m in MODELS:
        cells = []
        for tag, label in (("p0", "start"), ("p6", "final")):
            r = median_run(recs, tag, m)
            rel = publish(pipeline.ROOT / r["dir"] / "solo.mp3", f"audio/prompt/{m}_{label}.mp3")
            head = "benchmark prompt" if tag == "p0" else "after hill climbing"
            cells.append(f"<td data-label='{head}, {r['overall']:.0f} garths'><audio controls preload='none' src='{rel}'>"
                         f"</audio></td><td class='num'>{r['overall']:.0f}</td>")
        rows.append(f"<tr><td style='color:{COLORS[m]};font-weight:600'>{escape(m)}</td>{''.join(cells)}</tr>")
    return ("<table class='listen'><tr><th></th><th>benchmark prompt</th><th>score</th><th>after hill climbing</th>"
            "<th>score</th></tr>" + "".join(rows) + "</table>")


ROLL = ["other", "crash", "ride", "hi-hat", "toms", "snare", "kick"]  # top to bottom, as on a drum chart
ROLL_NAMES = {"other": "other percussion", "crash": "crash", "ride": "ride", "hi-hat": "hi-hat", "toms": "toms",
              "snare": "snare", "kick": "kick"}
WINDOW = 12.0


def window(f):
    """WINDOW seconds around a solo's most intense moment, kept inside the solo."""
    dur = f["scalars"]["duration_s"]
    mid = f["scalars"]["intensity_peak_pos"] * dur
    a = min(max(0.0, mid - WINDOW / 2), max(0.0, dur - WINDOW))
    return a, a + WINDOW


def fig_drumroll(panels):
    """Every hit in a short stretch of each solo, one row per part of the kit, bigger for louder."""
    fig = make_subplots(rows=len(panels), cols=1, shared_xaxes=True, vertical_spacing=0.09,
                        subplot_titles=[title for title, *_ in panels])
    for k, (title, f, (a, b), src) in enumerate(panels, 1):
        h = f["hits"]
        t, cat, lvl = np.array(h["t"]), np.array([c if c in ROLL[1:] else "other" for c in h["cat"]]), np.array(h["level_db"], dtype=float)
        lo, hi = np.nanpercentile(lvl, [5, 95])
        size = 3 + 10 * np.clip((lvl - lo) / (hi - lo), 0, 1)
        sel = (t >= a) & (t < b)
        for c in ROLL:
            m = sel & (cat == c)
            fig.add_trace(go.Scatter(x=t[m] - a, y=[ROLL_NAMES[c]] * int(m.sum()), mode="markers", showlegend=False,
                                     meta={"src": src, "offset": f["clip"]["segment"][0] + a} if src else None,
                                     marker=dict(size=size[m], color=drums.COLORS[c], opacity=0.85, line=dict(width=0)),
                                     hovertemplate=f"{ROLL_NAMES[c]} at %{{x:.2f}} s<extra></extra>"), row=k, col=1)
        fig.update_yaxes(categoryorder="array", categoryarray=[ROLL_NAMES[c] for c in reversed(ROLL)], showgrid=False,
                         row=k, col=1)
    fig.update_xaxes(range=[-0.1, WINDOW + 0.1], showgrid=False)
    fig.update_xaxes(title_text="seconds", row=len(panels), col=1)
    style(fig, 190 * len(panels), legend=False)
    fig.update_annotations(font=dict(size=13, color=INK), xanchor="left", x=0)
    return fig


def swarm(xs, gap):
    """Rows for a one-line dot plot: each dot takes the nearest row with no other dot within gap."""
    placed, rows = [], []
    for x in xs:
        y = next(y for y in (0, 1, -1, 2, -2, 3, -3, 4, -4)
                 if all(abs(x - px) >= gap for px, py in placed if py == y))
        placed.append((x, y))
        rows.append(y)
    return rows


def fig_humans(scores):
    """The recorded performances on the overall scale, names on hover only. Hovering plays them in the local build, where
    the recordings are hosted."""
    hum = sorted([s for s in scores["solos"] if s["group"] == "human"], key=lambda s: s["overall"])
    hv = [s["overall"] for s in hum]
    ys = swarm(hv, 1.2)
    fig = go.Figure()
    fig.add_vrect(x0=np.percentile(hv, 25), x1=np.percentile(hv, 75), fillcolor=HUMAN_BAND, line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=hv, y=ys, mode="markers", customdata=[s["label"] for s in hum],
                             meta=[s["id"] for s in hum], marker=dict(size=13, color=HUMAN_C, line=dict(width=1, color="white")),
                             hovertemplate="%{customdata}: %{x:.0f} garths<extra></extra>"))
    fig.add_annotation(xref="x", x=float(np.median(hv)), yref="paper", y=1, text="middle half", showarrow=False,
                       yanchor="bottom", font=dict(size=11, color=INK2))
    fig.update_yaxes(visible=False, range=[min(ys) - 1, max(ys) + 1])
    fig.update_xaxes(title_text="garths", range=[min(hv) - 4, 100])
    return style(fig, 110 + 22 * (max(ys) - min(ys) + 1), legend=False)


def fig_models(scores, items):
    """Every generated solo on the benchmark prompt, one run each, against the middle half of the human solos."""
    by_id = {s["id"]: s for s in scores["solos"]}
    gen = sorted([it for it in items if it["group"] != "human"], key=lambda it: by_id[it["id"]]["overall"])
    names = [model_name(it) for it in gen]
    ticks = [n for n, _, _ in names]
    if len(set(ticks)) != len(ticks):
        raise SystemExit("two generated solos share a display name")
    hv = [s["overall"] for s in scores["solos"] if s["group"] == "human"]
    fig = go.Figure()
    fig.add_vrect(x0=np.percentile(hv, 25), x1=np.percentile(hv, 75), fillcolor=HUMAN_BAND, line_width=0, layer="below")
    fig.add_annotation(x=float(np.median(hv)), y=1, yref="paper", text="middle half of the recorded solos", showarrow=False,
                       yanchor="bottom", font=dict(size=11, color=INK2))
    fig.add_trace(go.Scatter(x=[by_id[it["id"]]["overall"] for it in gen], y=ticks, mode="markers",
                             marker=dict(size=10, color=MACHINE_C, line=dict(width=1, color="white")),
                             customdata=[[maker, n.split(" · ")[0], setting] for n, maker, setting in names],
                             meta=[it["id"] for it in gen],
                             hovertemplate="%{customdata[0]} %{customdata[1]}, thinking: %{customdata[2]}<br>"
                                           "%{x:.0f} garths<extra></extra>"))
    fig.update_yaxes(showgrid=True, gridcolor="#f3f4f6")
    fig.update_xaxes(title_text="garths (one run each)", range=[20, 100])
    style(fig, 80 + 21 * len(gen), legend=False)
    fig.update_layout(margin=dict(t=30))
    return fig, {t: it["id"] for t, it in zip(ticks, gen)}


def fig_samekit(sk, scores):
    """Each human performance as recorded and rebuilt on the models' kit, joined, with the generated solos below."""
    by_id = {s["id"]: s for s in scores["solos"]}
    ids = sorted(sk, key=lambda i: sk[i]["original"])
    gen = [s for s in scores["solos"] if s["group"] != "human"]
    rec, kit = [sk[i]["original"] for i in ids], [sk[i]["samekit"] for i in ids]
    fig = go.Figure()
    fig.add_vrect(x0=np.percentile(rec, 25), x1=np.percentile(rec, 75), fillcolor=HUMAN_BAND, line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=[v for a, b in zip(rec, kit) for v in (a, b, None)], y=[v for _ in ids for v in (2, 1, None)],
                             mode="lines", line=dict(width=1, color=HUMAN_LIGHT), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=rec, y=[2] * len(ids), mode="markers", customdata=[by_id[i]["label"] for i in ids], meta=ids,
                             marker=dict(size=10, color=HUMAN_C, line=dict(width=1, color="white")),
                             hovertemplate="%{customdata}, the recording: %{x:.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=kit, y=[1] * len(ids), mode="markers", customdata=[by_id[i]["label"] for i in ids],
                             meta=[f"samekit-{i}" for i in ids],
                             marker=dict(size=10, color="white", line=dict(width=2, color=HUMAN_C)),
                             hovertemplate="%{customdata}, rebuilt on the General MIDI kit: %{x:.0f}<extra></extra>"))
    gv = [s["overall"] for s in gen]
    fig.add_trace(go.Scatter(x=gv, y=np.zeros(len(gv)) + np.random.default_rng(5).uniform(-0.15, 0.15, len(gv)),
                             mode="markers", customdata=[model_name({"model": s["model"]})[0] for s in gen],
                             meta=[s["id"] for s in gen], marker=dict(size=8, color=MACHINE_C, opacity=0.8,
                                                                      line=dict(width=1, color="white")),
                             hovertemplate="%{customdata}: %{x:.0f}<extra></extra>"))
    fig.update_yaxes(tickvals=[2, 1, 0], ticktext=["recorded solos", "the same hits on the models' kit",
                                                   "generated solos"], range=[-0.5, 2.5], showgrid=False)
    fig.update_xaxes(title_text="overall score", range=[20, 100])
    return style(fig, 230, legend=False)


def embeds(items, ids):
    """Embedded players for a few human recordings, each starting where its scored part starts."""
    by_id = {it["id"]: it for it in items}
    cells = []
    for i in ids:
        it = by_id[i]
        video = urllib.parse.parse_qs(urllib.parse.urlparse(it["url"]).query)["v"][0]
        a, _ = pipeline.best_chunk(it)
        cells.append(f"<figure><iframe src='https://www.youtube-nocookie.com/embed/{video}?start={int(a)}' "
                     f"title='{escape(it['label'])}' loading='lazy' allow='encrypted-media; picture-in-picture' "
                     f"allowfullscreen></iframe><figcaption>{escape(it['label'])}</figcaption></figure>")
    return f"<div class='embeds'>{''.join(cells)}</div>"


def listing(xs):
    xs = [f"{x:.0f}" for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def main():
    scores = json.loads((pipeline.OUT / "scores.json").read_text())
    sk = json.loads((pipeline.OUT / "samekit.json").read_text())
    items = pipeline.snapshot()
    hum = [s for s in scores["solos"] if s["group"] == "human"]
    gen = [s for s in scores["solos"] if s["group"] != "human"]
    if set(sk) != {s["id"] for s in hum}:
        raise SystemExit("samekit.json is not for the current human solos: run samekit.py")
    hv, gv = [s["overall"] for s in hum], [s["overall"] for s in gen]
    n_models = len({model_name(it)[0].split(" · ")[0] for it in items if it["group"] != "human"})
    human, _ = thinking.human_reference()
    climb = load_climb()
    p6_text = (HC / "prompts" / "p6.md").read_text()
    unquoted = [w for w in ASKED.values() if w not in p6_text]
    if unquoted:
        raise SystemExit(f"not in the final prompt: {unquoted}")
    p0, p6 = step_mean(climb, "p0"), step_mean(climb, "p6")
    spread = float(np.median([np.std([r["overall"] for r in scored(climb, t, m)], ddof=1) for t, *_ in STEPS for m in MODELS]))
    runs_per_step = min(len(scored(climb, t, m)) for t, *_ in STEPS for m in MODELS)
    think = thinking.load("t6")
    think_mean = lambda m, lv: np.mean([r["overall"] for r in think if r["name"] == m and r["thinking"] == lv and not r["failed"]])
    top = [r for r in think if r["name"] == "claude-opus-5.5" and r["thinking"] in ("xhigh", "max") and not r["failed"]]
    maxed = sum(1 for r in top if r["turns"] > 1)
    maxed_text = f"all {len(top)} runs" if maxed == len(top) else f"{maxed} of the {len(top)} runs"
    per_setting = min(sum(1 for r in think if r["name"] == m and r["thinking"] == lv)
                      for m in MODELS for lv in thinking.LEVELS[m])
    off = sorted(r["length"] for r in think if r["name"] == "deepseek-v4.1-flash" and r["thinking"] == "off")
    short = [x for x in off if x < 110]
    fresh = fresh_runs(think, climb)
    fresh_mean = float(np.mean([np.mean([r["overall"] for r in fresh[m][1]]) for m in MODELS]))
    rows = gains(climb)
    asked_gain = sum(r["change"] for r in rows if r["asked"])
    total_gain = sum(r["change"] for r in rows)
    n_metrics = sum(len(specs) for specs in scores["axes"].values())
    steps = "".join(f"<tr><td><b>{escape(label)}</b></td><td>{escape(what)}</td></tr>" for _, label, what in STEPS)
    orig, kit = np.array([r["original"] for r in sk.values()]), np.array([r["samekit"] for r in sk.values()])
    gem_main = next(s for s in gen if s["model"] == "google/gemini-3.1-pro-preview")["overall"]
    gem_climb = float(np.mean([r["overall"] for r in scored(climb, "p0", "gemini-3.1-pro-preview")]))
    fig_m, model_labels = fig_models(scores, items)

    by_id = {it["id"]: it for it in items}
    buddy_it = by_id["buddy_rich-impossible_drum_solo"]
    buddy = json.loads((pipeline.OUT / buddy_it["id"] / "features.json").read_text())
    best = max(gen, key=lambda s: s["overall"])
    fbest = json.loads((pipeline.OUT / best["id"] / "features.json").read_text())
    roll_models = fig_drumroll([("Buddy Rich, the Impossible Drum Solo", buddy, window(buddy), audio_src(buddy_it)),
                                (f"{model_name(by_id[best['id']])[0]}, the top generated solo", fbest, window(fbest),
                                 audio_src(by_id[best["id"]]))])
    c0, c6 = (median_run(climb, t, "claude-opus-5.5") for t in ("p0", "p6"))
    f0, f6 = (json.loads((HC / "work" / "__".join(r["dir"].split("/")[2:]) / "features.json").read_text()) for r in (c0, c6))
    roll_climb = fig_drumroll([("Claude Opus 5.5, benchmark prompt", f0, window(f0), "audio/prompt/claude-opus-5.5_start.mp3"),
                               ("Claude Opus 5.5, after hill climbing the prompt", f6, window(f6),
                                "audio/prompt/claude-opus-5.5_final.mp3")])
    low = min(hum, key=lambda s: s["overall"])
    mid = min([s for s in hum if s["id"] not in NO_EMBED], key=lambda s: abs(s["overall"] - np.median(hv)))
    high = max(hum, key=lambda s: s["overall"])
    listen_table = listening(climb)

    body = f"""<header class="hero"><div>
<h1>Drum Throne</h1>
<p class="subtitle">An experimental benchmark composing drum solos with language models</p>
<p class="byline">Giles Hall</p>
</div>{video(*GARTH)}</header>
<div class="tldr"><b>TL;DR</b><ul>
<li>Drum Throne asks language models to write a program that composes a two-minute drum solo, and scores each solo
against {len(hum)} recorded drum solos performed by professional drummers.</li>
<li>Is this a good benchmark? Well, can it be used to hill climb? Here are human reference points for
calibration.</li>
<li>The scoring system is not a well calibrated system to judge drum solos. It is an ad hoc approximation that considers
factors like complexity, dynamics, etc. Please take everything here with a grain of salt.</li>
<li>Point at or tap the dot or name of a generated solo to hear it. <button class="sound-cta">Turn on hover sound</button></li>
</ul></div>

<h2>Why drum solos rule</h2>
<p class="essay">A drum solo is the exposé of a drummer emptying their pockets and putting it all out there. It's the
musicality that springs out of an instrument that people only think about in terms of keeping a beat. And the complexity of a
drum solo can tell you about the person behind the drum sticks. You can see that in the data, and you can also hear it
with your own ears.</p>

<h3>Hearing the scale</h3>
<p class="note">The aim is to measure and evaluate drum solos, letting people hear the scale. Each of the
{len(hum)} recorded solos is measured {n_metrics} ways, grouped into dynamics, rhythm, feel, structure, orchestration,
energy and playability. A measurement in the middle half of the recorded solos gets full points, and fewer the further
outside it falls. The overall score is the average of the seven group scores, in garths (Groove, Accents, Rhythm,
Timing and Hits), and each recorded solo is scored against the other
{len(hum) - 1}.
Point at a dot to see whose it is.</p>
{html_of(fig_humans(scores), 'humans')}
<p class="note">Three points on the scale are {escape(high['label'])} at the top ({high['overall']:.0f} garths),
{escape(mid['label'])} near the middle ({mid['overall']:.0f}) and {escape(low['label'])} at the bottom
({low['overall']:.0f}). All {len(hum)} are world class drummers and that's not in question. This is evaluating a single
performance with all the caveats about that recording that go along with it. Among players like these the numbers say
little about quality. A low score says more about how unusual a solo is within this set than about the playing.</p>
{embeds(items, [high["id"], mid["id"], low["id"]])}
<p class="note"><a href="how.html">How it works</a> has every measurement and the weak spots.</p>

<h2>How the language models do</h2>
<p class="note">Every model gets the same prompt.</p>
<details><summary>The benchmark prompt</summary><pre>{escape(pipeline.PROMPT.read_text())}</pre></details>
<p class="note">Each model answers with a Python program. It runs in a sandbox, and if it breaks, the error goes back to
the model, up to two times. The MIDI file it writes is played through FluidR3, a free General MIDI soundfont.</p>
<p class="note">{len(gen)} solos from {n_models} models, one run each. The word after the · (as in Claude Opus 5.5 · max)
is the thinking setting, and a name without one used the provider's default.</p>
{html_of(fig_m, 'overall')}
<p class="note">The same model on the same prompt varies by about {spread:.0f} garths from run to run. Gemini 3.1 Pro
scored {gem_main:.0f} here, and three more runs of the same prompt in the hill climb below averaged {gem_climb:.0f}.</p>

<h2>How thinking affects the outcome</h2>
<p class="note">The same three models as the hill climb ran at every thinking setting they offer, at least {per_setting}
times each, with the final prompt from the next section.</p>
<p class="note">Claude Opus 5.5 scored {think_mean('claude-opus-5.5', 'low'):.0f} garths at low,
{think_mean('claude-opus-5.5', 'high'):.0f} at high, and {think_mean('claude-opus-5.5', 'xhigh'):.0f} and
{think_mean('claude-opus-5.5', 'max'):.0f} at its two top settings, where {maxed_text} used up the 128,000-token output
limit thinking and had to be asked again. With thinking off, DeepSeek scored
{think_mean('deepseek-v4.1-flash', 'off'):.0f}, and {len(short)} of its {len(off)} solos were well short of two minutes.
With thinking on at its lowest setting, it scored {think_mean('deepseek-v4.1-flash', 'low'):.0f}. <a href="thinking.html">The thinking
page</a> has all of these solos.</p>
{html_of(thinking.fig_score(think, human), 'thinking')}

<h2>Hill climbing the prompt</h2>
<p class="note">Hill climbing means changing the prompt a little at a time and keeping the changes that raise the score.
The prompt was rewritten in six steps over two rounds, with {runs_per_step} runs per step on each of three models.</p>
{html_of(fig_climb(climb, human, fresh), 'climb')}
<p class="note">The average went from {p0:.0f} to {p6:.0f} garths. Runs vary by about {spread:.0f}, and the climb used
each model's default thinking. The final prompt was run again, fresh, in the thinking runs, and at the setting closest to
that default it averaged {fresh_mean:.0f}. {asked_gain:.0f} of the {total_gain:.0f} garths came from measurements that
the new lines in the prompt ask for directly, like not repeating bars.</p>
<details><summary>What changed at each step, and the final prompt</summary><table class="steps">{steps}</table>
<pre>{escape(p6_text)}</pre></details>
<h3>Before and after</h3>
<p class="note">The middle run of three for each model, on the first and the final prompt.</p>
{listen_table}

{video(*ANIMAL, cls="video break")}

<h2>More</h2>
<ul class="note">
<li><a href="how.html">How it works</a>, with how a performance is measured, how to read the charts, and the known weak spots.</li>
<li><a href="measurements.html">All measurements</a>, with every solo's scores and the charts behind them.</li>
<li><a href="thinking.html">Thinking settings</a>, with charts and every solo from the thinking runs.</li>
<li><a href="detection.html">The scored part of each recording</a>, with how intros, applause and band sections were left out.</li>
<li><a href="graph.html">Similarity graph</a>, with solos joined to their most similar solos.</li>
<li><a href="{REPO_URL}">The GitHub repository</a>, with everything needed to rerun it.</li>
</ul>
<script>
// charts inside a closed <details> are drawn at zero width; redraw them when it opens
document.querySelectorAll("details").forEach(d => d.addEventListener("toggle", () =>
  d.querySelectorAll(".js-plotly-plot").forEach(p => Plotly.Plots.resize(p))));
const players = [...document.querySelectorAll("audio")];
players.forEach(p => p.addEventListener("play", () => players.forEach(o => {{ if (o !== p) o.pause(); }})));
</script>"""
    out = pipeline.SITE / "index.html"
    out.write_text(page("Drum Throne: An experimental benchmark composing drum solos with language models", body,
                        css=VIDEO_CSS + CSS, tail=sound.tags(labels=model_labels), here="index.html",
                        description=f"Language models write two-minute drum solos, measured against {len(hum)} recorded "
                                    "drum solos, with a thinking sweep and a hill climb of the prompt."))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
