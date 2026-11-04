"""The external cross-check of the test answers (pre-registration, Amendment 2).

Our answers come from NL4Opt's annotations, solved by CBC and checked by HiGHS and
arithmetic, and every hand review of them was written by Claude. Instead of the owner
confirming each review, the answers are compared with an answer set made outside this
repository: the corrected NL4OPT in ORLMBenchmark (data.ORLM_BENCHMARK), 245 of NL4Opt's
test problems with optimal values, reviewed and corrected by the SIRL paper's authors.

Problems are matched by normalized text (orlm.normalize). Where the benchmark edited the
text itself, the closest of our problems is matched if its words are at least EDITED_RATIO
alike, and the edits are listed: an edit means the benchmark's authors found the original
text wrong, so those problems go to the owner whatever the answers say.

Each matched problem gets one verdict, against the answers scoring accepts
(ground_truth.readings), at orlm.MATCH_TOLERANCE, since published values are rounded:
- "agrees": the benchmark's value is our answer.
- "agrees with another reading": it's the strict or "=" reading's answer, which scoring
  accepts as well.
- "other integrality": it's our optimum with the other integrality, so the label is in
  question.
- "disagrees": none of these.
"No Best Solution" agrees with an infeasible or unbounded answer; the benchmark doesn't
say which.

Agreement isn't independent proof. The benchmark descends from the same problems, and
possibly through ORLM's answers from the same annotations, so an error both inherit gets
through. A disagreement is the informative signal, and the owner sees every one.

The owner decides every problem the list names (Amendment 2), in external_check.csv: for
a disagreement, a label question or an edited text, `keep` (our answer stands) or `change`
(made in reviews.json or integrality.json); for a reviewed problem the benchmark doesn't
have, `confirmed` or `disputed`, as for the owner's review packet. The sheet is committed,
so the freeze can check it without the benchmark, which isn't committed.

The reviews the benchmark can't cover, and the two problems its rules can't settle
(HARD_CASES), go to both LLM judges instead of the owner (Amendment 2): one prompt, a
sheet per judge, each judgment `agree`, `disagree` or `unsure` on the review's claim.
Both agreeing confirms a review; anything else disputes it (review_outcomes).

Run:  python -m opt_agent.data         # fetches the pinned benchmark (git-ignored)
      python -m opt_agent.external_check   # writes review/external_check.md and .csv
      python -m opt_agent.external_check judges   # writes review/review_judge/
      python -m opt_agent.external_check judges --merge judge --reply R.csv --grader "MODEL"
"""

import argparse
import csv
import difflib
import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from opt_agent import orlm
from opt_agent.agent import format_model
from opt_agent.data import DATA_DIR, ORLM_BENCHMARK, ORLM_BENCHMARK_REVISION
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    CheckedSolve,
    Record,
    load_records,
    readings,
    reference_model,
    scorable,
)
from opt_agent.packets import JUDGE_SHEETS, REVIEW_DIR, kept_marks, merge_reply
from opt_agent.solver import Status

EXTERNAL_CHECK_PATH = REVIEW_DIR / "external_check.md"
DECISIONS_PATH = REVIEW_DIR / "external_check.csv"
UNCOVERED = "not cross-checked"  # a reviewed problem the benchmark doesn't have
# Why the owner decides a problem -> the decisions that settle it.
DECISIONS = {
    "disagrees": ("keep", "change", "exclude"),
    "other integrality": ("keep", "change"),
    "edited text": ("keep", "change", "exclude"),
    UNCOVERED: ("confirmed", "disputed"),
}
EDITED_RATIO = 0.9  # word-level SequenceMatcher ratio; a one-word edit scores about 0.99

Verdict = Literal["agrees", "agrees with another reading", "other integrality", "disagrees"]


class Match(BaseModel):
    problem_id: str
    answer: str  # the benchmark's, as published
    edits: list[str] = []  # where its text differs from ours; empty for the same text


def match(records: list[Record], answers: dict[str, str]) -> tuple[list[Match], list[str]]:
    """Benchmark problems matched to ours, and the benchmark's texts that match none.
    `answers` is normalized text -> answer (orlm.load_answers)."""
    by_text = {orlm.normalize(r.document): r for r in records}
    found: dict[str, Match] = {}
    unmatched = []
    for text, answer in answers.items():
        if text in by_text:
            found[by_text[text].id] = Match(problem_id=by_text[text].id, answer=answer)
            continue
        ours = max(by_text, key=lambda t: _alike(t, text))
        problem_id = by_text[ours].id
        if _alike(ours, text) < EDITED_RATIO or problem_id in found:
            unmatched.append(text)
            continue
        found[problem_id] = Match(problem_id=problem_id, answer=answer, edits=edits(ours, text))
    return list(found.values()), unmatched


def _alike(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.split(), b.split(), autojunk=False).ratio()


def edits(ours: str, theirs: str) -> list[str]:
    """The benchmark's word-level changes to our text, e.g. "'least' -> 'most'"."""
    a, b = ours.split(), theirs.split()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [f"{' '.join(a[i1:i2])!r} -> {' '.join(b[j1:j2])!r}"
            for op, i1, i2, j1, j2 in matcher.get_opcodes() if op != "equal"]  # fmt: skip


def verdict(record: Record, answer: str) -> Verdict:
    """How the benchmark's answer relates to the answers scoring accepts for `record`."""
    value = _value(answer)
    for reading, solve in readings(record):
        if _same(solve, value):
            return "agrees" if reading == "annotated" else "agrees with another reading"
    other = {"integer": record.lp, "continuous": record.ip}.get(record.integrality.kind)
    if other is not None and _same(other, value):  # an `either` label has no other
        return "other integrality"
    return "disagrees"


def _value(answer: str) -> float | None:
    """None for "no optimum"; anything else must be a number, or the data has changed."""
    if answer.strip().lower() in orlm.NO_SOLUTION_MARKERS:
        return None
    return float(answer)


def _same(solve: CheckedSolve, value: float | None) -> bool:
    if value is None:
        return solve.status is not Status.OPTIMAL
    return solve.status is Status.OPTIMAL and math.isclose(
        value, solve.objective, rel_tol=orlm.MATCH_TOLERANCE, abs_tol=orlm.MATCH_TOLERANCE
    )


# ---- the owner's list -----------------------------------------------------------------


def to_decide(records: list[Record], matches: list[Match]) -> dict[str, list[str]]:
    """Why -> the problems the owner decides for that reason (Amendment 2), in file order.
    An edited text is listed as such, whatever its verdict."""
    matched = {m.problem_id: m for m in matches}
    found = {why: [] for why in DECISIONS}
    for r in records:
        m = matched.get(r.id)
        if m is None:
            if r.review is not None:
                found[UNCOVERED].append(r.id)
        elif m.edits:
            found["edited text"].append(r.id)
        elif scorable(r) and (v := verdict(r, m.answer)) in ("disagrees", "other integrality"):
            found[v].append(r.id)
    return found


def render(records: list[Record], matches: list[Match], unmatched: list[str]) -> str:
    by_id = {r.id: r for r in records}
    matched = {m.problem_id: m for m in matches}
    scored = [r for r in records if scorable(r)]
    verdicts = {r.id: verdict(r, matched[r.id].answer) for r in scored if r.id in matched}
    decide = to_decide(records, matches)
    missing = [r for r in scored if r.id not in matched]
    lines = [
        "# External cross-check of the test answers",
        "",
        "Generated by `python -m opt_agent.external_check` (pre-registration, Amendment 2). "
        "Source: the corrected NL4OPT in ORLMBenchmark (`chenyitian-shanshu/ORLMBenchmark`, "
        f"`NL4OPT.jsonl`, revision `{ORLM_BENCHMARK_REVISION[:7]}`, Apache-2.0), from the "
        "authors of the SIRL paper (arXiv 2505.11792). Values are compared at "
        f"{orlm.MATCH_TOLERANCE:g} relative, since published values are rounded. "
        "Agreement isn't independent proof (both sides descend from the same problems); "
        "disagreements are the signal, and every one is listed below.",
        "",
        f"- Test problems: {len(records)}; the benchmark has {len(matches) + len(unmatched)}.",
        f"- Matched: {sum(not m.edits for m in matches)} with the same text, "
        f"{sum(bool(m.edits) for m in matches)} with an edited text.",
        *(f'- Matches none of ours: "{" ".join(t.split()[:12])} ..."' for t in unmatched),
        "",
        f"Scorable test problems ({len(scored)}):",
        "",
        "| verdict | problems | of them reviewed |",
        "|---|---|---|",
    ]
    for kind in ("agrees", "agrees with another reading", "other integrality", "disagrees"):
        ids = [i for i, v in verdicts.items() if v == kind]
        lines.append(f"| {kind} | {len(ids)} | {sum(by_id[i].review is not None for i in ids)} |")
    lines += [
        f"| not in the benchmark | {len(missing)} | {sum(r.review is not None for r in missing)} |",
        "",
        "Problems with an edited text are counted above but listed in their own section.",
        "",
    ]
    lines += _section("Disagrees: neither our answer nor another accepted one",
                      decide["disagrees"], by_id, matched)  # fmt: skip
    lines += _section("Other integrality: the benchmark has our optimum with the other "
                      "integrality, so the label is in question",
                      decide["other integrality"], by_id, matched)  # fmt: skip
    lines += _section("The benchmark edited the text: its authors found ours wrong",
                      decide["edited text"], by_id, matched, show_edits=True)  # fmt: skip
    other = [i for i, v in verdicts.items()
             if v == "agrees with another reading" and not matched[i].edits]  # fmt: skip
    lines += ["## Agrees with another accepted reading (no action)", ""]
    lines += [", ".join(f"`{i}`" for i in other) or "None.", ""]
    lines += _not_scorable(records, matched)
    lines += _uncovered(decide[UNCOVERED], by_id)
    return "\n".join(lines)


def _not_scorable(records: list[Record], matched: dict[str, Match]) -> list[str]:
    """Reviewed problems kept out of scoring. Most are annotation errors, where the benchmark
    should differ from the annotated answer; a benchmark that has it questions the review."""
    rows = [r for r in records if r.review and not scorable(r) and r.id in matched]
    lines = [f"## Reviewed and not scorable, in the benchmark ({len(rows)})", ""]
    lines += ["| id | review | as annotated (LP / IP) | benchmark | the annotated answer |",
              "|---|---|---|---|---|"]  # fmt: skip
    for r in rows:
        answer = matched[r.id].answer
        same = any(s is not None and _same(s, _value(answer)) for s in (r.lp, r.ip))
        review = r.review.verdict + (" (excluded)" if r.excluded else "")
        lines.append(f"| `{r.id}` | {review} | {_show(r.lp)} / {_show(r.ip)} | "
                     f"{answer} | {_sameness(r, same)} |")  # fmt: skip
    return [*lines, ""]


def _section(
    title: str,
    ids: list[str],
    by_id: dict[str, Record],
    matched: dict[str, Match],
    show_edits: bool = False,
) -> list[str]:
    lines = [f"## {title} ({len(ids)})", ""]
    if not ids:
        return [*lines, "None.", ""]
    header = ["id", "review", "accepted answers", "as annotated (LP / IP)", "benchmark"]
    if show_edits:
        header += ["verdict", "edits"]
    lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for i in ids:
        r, m = by_id[i], matched[i]
        cells = [f"`{i}`", r.review.verdict if r.review else "", _accepted(r),
                 f"{_show(r.lp)} / {_show(r.ip)}", m.answer]  # fmt: skip
        if show_edits:
            cells += [verdict(r, m.answer) if scorable(r) else "not scorable", "; ".join(m.edits)]
        lines.append("| " + " | ".join(cells) + " |")
    return [*lines, ""]


def _sameness(r: Record, same: bool) -> str:
    """The benchmark having an annotated answer questions only an annotation-error review."""
    if not same:
        return "differs"
    return (
        "**the same** (questions the review)"
        if r.review.verdict == "annotation-error"
        else ("the same")
    )


def _uncovered(ids: list[str], by_id: dict[str, Record]) -> list[str]:
    """Reviewed problems the cross-check says nothing about: the owner still has to."""
    lines = [f"## Reviewed, but not in the benchmark ({len(ids)}): not cross-checked", ""]
    lines += ["| id | review | scorable |", "|---|---|---|"]
    for i in ids:
        r = by_id[i]
        lines.append(f"| `{i}` | {r.review.verdict} | {'yes' if scorable(r) else 'no'} |")
    return [*lines, ""]


def decision_sheet(decide: dict[str, list[str]], path) -> None:
    """One row per problem to decide; a regenerated sheet keeps the owner's decisions."""
    kept = kept_marks(path, "problem_id", ["decision", "note"])
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["problem_id", "why", "decision", "note"])
        for why, ids in decide.items():
            for i in ids:
                mark = kept.get(i, {"decision": "", "note": ""})
                writer.writerow([i, why, mark["decision"], mark["note"]])


def read_decisions(path) -> list[dict[str, str]]:
    """The sheet's rows; a decision must be one its reason allows, or blank (undecided)."""
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        decision = row["decision"].strip().lower()
        if decision and decision not in DECISIONS[row["why"]]:
            raise ValueError(f"{row['problem_id']} ({row['why']}): {decision!r} is none of "
                             f"{', '.join(DECISIONS[row['why']])}")  # fmt: skip
        row["decision"] = decision
    return rows


def _accepted(r: Record) -> str:
    return "; ".join(f"{_show(s)} ({reading})" for reading, s in readings(r)) or "none trusted"


def _show(s: CheckedSolve | None) -> str:
    if s is None:
        return "-"
    return f"{s.objective:.10g}" if s.status is Status.OPTIMAL else s.status.value


# ---- the judges' verdicts on the reviews it leaves (Amendment 2) ----------------------

REVIEW_JUDGE_DIR = REVIEW_DIR / "review_judge"
JUDGMENTS = ("agree", "disagree", "unsure")
# The two problems the list's rules can't settle (owner, 2026-11-04): an edited text the
# benchmark answers differently, and a disagreement on an ambiguous-text problem. Listed by
# id, like packets.SAYS_LP.
HARD_CASES = ["1283305022", "-1715698555"]
# What each review verdict claims, in words a judge can check against the text.
CLAIMS = {
    "text-has-no-optimum": "As written, the problem has no optimal solution: no choice meets "
    "every requirement, or the objective can improve without limit. That status is the "
    "right answer.",
    "degenerate-text": "As written, nothing has to be made, so making nothing (objective 0) "
    "is optimal. That's the right answer, if a trivial one.",
    "annotation-error": "The annotated model doesn't say what the text says.",
    "ambiguous-text": "The text supports more than one reading of one constraint, and each "
    "reading's answer below is right.",
    "orlm-error": "The annotated answer is right.",
    "ok": "The problem looked suspicious, but the annotated answer is right.",
}
NO_REVIEW = "The annotated model says what the text says, so its answer is right."
# Words of a review's reason the prompt leaves out, because they say what an outside answer
# key found (owner, 2026-11-04). reviews.json keeps them.
REDACTED = {"-1715698555": "; ORLM found no solution"}


def judged_reviews(records: list[Record], decisions: Path = DECISIONS_PATH) -> list[Record]:
    """The reviewed problems the benchmark doesn't have, in the sheet's order, then the
    hard cases. Read from the committed sheet, since the benchmark isn't committed."""
    by_id = {r.id: r for r in records}
    uncovered = [row["problem_id"] for row in read_decisions(decisions) if row["why"] == UNCOVERED]
    return [by_id[i] for i in uncovered + HARD_CASES]


def review_prompt(records: list[Record]) -> str:
    """For an LLM judge in a new conversation. It doesn't name the system or who wrote the
    reviews, or say what the benchmark answered."""
    lines = [
        "# Is each review right?",
        "",
        f"Below are {len(records)} optimization word problems from a dataset. Each comes with "
        "the dataset's annotation (the reference model, with whole-number or fractional "
        "variables as the problem's label says), the answer that model gives, and a "
        "reviewer's claim about the problem, with the reviewer's reason. Decide whether the "
        "claim is right for the text as written, and answer:",
        "",
        "- `agree`: the claim is right.",
        "- `disagree`: it's wrong; say what's wrong in the reason.",
        "- `unsure`: you can't tell from the text.",
        "",
        "Judge against the text, not the annotation: the annotation can be wrong.",
        "",
        "Reply with CSV only, and no other text: the header `number,problem_id,judgment,reason`, "
        "then one row per problem, with its number and problem id exactly as given, a "
        "judgment, and a one-sentence reason in double quotes.",
        "",
    ]
    for number, r in enumerate(records, 1):
        claim = CLAIMS[r.review.verdict] if r.review else NO_REVIEW
        reason = _shown_reason(r) if r.review else "(no review: this is the annotation's claim)"
        lines += [f"## {number}. `{r.id}`", "", f"> {r.document}", "",
                  f"Reference model (label: {r.integrality.kind}):", "```",
                  *format_model(reference_model(r)), "```", "",
                  f"**Its answer:** {_answers(r)}  ", f"**The claim:** {claim}  ",
                  f"**The reviewer's reason:** {reason}", ""]  # fmt: skip
    return "\n".join(lines)


def _shown_reason(r: Record) -> str:
    """The review's reason, less any REDACTED words. A redaction that no longer matches is an
    error, so a changed review can't slip an answer key's verdict back in."""
    cut = REDACTED.get(r.id)
    if cut is None:
        return r.review.reason
    if cut not in r.review.reason:
        raise ValueError(f"{r.id}: the review no longer says {cut!r}; update REDACTED")
    return r.review.reason.replace(cut, "")


def _answers(r: Record) -> str:
    """The answers scoring accepts, with any second reading said in words."""
    found = [_show(s) + _how(r, reading) for reading, s in readings(r)]
    if found:
        return "; ".join(found)
    return f"{_show(r.lp)} with fractions, {_show(r.ip)} with whole numbers (not scored)"


def _how(r: Record, reading: str) -> str:
    if reading == "annotated":
        return ""
    return f" ({reading} reading: {'; '.join(getattr(r, reading).changed)})"


def review_sheet(records: list[Record], path: Path) -> None:
    kept = kept_marks(path, "problem_id", ["judgment", "reason", "grader"])
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "problem_id", "review", "judgment", "reason", "grader"])
        for number, r in enumerate(records, 1):
            mark = kept.get(r.id, dict.fromkeys(["judgment", "reason", "grader"], ""))
            writer.writerow([number, r.id, r.review.verdict if r.review else "none",
                             mark["judgment"], mark["reason"], mark["grader"]])  # fmt: skip


def read_judgments(path: Path) -> dict[str, str]:
    """problem id -> the judge's judgment. Every row must be filled in."""
    judgments = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            judgment = row["judgment"].strip().lower()
            if judgment not in JUDGMENTS:
                raise ValueError(f"problem {row['number']}: {judgment!r} is none of "
                                 f"{', '.join(JUDGMENTS)}")  # fmt: skip
            judgments[row["problem_id"]] = judgment
    return judgments


def review_outcomes(judge: dict[str, str], second: dict[str, str]) -> dict[str, str]:
    """Confirmed where both judges agree with the claim; disputed otherwise, so one
    judge's doubt is enough (Amendment 2)."""
    return {pid: "confirmed" if (j, second.get(pid)) == ("agree", "agree") else "disputed"
            for pid, j in judge.items()}  # fmt: skip


def write_review_packet(records: list[Record]) -> int:
    judged = judged_reviews(records)
    REVIEW_JUDGE_DIR.mkdir(parents=True, exist_ok=True)
    (REVIEW_JUDGE_DIR / "LLM_PROMPT.md").write_text(review_prompt(judged))
    for name in JUDGE_SHEETS.values():
        review_sheet(judged, REVIEW_JUDGE_DIR / name)
    return len(judged)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The external cross-check of test answers.")
    parser.add_argument("what", nargs="?", choices=["list", "judges"], default="list")
    parser.add_argument(
        "--merge", choices=list(JUDGE_SHEETS), help="judges: write a judge's reply into its sheet"
    )
    parser.add_argument("--reply", type=Path, help="with --merge: the reply, as a CSV file")
    parser.add_argument("--grader", help="with --merge: the judge's model and version")
    args = parser.parse_args(argv)
    records = load_records(GROUND_TRUTH_DIR / "test.json")
    if args.what == "judges" and args.merge:
        if not (args.reply and args.grader):
            parser.error("--merge needs --reply and --grader")
        sheet = REVIEW_JUDGE_DIR / JUDGE_SHEETS[args.merge]
        n = merge_reply(sheet, args.reply, ["judgment", "reason"], args.grader)
        print(f"merged {n} judgments from {args.reply} into {sheet}")
    elif args.what == "judges":
        n = write_review_packet(records)
        print(f"wrote {REVIEW_JUDGE_DIR}/LLM_PROMPT.md, judge.csv and second_judge.csv "
              f"({n} problems)")  # fmt: skip
    else:
        answers = orlm.load_answers(DATA_DIR / ORLM_BENCHMARK.path)
        matches, unmatched = match(records, answers)
        EXTERNAL_CHECK_PATH.write_text(render(records, matches, unmatched))
        decision_sheet(to_decide(records, matches), DECISIONS_PATH)
        print(f"wrote {EXTERNAL_CHECK_PATH} and {DECISIONS_PATH.name} ({len(matches)} "
              f"matched, {len(unmatched)} unmatched)")  # fmt: skip


if __name__ == "__main__":
    main()
