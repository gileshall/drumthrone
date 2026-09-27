#!/usr/bin/env python3
"""Build, check, preview and publish the public drumthrone site on GitHub Pages.

usage: uv run python deploy.py build     public copy of the site into analysis/site, then check it
       uv run python deploy.py serve     look at the built site on http://localhost:8794/
       uv run python deploy.py export    the replication repository into analysis/source, then check it
       uv run python deploy.py publish   check both, push one branch (main) to gileshall/drumthrone holding
                                         analysis/source with analysis/site in docs/, make the repository public, and
                                         serve docs/ with Pages

The public copy never holds the human recordings: their pages link to each recording's YouTube source. The replication
repository holds no audio, no keys and nothing that downloads the human recordings: its manifest lists their sources.
Neither holds a third-party image.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = HERE / "site"
SOURCE = HERE / "source"
BUNDLE = HERE / "publish"  # the one published branch: the replication repository plus the site in docs/
REPO = "gileshall/drumthrone"
URL = "https://gileshall.github.io/drumthrone/"
EMAIL = "giles@polymerase.org"
PORT = 8794
MAX_FILE = 100 * 1024 ** 2   # GitHub rejects larger files
MAX_SITE = 1024 ** 3         # GitHub Pages site limit
INTERNAL = ["Not analysed", "flagged", "by you", "Transcription check", "Set start", "Automatic is right",
            "bracket_overrides", "review/brackets", "hillclimb/", "pre_rescue", "/Users/", "image pending"]


HARNESS = ["prompt.md", "bench.py", "grader.py", "render.py", "Dockerfile", ".dockerignore", "compose.yaml"]
GITIGNORE = """.env
.venv/
__pycache__/
.DS_Store
assets/*.sf2
human_solos/*.mp3
transcriptions/
runs/**/solo.mp3
hillclimb/runs/**/solo.mp3
hillclimb/work/
analysis/out/
analysis/site/
analysis/publish/
analysis/work/
analysis/review/
analysis/images/
"""
DOWNLOADER = re.compile(r"yt[-_]dlp|youtube[-_]dl", re.I)  # the repository never ships a way to download the recordings
LEAKS = [re.compile(r"sk-or-[A-Za-z0-9-]{16,}"), re.compile(r"Bearer [A-Za-z0-9_-]{16,}"),
         re.compile(r"/keys/[0-9a-f]{16,}")]  # an OpenRouter key, a bearer token, a key's id in an API error


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def build():
    if SITE.exists():
        shutil.rmtree(SITE)
    env = {**os.environ, "DRUMTHRONE_SITE": str(SITE), "DRUMTHRONE_PUBLIC": "1"}
    run([sys.executable, HERE / "pipeline.py", "pages"], env=env)
    (SITE / ".nojekyll").write_text("")
    check()


def check():
    """Every link and audio path resolves inside the site; no human recording, no internal text, within size limits."""
    if not SITE.exists():
        raise SystemExit(f"{SITE} does not exist: run build first")
    root = SITE.resolve()
    problems = []
    files = [p for p in root.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    human = {p.name for p in (HERE.parent / "human_solos").glob("*.mp3")}
    for p in files:
        rel = p.relative_to(root)
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
            problems.append(f"{rel}: an image file (the site draws its own graphics; third-party images stay out)")
        if p.stat().st_size > MAX_FILE:
            problems.append(f"{rel}: larger than 100 MB")
        if p.suffix == ".mp3" and (p.name in human or rel.parts[0] != "audio"):
            problems.append(f"{rel}: audio that is not a generated solo")

    def resolves(page, ref):
        if re.match(r"^[a-z]+:", ref) or ref.startswith("//"):
            return
        target = (page.parent / ref).resolve()
        if target != root and root not in target.parents:
            problems.append(f"{page.relative_to(root)}: {ref} points outside the site")
        elif not target.exists():
            problems.append(f"{page.relative_to(root)}: {ref} is missing")

    pages = list(root.rglob("*.html"))
    for page in pages:
        text = page.read_text()
        problems += [f"{page.relative_to(root)}: contains '{w}'" for w in INTERNAL if w in text]
        if "drumthrone.goatcounter.com/count" not in text:
            problems.append(f"{page.relative_to(root)}: no visit counter")
        for ref in re.findall(r"""(?:src|href)=["']([^"'#?]+)""", text):
            resolves(page, ref)
        data = re.search(r"const DATA = (\{.*?\});</script>", text, re.S)
        if data:
            for node in json.loads(data[1])["nodes"]:
                resolves(page, node["page"])
                if node["audio"]:
                    resolves(page, node["audio"])
    if total > MAX_SITE:
        problems.append(f"the site is {total / 1e6:.0f} MB, over the 1 GB Pages limit")
    print(f"{len(pages)} pages, {len(files)} files, {total / 1e6:.0f} MB")
    if problems:
        for x in problems[:40]:
            print("  -", x)
        raise SystemExit(f"{len(problems)} problems: not publishable")
    print("checks passed")


def serve():
    check()
    print(f"serving {URL.replace('https://gileshall.github.io/drumthrone/', f'http://localhost:{PORT}/')}", flush=True)
    run([sys.executable, "-m", "http.server", PORT, "--bind", "127.0.0.1", "--directory", SITE])


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_batch(src, dst):
    """A bench.py batch without audio, and without runs the API refused before any generation (their only content is
    the refusal, which names the account's key)."""
    refused = set()
    for jl in src.glob("results*.jsonl"):
        keep = []
        for line in jl.read_text().splitlines():
            r = json.loads(line)
            if r["stop"] == "error" and r["cost"] == 0 and r["turns"] == 0:
                refused.add(Path(r["dir"]).resolve())
            else:
                keep.append(line)
        (dst / jl.name).parent.mkdir(parents=True, exist_ok=True)
        (dst / jl.name).write_text("".join(x + "\n" for x in keep))
    copy(src / "config.json", dst / "config.json")
    for run_dir in sorted(p for p in src.glob("*/*") if p.is_dir()):
        if run_dir.resolve() in refused:
            continue
        for f in run_dir.rglob("*"):
            if f.is_file() and f.suffix != ".mp3":
                copy(f, dst / f.relative_to(src))
    return len(refused)


def export():
    """The replication repository: harness and prompt, the experiment's runs, the hill-climb and thinking runs with
    their scores, the human recordings' sources and scored parts, and the analysis code."""
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    for f in HARNESS:
        copy(ROOT / f, SOURCE / f)
    for f in sorted(HERE.glob("*.py")) + [HERE / "pyproject.toml", HERE / "uv.lock"]:
        copy(f, SOURCE / "analysis" / f.name)
    copy(HERE / "repo" / "README.md", SOURCE / "README.md")
    copy(HERE / "repo" / "LICENSE", SOURCE / "LICENSE")
    (SOURCE / ".gitignore").write_text(GITIGNORE)
    (SOURCE / "assets").mkdir()
    (SOURCE / "assets" / ".gitkeep").write_text("")
    for f in ("manifest.tsv", "bracket_overrides.json"):
        copy(ROOT / "human_solos" / f, SOURCE / "human_solos" / f)
    prompt = (ROOT / "prompt.md").read_text().strip()
    refused = 0
    for batch in sorted((ROOT / "runs").iterdir()):
        cfg = batch / "config.json"
        if cfg.exists() and json.loads(cfg.read_text())["prompt"].strip() == prompt:  # the experiment's batches only
            refused += copy_batch(batch, SOURCE / "runs" / batch.name)
    for f in (ROOT / "hillclimb" / "prompts").glob("*.md"):
        copy(f, SOURCE / "hillclimb" / "prompts" / f.name)
    for batch in sorted((ROOT / "hillclimb" / "runs").glob("*/*")):
        refused += copy_batch(batch, SOURCE / "hillclimb" / "runs" / batch.parent.name / batch.name)
    results = [r for r in json.loads((ROOT / "hillclimb" / "results.json").read_text()) if not r["error"]]
    (SOURCE / "hillclimb" / "results.json").write_text(json.dumps(results, indent=1))
    print(f"left out {refused} runs the API refused before generating anything")
    check_source()


def read_env(path):
    """KEY=VALUE lines; the values are only compared, never printed."""
    out = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def check_source():
    """No audio, no images, no downloader, no keys or key names from .env values, nothing over GitHub's file limit."""
    if not SOURCE.exists():
        raise SystemExit(f"{SOURCE} does not exist: run export first")
    secrets = [v for v in read_env(ROOT / ".env").values() if len(v) >= 8]
    files = [p for p in SOURCE.rglob("*") if p.is_file()]
    problems = []
    for p in files:
        rel = p.relative_to(SOURCE)
        if p.suffix in (".mp3", ".wav", ".sf2", ".png", ".webp", ".jpg", ".gif") or p.name == ".env":
            problems.append(f"{rel}: must not be published")
        if p.stat().st_size > MAX_FILE:
            problems.append(f"{rel}: larger than 100 MB")
        text = p.read_bytes().decode("utf-8", "replace")
        problems += [f"{rel}: contains something shaped like a key ({w.pattern})" for w in LEAKS if w.search(text)]
        if DOWNLOADER.search(text):
            problems.append(f"{rel}: mentions a video downloader")
        if any(v in text for v in secrets):
            problems.append(f"{rel}: contains a value from .env")
    total = sum(p.stat().st_size for p in files)
    print(f"{len(files)} files, {total / 1e6:.0f} MB")
    if problems:
        for x in problems[:40]:
            print("  -", x)
        raise SystemExit(f"{len(problems)} problems: not publishable")
    print("source checks passed")


def push(folder, branch, message, name):
    """Force-push a folder as the only commit on a branch, with gh's login for this push only."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(folder, work)
        git = ["git", "-C", work]
        run(git + ["init", "-q", "-b", branch])
        # the machine's own global ignore rules must not decide what gets published
        run(git + ["-c", "core.excludesFile=/dev/null", "add", "-A"])
        tracked = run(git + ["ls-files"], capture_output=True, text=True).stdout.splitlines()
        files = [p for p in work.rglob("*") if p.is_file() and ".git" not in p.relative_to(work).parts]
        if len(tracked) != len(files):
            missing = sorted({str(p.relative_to(work)) for p in files} - set(tracked))
            raise SystemExit(f"{len(files) - len(tracked)} files would not be committed, e.g. {missing[:5]}")
        run(git + ["-c", f"user.name={name}", "-c", f"user.email={EMAIL}", "commit", "-q", "-m", message])
        run(git + ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
                   "push", "-q", "--force", f"https://github.com/{REPO}.git", branch])


def bundle():
    """The replication repository with the checked site copied into docs/."""
    check()
    check_source()
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    shutil.copytree(SOURCE, BUNDLE)
    shutil.copytree(SITE, BUNDLE / "docs")
    files = [p for p in BUNDLE.rglob("*") if p.is_file()]
    print(f"bundle: {len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.0f} MB")


def publish():
    bundle()
    description = "Drum Throne: An experimental benchmark composing drum solos with language models"
    if subprocess.run(["gh", "repo", "view", REPO], capture_output=True).returncode:
        run(["gh", "repo", "create", REPO, "--public", "--description", description])
    else:
        run(["gh", "repo", "edit", REPO, "--visibility", "public", "--accept-visibility-change-consequences",
             "--description", description])
    name = run(["gh", "api", "user", "--jq", ".name"], capture_output=True, text=True).stdout.strip()
    if not name:
        raise SystemExit("the GitHub profile has no name to author the commit with")
    push(BUNDLE, "main", "Drum Throne", name)
    others = run(["gh", "api", f"repos/{REPO}/branches", "--jq", ".[].name"], capture_output=True, text=True).stdout.split()
    if others != ["main"]:
        raise SystemExit(f"the repository has branches besides main: {others}")
    if subprocess.run(["gh", "api", f"repos/{REPO}/pages"], capture_output=True).returncode:
        run(["gh", "api", "-X", "POST", f"repos/{REPO}/pages", "-f", "source[branch]=main", "-f", "source[path]=/docs"])
    else:
        run(["gh", "api", "-X", "PUT", f"repos/{REPO}/pages", "-f", "source[branch]=main", "-f", "source[path]=/docs"])
    print(f"published: {URL} (Pages can take a minute or two to update)")


if __name__ == "__main__":
    commands = {"build": build, "check": check, "serve": serve, "export": export, "bundle": bundle, "publish": publish}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        raise SystemExit(__doc__)
    commands[sys.argv[1]]()
