# Architecture

## How it works

A Python script (`call.py`) triggers an outbound call via Vapi's REST API,
which dials Athena's test line (+1-805-439-8008) using a Vapi-provisioned
phone number and connects it to a Vapi-hosted assistant running Claude
Sonnet as the LLM, with Deepgram for transcription and a standard TTS voice
for synthesis — all orchestrated by Vapi's voice pipeline. Each call loads
a persona prompt from a `.txt` file in `scenarios/` (14 total, covering
scheduling, rescheduling, refills, hours/insurance questions, ambiguous
requests, interruptions, self-correction, disfluent speech, contradictory
information, silence/pauses, out-of-scope medical questions, multi-task
calls, closed-hours requests, and proxy callers) and PATCHes it into the
assistant's system prompt immediately before dialing, so scenarios can be
swapped without touching code or the Vapi dashboard. After each call ends,
`fetch_transcript.py` pulls the transcript and recording via Vapi's API,
and `convert_recordings.py` batch-converts the saved `.wav` recordings to
`.mp3`. A `run_batch.py` script can run every scenario sequentially with a
pause between calls, though most calls in this submission were run
individually so each transcript could be reviewed before continuing — this
caught several scenario design issues mid-run rather than after a blind
batch.

## Why these choices

Vapi was chosen over Retell AI and Bland AI because it allows bringing
Claude directly as the LLM rather than being locked into a vendor default,
and treats outbound calling as a first-class use case rather than an
afterthought. A Vapi-provisioned number hit a daily outbound call limit
partway through testing; importing a Twilio number was attempted to remove
the constraint, but Twilio required upgrading to a paid account before it
would place calls to an unverified number, which would have added
meaningful setup time. Rather than completing that upgrade, the pragmatic
choice was to spin up additional Vapi accounts to keep testing moving — not
the textbook-correct production fix, but the faster path to a finished
deliverable given time constraints. Persona prompts are
deliberately kept as plain text files rather than structured config, since
the actual point of this assignment was scenario design and bug-finding,
not engineering a more elaborate test harness — this kept iteration fast
when a scenario turned out to be flawed (e.g. an early scenario asked the
patient to request a medication an orthopedic clinic would never plausibly
prescribe, causing the test-bot to correctly abandon the call; the fix was
correcting the scenario's premise, not constraining the LLM further). One
scenario (genuine mid-sentence interruption/barge-in) was ultimately left
as a documented limitation rather than fully solved: the test-bot only has
access to Athena's finalized transcribed text, never her live audio stream,
so it has no mechanism to inject a response while she's still mid-sentence
— a real fix would require lower-level access to the voice pipeline's audio
timing, which was out of scope for this test harness.
