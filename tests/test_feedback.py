import pytest
from problems import INFEASIBLE, WYNDOR, terms

from opt_agent import feedback
from opt_agent.feedback import conflicting_constraints, for_invalid_reply, for_status
from opt_agent.highs import solve_with_highs
from opt_agent.schema import LPModel
from opt_agent.solver import Status

# NL4Opt dev problem -1028228232, infeasible as written. The smallest conflict is just two
# constraints: 300 strong containers alone need 1200 emulsifiers, and only 1000 are
# available. The 60% rule plays no part.
LOTION = LPModel.model_validate(
    {
        "variables": [{"name": "strong"}, {"name": "weak"}],
        "objective": {"sense": "min", "terms": terms({"strong": 3, "weak": 2})},
        "constraints": [
            {"name": "emulsifiers", "terms": terms({"strong": 4, "weak": 7}), "sense": "<=",
             "rhs": 1000},
            {"name": "strong minimum", "terms": terms({"strong": 1}), "sense": ">=", "rhs": 300},
            {"name": "weak share", "terms": terms({"strong": -0.6, "weak": 0.4}), "sense": ">=",
             "rhs": 0},
        ],
    }
)  # fmt: skip


def test_the_conflict_in_the_lotion_problem():
    assert conflicting_constraints(LOTION) == ["emulsifiers", "strong minimum"]


def test_a_two_constraint_conflict():
    assert conflicting_constraints(INFEASIBLE) == ["at_least_5", "at_most_3"]


def test_the_conflict_is_irreducible():
    """On its own the conflict is infeasible, and dropping any one of its constraints fixes it."""
    conflict = [c for c in LOTION.constraints if c.name in conflicting_constraints(LOTION)]
    assert status_with(conflict) is Status.INFEASIBLE
    for dropped in conflict:
        assert status_with([c for c in conflict if c is not dropped]) is not Status.INFEASIBLE


def status_with(constraints):
    return solve_with_highs(LOTION.model_copy(update={"constraints": constraints})).status


def test_bounds_alone_can_conflict():
    """No integer lies between 0.2 and 0.8, with or without constraints."""
    model = LPModel.model_validate(
        {
            "variables": [{"name": "x", "lower": 0.2, "upper": 0.8, "integer": True}],
            "objective": {"sense": "min", "terms": terms({"x": 1})},
            "constraints": [],
        }
    )
    assert conflicting_constraints(model) == []
    assert "bounds and integrality can't all hold" in for_status(model, Status.INFEASIBLE)


def test_infeasible_feedback_warns_against_dropping_requirements():
    feedback = for_status(LOTION, Status.INFEASIBLE)
    assert "can't all hold at once: 'emulsifiers', 'strong minimum'." in feedback
    assert "some problems are infeasible as written" in feedback


def test_unbounded_feedback_names_the_direction():
    assert "can increase forever" in for_status(WYNDOR, Status.UNBOUNDED)


def test_invalid_reply_feedback_quotes_the_error():
    assert for_invalid_reply("objective: Field required").endswith("objective: Field required")


def test_there_is_no_feedback_for_an_optimal_model():
    with pytest.raises(ValueError):
        for_status(WYNDOR, Status.OPTIMAL)


def test_no_conflict_is_named_for_a_feasible_model():
    """If the full set isn't confirmed infeasible, naming "the conflict" would be a guess."""
    assert conflicting_constraints(WYNDOR) is None


def test_a_solver_error_is_not_read_as_infeasible(monkeypatch):
    verdicts = iter([False, None])  # the full set is infeasible, then HiGHS can't decide
    monkeypatch.setattr(feedback, "feasible", lambda model: next(verdicts))
    assert conflicting_constraints(LOTION) is None
    monkeypatch.setattr(
        feedback, "feasible", lambda model: False if len(model.constraints) == 4 else None
    )
    assert "couldn't pin down which constraints conflict" in for_status(LOTION, Status.INFEASIBLE)
