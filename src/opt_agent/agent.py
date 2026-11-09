"""The whole pipeline: word problem -> Claude's model (revised if it fails) -> CBC's solution
-> independent checks -> explanation.

With `estimate`, Claude is also asked for the answer directly, with no solver (the no-solver
baseline's request, baseline.py), and a confirmed answer that disagrees with that estimate
beyond the scoring tolerance is marked low confidence (audit, finding 2): every failure in
M6 was a confirmed answer to a wrong model, which verification can't see, and a direct
answer that disagrees is a cheap sign of one. The flag is report-only: it's computed after
everything else and changes no answer, check or revision.

With `checklist`, a separate call lists what a correct formulation of the text must contain,
given only the text and the model's variable names (checklist.py), and every difference from
the model becomes a typed flag in `checklist_flags`. Report-only too, in the same way.

Run:  python -m opt_agent.agent "A gas company can transport gas using a pipeline or by train. ..."
      (or pass - and pipe the problem in). Needs ANTHROPIC_API_KEY exported, or
      OPT_AGENT_LIVE=1 to use the key in .env (see .env.example).
"""

import argparse
import sys
import time
from pathlib import Path

import anthropic
from pydantic import BaseModel

from opt_agent.api import Cache, CallInfo
from opt_agent.baseline import DirectAnswer, answer_directly
from opt_agent.checklist import ChecklistFlag, ChecklistReply
from opt_agent.checklist import ask as ask_checklist
from opt_agent.checklist import review as review_checklist
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.explain import Explanation, explain, solver_facts
from opt_agent.formulate import DEFAULT_MODEL, Formulation
from opt_agent.ground_truth import TOLERANCE, same_value
from opt_agent.runs import Run, Tags
from opt_agent.schema import LPModel, Term
from opt_agent.self_correct import MAX_ATTEMPTS, Outcome, solve_with_revisions
from opt_agent.solver import Solution, Status
from opt_agent.verify import check_solution, same_answer

DEFAULT_LOG = Path("logs/attempts.jsonl")
DEFAULT_CACHE = Path("cache/responses")


class Result(BaseModel):
    problem: str
    outcome: Outcome  # every attempt, and why the loop stopped
    highs_solution: Solution | None = None  # the independent second opinion
    highs_agrees: bool | None = None  # False is a loud failure: no answer is reported
    check_problems: list[str] = []  # from verify.check_solution: [] means it checks out
    explanation: Explanation | None = None  # only for verified answers
    estimate: DirectAnswer | None = None  # Claude's direct answer, if one was asked for
    # True: the estimate disagrees with the confirmed answer. None: nothing to compare.
    low_confidence: bool | None = None
    low_confidence_reason: str | None = None
    checklist: ChecklistReply | None = None  # the checklist call, if one was asked for
    checklist_flags: list[ChecklistFlag] | None = None  # None: not asked, or nothing to check
    checklist_notes: list[str] = []  # what the checklist couldn't check, and why
    wall_s: float = 0.0  # the whole pipeline, as measured; a replayed run is faster

    @property
    def calls(self) -> list[CallInfo]:
        formulations = [a.formulation.call for a in self.outcome.attempts]
        extra = [x.call for x in (self.estimate, self.checklist, self.explanation) if x]
        return formulations + extra

    @property
    def retry_s(self) -> float:
        """Time lost to failed tries and waits: kept out of latency, reported apart."""
        return sum(c.retry_s for c in self.calls)

    @property
    def latency_s(self) -> float:
        """API time plus solver time, without retries. Unlike wall_s, a replayed run
        reports the original calls' times, so this survives resuming from the cache."""
        return sum(c.latency_s for c in self.calls) + sum(a.solve_s for a in self.outcome.attempts)

    @property
    def formulation(self) -> Formulation:
        return self.outcome.final.formulation

    @property
    def solution(self) -> Solution | None:
        return self.outcome.final.solution  # None if no attempt produced a usable model

    @property
    def confirmed(self) -> bool:
        """CBC and HiGHS reach the same verdict and the arithmetic checks pass, whatever the
        status: "infeasible" and "unbounded" (which needs a certified ray) count too. A
        time-out or solver error never does. Like `verified`, this is about Claude's model,
        not about whether the model matches the text."""
        return self.solution is not None and bool(self.highs_agrees) and not self.check_problems

    @property
    def verified(self) -> bool:
        """Confirmed, and optimal: an answer with numbers that can be explained."""
        return self.confirmed and self.solution.status is Status.OPTIMAL


def run(
    problem: str,
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    with_explanation: bool = True,
    max_attempts: int = MAX_ATTEMPTS,
    session: Run | None = None,
    tags: Tags | None = None,
    estimate: bool = False,
    checklist: bool = False,
) -> Result:
    """`estimate`: also ask for a direct answer (one more call) and set low_confidence.
    `checklist`: also ask for a formulation checklist (one more call) and set
    checklist_flags. Neither changes the answer, the checks or the revisions."""
    start = time.perf_counter()
    session = session or Run()
    outcome = solve_with_revisions(problem, client, model_id, max_attempts, session, tags)
    result = Result(problem=problem, outcome=outcome)
    model, solution = result.formulation.model, result.solution
    if solution is not None:
        result.highs_solution = outcome.final.highs_solution  # the loop solved with both
        result.highs_agrees = same_answer(model, solution, result.highs_solution)
        result.check_problems = check_solution(model, solution)
    if estimate:  # after the loop and the checks, so it can't change either
        result.estimate = answer_directly(problem, client, model_id, session.cache)
        _log_estimate(session, tags, result.estimate)
        result.low_confidence, result.low_confidence_reason = confidence(result)
    if checklist:  # likewise after everything that decides the answer
        _check_formulation(problem, client, model_id, session, tags, result)
    if with_explanation and result.verified:  # never explain an answer that failed a check
        facts = solver_facts(model, solution)
        result.explanation = explain(problem, model, facts, client, model_id, session.cache)
        _log_explanation(session, tags, result.explanation)
    result.wall_s = time.perf_counter() - start
    _log_problem(session, tags, result)
    return result


def confidence(result: Result) -> tuple[bool | None, str]:
    """Does Claude's direct estimate disagree with the confirmed answer, beyond the scoring
    tolerance (ground_truth.TOLERANCE, 1e-6)? None when there's nothing to compare."""
    e, s = result.estimate, result.solution
    if e.status is None:
        return None, f"no direct estimate to compare ({e.error})"
    if not result.confirmed:
        return None, "no confirmed answer to compare the direct estimate with"
    if e.status != s.status:
        estimated, solved = _said(e.status, e.objective), _said(s.status, s.objective)
        return True, f"the direct estimate says {estimated}, the solver {solved}"
    if s.status is Status.OPTIMAL and not same_value(e.objective, s.objective, TOLERANCE):
        return True, f"the direct estimate is {e.objective:g}, the solver's optimum {s.objective:g}"
    return False, "the direct estimate agrees with the solver's answer"


def _check_formulation(
    problem: str, client: anthropic.Anthropic, model_id: str, session: Run, tags: Tags | None,
    result: Result,
) -> None:  # fmt: skip
    model = result.formulation.model
    if model is None:
        result.checklist_notes = ["no usable model to check"]
        return
    names = [v.name for v in model.variables]
    result.checklist = ask_checklist(problem, names, client, model_id, session.cache)
    c = result.checklist
    session.write("checklist", tags, model_id=c.model_id, request_sha256=c.call.request_sha256,
                  request=c.request, reply=c.raw_text, stop_reason=c.stop_reason,
                  usage=c.usage.model_dump(), call=c.call.model_dump(), error=c.error)  # fmt: skip
    if c.checklist is None:
        result.checklist_notes = [f"no usable checklist: {c.error}"]
        return
    found = review_checklist(model, c.checklist)
    result.checklist_flags, result.checklist_notes = found.flags, found.notes


def _said(status: Status, objective: float | None) -> str:
    return f"optimal ({objective:g})" if status is Status.OPTIMAL else status.value


def _log_estimate(session: Run, tags: Tags | None, a: DirectAnswer) -> None:
    session.write("estimate", tags, model_id=a.model_id, request_sha256=a.call.request_sha256,
                  request=a.request, reply=a.raw_text, stop_reason=a.stop_reason,
                  usage=a.usage.model_dump(), call=a.call.model_dump(), error=a.error,
                  status=a.status, objective=a.objective)  # fmt: skip


def _log_explanation(session: Run, tags: Tags | None, e: Explanation) -> None:
    session.write("explanation", tags, request_sha256=e.call.request_sha256, request=e.request,
              reply=e.text, stop_reason=e.stop_reason, usage=e.usage.model_dump(),
              call=e.call.model_dump(), problem=e.problem,
              unsupported_numbers=e.unsupported_numbers)  # fmt: skip


def _log_problem(session: Run, tags: Tags | None, result: Result) -> None:
    """One line per problem: what the evaluation counts, failures included."""
    s = result.solution
    session.write("problem", tags, stopped=result.outcome.stopped,
              attempts=len(result.outcome.attempts), status=s.status.value if s else None,
              objective=s.objective if s else None, confirmed=result.confirmed,
              verified=result.verified,
              wall_s=round(result.wall_s, 3), latency_s=round(result.latency_s, 3),
              retry_s=round(result.retry_s, 3),
              cached_calls=sum(c.cached for c in result.calls),
              low_confidence=result.low_confidence,
              checklist_flags=None if result.checklist_flags is None
              else [f.model_dump() for f in result.checklist_flags])  # fmt: skip


# ---- command line ----------------------------------------------------------------------


def render(result: Result) -> str:
    lines = [_attempt_line(a) for a in result.outcome.attempts]
    lines.append(f"Stopped: {result.outcome.stopped}")
    lines += [f"  flagged revision: {flag}" for flag in result.outcome.flags]
    f = result.formulation
    if f.model is None:
        return "\n".join(lines + ["", "No usable model:", f.error])
    lines += ["", *format_model(f.model), ""]
    s = result.solution
    failed = [x for x in (s, result.highs_solution) if x.failed]
    if failed:  # checked first: a time-out is no verdict, so it can't "disagree"
        lines += [f"NO ANSWER: {_failure(x)}." for x in failed]
        return "\n".join(lines + _checklist_lines(result))
    if result.highs_agrees is False:
        cbc, highs = _describe(s), _describe(result.highs_solution)
        lines.append(
            f"SOLVERS DISAGREE: CBC says {cbc}, HiGHS says {highs}. No answer is reported."
        )
        return "\n".join(lines + _checklist_lines(result))
    lines.append(f"Status: {s.status}")
    if s.note:
        lines.append(f"  ({s.note})")
    if s.status is Status.OPTIMAL:
        lines.append(f"Objective: {s.objective:g}")
        lines += [f"  {name} = {value:g}" for name, value in s.values.items()]
    lines.append(f"Verified (HiGHS agrees, constraints check out): {result.verified}")
    lines += [f"  problem: {p}" for p in result.check_problems]
    if result.low_confidence:
        lines.append(f"LOW CONFIDENCE: {result.low_confidence_reason}.")
    lines += _checklist_lines(result)
    e = result.explanation
    if e:
        lines += ["", e.text] if e.text else [""]
        if e.problem:
            lines.append(f"(explanation flagged: {e.problem})")
        if e.unsupported_numbers:
            lines.append(
                f"(not backed by the solver's numbers: {', '.join(e.unsupported_numbers)})"
            )
    return "\n".join(lines)


def _checklist_lines(result: Result) -> list[str]:
    """The checklist's flags (report-only), and anything it couldn't check."""
    lines = []
    if result.checklist_flags:
        lines.append(f"CHECKLIST: {len(result.checklist_flags)} difference(s) from the text:")
        lines += [f"  {flag.kind}: {flag.detail}" for flag in result.checklist_flags]
    elif result.checklist_flags is not None:
        lines.append("Checklist: no differences from the text found.")
    lines += [f"  (checklist: {note})" for note in result.checklist_notes]
    return lines


SOLVER_NAMES = {"cbc": "CBC", "highs": "HiGHS"}


def _failure(solution: Solution) -> str:
    name = SOLVER_NAMES[solution.solver]
    return solution.note or f"{name} stopped without an answer ({solution.status})"


def _describe(solution: Solution) -> str:
    if solution.status is Status.OPTIMAL:
        return f"optimal ({solution.objective:g})"
    return solution.status.value


def _attempt_line(attempt) -> str:
    f = attempt.formulation
    what = attempt.solution.status.value if attempt.solution else "unusable reply"
    if f.api_failed:
        what = "API error"
    timing = "cached" if f.call.cached else f"{f.call.latency_s:.1f} s"
    if f.call.retry_s:
        timing += f", plus {f.call.retry_s:.1f} s retrying"
    return (f"Attempt {attempt.number}: {what} ({f.model_id}, {f.usage.input_tokens} in / "
            f"{f.usage.output_tokens} out, {timing})")  # fmt: skip


def format_model(model: LPModel) -> list[str]:
    def expression(terms: list[Term]) -> str:
        return " + ".join(f"{t.coef:g}*[{t.var}]" for t in terms).replace("+ -", "- ")

    kinds = {v.name: "integer" if v.integer else "continuous" for v in model.variables}
    lines = [f"{model.objective.sense} {expression(model.objective.terms)}"]
    lines += [f"  {c.name}: {expression(c.terms)} {c.sense} {c.rhs:g}" for c in model.constraints]
    lines += [f"  {v.name}: {kinds[v.name]}, {_bounds(v.lower, v.upper)}" for v in model.variables]
    return lines


def _bounds(lower: float | None, upper: float | None) -> str:
    low = "-inf" if lower is None else f"{lower:g}"
    high = "inf" if upper is None else f"{upper:g}"
    return f"in [{low}, {high}]"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Solve a word problem with Claude + CBC.")
    parser.add_argument("problem", help="the problem text, or - to read it from stdin")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"default: {DEFAULT_MODEL}")
    parser.add_argument("--attempts", type=int, default=MAX_ATTEMPTS, help="1 = no revisions")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="JSONL log of the run")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="response cache")
    parser.add_argument("--no-cache", action="store_true", help="always call the API")
    parser.add_argument("--no-explanation", action="store_true", help="skip the last call")
    parser.add_argument("--estimate", action="store_true",
                        help="also ask for the answer directly (one more call) and flag a "
                             "confirmed answer that disagrees with it")  # fmt: skip
    args = parser.parse_args(argv)
    problem = sys.stdin.read() if args.problem == "-" else args.problem
    try:
        client = anthropic.Anthropic(api_key=get_api_key())
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    cache = None if args.no_cache else Cache(args.cache)
    session = Run.start(log_path=args.log, cache=cache)
    result = run(problem, client, args.model, not args.no_explanation, args.attempts, session,
                 estimate=args.estimate)  # fmt: skip
    print(render(result))


if __name__ == "__main__":
    main()
