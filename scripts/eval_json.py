"""results/eval.json: every number the README reports, gathered from the frozen test runs.

Pre-registration section 7: every number in the README comes from this file, and
tests/test_readme_numbers.py checks that. It's built from:
- runs/test/report.json and runs/test-perturbed/report.json (opt_agent.report);
- the Amendment 3 row in runs/test/report.json (scripts/amendment3.py). The frozen report
  rebuild drops that row, so this script refuses to run without it;
- Amendment 4's rows (scripts/amendment4.py), computed here from the test run and its
  report rather than stored in the report, so a rebuild can't drop them;
- the runs' scored pairs, for self-correction's revisions and changed outcomes;
- the test run's taxonomy and blind-grading sheets, for the two judges' agreement and each
  blind grade;
- docs/FREEZE.json.

It makes no API calls and writes no timestamps, so the same inputs give the same bytes.

The top-level order is the reporting order: provenance, then the pre-registered primary
results, then everything else, each labeled with what it is.

Run:  python scripts/eval_json.py   # writes results/eval.json
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from opt_agent import blind_grading, taxonomy
from opt_agent.packets import graders
from opt_agent.run_results import ScoredRun, load
from opt_agent.stats import wilson

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str):
    """A sibling script as a module, whether this file runs as a script or is loaded by a
    test (scripts/ isn't a package)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


amendment4 = _script("amendment4")
TEST = ROOT / "runs" / "test"
PERTURBED = ROOT / "runs" / "test-perturbed"
FREEZE = ROOT / "docs" / "FREEZE.json"
OUT = ROOT / "results" / "eval.json"
SCHEMA_VERSION = 1
AMENDMENT_3 = "exploratory, post hoc (Amendment 3)"  # scripts/amendment3.py's KEY
CONFIDENCE = 0.95  # every interval is a 95% Wilson interval (stats.wilson)


def build(test_dir: Path = TEST, perturbed_dir: Path = PERTURBED, freeze: Path = FREEZE) -> dict:
    test_report = _report(test_dir)
    if AMENDMENT_3 not in test_report:
        raise ValueError(f"{test_dir / 'report.json'} has no Amendment 3 row (a frozen "
                         f"rebuild drops it): python scripts/amendment3.py {test_dir}")  # fmt: skip
    perturbed_report = _report(perturbed_dir)
    test, perturbed = load(test_dir), load(perturbed_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "model": test.manifest.model_id,
        "provenance": provenance(
            {test_dir: test_report, perturbed_dir: perturbed_report}, json.loads(freeze.read_text())
        ),
        "primary": primary(test_report),
        "perturbed": perturbed_results(perturbed_report),
        "sensitivity": sensitivity(test_report),
        "exploratory_amendment_3": test_report[AMENDMENT_3],
        "amendment_4": amendment4.row(test, test_report),
        "hand_checks": hand_checks(test_report, test),
        "self_correction": self_correction({"test": test, "test-perturbed": perturbed}),
        "cost_latency": cost_latency({"test": test_report, "test-perturbed": perturbed_report}),
    }


def _report(run_dir: Path) -> dict:
    report = json.loads((run_dir / "report.json").read_text())
    if not report["complete"]:
        raise ValueError(f"{run_dir / 'report.json'} is incomplete")
    return report


# ---- each section ---------------------------------------------------------------------


def provenance(reports: dict[Path, dict], freeze: dict) -> dict:
    """The commit, the freeze fingerprint, and the hashes of everything the numbers came
    from. Every pass of both runs must have run on the approved inputs."""
    runs = {}
    for run_dir, report in reports.items():
        p = report["provenance"]
        if not p["every pass on the approved inputs"]:
            raise ValueError(f"{run_dir.name}: not every pass ran on the approved inputs")
        runs[run_dir.name] = {
            "passes": len(p["passes"]),
            "git_sha": sorted({x["git_sha"] for x in p["passes"]}),
            "git_dirty": any(x["git_dirty"] for x in p["passes"]),
            "fingerprint_sha256": sorted({x["fingerprint"] for x in p["passes"]}),
            "every pass on the approved inputs": True,
            "packages": p["passes"][0]["packages"],
            "inputs_sha256": p["inputs_sha256"],
        }
    test_report = next(iter(reports.values()))  # the main run comes first
    first = test_report["provenance"]
    return {
        "freeze": {
            "approved_on": freeze["approved_on"],
            "approved_commit": freeze["commit"],
            "fingerprint_sha256": first["approved_fingerprint"],
        },
        "runs": runs,
        "reports_sha256": {
            f"runs/{d.name}/report.json": _sha256(d / "report.json") for d in reports
        },
        "hand_check_sheets_sha256": {
            **first["hand_check_sheets_sha256"],
            **test_report[AMENDMENT_3]["sheets_sha256"],
        },
        "prices": first["prices"],
        "tolerance": first["tolerance"],
        "sensitivity_tolerance": first["sensitivity_tolerance"],
        "alpha": first["alpha"],
        "confidence": CONFIDENCE,
    }


def primary(report: dict) -> dict:
    """The pre-registered results (sections 1, 3, 4, 5): strict accuracy for every subset,
    with lenient accuracy next to it (Amendment 2), the McNemar family, and failures."""
    conditions = report["conditions"]
    return {
        "label": "pre-registered (sections 1, 3, 4 and 5)",
        "n": report["subsets"]["all"],
        "accuracy": {c: v["accuracy"]["all"] for c, v in conditions.items()},
        "subsets": {
            name: {
                "n": n,
                "strict": {c: v["accuracy"][name] for c, v in conditions.items()},
                "lenient": {c: v["lenient accuracy"][name] for c, v in conditions.items()},
            }
            for name, n in report["subsets"].items()
        },
        "comparisons": report["comparisons"],
        "failures": {c: _failures(v["failures"]) for c, v in conditions.items()},
        "correct by reading": {c: v["correct by reading"] for c, v in conditions.items()},
        "flips at 1e-4": {c: v["flips at 1e-4"] for c, v in conditions.items()},
        "says LP: answered with the LP optimum": {
            c: v["says LP: answered with the LP optimum"] for c, v in conditions.items()
        },
        "is a status: claimed an optimum": {
            c: v["is a status: claimed an optimum"] for c, v in conditions.items()
        },
        "notes": report["notes"],
    }


def _failures(f: dict) -> dict:
    return {
        "silent": len(f["silent"]),
        "silent_ids": f["silent"],
        "loud": sum(f["loud"].values()),
        "loud by kind": f["loud"],
        "api errors after every pass": f["api errors after every pass"],
    }


def perturbed_results(report: dict) -> dict:
    conditions = report["conditions"]
    p = report["perturbed"]
    return {
        "label": "robustness check, no tests (pre-registration, condition 4)",
        "n": report["subsets"]["all"],
        "accuracy": {c: v["accuracy"]["all"] for c, v in conditions.items()},
        "failures": {c: _failures(v["failures"]) for c, v in conditions.items()},
        "gave the original answer": {
            c: len(ids) for c, ids in p["gave the original answer"].items()
        },
        "against the original run": p["against the original run"],
    }


def sensitivity(report: dict) -> dict:
    conditions = report["conditions"]
    return {
        "without disputed reviews": {
            "label": "sensitivity (Amendment 2, part 6)",
            "accuracy": {c: v["accuracy without disputed reviews"] for c, v in conditions.items()},
        },
        "second judge's labels alone": {
            "label": "sensitivity (Amendment 2)",
            "accuracy": report["second judge's labels alone"],
        },
        "comparisons, lenient": {
            "label": "exploratory (Amendment 2)",
            "rows": report["comparisons, lenient (exploratory)"],
        },
    }


def hand_checks(report: dict, run: ScoredRun) -> dict:
    """Section 5a, as the report gives it, plus what only this file adds: every blind grade
    by problem, the second judge's taxonomy counts, and the two judges' agreement."""
    blind = report["hand_checks"]["blind grading"]
    return {
        "label": "LLM judges, not a human check (Amendment 2)",
        "blind_grading": {**blind, "items": _blind_items(run)},
        "taxonomy": {
            **report["hand_checks"]["taxonomy"],
            **_second_judge(run),
        },
        "integrality_agreement": report["integrality_agreement"],
    }


def _blind_items(run: ScoredRun) -> list[dict]:
    """Every graded model, in the sheet's order, with its problem and its score."""
    by_key = {f.key: f for f in blind_grading.pool(run)}
    grades = blind_grading.read_grades(blind_grading.sheet_path(run.name))
    return [
        {"problem_id": by_key[k].problem_id, "key": k, "graded": grade, "note": note,
         "scored": "right" if by_key[k].scored_right else "wrong"}
        for k, (grade, note) in grades.items()
    ]  # fmt: skip


def _second_judge(run: ScoredRun) -> dict:
    """The second judge's taxonomy counts (Amendment 3 only; 5a's counts are the judge of
    record's), and how often the two judges chose the same category."""
    folder = taxonomy.sheet_path(run.name).parent
    second_sheet = folder / "second_judge.csv"
    judge = taxonomy.read_labels(taxonomy.sheet_path(run.name))
    second = taxonomy.read_labels(second_sheet)
    failures = taxonomy.failures(run)
    counts = {c: {} for c in run.manifest.conditions}
    for f in failures:
        for c in f.conditions:
            category = second.get(f.key, taxonomy.UNLABELED)
            counts[c][category] = counts[c].get(category, 0) + 1
    order = [*taxonomy.CATEGORIES, taxonomy.UNLABELED]
    same = sum(f.key in judge and judge[f.key] == second.get(f.key) for f in failures)
    return {
        "second judge": {
            "label": "Amendment 3 only",
            "graders": graders(second_sheet),
            "by condition": {c: {k: n[k] for k in order if k in n} for c, n in counts.items()},
        },
        "judges agree": {  # as integrality_agreement gives "judge vs second"
            "label": "exploratory (Amendment 3)",
            "same": same,
            "different": len(failures) - same,
            "n": len(failures),
            "wilson95": list(wilson(same, len(failures))),
        },
    }


def self_correction(runs: dict[str, ScoredRun]) -> dict:
    """Per run: how many self-correction answers took a revision, which outcomes differ
    from single-shot's, and its extra cost over single-shot (every call at its original
    token counts)."""
    out = {"label": "descriptive, no tests"}
    totals = {"revised": 0, "outcomes changed": 0, "cost": 0.0, "single-shot cost": 0.0}
    for name, run in runs.items():
        by_problem = {}
        for p in run.pairs:
            by_problem.setdefault(p.problem_id, {})[p.condition] = p
        changed = [
            {"problem_id": i, "single-shot": _verdict(d["single-shot"]),
             "self-correction": _verdict(d["self-correction"])}
            for i, d in by_problem.items()
            if d["single-shot"].score.correct != d["self-correction"].score.correct
        ]  # fmt: skip
        revised = sum(d["self-correction"].item.attempts > 1 for d in by_problem.values())
        cost = sum(d["self-correction"].item.cost_usd for d in by_problem.values())
        single = sum(d["single-shot"].item.cost_usd for d in by_problem.values())
        out[name] = {
            "revised": revised,
            "outcomes changed vs single-shot": changed,
            "extra cost vs single-shot": cost / single - 1,
        }
        totals["revised"] += revised
        totals["outcomes changed"] += len(changed)
        totals["cost"] += cost
        totals["single-shot cost"] += single
    out["both runs"] = {
        "revised": totals["revised"],
        "outcomes changed vs single-shot": totals["outcomes changed"],
        "extra cost vs single-shot": totals["cost"] / totals["single-shot cost"] - 1,
    }
    return out


def _verdict(pair) -> str:
    return "right" if pair.score.correct else "wrong"


def cost_latency(reports: dict[str, dict]) -> dict:
    out = {
        "label": (
            "cost_usd: every call an answer used, at its original token counts; paid_usd: "
            "what the run paid, from its spend ledger (cached replies cost nothing); "
            "latency_s: API plus solver time, without retries"
        ),  # fmt: skip
    }
    for name, report in reports.items():
        out[name] = {
            "paid_usd": report["paid_usd"],
            "conditions": {
                c: {k: v[k] for k in ("cost_usd", "tokens", "latency_s", "retry_s", "wall_s")}
                for c, v in report["conditions"].items()
            },
        }
    out["paid_usd_total"] = sum(r["paid_usd"] for r in reports.values())
    return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dumps(data: dict) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write results/eval.json from the test runs.")
    parser.add_argument("--out", type=Path, default=OUT, help=f"default: {OUT.relative_to(ROOT)}")
    args = parser.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(dumps(build()))
    print(f"Written to {args.out}")


if __name__ == "__main__":
    main()
