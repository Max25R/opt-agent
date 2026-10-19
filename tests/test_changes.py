import pytest
from problems import WYNDOR

from opt_agent.changes import compare
from opt_agent.schema import Term, Variable


def edited(model, constraints=None, variables=None, objective=None):
    """A copy of `model` with some parts replaced (no re-validation: this is a test helper)."""
    update = {"constraints": constraints, "variables": variables, "objective": objective}
    return model.model_copy(update={k: v for k, v in update.items() if v is not None})


def with_constraint(model, which, **changes):
    return edited(model, constraints=[
        c.model_copy(update=changes) if c.name == which else c for c in model.constraints
    ])  # fmt: skip


def with_variable(model, which, **changes):
    return edited(model, variables=[
        v.model_copy(update=changes) if v.name == which else v for v in model.variables
    ])  # fmt: skip


def test_an_identical_model_has_no_changes():
    assert compare(WYNDOR, WYNDOR).none


def test_renaming_a_constraint_is_not_a_change():
    renamed = with_constraint(WYNDOR, "plant_1_hours", name="door capacity")
    assert compare(WYNDOR, renamed).none


def test_deleting_a_constraint_is_flagged():
    fewer = edited(WYNDOR, constraints=WYNDOR.constraints[1:])
    assert compare(WYNDOR, fewer).flags == ["deleted constraint 'plant_1_hours'"]


@pytest.mark.parametrize(
    ("rhs", "flagged", "text"),
    [
        (5, True, "loosened 'plant_1_hours': right-hand side 4 became 5"),
        (3, False, "tightened 'plant_1_hours': right-hand side 4 became 3"),
    ],
)
def test_moving_a_limit(rhs, flagged, text):
    changes = compare(WYNDOR, with_constraint(WYNDOR, "plant_1_hours", rhs=rhs))
    assert changes.changes == [text]
    assert changes.flags == ([text] if flagged else [])


def test_lowering_a_minimum_is_loosening():
    minimum = with_constraint(WYNDOR, "plant_1_hours", sense=">=")
    changes = compare(minimum, with_constraint(minimum, "plant_1_hours", rhs=1))
    assert changes.flags == ["loosened 'plant_1_hours': right-hand side 4 became 1"]


def test_an_equation_becoming_an_inequality_is_flagged():
    equation = with_constraint(WYNDOR, "plant_1_hours", sense="==")
    assert compare(equation, WYNDOR).flags == ["loosened 'plant_1_hours': == became <="]


def test_flipping_a_direction_is_a_change_not_a_flag():
    """Fixing a reversed <= is exactly what infeasibility feedback asks for."""
    changes = compare(WYNDOR, with_constraint(WYNDOR, "plant_1_hours", sense=">="))
    assert changes.changes == ["flipped 'plant_1_hours': <= became >="]
    assert changes.flags == []


def test_relaxing_integrality_is_flagged():
    integer = with_variable(WYNDOR, "doors", integer=True)
    assert compare(integer, WYNDOR).flags == ["made 'doors' continuous"]
    assert compare(WYNDOR, integer).flags == []  # requiring whole numbers is stricter


def test_removing_an_upper_bound_is_flagged():
    bounded = with_variable(WYNDOR, "doors", upper=4)
    assert compare(bounded, WYNDOR).flags == ["loosened the upper bound of 'doors': 4 became none"]


def test_flipping_the_objective_is_flagged():
    flipped = edited(WYNDOR, objective=WYNDOR.objective.model_copy(update={"sense": "min"}))
    assert compare(WYNDOR, flipped).flags == ["flipped the objective: max became min"]


def test_adding_a_constraint_is_a_change_not_a_flag():
    extra = WYNDOR.constraints[0].model_copy(update={"name": "extra", "rhs": 3})
    changes = compare(WYNDOR, edited(WYNDOR, constraints=[*WYNDOR.constraints, extra]))
    assert changes.changes == ["added constraint 'extra'"]
    assert changes.flags == []


def terms(coefs: dict[str, float]) -> list[Term]:
    return [Term(var=var, coef=coef) for var, coef in coefs.items()]


def with_terms(model, which, coefs):
    return with_constraint(model, which, terms=terms(coefs))


def test_lowering_a_coefficient_in_a_limit_is_loosening():
    """plant 3: 3 doors + 2 windows <= 18 hours. Saying a door takes 1 hour lets more through."""
    changes = compare(WYNDOR, with_terms(WYNDOR, "plant_3_hours", {"doors": 1, "windows": 2}))
    assert changes.flags == ["loosened the terms of 'plant_3_hours': 'doors' 3 became 1"]


def test_raising_a_coefficient_in_a_limit_is_tightening():
    changes = compare(WYNDOR, with_terms(WYNDOR, "plant_3_hours", {"doors": 4, "windows": 2}))
    assert changes.changes == ["tightened the terms of 'plant_3_hours': 'doors' 3 became 4"]
    assert changes.flags == []


def test_dropping_a_term_from_a_limit_is_loosening():
    changes = compare(WYNDOR, with_terms(WYNDOR, "plant_3_hours", {"windows": 2}))
    assert changes.flags == ["loosened the terms of 'plant_3_hours': 'doors' 3 became 0"]


def test_dropping_a_term_from_a_minimum_is_tightening():
    minimum = with_constraint(WYNDOR, "plant_3_hours", sense=">=")
    changes = compare(minimum, with_terms(minimum, "plant_3_hours", {"windows": 2}))
    assert changes.flags == []


def test_a_new_slack_variable_is_loosening():
    """The classic "fix" for infeasibility: let an invented variable absorb the shortfall."""
    slack = edited(
        with_terms(WYNDOR, "plant_3_hours", {"doors": 3, "windows": 2, "overtime": -1}),
        variables=[*WYNDOR.variables, Variable(name="overtime")],
    )
    assert compare(WYNDOR, slack).flags == [
        "loosened the terms of 'plant_3_hours': 'overtime' 0 became -1"
    ]


def test_any_coefficient_change_on_a_free_variable_may_loosen():
    free = with_variable(WYNDOR, "doors", lower=None)
    changes = compare(free, with_terms(free, "plant_3_hours", {"doors": 4, "windows": 2}))
    assert changes.flags == ["loosened the terms of 'plant_3_hours': 'doors' 3 became 4"]


def test_a_term_edit_doesnt_hide_a_looser_right_hand_side():
    revised = with_constraint(WYNDOR, "plant_3_hours", terms=terms({"doors": 4, "windows": 2}),
                              rhs=30)  # fmt: skip
    assert compare(WYNDOR, revised).flags == [
        "loosened 'plant_3_hours': right-hand side 18 became 30"
    ]


def test_removing_a_variable_is_flagged():
    """Removing windows takes its terms out of plant 2, plant 3 and the objective."""
    no_windows = edited(
        WYNDOR,
        variables=[v for v in WYNDOR.variables if v.name != "windows"],
        constraints=[
            c.model_copy(update={"terms": [t for t in c.terms if t.var != "windows"]})
            for c in WYNDOR.constraints
            if c.name != "plant_2_hours"  # its only term was windows
        ],
        objective=WYNDOR.objective.model_copy(
            update={"terms": [t for t in WYNDOR.objective.terms if t.var != "windows"]}
        ),
    )
    flags = compare(WYNDOR, no_windows).flags
    assert "removed variable 'windows'" in flags
    assert "deleted constraint 'plant_2_hours'" in flags


def test_dropping_a_variable_from_the_objective_is_flagged():
    objective = WYNDOR.objective.model_copy(update={"terms": terms({"doors": 3})})
    changes = compare(WYNDOR, edited(WYNDOR, objective=objective))
    assert changes.flags == ["dropped 'windows' from the objective"]
