"""Cache the demo examples' replies in src/opt_agent/demo/replies/, so the demo's examples
mode replays them with no key. PAID: run it only in the owner's terminal.

Each example is one solve with the demo's settings (demo.pipeline.solve): up to 3
formulations, a direct estimate, a checklist and an explanation, each reply capped at
pipeline.MAX_TOKENS. Every call goes through budget.BudgetedClient, with its own ledger
(logs/spend/demo-examples.jsonl), so the cap is never crossed. An example that's already
cached replays for free, so a re-run pays only for what's missing. Each outcome is printed
next to the example's hand-checked answer; a mismatch is reported, never retried (the cache
keeps the first reply, as the studies did).

Run:  python scripts/cache_examples.py --plan                       # worst case, no calls
      OPT_AGENT_LIVE=1 python scripts/cache_examples.py --cap 0.30   # pays for the replies
"""

import argparse
import sys
from pathlib import Path

import anthropic

from opt_agent import api, formulate, pricing
from opt_agent.api import Cache
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.demo import pipeline
from opt_agent.demo.app import REPLIES
from opt_agent.demo.examples import EXAMPLES

LEDGER = Path("logs/spend/demo-examples.jsonl")
LOG = Path("logs/demo/cache-examples.jsonl")
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Cache the demo examples' replies (paid).")
    parser.add_argument("--cap", type=float, default=0.30, help="USD for all the examples")
    parser.add_argument("--plan", action="store_true", help="print the worst case; no calls")
    args = parser.parse_args(argv)
    cache = Cache(REPLIES)
    missing = [e for e in EXAMPLES if not pipeline.first_call_cached(e.text, cache)]
    worst = sum(worst_case_usd(e.text) for e in missing)
    print(f"{len(missing)} of {len(EXAMPLES)} examples to cache, at most "
          f"{len(missing) * pipeline.CALLS_PER_SOLVE} calls; worst case ${worst:.4f} "
          f"({pipeline.MODEL}, replies capped at {pipeline.MAX_TOKENS:,} tokens); cap "
          f"${args.cap:.2f}.")  # fmt: skip
    if args.plan:
        return
    try:
        client = anthropic.Anthropic(api_key=get_api_key())
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    budget = Budget(args.cap, LEDGER)
    for example in EXAMPLES:
        result = pipeline.solve(example.text, BudgetedClient(client, budget), cache, LOG)
        r = pipeline.to_response(result, "examples", example)
        verdict = "VERIFIED" if r.verification.verified else f"NOT VERIFIED ({r.stopped})"
        match = {True: "matches", False: "DOESN'T MATCH", None: "nothing to compare"}
        print(f"{example.id:9} {verdict}; objective {r.objective} vs the hand-checked "
              f"{example.reference_objective:g}: {match[r.matches_reference]}; "
              f"{r.calls} calls ({r.cached_calls} cached), ${r.paid_usd:.4f} paid")  # fmt: skip
    print(f"Spent ${budget.spent_usd:.4f} on {budget.calls} calls in all ({LEDGER}).")
    print(f"Commit the replies: git add {REPLIES.relative_to(Path.cwd().resolve())}")


if __name__ == "__main__":
    main()
