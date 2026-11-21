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
from opt_agent.demo.examples import Example
from opt_agent.explain import solver_facts
from opt_agent.followup_report import Answer, same_answer
from opt_agent.formulate import DEFAULT_MODEL
from opt_agent.resampling_report import all_agree
from opt_agent.runs import Run
from opt_agent.schema import LPModel
from opt_agent.self_correct import MAX_ATTEMPTS
from opt_agent.solver import Solution, Status

MODEL = DEFAULT_MODEL
MAX_TOKENS = 8_000
MAX_PROBLEM_CHARS = 4_000
CALLS_PER_SOLVE = MAX_ATTEMPTS + 3  # the formulations, the estimate, the checklist, the explanation
# The four examples' replies were cached before ADR-0009 and before the badge drew five samples,
# and a replay has to send the requests it cached. scripts/cache_examples.py (a paid run, the
# owner's) caches what's missing: the integer examples' explanations with limits, and four more
# formulation samples of each example. Then REFRESHED turns True, and the demo explains with
# limits and draws five samples, in both modes, so the two modes match.
REFRESHED = True
EXPLAIN_LIMITS = REFRESHED
ANALYSIS_URL = "https://github.com/Max25R/opt-agent/blob/main/docs/resampling/RESULTS.md"


class Profile(BaseModel):
    """The settings a solve's replies are made with: a replay sends the same requests."""

    max_tokens: int  # each reply's cap
    max_attempts: int  # formulations for the answer; 1 is single-shot
    checklist: bool  # also ask for the formulation checklist (report-only)
    explain: bool  # explain a verified answer
    samples: tuple[int, ...]  # api.Cache samples: the answer's first, then the badge's others


def demo_profile(refreshed: bool = REFRESHED) -> Profile:
    """The demo's own settings: replies capped at MAX_TOKENS, three attempts, the checklist
    and the explanation, and (once refreshed) four more single-shot samples for the badge."""
    return Profile(max_tokens=MAX_TOKENS, max_attempts=MAX_ATTEMPTS, checklist=True,
                   explain=True, samples=(0, 1, 2, 3, 4) if refreshed else (0,))  # fmt: skip


# The resampling study's settings (its pre-registration, section 3), for an example that
# replays that run's recorded replies: single-shot samples 3 to 7 at the studies' max_tokens,
# its unit (sample 3) first, and only what the study asked for: the no-solver answer (sample 3),
# no checklist and no explanation.
STUDY = Profile(max_tokens=api.MAX_TOKENS, max_attempts=1, checklist=False, explain=False,
                samples=(3, 4, 5, 6, 7))  # fmt: skip


def profile_for(example: Example | None = None, refreshed: bool = REFRESHED) -> Profile:
    if example is not None and example.replay == "resampling":
        return STUDY
    return demo_profile(refreshed)


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


class AnswerView(BaseModel):
    status: str
    objective: float | None  # an optimum's only


class Disagreement(BaseModel):
    """Report-only, like the other flags: the resampling study's flag on this answer, by its
    pre-registration's rules (section 4). The answer and the profile's other formulation
    samples must all agree, and Claude's direct answer (the no-solver baseline's own request)
    must agree with the answer, by the follow-up's comparison (followup_report.same_answer,
    1e-4); a sample or a direct answer with no usable answer differs from any. Only a verified
    answer is one of the study's units, so nothing else gets a badge."""

    samples_disagree: bool | None  # None: no verified answer
    samples: list[AnswerView | None]  # the answer's first; None: no confirmed answer
    direct: AnswerView | None  # None: no usable direct answer
    measured: Measured


def answer_of(result: agent.Result) -> Answer | None:
    """A sample's answer, as the follow-up records one: a confirmed status, with an optimum's
    objective; None for a loud failure."""
    if not result.confirmed:
        return None
    s = cast(Solution, result.solution)
    return s.status.value, s.objective if s.status is Status.OPTIMAL else None


def direct_answer(result: agent.Result) -> Answer | None:
    e = result.estimate
    if e is None or e.status is None:
        return None
    return e.status, e.objective if e.status == Status.OPTIMAL else None


def disagreement(result: agent.Result, samples: list[agent.Result]) -> Disagreement:
    answers, direct = [answer_of(r) for r in [result, *samples]], direct_answer(result)
    flagged = None
    if result.verified:  # the study's unit: then the flag, exactly as resampling_report sets it
        flagged = not all_agree(answers) or not same_answer(direct, answers[0])

    def view(a: Answer | None) -> AnswerView | None:
        return None if a is None else AnswerView(status=a[0], objective=a[1])

    return Disagreement(samples_disagree=flagged, samples=[view(a) for a in answers],
                        direct=view(direct), measured=MEASURED)  # fmt: skip


def solve(
    problem: str,
    client: anthropic.Anthropic,
    cache: Cache,
    log: Path | None = None,
    profile: Profile | None = None,
    explain_limits: bool = EXPLAIN_LIMITS,
) -> agent.Result:
    """agent.run with a profile's settings (the demo's unless given), from the profile's first
    sample. Every reply comes from `cache` when it's there; otherwise from `client`
    (api.ReplayOnlyClient raises api.NotCached instead)."""
    profile = profile or demo_profile()
    cache = Cache(cache.directory, profile.samples[0])
    session = Run.start(log_path=log, cache=cache) if log else Run(cache=cache)
    with api.max_tokens_cap(profile.max_tokens):
        return agent.run(problem, client, MODEL, with_explanation=profile.explain,
                         max_attempts=profile.max_attempts, session=session, estimate=True,
                         checklist=profile.checklist, explain_limits=explain_limits)  # fmt: skip


def extra_samples(
    problem: str,
    client: anthropic.Anthropic,
    cache: Cache,
    profile: Profile | None = None,
    log: Path | None = None,
) -> list[agent.Result]:
    """The badge's other formulation samples: each single-shot, solved and checked like any
    answer, never explained. They replay from `cache` like the rest; in live mode each one
    that isn't there is a call."""
    profile, found = profile or demo_profile(), []
    for sample in profile.samples[1:]:
        mine = Cache(cache.directory, sample)
        session = Run.start(log_path=log, cache=mine) if log else Run(cache=mine)
        with api.max_tokens_cap(profile.max_tokens):
            found.append(agent.run(problem, client, MODEL, with_explanation=False,
                                   max_attempts=1, session=session))  # fmt: skip
    return found


def first_call_cached(problem: str, cache: Cache, profile: Profile | None = None) -> bool:
    """Whether the problem's first call (its formulation, as solve() builds it) is in
    `cache`. Every later request depends on earlier replies, so this is what a cheap check
    can say; a replay that misses later raises api.NotCached."""
    profile = profile or demo_profile()
    with api.max_tokens_cap(profile.max_tokens):
        request = formulate.build_request(problem, MODEL)
    mine = Cache(cache.directory, profile.samples[0])
    return mine.get(mine.key(request)) is not None


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
    reference_objective: float | None  # that example's reference answer
    reference_kind: str | None  # whose: "hand-checked", or the "benchmark's" answer key
    example_note: str | None  # why an example is here and where its text comes from, if said
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
    no_explanation: str | None  # why a verified answer wasn't explained, when that's by design
    low_confidence: bool | None  # report-only: Claude's direct estimate disagrees
    low_confidence_reason: str | None
    checklist_flags: list[dict] | None  # report-only: differences from what the text needs
    checklist_notes: list[str]
    disagreement: Disagreement
    calls: int
    cached_calls: int
    cost_usd: float  # every call, at the token counts it was answered with
    paid_usd: float  # only the calls made now (0 when everything replays)


def to_response(
    result: agent.Result,
    mode: str,
    example: Example | None = None,
    samples: list[agent.Result] | None = None,
) -> SolveResponse:
    """`samples`: the badge's other formulation samples (extra_samples), counted in the cost."""
    samples = samples or []
    model, s, h = result.formulation.model, result.solution, result.highs_solution
    priced = [(x.usage, x.call) for x in result.formulations]
    priced += [(x.usage, x.call) for x in (result.estimate, result.checklist, result.explanation)
               if x is not None]  # fmt: skip
    priced += [(x.usage, x.call) for r in samples for x in r.formulations]
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
        reference_kind=example.reference_kind if example else None,
        example_note=" ".join(n for n in (example.chosen, example.source and
                                          f"Problem text: {example.source}") if n) or None
        if example else None,
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
        no_explanation="The resampling study explained nothing, and this example replays only "
        "its recorded replies." if result.verified and e is None and example is not None
        and not profile_for(example).explain else None,
        low_confidence=result.low_confidence,
        low_confidence_reason=result.low_confidence_reason,
        checklist_flags=None if result.checklist_flags is None
        else [f.model_dump() for f in result.checklist_flags],
        checklist_notes=result.checklist_notes,
        disagreement=disagreement(result, samples),
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
