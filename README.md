# opt-agent

An LLM agent that turns plain-English operations/optimization problems into linear programs,
solves them with a real solver (PuLP + CBC), verifies the result, and explains it.

> **Status:** work in progress. See the roadmap below.

## Roadmap

- [x] 1. Project setup: packaging, config, tests, CI
- [x] 2. LP schema + solver, verified without trusting the solver
- [ ] 3. Ground truth built from the NL4Opt annotations (no LLM)
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

## Project structure

```
src/opt_agent/
  config.py        # API key loading (.env or environment)
  schema.py        # Pydantic LP/MIP schema: the contract between the LLM and the solver
  solver.py        # schema -> PuLP -> CBC; status, values, slacks, duals
  highs.py         # independent cross-check solver (SciPy's HiGHS, no PuLP)
  verify.py        # solver-free arithmetic checks of a solution
tests/
  problems.py      # hand-written problems with known answers
  strategies.py    # Hypothesis generators of random valid models
  test_*.py        # unit, cross-check, and metamorphic tests
.github/workflows/ # CI: lint + tests on every push
```

## Architecture

_TODO (milestone 7)._

## Evaluation

_TODO (milestone 5). Every number here will come from `results/eval.json`._

## Limitations

_TODO._
