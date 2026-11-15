"""results/followup.json and docs/followup/RESULTS.md (scripts/followup_results.py): current,
and faithful to the frozen analysis's report. The README's numbers are checked against the
JSON in test_readme_numbers.py. No API calls."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "followup_results.py"
spec = importlib.util.spec_from_file_location("followup_results", SCRIPT)
results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(results)

RUN = ROOT / "runs" / "followup-test"
REPORT = RUN / "followup_report.json"
DERIVED = {"score_difference_pp", "score_ci_pp", "majority_difference_pp", "majority_ci_pp"}
pytestmark = pytest.mark.skipif(not REPORT.exists(), reason="the follow-up run isn't here")


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(results.OUT.read_text())


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(REPORT.read_text())


def test_results_md_is_rendered_from_the_committed_json(committed):
    assert results.RESULTS_MD.read_text() == results.render(committed)


def test_the_json_is_built_from_this_report(committed):
    sha = hashlib.sha256(REPORT.read_bytes()).hexdigest()
    assert committed["provenance"]["report_sha256"] == sha
    freeze = json.loads(results.FREEZE.read_text())
    assert committed["provenance"]["analysis_sha256"] == freeze["analysis_sha256"]


@pytest.mark.parametrize("row", ["primary", "sensitivity"])
def test_every_pre_registered_number_is_the_reports(committed, report, row):
    """Copied, never recomputed: each field equals the frozen report's, and the derived
    forms are exact transformations of it."""
    mine, theirs = committed["pre_registered"][row], report["rows"][results.ROWS[row]]
    assert mine["problems"] == theirs["problems"]
    for c, a in theirs["accuracy"].items():
        assert {k: v for k, v in mine["accuracy"][c].items() if k != "majority_share"} == a
        assert mine["accuracy"][c]["majority_share"] == a["majority_right"] / a["problems"]
    for group in ("primary", "exploratory"):
        for name, c in theirs[group].items():
            m = mine[group][name]
            assert {k: v for k, v in m.items() if k not in DERIVED} == c
            assert m["score_difference_pp"] == 100 * c["score_difference"]
            assert m["score_ci_pp"] == [100 * x for x in c["score_ci"]]
            assert m["majority_difference_pp"] == 100 * c["majority_difference"]
            assert m["majority_ci_pp"] == [100 * x for x in c["majority_ci"]]


def test_verdicts_follow_section_4(committed):
    """Detected only at a Holm-adjusted p below alpha; an inconclusive contrast carries the
    one bound section 4 allows, and its interval lies within it."""
    alpha = committed["pre_registered"]["settings"]["alpha"]
    for row in ("primary", "sensitivity"):
        for c in committed["pre_registered"][row]["primary"].values():
            assert (c["verdict"] == "detected") == (c["sign_flip_p_holm"] < alpha)
            if c["verdict"] == "inconclusive":
                bound = c["no_difference_larger_than_pp"]
                assert all(abs(x) <= bound for x in c["score_ci_pp"])


def test_the_also_reported_items_are_the_reports(committed, report):
    also = committed["also_reported"]
    for key in ("sample_agreement", "checklist_revision", "failures", "right_only_by_rounding"):
        assert also[key] == report[key]
    for c, s in report["spend"].items():
        assert {k: v for k, v in also["spend"][c].items() if k != "paid_usd"} == s
    assert also["disputes"]["n"] == len(report["disputes"])


def test_what_the_conditions_paid_adds_up_to_the_run(committed):
    v, spend = committed["provenance"], committed["also_reported"]["spend"]
    assert sum(spend[c]["paid_usd"] for c in results.CONDITIONS) == pytest.approx(v["paid_usd"])
    ledger = [json.loads(line) for line in (RUN / "spend.jsonl").read_text().splitlines()]
    assert v["paid_calls"] == len(ledger)


def test_the_descriptive_counts_agree_with_the_report(committed, report):
    desc = committed["descriptive"]
    every = desc["revision_by_flag_kind"]["all"]
    cr = report["checklist_revision"]
    assert every["revised"] == cr["revised"]
    assert (every["wrong_to_right"], every["right_to_wrong"]) == (
        cr["wrong_to_right"], cr["right_to_wrong"])  # fmt: skip
    h = desc["h2_and_cut_off_replies"]
    h2 = committed["pre_registered"]["primary"]["primary"]["H2"]
    parts = h["from_pairs_with_a_cut_off_reply_pp"] + h["from_other_pairs_pp"]
    assert parts == pytest.approx(h2["score_difference_pp"])
    for c, kinds in desc["loud_failures_by_kind"].items():
        assert sum(kinds.values()) == report["failures"][c]["loud"]


def test_rebuilding_gives_the_committed_json(committed):
    """Needs the keys, which load only on the follow-up's frozen inputs (and the git-ignored
    LLM4OR data), so CI skips it."""
    from opt_agent import followup_freeze
    from opt_agent.freeze import FreezeError

    try:
        followup_freeze.check()
    except FreezeError:
        pytest.skip("the follow-up's frozen inputs aren't all here (CI has no LLM4OR data)")
    assert results.build() == committed
