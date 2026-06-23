# Athena Voice Agent Test

Automated voice bot that calls Pretty Good AI's Athena test line, simulates
realistic patient scenarios, and records/transcribes the conversations for
bug-finding.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your real Vapi values:
   ```
   cp .env.example .env
   ```
   You need: `VAPI_API_KEY`, `ASSISTANT_ID`, `PHONE_NUMBER_ID` (all from the
   Vapi dashboard). `TARGET_NUMBER` is already filled in
   (+1-805-439-8008, the official Athena test line).

## Running a call

```
python3 call.py                                   # uses default persona (basic scheduling)
python3 call.py scenarios/02_reschedule.txt        # uses a different persona
```

This pushes the chosen persona into the Vapi assistant's system prompt,
starts an outbound call to the Athena test number, waits for the call to
finish, and automatically saves the transcript + raw call data under
`transcripts/`.

## Fetching a transcript manually

If you need to re-fetch a transcript for a call ID directly:

```
python3 fetch_transcript.py <call_id>
```

## Running all scenarios as a batch

```
python3 run_batch.py              # one call per scenario
python3 run_batch.py --repeat 2    # run everything twice (e.g. before/after a fix)
```

Logs every call ID + scenario to `call_log.csv`, with a pause between calls.
Recommended to test scenarios individually first before batching, so a
flawed scenario can be caught and fixed before burning multiple calls on it.

## Converting recordings to mp3

```
python3 convert_recordings.py
```

Reads the `recordingUrl` from each saved `transcripts/*.json` file,
downloads the `.wav`, converts to `.mp3` via ffmpeg, and saves into
`recordings/`. Requires ffmpeg installed locally (`brew install ffmpeg`).

## Scenarios

- `01_basic_scheduling.txt` — straightforward new appointment request
- `02_reschedule.txt` — patient changing an existing appointment, doesn't volunteer details
- `03_ambiguous_confused.txt` — scattered/uncertain caller, edge-case stress test
- `04_medication_refill.txt` — refill request, deliberately vague on medication name
- `05_hours_insurance.txt` — informational questions (hours, insurance), not booking
- `06_interruption_barge_in.txt` — interrupts the agent mid-response to test barge-in handling
- `07_self_correction.txt` — patient corrects themselves mid-call, tests whether the correction persists
- `08_stutter.txt` — simulated mild stutter/disfluent speech
- `09_contradictory_info.txt` — patient unknowingly states conflicting information
- `10_silence_pause.txt` — patient pauses/hesitates, tests turn-taking and silence handling
- `11_out_of_scope.txt` — patient asks for medical advice the agent shouldn't give
- `12_multiple_requests.txt` — two unrelated tasks (reschedule + refill) in one call
- `13_closed_hours.txt` — patient requests a weekend/off-hours appointment
- `14_proxy_caller.txt` — caller phoning on behalf of someone else, tests identity verification

## Deliverables in this repo

- `call.py`, `fetch_transcript.py`, `run_batch.py`, `convert_recordings.py` — working code
- `ARCHITECTURE.md` — system design and key decisions (1-2 paragraphs, per the brief)
- `BUG_REPORT.md` — consolidated findings from all test calls
- `transcripts/` — call transcripts (text + raw JSON)
- `recordings/` — call audio in mp3 format

**Supplementary process notes (not primary deliverables):**
`DECISION_LOG.md` and `FEEDBACK_LOG.md` are detailed, unfiltered working logs
kept throughout development — engineering decisions, dead ends, root-cause
diagnoses, and raw per-call bug critiques before being distilled into
`BUG_REPORT.md`. Included for transparency into the iteration process; the
primary writeups are `ARCHITECTURE.md` and `BUG_REPORT.md`.
