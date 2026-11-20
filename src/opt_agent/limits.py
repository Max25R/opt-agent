"""What limits an integer program's optimum, found by solving it again (ADR-0009).

For an LP the explainer already has what it needs: a constraint with slack never limits the
optimum (the same point stays optimal without it), and a shadow price says what one more unit
of a binding one is worth. An integer program has neither. A constraint with slack can still
hold the answer back: in the rickshaw problem $2 of a $200 budget is left over, yet without
the budget the plan is unbounded. And a MIP has no duals. About a quarter of Claude's dev
explanations called such a constraint "not limiting" (docs/analysis/explanation_checker.md).

So each constraint of an integer program is tested the way the checker's labelers did, by
solving again:
- **dropped:** without the constraint. If that's better, the constraint limits the answer,
  however much slack it has.
- **loosened:** with its limit one unit further out (`<=`: rhs + 1; `>=`: rhs - 1). If that's
  better, one more unit is worth something. An equation has no outward side, so it isn't
  loosened. Loosening can fail to help where dropping helps (the rickshaw budget: 201 buys
  nothing whole), so neither stands in for the other.

"Better" is a strictly better optimum, beyond the objective's round-off
(verify.tolerance_for, as verify.same_answer uses it), or none at all because the objective
is now unbounded. Both solvers run integer programs at a zero gap, so a better optimum isn't a
gap closing. A re-solve counts only as the agent's own answer does (ADR-0003): CBC and HiGHS
agree on it and plain arithmetic finds nothing wrong. Otherwise the answer is None, "couldn't
tell". The feasible set only grows, so a re-solve that comes back infeasible is a solver
failure, and None too.

Only constraints are tested, not variable bounds. The cost is up to four solves per constraint
(CBC and HiGHS, dropped and loosened), only for a verified integer optimum about to be
explained.
"""

from pydantic import BaseModel

from opt_agent.highs import solve_with_highs
from opt_agent.schema import Constraint, LPModel
from opt_agent.solution import Solution, Status
from opt_agent.solver import solve
from opt_agent.verify import check_solution, same_answer, tolerance_for

OUTWARD = {"<=": 1.0, ">=": -1.0}  # the direction that loosens each inequality, by one unit


class Limit(BaseModel):
    """What re-solving found for one constraint: is the optimum better without it, or with
    its limit one unit further out? None where the solvers couldn't settle it, and for
    loosening an equation."""

    dropped_improves: bool | None
    loosened_improves: bool | None


def constraint_limits(model: LPModel, solution: Solution) -> dict[str, Limit] | None:
    """Each constraint's Limit, for an integer program's optimum; None for an LP, whose slack
    and shadow prices already say this."""
    if not model.is_mip:
        return None
    if solution.status is not Status.OPTIMAL or solution.objective is None:
        raise ValueError(f"only an optimum can be tested, not {solution.status}")
    return {
        c.name: Limit(
            dropped_improves=improves(model, solution, without(model, c)),
            loosened_improves=None if c.sense == "==" else improves(model, solution,
                                                                    loosened(model, c)),
        )
        for c in model.constraints
    }  # fmt: skip


def without(model: LPModel, constraint: Constraint) -> LPModel:
    kept = [c for c in model.constraints if c.name != constraint.name]
    return model.model_copy(update={"constraints": kept})


def loosened(model: LPModel, constraint: Constraint) -> LPModel:
    """The model with `constraint`'s limit one unit further out (an inequality only)."""
    step = OUTWARD[constraint.sense]
    changed = [c.model_copy(update={"rhs": c.rhs + step}) if c.name == constraint.name else c
               for c in model.constraints]  # fmt: skip
    return model.model_copy(update={"constraints": changed})


def improves(model: LPModel, solution: Solution, changed: LPModel) -> bool | None:
    """Is `changed`'s optimum better than `solution`, the optimum of `model`? None if CBC
    and HiGHS don't agree on `changed`, the arithmetic checks fail, or neither found an
    optimum or a certified unbounded ray."""
    cbc, highs = solve(changed), solve_with_highs(changed)
    if not same_answer(changed, cbc, highs) or check_solution(changed, cbc):
        return None
    if cbc.status is Status.UNBOUNDED:
        return True
    if cbc.status is not Status.OPTIMAL:
        return None  # the feasible set only grew, so infeasible is the solvers' failure
    assert cbc.objective is not None and solution.objective is not None  # both optimal
    terms = model.objective.terms
    tol = max(tolerance_for(terms, solution.values), tolerance_for(terms, cbc.values))
    gain = cbc.objective - solution.objective
    return (gain if model.objective.sense == "max" else -gain) > tol
