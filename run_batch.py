"""
run_batch.py — Run through every scenario in scenarios/, one call at a time.

Usage:
    python run_batch.py
    python run_batch.py --repeat 2   # run each scenario twice (e.g. before/after a fix)

Waits for each call to finish and saves its transcript before moving on.
Pauses between calls so you don't dial back-to-back, and logs every call to
call_log.csv.

Recommended real workflow: run one call at a time at first, listen to it, fix
issues, THEN batch the rest once you trust the persona prompts.
"""

import sys
import time
import argparse
from pathlib import Path

from call import load_persona, update_assistant_prompt, trigger_call, log_call, LOG_PATH
from fetch_transcript import wait_and_fetch, transcript_basename

SCENARIOS_DIR = Path("scenarios")
PAUSE_BETWEEN_CALLS_SECONDS = 30  # avoid hammering the test line back-to-back


def main(repeat: int):
    scenario_files = sorted(SCENARIOS_DIR.glob("*.txt"))
    if not scenario_files:
        print(f"No scenario files found in {SCENARIOS_DIR}/")
        sys.exit(1)

    print(f"Found {len(scenario_files)} scenarios. Running {repeat}x each "
          f"= {len(scenario_files) * repeat} total calls.\n")

    for i in range(repeat):
        for scenario_path in scenario_files:
            print(f"--- Scenario: {scenario_path.name} (pass {i + 1}/{repeat}) ---")
            persona = load_persona(str(scenario_path))
            update_assistant_prompt(persona)

            call_id = trigger_call()
            log_call(scenario_path.name, call_id)
            basename = transcript_basename(call_id)
            print(f"Call triggered. ID: {call_id}")
            print(f"Waiting for call to finish -> transcripts/{basename}.txt\n")
            wait_and_fetch(call_id)

            print(f"Waiting {PAUSE_BETWEEN_CALLS_SECONDS}s before next call...\n")
            time.sleep(PAUSE_BETWEEN_CALLS_SECONDS)

    print(f"Done. All calls logged to {LOG_PATH} and transcripts saved under transcripts/.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=1,
                         help="How many times to run through all scenarios")
    args = parser.parse_args()
    main(args.repeat)
