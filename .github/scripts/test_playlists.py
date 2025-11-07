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

# --- THIS IS THE CORRECTED REGEX ---
# It now correctly handles URLs containing parentheses and square brackets.
URL_RE = re.compile(r"https?://[^\s\"',<>]+")
# --- END OF CORRECTION ---

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
                    # The finditer will now correctly parse URLs with parentheses
                    for m in URL_RE.finditer(line):
                        urls.add(m.group(0))
    except Exception as e:
        return None, f"failed to read: {e}"
    return list(urls), None


def test_url(url, timeout=DEFAULT_TIMEOUT):
    """
    Tests a URL and returns a tuple: (is_ok: bool, reason: str).
    It tries a HEAD request first and falls back to a GET request if needed.
    """
    headers = {"User-Agent": "iptv-ungeoblocked-playlist-tester/1.0 (+https://github.com/matte-oss/iptv-ungeoblocked)"}
    
    try:
        with requests.head(url, allow_redirects=True, timeout=timeout, headers=headers) as r:
            if r.status_code < 400:
                return True, f"OK (HEAD: {r.status_code})"
    except requests.exceptions.RequestException:
        pass # Ignore HEAD exceptions and fall through to GET

    try:
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
    if total_urls == 0:
        print("No URLs found. Exiting.")
        # Create empty reports if no URLs are found
        summary_content = "No URLs found to test."
        badge_data = {"schemaVersion": 1, "label": "channels", "message": "0/0 working", "color": "lightgrey"}
        with open(args.output, "w", encoding="utf-8") as f: f.write(summary_content)
        with open(args.badge_output, "w", encoding="utf-8") as f: json.dump(badge_data, f, indent=2)
        return 0

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

    failed_count = total_urls - working_count
    success_rate = (working_count / total_urls) * 100
    end_time = datetime.now(timezone.utc)
    duration_seconds = (end_time - start_time).total_seconds()

    summary_content = (
        f"Playlist Test Summary\n---------------------\n"
        f"Test completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Total unique channels tested: {total_urls}\n"
        f"Working channels: {working_count}\n"
        f"Failing channels: {failed_count}\n"
        f"Success rate: {success_rate:.2f}%\n"
        f"Total test duration: {duration_seconds:.2f} seconds\n"
    )
    if failing_streams:
        failing_list_content = "\n\nFailing Channels List (with Debug Info)\n----------------------------------------\n"
        failing_list_content += "\n".join([f"{url}  --  [{reason}]" for url, reason in failing_streams])
        summary_content += failing_list_content

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(summary_content)

    if success_rate >= 90: color = "success"
    elif success_rate >= 70: color = "yellow"
    else: color = "critical"
    
    badge_data = {
        "schemaVersion": 1, "label": "channels",
        "message": f"{working_count}/{total_urls} working", "color": color
    }
    with open(args.badge_output, "w", encoding="utf-8") as f:
        json.dump(badge_data, f, indent=2)

    print("\n--- Report Summary ---")
    print(summary_content.split('\n\n')[0])
    print("----------------------")
    print(f"Comprehensive report saved to {args.output}")
    print(f"Badge data saved to {args.badge_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
