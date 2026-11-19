"""The Agent Skill (skills/opt-agent/): its frontmatter, that its helper scripts need only PuLP,
SciPy and the standard library, and that they verify one of the demo's cached examples and
back its explanation, run as a user would run them (`python -I`, outside this package). Also
the repository's plugin marketplace entry for it. No API calls: the example replays from the
committed replies."""

import ast
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from opt_agent.api import Cache, ReplayOnlyClient
from opt_agent.demo import app, examples, pipeline

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "opt-agent"
SCRIPTS = SKILL / "scripts"
spec = importlib.util.spec_from_file_location("solve_and_check", SCRIPTS / "solve_and_check.py")
solve_and_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solve_and_check)


def run(script: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, cwd=SKILL)  # fmt: skip


@pytest.fixture(scope="module")
def paint(tmp_path_factory) -> dict:
    """The paint example, replayed from its committed replies: Claude's model, its
    explanation, and the project's own verified result to compare with."""
    example = examples.BY_ID["paint"]
    result = pipeline.solve(example.text, ReplayOnlyClient(), Cache(app.REPLIES))
    assert result.verified and result.explanation is not None
    folder = tmp_path_factory.mktemp("skill")
    files = {"model": folder / "model.json", "explanation": folder / "explanation.txt",
             "problem": folder / "problem.txt", "report": folder / "report.json"}  # fmt: skip
    files["model"].write_text(json.dumps(result.formulation.model.model_dump(mode="json")))
    files["explanation"].write_text(result.explanation.text)
    files["problem"].write_text(example.text)
    return {"files": files, "result": result}


def test_the_skill_has_its_frontmatter_and_points_to_the_results():
    text = (SKILL / "SKILL.md").read_text()
    front = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert front is not None
    fields = dict(line.split(": ", 1) for line in front.group(1).splitlines())
    assert re.fullmatch(r"[a-z0-9-]{1,64}", fields["name"]) and fields["name"] == SKILL.name
    assert 0 < len(fields["description"]) <= 1024 and not re.search("[<>]", fields["description"])
    assert "https://github.com/Max25R/opt-agent#results" in text
    assert "silent" in text and len(text.splitlines()) < 100  # short, and it warns


def test_the_helpers_need_only_pulp_scipy_and_the_standard_library():
    allowed = set(sys.stdlib_module_names) | {"pulp", "scipy", "numpy"}
    for script in SCRIPTS.glob("*.py"):
        tree = ast.parse(script.read_text())
        modules = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names}  # fmt: skip
        modules |= {node.module for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom) and node.module}  # fmt: skip
        assert {m.split(".")[0] for m in modules} <= allowed, script.name


def test_the_helpers_verify_a_cached_example_and_back_its_explanation(paint):
    files, result = paint["files"], paint["result"]
    solved = run("solve_and_check.py", files["model"])
    assert solved.returncode == 0, solved.stdout + solved.stderr
    files["report"].write_text(solved.stdout)
    report = json.loads(solved.stdout)
    assert report["verified"] and report["solvers_agree"] and report["check_problems"] == []
    facts = report["facts"]
    assert facts["objective"] == pytest.approx(result.solution.objective)
    assert facts["values"] == pytest.approx(result.solution.values)
    assert facts["shadow_prices"] == pytest.approx(result.solution.duals)  # an LP: duals too
    checked = run("check_explanation.py", files["report"], files["model"],
                  files["explanation"], files["problem"])  # fmt: skip
    assert checked.returncode == 0, checked.stdout
    assert result.explanation.unsupported_numbers == []  # the project's checker agrees


def test_an_invented_number_is_flagged(paint, tmp_path):
    files = paint["files"]
    if not files["report"].exists():
        files["report"].write_text(run("solve_and_check.py", files["model"]).stdout)
    claim = tmp_path / "claim.txt"
    claim.write_text("Make 150 litres of Interior paint for $1,600, $37 more than last week.")
    checked = run("check_explanation.py", files["report"], files["model"], claim, files["problem"])
    assert checked.returncode == 1 and checked.stdout.split() == ["$37"]


def test_duals_that_dont_prove_the_optimum_fail_the_certificate(paint):
    model = solve_and_check.load(paint["files"]["model"].read_text())
    cbc = solve_and_check.solve_cbc(model)
    assert solve_and_check.certificate(model, cbc) == []
    wrong = cbc | {"duals": {name: 0.0 for name in cbc["duals"]}}
    assert solve_and_check.certificate(model, wrong) != []


def test_an_infeasible_model_is_not_verified(paint):
    model = json.loads(paint["files"]["model"].read_text())
    first = model["variables"][0]["name"]
    model["constraints"].append({"name": "impossible", "sense": ">=", "rhs": 1e6,
                                 "terms": [{"var": first, "coef": 1}]})  # fmt: skip
    report = solve_and_check.report(solve_and_check.load(json.dumps(model)))
    assert not report["verified"] and (report["cbc"], report["highs"]) == ("infeasible",) * 2


def test_the_repository_is_a_marketplace_for_the_skill():
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert market["name"] and market["owner"]["name"]
    (entry,) = market["plugins"]
    assert entry["name"] == "opt-agent" and entry["source"] == "./skills/opt-agent"
    assert ".." not in entry["source"] and (ROOT / entry["source"] / "SKILL.md").is_file()
    anchor = entry["homepage"].split("#")[1]
    assert anchor == "use-it-as-an-agent-skill"
    assert "\n## Use it as an Agent Skill\n" in (ROOT / "README.md").read_text()
