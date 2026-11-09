"""Amendment 4's rows (docs/amendments/amendment-4.md), computed from the frozen test run.

- **Two pre-registered rows the README left out**, copied from the frozen report as it
  computed them: lenient accuracy (Amendment 2, part 4) and accuracy without the disputed
  reviews (Amendment 2, part 6).
- **One exploratory, post hoc row: corrected labels.** The 4 problems whose integrality
  label is the rule's "continuous" only because the text says "units of X" (CORRECTED) are
  relabeled, and every answer is scored again. Nothing else changes. As in
  ground_truth.build_record, a label that isn't continuous brings the strict reading of the
  problem's strict wording with it, solved and cross-checked the same way.
- **The six answer-key errors** that Amendment 3's row counts as correct, each with its
  kind and reason. Only the 4 integrality ones are corrected here; the 2 operator errors
  are listed, not corrected (milestone 3: annotation errors are never repaired).

The result of record stays the pre-registered strict accuracy, 264/274 per condition.

Unlike Amendment 3's row, this one isn't written into runs/test/report.json:
scripts/eval_json.py calls row() directly, so the committed run's files stay as they were,
and a report rebuild can't drop it. No API calls; the strict readings are solved locally.

Run:  python scripts/amendment4.py runs/test   # prints the row; eval_json.py writes it
"""

import argparse
import json
from pathlib import Path

from opt_agent.ground_truth import (
    Record,
    StrictReading,
    answer,
    as_integer,
    scorable,
    solve_checked,
    trusted,
)
from opt_agent.report import rate
from opt_agent.run_results import ScoredRun, load
from opt_agent.scoring import score
from opt_agent.strict import strict_constraints, strict_model

# Problem id -> the corrected label. The rule (integrality.py) reads "units of X" as a
# divisible quantity. In the first three, X is an ingredient of a countable product; in the
# fourth, X is the product, but the text also counts it ("the number of wine must be larger
# than the number of kombucha"), so it gets `either`. Each has strict wording, and each
# annotated optimum is 0 whatever the label, so no hand label was ever required.
CORRECTED = {
    "431521997": "integer",  # bubble teas; the rule matched "units of lychee [juice]"
    "1605420061": "integer",  # crepes; "units of chocolate [spread]"
    "-1540907330": "integer",  # bowls of curry; "units of chicken [meat]"
    "2078392466": "either",  # "each unit of kombucha", and "the number of wine"
}

# The 6 failures Amendment 3's row counts as correct, in its order, with why each key is
# wrong for its text.
KEY_ERRORS = {
    "431521997": (
        "integrality rule",
        "The rule labeled bubble teas continuous because the text says 'units of lychee "
        "juice'. That switched off the strict reading of 'the number of mango bubble teas "
        "made must be large than the number of lychee bubble teas made', so making nothing "
        "(the annotated optimum) stayed the only accepted answer.",
    ),
    "1605420061": (
        "integrality rule",
        "The rule labeled crepes continuous because the text says 'units of chocolate "
        "spread'. That switched off the strict reading of 'the number of peanut butter "
        "crepes made must exceed the number of chocolate crepes made'.",
    ),
    "-1540907330": (
        "integrality rule",
        "The rule labeled curry bowls continuous because the text says 'units of chicken "
        "meat'. That switched off the strict reading of 'the number of goat curry bowls "
        "must be larger than the number of chicken curry bowls'.",
    ),
    "2078392466": (
        "integrality rule",
        "The rule labeled the products continuous because the text says 'each unit of "
        "kombucha'. The text also counts them ('the number of wine must be larger than the "
        "number of kombucha'), so the strict reading is supported and was switched off.",
    ),
    "-926961422": (
        "annotated operator",
        "'The company has a total of 6 working hours a day' is a limit, but the annotation "
        "says at least 6 hours. Not corrected here: the operator check only covers "
        "comparatives, and annotation errors are never repaired.",
    ),
    "-2138755435": (
        "annotated operator",
        "'The restaurant wants to have 4000 customer interactions per hour' is a "
        "requirement, but the annotation says at most 4000, so the key is a plan with "
        "almost no service. Not corrected here, for the same reason.",
    ),
}

RESULT_OF_RECORD = "pre-registered strict accuracy (sections 1, 4 and 5)"


def corrected(record: Record, kind: str) -> Record:
    """The record with its integrality label corrected, and the strict reading that a label
    that isn't continuous brings with it (as ground_truth.build_record makes it)."""
    names = strict_constraints(record.notes)
    if not names:
        raise ValueError(f"{record.id} has no strict wording to read strictly")
    tight, changed = strict_model(as_integer(record.model), names)
    strict = StrictReading(changed=changed, ip=solve_checked(tight))
    if not trusted(strict.ip):
        raise ValueError(f"{record.id}: the strict reading's solve isn't trusted")
    integrality = record.integrality.model_copy(
        update={"kind": kind, "note": f"Amendment 4 (exploratory): {kind}, not continuous"}
    )
    return record.model_copy(update={"integrality": integrality, "strict": strict})


def rule_continuous_with_strict_wording(records: list[Record]) -> list[str]:
    """The problems the criterion picks: scorable, a rule label of "continuous" from the
    "units of" match, and strict wording. CORRECTED must be exactly these."""
    return sorted(
        r.id
        for r in records
        if scorable(r)
        and r.integrality.source == "rule"
        and r.integrality.kind == "continuous"
        and (r.integrality.note or "").startswith("says 'unit")
        and strict_constraints(r.notes)
    )


def row(run: ScoredRun, report: dict) -> dict:
    """Amendment 4's rows for the test run. `report` is the run's report.json, from which
    the pre-registered rows are copied as the frozen code computed them."""
    if run.manifest.split != "test":
        raise ValueError("Amendment 4 covers the main test run only")
    picked = rule_continuous_with_strict_wording(run.records)
    if picked != sorted(CORRECTED):
        raise ValueError(f"the criterion picks {picked}, not {sorted(CORRECTED)}")
    fixed = {i: corrected(run.by_id[i], kind) for i, kind in CORRECTED.items()}

    by_condition = {}
    for c in run.manifest.conditions:
        scored = [p for p in run.pairs if p.condition == c and p.state == "scored"]
        primary = sum(p.score.correct for p in scored)
        if rate(primary, len(scored)) != report["conditions"][c]["accuracy"]["all"]:
            raise ValueError(f"{c}: the report's strict accuracy doesn't match the run")
        now = {p.problem_id: _rescore(p, fixed) for p in scored}
        broken = [p.problem_id for p in scored if p.score.correct and not now[p.problem_id]]
        if broken:  # relabeling must only add accepted answers here
            raise ValueError(f"{c}: corrected labels turn right answers wrong: {broken}")
        flipped = sorted(p.problem_id for p in scored if now[p.problem_id] and not p.score.correct)
        accuracy = report["conditions"][c]
        by_condition[c] = {
            "result of record": accuracy["accuracy"]["all"],
            "lenient": accuracy["lenient accuracy"]["all"],
            "without disputed reviews": accuracy["accuracy without disputed reviews"]["all"],
            "corrected labels": rate(sum(now.values()), len(scored)),
            "counted as correct": flipped,
        }

    return {
        "label": "Amendment 4 (draft): two pre-registered rows the README omitted, and one "
        "exploratory, post hoc row",
        "result of record": RESULT_OF_RECORD,
        "rows": {
            "result of record": RESULT_OF_RECORD,
            "lenient": "pre-registered (Amendment 2, part 4): integrality not graded",
            "without disputed reviews": "pre-registered sensitivity (Amendment 2, part 6)",
            "corrected labels": "exploratory, post hoc (Amendment 4): the 4 rule labels "
            "in `corrected` relabeled, every answer scored again",
        },
        "corrected": [
            {
                "problem_id": i,
                "label": kind,
                "was": run.by_id[i].integrality.kind,
                "rule note": run.by_id[i].integrality.note,
                "strict reading": fixed[i].strict.changed,
                "strict answer": fixed[i].strict.ip.objective,
            }
            for i, kind in CORRECTED.items()
        ],
        "by condition": by_condition,
        "key errors": [
            _key_error(run, i, kind, reason, fixed) for i, (kind, reason) in KEY_ERRORS.items()
        ],
    }


def _rescore(pair, fixed: dict[str, Record]) -> bool:
    if pair.problem_id not in fixed or pair.item.outcome != "done":
        return pair.score.correct
    return score(fixed[pair.problem_id], pair.item.status, pair.item.objective).correct


def _key_error(run: ScoredRun, problem: str, kind: str, reason: str, fixed: dict) -> dict:
    record = run.by_id[problem]
    answers = {p.condition: p.item.objective if p.item.status == "optimal" else p.item.status
               for p in run.pairs if p.problem_id == problem}  # fmt: skip
    return {
        "problem_id": problem,
        "kind": kind,
        "key": answer(record).objective,
        "answers": answers,
        "corrected here": problem in fixed,
        "reason": reason,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Print Amendment 4's rows.")
    parser.add_argument("run_dir", type=Path, help="the test run, e.g. runs/test")
    args = parser.parse_args(argv)
    report = json.loads((args.run_dir / "report.json").read_text())
    new = row(load(args.run_dir), report)
    for c, r in new["by condition"].items():
        print(f"{c}: result of record {_show(r['result of record'])}, lenient "
              f"{_show(r['lenient'])}, without disputed reviews "
              f"{_show(r['without disputed reviews'])}, corrected labels "
              f"{_show(r['corrected labels'])} (+{len(r['counted as correct'])})")  # fmt: skip
    print("Not written anywhere: python scripts/eval_json.py puts it in results/eval.json")


def _show(r: dict) -> str:
    return f"{r['right']}/{r['n']}"


if __name__ == "__main__":
    main()
