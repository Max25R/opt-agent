"""The second-model study's analysis (docs/SECOND_MODEL_PREREGISTRATION.md, section 4, and
Amendment 1): everything they compute, from the run's results.jsonl, Haiku's record and the
follow-up's keys. It calls no API, and its hash is part of the freeze.

- **Pairs:** each of the 121 problems, Sonnet's answer (the run's latest item for it) with
  Haiku's sample 0 (the latest item for it in second_model.HAIKU_RECORD), in the same
  condition.
- **Right:** a done item whose answer is right by the follow-up's scoring
  (followup_report.is_right: followup.is_correct, 1e-4). Anything else is wrong: no answer (a
  loud failure), an errored item, a missing one.
- **S1, the primary test (stage 1, single-shot):** exact McNemar, two-sided
  (stats.mcnemar_exact), alpha 0.05, on the problems only one model got right. Supported:
  p < alpha and Sonnet got more of those right; not supported: p < alpha and Haiku did;
  inconclusive: p >= alpha. A verdict needs stage 1 complete (every problem's call settled);
  otherwise it's "incomplete". Reported whatever the verdict: each model's accuracy with a 95%
  Wilson interval, and the paired difference (Sonnet minus Haiku) with the follow-up's 95%
  paired percentile bootstrap interval (followup_report.bootstrap_ci: 10,000 resamples, seed
  20261109) and the smallest whole X with that interval inside +/-X points
  (followup_report.bound_pp). The study's verdict is S1's alone.
- **Secondary, no test:** each model's silent failures in stage 1 (a verified answer, a
  confirmed optimum, that's wrong), of the problems and of its verified answers, with Wilson
  intervals; and the rest of its wrong answers: wrong confirmed verdicts (infeasible,
  unbounded) and loud failures (cut-off replies among them, counted).
- **Descriptive only:** cost and latency per correct answer. Each model's total cost_usd
  (every call its answers used, at its own prices) and total latency_s (API plus solver time,
  without retry waits) over the problems, divided by its right answers.
- **Sensitivity, no claim:** S1's counts and test again with Haiku's samples 1 and 2 in place
  of sample 0, which is Haiku's lowest-scoring sample on these problems (known before the
  study, section 2), and Haiku's accuracy averaged over samples 0 to 2.
- **Stage 2, secondary (Amendment 1):** single-shot against the no-solver baseline, for Sonnet
  (stage 1's answers against stage 2's) and, for context, for Haiku (sample 0 of each): the
  same exact McNemar test and paired difference (single-shot minus no-solver), no verdict.
  Sonnet's comparison only if stage 2 is complete; otherwise stage 2 is "incomplete" (or "not
  started", if stage 1 wasn't complete), with how far it got and what it cost.

Every value written is a Python bool, int, float, str, list or dict, so json writes it (the
resampling study's main() couldn't, over a numpy bool: its deviation 1).

Run:  python -m opt_agent.second_model_report [RUN_DIR]   # writes results/second_model.json
"""

import argparse
import json
from pathlib import Path

import numpy as np

from opt_agent import followup, second_model, stats
from opt_agent.evaluate import Item, latest_items
from opt_agent.followup_report import answer_of, bootstrap_ci, bound_pp, is_right
from opt_agent.runs import REPO_ROOT
from opt_agent.solver import Status

ALPHA = 0.05
RESULTS = REPO_ROOT / "results" / "second_model.json"
HAIKU_SAMPLES = (0, 1, 2)  # the follow-up's; 1 and 2 only in the sensitivity rows
VERDICTS = ("supported", "not supported", "inconclusive", "incomplete")
SINGLE_SHOT, NO_SOLVER = second_model.CONDITION, second_model.BASELINE


# ---- reading ----------------------------------------------------------------------------


def items_of(results: Path, sample: int, condition: str = SINGLE_SHOT) -> dict[str, Item]:
    """The latest item of `condition` and `sample` per problem."""
    return {i.problem_id: i for i in latest_items(results)
            if i.condition == condition and i.sample == sample}  # fmt: skip


def settled_problems(results: Path, condition: str = SINGLE_SHOT) -> set[str]:
    """The problems whose Sonnet call in `condition` needs nothing more
    (second_model.settled)."""
    entries: dict[str, list[dict]] = {}
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item" and entry["condition"] == condition:
            entries.setdefault(entry["problem_id"], []).append(entry)
    return {pid for pid, found in entries.items() if second_model.settled(found)}


def right(problem: followup.Problem, item: Item | None) -> bool:
    return item is not None and item.outcome == "done" and is_right(problem, answer_of(item))


def verified(item: Item | None) -> bool:
    """A confirmed optimum: CBC and HiGHS agree on it and the checks pass."""
    return item is not None and item.outcome == "done" and item.status == Status.OPTIMAL


# ---- statistics -------------------------------------------------------------------------


def rate(k: int, n: int) -> dict:
    low, high = stats.wilson(k, n)
    return {"k": k, "n": n, "value": k / n if n else None, "wilson95": [low, high]}


def verdict(only_sonnet: int, only_haiku: int, p_value: float, complete: bool) -> str:
    """Section 4's rule, decided before any Sonnet reply existed."""
    if not complete:
        return "incomplete"
    if p_value >= ALPHA:
        return "inconclusive"
    return "supported" if only_sonnet > only_haiku else "not supported"


def paired(problems: list[followup.Problem], first: dict[str, Item], second: dict[str, Item],
           names: tuple[str, str]) -> dict:  # fmt: skip
    """Right or wrong per problem for two answer sets, named `names`: the exact McNemar test
    (two-sided) on the problems only one got right, each set's accuracy, and the paired
    difference (first minus second) with its interval."""
    a, b = names
    x = np.array([right(p, first.get(p.id)) for p in problems], dtype=float)
    y = np.array([right(p, second.get(p.id)) for p in problems], dtype=float)
    only_x, only_y = int(((x == 1) & (y == 0)).sum()), int(((x == 0) & (y == 1)).sum())
    n, difference = len(problems), x - y
    ci = bootstrap_ci(difference)
    return {
        "problems": n,
        f"{a}_right": int(x.sum()), f"{b}_right": int(y.sum()),
        f"only_{a}_right": only_x, f"only_{b}_right": only_y,
        "both_right": int(((x == 1) & (y == 1)).sum()),
        "both_wrong": int(((x == 0) & (y == 0)).sum()),
        "p_value": float(stats.mcnemar_exact(only_x, only_y)),  # a numpy float when < 1
        f"{a}_accuracy": rate(int(x.sum()), n), f"{b}_accuracy": rate(int(y.sum()), n),
        "difference": float(difference.mean()) if n else None,
        "difference_ci95": ci,
        "within_pp": bound_pp(ci),
    }  # fmt: skip


def compare(problems: list[followup.Problem], sonnet: dict[str, Item], haiku: dict[str, Item],
            complete: bool) -> dict:  # fmt: skip
    """S1: Sonnet against Haiku, the exact McNemar test, the verdict, and the effect."""
    found = paired(problems, sonnet, haiku, ("sonnet", "haiku"))
    rule = verdict(found["only_sonnet_right"], found["only_haiku_right"], found["p_value"],
                   complete)  # fmt: skip
    return {**found, "alpha": ALPHA, "verdict": rule}


def failures(problems: list[followup.Problem], items: dict[str, Item]) -> dict:
    """Secondary: silent failures (verified and wrong), wrong confirmed verdicts, and loud
    failures (no answer: none confirmed or parsed, an errored item, or no item at all)."""
    found = [(p, items.get(p.id)) for p in problems]
    checked = [(p, i) for p, i in found if verified(i)]
    silent = sum(not right(p, i) for p, i in checked)
    confirmed = [(p, i) for p, i in found if i is not None and i.outcome == "done"]
    verdicts = [(p, i) for p, i in confirmed if i.status not in (None, Status.OPTIMAL)]
    loud = [i for _, i in found if i is None or i.outcome != "done" or i.status is None]
    return {
        "verified": len(checked),
        "silent": rate(silent, len(problems)),
        "silent_of_verified": rate(silent, len(checked)),
        "wrong_verdicts": sum(not right(p, i) for p, i in verdicts),
        "loud": len(loud),
        "cut_off": sum(i is not None and "cut off" in (i.reason or "") for i in loud),
        "errored_or_missing": sum(i is None or i.outcome != "done" for i in loud),
    }


def spend(problems: list[followup.Problem], items: dict[str, Item]) -> dict:
    """Descriptive: cost and latency in all, per answer and per right answer."""
    present = [items[p.id] for p in problems if p.id in items]
    right_answers = sum(right(p, items.get(p.id)) for p in problems)
    cost, latency = sum(i.cost_usd for i in present), sum(i.latency_s for i in present)
    return {
        "answers": len(present), "right": right_answers,
        "cost_usd": cost, "latency_s": latency,
        "cost_per_answer_usd": cost / len(present) if present else None,
        "cost_per_right_answer_usd": cost / right_answers if right_answers else None,
        "latency_per_right_answer_s": latency / right_answers if right_answers else None,
        "median_latency_s": float(np.median([i.latency_s for i in present])) if present else None,
        "input_tokens": sum(i.input_tokens for i in present),
        "output_tokens": sum(i.output_tokens for i in present),
    }  # fmt: skip


def sensitivity(problems: list[followup.Problem], sonnet: dict[str, Item], record: Path) -> dict:
    """S1's counts and test with each other Haiku sample in place of sample 0 (no claim)."""
    by_sample = {s: items_of(record, s) for s in HAIKU_SAMPLES}
    rows: dict[str, object] = {}
    for sample in HAIKU_SAMPLES[1:]:
        r = compare(problems, sonnet, by_sample[sample], complete=True)
        rows[f"haiku_sample_{sample}"] = {
            name: r[name] for name in ("haiku_right", "only_sonnet_right", "only_haiku_right",
                                       "p_value", "difference", "difference_ci95")
        }  # fmt: skip
    rights = sum(right(p, found.get(p.id)) for found in by_sample.values() for p in problems)
    n = len(problems) * len(HAIKU_SAMPLES)
    rows["haiku_mean_accuracy"] = rights / n if n else None
    return rows


def stage_2(problems: list[followup.Problem], results: Path, record: Path,
            stage_1_complete: bool) -> dict:  # fmt: skip
    """Amendment 1's secondary comparison: single-shot against the no-solver baseline."""
    ids = {p.id for p in problems}
    settled = ids & settled_problems(results, NO_SOLVER)
    complete = stage_1_complete and settled == ids
    status = "complete" if complete else "incomplete" if stage_1_complete else "not started"
    names = ("single_shot", "no_solver")
    sonnet_baseline = items_of(results, second_model.SAMPLE, NO_SOLVER)
    haiku = paired(problems, items_of(record, second_model.HAIKU_SAMPLE),
                   items_of(record, second_model.HAIKU_SAMPLE, NO_SOLVER), names)  # fmt: skip
    sonnet = (paired(problems, items_of(results, second_model.SAMPLE), sonnet_baseline, names)
              if complete else None)  # fmt: skip
    return {
        "status": status, "settled": len(settled),
        "sonnet": sonnet, "haiku": haiku,
        "spend": {"sonnet": spend(problems, sonnet_baseline),
                  "haiku": spend(problems, items_of(record, second_model.HAIKU_SAMPLE,
                                                    NO_SOLVER))},
    }  # fmt: skip


# ---- the report -------------------------------------------------------------------------


def build(run_dir: Path, problems: list[followup.Problem],
          record: Path = second_model.HAIKU_RECORD) -> dict:  # fmt: skip
    results = run_dir / "results.jsonl"
    sonnet = items_of(results, second_model.SAMPLE)
    haiku = items_of(record, second_model.HAIKU_SAMPLE)
    settled = settled_problems(results)
    ids = {p.id for p in problems}
    complete = ids <= settled
    shown = record.relative_to(REPO_ROOT) if record.is_relative_to(REPO_ROOT) else record
    return {
        "label": "the second-model study (docs/SECOND_MODEL_PREREGISTRATION.md, with its "
                 "Amendment 1); S1 primary",
        "models": {"sonnet": second_model.MODEL, "haiku": second_model.HAIKU_MODEL},
        "haiku_record": {"path": str(shown), "sample": second_model.HAIKU_SAMPLE},
        "problems": len(problems),
        "complete": complete,
        "sonnet_settled": len(ids & settled),
        "sonnet_errored": sum(i.outcome == "errored" for pid, i in sonnet.items() if pid in ids),
        "s1": compare(problems, sonnet, haiku, complete),
        "failures": {"sonnet": failures(problems, sonnet), "haiku": failures(problems, haiku)},
        "spend": {"sonnet": spend(problems, sonnet), "haiku": spend(problems, haiku)},
        "sensitivity": sensitivity(problems, sonnet, record),
        "stage_2": stage_2(problems, results, record, complete),
        "pairs": [{"problem": p.id,
                   "sonnet_right": right(p, sonnet.get(p.id)),
                   "haiku_right": right(p, haiku.get(p.id)),
                   "sonnet_verified": verified(sonnet.get(p.id)),
                   "haiku_verified": verified(haiku.get(p.id))} for p in problems],
    }  # fmt: skip


def dumps(report: dict) -> str:
    return json.dumps(report, indent=1) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The second-model study's analysis.")
    parser.add_argument("run_dir", type=Path, nargs="?", default=second_model.RUN_DIR)
    args = parser.parse_args(argv)
    problems, _ = second_model.inputs(tag=False)  # the approved inputs; the tag isn't needed
    report = build(args.run_dir, problems)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(dumps(report))
    s1, two = report["s1"], report["stage_2"]
    print(f"S1: {s1['sonnet_right']} vs {s1['haiku_right']} right of {s1['problems']}, "
          f"p = {s1['p_value']:.3g}: {s1['verdict']}. Stage 2: {two['status']}. "
          f"-> {RESULTS}")  # fmt: skip


if __name__ == "__main__":
    main()
