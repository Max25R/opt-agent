# History

The project's record, milestone by milestone: what was built, decided and checked, with its
dates. It was kept in `CLAUDE.md` until 2026-11-16, when it moved here (the final review,
item S11), so that `CLAUDE.md` holds only the working rules. The entries are as they were
written, so each status is as of its date, and paths can have moved since (for example
`scripts/historical/`). Where things stand now is in [`HANDOFF.md`](HANDOFF.md), and every
result is in `results/eval.json` and `results/followup.json`. Notes added later are marked
as such.

1. [x] Setup: src layout, pyproject, `.env` handling, pytest + ruff CI.
2. [x] LP schema + solver, verified with known answers, plain-arithmetic checks,
   Hypothesis CBC-vs-HiGHS agreement, and metamorphic tests.
3. [x] Ground truth from raw annotations (no LLM). Done 2026-10-16; the owner confirmed
   the dev walkthrough and their corrections are applied. NL4Opt has formulations but **no
   answers**. `ground_truth.py` converts them, solves each as an LP and as an all-integer
   IP, cross-checks with HiGHS and arithmetic, and compares with ORLM. Flagged problems
   carry a hand review, and each problem's integrality label picks its answer
   (`ground_truth.answer`). Counts are in the generated `REPORT.md`.
4. [x] LLM formulation (2026-10-17). `formulate.py` sends the problem through
   `messages.create` with structured output (`output_config.format`, using the SDK's
   public `anthropic.transform_schema(LPModel)`), then validates it with our own
   `LPModel`, so a bad reply becomes a readable `error` for milestone 5. `explain.py`
   builds facts from the solver and flags any number in the explanation that isn't a
   correct rounding of a fact or input. `agent.py` runs the pipeline and has a CLI.
5. [x] Self-correction loop (2026-10-19; built and tested with `FakeClient` only, since
   there's no API key yet). `self_correct.solve_with_revisions`: up to 3 attempts. Each
   revision is a self-contained request (problem + previous reply + feedback), so every
   attempt can be logged, cached, and replayed alone. Stops on optimal, the attempt limit,
   an unchanged model (Claude stands by it), a refusal, a solver time-out or error, a
   CBC/HiGHS disagreement, or an API error; only the first three are Claude's doing.
   `max_attempts=1` is the single-shot baseline. Feedback is sent only when both solvers
   agree. Infeasibility feedback names an IIS (deletion filter,
   `feedback.conflicting_constraints`, which first confirms the whole set is infeasible).
   `changes.compare` flags deleted or loosened constraints (rhs, direction, or
   coefficients), loosened bounds, relaxed integrality, removed variables, variables
   dropped from the objective, and a flipped objective. Since M7 (audit finding 6) it pairs
   constraints by structure (identical, then name, then same variables) and also flags any
   direction flip, any edit to an equation, and a negated objective coefficient.
   - **Pre-milestone-6 fixes (2026-10-19, from a health check; Batches A-D):**
     certified rays and LP duality certificates (`rays.py`, `verify.optimality_problems`);
     `Status.TIMEOUT`; `answer()`/`scorable()` require a trusted answer; one request
     dict per call with pinned settings, our own timed retries, and a response cache
     (`api.py`); a run log with git SHA and package versions (`runs.py`); dev-only
     fixtures and two excluded test problems; the strict reading (`strict.py`);
     `Result.confirmed`; the owner's packets (`review/`, `packets.py`); a draft
     pre-registration (`docs/PREREGISTRATION.md`); `requirements.lock`.
   - **Before milestone 6 (all done):** the owner ran `freeze approve` on 2026-11-04
     (`docs/FREEZE.json`, commit 8f522c0). The
     pre-registration was approved as a whole on 2026-11-04 (owner), with Amendments 1-2. Prices
     re-checked the same day, before the freeze: unchanged (`PRICES_CHECKED`). The owner
     approved the test-run plan: `--cap 1.60` for `runs/test` and `--cap 1.40` for
     `runs/test-perturbed` ($3 in all), run from the owner's terminal (the sandbox
     breaks Python's TLS here). Amendment 2's
     judges, cross-check and review outcomes are all applied (2026-11-04). The owner's own
     packets (`review/integrality_blind/`, `review/says_lp.md`, `review/test_reviews/`) are
     no longer used, and are kept as sent: the review packet's label lines predate the
     judges' labels. Also the owner's, on dev: label
     `review/taxonomy/dev-1/` (after the optional blind pilot, `review/blind_grading/dev-1/`),
     which settles the pre-registered categories. [Note added 2026-11-16: never done;
     `review/taxonomy/dev-1/labels.csv` has 0 of 7 rows labeled.] (The "=" reading, the
     1e-4 count,
     Amendment 1, the perturbation rule, the freeze checks, the baseline's prompt and the
     hand-check packets are done; see milestone 6.)
     `python -m opt_agent.freeze` lists what's left before the owner can freeze. Known and
     unfixed: the integrality rule matches ingredient names ("units of chicken" meat), so
     it labels countable products continuous in at least 4 reviewed test problems
     (bubble teas, crepes, curry bowls, and the wine/kombucha problem; harmless for the
     annotated answers, but not for the strict reading: 4 answers per condition, see
     DEVIATIONS.md section 3; fix after M6, and check the unreviewed rule labels too); `DEV_WALKTHROUGH.md` predates the owner's milestone 3
     corrections (the owner decides whether to regenerate it); no Farkas certificate for
     infeasible LPs; the CLI needs a key even when every call is cached (still open after milestone 8).
   - **Pre-milestone-6 step 1 (2026-10-28):** the key works; the live tests passed (5
     calls, $0.0025). Added the budget guard (`budget.py`, `pricing.py`), spend-limit
     stops (`api.SpendLimitReached`), the no-solver baseline (`baseline.py`), and a
     resumable dev-only runner (`evaluate.py`). A 3-problem dev smoke test of all three
     conditions cost $0.0042; the milestone 6 projection was about $0.71 (high: $2.06).
     Owner's decisions the same day: a $3 cap for the test + perturbed run; the model
     stays Haiku 5.5 (at Sonnet 5.5's prices the same projection is $14.29, high $41.19);
     API errors per pre-registration Amendment 1 (approved the same day); and dev
     793774916, a silent failure self-correction can't catch, goes in
     `docs/FAILURE_LOG.md`. **Don't tune prompts to fix a single dev problem.**
6. [x] Evaluation. Iterate on prompts with the dev split only, then run test once with
   everything frozen. Conditions: no-solver baseline, single-shot, self-correction, plus
   a perturbed-numbers set. Report Wilson CIs, McNemar's test, the silent-vs-loud failure
   split, p50/p95 latency, and cost from real token usage. Use a hash-keyed response
   cache and a hand-labeled error taxonomy. Prepare a blind-grading packet.
   - **Step 1 of the dev-only plan, scoring and report (2026-10-28; no API calls):**
     - **Runs record answers; `report.py` scores them.** An `evaluate.Item` holds the
       status and objective (or `no_answer`: the kind of loud failure), the pass
       (`run_id`), revision flags, and time and cost, but no verdict. `scoring.score`
       scores it against the ground truth, so a corrected review or the 1e-4 count is a
       re-scoring, never a paid re-run.
     - **A run directory is one experiment.** `manifest.json` fixes the split, problems,
       conditions, model and settings hashes; a resume that differs is refused. The
       manifest is the report's denominator: a pair with no line is pending, never
       missing. A report with open pairs says it's incomplete.
     - **Amendment 1 is in `report.py`:** after the first pass and `RESUME_PASSES` (3), an
       errored pair counts as wrong ("api error") and is listed; re-runs are counted.
     - **`report.build`** gives everything sections 1, 3, 4, 5 and Amendment 1 ask for:
       Wilson intervals per condition and subset, lenient accuracy (`readings(...,
       lenient=True)`: either integrality, no other change), which reading each correct
       answer needed, flips at 1e-4, LP optima on "says LP" problems, claimed optima on
       status problems with flags, silent ids and loud kinds, the 6 McNemar tests with
       Holm, p50/p95 latency (numpy's linear interpolation; done pairs only), retry and
       wall time over every pass, tokens, cost, and the owner's blind-label agreement for
       test runs. `subsets()` reproduces every pre-registered count. Same inputs, same
       JSON (no timestamps), with provenance (manifest, each pass's commit, input hashes,
       prices).
     - The smoke run (`runs/smoke`, given a manifest after the fact) reports exactly the
       step 1 numbers.
     - `results/eval.json` and the README-number test came after the test run (see
       "The test runs and the results" below).
   - **Step 2, the perturbed-numbers set (2026-10-28; no API calls):** all three
     conditions run on it (owner's decision). `perturb.py` (the rule is its docstring)
     changes every annotated number written in digits except 1, by a log-uniform factor in
     [1/2, 2] rounded to the original's precision, keyed by the span's exact text
     (declarations copy span texts verbatim, so text and formulation stay consistent; all
     2,806 do). It rebuilds the ground truth with `build_record` and keeps a draw only if
     the problem is the same kind with a new answer: same notes, every solve checks out, an
     optimum that does something, **integrality matters exactly where it did** (in a trial build
     without it, 58 of 242 perturbed test problems let the unreviewed rule label pick the
     answer), and no
     original answer is still accepted at 1e-4. Up to 200 draws (dev's worst needed 107);
     every eligible problem got one. `{dev,test}-perturbed.json` keep the original ids, so
     runs pair by id; `PERTURBED.md` has the counts. The runner accepts `--split
     dev-perturbed` (test splits still wait for the freeze checks). On a perturbed run,
     `report.py` runs no McNemar tests (outside the family), lists answers equal to the
     original problem's, and with `--original RUN` gives paired counts. The pre-registration
     draft's condition 4 now states the rule (not yet approved).
   - **Step 3, the freeze (2026-10-29; no API calls):** `freeze.fingerprint()` hashes
     section 6's list, **every source file in `src/opt_agent/`** (the list named prompts,
     but `feedback.py` writes what self-correction sends Claude, and solvers, checks and
     scoring are code too) and `requirements.lock`; installed packages must match the lock.
     **`python -m opt_agent.freeze approve` is the owner's step, never Claude's**: it
     refuses until `freeze.unfinished()` is empty (since Amendment 2: the pre-registration
     approved, both judges' sheets filled and their combined labels applied, a decision
     on every row of `review/external_check.csv`, the reviews it can't cover
     `confirmed_by_owner`, and a ground truth rebuilt from the final hand inputs) and the tree is
     committed, then writes `docs/FREEZE.json`. `evaluate()` refuses a test split
     (`FreezeError`, before writing anything) unless `freeze.check()` passes, and refuses a
     subset: a test run is `--all` in all three conditions. `--plan` needs no freeze, so
     the owner can see a test run's worst case first. Every pass's log line records its
     fingerprint digest; the report's provenance says whether every pass ran on the
     approved one. Section 6 of the draft now names the code and the lock.
   - **Step 4, the first dev runs (2026-10-29; owner approved $0.50 caps):** `runs/dev-1`
     (all 92 scorable dev problems, 188 paid calls, $0.0955) and `runs/dev-perturbed-1`
     (85, 170 calls, $0.0857); no API errors, no loud failures. Prices re-checked first
     (unchanged). Baseline 84/92, single-shot and self-correction 85/92; on the perturbed
     set no answer equaled the original problem's and accuracy held, so no sign of
     memorization. Self-correction revised 4 times (Claude stood by each status model) and
     changed no answer. Four dev failures in every condition were "twice as many" read as
     "=", which led to the owner's ratio-wording rule (3c, 2026-10-30); the dev runs were
     re-scored with it, with no new calls. Other failures, for the error taxonomy: baseline
     rounding (2 answers wrong at 1e-6 only because they were rounded; a baseline-prompt
     question for step 5), `562583112` (the objective read as the count of drones and
     couriers), `-577606329` (an integrality label every condition disagreed with), and
     run-to-run sampling (the bakery and the volcano problems).
   - **Step 5, prompts (2026-10-30; owner approved $0.25 caps):** one change, to the
     baseline prompt: give the objective unrounded (at least 8 significant digits, with
     2/3 as a generic example). The formulation prompts are unchanged (the pipeline's
     remaining dev failures are one-offs). Baseline re-runs: `runs/dev-2-baseline` 90/92
     ($0.0420) and `runs/dev-perturbed-2-baseline` 83/85 ($0.0395); every non-whole answer
     now has 8+ digits, and no answer flips at 1e-4. The baseline's remaining failures are
     the pipeline's own two (`-577606329`, `562583112`), so on dev the baseline is as
     accurate as the pipeline: the pipeline's case rests on checked answers and loud
     failures, not accuracy. That was 1 of the 2 extra dev passes the plan allows. Total
     spent so far: $0.2693.
   - **Step 6, the hand checks (2026-10-30; no API calls):** two run packets, both for
     after the test run, pre-registered in the draft's new section 5a. Both read a run
     back with `run_results.py` (split out of `report.py`: the scored pairs, and each
     answer's final model from the attempt log) and key their sheet rows by a hash of the
     problem and the model (`model_key`; `answer_key` for the baseline), so a regenerated
     packet keeps the owner's marks (`packets.kept_marks`).
     - **Blind grading** (`blind_grading.py`): the owner grades Claude's models against
       the text, next to the reference, with no answers, scores, conditions or ids shown.
       The pool is every distinct confirmed model on a blind-gradable problem; the sample
       (seed 20261030, 40) is stratified, up to half scored wrong, since wrong answers are
       rare. The report gives each stratum's agreement with a Wilson interval and lists
       every disagreement. It checks the score itself: a lucky right answer, or a
       reference that reads the text another way.
     - **Taxonomy** (`taxonomy.py`): every distinct silent failure gets one category, its
       main error, from 11 categories drawn up from the dev failures. The packet shows
       facts the scores give for free (correct if integrality weren't graded, within
       1e-4, revision flags, a baseline answer equal to a model's). The report counts
       categories per condition.
     - `report.build` has `hand_checks` ("pending" until a sheet is filled) and the
       sheets' hashes in its provenance. Dev packets: `review/taxonomy/dev-1/` (7
       failures) and a 10-model pilot, `review/blind_grading/dev-1/`.
   - **Owner's decision (2026-11-02): an LLM judge and an external cross-check**, as
     pre-registration Amendment 2 (approved 2026-11-04, below; the file as a whole is
     still a draft). The judge must be from another vendor than Anthropic, and is still to
     be named. Sheets have a `grader` column, and `--merge REPLY --grader NAME` writes a
     judge's CSV reply into a sheet, refusing skipped, doubled or shifted rows. The
     taxonomy also writes `LLM_PROMPT.md`, which doesn't name the system. The dev pilot was
     graded by Claude Opus 5.5 (same vendor: a format check only); its reply is
     `judge_reply.csv`. `external_check.py` compares test answers with the corrected
     NL4OPT in ORLMBenchmark (`data.ORLM_BENCHMARK`, Apache-2.0, git-ignored download)
     and writes `review/external_check.md`. That benchmark lacks every do-nothing problem
     and some no-optimum ones, so 24 reviews still need the owner.
   - **Revised, and Amendment 2 approved (owner, 2026-11-04):** the judge of record is Claude Opus 5.5
     in Claude Code ("extra"), run outside this repository; free ChatGPT is a second,
     cross-vendor judge on the integrality labels only (Claude wrote them). Both label the
     40 blind and 4 "says LP" problems per problem as integer, continuous or either
     (`packets judge` writes `review/integrality_judge/`; the owner's packets are untouched);
     a label they differ on becomes `either`. The report is to show lenient accuracy next
     to every strict one (McNemar on lenient scores as exploratory).
   - **Amendment 2 in `freeze.unfinished()` (2026-11-04):** `judged_labels()` (both sheets
     filled; `packets.combined_labels` applied to `integrality.json` with source `judge`,
     a new source) and `cross_check()` (reads the committed `review/external_check.csv`,
     which `external_check.py` now writes: 35 rows, `keep`/`change` for 11 listed
     problems, `confirmed`/`disputed` for the 24 uncovered reviews).
   - **The rest of Amendment 2 (2026-11-04):** `Integrality.kind` can be `either`, and
     `ground_truth.label_kinds` is the one place that says what a label accepts (`either`:
     both optima, the integer one standing for `answer()`, both solves trusted; the strict
     reading applies to it). `packets judge --apply` writes the judges' combined labels into
     `integrality.json` (source `judge`, keeping the kind it `replaced`); then rebuild the
     ground truth and the perturbed splits. `report.py`: `lenient accuracy` for every
     subset (replacing the sensitive-only entry), the six McNemar tests on lenient scores
     as `comparisons, lenient (exploratory)` (no Holm), and `integrality_agreement` from
     `packets.judges_agreement` (each judge against Claude's labels, and each other; an
     `either` "accepts" Claude's label). REPORT.md's wording changed; no ground-truth data did.
   - **Judges' integrality replies and Amendment 2 parts 5-6 (2026-11-04; parts 5-6
     approved and pushed before the review judges ran, so the rules came first):** both replies are merged (`review/integrality_judge/*_reply.csv` kept
     verbatim; ChatGPT's model wasn't recorded). They agree on 37 of 44 (36 of the 40);
     the combined labels turn 9 of Claude's integer labels into `either`, all 4 "says LP"
     among them, but they aren't applied yet (`packets judge --apply`, then rebuild).
     `review/external_check.csv` is filled by the owner's rules (part 5), with the rule in
     each note; 26 rows wait for the review judges. `external_check.py judges` writes
     `review/review_judge/` (the 24 uncovered reviews and the 2 hard cases,
     `HARD_CASES`; agree/disagree/unsure; both agree = confirmed, else disputed, `unsure`
     included; a hard case not confirmed is excluded). The prompt leaves out "ORLM found no
     solution" from one reason (`REDACTED`; reviews.json keeps it). The review judge of
     record is an incognito claude.ai chat: grader "Claude Opus 5.5 (claude.ai incognito)". Still to build after approval: applying the
     decisions (4 `either` labels, exclusions, review outcomes in `reviews.json`),
     `freeze` for them, and the report's 44-problem agreement, second-judge-only
     sensitivity check, and accuracy without disputed problems.
   - **Review judges and the rest of Amendment 2 (2026-11-04):** both replies merged
     (`review/review_judge/*_reply.csv` verbatim). `external_check judges --decide` fills
     the sheet by the rules: 16 reviews confirmed, 8 disputed (the second judge disputes
     all 8, the judge of record one, `1384123609`; 4 of the 8 are continuous rule labels
     on countable products with strict wording, the known ingredient-name issue), and both
     hard cases excluded. `external_check apply` wrote them in: `Review.judged`, 2 rows in
     `exclusions.json`, 4 `either` labels (source owner), after `packets judge --apply`'s 44
     (13 `either` in all). The decision sheet keeps every decided row when regenerated,
     since applying takes problems off the list. Ground truth and perturbed splits rebuilt:
     274 scorable (was 276), 240 perturbed (was 242), "says LP, labeled integer" empty;
     the pre-registration's counts regenerated and tested. `freeze.cross_check` checks the
     judged rows follow the replies and every decision is applied; `readings` accepts the
     strict reading only where the label accepts whole numbers. `report.py`: accuracy
     without disputed reviews, the second judge's labels alone (test), the judges'
     agreement on all 44, and a note on the empty "says LP" subset.
   - **The test runs and the results (2026-11-04 to 2026-11-08; no API calls from here):**
     - **The runs:** the owner ran `runs/test` and `runs/test-perturbed` from their own
       terminal, on the frozen inputs, with 0 errored pairs ($0.52 paid in all).
     - **Amendment 3** (`docs/amendments/AMENDMENT_3.md`, tag `amendment-3`, committed
       before any judge saw a prompt): an exploratory, post hoc row that counts a shared
       failure as correct only when both judges label it `reference`, and blinded 5a prompts
       (`scripts/blind_taxonomy.py`).
     - **The 5a replies:** merged with the graders as they actually ran (claude.ai incognito
       chats and a ChatGPT Temporary Chat, web search off).
       `docs/amendments/DEVIATIONS.md` records how that differs from Amendment 2, and that
       the second judge's sheets record no date.
     - **Amendment 3's row:** `scripts/amendment3.py runs/test` adds it to
       `runs/test/report.json`. **A frozen `opt_agent.report` rebuild drops the row**, so
       run the script again after any rebuild.
     - **The results file:** `scripts/eval_json.py` writes `results/eval.json` from both
       reports, the runs, the 5a sheets and `docs/FREEZE.json`. It refuses a report without
       the row, and its tests check that the same inputs give the same bytes and that the
       committed file is current.
     - **The README check:** `tests/test_readme_numbers.py` (section 7) checks every number
       in the README's Evaluation section against `results/eval.json` (since M8: the whole
       README against both results files, and `docs/EVALUATION.md`), at the precision
       shown. It matches by value, not by place.
     - **Paths under `runs/` are git-ignored:** commit them with `git add -f`.
   - **After the audit (2026-11-08; `docs/audit/2026-11-review.md`, no API calls):**
     - **Tag `m6-freeze`** marks `8f522c0`, the commit both test runs ran on. Any change
       under `src/opt_agent/` (the first: `config.py`, the `.env` gate) makes
       `python -m opt_agent.freeze` report a mismatch at HEAD; rebuild M6 from the tag.
       `freeze.tag_problems()` checks the tag against `docs/FREEZE.json` from git's objects,
       and `tests/test_freeze.py` runs it, so CI checks the freeze against the tag, not HEAD
       (the workflow fetches every tag). Push the tag with the commits.
     - **The integrality-rule bug wasn't harmless:** a continuous label also switches off
       the strict reading, which cost 4 answers per condition (`docs/amendments/DEVIATIONS.md`,
       section 3).
     - **Amendment 4 (tagged `amendment-4`, 5f10814):** the omitted pre-registered rows (lenient, without
       disputed reviews) and an exploratory corrected-labels row (268/274 per condition).
       `scripts/amendment4.py` computes them; `eval_json.py` writes them as `amendment_4`;
       264/274 stays the result of record.
     - **M7 part 1 (robustness, audit findings 6 and 2):** integer bounds rounded inward in
       both solvers; `PulpSolverError` is a loud solver error; change flags compare
       constraints by structure; the cache key leaves out the SDK-built schema (M6's files
       found through `Cache`'s index); `agent.run(estimate=True)` adds a report-only
       low-confidence flag (its counts on M6's cache were reported to the owner, and are
       deliberately not in any results file).
     - **Formulation checklist (M7, report-only; owner's design, 2026-11-09):**
       `checklist.py` asks what a correct formulation must contain, given only the text and
       the model's variable names (no fuzzy mapping; a missing variable is a known gap), and
       `review` gives typed flags (integrality, coefficient, missing, extra,
       invented-from-preference, objective). `--checklist` in the agent CLI and `evaluate`;
       it changes no answer, score or revision. **Its prompt was designed after seeing the M6
       test failures:** tune on dev only (follow-up dev, NL4Opt dev); any M6 number from it is
       exploratory, labeled "prompt designed after seeing these failures", and never goes in
       `results/eval.json` or the README's results. **Follow-up split**
       (`docs/FOLLOWUP_SPLIT.md`): ComplexLP 25 dev / 86 test, IndustryOR all test; the test
       side is sealed (`followup.load` raises `Sealed`) until its pre-registration is frozen.
     - **Amendment 5 (tagged `amendment-5`, 1cb05ed):**
       external corroboration against LLM4OR's cleaned NL4Opt (`docs/EXTERNAL_DATA.md`, data
       git-ignored): it removed 5 of Amendment 4's six key errors. `scripts/amendment5.py` →
       eval.json `amendment_5`, which CI's test job copies forward (no data there) and its
       `reproduce` job rebuilds (it fetches the data).
7. [x] **M7: the follow-up study and the demo are done (2026-11-15). Start from
   `docs/HANDOFF.md`.**
   Done: part 1's robustness fixes;
   the formulation checklist with dev revision 1 (`docs/FOLLOWUP_DEV_LOG.md`: dev run
   `runs/dev-checklist`, $0 re-score `runs/dev-checklist-rev1`, mutation recall 97% for either
   check, an upper bound); a sample index in the cache key (`evaluate --sample n`).
   - **Follow-up pre-registration** (`docs/FOLLOWUP_PREREGISTRATION.md`; owner's decisions
     2026-11-10 to 2026-11-13 in its section 0): **approved and frozen 2026-11-13**
     (`docs/followup/FREEZE.json`, tag `followup-freeze` = `f36e812`; never edit it).
     H1 checklist-revision vs single-shot, H2 single-shot vs baseline, Holm; per-problem
     score of 3 samples, exact sign-flip test (`stats.sign_flip_exact`), McNemar on majority;
     "detected" only at Holm p < 0.05, else inconclusive with its interval. Power:
     `docs/followup/power.md`: H2 about 15 pp, H1 about 8 pp (shared samples). **Dev revision 2 is declared unused**: only bug
     fixes (code not doing what revision 1 specifies), logged in the dev log.
   - **Built for it (no API calls):** condition 4 `checklist-revision` (`agent.run(...,
     checklist_revision=True)`: one revision on checklist flags of a confirmed optimum, kept
     only if it's a confirmed optimum; its API errors re-run the pair); unused variables
     dropped with a note in every solver condition (`schema.drop_unused`, `Item.dropped`);
     hash run order (`followup.in_run_order`) with `--sample 0 1 2` in one directory; conditions
     2-4 share their first reply (`tests/test_shared_first_reply.py`); the analysis,
     `followup_report.py`.
   - **Dev smoke run of condition 4 (2026-11-11, owner's terminal):** `runs/dev-checklist-revision`,
     24/25, $0.1775 on 57 calls; bug-finding only (dev log). One report bug fixed (NaN in JSON).
   - **The follow-up freeze** (`followup_freeze.py`): section 3's fingerprint (all source, the
     lock, the draft, split.json, both data files by hash, prompts, settings, seeds, id-list
     hashes) and `analysis_sha256` for `followup_report.py`. `approve` is THE OWNER'S STEP
     ONLY. `followup.load_sealed` reads a test split only after `followup_freeze.check()`
     passes; a `Problem`'s repr hides its text and key.
   - **The test split in `evaluate` (2026-11-12):** `--split followup-test`
     (`followup.TEST_SPLIT`, `followup.load_test`): both benchmarks in one directory, each
     problem named by its label (`complexlp:1`) in results, resumes, the manifest, the run
     order and the report. Only the whole experiment runs (`require_whole_followup`), and
     even `--plan` needs the follow-up freeze. Keys by format alone (`followup.parse_key`;
     unparseable: left out, listed, never "no optimum"); the aggregate check
     (`scripts/key_formats.py`) found all 128 are numbers. A `max_tokens` reply is the
     condition's outcome, never re-run (already so).
   - **Last fixes (2026-11-13):** a rounding clause for non-whole keys (`followup.right_by`;
     follow-up only, M6 unchanged; whole keys stay at 1e-4), after an aggregate precision
     check (7 non-whole keys, 2 under 5 significant figures); the encoding check's judge
     prompt `docs/followup/judge_prompt.md`, in the follow-up freeze; `verified` vs
     `confirmed` explained in the draft. A CBC fix found by the property test (it predates
     the follow-up): a claimed optimum at an infeasible point is settled like an
     "infeasible or unbounded" label (`CBC_INFEASIBLE_OPTIMUM_BUG`); it changes no logged
     solve, the ground truth, or M6's results (all rebuilt byte-identical).
   - **The test run and results (2026-11-15; no API calls after the run):** the owner ran
     `runs/followup-test` from their terminal at `f36e812` (1536 answers, 0 errored,
     $2.7176 on 1252 calls; committed). On the 121 unexposed problems: **H2 detected**
     (single-shot minus baseline +6.34 pp, sign-flip Holm p 0.0445; McNemar on majority not
     significant, Holm p 0.24; 1.38 pp of it from 8 baseline replies cut off at max_tokens,
     descriptive), **H1 inconclusive** (+0.6 pp; no difference larger than 4 pp).
     `scripts/followup_results.py` writes `results/followup.json` and renders
     `docs/followup/RESULTS.md`; the README's "Harder problems" subsection takes its numbers
     from that JSON (the README-number test). Descriptive extras and the HiGHS debug print
     check: `docs/followup/RUN_NOTES.md`.
   - **Deviations** (`docs/followup/DEVIATIONS.md`): **the 5b key-dispute check wasn't
     performed** (deviation 2; owner, 2026-11-15, for time, before any encoding or judging):
     no corrected-key row, raw keys are the result of record, the 15 trigger problems are
     listed by label, and whether any are key errors is unknown. Deviation 1 (Gemini JSON
     encodings) is superseded. `review/followup_disputes/` (plan marked not run, packets
     git-ignored) and `scripts/dispute_packets.py` are kept for an optional, exploratory check.
   - **Data notice (2026-11-15):** `DATA_NOTICE.md` (linked from the README's "License and sources" and
     `LICENSE`): MIT covers the code only; `runs/` holds Mamo ComplexLP (CC BY-SA 4.0) and
     IndustryOR (CC BY-NC 4.0) text as cleaned by LLM4OR (no license), plus NL4Opt (MIT).
     History kept, since rewriting it would break the freeze tags.
   - **The freeze checks read the tags (2026-11-15):** `freeze.approval_at_tag` reads a
     study's approval and every frozen file from git's objects; both `tag_problems` use it,
     and CI runs them. `check()` still compares the working tree (it gates a new run), so it
     refuses at HEAD for both studies now, as it should. `opt_agent.frozen.Tree` extracts a
     tag's tree (`git archive`) and runs its code there.
   - **The demo (2026-11-15):** `src/opt_agent/demo/` (FastAPI, imported only there; the
     `demo` extra; fastapi/uvicorn locked without moving any study package). `GET /`,
     `/health`, `/examples`; `POST /solve`. Examples mode (default) replays four original
     examples (`demo/examples.py`, each with a hand-checked answer a test re-derives) from
     `demo/replies/` through `api.ReplayOnlyClient`; live mode needs `OPT_AGENT_LIVE=1` and a
     key, and is guarded (one solve at a time, 4,000 characters, `api.max_tokens_cap` of
     8,000 per reply, a `BudgetedClient` cap of $0.50 by default). The owner cached the
     replies (16 calls, $0.0139); all four match their keys. Dockerfile + CI `demo-image`
     job (`scripts/demo_smoke.py`).
8. [x] **M8 (2026-11-15):** `scripts/reproduce.py` replays every committed answer from the
   caches and rebuilds every reported number from the tags, byte for byte (CI's `reproduce`
   job, after `scripts/fetch_llm4or.py`); the README rewritten for a short read, with the M6
   write-up moved to `docs/EVALUATION.md` and the design to `docs/DESIGN.md`, and every
   README number checked; `docs/demo.png` (`scripts/screenshot.py` headlessly; CI keeps an
   artifact). The picture tools (Playwright, matplotlib) are in the optional
   `requirements-docs.lock`, never in requirements.lock (which both freezes fingerprint). The IE 2310 kit is in `docs/ie2310/` (`scripts/ie2310.py`; the owner's
   teammate writes the time study, flow charts and summary). Left for the owner: the repo's
   description and topics on GitHub (open items in `docs/HANDOFF.md`).
   The final review (2026-11-15, `docs/audit/2026-11-final-review.md`) lists what's left to
   fix. Its mechanical fixes and its five must-fix items are done (the must-fix ones on the
   owner's go-ahead); the should-fix and nice-to-have items are open.
