"""The hand-labeled error taxonomy: why each wrong answer is wrong (pre-registration 5a).

The score says *that* an answer is wrong; only a person can say *why*. Every distinct silent
failure in a run (a wrong confirmed answer, or a wrong parsed baseline answer) is one row in
a packet: the text, the answer and the accepted ones, the reference model, Claude's model
(the baseline has none), and facts the scores give for free, such as whether the answer
would pass with integrality not graded. The owner gives each row one category from
CATEGORIES, for its main error, in labels.csv, and the report counts them per condition.
Loud failures already have a kind (evaluate.NoAnswer), so they aren't labeled again.

A row is one distinct failure: single-shot and self-correction share a row when they gave
the same model, as they do when self-correction didn't revise. Rows are keyed by the problem
and the model (or the baseline's answer; run_results.model_key), so a regenerated packet
keeps every label already written.

The categories were drawn up from the dev failures (docs/FAILURE_LOG.md and the step 4
runs) and are pre-registered for the test run: a failure that fits none is "other", with a
note, not a new category.

An LLM judge gets LLM_PROMPT.md instead (Amendment 2): the same rows, without naming the
system or who wrote the labels, and a reply format that --merge writes into labels.csv.

Run:  python -m opt_agent.taxonomy runs/NAME    # writes review/taxonomy/NAME/
      python -m opt_agent.taxonomy runs/NAME --merge REPLY.csv --grader "MODEL, LLM judge"
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from opt_agent.agent import format_model
from opt_agent.ground_truth import (
    SENSITIVITY_TOLERANCE,
    Record,
    readings,
    reference_model,
    same_value,
)
from opt_agent.packets import REVIEW_DIR, graders, kept_marks, merge_reply
from opt_agent.run_results import ScoredRun, answer_key, final_models, load, model_key, model_of
from opt_agent.schema import LPModel
from opt_agent.scoring import score

TAXONOMY_DIR = REVIEW_DIR / "taxonomy"
CATEGORIES = {
    # The model, or the baseline's answer, doesn't say what the text says.
    "objective": "optimizes the wrong quantity, or in the wrong direction",
    "constraint-scope": "a limit applied to the wrong set of things: one combined limit read "
    "as one per item, or the reverse",
    "missing-constraint": "leaves out a requirement the text states (also when a revision "
    "deleted it)",
    "invented-constraint": "adds a requirement the text doesn't state",
    "coefficient": "a wrong number: misread, attached to the wrong variable, or converted "
    "between units wrongly",
    "direction": "a constraint points the wrong way (at least vs at most), and no accepted "
    "reading allows it",
    "integrality": "whole numbers vs fractions differ from the label",
    # The baseline only: it has no model to inspect.
    "rounding": "the right answer, rounded too far to match at 1e-6",
    "calculation": "no misreading found that gives this answer: a slip in the arithmetic or "
    "in finding the best choice",
    # The reference, not Claude.
    "reference": "the system's reading is one the text supports but no accepted reading "
    "allows, or the reference is wrong",
    "other": "none of these; say what in the note",
}
UNLABELED = "unlabeled"
MARKS = ["category", "note", "grader"]  # the labeler's columns; `grader` names who filled them


class Failure(BaseModel):
    key: str
    problem_id: str
    conditions: list[str]
    status: str  # the wrong answer
    objective: float | None
    model: LPModel | None  # Claude's; None for the baseline, which gives only an answer
    flags: list[str] = []  # revisions that deleted or loosened something (changes.py)


def failures(run: ScoredRun) -> list[Failure]:
    """Every distinct silent failure, in the manifest's order."""
    models = final_models(run.directory)
    found: dict[str, Failure] = {}
    for p in run.pairs:
        if p.state != "scored" or p.score.failure != "silent":
            continue
        model = None if p.condition == "baseline" else model_of(p, models)
        key = (answer_key(p.problem_id, p.item.status, p.item.objective) if model is None
               else model_key(p.problem_id, model))  # fmt: skip
        if key in found:
            found[key].conditions.append(p.condition)
            found[key].flags += [f for f in p.item.flags if f not in found[key].flags]
            continue
        found[key] = Failure(key=key, problem_id=p.problem_id, conditions=[p.condition],
                             status=p.item.status, objective=p.item.objective, model=model,
                             flags=list(p.item.flags))  # fmt: skip
    return list(found.values())


def facts(failure: Failure, record: Record, rows: list[Failure]) -> list[str]:
    """What the scores say about a failure without anyone's judgment."""
    found = []
    if score(record, failure.status, failure.objective, lenient=True).correct:
        found.append("Correct if integrality weren't graded (the lenient score, 3f).")
    if score(record, failure.status, failure.objective, tolerance=SENSITIVITY_TOLERANCE).correct:
        found.append(f"Within {SENSITIVITY_TOLERANCE:g} of an accepted answer.")
    if failure.flags:
        found.append(f"Revision flags: {'; '.join(failure.flags)}.")
    if failure.model is None:  # the baseline: a model with the same answer may show its reading
        for number, other in enumerate(rows, 1):
            if (
                other.problem_id == failure.problem_id
                and other.model is not None
                and _same((other.status, other.objective), (failure.status, failure.objective))
            ):
                found.append(f"The same answer as row {number}'s model.")
    return found


def _same(a: tuple[str, float | None], b: tuple[str, float | None]) -> bool:
    if a[0] != b[0]:
        return False
    return a[0] != "optimal" or same_value(a[1], b[1])


# ---- the packet and its sheet ---------------------------------------------------------


def packet(run: ScoredRun, rows: list[Failure]) -> str:
    lines = [
        f"# Error taxonomy: `{run.name}`",
        "",
        f"The {len(rows)} distinct silent failures in `{run.directory}` (the "
        f"{run.manifest.split} split): answers that were confirmed (or, for the baseline, "
        "parsed) but are wrong. For each, write one category in the `category` column of "
        "`labels.csv`, for its main error: the one whose fix alone would give an accepted "
        "answer, if there is one. Any other errors go in `note`. Then run "
        f"`python -m opt_agent.report {run.directory}`.",
        "",
        "**If this run has a blind-grading packet (`review/blind_grading/`), grade it "
        "first**: this one shows which answers are wrong.",
        "",
        *_categories(),
    ]
    for number, f in enumerate(rows, 1):
        lines += _row(number, f, run.by_id[f.problem_id], rows)
    return "\n".join(lines)


def llm_packet(run: ScoredRun, rows: list[Failure]) -> str:
    """The same failures as a prompt for an LLM judge in a fresh conversation (Amendment 2).
    It doesn't name the system or who wrote the labels, and asks for a CSV reply that
    merges into labels.csv (packets.merge_reply)."""
    lines = [
        "# Why is each answer wrong?",
        "",
        "You are labeling the failures of a system that turns optimization word problems into "
        f"linear or integer programs and solves them. Below are {len(rows)} problems it "
        "answered wrongly. Each shows the problem text, the system's answer, the answers "
        "accepted as right, the reference model (the dataset's annotation, with whole-number "
        "or fractional variables as the problem's label says), and the system's own model. "
        "Rows marked `baseline` are answers the system gave directly, with no model.",
        "",
        "For each failure, choose exactly one category from the table: the one for its main "
        "error, the one whose fix alone would give an accepted answer, if there is one. "
        "Mention any other errors in the note. Judge against the problem text: the reference "
        "is usually right, but it can be wrong or be one of several readings.",
        "",
        "Reply with CSV only, and no other text: the header `number,key,category,note`, then "
        "one row per failure, with its number and key exactly as given, a category name from "
        "the table, and a one-sentence note in double quotes.",
        "",
        *_categories(),
    ]
    for number, f in enumerate(rows, 1):
        lines += _row(number, f, run.by_id[f.problem_id], rows, neutral=True)
    return "\n".join(lines)


def _categories() -> list[str]:
    return [
        "| category | meaning |",
        "|---|---|",
        *(f"| `{name}` | {meaning} |" for name, meaning in CATEGORIES.items()),
        "",
    ]


def _row(
    number: int, f: Failure, record: Record, rows: list[Failure], neutral: bool = False
) -> list[str]:
    """`neutral`: for an outside judge, so the system and the labels' authors go unnamed."""
    accepted = "; ".join(f"{_show(s.status.value, s.objective)} ({reading})"
                         for reading, s in readings(record))  # fmt: skip
    label = record.integrality
    source = "" if neutral else f" ({label.source})"
    lines = [
        f"## {number}. `{f.problem_id}`: {', '.join(f.conditions)} (key `{f.key}`)",
        "",
        f"> {record.document}",
        "",
        f"**Answered:** {_show(f.status, f.objective)}  ",
        f"**Accepted:** {accepted}  ",
        f"**As annotated:** LP {_show(record.lp.status.value, record.lp.objective)}, IP "
        f"{_show(record.ip.status.value, record.ip.objective)}; label {label.kind}{source}",
        "",
    ]
    if found := facts(f, record, rows):
        lines += [*(f"- {fact}" for fact in found), ""]
    lines += [
        "Reference (the annotation, with its label):",
        "```",
        *format_model(reference_model(record)),
        "```",
        "",
    ]
    if f.model is None:
        lines += ["No model: the baseline answers directly.", ""]
    else:
        whose = "The system's model:" if neutral else "Claude's model:"
        lines += [whose, "```", *format_model(f.model), "```", ""]
    if record.review:
        lines += [f"Review ({record.review.verdict}): {record.review.reason}", ""]
    return lines


def _show(status: str, objective: float | None) -> str:
    return f"optimal {objective:.10g}" if status == "optimal" else status


def sheet_path(run_name: str) -> Path:
    return TAXONOMY_DIR / run_name / "labels.csv"


def label_sheet(rows: list[Failure], path: Path) -> None:
    kept = kept_marks(path, "key", MARKS)
    with path.open("w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["number", "key", "problem_id", "conditions", *MARKS])
        for number, f in enumerate(rows, 1):
            mark = kept.get(f.key, dict.fromkeys(MARKS, ""))
            writer.writerow([number, f.key, f.problem_id, " ".join(f.conditions),
                             *(mark[c] for c in MARKS)])  # fmt: skip


def read_labels(path: Path) -> dict[str, str]:
    """Row key -> the owner's category, for the rows labeled so far."""
    labels = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            category = row["category"].strip().lower()
            if category and category not in CATEGORIES:
                raise ValueError(f"row {row['number']}: {category!r} isn't a category "
                                 f"({', '.join(CATEGORIES)})")  # fmt: skip
            if category:
                labels[row["key"]] = category
    return labels


# ---- what the report gives ------------------------------------------------------------


def summary(run: ScoredRun) -> dict:
    """Per condition, its silent failures by category (section 5a)."""
    path = sheet_path(run.name)
    if not path.exists():
        return {"pending": f"no packet yet: python -m opt_agent.taxonomy {run.directory}"}
    labels = read_labels(path)
    counts = {c: Counter() for c in run.manifest.conditions}
    for f in failures(run):
        for c in f.conditions:
            counts[c][labels.get(f.key, UNLABELED)] += 1
    order = [*CATEGORIES, UNLABELED]
    return {
        "graders": graders(path),
        "complete": not any(n[UNLABELED] for n in counts.values()),
        "by condition": {c: {k: n[k] for k in order if n[k]} for c, n in counts.items()},
    }


def write_packet(run_dir: Path) -> tuple[Path, int]:
    run = load(run_dir)
    rows = failures(run)
    out = sheet_path(run.name).parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "PACKET.md").write_text(packet(run, rows))
    (out / "LLM_PROMPT.md").write_text(llm_packet(run, rows))
    label_sheet(rows, sheet_path(run.name))
    return out, len(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The error-taxonomy packet for one run.")
    parser.add_argument("run_dir", type=Path, help="a directory evaluate.py wrote")
    parser.add_argument(
        "--merge",
        type=Path,
        metavar="REPLY",
        help="a judge's reply (number,key,category,note) to write into labels.csv",
    )
    parser.add_argument("--grader", help="with --merge: who labeled, e.g. a model and version")
    args = parser.parse_args(argv)
    if args.merge:
        if not args.grader:
            parser.error("--merge needs --grader")
        sheet = sheet_path(load(args.run_dir).name)
        n = merge_reply(sheet, args.merge, ["category", "note"], args.grader)
        print(f"merged {n} labels from {args.merge} into {sheet}")
        return
    out, n = write_packet(args.run_dir)
    print(f"wrote {out}/PACKET.md, LLM_PROMPT.md and labels.csv ({n} failures)")


if __name__ == "__main__":
    main()
