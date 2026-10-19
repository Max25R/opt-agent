import json

from fakes import BAD_EXPLANATION, FISHERY_REPLY, GOOD_EXPLANATION, FakeClient
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


def test_an_unusable_reply_stops_before_solving():
    client = FakeClient('{"variables": []}')
    result = run("...", client)
    assert result.formulation.error
    assert result.solution is None and not result.verified
    assert len(client.requests) == 1


def test_an_infeasible_model_is_reported_without_an_explanation():
    infeasible = {
        "variables": [{"name": "x"}],
        "objective": {"sense": "min", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [
            {"name": "at least 5", "terms": [{"var": "x", "coef": 1}], "sense": ">=", "rhs": 5},
            {"name": "at most 3", "terms": [{"var": "x", "coef": 1}], "sense": "<=", "rhs": 3},
        ],
    }
    client = FakeClient(json.dumps(infeasible))
    result = run("...", client)
    assert result.solution.status is Status.INFEASIBLE
    assert result.explanation is None and not result.verified
    assert len(client.requests) == 1


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
