#!/usr/bin/env python3
"""Finish hill-climb chat runs that ended without a MIDI file the way the main experiment's runs do: the error, or
the missing program, goes back to the model in the same conversation, up to two repair turns in all.

The conversation is rebuilt from the run's transcript and continued with bench.py's own functions; the run's first
grade and render move to pre_rescue/ and its line in results.jsonl is updated (the original file is kept as
results.pre_rescue.jsonl).

usage: <root>/.venv/bin/python rescue.py      (hillclimb.py rescue runs it with the API key loaded)
"""
import concurrent.futures as cf
import json
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import bench  # noqa: E402

RUNS = ROOT / "hillclimb" / "runs"
REPAIRS, MAX_COST = 2, 50.0  # the main experiment's --chat-repairs and --max-cost
NO_CODE = "I couldn't find a ```python block in your reply. Send the complete program."  # bench.run_chat's words
LOCK = threading.Lock()


def failure_feedback(rc, out, err, problems):
    """bench.run_chat's message for a program that failed."""
    return (f"I ran it and it failed (exit code {rc}" + "".join(f"; {p}" for p in problems) + ").\n"
            f"stderr:\n{bench.clip(err, 6000)}\nstdout:\n{bench.clip(out, 2000)}\n"
            "Send the complete corrected program.")


def conversation(run_dir, prompt):
    """The messages bench.py held when the run stopped, the feedback its next turn would send, the replies so far, and
    the usage they cost (summed as bench.Run.account does, so an interrupted rescue picks up where it stopped)."""
    messages = [{"role": "system", "content": bench.SYSTEM_CHAT}, {"role": "user", "content": prompt}]
    feedback, replies, resumed, elapsed = None, 0, False, 0.0
    usage = {"cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "providers": set()}
    for line in (run_dir / "transcript.jsonl").read_text().splitlines():
        e = json.loads(line)
        elapsed = max(elapsed, e["t"])
        if e["kind"] == "rescue":
            resumed = True
        elif e["kind"] == "response":
            u = e["data"].get("usage") or {}
            usage["cost"] += float(u.get("cost") or 0)
            usage["prompt_tokens"] += u.get("prompt_tokens") or 0
            usage["completion_tokens"] += u.get("completion_tokens") or 0
            usage["reasoning_tokens"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            if e["data"].get("provider"):
                usage["providers"].add(e["data"]["provider"])
            if replies:
                messages.append({"role": "user", "content": feedback})
            msg = bench.assistant_turn(e["data"]["choices"][0]["message"])
            messages.append(msg)
            replies += 1
            feedback = NO_CODE if bench.extract_code(msg.get("content")) is None else None
        elif e["kind"] == "run":
            d = e["data"]
            if d["exit_code"] == 0 and not d["problems"]:
                raise SystemExit(f"{run_dir}: the program already ran cleanly")
            feedback = failure_feedback(d["exit_code"], d["stdout"], d["stderr"], d["problems"])
        elif e["kind"] == "error" and not resumed:
            raise SystemExit(f"{run_dir}: the run broke ({e['data']}); rerun it instead")
    if feedback is None:
        raise SystemExit(f"{run_dir}: the last reply has code that was never run")
    return messages, feedback, replies, usage, elapsed


def rescue(client, catalog, cfg, rec):
    run_dir = Path(rec["dir"])
    model, thinking = bench.parse_spec(rec["model"], catalog)
    info = catalog[model]
    args = SimpleNamespace(**{k: cfg[k] for k in ("image", "max_tokens", "temperature", "seed", "provider",
                                                  "run_timeout", "network")},
                           chat_repairs=REPAIRS, max_cost=MAX_COST)
    messages, feedback, replies, usage, elapsed = conversation(run_dir, cfg["prompt"])
    run = bench.Run(rec["model"], "chat", rec["run"], run_dir, thinking, turns=replies, **usage)
    run.t0 = time.monotonic() - elapsed
    run.log("rescue", {"repairs": REPAIRS, "max_cost": MAX_COST, "replies_before": replies})
    stop = "failed"
    try:
        with bench.Sandbox(args.image, run_dir / "work", args.network) as sb:
            for _ in range(replies, REPAIRS + 1):
                if run.cost >= args.max_cost:
                    stop = "max_cost"
                    break
                messages.append({"role": "user", "content": feedback})
                data = client.complete(bench.make_body(args, info, thinking, messages))
                run.account(data)
                msg = bench.assistant_turn(data["choices"][0]["message"])
                messages.append(msg)
                code = bench.extract_code(msg.get("content"))
                if code is None:
                    feedback = NO_CODE
                    continue
                rc, out, err, problems = bench.run_and_share(sb, code, args.run_timeout)
                run.log("run", {"exit_code": rc, "stdout": bench.clip(out), "stderr": bench.clip(err), "problems": problems})
                if rc == 0 and not problems:
                    stop = "finished"
                    break
                feedback = failure_feedback(rc, out, err, problems)
    except Exception as e:  # logged on the run and raised; the run is left as it was, to be finished by a rerun
        run.log("error", f"rescue: {type(e).__name__}: {e}")
        raise

    old = run_dir / "pre_rescue"
    old.mkdir()
    for name in ("grade.json", "repro", "render.json", "solo.mp3"):
        if (run_dir / name).exists():
            shutil.move(run_dir / name, old / name)
    report = bench.grade(args.image, run_dir / "work", run_dir / "repro")
    (run_dir / "grade.json").write_text(json.dumps(report, indent=2))
    mp3 = None
    if (report.get("checks") or {}).get("midi_parses", {}).get("value") == 1:
        rendered = bench.render(args.image, run_dir / "repro", run_dir)
        (run_dir / "render.json").write_text(json.dumps(rendered, indent=2))
        mp3 = str(run_dir / "solo.mp3")
    return {**rec, "score": report.get("score", 0.0), "stop": stop, "error": report.get("error"),
            "turns": run.turns, "cost": round(run.cost, 5), "prompt_tokens": run.prompt_tokens,
            "completion_tokens": run.completion_tokens, "reasoning_tokens": run.reasoning_tokens,
            "providers": sorted(run.providers), "seconds": round(time.monotonic() - run.t0, 1),
            "checks": {k: v["value"] for k, v in (report.get("checks") or {}).items()}, "mp3": mp3,
            "rescued": {"repairs": REPAIRS, "max_cost": MAX_COST, "turns_before": rec["turns"], "cost_before": rec["cost"],
                        "replies_before_this_pass": replies}}


def update(results, new):
    """Replace one run's line in its batch's results.jsonl, keeping the original file once."""
    with LOCK:
        keep = results.with_name("results.pre_rescue.jsonl")
        if not keep.exists():
            shutil.copyfile(results, keep)
        lines = [json.loads(x) for x in results.read_text().splitlines()]
        hit = [i for i, r in enumerate(lines) if r["dir"] == new["dir"]]
        if len(hit) != 1:
            raise SystemExit(f"{results}: {len(hit)} lines for {new['dir']}")
        lines[hit[0]] = new
        results.write_text("".join(json.dumps(r) + "\n" for r in lines))


def main():
    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("set OPENROUTER_API_KEY")
    client = bench.OpenRouter(key)
    catalog = client.models()
    jobs = []
    for results in sorted(RUNS.glob("*/*/results.jsonl")):
        cfg = json.loads((results.parent / "config.json").read_text())
        for line in results.read_text().splitlines():
            rec = json.loads(line)
            if rec["stop"] != "error" and rec["checks"].get("midi_parses") != 1 and "rescued" not in rec:
                jobs.append((results, cfg, rec))
    print(f"{len(jobs)} runs to finish", flush=True)
    broken = []
    with cf.ThreadPoolExecutor(5) as pool:
        futs = {pool.submit(rescue, client, catalog, cfg, rec): (results, rec) for results, cfg, rec in jobs}
        for f in cf.as_completed(futs):
            results, rec = futs[f]
            try:
                new = f.result()
            except Exception as e:
                broken.append(rec["dir"])
                print(f"{rec['model']:<42} #{rec['run']}  NOT FINISHED: {type(e).__name__}: {str(e)[:300]}", flush=True)
                continue
            update(results, new)
            before = new["rescued"]
            print(f"{new['model']:<42} #{new['run']}  {new['stop']:<9} midi {new['checks'].get('midi_parses')}  "
                  f"turns {before['turns_before']}->{new['turns']}  ${before['cost_before']:.2f}->${new['cost']:.2f}"
                  + (f"  [{new['error'][:100]}]" if new["error"] else ""), flush=True)
    if broken:
        raise SystemExit(f"{len(broken)} runs not finished; rerun to continue them: {broken}")


if __name__ == "__main__":
    main()
