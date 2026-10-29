"""The perturbed-numbers set (pre-registration, section 2, condition 4): the same problems
with their numbers changed, and the ground truth recomputed from the changed annotations by
the same code as the original (nl4opt.convert, ground_truth.build_record). A system that
reads the text reaches the new answer. One that recalls NL4Opt's reaches the old answer,
which is wrong here by construction. The rule was fixed on the dev split.

**Which numbers.** Every annotated number (a PARAM or LIMIT span) written in digits:
"8000", "$1,500", "35%". Words ("twice", "a third") stay as they are, and so does 1, the one
number English agreement depends on ("1 hour", "2 hours"); no number becomes 1 either.
NL4Opt copies each
number in a declaration verbatim from a span (all 2,806 in dev and test are), but doesn't
say which span, so a number's text is the key: every span with that text changes the same
way, and so does every declaration string equal to it. Different texts with one value
("10 workers", "10%") are different quantities in every case in the data, so they change
independently.

**How.** Each number is multiplied by a factor drawn log-uniformly from [1/2, 2], then
rounded to the original's precision: no more significant digits, and the same decimal
places. So 8000 becomes another round number such as 6000, and 1.5 keeps one decimal. New
numbers look like the old ones, which matters for the no-solver baseline: uglier numbers
would make its arithmetic harder for reasons that have nothing to do with memory. A
percentage stays below 100, and no two numbers get the same new text, so the change can be
undone exactly (a test does).

**Which draws are kept** (`rejection`): the perturbed problem must be the same kind of
problem with a new answer. It converts with the same judgment calls (notes), every solve
checks out, it still has an optimum that does something, integrality changes the answer
exactly where it did before, and no answer accepted for the original (any reading, either
integrality) is accepted for it, even at the looser 1e-4 tolerance. Otherwise the next draw
is tried, up to MAX_DRAWS. Each problem has its own random stream, seeded by SEED, the
split and the problem id, so one problem's draws never shift another's.

Integrality is kept for two reasons. Uglier ratios make the LP and IP optima differ more
often (in a trial build without this check, 58 of 242 perturbed test problems newly
depended on it), and there the integrality label picks the answer. On the original
problems, every label that picks an answer is a hand label; a newly sensitive problem would
let the unreviewed rule pick it. And a problem that gains or loses that difficulty isn't
the same test: an accuracy change could come from integrality, not memory.

**Which problems** (`ineligible`): scorable ones with no known annotation error (an error
that leaves today's answer alone could change the new one), whose answer is an optimum that
does something. A problem whose answer is a status ("infeasible") can't test memory: the
same status would still be right.

Run:  python -m opt_agent.perturb
Writes data/nl4opt/ground_truth/{dev,test}-perturbed.json and PERTURBED.md. Needs the raw
annotations (python -m opt_agent.data). A perturbed split keeps the original problem ids,
so a run on it pairs with a run on the original by id (report.py).
"""

import json
import math
import random
import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pydantic import BaseModel

from opt_agent.data import fetch
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    SENSITIVITY_TOLERANCE,
    SPLITS,
    CheckedSolve,
    Record,
    answer,
    attach_review,
    blind_gradable,
    build_record,
    does_nothing,
    integrality_matters,
    load_records,
    readings,
    same_value,
    scorable,
    trusted,
    write_records,
)
from opt_agent.nl4opt import load_split
from opt_agent.solver import Status

SEED = 20261028
FACTOR = (0.5, 2.0)  # each number is scaled by a log-uniform draw from this range
MAX_DRAWS = 200  # set on dev, where the most any problem needed was 107
PERTURBED_SPLITS = {f"{split}-perturbed": split for split in SPLITS}  # -> the original split
NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")  # "8000", "1,500", "0.25"
NUMBER_LABELS = {"PARAM", "LIMIT"}  # the spans that hold a problem's numbers


class Perturbation(BaseModel):
    seed: int
    draw: int  # which draw was kept, counting from 1
    changes: dict[str, str]  # each number's text -> its new text, e.g. "$1,500" -> "$1,800"


class PerturbedRecord(Record):
    """A ground-truth record for the perturbed problem, and how it was made.
    ground_truth.load_records reads it as a plain Record."""

    perturbation: Perturbation


# ---- the rule ---------------------------------------------------------------------------


def number_texts(annotation: dict) -> list[str]:
    """The distinct texts of the annotated numbers written in digits, in reading order,
    except 1: "1 hour" can't become "2 hour", nor "2 hours" become "1 hours"."""
    texts = []
    for span in _number_spans(annotation):
        text = _text(annotation, span)
        match = NUMBER.search(text)
        if match and _value(match.group()) != 1 and text not in texts:
            texts.append(text)
    return texts


def draw_changes(annotation: dict, rng: random.Random) -> dict[str, str]:
    """One draw: a new text for every number, no two alike. A draw with two alike is drawn
    again as a whole: redrawing just one number can get stuck ("2" can only become "3" or
    "4", and other numbers may have taken both)."""
    texts = number_texts(annotation)
    for _ in range(1000):
        changes = {t: new_number(t, rng, is_percent(annotation, t)) for t in texts}
        if len(set(changes.values())) == len(changes):
            return changes
    raise ValueError(f"no draw gives each of {texts} a new text of its own")


def new_number(text: str, rng: random.Random, percent: bool = False) -> str:
    """`text` with its number scaled by a random factor and rounded to the same precision.
    Never the same number, never 1 (see number_texts), still within FACTOR of it after
    rounding, and a percentage below 100 stays below 100."""
    [match] = NUMBER.finditer(text)  # one number per span: true of every NL4Opt span
    written = match.group()
    old = _value(written)
    places = max(0, -old.as_tuple().exponent)
    digits = len(old.normalize().as_tuple().digits)
    low, high = (math.log(f) for f in FACTOR)
    for _ in range(1000):  # "2" becomes "3" or "4" in about 1 draw in 3, the hardest case
        new = _round(old * Decimal(math.exp(rng.uniform(low, high))), digits, places)
        in_range = FACTOR[0] <= new / old <= FACTOR[1]  # rounding can push it out: 16000 -> 20000
        if new not in (old, 1) and in_range and not (percent and old < 100 <= new):
            commas = "," if "," in written else ""
            return f"{text[: match.start()]}{new:{commas}.{places}f}{text[match.end() :]}"
    raise ValueError(f"can't find a new number for {text!r}")  # 0, say: none in NL4Opt


def _value(written: str) -> Decimal:
    return Decimal(written.replace(",", ""))


def _round(x: Decimal, digits: int, places: int) -> Decimal:
    """x with at most `digits` significant digits and at most `places` decimal places."""
    exponent = max(x.adjusted() - digits + 1, -places)
    return x.quantize(Decimal(1).scaleb(exponent), rounding=ROUND_HALF_UP)


def is_percent(annotation: dict, text: str) -> bool:
    """Is a span with this text a percentage ("35%", or "35" followed by "percent")?"""
    document = annotation["document"]
    for span in _number_spans(annotation):
        if _text(annotation, span) == text:
            after = document[span["end"] :].lstrip().lower()
            if "%" in text or "percent" in text.lower() or after.startswith(("%", "percent")):
                return True
    return False


def apply(annotation: dict, changes: dict[str, str]) -> dict:
    """The annotation with every number span whose text is in `changes` rewritten, and
    every declaration string equal to one likewise. Spans after a rewrite move with it."""
    document = annotation["document"]
    rewritten = [(s["start"], s["end"], changes[_text(annotation, s)])
                 for s in _number_spans(annotation) if _text(annotation, s) in changes]  # fmt: skip
    parts, cursor = [], 0
    for start, end, new in rewritten:
        parts += [document[cursor:start], new]
        cursor = end
    new_document = "".join(parts) + document[cursor:]

    def moved(position: int) -> int:
        return position + sum(len(new) - (end - start)
                              for start, end, new in rewritten if end <= position)  # fmt: skip

    spans = []
    for span in annotation["spans"]:
        span = {**span, "start": moved(span["start"]), "end": moved(span["end"])}
        if "text" in span and span["label"] in NUMBER_LABELS:
            span["text"] = changes.get(span["text"], span["text"])
        spans.append(span)
    perturbed = {
        **annotation,
        "document": new_document,
        "spans": spans,
        "params": [changes.get(p, p) for p in annotation.get("params", [])],
        "obj_declaration": _rewrite(annotation["obj_declaration"], changes),
        "const_declarations": [_rewrite(d, changes) for d in annotation["const_declarations"]],
    }
    perturbed.pop("tokens", None)  # their offsets would be stale, and nothing reads them
    return perturbed


def _rewrite(declaration: dict, changes: dict[str, str]) -> dict:
    """A declaration's numbers are verbatim span texts, so they change by lookup."""
    d = dict(declaration)
    for field in ("limit", "param"):
        if field in d:
            d[field] = changes.get(d[field], d[field])
    if "terms" in d:
        d["terms"] = {mention: changes.get(v, v) for mention, v in d["terms"].items()}
    return d


def _number_spans(annotation: dict) -> list[dict]:
    spans = [s for s in annotation["spans"] if s["label"] in NUMBER_LABELS]
    return sorted(spans, key=lambda s: s["start"])


def _text(annotation: dict, span: dict) -> str:
    return annotation["document"][span["start"] : span["end"]]  # some spans lack "text"


# ---- which problems, and which draws ----------------------------------------------------


def ineligible(original: Record, annotation: dict) -> str | None:
    """Why the problem can't be perturbed, or None."""
    if not scorable(original):
        return "not scorable"
    if not blind_gradable(original):
        return "a known annotation error"
    if answer(original).status is not Status.OPTIMAL:
        return "no optimum as written"
    if does_nothing(original):
        return "does nothing as written"
    if not number_texts(annotation):
        return "no number written in digits"
    return None


def rejection(original: Record, candidate: Record) -> str | None:
    """Why `candidate` isn't the same kind of problem as `original` with a new answer, or
    None if it is."""
    if candidate.error is not None:
        return "doesn't convert"
    if [n.kind for n in candidate.notes] != [n.kind for n in original.notes]:
        return "different judgment calls"
    if not all(trusted(s) for s in _solves(candidate)):
        return "a solve doesn't check out"
    if answer(candidate).status is not Status.OPTIMAL:
        return "no optimum"
    if does_nothing(candidate):
        return "does nothing"
    if integrality_matters(candidate) != integrality_matters(original):
        return "integrality matters differently"
    old, new = readings(original, lenient=True), readings(candidate, lenient=True)
    if any(_same(a, b) for _, a in old for _, b in new):
        return "an original answer would still be right"
    return None


def _solves(record: Record) -> list[CheckedSolve]:
    solves = [record.lp, record.ip]
    if record.strict is not None:
        solves.append(record.strict.ip)
    if record.equality is not None:
        solves += [record.equality.lp, record.equality.ip]
    return solves


def _same(a: CheckedSolve, b: CheckedSolve) -> bool:
    """Would one answer be right for both? At the looser tolerance, to be safe."""
    return a.status is b.status and (
        a.status is not Status.OPTIMAL
        or same_value(a.objective, b.objective, SENSITIVITY_TOLERANCE)
    )


def perturb(split: str, original: Record, annotation: dict) -> PerturbedRecord | str:
    """The first draw that passes `rejection`, or why none did."""
    rng = random.Random(f"{SEED}:{split}:{original.id}")
    rejected: Counter[str] = Counter()
    for draw in range(1, MAX_DRAWS + 1):
        changes = draw_changes(annotation, rng)
        candidate = build_record(original.id, apply(annotation, changes), original.integrality)
        attach_review(candidate, original.review)  # the wording, and so the review, is the same
        reason = rejection(original, candidate)
        if reason is None:
            how = Perturbation(seed=SEED, draw=draw, changes=changes)
            return PerturbedRecord(**dict(candidate), perturbation=how)
        rejected[reason] += 1
    return f"no draw kept in {MAX_DRAWS} (most often: {rejected.most_common(1)[0][0]})"


def load_perturbed(path: Path) -> list[PerturbedRecord]:
    return [PerturbedRecord.model_validate(row) for row in json.loads(path.read_text())]


def build_split(split: str) -> tuple[list[PerturbedRecord], dict[str, str]]:
    """The perturbed records, and why each other problem has none."""
    annotations = load_split(fetch(SPLITS[split]))
    kept, left_out = [], {}
    for original in load_records(GROUND_TRUTH_DIR / f"{split}.json"):
        annotation = annotations[original.id]
        result = ineligible(original, annotation) or perturb(split, original, annotation)
        if isinstance(result, str):
            left_out[original.id] = result
        else:
            kept.append(result)
    return kept, left_out


def main() -> None:
    built = {split: build_split(split) for split in SPLITS}
    for split, (kept, _) in built.items():
        write_records(kept, GROUND_TRUTH_DIR / f"{split}-perturbed.json")
    summary = render_summary(built)
    (GROUND_TRUTH_DIR / "PERTURBED.md").write_text(summary)
    print(summary)


# ---- summary ----------------------------------------------------------------------------


def render_summary(built: dict[str, tuple[list[PerturbedRecord], dict[str, str]]]) -> str:
    lines = [
        "# The perturbed-numbers set",
        "",
        "Generated by `python -m opt_agent.perturb` (the rule is in `perturb.py`'s docstring);",
        f"seed {SEED}, factor {FACTOR[0]:g} to {FACTOR[1]:g}, at most {MAX_DRAWS} draws per "
        "problem. Don't edit by hand.",
        "",
        "| split | problems | perturbed | integrality-sensitive | strict wording | "
        "ambiguous | numbers changed (median) |",
        "|---|---|---|---|---|---|---|",
    ]
    for split, (kept, left_out) in built.items():
        changed = sorted(len(r.perturbation.changes) for r in kept)
        median = changed[len(changed) // 2] if changed else 0
        sensitive = sum(integrality_matters(r) for r in kept)
        lines.append(
            f"| {split} | {len(kept) + len(left_out)} | {len(kept)} | {sensitive} | "
            f"{sum(r.strict is not None for r in kept)} | "
            f"{sum(r.equality is not None for r in kept)} | {median} |"
        )
    for split, (kept, left_out) in built.items():
        lines += ["", f"## {split}", "", "Not perturbed, by reason:", ""]
        for reason, n in sorted(Counter(left_out.values()).items(), key=lambda kv: -kv[1]):
            lines.append(f"- {reason}: {n}")
        draws = Counter(r.perturbation.draw for r in kept)
        lines += ["", "Draws needed: " + ", ".join(f"{d}: {n}" for d, n in sorted(draws.items()))]
        unkept = sorted(pid for pid, why in left_out.items() if why.startswith("no draw"))
        if unkept:
            lines += ["", "No draw kept: " + ", ".join(f"`{pid}`" for pid in unkept)]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
