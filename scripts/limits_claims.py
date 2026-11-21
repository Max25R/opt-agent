"""ADR-0009 measured on dev (exploratory): once the explainer is told what limits an integer
program, do its "not limiting" claims agree with the solver's facts more often?

Two runs explain the same verified answers on NL4Opt's dev split, one sample each:
- **before:** runs/explain-dev (2026-11-19), whose explainer saw the values, the objective,
  the binding constraints, the slack and shadow prices;
- **after:** runs/explain-dev-limits (the owner's paid run of 2026-11-20,
  scripts/paid_explain_limits.py), whose explainer also saw, for each constraint of an integer
  program, whether the optimum is better without it or with its limit one unit further out
  (src/opt_agent/limits.py, ADR-0009).
The formulations replayed from the same cache, so the runs explain the same models (checked);
an LP's request didn't change, so its explanation is the same text in both (checked), and the
comparison is over the integer programs.

**Claims** are found by scripts/ip_slack_check.py's rule, unchanged: each clause that says a
constraint doesn't limit the answer, or isn't binding, and the constraints it names. Claude
wrote that rule on the first run's text, before ADR-0009, so it can miss phrasings only the
new text uses. **Verdicts** come from the solver's facts in the after run's rows (the same
models): "X doesn't limit the answer" is false when the optimum is better without X
(dropped_improves), unknown when the solvers couldn't tell; "X isn't binding" is false when X
is binding. No labels, no API call; this script was written before its first run, and the
new explanations weren't read before the counts were.

Run:  python scripts/limits_claims.py           # the JSON and the doc's results section
      python scripts/limits_claims.py --verify  # also re-solve every integer program's limits
"""

import argparse
import importlib.util
import json
from pathlib import Path

from opt_agent.limits import constraint_limits
from opt_agent.schema import LPModel
from opt_agent.solver import solve

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / "runs" / "explain-dev" / "explanations.jsonl"
AFTER = ROOT / "runs" / "explain-dev-limits" / "explanations.jsonl"
OUT = ROOT / "docs" / "analysis" / "limits_claims.json"
DOC = ROOT / "docs" / "analysis" / "limits_claims.md"
BEGIN, END = "<!-- results: written by scripts/limits_claims.py -->", "<!-- end of results -->"
RUNS = ("before", "after")
LABEL = ("exploratory, dev split, one sample per problem: claims found by "
         "scripts/ip_slack_check.py's rule (unchanged; written by Claude, an LLM, on the first "
         "run's text), judged against the solver's facts (limits.py); no labels")  # fmt: skip

_spec = importlib.util.spec_from_file_location("ip_slack_check",
                                               ROOT / "scripts" / "ip_slack_check.py")  # fmt: skip
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)  # type: ignore[union-attr]


def explained(path: Path) -> dict[str, dict]:
    """Each problem's row, for the answers that were explained."""
    rows = map(json.loads, path.read_text().splitlines())
    return {r["problem"]: r for r in rows if r["explanation"] is not None}


def judged(text: str, model: LPModel, facts: dict) -> list[dict]:
    """Each claim in `text` and what the solver's facts say of it."""
    claims = []
    for name, phrases in check.claims_in(text, [c.name for c in model.constraints]).items():
        wording = check.kind(phrases)
        if wording == "binding":
            verdict = "false" if name in facts["binding"] else "true"
        else:
            improves = facts["limits"][name]["dropped_improves"]
            verdict = "unknown" if improves is None else "false" if improves else "true"
        claims.append({"constraint": name, "wording": wording, "verdict": verdict,
                       "slack": facts["slack"][name]})  # fmt: skip
    return claims


def per_problem(before: dict[str, dict], after: dict[str, dict]) -> tuple[list[dict], int]:
    """The integer programs' claims in both runs, and how many LP explanations are unchanged."""
    if before.keys() != after.keys():
        raise SystemExit("the two runs explained different problems")
    rows, unchanged_lps = [], 0
    for pid, a in after.items():
        b = before[pid]
        if b["model"] != a["model"]:
            raise SystemExit(f"{pid}: the two runs explain different models")
        model = LPModel.model_validate(a["model"])
        if not model.is_mip:
            if b["explanation"] != a["explanation"]:
                raise SystemExit(f"{pid}: an LP's explanation changed, but its request didn't")
            unchanged_lps += 1
            continue
        facts = a["facts"]
        rows.append({
            "problem": pid,
            # what a slack-based "not limiting" claim would get wrong here
            "slack_yet_limits": [n for n, lim in facts["limits"].items()
                                 if lim["dropped_improves"] and n not in facts["binding"]],
            "before": judged(b["explanation"], model, facts),
            "after": judged(a["explanation"], model, facts),
            "unsupported_numbers": {"before": len(b["unsupported_numbers"]),
                                    "after": len(a["unsupported_numbers"])},
        })  # fmt: skip
    return rows, unchanged_lps


def summary(rows: list[dict], run: str) -> dict:
    claims = [c for r in rows for c in r[run]]

    def count(wording: str) -> dict:
        mine = [c for c in claims if c["wording"] == wording]
        return {"found": len(mine), **{v: sum(c["verdict"] == v for c in mine)
                                       for v in ("false", "true", "unknown")}}  # fmt: skip

    return {
        "explanations_with_a_claim": sum(bool(r[run]) for r in rows),
        "explanations_with_a_false_claim": sum(any(c["verdict"] == "false" for c in r[run])
                                               for r in rows),
        "claims": {"limit": count("limit"), "binding": count("binding")},
        "unsupported_numbers": sum(r["unsupported_numbers"][run] for r in rows),
    }  # fmt: skip


def compute() -> dict:
    rows, unchanged_lps = per_problem(explained(BEFORE), explained(AFTER))
    false = [{run: any(c["verdict"] == "false" for c in r[run]) for run in RUNS} for r in rows]
    return {
        "label": LABEL,
        "integer_programs": len(rows),
        "lp_explanations_unchanged": unchanged_lps,
        "with_a_constraint_that_has_slack_yet_limits": sum(bool(r["slack_yet_limits"])
                                                           for r in rows),
        "runs": {run: summary(rows, run) for run in RUNS},
        "paired": {  # integer programs, by whether each run's explanation made a false claim
            "false_before_fine_after": sum(f["before"] and not f["after"] for f in false),
            "fine_before_false_after": sum(f["after"] and not f["before"] for f in false),
            "false_in_both": sum(f["before"] and f["after"] for f in false),
            "fine_in_both": sum(not f["before"] and not f["after"] for f in false),
        },
        "per_problem": rows,
    }  # fmt: skip


def verify() -> int:
    """Re-solve every integer program's limits and require the after run's facts."""
    checked = 0
    for pid, row in explained(AFTER).items():
        model = LPModel.model_validate(row["model"])
        if not model.is_mip:
            continue
        again = {n: lim.model_dump() for n, lim in constraint_limits(model, solve(model)).items()}
        if again != row["facts"]["limits"]:
            raise SystemExit(f"{pid}: limits.py now gives other limits than the run recorded")
        checked += 1
    return checked


# ---- the report -----------------------------------------------------------------------------


def render(data: dict) -> str:
    b, a, p = data["runs"]["before"], data["runs"]["after"], data["paired"]
    n = data["integer_programs"]

    def row(label: str, key: tuple[str, ...]) -> str:
        values = []
        for run in (b, a):
            value = run
            for k in key:
                value = value[k]
            values.append(str(value))
        return f"| {label} | {values[0]} | {values[1]} |"

    return "\n".join([
        "## Results", "",
        f"Dev split, exploratory: {n} integer programs, one explanation each per run; the "
        f"{data['lp_explanations_unchanged']} LP explanations are the same text in both runs. "
        f"{data['with_a_constraint_that_has_slack_yet_limits']} of the {n} have a constraint "
        "with slack that still limits the answer (the trap ADR-0009 is about).", "",
        "| over the integer programs | before | after |", "|---|---:|---:|",
        row("explanations with a claim the rule finds", ("explanations_with_a_claim",)),
        row("**explanations with a false claim**", ("explanations_with_a_false_claim",)),
        row('"not limiting" claims found', ("claims", "limit", "found")),
        row('... false (better without the constraint)', ("claims", "limit", "false")),
        row("... true", ("claims", "limit", "true")),
        row("... unknown (the solvers couldn't tell)", ("claims", "limit", "unknown")),
        row('"not binding" claims found', ("claims", "binding", "found")),
        row("... false (the constraint binds)", ("claims", "binding", "false")),
        row("numbers the number check flags", ("unsupported_numbers",)),
        "",
        f"Paired, by problem: {p['false_before_fine_after']} explanations made a false claim "
        f"before and none after, {p['fine_before_false_after']} the reverse, "
        f"{p['false_in_both']} made one in both runs, and {p['fine_in_both']} in neither.",
    ])  # fmt: skip


def write_report(data: dict) -> None:
    doc = DOC.read_text()
    start, end = doc.index(BEGIN) + len(BEGIN), doc.index(END)
    DOC.write_text(doc[:start] + "\n\n" + render(data) + "\n\n" + doc[end:])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ADR-0009 on dev (exploratory).")
    parser.add_argument("--verify", action="store_true",
                        help="also re-solve every integer program's limits")  # fmt: skip
    args = parser.parse_args(argv)
    if args.verify:
        print(f"{verify()} integer programs: the run's limits are what limits.py gives now")
    data = compute()
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    write_report(data)
    print(render(data))


if __name__ == "__main__":
    main()
