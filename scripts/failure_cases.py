"""The wrong answers that docs/analysis/failure_types.md classifies, each with the model behind it.

Every wrong answer of the solver conditions (M6: single-shot and self-correction on runs/test
and runs/test-perturbed; the follow-up: single-shot, self-correction and checklist revision on
runs/followup-test) is run again through its study's frozen pipeline, in the tag's own tree
(opt_agent.frozen, as in scripts/reproduce.py), with a client that refuses every request. So
the model is the one the cached replies give, and the answer must equal the committed one.

The output holds problem text (licensed data, DATA_NOTICE.md), so it goes to a git-ignored
folder: review/failure_types/cases.jsonl, one line per wrong answer.

Run:  python scripts/failure_cases.py   # no key, no API calls; about a minute
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review" / "failure_types" / "cases.jsonl"
RUN_FILES = ("manifest.json", "results.jsonl", "attempts.jsonl", "spend.jsonl")
STUDIES = {  # study -> (tag, runs)
    "m6": ("m6-freeze", ("runs/test", "runs/test-perturbed")),
    "followup": ("followup-freeze", ("runs/followup-test",)),
}
LLM4OR = "data/external/llm4or-clean"
INDUSTRYOR = ROOT / LLM4OR / "IndustryOR.jsonl"


class NotInCache(Exception):
    """Not an anthropic.APIError, so the pipeline can't treat it as a failed call."""


class RefusingClient:
    def __init__(self):
        self.messages = self

    def with_options(self, **options) -> "RefusingClient":
        return self

    def create(self, **request):
        raise NotInCache("a request wasn't in the run's cache: this never calls the API")


def jsonable(x):
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    if hasattr(x, "model_dump"):
        return x.model_dump(mode="json")
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    return str(x)


def replay(item, document: str, session, **extra):
    """The pipeline again for one answer, from the cache; its answer must be the committed one."""
    from opt_agent import agent, evaluate
    from opt_agent.runs import Tags

    tags = Tags(problem_id=item.problem_id, split=item.split, condition=item.condition)
    result = agent.run(document, RefusingClient(), item.model_id, with_explanation=False,
                       max_attempts=evaluate.ATTEMPTS[item.condition], session=session,
                       tags=tags, **extra)  # fmt: skip
    s = result.solution
    status, objective = (s.status, s.objective) if result.confirmed else (None, None)
    if (status, objective) != (item.status, item.objective):
        raise SystemExit(
            f"{item.problem_id} {item.condition} {item.sample}: the replay gave "
            f"{status} {objective}, the run {item.status} {item.objective}"
        )
    f = result.formulation
    return result, {
        "attempts": len(result.outcome.attempts),
        "stopped": result.outcome.stopped,
        "no_answer": item.no_answer,
        "reply_error": f.error,
        "model": jsonable(f.model),
        "attempt_models": [jsonable(a.formulation.model) for a in result.outcome.attempts],
        "dropped": jsonable(getattr(f, "dropped", None)),  # M6's code doesn't drop variables
    }


def m6_cases(run_dir: Path) -> list[dict]:
    from opt_agent import evaluate
    from opt_agent.api import Cache
    from opt_agent.ground_truth import readings, reference_model
    from opt_agent.runs import Run
    from opt_agent.scoring import score

    split = json.loads((run_dir / "manifest.json").read_text())["split"]
    records = {r.id: r for r in evaluate.scorable_records(split)}
    session = Run.start(cache=Cache(run_dir / "cache"))
    cases = []
    for item in evaluate.latest_items(run_dir / "results.jsonl"):
        if item.condition == "baseline" or item.outcome != "done":
            continue
        record = records[item.problem_id]
        if score(record, item.status, item.objective).correct:
            continue
        _, found = replay(item, record.document, session)
        cases.append({
            "study": "m6", "run": run_dir.name, "problem": item.problem_id,
            "condition": item.condition, "sample": getattr(item, "sample", 0),
            "loud": item.status is None, "status": item.status, "objective": item.objective,
            "accepted": [[r, jsonable(s)] for r, s in readings(record)],
            "accepted_lenient": [[r, jsonable(s)] for r, s in readings(record, lenient=True)],
            "reference_model": jsonable(reference_model(record)),
            "text": record.document, **found,
        })  # fmt: skip
    return cases


def followup_cases(run_dir: Path) -> list[dict]:
    from opt_agent import evaluate, followup, followup_report
    from opt_agent.api import Cache
    from opt_agent.runs import Run

    problems = {p.id: p for p in followup.load_test() if p.scorable}
    exposed = followup_report.exposed_labels()
    sessions = {}
    cases = []
    for item in evaluate.latest_items(run_dir / "results.jsonl"):
        if item.condition == "baseline" or item.outcome != "done":
            continue
        p = problems[item.problem_id]
        answer = followup_report.answer_of(item)
        if followup_report.is_right(p, answer):
            continue
        if item.sample not in sessions:
            sessions[item.sample] = Run.start(cache=Cache(run_dir / "cache", item.sample))
        revising = item.condition == "checklist-revision"
        result, found = replay(item, p.document, sessions[item.sample],
                               checklist_revision=revising)  # fmt: skip
        case = {
            "study": "followup", "run": run_dir.name, "problem": item.problem_id,
            "condition": item.condition, "sample": item.sample, "exposed": p.id in exposed,
            "loud": answer is None, "status": item.status, "objective": item.objective,
            "key": followup_report.key_of(p), "key_decimals": p.key_decimals,
            "text": p.document, **found,
        }  # fmt: skip
        if revising and item.revised:
            original = (item.original_status, item.original_objective)
            case["revision"] = {
                "kept": item.revision_kept,
                "original": list(original),
                "right_to_wrong": item.revision_kept and followup_report.is_right(p, original),
                "flags": jsonable(result.checklist_flags),
                "original_model": found["attempt_models"][0],
            }  # fmt: skip
        cases.append(case)
    return cases


def inside(study: str, runs: list[str], out: Path) -> None:
    make = m6_cases if study == "m6" else followup_cases
    with out.open("w") as f:
        for run in runs:
            for case in make(Path(run)):
                f.write(json.dumps(case) + "\n")


def question_types() -> dict[str, str]:
    """IndustryOR's own LP/IP/MIP tag, by label (line number), for the integrality type."""
    if not INDUSTRYOR.exists():
        return {}
    lines = INDUSTRYOR.read_text().splitlines()
    return {f"industryor:{i}": json.loads(line).get("question_type")
            for i, line in enumerate(lines, 1)}  # fmt: skip


def main() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from opt_agent.frozen import Tree

    OUT.parent.mkdir(parents=True, exist_ok=True)
    types = question_types()
    cases = []
    for study, (tag, runs) in STUDIES.items():
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree.extract(tag, Path(tmp) / "tree")
            for run in runs:
                tree.copy(*(f"{run}/{name}" for name in RUN_FILES), f"{run}/cache")
            if study == "followup":
                tree.copy(LLM4OR)
            tree.copy("scripts/failure_cases.py")
            tree.python("scripts/failure_cases.py", "--inside", study, "--out", "cases.jsonl",
                        *runs)  # fmt: skip
            for line in tree.read("cases.jsonl").decode().splitlines():
                case = json.loads(line)
                if case["problem"] in types:
                    case["question_type"] = types[case["problem"]]
                cases.append(case)
    OUT.write_text("".join(json.dumps(c) + "\n" for c in cases))
    print(f"{len(cases)} wrong answers -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inside", choices=sorted(STUDIES))
    parser.add_argument("--out", type=Path)
    parser.add_argument("runs", nargs="*")
    args = parser.parse_args()
    if args.inside:
        inside(args.inside, args.runs, args.out)
    else:
        main()
