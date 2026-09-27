# Sandbox shared by every model, and by the grader.
#   docker build -t drumbench .
FROM python:3.11-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends fluidsynth fluid-soundfont-gm ffmpeg \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "mido>=1.3,<2"

WORKDIR /work
