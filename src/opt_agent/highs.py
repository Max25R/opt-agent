"""Independent cross-check: solve the same LPModel with SciPy's HiGHS (no PuLP, no CBC).

Two unrelated solvers agreeing on status and optimal objective makes a bug in our PuLP
translation, or in CBC itself, very unlikely to go unnoticed.
"""

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from opt_agent.rays import refutation, refuting_ray
from opt_agent.schema import LPModel, Term
from opt_agent.solver import Solution, Status

# scipy.optimize.milp status codes
_OPTIMAL = 0
_INFEASIBLE, _UNBOUNDED, _INFEASIBLE_OR_UNBOUNDED = 2, 3, 4


def solve_with_highs(model: LPModel) -> Solution:
    """HiGHS's answer, with the same rule as CBC: a claimed optimum stands only if no
    improving ray, found by HiGHS itself, refutes it."""
    claimed = _solve_once(model)
    if claimed.status is Status.OPTIMAL and (ray := refuting_ray(model, _solve_once)):
        return Solution(solver="highs", status=Status.UNBOUNDED, note=refutation("HiGHS", ray))
    return claimed


def _solve_once(model: LPModel) -> Solution:
    sign = -1.0 if model.objective.sense == "max" else 1.0  # milp always minimizes
    costs = sign * _row(model.objective.terms, model)
    result = _run_milp(model, costs)
    if result.status in (_INFEASIBLE, _UNBOUNDED, _INFEASIBLE_OR_UNBOUNDED):
        return Solution(solver="highs", status=_infeasible_or_unbounded(model))
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


def _infeasible_or_unbounded(model: LPModel) -> Status:
    """Same rule as for CBC (see solver.py): a feasibility solve decides.

    HiGHS sometimes answers only "infeasible or unbounded" (common for MIPs), and the
    rule keeps both solvers' labels resting on the same simple question.
    """
    feasibility = _run_milp(model, np.zeros(len(model.variables))).status
    if feasibility == _OPTIMAL:
        return Status.UNBOUNDED
    if feasibility == _INFEASIBLE:
        return Status.INFEASIBLE
    return Status.ERROR


def _run_milp(model: LPModel, costs: np.ndarray):
    return milp(
        costs,
        constraints=_linear_constraints(model),
        bounds=Bounds(
            [-np.inf if v.lower is None else v.lower for v in model.variables],
            [np.inf if v.upper is None else v.upper for v in model.variables],
        ),
        integrality=[1 if v.integer else 0 for v in model.variables],
        options={"mip_rel_gap": 0},  # prove optimality; don't stop at a near-optimal MIP
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
