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

Run:  python -m opt_agent.data         # fetches the pinned benchmark (git-ignored)
      python -m opt_agent.external_check   # writes review/external_check.md and .csv
"""

import csv
import difflib
import math
from typing import Literal

from pydantic import BaseModel

from opt_agent import orlm
from opt_agent.data import DATA_DIR, ORLM_BENCHMARK, ORLM_BENCHMARK_REVISION
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    CheckedSolve,
    Record,
    load_records,
    readings,
    scorable,
)
from opt_agent.packets import REVIEW_DIR, kept_marks
from opt_agent.solver import Status

EXTERNAL_CHECK_PATH = REVIEW_DIR / "external_check.md"
DECISIONS_PATH = REVIEW_DIR / "external_check.csv"
UNCOVERED = "not cross-checked"  # a reviewed problem the benchmark doesn't have
# Why the owner decides a problem -> the decisions that settle it.
DECISIONS = {
    "disagrees": ("keep", "change"),
    "other integrality": ("keep", "change"),
    "edited text": ("keep", "change"),
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


def main() -> None:
    records = load_records(GROUND_TRUTH_DIR / "test.json")
    answers = orlm.load_answers(DATA_DIR / ORLM_BENCHMARK.path)
    matches, unmatched = match(records, answers)
    EXTERNAL_CHECK_PATH.write_text(render(records, matches, unmatched))
    decision_sheet(to_decide(records, matches), DECISIONS_PATH)
    print(f"wrote {EXTERNAL_CHECK_PATH} and {DECISIONS_PATH.name} ({len(matches)} matched, "
          f"{len(unmatched)} unmatched)")  # fmt: skip


if __name__ == "__main__":
    main()
