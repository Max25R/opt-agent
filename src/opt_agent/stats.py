"""The few statistics the evaluation reports, written out so each line can be explained.

- Wilson score interval for a proportion: unlike p +/- 1.96 * sqrt(p(1-p)/n), it stays
  inside [0, 1] and behaves at p = 0 or 1 and for small n.
- McNemar's exact test for two conditions run on the same problems: only the problems
  where they differ carry information, and under "no difference" each of those is a coin
  flip, so the p-value is a two-sided binomial test on the discordant pairs.
- Holm's step-down correction for testing several hypotheses at once.

Each is cross-checked against SciPy in tests/test_stats.py.
"""

import math

from scipy.stats import binom

Z_95 = 1.959963984540054  # the 97.5th percentile of the standard normal


def wilson(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """95% Wilson score interval for successes / n."""
    if n == 0:
        return 0.0, 1.0  # no data: anything is possible
    p = successes / n
    center = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return max(0.0, center - half), min(1.0, center + half)


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Two-sided p-value. only_a: problems condition A got right and B got wrong; only_b:
    the reverse. Problems both got right (or both wrong) don't enter."""
    discordant = only_a + only_b
    if discordant == 0:
        return 1.0
    tail = binom.cdf(min(only_a, only_b), discordant, 0.5)
    return min(1.0, 2 * tail)


def holm(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values: compare each to alpha as usual, and the family-wise error
    rate stays at most alpha. Sort ascending, multiply the i-th smallest (from 0) by
    m - i, and never let an adjusted value drop below the one before it."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    m, running, adjusted = len(ordered), 0.0, {}
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted
