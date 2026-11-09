"""The formulation checklist (checklist.py): the call sees the problem text and the model's
variable names only, and its reply is parsed like any other. Examples are NL4Opt dev only.
Never calls the API."""

import json

import pytest
from fakes import GAS_CHECKLIST_REPLY, GAS_PROBLEM, GAS_REPLY, FakeClient, status_error

from opt_agent import api, checklist, formulate
from opt_agent.api import Cache
from opt_agent.schema import LPModel

GAS = LPModel.model_validate_json(GAS_REPLY)
NAMES = [v.name for v in GAS.variables]


def test_the_call_sees_the_text_and_the_variable_names_only():
    request = checklist.build_request(GAS_PROBLEM, NAMES)
    (message,) = request["messages"]
    assert GAS_PROBLEM in message["content"] and "pipelines\ntrains" in message["content"]
    sent = json.dumps(request["messages"])
    for detail in ("integer", "daily gas", "1000000.0", "upper", "lower", '"sense"'):
        assert detail not in sent  # no kinds, bounds, constraints or objective of the model
    assert request["system"] == checklist.SYSTEM_PROMPT


def test_it_uses_the_same_pinned_settings_as_the_formulation():
    ours, theirs = checklist.build_request(GAS_PROBLEM, NAMES), formulate.build_request("", "m")
    for key in ("max_tokens", "thinking"):
        assert ours[key] == theirs[key]
    assert ours["output_config"]["effort"] == theirs["output_config"]["effort"]
    assert ours["output_config"]["format"]["schema"] == checklist.CHECKLIST_SCHEMA


def test_a_reply_is_parsed():
    reply = checklist.ask(GAS_PROBLEM, NAMES, FakeClient(GAS_CHECKLIST_REPLY))
    assert reply.error is None
    assert [v.kind for v in reply.checklist.variables] == ["integer", "integer"]
    assert len(reply.checklist.requirements) == 2


@pytest.mark.parametrize("reply", ["not json", ('{"variables": []}', "end_turn"), ("", "refusal")])
def test_an_unusable_reply_is_an_error_not_an_exception(reply):
    result = checklist.ask(GAS_PROBLEM, NAMES, FakeClient(reply))
    assert result.checklist is None and result.error


def test_an_api_error_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(api, "MAX_TRIES", 1)
    result = checklist.ask(GAS_PROBLEM, NAMES, FakeClient(status_error(400)))
    assert result.checklist is None and result.api_failed


def test_a_cached_reply_replays_without_a_call(tmp_path):
    cache = Cache(tmp_path)
    first = checklist.ask(GAS_PROBLEM, NAMES, FakeClient(GAS_CHECKLIST_REPLY), cache=cache)
    again = checklist.ask(GAS_PROBLEM, NAMES, FakeClient(), cache=cache)
    assert again.call.cached and again.checklist == first.checklist
