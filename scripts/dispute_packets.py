"""Section 5b's key disputes: packets for the encoders and, once encodings exist, the judges'
prompts. No API calls; nothing here judges anything.

**Not run:** the owner decided on 2026-11-15 not to perform the check
(docs/followup/DEVIATIONS.md, deviation 2). The script is kept so it could be run later, as an
exploratory, post hoc check.

The problems are the ones the frozen report lists under `disputes`
(runs/followup-test/followup_report.json), by label only: this script never reads the key,
an answer, or any condition's model.

- `python scripts/dispute_packets.py` writes, for each disputed problem,
  review/followup_disputes/packets/<label>.md: the problem text and the instructions for
  writing an encoding, nothing else. The encoder (Gemini on the web, a fresh chat per
  problem; review/followup_disputes/README.md) replies with the model as JSON in the project's
  own model format, so it solves as written, with no retyping. The LLM4OR data has no stated
  license (docs/EXTERNAL_DATA.md), so packets and prompts, which hold problem text, are
  git-ignored;
  review/followup_disputes/MANIFEST.json (committed) records each packet's SHA-256 and the
  judge prompt's, so the packets can be shown to be the ones used.
- `python scripts/dispute_packets.py --prompts` fills docs/followup/judge_prompt.md with each
  problem's text and its encoding (review/followup_disputes/encodings/<label>.json, the
  encoder's reply saved as it came) into review/followup_disputes/prompts/<label>.md, ready to
  paste. Each encoding is validated first (read_encoding: the project's LPModel, a meaning for
  every variable); a problem with no encoding, or one that doesn't validate, is listed and
  skipped, so a judge never sees a model that can't be solved as written.
- encoding_model() turns a confirmed encoding into the LPModel that 5b's step 3 solves, and
  objective_constant() gives the constant to add to its objective.

The problems load only on the follow-up's frozen inputs (followup.load_test).
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from opt_agent.schema import LPModel

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runs" / "followup-test" / "followup_report.json"
JUDGE_PROMPT = ROOT / "docs" / "followup" / "judge_prompt.md"
DIR = ROOT / "review" / "followup_disputes"
PACKETS, ENCODINGS, PROMPTS = DIR / "packets", DIR / "encodings", DIR / "prompts"
MANIFEST = DIR / "MANIFEST.json"
START, END = "---- Prompt starts ----", "---- Prompt ends ----"

ENCODER_INSTRUCTIONS = """\
Write a linear or mixed-integer linear optimization model for the problem below, from its
text alone. Don't look the problem or its answer up anywhere, don't solve the model, and
don't compute its optimal value: the model is all that's asked.

Reply with one JSON object and nothing else, in exactly this form:

{
  "model": {
    "variables": [
      {"name": "trucks", "lower": 0, "upper": null, "integer": true}
    ],
    "objective": {"sense": "max", "terms": [{"var": "trucks", "coef": 3.5}]},
    "constraints": [
      {"name": "budget", "terms": [{"var": "trucks", "coef": 2}], "sense": "<=", "rhs": 100}
    ]
  },
  "objective_constant": 0,
  "meanings": {"trucks": "number of trucks bought"},
  "readings": []
}

Rules:
- Variables: "lower" and "upper" are numbers, or null for no bound (lower 0 means
  non-negative). "integer" is true for a variable that counts whole things; a yes/no choice
  is an integer with lower 0 and upper 1.
- Objective: "sense" is "min" or "max"; "terms" lists every variable with its coefficient.
  A constant in the objective (a fixed cost, say) goes in "objective_constant", not in the
  terms.
- Constraints: each has a short unique "name", its "terms" (variables and coefficients, all
  on the left), a "sense" of "<=", ">=" or "==", and a number "rhs" (all constants on the
  right).
- Every variable appears with a nonzero coefficient in the objective or some constraint, and
  every term names a declared variable.
- Numbers are plain JSON numbers: no formulas, units or thousands separators.
- "meanings" gives each variable's meaning in a few words, one entry per variable.
- "readings": where the text can be read two reasonable ways, one sentence per choice made,
  saying which reading the model takes. Otherwise an empty list.
- If the problem can't be written as a linear or mixed-integer linear model, reply instead
  with {"not_linear": "why, in one or two sentences"}.
"""


def disputed_labels(report_path: Path = REPORT) -> list[str]:
    """The labels only: the report's dispute entries also hold the key and the conditions'
    answer, which no encoder or judge may see."""
    report = json.loads(report_path.read_text())
    return sorted(d["problem"] for d in report["disputes"])


def packet(label: str, text: str) -> str:
    return (f"# Encoding packet: {label}\n\n{ENCODER_INSTRUCTIONS}\n"
            f"## The problem\n\n{text.strip()}\n")  # fmt: skip


def prompt_template() -> str:
    """The prompt part of judge_prompt.md, between its start and end lines."""
    text = JUDGE_PROMPT.read_text()
    return text.split(f"{START}\n", 1)[1].split(f"\n{END}", 1)[0]


def judge_prompt(text: str, encoding: str) -> str:
    template = prompt_template()
    assert template.count("{{PROBLEM_TEXT}}") == 1 and template.count("{{ENCODING}}") == 1
    filled = template.replace("{{PROBLEM_TEXT}}", text.strip())
    return filled.replace("{{ENCODING}}", encoding.strip()) + "\n"


def file_name(label: str, suffix: str = ".md") -> str:
    return re.sub(r"[^a-z0-9]+", "-", label) + suffix  # "complexlp:14" -> "complexlp-14.md"


def read_encoding(text: str) -> dict:
    """The encoder's reply as saved: one JSON object, optionally inside a ```json fence.
    Raises ValueError, saying why, unless it's a model in the project's format with a meaning
    for every variable (or a not_linear answer, returned as it is)."""
    fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, flags=re.DOTALL)
    data = json.loads(fenced.group(1) if fenced else text)
    if not isinstance(data, dict):
        raise ValueError("the reply isn't a JSON object")
    if set(data) == {"not_linear"}:
        return data
    allowed = {"model", "objective_constant", "meanings", "readings"}
    if set(data) - allowed or "model" not in data or "meanings" not in data:
        raise ValueError(f"the reply's keys must be {sorted(allowed)}, with model and meanings")
    model = LPModel.model_validate(data["model"])  # the solver's own checks, as Claude's get
    names = {v.name for v in model.variables}
    if set(data["meanings"]) != names:
        raise ValueError("meanings must name exactly the model's variables")
    if not isinstance(data.get("objective_constant", 0), int | float):
        raise ValueError("objective_constant must be a number")
    if not isinstance(data.get("readings", []), list):
        raise ValueError("readings must be a list")
    return data


def encoding_model(text: str) -> LPModel:
    """The LPModel that 5b's step 3 solves, straight from a confirmed encoding."""
    data = read_encoding(text)
    if "not_linear" in data:
        raise ValueError("the encoder found no linear model")
    return LPModel.model_validate(data["model"])


def objective_constant(text: str) -> float:
    """Added to the solver's objective before comparing with the key."""
    return float(read_encoding(text).get("objective_constant", 0))


def problems_by_label() -> dict[str, str]:
    from opt_agent import followup  # the frozen inputs only

    return {p.id: p.document for p in followup.load_test()}


def write_packets() -> dict:
    texts = problems_by_label()
    PACKETS.mkdir(parents=True, exist_ok=True)
    ENCODINGS.mkdir(parents=True, exist_ok=True)
    shas = {}
    for label in disputed_labels():
        content = packet(label, texts[label])
        (PACKETS / file_name(label)).write_text(content)
        shas[label] = hashlib.sha256(content.encode()).hexdigest()
    manifest = {
        "problems": len(shas),
        "packet_sha256": shas,
        "judge_prompt_sha256": hashlib.sha256(JUDGE_PROMPT.read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def write_prompts() -> tuple[list[str], list[str]]:
    texts = problems_by_label()
    PROMPTS.mkdir(parents=True, exist_ok=True)
    done, waiting = [], []
    for label in disputed_labels():
        encoding = ENCODINGS / file_name(label, ".json")
        if not encoding.exists() or not encoding.read_text().strip():
            waiting.append(f"{label} (no encoding)")
            continue
        try:
            data = read_encoding(encoding.read_text())
        except ValueError as invalid:  # pydantic's ValidationError is a ValueError
            waiting.append(f"{label} (invalid: {str(invalid).splitlines()[0]})")
            continue
        if "not_linear" in data:
            waiting.append(f"{label} (the encoder says it isn't linear)")
            continue
        pretty = json.dumps(data, indent=1)  # what the judge reads: the reply, laid out
        (PROMPTS / file_name(label)).write_text(judge_prompt(texts[label], pretty))
        done.append(label)
    return done, waiting


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Section 5b's packets and judge prompts.")
    parser.add_argument("--prompts", action="store_true",
                        help="fill the judge prompt for each problem with an encoding")  # fmt: skip
    args = parser.parse_args(argv)
    if args.prompts:
        done, waiting = write_prompts()
        print(f"{len(done)} judge prompts in {PROMPTS.relative_to(ROOT)}; "
              f"not ready: {'; '.join(waiting) or 'none'}")  # fmt: skip
        return
    manifest = write_packets()
    print(f"{manifest['problems']} packets in {PACKETS.relative_to(ROOT)} (git-ignored); "
          f"hashes in {MANIFEST.relative_to(ROOT)}")  # fmt: skip


if __name__ == "__main__":
    main()
