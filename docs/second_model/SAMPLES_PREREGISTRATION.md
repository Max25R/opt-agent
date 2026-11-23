# Pre-registration: the second-model samples study (Claude Sonnet 5.5, samples 1 and 2)

**Status: FROZEN by `docs/second_model/SAMPLES_FREEZE.json`, tagged
`second-model-samples-freeze`.** The owner set the design in chat on 2026-11-23 (two more
Sonnet samples on the same problems, sent as Haiku's were; new paths; this disclosure; the
primary and secondary analyses; the cost guard; the gate, reproduce coverage and tests; the
tag) and asked Claude to write this file from it and freeze it. The owner hadn't read this
text when it was frozen, so any change before the run is an amendment (section 7). The runner,
the analysis, the gate and their tests were committed before the freeze, and no request for
Sonnet's samples 1 and 2 has been sent.

**Why it exists.** The second-model study's S1 (Sonnet 5.5 right more often than Haiku 5.5)
was inconclusive, on one answer per problem from each model, and its sensitivity rows showed
that which of Haiku's samples is used moves the comparison by several points. One Sonnet
sample is as noisy. This study gives Sonnet the three samples per problem that Haiku has, and
compares the two with the follow-up's own three-sample test.

## What was known when this was written

Everything the second-model study published (`results/second_model.json`,
`docs/second_model/RESULTS.md`), on the same 121 problems:

| Haiku's sample | Haiku right | Sonnet's sample 0 right | only Sonnet right | only Haiku right | exact McNemar p | difference, points (95% interval) |
|---|---:|---:|---:|---:|---:|---|
| 0 (S1) | 95 | 88 | 6 | 13 | 0.17 | -5.8 (-13.2 to +0.8) |
| 1 (sensitivity, no claim) | 102 | 88 | 4 | 18 | 0.0043 | -11.6 (-19.0 to -4.1) |
| 2 (sensitivity, no claim) | 101 | 88 | 4 | 17 | 0.0072 | -10.7 (-18.2 to -4.1) |

S1's verdict was **inconclusive** (p is at least alpha 0.05; "no difference larger than 14
points"). Haiku's accuracy over its three samples is 82.1%. Also known: Sonnet's sample 0 had
29 silent failures among its 117 verified answers, and Haiku's sample 0 had 25 among 120; and
the second-model study's stage 2 (Sonnet without the solver).

**What that fixes in advance** (Claude's arithmetic from the two records, before any new
reply): Haiku's side of the comparison is entirely known. Its three samples are right on 298
of its 363 answers; per problem, all three are right on 92 problems, two on 9, one on 4 and
none on 16, so its majority of three is right on 101. Sonnet's sample 0 is known too (88 of
121). Only Sonnet's samples 1 and 2 are new: for Sonnet's mean score to be higher than
Haiku's at all, they must be right on at least 211 of their 242 answers (87.2%; 210 ties),
against 72.7% for its sample 0. So "supported" needs Sonnet's new samples to do much better
than its first, and "not supported" (Haiku detected as better) is a likely outcome. The
verdict rules below are fixed anyway, before any new reply exists.

## 1. Hypotheses

- **S2 (primary): Claude Sonnet 5.5's single-shot answers are right more often than Claude
  Haiku 5.5's,** with three samples per problem from each model on the 121 problems. Tested
  two-sided (section 4). The study's verdict is S2's alone; S1's result stands as reported,
  and nothing here re-tests or replaces it.
- **Secondary, no verdict:** majority of three per problem (exact McNemar), and each model's
  silent failures over its three samples.
- **Descriptive only:** each model's right answers per sample, and the cost and latency of
  Sonnet's two new samples.

## 2. Data

- **Problems:** the second-model study's 121, exactly: the follow-up's unexposed test
  problems, from the same LLM4OR files and hashes (`Mamo_complex_lp_clean.jsonl`,
  `28e10dff1146ff635673293b5730abb3d7efa2f7bbe91de60fe67b729dfe7a0d`; `IndustryOR.jsonl`,
  `d7c2c05377ade5bc6a401ebf3075f0e00fa91068439761e5b46fa3045ffc19b5`), the same split
  (`data/followup/split.json`,
  `c37ecc0e93f16d0e496e5c2b95d8d8f4c477d92220205e63d73e5cbe4e0a3203`), and the id list whose
  SHA-256 is `5ba1e23a8a4964fa5a7fc649260df00fe30ca3eae8d3c7809523dabf26698ed2`.
- **Keys and scoring:** the follow-up's, unchanged (`followup.is_correct`: 1e-4 relative and
  absolute, and the rounding clause for keys written with decimals). No key is corrected; the
  13 problems whose keys an LLM judge flagged, not verified by a person, stay in as keys of
  record.
- **Haiku's answers, fixed here:** `runs/followup-test/results.jsonl`, SHA-256
  `cedc37164ab5497a62fd79c06154f9cb15f384fa6307174b46d949282c20c18e` (the follow-up's test run,
  the second-model study's pairing record): its single-shot items of **samples 0, 1 and 2** for
  each problem (the latest line per pair). All 363 are there, every one a done item.
- **Sonnet's sample 0, fixed here:** `runs/second-model/results.jsonl`, SHA-256
  `0440e003cdcb6db04a43dce88d30ce9993d246b8ad867b972e40a9a699189a49` (the second-model study's
  run, committed in `a78a2af` and never re-run): its single-shot items (stage 1), all 121 done.
  This study reads it and never writes to it, or to `results/second_model.json`.
- **Sonnet's samples 1 and 2:** this study's run, `runs/second-model-samples` (new).

## 3. Calls: sent the way Haiku's samples 1 and 2 were

Per problem, **two calls: single-shot, samples 1 and 2, model `claude-sonnet-5-5`**, solved and
checked as in the follow-up. 242 calls in all. No call for Haiku or for Sonnet's sample 0.

**Exactly as the follow-up sent Haiku's samples 1 and 2, but for the model.** No field of a
request names its sample: each sample's request is the one sample 0 was sent
(`formulate.build_request`). What makes a sample a new answer is the cache: its key is salted
with the sample's number (`api.cache_key`, `Cache(dir, sample)`), so no sample ever replays
another's reply. The run makes one pass with one session per sample, problem by problem,
sample 1 then sample 2, as `evaluate.evaluate` ran the follow-up's samples. Everything else is
Haiku's run's and Sonnet's sample 0's: the formulation prompt and schema
(`formulate.SYSTEM_PROMPT`, `formulate.LP_SCHEMA`); `max_tokens` 16,000; thinking adaptive
with its text omitted, and effort medium (`api.THINKING`, `api.EFFORT`); temperature not sent
(the API's default, 1); retries as `api.call` makes them; one attempt (no revision); CBC
(cbcbox 2.929) solving, HiGHS (SciPy 1.18.1) cross-checking, the arithmetic checks and the
improving-ray check; and the same record per answer (`evaluate.run_item`). The freeze records
each of these by name. Two checks from the files, both passed for all 121 problems before the
freeze (the freeze refuses otherwise: `second_model_samples_freeze.unfinished`, `approve`):

- **The requests:** for each problem, the request samples 1 and 2 will send is byte for byte
  the one the second-model study's run sent for Sonnet's sample 0 (stored with its reply in
  `runs/second-model/cache`), and equals Haiku's sample-1 and sample-2 requests, as the
  follow-up's run sent them (in `runs/followup-test/cache`, under their salted keys), in every
  field but `model`.
- **The solving and the checks:** every answer this comparison uses that already exists
  (Haiku's samples 0, 1 and 2, and Sonnet's sample 0: 484 answers), replayed from its run's
  cache through this code with a client that can send nothing, gives back every recorded field
  of every item, time and payment aside.

**Declared differences** (what can't match):

1. **The model,** by design: `claude-sonnet-5-5`, at $2 and $10 per million input and output
   tokens, 20 times Haiku 5.5's (`pricing.PRICES`, checked on the pricing page 2026-11-22).
2. **The code version.** Haiku's answers came from the code at `followup-freeze`, Sonnet's
   sample 0 from `second-model-freeze-2`'s, and samples 1 and 2 will come from this study's
   tag. Since `second-model-freeze-2`, nothing under `src/opt_agent/` and nothing in
   `requirements.lock` has changed but this study's three new modules (its runner, analysis and
   gate), which the answers don't go through; the second-model study's pre-registration
   (section 3, declared difference 2) gives how that code differs from `followup-freeze`'s.
   The replay above shows the differences change no recorded answer.
3. **The same effort label isn't the same thinking:** "medium" goes to both models, and each
   decides how much to think for it. Output tokens and cut-off replies are reported for each
   model (section 4's failures count cut-off replies; the cost section, the new samples'
   tokens).
4. **Refusals.** No fallback model is configured, as for Haiku and for Sonnet's sample 0: a
   Sonnet refusal is a reply with no answer, a loud failure.
5. **When.** Haiku's answers are from 2026-11-13 and 14, Sonnet's sample 0 from 2026-11-22
   (Eastern time), and samples 1 and 2 will be from after this freeze. Sonnet's three samples
   are from two runs, where Haiku's came from one pass; each answer is its own request either
   way. Latency depends on load, so it's descriptive only.

## 4. Scoring and statistics

- **Right or wrong, per answer:** right if it's a done item whose answer is right by the
  follow-up's scoring (`followup_report.is_right`); wrong otherwise: no answer (a loud failure:
  an unusable, cut-off or refused reply, solvers that disagree, a failed check), an item
  errored after Amendment 1's passes, or no item.
- **A model's score on a problem:** how many of its 3 samples are right (0 to 3). Its mean
  score is its right answers over its 363.
- **S2, the primary test: the follow-up's** (its pre-registration's section 4): the paired
  sign-flip permutation test on the per-problem score differences (Sonnet minus Haiku),
  two-sided, computed exactly (`stats.sign_flip_exact`), by the function the follow-up's report
  used (`followup_report.contrast`). Alpha 0.05. There is one comparison, so no Holm
  correction. Decided now, before any reply of samples 1 and 2:
  - **supported:** p < 0.05, and Sonnet's mean score is higher than Haiku's;
  - **not supported:** p < 0.05, and Haiku's mean score is higher (a detected difference the
    other way);
  - **inconclusive:** p >= 0.05. Reported with the difference and its 95% interval, never as
    "no difference"; "no difference larger than X points" is said only if that interval lies
    within +/-X points (the follow-up's rule);
  - **incomplete:** the run didn't settle all 242 calls (section 6's cap or checkpoint stopped
    it, or an errored call has passes left). No verdict is reported then.
- **S2's effect, reported whatever the verdict:** each model's mean score with the follow-up's
  bootstrap interval; the difference (Sonnet's mean score minus Haiku's, in points) with the
  follow-up's 95% paired percentile bootstrap interval over problems
  (`followup_report.bootstrap_ci`, 10,000 resamples, seed 20261109); and how many problems
  each model scored higher on, and how many tied.
- **Secondary, no verdict:**
  - **Majority of three:** a problem is right for a model if 2 or 3 of its samples are (the
    follow-up's secondary). The exact McNemar test (`stats.mcnemar_exact`), two-sided, on the
    problems only one model's majority got right; each model's majority accuracy with a 95%
    Wilson interval; and the majority difference with its bootstrap interval. Same contrast
    function.
  - **Silent failures over the three samples, each model:** verified answers (a confirmed
    optimum) that are wrong, of its 363 answers and of its verified answers, each with a Wilson
    interval; and the rest of its wrong answers: wrong confirmed verdicts (infeasible or
    unbounded) and loud failures, with cut-off replies among them counted. Each sample is
    counted as the second-model study counted one (`second_model_report.failures`), then added
    up.
- **Descriptive only:** each model's right answers in each sample; for Sonnet's samples 1 and
  2, the total cost (every call, at Sonnet's prices, from its token counts), the cost per
  answer and per right answer, the median latency (API plus solver time, without retry waits)
  and the tokens.
- **The analysis** is `src/opt_agent/second_model_samples_report.py`, tested on synthetic
  answers before the freeze; the freeze records its hash. Everything in this section is what it
  computes, and it writes `results/second_model_samples.json`.

## 5. Power (design information, not a threshold)

No power analysis was run for this study. For scale only: the follow-up's
(`docs/followup/power.md`, its H2 model: two conditions called separately, 121 problems,
three samples each) puts the smallest difference this test detects with 80% power at alpha
0.05 at 11 to 15 points, depending on how often the two disagree with no effect and how
consistent the samples are. Section "What was known" gives how far Sonnet's new samples would
have to move for each verdict.

## 6. Run protocol

- **Before any call:** the runner (`src/opt_agent/second_model_samples.py`), the analysis, the
  gate and their tests are committed; `docs/second_model/SAMPLES_FREEZE.json` records the
  fingerprint of the code, the lock and the inputs (`python -m
  opt_agent.second_model_samples_freeze approve`); the commit that adds it is tagged
  `second-model-samples-freeze`, and its parent is the approved commit. **The run refuses to
  start** unless that tag exists, holds exactly the approved inputs, and the inputs here match
  them (`second_model_samples_freeze.ready`). Every other study's freeze and tag stays as it
  is.
- **One run, from the owner's terminal, now** (the owner's API credit expires soon), on the
  frozen inputs, into `runs/second-model-samples`. Problems in the follow-up's run order
  (`followup.in_run_order`, seed 20261109), sample 1 then sample 2 for each. Resuming replays
  every finished call from the run's cache, for free.
- **The cost guard:**
  - **a hard cap of $7.00 of actual spend** (`budget.BudgetedClient`, ledger
    `runs/second-model-samples/spend.jsonl`): before each call it reserves that call's worst
    case (a reply at `max_tokens`: $0.17 to $0.19 at Sonnet's prices), so the spend never
    passes $7.00;
  - **a checkpoint after the first 10 problems** in run order (their 20 calls): before the
    next call, the run projects the total as the mean cost of the answers among those calls
    (`cost_usd`, from token counts only, never from whether they're right) times 242, records
    it, and **stops if it's over $7.00.** A resume recomputes it from the same records, so it
    stops again.
- **Expected cost: about $4.83,** priced from Sonnet's own single-shot calls in the second-model
  study: $2.4154 for its 121 (a mean of $0.0200 a call, the most expensive $0.0499), times 2.
  The cap leaves room for about 1.4 times sample 0's spend (the last reservation can leave up
  to $0.19 of it unspent); past that, the cap stops the run before the end. On sample 0's
  costs, the first 10 problems in this order project 0.80 of the actual total, and any 10 in a
  row between 0.72 and 1.46 of it, so the checkpoint is a noisy early stop and the hard cap is
  the guarantee. The worst case with no cap, every reply at `max_tokens`, is $41.90 (`python
  -m opt_agent.second_model_samples --plan`).
- **If the cap or the checkpoint stops the run:** S2 gets no verdict ("incomplete"); the
  partial run is committed and analyzed as it is; continuing needs an amendment (a new cap),
  dated and tagged before any further call. If the account can't pay (a spend limit, or no
  credit left), the run stops too; a resume continues it, and if none is possible, it's
  incomplete in the same way.
- **API errors:** Amendment 1 of the M6 pre-registration, unchanged: an errored call is re-run
  on resume, and one still errored after the first pass and 3 resume passes counts as no
  answer.

## 7. Deviations

Once frozen, this file isn't edited. A change before the run is an amendment, dated and tagged
before any call. Anything that runs differently is recorded in
`docs/second_model/SAMPLES_DEVIATIONS.md` with what was planned, what happened and what it
changes. Results are reported whatever they show, in `results/second_model_samples.json` (the
analysis writes it); none goes into `results/eval.json`, `results/followup.json`,
`results/resampling.json` or `results/second_model.json`, and any number of this study in the
README is checked by a test against `results/second_model_samples.json`.
