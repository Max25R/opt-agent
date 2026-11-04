"""The blind-grading packet: does a person agree with the automatic score? (pre-registration 5a)

The score compares answers, not models. A wrong model can still reach an accepted answer,
and a right one can miss when the reference reads the text another way or is wrong. So the
owner grades a sample of Claude's models against the text, next to the reference model,
without seeing any answer, score, condition, or problem id, and the report says how often
grade and score agree, separately for models scored right and models scored wrong.

The pool is every distinct final model with a confirmed answer, from single-shot and
self-correction (a model both gave is graded once), on a blind-gradable problem: no known
annotation error, since the packet shows the reference. The sample is stratified, because
wrong answers are rare: up to half of it is drawn from the models scored wrong and the rest
from those scored right, each with the recorded seed from a pool sorted by key, then
shuffled. An unstratified sample of 40 would hold two or three wrong models, too few to say
anything about how the score treats them.

The grade sheet links its rows to models only by key (run_results.model_key), which shows
nothing a grader could look up; the report recomputes the pool to read it.

Run:  python -m opt_agent.blind_grading runs/NAME [--size N]   # writes review/blind_grading/NAME/
      python -m opt_agent.blind_grading runs/NAME --merge REPLY.csv --grader "MODEL, LLM judge"
"""

import argparse
import csv
import random
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from opt_agent.agent import format_model
from opt_agent.ground_truth import blind_gradable, reference_model
from opt_agent.packets import REVIEW_DIR, graders, kept_marks, merge_reply
from opt_agent.run_results import ScoredRun, final_models, load, model_key, model_of
from opt_agent.schema import LPModel
from opt_agent.stats import wilson

BLIND_GRADING_DIR = REVIEW_DIR / "blind_grading"
SEED = 20261030  # recorded so anyone can redraw the same sample
SIZE = 40
GRADES = ("right", "wrong", "unsure")
MARKS = ["grade", "note", "grader"]  # the grader's columns; `grader` names who filled them in


class Formulation(BaseModel):
    key: str
    problem_id: str
    model: LPModel
    scored_right: bool


def pool(run: ScoredRun) -> list[Formulation]:
    """Every distinct model behind a confirmed answer on a blind-gradable problem, by key."""
    models = final_models(run.directory)
    found: dict[str, Formulation] = {}
    for p in run.pairs:
        confirmed = p.state == "scored" and p.score.failure != "loud"
        if p.condition == "baseline" or not confirmed:
            continue
        if not blind_gradable(run.by_id[p.problem_id]):
            continue
        model = model_of(p, models)
        key = model_key(p.problem_id, model)
        found.setdefault(key, Formulation(key=key, problem_id=p.problem_id, model=model,
                                          scored_right=p.score.correct))  # fmt: skip
    return sorted(found.values(), key=lambda f: f.key)


def draw(formulations: list[Formulation], seed: int = SEED, size: int = SIZE) -> list[Formulation]:
    """Up to half the sample scored wrong, the rest scored right, in shuffled order."""
    rng = random.Random(seed)
    wrong = [f for f in formulations if not f.scored_right]
    right = [f for f in formulations if f.scored_right]
    picked = rng.sample(wrong, min(size // 2, len(wrong)))
    picked += rng.sample(right, min(size - len(picked), len(right)))
    rng.shuffle(picked)
    return picked


# ---- the packet and its sheet ---------------------------------------------------------


def packet(run: ScoredRun, sample: list[Formulation]) -> str:
    lines = [
        f"# Blind grading: `{run.name}`",
        "",
        f"{len(sample)} models of word problems, drawn at random (seed {SEED}, `python -m "
        f"opt_agent.blind_grading {run.directory}`). For each, decide whether the model says "
        "what the text says, and write `right`, `wrong` or `unsure` in the `grade` column of "
        "`grades.csv`, with a note if it helps. Then run "
        f"`python -m opt_agent.report {run.directory}`.",
        "",
        "- **right**: a correct model of the text, under any reading the text supports. "
        "Names, the order of terms, and equivalent forms (x <= 3y written as x - 3y <= 0) "
        "don't matter.",
        "- **wrong**: some part doesn't say what the text says: the objective, a constraint, "
        "a number, a direction, or whole numbers vs fractions.",
        "- **unsure**: you can't decide.",
        "",
        "The reference is the dataset's annotation, with the problem's integrality label. It's "
        "usually right, but it can be wrong or be one of several readings: grade against the "
        "text.",
        "",
        "Answers, scores, conditions and problem ids are left out on purpose. Until you're "
        "done, please don't open the run's files, its report, or `review/taxonomy/`, which "
        "lists the wrong answers.",
        "",
    ]
    for number, f in enumerate(sample, 1):
        record = run.by_id[f.problem_id]
        lines += [
            f"## {number}.",
            "",
            f"> {record.document}",
            "",
            "Reference:",
            "```",
            *format_model(reference_model(record)),
            "```",
            "",
            *_either(record),
            "To grade:",
            "```",
            *format_model(f.model),
            "```",
            "",
        ]
    return "\n".join(lines)


def _either(record) -> list[str]:
    if record.integrality.kind != "either":
        return []
    return ["(Its label is `either`: the text supports whole-number and fractional "
            "decisions alike.)", ""]  # fmt: skip


def sheet_path(run_name: str) -> Path:
    return BLIND_GRADING_DIR / run_name / "grades.csv"


def grade_sheet(sample: list[Formulation], path: Path) -> None:
    kept = kept_marks(path, "key", MARKS)
    with path.open("w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["number", "key", *MARKS])
        for number, f in enumerate(sample, 1):
            mark = kept.get(f.key, dict.fromkeys(MARKS, ""))
            writer.writerow([number, f.key, *(mark[c] for c in MARKS)])


def read_grades(path: Path) -> dict[str, tuple[str, str]]:
    """Key -> (the owner's grade, note). Every row must be graded."""
    grades = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            grade = row["grade"].strip().lower()
            if grade not in GRADES:
                raise ValueError(f"row {row['number']}: {grade!r} is none of {', '.join(GRADES)}")
            grades[row["key"]] = (grade, row["note"].strip())
    return grades


# ---- what the report gives ------------------------------------------------------------


def agreement(formulations: list[Formulation], grades: dict[str, tuple[str, str]]) -> dict:
    """Per stratum, how many grades agree with the score, with a 95% Wilson interval.
    "unsure" is counted but kept out of the rate, which is about decided grades."""
    by_key = {f.key: f for f in formulations}
    unknown = sorted(set(grades) - set(by_key))
    if unknown:
        raise ValueError(f"grades for models that aren't in this run's pool: {unknown}")
    strata = {}
    for scored_right, name in ((True, "scored right"), (False, "scored wrong")):
        mine = [g for k, (g, _) in grades.items() if by_key[k].scored_right is scored_right]
        counts = Counter(mine)
        agree = counts["right" if scored_right else "wrong"]
        n = counts["right"] + counts["wrong"]
        strata[name] = {"graded right": counts["right"], "graded wrong": counts["wrong"],
                        "unsure": counts["unsure"], "agree": agree, "n": n,
                        "wilson95": list(wilson(agree, n))}  # fmt: skip
    disagreements = [
        {"problem_id": by_key[k].problem_id, "key": k, "graded": g, "note": note,
         "scored": "right" if by_key[k].scored_right else "wrong"}
        for k, (g, note) in grades.items()
        if g != "unsure" and (g == "right") != by_key[k].scored_right
    ]  # fmt: skip
    disagreements.sort(key=lambda d: (d["problem_id"], d["key"]))
    return {"strata": strata, "disagreements": disagreements}


def summary(run: ScoredRun) -> dict:
    path = sheet_path(run.name)
    if not path.exists():
        return {"pending": f"no packet yet: python -m opt_agent.blind_grading {run.directory}"}
    try:
        grades = read_grades(path)
    except ValueError as unfilled:
        return {"pending": f"grades.csv isn't filled in yet ({unfilled})"}
    return {"graders": graders(path), **agreement(pool(run), grades)}


def write_packet(run_dir: Path, size: int = SIZE) -> tuple[Path, int]:
    run = load(run_dir)
    sample = draw(pool(run), size=size)
    out = sheet_path(run.name).parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "PACKET.md").write_text(packet(run, sample))
    grade_sheet(sample, sheet_path(run.name))
    return out, len(sample)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The blind-grading packet for one run.")
    parser.add_argument("run_dir", type=Path, help="a directory evaluate.py wrote")
    parser.add_argument("--size", type=int, default=SIZE, help=f"default: {SIZE}")
    parser.add_argument(
        "--merge",
        type=Path,
        metavar="REPLY",
        help="a judge's reply (number,grade,note) to write into grades.csv",
    )
    parser.add_argument("--grader", help="with --merge: who graded, e.g. a model and version")
    args = parser.parse_args(argv)
    if args.merge:
        if not args.grader:
            parser.error("--merge needs --grader")
        sheet = sheet_path(load(args.run_dir).name)
        n = merge_reply(sheet, args.merge, ["grade", "note"], args.grader)
        print(f"merged {n} grades from {args.merge} into {sheet}")
        return
    out, n = write_packet(args.run_dir, args.size)
    print(f"wrote {out}/PACKET.md and grades.csv ({n} models)")


if __name__ == "__main__":
    main()
