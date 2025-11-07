#!/usr/bin/env python3
"""
Scan playlist files, test URLs, and write a comprehensive report and a separate JSON file for a custom badge.
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

# CORRECTED: The ')' character has been removed from the negated set to allow it within URLs.
URL_RE = re.compile(r"https?://[^\s'\",>\]]+")
DEFAULT_TIMEOUT = 10  # seconds


def find_playlist_files(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for fn in filenames:
            if not fn.startswith("."):
                files.append(os.path.join(root, fn))
    return sorted(files)


def extract_urls_from_file(path):
    urls = set()
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
        with requests.head(url, allow_redirects=True, timeout=timeout, headers=headers) as r:
            if r.status_code < 400:
                return True, f"OK (HEAD: {r.status_code})"
        with requests.get(url, allow_redirects=True, timeout=timeout, headers=headers, stream=True) as r:
            if r.status_code < 400:
                return True, f"OK (GET: {r.status_code})"
            else:
                return False, f"HTTP {r.status_code} {r.reason}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection Error"
    except requests.exceptions.RequestException as e:
        return False, f"Request Error ({type(e).__name__})"
    except Exception as e:
        return False, f"Unexpected Error ({type(e).__name__})"


def main():
    parser = argparse.ArgumentParser(description="Test playlists and save a comprehensive summary report.")
    parser.add_argument("--dir", "-d", default="playlists", help="Directory containing playlist files")
    parser.add_argument("--output", "-o", required=True, help="Output summary report file path (.txt)")
    parser.add_argument("--badge-output", required=True, help="Output path for the badge JSON data")
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
    failing_streams = []
    for i, url in enumerate(unique_urls):
        is_working, reason = test_url(url, timeout=args.timeout)
        status = "WORKING" if is_working else "FAILED"
        if is_working:
            working_count += 1
        else:
            failing_streams.append((url, reason))
        print(f"[{i+1}/{total_urls}] {status} ({reason}): {url[:80]}{'...' if len(url) > 80 else ''}")
        time.sleep(0.1)

    failed_count
