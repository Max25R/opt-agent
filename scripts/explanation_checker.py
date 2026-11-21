"""The explanation checker's evaluation on dev (docs/analysis/explanation_checker.md), from the
owner's paid run (runs/explain-dev/explanations.jsonl, scripts/paid_dev_and_demo.py).

  sheet   the labeling sheets: each explanation with its problem, its model and its solver
          facts, and each number the checker reads, numbered, but NOT the checker's flags
          (review/explain_dev/batch-<k>.md), with blank label files beside them
          (labels-<k>.csv: one row per number; claims-<k>.csv: one row per explanation).
  score   the filled-in labels against the checker's own verdict, recomputed number by number
          with explain.py's rule and held equal to the run's: docs/analysis/explanation_checker.json
          and the doc's results section.
  prune   keep in runs/explain-dev/cache only the replies the run replays (it was seeded with
          a copy of runs/dev-1's whole cache).

`sheet --after`: the same sheets for ADR-0009's regenerated explanations
(runs/explain-dev-limits, into review/explain_dev_limits/), so the same checker can label
them: the same fields (the facts line leaves out the new limits, as the first sheets had
none), the same batches, and still none of the checker's flags.
`score --after`: those labels against the first run's (docs/analysis/limits_checker.json and
the checker results in docs/analysis/limits_claims.md): explanations with a false claim
before and after, paired by problem, and the owner's consistency rule on the 15 LP entries
the two sheets share word for word (fewer than 13 matching: inconclusive). It also scores the
rule's flags (docs/analysis/limits_claims.json, scripts/limits_claims.py) against each
labeling, and writes the numbers of review/explain_dev_limits/RESULTS.md.

No API calls. Run:  python scripts/explanation_checker.py sheet [--after]|score|prune
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from opt_agent import agent, explain
from opt_agent.api import Cache, ReplayOnlyClient
from opt_agent.explain import Facts
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.runs import Run
from opt_agent.schema import LPModel
from opt_agent.stats import wilson

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "explain-dev"
ROWS = RUN / "explanations.jsonl"
SHEETS = ROOT / "review" / "explain_dev"
DOC = ROOT / "docs" / "analysis" / "explanation_checker.md"
OUT = ROOT / "docs" / "analysis" / "explanation_checker.json"
BEGIN, END = "<!-- results: added after the labels -->", "<!-- end of results -->"
AFTER_ROWS = ROOT / "runs" / "explain-dev-limits" / "explanations.jsonl"  # ADR-0009's run
AFTER_SHEETS = ROOT / "review" / "explain_dev_limits"
AFTER_OUT = ROOT / "docs" / "analysis" / "limits_checker.json"
AFTER_DOC = ROOT / "docs" / "analysis" / "limits_claims.md"
AFTER_BEGIN = "<!-- checker results: written by scripts/explanation_checker.py score --after -->"
AFTER_END = "<!-- end of checker results -->"
RULE = ROOT / "docs" / "analysis" / "limits_claims.json"  # the rule's flags, both runs
NOTE = AFTER_SHEETS / "RESULTS.md"
NOTE_BEGIN = "<!-- results: written by scripts/explanation_checker.py score --after -->"
NOTE_END = "<!-- end of results -->"
LP_RULE = 13  # of the 15 LP entries both sheets share: the owner's rule, fixed before labeling
BATCHES = 4
LABELS = {"correct", "wrong"}


def explained(rows: Path = ROWS) -> list[dict]:
    """The run's explained answers, in its order."""
    return [r for r in map(json.loads, rows.read_text().splitlines()) if r["explanation"]]


def texts() -> dict[str, str]:
    return {r.id: r.document for r in load_records(GROUND_TRUTH_DIR / "dev.json")}


def tokens(text: str) -> list[tuple[str, str]]:
    """Each number the checker reads, with a few words around it."""
    found = []
    for m in explain._NUMBER.finditer(text):
        before = text[max(0, m.start() - 45) : m.start()].split(" ", 1)[-1]
        after = text[m.end() : m.end() + 45].rsplit(" ", 1)[0]
        found.append((m.group(), f"...{before}[{m.group()}]{after}...".replace("\n", " ")))
    return found


def flagged(row: dict, problem: str) -> list[bool]:
    """The checker's verdict on each number, in order (explain.unsupported_numbers' rule)."""
    allowed = explain.allowed_numbers(problem, LPModel.model_validate(row["model"]),
                                      Facts.model_validate(row["facts"]))  # fmt: skip
    return [not any(explain._rounds_to(exact, value, places)
                    for value, places in explain._readings(token) for exact in allowed)
            for token, _ in tokens(row["explanation"])]  # fmt: skip


# ---- sheet --------------------------------------------------------------------------------


def write_sheets(source: Path = ROWS, sheets: Path = SHEETS) -> None:
    rows, problems = explained(source), texts()
    sheets.mkdir(parents=True, exist_ok=True)
    for k in range(BATCHES):
        batch = rows[k::BATCHES]
        lines = [f"# Explanation labels, batch {k + 1} of {BATCHES}", "",
                 "Label every numbered number `correct` or `wrong` in "
                 f"`labels-{k + 1}.csv`, and every explanation's false claim `yes` or `no` in "
                 f"`claims-{k + 1}.csv`, by the rules of docs/analysis/explanation_checker.md. "
                 "This sheet doesn't show the checker's flags, on purpose.", ""]  # fmt: skip
        label_rows, claim_rows = [], []
        for r in batch:
            model, facts = LPModel.model_validate(r["model"]), r["facts"]
            lines += [f"## {r['problem']}", "", "**Problem.** " + problems[r["problem"]], "",
                      "**Model.**", "```", *agent.format_model(model), "```", "",
                      f"**Facts.** objective {facts['objective']:g}; values "
                      + ", ".join(f"{k} = {v:g}" for k, v in facts["values"].items())
                      + "; slack " + ", ".join(f"{k}: {v:g}" for k, v in facts["slack"].items())
                      + f"; binding: {', '.join(facts['binding']) or 'none'}; shadow prices "
                      + (", ".join(f"{k}: {v:g}" for k, v in facts["shadow_prices"].items())
                         if facts["shadow_prices"] else "none (a MIP)"), "",
                      "**Explanation.**", "", r["explanation"], "", "**Numbers.**", ""]  # fmt: skip
            for i, (token, context) in enumerate(tokens(r["explanation"]), start=1):
                lines.append(f"{i}. `{token}` {context}")
                label_rows.append({"problem": r["problem"], "index": i, "token": token,
                                   "label": "", "note": ""})  # fmt: skip
            claim_rows.append({"problem": r["problem"], "false_claim": "", "note": ""})
            lines.append("")
        (sheets / f"batch-{k + 1}.md").write_text("\n".join(lines))
        for name, fields, data in ((f"labels-{k + 1}.csv", ["problem", "index", "token", "label",
                                                            "note"], label_rows),
                                   (f"claims-{k + 1}.csv", ["problem", "false_claim", "note"],
                                    claim_rows)):  # fmt: skip
            path = sheets / name
            if path.exists():
                raise SystemExit(f"{path.relative_to(ROOT)} exists: labels are never overwritten")
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(data)
    shown = sheets.relative_to(ROOT) if sheets.is_relative_to(ROOT) else sheets
    print(f"wrote {BATCHES} sheets for {len(rows)} explanations to {shown}")


# ---- score --------------------------------------------------------------------------------


def read(pattern: str) -> list[dict]:
    rows = []
    for path in sorted(SHEETS.glob(pattern)):
        with path.open(newline="") as f:
            rows += list(csv.DictReader(f))
    return rows


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "value": k / n if n else None, "wilson95": list(wilson(k, n))}


def compute() -> dict:
    """The labels against the checker's verdict; writes nothing."""
    rows, problems = explained(), texts()
    labels = {(r["problem"], int(r["index"])): r for r in read("labels-*.csv")}
    claims = {r["problem"]: r for r in read("claims-*.csv")}
    numbers, per_explanation = [], []
    for r in rows:
        verdicts = flagged(r, problems[r["problem"]])
        found = tokens(r["explanation"])
        mine = Counter(t for (t, _), f in zip(found, verdicts, strict=True) if f)
        if mine != Counter(r["unsupported_numbers"]):
            raise SystemExit(f"{r['problem']}: the recomputed flags differ from the run's")
        wrong = []
        for i, ((token, _), flag) in enumerate(zip(found, verdicts, strict=True), start=1):
            label = labels[(r["problem"], i)]
            if label["token"] != token or label["label"] not in LABELS:
                raise SystemExit(f"{r['problem']} number {i}: label it correct or wrong")
            numbers.append({"problem": r["problem"], "index": i, "token": token,
                            "flagged": flag, "wrong": label["label"] == "wrong",
                            "note": label["note"]})  # fmt: skip
            wrong.append(label["label"] == "wrong")
        claim = claims[r["problem"]]["false_claim"]
        if claim not in ("yes", "no"):
            raise SystemExit(f"{r['problem']}: false_claim is yes or no")
        flag = any(verdicts) or r["explanation_problem"] is not None
        caught = any(f and w for f, w in zip(verdicts, wrong, strict=True))
        note = claims[r["problem"]]["note"]
        per_explanation.append({"problem": r["problem"], "flagged": flag,
                                "wrong_number": any(wrong), "false_claim": claim == "yes",
                                "caught": caught, "note": note})  # fmt: skip
    hit = sum(n["flagged"] and n["wrong"] for n in numbers)
    flagged_n, wrong_n = sum(n["flagged"] for n in numbers), sum(n["wrong"] for n in numbers)
    errors = [e for e in per_explanation if e["wrong_number"] or e["false_claim"]]
    result = {
        "label": "exploratory: labels by Claude (an LLM, not a person) from sheets without the "
                 "checker's flags, by the protocol committed before the explanations existed",
        "explanations": len(per_explanation), "numbers": len(numbers),
        "numbers_summary": {"flagged": flagged_n, "wrong": wrong_n, "caught": hit,
                            "false_alarms": flagged_n - hit, "missed": wrong_n - hit,
                            "precision": rate(hit, flagged_n), "recall": rate(hit, wrong_n)},
        "explanations_summary": {
            "with_an_error": rate(len(errors), len(per_explanation)),
            "with_a_wrong_number": sum(e["wrong_number"] for e in per_explanation),
            "with_a_false_claim": sum(e["false_claim"] for e in per_explanation),
            "flagged": sum(e["flagged"] for e in per_explanation),
            "errors_flagged": rate(sum(e["flagged"] for e in errors), len(errors)),
            "errors_only_invisible": sum(not e["caught"] for e in errors),
            "flagged_without_an_error": sum(e["flagged"] and not (e["wrong_number"] or
                                                                   e["false_claim"])
                                            for e in per_explanation),
        },
        "numbers_detail": numbers, "explanations_detail": per_explanation,
    }  # fmt: skip
    return result


# ---- score --after: ADR-0009's regenerated explanations ------------------------------------


def labeled(sheets: Path) -> tuple[dict[str, list[str]], dict[str, dict]]:
    """Each problem's number labels, in the sheet's order, and its claims row; a blank or
    unknown label is refused."""
    numbers: dict[str, list[str]] = {}
    claims: dict[str, dict] = {}
    for path in sorted(sheets.glob("labels-*.csv")):
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["label"] not in LABELS:
                    raise SystemExit(f"{path.name}: {row['problem']} number {row['index']} "
                                     "isn't labeled correct or wrong")  # fmt: skip
                numbers.setdefault(row["problem"], []).append(row["label"])
    for path in sorted(sheets.glob("claims-*.csv")):
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["false_claim"] not in ("yes", "no"):
                    raise SystemExit(f"{path.name}: {row['problem']}: false_claim is yes or no")
                claims[row["problem"]] = row
    return numbers, claims


def compare() -> dict:
    """The regenerated explanations' labels against the first run's; writes nothing."""
    before_numbers, before_claims = labeled(SHEETS)
    after_numbers, after_claims = labeled(AFTER_SHEETS)
    rows = explained(AFTER_ROWS)
    problems = [r["problem"] for r in rows]
    if set(problems) != set(after_claims) or set(before_claims) != set(after_claims):
        raise SystemExit("the two labelings don't cover the same 88 explanations")
    lps = [r["problem"] for r in rows if not LPModel.model_validate(r["model"]).is_mip]

    def false(claims: dict[str, dict], p: str) -> bool:
        return claims[p]["false_claim"] == "yes"

    def same_claim(p: str) -> bool:
        return false(before_claims, p) == false(after_claims, p)

    matching = [p for p in lps if same_claim(p) and before_numbers.get(p, []) ==
                after_numbers.get(p, [])]  # fmt: skip
    ips = [p for p in problems if p not in lps]
    rule = {r["problem"]: r for r in json.loads(RULE.read_text())["per_problem"]}
    if set(rule) != set(ips):
        raise SystemExit("the rule's record doesn't cover the same integer programs")

    def against_rule(claims: dict[str, dict], run: str) -> dict:
        """The rule's flags (a false "not limiting" claim) against a labeling's false claims,
        which can be of any kind, over the integer programs: the only ones the rule reads."""
        flagged = [p for p in ips if any(c["verdict"] == "false" for c in rule[p][run])]
        labeled = [p for p in ips if false(claims, p)]
        both = [p for p in flagged if p in labeled]
        return {"flagged": len(flagged), "labeled_false": len(labeled),
                "precision": rate(len(both), len(flagged)),
                "recall": rate(len(both), len(labeled)),
                "flagged_but_labeled_fine": [p for p in flagged if p not in labeled],
                "labeled_false_not_flagged": [p for p in labeled if p not in flagged]}  # fmt: skip

    def count(claims: dict[str, dict], among: list[str]) -> int:
        return sum(false(claims, p) for p in among)

    def wrong(numbers: dict[str, list[str]]) -> int:
        return sum(labels.count("wrong") for labels in numbers.values())

    return {
        "label": "exploratory, dev only: labels by Claude (four Claude subagents per run, an "
                 "LLM's, not a person's), blind, by the same rules and sheets",
        "explanations": len(problems), "integer_programs": len(ips),
        "lp_agreement": {"entries": len(lps), "matching": len(matching), "needed": LP_RULE,
                         "matching_false_claim_label": sum(same_claim(p) for p in lps)},
        "verdict": "inconclusive" if len(matching) < LP_RULE else "comparable",
        "false_claims": {"before": count(before_claims, problems),
                         "after": count(after_claims, problems)},
        "false_claims_integer_programs": {"before": count(before_claims, ips),
                                          "after": count(after_claims, ips)},
        "wrong_numbers": {"before": wrong(before_numbers), "after": wrong(after_numbers)},
        "paired": {
            "false_before_fine_after": sum(false(before_claims, p) and not false(after_claims, p)
                                           for p in problems),
            "fine_before_false_after": sum(false(after_claims, p) and not false(before_claims, p)
                                           for p in problems),
            "false_in_both": sum(false(before_claims, p) and false(after_claims, p)
                                 for p in problems),
            "fine_in_both": sum(not false(before_claims, p) and not false(after_claims, p)
                                for p in problems),
        },
        "rule_vs_labels": {
            "label": "added after the labels were in (the owner's request, 2026-11-21), so post "
                     "hoc: scripts/limits_claims.py's flags against each labeling's false "
                     "claims, of any kind, over the integer programs",
            "before": against_rule(before_claims, "before"),
            "after": against_rule(after_claims, "after"),
        },
        "lp_entries_not_matching": [p for p in lps if p not in matching],
        "per_problem": [{"problem": p, "integer_program": p in ips,
                         "before": false(before_claims, p), "after": false(after_claims, p),
                         "after_note": after_claims[p]["note"]} for p in problems],
    }  # fmt: skip


def render_after(d: dict) -> str:
    lp, f, fi, w, p = (d["lp_agreement"], d["false_claims"], d["false_claims_integer_programs"],
                       d["wrong_numbers"], d["paired"])  # fmt: skip
    verdict = ("**inconclusive**: the labelers didn't agree with the first labeling closely "
               "enough on entries that didn't change" if d["verdict"] == "inconclusive"
               else "comparable")  # fmt: skip
    return "\n".join([
        "### The checker's labels, before and after", "",
        "Exploratory, dev only, one sample per problem; labels by Claude (four Claude subagents "
        "per run, an LLM's, not a person's), blind, by the same rules and sheets.", "",
        f"**The consistency rule:** on the {lp['entries']} LP entries both sheets share word for "
        f"word, the new labels match the first labeling's on {lp['matching']} (every label "
        f"alike; on the false-claim label alone, {lp['matching_false_claim_label']}); "
        f"{lp['needed']} were needed, so the before/after comparison is {verdict}.", "",
        "| | before | after |", "|---|---:|---:|",
        f"| explanations with a false claim (of {d['explanations']}) | {f['before']} | "
        f"{f['after']} |",
        f"| ... of the {d['integer_programs']} integer programs | {fi['before']} | "
        f"{fi['after']} |",
        f"| numbers labeled wrong | {w['before']} | {w['after']} |", "",
        f"Paired by problem: {p['false_before_fine_after']} explanations had a false claim "
        f"before and none after, {p['fine_before_false_after']} the reverse, "
        f"{p['false_in_both']} had one in both, and {p['fine_in_both']} in neither.",
    ])  # fmt: skip


def render_note(d: dict) -> str:
    """The numbers of review/explain_dev_limits/RESULTS.md: the consistency rule, and the
    rule's flags against both labelings over the integer programs."""
    lp, f, fi = d["lp_agreement"], d["false_claims"], d["false_claims_integer_programs"]
    before, after = d["rule_vs_labels"]["before"], d["rule_vs_labels"]["after"]
    verdict = ("**inconclusive**: the counts below are reported as they are, not as a "
               "comparison" if d["verdict"] == "inconclusive" else "**comparable**")  # fmt: skip
    return "\n".join([
        f"**The consistency rule:** {lp['matching']} of the {lp['entries']} LP entries both "
        f"sheets share got the first labeling's labels ({lp['needed']} needed), so the "
        f"before/after comparison is {verdict}.", "",
        f"| over the {d['integer_programs']} integer programs | first explanations | "
        "regenerated |", "|---|---:|---:|",
        f"| labeled with a false claim (any kind) | {fi['before']} | {fi['after']} |",
        f"| flagged by the rule (a false \"not limiting\" claim) | {before['flagged']} | "
        f"{after['flagged']} |",
        f"| the rule's precision (labeled false, of those flagged) | "
        f"{pct(before['precision'])} | {pct(after['precision'])} |",
        f"| the rule's recall (flagged, of those labeled false) | {pct(before['recall'])} | "
        f"{pct(after['recall'])} |", "",
        f"Of all {d['explanations']} explanations, LPs included, {f['before']} were labeled "
        f"with a false claim before and {f['after']} after. Regenerated explanations the rule "
        f"flags but the labels call fine: {', '.join(after['flagged_but_labeled_fine']) or 'none'}"
        f"; labeled false but not flagged: "
        f"{', '.join(after['labeled_false_not_flagged']) or 'none'}.",
    ])  # fmt: skip


def fill(path: Path, begin: str, end: str, text: str) -> None:
    """Replace what a document has between two markers."""
    doc = path.read_text()
    start, stop = doc.index(begin) + len(begin), doc.index(end)
    path.write_text(doc[:start] + "\n\n" + text + "\n\n" + doc[stop:])


def write_after(d: dict) -> None:
    AFTER_OUT.write_text(json.dumps(d, indent=1) + "\n")
    fill(AFTER_DOC, AFTER_BEGIN, AFTER_END, render_after(d))
    fill(NOTE, NOTE_BEGIN, NOTE_END, render_note(d))


def score() -> dict:
    result = compute()
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    return result


def pct(r: dict) -> str:
    if r["value"] is None:
        return f"{r['k']} of {r['n']}"
    low, high = r["wilson95"]
    return f"{r['k']} of {r['n']}, {100 * r['value']:.1f}% ({100 * low:.1f} to {100 * high:.1f})"


def render(result: dict) -> str:
    n, e = result["numbers_summary"], result["explanations_summary"]
    return "\n".join([
        "## Results", "",
        f"{result['explanations']} explanations, {result['numbers']} numbers. Labels by "
        "Claude (an LLM, not a person) from sheets without the checker's flags. Exploratory.",
        "",
        "| numbers | count |", "|---|---:|",
        f"| flagged by the checker | {n['flagged']} |",
        f"| labeled wrong | {n['wrong']} |",
        f"| flagged and wrong (caught) | {n['caught']} |",
        f"| flagged but correct (false alarms) | {n['false_alarms']} |",
        f"| wrong but not flagged (missed) | {n['missed']} |", "",
        f"Precision (caught over flagged): {pct(n['precision'])}. Recall (caught over wrong): "
        f"{pct(n['recall'])}.", "",
        "| explanations | count |", "|---|---:|",
        f"| with an error (a wrong number or a false claim) | {pct(e['with_an_error'])} |",
        f"| with a wrong number | {e['with_a_wrong_number']} |",
        f"| with a false claim, every number correct | {e['with_a_false_claim']} |",
        f"| flagged by the checker | {e['flagged']} |",
        f"| errors the checker flags | {pct(e['errors_flagged'])} |",
        f"| errors with no wrong number flagged (invisible to it) | "
        f"{e['errors_only_invisible']} |",
        f"| flagged without an error | {e['flagged_without_an_error']} |",
    ])  # fmt: skip


def write_report(result: dict) -> None:
    doc = DOC.read_text()
    start, end = doc.index(BEGIN) + len(BEGIN), doc.index(END)
    DOC.write_text(doc[:start] + "\n\n" + render(result) + "\n\n" + doc[end:])


# ---- prune --------------------------------------------------------------------------------


class Recording(Cache):
    """A cache that remembers every file it served. M6-era files are named by request_sha256
    and found through the cache's index, so it records the file, not the key."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.used: set[Path] = set()

    def get(self, key):
        path = self._path(key)
        found = path if path.exists() else self._indexed().get(key)
        if found is not None:
            self.used.add(found)
        return super().get(key)


def prune() -> None:
    cache, problems = Recording(RUN / "cache"), texts()
    for r in map(json.loads, ROWS.read_text().splitlines()):
        # the run predates ADR-0009: its explanation requests carry no limits
        result = agent.run(problems[r["problem"]], ReplayOnlyClient(), r.get("model_id") or
                           "claude-haiku-5-5", with_explanation=True, max_attempts=1,
                           session=Run(cache=cache), explain_limits=False)  # fmt: skip
        if (result.explanation.text if result.explanation else None) != r["explanation"]:
            raise SystemExit(f"{r['problem']} doesn't replay its explanation")
    unused = [p for p in (RUN / "cache").glob("*.json") if p not in cache.used]
    for path in unused:
        path.unlink()
    print(f"kept {len(cache.used)} replies, removed {len(unused)} unused copies")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The explanation checker's evaluation on dev.")
    parser.add_argument("step", choices=["sheet", "score", "prune"])
    parser.add_argument("--after", action="store_true", help="sheet: ADR-0009's regenerated run")
    args = parser.parse_args(argv)
    if args.step == "sheet":
        write_sheets(*((AFTER_ROWS, AFTER_SHEETS) if args.after else (ROWS, SHEETS)))
    elif args.step == "score" and args.after:
        result = compare()
        write_after(result)
        print(render_after(result) + "\n\n" + render_note(result))
    elif args.step == "prune":
        prune()
    else:
        result = score()
        write_report(result)
        print(render(result))


if __name__ == "__main__":
    main()
