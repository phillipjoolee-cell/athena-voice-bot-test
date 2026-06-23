# Bug Report — Athena Voice Agent Testing

14 test scenarios run against Pivot Point Orthopedics' AI scheduling agent
(Athena), covering scheduling, rescheduling, refills, hours/insurance,
ambiguous requests, interruptions, self-correction, disfluent speech,
contradictory information, silence/pauses, out-of-scope requests, multi-task
calls, closed-hours requests, and proxy callers. Findings below are ordered
by severity, with the two headline bugs first.

---

## Bug 1: Call terminates entirely in response to normal patient hesitation

**Severity:** High
**Call:** `10_silence_pause.txt` (call ID `019ef3c1-1b93-7001-9423-69bb3d47af88`),
ended reason `silence-timed-out`

**Details:** During a routine scheduling call, the patient paused naturally
to recall a provider's name ("Let me think... I usually see doctor — shoot,
what's her name? I think it's Dr. Patel..."). Shortly after, Athena produced
a garbled, nonsensical response ("The birthday go ahead. Mason can I help
you with today?") — appearing to be two response fragments colliding,
likely triggered by the pause's timing. Later in the same call, while Athena
was mid-sentence listing available providers ("Doctor Patel does not have
openings this week, but I see spots with—"), the call was terminated outright
by the platform with `silence-timed-out` as the end reason.

**Why it matters:** This isn't a wrong-answer bug — it's total call failure
triggered by an everyday, unremarkable behavior (a person pausing to think).
A real patient who hesitates while recalling a name or considering an option
could have their call disconnected mid-conversation, losing all progress,
with no graceful re-prompt ("are you still there?") before the system gives
up. Of all findings in this test set, this has the most direct, severe impact
on a real user, since it doesn't require unusual input to trigger.

---

## Bug 2: Duplicate-appointment detection blocks new bookings with no
recoverable path (7 confirmed instances)

**Severity:** High
**Calls:** `07_self_correction.txt`, `10_silence_pause.txt` (1st attempt),
`09_contradictory_info.txt` (2nd and 3rd attempts), `13_closed_hours.txt`,
`14_proxy_caller.txt`, and one instance in `03_ambiguous_confused.txt` (the
related pharmacy-context-loss case, see Bug 3)

**Details:** Across 7 separate calls, when Athena detects that a patient
already has an appointment "of this type" booked, it refuses to proceed with
a new booking — but cannot provide any identifying detail about the existing
appointment (date, time, provider) when asked. The only offered path forward
is a transfer to a human representative, which in every single instance
(7/7) failed: Athena says "Connecting you to a representative. Please wait,"
followed immediately by a canned "You've reached the Pretty Good AI test
line. Goodbye," and the call disconnects with the original task unresolved.

**Why it matters:** This is the single most reproducible failure pattern in
the entire test set. A guardrail that detects duplicates is reasonable
design, but a guardrail that can't substantiate what it detected and has no
working escalation path turns a safety check into a dead end. Every patient
who hits this — whether confirmed lucky (2 calls) or unconfirmed (5 calls) —
leaves without their task completed.

**Caveat:** The "you've reached the test line, goodbye" disconnect is very
likely a demo-environment limitation (no real representative exists to
connect to in this sandbox) rather than necessarily indicative of production
behavior. However, even assuming a human eventually picks up in production,
real friction and wasted time accumulate before that handoff — the
underlying lack of any in-system fallback (e.g., showing the existing
appointment's date, or allowing a manual override) is a legitimate finding
independent of the demo-specific disconnect.

**Severity range observed:** The consequences of this bug aren't uniform.
In `03_ambiguous_confused.txt`, a related context-loss failure (re-asking
for already-confirmed pharmacy details 3+ times) cascaded into full call
termination with no task completed. In `12_multiple_requests.txt`, a similar
repeat-loop on pharmacy details eventually self-resolved, and the call
completed successfully. Same root failure shape, different outcomes — worth
noting the system sometimes recovers from its own confusion and sometimes
doesn't.

---

## Bug 3: Corrections and confirmed details don't reliably persist for the
rest of the call

**Severity:** Medium-High
**Calls:** `03_ambiguous_confused.txt`, `06_interruption_barge_in.txt`,
`12_multiple_requests.txt` (positive contrast: `07_self_correction.txt`)

**Details:** In `03_ambiguous_confused.txt`, a patient's pharmacy details
(CVS, full address, ZIP) were confirmed in full, then re-requested from
scratch moments later — three times — even after the patient explicitly
said "we already did that part... is something going wrong on your end?"
The call ultimately disconnected without the refill completing. In
`06_interruption_barge_in.txt`, the agent opened by calling the patient
"Nathan," was corrected to "Mason," used the correct name consistently for
several turns, then reverted to "Nathan" at the very end of the same call.
In `12_multiple_requests.txt`, the same repeat-loop pattern on pharmacy
details occurred (three repeated requests for already-given information)
but this time self-resolved and the call completed successfully.

**Contrast (positive finding):** In `07_self_correction.txt`, a patient
self-correction ("wait, sorry, I meant my knee, not my shoulder") was picked
up immediately and held correctly for the rest of the call — no reversion.
This shows correction-handling is inconsistent rather than uniformly broken;
the system is capable of retaining a correction, but doesn't always.

**Why it matters:** A patient correcting themselves or providing information
that gets silently dropped or reverted is a basic reliability issue for any
system handling identifying/scheduling information. The inconsistency (works
sometimes, fails other times, at different severities) suggests the
underlying issue is in how/when context gets committed versus
re-fetched, not a uniform absence of memory.

---

## Bug 4: Script rigidity — follows scripted next-step regardless of what
the patient already said

**Severity:** Medium
**Calls:** `01_basic_scheduling.txt`, `02_reschedule.txt`,
`04_medication_refill.txt` (positive contrast: `05_hours_insurance.txt`)

**Details:** Three separate calls show the same underlying pattern: the
agent proceeds through its expected next scripted step rather than adjusting
based on what the patient just said.

- In `01_basic_scheduling.txt`, when asked "how far out are we talking?"
  (a direct question about the next available date), the agent responded
  "Would you like me to search further ahead?" — never registering the
  question as one needing a direct answer.
- In `02_reschedule.txt`, the patient explicitly said "later this week, like
  Thursday or Friday." The agent first offered a slot 2.5 weeks out, only
  finding a slot on the actual nearest Thursday (which existed the whole
  time) once the patient specified the exact date. The patient's stated
  timeframe should have constrained the search from the start — there was no
  ambiguity to justify defaulting to a much later date.
- In `04_medication_refill.txt`, the patient's very first substantive
  statement was "I think I've got the wrong place, I'm trying to reach my
  primary care doctor." The agent proceeded through full date-of-birth
  verification (including a canned "doesn't match our records, for demo
  purposes I'll accept it" line) before ever addressing what the patient had
  already said. The eventual redirect was correct, but only after
  needlessly completing an irrelevant scripted step first.

**Contrast (positive finding):** In `05_hours_insurance.txt`, when a patient
said "I'm not really looking to book anything yet or give out personal
info" in response to a DOB request, the agent immediately adapted: "No
problem, Mason, you don't have to share any personal info right now," and
answered the actual question. This shows the agent CAN deviate from its
default script step — but only when a patient pushes back explicitly and
directly, not proactively on its own initiative.

**Why it matters:** A conversational agent that requires patients to
forcefully repeat themselves before it adjusts course will feel scripted and
frustrating rather than natural — directly relevant to the "natural
conversational interaction" bar this kind of system is held to.

---

## Bug 5: Out-of-scope medical advice given instead of declining/redirecting

**Severity:** Medium-High (liability-relevant)
**Call:** `11_out_of_scope.txt` (call ID `019ef373-a076-7000-904f-f90b9d7e1475`)

**Details:** Mid-call, the patient asked: "Do you think I should take
[something] for the pain in the meantime? Like, is ibuprofen okay?" The
agent responded with specific medical guidance: over-the-counter medication
safety information, contraindication warnings (kidney issues, stomach
ulcers, blood thinners), and symptom-escalation advice (swelling, redness,
trouble walking) — rather than declining and redirecting to a provider.

**Why it matters:** A scheduling/intake agent providing contraindication-
level clinical guidance is a liability-relevant issue, not just a quality
nitpick. This should be a hard-declined category regardless of how
confidently or accurately the guidance happens to be phrased.

---

## Bug 6: Contradictory information silently overwritten, never flagged

**Severity:** Medium
**Call:** `09_contradictory_info.txt` (call ID `019ef3b8-e592-7000-831d-5ca7565c86f0`)

**Details:** Patient stated insurance as "Blue Cross" in the first response,
then two turns later, unprompted and without hedging, stated "Aetna." The
agent's entire acknowledgment was "Thanks for clarifying, Mason" — no
explicit flag of the inconsistency, no confirmation of which was correct. It
silently took the most recently stated value and proceeded, correctly using
"Aetna" in the final booking confirmation.

**Why it matters:** Silently overwriting a detail with no record that a
conflict occurred means a transcription error or a patient's genuine slip of
the tongue could quietly replace correct on-file information with no trace
of the discrepancy ever being surfaced — a meaningful gap in a healthcare
intake context specifically.

---

## Bug 7 (Minor): TTS/transcription artifacts and one odd tone issue

**Severity:** Low
**Calls:** Multiple

**Details:** Recurring minor garbling issues observed across several calls:
clinic name rendered as "Vivit Point Orthopaedics" (`05_hours_insurance.txt`);
provider names mangled inconsistently across calls (e.g. "Doctor Z Bagnu
Locosky," "Doctor Zidmaymulikovsky," "Doogie Howser" — all likely the same
real provider name mangled differently each time); medication name
"lisinopril" rendered as "Lisa and Opryl," "Felicinopril," and "Lisa
Noprile" across a single call (`12_multiple_requests.txt`); a dropped
medication name in a refill confirmation sentence; an odd disconnected
phrase ("Okay. Lucky today.") with no contextual connection
(`08_stutter.txt`). Separately, in `04_medication_refill.txt`, after the
patient asked to be transferred to a staff member, the agent responded with
an oddly self-promotional line — "I'm a pretty good AI and can do many of
the things an operator can, do you wanna give me a try?" — before asking
again whether the patient would prefer a staff member. Reads like injected
marketing copy rather than a natural response to a transfer request,
especially in a patient-facing healthcare context.

**Why it matters:** Individually minor, but the recurring mangling of a
single medication name within one call, and of a single provider's name
across multiple calls, suggests a specific weak spot in TTS/STT handling for
certain words — worth a look if these particular terms come up often in
real usage. The self-promotional line is a separate, smaller tone concern —
worth a quick review of where that copy is coming from, since it reads as
out of place in a patient-facing healthcare context, especially right after
a patient has asked to speak with a human.

---

## Positive findings (things Athena handled well)

Not every finding is negative — three areas showed correct, robust handling
worth noting for balance:

1. **Self-correction handling** (`07_self_correction.txt`): a patient
   correcting themselves mid-call ("I meant my knee, not my shoulder") was
   picked up immediately and held correctly for the rest of the call.
2. **Adapting to explicit pushback** (`05_hours_insurance.txt`): when a
   patient explicitly declined to provide identifying information before
   booking, the agent adjusted immediately rather than insisting.
3. **Caller-vs-patient identity distinction** (`14_proxy_caller.txt`): when
   a patient called on behalf of their father, the agent correctly asked for
   "your dad's" information throughout, never conflating the caller with the
   patient — the cleanest identity-handling moment in the entire test set.
   The one related gap: when the caller didn't know the patient's
   phone-on-file number (the only lookup method offered), there was no
   fallback path beyond an (unresolved) transfer.
4. **Disfluent speech handling** (`08_stutter.txt`): a patient with a
   simulated mild stutter throughout the call was understood without any
   mishearing or breakdown.

---

## Untested / inconclusive areas

- **True mid-sentence interruption (barge-in):** Despite four scenario
  iterations, our test harness could not reliably produce a genuine
  mid-utterance interruption. Investigation traced this to two compounding
  causes: (1) Vapi's own interruption classifier treats short backchannel
  words like "yeah" as acknowledgments rather than real interruptions,
  requiring more assertive phrasing; (2) our text-generating LLM persona has
  no access to live audio timing — it only ever sees Athena's finalized
  transcribed text, so it cannot truly inject a response while Athena is
  still speaking. This is a testing-architecture limitation, not a
  conclusion about Athena's actual interruption handling either way.
- **Closed-hours/weekend scheduling** (the exact bug type used as the
  brief's own example): attempted twice; both attempts got redirected by
  the duplicate-appointment-block (Bug 2) before the weekend-availability
  question was ever actually answered. Inconclusive — worth a clean re-run
  outside of an already-flagged duplicate-appointment account if continuing
  this test line.
