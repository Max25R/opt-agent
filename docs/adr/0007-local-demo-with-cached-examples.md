# ADR-0007: A local Docker demo with cached examples

- **Status:** Accepted
- **Date:** 2026-10-16 (planned), built 2026-11-15. Recorded retrospectively on 2026-11-16.
- **Deciders:** Max (implemented with Claude Code)

## Context

Milestone 7 of the first-day plan (`63f5f02`): "FastAPI `POST /solve` + one HTML page + Dockerfile".
A visitor has no key, and each live call spends the owner's credit (ADR-0006).

## Decision

A local app (`src/opt_agent/demo/`). Examples mode, the default, replays four original examples
from committed replies through `api.ReplayOnlyClient`, with no key and nothing sent. Live mode needs
`OPT_AGENT_LIVE=1` and a key, and is guarded: one solve at a time, 4,000 characters, 8,000 tokens
per reply, and a dollar cap ($0.50 by default).

## Options Considered

### Option A: A local app in Docker, with cached examples (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Medium: two modes, live guards, an image, and a CI job that builds and smoke-tests it |
| API cost | None in examples mode; caching the examples' replies cost $0.0139, once ([`HANDOFF.md`](../HANDOFF.md), "Spend") |
| Verifiability | High: each example has a hand-checked answer that a test re-derives with both solvers, and the page says whether the verified answer matches it |
| Reproducibility | High: the examples replay from committed replies |

**Pros:** anyone can run it, with no key and no spend. **Cons:** it needs Docker or Python.

### Option B: A hosted public demo (noted in hindsight)

| Dimension | Assessment |
|---|---|
| Complexity | High: hosting, plus the hardening for a public endpoint that live mode lacks |
| API cost | Every visitor's new text is a paid call against the owner's $10 monthly limit |
| Verifiability | The same pipeline, but new text has no hand-checked answer |
| Reproducibility | New text gets one sample at temperature 1; only repeats replay from the live cache |

**Pros:** nothing to install. **Cons:** open-ended spend and exposure on a student's budget.

## Trade-off Analysis

Known examples with cached replies show the pipeline honestly at no cost; hosting adds reach but
makes the spend limit public. No record weighs it: the [first audit](../audit/2026-11-review.md)
(finding 6) only listed what a public `/solve` would meet.

## Consequences

- Easier: CI builds the image, replays an example, and checks live mode won't start without a key.
- Harder: the live cap's ledger is inside the container, so each `docker run --rm` starts at zero
  unless a volume holds `/app/logs` (README; documented, not built). Every example solves on its
  first attempt, so self-correction never shows; live mode is guarded, not hardened (README).
- Revisit: an example whose first model fails; hosting, only with per-visitor limits and one ledger.

## Action Items

1. [x] App, image, CI smoke test and the examples' replies (2026-11-15); the cap note (2026-11-16).
2. [ ] An example that shows the fix step (a paid run, the owner's). Tried 2026-11-19: three
   candidates with units or percentage traps, five samples each, and all 15 first models were
   right ([`fix_step_tries.json`](../analysis/fix_step_tries.json)), so none was added.
