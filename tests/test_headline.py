"""scripts/headline.py, the README's headline figure and its cost and latency table: the
committed record (results/headline.json) is what the script computes now; the figure's numbers
are the results files' own; each condition's total cost and median latency equal the results
files' (so the cost per answer and the p90 come from the same answers), Claude Sonnet 5.5's
rows results/second_model.json's, with no p90; and the percentile is
numpy's linear one, as in both reports. The PNG's bytes aren't checked; CI's pictures job draws
it. No API calls, no matplotlib here."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("headline", ROOT / "scripts" / "headline.py")
headline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(headline)

EVAL = json.loads(headline.EVAL.read_text())
FOLLOWUP = json.loads(headline.FOLLOWUP.read_text())
SECOND_MODEL = json.loads(headline.SECOND_MODEL.read_text())
COMMITTED = json.loads(headline.OUT.read_text())


def test_the_committed_record_is_current():
    assert headline.compute() == COMMITTED


def test_the_figures_numbers_are_the_results_files():
    figure = COMMITTED["figure"]
    for c in headline.NL4OPT:
        assert figure["nl4opt"]["accuracy"][c] == EVAL["primary"]["accuracy"][c]
    assert figure["nl4opt"]["problems"] == EVAL["primary"]["n"] == 274
    tests = FOLLOWUP["pre_registered"]["primary"]["primary"]
    for h in ("H1", "H2"):
        for key, value in figure["harder"]["differences"][h].items():
            assert value == tests[h][key]
    h2 = figure["harder"]["differences"]["H2"]
    assert (h2["a"], h2["b"], h2["verdict"]) == ("baseline", "single-shot", "detected")


def test_each_condition_matches_its_results_files_total_and_median():
    table = COMMITTED["cost_latency"]
    for study, conditions in headline.STUDIES:
        for c in conditions:
            row = table[study]["conditions"][c]
            cost, p50 = headline.recorded(EVAL, FOLLOWUP, SECOND_MODEL, study, c)
            assert row["cost_usd"] == pytest.approx(cost, rel=1e-9)
            assert row["latency_p50_s"] == pytest.approx(p50, rel=1e-12)
            assert row["cost_per_answer_usd"] == pytest.approx(row["cost_usd"] / row["answers"])
            if study in headline.WITHOUT_P90:
                assert "latency_p90_s" not in row
            else:
                assert row["latency_p50_s"] <= row["latency_p90_s"]
    assert (table["nl4opt"]["problems"], table["nl4opt"]["samples"]) == (274, 1)
    assert (table["harder"]["problems"], table["harder"]["samples"]) == (128, 3)
    assert {r["answers"] for r in table["harder"]["conditions"].values()} == {128 * 3}
    assert (table["sonnet"]["problems"], table["sonnet"]["samples"]) == (121, 1)


def test_sonnets_rows_are_the_second_model_studys_answers():
    """Each stage's 121 answers, as the frozen analysis counted them: the same total cost,
    cost per answer and median latency as results/second_model.json (its single-shot stage,
    then its no-solver stage), and no p90, which the report doesn't have (its deviation 2,
    removed on 2026-11-23)."""
    rows = COMMITTED["cost_latency"]["sonnet"]["conditions"]
    for condition, spend in (("single-shot", SECOND_MODEL["spend"]["sonnet"]),
                             ("baseline", SECOND_MODEL["stage_2"]["spend"]["sonnet"])):  # fmt: skip
        row = rows[condition]
        assert row["answers"] == spend["answers"] == 121
        assert row["cost_usd"] == pytest.approx(spend["cost_usd"], rel=1e-12)
        assert row["cost_per_answer_usd"] == pytest.approx(spend["cost_per_answer_usd"])
        assert row["latency_p50_s"] == spend["median_latency_s"]
        assert set(row) == {"answers", "cost_usd", "cost_per_answer_usd", "latency_p50_s"}


def test_the_percentiles_are_numpys_linear_ones():
    items = [{"latency_s": float(x), "cost_usd": 0.001} for x in range(1, 11)]  # 1 to 10 s
    row = headline.per_answer(items)
    assert row["latency_p50_s"] == pytest.approx(5.5)  # halfway between 5 and 6
    assert row["latency_p90_s"] == pytest.approx(9.1)  # 9 + 0.1 of the way to 10
    assert row["cost_per_answer_usd"] == pytest.approx(0.001)


def test_a_run_that_doesnt_give_the_results_files_numbers_is_refused(monkeypatch):
    monkeypatch.setattr(headline, "recorded", lambda e, f, s, study, c: (1.0, 1.0))
    with pytest.raises(SystemExit, match="total cost and median latency"):
        headline.cost_latency(EVAL, FOLLOWUP, SECOND_MODEL)


def test_check_refuses_a_stale_record(monkeypatch, tmp_path):
    stale = tmp_path / "headline.json"
    stale.write_text(json.dumps({**COMMITTED, "figure": {}}))
    monkeypatch.setattr(headline, "OUT", stale)
    with pytest.raises(SystemExit, match="isn't current"):
        headline.main(["--check", str(tmp_path / "out.png")])
