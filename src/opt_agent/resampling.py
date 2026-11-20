"""The resampling study's runner (docs/RESAMPLING_PREREGISTRATION.md, sections 3 and 6).

Per problem, in the follow-up's run order (followup.in_run_order): single-shot samples 3 to 7
and the baseline's sample 3 (CELLS), each through the follow-up's own per-item code
(evaluate.run_item), so the requests, the solving, the checks and the recorded item are the
follow-up's, with the same model, prompts and max_tokens; only the sample number is new (a
salted cache key, Cache(dir, sample), so a fresh reply). All six calls of a problem run
before the next problem, so a stopped run leaves whole problems.

One run directory holds everything: manifest.json (the problems, the cells, the model, each
condition's settings hash and the freeze's digest; a resume with any of them changed is
refused), results.jsonl (one item line per call), attempts.jsonl, the cache and the spend
ledger. A re-run resumes: done cells are skipped and every call that succeeded replays for
free. An errored cell (an API error that outlasted the retries) is re-run on resume, as
Amendment 1 says, until it has errored on the first pass and 3 resume passes; then it stays an
errored line, which the analysis reads as no answer.

The problems are read only on the frozen inputs (resampling_freeze.check, FreezeError
otherwise), and a run is always the whole experiment: all 121 problems, all six cells.

Run:  python -m opt_agent.resampling --plan                       # worst case; no calls
      OPT_AGENT_LIVE=1 python -m opt_agent.resampling --cap 3.00   # THE OWNER'S paid run
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

from opt_agent import baseline, evaluate, followup, followup_report, formulate, pricing
from opt_agent.api import Cache, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.evaluate import Condition, Item
from opt_agent.runs import REPO_ROOT, Run, Tags

SPLIT = "resampling"
RUN_DIR = REPO_ROOT / "runs" / "resampling"
MODEL = formulate.DEFAULT_MODEL
CAP_USD = 3.00  # section 6's hard cap
SINGLE_SHOT_SAMPLES = (3, 4, 5, 6, 7)
BASELINE_SAMPLE = 3
UNIT_SAMPLE = 3  # R1's unit: single-shot sample 3 (section 4)
CELLS: tuple[tuple[Condition, int], ...] = (
    *(("single-shot", s) for s in SINGLE_SHOT_SAMPLES),
    ("baseline", BASELINE_SAMPLE),
)
PROBLEMS = 121  # the follow-up's unexposed test problems (section 2)
RESUME_PASSES = 3  # Amendment 1: the first pass and 3 resumes, then an error is final
MAX_ERRORS_IN_A_ROW = evaluate.MAX_ERRORS_IN_A_ROW


def problems() -> list[followup.Problem]:
    """The 121 problems, in the follow-up's run order, only on the frozen inputs."""
    from opt_agent import resampling_freeze  # here: it imports this module

    resampling_freeze.check()
    exposed = followup_report.exposed_labels()
    chosen = [p for p in followup.read_test() if p.scorable and p.id not in exposed]
    if len(chosen) != PROBLEMS:
        raise ValueError(f"expected {PROBLEMS} unexposed scorable problems, found {len(chosen)}")
    return followup.in_run_order(followup.TEST_SPLIT, chosen)


def manifest(records: list[followup.Problem], digest: str) -> dict:
    return {
        "split": SPLIT,
        "problems": [r.id for r in records],
        "cells": [list(cell) for cell in CELLS],
        "model": MODEL,
        "settings_sha256": {c: evaluate.settings_sha256(c, MODEL) for c in ("single-shot",
                                                                           "baseline")},
        "freeze": digest,
    }  # fmt: skip


def fix_manifest(out: Path, wanted: dict) -> None:
    path = out / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != wanted:
        raise ValueError(f"{path} describes another run (problems, cells, model, settings or "
                         "freeze); use a new run directory")  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(wanted, indent=1) + "\n")


def lines(out: Path) -> dict[tuple[str, str, int], list[dict]]:
    """Every item line so far, per cell, in order."""
    found: dict[tuple[str, str, int], list[dict]] = {}
    results = out / "results.jsonl"
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            found.setdefault((entry["problem_id"], entry["condition"], entry["sample"]),
                             []).append(entry)  # fmt: skip
    return found


def settled(entries: list[dict]) -> bool:
    """A cell needs no more calls: it's done, or it has errored on every allowed pass."""
    return any(e["outcome"] == "done" for e in entries) or len(entries) >= 1 + RESUME_PASSES


def run(
    client: anthropic.Anthropic,
    out: Path = RUN_DIR,
    records: list[followup.Problem] | None = None,
    digest: str | None = None,
) -> list[Item]:
    """Every cell not yet settled; returns the items this pass added. `records` and `digest`
    are for tests (fake problems, no freeze); a real run takes neither."""
    if records is None:
        from opt_agent import resampling_freeze

        records, digest = problems(), resampling_freeze.check()
    fix_manifest(out, manifest(records, digest or "unfrozen (a test)"))
    before = lines(out)
    first = Run.start(log_path=out / "attempts.jsonl", cache=Cache(out / "cache"),
                      fingerprint=digest)  # fmt: skip
    sessions = {s: Run(log_path=first.log_path, cache=Cache(out / "cache", s),
                       run_id=first.run_id) for _, s in CELLS}  # fmt: skip
    added: list[Item] = []
    errors_in_a_row = 0
    try:
        for record in records:
            for condition, sample in CELLS:
                if settled(before.get((record.id, condition, sample), [])):
                    continue
                tags = Tags(problem_id=record.id, split=SPLIT, condition=condition)
                item = evaluate.run_item(record, condition, client, sessions[sample], tags,
                                         MODEL)  # fmt: skip
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
    """(calls left, worst case in USD): every unsettled cell's request at its full size."""
    before, calls, worst = lines(out), 0, 0.0
    for record in records:
        requests = {"single-shot": formulate.build_request(record.document, MODEL),
                    "baseline": baseline.build_request(record.document, MODEL)}  # fmt: skip
        for condition, sample in CELLS:
            if not settled(before.get((record.id, condition, sample), [])):
                calls += 1
                worst += pricing.worst_case_usd(requests[condition])
    return calls, worst


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The resampling study's runner.")
    parser.add_argument("--out", type=Path, default=RUN_DIR)
    parser.add_argument("--cap", type=float, default=CAP_USD, help="USD for the whole run")
    parser.add_argument("--plan", action="store_true", help="the worst case; no calls")
    args = parser.parse_args(argv)
    if args.cap > CAP_USD:
        sys.exit(f"the pre-registered hard cap is ${CAP_USD:.2f}")
    records = problems()
    calls, worst = plan(records, args.out)
    print(f"{len(records)} problems x {len(CELLS)} cells: {calls} calls left, worst case "
          f"${worst:.2f}; cap ${args.cap:.2f} ({MODEL}).")  # fmt: skip
    if args.plan:
        return
    try:
        client = BudgetedClient(anthropic.Anthropic(api_key=get_api_key()),
                                Budget(args.cap, args.out / "spend.jsonl"))  # fmt: skip
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    try:
        added = run(client, args.out)  # type: ignore[arg-type]  # BudgetedClient wraps one
    except RunStopped as stop:
        sys.exit(f"stopped: {stop}. Run it again to resume; done cells replay for free.")
    print(f"{len(added)} calls this pass; spent ${client.budget.spent_usd:.4f} in all. "
          "Then: python -m opt_agent.resampling_report")  # fmt: skip


if __name__ == "__main__":
    main()
