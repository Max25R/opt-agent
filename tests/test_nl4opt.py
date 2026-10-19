import pytest
from problems import DUCKS, FISHERY
from pytest import approx

from opt_agent.ground_truth import as_integer
from opt_agent.nl4opt import (
    ConversionError,
    convert,
    implied_operator,
    is_strict,
    load_split,
    objective_sense,
    parse_number,
)
from opt_agent.solver import Status, solve


def annotation(constraints, objective=None, names=("x", "y"), order_mapping=None, document=""):
    """A minimal annotation in NL4Opt's format, for testing one declaration at a time."""
    return {
        "document": document,
        "vars": list(names),
        "order_mapping": order_mapping or {n: i for i, n in enumerate(names)},
        "obj_declaration": objective
        or {"type": "objvar", "direction": "maximize", "name": "total", "vars": list(names)},
        "const_declarations": constraints,
    }


def only_constraint(ann):
    """Convert, and return the single constraint as ({var: coef}, sense, rhs)."""
    [c] = convert(ann).model.constraints
    return {t.var: t.coef for t in c.terms}, c.sense, c.rhs


# ---- end to end on real problems -------------------------------------------------------


def test_fishery_end_to_end():
    """By hand: trucks carry 3 fish per dollar vs 2, so 10 trucks and no dogs: 3000 fish."""
    conversion = convert(FISHERY)
    budget, order = conversion.model.constraints
    assert {t.var: t.coef for t in budget.terms} == {"sled dogs": 50, "trucks": 100}
    assert {t.var: t.coef for t in order.terms} == {"sled dogs": 1, "trucks": -1}
    assert [n.kind for n in conversion.notes] == ["strict-wording"]  # "less than"

    s = solve(conversion.model)
    assert s.status is Status.OPTIMAL
    assert s.objective == approx(3000)
    assert s.values == approx({"sled dogs": 0, "trucks": 10})


def test_ducks_lp_and_integer_optima_differ():
    """By hand: 12 boats and 22.5 canoes (1140 min) as an LP; 23 canoes (1160) with integers."""
    model = convert(DUCKS).model
    assert solve(model).objective == approx(1140)
    assert solve(as_integer(model)).objective == approx(1160)


def test_load_split(tmp_path):
    path = tmp_path / "split.jsonl"
    path.write_text('{"1": {"document": "a"}}\n{"2": {"document": "b"}}\n')
    assert load_split(path) == {"1": {"document": "a"}, "2": {"document": "b"}}


# ---- numbers and wording ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("100", 100), ("4,000", 4000), ("$500", 500), ("7.5", 7.5),
        ("60%", 0.6), ("7.5%", 0.075), ("35 percent", 0.35), ("thirty percent", 0.3),
        ("fifteen percent", 0.15), ("twice", 2), ("thrice", 3), ("three times", 3),
        ("2 times", 2), ("1.5 times", 1.5), ("half", 0.5), ("a third", 1 / 3),
        ("Four", 4), ("one hundred thousand", 100_000), ("8000 minutes", 8000),
    ],
)  # fmt: skip
def test_parse_number(text, value):
    assert parse_number(text) == approx(value)


@pytest.mark.parametrize("text", ["", "lots", "a few", "twelve-ish"])
def test_unreadable_numbers_fail_loudly(text):
    with pytest.raises(ConversionError, match="can't read the number"):
        parse_number(text)


@pytest.mark.parametrize(
    ("direction", "sense"),
    [("maximize", "max"), ("maximum", "max"), ("highest", "max"), ("minimize", "min"),
     ("minimum", "min"), ("lowest", "min"), ("reduce", "min"), ("decrease", "min")],
)  # fmt: skip
def test_objective_sense(direction, sense):
    assert objective_sense(direction) == sense


def test_unknown_objective_direction_fails():
    with pytest.raises(ConversionError, match="unknown objective direction"):
        objective_sense("optimize")


@pytest.mark.parametrize(
    ("direction", "document", "operator"),
    [
        ("at least", "", ">="),
        ("must exceed", "", ">="),
        ("at most", "", "<="),
        ("less than", "", "<="),
        ("no more than", "", "<="),
        ("cannot exceed", "", "<="),
        # The annotated phrase is clipped; the negation sits just before it in the text.
        ("more than", "the company does not want to spend more than $400000", "<="),
        ("budget", "", None),
        ("available", "", None),
    ],
)
def test_implied_operator(direction, document, operator):
    assert implied_operator(direction, document) == operator


@pytest.mark.parametrize(
    ("direction", "document", "strict"),
    [
        ("must exceed", "", True),
        ("more than", "", True),
        ("less than", "", True),
        ("at least", "", False),
        ("cannot exceed", "", False),
        ("more than", "does not want to spend more than $400000", False),
    ],
)
def test_is_strict(direction, document, strict):
    assert is_strict(direction, document) is strict


# ---- each declaration type -------------------------------------------------------------


def test_linear():
    decl = {"type": "linear", "terms": {"x": "2", "y": "3"}, "limit": "20",
            "operator": "LESS_OR_EQUAL", "direction": "available"}  # fmt: skip
    assert only_constraint(annotation([decl])) == ({"x": 2, "y": 3}, "<=", 20)


def test_linear_with_an_unlisted_variable_gets_coefficient_zero_and_a_note():
    decl = {"type": "linear", "terms": {"x": "5"}, "limit": "10",
            "operator": "LESS_OR_EQUAL", "direction": "available"}  # fmt: skip
    ann = annotation([decl])
    assert only_constraint(ann) == ({"x": 5}, "<=", 10)
    assert [n.kind for n in convert(ann).notes] == ["unlisted-variable"]


def test_sum_covers_every_variable():
    decl = {"type": "sum", "limit": "150", "operator": "GREATER_OR_EQUAL", "direction": "total"}
    assert only_constraint(annotation([decl])) == ({"x": 1, "y": 1}, ">=", 150)


@pytest.mark.parametrize(
    ("kind", "operator", "sense"),
    [("upperbound", "LESS_OR_EQUAL", "<="), ("lowerbound", "GREATER_OR_EQUAL", ">=")],
)
def test_bounds(kind, operator, sense):
    decl = {"type": kind, "var": "x", "limit": "50", "operator": operator, "direction": ""}
    assert only_constraint(annotation([decl])) == ({"x": 1}, sense, 50)


def test_xy_has_right_hand_side_zero():
    """x <= y. The official converter leaves the right-hand side at 1 here."""
    decl = {"type": "xy", "x_var": "x", "y_var": "y", "operator": "LESS_OR_EQUAL",
            "direction": ""}  # fmt: skip
    assert only_constraint(annotation([decl])) == ({"x": 1, "y": -1}, "<=", 0)


def test_xby():
    """x >= 2y  ->  x - 2y >= 0"""
    decl = {"type": "xby", "x_var": "x", "y_var": "y", "param": "twice",
            "operator": "GREATER_OR_EQUAL", "direction": "at least"}  # fmt: skip
    assert only_constraint(annotation([decl])) == ({"x": 1, "y": -2}, ">=", 0)


def test_ratio_is_a_share_of_all_variables():
    """x >= 60% of (x + y + z)  ->  0.4x - 0.6y - 0.6z >= 0"""
    decl = {"type": "ratio", "var": "x", "limit": "60%", "operator": "GREATER_OR_EQUAL",
            "direction": "at least"}  # fmt: skip
    coefs, sense, rhs = only_constraint(annotation([decl], names=("x", "y", "z")))
    assert coefs == approx({"x": 0.4, "y": -0.6, "z": -0.6})
    assert (sense, rhs) == (">=", 0)


def test_ratio_above_one_is_read_as_a_percentage():
    """'at most 60% of carts can be golf carts' annotated as "60"."""
    decl = {"type": "ratio", "var": "x", "limit": "60", "operator": "LESS_OR_EQUAL",
            "direction": "at most"}  # fmt: skip
    ann = annotation([decl])
    coefs, _, _ = only_constraint(ann)
    assert coefs == approx({"x": 0.4, "y": -0.6})
    assert [n.kind for n in convert(ann).notes] == ["share-above-1"]


def test_objective_terms_and_objvar():
    objective = {"type": "objective", "direction": "minimize", "name": "cost",
                 "terms": {"x": "$3", "y": "4,000"}}  # fmt: skip
    model = convert(annotation([], objective=objective)).model
    assert model.objective.sense == "min"
    assert {t.var: t.coef for t in model.objective.terms} == {"x": 3, "y": 4000}


def test_empty_objvar_means_the_sum_of_all_variables():
    objective = {"type": "objvar", "direction": "maximize", "name": "total number", "vars": []}
    conversion = convert(annotation([], objective=objective))
    assert {t.var: t.coef for t in conversion.model.objective.terms} == {"x": 1, "y": 1}
    assert [n.kind for n in conversion.notes] == ["empty-objvar"]


def test_mentions_resolve_through_order_mapping():
    ann = annotation(
        [{"type": "upperbound", "var": "truck", "limit": "5", "operator": "LESS_OR_EQUAL",
          "direction": "at most"}],
        names=("trucks", "vans"),
        order_mapping={"trucks": 0, "vans": 1, "truck": 0},
    )  # fmt: skip
    assert only_constraint(ann) == ({"trucks": 1}, "<=", 5)


def test_duplicate_entry_in_vars_is_kept_once():
    objective = {"type": "objvar", "direction": "minimize", "name": "trips",
                 "vars": ["freight", "air"]}  # fmt: skip
    ann = annotation([], objective=objective, names=("freight", "air", "air"),
                     order_mapping={"freight": 0, "air": 1})  # fmt: skip
    conversion = convert(ann)
    assert [v.name for v in conversion.model.variables] == ["freight", "air"]
    assert [n.kind for n in conversion.notes] == ["duplicate-var"]


# ---- annotation errors are rejected, never repaired --------------------------------------


def test_the_name_in_a_mention_beats_a_wrong_order_mapping():
    """'graduate researcher' mapped to the technicians (a real case from the test split)."""
    ann = annotation(
        [{"type": "lowerbound", "var": "graduate researcher", "limit": "2",
          "operator": "GREATER_OR_EQUAL", "direction": "at least"}],
        names=("technicians", "graduate researchers"),
        order_mapping={"technicians": 0, "graduate researchers": 1, "graduate researcher": 0},
    )  # fmt: skip
    assert only_constraint(ann) == ({"graduate researchers": 1}, ">=", 2)
    assert [n.kind for n in convert(ann).notes] == ["order-mapping-overridden"]


def test_a_mention_resolves_to_the_variable_name_it_contains():
    """'economical mobile phone' -> 'economical', though order_mapping says premium (dev #2)."""
    ann = annotation(
        [{"type": "linear", "terms": {"economical mobile phone": "5", "premium mobile phone": "12"},
          "limit": "150", "operator": "LESS_OR_EQUAL", "direction": "available"}],
        names=("economical", "premium mobile"),
        order_mapping={"economical": 0, "premium mobile": 1, "economical mobile phone": 1,
                       "premium mobile phone": 1},
    )  # fmt: skip
    assert only_constraint(ann) == ({"economical": 5, "premium mobile": 12}, "<=", 150)


def test_order_mapping_decides_when_the_name_does_not():
    """'Firemen' names neither variable, so order_mapping decides."""
    ann = annotation(
        [{"type": "upperbound", "var": "Firemen", "limit": "9", "operator": "LESS_OR_EQUAL",
          "direction": "at most"}],
        names=("firefighters", "volunteer fire patrols"),
        order_mapping={"firefighters": 0, "volunteer fire patrols": 1, "Firemen": 0},
    )  # fmt: skip
    assert only_constraint(ann) == ({"firefighters": 1}, "<=", 9)
    assert convert(ann).notes == []


def test_rejects_two_mentions_of_one_variable():
    decl = {"type": "linear", "terms": {"x": "1", "x2": "2"}, "limit": "5",
            "operator": "LESS_OR_EQUAL", "direction": "available"}  # fmt: skip
    ann = annotation([decl], order_mapping={"x": 0, "y": 1, "x2": 0})
    with pytest.raises(ConversionError, match="two mentions resolve to 'x'"):
        convert(ann)


def test_rejects_one_variable_annotated_twice():
    ann = annotation([], names=("kayak", "motorboat", "Kayaks"))
    with pytest.raises(ConversionError, match="one thing annotated twice"):
        convert(ann)


def test_rejects_empty_terms():
    decl = {"type": "linear", "terms": {}, "limit": "1200", "operator": "GREATER_OR_EQUAL",
            "direction": "at least"}  # fmt: skip
    with pytest.raises(ConversionError, match="the annotation has no terms"):
        convert(annotation([decl]))


def test_rejects_an_operator_that_contradicts_the_wording():
    """'single machines must be more than dual ones', annotated as <=."""
    decl = {"type": "xy", "x_var": "x", "y_var": "y", "operator": "LESS_OR_EQUAL",
            "direction": "more than"}  # fmt: skip
    ann = annotation([decl], document="the number of x must be more than the number of y")
    with pytest.raises(ConversionError, match="text says 'more than', but the operator is <="):
        convert(ann)


@pytest.mark.parametrize(
    ("decl", "message"),
    [
        ({"type": "mystery", "operator": "LESS_OR_EQUAL"}, "unknown constraint type"),
        ({"type": "sum", "limit": "1", "operator": "EQUAL"}, "unknown operator"),
        ({"type": "upperbound", "var": "z", "limit": "1", "operator": "LESS_OR_EQUAL"},
         "unknown variable mention 'z'"),
        ({"type": "upperbound", "var": "x", "operator": "LESS_OR_EQUAL"}, "missing 'limit'"),
    ],
)  # fmt: skip
def test_rejects_malformed_declarations(decl, message):
    with pytest.raises(ConversionError, match=message):
        convert(annotation([decl]))
