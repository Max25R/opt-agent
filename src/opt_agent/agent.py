"""The whole pipeline: word problem -> Claude's model (revised if it fails) -> CBC's solution
-> independent checks -> explanation.

Run:  python -m opt_agent.agent "A fishery wants to transport their catch. ..."
      (or pass - and pipe the problem in). Needs ANTHROPIC_API_KEY (see .env.example).
"""

import argparse
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel

from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.explain import Explanation, explain, solver_facts
from opt_agent.formulate import DEFAULT_MODEL, Formulation
from opt_agent.highs import solve_with_highs
from opt_agent.schema import LPModel, Term
from opt_agent.self_correct import MAX_ATTEMPTS, Outcome, solve_with_revisions
from opt_agent.solver import Solution, Status
from opt_agent.verify import check_solution, same_answer

DEFAULT_LOG = Path("logs/attempts.jsonl")


class Result(BaseModel):
    problem: str
    outcome: Outcome  # every attempt, and why the loop stopped
    highs_solution: Solution | None = None  # the independent second opinion
    highs_agrees: bool | None = None  # False is a loud failure: no answer is reported
    check_problems: list[str] = []  # from verify.check_solution: [] means it checks out
    explanation: Explanation | None = None  # only for verified answers

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
    log_path: Path | None = None,
) -> Result:
    outcome = solve_with_revisions(problem, client, model_id, max_attempts, log_path)
    result = Result(problem=problem, outcome=outcome)
    model, solution = result.formulation.model, result.solution
    if solution is None:
        return result
    result.highs_solution = solve_with_highs(model)
    result.highs_agrees = same_answer(model, solution, result.highs_solution)
    result.check_problems = check_solution(model, solution)
    if with_explanation and result.verified:  # never explain an answer that failed a check
        facts = solver_facts(model, solution)
        result.explanation = explain(problem, model, facts, client, model_id)
    return result


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
    if result.explanation:
        lines += ["", result.explanation.text]
        if result.explanation.unsupported_numbers:
            flagged = ", ".join(result.explanation.unsupported_numbers)
            lines.append(f"(not backed by the solver's numbers: {flagged})")
    return "\n".join(lines)


def _describe(solution: Solution) -> str:
    if solution.status is Status.OPTIMAL:
        return f"optimal ({solution.objective:g})"
    return solution.status.value


def _attempt_line(attempt) -> str:
    f = attempt.formulation
    what = attempt.solution.status.value if attempt.solution else "unusable reply"
    return (f"Attempt {attempt.number}: {what} ({f.model_id}, {f.usage.input_tokens} in / "
            f"{f.usage.output_tokens} out, {f.latency_s:.1f} s)")  # fmt: skip


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
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="JSONL log of attempts")
    parser.add_argument("--no-explanation", action="store_true", help="skip the last call")
    args = parser.parse_args(argv)
    problem = sys.stdin.read() if args.problem == "-" else args.problem
    try:
        client = anthropic.Anthropic(api_key=get_api_key())
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    result = run(problem, client, args.model, not args.no_explanation, args.attempts, args.log)
    print(render(result))


if __name__ == "__main__":
    main()
