"""Integer variables with fractional bounds (audit, finding 6): both solvers must see the
bounds rounded inward, so HiGHS can't return a fractional value for an integer variable and
the cross-check can't report a false disagreement. Never calls the API."""

import pytest

from opt_agent.highs import solve_with_highs
from opt_agent.schema import Constraint, LPModel, Objective, Term, Variable
from opt_agent.solver import Status, solve
from opt_agent.verify import check_solution, same_answer


def one_variable(lower: float | None, upper: float | None, at_least: float = 0.0) -> LPModel:
    """Maximize an integer x within its bounds, with one constraint so every solver sees x."""
    return LPModel(
        variables=[Variable(name="x", lower=lower, upper=upper, integer=True)],
        objective=Objective(sense="max", terms=[Term(var="x", coef=1)]),
        constraints=[
            Constraint(name="floor", terms=[Term(var="x", coef=1)], sense=">=", rhs=at_least)
        ],
    )


AUDIT_CASE = one_variable(lower=0.0, upper=2.5, at_least=1.0)  # HiGHS returned x = 2.5


@pytest.mark.parametrize("solver", [solve, solve_with_highs], ids=["cbc", "highs"])
def test_a_fractional_upper_bound_gives_a_whole_number(solver):
    s = solver(AUDIT_CASE)
    assert s.status is Status.OPTIMAL
    assert s.values["x"] == 2.0 and s.objective == 2.0
    assert check_solution(AUDIT_CASE, s) == []


def test_the_audit_case_is_no_longer_a_disagreement():
    assert same_answer(AUDIT_CASE, solve(AUDIT_CASE), solve_with_highs(AUDIT_CASE))


@pytest.mark.parametrize("solver", [solve, solve_with_highs], ids=["cbc", "highs"])
def test_no_whole_number_within_the_bounds_is_infeasible(solver):
    model = one_variable(lower=0.2, upper=0.8)
    assert solver(model).status is Status.INFEASIBLE


def test_an_empty_integer_range_is_agreed_on():
    model = one_variable(lower=0.2, upper=0.8)
    assert same_answer(model, solve(model), solve_with_highs(model))


@pytest.mark.parametrize("solver", [solve, solve_with_highs], ids=["cbc", "highs"])
def test_a_fractional_lower_bound_rounds_up(solver):
    model = LPModel(
        variables=[Variable(name="x", lower=1.5, upper=None, integer=True)],
        objective=Objective(sense="min", terms=[Term(var="x", coef=1)]),
        constraints=[Constraint(name="cap", terms=[Term(var="x", coef=1)], sense="<=", rhs=9)],
    )
    s = solver(model)
    assert (s.status, s.values["x"]) == (Status.OPTIMAL, 2.0)


@pytest.mark.parametrize("solver", [solve, solve_with_highs], ids=["cbc", "highs"])
def test_round_off_in_a_whole_bound_isnt_rounded_away(solver):
    """3.0000000000004 is 3 written with float noise, not a bound between 3 and 4."""
    model = one_variable(lower=1.9999999999997, upper=3.0000000000004)
    s = solver(model)
    assert (s.status, s.values["x"]) == (Status.OPTIMAL, 3.0)


@pytest.mark.parametrize("solver", [solve, solve_with_highs], ids=["cbc", "highs"])
def test_continuous_bounds_are_left_alone(solver):
    model = LPModel(
        variables=[Variable(name="x", lower=0.0, upper=2.5, integer=False)],
        objective=Objective(sense="max", terms=[Term(var="x", coef=1)]),
        constraints=[Constraint(name="floor", terms=[Term(var="x", coef=1)], sense=">=", rhs=1)],
    )
    assert solver(model).values["x"] == 2.5


def objective_only_empty_range() -> LPModel:
    """z appears only in the objective, so CBC's zero-objective feasibility solve never
    sees it (audit: CBC said ERROR, HiGHS said INFEASIBLE)."""
    return LPModel(
        variables=[
            Variable(name="x", lower=0.0, upper=None),
            Variable(name="z", lower=0.2, upper=0.8, integer=True),
        ],
        objective=Objective(sense="max", terms=[Term(var="z", coef=1), Term(var="x", coef=1)]),
        constraints=[Constraint(name="cap", terms=[Term(var="x", coef=1)], sense="<=", rhs=4)],
    )


@pytest.mark.parametrize("solver", [solve, solve_with_highs], ids=["cbc", "highs"])
def test_an_objective_only_variable_with_no_whole_number_is_infeasible(solver):
    s = solver(objective_only_empty_range())
    assert s.status is Status.INFEASIBLE
    assert "z" in s.note


def test_the_objective_only_case_is_agreed_on():
    model = objective_only_empty_range()
    assert same_answer(model, solve(model), solve_with_highs(model))
