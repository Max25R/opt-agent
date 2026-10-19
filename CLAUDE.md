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
5. [x] Self-correction loop (2026-10-19; built and tested with `FakeClient` only, since
   there's no API key yet). `self_correct.solve_with_revisions`: up to 3 attempts. Each
   revision is a self-contained request (problem + previous reply + feedback), so every
   attempt can be logged, cached, and replayed alone. Stops on optimal, the attempt limit,
   an unchanged model (Claude stands by it), a refusal, a solver time-out or error, a
   CBC/HiGHS disagreement, or an API error; only the first three are Claude's doing.
   `max_attempts=1` is the single-shot baseline. Feedback is sent only when both solvers
   agree. Infeasibility feedback names an IIS (deletion filter,
   `feedback.conflicting_constraints`, which first confirms the whole set is infeasible).
   `changes.compare` flags deleted or loosened constraints (rhs, direction, or
   coefficients), loosened bounds, relaxed integrality, removed variables, variables
   dropped from the objective, and a flipped objective.
   - **Pre-milestone-6 fixes (2026-10-19, from a health check; Batches A-D):**
     certified rays and LP duality certificates (`rays.py`, `verify.optimality_problems`);
     `Status.TIMEOUT`; `answer()`/`scorable()` require a trusted answer; one request
     dict per call with pinned settings, our own timed retries, and a response cache
     (`api.py`); a run log with git SHA and package versions (`runs.py`); dev-only
     fixtures and two excluded test problems; the strict reading (`strict.py`);
     `Result.confirmed`; the owner's packets (`review/`, `packets.py`); a draft
     pre-registration (`docs/PREREGISTRATION.md`); `requirements.lock`.
   - **Still open before milestone 6:** the owner marks `review/integrality_blind/`
     (first: the review packet shows labels), `review/test_reviews/`, and
     `review/says_lp.md`, and approves the pre-registration (its 4 decisions were made on
     2026-10-19; it's still a draft). Apply their marks: `confirmed_by_owner` for
     confirmed reviews, source `owner` for labels. Milestone 6 must implement, before
     approval: the "=" reading for the 3 ambiguous problems (accepted like the strict
     one), the baseline's answer schema and parsing (pre-registration 2a), and the
     1e-4 sensitivity count. Run the live tests once there's a key. Known and
     unfixed: the integrality rule matches ingredient names ("units of chicken" meat), so
     it labels countable products continuous in at least 3 reviewed test problems
     (bubble teas, crepes, curry bowls; harmless for the annotated answers; fix after the
     owner's labels, and check the unreviewed rule labels too); `DEV_WALKTHROUGH.md` predates the owner's milestone 3
     corrections (the owner decides whether to regenerate it); no Farkas certificate for
     infeasible LPs; the CLI needs a key even when every call is cached (milestone 8);
     freezing data and prompt hashes at the start of a test run (milestone 6).
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
- Every API call goes through `api.call`: the request is built once
  (`formulate.build_request`, `explain.build_request`), and that same dict is sent,
  hashed (`request_sha256`, the cache key), cached, and logged. Thinking and effort are
  pinned (`api.THINKING`, `api.EFFORT`): adaptive thinking with its text omitted, and
  medium effort, Haiku 5.5's current defaults. Haiku 5.5 rejects `thinking: enabled`
  with a budget, and temperature can only be 1, so a run is reproducible only by replaying
  the cache. The SDK's retries are off (`with_options(max_retries=0)`); `api.call` retries
  with the SDK's own rule so retry time is measured. A call that still fails comes back as
  `CallInfo.error`, never as an exception.
- Every API call takes a `client` argument, and tests pass `tests/fakes.FakeClient`
  (which returns real `anthropic.types.Message` objects, so they can be cached). Only
  `tests/test_live.py` (marker `live`, excluded by default and in CI) calls the real API,
  and it uses dev problems only.
- `.env` exists in the owner's checkout (git-ignored). Claude never reads or commits it.
- `Result.confirmed`: CBC and HiGHS agree and the checks pass, for any status.
  `Result.verified`: confirmed and optimal. Both are about the solution of Claude's model,
  not whether the model matches the text; that's milestone 6. A flagged revision can be
  "verified" too, which is why the flags exist.
- **None of the live tests has run yet** (no key as of 2026-10-19). When the owner has
  a key: `python -m pytest -m live -s` runs all three; fix anything that breaks before
  starting milestone 6's paid runs.

## Commands

```bash
source .venv/bin/activate
pip install -r requirements.lock && pip install --no-deps -e .   # the locked versions
python -m pytest              # ~75 s; property tests explore new random cases each run
HYPOTHESIS_PROFILE=ci python -m pytest   # deterministic, as in CI
ruff check . && ruff format .            # CI runs ruff format --check
python -m opt_agent.data            # pinned, SHA-256-checked downloads (git-ignored)
python -m opt_agent.ground_truth    # rebuild data/nl4opt/ground_truth/ (~55 s)
python scripts/dev_walkthrough.py   # rebuild the 30-problem dev review sheet
python -m opt_agent.packets integrality|reviews|agreement   # the owner's packets
python -m opt_agent.agent "problem text"   # needs ANTHROPIC_API_KEY
python -m pytest -m live -s         # the tests that call the real API (not in CI)
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
  answers), review them. **Provenance:** the 9 owner labels are dev problems; every other
  hand label (the rest of dev, and all of test) is Claude's. The owner is checking a blind
  sample of 40 test labels (`review/integrality_blind/`, seed 20261019).
- **Strict wording** ("more than"; the scheme has no strict operators, so it's annotated
  as >=): for integer problems, `Record.strict` stores the answer with each noted
  constraint read strictly (`strict.py`), and `matching_reading` accepts either reading
  and says which one matched.
- **Exclusions:** test problems used while building the agent are not scorable
  (`data/nl4opt/exclusions.json`: the fishery and ads problems). Demos, fakes and live
  tests use dev problems only.
- `answer()` returns None (and `scorable()` False) unless HiGHS agrees and the
  arithmetic checks pass.
- `data/nl4opt/reviews.json` is **hand-written input**. Every problem with no optimum, a
  do-nothing optimum, an ORLM disagreement, an unlisted variable, or an overridden
  `order_mapping` must have a review (the report and the tests enforce this). For an
  unlisted variable, neither 0 nor 1 is a safe default. `scorable()` excludes annotation
  errors that change the answer (`answer_affected`); `blind_gradable()` excludes every
  annotation error. Dev #4 (471112257) is scorable but not blind-gradable (owner's call).
  **Provenance:** Claude wrote every review. The owner confirmed 11 of the 12 dev reviews
  (not 1670020945, written after the walkthrough); all 62 test reviews are unconfirmed and
  in the owner's packet (`review/test_reviews/`, least sure first).
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
- **Both solvers can claim a false optimum** when free variables let the objective run away,
  in one variable order only (`CBC_FREE_VARIABLE_BUG`, `HIGHS_FREE_VARIABLE_BUG`). CBC's log
  says "Unscaled problem has dual infeasibilities". `-scaling off` fixes that case but caused
  new false optima (3 in 4000 random models), so don't use it. Instead, every claimed optimum
  must survive an improving-ray check (`rays.py`): the same solver looks for a ray in a
  bounded LP, and any ray it finds is verified by arithmetic, scaled to a largest entry
  of 1 (so a near-zero direction can't hide in a tolerance) and by a long step from a
  checked feasible point. "Unbounded" is only ever reported with such a ray.
- **A CBC/HiGHS disagreement is a loud failure:** `Result.verified` is False, nothing is
  explained (only verified answers are), and the CLI prints "SOLVERS DISAGREE". A time-out
  is not a disagreement: it's shown as "NO ANSWER" first. For an LP, the arithmetic checks
  now prove optimality too (a duality certificate from CBC's duals); for a MIP they check
  feasibility only, and optimality rests on the cross-check.
- CBC reports values to ~8 significant digits, so tolerances scale with the size of the
  terms being added (`verify.tolerance_for`).
- CBC can time out (status `timeout`) proving integer infeasibility over unbounded integer
  variables. That's expected; the random generator bounds integer variables.
- **CBC gives no value to a variable that appears only in the objective** when the
  objective is zeroed (the feasibility solve). `solver._value_or_any_in_bounds` fills one in.
- **SciPy's `milp` status 4 means "other"**: HiGHS's "infeasible or unbounded" (common for
  MIPs), but also its solve errors. Status 1 is the time limit. So 2, 3 and 4 are settled
  by a feasibility solve and a certified ray, or else become `error`.
- **anthropic 1.15 uses `httpx2`**, not `httpx`; tests build API errors from
  `SimpleNamespace` responses (`tests/fakes.status_error`).
- Don't keep the repo or its `.venv` under iCloud: iCloud hides `.pth` files and
  Python 3.13 then skips them.
- python.org's macOS Python has no CA certificates, so downloads pass `certifi`'s bundle
  explicitly (`data.py`).

## Settled decisions

- No license for this repo (owner's call, 2026-10-16).
- Don't file the CBC preprocessing bug upstream (owner's call, 2026-10-16).
