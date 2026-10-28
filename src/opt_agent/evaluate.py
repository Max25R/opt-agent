"""Run problems through the evaluation's conditions: resumable, and within a dollar cap.

The conditions (docs/PREREGISTRATION.md, section 2): "baseline" (Claude answers directly,
no solver), "single-shot" (one formulation, solved and checked) and "self-correction" (up
to 3 attempts). Self-correction's first request is byte-identical to single-shot's, so it
replays from the run's cache: the two are paired on the same first replies, paid once.

Each (problem, condition) pair becomes one "item" line in results.jsonl, recording what
the condition answered, never whether that's right: report.py scores the answers against
the ground truth afterwards (scoring.py), so a corrected review never needs a paid re-run.
- **done**: the answer (a confirmed status and objective; for the baseline, a parsed one),
  or no answer and the kind of failure (`no_answer`: an unusable reply, solvers
  disagreeing, a solver time-out, ...).
- **errored**: an API error outlasted every retry (api.call). That isn't Claude's
  failure, so a resumed run tries the pair again (pre-registration, Amendment 1). Each
  line names its pass (`run_id`), so the report can count how many passes a pair needed.

A run directory is one experiment: manifest.json, written by the first pass, fixes its
split, problems, conditions, model, and request settings, and a resume with any of them
changed is refused. The manifest is also the report's denominator: a pair with no line yet
is pending, never silently missing.

The run stops cleanly, with a "stopped" line, when the budget's next call could exceed the
cap (budget.py), when the account reaches its spend limit, or after MAX_ERRORS_IN_A_ROW
errored pairs. Re-running the same command resumes it: done pairs are skipped, and every
call that already succeeded replays from the run's cache, so nothing is paid for twice.
The cap counts what earlier runs in the same directory spent (its spend.jsonl).

Only the dev split runs here until milestone 6 adds the pre-registration's freeze checks.

Run:  python -m opt_agent.evaluate --out runs/smoke --cap 1.00 ID [ID ...]
      (add --plan to see the pending pairs and the worst-case cost without calling)
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from opt_agent import agent, api, baseline, formulate, pricing
from opt_agent.api import Cache, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.ground_truth import GROUND_TRUTH_DIR, Record, load_records
from opt_agent.ground_truth import scorable as is_scorable
from opt_agent.runs import Run, Tags
from opt_agent.scoring import score
from opt_agent.self_correct import MAX_ATTEMPTS
from opt_agent.solver import Status

Condition = Literal["baseline", "single-shot", "self-correction"]
CONDITIONS: tuple[Condition, ...] = ("baseline", "single-shot", "self-correction")
ATTEMPTS = {"single-shot": 1, "self-correction": MAX_ATTEMPTS}
MAX_ERRORS_IN_A_ROW = 3  # the API is down or the limits are too low: stop, resume later

# Why a done pair has no answer: the loud failures of pre-registration section 3g. (An API
# error is an errored pair instead; only the report turns one into a failure.)
NoAnswer = Literal[
    "unusable reply", "refusal", "solvers disagree", "solver time-out", "solver error",
    "failed check",
]  # fmt: skip


class Item(BaseModel):
    """One (problem, condition) pair in one pass: what the condition answered."""

    kind: Literal["item"] = "item"
    problem_id: str
    split: str
    condition: Condition
    outcome: Literal["done", "errored"]
    run_id: str | None = None  # the pass that wrote this line (runs.Run)
    model_id: str
    settings_sha256: str  # the condition's request template: prompt, schema, settings
    status: str | None = None  # the system's answer; None if there's no confirmed one
    objective: float | None = None
    no_answer: NoAnswer | None = None  # why a done pair has no answer
    reason: str | None = None  # in words: why the loop stopped, or the error
    flags: list[str] = []  # revisions that deleted or loosened something (changes.py)
    attempts: int = 0
    cached_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0  # includes thinking
    cost_usd: float = 0.0  # every call the answer used, at its original token counts
    paid_usd: float = 0.0  # only the calls this run paid for (not replayed from the cache)
    latency_s: float = 0.0  # API plus solver time, without retries
    retry_s: float = 0.0  # failed tries and the waits after them
    wall_s: float = 0.0  # as measured in this pass; shorter when calls replay from the cache


class Manifest(BaseModel):
    """What a run directory is an experiment of. Fixed by its first pass."""

    split: str
    problem_ids: list[str]
    conditions: list[Condition]
    model_id: str
    settings: dict[str, str]  # condition -> settings_sha256


def manifest_for(
    split: str, records: list[Record], conditions: tuple[Condition, ...], model_id: str
) -> Manifest:
    return Manifest(split=split, problem_ids=[r.id for r in records],
                    conditions=list(conditions), model_id=model_id,
                    settings={c: settings_sha256(c, model_id) for c in conditions})  # fmt: skip


def fix_manifest(out: Path, manifest: Manifest) -> None:
    """Write the manifest on the first pass; afterwards, refuse a pass that differs."""
    path = out / "manifest.json"
    if not path.exists():
        out.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest.model_dump_json(indent=1) + "\n")
        return
    fixed = Manifest.model_validate_json(path.read_text())
    if fixed != manifest:
        changed = [k for k in Manifest.model_fields if getattr(fixed, k) != getattr(manifest, k)]
        raise ValueError(
            f"{path} was made with different {', '.join(changed)}; a resume must repeat the "
            "same experiment, so start a new run directory instead"
        )


def settings_sha256(condition: Condition, model_id: str) -> str:
    """Changes whenever the condition's prompt, schema, or pinned settings change, so
    results from different versions can't be mixed in one run directory."""
    template = (baseline if condition == "baseline" else formulate).build_request("", model_id)
    return api.request_sha256(template)[:12]


def evaluate(
    records: list[Record],
    conditions: tuple[Condition, ...],
    client: anthropic.Anthropic,
    out: Path,
    split: str = "dev",
    model_id: str = formulate.DEFAULT_MODEL,
) -> list[Item]:
    """Every pending pair, in order; returns the items this call added. Raises RunStopped
    (after writing a "stopped" line) when the run has to stop."""
    fix_manifest(out, manifest_for(split, records, conditions, model_id))
    results = out / "results.jsonl"
    done = done_pairs(results, model_id)
    session = Run.start(log_path=out / "attempts.jsonl", cache=Cache(out / "cache"))
    added: list[Item] = []
    errors_in_a_row = 0
    try:
        for record in records:
            for condition in conditions:
                if (record.id, condition) in done:
                    continue
                tags = Tags(problem_id=record.id, split=split, condition=condition)
                item = run_item(record, condition, client, session, tags, model_id)
                _append(results, item.model_dump(mode="json"))
                added.append(item)
                errors_in_a_row = errors_in_a_row + 1 if item.outcome == "errored" else 0
                if errors_in_a_row >= MAX_ERRORS_IN_A_ROW:
                    raise RunStopped(f"{errors_in_a_row} API errors in a row: {item.reason}")
    except RunStopped as stop:
        _append(results, {"kind": "stopped", "time": _now(), "reason": str(stop)})
        raise
    return added


def run_item(
    record: Record,
    condition: Condition,
    client: anthropic.Anthropic,
    session: Run,
    tags: Tags,
    model_id: str,
) -> Item:
    base = {
        "problem_id": record.id,
        "split": tags.split,
        "condition": condition,
        "run_id": session.run_id,
        "model_id": model_id,
        "settings_sha256": settings_sha256(condition, model_id),
    }
    if condition == "baseline":
        return _baseline_item(record, client, session, tags, model_id, base)
    return _solver_item(record, condition, client, session, tags, model_id, base)


def _baseline_item(
    record: Record,
    client: anthropic.Anthropic,
    session: Run,
    tags: Tags,
    model_id: str,
    base: dict,
) -> Item:
    start = time.perf_counter()
    a = baseline.answer_directly(record.document, client, model_id, session.cache)
    wall = time.perf_counter() - start
    session.write("baseline", tags, model_id=model_id, request_sha256=a.call.request_sha256,
                  request=a.request, reply=a.raw_text, stop_reason=a.stop_reason,
                  usage=a.usage.model_dump(), call=a.call.model_dump(), error=a.error,
                  status=a.status, objective=a.objective)  # fmt: skip
    cost = pricing.cost_usd(a.usage, model_id)
    spend = {"attempts": 1, "cached_calls": int(a.call.cached),
             "input_tokens": a.usage.input_tokens, "output_tokens": a.usage.output_tokens,
             "cost_usd": cost, "paid_usd": 0.0 if a.call.cached else cost,
             "latency_s": a.call.latency_s, "retry_s": a.call.retry_s, "wall_s": wall}  # fmt: skip
    if a.api_failed:
        return Item(**base, **spend, outcome="errored", reason=a.call.error)
    no_answer = None
    if a.status is None:
        no_answer = "refusal" if a.stop_reason == "refusal" else "unusable reply"
    return Item(**base, **spend, outcome="done", status=a.status, objective=a.objective,
                no_answer=no_answer, reason=a.error)  # fmt: skip


def _solver_item(
    record: Record,
    condition: Condition,
    client: anthropic.Anthropic,
    session: Run,
    tags: Tags,
    model_id: str,
    base: dict,
) -> Item:
    result = agent.run(record.document, client, model_id, with_explanation=False,
                       max_attempts=ATTEMPTS[condition], session=session, tags=tags)  # fmt: skip
    formulations = [a.formulation for a in result.outcome.attempts]
    costs = [pricing.cost_usd(f.usage, f.model_id) for f in formulations]
    spend = {
        "attempts": len(formulations),
        "cached_calls": sum(f.call.cached for f in formulations),
        "input_tokens": sum(f.usage.input_tokens for f in formulations),
        "output_tokens": sum(f.usage.output_tokens for f in formulations),
        "cost_usd": sum(costs),
        "paid_usd": sum(c for c, f in zip(costs, formulations, strict=True) if not f.call.cached),
        "latency_s": result.latency_s,
        "retry_s": result.retry_s,
        "wall_s": result.wall_s,
    }
    if result.outcome.stopped == "api error":
        return Item(**base, **spend, outcome="errored", reason=formulations[-1].call.error)
    s = result.solution
    status, objective = (s.status, s.objective) if result.confirmed else (None, None)
    return Item(**base, **spend, outcome="done", status=status, objective=objective,
                no_answer=_no_answer(result), reason=_reason(result),
                flags=result.outcome.flags)  # fmt: skip


def _no_answer(result: agent.Result) -> NoAnswer | None:
    if result.confirmed:
        return None
    if result.solution is None:
        return "refusal" if result.outcome.stopped == "refused" else "unusable reply"
    for s in (result.solution, result.highs_solution):
        if s is not None and s.failed:
            return "solver time-out" if s.status is Status.TIMEOUT else "solver error"
    return "solvers disagree" if result.highs_agrees is False else "failed check"


def _reason(result: agent.Result) -> str:
    stopped = result.outcome.stopped
    if result.confirmed:
        return stopped
    if result.solution is None:
        return f"{stopped}; no usable model: {result.formulation.error}"
    if result.solution.failed or (result.highs_solution and result.highs_solution.failed):
        return f"{stopped}; a solver timed out or failed"
    if result.highs_agrees is False:
        return f"{stopped}; CBC and HiGHS disagree"
    return f"{stopped}; failed checks: {'; '.join(result.check_problems)}"


# ---- resuming ---------------------------------------------------------------------------


def done_pairs(results: Path, model_id: str) -> set[tuple[str, str]]:
    """The pairs already done. A later line for a pair replaces an earlier one (errored,
    then done on resume)."""
    if not results.exists():
        return set()
    latest: dict[tuple[str, str], dict] = {}
    for line in results.read_text().splitlines():
        entry = json.loads(line)
        if entry["kind"] == "item":
            latest[(entry["problem_id"], entry["condition"])] = entry
    for (problem_id, condition), entry in latest.items():
        expected = settings_sha256(condition, model_id)
        if (entry["model_id"], entry["settings_sha256"]) != (model_id, expected):
            raise ValueError(
                f"{results} has {condition} results for {problem_id} from another model or "
                f"prompt version ({entry['model_id']}, {entry['settings_sha256']}); start a "
                "new run directory instead of mixing them"
            )
    return {pair for pair, entry in latest.items() if entry["outcome"] == "done"}


def latest_items(results: Path) -> list[Item]:
    latest: dict[tuple[str, str], Item] = {}
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            item = Item.model_validate(entry)
            latest[(item.problem_id, item.condition)] = item
    return list(latest.values())


def _append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ---- planning and reporting -------------------------------------------------------------


def worst_case_plan(
    records: list[Record], conditions: tuple[Condition, ...], done: set, model_id: str
) -> tuple[int, float]:
    """(most paid calls, most they can cost) for the pending pairs, if every reply used
    all of max_tokens. Self-correction's first call is free when single-shot runs too."""
    calls, usd = 0, 0.0
    # A revision carries the previous reply (at most max_tokens) and feedback on top.
    revision_extra = pricing.prices_for(model_id, 0).input * (api.MAX_TOKENS + 2_000) / 1e6
    for record in records:
        for condition in conditions:
            if (record.id, condition) in done:
                continue
            module = baseline if condition == "baseline" else formulate
            first = pricing.worst_case_usd(module.build_request(record.document, model_id))
            if condition == "baseline":
                calls, usd = calls + 1, usd + first
                continue
            replayed = condition == "self-correction" and "single-shot" in conditions
            paid_first = 0 if replayed else 1
            revisions = ATTEMPTS[condition] - 1
            calls += paid_first + revisions
            usd += paid_first * first + revisions * (first + revision_extra)
    return calls, usd


def render(items: list[Item], records: dict[str, Record], budget: Budget) -> str:
    rows = [["problem", "condition", "result", "tries", "tokens in/out", "cost", "paid"]]
    right: dict[str, int] = {}
    for i in items:
        if i.outcome == "errored":
            result = "ERRORED (not scored yet)"
        else:
            s = score(records[i.problem_id], i.status, i.objective)
            right[i.condition] = right.get(i.condition, 0) + s.correct
            result = "right" if s.correct else f"wrong ({s.failure})"
        rows.append([i.problem_id, i.condition, result, str(i.attempts),
                     f"{i.input_tokens:,}/{i.output_tokens:,}", f"${i.cost_usd:.4f}",
                     f"${i.paid_usd:.4f}"])  # fmt: skip
    widths = [max(len(r[k]) for r in rows) for k in range(len(rows[0]))]
    lines = ["  ".join(cell.ljust(w) for cell, w in zip(r, widths, strict=True)) for r in rows]
    lines.append("")
    for condition in CONDITIONS:
        mine = [i for i in items if i.condition == condition]
        if mine:
            scored = [i for i in mine if i.outcome == "done"]
            lines.append(
                f"{condition}: {right.get(condition, 0)}/{len(scored)} right, "
                f"{len(mine) - len(scored)} errored; cost ${sum(i.cost_usd for i in mine):.4f}"
            )
    lines.append(
        f"Spent in this directory: ${budget.spent_usd:.4f} on {budget.calls} paid calls, "
        f"cap ${budget.cap_usd:.2f}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run dev problems through the conditions.")
    parser.add_argument("ids", nargs="+", help="problem ids from the split")
    parser.add_argument("--out", type=Path, required=True, help="the run's directory")
    parser.add_argument("--cap", type=float, default=1.00, help="dollar cap (default 1.00)")
    parser.add_argument("--split", choices=["dev"], default="dev", help="dev only, for now")
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=list(CONDITIONS))
    parser.add_argument("--model", default=formulate.DEFAULT_MODEL)
    parser.add_argument("--plan", action="store_true", help="show the worst case; no calls")
    args = parser.parse_args(argv)

    by_id = {r.id: r for r in load_records(GROUND_TRUTH_DIR / f"{args.split}.json")}
    unknown = [i for i in args.ids if i not in by_id or not is_scorable(by_id[i])]
    if unknown:
        sys.exit(f"not scorable {args.split} problems: {', '.join(unknown)}")
    records = [by_id[i] for i in args.ids]
    conditions = tuple(c for c in CONDITIONS if c in args.conditions)  # baseline first
    budget = Budget(args.cap, args.out / "spend.jsonl")

    done = done_pairs(args.out / "results.jsonl", args.model)
    pending = sum((r.id, c) not in done for r in records for c in conditions)
    calls, worst = worst_case_plan(records, conditions, done, args.model)
    print(f"{pending} pairs pending: at most {calls} paid "
          f"calls, at most ${worst:.4f} if every reply used all {api.MAX_TOKENS:,} tokens. "
          f"Already spent here: ${budget.spent_usd:.4f} of the ${args.cap:.2f} cap.")  # fmt: skip
    if args.plan:
        return
    try:
        client = BudgetedClient(anthropic.Anthropic(api_key=get_api_key()), budget)
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    try:
        evaluate(records, conditions, client, args.out, args.split, args.model)
    except RunStopped as stop:
        print(render(latest_items(args.out / "results.jsonl"), by_id, budget))
        sys.exit(f"\nSTOPPED: {stop}\nRe-run the same command to resume; nothing is paid twice.")
    print(render(latest_items(args.out / "results.jsonl"), by_id, budget))


if __name__ == "__main__":
    main()
