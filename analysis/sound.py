#!/usr/bin/env python3
"""Hover previews for the whole site.

build() cuts a short clip from every solo this build can play (generated solos always, human recordings only in the
local build) and writes sound.js. Every page then calls tags(): marks whose trace carries meta (one solo id, or one per
point), tick labels that name a solo, and elements with data-solo play that solo's clip when hovered, fading in. A
trace with meta {src, offset}, and on a solo's own page every time chart, plays the hovered moment instead. One switch,
remembered across pages, turns it on. Clicking a mark does nothing. With the switch on, a recorded solo this build has
no audio for shows a note saying why it is silent.

usage: uv run python sound.py      (the pipeline's pages stage runs it first)
"""
import functools
import json
import subprocess
from pathlib import Path

import numpy as np

import pipeline
from hillclimb import RESULTS, WORK as RUN_WORK

CLIP_S = 8.0     # clip length
FADE_OUT = 0.8   # baked into the clip's end; the fade-in happens in the page, so a hover never starts with a click


def preview_start(f):
    """Recording time two seconds before a solo's most intense moment."""
    seg0 = f["clip"]["segment"][0]
    t = np.array(f["windows"]["t"], dtype=float)
    inten = np.array(f["windows"]["intensity"], dtype=float)
    return max(seg0, seg0 + float(t[np.nanargmax(inten)]) - 2.0)


def run_id(rec):
    """Site id of a hill-climb or thinking run: its path under the runs folder."""
    return "run-" + "-".join(Path(rec["dir"]).parts[2:])


def run_features(rec):
    return json.loads((RUN_WORK / "__".join(Path(rec["dir"]).parts[2:]) / "features.json").read_text())


def cut(src, start, dst):
    if not pipeline.stale(dst, src):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{CLIP_S}", "-i", str(src),
                    "-af", f"afade=t=out:st={CLIP_S - FADE_OUT}:d={FADE_OUT}", "-ac", "2", "-b:a", "128k", str(dst)],
                   check=True)


def build():
    clips = {}
    for it in pipeline.snapshot():
        if it["group"] == "human" and pipeline.PUBLIC:
            continue  # human recordings are never part of a public build
        f = json.loads((pipeline.OUT / it["id"] / "features.json").read_text())
        rel = f"audio/clip/{it['id']}.mp3"
        cut(it["audio"], preview_start(f), pipeline.SITE / rel)
        clips[it["id"]] = rel
    if not pipeline.PUBLIC:  # the human solos rebuilt on the General MIDI kit (samekit.py), local like the recordings
        for it in pipeline.snapshot():
            if it["group"] != "human":
                continue
            src = pipeline.WORK / "samekit" / it["id"] / "solo.mp3"
            if not src.exists():
                raise SystemExit(f"{src} is missing: run samekit.py")
            f = json.loads((pipeline.OUT / it["id"] / "features.json").read_text())
            rel = f"audio/clip/samekit-{it['id']}.mp3"
            cut(src, preview_start(f) - f["clip"]["segment"][0], pipeline.SITE / rel)  # the rebuild starts at the scored part
            clips[f"samekit-{it['id']}"] = rel
    for rec in json.loads(RESULTS.read_text()):
        if rec["error"] or rec["failed"]:
            continue
        rel = f"audio/clip/{run_id(rec)}.mp3"
        cut(pipeline.ROOT / rec["dir"] / "solo.mp3", preview_start(run_features(rec)), pipeline.SITE / rel)
        clips[run_id(rec)] = rel
    (pipeline.SITE / "audio" / "clip" / "index.json").write_text(json.dumps(clips, sort_keys=True))
    (pipeline.SITE / "sound.js").write_text(SOUND_JS)
    print(f"{len(clips)} clips, sound.js")


@functools.cache
def recorded():
    """Ids whose marks stand for a recorded solo: the recordings and their General MIDI rebuilds."""
    ids = [it["id"] for it in pipeline.snapshot() if it["group"] == "human"]
    return ids + [f"samekit-{i}" for i in ids]


def tags(prefix="", labels=None, solo=None):
    """What a page includes at the end of its body. prefix: path from the page to the site root. labels: tick-label
    text -> solo id. solo: on a solo's own page, {"src": its audio, "offset": recording time of the page's zero,
    "charts": ids of the time charts}."""
    clips = json.loads((pipeline.SITE / "audio" / "clip" / "index.json").read_text())
    data = {"clips": {k: prefix + v for k, v in clips.items()}, "labels": labels or {}, "solo": solo,
            "recorded": [i for i in recorded() if i not in clips]}
    return (f"<style>{SOUND_CSS}</style><script>window.SOUND = {json.dumps(data)};</script>"
            f'<script src="{prefix}sound.js"></script>')


SOUND_CSS = """
.sound-switch{margin-left:auto;display:flex;align-items:center;gap:6px;font:inherit;font-size:13px;font-weight:600;
padding:4px 12px 4px 9px;border-radius:999px;border:1px solid #c9d1d9;background:#fff;color:#57606a;cursor:pointer}
.sound-switch:hover{background:#f6f8fa} .sound-switch.on{border-color:#b8860b;color:#1f2328;background:#fff8e5}
.sound-switch small{color:#b36b00;margin-left:4px;font-weight:400}
.sound-switch svg{width:16px;height:16px}
.sound-switch.pulse{animation:sound-pulse 1.6s ease-in-out 5}
@keyframes sound-pulse{0%,100%{box-shadow:none}50%{box-shadow:0 0 0 6px rgba(184,134,11,.28)}}
.sound-hint{position:absolute;top:calc(100% + 8px);right:0;z-index:31;width:260px;background:#fff8e5;border:1px solid #d4a72c;
border-radius:10px;padding:10px 32px 10px 14px;font-size:13.5px;line-height:1.45;color:#1f2328;box-shadow:0 2px 8px rgba(0,0,0,.12)}
@media (max-width:1200px){.sound-hint{right:84px}}
@media (max-width:700px){.sound-hint{position:relative;top:auto;right:auto;left:auto;width:auto;margin:0 0 16px;
padding-right:48px}
.sound-hint button{width:40px;height:40px;top:2px;right:2px;font-size:24px}}
.sound-hint button{position:absolute;top:4px;right:6px;border:0;background:none;font-size:18px;color:#8a4600;cursor:pointer}
button.sound-cta{font:inherit;font-size:14px;font-weight:600;padding:6px 14px;border-radius:999px;cursor:pointer;
border:1px solid #b8860b;background:#fff;color:#8a4600}
button.sound-cta.on{background:#fff8e5;color:#1f2328}
.sound-note{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom, 0px));transform:translateX(-50%);
z-index:40;width:max-content;max-width:calc(100vw - 32px);background:#fff8e5;border:1px solid #d4a72c;border-radius:10px;
padding:8px 14px;font-size:13.5px;line-height:1.45;color:#1f2328;box-shadow:0 2px 8px rgba(0,0,0,.12);
pointer-events:none;opacity:0;transition:opacity .15s}
.sound-note.show{opacity:1}
"""

SOUND_JS = r"""// Hover previews: hovering any mark for a solo plays a few seconds of it, fading in. One switch for the whole site.
(() => {
  const KEY = "drumthrone-sound", FADE_IN = 120, FADE_OUT = 220, DWELL = 110;
  const {clips, labels, solo, recorded} = window.SOUND;
  const unheard = new Set(recorded);  // recorded solos this build has no audio for
  let on = localStorage.getItem(KEY) === "on", playing = null, key = null, timer = null, ticket = 0;
  const touch = matchMedia("(pointer: coarse)").matches;
  const ICON = '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M3 6h2.5L9 3v10L5.5 10H3z"/>' +
    '<path d="M11 5.5a3.5 3.5 0 0 1 0 5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
  const sw = document.createElement("button");
  sw.className = "sound-switch";
  sw.title = "Hear a few seconds of a solo when you hover over it";
  const draw = note => {
    sw.innerHTML = `${ICON}<span>${on ? "Hover sound on" : "Hover sound off"}</span>` + (note ? `<small>${note}</small>` : "");
    sw.setAttribute("aria-label", on ? "Hover sound on" : "Hover sound off");
    sw.classList.toggle("on", on);
  };
  let hint = null;
  const ctas = () => document.querySelectorAll("button.sound-cta").forEach(b => {
    b.textContent = on ? "Hover sound is on" : "Turn on hover sound";
    b.classList.toggle("on", on);
  });
  const set = v => {
    on = v;
    localStorage.setItem(KEY, on ? "on" : "off");
    draw(); ctas();
    sw.classList.remove("pulse");
    if (hint) { hint.remove(); hint = null; }
    if (!on) { stop(); unexplain(0); }
  };
  // with sound on, pointing at a recorded solo that can't play says why
  const note = document.createElement("div");
  note.className = "sound-note";
  note.setAttribute("role", "status");
  note.textContent = "Recorded solos don't play because the recordings aren't on this site.";
  document.body.appendChild(note);
  let noteTimer = null;
  const unexplain = ms => {
    clearTimeout(noteTimer);
    noteTimer = setTimeout(() => note.classList.remove("show"), ms);  // a short wait, so sweeping between dots doesn't flicker
  };
  const explain = () => {
    if (!on) return;
    clearTimeout(noteTimer);
    note.classList.add("show");
    if (touch) unexplain(3000);
  };
  sw.onclick = () => set(!on);
  document.querySelectorAll("button.sound-cta").forEach(b => { b.onclick = () => set(!on); });
  const bar = document.querySelector("nav.site");
  if (!bar) throw new Error("sound.js needs the page's nav bar to hold its switch");
  bar.appendChild(sw);
  draw(); ctas();
  // first visit: say out loud that everything can be heard
  if (localStorage.getItem(KEY) === null) {
    hint = document.createElement("div");
    hint.className = "sound-hint";
    hint.innerHTML = "Turn on hover sound, then point at or tap a generated solo's dot or name to hear a few seconds of it." +
      '<button aria-label="dismiss">\u00d7</button>';
    hint.querySelector("button").onclick = () => set(false);
    // on phones the nav scrolls sideways and would clip the hint, so it sits in the page right under the nav instead
    if (matchMedia("(max-width: 700px)").matches) bar.after(hint); else bar.appendChild(hint);
    sw.classList.add("pulse");
  }

  // iOS starts audio only from a tap, and later only on a player a tap has already started. So previews take turns on
  // a small pool of players, and the first tap, click or key press anywhere on the page starts each of them silently.
  const SILENT = "data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSADAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==";
  const pool = [new Audio(), new Audio(), new Audio()];
  let turn = 0, unlocked = false;
  const unlock = () => {
    if (unlocked) return;
    unlocked = true;
    pool.forEach(a => {
      if (a === playing) return;  // a preview this same tap started already unlocked it
      a.muted = true;
      a.src = SILENT;
      a.play().then(() => { if (a.src === SILENT) a.pause(); a.muted = false; },
                    e => {
                      a.muted = false;
                      if (e.name === "AbortError") return;  // a preview took this player over within the same tap
                      unlocked = false;
                      console.warn("sound.js could not unlock a player", e);
                    });
    });
  };
  ["touchend", "click", "keydown"].forEach(t => document.addEventListener(t, unlock, true));
  // each use of a player is a new generation, so a fade or pause left over from its last preview never touches the next
  const fade = (a, to, ms) => {
    const gen = a.gen, from = a.volume, t0 = performance.now();
    const step = now => {
      if (a.gen !== gen) return;
      const k = Math.max(0, Math.min(1, (now - t0) / ms));  // a frame's timestamp can come just before t0
      a.volume = Math.max(0, Math.min(1, from + (to - from) * k));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  // every preview holds a ticket; stopping takes it back, so audio still loading when the pointer moves off never starts
  const release = () => {
    ticket++;
    if (!playing) return;
    const a = playing;
    playing = null;
    a.gen++;
    const gen = a.gen;
    fade(a, 0, FADE_OUT);
    setTimeout(() => { if (a.gen === gen) a.pause(); }, FADE_OUT + 20);  // a timer: animation frames stop in background tabs
  };
  const stop = () => { clearTimeout(timer); key = null; release(); if (!touch) unexplain(200); };
  const start = (src, t, k, now) => {
    if (!on || k === key) return;
    clearTimeout(timer);
    key = k;
    const go = () => {
      release();
      const mine = ticket, a = pool[turn];
      turn = (turn + 1) % pool.length;
      a.gen = (a.gen || 0) + 1;
      a.muted = false;
      a.volume = 0;
      a.src = t ? `${src}#t=${t.toFixed(2)}` : src;  // a media fragment starts it at the moment without waiting to load
      playing = a;
      a.play().then(() => { if (mine === ticket) fade(a, 1, FADE_IN); else a.pause(); },
                    e => {
                      if (e.name === "NotAllowedError") draw("tap or click the page once to allow sound");
                      else if (e.name !== "AbortError") console.warn("sound.js could not play", src, e);
                    });
    };
    if (now) go(); else timer = setTimeout(go, DWELL);
  };
  const clip = (id, now) => {
    if (id && clips[id]) start(clips[id], 0, id, now);
    else if (unheard.has(id)) { stop(); explain(); }
  };
  const idOf = pt => {
    const m = pt.data.meta;
    if (typeof m === "string") return m;
    const i = Array.isArray(pt.pointIndex) ? pt.pointIndex[0] : pt.pointIndex;
    return Array.isArray(m) ? m[i] : null;
  };
  const wire = gd => {
    const timed = solo && solo.charts.includes(gd.id);
    const hover = (ev, now) => {
      const pt = ev.points[0], m = pt.data.meta;
      // a trace can carry its own audio and offset (meta {src, offset}): the hovered time plays
      if (m && m.src && typeof pt.x === "number") start(m.src, m.offset + pt.x, `${m.src}#${Math.floor(pt.x / 3)}`, now);
      else if (timed && typeof pt.x === "number") start(solo.src, solo.offset + pt.x, `t${Math.floor(pt.x / 3)}`, now);
      else clip(idOf(pt), now);
    };
    gd.on("plotly_hover", ev => hover(ev, false));
    // on a phone a tap is the hover: play it right away, inside the tap, which is what iOS allows
    gd.on("plotly_click", ev => { if (touch) { clearTimeout(timer); key = null; hover(ev, true); } });
    gd.on("plotly_unhover", stop);
    gd.addEventListener("mouseleave", stop);
    const ticks = () => gd.querySelectorAll(".xtick text, .ytick text").forEach(el => {
      const id = labels[el.textContent.trim()];
      if (!id || !(clips[id] || unheard.has(id))) return;
      el.style.pointerEvents = "all";
      if (clips[id]) el.style.cursor = "pointer";
      el.onmouseenter = () => clip(id);
      el.onmouseleave = stop;
      el.onclick = () => { if (touch) { key = null; clip(id, true); } };
    });
    ticks();
    gd.on("plotly_afterplot", ticks);
  };
  document.querySelectorAll(".js-plotly-plot").forEach(wire);
  document.querySelectorAll("[data-solo]").forEach(el => {
    el.addEventListener("mouseenter", () => clip(el.dataset.solo));
    el.addEventListener("mouseleave", stop);
  });
  // a page's own players take over from previews; leaving the page or the window stops them too
  document.querySelectorAll("audio").forEach(a => a.addEventListener("play", stop));
  document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
  window.addEventListener("blur", stop);
  window.drumSound = {clip, stop, clips, playing: () => (playing ? playing.src : null),
                      explaining: () => note.classList.contains("show")};
})();
"""


if __name__ == "__main__":
    build()
