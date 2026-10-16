"""Check a solution with plain arithmetic. No solver is involved, so solver bugs can't hide."""

from opt_agent.schema import LPModel, Term, evaluate, magnitude
from opt_agent.solver import Solution, Status

TOLERANCE = 1e-6


def check_solution(model: LPModel, solution: Solution, tol: float = TOLERANCE) -> list[str]:
    """Return human-readable problems with an optimal solution; [] means it checks out.

    Only optimal solutions carry values to check. (Proving a problem infeasible would need
    a certificate; the CBC-vs-HiGHS cross-check covers statuses instead.)
    """
    if solution.status is not Status.OPTIMAL:
        return []
    missing = [v.name for v in model.variables if v.name not in solution.values]
    if missing:
        return [f"no value for variable '{name}'" for name in missing]
    return (
        _bound_violations(model, solution.values, tol)
        + _integrality_violations(model, solution.values, tol)
        + _constraint_violations(model, solution.values, tol)
        + _objective_mismatch(model, solution, tol)
    )


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
