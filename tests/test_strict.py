import itertools
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    load_records,
    matching_reading,
    readings,
    scorable,
)
from opt_agent.nl4opt import Note
from opt_agent.schema import Constraint, Term
from opt_agent.solver import Status
from opt_agent.strict import step, strict_constraints, tighten

RECORDS = {split: load_records(GROUND_TRUTH_DIR / f"{split}.json") for split in ("dev", "test")}
BY_ID = {r.id: r for rs in RECORDS.values() for r in rs}


def row(coefs: dict[str, float], sense: str, rhs: float) -> Constraint:
    terms = [Term(var=v, coef=c) for v, c in coefs.items()]
    return Constraint(name="c", terms=terms, sense=sense, rhs=rhs)


@pytest.mark.parametrize(
    ("coefs", "expected"),
    [({"x": 1, "y": -1}, 1), ({"x": 0.6, "y": -0.4}, Fraction(1, 5)),
     ({"x": 3000, "y": 1000}, 1000), ({"x": 0.35, "y": 0.65}, Fraction(1, 20))],
)  # fmt: skip
def test_the_step_is_the_smallest_move_of_the_left_side(coefs, expected):
    assert step(row(coefs, ">=", 0)) == expected


@pytest.mark.parametrize(
    ("coefs", "sense", "rhs", "tight"),
    [
        ({"x": 1, "y": -1}, ">=", 0, 1),  # x > y  ->  x >= y + 1
        ({"x": 1}, "<=", 15, 14),  # less than 15 -> at most 14
        ({"x": 0.6, "y": -0.4}, ">=", 0, 0.2),  # 3x - 2y > 0  ->  3x - 2y >= 1
        ({"x": 3000, "y": 1000}, "<=", 150000, 149000),  # a wage bill "below" $150,000
        ({"x": 1}, ">=", 2.5, 3),
        ({"x": 1}, "<=", 2.5, 2),
    ],
)
def test_tighten(coefs, sense, rhs, tight):
    assert tighten(row(coefs, sense, rhs)).rhs == pytest.approx(tight)


decimals = st.integers(-30, 30).map(lambda k: k / 10) | st.integers(-300, 300).map(
    lambda k: k / 100
)


@given(
    a=decimals.filter(bool),
    b=decimals.filter(bool),
    rhs=decimals,
    sense=st.sampled_from([">=", "<="]),
)
def test_the_tightened_row_holds_exactly_where_the_strict_one_does(a, b, rhs, sense):
    """Brute force over every integer point in a box, in exact arithmetic: a.x > rhs
    (or a.x < rhs) holds exactly where the tightened non-strict row holds."""
    c = row({"x": a, "y": b}, sense, rhs)
    t = tighten(c)
    fa, fb, frhs, ftight = (Fraction(repr(v)) for v in (a, b, rhs, t.rhs))
    for x, y in itertools.product(range(-12, 13), repeat=2):
        lhs = fa * x + fb * y
        strict = lhs > frhs if sense == ">=" else lhs < frhs
        tightened = lhs >= ftight if sense == ">=" else lhs <= ftight
        assert strict == tightened, (x, y)


def test_strict_constraints_are_read_from_the_notes():
    notes = [
        Note(
            kind="strict-wording", detail="c2_xy: text says 'must exceed' (strict); modeled as >="
        ),
        Note(kind="unlisted-variable", detail="c0_linear: ['x'] not listed, so coefficient 0"),
    ]
    assert strict_constraints(notes) == ["c2_xy"]


def test_every_integer_problem_with_strict_wording_has_a_strict_reading():
    for r in BY_ID.values():
        noted = r.error is None and strict_constraints(r.notes)
        assert (r.strict is not None) == bool(noted and r.integrality.kind == "integer"), r.id


@pytest.mark.parametrize(
    ("problem", "annotated", "strict"),
    [
        ("615752596", 80, 76),  # "doses of medicine B must be larger than doses of A"
        ("-1243268146", 3200, 3220),  # "more first-dose than second-dose vaccines"
        ("1151835649", 0, 26),  # was a do-nothing optimum
        ("-1394927728", 150000, "infeasible"),  # a wage bill "below" $150,000
        ("1789644271", 6, "infeasible"),  # "electric grills must be less than gas grills"
    ],
)
def test_known_strict_answers(problem, annotated, strict):
    r = BY_ID[problem]
    shown = (
        r.strict.ip.objective if r.strict.ip.status is Status.OPTIMAL else r.strict.ip.status.value
    )
    assert (r.ip.objective, shown) == (annotated, strict)


def test_either_reading_is_accepted_and_the_one_used_is_named():
    r = BY_ID["615752596"]
    assert [name for name, _ in readings(r)] == ["annotated", "strict"]
    assert matching_reading(r, Status.OPTIMAL, 80.0) == "annotated"
    assert matching_reading(r, Status.OPTIMAL, 76.0) == "strict"
    assert matching_reading(r, Status.OPTIMAL, 85.714) is None  # the LP optimum: not integer
    assert matching_reading(r, Status.INFEASIBLE, None) is None


def test_a_status_can_be_the_strict_answer():
    r = BY_ID["1789644271"]
    assert matching_reading(r, Status.INFEASIBLE, None) == "strict"
    assert matching_reading(r, Status.OPTIMAL, 6.0) == "annotated"


def test_continuous_problems_have_only_the_annotated_reading():
    continuous = [
        r for r in BY_ID.values() if r.error is None and r.integrality.kind == "continuous"
    ]
    assert all({name for name, _ in readings(r)} <= {"annotated"} for r in continuous)


def test_nine_of_the_twenty_five_scorable_test_answers_change():
    strict = [r for r in RECORDS["test"] if r.strict and scorable(r)]
    changed = [
        r
        for r in strict
        if (r.ip.status, r.ip.objective) != (r.strict.ip.status, r.strict.ip.objective)
    ]
    assert (len(changed), len(strict)) == (9, 25)
