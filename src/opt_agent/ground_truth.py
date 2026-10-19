"""Build our own NL4Opt ground truth from the human annotations. No LLM is involved.

Each problem is converted (nl4opt.py), then solved twice: once with every variable
continuous (LP) and once with every variable integer (IP), because the annotations don't
say which is intended. Each solve is cross-checked against HiGHS and plain arithmetic.
Problems the checks flag carry a hand review from data/nl4opt/reviews.json, and each
problem's integrality label (integrality.py) picks which of the two answers is the truth.
Test problems used while building the agent are excluded from scoring
(data/nl4opt/exclusions.json). For integer problems with strict wording ("more than"),
the answer with that wording read strictly is stored too, and either reading is accepted
(strict.py, matching_reading).

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
from opt_agent.integrality import Integrality, guess
from opt_agent.nl4opt import ConversionError, Note, convert, load_split
from opt_agent.schema import LPModel
from opt_agent.solver import Status, solve
from opt_agent.strict import strict_constraints, strict_model
from opt_agent.verify import check_solution, same_answer

GROUND_TRUTH_DIR = DATA_DIR / "nl4opt" / "ground_truth"
REVIEWS_PATH = DATA_DIR / "nl4opt" / "reviews.json"
INTEGRALITY_PATH = DATA_DIR / "nl4opt" / "integrality.json"
EXCLUSIONS_PATH = DATA_DIR / "nl4opt" / "exclusions.json"
SPLITS = {"dev": NL4OPT_DEV, "test": NL4OPT_TEST}
# ORLM verdicts that mean "someone is wrong here", so the problem needs a hand review.
DISAGREEMENTS = {"matches neither", "only we find an optimum", "only ORLM finds an optimum"}
# Judgment calls risky enough to need a hand review. For an unlisted variable, neither
# coefficient 0 nor the official converter's 1 is safe: the text may say 45 or 150.
RISKY_NOTES = {"unlisted-variable", "order-mapping-overridden"}


class CheckedSolve(BaseModel):
    status: Status
    objective: float | None = None
    values: dict[str, float] = {}
    highs_agrees: bool
    check_problems: list[str] = []  # from verify.check_solution; [] means it checks out


class StrictReading(BaseModel):
    """The answer with strict wording read strictly (x > y as x >= y + 1)."""

    changed: list[str]  # e.g. "c2_xy: >= 0 became >= 1"
    ip: CheckedSolve  # strictness only has meaning over integers


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
    confirmed_by_owner: bool = False
    answer_affected: bool = True  # for annotation errors: does the error change the answer?


class Record(BaseModel):
    id: str
    document: str
    integrality: Integrality  # picks the ground-truth answer: `ip` if integer, else `lp`
    error: str | None = None  # why the annotation couldn't be converted
    notes: list[Note] = []
    model: LPModel | None = None  # every variable continuous
    lp: CheckedSolve | None = None
    ip: CheckedSolve | None = None  # the same model with every variable integer
    review: Review | None = None
    excluded: str | None = None  # why it's left out of scoring although its answer is fine
    strict: StrictReading | None = None  # integer problems with strict wording only


def build_record(problem_id: str, annotation: dict, label: Integrality | None) -> Record:
    """`label` is the hand label, if any; otherwise the rule decides."""
    document = annotation["document"]
    mentions = set(annotation["order_mapping"]) | set(annotation["vars"])
    integrality = label or guess(document, mentions)
    base = {"id": problem_id, "document": document, "integrality": integrality}
    try:
        conversion = convert(annotation)
    except ConversionError as error:
        return Record(**base, error=str(error))
    model, notes = conversion.model, conversion.notes
    names = strict_constraints(notes)
    strict = None
    if names and integrality.kind == "integer":
        tight, changed = strict_model(as_integer(model), names)
        strict = StrictReading(changed=changed, ip=solve_checked(tight))
    return Record(
        **base,
        notes=notes,
        model=model,
        lp=solve_checked(model),
        ip=solve_checked(as_integer(model)),
        strict=strict,
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


def answer(record: Record) -> CheckedSolve | None:
    """The ground-truth answer: the integer solve for whole things, else the LP.

    None if there's no answer to trust: the annotation wasn't converted, HiGHS disagrees
    with CBC, or plain arithmetic finds a problem with CBC's solution.
    """
    solve = record.ip if record.integrality.kind == "integer" else record.lp
    return solve if solve is not None and _trusted(solve) else None


def _trusted(solve: CheckedSolve) -> bool:
    return solve.highs_agrees and not solve.check_problems


Reading = Literal["annotated", "strict"]


def readings(record: Record) -> dict[Reading, CheckedSolve]:
    """Every answer a correct model may reach: the annotated reading, and for integer
    problems with strict wording, the strict one. Untrusted solves are left out."""
    found: dict[Reading, CheckedSolve] = {}
    if (annotated := answer(record)) is not None:
        found["annotated"] = annotated
    if record.strict is not None and _trusted(record.strict.ip):
        found["strict"] = record.strict.ip
    return found


def matching_reading(record: Record, status: Status, objective: float | None) -> Reading | None:
    """Which reading an agent's answer matches, "annotated" first; None if neither. A score
    records this, so the report can say how many correct answers needed the strict one."""
    for reading, truth in readings(record).items():
        if status is truth.status and (
            status is not Status.OPTIMAL or same_value(objective, truth.objective)
        ):
            return reading
    return None


def same_value(a: float, b: float) -> bool:
    """Equal objectives, up to solver round-off."""
    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)


def needs_hand_label(record: Record) -> bool:
    """Where integrality changes the answer, the label picks the truth, so a rule won't do."""
    return record.error is None and integrality_matters(record)


def integrality_matters(record: Record) -> bool:
    """Does requiring whole numbers change the answer?"""
    lp, ip = record.lp, record.ip
    if lp.status != ip.status:
        return True
    if lp.status is not Status.OPTIMAL:
        return False
    return not same_value(lp.objective, ip.objective)


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
    risky = any(n.kind in RISKY_NOTES for n in record.notes)
    return risky or lacks_optimum(record) or does_nothing(record) or orlm_verdict in DISAGREEMENTS


def scorable(record: Record) -> bool:
    """Usable as ground truth: a trusted answer that no known annotation error changes, on a
    problem that wasn't used while building the agent."""
    return (
        answer(record) is not None
        and record.excluded is None
        and not (_annotation_error(record) and record.review.answer_affected)
    )


def blind_gradable(record: Record) -> bool:
    """Fit for milestone 6's blind-grading packet, which shows graders the annotators'
    formulation next to the model's: so no known annotation error at all."""
    return scorable(record) and not _annotation_error(record)


def _annotation_error(record: Record) -> bool:
    return record.review is not None and record.review.verdict == "annotation-error"


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


def load_integrality(path: Path) -> dict[tuple[str, str], Integrality]:
    """(split, problem id) -> hand label."""
    rows = json.loads(path.read_text())["labels"]
    return {(row["split"], row["id"]): Integrality(**row) for row in rows}  # extra keys ignored


def load_exclusions(path: Path) -> dict[tuple[str, str], str]:
    """(split, problem id) -> why it's excluded from scoring."""
    rows = json.loads(path.read_text())["exclusions"]
    return {(row["split"], row["id"]): row["reason"] for row in rows}


def load_records(path: Path) -> list[Record]:
    return [Record.model_validate(row) for row in json.loads(path.read_text())]


def write_records(records: list[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r.model_dump(mode="json", exclude_none=True) for r in records]
    path.write_text(json.dumps(rows, indent=1) + "\n")


def main() -> None:
    reviews = load_reviews(REVIEWS_PATH)
    labels = load_integrality(INTEGRALITY_PATH)
    exclusions = load_exclusions(EXCLUSIONS_PATH)
    by_split = {}
    for split, source in SPLITS.items():
        problems = load_split(fetch(source))
        records = [
            build_record(pid, ann, labels.get((split, pid))) for pid, ann in problems.items()
        ]
        for r in records:
            r.review = reviews.get((split, r.id))
            r.excluded = exclusions.get((split, r.id))
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
    lines += _excluded_section(by_split)
    lines += _review_section(by_split, verdicts)
    lines += _integrality_section(by_split, verdicts["test"])
    lines += _notes_section(by_split)
    lines += _strict_section(by_split)
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
            sum(blind_gradable(r) for r in records),
            sum(r.lp.status is Status.OPTIMAL for r in ok),
            sum(r.ip.status is Status.OPTIMAL for r in ok),
            sum(answer(r).status is Status.OPTIMAL for r in ok if scorable(r)),
            sum(integrality_matters(r) for r in ok),
            sum(not s.highs_agrees for s in solves),
            sum(bool(s.check_problems) for s in solves),
        ])  # fmt: skip
    header = [
        "split", "problems", "converted", "scorable", "blind-gradable", "LP optimal", "IP optimal",
        "scorable with an optimal answer", "integrality changes the answer",
        "CBC/HiGHS disagreements", "failed arithmetic checks",
    ]  # fmt: skip
    note = (
        "*Scorable* = converted; its answer is confirmed by HiGHS and passes the arithmetic "
        "checks; no annotation error found by hand review changes it; and the problem wasn't "
        "used while building the agent. *Blind-gradable* = scorable with no known annotation "
        "error at all. A problem's answer is its IP or LP optimum, picked by its integrality "
        "label."
    )
    return ["## Summary", "", *_table(header, rows), note, ""]


def _rejected_section(by_split: dict[str, list[Record]]) -> list[str]:
    rows = [[split, f"`{r.id}`", r.error] for split, rs in by_split.items() for r in rs if r.error]
    intro = "Annotation errors caught automatically; these problems can't be converted."
    return ["## Rejected annotations", "", intro, "", *_table(["split", "id", "reason"], rows)]


def _excluded_section(by_split: dict[str, list[Record]]) -> list[str]:
    rows = [
        [split, f"`{r.id}`", r.excluded] for split, rs in by_split.items() for r in rs if r.excluded
    ]
    intro = (
        "Used while building the agent, so not scored; the ground truth itself is fine "
        "(`data/nl4opt/exclusions.json`)."
    )
    return ["## Excluded from scoring", "", intro, "", *_table(["split", "id", "reason"], rows)]


def _review_section(by_split: dict[str, list[Record]], verdicts: dict[str, dict]) -> list[str]:
    reviewed = [(split, r) for split, rs in by_split.items() for r in rs if r.review]
    kinds = list(Review.model_fields["verdict"].annotation.__args__)
    counts = [[k, *(sum(r.review.verdict == k for s, r in reviewed if s == sp) for sp in by_split)]
              for k in kinds]  # fmt: skip
    rows = [
        [
            s,
            f"`{r.id}`",
            r.review.verdict,
            "yes" if r.review.confirmed_by_owner else "",
            r.review.reason,
        ]
        for s, r in reviewed
    ]
    missing = [
        f"`{r.id}` ({split})"
        for split, rs in by_split.items()
        for r in rs
        if needs_review(r, verdicts[split].get(r.id)) and not r.review
    ]
    # These verdicts describe a flag ("no optimum", "do-nothing", "ORLM is wrong"), so they go
    # stale if the flag goes away. Annotation errors can also be found just by reading.
    flag_verdicts = {"text-has-no-optimum", "degenerate-text", "orlm-error"}
    stale = [
        f"`{r.id}` ({split})"
        for split, r in reviewed
        if r.review.verdict in flag_verdicts and not needs_review(r, verdicts[split].get(r.id))
    ]
    confirmed = ", ".join(
        f"{split} {sum(r.review.confirmed_by_owner for s, r in reviewed if s == split)} of "
        f"{sum(s == split for s, _ in reviewed)}"
        for split in by_split
    )
    return [
        "## Hand review",
        "",
        "Every problem with no optimum, a do-nothing optimum, an ORLM disagreement, an",
        "unlisted variable, or an overridden order_mapping is checked by hand against the text",
        "(`data/nl4opt/reviews.json`). Claude wrote every review; the owner confirms them.",
        "",
        *_table(["verdict", *by_split], counts),
        f"Confirmed by the owner: {confirmed}. Unconfirmed test reviews are in "
        "`review/test_reviews/`.",
        "",
        f"Flagged but not reviewed: {', '.join(missing) or 'none'}.",
        f"Reviewed but no longer flagged: {', '.join(stale) or 'none'}.",
        "",
        *_table(["split", "id", "verdict", "owner-confirmed", "reason"], rows),
    ]


def _integrality_section(by_split: dict[str, list[Record]], test_verdicts: dict) -> list[str]:
    kinds = [(k, s) for k in ("integer", "continuous") for s in ("owner", "claude", "rule")]
    counts = [
        [kind, source, *(sum(r.integrality.kind == kind and r.integrality.source == source
                             for r in rs) for rs in by_split.values())]
        for kind, source in kinds
    ]  # fmt: skip
    unlabeled = [
        f"`{r.id}` ({split})"
        for split, rs in by_split.items()
        for r in rs
        if needs_hand_label(r) and r.integrality.source == "rule"
    ]
    orlm_kind = {"matches IP only": "integer", "matches LP only": "continuous"}
    test = {r.id: r for r in by_split["test"]}
    compared = {i: orlm_kind[v] for i, v in test_verdicts.items() if v in orlm_kind}
    disagreements = [
        [f"`{i}`", test[i].integrality.kind, kind, test[i].document[:80]]
        for i, kind in compared.items()
        if test[i].integrality.kind != kind
    ]
    agreeing = len(compared) - len(disagreements)
    return [
        "## Integrality labels",
        "",
        "Each problem's label picks its answer (IP for integer, LP for continuous). Where",
        "integrality changes the answer, the label is a hand label",
        "(`data/nl4opt/integrality.json`); elsewhere a rule (`integrality.py`) sets it.",
        "",
        *_table(["label", "source", *by_split], counts),
        f"Integrality changes the answer but there's no hand label: "
        f"{', '.join(unlabeled) or 'none'}.",
        "",
        f"Where ORLM's answer matches exactly one of our optima, its implied label agrees with "
        f"ours in {agreeing} of {len(compared)} test problems. (ORLM's labels came from GPT-4, "
        "so this is a sanity check, not a score.) Where they differ:",
        "",
        *_table(["id", "ours", "ORLM's", "problem"], disagreements),
    ]


def _notes_section(by_split: dict[str, list[Record]]) -> list[str]:
    kinds = sorted({n.kind for rs in by_split.values() for r in rs for n in r.notes})
    rows = [
        [kind, *(sum(any(n.kind == kind for n in r.notes) for r in rs) for rs in by_split.values())]
        for kind in kinds
    ]
    intro = "Problems affected by each kind of judgment call (details are in the JSON `notes`)."
    return ["## Judgment calls", "", intro, "", *_table(["kind", *by_split], rows)]


def _strict_section(by_split: dict[str, list[Record]]) -> list[str]:
    def show(s: CheckedSolve) -> str:
        return f"{s.objective:g}" if s.status is Status.OPTIMAL else s.status.value

    with_strict = [(split, r) for split, rs in by_split.items() for r in rs if r.strict]
    rows = [
        [split, f"`{r.id}`", show(r.ip), show(r.strict.ip), "; ".join(r.strict.changed)]
        for split, r in with_strict
    ]
    changes = {
        split: sum(
            show(r.ip) != show(r.strict.ip) for s, r in with_strict if s == split and scorable(r)
        )
        for split in by_split
    }
    totals = {split: sum(s == split and scorable(r) for s, r in with_strict) for split in by_split}
    counts = ", ".join(f"{changes[s]} of {totals[s]} scorable {s} problems" for s in by_split)
    intro = (
        'Integer problems whose wording is strict ("more than", "must exceed") but which are '
        "annotated, and so modeled, as >= or <=. Read strictly, each noted constraint moves by "
        "the smallest step its left side can take over integers (`strict.py`). Either answer "
        f"is accepted. The strict reading changes the answer in {counts}."
    )
    return [
        "## Strict wording",
        "",
        intro,
        "",
        *_table(["split", "id", "annotated (IP)", "strict (IP)", "tightened"], rows),
    ]


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
