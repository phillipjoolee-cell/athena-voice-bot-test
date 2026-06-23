"""
convert_recordings.py — Download every call recording and convert to mp3.

Reads recordingUrl from each saved transcripts/*.json file, downloads the
.wav, converts it to .mp3 via ffmpeg, and saves into recordings/.

Usage:
    python3 convert_recordings.py

Requires ffmpeg installed locally (e.g. `brew install ffmpeg` on Mac).
"""

import json
import subprocess
import sys
from pathlib import Path

import requests

TRANSCRIPTS_DIR = Path("transcripts")
RECORDINGS_DIR = Path("recordings")


def find_recording_url(data: dict) -> str | None:
    """Recording URL can show up in a couple of places depending on Vapi's
    response shape — check the common spots."""
    if data.get("recordingUrl"):
        return data["recordingUrl"]
    artifact = data.get("artifact", {})
    if artifact.get("recordingUrl"):
        return artifact["recordingUrl"]
    return None


def download_wav(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"  Failed to download {url}: {e}")
        return False


def convert_to_mp3(wav_path: Path, mp3_path: Path) -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame",
             "-qscale:a", "2", str(mp3_path)],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ffmpeg failed for {wav_path}: {e.stderr.decode(errors='ignore')}")
        return False
    except FileNotFoundError:
        print("  ffmpeg not found. Install it first (e.g. `brew install ffmpeg`).")
        return False


def main():
    RECORDINGS_DIR.mkdir(exist_ok=True)
    json_files = sorted(TRANSCRIPTS_DIR.glob("*.json"))

    if not json_files:
        print(f"No .json files found in {TRANSCRIPTS_DIR}/")
        sys.exit(1)

    print(f"Found {len(json_files)} call records.\n")

    converted = 0
    skipped = 0
    failed = 0

    for json_path in json_files:
        base_name = json_path.stem  # e.g. "01_basic_scheduling"
        mp3_path = RECORDINGS_DIR / f"{base_name}.mp3"

        if mp3_path.exists():
            print(f"[skip] {base_name} — mp3 already exists")
            skipped += 1
            continue

        try:
            data = json.loads(json_path.read_text())
        except Exception as e:
            print(f"[fail] {base_name} — couldn't read json: {e}")
            failed += 1
            continue

        url = find_recording_url(data)
        if not url:
            print(f"[fail] {base_name} — no recordingUrl found in json")
            failed += 1
            continue

        wav_path = RECORDINGS_DIR / f"{base_name}.wav"
        print(f"[downloading] {base_name}...")
        if not download_wav(url, wav_path):
            failed += 1
            continue

        print(f"[converting]  {base_name}...")
        if convert_to_mp3(wav_path, mp3_path):
            wav_path.unlink()  # remove the intermediate wav, keep only mp3
            print(f"[done]        {base_name}.mp3\n")
            converted += 1
        else:
            failed += 1

    print(f"\nSummary: {converted} converted, {skipped} skipped (already done), {failed} failed.")
    print(f"Output folder: {RECORDINGS_DIR}/")


if __name__ == "__main__":
    main()
