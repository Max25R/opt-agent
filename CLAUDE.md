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
3. [x] Ground truth from raw annotations (no LLM). Done 2026-10-16; the owner confirmed
   the dev walkthrough and their corrections are applied. NL4Opt has formulations but **no
   answers**. `ground_truth.py` converts them, solves each as an LP and as an all-integer
   IP, cross-checks with HiGHS and arithmetic, and compares with ORLM. Flagged problems
   carry a hand review, and each problem's integrality label picks its answer
   (`ground_truth.answer`). Counts are in the generated `REPORT.md`.
4. [x] LLM formulation (2026-10-17). `formulate.py` sends the problem through
   `messages.create` with structured output (`output_config.format`, using the SDK's
   public `anthropic.transform_schema(LPModel)`), then validates it with our own
   `LPModel`, so a bad reply becomes a readable `error` for milestone 5. `explain.py`
   builds facts from the solver and flags any number in the explanation that isn't a
   correct rounding of a fact or input. `agent.py` runs the pipeline and has a CLI.
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

## Claude API notes

- `formulate.DEFAULT_MODEL = "claude-haiku-5-5"`: the owner asked for a small, cheap
  model for bulk eval runs. Check model IDs and prices in the docs before changing it.
- Every API call takes a `client` argument, and tests pass `tests/fakes.FakeClient`.
  Only `tests/test_live.py` (marker `live`, excluded by default and in CI) calls the real
  API. Run it with `python -m pytest -m live` when `ANTHROPIC_API_KEY` is set.
- `.env` doesn't exist in this checkout (it's git-ignored); the owner adds their key.
- `Result.verified` means the solution of Claude's model is optimal and independently
  confirmed. It says nothing about whether the model matches the text; that's milestone 6.

## Commands

```bash
source .venv/bin/activate
python -m pytest              # ~50 s; property tests explore new random cases each run
HYPOTHESIS_PROFILE=ci python -m pytest   # deterministic, as in CI
ruff check . && ruff format .
python -m opt_agent.data            # pinned, SHA-256-checked downloads (git-ignored)
python -m opt_agent.ground_truth    # rebuild data/nl4opt/ground_truth/ (~30 s)
python scripts/dev_walkthrough.py   # rebuild the 30-problem dev review sheet
python -m opt_agent.agent "problem text"   # needs ANTHROPIC_API_KEY
python -m pytest -m live            # the one test that calls the real API
```

## Ground truth (milestone 3 decisions)

- **Annotation errors are rejected, never repaired.** That covers one variable annotated
  twice, empty terms, two mentions resolving to one variable, and operators that
  contradict the wording. A repair would be our reading presented as theirs.
- **Mentions resolve by the variable name they contain** ("economical mobile phone" ->
  economical). `order_mapping` decides only when the name doesn't, and every override is
  noted. This rescued 3 problems where `order_mapping` was wrong and changed nothing else.
- **Integrality:** both optima are stored (`lp`, `ip`), and a per-problem label picks the
  answer. Wherever integrality changes the answer, the label is a hand label in
  `data/nl4opt/integrality.json` (source `owner` or `claude`). Elsewhere the rule in
  `integrality.py` labels it (source `rule`), which agrees with all 9 owner labels. The
  owner's criteria: countable objects, trips, ads, machines, people and servings are
  integer; mass, volume, area, time, money and "units of" a substance are continuous.
  Before using rule labels to grade an agent's integrality choice (not just to pick
  answers), review them.
- `data/nl4opt/reviews.json` is **hand-written input**. Every problem with no optimum, a
  do-nothing optimum, an ORLM disagreement, an unlisted variable, or an overridden
  `order_mapping` must have a review (the report and the tests enforce this). For an
  unlisted variable, neither 0 nor 1 is a safe default. `scorable()` excludes annotation
  errors that change the answer (`answer_affected`); `blind_gradable()` excludes every
  annotation error. Dev #4 (471112257) is scorable but not blind-gradable (owner's call). Dev reviews are owner-confirmed; test reviews are Claude's, pending
  confirmation.
- ORLM's answers (CC BY-NC 4.0) are a cross-check only and are **never committed**.
- After changing the converter or the solver, rebuild the ground truth.
  `test_highs_reproduces_every_committed_answer` fails if the data has drifted.

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
- python.org's macOS Python has no CA certificates, so downloads pass `certifi`'s bundle
  explicitly (`data.py`).

## Settled decisions

- No license for this repo (owner's call, 2026-10-16).
- Don't file the CBC preprocessing bug upstream (owner's call, 2026-10-16).
