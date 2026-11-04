"""Every count in docs/PREREGISTRATION.md is recomputed here from the committed data."""

import re

from opt_agent import blind_grading, external_check, packets, perturb, taxonomy
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    answer,
    does_nothing,
    integrality_matters,
    load_records,
    says_lp,
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
    """The 4 are the problems 3d names. Amendment 2's judges made all 4 `either`, so
    says_lp (a "says LP" text with an integer label) flags none of them now."""
    listed = set(re.findall(r"`(-?\d+)`", DOC.split("**d.")[1].split("**e.")[0]))
    owner_precedents = {"-640645082", "892653388"}
    assert listed - owner_precedents == set(SAYS_LP)
    by_id = {r.id: r for r in SCORABLE}
    assert all(integrality_matters(by_id[i]) for i in SAYS_LP)
    assert {r.id for r in SCORABLE if says_lp(r)} == set()
    assert all(by_id[i].integrality.kind == "either" for i in SAYS_LP)
    assert says(f"{len(SAYS_LP)} scorable test problems where integrality changes the answer")
    assert says("Amendment 2's judges made them `either`")
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
    """The table lists every ambiguous-text test review, also the one Amendment 2 excludes."""
    rows = re.findall(r"\| `(-?\d+)` \| `(\w+)` \|", DOC)
    ambiguous = {r.id: r for r in TEST if r.review and r.review.verdict == "ambiguous-text"}
    assert {pid for pid, _ in rows} == set(ambiguous)
    excluded = {i for i, r in ambiguous.items() if not scorable(r)}
    assert excluded == {"-1715698555"} and says("`-1715698555`, that Amendment 2 excludes")
    for pid, constraint in rows:
        assert constraint in {c.name for c in ambiguous[pid].model.constraints}, pid
        assert ambiguous[pid].review.equality == [constraint], pid  # the "=" reading's input


def test_the_ratio_wording_counts():
    def changed(r):
        kind = "ip" if r.integrality.kind != "continuous" else "lp"
        return (getattr(r.equality, kind).status, getattr(r.equality, kind).objective) != (
            answer(r).status, answer(r).objective)  # fmt: skip

    dev = [r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if scorable(r)]
    dev_changed = [r for r in dev if r.ratio_wording and changed(r)]
    assert says(f"the rule changes the answer in {len(dev_changed)} scorable dev problems")
    flagged = [r for r in SCORABLE if r.ratio_wording]
    test_changed = {r.id for r in flagged if changed(r)}
    assert says(f"gives {len(flagged)} scorable problems an \"=\" reading and changes the "
                f"answer in {len(test_changed)}")  # fmt: skip
    reviewed = {r.id for r in SCORABLE if r.review and r.review.equality}
    [unreviewed] = test_changed - reviewed
    assert says(f"one of the reviewed problems above, and `{unreviewed}`")
    assert len(test_changed & reviewed) == 1


def test_the_status_subset_power_floor():
    """The smallest number of one-directional discordant pairs that reaches p < 0.05 alone,
    and that survives Holm as the smallest of the 6 p-values (alpha / 6)."""
    alone = next(n for n in range(1, 21) if mcnemar_exact(0, n) < 0.05)
    in_family = next(n for n in range(1, 21) if mcnemar_exact(0, n) < 0.05 / 6)
    assert says(f"only if at least {alone} of the 20 problems are discordant")
    assert says(f"As the smallest p in the family, it needs at least {in_family}")


def test_the_perturbed_counts_and_rule():
    perturbed = load_records(GROUND_TRUTH_DIR / "test-perturbed.json")
    assert says(f"{len(perturbed)} of the {len(SCORABLE)} scorable test problems")
    assert says(f"seed {perturb.SEED}") and says(f"up to {perturb.MAX_DRAWS} times")
    low, high = perturb.FACTOR
    assert (low, high) == (0.5, 2.0) and says("log-uniformly from [1/2, 2]")


def test_the_hand_checks_are_the_codes():
    section = DOC.split("## 5a.")[1].split("## 6.")[0]
    assert f"(seed {blind_grading.SEED})" in section
    size = blind_grading.SIZE
    assert f"up to {size // 2} models scored wrong, and models scored right to make {size}" in (
        section
    )
    assert re.findall(r"\| `([a-z-]+)` \|", section) == list(taxonomy.CATEGORIES)


def test_the_freeze_list_names_everything_a_run_depends_on():
    freeze = DOC.split("## 6.")[1].split("## 7.")[0]
    frozen = [
        "reviews.json", "integrality.json", "exclusions.json", "test.json",
        "formulate.SYSTEM_PROMPT", "explain.SYSTEM_PROMPT", "formulate.LP_SCHEMA",
        "baseline's system prompt", "perturbation code", "test-perturbed.json",
        "PREREGISTRATION.md", "src/opt_agent/", "requirements.lock", "docs/FREEZE.json",
    ]  # fmt: skip
    for item in frozen:
        assert item in freeze, item


def test_it_is_still_a_draft():
    assert says("**Status: DRAFT") and says("Not approved.")
    assert "approved by the owner" not in DOC.lower()


def test_the_judges_integrality_replies_are_as_the_amendment_says():
    judge, second = (packets.read_judge_labels(packets.JUDGE_DIR / name)
                     for name in packets.JUDGE_SHEETS.values())  # fmt: skip
    problems = packets.judged_problems(TEST)
    differ = [n for n, (_, r) in enumerate(problems, 1) if judge[r.id] != second[r.id]]
    assert says(f"give the same label to {44 - len(differ)} of the 44 problems")
    listed = ", ".join(map(str, differ[:-1])) + f" and {differ[-1]}"
    assert says(f"They differ on {len(differ)} (numbers {listed} of the prompt)")
    a = packets.judges_agreement(TEST)
    assert says(f"and to {a['judge vs second']['same']} of the 40 in the blind sample")
    j, s = a["judge vs Claude"], a["second vs Claude"]
    assert says(f"accepts all {j['accepts']} of Claude's labels ({j['same']} the same, "
                f"{j['either']} `either`)") and j["accepts"] == 40  # fmt: skip
    assert says(f"the second judge {s['accepts']} ({s['same']} the same, {s['either']} "
                f"`either`, {s['different']} different)")  # fmt: skip
    combined = packets.combined_labels(judge, second)
    by_id = {r.id: r for r in TEST}
    turned = [
        i
        for i, k in combined.items()
        if k == "either" and packets.claude_label(by_id[i]) == "integer"
    ]
    assert says(f"turn {len(turned)} of Claude's `integer` labels into `either`")
    assert set(SAYS_LP) <= set(turned)


def test_the_review_judges_outcomes_are_as_the_amendment_says():
    judge, second = (external_check.read_judgments(external_check.REVIEW_JUDGE_DIR / name)
                     for name in packets.JUDGE_SHEETS.values())  # fmt: skip
    outcomes = external_check.review_outcomes(judge, second)
    reviews = {i: o for i, o in outcomes.items() if i not in external_check.HARD_CASES}
    disputed = [i for i, o in reviews.items() if o == "disputed"]
    assert says(f"of the {len(reviews)} reviews, {len(reviews) - len(disputed)} are confirmed "
                f"and {len(disputed)} disputed")  # fmt: skip
    assert all(second[i] != "agree" for i in disputed)
    [by_record] = [i for i in disputed if judge[i] != "agree"]
    assert says(f"the judge of record one of them (`{by_record}`)")
    assert all(outcomes[i] == "disputed" for i in external_check.HARD_CASES)
