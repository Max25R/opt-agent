import pytest
from fakes import FakeClient
from problems import INFEASIBLE, REDDY_MIKKS, WYNDOR

from opt_agent.explain import explain, solver_facts, unsupported_numbers
from opt_agent.solver import solve


def test_wyndor_facts():
    facts = solver_facts(WYNDOR, solve(WYNDOR))
    assert facts.objective == 36
    assert facts.values == {"doors": 2, "windows": 6}
    assert facts.binding == ["plant_2_hours", "plant_3_hours"]
    assert facts.slack == {"plant_1_hours": 2, "plant_2_hours": 0, "plant_3_hours": 0}
    assert facts.shadow_prices == {"plant_1_hours": 0, "plant_2_hours": 1.5, "plant_3_hours": 1}


def test_an_integer_program_has_no_shadow_prices():
    assert solver_facts(REDDY_MIKKS, solve(REDDY_MIKKS)).shadow_prices is None


def test_only_optimal_solutions_are_explained():
    with pytest.raises(ValueError, match="only an optimal solution"):
        solver_facts(INFEASIBLE, solve(INFEASIBLE))


@pytest.mark.parametrize(
    ("text", "flagged"),
    [
        ("Make about 2,333.33 units.", []),
        ("Make about 2,333 units.", []),  # correctly rounded
        ("Make about 2,334 units.", ["2,334"]),  # wrongly rounded
        ("Keep at least 30% for testing.", []),  # 30% = 0.3
        ("Keep at least 25% for testing.", ["25%"]),
        ("It costs $1,160.", []),
        ("It costs $1,170.", ["$1,170"]),
        ("Constraint c0_budget binds.", []),  # digits inside a name aren't a number
    ],
)
def test_unsupported_numbers(text, flagged):
    assert unsupported_numbers(text, allowed=[2333.3333, 0.3, 1160]) == flagged


def test_explain_sends_the_facts_and_checks_every_number():
    facts = solver_facts(WYNDOR, solve(WYNDOR))
    reply = (
        "Make 2 doors and 6 windows a week for a profit of 36 thousand dollars. Plants 2 and 3 "
        "are fully used; an extra hour at plant 2 would add 1.5 thousand. That beats the "
        "next best plan by 7 thousand."  # "7" is made up
    )
    client = FakeClient(reply)
    explanation = explain("Wyndor Glass makes doors and windows.", WYNDOR, facts, client)
    assert explanation.text == reply
    assert explanation.unsupported_numbers == ["7"]
    assert '"binding"' in client.requests[0]["messages"][0]["content"]
