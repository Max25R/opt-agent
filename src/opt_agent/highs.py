"""Independent cross-check: solve the same LPModel with SciPy's HiGHS (no PuLP, no CBC).

Two unrelated solvers agreeing on status and optimal objective makes a bug in our PuLP
translation, or in CBC itself, very unlikely to go unnoticed.
"""

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from opt_agent.rays import certified_ray, describe
from opt_agent.schema import LPModel, Term
from opt_agent.solution import Solution, Status

HIGHS_TIME_LIMIT_SECONDS = 30

# scipy.optimize.milp status codes
_OPTIMAL = 0
_LIMIT = 1  # "iteration or time limit"; we set no iteration limit, so it's the time limit
# SciPy documents 4 as "other": HiGHS's "infeasible or unbounded" (common for MIPs), but also
# its solve errors. So 2, 3 and 4 are all ERROR until a check settles them.
_INFEASIBLE, _UNBOUNDED, _OTHER = 2, 3, 4


def solve_with_highs(model: LPModel) -> Solution:
    """HiGHS's answer, with the same rule as CBC: a claimed optimum stands only if no
    improving ray, found by HiGHS itself, refutes it."""
    claimed = _solve_once(model)
    if claimed.status is Status.OPTIMAL:
        ray = certified_ray(model, claimed.values, _solve_once)
        if ray is not None:
            note = f"HiGHS claimed an optimum, but the objective improves along {describe(ray)}"
            return Solution(solver="highs", status=Status.UNBOUNDED, note=note)
    return claimed


def _solve_once(model: LPModel) -> Solution:
    sign = -1.0 if model.objective.sense == "max" else 1.0  # milp always minimizes
    costs = sign * _row(model.objective.terms, model)
    result = _run_milp(model, costs)
    if result.status in (_INFEASIBLE, _UNBOUNDED, _OTHER):
        return _infeasible_or_unbounded(model)
    if result.status == _LIMIT:
        return _timed_out("solving")
    if result.status != _OPTIMAL:
        return Solution(solver="highs", status=Status.ERROR)

    values = {v.name: float(x) for v, x in zip(model.variables, result.x, strict=True)}
    return Solution(
        solver="highs",
        status=Status.OPTIMAL,
        objective=sign * result.fun,
        values=values,
        slacks={c.name: c.slack(values) for c in model.constraints},
    )


def feasible(model: LPModel) -> bool | None:
    """Does any point satisfy every bound and constraint? None if HiGHS can't tell.

    With a zero objective the problem can't be unbounded, so this is the one question.
    """
    status = _feasibility(model)[0]
    return {Status.OPTIMAL: True, Status.INFEASIBLE: False}.get(status)


def _feasibility(model: LPModel) -> tuple[Status, dict[str, float] | None]:
    """HiGHS's answer to "is there any feasible point?" (OPTIMAL means yes), with the point."""
    result = _run_milp(model, np.zeros(len(model.variables)))
    if result.status == _OPTIMAL:
        point = {v.name: float(x) for v, x in zip(model.variables, result.x, strict=True)}
        return Status.OPTIMAL, point
    statuses = {_INFEASIBLE: Status.INFEASIBLE, _LIMIT: Status.TIMEOUT}
    return statuses.get(result.status, Status.ERROR), None


def _infeasible_or_unbounded(model: LPModel) -> Solution:
    """Same rule as for CBC (see solver.py): a feasibility solve decides, and "unbounded"
    needs an improving ray certified from the feasible point it returns; otherwise ERROR."""
    status, point = _feasibility(model)
    if status is Status.INFEASIBLE:
        return Solution(solver="highs", status=Status.INFEASIBLE)
    if status is Status.TIMEOUT:
        return _timed_out("deciding feasibility")
    if status is not Status.OPTIMAL:
        return Solution(
            solver="highs", status=Status.ERROR, note="HiGHS couldn't decide feasibility"
        )
    ray = certified_ray(model, point, _solve_once)
    if ray is None:
        note = (
            "HiGHS found no optimum for a feasible model, and no certified ray shows it unbounded"
        )
        return Solution(solver="highs", status=Status.ERROR, note=note)
    note = f"feasible, and the objective improves forever along {describe(ray)}"
    return Solution(solver="highs", status=Status.UNBOUNDED, note=note)


def _timed_out(doing: str) -> Solution:
    note = f"HiGHS hit its {HIGHS_TIME_LIMIT_SECONDS} s time limit while {doing}"
    return Solution(solver="highs", status=Status.TIMEOUT, note=note)


def _run_milp(model: LPModel, costs: np.ndarray):
    return milp(
        costs,
        constraints=_linear_constraints(model),
        bounds=Bounds(
            [-np.inf if v.lower is None else v.lower for v in model.variables],
            [np.inf if v.upper is None else v.upper for v in model.variables],
        ),
        integrality=[1 if v.integer else 0 for v in model.variables],
        # Prove optimality (don't stop at a near-optimal MIP), but don't hang forever.
        options={"mip_rel_gap": 0, "time_limit": HIGHS_TIME_LIMIT_SECONDS},
    )


def _linear_constraints(model: LPModel) -> list[LinearConstraint]:
    """All constraints as one matrix with row bounds: lower <= A @ x <= upper."""
    if not model.constraints:
        return []
    matrix = np.array([_row(c.terms, model) for c in model.constraints])
    lower = [c.rhs if c.sense in (">=", "==") else -np.inf for c in model.constraints]
    upper = [c.rhs if c.sense in ("<=", "==") else np.inf for c in model.constraints]
    return [LinearConstraint(matrix, lower, upper)]


def _row(terms: list[Term], model: LPModel) -> np.ndarray:
    """A linear expression as a dense coefficient vector, one entry per variable."""
    position = {v.name: i for i, v in enumerate(model.variables)}
    row = np.zeros(len(model.variables))
    for t in terms:
        row[position[t.var]] += t.coef
    return row
