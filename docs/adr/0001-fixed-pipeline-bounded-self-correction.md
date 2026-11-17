# ADR-0001: A fixed pipeline with a bounded self-correction loop

- **Status:** Accepted
- **Date:** 2026-10-16 (planned), built 2026-10-19. Recorded retrospectively on 2026-11-16.
- **Deciders:** Max (implemented with Claude Code)

## Context

The first-day plan (`63f5f02`) set a "Self-correction loop (max 3 attempts)". The evaluation
compares conditions, so they must differ in one step, and each paid call needs a known worst
case ([ADR-0006](0006-haiku-under-a-budget.md)).

## Decision

A fixed sequence (formulate, solve, verify, explain: [`DESIGN.md`](../DESIGN.md)) with a bounded
loop of at most 3 attempts (`self_correct.MAX_ATTEMPTS`). It revises only an unusable reply or an
infeasible or unbounded model, and stops if Claude returns it unchanged. Single-shot: 1 attempt.

## Options Considered

### Option A: A fixed pipeline with a bounded loop (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one path through `agent.run`; the stop rules fit in a list ([`HISTORY.md`](../HISTORY.md), milestone 5) |
| API cost | Bounded: at most 3 formulation calls per answer, each reserved at its worst case before it's sent |
| Verifiability | High: every attempt is one JSONL line, and a revision that deletes or loosens a constraint is flagged (`changes.py`) |
| Reproducibility | High: a revision is a self-contained request (problem, previous reply, feedback), so it's cached and replays alone |

**Pros:** the conditions nest and share their first reply. **Cons:** only loud failures revise.

### Option B: A free-acting agent (noted in hindsight)

| Dimension | Assessment |
|---|---|
| Complexity | Higher: tools, and a loop in which Claude decides when it's done; never built |
| API cost | Open-ended: Claude picks how many calls, so only a cap bounds it |
| Verifiability | Lower: each problem takes its own path, so a condition isn't one procedure |
| Reproducibility | Replays only along the recorded path |

**Pros:** it could re-read the text or probe its own model. **Cons:** no fixed conditions.

## Trade-off Analysis

A buys a clean experiment, since conditions differ only where they revise. Its price is reach:
it fires on loud failures, and most failures were silent ([README](../../README.md#limitations)).

## Consequences

- Easier: paired comparisons at half the cost: self-correction's first attempt is single-shot's
  cached reply ([first audit](../audit/2026-11-review.md), section 3).
- Harder: it can't fix a model that solves. On the NL4Opt test run no revision changed an outcome
  (first audit, finding 2); in the follow-up, of single-shot's unusable replies it revised, one
  became right and the rest silently wrong (README, Limitations).
- Revisit: a trigger that reaches silent failures; the checklist revision was inconclusive (H1).

## Action Items

1. [x] The loop, its IIS feedback and change flags (2026-10-19); an estimate flag (2026-11-09).
2. [ ] A pre-registered test of another trigger, such as self-consistency over k samples.
