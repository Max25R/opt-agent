"""Do the explanations' "not limiting" claims hold in integer programs? An exploratory check
(docs/analysis/ip_slack_check.md) on saved outputs only: the explanations of the owner's paid
run of 2026-11-19 (runs/explain-dev/explanations.jsonl, each with its model and solver facts)
and their 88 labels (review/explain_dev/claims-*.csv, Claude's, an LLM's, not a person's).

  flags   in each explanation, every clause that says a constraint doesn't limit the answer
          or isn't binding (NEGATED, a fixed list of phrasings) and the constraints it names
          (named); for an integer program, the model is solved again without each named
          constraint (CBC, cross-checked by HiGHS: ground_truth.solve_checked), and the claim
          is flagged when the optimum changes. Writes docs/analysis/ip_slack_check.json and
          reads no label.
  score   the flags against the labels, once: precision and recall with 95% Wilson
          intervals, into the JSON and the doc's results section. It refuses if the flags it
          recomputes differ from the committed ones, or if the JSON has results already.

Only integer programs are checked: in an LP a constraint with slack never limits (the optimum
stays optimal without it). No API calls.  Run:  python scripts/ip_slack_check.py flags|score
"""

import argparse
import csv
import json
import re
from pathlib import Path

from opt_agent.ground_truth import CheckedSolve, same_value, solve_checked
from opt_agent.schema import LPModel
from opt_agent.solution import Status
from opt_agent.stats import wilson

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "runs" / "explain-dev" / "explanations.jsonl"
LABELS = ROOT / "review" / "explain_dev"
OUT = ROOT / "docs" / "analysis" / "ip_slack_check.json"
DOC = ROOT / "docs" / "analysis" / "ip_slack_check.md"
BEGIN, END = "<!-- results: added by the score step -->", "<!-- end of results -->"
LABEL = ("exploratory: a rule written from the 88 explanations' text before their labels were "
         "read; the labels are Claude's (an LLM's), not a person's")  # fmt: skip

# ---- the claims -----------------------------------------------------------------------------

# A clause that denies that a constraint limits the answer: "is not the bottleneck", "isn't
# what holds the plan back", "doesn't restrict the answer", "neither is the main constraint",
# "are not binding". "No constraint is fully used" isn't one: that's a fact about slack.
_NOT = r"(?:\bnot|n't)"
NEGATED = [re.compile(pattern, re.IGNORECASE) for pattern in (
    _NOT + r"\s+(?:the\s+|a\s+|an\s+)?(?:main\s+|real\s+|practical\s+|only\s+|current\s+)?"
           r"(?:bottleneck|limit\b|limiting\s+factor|limitation|constraint|binding)",
    _NOT + r"\s+what\s+(?:is\s+|are\s+)?(?:limits?|limiting|holds?|holding|restricts?|"
           r"restricting|caps|sets|stops)\b",
    _NOT + r"\s+(?:currently\s+|really\s+)?(?:limits?|limiting|restricts?|restricting|"
           r"constrains?|constraining|hold\w*|held)\b",
    r"\b(?:neither|none)\b(?:\s+[\w'-]+){0,3}?\s+(?:is\s+|are\s+)?(?:currently\s+)?"
    r"(?:what\s+(?:limits|holds|restricts)|limiting|restricting|holding|restricts?|limits?|"
    r"holds?|constrains?|the\s+(?:main\s+|real\s+)?(?:constraint|bottleneck|limit))\b",
    r"\bnon-?binding\b",
)]  # fmt: skip

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_CONTRAST = re.compile(r";|,?\s+\b(?:while|but|whereas)\b\s+", re.IGNORECASE)

STOP = {
    "a", "all", "an", "and", "any", "are", "at", "be", "by", "each", "every", "for", "from",
    "in", "is", "must", "no", "not", "of", "on", "or", "per", "than", "the", "to", "with",
}  # fmt: skip
# What a name calls the constraint ("the gondola share limit"), which the text may call
# otherwise ("the gondola share rule"): left off the ends of a name matched as a phrase.
KIND = {"cap", "constraint", "limit", "requirement", "rule"}
# Words that say what kind of constraint it is, not which one: "the budget limit" and "the
# flyer limit" share "limit", which can't tell them apart.
GENERIC = STOP | {
    "available", "availability", "cap", "capacity", "constraint", "daily", "day", "double",
    "exceed", "exceeds", "fewer", "five", "four", "half", "hour", "least", "less", "limit",
    "max", "maximum", "min", "minimum", "minute", "more", "most", "one", "percent", "ratio",
    "required", "requirement", "rule", "second", "share", "ten", "three", "time", "total",
    "triple", "twice", "two", "unit", "week", "weekly",
}  # fmt: skip


def clauses(text: str) -> list[str]:
    """Sentences, cut at semicolons and at "while", "but" or "whereas": a contrast usually
    turns from one constraint to another ("the budget isn't the limit; the trips are")."""
    plain = text.replace("**", "").replace("’", "'")
    return [c.strip() for s in _SENTENCE.split(plain) for c in _CONTRAST.split(s) if c.strip()]


def words(text: str) -> list[str]:
    """Lower case, no possessive, no number, a plural's s dropped: the same for a constraint's
    name and the text, so "John's hours" and "John has 10 hours" share john and hour."""
    found = []
    for word in re.split(r"[^a-z0-9']+", text.lower().replace("'s", "")):
        word = word.strip("'")
        if word and not any(ch.isdigit() for ch in word):
            plural = len(word) > 3 and word.endswith("s") and not word.endswith("ss")
            found.append(word[:-1] if plural else word)
    return found


def distinctive(name: str) -> set[str]:
    """The words of a constraint's name that pick it out, or all of them if none does (a
    constraint called "time" or "capacity")."""
    every = set(words(name)) - STOP
    return (every - GENERIC) or every


def phrase(name: str) -> str:
    """A name's words as a phrase, without what it calls the constraint at either end."""
    found = words(name)
    while found and found[-1] in KIND:
        found.pop()
    while found and found[0] in KIND:
        found.pop(0)
    return " ".join(found or words(name))


def named(span: str, names: list[str]) -> list[str]:
    """The constraints a stretch of text names: by the name as a phrase, or by every
    distinctive word of it, unless those words are only part of what another named constraint
    matched (so "the requirement that cones be at least twice the tubs" names
    cones_at_least_2x_tubs, not min_tubs)."""
    present = words(span)
    text, have = f" {' '.join(present)} ", set(present)
    phrased = {n for n in names if phrase(n) and f" {phrase(n)} " in text}
    matched = {n: distinctive(n) for n in names if distinctive(n) and distinctive(n) <= have}
    part_of_another = {n for n, got in matched.items()
                       if any(got < other for m, other in matched.items() if m != n)}  # fmt: skip
    keep = phrased | (set(matched) - part_of_another)
    return [n for n in names if n in keep]  # in the model's order


def claims_in(text: str, names: list[str]) -> dict[str, list[str]]:
    """Each constraint a clause says doesn't limit the answer, with the phrases that said so:
    the constraints named before the phrase ("the budget isn't the limit"), or, if none is,
    after it ("the other rules are not holding it back: the manual-use cap has 2 spare")."""
    found: dict[str, list[str]] = {}
    for clause in clauses(text):
        hits = sorted((m for p in NEGATED for m in p.finditer(clause)), key=lambda m: m.start())
        for m in hits:
            subjects = named(clause[: m.start()], names) or named(clause[m.end() :], names)
            for name in subjects:
                found.setdefault(name, []).append(m.group())
    return found


def kind(phrases: list[str]) -> str:
    """The claim's wording: "binding" if every phrase only says the constraint isn't binding
    (the owner's word, and a solver's: about slack), else "limit" (what holds the answer
    back)."""
    return "binding" if all("binding" in p.lower() for p in phrases) else "limit"


# ---- the re-solve ---------------------------------------------------------------------------


def without(model: LPModel, name: str) -> LPModel:
    return model.model_copy(update={"constraints": [c for c in model.constraints
                                                    if c.name != name]})  # fmt: skip


def trusted(solve: CheckedSolve) -> bool:
    return solve.highs_agrees and not solve.check_problems


def changes_the_optimum(model: LPModel, name: str, original: CheckedSolve) -> dict:
    """Solve the model without `name`: "flagged" when the optimum changes (a better objective,
    or none at all: unbounded), "holds" when it doesn't, "undetermined" when CBC and HiGHS
    disagree or the arithmetic checks fail on either solve."""
    dropped = solve_checked(without(model, name))
    found = {"dropped_status": dropped.status.value, "dropped_objective": dropped.objective}
    if not (trusted(original) and trusted(dropped)):
        return found | {"verdict": "undetermined"}
    same = (dropped.status is Status.OPTIMAL and original.objective is not None
            and same_value(dropped.objective, original.objective))  # fmt: skip
    return found | {"verdict": "holds" if same else "flagged"}


def explained() -> list[dict]:
    return [r for r in map(json.loads, ROWS.read_text().splitlines()) if r["explanation"]]


def check_row(row: dict) -> tuple[dict, list[dict]]:
    """One explanation: its summary line and its claims, each re-solved if it's an IP's."""
    model = LPModel.model_validate(row["model"])
    found = claims_in(row["explanation"], [c.name for c in model.constraints])
    original = solve_checked(model) if model.is_mip and found else None
    if original is not None and not (original.status is Status.OPTIMAL and same_value(
            original.objective, row["facts"]["objective"])):  # fmt: skip
        raise SystemExit(f"{row['problem']}: the model no longer solves to the run's optimum")
    claims = []
    for name, phrases in found.items():
        claim = {"problem": row["problem"], "constraint": name, "kind": kind(phrases),
                 "phrases": phrases, "slack": row["facts"]["slack"].get(name),
                 "objective": row["facts"]["objective"]}  # fmt: skip
        if original is None:
            claim["verdict"] = "not checked (an LP)"
        else:
            claim |= changes_the_optimum(model, name, original)
        claims.append(claim)
    summary = {"problem": row["problem"], "integer_program": model.is_mip,
               "claims": len(claims), "flagged": any(c["verdict"] == "flagged" for c in claims),
               "undetermined": any(c["verdict"] == "undetermined" for c in claims)}  # fmt: skip
    return summary, claims


def compute_flags(rows: list[dict] | None = None) -> dict:
    """Every claim of every explanation and its verdict; reads no label."""
    explanations, claims = [], []
    for row in explained() if rows is None else rows:
        summary, found = check_row(row)
        explanations.append(summary)
        claims += found
    return {"label": LABEL, "explanations": len(explanations),
            "integer_programs": sum(e["integer_program"] for e in explanations),
            "per_explanation": explanations, "claims": claims}  # fmt: skip


# ---- the score ------------------------------------------------------------------------------


def read_labels() -> dict[str, bool]:
    """Problem -> does the explanation make a false claim (the labelers' rule: dropping or
    loosening a constraint called "not limiting" changes the optimum, among others)."""
    labels: dict[str, bool] = {}
    for path in sorted(LABELS.glob("claims-*.csv")):
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["false_claim"] not in ("yes", "no"):
                    raise SystemExit(f"{path.name}, {row['problem']}: false_claim is yes or no")
                labels[row["problem"]] = row["false_claim"] == "yes"
    return labels


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "value": k / n if n else None, "wilson95": list(wilson(k, n))}


def compute_results(flags: dict, labels: dict[str, bool]) -> dict:
    """Explanation by explanation: flagged (any claim flagged) against labeled false."""
    rows = {e["problem"]: e for e in flags["per_explanation"]}
    if set(rows) != set(labels):
        raise SystemExit("the labels and the explanations aren't the same problems")
    flagged = {p for p, e in rows.items() if e["flagged"]}
    false = {p for p, is_false in labels.items() if is_false}
    integer = {p for p, e in rows.items() if e["integer_program"]}
    by_kind = {k: [c for c in flags["claims"] if c["kind"] == k] for k in ("limit", "binding")}
    return {
        "explanations": len(rows), "flagged": len(flagged), "labeled_false": len(false),
        "precision": rate(len(flagged & false), len(flagged)),
        "recall": rate(len(flagged & false), len(false)),
        "recall_integer_programs": rate(len(flagged & false & integer), len(false & integer)),
        "flagged_but_labeled_fine": sorted(flagged - false),
        "labeled_false_not_flagged": sorted(false - flagged),
        "claims": {k: {"found": len(cs), "in_integer_programs": sum(c["verdict"] !=
                                                                    "not checked (an LP)"
                                                                    for c in cs),
                       "flagged": sum(c["verdict"] == "flagged" for c in cs),
                       "undetermined": sum(c["verdict"] == "undetermined" for c in cs)}
                   for k, cs in by_kind.items()},
    }  # fmt: skip


def pct(r: dict) -> str:
    if r["value"] is None:
        return f"{r['k']} of {r['n']}"
    low, high = r["wilson95"]
    return f"{r['k']} of {r['n']}, {100 * r['value']:.1f}% ({100 * low:.1f} to {100 * high:.1f})"


def render(flags: dict, results: dict) -> str:
    c = results["claims"]
    return "\n".join([
        "## Results", "",
        f"{results['explanations']} explanations ({flags['integer_programs']} of them integer "
        "programs). Labels by Claude (an LLM, not a person). Exploratory.", "",
        "| claims found | limit wording | binding wording |", "|---|---:|---:|",
        f"| in all explanations | {c['limit']['found']} | {c['binding']['found']} |",
        f"| in integer programs (re-solved) | {c['limit']['in_integer_programs']} | "
        f"{c['binding']['in_integer_programs']} |",
        f"| flagged: the optimum changes without the constraint | {c['limit']['flagged']} | "
        f"{c['binding']['flagged']} |",
        f"| undetermined (the solvers disagree or a check fails) | "
        f"{c['limit']['undetermined']} | {c['binding']['undetermined']} |", "",
        f"Explanations flagged: {results['flagged']}; labeled with a false claim: "
        f"{results['labeled_false']}.", "",
        f"- **Precision** (labeled false, of those flagged): {pct(results['precision'])}.",
        f"- **Recall** (flagged, of those labeled false): {pct(results['recall'])}.",
        f"- **Recall in integer programs:** {pct(results['recall_integer_programs'])}.",
        f"- Flagged but labeled fine: {', '.join(results['flagged_but_labeled_fine']) or 'none'}.",
        f"- Labeled false but not flagged: "
        f"{', '.join(results['labeled_false_not_flagged']) or 'none'}.",
    ])  # fmt: skip


def write_report(flags: dict, results: dict) -> None:
    doc = DOC.read_text()
    start, end = doc.index(BEGIN) + len(BEGIN), doc.index(END)
    DOC.write_text(doc[:start] + "\n\n" + render(flags, results) + "\n\n" + doc[end:])


def write(data: dict) -> None:
    OUT.write_text(json.dumps(data, indent=1) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The IP slack-claim check (exploratory).")
    parser.add_argument("step", choices=["flags", "score"])
    args = parser.parse_args(argv)
    flags = compute_flags()
    if args.step == "flags":
        write(flags)
        flagged = sum(e["flagged"] for e in flags["per_explanation"])
        print(f"{len(flags['claims'])} claims in {flags['explanations']} explanations; "
              f"{flagged} explanations flagged")  # fmt: skip
        return
    committed = json.loads(OUT.read_text())
    if "results" in committed:
        raise SystemExit(f"{OUT.relative_to(ROOT)} has results already: it's scored once")
    if {k: committed[k] for k in flags} != flags:
        raise SystemExit("the recomputed flags differ from the committed ones")
    results = compute_results(flags, read_labels())
    write(flags | {"results": results})
    write_report(flags, results)
    print(render(flags, results))


if __name__ == "__main__":
    main()
