# Decision & Progress Log

Tracks key decisions, issues encountered, and how they were resolved throughout
the build — separate from FEEDBACK_LOG.md (which tracks bug findings from
Athena's responses specifically). Useful raw material for the architecture doc
and Loom walkthrough.

---

## Platform selection

**Decision:** Chose Vapi over Retell AI and Bland AI.
**Reasoning:** Vapi allows bringing your own LLM (used Claude rather than a
default model), is built developer-first with outbound calling as a
first-class use case (unlike Bland, where inbound is the focus and outbound
feels secondary), and its $10 trial credit was expected to comfortably cover
testing volume for this assignment. Retell was considered as a backup for
lower latency out of the box, but Vapi's flexibility around model choice
was the deciding factor.

---

## Initial setup

- Created Vapi account, assistant, and a Vapi-provisioned outbound phone number.
- Confirmed assistant model provider set to Anthropic/Claude, voice provider
  and transcriber configured via dashboard.
- Built local project (`call.py`, `fetch_transcript.py`, `run_batch.py`,
  `.env`/`.env.example`, `requirements.txt`) to trigger calls and pull
  transcripts/recordings via Vapi's API.

**Issue caught early:** Initial target number used during setup
(+1 930-239-2737) did not match the official test number specified in the
challenge brief (+1-805-439-8008). Caught before any real test calls were
made — corrected `TARGET_NUMBER` in `.env`/`.env.example` to the correct
number before proceeding. Important catch since calling the wrong number
would have wasted budget and potentially called an unintended real line.

---

## System prompt / persona design

- Built persona prompts as separate `.txt` files per scenario in `scenarios/`,
  loaded dynamically by `call.py` and pushed into the assistant's system
  prompt via Vapi's PATCH endpoint right before each call — rather than
  hardcoding one static prompt or managing personas only through the
  dashboard. This allows swapping test scenarios without touching code or
  the dashboard UI.
- Designed personas to avoid the "robotic patient" failure mode — explicit
  rules against over-explaining or repeating the full request like a
  script, since early thinking about this (before any real calls) flagged
  that LLM-played callers tend to over-volunteer information in ways real
  patients don't.

---

## Engineering decision: CSV call logging

**Issue:** Originally only `run_batch.py` logged triggered calls (scenario +
call ID + timestamp) to `call_log.csv`. `call.py` (used for manual one-at-a-
time runs) did not, making it hard to track which call ID corresponded to
which scenario when running calls individually.

**Process:** Asked Cursor to add the same logging to `call.py`. Cursor
proposed duplicating the `log_call()` function in both files, but flagged
this would cause drift risk (format changes would need to be applied in two
places). Asked Cursor to apply a DRY refactor instead: moved `log_call()`
and `LOG_PATH` into `call.py` as the single shared implementation, with
`run_batch.py` importing from `call.py` instead of duplicating the logic.
Verified the change by triggering a real call and checking `call_log.csv`
output before proceeding.

**This is a concrete example of iterative AI-assisted debugging**: identified
a need → had Cursor propose a plan → caught a code-quality issue in that
plan (duplication) → directed a specific refactor → verified the result
actually worked before moving on, rather than accepting the first answer.

---

## Scenario design correction: medication mismatch (scenario 04)

**Issue:** First run of `04_medication_refill.txt` had the test-bot patient
abandon the scenario's premise entirely, improvising a "wrong number,
trying to reach primary care" framing instead of requesting the scripted
blood pressure medication refill.

**Diagnosis:** Initially assumed this was an LLM "drift" problem (the bot
not following its prompt). On closer inspection, recognized it was actually
a flaw in the scenario's own design: the target clinic (Pivot Point
Orthopedics) has no plausible reason to manage a blood pressure
prescription. The LLM playing the patient was being MORE logically
consistent than the scenario itself, not less.

**Fix:** Changed the medication in the scenario to an orthopedics-
appropriate anti-inflammatory for knee pain (consistent with what had
already come up organically in other calls — e.g. meloxicam), rather than
just adding a generic "stay on topic" instruction to force compliance with
a premise that didn't actually make sense. Re-ran the scenario afterward and
confirmed it now tested medication refill behavior as intended.

**Why this matters for the writeup:** This is a good example of diagnosing
root cause rather than patching a symptom — the first instinct (constrain
the LLM harder) would have masked a real design flaw rather than fixing it.

---

## Scenario design correction: contradiction timing (scenario 09)

**Issue:** Two failed attempts at testing scenario 09
(contradictory-info). First attempt: test-bot violated its own
instructions and self-flagged the contradiction instead of letting Athena
catch it. Second attempt: test-bot followed instructions correctly, but the
call got cut short by an unrelated Athena bug (duplicate-appointment-block
+ failed transfer) before the conversation reached the point where the
contradiction would naturally surface — the scenario was written to
introduce the contradiction "partway through," dependent on insurance/
booking details coming up later in a normal flow.

**Diagnosis:** The scenario's design assumed the call would reliably reach
a certain conversational depth before the test condition occurred — a risky
assumption once it became clear Athena has a high-frequency bug
(duplicate-appointment-block) that can end calls early and unpredictably.

**Fix:** Restructured the scenario to front-load the contradiction into the
patient's first 2-3 responses, rather than waiting for it to occur
naturally later in the conversation — removes dependency on the call
surviving long enough to reach a specific later point.

**Why this matters for the writeup:** Second example (after the scenario
04 medication fix) of iterating on test design itself based on what was
observed, rather than just re-running the same setup and hoping for a
different result — relevant for rubric item #5 ("evidence you iterated").

---

## Root-cause diagnosis: why scenarios 06, 09, and 10 weren't testing what
they were designed to test

After three scenarios kept producing invalid/inconclusive test results, did
a deeper investigation (web research into Vapi's actual voice pipeline
behavior) rather than continuing to guess at prompt wording. Findings:

**Scenario 06 (interruption):** Vapi has a real, built-in interruption
classifier that distinguishes genuine barge-ins ("stop," "hold up," "wait")
from passive backchannel acknowledgments ("yeah," "okay," "got it") — the
latter are intentionally NOT treated as interruptions, since real listeners
use them just to signal they're following along, not to cut in. The
scenario's example interruption phrase ("yeah, the first one's fine") was
short enough to be classified as a backchannel, not a real interruption —
so the test never actually exercised barge-in handling at all, regardless
of how the LLM played it. FIX: rewrote the scenario to require longer,
unambiguously interruptive phrasing ("wait, hold on—", "actually, can I
just say something—") that should register as a genuine interruption under
Vapi's classifier.

**Scenario 09 (contradictory info):** Root cause was a model behavior
tendency, not a Vapi pipeline limitation — LLMs are trained toward internal
consistency, so when asked to "decide" to contradict itself naturally
mid-call, the model tended to soften the instruction (stating a detail once
instead of truly conflicting itself, or self-flagging the inconsistency).
FIX: rewrote the scenario to specify both conflicting facts explicitly as
fixed, given values rather than something the model has to "choose" to
generate inconsistently — removes the model's room to resolve the conflict
on its own.

**Scenario 10 (silence/pause):** Genuine architecture limitation, not
something fixable via prompt wording alone. Vapi's endpointing system
reacts to actual silence/timing in incoming audio — but a text-generating
LLM has no mechanism to insert real dead air into its own output; "[pause]"
in a prompt is just words to be spoken by TTS, not actual silence, unless
the TTS provider supports SSML break tags AND Vapi passes them through
(unconfirmed). DECISION: treat this as a known testing limitation rather
than continuing to chase a fix — document in the architecture doc rather
than spending further scenario-design effort on it.

**Why this matters for the writeup:** Good example of recognizing when a
recurring test failure is NOT a prompt-wording problem and requires
understanding the actual underlying system (the voice pipeline/platform)
rather than just iterating on text. Strong material for the Loom — shows
debugging that goes beyond surface-level prompt tweaking.

---

## Pattern recognized: medical-complaint/clinic-type mismatch (2nd
occurrence — scenario 06)

**Issue:** Scenario 06's re-run (after the interruption-phrasing fix) still
failed — but for a DIFFERENT, recurring reason: the original scenario had
the patient calling about a "sinus infection," which has no plausible
connection to an orthopedic clinic. Same root cause as the original
scenario 04 failure (blood pressure medication at an orthopedic clinic) —
the LLM playing the patient correctly recognized the premise didn't fit the
business type and abandoned the call before any interruption testing could
occur.

**Fix:** Changed the complaint to sudden lower back pain (orthopedics-
appropriate) and added the same "stay committed to the premise" guardrail
used in scenario 04.

**Generalized lesson for remaining/future scenario design:** ANY scenario
premise must be something Pivot Point Orthopedics would plausibly handle —
back pain, joint pain, knee/shoulder/bone issues, fractures, physical
therapy follow-ups. Avoid general-practice-sounding complaints (sinus
infections, blood pressure meds, etc.) even when the complaint itself isn't
the point of the test (e.g. when the real focus is interruption handling
or pause handling) — an implausible premise can derail the entire call
before the actual test condition is reached, regardless of what's being
tested.

---

## Third issue with scenario 06: interruption timing relative to response
length

**Issue:** After fixing the premise (back pain), the call completed
naturally, but still no genuine interruption occurred. Root cause: Athena's
responses in that call stayed short (single questions), so there was never
a long, multi-part response for the patient to actually cut into. The
patient's "Wait. Hold on." phrase only landed AFTER Athena had already
finished a short, complete sentence — that's a normal turn, not a barge-in,
regardless of how interruptive the phrasing sounds.

**Fix:** Added an explicit instruction for the patient to ask for multiple
options at once ("what times do you have today or tomorrow, can you list a
few?") — this should force Athena into a longer, multi-item response,
creating an actual window mid-delivery for a real interruption to occur.
Also tightened the rule to explicitly require waiting for a LONG response
before interrupting, rather than cutting in after any short, already-
complete sentence.

**Status:** Scenario 06 has now been revised three times across attempts —
(1) premise fix, (2) interruption phrasing strength, (3) forcing a longer
target response to interrupt into. Will need one more clean run to confirm
this finally produces a genuine barge-in test.

---

## Operational constraint hit: Vapi daily outbound call limit

**Issue:** After 8 successful calls, a 9th call attempt failed with a 400
error. Diagnosed by printing the raw API response body (rather than just
the generic `HTTPError`), which revealed: "Numbers Bought On Vapi Have A
Daily Outbound Call Limit. Import Your Own Twilio Numbers To Scale Without
Limits."

**Decision:** Considered two options — (1) import a self-purchased Twilio
number into Vapi to remove the limit entirely, or (2) wait for the daily
limit to reset and continue with the existing Vapi-provisioned number.
**Chose option 1 (Twilio)**, reasoning: removes the constraint entirely
rather than being subject to it again on a future run, and the setup is a
one-time cost that also demonstrates a more production-realistic
architecture decision (importing your own carrier number is the standard
way to scale past a vendor's default limits) — worth having as a concrete
example of solving an infrastructure constraint rather than just waiting it
out, for the architecture doc / Loom.

**Execution:** Created Twilio account, purchased a voice-enabled number,
imported it into Vapi's Phone Numbers section using Twilio Account SID +
Auth Token, then updated `.env`'s `PHONE_NUMBER_ID` to the new Twilio-linked
number's ID (all other `.env` values — `VAPI_API_KEY`, `ASSISTANT_ID`,
`TARGET_NUMBER` — left unchanged, since only the outbound-calling number
itself changed).

**New issue hit immediately after switching to Twilio:** First call attempt
on the new number ended with `call.start.error-get-transport` — a
transport-layer failure, meaning Vapi couldn't establish the telephony
connection via the newly-imported Twilio number. No recording/transcript
content produced (call never actually connected). The Twilio number's
Voice Configuration page also showed no registered emergency (E911)
address, a likely contributing factor for US local number voice routing.

**Follow-up issue:** After attempting to fix `.env`'s `PHONE_NUMBER_ID` to
point at the new Twilio number, a retry returned the SAME original error
("Numbers Bought On Vapi Have A Daily Outbound Call Limit") — indicating
the `.env` update never actually took effect.

**Decision — clean restart:** Rather than continuing to debug a stack of
compounding issues across the existing account (original Vapi limit +
transport error + a stale env value that wasn't updating), did a full
clean restart: new Vapi account, new assistant, and a new Twilio account/
number with the emergency address registered up front this time (before
any test calls, rather than discovering the requirement only after a
failure). Reasoning: with multiple unresolved issues layered on top of each
other, isolating the actual root cause of any single one was getting harder
to do cleanly — a fresh, correctly-ordered setup was judged faster than
continuing to debug the existing tangled state. [UPDATE this entry once the
restart is confirmed working with a successful test call.]

---

## Status snapshot (update as you go)

- Scenarios completed: 8 valid calls (01, 02, 03, 04-retry, 05, 06, 07, 08)
  + 1 wasted call (04 first attempt, scenario design flaw)
- Scenarios remaining: 09 (contradictory info), 10 (silence/pause),
  11 (out-of-scope), 12 (multiple requests)
- Blocked on: Vapi daily outbound limit — [resolve before continuing]
- Bug report: drafted findings live in FEEDBACK_LOG.md, not yet
  consolidated into final BUG_REPORT.md
- Architecture doc: skeleton only, not yet filled in
- GitHub repo: not yet created
- Loom + AI-debugging recording: not yet recorded
