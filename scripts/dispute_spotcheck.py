"""docs/analysis/dispute_spotcheck.md: 10 of the follow-up's disputed problems, for a person.

An LLM judge (Claude) flagged some of the follow-up's wrong answers as answer-key disputes
(docs/analysis/failure_types.md): it found no error in the model. No person has verified any
of those flags. This draws 10 of the disputed problems at random, with a fixed seed, from the
list in id order, and writes, for each, the key as LLM4OR's file writes it, the answers the
judge flagged (from the committed run), and the judge's reason in one line, with an empty
column for a person's verdict. Exploratory and post hoc: nothing here changes a result.

The reasons are condensed from failure_types.csv's notes, one for each disputed problem (not
only the drawn ones), in this project's words; no problem text is quoted.

Needs LLM4OR's data for the keys (python scripts/fetch_llm4or.py). Run:
    python scripts/dispute_spotcheck.py
"""

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from opt_agent import followup

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "docs" / "analysis" / "failure_types.csv"
RUN = ROOT / "runs" / "followup-test" / "results.jsonl"
DOC = ROOT / "docs" / "analysis" / "dispute_spotcheck.md"
DISPUTE = "answer-key dispute"
SEED = 20261118  # the day it was drawn
SIZE = 10

REASONS = {
    "complexlp:63": "The key is two separate round trips (cities 1-4 and 2-3); the text asks "
    "for one tour, and the model's tour is the cheapest one.",
    "complexlp:78": "The key is two separate round trips (cities 1-2 and 3-4); the text asks "
    "for one tour, and the model's tour is the cheapest one.",
    "complexlp:81": "The key is two separate round trips (cities 1-3 and 2-4); the text asks "
    "for one tour, and the model's (1-2-4-3-1) is the cheapest.",
    "complexlp:83": "The key is two separate two-city loops; the text asks for one tour back "
    "to the start, and the model's tour is the cheapest one.",
    "complexlp:94": "The key is two separate round trips (A-B and C-D); the text asks for one "
    "tour, and the model's tour is the cheapest one.",
    "industryor:17": "A fixed-charge reading: setup costs only for the types made, and larger "
    "containers may serve smaller demand; the key makes every type for its own demand.",
    "industryor:22": "The model answers the text's first question (the most even split); the "
    "key answers its follow-up question, which adds a cap on one side.",
    "industryor:24": "The text states no objective: the model minimizes the number of trips, "
    "the key the total pollution.",
    "industryor:26": "The model charges storage on the required year-end stock too, a literal "
    "reading of the fee rule; the key is exactly that fee less.",
    "industryor:27": "Units: the model reads the nutrient contents per gram, as the text "
    "writes them; the key is exactly 1000 times its answer (per kilogram).",
    "industryor:28": "Integrality: the model keeps production in whole units, as IndustryOR's "
    "own MIP tag has it; the key is the continuous optimum.",
    "industryor:30": "No model error found, yet the key is about 1.01 million below the "
    "model's optimum: it needs a cost or limit the judge found nowhere in the text.",
    "industryor:41": "Integrality: the model keeps every quantity in whole units, as "
    "IndustryOR's own MIP tag has it; the key is the continuous optimum.",
}


def disputed_rows() -> list[dict]:
    with CSV.open() as f:
        return [
            r for r in csv.DictReader(f) if r["study"] == "followup" and r["primary"] == DISPUTE
        ]


def disputed() -> list[str]:
    """The follow-up's disputed problems, in id order (benchmark, then number)."""
    ids = {r["problem"] for r in disputed_rows()}
    return sorted(ids, key=lambda p: (p.split(":")[0], int(p.split(":")[1])))


def draw(pool: list[str]) -> list[str]:
    """The seeded draw, in draw order."""
    return random.Random(SEED).sample(pool, SIZE)


def keys() -> dict[str, str]:
    """Each follow-up problem's key as LLM4OR's file writes it (a ComplexLP row's id; an
    IndustryOR problem's line number, 1-based, as followup.load_sealed numbers them)."""
    found = {}
    for line in followup.COMPLEXLP.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            found[f"complexlp:{row['id']}"] = str(row["Answer"])
    for n, line in enumerate(followup.INDUSTRYOR.read_text().splitlines(), start=1):
        if line.strip():
            found[f"industryor:{n}"] = str(json.loads(line)["en_answer"])
    return found


def answers() -> dict[tuple[str, str, int], float | None]:
    """Each pair's answer in the committed run; a resumed pair's last record wins."""
    found = {}
    for line in RUN.read_text().splitlines():
        item = json.loads(line)
        if item.get("kind") == "item":
            found[(item["problem_id"], item["condition"], item["sample"])] = item["objective"]
    return found


def number(value: float | None) -> str:
    if value is None:
        return "no answer"
    if abs(value - round(value)) < 1e-9:
        return str(round(value))
    return f"{value:.6g}"


def count(n: int, thing: str) -> str:
    return f"{n} {thing}" if n == 1 else f"{n} {thing}s"


def our_answers(problem: str, rows: list[dict], run: dict) -> str:
    """The flagged answers' values, each with how many answers and models gave it."""
    by_value: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["problem"] == problem:
            by_value[number(run[(problem, r["condition"], int(r["sample"]))])].append(r)
    return "; ".join(f"{value} ({count(len(rs), 'answer')}, "
                     f"{count(len({r['model'] for r in rs}), 'model')})"
                     for value, rs in by_value.items())  # fmt: skip


def render() -> str:
    rows, pool = disputed_rows(), disputed()
    if set(pool) != set(REASONS):
        raise SystemExit(
            f"a reason is needed for each disputed problem: {sorted(set(pool) ^ set(REASONS))}"
        )
    key, run = keys(), answers()
    lines = [
        "# Answer-key disputes: a spot-check for a person",
        "",
        "*Exploratory and post hoc. Written by `python scripts/dispute_spotcheck.py`; please "
        "don't edit the table by hand, except the verdict column.*",
        "",
        f"An LLM judge (Claude) flagged {len(rows)} of the follow-up's wrong answers, on "
        f"{len(pool)} problems, as answer-key disputes "
        "([`failure_types.md`](failure_types.md)): it found no error in the model, so either "
        "the key is wrong or it rests on another reading of the text. **No person has verified "
        f"any of them.** Here are {SIZE} of the {len(pool)} problems, drawn at random (seed "
        f"{SEED}, from the {len(pool)} in id order; the table is in draw order), for a person "
        "to check. Nothing here changes a reported result: the raw keys are the result of "
        "record, as pre-registered (the key check 5b wasn't run: "
        "[`DEVIATIONS.md`](../followup/DEVIATIONS.md), deviation 2).",
        "",
        "**How to check one.** Fetch the problems with `python scripts/fetch_llm4or.py`. A "
        "ComplexLP problem is the row of `data/external/llm4or-clean/Mamo_complex_lp_clean.jsonl` "
        "whose `id` is its number (the text is `Question`, the key `Answer`); an IndustryOR "
        "problem is the line of `data/external/llm4or-clean/IndustryOR.jsonl` with its number, "
        "counting from 1 (`en_question`, `en_answer`). Claude's models come from a replay with "
        "no key, `python scripts/failure_cases.py` (into the git-ignored "
        "`review/failure_types/cases.jsonl`), and the judge's full notes are the problem's rows "
        "of [`failure_types.csv`](failure_types.csv). Write one verdict per problem: **key "
        "wrong**, **model wrong**, **both readings defensible** or **can't tell**.",
        "",
        "| # | Problem | Key, as written | Our flagged answers | Why it was flagged | Verdict |",
        "|---:|---|---:|---|---|---|",
    ]
    for n, problem in enumerate(draw(pool), start=1):
        lines.append(f"| {n} | `{problem}` | {key[problem]} | {our_answers(problem, rows, run)} "
                     f"| {REASONS[problem]} | |")  # fmt: skip
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    DOC.write_text(render())
    print(f"{DOC.relative_to(ROOT)}: {SIZE} problems")
