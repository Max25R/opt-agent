# opt-agent

An LLM agent that turns plain-English operations/optimization problems into linear programs,
solves them with a real solver (PuLP + CBC), verifies the result, and explains it.

> **Status:** work in progress. See the roadmap below.

## Roadmap

- [x] 1. Project setup: packaging, config, tests, CI
- [x] 2. LP schema + solver, verified without trusting the solver
- [x] 3. Ground truth built from the NL4Opt annotations (no LLM)
- [x] 4. LLM formulation with Claude structured output
- [x] 5. Self-correction loop
- [ ] 6. Evaluation on the NL4Opt test set
- [ ] 7. FastAPI endpoint + demo + Docker
- [ ] 8. Polish

## Quickstart

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock   # the exact versions the ground truth was built with
pip install --no-deps -e .
cp .env.example .env   # then add your ANTHROPIC_API_KEY
python -m opt_agent.data          # pinned, checksummed downloads of the datasets
python -m opt_agent.ground_truth  # rebuild data/nl4opt/ground_truth/ (committed already)
```

Solve a word problem (needs `ANTHROPIC_API_KEY`):

```bash
python -m opt_agent.agent "A gas company can transport gas using a pipeline or by train. ..."
```

(NL4Opt dev problem 439170086. Demos and tests use dev problems only; the two test
problems used while building the agent are excluded from scoring, see
`data/nl4opt/exclusions.json`.)

`--attempts 1` turns off self-correction. Each run appends to `logs/attempts.jsonl`
(`--log` to change it): a header with the git commit and package versions, then one line
per API call with the full request, its SHA-256, and the reply. Responses are cached by
that hash in `cache/responses/` (`--cache`, or `--no-cache` to always call the API), so
re-running a request replays it instead of paying again.

## Running tests

```bash
pytest
ruff check . && ruff format --check .
```

Tests never call the Claude API, so they run without a key (this is also how CI runs them):
the agent's tests use a fake client. Three opt-in tests call the real API
(`python -m pytest -m live -s`, a fraction of a cent each); none has been run yet.
The property-based tests explore new random problems on every local run; in CI
(`HYPOTHESIS_PROFILE=ci`) they replay a fixed set, so CI is deterministic. CI installs
from `requirements.lock`, and a test fails if the installed versions differ from it, so a
SciPy (HiGHS), PuLP or CBC upgrade can't shift the ground truth unnoticed.

## How the solver layer is verified

The solver's own word isn't trusted. Every solve in the pipeline is checked three ways
at run time:

1. **Plain arithmetic** (`verify.py`): bounds, integrality, every constraint, and the
   objective, without any solver. For an LP it also checks optimality itself: CBC's own
   duals must form a certificate (the right signs, reduced costs that only push against
   finite bounds, and zero duality gap).
2. **A second solver:** CBC (via PuLP) and HiGHS (via SciPy, no PuLP) must agree on the
   status and the optimal objective. When they don't, no answer is reported.
3. **Certified statuses:** "unbounded" needs a feasible point and an improving ray (a
   direction along which the objective improves forever), both checked by arithmetic, and
   a claimed optimum is overruled only by such a ray (`rays.py`). "Infeasible" comes from
   a feasibility solve that both solvers must agree on. A time-out is reported as one.

What run-time arithmetic doesn't prove: that a MIP's optimum is optimal, and that an
infeasible model is infeasible (there's no Farkas certificate yet). Those rest on the
two solvers agreeing.

The test suite adds three more kinds of evidence:

4. **Known answers:** textbook problems (Wyndor Glass, Reddy Mikks) and hand-solved ones,
   including shadow prices checked against finite differences.
5. **Random problems:** Hypothesis generates LPs and MIPs; CBC and HiGHS must agree, and
   both must pass the run-time checks.
6. **Metamorphic relations:** scaling the objective, flipping min/max, adding a redundant
   constraint, or reordering everything must change the answer in a known way.

Problems these checks found, each with a regression test:

- PuLP 4 returns max-problem duals with flipped signs.
- CBC mislabels some unbounded problems as infeasible, and some infeasible ones as
  unbounded. Statuses are decided by a feasibility solve, and "unbounded" also needs a
  certified ray.
- CBC's integer preprocessing returned a wrong "optimal" answer on a 3-variable MIP.
  Preprocessing is now off.
- CBC can't always prove integer infeasibility over unbounded integer variables. It hits
  its time limit and reports `timeout` rather than guessing.
- With free variables, CBC (on an LP) and HiGHS (on a MIP) each claimed "optimal" for an
  unbounded model, but only in one variable order. Found by the reordering test; fixed by
  the improving-ray check, not by changing solver settings (turning off CBC's scaling
  caused new false optima).

## How the agent works

1. **Formulate:** Claude turns the problem text into our `LPModel` through structured
   output. The API guarantees JSON with the schema's shape, and `schema.py` then checks
   the meaning (declared variables, sane bounds). A failure becomes a readable error.
2. **Self-correct:** if the reply is unusable, or the model is infeasible or unbounded
   (by both solvers' verdict), Claude gets the error back and revises (3 attempts at
   most). For an infeasible model the feedback names the conflicting constraints (an
   irreducible infeasible subset), and it warns against dropping requirements, because
   some problems are infeasible as written. The loop stops without revising when Claude
   returns the same model, refuses, or when the failure isn't Claude's: the solvers
   disagree, one times out, or the API call fails (then the problem counts as failed).
   Revisions that delete or loosen a constraint (its right-hand side, direction, or
   coefficients), loosen a bound, relax integrality, remove a variable, drop one from the
   objective, or flip the objective are flagged. Every attempt is logged as one JSONL line.
3. **Solve and verify** with both solvers and the checks above. An answer is *confirmed*
   when they agree and the checks pass (for any status), and *verified* when it's also an
   optimum. This is about the solution of Claude's model, not whether the model matches
   the text; that's what the evaluation is for.
4. **Explain** verified answers only, from solver facts: the values, the objective, which
   constraints bind, the slack, and shadow prices. Every number in the explanation must be
   a correct rounding of a fact or an input, or it's flagged. That checks where a number
   comes from, not whether the sentence is true: "10 trips move 1,000 fish" passes when 10
   and 1,000 are both facts. A refused, cut-off or empty explanation is flagged too.

## Ground truth

NL4Opt's test set has human-annotated formulations but no answers. Rather than borrow a
third-party answer key, `ground_truth.py` builds one from the raw annotations:

1. **Convert** each annotation to our schema (`nl4opt.py`). The semantics follow the
   official baseline's converter, except in two places where that code is mathematically
   wrong; the competition never solved the models, so its bugs went unnoticed.
2. **Reject, never repair** annotations that contradict themselves or the text: one
   variable annotated twice, empty terms, or an operator that contradicts the wording
   ("more than" annotated as <=). Mentions resolve by the variable name they contain, so a
   wrong `order_mapping` is overridden, with a note.
3. **Solve twice, then pick:** NL4Opt doesn't say which variables are integers, so every
   problem is solved as an LP and as an all-integer program, each cross-checked with
   HiGHS and plain arithmetic. A per-problem integrality label picks the answer. Wherever
   the choice changes the answer the label is a hand label (`data/nl4opt/integrality.json`),
   elsewhere a rule sets it.
4. **Accept strict wording either way:** the annotation scheme has no strict operators, so
   "more than" is annotated as >=. For integer problems the answer with that wording read
   strictly (x > y as x >= y + 1) is stored too, and either is accepted (`strict.py`).
5. **Review by hand** every problem with no optimum, a do-nothing optimum, an unlisted
   variable, an overridden `order_mapping`, or a disagreement with
   [ORLM's](https://huggingface.co/datasets/CardinalOperations/NL4OPT) GPT-4-made answers
   (`data/nl4opt/reviews.json`).
6. **Score only what's trusted:** a problem is scorable if it converted, its answer is
   confirmed by HiGHS and the arithmetic checks, no annotation error found in review
   changes it, and it wasn't used while building the agent (`exclusions.json`).

**Who decided what.** Claude (the AI model that wrote this code) wrote every hand review and
most hand labels; the owner decided the rest and confirms Claude's work:

- *Dev split:* the owner set the integrality labels for the problems in the dev
  walkthrough, and confirmed (and corrected) the dev reviews, except one that was written
  after the walkthrough. The other dev hand labels are Claude's.
- *Test split:* every hand label and every review is Claude's, and none is confirmed yet.
  The owner is labeling a blind random sample (`review/integrality_blind/`) and checking
  every test review (`review/test_reviews/`) before any test run, under the rules in
  [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md) (a draft, not yet approved).

Every count, including who labeled and confirmed what, lives in the generated
[`data/nl4opt/ground_truth/REPORT.md`](data/nl4opt/ground_truth/REPORT.md).

## Project structure

```
src/opt_agent/
  config.py        # API key loading (.env or environment)
  schema.py        # Pydantic LP/MIP schema: the contract between the LLM and the solver
  solution.py      # what a solver returns: status, values, slacks, duals
  solver.py        # schema -> PuLP -> CBC
  highs.py         # independent cross-check solver (SciPy's HiGHS, no PuLP)
  verify.py        # solver-free checks of a solution, incl. an LP duality certificate
  rays.py          # is a claimed optimum real? an improving ray, checked by arithmetic
  data.py          # pinned, checksummed dataset downloads
  nl4opt.py        # NL4Opt annotation -> our schema, with every judgment call noted
  integrality.py   # integer or continuous? the label type and the rule for unlabeled problems
  strict.py        # the strict reading of "more than" over integers
  ground_truth.py  # convert, solve as LP and IP, cross-check, write data + REPORT.md
  orlm.py          # cross-check against ORLM's third-party answers
  api.py           # every Claude call: one request, timed retries, response cache
  runs.py          # a run's id, JSONL log, and environment (git commit, package versions)
  formulate.py     # problem text -> Claude (structured output) -> validated LPModel
  explain.py       # solver facts -> plain-English explanation, every number traced
  self_correct.py  # the revision loop: retry on failure, stop rules, logging
  feedback.py      # what to tell Claude when an attempt fails (incl. conflicting constraints)
  changes.py       # how a revision differs from the last model; flags loosening "fixes"
  agent.py         # the pipeline (formulate + revise, solve, verify, explain) and its CLI
  stats.py         # Wilson intervals, exact McNemar, Holm correction
  packets.py       # hand-check packets for the owner, and their agreement statistics
data/nl4opt/       # committed ground truth, hand reviews, labels, exclusions, NL4Opt's license
docs/              # PREREGISTRATION.md: the evaluation's rules, fixed before the test run
review/            # packets for the owner's blind labels and review checks
scripts/           # dev_walkthrough.py: a review sheet of 30 dev problems
tests/
  problems.py      # hand-written problems with known answers
  strategies.py    # Hypothesis generators of random valid models
  fakes.py         # a fake Claude client, so tests never call the API
  test_*.py        # unit, cross-check, metamorphic, and ground-truth tests
requirements.lock  # exact versions of every package; CI installs from it
.github/workflows/ # CI: lint, format check, tests on every push
```

## Architecture

_TODO (milestone 7)._

## Evaluation

_TODO (milestone 6). Every number here will come from `results/eval.json`._

## Limitations

_TODO._
