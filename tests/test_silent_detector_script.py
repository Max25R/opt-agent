"""The detector's one run (scripts/silent_detector.py): its counts, and its refusal to run
again. Made-up rows only: the real run is the one-time test."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "silent_detector", ROOT / "scripts" / "silent_detector.py"
)
silent_detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(silent_detector)


def rows(*pairs: tuple[bool, bool]) -> list[dict]:
    return [{"right": right, "flagged": flagged} for right, flagged in pairs]


def test_precision_recall_and_false_flags():
    # 4 silent failures (3 flagged), 6 right answers (1 flagged)
    data = rows(*[(False, True)] * 3, (False, False), (True, True), *[(True, False)] * 5)
    c = silent_detector.confusion(data)
    assert (c["silent_failures"], c["correct"], c["flagged"]) == (4, 6, 4)
    assert (c["flagged_silent"], c["flagged_correct"]) == (3, 1)
    assert c["precision"]["value"] == 3 / 4
    assert c["recall"]["value"] == 3 / 4
    assert c["false_flag_rate"]["value"] == 1 / 6
    low, high = c["recall"]["wilson95"]
    assert low < 3 / 4 < high


def test_nothing_flagged_has_no_precision():
    c = silent_detector.confusion(rows((False, False), (True, False)))
    assert c["precision"]["value"] is None
    assert c["recall"]["value"] == 0


def test_it_refuses_to_run_twice(tmp_path, monkeypatch):
    done = tmp_path / "silent_detector.json"
    done.write_text("{}")
    monkeypatch.setattr(silent_detector, "OUT", done)
    monkeypatch.setattr(silent_detector, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="runs once"):
        silent_detector.main()
