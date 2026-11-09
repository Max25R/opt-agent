"""Re-score a follow-up dev run from its cache, at $0: replay every pair through the current
pipeline (evaluate.run_item, same conditions and extras) with a client that refuses any call,
reading the original run's cache and writing a new run directory. Used after each dev revision
(docs/FOLLOWUP_DEV_LOG.md).

Run:  python scripts/rescore_dev.py runs/dev-checklist runs/dev-checklist-rev1
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from opt_agent import evaluate, followup
from opt_agent.api import Cache
from opt_agent.runs import Run, Tags

# Problems whose dev key is known to be wrong (docs/FOLLOWUP_DEV_LOG.md), and the answer
# that is right: they're reported both ways, never silently re-keyed.
KNOWN_KEY_ERRORS = {"82": 212.0}


class NoCalls:
    """Fails loudly if any request misses the cache: a re-score must cost nothing."""

    def with_options(self, **options):
        raise RuntimeError("a request missed the cache: the re-score would call the API")


def rescore(source: Path, out: Path) -> list[evaluate.Item]:
    manifest = evaluate.Manifest.model_validate_json((source / "manifest.json").read_text())
    extras = tuple(x for x in ("estimate", "checklist") if x in manifest.settings)
    problems = {p.id: p for p in followup.load(manifest.split)}
    out.mkdir(parents=True, exist_ok=False)
    (out / "manifest.json").write_text(manifest.model_dump_json(indent=1) + "\n")
    session = Run.start(log_path=out / "attempts.jsonl", cache=Cache(source / "cache"),
                        rescored_from=str(source))  # fmt: skip
    items = []
    for pid in manifest.problem_ids:
        for condition in manifest.conditions:
            tags = Tags(problem_id=pid, split=manifest.split, condition=condition)
            item = evaluate.run_item(problems[pid], condition, NoCalls(), session, tags,
                                     manifest.model_id, extras)  # fmt: skip
            items.append(item)
            with (out / "results.jsonl").open("a") as f:
                f.write(json.dumps(item.model_dump(mode="json")) + "\n")
    return items


def summary(items: list[evaluate.Item], problems: dict) -> str:
    lines = []
    for keyed in (False, True):
        right = [i for i in items if _right(i, problems[i.problem_id], keyed)]
        flagged = [i for i in right if i.checklist_flags]
        low = [i for i in right if i.low_confidence]
        name = "truly right (the known key errors fixed)" if keyed else "right by the key"
        lines.append(f"{name}: {len(right)}; checklist flags on {len(flagged)} "
                     f"({sorted(i.problem_id for i in flagged)}), "
                     f"{sum(len(i.checklist_flags) for i in flagged)} flags; low confidence on "
                     f"{len(low)} ({sorted(i.problem_id for i in low)})")  # fmt: skip
    kinds = Counter(f["kind"] for i in items for f in (i.checklist_flags or []))
    lines.append(f"flags by kind, every pair: {dict(kinds)}")
    return "\n".join(lines)


def _right(item, problem, fix_known_keys: bool) -> bool:
    if fix_known_keys and problem.id in KNOWN_KEY_ERRORS:
        problem = problem.model_copy(update={"answer": KNOWN_KEY_ERRORS[problem.id]})
    return followup.is_correct(problem, item.status, item.objective)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Re-score a dev run from its cache, at $0.")
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    items = rescore(args.source, args.out)
    manifest = json.loads((args.source / "manifest.json").read_text())
    print(summary(items, {p.id: p for p in followup.load(manifest["split"])}))


if __name__ == "__main__":
    main()
