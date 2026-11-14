"""Unused variables are dropped with a note, never rejected (follow-up pre-registration, 5a),
in every solver condition, and every drop is in the run record. Never calls the API."""

import json

from fakes import GAS_MODEL, GAS_REPLY, FakeClient

from opt_agent import evaluate, formulate
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.schema import LPModel, drop_unused
from opt_agent.solver import solve

GAS = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev.json")}["439170086"]
SPARE = {"name": "spare trucks", "lower": 0, "upper": None, "integer": True}


def with_spare(zero_term: bool = False) -> dict:
    """The gas model with a variable no expression uses (and, optionally, a 0 term for it)."""
    data = json.loads(GAS_REPLY)
    data["variables"].append(SPARE)
    if zero_term:
        data["constraints"][0]["terms"].append({"var": "spare trucks", "coef": 0})
    return data


def test_an_unused_variable_is_dropped_and_named():
    cleaned, dropped = drop_unused(with_spare())
    assert dropped == ["spare trucks"]
    assert LPModel.model_validate(cleaned) == LPModel.model_validate(GAS_MODEL)


def test_its_zero_terms_go_too():
    cleaned, dropped = drop_unused(with_spare(zero_term=True))
    assert dropped == ["spare trucks"]
    assert LPModel.model_validate(cleaned) == LPModel.model_validate(GAS_MODEL)


def test_a_model_using_every_variable_is_untouched():
    assert drop_unused(GAS_MODEL) == (GAS_MODEL, [])


def test_what_isnt_a_model_is_left_for_the_validator():
    for data in (None, [], {"variables": []}, {"variables": [1], "objective": 2, "constraints": 3}):
        assert drop_unused(data) == (data, [])


def test_the_reply_parses_and_solves_as_if_the_variable_were_never_there():
    model, error, dropped = formulate.parse_with_drops(json.dumps(with_spare()), "end_turn")
    assert error is None and dropped == ["spare trucks"]
    assert solve(model).objective == solve(LPModel.model_validate(GAS_MODEL)).objective == 251


def test_parse_reply_keeps_its_shape_and_errors_keep_their_words():
    model, error = formulate.parse_reply(json.dumps(with_spare()), "end_turn")
    assert error is None and len(model.variables) == 2
    model, error, dropped = formulate.parse_with_drops("not json", "end_turn")
    assert model is None and "Invalid JSON" in error and dropped == []
    bad = with_spare()
    bad["constraints"][0]["terms"].append({"var": "ghost", "coef": 1})
    model, error, dropped = formulate.parse_with_drops(json.dumps(bad), "end_turn")
    assert model is None and "undeclared variable 'ghost'" in error


def test_a_model_built_directly_is_still_checked():
    # The validator's rule stands for code that builds models; only replies get the drop.
    try:
        LPModel.model_validate(with_spare())
    except ValueError as error:
        assert "declared but never used" in str(error)
    else:
        raise AssertionError("an unused variable passed validation")


def test_every_drop_is_in_the_attempt_log_and_the_result_line(tmp_path):
    client = FakeClient(json.dumps(with_spare()))
    [item] = evaluate.evaluate([GAS], ("single-shot",), client, tmp_path)
    assert item.dropped == ["spare trucks"] and item.objective == 251
    lines = [json.loads(x) for x in (tmp_path / "attempts.jsonl").read_text().splitlines()]
    [attempt] = [x for x in lines if x["kind"] == "attempt"]
    assert attempt["dropped"] == ["spare trucks"]
