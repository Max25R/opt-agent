"""Score a run against the ground truth and summarize it as pre-registered.

Input is one run directory (evaluate.py): manifest.json (the denominator), results.jsonl
(every pass's lines), attempts.jsonl (each pass's git commit and package versions) and
spend.jsonl (what was paid). Output is one JSON document, the same for the same inputs, so
a test can check every number the README quotes against it.

Every answer is scored here, from the status and objective the run recorded
(scoring.py). The table evaluate.py prints is a convenience; this is the result.

Each (problem, condition) pair in the manifest is, following Amendment 1:
- **scored**: done in some pass, or errored in the first pass and in each of the
  RESUME_PASSES after it. The second counts as wrong (loud, "api error") and is listed
  separately.
- **open**: errored in fewer passes, or pending (no line yet). A report with any open pair
  is marked incomplete: its numbers are provisional, and the test run isn't over.

What's reported, by section of docs/PREREGISTRATION.md: accuracy with 95% Wilson intervals
per condition and subset (4, 5), lenient accuracy on the integrality-sensitive subset (3f),
which reading each correct answer needed (3c, 3e), answers that would flip at a 1e-4
tolerance (1), LP optima on "says LP" problems (3d), optima claimed for problems that have
none, with revision flags (3a), silent and loud failures (3g), McNemar's exact test with
Holm's correction (4), latency, retry and wall time, tokens, and cost (4), and re-runs
(Amendment 1).
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel

from opt_agent import packets
from opt_agent.evaluate import CONDITIONS, Item, Manifest
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    REVIEWS_PATH,
    TOLERANCE,
    Record,
    answer,
    integrality_matters,
    load_records,
    same_value,
    says_lp,
)
from opt_agent.pricing import PRICES, PRICES_CHECKED, PRICING_URL
from opt_agent.scoring import Score, score
from opt_agent.solver import Status
from opt_agent.stats import holm, mcnemar_exact, wilson

RESUME_PASSES = 3  # Amendment 1: after the first pass and 3 resumes, an error counts as wrong
SENSITIVITY_TOLERANCE = 1e-4  # section 1
ALPHA = 0.05  # family-wise, over the McNemar tests (section 4)
COMPARISONS = [("single-shot", "self-correction"), ("baseline", "single-shot"),
               ("baseline", "self-correction")]  # fmt: skip
COMPARISON_SUBSETS = ["has an optimum", "is a status"]


class Pair(BaseModel):
    problem_id: str
    condition: str
    state: Literal["scored", "errored", "pending"]  # errored and pending are open
    item: Item | None = None  # the done line, else the last errored one
    errored_passes: int = 0  # a pass writes at most one line per pair
    score: Score | None = None  # scored pairs only
    retry_s: float = 0.0  # over every pass, errored ones included
    wall_s: float = 0.0  # likewise

    @property
    def no_answer(self) -> str | None:
        if self.state != "scored" or self.score.correct or self.score.failure != "loud":
            return None
        return self.item.no_answer if self.item.outcome == "done" else "api error"


def build(run_dir: Path) -> dict:
    """The whole report for one run directory."""
    manifest = Manifest.model_validate_json((run_dir / "manifest.json").read_text())
    by_id = {r.id: r for r in load_records(GROUND_TRUTH_DIR / f"{manifest.split}.json")}
    records = [by_id[i] for i in manifest.problem_ids]
    pairs = load_pairs(manifest, run_dir / "results.jsonl", by_id)
    groups = subsets(records)
    open_pairs = [p for p in pairs if p.state != "scored"]
    report = {
        "complete": not open_pairs,
        "open": {
            "errored": sum(p.state == "errored" for p in pairs),
            "pending": sum(p.state == "pending" for p in pairs),
        },  # fmt: skip
        "subsets": {name: len(ids) for name, ids in groups.items()},
        "conditions": {
            c: condition_summary([p for p in pairs if p.condition == c], by_id, groups)
            for c in manifest.conditions
        },
        "comparisons": comparisons(pairs, groups, manifest.conditions),
        "paid_usd": _ledger_usd(run_dir / "spend.jsonl"),
        "provenance": provenance(run_dir, manifest),
    }
    if manifest.split == "test":
        report["integrality_agreement"] = integrality_agreement(list(by_id.values()))
    return report


def load_pairs(manifest: Manifest, results: Path, by_id: dict[str, Record]) -> list[Pair]:
    lines: dict[tuple[str, str], list[Item]] = {}
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            item = Item.model_validate(entry)
            lines.setdefault((item.problem_id, item.condition), []).append(item)
    pairs = []
    for problem_id in manifest.problem_ids:
        for condition in manifest.conditions:
            items = lines.get((problem_id, condition), [])
            done = [i for i in items if i.outcome == "done"]
            errored = [i for i in items if i.outcome == "errored"]
            pair = Pair(problem_id=problem_id, condition=condition, state="pending",
                        errored_passes=len(errored), retry_s=sum(i.retry_s for i in items),
                        wall_s=sum(i.wall_s for i in items))  # fmt: skip
            if done:
                record = by_id[problem_id]
                item = done[-1]
                pair = pair.model_copy(update={"state": "scored", "item": item,
                                               "score": score(record, item.status,
                                                              item.objective)})  # fmt: skip
            elif len(errored) >= 1 + RESUME_PASSES:
                pair = pair.model_copy(update={"state": "scored", "item": errored[-1],
                                               "score": Score(correct=False,
                                                              failure="loud")})  # fmt: skip
            elif errored:
                pair = pair.model_copy(update={"state": "errored", "item": errored[-1]})
            pairs.append(pair)
    return pairs


def subsets(records: list[Record]) -> dict[str, list[str]]:
    """The rows every table gives (section 5), as problem ids."""

    def verdict(r: Record, v: str) -> bool:
        return r.review is not None and r.review.verdict == v

    optimal = {r.id for r in records if answer(r).status is Status.OPTIMAL}
    return {
        "all": [r.id for r in records],
        "has an optimum": [r.id for r in records if r.id in optimal],
        "is a status": [r.id for r in records if r.id not in optimal],
        "integrality-insensitive": [r.id for r in records if not integrality_matters(r)],
        "integrality-sensitive": [r.id for r in records if integrality_matters(r)],
        "do-nothing": [r.id for r in records if verdict(r, "degenerate-text")],
        "strict wording": [r.id for r in records if r.strict is not None],
        "ambiguous": [r.id for r in records if verdict(r, "ambiguous-text")],
        "says LP, labeled integer": [r.id for r in records if says_lp(r)],
    }


def condition_summary(
    pairs: list[Pair], by_id: dict[str, Record], groups: dict[str, list[str]]
) -> dict:
    scored = {p.problem_id: p for p in pairs if p.state == "scored"}
    done = [p for p in scored.values() if p.item.outcome == "done"]

    def accuracy(ids: list[str], lenient: bool = False) -> dict:
        mine = [scored[i] for i in ids if i in scored]
        if lenient:
            right = sum(_rescore(p, by_id, lenient=True).correct for p in mine)
        else:
            right = sum(p.score.correct for p in mine)
        return rate(right, len(mine))

    sensitivity = Counter()
    for p in done:
        loose = _rescore(p, by_id, tolerance=SENSITIVITY_TOLERANCE).correct
        if loose != p.score.correct:
            sensitivity["wrong to right" if loose else "right to wrong"] += 1

    claimed = [p for p in done if p.problem_id in groups["is a status"]
               and p.item.status == Status.OPTIMAL]  # fmt: skip
    wrong = [p for p in scored.values() if not p.score.correct]
    rerun = [p for p in scored.values() if p.item.outcome == "done" and p.errored_passes]
    latency = [p.item.latency_s for p in done]
    return {
        "accuracy": {name: accuracy(ids) for name, ids in groups.items()},
        "lenient accuracy, integrality-sensitive": accuracy(
            groups["integrality-sensitive"], lenient=True
        ),
        "correct by reading": dict(
            Counter(p.score.reading for p in scored.values() if p.score.correct)
        ),  # fmt: skip
        "flips at 1e-4": {
            "wrong to right": sensitivity["wrong to right"],
            "right to wrong": sensitivity["right to wrong"],
        },  # fmt: skip
        "says LP: answered with the LP optimum": sum(
            p.item.status == Status.OPTIMAL
            and same_value(p.item.objective, by_id[p.problem_id].lp.objective)
            for p in done
            if p.problem_id in groups["says LP, labeled integer"]
        ),
        "is a status: claimed an optimum": {
            "problems": len(claimed),
            "with revision flags": sum(bool(p.item.flags) for p in claimed),
        },
        "failures": {
            "silent": sorted(p.problem_id for p in wrong if p.score.failure == "silent"),
            "loud": dict(Counter(p.no_answer for p in wrong if p.score.failure == "loud")),
            "api errors after every pass": sorted(
                p.problem_id for p in wrong if p.no_answer == "api error"
            ),
        },
        "re-runs": {
            "pairs": len(rerun),
            "by passes needed": dict(Counter(str(p.errored_passes + 1) for p in rerun)),
        },
        "latency_s": percentiles(latency),
        "retry_s": sum(p.retry_s for p in pairs),
        "wall_s": sum(p.wall_s for p in pairs),
        "tokens": {
            "input": sum(p.item.input_tokens for p in scored.values()),
            "output": sum(p.item.output_tokens for p in scored.values()),
        },  # fmt: skip
        "cost_usd": sum(p.item.cost_usd for p in scored.values()),
    }


def _rescore(pair: Pair, by_id: dict[str, Record], **how) -> Score:
    if pair.item.outcome != "done":
        return pair.score  # an API error is wrong under any tolerance
    return score(by_id[pair.problem_id], pair.item.status, pair.item.objective, **how)


def rate(right: int, n: int) -> dict:
    low, high = wilson(right, n)
    return {"right": right, "n": n, "accuracy": right / n if n else None, "wilson95": [low, high]}


def percentiles(values: list[float]) -> dict:
    """p50 and p95, by linear interpolation between order statistics (numpy's default)."""
    if not values:
        return {"n": 0, "p50": None, "p95": None}
    p50, p95 = np.percentile(values, [50, 95])
    return {"n": len(values), "p50": float(p50), "p95": float(p95)}


def comparisons(
    pairs: list[Pair], groups: dict[str, list[str]], conditions: list[str]
) -> list[dict]:
    """McNemar's exact test for each pre-registered pair of conditions, on each kind of
    answer, using only the problems both have scored. Holm's correction over all of them."""
    right = {(p.problem_id, p.condition): p.score.correct for p in pairs if p.state == "scored"}
    rows = []
    for a, b in COMPARISONS:
        if a not in conditions or b not in conditions:
            continue
        for subset in COMPARISON_SUBSETS:
            both = [i for i in groups[subset] if (i, a) in right and (i, b) in right]
            outcomes = Counter((right[(i, a)], right[(i, b)]) for i in both)
            only_a, only_b = outcomes[(True, False)], outcomes[(False, True)]
            rows.append({"a": a, "b": b, "subset": subset, "n": len(both),
                         "both right": outcomes[(True, True)],
                         "both wrong": outcomes[(False, False)],
                         "only a right": only_a, "only b right": only_b,
                         "p": mcnemar_exact(only_a, only_b)})  # fmt: skip
    adjusted = holm({_key(r): r["p"] for r in rows})
    for r in rows:
        r["p_holm"] = adjusted[_key(r)]
        r["significant"] = r["p_holm"] < ALPHA
    return rows


def _key(row: dict) -> str:
    return f"{row['a']} vs {row['b']}, {row['subset']}"


def integrality_agreement(records: list[Record]) -> dict:
    """The owner's blind labels against Claude's (section 3f), once labels.csv is filled."""
    try:
        owner = packets.read_labels(packets.BLIND_DIR / "labels.csv")
    except ValueError as unfilled:
        return {"pending": f"labels.csv isn't filled in yet ({unfilled})"}
    return packets.agreement(owner, records).model_dump(mode="json")


def provenance(run_dir: Path, manifest: Manifest) -> dict:
    passes = []
    log = run_dir / "attempts.jsonl"
    for line in log.read_text().splitlines() if log.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "run":
            passes.append({k: entry.get(k) for k in
                           ("run_id", "time", "git_sha", "git_dirty", "packages")})  # fmt: skip
    return {
        "manifest": manifest.model_dump(mode="json"),
        "passes": passes,
        "inputs_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (GROUND_TRUTH_DIR / f"{manifest.split}.json", REVIEWS_PATH)
        },
        "tolerance": TOLERANCE,
        "sensitivity_tolerance": SENSITIVITY_TOLERANCE,
        "resume_passes": RESUME_PASSES,
        "alpha": ALPHA,
        "prices": {
            "checked": PRICES_CHECKED,
            "url": PRICING_URL,
            manifest.model_id: PRICES[manifest.model_id][0].model_dump(),
        },  # fmt: skip
    }


def _ledger_usd(path: Path) -> float:
    lines = path.read_text().splitlines() if path.exists() else []
    return sum(json.loads(line)["cost_usd"] for line in lines)


# ---- reading it -------------------------------------------------------------------------


def render(report: dict) -> str:
    conditions = [c for c in CONDITIONS if c in report["conditions"]]
    state = "complete" if report["complete"] else (
        f"INCOMPLETE: {report['open']['errored']} errored and {report['open']['pending']} "
        "pending pairs; every number below is provisional"
    )  # fmt: skip
    lines = [f"Run report ({state})", "", "| subset | n | " + " | ".join(conditions) + " |",
             "|---|---|" + "---|" * len(conditions)]  # fmt: skip
    for subset, n in report["subsets"].items():
        cells = [_show_rate(report["conditions"][c]["accuracy"][subset]) for c in conditions]
        lines.append(f"| {subset} | {n} | " + " | ".join(cells) + " |")
    lenient = [_show_rate(report["conditions"][c]["lenient accuracy, integrality-sensitive"])
               for c in conditions]  # fmt: skip
    lines.append("| sensitive, lenient | | " + " | ".join(lenient) + " |")
    lines.append("")
    for c in conditions:
        s = report["conditions"][c]
        f = s["failures"]
        latency = s["latency_s"]
        lines.append(
            f"{c}: silent failures {len(f['silent'])} {f['silent']}; loud {f['loud'] or 0}; "
            f"latency p50 {_seconds(latency['p50'])}, p95 {_seconds(latency['p95'])}; "
            f"cost ${s['cost_usd']:.4f}"
        )
    if report["comparisons"]:
        lines += [
            "",
            "| comparison | n | only a | only b | p | Holm p |",
            "|---|---|---|---|---|---|",
        ]
        for r in report["comparisons"]:
            lines.append(f"| {_key(r)} | {r['n']} | {r['only a right']} | "
                         f"{r['only b right']} | {r['p']:.3g} | {r['p_holm']:.3g} |")  # fmt: skip
    lines += ["", f"Paid in this run directory: ${report['paid_usd']:.4f}"]
    return "\n".join(lines)


def _show_rate(r: dict) -> str:
    if not r["n"]:
        return "-"
    low, high = r["wilson95"]
    return f"{r['right']}/{r['n']} ({r['accuracy']:.0%}; {low:.0%}-{high:.0%})"


def _seconds(x: float | None) -> str:
    return "-" if x is None else f"{x:.1f} s"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score a run and summarize it.")
    parser.add_argument("run_dir", type=Path, help="a directory evaluate.py wrote")
    parser.add_argument("--out", type=Path, help="where to write the JSON (default: in run_dir)")
    args = parser.parse_args(argv)
    report = build(args.run_dir)
    out = args.out or args.run_dir / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(render(report))
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
