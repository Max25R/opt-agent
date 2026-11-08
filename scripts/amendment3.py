"""Amendment 3's exploratory row, added to a test run's report.json.

The row: all scorable problems, with the shared failures that both judges call answer-key
errors counted as correct. A condition's failure on a covered problem (COVERED, fixed by
the amendment before any judge labeled the taxonomy) counts as correct only if both judges
gave `reference` to the taxonomy row that holds that condition's answer. Anything else
(another category from either judge, or a missing label) leaves it wrong. No score, answer
key or ground truth changes: this only recounts.

It's post hoc and exploratory, outside the Holm family, with no tests.

The row lives in report.json because that's where the primary numbers are. The frozen
`opt_agent.report` rewrites report.json without it, so after a rebuild run this again.

Run:  python scripts/amendment3.py runs/test
"""

import argparse
import hashlib
import json
from pathlib import Path

from opt_agent import taxonomy
from opt_agent.packets import graders
from opt_agent.report import rate
from opt_agent.run_results import ScoredRun, load

# The 8 problems wrong in all three conditions of runs/test (Amendment 3, part 1).
COVERED = ("431521997", "1605420061", "-1540907330", "2078392466",
           "-926961422", "-2138755435", "1344881875", "181608358")  # fmt: skip
SHEETS = {"judge": "labels.csv", "second": "second_judge.csv"}
REFERENCE = "reference"
KEY = "exploratory, post hoc (Amendment 3)"
RULE = ("all scorable, with the shared failures both judges call answer-key errors counted "
        "as correct: a condition's failure on a covered problem counts as correct only if "
        "both judges labeled that condition's taxonomy row `reference`")  # fmt: skip


def counted_as_correct(
    failures: list[taxonomy.Failure],
    labels: dict[str, dict[str, str]],
    covered: tuple[str, ...] = COVERED,
) -> dict[str, list[str]]:
    """Condition -> the covered problems whose failure counts as correct. `labels` maps
    each judge to its sheet (row key -> category); both must say `reference`."""
    flipped: dict[str, set[str]] = {}
    for f in failures:
        if f.problem_id not in covered:
            continue
        if all(sheet.get(f.key) == REFERENCE for sheet in labels.values()):
            for condition in f.conditions:
                flipped.setdefault(condition, set()).add(f.problem_id)
    return {c: sorted(ids) for c, ids in flipped.items()}


def row(run: ScoredRun) -> dict:
    """The exploratory row for every condition, next to the primary strict accuracy."""
    folder = taxonomy.sheet_path(run.name).parent
    sheets = {judge: folder / name for judge, name in SHEETS.items()}
    labels = {judge: taxonomy.read_labels(path) for judge, path in sheets.items()}
    failures = taxonomy.failures(run)
    unlabeled = [f.key for f in failures if any(f.key not in s for s in labels.values())]
    if unlabeled:
        raise ValueError(f"taxonomy rows not labeled by both judges: {unlabeled}")
    _check_covered(run)
    flipped = counted_as_correct(failures, labels)
    by_condition = {}
    for c in run.manifest.conditions:
        scored = [p for p in run.pairs if p.condition == c and p.state == "scored"]
        right = sum(p.score.correct for p in scored)
        extra = flipped.get(c, [])
        by_condition[c] = {
            "primary": rate(right, len(scored)),
            "exploratory": rate(right + len(extra), len(scored)),
            "counted as correct": extra,
            "still wrong": [i for i in COVERED if i not in extra],
        }
    return {
        "label": "exploratory, post hoc; outside the Holm family, no tests (Amendment 3)",
        "rule": RULE,
        "covered": list(COVERED),
        "graders": {judge: graders(path) for judge, path in sheets.items()},
        "by condition": by_condition,
        "sheets_sha256": {
            str(path.relative_to(folder.parents[1])): _sha256(path) for path in sheets.values()
        },
    }


def _check_covered(run: ScoredRun) -> None:
    """The covered problems are the run's shared failures: wrong in every condition."""
    for problem in COVERED:
        pairs = [p for p in run.pairs if p.problem_id == problem]
        if len(pairs) != len(run.manifest.conditions) or any(p.score.correct for p in pairs):
            raise ValueError(f"{problem} isn't wrong in every condition of {run.name}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_to_report(run_dir: Path) -> dict:
    """Put the row into report.json, right after the primary numbers ("conditions"). The
    report must be complete and its primary counts must match the run's, so a stale
    report.json is refused rather than mixed with fresh numbers."""
    run = load(run_dir)
    path = run_dir / "report.json"
    report = json.loads(path.read_text())
    if not report["complete"]:
        raise ValueError(f"{path} is incomplete")
    new = row(run)
    for c, r in new["by condition"].items():
        if r["primary"] != report["conditions"][c]["accuracy"]["all"]:
            raise ValueError(f"{path}: {c}'s primary accuracy doesn't match the run; rebuild it")
    rebuilt = {}
    for key, value in report.items():
        if key == KEY:
            continue
        rebuilt[key] = value
        if key == "conditions":
            rebuilt[KEY] = new
    path.write_text(json.dumps(rebuilt, indent=1) + "\n")
    return new


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Add Amendment 3's exploratory row.")
    parser.add_argument("run_dir", type=Path, help="the test run, e.g. runs/test")
    args = parser.parse_args(argv)
    new = add_to_report(args.run_dir)
    for c, r in new["by condition"].items():
        p, e = r["primary"], r["exploratory"]
        print(f"{c}: primary {p['right']}/{p['n']}, exploratory {e['right']}/{e['n']} "
              f"({len(r['counted as correct'])} counted as correct)")  # fmt: skip
    print(f"Written to {args.run_dir / 'report.json'}")


if __name__ == "__main__":
    main()
