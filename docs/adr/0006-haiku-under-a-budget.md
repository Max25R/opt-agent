# ADR-0006: Claude Haiku 5.5 under a $20 budget

- **Status:** Accepted
- **Date:** 2026-10-16 (small model), confirmed 2026-10-28. Recorded retrospectively on 2026-11-16.
- **Deciders:** Max (implemented with Claude Code)

## Context

The owner has $20 of API credit in all and a $10 monthly spend limit (`CLAUDE.md`, "Budget",
2026-10-28). The first-day rule (`63f5f02`): "Bulk eval runs use a small, cheap model."

## Decision

`claude-haiku-5-5` in every condition of both studies (`formulate.DEFAULT_MODEL`), with pinned
settings. Every live call goes through `budget.BudgetedClient`, which reserves the call's worst
case first and refuses a call that could cross the cap.

## Options Considered

### Option A: Claude Haiku 5.5 (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one pinned model string and settings (`api.THINKING`, `api.EFFORT`) |
| API cost | M6 projected at about $0.71 (high $2.06); the project has spent $3.89 of the $20 in all ([`HANDOFF.md`](../HANDOFF.md), "Spend") |
| Verifiability | The same checks as for any model |
| Reproducibility | Temperature can only be 1, so a run reproduces only by replaying its cache |

**Pros:** both studies and the demo fit the credit. **Cons:** every result is one small model's.

### Option B: A larger model (Sonnet 5.5, weighed on 2026-10-28)

| Dimension | Assessment |
|---|---|
| Complexity | Low: the same code, another model string |
| API cost | M6 projected at $14.29, high $41.19: about twice the whole credit ([`HISTORY.md`](../HISTORY.md), milestone 5) |
| Verifiability | The same checks |
| Reproducibility | Replay from the cache, as for A |

**Pros:** a stronger model's results. **Cons:** its high projection alone exceeds the credit.

## Trade-off Analysis

Sonnet's high case exceeded the whole credit; in hindsight, Haiku also left room for the
follow-up's 3 samples per problem. A stronger model also risks the ceiling NL4Opt showed, where
Haiku 5.5's direct answers matched the solver conditions ([README](../../README.md#results)).

## Consequences

- Easier: the whole project cost less than a fifth of the credit.
- Harder: every number is Haiku 5.5's ([README](../../README.md#limitations)), so whether another
  model changes either finding is unknown. The [first audit](../audit/2026-11-review.md) (section 3)
  said to add a second model in the follow-up; the follow-up used Haiku 5.5 alone.
- Revisit: a model ladder, one weaker and one stronger (noted in hindsight: first audit, section 3).

## Action Items

1. [x] One pinned model; the budget guard (2026-10-28), on the agent CLI too since 2026-11-16.
2. [x] Prices re-checked before each paid run (`pricing.PRICES_CHECKED`).
3. [ ] A second model, under its own pre-registration and cap.
