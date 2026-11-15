"""The follow-up freeze and the sealed-split loader. Ids and hashes only: no test prints,
compares or logs a sealed problem's text or key (an assertion that failed on one would print
it, so they're checked through booleans and hashes). Every approval goes to a temporary
FREEZE.json; nothing calls the API."""

import hashlib
import json
from pathlib import Path

import pytest

from opt_agent import followup, followup_freeze
from opt_agent.followup_freeze import FollowupApproval, FreezeError, fingerprint

HAVE_DATA = all(p.exists() for p in followup_freeze.data_files())
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="LLM4OR data not downloaded")

SECTION_3 = [
    "docs/FOLLOWUP_PREREGISTRATION.md", "data/followup/split.json", "requirements.lock",
    "docs/followup/judge_prompt.md",
    "data/external/llm4or-clean/Mamo_complex_lp_clean.jsonl",
    "data/external/llm4or-clean/IndustryOR.jsonl",
    "src/opt_agent/followup_report.py", "src/opt_agent/checklist.py",
    "src/opt_agent/feedback.py", "model", "api.MAX_TOKENS", "api.THINKING", "api.EFFORT",
    "temperature", "formulate.SYSTEM_PROMPT", "formulate.LP_SCHEMA", "baseline.SYSTEM_PROMPT",
    "baseline.ANSWER_SCHEMA", "checklist.SYSTEM_PROMPT", "checklist.CHECKLIST_SCHEMA",
    "explain.SYSTEM_PROMPT", "feedback.CHECKLIST_INTRO", "feedback.CHECKLIST_OUTRO",
    "seed.split", "seed.order", "seed.bootstrap", "samples", "ids.all", "ids.unexposed",
]  # fmt: skip


@pytest.fixture
def freeze_file(tmp_path, monkeypatch):
    path = tmp_path / "followup" / "FREEZE.json"
    monkeypatch.setattr(followup_freeze, "FREEZE_PATH", path)
    return path


def approve_now(path, prints=None, analysis=None) -> None:
    prints = prints or fingerprint()
    analysis = analysis or prints["src/opt_agent/followup_report.py"]
    approval = FollowupApproval(approved_on="2026-11-11", commit="abc", fingerprint=prints,
                                analysis_sha256=analysis)  # fmt: skip
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(approval.model_dump_json())


# ---- what's frozen ----------------------------------------------------------------------


def test_the_fingerprint_covers_section_3_and_all_the_code():
    prints = fingerprint()
    assert set(SECTION_3) <= set(prints)
    sources = {p.relative_to(followup_freeze.REPO_ROOT).as_posix()
               for p in followup_freeze.SOURCE_DIR.rglob("*.py")}  # fmt: skip
    assert sources <= set(prints)


def test_section_2s_id_hashes_come_from_split_json():
    labels = followup_freeze.sealed_labels()
    assert len(labels) == 128 and labels[0] == "complexlp:1" and labels[-1] == "industryor:42"
    assert followup_freeze.id_list_sha256() == followup_freeze.IDS_SHA256
    assert followup_freeze.id_list_sha256(unexposed_only=True) == followup_freeze.UNEXPOSED_SHA256


@needs_data
def test_nothing_is_left_once_the_owner_approved():
    """Approved on 2026-11-13: every section 2 hash holds and the status line isn't a draft."""
    assert followup_freeze.unfinished() == []


def test_a_draft_is_left_to_approve(monkeypatch, tmp_path):
    draft = tmp_path / "FOLLOWUP_PREREGISTRATION.md"
    text = followup_freeze.PREREGISTRATION_PATH.read_text()
    draft.write_text("**Status: DRAFT (made-up).**\n" + text)
    monkeypatch.setattr(followup_freeze, "PREREGISTRATION_PATH", draft)
    monkeypatch.setattr(followup_freeze, "_relative", lambda path: Path(path).name)
    assert any("still a draft" in item for item in followup_freeze.unfinished())


def test_a_missing_data_file_is_named(monkeypatch):
    nowhere = followup_freeze.REPO_ROOT / "data" / "external" / "no-such-directory"
    monkeypatch.setattr(followup, "DATA", nowhere)
    todo = followup_freeze.unfinished()
    assert any("Mamo_complex_lp_clean.jsonl is missing" in t for t in todo)
    missing = [name for name, sha in fingerprint().items() if sha == "missing"]
    assert sorted(missing) == sorted(followup_freeze._relative(p)
                                     for p in followup_freeze.data_files())  # fmt: skip


# ---- checking and approving -------------------------------------------------------------


def test_nothing_approved_means_no_check(freeze_file):
    with pytest.raises(FreezeError, match="isn't frozen yet"):
        followup_freeze.check()


def test_the_approved_inputs_pass(freeze_file, monkeypatch):
    monkeypatch.setattr(followup_freeze, "drifted_packages", dict)
    approve_now(freeze_file)
    assert followup_freeze.check() == followup_freeze.digest(fingerprint())


def test_any_change_is_named(freeze_file, monkeypatch):
    monkeypatch.setattr(followup_freeze, "drifted_packages", dict)
    prints = fingerprint() | {"checklist.SYSTEM_PROMPT": "0" * 64}
    approve_now(freeze_file, prints)
    with pytest.raises(FreezeError, match="checklist.SYSTEM_PROMPT: changed"):
        followup_freeze.check()


def test_the_analysis_hash_must_be_the_fingerprints(freeze_file, monkeypatch):
    monkeypatch.setattr(followup_freeze, "drifted_packages", dict)
    approve_now(freeze_file, analysis="0" * 64)
    with pytest.raises(FreezeError, match="analysis_sha256"):
        followup_freeze.check()


def test_approve_refuses_a_draft(freeze_file, monkeypatch, tmp_path):
    draft = tmp_path / "FOLLOWUP_PREREGISTRATION.md"
    draft.write_text("**Status: DRAFT (made-up).**\n")
    monkeypatch.setattr(followup_freeze, "PREREGISTRATION_PATH", draft)
    monkeypatch.setattr(followup_freeze, "_relative", lambda path: Path(path).name)
    with pytest.raises(FreezeError, match="still a draft"):
        followup_freeze.approve()
    assert not freeze_file.exists()


def test_approve_writes_the_fingerprint_and_the_analysis_hash(freeze_file, monkeypatch):
    monkeypatch.setattr(followup_freeze, "unfinished", list)
    monkeypatch.setattr(followup_freeze, "drifted_packages", dict)
    monkeypatch.setattr(followup_freeze, "git", lambda *a: "" if a[0] == "status" else "abc")
    approval = followup_freeze.approve(today="2026-11-12")
    written = json.loads(freeze_file.read_text())
    assert written["approved_on"] == "2026-11-12" and written["commit"] == "abc"
    expected = hashlib.sha256(followup_freeze.ANALYSIS_PATH.read_bytes()).hexdigest()
    assert approval.analysis_sha256 == written["analysis_sha256"] == expected
    assert followup_freeze.check()


def test_approve_refuses_uncommitted_changes(freeze_file, monkeypatch):
    monkeypatch.setattr(followup_freeze, "unfinished", list)
    monkeypatch.setattr(followup_freeze, "drifted_packages", dict)
    monkeypatch.setattr(followup_freeze, "git", lambda *a: " M x.py")
    with pytest.raises(FreezeError, match="uncommitted"):
        followup_freeze.approve()


# ---- the sealed loader ------------------------------------------------------------------


def test_load_still_refuses_the_test_splits():
    for split in followup.SEALED:
        with pytest.raises(followup.Sealed):
            followup.load(split)


def test_load_sealed_checks_the_freeze_before_reading(freeze_file, monkeypatch, tmp_path):
    # with no data file at all, the freeze error comes first: nothing was opened
    monkeypatch.setattr(followup, "COMPLEXLP", tmp_path / "nowhere.jsonl")
    with pytest.raises(FreezeError):
        followup.load_sealed("complexlp-test")


def test_load_sealed_refuses_changed_inputs(freeze_file, monkeypatch):
    monkeypatch.setattr(followup_freeze, "drifted_packages", dict)
    prints = fingerprint() | {"data/followup/split.json": "0" * 64}
    approve_now(freeze_file, prints)
    with pytest.raises(FreezeError, match="split.json: changed"):
        followup.load_sealed("industryor-test")


def test_load_sealed_refuses_other_splits():
    with pytest.raises(ValueError, match="no sealed split"):
        followup.load_sealed("complexlp-dev")


@needs_data
@pytest.mark.parametrize("split, n", [("complexlp-test", 86), ("industryor-test", 42)])
def test_load_sealed_gives_exactly_the_split_ids(split, n, monkeypatch, capsys, caplog):
    monkeypatch.setattr(followup_freeze, "check", lambda: "ok")
    problems = followup.load_sealed(split)
    benchmark = split.split("-")[0]
    assert [p.id for p in problems] == [
        str(i) for i in sorted(followup.read_split()[benchmark]["test"])
    ]
    assert len(problems) == n
    hidden = all(p.document not in repr(p) and "document" not in repr(p) for p in problems)
    assert hidden  # a bool, so a failure can't print a problem
    nonempty = all(p.document.strip() for p in problems)
    assert nonempty
    assert capsys.readouterr() == ("", "") and caplog.records == []


@needs_data
def test_both_splits_give_section_2s_hash(monkeypatch):
    monkeypatch.setattr(followup_freeze, "check", lambda: "ok")
    labels = sorted(
        (b, int(p.id)) for b in ("complexlp", "industryor")
        for p in followup.load_sealed(f"{b}-test")
    )  # fmt: skip
    text = "".join(f"{b}:{i}\n" for b, i in labels)
    assert hashlib.sha256(text.encode()).hexdigest() == followup_freeze.IDS_SHA256


# Made-up rows (not the benchmark): the loader's id and error handling.


def fake_industryor(tmp_path, monkeypatch, rows, test_lines):
    path = tmp_path / "IndustryOR.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(followup, "INDUSTRYOR", path)
    monkeypatch.setattr(followup_freeze, "check", lambda: "ok")
    split = followup.read_split() | {"industryor": {"dev": [], "test": test_lines}}
    monkeypatch.setattr(followup, "read_split", lambda: split)


def test_ids_are_line_numbers_and_must_match(tmp_path, monkeypatch):
    rows = [{"en_question": "made-up one", "en_answer": "3"},
            {"en_question": "made-up two", "en_answer": "No Best Solution"}]  # fmt: skip
    fake_industryor(tmp_path, monkeypatch, rows, [1, 2])
    problems = followup.load_sealed("industryor-test")
    assert [(p.id, p.answer) for p in problems] == [("1", 3.0), ("2", None)]
    fake_industryor(tmp_path, monkeypatch, rows, [1, 2, 3])
    with pytest.raises(ValueError, match="ids aren't split.json's"):
        followup.load_sealed("industryor-test")


def test_a_bad_row_is_named_by_id_without_its_text(tmp_path, monkeypatch):
    rows = [{"en_question": ["SECRET-TEXT"], "en_answer": "3"}]
    fake_industryor(tmp_path, monkeypatch, rows, [1])
    with pytest.raises(ValueError) as error:
        followup.load_sealed("industryor-test")
    assert "problem 1" in str(error.value) and "SECRET" not in str(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__


# ---- the tag ----------------------------------------------------------------------------
# HEAD moves on after the run (the demo changes src/ and the lock), so these read the
# approval and every frozen file from git's objects at followup-freeze, never the working
# tree. In CI they need the tag fetched (the workflow's checkout uses fetch-depth: 0).

in_git = pytest.mark.skipif(followup_freeze.git("rev-parse", "HEAD") is None,
                            reason="not a git checkout")  # fmt: skip
TAG = followup_freeze.FREEZE_TAG


@in_git
def test_the_followup_freeze_tag_holds_the_approved_inputs():
    assert followup_freeze.tag_problems() == []


@in_git
def test_the_test_run_ran_on_the_tagged_commit_and_the_approved_inputs():
    tagged = followup_freeze.git("rev-parse", f"{TAG}^{{commit}}")
    approved = followup_freeze.digest(followup_freeze.approved().fingerprint)
    log = followup_freeze.REPO_ROOT / "runs" / "followup-test" / "attempts.jsonl"
    if not log.exists():
        pytest.skip("the follow-up run isn't here")
    passes = [json.loads(line) for line in log.read_text().splitlines()]
    passes = [p for p in passes if p["kind"] == "run"]
    assert passes and all(
        (p["git_sha"], p["fingerprint"], p["git_dirty"]) == (tagged, approved, False)
        for p in passes
    )


@in_git
def test_a_commit_without_the_followup_approval_is_named():
    assert followup_freeze.tag_problems(f"{TAG}^") == [
        f"docs/followup/FREEZE.json isn't in {TAG}^ (f2bd2e3)"
    ]


@in_git
def test_a_source_file_that_differs_at_the_tag_is_named(monkeypatch):
    from opt_agent import freeze

    committed = freeze._committed

    def one_file_changed(commit: str, path: str) -> bytes | None:
        return b"changed" if path == "src/opt_agent/followup_report.py" else committed(commit, path)

    monkeypatch.setattr(freeze, "_committed", one_file_changed)
    assert followup_freeze.tag_problems() == [f"src/opt_agent/followup_report.py: differs at {TAG}"]


@in_git
def test_a_working_tree_change_doesnt_matter_to_the_tag(monkeypatch):
    """What a throwaway edit to src/ or a new dependency in the lock does: the working
    tree's fingerprint changes, the tag's doesn't."""
    real = followup_freeze.fingerprint()
    monkeypatch.setattr(followup_freeze, "fingerprint",
                        lambda: real | {"requirements.lock": "0" * 64,
                                        "src/opt_agent/web.py": "1" * 64})  # fmt: skip
    with pytest.raises(FreezeError):
        followup_freeze.check()  # a new run at HEAD is refused, as it should be
    assert followup_freeze.tag_problems() == []


@in_git
def test_a_data_file_that_isnt_the_approved_one_is_named(monkeypatch, tmp_path):
    fake = tmp_path / "IndustryOR.jsonl"
    fake.write_text("made-up\n")
    monkeypatch.setattr(followup_freeze, "data_files", lambda: [fake])
    name, real = "data/external/llm4or-clean/IndustryOR.jsonl", followup_freeze._relative
    monkeypatch.setattr(followup_freeze, "_relative", lambda p: name if p == fake else real(p))
    assert followup_freeze.tag_problems() == [f"{name}: here, but not the file approved at {TAG}"]


def test_a_missing_followup_tag_is_named():
    assert followup_freeze.tag_problems("no-such-tag")[0].startswith("no tag no-such-tag here")
