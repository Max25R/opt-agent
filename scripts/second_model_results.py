"""docs/second_model/RESULTS.md: the second-model study's write-up, rendered from
results/second_model.json alone.

- **The numbers are the frozen analysis's.** results/second_model.json is what
  `python -m opt_agent.second_model_report` wrote from the owner's run (the analysis whose hash
  docs/second_model/FREEZE-2.json records), and scripts/reproduce.py rebuilds it byte for byte
  in second-model-freeze-2's own tree. Nothing here computes a reported number: it only rounds
  and lays out the file's values.
- **The order is the owner's** (2026-11-22): the pre-registered result first, then the
  sensitivity rows, the secondary results, stage 2, cost, the deviations and the limitations.
  The deviations' details, and the counts the frozen analysis doesn't make, are in
  docs/second_model/DEVIATIONS.md, written by hand from the run's records.

A difference here is in percentage points: the JSON stores it as a share (Sonnet's accuracy
minus Haiku's), so it's shown times 100. No API calls, no timestamps: the same JSON gives the
same bytes.

Run:  python scripts/second_model_results.py   # docs/second_model/RESULTS.md from the JSON
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON = ROOT / "results" / "second_model.json"
RESULTS_MD = ROOT / "docs" / "second_model" / "RESULTS.md"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def interval(rate: dict) -> str:
    low, high = rate["wilson95"]
    return f"{100 * low:.1f}–{100 * high:.1f}%"


def accuracy(rate: dict) -> str:
    return f"{rate['k']} of {rate['n']} | {pct(rate['value'])} ({interval(rate)})"


def silent(rate: dict, of: bool = False) -> str:
    count = f"{rate['k']} of {rate['n']}" if of else f"{rate['k']}"
    return f"{count}: {pct(rate['value'])} ({interval(rate)})"


def p(x: float) -> str:
    """Two significant digits, as 0.17, 0.0043 or 7.0e-8."""
    text = f"{x:#.2g}"
    if "e" in text:
        mantissa, exponent = text.split("e")
        text = f"{mantissa}e{int(exponent)}"
    return text


def points(x: float) -> str:
    """A share as signed percentage points: -0.0579 is -5.8."""
    return f"{100 * x:+.1f}"


def difference(row: dict) -> str:
    low, high = row["difference_ci95"]
    return f"{points(row['difference'])} ({points(low)} to {points(high)})"


def usd(x: float) -> str:
    return f"${x:.4f}"


def verdict_rule(s1: dict) -> str:
    """Section 4's rule, in words, for the verdict the analysis gave."""
    if s1["verdict"] == "incomplete":
        return "the run didn't settle every problem, so there is no verdict"
    if s1["verdict"] == "inconclusive":
        return f"p is at least alpha {s1['alpha']}"
    side = "Sonnet" if s1["verdict"] == "supported" else "Haiku"
    return f"p is below alpha {s1['alpha']}, and {side} got more of those problems right"


def stage_2(two: dict) -> list[str]:
    s, h = two["sonnet"], two["haiku"]
    head = [
        "## Stage 2 (Amendment 1, secondary, no verdict): with and without the solver",
        "",
    ]
    if s is None:
        return [*head, f"Stage 2 is **{two['status']}**: it settled {two['settled']} of the "
                       f"{h['problems']} problems, so Sonnet's comparison isn't computed "
                       "(Amendment 1), and S1's result stands as it is.", ""]  # fmt: skip
    return [
        *head,
        f"Stage 1 settled all {s['problems']} problems, so stage 2 ran: one no-solver answer",
        "per problem from Claude Sonnet 5.5 (Claude answers directly, no model and no solver),",
        f"with Haiku's no-solver settings but the model. It settled all {two['settled']}.",
        "Single-shot against no-solver, for each model: the exact McNemar test, two-sided, and",
        "the difference (single-shot minus no-solver, in points) with the follow-up's",
        "95% bootstrap interval.",
        "",
        "| | single-shot right | no-solver right | only single-shot right | only no-solver right "
        "| p | difference (95% interval) |",
        "|---|---:|---:|---:|---:|---:|---|",
        f"| Claude Sonnet 5.5 | {s['single_shot_right']} | {s['no_solver_right']} "
        f"| {s['only_single_shot_right']} | {s['only_no_solver_right']} | {p(s['p_value'])} "
        f"| {difference(s)} |",
        f"| Claude Haiku 5.5, sample 0 (context) | {h['single_shot_right']} "
        f"| {h['no_solver_right']} | {h['only_single_shot_right']} "
        f"| {h['only_no_solver_right']} | {p(h['p_value'])} | {difference(h)} |",
        "",
        f"Sonnet's no-solver accuracy: {pct(s['no_solver_accuracy']['value'])} "
        f"({interval(s['no_solver_accuracy'])}); Haiku's: "
        f"{pct(h['no_solver_accuracy']['value'])} ({interval(h['no_solver_accuracy'])}).",
        "Haiku's row was known before Amendment 1 and is there for context. Some of Sonnet's",
        "no-solver replies gave no answer at all, more of them than Haiku's (cut off at",
        "`max_tokens`, or an optimum claimed without its value), and those count as wrong; the",
        "frozen analysis doesn't count them for stage 2, so [`DEVIATIONS.md`](DEVIATIONS.md)",
        "does (its first deviation).",
        "",
    ]  # fmt: skip


def cost(data: dict) -> list[str]:
    one, two = data["spend"], data["stage_2"]["spend"]
    columns = [("Sonnet single-shot", one["sonnet"]), ("Haiku single-shot", one["haiku"]),
               ("Sonnet no-solver", two["sonnet"]), ("Haiku no-solver", two["haiku"])]  # fmt: skip
    rows = [
        ("answers", lambda r: f"{r['answers']}"),
        ("right", lambda r: f"{r['right']}"),
        ("total cost", lambda r: usd(r["cost_usd"])),
        ("cost per answer", lambda r: usd(r["cost_per_answer_usd"])),
        ("**cost per right answer**", lambda r: usd(r["cost_per_right_answer_usd"])),
        ("median latency", lambda r: f"{r['median_latency_s']:.1f} s"),
        ("latency per right answer", lambda r: f"{r['latency_per_right_answer_s']:.1f} s"),
        ("input tokens", lambda r: f"{r['input_tokens']}"),
        ("output tokens (thinking included)", lambda r: f"{r['output_tokens']}"),
    ]  # fmt: skip
    return [
        "## Cost and latency (descriptive only)",
        "",
        "Each model at its own prices: every call an answer used, from its token counts.",
        "Latency is API plus solver time without retry waits; per right answer, it's the total",
        "over the right answers. Haiku's columns are its sample 0 in each condition, from the",
        "follow-up's run, a week earlier; latency depends on load, so it's descriptive only.",
        "",
        "| | " + " | ".join(name for name, _ in columns) + " |",
        "|---|" + "---:|" * len(columns),
        *[f"| {label} | " + " | ".join(show(r) for _, r in columns) + " |"
          for label, show in rows],
        "",
        "Both models read the same requests (the same input tokens). Sonnet wrote fewer output",
        "tokens than Haiku at the same effort label, and its median answer took less time; at",
        "its higher prices per token (`pricing.PRICES`), each answer still cost more.",
        "",
    ]  # fmt: skip


def render(data: dict) -> str:
    s1, f, sens = data["s1"], data["failures"], data["sensitivity"]
    sonnet, haiku = f["sonnet"], f["haiku"]
    return "\n".join([
        "# The second-model study: results",
        "",
        "Generated by `scripts/second_model_results.py` from `results/second_model.json`, the",
        "frozen analysis's report (`src/opt_agent/second_model_report.py`, by its hash in",
        "`docs/second_model/FREEZE-2.json`), which `scripts/reproduce.py` rebuilds byte for byte",
        "from the tag; don't edit by hand. Every number here is in that file, and a test checks",
        "it. The study: [the pre-registration](../SECOND_MODEL_PREREGISTRATION.md), with its",
        "Amendment 1; the run: `runs/second-model`, the owner's, on 2026-11-22.",
        "",
        f"## Primary outcome: S1 is {s1['verdict']}",
        "",
        "S1: Claude Sonnet 5.5's single-shot answers are right more often than those of",
        f"Claude Haiku 5.5, on the follow-up's {data['problems']} unexposed harder problems: one",
        "answer per problem from each model, with every setting but the model as in Haiku's",
        "run. Haiku's answer is its sample 0 from the follow-up, fixed before any Sonnet reply",
        "existed. Sonnet was right on",
        f"{s1['sonnet_right']} of the {s1['problems']} problems and Haiku on {s1['haiku_right']}. "
        f"Of the problems only one model got right, {s1['only_sonnet_right']}",
        f"went to Sonnet and {s1['only_haiku_right']} to Haiku. Exact McNemar, two-sided: "
        f"**p = {p(s1['p_value'])}, so S1 is {s1['verdict']}**",
        f"({verdict_rule(s1)}; the rule was fixed before the run).",
        "",
        "| | Haiku right | Haiku wrong |",
        "|---|---:|---:|",
        f"| Sonnet right | {s1['both_right']} | {s1['only_sonnet_right']} |",
        f"| Sonnet wrong | {s1['only_haiku_right']} | {s1['both_wrong']} |",
        "",
        "## S1's effect (reported whatever p is)",
        "",
        "| model | right | accuracy (95% Wilson) |",
        "|---|---|---|",
        f"| Claude Sonnet 5.5 | {accuracy(s1['sonnet_accuracy'])} |",
        f"| Claude Haiku 5.5, sample 0 | {accuracy(s1['haiku_accuracy'])} |",
        "",
        "The paired difference, "
        f"**Sonnet minus Haiku: {points(s1['difference'])} points** (95% bootstrap interval",
        f"{points(s1['difference_ci95'][0])} to {points(s1['difference_ci95'][1])}). "
        "The pre-registered reading of an inconclusive result is \"no difference",
        f"larger than {s1['within_pp']} points\" (the smallest whole number of points the "
        "interval fits inside), never",
        "\"no difference\". Sonnet was right less often, and the interval's upper end is "
        f"{points(s1['difference_ci95'][1])} points.",
        "",
        "## Sensitivity rows (no claim)",
        "",
        "Sample 0 is Haiku's lowest-scoring sample on these problems, which was known and",
        "disclosed before the run (section 2): it favors Sonnet. The same comparison with Haiku's",
        "other two samples in its place, pre-registered with no claim:",
        "",
        "| Haiku's answer | Haiku right | only Sonnet right | only Haiku right | exact McNemar p "
        "| difference (95% interval) |",
        "|---|---:|---:|---:|---:|---|",
        f"| sample 0 (S1) | {s1['haiku_right']} | {s1['only_sonnet_right']} "
        f"| {s1['only_haiku_right']} | {p(s1['p_value'])} | {difference(s1)} |",
        *[f"| sample {n} | {row['haiku_right']} | {row['only_sonnet_right']} "
          f"| {row['only_haiku_right']} | {p(row['p_value'])} | {difference(row)} |"
          for n, row in ((1, sens["haiku_sample_1"]), (2, sens["haiku_sample_2"]))],
        "",
        f"Sonnet's {s1['sonnet_right']} right answers are the same in every row. Haiku's "
        f"accuracy over samples 0 to 2: {pct(sens['haiku_mean_accuracy'])}.",
        "Every row points the same way as S1, and the verdict stays S1's alone.",
        "",
        "## Secondary: how the wrong answers went wrong (no test)",
        "",
        "A *silent* failure is a verified answer (CBC and HiGHS agree on a confirmed optimum and",
        "every check passes) that's wrong; a *loud* one is no answer at all.",
        "",
        "| | Claude Sonnet 5.5 | Claude Haiku 5.5, sample 0 |",
        "|---|---|---|",
        f"| verified answers | {sonnet['verified']} | {haiku['verified']} |",
        f"| silent failures, of the {data['problems']} problems "
        f"| {silent(sonnet['silent'])} | {silent(haiku['silent'])} |",
        "| silent failures, of the verified answers "
        f"| {silent(sonnet['silent_of_verified'], of=True)} "
        f"| {silent(haiku['silent_of_verified'], of=True)} |",
        "| wrong confirmed verdicts (infeasible or unbounded) "
        f"| {sonnet['wrong_verdicts']} | {haiku['wrong_verdicts']} |",
        f"| loud failures | {sonnet['loud']} | {haiku['loud']} |",
        f"| of them, cut off at `max_tokens` | {sonnet['cut_off']} | {haiku['cut_off']} |",
        f"| errored or missing | {sonnet['errored_or_missing']} | {haiku['errored_or_missing']} |",
        "",
        "Most of each model's wrong answers are silent: every check passed, and nothing warned.",
        "",
        *stage_2(data["stage_2"]),
        *cost(data),
        "## Deviations",
        "",
        "Two, recorded in [`DEVIATIONS.md`](DEVIATIONS.md), with notes on the run; neither",
        "changes a number in the report. First, Amendment 1 applies section 3's declared",
        "differences to stage 2, so its cut-off replies are to be reported for each model, and",
        "the frozen analysis doesn't count them for stage 2: they're counted there, from the",
        "run's records. Second, the README's cost table gives Sonnet's p90 latency, which the",
        "report doesn't have: `scripts/headline.py` computes it from the run's log, as it does",
        "for Haiku's rows, and a test checks the README against that record, not against",
        "`results/second_model.json` as section 7 says.",
        "",
        "## Limitations",
        "",
        "- **One answer per problem from each model.** Haiku's three samples were right on",
        f"  {s1['haiku_right']}, {sens['haiku_sample_1']['haiku_right']} and "
        f"{sens['haiku_sample_2']['haiku_right']} of these problems, so one Sonnet sample is a "
        "noisy measure of",
        "  Sonnet; the sensitivity rows show how much the choice of Haiku's sample moves the",
        "  comparison.",
        "- **Haiku's prompts.** The formulation prompt, its schema and the no-solver prompt were",
        "  written and tuned on development problems with Haiku's replies only; nothing was",
        "  tuned for Sonnet. This compares the two models on this pipeline as built, not each",
        "  at its best.",
        "- **The same effort label isn't the same thinking** (section 3's declared differences).",
        "  Both got medium effort with adaptive thinking, and Sonnet wrote fewer output tokens.",
        "  At high effort either model might do differently; that wasn't tested.",
        "- **The keys are the follow-up's,** unchanged, including those an LLM judge flagged",
        "  (not verified by a person). A wrong key scores both models against the same wrong",
        "  number.",
        "- **Public benchmarks.** Either model may have seen these problems in training.",
        "- **Latency** was measured a week apart, under whatever load the API had then.",
        "",
        "## The run",
        "",
        f"`runs/second-model`: stage 1 settled {data['sonnet_settled']} of {data['problems']} "
        f"problems and stage 2 {data['stage_2']['settled']}, with",
        f"{data['sonnet_errored']} errored. What it paid and how it went: "
        "[`DEVIATIONS.md`](DEVIATIONS.md), the notes on the run.",
        "",
    ])  # fmt: skip


def main() -> None:
    RESULTS_MD.write_text(render(json.loads(JSON.read_text())))
    print(f"wrote {RESULTS_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
