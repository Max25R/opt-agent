"""The second-model samples study's analysis (docs/second_model/SAMPLES_PREREGISTRATION.md,
section 4): everything it computes, from three single-shot samples per problem for each model
and the follow-up's keys. It calls no API, and its hash is part of the freeze.

- **The answers:** Claude Sonnet 5.5's sample 0 from the second-model study's run
  (second_model_samples.SONNET_RECORD), its samples 1 and 2 from this study's run; Claude Haiku
  5.5's samples 0, 1 and 2 from the follow-up's test run (HAIKU_RECORD). For each, the latest
  single-shot item of that sample per problem.
- **Right:** a done item whose answer is right by the follow-up's scoring
  (second_model_report.right: followup_report.is_right, followup.is_correct). Anything else is
  wrong: no answer (a loud failure), an errored item, a missing one.
- **A model's score on a problem:** how many of its 3 samples are right (0 to 3).
- **S2, the primary test,** is the follow-up's three-sample comparison, computed by the function
  its report used (followup_report.contrast, with Haiku as "a" and Sonnet as "b"): the paired
  sign-flip permutation test on the per-problem score differences, Sonnet minus Haiku,
  two-sided and exact (stats.sign_flip_exact), alpha 0.05. One comparison, so no Holm.
  Supported: p < alpha and Sonnet's mean score is higher; not supported: p < alpha and Haiku's
  is; inconclusive: p >= alpha. A verdict needs the run complete (every call of samples 1 and
  2 settled); otherwise it's "incomplete". Reported whatever the verdict: each model's mean
  score (its right answers over its 363) with the follow-up's bootstrap interval, the
  difference (a share: Sonnet's mean score minus Haiku's) with the follow-up's 95% paired
  percentile bootstrap interval over problems (10,000 resamples, seed 20261109), the smallest
  whole X with that interval inside +/-X points (followup_report.bound_pp), and how many
  problems each model scored higher on.
- **Secondary, no verdict:** majority of three (a problem is right for a model if 2 or 3 of
  its samples are), from the same contrast: the exact McNemar test (two-sided) on the problems
  only one model's majority got right, each model's majority accuracy with a 95% Wilson
  interval, and the majority difference with its bootstrap interval. And each model's silent
  failures over its three samples (a verified answer, a confirmed optimum, that's wrong), of
  its answers and of its verified answers, with Wilson intervals, and the rest of its wrong
  answers, each counted as second_model_report.failures counts them for one sample.
- **Descriptive:** each model's right answers per sample, and the cost and latency of Sonnet's
  samples 1 and 2 (second_model_report.spend).

Every value written is a Python bool, int, float, str, list or dict, so json writes it.

Run:  python -m opt_agent.second_model_samples_report [RUN_DIR]
      # writes results/second_model_samples.json
"""

import argparse
import json
from pathlib import Path

from opt_agent import followup, followup_report, second_model, second_model_samples
from opt_agent.evaluate import Item
from opt_agent.followup_report import bound_pp
from opt_agent.runs import REPO_ROOT
from opt_agent.second_model_report import failures, items_of, rate, right, spend

ALPHA = 0.05
RESULTS = REPO_ROOT / "results" / "second_model_samples.json"
VERDICTS = ("supported", "not supported", "inconclusive", "incomplete")
SAMPLES = (0, *second_model_samples.SAMPLES)  # each model's three: 0, 1 and 2
NEW = second_model_samples.SAMPLES  # Sonnet's samples from this study's run
HAIKU_RECORD = second_model_samples.HAIKU_RECORD
SONNET_RECORD = second_model_samples.SONNET_RECORD
CONDITION = second_model_samples.CONDITION

BySample = dict[int, dict[str, Item]]  # sample -> problem id -> its latest item


# ---- reading ----------------------------------------------------------------------------


def sonnet_items(run_dir: Path, record: Path = SONNET_RECORD) -> BySample:
    """Sonnet's sample 0 from the second-model study's run, and samples 1 and 2 from this one."""
    found = {0: items_of(record, 0, CONDITION)}
    found |= {s: items_of(run_dir / "results.jsonl", s, CONDITION) for s in NEW}
    return found


def haiku_items(record: Path = HAIKU_RECORD) -> BySample:
    return {s: items_of(record, s, CONDITION) for s in second_model_samples.HAIKU_SAMPLES}


def settled_calls(results: Path) -> set[tuple[str, int]]:
    """The (problem, sample) calls of the run that need nothing more (second_model.settled)."""
    entries: dict[tuple[str, int], list[dict]] = {}
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item" and entry["condition"] == CONDITION:
            entries.setdefault((entry["problem_id"], entry["sample"]), []).append(entry)
    return {key for key, found in entries.items() if second_model.settled(found)}


# ---- statistics -------------------------------------------------------------------------


def scores(problems: list[followup.Problem], by_sample: BySample) -> dict[str, int]:
    """Per problem, how many of the model's samples are right."""
    return {p.id: sum(right(p, items.get(p.id)) for items in by_sample.values())
            for p in problems}  # fmt: skip


def verdict(difference: float | None, p_value: float, complete: bool) -> str:
    """Section 4's rule, decided before any reply of samples 1 and 2 existed."""
    if not complete:
        return "incomplete"
    if p_value >= ALPHA or difference is None:
        return "inconclusive"
    return "supported" if difference > 0 else "not supported"


def compare(problems: list[followup.Problem], sonnet: BySample, haiku: BySample,
            complete: bool) -> tuple[dict, dict]:  # fmt: skip
    """S2 and the majority-of-three comparison, both from the follow-up's contrast (b minus
    a: Sonnet minus Haiku)."""
    n, each = len(problems), len(SAMPLES)
    s, h = scores(problems, sonnet), scores(problems, haiku)
    counts = {p.id: {"haiku": h[p.id], "sonnet": s[p.id]} for p in problems}
    c = followup_report.contrast(counts, "haiku", "sonnet", each)
    mean = {m: followup_report.accuracy(counts, m, each) for m in ("sonnet", "haiku")}
    s2 = {
        "problems": n,
        "samples_each": each,
        "sonnet_right": sum(s.values()),
        "haiku_right": sum(h.values()),
        "answers_each": n * each,
        "sonnet_mean_score": mean["sonnet"]["mean_score"],
        "sonnet_mean_score_ci95": mean["sonnet"]["mean_score_ci"],
        "haiku_mean_score": mean["haiku"]["mean_score"],
        "haiku_mean_score_ci95": mean["haiku"]["mean_score_ci"],
        "problems_sonnet_higher": c["problems_b_better"],
        "problems_haiku_higher": c["problems_a_better"],
        "problems_tied": n - c["problems_b_better"] - c["problems_a_better"],
        "difference": c["score_difference"],
        "difference_ci95": c["score_ci"],
        "within_pp": bound_pp(c["score_ci"]),
        "p_value": float(c["sign_flip_p"]),
        "alpha": ALPHA,
        "verdict": verdict(c["score_difference"], c["sign_flip_p"], complete),
    }
    majority = {
        "problems": n,
        "sonnet_right": mean["sonnet"]["majority_right"],
        "haiku_right": mean["haiku"]["majority_right"],
        "only_sonnet_right": c["majority_only_b"],
        "only_haiku_right": c["majority_only_a"],
        "p_value": float(c["mcnemar_p"]),
        "sonnet_accuracy": rate(mean["sonnet"]["majority_right"], n),
        "haiku_accuracy": rate(mean["haiku"]["majority_right"], n),
        "difference": c["majority_difference"],
        "difference_ci95": c["majority_ci"],
    }
    return s2, majority


def all_failures(problems: list[followup.Problem], by_sample: BySample) -> dict:
    """Secondary: second_model_report.failures for each sample, added up over the three, with
    silent failures as rates of the answers and of the verified answers."""
    per = [failures(problems, items) for items in by_sample.values()]
    verified = sum(f["verified"] for f in per)
    silent = sum(f["silent"]["k"] for f in per)
    return {
        "answers": len(problems) * len(per),
        "verified": verified,
        "silent": rate(silent, len(problems) * len(per)),
        "silent_of_verified": rate(silent, verified),
        **{name: sum(f[name] for f in per)
           for name in ("wrong_verdicts", "loud", "cut_off", "errored_or_missing")},
        "silent_by_sample": [f["silent"]["k"] for f in per],
    }  # fmt: skip


# ---- the report -------------------------------------------------------------------------


def build(run_dir: Path, problems: list[followup.Problem], sonnet_record: Path = SONNET_RECORD,
          haiku_record: Path = HAIKU_RECORD) -> dict:  # fmt: skip
    results = run_dir / "results.jsonl"
    sonnet, haiku = sonnet_items(run_dir, sonnet_record), haiku_items(haiku_record)
    wanted = {(p.id, s) for p in problems for s in NEW}
    settled = wanted & settled_calls(results)
    complete = settled == wanted
    s2, majority = compare(problems, sonnet, haiku, complete)
    s_scores, h_scores = scores(problems, sonnet), scores(problems, haiku)
    return {
        "label": "the second-model samples study (docs/second_model/SAMPLES_PREREGISTRATION.md); "
                 "S2 primary",
        "models": {"sonnet": second_model_samples.MODEL,
                   "haiku": second_model_samples.HAIKU_MODEL},
        "records": {"sonnet_sample_0": shown(sonnet_record), "haiku": shown(haiku_record),
                    "sonnet_samples_1_and_2": shown(run_dir)},
        "problems": len(problems),
        "samples": list(SAMPLES),
        "complete": complete,
        "calls": len(wanted),
        "settled": len(settled),
        "errored": sum(items[p.id].outcome == "errored" for s, items in sonnet.items()
                       if s in NEW for p in problems if p.id in items),
        "s2": s2,
        "majority": majority,
        "failures": {"sonnet": all_failures(problems, sonnet),
                     "haiku": all_failures(problems, haiku)},
        "right_by_sample": {
            name: [sum(right(p, items.get(p.id)) for p in problems) for items in found.values()]
            for name, found in (("sonnet", sonnet), ("haiku", haiku))},
        "spend": {f"sonnet_sample_{s}": spend(problems, sonnet[s]) for s in NEW},
        "scores": [{"problem": p.id, "sonnet_right": s_scores[p.id], "haiku_right": h_scores[p.id]}
                   for p in problems],
    }  # fmt: skip


def shown(path: Path) -> str:
    """A path as the report writes it: repo-relative when it can be."""
    return str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)


def dumps(report: dict) -> str:
    return json.dumps(report, indent=1) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The second-model samples study's analysis.")
    parser.add_argument("run_dir", type=Path, nargs="?", default=second_model_samples.RUN_DIR)
    args = parser.parse_args(argv)
    problems, _ = second_model_samples.inputs(tag=False)  # the approved inputs, no tag needed
    report = build(args.run_dir, problems)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(dumps(report))
    s2 = report["s2"]
    print(f"S2: Sonnet {s2['sonnet_right']} vs Haiku {s2['haiku_right']} right of "
          f"{s2['answers_each']} each, sign-flip p = {s2['p_value']:.3g}: {s2['verdict']}. "
          f"-> {RESULTS}")  # fmt: skip


if __name__ == "__main__":
    main()
