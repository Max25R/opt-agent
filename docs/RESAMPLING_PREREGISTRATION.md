# Pre-registration: the resampling study

**Status: APPROVED (owner, 2026-11-19, in chat), with the three edits the owner asked for
made here before the freeze (R1's units, missing answers, the same settings as the
follow-up). Frozen by `docs/resampling/FREEZE.json`, tagged `resampling-freeze`.** The runner
and the analysis it names were committed, with their tests, before the freeze, and no call of
this study was made before it.

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

- **R1 (primary): a disagreement flag marks silent failures.** Among the answers the agent
  would report (verified sample-3 answers, section 4), a flagged answer is wrong more often
  than an unflagged one. One-sided: the exploratory run predicts the direction.
- **R2 (secondary): five samples' majority beats one sample.** Per problem, the majority answer
  of samples 3 to 7 is right more often than sample 3 alone. Two-sided; it doesn't decide R1.
- **Also reported, no test:** what abstaining on a flag would do (silent failures made loud,
  right answers lost), and R1 without the 13 disputed problems.

## 2. Data

- **Problems:** the follow-up's 121 unexposed test problems, exactly as in
  [`docs/FOLLOWUP_PREREGISTRATION.md`](FOLLOWUP_PREREGISTRATION.md), section 2: the same LLM4OR
  files and hashes (`Mamo_complex_lp_clean.jsonl`,
  `28e10dff1146ff635673293b5730abb3d7efa2f7bbe91de60fe67b729dfe7a0d`; `IndustryOR.jsonl`,
  `d7c2c05377ade5bc6a401ebf3075f0e00fa91068439761e5b46fa3045ffc19b5`), the same split
  (`data/followup/split.json`,
  `c37ecc0e93f16d0e496e5c2b95d8d8f4c477d92220205e63d73e5cbe4e0a3203`), and the id list of
  the 121 whose SHA-256 is
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

## 3. Calls, and the same settings as the follow-up

Per problem: **single-shot, samples 3, 4, 5, 6 and 7** (one formulation each, solved and checked
as in the follow-up), and **the no-solver baseline, sample 3.** Six calls per problem, 726 in
all. No self-correction and no checklist revision: the checklist signal (b) costs a checklist
call and a revision per answer, and is left out.

**The same model, prompts and `max_tokens` as the follow-up, by design.** The model is
`claude-haiku-5-5`; the formulation and baseline prompts and schemas are the follow-up's
(`formulate.SYSTEM_PROMPT` and `LP_SCHEMA`, `baseline.SYSTEM_PROMPT` and `ANSWER_SCHEMA`);
`max_tokens` is 16,000; thinking and effort are pinned as there (`api.THINKING`, `api.EFFORT`);
temperature isn't sent (the API's default, 1). Only the sample number is new
(`Cache(dir, sample=n)`, a salted key, so a fresh reply). Before the freeze, a test checks this
from the files: for every one of the 121 problems, the study's formulation and baseline requests
have the same cache key as the follow-up's sample-0 requests, which covers the model, the system
prompt, the messages, `max_tokens`, thinking and effort (`api.KEYED_FIELDS`). The freeze records
each of these by name.

## 4. Scoring and statistics

- **R1's units: the answers the agent would report.** A problem's unit is its single-shot
  **sample 3**, if that answer is **verified**: CBC and HiGHS agree on an optimum and the
  arithmetic checks pass (`Result.verified`). A sample 3 that isn't verified (no answer, a cut-off
  or unusable reply, solvers that disagree, an infeasible or unbounded verdict) gives no unit;
  such problems are counted and reported, and left out of R1. **Expected units: 120.** On these
  121 problems, 359 of the follow-up's 363 single-shot answers (samples 0 to 2) were verified.
- **R1's outcome:** a unit is a **silent failure** if it's wrong by the follow-up's scoring, and
  **right** otherwise.
- **The same answer:** the follow-up's rule (`followup_report.same_answer`): the same status and,
  for an optimum, objectives within 1e-4 relative and absolute. Five samples **agree** only if
  every pair does.
- **Missing answers count as disagreement.** If any of samples 3 to 7, or the baseline's sample
  3, has no usable answer (a loud failure, a reply cut off at `max_tokens`, an unusable or
  unparseable reply, solvers that disagree), it differs from every answer, so the flag is set.
- **The flag:** a unit is flagged if samples 3 to 7 don't all agree (signal (a), with five
  samples), **or** if the baseline's sample 3 differs from the unit's answer (signal (c)).
- **R1, the primary test:** Fisher's exact test, one-sided (flagged units are more often silent
  failures), on the 2 x 2 table of flagged by silent, alpha 0.05. **R1 is supported if
  p < 0.05**; otherwise it's reported as not supported, with its numbers, never as "no
  effect".
- **R1's effect, reported whatever p is:** the base rate (silent failures over units), the
  flag rate, precision (silent failures over flagged units) and recall (flagged silent
  failures over silent failures), each with a 95% Wilson interval, and precision over base
  rate. With one unit per problem, the units are independent and the intervals honest.
- **R2, on all 121 problems:** each problem is right or wrong under two rules, and an exact
  McNemar test (`stats.mcnemar_exact`), two-sided, alpha 0.05, compares them.
  - **One sample:** sample 3's verified answer; with none, the problem is wrong (loud).
  - **Majority of five:** the answer that at least 3 of samples 3 to 7 give, counting verified
    answers only; a sample with no usable answer is no vote. With no such answer, the problem is
    wrong (loud).
- **Without the disputed problems:** R1's test and effect again on the units left after
  removing the 13, labeled secondary, no claim.
- **Abstention, described:** if flagged units were withheld, how many silent failures would
  become loud and how many right answers would be lost.
- **The analysis** is `src/opt_agent/resampling_report.py`, tested on synthetic answers before
  the freeze; the freeze records its hash. Everything in this section is what it computes.

## 5. Power (design information, not a threshold)

[`docs/resampling/power.md`](resampling/power.md) (`scripts/resampling_power.py`, seeded), with
the rates of the follow-up's verified answers on these 121 problems: with 120 units, the primary
test's power is 0.97 if the flag behaves as it did on samples 0 to 2 (it fired on 60.7% of
silent failures and 17.8% of right answers, at a 17.0% base rate), 0.46 if it fires on 45% and
25%, and 0.17 at 35% and 25%. Five samples can disagree more often than three, which may raise
both rates. R2 isn't powered for anything small.

## 6. Run protocol

- **Before any call:** the runner (`src/opt_agent/resampling.py`, which calls the follow-up's
  per-item code, `evaluate.run_item`), the analysis and their tests are committed; a freeze file
  `docs/resampling/FREEZE.json` records the fingerprint of the code, the lock and the inputs
  (`python -m opt_agent.resampling_freeze approve`), and is tagged `resampling-freeze`. The
  follow-up's own freeze stays untouched.
- **One run, from the owner's terminal,** on the frozen inputs: the runner refuses otherwise.
  Problems in the follow-up's run order (`followup.in_run_order`); all six calls of a problem
  run before the next one, so a stopped run leaves whole problems.
- **Hard spend cap: $3.00** (`budget.BudgetedClient`). Expected cost: about **$1.44**, at the
  follow-up's mean cost per answer ($0.00206 single-shot, $0.00163 baseline;
  `runs/followup-test/results.jsonl`): 121 x (5 x $0.00206 + $0.00163). `--plan` gives the
  worst case before the run.
- **If the cap is hit:** the run stops; only problems with all six calls are analyzed; the
  shortfall is a recorded deviation, and section 5's power no longer describes the study.
- **API errors:** Amendment 1 of the M6 pre-registration, unchanged: an errored call is re-run on
  resume, and one still errored after the first pass and 3 resume passes counts as no answer.

## 7. Deviations

Once approved and frozen, this file isn't edited. A change before the run is an amendment,
dated and tagged before any call. Anything that runs differently is recorded in
`docs/resampling/DEVIATIONS.md` with what was planned, what happened and what it changes.
Results are reported whatever they show, in `results/resampling.json` (the analysis writes it);
none goes into `results/eval.json` or `results/followup.json`, and any number of this study in
the README is checked by a test against `results/resampling.json`.
