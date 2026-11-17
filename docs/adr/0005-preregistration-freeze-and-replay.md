# ADR-0005: Pre-registration, freeze tags and cache replay

- **Status:** Accepted
- **Date:** 2026-10-16 (planned), built from 2026-10-19. Recorded retrospectively on 2026-11-16.
- **Deciders:** Max (implemented with Claude Code)

## Context

An evaluation tuned on its test set measures the tuning. The first-day plan (`63f5f02`): "Iterate
on prompts with the dev split only, then run test once with everything frozen".

## Decision

Each study is pre-registered and approved by the owner; a fingerprint of all source, the lock and
the inputs gates its test runs (`freeze.py`, `followup_freeze.py`). Tags mark the frozen commits,
and `scripts/reproduce.py` replays the cached replies and rebuilds every number in each tag's tree.

## Options Considered

### Option A: Pre-register, freeze, replay (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | High: two freeze tools, amendments, deviations, tag checks, and a rebuild from each tag's own tree |
| API cost | The pre-registered test runs once; replay and re-scoring are free, since scores come from recorded answers |
| Verifiability | High: CI checks each tag against its approval, from git's objects, and every README number against the results files |
| Reproducibility | High for what ran: every answer replays and every number rebuilds byte for byte; not a new run, nor the judges' chat sessions |

**Pros:** the result of record can't move after the fact. **Cons:** a later-found key error stays.

### Option B: Iterative evaluation (ruled out by the first-day plan)

| Dimension | Assessment |
|---|---|
| Complexity | Low: run, look, adjust, run again |
| API cost | A paid run per iteration |
| Verifiability | Low: the test score measures the tuning, and nothing fixes which run counts |
| Reproducibility | Low: each run samples anew at temperature 1 unless every reply is cached |

**Pros:** fast feedback, and errors fixed as found. **Cons:** the result can be chosen.

## Trade-off Analysis

The freeze gives up fixing the result of record so it can't drift: an integrality-rule bug, which
the [first audit](../audit/2026-11-review.md) showed cost answers, is a recorded deviation instead.

## Consequences

- Easier: CI rebuilds every number from each tag's tree with no key, so later code can't move it.
- Harder: a change under `src/opt_agent/` makes each study's `check()` refuse at HEAD (by design).
  A freeze doesn't undo exposure: NL4Opt's test problems were read to build its key, and problems
  seen in development are left out of the primary results (`2026-11-final-review.md`, M1).
- M6 had no power analysis, so its null was all but certain (first audit, finding 3); the
  follow-up has one ([`power.md`](../followup/power.md)).
- Revisit: API judges with logged requests, so the hand checks replay too (first audit, finding 9).

## Action Items

1. [x] M6 frozen 2026-11-04, the follow-up 2026-11-13; both tags checked in CI by 2026-11-15.
2. [ ] API judges with logged requests, for any new study.
