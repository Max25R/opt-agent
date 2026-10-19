"""Every count in docs/PREREGISTRATION.md is recomputed here from the committed data."""

import re

from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    answer,
    does_nothing,
    integrality_matters,
    load_records,
    scorable,
)
from opt_agent.packets import SAYS_LP, SAYS_LP_PATH, SEED
from opt_agent.runs import REPO_ROOT
from opt_agent.solver import Status
from opt_agent.stats import mcnemar_exact

DOC = " ".join((REPO_ROOT / "docs" / "PREREGISTRATION.md").read_text().split())
TEST = load_records(GROUND_TRUTH_DIR / "test.json")
SCORABLE = [r for r in TEST if scorable(r)]


def says(text: str) -> bool:
    return text in DOC


def verdict_count(verdict: str) -> int:
    return sum(r.review is not None and r.review.verdict == verdict for r in SCORABLE)


def test_problem_counts():
    assert says(f"{len(SCORABLE)} of {len(TEST)}")
    with_optimum = sum(answer(r).status is Status.OPTIMAL for r in SCORABLE)
    assert says(f"has an optimum ({with_optimum})") or says(f"an optimum ({with_optimum})")
    assert says(f"is a status ({len(SCORABLE) - with_optimum})")


def test_no_optimum_counts():
    statuses = [answer(r).status for r in SCORABLE if answer(r).status is not Status.OPTIMAL]
    infeasible = statuses.count(Status.INFEASIBLE)
    unbounded = statuses.count(Status.UNBOUNDED)
    assert verdict_count("text-has-no-optimum") == len(statuses)
    assert says(
        f"{len(statuses)} scorable test problems: {infeasible} infeasible, {unbounded} unbounded"
    )


def test_do_nothing_counts():
    nothing = [r for r in SCORABLE if does_nothing(r)]
    assert verdict_count("degenerate-text") == len(nothing)
    assert says(f"{len(nothing)} scorable test problems, all with objective 0")
    nonzero = sum(r.strict is not None and r.strict.ip.objective not in (0, None) for r in nothing)
    assert says(f"{nonzero} of the {len(nothing)} have a nonzero optimum under the strict reading")


def test_ambiguous_count():
    assert says(f"{verdict_count('ambiguous-text')} scorable test problems")


def test_lp_text_problems():
    listed = set(re.findall(r"`(-?\d+)`", DOC.split("**d.")[1].split("**e.")[0]))
    says_lp = {
        r.id
        for r in SCORABLE
        if re.search(r"\bLP\b|linear program", r.document, re.I)
        and r.integrality.kind == "integer"
        and integrality_matters(r)
    }
    owner_precedents = {"-640645082", "892653388"}
    assert listed - owner_precedents == says_lp == set(SAYS_LP)
    assert says(f"{len(says_lp)} scorable test problems where integrality changes the answer")
    assert says(f"**The owner labels these {len(SAYS_LP)}** (`review/says_lp.md`)")
    assert SAYS_LP_PATH.exists()


def test_strict_counts():
    strict = [r for r in SCORABLE if r.strict]
    changed = sum(
        (r.ip.status, r.ip.objective) != (r.strict.ip.status, r.strict.ip.objective) for r in strict
    )
    assert says(f"{len(strict)} scorable integer test problems")
    assert says(f"changes the answer in {changed} of the {len(strict)}")


def test_integrality_counts():
    sensitive = sum(integrality_matters(r) for r in SCORABLE)
    assert says(f"{sensitive} of the {len(SCORABLE)} scorable test problems")
    assert says(f"insensitive subset ({len(SCORABLE) - sensitive})")
    assert says(f"sensitive one ({sensitive})")
    assert says(f"seed {SEED}")


def test_the_ambiguous_constraints_exist():
    rows = re.findall(r"\| `(-?\d+)` \| `(\w+)` \|", DOC)
    ambiguous = {r.id: r for r in SCORABLE if r.review and r.review.verdict == "ambiguous-text"}
    assert {pid for pid, _ in rows} == set(ambiguous)
    for pid, constraint in rows:
        assert constraint in {c.name for c in ambiguous[pid].model.constraints}, pid


def test_the_status_subset_power_floor():
    """The smallest number of one-directional discordant pairs that reaches p < 0.05 alone,
    and that survives Holm as the smallest of the 6 p-values (alpha / 6)."""
    alone = next(n for n in range(1, 21) if mcnemar_exact(0, n) < 0.05)
    in_family = next(n for n in range(1, 21) if mcnemar_exact(0, n) < 0.05 / 6)
    assert says(f"only if at least {alone} of the 20 problems are discordant")
    assert says(f"As the smallest p in the family, it needs at least {in_family}")


def test_the_freeze_list_names_everything_a_run_depends_on():
    freeze = DOC.split("## 6.")[1].split("## 7.")[0]
    frozen = [
        "reviews.json", "integrality.json", "exclusions.json", "test.json",
        "formulate.SYSTEM_PROMPT", "explain.SYSTEM_PROMPT", "formulate.LP_SCHEMA",
        "baseline's system prompt", "perturbation code", "PREREGISTRATION.md",
    ]  # fmt: skip
    for item in frozen:
        assert item in freeze, item


def test_it_is_still_a_draft():
    assert says("**Status: DRAFT") and says("Not approved.")
    assert "approved by the owner" not in DOC.lower()
