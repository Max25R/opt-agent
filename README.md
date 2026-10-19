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
pip install -e ".[dev]"
cp .env.example .env   # then add your ANTHROPIC_API_KEY
python -m opt_agent.data          # pinned, checksummed downloads of the datasets
python -m opt_agent.ground_truth  # rebuild data/nl4opt/ground_truth/ (committed already)
```

Solve a word problem (needs `ANTHROPIC_API_KEY`):

```bash
python -m opt_agent.agent "A fishery wants to transport their catch. ..."
```

`--attempts 1` turns off self-correction; every attempt is appended to
`logs/attempts.jsonl` (`--log` to change it).

## Running tests

```bash
pytest
ruff check .
```

Tests never call the Claude API, so they run without a key (this is also how CI runs them):
the agent's tests use a fake client. One opt-in test calls the real API
(`python -m pytest -m live -s`, a fraction of a cent each).
The property-based tests take about a minute. They explore new random problems on every
local run. In CI (`HYPOTHESIS_PROFILE=ci`) they replay a fixed set, so CI is deterministic.

## How the solver layer is verified

The solver's own word isn't trusted. Each solution is checked four independent ways:

1. **Known answers:** textbook problems (Wyndor Glass, Reddy Mikks) and hand-solved ones,
   including shadow prices checked against finite differences.
2. **Plain arithmetic:** `verify.py` rechecks bounds, integrality, every constraint, and
   the objective without any solver.
3. **A second solver:** Hypothesis generates random LPs and MIPs. CBC (via PuLP) and HiGHS
   (via SciPy) must agree on the status and the optimal objective.
4. **Metamorphic relations:** scaling the objective, flipping min/max, adding a redundant
   constraint, or reordering everything must change the answer in a known way.

Problems these checks found, each with a regression test:

- PuLP 4 returns max-problem duals with flipped signs.
- CBC mislabels some unbounded problems as infeasible, and some infeasible ones as
  unbounded. Statuses are now decided by a feasibility solve.
- CBC's integer preprocessing returned a wrong "optimal" answer on a 3-variable MIP.
  Preprocessing is now off.
- CBC can't always prove integer infeasibility over unbounded integer variables. It times
  out and reports `error` rather than guessing.

## How the agent works

1. **Formulate:** Claude turns the problem text into our `LPModel` through structured
   output. The API guarantees JSON with the schema's shape, and `schema.py` then checks
   the meaning (declared variables, sane bounds). A failure becomes a readable error.
2. **Self-correct:** if the reply is unusable, or the model is infeasible or unbounded,
   Claude gets the error back and revises (3 attempts at most). For an infeasible model
   the feedback names the conflicting constraints (an irreducible infeasible subset), and
   it warns against dropping requirements, because some problems are infeasible as
   written. If Claude returns the same model, the loop stops. Revisions that delete or
   loosen a constraint, loosen a bound, relax integrality, or flip the objective are
   flagged, and every attempt is logged as one JSONL line.
3. **Solve** with CBC, and **verify**: HiGHS must reach the same answer, and plain
   arithmetic must confirm every bound and constraint. This verifies the solution of
   Claude's model, not that the model matches the text; that's what the evaluation is for.
4. **Explain** from solver facts only: the values, the objective, which constraints bind,
   the slack, and shadow prices. Every number in Claude's explanation is checked against
   those facts and the inputs, and any that can't be traced back is flagged.

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
   the choice changes the answer, that label was set by hand (`data/nl4opt/integrality.json`).
4. **Review by hand** every problem with no optimum, a do-nothing optimum, an unlisted
   variable, an overridden `order_mapping`, or a disagreement with
   [ORLM's](https://huggingface.co/datasets/CardinalOperations/NL4OPT) GPT-4-made answers
   (`data/nl4opt/reviews.json`). Confirmed annotation errors are left out of scoring.

Every count lives in the generated
[`data/nl4opt/ground_truth/REPORT.md`](data/nl4opt/ground_truth/REPORT.md).

## Project structure

```
src/opt_agent/
  config.py        # API key loading (.env or environment)
  schema.py        # Pydantic LP/MIP schema: the contract between the LLM and the solver
  solver.py        # schema -> PuLP -> CBC; status, values, slacks, duals
  highs.py         # independent cross-check solver (SciPy's HiGHS, no PuLP)
  verify.py        # solver-free arithmetic checks of a solution
  data.py          # pinned, checksummed dataset downloads
  nl4opt.py        # NL4Opt annotation -> our schema, with every judgment call noted
  integrality.py   # integer or continuous? the label type and the rule for unlabeled problems
  ground_truth.py  # convert, solve as LP and IP, cross-check, write data + REPORT.md
  orlm.py          # cross-check against ORLM's third-party answers
  formulate.py     # problem text -> Claude (structured output) -> validated LPModel
  explain.py       # solver facts -> plain-English explanation, every number checked
  self_correct.py  # the revision loop: retry on failure, stop rules, JSONL log
  feedback.py      # what to tell Claude when an attempt fails (incl. conflicting constraints)
  changes.py       # how a revision differs from the last model; flags loosening "fixes"
  agent.py         # the pipeline (formulate + revise, solve, verify, explain) and its CLI
data/nl4opt/       # committed ground truth, hand reviews, and NL4Opt's license
scripts/           # dev_walkthrough.py: a review sheet of 30 dev problems
tests/
  problems.py      # hand-written problems with known answers
  strategies.py    # Hypothesis generators of random valid models
  fakes.py         # a fake Claude client, so tests never call the API
  test_*.py        # unit, cross-check, metamorphic, and ground-truth tests
.github/workflows/ # CI: lint + tests on every push
```

## Architecture

_TODO (milestone 7)._

## Evaluation

_TODO (milestone 6). Every number here will come from `results/eval.json`._

## Limitations

_TODO._
