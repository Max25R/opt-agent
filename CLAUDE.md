# opt-agent

An LLM agent that turns plain-English operations problems into linear/integer programs,
solves them with a real solver, verifies the result independently, and explains it using
the solver's own numbers. A portfolio project for AI-engineering co-op applications. The
point is a trustworthy evaluation, not a demo.

## How to work on this repo

- The owner (a CS + Industrial Engineering student) has to explain every line in
  interviews. Work **one milestone at a time**: briefly explain each design choice, keep
  code simple and readable, and stop after each milestone for review. Don't start the next
  milestone without a go-ahead.
- End every milestone with the exact `git add` / `git commit` / `git push` commands.
- Match the existing style: small, well-named functions; comments explain *why*.
- Don't trust a solver's word: anything solver-related gets a known-answer test, a
  plain-arithmetic check, a CBC-vs-HiGHS cross-check, or a metamorphic test.

## Hard rules

- **No made-up numbers.** Every number in the README comes from `results/eval.json`
  (milestone 6 adds a test that enforces this).
- Tests for the schema, solver, and ground-truth layers **never call the Claude API**.
- Report failures honestly. If something (e.g. self-correction) doesn't help, say so.
- Bulk eval runs use a small, cheap model. Check current model IDs and prices in the docs
  before writing API code.

## Plan and status

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
     which settles the pre-registered categories. (The "=" reading, the 1e-4 count,
     Amendment 1, the perturbation rule, the freeze checks, the baseline's prompt and the
     hand-check packets are done; see milestone 6.)
     `python -m opt_agent.freeze` lists what's left before the owner can freeze. Known and
     unfixed: the integrality rule matches ingredient names ("units of chicken" meat), so
     it labels countable products continuous in at least 3 reviewed test problems
     (bubble teas, crepes, curry bowls, and the wine/kombucha problem; harmless for the
     annotated answers, but not for the strict reading: 4 answers per condition, see
     DEVIATIONS.md section 3; fix after M6, and check the unreviewed rule labels too); `DEV_WALKTHROUGH.md` predates the owner's milestone 3
     corrections (the owner decides whether to regenerate it); no Farkas certificate for
     infeasible LPs; the CLI needs a key even when every call is cached (milestone 8).
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
       in the README's Evaluation section against `results/eval.json`, at the precision
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
     - **Amendment 4 (draft, not tagged):** the omitted pre-registered rows (lenient, without
       disputed reviews) and an exploratory corrected-labels row (268/274 per condition).
       `scripts/amendment4.py` computes them; `eval_json.py` writes them as `amendment_4`;
       264/274 stays the result of record.
     - **Amendment 5 (draft, not tagged):** external corroboration against LLM4OR's cleaned
       NL4Opt (`docs/EXTERNAL_DATA.md`, data git-ignored): it removed 5 of Amendment 4's six
       key errors. `scripts/amendment5.py` → eval.json `amendment_5`, which CI copies forward
       without recomputing (no data there).
7. [ ] FastAPI `POST /solve` + one HTML page + Dockerfile.
8. [ ] README polish: diagram, results table, reproducing from the cache without a key,
   limitations, repo description/topics.

## Claude API notes

- `formulate.DEFAULT_MODEL = "claude-haiku-5-5"`: the owner asked for a small, cheap
  model for bulk eval runs. Check model IDs and prices in the docs before changing it.
- Every API call goes through `api.call`: the request is built once
  (`formulate.build_request`, `explain.build_request`), and that same dict is sent,
  hashed (`request_sha256`, logged), cached, and logged. The cache's key is `api.cache_key`
  (model, system, messages, sampling settings; not the SDK-built schema, since M7), and
  `Cache` indexes M6's files, named by `request_sha256`, by the request each stored, so
  every M6 reply is still found. Thinking and effort are
  pinned (`api.THINKING`, `api.EFFORT`): adaptive thinking with its text omitted, and
  medium effort, Haiku 5.5's current defaults. Haiku 5.5 rejects `thinking: enabled`
  with a budget, and temperature can only be 1, so a run is reproducible only by replaying
  the cache. The SDK's retries are off (`with_options(max_retries=0)`); `api.call` retries
  with the SDK's own rule so retry time is measured (8 tries, so a 429 gets about a
  minute of backoff, or the waits `retry-after` names). A call that still fails comes
  back as `CallInfo.error`, never as an exception, except for a spend limit, which raises
  `api.SpendLimitReached` to stop the run.
- Every API call takes a `client` argument, and tests pass `tests/fakes.FakeClient`
  (which returns real `anthropic.types.Message` objects, so they can be cached). Only
  `tests/test_live.py` (marker `live`, excluded by default and in CI) calls the real API,
  and it uses dev problems only.
- `.env` exists in the owner's checkout (git-ignored). Claude never reads or commits it.
  `config.get_api_key` uses an exported `ANTHROPIC_API_KEY`, and reads `.env` only when
  `OPT_AGENT_LIVE=1` (2026-11-08, from the audit): unsetting the key guarantees that
  nothing can spend.
- `Result.confirmed`: CBC and HiGHS agree and the checks pass, for any status.
  `Result.verified`: confirmed and optimal. Both are about the solution of Claude's model,
  not whether the model matches the text; that's milestone 6. A flagged revision can be
  "verified" too, which is why the flags exist.
- The live tests (`OPT_AGENT_LIVE=1 python -m pytest -m live -s`, 4 to 8 calls) first passed on
  2026-10-28.

## Budget (hard constraint, owner, 2026-10-28)

- The owner has $20 of API credit in total and a $10/month spend limit (resets on the
  1st). **Never run live calls, in loops or retries, without telling the owner first**
  (how many calls, the worst-case cost), and never run the full milestone 6 evaluation
  until the owner approves its cost and confirms the test-split reviews.
- Every live call goes through `budget.BudgetedClient`. Before a call it reserves the
  worst case (`pricing.worst_case_usd`: every request byte as an input token, plus a
  2,000-token margin, and all of `max_tokens`); if that could cross the cap, it raises
  `BudgetExceeded` instead of calling. After the call it writes the real cost (from
  `response.usage`) to a JSONL ledger, so a resumed run counts earlier spend. Cached
  replies cost nothing. Caps: $1 for smoke tests, $0.25 for all live-test runs together
  (`logs/spend/live-tests.jsonl`), and $3 for milestone 6's test + perturbed run (owner,
  2026-10-28). Dev runs get their own cap, agreed with the owner before each one.
- `pricing.PRICES` came from the pricing page on `PRICES_CHECKED`; re-check it before a
  paid run. An unlisted model raises instead of being guessed.
- Budget stops, spend-limit errors (`api.SpendLimitReached`: a 429 with
  `enforced_spend_limit_reached`, or a 400 "You have reached your specified ... limits"),
  and API errors are never scored as Claude's failures. `evaluate.py` logs an API error
  that outlasts the retries as `errored` and retries it on resume. The rule for scoring is
  the pre-registration's **Amendment 1**, which the owner approved on 2026-10-28:
  errored and pending pairs are re-run until none remain; a pair still errored
  after the first run and 3 resume passes counts as wrong (loud) and is listed
  separately; refusals and unusable replies are replies, so they count as wrong the first
  time (the cache replays them); the report says how many pairs needed re-runs.
  `report.py` counts the passes.
- Runs are resumable: `python -m opt_agent.evaluate --out runs/NAME ...` again skips done
  pairs and replays every successful call from `runs/NAME/cache`.

## Commands

```bash
source .venv/bin/activate
pip install -r requirements.lock && pip install --no-deps -e .   # the locked versions
python -m pytest              # ~100 s; property tests explore new random cases each run
HYPOTHESIS_PROFILE=ci python -m pytest   # deterministic, as in CI
ruff check . && ruff format .            # CI runs ruff format --check
python -m opt_agent.data            # pinned, SHA-256-checked downloads (git-ignored)
python -m opt_agent.ground_truth    # rebuild data/nl4opt/ground_truth/ (~55 s)
python -m opt_agent.perturb         # then rebuild the perturbed splits (~4.5 min)
python scripts/dev_walkthrough.py   # rebuild the 30-problem dev review sheet
python -m opt_agent.packets integrality|reviews|agreement   # the owner's packets
OPT_AGENT_LIVE=1 python -m opt_agent.agent "problem text"   # or export ANTHROPIC_API_KEY
OPT_AGENT_LIVE=1 python -m pytest -m live -s   # the tests that call the real API (not in CI)
python -m opt_agent.evaluate --out runs/NAME --cap 1.00 ID ... --plan   # worst case, no calls
OPT_AGENT_LIVE=1 python -m opt_agent.evaluate --out runs/NAME --cap 1.00 ID ...   # dev only; resumable
OPT_AGENT_LIVE=1 python -m opt_agent.evaluate --out runs/NAME --cap 0.50 --all    # every scorable problem
python -m opt_agent.freeze          # what's left before the freeze; whether inputs match it
python -m opt_agent.freeze approve  # THE OWNER'S STEP ONLY: writes docs/FREEZE.json
python -m opt_agent.report runs/NAME     # score a run; writes runs/NAME/report.json
python -m opt_agent.report runs/P --original runs/NAME   # a perturbed run, paired
python -m opt_agent.blind_grading runs/NAME [--size N]   # review/blind_grading/NAME/, first
python -m opt_agent.taxonomy runs/NAME   # review/taxonomy/NAME/: label each silent failure
python -m opt_agent.taxonomy runs/NAME --merge REPLY.csv --grader "MODEL, LLM judge"
python -m opt_agent.external_check   # review/external_check.md: test answers vs ORLMBenchmark
python -m opt_agent.external_check judges   # review/review_judge/: the reviews it leaves
python -m opt_agent.external_check judges --decide   # both replies in: fill the sheet by rule
python -m opt_agent.external_check apply   # the decisions into reviews/exclusions/integrality
python -m opt_agent.packets judge   # review/integrality_judge/: one prompt, a sheet per judge
python -m opt_agent.packets judge --merge judge|second --reply REPLY.csv --grader "MODEL"
python -m opt_agent.packets judge --apply   # both sheets filled: combined labels into integrality.json
python scripts/blind_taxonomy.py runs/test [--merge judge|second --reply R.csv --grader G]
python scripts/amendment3.py runs/test   # after every report rebuild: Amendment 3's row
python scripts/eval_json.py              # then results/eval.json (README numbers come from it)
```

## Ground truth (milestone 3 decisions)

- **Annotation errors are rejected, never repaired.** That covers one variable annotated
  twice, empty terms, two mentions resolving to one variable, and operators that
  contradict the wording. A repair would be our reading presented as theirs.
- **Mentions resolve by the variable name they contain** ("economical mobile phone" ->
  economical). `order_mapping` decides only when the name doesn't, and every override is
  noted. This rescued 3 problems where `order_mapping` was wrong and changed nothing else.
- **Integrality:** both optima are stored (`lp`, `ip`), and a per-problem label picks the
  answer. Wherever integrality changes the answer, the label is a hand label in
  `data/nl4opt/integrality.json` (source `owner` or `claude`). Elsewhere the rule in
  `integrality.py` labels it (source `rule`), which agrees with all 9 owner labels. The
  owner's criteria: countable objects, trips, ads, machines, people and servings are
  integer; mass, volume, area, time, money and "units of" a substance are continuous.
  Before using rule labels to grade an agent's integrality choice (not just to pick
  answers), review them. **Provenance:** the 9 owner labels are dev problems; every other
  hand label (the rest of dev, and all of test) is Claude's. The owner is checking a blind
  sample of 40 test labels (`review/integrality_blind/`, seed 20261019).
- **Strict wording** ("more than"; the scheme has no strict operators, so it's annotated
  as >=): for integer problems, `Record.strict` stores the answer with each noted
  constraint read strictly (`strict.py`), and `matching_reading` accepts either reading
  and says which one matched.
- **The "=" reading** (pre-registration 3c, owner's decisions): `Record.equality` stores the
  model with some inequalities made equations, solved as LP and IP and checked like the
  annotated one, and `matching_reading` accepts it as "equality". The constraints
  (`equality_names`) come from two places: **the wording**, by rule (owner, 2026-10-30):
  every `xby`/`xy` ratio whose direction names no inequality, such as "must be twice as many"
  (`nl4opt.ratio_wording`, stored as `Record.ratio_wording`); and an `ambiguous-text`
  review (`Review.equality`). The 3 reviewed test answers (50, 1215, 32) match the hand
  reviews. It's a field, not a converter note, because the review packet prints notes; the
  owner's packets are unchanged.
- **Exclusions:** test problems used while building the agent are not scorable
  (`data/nl4opt/exclusions.json`: the fishery and ads problems), nor are the 2 that
  Amendment 2's rules exclude (`1283305022`, `-1715698555`). Demos, fakes and live
  tests use dev problems only.
- `answer()` returns None (and `scorable()` False) unless HiGHS agrees and the
  arithmetic checks pass.
- `data/nl4opt/reviews.json` is **hand-written input**. Every problem with no optimum, a
  do-nothing optimum, an ORLM disagreement, an unlisted variable, or an overridden
  `order_mapping` must have a review (the report and the tests enforce this). For an
  unlisted variable, neither 0 nor 1 is a safe default. `scorable()` excludes annotation
  errors that change the answer (`answer_affected`); `blind_gradable()` excludes every
  annotation error. Dev #4 (471112257) is scorable but not blind-gradable (owner's call).
  **Provenance:** Claude wrote every review. The owner confirmed 11 of the 12 dev reviews
  (not 1670020945, written after the walkthrough); all 62 test reviews are unconfirmed and
  in the owner's packet (`review/test_reviews/`, least sure first).
- ORLM's answers (CC BY-NC 4.0) are a cross-check only and are **never committed**.
- After changing the converter or the solver, rebuild the ground truth, then the perturbed
  splits (they're built from it, and from `reviews.json`: a changed review needs a rebuild
  too). `test_highs_reproduces_every_committed_answer` and
  `test_highs_reproduces_every_perturbed_answer` fail if the data has drifted.

## Gotchas (learned the hard way)

- **PuLP 4.0** changed its API: `prob.add_variable(name, low, up, cat)`,
  `prob.constraints()` is a method, the CBC class is `COIN_CMD` (there's no
  `PULP_CBC_CMD`), and `solve()` returns an `LpSolveStats`.
- **CBC comes from `cbcbox`, pinned to 2.929.** 2.931+ crash on Apple Silicon because a
  bundled dylib has an invalid code signature.
- **PuLP 4 flips dual signs for max problems.** `solver.py` negates them, and a
  finite-difference test checks this.
- **CBC integer preprocessing is off.** It returned a wrong "optimal" answer on a
  3-variable MIP (`CBC_PREPROCESS_BUG` in `tests/problems.py`).
- **CBC's infeasible/unbounded labels are unreliable**, so both solvers settle them with a
  zero-objective feasibility solve.
- **Both solvers can claim a false optimum** when free variables let the objective run away,
  in one variable order only (`CBC_FREE_VARIABLE_BUG`, `HIGHS_FREE_VARIABLE_BUG`). CBC's log
  says "Unscaled problem has dual infeasibilities". `-scaling off` fixes that case but caused
  new false optima (3 in 4000 random models), so don't use it. Instead, every claimed optimum
  must survive an improving-ray check (`rays.py`): the same solver looks for a ray in a
  bounded LP, and any ray it finds is verified by arithmetic, scaled to a largest entry
  of 1 (so a near-zero direction can't hide in a tolerance) and by a long step from a
  checked feasible point. "Unbounded" is only ever reported with such a ray.
- **A CBC/HiGHS disagreement is a loud failure:** `Result.verified` is False, nothing is
  explained (only verified answers are), and the CLI prints "SOLVERS DISAGREE". A time-out
  is not a disagreement: it's shown as "NO ANSWER" first. For an LP, the arithmetic checks
  now prove optimality too (a duality certificate from CBC's duals); for a MIP they check
  feasibility only, and optimality rests on the cross-check.
- CBC reports values to ~8 significant digits, so tolerances scale with the size of the
  terms being added (`verify.tolerance_for`).
- CBC can time out (status `timeout`) proving integer infeasibility over unbounded integer
  variables. That's expected; the random generator bounds integer variables.
- **CBC gives no value to a variable that appears only in the objective** when the
  objective is zeroed (the feasibility solve). `solver._value_or_any_in_bounds` fills one in.
- **HiGHS can return a fractional value for an integer variable with a fractional bound**
  (scipy 1.18.1, presolve on: maximize x <= 2.5 gave 2.5). Both solvers take
  `Variable.solver_bounds()`, integer bounds rounded inward, and `schema.no_whole_number`
  makes an integer variable with no whole number in its bounds infeasible in both (CBC's
  feasibility solve never sees an objective-only variable).
- **SciPy's `milp` status 4 means "other"**: HiGHS's "infeasible or unbounded" (common for
  MIPs), but also its solve errors. Status 1 is the time limit. So 2, 3 and 4 are settled
  by a feasibility solve and a certified ray, or else become `error`.
- **anthropic 1.15 uses `httpx2`**, not `httpx`; tests build API errors from
  `SimpleNamespace` responses (`tests/fakes.status_error`).
- Don't keep the repo or its `.venv` under iCloud: iCloud hides `.pth` files and
  Python 3.13 then skips them.
- python.org's macOS Python has no CA certificates, so downloads pass `certifi`'s bundle
  explicitly (`data.py`).
- **Claude Code's Bash sandbox breaks Python's TLS on macOS** (`OSStatus -26276`, which
  the SDK reports as `APIConnectionError: Connection error.`), while `curl` gets through.
  Paid runs go outside the sandbox. A keyless check costs nothing: `httpx2.get(
  "https://api.anthropic.com/v1/models")` should return 401.

## Settled decisions

- MIT license, "Copyright (c) 2026 Max Reese" (owner, 2026-11-04; this reverses the
  2026-10-16 "no license" call, so the repo can be used and installed). The
  data keeps its own licenses: NL4Opt is MIT (`data/nl4opt/LICENSE`), ORLMBenchmark is
  Apache-2.0 (credited in `review/external_check.md`), and ORLM's CC BY-NC answers are
  never committed.
- No API key is ever committed: `tests/test_repo_hygiene.py` checks every tracked file
  (the history was checked by hand on 2026-11-04 and is clean).
- Don't file the CBC preprocessing bug upstream (owner's call, 2026-10-16).
