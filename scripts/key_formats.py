"""The format of the follow-up's keys, in aggregate only (owner's request, 2026-11-12).

For each benchmark's follow-up test keys: how many the old parser (`float`) reads as a
finite number, and for the rest only a shape mask (every digit -> 9, every letter -> a) with
its count; then how the pre-registered rule (followup.parse_key) reads them, as counts per
status, and how many of its values equal float's. Then their precision (2026-11-13), for the
tolerance rule: decimal places as written (0, 1, 2, 3+), and for keys that aren't whole
numbers, significant figures as written (<=3, 4, 5+). It prints no id, no line number, no
value and no problem text, so it can run while the split is sealed. It reads the data files
directly, since followup.load_sealed needs the freeze, and keeps only the key fields.

    python scripts/key_formats.py
"""

import json
import math
from collections import Counter

from opt_agent import followup


def mask(value: object) -> str:
    text = str(value)
    return "".join("9" if c.isdigit() else "a" if c.isalpha() else c for c in text)


def finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def written(value: object) -> str | None:
    """The key's number as written: its digits and point, without sign, separators or units
    (a JSON number as Python writes it). None for an exponent or an unparseable key."""
    found = followup._KEY_NUMBER.fullmatch(str(value).strip())
    if found is None or found["exponent"]:
        return None
    return "".join(c for c in found["number"] if c.isdigit() or c == ".")


def decimals(number: str) -> int:
    return len(number.split(".")[1]) if "." in number else 0


def significant_figures(number: str) -> int:
    """Digits from the first non-zero one to the last written one ("0.0450" -> 3)."""
    return len(number.replace(".", "").lstrip("0"))


def precision(values: list[object]) -> tuple[Counter, Counter, int]:
    """Counts by decimal places written, by significant figures of the non-whole keys, and
    how many keys are whole numbers (14 and "14.0" alike)."""
    places, figures, whole = Counter(), Counter(), 0
    for value in values:
        number, (_, parsed) = written(value), followup.parse_key(value)
        if number is None or parsed is None:
            places["other"] += 1
            continue
        places[min(decimals(number), 3)] += 1
        if parsed == round(parsed):
            whole += 1
        else:
            figures[min(max(significant_figures(number), 3), 5)] += 1
    return places, figures, whole


def keys(benchmark: str) -> list[object]:
    """The follow-up test keys only, in file order (no ids kept)."""
    test = {str(i) for i in followup.read_split()[benchmark]["test"]}
    if benchmark == "complexlp":
        rows = [json.loads(line) for line in followup.COMPLEXLP.read_text().splitlines()
                if line.strip()]  # fmt: skip
        return [r["Answer"] for r in rows if str(r["id"]) in test]
    lines = followup.INDUSTRYOR.read_text().splitlines()
    return [json.loads(line)["en_answer"] for n, line in enumerate(lines, start=1)
            if line.strip() and str(n) in test]  # fmt: skip


def main() -> None:
    for benchmark in ("complexlp", "industryor"):
        values = keys(benchmark)
        numbers = sum(finite(v) for v in values)
        print(f"{benchmark}: {len(values)} keys; {numbers} parse as finite numbers")
        for shape, n in sorted(Counter(mask(v) for v in values if not finite(v)).items()):
            print(f"  {n} x {shape!r}")
        parsed = [followup.parse_key(v) for v in values]
        statuses = Counter(str(status) if status else "unparseable" for status, _ in parsed)
        same = sum(
            finite(v) and value == float(v) for v, (_, value) in zip(values, parsed, strict=True)
        )
        print(f"  parse_key: {dict(sorted(statuses.items()))}; {same} values equal float's")
        places, figures, whole = precision(values)
        types = Counter(type(v).__name__ for v in values)
        print(f"  written as: {dict(sorted(types.items()))}")
        print("  decimal places written (3 = 3+): "
              f"{dict(sorted(places.items(), key=lambda kv: str(kv[0])))}")  # fmt: skip
        print(f"  whole numbers: {whole}; the other {len(values) - whole} by significant "
              f"figures (3 = <=3, 5 = 5+): {dict(sorted(figures.items()))}")  # fmt: skip


if __name__ == "__main__":
    main()
