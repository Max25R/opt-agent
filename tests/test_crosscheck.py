"""Property test: CBC (via PuLP) and HiGHS (via SciPy) must agree on random problems."""

from hypothesis import event, given, settings
from strategies import lp_models

from opt_agent.highs import solve_with_highs
from opt_agent.solver import Status, solve
from opt_agent.verify import check_solution, tolerance_for


@settings(max_examples=200, deadline=None)  # no deadline: CBC runs as a subprocess
@given(lp_models())
def test_cbc_and_highs_agree(model):
    cbc, highs = solve(model), solve_with_highs(model)
    event(f"status: {cbc.status}")  # shown with `pytest --hypothesis-show-statistics`

    assert cbc.status is not Status.ERROR
    assert cbc.status == highs.status
    if cbc.status is Status.OPTIMAL:
        # Compare objectives, not variable values: a problem can have many optimal points.
        allowed = tolerance_for(model.objective.terms, highs.values)
        assert abs(cbc.objective - highs.objective) <= allowed
        assert check_solution(model, cbc) == []
        assert check_solution(model, highs) == []
