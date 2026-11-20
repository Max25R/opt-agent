"""The resampling study's analysis (docs/RESAMPLING_PREREGISTRATION.md, section 4): everything
that section computes, from a run directory's results.jsonl and the follow-up's keys. It
calls no API, and its hash is part of the freeze.

- **Units (R1):** a problem's single-shot sample 3, if it's verified. In the follow-up's
  records a single-shot item holds only a confirmed answer, so verified is a confirmed
  optimum: status "optimal". Silent failure: wrong by followup.is_correct.
- **The flag:** samples 3 to 7 don't all agree, or the baseline's sample 3 differs from the
  unit (followup_report.same_answer, 1e-4). A cell with no usable answer (a loud failure, a
  cut-off or unparseable reply, an errored call) has none, and none differs from any answer.
- **R1:** Fisher's exact test, one-sided ("greater": flagged units are more often silent
  failures), alpha 0.05; supported if p < 0.05. With the base rate, flag rate, precision and
  recall, each with a 95% Wilson interval.
- **R2, on every problem:** sample 3 alone against the majority of samples 3 to 7 (an answer
  at least 3 verified samples give), each right or wrong; exact McNemar, two-sided.
- **Secondary:** R1 without the 13 disputed problems; and what abstaining on a flag would do.

Run:  python -m opt_agent.resampling_report [RUN_DIR]   # writes results/resampling.json
"""

import argparse
import json
from pathlib import Path

from scipy.stats import fisher_exact

from opt_agent import followup, followup_report, resampling, stats
from opt_agent.evaluate import Item, latest_items
from opt_agent.followup_report import Answer, answer_of, same_answer
from opt_agent.runs import REPO_ROOT

ALPHA = 0.05
MAJORITY = 3  # of the 5 single-shot samples
RESULTS = REPO_ROOT / "results" / "resampling.json"
DISPUTED = frozenset({
    "complexlp:63", "complexlp:78", "complexlp:81", "complexlp:83", "complexlp:94",
    "industryor:17", "industryor:22", "industryor:24", "industryor:26", "industryor:27",
    "industryor:28", "industryor:30", "industryor:41",
})  # fmt: skip  # section 2: an LLM judge's flags, not verified by a person


def cell_answers(items: list[Item]) -> dict[tuple[str, str, int], Answer | None]:
    """Each cell's answer; None where it has none (an errored latest line is none too)."""
    return {(i.problem_id, i.condition, i.sample): answer_of(i) if i.outcome == "done" else None
            for i in items}  # fmt: skip


def verified(answer: Answer | None) -> bool:
    return answer is not None and answer[0] == "optimal"


def all_agree(answers: list[Answer | None]) -> bool:
    return all(same_answer(x, y) for i, x in enumerate(answers) for y in answers[i + 1 :])


def unit_rows(problems: list[followup.Problem], answers: dict) -> list[dict]:
    """One row per problem whose sample 3 is verified."""
    rows = []
    for p in problems:
        unit = answers.get((p.id, "single-shot", resampling.UNIT_SAMPLE))
        if not verified(unit):
            continue
        samples = [answers.get((p.id, "single-shot", s)) for s in resampling.SINGLE_SHOT_SAMPLES]
        base = answers.get((p.id, "baseline", resampling.BASELINE_SAMPLE))
        rows.append({"problem": p.id, "silent": not followup_report.is_right(p, unit),
                     "samples_disagree": not all_agree(samples),
                     "baseline_disagrees": not same_answer(base, unit)})  # fmt: skip
        rows[-1]["flagged"] = rows[-1]["samples_disagree"] or rows[-1]["baseline_disagrees"]
    return rows


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "value": k / n if n else None, "wilson95": list(stats.wilson(k, n))}


def r1(rows: list[dict]) -> dict:
    flagged = [r for r in rows if r["flagged"]]
    silent = [r for r in rows if r["silent"]]
    a = sum(r["silent"] for r in flagged)
    b, c = len(flagged) - a, len(silent) - a
    d = len(rows) - a - b - c
    p = float(fisher_exact([[a, b], [c, d]], alternative="greater").pvalue) if rows else None
    precision, base = rate(a, len(flagged)), rate(len(silent), len(rows))
    return {
        "units": len(rows), "table": {"flagged_silent": a, "flagged_right": b,
                                      "unflagged_silent": c, "unflagged_right": d},
        "p_value": p, "supported": p is not None and p < ALPHA,
        "base_rate": base, "flag_rate": rate(len(flagged), len(rows)), "precision": precision,
        "recall": rate(a, len(silent)),
        "precision_over_base_rate": precision["value"] / base["value"]
        if precision["value"] is not None and base["value"] else None,
    }  # fmt: skip


def majority(answers: list[Answer | None]) -> Answer | None:
    """An answer at least MAJORITY of the verified samples give (the first such), or None."""
    votes = [a for a in answers if verified(a)]
    for candidate in votes:
        if sum(same_answer(candidate, other) for other in votes) >= MAJORITY:
            return candidate
    return None


def r2(problems: list[followup.Problem], answers: dict) -> dict:
    one, many = [], []
    for p in problems:
        unit = answers.get((p.id, "single-shot", resampling.UNIT_SAMPLE))
        five = [answers.get((p.id, "single-shot", s)) for s in resampling.SINGLE_SHOT_SAMPLES]
        one.append(verified(unit) and followup_report.is_right(p, unit))
        best = majority(five)
        many.append(best is not None and followup_report.is_right(p, best))
    only_one = sum(o and not m for o, m in zip(one, many, strict=True))
    only_many = sum(m and not o for o, m in zip(one, many, strict=True))
    p_value = stats.mcnemar_exact(only_one, only_many)
    return {"problems": len(problems), "one_sample_right": sum(one),
            "majority_right": sum(many), "only_one_sample_right": only_one,
            "only_majority_right": only_many, "p_value": p_value,
            "detected": p_value < ALPHA}  # fmt: skip


def abstention(rows: list[dict]) -> dict:
    """If flagged units were withheld: silent failures made loud, right answers lost."""
    return {"silent_made_loud": sum(r["flagged"] and r["silent"] for r in rows),
            "right_lost": sum(r["flagged"] and not r["silent"] for r in rows),
            "silent_left": sum(r["silent"] and not r["flagged"] for r in rows)}  # fmt: skip


def build(items: list[Item], problems: list[followup.Problem]) -> dict:
    answers = cell_answers(items)
    rows = unit_rows(problems, answers)
    complete = sum(all((p.id, c, s) in answers for c, s in resampling.CELLS) for p in problems)
    return {
        "label": "the resampling study (docs/RESAMPLING_PREREGISTRATION.md); R1 primary",
        "problems": len(problems), "problems_complete": complete,
        "problems_without_a_unit": len(problems) - len(rows),
        "cells_errored": sum(i.outcome == "errored" for i in items),
        "r1": r1(rows),
        "r1_without_disputed": r1([r for r in rows if r["problem"] not in DISPUTED]),
        "r2": r2(problems, answers),
        "abstention": abstention(rows),
        "units": rows,
    }  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The resampling study's analysis.")
    parser.add_argument("run_dir", type=Path, nargs="?", default=resampling.RUN_DIR)
    args = parser.parse_args(argv)
    report = build(latest_items(args.run_dir / "results.jsonl"), resampling.problems())
    RESULTS.write_text(json.dumps(report, indent=1) + "\n")
    r = report["r1"]
    print(f"R1: {r['units']} units, p = {r['p_value']}, "
          f"{'supported' if r['supported'] else 'not supported'}; -> {RESULTS}")  # fmt: skip


if __name__ == "__main__":
    main()
