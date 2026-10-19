"""What to tell Claude when an attempt fails, as specifically as the solver allows.

The feedback must not push Claude to "fix" a model by dropping what the text requires:
some NL4Opt problems are infeasible or unbounded as written, and then the honest answer
is to keep the model.
"""

from opt_agent.highs import feasible
from opt_agent.schema import LPModel
from opt_agent.solver import Status


def for_invalid_reply(error: str) -> str:
    return f"Your reply couldn't be used as a model:\n{error}"


def for_status(model: LPModel, status: Status) -> str:
    if status is Status.INFEASIBLE:
        return _infeasible(model)
    if status is Status.UNBOUNDED:
        return _unbounded(model)
    raise ValueError(f"no feedback for a model that is {status}")


def _infeasible(model: LPModel) -> str:
    conflict = conflicting_constraints(model)
    if conflict is None:
        where = "The solver couldn't pin down which constraints conflict."
    elif conflict:
        where = f"These constraints can't all hold at once: {', '.join(map(repr, conflict))}."
    else:
        where = "The variables' bounds and integrality can't all hold, even without constraints."
    return (
        f"The solver found the model infeasible: no values satisfy every constraint. {where} "
        "Check them against the problem text for a reversed direction (<= vs >=), a wrong "
        "number, or a requirement the text doesn't state. Don't drop or loosen a requirement "
        "the text does state just to get a solution: some problems are infeasible as written."
    )


def _unbounded(model: LPModel) -> str:
    direction = "increase" if model.objective.sense == "max" else "decrease"
    return (
        f"The solver found the model unbounded: the objective can {direction} forever. Usually "
        "a limit the text states (a budget, a capacity, an amount available) is missing or "
        "points the wrong way. Don't invent a limit the text doesn't state: some problems are "
        "unbounded as written."
    )


def conflicting_constraints(model: LPModel) -> list[str] | None:
    """A smallest set of constraints that can't all hold together, given the variables' bounds.

    This is the classic deletion filter for an irreducible infeasible subset (IIS): drop each
    constraint in turn, and if what's left is still infeasible, that constraint wasn't part
    of the conflict. Every constraint that survives is needed for the conflict.

    None means there's no conflict to report: the full set isn't confirmed infeasible, or
    HiGHS couldn't decide one of the checks. A solver error is never read as "infeasible".
    """
    if feasible(model) is not False:
        return None
    kept = list(model.constraints)
    for constraint in model.constraints:
        rest = [c for c in kept if c is not constraint]
        verdict = feasible(model.model_copy(update={"constraints": rest}))
        if verdict is None:
            return None
        if not verdict:
            kept = rest
    return [c.name for c in kept]
