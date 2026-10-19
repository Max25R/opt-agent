"""Metamorphic tests: change a problem in a way whose effect on the answer is known.

None of these needs a known answer for the original problem, only the math relating the
two answers.
"""

from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from problems import CBC_FREE_VARIABLE_BUG
from strategies import lp_models

from opt_agent.schema import LPModel, Objective, Term
from opt_agent.solver import Status, solve
from opt_agent.verify import tolerance_for

SETTINGS = settings(max_examples=75, deadline=None)


def assert_same_answer(model: LPModel, changed: LPModel, factor: float = 1.0):
    """Same status, and (if optimal) changed's optimum equals factor * model's optimum."""
    a, b = solve(model), solve(changed)
    assert a.status is not Status.ERROR
    assert b.status == a.status
    if a.status is Status.OPTIMAL:
        allowed = tolerance_for(changed.objective.terms, b.values)
        assert abs(b.objective - factor * a.objective) <= allowed


@SETTINGS
@given(lp_models(), st.sampled_from([0.5, 2.0, 10.0]))
def test_scaling_the_objective_scales_the_optimum(model, k):
    assert_same_answer(model, scale_objective(model, k), factor=k)


@SETTINGS
@given(lp_models())
def test_max_f_equals_minus_min_of_minus_f(model):
    # Exercises the max/min handling, which is exactly where PuLP flips signs internally.
    assert_same_answer(model, flip_sense(model), factor=-1.0)


@SETTINGS
@given(lp_models())
def test_adding_a_redundant_constraint_changes_nothing(model):
    assume(model.constraints)
    assert_same_answer(model, add_loosened_copy(model))


@SETTINGS
@given(lp_models())
@example(CBC_FREE_VARIABLE_BUG)  # CBC called it optimal in one variable order only
def test_reordering_changes_nothing(model):
    assert_same_answer(model, reverse_everything(model))


def scale_objective(model: LPModel, k: float) -> LPModel:
    terms = [Term(var=t.var, coef=k * t.coef) for t in model.objective.terms]
    return model.model_copy(
        update={"objective": Objective(sense=model.objective.sense, terms=terms)}
    )


def flip_sense(model: LPModel) -> LPModel:
    """max f  ->  min -f  (and vice versa)."""
    sense = "min" if model.objective.sense == "max" else "max"
    terms = [Term(var=t.var, coef=-t.coef) for t in model.objective.terms]
    return model.model_copy(update={"objective": Objective(sense=sense, terms=terms)})


def add_loosened_copy(model: LPModel) -> LPModel:
    """Duplicate the first constraint with 1 unit of extra room, so it can never bind."""
    first = model.constraints[0]
    loosen = {"<=": 1, ">=": -1, "==": 0}[first.sense]
    copy = first.model_copy(update={"name": "redundant_copy", "rhs": first.rhs + loosen})
    return model.model_copy(update={"constraints": [*model.constraints, copy]})


def reverse_everything(model: LPModel) -> LPModel:
    """Same problem with variables, constraints, and terms all listed in reverse order."""
    constraints = [c.model_copy(update={"terms": c.terms[::-1]}) for c in model.constraints]
    objective = model.objective.model_copy(update={"terms": model.objective.terms[::-1]})
    return model.model_copy(
        update={
            "variables": model.variables[::-1],
            "objective": objective,
            "constraints": constraints[::-1],
        }
    )
