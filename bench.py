#!/usr/bin/env python3
"""OpenRouter benchmark harness for sandboxed code-generation tasks.

API models don't come with the sandbox a chat app gives them, so the harness
supplies it. Two modes:

  agent  Emulates a chat app *with* a code interpreter. The model gets bash,
         write_file, read_file and finish tools that run in a per-run Docker
         sandbox, and iterates until it calls finish or hits a limit.
  chat   Emulates a chat app *without* code execution. One request; the
         harness extracts the script from the reply and runs it.
         --chat-repairs N pastes errors back N times, like a user would.

Models that don't advertise tool support on OpenRouter are run in chat mode
(recorded as "chat-fallback") instead of failing silently.

Provider quirks handled: reasoning_details (Anthropic thinking blocks, Gemini
thought signatures) are echoed back unchanged; missing or duplicate tool-call
IDs are repaired; malformed tool arguments go back to the model as errors;
200 responses carrying an error body are retried; parameters a model doesn't
support are dropped; routing is restricted to providers that honor every
parameter sent; OpenRouter's context-compressing transform is disabled.

Setup: put OPENROUTER_API_KEY in .env, then `docker compose build`.

Run (model@setting picks a model's thinking: any effort listed under
"reasoning" in openrouter.ai/api/v1/models, or @on / @off; no @ means the
model's default):
  docker compose run --rm bench openai/gpt-6-sol@none openai/gpt-6-sol@max \\
      x-ai/grok-4.7 --mode chat --runs 1 --chat-repairs 2

Output goes to runs/<timestamp>/: a directory per run (transcript.jsonl,
work/, repro/, grade.json, solo.mp3, render.json), results.jsonl,
summary.csv and checks.csv. Only the shared script (work/out/drum_solo.py)
counts: the grader reruns it alone in repro/, and render.py turns
repro/solo.mid into solo.mp3 the same way for every run.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import difflib
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx

API = "https://openrouter.ai/api/v1"
HERE = Path(__file__).resolve().parent
RETRY_STATUS = {408, 429, 500, 502, 503, 504, 529}

SYSTEM_AGENT = """\
You are working in a Linux sandbox (Debian, Python 3.11) with no network access.
Your working directory is /work, and everything the task needs is preinstalled.
Use the tools to write and run code, and check that your outputs work before
finishing. To share a file with the user, save it in /work/out/. When the task
is complete, call the finish tool."""

SYSTEM_CHAT = """\
You cannot run code. Reply with the complete program in a single ```python block.
The harness saves it as drum_solo.py in an empty directory and runs
`python drum_solo.py` there, in a Linux sandbox (Debian, Python 3.11, no network)
with everything the task needs preinstalled."""

NUDGE = "Continue using the tools. Call finish when the task is complete."


def tool(name, description, properties, required):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


TOOLS = [
    tool("bash", "Run a bash command in /work. Returns the exit code and truncated stdout/stderr.",
         {"command": {"type": "string"},
          "timeout": {"type": "integer", "description": "Seconds (default 120, max 600)."}},
         ["command"]),
    tool("write_file", "Create or overwrite a text file. Relative paths resolve from /work.",
         {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    tool("read_file", "Read a text file (truncated if long).",
         {"path": {"type": "string"}}, ["path"]),
    tool("finish", "Call once the task is complete.",
         {"summary": {"type": "string"}}, ["summary"]),
]


def clip(s: str, n: int = 12000) -> str:
    if len(s) <= n:
        return s
    h = n // 2
    return f"{s[:h]}\n... [{len(s) - n} chars truncated] ...\n{s[-h:]}"


def container_opts() -> list[str]:
    opts = ["-e", "HOME=/tmp", "--memory", "2g", "--cpus", "2", "--pids-limit", "512"]
    if hasattr(os, "getuid"):  # keep files in the bind mount owned by you
        opts += ["--user", f"{os.getuid()}:{os.getgid()}"]
    return opts


# --------------------------------------------------------------------------- sandbox

class Sandbox:
    def __init__(self, image: str, workdir: Path, network: bool):
        self.name = f"drumbench-{uuid.uuid4().hex[:12]}"
        workdir.mkdir(parents=True, exist_ok=True)
        cmd = ["docker", "run", "-d", "--rm", "--name", self.name, *container_opts(),
               "-v", f"{workdir.resolve()}:/work", "-w", "/work"]
        if not network:
            cmd += ["--network", "none"]
        subprocess.run([*cmd, image, "sleep", "infinity"], check=True, capture_output=True)

    def exec(self, script: str, timeout: int = 120, stdin: str | None = None,
             args: tuple | list = ()) -> tuple[int, str, str]:
        # `timeout` runs inside the container so a killed exec doesn't leave strays.
        cmd = ["docker", "exec", *(["-i"] if stdin is not None else []), "-w", "/work", self.name,
               "timeout", "-k", "5", str(timeout), "bash", "-c", script, "_", *args]
        try:
            p = subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                               errors="replace", timeout=timeout + 30)
        except subprocess.TimeoutExpired:
            return 124, "", "harness timeout"
        return p.returncode, p.stdout, p.stderr

    def checked(self, script: str, stdin: str | None = None) -> str:
        """Run a harness command that must succeed; returns stdout."""
        rc, out, err = self.exec(script, 60, stdin=stdin)
        if rc:
            raise RuntimeError(f"sandbox command failed (exit {rc}): {script}\n{clip(err, 2000)}")
        return out

    def close(self):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def dispatch(sb: Sandbox, name: str, a: dict) -> str:
    if name == "bash":
        t = max(1, min(int(a.get("timeout") or 120), 600))
        rc, out, err = sb.exec(a["command"], t)
        note = " (timed out)" if rc in (124, 137) else ""
        return f"exit_code: {rc}{note}\n--- stdout ---\n{clip(out)}\n--- stderr ---\n{clip(err)}"
    if name == "write_file":
        content = str(a["content"])
        rc, _, err = sb.exec('mkdir -p -- "$(dirname -- "$1")" && cat > "$1"', 60,
                             stdin=content, args=[a["path"]])
        return f"wrote {len(content)} chars to {a['path']}" if rc == 0 else f"error: {clip(err, 2000)}"
    if name == "read_file":
        rc, out, err = sb.exec('cat -- "$1"', 60, args=[a["path"]])
        return clip(out, 20000) if rc == 0 else f"error: {clip(err, 2000)}"
    if name == "finish":
        return "ok"
    return f"error: unknown tool {name!r}"


# --------------------------------------------------------------------------- API

class APIError(RuntimeError):
    pass


class OpenRouter:
    def __init__(self, key: str):
        self.http = httpx.Client(base_url=API, timeout=httpx.Timeout(900, connect=30),
                                 headers={"Authorization": f"Bearer {key}", "X-Title": "drumbench"})

    def models(self) -> dict[str, dict]:
        r = self.http.get("/models")
        r.raise_for_status()
        return {m["id"]: m for m in r.json()["data"]}

    def complete(self, body: dict, attempts: int = 6) -> dict:
        last = None
        for i in range(attempts):
            if i:
                time.sleep(min(60, 2 ** i + random.random()))
            try:
                r = self.http.post("/chat/completions", json=body)
            except httpx.TransportError as e:
                last = f"transport error: {e}"
                continue
            if r.status_code in RETRY_STATUS:
                last = f"HTTP {r.status_code}: {r.text[:300]}"
                continue
            if r.status_code != 200:
                raise APIError(f"HTTP {r.status_code}: {r.text[:1000]}")
            try:
                data = r.json()
            except ValueError:
                last = f"non-JSON body: {r.text[:300]}"
                continue
            # OpenRouter can return 200 with the upstream error in the body or the choice.
            err = data.get("error") or (data.get("choices") or [{}])[0].get("error")
            if err or not data.get("choices"):
                last = f"error in body: {err or 'no choices'}"
                code = err.get("code") if isinstance(err, dict) else None
                if isinstance(code, int) and code not in RETRY_STATUS:
                    raise APIError(last)
                continue
            return data
        raise APIError(f"gave up after {attempts} attempts; last: {last}")


def thinking_settings(info: dict) -> list[str]:
    """Thinking settings a model takes: its listed efforts, plus on and (unless mandatory) off."""
    r = info.get("reasoning") or {}
    if not r or "reasoning" not in (info.get("supported_parameters") or []):
        return []
    return [*(r.get("supported_efforts") or []), "on", *([] if r.get("mandatory") else ["off"])]


def default_thinking(info: dict) -> str:
    r = info.get("reasoning") or {}
    if not r:
        return "none"
    return r.get("default_effort") or ("on" if r.get("mandatory") or r.get("default_enabled") else "off")


def parse_spec(spec: str, catalog: dict) -> tuple[str, str | None]:
    """'vendor/model[@setting]' -> (model id, thinking setting or None for the model's default)."""
    model, at, setting = spec.partition("@")
    if model not in catalog:
        near = difflib.get_close_matches(model, list(catalog), n=3)
        raise ValueError(f"unknown model {model!r}" + (f"; did you mean {', '.join(near)}?" if near else ""))
    if not at:
        return model, None
    allowed = thinking_settings(catalog[model])
    if setting not in allowed:
        raise ValueError(f"{model} doesn't take thinking setting {setting!r}; "
                         + (f"choose from {', '.join(allowed)}" if allowed else "it has no thinking settings"))
    return model, setting


def token_budget(args, info: dict) -> int:
    """--max-tokens if given, else the model's own output limit. Never clamped."""
    cap = (info.get("top_provider") or {}).get("max_completion_tokens")
    if args.max_tokens is None:
        if not cap:
            raise ValueError(f"{info['id']} lists no output limit; pass --max-tokens")
        return cap
    if cap and args.max_tokens > cap:
        raise ValueError(f"--max-tokens {args.max_tokens} exceeds {info['id']}'s limit of {cap}")
    return args.max_tokens


def make_body(args, info: dict, thinking: str | None, messages: list, tools: list | None = None) -> dict:
    sp = set(info.get("supported_parameters") or [])
    body = {
        "model": info["id"],
        "messages": messages,
        "max_tokens": token_budget(args, info),
        "usage": {"include": True},
        "transforms": [],  # never silently compress the transcript
    }
    if tools:
        body["tools"] = tools
    if thinking in ("on", "off"):
        body["reasoning"] = {"enabled": thinking == "on"}
    elif thinking:
        body["reasoning"] = {"effort": thinking}
    if args.temperature is not None and "temperature" in sp:
        body["temperature"] = args.temperature
    if args.seed is not None and "seed" in sp:
        body["seed"] = args.seed
    provider = {"require_parameters": True}
    if args.provider:
        provider.update(order=args.provider, allow_fallbacks=False)
    body["provider"] = provider
    return body


def assistant_turn(msg: dict) -> dict:
    """Rebuild the assistant message so every provider accepts it next turn.
    reasoning_details must go back unchanged or multi-turn tool use breaks
    on models that sign their reasoning."""
    out = {"role": "assistant", "content": msg.get("content")}
    calls, seen = msg.get("tool_calls") or [], set()
    for c in calls:
        if not c.get("id") or c["id"] in seen:
            c["id"] = f"call_{uuid.uuid4().hex[:24]}"
        seen.add(c["id"])
        c["type"] = "function"
    if calls:
        out["tool_calls"] = calls
    elif out["content"] is None:
        out["content"] = ""
    if msg.get("reasoning_details"):
        out["reasoning_details"] = msg["reasoning_details"]
    return out


# --------------------------------------------------------------------------- runs

@dataclass
class Run:
    model: str
    mode: str  # agent | chat | chat-fallback
    index: int
    dir: Path
    thinking: str | None = None  # None = the model's default
    cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    turns: int = 0
    providers: set = field(default_factory=set)
    stop: str = ""
    t0: float = field(default_factory=time.monotonic)

    def log(self, kind: str, payload):
        line = {"t": round(time.monotonic() - self.t0, 2), "kind": kind, "data": payload}
        with open(self.dir / "transcript.jsonl", "a") as f:
            f.write(json.dumps(line) + "\n")

    def account(self, data: dict):
        u = data.get("usage") or {}
        self.turns += 1
        self.cost += float(u.get("cost") or 0)
        self.prompt_tokens += u.get("prompt_tokens") or 0
        self.completion_tokens += u.get("completion_tokens") or 0
        self.reasoning_tokens += (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
        if data.get("provider"):
            self.providers.add(data["provider"])
        self.log("response", data)


def run_agent(client, args, info, prompt, run: Run, sb: Sandbox) -> str:
    messages = [{"role": "system", "content": SYSTEM_AGENT}, {"role": "user", "content": prompt}]
    nudges = 0
    while True:
        if run.turns >= args.max_turns:
            return "max_turns"
        if run.cost >= args.max_cost:
            return "max_cost"
        if time.monotonic() - run.t0 >= args.wall_clock:
            return "wall_clock"
        data = client.complete(make_body(args, info, run.thinking, messages, TOOLS))
        run.account(data)
        choice = data["choices"][0]
        msg = assistant_turn(choice["message"])
        messages.append(msg)
        calls = msg.get("tool_calls", [])
        if not calls:
            nudges += 1
            if nudges > args.max_nudges:
                return "no_tool_calls"
            messages.append({"role": "user", "content": NUDGE})
            continue
        nudges, done = 0, False
        for c in calls:
            name = (c.get("function") or {}).get("name", "")
            try:
                raw = c["function"].get("arguments") or "{}"
                a = json.loads(raw) if isinstance(raw, str) else raw
                if not isinstance(a, dict):
                    raise TypeError("arguments must be a JSON object")
                result = dispatch(sb, name, a)
                done |= name == "finish"
            except (ValueError, KeyError, TypeError) as e:
                cut = " (your reply hit the token limit)" if choice.get("finish_reason") == "length" else ""
                result = f"error: bad arguments{cut}: {e}. Re-issue the call."
            run.log("tool", {"name": name, "result": result})
            messages.append({"role": "tool", "tool_call_id": c["id"], "name": name, "content": result})
        if done:
            return "finished"


CODE_RE = re.compile(r"```([\w+-]*)[ \t]*\n(.*?)```", re.S)


def extract_code(text: str | None) -> str | None:
    blocks = CODE_RE.findall(text or "")
    py = [b for lang, b in blocks if lang.lower() in ("python", "py", "python3")]
    pool = py or [b for _, b in blocks]
    return max(pool, key=len) if pool else None


def run_and_share(sb: Sandbox, code: str, timeout: int) -> tuple[int, str, str, list[str]]:
    """Run a chat reply's script as the user would, alone in an empty directory,
    then share it in out/. Returns problems found."""
    sb.checked("find . -mindepth 1 -delete && mkdir run && cat > run/drum_solo.py", stdin=code)
    rc, out, err = sb.exec("cd run && python drum_solo.py", timeout)
    sb.checked("mkdir out && cat > out/drum_solo.py", stdin=code)
    wrote = sb.checked("[ -f run/solo.mid ] && echo yes || echo no").strip() == "yes"
    return rc, out, err, [] if wrote else ["no solo.mid was written"]


def run_chat(client, args, info, prompt, run: Run, sb: Sandbox) -> str:
    messages = [{"role": "system", "content": SYSTEM_CHAT}, {"role": "user", "content": prompt}]
    for attempt in range(args.chat_repairs + 1):
        if run.cost >= args.max_cost:
            return "max_cost"
        data = client.complete(make_body(args, info, run.thinking, messages))
        run.account(data)
        msg = assistant_turn(data["choices"][0]["message"])
        messages.append(msg)
        code = extract_code(msg.get("content"))
        if code is None:
            feedback = "I couldn't find a ```python block in your reply. Send the complete program."
        else:
            rc, out, err, problems = run_and_share(sb, code, args.run_timeout)
            run.log("run", {"exit_code": rc, "stdout": clip(out), "stderr": clip(err), "problems": problems})
            if rc == 0 and not problems:
                return "finished"
            feedback = (f"I ran it and it failed (exit code {rc}" + "".join(f"; {p}" for p in problems) + ").\n"
                        f"stderr:\n{clip(err, 6000)}\nstdout:\n{clip(out, 2000)}\n"
                        "Send the complete corrected program.")
        if attempt < args.chat_repairs:
            messages.append({"role": "user", "content": feedback})
    return "failed"


def grade(image: str, work: Path, repro: Path) -> dict:
    # The shared script is rerun in the empty repro dir at /work, the path the
    # sandbox used, so absolute /work paths behave the same.
    repro.mkdir()
    cmd = ["docker", "run", "--rm", "--network", "none", *container_opts(),
           "-v", f"{work.resolve()}:/submission:ro", "-v", f"{repro.resolve()}:/work",
           "-v", f"{HERE / 'grader.py'}:/grader.py:ro",
           image, "python", "/grader.py", "/submission", "/work"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=900)
    except subprocess.TimeoutExpired:
        return {"score": 0.0, "error": "grader timed out"}
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"score": 0.0, "error": f"grader failed: {p.stderr[-2000:]}"}


def render(image: str, repro: Path, out: Path) -> dict:
    """Render repro/solo.mid to out/solo.mp3 the same way for every run."""
    cmd = ["docker", "run", "--rm", "--network", "none", *container_opts(),
           "-v", f"{repro.resolve()}:/in:ro", "-v", f"{out.resolve()}:/out",
           "-v", f"{HERE / 'render.py'}:/render.py:ro",
           image, "python", "/render.py", "/in/solo.mid", "/out/solo.mp3"]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=600)
    if p.returncode:
        raise RuntimeError(f"render failed: {p.stderr.strip()[-2000:]}")
    return json.loads(p.stdout)


def slug(model: str) -> str:
    return re.sub(r"[^\w.-]+", "_", model)


def run_one(client, args, info, prompt, root: Path, model: str, thinking: str | None, mode: str, i: int) -> dict:
    run = Run(model, mode, i, root / slug(model) / f"{mode}-{i}", thinking)
    run.dir.mkdir(parents=True, exist_ok=True)
    work, error = run.dir / "work", None
    try:
        with Sandbox(args.image, work, args.network) as sb:
            runner = run_agent if mode == "agent" else run_chat
            run.stop = runner(client, args, info, prompt, run, sb)
    except Exception as e:  # one bad run shouldn't sink the batch
        run.stop, error = "error", f"{type(e).__name__}: {e}"
        run.log("error", error)
    seconds = time.monotonic() - run.t0
    report = grade(args.image, work, run.dir / "repro")
    (run.dir / "grade.json").write_text(json.dumps(report, indent=2))
    mp3 = None
    if (report.get("checks") or {}).get("midi_parses", {}).get("value") == 1:
        try:
            rendered = render(args.image, run.dir / "repro", run.dir)
            (run.dir / "render.json").write_text(json.dumps(rendered, indent=2))
            mp3 = str(run.dir / "solo.mp3")
        except Exception as e:  # recorded; one bad render shouldn't sink the batch
            msg = f"render: {type(e).__name__}: {e}"
            run.log("error", msg)
            error = f"{error}; {msg}" if error else msg
    return {
        # The catalog's default isn't always what the provider does; reasoning_tokens is.
        "model": model, "thinking": thinking or "default", "catalog_default": default_thinking(info),
        "mode": mode, "run": i, "score": report.get("score", 0.0),
        "stop": run.stop, "error": error or report.get("error"), "turns": run.turns,
        "cost": round(run.cost, 5), "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens, "reasoning_tokens": run.reasoning_tokens,
        "providers": sorted(run.providers), "seconds": round(seconds, 1),
        "checks": {k: v["value"] for k, v in (report.get("checks") or {}).items()},
        "dir": str(run.dir),
        "mp3": mp3,
    }


# --------------------------------------------------------------------------- reporting

def summarize(results: list[dict], root: Path):
    groups: dict[tuple, list] = {}
    for r in results:
        groups.setdefault((r["model"], r["mode"]), []).append(r)
    rows, check_rows = [], []
    for (model, mode), rs in groups.items():
        s = [r["score"] for r in rs]
        rows.append({
            "model": model, "mode": mode, "runs": len(rs),
            "mean": round(statistics.mean(s), 1),
            "stdev": round(statistics.stdev(s), 1) if len(s) > 1 else 0.0,
            "min": min(s), "max": max(s),
            "finished": sum(r["stop"] == "finished" for r in rs),
            "mean_cost": round(statistics.mean(r["cost"] for r in rs), 4),
            "mean_turns": round(statistics.mean(r["turns"] for r in rs), 1),
            "mean_seconds": round(statistics.mean(r["seconds"] for r in rs)),
        })
        for name in sorted({k for r in rs for k in r["checks"]}):
            vals = [r["checks"].get(name, 0.0) for r in rs]
            check_rows.append({"model": model, "mode": mode, "check": name,
                               "mean": round(statistics.mean(vals), 3)})
    rows.sort(key=lambda r: -r["mean"])
    for path, data in (("summary.csv", rows), ("checks.csv", check_rows)):
        if data:
            with open(root / path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(data[0]))
                w.writeheader()
                w.writerows(data)
    print(f"\n{'model':<42}{'mode':<15}{'n':>3}{'mean':>7}{'sd':>6}{'done':>6}{'$/run':>9}{'s/run':>7}")
    for r in rows:
        print(f"{r['model']:<42}{r['mode']:<15}{r['runs']:>3}{r['mean']:>7.1f}{r['stdev']:>6.1f}"
              f"{r['finished']:>6}{r['mean_cost']:>9.3f}{r['mean_seconds']:>7}")
    print(f"\nresults in {root}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("models", nargs="+", help="OpenRouter model IDs, each optionally @thinking (e.g. @max, @off)")
    p.add_argument("--mode", choices=["agent", "chat", "both"], default="both")
    p.add_argument("--runs", type=int, default=1, help="runs per model per mode")
    p.add_argument("--prompt", type=Path, default=HERE / "prompt.md")
    p.add_argument("--image", default="drumbench")
    p.add_argument("--out", type=Path, default=Path("runs"))
    p.add_argument("--jobs", type=int, default=4, help="concurrent runs")
    p.add_argument("--max-turns", type=int, default=40)
    p.add_argument("--max-nudges", type=int, default=2, help="agent: replies without tool calls tolerated in a row")
    p.add_argument("--max-cost", type=float, default=2.0, help="USD cap per run")
    p.add_argument("--wall-clock", type=float, default=1800, help="seconds cap per run")
    p.add_argument("--max-tokens", type=int, help="default: each model's own output limit")
    p.add_argument("--temperature", type=float)
    p.add_argument("--seed", type=int)
    p.add_argument("--provider", action="append", help="pin an upstream provider (repeatable, in order)")
    p.add_argument("--chat-repairs", type=int, default=0, help="chat: paste errors back this many times")
    p.add_argument("--run-timeout", type=int, default=300, help="chat: seconds to run the script")
    p.add_argument("--network", action="store_true", help="allow network inside the sandbox")
    args = p.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("set OPENROUTER_API_KEY")
    if subprocess.run(["docker", "image", "inspect", args.image], capture_output=True).returncode:
        sys.exit(f"docker image {args.image!r} not found; run: docker build -t {args.image} {HERE}")
    prompt = args.prompt.read_text()
    client = OpenRouter(key)
    catalog = client.models()

    jobs = []
    for spec in args.models:
        try:
            m, thinking = parse_spec(spec, catalog)
            token_budget(args, catalog[m])
        except ValueError as e:
            sys.exit(str(e))
        has_tools = "tools" in (catalog[m].get("supported_parameters") or [])
        for mode in (["agent", "chat"] if args.mode == "both" else [args.mode]):
            if mode == "agent" and not has_tools:
                if args.mode == "both":
                    print(f"note: {m} lacks tool support; running chat mode only", file=sys.stderr)
                    continue
                print(f"note: {m} lacks tool support; running as chat-fallback", file=sys.stderr)
                mode = "chat-fallback"
            jobs += [(spec, m, thinking, mode, i) for i in range(args.runs)]

    root = args.out / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    root.mkdir(parents=True)
    (root / "config.json").write_text(json.dumps(
        {**{k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}, "prompt": prompt},
        indent=2))

    results = []
    with cf.ThreadPoolExecutor(args.jobs) as pool:
        futs = [pool.submit(run_one, client, args, catalog[m], prompt, root, spec, thinking, mode, i)
                for spec, m, thinking, mode, i in jobs]
        for f in cf.as_completed(futs):
            r = f.result()
            results.append(r)
            with open(root / "results.jsonl", "a") as fh:
                fh.write(json.dumps(r) + "\n")
            print(f"{r['model']:<42}{r['mode']:<15}#{r['run']:<3}score {r['score']:5.1f}  "
                  f"{r['stop']:<14}${r['cost']:.3f}  {r['seconds']:.0f}s"
                  + (f"  [{r['error'][:80]}]" if r["error"] else ""), flush=True)
    summarize(results, root)


if __name__ == "__main__":
    main()
