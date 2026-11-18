"""The failure-type analysis (docs/analysis/failure_types.md): packets to classify from, the
re-solve check each corrected model gets, and the build of the counts and the figure.

    python scripts/failure_cases.py               # first: review/failure_types/cases.jsonl
    python scripts/failure_types.py packets       # one packet per problem, for the classifier
    python scripts/failure_types.py check ID FIX  # re-solve one corrected model (logged)
    python scripts/failure_types.py build         # labels -> docs/analysis/ (CSV, counts, figure)

Working files (problem text: licensed data) stay in the git-ignored review/failure_types/.
No key, no API calls: the check is the solvers' and the scoring's own code, at HEAD.
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opt_agent import followup  # noqa: E402
from opt_agent.agent import format_model  # noqa: E402
from opt_agent.ground_truth import same_value  # noqa: E402
from opt_agent.highs import solve_with_highs  # noqa: E402
from opt_agent.schema import LPModel  # noqa: E402
from opt_agent.solver import Status, solve  # noqa: E402
from opt_agent.verify import check_solution, same_answer  # noqa: E402

WORK = ROOT / "review" / "failure_types"
CASES = WORK / "cases.jsonl"
PACKETS, MODELS, LABELS, FIXES = (WORK / d for d in ("packets", "models", "labels", "fixes"))
CHECK_LOG = WORK / "checks.jsonl"


def model_key(model: dict | None) -> str:
    """A model's name across answers: the same model, the same key (none: no usable model)."""
    if model is None:
        return "none"
    return hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()[:10]


def case_id(case: dict) -> str:
    """By run: M6's perturbed problems keep their original ids, with other numbers."""
    return f"{case['run']}__{case['problem'].replace(':', '-')}"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text().splitlines()]


def by_problem(cases: list[dict]) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for c in cases:
        out[case_id(c)].append(c)
    return dict(sorted(out.items()))


# ---- the check: a corrected model, re-solved and scored ----------------------------------


def right(case: dict, status: str | None, objective: float | None) -> bool:
    """Scored as the study scores: M6, any accepted reading at 1e-6 (strict accuracy); the
    follow-up, followup.is_correct against the raw key (1e-4, or the rounding clause)."""
    if status is None:
        return False
    if case["study"] == "m6":
        return any(status == s["status"] and (status != Status.OPTIMAL
                                              or same_value(objective, s["objective"]))
                   for _, s in case["accepted"])  # fmt: skip
    key = case["key"]
    optimal = not isinstance(key, str)
    problem = followup.Problem(id=case["problem"], document="", answer=key if optimal else None,
                               key_status=Status.OPTIMAL if optimal else Status(key),
                               key_decimals=case.get("key_decimals"))  # fmt: skip
    return followup.is_correct(problem, status, objective)


def solve_checked(model: LPModel) -> dict:
    """Both solvers, and the arithmetic checks: the pipeline's own notion of confirmed."""
    cbc, highs = solve(model), solve_with_highs(model)
    confirmed = same_answer(model, cbc, highs) and not check_solution(model, cbc)
    return {"status": str(cbc.status) if confirmed else None,
            "objective": cbc.objective if confirmed else None,
            "cbc": [str(cbc.status), cbc.objective], "highs": [str(highs.status), highs.objective],
            "confirmed": confirmed}  # fmt: skip


def check(problem_id: str, fix_path: Path, log: bool = True) -> dict:
    cases = by_problem(load_cases())[problem_id]
    model = LPModel.model_validate(json.loads(fix_path.read_text()))
    solved = solve_checked(model)
    verdict = right(cases[0], solved["status"], solved["objective"])
    entry = {"time": datetime.now(UTC).isoformat(timespec="seconds"), "problem": problem_id,
             "fix": fix_path.name, "fix_sha256": hashlib.sha256(fix_path.read_bytes()).hexdigest(),
             **solved, "right": verdict}  # fmt: skip
    if log:
        with CHECK_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    return entry


# ---- packets -------------------------------------------------------------------------------


def show(model: dict | None) -> str:
    if model is None:
        return "(no usable model)"
    return "\n".join(format_model(LPModel.model_validate(model)))


def answer_text(c: dict) -> str:
    if c["loud"]:
        return f"no answer ({c['no_answer'] or c['stopped']}; {c['reply_error']})"
    return f"{c['status']} {c['objective']}" if c["objective"] is not None else c["status"]


def packet(pid: str, cases: list[dict]) -> str:
    first = cases[0]
    lines = [f"# {pid}", "", f"- study: {first['study']}; problem `{first['problem']}`"]
    if first["study"] == "m6":
        acc = "; ".join(f"{r}: {s['status']} {s['objective']}" for r, s in first["accepted"])
        lenient = "; ".join(f"{r}: {s['status']} {s['objective']}"
                            for r, s in first["accepted_lenient"])  # fmt: skip
        lines += [f"- accepted answers (strict scoring): {acc}",
                  f"- accepted if integrality weren't graded (lenient): {lenient}",
                  "", "## Reference model (from NL4Opt's annotations)", "", "```",
                  show(first["reference_model"]), "```"]  # fmt: skip
    else:
        lines += [
            f"- key: {first['key']} (written with {first['key_decimals']} decimals; "
            "right within 1e-4 relative, or rounding to the key's decimals)"
        ]
        if first.get("question_type"):
            lines.append(f"- IndustryOR's own type tag: {first['question_type']}")
        if first["exposed"]:
            lines.append("- exposed: seen during development (left out of the primary analysis)")
    lines += ["", "## Problem text", "", "```", first["text"].strip(), "```"]
    groups = defaultdict(list)
    for c in cases:
        groups[model_key(c["model"])].append(c)
    for key, members in groups.items():
        c = members[0]
        who = ", ".join(f"{m['run']} {m['condition']} sample {m['sample']}" for m in members)
        lines += ["", f"## Wrong model `{key}`", "", f"- answers: {len(members)} ({who})",
                  f"- its answer: {answer_text(c)}", f"- attempts: {c['attempts']}"]  # fmt: skip
        if c["model"] is not None:
            path = MODELS / f"{pid}__{key}.json"
            path.write_text(json.dumps(c["model"], indent=1) + "\n")
            lines.append(f"- JSON: `{path.relative_to(ROOT)}`")
        if len(c["attempt_models"]) > 1:
            lines.append("- earlier attempts (self-correction): "
                         + ", ".join(model_key(m) for m in c["attempt_models"][:-1]))  # fmt: skip
        for m in members:
            rev = m.get("revision")
            if rev:
                was = "RIGHT (a right-to-wrong revision)" if rev["right_to_wrong"] else "wrong"
                lines.append(f"- {m['condition']} sample {m['sample']}: a checklist revision, "
                             f"kept; the original answered {rev['original'][0]} "
                             f"{rev['original'][1]}, which was {was}; "
                             f"original model `{model_key(rev['original_model'])}`")  # fmt: skip
        lines += ["", "```", show(c["model"]), "```"]
        originals = {model_key(m["revision"]["original_model"]): m["revision"]
                     for m in members if m.get("revision", {}).get("right_to_wrong")}  # fmt: skip
        for okey, rev in originals.items():
            flags = "; ".join(f"{f.get('kind')}: {f.get('note') or f.get('detail') or ''}"
                              for f in rev["flags"] or [])  # fmt: skip
            lines += ["", f"### The right original `{okey}` that the revision changed",
                      f"- checklist flags: {flags}", "", "```", show(rev["original_model"]),
                      "```"]  # fmt: skip
    return "\n".join(lines) + "\n"


def write_packets() -> None:
    for d in (PACKETS, MODELS, LABELS, FIXES):
        d.mkdir(parents=True, exist_ok=True)
    groups = by_problem(load_cases())
    for pid, cases in groups.items():
        (PACKETS / f"{pid}.md").write_text(packet(pid, cases))
    print(f"{len(groups)} packets -> {PACKETS.relative_to(ROOT)}")


# ---- build: labels -> docs/analysis/ --------------------------------------------------------

TYPES = ["wrong objective", "missing constraint", "wrong number/coefficient",
         "wrong inequality direction", "integrality", "units/misread quantity",
         "answer-key dispute", "other"]  # fmt: skip
STUDIES = {"m6": "M6 (NL4Opt test and perturbed runs)",
           "followup": "Follow-up (ComplexLP and IndustryOR)"}  # fmt: skip
CONDITIONS = ["single-shot", "self-correction", "checklist-revision"]
OUT_DIR = ROOT / "docs" / "analysis"
CSV_OUT, JSON_OUT, FIG_OUT = (OUT_DIR / f"failure_types.{x}" for x in ("csv", "json", "png"))
FIX_OUT = OUT_DIR / "fixes"
DOC = OUT_DIR / "failure_types.md"
BEGIN = "<!-- results: written by `python scripts/failure_types.py build` -->"
END = "<!-- end of results -->"
# M6's pre-registered categories (taxonomy.py), mapped onto this list, to compare with the
# judges' labels (review/taxonomy/test/labels.csv) after classifying.
M6_CATEGORY = {"objective": "wrong objective", "missing-constraint": "missing constraint",
               "coefficient": "wrong number/coefficient", "direction": "wrong inequality direction",
               "integrality": "integrality", "constraint-scope": "units/misread quantity",
               "reference": "answer-key dispute", "invented-constraint": "other",
               "calculation": "other", "rounding": "other", "other": "other"}  # fmt: skip
M6_JUDGES = ROOT / "review" / "taxonomy" / "test" / "labels.csv"
# A corrected model bigger than this restates a whole instance (IndustryOR's, non-commercial
# data), so it stays in the git-ignored working folder; the CSV still records its verdict.
MAX_COMMITTED_FIX = 100_000  # bytes


def committed(fix: str | None) -> bool:
    return bool(fix) and (WORK / fix).stat().st_size <= MAX_COMMITTED_FIX


def load_labels() -> dict[str, dict]:
    return {json.loads(p.read_text())["id"]: json.loads(p.read_text())
            for p in sorted(LABELS.glob("*.json"))}  # fmt: skip


def label_problems(pid: str, key: str, label: dict) -> list[str]:
    found = []
    if label.get("primary") not in TYPES:
        found.append(f"{pid} {key}: primary {label.get('primary')!r} isn't a type")
    found += [f"{pid} {key}: secondary {s!r} isn't a type"
              for s in label.get("secondary", []) if s not in TYPES]  # fmt: skip
    if label.get("primary") == "other" and not label.get("sub_label"):
        found.append(f"{pid} {key}: 'other' needs a sub_label")
    if not label.get("note"):
        found.append(f"{pid} {key}: no note")
    return found


def first_checks() -> dict[tuple[str, str], list[bool]]:
    """Each fix's check results in the order they ran (the log), by (packet, fix file)."""
    out = defaultdict(list)
    if CHECK_LOG.exists():
        for line in CHECK_LOG.read_text().splitlines():
            e = json.loads(line)
            out[(e["problem"], e["fix"])].append(e["right"])
    return out


def rows_and_fixes() -> tuple[list[dict], dict]:
    """One row per wrong answer, with its model's label and its fix's re-solve verdict."""
    labels, problems, rows, verdicts = load_labels(), [], [], {}
    for pid, members in by_problem(load_cases()).items():
        models = labels.get(pid, {}).get("models", {})
        for c in members:
            key = model_key(c["model"])
            label = models.get(key)
            if label is None:
                problems.append(f"{pid} {key}: no label")
                continue
            problems += label_problems(pid, key, label)
            if (pid, key) not in verdicts:
                fix = label.get("fix")
                verdicts[(pid, key)] = None if not fix else check(pid, WORK / fix, log=False)
            verdict = verdicts[(pid, key)]
            rev = c.get("revision") or {}
            rows.append({
                "study": c["study"], "run": c["run"], "problem": c["problem"],
                "condition": c["condition"], "sample": c["sample"],
                "exposed": bool(c.get("exposed")), "loud": c["loud"],
                "primary": label["primary"], "secondary": ";".join(label.get("secondary", [])),
                "sub_label": label.get("sub_label") or "", "model": key,
                "fix": Path(label["fix"]).name if label.get("fix") else "",
                "fix_committed": "" if not label.get("fix")
                else ("yes" if committed(label["fix"]) else "no"),
                # what the corrected model solves to (tests/test_failure_types.py re-solves it)
                "fix_status": "" if verdict is None else (verdict["status"] or "unconfirmed"),
                "fix_objective": "" if verdict is None or verdict["objective"] is None
                else repr(verdict["objective"]),
                "confirmed": "" if verdict is None else ("yes" if verdict["right"] else "no"),
                "right_to_wrong": bool(rev.get("right_to_wrong")),
                "revision_note": labels[pid].get("revision", {}).get(key, "")
                if rev.get("right_to_wrong") else "",
                "note": label["note"],
            })  # fmt: skip
    if problems:
        raise SystemExit("labels aren't complete:\n" + "\n".join(problems))
    return rows, verdicts


def tally(rows: list[dict], column: str = "primary") -> dict[str, int]:
    counts = {t: 0 for t in TYPES}
    for r in rows:
        counts[r[column]] += 1
    return counts


def summarize(rows: list[dict], verdicts: dict) -> dict:
    out = {"label": "exploratory, post hoc: classified by Claude (an LLM), not a person",
           "studies": {}}  # fmt: skip
    for study in STUDIES:
        mine = [r for r in rows if r["study"] == study]
        models = {(r["run"], r["problem"], r["model"]): r for r in mine}
        any_error = {t: sum(t == r["primary"] or t in r["secondary"].split(";")
                            for r in mine) for t in TYPES}  # fmt: skip
        out["studies"][study] = {
            "answers": len(mine), "silent": sum(not r["loud"] for r in mine),
            "loud": sum(r["loud"] for r in mine), "models": len(models),
            "problems": len({(r["run"], r["problem"]) for r in mine}),
            "primary": tally(mine), "primary_models": tally(list(models.values())),
            "any_error": any_error,
            "confirmed": {t: sum(r["primary"] == t and r["confirmed"] == "yes" for r in mine)
                          for t in TYPES},  # fmt: skip
            "by_condition": {f"{run} {cond}": tally([r for r in mine if r["run"] == run
                                                     and r["condition"] == cond])
                             for run in sorted({r["run"] for r in mine})
                             for cond in CONDITIONS
                             if any(r["run"] == run and r["condition"] == cond for r in mine)},
            "other_sub_labels": dict(sorted(
                {s: sum(r["sub_label"] == s for r in mine if r["primary"] == "other")
                 for s in {r["sub_label"] for r in mine if r["primary"] == "other"}}.items())),
        }  # fmt: skip
    r2w = [r for r in rows if r["right_to_wrong"]]
    out["right_to_wrong"] = {"answers": len(r2w), "primary": tally(r2w)}
    log = first_checks()  # keyed like the check command's arguments: (packet, fix file)
    finals = [(pid, Path(lab["fix"]).name) for (pid, _), lab in _final_labels().items()
              if lab.get("fix")]  # fmt: skip
    out["checks"] = {
        "fixes": len(finals),
        "right": sum(bool(v and v["right"]) for v in verdicts.values()),
        "right_on_the_first_check": sum(log[f][0] for f in finals if log.get(f)),
        "checks_logged": sum(len(v) for v in log.values()),
        "not_committed": sum(not committed(lab.get("fix")) for lab in _final_labels().values()
                             if lab.get("fix")),
    }  # fmt: skip
    out["m6_judges"] = m6_agreement(rows)
    return out


def _final_labels() -> dict[tuple[str, str], dict]:
    return {(pid, key): lab for pid, data in load_labels().items()
            for key, lab in data["models"].items()}  # fmt: skip


def m6_agreement(rows: list[dict]) -> dict | None:
    """The M6 judges' pre-registered labels (main test run), mapped onto these types: on how
    many of the same failures do the primary types agree?"""
    if not M6_JUDGES.exists():
        return None
    import csv

    def solver_row(row: dict) -> bool:
        return "single-shot" in row["conditions"] or "self-correction" in row["conditions"]

    with M6_JUDGES.open() as f:
        judged = {row["problem_id"]: row["category"] for row in csv.DictReader(f)
                  if row.get("category") and solver_row(row)}  # fmt: skip
    mine = {r["problem"]: r["primary"] for r in rows if r["run"] == "test"}
    both = sorted(set(judged) & set(mine))
    agree = [p for p in both if M6_CATEGORY.get(judged[p]) == mine[p]]
    return {"failures": len(both), "agree": len(agree),
            "disagree": {p: [judged[p], mine[p]] for p in both if p not in agree}}  # fmt: skip


def write_csv(rows: list[dict]) -> None:
    import csv

    with CSV_OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def copy_fixes(verdicts: dict) -> None:
    FIX_OUT.mkdir(parents=True, exist_ok=True)
    for old in FIX_OUT.glob("*.json"):
        old.unlink()
    for lab in _final_labels().values():
        if committed(lab.get("fix")):
            (FIX_OUT / Path(lab["fix"]).name).write_bytes((WORK / lab["fix"]).read_bytes())


# Figure style: the same as scripts/ie2310.py (the dataviz reference palette's slots 1 and
# 2, recessive axes, text in text colors, every bar labeled, one panel per study).
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def figure(summary: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": INK, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "svg.hashsalt": "failure-types", "path.simplify": False,
    })  # fmt: skip
    fig, axes = plt.subplots(1, 2, figsize=(11, 2.0 + 0.42 * len(TYPES)), sharey=True)
    title = "Why the wrong answers were wrong (primary type; classified by Claude, an LLM)"
    fig.suptitle(title, x=0.01, y=0.985, ha="left", fontsize=12, fontweight="bold")
    confirmed = "its corrected model re-solves to the key"
    unconfirmed = "not confirmed: no corrected model, or it misses the key"
    for ax, (study, title) in zip(axes, STUDIES.items(), strict=True):
        s = summary["studies"][study]
        for y, t in enumerate(reversed(TYPES)):
            n, ok = s["primary"][t], s["confirmed"][t]
            ax.barh(y, ok, color=BLUE, height=0.55, edgecolor=SURFACE, linewidth=2,
                    label=confirmed if y == 0 else None)  # fmt: skip
            ax.barh(y, n - ok, left=ok, color=ORANGE, height=0.55, edgecolor=SURFACE,
                    linewidth=2, label=unconfirmed if y == 0 else None)  # fmt: skip
            if n:
                ax.annotate(str(n), (n, y), xytext=(5, 0), textcoords="offset points",
                            va="center", fontsize=9)  # fmt: skip
        ax.set_yticks(range(len(TYPES)), list(reversed(TYPES)))
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlim(0, max(s["primary"].values()) * 1.25 + 1)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))  # counts: whole numbers
        ax.set_xlabel("wrong answers")
        ax.set_title(f"{title}\n{s['answers']} wrong answers ({s['models']} distinct models)",
                     fontsize=10, color=MUTED, loc="left")  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.9))  # room for the title and, under it, the legend
    fig.legend(*axes[1].get_legend_handles_labels(), loc="upper left", ncol=2,
               bbox_to_anchor=(0.005, 0.95), frameon=False, fontsize=9)  # fmt: skip
    fig.savefig(FIG_OUT, dpi=200, metadata={"Software": None})
    plt.close(fig)


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:.0f}%" if total else "-"


def results_markdown(summary: dict) -> str:
    st = summary["studies"]
    m6, fu = st["m6"], st["followup"]
    lines = [BEGIN, "", "## Results", "",
             f"Classified by Claude (an LLM), not a person. {m6['answers'] + fu['answers']} "
             f"wrong answers ({m6['models'] + fu['models']} distinct models on "
             f"{m6['problems'] + fu['problems']} problems); per-answer rows in "
             "[`failure_types.csv`](failure_types.csv), counts in "
             "[`failure_types.json`](failure_types.json), corrected models in "
             "[`fixes/`](fixes/).", "",
             "![Wrong answers by primary type, per study](failure_types.png)", "",
             "| Primary type | M6 answers | M6 share | Follow-up answers | Follow-up share | "
             "Follow-up models | Found at all (follow-up) |",
             "|---|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    for t in TYPES:
        lines.append(f"| {t} | {m6['primary'][t]} | {pct(m6['primary'][t], m6['answers'])} | "
                     f"{fu['primary'][t]} | {pct(fu['primary'][t], fu['answers'])} | "
                     f"{fu['primary_models'][t]} | {fu['any_error'][t]} |")  # fmt: skip
    lines += [f"| **all** | {m6['answers']} | | {fu['answers']} | | {fu['models']} | |", "",
              "\"Found at all\" counts answers whose model has the error as its primary or a "
              "secondary type.", ""]  # fmt: skip
    c = summary["checks"]
    lines += [f"**Re-solving.** {c['right']} of {c['fixes']} corrected models re-solve to "
              f"the key ({c['right_on_the_first_check']} on their first check); the rest stay "
              "unconfirmed (`confirmed` = no in the CSV). Answer-key disputes and loud "
              f"failures have no corrected model. {c['checks_logged']} checks were run in all. "
              f"{c['not_committed']} corrected models restate a whole instance (over "
              f"{MAX_COMMITTED_FIX // 1000} KB, IndustryOR's non-commercial data), so they "
              "aren't committed (`fix_committed` = no); their verdicts are.", ""]  # fmt: skip
    lines += ["**By condition** (wrong answers by primary type):", "",
              "| Run and condition | " + " | ".join(TYPES) + " |",
              "|---|" + "---:|" * len(TYPES)]  # fmt: skip
    for study in STUDIES:
        for name, counts in st[study]["by_condition"].items():
            lines.append(f"| {name} | " + " | ".join(str(counts[t]) for t in TYPES) + " |")
    others = {k: v for s in st.values() for k, v in s["other_sub_labels"].items()}
    lines += [
        "",
        '**"Other", by sub-label:** '
        + "; ".join(
            f"{STUDIES[s].split(' (')[0]}: "
            + ", ".join(f"{k} {v}" for k, v in st[s]["other_sub_labels"].items())
            for s in STUDIES
            if st[s]["other_sub_labels"]
        )
        + "."
        if others
        else "",
        "",
    ]
    r2w = summary["right_to_wrong"]
    lines += [f"**The checklist's {r2w['answers']} right-to-wrong revisions**, by the error "
              "the revision added: " + ", ".join(f"{t} {n}" for t, n in r2w["primary"].items()
                                                if n) + ".", ""]  # fmt: skip
    j = summary["m6_judges"]
    if j:
        lines += [f"**Against M6's pre-registered labels** (two LLM judges, main test run "
                  f"only; their categories mapped onto these types): the primary types agree on "
                  f"{j['agree']} of {j['failures']} failures.", ""]  # fmt: skip
    lines.append(END)
    return "\n".join(lines)


def write_doc(summary: dict) -> None:
    text = DOC.read_text()
    section = results_markdown(summary)
    if BEGIN in text:
        head, rest = text.split(BEGIN, 1)
        text = head + section + rest.split(END, 1)[1]
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n"
    DOC.write_text(text)


def build() -> None:
    rows, verdicts = rows_and_fixes()
    summary = summarize(rows, verdicts)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(rows)
    JSON_OUT.write_text(json.dumps(summary, indent=1) + "\n")
    copy_fixes(verdicts)
    figure(summary)
    write_doc(summary)
    print(f"{len(rows)} rows -> {CSV_OUT.relative_to(ROOT)}, {JSON_OUT.name}, {FIG_OUT.name}; "
          f"{DOC.relative_to(ROOT)} results section rewritten")  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("packets")
    c = sub.add_parser("check")
    c.add_argument("problem", help="a packet's id, such as followup__complexlp-102")
    c.add_argument("fix", type=Path)
    sub.add_parser("build")
    args = parser.parse_args()
    if args.command == "packets":
        write_packets()
    elif args.command == "check":
        print(json.dumps(check(args.problem, args.fix)))
    else:
        build()


if __name__ == "__main__":
    main()
