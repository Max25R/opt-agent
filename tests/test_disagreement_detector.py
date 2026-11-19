"""scripts/disagreement_detector.py, on synthetic answers: the signals (rule 4), the counts and
intervals (rule 6), the real-signal rule (rule 7), that it runs only once, that rule 5's
disputed problems are the failure-type analysis's, and that the doc's results section is the
one run's record (docs/analysis/disagreement_detector.md). No API calls, and no study data:
the one run reads the committed runs in each tag's tree."""

import importlib.util
import json
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "disagreement_detector", ROOT / "scripts" / "disagreement_detector.py"
)
detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detector)


def same(a, b, tol: float = 1e-4) -> bool:  # the follow-up grader's rule, for answers here
    if a is None or b is None:
        return a is b
    return a[0] == b[0] and (a[0] != "optimal" or math.isclose(a[1], b[1], rel_tol=tol,
                                                                abs_tol=tol))  # fmt: skip


def opt(x: float) -> tuple[str, float]:
    return ("optimal", x)


def test_samples_agree_only_if_every_pair_does():
    """With a tolerance, "the same" isn't transitive: 1 ~ 1.00008 ~ 1.00016, but 1 !~ 1.00016."""
    assert detector.all_agree([opt(1), opt(1.00008)], same)
    assert not detector.all_agree([opt(1), opt(1.00008), opt(1.00016)], same)
    assert not detector.all_agree([opt(1), opt(1), None], same)  # a loud sample differs
    assert detector.all_agree([("infeasible", None)] * 3, same)


def test_a_units_signals():
    row = detector.unit_row("p", 1, False, opt(5), same, samples=[opt(5), opt(5), opt(6)],
                            checklist=opt(5), baseline=None, has_checklist=True)  # fmt: skip
    assert (row["a"], row["b"], row["c"]) == (True, False, True)  # no baseline answer differs
    nl4opt = detector.unit_row("q", 0, True, opt(5), same, baseline=opt(5.00001))
    assert (nl4opt["a"], nl4opt["b"], nl4opt["c"]) == (None, None, False)
    rows = detector.with_any([row, nl4opt])
    assert [r["d"] for r in rows] == [True, False]


def test_counts_and_intervals():
    rows = [{"problem": f"p{i // 3}", "right": i >= 4, "x": i in (0, 1, 2, 5)} for i in range(10)]
    c = detector.confusion(rows, "x")
    assert (c["answers"], c["silent"], c["flagged"], c["flagged_silent"]) == (10, 4, 4, 3)
    assert c["precision"]["value"] == 0.75 and c["recall"]["value"] == 0.75
    assert c["base_rate"]["value"] == 0.4 and c["flag_rate"]["value"] == 0.4
    assert c["flagged_problems"] == 2  # p0 (0, 1, 2) and p1 (5)
    low, high = c["precision"]["wilson95"]
    assert low < 0.75 < high
    empty = detector.confusion([r | {"x": False} for r in rows], "x")
    assert empty["precision"]["value"] is None  # nothing flagged: no precision to report


def test_real_signal_needs_both_populations():
    def population(low: float, base: float) -> dict:
        return {"d": {"precision": {"wilson95": [low, 1.0]}, "base_rate": {"value": base}}}

    assert detector.real_signal({"all": population(0.3, 0.2), "w": population(0.25, 0.2)}, "d")
    assert not detector.real_signal({"all": population(0.3, 0.2), "w": population(0.2, 0.2)}, "d")


def test_it_runs_only_once(tmp_path, monkeypatch):
    done = tmp_path / "disagreement_detector.json"
    done.write_text("{}")
    monkeypatch.setattr(detector, "OUT", done)
    with pytest.raises(SystemExit, match="runs once"):
        detector.run()


def test_rule_5s_disputes_are_the_failure_type_analysis_and_the_docs():
    rules = detector.DOC.read_text().split("## The rules, exactly")[1].split("<!-- results")[0]
    listed = set(re.findall(r"`(-?\d+|(?:complexlp|industryor):\d+)`", rules))
    for study, problems in detector.DISPUTED.items():
        assert detector.disputed_from_csv(study) == problems
        assert problems <= listed
    assert (len(detector.DISPUTED["followup"]), len(detector.DISPUTED["nl4opt"])) == (13, 5)


def test_the_results_section_is_the_one_runs_record():
    doc = detector.DOC.read_text()
    section = doc[doc.index(detector.BEGIN) + len(detector.BEGIN) : doc.index(detector.END)]
    if not detector.OUT.exists():  # the rules are committed before the one run
        assert "Not run yet." in section
        return
    assert section.strip() == detector.render(json.loads(detector.OUT.read_text()))
