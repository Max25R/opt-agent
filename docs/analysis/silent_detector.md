# A silent-failure detector, tested once (exploratory)

**Status.** The rule below was written on 2026-11-17, while the failure types
([`failure_types.md`](failure_types.md)) were being classified and before their results were
read. It was committed, with its code and tests, before the detector ran on any follow-up
answer (`git log -- docs/analysis/silent_detector.md src/opt_agent/detector.py`). It then runs
**once** over the follow-up's cached answers (`scripts/silent_detector.py` refuses to run
again), with no tuning after the results are seen. Exploratory: neither study pre-registered
it, and nothing here is a result of record.

**The idea** (the owner's): a silent failure, a verified answer that's wrong, often comes from a
model that leaves out something the text says. So: **every numeric constant in the problem
text should appear somewhere in the model, allowing simple unit conversions.** An answer whose
model misses one is flagged.

## The rule, exactly (`src/opt_agent/detector.py`)

1. **The text's constants** are the numbers written in digits: whole numbers, decimals,
   thousands separators (`1,200` is 1200), signs, and percentages (`15%`, `15 percent`).
   Not constants (fixed now, never adjusted):
   - a number that's part of a name: right after a letter or `#` (`x1`, `A2`, `#4`), or right
     after one of the naming words in `NAMING_WORDS` (`Product 1`, `Machine 2`, `Day 3`);
   - an ordinal (`5th`, `1st`);
   - a number right before `decimal`, `significant` or `digit` (answer-format instructions).
   - Number words (`two`, `twice`, `half`) aren't read: only digits count.
2. **The model's numbers** are every coefficient in the objective and the constraints, every
   right-hand side and every finite variable bound.
3. **A constant appears** if some model number equals it, up to sign, times one of these
   factors: 1; 100 and 1/100; 60 and 1/60; 3,600 and 1/3,600; 24 and 1/24; 7 and 1/7; 12 and
   1/12; 52 and 1/52; 1,000 and 1/1,000; 10^6 and 10^-6; 10^9 and 10^-9. A percentage p also
   appears as 1 + p/100 or 1 - p/100. Equal means within 1e-6, relative only (an absolute
   floor would let a tiny converted target, 25 / 10^9, match a bound at zero). Zero always
   appears (every variable has a bound at zero or is free). A number written without a
   leading digit (`.5`) isn't read.
4. **An answer is flagged** if at least one of its text's constants doesn't appear in its
   model.

## What it runs on, and what's reported

- **Answers:** every answer of the follow-up test run's three solver conditions (single-shot,
  self-correction, checklist revision), every sample, all 128 problems, that reported an
  answer (loud failures have no answer to judge). Each answer's model is the one the frozen
  pipeline makes of the cached replies (replayed in the `followup-freeze` tree, as in
  `scripts/failure_cases.py`).
- **Truth:** a **silent failure** is an answer that's wrong against the raw key, scored as in
  `runs/followup-test/followup_report.json`; a **correct answer** is one that's right.
- **Reported** (pooled over the three conditions, then per condition, for the 121 unexposed
  problems alone, the follow-up's primary set, and per distinct model):
  the silent failures it flags (true positives), the correct answers it flags (false flags),
  **precision** (flagged silent failures over all flagged answers) and **recall** (flagged
  silent failures over all silent failures), each with a 95% Wilson interval. The intervals
  treat answers as independent, which they aren't (three samples and three conditions share a
  problem), so they're too narrow; the per-model counts show by how much.
- **Exploratory, once.** The results are written to `docs/analysis/silent_detector.json` and
  summarized below, whatever they are. A weak result is reported as weak.

<!-- results: written by `python scripts/silent_detector_report.py` -->

## Results (the one run)

Run once, at `6ca49db` with no uncommitted changes (2026-11-18T03:36:17+00:00), over 1144 answers that reported one (8 loud failures left out). Exploratory.

| | Answers | Silent failures | Flagged silent | Flagged right | Precision (95% CI) | Recall (95% CI) | Right answers flagged |
|---|---:|---:|---:|---:|---:|---:|---:|
| all three conditions, pooled | 1144 | 186 | 96 | 395 | 19.6% (16.3 to 23.3) | 51.6% (44.5 to 58.7) | 41.2% |
| single-shot | 380 | 62 | 32 | 132 | 19.5% (14.2 to 26.2) | 51.6% (39.4 to 63.6) | 41.5% |
| self-correction | 384 | 65 | 32 | 132 | 19.5% (14.2 to 26.2) | 49.2% (37.5 to 61.1) | 41.4% |
| checklist revision | 380 | 59 | 32 | 131 | 19.6% (14.3 to 26.4) | 54.2% (41.7 to 66.3) | 40.8% |
| the 121 unexposed problems | 1081 | 184 | 94 | 343 | 21.5% (17.9 to 25.6) | 51.1% (43.9 to 58.2) | 38.2% |
| distinct models (one per problem and model) | 412 | 85 | 46 | 147 | 23.8% (18.4 to 30.3) | 54.1% (43.6 to 64.3) | 45.0% |

**A weak detector.** 16.3% of these answers are silent failures, so a flag picked at random would be right 16.3% of the time; this one's flags are right 19.6% of the time. It finds about half the silent failures (96 of 186) and flags 41.2% of the right answers (395 of 958), so as a warning it would mostly cry wolf: a right model needn't carry every number of the text as written (why each flagged right answer lacks its numbers wasn't checked). Nothing was tuned after the run.

**Post hoc** (after the run, joining [`failure_types.csv`](failure_types.csv), whose types are Claude's labels, not verified by a person; not part of the declared report). Flagged, of each type's silent failures: answer-key dispute 47 of 90; integrality 0 of 32; wrong objective 13 of 21; missing constraint 16 of 19; other 10 of 10; wrong number/coefficient 7 of 8; units/misread quantity 3 of 6. Of the silent failures with a model error (not a dispute), it flags 49 of 96. It can't see an integrality error by design (no number is missing), and in an answer-key dispute Claude found no model error to see.

<!-- end of results -->
