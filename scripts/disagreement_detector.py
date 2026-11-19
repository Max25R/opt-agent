"""Run the disagreement detector once (docs/analysis/disagreement_detector.md) over both studies'
committed answers and write docs/analysis/disagreement_detector.json; `--report` rewrites the
doc's results section from that record and never runs the detector.

Each study's answers are read and scored in its tag's own tree (opt_agent.frozen, as in
scripts/reproduce.py), by its own grader and with its own "same answer" rule, so the
tolerance is the grader's. No model is replayed (the signals only compare answers) and no
API call is made. Nothing written holds problem text: rows give labels and booleans.

It runs once: with the JSON there, it refuses, so the rules can't be tuned on the results.

Run:  python scripts/disagreement_detector.py            # once; no key; about a minute
      python scripts/disagreement_detector.py --report   # the doc's results section again
"""

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs" / "analysis"
OUT, DOC = ANALYSIS / "disagreement_detector.json", ANALYSIS / "disagreement_detector.md"
NUMBER_COVERAGE, TYPES_CSV = ANALYSIS / "silent_detector.json", ANALYSIS / "failure_types.csv"
BEGIN = "<!-- results: written by `python scripts/disagreement_detector.py --report` -->"
END = "<!-- end of results -->"
RUN_FILES = ("manifest.json", "results.jsonl", "attempts.jsonl", "spend.jsonl")
LLM4OR = "data/external/llm4or-clean"
STUDIES = {  # study -> (tag, run, the signals it has)
    "followup": ("followup-freeze", "runs/followup-test", ("a", "b", "c", "d")),
    "nl4opt": ("m6-freeze", "runs/test", ("c", "d")),
}
SAMPLES = (0, 1, 2)  # the follow-up's
# Rule 5's disputed problems, as the doc lists them; check_disputed() holds them to the CSV.
DISPUTED = {
    "followup": {"complexlp:63", "complexlp:78", "complexlp:81", "complexlp:83", "complexlp:94",
                 "industryor:17", "industryor:22", "industryor:24", "industryor:26",
                 "industryor:27", "industryor:28", "industryor:30", "industryor:41"},
    "nl4opt": {"-1540907330", "-2138755435", "-926961422", "1605420061", "2078392466"},
}  # fmt: skip
CSV_RUN = {"followup": ("followup", "followup-test"), "nl4opt": ("m6", "test")}
SIGNAL_NAMES = {"a": "(a) the samples disagree", "b": "(b) the checklist disagrees",
                "c": "(c) the baseline disagrees", "d": "(d) any of them"}  # fmt: skip


# ---- the signals (run in each tag's tree, with its grader's rule) --------------------------


def all_agree(answers: list, same) -> bool:
    """Every pair gives the same answer (with a tolerance, "same" isn't transitive)."""
    return all(same(x, y) for i, x in enumerate(answers) for y in answers[i + 1 :])


def unit_row(problem: str, sample: int, right: bool, single, same, *, samples=None,
             checklist=None, baseline=None, has_checklist: bool = False,
             exposed: bool = False) -> dict:  # fmt: skip
    """One single-shot answer's row (rule 4). `samples`: every single-shot sample's answer of
    the problem (None: a study with one sample); a missing answer (None) differs from any."""
    return {
        "problem": problem, "sample": sample, "exposed": exposed, "right": right,
        "a": None if samples is None else not all_agree(samples, same),
        "b": not same(checklist, single) if has_checklist else None,
        "c": not same(baseline, single),
    }  # fmt: skip


def inside_followup(out: Path) -> None:
    from opt_agent import evaluate, followup
    from opt_agent import followup_report as fr

    problems = {p.id: p for p in followup.load_test() if p.scorable}
    exposed = fr.exposed_labels()
    answers = {(i.problem_id, i.condition, i.sample): fr.answer_of(i)
               for i in evaluate.latest_items(Path(STUDIES["followup"][1]) / "results.jsonl")
               if i.outcome == "done"}  # fmt: skip
    rows = []
    for label, problem in sorted(problems.items()):
        samples = [answers.get((label, "single-shot", s)) for s in SAMPLES]
        for s, single in zip(SAMPLES, samples, strict=True):
            if single is None:  # a loud failure: nothing to flag (rule 1)
                continue
            rows.append(unit_row(
                label, s, fr.is_right(problem, single), single, fr.same_answer,
                samples=samples, checklist=answers.get((label, "checklist-revision", s)),
                baseline=answers.get((label, "baseline", s)), has_checklist=True,
                exposed=label in exposed))  # fmt: skip
    out.write_text(json.dumps(rows))


def inside_nl4opt(out: Path) -> None:
    from opt_agent import run_results
    from opt_agent.ground_truth import same_value

    def same(a, b) -> bool:  # the M6 grader's: the same status, objectives by same_value
        if a is None or b is None:
            return a is b
        return a[0] == b[0] and (a[0] != "optimal" or same_value(a[1], b[1]))

    run = run_results.load(Path(STUDIES["nl4opt"][1]))
    pairs = {(p.problem_id, p.condition): p for p in run.pairs if p.state == "scored"}

    def answer(pair):
        item = pair.item if pair is not None else None
        if item is None or item.outcome != "done" or item.status is None:
            return None
        if item.status == "optimal":  # an optimum without a value says nothing to compare
            return None if item.objective is None else (item.status, item.objective)
        return item.status, None

    rows = []
    for pid in run.manifest.problem_ids:
        single_pair = pairs.get((pid, "single-shot"))
        single = answer(single_pair)
        if single is None:
            continue
        rows.append(unit_row(pid, 0, single_pair.score.correct, single, same,
                             baseline=answer(pairs.get((pid, "baseline")))))  # fmt: skip
    out.write_text(json.dumps(rows))


# ---- the counts (at HEAD) -----------------------------------------------------------------


def with_any(rows: list[dict]) -> list[dict]:
    """Signal (d): any signal the study has."""
    return [r | {"d": any(r[k] for k in ("a", "b", "c") if r[k] is not None)} for r in rows]


def rate(k: int, n: int) -> dict:
    from opt_agent.stats import wilson

    return {"k": k, "n": n, "value": k / n if n else None, "wilson95": list(wilson(k, n))}


def confusion(rows: list[dict], signal: str) -> dict:
    silent = [r for r in rows if not r["right"]]
    flagged = [r for r in rows if r[signal]]
    hits = sum(not r["right"] for r in flagged)
    return {"answers": len(rows), "silent": len(silent), "flagged": len(flagged),
            "flagged_silent": hits, "base_rate": rate(len(silent), len(rows)),
            "flag_rate": rate(len(flagged), len(rows)), "precision": rate(hits, len(flagged)),
            "recall": rate(hits, len(silent)),
            "flagged_problems": len({r["problem"] for r in flagged})}  # fmt: skip


def populations(rows: list[dict], disputed: set[str]) -> dict[str, list[dict]]:
    return {"all": rows, "without_disputed": [r for r in rows if r["problem"] not in disputed]}


def real_signal(followup: dict[str, dict], signal: str) -> bool:
    """Rule 7: precision's lower 95% end above the base rate, with and without the disputes."""
    return all(c[signal]["precision"]["wilson95"][0] > c[signal]["base_rate"]["value"]
               for c in followup.values())  # fmt: skip


def disputed_from_csv(study: str) -> set[str]:
    with TYPES_CSV.open() as f:
        return {r["problem"] for r in csv.DictReader(f)
                if (r["study"], r["run"]) == CSV_RUN[study]
                and r["primary"] == "answer-key dispute"}  # fmt: skip


def number_coverage() -> dict:
    """The other detector's single-shot answers (its committed rows), on rule 5's populations,
    and its pooled figure, as its doc reports it."""
    record = json.loads(NUMBER_COVERAGE.read_text())
    single = [{"problem": r["problem"], "right": r["right"], "flagged": r["flagged"]}
              for r in record["rows"] if r["condition"] == "single-shot"]  # fmt: skip
    pooled = record["pooled"]
    return {name: confusion(rows, "flagged")
            for name, rows in populations(single, DISPUTED["followup"]).items()} | {
        "pooled": {"precision": pooled["precision"]["value"],
                   "base_rate": pooled["silent_failures"] / pooled["answers"]}}  # fmt: skip


def run() -> dict:
    if OUT.exists():
        raise SystemExit(f"{OUT.name} exists: the detector runs once, so its rules can't "
                         "be tuned on the results (its doc says why)")  # fmt: skip
    for study, listed in DISPUTED.items():
        if disputed_from_csv(study) != listed:
            raise SystemExit(f"rule 5's {study} disputes differ from failure_types.csv")
    sys.path.insert(0, str(ROOT / "src"))
    from opt_agent.frozen import Tree

    git = ["git", "-C", str(ROOT)]
    commit = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=True).stdout.strip()  # fmt: skip
    dirty = subprocess.run([*git, "status", "--porcelain", "--", "src", "scripts", "docs"],
                           capture_output=True, text=True, check=True).stdout  # fmt: skip
    rows = {}
    with tempfile.TemporaryDirectory() as tmp:
        for study, (tag, run_dir, _) in STUDIES.items():
            tree = Tree.extract(tag, Path(tmp) / study)
            extra = (LLM4OR,) if study == "followup" else ()
            tree.copy(*(f"{run_dir}/{name}" for name in RUN_FILES), *extra,
                      "scripts/disagreement_detector.py")  # fmt: skip
            tree.python("scripts/disagreement_detector.py", "--inside", study, "rows.json")
            rows[study] = with_any(json.loads(tree.read("rows.json")))
    studies = {study: {name: {s: confusion(subset, s) for s in STUDIES[study][2]}
                       for name, subset in populations(rows[study], DISPUTED[study]).items()}
               for study in STUDIES}  # fmt: skip
    result = {
        "label": "exploratory: the rules were committed before this one run "
                 "(docs/analysis/disagreement_detector.md); no tuning after it",
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit, "uncommitted_changes": bool(dirty),
        "studies": studies,
        "number_coverage": number_coverage(),
        "real_signal": {s: real_signal(studies["followup"], s) for s in ("a", "b", "c", "d")},
        "rows": rows,
    }  # fmt: skip
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    return result


# ---- the doc's results section ------------------------------------------------------------


def pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def with_ci(r: dict) -> str:
    low, high = r["wilson95"]
    return f"{pct(r['value'])} ({100 * low:.1f} to {100 * high:.1f})"


def table(rows: list[tuple[str, dict]]) -> list[str]:
    lines = ["| signal | answers | silent: base rate (95% CI) | flagged: flag rate (95% CI) | "
             "precision (95% CI) | recall (95% CI) | flagged problems |",
             "|---|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    for name, c in rows:
        lines.append(f"| {name} | {c['answers']} | {c['silent']}: {with_ci(c['base_rate'])} "
                     f"| {c['flagged']}: {with_ci(c['flag_rate'])} | {with_ci(c['precision'])} "
                     f"| {with_ci(c['recall'])} | {c['flagged_problems']} |")  # fmt: skip
    return lines


def render(result: dict) -> str:
    dirty = " with uncommitted changes" if result["uncommitted_changes"] else ""
    when = f"at `{result['commit'][:7]}`{dirty}"
    out = ["## Results (the one run)", "",
           f"Run once, {when} ({result['ran_at']}). Exploratory; Wilson intervals treat "
           "answers as independent, so they're too narrow (rule 7).", ""]  # fmt: skip
    titles = {("followup", "all"): "Follow-up, all 128 problems",
              ("followup", "without_disputed"): "Follow-up, without the 13 disputed problems",
              ("nl4opt", "all"): "NL4Opt, all 274 problems",
              ("nl4opt", "without_disputed"): "NL4Opt, without the 5 disputed"}  # fmt: skip
    for (study, population), title in titles.items():
        signals = result["studies"][study][population]
        rows = [(SIGNAL_NAMES[s], c) for s, c in signals.items()]
        if study == "followup":
            rows.append(("number coverage (single-shot)", result["number_coverage"][population]))
        out += [f"**{title}.**", "", *table(rows), ""]
    pooled = result["number_coverage"]["pooled"]
    passing = [SIGNAL_NAMES[s] for s, ok in result["real_signal"].items() if ok]
    out += [f"The number-coverage detector's pooled figure (three conditions): precision "
            f"{pct(pooled['precision'])} against a {pct(pooled['base_rate'])} base rate.", "",
            "**Rule 7** (decided before the run): "
            + (f"real signal for {', '.join(passing)}." if passing else
               "no signal shows real signal: none has its precision's lower 95% end above the "
               "base rate both with and without the 13 disputed problems.")]  # fmt: skip
    return "\n".join(out)


def write_report() -> None:
    doc = DOC.read_text()
    start, end = doc.index(BEGIN) + len(BEGIN), doc.index(END)
    DOC.write_text(doc[:start] + "\n\n" + render(json.loads(OUT.read_text())) + "\n\n" + doc[end:])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The disagreement detector, run once.")
    parser.add_argument("--inside", nargs=2, metavar=("STUDY", "OUT"), help=argparse.SUPPRESS)
    parser.add_argument("--report", action="store_true", help="only rewrite the doc's results")
    args = parser.parse_args(argv)
    if args.inside:
        study, out = args.inside
        (inside_followup if study == "followup" else inside_nl4opt)(Path(out))
    elif args.report:
        write_report()
    else:
        run()
        write_report()
        print(f"wrote {OUT.relative_to(ROOT)} and the results in {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
