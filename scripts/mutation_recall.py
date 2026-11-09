"""Mutation recall of the report-only checks, at $0 (docs/FOLLOWUP_DEV_LOG.md).

Takes the follow-up dev run's models that were scored right, breaks each in small known ways,
and asks whether the checklist (its cached reply for that problem) or the low-confidence
check (its cached direct estimate) notices. No API calls: every checklist and estimate comes
from the run's log, and every solve is local.

Mutation types (up to PER_TYPE of each per model, chosen with SEED):
- drop: delete one constraint;
- flip: turn one inequality around (<= and >=);
- scale: multiply one constraint coefficient by 2 or 0.5;
- rhs: move one non-zero right-hand side by +20% or -20%;
- continuous: make one integer variable continuous;
- invent: add one constraint x_i >= x_j between two variables.

A mutant counts only if it changes the optimum (status, or the objective beyond 1e-6):
one that doesn't is undetectable by design, and is reported as discarded, like a mutant the
schema rejects (e.g. dropping a variable's only row) or one CBC can't solve.

**Detected** means a check says something about the mutant it didn't say about the original:
a checklist flag the unmutated model doesn't have, or low confidence where the original
had none. So the original's false positives don't count as catches.

Run:  python scripts/mutation_recall.py   # prints the table; writes the JSON next to the run
"""

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from opt_agent import followup
from opt_agent.agent import compare_estimate
from opt_agent.checklist import parse_reply as parse_checklist
from opt_agent.checklist import review
from opt_agent.formulate import parse_reply
from opt_agent.ground_truth import same_value
from opt_agent.schema import Constraint, LPModel, Term
from opt_agent.solver import Status, solve
from opt_agent.stats import wilson

SEED = 20261109
PER_TYPE = 3
TYPES = ("drop", "flip", "scale", "rhs", "continuous", "invent")
ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "dev-checklist"


def load_run(run: Path) -> dict[str, dict]:
    """Problem id -> its final model, cached checklist, estimate and answer, for the pairs
    scored right."""
    problems = {p.id: p for p in followup.load("complexlp-dev")}
    found: dict[str, dict] = defaultdict(dict)
    for line in (run / "attempts.jsonl").read_text().splitlines():
        e = json.loads(line)
        pid = e.get("problem_id")
        if e["kind"] == "attempt":
            model, _ = parse_reply(e["reply"], e["stop_reason"])
            if model is not None:
                found[pid]["model"] = model  # the last usable attempt is the answer's model
        elif e["kind"] == "checklist":
            found[pid]["checklist"] = parse_checklist(e["reply"], e["stop_reason"])[0]
    for line in (run / "results.jsonl").read_text().splitlines():
        item = json.loads(line)
        if item["kind"] != "item":
            continue
        pid = item["problem_id"]
        right = followup.is_correct(problems[pid], item["status"], item["objective"])
        if right and found[pid].get("model") and found[pid].get("checklist"):
            found[pid]["estimate"] = (item["estimate_status"], item["estimate_objective"])
        else:
            found.pop(pid, None)
    return {pid: x for pid, x in found.items() if "estimate" in x}


def mutants(model: LPModel, rng: random.Random) -> list[tuple[str, str, dict]]:
    """(type, description, the mutated model as a dict) for every type, up to PER_TYPE each."""
    data = model.model_dump(mode="json")
    found = []

    def pick(kind: str, candidates: list, make) -> None:
        for choice in rng.sample(candidates, min(PER_TYPE, len(candidates))):
            found.append((kind, *make(choice)))

    rows = list(range(len(data["constraints"])))
    inequalities = [i for i in rows if data["constraints"][i]["sense"] != "=="]
    terms = [(i, j) for i in rows for j in range(len(data["constraints"][i]["terms"]))]
    nonzero_rhs = [i for i in rows if data["constraints"][i]["rhs"] != 0]
    integers = [k for k, v in enumerate(data["variables"]) if v["integer"]]
    names = [v["name"] for v in data["variables"]]
    pairs = [(a, b) for a in names for b in names if a != b]

    def edited(change) -> dict:
        copy = json.loads(json.dumps(data))
        change(copy)
        return copy

    def drop(i):
        return f"dropped {data['constraints'][i]['name']!r}", edited(
            lambda d: d["constraints"].pop(i)
        )

    def flip(i):
        def change(d):
            c = d["constraints"][i]
            c["sense"] = "<=" if c["sense"] == ">=" else ">="

        return f"flipped {data['constraints'][i]['name']!r}", edited(change)

    def scale(ij):
        i, j = ij
        factor = rng.choice([2.0, 0.5])

        def change(d):
            d["constraints"][i]["terms"][j]["coef"] *= factor

        term = data["constraints"][i]["terms"][j]["var"]
        return f"x{factor:g} on {term!r} in {data['constraints'][i]['name']!r}", edited(change)

    def rhs(i):
        factor = rng.choice([1.2, 0.8])

        def change(d):
            d["constraints"][i]["rhs"] *= factor

        return f"rhs x{factor:g} in {data['constraints'][i]['name']!r}", edited(change)

    def continuous(k):
        def change(d):
            d["variables"][k]["integer"] = False

        return f"{names[k]!r} made continuous", edited(change)

    def invent(ab):
        a, b = ab
        row = Constraint(name=f"invented {a} >= {b}", sense=">=", rhs=0,
                         terms=[Term(var=a, coef=1), Term(var=b, coef=-1)])  # fmt: skip
        return f"added {a!r} >= {b!r}", edited(
            lambda d: d["constraints"].append(row.model_dump(mode="json"))
        )

    pick("drop", rows, drop)
    pick("flip", inequalities, flip)
    pick("scale", terms, scale)
    pick("rhs", nonzero_rhs, rhs)
    pick("continuous", integers, continuous)
    pick("invent", pairs, invent)
    return found


def answer(model: LPModel) -> tuple[Status, float | None, dict[str, float]]:
    s = solve(model)
    return s.status, s.objective, s.values


def signature(model, checklist, status, values) -> set[tuple]:
    found = review(model, checklist, values if status is Status.OPTIMAL else None)
    return {(f.kind, f.quote, f.constraint, f.detail) for f in found.flags}


def low(model, estimate, status, objective) -> bool:
    flag, _ = compare_estimate(*estimate, status, objective, model)
    return flag is True


def measure(run: Path = RUN) -> dict:
    rng = random.Random(SEED)
    counts = Counter()
    hits: dict[str, dict[str, list[bool]]] = {t: defaultdict(list) for t in TYPES}
    for _pid, x in sorted(load_run(run).items(), key=lambda kv: int(kv[0])):
        model, checklist, estimate = x["model"], x["checklist"], x["estimate"]
        status, objective, values = answer(model)
        before_flags = signature(model, checklist, status, values)
        before_low = low(model, estimate, status, objective)
        for kind, _what, data in mutants(model, rng):
            counts[(kind, "generated")] += 1
            try:
                mutant = LPModel.model_validate(data)
            except ValueError:
                counts[(kind, "schema rejects it")] += 1
                continue
            m_status, m_objective, m_values = answer(mutant)
            if m_status in (Status.ERROR, Status.TIMEOUT):
                counts[(kind, "solver failed")] += 1
                continue
            unchanged = m_status == status and (
                status is not Status.OPTIMAL or same_value(m_objective, objective)
            )
            if unchanged:
                counts[(kind, "optimum unchanged")] += 1
                continue
            counts[(kind, "counted")] += 1
            flagged = bool(signature(mutant, checklist, m_status, m_values) - before_flags)
            lowered = not before_low and low(mutant, estimate, m_status, m_objective)
            hits[kind]["checklist"].append(flagged)
            hits[kind]["low confidence"].append(lowered)
            hits[kind]["either"].append(flagged or lowered)
    table = {}
    for kind in (*TYPES, "all"):
        rows = hits[kind] if kind != "all" else {
            check: [h for t in TYPES for h in hits[t][check]]
            for check in ("checklist", "low confidence", "either")}  # fmt: skip
        table[kind] = {check: _rate(rows.get(check, [])) for check in
                       ("checklist", "low confidence", "either")}  # fmt: skip
    return {
        "seed": SEED,
        "per_type": PER_TYPE,
        "models": len(load_run(run)),
        "counts": {f"{k}: {what}": n for (k, what), n in sorted(counts.items())},
        "recall": table,
    }


def _rate(found: list[bool]) -> dict:
    low_, high = wilson(sum(found), len(found))
    return {"caught": sum(found), "n": len(found), "wilson95": [low_, high]}


def render(result: dict) -> str:
    lines = ["| mutation | n | checklist | low confidence | either |", "|---|---|---|---|---|"]
    for kind, row in result["recall"].items():
        n = row["either"]["n"]
        cells = [_cell(row[c]) for c in ("checklist", "low confidence", "either")]
        lines.append(f"| {kind} | {n} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _cell(r: dict) -> str:
    if not r["n"]:
        return "-"
    low_, high = r["wilson95"]
    return f"{r['caught']}/{r['n']} ({r['caught'] / r['n']:.0%}; {low_:.0%}-{high:.0%})"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Mutation recall of the report-only checks.")
    parser.add_argument("--run", type=Path, default=RUN)
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "dev-checklist-rev1"
                        / "mutation_recall.json")  # fmt: skip
    args = parser.parse_args(argv)
    result = measure(args.run)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(render(result))
    print()
    for key, n in result["counts"].items():
        print(f"  {key}: {n}")


if __name__ == "__main__":
    main()
