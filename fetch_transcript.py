"""
fetch_transcript.py — Pull the transcript + recording URL for a finished call.

Usage:
    python fetch_transcript.py <call_id>              # fetch now
    python fetch_transcript.py <call_id> --wait       # poll until call ends, then save
    python fetch_transcript.py --all                  # fetch any missing from call_log.csv
    python fetch_transcript.py --all --wait           # poll for in-progress calls too

Saves the transcript as a .json and .txt file under transcripts/.
Filenames use the scenario name from call_log.csv when available.
"""

import os
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

from call import read_call_log, transcript_basename

load_dotenv()


def require_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            "Please add it to your .env file or export it in your shell."
        )
    return value

VAPI_API_KEY = require_env_var("VAPI_API_KEY")
BASE_URL = "https://api.vapi.ai"
HEADERS = {"Authorization": f"Bearer {VAPI_API_KEY}"}

TERMINAL_STATUSES = {"ended"}
DEFAULT_POLL_INTERVAL = 15
DEFAULT_TIMEOUT = 900

# Retry settings for transient network/server failures
DEFAULT_FETCH_RETRIES = 3
DEFAULT_FETCH_RETRY_BACKOFF = 2  # base seconds, exponential backoff


def fetch_call(call_id: str, retries: int = DEFAULT_FETCH_RETRIES, backoff: int = DEFAULT_FETCH_RETRY_BACKOFF) -> dict:
    """Fetch call data with simple retry/backoff for transient failures.

    Retries on network errors and on 5xx responses up to `retries` times.
    """
    url = f"{BASE_URL}/call/{call_id}"
    attempt = 0
    while True:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            # Treat 5xx as transient server errors we can retry
            if resp.status_code >= 500 and attempt < retries:
                attempt += 1
                sleep_for = backoff * (2 ** (attempt - 1))
                print(f"Transient server error ({resp.status_code}). Retry {attempt}/{retries} in {sleep_for}s...")
                time.sleep(sleep_for)
                continue

            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt < retries:
                attempt += 1
                sleep_for = backoff * (2 ** (attempt - 1))
                print(f"Request failed: {exc}. Retry {attempt}/{retries} in {sleep_for}s...")
                time.sleep(sleep_for)
                continue
            raise


def is_call_finished(data: dict) -> bool:
    return data.get("status") in TERMINAL_STATUSES or data.get("endedAt") is not None


def transcript_path(call_id: str, ext: str) -> Path:
    return Path("transcripts") / f"{transcript_basename(call_id)}{ext}"


def transcript_saved(call_id: str) -> bool:
    return transcript_path(call_id, ".txt").exists()


def save_outputs(call_id: str, data: dict):
    os.makedirs("transcripts", exist_ok=True)

    basename = transcript_basename(call_id)
    raw_path = transcript_path(call_id, ".json")
    with open(raw_path, "w") as f:
        json.dump(data, f, indent=2)

    transcript_text = data.get("transcript", "")
    txt_path = transcript_path(call_id, ".txt")
    with open(txt_path, "w") as f:
        f.write(transcript_text)

    recording_url = data.get("recordingUrl") or data.get("artifact", {}).get("recordingUrl")

    print(f"Status: {data.get('status')}, ended reason: {data.get('endedReason')}")
    print(f"Saved raw call data -> {raw_path}")
    print(f"Saved transcript     -> {txt_path}")
    if recording_url:
        print(f"Recording URL         -> {recording_url}")
    else:
        print("No recording URL found yet — call may still be in progress.")


def wait_and_fetch(
    call_id: str,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Poll until the call finishes, then save transcript files."""
    if transcript_saved(call_id):
        basename = transcript_basename(call_id)
        print(f"Transcript already saved for {basename}. Skipping.")
        return fetch_call(call_id)

    print(f"Waiting for call to finish ({call_id})...")
    start = time.time()
    while True:
        data = fetch_call(call_id)
        if is_call_finished(data):
            save_outputs(call_id, data)
            return data

        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            raise TimeoutError(
                f"Call {call_id} did not finish within {timeout}s "
                f"(status: {data.get('status')})"
            )

        print(
            f"  Still in progress (status: {data.get('status')}, "
            f"{elapsed}s elapsed). Checking again in {poll_interval}s..."
        )
        time.sleep(poll_interval)


def fetch_one(call_id: str, wait: bool = False) -> dict | None:
    if wait:
        return wait_and_fetch(call_id)

    data = fetch_call(call_id)
    if not is_call_finished(data):
        print(
            f"Call not finished yet (status: {data.get('status')}). "
            f"Re-run with --wait to poll automatically."
        )
        return data

    save_outputs(call_id, data)
    return data


def fetch_all_pending(wait: bool = False):
    rows = read_call_log()
    if not rows:
        print("No calls found in call_log.csv.")
        return

    for row in rows:
        call_id = row["call_id"]
        basename = transcript_basename(call_id)
        if transcript_saved(call_id):
            print(f"Skipping {basename} — already saved.")
            continue

        print(f"\n--- {basename} ({call_id}) ---")
        if wait:
            wait_and_fetch(call_id)
        else:
            fetch_one(call_id, wait=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Vapi call transcripts.")
    parser.add_argument("call_id", nargs="?", help="Call ID to fetch")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all calls from call_log.csv that do not have transcripts yet",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll until the call finishes before saving",
    )
    args = parser.parse_args()

    if args.all:
        fetch_all_pending(wait=args.wait)
    elif args.call_id:
        fetch_one(args.call_id, wait=args.wait)
    else:
        parser.print_help()
        sys.exit(1)
