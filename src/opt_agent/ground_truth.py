"""Build our own NL4Opt ground truth from the human annotations. No LLM is involved.

Each problem is converted (nl4opt.py), then solved twice: once with every variable
continuous (LP) and once with every variable integer (IP), because the annotations don't
say which is intended. Each solve is cross-checked against HiGHS and plain arithmetic.
Problems the checks flag carry a hand review from data/nl4opt/reviews.json.

Run:  python -m opt_agent.data && python -m opt_agent.ground_truth
Writes data/nl4opt/ground_truth/{dev,test}.json and REPORT.md. The report is generated
from those files, so every number in it comes from the code, not from typing.
"""

import json
import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from opt_agent import orlm
from opt_agent.data import (
    DATA_DIR,
    NL4OPT_COMMIT,
    NL4OPT_DEV,
    NL4OPT_TEST,
    ORLM_ANSWERS,
    ORLM_REVISION,
    fetch,
)
from opt_agent.highs import solve_with_highs
from opt_agent.nl4opt import ConversionError, Note, convert, load_split
from opt_agent.schema import LPModel
from opt_agent.solver import Solution, Status, solve
from opt_agent.verify import check_solution, tolerance_for

GROUND_TRUTH_DIR = DATA_DIR / "nl4opt" / "ground_truth"
REVIEWS_PATH = DATA_DIR / "nl4opt" / "reviews.json"
SPLITS = {"dev": NL4OPT_DEV, "test": NL4OPT_TEST}
# ORLM verdicts that mean "someone is wrong here", so the problem needs a hand review.
DISAGREEMENTS = {"matches neither", "only we find an optimum", "only ORLM finds an optimum"}


class CheckedSolve(BaseModel):
    status: Status
    objective: float | None = None
    values: dict[str, float] = {}
    highs_agrees: bool
    check_problems: list[str] = []  # from verify.check_solution; [] means it checks out


class Review(BaseModel):
    verdict: Literal[
        "text-has-no-optimum",  # infeasible/unbounded as written: that status is the answer
        "annotation-error",  # the annotation doesn't say what the text says: not scorable
        "orlm-error",  # we're right, ORLM's answer is wrong
        "ambiguous-text",  # the text supports more than one formulation
        "degenerate-text",  # as written, the optimum is to make nothing: right but trivial
        "ok",  # looked suspicious, but the ground truth is right
    ]
    reason: str


class Record(BaseModel):
    id: str
    document: str
    error: str | None = None  # why the annotation couldn't be converted
    notes: list[Note] = []
    model: LPModel | None = None  # every variable continuous
    lp: CheckedSolve | None = None
    ip: CheckedSolve | None = None  # the same model with every variable integer
    review: Review | None = None


def build_record(problem_id: str, annotation: dict) -> Record:
    base = {"id": problem_id, "document": annotation["document"]}
    try:
        conversion = convert(annotation)
    except ConversionError as error:
        return Record(**base, error=str(error))
    model = conversion.model
    return Record(
        **base,
        notes=conversion.notes,
        model=model,
        lp=solve_checked(model),
        ip=solve_checked(as_integer(model)),
    )


def as_integer(model: LPModel) -> LPModel:
    variables = [v.model_copy(update={"integer": True}) for v in model.variables]
    return model.model_copy(update={"variables": variables})


def solve_checked(model: LPModel) -> CheckedSolve:
    cbc, highs = solve(model), solve_with_highs(model)
    return CheckedSolve(
        status=cbc.status,
        objective=cbc.objective,
        values=cbc.values,
        highs_agrees=same_answer(model, cbc, highs),
        check_problems=check_solution(model, cbc),
    )


def same_answer(model: LPModel, a: Solution, b: Solution) -> bool:
    if a.status != b.status:
        return False
    if a.status is not Status.OPTIMAL:
        return True
    return abs(a.objective - b.objective) <= tolerance_for(model.objective.terms, b.values)


def integrality_matters(record: Record) -> bool:
    """Does requiring whole numbers change the answer?"""
    lp, ip = record.lp, record.ip
    if lp.status != ip.status:
        return True
    if lp.status is not Status.OPTIMAL:
        return False
    return not math.isclose(lp.objective, ip.objective, rel_tol=1e-6, abs_tol=1e-6)


def lacks_optimum(record: Record) -> bool:
    return Status.OPTIMAL not in (record.lp.status, record.ip.status) or (
        record.lp.status != record.ip.status
    )


def does_nothing(record: Record) -> bool:
    """The optimum is to make nothing at all: a sign of a degenerate problem text."""
    return record.lp.status is Status.OPTIMAL and all(x == 0 for x in record.lp.values.values())


def needs_review(record: Record, orlm_verdict: str | None) -> bool:
    if record.error is not None:
        return False
    return lacks_optimum(record) or does_nothing(record) or orlm_verdict in DISAGREEMENTS


def scorable(record: Record) -> bool:
    """Usable as ground truth: converted, and not a confirmed annotation error."""
    return record.error is None and not (
        record.review and record.review.verdict == "annotation-error"
    )


def orlm_verdicts(records: list[Record], answers: dict[str, str]) -> dict[str, orlm.Verdict]:
    """Problem id -> how ORLM's answer relates to ours, for problems both sides have."""
    verdicts = {}
    for r in records:
        answer = answers.get(orlm.normalize(r.document))
        if answer is not None and r.error is None:
            verdicts[r.id] = orlm.verdict(answer, r.lp.objective, r.ip.objective)
    return verdicts


def load_reviews(path: Path) -> dict[tuple[str, str], Review]:
    """(split, problem id) -> hand review."""
    rows = json.loads(path.read_text())["reviews"]
    return {(row["split"], row["id"]): Review(**row) for row in rows}  # extra keys ignored


def load_records(path: Path) -> list[Record]:
    return [Record.model_validate(row) for row in json.loads(path.read_text())]


def write_records(records: list[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r.model_dump(mode="json", exclude_none=True) for r in records]
    path.write_text(json.dumps(rows, indent=1) + "\n")


def main() -> None:
    reviews = load_reviews(REVIEWS_PATH)
    by_split = {}
    for split, source in SPLITS.items():
        problems = load_split(fetch(source))
        records = [build_record(pid, annotation) for pid, annotation in problems.items()]
        for r in records:
            r.review = reviews.get((split, r.id))
        by_split[split] = records
        write_records(records, GROUND_TRUTH_DIR / f"{split}.json")
    answers = orlm.load_answers(fetch(ORLM_ANSWERS))
    report = render_report(by_split, answers)
    (GROUND_TRUTH_DIR / "REPORT.md").write_text(report)
    print(report)


# ---- report ----------------------------------------------------------------------------


def render_report(by_split: dict[str, list[Record]], orlm_answers: dict[str, str]) -> str:
    verdicts = {"test": orlm_verdicts(by_split["test"], orlm_answers), "dev": {}}
    lines = [
        "# NL4Opt ground truth: build report",
        "",
        "Generated by `python -m opt_agent.ground_truth`. Don't edit by hand.",
        "",
        f"- NL4Opt annotations: commit `{NL4OPT_COMMIT[:7]}` (MIT License).",
        f"- ORLM answers (cross-check only): revision `{ORLM_REVISION[:7]}` (CC BY-NC 4.0).",
        "- Every variable is >= 0. *LP* treats all variables as continuous, *IP* as integer.",
        "",
    ]
    lines += _summary_section(by_split)
    lines += _rejected_section(by_split)
    lines += _review_section(by_split, verdicts)
    lines += _notes_section(by_split)
    lines += _does_nothing_section(by_split)
    lines += _orlm_section(by_split["test"], orlm_answers, verdicts["test"])
    return "\n".join(lines) + "\n"


def _table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines + [""]


def _converted(records: list[Record]) -> list[Record]:
    return [r for r in records if r.error is None]


def _summary_section(by_split: dict[str, list[Record]]) -> list[str]:
    rows = []
    for split, records in by_split.items():
        ok = _converted(records)
        solves = [s for r in ok for s in (r.lp, r.ip)]
        rows.append([
            split,
            len(records),
            len(ok),
            sum(scorable(r) for r in records),
            sum(r.lp.status is Status.OPTIMAL for r in ok),
            sum(r.ip.status is Status.OPTIMAL for r in ok),
            sum(integrality_matters(r) for r in ok),
            sum(not s.highs_agrees for s in solves),
            sum(bool(s.check_problems) for s in solves),
        ])  # fmt: skip
    header = [
        "split", "problems", "converted", "scorable", "LP optimal", "IP optimal",
        "integrality changes the answer", "CBC/HiGHS disagreements", "failed arithmetic checks",
    ]  # fmt: skip
    note = "*Scorable* = converted and not found to be an annotation error by hand review."
    return ["## Summary", "", *_table(header, rows), note, ""]


def _rejected_section(by_split: dict[str, list[Record]]) -> list[str]:
    rows = [[split, f"`{r.id}`", r.error] for split, rs in by_split.items() for r in rs if r.error]
    intro = "Annotation errors caught automatically; these problems can't be converted."
    return ["## Rejected annotations", "", intro, "", *_table(["split", "id", "reason"], rows)]


def _review_section(by_split: dict[str, list[Record]], verdicts: dict[str, dict]) -> list[str]:
    reviewed = [(split, r) for split, rs in by_split.items() for r in rs if r.review]
    kinds = list(Review.model_fields["verdict"].annotation.__args__)
    counts = [[k, *(sum(r.review.verdict == k for s, r in reviewed if s == sp) for sp in by_split)]
              for k in kinds]  # fmt: skip
    rows = [[s, f"`{r.id}`", r.review.verdict, r.review.reason] for s, r in reviewed]
    missing = [
        f"`{r.id}` ({split})"
        for split, rs in by_split.items()
        for r in rs
        if needs_review(r, verdicts[split].get(r.id)) and not r.review
    ]
    stale = [
        f"`{r.id}` ({split})"
        for split, r in reviewed
        if not needs_review(r, verdicts[split].get(r.id)) and r.review.verdict != "ok"
    ]
    return [
        "## Hand review",
        "",
        "Every problem with no optimum, a do-nothing optimum, or an ORLM disagreement is",
        "checked by hand against the text (`data/nl4opt/reviews.json`).",
        "",
        *_table(["verdict", *by_split], counts),
        f"Flagged but not reviewed: {', '.join(missing) or 'none'}.",
        f"Reviewed but no longer flagged: {', '.join(stale) or 'none'}.",
        "",
        *_table(["split", "id", "verdict", "reason"], rows),
    ]


def _notes_section(by_split: dict[str, list[Record]]) -> list[str]:
    kinds = sorted({n.kind for rs in by_split.values() for r in rs for n in r.notes})
    rows = [
        [kind, *(sum(any(n.kind == kind for n in r.notes) for r in rs) for rs in by_split.values())]
        for kind in kinds
    ]
    intro = "Problems affected by each kind of judgment call (details are in the JSON `notes`)."
    return ["## Judgment calls", "", intro, "", *_table(["kind", *by_split], rows)]


def _does_nothing_section(by_split: dict[str, list[Record]]) -> list[str]:
    rows = [
        [split, f"`{r.id}`", r.document[:90]]
        for split, rs in by_split.items()
        for r in _converted(rs)
        if does_nothing(r)
    ]
    intro = (
        'The optimum is to make nothing (objective 0), usually "minimize resource use" with no '
        "demand to meet. Correct as written, but a degenerate problem."
    )
    return ["## Do-nothing optima", "", intro, "", *_table(["split", "id", "problem"], rows)]


def _orlm_section(test: list[Record], answers: dict[str, str], verdicts: dict) -> list[str]:
    ours = {orlm.normalize(r.document): r for r in test}
    matched = [ours[text] for text in answers if text in ours]
    counts = [[v, sum(x == v for x in verdicts.values())] for v in orlm.Verdict.__args__]
    return [
        "## Cross-check against ORLM (test split)",
        "",
        f"ORLM publishes {len(answers)} answers; {len(matched)} match a test problem by text, "
        f"and {len(verdicts)} of those are problems we could convert. Tolerance: relative "
        f"{orlm.MATCH_TOLERANCE:g}. Disagreements are resolved in the hand review above.",
        "",
        *_table(["verdict", "problems"], counts),
    ]


if __name__ == "__main__":
    main()
