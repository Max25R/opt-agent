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
- [x] 6. Evaluation on the NL4Opt test set
- [ ] 7. FastAPI endpoint + demo + Docker
- [ ] 8. Polish

## Quickstart

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock   # the exact versions the ground truth was built with
pip install --no-deps -e .
cp .env.example .env   # then add your ANTHROPIC_API_KEY (read only with OPT_AGENT_LIVE=1)
python -m opt_agent.data          # pinned, checksummed downloads of the datasets
python -m opt_agent.ground_truth  # rebuild data/nl4opt/ground_truth/ (committed already)
```

Solve a word problem (needs `ANTHROPIC_API_KEY` exported, or `OPT_AGENT_LIVE=1` to use the
key in `.env`; without one of them nothing can spend):

```bash
OPT_AGENT_LIVE=1 python -m opt_agent.agent "A gas company can transport gas using a pipeline or by train. ..."
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
(`OPT_AGENT_LIVE=1 python -m pytest -m live -s`, a fraction of a cent each); they first
passed on 2026-10-28.
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
- HiGHS returned a fractional value (2.5) for an integer variable with a fractional bound,
  which made the cross-check report a false disagreement (found by the audit). Both solvers
  now get integer bounds rounded inward, and an integer variable with no whole number in its
  bounds is infeasible by arithmetic.

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
   Revisions that delete or loosen a constraint (its right-hand side or coefficients), flip
   a constraint's direction, change an equation at all, loosen a bound, relax integrality,
   remove a variable, drop one from the objective or negate its coefficient there, or flip
   the objective are flagged. Constraints are compared by structure, so a renamed, reordered
   or rewritten row isn't a change. Every attempt is logged as one JSONL line.
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
most hand labels. The owner decided the rest. Claude's work was checked by the owner on dev,
and by LLM judges on test:

- *Dev split:* the owner set the integrality labels for the problems in the dev
  walkthrough, and confirmed (and corrected) the dev reviews, except one that was written
  after the walkthrough. The other dev hand labels are Claude's.
- *Test split:* every hand label and every review is Claude's. Two LLM judges from
  different vendors checked them instead of the owner (pre-registration, Amendment 2):
  - **Integrality labels:** they labeled a blind sample and the "says LP" problems. Where
    they disagree, either answer is accepted.
  - **Reviews:** they judged the reviews that an external cross-check against
    ORLMBenchmark couldn't cover. Accuracy is also reported without the reviews they
    disputed, and the hard cases they didn't confirm are excluded.

  All of this was settled under the rules in
  [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md), which was approved and frozen
  (`docs/FREEZE.json`) before any test run.

Every count, including who labeled and confirmed what, lives in the generated
[`data/nl4opt/ground_truth/REPORT.md`](data/nl4opt/ground_truth/REPORT.md).

## Project structure

```
src/opt_agent/
  config.py        # API key loading (the environment; .env only with OPT_AGENT_LIVE=1)
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
docs/              # PREREGISTRATION.md: the evaluation's rules, frozen before the test run
  amendments/      # Amendment 3 and the deviations note
review/            # hand-check packets, the judges' replies, and the filled-in sheets
scripts/
  dev_walkthrough.py  # a review sheet of 30 dev problems
  blind_taxonomy.py   # the blinded taxonomy prompt for both judges, and merging their replies
  amendment3.py       # Amendment 3's exploratory row, added to runs/test/report.json
  eval_json.py        # results/eval.json, the source of every number in the Evaluation section
results/           # eval.json
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

The NL4Opt test split has 274 scorable problems, and every condition used Claude Haiku 5.5.
The inputs (prompts, code, data and ground truth) were frozen before the run, and the
analysis was pre-registered ([`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md)). An
answer is correct if its status and objective match the answer key (relative tolerance
1e-6). Every number in this section comes from [`results/eval.json`](results/eval.json),
and a test checks it.

| condition | accuracy (95% Wilson) | silent / loud failures | perturbed set (n = 240) | cost | latency p50 / p95 |
|---|---|---|---|---|---|
| no-solver baseline | 96.4% (93.4–98.0%) | 10 / 0 | 97.1% | $0.124 | 3.8 s / 8.1 s |
| single-shot | 96.4% (93.4–98.0%) | 10 / 0 | 96.7% | $0.150 | 3.6 s / 6.7 s |
| self-correction | 96.4% (93.4–98.0%) | 10 / 0 | 97.1% | $0.167 | 3.7 s / 9.5 s |
| *exploratory, post hoc:* answer-key errors counted as correct | 98.5% (96.3–99.4%) in each | | | | |

**No detectable difference on NL4Opt.** All three conditions got 264 of 274 right. None of
the 6 pre-registered McNemar tests comes close (every p = 1, with at most 3 discordant
pairs in any comparison). That isn't evidence that the conditions are equivalent. But the
baseline, which answers directly with no solver, matched the solver conditions. That
suggests NL4Opt is saturated as a test of what a solver adds.

**Most shared failures are answer-key errors (exploratory, post hoc).** 8 problems were
wrong in all three conditions. Two LLM judges labeled each failure on its own, and both
called 6 of the 8 answer-key errors: a key that is wrong, or that rejects a reading the
text supports. Counting those 6 as correct gives 98.5% in every condition, which leaves 4
real failures per condition. This row was added after the results were seen, and it is
not a pre-registered result.

**Same score, different failures.** By the judge of record's labels, the baseline's 4
remaining failures are 2 missing constraints, 1 arithmetic slip and 1 wrong coefficient.
The solver conditions' 4 are 2 integrality errors, 1 invented constraint (a stated
preference, "prefers", made a requirement) and the same wrong coefficient. With 4 failures
per condition, this is a description, not a finding.

**0 loud failures, and why that's not reassuring.** Every answer from the solver
conditions was confirmed: CBC and HiGHS agreed, and the arithmetic checks passed. But
verification checks the solution of Claude's own formulation, not whether that formulation
matches the text. So every modeling error passed every check, and all 10 failures per
condition were silent.

**No sign of memorization.** On 240 problems with their numbers changed and their answers
recomputed, accuracy held (96.7–97.1%). No condition gave the original problem's answer to
any changed problem.

**Self-correction barely mattered.** It revised 23 answers across both runs and changed 1
outcome. It cost 7% more than single-shot across both runs (11% on the test run).

**Limitations.**
- **The judges aren't independent proof.** The judge of record is Claude, the same model
  family as the agent, and both judges saw the same inputs and row-pairing hints, so their
  20/20 agreement isn't independent proof.
- **One answer counted as correct has a bug.** Of the 6 answers that count as correct,
  `431521997`'s model has an error that doesn't change its answer (an upper limit
  replaced by a trivial constraint), and blind grading graded it wrong.
- **The answer key can be wrong without the score showing it.** On `-2001553884` the
  reference model leaves out a land limit. The limit doesn't bind, so the score can't see
  the error.
- **"Prefers" is a systematic weakness.** Reading a stated preference as a requirement
  cost one problem in both solver conditions. The same mistake turned up in a model
  that was scored right, because there the constraint doesn't bind.
- **Blind grading.** Blind grading agreed with the automatic score on 29 of 30 models
  scored right and 5 of 10 scored wrong. All 5 wrong-side disagreements are the answer-key
  errors above; the 1 right-side disagreement is a correct answer from a model with a
  non-binding bug.

**Cost.** Both test runs together (the main one and the perturbed one) cost $0.52 in API
calls.

**The rules.**
- Amendments 1 and 2 are at the end of the
  [pre-registration](docs/PREREGISTRATION.md#amendments).
- Amendment 3 (the exploratory row and blinded judge prompts) and a
  [note on deviations](docs/amendments/DEVIATIONS.md) are in
  [`docs/amendments/`](docs/amendments/).

## Limitations

_TODO._
