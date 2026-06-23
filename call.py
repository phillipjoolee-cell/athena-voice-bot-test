"""
call.py — Trigger an outbound call via Vapi to the Athena test number.

Usage:
    python call.py
    python call.py scenarios/02_reschedule.txt   # optional: pick a different persona

This updates the assistant's system prompt right before dialing, so you can
swap personas without touching the Vapi dashboard.
"""

import os
import json
import csv
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

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
ASSISTANT_ID = require_env_var("ASSISTANT_ID")
PHONE_NUMBER_ID = require_env_var("PHONE_NUMBER_ID")
TARGET_NUMBER = require_env_var("TARGET_NUMBER")

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

LOG_PATH = Path("call_log.csv")
TRANSCRIPTS_DIR = Path("transcripts")


def log_call(scenario_file: str, call_id: str):
    is_new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["scenario_file", "call_id", "timestamp"])
        writer.writerow([scenario_file, call_id, time.strftime("%Y-%m-%d %H:%M:%S")])


def read_call_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, newline="") as f:
        return list(csv.DictReader(f))


def lookup_call(call_id: str) -> dict | None:
    matches = [row for row in read_call_log() if row["call_id"] == call_id]
    return matches[-1] if matches else None


def _find_basename_for_call_id(call_id: str) -> str | None:
    """Return existing transcript stem if this call was already saved."""
    if not TRANSCRIPTS_DIR.exists():
        return None
    for json_path in TRANSCRIPTS_DIR.glob("*.json"):
        try:
            with open(json_path) as f:
                data = json.load(f)
            if data.get("id") == call_id:
                return json_path.stem
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _next_available_basename(stem: str) -> str:
    """Pick stem, or stem_2, stem_3, ... based on existing .txt files."""
    if not (TRANSCRIPTS_DIR / f"{stem}.txt").exists():
        return stem
    n = 2
    while (TRANSCRIPTS_DIR / f"{stem}_{n}.txt").exists():
        n += 1
    return f"{stem}_{n}"


def transcript_basename(call_id: str) -> str:
    """Filename stem for transcript files, based on scenario name when available."""
    existing = _find_basename_for_call_id(call_id)
    if existing:
        return existing

    row = lookup_call(call_id)
    if not row:
        return call_id

    stem = Path(row["scenario_file"]).stem
    return _next_available_basename(stem)


def load_persona(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def update_assistant_prompt(system_prompt: str):
    """Push the chosen persona into the assistant's system message before calling."""
    url = f"{BASE_URL}/assistant/{ASSISTANT_ID}"
    payload = {
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "messages": [
                {"role": "system", "content": system_prompt}
            ],
        }
    }
    resp = requests.patch(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    print("Assistant persona updated.")


def trigger_call() -> str:
    """Start the outbound call. Returns the call ID."""
    url = f"{BASE_URL}/call"
    payload = {
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {"number": TARGET_NUMBER},
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()
    print(json.dumps(data, indent=2))
    return data["id"]


if __name__ == "__main__":
    import argparse
    from fetch_transcript import wait_and_fetch

    parser = argparse.ArgumentParser(description="Trigger a Vapi test call.")
    parser.add_argument(
        "persona",
        nargs="?",
        default="scenarios/01_basic_scheduling.txt",
        help="Path to scenario/persona file (default: scenarios/01_basic_scheduling.txt)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for the call to finish or fetch the transcript",
    )
    args = parser.parse_args()

    persona = load_persona(args.persona)
    print(f"Using persona: {args.persona}")
    update_assistant_prompt(persona)

    call_id = trigger_call()
    log_call(Path(args.persona).name, call_id)
    basename = transcript_basename(call_id)
    print(f"\nCall started. Call ID: {call_id}")

    if args.no_wait:
        print("Transcript will not be fetched automatically. Run later with:")
        print(f"  python fetch_transcript.py {call_id} --wait")
        print(f"  -> saves as transcripts/{basename}.txt")
    else:
        print(f"Waiting for call to finish, then saving as transcripts/{basename}.txt\n")
        wait_and_fetch(call_id)
