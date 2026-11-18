"""The failure-type analysis (docs/analysis/failure_types.md): every wrong answer of the solver
conditions is classified exactly once, the counts are the CSV's, and every committed corrected
model still solves to what the CSV says. Exploratory and post hoc, so these check consistency,
not the labels themselves (an LLM's reading)."""

import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from opt_agent.highs import solve_with_highs
from opt_agent.schema import LPModel
from opt_agent.solver import solve
from opt_agent.verify import check_solution, same_answer

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs" / "analysis"
TYPES = ["wrong objective", "missing constraint", "wrong number/coefficient",
         "wrong inequality direction", "integrality", "units/misread quantity",
         "answer-key dispute", "other"]  # fmt: skip

pytestmark = pytest.mark.skipif(not (ANALYSIS / "failure_types.csv").exists(),
                                reason="the classification isn't built yet")  # fmt: skip


def rows() -> list[dict]:
    with (ANALYSIS / "failure_types.csv").open() as f:
        return list(csv.DictReader(f))


def test_every_wrong_answer_of_the_results_files_is_classified_once():
    counts = Counter((r["run"], r["condition"]) for r in rows())
    assert len(set((r["run"], r["problem"], r["condition"], r["sample"]) for r in rows())) == len(
        rows()
    )
    e = json.loads((ROOT / "results" / "eval.json").read_text())
    for condition in ("single-shot", "self-correction"):
        primary = e["primary"]["accuracy"][condition]
        assert counts[("test", condition)] == primary["n"] - primary["right"]
        perturbed = e["perturbed"]["accuracy"][condition]
        assert counts[("test-perturbed", condition)] == perturbed["n"] - perturbed["right"]
    f = json.loads((ROOT / "results" / "followup.json").read_text())
    for condition in ("single-shot", "self-correction", "checklist-revision"):
        failures = f["also_reported"]["failures"][condition]
        assert counts[("followup-test", condition)] == failures["loud"] + failures["silent"]
    right_to_wrong = sum(r["right_to_wrong"] == "True" for r in rows())
    assert right_to_wrong == f["also_reported"]["checklist_revision"]["right_to_wrong"]


def test_every_label_is_a_type_and_other_names_its_sub_label():
    for r in rows():
        assert r["primary"] in TYPES
        assert all(s in TYPES for s in r["secondary"].split(";") if s)
        assert r["note"]
        if r["primary"] == "other":
            assert r["sub_label"]
        if r["loud"] == "True":
            assert (r["primary"], r["sub_label"]) == ("other", "no usable model")


def test_the_counts_are_the_csvs():
    summary = json.loads((ANALYSIS / "failure_types.json").read_text())
    for study, s in summary["studies"].items():
        mine = [r for r in rows() if r["study"] == study]
        assert s["answers"] == len(mine)
        assert s["primary"] == {t: sum(r["primary"] == t for r in mine) for t in TYPES}


def test_every_committed_corrected_model_solves_to_what_the_csv_says():
    """The big ones restate a whole instance and aren't committed: their verdicts are."""
    fixes = {r["fix"]: r for r in rows() if r["fix_committed"] == "yes"}
    assert {p.name for p in (ANALYSIS / "fixes").glob("*.json")} == set(fixes)
    for name, r in sorted(fixes.items()):
        model = LPModel.model_validate(json.loads((ANALYSIS / "fixes" / name).read_text()))
        cbc, highs = solve(model), solve_with_highs(model)
        confirmed = same_answer(model, cbc, highs) and not check_solution(model, cbc)
        if r["fix_status"] == "unconfirmed":
            assert not confirmed, name
            continue
        assert confirmed and str(cbc.status) == r["fix_status"], name
        if r["fix_objective"]:
            assert cbc.objective == pytest.approx(float(r["fix_objective"]), rel=1e-6), name
