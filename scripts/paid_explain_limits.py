"""The dev explanations again, with ADR-0009's limits, for the owner's terminal. PAID: Claude
never runs it.

The explanation checker's run (runs/explain-dev, 2026-11-19) explained every verified
single-shot answer on NL4Opt's dev split: 92 problems, 88 verified, 73 of them integer
programs. This explains the same answers again as agent.run does since ADR-0009: an integer
program's explainer also gets what re-solving finds about each constraint
(src/opt_agent/limits.py). Every formulation replays from that run's committed cache, so none
is paid for, and an LP's explanation request hasn't changed, so it replays too: only the
integer programs' explanations are new calls. Rows go to runs/explain-dev-limits/
explanations.jsonl in runs/explain-dev's format (each row's facts with their limits). Comparing
the two runs' explanations comes after, as its own exploratory step.

Every call goes through budget.BudgetedClient with --cap dollars in all, counted in
runs/explain-dev-limits/spend.jsonl: a call whose worst case could cross the cap is never sent,
and the run stops cleanly. A re-run replays every call that already succeeded, for free.

Run:  python scripts/paid_explain_limits.py --plan                       # no calls
      OPT_AGENT_LIVE=1 python scripts/paid_explain_limits.py --cap 0.25  # the owner's paid run
"""

import argparse
import json
import shutil
import statistics
import sys
from pathlib import Path

import anthropic

from opt_agent import agent, explain, formulate, pricing
from opt_agent.api import Cache, NotCached, ReplayOnlyClient, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records, scorable
from opt_agent.runs import Run

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runs" / "explain-dev"  # its cache: M6's dev formulations and 88 explanations
OUT = ROOT / "runs" / "explain-dev-limits"
MODEL = formulate.DEFAULT_MODEL
CAP_USD = 0.25


def dev_problems() -> list:
    return [r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if scorable(r)]


def replayed(record, cache: Cache) -> agent.Result:
    """Single-shot from the cache alone, no explanation (a missing reply raises NotCached)."""
    return agent.run(record.document, ReplayOnlyClient(), MODEL, with_explanation=False,
                     max_attempts=1, session=Run(cache=cache))  # fmt: skip


def plan(cache: Cache | None = None) -> dict:
    """What the run would do, replaying with no client: the new explanation calls and their
    worst case."""
    cache = cache or Cache(SOURCE / "cache")
    counts = {"problems": 0, "verified": 0, "integer_programs": 0, "new_calls": 0, "worst": 0.0}
    for record in dev_problems():
        counts["problems"] += 1
        result = replayed(record, cache)
        if not result.verified:
            continue
        model, solution = result.formulation.model, result.solution
        assert model is not None and solution is not None  # verified: a model, solved
        facts = explain.solver_facts(model, solution, with_limits=True)
        request = explain.build_request(record.document, model, facts, MODEL)
        counts["verified"] += 1
        counts["integer_programs"] += model.is_mip
        if cache.get(cache.key(request)) is None:
            counts["new_calls"] += 1
            counts["worst"] += pricing.worst_case_usd(request)
    return counts


def mean_explanation_usd(cache_dir: Path = SOURCE / "cache") -> float:
    """What the first run's explanation calls cost on average, at their recorded tokens."""
    costs = []
    for path in sorted(cache_dir.glob("*.json")):
        entry = json.loads(path.read_text())
        if entry["request"]["system"] == explain.SYSTEM_PROMPT:
            message = anthropic.types.Message.model_validate(entry["response"])
            costs.append(pricing.cost_usd(message.usage, MODEL))
    return statistics.mean(costs)


def explain_again(client) -> list[dict]:
    """Single-shot and an explanation (with limits, agent.run's default) for each dev problem."""
    cache = Cache(OUT / "cache")
    rows = []
    for record in dev_problems():
        session = Run.start(log_path=OUT / "attempts.jsonl", cache=cache)
        result = agent.run(record.document, client, MODEL, with_explanation=True,
                           max_attempts=1, session=session)  # fmt: skip
        e, facts = result.explanation, None
        if result.verified:
            model, solution = result.formulation.model, result.solution
            assert model is not None and solution is not None
            facts = explain.solver_facts(model, solution, with_limits=True).model_dump(mode="json")
        rows.append({
            "problem": record.id, "verified": result.verified, "stopped": result.outcome.stopped,
            "model": None if result.formulation.model is None
            else result.formulation.model.model_dump(mode="json"),
            "facts": facts, "explanation": None if e is None else e.text,
            "unsupported_numbers": None if e is None else e.unsupported_numbers,
            "explanation_problem": None if e is None else e.problem,
            "calls": len(result.calls), "cached_calls": sum(c.cached for c in result.calls),
        })  # fmt: skip
        print(f"dev {record.id}: {'verified' if result.verified else result.outcome.stopped}")
    (OUT / "explanations.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The dev explanations with limits (paid).")
    parser.add_argument("--cap", type=float, default=CAP_USD, help="USD for the whole run")
    parser.add_argument("--plan", action="store_true", help="counts and worst case; no calls")
    args = parser.parse_args(argv)
    counts, typical = plan(), mean_explanation_usd()
    replays = counts["verified"] - counts["new_calls"]
    print(
        f"{counts['problems']} dev problems, {counts['verified']} verified answers to explain "
        f"({counts['integer_programs']} integer programs): {counts['new_calls']} new explanation "
        f"calls, and {replays} explanations and every formulation replay from "
        f"{SOURCE.relative_to(ROOT)}. Worst case ${counts['worst']:.2f}; expected about "
        f"${counts['new_calls'] * typical:.2f}, at the first run's ${typical:.5f} an "
        f"explanation; cap ${args.cap:.2f} ({MODEL}; prices of {pricing.PRICES_CHECKED})."
    )
    if args.plan:
        return
    try:
        client = BudgetedClient(anthropic.Anthropic(api_key=get_api_key()),
                                Budget(args.cap, OUT / "spend.jsonl"))  # fmt: skip
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE / "cache", OUT / "cache", dirs_exist_ok=True)
    try:
        rows = explain_again(client)
    except (RunStopped, NotCached) as stop:
        sys.exit(f"stopped: {stop}. Spent ${client.budget.spent_usd:.4f}; run it again to "
                 "resume (what's done replays for free).")  # fmt: skip
    explained = sum(r["explanation"] is not None for r in rows)
    print(f"{explained} explanations in {OUT.relative_to(ROOT)}/explanations.jsonl; spent "
          f"${client.budget.spent_usd:.4f} on {client.budget.calls} calls.")  # fmt: skip


if __name__ == "__main__":
    main()
