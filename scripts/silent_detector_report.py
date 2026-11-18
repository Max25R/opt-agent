"""The results section of docs/analysis/silent_detector.md, from the one run's record.

It reads docs/analysis/silent_detector.json (written once by scripts/silent_detector.py) and
never runs the detector. The breakdown by failure type joins that record with
docs/analysis/failure_types.csv; it's post hoc (decided after the run) and labeled so.

Run:  python scripts/silent_detector_report.py   # rewrites the doc's results section
"""

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs" / "analysis"
RESULTS, TYPES_CSV, DOC = (ANALYSIS / n for n in ("silent_detector.json", "failure_types.csv",
                                                  "silent_detector.md"))  # fmt: skip
BEGIN = "<!-- results: written by `python scripts/silent_detector_report.py` -->"
END = "<!-- end of results -->"
ROWS = [("all three conditions, pooled", "pooled"), ("single-shot", "single-shot"),
        ("self-correction", "self-correction"), ("checklist revision", "checklist-revision"),
        ("the 121 unexposed problems", "unexposed"),
        ("distinct models (one per problem and model)", "distinct_models")]  # fmt: skip


def pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def interval(rate: dict) -> str:
    low, high = rate["wilson95"]
    return f"{pct(rate['value'])} ({100 * low:.1f} to {100 * high:.1f})"


def table(result: dict) -> list[str]:
    lines = ["| | Answers | Silent failures | Flagged silent | Flagged right | "
             "Precision (95% CI) | Recall (95% CI) | Right answers flagged |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    for name, key in ROWS:
        c = result[key] if key in result else result["by_condition"][key]
        lines.append(f"| {name} | {c['answers']} | {c['silent_failures']} | "
                     f"{c['flagged_silent']} | {c['flagged_correct']} | "
                     f"{interval(c['precision'])} | {interval(c['recall'])} | "
                     f"{pct(c['false_flag_rate']['value'])} |")  # fmt: skip
    return lines


def by_failure_type(result: dict) -> list[str]:
    """Post hoc: each silent failure's primary type (failure_types.csv), flagged or not."""
    with TYPES_CSV.open() as f:
        types = {(r["problem"], r["condition"], int(r["sample"])): r["primary"]
                 for r in csv.DictReader(f) if r["run"] == "followup-test"}  # fmt: skip
    silent, flagged = Counter(), Counter()
    for r in result["rows"]:
        if not r["right"]:
            t = types[(r["problem"], r["condition"], r["sample"])]
            silent[t] += 1
            flagged[t] += r["flagged"]
    parts = [f"{t} {flagged[t]} of {n}" for t, n in silent.most_common()]
    errors = sum(n for t, n in silent.items() if t != "answer-key dispute")
    caught = sum(n for t, n in flagged.items() if t != "answer-key dispute")
    return [
        f"Flagged, of each type's silent failures: {'; '.join(parts)}. Of the silent failures "
        f"with a model error (not a dispute), it flags {caught} of {errors}."
    ]


def section(result: dict) -> str:
    p = result["pooled"]
    base = p["silent_failures"] / p["answers"]
    lines = [BEGIN, "", "## Results (the one run)", "",
             f"Run once, at `{result['commit'][:7]}` with no uncommitted changes "
             f"({result['ran_at']}), over {p['answers']} answers that reported one "
             f"({result['loud_left_out']} loud failures left out). Exploratory.", "",
             *table(result), "",
             f"**A weak detector.** {pct(base)} of these answers are silent failures, so a flag "
             f"picked at random would be right {pct(base)} of the time; this one's flags are "
             f"right {pct(p['precision']['value'])} of the time. It finds about half the silent "
             f"failures ({p['flagged_silent']} of {p['silent_failures']}) and flags "
             f"{pct(p['false_flag_rate']['value'])} of the right answers ({p['flagged_correct']} "
             f"of {p['correct']}), so as a warning it would mostly cry wolf: a right model "
             "needn't carry every number of the text as written (why each flagged right answer "
             "lacks its numbers wasn't checked). Nothing was tuned after the run.", "",
             "**Post hoc** (after the run, joining [`failure_types.csv`](failure_types.csv), "
             "whose types are Claude's labels, not verified by a person; not part of the "
             "declared report). " + " ".join(by_failure_type(result))
             + " It can't see an integrality error by design (no number is missing), and in an "
             "answer-key dispute Claude found no model error to see.", "", END]  # fmt: skip
    return "\n".join(lines)


def main() -> None:
    result = json.loads(RESULTS.read_text())
    text = DOC.read_text()
    if BEGIN in text:
        head, rest = text.split(BEGIN, 1)
        text = head + section(result) + rest.split(END, 1)[1]
    else:
        text = text.rstrip("\n") + "\n\n" + section(result) + "\n"
    DOC.write_text(text)
    print(f"{DOC.relative_to(ROOT)}: results section written")


if __name__ == "__main__":
    main()
