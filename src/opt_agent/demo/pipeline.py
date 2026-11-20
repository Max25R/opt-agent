"""The demo's pipeline: agent.run with fixed settings, and the JSON the page shows.

The settings are fixed rather than chosen per request because the examples replay from
their cache, and a cached reply is found only if each request is built exactly as it was
when it was cached (api.cache_key covers the model, the prompts, max_tokens and the
sampling settings). scripts/cache_examples.py calls the same solve().

- MODEL and MAX_ATTEMPTS: the evaluated model and self-correction's 3 attempts (M6).
- MAX_TOKENS: 8,000 per reply, half the studies' 16,000, set with api.max_tokens_cap. A
  live-mode guard: it halves the worst case of every call. NL4Opt-sized problems never came
  near it (M6's longest formulation reply was 3,409 tokens); a reply that hits it is a loud
  failure ("cut off"), never a wrong answer.
- estimate and checklist: on, so the page shows both report-only flags (agent.py). They
  change no answer, check or revision.
- The disagreement badge (report-only too): the resampling study's flag, as far as one solve
  can check it (samples_disagree), shown with what the study measured (MEASURED).
- MAX_PROBLEM_CHARS: the longest problem accepted, a live-mode guard against pasting a
  document (the examples are about 600 characters; NL4Opt's are shorter).
"""

from pathlib import Path
from typing import cast

import anthropic
from pydantic import BaseModel

from opt_agent import agent, api, formulate, pricing
from opt_agent.api import Cache
from opt_agent.explain import solver_facts
from opt_agent.followup_report import same_answer
from opt_agent.formulate import DEFAULT_MODEL
from opt_agent.runs import Run
from opt_agent.schema import LPModel
from opt_agent.self_correct import MAX_ATTEMPTS
from opt_agent.solver import Solution, Status

MODEL = DEFAULT_MODEL
MAX_TOKENS = 8_000
MAX_PROBLEM_CHARS = 4_000
CALLS_PER_SOLVE = MAX_ATTEMPTS + 3  # the formulations, the estimate, the checklist, the explanation
# The committed example replies were cached before ADR-0009, so their explanation requests carry
# no limits, and a replay must send the same requests: until those replies are refreshed (a paid
# run, the owner's), the demo explains without them, in both modes, so the two modes match.
EXPLAIN_LIMITS = False
ANALYSIS_URL = "https://github.com/Max25R/opt-agent/blob/main/docs/resampling/RESULTS.md"


class Measured(BaseModel):
    """The resampling study's pre-registered disagreement flag, as the study measured it
    (results/resampling.json, r1): counts, so the page shows each rate with what it's of."""

    answers: int  # the units: verified single-shot answers, one per problem
    precision: tuple[int, int]  # silent failures, of the flagged answers
    recall: tuple[int, int]  # flagged, of the silent failures
    base_rate: tuple[int, int]  # silent failures, of all the answers
    analysis: str  # where it's written up


# Copied from results/resampling.json, since the image has no results/: tests/test_demo.py
# checks each count against the file, and that R1 was supported (why the badge exists).
MEASURED = Measured(answers=119, precision=(20, 38), recall=(20, 29), base_rate=(29, 119),
                    analysis=ANALYSIS_URL)  # fmt: skip


class Disagreement(BaseModel):
    """Report-only, like the other flags. The study flagged an answer when five formulation
    samples didn't all agree or the no-solver answer differed. One solve here has one
    formulation, so the page checks the part it can: the verified answer against Claude's
    direct answer, which is the no-solver baseline's own request (baseline.build_request)."""

    samples_disagree: bool | None  # None: no verified answer, so nothing the study would flag
    measured: Measured


def samples_disagree(result: agent.Result) -> bool | None:
    """The study's no-solver signal on this answer, by its own rules (pre-registration,
    section 4): only a verified answer is a unit, the comparison is the follow-up's
    (followup_report.same_answer, 1e-4), and a missing direct answer counts as one that
    differs."""
    if not result.verified or result.estimate is None:
        return None
    s, e = cast(Solution, result.solution), result.estimate
    direct = None if e.status is None else (e.status, e.objective)
    return not same_answer(direct, (s.status.value, s.objective))


def solve(problem: str, client: anthropic.Anthropic, cache: Cache, log: Path | None = None):
    """agent.run with the demo's settings. Every reply comes from `cache` when it's there;
    otherwise from `client` (api.ReplayOnlyClient raises api.NotCached instead)."""
    session = Run.start(log_path=log, cache=cache) if log else Run(cache=cache)
    with api.max_tokens_cap(MAX_TOKENS):
        return agent.run(problem, client, MODEL, with_explanation=True,
                         max_attempts=MAX_ATTEMPTS, session=session, estimate=True,
                         checklist=True, explain_limits=EXPLAIN_LIMITS)  # fmt: skip


def first_call_cached(problem: str, cache: Cache) -> bool:
    """Whether the problem's first call (its formulation, as solve() builds it) is in
    `cache`. Every later request depends on earlier replies, so this is what a cheap check
    can say; a replay that misses later raises api.NotCached."""
    with api.max_tokens_cap(MAX_TOKENS):
        request = formulate.build_request(problem, MODEL)
    return cache.get(cache.key(request)) is not None


# ---- the response -----------------------------------------------------------------------


class Verification(BaseModel):
    cbc: str  # CBC's verdict, in words ("optimal, 1600")
    highs: str | None  # HiGHS's, solved independently; None if there was no model to solve
    solvers_agree: bool | None
    check_problems: list[str]  # the arithmetic checks (verify.check_solution); [] = pass
    confirmed: bool  # both solvers agree and the checks pass, whatever the status
    verified: bool  # confirmed, and optimal: the only answers that get an explanation


class AttemptView(BaseModel):
    number: int
    outcome: str  # the model's status, or why the reply couldn't be used
    feedback: str | None  # what the next attempt was told
    cached: bool


class SolveResponse(BaseModel):
    mode: str  # "examples" or "live"
    example: str | None  # the example's id, if the text is one of them
    reference_objective: float | None  # that example's hand-checked answer
    matches_reference: bool | None  # a verified answer equal to it (None: nothing to compare)
    stopped: str  # why the loop stopped (self_correct.StopReason)
    attempts: list[AttemptView]
    revision_flags: list[str]  # revisions that deleted or loosened something
    model_lines: list[str]  # Claude's model, as the CLI prints it (agent.format_model)
    model: dict | None  # the same model as JSON (schema.LPModel)
    model_error: str | None  # why no attempt gave a usable model
    status: str | None  # CBC's status for the final model
    objective: float | None  # only for a verified optimum: nothing else is an answer
    values: dict[str, float]
    binding: list[str]  # constraints with no slack at the optimum
    verification: Verification
    explanation: str | None
    explanation_unsupported: list[str]  # numbers in it that no solver fact backs up
    explanation_problem: str | None
    low_confidence: bool | None  # report-only: Claude's direct estimate disagrees
    low_confidence_reason: str | None
    checklist_flags: list[dict] | None  # report-only: differences from what the text needs
    checklist_notes: list[str]
    disagreement: Disagreement
    calls: int
    cached_calls: int
    cost_usd: float  # every call, at the token counts it was answered with
    paid_usd: float  # only the calls made now (0 when everything replays)


def to_response(result: agent.Result, mode: str, example=None) -> SolveResponse:
    model, s, h = result.formulation.model, result.solution, result.highs_solution
    priced = [(x.usage, x.call) for x in result.formulations]
    priced += [(x.usage, x.call) for x in (result.estimate, result.checklist, result.explanation)
               if x is not None]  # fmt: skip
    costs = [pricing.cost_usd(usage, MODEL) for usage, _ in priced]
    reference = example.reference_objective if example else None
    matches = None
    if reference is not None and result.verified:
        assert s is not None and s.objective is not None  # verified: an optimum
        matches = abs(s.objective - reference) <= 1e-6 * max(1.0, abs(reference))
    e = result.explanation
    # The verified optimum as the explanation was told it (round-off dropped), and which
    # constraints bind, by the same tolerance the explanation's facts use.
    facts = solver_facts(cast(LPModel, model), cast(Solution, s)) if result.verified else None
    return SolveResponse(
        mode=mode,
        example=example.id if example else None,
        reference_objective=reference,
        matches_reference=matches,
        stopped=result.outcome.stopped,
        attempts=[_attempt(a) for a in result.outcome.attempts],
        revision_flags=result.outcome.flags,
        model_lines=agent.format_model(model) if model else [],
        model=model.model_dump(mode="json") if model else None,
        model_error=None if model else result.formulation.error,
        status=s.status.value if s else None,
        objective=facts.objective if facts else None,
        values=facts.values if facts else {},
        binding=facts.binding if facts else [],
        verification=Verification(
            cbc=_verdict(s) if s else "no model to solve",
            highs=_verdict(h) if h else None,
            solvers_agree=result.highs_agrees,
            check_problems=result.check_problems,
            confirmed=result.confirmed,
            verified=result.verified,
        ),
        explanation=e.text if e else None,
        explanation_unsupported=e.unsupported_numbers if e else [],
        explanation_problem=e.problem if e else None,
        low_confidence=result.low_confidence,
        low_confidence_reason=result.low_confidence_reason,
        checklist_flags=None if result.checklist_flags is None
        else [f.model_dump() for f in result.checklist_flags],
        checklist_notes=result.checklist_notes,
        disagreement=Disagreement(samples_disagree=samples_disagree(result), measured=MEASURED),
        calls=len(priced),
        cached_calls=sum(call.cached for _, call in priced),
        cost_usd=sum(costs),
        paid_usd=sum(c for c, (_, call) in zip(costs, priced, strict=True) if not call.cached),
    )  # fmt: skip


def _attempt(a) -> AttemptView:
    f = a.formulation
    outcome = a.solution.status.value if a.solution else f"unusable reply: {f.error}"
    if f.api_failed:
        outcome = f"API error: {f.error}"
    return AttemptView(number=a.number, outcome=outcome, feedback=a.feedback,
                       cached=f.call.cached)  # fmt: skip


def _verdict(solution: Solution) -> str:
    if solution.status is Status.OPTIMAL:
        return f"optimal, {solution.objective:g}"
    return solution.note or solution.status.value
