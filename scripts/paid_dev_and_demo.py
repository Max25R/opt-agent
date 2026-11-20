"""The one paid run of 2026-11-19, for the owner's terminal. PAID: Claude never runs it.

**Part 1, explanations on NL4Opt's dev split**, to evaluate the explanation checker
(docs/analysis/explanation_checker.md). Each of the 92 scorable dev problems is solved
single-shot, as in M6, from the cached replies of M6's dev run (runs/dev-1/cache, copied into
runs/explain-dev/cache first; a formulation not found there is a paid call), and each verified
answer gets one explanation call. The checker runs on each, and every row goes to
runs/explain-dev/explanations.jsonl.

**Part 2, a demo example whose first model fails and self-correction fixes it.** The
candidates (demo.examples.FIX_STEP_CANDIDATES) are tried in order, fresh samples 0 to 4 of
each, with the demo's settings (pipeline.MAX_TOKENS) and formulation and self-correction
only, until one's first attempt fails (infeasible, unbounded or an unusable reply) and its
final answer is verified and equal to its hand-checked answer. That try then gets the demo's
whole pipeline (estimate, checklist, explanation). Each try's replies go to their own folder,
logs/demo-fix-step/<candidate>-s<sample>/, so the chosen one's can be copied into
src/opt_agent/demo/replies/, and every try is listed in logs/demo-fix-step/tries.json. If no
try qualifies, it says so: nothing is chosen.

Every call goes through budget.BudgetedClient with --cap dollars in all, counted in
logs/spend/paid-2026-11-19.jsonl: a call whose worst case could cross the cap is never sent,
and the run stops cleanly. A re-run replays every call that already succeeded, for free.

Run:  python scripts/paid_dev_and_demo.py --plan                    # no calls: counts, worst case
      OPT_AGENT_LIVE=1 python scripts/paid_dev_and_demo.py --cap 0.30   # the paid run
"""

import argparse
import json
import shutil
import statistics
import sys
from pathlib import Path

import anthropic

from opt_agent import agent, api, explain, formulate, pricing
from opt_agent.api import Cache, NotCached, ReplayOnlyClient, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.demo import app, pipeline
from opt_agent.demo.examples import FIX_STEP_CANDIDATES
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records, scorable
from opt_agent.runs import Run
from opt_agent.self_correct import MAX_ATTEMPTS
from opt_agent.solver import Status

ROOT = Path(__file__).resolve().parents[1]
DEV_SOURCE = ROOT / "runs" / "dev-1" / "cache"  # M6's dev run, with its single-shot replies
DEV_RUN = ROOT / "runs" / "explain-dev"
FIX = ROOT / "logs" / "demo-fix-step"
LEDGER = ROOT / "logs" / "spend" / "paid-2026-11-19.jsonl"
SAMPLES = range(5)  # fresh samples per candidate
MODEL = formulate.DEFAULT_MODEL
BYTES_PER_TOKEN = 4  # a reply carried into a later request adds at most this per token


# ---- part 1: explanations on dev ----------------------------------------------------------


def dev_problems() -> list:
    return [r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if scorable(r)]


def explain_dev(client) -> list[dict]:
    """Single-shot and an explanation for each dev problem; rows for the checker's study."""
    cache = Cache(DEV_RUN / "cache")
    rows = []
    for record in dev_problems():
        session = Run.start(log_path=DEV_RUN / "attempts.jsonl", cache=cache)
        # this run (2026-11-19) predates ADR-0009, so a resume sends its requests: no limits
        result = agent.run(record.document, client, MODEL, with_explanation=True,
                           max_attempts=1, session=session, explain_limits=False)  # fmt: skip
        e = result.explanation
        facts = None
        if result.verified:
            model, solution = result.formulation.model, result.solution
            facts = explain.solver_facts(model, solution).model_dump(mode="json")
        rows.append({
            "problem": record.id, "verified": result.verified, "stopped": result.outcome.stopped,
            "model": None if result.formulation.model is None
            else result.formulation.model.model_dump(mode="json"),
            "facts": facts, "explanation": None if e is None else e.text,
            "unsupported_numbers": None if e is None else e.unsupported_numbers,
            "explanation_problem": None if e is None else e.problem,
            "calls": len(result.calls), "cached_calls": sum(c.cached for c in result.calls),
        })  # fmt: skip
        print(f"dev {record.id}: {'verified' if result.verified else result.outcome.stopped}"
              + (f", {len(e.unsupported_numbers)} unbacked numbers" if e else ""))  # fmt: skip
    (DEV_RUN / "explanations.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return rows


def plan_dev() -> tuple[int, int, float]:
    """(formulations to pay for, explanation calls, worst case), replaying with no client."""
    cache, paid, explanations, worst = Cache(DEV_SOURCE), 0, 0, 0.0
    for record in dev_problems():
        request = formulate.build_request(record.document, MODEL)
        if cache.get(cache.key(request)) is None:
            padded = {"padding": "x" * (api.MAX_TOKENS * BYTES_PER_TOKEN)}
            paid += 1
            explanations += 1  # it may be verified, and then it's explained
            worst += pricing.worst_case_usd(request) + pricing.worst_case_usd(request | padded)
            continue
        result = agent.run(record.document, ReplayOnlyClient(), MODEL, with_explanation=False,
                           max_attempts=1, session=Run(cache=cache))  # fmt: skip
        if result.verified:
            model, solution = result.formulation.model, result.solution
            facts = explain.solver_facts(model, solution)
            explanations += 1
            worst += pricing.worst_case_usd(explain.build_request(record.document, model, facts,
                                                                  MODEL))  # fmt: skip
    return paid, explanations, worst


# ---- part 2: the fix-step example ---------------------------------------------------------


def first_attempt_failed(result: agent.Result) -> bool:
    first = result.outcome.attempts[0]
    return first.solution is None or first.solution.status is not Status.OPTIMAL


def matches(objective: float | None, reference: float) -> bool:
    return objective is not None and abs(objective - reference) <= 1e-6 * max(1.0, abs(reference))


def probe(candidate, sample: int, client) -> dict:
    """One try: formulation and self-correction only, with the demo's settings, into the
    try's own folder. Whether it shows the loop: the first attempt failed, and the final
    answer is verified and equal to the hand-checked one."""
    folder = FIX / f"{candidate.id}-s{sample}"
    with api.max_tokens_cap(pipeline.MAX_TOKENS):
        result = agent.run(candidate.text, client, pipeline.MODEL, with_explanation=False,
                           max_attempts=MAX_ATTEMPTS, session=Run(cache=Cache(folder)))  # fmt: skip
    objective = result.solution.objective if result.verified else None
    attempts = [a.solution.status.value if a.solution else f"unusable: {a.formulation.error}"
                for a in result.outcome.attempts]  # fmt: skip
    right = matches(objective, candidate.reference_objective)
    shown = folder.relative_to(ROOT) if folder.is_relative_to(ROOT) else folder
    return {"candidate": candidate.id, "sample": sample, "folder": str(shown),
            "attempts": attempts, "stopped": result.outcome.stopped,
            "verified": result.verified, "objective": objective, "matches": right,
            "shows_the_loop": first_attempt_failed(result) and result.verified
            and right}  # fmt: skip


def fix_step(client) -> dict:
    """Try the candidates in order until one shows the loop; every try is recorded."""
    tries, chosen = [], None
    for candidate in FIX_STEP_CANDIDATES:
        for sample in SAMPLES:
            entry = probe(candidate, sample, client)
            tries.append(entry)
            print(f"fix step {candidate.id} sample {sample}: {' -> '.join(entry['attempts'])}"
                  + ("  <- shows the loop" if entry["shows_the_loop"] else ""))  # fmt: skip
            if entry["shows_the_loop"]:  # the rest of the demo's pipeline; the loop replays
                full = pipeline.solve(candidate.text, client, Cache(ROOT / entry["folder"]))
                r = pipeline.to_response(full, "examples", candidate)
                full_pipeline = {"verified": r.verification.verified,
                                 "matches_reference": r.matches_reference, "calls": r.calls,
                                 "explanation_unsupported": r.explanation_unsupported}  # fmt: skip
                chosen = entry | {"full_pipeline": full_pipeline}
                break
        if chosen:
            break
    record = {"label": "a demo example chosen to show self-correction: the first try, in the "
                       "order listed, whose first model failed and whose revision is verified "
                       "and equal to its hand-checked answer",
              "tries": tries, "chosen": chosen}  # fmt: skip
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / "tries.json").write_text(json.dumps(record, indent=1) + "\n")
    return record


def plan_fix_step() -> tuple[int, float]:
    """(calls, worst case): every try uses all its attempts, and the chosen one adds the rest
    of the pipeline (estimate, checklist, explanation)."""
    calls, worst = 0, 0.0
    for candidate in FIX_STEP_CANDIDATES:
        with api.max_tokens_cap(pipeline.MAX_TOKENS):
            request = formulate.build_request(candidate.text, pipeline.MODEL)
        padded = request | {"padding": "x" * (pipeline.MAX_TOKENS * BYTES_PER_TOKEN)}
        calls += len(SAMPLES) * MAX_ATTEMPTS
        worst += len(SAMPLES) * MAX_ATTEMPTS * pricing.worst_case_usd(padded)
    extra = pipeline.CALLS_PER_SOLVE - MAX_ATTEMPTS
    return calls + extra, worst + extra * pricing.worst_case_usd(padded)


def mean_call_usd() -> float:
    """What a call costs on average: the demo examples' committed replies, at their tokens."""
    costs = []
    for path in sorted(app.REPLIES.glob("*.json")):
        usage = api.usage_of(anthropic.types.Message.model_validate(
            json.loads(path.read_text())["response"]))  # fmt: skip
        costs.append(pricing.cost_usd(usage, MODEL))
    return statistics.mean(costs)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The paid run of 2026-11-19 (the owner's).")
    parser.add_argument("--cap", type=float, default=0.30, help="USD for the whole run")
    parser.add_argument("--plan", action="store_true", help="counts and worst case; no calls")
    args = parser.parse_args(argv)
    paid, explanations, dev_worst = plan_dev()
    fix_calls, fix_worst = plan_fix_step()
    typical = mean_call_usd()
    dev_calls = paid + explanations
    expected = (dev_calls + len(FIX_STEP_CANDIDATES) * len(SAMPLES) + 6) * typical
    print(
        f"Part 1, explanations on NL4Opt dev: {len(dev_problems())} problems, {paid} "
        f"formulations to pay for (the rest replay from runs/dev-1), {explanations} "
        f"explanation calls; worst case ${dev_worst:.2f}."
    )
    print(
        f"Part 2, the fix-step example: {len(FIX_STEP_CANDIDATES)} candidates x "
        f"{len(SAMPLES)} samples, at most {fix_calls} calls; worst case ${fix_worst:.2f}."
    )
    print(
        f"Expected about ${expected:.2f}, at the demo examples' ${typical:.4f} a call; "
        f"hard cap ${args.cap:.2f} ({MODEL}; prices of {pricing.PRICES_CHECKED})."
    )
    if args.plan:
        return
    try:
        client = BudgetedClient(anthropic.Anthropic(api_key=get_api_key()),
                                Budget(args.cap, LEDGER))  # fmt: skip
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    DEV_RUN.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DEV_SOURCE, DEV_RUN / "cache", dirs_exist_ok=True)
    try:
        rows = explain_dev(client)
        record = fix_step(client)
    except (RunStopped, NotCached) as stop:
        sys.exit(f"stopped: {stop}. Spent ${client.budget.spent_usd:.4f}; run it again to "
                 "resume (what's done replays for free).")  # fmt: skip
    explained = sum(r["explanation"] is not None for r in rows)
    print(f"Part 1: {explained} explanations, in {DEV_RUN.relative_to(ROOT)}/explanations.jsonl")
    chosen = record["chosen"]
    print(
        "Part 2: "
        + (
            f"chosen {chosen['candidate']} sample {chosen['sample']} ({chosen['folder']})"
            if chosen
            else f"no try of {len(record['tries'])} showed the loop; nothing chosen"
        )
    )
    print(f"Spent ${client.budget.spent_usd:.4f} on {client.budget.calls} calls ({LEDGER}).")


if __name__ == "__main__":
    main()
