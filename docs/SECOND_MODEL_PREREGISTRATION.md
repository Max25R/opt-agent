# Pre-registration: the second-model study

**Status: FROZEN by `docs/second_model/FREEZE.json`, tagged `second-model-freeze`.** The owner
approved the design in chat on 2026-11-22 with seven decisions (the model and the cell, the
pairing, matched settings, the analysis, the cost guard, the gate, the tag) and asked Claude to
write this file from them and freeze it. The owner hadn't read this text when it was frozen, so
any change before the run is an amendment (section 7). The runner, the analysis and their
tests were committed before the freeze, and no request to Claude Sonnet 5.5 has been sent from
this project.

**Why it exists.** Every study so far used one model, Claude Haiku 5.5 (the README's "One
model" limitation). This one asks the question that leaves open, on the same problems with the
same pipeline: does a larger model, Claude Sonnet 5.5, answer them right more often, and what
does a right answer cost?

**What was known when it was written:** everything the follow-up published, including Haiku's
single-shot answers on these problems sample by sample (section 2 says what that shows) and
their cost. No Sonnet 5.5 reply exists.

## 1. Hypotheses

- **S1 (primary): Sonnet 5.5's single-shot answers are right more often than Haiku 5.5's,** on
  the 121 problems, one answer per problem from each model. Tested two-sided (section 4).
- **Secondary, no test:** each model's silent failures (a verified answer that's wrong).
- **Descriptive only:** cost and latency per correct answer.
- **Sensitivity, no claim:** S1's counts and test with Haiku's samples 1 and 2 in place of
  sample 0.

## 2. Data

- **Problems:** the follow-up's 121 unexposed test problems, exactly as in
  [`docs/FOLLOWUP_PREREGISTRATION.md`](FOLLOWUP_PREREGISTRATION.md), section 2, and the
  resampling study: the same LLM4OR files and hashes (`Mamo_complex_lp_clean.jsonl`,
  `28e10dff1146ff635673293b5730abb3d7efa2f7bbe91de60fe67b729dfe7a0d`; `IndustryOR.jsonl`,
  `d7c2c05377ade5bc6a401ebf3075f0e00fa91068439761e5b46fa3045ffc19b5`), the same split
  (`data/followup/split.json`,
  `c37ecc0e93f16d0e496e5c2b95d8d8f4c477d92220205e63d73e5cbe4e0a3203`), and the id list of the
  121 whose SHA-256 is `5ba1e23a8a4964fa5a7fc649260df00fe30ca3eae8d3c7809523dabf26698ed2`.
- **Keys and scoring:** the follow-up's, unchanged (`followup.is_correct`: the raw key, 1e-4
  relative and absolute, the rounding clause for keys written with decimals). No key is
  corrected. The 13 problems whose keys an LLM judge flagged, not verified by a person, stay
  in as keys of record.
- **Haiku's answers, the pairing record, fixed here:** `runs/followup-test/results.jsonl`,
  SHA-256 `cedc37164ab5497a62fd79c06154f9cb15f384fa6307174b46d949282c20c18e`. It's the
  follow-up's test run, made on the code at tag `followup-freeze`, committed in `7cfe7bb` and
  unchanged since; tag `resampling-freeze` holds the same file, and so does this study's tag.
  The pair of each Sonnet answer is that file's single-shot item of **sample 0** for the same
  problem (the latest line for the pair): all 121 are there, every one a done item.
  - **Why sample 0:** it's the follow-up's first sample, sent as the plain request (the
    unsalted cache key, `Cache(dir, sample=0)`), which is also how this study asks Sonnet: one
    first sample from each model. Fixed here, before any Sonnet reply exists, and never
    switched.
  - **Known before this study, and disclosed:** sample 0 is Haiku's lowest-scoring sample on
    these problems: 95 of 121 right (78.5%), against 102 and 101 for samples 1 and 2 (82.1%
    over all three). So the primary comparison is against a Haiku answer 3.6 points below its
    average, which favors Sonnet; section 4's sensitivity rows show whether S1's result holds
    against samples 1 and 2. Of sample 0's answers, 120 are verified and 25 of those are wrong
    (silent failures); 1 is a loud failure.

## 3. Calls, and the same settings as Haiku's run

Per problem, **one call: single-shot, sample 0, model `claude-sonnet-5-5`**, solved and
checked as in the follow-up. 121 calls in all. No call for Haiku (its answers are recorded) and
no no-solver baseline this round.

**Everything but the model is Haiku's run's.** The formulation prompt and schema
(`formulate.SYSTEM_PROMPT`, `formulate.LP_SCHEMA`); `max_tokens` 16,000; thinking adaptive with
its text omitted, and effort medium (`api.THINKING`, `api.EFFORT`); temperature not sent (the
API's default, 1); retries as `api.call` makes them (up to 8 tries, the SDK's rule, waiting what
`retry-after` names); one attempt (no revision); CBC (cbcbox 2.929) solving, HiGHS (SciPy
1.18.1) cross-checking, the arithmetic checks and the improving-ray check; and the same record
per answer (`evaluate.run_item`). The freeze records each of these by name. Two checks from
the files, both passed for all 121 problems before the freeze (the freeze refuses otherwise,
`second_model_freeze.unfinished` and `approve`):

- **The requests:** each Sonnet request equals Haiku's sample-0 request in every field but
  `model`, and Haiku's request, built by this code, is byte for byte the request its run sent
  (stored with its reply in `runs/followup-test/cache`).
- **The solving and the checks:** Haiku's 121 sample-0 answers, replayed from that cache through
  this code with a client that can send nothing, give back every recorded field of every item,
  time and payment aside.

**Declared differences** (what can't match):

1. **The model,** by design: `claude-sonnet-5-5`, at $2 and $10 per million input and output
   tokens, 20 times Haiku 5.5's (`pricing.PRICES`, checked on the pricing page 2026-11-22).
2. **The code version.** Haiku's answers came from the code at `followup-freeze`; Sonnet's
   come from `second-model-freeze`'s. On this pipeline the two differ in typing, docstrings and
   messages, and in one behavior: CBC leaving an LP's constraint without a dual is now a loud
   failure (no answer), where the old code would have stopped the run with an error. Haiku's
   run never hit it (it finished, and the replay above gives back all 121 answers). The
   packages the pipeline uses are at the same versions (anthropic 1.15.0, PuLP 4.0.1, cbcbox
   2.929, SciPy 1.18.1, NumPy 2.5.4); the lock only added the demo's.
3. **The same effort label isn't the same thinking.** "medium" goes to both models, and each
   decides how much to think for it; that's part of the model difference, not a setting. A
   model's tokenizer may also count the same text differently, so 16,000 tokens may hold more
   or less of a reply. Output tokens (thinking included) and cut-off replies are reported for
   each model.
4. **Refusals.** No fallback model is configured (`fallbacks` isn't sent, as it wasn't for
   Haiku): a fallback would let another model answer. A Sonnet refusal is a reply with no
   answer, a loud failure, as a Haiku one would have been.
5. **When.** Haiku's answers are from November 2026; Sonnet's will be from December 2026.
   Latency depends on load, so it's descriptive only.

## 4. Scoring and statistics

- **Right or wrong, per answer:** right if it's a done item whose answer is right by the
  follow-up's scoring (`followup_report.is_right`); wrong otherwise: no answer (a loud failure:
  an unusable, cut-off or refused reply, solvers that disagree, a failed check), an item
  errored after Amendment 1's passes, or no item.
- **S1, the primary test:** an exact McNemar test (`stats.mcnemar_exact`), two-sided, alpha
  0.05, on the problems only one model got right. Decided now, before any Sonnet reply:
  - **supported:** p < 0.05, and Sonnet got more of those problems right;
  - **not supported:** p < 0.05, and Haiku got more of them right (a detected difference the
    other way);
  - **inconclusive:** p >= 0.05. Reported with the paired difference and its 95% interval,
    never as "no difference"; "no difference larger than X points" is said only if that
    interval lies within +/-X points (the follow-up's rule);
  - **incomplete:** the run didn't settle all 121 problems (section 6's cap or checkpoint
    stopped it, or an errored call has passes left). No verdict is reported then.
- **S1's effect, reported whatever the verdict:** each model's accuracy with a 95% Wilson
  interval; the paired difference (Sonnet's accuracy minus Haiku's) with the follow-up's 95%
  paired percentile bootstrap interval over problems (`followup_report.bootstrap_ci`, 10,000
  resamples, seed 20261109); and the 2 x 2 counts.
- **Secondary, each model, no test:** silent failures (a verified answer, a confirmed optimum,
  that's wrong) of the 121 problems and of its verified answers, each with a Wilson interval;
  and the rest of its wrong answers: wrong confirmed verdicts (infeasible or unbounded) and
  loud failures, with cut-off replies among them counted.
- **Descriptive only, each model:** cost per correct answer (the total `cost_usd` of its 121
  answers, every call each used, at its own prices, over its right answers) and latency per
  correct answer (the total `latency_s`, API plus solver time without retry waits, over its
  right answers); with the cost per answer, the median latency and the tokens.
- **Sensitivity, no claim:** S1's counts, p-value and difference with Haiku's sample 1, then
  sample 2, in place of sample 0; and Haiku's accuracy averaged over samples 0 to 2.
- **The analysis** is `src/opt_agent/second_model_report.py`, tested on synthetic answers
  before the freeze; the freeze records its hash. Everything in this section is what it
  computes, and it writes `results/second_model.json`.

## 5. Power (design information, not a threshold)

[`docs/second_model/power.md`](second_model/power.md) (`scripts/second_model_power.py`, exact):
the chance S1 comes out supported if Sonnet's accuracy is higher by a given difference, for
shares of problems that only Haiku gets right from 2% to 8% (two of Haiku's own samples
disagree on 7 to 11 of the 121). About 80% power needs a gain of 10 points if Haiku alone is
right on 2% of problems, and 12 to 13.5 points at 4% to 6%; a 5-point gain has power 0.16 to
0.34. Sonnet can gain at most 21.5 points over sample 0 (26 problems).

## 6. Run protocol

- **Before any call:** the runner (`src/opt_agent/second_model.py`), the analysis and their
  tests are committed; `docs/second_model/FREEZE.json` records the fingerprint of the code, the
  lock and the inputs (`python -m opt_agent.second_model_freeze approve`); the commit that adds
  it is tagged `second-model-freeze`, and its parent is the approved commit. **The run refuses
  to start** unless that tag exists, holds exactly the approved inputs, and the inputs here
  match them (`second_model_freeze.ready`). The other studies' freezes stay untouched.
- **One run, from the owner's terminal, in December 2026** (after the monthly credit resets),
  on the frozen inputs. Problems in the follow-up's run order (`followup.in_run_order`, seed
  20261109). Resuming replays every finished call from the run's cache, for free.
- **The cost guard:**
  - **a hard cap of $7.00 of actual spend** (`budget.BudgetedClient`, ledger
    `runs/second-model/spend.jsonl`): before each call it reserves that call's worst case
    (every reply at `max_tokens`, about $0.17 to $0.19), so the spend never passes $7.00;
  - **a checkpoint after the first 10 problems** in run order: before the next call, the run
    projects the total as the mean cost of the answers among those 10 (`cost_usd`, from token
    counts only, never from whether they're right) times 121, records it, and **stops if it's
    over $7.00.** A resume recomputes it from the same records, so it stops again.
- **Expected cost: about $5.18,** if Sonnet uses as many tokens as Haiku's sample 0 did
  ($0.2589 for the 121, times 20). Sonnet may think more or less at the same effort label; the
  checkpoint measures it. Known before the run: on Haiku's costs, the first 10 problems in this
  order (all from ComplexLP) project 0.78 of the actual total, and any 10 in a row between 0.72
  and 1.53 of it, so the checkpoint is a noisy early stop and the hard cap is the guarantee. If
  Sonnet's answers use more than about 1.3 times Haiku's tokens, the cap can stop the run
  before the end (the last reservation leaves up to $0.19 of it unspent). The worst case with no cap, every reply at `max_tokens`, is $20.95
  (`python -m opt_agent.second_model --plan`).
- **If the cap or the checkpoint stops the run:** S1 gets no verdict ("incomplete"); the
  partial run is committed as it is and analyzed as it is; continuing needs an amendment (a new
  cap), dated and tagged before any further call.
- **API errors:** Amendment 1 of the M6 pre-registration, unchanged: an errored call is re-run
  on resume, and one still errored after the first pass and 3 resume passes counts as no
  answer.

## 7. Deviations

Once frozen, this file isn't edited. A change before the run is an amendment, dated and tagged
before any call. Anything that runs differently is recorded in `docs/second_model/DEVIATIONS.md`
with what was planned, what happened and what it changes. Results are reported whatever they
show, in `results/second_model.json` (the analysis writes it); none goes into
`results/eval.json`, `results/followup.json` or `results/resampling.json`, and any number of
this study in the README is checked by a test against `results/second_model.json`.

## Amendment 1 (before any paid call), 2026-11-22

**Why.** The owner's API credit expires soon, so the run moves from December to now, and the
owner can spend up to $13.50 of the $14.53 left. The owner decided both changes below in chat
on 2026-11-22. No call of this study had been made and no Sonnet output had been seen:
`runs/second-model` didn't exist, and no spend ledger in this project has an entry for
`claude-sonnet-5-5`. Everything above stays as it was frozen; this section is added below it.
The first freeze (`docs/second_model/FREEZE.json`, tag `second-model-freeze`) is kept as it
was committed and still verifies, but no longer gates the run: the amended study is frozen by
`docs/second_model/FREEZE-2.json`, tagged `second-model-freeze-2`, and the run refuses to start
unless that tag holds it and the inputs here match.

**Stage 1 is the study as registered, with one change: its hard cap is $11.00, not $7.00.**
Its checkpoint after the first 10 problems compares the projected stage-1 total with $11.00.
S1, the pairing (Haiku's sample 0), the sensitivity rows, the verdict rules and everything
else in sections 1 to 7 are unchanged. The study's verdict rests only on S1.

**Stage 2 (new, secondary): the no-solver baseline with Sonnet 5.5.**

- **Calls:** one per problem, sample 0, on the same 121 problems in the same run order, with
  the settings of Haiku's no-solver condition in the follow-up except the model: the prompt
  and schema (`baseline.SYSTEM_PROMPT`, `baseline.ANSWER_SCHEMA`), `max_tokens` 16,000,
  thinking and effort pinned as in section 3, temperature not sent, the same retries and the
  same parsing and record (`evaluate.run_item`, condition `baseline`). Section 3's declared
  differences apply to it too.
- **It starts only if stage 1 settled all 121 problems.** Otherwise it's "not started".
- **Its cost guard:** a hard cap of $13.50 of total spend across both stages (one ledger, so
  stage 1's spend counts), and its own checkpoint after its first 10 problems: the projected
  total is stage 1's cost plus the mean cost of stage 2's answers among those 10 times 121,
  from token counts only, never from whether anything is right; over $13.50, it stops there.
- **Its analysis, secondary, no verdict:** Sonnet single-shot (stage 1's answers) against
  Sonnet no-solver (stage 2's), with the exact McNemar test, two-sided, and the paired
  difference (single-shot minus no-solver) with the follow-up's bootstrap interval; and the
  same comparison for Haiku (its sample 0 in each condition, from the same record), for
  context. Sonnet's comparison is computed only if stage 2 settled all 121 problems;
  otherwise stage 2 is reported as "incomplete" with how far it got and what it cost, and
  stage 1's result stands. Each stage's cost and latency are reported too.
- **Known before this amendment, and disclosed:** Haiku's own comparison on these problems,
  sample 0: single-shot right on 95 and no-solver on 92 (11 problems right only single-shot,
  8 only no-solver; p 0.65; a difference of +2.5 points, interval -4.1 to +9.9).
- **Checks before the freeze,** as in section 3, now in both conditions, all passed: every
  Sonnet no-solver request equals Haiku's sample-0 no-solver request but for the model, and
  Haiku's is byte for byte the one its run sent; and Haiku's 121 sample-0 no-solver answers
  replay through this code with every recorded field back, with one wording change counted as
  the same: four of them were cut off at `max_tokens`, and that reason's message now reads
  "the reply was cut off at its max_tokens limit" where the record says "the reply was cut off
  at 16000 tokens" (section 3's declared difference 2, "messages").

**Expected cost:** stage 1 about $5.18, as in section 6; stage 2 about $4.14 (Haiku's
no-solver sample 0 cost $0.2069 for the 121, times 20); about $9.32 in all. The hard caps:
stage 1 $11.00, both stages together $13.50. Uncapped worst cases, every reply at
`max_tokens`: $20.95 for stage 1 and $20.59 for stage 2 (`--plan` prints them). Each call's
reservation leaves up to $0.19 of a cap unspent, so stage 1 has room for about 2.1 times
Haiku's tokens, and both stages together for about 1.4 times; past that, the total cap can
stop stage 2 before the end. On Haiku's costs, stage 2's first 10 problems project 1.13 of its
actual total.
