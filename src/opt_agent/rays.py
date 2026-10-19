"""Is a claimed optimum really one, or can the objective improve forever?

CBC and HiGHS have both reported "optimal" for unbounded models with free variables, in
one variable order but not another (CBC_FREE_VARIABLE_BUG and HIGHS_FREE_VARIABLE_BUG in
tests/problems.py). So after a solver claims an optimum, the same solver looks for an
*improving ray*: a direction d that you can move along forever without breaking a
constraint while the objective keeps improving. A feasible model has one exactly when it's
unbounded. For a MIP the ray comes from its LP relaxation; that's enough because a feasible
integer program with an unbounded relaxation is itself unbounded (for rational data).

Finding d is a small LP that can't be unbounded itself (every d_j lies within [-1, 1]), and
a d that's found is checked by plain arithmetic, so no ray is taken on a solver's word.
"""

from collections.abc import Callable

from opt_agent.schema import LPModel, Variable, evaluate, magnitude

TOLERANCE = 1e-7


def refuting_ray(model: LPModel, solve_once: Callable) -> dict[str, float] | None:
    """An arithmetic-checked improving ray found with `solve_once`, or None if there's none.

    `solve_once` should be the solver whose claim is being checked, so that CBC's and
    HiGHS's verdicts stay independent of each other.
    """
    found = solve_once(ray_model(model))
    if found.status == "optimal" and is_improving_ray(model, found.values):
        return found.values
    return None


def refutation(solver: str, ray: dict[str, float]) -> str:
    """The note recorded when a claimed optimum is overruled."""
    direction = ", ".join(f"{name} {step:+g}" for name, step in ray.items() if step)
    return f"{solver} claimed an optimum, but the objective improves forever along ({direction})"


def ray_model(model: LPModel) -> LPModel:
    """The LP whose optimum is the best improving direction (0 if there's none).

    Same constraints with right-hand sides 0; each direction may only go where the
    variable's bounds allow forever (up if only bounded below, and so on); no integrality.
    """
    variables = [
        Variable(
            name=v.name,
            lower=0.0 if v.lower is not None else -1.0,
            upper=0.0 if v.upper is not None else 1.0,
        )
        for v in model.variables
    ]
    constraints = [c.model_copy(update={"rhs": 0.0}) for c in model.constraints]
    return model.model_copy(update={"variables": variables, "constraints": constraints})


def is_improving_ray(model: LPModel, d: dict[str, float], tol: float = TOLERANCE) -> bool:
    """Plain arithmetic: moving along d keeps every constraint and every bound, forever,
    and improves the objective."""
    for v in model.variables:
        if (v.lower is not None and d[v.name] < -tol) or (v.upper is not None and d[v.name] > tol):
            return False
    for c in model.constraints:
        moved, allowed = evaluate(c.terms, d), tol * max(1.0, magnitude(c.terms, d))
        if (c.sense in ("<=", "==") and moved > allowed) or (
            c.sense in (">=", "==") and moved < -allowed
        ):
            return False
    return improvement(model, d) > tol * max(1.0, magnitude(model.objective.terms, d))


def improvement(model: LPModel, d: dict[str, float]) -> float:
    """How much one step along d improves the objective (positive means better)."""
    change = evaluate(model.objective.terms, d)
    return change if model.objective.sense == "max" else -change
