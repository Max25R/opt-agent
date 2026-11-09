"""Amendment 5's rows (docs/amendments/amendment-5.md): external corroboration, exploratory.

The external key is LLM4OR's cleaned NL4Opt (docs/EXTERNAL_DATA.md): one answer per problem,
for the problems its authors kept after removing the ones they found in error. Its data
has no license, so it's git-ignored and must be fetched first. This script refuses data
whose hash isn't the recorded one.

- **The overlap:** cleaned problems matched to our test split by exact text (normalized as
  the cross-check does), and those of them we score.
- **Accuracy on the overlap,** per condition, against the LLM4OR key (its one answer, at the
  external cross-check's 1e-4; a null answer means no optimum) and, next to it, against our
  frozen key on the same problems (frozen scoring, unchanged).
- **Amendment 4's six answer-key errors:** which ones LLM4OR kept, and with what key.
- **The keys that differ:** every overlap problem whose LLM4OR answer is no answer our
  frozen key accepts, and which key each condition's answer matched.

Descriptive and exploratory: no tests, nothing scored differently, and the result of record
stays the pre-registered strict accuracy, 264/274 per condition. No API calls.

Run:  python scripts/amendment5.py   # prints the rows; eval_json.py writes them
"""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

from opt_agent import orlm
from opt_agent.external_check import verdict
from opt_agent.ground_truth import Record, answer
from opt_agent.report import rate
from opt_agent.run_results import ScoredRun, load
from opt_agent.solver import Status

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external" / "llm4or-clean"
SOURCE = {
    "repository": "https://github.com/LLM4OR/LLM4OR",
    "path": "static/clean_benchmarks/NL4Opt",
    "commit": "75962df5ddf531906fda76f8708c658114e63c0e",
    # SHA-256 of the sorted `shasum -a 256` list of the copied files (docs/EXTERNAL_DATA.md)
    "nl4opt_sha256": "ce544464946e83514bd73b2e82e9f3cb50d7d64076fc1c81e9e176d09e5e88c8",
}
TOLERANCE = orlm.MATCH_TOLERANCE  # 1e-4: published values can be rounded
AGREES = ("agrees", "agrees with another reading")  # external_check.verdict: an accepted answer
CONDITIONS = ("baseline", "single-shot", "self-correction")
RESULT_OF_RECORD = "pre-registered strict accuracy (sections 1, 4 and 5): 264/274 per condition"


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


amendment4 = _script("amendment4")


def available(data: Path = DATA) -> bool:
    return (data / "NL4Opt").is_dir()


def load_llm4or(data: Path = DATA) -> dict[str, tuple[str, float | None]]:
    """Problem folder -> (text, answer), after checking the data is the recorded copy."""
    files = sorted(p for p in (data / "NL4Opt").rglob("*") if p.is_file())
    listing = "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(data).as_posix()}\n"
        for p in files
    )
    if hashlib.sha256(listing.encode()).hexdigest() != SOURCE["nl4opt_sha256"]:
        raise ValueError(f"{data / 'NL4Opt'} isn't the copy docs/EXTERNAL_DATA.md records")
    problems = {}
    for folder in sorted((data / "NL4Opt").iterdir()):
        output = json.loads((folder / "sample.json").read_text())[0]["output"]
        problems[folder.name] = ((folder / "description.txt").read_text(), output[0])
    return problems


def overlap(run: ScoredRun, problems: dict) -> dict[str, tuple[str, float | None]]:
    """Our problem id -> (LLM4OR folder, its answer), for exact text matches. Every cleaned
    problem must match one of ours exactly, or the comparison would rest on guesses."""
    by_text = {orlm.normalize(r.document): r.id for r in run.by_id.values()}
    found, missing = {}, []
    for folder, (text, value) in problems.items():
        ours = by_text.get(orlm.normalize(text))
        if ours is None:
            missing.append(folder)
        else:
            found[ours] = (folder, value)
    if missing or len(found) != len(problems):
        raise ValueError(f"cleaned problems without one exact match in our split: {missing}")
    return found


def matches_llm4or(status: str | None, objective: float | None, value: float | None) -> bool:
    if status is None:
        return False  # no confirmed or parsed answer
    if value is None:
        return status != Status.OPTIMAL  # their null: no optimum
    return status == Status.OPTIMAL and math.isclose(
        objective, value, rel_tol=TOLERANCE, abs_tol=TOLERANCE
    )


def row(run: ScoredRun, data: Path = DATA) -> dict:
    if run.manifest.split != "test":
        raise ValueError("Amendment 5 covers the main test run only")
    problems = load_llm4or(data)
    matched = overlap(run, problems)
    shared = [i for i in run.manifest.problem_ids if i in matched]  # scored, in run order
    pairs = {(p.problem_id, p.condition): p for p in run.pairs if p.state == "scored"}

    differing = [i for i in shared if _verdict(run.by_id[i], matched[i][1]) not in AGREES]
    by_condition = {}
    for c in CONDITIONS:
        theirs = {i: _matches(pairs[(i, c)], matched[i][1]) for i in shared}
        ours = {i: pairs[(i, c)].score.correct for i in shared}
        by_condition[c] = {
            "LLM4OR key": rate(sum(theirs.values()), len(shared)),
            "our frozen key": rate(sum(ours.values()), len(shared)),
            "wrong against the LLM4OR key": _why_wrong(
                [i for i in shared if not theirs[i]], ours, differing, pairs, c
            ),
        }

    items = [_differing(run.by_id[i], matched[i], pairs) for i in differing]
    return {
        "label": "exploratory, post hoc: external corroboration (Amendment 5, draft); "
        "descriptive, no tests",
        "result of record": RESULT_OF_RECORD,
        "source": {**SOURCE, "tolerance": TOLERANCE},
        "overlap": {
            "cleaned problems": len(problems),
            "matched exactly": len(matched),
            "scorable": len(shared),
            "matched but not scorable": sorted(i for i in matched if i not in shared),
            "scorable but not in the cleaned set": len(run.manifest.problem_ids) - len(shared),
        },
        "by condition": by_condition,
        "amendment 4 key errors": _key_errors(run, matched),
        "differing keys": {
            "n": len(items),
            "kinds": {
                k: sum(x["kind"] == k for x in items) for k in sorted({x["kind"] for x in items})
            },
            "each condition matched": {
                c: {
                    which: sum(x["matched"][c] == which for x in items)
                    for which in ("our key", "the LLM4OR key", "neither")
                }
                for c in CONDITIONS
            },
            "items": items,
        },
    }


WHY = {
    "differing": "its key differs from ours, and the answer matched ours",
    "reading": "the answer matched a reading ours accepts and its one answer doesn't "
    "(strict, '=', or the other optimum of an `either` label)",
    "both": "wrong against both keys",
}


def _why_wrong(wrong: list[str], ours: dict, differing: list[str], pairs: dict, c: str) -> dict:
    """Why an answer that our frozen key accepts can still miss the LLM4OR key."""
    counts = {k: 0 for k in WHY}
    for i in wrong:
        if not ours[i]:
            counts["both"] += 1
        elif i in differing:
            counts["differing"] += 1
        else:  # their key is one our key accepts, but the answer matched another one
            counts["reading"] += 1
    return {WHY[k]: n for k, n in counts.items()}


def _matches(pair, value: float | None) -> bool:
    item = pair.item
    if item.outcome != "done":
        return False
    return matches_llm4or(item.status, item.objective, value)


def _verdict(record: Record, value: float | None) -> str:
    published = sorted(orlm.NO_SOLUTION_MARKERS)[0] if value is None else repr(float(value))
    return verdict(record, published)


def _show(status: str | None, objective: float | None) -> float | str | None:
    return objective if status == Status.OPTIMAL else status


def _differing(record: Record, found: tuple[str, float | None], pairs: dict) -> dict:
    folder, value = found
    ours = answer(record)
    matched, answers = {}, {}
    for c in CONDITIONS:
        pair = pairs[(record.id, c)]
        answers[c] = _show(pair.item.status, pair.item.objective)
        on_ours, on_theirs = pair.score.correct, _matches(pair, value)
        matched[c] = "our key" if on_ours else "the LLM4OR key" if on_theirs else "neither"
        if on_ours and on_theirs:
            matched[c] = "both"
    return {
        "problem_id": record.id,
        "llm4or folder": folder,
        "kind": _verdict(record, value),
        "label": record.integrality.kind,
        "our key": _show(ours.status.value, ours.objective),
        "LLM4OR key": value,
        "answers": answers,
        "matched": matched,
    }


def _key_errors(run: ScoredRun, matched: dict) -> dict:
    """Amendment 4's six: which LLM4OR removed, and the key of any it kept, next to our
    frozen key and the answer Amendment 4's corrected label accepts."""
    removed = [i for i in amendment4.KEY_ERRORS if i not in matched]
    kept = []
    for i in (i for i in amendment4.KEY_ERRORS if i in matched):
        record = run.by_id[i]
        fixed = (amendment4.corrected(record, amendment4.CORRECTED[i])
                 if i in amendment4.CORRECTED else None)  # fmt: skip
        kept.append({
            "problem_id": i,
            "LLM4OR key": matched[i][1],
            "our frozen key": answer(record).objective,
            "corrected label also accepts": fixed.strict.ip.objective if fixed else None,
            "LLM4OR key agrees with": "our frozen key"
            if _verdict(record, matched[i][1]) == "agrees" else "not our frozen key",
        })  # fmt: skip
    return {"removed by LLM4OR": removed, "kept": kept}


def main() -> None:
    new = row(load(ROOT / "runs" / "test"))
    o = new["overlap"]
    print(f"overlap: {o['scorable']} scorable of {o['matched exactly']} matched "
          f"({o['cleaned problems']} cleaned problems)")  # fmt: skip
    for c, r in new["by condition"].items():
        t, f = r["LLM4OR key"], r["our frozen key"]
        print(f"{c}: LLM4OR key {t['right']}/{t['n']}, our frozen key {f['right']}/{f['n']}")
    print(
        "Amendment 4 key errors removed by LLM4OR:",
        new["amendment 4 key errors"]["removed by LLM4OR"],
    )
    print(
        "differing keys:",
        new["differing keys"]["n"],
        new["differing keys"]["each condition matched"],
    )


if __name__ == "__main__":
    main()
