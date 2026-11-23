"""docs/second_model/power.md: the power of the second-model study's primary test
(docs/SECOND_MODEL_PREREGISTRATION.md, section 5): the chance that an exact two-sided McNemar
test at alpha 0.05, on 121 pairs, comes out "supported" (p < 0.05, Sonnet ahead).

Exact, not simulated, so there's no seed. Per problem, independently, Sonnet alone is right
with probability p10 and Haiku alone with p01. Then the number of problems only one model gets
right is binomial (121, p10 + p01), and given that number, Sonnet's share of them is binomial
with p10 / (p10 + p01); the test's verdict depends only on those two counts, so the power is a
finite sum.

The design inputs come from Haiku's record (runs/followup-test/results.jsonl), and a test
checks them against it where the follow-up's keys are (tests/test_second_model_power.py):
- Haiku's sample 0, the pair of every Sonnet answer, is right on 95 of the 121 problems, so
  Sonnet can be right alone on at most 26 of them (p10 <= 26/121);
- two of Haiku's own samples disagree on 7 to 11 problems (one right, the other wrong): its
  answers vary from sample to sample, so a model that differs from it will disagree with it
  at least that often. The rows of p01 run from below that one-way rate to above it.

Design information, not a threshold: the study is reported whatever it finds.

Run:  python scripts/second_model_power.py   # a few seconds
"""

from pathlib import Path

from scipy.stats import binom

from opt_agent import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "second_model" / "power.md"
N = 121
ALPHA = 0.05
HAIKU_RIGHT = {0: 95, 1: 102, 2: 101}  # per sample, of the 121 problems
# For each pair of Haiku's samples (a, b): problems only a got right, and only b.
HAIKU_DISAGREE = {(0, 1): (2, 9), (0, 2): (1, 7), (1, 2): (4, 3)}
P01 = (0.02, 0.04, 0.06, 0.08)  # Haiku alone right
DIFFERENCES = (0.05, 0.08, 0.10, 0.15)  # p10 - p01: Sonnet's accuracy minus Haiku's
STEP = 0.005  # for the smallest difference with 80% power


def thresholds(n: int = N) -> list[int | None]:
    """For each number d of problems only one model got right: the fewest of them Sonnet must
    have for "supported" (p < ALPHA and Sonnet ahead), or None if no count is enough. The test
    rejects more readily the further the split is from even, so it's a threshold."""
    found: list[int | None] = []
    for d in range(n + 1):
        enough = [b for b in range(d + 1) if b > d - b and stats.mcnemar_exact(b, d - b) < ALPHA]
        found.append(enough[0] if enough else None)
    return found


def power(p10: float, p01: float, cutoffs: list[int | None], n: int = N) -> float:
    """P(supported) when, per problem, Sonnet alone is right w.p. p10 and Haiku alone p01."""
    discordant, total = p10 + p01, 0.0
    for d, cutoff in enumerate(cutoffs):
        if cutoff is None:
            continue
        total += binom.pmf(d, n, discordant) * binom.sf(cutoff - 1, d, p10 / discordant)
    return float(total)


def feasible(p10: float) -> bool:
    """Sonnet can be right alone only where Haiku's sample 0 is wrong."""
    return p10 <= (N - HAIKU_RIGHT[0]) / N + 1e-12


def smallest_difference(p01: float, cutoffs: list[int | None]) -> float | None:
    """The smallest difference (in STEP steps) with power of at least 0.80, if any."""
    difference = STEP
    while feasible(p01 + difference):
        if power(p01 + difference, p01, cutoffs) >= 0.80:
            return difference
        difference += STEP
    return None


def render() -> str:
    cutoffs = thresholds()
    header = "| Haiku alone right (p01) | " + " | ".join(
        f"+{100 * d:g} points" for d in DIFFERENCES) + " | 80% power from |"  # fmt: skip
    rows = []
    for p01 in P01:
        cells = [f"{power(p01 + d, p01, cutoffs):.2f}" if feasible(p01 + d) else "can't happen"
                 for d in DIFFERENCES]  # fmt: skip
        mde = smallest_difference(p01, cutoffs)
        last = f"+{100 * mde:.1f} points" if mde is not None else "never"
        rows.append(f"| {100 * p01:g}% | " + " | ".join(cells) + f" | {last} |")
    disagree = ", ".join(f"{a} and {b} on {x + y}" for (a, b), (x, y) in HAIKU_DISAGREE.items())
    return "\n".join([
        "# The second-model study's power (design information)",
        "",
        "Written by `scripts/second_model_power.py`: the exact chance that the primary test (a",
        f"two-sided exact McNemar test, alpha {ALPHA}, on {N} pairs) comes out supported (p below",
        "alpha, with Sonnet right on more of the problems only one model gets right), if Sonnet's",
        "accuracy is higher than Haiku's by each difference and Haiku alone is right on each share",
        "of the problems (p01). Exact, so there's no seed. Not a threshold: the study is reported",
        "whatever it finds.",
        "",
        f"Haiku's sample 0, the pair of every Sonnet answer, is right on {HAIKU_RIGHT[0]} of the "
        f"{N} problems, so",
        f"Sonnet can be right alone on at most {N - HAIKU_RIGHT[0]} of them (\"can't happen\" "
        "below). Two of Haiku's",
        f"own samples disagree (one right, one wrong) on 7 to 11 problems (samples {disagree});",
        "a different model should disagree with it at least that often.",
        "",
        header,
        "|---|" + "---:|" * (len(DIFFERENCES) + 1),
        *rows,
        "",
    ])  # fmt: skip


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render())
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
