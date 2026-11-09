"""Revision 1 of the checklist comparison (docs/FOLLOWUP_DEV_LOG.md): binary domain,
auxiliary variables, LP implication both ways, answer relevance, and the LP-relaxation note
for the estimate. Examples are NL4Opt dev only (the gas problem). Never calls the API."""

import json

from fakes import GAS_CHECKLIST, GAS_MODEL, GAS_PROBLEM, GAS_REPLY, FakeClient

from opt_agent.agent import run
from opt_agent.checklist import Checklist, review
from opt_agent.schema import LPModel
from opt_agent.solver import solve

DAILY = {"name": "daily gas", "terms": [{"var": "pipelines", "coef": 8000},
                                        {"var": "trains", "coef": 2000}],
         "sense": ">=", "rhs": 1_000_000}  # fmt: skip
RATIO = {"name": "ratio", "terms": [{"var": "trains", "coef": 1}, {"var": "pipelines", "coef": -2}],
         "sense": ">=", "rhs": 0}  # fmt: skip


def gas(variables=None, extra_rows=(), extra_variables=()) -> LPModel:
    variables = variables or GAS_MODEL["variables"]
    return LPModel.model_validate({**GAS_MODEL, "variables": [*variables, *extra_variables],
                                   "constraints": [DAILY, RATIO, *extra_rows]})  # fmt: skip


def checklist(**changes) -> Checklist:
    return Checklist.model_validate({**GAS_CHECKLIST, **changes})


def kinds(model, values=None, check=None):
    return [f.kind for f in review(model, check or checklist(), values).flags]


def optimum(model) -> dict[str, float]:
    return solve(model).values


def row(name, terms, sense, rhs):
    return {"name": name, "terms": [{"var": v, "coef": a} for v, a in terms.items()],
            "sense": sense, "rhs": rhs}  # fmt: skip


# ---- 1. binary domain --------------------------------------------------------------------


def test_an_upper_bound_of_1_on_an_integer_variable_is_its_domain_not_a_row():
    binary = [{"name": "pipelines", "integer": True}, {"name": "trains", "integer": True},
              {"name": "permit", "integer": True, "upper": 1}]  # fmt: skip
    model = gas(variables=binary, extra_rows=[row("permit use", {"permit": 1, "trains": 1},
                                                  "<=", 999)])  # fmt: skip
    found = review(model, checklist())
    assert "the upper bound of 'permit'" not in [f.constraint for f in found.flags]
    assert any("binary" in note for note in found.notes)


def test_other_bounds_are_still_checked():
    capped = [{"name": "pipelines", "integer": True},
              {"name": "trains", "integer": True, "upper": 500}]  # fmt: skip
    assert kinds(gas(variables=capped)) == ["extra"]


# ---- 2. auxiliary variables --------------------------------------------------------------


def test_a_row_with_a_variable_no_requirement_uses_is_a_modeling_device():
    """Like subtour elimination's position variables, or a facility's open/closed switch."""
    order = {"name": "order", "lower": 0, "upper": None, "integer": False}
    device = row("device", {"order": 1, "trains": -1}, "<=", 3)
    found = review(gas(extra_rows=[device], extra_variables=[order]), checklist())
    assert found.flags == [] and any("no requirement uses" in note for note in found.notes)


def test_integrality_isnt_checked_on_an_auxiliary_variable():
    order = {"name": "order", "lower": 0, "upper": None, "integer": False}
    device = row("device", {"order": 1, "trains": -1}, "<=", 3)
    listed = [*GAS_CHECKLIST["variables"], {"name": "order", "kind": "integer", "quote": "q"}]
    model = gas(extra_rows=[device], extra_variables=[order])
    assert kinds(model, check=checklist(variables=listed)) == []


# ---- 3. implication, both ways -----------------------------------------------------------


def test_a_row_the_requirements_imply_isnt_extra():
    weaker = row("half the gas", {"pipelines": 8000, "trains": 2000}, ">=", 500_000)
    assert kinds(gas(extra_rows=[weaker])) == []


def test_a_requirement_the_models_rows_imply_isnt_missing():
    """With p, t >= 0, 8000p + 2000t >= 1e6 and t >= 2p imply p + t >= 250."""
    implied = {**GAS_CHECKLIST["requirements"][0], "quote": "at least 100 vehicles",
               "terms": [{"var": "pipelines", "coef": 1}, {"var": "trains", "coef": 1}],
               "sense": ">=", "rhs": 100}  # fmt: skip
    check = checklist(requirements=[*GAS_CHECKLIST["requirements"], implied])
    assert kinds(gas(), check=check) == []


def test_a_requirement_nothing_implies_is_still_missing():
    cap = {**GAS_CHECKLIST["requirements"][0], "quote": "at most 150 trains",
           "terms": [{"var": "trains", "coef": 1}], "sense": "<=", "rhs": 150}  # fmt: skip
    check = checklist(requirements=[*GAS_CHECKLIST["requirements"], cap])
    assert kinds(gas(), check=check) == ["missing"]


# ---- 4. answer relevance -----------------------------------------------------------------


def cap_requirement(limit):
    return {**GAS_CHECKLIST["requirements"][0], "quote": f"at most {limit} trains",
            "terms": [{"var": "trains", "coef": 1}], "sense": "<=", "rhs": limit}  # fmt: skip


def test_a_requirement_the_optimum_satisfies_is_a_note_with_the_answer():
    """The optimum has 168 trains: adding "at most 200 trains" can't change the answer."""
    check = checklist(requirements=[*GAS_CHECKLIST["requirements"], cap_requirement(200)])
    model = gas()
    assert kinds(model, check=check) == ["missing"]  # without the answer: flagged
    assert kinds(model, optimum(model), check=check) == []


def test_a_requirement_the_optimum_violates_is_flagged():
    check = checklist(requirements=[*GAS_CHECKLIST["requirements"], cap_requirement(150)])
    model = gas()
    assert kinds(model, optimum(model), check=check) == ["missing"]


def test_an_extra_row_that_doesnt_bind_is_a_note_one_that_binds_is_flagged():
    slack = gas(extra_rows=[row("pipeline permits", {"pipelines": 1}, "<=", 100)])
    assert kinds(slack, optimum(slack)) == []  # 83 pipelines: 17 to spare
    tight = gas(extra_rows=[row("pipeline permits", {"pipelines": 1}, "<=", 80)])
    assert kinds(tight, optimum(tight)) == ["extra"]  # it binds, and it moves the answer


# ---- 5. the estimate and the LP relaxation ------------------------------------------------


def estimate(objective):
    return json.dumps({"status": "optimal", "objective": objective})


def test_an_estimate_equal_to_the_lp_relaxation_is_a_note_not_low_confidence():
    """The gas model's LP relaxation is 250 (its integer optimum is 251)."""
    result = run(GAS_PROBLEM, FakeClient(GAS_REPLY, estimate(250)), with_explanation=False,
                 max_attempts=1, estimate=True)  # fmt: skip
    assert result.low_confidence is False and "LP relaxation" in result.low_confidence_reason


def test_any_other_disagreement_is_still_low_confidence():
    result = run(GAS_PROBLEM, FakeClient(GAS_REPLY, estimate(249)), with_explanation=False,
                 max_attempts=1, estimate=True)  # fmt: skip
    assert result.low_confidence is True
