"""Checks on the committed ground truth files. No network: raw data isn't needed here."""

import json

import pytest
from pytest import approx

from opt_agent import orlm
from opt_agent.data import ORLM_ANSWERS
from opt_agent.ground_truth import (
    EXCLUSIONS_PATH,
    GROUND_TRUTH_DIR,
    INTEGRALITY_PATH,
    REVIEWS_PATH,
    RISKY_NOTES,
    SPLITS,
    answer,
    as_integer,
    blind_gradable,
    does_nothing,
    equality_model,
    lacks_optimum,
    load_exclusions,
    load_integrality,
    load_records,
    load_reviews,
    matching_reading,
    needs_hand_label,
    readings,
    render_report,
    scorable,
)
from opt_agent.highs import solve_with_highs
from opt_agent.solver import Solution
from opt_agent.strict import strict_constraints, strict_model
from opt_agent.verify import same_answer

RECORDS = {split: load_records(GROUND_TRUTH_DIR / f"{split}.json") for split in SPLITS}


def committed(solve) -> Solution:
    """A committed CheckedSolve as a Solution, so it can be compared with a fresh solve."""
    return Solution(solver="cbc", status=solve.status, objective=solve.objective,
                    values=solve.values)  # fmt: skip


@pytest.mark.parametrize("split", SPLITS)
def test_highs_reproduces_every_committed_answer(split):
    """An independent solver re-derives every LP, IP and strict-reading answer from the
    committed models. This also catches drift: if the code changes but the data files
    aren't rebuilt.
    """
    for r in RECORDS[split]:
        if r.error is None:
            assert same_answer(r.model, committed(r.lp), solve_with_highs(r.model)), r.id
            integer = as_integer(r.model)
            assert same_answer(integer, committed(r.ip), solve_with_highs(integer)), r.id
        if r.strict is not None:
            tight, changed = strict_model(as_integer(r.model), strict_constraints(r.notes))
            assert changed == r.strict.changed, r.id
            assert same_answer(tight, committed(r.strict.ip), solve_with_highs(tight)), r.id
        if r.equality is not None:
            equal, changed = equality_model(r.model, r.review.equality)
            assert changed == r.equality.changed, r.id
            assert same_answer(equal, committed(r.equality.lp), solve_with_highs(equal)), r.id
            integer = as_integer(equal)
            assert same_answer(integer, committed(r.equality.ip), solve_with_highs(integer)), r.id


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


@pytest.mark.parametrize(
    "distrust", [{"highs_agrees": False}, {"check_problems": ["constraint 'c0' is violated"]}]
)
def test_an_answer_that_fails_a_check_is_no_answer(distrust):
    """Every committed answer passes both checks today; one that didn't must not be scored."""
    [ducks] = [r for r in RECORDS["test"] if r.id == "349208478"]  # labeled integer
    assert scorable(ducks)
    broken = ducks.model_copy(update={"ip": ducks.ip.model_copy(update=distrust)})
    assert answer(broken) is None
    assert not scorable(broken) and not blind_gradable(broken)
    assert answer(broken.model_copy(update={"lp": broken.ip})) is None  # the LP is unused


def test_an_unconverted_problem_has_no_answer():
    [unconverted] = [r for r in RECORDS["dev"] if r.error is not None][:1]
    assert answer(unconverted) is None and not scorable(unconverted)


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


def test_problems_used_while_building_the_agent_are_not_scored():
    exclusions = load_exclusions(EXCLUSIONS_PATH)
    assert set(exclusions) == {("test", "1117636837"), ("test", "-725478241")}
    by_key = {(split, r.id): r for split, rs in RECORDS.items() for r in rs}
    for key, reason in exclusions.items():
        r = by_key[key]
        assert r.excluded == reason and reason
        assert answer(r) is not None or key == ("test", "-725478241")  # ads: no optimum
        assert not scorable(r) and not blind_gradable(r)
    assert all(r.excluded is None for (split, _), r in by_key.items() if split == "dev")


@pytest.mark.parametrize(
    "problem, annotated, equal",
    [("-169306566", 56, 32), ("-1765797791", 54, 50), ("-1715698555", 1240, 1215)],
)
def test_the_equality_readings_match_the_hand_reviews(problem, annotated, equal):
    """Each ambiguous-text review states both answers by hand (from ORLM, or worked out);
    the computed "=" reading must reproduce them."""
    r = {x.id: x for x in RECORDS["test"]}[problem]
    assert (r.ip.objective, r.equality.ip.objective) == (annotated, equal)
    assert f"{annotated}" in r.review.reason and f"{equal}" in r.review.reason
    assert matching_reading(r, r.ip.status, annotated) == "annotated"
    assert matching_reading(r, r.ip.status, equal) == "equality"


def test_only_reviewed_ambiguous_problems_have_an_equality_reading():
    for records in RECORDS.values():
        for r in records:
            named = r.review is not None and bool(r.review.equality)
            assert (r.equality is not None) == named, r.id
            if named:
                assert r.review.verdict == "ambiguous-text", r.id


def test_lenient_scoring_accepts_either_integrality():
    r = {x.id: x for x in RECORDS["dev"]}["439170086"]  # gas: IP 251, LP 250
    assert matching_reading(r, r.lp.status, 250.0) is None
    assert matching_reading(r, r.lp.status, 250.0, lenient=True) == "annotated"
    assert len(readings(r, lenient=True)) == 2


def test_the_tolerance_is_relative_and_absolute_near_zero():
    r = {x.id: x for x in RECORDS["dev"]}["439170086"]
    assert matching_reading(r, r.ip.status, 251 * (1 + 5e-7)) == "annotated"
    assert matching_reading(r, r.ip.status, 251 * (1 + 5e-5)) is None
    assert matching_reading(r, r.ip.status, 251 * (1 + 5e-5), tolerance=1e-4) == "annotated"
