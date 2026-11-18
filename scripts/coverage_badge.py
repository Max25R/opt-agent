"""The README's coverage badge: docs/badges/coverage.json, in shields.io's endpoint format.

After the whole suite has run under coverage with all the data (CI's reproduce job, or
locally after `python -m opt_agent.data` and `scripts/fetch_llm4or.py`), this writes the total
line coverage of src/opt_agent into the badge. With --check it writes nothing and fails if
the committed badge is more than a point off what was just measured, so the badge can't go
stale without CI going red. The number lives in the badge file, never in the README.

Run:  HYPOTHESIS_PROFILE=ci python -m coverage run -m pytest
      python scripts/coverage_badge.py            # write the badge
      python scripts/coverage_badge.py --check    # what CI runs
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BADGE = ROOT / "docs" / "badges" / "coverage.json"
SLACK = 1.0  # percentage points: the badge shows a whole number, and runs can differ a little


def measured() -> float:
    """Total line coverage of the last `coverage run`, in percent."""
    done = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--format=total", "--precision=1"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )  # fmt: skip
    return float(done.stdout.strip())


def badge(percent: float) -> dict:
    color = "brightgreen" if percent >= 90 else "green" if percent >= 80 else "yellow"
    return {"schemaVersion": 1, "label": "coverage", "message": f"{percent:.0f}%",
            "color": color}  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="compare, don't write")
    args = parser.parse_args(argv)
    now = measured()
    if args.check:
        shown = float(json.loads(BADGE.read_text())["message"].rstrip("%"))
        if abs(shown - now) > SLACK:
            raise SystemExit(f"the badge says {shown:.0f}%, coverage is {now}%: rerun "
                             "python scripts/coverage_badge.py and commit the badge")  # fmt: skip
        print(f"coverage {now}%: the badge's {shown:.0f}% is within {SLACK:.0f} point")
        return
    BADGE.parent.mkdir(parents=True, exist_ok=True)
    BADGE.write_text(json.dumps(badge(now), indent=1) + "\n")
    print(f"coverage {now}% -> {BADGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
