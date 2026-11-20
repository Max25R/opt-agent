"""The resampling study's analysis (docs/RESAMPLING_PREREGISTRATION.md, section 4), on synthetic
answers: R1's units are verified sample-3 answers; a missing answer anywhere counts as
disagreement; Fisher's exact test, one-sided; R2's majority of five against sample 3, with
missing answers as no vote; the secondary analysis without the disputed problems."""

import pytest
from scipy.stats import fisher_exact

from opt_agent import followup, resampling_report
from opt_agent.evaluate import Item


def item(problem: str, condition: str, sample: int, objective: float | None = 4.0,
         status: str | None = "optimal", outcome: str = "done") -> Item:  # fmt: skip
    return Item(problem_id=problem, split="resampling", condition=condition, outcome=outcome,
                sample=sample, model_id="m", settings_sha256="s",
                status=None if objective is None and status == "optimal" else status,
                objective=objective)  # fmt: skip


def problem(pid: str, key: float = 4.0) -> followup.Problem:
    return followup.Problem(id=pid, document="toy", answer=key)


def cells(pid: str, samples=(4.0, 4.0, 4.0, 4.0, 4.0), base: float | None = 4.0) -> list[Item]:
    """Single-shot samples 3 to 7, then the baseline's sample 3 (None: no answer)."""
    found = [item(pid, "single-shot", s, v) for s, v in zip(range(3, 8), samples, strict=True)]
    return [*found, item(pid, "baseline", 3, base)]


def test_a_unit_is_a_verified_sample_3_and_wrong_means_silent():
    items = [*cells("p1"), *cells("p2", (5.0, 5.0, 5.0, 5.0, 5.0), 5.0),
             *cells("p3", (None, 4.0, 4.0, 4.0, 4.0)),
             item("p4", "single-shot", 3, None, status="infeasible"), *cells("p4")[1:]]  # fmt: skip
    problems = [problem(p) for p in ("p1", "p2", "p3", "p4")]
    rows = resampling_report.unit_rows(problems, resampling_report.cell_answers(items))
    assert [(r["problem"], r["silent"], r["flagged"]) for r in rows] == [
        ("p1", False, False), ("p2", True, False)]  # fmt: skip
    # p3: no answer at sample 3; p4: a confirmed "infeasible" isn't verified: no unit either.


def test_missing_answers_anywhere_count_as_disagreement():
    errored = item("p1", "single-shot", 6, outcome="errored", objective=None)
    loud = cells("p2", (4.0, 4.0, None, 4.0, 4.0))  # a loud failure at sample 5
    no_base = cells("p3", base=None)  # the baseline's reply couldn't be parsed
    items = [*cells("p1")[:3], errored, *cells("p1")[4:], *loud, *no_base]
    rows = resampling_report.unit_rows([problem(p) for p in ("p1", "p2", "p3")],
                                       resampling_report.cell_answers(items))  # fmt: skip
    assert [(r["samples_disagree"], r["baseline_disagrees"]) for r in rows] == [
        (True, False), (True, False), (False, True)]  # fmt: skip
    assert all(r["flagged"] for r in rows)


def test_a_difference_within_the_tolerance_is_agreement():
    rows = resampling_report.unit_rows([problem("p1")], resampling_report.cell_answers(
        cells("p1", (4.0, 4.0002, 4.0, 4.0, 4.0), 4.0003)))  # fmt: skip
    assert rows[0]["flagged"] is False  # 1e-4 relative and absolute


def test_r1_is_fishers_exact_test_one_sided():
    counts = {(True, True): 6, (True, False): 4, (False, True): 2, (False, False): 30}
    rows = [{"flagged": flagged, "silent": silent, "problem": f"{flagged}{silent}{i}"}
            for (flagged, silent), n in counts.items() for i in range(n)]  # fmt: skip
    r = resampling_report.r1(rows)
    expected = fisher_exact([[6, 4], [2, 30]], alternative="greater").pvalue
    assert r["p_value"] == pytest.approx(expected) and r["supported"] == (expected < 0.05)
    assert (r["precision"]["value"], r["recall"]["value"]) == (0.6, 0.75)
    assert r["base_rate"]["value"] == pytest.approx(8 / 42)
    assert r["precision_over_base_rate"] == pytest.approx(0.6 / (8 / 42))


def test_r2_majority_of_five_against_one_sample():
    problems = [problem(p) for p in ("p1", "p2", "p3", "p4")]
    items = [
        *cells("p1", (5.0, 4.0, 4.0, 4.0, 5.0)),  # majority right, sample 3 wrong
        *cells("p2", (4.0, 5.0, 5.0, 5.0, 4.0)),  # majority wrong, sample 3 right
        *cells("p3", (4.0, 5.0, None, None, 6.0)),  # no 3 agree: the majority has none
        *cells("p4", (None, 4.0, 4.0, 4.0, None)),
    ]  # sample 3 missing; majority right
    r = resampling_report.r2(problems, resampling_report.cell_answers(items))
    assert (r["one_sample_right"], r["majority_right"]) == (2, 2)
    assert (r["only_one_sample_right"], r["only_majority_right"]) == (2, 2)
    assert r["p_value"] == 1.0 and r["detected"] is False


def test_the_report_has_the_secondary_analysis_and_abstention():
    disputed = sorted(resampling_report.DISPUTED)[0]
    problems = [problem("p1"), problem(disputed, key=9.0)]
    items = [*cells("p1", (4.0, 5.0, 4.0, 4.0, 4.0)), *cells(disputed)]
    report = resampling_report.build(items, problems)
    assert report["r1"]["units"] == 2 and report["r1_without_disputed"]["units"] == 1
    assert report["abstention"] == {"silent_made_loud": 0, "right_lost": 1, "silent_left": 1}
    assert report["problems_complete"] == 2 and report["cells_errored"] == 0
