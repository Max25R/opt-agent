"""Packets for the owner's hand checks, and what to make of the marks that come back.

1. **Blind integrality labels.** 40 problems, drawn with a recorded seed from the scorable
   test problems where integer vs continuous changes the answer. The packet shows only the
   text and the variable names, never our label. The owner marks each variable in
   labels.csv, and `agreement` compares their labels with ours, with a Wilson interval.
2. **Test reviews.** Every test-split hand review (all Claude's so far), least sure first,
   with the text, the model, both optima, the labels, and the note. The owner marks each
   one confirmed or disputed in marks.csv.
3. **"Says LP" labels.** The 4 scorable test problems whose text asks for an LP but where
   integrality changes the answer. The pre-registration lets the label decide, so the
   owner sets these labels (review/says_lp.md). They're not a blind check of Claude's
   labels, so `agreement` leaves them out.
4. **The judges' integrality labels** (pre-registration, Amendment 2): the problems of 1
   and 3 in one prompt for an LLM judge, which labels each problem integer, continuous or
   either. Two judges answer the same prompt, each in its own sheet, so their labels can
   be compared. The owner's packets 1 and 3 are left as they are.

Run:  python -m opt_agent.packets integrality    # writes review/integrality_blind/
      python -m opt_agent.packets reviews        # writes review/test_reviews/
      python -m opt_agent.packets says-lp        # writes review/says_lp.md
      python -m opt_agent.packets agreement      # after labels.csv is filled in
      python -m opt_agent.packets judge          # writes review/integrality_judge/
      python -m opt_agent.packets judge --merge judge --reply REPLY.csv --grader "MODEL"
"""

import argparse
import csv
import json
import random
import re
from pathlib import Path

from pydantic import BaseModel

from opt_agent.agent import format_model
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    CheckedSolve,
    Record,
    integrality_matters,
    load_records,
    scorable,
)
from opt_agent.runs import REPO_ROOT
from opt_agent.solver import Status
from opt_agent.stats import wilson

REVIEW_DIR = REPO_ROOT / "review"
BLIND_DIR = REVIEW_DIR / "integrality_blind"
REVIEWS_DIR = REVIEW_DIR / "test_reviews"
SEED = 20261019  # recorded so anyone can redraw the same 40
SAMPLE_SIZE = 40
KINDS = ("integer", "continuous")
SURENESS_ORDER = {"low": 0, "medium": 1, "high": 2}
SAYS_LP_PATH = REVIEW_DIR / "says_lp.md"
# Scorable, integrality-sensitive test problems whose text says "LP" or "linear program"
# and that were labeled integer by Claude (docs/PREREGISTRATION.md, 3d). Listed by id: the
# owner's labels may change their kind, and the list must stay put.
SAYS_LP = ["1040407495", "-1536845616", "1703643437", "1054847148"]


# ---- 1. blind integrality labels -------------------------------------------------------


def sensitive_problems(records: list[Record]) -> list[Record]:
    """Scorable problems where requiring whole numbers changes the answer."""
    return [r for r in records if scorable(r) and integrality_matters(r)]


def blind_sample(records: list[Record], seed: int = SEED, size: int = SAMPLE_SIZE) -> list[Record]:
    """A seeded draw, in draw order. Sorting by id first makes it independent of file order."""
    pool = sorted(sensitive_problems(records), key=lambda r: r.id)
    return random.Random(seed).sample(pool, size)


def integrality_packet(sample: list[Record], pool_size: int) -> str:
    lines = [
        "# Blind integrality labels",
        "",
        f"{len(sample)} problems drawn at random (seed {SEED}, `python -m opt_agent.packets "
        f"integrality`) from the {pool_size} scorable test problems where integer vs "
        "continuous changes the answer. Our labels are deliberately not shown; please don't "
        "open `data/nl4opt/integrality.json`, or the review packet (`review/test_reviews/`, "
        "which shows labels), until you're done.",
        "",
        "For every variable, write `integer` or `continuous` in the `label` column of "
        "`labels.csv`, by what the text says it counts or measures. Then run "
        "`python -m opt_agent.packets agreement`.",
        "",
    ]
    for number, r in enumerate(sample, 1):
        names = ", ".join(f"`{v.name}`" for v in r.model.variables)
        lines += [f"## {number}. `{r.id}`", "", f"> {r.document}", "", f"Variables: {names}", ""]
    return "\n".join(lines)


def label_sheet(sample: list[Record], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "problem_id", "variable", "label"])
        for number, r in enumerate(sample, 1):
            for v in r.model.variables:
                writer.writerow([number, r.id, v.name, ""])


def read_labels(path: Path) -> dict[str, dict[str, str]]:
    """problem id -> variable -> the owner's label. Every row must be filled in."""
    labels: dict[str, dict[str, str]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            label = row["label"].strip().lower()
            if label not in KINDS:
                raise ValueError(f"problem {row['number']}, {row['variable']!r}: {label!r} "
                                 f"is neither integer nor continuous")  # fmt: skip
            labels.setdefault(row["problem_id"], {})[row["variable"]] = label
    return labels


class Agreement(BaseModel):
    problems: int
    agree: int
    interval: tuple[float, float]  # 95% Wilson
    variables: int
    variables_agree: int
    mixed: list[str]  # problems the owner marked partly integer: neither stored answer fits
    disagreements: list[tuple[str, str, str]]  # (problem id, ours, the owner's)


def agreement(owner: dict[str, dict[str, str]], records: list[Record]) -> Agreement:
    """Per problem: the owner's label is integer (or continuous) if every variable is.
    Our labels are per problem, so a mixed mark disagrees with ours whichever it is."""
    by_id = {r.id: r for r in records}
    agree, mixed, disagreements = 0, [], []
    variables = variables_agree = 0
    owner = {pid: marks for pid, marks in owner.items() if pid not in SAYS_LP}  # 3d
    for problem_id, marks in owner.items():
        ours = by_id[problem_id].integrality.kind
        kinds = set(marks.values())
        theirs = kinds.pop() if len(kinds) == 1 else "mixed"
        variables += len(marks)
        variables_agree += sum(kind == ours for kind in marks.values())
        if theirs == ours:
            agree += 1
        else:
            disagreements.append((problem_id, ours, theirs))
            if theirs == "mixed":
                mixed.append(problem_id)
    return Agreement(
        problems=len(owner),
        agree=agree,
        interval=wilson(agree, len(owner)),
        variables=variables,
        variables_agree=variables_agree,
        mixed=mixed,
        disagreements=disagreements,
    )


def agreement_report(a: Agreement) -> str:
    low, high = a.interval
    lines = [
        "# Integrality labels: owner vs Claude",
        "",
        "Generated by `python -m opt_agent.packets agreement` from `labels.csv`.",
        "",
        f"- Problems: the owner's label matches ours in **{a.agree} of {a.problems}** "
        f"({a.agree / a.problems:.0%}; 95% Wilson interval {low:.0%} to {high:.0%}).",
        f"- Variables: {a.variables_agree} of {a.variables} match the problem's label.",
        f"- Marked partly integer (neither stored answer applies): {len(a.mixed)}.",
        "",
        "| problem | ours | owner's |",
        "|---|---|---|",
        *(f"| `{pid}` | {ours} | {theirs} |" for pid, ours, theirs in a.disagreements),
    ]
    return "\n".join(lines) + "\n"


# ---- 2. test reviews --------------------------------------------------------------------


def load_sureness(path: Path) -> dict[str, tuple[str, str]]:
    rows = json.loads(path.read_text())["sureness"]
    return {row["id"]: (row["level"], row["why"]) for row in rows}


def review_order(
    records: list[Record], sureness: dict[str, tuple[str, str]]
) -> list[tuple[Record, str, str | None]]:
    """(record, level, why) for every reviewed problem, least sure first, then file order."""
    reviewed = [r for r in records if r.review]
    unknown = set(sureness) - {r.id for r in reviewed}
    if unknown:
        raise ValueError(f"sureness for problems without a review: {sorted(unknown)}")
    rows = [(r, *sureness.get(r.id, ("high", None))) for r in reviewed]
    return sorted(rows, key=lambda row: SURENESS_ORDER[row[1]])  # stable: file order within


def review_packet(rows: list[tuple[Record, str, str | None]], blind: set[str]) -> str:
    """`blind`: ids in the blind integrality sample. This packet shows their labels."""
    overlap = [r.id for r, _, _ in rows if r.id in blind]
    lines = [
        "# Test-split reviews to confirm",
        "",
        f"**Do the blind integrality packet first** (`review/integrality_blind/`): "
        f"{len(overlap)} of these problems are in it, and this packet shows their labels.",
        "",
        f"All {len(rows)} test-split hand reviews are Claude's and unconfirmed. They're ordered "
        "least sure first. For each, mark `confirmed` or `disputed` (with a word on why) in "
        "`marks.csv`. A confirmed review stays as it is; a disputed one gets discussed before "
        "any test run.",
        "",
    ]
    for number, (r, level, why) in enumerate(rows, 1):
        v = r.review
        lines += [f"## {number}. `{r.id}`: {v.verdict} (sureness: {level})", ""]
        if why:
            lines += [f"**Why I'm not sure:** {why}", ""]
        lines += [f"> {r.document}", ""]
        if r.model is None:
            lines += [f"**Not converted:** {r.error}", ""]
        else:
            # Objective and constraints only: the stored model is all-continuous, and its
            # variable lines would read like a label. The label is shown below.
            shown = format_model(r.model)[: 1 + len(r.model.constraints)]
            lines += ["```", *shown, "  every variable >= 0", "```", "", *_answers(r), ""]
        label = r.integrality
        lines += [
            f"- Integrality label: **{label.kind}** ({label.source}"
            + (f": {label.note}" if label.note else "")
            + ")",
            *(f"- Note ({n.kind}): {n.detail}" for n in r.notes),
            f"- **My review ({v.verdict}):** {v.reason}",
        ]
        if v.verdict == "annotation-error":
            changes = "changes the answer" if v.answer_affected else "leaves the answer alone"
            lines.append(f"- The error {changes}.")
        if r.excluded:
            lines.append(f"- Excluded from scoring anyway: {r.excluded}.")
        lines.append("")
    return "\n".join(lines)


def _answers(r: Record) -> list[str]:
    lines = [f"**LP:** {_show(r.lp)}  ", f"**IP:** {_show(r.ip)}"]
    if r.strict:
        lines[-1] += "  "
        lines.append(
            f"**IP, strict reading:** {_show(r.strict.ip)} ({'; '.join(r.strict.changed)})"
        )
    return lines


def _show(s: CheckedSolve) -> str:
    if s.status is not Status.OPTIMAL:
        return s.status.value
    values = ", ".join(f"{name} = {x:g}" for name, x in s.values.items())
    return f"{s.objective:g} ({values})"


def mark_sheet(rows: list[tuple[Record, str, str | None]], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "problem_id", "verdict", "sureness", "mark", "comment"])
        for number, (r, level, _) in enumerate(rows, 1):
            writer.writerow([number, r.id, r.review.verdict, level, "", ""])


# ---- sheets the run packets regenerate (blind_grading.py, taxonomy.py) ------------------


def kept_marks(path: Path, key: str, columns: list[str]) -> dict[str, dict[str, str]]:
    """What a grader already wrote in a sheet, by each row's key, so that regenerating its
    packet keeps it. A column the sheet doesn't have yet comes back empty."""
    if not path.exists():
        return {}
    with path.open(newline="") as f:
        return {row[key]: {c: row.get(c) or "" for c in columns} for row in csv.DictReader(f)}


def merge_reply(sheet: Path, reply: Path, columns: list[str], grader: str) -> int:
    """Write a judge's reply (a CSV with `number` and `columns`, as the judge gave it) into a
    packet's sheet row by row, naming the judge in the sheet's `grader` column. The reply
    must cover every row exactly once, and if it repeats the keys they must match, so a
    skipped, doubled or shifted row can't slip in. Returns the number of rows merged."""
    with sheet.open(newline="") as f:
        rows = list(csv.DictReader(f))
    with reply.open(newline="") as f:
        answered = list(csv.DictReader(f))
    replies = {r["number"].strip(): r for r in answered}
    numbers = [row["number"] for row in rows]
    if len(answered) != len(replies) or sorted(replies) != sorted(numbers):
        given = [r["number"].strip() for r in answered]
        raise ValueError(f"{reply} answers rows {given}, not each of {numbers} once")
    for row in rows:
        answer = replies[row["number"]]
        for name in ("key", "problem_id"):  # whichever the sheet and the reply both have
            if answer.get(name) and name in row and answer[name].strip() != row[name]:
                raise ValueError(f"row {row['number']}: {name} {answer[name]!r}, "
                                 f"not {row[name]!r}")  # fmt: skip
        row.update({c: (answer.get(c) or "").strip() for c in columns}, grader=grader)
    fields = [*rows[0].keys()]
    with sheet.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def graders(sheet: Path) -> list[str]:
    """Who filled in a sheet, as its `grader` column names them."""
    with sheet.open(newline="") as f:
        return sorted({(row.get("grader") or "").strip() for row in csv.DictReader(f)} - {""})


# ---- 3. "says LP" labels ---------------------------------------------------------------

_ROW = re.compile(r"^\| `(?P<variable>[^`]+)` \| (?P<label>[^|]*?) \|$")


def says_lp_packet(records: list[Record]) -> str:
    by_id = {r.id: r for r in records}
    lines = [
        '# Text says "LP": your integrality labels',
        "",
        f"{len(SAYS_LP)} scorable test problems whose text asks for an LP, but where requiring "
        "whole numbers changes the answer. Under the pre-registration (3d) the label decides, "
        "and these labels are yours: Claude's aren't shown. They're not part of the "
        "blind-agreement statistic.",
        "",
        "For each variable, replace `?` with `integer` or `continuous`, by what the text says "
        "it counts or measures.",
        "",
    ]
    for number, problem_id in enumerate(SAYS_LP, 1):
        r = by_id[problem_id]
        lines += [f"## {number}. `{r.id}`", "", f"> {r.document}", ""]
        lines += ["| variable | label |", "|---|---|"]
        lines += [f"| `{v.name}` | ? |" for v in r.model.variables]
        lines.append("")
    return "\n".join(lines)


def read_says_lp(path: Path) -> dict[str, dict[str, str]]:
    """problem id -> variable -> the owner's label, from the filled-in tables."""
    labels: dict[str, dict[str, str]] = {}
    problem_id = None
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            problem_id = line.split("`")[1]
        elif (row := _ROW.match(line)) and problem_id is not None:
            label = row["label"].strip().lower()
            if label not in KINDS:
                raise ValueError(f"{problem_id}, {row['variable']!r}: {label!r} is neither "
                                 "integer nor continuous")  # fmt: skip
            labels.setdefault(problem_id, {})[row["variable"]] = label
    return labels


# ---- 4. the judges' integrality labels -------------------------------------------------

JUDGE_DIR = REVIEW_DIR / "integrality_judge"
JUDGE_LABELS = ("integer", "continuous", "either")
# Sheet name -> role. Both judges answer the same prompt (Amendment 2).
JUDGE_SHEETS = {"judge": "judge.csv", "second": "second_judge.csv"}


def judged_problems(records: list[Record]) -> list[tuple[str, Record]]:
    """(set, record): the blind sample in draw order, then the 4 "says LP" problems."""
    by_id = {r.id: r for r in records}
    return [("blind sample", r) for r in blind_sample(records)] + [
        ("says LP", by_id[i]) for i in SAYS_LP
    ]


def judge_prompt(problems: list[tuple[str, Record]]) -> str:
    """For an LLM judge in a new conversation: the text and the decisions' names only, as
    in the owner's blind packet. It doesn't say which set a problem is from, or name the
    system or who wrote the labels. Labels are per problem, because the ground truth
    stores only the all-integer and the all-continuous optimum."""
    lines = [
        "# Whole numbers or fractions?",
        "",
        f"Below are {len(problems)} optimization word problems. For each, decide whether "
        "its decisions must be whole numbers, by what the text says each one counts or "
        "measures, and give one label:",
        "",
        "- `integer`: only whole-number decisions make sense.",
        "- `continuous`: fractional decisions make sense.",
        "- `either`: the text supports both readings, so a whole-number answer and a "
        "fractional one would both be right.",
        "",
        "Label each problem's decisions as a whole. If they differ (some must be whole and "
        "some needn't), say so in the note.",
        "",
        "Reply with CSV only, and no other text: the header `number,problem_id,label,note`, "
        "then one row per problem, with its number and problem id exactly as given, a "
        "label, and a one-sentence note in double quotes.",
        "",
    ]
    for number, (_, r) in enumerate(problems, 1):
        names = ", ".join(f"`{v.name}`" for v in r.model.variables)
        lines += [f"## {number}. `{r.id}`", "", f"> {r.document}", "", f"Decisions: {names}", ""]
    return "\n".join(lines)


def judge_sheet(problems: list[tuple[str, Record]], path: Path) -> None:
    kept = kept_marks(path, "problem_id", ["label", "note", "grader"])
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "problem_id", "set", "label", "note", "grader"])
        for number, (which, r) in enumerate(problems, 1):
            mark = kept.get(r.id, dict.fromkeys(["label", "note", "grader"], ""))
            writer.writerow([number, r.id, which, mark["label"], mark["note"], mark["grader"]])


def read_judge_labels(path: Path) -> dict[str, str]:
    """problem id -> the judge's label. Every row must be filled in."""
    labels = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            label = row["label"].strip().lower()
            if label not in JUDGE_LABELS:
                raise ValueError(f"problem {row['number']}: {label!r} is none of "
                                 f"{', '.join(JUDGE_LABELS)}")  # fmt: skip
            labels[row["problem_id"]] = label
    return labels


def write_judge_packet(records: list[Record]) -> int:
    problems = judged_problems(records)
    JUDGE_DIR.mkdir(parents=True, exist_ok=True)
    (JUDGE_DIR / "LLM_PROMPT.md").write_text(judge_prompt(problems))
    for name in JUDGE_SHEETS.values():
        judge_sheet(problems, JUDGE_DIR / name)
    return len(problems)


# ---- command line ----------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Hand-check packets for the owner.")
    parser.add_argument(
        "packet", choices=["integrality", "reviews", "says-lp", "agreement", "judge"]
    )
    parser.add_argument(
        "--merge", choices=list(JUDGE_SHEETS), help="judge: write a judge's reply into its sheet"
    )
    parser.add_argument("--reply", type=Path, help="with --merge: the reply, as a CSV file")
    parser.add_argument("--grader", help="with --merge: the judge's model and version")
    args = parser.parse_args(argv)
    test = load_records(GROUND_TRUTH_DIR / "test.json")
    if args.packet == "judge" and args.merge:
        if not (args.reply and args.grader):
            parser.error("--merge needs --reply and --grader")
        sheet = JUDGE_DIR / JUDGE_SHEETS[args.merge]
        n = merge_reply(sheet, args.reply, ["label", "note"], args.grader)
        print(f"merged {n} labels from {args.reply} into {sheet}")
    elif args.packet == "judge":
        n = write_judge_packet(test)
        print(f"wrote {JUDGE_DIR}/LLM_PROMPT.md, judge.csv and second_judge.csv ({n} problems)")
    elif args.packet == "integrality":
        BLIND_DIR.mkdir(parents=True, exist_ok=True)
        sample = blind_sample(test)
        (BLIND_DIR / "PACKET.md").write_text(
            integrality_packet(sample, len(sensitive_problems(test)))
        )
        label_sheet(sample, BLIND_DIR / "labels.csv")
        print(f"wrote {BLIND_DIR}/PACKET.md and labels.csv ({len(sample)} problems)")
    elif args.packet == "reviews":
        rows = review_order(test, load_sureness(REVIEWS_DIR / "sureness.json"))
        blind = {r.id for r in blind_sample(test)}
        (REVIEWS_DIR / "PACKET.md").write_text(review_packet(rows, blind))
        mark_sheet(rows, REVIEWS_DIR / "marks.csv")
        print(f"wrote {REVIEWS_DIR}/PACKET.md and marks.csv ({len(rows)} reviews)")
    elif args.packet == "says-lp":
        SAYS_LP_PATH.write_text(says_lp_packet(test))
        print(f"wrote {SAYS_LP_PATH} ({len(SAYS_LP)} problems)")
    else:
        result = agreement(read_labels(BLIND_DIR / "labels.csv"), test)
        report = agreement_report(result)
        (BLIND_DIR / "AGREEMENT.md").write_text(report)
        print(report)


if __name__ == "__main__":
    main()
