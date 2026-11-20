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

No API calls. Run:  python scripts/explanation_checker.py sheet|score|prune
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
BATCHES = 4
LABELS = {"correct", "wrong"}


def explained() -> list[dict]:
    """The run's explained answers, in its order."""
    return [r for r in map(json.loads, ROWS.read_text().splitlines()) if r["explanation"]]


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


def write_sheets() -> None:
    rows, problems = explained(), texts()
    SHEETS.mkdir(parents=True, exist_ok=True)
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
        (SHEETS / f"batch-{k + 1}.md").write_text("\n".join(lines))
        for name, fields, data in ((f"labels-{k + 1}.csv", ["problem", "index", "token", "label",
                                                            "note"], label_rows),
                                   (f"claims-{k + 1}.csv", ["problem", "false_claim", "note"],
                                    claim_rows)):  # fmt: skip
            path = SHEETS / name
            if path.exists():
                raise SystemExit(f"{path.relative_to(ROOT)} exists: labels are never overwritten")
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(data)
    print(f"wrote {BATCHES} sheets for {len(rows)} explanations to {SHEETS.relative_to(ROOT)}")


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
    args = parser.parse_args(argv)
    if args.step == "sheet":
        write_sheets()
    elif args.step == "prune":
        prune()
    else:
        result = score()
        write_report(result)
        print(render(result))


if __name__ == "__main__":
    main()
