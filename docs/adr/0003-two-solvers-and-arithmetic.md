# ADR-0003: Two solvers and plain arithmetic, not one solver's word

- **Status:** Accepted
- **Date:** 2026-10-16 (milestone 2), extended 2026-10-19. Recorded retrospectively on 2026-11-16.
- **Deciders:** Max (implemented with Claude Code)

## Context

A solver's "optimal" is a claim too. The first-day rule (`63f5f02`): "Don't trust a solver's word",
so anything solver-related gets a known-answer, arithmetic, CBC-vs-HiGHS or metamorphic test.

## Decision

CBC (through PuLP) solves; HiGHS (through SciPy) must agree on status and objective; arithmetic
checks CBC's point, with a duality certificate for an LP and a certified ray for "unbounded". A
disagreement is a loud failure, never an answer. Details: [`DESIGN.md`](../DESIGN.md).

## Options Considered

### Option A: CBC, HiGHS and arithmetic (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | High: two solver stacks, certificates, rays, feasibility solves and scaled tolerances |
| API cost | None: every check is local |
| Verifiability | High for the solution: an LP's optimum is proved; a MIP's rests on two solvers agreeing |
| Reproducibility | Pinned solvers (CBC from `cbcbox` 2.929); CI reproduces on macOS arm64, since on Linux CBC picks another optimal solution for one follow-up model |

**Pros:** it found real solver bugs, each now a regression test. **Cons:** more code, two solvers.

### Option B: One solver, trusted (rejected by the first-day rule)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one solve |
| API cost | None |
| Verifiability | Low: CBC's wrong "optimal" under integer preprocessing, its mislabeled statuses and its false optima could have reached the answers |
| Reproducibility | Same as A |

**Pros:** simple and fast. **Cons:** nothing catches the solver's mistakes.

## Trade-off Analysis

A guards against the solver being wrong, which the tests and an audit caught several times and
the studies never saw ([`DESIGN.md`](../DESIGN.md)); neither option sees the model being wrong.

## Consequences

- Easier: "confirmed" means something exact: both solvers agree and every check passes.
- Harder: the cross-check never fired in either study ([README](../../README.md#limitations)), and
  a model that misreads the text passes every check, failing silently (first audit, finding 2).
- Gaps ([first audit](../audit/2026-11-review.md), section 3 and finding 6): a MIP's optimum and
  an infeasible model rest on agreement (no Farkas certificate), arithmetic checks CBC's point but
  not HiGHS's, and rays and duals are checked within tolerances an ill-conditioned model can fool.
- Revisit: exact certificates, a check of HiGHS's point, and a model-level check (finding 5).

## Action Items

1. [x] Both solvers and the checks (2026-10-16); certified rays and LP certificates (2026-10-19).
2. [ ] Exact certificates, Farkas included, and an arithmetic check of HiGHS's solution.
