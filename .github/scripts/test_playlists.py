#!/usr/bin/env python3
"""
Scan playlist files in a directory for http(s) URLs, test each URL,
and write a simple text summary report.

Usage:
  python .github/scripts/test_playlists.py --dir countries --output reports/summary.txt
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
    files = []
    for root, _, filenames in os.walk(directory):
        for fn in filenames:
            # Simple check for any text-based file, can be refined if needed
            if not fn.startswith("."):
                files.append(os.path.join(root, fn))
    return sorted(files)


def extract_urls_from_file(path):
    urls = set()  # Use a set for automatic deduplication
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip().startswith("#"):
                    for m in URL_RE.finditer(line):
                        urls.add(m.group(0))
    except Exception as e:
        return None, f"failed to read: {e}"
    return list(urls), None


def test_url(url, timeout=DEFAULT_TIMEOUT):
    headers = {"User-Agent": "iptv-ungeoblocked-playlist-tester/1.0 (+https://github.com/matte-oss/iptv-ungeoblocked)"}
    try:
        # Try HEAD first (faster when supported)
        with requests.head(url, allow_redirects=True, timeout=timeout, headers=headers) as r:
            if r.status_code < 400:
                return True
        # Fallback to GET if HEAD fails or is disallowed
        with requests.get(url, allow_redirects=True, timeout=timeout, headers=headers, stream=True) as r:
            return r.status_code < 400
    except requests.exceptions.RequestException:
        return False
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Test playlists and save a summary report.")
    parser.add_argument("--dir", "-d", default="playlists", help="Directory containing playlist files")
    parser.add_argument("--output", "-o", required=True, help="Output summary report file path (.txt)")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT, help="Timeout per request (s)")
    args = parser.parse_args()

    start_time = datetime.now(timezone.utc)

    if not os.path.isdir(args.dir):
        print(f"Playlist directory not found: {args.dir}", file=sys.stderr)
        return 1

    files = find_playlist_files(args.dir)
    print(f"Found {len(files)} files to scan in '{args.dir}'.")

    all_urls = set()
    for i, path in enumerate(files):
        print(f"[{i+1}/{len(files)}] Scanning: {path}")
        urls, err = extract_urls_from_file(path)
        if err:
            print(f"  -> Skipping file due to error: {err}")
            continue
        all_urls.update(urls)

    unique_urls = sorted(list(all_urls))
    total_urls = len(unique_urls)
    print(f"\nFound {total_urls} unique URLs to test.\n")

    working_count = 0
    for i, url in enumerate(unique_urls):
        status = "WORKING" if test_url(url, timeout=args.timeout) else "FAILED"
        if status == "WORKING":
            working_count += 1
        print(f"[{i+1}/{total_urls}] {status}: {url[:100]}{'...' if len(url) > 100 else ''}")
        time.sleep(0.1) # Small delay to be polite

    failed_count = total_urls - working_count
    success_rate = (working_count / total_urls) * 100 if total_urls > 0 else 0
    end_time = datetime.now(timezone.utc)
    duration_seconds = (end_time - start_time).total_seconds()

    summary_content = (
        f"Playlist Test Summary\n"
        f"---------------------\n"
        f"Test completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Total unique channels tested: {total_urls}\n"
        f"Working channels: {working_count}\n"
        f"Failing channels: {failed_count}\n"
        f"Success rate: {success_rate:.2f}%\n"
        f"Total test duration: {duration_seconds:.2f} seconds\n"
    )

    print("\n" + summary_content)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(summary_content)

    print(f"Summary report saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
