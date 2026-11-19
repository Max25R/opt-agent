"""The demo (opt_agent.demo): the examples, both modes and the live-mode guards. Every reply
comes from tests/fakes.FakeClient or from a cache it wrote to a temporary directory; nothing
calls the API."""

import json
import re

import pytest
from fakes import GAS_PROBLEM, GAS_REPLY, GOOD_EXPLANATION, FakeClient
from fastapi.testclient import TestClient
from pytest import approx

from opt_agent import api, formulate
from opt_agent.api import Cache, NotCached, ReplayOnlyClient
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError
from opt_agent.demo import app as demo_app
from opt_agent.demo import examples, pipeline
from opt_agent.demo.app import Settings, create_app
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.highs import solve_with_highs
from opt_agent.schema import LPModel
from opt_agent.solver import Status, solve

PAINT = examples.BY_ID["paint"]


def model(variables, sense, objective, constraints, integer=False) -> dict:
    return {
        "variables": [{"name": v, "lower": 0, "upper": None, "integer": integer}
                      for v in variables],
        "objective": {"sense": sense, "terms": [{"var": v, "coef": c}
                                                for v, c in objective.items()]},
        "constraints": [{"name": name, "terms": [{"var": v, "coef": c} for v, c in terms.items()],
                         "sense": op, "rhs": rhs} for name, terms, op, rhs in constraints],
    }  # fmt: skip


DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
NEED = [10, 8, 9, 9, 12, 15, 14]
COST = {("a", "north"): 4, ("a", "central"): 6, ("a", "south"): 9,
        ("b", "north"): 7, ("b", "central"): 3, ("b", "south"): 5}  # fmt: skip
SHIP = {f"{w}_{s}": c for (w, s), c in COST.items()}

# The hand-written model of each example, as its text reads.
REFERENCE_MODELS = {
    "paint": model(["interior", "exterior"], "max", {"interior": 4, "exterior": 5}, [
        ("mixing hours", {"interior": 0.5, "exterior": 0.25}, "<=", 125),
        ("pigment kg", {"interior": 0.2, "exterior": 0.4}, "<=", 110),
        ("exterior sales", {"exterior": 1}, "<=", 250),
    ]),
    "baristas": model([f"start_{d}" for d in DAYS], "min", {f"start_{d}": 1 for d in DAYS}, [
        (f"cover {d}", {f"start_{DAYS[(i - k) % 7]}": 1 for k in range(5)}, ">=", NEED[i])
        for i, d in enumerate(DAYS)
    ], integer=True),
    "crates": model(list(SHIP), "min", SHIP, [
        ("supply a", {f"a_{s}": 1 for s in ("north", "central", "south")}, "<=", 300),
        ("supply b", {f"b_{s}": 1 for s in ("north", "central", "south")}, "<=", 250),
        ("north", {"a_north": 1, "b_north": 1}, ">=", 180),
        ("central", {"a_central": 1, "b_central": 1}, ">=", 200),
        ("south", {"a_south": 1, "b_south": 1}, ">=", 150),
    ], integer=True),
    "feed": model(["corn", "soy", "oats"], "min", {"corn": 0.30, "soy": 0.80, "oats": 0.20}, [
        ("total kg", {"corn": 1, "soy": 1, "oats": 1}, "==", 1000),
        ("protein kg", {"corn": 0.10, "soy": 0.45, "oats": 0.10}, ">=", 170),
        ("fiber kg", {"corn": 0.03, "soy": 0.06, "oats": 0.11}, "<=", 60),
    ]),
    # The fix-step candidates: loaves, vans and furniture are whole things.
    "bakery": model(["sourdough", "rye"], "max", {"sourdough": 3, "rye": 2.5}, [
        ("oven minutes", {"sourdough": 20, "rye": 15}, "<=", 480),
        ("flour kg", {"sourdough": 0.5, "rye": 0.4}, "<=", 30),
        ("cafe contract", {"rye": 1}, ">=", 10),
        ("rye sales", {"rye": 1}, "<=", 24),
    ], integer=True),
    "fleet": model(["electric", "diesel"], "min", {"electric": 40_000, "diesel": 30_000}, [
        ("budget", {"electric": 40_000, "diesel": 30_000}, "<=", 1_200_000),
        ("vans", {"electric": 1, "diesel": 1}, ">=", 35),
        ("electric share", {"electric": 0.6, "diesel": -0.4}, ">=", 0),
    ], integer=True),
    "furniture": model(["tables", "chairs"], "max", {"tables": 120, "chairs": 45}, [
        ("carpentry minutes", {"tables": 90, "chairs": 30}, "<=", 3 * 40 * 60),
        ("finishing minutes", {"tables": 20, "chairs": 15}, "<=", 40 * 60),
        ("school order", {"chairs": 1}, ">=", 20),
    ], integer=True),
}  # fmt: skip


# ---- the examples -----------------------------------------------------------------------


@pytest.mark.parametrize("example", examples.EXAMPLES + examples.FIX_STEP_CANDIDATES,
                         ids=lambda e: e.id)  # fmt: skip
def test_each_reference_answer_is_its_hand_written_models_optimum(example):
    lp = LPModel.model_validate(REFERENCE_MODELS[example.id])
    cbc, highs = solve(lp), solve_with_highs(lp)
    assert cbc.status is highs.status is Status.OPTIMAL
    assert cbc.objective == approx(example.reference_objective)
    assert highs.objective == approx(example.reference_objective)
    relaxed = lp.model_copy(update={"variables": [v.model_copy(update={"integer": False})
                                                  for v in lp.variables]})  # fmt: skip
    integrality_matters = solve(relaxed).objective != approx(example.reference_objective)
    assert integrality_matters == example.integer  # only the baristas: LP 15.4, integer 16


def eight_word_runs(text: str) -> set[tuple[str, ...]]:
    """Every run of 8 words, punctuation dropped on both sides, so a comma can't hide one."""
    words = re.findall(r"[a-z0-9$.%]+", text.lower())
    return {tuple(words[i:i + 8]) for i in range(len(words) - 7)}  # fmt: skip


def benchmark_texts() -> dict[str, list[str]]:
    """Every benchmark problem text this checkout has: NL4Opt (committed), and where they've
    been fetched (python -m opt_agent.data, scripts/fetch_llm4or.py; CI's reproduce job has
    them all), ORLM's and ORLMBenchmark's NL4Opt and LLM4OR's three cleaned benchmarks."""
    root = GROUND_TRUTH_DIR.parents[1]  # data/
    texts = {"NL4Opt": [r.document for split in ("dev", "test")
                        for r in load_records(GROUND_TRUTH_DIR / f"{split}.json")]}  # fmt: skip

    def lines(path, field):
        if path.exists():
            return [json.loads(line)[field] for line in path.read_text().splitlines() if line]
        return None

    llm4or = root / "external" / "llm4or-clean"
    found = {
        "ORLM's NL4Opt": lines(root / "thirdparty/orlm/NL4OPT_with_optimal_solution.json",
                               "en_question"),
        "ORLMBenchmark's NL4Opt": lines(root / "thirdparty/orlmbench/NL4OPT.jsonl", "en_question"),
        "IndustryOR": lines(llm4or / "IndustryOR.jsonl", "en_question"),
        "ComplexLP": lines(llm4or / "Mamo_complex_lp_clean.jsonl", "Question"),
        "LLM4OR's NL4Opt": [p.read_text() for p in sorted(llm4or.glob("NL4Opt/*/description.txt"))]
        or None,
    }  # fmt: skip
    return texts | {name: t for name, t in found.items() if t}


def test_the_examples_are_four_kinds_and_none_is_benchmark_text():
    assert [e.kind for e in examples.EXAMPLES] == [
        "production mix", "staffing", "transportation", "blending"]  # fmt: skip
    assert any(e.integer for e in examples.EXAMPLES)
    sources = {name: set().union(*map(eight_word_runs, texts))
               for name, texts in benchmark_texts().items()}  # fmt: skip
    for e in examples.EXAMPLES + examples.FIX_STEP_CANDIDATES:
        mine = eight_word_runs(e.text)
        for name, runs in sources.items():
            assert not mine & runs, f"{e.id} shares 8 words in a row with a {name} problem"
        assert len(e.text) <= pipeline.MAX_PROBLEM_CHARS


def test_the_eight_word_check_sees_through_punctuation():
    text = "Each batch of paint needs 3 hours, 2 litres of base, and a crate."
    assert eight_word_runs(text) & eight_word_runs(text.replace(",", ""))


# ---- fake replies for one solve ---------------------------------------------------------


def paint_replies() -> list[str]:
    """What Claude might say in one demo solve of the paint example, call by call:
    the formulation, the direct estimate, the checklist and the explanation."""
    checklist = {
        "variables": [
            {"name": "interior", "kind": "continuous", "quote": "litres of Interior paint"},
            {"name": "exterior", "kind": "continuous", "quote": "litres of Exterior paint"},
        ],
        "objective": {"sense": "max", "terms": [{"var": "interior", "coef": 4},
                                                {"var": "exterior", "coef": 5}],
                      "quote": "maximize profit"},
        "requirements": [
            {"quote": "125 hours of mixing time", "terms": [{"var": "interior", "coef": 0.5},
             {"var": "exterior", "coef": 0.25}], "sense": "<=", "rhs": 125, "strict": False,
             "could_be_equal": False, "scope": "combined"},
            {"quote": "110 kg of pigment", "terms": [{"var": "interior", "coef": 0.2},
             {"var": "exterior", "coef": 0.4}], "sense": "<=", "rhs": 110, "strict": False,
             "could_be_equal": False, "scope": "combined"},
            {"quote": "at most 250 litres of Exterior paint", "terms": [{"var": "exterior",
             "coef": 1}], "sense": "<=", "rhs": 250, "strict": False,
             "could_be_equal": False, "scope": "single"},
        ],
        "not_requirements": [],
        "cannot_express": [],
    }  # fmt: skip
    explanation = (
        "Make 150 litres of Interior paint and 200 litres of Exterior paint, for a "
        "profit of $1,600. Both the 125 hours of mixing time and the 110 kg of "
        "pigment are used up; the Exterior limit of 250 litres has 50 to spare."
    )
    return [json.dumps(REFERENCE_MODELS["paint"]), '{"status": "optimal", "objective": 1600}',
            json.dumps(checklist), explanation]  # fmt: skip


@pytest.fixture
def replies(tmp_path):
    """A replies directory with the paint example cached, the way cache_examples.py does it
    but with FakeClient's replies."""
    directory = tmp_path / "replies"
    client = FakeClient(*paint_replies())
    pipeline.solve(PAINT.text, client, Cache(directory))
    assert client.replies == []  # the whole solve used exactly these four calls
    return directory


def examples_app(replies_dir) -> TestClient:
    return TestClient(create_app(Settings(mode="examples", replies=replies_dir)))


def live_app(tmp_path, client, replies_dir=None) -> TestClient:
    settings = Settings(mode="live", api_key="unused", ledger=tmp_path / "ledger.jsonl",
                        live_cache=tmp_path / "live", log=tmp_path / "log.jsonl",
                        replies=replies_dir or tmp_path / "no-replies")  # fmt: skip
    return TestClient(create_app(settings, client=client))


# ---- examples mode ----------------------------------------------------------------------


def test_the_page_health_and_examples(tmp_path, replies):
    web = examples_app(replies)
    assert "<title>opt-agent demo</title>" in web.get("/").text
    health = web.get("/health").json()
    assert (health["status"], health["mode"], health["examples_cached"]) == ("ok", "examples", 1)
    assert health["max_tokens"] == pipeline.MAX_TOKENS == 8_000
    listed = web.get("/examples").json()
    assert [e["id"] for e in listed] == ["paint", "baristas", "crates", "feed"]
    assert [e["cached"] for e in listed] == [True, False, False, False]


def test_an_example_replays_from_its_cache_and_sends_nothing(replies):
    response = examples_app(replies).post("/solve", json={"problem": PAINT.text + "\n"})
    assert response.status_code == 200
    r = response.json()
    assert r["mode"] == "examples" and r["example"] == "paint"
    assert r["verification"]["verified"] and r["verification"]["solvers_agree"]
    assert r["objective"] == approx(1600) and r["matches_reference"] is True
    assert r["values"] == approx({"interior": 150, "exterior": 200})
    assert sorted(r["binding"]) == ["mixing hours", "pigment kg"]
    assert r["explanation"].startswith("Make 150 litres") and r["explanation_unsupported"] == []
    assert r["low_confidence"] is False and r["checklist_flags"] == []
    assert (r["calls"], r["cached_calls"], r["paid_usd"]) == (4, 4, 0)
    assert r["model_lines"][0] == "max 4*[interior] + 5*[exterior]"


def test_examples_mode_answers_nothing_else(replies):
    web = examples_app(replies)
    response = web.post("/solve", json={"problem": PAINT.text.replace("$4", "$6")})
    assert response.status_code == 404 and "examples mode" in response.json()["detail"]
    uncached = web.post("/solve", json={"problem": examples.BY_ID["feed"].text})
    assert uncached.status_code == 503 and "aren't cached yet" in uncached.json()["detail"]


def test_the_replay_only_client_never_sends():
    with pytest.raises(NotCached):
        api.call(ReplayOnlyClient(), formulate.build_request("x", pipeline.MODEL))


# ---- live mode --------------------------------------------------------------------------


def gas_replies() -> list[str]:
    checklist = json.dumps({"variables": [], "objective": None, "requirements": [],
                            "not_requirements": [], "cannot_express": []})  # fmt: skip
    return [GAS_REPLY, '{"status": "optimal", "objective": 251}', checklist, GOOD_EXPLANATION]


def test_live_mode_solves_with_every_reply_capped(tmp_path):
    client = FakeClient(*gas_replies())
    response = live_app(tmp_path, client).post("/solve", json={"problem": GAS_PROBLEM})
    assert response.status_code == 200, response.text
    r = response.json()
    assert r["mode"] == "live" and r["verification"]["verified"]
    assert r["objective"] == approx(251) and r["reference_objective"] is None
    assert len(client.requests) == 4
    assert {req["max_tokens"] for req in client.requests} == {pipeline.MAX_TOKENS}
    assert r["paid_usd"] > 0 and r["cached_calls"] == 0
    assert (tmp_path / "log.jsonl").exists()  # live calls are logged


def test_a_live_answer_asked_again_replays(tmp_path):
    client = FakeClient(*gas_replies())
    web = live_app(tmp_path, client)
    web.post("/solve", json={"problem": GAS_PROBLEM})
    again = web.post("/solve", json={"problem": GAS_PROBLEM}).json()
    assert again["cached_calls"] == again["calls"] == 4 and again["paid_usd"] == 0


def test_live_mode_replays_the_examples_without_the_client(tmp_path, replies):
    client = FakeClient()  # any call would fail the test
    r = live_app(tmp_path, client, replies).post("/solve", json={"problem": PAINT.text}).json()
    assert r["mode"] == "live" and r["matches_reference"] is True and client.requests == []


def test_a_long_or_empty_problem_is_refused_before_any_call(tmp_path):
    client = FakeClient()
    web = live_app(tmp_path, client)
    too_long = web.post("/solve", json={"problem": "x" * (pipeline.MAX_PROBLEM_CHARS + 1)})
    assert too_long.status_code == 413
    assert web.post("/solve", json={"problem": "   "}).status_code == 422
    assert client.requests == []


def test_live_mode_solves_one_problem_at_a_time(tmp_path):
    client = FakeClient(*gas_replies())
    web = live_app(tmp_path, client)
    with web.app.state.one_at_a_time:  # as if another solve were running
        busy = web.post("/solve", json={"problem": GAS_PROBLEM})
    assert busy.status_code == 429 and client.requests == []
    assert web.post("/solve", json={"problem": GAS_PROBLEM}).status_code == 200


def test_the_dollar_cap_stops_live_calls_before_they_are_sent(tmp_path):
    fake = FakeClient(*gas_replies())
    capped = BudgetedClient(fake, Budget(0.000_01))
    response = live_app(tmp_path, capped).post("/solve", json={"problem": GAS_PROBLEM})
    assert response.status_code == 503 and "no more live calls" in response.json()["detail"]
    assert fake.requests == []


# ---- the mode and the cap ---------------------------------------------------------------


def test_the_mode_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env here
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPT_AGENT_LIVE", raising=False)
    assert Settings.from_env().mode == "examples"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-made-up")
    assert Settings.from_env().mode == "examples"  # a key alone never turns live mode on
    monkeypatch.setenv("OPT_AGENT_LIVE", "1")
    monkeypatch.setenv(demo_app.CAP_VAR, "0.10")
    live = Settings.from_env()
    assert (live.mode, live.api_key, live.cap_usd) == ("live", "sk-made-up", 0.10)
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    with pytest.raises(MissingAPIKeyError):
        Settings.from_env()  # live mode with no key doesn't start


def test_the_max_tokens_cap_holds_only_inside_its_block():
    assert api.max_tokens() == api.MAX_TOKENS == 16_000
    with api.max_tokens_cap(8_000):
        assert formulate.build_request("x", pipeline.MODEL)["max_tokens"] == 8_000
        with api.max_tokens_cap(50_000):
            assert api.max_tokens() == api.MAX_TOKENS  # a cap never raises the limit
    assert formulate.build_request("x", pipeline.MODEL)["max_tokens"] == api.MAX_TOKENS


# ---- the image --------------------------------------------------------------------------


def test_the_image_never_gets_the_key_the_data_or_the_runs():
    root = demo_app.HERE.parents[2]
    ignored = (root / ".dockerignore").read_text().split()
    assert {".env", ".env.*", "runs/", "data/", ".venv/", "logs/"} <= set(ignored)
    dockerfile = (root / "Dockerfile").read_text()
    assert "COPY . " not in dockerfile  # only named files and src/ go in
    assert 'CMD ["python", "-m", "opt_agent.demo", "--host", "0.0.0.0"' in dockerfile


# ---- the committed replies --------------------------------------------------------------


@pytest.mark.parametrize("example", examples.EXAMPLES, ids=lambda e: e.id)
def test_each_committed_example_replays_and_matches_its_hand_checked_answer(example):
    """The replies scripts/cache_examples.py wrote (the owner's paid run, 2026-11-15) replay
    with no client at all, every call from the cache. A change to a prompt or a setting
    would miss them: re-cache, never edit them."""
    result = pipeline.solve(example.text, ReplayOnlyClient(), Cache(demo_app.REPLIES))
    r = pipeline.to_response(result, "examples", example)
    assert r.verification.verified and r.matches_reference is True
    assert r.calls == r.cached_calls and r.paid_usd == 0
