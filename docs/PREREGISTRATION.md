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
  confirmed answer (solvers disagree, solver time-out, solver error, failed check)
  counts as **wrong**. An API error is re-run first (Amendment 1). The problem is never
  dropped.
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
   approval. It asks for the objective unrounded (at least 8 significant digits), since
   answers are scored at 1e-6 and the solver gives the other conditions full precision.
2. **Single-shot:** one formulation, solved and checked (`max_attempts=1`).
3. **Self-correction:** up to 3 attempts (`max_attempts=3`). Its first attempt is
   byte-identical to single-shot, so with the response cache the two are a paired
   comparison on the same first replies.
4. **Perturbed numbers:** the same problems with their numbers changed and the ground
   truth recomputed from the changed annotations. This tests whether answers come from
   the text or from memory.
   - **Decided (owner, 2026-10-28): all three conditions run on it.** The no-solver
     baseline is the condition most exposed to recalled answers.
   - **The rule** (`perturb.py`, fixed on dev, seed 20261028): every annotated number
     written in digits, except 1, is scaled by a factor drawn log-uniformly from [1/2, 2]
     and rounded to the original's precision (no more significant digits, the same
     decimal places and symbols), so the new numbers look like the old ones. Numbers in
     words ("twice") stay. A percentage stays below 100, and no two numbers get the same
     new text.
   - **A draw is kept** only if the perturbed problem is the same kind of problem with a
     new answer: the same judgment calls, every solve checks out, an optimum that does
     something, integrality changes the answer exactly where it did before (so every
     label that picks an answer is still a hand label), and no answer accepted for the
     original is accepted for it, even at 1e-4. Otherwise it's drawn again, up to 200
     times.
   - **Problems:** 242 of the 276 scorable test problems: those with an optimum that does
     something and no known annotation error. A problem whose answer is a status can't
     test memory, since the same status would still be right.
   - **Reported**, with no tests (section 4): accuracy with Wilson intervals per condition
     and subset; per condition, the answers that equal the original problem's answer; and,
     paired with the main run on the same problems, how many were right on the original
     only and on the perturbed one only.

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
  reply, invalid JSON, a failed validation, and a missing objective for "optimal". An API
  error isn't a reply, so it's re-run (Amendment 1). There is one attempt and no
  revision.
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
  - It's stored next to the annotated answer (`Record.equality`). `matching_reading`
    accepts it and records which reading matched.
- **Decided (owner, 2026-10-30, from the dev runs): the same holds, by rule, for every
  ratio constraint (x >= k·y, or <=) whose wording names no inequality**: "must be twice
  as many", "have three times the number of" (`nl4opt.ratio_wording`). The annotator chose
  the inequality; the text reads as "=" at least as naturally.
  - Why: the rule changes the answer in 4 scorable dev problems, and in both dev passes
    every condition answered each of those 4 with exactly its "=" answer.
  - On test, the rule gives 8 scorable problems an "=" reading and changes the answer in
    3: two of the reviewed problems above, and `-2015083686`. (The third reviewed problem
    says "2 times more", which names an inequality, so only its review covers it.)
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
  the blind sample. (Amendment 2: two LLM judges label them instead.)
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
    (Amendment 2: two LLM judges label them instead, and may answer `either`.)

**g. Failures** are classified for every problem:
- **silent:** a confirmed answer that's wrong;
- **loud:** no confirmed answer, with the reason (solvers disagree, solver time-out,
  solver error, unusable reply, refusal, or an API error that outlasted every resume
  pass: Amendment 1).

Silent failures are the dangerous kind, and they're reported first. Each one also gets a
hand label for its cause (section 5a).

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
  reported with intervals and counts only (section 2, condition 4), as a robustness check.
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

## 5a. Hand checks of the run

Two checks are done after the test run, from packets the code builds in `review/`: by an
LLM judge, not by the owner (Amendment 2). The blind grading comes
first, since the taxonomy packet shows which answers are wrong.
Both are reported with counts and intervals, with no tests.

**Blind grading** (`blind_grading.py`). The score compares answers, not models. A wrong
model can still reach an accepted answer, and a right one can miss when the reference reads
the text another way or is wrong. So:
- **The pool** is every distinct final model with a confirmed answer, from single-shot and
  self-correction (a model both gave counts once), on the blind-gradable problems: scorable,
  with no known annotation error, since the reference model is shown.
- **The sample** (seed 20261030): up to 20 models scored wrong, and models scored right to
  make 40, in shuffled order. Wrong answers are rare, so an unstratified sample of 40 would
  hold too few of them to say anything.
- **The owner grades** each model `right`, `wrong` or `unsure` against the text, next to
  the reference model and its integrality label, without seeing any answer, score,
  condition or problem id.
- **Reported:** for the models scored right, how many were graded wrong, and for those
  scored wrong, how many were graded right; each stratum's agreement with its Wilson
  interval (`unsure` counted, but kept out of the rate); and every disagreement, listed.
- **Known limit:** the owner knows the sample is about half wrong by design, far above the
  run's rate, and has seen the reference models while confirming the reviews.

**Error taxonomy** (`taxonomy.py`). Every distinct silent failure of the main test run, in
every condition, gets one category: its main error, the one whose fix alone would give an
accepted answer, if there is one. Any others go in a note. The categories were drawn up
from the dev failures (`review/taxonomy/dev-1/`), and a failure that fits none is `other`:

| category | meaning |
|---|---|
| `objective` | optimizes the wrong quantity, or in the wrong direction |
| `constraint-scope` | a limit applied to the wrong set of things: one combined limit read as one per item, or the reverse |
| `missing-constraint` | leaves out a requirement the text states (also when a revision deleted it) |
| `invented-constraint` | adds a requirement the text doesn't state |
| `coefficient` | a wrong number: misread, attached to the wrong variable, or converted between units wrongly |
| `direction` | a constraint points the wrong way (at least vs at most), and no accepted reading allows it |
| `integrality` | whole numbers vs fractions differ from the label |
| `rounding` | the right answer, rounded too far to match at 1e-6 (baseline) |
| `calculation` | no misreading found that gives this answer: a slip in the arithmetic or in finding the best choice (baseline) |
| `reference` | the system's reading is one the text supports but no accepted reading allows, or the reference is wrong |
| `other` | none of these, with a note |

Reported: per condition, the number of silent failures in each category. Loud failures
keep their automatic kinds (3g). A `reference` label doesn't change the score: the ground
truth is frozen, and those failures stay wrong.

## 6. Frozen before the test run

The run's header line (`runs.environment`) already records the git commit, a dirty-tree
flag, and package versions. Milestone 6 adds the SHA-256 of each of these, and the run
refuses to start on the test split if any differs from the approved values:
- `data/nl4opt/reviews.json`, `integrality.json`, `exclusions.json`;
- `data/nl4opt/ground_truth/test.json`;
- the two system prompts (`formulate.SYSTEM_PROMPT`, `explain.SYSTEM_PROMPT`) and the
  schema (`formulate.LP_SCHEMA`);
- the baseline's system prompt and its answer schema (section 2a);
- the perturbation code and its seed (condition 4), and the perturbed problems it made,
  `data/nl4opt/ground_truth/test-perturbed.json`;
- every source file in `src/opt_agent/`: answers depend on code as well as on the prompts
  above (the messages self-correction sends Claude are written by `feedback.py`, and the
  solvers, the checks and the scoring are code);
- `requirements.lock`, with every installed package at its locked version;
- this file, `docs/PREREGISTRATION.md`, as approved.

The approved values are `docs/FREEZE.json`, written by the owner with
`python -m opt_agent.freeze approve`. It refuses until the steps below are done, the
ground truth is rebuilt from the final hand inputs, and the tree is committed
(`python -m opt_agent.freeze` lists what's left). Every pass of a test run checks the
values first and records its fingerprint, so the report shows whether every pass ran on
the approved inputs. A test run covers every scorable problem in all three conditions; a
subset is refused.

Before freezing:
- the owner marks the packets in `review/` (blind labels, test reviews, and the 4
  "says LP" labels; Amendment 2 gives the labels to two LLM judges, and replaces most of
  the review confirmations with an external cross-check);
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

### Amendment 1 (owner, 2026-10-28): API errors and stopped runs

Made while this file is still a draft. It replaces "an API error counts as wrong" in
sections 1, 2a and 3g.

- **An API error isn't an answer.** A call that still fails after `api.call`'s own retries
  (8 tries, with backoff or the wait the server names) leaves its (problem, condition) pair
  **errored**: logged, not scored. That covers rate limits (429), server errors (5xx,
  including 529 overloaded), API time-outs, network errors, and any other error response.
  A run stopped by the budget cap or the account's spend limit leaves its remaining pairs
  **pending**.
- **Errored and pending pairs are re-run on resume** until none remain. Calls that already
  succeeded replay from the response cache, so a re-run never repeats a paid call and
  never asks Claude again for a reply it has already given.
- **A pair still errored after the first run and 3 resume passes counts as wrong** (a loud
  failure, reason "API error"). The report lists those pairs separately, with their
  errors. A resume pass is one re-run of the evaluation command. A pair that a stop left
  pending hasn't used up a pass.
- **Claude's replies are scored as they stand.** A refusal, a cut-off reply, or a reply
  that fails the schema or validation is a reply, not an error. It counts as wrong (a
  loud failure) the first time. It's cached, so every resume replays it and gets the same
  result. Within its 3 attempts, self-correction still revises an unusable reply, as in
  section 2.
- **The report says how many pairs needed re-runs**, per condition, and how many passes
  each one took.
- A solver time-out is still a loud failure (section 1): it's about Claude's model, not
  the API.

### Amendment 2 (owner, 2026-11-02; revised 2026-11-04): LLM judges and an external cross-check

Made while this file is still a draft. It changes who does the hand checks of section 5a,
who labels integrality for 3d and 3f, how the test reviews are confirmed before freezing
(section 6), and what the report shows next to each accuracy (sections 4 and 5).

**1. LLM judges do the hand checks (5a), not the owner.**
- **The judge of record** is Claude Opus 5.5 in Claude Code ("extra"), the owner's
  choice. It does the blind grading, the taxonomy, and the integrality labels (part 3).
- **A second judge, from another vendor:** the free version of ChatGPT labels integrality
  too (part 3). That's the one check where a Claude judge would be checking labels Claude
  wrote. The free version may not say which model answered, so its sheet records what it
  shows, and the date.
- **The same-vendor limit:** the system under test, the author of the labels and reviews,
  and the judge of record are all Claude, and may share blind spots. Blind grading and
  the taxonomy have no cross-vendor check. Part 4 keeps every headline number from
  resting on a judge's labels alone.
- **What a judge gets:** the generated prompt, byte for byte, in a new conversation with
  nothing else. The judge of record runs in a Claude Code session started outside this
  repository, so it can't read the run, the labels or the other packets. For blind
  grading that's `PACKET.md`; for the taxonomy, `LLM_PROMPT.md` (the same rows as the
  owner's packet, without naming the system or who wrote the labels); for the
  integrality labels, `review/integrality_judge/LLM_PROMPT.md`. Blind grading comes
  first.
- **Its reply** is saved verbatim next to the sheet and merged by row number (`--merge`).
  The merge refuses a reply that skips, doubles or shifts a row. The judge's name goes in
  the sheet's `grader` column, and the report lists the graders. A reply that can't be
  merged is asked for again in a new conversation, and every reply is kept.
- **Reported** as section 5a says, but called what it is: agreement between an LLM judge
  and the automatic score, not a human check. A judge makes mistakes of its own; the two
  judges' agreement on the integrality labels (part 3) is the only measure of them.
- **The dev pilot** (`review/blind_grading/dev-1/`) was graded by the judge of record. It
  checked the packet's format only, and its grades aren't reported as a result.

**2. An external cross-check replaces most of the owner's review confirmations (6).**
- **The source:** the corrected NL4OPT in ORLMBenchmark (`chenyitian-shanshu/ORLMBenchmark`,
  `NL4OPT.jsonl`, pinned by revision and SHA-256 in `data.py`; Apache-2.0), from the
  authors of the SIRL paper. It gives optimal values for 245 of NL4Opt's test problems.
- **The check** (`external_check.py`): each test problem is matched to the benchmark by
  normalized text, or to a benchmark text that edits a few of its words, and the
  benchmark's value is compared with the answers scoring accepts, at 1e-4 relative (the
  published values are rounded). The owner's list is `review/external_check.md`.
- **Where the benchmark agrees** with our answer, or with another accepted reading (strict,
  "="), the answer stands with no hand check, and so does the review, if there is one.
- **The owner decides every problem the list names:** each disagreement; each "other
  integrality" (the benchmark has our optimum with the other integrality, so the label is
  in question); and each problem whose text the benchmark edited, since an edit says its
  authors found the text wrong. A decision that changes the ground truth goes into
  `reviews.json`, or `integrality.json` with source `owner`, before the freeze.
- **Reviewed problems the benchmark doesn't have can't be cross-checked.** It has none of
  the do-nothing problems (3b) and lacks about a third of those with no optimum (3a), so
  these are most of the reviews it leaves. The owner still confirms those by hand
  (`confirmed_by_owner`).
- **Limits:** agreement isn't independent proof. The benchmark descends from the same
  NL4Opt problems, and possibly, through ORLM's answers, from the same annotations, so an
  error both inherit gets through. Its authors describe their review as quick. A
  disagreement is the informative signal.

**3. Both judges label integrality where the owner would have (3d, 3f).**
- **The problems:** the 40 of the blind sample (seed 20261019) and the 4 "says LP"
  problems, in one prompt (`review/integrality_judge/LLM_PROMPT.md`). It shows the text
  and the decisions' names, as the owner's blind packet does, with no label and no sign of
  which set a problem is from. Each judge answers in its own conversation, into its own
  sheet (`judge.csv`, `second_judge.csv`). The owner's packets (`review/integrality_blind/`,
  `review/says_lp.md`) aren't used.
- **A label is per problem:** `integer`, `continuous`, or `either` (the text supports both
  readings, so both optima are accepted). It's per problem, not per variable, because the
  ground truth stores only the all-integer and the all-continuous optimum. The dev pilot
  showed why `either` is needed: the judge was unsure about an integrality choice the text
  supports both ways (the method runs of dev `-577606329`).
- **The label that scores:** where both judges give the same label, that's the problem's
  label (source `judge` in `integrality.json`); where they differ, it's `either`. This
  replaces the owner's labels in 3d and in section 6. So on the 4 "says LP" problems the
  judges' label decides, and an `either` there accepts the LP optimum too. Every other
  label stays Claude's (or the rule's).
- **The agreement statistic (3f)** is reported for each judge against Claude's labels on
  the 40, and for the two judges against each other: how many give the same label, a
  different one, or `either`, and the Wilson interval of "the same label or `either`" (a
  label the judge accepts). The second judge's is the independent one. The 4 "says LP"
  problems stay out of it, as before.

**4. Lenient accuracy next to every strict one (4, 5).**
- Every accuracy the report gives, per condition and subset, comes with its lenient version
  beside it: integrality not graded, so either optimum is accepted (3f's lenient score,
  now on every row, not only the sensitive subset). So no headline number rests only on
  labels, whether a judge's or Claude's. On the integrality-insensitive subset the two
  are equal by construction.
- The McNemar tests stay on the strict scores, as pre-registered. The same six on the
  lenient scores are reported next to them as exploratory, outside the Holm family.

**Code:** once this amendment is approved, `freeze.unfinished()` will require both judges'
sheets filled, their combined labels applied to `integrality.json`, the owner's decision on
every problem `review/external_check.md` lists, and `confirmed_by_owner` only for reviews
the benchmark doesn't cover. It will no longer ask for the owner's `labels.csv` or "says
LP" labels. The `either` label, the agreement counts and the lenient rows come with it.
Until then, all of it is unchanged.
