"""Checks on the committed ground truth files. No network: raw data isn't needed here."""

import json

import pytest
from pytest import approx

from opt_agent import orlm
from opt_agent.data import ORLM_ANSWERS
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    INTEGRALITY_PATH,
    REVIEWS_PATH,
    RISKY_NOTES,
    SPLITS,
    answer,
    as_integer,
    blind_gradable,
    does_nothing,
    lacks_optimum,
    load_integrality,
    load_records,
    load_reviews,
    needs_hand_label,
    render_report,
    scorable,
)
from opt_agent.highs import solve_with_highs
from opt_agent.solver import Solution
from opt_agent.verify import same_answer

RECORDS = {split: load_records(GROUND_TRUTH_DIR / f"{split}.json") for split in SPLITS}


def committed(solve) -> Solution:
    """A committed CheckedSolve as a Solution, so it can be compared with a fresh solve."""
    return Solution(solver="cbc", status=solve.status, objective=solve.objective,
                    values=solve.values)  # fmt: skip


@pytest.mark.parametrize("split", SPLITS)
def test_highs_reproduces_every_committed_answer(split):
    """An independent solver re-derives every LP and IP answer from the committed models.

    This also catches drift: if the code changes but the data files aren't rebuilt.
    """
    for r in RECORDS[split]:
        if r.error is None:
            assert same_answer(r.model, committed(r.lp), solve_with_highs(r.model)), r.id
            integer = as_integer(r.model)
            assert same_answer(integer, committed(r.ip), solve_with_highs(integer)), r.id


@pytest.mark.parametrize("split", SPLITS)
def test_committed_solutions_passed_their_checks(split):
    for r in RECORDS[split]:
        if r.error is None:
            assert r.lp.highs_agrees and r.ip.highs_agrees, r.id
            assert r.lp.check_problems == [] and r.ip.check_problems == [], r.id


def test_known_answers_in_the_test_split():
    by_id = {r.id: r for r in RECORDS["test"]}
    fishery, ducks = by_id["1117636837"], by_id["349208478"]
    assert (fishery.lp.objective, fishery.ip.objective) == approx((3000, 3000))
    assert (ducks.lp.objective, ducks.ip.objective) == approx((1140, 1160))
    assert ducks.integrality.kind == "integer"  # boat trips: the answer is 1160
    assert answer(ducks).objective == approx(1160)


def test_answer_follows_the_integrality_label():
    for records in RECORDS.values():
        for r in records:
            if r.error is None:
                assert answer(r) is (r.ip if r.integrality.kind == "integer" else r.lp), r.id


def test_every_problem_where_integrality_matters_has_a_hand_label():
    for split, records in RECORDS.items():
        for r in records:
            if needs_hand_label(r):
                assert r.integrality.source != "rule", f"{split} {r.id} needs a hand label"


def test_every_hand_label_is_used():
    used = {(split, r.id): r.integrality for split, rs in RECORDS.items() for r in rs}
    for key, label in load_integrality(INTEGRALITY_PATH).items():
        assert used[key] == label, key


def test_every_review_points_at_a_real_problem():
    ids = {(split, r.id) for split, rs in RECORDS.items() for r in rs}
    assert set(load_reviews(REVIEWS_PATH)) <= ids


def test_every_flagged_problem_is_reviewed():
    """ORLM-based flags are checked when the report is built (ORLM's data isn't in git)."""
    for split, records in RECORDS.items():
        for r in records:
            risky = any(n.kind in RISKY_NOTES for n in r.notes)
            if r.error is None and (lacks_optimum(r) or does_nothing(r) or risky):
                assert r.review is not None, f"{split} {r.id} needs a hand review"


def test_annotation_errors_that_change_the_answer_are_not_scorable():
    for records in RECORDS.values():
        for r in records:
            if r.review and r.review.verdict == "annotation-error":
                assert scorable(r) is not r.review.answer_affected, r.id
                assert not blind_gradable(r), r.id


def test_an_annotation_error_that_leaves_the_answer_alone_stays_scorable():
    """Dev #4: the demand constraint omits a coefficient, but the optimum is unchanged."""
    [clothing] = [r for r in RECORDS["dev"] if r.id == "471112257"]
    assert scorable(clothing) and not blind_gradable(clothing)


def test_report_is_up_to_date():
    orlm_path = ORLM_ANSWERS.path
    path = GROUND_TRUTH_DIR.parent.parent / orlm_path
    if not path.exists():
        pytest.skip("ORLM's answers aren't downloaded (run `python -m opt_agent.data`)")
    expected = render_report(RECORDS, orlm.load_answers(path))
    assert (GROUND_TRUTH_DIR / "REPORT.md").read_text() == expected


def test_ground_truth_files_are_plain_json():
    for split in SPLITS:
        rows = json.loads((GROUND_TRUTH_DIR / f"{split}.json").read_text())
        assert len(rows) == len(RECORDS[split])
