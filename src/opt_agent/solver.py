"""Build a PuLP model from an LPModel and solve it with CBC."""

import math

import pulp

from opt_agent.rays import certified_ray, describe
from opt_agent.schema import Constraint, LPModel, Term, Variable
from opt_agent.solution import Solution, Status

__all__ = ["Solution", "Status", "build_problem", "solve"]  # Solution/Status re-exported

CBC_TIME_LIMIT_SECONDS = 30


_STATUS_FROM_PULP = {
    pulp.LpSolveStatus.Optimal: Status.OPTIMAL,
    # CBC says "Optimal (within gap tolerance)" when the only gap left between its solution
    # and its proven bound is round-off (e.g. -1e-12 vs 0). We demand gapRel=0, so that
    # is a proven optimum too. Found by the CBC-vs-HiGHS property test.
    pulp.LpSolveStatus.GapLimit: Status.OPTIMAL,
    pulp.LpSolveStatus.Infeasible: Status.INFEASIBLE,
    pulp.LpSolveStatus.Unbounded: Status.UNBOUNDED,
    pulp.LpSolveStatus.TimeLimit: Status.TIMEOUT,
}


def solve(model: LPModel) -> Solution:
    """CBC's answer. A claimed optimum stands only if no certified improving ray refutes it."""
    claimed = _solve_once(model)
    if claimed.status is Status.OPTIMAL:
        ray = certified_ray(model, claimed.values, _solve_once)
        if ray is not None:
            note = (
                f"CBC claimed an optimum, but the objective improves forever along {describe(ray)}"
            )
            return Solution(solver="cbc", status=Status.UNBOUNDED, note=note)
    return claimed


def _solve_once(model: LPModel) -> Solution:
    problem, pulp_vars = build_problem(model)
    stats = _run_cbc(problem)
    status = _STATUS_FROM_PULP.get(stats.status, Status.ERROR)
    if status in (Status.INFEASIBLE, Status.UNBOUNDED):
        return _infeasible_or_unbounded(model)
    if status is Status.TIMEOUT:
        # Even with a solution in hand: it isn't proven optimal, so it isn't an answer.
        return _timed_out("solving")
    if status is not Status.OPTIMAL or not stats.has_solution:
        # Never read values after a failed solve: PuLP still holds CBC's last (junk) iterate.
        return Solution(solver="cbc", status=Status.ERROR)

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


def _infeasible_or_unbounded(model: LPModel) -> Solution:
    """Decide between infeasible and unbounded, accepting only a decision that's checked.

    CBC's own labels are unreliable: the CBC-vs-HiGHS property test found it calling
    unbounded problems infeasible, and calling integer-infeasible problems unbounded
    when their LP relaxation is unbounded. A zero objective can't be unbounded, so it
    asks only "is there any feasible point?". None: infeasible. One: unbounded, but only
    with an improving ray certified from that point; without one, CBC's label is
    unexplained and the answer is ERROR.
    """
    status, point = _feasibility(model)
    if status is Status.INFEASIBLE:
        return Solution(solver="cbc", status=Status.INFEASIBLE)
    if status is Status.TIMEOUT:
        return _timed_out("deciding feasibility")
    if status is not Status.OPTIMAL:
        return Solution(solver="cbc", status=Status.ERROR, note="CBC couldn't decide feasibility")
    ray = certified_ray(model, point, _solve_once)
    if ray is None:
        note = "CBC found no optimum for a feasible model, and no certified ray shows it unbounded"
        return Solution(solver="cbc", status=Status.ERROR, note=note)
    note = f"feasible, and the objective improves forever along {describe(ray)}"
    return Solution(solver="cbc", status=Status.UNBOUNDED, note=note)


def _timed_out(doing: str) -> Solution:
    note = f"CBC hit its {CBC_TIME_LIMIT_SECONDS} s time limit while {doing}"
    return Solution(solver="cbc", status=Status.TIMEOUT, note=note)


def _feasibility(model: LPModel) -> tuple[Status, dict[str, float] | None]:
    """CBC's answer to "is there any feasible point?", with the point if there is one."""
    problem, pulp_vars = build_problem(model)
    problem.setObjective(pulp.lpSum([]))
    stats = _run_cbc(problem)
    status = _STATUS_FROM_PULP.get(stats.status, Status.ERROR)
    if status is Status.OPTIMAL and stats.has_solution:
        return status, {
            v.name: _value_or_any_in_bounds(pulp_vars[v.name].varValue, v) for v in model.variables
        }
    return (Status.ERROR if status is Status.OPTIMAL else status), None


def _value_or_any_in_bounds(value: float | None, v: Variable) -> float:
    """CBC never sees a variable that appears only in the (here zeroed) objective, so it has
    no value. It touches no constraint, so any value within its bounds is feasible."""
    if value is not None:
        return value
    if v.lower is not None and v.lower > 0:
        return float(math.ceil(v.lower)) if v.integer else v.lower
    if v.upper is not None and v.upper < 0:
        return float(math.floor(v.upper)) if v.integer else v.upper
    return 0.0


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
