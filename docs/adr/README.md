# Architecture decision records

ADRs for opt-agent's key design decisions, each dated when the decision was made: 0001-0007 were
recorded retrospectively on 2026-11-16, and later ones are recorded when they're made.
[`docs/DESIGN.md`](../DESIGN.md) says how the system works; these say why, what else was on the
table, and what each choice cost. The results they point to are in `results/eval.json` and
`results/followup.json`, written up in the [README](../../README.md#results).

| ADR | decision | decided (built) |
|---|---|---|
| [0001](0001-fixed-pipeline-bounded-self-correction.md) | A fixed pipeline with a bounded self-correction loop, not a free-acting agent | 2026-10-16 (2026-10-19) |
| [0002](0002-structured-model-not-solver-code.md) | Claude emits a structured model (a JSON schema), not solver code | 2026-10-16 (2026-10-17) |
| [0003](0003-two-solvers-and-arithmetic.md) | CBC, HiGHS and plain arithmetic, not one solver's word | 2026-10-16 (extended 2026-10-19) |
| [0004](0004-explanations-from-solver-numbers.md) | Explanations restricted to the solver's numbers, not free-form | 2026-10-16 (2026-10-17) |
| [0005](0005-preregistration-freeze-and-replay.md) | Pre-registration, freeze tags and cache replay, not iterative evaluation | 2026-10-16 (2026-10-19 to 2026-11-15) |
| [0006](0006-haiku-under-a-budget.md) | Claude Haiku 5.5 under a $20 budget, not a larger model | 2026-10-16 (confirmed 2026-10-28) |
| [0007](0007-local-demo-with-cached-examples.md) | A local Docker demo with cached examples, not a hosted one | 2026-10-16 (2026-11-15) |
| [0008](0008-static-demo-computed-at-build-time.md) | A static copy of the examples page, computed when CI builds it, not in the browser | 2026-11-18 (2026-11-18) |
| [0009](0009-what-limits-an-integer-program.md) | The solver's own test of what limits an integer program, given to the explainer, not slack alone | 2026-11-20 (2026-11-20) |

Each has the same parts: status, date, deciders, context, decision, the options (each rated on
complexity, API cost, verifiability and reproducibility), the trade-off, the consequences and the
action items. They cite the first-day plan (`CLAUDE.md` as first committed, `63f5f02`), the
[history](../HISTORY.md), the [first audit](../audit/2026-11-review.md) (2026-11-08) and the
[final review](../audit/2026-11-final-review.md) (2026-11-15). An option marked **noted in
hindsight** is one that no record shows was weighed when the decision was made.

## Future work

The ADRs' "revisit" items:

- A revision trigger that reaches silent failures. The checklist revision was inconclusive, and
  self-consistency over k samples is untested ([0001](0001-fixed-pipeline-bounded-self-correction.md)).
- Whether the flat schema costs accuracy on larger models, and indexed sets if it does
  ([0002](0002-structured-model-not-solver-code.md)).
- Exact certificates (Farkas for infeasibility), an arithmetic check of HiGHS's solution, and a
  model-level check against a reference ([0003](0003-two-solvers-and-arithmetic.md)).
- The explanation checker's blind spot that its dev evaluation found (claims about slack in
  integer programs), or placeholders instead ([0004](0004-explanations-from-solver-numbers.md)):
  the explainer now gets the solver's facts about it ([0009](0009-what-limits-an-integer-program.md)),
  and on dev, by the same rule, the explanations with such a false claim went 13 → 4, and by
  the explanation checker's own labels 22 → 11 (exploratory:
  [`limits_claims.md`](../analysis/limits_claims.md)).
- Judges called through the API with logged requests, so the hand checks replay too
  ([0005](0005-preregistration-freeze-and-replay.md)).
- A model ladder, one weaker and one stronger model, each under its own pre-registration and cap
  ([0006](0006-haiku-under-a-budget.md)).
- A demo example whose first model fails, so the fix step shows; hosting only with per-visitor
  limits and one lasting spend ledger ([0007](0007-local-demo-with-cached-examples.md)).
