#!/usr/bin/env python3
"""Comparison page for the whole corpus (humans, models, both) and the bracket review page.

usage: uv run python report_corpus.py
"""
import json
import os
from html import escape
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy import ndimage

import drums
import pipeline
import sound
from bracket import OTHER_MIN
from score import AXES, Z0
from report_solo import (ACCENT_CSS, CONFIG, COUNTER, FOOTER, FORK, FORK_CSS, MOBILE_JS, NAV_CSS, nav, og, FONT, GRID, INK, INK2, LIGHT, MUTED,
                         SEQ, hist_log, mmss, style)

OUT = pipeline.OUT
SITE = pipeline.SITE
REVIEW = pipeline.HERE / "review"  # internal tools, never published
HUMAN_C, HUMAN_LIGHT, HUMAN_BAND = "#57606a", "#d0d7de", "rgba(87,96,106,0.16)"
MACHINE_C = "#DC267F"
SYMBOLS = ["diamond", "square", "triangle-up", "pentagon", "star", "hexagram", "cross", "x"]
CATS = list(drums.CATEGORIES)
GRID_X = np.linspace(0, 100, 51)


def load(items):
    data = {}
    for it in items:
        d = OUT / it["id"]
        e = {"item": it, "f": json.loads((d / "features.json").read_text())}
        if it["group"] != "human":
            e["native"] = json.loads((d / "features_native.json").read_text())
            e["val"] = json.loads((OUT / "validation" / f"{it['id']}.json").read_text())
        e["bracket"] = json.loads((OUT / "brackets" / f"{it['id']}.json").read_text())
        data[it["id"]] = e
    return data


def marker_for(it, models):
    if it["group"] == "human":
        return dict(symbol="circle", size=10, color=HUMAN_C, line=dict(width=1.5, color="white"))
    return dict(symbol="diamond", size=12, color=MACHINE_C, line=dict(width=1.5, color="white"))


def machine_groups(items):
    """The generated solos as one legend group."""
    gen = [it for it in items if it["group"] != "human"]
    return [], [(f"generated ({len(gen)} solo{'s' if len(gen) > 1 else ''})", gen)]


def audio_src(it):
    """Page-relative path of the audio a page plays for this solo, or None when it is not hosted."""
    audio = pipeline.page_audio(it)
    return os.path.relpath(audio.resolve(), SITE) if audio else None


def jitter(n, seed, amp=0.18):
    return np.random.default_rng(seed).uniform(-amp, amp, n)


def html_of(fig, key):
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config=CONFIG, div_id=key)


def resample(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ok = ~np.isnan(y)
    return np.interp(GRID_X, x[ok], y[ok])


# ---------------------------------------------------------------- scorecard

def fig_score_curve():
    """How one measurement turns into points: flat across the middle half of the recorded solos, falling off outside."""
    z = np.linspace(-4, 4, 401)
    fig = go.Figure()
    fig.add_vrect(x0=-Z0, x1=Z0, fillcolor=HUMAN_BAND, line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=z, y=100 * np.exp(-0.5 * np.clip(np.abs(z) - Z0, 0, None) ** 2), mode="lines",
                             line=dict(width=3, color=INK), name="every measurement except playability",
                             hovertemplate="%{y:.0f} points<extra></extra>"))
    fig.add_trace(go.Scatter(x=z, y=100 * np.exp(-0.5 * np.clip(z - Z0, 0, None) ** 2), mode="lines",
                             line=dict(width=2, color=MUTED, dash="dash"),
                             name="playability: only too many impossible strokes costs points",
                             hovertemplate="%{y:.0f} points<extra></extra>"))
    fig.add_annotation(x=0, y=101, text="middle half of the recorded solos", showarrow=False, yanchor="bottom",
                       font=dict(size=12, color=INK2))
    fig.update_xaxes(tickvals=[-3, -1.5, 0, 1.5, 3], ticktext=["far below", "below", "recorded median", "above", "far above"],
                     range=[-4, 4], title_text="measurement, relative to the recorded solos")
    fig.update_yaxes(range=[0, 112], title_text="points for that measurement")
    return style(fig, 340)


def provider(it):
    return it["model"].split("/")[0]


# every model in the main set: display name and maker
MODEL_NAMES = {
    "anthropic/claude-opus-5.5": ("Claude Opus 5.5", "Anthropic"),
    "anthropic/claude-sonnet-5": ("Claude Sonnet 5", "Anthropic"),
    "anthropic/claude-fable-5.1": ("Claude Fable 5.1", "Anthropic"),
    "google/gemini-3.1-pro-preview": ("Gemini 3.1 Pro (preview)", "Google"),
    "google/gemini-3.8-flash": ("Gemini 3.8 Flash", "Google"),
    "openai/gpt-6-astra": ("GPT-6 Astra", "OpenAI"),
    "openai/gpt-6-astra-pro": ("GPT-6 Astra Pro", "OpenAI"),
    "openai/gpt-6-sol": ("GPT-6 Sol", "OpenAI"),
    "openai/gpt-6-sol-pro": ("GPT-6 Sol Pro", "OpenAI"),
    "deepseek/deepseek-v4.1-flash": ("DeepSeek V4.1 Flash", "DeepSeek"),
    "moonshotai/kimi-k3": ("Kimi K3", "Moonshot AI"),
    "xiaomi/mimo-v2.6-pro": ("MiMo V2.6 Pro", "Xiaomi"),
    "qwen/qwen3.8-max-0902": ("Qwen3.8 Max 0902", "Alibaba"),
    "z-ai/glm-5.3": ("GLM 5.3", "Z.ai"),
    "x-ai/grok-4.7": ("Grok 4.7", "xAI"),
    "meta/muse-spark-1.3": ("Muse Spark 1.3", "Meta"),
    "minimax/minimax-m3": ("MiniMax M3", "MiniMax"),
}


def model_name(it):
    """Display name, maker and thinking setting of a generated solo; no setting is the provider's default."""
    base, _, setting = it["model"].partition("_")
    if base not in MODEL_NAMES:
        raise SystemExit(f"no display name for {base}: add it to MODEL_NAMES")
    name, maker = MODEL_NAMES[base]
    return (f"{name} · {setting}" if setting else name), maker, setting or "default"


def maker(it):
    return model_name(it)[1]


def fig_overall(scores, items, models):
    """Humans in one row, then one row per model provider, best provider first."""
    by_id = {s["id"]: s for s in scores["solos"]}
    fig = go.Figure()
    hum = [s for s in scores["solos"] if s["group"] == "human"]
    hv = np.array([s["overall"] for s in hum])
    fig.add_shape(type="rect", x0=np.percentile(hv, 25), x1=np.percentile(hv, 75), y0=-0.3, y1=0.3, yref="y",
                  fillcolor=HUMAN_BAND, line=dict(width=0), layer="below")
    fig.add_trace(go.Scatter(x=hv, y=np.zeros(len(hv)) + jitter(len(hv), 1), mode="markers", name="recorded solo",
                             marker=marker_for({"group": "human"}, models), customdata=[s["label"] for s in hum],
                             meta=[s["id"] for s in hum], hovertemplate="%{customdata}<br>%{x:.1f} garths<extra></extra>"))
    gen = [it for it in items if it["group"] != "human"]
    provs = sorted({maker(it) for it in gen},
                   key=lambda p: -max(by_id[it["id"]]["overall"] for it in gen if maker(it) == p))
    rows = [f"Recorded solos ({len(hum)})"]
    for k, prov in enumerate(provs, 1):
        its = [it for it in gen if maker(it) == prov]
        rows.append(f"{prov} ({len(its)})")
        ss = [by_id[it["id"]] for it in its]
        fig.add_trace(go.Scatter(x=[s["overall"] for s in ss], y=np.full(len(ss), -k) + jitter(len(ss), k + 1, 0.12),
                                 mode="markers", name=machine_groups(items)[1][0][0], legendgroup="gen", showlegend=k == 1,
                                 marker=marker_for(its[0], models),
                                 customdata=[model_name(it)[0] for it in its], meta=[s["id"] for s in ss],
                                 hovertemplate="%{customdata}<br>%{x:.1f} garths<extra></extra>"))
    fig.add_vline(x=float(np.median(hv)), line=dict(color=HUMAN_C, width=1, dash="dot"),
                  annotation_text=f"recorded median {np.median(hv):.0f}", annotation_position="top")
    fig.update_yaxes(tickvals=[-k for k in range(len(rows))], ticktext=rows, range=[-len(rows) + 0.4, 0.6], showgrid=False)
    fig.update_xaxes(range=[0, 100], title_text="garths (0 to 100)")
    return style(fig, 130 + 44 * len(rows))


def fig_scoregrid(solos):
    """Axis and overall scores, one row per solo, in the order given."""
    axes = list(AXES) + ["Overall"]
    z = [[s["axis_scores"][a] for a in axes[:-1]] + [s["overall"]] for s in solos]
    labels = [s["short"] if s["group"] == "human" else f"<span style='color:{MACHINE_C}'><b>{escape(s['short'])}</b></span>"
              for s in solos]
    fig = go.Figure(go.Heatmap(z=z, x=axes, y=labels, colorscale=SEQ, zmin=0, zmax=100, xgap=2, ygap=2,
                               text=[[f"{v:.0f}" for v in row] for row in z], texttemplate="%{text}",
                               textfont=dict(size=11), colorbar=dict(title=dict(text="score"), thickness=10),
                               meta=[s["id"] for s in solos],
                               hovertemplate="%{y}<br>%{x}: %{z:.1f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(side="top", showgrid=False, showline=False, ticks="")
    fig.update_yaxes(automargin=True)
    return style(fig, 80 + 24 * len(solos), legend=False)


def fig_axes_strip(scores, items, models):
    axes = list(scores["axes"])
    fig = go.Figure()
    hum = [s for s in scores["solos"] if s["group"] == "human"]
    for k, a in enumerate(axes):
        hv = [s["axis_scores"][a] for s in hum]
        fig.add_trace(go.Scatter(x=hv, y=np.full(len(hv), -k) + jitter(len(hv), k, 0.2), mode="markers",
                                 name="recorded solo", legendgroup="human", showlegend=k == 0,
                                 marker=dict(size=8, color=HUMAN_C, opacity=0.8, line=dict(width=1, color="white")),
                                 customdata=[s["label"] for s in hum], meta=[s["id"] for s in hum],
                                 hovertemplate=f"%{{customdata}}<br>{a}: %{{x:.0f}}<extra></extra>"))
    _, groups = machine_groups(items)
    by_id = {s["id"]: s for s in scores["solos"]}
    for name, its in groups:
        ss = [by_id[it["id"]] for it in its]
        for k, a in enumerate(axes):
            fig.add_trace(go.Scatter(x=[s["axis_scores"][a] for s in ss], y=np.full(len(ss), -k) + jitter(len(ss), 50 + k, 0.08),
                                     mode="markers", name=name, legendgroup=name, showlegend=k == 0,
                                     marker=marker_for(its[0], models), customdata=[s["label"] for s in ss],
                                     meta=[s["id"] for s in ss],
                                     hovertemplate=f"%{{customdata}}<br>{a}: %{{x:.0f}}<extra></extra>"))
    fig.update_yaxes(tickvals=[-k for k in range(len(axes))], ticktext=axes, showgrid=False,
                     range=[-len(axes) + 0.5, 0.5])
    fig.update_xaxes(range=[-2, 102], title_text="group score")
    return style(fig, 120 + 56 * len(axes))


DIRECTION = {"higher": "more is better", "lower": "less is better", "two": "typical is best",
             "task": "full points inside the shaded window, generated solos only"}


def fig_axis_metrics(axis, specs, scores, items, models):
    fig = make_subplots(rows=len(specs), cols=1, vertical_spacing=0.55 / len(specs),
                        subplot_titles=[f"{m['label']}  ({DIRECTION[m['direction']]})" for m in specs])
    hum = [s for s in scores["solos"] if s["group"] == "human"]
    _, groups = machine_groups(items)
    by_id = {s["id"]: s for s in scores["solos"]}
    for r, m in enumerate(specs, 1):
        k = m["key"]
        if m["direction"] == "task":  # generated solos only, against the length the prompt asks for
            lo, hi = scores["length"]["window_s"]
            fig.add_shape(type="rect", x0=lo, x1=hi, y0=-0.4, y1=0.4, fillcolor="rgba(184,134,11,0.18)",
                          line=dict(width=0), layer="below", row=r, col=1)
        else:
            b = scores["bands"][k]
            fig.add_shape(type="rect", x0=b["p25"], x1=b["p75"], y0=-0.4, y1=0.4, fillcolor=HUMAN_BAND,
                          line=dict(width=0), layer="below", row=r, col=1)
            fig.add_shape(type="line", x0=b["min"], x1=b["max"], y0=0, y1=0, line=dict(color=HUMAN_LIGHT, width=2),
                          layer="below", row=r, col=1)
        hm = [s for s in hum if k in s["metrics"]]
        hv = [s["metrics"][k] for s in hm]  # none on a task measurement
        fig.add_trace(go.Scatter(x=hv, y=jitter(len(hv), r, 0.22), mode="markers", name="recorded solo",
                                 legendgroup="human", showlegend=r == 1,
                                 marker=dict(size=8, color=HUMAN_C, opacity=0.85, line=dict(width=1, color="white")),
                                 customdata=[s["label"] for s in hm], meta=[s["id"] for s in hm],
                                 hovertemplate="%{customdata}: %{x:.3g}<extra></extra>"),
                      row=r, col=1)
        for name, its in groups:
            ss = [by_id[it["id"]] for it in its if k in by_id[it["id"]]["metrics"]]
            fig.add_trace(go.Scatter(x=[s["metrics"][k] for s in ss], y=jitter(len(ss), 90 + r, 0.1), mode="markers",
                                     name=name, legendgroup=name, showlegend=r == 1, marker=marker_for(its[0], models),
                                     customdata=[[s["label"], s["metric_scores"][k]] for s in ss], meta=[s["id"] for s in ss],
                                     hovertemplate="%{customdata[0]}: %{x:.3g} (score %{customdata[1]:.0f})<extra></extra>"),
                          row=r, col=1)
        fig.update_yaxes(range=[-0.6, 0.6], showticklabels=False, showgrid=False, row=r, col=1)
        if m["transform"] in ("log", "log1p") and min(hv) > 0:
            fig.update_xaxes(type="log", row=r, col=1)
    fig.update_annotations(font=dict(size=12, color=INK), xanchor="left", x=0)
    return style(fig, 70 + 130 * len(specs), legend=False)


# ---------------------------------------------------------------- shape over time

def arcs(data):
    out = {}
    for sid, e in data.items():
        f = e["f"]
        w, s = f["windows"], f["scalars"]
        x = np.array(w["t"]) / s["duration_s"] * 100
        dens = np.array(w["hits_per_s"], dtype=float)
        loud = np.array(w["loudness_lufs"], dtype=float) - s["integrated_lufs"]
        sb = np.array(f["beats"]["smoothed"])
        bpm = 60 / np.diff(sb)
        tempo = 100 * (bpm / np.median(bpm) - 1)
        k = 9  # beats in a centred moving median, to keep sections and drop jitter
        tempo = ndimage.median_filter(tempo, size=k, mode="nearest")
        out[sid] = {"density": resample(x, ndimage.uniform_filter1d(dens / dens.mean(), 3)),
                    "loudness": resample(x, ndimage.uniform_filter1d(np.nan_to_num(loud, nan=np.nanmin(loud)), 3)),
                    "tempo": resample(sb[1:] / s["duration_s"] * 100, tempo)}
    return out


def fig_arcs(data, arc, items, models, key, ytitle):
    fig = go.Figure()
    hum = [it for it in items if it["group"] == "human"]
    H = np.array([arc[it["id"]][key] for it in hum])
    for i, it in enumerate(hum):
        fig.add_trace(go.Scatter(x=GRID_X, y=H[i], mode="lines", line=dict(width=1, color=HUMAN_LIGHT), name="recorded solo",
                                 legendgroup="human", showlegend=False, meta=it["id"],
                                 hovertemplate=f"{escape(it['short'])}: %{{y:.2f}}<extra></extra>"))
    q25, q50, q75 = np.percentile(H, [25, 50, 75], axis=0)
    fig.add_trace(go.Scatter(x=np.r_[GRID_X, GRID_X[::-1]], y=np.r_[q75, q25[::-1]], fill="toself", fillcolor=HUMAN_BAND,
                             line=dict(width=0), name="recorded middle half", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=GRID_X, y=q50, mode="lines", line=dict(width=3, color=HUMAN_C), name="recorded median",
                             hovertemplate="recorded median: %{y:.2f}<extra></extra>"))
    gen = [it for it in items if it["group"] != "human"]
    G = np.array([arc[it["id"]][key] for it in gen])
    for it, row in zip(gen, G):
        fig.add_trace(go.Scatter(x=GRID_X, y=row, mode="lines", line=dict(width=1, color="rgba(220,38,127,0.22)"),
                                 showlegend=False, meta=it["id"], hovertemplate=f"{escape(it['short'])}: %{{y:.2f}}<extra></extra>"))
    g25, g50, g75 = np.percentile(G, [25, 50, 75], axis=0)
    fig.add_trace(go.Scatter(x=np.r_[GRID_X, GRID_X[::-1]], y=np.r_[g75, g25[::-1]], fill="toself",
                             fillcolor="rgba(220,38,127,0.14)", line=dict(width=0), name="generated middle half",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=GRID_X, y=g50, mode="lines", line=dict(width=3, color=MACHINE_C), name="generated median",
                             hovertemplate="generated median: %{y:.2f}<extra></extra>"))
    fig.update_xaxes(title_text="position in the solo (%)", range=[0, 100], ticksuffix="%")
    fig.update_yaxes(title_text=ytitle)
    return style(fig, 380)


# ---------------------------------------------------------------- map, feel, rhythm

def fig_map(scores, items, models):
    fig = go.Figure()
    hum = [s for s in scores["solos"] if s["group"] == "human"]
    fig.add_trace(go.Scatter(x=[s["pca"][0] for s in hum], y=[s["pca"][1] for s in hum], mode="markers+text",
                             name="recorded solo", marker=marker_for({"group": "human"}, models),
                             text=[s["short"] for s in hum], textposition="top center",
                             textfont=dict(size=10, color=INK2), customdata=[s["label"] for s in hum],
                             meta=[s["id"] for s in hum], hovertemplate="%{customdata}<extra></extra>"))
    _, groups = machine_groups(items)
    by_id = {s["id"]: s for s in scores["solos"]}
    for name, its in groups:
        ss = [by_id[it["id"]] for it in its]
        fig.add_trace(go.Scatter(x=[s["pca"][0] for s in ss], y=[s["pca"][1] for s in ss], mode="markers+text",
                                 name=name, marker=marker_for(its[0], models), text=[s["short"] for s in ss],
                                 textposition="bottom center", textfont=dict(size=10, color=MACHINE_C),
                                 customdata=[s["label"] for s in ss], meta=[s["id"] for s in ss],
                                 hovertemplate="%{customdata}<extra></extra>"))
    ev = scores["pca"]["explained"]
    fig.update_xaxes(title_text=f"first principal component ({ev[0]:.0%} of the recorded solos' variation)", zeroline=True,
                     zerolinecolor=GRID)
    fig.update_yaxes(title_text=f"second principal component ({ev[1]:.0%})", zeroline=True, zerolinecolor=GRID)
    return style(fig, 560)


def fig_feel(scores, items, models):
    fig = go.Figure()
    hum = [s for s in scores["solos"] if s["group"] == "human" and "stroke_jitter_ms" in s["metrics"]]
    fig.add_trace(go.Scatter(x=[s["metrics"]["grid_lock"] for s in hum], y=[s["metrics"]["stroke_jitter_ms"] for s in hum],
                             mode="markers", name="recorded solo", marker=marker_for({"group": "human"}, models),
                             customdata=[s["label"] for s in hum], meta=[s["id"] for s in hum],
                             hovertemplate="%{customdata}<br>grid lock %{x:.2f}, jitter %{y:.1f} ms<extra></extra>"))
    _, groups = machine_groups(items)
    by_id = {s["id"]: s for s in scores["solos"]}
    for name, its in groups:
        ss = [by_id[it["id"]] for it in its if "stroke_jitter_ms" in by_id[it["id"]]["metrics"]]
        fig.add_trace(go.Scatter(x=[s["metrics"]["grid_lock"] for s in ss], y=[s["metrics"]["stroke_jitter_ms"] for s in ss],
                                 mode="markers", name=name, marker=marker_for(its[0], models),
                                 customdata=[s["label"] for s in ss], meta=[s["id"] for s in ss],
                                 hovertemplate="%{customdata}<br>grid lock %{x:.2f}, jitter %{y:.1f} ms<extra></extra>"))
    fig.update_xaxes(title_text="grid lock: how tightly hits sit on a steady 16th/triplet grid (0 to 1)", range=[0, 1])
    fig.update_yaxes(title_text="stroke timing jitter in steady runs (ms)", rangemode="tozero")
    return style(fig, 420)


def fig_ridgeline(data, items):
    rows = []
    for it in items:
        g = np.array(data[it["id"]]["f"]["groups"]["t"])
        x, counts, _ = hist_log(np.diff(g), 0.02, 2.0, per_octave=6)
        rows.append((float(np.median(np.diff(g))), it, np.log2(x), counts / counts.max()))
    rows.sort(key=lambda r: r[0])
    fig = go.Figure()
    for k, (_, it, lx, c) in enumerate(rows):
        human = it["group"] == "human"
        color = HUMAN_C if human else MACHINE_C
        fill = "rgba(87,96,106,0.35)" if human else "rgba(220,38,127,0.35)"
        fig.add_trace(go.Scatter(x=lx, y=k + 0.9 * c, mode="lines", line=dict(width=1.5, color=color), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=np.r_[lx, lx[::-1]], y=np.r_[k + 0.9 * c, np.full(len(lx), k)], fill="toself",
                                 fillcolor=fill, line=dict(width=0), showlegend=False, name=it["short"], meta=it["id"],
                                 hovertemplate=f"{escape(it['label'])}<extra></extra>"))
    ticks = [0.02, 0.05, 0.1, 0.2, 0.5, 1, 2]
    fig.update_xaxes(tickvals=np.log2(ticks), ticktext=["20 ms", "50 ms", "100 ms", "200 ms", "500 ms", "1 s", "2 s"],
                     title_text="time between consecutive strokes (log scale)")
    labels = [r[1]["short"] if r[1]["group"] == "human" else f"<span style='color:{MACHINE_C}'><b>{escape(r[1]['short'])}</b></span>"
              for r in rows]
    fig.update_yaxes(tickvals=list(range(len(rows))), ticktext=labels, showgrid=True, range=[-0.2, len(rows) + 0.2])
    return style(fig, 120 + 30 * len(rows), legend=False)


# ---------------------------------------------------------------- instruments, playability, structure

def fig_families(data, items):
    """Humans and generated solos as the transcriber hears them, then generated averages heard vs written."""
    share = lambda sc: [sc.get(f"share_{c}", 0) for c in CATS]
    hum = sorted([it for it in items if it["group"] == "human"],
                 key=lambda it: -data[it["id"]]["f"]["scalars"]["share_snare"])
    gen = sorted([it for it in items if it["group"] != "human"],
                 key=lambda it: -data[it["id"]]["f"]["scalars"]["share_snare"])
    rows = [(it["short"], share(data[it["id"]]["f"]["scalars"])) for it in hum]
    rows += [(f"<span style='color:{MACHINE_C}'>{escape(it['short'])}</span>", share(data[it["id"]]["f"]["scalars"]))
             for it in gen]
    rows += [(f"<span style='color:{MACHINE_C}'><b>all generated, as heard</b></span>",
              np.mean([share(data[it["id"]]["f"]["scalars"]) for it in gen], axis=0).tolist()),
             (f"<span style='color:{MACHINE_C}'><b>all generated, as written</b></span>",
              np.mean([share(data[it["id"]]["native"]["scalars"]) for it in gen], axis=0).tolist())]
    labels = [r[0] for r in rows]
    row_ids = [it["id"] for it in hum] + [it["id"] for it in gen] + [None, None]
    fig = go.Figure()
    for c in CATS:
        vals = [r[1][CATS.index(c)] for r in rows]
        if max(vals) > 0:
            fig.add_trace(go.Bar(y=labels, x=vals, orientation="h", name=c,
                                 marker=dict(color=drums.COLORS[c], line=dict(width=1, color="white")), meta=row_ids,
                                 hovertemplate=f"%{{y}}<br>{c}: %{{x:.1%}}<extra></extra>"))
    fig.update_layout(barmode="stack", bargap=0.25, legend_traceorder="normal")
    fig.update_xaxes(tickformat=".0%", range=[0, 1], title_text="share of hits")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, 110 + 20 * len(rows))


def fig_range(data, items, models):
    fig = go.Figure()
    hum = [it for it in items if it["group"] == "human"]
    fig.add_trace(go.Scatter(x=[data[it["id"]]["f"]["scalars"]["distinct_notes"] for it in hum],
                             y=[it["short"] for it in hum], mode="markers", name="human (transcription)",
                             marker=marker_for({"group": "human"}, models), meta=[it["id"] for it in hum],
                             hovertemplate="%{y}: %{x} drums<extra></extra>"))
    gen = [it for it in items if it["group"] != "human"]
    for it in gen:
        a = data[it["id"]]["f"]["scalars"]["distinct_notes"]
        b = data[it["id"]]["native"]["scalars"]["distinct_notes"]
        fig.add_trace(go.Scatter(x=[a, b], y=[it["short"]] * 2, mode="lines", line=dict(color=LIGHT, width=3),
                                 showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[data[it["id"]]["f"]["scalars"]["distinct_notes"] for it in gen], y=[it["short"] for it in gen],
                             mode="markers", name="generated (transcription)",
                             marker=dict(symbol="circle-open", size=11, color=MACHINE_C, line=dict(width=2, color=MACHINE_C)),
                             meta=[it["id"] for it in gen], hovertemplate="%{y}: %{x} drums heard<extra></extra>"))
    fig.add_trace(go.Scatter(x=[data[it["id"]]["native"]["scalars"]["distinct_notes"] for it in gen], y=[it["short"] for it in gen],
                             mode="markers", name="generated (own MIDI)", marker=dict(size=11, color=MACHINE_C),
                             meta=[it["id"] for it in gen], hovertemplate="%{y}: %{x} drums written<extra></extra>"))
    fig.add_vline(x=47, line=dict(color=MUTED, width=1, dash="dot"), annotation_text="all 47 GM drums",
                  annotation_position="top left")
    fig.update_xaxes(range=[0, 50], title_text="distinct GM drum notes")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, 120 + 22 * len(items))


def fig_playability(data, items, models):
    fig = go.Figure()
    hum = [it for it in items if it["group"] == "human"]
    hv = [data[it["id"]]["f"]["scalars"]["limb_violations_per_min"] for it in hum]
    fig.add_trace(go.Scatter(x=hv, y=np.zeros(len(hv)) + jitter(len(hv), 7, 0.15), mode="markers",
                             name="human, from transcription (artifact floor)", marker=marker_for({"group": "human"}, models),
                             customdata=[it["label"] for it in hum], meta=[it["id"] for it in hum],
                             hovertemplate="%{customdata}: %{x:.1f} per min<extra></extra>"))
    _, groups = machine_groups(items)
    for k, (name, its) in enumerate(groups, 1):
        fig.add_trace(go.Scatter(x=[data[it["id"]]["native"]["scalars"]["limb_violations_per_min"] for it in its],
                                 y=np.full(len(its), -k) + jitter(len(its), 20 + k, 0.1), mode="markers",
                                 name=f"{name}, own MIDI", marker=marker_for(its[0], models),
                                 customdata=[it["label"] for it in its], meta=[it["id"] for it in its],
                                 hovertemplate="%{customdata}: %{x:.1f} per min<extra></extra>"))
    rows = ["recorded"] + [g[0] for g in groups]
    fig.update_yaxes(tickvals=[-k for k in range(len(rows))], ticktext=rows, showgrid=False, range=[-len(rows) + 0.5, 0.5])
    fig.update_xaxes(type="log", title_text="stroke groups needing three or more hands, per minute (log scale)",
                     tickvals=[0.3, 1, 3, 10, 30, 100], ticktext=["0.3", "1", "3", "10", "30", "100"])
    return style(fig, 130 + 60 * len(rows))


def fig_gallery(data, items, cols=6):
    n = len(items)
    rows = int(np.ceil(n / cols))
    titles = [it["short"] if it["group"] == "human" else f"<span style='color:{MACHINE_C}'>{escape(it['short'])}</span>"
              for it in items]
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=titles, horizontal_spacing=0.02, vertical_spacing=0.06)
    for k, it in enumerate(items):
        S = np.array(data[it["id"]]["f"]["images"]["ssm"]["symbolic"], dtype=float)
        T = ndimage.zoom(S, 40 / S.shape[0], order=1)
        r, c = k // cols + 1, k % cols + 1
        fig.add_trace(go.Heatmap(z=T, colorscale=SEQ, zmin=0, zmax=1, showscale=False, hoverinfo="none", meta=it["id"]),
                      row=r, col=c)
        fig.update_xaxes(visible=False, row=r, col=c)
        fig.update_yaxes(visible=False, autorange="reversed", scaleanchor=f"x{k + 1 if k else ''}", row=r, col=c)
    fig.update_annotations(font=dict(size=11))
    style(fig, 190 * rows + 60, legend=False)
    fig.update_layout(margin=dict(t=56))
    return fig


def fig_trust(data, items):
    """Transcriber scored on every generated solo: one dot per solo on each measure."""
    gen = [it for it in items if it["group"] != "human"]
    val = [data[it["id"]]["val"] for it in gen]
    names = [it["label"] for it in gen]
    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.1,
                        subplot_titles=["hits found (F1, 50 ms)", "median timing error (ms)", "audio level vs true velocity (rho)"])
    ids = [it["id"] for it in gen]
    fig.add_trace(go.Scatter(x=[v["f1"] for v in val], y=jitter(len(val), 3, 0.25), mode="markers", customdata=names, meta=ids,
                             marker=dict(size=9, color=INK2, opacity=0.8), showlegend=False,
                             hovertemplate="%{customdata}: %{x:.0%}<extra></extra>"), row=1, col=1)
    for k, (key, color, name) in enumerate((("raw", MUTED, "transcription alone"), ("refined", INK, "refined on the audio"))):
        fig.add_trace(go.Scatter(x=[v["timing_summary"][key]["median_abs_ms"] for v in val], y=np.full(len(val), -k) + jitter(len(val), 4 + k, 0.25),
                                 mode="markers", name=name, customdata=names, meta=ids, marker=dict(size=9, color=color, opacity=0.8),
                                 hovertemplate=f"%{{customdata}}, {name}: %{{x:.1f}} ms<extra></extra>"), row=1, col=2)
    fams = ("kick", "snare", "toms", "ride", "hi-hat")
    for k, c in enumerate(fams):
        vals = [(v["level_vs_velocity"]["spearman"].get(c), n, i) for v, n, i in zip(val, names, ids)]
        vals = [(x, n, i) for x, n, i in vals if x is not None]
        fig.add_trace(go.Scatter(x=[x for x, _, _ in vals], y=np.full(len(vals), -k) + jitter(len(vals), 9 + k, 0.25),
                                 mode="markers", name=c, customdata=[n for _, n, _ in vals], meta=[i for _, _, i in vals],
                                 marker=dict(size=9, color=drums.COLORS[c], opacity=0.85),
                                 hovertemplate=f"%{{customdata}}, {c}: %{{x:.2f}}<extra></extra>"), row=1, col=3)
    fig.update_xaxes(tickformat=".0%", range=[0, 1], row=1, col=1)
    fig.update_xaxes(rangemode="tozero", row=1, col=2)
    fig.update_xaxes(range=[-0.2, 1], row=1, col=3)
    fig.update_yaxes(showticklabels=False, showgrid=False, row=1, col=1)
    fig.update_yaxes(tickvals=[0, -1], ticktext=["alone", "refined"], showgrid=False, row=1, col=2)
    fig.update_yaxes(tickvals=[-k for k in range(len(fams))], ticktext=list(fams), showgrid=False, row=1, col=3)
    style(fig, 330)
    fig.update_layout(margin=dict(b=90), legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0))
    return fig


# ---------------------------------------------------------------- bracket review page

PLAYHEAD = "#D55E00"
SCORED_C = "#009E73"  # the scored chunk on the review page
BRACKET_C = "#0072B2"  # the solo band and its edges


def spans_of(mask, offset=0):
    lab, n = ndimage.label(mask)
    return [(int(np.flatnonzero(lab == k)[0]) + offset, int(np.flatnonzero(lab == k)[-1]) + 1 + offset)
            for k in range(1, n + 1)]


def detected_edges(b, part):
    """Where the detector changes its mind, for the review page to snap to: its solo bracket and scored part, and the
    edges of band-like, solo-like and silent stretches."""
    s = b["series"]
    band, solo, drum = (np.array(s[k], dtype=float) for k in ("band", "solo_like", "drum"))
    edges = {float(b["start"]), float(b["end"]), float(part[0]), float(part[1])}
    for mask, least in ((band > 0, 1), (solo > 0, 2), (drum < 0.5, 2)):
        for a, z in spans_of(mask):
            if z - a >= least:
                edges.update((float(a), float(z)))
    return sorted(round(x, 2) for x in edges if 0 <= x <= b["duration"])


def fig_bracket(e, part, cands, key):
    """Evidence for one recording, drawn for the review script. Shapes by index: 0 the detector's solo, 1 the scored
    part, 2-3 its start and end, 4 playhead, 5-6 the detector's solo edges; trace 3 marks the detected edges."""
    b = e["bracket"]
    s, dur = b["series"], b["duration"]
    t = np.arange(len(s["drum"])) + 0.5
    other = ndimage.uniform_filter1d(np.array(s["other"], dtype=float), 5)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=["drum hits per second", "notes per second from any other instrument (5 s average)",
                                        "level (dBFS)"])
    fig.add_trace(go.Bar(x=t, y=s["drum"], marker=dict(color=HUMAN_C, line=dict(width=0)), showlegend=False,
                         hovertemplate="%{y} drum hits<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=other, mode="lines", line=dict(width=2, color=MACHINE_C), showlegend=False,
                             hovertemplate="%{y:.1f} other notes/s<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=t, y=s["level_db"], mode="lines", line=dict(width=1.5, color=INK), showlegend=False,
                             hovertemplate="%{y:.0f} dBFS<extra></extra>"), row=3, col=1)
    top = max(max(s["drum"]), 1) * 1.1
    fig.add_trace(go.Scatter(x=cands, y=[top] * len(cands), mode="markers", showlegend=False, cliponaxis=False,
                             marker=dict(symbol="triangle-down", size=9, color=MUTED),
                             text=[f"{int(c // 60)}:{c % 60:04.1f}" for c in cands],
                             hovertemplate="detected edge %{text}<extra></extra>"), row=1, col=1)
    full = dict(xref="x", yref="paper", y0=0, y1=1)
    shapes = [
        dict(type="rect", x0=b["start"], x1=b["end"], fillcolor="rgba(0,114,178,0.08)", line_width=0, layer="below", **full),
        dict(type="rect", x0=part[0], x1=part[1], fillcolor="rgba(0,158,115,0.10)", line_width=0, layer="below",
             label=dict(text="scored", textposition="top center", font=dict(size=12, color=SCORED_C)), **full),
        dict(type="line", x0=part[0], x1=part[0], line=dict(color=SCORED_C, width=3), **full),
        dict(type="line", x0=part[1], x1=part[1], line=dict(color=SCORED_C, width=3), **full),
        dict(type="line", x0=0, x1=0, line=dict(color=PLAYHEAD, width=2), visible=False, **full),
        dict(type="line", x0=b["start"], x1=b["start"], line=dict(color=BRACKET_C, width=1.5, dash="dot"), **full),
        dict(type="line", x0=b["end"], x1=b["end"], line=dict(color=BRACKET_C, width=1.5, dash="dot"), **full),
        dict(type="line", xref="paper", x0=0, x1=1, yref="y2", y0=OTHER_MIN, y1=OTHER_MIN,
             line=dict(color=MUTED, width=1, dash="dot")),
    ]
    for a, z in spans_of(np.array(s["band"]) > 0):
        shapes.append(dict(type="rect", x0=a, x1=z, fillcolor="rgba(230,159,0,0.22)", line_width=0, layer="below", **full))
    ticks = np.arange(0, dur + 1, 30)
    fig.update_xaxes(tickvals=ticks, ticktext=[mmss(x) for x in ticks], range=[0, dur], fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_yaxes(range=[0, top * 1.04], row=1, col=1)
    fig.update_yaxes(range=[-70, 0], row=3, col=1)
    style(fig, 440, legend=False)
    fig.update_layout(shapes=shapes, hovermode="x", hoverlabel=dict(namelength=0), dragmode=False, margin=dict(t=40))
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id=key,
                       config={**CONFIG, "displayModeBar": False, "doubleClick": False, "scrollZoom": False})


def listen_points(b):
    """Flagged moments to jump to, at their exact times: the recording's start, the detector's solo edges, and every
    flagged stretch inside the solo."""
    s = b["series"]
    band, drum, voice = (np.array(s[k]) for k in ("band", "drum", "voice"))
    start, end = b["start"], b["end"]
    w0, w1 = int(start), int(np.ceil(end))
    pts = [(0.0, "Recording start")] if start > 3 else []
    pts += [(start, f"Detected solo start {mmss(start)}"), (end, f"Detected solo end {mmss(end)}")]
    pts += [(float(a), f"Band-like {mmss(a)}") for a, z in spans_of(band[w0:w1] > 0, w0) if z - a >= 2]
    pts += [(float(a), f"No drums {mmss(a)}") for a, z in spans_of(drum[w0:w1] < 0.5, w0) if z - a > 4]
    pts += [(float(a), f"Voice {mmss(a)}") for a, z in spans_of(voice[w0:w1] > 0, w0)]
    return sorted(pts)


REVIEW_JS = """
<script>
const KEY = "drum-scored-review", OLD = "drum-bracket-review", PREFS = "drum-bracket-review-prefs";
const SNAP_PX = 10, DRAG_PX = 4;
const fmt = t => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;
const parse = s => {  // "1:23.4" or "83.4" -> seconds, else NaN
  const m = String(s).trim().match(/^(?:(\\d+):)?(\\d+(?:\\.\\d*)?)$/);
  return m ? (m[1] ? +m[1] * 60 : 0) + +m[2] : NaN;
};
// pipeline.auto_chunk's rule: the longest stretch of [start, end] with no band-like second
function longestClean(band, start, end) {
  const spans = [];
  for (let w = Math.floor(start); w < Math.ceil(end); w++) {
    if (band[w] === "1") continue;
    const a = Math.max(start, w), b = Math.min(end, w + 1);
    if (spans.length && Math.abs(spans[spans.length - 1][1] - a) < 1e-9) spans[spans.length - 1][1] = b;
    else spans.push([a, b]);
  }
  const ok = spans.filter(([a, b]) => b > a);
  return ok.length ? ok.reduce((m, s) => (s[1] - s[0] > m[1] - m[0] ? s : m)) : null;
}
const bandSeconds = (band, start, end) => {
  let n = 0;
  for (let w = Math.floor(start); w < Math.ceil(end); w++) n += band[w] === "1";
  return n;
};

const tracks = [...document.querySelectorAll("section.track")];
const msg = document.getElementById("rv-msg");
// decisions are the scored part itself: {id: {start, end, status}}; the saved file first, this browser on top
const review = {...SAVED, ...JSON.parse(localStorage.getItem(KEY) || "{}")};
// decisions from the earlier page set the solo bracket; keep what they would have scored
const old = JSON.parse(localStorage.getItem(OLD) || "{}");
for (const [id, r] of Object.entries(old)) {
  const sec = document.getElementById(id), c = sec && longestClean(sec.dataset.band, r.start, r.end);
  if (c && !review[id]) review[id] = {start: +c[0].toFixed(2), end: +c[1].toFixed(2), status: r.status};
}
localStorage.removeItem(OLD);
const prefs = {autoplay: false, lead: 3, snap: true, ...JSON.parse(localStorage.getItem(PREFS) || "{}")};
let active = null;  // the track the keys act on: the last one touched
const activate = sec => { if (active !== sec) { active && active.classList.remove("active"); active = sec; sec.classList.add("active"); } };

function refresh() {
  localStorage.setItem(KEY, JSON.stringify(review));
  const ids = Object.keys(review).sort();
  document.getElementById("rv-json").value = JSON.stringify(Object.fromEntries(ids.map(i => [i, review[i]])), null, 1);
  const fixed = ids.filter(i => review[i].status === "corrected").length;
  document.getElementById("rv-count").textContent =
    `${ids.length} of ${tracks.length} reviewed (${fixed} corrected, ${ids.length - fixed} confirmed)`;
  document.querySelectorAll("li[data-id] .mine").forEach(s => {
    const r = review[s.closest("li").dataset.id];
    s.textContent = r ? r.status : "";
    s.className = r ? "mine ok" : "mine";
  });
}

const ap = document.getElementById("rv-autoplay"), lead = document.getElementById("rv-lead");
const snapBox = document.getElementById("rv-snap");
ap.checked = prefs.autoplay; lead.value = String(prefs.lead); snapBox.checked = prefs.snap;
[ap, lead, snapBox].forEach(el => el.addEventListener("change", () => {
  Object.assign(prefs, {autoplay: ap.checked, lead: +lead.value, snap: snapBox.checked});
  localStorage.setItem(PREFS, JSON.stringify(prefs));
  tracks.forEach(t => t.showTicks());
}));

for (const sec of tracks) {
  const id = sec.dataset.id, audio = sec.querySelector("audio.main"), gd = document.getElementById("br_" + id);
  const auto = {start: +sec.dataset.autoStart, end: +sec.dataset.autoEnd}, dur = +sec.dataset.dur;
  const band = sec.dataset.band, cands = JSON.parse(sec.dataset.cands);
  const state = sec.querySelector(".state"), now = sec.querySelector(".now");
  const inStart = sec.querySelector("input.t-start"), inEnd = sec.querySelector("input.t-end");
  const current = () => review[id] || {...auto, status: "not reviewed yet"};
  const clamp = x => Math.min(dur, Math.max(0, x));
  const xa = () => gd._fullLayout.xaxis;
  const px = x => xa()._offset + (x - xa().range[0]) / (xa().range[1] - xa().range[0]) * xa()._length;
  const local = e => e.clientX - gd.getBoundingClientRect().left;
  const xAt = e => xa().range[0] + (local(e) - xa()._offset) / xa()._length * (xa().range[1] - xa().range[0]);
  const inPlot = e => {
    const z = gd._fullLayout._size, r = gd.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    return x >= z.l && x <= z.l + z.w && y >= z.t && y <= z.t + z.h;
  };
  const snap = (x, free) => {  // nearest detected edge within SNAP_PX on screen, else a tenth of a second
    x = clamp(x);
    if (prefs.snap && !free) {
      let best = null;
      for (const c of cands) if (Math.abs(px(c) - px(x)) <= SNAP_PX && (best === null || Math.abs(c - x) < Math.abs(best - x))) best = c;
      if (best !== null) return best;
    }
    return Math.round(x * 10) / 10;
  };
  const nearest = x => { const r = current(); return Math.abs(x - r.start) <= Math.abs(x - r.end) ? "start" : "end"; };
  let lit = null;  // the edge a drag would move, drawn thicker
  const light = edge => {
    if (edge === lit) return;
    lit = edge;
    Plotly.relayout(gd, {"shapes[2].line.width": edge === "start" ? 6 : 3, "shapes[3].line.width": edge === "end" ? 6 : 3});
  };
  const draw = r => Plotly.relayout(gd, {"shapes[1].x0": r.start, "shapes[1].x1": r.end, "shapes[2].x0": r.start,
    "shapes[2].x1": r.start, "shapes[3].x0": r.end, "shapes[3].x1": r.end});
  const describe = r => {
    const n = bandSeconds(band, r.start, r.end);
    return `scored ${fmt(r.start)} to ${fmt(r.end)}` + (n ? `, including ${n} s the detector heard as band-like` : "");
  };
  const show = () => {
    const r = current();
    draw(r);
    inStart.value = fmt(r.start); inEnd.value = fmt(r.end);
    const moved = Math.abs(r.start - auto.start) > 0.05 || Math.abs(r.end - auto.end) > 0.05;
    state.textContent = `${describe(r)}; ${r.status}` + (moved ? ` (the detector picked ${fmt(auto.start)} to ${fmt(auto.end)})` : "");
    sec.querySelectorAll("button.edge").forEach(b => {
      const t = b.dataset.edge === "start" ? r.start : r.end;
      b.dataset.t = t;
      b.textContent = `${b.dataset.label} ${fmt(t)}`;
    });
  };
  sec.showTicks = () => Plotly.restyle(gd, {visible: prefs.snap}, [3]);
  const decide = (start, end) => {
    [start, end] = [clamp(Math.min(start, end)), clamp(Math.max(start, end))];
    if (end - start < 1) { show(); state.textContent = "the scored part has to be at least a second long"; return; }
    const same = Math.abs(start - auto.start) <= 0.05 && Math.abs(end - auto.end) <= 0.05;
    review[id] = {start: +start.toFixed(2), end: +end.toFixed(2), status: same ? "confirmed" : "corrected"};
    refresh(); show();
  };

  // the playhead: every jump lands exactly on its time; autoplay starts the lead-in before it
  const mark = () => {
    now.textContent = `playhead ${fmt(audio.currentTime)}`;
    Plotly.relayout(gd, {"shapes[4].x0": audio.currentTime, "shapes[4].x1": audio.currentTime, "shapes[4].visible": true});
  };
  let until = null;  // a preview's end: playback pauses exactly there
  const stopAt = () => {
    if (until === null) return;
    if (audio.paused || audio.currentTime >= until) {
      if (!audio.paused) { audio.pause(); audio.currentTime = until; }
      until = null;
      mark();
      return;
    }
    requestAnimationFrame(stopAt);
  };
  const preview = (a, b) => {
    activate(sec);
    until = clamp(b);
    audio.currentTime = clamp(a);
    audio.play().then(() => requestAnimationFrame(stopAt), e => { state.textContent = `could not play: ${e.message}`; until = null; });
  };
  const jump = t => {
    activate(sec);
    until = null;
    t = clamp(t);
    if (prefs.autoplay) { audio.currentTime = Math.max(0, t - prefs.lead); audio.play(); }
    else { audio.pause(); audio.currentTime = t; }
    mark();
  };
  audio.addEventListener("timeupdate", mark);
  audio.addEventListener("seeked", mark);
  audio.addEventListener("play", () => activate(sec));

  const button = (sel, fn) => sec.querySelectorAll(sel).forEach(b => b.addEventListener("click", () => { activate(sec); fn(b); b.blur(); }));
  button("button.seek, button.edge", b => jump(+b.dataset.t));
  button(".set-start", () => decide(audio.currentTime, current().end));
  button(".set-end", () => decide(current().start, audio.currentTime));
  button(".accept", () => { review[id] = {...auto, status: "confirmed"}; refresh(); show(); });
  button(".pv-all", () => { const r = current(); preview(r.start, r.end); });
  button(".pv-first", () => { const r = current(); preview(r.start, Math.min(r.end, r.start + 8)); });
  button(".pv-last", () => { const r = current(); preview(Math.max(r.start, r.end - 8), r.end); });
  button(".clear", () => { delete review[id]; refresh(); show(); });
  const view = (a, b) => Plotly.relayout(gd, {"xaxis.range": [Math.max(0, a), Math.min(dur, b)]});
  button(".z-start", () => view(current().start - 20, current().start + 20));
  button(".z-end", () => view(current().end - 20, current().end + 20));
  button(".z-all", () => view(0, dur));
  for (const [input, key] of [[inStart, "start"], [inEnd, "end"]]) {
    input.addEventListener("focus", () => activate(sec));
    input.addEventListener("change", () => {
      const raw = input.value, t = parse(raw), r = current();
      if (Number.isNaN(t)) { show(); state.textContent = `can't read "${raw}": use m:ss.s or seconds`; return; }
      decide(key === "start" ? t : r.start, key === "end" ? t : r.end);
    });
  }

  // the chart: a click moves the playhead; a drag moves the nearer green edge; shift-drag draws a new scored part
  let drag = null;
  gd.addEventListener("mousedown", e => {
    if (e.button !== 0 || !inPlot(e)) return;
    e.preventDefault(); e.stopPropagation();
    activate(sec);
    const x = xAt(e);
    drag = {x0: x, cx: e.clientX, mode: e.shiftKey ? "new" : nearest(x), next: null};
  }, true);
  gd.addEventListener("mousemove", e => {
    if (drag) return;
    const inside = inPlot(e);
    gd.querySelectorAll(".nsewdrag").forEach(d => { d.style.cursor = inside ? (e.shiftKey ? "crosshair" : "ew-resize") : ""; });
    light(inside && !e.shiftKey ? nearest(xAt(e)) : null);
  });
  gd.addEventListener("mouseleave", () => { if (!drag) light(null); });
  window.addEventListener("mousemove", e => {
    if (!drag || (!drag.next && Math.abs(e.clientX - drag.cx) < DRAG_PX)) return;
    const x = snap(xAt(e), e.altKey), r = current();
    const n = drag.mode === "new" ? {start: snap(drag.x0, e.altKey), end: x} : {...r, [drag.mode]: x};
    drag.next = {start: Math.min(n.start, n.end), end: Math.max(n.start, n.end)};
    draw(drag.next);
    state.textContent = describe(drag.next) + (prefs.snap && !e.altKey ? " (snapping to the gray ticks; hold Alt/Option to place freely)" : "");
  });
  window.addEventListener("mouseup", e => {
    if (!drag) return;
    const d = drag;
    drag = null;
    if (d.next) decide(d.next.start, d.next.end);
    else jump(xAt(e));
  });
  show();
  sec.showTicks();
}

document.addEventListener("keydown", e => {
  const tag = document.activeElement ? document.activeElement.tagName : "";
  if (!active || e.metaKey || e.ctrlKey || e.altKey || ["INPUT", "TEXTAREA", "SELECT", "AUDIO"].includes(tag)) return;
  const key = e.key.toLowerCase(), audio = active.querySelector("audio.main");
  if (key === "s") active.querySelector(".set-start").click();
  else if (key === "e") active.querySelector(".set-end").click();
  else if (key === "p") active.querySelector(".pv-all").click();
  else if (key === " ") audio.paused ? audio.play() : audio.pause();
  else return;
  e.preventDefault();
});
const players = [...document.querySelectorAll("audio")];
players.forEach(p => p.addEventListener("play", () => players.forEach(o => { if (o !== p) o.pause(); })));
document.getElementById("rv-download").onclick = () => {
  const blob = new Blob([document.getElementById("rv-json").value], {type: "application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "bracket_overrides.json";
  a.click();
  msg.textContent = "downloaded bracket_overrides.json";
};
document.getElementById("rv-copy").onclick = () => navigator.clipboard.writeText(document.getElementById("rv-json").value)
  .then(() => { msg.textContent = "copied"; }, e => { msg.textContent = `copy failed: ${e.message}`; });
refresh();
</script>"""

REVIEW_CSS = f"""
section.track{{padding-left:10px;border-left:3px solid transparent}}
section.track.active{{border-left-color:{SCORED_C}}}
input.t{{width:64px;font:inherit;font-size:13px;padding:2px 6px;border:1px solid {LIGHT};border-radius:6px}}
.bar label{{display:flex;align-items:center;gap:5px;font-size:13px;color:{INK2}}}
.bar select{{font:inherit;font-size:13px}}
.bar .sep{{width:1px;align-self:stretch;background:{LIGHT}}}
kbd{{font:12px ui-monospace,Menlo,monospace;border:1px solid {LIGHT};border-radius:4px;padding:0 4px;background:#f6f8fa}}
.mine{{font-size:12px;margin-left:6px}}
.key-b{{color:{BRACKET_C};font-weight:600}} .key-o{{color:#b36b00;font-weight:600}} .key-g{{color:{SCORED_C};font-weight:600}}
"""


def brackets_page(data, items):
    ov = pipeline.overrides()
    hum = sorted([it for it in items if it["group"] == "human"],
                 key=lambda it: (it["id"] in ov, not data[it["id"]]["bracket"]["check"], it["short"]))
    parts = []
    for it in hum:
        b = data[it["id"]]["bracket"]
        auto = pipeline.auto_chunk(it)
        if it["id"] in ov:
            flag = f"<span class='ok'>{escape(ov[it['id']]['status'])} in the saved file</span>"
        else:
            flag = "<span class='chk'>check</span>" if b["check"] else "<span class='ok'>looks clean</span>"
        reasons = "".join(f"<li>{escape(r)}</li>" for r in b["reasons"])
        flagged = "".join(f"<button class='seek' data-t='{t:.2f}'>{escape(label)}</button>" for t, label in listen_points(b))
        rel = escape(os.path.relpath(Path(it["audio"]).resolve(), REVIEW.resolve()))
        band = "".join("1" if x else "0" for x in b["series"]["band"])
        cands = detected_edges(b, auto)
        edge = lambda key, label: f"<button class='edge' data-edge='{key}' data-label='{label}'>{label}</button>"
        parts.append(f"""<section class="track" id="{it['id']}" data-id="{it['id']}" data-auto-start="{auto[0]:.2f}"
 data-auto-end="{auto[1]:.2f}" data-dur="{b['duration']:.2f}" data-band="{band}" data-cands='{json.dumps(cands)}'>
<h2>{escape(it['label'])} {flag}</h2>
<p class="note">The detector heard the solo from {mmss(b['start'])} to {mmss(b['end'])} of {mmss(b['duration'])} (trimmed
before: {escape(b['lead']['text'])}; after: {escape(b['tail']['text'])}) and picked {mmss(auto[0])} to {mmss(auto[1])} to
score, its longest stretch with no band-like second. <a href="{escape(it['url'])}">source</a></p>
{f'<ul class="note">{reasons}</ul>' if reasons else ''}
<div class="player"><audio class="main" controls preload="metadata" src="{rel}"></audio>
<div class="row"><span class="lbl">Jump</span>{edge('start', 'Scored start')}{edge('end', 'Scored end')}{flagged}</div>
<div class="row"><span class="lbl">Scored</span>start <input class="t t-start"> end <input class="t t-end">
<button class="set-start">Start at playhead <kbd>S</kbd></button><button class="set-end">End at playhead <kbd>E</kbd></button>
<button class="accept">Detector is right</button><button class="clear">Clear my times</button></div>
<div class="row"><span class="lbl">Preview</span><button class="pv-all">Play the scored part <kbd>P</kbd></button>
<button class="pv-first">Its first 8 s</button><button class="pv-last">Its last 8 s</button></div>
<div class="row"><span class="lbl">View</span><button class="z-start">Zoom to start</button><button class="z-end">Zoom to end</button>
<button class="z-all">Whole track</button><span class="now"></span><span class="state"></span></div></div>
{fig_bracket(data[it['id']], pipeline.best_chunk(it), cands, 'br_' + it['id'])}
<p class="note"><b>Transcription check</b>: left channel the recording, right channel the transcription played on the
FluidR3 kit (every note at velocity 100). Pan or use headphones to compare.</p>
<audio class="check" controls preload="none" src="{escape(os.path.relpath((pipeline.TRANS / (it['id'] + '.auralize.mp3')).resolve(), REVIEW.resolve()))}"></audio>
</section>""")
    n_check = sum(data[it["id"]]["bracket"]["check"] and it["id"] not in ov for it in hum)

    def status(it):
        if it["id"] in ov:
            return f"<span class='ok'>{escape(ov[it['id']]['status'])} in the saved file</span>"
        return "<span class='chk'>check</span>" if data[it["id"]]["bracket"]["check"] else "<span class='ok'>looks clean</span>"
    toc = "<ul class='toc'>" + "".join(f"<li data-id='{it['id']}'><a href='#{it['id']}'>{escape(it['label'])}</a> {status(it)}"
                                         f"<span class='mine'></span></li>" for it in hum) + "</ul>"
    body = f"""<h1>Which part of each recording gets scored?</h1>
<p class="sub">The detector picked a part of each recording to score. {n_check} of {len(hum)} tracks are flagged for a
listen and come first.</p>
<div class="howto"><b>How to set the scored part</b>
<ol><li><b>Read the chart.</b> <span class="key-g">Green</span>: the part that gets scored, exactly as shown.
<span class="key-b">Blue</span> (dotted edges): where the detector heard the solo. <span class="key-o">Orange</span>:
seconds that sound like a band. Gray ticks along the top: edges the detector found.</li>
<li><b>Listen.</b> Click the chart or a <b>Jump</b> button: the playhead (red line) lands exactly there. With
<b>Autoplay</b> off (bottom bar) nothing plays until you press <kbd>Space</kbd> or the play button; with it on, playback
starts the lead-in before that point.</li>
<li><b>Preview.</b> <b>Play the scored part</b> (<kbd>P</kbd>) plays exactly the green part and stops at its
end; <b>Its first 8 s</b> and <b>Its last 8 s</b> play just its edges. <kbd>Space</kbd> stops.</li>
<li><b>Move the green edges.</b> Drag anywhere on the chart and the nearer green edge follows (it thickens as you hover,
so you can see which one). <kbd>Shift</kbd>-drag draws a new part. <kbd>S</kbd> / <kbd>E</kbd> put the start or end at
the playhead, or type the times. Edges snap to the gray ticks while <b>Snap</b> is on; hold <kbd>Alt</kbd>/<kbd>Option</kbd>
to place freely. <b>Detector is right</b> keeps its pick; <b>Clear my times</b> goes back to it. The keys act on the
track with the green bar at its left: the last one you touched.</li>
<li><b>Save.</b> Press <b>Download</b> in the bottom bar and move <code>bracket_overrides.json</code> into
<code>human_solos/</code>, or paste the JSON into chat. Decisions are kept in this browser as you go.</li></ol>
<details><summary>Your decisions as JSON</summary><textarea id="rv-json" readonly></textarea></details></div>
<p class="note">Why the middle row is never zero: MuScriptor hears phantom bass and guitar notes in pure drum recordings
(kick and tom resonance, cymbal ring). Only a sustained rate above the dotted line, well above the drums' own phantom rate,
counts as a band.</p>
{toc}
{''.join(parts)}
<div class="bar"><label><input type="checkbox" id="rv-autoplay"> Autoplay, from
<select id="rv-lead"><option value="0">0</option><option value="1">1</option><option value="2">2</option>
<option value="3">3</option><option value="5">5</option></select> s before</label>
<label><input type="checkbox" id="rv-snap"> Snap to detected edges</label><span class="sep"></span>
<span id="rv-count"></span><button id="rv-download">Download</button><button id="rv-copy">Copy JSON</button>
<span id="rv-msg"></span></div>
<script>const SAVED = {json.dumps(ov)};</script>
{REVIEW_JS}"""
    return page("Scored parts", body, js=os.path.relpath(OUT / "plotly.min.js", REVIEW), css=REVIEW_CSS, fork=False)


# ---------------------------------------------------------------- detection page (public)

def fig_detection(e, spans, chunk, key, src=None):
    """What the algorithm hears in one recording: solo stretches, other instruments, and the scored chunk."""
    s = e["bracket"]["series"]
    dur = e["bracket"]["duration"]
    t = np.arange(len(s["drum"])) + 0.5
    other = ndimage.uniform_filter1d(np.array(s["other"], dtype=float), 5)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=["drum hits per second", "notes per second from any other instrument (5 s average)",
                                        "level (dBFS)"])
    meta = {"src": src, "offset": 0} if src else None
    fig.add_trace(go.Bar(x=t, y=s["drum"], marker=dict(color=HUMAN_C, line=dict(width=0)), showlegend=False, meta=meta,
                         hovertemplate="%{y} drum hits<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=other, mode="lines", line=dict(width=2, color=MACHINE_C), showlegend=False, meta=meta,
                             hovertemplate="%{y:.1f} other notes/s<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=t, y=s["level_db"], mode="lines", line=dict(width=1.5, color=INK), showlegend=False, meta=meta,
                             hovertemplate="%{y:.0f} dBFS<extra></extra>"), row=3, col=1)
    full = dict(xref="x", yref="paper", y0=0, y1=1)
    shapes = [dict(type="line", x0=0, x1=0, line=dict(color=PLAYHEAD, width=2), visible=False, **full)]  # moved by script
    shapes += [dict(type="rect", x0=a, x1=b, fillcolor="rgba(0,114,178,0.11)", line_width=0, layer="below", **full)
               for a, b in spans]
    shapes += [dict(type="rect", x0=a, x1=z, fillcolor="rgba(230,159,0,0.24)", line_width=0, layer="below", **full)
               for a, z in spans_of(np.array(s["band"]) > 0)]
    if chunk:
        shapes += [dict(type="line", x0=x, x1=x, line=dict(color=INK, width=2), **full) for x in chunk]
    shapes.append(dict(type="line", xref="paper", x0=0, x1=1, yref="y2", y0=OTHER_MIN, y1=OTHER_MIN,
                       line=dict(color=MUTED, width=1, dash="dot")))
    ticks = np.arange(0, dur + 1, 30)
    fig.update_xaxes(tickvals=ticks, ticktext=[mmss(x) for x in ticks], range=[0, dur])
    fig.update_yaxes(range=[-70, 0], row=3, col=1)
    style(fig, 400, legend=False)
    fig.update_layout(shapes=shapes, hovermode="x")
    return html_of(fig, key)


def detection_page(data, items, scores):
    by_id = {s["id"]: s for s in scores["solos"]}
    hum = sorted([it for it in items if it["group"] == "human"], key=lambda it: it["short"])
    gen = sorted([it for it in items if it["group"] != "human"], key=lambda it: -by_id[it["id"]]["overall"])

    def block(it):
        e = data[it["id"]]
        dur = e["bracket"]["duration"]
        spans = pipeline.spans_for(it)
        band = [(a, z) for a, z in spans_of(np.array(e["bracket"]["series"]["band"]) > 0) if z - a >= 2]
        if it["group"] == "human":
            a, b = pipeline.best_chunk(it)
            line = (f"Scored: {mmss(a)} to {mmss(b)} ({mmss(b - a)}) of {mmss(dur)}"
                    + (", set by listening." if it["id"] in pipeline.overrides() else "."))
            chunk = (a, b)
            buttons = [(a, b, f"Scored part, {mmss(a)} to {mmss(b)}")]
        else:
            heard = int(np.sum(e["bracket"]["series"]["band"]))
            line = (f"Scored whole ({mmss(dur)}). "
                    + (f"{heard} s heard as other instruments." if heard else "No seconds heard as other instruments."))
            chunk = None
            buttons = [(0.0, dur, "Whole solo")]
        buttons += [(a, z, f"Other instruments, {mmss(a)}") for a, z in band]
        src = audio_src(it)
        if src:
            row = "".join(f"<button class='seek' data-t='{a:.2f}' data-end='{z:.2f}'>{escape(label)}</button>"
                          for a, z, label in buttons)
            player = f"<audio controls preload='none' src='{escape(src)}'></audio>"
        else:
            row = "".join(f"<a class='btn' href='{escape(it['url'])}&t={int(a)}s' target='_blank'>{escape(label)}</a>"
                          for a, z, label in buttons)
            player = ""
        return (f"<section class='det' id='{it['id']}' data-id='{it['id']}'><h3 data-solo='{it['id']}'>{escape(it['label'])}</h3>"
                f"<p class='note'>{line}</p>{player}"
                f"<div class='row'><span class='lbl'>{'Play' if src else 'On YouTube'}</span>{row}</div>"
                f"{fig_detection(e, spans, chunk, 'det_' + it['id'], src)}</section>")

    toc = lambda its: "<ul class='toc'>" + "".join(f"<li><a href='#{it['id']}'>{escape(it['label'])}</a></li>" for it in its) + "</ul>"
    body = f"""<h1>The scored part of each recording</h1>
<p class="sub">Most of the recordings have more than the solo on them: an intro, applause, a band. Only the solo
gets scored.</p>
<p class="note">Each recording is transcribed twice, once listening only for drums and once allowing every instrument. A
second counts as solo when there is steady drumming and no sustained activity from other instruments; sustained means above
the dotted line in the middle chart, because even a pure drum recording produces a few stray notes that the transcriber
takes for bass or guitar. <b style="color:#0072B2">Blue</b> marks solo stretches and <b style="color:#b07800">orange</b>
marks seconds where other instruments play. The scored part of each recording is between the black lines: the
longest uninterrupted solo stretch, or a stretch set by listening where noted. It is always one continuous stretch, so
tempo and timing are measured on continuous playing.</p>
<p class="note">The generated solos went through the same algorithm. They are scored whole, since no one else plays on them;
any orange shows where the algorithm hears one of their own sounds as another instrument.</p>
<p class="note">{"Buttons under a recording open it on YouTube at that moment. For generated solos, press" if pipeline.PUBLIC else "Press"}
a button to hear that section, or click anywhere on a chart to play from there; the red line follows playback.</p>
<h2>Recorded solos</h2>{toc(hum)}{''.join(block(it) for it in hum)}
<h2>Generated solos</h2><p class="note">Best overall score first.</p>{toc(gen)}{''.join(block(it) for it in gen)}
{DETECTION_JS}"""
    return page("The scored part of each recording", body, tail=sound.tags(), here="detection.html")


DETECTION_JS = """<script>
const players = [...document.querySelectorAll("audio")];
players.forEach(p => p.addEventListener("play", () => players.forEach(o => { if (o !== p) o.pause(); })));
for (const sec of document.querySelectorAll("section.det")) {
  const audio = sec.querySelector("audio"), gd = document.getElementById("det_" + sec.dataset.id);
  if (!audio) continue;  // recording not hosted: its buttons are YouTube links
  let stopAt = null;
  const play = (t, end) => { stopAt = end; audio.currentTime = t; audio.play(); };
  sec.querySelectorAll("button.seek").forEach(b => b.onclick = () => play(+b.dataset.t, +b.dataset.end));
  gd.on("plotly_click", ev => play(ev.points[0].x, null));
  audio.addEventListener("timeupdate", () => {
    if (stopAt !== null && audio.currentTime >= stopAt) { audio.pause(); stopAt = null; }
    Plotly.relayout(gd, {"shapes[0].x0": audio.currentTime, "shapes[0].x1": audio.currentTime, "shapes[0].visible": true});
  });
}
</script>"""


# ---------------------------------------------------------------- graph page

GRAPH_CSS = f"""
#wrap{{position:relative;border:1px solid {GRID};border-radius:8px;margin-top:8px}}
#graph{{width:100%;height:780px;display:block;touch-action:none}}
.controls{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:12px 0}}
.controls button.on{{background:{INK};color:#fff;border-color:{INK}}}
.node{{cursor:pointer}}
.node circle{{stroke:#fff;stroke-width:1.5}}
.node.human circle{{fill:{HUMAN_C}}}
.node.generated circle{{fill:{MACHINE_C}}}
.node text{{font-size:11px;fill:{INK2};text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:#fff;stroke-width:3px}}
.node.generated text{{fill:#a3195b;font-size:10.5px}}
#sizes{{width:320px;height:44px;margin-left:8px}}
#sizes .keydot{{fill:none;stroke:{INK2};stroke-width:1.2}}
#sizes .keytext{{font-size:12px;fill:{INK2}}}
.node.dim{{opacity:.15}}
.edge{{stroke:{LIGHT};stroke-width:1}}
.edge.generated{{stroke:rgba(220,38,127,.35)}}
.edge.mixed{{stroke:{MUTED};stroke-dasharray:3 3}}
.edge.hot{{stroke:{INK};stroke-width:2;stroke-dasharray:none}}
.tip{{position:absolute;display:none;pointer-events:none;background:#fff;border:1px solid {LIGHT};border-radius:6px;
padding:6px 10px;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,.08);max-width:280px}}
.tip .muted{{color:{MUTED}}}
"""

GRAPH_JS = """<script>
(() => {
  const svg = document.getElementById("graph"), tip = document.getElementById("tip");
  const NS = "http://www.w3.org/2000/svg";
  const make = (tag, attrs = {}) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  let W = svg.clientWidth, H = svg.clientHeight;
  const spiral = i => 24 * Math.sqrt(i + 1);  // start on a spiral so no two nodes overlap
  const nodes = DATA.nodes.map((d, i) => ({...d, i, x: W / 2 + spiral(i) * Math.cos(i * 2.4), y: H / 2 + spiral(i) * Math.sin(i * 2.4), vx: 0, vy: 0}));
  const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
  const edges = DATA.edges.map(([a, b, d]) => ({a: byId[a], b: byId[b], d}));
  const sorted = edges.map(e => e.d).sort((x, y) => x - y), med = sorted[Math.floor(sorted.length / 2)];
  const near = Object.fromEntries(nodes.map(n => [n.id, new Set()]));
  edges.forEach(e => { near[e.a.id].add(e.b.id); near[e.b.id].add(e.a.id); });
  const scores = nodes.map(n => n.score), sMin = Math.min(...scores), sMax = Math.max(...scores);
  const size = sc => Math.sqrt(16 + 308 * (sc - sMin) / (sMax - sMin));  // area grows with score: 4 px to 18 px radius
  const radius = n => n.r;
  nodes.forEach(n => { n.r = size(n.score); });
  const gE = make("g"), gN = make("g");
  svg.append(gE, gN);
  edges.forEach(e => { e.el = make("line", {class: "edge " + (e.a.group === e.b.group ? e.a.group : "mixed")}); gE.append(e.el); });
  nodes.forEach(n => {
    n.el = make("g", {class: "node " + n.group});
    n.el.append(make("circle", {r: radius(n)}));
    const t = make("text", {y: -radius(n) - 5});
    t.textContent = n.short;
    n.el.append(t);
    gN.append(n.el);
  });

  let mode = "springs", target = null, dragged = null, downAt = null;
  const place = key => {
    const xs = nodes.map(n => n[key][0]), ys = nodes.map(n => n[key][1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys), m = 95;
    return nodes.map(n => [m + (n[key][0] - x0) / (x1 - x0) * (W - 2 * m), H - m - (n[key][1] - y0) / (y1 - y0) * (H - 2 * m)]);
  };
  const setMode = m => {
    mode = m;
    target = m === "springs" ? null : place(m);
    document.querySelectorAll("button[data-mode]").forEach(b => b.classList.toggle("on", b.dataset.mode === m));
    nodes.forEach(n => { n.vx += (Math.random() - 0.5) * 10; n.vy += (Math.random() - 0.5) * 10; });
  };
  const step = () => {
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j], dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy + 100, d = Math.sqrt(d2);
      const f = (mode === "springs" ? 3800 : 220) / d2;
      a.vx -= f * dx / d; a.vy -= f * dy / d; b.vx += f * dx / d; b.vy += f * dy / d;
      const gap = a.r + b.r + 14 - Math.hypot(dx, dy);  // keep dots (and their labels) apart
      if (gap > 0) { const k = 0.25 * gap / d; a.vx -= k * dx; a.vy -= k * dy; b.vx += k * dx; b.vy += k * dy; }
    }
    if (mode === "springs") {
      edges.forEach(e => {
        const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y, d = Math.hypot(dx, dy) || 1, f = 0.02 * (d - 95 * e.d / med);
        e.a.vx += f * dx / d; e.a.vy += f * dy / d; e.b.vx -= f * dx / d; e.b.vy -= f * dy / d;
      });
      nodes.forEach(n => { n.vx += (W / 2 - n.x) * 0.003; n.vy += (H / 2 - n.y) * 0.003; });
    } else {
      nodes.forEach(n => { n.vx += (target[n.i][0] - n.x) * 0.02; n.vy += (target[n.i][1] - n.y) * 0.02; });
    }
    nodes.forEach(n => {
      if (n === dragged) { n.vx = n.vy = 0; return; }
      n.vx *= 0.88; n.vy *= 0.88;
      const sp = Math.hypot(n.vx, n.vy);
      if (sp > 14) { n.vx *= 14 / sp; n.vy *= 14 / sp; }
      n.x += n.vx; n.y += n.vy;
      if (n.x < 80 || n.x > W - 80) { n.x = Math.max(80, Math.min(W - 80, n.x)); n.vx = 0; }  // room for labels
      if (n.y < 22 || n.y > H - 15) { n.y = Math.max(22, Math.min(H - 15, n.y)); n.vy = 0; }
    });
  };
  const draw = () => {
    edges.forEach(e => { e.el.setAttribute("x1", e.a.x); e.el.setAttribute("y1", e.a.y); e.el.setAttribute("x2", e.b.x); e.el.setAttribute("y2", e.b.y); });
    nodes.forEach(n => n.el.setAttribute("transform", `translate(${n.x},${n.y})`));
  };
  const key = document.getElementById("sizes");
  [sMin, Math.round((sMin + sMax) / 2), sMax].forEach((sc, k) => {
    const x = [20, 115, 225][k], r = size(sc);
    key.append(make("circle", {cx: x, cy: 22, r, class: "keydot"}));
    const t = make("text", {x: x + r + 5, y: 26, class: "keytext"});
    t.textContent = `score ${sc}`;
    key.append(t);
  });
  // nodes move under a resting pointer, and the browser only reports enter and leave when the pointer moves, so the
  // node under the pointer is checked every frame
  let pointer = null, hovered = null;
  const underPointer = () => {
    if (!pointer) return null;
    const g = document.elementFromPoint(pointer[0], pointer[1])?.closest("g.node");
    return g ? nodes.find(n => n.el === g) : null;
  };
  const track = () => {
    if (dragged) return;
    const n = underPointer();
    if (n === hovered) return;
    hovered = n;
    if (n) focus(n); else blur();
  };
  const loop = () => { step(); draw(); track(); requestAnimationFrame(loop); };
  loop();

  const at = ev => { const r = svg.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };
  const focus = n => {
    tip.innerHTML = `<b>${n.label}</b><br>${n.group === "human" ? "recorded solo" : "generated solo"}, score ${n.score}` +
      `<br><span class="muted">click to open its page</span>`;
    tip.style.display = "block";
    nodes.forEach(m => m.el.classList.toggle("dim", m !== n && !near[n.id].has(m.id)));
    edges.forEach(e => e.el.classList.toggle("hot", e.a === n || e.b === n));
    if (window.drumSound) drumSound.clip(n.id);
  };
  const blur = () => {
    tip.style.display = "none";
    nodes.forEach(m => m.el.classList.remove("dim"));
    edges.forEach(e => e.el.classList.remove("hot"));
    if (window.drumSound) drumSound.stop();
  };
  nodes.forEach(n => {
    n.el.addEventListener("pointerdown", ev => { dragged = n; downAt = at(ev); svg.setPointerCapture(ev.pointerId); });
  });
  svg.addEventListener("pointerleave", () => { pointer = null; if (!dragged) { hovered = null; blur(); } });
  svg.addEventListener("pointermove", ev => {
    pointer = [ev.clientX, ev.clientY];
    track();
    const [x, y] = at(ev);
    tip.style.left = `${x + 18}px`; tip.style.top = `${y + 12}px`;
    if (dragged) { dragged.x = x; dragged.y = y; }
  });
  svg.addEventListener("pointerup", ev => {
    if (dragged && Math.hypot(at(ev)[0] - downAt[0], at(ev)[1] - downAt[1]) < 5) window.location.href = dragged.page;
    dragged = null; hovered = null; blur();
  });
  document.querySelectorAll("button[data-mode]").forEach(b => b.onclick = () => setMode(b.dataset.mode));
  window.addEventListener("resize", () => { W = svg.clientWidth; H = svg.clientHeight; if (target) target = place(mode); });
})();
</script>"""


PUBLIC_NOTE = "; the recordings are linked from their own pages"


def graph_page(scores, data, items):
    by_id = {it["id"]: it for it in items}
    nodes = [{"id": sc_["id"], "label": escape(sc_["label"]), "short": sc_["short"],
              "group": "human" if sc_["group"] == "human" else "generated", "score": round(sc_["overall"]),
              "pca": sc_["pca"], "umap": sc_["umap"],
              "audio": audio_src(by_id[sc_["id"]]),
              "page": f"{sc_['id']}/index.html"} for sc_ in scores["solos"]]
    n_h = sum(n["group"] == "human" for n in nodes)
    body = f"""<h1>Similarity graph</h1>
<p class="sub">Each dot is a solo, <b style="color:{HUMAN_C}">gray</b> for the {n_h} recorded solos and <b
style="color:{MACHINE_C}">magenta</b> for the {len(nodes) - n_h} generated ones, sized by overall score (key next to the
buttons). Lines connect each solo to the three it's most similar to, across all the scoring measurements.</p>
<p class="note"><b>Springs</b>: a force-directed layout of the similarity network; dots can be dragged. <b>PCA</b>: the two
directions along which the recorded solos differ most. <b>UMAP</b>: a map that keeps each solo close to its nearest
neighbors. With hover sound on (top right), hovering a dot plays a few seconds of that solo{PUBLIC_NOTE if pipeline.PUBLIC else ""}.
Click a dot to open its page.</p>
<div class="controls"><button data-mode="springs" class="on">Springs</button><button data-mode="pca">PCA</button>
<button data-mode="umap">UMAP</button><svg id="sizes"></svg></div>
<div id="wrap"><svg id="graph"></svg><div id="tip" class="tip"></div></div>
<script>const DATA = {json.dumps({"nodes": nodes, "edges": scores["edges"]})};</script>
{GRAPH_JS}"""
    return page("Similarity graph", body, js=None, css=GRAPH_CSS, tail=sound.tags(), here="graph.html")


# ---------------------------------------------------------------- page

DESCRIPTION = "Drum Throne: An experimental benchmark composing drum solos with language models."
VIDEO_CSS = """
.video{margin:16px 0} .video iframe{width:100%;max-width:560px;aspect-ratio:16/9;border:0;border-radius:8px;display:block}
.video figcaption{font-size:13px;color:#57606a;margin-top:4px}
"""


def video(vid, start, caption, cls="video"):
    """An embedded YouTube player (privacy-enhanced mode) starting at start seconds, captioned."""
    return (f"<figure class='{cls}'><iframe src='https://www.youtube-nocookie.com/embed/{vid}?start={start}' "
            f"title='{escape(caption)}' loading='lazy' allow='encrypted-media; picture-in-picture' allowfullscreen>"
            f"</iframe><figcaption>{escape(caption)}</figcaption></figure>")


def page(title, body, js="plotly.min.js", css="", tail="", fork=True, here=None, description=DESCRIPTION):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
{og(title, description, "" if here in (None, "index.html") else here) if fork else ""}
{f'<script src="{js}"></script>' if js else ''}
<style>
body{{font-family:{FONT};color:{INK};background:#fff;margin:0;line-height:1.45}}
main{{max-width:1000px;margin:0 auto;padding:36px 24px 40px}}
h1{{font-size:30px;margin:0 0 6px}}
.sub{{color:{INK2};margin:0 0 20px;font-size:15px}}
h2{{font-size:21px;margin:56px 0 6px;padding-top:18px;border-top:1px solid {GRID}}}
{ACCENT_CSS.format()}
h3{{font-size:15px;margin:28px 0 2px}}
p.note,ul.note{{color:{INK2};font-size:14px;margin:2px 0 8px}}
table{{border-collapse:collapse;font-size:13px;margin-top:8px;width:100%}}
th{{text-align:left;color:{INK2};font-weight:600;border-bottom:1px solid {LIGHT};padding:4px 8px}}
td{{padding:4px 8px;border-bottom:1px solid {GRID}}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.m{{color:{MACHINE_C};font-weight:600}}
.chk{{font-size:12px;background:#fff1e5;color:#8a4600;border-radius:4px;padding:2px 6px;margin-left:6px;vertical-align:middle}}
.ok{{font-size:12px;background:#eef6ee;color:#1a5e1a;border-radius:4px;padding:2px 6px;margin-left:6px;vertical-align:middle}}
a{{color:#0969da}}
a.btn{{font-size:13px;border:1px solid {LIGHT};background:#f6f8fa;color:{INK};border-radius:6px;padding:3px 10px;text-decoration:none}}
.player{{position:sticky;top:0;z-index:5;background:#fff;padding:8px 0 4px;border-bottom:1px solid {GRID}}}
.player audio{{width:100%}}
.row{{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:6px 0}}
.lbl{{font-size:12px;color:{INK2};width:52px}}
button{{font:inherit;font-size:13px;border:1px solid {LIGHT};background:#f6f8fa;color:{INK};border-radius:6px;padding:3px 10px;cursor:pointer}}
button:hover{{background:#eaeef2}}
.now,.state{{font-size:13px;color:{INK2};margin-left:8px;font-variant-numeric:tabular-nums}}
.howto{{border:1px solid {GRID};border-radius:8px;padding:10px 16px;margin:12px 0;font-size:14px}}
.howto ol{{margin:6px 0;padding-left:20px}}
textarea{{width:100%;height:140px;font:12px ui-monospace,Menlo,monospace;margin-top:6px}}
pre{{white-space:pre-wrap;font:12.5px ui-monospace,Menlo,monospace;background:#f6f8fa;padding:10px;border-radius:6px}}
.bar{{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid {LIGHT};padding:8px 24px;display:flex;
gap:8px;align-items:center;font-size:14px;z-index:10}}
section.track{{padding-bottom:12px}}
ul.toc{{columns:2;font-size:14px;padding-left:18px}}
section h3{{margin-top:36px}}
ul.toc li{{margin:3px 0}}
audio.check{{width:100%;margin-bottom:8px}}
main{{padding-bottom:120px}}
{css}
{FORK_CSS + NAV_CSS if fork else ""}
</style></head><body>{FORK if fork else ""}<main>{nav(here=here) if fork else ""}{body}</main>{FOOTER if fork else ""}{MOBILE_JS if fork else ""}{tail}{COUNTER if fork else ""}</body></html>"""


def metric_label(scores, key):
    return next(m["label"] for ms in scores["axes"].values() for m in ms if m["key"] == key)


def field_table(scores, data, items):
    """One row per solo, in the order given."""
    by_id = {s["id"]: s for s in scores["solos"]}
    rows = []
    for it in items:
        s, f = by_id[it["id"]], data[it["id"]]["f"]["scalars"]
        cls = "" if it["group"] == "human" else " class='m'"
        src = f"<a href='{escape(it['url'])}'>source</a>" if it["group"] == "human" else escape(maker(it))
        if it["group"] == "human":
            a, b = pipeline.best_chunk(it)
            cut = f"<a href='detection.html#{it['id']}'>{mmss(a)} to {mmss(b)}</a>"
        else:
            cut = f"<a href='detection.html#{it['id']}'>whole solo</a>"
        rows.append(f"<tr data-solo='{it['id']}'><td{cls}><a href='{it['id']}/index.html'>{escape(it['label'])}</a></td><td>{src}</td>"
                    f"<td>{cut}</td><td class='num'>{mmss(f['duration_s'])}</td><td class='num'>{f['hits_per_s']:.1f}</td>"
                    f"<td class='num'>{np.median(data[it['id']]['f']['beats']['ibi_bpm']):.0f}</td>"
                    f"<td class='num'>{s['overall']:.0f}</td></tr>")
    return ("<table><tr><th>solo</th><th>source</th><th>part analyzed</th><th>analyzed</th><th>hits/s</th><th>pulse (BPM)</th>"
            "<th>score</th></tr>" + "".join(rows) + "</table>")


def main():
    items = pipeline.snapshot()
    scores = json.loads((OUT / "scores.json").read_text())
    data = load(items)
    models, _ = machine_groups(items)
    arc = arcs(data)
    hum = [s for s in scores["solos"] if s["group"] == "human"]
    gen = [s for s in scores["solos"] if s["group"] != "human"]  # scores.json lists solos by overall score
    by_id = {it["id"]: it for it in items}
    humans_abc = sorted([it for it in items if it["group"] == "human"], key=lambda it: it["label"])
    gen_items = [by_id[s["id"]] for s in gen]

    axis_html = "".join(
        f"<h3>{escape(a)}</h3>{html_of(fig_axis_metrics(a, specs, scores, items, models), 'ax_' + a)}"
        for a, specs in scores["axes"].items())
    axis_list = "".join(f"<li><b>{escape(a)}</b>: " + ", ".join(escape(m["label"]) for m in specs) + "</li>"
                        for a, specs in scores["axes"].items())
    body = f"""<h1>All measurements</h1>
<p class="sub">Every solo and every number behind its score, for the {len(hum)} recorded solos and the {len(gen)} generated ones
from the benchmark prompt. <a href="index.html">The main page</a> explains how the scores work and how far to trust them.
Recorded solos are <b style="color:{HUMAN_C}">gray</b>, generated ones <b style="color:{MACHINE_C}">magenta</b>, and hovering
any mark tells you which one it is.</p>

<h2>All solos</h2>
<p class="note">Names link to each solo's page. The part analyzed links to
<a href="detection.html">the scored part of each recording</a>.</p>
<h3>Recorded solos, alphabetically</h3>
{field_table(scores, data, humans_abc)}
<h3>Generated solos, by overall score</h3>
{field_table(scores, data, gen_items)}
<h3>Measurements in each group</h3>
<ul class="note">{axis_list}</ul>

<h2>Scores</h2>
<h3>Overall score</h3>{html_of(fig_overall(scores, items, models), 'overall')}
<h3>Recorded solos by group, alphabetically</h3>{html_of(fig_scoregrid(sorted(hum, key=lambda s: s['label'])), 'grid_h')}
<h3>Generated solos by group, by overall score</h3>{html_of(fig_scoregrid(gen), 'grid_g')}
<h3>Score by group</h3>{html_of(fig_axes_strip(scores, items, models), 'axes')}

<h2>Group by group</h2>
<p class="note">Every measurement behind the score, in its own units. The shaded band is the middle half of the recorded solos,
the line their full range.</p>
{axis_html}

<h2>Shape of a solo</h2>
<p class="note">Every solo stretched to the same length. Thin lines are individual solos, bands the middle half of each group,
thick lines the medians, gray for recorded solos and magenta for generated.</p>
<h3>Density</h3>{html_of(fig_arcs(data, arc, items, models, 'density', 'hits per second, relative to the solo average'), 'arc_d')}
<h3>Loudness</h3>{html_of(fig_arcs(data, arc, items, models, 'loudness', 'loudness relative to the whole solo (LU)'), 'arc_l')}
<h3>Tempo</h3>{html_of(fig_arcs(data, arc, items, models, 'tempo', 'tempo vs the solo median (%)'), 'arc_t')}

<h2>Map</h2>
<p class="note">All {len(scores['solos'])} solos placed by every scoring metric at once (principal components of the metrics,
each standardized by the recorded solos' spread). Nearby solos have similar measurements.</p>
{html_of(fig_map(scores, items, models), 'map')}

<h2>Feel</h2>
<p class="note">How tightly a solo sits on a steady grid, and how much individual strokes wobble inside steady runs.</p>
{html_of(fig_feel(scores, items, models), 'feel')}

<h2>Stroke spacing</h2>
<p class="note">Distribution of the time between consecutive strokes, one row per solo, sorted by the typical spacing.
Sharp single peaks are one subdivision played throughout. Wide or multi-peaked shapes mix several.</p>
{html_of(fig_ridgeline(data, items), 'ridge')}

<h2>Drum families</h2>
<p class="note">Share of hits by family, as the transcriber hears each solo (comparable with the recorded solos). The last two rows
average the generated solos as heard and as written in their own MIDI.</p>
{html_of(fig_families(data, items), 'fam')}
<h3>Range</h3><p class="note">Generated solos can write any of the 47 GM drum notes, but the transcriber names about
{int(np.median([data[s['id']]['f']['scalars']['distinct_notes'] for s in scores['solos']]))} different drums in a typical
solo (up to {max(data[s['id']]['f']['scalars']['distinct_notes'] for s in scores['solos'])}), so their written range
(filled) is wider than what it hears back (open).</p>
{html_of(fig_range(data, items, models), 'range')}

<h2>Playability</h2>
<p class="note">Stroke groups (hits within 30 ms) that need more than two hands or two feet. Only generated solos are
scored on this, counted in their own MIDI. A person played every recorded solo, so the values shown here for them are the
transcriber misreading flams, grace notes, cymbal chokes and foot percussion, and the recorded solos get full marks.</p>
{html_of(fig_playability(data, items, models), 'play')}

<h2>Structure</h2>
<p class="note">Self-similarity of what was played, each solo scaled to the same size. Dark squares on the diagonal are
sections, and off-diagonal blocks are returns to earlier material.</p>
{html_of(fig_gallery(data, items), 'gallery')}

<h2>Transcription accuracy</h2>
<p class="note">For generated solos the true notes are known, so the transcriber can be scored on each one.</p>
{html_of(fig_trust(data, items), 'trust')}"""
    SITE.mkdir(parents=True, exist_ok=True)
    labels = {name: it["id"] for it in items for name in (it["short"], it["label"])}
    (SITE / "measurements.html").write_text(page("All measurements", body, tail=sound.tags(labels=labels),
                                                 here="measurements.html"))
    (SITE / "detection.html").write_text(detection_page(data, items, scores))
    (SITE / "graph.html").write_text(graph_page(scores, data, items))
    print(f"wrote {SITE / 'measurements.html'}, detection.html and graph.html")
    if not pipeline.PUBLIC:  # the review tool is internal: never part of a public build
        REVIEW.mkdir(exist_ok=True)
        (REVIEW / "brackets.html").write_text(brackets_page(data, items))
        print(f"wrote {REVIEW / 'brackets.html'}")


if __name__ == "__main__":
    main()
