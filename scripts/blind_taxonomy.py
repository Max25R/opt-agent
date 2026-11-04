"""The blinded taxonomy prompt for both LLM judges (pre-registration, Amendment 3).

The frozen taxonomy prompt (opt_agent.taxonomy, LLM_PROMPT.md) shows each row's problem id
and condition names, and Claude's review reasons. Amendment 3 removes all three. This script
rebuilds the same rows from the frozen code, with those removed and nothing else changed or
added. The rows are shuffled with a recorded seed and numbered "Row 1" to "Row N". Only
blind_rows.csv, which the judges never see, maps a row back to its problem, its conditions
and its row in labels.csv.

A reply (row,category,note) is kept verbatim. --merge translates it back to labels.csv's
numbering and merges it with the frozen packets.merge_reply, which checks every key:
- the judge of record's reply goes into labels.csv, the pre-registered sheet (5a);
- the second judge's goes into second_judge.csv, which only Amendment 3's row reads.

Run:  python scripts/blind_taxonomy.py runs/test   # writes BLIND_PROMPT.md and blind_rows.csv
      python scripts/blind_taxonomy.py runs/test --merge judge|second --reply R.csv --grader G
"""

import argparse
import csv
import random
import tempfile
from pathlib import Path

from opt_agent import taxonomy
from opt_agent.agent import format_model
from opt_agent.ground_truth import Record, readings, reference_model
from opt_agent.packets import merge_reply
from opt_agent.run_results import ScoredRun, load

SEED = 20261104  # recorded so anyone can rebuild the same row order
PROMPT = "BLIND_PROMPT.md"
MAPPING = "blind_rows.csv"  # row -> problem: for merging and the report, never for a judge
SHEETS = {"judge": "labels.csv", "second": "second_judge.csv"}
HEADER = "row,category,note"  # a reply's first line


def shuffled(run: ScoredRun, seed: int = SEED) -> list[taxonomy.Failure]:
    """The frozen code's rows (taxonomy.failures), in an order that says nothing about the
    problem or the condition."""
    rows = taxonomy.failures(run)
    random.Random(seed).shuffle(rows)
    return rows


def prompt(run: ScoredRun, rows: list[taxonomy.Failure]) -> str:
    """The frozen LLM prompt's instructions, without the condition name, and a CSV reply
    keyed by row number."""
    lines = [
        "# Why is each answer wrong?",
        "",
        "You are labeling the failures of a system that turns optimization word problems into "
        f"linear or integer programs and solves them. Below are {len(rows)} answers it got "
        "wrong. Each shows the problem text, the system's answer, the answers accepted as "
        "right, the reference model (the dataset's annotation, with whole-number or "
        "fractional variables as the problem's label says), and the system's own model. "
        "Some answers were given directly, with no model.",
        "",
        "For each failure, choose exactly one category from the table: the one for its main "
        "error, the one whose fix alone would give an accepted answer, if there is one. "
        "Mention any other errors in the note. Judge against the problem text: the reference "
        "is usually right, but it can be wrong or be one of several readings.",
        "",
        # The header on a line of its own, without backticks: the merge reads the reply's
        # first line as its column names, so it must be exactly this.
        "Reply with CSV only, and nothing else in the reply. Make the first line exactly:",
        HEADER,
        "Then one line per row: its row number as given, a category name from the table, and "
        "a one-sentence note in double quotes.",
        "",
        *taxonomy._categories(),  # the pre-registered table, as the frozen prompt shows it
    ]
    for number, f in enumerate(rows, 1):
        lines += _row(number, f, run.by_id[f.problem_id], rows)
    return "\n".join(lines)


def _row(number: int, f: taxonomy.Failure, record: Record, rows: list) -> list[str]:
    """taxonomy._row(neutral=True), without the id, conditions, key and review."""
    accepted = "; ".join(f"{taxonomy._show(s.status.value, s.objective)} ({reading})"
                         for reading, s in readings(record))  # fmt: skip
    lines = [
        f"## Row {number}",
        "",
        f"> {record.document}",
        "",
        f"**Answered:** {taxonomy._show(f.status, f.objective)}  ",
        f"**Accepted:** {accepted}  ",
        f"**As annotated:** LP {taxonomy._show(record.lp.status.value, record.lp.objective)}, "
        f"IP {taxonomy._show(record.ip.status.value, record.ip.objective)}; label "
        f"{record.integrality.kind}",
        "",
    ]
    # Revision flags would show that the answer came from self-correction, so they're left
    # out (the test run's failures have none). A fact's "row N" is this prompt's numbering.
    if found := taxonomy.facts(f.model_copy(update={"flags": []}), record, rows):
        lines += [*(f"- {fact}" for fact in found), ""]
    lines += [
        "Reference (the annotation, with its label):",
        "```",
        *format_model(reference_model(record)),
        "```",
        "",
    ]
    if f.model is None:
        lines += ["No model: this answer was given directly.", ""]
    else:
        lines += ["The system's model:", "```", *format_model(f.model), "```", ""]
    return lines


def write(run_dir: Path, seed: int = SEED) -> tuple[Path, int]:
    run = load(run_dir)
    rows = shuffled(run, seed)
    numbers = {f.key: n for n, f in enumerate(taxonomy.failures(run), 1)}  # labels.csv's
    out = taxonomy.sheet_path(run.name).parent
    out.mkdir(parents=True, exist_ok=True)
    (out / PROMPT).write_text(prompt(run, rows))
    with (out / MAPPING).open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row", "number", "key", "problem_id", "conditions"])
        for row, failure in enumerate(rows, 1):
            writer.writerow([row, numbers[failure.key], failure.key, failure.problem_id,
                             " ".join(failure.conditions)])  # fmt: skip
    return out, len(rows)


def translate(reply: Path, mapping: Path) -> list[dict[str, str]]:
    """A judge's reply (row,category,note) in labels.csv's numbering, with each row's key,
    so merge_reply can check it. Refuses a reply without the header, one that skips, doubles
    or adds a row, and a category that isn't pre-registered."""
    with mapping.open(newline="") as f:
        by_row = {m["row"]: m for m in csv.DictReader(f)}
    with reply.open(newline="") as f:
        reader = csv.DictReader(f)
        if [name.strip() for name in reader.fieldnames or []] != HEADER.split(","):
            raise ValueError(f"{reply}: the first line must be exactly {HEADER}")
        answered = list(reader)
    given = [a["row"].strip() for a in answered]
    if sorted(given) != sorted(by_row):
        raise ValueError(f"{reply} answers rows {given}, not each of 1-{len(by_row)} once")
    out = []
    for a in answered:
        category = a["category"].strip().lower()
        if category not in taxonomy.CATEGORIES:
            raise ValueError(f"row {a['row']}: {category!r} isn't a category")
        m = by_row[a["row"].strip()]
        out.append({"number": m["number"], "key": m["key"], "category": category,
                    "note": (a.get("note") or "").strip()})  # fmt: skip
    return out


def merge(run_dir: Path, judge: str, reply: Path, grader: str) -> int:
    """Write a judge's reply into its sheet. The second judge's sheet starts as a blank copy
    of labels.csv's rows."""
    folder = taxonomy.sheet_path(load(run_dir).name).parent
    sheet = folder / SHEETS[judge]
    if not sheet.exists():
        taxonomy.label_sheet(taxonomy.failures(load(run_dir)), sheet)
    rows = translate(reply, folder / MAPPING)
    with tempfile.TemporaryDirectory() as tmp:
        translated = Path(tmp) / "translated.csv"
        with translated.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["number", "key", "category", "note"])
            writer.writeheader()
            writer.writerows(rows)
        return merge_reply(sheet, translated, ["category", "note"], grader)


def main() -> None:
    parser = argparse.ArgumentParser(description="The blinded taxonomy prompt (Amendment 3).")
    parser.add_argument("run_dir", type=Path, help="a directory evaluate.py wrote")
    parser.add_argument("--merge", choices=list(SHEETS), help="merge a judge's reply")
    parser.add_argument("--reply", type=Path, help="with --merge: the reply, kept verbatim")
    parser.add_argument("--grader", help="with --merge: the judge's model and version")
    args = parser.parse_args()
    if args.merge:
        if not (args.reply and args.grader):
            parser.error("--merge needs --reply and --grader")
        n = merge(args.run_dir, args.merge, args.reply, args.grader)
        print(f"merged {n} labels from {args.reply} into {SHEETS[args.merge]}")
        return
    out, n = write(args.run_dir)
    print(f"wrote {out}/{PROMPT} and {MAPPING} ({n} rows, seed {SEED})")


if __name__ == "__main__":
    main()
