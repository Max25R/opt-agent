"""The follow-up's analysis (docs/FOLLOWUP_PREREGISTRATION.md, sections 4 and 5): a run
directory's answers, scored against the key, into report.json. No API calls.

- **Unit: the problem.** A problem counts only if every condition has a done answer for every
  sample (section 6: a run stopped by its cap is analyzed on complete problems only, the same
  set for every condition). The others are listed as incomplete.
- **Per-problem score:** samples right out of n (followup.is_correct, 1e-4). **Majority:**
  right in more than half the samples.
- **Contrasts** (a, b) give b minus a. The primary test is the exact paired sign-flip test on
  the per-problem differences (stats.sign_flip_exact); the secondary is exact McNemar on the
  majority. Holm over H1 and H2, separately for each test; the four other pairs are
  exploratory, with no Holm.
- **Intervals:** a paired percentile bootstrap over problems, BOOTSTRAP_RESAMPLES resamples,
  seeded with BOOTSTRAP_SEED afresh for every interval, so each is reproducible on its own.
- **Verdict:** "detected" only if the primary test's Holm-adjusted p is below 0.05, else
  "inconclusive"; then `bound_pp` is the smallest whole X with the interval inside +/-X, the
  only "no difference larger than X pp" the report may claim.
- **Rows:** the primary analysis leaves out the problems seen before the split; the
  sensitivity row has every complete problem. A corrected-key row is added when corrected
  keys are given (5b: overturned keys only, applied to every condition).
- **Dispute trigger (5b):** a problem is checked if at least 3 conditions' majority answers
  agree (same status, objectives within 1e-4) and differ from the key.
- **Rounding clause (section 4):** an optimum is right within 1e-4, or, for a key written
  with decimals that isn't a whole number, if it rounds to the key at those decimals. The
  report counts, per condition, the answers right only by the rounding clause.
- **Problems are labels** ("complexlp:1", "industryor:1"), and the manifest's problems are the
  denominator: one with no line yet is incomplete, never missing. A key that can't be parsed
  (followup.parse_key) leaves its problem out of every condition before the run, by format
  alone; the report lists those labels and their number.

Same inputs, same report.json: nothing here depends on the time or the order of the lines.

Run:  python -m opt_agent.followup_report runs/NAME   # dev, or the test run once it's frozen
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact

from opt_agent import followup, stats
from opt_agent.evaluate import Item, followup_problems, latest_items
from opt_agent.solver import Status

PRIMARY = {"H1": ("single-shot", "checklist-revision"), "H2": ("baseline", "single-shot")}
EXPLORATORY = {
    "baseline vs self-correction": ("baseline", "self-correction"),
    "baseline vs checklist-revision": ("baseline", "checklist-revision"),
    "single-shot vs self-correction": ("single-shot", "self-correction"),
    "self-correction vs checklist-revision": ("self-correction", "checklist-revision"),
}
ALPHA = 0.05
BOOTSTRAP_SEED = 20261109
BOOTSTRAP_RESAMPLES = 10_000
TRIGGER_CONDITIONS = 3  # 5b: at least 3 of the 4 conditions' majority answers agree
SOLVER_CONDITIONS = ("single-shot", "self-correction", "checklist-revision")

Answer = tuple[str, float | None]  # (status, objective); a loud failure has none


# ---- answers ----------------------------------------------------------------------------


def answer_of(item: Item) -> Answer | None:
    """What a done item answered; None for a loud failure (no confirmed or parsed answer)."""
    if item.status is None:
        return None
    return item.status, item.objective if item.status == Status.OPTIMAL else None


def same_answer(a: Answer | None, b: Answer | None) -> bool:
    """Two answers agree: the same status, and for an optimum objectives within the scoring
    tolerance. Two loud failures agree too (both gave nothing)."""
    if a is None or b is None:
        return a is b
    if a[0] != b[0]:
        return False
    if a[0] != Status.OPTIMAL:
        return True
    tol = followup.TOLERANCE
    return math.isclose(a[1], b[1], rel_tol=tol, abs_tol=tol)


def majority_answer(answers: list[Answer | None]) -> Answer | None:
    """The answer more than half the samples give (the first such sample's), or None. A loud
    failure is never a majority answer: it says nothing to agree on."""
    for candidate in answers:
        if candidate is None:
            continue
        if 2 * sum(same_answer(candidate, other) for other in answers) > len(answers):
            return candidate
    return None


def key_of(problem: followup.Problem) -> float | str:
    """The key as the report writes it: the objective, or the status it names."""
    return problem.answer if problem.key_status == Status.OPTIMAL else str(problem.key_status)


def is_right(problem: followup.Problem, answer: Answer | None) -> bool:
    if answer is None:
        return False
    return followup.is_correct(problem, answer[0], answer[1])


# ---- the table: problem x condition x sample --------------------------------------------


def table(
    items: list[Item], conditions: list[str], samples: list[int], expected: list[str] | None = None
) -> tuple[dict[str, dict[str, list[Item]]], list[str]]:
    """{label: {condition: items in sample order}} for complete problems, and the labels
    of incomplete ones (a pair pending or errored). `expected`: the manifest's problems, as
    labels, so a problem with no line yet is incomplete too; without it, the items' own."""
    by_pair = {(followup.label(i.split, i.problem_id), i.condition, i.sample): i for i in items}
    labels = sorted(expected) if expected is not None else sorted({key[0] for key in by_pair})
    complete, incomplete = {}, []
    for label in labels:
        row = {c: [by_pair.get((label, c, s)) for s in samples] for c in conditions}
        if all(i is not None and i.outcome == "done" for cells in row.values() for i in cells):
            complete[label] = row
        else:
            incomplete.append(label)
    return complete, incomplete


def right_counts(
    grid: dict[str, dict[str, list[Item]]], problems: dict[str, followup.Problem]
) -> dict[str, dict[str, int]]:
    """{label: {condition: samples right}}."""
    return {
        label: {c: sum(is_right(problems[label], answer_of(i)) for i in cells)
                for c, cells in row.items()}
        for label, row in grid.items()
    }  # fmt: skip


# ---- statistics -------------------------------------------------------------------------


def bootstrap_ci(values: np.ndarray) -> list[float] | None:
    """95% paired percentile bootstrap interval for the mean over problems (None for no
    problems: the report is JSON, which has no NaN)."""
    if len(values) == 0:
        return None
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    picks = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    means = values[picks].mean(axis=1)
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def bound_pp(ci: list[float] | None) -> int | None:
    """The smallest whole X (percentage points) with the interval inside +/-X."""
    if ci is None:
        return None
    return math.ceil(round(100 * max(abs(ci[0]), abs(ci[1])), 9))


def contrast(counts: dict[str, dict[str, int]], a: str, b: str, n_samples: int) -> dict:
    """b minus a: the per-problem score difference and the majority difference, each with its
    exact test and bootstrap interval."""
    labels = sorted(counts)
    diffs = np.array([counts[k][b] - counts[k][a] for k in labels], dtype=float)
    # dtype=bool: an empty row (no complete problems) would otherwise be float, and ~ fails
    maj_a = np.array([2 * counts[k][a] > n_samples for k in labels], dtype=bool)
    maj_b = np.array([2 * counts[k][b] > n_samples for k in labels], dtype=bool)
    only_a, only_b = int(np.sum(maj_a & ~maj_b)), int(np.sum(maj_b & ~maj_a))
    return {
        "a": a,
        "b": b,
        "problems": len(labels),
        "score_difference": float(diffs.mean() / n_samples) if labels else None,
        "score_ci": bootstrap_ci(diffs / n_samples),
        "sign_flip_p": stats.sign_flip_exact([int(d) for d in diffs]),
        "problems_b_better": int(np.sum(diffs > 0)),
        "problems_a_better": int(np.sum(diffs < 0)),
        "majority_difference": float((maj_b.astype(float) - maj_a).mean()) if labels else None,
        "majority_ci": bootstrap_ci(maj_b.astype(float) - maj_a.astype(float)),
        "mcnemar_p": stats.mcnemar_exact(only_a, only_b),
        "majority_only_a": only_a,
        "majority_only_b": only_b,
    }


def primary(counts: dict[str, dict[str, int]], n_samples: int) -> dict:
    """H1 and H2 with Holm per test, and each one's verdict (from the primary test)."""
    found = {name: contrast(counts, a, b, n_samples) for name, (a, b) in PRIMARY.items()}
    flips = stats.holm({name: c["sign_flip_p"] for name, c in found.items()})
    mcnemar = stats.holm({name: c["mcnemar_p"] for name, c in found.items()})
    for name, c in found.items():
        c["sign_flip_p_holm"], c["mcnemar_p_holm"] = flips[name], mcnemar[name]
        if c["sign_flip_p_holm"] < ALPHA:
            c["verdict"] = "detected"
        else:
            c["verdict"] = "inconclusive"
            c["no_difference_larger_than_pp"] = bound_pp(c["score_ci"])
    return found


def accuracy(counts: dict[str, dict[str, int]], condition: str, n_samples: int) -> dict:
    scores = np.array([counts[k][condition] / n_samples for k in sorted(counts)])
    majority = int(sum(2 * counts[k][condition] > n_samples for k in counts))
    low, high = stats.wilson(majority, len(counts))
    return {"mean_score": float(scores.mean()) if len(scores) else None,
            "mean_score_ci": bootstrap_ci(scores), "majority_right": majority,
            "problems": len(counts), "majority_wilson": [low, high]}  # fmt: skip


def analysis_row(counts: dict[str, dict[str, int]], conditions: list[str], n: int) -> dict:
    present = set(conditions)
    return {
        "problems": len(counts),
        "accuracy": {c: accuracy(counts, c, n) for c in conditions},
        "primary": primary(counts, n) if all(set(p) <= present for p in PRIMARY.values()) else {},
        "exploratory": {
            name: contrast(counts, a, b, n)
            for name, (a, b) in EXPLORATORY.items()
            if {a, b} <= present
        },  # fmt: skip
    }


# ---- 5b: the dispute trigger ------------------------------------------------------------


def disputes(
    grid: dict[str, dict[str, list[Item]]], problems: dict[str, followup.Problem]
) -> list[dict]:
    """Problems where at least TRIGGER_CONDITIONS conditions' majority answers agree with each
    other and differ from the key: the only problems whose keys are checked."""
    found = []
    for label, row in sorted(grid.items()):
        majorities = {c: majority_answer([answer_of(i) for i in cells]) for c, cells in row.items()}
        for answer in majorities.values():
            if answer is None:
                continue
            agreeing = sorted(c for c, m in majorities.items() if same_answer(answer, m))
            if len(agreeing) >= TRIGGER_CONDITIONS and not is_right(problems[label], answer):
                found.append({"problem": label, "answer": list(answer), "conditions": agreeing,
                              "key": key_of(problems[label])})  # fmt: skip
                break
    return found


# ---- also reported ----------------------------------------------------------------------


def sample_agreement(grid: dict[str, dict[str, list[Item]]], condition: str) -> float | None:
    """The share of sample pairs, within a problem, that give the same answer (mean over
    problems); None with one sample, since there are no pairs (JSON has no NaN)."""
    shares = []
    for row in grid.values():
        answers = [answer_of(i) for i in row[condition]]
        pairs = [(x, y) for k, x in enumerate(answers) for y in answers[k + 1 :]]
        if pairs:
            shares.append(sum(same_answer(x, y) for x, y in pairs) / len(pairs))
    return float(np.mean(shares)) if shares else None


def rounding_only(grid, problems, condition: str) -> dict:
    """Sample answers right only by section 4's rounding clause (a key written with
    decimals, rounded), not within 1e-4: how many, and on which problems."""
    found = [label for label, row in grid.items() for i in row[condition]
             if (a := answer_of(i)) is not None
             and followup.right_by(problems[label], a[0], a[1]) == "rounding"]  # fmt: skip
    return {"answers": len(found), "problems": sorted(set(found))}


def failures(grid, problems, condition: str) -> dict:
    """Wrong answers split into loud (no answer) and silent (an answer, wrong)."""
    loud = silent = 0
    for label, row in grid.items():
        for i in row[condition]:
            answer = answer_of(i)
            if answer is None:
                loud += 1
            elif not is_right(problems[label], answer):
                silent += 1
    return {"loud": loud, "silent": silent}


def revisions(grid, problems) -> dict:
    """Condition 4's revisions, per sample answer: how many were made, kept and discarded,
    and how the answer moved from the single-shot answer each started from."""
    out = {"answers": 0, "revised": 0, "kept": 0, "discarded": 0, "right_to_wrong": 0,
           "wrong_to_right": 0, "flags_by_kind": {}}  # fmt: skip
    for label, row in grid.items():
        for mine in row.get("checklist-revision", []):
            out["answers"] += 1
            for flag in mine.checklist_flags or []:
                out["flags_by_kind"][flag["kind"]] = out["flags_by_kind"].get(flag["kind"], 0) + 1
            if not mine.revised:
                continue
            out["revised"] += 1
            out["kept" if mine.revision_kept else "discarded"] += 1
            original = (mine.original_status, mine.original_objective)
            before = is_right(problems[label], original)
            after = is_right(problems[label], answer_of(mine))
            out["right_to_wrong"] += before and not after
            out["wrong_to_right"] += after and not before
    out["flags_by_kind"] = dict(sorted(out["flags_by_kind"].items()))
    return out


def drops(grid, problems) -> dict:
    """5a, exploratory: are answers whose model had a variable dropped wrong more often?"""
    table_ = {True: [0, 0], False: [0, 0]}  # dropped -> [right, wrong]
    for label, row in grid.items():
        for c in SOLVER_CONDITIONS:
            for i in row.get(c, []):
                right = is_right(problems[label], answer_of(i))
                table_[bool(i.dropped)][0 if right else 1] += 1
    with_drop, without = table_[True], table_[False]
    p = fisher_exact([with_drop, without])[1] if sum(with_drop) and sum(without) else None
    return {"with_drop": {"right": with_drop[0], "wrong": with_drop[1]},
            "without_drop": {"right": without[0], "wrong": without[1]},
            "fisher_p": None if p is None else float(p), "label": "exploratory"}  # fmt: skip


def spend(grid, condition: str) -> dict:
    cells = [i for row in grid.values() for i in row[condition]]
    latencies = [i.latency_s for i in cells]
    return {
        "latency_p50_s": float(np.percentile(latencies, 50)) if latencies else None,
        "latency_p95_s": float(np.percentile(latencies, 95)) if latencies else None,
        "cost_usd": sum(i.cost_usd for i in cells),
    }


# ---- the report -------------------------------------------------------------------------


def exposed_labels(split: dict | None = None) -> set[str]:
    """The problems seen before the split (5c), as labels."""
    seen = (split or followup.read_split())["seen_before_the_split"]
    return {f"{benchmark}:{pid}" for benchmark, ids in seen.items() for pid in ids}


def build(
    items: list[Item],
    conditions: list[str],
    samples: list[int],
    problems: dict[str, followup.Problem],
    exposed: set[str],
    corrected_keys: dict[str, float | str] | None = None,
    expected: list[str] | None = None,
    unscorable: list[str] = (),
) -> dict:
    """The whole report. `problems`: label -> Problem (the raw key). `corrected_keys`: label
    -> the key that replaces it, for overturned keys only (5b): an objective, or
    "infeasible"/"unbounded". `expected`: the manifest's problems as labels. `unscorable`:
    the labels left out before the run because their keys can't be parsed."""
    grid, incomplete = table(items, conditions, samples, expected)
    n = len(samples)
    counts = right_counts(grid, problems)
    unexposed = {k: v for k, v in counts.items() if k not in exposed}
    rows = {
        "primary (unexposed)": analysis_row(unexposed, conditions, n),
        "sensitivity (all)": analysis_row(counts, conditions, n),
    }
    if corrected_keys:
        fixed = dict(problems)
        for label, key in corrected_keys.items():
            status, value = followup.parse_key(key)
            if status is None:
                raise ValueError(f"corrected key for {label} isn't a key")
            fixed[label] = problems[label].model_copy(update={"answer": value,
                                                              "key_status": status})  # fmt: skip
        corrected = {k: v for k, v in right_counts(grid, fixed).items() if k not in exposed}
        rows["corrected keys (unexposed)"] = analysis_row(corrected, conditions, n)
    return {
        "conditions": conditions,
        "samples": samples,
        "complete_problems": len(grid),
        "incomplete_problems": incomplete,
        "unscorable_keys": {"n": len(unscorable), "problems": sorted(unscorable)},
        "exposed_left_out": sorted(set(grid) & exposed),
        "rows": rows,
        "disputes": disputes(grid, problems),
        "corrected_keys": dict(sorted((corrected_keys or {}).items())),
        "sample_agreement": {c: sample_agreement(grid, c) for c in conditions},
        "failures": {c: failures(grid, problems, c) for c in conditions},
        "right_only_by_rounding": {c: rounding_only(grid, problems, c) for c in conditions},
        "checklist_revision": revisions(grid, problems),
        "unused_variable_drops": drops(grid, problems),
        "spend": {c: spend(grid, c) for c in conditions},
        "settings": {
            "alpha": ALPHA,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "tolerance": followup.TOLERANCE,
            "trigger_conditions": TRIGGER_CONDITIONS,
        },  # fmt: skip
    }


def samples_of(manifest: dict) -> list[int]:
    settings = manifest["settings"]
    if "samples" in settings:
        return [int(s) for s in settings["samples"].split(",")]
    return [int(settings.get("sample", 0))]


def report_run(run_dir: Path) -> dict:
    """A follow-up run's report: dev, or the test run (whose problems load only on the
    follow-up's frozen inputs: FreezeError otherwise)."""
    manifest = json.loads((run_dir / "manifest.json").read_text())
    split = manifest["split"]
    every = {followup.label(split, p.id): p for p in followup_problems(split)}
    problems = {label: p for label, p in every.items() if p.scorable}
    unscorable = [label for label, p in every.items() if not p.scorable]
    expected = [followup.label(split, pid) for pid in manifest["problem_ids"]]
    items = latest_items(run_dir / "results.jsonl")
    return build(items, manifest["conditions"], samples_of(manifest), problems, exposed_labels(),
                 expected=expected, unscorable=unscorable)  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score a follow-up run: report.json.")
    parser.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    report = report_run(args.run)
    out = args.run / "followup_report.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n")
    row = report["rows"]["primary (unexposed)"]
    incomplete = len(report["incomplete_problems"])
    print(f"{report['complete_problems']} complete problems ({incomplete} incomplete); "
          f"primary row: {row['problems']}")  # fmt: skip
    for c, a in row["accuracy"].items():
        print(f"  {c}: mean score {a['mean_score']:.3f}, majority {a['majority_right']}/"
              f"{a['problems']}")  # fmt: skip
    for name, c in row["primary"].items():
        print(f"  {name} ({c['b']} - {c['a']}): {c['score_difference']:+.3f}, "
              f"Holm p {c['sign_flip_p_holm']:.3g}: {c['verdict']}")  # fmt: skip
    left_out = report["unscorable_keys"]
    print(f"left out for unparseable keys: {left_out['n']} {left_out['problems']}")
    print(f"disputes to check: {len(report['disputes'])}; wrote {out}")


if __name__ == "__main__":
    main()
