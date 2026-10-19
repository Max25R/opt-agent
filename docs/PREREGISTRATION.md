# Pre-registration: the milestone 6 evaluation

**Status: DRAFT (Claude, 2026-10-19). Not approved.** No test-split run happens until the
owner approves this file. After approval, any change goes in "Amendments" at the bottom,
with its date and reason, and the test split is run **once**, with everything frozen.

The owner settled the four open decisions on 2026-10-19; each is recorded where it
applies, under "Decided". The draft as a whole is still unapproved.

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
  - **Decided (owner): 1e-6.** Both sides are solver output for models of the same
    problem, so a looser tolerance would mostly accept near-misses from wrong
    coefficients.
  - **Sensitivity:** the report also gives, per condition, how many answers would flip
    (wrong to right, or right to wrong) at 1e-4 instead.

## 2. Conditions

All conditions use the same model (`claude-haiku-5-5`), the same pinned request settings
(`api.py`: adaptive thinking, medium effort, 16,000 max tokens), and system prompts whose
hashes are frozen (section 6).

1. **No-solver baseline:** Claude answers the problem directly, with no solver. It's
   scored as in section 2a. Its prompt is fixed in milestone 6, on dev only, before
   approval.
2. **Single-shot:** one formulation, solved and checked (`max_attempts=1`).
3. **Self-correction:** up to 3 attempts (`max_attempts=3`). Its first attempt is
   byte-identical to single-shot, so with the response cache the two are a paired
   comparison on the same first replies.
4. **Perturbed numbers:** the same problems with their numbers changed and the ground
   truth recomputed from the changed annotations. This tests whether answers come from
   the text or from memory. The perturbation rule is fixed in milestone 6, on dev only,
   before approval.

Prompts are iterated on the dev split only.

## 2a. Scoring the no-solver baseline

The baseline has no model to solve, so there's no `Result.confirmed`. Its answer is what
Claude states, scored as it stands:

- **The request** uses the same model and pinned settings as the other conditions, with
  its own system prompt. Its structured output schema asks for exactly
  `{"status": "optimal" | "infeasible" | "unbounded", "objective": number or null}`.
  Claude is asked for nothing else, such as variable values.
- **Parsing:** the reply is validated as that schema:
  - the status must be one of the three values;
  - for "optimal", the objective must be a finite number;
  - for the other statuses, the objective is ignored.
- **Unparseable counts as wrong** (a loud failure). That covers a refusal, a cut-off
  reply, invalid JSON, a failed validation, a missing objective for "optimal", and an API
  error. There is one attempt and no revision.
- **A parsed answer** is scored with `matching_reading` and the 1e-6 tolerance, exactly
  like the other conditions. A parsed wrong answer is a silent failure, since nothing
  checks it.

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
defensible readings of one constraint, ">= as annotated" or "=":

| problem | constraint | wording |
|---|---|---|
| `-1765797791` | `c0_xby` | "three times as many apple ... as carrot" |
| `-1715698555` | `c1_xby` | "must be three times the number of large bins" |
| `-169306566` | `c1_xby` | "2 times more protein bars than smoothies" |

- **Decided (owner): accept either reading, as for strict wording.**
  - The "=" reading's answer is computed the same way as the annotated one: that one
    constraint changed, solved, and cross-checked with HiGHS and arithmetic.
  - It's stored next to the annotated answer. `matching_reading` accepts it and records
    which reading matched.
  - This is still to be implemented, in milestone 6, before approval.
- The report gives how many correct answers needed the "=" reading.

**d. Text says "LP", but the label is integer** (4 scorable test problems where integrality
changes the answer: `1040407495`, `-1536845616`, `1703643437`, `1054847148`; all four
labels are Claude's).
- **Decided (owner): the label decides**, so only the labeled answer is accepted. This
  follows the owner's dev decisions on `-640645082` ("text says LP, but trips are
  integer") and `892653388`.
- **The owner labels these 4** (`review/says_lp.md`), so their labels become the owner's.
  They're kept out of the blind-agreement statistic: that statistic measures Claude's
  labels against the owner's blind ones, and these won't be Claude's. None of the 4 is in
  the blind sample.
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
- **Decided (owner): the perturbed-numbers condition stays outside the family.** It's
  reported with intervals only, as a robustness check.
- **The status subset (20 problems) is for failure patterns, and is underpowered for
  significance.** Its job is to show which problems a condition gets right as written
  and which it "fixes" into having an optimum.
  - Its tests stay in the Holm family, so the correction stays honest.
  - A comparison on it reaches p < 0.05 alone only if at least 6 of the 20 problems are
    discordant, all in the same direction. As the smallest p in the family, it needs at
    least 8.
  - A non-significant result there is not evidence of no difference.
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
- ambiguous (either reading accepted);
- text says "LP" but labeled integer.

## 6. Frozen before the test run

The run's header line (`runs.environment`) already records the git commit, a dirty-tree
flag, and package versions. Milestone 6 adds the SHA-256 of each of these, and the run
refuses to start on the test split if any differs from the approved values:
- `data/nl4opt/reviews.json`, `integrality.json`, `exclusions.json`;
- `data/nl4opt/ground_truth/test.json`;
- the two system prompts (`formulate.SYSTEM_PROMPT`, `explain.SYSTEM_PROMPT`) and the
  schema (`formulate.LP_SCHEMA`);
- the baseline's system prompt and its answer schema (section 2a);
- the perturbation code and its seed (condition 4);
- this file, `docs/PREREGISTRATION.md`, as approved.

Before freezing:
- the owner marks the packets in `review/` (blind labels, test reviews, and the 4
  "says LP" labels);
- disputed reviews are resolved;
- labels the owner changes are written to `integrality.json` with source `owner`.

## 7. Reporting

- Every number in the README comes from `results/eval.json`, generated by the evaluation
  code, and a test enforces this.
- Results are reported as they come out, including any condition that doesn't help.

## Decisions (owner, 2026-10-19)

1. Match tolerance (section 1): 1e-6, with a count of answers that would flip at 1e-4.
2. Ambiguous problems (3c): either reading is accepted, and the one that matched is
   recorded.
3. "Says LP" problems labeled integer (3d): the label decides. The owner labels the 4, and
   they're kept out of the blind-agreement statistic.
4. Perturbed numbers (section 4): outside the McNemar family.

## Amendments

None yet.
