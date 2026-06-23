# Architecture

<!--
Fill this in yourself once the system is actually running — the brief explicitly
evaluates whether you can explain your own design choices, not whether this reads
well. Keep it to 1-2 paragraphs total, per the brief. Bracketed notes below are
prompts for you, delete them once filled in.
-->

## How it works

[1 paragraph: the actual pipeline. Something like — "A Python script (call.py) triggers
an outbound call via Vapi's REST API, which dials Athena's test line
(+1-805-439-8008) and connects it to a Vapi-hosted assistant. The assistant runs on
[STT provider], Claude Sonnet [version] as the LLM, and [TTS provider] for voice
synthesis, all orchestrated by Vapi. Each assistant run uses a persona prompt loaded
from scenarios/, describing a specific patient scenario (scheduling, refill, edge
case, etc.). After the call ends, fetch_transcript.py pulls the transcript and
recording via Vapi's API and saves them locally."]

## Why these choices

[1 paragraph: the reasoning, written honestly — e.g. why Vapi over Retell/Bland,
why Claude as the LLM, why a static prompt library instead of a dynamic
scenario generator, what tradeoff you accepted given the 6-12 hour window.
This is the part that's actually graded — be specific about what you decided
NOT to build and why, not just what you did build.]
