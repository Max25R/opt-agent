# Follow-up: deviations from the pre-registration

Section 7 of `docs/FOLLOWUP_PREREGISTRATION.md`: anything that runs differently from what's
written there is recorded here, with what was planned, what happened, and what it changes.

## 1. The dispute encodings' format and encoder (2026-11-15, before any encoding was written)

**Superseded by deviation 2:** the check wasn't performed, so no encoding was written in
this format or any other.

**Planned.** `docs/followup/judge_prompt.md` (frozen) describes the encoding as "one block of
plain text": each variable with its meaning, type and bounds; the objective; each constraint
with a name, every term, its sense and right-hand side. 5b, step 1 says only that the
encoding is written from the text alone and that its author is recorded.

**What's done instead.** The encoder (Gemini on the web, a fresh chat per problem, given only
the packet; the owner's choice) replies with one JSON object: the model in the project's own
format (`schema.LPModel`), a meaning for every variable, any objective constant, and the
readings it chose. The judges receive that JSON, laid out with indentation, in place of a
plain-text block. The prompt's own text is unchanged.

**Why.** The JSON is solved exactly as the judges confirmed it
(`scripts/dispute_packets.py`, `encoding_model`). A plain-text model would have to be retyped
before the solve, and a retyping error would put a model the judges never saw behind the
certificate.

**What it changes.** The judges see the same elements in another layout; nothing about keys,
answers or the conditions reaches them or the encoder. The encoder is from a third vendor,
neither Anthropic (the agent, the judge of record) nor OpenAI (the second judge). A reply
that doesn't validate never reaches a judge; it goes back to the encoder with the reason, and
the sheet records it.

## 2. The key-dispute check (5b) wasn't performed (decided 2026-11-15)

**Planned.** Section 5b: a problem whose key at least 3 of the 4 conditions' majority answers
agree against is checked. An encoding written from the text alone, confirmed by both blinded
judges, solved for a certificate and checked by arithmetic, can overturn its key. Overturned
keys feed a corrected-key row, applied to all four conditions alike; the raw key stays the
result of record.

**What happened.** 15 problems met the trigger (`followup_report.json`'s `disputes`):
`complexlp:14`, `complexlp:25`, `complexlp:63`, `complexlp:78`, `complexlp:81`, `complexlp:83`, `complexlp:94`, `industryor:17`, `industryor:22`, `industryor:26`, `industryor:27`, `industryor:30`, `industryor:31`, `industryor:32`, `industryor:41`.
The check wasn't run: no encoding was written and no judge saw anything. **Decided by the
owner on 2026-11-15, for time**, after the results were written up but before any encoding
or judging, so no part of the check's outcome was seen or could have shaped the decision.

**What it changes.**
- **No corrected-key row.** The report has none (`corrected_keys` is empty), and none will be
  added.
- **The result of record doesn't change.** It was always the raw keys, as pre-registered:
  every accuracy, contrast and verdict in `RESULTS.md` and the README stands as it is.
- **What stays unknown.** Some of these 15 failures may be key errors rather than errors by
  the conditions (in M6, both judges called 6 of NL4Opt's 8 shared failures answer-key
  errors). If so, accuracy is understated for every condition that gave the trigger answer;
  how H1 and H2 would move is unknown, since the conditions that agree differ from problem
  to problem.
- **Deviation 1 is superseded**, and the dispute plan (`review/followup_disputes/README.md`)
  is marked not run. Its packets stay git-ignored and its script
  (`scripts/dispute_packets.py`) stays, so the check can still be run later; anything it
  finds then would be exploratory and post hoc, never the result of record.
