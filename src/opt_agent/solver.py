"""Build a PuLP model from an LPModel and solve it with CBC."""

from enum import StrEnum

import pulp
from pydantic import BaseModel

from opt_agent.schema import Constraint, LPModel, Term

CBC_TIME_LIMIT_SECONDS = 30


class Status(StrEnum):
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    ERROR = "error"  # the solver stopped without a definite answer


class Solution(BaseModel):
    solver: str
    status: Status
    objective: float | None = None
    values: dict[str, float] = {}
    slacks: dict[str, float] = {}
    # Shadow prices: d(objective)/d(rhs) for each constraint. Pure LPs only; a MIP has none.
    duals: dict[str, float] | None = None


_STATUS_FROM_PULP = {
    pulp.LpSolveStatus.Optimal: Status.OPTIMAL,
    # CBC says "Optimal (within gap tolerance)" when the only gap left between its solution
    # and its proven bound is round-off (e.g. -1e-12 vs 0). We demand gapRel=0, so that
    # is a proven optimum too. Found by the CBC-vs-HiGHS property test.
    pulp.LpSolveStatus.GapLimit: Status.OPTIMAL,
    pulp.LpSolveStatus.Infeasible: Status.INFEASIBLE,
    pulp.LpSolveStatus.Unbounded: Status.UNBOUNDED,
}


def solve(model: LPModel) -> Solution:
    problem, pulp_vars = build_problem(model)
    stats = _run_cbc(problem)
    status = _STATUS_FROM_PULP.get(stats.status, Status.ERROR)
    if status in (Status.INFEASIBLE, Status.UNBOUNDED):
        status = _infeasible_or_unbounded(model)
    if status is not Status.OPTIMAL or not stats.has_solution:
        # Never read values after a failed solve: PuLP still holds CBC's last (junk) iterate.
        return Solution(solver="cbc", status=status)

    values = {name: var.varValue for name, var in pulp_vars.items()}
    return Solution(
        solver="cbc",
        status=status,
        objective=stats.objective,
        values=values,
        slacks={c.name: c.slack(values) for c in model.constraints},
        duals=None if model.is_mip else _duals(problem, model),
    )


def _run_cbc(problem: pulp.LpProblem):
    # "preprocess off": CBC's integer preprocessing returned a wrong "optimal" answer on a
    # 3-variable MIP that the property test found (CBC_PREPROCESS_BUG in tests/problems.py;
    # reproduced with CBC 2.10.3 and the current dev build). Our problems are tiny, so
    # skipping it costs nothing noticeable.
    solver = pulp.COIN_CMD(
        msg=False, gapRel=0, timeLimit=CBC_TIME_LIMIT_SECONDS, options=["preprocess off"]
    )
    return problem.solve(solver)


def _infeasible_or_unbounded(model: LPModel) -> Status:
    """Decide between infeasible and unbounded with a feasibility solve.

    CBC's own labels are unreliable: the CBC-vs-HiGHS property test found it calling
    unbounded problems infeasible, and calling integer-infeasible problems unbounded
    when their LP relaxation is unbounded. A zero objective can't be unbounded, so it
    asks only "is there any feasible point?". A feasible problem that has no optimum
    is unbounded (true for LPs, and for MIPs with rational data).
    """
    problem, _ = build_problem(model)
    problem.setObjective(pulp.lpSum([]))
    feasibility = _STATUS_FROM_PULP.get(_run_cbc(problem).status, Status.ERROR)
    if feasibility is Status.OPTIMAL:
        return Status.UNBOUNDED
    if feasibility is Status.INFEASIBLE:
        return Status.INFEASIBLE
    return Status.ERROR


def build_problem(model: LPModel) -> tuple[pulp.LpProblem, dict[str, pulp.LpVariable]]:
    sense = pulp.LpMaximize if model.objective.sense == "max" else pulp.LpMinimize
    problem = pulp.LpProblem("opt_agent", sense)
    # Solver-side names are x0, x1, ... and c0, c1, ...: PuLP rewrites names with spaces
    # or symbols, which could make two of our names collide. We map back by position.
    pulp_vars = {
        v.name: problem.add_variable(
            f"x{i}", v.lower, v.upper, pulp.LpInteger if v.integer else pulp.LpContinuous
        )
        for i, v in enumerate(model.variables)
    }
    problem.setObjective(_expression(model.objective.terms, pulp_vars))
    for i, c in enumerate(model.constraints):
        problem.addConstraint(_pulp_constraint(c, pulp_vars), _constraint_id(i))
    return problem, pulp_vars


def _constraint_id(index: int) -> str:
    return f"c{index}"


def _expression(terms: list[Term], pulp_vars: dict[str, pulp.LpVariable]):
    return pulp.lpSum(t.coef * pulp_vars[t.var] for t in terms)


def _pulp_constraint(c: Constraint, pulp_vars: dict[str, pulp.LpVariable]):
    lhs = _expression(c.terms, pulp_vars)
    if c.sense == "<=":
        return lhs <= c.rhs
    if c.sense == ">=":
        return lhs >= c.rhs
    return lhs == c.rhs


def _duals(problem: pulp.LpProblem, model: LPModel) -> dict[str, float]:
    # PuLP hands CBC a max problem as min(-objective) and returns that problem's duals.
    # Negating them for max makes every dual mean d(objective)/d(rhs) of *our* objective.
    sign = -1.0 if model.objective.sense == "max" else 1.0
    return {
        c.name: sign * problem.get_constraint_by_name(_constraint_id(i)).pi
        for i, c in enumerate(model.constraints)
    }
