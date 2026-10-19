"""The whole pipeline: word problem -> Claude's model -> CBC's solution -> checks -> explanation.

Run:  python -m opt_agent.agent "A fishery wants to transport their catch. ..."
      (or pass - and pipe the problem in). Needs ANTHROPIC_API_KEY (see .env.example).
"""

import argparse
import sys

import anthropic
from pydantic import BaseModel

from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.explain import Explanation, explain, solver_facts
from opt_agent.formulate import DEFAULT_MODEL, Formulation, formulate
from opt_agent.highs import solve_with_highs
from opt_agent.schema import LPModel, Term
from opt_agent.solver import Solution, Status, solve
from opt_agent.verify import check_solution, same_answer


class Result(BaseModel):
    problem: str
    formulation: Formulation
    solution: Solution | None = None  # None if Claude's reply couldn't be used
    highs_agrees: bool | None = None  # an independent solver reached the same answer
    check_problems: list[str] = []  # from verify.check_solution: [] means it checks out
    explanation: Explanation | None = None  # only for optimal solutions

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
) -> Result:
    formulation = formulate(problem, client, model_id)
    if formulation.model is None:
        return Result(problem=problem, formulation=formulation)
    model = formulation.model
    solution = solve(model)
    result = Result(
        problem=problem,
        formulation=formulation,
        solution=solution,
        highs_agrees=same_answer(model, solution, solve_with_highs(model)),
        check_problems=check_solution(model, solution),
    )
    if with_explanation and solution.status is Status.OPTIMAL:
        facts = solver_facts(model, solution)
        result.explanation = explain(problem, model, facts, client, model_id)
    return result


# ---- command line ----------------------------------------------------------------------


def render(result: Result) -> str:
    f = result.formulation
    lines = [f"Model: {f.model_id} ({f.usage.input_tokens} in / {f.usage.output_tokens} out, "
             f"{f.latency_s:.1f} s)", ""]  # fmt: skip
    if f.model is None:
        return "\n".join(lines + ["Claude's reply couldn't be used:", f.error])
    lines += format_model(f.model) + [""]
    s = result.solution
    lines.append(f"Status: {s.status}")
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
    parser.add_argument("--no-explanation", action="store_true", help="skip the second call")
    args = parser.parse_args(argv)
    problem = sys.stdin.read() if args.problem == "-" else args.problem
    try:
        client = anthropic.Anthropic(api_key=get_api_key())
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    print(render(run(problem, client, args.model, not args.no_explanation)))


if __name__ == "__main__":
    main()
