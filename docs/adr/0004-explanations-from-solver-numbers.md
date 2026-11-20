# ADR-0004: Explanations restricted to the solver's numbers

- **Status:** Accepted
- **Date:** 2026-10-16 (planned), built 2026-10-17. Recorded retrospectively on 2026-11-16.
- **Deciders:** Max (implemented with Claude Code)

## Context

An explanation is where an LLM can state a number the solver never produced. The first-day plan
(`63f5f02`) built it "from solver facts" and said "every number in it must match solver output".

## Decision

Only verified answers are explained, from a fixed set of solver facts; any number in the text that
isn't a correct rounding of a fact or an input is flagged ([`DESIGN.md`](../DESIGN.md), "Explain").

## Options Considered

### Option A: Facts in, every number checked (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one call with the facts, and a regular-expression number check (`explain.py`) |
| API cost | One call per verified answer; none in the studies, which skipped it |
| Verifiability | Medium: it checks where a number comes from, not whether the sentence is true ("10 trips move 1,000 fish" passes when both are facts) |
| Reproducibility | Cached and replayed like every call |

**Pros:** an invented number gets flagged. **Cons:** a false sentence of true numbers passes.

### Option B: Free-form explanations (ruled out by the first-day plan)

| Dimension | Assessment |
|---|---|
| Complexity | Lowest: one call, no checker |
| API cost | One call per answer |
| Verifiability | Low: nothing ties a number in the text to the solver |
| Reproducibility | Same as A |

**Pros:** no constraint on the writing. **Cons:** nothing stops a number the solver never produced.

## Trade-off Analysis

A catches the most checkable error, a made-up number. Placeholders that code fills in (noted in
hindsight: [first audit](../audit/2026-11-review.md), finding 10) would end those, not false claims.

## Consequences

- Easier: the demo shows each explanation next to its flags.
- Harder: it was never evaluated. Every study run skipped it (`with_explanation=False`), so what
  the code checks isn't a measured result ([README](../../README.md#limitations)).
- Gaps (first audit, finding 10): a whole number passes within 0.5 of any allowed number, ".5"
  isn't read, "1e5" reads as 1, number words go unchecked, and "36,000" for 36 thousand is flagged.
- A silently wrong answer is verified too ([ADR-0003](0003-two-solvers-and-arithmetic.md)), so its
  explanation's numbers trace to the wrong model's solution.
- Revisit: test the checker on dev's verified answers; close its gaps, or switch to placeholders.

## Action Items

1. [x] The facts-only explanation and its number check (2026-10-17).
2. [x] Evaluate it on dev under its own cap (2026-11-19, exploratory, Claude's labels:
   [`explanation_checker.md`](../analysis/explanation_checker.md)). It found no wrong number
   to catch, and false claims no number check sees, mostly about integer programs.
3. [ ] Decide on placeholders, or a check of claims about slack in integer programs.
