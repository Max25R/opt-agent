"""docs/resampling/power.md: the power of the resampling study's primary test (a one-sided
Fisher exact test, alpha 0.05; docs/RESAMPLING_PREREGISTRATION.md, section 5), by simulation.

The planned flag is "the samples disagree, or the baseline disagrees": signal (a) or (c) of
the exploratory disagreement detector. Its rates come from that detector's one run on the
follow-up's samples 0 to 2 (docs/analysis/disagreement_detector.json: the base rate, and how
often the flag fires on silent failures and on right answers), with and without the 13
disputed problems, and from two weaker scenarios fixed here, since an exploratory effect
usually shrinks when it's tested again. Seeded; no API calls.

Run:  python scripts/resampling_power.py   # about a minute
"""

import json
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / "docs" / "analysis" / "disagreement_detector.json"
OUT = ROOT / "docs" / "resampling" / "power.md"
SEED = 20261119
SIMULATIONS = 4000
UNITS = 120  # 121 problems, allowing for one with no answer at sample 3
UNDISPUTED_UNITS = UNITS - 13  # the secondary analysis, without the disputed problems
ALPHA = 0.05
DISPUTED = {"complexlp:63", "complexlp:78", "complexlp:81", "complexlp:83", "complexlp:94",
            "industryor:17", "industryor:22", "industryor:24", "industryor:26", "industryor:27",
            "industryor:28", "industryor:30", "industryor:41"}  # fmt: skip


def rates(rows: list[dict]) -> tuple[float, float, float]:
    """(base rate, flag rate on silent failures, flag rate on right answers) for (a) or (c)."""
    silent = [r for r in rows if not r["right"]]
    right = [r for r in rows if r["right"]]
    flag = lambda r: bool(r["a"] or r["c"])  # noqa: E731
    return (len(silent) / len(rows), sum(map(flag, silent)) / len(silent),
            sum(map(flag, right)) / len(right))  # fmt: skip


def power(units: int, base: float, on_silent: float, on_right: float, rng) -> float:
    hits = 0
    for _ in range(SIMULATIONS):
        silent = rng.random(units) < base
        flagged = np.where(silent, rng.random(units) < on_silent, rng.random(units) < on_right)
        table = [[int((flagged & silent).sum()), int((flagged & ~silent).sum())],
                 [int((~flagged & silent).sum()), int((~flagged & ~silent).sum())]]  # fmt: skip
        hits += fisher_exact(table, alternative="greater").pvalue < ALPHA
    return hits / SIMULATIONS


def main() -> None:
    rows = json.loads(DETECTOR.read_text())["rows"]["followup"]
    seen, undisputed = rates(rows), rates([r for r in rows if r["problem"] not in DISPUTED])
    scenarios = [
        ("as seen on samples 0 to 2", UNITS, *seen),
        ("as seen, without the 13 disputed problems", UNDISPUTED_UNITS, *undisputed),
        ("weaker: flags 45% of silent failures, 25% of right answers", UNITS, seen[0], 0.45, 0.25),
        ("weak: flags 35% of silent failures, 25% of right answers", UNITS, seen[0], 0.35, 0.25),
    ]
    rng = np.random.default_rng(SEED)
    lines = ["# The resampling study's power (design information)", "",
             f"Written by `scripts/resampling_power.py` (seed {SEED}, {SIMULATIONS} simulations "
             f"each): the chance that the primary test (one-sided Fisher exact, "
             f"alpha {ALPHA}) finds a flagged answer more often wrong than an unflagged one, "
             "for each scenario. Not a threshold: the study is reported whatever it finds.", "",
             "| scenario | units | base rate | flags on silent failures | flags on right "
             "answers | power |", "|---|---:|---:|---:|---:|---:|"]  # fmt: skip
    for name, units, base, on_silent, on_right in scenarios:
        chance = power(units, base, on_silent, on_right, rng)
        lines.append(f"| {name} | {units} | {100 * base:.1f}% | {100 * on_silent:.1f}% | "
                     f"{100 * on_right:.1f}% | {chance:.2f} |")  # fmt: skip
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
