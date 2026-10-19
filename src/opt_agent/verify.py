"""Check a solution with plain arithmetic. No solver is involved, so solver bugs can't hide."""

from opt_agent.schema import LPModel, Term, evaluate, magnitude
from opt_agent.solution import Solution, Status

TOLERANCE = 1e-6


def check_solution(model: LPModel, solution: Solution, tol: float = TOLERANCE) -> list[str]:
    """Return human-readable problems with an optimal solution; [] means it checks out.

    Only optimal solutions carry values to check: feasibility, the objective, and, for an
    LP with duals, optimality itself (optimality_problems). A MIP's optimality and the
    other statuses rest on the CBC-vs-HiGHS cross-check and certified rays (rays.py).
    """
    if solution.status is not Status.OPTIMAL:
        return []
    missing = [v.name for v in model.variables if v.name not in solution.values]
    if missing:
        return [f"no value for variable '{name}'" for name in missing]
    return (
        feasibility_problems(model, solution.values, tol)
        + _objective_mismatch(model, solution, tol)
        + optimality_problems(model, solution, tol)
    )


def optimality_problems(model: LPModel, solution: Solution, tol: float = TOLERANCE) -> list[str]:
    """LP duality by plain arithmetic: do the solver's duals prove the solution optimal?

    Write the problem as a minimization (negate a max objective). Duals y with the sign
    each row allows (>= 0 on a >= row, <= 0 on a <= row, any sign on ==) give the reduced
    costs r = c - yA, and every feasible point x then satisfies

        c.x  >=  y.b + sum over j of r_j * (lower_j if r_j > 0 else upper_j),

    provided each nonzero r_j pushes against a finite bound. If the solution reaches that
    bound (zero duality gap), nothing feasible beats it. The duals are the solver's, but
    they're only the witness; the proof is this arithmetic. [] if there are no duals (MIPs).
    """
    if solution.duals is None or model.is_mip or solution.status is not Status.OPTIMAL:
        return []
    sign = 1.0 if model.objective.sense == "min" else -1.0
    y, problems = _duals_of_min_form(model, solution.duals, sign, tol)
    reduced, scale = _reduced_costs(model, y, sign)
    bound = [y[c.name] * c.rhs for c in model.constraints]
    for v in model.variables:
        r = reduced[v.name]
        limit = v.lower if r > 0 else v.upper
        if limit is not None:
            bound.append(r * limit)
        elif abs(r) > tol * scale[v.name]:
            side = "lower" if r > 0 else "upper"
            problems.append(f"reduced cost of '{v.name}' is {r:g}, but it has no {side} bound")
    if problems:
        return problems
    terms = model.objective.terms
    gap = sign * evaluate(terms, solution.values) - sum(bound)
    allowed = tol * max(1.0, magnitude(terms, solution.values), sum(map(abs, bound)))
    if abs(gap) > allowed:
        return [f"the duals leave a duality gap of {gap:g}: optimality isn't proven"]
    return []


def _duals_of_min_form(
    model: LPModel, duals: dict[str, float], sign: float, tol: float
) -> tuple[dict[str, float], list[str]]:
    """Each dual in min form, clipped to the sign its row allows. A wrong sign within
    round-off is clipped (that keeps the bound valid); a bigger one is a problem."""
    y = {c.name: sign * duals[c.name] for c in model.constraints}
    allowed = tol * max([1.0, *map(abs, y.values())])
    problems = []
    for c in model.constraints:
        right = {"<=": min(y[c.name], 0.0), ">=": max(y[c.name], 0.0), "==": y[c.name]}[c.sense]
        if abs(y[c.name] - right) > allowed:
            problems.append(
                f"shadow price of '{c.name}' is {duals[c.name]:g}: the wrong sign for a "
                f"{c.sense} constraint in a {model.objective.sense} problem"
            )
        y[c.name] = right
    return y, problems


def _reduced_costs(
    model: LPModel, y: dict[str, float], sign: float
) -> tuple[dict[str, float], dict[str, float]]:
    """r = c - yA in min form, and the size of the numbers each r_j came from."""
    reduced = {v.name: 0.0 for v in model.variables}
    scale = {v.name: 1.0 for v in model.variables}
    for t in model.objective.terms:
        reduced[t.var] += sign * t.coef
        scale[t.var] += abs(t.coef)
    for c in model.constraints:
        for t in c.terms:
            reduced[t.var] -= y[c.name] * t.coef
            scale[t.var] += abs(y[c.name] * t.coef)
    return reduced, scale


def feasibility_problems(
    model: LPModel, values: dict[str, float], tol: float = TOLERANCE, integrality: bool = True
) -> list[str]:
    """Bound, constraint (and, unless told otherwise, integrality) violations of a point."""
    problems = _bound_violations(model, values, tol)
    if integrality:
        problems += _integrality_violations(model, values, tol)
    return problems + _constraint_violations(model, values, tol)


def same_answer(model: LPModel, a: Solution, b: Solution) -> bool:
    """Do two solutions of the same model agree on status and, if optimal, objective?

    A time-out or an error is no answer, so it never agrees with anything, not even
    another one. The tolerance is the larger of the two solutions' own, so that
    same_answer(a, b) and same_answer(b, a) can't differ.
    """
    if a.failed or b.failed or a.status != b.status:
        return False
    if a.status is not Status.OPTIMAL:
        return True
    terms = model.objective.terms
    tol = max(tolerance_for(terms, a.values), tolerance_for(terms, b.values))
    return abs(a.objective - b.objective) <= tol


def tolerance_for(terms: list[Term], values: dict[str, float], tol: float = TOLERANCE) -> float:
    """Round-off allowed in a sum of terms.

    CBC reports values to ~8 significant digits, so the error in a sum grows with the size
    of the terms, even when they cancel to a small result.
    """
    return tol * max(1.0, magnitude(terms, values))


def _bound_violations(model: LPModel, values: dict[str, float], tol: float) -> list[str]:
    problems = []
    for v in model.variables:
        x = values[v.name]
        if v.lower is not None and x < v.lower - tol * max(1.0, abs(v.lower)):
            problems.append(f"variable '{v.name}' = {x} is below its lower bound {v.lower}")
        if v.upper is not None and x > v.upper + tol * max(1.0, abs(v.upper)):
            problems.append(f"variable '{v.name}' = {x} is above its upper bound {v.upper}")
    return problems


def _integrality_violations(model: LPModel, values: dict[str, float], tol: float) -> list[str]:
    return [
        f"integer variable '{v.name}' = {values[v.name]} is not an integer"
        for v in model.variables
        if v.integer and abs(values[v.name] - round(values[v.name])) > tol
    ]


def _constraint_violations(model: LPModel, values: dict[str, float], tol: float) -> list[str]:
    return [
        f"constraint '{c.name}' is violated by {-c.slack(values):g}"
        for c in model.constraints
        if c.slack(values) < -tolerance_for(c.terms, values, tol)
    ]


def _objective_mismatch(model: LPModel, solution: Solution, tol: float) -> list[str]:
    recomputed = evaluate(model.objective.terms, solution.values)
    allowed = tolerance_for(model.objective.terms, solution.values, tol)
    if solution.objective is None or abs(solution.objective - recomputed) > allowed:
        return [f"reported objective {solution.objective} but the values give {recomputed}"]
    return []
