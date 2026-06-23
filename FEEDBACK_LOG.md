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

## Call 3 — [scenario TBD]
**Call ID:**
**Duration:**

[Add as you go]

---

## Running patterns to watch across remaining calls

1. **Search/availability inconsistency** — does the agent respect explicit
   time constraints given by the patient, or does it default to a different
   window? (2/2 calls so far show this bug — watching for more occurrences)
2. **No clarification-seeking behavior** — agent has not asked a single
   clarifying question across calls so far; it always picks an interpretation
   and proceeds rather than checking. Relevant for scenario 07 (self-correction)
   and 09 (contradictory info) specifically.
3. **Interruption recovery** — does it ever acknowledge/yield when it
   talks over the patient, or does it always just continue its own thread?
