"""The demo's web app: one page and a small JSON API around pipeline.solve.

Run:  python -m opt_agent.demo                    # examples mode: no key, nothing is sent
      OPT_AGENT_LIVE=1 python -m opt_agent.demo   # live mode: the key in .env, or exported

Two modes, fixed when the app starts (Settings.from_env):
- **examples** (the default): POST /solve answers the example problems from their cached
  replies (replies/) through api.ReplayOnlyClient, which has no key and sends nothing. Any
  other text gets 404, since it would need a live call.
- **live** (OPT_AGENT_LIVE=1, and a key from config.get_api_key): the examples still replay
  for free; anything else calls Claude through budget.BudgetedClient, with a spend ledger
  and a dollar cap (OPT_AGENT_DEMO_CAP_USD, default $0.50 in all). The guards: one solve at
  a time (a second request gets 429 rather than queueing paid calls), problems of at most
  pipeline.MAX_PROBLEM_CHARS, and every reply capped at pipeline.MAX_TOKENS.

Endpoints: GET / (the page), GET /health, GET /examples, POST /solve {"problem": "..."}.
"""

import os
import threading
from dataclasses import dataclass
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from opt_agent import config
from opt_agent.api import Cache, NotCached, ReplayOnlyClient, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.demo import examples, pipeline

HERE = Path(__file__).resolve().parent
REPLIES = HERE / "replies"  # the examples' cached replies (scripts/cache_examples.py)
PAGE = HERE / "page.html"
CAP_VAR = "OPT_AGENT_DEMO_CAP_USD"
DEFAULT_CAP_USD = 0.50


@dataclass(frozen=True)
class Settings:
    mode: str  # "examples" or "live"
    api_key: str | None = None
    cap_usd: float = DEFAULT_CAP_USD
    ledger: Path = Path("logs/spend/demo.jsonl")  # live spend, kept across restarts
    live_cache: Path = Path("logs/demo/replies")  # live replies: asking again is free
    log: Path = Path("logs/demo/attempts.jsonl")  # every live call, as the CLI logs it
    replies: Path = REPLIES

    @classmethod
    def from_env(cls) -> "Settings":
        """Live only when OPT_AGENT_LIVE is exactly 1; then a missing key stops the app
        from starting (MissingAPIKeyError) instead of quietly falling back."""
        if os.environ.get(config.LIVE_VAR) != "1":
            return cls(mode="examples")
        cap = float(os.environ.get(CAP_VAR, DEFAULT_CAP_USD))
        return cls(mode="live", api_key=config.get_api_key(), cap_usd=cap)


class SolveRequest(BaseModel):
    problem: str


def create_app(settings: Settings | None = None, client=None) -> FastAPI:
    """`client`: for tests, a stand-in for the live client (tests/fakes.FakeClient)."""
    settings = settings or Settings.from_env()
    if settings.mode == "live" and client is None:
        client = BudgetedClient(anthropic.Anthropic(api_key=settings.api_key),
                                Budget(settings.cap_usd, settings.ledger))  # fmt: skip
    app = FastAPI(title="opt-agent demo", docs_url="/docs")
    app.state.one_at_a_time = threading.Lock()  # live calls: a second request gets 429

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return PAGE.read_text()

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "mode": settings.mode,
            "model": pipeline.MODEL,
            "max_problem_chars": pipeline.MAX_PROBLEM_CHARS,
            "max_tokens": pipeline.MAX_TOKENS,
            "examples_cached": sum(_cached(e.text, settings) for e in examples.EXAMPLES),
        }

    @app.get("/examples")
    def list_examples() -> list[dict]:
        return [e.model_dump() | {"cached": _cached(e.text, settings)}
                for e in examples.EXAMPLES]  # fmt: skip

    @app.post("/solve", response_model=pipeline.SolveResponse)
    def solve(request: SolveRequest) -> pipeline.SolveResponse:
        problem = request.problem.strip()
        if not problem:
            raise HTTPException(422, "the problem is empty")
        if len(problem) > pipeline.MAX_PROBLEM_CHARS:
            raise HTTPException(413, f"the problem is {len(problem):,} characters; this demo "
                                f"takes at most {pipeline.MAX_PROBLEM_CHARS:,}")  # fmt: skip
        example = examples.BY_TEXT.get(problem)
        if example is not None:  # both modes: an example replays from its cache, for free
            return _replay(problem, example, settings)
        if settings.mode == "examples":
            raise HTTPException(404, "examples mode solves only the example problems, from "
                                "their cached replies; anything else needs a live call (run "
                                "with OPT_AGENT_LIVE=1 and your own key)")  # fmt: skip
        if not app.state.one_at_a_time.acquire(blocking=False):
            raise HTTPException(429, "busy: live mode solves one problem at a time")
        try:
            result = pipeline.solve(problem, client, Cache(settings.live_cache), settings.log)
        except RunStopped as stop:  # the dollar cap, or the account's spend limit
            raise HTTPException(503, f"no more live calls: {stop}") from None
        finally:
            app.state.one_at_a_time.release()
        return pipeline.to_response(result, "live")

    return app


def _replay(problem: str, example: examples.Example, settings: Settings):
    try:
        result = pipeline.solve(problem, ReplayOnlyClient(), Cache(settings.replies))
    except NotCached:
        raise HTTPException(503, f"the replies for example '{example.id}' aren't cached yet "
                            "(scripts/cache_examples.py)") from None  # fmt: skip
    return pipeline.to_response(result, settings.mode, example)


def _cached(problem: str, settings: Settings) -> bool:
    """Whether the example's first call (its formulation) replays; the rest follow it."""
    return pipeline.first_call_cached(problem, Cache(settings.replies))
