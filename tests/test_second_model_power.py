"""docs/second_model/power.md (scripts/second_model_power.py): the committed file is what the
script writes, the power is exact (no seed), and its design inputs are Haiku's record, checked
against it where the follow-up's keys are. No API calls."""

import importlib.util
from pathlib import Path

import pytest
from scipy.stats import binom

from opt_agent import followup_freeze, followup_report, stats

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "second_model_power", ROOT / "scripts" / "second_model_power.py"
)
power = importlib.util.module_from_spec(spec)
spec.loader.exec_module(power)


def test_power_md_is_what_the_script_writes():
    assert power.OUT.read_text() == power.render()


def test_the_rejection_thresholds_are_the_exact_mcnemar_tests():
    cutoffs = power.thresholds()
    assert cutoffs[5] is None  # 5 of 5: p = 2/32, not below 0.05
    assert cutoffs[6] == 6  # 6 of 6: p = 2/64
    for d in (12, 30, 60):
        b = cutoffs[d]
        assert stats.mcnemar_exact(b, d - b) < 0.05 <= stats.mcnemar_exact(b - 1, d - b + 1)


def test_the_power_is_an_exact_sum_and_small_with_no_difference():
    cutoffs = power.thresholds()
    by_hand = sum(binom.pmf(d, power.N, 0.12) * binom.sf(cutoffs[d] - 1, d, 0.10 / 0.12)
                  for d in range(power.N + 1) if cutoffs[d] is not None)  # fmt: skip
    assert power.power(0.10, 0.02, cutoffs) == pytest.approx(by_hand)
    assert power.power(0.05, 0.05, cutoffs) < 0.025  # no difference: one tail of alpha at most
    assert power.feasible(26 / 121) and not power.feasible(27 / 121)


def test_the_design_inputs_are_haikus_record():
    """Sample by sample, Haiku's single-shot answers on the 121 problems (section 2)."""
    if not all(p.exists() for p in followup_freeze.data_files()):
        pytest.skip("needs LLM4OR's data (python scripts/fetch_llm4or.py)")
    from opt_agent import second_model, second_model_freeze
    from opt_agent.evaluate import latest_items

    records = second_model_freeze.problems()
    items = {(i.problem_id, i.sample): i for i in latest_items(second_model.HAIKU_RECORD)
             if i.condition == "single-shot"}  # fmt: skip

    def right(pid: str, sample: int) -> bool:
        i = items[(pid, sample)]
        return i.outcome == "done" and followup_report.is_right(
            next(r for r in records if r.id == pid), followup_report.answer_of(i))  # fmt: skip

    rights = {s: {r.id for r in records if right(r.id, s)} for s in (0, 1, 2)}
    assert {s: len(found) for s, found in rights.items()} == power.HAIKU_RIGHT
    assert {(a, b): (len(rights[a] - rights[b]), len(rights[b] - rights[a]))
            for a, b in power.HAIKU_DISAGREE} == power.HAIKU_DISAGREE  # fmt: skip
