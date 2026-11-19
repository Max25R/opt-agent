---
name: opt-agent
description: Turn a plain-English operations problem (a production mix, staffing, shipping, blending or scheduling question) into a linear or integer program, solve it with CBC, verify the answer with HiGHS and plain arithmetic, and explain it using only the solver's numbers. Use it when someone asks how much of each thing to make, buy, ship, hire or schedule to maximize or minimize something under limits.
---

# Optimization word problems, solved and verified

Work in five steps. The scripts are in this skill's `scripts/` folder (paths below are
relative to the skill's directory) and need PuLP 4 with CBC and SciPy, nothing else:
`pip install "pulp[cbc]" scipy` (on Apple Silicon, pin `cbcbox==2.929`; later builds crash).

## 1. Formulate

Write the model as JSON, one variable per decision, named for what it counts:

```json
{"variables": [{"name": "interior litres", "lower": 0, "upper": null, "integer": false}],
 "objective": {"sense": "max", "terms": [{"var": "interior litres", "coef": 4}]},
 "constraints": [{"name": "mixing hours", "terms": [{"var": "interior litres", "coef": 0.5}],
                  "sense": "<=", "rhs": 125}]}
```

- **Integrality, per variable:** integer if it counts whole things (vehicles, trips, people,
  machines, servings, items sold as units); continuous for divisible quantities (kilograms,
  litres, hours, money, "units of" a substance). This choice can change the answer, so say
  which you made.
- Variables are at least 0 unless the text says otherwise. Every requirement the text states
  is a constraint, and none it doesn't state. Use the numbers as given; 30% is 0.3.

## 2. Solve and check

```bash
python scripts/solve_and_check.py model.json > report.json
```

It solves with CBC, solves again with HiGHS (no shared code), and checks CBC's answer by
arithmetic: bounds, integrality, every constraint, the objective, and for an LP a duality
certificate from CBC's duals. Exit 0 and `"verified": true` mean all of that holds.

## 3. If it isn't verified

- **Infeasible:** compare each constraint with the text. Don't drop a requirement just to
  get an answer; some problems are infeasible as written, and saying so is the answer.
- **Unbounded:** a limit the text states is missing from the model.
- **The solvers disagree:** report no answer. A loud failure is better than a wrong one.

## 4. Explain, with the solver's numbers only

Explain a verified answer only, from `report.json`'s `facts` (values, objective, binding
constraints, slack, shadow prices) and the problem's own numbers. Then check it:

```bash
python scripts/check_explanation.py report.json model.json explanation.txt problem.txt
```

Every number it prints is backed by nothing: fix it or take it out. A number you computed
yourself (a difference, a saving) is flagged on purpose.

## 5. Warn the user

"Verified" means the answer is right **for your model**, not that the model says what the
problem says. In this project's evaluation most wrong answers passed every check: a silent
failure, with nothing to warn anyone
([results](https://github.com/Max25R/opt-agent#results)). Show the model with the answer,
and ask the user to check it against the text, especially the integrality choices.
