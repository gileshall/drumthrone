#!/usr/bin/env python3
"""The thinking sweep: how much a model thinks against how its drum solo scores, plans and sounds.

usage: uv run python report_thinking.py [tag]   (default tag: t6)   writes thinking.html into the site (pipeline.SITE)
"""
import json
import re
import shutil
import sys
from collections import Counter
from html import escape

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy import ndimage

import pipeline
import sound
from hillclimb import HC, RESULTS, WORK
from report_corpus import page
from report_solo import CONFIG, GRID, INK, INK2, MUTED, style

LEVELS = {"claude-opus-5.5": ["low", "medium", "high", "xhigh", "max"],
          "gemini-3.1-pro-preview": ["low", "medium", "high"],
          "deepseek-v4.1-flash": ["off", "low", "high", "max"]}
COLORS = {"claude-opus-5.5": "#0072B2", "gemini-3.1-pro-preview": "#D55E00", "deepseek-v4.1-flash": "#009E73"}
HUMAN_BAND = "rgba(87,96,106,0.14)"
PLAN = [("n_sections", "Sections", "how many distinct sections the solo falls into"),
        ("section_median_s", "Section length", "seconds spent in a typical section before moving on"),
        ("rhythm_vocab_per_block", "Rhythmic vocabulary", "distinct one-beat rhythms in every 64 beats"),
        ("rhythm_cell_repeat_rate", "Reuse", "share of beats that repeat a rhythm heard earlier in the solo"),
        ("lz_relative", "Pattern complexity",
         "how compressible the sequence of rhythms is, compared with a shuffled copy, where 1 is as unpredictable as random order"),
        ("intensity_peak_pos", "Where the climax falls",
         "the most intense moment (density and loudness together), as a fraction of the way through"),
        ("grid_lock", "Grid lock", "how tightly hits sit on a grid of sixteenths and triplets, where 1 is fully quantized"),
        ("steady_run_share", "Flow", "share of strokes inside steady, even runs")]


def html_of(fig, key):
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config=CONFIG, div_id=key)


def load(tag):
    recs = [r for r in json.loads(RESULTS.read_text()) if r["tag"] == tag and not r["error"]]
    for r in recs:
        r["name"] = r["model"].split("/")[1]
        r["work"] = WORK / "__".join(r["dir"].split("/")[2:])
        checks = json.loads((pipeline.ROOT / r["dir"] / "grade.json").read_text())["checks"]
        r["crash"] = checks["runs"]["detail"].strip().splitlines()[-1] if checks["runs"]["value"] != 1 else None
        r["length"] = None if r["crash"] else float(re.match(r"([\d.]+)s", checks["duration"]["detail"])[1])
        r["src"] = pipeline.ROOT / r["dir"] / "solo.mp3" if "render" not in r["failed"] else None
        r["provider"] = " + ".join(r["providers"])
    return recs


def human_reference():
    scores = json.loads((pipeline.OUT / "scores.json").read_text())
    overall = [s["overall"] for s in scores["solos"] if s["group"] == "human"]
    feats = [json.loads((pipeline.OUT / it["id"] / "features.json").read_text())["scalars"]
             for it in pipeline.corpus() if it["group"] == "human"]
    plan = {k: np.percentile([f[k] for f in feats if f[k] is not None], [25, 50, 75]) for k, *_ in PLAN}
    return np.percentile(overall, [25, 50, 75]), plan


SYMBOLS = ["circle", "diamond", "square", "triangle-up"]
GLYPHS = {"circle": "\u25cf", "diamond": "\u25c6", "square": "\u25a0", "triangle-up": "\u25b2"}


def groups(recs, name):
    """A model's runs split by the upstream provider(s) that served them, most runs first: (label, symbol, dash, runs)."""
    rs = [r for r in recs if r["name"] == name]
    labels = [lab for lab, _ in Counter(r["provider"] for r in rs).most_common()]
    return [(lab, SYMBOLS[i], "solid" if i == 0 else "dash", [r for r in rs if r["provider"] == lab])
            for i, lab in enumerate(labels)]


def title(recs, name):
    gs = groups(recs, name)
    if len(gs) == 1:
        return name
    return name + "<br><span style='font-size:10.5px'>" + "   ".join(f"{GLYPHS[sym]} {lab}" for lab, sym, _, _ in gs) + "</span>"


def styled(fig, height, recs, legend=False):
    """report_solo.style, with room above the plots for two-line subplot titles."""
    style(fig, height, legend=legend)
    if any(len(groups(recs, n)) > 1 for n in names_of(recs)):
        fig.update_layout(margin=dict(t=64 if legend else 44))
    return fig


def names_of(recs):
    return [n for n in LEVELS if any(r["name"] == n for r in recs)]


def by_level(rs, name, key):
    """Per thinking level: (key, run) for the scored runs among rs where key is measured."""
    return [[(key(r), r) for r in rs if r["thinking"] == lv and not r["failed"] and key(r) is not None]
            for lv in LEVELS[name]]


def jitter(n, seed):
    return np.random.default_rng(seed).uniform(-0.12, 0.12, n)


def level_axes(fig, lv, c, label=True):
    fig.update_xaxes(tickvals=list(range(len(lv))), ticktext=lv, range=[-0.5, len(lv) - 0.5],
                     title_text="thinking" if label else None, row=1, col=c)


def dots_and_line(fig, name, pairs, lv, c, lab, sym, dash, seed, fmt, size=9):
    vals = [[x for x, _ in p] for p in pairs]
    for k, (v, p) in enumerate(zip(vals, pairs)):
        fig.add_trace(go.Scatter(x=k + jitter(len(v), seed + k), y=v, mode="markers", showlegend=False,
                                 marker=dict(size=size, symbol=sym, color=COLORS[name], opacity=0.75,
                                             line=dict(width=1, color="white")),
                                 meta=[sound.run_id(r) for _, r in p],
                                 hovertemplate=f"{lv[k]} ({lab}): %{{y:{fmt}}}<extra></extra>"), row=1, col=c)
    if sum(1 for v in vals if v) > 1:
        fig.add_trace(go.Scatter(x=list(range(len(lv))), y=[np.mean(v) if v else None for v in vals], mode="lines",
                                 connectgaps=True, showlegend=False, line=dict(width=2.5, color=COLORS[name], dash=dash),
                                 hovertemplate=f"mean ({lab}) %{{y:{fmt}}}<extra></extra>"), row=1, col=c)


def fig_score(recs, human):
    names = names_of(recs)
    fig = make_subplots(rows=1, cols=len(names), shared_yaxes=True, subplot_titles=[title(recs, n) for n in names],
                        horizontal_spacing=0.04)
    for c, name in enumerate(names, 1):
        lv = LEVELS[name]
        fig.add_hrect(y0=human[0], y1=human[2], fillcolor=HUMAN_BAND, line_width=0, layer="below", row=1, col=c,
                      exclude_empty_subplots=False)
        fig.add_hline(y=human[1], line=dict(color=MUTED, width=1, dash="dot"), row=1, col=c, exclude_empty_subplots=False)
        for g, (lab, sym, dash, rs) in enumerate(groups(recs, name)):
            dots_and_line(fig, name, by_level(rs, name, lambda r: r["overall"]), lv, c, lab, sym, dash, 10 * g, ".0f")
        level_axes(fig, lv, c)
    fig.update_yaxes(title_text="garths", range=[20, 100], row=1, col=1)
    return styled(fig, 400, recs)


def fig_delivery(recs):
    """Length of every solo that produced a MIDI file; runs without one as x at the foot of the axis."""
    names = names_of(recs)
    fig = make_subplots(rows=1, cols=len(names), shared_yaxes=True, subplot_titles=[title(recs, n) for n in names],
                        horizontal_spacing=0.04)
    for c, name in enumerate(names, 1):
        lv = LEVELS[name]
        fig.add_hline(y=120, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=c, exclude_empty_subplots=False)
        for g, (lab, sym, _, rs) in enumerate(groups(recs, name)):
            for k, level in enumerate(lv):
                made = [r for r in rs if r["thinking"] == level and not r["crash"]]
                crashed = [r for r in rs if r["thinking"] == level and r["crash"]]
                fig.add_trace(go.Scatter(x=k + jitter(len(made), 20 + 10 * g + k), y=[r["length"] for r in made],
                                         mode="markers", showlegend=False,
                                         customdata=[f"{r['overall']:.0f}" if not r["failed"] else "none" for r in made],
                                         meta=[sound.run_id(r) for r in made],
                                         marker=dict(size=9, symbol=sym, color=COLORS[name], opacity=0.75,
                                                     line=dict(width=1, color="white")),
                                         hovertemplate=f"{level} ({lab}): %{{y:.1f}} s, %{{customdata}} garths<extra></extra>"),
                              row=1, col=c)
                fig.add_trace(go.Scatter(x=k + jitter(len(crashed), 30 + 10 * g + k), y=[8] * len(crashed), mode="markers",
                                         showlegend=False, text=[escape(r["crash"]) for r in crashed],
                                         marker=dict(size=10, symbol="x-thin", color=INK, line=dict(width=2, color=INK)),
                                         hovertemplate=f"{level} ({lab}): no MIDI file<br>%{{text}}<extra></extra>"),
                              row=1, col=c)
        level_axes(fig, lv, c)
    fig.update_yaxes(title_text="length of the solo (s)", rangemode="tozero", row=1, col=1)
    return styled(fig, 360, recs)


def axis_ref(c):
    return ("x" if c == 1 else f"x{c}"), ("y" if c == 1 else f"y{c}")


def fig_tokens(recs):
    """Reasoning tokens of every run; runs that spent none are counted at the foot of the axis."""
    names = names_of(recs)
    fig = make_subplots(rows=1, cols=len(names), shared_yaxes=True, subplot_titles=[title(recs, n) for n in names],
                        horizontal_spacing=0.04)
    for c, name in enumerate(names, 1):
        lv = LEVELS[name]
        none = Counter()
        for g, (lab, sym, _, rs) in enumerate(groups(recs, name)):
            for k, level in enumerate(lv):
                runs = [r for r in rs if r["thinking"] == level]
                spent = [r for r in runs if r["reasoning_tokens"] > 0]
                none[k] += len(runs) - len(spent)
                pos = [r["reasoning_tokens"] for r in spent]
                fig.add_trace(go.Scatter(x=k + jitter(len(pos), 50 + 10 * g + k), y=pos, mode="markers", showlegend=False,
                                         meta=[sound.run_id(r) for r in spent],
                                         marker=dict(size=9, symbol=sym, color=COLORS[name], opacity=0.75,
                                                     line=dict(width=1, color="white")),
                                         hovertemplate=f"{level} ({lab}): %{{y:,}} tokens<extra></extra>"), row=1, col=c)
        for k, n in none.items():
            if n:
                xr, yr = axis_ref(c)
                total = sum(1 for r in recs if r["name"] == name and r["thinking"] == lv[k])
                fig.add_annotation(x=k, y=0.03, xref=xr, yref=f"{yr} domain", yanchor="bottom", showarrow=False,
                                   text=f"none: {n} of {total}", font=dict(size=11, color=INK2))
        level_axes(fig, lv, c)
    fig.update_yaxes(type="log", dtick=1)
    fig.update_yaxes(title_text="reasoning tokens (log scale)", row=1, col=1)
    return styled(fig, 360, recs)


def fig_score_vs_tokens(recs, human):
    """Scored runs: overall score against reasoning tokens, with a narrow panel for runs that spent none."""
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.07, 0.93], horizontal_spacing=0.012)
    for c in (1, 2):
        fig.add_hrect(y0=human[0], y1=human[2], fillcolor=HUMAN_BAND, line_width=0, layer="below", row=1, col=c,
                      exclude_empty_subplots=False)
    for name in names_of(recs):
        gs = groups(recs, name)
        for lab, sym, _, rs in gs:
            legend = name if len(gs) == 1 else f"{name} ({lab})"
            shown = False
            scored = [r for r in rs if not r["failed"]]
            for c, part in ((1, [r for r in scored if r["reasoning_tokens"] == 0]),
                            (2, [r for r in scored if r["reasoning_tokens"] > 0])):
                if not part:
                    continue
                x = jitter(len(part), 7) if c == 1 else [r["reasoning_tokens"] for r in part]
                fig.add_trace(go.Scatter(x=x, y=[r["overall"] for r in part], mode="markers", name=legend, legendgroup=legend,
                                         meta=[sound.run_id(r) for r in part],
                                         showlegend=not shown, customdata=[[r["thinking"], r["reasoning_tokens"]] for r in part],
                                         marker=dict(size=10, symbol=sym, color=COLORS[name], opacity=0.8,
                                                     line=dict(width=1, color="white")),
                                         hovertemplate="%{customdata[0]}: %{customdata[1]:,} tokens, %{y:.0f} garths<extra></extra>"),
                              row=1, col=c)
                shown = True
    fig.add_annotation(xref="x2 domain", x=1, yref="y2", y=human[2], text="recorded solos (middle half)", showarrow=False,
                       xanchor="right", yanchor="top", font=dict(size=11, color=INK2))
    fig.update_xaxes(tickvals=[0], ticktext=["none"], range=[-0.5, 0.5], row=1, col=1)
    fig.update_xaxes(type="log", dtick=1, title_text="reasoning tokens spent (log scale)", row=1, col=2)
    fig.update_yaxes(range=[20, 100])
    fig.update_yaxes(title_text="garths", row=1, col=1)
    return style(fig, 440)


def fig_metric(recs, key, band):
    names = names_of(recs)
    fig = make_subplots(rows=1, cols=len(names), shared_yaxes=True, subplot_titles=[title(recs, n) for n in names],
                        horizontal_spacing=0.04)
    for c, name in enumerate(names, 1):
        lv = LEVELS[name]
        fig.add_hrect(y0=band[0], y1=band[2], fillcolor=HUMAN_BAND, line_width=0, layer="below", row=1, col=c,
                      exclude_empty_subplots=False)
        for g, (lab, sym, dash, rs) in enumerate(groups(recs, name)):
            dots_and_line(fig, name, by_level(rs, name, lambda r: r["planning"][key]), lv, c, lab, sym, dash, 40 + 10 * g,
                          ".3g", size=8)
        level_axes(fig, lv, c, label=False)
    return styled(fig, 270, recs)


def listening(recs):
    """Per model: one row per thinking level, every run playable with its score and a structure thumbnail."""
    thumbs, blocks = {}, []
    for name in LEVELS:
        several = len(groups(recs, name)) > 1
        rows = []
        for lv in LEVELS[name]:
            cells = []
            for r in sorted([r for r in recs if r["name"] == name and r["thinking"] == lv], key=lambda r: (r["provider"], r["dir"])):
                where = f"<div class='muted'>{escape(r['provider'])}</div>" if several else ""
                if r["crash"]:
                    cells.append(f"<div class='cell fail'>no MIDI file:<br><code>{escape(r['crash'][:120])}</code>{where}</div>")
                    continue
                if r["failed"]:
                    cells.append(f"<div class='cell fail'>not analyzed: {escape(', '.join(r['failed']))}{where}</div>")
                    continue
                key = f"ssm{len(thumbs)}"
                S = np.array(json.loads((r["work"] / "features.json").read_text())["images"]["ssm"]["symbolic"], dtype=float)
                thumbs[key] = np.round(ndimage.zoom(S, 48 / S.shape[0], order=1), 2).tolist()
                turns = f", {r['turns']} turns" if r["turns"] > 1 else ""
                cells.append(f"<div class='cell' data-solo='{sound.run_id(r)}'><canvas id='{key}' width='48' height='48'></canvas><div>"
                             f"<b>{r['overall']:.0f}</b> <span class='muted'>{r['reasoning_tokens']:,} tok{turns}</span></div>"
                             f"{where}<audio controls preload='none' src='{escape(r['audio'])}'></audio></div>")
            if cells:
                rows.append(f"<div class='lvl'><div class='lvl-name'>{escape(lv)}</div><div class='cells'>{''.join(cells)}</div></div>")
        if rows:
            blocks.append(f"<h3 style='color:{COLORS[name]}'>{escape(name)}</h3>{''.join(rows)}")
    return "".join(blocks), thumbs


THUMB_JS = """<script>
for (const [id, S] of Object.entries(THUMBS)) {
  const ctx = document.getElementById(id).getContext("2d"), n = S.length, img = ctx.createImageData(n, n);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const v = Math.round(255 - 215 * S[i][j]), p = 4 * (i * n + j);
    img.data[p] = v; img.data[p + 1] = v; img.data[p + 2] = Math.min(255, v + 20); img.data[p + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
}
const players = [...document.querySelectorAll("audio")];
players.forEach(p => p.addEventListener("play", () => players.forEach(o => { if (o !== p) o.pause(); })));
</script>"""


def publish_audio(recs):
    """Copy each playable render into the site as audio/thinking/<model>_<setting>_<n>.mp3."""
    for name in LEVELS:
        for lv in LEVELS[name]:
            rs = sorted([r for r in recs if r["name"] == name and r["thinking"] == lv and r["src"]],
                        key=lambda r: (r["provider"], r["dir"]))
            for k, r in enumerate(rs, 1):
                rel = f"audio/thinking/{name}_{lv}_{k}.mp3"
                dst = pipeline.SITE / rel
                if pipeline.stale(dst, r["src"]):
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(r["src"], dst)
                r["audio"] = rel


def glance(recs):
    """One row per model and setting: runs, score, thinking spent, cost, and runs that needed another turn."""
    rows = []
    for name in names_of(recs):
        for lv in LEVELS[name]:
            rs = [r for r in recs if r["name"] == name and r["thinking"] == lv]
            ok = [r["overall"] for r in rs if not r["failed"]]
            more = sum(1 for r in rs if r["turns"] > 1)
            rows.append(f"<tr><td style='color:{COLORS[name]};font-weight:600'>{escape(name)}</td><td>{escape(lv)}</td>"
                        f"<td class='num'>{len(rs)}</td><td class='num'>{np.mean(ok):.1f}</td>"
                        f"<td class='num'>{min(ok):.0f} to {max(ok):.0f}</td>"
                        f"<td class='num'>{np.median([r['reasoning_tokens'] for r in rs]):,.0f}</td>"
                        f"<td class='num'>${np.mean([r['cost'] for r in rs]):.2f}</td><td class='num'>{more or ''}</td></tr>")
    return ("<table class='glance'><tr><th>model</th><th>thinking</th><th>runs</th><th>mean score</th><th>range</th>"
            "<th>reasoning tokens (median)</th><th>cost per run</th><th>runs needing another turn</th></tr>"
            + "".join(rows) + "</table>")


CSS = f"""
table.glance{{width:100%}} table.glance td,table.glance th{{padding:4px 12px}}
.lvl{{display:flex;gap:12px;align-items:flex-start;margin:8px 0}} .lvl-name{{width:60px;padding-top:6px;color:{INK2};font-weight:600;flex:none}}
.cells{{display:flex;flex-wrap:wrap;gap:8px;flex:1}}
.cell{{padding:6px;border:1px solid {GRID};border-radius:6px;font-size:13px;width:196px;box-sizing:border-box}}
.cell canvas{{width:72px;height:72px;image-rendering:pixelated;display:block;margin-bottom:4px}}
.cell audio{{width:100%;height:32px}} .fail{{color:{INK2}}} .muted{{color:{MUTED}}}
.fail code{{font-size:11.5px;word-break:break-word}}
details{{font-size:14px;margin:8px 0}}
@media (max-width:700px){{.lvl{{flex-direction:column;gap:4px}} .cell{{width:100%}}}}
"""


def main(tag):
    recs = load(tag)
    human, plan = human_reference()
    prompt = (HC / "prompts" / f"{tag}.md").read_text()
    publish_audio(recs)
    grid, thumbs = listening(recs)
    per_setting = Counter((r["name"], r["thinking"]) for r in recs)
    crashed = any(r["crash"] for r in recs)
    body = f"""<h1>Thinking settings</h1>
<p class="sub">Three models wrote a two-minute drum solo at every thinking setting they offer, at least
{min(per_setting.values())} times each. The {len(recs)} solos cost ${sum(r['cost'] for r in recs):.0f} in API fees. They're scored
exactly like on <a href="index.html">the main page</a>, and the gray bands show the middle half of the recorded solos. Every
solo is in the grid at the bottom.</p>
<p class="note">These runs use the final prompt from the hill climb on the main page, so they score higher than the
same models do on the benchmark prompt. If a program breaks, the error goes back to the model, up to two times.
OpenRouter hands each request to one of several providers for a model. Where a model was served by more than one, the
marker shape tells you which.</p>
<details><summary>The prompt</summary><pre>{escape(prompt)}</pre></details>
<h2>Summary</h2>{glance(recs)}
<h2>Score by thinking setting</h2>{html_of(fig_score(recs, human), 'score')}
<h2>Reasoning tokens by setting</h2>{html_of(fig_tokens(recs), 'tokens')}
<h2>Score by reasoning tokens</h2>{html_of(fig_score_vs_tokens(recs, human), 'svt')}
<h2>Length</h2>
<p class="note">The prompt asked for two minutes (dotted line), and a solo far from it loses points on the length
measurement.{" An x is a run that never wrote a MIDI file, even after two repair turns." if crashed else ""}</p>
{html_of(fig_delivery(recs), 'delivery')}
<h2>Measures by setting</h2>
<p class="note">Each chart is one measure of how a solo is built. The gray band is the middle half of the recorded solos.</p>
{"".join(f"<h3>{label}</h3><p class='note'>{desc}</p>{html_of(fig_metric(recs, key, plan[key]), key)}" for key, label, desc in PLAN)}
<h2>Listen</h2>
<p class="note">Every solo, by thinking setting. The square is the solo's structure. Dark blocks on the diagonal are
sections, off-diagonal blocks are returns to earlier material. The number is the overall score, then the reasoning tokens
spent, and the number of turns when the first reply had no working program.</p>
{grid}
<script>const THUMBS = {json.dumps(thumbs)};</script>{THUMB_JS}"""
    out = pipeline.SITE / "thinking.html"
    out.write_text(page("Thinking settings", body, css=CSS, tail=sound.tags(), here="thinking.html"))
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "t6")
