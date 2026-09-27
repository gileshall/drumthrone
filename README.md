# Drum Throne

An experimental benchmark for composing drum solos with language models. Each model writes a Python program that
writes a two-minute drum solo as MIDI, played on a General MIDI kit; the solos are measured against 20 recorded human
solos, and the score is then used to study thinking settings and to hill climb the prompt. This repository holds
everything behind [the write-up](https://gileshall.github.io/drumthrone/): the benchmark harness, every generated
program with its MIDI, the hill-climb and thinking runs, and the code that measures and scores the solos.

Take the scores with a grain of salt. They are an ad hoc approximation built from things that can be measured
(complexity, dynamics, timing, structure), not a calibrated judge of drum solos.
[How it works](https://gileshall.github.io/drumthrone/how.html) explains every measurement and its weak spots.

## Layout

| path | what |
|---|---|
| `prompt.md` | the benchmark prompt |
| `bench.py`, `grader.py`, `render.py`, `Dockerfile`, `compose.yaml` | the harness: sends the prompt to models through OpenRouter, runs each program alone in a sandbox, grades and renders the MIDI |
| `runs/` | the main set: one run per model and thinking setting, with the program, its MIDI, the grade and the full transcript |
| `hillclimb/prompts/` | the prompts of the hill climb: `p0` is the benchmark prompt and `p6` the final one; `t6` is `p6`, used for the thinking runs |
| `hillclimb/runs/` | the hill-climb runs (`p0` to `p6`) and the thinking runs (`t6`) |
| `hillclimb/results.json` | score and measurements of every hill-climb and thinking run |
| `human_solos/manifest.tsv` | the 20 human recordings and their sources; `bracket_overrides.json` holds the scored parts set by listening |
| `analysis/` | measurement, scoring, hill-climb and site code (a [uv](https://docs.astral.sh/uv/) project) |
| `docs/` | the built site, served by GitHub Pages |

## Replicate

Needs Docker, [uv](https://docs.astral.sh/uv/) and ffmpeg, and the 20 human recordings. They are not included.
`human_solos/manifest.tsv` lists where each one comes from. Save each one as an MP3 in `human_solos/` under its file name
from the manifest.

```bash
git clone https://github.com/gileshall/drumthrone && cd drumthrone
docker build -t drumbench .                        # sandbox, grader and renderer
docker run --rm drumbench cat /usr/share/sounds/sf2/FluidR3_GM.sf2 > assets/FluidR3_GM.sf2
cd analysis
uv run python pipeline.py render transcribe bracket features validate score   # the main set and the human solos
uv run python hillclimb.py render                  # render the hill-climb and thinking runs
uv run python hillclimb.py score                   # transcribe, measure and score them
uv run python samekit.py                           # the human solos rebuilt and played on the General MIDI kit
uv run python pipeline.py pages                    # the site, in analysis/out
uv run python serve.py                             # look at it on http://localhost:8793/
```

Transcription uses [MuScriptor](https://muscriptor.kyutai.org), fetched by `uvx` on first use.

New runs need an OpenRouter key. Put `OPENROUTER_API_KEY`, `HOST_UID` and `HOST_GID` (your `id -u` and `id -g`) in
`.env`, then:

```bash
docker compose build
docker compose run --rm bench anthropic/claude-opus-5.5@high --mode chat --runs 1 --chat-repairs 2 --max-cost 50
```

`analysis/hillclimb.py gen` runs `bench.py` directly with the project's own virtual environment:

```bash
uv venv && uv pip install "httpx>=0.27,<1"
cd analysis && uv run python hillclimb.py gen ../hillclimb/prompts/p6.md mytag 4 google/gemini-3.1-pro-preview@low
```

## Notes

- The human recordings are not included; they belong to their owners. `human_solos/manifest.tsv` lists each one's
  source and `bracket_overrides.json` the parts scored by listening. A recording from another source or encoding can
  move the human numbers slightly.
- The main set was run with `--chat-repairs 2`: a reply without a program, or a program that fails, goes back to the
  model up to two times. Hill-climb and thinking runs that ended without a MIDI file were continued the same way in
  their original conversations (`analysis/rescue.py`); their first grade is kept in `pre_rescue/`.
- The main set's `openai/gpt-chat-latest` run is left out of the analysis: the alias records no model version, so its
  solo can't be attributed to a model.
- 29 requests were refused by the API before any generation (28 in the thinking runs, for a credit limit, and one in
  the main set, for an account setting) and were rerun. They are not included.
- In the thinking runs, OpenRouter served DeepSeek's `high` and `max` settings from two upstream providers; the runs
  record which (`providers` in `results.jsonl`).

## License

Copyright (c) 2026 Giles Hall. The code is released under the [MIT License](LICENSE). The human recordings belong to
their owners and are not covered by it. The GitHub corner on the site is Tim Holman's
[GitHub Corners](https://github.com/tholman/github-corners) (MIT).
