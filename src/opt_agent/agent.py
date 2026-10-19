"""The whole pipeline: word problem -> Claude's model (revised if it fails) -> CBC's solution
-> independent checks -> explanation.

Run:  python -m opt_agent.agent "A gas company can transport gas using a pipeline or by train. ..."
      (or pass - and pipe the problem in). Needs ANTHROPIC_API_KEY (see .env.example).
"""

import argparse
import sys
import time
from pathlib import Path

import anthropic
from pydantic import BaseModel

from opt_agent.api import Cache, CallInfo
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.explain import Explanation, explain, solver_facts
from opt_agent.formulate import DEFAULT_MODEL, Formulation
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
    wall_s: float = 0.0  # the whole pipeline, as measured; a replayed run is faster

    @property
    def calls(self) -> list[CallInfo]:
        formulations = [a.formulation.call for a in self.outcome.attempts]
        return formulations + ([self.explanation.call] if self.explanation else [])

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
    def verified(self) -> bool:
        """Solved to optimality, confirmed by HiGHS, and every constraint checks out.

        This verifies the *solution of Claude's model*, not that the model matches the text.
        """
        return (
            self.solution is not None
            and self.solution.status is Status.OPTIMAL
            and bool(self.highs_agrees)
            and not self.check_problems
        )


def run(
    problem: str,
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    with_explanation: bool = True,
    max_attempts: int = MAX_ATTEMPTS,
    session: Run | None = None,
    tags: Tags | None = None,
) -> Result:
    start = time.perf_counter()
    session = session or Run()
    outcome = solve_with_revisions(problem, client, model_id, max_attempts, session, tags)
    result = Result(problem=problem, outcome=outcome)
    model, solution = result.formulation.model, result.solution
    if solution is not None:
        result.highs_solution = outcome.final.highs_solution  # the loop solved with both
        result.highs_agrees = same_answer(model, solution, result.highs_solution)
        result.check_problems = check_solution(model, solution)
    if with_explanation and result.verified:  # never explain an answer that failed a check
        facts = solver_facts(model, solution)
        result.explanation = explain(problem, model, facts, client, model_id, session.cache)
        _log_explanation(session, tags, result.explanation)
    result.wall_s = time.perf_counter() - start
    _log_problem(session, tags, result)
    return result


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
              objective=s.objective if s else None, verified=result.verified,
              wall_s=round(result.wall_s, 3), latency_s=round(result.latency_s, 3),
              retry_s=round(result.retry_s, 3),
              cached_calls=sum(c.cached for c in result.calls))  # fmt: skip


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
        return "\n".join(lines + [f"NO ANSWER: {_failure(x)}." for x in failed])
    if result.highs_agrees is False:
        cbc, highs = _describe(s), _describe(result.highs_solution)
        return "\n".join(lines + [
            f"SOLVERS DISAGREE: CBC says {cbc}, HiGHS says {highs}. No answer is reported."
        ])  # fmt: skip
    lines.append(f"Status: {s.status}")
    if s.note:
        lines.append(f"  ({s.note})")
    if s.status is Status.OPTIMAL:
        lines.append(f"Objective: {s.objective:g}")
        lines += [f"  {name} = {value:g}" for name, value in s.values.items()]
    lines.append(f"Verified (HiGHS agrees, constraints check out): {result.verified}")
    lines += [f"  problem: {p}" for p in result.check_problems]
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
    args = parser.parse_args(argv)
    problem = sys.stdin.read() if args.problem == "-" else args.problem
    try:
        client = anthropic.Anthropic(api_key=get_api_key())
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    cache = None if args.no_cache else Cache(args.cache)
    session = Run.start(log_path=args.log, cache=cache)
    result = run(problem, client, args.model, not args.no_explanation, args.attempts, session)
    print(render(result))


if __name__ == "__main__":
    main()
