from fakes import (
    BAD_EXPLANATION,
    FISHERY_REPLY,
    GOOD_EXPLANATION,
    INFEASIBLE_REPLY,
    FakeClient,
    model,
)
from problems import FISHERY
from pytest import approx

from opt_agent.agent import render, run
from opt_agent.solver import Status


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
