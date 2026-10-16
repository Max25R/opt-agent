import pytest
from problems import WYNDOR, terms
from pydantic import ValidationError

from opt_agent.schema import LPModel

# What the LLM will send back in milestone 4: plain JSON matching the schema.
SMALL_MODEL_JSON = """
{
  "variables": [{"name": "x", "lower": 0, "upper": 10, "integer": true}, {"name": "y"}],
  "objective": {"sense": "max", "terms": [{"var": "x", "coef": 2}, {"var": "y", "coef": 1}]},
  "constraints": [
    {"name": "capacity", "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": 1}],
     "sense": "<=", "rhs": 8}
  ]
}
"""


def make(variables=None, objective=None, constraints=None) -> dict:
    """A small valid model as a dict; override one part to make it invalid."""
    return {
        "variables": variables or [{"name": "x"}, {"name": "y"}],
        "objective": objective or {"sense": "min", "terms": terms({"x": 1, "y": 1})},
        "constraints": constraints
        or [{"name": "c", "terms": terms({"x": 1}), "sense": ">=", "rhs": 1}],
    }


def test_parses_json_with_defaults():
    model = LPModel.model_validate_json(SMALL_MODEL_JSON)
    x, y = model.variables
    assert (x.lower, x.upper, x.integer) == (0, 10, True)
    assert (y.lower, y.upper, y.integer) == (0, None, False)  # defaults: x >= 0, continuous
    assert model.is_mip


def test_json_round_trip():
    assert LPModel.model_validate_json(WYNDOR.model_dump_json()) == WYNDOR


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            make(objective={"sense": "min", "terms": terms({"x": 1, "z": 1})}),
            "objective uses undeclared variable 'z'",
        ),
        (
            make(variables=[{"name": "x"}, {"name": "x"}, {"name": "y"}]),
            "variable 'x' is declared more than once",
        ),
        (
            make(
                constraints=[{"name": "c", "terms": terms({"x": 1}), "sense": ">=", "rhs": 1}] * 2
            ),
            "constraint 'c' is declared more than once",
        ),
        (
            make(variables=[{"name": "x", "lower": 5, "upper": 1}, {"name": "y"}]),
            "lower bound 5.0 > upper 1.0",
        ),
        (
            make(variables=[{"name": "x"}, {"name": "y"}, {"name": "unused"}]),
            "variable 'unused' is declared but never used",
        ),
        (
            make(objective={"sense": "min", "terms": terms({"x": 0, "y": 0})}),
            "objective has no nonzero terms",
        ),
        (
            make(
                objective={"sense": "min", "terms": [{"var": "x", "coef": 1}] * 2 + terms({"y": 1})}
            ),
            "objective lists variable 'x' more than once",
        ),
    ],
    ids=[
        "undeclared",
        "dup-var",
        "dup-constraint",
        "bounds",
        "unused",
        "zero-objective",
        "repeated-term",
    ],
)
def test_rejects_inconsistent_models(data, message):
    with pytest.raises(ValidationError, match=message):
        LPModel.model_validate(data)


@pytest.mark.parametrize(
    "data",
    [
        make(objective={"sense": "minimize", "terms": terms({"x": 1, "y": 1})}),
        make(variables=[{"name": "x", "upper": float("nan")}, {"name": "y"}]),
        {**make(), "notes": "unknown keys are rejected, not ignored"},
    ],
    ids=["bad-sense", "nan", "extra-key"],
)
def test_rejects_malformed_fields(data):
    with pytest.raises(ValidationError):
        LPModel.model_validate(data)


def test_reports_every_problem_at_once():
    data = make(
        variables=[{"name": "x", "lower": 3, "upper": 1}, {"name": "y"}],
        objective={"sense": "min", "terms": terms({"x": 1, "y": 1, "ghost": 2})},
    )
    with pytest.raises(ValidationError) as error:
        LPModel.model_validate(data)
    assert "lower bound" in str(error.value) and "'ghost'" in str(error.value)
