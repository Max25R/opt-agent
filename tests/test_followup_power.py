"""The power script's simulated design, checked against the numbers it's built to give (its
sign-flip test is stats.sign_flip_exact, tested in test_stats.py). No API calls."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "followup_power.py"
spec = importlib.util.spec_from_file_location("followup_power", SCRIPT)
power = importlib.util.module_from_spec(spec)
spec.loader.exec_module(power)


def test_latent_table_gives_the_planned_per_sample_difference():
    agreement, diff = 0.8, 0.10
    both_right, _, a_only, b_only = power.latent_table(0.10, diff, agreement)
    accuracy = lambda right: right * agreement + (1 - right) * (1 - agreement)  # noqa: E731
    gap = accuracy(both_right + b_only) - accuracy(both_right + a_only)
    assert gap == pytest.approx(diff)


def test_latent_table_refuses_more_than_every_problem():
    with pytest.raises(ValueError):
        power.latent_table(0.5, 0.5, 0.6)


@pytest.mark.parametrize("reverse", [0.0, 0.01, 0.02])
@pytest.mark.parametrize("agreement", [0.95, 0.80])
def test_h1s_shared_model_gives_the_planned_difference(reverse, agreement):
    rng = np.random.default_rng(0)
    effect, accuracy = power.shared_rates(0.10, reverse, agreement)
    assert effect * (1 - accuracy) - reverse * accuracy == pytest.approx(0.10)
    # and in simulation: per-sample accuracy rises by 10 points, and only where revised
    right, revised = power.draw_shared(121, 0.10, reverse, agreement, 2000, rng)
    assert revised.mean() - right.mean() == pytest.approx(0.10, abs=0.005)
    assert right.mean() == pytest.approx(accuracy, abs=0.005)
    changed = (right != revised).any(axis=2)
    assert ((right == revised).all(axis=2) | changed).all()  # a problem changes or doesn't
    if reverse == 0:
        assert not (right & ~revised).any()  # one-way: nothing right is made wrong


def test_h1s_conditions_are_identical_with_no_effect_and_no_reverse():
    p = power.simulate_shared(50, 0.0, 0.0, 0.8, 20, np.random.default_rng(1))
    assert (p["sign_flip"] == 1.0).all() and (p["mcnemar"] == 1.0).all()


def test_h1s_infeasible_differences_are_refused():
    with pytest.raises(ValueError):
        power.shared_rates(0.40, 0.02, 0.95)
