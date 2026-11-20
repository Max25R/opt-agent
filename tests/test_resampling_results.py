"""results/resampling.json and docs/resampling/RESULTS.md (scripts/resampling_results.py): the
JSON is the frozen analysis's report, written past its one bug (deviation 1,
docs/resampling/DEVIATIONS.md), and RESULTS.md is rendered from it. The README's numbers are
checked against the JSON in test_readme_numbers.py. No API calls.

Rebuilding the JSON needs the follow-up's keys (LLM4OR's git-ignored data) and the tag, so the
test job skips that one test and CI's reproduce job, which has both, runs it; the rest check
the committed report against the frozen analysis's own functions, which need neither."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from opt_agent import resampling_report, stats

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "resampling_results.py"
spec = importlib.util.spec_from_file_location("resampling_results", SCRIPT)
results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(results)
spec = importlib.util.spec_from_file_location("reproduce", ROOT / "scripts" / "reproduce.py")
reproduce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reproduce)


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(results.OUT.read_text())


def test_results_md_is_rendered_from_the_committed_json(committed):
    assert results.render(committed) == results.RESULTS_MD.read_text()


def test_the_frozen_analysis_makes_a_numpy_bool_that_json_cant_write():
    """Deviation 1: stats.mcnemar_exact returns a numpy float when p < 1, so R2's verdict,
    p < ALPHA, is a numpy bool, which stopped the frozen main(). The script writes it as the
    Python value it holds; the p-value, a numpy float (a Python float too), as json would."""
    p = stats.mcnemar_exact(0, 11)  # 11 discordant problems, all one way: 2 / 2**11
    detected = p < resampling_report.ALPHA
    assert isinstance(p, np.floating) and p == 2 / 2**11
    assert type(detected) is np.bool_
    with pytest.raises(TypeError, match="not JSON serializable"):
        json.dumps({"detected": detected})
    assert results.dumps({"detected": detected, "p_value": p}) == (
        '{\n "detected": true,\n "p_value": 0.0009765625\n}\n')  # fmt: skip
    assert results.dumps({"p_value": p}) == json.dumps({"p_value": 2 / 2**11}, indent=1) + "\n"


def test_nothing_else_is_converted():
    with pytest.raises(TypeError, match="not JSON serializable"):
        results.dumps({"x": object()})


def test_r1_its_secondary_and_abstention_follow_from_the_committed_units(committed):
    """The frozen analysis's own functions, on the committed units, give the committed report."""
    rows = committed["units"]
    assert resampling_report.r1(rows) == committed["r1"]
    unaffected = [r for r in rows if r["problem"] not in resampling_report.DISPUTED]
    assert resampling_report.r1(unaffected) == committed["r1_without_disputed"]
    assert resampling_report.abstention(rows) == committed["abstention"]
    assert len(rows) == committed["problems"] - committed["problems_without_a_unit"]
    assert all(r["flagged"] == (r["samples_disagree"] or r["baseline_disagrees"]) for r in rows)


def test_the_verdicts_follow_section_4(committed):
    r1, r2 = committed["r1"], committed["r2"]
    assert r1["supported"] == (r1["p_value"] < resampling_report.ALPHA)
    assert r2["p_value"] == stats.mcnemar_exact(r2["only_one_sample_right"],
                                                r2["only_majority_right"])  # fmt: skip
    assert r2["detected"] == (r2["p_value"] < resampling_report.ALPHA)
    # one sample's right answers are the right units: a problem without a unit is wrong
    t = r1["table"]
    assert r2["one_sample_right"] == t["flagged_right"] + t["unflagged_right"]


def test_rebuilding_from_the_tag_gives_the_committed_files(tmp_path):
    """The frozen analysis, run in resampling-freeze's own tree (scripts/reproduce.py),
    rebuilds results/resampling.json and RESULTS.md byte for byte, however far HEAD has
    moved. Needs the keys (the git-ignored LLM4OR data), so CI's test job skips it."""
    from opt_agent import followup_freeze, resampling_freeze

    if not all(p.exists() for p in followup_freeze.data_files()):
        pytest.skip("needs the LLM4OR data (docs/EXTERNAL_DATA.md)")
    if not resampling_freeze.tag_exists():
        pytest.skip("needs the tag resampling-freeze")
    rebuilt = reproduce.rebuild_resampling(tmp_path)
    assert set(rebuilt) == set(reproduce.RESAMPLING_OUTPUTS)
    assert reproduce.differences(rebuilt) == []
