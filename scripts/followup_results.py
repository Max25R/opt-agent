"""results/followup.json and docs/followup/RESULTS.md: the follow-up test run, written up as
section 4 of docs/FOLLOWUP_PREREGISTRATION.md specifies.

Every number comes from the run directory, runs/followup-test:
- **pre-registered** (section 4): copied from followup_report.json, which the frozen
  analysis (src/opt_agent/followup_report.py, by its hash in docs/followup/FREEZE.json)
  wrote. Nothing here recomputes a pre-registered number; the one exception is
  self-correction's revisions, which section 4 lists under "also reported" and the frozen
  report doesn't count, so they're counted here from results.jsonl;
- **descriptive** (not pre-registered; the result of record doesn't change): condition 4's
  changes by flag type, replies cut off at max_tokens and their share of the H2 difference,
  and loud failures by kind. Counted here from results.jsonl and attempts.jsonl.

The README's follow-up section and RESULTS.md take every number from results/followup.json
(tests/test_readme_numbers.py). RESULTS.md is rendered from that file alone, and
tests/test_followup_results.py checks that both are current.

Right and wrong need the keys, which load only on the follow-up's frozen inputs
(followup.load_test), so building needs the LLM4OR data; rendering RESULTS.md doesn't. No API
calls, no timestamps: the same inputs give the same bytes.

Run:  python scripts/followup_results.py            # build results/followup.json, render
      python scripts/followup_results.py --render   # RESULTS.md from the committed JSON
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "followup-test"
FREEZE = ROOT / "docs" / "followup" / "FREEZE.json"
OUT = ROOT / "results" / "followup.json"
RESULTS_MD = ROOT / "docs" / "followup" / "RESULTS.md"
CONDITIONS = ["baseline", "single-shot", "self-correction", "checklist-revision"]
NAMES = {
    "baseline": "no-solver baseline",
    "single-shot": "single-shot",
    "self-correction": "self-correction",
    "checklist-revision": "checklist revision",
}
ROWS = {"primary": "primary (unexposed)", "sensitivity": "sensitivity (all)"}
CUT_OFF = "the reply was cut off at 16000 tokens"  # api.UNFINISHED["max_tokens"]


# ---- building ---------------------------------------------------------------------------


def build(run: Path = RUN) -> dict:
    from opt_agent import followup  # needs the data and the freeze; rendering doesn't
    from opt_agent.evaluate import latest_items

    report_path = run / "followup_report.json"
    report = json.loads(report_path.read_text())
    items = latest_items(run / "results.jsonl")
    problems = {p.id: p for p in followup.load_test()}
    attempts = [json.loads(line) for line in (run / "attempts.jsonl").read_text().splitlines()]
    spend = [json.loads(line) for line in (run / "spend.jsonl").read_text().splitlines()]
    freeze = json.loads(FREEZE.read_text())
    exposed = set(report["exposed_left_out"])
    unexposed = {label for label in problems if label not in exposed}
    return {
        "provenance": provenance(run, report_path, freeze, items, spend, report),
        "pre_registered": pre_registered(report),
        "also_reported": also_reported(report, items, problems),
        "descriptive": descriptive(items, attempts, problems, unexposed, report),
    }


def provenance(run, report_path, freeze, items, spend, report) -> dict:
    manifest = json.loads((run / "manifest.json").read_text())
    return {
        "run": run.relative_to(ROOT).as_posix(),
        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "analysis_sha256": freeze["analysis_sha256"],
        "freeze_approved_on": freeze["approved_on"],
        "model": manifest["model_id"],
        "problems": len(manifest["problem_ids"]),
        "by_benchmark": dict(Counter(pid.split(":")[0] for pid in manifest["problem_ids"])),
        "unexposed_problems": report["rows"][ROWS["primary"]]["problems"],
        "exposed_problems": len(report["exposed_left_out"]),
        "samples": len(report["samples"]),
        "pairs": len(items),
        "errored_pairs": sum(i.outcome == "errored" for i in items),
        "unscorable_keys": report["unscorable_keys"]["n"],
        "paid_calls": len(spend),
        "paid_usd": round(sum(s["cost_usd"] for s in spend), 6),
    }


def pre_registered(report: dict) -> dict:
    """Section 4's numbers, as followup_report.json gives them, plus two derived forms a test
    can match: percentage-point copies of every difference ("+6.3 pp") and the majority's
    share of problems."""
    out = {}
    for key, name in ROWS.items():
        row = report["rows"][name]
        out[key] = {
            "problems": row["problems"],
            "accuracy": {
                c: a | {"majority_share": a["majority_right"] / a["problems"]}
                for c, a in row["accuracy"].items()
            },  # fmt: skip
            "primary": {h: with_pp(c) for h, c in row["primary"].items()},
            "exploratory": {n: with_pp(c) for n, c in row["exploratory"].items()},
        }
    # every interval is 95% (section 4; followup_report's 2.5th and 97.5th percentiles, and
    # stats.wilson's default)
    out["settings"] = report["settings"] | {"confidence": 0.95}
    return out


def with_pp(contrast: dict) -> dict:
    pp = {
        "score_difference_pp": 100 * contrast["score_difference"],
        "score_ci_pp": [100 * x for x in contrast["score_ci"]],
        "majority_difference_pp": 100 * contrast["majority_difference"],
        "majority_ci_pp": [100 * x for x in contrast["majority_ci"]],
    }
    return contrast | pp


def also_reported(report: dict, items, problems) -> dict:
    return {
        "sample_agreement": report["sample_agreement"],
        "checklist_revision": report["checklist_revision"],
        "self_correction": self_correction(items, problems),
        "unused_variable_drops": drops_with_totals(report["unused_variable_drops"]),
        "failures": report["failures"],
        "spend": report["spend"]
        | {c: report["spend"][c] | {"paid_usd": paid(items, c)} for c in CONDITIONS},  # fmt: skip
        "right_only_by_rounding": report["right_only_by_rounding"],
        "disputes": {
            "n": len(report["disputes"]),
            "problems": sorted(d["problem"] for d in report["disputes"]),
        },  # fmt: skip
    }


def drops_with_totals(drops: dict) -> dict:
    """The report's 2x2, with each row's total for the write-up."""
    totals = {f"{row}_answers": drops[row]["right"] + drops[row]["wrong"]
              for row in ("with_drop", "without_drop")}  # fmt: skip
    return drops | totals


def paid(items, condition: str) -> float:
    """What the condition actually paid: a reply it replayed from the cache cost nothing
    (conditions 2-4 share their first reply, paid by whichever ran first)."""
    return round(sum(i.paid_usd for i in items if i.condition == condition), 6)


def right(problem, status, objective) -> bool:
    from opt_agent import followup

    return followup.is_correct(problem, status, objective)


def self_correction(items, problems) -> dict:
    """Section 4's "self-correction's revisions": answers that took more than one attempt,
    against the single-shot answer of the same problem and sample (the same first reply)."""
    single = {(i.problem_id, i.sample): i for i in items if i.condition == "single-shot"}
    revised = [i for i in items if i.condition == "self-correction" and i.attempts > 1]
    moves = Counter()
    for i in revised:
        before = single[(i.problem_id, i.sample)]
        moves[_move(right(problems[i.problem_id], before.status, before.objective),
                    right(problems[i.problem_id], i.status, i.objective))] += 1  # fmt: skip
    return {"answers": sum(i.condition == "self-correction" for i in items),
            "revised": len(revised), "problems": sorted({i.problem_id for i in revised}),
            **{m: moves[m] for m in MOVES}}  # fmt: skip


MOVES = ["wrong_to_right", "right_to_wrong", "right_to_right", "wrong_to_wrong"]


def _move(before: bool, after: bool) -> str:
    return f"{'right' if before else 'wrong'}_to_{'right' if after else 'wrong'}"


# ---- descriptive, not pre-registered ----------------------------------------------------


def descriptive(items, attempts, problems, unexposed, report) -> dict:
    return {
        "label": "descriptive, not pre-registered: the result of record doesn't change",
        "revision_by_flag_kind": revision_by_flag_kind(items, problems),
        "cut_off_replies": cut_off_replies(attempts),
        "h2_and_cut_off_replies": h2_cut_off(items, problems, unexposed, report),
        "loud_failures_by_kind": loud_by_kind(items),
    }


def revision_by_flag_kind(items, problems) -> dict:
    """Condition 4's revised answers, by each flag kind among the flags that triggered them
    (an answer with several kinds counts under each), and in all."""
    out: dict[str, Counter] = {}
    for i in items:
        if i.condition != "checklist-revision" or not i.revised:
            continue
        p = problems[i.problem_id]
        move = _move(right(p, i.original_status, i.original_objective),
                     right(p, i.status, i.objective))  # fmt: skip
        for kind in ["all", *sorted({f["kind"] for f in i.checklist_flags})]:
            out.setdefault(kind, Counter({m: 0 for m in MOVES}))
            out[kind]["revised"] += 1
            out[kind][move] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


def cut_off_replies(attempts) -> dict:
    """Replies that stopped at max_tokens, per condition and kind of call. A reply replayed
    from the cache is logged in each condition that used it, and counted in each."""
    counts = {c: Counter() for c in CONDITIONS}
    replies = Counter()
    for a in attempts:
        if a.get("stop_reason") is None or a.get("condition") not in counts:
            continue
        replies[a["condition"]] += 1
        if a["stop_reason"] == "max_tokens":
            counts[a["condition"]][a["kind"]] += 1
    return {c: {"replies": replies[c], "cut_off": sum(counts[c].values()),
                "by_call": dict(sorted(counts[c].items()))} for c in CONDITIONS}  # fmt: skip


def h2_cut_off(items, problems, unexposed, report) -> dict:
    """How much of H2's score difference (single-shot minus baseline, the 121 unexposed
    problems) comes from sample pairs where a reply was cut off at max_tokens. The per-problem
    score difference is a sum over samples, so it splits exactly over the 3 sample pairs
    (baseline sample s, single-shot sample s) of each problem."""
    by = {(i.problem_id, i.condition, i.sample): i for i in items}
    parts = Counter()
    pairs = Counter()
    for label in unexposed:
        for s in range(3):
            base, single = by[(label, "baseline", s)], by[(label, "single-shot", s)]
            p = problems[label]
            d = (int(right(p, single.status, single.objective))
                 - int(right(p, base.status, base.objective)))  # fmt: skip
            cut = "cut_off" if CUT_OFF in (base.reason, single.reason) else "not_cut_off"
            parts[cut] += d
            pairs[cut] += 1
    n = len(unexposed) * 3
    total_pp = 100 * (parts["cut_off"] + parts["not_cut_off"]) / n
    h2 = report["rows"][ROWS["primary"]]["primary"]["H2"]
    assert abs(total_pp - 100 * h2["score_difference"]) < 1e-9, "the split must add up to H2"
    return {
        "problems": len(unexposed),
        "score_difference_pp": total_pp,
        "pairs_with_a_cut_off_reply": pairs["cut_off"],
        "from_pairs_with_a_cut_off_reply_pp": 100 * parts["cut_off"] / n,
        "from_other_pairs_pp": 100 * parts["not_cut_off"] / n,
        "share_from_cut_off": parts["cut_off"] / (parts["cut_off"] + parts["not_cut_off"]),
    }


def loud_by_kind(items) -> dict:
    """Loud failures (no answer) per condition, all 128 problems, by why."""
    out = {c: Counter() for c in CONDITIONS}
    for i in items:
        if i.status is None:
            why = "cut off at max_tokens" if i.reason == CUT_OFF else (i.no_answer or "other")
            out[i.condition][why] += 1
    return {c: dict(sorted(v.items())) for c, v in out.items()}


# ---- rendering --------------------------------------------------------------------------


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%"


def sci(x: float) -> str:
    """1e-4, as the pre-registration writes it (not Python's 1e-04)."""
    mantissa, exponent = f"{x:.0e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def pp(x: float, d: int = 1) -> str:
    return f"{x:+.{d}f} pp"


def p(x: float) -> str:
    return f"{x:.4f}" if x >= 0.0001 else f"{x:.1e}"


def ci_pp(ci: list[float]) -> str:
    return f"{ci[0]:.1f} to {ci[1]:.1f} pp"


def accuracy_table(rows: dict) -> list[str]:
    lines = ["| condition | mean score (95% bootstrap) | right by majority (95% Wilson) |",
             "|---|---|---|"]  # fmt: skip
    for c in CONDITIONS:
        a = rows["accuracy"][c]
        lo, hi = a["mean_score_ci"]
        wlo, whi = a["majority_wilson"]
        share = pct(a["majority_share"])
        lines.append(f"| {NAMES[c]} | {pct(a['mean_score'])} ({pct(lo)} to {pct(hi)}) | "
                     f"{a['majority_right']} of {a['problems']}, {share} "
                     f"({pct(wlo)} to {pct(whi)}) |")  # fmt: skip
    return lines


def contrast_table(primary: dict) -> list[str]:
    lines = ["| contrast | score difference (95% CI) | sign-flip p | Holm p | verdict |",
             "|---|---|---|---|---|"]  # fmt: skip
    titles = {"H1": "H1: checklist revision minus single-shot",
              "H2": "H2: single-shot minus baseline"}  # fmt: skip
    for h in ("H1", "H2"):
        c = primary[h]
        lines.append(f"| {titles[h]} | {pp(c['score_difference_pp'])} "
                     f"({ci_pp(c['score_ci_pp'])}) | {p(c['sign_flip_p'])} | "
                     f"{p(c['sign_flip_p_holm'])} | **{c['verdict']}** |")  # fmt: skip
    return lines


def mcnemar_table(primary: dict) -> list[str]:
    lines = ["| contrast | majority difference (95% CI) | only a / only b right | McNemar p "
             "| Holm p |", "|---|---|---|---|---|"]  # fmt: skip
    for h in ("H1", "H2"):
        c = primary[h]
        lines.append(f"| {h} | {pp(c['majority_difference_pp'])} ({ci_pp(c['majority_ci_pp'])}) | "
                     f"{c['majority_only_a']} / {c['majority_only_b']} | {p(c['mcnemar_p'])} | "
                     f"{p(c['mcnemar_p_holm'])} |")  # fmt: skip
    return lines


def verdict_text(h: str, c: dict, cut_off: dict | None = None) -> str:
    """The verdict as section 4 defines it. For a detected contrast, also the secondary
    test's result and, if given, how much of the difference comes from cut-off replies."""
    if c["verdict"] == "detected":
        text = (
            f"**{h}: {pp(c['score_difference_pp'], 2)}, detected on the primary sign-flip "
            f"test** (Holm p {p(c['sign_flip_p_holm'])}, 95% CI {ci_pp(c['score_ci_pp'])}). "
            "The secondary majority-vote McNemar test isn't significant (Holm p "
            f"{c['mcnemar_p_holm']:.2f}); it doesn't decide the claim."
        )
        if cut_off is not None:
            text += (
                f" Descriptively, {cut_off['from_pairs_with_a_cut_off_reply_pp']:.2f} pp of "
                f"the {cut_off['score_difference_pp']:.2f} comes from "
                f"{cut_off['pairs_with_a_cut_off_reply']} baseline replies cut off at "
                "max_tokens (see the descriptive section)."
            )
        return text
    bound = c.get("no_difference_larger_than_pp")
    return (
        f"**{h}: inconclusive.** {pp(c['score_difference_pp'])} (95% CI "
        f"{ci_pp(c['score_ci_pp'])}), Holm-adjusted p {p(c['sign_flip_p_holm'])}. Section 4 "
        f'allows "no difference larger than {bound} pp" and nothing stronger: {bound} is the '
        "smallest whole number of percentage points X with the 95% CI inside +/-X."
    )


def render(data: dict) -> str:
    v, pre = data["provenance"], data["pre_registered"]
    also, desc = data["also_reported"], data["descriptive"]
    prim, sens = pre["primary"], pre["sensitivity"]
    s = pre["settings"]
    out = [
        "# Follow-up results",
        "",
        "Generated by `scripts/followup_results.py` from `results/followup.json`; don't edit by",
        "hand. Every number here is in that file, and a test checks it.",
        "",
        "## The run",
        "",
        f"- **Run:** `{v['run']}`, on the frozen inputs (`docs/followup/FREEZE.json`, approved "
        f"{v['freeze_approved_on']}; the analysis is `followup_report.py` at SHA-256 "
        f"`{v['analysis_sha256'][:12]}`).",
        f"- **Problems:** {v['problems']} ({v['unexposed_problems']} unexposed, the primary set; "
        f"{v['exposed_problems']} seen before the split, in the sensitivity row only), "
        f"{v['samples']} samples each, 4 conditions: {v['pairs']} answers, "
        f"{v['errored_pairs']} errored. Keys left out as unparseable: {v['unscorable_keys']}.",
        f"- **Model:** `{v['model']}`. **Paid:** ${v['paid_usd']:.4f} on {v['paid_calls']} calls.",
        f"- **Benchmarks:** ComplexLP {v['by_benchmark']['complexlp']}, IndustryOR "
        f"{v['by_benchmark']['industryor']}.",
        f"- **Scoring:** status and objective against the key at {sci(s['tolerance'])} relative, "
        "or by rounding to a non-whole key's written decimals (section 4). Answers right only "
        "by rounding: "
        + ", ".join(
            f"{NAMES[c]} {also['right_only_by_rounding'][c]['answers']}" for c in CONDITIONS
        )
        + ".",  # fmt: skip
        "",
        "## Accuracy (primary: the unexposed problems)",
        "",
        f"Mean score is the mean over problems of the share of {v['samples']} samples right; "
        f"majority is right in at least 2 of {v['samples']}. n = {prim['problems']}.",
        "",
        *accuracy_table(prim),
        "",
        "## The pre-registered contrasts",
        "",
        "Primary test: exact paired sign-flip test on per-problem score differences, Holm over "
        "H1 and H2. A contrast is **detected** only if its Holm-adjusted p is below "
        f"{s['alpha']}; otherwise it is **inconclusive**, with its interval. 95% intervals by "
        f"paired bootstrap over problems ({s['bootstrap_resamples']} resamples, seed "
        f"{s['bootstrap_seed']}).",
        "",
        *contrast_table(prim["primary"]),
        "",
        verdict_text("H2", prim["primary"]["H2"], desc["h2_and_cut_off_replies"]),
        "",
        verdict_text("H1", prim["primary"]["H1"]),
        "",
        "**Secondary test** (exact McNemar on majority vote, Holm over H1 and H2; it doesn't "
        "decide the claims):",
        "",
        *mcnemar_table(prim["primary"]),
        "",
        f"## Sensitivity: all {sens['problems']} problems",
        "",
        "The same analysis with the problems seen before the split included.",
        "",
        *accuracy_table(sens),
        "",
        *contrast_table(sens["primary"]),
        "",
        "## Exploratory contrasts (no Holm, no claims)",
        "",
        "| contrast (b minus a) | score difference (95% CI) | sign-flip p | McNemar p |",
        "|---|---|---|---|",
        *[
            f"| {NAMES[c['b']]} minus {NAMES[c['a']]} | {pp(c['score_difference_pp'])} "
            f"({ci_pp(c['score_ci_pp'])}) | {p(c['sign_flip_p'])} | {p(c['mcnemar_p'])} |"
            for c in prim["exploratory"].values()
        ],  # fmt: skip
        "",
        "## Also reported (section 4)",
        "",
        *also_lines(also),
        "",
        "## Descriptive, not pre-registered",
        "",
        "These don't change the result of record.",
        "",
        *descriptive_lines(desc),
        "",
    ]
    return "\n".join(out)


def also_lines(also: dict) -> list[str]:
    cr, sc = also["checklist_revision"], also["self_correction"]
    drops = also["unused_variable_drops"]
    by_count = sorted(cr["flags_by_kind"].items(), key=lambda kv: -kv[1])
    flags = ", ".join(f"{k} {n}" for k, n in by_count)
    with_drop, without_drop = drops["with_drop_answers"], drops["without_drop_answers"]
    lines = [
        "- **Sample agreement** (share of sample pairs giving the same answer): "
        + ", ".join(f"{NAMES[c]} {pct(also['sample_agreement'][c])}" for c in CONDITIONS) + ".",
        f"- **Condition 4 (checklist revision)** triggered on {cr['revised']} of {cr['answers']} "
        f"answers; {cr['kept']} revisions kept, {cr['discarded']} discarded. Answers changed: "
        f"{cr['wrong_to_right']} wrong to right, {cr['right_to_wrong']} right to wrong. Flags by "
        f"type: {flags}.",
        f"- **Self-correction** revised {sc['revised']} of {sc['answers']} answers (on "
        f"{len(sc['problems'])} problems): {sc['wrong_to_right']} wrong to right, "
        f"{sc['right_to_wrong']} right to wrong, {sc['wrong_to_wrong']} still wrong.",
        f"- **Unused variables dropped (5a, exploratory):** answers with a drop were right "
        f"{drops['with_drop']['right']} of {with_drop}, "
        f"without {drops['without_drop']['right']} of {without_drop} (Fisher p "
        f"{p(drops['fisher_p'])}).",
        "- **Failures, silent / loud** (all 128 problems, sample answers): "
        + ", ".join(f"{NAMES[c]} {also['failures'][c]['silent']} / {also['failures'][c]['loud']}"
                    for c in CONDITIONS) + ".",  # fmt: skip
        "- **Latency p50 / p95, cost:** "
        + "; ".join(spend_text(c, also["spend"][c]) for c in CONDITIONS)
        + ". A condition's cost counts every reply it used; conditions 2 to 4 share each "
        "sample's first reply, which only the first of them to run paid for.",
        f"- **Keys not checked (5b):** {also['disputes']['n']} problems meet the dispute "
        "trigger: " + ", ".join(f"`{x}`" for x in also["disputes"]["problems"])
        + ". The pre-registered check of those keys wasn't performed "
        "([deviation 2](DEVIATIONS.md)), so the raw keys are the result of record, as "
        "pre-registered. Some of these failures may be key errors rather than errors by the "
        "conditions; that is unknown.",
    ]  # fmt: skip
    return lines


def spend_text(condition: str, s: dict) -> str:
    return (f"{NAMES[condition]} {s['latency_p50_s']:.1f} s / {s['latency_p95_s']:.1f} s, "
            f"${s['cost_usd']:.4f} (paid ${s['paid_usd']:.4f})")  # fmt: skip


def descriptive_lines(desc: dict) -> list[str]:
    by_kind = desc["revision_by_flag_kind"]
    lines = [
        "**Condition 4's revised answers by flag type** (an answer flagged with several types "
        "counts under each):",
        "",
        "| flag type | revised | wrong to right | right to wrong | stayed right | stayed wrong |",
        "|---|---|---|---|---|---|",
        *[f"| {k} | {v['revised']} | {v['wrong_to_right']} | {v['right_to_wrong']} | "
          f"{v['right_to_right']} | {v['wrong_to_wrong']} |" for k, v in by_kind.items()],
        "",
        "**Replies cut off at max_tokens**, per condition (a reply replayed from the cache is "
        "counted in each condition that used it):",
        "",
        "| condition | replies | cut off | of which |",
        "|---|---|---|---|",
        *[f"| {NAMES[c]} | {v['replies']} | {v['cut_off']} | "
          + (", ".join(f"{k} {n}" for k, n in v["by_call"].items()) or "-") + " |"
          for c, v in ((c, desc["cut_off_replies"][c]) for c in CONDITIONS)],
    ]  # fmt: skip
    h = desc["h2_and_cut_off_replies"]
    lines += [
        "",
        f"**H2 and cut-off replies.** Of H2's {pp(h['score_difference_pp'], 2)} on the "
        f"{h['problems']} unexposed problems, {pp(h['from_pairs_with_a_cut_off_reply_pp'], 2)} "
        f"comes from the {h['pairs_with_a_cut_off_reply']} sample pairs (baseline sample s, "
        f"single-shot sample s) in which a reply was cut off, and "
        f"{pp(h['from_other_pairs_pp'], 2)} from the rest: {pct(h['share_from_cut_off'])} of "
        "the difference. The per-problem difference is a sum over samples, so the split is "
        "exact; no test is recomputed.",
        "",
        "**Loud failures by kind** (all 128 problems): "
        + "; ".join(
            f"{NAMES[c]}: " + (", ".join(f"{k} {n}" for k, n in v.items()) or "none")
            for c, v in ((c, desc["loud_failures_by_kind"][c]) for c in CONDITIONS)
        )
        + ".",  # fmt: skip
    ]
    return lines


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The follow-up results file and write-up.")
    parser.add_argument("--render", action="store_true",
                        help="only render RESULTS.md from the committed JSON")  # fmt: skip
    args = parser.parse_args(argv)
    if not args.render:
        OUT.write_text(json.dumps(build(), indent=1, sort_keys=True) + "\n")
    RESULTS_MD.write_text(render(json.loads(OUT.read_text())))
    print(f"wrote {OUT.relative_to(ROOT)} and {RESULTS_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
