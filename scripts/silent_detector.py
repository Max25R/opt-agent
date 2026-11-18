"""Run the silent-failure detector once (docs/analysis/silent_detector.md) over the follow-up's
cached answers, and write docs/analysis/silent_detector.json.

Every answer of the three solver conditions is replayed in the followup-freeze tree, as in
scripts/failure_cases.py (a client that refuses every request; the answer must equal the
committed one), to get the model behind it. Then the detector (src/opt_agent/detector.py, at
HEAD) checks each answer's model against its problem's text. Nothing written holds problem
text: the rows give labels, verdicts and the missing numbers only.

It runs once: with docs/analysis/silent_detector.json there, it refuses, so the rule can't be
tuned on the results (the rule's doc says why).

Run:  python scripts/silent_detector.py   # once; no key, no API calls; a few minutes
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "analysis" / "silent_detector.json"
RUN = "runs/followup-test"
RUN_FILES = ("manifest.json", "results.jsonl", "attempts.jsonl", "spend.jsonl")
LLM4OR = "data/external/llm4or-clean"
CONDITIONS = ("single-shot", "self-correction", "checklist-revision")


def inside(out: Path) -> None:
    """In the tag's tree: every solver-condition answer, with its text and model."""
    sys.path.insert(0, str(Path(__file__).parent))
    import failure_cases  # noqa: I001 (copied in beside this script)
    from opt_agent import evaluate, followup, followup_report
    from opt_agent.api import Cache
    from opt_agent.runs import Run

    problems = {p.id: p for p in followup.load_test() if p.scorable}
    exposed = followup_report.exposed_labels()
    sessions: dict[int, Run] = {}
    with out.open("w") as f:
        for item in evaluate.latest_items(Path(RUN) / "results.jsonl"):
            if item.condition not in CONDITIONS or item.outcome != "done":
                continue
            p = problems[item.problem_id]
            answer = followup_report.answer_of(item)
            row = {"problem": item.problem_id, "condition": item.condition,
                   "sample": item.sample, "exposed": p.id in exposed,
                   "loud": answer is None}  # fmt: skip
            if answer is not None:
                if item.sample not in sessions:
                    cache = Cache(Path(RUN) / "cache", item.sample)
                    sessions[item.sample] = Run.start(cache=cache)
                _, found = failure_cases.replay(
                    item, p.document, sessions[item.sample],
                    checklist_revision=item.condition == "checklist-revision")  # fmt: skip
                row |= {"right": followup_report.is_right(p, answer), "text": p.document,
                        "model": found["model"]}  # fmt: skip
            f.write(json.dumps(row) + "\n")


def confusion(rows: list[dict]) -> dict:
    from opt_agent.stats import wilson

    silent = [r for r in rows if not r["right"]]
    correct = [r for r in rows if r["right"]]
    tp = sum(r["flagged"] for r in silent)
    fp = sum(r["flagged"] for r in correct)
    flagged = tp + fp

    def rate(k: int, n: int) -> dict:
        return {"value": k / n if n else None, "wilson95": list(wilson(k, n))}

    return {"answers": len(rows), "silent_failures": len(silent), "correct": len(correct),
            "flagged": flagged, "flagged_silent": tp, "flagged_correct": fp,
            "precision": rate(tp, flagged), "recall": rate(tp, len(silent)),
            "false_flag_rate": rate(fp, len(correct))}  # fmt: skip


def main() -> None:
    if OUT.exists():
        raise SystemExit(
            f"{OUT.relative_to(ROOT)} exists: the detector runs once, so its "
            "rule can't be tuned on the results (docs/analysis/silent_detector.md)"
        )
    sys.path.insert(0, str(ROOT / "src"))
    from opt_agent.detector import check
    from opt_agent.frozen import Tree
    from opt_agent.schema import LPModel

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True, check=True).stdout.strip()  # fmt: skip
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "scripts", "docs"],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout  # fmt: skip
    with tempfile.TemporaryDirectory() as tmp:
        tree = Tree.extract("followup-freeze", Path(tmp) / "tree")
        tree.copy(*(f"{RUN}/{name}" for name in RUN_FILES), f"{RUN}/cache", LLM4OR,
                  "scripts/failure_cases.py", "scripts/silent_detector.py")  # fmt: skip
        tree.python("scripts/silent_detector.py", "--inside", "answers.jsonl")
        answers = [json.loads(line) for line in tree.read("answers.jsonl").decode().splitlines()]
    rows = []
    for a in answers:
        if a["loud"]:
            continue
        verdict = check(a["text"], LPModel.model_validate(a["model"]))
        rows.append({
            "problem": a["problem"], "condition": a["condition"], "sample": a["sample"],
            "exposed": a["exposed"], "right": a["right"], "flagged": verdict.flagged,
            "constants": len(verdict.constants), "missing": [c.text for c in verdict.missing],
            "model": hashlib.sha256(json.dumps(a["model"], sort_keys=True).encode())
            .hexdigest()[:10],
        })  # fmt: skip
    models = {(r["problem"], r["model"]): r for r in rows}  # one verdict and truth per model
    result = {
        "label": "exploratory: the rule was committed before this one run "
                 "(docs/analysis/silent_detector.md); no tuning after it",
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit, "uncommitted_changes": bool(dirty),
        "loud_left_out": sum(a["loud"] for a in answers),
        "pooled": confusion(rows),
        "by_condition": {c: confusion([r for r in rows if r["condition"] == c])
                         for c in CONDITIONS},
        "unexposed": confusion([r for r in rows if not r["exposed"]]),
        "distinct_models": confusion(list(models.values())),
        "rows": rows,
    }  # fmt: skip
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    p = result["pooled"]
    print(
        f"{p['answers']} answers: {p['silent_failures']} silent failures, {p['correct']} right; "
        f"flagged {p['flagged_silent']} silent, {p['flagged_correct']} right; precision "
        f"{p['precision']['value']}, recall {p['recall']['value']} -> {OUT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inside", type=Path, help="(in the tag's tree) where to write answers")
    args = parser.parse_args()
    if args.inside:
        inside(args.inside)
    else:
        main()
