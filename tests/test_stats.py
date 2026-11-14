import itertools

import numpy as np
import pytest
from pytest import approx
from scipy.stats import binomtest

from opt_agent import stats
from opt_agent.stats import holm, mcnemar_exact, wilson


def test_wilson_by_hand():
    """8 of 10: center (0.8 + 1.92/10) / 1.384 = 0.717, half-width 0.227."""
    assert wilson(8, 10) == approx((0.4902, 0.9433), abs=1e-4)


@pytest.mark.parametrize(("k", "n"), [(0, 10), (10, 10), (1, 40), (31, 40), (131, 276), (3, 7)])
def test_wilson_matches_scipy(k, n):
    ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    assert wilson(k, n) == approx((ci.low, ci.high), abs=1e-12)


def test_wilson_with_no_data_says_nothing():
    assert wilson(0, 0) == (0.0, 1.0)


def test_mcnemar_by_hand():
    """1 vs 7 discordant: P(X <= 1) for Binomial(8, 1/2) is 9/256; two-sided, 18/256."""
    assert mcnemar_exact(1, 7) == approx(18 / 256)
    assert mcnemar_exact(7, 1) == mcnemar_exact(1, 7)


@pytest.mark.parametrize(("a", "b"), [(0, 5), (3, 3), (2, 9), (12, 30)])
def test_mcnemar_is_scipys_binomial_test(a, b):
    assert mcnemar_exact(a, b) == approx(binomtest(a, a + b, 0.5).pvalue)


def test_mcnemar_without_discordant_pairs():
    assert mcnemar_exact(0, 0) == 1.0


def test_holm_by_hand():
    """Sorted 0.01, 0.03, 0.04 times 3, 2, 1: 0.03, 0.06, 0.04 -> kept monotone: 0.06."""
    assert holm({"a": 0.04, "b": 0.01, "c": 0.03}) == approx({"b": 0.03, "c": 0.06, "a": 0.06})


def test_holm_never_exceeds_one():
    assert holm({"a": 0.6, "b": 0.7}) == {"a": 1.0, "b": 1.0}


def brute_force_sign_flip(diffs):
    """Every one of the 2^k sign flips, counted."""
    observed = abs(sum(diffs))
    sizes = [abs(d) for d in diffs]
    hits = sum(abs(sum(s * f for s, f in zip(sizes, flips, strict=True))) >= observed
               for flips in itertools.product((1, -1), repeat=len(sizes)))  # fmt: skip
    return hits / 2 ** len(sizes)


@pytest.mark.parametrize("seed", range(30))
def test_sign_flip_matches_brute_force(seed):
    rng = np.random.default_rng(seed)
    diffs = [int(d) for d in rng.integers(-3, 4, size=int(rng.integers(1, 14)))]
    assert stats.sign_flip_exact(diffs) == pytest.approx(brute_force_sign_flip(diffs), abs=1e-12)


def test_sign_flip_of_no_differences_is_one():
    assert stats.sign_flip_exact([0] * 10) == stats.sign_flip_exact([]) == 1.0


def test_sign_flip_with_sizes_of_one_is_the_two_sided_sign_test():
    # all differences +/-1: the sum is 2 * (pluses) - n, so this is McNemar's binomial test
    diffs = [1] * 9 + [-1] * 2
    assert stats.sign_flip_exact(diffs) == pytest.approx(stats.mcnemar_exact(2, 9))
