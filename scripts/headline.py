"""The README's headline figure (on its first screen) and its table of cost and latency, from
numbers that are already recorded, so that nothing in either is typed by hand.

- **The figure** (docs/headline.png): NL4Opt's accuracy in each condition and the follow-up's
  two pre-registered differences, each with its 95% interval, read from results/eval.json and
  results/followup.json, the files scripts/reproduce.py rebuilds byte for byte from the tags.
- **The table:** what an answer cost and how long it took (the median and the 90th
  percentile), per condition, from the committed test runs' own logs (runs/test,
  runs/followup-test and runs/second-model, results.jsonl: each answer's cost_usd, every call
  it used at its original token counts, and latency_s, API plus solver time without retry
  waits). The results files report each condition's total cost and its median (and, for
  M6 and the follow-up, its p95), not a p90, so the p90 is computed here with the reports' own
  method (numpy's linear percentile), and only after each condition's total and median come
  out equal to the results file's: the same answers, counted the same way. The second-model
  study's two Claude Sonnet 5.5 conditions (its single-shot stage and its no-solver stage)
  are checked against results/second_model.json, and have no p90: its pre-registration wants
  every number of the study in the README checked against that file, which has none (its
  deviation 2 until the owner dropped Sonnet's p90 on 2026-11-23:
  docs/second_model/DEVIATIONS.md).

Both land in results/headline.json: tests/test_headline.py rebuilds it, and
tests/test_readme_numbers.py checks the README's table against it. The PNG needs matplotlib
(requirements-docs.lock); its numbers are checked, its bytes aren't.

Run:  python scripts/headline.py                 # results/headline.json and docs/headline.png
      python scripts/headline.py --check OUT.png   # the JSON must be current; draws to OUT.png
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "results" / "eval.json"
FOLLOWUP = ROOT / "results" / "followup.json"
SECOND_MODEL = ROOT / "results" / "second_model.json"
RUNS = {"nl4opt": ROOT / "runs" / "test" / "results.jsonl",
        "harder": ROOT / "runs" / "followup-test" / "results.jsonl",
        "sonnet": ROOT / "runs" / "second-model" / "results.jsonl"}  # fmt: skip
OUT = ROOT / "results" / "headline.json"
PNG = ROOT / "docs" / "headline.png"
NL4OPT = ("baseline", "single-shot", "self-correction")
HARDER = (*NL4OPT, "checklist-revision")
SONNET = ("baseline", "single-shot")  # the second-model study's stages 2 and 1
STUDIES = (("nl4opt", NL4OPT), ("harder", HARDER), ("sonnet", SONNET))
WITHOUT_P90 = {"sonnet"}  # its report has no p90, and the README shows only the report's
NAMES = {
    "baseline": "no-solver baseline", "single-shot": "single-shot",
    "self-correction": "self-correction", "checklist-revision": "checklist revision",
}  # fmt: skip
SHORT = {**NAMES, "baseline": "baseline", "checklist-revision": "checklist"}


def figure_numbers(e: dict, f: dict) -> dict:
    """What the figure plots, copied from the results files."""
    primary = f["pre_registered"]["primary"]
    return {
        "nl4opt": {"problems": e["primary"]["n"],
                   "accuracy": {c: e["primary"]["accuracy"][c] for c in NL4OPT}},
        "harder": {"problems": primary["problems"],
                   "differences": {h: {k: primary["primary"][h][k] for k in
                                       ("a", "b", "score_difference_pp", "score_ci_pp",
                                        "verdict")} for h in ("H2", "H1")}},
    }  # fmt: skip


def answers(path: Path) -> dict[str, list[dict]]:
    """Each condition's answers: the last item line of each problem (and sample)."""
    last: dict[tuple, dict] = {}
    for line in path.read_text().splitlines():
        item = json.loads(line)
        if item["kind"] == "item":
            last[(item["problem_id"], item["condition"], item.get("sample"))] = item
    found: dict[str, list[dict]] = {}
    for item in last.values():
        found.setdefault(item["condition"], []).append(item)
    return found


def per_answer(items: list[dict], p90: bool = True) -> dict:
    latency = [i["latency_s"] for i in items]
    p50, p90_s = np.percentile(latency, [50, 90])
    row = {"answers": len(items), "cost_usd": sum(i["cost_usd"] for i in items),
           "cost_per_answer_usd": sum(i["cost_usd"] for i in items) / len(items),
           "latency_p50_s": float(p50)}  # fmt: skip
    if p90:
        row["latency_p90_s"] = float(p90_s)
    return row


def recorded(e: dict, f: dict, s: dict, study: str, condition: str) -> tuple[float, float]:
    """(total cost, median latency) as the results file reports them."""
    if study == "nl4opt":
        row = e["cost_latency"]["test"]["conditions"][condition]
        return row["cost_usd"], row["latency_s"]["p50"]
    if study == "harder":
        row = f["also_reported"]["spend"][condition]
        return row["cost_usd"], row["latency_p50_s"]
    spend = s["spend"] if condition == "single-shot" else s["stage_2"]["spend"]
    return spend["sonnet"]["cost_usd"], spend["sonnet"]["median_latency_s"]


def cost_latency(e: dict, f: dict, s: dict) -> dict:
    table: dict[str, dict] = {}
    for study, conditions in STUDIES:
        found = answers(RUNS[study])
        every = [i for c in conditions for i in found[c]]
        table[study] = {"problems": len({i["problem_id"] for i in every}),
                        "samples": len({i.get("sample") for i in every}),
                        "conditions": {}}  # fmt: skip
        for c in conditions:
            row = per_answer([i for i in found[c] if i["outcome"] == "done"],
                             p90=study not in WITHOUT_P90)  # fmt: skip
            cost, p50 = recorded(e, f, s, study, c)
            if not (math.isclose(row["cost_usd"], cost, rel_tol=1e-9)
                    and math.isclose(row["latency_p50_s"], p50, rel_tol=1e-12)):  # fmt: skip
                raise SystemExit(f"{study}, {c}: the run's answers don't give the results "
                                 "file's total cost and median latency")  # fmt: skip
            table[study]["conditions"][c] = row
    return table


def compute() -> dict:
    e, f = json.loads(EVAL.read_text()), json.loads(FOLLOWUP.read_text())
    s = json.loads(SECOND_MODEL.read_text())
    return {
        "label": "descriptive: the figure's numbers are copied from results/eval.json and "
                 "results/followup.json; cost and latency per answer are computed from the "
                 "committed test runs' logs, each condition's total cost and median latency "
                 "checked equal to its results file's (scripts/headline.py)",
        "figure": figure_numbers(e, f),
        "cost_latency": cost_latency(e, f, s),
    }  # fmt: skip


# ---- the figure -----------------------------------------------------------------------------
# The repository's figure style (scripts/ie2310.py): the dataviz reference palette's slot 1
# for the marks, text in text colors, recessive axes, a dot for the value and a line for its
# 95% interval, every dot labeled. One series per panel, so the titles name it: no legend.

INK, MUTED, GRID, SURFACE, BLUE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb", "#2a78d6"


def draw(numbers: dict, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": INK, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    })  # fmt: skip
    nl4opt, harder = numbers["nl4opt"], numbers["harder"]
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 2.8), width_ratios=[1, 1.35],
                                      layout="constrained")  # fmt: skip
    fig.get_layout_engine().set(w_pad=0.12, h_pad=0.08)
    rows = [(NAMES[c], 100 * a["accuracy"], [100 * x for x in a["wilson95"]],
             f"{100 * a['accuracy']:.1f}%") for c, a in nl4opt["accuracy"].items()]  # fmt: skip
    dots(left, rows, "percent right (95% Wilson interval)")
    left.set_xlim(90, 101)
    left.set_title(f"NL4Opt test, {nl4opt['problems']} problems: accuracy", loc="left",
                   fontsize=10.5, fontweight="bold")  # fmt: skip
    rows = [(f"{h}: {SHORT[d['b']]} − {SHORT[d['a']]}", d["score_difference_pp"],
             d["score_ci_pp"], f"{d['score_difference_pp']:+.1f} pp, {d['verdict']}")
            for h, d in harder["differences"].items()]  # fmt: skip
    dots(right, rows, "percentage points (95% interval)")
    right.axvline(0, color=MUTED, linewidth=1)
    right.set_xlim(-4, 22)
    right.set_title(f"Harder problems, {harder['problems']}: pre-registered tests",
                    loc="left", fontsize=10.5, fontweight="bold")  # fmt: skip
    fig.savefig(out, dpi=200, metadata={"Software": None})
    plt.close(fig)


def dots(ax, rows: list[tuple[str, float, list[float], str]], xlabel: str) -> None:
    """One row per value, top to bottom: the interval's line, the dot, the value's label."""
    for y, (_, value, (low, high), label) in enumerate(reversed(rows)):
        ax.plot([low, high], [y, y], color=BLUE, linewidth=2, solid_capstyle="round")
        ax.plot(value, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE,
                markeredgewidth=2)  # fmt: skip
        ax.annotate(label, (high, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=9, color=INK)  # fmt: skip
    ax.set_yticks(range(len(rows)), [name for name, *_ in reversed(rows)])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel(xlabel)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The README's headline figure and table.")
    parser.add_argument(
        "--check",
        type=Path,
        metavar="OUT.png",
        help="refuse a stale JSON; draw the figure to OUT.png",
    )
    args = parser.parse_args(argv)
    numbers = compute()
    if args.check is not None:
        if json.loads(OUT.read_text()) != numbers:
            sys.exit(f"{OUT.name} isn't current: run python scripts/headline.py")
        draw(numbers["figure"], args.check)
        print(f"{OUT.name} is current; the figure is drawn in {args.check}")
        return
    OUT.write_text(json.dumps(numbers, indent=1) + "\n")
    draw(numbers["figure"], PNG)
    print(f"wrote {OUT.relative_to(ROOT)} and {PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
