"""Pinned downloads of external datasets: a fixed revision and a SHA-256 for every file.

Run:  python -m opt_agent.data

Files land under data/ and are git-ignored. Pinning means a re-run gets byte-identical
inputs; if a source ever changes, the checksum fails loudly instead of silently shifting
the ground truth.
"""

import hashlib
import ssl
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import certifi

DATA_DIR = Path("data")
NL4OPT_COMMIT = "49f1e0d66b7fdcd33305a7f281c2a7c13f5620ea"
ORLM_REVISION = "98da4f57462f03c0c8d44211647be87acd649d20"

_NL4OPT = f"https://raw.githubusercontent.com/nl4opt/nl4opt-competition/{NL4OPT_COMMIT}"
_ORLM = f"https://huggingface.co/datasets/CardinalOperations/NL4OPT/resolve/{ORLM_REVISION}"


@dataclass(frozen=True)
class Source:
    path: str  # relative to the data directory
    url: str
    sha256: str


NL4OPT_DEV = Source(
    "nl4opt/raw/dev.jsonl",
    f"{_NL4OPT}/generation_data/dev.jsonl",
    "6538ce1fe76861f89879672a6c9a02c8f41156952256f3cfde82c2808ba320ee",
)
NL4OPT_TEST = Source(
    "nl4opt/raw/test.jsonl",
    f"{_NL4OPT}/generation_data/test.jsonl",
    "2a4a20a11935aacc99068ee4207d5265f15c0b387d4720c548c196d8ff2fcf5b",
)
# ORLM's answers: GPT-4 turned the annotations into programs and solved them. Used only as a
# cross-check, never as ground truth. License: CC BY-NC 4.0, so it's never committed here.
ORLM_ANSWERS = Source(
    "thirdparty/orlm/NL4OPT_with_optimal_solution.json",
    f"{_ORLM}/NL4OPT_with_optimal_solution.json",
    "3ff8bb26595ae65c9a115ea3f578086007e10475e0ef7f508707558058f2d8a2",
)
SOURCES = [NL4OPT_DEV, NL4OPT_TEST, ORLM_ANSWERS]


def fetch(source: Source, data_dir: Path = DATA_DIR) -> Path:
    """Download a source unless an intact copy is already there; return its path."""
    target = data_dir / source.path
    if target.exists() and _sha256(target.read_bytes()) == source.sha256:
        return target
    # certifi's CA bundle: python.org's macOS Python ships without one, so HTTPS would fail.
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(source.url, timeout=60, context=context) as response:
        content = response.read()
    if _sha256(content) != source.sha256:
        raise RuntimeError(f"{source.url} doesn't match its pinned SHA-256; refusing to use it")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


if __name__ == "__main__":
    for source in SOURCES:
        print(f"ok  {fetch(source)}")
