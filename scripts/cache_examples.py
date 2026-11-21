"""Cache the demo examples' replies in src/opt_agent/demo/replies/, so the demo's examples
mode replays them with no key. PAID: run it only in the owner's terminal.

It caches what the refreshed demo needs (pipeline.REFRESHED): each example solved with the
demo's settings (demo.pipeline.solve: up to 3 formulations, a direct estimate, a checklist
and an explanation, which for an integer program carries ADR-0009's limits), and four more
single-shot formulation samples for the disagreement badge (pipeline.extra_samples). The
example that replays the resampling study's own replies (pipeline.STUDY) is cached already
and sends nothing. Whatever is cached replays for free, so a run pays only for what's
missing, and --plan counts exactly that without a call: each missing sample's formulation
and each missing explanation (a missing first formulation means the whole example, bounded
by worst_case_usd). Every call goes through budget.BudgetedClient with its own ledger
(logs/spend/demo-examples.jsonl), so the cap is never crossed. Each outcome is printed next
to the example's reference answer; a mismatch is reported, never retried (the cache keeps
the first reply, as the studies did). After a run, pipeline.REFRESHED turns True.

Run:  python scripts/cache_examples.py --plan                       # what's missing; no calls
      OPT_AGENT_LIVE=1 python scripts/cache_examples.py --cap 0.15   # pays for the replies
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

import anthropic

from opt_agent import api, explain, formulate, pricing
from opt_agent.api import Cache, ReplayOnlyClient
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.demo import pipeline
from opt_agent.demo.app import REPLIES
from opt_agent.demo.examples import EXAMPLES, Example

LEDGER = Path("logs/spend/demo-examples.jsonl")
LOG = Path("logs/demo/cache-examples.jsonl")
CAP_USD = 0.15
# A later request carries an earlier reply (a revision repeats the previous model; the
# explanation, the model and its numbers). A reply is at most MAX_TOKENS tokens, and a
# token is at most this many bytes of text, so this bounds what a later request can add.
BYTES_PER_TOKEN = 4


def worst_case_usd(problem: str) -> float:
    """An upper bound on one solve: every call as large as the first formulation request
    plus a whole reply, and each reply using all of MAX_TOKENS."""
    with api.max_tokens_cap(pipeline.MAX_TOKENS):
        request = formulate.build_request(problem, pipeline.MODEL)
    padded = request | {"padding": "x" * (pipeline.MAX_TOKENS * BYTES_PER_TOKEN)}
    return pipeline.CALLS_PER_SOLVE * pricing.worst_case_usd(padded)


def missing(example: Example, cache: Cache) -> list[tuple[str, dict | None]]:
    """What a refreshed solve of `example` would send that `cache` doesn't hold, as (kind,
    request): "example" (its first formulation, so everything), "formulation" or
    "explanation"."""
    profile = pipeline.profile_for(example, refreshed=True)
    if not pipeline.first_call_cached(example.text, cache, profile):
        return [("example", None)]
    found: list[tuple[str, dict | None]] = []
    with api.max_tokens_cap(profile.max_tokens):
        request = formulate.build_request(example.text, pipeline.MODEL)
    for sample in profile.samples[1:]:  # each is single-shot: one call if it isn't cached
        mine = Cache(cache.directory, sample)
        if mine.get(mine.key(request)) is None:
            found.append(("formulation", request))
    if profile.explain:
        quiet = profile.model_copy(update={"explain": False})
        result = pipeline.solve(example.text, ReplayOnlyClient(), cache, profile=quiet)  # type: ignore[arg-type]
        if result.verified:
            model, solution = result.formulation.model, result.solution
            assert model is not None and solution is not None  # verified: a model, solved
            facts = explain.solver_facts(model, solution, with_limits=True)
            with api.max_tokens_cap(profile.max_tokens):
                request = explain.build_request(example.text, model, facts, pipeline.MODEL)
            mine = Cache(cache.directory, profile.samples[0])
            if mine.get(mine.key(request)) is None:
                found.append(("explanation", request))
    return found


def mean_usd(system_prompt: str) -> float:
    """What the committed replies to requests with this system prompt cost, on average."""
    costs = []
    for path in sorted(REPLIES.glob("*.json")):
        entry = json.loads(path.read_text())
        if entry["request"]["system"] == system_prompt:
            message = anthropic.types.Message.model_validate(entry["response"])
            costs.append(pricing.cost_usd(api.usage_of(message), pipeline.MODEL))
    return statistics.mean(costs)


def plan(cache: Cache) -> dict:
    calls = {"example": 0, "formulation": 0, "explanation": 0}
    worst = 0.0
    for example in EXAMPLES:
        for kind, request in missing(example, cache):
            calls[kind] += 1
            worst += (worst_case_usd(example.text) if request is None
                      else pricing.worst_case_usd(request))  # fmt: skip
    # the committed explanations predate ADR-0009's limits, which add a paragraph and a few
    # lines of facts: their mean is a slight underestimate for the new ones
    expected = (calls["formulation"] * mean_usd(formulate.SYSTEM_PROMPT)
                + calls["explanation"] * mean_usd(explain.SYSTEM_PROMPT))  # fmt: skip
    return {"calls": calls, "worst_usd": worst, "expected_usd": expected}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Cache the demo examples' replies (paid).")
    parser.add_argument("--cap", type=float, default=CAP_USD, help="USD for all the examples")
    parser.add_argument("--plan", action="store_true", help="what's missing; no calls")
    args = parser.parse_args(argv)
    cache = Cache(REPLIES)
    p = plan(cache)
    c = p["calls"]
    print(f"Missing: {c['formulation']} formulation samples, {c['explanation']} explanations"
          + (f", and {c['example']} whole examples" if c["example"] else "")
          + f"; worst case ${p['worst_usd']:.2f}, expected about ${p['expected_usd']:.3f} at "
          f"the committed replies' mean cost; cap ${args.cap:.2f} ({pipeline.MODEL}, prices "
          f"of {pricing.PRICES_CHECKED}).")  # fmt: skip
    if args.plan:
        return
    try:
        client = anthropic.Anthropic(api_key=get_api_key())
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    budget = Budget(args.cap, LEDGER)
    for example in EXAMPLES:
        profile = pipeline.profile_for(example, refreshed=True)
        paid = BudgetedClient(client, budget)
        result = pipeline.solve(example.text, paid, cache, LOG, profile, explain_limits=True)
        samples = pipeline.extra_samples(example.text, paid, cache, profile, LOG)
        r = pipeline.to_response(result, "examples", example, samples)
        verdict = "VERIFIED" if r.verification.verified else f"NOT VERIFIED ({r.stopped})"
        match = {True: "matches", False: "DOESN'T MATCH", None: "nothing to compare"}
        badge = {True: "samples disagree", False: "samples agree", None: "no badge"}
        print(f"{example.id:9} {verdict}; objective {r.objective} vs the {r.reference_kind} "
              f"{example.reference_objective:g}: {match[r.matches_reference]}; "
              f"{badge[r.disagreement.samples_disagree]}; {r.calls} calls "
              f"({r.cached_calls} cached), ${r.paid_usd:.4f} paid")  # fmt: skip
    print(f"Spent ${budget.spent_usd:.4f} on {budget.calls} calls in all ({LEDGER}).")
    print(f"Then: commit the replies (git add {REPLIES.relative_to(Path.cwd().resolve())}), "
          "and pipeline.REFRESHED turns True.")  # fmt: skip


if __name__ == "__main__":
    main()
