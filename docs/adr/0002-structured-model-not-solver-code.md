# ADR-0002: Claude emits a structured model, not solver code

- **Status:** Accepted
- **Date:** 2026-10-16 (the schema), built 2026-10-17. Recorded retrospectively on 2026-11-16.
- **Deciders:** Max (implemented with Claude Code)

## Context

Two solvers, an arithmetic checker and a diff between attempts all need Claude's model as data
([ADR-0003](0003-two-solvers-and-arithmetic.md)). The first-day plan (`63f5f02`) said "tool use /
structured output"; `schema.py` (milestone 2) is "the contract between the LLM and the solver".

## Decision

Claude fills in `LPModel` through structured output (`formulate.build_request`); `schema.py` checks
its meaning, and a failed reply goes back to Claude as a readable error. Nothing Claude writes runs.
Strict tool use would carry the same schema; `HISTORY.md` records the choice (milestone 4), not why.

## Options Considered

### Option A: Structured output into a typed `LPModel` (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one Pydantic schema that rejects unknown keys and NaN; nothing to sandbox |
| API cost | One call per attempt |
| Verifiability | High: the model is data, so it's validated, solved by both solvers, checked by arithmetic and diffed between attempts (`changes.compare`) |
| Reproducibility | High: replies are JSON, cached by request; since 2026-11-09 the cache key leaves out the SDK-built schema, so an SDK upgrade doesn't miss the cache |

**Pros:** safe, cacheable, checkable and diffable. **Cons:** no indexed sets or nonlinear terms.

### Option B: Claude writes solver code (noted in hindsight)

| Dimension | Assessment |
|---|---|
| Complexity | High: model-written PuLP or Pyomo code has to run somewhere safe |
| API cost | One call per attempt, plus revisions for code that fails to run (never measured) |
| Verifiability | Lower: the model exists only once the code runs; the solvers and the diff need it extracted |
| Reproducibility | Depends on the library versions the code imports |

**Pros:** indexed sets, loops, anything the library expresses. **Cons:** running LLM-written code.

## Trade-off Analysis

The schema limits Claude to what every checker understands, which is what makes the checks work.
The [first audit](../audit/2026-11-review.md) (section 3) found that fine at NL4Opt's size and named
code as the alternative; whether the follow-up's harder problems need more wasn't measured.

## Consequences

- Easier: one model feeds both solvers, the checks, the change flags and the demo's display.
- Harder: a reply that doesn't give a valid model is a loud failure; in the follow-up, these were
  the solver conditions' only loud failures (`results/followup.json`, `loud_failures_by_kind`).
  Every coefficient is written out, so a big model is a long reply.
- Revisit: whether the flat schema costs accuracy on larger models; indexed sets if it does.

## Action Items

1. [x] The schema (2026-10-16), structured output (2026-10-17), a schema-free cache key (2026-11-09).
2. [ ] Measure the schema's limits on larger models.
