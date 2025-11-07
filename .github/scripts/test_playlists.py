#!/usr/bin/env python3
"""
Scan playlist files in a directory for http(s) URLs, test each URL (HEAD then GET fallback),
and write a JSON report describing results.

Usage:
  python .github/scripts/test_playlists.py --dir playlists --output reports/playlist-test-20251107.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

URL_RE = re.compile(r"https?://[^\s'\",)>\]]+")

DEFAULT_TIMEOUT = 10  # seconds


def find_playlist_files(directory):
    exts = {".m3u", ".m3u8", ".txt", ".pls"}
    files = []
    for root, _, filenames in os.walk(directory):
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in exts or True:
                # include all files but prefer known extensions
                files.append(os.path.join(root, fn))
    return sorted(files)


def extract_urls_from_file(path):
    urls = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for m in URL_RE.finditer(line):
                    urls.append(m.group(0))
    except Exception as e:
        return {"error": f"failed to read: {e}", "urls": []}
    return {"error": None, "urls": urls}


def test_url(url, timeout=DEFAULT_TIMEOUT):
    out = {
        "url": url,
        "ok": False,
        "status_code": None,
        "reason": None,
        "elapsed_ms": None,
        "content_length": None,
        "error": None,
        "tested_with": None,
        "final_url": None,
    }
    headers = {"User-Agent": "iptv-ungeoblocked-playlist-tester/1.0 (+https://github.com/matte-oss/iptv-ungeoblocked)"}
    try:
        start = time.time()
        # Try HEAD first (faster when supported)
        try:
            r = requests.head(url, allow_redirects=True, timeout=timeout, headers=headers)
            out["tested_with"] = "HEAD"
        except Exception:
            r = None

        if r is None or r.status_code >= 400:
            # fallback to GET
            start = time.time()
            r = requests.get(url, allow_redirects=True, timeout=timeout, headers=headers, stream=True)
            out["tested_with"] = "GET"

        elapsed = (time.time() - start) * 1000.0
        out["elapsed_ms"] = int(elapsed)
        out["status_code"] = getattr(r, "status_code", None)
        out["reason"] = getattr(r, "reason", None)
        out["final_url"] = getattr(r, "url", None)
        out["ok"] = r is not None and r.status_code < 400

        # try to determine content length if GET returned headers
        try:
            cl = r.headers.get("Content-Length")
            if cl:
                out["content_length"] = int(cl)
            else:
                # if no content-length header, try reading small chunk to estimate
                if out["tested_with"] == "GET":
                    chunk = next(r.iter_content(1024), b"")
                    out["content_length"] = len(chunk)
        except Exception:
            pass

    except requests.exceptions.RequestException as e:
        out["error"] = str(e)
    except Exception as e:
        out["error"] = f"unexpected: {e}"
    finally:
        try:
            if "r" in locals() and hasattr(r, "close"):
                r.close()
        except Exception:
            pass
    return out


def main():
    parser = argparse.ArgumentParser(description="Test playlists and save report.")
    parser.add_argument("--dir", "-d", default="playlists", help="Directory containing playlist files")
    parser.add_argument("--output", "-o", required=True, help="Output report file path (JSON)")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT, help="Timeout per request (s)")
    args = parser.parse_args()

    playlist_dir = args.dir
    output_path = args.output
    timeout = args.timeout

    run_at = datetime.now(timezone.utc).isoformat()

    report = {
        "run_at": run_at,
        "playlist_dir": playlist_dir,
        "git_commit": None,
        "results": [],
    }

    # try to get current commit sha if available
    try:
        import subprocess

        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).strip().decode()
        report["git_commit"] = sha
    except Exception:
        report["git_commit"] = None

    if not os.path.isdir(playlist_dir):
        print(f"Playlist directory not found: {playlist_dir}", file=sys.stderr)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as outf:
            json.dump({**report, "error": f"playlist directory not found: {playlist_dir}"}, outf, ensure_ascii=False, indent=2)
        print(f"Wrote report to {output_path}")
        return 0

    files = find_playlist_files(playlist_dir)
    if not files:
        print(f"No files found in {playlist_dir}", file=sys.stderr)

    for path in files:
        entry = {"playlist_file": path, "scanned_at": datetime.now(timezone.utc).isoformat(), "urls": [], "file_error": None}
        extract = extract_urls_from_file(path)
        if extract.get("error"):
            entry["file_error"] = extract["error"]
            report["results"].append(entry)
            continue

        urls = extract.get("urls", [])
        # keep unique and preserve order
        seen = set()
        uniq_urls = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                uniq_urls.append(u)

        for url in uniq_urls:
            if not urlparse(url).scheme.startswith("http"):
                continue
            res = test_url(url, timeout=timeout)
            entry["urls"].append(res)
            # small sleep to avoid hammering (tweakable)
            time.sleep(0.1)

        report["results"].append(entry)

    # Ensure parent dir exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as outf:
        json.dump(report, outf, ensure_ascii=False, indent=2)

    print(f"Wrote report to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
