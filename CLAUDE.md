# opt-agent

An LLM agent that turns plain-English operations problems into linear/integer programs,
solves them with a real solver, verifies the result independently, and explains it using
the solver's own numbers. A portfolio project for AI-engineering co-op applications. The
point is a trustworthy evaluation, not a demo.

## How to work on this repo

- The owner (a CS + Industrial Engineering student) has to explain every line in
  interviews. Work **one milestone at a time**: briefly explain each design choice, keep
  code simple and readable, and stop after each milestone for review. Don't start the next
  milestone without a go-ahead.
- End every milestone with the exact `git add` / `git commit` / `git push` commands.
- Match the existing style: small, well-named functions; comments explain *why*.
- Don't trust a solver's word: anything solver-related gets a known-answer test, a
  plain-arithmetic check, a CBC-vs-HiGHS cross-check, or a metamorphic test.

## Hard rules

- **No made-up numbers.** Every number in the README comes from `results/eval.json`
  (milestone 6 adds a test that enforces this).
- Tests for the schema, solver, and ground-truth layers **never call the Claude API**.
- Report failures honestly. If something (e.g. self-correction) doesn't help, say so.
- Bulk eval runs use a small, cheap model. Check current model IDs and prices in the docs
  before writing API code.

## Plan and status

1. [x] Setup: src layout, pyproject, `.env` handling, pytest + ruff CI.
2. [x] LP schema + solver, verified with known answers, plain-arithmetic checks,
   Hypothesis CBC-vs-HiGHS agreement, and metamorphic tests.
3. [ ] Ground truth from raw annotations (no LLM). NL4Opt's `generation_data/*.jsonl` has
   human-annotated formulations but **no objective values**. Convert the annotations to
   our schema, solve them, and record every assumption (integrality isn't annotated:
   record both LP and integer optima). List unconvertible or suspect problems. Use any
   third-party answer set only as a cross-check. Walk the owner through 30 dev problems.
4. [ ] LLM formulation via Claude tool use / structured output. The explanation is built
   from solver facts (binding constraints, slacks, shadow prices); every number in it
   must match solver output.
5. [ ] Self-correction loop (max 3 attempts) on validation errors or infeasible/unbounded
   results. Raw JSONL log of every attempt. Flag "fixes" that delete or loosen
   constraints.
6. [ ] Evaluation. Iterate on prompts with the dev split only, then run test once with
   everything frozen. Conditions: no-solver baseline, single-shot, self-correction, plus
   a perturbed-numbers set. Report Wilson CIs, McNemar's test, the silent-vs-loud failure
   split, p50/p95 latency, and cost from real token usage. Use a hash-keyed response
   cache and a hand-labeled error taxonomy. Prepare a blind-grading packet.
7. [ ] FastAPI `POST /solve` + one HTML page + Dockerfile.
8. [ ] README polish: diagram, results table, reproducing from the cache without a key,
   limitations, repo description/topics.

## Commands

```bash
source .venv/bin/activate
python -m pytest              # ~50 s; property tests explore new random cases each run
HYPOTHESIS_PROFILE=ci python -m pytest   # deterministic, as in CI
ruff check . && ruff format .
```

## Gotchas (learned the hard way)

- **PuLP 4.0** changed its API: `prob.add_variable(name, low, up, cat)`,
  `prob.constraints()` is a method, the CBC class is `COIN_CMD` (there's no
  `PULP_CBC_CMD`), and `solve()` returns an `LpSolveStats`.
- **CBC comes from `cbcbox`, pinned to 2.929.** 2.931+ crash on Apple Silicon because a
  bundled dylib has an invalid code signature.
- **PuLP 4 flips dual signs for max problems.** `solver.py` negates them, and a
  finite-difference test checks this.
- **CBC integer preprocessing is off.** It returned a wrong "optimal" answer on a
  3-variable MIP (`CBC_PREPROCESS_BUG` in `tests/problems.py`).
- **CBC's infeasible/unbounded labels are unreliable**, so both solvers settle them with a
  zero-objective feasibility solve.
- CBC reports values to ~8 significant digits, so tolerances scale with the size of the
  terms being added (`verify.tolerance_for`).
- CBC can time out (status `error`) proving integer infeasibility over unbounded integer
  variables. That's expected; the random generator bounds integer variables.
- Don't keep the repo or its `.venv` under iCloud: iCloud hides `.pth` files and
  Python 3.13 then skips them.

## Open decisions (ask the owner)

- License (none yet).
- Whether to file the CBC preprocessing bug upstream (coin-or/Cbc).
