# Follow-up: deviations from the pre-registration

Section 7 of `docs/FOLLOWUP_PREREGISTRATION.md`: anything that runs differently from what's
written there is recorded here, with what was planned, what happened, and what it changes.

## 1. The dispute encodings' format and encoder (2026-11-15, before any encoding was written)

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
