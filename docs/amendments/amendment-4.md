# Amendment 4: two omitted pre-registered rows, and an exploratory corrected-labels row

**Status: DRAFT (2026-11-08). Not approved, not tagged.** Drafted by Claude from the project
audit (`docs/audit/2026-11-review.md`, sections 1.1 and 1.2). Like Amendment 3, it lives
here because `docs/PREREGISTRATION.md` is frozen (`docs/FREEZE.json` hashes it).

**Post hoc.** Written after both test runs, their reports, the judges' labels, Amendment 3
and the audit. Nothing in sections 1 to 7, Amendments 1 to 3, the frozen ground truth, any
score, or the McNemar family changes. No API calls: every row below is computed from the
committed run and the committed ground truth.

## The result of record

**The result of record stays the pre-registered strict accuracy: 264 of 274 in every
condition** (96.4%, Wilson 93.4–98.0%), with the six McNemar tests and their Holm
correction as reported. Nothing in this amendment replaces, adjusts or reinterprets it.
Every other row below is either a pre-registered companion row or exploratory, and is
labeled so wherever it appears.

## 1. Two pre-registered rows the README left out

Both were computed by the frozen report code (`runs/test/report.json`) and are in
`results/eval.json`. The README's Evaluation section showed strict accuracy only, so they
weren't reported where the results are summarized. This amendment reports them; it adds no
analysis.

- **Lenient accuracy** (Amendment 2, part 4): "Every accuracy the report gives, per
  condition and subset, comes with its lenient version beside it", integrality not graded,
  so that "no headline number rests only on labels". The lenient row favors the solver
  conditions by 2 problems (`-2012603375` and `-258335120`, where both took the LP optimum
  of a problem labeled integer).
- **Accuracy without the disputed reviews** (Amendment 2, part 6): "Reported: every
  accuracy with and without the disputed problems". This row was pre-registered as a
  sensitivity row, so it keeps that label here, not "exploratory".

## 2. One exploratory row: corrected integrality labels

**Why.** The audit traced 4 of the 10 failures in every condition to the integrality rule
(`integrality.py`), not to Claude:
- The rule reads "units of X" as a divisible quantity. In 3 problems X is an ingredient of a
  countable product ("units of lychee juice" in bubble teas, "units of chocolate spread" in
  crepes, "units of chicken meat" in bowls of curry). In the 4th, X is the product itself
  ("each unit of kombucha"), but the text also counts it ("the number of wine must be larger
  than the number of kombucha").
- Each problem has strict wording ("must exceed", "must be larger than"). The ground truth
  stores a strict reading only for labels that aren't continuous
  (`ground_truth.build_record`), so the continuous label switched it off.
- Each annotated optimum is 0 under either integrality, so `integrality_matters` was false
  and no hand label was ever required.
- All three conditions answered each of the 4 with exactly its strict reading's integer
  optimum, and were scored wrong. Three structurally identical problems (`1151835649`,
  `1268238141`, `-685300642`) are rule-labeled integer and were scored with their strict
  readings.

**The rule of the row.** The problems are the ones a mechanical criterion picks: scorable,
a rule label of "continuous" that comes from the "units of" match, and strict wording. It
picks exactly these 4 (`scripts/amendment4.py` checks this). Each gets a corrected label:
`integer` for the three countable products, `either` for wine and kombucha, whose text
supports both. As in `build_record`, a label that isn't continuous brings the strict reading
with it, built by the frozen `strict.py` and solved and cross-checked the same way. Every
answer of the run is then scored again with the frozen `scoring.score`. Nothing else
changes: no other label, review, exclusion or tolerance.

**What it doesn't correct.** Amendment 3's row counts 6 shared failures as correct. The
other 2 are operator errors in NL4Opt's annotation (`-926961422`, `-2138755435`; reasons
below). Correcting them would mean repairing an annotation, which milestone 3 rules out, so
this row leaves them wrong. They stay counted as correct only in Amendment 3's row, which
rests on the judges' labels.

**Limits.**
- **Post hoc.** The criterion, and the decision to correct, came after the failures were
  seen. The criterion picks every problem with this defect, not just failures, but it was
  written knowing which ones failed.
- **One direction.** Here the correction can only add an accepted answer (the annotated
  optimum is 0 under both labels), so the row can't go down. The script refuses to run if
  any answer scored right would turn wrong.
- **A judgment.** `integer` and `either` are Claude's choices, by the owner's integrality
  criteria (countable objects and servings are integer). Both judges' taxonomy labels call
  all 4 failures `reference` (Amendment 3), but neither judge labeled their integrality.
- **The `either` label on `2078392466` is a post hoc choice with no effect on the score.**
  It was chosen while drafting this amendment, after the results were known. Its annotated
  optimum is 0 under both integralities, and `either` and `integer` both bring the strict
  reading, so the two labels accept the same answers: with `integer` instead, the row is
  still 268/274 in every condition (checked by running the script both ways).
- **No tests.** It's outside the Holm family and gets no McNemar test of its own. It moves
  all three conditions together, so it says something about accuracy and almost nothing
  about differences between conditions.
- **Not the perturbed run.** None of the 4 is in the perturbed set (do-nothing problems
  can't test memory), so the perturbed results are unaffected.

## 3. The six answer-key errors, and why each key is wrong for its text

These are the shared failures that both judges labeled `reference` (Amendment 3). The
corrected-labels row covers the first four.

1. `431521997` (integrality rule): bubble teas, labeled continuous because the text says
   "units of lychee juice". That switched off the strict reading of "the number of mango
   bubble teas made must be large than the number of lychee bubble teas made", so making
   nothing (the annotated optimum) stayed the only accepted answer.
2. `1605420061` (integrality rule): crepes, labeled continuous because the text says "units
   of chocolate spread"; the strict reading of "the number of peanut butter crepes made must
   exceed the number of chocolate crepes made" was switched off.
3. `-1540907330` (integrality rule): curry bowls, labeled continuous because the text says
   "units of chicken meat"; the strict reading of "the number of goat curry bowls must be
   larger than the number of chicken curry bowls" was switched off.
4. `2078392466` (integrality rule): wine and kombucha, labeled continuous because the text
   says "each unit of kombucha". The text also counts them ("the number of wine must be
   larger than the number of kombucha"), so the strict reading is supported and was
   switched off.
5. `-926961422` (annotated operator): "The company has a total of 6 working hours a day" is
   a limit, but the annotation says at least 6 hours. Not corrected: `nl4opt.py` checks an
   operator against the text only for comparatives, and annotation errors are never
   repaired.
6. `-2138755435` (annotated operator): "the restaurant wants to have 4000 customer
   interactions per hour" is a requirement, but the annotation says at most 4000, so the key
   is a plan with almost no service. Not corrected, for the same reason. The external
   cross-check kept it because the benchmark's edited text (400 instead of 4000) happens to
   give the same answer (Amendment 3).

## The rows

Every number and problem id in this section comes from `results/eval.json` (its
`amendment_4` and `exploratory_amendment_3` entries), and `tests/test_readme_numbers.py`
checks it, as it checks the README. Each cell is right of n, the accuracy, and its 95%
Wilson interval.

| row | label | baseline | single-shot | self-correction |
|---|---|---|---|---|
| strict accuracy | **result of record** | 264/274, 96.4% (93.4–98.0%) | 264/274, 96.4% (93.4–98.0%) | 264/274, 96.4% (93.4–98.0%) |
| lenient accuracy | pre-registered, omitted from the README | 264/274, 96.4% (93.4–98.0%) | 266/274, 97.1% (94.3–98.5%) | 266/274, 97.1% (94.3–98.5%) |
| without disputed reviews | pre-registered sensitivity, omitted from the README | 260/266, 97.7% (95.2–99.0%) | 260/266, 97.7% (95.2–99.0%) | 260/266, 97.7% (95.2–99.0%) |
| corrected labels | exploratory, post hoc | 268/274, 97.8% (95.3–99.0%) | 268/274, 97.8% (95.3–99.0%) | 268/274, 97.8% (95.3–99.0%) |
| answer-key errors counted as correct | exploratory, post hoc (Amendment 3) | 270/274, 98.5% (96.3–99.4%) | 270/274, 98.5% (96.3–99.4%) | 270/274, 98.5% (96.3–99.4%) |

The six answer-key errors (every condition gave the same answer on each):

| problem | kind | the key's answer | every condition answered | in the corrected-labels row |
|---|---|---|---|---|
| `431521997` | integrality rule | 0 | 36 | yes: the strict reading, 36 |
| `1605420061` | integrality rule | 0 | 20 | yes: the strict reading, 20 |
| `-1540907330` | integrality rule | 0 | 17 | yes: the strict reading, 17 |
| `2078392466` | integrality rule | 0 | 11 | yes: the strict reading, 11 |
| `-926961422` | annotated operator | 559600 | 14000 | no |
| `-2138755435` | annotated operator | 95 | 425 | no |

## Code

- **`scripts/amendment4.py`** computes the rows from the committed run, its frozen report
  and the committed ground truth. It checks that the criterion picks exactly the 4 corrected
  problems, that the run's strict accuracy matches the report's, and that no right answer
  turns wrong. `python scripts/amendment4.py runs/test` prints them.
- **`scripts/eval_json.py`** puts them in `results/eval.json` as `amendment_4`. Unlike
  Amendment 3's row, they aren't written into `runs/test/report.json`, so the committed
  run's files stay as they were and a report rebuild can't drop them.
- **`tests/test_amendment4.py`** checks the criterion, a corrected record's strict reading,
  the rows against the run, and that the two operator errors are listed but not corrected.
  **`tests/test_readme_numbers.py`** now checks this file's "The rows" section too.
- **No scoring code changes.** The rows use the frozen `ground_truth`, `strict` and
  `scoring` modules as they are. (`src/opt_agent/config.py` changed the same day, for the
  audit's finding on API keys. It doesn't touch scoring, but it is in the freeze
  fingerprint, so `python -m opt_agent.freeze` no longer matches at HEAD. The commit the test
  runs used is tagged `m6-freeze`.)
