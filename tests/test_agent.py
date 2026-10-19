import pytest
from fakes import (
    BAD_EXPLANATION,
    FISHERY_REPLY,
    GOOD_EXPLANATION,
    INFEASIBLE_REPLY,
    FakeClient,
    model,
)
from problems import CBC_FREE_VARIABLE_BUG, FISHERY
from pytest import approx

from opt_agent import self_correct
from opt_agent.agent import render, run
from opt_agent.solver import Solution, Status


def test_fishery_end_to_end():
    client = FakeClient(FISHERY_REPLY, GOOD_EXPLANATION)
    result = run(FISHERY["document"], client)
    assert result.solution.objective == approx(3000)
    assert result.solution.values == approx({"sled dog trips": 0, "truck trips": 10})
    assert result.verified
    assert result.explanation.text == GOOD_EXPLANATION
    assert result.explanation.unsupported_numbers == []
    assert len(client.requests) == 2  # formulate, then explain


def test_an_unusable_reply_on_every_attempt_never_reaches_the_solver():
    client = FakeClient('{"variables": []}', '{"variables": []}', '{"variables": []}')
    result = run("...", client)
    assert result.outcome.stopped == "attempt limit"
    assert result.formulation.error
    assert result.solution is None and not result.verified
    assert len(client.requests) == 3


def test_an_infeasible_model_claude_stands_by_gets_no_explanation():
    client = FakeClient(INFEASIBLE_REPLY, INFEASIBLE_REPLY)  # revised to the same model
    result = run("...", client)
    assert result.outcome.stopped == "model unchanged"
    assert result.solution.status is Status.INFEASIBLE
    assert result.explanation is None and not result.verified
    assert len(client.requests) == 2


def test_single_shot_makes_one_formulation_call():
    client = FakeClient(INFEASIBLE_REPLY)
    result = run("...", client, max_attempts=1)
    assert result.outcome.stopped == "attempt limit"
    assert len(result.outcome.attempts) == 1 and len(client.requests) == 1


def test_without_an_explanation_there_is_one_call():
    client = FakeClient(FISHERY_REPLY)
    result = run(FISHERY["document"], client, with_explanation=False)
    assert result.verified and result.explanation is None
    assert len(client.requests) == 1


def test_render_shows_the_model_the_answer_and_the_explanation():
    text = render(run(FISHERY["document"], FakeClient(FISHERY_REPLY, GOOD_EXPLANATION)))
    assert "budget: 50*[sled dog trips] + 100*[truck trips] <= 1000" in text
    assert "fewer sled dog trips: 1*[sled dog trips] - 1*[truck trips] <= 0" in text
    assert "Objective: 3000" in text
    assert GOOD_EXPLANATION in text
    assert "not backed" not in text


def test_render_flags_numbers_the_solver_didnt_produce():
    text = render(run(FISHERY["document"], FakeClient(FISHERY_REPLY, BAD_EXPLANATION)))
    assert "(not backed by the solver's numbers: $200)" in text


def test_render_lists_the_attempts_and_flags():
    fixed = model([("at least 5", ">=", 5)])  # "fixed" by deleting a constraint
    text = render(run("...", FakeClient(INFEASIBLE_REPLY, fixed), with_explanation=False))
    assert "Attempt 1: infeasible" in text and "Attempt 2: optimal" in text
    assert "Stopped: optimal" in text
    assert "flagged revision: deleted constraint 'at most 3'" in text


# CBC's recorded answer for CBC_FREE_VARIABLE_BUG: "optimal" at enormous values, though the
# model is unbounded. c0 is violated by 1, far inside the round-off allowed at that size.
FALSE_OPTIMUM = Solution(
    solver="cbc",
    status=Status.OPTIMAL,
    objective=-6.25e11,
    values={"x0": -5e11, "x1": 6.25e11, "x2": 0.0},
    slacks={"c0": -1.0},
)


@pytest.fixture
def cbc_claims_a_false_optimum(monkeypatch):
    monkeypatch.setattr(self_correct, "solve", lambda model: FALSE_OPTIMUM)
    return CBC_FREE_VARIABLE_BUG.model_dump_json()


def test_a_false_optimum_is_caught_by_the_cross_check_not_by_arithmetic(
    cbc_claims_a_false_optimum,
):
    result = run("...", FakeClient(cbc_claims_a_false_optimum), with_explanation=False)
    assert result.outcome.stopped == "optimal"  # the loop trusts the solver: no revision
    assert result.solution.status is Status.OPTIMAL  # CBC's claim is what gets reported
    assert result.check_problems == []  # arithmetic checks feasibility, not optimality
    assert result.highs_agrees is False  # HiGHS says unbounded
    assert not result.verified  # so the answer is not verified


def test_an_unverified_answer_is_not_explained(cbc_claims_a_false_optimum):
    client = FakeClient(cbc_claims_a_false_optimum, "An explanation of a wrong answer.")
    result = run("...", client)
    assert result.explanation is None
    assert len(client.requests) == 1  # no explanation call at all


def test_a_solver_disagreement_is_reported_as_such(cbc_claims_a_false_optimum):
    text = render(run("...", FakeClient(cbc_claims_a_false_optimum), with_explanation=False))
    assert "SOLVERS DISAGREE: CBC says optimal (-6.25e+11), HiGHS says unbounded." in text
    assert "No answer is reported." in text
    assert "Objective:" not in text


def test_an_overruled_claim_is_shown():
    """Real CBC on the counterexample: its "optimal" is overruled by an improving ray."""
    result = run("...", FakeClient(CBC_FREE_VARIABLE_BUG.model_dump_json()), max_attempts=1)
    assert result.solution.status is Status.UNBOUNDED and result.highs_agrees
    assert "CBC claimed an optimum, but the objective improves forever" in render(result)
