"""The freeze: what it covers, how a test run is refused, and the owner's approval. Every
approval here goes to a temporary FREEZE.json; never calls the API."""

import pytest

from opt_agent import evaluate, formulate, freeze
from opt_agent.evaluate import CONDITIONS, require_whole_experiment, scorable_records
from opt_agent.freeze import Approval, FreezeError, differences, fingerprint
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records

SECTION_6 = [
    "data/nl4opt/reviews.json", "data/nl4opt/integrality.json", "data/nl4opt/exclusions.json",
    "data/nl4opt/ground_truth/test.json", "data/nl4opt/ground_truth/test-perturbed.json",
    "formulate.SYSTEM_PROMPT", "explain.SYSTEM_PROMPT", "formulate.LP_SCHEMA",
    "baseline.SYSTEM_PROMPT", "baseline.ANSWER_SCHEMA", "perturb.SEED",
    "src/opt_agent/perturb.py", "docs/PREREGISTRATION.md",
]  # fmt: skip


@pytest.fixture
def freeze_file(tmp_path, monkeypatch):
    path = tmp_path / "FREEZE.json"
    monkeypatch.setattr(freeze, "FREEZE_PATH", path)
    return path


def approve_now(path, prints=None) -> None:
    approval = Approval(approved_on="2026-10-29", commit="abc", fingerprint=prints or fingerprint())
    path.write_text(approval.model_dump_json())


# ---- what's frozen ----------------------------------------------------------------------


def test_the_fingerprint_covers_section_6_all_the_code_and_the_lock():
    prints = fingerprint()
    assert set(SECTION_6) <= set(prints)
    sources = {p.relative_to(freeze.REPO_ROOT).as_posix() for p in freeze.SOURCE_DIR.rglob("*.py")}
    assert sources <= set(prints) and "src/opt_agent/feedback.py" in sources
    assert "requirements.lock" in prints
    assert all(len(h) == 64 for h in prints.values())


def test_the_fingerprint_is_stable_and_sees_a_changed_prompt(monkeypatch):
    before = fingerprint()
    assert fingerprint() == before
    monkeypatch.setattr(formulate, "SYSTEM_PROMPT", formulate.SYSTEM_PROMPT + " ")
    assert differences(before, fingerprint()) == ["formulate.SYSTEM_PROMPT: changed"]


def test_differences_name_what_changed_appeared_or_went():
    assert differences({"a": "1", "b": "2"}, {"a": "1", "b": "3", "c": "4"}) == [
        "b: changed", "c: new"]  # fmt: skip
    assert differences({"a": "1"}, {}) == ["a: gone"]


# ---- refusing a test run ----------------------------------------------------------------


def test_nothing_approved_means_no_test_run(freeze_file):
    with pytest.raises(FreezeError, match="nothing is frozen yet"):
        freeze.check()


def test_the_approved_inputs_pass_and_any_change_is_named(freeze_file):
    approve_now(freeze_file)
    assert freeze.check() == freeze.digest(fingerprint())
    approve_now(freeze_file, {**fingerprint(), "data/nl4opt/reviews.json": "0" * 64})
    with pytest.raises(FreezeError, match="data/nl4opt/reviews.json: changed"):
        freeze.check()


def test_a_package_that_drifted_from_the_lock_blocks_a_test_run(freeze_file, monkeypatch):
    approve_now(freeze_file)
    monkeypatch.setattr(freeze, "drifted_packages", lambda: {"cbcbox": ("2.929", "2.931")})
    with pytest.raises(FreezeError, match="cbcbox: installed 2.931, locked 2.929"):
        freeze.check()


def test_a_test_run_refuses_before_writing_anything(freeze_file, tmp_path):
    test = scorable_records("test")
    with pytest.raises(FreezeError):
        evaluate.evaluate(test, CONDITIONS, client=None, out=tmp_path / "run", split="test")
    assert not (tmp_path / "run").exists()


def test_a_test_run_is_the_whole_experiment(monkeypatch, tmp_path):
    monkeypatch.setattr(freeze, "check", lambda: "approved")
    test = scorable_records("test")
    require_whole_experiment("test", test, CONDITIONS)  # all of it: fine
    with pytest.raises(ValueError, match="all 276 scorable problems"):
        evaluate.evaluate(test[:3], CONDITIONS, client=None, out=tmp_path, split="test")
    with pytest.raises(ValueError, match="every condition"):
        require_whole_experiment("test", test, ("single-shot",))
    perturbed = load_records(GROUND_TRUTH_DIR / "test-perturbed.json")
    require_whole_experiment("test-perturbed", perturbed, CONDITIONS)


# ---- before the freeze, and approving ---------------------------------------------------


def test_the_owner_cannot_approve_yet(freeze_file):
    """While the pre-registration is a draft (test_preregistration checks it still is)."""
    with pytest.raises(FreezeError, match="still a draft"):
        freeze.approve()
    assert not freeze_file.exists()


def test_approving_writes_the_current_fingerprint(freeze_file, monkeypatch):
    monkeypatch.setattr(freeze, "unfinished", lambda: [])
    monkeypatch.setattr(freeze, "drifted_packages", lambda: {})
    monkeypatch.setattr(freeze, "git", lambda *args: "" if args[0] == "status" else "abc123")
    approval = freeze.approve(today="2026-11-02")
    assert (approval.approved_on, approval.commit) == ("2026-11-02", "abc123")
    assert approval.fingerprint == fingerprint() and freeze.check()
    assert "test runs may start" in freeze.status()


def test_uncommitted_changes_block_approval(freeze_file, monkeypatch):
    monkeypatch.setattr(freeze, "unfinished", lambda: [])
    monkeypatch.setattr(freeze, "drifted_packages", lambda: {})
    monkeypatch.setattr(freeze, "git", lambda *args: " M src/opt_agent/feedback.py")
    with pytest.raises(FreezeError, match="uncommitted changes"):
        freeze.approve()


def test_the_committed_ground_truth_is_built_from_the_current_hand_inputs():
    assert freeze.stale_ground_truth() == []


def test_a_review_applied_without_a_rebuild_is_caught(monkeypatch):
    reviews = freeze.load_reviews(freeze.REVIEWS_PATH)
    key = next(k for k in reviews if k[0] == "test")
    confirmed = {**reviews, key: reviews[key].model_copy(update={"confirmed_by_owner": True})}
    monkeypatch.setattr(freeze, "load_reviews", lambda path: confirmed)
    [stale] = freeze.stale_ground_truth()
    assert "older than the hand inputs for 1 problems" in stale  # in test.json, not perturbed


def test_status_says_what_is_left_and_that_nothing_is_approved(freeze_file, capsys):
    freeze.main([])
    printed = capsys.readouterr().out
    assert "still a draft" in printed and "Not approved yet" in printed
