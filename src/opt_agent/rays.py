"""Is a claimed optimum really one, or can the objective improve forever?

CBC and HiGHS have both reported "optimal" for unbounded models with free variables, in
one variable order but not another (CBC_FREE_VARIABLE_BUG and HIGHS_FREE_VARIABLE_BUG in
tests/problems.py). So "unbounded" needs a certificate, and so does overruling an
"optimal": a feasible point x plus an *improving ray* d, a direction you can move along
forever without breaking a constraint while the objective keeps improving. For a MIP the
ray comes from its LP relaxation; that's enough because a feasible integer program with an
unbounded relaxation is itself unbounded (for rational data).

Finding d is a small LP that can't be unbounded itself (every d_j lies within [-1, 1]). A d
that's found is accepted only if it passes two checks, both with the same relative
tolerances as every other check (verify.py):

1. Scaled so its largest entry is 1, it keeps every constraint (A d <= 0 for a <= row, and
   so on) and every bound's direction, and it improves the objective. Scaling first means
   a spurious near-zero direction can't hide inside an absolute tolerance.
2. A long step: x moved LONG_STEP times the problem's own scale along d is still feasible.
"""

from collections.abc import Callable

from opt_agent.schema import LPModel, Variable, evaluate, magnitude
from opt_agent.solution import Solution, Status
from opt_agent.verify import TOLERANCE, feasibility_problems

LONG_STEP = 1e3


def certified_ray(
    model: LPModel, point: dict[str, float] | None, solve_once: Callable[[LPModel], Solution]
) -> dict[str, float] | None:
    """An improving ray from `solve_once` that survives a long step from `point`, or None.

    `point` must itself be feasible; that's checked here, because "feasible and has an
    improving ray" is what proves a model unbounded. `solve_once` should be the solver whose
    claim is being checked, so that CBC's and HiGHS's verdicts stay independent.
    """
    if point is None or feasibility_problems(model, point):
        return None
    found = solve_once(ray_model(model))
    if found.status is not Status.OPTIMAL:
        return None
    return found.values if is_ray_from(model, point, found.values) else None


def is_ray_from(model: LPModel, point: dict[str, float], d: dict[str, float]) -> bool:
    """Plain arithmetic: is d an improving ray, and does a long step from `point` stay feasible?"""
    size = max((abs(step) for step in d.values()), default=0.0)
    if size == 0:
        return False
    unit = {name: step / size for name, step in d.items()}
    if feasibility_problems(ray_model(model), unit, integrality=False):
        return False  # breaks a constraint or a bound's direction
    if improvement(model, unit) <= TOLERANCE * max(1.0, magnitude(model.objective.terms, unit)):
        return False  # doesn't improve the objective
    scale = max([1.0, *(abs(x) for x in point.values()), *(abs(c.rhs) for c in model.constraints)])
    moved = {name: x + LONG_STEP * scale * unit.get(name, 0.0) for name, x in point.items()}
    return not feasibility_problems(model, moved, integrality=False)  # a relaxation's ray


def improvement(model: LPModel, d: dict[str, float]) -> float:
    """How much one step along d improves the objective (positive means better)."""
    change = evaluate(model.objective.terms, d)
    return change if model.objective.sense == "max" else -change


def describe(ray: dict[str, float]) -> str:
    return "(" + ", ".join(f"{name} {step:+g}" for name, step in ray.items() if step) + ")"


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
