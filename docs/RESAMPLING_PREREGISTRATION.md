# Pre-registration: the resampling study (draft)

**Status: DRAFT (2026-11-19), not approved, not frozen, not run.** Nothing here binds until
the owner approves it, the freeze file (section 6) is written by the owner and tagged
`resampling-freeze`, and the runner it names exists and passes its tests. Until then no call
of this study is made.

**Why it exists.** The exploratory disagreement detector
([`docs/analysis/disagreement_detector.md`](analysis/disagreement_detector.md)) passed its
pre-declared screen on the follow-up's samples 0 to 2: answers that independent attempts
contradicted were silent failures far more often than chance. Its intervals treated a
problem's three samples as independent, so they were too narrow, and it was one exploratory
look. This study is the confirmatory test it called for: the same question, fresh samples, one
answer per problem, and the analysis fixed before any reply exists.

**What was known when it was written:** the detector's results on samples 0 to 2 (its doc and
JSON), the follow-up's published results, and its mean cost per answer. No reply of samples 3
to 7 exists: their cache keys have never been requested.

## 1. Hypotheses

- **R1 (primary): a disagreement flag marks silent failures.** Among the study's answers, a
  flagged answer is a silent failure more often than an unflagged one. One-sided: the
  exploratory run predicts the direction.
- **R2 (secondary): five samples' majority beats one sample.** Per problem, the majority answer
  of samples 3 to 7 is right more often than sample 3 alone. Two-sided; it doesn't decide R1.
- **Also reported, no test:** what abstaining on a flag would do (silent failures made loud,
  right answers lost), and R1 without the 13 disputed problems.

## 2. Data

- **Problems:** the follow-up's 121 unexposed test problems, exactly as in
  [`docs/FOLLOWUP_PREREGISTRATION.md`](FOLLOWUP_PREREGISTRATION.md), section 2: the same LLM4OR
  files and hashes, the same split, and the id list whose SHA-256 is
  `5ba1e23a8a4964fa5a7fc649260df00fe30ca3eae8d3c7809523dabf26698ed2`. The 7 exposed problems
  stay out.
- **Keys and scoring:** the follow-up's, unchanged (`followup.is_correct`: the raw key, 1e-4
  relative and absolute, the rounding clause for keys written with decimals). No key is
  corrected.
- **The 13 disputed problems** (`complexlp:63`, `complexlp:78`, `complexlp:81`,
  `complexlp:83`, `complexlp:94`, `industryor:17`, `industryor:22`, `industryor:24`,
  `industryor:26`, `industryor:27`, `industryor:28`, `industryor:30`, `industryor:41`; all
  unexposed): an LLM judge (Claude) flagged their keys, not verified by a person. They stay in
  the primary analysis, as keys of record, and are left out only in the secondary one.

## 3. Calls

Per problem, with the follow-up's model (`claude-haiku-5-5`), prompts and pinned settings
(`max_tokens` 16,000), only the sample number new (`Cache(dir, sample=n)`, a salted key, so a
fresh reply):

- **single-shot, samples 3, 4, 5, 6 and 7** (one formulation each, solved and checked as in
  the follow-up);
- **the no-solver baseline, sample 3.**

Six calls per problem, 726 in all. No self-correction and no checklist revision: the
checklist signal (b) costs a checklist call and a revision per answer, and is left out.

## 4. Scoring and statistics

- **The unit** is single-shot **sample 3**: one answer per problem, chosen now, not after. A
  problem whose sample 3 has no answer (a loud failure) has no unit; it's counted and
  reported, and left out of R1.
- **Silent failure:** the unit answer is wrong by the follow-up's scoring. **Right:** it's right.
- **The same answer:** the follow-up's rule (`followup_report.same_answer`): the same status
  and, for an optimum, objectives within 1e-4 relative and absolute. A sample with no answer
  differs from any answer. Five samples **agree** only if every pair does.
- **The flag:** the unit is flagged if samples 3 to 7 don't all agree (signal (a), with five
  samples), **or** if the baseline's sample 3 differs from the unit answer (signal (c)).
- **R1, the primary test:** Fisher's exact test, one-sided (flagged answers are more often
  silent failures), on the 2 x 2 table of flagged by silent, alpha 0.05. **R1 is supported if
  p < 0.05**; otherwise it's reported as not supported, with its numbers, never as "no
  effect".
- **R1's effect, reported whatever p is:** the base rate (silent failures over units), the
  flag rate, precision (silent failures over flagged units) and recall (flagged silent
  failures over silent failures), each with a 95% Wilson interval, and precision over base
  rate. With one unit per problem, the units are independent and the intervals honest.
- **R2:** exact McNemar (`stats.mcnemar_exact`), two-sided, alpha 0.05, on each problem's
  right or wrong under the two rules. The majority answer is the one at least 3 of the 5
  samples give; with none, the problem has no answer (wrong, loud).
- **Without the disputed problems:** R1's test and effect again on the units left after
  removing the 13, labeled secondary, no claim.
- **The analysis** is a script written and tested on synthetic answers before the freeze; the
  freeze records its hash. Everything in this section is what it computes.

## 5. Power (design information, not a threshold)

[`docs/resampling/power.md`](resampling/power.md) (`scripts/resampling_power.py`, seeded): with
120 units, the primary test's power is 0.96 if the flag behaves as it did on samples 0 to 2
(it fired on 61.3% of silent failures and 18.2% of right answers, at a 16.3% base rate), 0.44
if it fires on 45% and 25%, and 0.17 at 35% and 25%. Five samples can disagree more often
than three, which may raise both rates. R2 isn't powered for anything small.

## 6. Run protocol

- **Before any call:** the runner (the follow-up's `evaluate.py`, or a short script on it, for
  the calls of section 3), the analysis script and their tests are committed; a freeze file
  `docs/resampling/FREEZE.json` (the owner's step only) records the fingerprint of the code,
  the lock and the inputs, and is tagged `resampling-freeze`, like the follow-up's. The
  follow-up's own freeze stays untouched.
- **One run, from the owner's terminal,** on the frozen inputs. Problems in the follow-up's
  run order (`followup.in_run_order`); all six calls of a problem run before the next one, so
  a stopped run leaves whole problems.
- **Hard spend cap: $3.00** (`budget.BudgetedClient`). Expected cost: about **$1.44**, at the
  follow-up's mean cost per answer ($0.00206 single-shot, $0.00163 baseline;
  `runs/followup-test/results.jsonl`): 121 x (5 x $0.00206 + $0.00163). `--plan` gives the
  worst case before the run.
- **If the cap is hit:** the run stops; only problems with all six calls are analyzed; the
  shortfall is a recorded deviation, and section 5's power no longer describes the study.
- **API errors:** Amendment 1 of the M6 pre-registration, unchanged.

## 7. Deviations

Once approved and frozen, this file isn't edited. A change before the run is an amendment,
dated and tagged before any call. Anything that runs differently is recorded in
`docs/resampling/DEVIATIONS.md` with what was planned, what happened and what it changes.
Results are reported whatever they show; none goes into `results/eval.json` or
`results/followup.json`, and any number of this study in the README is checked by a test
against the study's own generated results file.
