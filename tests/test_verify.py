from problems import BLEND, REDDY_MIKKS, WYNDOR, terms
from pytest import mark

from opt_agent.schema import LPModel
from opt_agent.solver import Solution, Status, solve
from opt_agent.verify import check_solution, optimality_problems, same_answer


def claimed(values: dict[str, float], objective: float) -> Solution:
    """A solution as some solver might report it, right or wrong."""
    return Solution(solver="test", status=Status.OPTIMAL, objective=objective, values=values)


def test_accepts_a_correct_solution():
    assert check_solution(WYNDOR, claimed({"doors": 2, "windows": 6}, 36)) == []


def test_catches_a_violated_constraint():
    # Profit 42 would beat the optimum, but plant 3 only has 18 hours (this needs 24).
    problems = check_solution(WYNDOR, claimed({"doors": 4, "windows": 6}, 42))
    assert problems == ["constraint 'plant_3_hours' is violated by 6"]


def test_catches_a_bound_violation():
    problems = check_solution(WYNDOR, claimed({"doors": -1, "windows": 6}, 27))
    assert problems == ["variable 'doors' = -1.0 is below its lower bound 0.0"]


def test_catches_a_fractional_integer():
    problems = check_solution(REDDY_MIKKS, claimed({"exterior": 3, "interior": 1.5}, 21))
    assert problems == ["integer variable 'interior' = 1.5 is not an integer"]


def test_catches_a_wrong_objective():
    problems = check_solution(WYNDOR, claimed({"doors": 2, "windows": 6}, -36))
    assert problems == ["reported objective -36.0 but the values give 36.0"]


def test_catches_a_missing_value():
    assert check_solution(WYNDOR, claimed({"doors": 2}, 36)) == ["no value for variable 'windows'"]


def test_tolerates_solver_round_off():
    almost = claimed({"doors": 2 + 1e-9, "windows": 6 - 1e-9}, 36 + 1e-9)
    assert check_solution(WYNDOR, almost) == []


def test_same_answer_is_symmetric():
    """max x - y: one solver reports (1e9, 1e9), the other (0, 0), objectives 0 and 0.5.
    Big terms earn a big round-off allowance (2000); the comparison must use it both ways,
    not only when the big solution happens to come second."""
    model = LPModel.model_validate(
        {
            "variables": [{"name": "x"}, {"name": "y"}],
            "objective": {"sense": "max", "terms": terms({"x": 1, "y": -1})},
            "constraints": [],
        }
    )
    big, small = claimed({"x": 1e9, "y": 1e9}, 0.0), claimed({"x": 0, "y": 0}, 0.5)
    assert same_answer(model, big, small) and same_answer(model, small, big)


def test_a_failed_solve_agrees_with_nothing():
    timed_out = Solution(solver="test", status=Status.TIMEOUT)
    error = Solution(solver="test", status=Status.ERROR)
    assert not same_answer(WYNDOR, timed_out, timed_out)
    assert not same_answer(WYNDOR, error, error)
    assert not same_answer(WYNDOR, timed_out, claimed({"doors": 2, "windows": 6}, 36))


def with_duals(values: dict[str, float], objective: float, duals: dict[str, float]) -> Solution:
    return claimed(values, objective).model_copy(update={"duals": duals})


WYNDOR_DUALS = {"plant_1_hours": 0, "plant_2_hours": 1.5, "plant_3_hours": 1}  # by hand


@mark.parametrize("model", [WYNDOR, BLEND, REDDY_MIKKS], ids=["wyndor", "blend", "reddy_mikks"])
def test_cbcs_duals_prove_its_textbook_optima(model):
    assert optimality_problems(model, solve(model)) == []


def test_hand_computed_duals_prove_wyndors_optimum():
    """y.b = 0*4 + 1.5*12 + 1*18 = 36 = 3*2 + 5*6: no feasible plan can earn more."""
    optimum = with_duals({"doors": 2, "windows": 6}, 36, WYNDOR_DUALS)
    assert optimality_problems(WYNDOR, optimum) == []


def test_a_feasible_but_worse_point_leaves_a_gap():
    """(4, 3) uses every plant-3 hour and earns 27; the same duals still bound profit by 36.
    Feasibility checks alone would pass it."""
    worse = with_duals({"doors": 4, "windows": 3}, 27, WYNDOR_DUALS)
    assert optimality_problems(WYNDOR, worse) == [
        "the duals leave a duality gap of 9: optimality isn't proven"
    ]


def test_zero_duals_prove_nothing():
    """With y = 0 every reduced cost is a profit, and doors has no upper bound to stop it."""
    zeros = with_duals({"doors": 2, "windows": 6}, 36, dict.fromkeys(WYNDOR_DUALS, 0.0))
    assert optimality_problems(WYNDOR, zeros) == [
        "reduced cost of 'doors' is -3, but it has no upper bound",
        "reduced cost of 'windows' is -5, but it has no upper bound",
    ]


def test_a_shadow_price_with_the_wrong_sign_is_caught():
    """More hours can't lower the best profit: a negative price on a <= row is impossible."""
    wrong = with_duals({"doors": 2, "windows": 6}, 36, WYNDOR_DUALS | {"plant_2_hours": -1.5})
    assert optimality_problems(WYNDOR, wrong)[0] == (
        "shadow price of 'plant_2_hours' is -1.5: the wrong sign for a <= constraint in a "
        "max problem"
    )


def test_a_variable_bound_can_be_the_certificate():
    """max x with x <= 5 and no constraints: the bound alone proves x = 5 optimal."""
    model = LPModel.model_validate(
        {
            "variables": [{"name": "x", "upper": 5}],
            "objective": {"sense": "max", "terms": terms({"x": 1})},
            "constraints": [],
        }
    )
    assert optimality_problems(model, with_duals({"x": 5}, 5, {})) == []
    assert optimality_problems(model, with_duals({"x": 4}, 4, {})) != []


def test_check_solution_includes_the_certificate():
    assert check_solution(WYNDOR, with_duals({"doors": 4, "windows": 3}, 27, WYNDOR_DUALS))
    assert check_solution(WYNDOR, claimed({"doors": 4, "windows": 3}, 27)) == []  # no duals
