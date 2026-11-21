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
  (milestone 6 adds a test that enforces this), or, in its "Harder problems" results
  subsection, from `results/followup.json` (`scripts/followup_results.py`; the same test),
  or, in its "Resampling" results subsection, from `results/resampling.json`
  (`scripts/resampling_results.py`; the same test).
  The exceptions, the owner's (2026-11-19): the Limitations bullets labeled "Exploratory"
  (the disagreement detector, the explanation checker), each checked against its own record
  in `docs/analysis/` (`tests/test_readme_numbers.py`, `EXPLORATORY`; the explanation
  checker's also against `limits_claims.json`, for ADR-0009's 13 → 4, the owner's request of
  2026-11-20); and the cost and
  latency table at the top, checked against `results/headline.json` (`TABLE`), which
  `scripts/headline.py` computes from the committed test runs' logs after checking each
  condition's total cost and median latency against the results files.
- **Results live in the results files**, and in the documents the README-number test
  checks against them. Elsewhere (this file, `docs/HANDOFF.md`) point to them; don't
  restate results by hand.
- Tests for the schema, solver, and ground-truth layers **never call the Claude API**.
- Report failures honestly. If something (e.g. self-correction) doesn't help, say so.
- Bulk eval runs use a small, cheap model. Check current model IDs and prices in the docs
  before writing API code.

## Plan and status

All eight milestones are done (2026-11-15), and the owner's later lists (2026-11-17 and 18:
CI hardening, mypy and coverage, the post hoc analyses in `docs/analysis/`, the ADRs in
`docs/adr/`, the two bugs mypy found; then the polish list: the static demo on GitHub Pages,
the code tour in `docs/DESIGN.md`, a README pass; and on 2026-11-19 the disagreement detector,
the explanation checker's dev evaluation, the Agent Skill, the resampling study and the IP
slack-claim check) are done too. **Where things stand: the resampling study is done (run by
the owner on 2026-11-19, analyzed on 2026-11-20): R1 is supported (`results/resampling.json`,
`docs/resampling/RESULTS.md`).** ADR-0009 (2026-11-20): for an integer program the explainer
also gets the solver's own test of what limits the answer (`src/opt_agent/limits.py`); the owner
regenerated the dev explanations with it (`runs/explain-dev-limits`), compared in
`docs/analysis/limits_claims.md` (exploratory, dev only): **13 → 4** explanations with a false
"not limiting" claim, by the same rule; keep that as the headline everywhere (owner,
2026-11-20), and the "rule mistakes" reading as a labeled post hoc note.
The demo's disagreement badge (2026-11-20): each verified answer shows the resampling study's
flag (its samples and Claude's direct answer), with the study's measured precision and recall
(`demo/pipeline.py`, `MEASURED`, checked against `results/resampling.json`); a fifth example,
"Freight cars", is chosen to show the warning. The four written examples get their extra
samples from the owner's paid run (`scripts/cache_examples.py`), then `pipeline.REFRESHED`.
The full record, with every
decision and its date, is in `docs/HISTORY.md` and `docs/HANDOFF.md`'s decision logs; where
things stand, every open item and the environment are in `docs/HANDOFF.md`. **Start from
`docs/HANDOFF.md`'s "Start here".**

1. [x] Setup: src layout, pyproject, `.env` handling, pytest + ruff CI.
2. [x] LP schema and solver, verified with known answers, plain-arithmetic checks,
   CBC-vs-HiGHS property tests and metamorphic tests.
3. [x] Ground truth from NL4Opt's raw annotations, with no LLM (2026-10-16; see "Ground
   truth" below).
4. [x] LLM formulation, the explanation checker and the CLI (2026-10-17).
5. [x] Self-correction (2026-10-19): up to 3 attempts, IIS feedback, change flags.
6. [x] **M6, the NL4Opt evaluation:** pre-registered (`docs/PREREGISTRATION.md`, frozen),
   frozen at tag `m6-freeze` (= `8f522c0`, the commit both test runs ran on); Amendments 3-5
   in `docs/amendments/` (tagged), deviations in `docs/amendments/DEVIATIONS.md`. Results:
   `results/eval.json`, written up in `docs/EVALUATION.md`.
7. [x] **M7, the follow-up study and the demo:** pre-registered
   (`docs/FOLLOWUP_PREREGISTRATION.md`, frozen), frozen at tag `followup-freeze` (=
   `f36e812`); deviations in `docs/followup/DEVIATIONS.md`. Results: `results/followup.json`,
   written up in `docs/followup/RESULTS.md`. The demo: `src/opt_agent/demo/`.
8. [x] **M8:** `scripts/reproduce.py` (every number replayed and rebuilt from the tags, in
   CI), the README, `docs/EVALUATION.md` and `docs/DESIGN.md`, the screenshot, and the IE 2310
   kit (`docs/ie2310/`). Two reviews: `docs/audit/2026-11-review.md` and
   `docs/audit/2026-11-final-review.md` (its status line says what's left).
9. [x] **The resampling study** (2026-11-19): `docs/RESAMPLING_PREREGISTRATION.md` (approved
   by the owner with three edits), runner `src/opt_agent/resampling.py`, analysis
   `src/opt_agent/resampling_report.py`, gate `src/opt_agent/resampling_freeze.py`, frozen in
   `docs/resampling/FREEZE.json` at tag `resampling-freeze`. Run by the owner on 2026-11-19
   (`runs/resampling`), analyzed 2026-11-20: `results/resampling.json` (written by
   `scripts/resampling_results.py`; deviation 1 in `docs/resampling/DEVIATIONS.md`), written
   up in `docs/resampling/RESULTS.md`.
   Its hypothesis comes from the exploratory disagreement detector
   (`docs/analysis/disagreement_detector.md`).

**Standing rules from the history** (the reasons are in `docs/HISTORY.md`):
- **The resampling study is done and frozen at `resampling-freeze`.** Never edit
  `docs/RESAMPLING_PREREGISTRATION.md`, `docs/resampling/FREEZE.json` or the run
  (`runs/resampling`). Its frozen `resampling_report.main()` can't write its JSON (a numpy
  bool), so `scripts/resampling_results.py` writes it, from the frozen `build()` (deviation
  1). The owner asked Claude to write this study's freeze (2026-11-19); the two older
  studies' approvals stay the owner's steps only.
- `python -m opt_agent.freeze approve` and `python -m opt_agent.followup_freeze approve` are
  **the owner's steps only**, never Claude's. Never edit `docs/FREEZE.json` or
  `docs/followup/FREEZE.json`, and never rewrite git history (it would break the freeze tags).
- All three studies are done and frozen at their tags. Any change under `src/opt_agent/` or
  to the lock makes each study's `check()` refuse at HEAD, as it should (it gates a new test
  run); `python -m opt_agent.freeze`, `followup_freeze` and `resampling_freeze` say so and
  report whether the tag verifies. The tag checks read git's objects (CI runs them), and `scripts/reproduce.py`
  rebuilds from each tag's own tree. Push tags with commits.
- **Don't tune prompts to fix a single dev problem**, and tune on dev splits only. The
  follow-up's dev revision 2 is declared unused: only bug fixes, logged in
  `docs/FOLLOWUP_DEV_LOG.md`.
- The formulation checklist's prompt was designed after seeing M6's test failures: any M6
  number from it is exploratory, labeled "prompt designed after seeing these failures", and
  never goes in `results/eval.json` or the README's results.
- M6 rebuild order: `opt_agent.report`, then `scripts/amendment3.py runs/test` (a frozen
  report rebuild drops Amendment 3's row), then `scripts/eval_json.py`.
- Paths under `runs/` are git-ignored: commit a run directory with `git add -f`.
- The owner's packets (`review/integrality_blind/`, `review/says_lp.md`,
  `review/test_reviews/`) and `DEV_WALKTHROUGH.md` are kept as sent: don't regenerate them
  unless the owner asks (whether to regenerate `DEV_WALKTHROUGH.md`, which predates their
  milestone 3 corrections, is their call).
- The picture tools (Playwright, matplotlib) belong in the optional `requirements-docs.lock`,
  never in `requirements.lock`, which both freezes fingerprint.
- In `docs/ie2310/`, the time study, the flow charts and the project summary are the owner's
  teammate's to write.
- Scripts that ran at an earlier commit and don't run at HEAD are in `scripts/historical/`
  (its README says where each ran).
- Known and unfixed: `docs/HANDOFF.md`, open items.
- **Answer-key disputes are an LLM judge's flags** (owner, 2026-11-18): wherever a dispute
  share is stated, lead with the problem count and its denominator ("an LLM judge flagged
  the key on 13 of the 35 follow-up problems with a wrong answer, not verified by a
  person"), and the share of wrong answers second, if at all. Never "N% of failures were key
  errors". Frozen files keep their wording. `docs/analysis/dispute_spotcheck.md`'s verdict
  column is for a person, never Claude.
- **Every new analysis or classification done by Claude says so** ("classified by Claude, an
  LLM, not a person"), and anything exploratory is labeled exploratory/post hoc.
- **The explanation checker's finding** (exploratory, Claude's labels:
  `docs/analysis/explanation_checker.md`): on dev, no explanation used a wrong number, but
  about a quarter made false claims about slack in integer programs, which no number check
  sees. Say that, not "explanations are verified".

## Environment (details in `docs/HANDOFF.md`, "Environment")

- The owner's Mac is Apple Silicon (`arm64`); the studies ran there and CI's `reproduce` job
  runs on `macos-15`.
- No `gh`: read CI from the public GitHub API with `curl` + `jq`
  (`api.github.com/repos/Max25R/opt-agent/actions/runs?head_sha=SHA`, then `.../jobs`).
  Sandboxed commands must list `api.github.com` (and `github.com` to push).
- **CI waits: 30 minutes at most.** If it isn't done, stop and report each job's name and
  status. Job `timeout-minutes` (10; 30 for reproduce) are hang guards: never tighten them.
- The sandbox can't start a browser, open or reach local ports, or make paid calls (Python's
  TLS fails there; paid runs are the owner's, in their terminal). pip needs
  `--use-deprecated=legacy-certs`. Activate `.venv` first; use `$TMPDIR` and
  `MPLCONFIGDIR="$TMPDIR/mpl"`.

## Claude API notes

- `formulate.DEFAULT_MODEL = "claude-haiku-5-5"`: the owner asked for a small, cheap
  model for bulk eval runs. Check model IDs and prices in the docs before changing it.
- Every API call goes through `api.call`: the request is built once
  (`formulate.build_request`, `explain.build_request`), and that same dict is sent,
  hashed (`request_sha256`, logged), cached, and logged. The cache's key is `api.cache_key`
  (model, system, messages, sampling settings; not the SDK-built schema, since M7), and
  `Cache` indexes M6's files, named by `request_sha256`, by the request each stored, so
  every M6 reply is still found. Repeated samples: `Cache(dir, sample=n)` (`evaluate
  --sample n`, one run directory per sample) salts the key for n > 0; sample 0 is the
  unchanged key, so every existing cache replays. Thinking and effort are
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
  `tests/test_live.py` (marker `live`, excluded by default and in CI, and skipped without
  `OPT_AGENT_LIVE=1` whatever `-m` says: `tests/conftest.py`) calls the real API, and it
  uses dev problems only.
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
  2026-10-28). Dev runs get their own cap, agreed with the owner before each one: $0.75 for
  the condition-4 dev smoke run (owner, 2026-11-11). The follow-up test run's cap was $6
  (pre-registration, section 6); it paid $2.7176. The demo examples' replies: cap $0.30,
  paid $0.0139 (owner's terminal, 2026-11-15; `logs/spend/demo-examples.jsonl`). The demo's
  live mode has its own cap ($0.50 by default, `logs/spend/demo.jsonl`), and so does the
  agent CLI (`--cap`, $0.50 by default, `logs/spend/agent.jsonl`; since 2026-11-15, from the
  final review). The paid run of 2026-11-19 (`scripts/paid_dev_and_demo.py`): cap $0.30,
  paid $0.0399. The resampling study's run: hard cap $3.00, paid $1.4884 (owner's terminal,
  2026-11-19; `runs/resampling/spend.jsonl`). ADR-0009's dev regeneration
  (`scripts/paid_explain_limits.py`): cap $0.25, paid $0.0358 (owner's terminal, 2026-11-20;
  `runs/explain-dev-limits/spend.jsonl`). Spent so far: $5.45 of the $20 credit (2026-11-20;
  the ledger is in `docs/HANDOFF.md`).
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
python -m pytest              # ~2.5 min; property tests explore new random cases each run
HYPOTHESIS_PROFILE=ci python -m pytest   # deterministic, as in CI
ruff check . && ruff format .            # CI runs ruff format --check
python -m opt_agent.data            # pinned, SHA-256-checked downloads (git-ignored)
python -m opt_agent.ground_truth    # rebuild data/nl4opt/ground_truth/ (~55 s)
python -m opt_agent.perturb         # then rebuild the perturbed splits (~4.5 min)
python scripts/dev_walkthrough.py   # the 30-problem dev review sheet: kept as reviewed, don't regenerate
python -m opt_agent.packets integrality|reviews|agreement   # the owner's packets: kept as sent, don't regenerate
OPT_AGENT_LIVE=1 python -m opt_agent.agent "problem text"   # or export ANTHROPIC_API_KEY; capped (--cap)
OPT_AGENT_LIVE=1 python -m pytest -m live -s   # the tests that call the real API (not in CI; skipped without OPT_AGENT_LIVE=1)
python -m opt_agent.evaluate --out runs/NAME --cap 1.00 ID ... --plan   # worst case, no calls
OPT_AGENT_LIVE=1 python -m opt_agent.evaluate --out runs/NAME --cap 1.00 ID ...   # dev only; resumable
OPT_AGENT_LIVE=1 python -m opt_agent.evaluate --out runs/NAME --cap 0.50 --all    # every scorable problem
python scripts/followup_split.py    # the follow-up split (made once; refuses to change it)
python -m opt_agent.evaluate --split complexlp-dev --all --conditions single-shot --estimate --checklist --out runs/NAME --cap 0.25 --plan   # follow-up dev, report-only extras
python -m opt_agent.evaluate --split complexlp-dev --all --conditions checklist-revision --sample 0 --out runs/NAME --cap 0.75 --plan   # condition 4, worst case
python -m opt_agent.followup_report runs/NAME   # score a follow-up run: followup_report.json
python scripts/key_formats.py       # the follow-up keys' formats, aggregate only (no ids or values)
python scripts/followup_power.py    # docs/followup/power.md (~2 min, seeded)
python scripts/disagreement_detector.py --report   # its doc's results, from the one run's JSON (it never runs again)
python scripts/explanation_checker.py score   # the checker's dev evaluation: labels (review/explain_dev/) vs flags
python scripts/ip_slack_check.py flags|score   # IP slack claims re-solved (exploratory): flags committed first, scored once
python scripts/limits_claims.py [--verify]     # ADR-0009 on dev (exploratory): both runs' claims vs the solver's facts
python -m opt_agent.freeze          # what's left before the freeze; whether inputs match it
python -m opt_agent.freeze approve  # THE OWNER'S STEP ONLY: writes docs/FREEZE.json
python -m opt_agent.followup_freeze          # the follow-up's: what's left, whether inputs match
python -m opt_agent.followup_freeze approve  # THE OWNER'S STEP ONLY: docs/followup/FREEZE.json
python -m opt_agent.resampling_freeze         # the resampling study: does the tag verify, do the inputs match
python -m opt_agent.resampling --plan          # its calls left and worst case, no calls (the paid run is the owner's)
python scripts/resampling_results.py           # results/resampling.json (the frozen build()'s report) + docs/resampling/RESULTS.md (needs the data)
python scripts/resampling_power.py             # docs/resampling/power.md (seeded)
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
python scripts/followup_results.py       # results/followup.json + docs/followup/RESULTS.md (needs the data)
python scripts/dispute_packets.py [--prompts]   # at 29b7c99 only (scripts/historical/README.md): 5b, not run (deviation 2)
python scripts/fetch_llm4or.py      # LLM4OR's data at its pinned commit, hashes checked (git-ignored)
python scripts/reproduce.py         # replay + rebuild every reported number from the tags; no key
python scripts/reproduce.py --no-replay   # the rebuild alone (about 15 s)
pip install -r requirements-docs.lock -c requirements.lock   # optional: Playwright, matplotlib
python scripts/screenshot.py        # docs/demo.png headlessly, in its committed frame (needs: playwright install --only-shell chromium)
python scripts/screenshot.py --check docs/demo.png   # a picture's margins against that frame
python scripts/ie2310.py            # docs/ie2310/: the numbers table and the figures
python scripts/headline.py          # the README's headline figure and cost/latency table: results/headline.json, docs/headline.png
python -m opt_agent.demo            # the demo, examples mode (no key): http://127.0.0.1:8000
python scripts/static_demo.py       # the demo as a static site (build/site; GitHub Pages, via CI)
python scripts/static_demo.py --check build/site   # it, in headless Chromium (CI only: not in the sandbox)
OPT_AGENT_LIVE=1 python -m opt_agent.demo   # live mode: the key in .env; guarded (demo/app.py)
python scripts/cache_examples.py --plan     # the examples' missing replies, counted with no calls (the paid run is the owner's, --cap 0.15)
python scripts/paid_dev_and_demo.py --plan  # 2026-11-19's paid run (the owner's, --cap 0.30): dev explanations + the fix-step example
python scripts/paid_explain_limits.py --plan  # ADR-0009: the dev explanations again, with limits (the paid run is the owner's, --cap 0.25)
docker build -t opt-agent . && docker run --rm -p 8000:8000 opt-agent   # the image (CI builds it)
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
  `data/nl4opt/integrality.json` (source `owner`, `claude` or `judge`). Elsewhere the rule in
  `integrality.py` labels it (source `rule`), which agrees with all 9 owner labels. The
  owner's criteria: countable objects, trips, ads, machines, people and servings are
  integer; mass, volume, area, time, money and "units of" a substance are continuous.
  Before using rule labels to grade an agent's integrality choice (not just to pick
  answers), review them. **Provenance:** 9 dev labels are the owner's. On test, Amendment 2
  put the two judges' combined labels on the 44 problems they labeled (source `judge`) and
  4 `either` labels by the owner's decision rules (source `owner`); every other hand label
  is Claude's. The owner's blind sample (`review/integrality_blind/`, seed 20261019) went
  unused: the judges replaced it (Amendment 2).
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
  tests use dev problems only, with one exception (owner, 2026-11-20): the demo's "Freight
  cars" example is the follow-up's test problem `complexlp:195`, chosen to show the
  disagreement badge's warning and replaying the resampling run's own replies. No study's
  result changes, but a future study on those problems should count it as exposed.
- `answer()` returns None (and `scorable()` False) unless HiGHS agrees and the
  arithmetic checks pass.
- `data/nl4opt/reviews.json` is **hand-written input**. Every problem with no optimum, a
  do-nothing optimum, an ORLM disagreement, an unlisted variable, or an overridden
  `order_mapping` must have a review (the report and the tests enforce this). For an
  unlisted variable, neither 0 nor 1 is a safe default. `scorable()` excludes annotation
  errors that change the answer (`answer_affected`); `blind_gradable()` excludes every
  annotation error. Dev #4 (471112257) is scorable but not blind-gradable (owner's call).
  **Provenance:** Claude wrote every review. The owner confirmed 11 of the 12 dev reviews
  (not 1670020945, written after the walkthrough). Test reviews were checked under
  Amendment 2 instead: the external cross-check (`review/external_check.csv`) and, for the
  ones it couldn't cover, two LLM judges (`Review.judged`); the owner's packet
  (`review/test_reviews/`) is kept as sent, unused.
- ORLM's answer file (CC BY-NC 4.0) is a cross-check only and is **never committed**.
  Reviews cite some of its answers one problem at a time, under that license;
  `DATA_NOTICE.md` lists where.
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
- **CBC can claim an optimum at an infeasible point** of an unbounded LP
  (`CBC_INFEASIBLE_OPTIMUM_BUG`: x3 = 100 against x3 <= 1). `solver._solve` checks the claimed
  point's feasibility first and settles a failure like an "infeasible or unbounded" label.
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
- **An explanation request without limits must stay byte for byte the one from before
  ADR-0009** (`explain.build_request` leaves `limits` out when it's None, and adds
  `LIMITS_PROMPT` only with them): every cached explanation, the demo's included, replays only
  so (`tests/test_limits.py`). The demo keeps `pipeline.EXPLAIN_LIMITS` off until its two
  integer examples' replies are refreshed.
- **The demo replays each example with the settings its replies were made with**
  (`pipeline.profile_for`): the four written examples with the demo's, and "Freight cars"
  with the resampling study's (`pipeline.STUDY`: samples 3 to 7, 16,000 tokens, no checklist
  or explanation). `pipeline.REFRESHED` turns on the four examples' extra badge samples and
  ADR-0009's limits together, only after `scripts/cache_examples.py` (the owner's paid run)
  has cached them; a test fails if it's on with anything missing.
- **anthropic 1.15 uses `httpx2`**, not `httpx`; tests build API errors from
  `SimpleNamespace` responses (`tests/fakes.status_error`).
- Don't keep the repo or its `.venv` under iCloud: iCloud hides `.pth` files and
  Python 3.13 then skips them.
- python.org's macOS Python has no CA certificates, so downloads pass `certifi`'s bundle
  explicitly (`data.py`).
- **The follow-up is frozen at `followup-freeze`, not HEAD.** Any change under
  `src/opt_agent/` or to the lock makes `followup_freeze.check()` fail, so `followup.load_test`,
  the follow-up report and `scripts/followup_results.py`'s build stop working at HEAD
  (rendering from the committed JSON still works). `python scripts/reproduce.py` rebuilds
  from the tag's own tree (`opt_agent.frozen`: `git archive`, run files and data copied in,
  the tag's package first on the path), and the tag checks (`freeze.approval_at_tag`, used by
  both `tag_problems`) read everything from git's objects, never the working tree. Tests that
  need "not frozen" set it up themselves (`not_frozen` fixture), never rely on the
  repository's state.
- **HiGHS prints `HighsMipSolverData::transformNewIntegerFeasibleSolution tmpSolver.run();`**
  on some MIPs. It changed no verification result (`docs/followup/RUN_NOTES.md`).
- **Problem text is licensed data** (`DATA_NOTICE.md`): commit none outside `runs/` without
  updating the notice; IndustryOR material is non-commercial only.
- **Claude Code's Bash sandbox breaks Python's TLS on macOS** (`OSStatus -26276`, which
  the SDK reports as `APIConnectionError: Connection error.`), while `curl` gets through.
  Paid runs go outside the sandbox. A keyless check costs nothing: `httpx2.get(
  "https://api.anthropic.com/v1/models")` should return 401.

## Settled decisions

- MIT license, "Copyright (c) 2026 Max Reese" (owner, 2026-11-04; this reverses the
  2026-10-16 "no license" call, so the repo can be used and installed). `LICENSE` is the
  plain MIT text, so GitHub detects it; the code-only note is in `DATA_NOTICE.md` and the
  README (2026-11-16, the final review). The
  data keeps its own licenses: NL4Opt is MIT (`data/nl4opt/LICENSE`), ORLMBenchmark is
  Apache-2.0 (credited in `review/external_check.md`), and ORLM's CC BY-NC answer file is
  never committed (the answers reviews cite are listed in `DATA_NOTICE.md`).
- No API key is ever committed: `tests/test_repo_hygiene.py` checks every tracked file
  (the history was checked by hand on 2026-11-04 and is clean).
- Don't file the CBC preprocessing bug upstream (owner's call, 2026-10-16).
