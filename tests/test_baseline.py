"""The no-solver baseline's request and its pre-registered parsing (section 2a)."""

import json

import pytest
from fakes import GAS_PROBLEM, FakeClient, status_error

from opt_agent import api, formulate
from opt_agent.baseline import ANSWER_SCHEMA, SYSTEM_PROMPT, answer_directly, build_request
from opt_agent.baseline import parse_answer as parse
from opt_agent.solver import Status


def test_the_request_differs_from_single_shot_only_in_prompt_and_schema():
    mine = build_request(GAS_PROBLEM, formulate.DEFAULT_MODEL)
    theirs = formulate.build_request(GAS_PROBLEM, formulate.DEFAULT_MODEL)
    assert mine["system"] == SYSTEM_PROMPT != theirs["system"]
    assert mine["output_config"]["format"]["schema"] == ANSWER_SCHEMA
    for settings in (mine, theirs):
        del settings["system"], settings["output_config"]["format"]
    assert mine == theirs  # same model, max_tokens, thinking, effort, and problem text


def test_the_schema_asks_for_exactly_status_and_objective():
    assert ANSWER_SCHEMA["required"] == ["status", "objective"]
    assert ANSWER_SCHEMA["additionalProperties"] is False
    assert ANSWER_SCHEMA["properties"]["status"]["enum"] == ["optimal", "infeasible", "unbounded"]


def test_an_optimum_needs_a_finite_objective():
    assert parse('{"status": "optimal", "objective": 251}', "end_turn") == (
        Status.OPTIMAL, 251.0, None)  # fmt: skip
    status, objective, error = parse('{"status": "optimal", "objective": null}', "end_turn")
    assert (status, objective) == (None, None) and "finite objective" in error
    assert parse('{"status": "optimal", "objective": 1e999}', "end_turn")[0] is None  # inf


def test_without_an_optimum_the_objective_is_ignored():
    assert parse('{"status": "infeasible", "objective": 7}', "end_turn") == (
        Status.INFEASIBLE, None, None)  # fmt: skip
    assert parse('{"status": "unbounded", "objective": null}', "end_turn")[0] is Status.UNBOUNDED


@pytest.mark.parametrize(
    "text, stop_reason, says",
    [
        ('{"status": "optimal", "objective": 2', "max_tokens", "cut off"),
        ("", "refusal", "declined"),
        ("251", "end_turn", "Input should be an object"),
        ('{"status": "timeout", "objective": null}', "end_turn", "status"),
        ('{"status": "optimal"}', "end_turn", "objective: Field required"),
    ],
    ids=["cut off", "refusal", "not an object", "unknown status", "missing objective"],
)
def test_an_unusable_reply_has_no_answer_and_says_why(text, stop_reason, says):
    status, objective, error = parse(text, stop_reason)
    assert status is None and objective is None
    assert says in error


def test_a_failed_call_is_an_api_failure_not_an_answer(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)
    a = answer_directly(GAS_PROBLEM, FakeClient(status_error(400)))
    assert a.api_failed and a.status is None


def test_a_usable_reply_is_kept_with_its_usage():
    reply = json.dumps({"status": "optimal", "objective": 251})
    a = answer_directly(GAS_PROBLEM, FakeClient(reply))
    assert (a.status, a.objective, a.error) == (Status.OPTIMAL, 251.0, None)
    assert a.usage.output_tokens == 300 and a.raw_text == reply
