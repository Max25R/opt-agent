# Amendment 5: external corroboration (exploratory)

**Status: DRAFT (2026-11-08). Not approved, not tagged.** Drafted by Claude. Like Amendments 3
and 4, it lives here because `docs/PREREGISTRATION.md` is frozen.

**Exploratory and post hoc.** Written after both test runs, every report, the judges' labels,
Amendments 3 and 4, and the audit. It compares the frozen answers with an outside answer key
and reports what it finds, descriptively: no tests, nothing outside this amendment scored
differently, no answer key or label changed.

## The result of record

**The result of record stays the pre-registered strict accuracy: 264 of 274 in every
condition**, with the six McNemar tests and their Holm correction as reported. Nothing here
replaces, adjusts or reinterprets it.

## How much this shows

- **Strong evidence: the five removals.** A team independent of this project, with none of
  our labels, reviews or judges, removed 5 of Amendment 4's six answer-key errors from its
  cleaned set as errors. That is the corroboration this amendment rests on.
- **Weak evidence: the 14/14 agreement on the keys that differ.** The models and our key share
  Claude-written readings. Claude wrote every review and most integrality labels, and the
  formulation and baseline prompts use the same integrality rule of thumb as the labels
  (pre-registration 3f). So Claude's answers agreeing with Claude's key is close to circular:
  it shows the two are consistent, not that either is right.

## The outside key

LLM4OR's cleaned NL4Opt, from the survey by Xiao et al. 2025 (arXiv 2508.10047), recorded in
`docs/EXTERNAL_DATA.md` (repository `LLM4OR/LLM4OR`, commit `75962df`). Its authors removed
the problems they found in error and kept 214 of NL4Opt's 289 test problems, each with one
answer: an objective value, or null for no optimum. Their data states no license, so it isn't
committed; `scripts/amendment5.py` refuses any copy whose hash isn't the recorded one.

**How it's compared.**
- **Matching:** each cleaned problem is matched to ours by exact text (whitespace and case
  normalized, as the cross-check does). All 214 match exactly; the script refuses any that
  doesn't, so nothing rests on a fuzzy match.
- **Scoring against their key:** an answer matches when it has the same status and, for an
  optimum, the same objective within 1e-4 relative (the external cross-check's tolerance,
  since published values can be rounded). A null key matches any answer of "no optimum".
- **Against ours, on the same problems:** the frozen scores, unchanged.

## What it shows

**(a) Accuracy on the overlap.** On the 210 overlapping problems we score, every condition
matches the LLM4OR key on 185 (88.1%), against 205 or 206 (about 98%) for our frozen key on the
same problems. The gap is accounted for in full (section "The rows"):
- 13 or 14 per condition are problems where their key differs from ours and the condition's
  answer matched ours (part c).
- 6 to 8 are answers our pre-registered scoring accepts through another reading (the strict
  reading of "more than", the "=" reading of a ratio, or the other optimum of an `either`
  label), which a one-answer key can't accept.
- 4 or 5 are wrong against both keys.

So the lower number mostly says the two keys differ, not that the answers got worse.

**(b) Amendment 4's six answer-key errors.**
- **Five were removed by LLM4OR** as errors: `431521997`, `1605420061`, `2078392466`,
  `-926961422` and `-2138755435`. This corroborates that their keys are wrong without any LLM
  judge. It doesn't confirm Amendment 4's diagnosis of each one: the release doesn't say why
  a problem was removed.
- **The sixth, `-1540907330` (curry bowls), was kept with key 0.** That agrees with our frozen
  key, not with Amendment 4's corrected label, which also accepts the strict reading's 17 (the
  answer every condition gave). On this problem the outside key sides with the frozen key.

**(c) The 14 keys that differ.** On 14 overlapping problems, the LLM4OR key is not an answer
our frozen key accepts: 5 where it is our key's other-integrality optimum, 9 where it differs
otherwise. On all 14, single-shot and self-correction matched our key. The baseline matched
our key on 13; on `-38093970` it matched neither (it answered 35; our `either` label accepts
36.67 and 37, and their key is 36). No condition matched the LLM4OR key on any of the 14.

This is descriptive, not proof that our key is right, and it is the weak half of the evidence
("How much this shows"): the models and our key share Claude-written readings. Several of
their values look rounded down or truncated (33 for 33.5, 23 for 23.5, 507 for 507.8), which
would explain some differences without either key reading the text differently.

## Limits

- **Not ground truth.** The LLM4OR key gives one answer per problem, with no integrality
  label or alternative readings, and its release doesn't document how the answers were made
  or which problems were removed for what.
- **Not comparable with 264/274.** Different key, different problems: their 210 leave out the
  64 we score but they removed, which include 5 of Amendment 4's six and other problems we
  reviewed by hand.
- **Not independent of NL4Opt.** Both keys descend from its text and annotations, so an error
  both inherit gets through.
- **Post hoc and one-off.** The comparison was chosen after the results were known. No tests,
  outside the Holm family.
- **Reproducible only with the data.** The rows are computed from the git-ignored copy. Where
  it's absent (CI), `scripts/eval_json.py` keeps the committed `amendment_5` block unchanged,
  and `tests/test_amendment5.py` (which needs the data) is skipped; with the data, the test
  recomputes the block and compares. So CI copies the `amendment_5` block forward without
  recomputing it, and a hand edit to that block is caught only where the LLM4OR data exists.

## The rows

Every number and problem id in this section comes from `results/eval.json` (its `amendment_5`
entry), and `tests/test_readme_numbers.py` checks it, as it checks the README. Rates are right
of n, the accuracy, and its 95% Wilson interval.

The overlap: 214 cleaned problems, all 214 matched exactly to our test split, 210 of them
scorable. 64 of our 274 scorable problems aren't in the cleaned set. Matched but not scorable:
`-114149479`, `358766780` (reviewed annotation errors), `-642253022`, `-876754599` (annotations
we reject).

| condition | against the LLM4OR key | against our frozen key, same problems |
|---|---|---|
| baseline | 185/210, 88.1% (83.0–91.8%) | 206/210, 98.1% (95.2–99.3%) |
| single-shot | 185/210, 88.1% (83.0–91.8%) | 205/210, 97.6% (94.5–99.0%) |
| self-correction | 185/210, 88.1% (83.0–91.8%) | 205/210, 97.6% (94.5–99.0%) |

Why an answer misses the LLM4OR key:

| condition | their key differs, the answer matched ours | the answer matched another reading ours accepts | wrong against both keys |
|---|---|---|---|
| baseline | 13 | 8 | 4 |
| single-shot | 14 | 6 | 5 |
| self-correction | 14 | 6 | 5 |

Amendment 4's six answer-key errors: removed by LLM4OR, `431521997`, `1605420061`,
`2078392466`, `-926961422` and `-2138755435`. Kept, `-1540907330`: LLM4OR key 0, our frozen key
0; the corrected label also accepts 17.

The 14 differing keys (answers rounded to two decimals):

| problem | kind | our label | our key | LLM4OR key | baseline | single-shot and self-correction | matched |
|---|---|---|---|---|---|---|---|
| `294897151` | other integrality | continuous | 166.67 | 166 | 166.67 | 166.67 | ours, all three |
| `-450888040` | disagrees | integer | 507.8 | 507 | 507.8 | 507.8 | ours, all three |
| `811663079` | other integrality | continuous | 30000.00 | 29950 | 30000 | 30000.00 | ours, all three |
| `-1965714403` | other integrality | continuous | 14375.00 | 14325 | 14375 | 14375.00 | ours, all three |
| `-1066222271` | disagrees | integer | 20 | no optimum | 20 | 20 | ours, all three |
| `-847055511` | disagrees | integer | infeasible | 17.02 | infeasible | infeasible | ours, all three |
| `-1681245352` | disagrees | integer | 25 | 0 | 25 | 25 | ours, all three |
| `902707159` | disagrees | integer | 12 | 0 | 12 | 12 | ours, all three |
| `-38093970` | disagrees | either | 37 (and 36.67) | 36 | 35 | 36.67 | baseline neither; the other two ours |
| `-355557676` | disagrees | continuous | 34.17 | 0 | 34.17 | 34.17 | ours, all three |
| `-1911316210` | other integrality | integer | 4347 | 4347.83 | 4347 | 4347 | ours, all three |
| `2137478401` | disagrees | integer | 33.5 | 33 | 33.5 | 33.5 | ours, all three |
| `981967779` | disagrees | either | 23.5 | 23 | 23.5 | 23.5 | ours, all three |
| `-443833341` | other integrality | continuous | 37083.33 | 36900 | 37083.33 | 37083.33 | ours, all three |

## Code

- **`scripts/amendment5.py`** checks the data's hash, matches by exact text (refusing any
  cleaned problem without one exact match), and computes the rows from the committed run.
  `python scripts/amendment5.py` prints them.
- **`scripts/eval_json.py`** writes them to `results/eval.json` as `amendment_5`; no existing
  key changes.
- **`tests/test_amendment5.py`** checks the rows against the run and the data (skipped
  without the data), and the matching rule. **`tests/test_readme_numbers.py`** now checks this
  file's "The rows" section too.
- **No module in `src/opt_agent/` changes.** The rows use the frozen scoring and the external
  cross-check's own matching and tolerance as they are.
