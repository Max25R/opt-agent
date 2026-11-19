"""Flag every number in an explanation that nothing backs. A number is backed if it's a correct
rounding of a solver fact in the report (the objective, a value, a slack, a shadow price), of
a number in the model (a coefficient, a right-hand side, a bound), or of a number in the
problem's text. "30%" may be 30 or 0.30. Prints the unbacked numbers, one per line, and exits
1 if there are any.

    python check_explanation.py report.json model.json explanation.txt [problem.txt]

It checks where each number comes from, not whether the sentence using it is true: "10 trips
move 1,000 fish" passes whenever 10 and 1,000 are both backed. A number Claude computed (a
difference, a saving) is flagged on purpose: say it in words, or leave it out.

Standard library only.
"""

import json
import re
import sys

# "36", "1,160", "$2,333.33", "30%", "-0.5"; not digits inside names like "c0_budget".
NUMBER = re.compile(r"(?<![\w.])-?\$?\d[\d,]*(?:\.\d+)?%?")


def readings(token: str) -> list[tuple[float, int]]:
    """(value, decimal places shown) for each way to read a token."""
    digits = token.strip("$%").replace(",", "").replace("$", "")
    value = abs(float(digits))
    places = len(digits.split(".")[1]) if "." in digits else 0
    if token.endswith("%"):
        return [(value, places), (value / 100, places + 2)]
    return [(value, places)]


def rounds_to(exact: float, written: float, places: int) -> bool:
    """Is `written`, shown with `places` decimals, a correct rounding of `exact`?"""
    return abs(exact - written) <= 0.5 * 10.0**-places + 1e-9


def backed_numbers(report: dict, model: dict, problem: str = "") -> list[float]:
    facts = report.get("facts")
    if facts is None:
        raise SystemExit("the report has no facts: only a verified optimum may be explained")
    numbers = [facts["objective"], *facts["values"].values(), *facts["slack"].values()]
    numbers += list((facts.get("shadow_prices") or {}).values())
    for terms in [model["objective"]["terms"], *(c["terms"] for c in model["constraints"])]:
        numbers += [t["coef"] for t in terms]
    numbers += [c["rhs"] for c in model["constraints"]]
    numbers += [b for v in model["variables"] for b in (v.get("lower", 0), v.get("upper"))
                if b is not None]  # fmt: skip
    numbers += [value for token in NUMBER.findall(problem) for value, _ in readings(token)]
    return [abs(n) for n in numbers]


def unbacked(text: str, allowed: list[float]) -> list[str]:
    return [token for token in NUMBER.findall(text)
            if not any(rounds_to(exact, value, places)
                       for value, places in readings(token) for exact in allowed)]  # fmt: skip


def main() -> None:
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    report, model = (json.loads(open(path).read()) for path in sys.argv[1:3])
    text = open(sys.argv[3]).read()
    problem = open(sys.argv[4]).read() if len(sys.argv) == 5 else ""
    found = unbacked(text, backed_numbers(report, model, problem))
    print("\n".join(found) if found else "every number is backed")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
