#!/usr/bin/env python3
"""Serve the analysis pages on localhost so audio, seeking and the review tools work in any browser.

Serves only the pages (analysis/out, and the bracket review at /review/brackets.html) and the audio they play:
human_solos/, transcriptions/ and analysis/work/. Byte ranges are supported, which browsers need to seek inside audio.

usage: uv run python serve.py [port]   then open http://localhost:<port>/
"""
import http.server
import posixpath
import re
import sys
import urllib.parse
from pathlib import Path

from pipeline import HERE, HUMAN, OUT, TRANS, WORK

MOUNTS = {"human_solos": HUMAN, "transcriptions": TRANS, "work": WORK, "review": HERE / "review", "out": OUT}


class Handler(http.server.SimpleHTTPRequestHandler):
    range_left = None

    def translate_path(self, path):
        clean = posixpath.normpath(urllib.parse.unquote(urllib.parse.urlsplit(path).path))
        parts = [p for p in clean.split("/") if p not in ("", ".", "..")]
        if parts and parts[0] in MOUNTS:
            return str(MOUNTS[parts[0]].joinpath(*parts[1:]))
        return str(OUT.joinpath(*parts))

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        self.range_left = None
        rng = self.headers.get("Range")
        path = Path(self.translate_path(self.path))
        if not rng or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
        if not m or not (m[1] or m[2]):
            self.send_error(416, "unsupported range")
            return None
        start = int(m[1]) if m[1] else max(0, size - int(m[2]))
        end = min(int(m[2]), size - 1) if m[1] and m[2] else size - 1
        if start > end:
            self.send_error(416, "range outside the file")
            return None
        f = path.open("rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self.range_left = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        if self.range_left is None:
            return super().copyfile(source, outputfile)
        while self.range_left > 0:
            chunk = source.read(min(1 << 16, self.range_left))
            if not chunk:
                break
            outputfile.write(chunk)
            self.range_left -= len(chunk)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8793
    print(f"serving http://localhost:{port}/", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
