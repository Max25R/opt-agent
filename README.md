# opt-agent

An LLM agent that turns plain-English operations/optimization problems into linear programs,
solves them with a real solver (PuLP + CBC), verifies the result, and explains it.

> **Status:** work in progress. See the roadmap below.

## Roadmap

- [x] 1. Project setup: packaging, config, tests, CI
- [x] 2. LP schema + solver, verified without trusting the solver
- [x] 3. Ground truth built from the NL4Opt annotations (no LLM)
- [ ] 4. LLM formulation with Claude tool use
- [ ] 5. Self-correction loop
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

## Running tests

```bash
pytest
ruff check .
```

Tests never call the Claude API, so they run without a key (this is also how CI runs them).
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

## Ground truth

NL4Opt's test set has human-annotated formulations but no answers. Rather than borrow a
third-party answer key, `ground_truth.py` builds one from the raw annotations:

1. **Convert** each annotation to our schema (`nl4opt.py`). The semantics follow the
   official baseline's converter, except in two places where that code is mathematically
   wrong; the competition never solved the models, so its bugs went unnoticed.
2. **Reject, never repair** annotations that contradict themselves or the text: a mention
   mapped to the wrong variable, one variable annotated twice, empty terms, or an operator
   that contradicts the wording ("more than" annotated as <=).
3. **Solve twice:** NL4Opt doesn't say which variables are integers, so every problem is
   solved as an LP and as an all-integer program. Both answers are kept; each is
   cross-checked with HiGHS and plain arithmetic.
4. **Review by hand** every problem with no optimum, a do-nothing optimum, or a
   disagreement with [ORLM's](https://huggingface.co/datasets/CardinalOperations/NL4OPT)
   GPT-4-made answers (`data/nl4opt/reviews.json`). Confirmed annotation errors are left
   out of scoring.

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
  ground_truth.py  # convert, solve as LP and IP, cross-check, write data + REPORT.md
  orlm.py          # cross-check against ORLM's third-party answers
data/nl4opt/       # committed ground truth, hand reviews, and NL4Opt's license
scripts/           # dev_walkthrough.py: a review sheet of 30 dev problems
tests/
  problems.py      # hand-written problems with known answers
  strategies.py    # Hypothesis generators of random valid models
  test_*.py        # unit, cross-check, metamorphic, and ground-truth tests
.github/workflows/ # CI: lint + tests on every push
```

## Architecture

_TODO (milestone 7)._

## Evaluation

_TODO (milestone 6). Every number here will come from `results/eval.json`._

## Limitations

_TODO._
