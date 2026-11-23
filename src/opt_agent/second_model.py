"""The second-model study's runner (docs/SECOND_MODEL_PREREGISTRATION.md, sections 3 and 6).

One call per problem: Claude Sonnet 5.5's single-shot answer (MODEL, sample 0), through the
follow-up's own per-item code (evaluate.run_item), so the request is the follow-up's but for
the model, and the solving, the checks and the recorded item are the follow-up's. Its pair is
Claude Haiku 5.5's single-shot sample 0 in the follow-up's test run (HAIKU_RECORD), already
recorded: this study makes no call for Haiku. Problems run in the follow-up's order
(followup.in_run_order), so the first CHECKPOINT of them are a fixed, pre-registered sample.

The cost guard (section 6) has two parts:
- **A hard cap,** CAP_USD of actual spend, kept by budget.BudgetedClient: before each call it
  reserves the call's worst case (all of max_tokens), so the spend can't pass the cap.
- **A checkpoint,** before the first call after the first CHECKPOINT problems: the projected
  total is the mean cost of the answers among those problems (cost_usd, from their token
  counts, never from whether they're right) times the number of problems. Over CAP_USD, the
  run stops there. A resume recomputes it from the same recorded items, so it stops again.

One run directory holds everything: manifest.json (the problems, the model, the settings hash,
the cap, the checkpoint and the freeze's digest; a resume with any of them changed is
refused), results.jsonl (one item line per call, and a checkpoint line each time a pass gets
there), attempts.jsonl, the cache and the spend ledger. A re-run resumes: settled problems are
skipped, and every call that succeeded replays from the cache for free. An errored call (an
API error that outlasted the retries) is re-run on resume, as Amendment 1 says, until it has
errored on the first pass and 3 resume passes; then it stays errored, which the analysis reads
as no answer.

A run reads the problems only when the study's tag exists and holds the approved inputs, and
the inputs here are those (second_model_freeze.ready). A rebuild in the tag's own tree, which
has no git, reads them on the approval alone (inputs(tag=False): second_model_freeze.check).

Run:  python -m opt_agent.second_model --plan           # calls left and the worst case; no calls
      OPT_AGENT_LIVE=1 python -m opt_agent.second_model  # THE OWNER'S paid run
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

from opt_agent import evaluate, followup, followup_report, formulate, pricing
from opt_agent.api import Cache, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.evaluate import Condition, Item
from opt_agent.runs import REPO_ROOT, Run, Tags

SPLIT = "second-model"
RUN_DIR = REPO_ROOT / "runs" / "second-model"
MODEL = "claude-sonnet-5-5"
CONDITION: Condition = "single-shot"
SAMPLE = 0  # Sonnet's one sample: the plain request (unsalted cache key), as Haiku's sample 0
HAIKU_MODEL = formulate.DEFAULT_MODEL  # the paired answers' model, claude-haiku-5-5
HAIKU_RECORD = REPO_ROOT / "runs" / "followup-test" / "results.jsonl"  # section 2
HAIKU_SAMPLE = 0  # section 2: the pair of each Sonnet answer
CAP_USD = 7.00  # section 6: actual spend, never passed
CHECKPOINT = 10  # section 6: problems, in run order, before the projection
PROBLEMS = 121  # the follow-up's unexposed test problems (section 2)
RESUME_PASSES = 3  # Amendment 1: the first pass and 3 resumes, then an error is final
MAX_ERRORS_IN_A_ROW = evaluate.MAX_ERRORS_IN_A_ROW


class ProjectionTooHigh(RunStopped):
    """The checkpoint projects a total over the cap: the run stops before calling more."""


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
    return {
        "split": SPLIT,
        "problems": [r.id for r in records],
        "condition": CONDITION,
        "sample": SAMPLE,
        "model": MODEL,
        "settings_sha256": evaluate.settings_sha256(CONDITION, MODEL),
        "cap_usd": CAP_USD,
        "checkpoint": CHECKPOINT,
        "freeze": digest,
    }


def fix_manifest(out: Path, wanted: dict) -> None:
    path = out / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != wanted:
        raise ValueError(f"{path} describes another run (problems, model, settings, cap, "
                         "checkpoint or freeze); use a new run directory")  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(wanted, indent=1) + "\n")


def lines(out: Path) -> dict[str, list[dict]]:
    """Every item line so far, per problem, in order."""
    found: dict[str, list[dict]] = {}
    results = out / "results.jsonl"
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            found.setdefault(entry["problem_id"], []).append(entry)
    return found


def settled(entries: list[dict]) -> bool:
    """A problem needs no more calls: it's done, or it has errored on every allowed pass."""
    return any(e["outcome"] == "done" for e in entries) or len(entries) >= 1 + RESUME_PASSES


def projection(records: list[followup.Problem], found: dict[str, list[dict]]) -> dict:
    """The checkpoint's numbers: among the first CHECKPOINT problems, the answers so far (a
    done item, right or wrong), their cost, and the projected total for every problem at that
    mean (None with no answer to project from). Token counts only: nothing here is scored."""
    latest = [found[r.id][-1] for r in records[:CHECKPOINT] if found.get(r.id)]
    done = [e for e in latest if e["outcome"] == "done"]
    cost = sum(e["cost_usd"] for e in done)
    projected = cost / len(done) * len(records) if done else None
    return {"answered": len(done), "cost_usd": cost, "projected_usd": projected}


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
               else f"they project ${projected:.2f} for all {len(records)}, over the "
                    f"${cap:.2f} cap")  # fmt: skip
        raise ProjectionTooHigh(f"after the first {CHECKPOINT} problems, {why}")


def run(
    client: anthropic.Anthropic,
    out: Path = RUN_DIR,
    records: list[followup.Problem] | None = None,
    digest: str | None = None,
    cap: float = CAP_USD,
    limit: int | None = None,
) -> list[Item]:
    """Every problem not yet settled, in order; returns the items this pass added. `records`
    and `digest` are for tests (fake problems, no freeze) and for a replay, which also passes
    `limit`: only the first `limit` problems, as many as the committed run reached."""
    if records is None:
        records, digest = inputs()
    fix_manifest(out, manifest(records, digest or "unfrozen (a test)"))
    before = lines(out)
    session = Run.start(log_path=out / "attempts.jsonl", cache=Cache(out / "cache", SAMPLE),
                        fingerprint=digest)  # fmt: skip
    added: list[Item] = []
    errors_in_a_row, checked = 0, False
    try:
        for index, record in enumerate(records[:limit]):
            if settled(before.get(record.id, [])):
                continue
            if index >= CHECKPOINT and not checked:
                checked = True
                checkpoint(out, records, cap)
            tags = Tags(problem_id=record.id, split=SPLIT, condition=CONDITION)
            item = evaluate.run_item(record, CONDITION, client, session, tags, MODEL)
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
    """(calls left, worst case in USD): every unsettled problem's request at its full size,
    with a reply that uses all of max_tokens."""
    before, calls, worst = lines(out), 0, 0.0
    for record in records:
        if not settled(before.get(record.id, [])):
            calls += 1
            worst += pricing.worst_case_usd(formulate.build_request(record.document, MODEL))
    return calls, worst


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The second-model study's runner.")
    parser.add_argument("--out", type=Path, default=RUN_DIR)
    parser.add_argument("--plan", action="store_true", help="the worst case; no calls")
    args = parser.parse_args(argv)
    records, digest = inputs()  # the tag, the approval and these inputs, or FreezeError
    calls, worst = plan(records, args.out)
    print(f"{len(records)} problems: {calls} calls left ({MODEL}); worst case ${worst:.2f} if "
          f"every reply used all of max_tokens. Hard cap ${CAP_USD:.2f}, and a stop after the "
          f"first {CHECKPOINT} problems if they project more than that.")  # fmt: skip
    if args.plan:
        return
    try:
        client = BudgetedClient(anthropic.Anthropic(api_key=get_api_key()),
                                Budget(CAP_USD, args.out / "spend.jsonl"))  # fmt: skip
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    try:
        added = run(client, args.out, records, digest)  # type: ignore[arg-type]  # BudgetedClient wraps one
    except RunStopped as stop:
        sys.exit(f"stopped: {stop}. Spent ${client.budget.spent_usd:.4f} in all. Running it "
                 "again resumes; finished calls replay for free.")  # fmt: skip
    print(f"{len(added)} calls this pass; spent ${client.budget.spent_usd:.4f} in all. "
          "Then: python -m opt_agent.second_model_report")  # fmt: skip


if __name__ == "__main__":
    main()
