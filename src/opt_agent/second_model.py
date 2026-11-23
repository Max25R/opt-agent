"""The second-model study's runner (docs/SECOND_MODEL_PREREGISTRATION.md, sections 3 and 6, and
Amendment 1).

Two stages, each one call per problem with Claude Sonnet 5.5 (MODEL, sample 0), through the
follow-up's own per-item code (evaluate.run_item), so the requests are the follow-up's but for
the model, and the solving, the checks and the recorded items are the follow-up's:
- **Stage 1,** the study as registered: single-shot. Its pair is Claude Haiku 5.5's single-shot
  sample 0 in the follow-up's test run (HAIKU_RECORD), already recorded.
- **Stage 2** (Amendment 1): the no-solver baseline, as in the follow-up. It starts only once
  stage 1 has settled all its problems (stage_complete).
Problems run in the follow-up's order (followup.in_run_order) in each stage, so the first
CHECKPOINT of them are a fixed, pre-registered sample. No call is made for Haiku.

The cost guard, per stage (Stage.cap_usd):
- **A hard cap** of actual spend, kept by budget.BudgetedClient over one ledger for both
  stages: stage 1's is $11.00, stage 2's is $13.50 for both stages together. Before each call
  the budget reserves the call's worst case (all of max_tokens), so the spend can't pass it.
- **A checkpoint,** before the first call after a stage's first CHECKPOINT problems: the
  projected total is what the earlier stages' answers cost plus the mean cost of this stage's
  answers among those problems times the number of problems (cost_usd, from token counts,
  never from whether anything is right). Over the stage's cap, the run stops there. A resume
  recomputes it from the same recorded items, so it stops again.

One run directory holds everything: manifest.json (the problems, the model, the stages and
their caps and settings hashes, the checkpoint and the freeze's digest; a resume with any of
them changed is refused), results.jsonl (one item line per call, and a checkpoint line each
time a pass gets there), attempts.jsonl, the cache and the spend ledger. A re-run resumes:
settled problems are skipped, and every call that succeeded replays from the cache for free.
An errored call (an API error that outlasted the retries) is re-run on resume, as Amendment 1
of the M6 pre-registration says, until it has errored on the first pass and 3 resume passes;
then it stays errored, which the analysis reads as no answer.

A run reads the problems only when the study's tag exists and holds the approved inputs, and
the inputs here are those (second_model_freeze.ready). A rebuild in the tag's own tree, which
has no git, reads them on the approval alone (inputs(tag=False): second_model_freeze.check).

Run:  python -m opt_agent.second_model --plan           # calls left and the worst cases; no calls
      OPT_AGENT_LIVE=1 python -m opt_agent.second_model  # THE OWNER'S paid run: both stages
"""

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

import anthropic

from opt_agent import baseline, evaluate, followup, followup_report, formulate, pricing
from opt_agent.api import Cache, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.evaluate import Condition, Item
from opt_agent.runs import REPO_ROOT, Run, Tags

SPLIT = "second-model"
RUN_DIR = REPO_ROOT / "runs" / "second-model"
MODEL = "claude-sonnet-5-5"
CONDITION: Condition = "single-shot"  # stage 1's, and S1's
BASELINE: Condition = "baseline"  # stage 2's (Amendment 1)
SAMPLE = 0  # Sonnet's one sample: the plain request (unsalted cache key), as Haiku's sample 0
HAIKU_MODEL = formulate.DEFAULT_MODEL  # the paired answers' model, claude-haiku-5-5
HAIKU_RECORD = REPO_ROOT / "runs" / "followup-test" / "results.jsonl"  # section 2
HAIKU_SAMPLE = 0  # section 2: the pair of each Sonnet answer, in either condition


class Stage(NamedTuple):
    number: int
    condition: Condition
    cap_usd: float  # actual spend, never passed: stage 2's counts both stages


STAGES = (Stage(1, CONDITION, 11.00), Stage(2, BASELINE, 13.50))  # Amendment 1's caps
CHECKPOINT = 10  # section 6: problems, in run order, before a stage's projection
PROBLEMS = 121  # the follow-up's unexposed test problems (section 2)
RESUME_PASSES = 3  # the first pass and 3 resumes, then an error is final
MAX_ERRORS_IN_A_ROW = evaluate.MAX_ERRORS_IN_A_ROW


class ProjectionTooHigh(RunStopped):
    """A checkpoint projects a total over the stage's cap: the run stops before calling more."""


class StageOneIncomplete(RunStopped):
    """Stage 2 was asked to run before stage 1 had settled every problem (Amendment 1)."""


def select(found: list[followup.Problem]) -> list[followup.Problem]:
    """The 121 unexposed scorable problems, in the follow-up's run order."""
    exposed = followup_report.exposed_labels()
    chosen = [p for p in found if p.scorable and p.id not in exposed]
    if len(chosen) != PROBLEMS:
        raise ValueError(f"expected {PROBLEMS} unexposed scorable problems, found {len(chosen)}")
    return followup.in_run_order(followup.TEST_SPLIT, chosen)


def inputs(tag: bool = True) -> tuple[list[followup.Problem], str]:
    """The problems and the freeze's digest, only on the frozen inputs. With `tag` (a run),
    the tag must exist and hold them too; without it (a rebuild in the tag's own tree), the
    approval alone."""
    from opt_agent import second_model_freeze  # here: it imports this module

    digest = second_model_freeze.ready() if tag else second_model_freeze.check()
    return select(followup.read_test()), digest


def manifest(records: list[followup.Problem], digest: str) -> dict:
    stages = [{"stage": s.number, "condition": s.condition, "cap_usd": s.cap_usd,
               "settings_sha256": evaluate.settings_sha256(s.condition, MODEL)}
              for s in STAGES]  # fmt: skip
    return {
        "split": SPLIT,
        "problems": [r.id for r in records],
        "sample": SAMPLE,
        "model": MODEL,
        "stages": stages,
        "checkpoint": CHECKPOINT,
        "freeze": digest,
    }


def fix_manifest(out: Path, wanted: dict) -> None:
    path = out / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != wanted:
        raise ValueError(f"{path} describes another run (problems, model, stages, caps, "
                         "checkpoint or freeze); use a new run directory")  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(wanted, indent=1) + "\n")


def lines(out: Path) -> dict[tuple[str, str], list[dict]]:
    """Every item line so far, per problem and condition, in order."""
    found: dict[tuple[str, str], list[dict]] = {}
    results = out / "results.jsonl"
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            found.setdefault((entry["problem_id"], entry["condition"]), []).append(entry)
    return found


def settled(entries: list[dict]) -> bool:
    """A call needs no more tries: it's done, or it has errored on every allowed pass."""
    return any(e["outcome"] == "done" for e in entries) or len(entries) >= 1 + RESUME_PASSES


def stage_complete(out: Path, records: list[followup.Problem], stage: Stage) -> bool:
    """Every problem's call in `stage` is settled."""
    found = lines(out)
    return all(settled(found.get((r.id, stage.condition), [])) for r in records)


def projection(records: list[followup.Problem], found: dict, stage: Stage) -> dict:
    """A checkpoint's numbers: what the earlier stages' answers cost; among this stage's first
    CHECKPOINT problems, the answers so far (a done item, right or wrong) and their cost; and
    the projected total, the earlier stages plus this stage's mean times every problem (None
    with no answer to project from). Token counts only: nothing here is scored."""
    earlier = {s.condition for s in STAGES if s.number < stage.number}
    before = sum(entries[-1]["cost_usd"] for (_, condition), entries in found.items()
                 if condition in earlier)  # fmt: skip
    latest = [found[r.id, stage.condition][-1] for r in records[:CHECKPOINT]
              if found.get((r.id, stage.condition))]  # fmt: skip
    done = [e for e in latest if e["outcome"] == "done"]
    cost = sum(e["cost_usd"] for e in done)
    projected = before + cost / len(done) * len(records) if done else None
    return {"earlier_usd": before, "answered": len(done), "cost_usd": cost,
            "projected_usd": projected}  # fmt: skip


def checkpoint(out: Path, records: list[followup.Problem], stage: Stage, cap: float) -> None:
    """Record the projection, and raise ProjectionTooHigh if it's over `cap` (or there's
    nothing to project from)."""
    numbers = projection(records, lines(out), stage)
    projected = numbers["projected_usd"]
    stop = projected is None or projected > cap
    evaluate._append(out / "results.jsonl", {
        "kind": "checkpoint", "time": evaluate._now(), "stage": stage.number,
        "problems": CHECKPOINT, **numbers, "cap_usd": cap,
        "decision": "stop" if stop else "continue",
    })  # fmt: skip
    if stop:
        why = ("no answer among them to project from" if projected is None
               else f"they project ${projected:.2f} in all, over the ${cap:.2f} cap")  # fmt: skip
        raise ProjectionTooHigh(f"stage {stage.number}, after its first {CHECKPOINT} "
                                f"problems: {why}")  # fmt: skip


def run(
    client: anthropic.Anthropic,
    out: Path = RUN_DIR,
    records: list[followup.Problem] | None = None,
    digest: str | None = None,
    stage: Stage = STAGES[0],
    cap: float | None = None,
    limit: int | None = None,
) -> list[Item]:
    """Every problem not yet settled in `stage`, in order; returns the items this pass added.
    Stage 2 refuses to start before stage 1 is complete. `records` and `digest` are for tests
    (fake problems, no freeze) and for a replay, which also passes `limit`: only the first
    `limit` problems, as many as the committed run reached. `cap` (the stage's, unless a test
    sets another) is what the checkpoint compares with; the budget keeps the hard cap."""
    if records is None:
        records, digest = inputs()
    fix_manifest(out, manifest(records, digest or "unfrozen (a test)"))
    if stage.number > 1 and not stage_complete(out, records, STAGES[0]):
        raise StageOneIncomplete("stage 1 hasn't settled every problem, so stage 2 can't start")
    before = lines(out)
    session = Run.start(log_path=out / "attempts.jsonl", cache=Cache(out / "cache", SAMPLE),
                        fingerprint=digest, stage=stage.number)  # fmt: skip
    added: list[Item] = []
    errors_in_a_row, checked = 0, False
    try:
        for index, record in enumerate(records[:limit]):
            if settled(before.get((record.id, stage.condition), [])):
                continue
            if index >= CHECKPOINT and not checked:
                checked = True
                checkpoint(out, records, stage, stage.cap_usd if cap is None else cap)
            tags = Tags(problem_id=record.id, split=SPLIT, condition=stage.condition)
            item = evaluate.run_item(record, stage.condition, client, session, tags, MODEL)
            evaluate._append(out / "results.jsonl", item.model_dump(mode="json"))
            added.append(item)
            errors_in_a_row = errors_in_a_row + 1 if item.outcome == "errored" else 0
            if errors_in_a_row >= MAX_ERRORS_IN_A_ROW:
                raise RunStopped(f"{errors_in_a_row} API errors in a row: {item.reason}")
    except RunStopped as stop:
        stopped = {"kind": "stopped", "time": evaluate._now(), "stage": stage.number,
                   "reason": str(stop)}  # fmt: skip
        evaluate._append(out / "results.jsonl", stopped)
        raise
    return added


def request(record: followup.Problem, stage: Stage) -> dict:
    """The stage's request for a problem, as run_item builds it."""
    module = baseline if stage.condition == BASELINE else formulate
    return module.build_request(record.document, MODEL)


def plan(records: list[followup.Problem], out: Path = RUN_DIR) -> list[tuple[Stage, int, float]]:
    """Per stage: calls left and the worst case in USD, every unsettled problem's request at
    its full size with a reply that uses all of max_tokens."""
    before, found = lines(out), []
    for stage in STAGES:
        left = [r for r in records if not settled(before.get((r.id, stage.condition), []))]
        found.append((stage, len(left),
                      sum(pricing.worst_case_usd(request(r, stage)) for r in left)))  # fmt: skip
    return found


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The second-model study's runner.")
    parser.add_argument("--out", type=Path, default=RUN_DIR)
    parser.add_argument("--plan", action="store_true", help="the worst cases; no calls")
    args = parser.parse_args(argv)
    records, digest = inputs()  # the tag, the approval and these inputs, or FreezeError
    rows = plan(records, args.out)
    print(f"{len(records)} problems, {MODEL}: {sum(calls for _, calls, _ in rows)} calls left.")
    for stage, calls, worst in rows:
        print(f"  stage {stage.number} ({stage.condition}): {calls} calls left, worst case "
              f"${worst:.2f} if every reply used all of max_tokens; hard cap "
              f"${stage.cap_usd:.2f}{' for both stages' if stage.number > 1 else ''}, and a "
              f"stop after its first {CHECKPOINT} problems if they project more")  # fmt: skip
    if args.plan:
        return
    try:
        api_key = get_api_key()
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    ledger = args.out / "spend.jsonl"
    for stage in STAGES:
        client = BudgetedClient(anthropic.Anthropic(api_key=api_key),
                                Budget(stage.cap_usd, ledger))  # fmt: skip
        if stage.number > 1 and not stage_complete(args.out, records, STAGES[0]):
            sys.exit("Stage 1 isn't complete: a call still has resume passes left. Run this "
                     "again to retry it; stage 2 starts once stage 1 is complete.")  # fmt: skip
        try:
            added = run(client, args.out, records, digest, stage)  # type: ignore[arg-type]  # BudgetedClient wraps one
        except RunStopped as stop:
            sys.exit(f"stopped in stage {stage.number}: {stop}. Spent "
                     f"${client.budget.spent_usd:.4f} in all. Running it again resumes; "
                     "finished calls replay for free.")  # fmt: skip
        print(f"stage {stage.number}: {len(added)} calls this pass; spent "
              f"${client.budget.spent_usd:.4f} in all")  # fmt: skip
    print("Then: python -m opt_agent.second_model_report")


if __name__ == "__main__":
    main()
