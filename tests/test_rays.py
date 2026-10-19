from problems import CBC_FREE_VARIABLE_BUG, FISHERY, HIGHS_FREE_VARIABLE_BUG, WYNDOR
from pytest import mark

from opt_agent.highs import _solve_once as highs_once
from opt_agent.nl4opt import convert
from opt_agent.rays import improvement, is_improving_ray, ray_model, refuting_ray
from opt_agent.solver import _solve_once as cbc_once

SOLVERS = [cbc_once, highs_once]


def test_the_ray_model_keeps_constraints_and_makes_every_direction_bounded():
    rays = ray_model(CBC_FREE_VARIABLE_BUG)
    assert [(v.lower, v.upper) for v in rays.variables] == [(-1, 1), (-1, 1), (0, 1)]
    assert [(c.terms, c.sense, c.rhs) for c in rays.constraints] == [
        (CBC_FREE_VARIABLE_BUG.constraints[0].terms, "<=", 0.0)
    ]


def test_bounded_both_ways_means_no_direction_and_integers_are_relaxed():
    rays = ray_model(HIGHS_FREE_VARIABLE_BUG)
    assert [(v.lower, v.upper, v.integer) for v in rays.variables] == [
        (-1, 1, False), (0, 0, False), (0, 0, False), (-1, 0, False),
    ]  # fmt: skip


def test_a_ray_is_checked_by_arithmetic():
    """For CBC_FREE_VARIABLE_BUG, d = (1, 0, 0) keeps 5*x0 + 4*x1 >= 1 and lowers the cost."""
    assert is_improving_ray(CBC_FREE_VARIABLE_BUG, {"x0": 1, "x1": 0, "x2": 0})
    assert improvement(CBC_FREE_VARIABLE_BUG, {"x0": 1, "x1": 0, "x2": 0}) == 5
    assert not is_improving_ray(CBC_FREE_VARIABLE_BUG, {"x0": -1, "x1": 0, "x2": 0})  # breaks c0
    assert not is_improving_ray(CBC_FREE_VARIABLE_BUG, {"x0": 0, "x1": 0, "x2": -1})  # x2 >= 0
    assert not is_improving_ray(CBC_FREE_VARIABLE_BUG, {"x0": 0, "x1": 0, "x2": 1})  # costs more


@mark.parametrize("solve_once", SOLVERS, ids=["cbc", "highs"])
@mark.parametrize(
    "model", [CBC_FREE_VARIABLE_BUG, HIGHS_FREE_VARIABLE_BUG], ids=["cbc-bug", "highs-bug"]
)
def test_both_solvers_find_a_ray_for_both_counterexamples(model, solve_once):
    ray = refuting_ray(model, solve_once)
    assert ray is not None and is_improving_ray(model, ray)


@mark.parametrize("solve_once", SOLVERS, ids=["cbc", "highs"])
@mark.parametrize("model", [WYNDOR, convert(FISHERY).model], ids=["wyndor", "fishery"])
def test_a_true_optimum_has_no_ray(model, solve_once):
    assert refuting_ray(model, solve_once) is None
