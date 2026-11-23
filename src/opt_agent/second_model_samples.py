"""The second-model samples study's runner (docs/second_model/SAMPLES_PREREGISTRATION.md,
sections 3 and 6).

Two more single-shot answers per problem from Claude Sonnet 5.5 (MODEL), samples 1 and 2, on
the second-model study's 121 problems, sent the way the follow-up sent Claude Haiku 5.5's
samples 1 and 2 (evaluate.evaluate): the request Sonnet's sample 0 was sent, which is Haiku's
but for the model (formulate.build_request), through the follow-up's per-item code
(evaluate.run_item), one session per sample in one pass, each with the cache key
salted by its sample (Cache(dir, sample)), so a sample never replays another's reply. Each
problem runs sample 1, then sample 2, before the next problem starts, as the follow-up ran its
samples, in the follow-up's run order (second_model.select), so the first CHECKPOINT problems
are a fixed, pre-registered sample. No call is made for Haiku, and Sonnet's sample 0 is the
second-model study's (runs/second-model, which this never writes to).

The cost guard:
- **A hard cap** of actual spend, CAP_USD, kept by budget.BudgetedClient over the run's
  ledger: before each call it reserves the call's worst case (all of max_tokens), so the spend
  can't pass it.
- **A checkpoint,** before the first call after the first CHECKPOINT problems: the projected
  total is the mean cost of the answers among those problems' calls times every call of the
  run (cost_usd, from token counts, never from whether anything is right). Over the cap, the
  run stops there. A resume recomputes it from the same recorded items, so it stops again.

One run directory holds everything: manifest.json (the problems, the model, the samples, the
cap, the checkpoint and the freeze's digest; a resume with any of them changed is refused),
results.jsonl (one item line per call, and a checkpoint line each time a pass gets there),
attempts.jsonl, the cache and the spend ledger. A re-run resumes: settled calls are skipped,
and every call that succeeded replays from the cache for free. An errored call (an API error
that outlasted the retries) is re-run on resume, as Amendment 1 of the M6 pre-registration
says, until it has errored on the first pass and 3 resume passes (second_model.settled); then
it stays errored, which the analysis reads as no answer.

A run reads the problems only when the study's tag exists and holds the approved inputs, and
the inputs here are those (second_model_samples_freeze.ready). A rebuild in the tag's own tree,
which has no git, reads them on the approval alone (inputs(tag=False)).

Run:  python -m opt_agent.second_model_samples --plan           # calls left, worst case; no calls
      OPT_AGENT_LIVE=1 python -m opt_agent.second_model_samples  # THE OWNER'S paid run
"""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import anthropic

from opt_agent import evaluate, followup, formulate, pricing, second_model
from opt_agent.api import Cache, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.evaluate import Item
from opt_agent.runs import REPO_ROOT, Run, Tags

SPLIT = "second-model-samples"
RUN_DIR = REPO_ROOT / "runs" / "second-model-samples"
MODEL = second_model.MODEL  # claude-sonnet-5-5
CONDITION = second_model.CONDITION  # single-shot
SAMPLES = (1, 2)  # Sonnet's sample 0 is the second-model study's
SONNET_RECORD = second_model.RUN_DIR / "results.jsonl"  # its sample 0 (section 2)
HAIKU_MODEL = second_model.HAIKU_MODEL  # claude-haiku-5-5
HAIKU_RECORD = second_model.HAIKU_RECORD  # the follow-up's test run (section 2)
HAIKU_SAMPLES = (0, 1, 2)
CAP_USD = 7.00  # section 6: actual spend, never passed
CHECKPOINT = 10  # section 6: problems, in run order, whose calls project the total
MAX_ERRORS_IN_A_ROW = evaluate.MAX_ERRORS_IN_A_ROW


class ProjectionTooHigh(RunStopped):
    """The checkpoint projects a total over the cap: the run stops before calling more."""


def inputs(tag: bool = True) -> tuple[list[followup.Problem], str]:
    """The problems and the freeze's digest, only on the frozen inputs. With `tag` (a run),
    the tag must exist and hold them too; without it (a rebuild in the tag's own tree), the
    approval alone."""
    from opt_agent import second_model_samples_freeze  # here: it imports this module

    freeze = second_model_samples_freeze
    digest = freeze.ready() if tag else freeze.check()
    return second_model.select(followup.read_test()), digest


def calls(records: list[followup.Problem]) -> list[tuple[int, followup.Problem, int]]:
    """Every call in run order: (the problem's place, the problem, the sample)."""
    return [(index, record, sample) for index, record in enumerate(records) for sample in SAMPLES]


def manifest(records: list[followup.Problem], digest: str) -> dict:
    return {
        "split": SPLIT,
        "problems": [r.id for r in records],
        "model": MODEL,
        "condition": CONDITION,
        "samples": list(SAMPLES),
        "settings_sha256": evaluate.settings_sha256(CONDITION, MODEL),
        "cap_usd": CAP_USD,
        "checkpoint": CHECKPOINT,
        "freeze": digest,
    }


def fix_manifest(out: Path, wanted: dict) -> None:
    path = out / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != wanted:
        raise ValueError(f"{path} describes another run (problems, model, samples, cap, "
                         "checkpoint or freeze); use a new run directory")  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(wanted, indent=1) + "\n")


def lines(out: Path) -> dict[tuple[str, int], list[dict]]:
    """Every item line so far, per problem and sample, in order."""
    found: dict[tuple[str, int], list[dict]] = {}
    results = out / "results.jsonl"
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            found.setdefault((entry["problem_id"], entry["sample"]), []).append(entry)
    return found


def complete(out: Path, records: list[followup.Problem]) -> bool:
    """Every call of the run is settled (second_model.settled)."""
    found = lines(out)
    return all(second_model.settled(found.get((r.id, s), [])) for _, r, s in calls(records))


def projection(records: list[followup.Problem], found: dict) -> dict:
    """The checkpoint's numbers: among the first CHECKPOINT problems' calls, the answers so far
    (a done item, right or wrong) and their cost, and the projected total, their mean cost
    times every call of the run (None with no answer to project from). Token counts only:
    nothing here is scored."""
    latest = [found[r.id, s][-1] for _, r, s in calls(records[:CHECKPOINT])
              if found.get((r.id, s))]  # fmt: skip
    done = [e for e in latest if e["outcome"] == "done"]
    cost = sum(e["cost_usd"] for e in done)
    every = len(records) * len(SAMPLES)
    projected = cost / len(done) * every if done else None
    return {"calls": every, "answered": len(done), "cost_usd": cost, "projected_usd": projected}


def checkpoint(out: Path, records: list[followup.Problem], cap: float) -> None:
    """Record the projection, and raise ProjectionTooHigh if it's over `cap` (or there's
    nothing to project from)."""
    numbers = projection(records, lines(out))
    projected = numbers["projected_usd"]
    stop = projected is None or projected > cap
    evaluate._append(out / "results.jsonl", {
        "kind": "checkpoint", "time": evaluate._now(), "problems": CHECKPOINT, **numbers,
        "cap_usd": cap, "decision": "stop" if stop else "continue",
    })  # fmt: skip
    if stop:
        why = ("no answer among them to project from" if projected is None
               else f"they project ${projected:.2f} in all, over the ${cap:.2f} cap")  # fmt: skip
        raise ProjectionTooHigh(f"after the first {CHECKPOINT} problems: {why}")


def run(
    client: anthropic.Anthropic,
    out: Path = RUN_DIR,
    records: list[followup.Problem] | None = None,
    digest: str | None = None,
    cap: float | None = None,
    limit: int | None = None,
) -> list[Item]:
    """Every call not yet settled, in run order; returns the items this pass added. `records`
    and `digest` are for tests (fake problems, no freeze) and for a replay, which also passes
    `limit`: only the first `limit` calls in run order, as many as the committed run reached.
    `cap` (CAP_USD, unless a test sets another) is what the checkpoint compares with; the
    budget keeps the hard cap."""
    if records is None:
        records, digest = inputs()
    fix_manifest(out, manifest(records, digest or "unfrozen (a test)"))
    before = lines(out)
    first = Run.start(log_path=out / "attempts.jsonl", cache=Cache(out / "cache", SAMPLES[0]),
                      fingerprint=digest)  # fmt: skip
    # One pass, one run_id and one log; each sample reads and writes its own cache entries,
    # as evaluate.evaluate ran Haiku's samples.
    sessions = {s: replace(first, cache=Cache(out / "cache", s)) for s in SAMPLES}
    added: list[Item] = []
    errors_in_a_row, checked = 0, False
    try:
        for index, record, sample in calls(records)[:limit]:
            if second_model.settled(before.get((record.id, sample), [])):
                continue
            if index >= CHECKPOINT and not checked:
                checked = True
                checkpoint(out, records, CAP_USD if cap is None else cap)
            tags = Tags(problem_id=record.id, split=SPLIT, condition=CONDITION)
            item = evaluate.run_item(record, CONDITION, client, sessions[sample], tags, MODEL)
            evaluate._append(out / "results.jsonl", item.model_dump(mode="json"))
            added.append(item)
            errors_in_a_row = errors_in_a_row + 1 if item.outcome == "errored" else 0
            if errors_in_a_row >= MAX_ERRORS_IN_A_ROW:
                raise RunStopped(f"{errors_in_a_row} API errors in a row: {item.reason}")
    except RunStopped as stop:
        stopped = {"kind": "stopped", "time": evaluate._now(), "reason": str(stop)}
        evaluate._append(out / "results.jsonl", stopped)
        raise
    return added


def plan(records: list[followup.Problem], out: Path = RUN_DIR) -> tuple[int, float]:
    """Calls left and the worst case in USD: every unsettled call's request at its full size
    with a reply that uses all of max_tokens."""
    before = lines(out)
    left = [r for _, r, s in calls(records) if not second_model.settled(before.get((r.id, s), []))]
    worst = sum(pricing.worst_case_usd(formulate.build_request(r.document, MODEL)) for r in left)
    return len(left), worst


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The second-model samples study's runner.")
    parser.add_argument("--out", type=Path, default=RUN_DIR)
    parser.add_argument("--plan", action="store_true", help="the worst case; no calls")
    args = parser.parse_args(argv)
    records, digest = inputs()  # the tag, the approval and these inputs, or FreezeError
    left, worst = plan(records, args.out)
    print(f"{len(records)} problems, {MODEL}, samples {' and '.join(map(str, SAMPLES))}: "
          f"{left} calls left, worst case ${worst:.2f} if every reply used all of max_tokens; "
          f"hard cap ${CAP_USD:.2f}, and a stop after the first {CHECKPOINT} problems if "
          "they project more")  # fmt: skip
    if args.plan:
        return
    try:
        api_key = get_api_key()
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    client = BudgetedClient(anthropic.Anthropic(api_key=api_key),
                            Budget(CAP_USD, args.out / "spend.jsonl"))  # fmt: skip
    try:
        added = run(client, args.out, records, digest)  # type: ignore[arg-type]  # BudgetedClient wraps one
    except RunStopped as stop:
        sys.exit(f"stopped: {stop}. Spent ${client.budget.spent_usd:.4f} in all. Running it "
                 "again resumes; finished calls replay for free.")  # fmt: skip
    print(f"{len(added)} calls this pass; spent ${client.budget.spent_usd:.4f} in all")
    if not complete(args.out, records):
        sys.exit("Not complete: an errored call still has resume passes left. Run this again "
                 "to retry it; finished calls replay for free.")  # fmt: skip
    print("Complete. Then: python -m opt_agent.second_model_samples_report")


if __name__ == "__main__":
    main()
