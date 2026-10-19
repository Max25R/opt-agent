# Pre-registration: the milestone 6 evaluation

**Status: DRAFT (Claude, 2026-10-19). Not approved.** No test-split run happens until the
owner approves this file. After approval, any change goes in "Amendments" at the bottom,
with its date and reason, and the test split is run **once**, with everything frozen.

Items marked **DECISION** are the owner's call; each has a proposed default.

Counts below come from the committed ground truth (`data/nl4opt/ground_truth/`,
`REPORT.md`). They'll be regenerated, not retyped, when this file is finalized.

## 1. What is measured

- **Problems:** the scorable test problems (`ground_truth.scorable`): 276 of 289. They
  exclude rejected annotations, annotation errors that change the answer, untrusted
  answers (CBC and HiGHS disagree, or an arithmetic check fails), and the two problems
  used while building the agent (`data/nl4opt/exclusions.json`).
- **The answer** is the status and, if optimal, the objective value. Variable values aren't
  compared: alternative optima are equally right.
- **The system's answer** is what the pipeline reports: the final model's status and
  objective, and only if `Result.confirmed` (both solvers agree and the checks pass). No
  confirmed answer (solvers disagree, time-out, solver error, API error, failed check)
  counts as **wrong**. The problem is never dropped.
- **Correct** means `ground_truth.matching_reading` finds a match: same status, and for an
  optimum, objectives equal within 1e-6 relative (1e-6 absolute near zero;
  `ground_truth.same_value`). The reading that matched is recorded for every problem.
  - **DECISION:** the tolerance. Proposed: 1e-6. Both sides are solver output for models
    of the same problem, so a looser tolerance (e.g. 1e-4) would mostly accept near-misses
    from wrong coefficients.

## 2. Conditions

All conditions use the same model (`claude-haiku-5-5`), the same pinned request settings
(`api.py`: adaptive thinking, medium effort, 16,000 max tokens), and system prompts whose
hashes are frozen (section 6).

1. **No-solver baseline:** Claude answers the problem directly, with no solver. The prompt
   is fixed in milestone 6, on dev only, before approval.
2. **Single-shot:** one formulation, solved and checked (`max_attempts=1`).
3. **Self-correction:** up to 3 attempts (`max_attempts=3`). Its first attempt is
   byte-identical to single-shot, so with the response cache the two are a paired
   comparison on the same first replies.
4. **Perturbed numbers:** the same problems with their numbers changed and the ground
   truth recomputed from the changed annotations. This tests whether answers come from
   the text or from memory. The perturbation rule is fixed in milestone 6, on dev only,
   before approval.

Prompts are iterated on the dev split only.

## 3. Rules by kind of problem

**a. Infeasible or unbounded as written** (verdict `text-has-no-optimum`; 20 scorable test
problems: 17 infeasible, 3 unbounded).
- The correct answer is the status.
- A revision that "fixes" the text into having an optimum is wrong, even if it is flagged.
- Self-correction is the condition most tempted to do that, so this subset is reported
  separately (section 5), with the change flags.

**b. Do-nothing optima** (verdict `degenerate-text`; 14 scorable test problems, all with
objective 0).
- Scored like any other problem. The answer, 0, is right as written.
- They're also reported as a separate subset. A model that drops constraints reaches 0 too,
  so these problems can't tell a right model from a careless one.
- 3 of the 14 have a nonzero optimum under the strict reading (rule e), which is accepted.

**c. Ambiguous text** (verdict `ambiguous-text`; 3 scorable test problems). Each has two
defensible readings, for example "three times as many": >= or =.
- **DECISION.** Proposed: leave them out of the primary metric, and report them separately
  with both readings' answers.
- Alternative: store the second reading's answer and accept either, as for strict wording.

**d. Text says "LP", but the label is integer** (4 scorable test problems where integrality
changes the answer: `1040407495`, `-1536845616`, `1703643437`, `1054847148`; all four
labels are Claude's).
- **DECISION.** Proposed, following the owner's dev decisions on `-640645082` ("text says
  LP, but trips are integer") and `892653388`: the label decides, so only the integer
  answer is accepted.
- The report says how many of these the system answered with the LP optimum.

**e. Strict wording** ("more than", "must exceed"; 25 scorable integer test problems).
- The annotated reading (>=) and the strict one (x > y as x >= y + 1, `strict.py`) are both
  accepted.
- The report gives how many correct answers needed the strict reading.
- The strict reading changes the answer in 9 of the 25.

**f. Integrality.** 131 of the 276 scorable test problems are integrality-sensitive (the LP
and IP optima differ).
- Their labels are all Claude's, and the formulation prompt uses the same rule of thumb.
  So the grader and the system under test can agree by construction.
- Therefore:
  - Accuracy is reported **separately** on the insensitive subset (145) and the sensitive
    one (131).
  - On the sensitive subset, a lenient accuracy is reported too: either the LP or the IP
    optimum is accepted.
  - The owner's blind labeling of 40 of the 131 (`review/integrality_blind/`, seed
    20261019) is reported next to the scores: the agreement, with its Wilson interval.

**g. Failures** are classified for every problem:
- **silent:** a confirmed answer that's wrong;
- **loud:** no confirmed answer, with the reason (solvers disagree, time-out, solver
  error, API error, unusable reply, refusal).

Silent failures are the dangerous kind, and they're reported first.

## 4. Statistics

- **Accuracy**, per condition and per subset, with a 95% Wilson interval (`stats.wilson`).
- **Paired comparisons** use McNemar's exact test (`stats.mcnemar_exact`) on the discordant
  pairs, which are reported alongside each test:
  - single-shot vs self-correction;
  - baseline vs single-shot;
  - baseline vs self-correction.
- Each comparison is run **separately** on problems whose answer has an optimum (256) and
  on problems whose answer is a status (20). The two kinds fail in different ways: a wrong
  number, or a "fix" of a problem that has no optimum.
- That makes 6 tests. Their p-values get Holm's correction together (`stats.holm`), at a
  family-wise alpha of 0.05.
- **DECISION:** whether the perturbed-numbers condition enters the family. Proposed: no.
  Report it with intervals only, as a robustness check.
- Any other comparison is exploratory and labeled so.
- **Latency:** p50 and p95 of `Result.latency_s` (API time plus solver time, without
  retries). Retry time and wall time are reported separately.
- **Cost** comes from the logged token usage, at the per-token prices published on the
  run date.

## 5. Reported subsets

Every table gives these rows, with n:
- all scorable;
- has an optimum / is a status;
- integrality-insensitive / sensitive (strict and lenient);
- do-nothing;
- strict wording;
- ambiguous (if excluded from the primary metric).

## 6. Frozen before the test run

The run's header line (`runs.environment`) already records the git commit, a dirty-tree
flag, and package versions. Milestone 6 adds the SHA-256 of each of these, and the run
refuses to start on the test split if any differs from the approved values:
- `data/nl4opt/reviews.json`, `integrality.json`, `exclusions.json`;
- `data/nl4opt/ground_truth/test.json`;
- the two system prompts (`formulate.SYSTEM_PROMPT`, `explain.SYSTEM_PROMPT`) and the
  schema (`formulate.LP_SCHEMA`).

Before freezing:
- the owner marks both packets in `review/`;
- disputed reviews are resolved;
- labels the owner changes are written to `integrality.json` with source `owner`.

## 7. Reporting

- Every number in the README comes from `results/eval.json`, generated by the evaluation
  code, and a test enforces this.
- Results are reported as they come out, including any condition that doesn't help.

## Open decisions

1. The match tolerance (section 1): 1e-6 proposed.
2. Ambiguous problems (3c): leave them out of the primary metric, proposed.
3. Text-says-LP problems labeled integer (3d): the label decides, proposed.
4. Perturbed numbers in the McNemar family (section 4): no, proposed.

## Amendments

None yet.
