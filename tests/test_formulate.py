import json

import pytest
from fakes import FISHERY_MODEL, FISHERY_REPLY, FakeClient
from problems import FISHERY

from opt_agent.formulate import DEFAULT_MODEL, LP_SCHEMA, SYSTEM_PROMPT, formulate


def test_a_valid_reply_becomes_a_model():
    f = formulate(FISHERY["document"], FakeClient(FISHERY_REPLY))
    assert f.error is None
    assert [v.name for v in f.model.variables] == ["sled dog trips", "truck trips"]
    assert f.raw_text == FISHERY_REPLY
    assert (f.usage.input_tokens, f.usage.output_tokens) == (1200, 300)
    assert f.model_id == DEFAULT_MODEL


def test_the_request_asks_for_structured_output():
    client = FakeClient(FISHERY_REPLY)
    formulate("some problem", client)
    [request] = client.requests
    assert request["model"] == DEFAULT_MODEL
    assert request["system"] == SYSTEM_PROMPT
    assert request["messages"] == [{"role": "user", "content": "some problem"}]
    assert request["output_config"] == {"format": {"type": "json_schema", "schema": LP_SCHEMA}}


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
    bad = json.loads(FISHERY_REPLY)
    bad["constraints"][0]["terms"].append({"var": "boats", "coef": 70})
    f = formulate("...", FakeClient(json.dumps(bad)))
    assert f.model is None
    assert "constraint 'budget' uses undeclared variable 'boats'" in f.error


def test_a_wrongly_typed_field_names_where_it_is():
    bad = {**FISHERY_MODEL, "variables": [{"name": "sled dog trips", "lower": "zero"}]}
    f = formulate("...", FakeClient(json.dumps(bad)))
    assert f.error.startswith("variables.0.lower:")


@pytest.mark.parametrize(
    ("stop_reason", "message"), [("refusal", "declined"), ("max_tokens", "cut off")]
)
def test_unfinished_replies_are_errors(stop_reason, message):
    f = formulate("...", FakeClient(('{"variab', stop_reason)))
    assert f.model is None
    assert message in f.error
