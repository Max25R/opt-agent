from problems import REDDY_MIKKS, WYNDOR

from opt_agent.solver import Solution, Status
from opt_agent.verify import check_solution


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
