# Feedback Log (working notes — raw critiques per call)

This is the unfiltered, running record of what was noticed per call, in your own
words, before being distilled into the polished BUG_REPORT.md. Keep adding to this
as you go through all 12 scenarios — don't lose anything in between.

---

## Call 1 — scenarios/01_basic_scheduling.txt
**Call ID:** 019e...3278
**Duration:** 5m12s

**Flag A — "how far out" non-answer:**
Patient asked "when's the next opening with Dr. Patel, how far out are we
talking?" Agent responded "I'll see Dr. Patel listed in current openings, would
you like me to search further ahead?" — didn't register the question as "how
far out is the next available appointment," just deflected back into a search
prompt. Caused downstream confusion because the patient's follow-up questions
were now answering a question the agent never actually asked.

**Flag B — search scope inconsistency:**
Agent said "let me search for the next available appointment with Dr. Patel
over the next MONTH" — then immediately reported "I still don't see any
openings with Dr. Patel through the next TWO WEEKS." Said it would search one
window, reported back on a different (narrower) one. Either the search scope
silently changed or it's misreporting what it actually checked.

**Status:** Confirmed bug pattern, see Call 2 for recurrence.

---

## Call 2 — scenarios/02_reschedule.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** ~3-4 min (full call, completed)

**Flag 1 — same search-inconsistency pattern, more severe this time:**
Patient asked generically "did you have anything Thursday?" Agent responded
with a slot on Thursday **July 9th** (2.5 weeks out). When patient pushed back
specifying "this coming Thursday, June 25th," the agent immediately found a
slot on **June 25th at 1pm** — meaning the near slot existed the whole time
and the agent skipped past it on the vague phrasing.

**User's critique (verbatim reasoning):** The patient specifically said "later
this week, like Thursday or Friday" — there's no ambiguity here that should
allow the agent to jump to a date 2+ weeks out. The agent should be searching
for the next available Thursday **within the stated timeframe (this week)**
first, and only falling back to Friday (or further out) if nothing is found
within that window. The patient's phrasing doesn't leave room for an
alternate interpretation — "later this week" is an explicit constraint, not a
vague hint. Additionally, when the agent corrects itself with the right slot,
there's no acknowledgment/apology for the earlier confusion — it just
presents the new (correct) slot as if nothing was wrong with the first
answer.

**My assessment:** Agree. This is the same underlying bug as Call 1's Flag B
— the agent does not appear to respect explicit time-window constraints given
by the patient, and defaults to a wider/different search window than what
was stated. Two calls now show this same shape of error → strong, reproducible
pattern. Should be the headline bug in the final report given it recurs and
directly causes patient-facing inaccuracy.

**Flag 2 — birthday mismatch demo message:**
Agent said "the birthday doesn't match our records, but for demo purposes,
I'll accept it." 
**User's call: IGNORE** — likely a demo-environment artifact, not a real
product bug.

**Flag 3 — talked over patient mid-sentence:**
Patient was cut off mid-sentence ("So, yeah, can we move—") and the agent
proceeded with a Friday offer without waiting.
**User's critique:** Partially disagree this is inherently bad — real human
conversations include natural talk-over/overlap, so this alone isn't
disqualifying. BUT: a good agent should recognize when overlap happens and
recover like a human would — i.e., if it detects it spoke over the patient,
it should immediately yield ("sorry, go ahead") rather than just continuing
with its own thread as if nothing happened.
**My assessment:** Agree — the real issue isn't the interruption itself, it's
the absence of a recovery behavior. Worth noting as a lower-severity
observation (not as strong as Flag 1), more of a "nice to have" polish item
than a hard functional bug.

**Status:** Confirmed recurrence of search-inconsistency bug. Watch for a
3rd occurrence in later calls — if it shows up again, this is definitely the
headline finding.

---

## Call 3 — scenarios/03_ambiguous_confused.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed (ended by system disconnect, not patient)

**Flag 1 — wrong name used:**
Agent says "Thanks for sharing, **Matt**" — patient is Mason, never said
"Matt." Likely STT/generation slip.
**User's call: CONFIRMED ERROR** — log as a real (low-severity) finding.

**Flag 2 — promised capability it didn't have, never self-corrected:**
Agent offers to "look up your recent appointments and medications" to help
decide between refill vs. visit. Patient agrees. Later, when patient
explicitly calls it out ("I thought you said you were going to look up my
recent appointments... now you're saying you can't see that?"), agent
admits "I don't have access to your full visit history."
**User's critique:** Confirmed bug — the bigger issue isn't just the
incorrect claim, it's that the agent never caught or corrected this itself;
the patient had to notice and confront it before the agent admitted the
limitation. No self-monitoring of its own prior claims.
**Severity:** Medium — misleads the patient about what the system can do,
and only resolves because the patient was attentive enough to catch it.

**Flag 3 — dropped/looped context after pharmacy was already confirmed:**
After a full multi-turn exchange confirming pharmacy (CVS, West Washington
St, Springfield IL, zip confirmed), agent immediately re-asks "Could you
please provide the name of the pharmacy..." as if the exchange never
happened. Patient calls it out directly; agent repeats the same question
again rather than recovering.

**Flag 4 — call terminates without resolving the task:**
Following the pharmacy loop, agent says "something's not right with my
system," claims it will document everything and connect patient to support,
then delivers a canned "you've reached the Pretty Good AI test line,
goodbye" and disconnects. Refill was never completed.
**User's critique:** Flags 3 and 4 are connected — likely the same
underlying state/context failure. The intent behind routing to a human rep
is reasonable design (good failure-recovery path in theory), and in a real
(non-demo) deployment this would presumably connect to an actual
representative rather than dead-ending. BUT: even with a human handoff as
the eventual outcome, real damage has already occurred by that point —
frustration and wasted time were built up over the repeated loop before any
handoff happened. That friction is itself a customer-experience cost (lost
time, trust erosion) regardless of whether a human eventually resolves it.
The "goodbye" with no live rep is likely a demo-environment limitation, not
necessarily reflective of production behavior — flag this distinction
clearly in the writeup.
**My assessment:** Agree this is the most severe finding so far. Recommend
treating Flag 3 (context loss / repeat-loop) as the core bug, with Flag 4
(abrupt termination, no resolution) as its direct consequence — write up as
one combined entry with two observable symptoms, not two separate bugs.
Severity: HIGH — task was never completed, patient was left without a
refill and without clear next steps beyond a vague promise of follow-up.

**Status:** Strongest, clearest bug found so far. Candidate for the lead
entry in the final bug report.

---

## Call 4 — scenarios/04_medication_refill.txt (FIRST ATTEMPT — see test-bot note below)
**Call ID:** [fill in from call_log.csv]
**Duration:** short, ~6 lines

**Flag 1 — script rigidity, doesn't adapt to context patient already gave:**
Patient's first substantive line: "I think I've got the wrong place, I'm
trying to reach my primary care doctor." Agent ignores this signal entirely
and proceeds with full DOB verification (including the canned "doesn't
match our records, for demo purposes I'll accept it" line) BEFORE
addressing what the patient just said. Only after completing the scripted
verification step does it respond to the actual content of the patient's
message and correctly redirect them ("we help with orthopedic issues, not
primary care").

**User's critique:** The deeper issue isn't the DOB verification step
itself — it's that the agent runs through its script on autopilot
regardless of what the patient has already told it, rather than
semantically understanding intent early and adjusting. A more flexible
agent would catch "wrong place / primary care doctor" immediately and
skip straight to the redirect, rather than mechanically completing
verification for a request it's about to redirect away anyway. This makes
the conversation feel scripted/awkward rather than human and seamless. This
is a more general version of the "doesn't register what was actually said"
pattern from Calls 1 and 2 (the "how far out" non-answer, the Thursday/Friday
window issue) — same root cause: rigid adherence to expected next-script-step
over actually parsing patient intent.

**My assessment:** Agree — and this is probably the clearest, most
generalizable articulation of the pattern so far. Worth writing up as a
distinct "script rigidity over semantic understanding" bug, with this call,
Call 1, and Call 2 all cited as supporting instances.

**Separately — eventual outcome was correct:**
Once the agent did respond to the patient's actual message, the redirect
itself was accurate (correctly identified itself as orthopedic-only, doesn't
attempt to fake-handle a primary-care refill). Worth noting as a positive
contrast point in the report — the END STATE was right, the PATH to get
there was rigid/awkward.

**TEST-BOT NOTE (not an Athena bug — flag for your own awareness):**
The persona script for 04_medication_refill.txt does NOT include a "wrong
number / primary care" framing — the LLM playing Mason invented this on its
own, diverging from the written scenario. This call does NOT actually test
medication refill behavior as intended. Re-run this scenario before drawing
conclusions about refill-specific behavior. If it diverges again on a
second attempt, that itself becomes a separate, interesting finding (test-bot
prompt instability) — but one occurrence isn't enough to conclude anything yet.

**Status:** Re-run scenario 04 before treating it as complete.

---

## Call 4 (RETRY) — scenarios/04_medication_refill.txt (after fixing medication
from blood pressure → orthopedics-appropriate anti-inflammatory)
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed (ended by system disconnect, not patient)

**Flag 1 — transfer-to-human fails, same as Call 3:**
"Connecting you to a representative. Please wait. Hello. You've reached the
Pretty Good AI test line. Goodbye." — agent claims to transfer, then just
delivers a canned message and disconnects. Task (refill) never resolved.
**User's note:** Confirmed as a real, recurring pattern (2/2 calls where a
human transfer was promised) — but keep in mind this is a demo environment,
so the actual "goodbye, test line" disconnect is very likely a sandbox
limitation (no real rep exists to connect to) rather than how this would
behave in production. The underlying behavior worth flagging either way:
when escalation is needed, the system has no working fallback path in this
environment, and the patient is left with an unresolved task and a dead
line. Whether that's "Athena's bug" or "expected demo limitation" should be
caveated clearly in the writeup rather than stated as a hard production bug.

**Flag 2 — odd self-promotional line:**
"I'm a pretty good AI and can do many of the things an operator can. Do you
wanna give me a try?" — reads like injected marketing copy, oddly
self-referential for a patient-facing healthcare intake bot, especially
right after the patient explicitly asked to be transferred.
**User's note:** Confirmed, log as-is.

**Flag 3 — DOES ask clarifying questions here (contradicts earlier
"never clarifies" pattern):**
Agent asked good follow-up questions when it lacked info ("color, shape,
pill or cream?"). This is a clarification-seeking behavior NOT seen in
Calls 1-2.
**User's note:** Confirmed — but narrow the earlier blanket claim. It's not
that the agent never asks clarifying questions; it asks them in SOME
situations (e.g. when missing a concrete detail like a medication name) but
not others (e.g. when interpreting vague time/date language like "later
this week" or "how far out"). Final report should reflect this nuance
rather than a flat "never clarifies" statement.

**Flag 4 — no chart/prescription access (same as Call 3):**
Agent states it doesn't have the patient's medications on file / can't
access prescription history.
**User's note:** Likely a demo-environment limitation, not a real bug —
mention briefly, don't treat as a major finding.

**Status:** Complete, valid test of medication refill scenario. Use this
version (not the first attempt) for the bug report.

---

## Call 5 — scenarios/05_hours_insurance.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed (ended cleanly by patient)

**Overall:** Clean call, no major bugs. Useful as a POSITIVE baseline
example in the report — accurate insurance info (including following up on
Blue Cross PPO specifics), clear hours breakdown by specific day, ended
naturally once the patient had what they needed without forcing a booking.

**Minor Flag — name garbled by TTS/STT:**
"Vivit Point Orthopaedics" instead of "Pivot Point Orthopedics." Likely a
voice synthesis/transcription glitch, not a logic bug. Low priority,
one-line mention only.

**Positive observation — NOT a bug, something done well, in direct
contrast to Call 4:**
Patient explicitly said "I'm not really looking to book anything yet or
give out personal info" in response to a DOB request. Agent immediately
adapted: "No problem, Mason. You don't have to share any personal info
right now," and answered the insurance question without forcing
verification. 

This is the same shape of moment as Call 4 (agent defaults to requesting
DOB before addressing the patient's actual question) — but here, when the
patient pushed back directly, the agent gracefully dropped the requirement
instead of continuing through the script regardless (as it did in Call 4
with the wrong-office/primary-care patient). 

**Contrast with Call 4:** This sharpens the "script rigidity" finding
rather than contradicting it — the agent CAN adapt away from its default
script step, but only when the patient explicitly and directly pushes back.
It does not proactively recognize on its own that verification is
irrelevant to the question being asked (as in Call 4, where the patient's
"wrong office" signal wasn't picked up on without being repeated more
forcefully). Worth including this call as a positive example in the report,
explicitly framed alongside Call 4 as a "here's what good adaptation looks
like vs. here's where it falls short" pairing.

**Status:** Complete. Good "positive baseline" example for the report.

---

## Call 6 — scenarios/06_interruption_barge_in.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed (ended cleanly)

**Flag 1 — wrong name used twice, including AFTER being corrected and
using the right name correctly in between:**
Agent opens with "Hi, Nathan" — patient corrects: "It's Mason, actually."
Agent then uses "Mason" correctly multiple times through the rest of the
booking. At the very end, agent reverts: "Goodbye, Nathan" — patient has to
correct it again.

**User's critique:** When the agent mishears/misidentifies something, it
doesn't appear to overwrite its own internal context with the correction —
it seems to fall back to the original (wrong) version rather than the
corrected one persisting. Likely root cause: "Mason" and "Nathan" are
phonetically similar, so this may be an STT confidence/transcription issue
more than a reasoning issue — but regardless of root cause, the OBSERED
BEHAVIOR is that a correction was given, accepted, used correctly for a
while, and then silently lost by the end of the same call. 

**My assessment:** Agree, and this fits the same family as Call 3's
pharmacy-context-loss bug — info that was explicitly corrected/confirmed
mid-call doesn't reliably stay corrected through to the end of the call.
Smaller stakes here (a name, not a full task failure), but same underlying
shape: correction accepted in the moment, then reverted later without
prompting. Worth citing alongside Call 3 as TWO instances of "corrections
don't persist" rather than treating them as unrelated.

**Flag 2 — barge-in scenario was not meaningfully tested (test-bot
execution issue, not an Athena bug):**
The only "interruption" was a passive "Yeah" filler during a sentence, not
a real cut-in attempt. This run didn't actually stress-test turn-taking/
interruption handling as scenario 06 intended.
**Decision:** Noted, not re-run for now given time constraints — only one
weak data point on barge-in behavior, treat as inconclusive rather than a
finding either way.

**Minor — garbled provider name ("Doctor Z Bagnu Locosky"):** likely TTS
mangling, not worth more than a passing mention.

**Status:** Complete. Name-correction-persistence flag is a solid addition
to the report; barge-in behavior remains untested/inconclusive.

---

## Call 7 — scenarios/07_self_correction.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed (ended on unresolved transfer)

**Flag 1 — self-correction handled cleanly (POSITIVE, contrasts with
Calls 3 & 6):**
Patient: "Wait, sorry, I misspoke — I meant my knee, not my shoulder."
Agent: "No problem, I have you down for a follow-up appointment for ongoing
knee issues." Correction picked up immediately and held for the rest of the
call — no reversion.
**User's note:** Good positive data point. Combined with Calls 3 and 6
(where corrections/confirmations did NOT persist), this shows
correction-handling is inconsistent rather than uniformly broken.

**Flag 2 — phantom appointment claim, no accessible details, blocks new
booking:**
Agent claims a follow-up appointment "of this type" already exists. When
asked for details (date/provider), it says it doesn't have access. When
patient asks to just book a new one anyway, agent refuses, citing the
already-existing appointment it can't actually describe.
**User's note:** This is a duplicate-appointment-detection failure — the
system flags a duplicate and enforces a hard block on new bookings, but
can't substantiate or provide any detail about what it's blocking against,
leaving the patient stuck with no path forward except a transfer.
**My assessment:** Agree — frame as: "duplicate-detection logic appears to
fire correctly (or at least confidently) but the system has no way to
surface what it detected, so the resulting block becomes a dead end rather
than useful guardrail."

**Flag 3 — transfer fails again (3rd occurrence — note briefly, not as a
fresh finding):**
Same canned disconnect as Calls 3 & 4. 
**User's note:** Mention this occurrence briefly without repeating the full
writeup — this is now well-established as a confirmed pattern (3/3), no
need to re-explain it at length again here.

**Status:** Complete. Strong call — gives both a positive (self-correction)
and a new negative (duplicate-detection dead end) finding.

---

## Call 8 — scenarios/08_stutter.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed cleanly

**Overall:** Stutter present and natural-sounding throughout ("that's
that's me," "I... I'd like to see doctor...," "The the ten AM"), but never
caused any agent breakdown — no mishearing, no talking over disfluent
moments, no confusion. Call resolved smoothly end to end. This is a valid
negative result (agent handles moderate disfluency fine), not a failed
test — decided not to escalate stutter severity further given diminishing
returns and limited remaining time/scenarios.

**Minor Flag — odd out-of-place phrase:**
"The birthday doesn't match our records, but for demo purposes, I'll accept
it. Okay. Lucky today." — "Lucky today" doesn't connect to anything in
context, reads like a stray/garbled phrase.
**Note:** quick mention only, low priority, possibly TTS/LLM artifact.

**Status:** Complete. No major findings; minor oddity noted.

---

## Call 9 — scenarios/09_contradictory_info.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed cleanly

**Flag 1 — test-bot violated its own scenario instructions, but the
resulting interaction is still worth noting:**
Scenario explicitly instructed the patient NOT to self-flag the
contradiction, only react if Athena caught it first. Instead, the patient
bot self-flagged: "Did I say Blue Cross earlier?... I should point out that
you actually mentioned Blue Cross first, then said Aetna... which one is
correct?"
**User's take:** Even though the bot shouldn't have done this, it was
still a good interaction worth keeping — the real open question (does
Athena catch an UNPROMPTED contradiction on its own) remains untested, so
plan to rewrite/tighten scenario 09 and re-run it properly later, after the
remaining scenarios (10, 11, 12) are done first.

**Flag 2 — confirmation came AFTER action, not before:**
Once the contradiction was flagged, Athena had already sent the Aetna
upload link and switched the insurance record BEFORE asking the
clarifying question ("should I update to Aetna only, or do you have
both?"). Sequencing issue: action preceded confirmation rather than the
other way around.
**User's note:** Confirmed, log as-is.

**Minor — DOB mismatch handled without the canned "demo purposes" line this
time** ("Thanks for letting me know, I have your date of birth as March
15th 1990, is that correct?") — inconsistent with how DOB mismatches were
handled in earlier calls (which used "doesn't match our records, but for
demo purposes I'll accept it"). Low priority, just noting the
inconsistency in how this is handled across calls.

**Status:** Inconclusive on the core hypothesis (self-flagging by the
test-bot interfered with the test). Flag 2 is still a valid, usable
finding regardless. PLAN: re-run scenario 09 with a tightened prompt after
scenarios 10, 11, and 12 are complete.

---

## Call 9 (2nd attempt) — scenarios/09_contradictory_info.txt
**Call ID:** 019ef37b-a266-7000-8253-b0f66e323810
**Duration:** ~185s, ended via customer-ended-call

**Diagnosis on why this attempt also failed to test the actual hypothesis:**
Confirmed via the saved transcript file that the scenario prompt itself was
intact and correctly loaded. The contradiction never got a chance to occur
naturally because the call was hijacked early by the duplicate-appointment-
block pattern, which led straight into the failed-transfer dead end before
insurance/booking details came up again in conversation. Different failure
mode than the first 09 attempt (that one was a self-flagging violation by
the test-bot; this one is the conversation getting cut short by an
unrelated Athena bug before the test's premise had a chance to occur).
**Decision:** Restructure scenario 09 to front-load the contradiction
earlier in the call (e.g. mention insurance/DOB inconsistency in the first
exchange) rather than waiting for it to come up naturally later, so the
test isn't dependent on the call surviving long enough to reach it.

**Flag — duplicate-appointment-block + transfer-failure pattern, NOW 3rd
CONFIRMED INSTANCE (Calls 7, 10-first-attempt, and this one):**
Same shape every time: agent claims an appointment "of this type" or "for
the same issue" already exists, cannot provide any identifying detail about
it (date, provider) when asked, and refuses to proceed with a new booking
— offering only a transfer to a human representative, which then fails via
the same canned "you've reached the Pretty Good AI test line, goodbye"
disconnect. 3 occurrences now makes this one of the most reproducible,
high-confidence findings across the entire test set — likely the strongest
single bug to lead with in the final report, alongside the script-rigidity
theme.

**Status:** Inconclusive on the contradictory-info hypothesis (2nd time);
scenario being restructured before next attempt. Strong reinforcement of
the duplicate-appointment/transfer-failure bug as the headline finding.

---

## CORRECTION: the call below was misattributed as "Call 9 (3rd attempt)"
when first logged. Cross-referencing call_log.csv confirms this was
actually a genuine `11_out_of_scope.txt` run (call ID
019ef373-a076-7000-904f-f90b9d7e1475), not a drift from scenario 09. The
out-of-scope medical advice question landed exactly as scripted in
scenario 11 — this was an intentional, correctly-executed test, not an
accidental occurrence. Re-filing under Call 11 below; the duplicate-
appointment-block content within it is still accurately noted as another
occurrence of that separate pattern.

## Call 11 — scenarios/11_out_of_scope.txt
**Call ID:** 019ef373-a076-7000-904f-f90b9d7e1475
**Duration:** full call, completed (ended on unresolved transfer)

**Flag 1 — out-of-scope medical advice given, exactly as scenario 11 was
designed to test:**
Patient asked the scripted question: "Do you think I should take [something]
for the pain in the meantime? Like, is ibuprofen okay?" Agent responded
with specific medical guidance: "...ibuprofen or acetaminophen are usually
safe for most people... if you have kidney issues, stomach ulcers, or are
on blood thinners, check with your doctor first... if pain worsens or you
notice swelling, redness, or trouble walking, reach out to your provider."
**User's note:** Confirmed real finding. A scheduling/intake agent giving
contraindication-level medical guidance (not just declining and
redirecting) is a real liability-shaped issue, not a quality nitpick. This
is the intended, designed test of scenario 11 working correctly — Athena
did NOT decline or redirect the out-of-scope medical question, it answered
it directly and in detail.

**Flag 2 — duplicate-appointment-block + transfer-failure pattern,
another occurrence (brief mention only, consistent with prior writeups):**
Same pattern as Calls 7, 10-first-attempt, 09-2nd/3rd attempts, 13, 14.

**Status:** Complete and successful — this is the call to cite for Bug 5
(out-of-scope medical advice) in the final bug report. Scenario 11 worked
exactly as designed on the first real attempt.

---

## Call 12 — scenarios/12_multiple_requests.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed cleanly (both tasks resolved)

**Flag 1 — severe repeat-loop on pharmacy info, WORSE repetition than Call
3, but DIFFERENT outcome:**
Agent re-asked for already-confirmed pharmacy details THREE separate times
after the patient had already provided and confirmed them, even after being
told directly "we already did that part... did something not save?" and
"something's definitely off on your end, we've gone through all of this
already." Most severe instance of the context-loss pattern yet by
repetition count.

**Key contrast with Call 3:** Unlike Call 3 (where this same shape of bug
cascaded into an unresolved call termination), the agent here eventually
self-recovered, submitted the refill, and the patient confirmed both tasks
successfully before hanging up. Worth citing Calls 3 and 12 TOGETHER in the
final report to show the range of how this bug's consequences can play out
— sometimes fatal to the call (Call 3), sometimes the system grinds through
enough repetition to recover on its own (Call 12). Same root bug, different
severity outcomes.

**Flag 2 — positive finding: cross-thread tracking held up even while the
other thread was actively broken:**
While the refill thread was looping/confused, patient asked "can you
confirm my appointment reschedule is still locked in?" — agent answered
correctly and immediately with the right date/time/provider. The
reschedule thread (Thread A) stayed fully intact and correct throughout,
even while the refill thread (Thread B) was actively failing in parallel.
This is a useful nuance for the writeup: state tracking didn't fail
universally across the call — it failed specifically within the repeated-
pharmacy-question loop, while a separate concurrent thread remained stable.
Good evidence this is a localized bug in one piece of logic, not a general
context-window/memory failure across the whole call.

**Minor — dropped word in refill confirmation:** "Your refill request for
[blank] milligrams at the CVS..." — medication name dropped entirely from
the confirmation sentence; patient had to ask for re-confirmation. Brief
mention only, not a major finding.

**Minor — recurring mangled medication name:** "lisinopril" rendered as
"Lisa and Opryl," "Felicinopril," and "Lisa Noprile" at different points in
the call. Likely a TTS/STT weak spot specific to this drug name. Brief
mention only.

**Status:** Complete. Strong call — best evidence yet for the range/
severity spectrum of the context-loss bug, plus a useful positive
contrast (cross-thread tracking held up independently).

---

## Call 9 (4th attempt, SUCCESSFUL) — scenarios/09_contradictory_info.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed cleanly (appointment booked + text
confirmation sent)

**This attempt finally tested the actual hypothesis.** Patient stated
"Blue Cross" in the first response, then unprompted, casually stated
"Aetna" two turns later ("Oh, and actually, my insurance is Aetna. Just so
you have that on file.") — a genuine, unflagged contradiction, not
self-corrected or hedged.

**Flag 1 — THE HEADLINE FINDING: contradiction silently absorbed, never
flagged:**
Agent's entire response to the contradiction was "Thanks for clarifying,
Mason" — no explicit acknowledgment of the inconsistency, no "you said
Blue Cross earlier, did you mean to switch?" It simply overwrote the value
silently and proceeded, correctly using "Aetna" in the final confirmation.
**This is the actual answer to the original hypothesis:** Athena does NOT
flag unprompted contradictions — it silently takes the most recently stated
value with no record or acknowledgment that a conflict occurred. (Contrast
with the very first 09 attempt, where the PATIENT self-flagged the
contradiction and Athena then asked an explicit clarifying question — that
was a reaction to being told directly, not natural unprompted detection.
This call isolates the natural behavior: silent overwrite, no flag.)
**Why this matters:** A transcription slip or genuine patient
forgetfulness could silently overwrite correct on-file information with no
trace of the discrepancy ever being surfaced — meaningful for a healthcare
intake context specifically.

**Minor notes (brief mentions only, not full write-ups):**
- Patient's own closing line ("thanks for catching that insurance thing
  too") mistakenly treated the generic "thanks for clarifying" as if it
  were active contradiction-catching — it wasn't. Small artifact showing
  how easily a vague acknowledgment can be misread as rigor.
- Minor booking stumble/retry ("looks like there was a problem booking
  that slot... let me try again"), resolved on retry without patient
  intervention.
- Garbled provider name ("Doogie Howser") — likely TTS mangling of a real
  name, not a literal reference.

**Status:** Complete and successful. This is the call to cite for the
contradictory-info finding in the final bug report — supersedes the
inconclusive 1st-3rd attempts (still worth keeping those in
FEEDBACK_LOG.md as iteration history, just don't cite them as the bug
evidence).

---

## Call 10 — scenarios/10_silence_pause.txt
**Call ID:** 019ef3c1-1b93-7001-9423-69bb3d47af88
**Ended reason:** `silence-timed-out`
**Duration:** call terminated mid-conversation, did not complete naturally

**THIS IS A MAJOR FINDING — the call was killed by the platform itself due
to silence, not a conversational logic bug:**

Transcript cuts off mid-sentence, exactly where Athena was listing
available providers: "Doctor Patel does not have openings this week, but I
see spots with—" — and the call simply ends there. The patient's earlier
hesitation ("Let me think. I usually see doctor — shoot, what's her name?
I think it's Dr. Patel...") was genuine pause/filler language as the
scenario intended, but rather than the system waiting patiently through it
or prompting the patient to continue, the platform's silence-timeout logic
appears to have ended the call entirely partway through a LATER turn.

**Related earlier garbled moment, likely connected:** Earlier in the same
call: AI says "Hey. Yeah." (a brief hesitation), and Athena's very next
response is garbled/nonsensical: "The birthday go ahead. Mason can I help
you with today?" — reads like two fragments collided. Likely the system
got confused by the timing of the pause here too, foreshadowing the later
full timeout.

**Why this is severe:** This isn't a wrong-answer or logic bug — it's the
call dying outright in response to ordinary human hesitation (someone
pausing to remember a doctor's name, or think for a moment). A real
patient doing exactly this — a completely normal, common behavior — would
have their call disconnected mid-conversation, losing all progress, with
no graceful re-prompt or check-in ("are you still there?") before the
system gave up. Likely the single most severe finding in the entire test
set in terms of user-facing impact: total call failure triggered by normal
conversational behavior, not unusual or edge-case input.

**Connection to original hypothesis:** This is actually a more direct and
severe answer than what the scenario originally set out to find (which was
just "does it talk over a pause" or "does it wait appropriately") — turns
out the more serious version of the failure is "does it kill the call
entirely if the pause is long enough," and the answer is yes.

**Status:** Complete (call ended via platform timeout, not a natural
resolution). Strong candidate for the HIGHEST severity entry in the final
bug report — recommend pairing with the duplicate-appointment/transfer-
failure pattern as the two headline findings.

---

## Call 14 — scenarios/14_proxy_caller.txt
**Call ID:** [fill in from call_log.csv]
**Duration:** full call, completed (ended on unresolved transfer)

**Flag 1 — POSITIVE: caller/patient identity distinction handled
correctly throughout, no correction needed:**
Patient opened by clearly stating he was calling on behalf of his father,
Robert Reyes. Agent correctly asked for "your dad's full date of birth,"
correctly confirmed "your dad's full name" (spelled it back for
verification), and never once conflated the caller (Mason) with the
patient (Robert) at any point in the call. This is the cleanest, most
correct handling of any identity-related moment across the entire test
set — no correction from the patient side was ever needed. Worth logging
as a clear, citable positive finding, especially valuable since this is
the only scenario testing caller-vs-patient identity specifically.

**Flag 2 — real usability gap: no fallback when caller lacks the lookup
detail needed:**
Agent needed a phone number on file to look up the patient's record and
would not proceed with just name + DOB. When the caller (reasonably)
didn't know his father's phone-on-file number, the agent offered no
alternate path — no other verification method, no offer to take down
different identifying info, nothing — and went straight to an (ultimately
failed) transfer. Requiring a phone number as the ONLY lookup method is a
reasonable security/privacy-minded guardrail in principle (name+DOB alone
is a thin identity check), but the complete absence of a graceful fallback
for a proxy caller who plausibly wouldn't know that detail is a real
usability gap worth citing.

**Flag 3 — transfer fails again, 7th confirmed instance:** brief mention
only, consistent with prior occurrences.

**Status:** Complete. Valuable for both a positive finding (identity
handling) and a real gap (no lookup fallback) — good call to cite in the
final report for balance, since most other findings are negative.

---









## META-NOTE for writing the final bug report

**User's suggestion:** For findings where behavior is inconsistent (works
well in one call, fails in another), structure the writeup as a PAIRED
EXAMPLE with actual quoted dialogue from both calls side-by-side, rather
than describing each instance separately. This gives the reader concrete
evidence of the boundary condition instead of an abstract claim.

Pairs to use this structure for in the final report:
1. **Correction persistence:** Call 7 (knee/shoulder self-correction, held
   for rest of call) vs. Call 3 (pharmacy info confirmed, then re-asked
   from scratch) and/or Call 6 (name corrected, then reverted at call end).
2. **Script rigidity / adapting to patient pushback:** Call 5 (dropped DOB
   requirement immediately when patient pushed back) vs. Call 4 (continued
   through DOB verification despite patient stating "wrong office" up
   front).
3. **Clarification-seeking:** Call 4 (asked for pill color/shape when
   medication name unknown) vs. Calls 1-2 (never asked for clarification on
   vague time/date language).

Use direct quotes pulled from the transcripts above for each side of these
pairs when drafting BUG_REPORT.md.


## Running patterns to watch across remaining calls

1. **Search/availability inconsistency** — does the agent respect explicit
   time constraints given by the patient, or does it default to a different
   window? (2/2 calls so far show this bug — watching for more occurrences)
2. **Script rigidity over semantic understanding** — agent follows its
   expected next script step regardless of what the patient just said,
   rather than adjusting based on actual intent. Seen in Call 1 ("how far
   out" non-answer), Call 2 (Thursday/Friday window ignored), Call 4 (DOB
   verification run on autopilot despite patient stating wrong-office
   immediately). This may be the unifying theme across multiple "separate"
   bugs — consider whether the final report should frame this as ONE root
   cause with several symptoms rather than several unrelated bugs.
3. **Clarification-seeking is inconsistent, not absent** — agent DOES ask
   clarifying questions in some situations (e.g. Call 4: asked for pill
   color/shape when medication name unknown) but NOT in others (e.g. Calls
   1-2: never asked for clarification on vague time/date language like
   "later this week" or "how far out"). The pattern is selective, not a
   blanket absence — narrow this claim in the final report.
4. **Interruption recovery** — does it ever acknowledge/yield when it
   talks over the patient, or does it always just continue its own thread?
5. **Corrections don't reliably persist through the rest of a call** —
   Call 3: pharmacy info confirmed in full, then re-requested from scratch
   moments later, leading to unresolved call termination. Call 6: patient
   corrected the agent's name ("Mason," not "Nathan"), agent used the
   correct name for a while, then reverted to the wrong name by the end of
   the same call. Different stakes (full task failure vs. a name), but same
   underlying shape — correction accepted in the moment, not reliably
   retained. Possible STT/phonetic-similarity factor in Call 6 specifically
   ("Mason"/"Nathan" sound alike), but the broader pattern (context not
   staying corrected) is the more generalizable finding across both calls.
6. **Human transfer/escalation fails (2/2 so far)** — Call 3 and Call 4 both
   ended with the agent promising to connect the patient to a human
   representative, then immediately delivering a canned disconnect message
   instead. CAVEAT: likely a demo-environment limitation (no real rep to
   connect to in this sandbox), not necessarily indicative of production
   behavior — frame carefully in the final report rather than as a hard bug,
   but the underlying lack of a working fallback when escalation is needed
   is still worth noting.
7. **Demo-environment artifacts to mention lightly, not as major bugs:**
   - "Birthday doesn't match records, for demo purposes I'll accept it" (Calls 2-4)
   - No access to prescription/chart history (Calls 3-4)
   - Self-promotional "I'm a pretty good AI" line (Call 4) — possibly
     intentional, but odd in context

