"""Smoke-test a running demo (CI runs it against the Docker image; standard library only).

Checks that /health answers in examples mode, that /examples lists the four examples, and
that each example given with --example solves through the replay path: verified, equal to
its hand-checked answer, and every call replayed (nothing paid, and no key in the image).

Run:  python scripts/demo_smoke.py http://localhost:8000 --example paint
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

WAIT_S = 90  # the image's first start imports scipy and friends


def get(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def post(url: str, body: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})  # fmt: skip
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def wait_for(base: str) -> dict:
    deadline = time.monotonic() + WAIT_S
    while True:
        try:
            return get(f"{base}/health")
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if time.monotonic() > deadline:
                raise
            time.sleep(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Smoke-test a running demo.")
    parser.add_argument("base", help="e.g. http://localhost:8000")
    parser.add_argument("--example", action="append", default=[], help="an example's id")
    args = parser.parse_args(argv)
    base = args.base.rstrip("/")
    health = wait_for(base)
    assert health["status"] == "ok" and health["mode"] == "examples", health
    print(f"health: {health}")
    examples = {e["id"]: e for e in get(f"{base}/examples")}
    assert sorted(examples) == ["baristas", "crates", "feed", "paint"], sorted(examples)
    for name in args.example:
        example = examples[name]
        assert example["cached"], f"{name}'s replies aren't in the image"
        r = post(f"{base}/solve", {"problem": example["text"]})
        assert r["verification"]["verified"], r["stopped"]
        assert r["matches_reference"] is True, (r["objective"], example["reference_objective"])
        assert r["calls"] == r["cached_calls"] and r["paid_usd"] == 0, r
        print(f"{name}: verified, objective {r['objective']} (hand-checked "
              f"{example['reference_objective']}), {r['calls']} calls, all replayed")  # fmt: skip
    print("demo smoke test passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as failure:
        sys.exit(f"demo smoke test FAILED: {failure}")
