"""The IE 2310 kit's numbers and figures (docs/ie2310/), from results/eval.json and
results/followup.json only, so nothing in the kit can drift from the studies.

- numbers.md and numbers.csv: every number the kit cites, each with the JSON path it comes
  from. A few are derived (cost per answer: a condition's cost over its answers); those say
  so in their source. tests/test_ie2310.py checks both files are current.
- figures/accuracy.png, figures/failures.png, figures/cost.png: accuracy with 95%
  intervals, silent and loud failures, and cost, by condition, one panel per study.

No API calls; the same inputs give the same tables. The figures need matplotlib, pinned in the
optional requirements-docs.lock: pip install -r requirements-docs.lock -c requirements.lock.

Run:  python scripts/ie2310.py                # tables and figures
      python scripts/ie2310.py --tables-only  # no matplotlib needed
"""

import argparse
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "results" / "eval.json"
FOLLOWUP = ROOT / "results" / "followup.json"
OUT = ROOT / "docs" / "ie2310"
CONDITIONS = {
    "baseline": "No-solver baseline",
    "single-shot": "Single-shot",
    "self-correction": "Self-correction",
    "checklist-revision": "Checklist revision",
}
M6, FU = "NL4Opt (milestone 6)", "Harder problems (follow-up)"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def ci(pair: list[float]) -> str:
    return f"{100 * pair[0]:.1f}–{100 * pair[1]:.1f}%"


def rows() -> list[dict]:
    """Study, what, condition, value (as the kit writes it), source (the JSON path)."""
    e, f = json.loads(EVAL.read_text()), json.loads(FOLLOWUP.read_text())
    out = []

    def add(study, what, condition, value, source):
        out.append({"study": study, "what": what, "condition": condition, "value": value,
                    "source": source})  # fmt: skip

    p, run = e["primary"], e["cost_latency"]["test"]["conditions"]
    add(M6, "test problems scored", "all", str(p["n"]), "eval.json: primary.n")
    for c in ("baseline", "single-shot", "self-correction"):
        a, fail, cost = p["accuracy"][c], p["failures"][c], run[c]
        name = CONDITIONS[c]
        add(
            M6,
            "right answers",
            name,
            f"{a['right']} of {a['n']}",
            f"eval.json: primary.accuracy.{c}.right, .n",
        )
        add(
            M6,
            "accuracy (95% Wilson interval)",
            name,
            f"{pct(a['accuracy'])} ({ci(a['wilson95'])})",
            f"eval.json: primary.accuracy.{c}.accuracy, .wilson95",
        )
        add(
            M6,
            "silent / loud failures",
            name,
            f"{fail['silent']} / {fail['loud']}",
            f"eval.json: primary.failures.{c}.silent, .loud",
        )
        add(
            M6,
            "API cost, all answers",
            name,
            f"${cost['cost_usd']:.3f}",
            f"eval.json: cost_latency.test.conditions.{c}.cost_usd",
        )
        add(
            M6,
            "API cost per answer (derived)",
            name,
            f"${cost['cost_usd'] / a['n']:.5f}",
            f"derived: cost_latency.test.conditions.{c}.cost_usd / primary.accuracy.{c}.n",
        )
        lat = cost["latency_s"]
        add(
            M6,
            "time per answer, median / 95th percentile",
            name,
            f"{lat['p50']:.1f} s / {lat['p95']:.1f} s",
            f"eval.json: cost_latency.test.conditions.{c}.latency_s.p50, .p95",
        )
        add(
            M6,
            "accuracy with the numbers changed (perturbed set)",
            name,
            pct(e["perturbed"]["accuracy"][c]["accuracy"]),
            f"eval.json: perturbed.accuracy.{c}.accuracy",
        )
    add(M6, "perturbed problems", "all", str(e["perturbed"]["n"]), "eval.json: perturbed.n")
    add(
        M6,
        "API cost paid, both test runs",
        "all",
        f"${e['cost_latency']['paid_usd_total']:.2f}",
        "eval.json: cost_latency.paid_usd_total",
    )

    v, pr = f["provenance"], f["pre_registered"]["primary"]
    add(FU, "test problems", "all", str(v["problems"]), "followup.json: provenance.problems")
    add(
        FU,
        "problems in the primary analysis (unseen before the split)",
        "all",
        str(pr["problems"]),
        "followup.json: pre_registered.primary.problems",
    )
    add(
        FU,
        "samples per problem and condition",
        "all",
        str(v["samples"]),
        "followup.json: provenance.samples",
    )
    spend, failures = f["also_reported"]["spend"], f["also_reported"]["failures"]
    answers = v["problems"] * v["samples"]
    for c, name in CONDITIONS.items():
        a = pr["accuracy"][c]
        add(
            FU,
            "mean score (95% bootstrap interval)",
            name,
            f"{pct(a['mean_score'])} ({ci(a['mean_score_ci'])})",
            f"followup.json: pre_registered.primary.accuracy.{c}.mean_score, .mean_score_ci",
        )
        add(
            FU,
            "right by majority of the 3 samples",
            name,
            f"{a['majority_right']} of {a['problems']}",
            f"followup.json: pre_registered.primary.accuracy.{c}.majority_right, .problems",
        )
        add(
            FU,
            "silent / loud failures (sample answers, all problems)",
            name,
            f"{failures[c]['silent']} / {failures[c]['loud']}",
            f"followup.json: also_reported.failures.{c}.silent, .loud",
        )
        add(
            FU,
            "API cost, all answers",
            name,
            f"${spend[c]['cost_usd']:.4f}",
            f"followup.json: also_reported.spend.{c}.cost_usd",
        )
        add(
            FU,
            "API cost per answer (derived)",
            name,
            f"${spend[c]['cost_usd'] / answers:.5f}",
            f"derived: also_reported.spend.{c}.cost_usd / (provenance.problems x .samples)",
        )
        add(
            FU,
            "time per answer, median / 95th percentile",
            name,
            f"{spend[c]['latency_p50_s']:.1f} s / {spend[c]['latency_p95_s']:.1f} s",
            f"followup.json: also_reported.spend.{c}.latency_p50_s, .latency_p95_s",
        )
    h2, h1 = pr["primary"]["H2"], pr["primary"]["H1"]
    cut = f["descriptive"]["h2_and_cut_off_replies"]
    add(FU, "H2: single-shot minus baseline", "",
        f"{h2['score_difference_pp']:+.1f} pp (95% CI {h2['score_ci_pp'][0]:.1f} to "
        f"{h2['score_ci_pp'][1]:.1f}); sign-flip Holm p {h2['sign_flip_p_holm']:.4f}: "
        f"{h2['verdict']}",
        "followup.json: pre_registered.primary.primary.H2")  # fmt: skip
    add(
        FU,
        "H2: McNemar on majority votes (secondary)",
        "",
        f"Holm p {h2['mcnemar_p_holm']:.2f}: not significant",
        "followup.json: pre_registered.primary.primary.H2.mcnemar_p_holm",
    )
    add(
        FU,
        "H2: part from baseline replies cut off at max_tokens",
        "",
        f"{cut['from_pairs_with_a_cut_off_reply_pp']:.2f} pp, from "
        f"{cut['pairs_with_a_cut_off_reply']} replies",
        "followup.json: descriptive.h2_and_cut_off_replies",
    )
    add(FU, "H1: checklist revision minus single-shot", "",
        f"{h1['score_difference_pp']:+.1f} pp (95% CI {h1['score_ci_pp'][0]:.1f} to "
        f"{h1['score_ci_pp'][1]:.1f}); Holm p {h1['sign_flip_p_holm']:.4f}: {h1['verdict']}, "
        f"no difference larger than {h1['no_difference_larger_than_pp']} pp",
        "followup.json: pre_registered.primary.primary.H1")  # fmt: skip
    add(
        FU,
        "API cost paid, the test run",
        "all",
        f"${v['paid_usd']:.4f} on {v['paid_calls']} calls",
        "followup.json: provenance.paid_usd, .paid_calls",
    )
    return out


def table_md(data: list[dict]) -> str:
    lines = [
        "# Numbers to cite",
        "",
        "Generated by `scripts/ie2310.py` from `results/eval.json` and `results/followup.json`;",
        "don't edit by hand. Each row names the JSON field it comes from, so any number can be",
        "traced. Rows marked *derived* are computed from those fields as the source says.",
        "Percentages are of problems (NL4Opt) or of sample answers averaged per problem",
        "(follow-up); every interval is 95%.",
        "",
        "| study | what | condition | value | source |",
        "|---|---|---|---|---|",
    ]  # fmt: skip
    lines += [f"| {r['study']} | {r['what']} | {r['condition']} | {r['value']} | `{r['source']}` |"
              for r in data]  # fmt: skip
    return "\n".join(lines) + "\n"


def table_csv(data: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["study", "what", "condition", "value", "source"],
                            lineterminator="\n")  # fmt: skip
    writer.writeheader()
    writer.writerows(data)
    return buffer.getvalue()


# ---- figures ------------------------------------------------------------------------------
# One hue for magnitude, two categorical slots for silent and loud (the dataviz reference
# palette's slots 1 and 2, which it validates for colorblind separation), recessive axes,
# text in text colors, every bar or dot labeled with its value, one panel per study.

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def _style(plt) -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": INK, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    })  # fmt: skip


def _panels(plt, title: str, rows_left: int, rows_right: int):
    height = 1.5 + 0.42 * max(rows_left, rows_right)
    fig, axes = plt.subplots(1, 2, figsize=(10, height), width_ratios=[1, 1])
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="bold")
    for ax in axes:
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0)
    return fig, axes


def figures(out: Path = OUT / "figures") -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _style(plt)
    e, f = json.loads(EVAL.read_text()), json.loads(FOLLOWUP.read_text())
    m6 = ["baseline", "single-shot", "self-correction"]
    fu = list(CONDITIONS)
    out.mkdir(parents=True, exist_ok=True)

    # accuracy with 95% intervals
    fig, (left, right) = _panels(plt, "Accuracy by condition, with 95% intervals", 3, 4)
    for ax, conditions, get, title in (
        (left, m6, lambda c: (e["primary"]["accuracy"][c]["accuracy"],
                              e["primary"]["accuracy"][c]["wilson95"]),
         f"{M6}\n{e['primary']['n']} problems"),
        (right, fu, lambda c: (f["pre_registered"]["primary"]["accuracy"][c]["mean_score"],
                               f["pre_registered"]["primary"]["accuracy"][c]["mean_score_ci"]),
         f"{FU}\n{f['pre_registered']['primary']['problems']} unseen problems, mean of 3 samples"),
    ):  # fmt: skip
        for y, c in enumerate(reversed(conditions)):
            value, (low, high) = get(c)
            ax.plot([100 * low, 100 * high], [y, y], color=BLUE, linewidth=2,
                    solid_capstyle="round")  # fmt: skip
            ax.plot(100 * value, y, "o", color=BLUE, markersize=8,
                    markeredgecolor=SURFACE, markeredgewidth=2)  # fmt: skip
            ax.annotate(f"{100 * value:.1f}%", (100 * high, y), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=9, color=INK)  # fmt: skip
        ax.set_yticks(range(len(conditions)), [CONDITIONS[c] for c in reversed(conditions)])
        ax.set_xlim(60, 104)
        ax.set_xlabel("percent right (dot) and its 95% interval (line)")
        ax.set_title(title, fontsize=10, color=MUTED, fontweight="normal")
    fig.tight_layout()
    fig.savefig(out / "accuracy.png", dpi=200)
    plt.close(fig)

    # silent and loud failures
    fig, (left, right) = _panels(plt, "Failures by condition: silent (passed every check) "
                                      "and loud (no answer reported)", 3, 4)  # fmt: skip
    answers = f["provenance"]["problems"] * f["provenance"]["samples"]
    for ax, conditions, get, title in (
        (left, m6, lambda c: e["primary"]["failures"][c],
         f"{M6}\nout of {e['primary']['n']} answers per condition"),
        (right, fu, lambda c: f["also_reported"]["failures"][c],
         f"{FU}\nout of {answers} sample answers per condition"),
    ):  # fmt: skip
        for y, c in enumerate(reversed(conditions)):
            silent, loud = get(c)["silent"], get(c)["loud"]
            ax.barh(y, silent, color=BLUE, height=0.55, edgecolor=SURFACE, linewidth=2,
                    label="silent" if y == 0 else None)  # fmt: skip
            ax.barh(y, loud, left=silent, color=ORANGE, height=0.55, edgecolor=SURFACE,
                    linewidth=2, label="loud" if y == 0 else None)  # fmt: skip
            ax.annotate(f"{silent} silent / {loud} loud", (silent + loud, y), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=9)  # fmt: skip
        ax.set_yticks(range(len(conditions)), [CONDITIONS[c] for c in reversed(conditions)])
        top = max(get(c)["silent"] + get(c)["loud"] for c in conditions)
        ax.set_xlim(0, top * 1.55)
        ax.set_xlabel("failures")
        ax.set_title(title, fontsize=10, color=MUTED, fontweight="normal")
    fig.tight_layout()
    fig.legend(*right.get_legend_handles_labels(), loc="upper right", ncol=2, frameon=False,
               fontsize=9)  # fmt: skip
    fig.savefig(out / "failures.png", dpi=200)
    plt.close(fig)

    # cost
    fig, (left, right) = _panels(plt, "API cost by condition (Claude Haiku 5.5)", 3, 4)
    run = e["cost_latency"]["test"]["conditions"]
    for ax, conditions, get, title in (
        (left, m6, lambda c: run[c]["cost_usd"], f"{M6}\nall {e['primary']['n']} answers"),
        (right, fu, lambda c: f["also_reported"]["spend"][c]["cost_usd"],
         f"{FU}\nall {answers} sample answers"),
    ):  # fmt: skip
        for y, c in enumerate(reversed(conditions)):
            ax.barh(y, get(c), color=BLUE, height=0.55)
            ax.annotate(f"${get(c):.3f}", (get(c), y), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=9)  # fmt: skip
        ax.set_yticks(range(len(conditions)), [CONDITIONS[c] for c in reversed(conditions)])
        ax.set_xlim(0, max(get(c) for c in conditions) * 1.3)
        ax.set_xlabel("US dollars, every call the answers used")
        ax.set_title(title, fontsize=10, color=MUTED, fontweight="normal")
    fig.tight_layout()
    fig.savefig(out / "cost.png", dpi=200)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The IE 2310 kit's tables and figures.")
    parser.add_argument("--tables-only", action="store_true", help="skip the figures")
    args = parser.parse_args(argv)
    data = rows()
    (OUT / "numbers.md").write_text(table_md(data))
    (OUT / "numbers.csv").write_text(table_csv(data))
    if not args.tables_only:
        figures()
    print(f"wrote {OUT.relative_to(ROOT)}: numbers.md, numbers.csv"
          + ("" if args.tables_only else ", figures/"))  # fmt: skip


if __name__ == "__main__":
    main()
