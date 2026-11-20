"""scripts/ip_slack_check.py: the claims a clause makes, the constraints it names, the re-solve
on small models whose answers are worked out by hand, the score on synthetic labels, and that
the committed flags and results are the script's own (docs/analysis/ip_slack_check.md). No API
calls: the explanations are the committed run's (runs/explain-dev)."""

import importlib.util
import json
from pathlib import Path

import pytest

from opt_agent.ground_truth import solve_checked
from opt_agent.schema import LPModel

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ip_slack_check", ROOT / "scripts" /
                                              "ip_slack_check.py")  # fmt: skip
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def claimed(text: str, names: list[str]) -> list[str]:
    return list(check.claims_in(text, names))


@pytest.mark.parametrize("sentence", [
    "The $200 budget is not the bottleneck, since $2 of it stays unspent.",
    "Packaging isn't the limit, since 1,500 hours go unused.",
    "Measuring time has 54 hours left over, so it is not what holds the plan back.",
    "It has 1,366 to spare and isn't limiting the result.",
    "So none of those rules restrict the answer.",
    "So neither is currently limiting the plan.",
    "So neither is the main constraint.",
    "The plan is not held back by either one.",
    "The car limit and the wood are not binding.",
    "The wood constraint is non-binding.",
])  # fmt: skip
def test_each_phrasing_is_a_claim(sentence):
    assert any(p.search(sentence) for p in check.NEGATED)


@pytest.mark.parametrize("sentence", [
    "No constraint is fully used, so the plan has room to spare.",  # a fact about slack
    "Neither constraint is fully used: the flower requirement has 2 units spare.",
    "The budget is not fully used, leaving $140 unspent.",
    "The model does not give shadow prices, so it cannot say what the flyer limit is worth.",
    "The pollution rule is the constraint that limits the plan.",
])  # fmt: skip
def test_slack_facts_and_positive_claims_are_not(sentence):
    assert not any(p.search(sentence) for p in check.NEGATED)


def test_a_contrast_starts_a_new_clause():
    assert check.clauses("The budget isn't what limits the plan; the trip requirement is. "
                         "Chocolate demand is not the constraint, but staffing is.") == [
        "The budget isn't what limits the plan", "the trip requirement is.",
        "Chocolate demand is not the constraint", "staffing is."]  # fmt: skip


def test_the_constraints_named_before_the_phrase_are_the_claim():
    names = ["budget", "trips_required"]
    assert claimed("The budget isn't what limits the plan; the trip requirement is.",
                   names) == ["budget"]  # fmt: skip
    names = ["wood", "time", "sofa_bed_ratio"]
    assert claimed("The wood (620) and time (1055) limits are not binding, and the only "
                   "binding rule is that sofas must equal twice the number of beds.",
                   names) == ["wood", "time"]  # fmt: skip


def test_after_the_phrase_when_nothing_is_named_before_it():
    names = ["manual access limit", "manual use limit", "minimum electric jacks"]
    text = ("The other rules are not holding it back: the manual-use cap has 2 spare, and "
            "the minimum of 5 electric jacks has 10 spare.")  # fmt: skip
    assert claimed(text, names) == ["manual use limit", "minimum electric jacks"]


def test_a_name_is_matched_as_a_phrase_or_by_its_distinctive_words():
    names = ["gondola share limit", "bus to gondola ratio", "throughput"]
    assert check.named("The gondola share rule and the bus-to-gondola ratio both have room",
                       names) == ["gondola share limit", "bus to gondola ratio"]  # fmt: skip
    # "time" and "hours" say what kind of constraint it is, not which one
    names = ["drying machine time", "medicinal herbs"]
    assert check.named("the drying machine has 20 seconds left over", names) == names[:1]
    assert check.distinctive("time") == {"time"}  # a name with no distinctive word keeps its own


def test_a_name_whose_words_are_part_of_anothers_match_is_dropped():
    names = ["cones_at_least_2x_tubs", "min_tubs", "capacity_oz"]
    assert check.named("The requirement that cones be at least twice the tubs has 1,366 to "
                       "spare", names) == ["cones_at_least_2x_tubs"]  # fmt: skip
    names = ["chocolate demand", "vanilla demand"]
    assert check.named("Chocolate demand is", names) == ["chocolate demand"]


def model(*constraints, integer: bool = True, upper_o: float | None = None) -> LPModel:
    """max 50 r + 30 o over r, o >= 0, the rickshaw problem's shape (dev -640645082)."""
    return LPModel.model_validate({
        "variables": [{"name": "r", "lower": 0, "upper": None, "integer": integer},
                      {"name": "o", "lower": 0, "upper": upper_o, "integer": integer}],
        "objective": {"sense": "max", "terms": [{"var": "r", "coef": 50},
                                                {"var": "o", "coef": 30}]},
        "constraints": [{"name": n, "terms": [{"var": v, "coef": c} for v, c in t],
                         "sense": "<=", "rhs": rhs} for n, t, rhs in constraints]})  # fmt: skip


BUDGET = ("budget", [("r", 10), ("o", 8)], 200)  # 10 r + 8 o <= 200
POLLUTION = ("pollution", [("r", 1), ("o", -1)], 0)  # r <= o
CAP = ("cap", [("o", 1)], 30)  # o <= 30


def verdict(m: LPModel, name: str) -> dict:
    return check.changes_the_optimum(m, name, solve_checked(m))


def test_slack_in_an_integer_program_can_still_limit_it():
    # r = o = 11 earns 880 and spends 198 of 200: the budget has slack 2, and without it the
    # model is unbounded (r = o can grow forever)
    m = model(BUDGET, POLLUTION)
    assert solve_checked(m).objective == pytest.approx(880)
    assert verdict(m, "budget") == {"dropped_status": "unbounded", "dropped_objective": None,
                                    "verdict": "flagged"}  # fmt: skip
    # with o <= 15 too, the optimum without the budget is finite: r = o = 15, 1200
    found = verdict(model(BUDGET, POLLUTION, upper_o=15), "budget")
    assert found["verdict"] == "flagged" and found["dropped_objective"] == pytest.approx(1200)


def test_a_constraint_that_never_limits_holds():
    # o <= 30 has slack 19 at r = o = 11 and nothing changes without it, in the IP and the LP
    assert verdict(model(BUDGET, POLLUTION, CAP), "cap")["verdict"] == "holds"
    assert verdict(model(BUDGET, POLLUTION, CAP, integer=False), "cap")["verdict"] == "holds"


def test_an_lp_is_never_re_solved():
    row = {"problem": "p", "explanation": "The cap is not the limit.",
           "model": model(BUDGET, POLLUTION, CAP, integer=False).model_dump(),
           "facts": {"objective": 20000 / 18, "slack": {"cap": 18.9}}}  # fmt: skip
    summary, claims = check.check_row(row)
    assert summary == {"problem": "p", "integer_program": False, "claims": 1, "flagged": False,
                       "undetermined": False}  # fmt: skip
    assert claims[0]["verdict"] == "not checked (an LP)"


def test_the_score_counts_explanations_and_lists_the_disagreements():
    flags = {"per_explanation": [
        {"problem": p, "integer_program": p != "e", "flagged": p in "ab"} for p in "abcde"],
        "claims": [{"kind": "limit", "verdict": "flagged"}, {"kind": "binding",
                                                             "verdict": "holds"}]}  # fmt: skip
    labels = {"a": True, "b": False, "c": True, "d": False, "e": True}
    found = check.compute_results(flags, labels)
    assert (found["precision"]["k"], found["precision"]["n"]) == (1, 2)
    assert (found["recall"]["k"], found["recall"]["n"]) == (1, 3)
    assert (found["recall_integer_programs"]["k"], found["recall_integer_programs"]["n"]) == (1, 2)
    assert found["flagged_but_labeled_fine"] == ["b"]
    assert found["labeled_false_not_flagged"] == ["c", "e"]
    with pytest.raises(SystemExit, match="same problems"):
        check.compute_results(flags, {"a": True})


def test_the_committed_flags_are_the_scripts_own():
    committed = json.loads(check.OUT.read_text())
    flags = check.compute_flags()
    assert {k: committed[k] for k in flags} == flags
    assert flags["explanations"] == 88 and flags["integer_programs"] == 73


def test_the_doc_shows_the_committed_results():
    committed = json.loads(check.OUT.read_text())
    if "results" not in committed:
        pytest.skip("not scored yet")
    assert check.compute_results(committed, check.read_labels()) == committed["results"]
    assert check.render(committed, committed["results"]) in check.DOC.read_text()
