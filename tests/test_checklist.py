"""The formulation checklist (checklist.py): the call sees the problem text and the model's
variable names only; the diff gives typed flags; and it's report-only and opt-in. Examples
are NL4Opt dev only (the gas problem). Never calls the API."""

import json

import pytest
from fakes import (
    GAS_CHECKLIST,
    GAS_CHECKLIST_REPLY,
    GAS_MODEL,
    GAS_PROBLEM,
    GAS_REPLY,
    INFEASIBLE_REPLY,
    FakeClient,
    status_error,
)

from opt_agent import api, checklist, formulate
from opt_agent.agent import render, run
from opt_agent.api import Cache
from opt_agent.checklist import Checklist, review
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


# ---- the diff: typed flags ---------------------------------------------------------------


def gas_model(**changes) -> LPModel:
    """The gas model with some parts replaced: variables, objective or constraints."""
    return LPModel.model_validate({**GAS_MODEL, **changes})


def gas_checklist(**changes) -> Checklist:
    return Checklist.model_validate({**GAS_CHECKLIST, **changes})


def kinds(model: LPModel, checklist: Checklist = None) -> list[str]:
    return [f.kind for f in review(model, checklist or gas_checklist()).flags]


def term(var, coef):
    return {"var": var, "coef": coef}


def row(name, terms, sense, rhs):
    return {"name": name, "terms": terms, "sense": sense, "rhs": rhs}


DAILY = row("daily gas", [term("pipelines", 8000), term("trains", 2000)], ">=", 1_000_000)
RATIO = row("ratio", [term("trains", 1), term("pipelines", -2)], ">=", 0)


def test_the_model_that_matches_has_no_flags():
    found = review(GAS, gas_checklist())
    assert found.flags == [] and found.notes == []


def test_a_rewritten_or_scaled_row_is_the_same_row():
    rewritten = row("ratio", [term("pipelines", 2), term("trains", -1)], "<=", 0)
    scaled = row("daily gas", [term("pipelines", 4000), term("trains", 1000)], ">=", 500_000)
    assert kinds(gas_model(constraints=[scaled, rewritten])) == []


def test_an_integer_count_made_continuous_is_an_integrality_flag():
    variables = [{"name": "pipelines", "integer": True}, {"name": "trains", "integer": False}]
    found = review(gas_model(variables=variables), gas_checklist()).flags
    assert [(f.kind, f.quote) for f in found] == [("integrality", "the number of trains used")]


def test_unclear_never_flags_integrality():
    variables = [{"name": "pipelines", "integer": False}, {"name": "trains", "integer": False}]
    unclear = [{**v, "kind": "unclear"} for v in GAS_CHECKLIST["variables"]]
    assert kinds(gas_model(variables=variables), gas_checklist(variables=unclear)) == []


def test_a_wrong_number_is_a_coefficient_flag():
    typo = row("daily gas", [term("pipelines", 8000), term("trains", 200)], ">=", 1_000_000)
    (flag,) = review(gas_model(constraints=[typo, RATIO]), gas_checklist()).flags
    assert (flag.kind, flag.constraint) == ("coefficient", "constraint 'daily gas'")


def test_a_flipped_direction_is_a_coefficient_flag():
    flipped = row("ratio", [term("trains", 1), term("pipelines", -2)], "<=", 0)
    assert kinds(gas_model(constraints=[DAILY, flipped])) == ["coefficient"]


def test_a_requirement_with_no_row_is_missing():
    (flag,) = review(gas_model(constraints=[DAILY]), gas_checklist()).flags
    assert flag.kind == "missing" and "twice" in flag.quote


def test_a_row_the_text_doesnt_state_is_extra():
    cap = row("depot", [term("trains", 1)], "<=", 500)
    (flag,) = review(gas_model(constraints=[DAILY, RATIO, cap]), gas_checklist()).flags
    assert (flag.kind, flag.constraint) == ("extra", "constraint 'depot'")


def test_an_upper_bound_the_text_doesnt_state_is_extra():
    variables = [{"name": "pipelines", "integer": True},
                 {"name": "trains", "integer": True, "upper": 500}]  # fmt: skip
    assert kinds(gas_model(variables=variables)) == ["extra"]


def test_a_row_made_from_a_preference_is_invented():
    prefers = {
        "quote": "the company prefers trains",
        "why": "a stated preference",
        "terms": [term("trains", 1), term("pipelines", -1)],
        "sense": ">=",
        "rhs": 0,
    }
    checklist = gas_checklist(not_requirements=[prefers])
    invented = row("prefers trains", [term("trains", 1), term("pipelines", -1)], ">=", 0)
    (flag,) = review(gas_model(constraints=[DAILY, RATIO, invented]), checklist).flags
    assert (flag.kind, flag.quote) == ("invented-from-preference", "the company prefers trains")


def test_a_different_objective_is_flagged_but_a_scaled_one_isnt():
    maximize = {"sense": "max", "terms": GAS_MODEL["objective"]["terms"]}
    assert kinds(gas_model(objective=maximize)) == ["objective"]
    weighted = {"sense": "min", "terms": [term("pipelines", 3), term("trains", 1)]}
    assert kinds(gas_model(objective=weighted)) == ["objective"]
    doubled = {"sense": "min", "terms": [term("pipelines", 2), term("trains", 2)]}
    assert kinds(gas_model(objective=doubled)) == []


def strict_ratio(**changes) -> Checklist:
    ratio = {**GAS_CHECKLIST["requirements"][1], **changes}
    return gas_checklist(requirements=[GAS_CHECKLIST["requirements"][0], ratio])


def test_strict_wording_accepts_the_strict_reading_over_integers():
    tight = row("ratio", [term("trains", 1), term("pipelines", -2)], ">=", 1)
    assert kinds(gas_model(constraints=[DAILY, tight]), strict_ratio(strict=True)) == []
    assert kinds(gas_model(constraints=[DAILY, RATIO]), strict_ratio(strict=True)) == []
    assert kinds(gas_model(constraints=[DAILY, tight]), strict_ratio(strict=False)) == [
        "coefficient"
    ]


def test_the_strict_reading_needs_integer_variables():
    variables = [{"name": "pipelines"}, {"name": "trains"}]  # continuous
    tight = row("ratio", [term("trains", 1), term("pipelines", -2)], ">=", 1)
    checklist = strict_ratio(strict=True)
    checklist.variables[0].kind = checklist.variables[1].kind = "continuous"
    model = gas_model(variables=variables, constraints=[DAILY, tight])
    assert kinds(model, checklist) == ["coefficient"]


def test_could_be_equal_accepts_an_equation():
    equation = row("ratio", [term("trains", 1), term("pipelines", -2)], "==", 0)
    model = gas_model(constraints=[DAILY, equation])
    assert kinds(model, strict_ratio(could_be_equal=True)) == []
    assert kinds(model, strict_ratio(could_be_equal=False)) == ["coefficient"]


def test_unknown_names_and_unwritable_requirements_are_notes_not_flags():
    stray = {**GAS_CHECKLIST["requirements"][1], "terms": [term("ships", 1)]}
    checklist = gas_checklist(
        requirements=[GAS_CHECKLIST["requirements"][0], stray],
        cannot_express=[{"quote": "each ship carries 500", "needs": "ships"}],
    )
    found = review(gas_model(constraints=[DAILY]), checklist)
    assert found.flags == []
    assert len(found.notes) == 2 and all("not checked" in n for n in found.notes)


# ---- report-only, opt-in -----------------------------------------------------------------


def test_the_checklist_changes_no_answer_score_or_revision():
    """The same replies with and without it: the same loop, answer, checks and formulation
    requests; the checklist call comes last, and its flags revise nothing."""
    flagging = json.dumps({**GAS_CHECKLIST, "requirements": GAS_CHECKLIST["requirements"][:1]})
    for replies in [(GAS_REPLY,), (INFEASIBLE_REPLY, INFEASIBLE_REPLY)]:
        plain, checked = FakeClient(*replies), FakeClient(*replies, flagging)
        a = run(GAS_PROBLEM, plain, with_explanation=False)
        b = run(GAS_PROBLEM, checked, with_explanation=False, checklist=True)
        assert b.checklist_flags  # it found something to flag
        assert (a.outcome.stopped, len(a.outcome.attempts)) == (
            b.outcome.stopped, len(b.outcome.attempts)
        )  # fmt: skip
        assert a.solution == b.solution and a.confirmed == b.confirmed
        assert checked.requests[: len(plain.requests)] == plain.requests


def test_it_is_opt_in():
    client = FakeClient(GAS_REPLY)
    result = run(GAS_PROBLEM, client, with_explanation=False)
    assert result.checklist_flags is None and len(client.requests) == 1


def test_flags_are_shown_and_a_clean_check_says_so():
    flagged = run(GAS_PROBLEM, FakeClient(GAS_REPLY, json.dumps(
        {**GAS_CHECKLIST, "requirements": GAS_CHECKLIST["requirements"][:1]})),
        with_explanation=False, checklist=True)  # fmt: skip
    assert "CHECKLIST: 1 difference(s)" in render(flagged) and "extra:" in render(flagged)
    clean = run(GAS_PROBLEM, FakeClient(GAS_REPLY, GAS_CHECKLIST_REPLY), with_explanation=False,
                checklist=True)  # fmt: skip
    assert "Checklist: no differences from the text found." in render(clean)


def test_an_unusable_checklist_is_a_note():
    result = run(GAS_PROBLEM, FakeClient(GAS_REPLY, "not json"), with_explanation=False,
                 checklist=True)  # fmt: skip
    assert result.checklist_flags is None and "no usable checklist" in result.checklist_notes[0]
