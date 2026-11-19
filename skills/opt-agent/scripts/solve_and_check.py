"""Solve a linear or integer program with CBC, solve it again with HiGHS, and check CBC's
answer by plain arithmetic. Prints a JSON report and exits 0 only for a verified optimum.

    python solve_and_check.py model.json > report.json      (or - to read stdin)

The model is JSON (see SKILL.md):
    {"variables": [{"name": "trucks", "lower": 0, "upper": null, "integer": true}],
     "objective": {"sense": "max", "terms": [{"var": "trucks", "coef": 3}]},
     "constraints": [{"name": "budget", "terms": [{"var": "trucks", "coef": 2}],
                      "sense": "<=", "rhs": 10}]}

"Verified" means: CBC and HiGHS both find an optimum with the same objective, and CBC's
values pass every bound, integrality and constraint check and reproduce the objective; for
an LP, CBC's duals also prove the optimum (a duality certificate). It says nothing about
whether the model matches the problem's text.

Needs only PuLP 4 with CBC (pip install "pulp[cbc]") and SciPy (HiGHS); no other package.
"""

import json
import math
import sys

import numpy as np
import pulp
from scipy.optimize import Bounds, LinearConstraint, milp

TOL = 1e-6  # relative, scaled by the size of the terms being added
TIME_LIMIT_S = 30
SENSES = {"<=", ">=", "==", "="}


def load(text: str) -> dict:
    """The model, with defaults filled in; ValueError listing every problem found."""
    model = json.loads(text)
    problems = []
    names = [v.get("name") for v in model.get("variables", [])]
    if not names or len(set(names)) != len(names):
        problems.append("variables need unique names, and there must be at least one")
    for v in model.get("variables", []):
        v.setdefault("lower", 0)
        v.setdefault("upper", None)
        v.setdefault("integer", False)
        low, up = v["lower"], v["upper"]
        if low is not None and up is not None and low > up:
            problems.append(f"variable '{v['name']}' has lower bound {low} > upper {up}")
    if model.get("objective", {}).get("sense") not in ("min", "max"):
        problems.append("the objective's sense must be 'min' or 'max'")
    rows = [("objective", model.get("objective", {}).get("terms", []))]
    for c in model.get("constraints", []):
        if c.get("sense") not in SENSES:
            problems.append(f"constraint '{c.get('name')}' has sense {c.get('sense')!r}")
        rows.append((f"constraint '{c.get('name')}'", c.get("terms", [])))
    for label, terms in rows:
        for t in terms:
            if t.get("var") not in names:
                problems.append(f"{label} uses undeclared variable '{t.get('var')}'")
    if problems:
        raise ValueError("; ".join(problems))
    for c in model.get("constraints", []):
        c["sense"] = "==" if c["sense"] == "=" else c["sense"]
    model.setdefault("constraints", [])
    return model


def solver_bounds(v: dict) -> tuple[float | None, float | None]:
    """An integer variable's bounds rounded inward (2.5 -> 2), as both solvers need."""
    low, up = v["lower"], v["upper"]
    if v["integer"]:
        low = None if low is None else math.ceil(low - 1e-9)
        up = None if up is None else math.floor(up + 1e-9)
    return low, up


def solve_cbc(model: dict) -> dict:
    sense = pulp.LpMaximize if model["objective"]["sense"] == "max" else pulp.LpMinimize
    problem = pulp.LpProblem("model", sense)
    if not hasattr(problem, "add_variable"):
        raise SystemExit("this script needs PuLP 4 (pip install 'pulp[cbc]>=4')")
    x = {v["name"]: problem.add_variable(f"x{i}", *solver_bounds(v),
                                         pulp.LpInteger if v["integer"] else pulp.LpContinuous)
         for i, v in enumerate(model["variables"])}  # fmt: skip
    problem.setObjective(pulp.lpSum(t["coef"] * x[t["var"]] for t in model["objective"]["terms"]))
    for i, c in enumerate(model["constraints"]):
        lhs = pulp.lpSum(t["coef"] * x[t["var"]] for t in c["terms"])
        row = lhs <= c["rhs"] if c["sense"] == "<=" else lhs >= c["rhs"] if c["sense"] == ">=" \
            else lhs == c["rhs"]  # fmt: skip
        problem.addConstraint(row, f"c{i}")
    # gapRel=0: prove the optimum. Preprocessing off: CBC's integer preprocessing once
    # returned a wrong optimum on a three-variable MIP.
    stats = problem.solve(pulp.COIN_CMD(msg=False, gapRel=0, timeLimit=TIME_LIMIT_S,
                                        options=["preprocess off"]))  # fmt: skip
    status = {pulp.LpSolveStatus.Optimal: "optimal", pulp.LpSolveStatus.GapLimit: "optimal",
              pulp.LpSolveStatus.Infeasible: "infeasible",
              pulp.LpSolveStatus.Unbounded: "unbounded",
              pulp.LpSolveStatus.TimeLimit: "timeout"}.get(stats.status, "error")  # fmt: skip
    if status != "optimal" or not stats.has_solution:
        return {"status": "error" if status == "optimal" else status}
    values = {name: var.varValue if var.varValue is not None else 0.0 for name, var in x.items()}
    duals = None
    if not any(v["integer"] for v in model["variables"]):
        # PuLP gives a max problem's duals as those of min(-objective): negated here, each is
        # d(objective)/d(rhs) of the objective as written.
        sign = -1.0 if model["objective"]["sense"] == "max" else 1.0
        pis = [problem.get_constraint_by_name(f"c{i}") for i in range(len(model["constraints"]))]
        if all(row is not None and row.pi is not None for row in pis):
            duals = {c["name"]: sign * row.pi
                     for c, row in zip(model["constraints"], pis, strict=True)}  # fmt: skip
    return {"status": "optimal", "objective": stats.objective, "values": values, "duals": duals}


def solve_highs(model: dict) -> dict:
    """The same model through SciPy's HiGHS: no PuLP, no CBC."""
    names = [v["name"] for v in model["variables"]]
    column = {name: j for j, name in enumerate(names)}
    flip = -1.0 if model["objective"]["sense"] == "max" else 1.0  # milp minimizes
    cost = np.zeros(len(names))
    for t in model["objective"]["terms"]:
        cost[column[t["var"]]] += flip * t["coef"]
    lows, ups = zip(*(solver_bounds(v) for v in model["variables"]), strict=True)
    bounds = Bounds([-np.inf if b is None else b for b in lows],
                    [np.inf if b is None else b for b in ups])  # fmt: skip
    constraints = []
    for c in model["constraints"]:
        row = np.zeros(len(names))
        for t in c["terms"]:
            row[column[t["var"]]] += t["coef"]
        low = -np.inf if c["sense"] == "<=" else c["rhs"]
        high = np.inf if c["sense"] == ">=" else c["rhs"]
        constraints.append(LinearConstraint(row, low, high))
    result = milp(cost, integrality=[int(v["integer"]) for v in model["variables"]],
                  bounds=bounds, constraints=constraints or None,
                  options={"time_limit": TIME_LIMIT_S})  # fmt: skip
    # SciPy's status 4 ("other") includes HiGHS's "infeasible or unbounded": not settled here.
    status = {0: "optimal", 1: "timeout", 2: "infeasible", 3: "unbounded"}.get(
        result.status, "error")  # fmt: skip
    if status != "optimal":
        return {"status": status}
    return {"status": "optimal", "objective": flip * result.fun,
            "values": dict(zip(names, map(float, result.x), strict=True))}  # fmt: skip


def lhs_of(terms: list[dict], values: dict) -> tuple[float, float]:
    """A linear expression's value, and the size of its terms (for a scaled tolerance)."""
    parts = [t["coef"] * values[t["var"]] for t in terms]
    return sum(parts), sum(abs(p) for p in parts)


def check(model: dict, solution: dict) -> list[str]:
    """Plain arithmetic on CBC's values: [] means every check passes."""
    values, problems = solution["values"], []
    for v in model["variables"]:
        x, low, up = values[v["name"]], v["lower"], v["upper"]
        tol = TOL * max(1.0, abs(x))
        if (low is not None and x < low - tol) or (up is not None and x > up + tol):
            problems.append(f"'{v['name']}' = {x} is outside its bounds [{low}, {up}]")
        if v["integer"] and abs(x - round(x)) > TOL:
            problems.append(f"integer variable '{v['name']}' = {x} is not a whole number")
    for c in model["constraints"]:
        lhs, size = lhs_of(c["terms"], values)
        tol = TOL * max(1.0, size, abs(c["rhs"]))
        broken = {"<=": lhs > c["rhs"] + tol, ">=": lhs < c["rhs"] - tol,
                  "==": abs(lhs - c["rhs"]) > tol}[c["sense"]]  # fmt: skip
        if broken:
            problems.append(f"constraint '{c['name']}': {lhs} {c['sense']} {c['rhs']} fails")
    objective, size = lhs_of(model["objective"]["terms"], values)
    if abs(objective - solution["objective"]) > TOL * max(1.0, size):
        problems.append(f"the objective recomputes to {objective}, not {solution['objective']}")
    if solution.get("duals") is not None:
        problems += certificate(model, solution)
    return problems


def certificate(model: dict, solution: dict) -> list[str]:
    """LP duality by arithmetic. As a minimization (a max objective negated), duals y with the
    signs each row allows give reduced costs r = c - yA, and every feasible x has
    c.x >= y.b + sum of r_j * (lower_j if r_j > 0 else upper_j). Reaching that bound (no gap)
    proves the optimum; the duals are only the witness."""
    flip = -1.0 if model["objective"]["sense"] == "max" else 1.0
    problems: list[str] = []
    reduced = {v["name"]: 0.0 for v in model["variables"]}
    for t in model["objective"]["terms"]:
        reduced[t["var"]] += flip * t["coef"]
    bound = 0.0
    for c in model["constraints"]:
        y = flip * solution["duals"][c["name"]]  # the minimization's dual
        scale = TOL * max(1.0, abs(y))
        if (c["sense"] == ">=" and y < -scale) or (c["sense"] == "<=" and y > scale):
            problems.append(f"the dual of '{c['name']}' has the wrong sign: {y}")
        for t in c["terms"]:
            reduced[t["var"]] -= y * t["coef"]
        bound += y * c["rhs"]
    for v in model["variables"]:
        r = reduced[v["name"]]
        if abs(r) <= TOL:
            continue
        edge = v["lower"] if r > 0 else v["upper"]
        if edge is None:
            problems.append(f"'{v['name']}' has reduced cost {r} against an infinite bound")
            return problems
        bound += r * edge
    value = flip * solution["objective"]
    if value - bound > TOL * max(1.0, abs(value), abs(bound)):
        problems.append(f"duality gap {value - bound}: the duals don't prove this optimum")
    return problems


def clean(x: float) -> float:
    """Drop the solver's round-off (CBC reports about 8 digits) and turn -0.0 into 0.0."""
    return round(x, 6) + 0.0


def facts(model: dict, solution: dict) -> dict:
    """The numbers an explanation may use, from a verified optimum."""
    values, slack, binding = solution["values"], {}, []
    for c in model["constraints"]:
        lhs, size = lhs_of(c["terms"], values)
        slack[c["name"]] = clean(c["rhs"] - lhs if c["sense"] == "<=" else lhs - c["rhs"])
        if abs(slack[c["name"]]) <= TOL * max(1.0, size, abs(c["rhs"])):
            binding.append(c["name"])
    duals = solution["duals"]
    prices = None if duals is None else {k: clean(v) for k, v in duals.items()}
    return {"objective": clean(solution["objective"]),
            "values": {k: clean(v) for k, v in values.items()}, "slack": slack,
            "binding": binding, "shadow_prices": prices}  # fmt: skip


def report(model: dict) -> dict:
    cbc, highs = solve_cbc(model), solve_highs(model)
    agree = cbc["status"] == highs["status"] and (cbc["status"] != "optimal" or math.isclose(
        cbc["objective"], highs["objective"], rel_tol=TOL, abs_tol=TOL))  # fmt: skip
    problems = check(model, cbc) if cbc["status"] == "optimal" else []
    verified = agree and cbc["status"] == "optimal" and not problems
    integers = [v["name"] for v in model["variables"] if v["integer"]]
    out = {"verified": verified, "cbc": cbc["status"], "highs": highs["status"],
           "solvers_agree": agree, "check_problems": problems,
           "integer_variables": integers}  # fmt: skip
    if verified:
        out["facts"] = facts(model, cbc)
    elif not agree:
        out["note"] = "CBC and HiGHS disagree: report no answer (a loud failure)"
    out["warning"] = ("Verified means CBC's answer to this model checks out, not that the model "
                      "says what the problem says. Check the model against the text.")  # fmt: skip
    return out


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    model = load(sys.stdin.read() if path == "-" else open(path).read())
    result = report(model)
    print(json.dumps(result, indent=1))
    sys.exit(0 if result["verified"] else 1)


if __name__ == "__main__":
    main()
