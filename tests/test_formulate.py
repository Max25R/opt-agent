import json

import pytest
from fakes import GAS_MODEL, GAS_PROBLEM, GAS_REPLY, FakeClient, status_error

from opt_agent.api import request_sha256
from opt_agent.formulate import (
    DEFAULT_MODEL,
    LP_SCHEMA,
    SYSTEM_PROMPT,
    Revision,
    build_request,
    formulate,
)


def test_a_valid_reply_becomes_a_model():
    f = formulate(GAS_PROBLEM, FakeClient(GAS_REPLY))
    assert f.error is None
    assert [v.name for v in f.model.variables] == ["pipelines", "trains"]
    assert f.raw_text == GAS_REPLY
    assert (f.usage.input_tokens, f.usage.output_tokens) == (1200, 300)
    assert f.model_id == DEFAULT_MODEL


def test_the_request_pins_every_setting():
    """Structured output, and thinking and effort written out, not left to defaults."""
    client = FakeClient(GAS_REPLY)
    formulate("some problem", client)
    [request] = client.requests
    assert request == {
        "model": DEFAULT_MODEL,
        "max_tokens": 16000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": "some problem"}],
        "thinking": {"type": "adaptive", "display": "omitted"},
        "output_config": {
            "effort": "medium",
            "format": {"type": "json_schema", "schema": LP_SCHEMA},
        },
    }


def test_what_is_sent_is_what_is_recorded():
    """One build_request() for the call, the hash, and the log: they can't drift apart."""
    revision = Revision(previous_reply="{}", feedback="objective: Field required")
    client = FakeClient(GAS_REPLY)
    f = formulate("some problem", client, revision=revision)
    [sent] = client.requests
    assert f.request == sent == build_request("some problem", DEFAULT_MODEL, revision)
    assert f.call.request_sha256 == request_sha256(sent)
    assert client.options == [{"max_retries": 0}]  # api.call retries, and times it


def test_the_hash_changes_with_anything_that_changes_the_reply():
    base = build_request("p", DEFAULT_MODEL)
    assert request_sha256(base) == request_sha256(build_request("p", DEFAULT_MODEL))
    assert request_sha256(base) != request_sha256(build_request("q", DEFAULT_MODEL))
    assert request_sha256(base) != request_sha256(build_request("p", "claude-opus-5-5"))
    assert request_sha256(base) != request_sha256({**base, "output_config": {"effort": "high"}})


def test_a_failed_call_is_an_error_not_an_exception():
    f = formulate("...", FakeClient(status_error(400)))
    assert f.model is None and f.api_failed
    assert f.error == "the API call failed: APIStatusError (400): HTTP 400"
    assert f.usage.output_tokens == 0


def test_the_schema_is_strict():
    """Structured output needs additionalProperties: false on every object."""

    def objects(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                yield node
            for value in node.values():
                yield from objects(value)
        elif isinstance(node, list):
            for value in node:
                yield from objects(value)

    found = list(objects(LP_SCHEMA))  # LPModel, Variable, Objective, Constraint, Term
    assert len(found) == 5
    assert all(o["additionalProperties"] is False for o in found)


def test_an_inconsistent_model_is_an_error_claude_can_act_on():
    bad = json.loads(GAS_REPLY)
    bad["constraints"][0]["terms"].append({"var": "trucks", "coef": 500})
    f = formulate("...", FakeClient(json.dumps(bad)))
    assert f.model is None and not f.api_failed
    assert "constraint 'daily gas' uses undeclared variable 'trucks'" in f.error


def test_a_wrongly_typed_field_names_where_it_is():
    bad = {**GAS_MODEL, "variables": [{"name": "pipelines", "lower": "zero"}]}
    f = formulate("...", FakeClient(json.dumps(bad)))
    assert f.error.startswith("variables.0.lower:")


@pytest.mark.parametrize(
    ("stop_reason", "message"),
    [
        ("refusal", "declined"),
        ("max_tokens", "cut off"),
        ("model_context_window_exceeded", "cut off"),
        ("pause_turn", "paused"),
    ],
)
def test_unfinished_replies_are_errors(stop_reason, message):
    f = formulate("...", FakeClient(('{"variab', stop_reason)))
    assert f.model is None
    assert message in f.error
