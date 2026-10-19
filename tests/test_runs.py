import json
import subprocess

from opt_agent.runs import PACKAGES, REPO_ROOT, Run, Tags, environment


def test_a_run_starts_with_what_it_ran_on(tmp_path):
    log = tmp_path / "run.jsonl"
    run = Run.start(log_path=log)
    [header] = [json.loads(line) for line in log.read_text().splitlines()]
    assert header["kind"] == "run" and header["run_id"] == run.run_id
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                          text=True).stdout.strip()  # fmt: skip
    assert header["git_sha"] == head
    assert isinstance(header["git_dirty"], bool)
    assert set(header["packages"]) == set(PACKAGES)
    assert header["packages"]["anthropic"] and header["packages"]["cbcbox"] == "2.929"


def test_tags_go_on_every_line(tmp_path):
    log = tmp_path / "run.jsonl"
    Run(log_path=log).write("attempt", Tags(problem_id="1", split="dev"), attempt=1)
    [line] = [json.loads(x) for x in log.read_text().splitlines()]
    assert (line["problem_id"], line["split"], line["condition"]) == ("1", "dev", None)
    assert line["attempt"] == 1


def test_without_a_log_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Run.start().write("attempt", attempt=1)
    assert list(tmp_path.iterdir()) == []


def test_environment_survives_a_missing_git(monkeypatch):
    def no_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", no_git)
    assert environment()["git_sha"] is None and environment()["git_dirty"] is None
