"""The silent-failure detector's rule (docs/analysis/silent_detector.md), on made-up text only:
it's tested once, on the follow-up's answers, so nothing here uses them."""

from opt_agent.detector import check, constants
from opt_agent.schema import LPModel


def model(*numbers: float, bounds: tuple[float | None, float | None] = (0, None)) -> LPModel:
    """A one-variable model whose constraints carry `numbers` as right-hand sides."""
    return LPModel.model_validate({
        "variables": [{"name": "x", "lower": bounds[0], "upper": bounds[1], "integer": False}],
        "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [{"name": f"c{i}", "terms": [{"var": "x", "coef": 1}], "sense": "<=",
                         "rhs": n} for i, n in enumerate(numbers)],
    })  # fmt: skip


def values(text: str) -> list[float]:
    return [c.value for c in constants(text)]


def test_reads_whole_numbers_decimals_thousands_signs_and_percentages():
    text = "Each chair needs 3.5 hours, earns $1,200 and loses -4 on returns; 15% is reworked."
    assert values(text) == [3.5, 1200, -4, 15]
    assert [c.percent for c in constants(text)] == [False, False, False, True]
    assert values("a share of 20 percent") == [20]


def test_skips_names_ordinals_and_format_instructions():
    assert values("Product 1 and machine 2 on Day 3 make 40 units") == [40]
    assert values("variables x1 and A2, plant #4") == []
    assert values("in the 5th week, the 1st shift") == []
    assert values("round to 2 decimal places, or 3 significant figures") == []


def test_a_range_gives_two_positive_numbers_and_a_list_each_number():
    assert values("between 10-20 tons") == [10, 20]
    assert values("sizes 3,4 and 5") == [3, 4, 5]


def test_every_constant_present_is_not_flagged():
    assert not check("at most 40 hours and 25 units", model(40, 25)).flagged


def test_a_missing_constant_is_flagged_and_named():
    verdict = check("at most 40 hours and 25 units", model(40))
    assert verdict.flagged
    assert [c.text for c in verdict.missing] == ["25"]


def test_unit_conversions_and_percentages_count():
    assert not check("a 30 minute break", model(0.5)).flagged  # minutes -> hours
    assert not check("2 hours", model(120)).flagged  # hours -> minutes
    assert not check("$3.5 million", model(3_500_000)).flagged
    assert not check("at least 15% of output", model(0.15)).flagged
    assert not check("prices rise 15%", model(1.15)).flagged
    assert not check("a 15% discount", model(0.85)).flagged
    assert check("a 15 ton limit", model(1.15)).flagged  # only a percentage gets 1 +/- p


def test_signs_bounds_and_zero():
    assert not check("a loss of 7", model(-7)).flagged
    assert not check("up to 9 crates", model(bounds=(0, 9))).flagged
    assert not check("no less than 0 units", model()).flagged
