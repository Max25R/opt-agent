from problems import BLEND, INFEASIBLE, INTEGER_INFEASIBLE, REDDY_MIKKS, WYNDOR, unbounded
from pytest import approx, mark

from opt_agent.highs import solve_with_highs
from opt_agent.solver import Status
from opt_agent.verify import check_solution


@mark.parametrize(
    ("model", "expected"),
    [(WYNDOR, 36), (BLEND, 24), (REDDY_MIKKS, 20)],
    ids=["wyndor", "blend", "reddy_mikks"],
)
def test_known_answers(model, expected):
    s = solve_with_highs(model)
    assert s.status is Status.OPTIMAL
    assert s.objective == approx(expected)
    assert check_solution(model, s) == []


def test_infeasible():
    assert solve_with_highs(INFEASIBLE).status is Status.INFEASIBLE
    assert solve_with_highs(INTEGER_INFEASIBLE).status is Status.INFEASIBLE


@mark.parametrize("integer", [False, True], ids=["lp", "mip"])
def test_unbounded(integer):
    # For the MIP, HiGHS answers "infeasible or unbounded"; the zero-objective solve decides.
    assert solve_with_highs(unbounded(integer)).status is Status.UNBOUNDED
