"""Power of the follow-up's two primary contrasts, simulated before the pre-registration is
frozen ($0, no API calls, no test problem read). Writes docs/followup/power.md.

The two contrasts need different models, because their conditions are paired differently:
- **H2 (single-shot vs baseline): independent discordance.** The two conditions make
  separate calls, so they disagree on some problems even with no effect.
- **H1 (checklist revision vs single-shot): shared samples.** Condition 4 reuses each of
  single-shot's samples (the same cached first reply), so the two differ only where a revision
  changes the outcome.

**H2's design.** n problems, two conditions A and B on the same problems, 3
samples per problem and condition. Each problem has a latent state per condition (right or
wrong), drawn as a paired 2x2 table:
- `discordance` is the share of problems where the two conditions differ for reasons that
  have nothing to do with the effect, split evenly both ways (so under no effect, A-only and
  B-only are equally likely);
- the effect adds B-only problems on top, enough that B's expected per-sample accuracy is
  `diff` above A's;
- the remaining problems are concordant, CONCORDANT_RIGHT of them right in both.
Each sample is right with probability `agreement` when its latent state is right, and wrong
with that probability when it's wrong. So `agreement` is how often a sample says what the
problem's state says: high (0.95: two samples agree 90.5% of the time) or moderate (0.80:
68%). A latent effect of diff / (2 * agreement - 1) gives a per-sample difference of `diff`.

**H1's design.** Single-shot's samples are drawn as above, from a latent state that is right
for CONCORDANT_RIGHT of the problems, with the same `agreement`. Condition 4 starts from the
very same samples. On a share `effect` of the problems a revision applies and every wrong
sample of that problem becomes right; on a share `reverse` (0%, 1% or 2%; disjoint from the
first) a revision turns every right sample wrong; elsewhere condition 4's samples equal
single-shot's. `effect` is set so the expected per-sample difference is `diff`:
effect * (1 - accuracy) - reverse * accuracy = diff, with accuracy single-shot's per-sample
accuracy. A problem changes all its samples together, the strongest within-problem
correlation, which is the cautious choice for a per-problem test.

**The tests** (both two-sided, both exact):
- McNemar on majority-of-3: a condition's answer to a problem is right if 2 or 3 samples are;
  `stats.mcnemar_exact` on the discordant pairs.
- Paired sign-flip permutation on the fraction correct: D_i = (B right - A right) / 3. Under
  no difference each D_i is as likely to be +|D_i| as -|D_i|, so the null distribution of the
  sum is the sum of independent +/-|D_i|. Every |D_i| is 1, 2 or 3 thirds, so that
  distribution is computed exactly (stats.sign_flip_exact, the analysis's own code).

**Holm with 2 contrasts.** A contrast is rejected for sure when p <= 0.025 (Holm's first
step, whatever the other contrast does); at p <= 0.05 only if the other is rejected too. The
minimum detectable effect is given for both: 0.025 is the honest one to plan on.

Run:  python scripts/followup_power.py   # ~3 min; writes docs/followup/power.md
"""

import argparse
from pathlib import Path

import numpy as np

from opt_agent.stats import mcnemar_exact, sign_flip_exact

SEED = 20261109
REPS = 4000
NS = (128, 121)
DISCORDANCES = (0.05, 0.10, 0.20)
DIFFS_PP = (5, 8, 10, 12, 15)
AGREEMENTS = {"high": 0.95, "moderate": 0.80}
CONCORDANT_RIGHT = 0.80  # of the concordant problems; follow-up dev single-shot was 22/25
SAMPLES = 3
POWER_TARGET = 0.80
ALPHA_HOLM_FIRST = 0.025  # 0.05 / 2: rejected whatever the other contrast does
ALPHA_HOLM_LAST = 0.05  # rejected only if the other contrast is too
MDE_GRID_PP = range(1, 41)
REVERSES = (0.0, 0.01, 0.02)  # H1: revisions that turn right answers wrong
OUT = Path(__file__).resolve().parents[1] / "docs" / "followup" / "power.md"


def sign_flip_p(diffs_in_thirds: np.ndarray) -> float:
    """The primary test, stats.sign_flip_exact, on one simulated experiment's differences."""
    return sign_flip_exact(diffs_in_thirds.tolist())


def latent_table(discordance: float, diff: float, agreement: float) -> np.ndarray:
    """Probabilities of (both right, both wrong, A only, B only) at the latent level."""
    effect = diff / (2 * agreement - 1)
    a_only, b_only = discordance / 2, discordance / 2 + effect
    concordant = 1 - a_only - b_only
    if concordant < 0:
        raise ValueError("discordance plus effect is more than every problem")
    return np.array([concordant * CONCORDANT_RIGHT, concordant * (1 - CONCORDANT_RIGHT),
                     a_only, b_only])  # fmt: skip


def simulate(n, discordance, diff, agreement, reps, rng) -> dict[str, np.ndarray]:
    """p-values of both tests for `reps` simulated experiments."""
    probs = latent_table(discordance, diff, agreement)
    kind = rng.choice(4, size=(reps, n), p=probs)
    a_right = (kind == 0) | (kind == 2)
    b_right = (kind == 0) | (kind == 3)
    # samples right out of 3: Binomial(3, agreement) if latent right, else (3, 1 - agreement)
    a_k = rng.binomial(SAMPLES, np.where(a_right, agreement, 1 - agreement))
    b_k = rng.binomial(SAMPLES, np.where(b_right, agreement, 1 - agreement))
    a_maj, b_maj = a_k >= 2, b_k >= 2
    only_a = np.sum(a_maj & ~b_maj, axis=1)
    only_b = np.sum(b_maj & ~a_maj, axis=1)
    mcnemar = np.array([mcnemar_exact(int(x), int(y)) for x, y in zip(only_a, only_b, strict=True)])
    flips = np.array([sign_flip_p(row) for row in b_k - a_k])
    return {"mcnemar": mcnemar, "sign_flip": flips}


def shared_rates(diff: float, reverse: float, agreement: float) -> tuple[float, float]:
    """H1: (the share of problems a revision fixes, single-shot's per-sample accuracy) that
    give a per-sample difference of `diff` with `reverse` of the problems made worse."""
    accuracy = CONCORDANT_RIGHT * agreement + (1 - CONCORDANT_RIGHT) * (1 - agreement)
    effect = (diff + reverse * accuracy) / (1 - accuracy)
    if effect < 0 or effect + reverse > 1:
        raise ValueError("no share of problems gives that difference")
    return effect, accuracy


def simulate_shared(n, diff, reverse, agreement, reps, rng) -> dict[str, np.ndarray]:
    """H1: p-values of both tests when condition 4 reuses single-shot's samples."""
    right, revised = draw_shared(n, diff, reverse, agreement, reps, rng)
    return _tests(right.sum(axis=2), revised.sum(axis=2))


def draw_shared(n, diff, reverse, agreement, reps, rng) -> tuple[np.ndarray, np.ndarray]:
    """H1: (single-shot's samples, condition 4's), each right or not, shape (reps, n, 3)."""
    effect, _ = shared_rates(diff, reverse, agreement)
    latent = rng.random((reps, n)) < CONCORDANT_RIGHT
    right = rng.random((reps, n, SAMPLES)) < np.where(latent, agreement, 1 - agreement)[..., None]
    draw = rng.random((reps, n))
    fixed = (draw < effect)[..., None]
    broken = ((draw >= effect) & (draw < effect + reverse))[..., None]
    return right, np.where(fixed, True, np.where(broken, False, right))


def _tests(a_k: np.ndarray, b_k: np.ndarray) -> dict[str, np.ndarray]:
    a_maj, b_maj = a_k >= 2, b_k >= 2
    only_a = np.sum(a_maj & ~b_maj, axis=1)
    only_b = np.sum(b_maj & ~a_maj, axis=1)
    mcnemar = np.array([mcnemar_exact(int(x), int(y)) for x, y in zip(only_a, only_b, strict=True)])
    flips = np.array([sign_flip_p(row) for row in b_k - a_k])
    return {"mcnemar": mcnemar, "sign_flip": flips}


def power_shared(n, diff, reverse, agreement, reps, seed) -> dict[str, dict[float, float]]:
    """H1's power, like power(): same seed, common random numbers."""
    p = simulate_shared(n, diff, reverse, agreement, reps, np.random.default_rng(seed))
    levels = (ALPHA_HOLM_FIRST, ALPHA_HOLM_LAST)
    return {test: {a: float(np.mean(v <= a)) for a in levels} for test, v in p.items()}


def mde_shared(n, reverse, agreement, reps, seed, test, alpha) -> int | None:
    """H1's smallest whole-point difference with power >= POWER_TARGET (None: none feasible)."""
    for pp in MDE_GRID_PP:
        try:
            result = power_shared(n, pp / 100, reverse, agreement, reps, seed)
        except ValueError:
            return None
        if result[test][alpha] >= POWER_TARGET:
            return pp
    return None


def power(n, discordance, diff, agreement, reps, seed) -> dict[str, dict[float, float]]:
    """Share of experiments rejected, per test, at both Holm levels. Each cell gets its own
    generator from the same seed (common random numbers), so curves over diff are smooth."""
    p = simulate(n, discordance, diff, agreement, reps, np.random.default_rng(seed))
    levels = (ALPHA_HOLM_FIRST, ALPHA_HOLM_LAST)
    return {test: {a: float(np.mean(v <= a)) for a in levels} for test, v in p.items()}


def mde(n, discordance, agreement, reps, seed, test, alpha) -> int | None:
    """The smallest whole-point difference with power >= POWER_TARGET (None: not in 1-40)."""
    for pp in MDE_GRID_PP:
        try:
            if power(n, discordance, pp / 100, agreement, reps, seed)[test][alpha] >= POWER_TARGET:
                return pp
        except ValueError:
            return None
    return None


def render(reps: int, seed: int) -> str:
    tests = (("sign_flip", "sign-flip (primary)"), ("mcnemar", "McNemar, majority of 3"))
    lines = [
        "# Follow-up power analysis",
        "",
        "Generated by `scripts/followup_power.py`; don't edit by hand. Simulated, $0, before",
        "the follow-up pre-registration is frozen; no follow-up test problem was read.",
        "",
        f"Seed {seed}, {reps} simulated experiments per cell (a power near 80% has a",
        f"standard error of about {100 * (0.8 * 0.2 / reps) ** 0.5:.1f} points). Exact tests,",
        "two-sided. **Difference** is in expected per-sample accuracy, in percentage points.",
        "",
        "**Which table is which.** H2 (single-shot vs baseline) compares two conditions that",
        "call the API separately: the H2 tables, with independent background discordance.",
        "H1 (checklist revision vs single-shot) compares two conditions that share every",
        "sample's first reply, so they differ only where a revision changes the outcome: the",
        "H1 tables, with shared samples.",
        "",
        "**H2's model** (the script's docstring has both in full): a paired latent 2x2 per",
        "problem; **discordance** is the share of problems the two conditions disagree on",
        "with no effect (split evenly both ways), and the effect adds one-way discordance on",
        f"top; {100 * CONCORDANT_RIGHT:.0f}% of concordant problems are right in both; each of the",
        "3 samples agrees with its problem's latent state with probability "
        + ", ".join(f"{a} ({name})" for name, a in AGREEMENTS.items())
        + ".",
        "",
        "Because the difference is per sample, moderate agreement needs a larger latent gap",
        "to give the same difference, which is why it can need a smaller one than high",
        "agreement: noise dilutes the per-sample difference, and majority-of-3 partly undoes it.",
        "",
        "**H1's model:** single-shot's samples drawn the same way; condition 4 keeps them,",
        "except on the problems a revision fixes (every wrong sample made right) and, at a",
        "reverse rate of 0%, 1% or 2% of problems, those it breaks (every right sample made",
        "wrong). The fix rate is set so the per-sample difference is the one in the table.",
        "",
        "**Holm, 2 primary contrasts.** At p <= 0.025 a contrast is rejected whatever the",
        "other does; at p <= 0.05 only if the other is rejected too. Plan on 0.025.",
        "",
        "## H2: minimum detectable effect at 80% power (independent discordance)",
        "",
        "Smallest whole-point difference with power >= 80%, searched over 1 to 40 points.",
        "",
        "| n | discordance | agreement | sign-flip, 0.025 | sign-flip, 0.05 "
        "| McNemar, 0.025 | McNemar, 0.05 |",
        "|---|---|---|---|---|---|---|",
    ]
    for n in NS:
        for disc in DISCORDANCES:
            for name, agree in AGREEMENTS.items():
                cells = []
                for test, _ in tests:
                    for alpha in (ALPHA_HOLM_FIRST, ALPHA_HOLM_LAST):
                        found = mde(n, disc, agree, reps, seed, test, alpha)
                        cells.append("> 40" if found is None else f"{found} pp")
                lines.append(f"| {n} | {disc:.0%} | {name} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## H2: power at the planned differences (Holm's first step, alpha 0.025)",
        "",
        "| n | discordance | agreement | test | " + " | ".join(f"{d} pp" for d in DIFFS_PP) + " |",
        "|---|---|---|---|" + "---|" * len(DIFFS_PP),
    ]
    for n in NS:
        for disc in DISCORDANCES:
            for name, agree in AGREEMENTS.items():
                rows = {test: [] for test, _ in tests}
                for d in DIFFS_PP:
                    result = power(n, disc, d / 100, agree, reps, seed)
                    for test, _ in tests:
                        rows[test].append(f"{result[test][ALPHA_HOLM_FIRST]:.0%}")
                for test, label in tests:
                    lines.append(f"| {n} | {disc:.0%} | {name} | {label} | "
                                 + " | ".join(rows[test]) + " |")  # fmt: skip
    lines += [
        "",
        "## H2: size check (no effect)",
        "",
        "Rejection rate at difference 0, which must not exceed alpha (both tests are exact,",
        "so they're conservative).",
        "",
        "| n | discordance | agreement | sign-flip, 0.05 | McNemar, 0.05 |",
        "|---|---|---|---|---|",
    ]
    for n in NS:
        for disc in DISCORDANCES:
            for name, agree in AGREEMENTS.items():
                result = power(n, disc, 0.0, agree, reps, seed)
                lines.append(f"| {n} | {disc:.0%} | {name} | "
                             f"{result['sign_flip'][ALPHA_HOLM_LAST]:.1%} | "
                             f"{result['mcnemar'][ALPHA_HOLM_LAST]:.1%} |")  # fmt: skip
    return "\n".join(lines + render_shared(reps, seed, tests)) + "\n"


def render_shared(reps: int, seed: int, tests) -> list[str]:
    """H1's sections: shared samples, by reverse rate."""
    lines = [
        "",
        "## H1: minimum detectable effect at 80% power (shared samples)",
        "",
        "Smallest whole-point difference with power >= 80%, searched over 1 to 40 points (n/a:",
        "no feasible difference reaches 80%).",
        "",
        "| n | reverse | agreement | sign-flip, 0.025 | sign-flip, 0.05 "
        "| McNemar, 0.025 | McNemar, 0.05 |",
        "|---|---|---|---|---|---|---|",
    ]
    for n in NS:
        for reverse in REVERSES:
            for name, agree in AGREEMENTS.items():
                cells = []
                for test, _ in tests:
                    for alpha in (ALPHA_HOLM_FIRST, ALPHA_HOLM_LAST):
                        found = mde_shared(n, reverse, agree, reps, seed, test, alpha)
                        cells.append("n/a" if found is None else f"{found} pp")
                lines.append(f"| {n} | {reverse:.0%} | {name} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## H1: power at the planned differences (Holm's first step, alpha 0.025)",
        "",
        "| n | reverse | agreement | test | " + " | ".join(f"{d} pp" for d in DIFFS_PP) + " |",
        "|---|---|---|---|" + "---|" * len(DIFFS_PP),
    ]
    for n in NS:
        for reverse in REVERSES:
            for name, agree in AGREEMENTS.items():
                rows = {test: [] for test, _ in tests}
                for d in DIFFS_PP:
                    try:
                        result = power_shared(n, d / 100, reverse, agree, reps, seed)
                    except ValueError:
                        result = None
                    for test, _ in tests:
                        rows[test].append("n/a" if result is None
                                          else f"{result[test][ALPHA_HOLM_FIRST]:.0%}")  # fmt: skip
                for test, label in tests:
                    lines.append(f"| {n} | {reverse:.0%} | {name} | {label} | "
                                 + " | ".join(rows[test]) + " |")  # fmt: skip
    lines += [
        "",
        "## H1: size check (no net effect)",
        "",
        "Rejection rate at difference 0. With no reverse rate nothing changes, so nothing is",
        "rejected; with one, fixes and breaks balance in expectation.",
        "",
        "| n | reverse | agreement | sign-flip, 0.05 | McNemar, 0.05 |",
        "|---|---|---|---|---|",
    ]
    for n in NS:
        for reverse in REVERSES:
            for name, agree in AGREEMENTS.items():
                result = power_shared(n, 0.0, reverse, agree, reps, seed)
                lines.append(f"| {n} | {reverse:.0%} | {name} | "
                             f"{result['sign_flip'][ALPHA_HOLM_LAST]:.1%} | "
                             f"{result['mcnemar'][ALPHA_HOLM_LAST]:.1%} |")  # fmt: skip
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reps", type=int, default=REPS)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(args.reps, SEED))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
