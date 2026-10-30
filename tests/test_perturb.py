"""The perturbed-numbers set: the rule, worked by hand on the gas problem, and checks on the
committed perturbed splits against the committed originals. No raw data or network is
needed, except where a test says so; never calls the API."""

import random
import re
from decimal import Decimal

import pytest
from problems import GAS
from pytest import approx

from opt_agent import perturb
from opt_agent.data import DATA_DIR, NL4OPT_DEV
from opt_agent.ground_truth import (
    GROUND_TRUTH_DIR,
    answer,
    as_integer,
    blind_gradable,
    build_record,
    does_nothing,
    equality_model,
    equality_names,
    load_records,
)
from opt_agent.highs import solve_with_highs
from opt_agent.integrality import Integrality
from opt_agent.nl4opt import Note, convert, load_split
from opt_agent.perturb import (
    FACTOR,
    NUMBER,
    PERTURBED_SPLITS,
    apply,
    draw_changes,
    new_number,
    number_texts,
    rejection,
)
from opt_agent.solver import Solution, Status
from opt_agent.strict import strict_constraints, strict_model
from opt_agent.verify import same_answer

INTEGER = Integrality(kind="integer", source="rule")
BY_HAND = {"8000": "6000", "2000": "3000", "1000000": "700000"}
ORIGINALS = {
    split: {r.id: r for r in load_records(GROUND_TRUTH_DIR / f"{split}.json")}
    for split in PERTURBED_SPLITS.values()
}
PERTURBED = {
    split: perturb.load_perturbed(GROUND_TRUTH_DIR / f"{split}.json") for split in PERTURBED_SPLITS
}


def shape(text: str) -> tuple[int, int]:
    """(significant digits, decimal places) of the number in a text."""
    value = Decimal(NUMBER.search(text).group().replace(",", ""))
    return len(value.normalize().as_tuple().digits), max(0, -value.as_tuple().exponent)


def value(text: str) -> Decimal:
    return Decimal(NUMBER.search(text).group().replace(",", ""))


def rngs(n: int = 300):
    return (random.Random(i) for i in range(n))


# ---- one number -------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["8000", "$1,500", "1.5", "0.25", "8000 minutes", "35", "12"])
def test_a_new_number_looks_like_the_old_one(text):
    """No more significant digits, the same decimal places, the same words and symbols
    around it, and within FACTOR of it."""
    digits, places = shape(text)
    for rng in rngs():
        new = new_number(text, rng)
        assert NUMBER.sub("#", new) == NUMBER.sub("#", text), new  # "$#", "# minutes"
        assert shape(new)[0] <= digits and shape(new)[1] == places, new
        assert value(new) != value(text), new
        assert FACTOR[0] <= value(new) / value(text) <= FACTOR[1], new


def test_thousands_keep_their_commas():
    for rng in rngs():
        new = new_number("$1,500", rng)
        assert ("," in new) == (value(new) >= 1000), new
        assert "," not in new_number("1500", rng)


def test_one_stays_one_and_nothing_becomes_one():
    """English agreement: "1 hour" can't become "2 hour", nor "2 hours" "1 hours"."""
    assert number_texts(apply(GAS, {})) == ["8000", "2000", "1000000"]
    doc = "It takes 1 hour, or 2 hours by train."
    spans = [{"start": m.start(), "end": m.end(), "label": "PARAM"}
             for m in re.finditer(r"\d", doc)]  # fmt: skip
    assert number_texts({**GAS, "document": doc, "spans": spans}) == ["2"]
    assert {new_number("2", rng) for rng in rngs()} == {"3", "4"}  # 1 sig. digit, up to x2


def test_a_percentage_stays_below_100():
    news = {value(new_number("60%", rng, percent=True)) for rng in rngs()}
    assert max(news) < 100 and min(news) >= 30
    assert max(value(new_number("60", rng)) for rng in rngs()) >= 100  # not a percentage


def test_small_numbers_still_get_texts_of_their_own():
    """Like dev 1775140418's 2, 3, 4, 5, 6: "2" can only become 3 or 4, and the others may
    have taken both. Redrawing just "2" would never finish; redrawing the draw does."""
    doc = "It needs 2, 3, 4, 5 and 6 hours."
    spans = [{"start": m.start(), "end": m.end(), "label": "PARAM"}
             for m in re.finditer(r"\d", doc)]  # fmt: skip
    ann = {**GAS, "document": doc, "spans": spans}
    for rng in rngs(50):
        changes = draw_changes(ann, rng)
        assert changes["2"] in ("3", "4") and len(set(changes.values())) == 5


def test_a_draw_is_reproducible():
    first = draw_changes(GAS, random.Random("seed"))
    assert draw_changes(GAS, random.Random("seed")) == first
    assert set(first) == {"8000", "2000", "1000000"}  # "twice" is a word: it stays
    assert len(set(first.values())) == 3


# ---- the gas problem, by hand -----------------------------------------------------------


def test_the_gas_problem_by_hand():
    """min p + t, with 6000p + 3000t >= 700000 and t >= 2p (the "twice" stays). As an LP the
    second binds: 12000p = 700000, so p = 58 1/3 and t = 116 2/3, 175 in all. In whole
    numbers 175 can't be done (t >= 2p caps p at 58; the capacity needs p >= 59), so 176:
    58 pipelines and 118 trains. The original is 250 (LP) and 251 (IP): a new answer, and
    integrality still matters."""
    changed = apply(GAS, BY_HAND)
    doc = changed["document"]
    assert "carry 6000 units" in doc and "carry 3000 units" in doc
    assert "at least 700000 units" in doc and "at least twice as many" in doc
    demand, ratio = convert(changed).model.constraints
    assert {t.var: t.coef for t in demand.terms} == {"pipeline": 6000, "train": 3000}
    assert demand.rhs == 700000
    assert {t.var: t.coef for t in ratio.terms} == {"train": 1, "pipeline": -2}
    record = build_record("439170086", changed, INTEGER)
    assert (record.lp.objective, record.ip.objective) == approx((175, 176))
    assert record.ip.values == approx({"pipeline": 58, "train": 118})
    original = build_record("439170086", GAS, INTEGER)
    assert (original.lp.objective, original.ip.objective) == approx((250, 251))
    assert rejection(original, record) is None


def test_a_draw_where_integrality_stops_mattering_is_rejected():
    """With 900000 instead: 12000p = 900000 gives 75 and 150, whole numbers already, so the
    LP and IP agree at 225. The original's differ, so this isn't the same kind of problem."""
    record = build_record("439170086", apply(GAS, {**BY_HAND, "1000000": "900000"}), INTEGER)
    assert (record.lp.objective, record.ip.objective) == approx((225, 225))
    original = build_record("439170086", GAS, INTEGER)
    assert rejection(original, record) == "integrality matters differently"


def test_spans_move_with_the_text_and_a_change_can_be_undone():
    changes = draw_changes(GAS, random.Random(7))
    changed = apply(GAS, changes)
    for old_span, new_span in zip(GAS["spans"], changed["spans"], strict=True):
        old = GAS["document"][old_span["start"] : old_span["end"]]
        new = changed["document"][new_span["start"] : new_span["end"]]
        assert new == changes.get(old, old)  # every span still covers its words
    undone = apply(changed, {new: old for old, new in changes.items()})
    for field in ("document", "spans", "obj_declaration", "const_declarations"):
        assert undone[field] == GAS[field], field


def test_one_text_changes_everywhere_and_other_texts_with_its_value_change_apart():
    """Two quantities written "10" (NL4Opt can't tell them apart), and one "10%"."""
    doc = "A line needs 10 workers and 10 hours. At least 10% of lines are new."
    spans = [{"start": m.start(), "end": m.end(), "label": "PARAM"}
             for m in re.finditer(r"10%?", doc)]  # fmt: skip
    ann = {**GAS, "document": doc, "spans": spans, "const_declarations": [
        {"type": "linear", "limit": "10%", "terms": {"pipeline": "10", "train": "10"},
         "operator": "LESS_OR_EQUAL", "direction": "at most"}]}  # fmt: skip
    assert number_texts(ann) == ["10", "10%"]
    changes = draw_changes(ann, random.Random(1))
    changed = apply(ann, changes)
    [decl] = changed["const_declarations"]
    assert decl["terms"] == {"pipeline": changes["10"], "train": changes["10"]}
    assert decl["limit"] == changes["10%"] and changes["10%"].endswith("%")
    assert changed["document"].count(changes["10"] + " ") == 2  # workers and hours


# ---- which draws are kept ---------------------------------------------------------------


def test_a_draw_that_keeps_an_old_answer_is_rejected():
    original = build_record("439170086", GAS, INTEGER)
    assert rejection(original, original) == "an original answer would still be right"
    # 8000 and 2000 doubled, 1000000 doubled: the same problem at twice the scale, IP 251.
    doubled = apply(GAS, {"8000": "16000", "2000": "4000", "1000000": "2000000"})
    assert rejection(original, build_record("439170086", doubled, INTEGER)) == (
        "an original answer would still be right"
    )


def test_a_draw_with_no_optimum_or_other_judgment_calls_is_rejected():
    original = build_record("439170086", GAS, INTEGER)
    infeasible = original.model_copy(update={"ip": original.ip.model_copy(
        update={"status": Status.INFEASIBLE, "objective": None})})  # fmt: skip
    assert rejection(original, infeasible) == "no optimum"
    extra = original.model_copy(update={"notes": [Note(kind="duplicate-var", detail="x")]})
    assert rejection(original, extra) == "different judgment calls"
    untrusted = original.model_copy(update={"lp": original.lp.model_copy(
        update={"highs_agrees": False})})  # fmt: skip
    assert rejection(original, untrusted) == "a solve doesn't check out"


# ---- the committed perturbed splits -----------------------------------------------------


def committed(solve) -> Solution:
    return Solution(solver="cbc", status=solve.status, objective=solve.objective,
                    values=solve.values)  # fmt: skip


@pytest.mark.parametrize("split", PERTURBED_SPLITS)
def test_highs_reproduces_every_perturbed_answer(split):
    for r in PERTURBED[split]:
        assert same_answer(r.model, committed(r.lp), solve_with_highs(r.model)), r.id
        integer = as_integer(r.model)
        assert same_answer(integer, committed(r.ip), solve_with_highs(integer)), r.id
        if r.strict is not None:
            tight, _ = strict_model(integer, strict_constraints(r.notes))
            assert same_answer(tight, committed(r.strict.ip), solve_with_highs(tight)), r.id
        if r.equality is not None:
            equal, _ = equality_model(r.model, equality_names(r))
            assert same_answer(equal, committed(r.equality.lp), solve_with_highs(equal)), r.id


@pytest.mark.parametrize("split", PERTURBED_SPLITS)
def test_every_perturbed_problem_passes_the_rule_against_its_original(split):
    originals = ORIGINALS[PERTURBED_SPLITS[split]]
    for r in PERTURBED[split]:
        original = originals[r.id]
        assert blind_gradable(original) and answer(original).status is Status.OPTIMAL, r.id
        assert not does_nothing(original), r.id
        assert rejection(original, r) is None, r.id
        assert r.integrality == original.integrality and r.review == original.review, r.id
        assert r.perturbation.seed == perturb.SEED
        assert 1 <= r.perturbation.draw <= perturb.MAX_DRAWS


@pytest.mark.parametrize("split", PERTURBED_SPLITS)
def test_only_the_numbers_changed(split):
    """Outside its numbers, the text is the original's; each number that differs is one
    the changes name; each new text is in it; and the model has the original's shape."""
    originals = ORIGINALS[PERTURBED_SPLITS[split]]
    for r in PERTURBED[split]:
        original, changes = originals[r.id], r.perturbation.changes
        old_parts, new_parts = NUMBER.split(original.document), NUMBER.split(r.document)
        assert old_parts == new_parts, r.id  # the words between the numbers
        renamed: dict[str, set[str]] = {}  # "20" -> {"30", "10"} when "20" and "20%" both change
        for o, n in changes.items():
            renamed.setdefault(NUMBER.search(o).group(), set()).add(NUMBER.search(n).group())
        for old, new in zip(NUMBER.findall(original.document), NUMBER.findall(r.document),
                            strict=True):  # fmt: skip
            assert new == old or new in renamed.get(old, ()), (r.id, old, new)
        assert all(new in r.document for new in changes.values()), r.id
        assert _shape_of(r.model) == _shape_of(original.model), r.id


@pytest.mark.parametrize("split", PERTURBED_SPLITS)
def test_every_change_follows_the_rule(split):
    for r in PERTURBED[split]:
        changes = r.perturbation.changes
        assert changes and len(set(changes.values())) == len(changes), r.id
        for old, new in changes.items():
            assert NUMBER.sub("#", old) == NUMBER.sub("#", new), (r.id, old, new)
            assert shape(new)[0] <= shape(old)[0] and shape(new)[1] == shape(old)[1], r.id
            assert FACTOR[0] <= value(new) / value(old) <= FACTOR[1], (r.id, old, new)
            if "%" in old and value(old) < 100:
                assert value(new) < 100, (r.id, old, new)


@pytest.mark.parametrize("split", PERTURBED_SPLITS)
def test_a_perturbed_split_reads_as_plain_records(split):
    """The runner and the report load every split the same way."""
    plain = load_records(GROUND_TRUTH_DIR / f"{split}.json")
    assert [r.id for r in plain] == [r.id for r in PERTURBED[split]]
    assert set(r.id for r in plain) <= set(ORIGINALS[PERTURBED_SPLITS[split]])


def _shape_of(model) -> tuple:
    return (
        [v.name for v in model.variables],
        model.objective.sense,
        sorted(t.var for t in model.objective.terms),
        [(c.name, c.sense, sorted(t.var for t in c.terms)) for c in model.constraints],
    )


def test_rebuilding_dev_problems_reproduces_the_committed_records():
    """Same seed, same draws, same records. Each problem has its own random stream, so a
    sample will do (the whole build takes minutes). Needs the raw annotations."""
    path = DATA_DIR / NL4OPT_DEV.path
    if not path.exists():
        pytest.skip("the raw annotations aren't downloaded (run `python -m opt_agent.data`)")
    annotations = load_split(path)
    for r in PERTURBED["dev-perturbed"][:12]:
        assert perturb.perturb("dev", ORIGINALS["dev"][r.id], annotations[r.id]) == r, r.id
