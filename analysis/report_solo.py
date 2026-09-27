#!/usr/bin/env python3
"""Build the analysis page for one solo from features.json and a transcription validation.

usage: uv run python report_solo.py features.json validation.json out.html [--audio a.mp3]
"""
import argparse
import json
import os
from collections import Counter
from html import escape
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots

import drums
import pipeline
import sound

INK, INK2, MUTED, LIGHT, GRID = "#1f2328", "#57606a", "#8c959f", "#c9d1d9", "#eaeef2"
BRONZE = "#b8860b"  # cymbal bronze: the one accent color of the site
REPO_URL = "https://github.com/gileshall/drumthrone"
SITE_URL = "https://gileshall.github.io/drumthrone/"
# the corner is Tim Holman's GitHub Corners (github.com/tholman/github-corners, MIT License)
FORK = (f"<a class='fork' href='{REPO_URL}' aria-label='Fork me on GitHub' title='Fork me on GitHub'>"
        "<svg width='80' height='80' viewBox='0 0 250 250' aria-hidden='true'>"
        "<path d='M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z'/>"
        "<path class='octo-arm' d='M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 "
        "C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2'/>"
        "<path class='octo-body' d='M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 "
        "142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 "
        "C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 "
        "C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 "
        "C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 "
        "141.6,141.9 141.8,141.8 Z'/></svg></a>")
FORK_CSS = """
.fork{position:absolute;top:0;right:0;z-index:40}
.fork svg{display:block;fill:#1f2328;color:#fff}
.fork .octo-arm,.fork .octo-body{fill:currentColor}
.fork .octo-arm{transform-origin:130px 106px}
.fork:hover svg{fill:#b8860b}
.fork:hover .octo-arm{animation:octo-wave 560ms ease-in-out}
@keyframes octo-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}
@media (max-width:700px){.fork{display:none}}
footer{max-width:1000px;margin:0 auto;padding:16px 24px 110px;border-top:1px solid #eaeef2;color:#8c959f;font-size:12.5px}
footer a{color:#8c959f}
"""
NAV_PAGES = [("index.html", "Drum Throne"), ("how.html", "How it works"), ("measurements.html", "Measurements"),
             ("thinking.html", "Thinking"), ("detection.html", "Scored parts"), ("graph.html", "Graph")]
NAV_CSS = """
nav.site{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.96);display:flex;flex-wrap:wrap;align-items:center;
gap:4px 20px;font-size:14px;padding:12px 0;margin:-36px 0 26px;border-bottom:1px solid #eaeef2}
@media (max-width:1200px){nav.site{padding-right:84px}}
nav.site a{color:#57606a;text-decoration:none} nav.site a:hover{color:#1f2328}
nav.site a.here{color:#1f2328;font-weight:600} nav.site a.brand{color:#1f2328;font-weight:700}
@media (max-width:700px){
nav.site{flex-wrap:nowrap;overflow-x:auto;white-space:nowrap;scrollbar-width:none;gap:0 18px;padding:2px 0;
margin:-36px 0 20px}
nav.site::-webkit-scrollbar{display:none}
nav.site a{flex:none;padding:12px 0}
nav.site .sound-switch{flex:none;order:-1;margin:0;padding:6px 10px}
nav.site .sound-switch span{display:none}
nav.site{-webkit-mask-image:linear-gradient(to right,#000 82%,transparent);mask-image:linear-gradient(to right,#000 82%,transparent)}
main{padding-left:16px !important;padding-right:16px !important}
main table:not(.listen):not(.metrics){display:block;overflow-x:auto;max-width:100%;white-space:nowrap;
background:linear-gradient(to right,#fff 30%,rgba(255,255,255,0)) left center/40px 100% no-repeat local,
linear-gradient(to left,#fff 30%,rgba(255,255,255,0)) right center/40px 100% no-repeat local,
radial-gradient(farthest-side at 0 50%,rgba(0,0,0,.2),rgba(0,0,0,0)) left center/14px 100% no-repeat scroll,
radial-gradient(farthest-side at 100% 50%,rgba(0,0,0,.2),rgba(0,0,0,0)) right center/14px 100% no-repeat scroll}
.modebar{display:none !important}
button,summary{min-height:36px}
}
"""
# phones: side-by-side panels restack into one column (two for big grids), charts give their labels less room and small
# text, point labels move to hover, and charts never capture a swipe meant to scroll the page
MOBILE_JS = r"""<script>
if (matchMedia("(max-width: 700px)").matches) window.addEventListener("load", () =>
  document.querySelectorAll(".js-plotly-plot").forEach(gd => {
    const fl = gd._fullLayout;
    if (!fl) return;
    const upd = {"font.size": 10, "margin.l": 8, "margin.r": 8, "legend.font.size": 9, dragmode: false};
    const panels = [];
    for (const k of Object.keys(fl)) {
      if (/^xaxis\d*$/.test(k)) {
        const xa = fl[k], y = "yaxis" + (xa.anchor || "y").slice(1);
        if (fl[y]) panels.push({x: k, y, xd: xa.domain, yd: fl[y].domain});
      } else if (/^polar\d*$/.test(k)) {
        panels.push({polar: k, xd: fl[k].domain.x, yd: fl[k].domain.y, square: true});
      }
    }
    const cols = new Set(panels.map(p => p.xd[0].toFixed(2))).size;
    const target = panels.length > 6 ? 2 : 1;
    if (cols > target) {
      const anns = (gd.layout.annotations || []);
      panels.sort((a, b) => (b.yd[1] - a.yd[1]) || (a.xd[0] - b.xd[0]));
      const plotH = fl._size.h, plotW = gd.getBoundingClientRect().width - 16;
      const rows = Math.ceil(panels.length / target), gap = 64, mt = fl.margin.t, mb = fl.margin.b;
      const panelH = Math.max(150, ...panels.map(p => (p.yd[1] - p.yd[0]) * plotH),
                              panels.some(p => p.square || fl[p.y] && fl[p.y].scaleanchor) ? plotW / target : 0);
      const H = rows * panelH + (rows - 1) * gap;
      panels.forEach((p, i) => {
        const r = Math.floor(i / target), c = i % target;
        const top = 1 - r * (panelH + gap) / H, bottom = top - panelH / H;
        const xd = [c / target + (c ? 0.06 : 0), (c + 1) / target - (c < target - 1 ? 0.06 : 0)];
        anns.forEach((a, j) => {
          if (a.xref === "paper" && a.yref === "paper" && Math.abs(a.x - (p.xd[0] + p.xd[1]) / 2) < 0.03 &&
              Math.abs(a.y - p.yd[1]) < 0.06) {
            upd[`annotations[${j}].x`] = (xd[0] + xd[1]) / 2; upd[`annotations[${j}].xanchor`] = "center";
            upd[`annotations[${j}].y`] = top;
          }
        });
        if (p.polar) { upd[`${p.polar}.domain.x`] = xd; upd[`${p.polar}.domain.y`] = [bottom, top]; }
        else {
          upd[`${p.x}.domain`] = xd; upd[`${p.y}.domain`] = [bottom, top];
          upd[`${p.x}.showticklabels`] = true; upd[`${p.y}.showticklabels`] = true;  // shared axes hid them on inner panels
        }
      });
      upd.height = H + mt + mb + Math.max(0, 48 - mt);
      upd["margin.t"] = Math.max(mt, 48);  // room above the first panel for its title
      // one colorbar beside the first panel instead of stretched down every stacked panel
      const bars = gd.data.map((t, i) => t.showscale ? i : -1).filter(i => i >= 0);
      if (bars.length) Plotly.restyle(gd, {"colorbar.len": panelH / H, "colorbar.y": 1, "colorbar.yanchor": "top"}, bars);
    }
    let extraTop = 0;
    (gd.layout.annotations || []).forEach((a, j) => {
      upd[`annotations[${j}].font.size`] = 9;
      const t = String(a.text || "");
      if (t.length > 46 && !t.includes("<")) {  // long plain titles wrap onto two lines
        const mid = t.length / 2, cut = [...t.matchAll(/ /g)].map(m => m.index)
          .reduce((b, i) => Math.abs(i - mid) < Math.abs(b - mid) ? i : b, -1);
        if (cut > 0) {
          upd[`annotations[${j}].text`] = t.slice(0, cut) + "<br>" + t.slice(cut + 1);
          if (a.yref === "paper" && a.y >= 0.95) extraTop = 16;  // the top title needs room for its second line
        }
      }
    });
    if (extraTop) {
      upd["margin.t"] = (upd["margin.t"] || fl.margin.t) + extraTop;
      if (upd.height) upd.height += extraTop;
    }
    for (const k of Object.keys(fl)) if (/^[xy]axis\d*$/.test(k)) {
      upd[k + ".tickfont.size"] = 9; upd[k + ".title.font.size"] = 9; upd[k + ".automargin"] = true;
      upd[k + ".fixedrange"] = true;
      const tt = fl[k].ticktext;
      if (k[0] === "x" && tt && tt.length > 4 && Math.max(...tt.map(t => String(t).length)) > 6) upd[k + ".tickangle"] = -40;
    }
    const labelled = gd.data.map((t, i) => (t.type || "scatter") === "scatter" && /text/.test(t.mode || "") &&
                                         (t.x || []).length > 10 ? i : -1).filter(i => i >= 0);
    const heat = gd.data.map((t, i) => t.type === "heatmap" && t.texttemplate ? i : -1).filter(i => i >= 0);
    // a tap goes to whatever is drawn on top, so in a chart with solos to hear, the marks without sound let taps through
    const sounding = gd.data.some(t => t.meta);
    const mute = gd.data.map((t, i) => sounding && !t.meta ? i : -1).filter(i => i >= 0);
    const done = (labelled.length ? Plotly.restyle(gd, {mode: "markers"}, labelled) : Promise.resolve())
      .then(() => heat.length ? Plotly.restyle(gd, {"textfont.size": 8}, heat) : null)
      .then(() => mute.length ? Plotly.restyle(gd, {hoverinfo: "skip", hovertemplate: null}, mute) : null);
    if (upd.height) {  // the chart's boxes (Plotly's wrapper too) grow with it, so nothing below is covered
      gd.style.height = upd.height + "px";
      if (gd.parentElement && gd.parentElement.style.height) gd.parentElement.style.height = upd.height + "px";
    }
    done.then(() => Plotly.relayout(gd, upd)).then(() => {
      const lg = gd._fullLayout.legend;
      if (gd._fullLayout.showlegend && lg && lg._height && lg.orientation === "h" && lg.y >= 1)
        return Plotly.relayout(gd, {"margin.t": Math.max(gd._fullLayout.margin.t, lg._height + 24)});
    });
  }));
</script>"""


def nav(prefix="", here=None):
    """The same links on every page; prefix is the path from the page to the site root."""
    links = [f"<a class='{'brand ' if i == 0 else ''}{'here' if f == here else ''}' href='{prefix}{f}'>{label}</a>"
             for i, (f, label) in enumerate(NAV_PAGES)]
    return f"<nav class='site'>{''.join(links)}<a href='{REPO_URL}'>GitHub</a></nav>"


def og(title, description, path=""):
    """Link-preview tags; path is the page's place under the published site."""
    return (f'<meta name="description" content="{escape(description)}">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="Drum Throne">'
            f'<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(description)}">'
            f'<meta property="og:url" content="{SITE_URL}{path}"><meta name="twitter:card" content="summary">')


FOOTER = (f"<footer>&copy; 2026 Giles Hall &middot; code under the <a href='{REPO_URL}/blob/main/LICENSE'>MIT License</a> "
          "&middot; the recordings belong to their owners</footer>")
# GoatCounter visit counts (no cookies), on the published site only
COUNTER = ('<script data-goatcounter="https://drumthrone.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
           if pipeline.PUBLIC else "")
NOTEHEAD = ("url(\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 13 17'>"
            "<path d='M1 11l5 5M6 11l-5 5' stroke='%23b8860b' stroke-width='1.8' stroke-linecap='round'/>"
            "<path d='M6.3 12.5V1.5' stroke='%23b8860b' stroke-width='1.4'/></svg>\")")
ACCENT_CSS = f"""
h2{{{{border-top:none;padding-top:22px;background:linear-gradient({LIGHT},{LIGHT}) 0 0/100% 1px no-repeat,
repeating-linear-gradient(90deg,{LIGHT} 0 1px,transparent 1px 180px) 0 0/100% 8px no-repeat}}}}
h2::before{{{{content:"";display:inline-block;width:13px;height:17px;margin-right:9px;vertical-align:-1px;
background:{NOTEHEAD} no-repeat}}}}
"""
FONT = 'system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif'
SEQ = [[0, "#ffffff"], [0.3, "#c9d6e3"], [0.65, "#6283a6"], [1, "#15263b"]]  # one hue, light to dark
CATS = list(drums.CATEGORIES)
LOG_HZ = [50, 100, 200, 500, 1000, 2000, 5000, 10000]
LOG_COUNTS = dict(tickvals=[1, 10, 100, 1000, 10000], ticktext=["1", "10", "100", "1,000", "10,000"])
CONFIG = {"displaylogo": False, "responsive": True,
          "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"]}


def style(fig, height, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=64, r=24, t=36 if legend else 16, b=48),
        font=dict(family=FONT, size=12, color=INK2), paper_bgcolor="white", plot_bgcolor="white",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=12, color=INK)),
        hoverlabel=dict(bgcolor="white", bordercolor=LIGHT, font=dict(family=FONT, color=INK, size=12)),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, showline=True, linecolor=LIGHT,
                     ticks="outside", tickcolor=LIGHT, title_font=dict(size=12, color=INK2))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, showline=False, automargin=True,
                     title_font=dict(size=12, color=INK2))
    fig.update_annotations(font=dict(size=12, color=INK))
    return fig


def mmss(t):
    return f"{int(t // 60)}:{int(round(t % 60)):02d}" if round(t % 60) < 60 else f"{int(t // 60) + 1}:00"


def time_ticks(fig, dur, step=60, **kw):
    ticks = np.arange(0, dur + 1e-9, step)
    fig.update_xaxes(tickvals=ticks, ticktext=[mmss(t) for t in ticks], range=[0, dur], **kw)


def vlines(fig, xs, **kw):
    for x in xs:
        fig.add_vline(x=x, line=dict(color=MUTED, width=1, dash="dot"), **kw)


def hist_log(values, lo, hi, per_octave=12):
    edges = 2 ** np.arange(np.log2(lo), np.log2(hi) + 1e-9, 1 / per_octave)
    counts, _ = np.histogram(np.clip(values, lo, hi * 0.999), bins=edges)
    return np.sqrt(edges[:-1] * edges[1:]), counts, edges


# ---------------------------------------------------------------- figures

def fig_drum_roll(f, center):
    h = f["hits"]
    t, notes, cats = np.array(h["t"]), np.array(h["note"]), np.array(h["cat"])
    rows = sorted(set(notes.tolist()), key=lambda n: (CATS.index(drums.category(n)), n))
    ypos = {n: i + 1 for i, n in enumerate(rows)}
    fig = go.Figure()
    sb = f["beats"]["smoothed"]
    fig.add_trace(go.Scatter(x=sb, y=[0] * len(sb), mode="markers", name="tracked beat",
                             marker=dict(symbol="line-ns-open", size=12, line=dict(width=1.5, color=MUTED)),
                             hovertemplate="beat at %{x:.2f} s<extra></extra>"))
    level, grid, dev = np.array(h["level_db"]), np.array(h["grid"]), np.array(h["dev_ms"])
    for c in CATS:
        m = cats == c
        if not m.any():
            continue
        cd = [[drums.name(n), f"{lv:+.1f}", g or "outside beats", "" if np.isnan(d) else f"{d:+.1f} ms"]
              for n, lv, g, d in zip(notes[m], level[m], grid[m], dev[m])]
        fig.add_trace(go.Scattergl(
            x=t[m], y=[ypos[n] for n in notes[m]], mode="markers", name=c, customdata=cd,
            marker=dict(size=8, color=drums.COLORS[c], line=dict(width=1, color="white")),
            hovertemplate="%{customdata[0]}<br>%{x:.3f} s<br>level %{customdata[1]} dB"
                          "<br>grid: %{customdata[2]} %{customdata[3]}<extra></extra>"))
    fig.update_xaxes(range=[center - 10, center + 10], title_text="time (s)")
    fig.update_yaxes(tickvals=[0] + [ypos[n] for n in rows],
                     ticktext=["tracked beat"] + [f"{drums.name(n)} ({n})" for n in rows],
                     range=[-0.8, len(rows) + 0.8], showgrid=True)
    return style(fig, 120 + 22 * len(rows))


def fig_timeline(f, dur):
    w, b = f["windows"], f["beats"]
    wt = np.array(w["t"])
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.34, 0.22, 0.22, 0.22],
                        subplot_titles=("Hits per second, by instrument (2 s windows)",
                                        "Loudness (LUFS)", "Tracked tempo (BPM)",
                                        "Novelty: how much the next 16 s differs from the last 16 s"))
    for c in CATS:
        if c in w["hits_per_s_by_cat"]:
            fig.add_trace(go.Scatter(x=wt, y=w["hits_per_s_by_cat"][c], name=c, stackgroup="rate", mode="lines",
                                     line=dict(width=1, color="white"), fillcolor=drums.COLORS[c],
                                     hovertemplate=f"{c}: %{{y:.1f}} hits/s<extra></extra>"), row=1, col=1)
    lo = f["loudness"]
    fig.add_trace(go.Scatter(x=lo["t"], y=lo["momentary"], name="momentary loudness (0.4 s)", mode="lines",
                             line=dict(width=1, color=LIGHT), hovertemplate="%{y:.1f} LUFS<extra></extra>"),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=lo["t"], y=lo["short_term"], name="short-term loudness (3 s)", mode="lines",
                             line=dict(width=2, color=INK), hovertemplate="%{y:.1f} LUFS<extra></extra>"),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=b["t"][1:], y=b["ibi_bpm"], name="beat-to-beat tempo", mode="markers",
                             marker=dict(size=4, color=LIGHT), hovertemplate="%{y:.0f} BPM<extra></extra>"),
                  row=3, col=1)
    sb = np.array(b["smoothed"])
    fig.add_trace(go.Scatter(x=sb[1:], y=60 / np.diff(sb), name="smoothed tempo", mode="lines",
                             line=dict(width=2, color=INK), hovertemplate="%{y:.1f} BPM<extra></extra>"),
                  row=3, col=1)
    fig.add_trace(go.Scatter(x=wt, y=w["novelty"], name="novelty", mode="lines", fill="tozeroy",
                             line=dict(width=1.5, color=INK2), fillcolor=GRID, showlegend=False,
                             hovertemplate="%{y:.2f}<extra></extra>"), row=4, col=1)
    vlines(fig, f["sections"]["boundaries_s"], row="all", col=1)
    ib = np.array(b["ibi_bpm"])
    fig.update_yaxes(range=[np.percentile(ib, 1) * 0.9, np.percentile(ib, 99) * 1.1], row=3, col=1)
    fig.update_yaxes(range=[-45, -5], row=2, col=1)
    time_ticks(fig, dur, 30)
    fig.update_xaxes(title_text="time (m:ss)", row=4, col=1)
    style(fig, 900)
    fig.update_layout(legend_traceorder="normal")
    return fig


def fig_mel(f, dur):
    m = f["images"]["mel"]
    keep = np.array(m["freqs"]) >= 20
    z = np.array(m["db"])[keep]
    x = (np.arange(z.shape[1]) + 0.5) * m["t_step"]
    fig = go.Figure(go.Heatmap(z=z, x=x, y=np.array(m["freqs"])[keep], colorscale=SEQ, zmin=-70, zmax=0,
                               colorbar=dict(title=dict(text="dB"), thickness=10, len=0.9),
                               hovertemplate="%{x:.1f} s, %{y:.0f} Hz: %{z} dB<extra></extra>"))
    fig.update_yaxes(type="log", title_text="frequency (Hz)", showgrid=False, tickvals=LOG_HZ,
                     ticktext=["50", "100", "200", "500", "1k", "2k", "5k", "10k"])
    vlines(fig, f["sections"]["boundaries_s"])
    time_ticks(fig, dur, 30, title_text="time (m:ss)", showgrid=False)
    return style(fig, 380, legend=False)


def fig_notes(f):
    notes = Counter(f["hits"]["note"])
    total = sum(notes.values())
    order = sorted(notes, key=lambda n: (CATS.index(drums.category(n)), n))
    labels = {n: f"{drums.name(n)} ({n})" for n in order}
    fig = go.Figure()
    for c in CATS:
        ns = [n for n in order if drums.category(n) == c]
        if ns:
            fig.add_trace(go.Bar(y=[labels[n] for n in ns], x=[notes[n] for n in ns], orientation="h", name=c,
                                 marker=dict(color=drums.COLORS[c], line=dict(width=0)),
                                 customdata=[f"{notes[n] / total:.1%}" for n in ns],
                                 hovertemplate="%{y}: %{x} hits (%{customdata})<extra></extra>"))
    fig.update_yaxes(categoryorder="array", categoryarray=[labels[n] for n in order], showgrid=False)
    fig.update_xaxes(type="log", title_text="hits (log scale)", **LOG_COUNTS)
    fig.update_layout(bargap=0.25)
    return style(fig, 110 + 22 * len(order))


def fig_loudness_hist(f):
    s = f["scalars"]
    m = np.array(f["loudness"]["momentary"], dtype=float)
    fig = go.Figure(go.Histogram(x=m[~np.isnan(m)], xbins=dict(size=1), marker=dict(color=INK2, line=dict(width=1, color="white")),
                                 hovertemplate="%{x} LUFS: %{y} frames<extra></extra>"))
    for x, label in ((s["lra_low_lufs"], "LRA low"), (s["lra_high_lufs"], "LRA high"),
                     (s["integrated_lufs"], "integrated")):
        fig.add_vline(x=x, line=dict(color=INK if label == "integrated" else MUTED, width=1.5,
                                     dash="solid" if label == "integrated" else "dash"),
                      annotation_text=label,
                      annotation_position={"integrated": "top left", "LRA high": "top right"}.get(label, "top"))
    fig.update_xaxes(title_text="momentary loudness (LUFS, 100 ms frames)", range=[-50, -3])
    fig.update_yaxes(title_text="frames")
    return style(fig, 340, legend=False)


def fig_levels(f, reliable):
    h = f["hits"]
    cats, level = np.array(h["cat"]), np.array(h["level_db"])
    fig = go.Figure()
    for c in CATS:
        if c in reliable and (cats == c).sum() >= 20:
            fig.add_trace(go.Violin(y=level[cats == c], name=c, line=dict(color=drums.COLORS[c], width=1.5),
                                    fillcolor=drums.COLORS[c], opacity=0.85, box=dict(visible=True),
                                    meanline=dict(visible=False), points=False, spanmode="hard",
                                    hoverinfo="y"))
    fig.update_yaxes(title_text="hit level (dB below the loudest 1% in its band)")
    return style(fig, 380, legend=False)


def fig_level_contour(f, dur, reliable):
    w = f["windows"]
    fig = go.Figure()
    for c, v in w["level_db_by_cat"].items():
        v = np.array(v, dtype=float)
        if c in reliable and np.mean(~np.isnan(v)) >= 0.5:
            ok = ~np.isnan(v)
            num = np.convolve(np.where(ok, v, 0), np.ones(5), "same")
            den = np.convolve(ok.astype(float), np.ones(5), "same")
            sm = np.where(ok, num / np.maximum(den, 1), np.nan)
            fig.add_trace(go.Scatter(x=w["t"], y=sm, name=c, mode="lines", connectgaps=False,
                                     line=dict(width=2, color=drums.COLORS[c]),
                                     hovertemplate=f"{c}: %{{y:.1f}} dB<extra></extra>"))
    time_ticks(fig, dur, 60, title_text="time (m:ss)")
    fig.update_yaxes(title_text="median hit level (dB, 10 s smoothing)")
    return style(fig, 340)


def fig_snare_hist(f):
    h = f["hits"]
    lv = np.array(h["level_db"])[np.array(h["cat"]) == "snare"]
    fig = go.Figure(go.Histogram(x=lv, xbins=dict(size=1), marker=dict(color=drums.COLORS["snare"], line=dict(width=1, color="white")),
                                 hovertemplate="%{x} dB: %{y} hits<extra></extra>"))
    fig.update_xaxes(title_text="snare hit level (dB below band peak)")
    fig.update_yaxes(title_text="hits")
    return style(fig, 300, legend=False)


def fig_tempogram(f, dur):
    tg = f["images"]["tempogram"]
    z = np.array(tg["z"])
    x = (np.arange(z.shape[1]) + 0.5) * tg["t_step"]
    fig = go.Figure(go.Heatmap(z=z, x=x, y=tg["bpm"], colorscale=SEQ, zmin=0, zmax=1, showscale=False,
                               hovertemplate="%{x:.1f} s, %{y:.0f} BPM: %{z:.2f}<extra></extra>"))
    sb = np.array(f["beats"]["smoothed"])
    bpm = 60 / np.diff(sb)
    fig.add_trace(go.Scatter(x=sb[1:], y=bpm, mode="lines", line=dict(width=5, color=INK), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=sb[1:], y=bpm, mode="lines", name="tracked beat", line=dict(width=2, color="white"),
                             hovertemplate="tracked: %{y:.1f} BPM<extra></extra>"))
    fig.update_yaxes(type="log", title_text="tempo (BPM)", tickvals=[40, 60, 80, 120, 160, 240, 320], showgrid=False)
    time_ticks(fig, dur, 30, title_text="time (m:ss)", showgrid=False)
    return style(fig, 400)


def fig_tempo_hist(f):
    b = np.array(f["beats"]["ibi_bpm"])
    fig = go.Figure(go.Histogram(x=b, xbins=dict(size=2), marker=dict(color=INK2, line=dict(width=1, color="white")),
                                 hovertemplate="%{x} BPM: %{y} beats<extra></extra>"))
    fig.add_vline(x=float(np.median(b)), line=dict(color=INK, width=1.5), annotation_text=f"median {np.median(b):.0f}",
                  annotation_position="top")
    fig.update_xaxes(title_text="beat-to-beat tempo (BPM)", range=[np.percentile(b, 0.5) - 5, np.percentile(b, 99.5) + 5])
    fig.update_yaxes(title_text="beats")
    return style(fig, 300, legend=False)


def fig_ioi(f):
    g = np.array(f["groups"]["t"])
    x, counts, edges = hist_log(np.diff(g), 0.02, 2.0)
    fig = go.Figure(go.Bar(x=np.log2(x), y=counts, width=np.diff(np.log2(edges)) * 0.9,
                           marker=dict(color=INK2, line=dict(width=0)),
                           customdata=np.round(x * 1000), hovertemplate="%{customdata} ms: %{y}<extra></extra>"))
    beat = float(np.median(np.diff(f["beats"]["smoothed"])))
    top = counts.max()
    for k, (div, label) in enumerate(((1, "beat"), (2, "8th"), (3, "triplet"), (4, "16th"), (6, "sextuplet"), (8, "32nd"))):
        xl = float(np.log2(beat / div))
        fig.add_shape(type="line", x0=xl, x1=xl, y0=0, y1=top * (1.08 if k % 2 else 1.22),
                      line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=xl, y=top * (1.08 if k % 2 else 1.22), text=label, showarrow=False, yanchor="bottom",
                           font=dict(size=11, color=INK2))
    ticks = [0.02, 0.05, 0.1, 0.2, 0.5, 1, 2]
    fig.update_xaxes(tickvals=np.log2(ticks), ticktext=["20 ms", "50 ms", "100 ms", "200 ms", "500 ms", "1 s", "2 s"],
                     title_text="time between consecutive strokes (log scale)")
    fig.update_yaxes(title_text="strokes", range=[0, top * 1.35])
    return style(fig, 360, legend=False)


def fig_clock(f):
    h = f["hits"]
    cats, phase = np.array(h["cat"]), np.array(h["phase"], dtype=float)
    show = [c for c in ("kick", "snare", "hi-hat", "ride", "toms") if ((cats == c) & ~np.isnan(phase)).sum() >= 40][:4]
    fig = make_subplots(rows=1, cols=len(show), specs=[[{"type": "polar"}] * len(show)],
                        subplot_titles=[f"{c} ({((cats == c) & ~np.isnan(phase)).sum()} hits)" for c in show])
    edges = np.linspace(0, 1, 49)
    for i, c in enumerate(show, 1):
        p = phase[(cats == c) & ~np.isnan(phase)]
        cnt, _ = np.histogram(p, bins=edges)
        fig.add_trace(go.Barpolar(r=cnt / cnt.max(), theta=(edges[:-1] + 1 / 96) * 360, width=[7.5] * 48, name=c,
                                  marker=dict(color=drums.COLORS[c], line=dict(width=0.5, color="white")),
                                  customdata=cnt, hovertemplate="%{customdata} hits<extra></extra>"),
                      row=1, col=i)
    fig.update_polars(angularaxis=dict(rotation=90, direction="clockwise", tickvals=[0, 90, 120, 180, 240, 270],
                                       ticktext=["1", "e", "trip", "&", "trip", "a"], gridcolor=GRID,
                                       linecolor=LIGHT, tickfont=dict(size=11, color=INK2)),
                      radialaxis=dict(showticklabels=False, gridcolor=GRID, linecolor=GRID, ticks=""),
                      bgcolor="white")
    fig.update_annotations(yshift=12)
    return style(fig, 330, legend=False)


def fig_grid_profile(f):
    s = f["scalars"]
    classes = ["beat", "8th", "16th", "triplet", "sextuplet", "off-grid"]
    vals = [s[f"grid_{c}"] for c in classes]
    fig = go.Figure(go.Bar(x=classes, y=vals, marker=dict(color=[INK2] * 5 + [LIGHT], line=dict(width=0)),
                           hovertemplate="%{x}: %{y:.1%}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", title_text="share of hits")
    fig.update_layout(bargap=0.35)
    return style(fig, 300, legend=False)


def fig_evenness(f):
    d = np.array(f["evenness"]["dev_ms"], dtype=float)
    fig = go.Figure(go.Histogram(x=d, xbins=dict(start=-30, end=30, size=1),
                                 marker=dict(color=INK2, line=dict(width=1, color="white")),
                                 hovertemplate="%{x} ms: %{y} strokes<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_xaxes(title_text="offset from the midpoint of the strokes two either side (ms; negative = early)",
                     range=[-30, 30])
    fig.update_yaxes(title_text="strokes")
    return style(fig, 300, legend=False)


def fig_vocab(f):
    cl = f["cells"]
    sb = np.array(f["beats"]["smoothed"])
    n = len(cl["rhythm_growth"])
    x = sb[:n]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=np.arange(1, n + 1), name="every beat new", mode="lines",
                             line=dict(width=1.5, color=LIGHT, dash="dash"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=cl["orch_growth"], name="rhythm + instruments", mode="lines",
                             line=dict(width=2, color=INK2), hovertemplate="%{y} distinct<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=cl["rhythm_growth"], name="rhythm only", mode="lines",
                             line=dict(width=2, color=INK), hovertemplate="%{y} distinct<extra></extra>"))
    time_ticks(fig, float(x[-1]), 60, title_text="time (m:ss)")
    fig.update_yaxes(title_text="distinct one-beat patterns so far")
    return style(fig, 360)


def fig_top_cells(f):
    cl = f["cells"]
    steps = cl["steps"]
    top = cl["top_rhythm"]
    z = [[(cell >> i) & 1 for i in range(steps)] for cell, _ in top]
    labels = [f"#{k + 1}: {'rest, ' if cell == 0 else ''}{cnt} beats" for k, (cell, cnt) in enumerate(top)]
    ticks = {0: "1", 3: "e", 4: "trip", 6: "&", 8: "trip", 9: "a"}
    fig = go.Figure(go.Heatmap(z=z, x=list(range(steps)), y=labels, colorscale=[[0, "#f3f5f7"], [1, INK]],
                               showscale=False, xgap=3, ygap=3, hoverinfo="skip"))
    fig.update_xaxes(tickvals=list(ticks), ticktext=list(ticks.values()), showgrid=False, side="top", showline=False,
                     ticks="")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, 60 + 26 * len(top), legend=False)


def fig_ssm(f):
    wt = np.array(f["windows"]["t"])
    ssm = f["images"]["ssm"]
    names = {"timbre": "Timbre (MFCC)", "rhythm": "Rhythm (tempogram)", "symbolic": "Pattern (transcription)"}
    fig = make_subplots(rows=1, cols=3, subplot_titles=[names[k] for k in ssm], horizontal_spacing=0.06)
    for i, (k, z) in enumerate(ssm.items(), 1):
        fig.add_trace(go.Heatmap(z=z, x=wt, y=wt, colorscale=SEQ, zmin=0, zmax=1, showscale=i == 3,
                                 colorbar=dict(title=dict(text="similarity"), thickness=10),
                                 hovertemplate="%{x:.0f} s vs %{y:.0f} s: %{z}<extra></extra>"), row=1, col=i)
        fig.update_yaxes(autorange="reversed", scaleanchor=f"x{'' if i == 1 else i}", showgrid=False, row=1, col=i)
        fig.update_xaxes(showgrid=False, row=1, col=i)
    ticks = np.arange(0, wt[-1] + 1, 120)
    fig.update_xaxes(tickvals=ticks, ticktext=[mmss(t) for t in ticks])
    fig.update_yaxes(tickvals=ticks, ticktext=[mmss(t) for t in ticks])
    return style(fig, 420, legend=False)


def fig_hands(f):
    hands = Counter(f["groups"]["hands"])
    xs = list(range(0, max(hands) + 1))
    fig = go.Figure(go.Bar(x=[str(x) for x in xs], y=[hands.get(x, 0) for x in xs],
                           marker=dict(color=[INK2 if x <= 2 else INK for x in xs], line=dict(width=0)),
                           hovertemplate="%{x} hands: %{y} stroke groups<extra></extra>"))
    fig.add_vline(x=2.5, line=dict(color=MUTED, width=1.5, dash="dash"), annotation_text="two hands",
                  annotation_position="top left")
    fig.update_xaxes(title_text="hands needed by one stroke group (hits within 30 ms)", type="category")
    fig.update_yaxes(type="log", title_text="stroke groups (log scale)", **LOG_COUNTS)
    fig.update_layout(bargap=0.35)
    return style(fig, 300, legend=False)


def fig_phrases(f, dur):
    g = np.array(f["groups"]["t"])
    brk = np.flatnonzero(np.diff(g) >= 0.5)
    starts, ends = np.r_[0, brk + 1], np.r_[brk, len(g) - 1]
    fig = go.Figure(go.Bar(y=["phrases"] * len(starts), x=g[ends] - g[starts], base=g[starts], orientation="h",
                           marker=dict(color=INK2, line=dict(width=0)),
                           customdata=[[mmss(g[a]), mmss(g[b]), g[b] - g[a], b - a + 1] for a, b in zip(starts, ends)],
                           hovertemplate="%{customdata[0]} to %{customdata[1]} (%{customdata[2]:.1f} s, "
                                         "%{customdata[3]} strokes)<extra></extra>"))
    time_ticks(fig, dur, 30, title_text="time (m:ss)")
    fig.update_yaxes(showgrid=False, showticklabels=False)
    fig.update_layout(bargap=0.3)
    return style(fig, 150, legend=False)


def fig_activity(f, dur):
    w = f["windows"]
    r = np.array(w["hits_per_s"], dtype=float)
    a = np.array(w["audio_activity"], dtype=float)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=w["t"], y=r / np.nanmax(r), name="transcribed hits per second", mode="lines",
                             line=dict(width=2, color=INK), hovertemplate="%{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=w["t"], y=a, name="audio onset strength (no transcription)", mode="lines",
                             line=dict(width=2, color=MUTED), hovertemplate="%{y:.2f}<extra></extra>"))
    time_ticks(fig, dur, 30, title_text="time (m:ss)")
    fig.update_yaxes(title_text="relative to its own maximum", range=[0, 1.05])
    return style(fig, 320)


def fig_val_recall(v):
    pc = v["per_category"]
    cs = [c for c in CATS if c in pc and pc[c]["true"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=cs, y=[pc[c]["recall"] for c in cs], name="recall (true hits found)",
                         marker=dict(color=INK, line=dict(width=0)), hovertemplate="%{x}: %{y:.0%}<extra></extra>"))
    fig.add_trace(go.Bar(x=cs, y=[pc[c]["precision"] for c in cs], name="precision (transcribed hits that are real)",
                         marker=dict(color=MUTED, line=dict(width=0)), hovertemplate="%{x}: %{y:.0%}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    return style(fig, 320)


def fig_val_timing(v):
    fig = go.Figure()
    for k, name, color in (("raw", "transcription alone", MUTED), ("refined", "refined on the audio", INK)):
        fig.add_trace(go.Histogram(x=v["timing_error_ms"][k], name=name, xbins=dict(start=-25, end=25, size=1),
                                   marker=dict(color=color, line=dict(width=1, color="white")), opacity=0.7,
                                   hovertemplate="%{x} ms: %{y}<extra></extra>"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="onset error (ms)", range=[-25, 25])
    fig.update_yaxes(title_text="hits")
    return style(fig, 320)


def fig_val_level(v):
    lv = v["level_vs_velocity"]
    cats, vel, lev = np.array(lv["cat"]), np.array(lv["velocity"]), np.array(lv["level_db"])
    show = [c for c in ("kick", "snare", "toms", "ride", "hi-hat") if c in lv["spearman"]]
    fig = make_subplots(rows=1, cols=len(show), shared_yaxes=True, horizontal_spacing=0.03,
                        subplot_titles=[f"{c}: rho {lv['spearman'][c]:.2f}" for c in show])
    for i, c in enumerate(show, 1):
        m = cats == c
        fig.add_trace(go.Scatter(x=vel[m], y=lev[m], mode="markers", name=c,
                                 marker=dict(size=8, color=drums.COLORS[c], opacity=0.75, line=dict(width=1, color="white")),
                                 hovertemplate="velocity %{x}, level %{y} dB<extra></extra>"), row=1, col=i)
        fig.update_xaxes(title_text="true velocity", row=1, col=i)
    fig.update_yaxes(title_text="audio level (dB)", row=1, col=1)
    return style(fig, 320, legend=False)


def fig_coverage(v, f, vlabel):
    rows = [(f"{vlabel}: written", dict(v["true_notes"])), (f"{vlabel}: transcribed", dict(v["transcribed_notes"]))]
    if vlabel != "this solo":
        rows.append(("this solo: transcribed", Counter(f["hits"]["note"])))
    fig = go.Figure()
    for r, (label, counts) in enumerate(rows):
        for c in CATS:
            ns = [n for n in range(35, 82) if drums.category(n) == c]
            present = [n for n in ns if counts.get(n)]
            absent = [n for n in ns if not counts.get(n)]
            if present:
                fig.add_trace(go.Scatter(x=present, y=[label] * len(present), mode="markers", name=c,
                                         legendgroup=c, showlegend=r == 0,
                                         marker=dict(symbol="square", size=13, color=drums.COLORS[c]),
                                         customdata=[[drums.name(n), counts[n]] for n in present],
                                         hovertemplate="%{customdata[0]} (%{x}): %{customdata[1]} hits<extra></extra>"))
            if absent:
                fig.add_trace(go.Scatter(x=absent, y=[label] * len(absent), mode="markers", showlegend=False,
                                         marker=dict(symbol="square-open", size=13, color=LIGHT),
                                         customdata=[drums.name(n) for n in absent],
                                         hovertemplate="%{customdata} (%{x}): none<extra></extra>"))
    fig.update_xaxes(title_text="GM percussion note", dtick=5, range=[34, 82], showgrid=False)
    fig.update_yaxes(categoryorder="array", categoryarray=[r[0] for r in rows][::-1], showgrid=False)
    return style(fig, 230)


# ---------------------------------------------------------------- page

def tile(value, label):
    return f'<div class="tile"><div class="v">{escape(value)}</div><div class="k">{escape(label)}</div></div>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("validation", help="validate.py output for a solo with known MIDI")
    ap.add_argument("out")
    ap.add_argument("--audio")
    ap.add_argument("--youtube", help="source video to link instead of hosting the recording")
    ap.add_argument("--title", required=True)
    ap.add_argument("--validation-label", required=True,
                    help="whose true MIDI the validation used: 'this solo' or 'generated solos'")
    ap.add_argument("--native", help="features.json computed from a generated solo's own MIDI")
    a = ap.parse_args()

    f = json.loads(Path(a.features).read_text())
    v = json.loads(Path(a.validation).read_text())
    nat = json.loads(Path(a.native).read_text()) if a.native else None
    vl = a.validation_label
    s = f["scalars"]
    dur = s["duration_s"]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    js = out.parent.parent / "plotly.min.js"
    if not js.exists():
        js.write_text(get_plotlyjs())
    reliable = {c for c, r in v["level_vs_velocity"]["spearman"].items() if r >= 0.7}
    w = f["windows"]
    center = float(np.array(w["t"])[int(np.nanargmax(np.array(w["intensity"], dtype=float)))])

    figs = {}

    def put(key, fig):
        figs[key] = pio.to_html(fig, include_plotlyjs=False, full_html=False, config=CONFIG, div_id=key)

    put("roll", fig_drum_roll(f, center))
    put("timeline", fig_timeline(f, dur))
    put("mel", fig_mel(f, dur))
    put("notes", fig_notes(f))
    put("loud_hist", fig_loudness_hist(f))
    put("levels", fig_levels(f, reliable))
    put("contour", fig_level_contour(f, dur, reliable))
    put("snare", fig_snare_hist(f))
    put("tempogram", fig_tempogram(f, dur))
    put("tempo_hist", fig_tempo_hist(f))
    put("ioi", fig_ioi(f))
    put("clock", fig_clock(f))
    put("grid", fig_grid_profile(f))
    put("micro", fig_evenness(f))
    put("vocab", fig_vocab(f))
    put("cells", fig_top_cells(f))
    put("ssm", fig_ssm(f))
    put("hands", fig_hands(nat or f))
    put("phrases", fig_phrases(f, dur))
    put("activity", fig_activity(f, dur))
    put("val_recall", fig_val_recall(v))
    put("val_timing", fig_val_timing(v))
    put("val_level", fig_val_level(v))
    put("coverage", fig_coverage(v, f, vl))

    rel = lambda p: escape(os.path.relpath(Path(p).resolve(), out.parent.resolve()))
    # hovering a time chart plays that moment; page times count from the start of the analysed part
    timed = {"src": os.path.relpath(Path(a.audio).resolve(), out.parent.resolve()), "offset": f["clip"]["segment"][0],
             "charts": ["roll", "timeline", "mel", "contour", "tempogram", "activity", "ssm"]} if a.audio else None
    sound_tags = sound.tags("../", solo=timed)
    title = a.title
    notes = Counter(f["hits"]["note"])
    tiles = "".join([
        tile(mmss(dur), "duration"),
        tile(f"{s['n_hits']:,}", "transcribed hits"),
        tile(f"{s['hits_per_s']:.1f}/s", f"average density (peak {s['peak_hits_per_s']}/s)"),
        tile(f"{s['distinct_notes']}" if not nat else f"{nat['scalars']['distinct_notes']} / {s['distinct_notes']}",
             f"distinct drums ({s['distinct_categories']} families)" if not nat else "distinct drums, written / heard"),
        tile(f"{np.median(f['beats']['ibi_bpm']):.0f} BPM", f"tracked pulse, beat-to-beat spread {s['ibi_cv']:.1%}"),
        tile(f"{s['lra_lu']:.0f} LU", "loudness range (EBU R128)"),
        tile(f"{s['n_sections']}", f"sections (median {s['section_median_s']:.0f} s)"),
        tile(f"{s['rhythm_cell_repeat_rate']:.0%}", "beats that reuse an earlier rhythm"),
        tile(f"{s['intensity_peak_pos']:.0%}", "where the peak intensity falls"),
        tile(f"{(nat or f)['scalars']['limb_violations_per_min']:.1f}/min",
             "stroke groups needing 3+ hands" + (", as written" if nat else "")),
    ])

    if a.audio:
        listen = f'<h2>Listen</h2><audio controls preload="none" src="{rel(a.audio)}"></audio>'
    elif a.youtube:
        seg0 = int(f["clip"]["segment"][0])
        listen = (f'<h2>Listen</h2><p class="note"><a href="{escape(a.youtube)}&t={seg0}s">Listen on YouTube</a>, '
                  f'starting where the analyzed part begins ({mmss(seg0)}).</p>')
    else:
        listen = ""

    jitter_note = (f"Timing jitter {s['stroke_jitter_ms']:.1f} ms ({s['stroke_jitter_rel']:.0%} of the stroke spacing). "
                   "Measurement error was 1.6 ms on clean audio and is likely higher on a live recording."
                   if s["stroke_jitter_ms"] is not None else
                   f"Timing jitter is not measurable, since only {s['even_run_strokes']} strokes sit in steady runs "
                   f"({s['steady_run_share']:.0%} of the solo).")
    seg0, seg1 = f["clip"]["segment"]
    segment_note = (f", analyzed from {mmss(seg0)} to {mmss(seg1)} of the recording, and times on this page "
                    f"count from {mmss(seg0)}") if seg0 > 0.5 else ""
    ps = (nat or f)["scalars"]
    playability_note = (
        f"Counted in the solo's own MIDI: {ps['limb_violations']} groups need three or more hands "
        f"({ps['limb_violations_per_min']:.1f} per minute), up to {ps['max_hands_in_group']} at once."
        if nat else
        f"A human played this, so the {ps['limb_violations']} groups that need three or more hands "
        f"({ps['limb_violations_per_min']:.1f} per minute) are transcription artifacts or grace notes closer than 30 ms. "
        "That is the noise floor when this check runs on generated solos. The check treats every drum except kick and "
        "hi-hat pedal as hand-played, so a foot-pedal cowbell or clave block also counts here.")
    ts = v["timing_summary"]
    val_html = f"""
<h2>Transcription accuracy</h2>
<p class="note">{"This solo's true notes are known, so the transcriber is scored on it directly." if vl == "this solo" else
f"The recordings have no ground-truth MIDI, so the transcriber is scored on the {len(v['solos'])} generated solos, whose true notes are known. Clean synthesized audio is easier than a live kit, so treat these as best-case numbers."}
Onset F1 {v['f1']:.0%} at a {v['tolerance_ms']:.0f} ms tolerance with the drum family required to match
(recall {v['recall']:.0%}, precision {v['precision']:.0%}).</p>
<h3>Hits found, by family</h3>{figs['val_recall']}
<h3>Timing error</h3>
<p class="note">Median error {ts['raw']['median_abs_ms']:.1f} ms from the transcription alone, {ts['refined']['median_abs_ms']:.1f} ms after
snapping each stroke to the sharpest nearby onset in the audio ({ts['refined']['within_5ms']:.0%} within 5 ms). Every timing chart on
this page uses refined times.</p>{figs['val_timing']}
<h3>Does audio level track how hard a drum was hit?</h3>
<p class="note">The transcriber outputs every note at velocity 100, so dynamics come from the audio, from the peak energy in the
instrument's frequency band right after each hit. Families with rho below 0.7 are left out of the dynamics charts above.</p>{figs['val_level']}
<h3>Which drums can the transcriber name?</h3>
<p class="note">Generated solos can use all 47 GM percussion notes, but the transcriber names fewer of them (about 20 in a
typical solo), so the instrument range of a generated solo comes from its own MIDI.</p>{figs['coverage']}
<h3>Does the transcription follow the audio?</h3>
<p class="note">Transcribed density next to a transcription-free measure (mean spectral flux), per 2 s window. Correlation
{s['density_activity_corr']:.2f}.</p>{figs['activity']}"""

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
{og(f"{title}: Drum Throne", "One solo's measurements and charts, from Drum Throne: an experimental benchmark for "
    "composing drum solos with language models.", f"{out.parent.name}/")}
<script src="../plotly.min.js"></script>
<style>
body{{font-family:{FONT};color:{INK};background:#fff;margin:0;line-height:1.45}}
main{{max-width:1000px;margin:0 auto;padding:36px 24px 40px}}
h1{{font-size:28px;margin:0 0 6px}}
.sub{{color:{INK2};margin:0 0 24px;font-size:14px}}
h2{{font-size:20px;margin:56px 0 6px;padding-top:18px;border-top:1px solid {GRID}}}
{ACCENT_CSS.format()}
h3{{font-size:15px;margin:28px 0 2px}}
p.note{{color:{INK2};font-size:14px;margin:2px 0 8px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin:8px 0 8px}}
.tile{{border:1px solid {GRID};border-radius:8px;padding:12px 14px}}
.tile .v{{font-size:24px;font-weight:600;color:{INK}}}
.tile .k{{font-size:12.5px;color:{INK2}}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media (max-width:860px){{.two{{grid-template-columns:1fr}}}}
table{{border-collapse:collapse;font-size:13px;margin-top:8px}}
td{{padding:3px 12px;border-bottom:1px solid {GRID}}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
audio{{width:100%;margin:4px 0 8px}}
summary{{cursor:pointer;color:{INK2};margin-top:24px}}
{FORK_CSS}
{NAV_CSS}
</style></head><body>{FORK}<main>
{nav("../")}
<h1>{escape(title)}</h1>
<p class="sub">{mmss(dur)} of solo drums{segment_note}. The audio is analyzed directly, and the notes come from a MuScriptor drum
transcription ({s['n_hits']:,} hits), with timing refined on the audio.</p>
<div class="tiles">{tiles}</div>
{listen}

<h2>Overview</h2>
<h3>Drum roll</h3>
<p class="note">Every transcribed hit, one row per drum, with the tracked beat along the bottom. Opens on the 20 seconds
around the most intense moment. Drag to pan, scroll or box-zoom, double-click to see the whole solo.</p>
{figs['roll']}
<h3>Over time</h3>
<p class="note">Density by instrument, loudness, tempo and novelty on one time axis. Dotted lines mark the
{s['n_sections']} section boundaries found in the self-similarity analysis below.</p>
{figs['timeline']}
<h3>Spectrogram</h3>
<p class="note">Mel spectrogram. Kick and floor tom sit at the bottom, snare and toms in the middle, cymbals across the top.</p>
{figs['mel']}

<h2>Instrument range</h2>
<p class="note">{s['distinct_notes']} distinct GM drum notes in {s['distinct_categories']} families. Note entropy
{s['note_entropy_bits']:.2f} bits ({s['note_entropy_norm']:.0%} of the maximum for {s['distinct_notes']} notes); the three
most-used notes take {sum(c for _, c in notes.most_common(3)) / sum(notes.values()):.0%} of the hits. Snare {s['share_snare']:.0%}, hi-hat {s['share_hi-hat']:.0%}, kick {s['share_kick']:.0%},
toms {s['share_toms']:.0%}, cymbals {s['share_ride'] + s['share_crash']:.0%}.</p>
{figs['notes']}

<h2>Dynamics</h2>
<div class="two"><div><h3>Loudness distribution</h3>
<p class="note">Integrated {s['integrated_lufs']:.1f} LUFS, loudness range {s['lra_lu']:.1f} LU, crest factor
{s['crest_db']:.1f} dB.</p>{figs['loud_hist']}</div>
<div><h3>How hard each drum is hit</h3>
<p class="note">Per-hit level from the audio, for the families where it tracks velocity.</p>{figs['levels']}</div></div>
<div class="two"><div><h3>Snare: ghost notes to accents</h3>
<p class="note">Interquartile range {s['level_iqr_db_snare']:.1f} dB.</p>{figs['snare']}</div>
<div><h3>Dynamic contour</h3><p class="note">Median hit level per family over time.</p>{figs['contour']}</div></div>

<h2>Tempo consistency</h2>
<p class="note">Tracked pulse {np.median(f['beats']['ibi_bpm']):.0f} BPM (10th to 90th percentile {s['tempo_p10_bpm']:.0f} to
{s['tempo_p90_bpm']:.0f}). Beat-to-beat variation {s['ibi_cv']:.1%} overall and {s['local_ibi_cv_median']:.1%} within
8-beat stretches; drift {s['tempo_drift_bpm_per_min']:+.2f} BPM per minute. Which pulse level counts as "the beat" is ambiguous in
a solo; the tracker picked this one, and the tempogram shows the others.</p>
<h3>Tempogram</h3><p class="note">Periodicity strength at each tempo over time (dark = strong), with the tracked beat on top.</p>
{figs['tempogram']}
<h3>Beat-to-beat tempo</h3>{figs['tempo_hist']}

<h2>Rhythm and complexity</h2>
<h3>Time between strokes</h3>
<p class="note">Peaks line up with the subdivisions the drummer uses. Median {s['ioi_median_ms']:.0f} ms, entropy
{s['ioi_entropy_bits']:.2f} bits, nPVI {s['npvi']:.1f} (0 would be perfectly even spacing).</p>{figs['ioi']}
<h3>Position in the beat</h3>
<p class="note">Where in the beat each drum lands, one full turn per beat, with 16th positions at the quarters and triplets at the thirds.</p>
{figs['clock']}
<div class="two"><div><h3>Subdivisions</h3>
<p class="note">Each hit snapped to the nearest of 12 positions per tracked beat. Grid lock {s['grid_lock']:.2f}
(1 = every hit exactly on a 16th or triplet position, 0 = no relation to the grid). The lower the grid lock, the less
these shares mean.</p>{figs['grid']}</div>
<div><h3>Stroke evenness</h3>
<p class="note">Inside steady runs ({s['even_run_strokes']:,} strokes), each stroke is compared with the midpoint of the strokes two
either side, so swing counts as feel, not error. This ignores tempo drift entirely. {jitter_note}</p>{figs['micro']}</div></div>
<h3>Rhythmic vocabulary</h3>
<p class="note">Each beat reduced to a 12-step pattern. {s['rhythm_cell_vocab']} distinct rhythms across {s['n_beats']:,} beats
({s['rhythm_cell_repeat_rate']:.0%} of beats reuse an earlier one); {s['orch_cell_vocab']} distinct once the choice of drum counts.
Lempel-Ziv complexity {s['lz_relative']:.2f} of a shuffled version of the same hits (1.0 = no structure).</p>
{figs['vocab']}
<h3>Most-used one-beat rhythms</h3>{figs['cells']}

<h2>Structure</h2>
<p class="note">Each point compares two 2-second windows, relative to the solo's average (dark = alike).
Squares on the diagonal are sections, and off-diagonal blocks are returns to earlier material. The three views show how it sounds, how it pulses, and what the transcription says was played.
{s['n_sections']} sections, median {s['section_median_s']:.0f} s, with peak intensity at {s['intensity_peak_pos']:.0%} of the solo.</p>
{figs['ssm']}
<h3>Phrasing</h3>
<p class="note">Stretches of playing separated by silences of at least 0.5 s: {s['n_phrases']} phrases, median
{s['phrase_median_s']:.1f} s; rests take up {s['rest_time_frac']:.0%} of the solo.</p>{figs['phrases']}

<h2>Playability</h2>
<p class="note">Hits closer than 30 ms are grouped as one stroke, and each stroke is counted by the hands and feet it needs.
{playability_note}</p>{figs['hands']}
{val_html}
</main>{FOOTER}{MOBILE_JS}{sound_tags}{COUNTER}</body></html>"""
    out.write_text(page)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
