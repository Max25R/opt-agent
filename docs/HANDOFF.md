# Handoff (2026-11-20)

Read CLAUDE.md first (rules, budget, gotchas), then this file: where things stand, every
open item, and the environment. A new session needs nothing else; the full record of
decisions is `docs/HISTORY.md` (to M8) and the decision logs at the end of this file.

## Start here (a new session)
1. `source .venv/bin/activate` (`python` isn't on the path without it), `unset
   ANTHROPIC_API_KEY`, then `git status` and `git log --oneline -5`: the tree should be clean
   at the last commit on `main`, pushed, with CI green (its status: see Environment).
2. **Where things stand: the resampling study is done; R1 is supported.** Its paid run (the
   owner's, from their terminal, 2026-11-19, `runs/resampling`, $1.4884 of its $3.00 cap)
   and its analysis (2026-11-20) are committed: `results/resampling.json` (the frozen
   analysis's report), `docs/resampling/RESULTS.md`, and one deviation that changes no number
   (`docs/resampling/DEVIATIONS.md`: the frozen `main()` couldn't write its JSON, so
   `scripts/resampling_results.py` writes it). The README reports it in a Results subsection
   checked against that file. `python -m opt_agent.resampling_freeze` must still say the tag
   verifies (the inputs at HEAD stop matching once `src/opt_agent/` changes, as for the other
   two studies).
   - **ADR-0009 is done and measured on dev** (2026-11-20, open item 16): for an integer
     program, the explainer gets the solver's own test of what limits the answer. The owner
     regenerated the dev explanations with it (`runs/explain-dev-limits`, $0.0358), and
     `docs/analysis/limits_claims.md` compares the two runs (exploratory). The headline, since
     the owner's call of 2026-11-21: the integer programs' explanations with a false claim of
     any kind went 21 → 10 by the explanation checker's blind labels (ADR-0009's update; the
     rule's count, the headline before, doesn't measure the regenerated text).
   - **The demo's disagreement badge** (2026-11-20; "Current state") has a fifth example
     chosen to show its warning ("Freight cars", from the resampling run, its own replies),
     and since the owner's refresh (2026-11-21, $0.0136) every example compares five samples
     and the direct answer (`pipeline.REFRESHED` on): the four written ones agree.
3. Read "Open items" below. Everything else is optional or the owner's.
4. Before committing: `ruff check . && ruff format --check .`, `python -m mypy`, and
   `HYPOTHESIS_PROFILE=ci python -m pytest` (about 3 minutes; with all the data here, nothing
   skips). After a change under `src/opt_agent/`, `python scripts/reproduce.py` (about 5
   minutes, no key; it once took 39 on a busy machine) must still say every answer replays
   and all 8 files match.

## Current state
- **Everything is committed and pushed** (`main`, 2026-11-20; tags `m6-freeze`,
  `amendment-3`, `amendment-4`, `amendment-5`, `followup-freeze`, `resampling-freeze`), and
  CI's jobs (test on 3.12 and 3.13, types, reproduce, demo-image, pictures, plugin,
  static-demo, deploy-pages) pass on the last commit. The only API calls since 2026-11-15 are
  the owner's two paid runs of 2026-11-19: $0.0399 (open item 14) and the resampling study's,
  $1.4884.
- **The resampling study: done, R1 supported** (run 2026-11-19, analyzed 2026-11-20; "Start
  here", step 2). The pre-registration is `docs/RESAMPLING_PREREGISTRATION.md` (approved by
  the owner with three edits), the runner `src/opt_agent/resampling.py`, the analysis
  `src/opt_agent/resampling_report.py`, the gate `src/opt_agent/resampling_freeze.py`; the
  freeze is `docs/resampling/FREEZE.json` at the tag `resampling-freeze`. The run is committed
  (`runs/resampling`, its cache included); `scripts/resampling_results.py` writes
  `results/resampling.json` with the frozen `build()`'s report and renders
  `docs/resampling/RESULTS.md` from it; `scripts/reproduce.py` replays the run from its cache
  and rebuilds both files in the tag's own tree. The numbers are in those files; the run's
  notes (one pass, the cost, the three commits made during it) are in
  `docs/resampling/DEVIATIONS.md`.
- **ADR-0009, what limits an integer program** (2026-11-20, the owner's request;
  `docs/adr/0009-what-limits-an-integer-program.md`). For a verified integer optimum about to
  be explained, `limits.constraint_limits` solves again without each constraint and with its
  limit one unit further out (CBC and HiGHS must agree, and the arithmetic checks pass;
  otherwise null), and the explainer's facts carry the result with one more paragraph of the
  system prompt. An LP's request, and any request without limits, is byte for byte the old
  one, so every cached explanation still replays; the demo's two integer examples were
  re-explained with limits in the owner's refresh (2026-11-21), so `pipeline.EXPLAIN_LIMITS`
  is on. The dev
  explanations' regeneration is `scripts/paid_explain_limits.py` (the owner's paid run; its
  `--plan` gives the calls and the worst case); the owner ran it on 2026-11-20
  (`runs/explain-dev-limits`, 73 calls, $0.0358). **Measured on dev, exploratory.**
  **Headline: 21 → 10** integer-program explanations with a false claim of any kind, by the
  explanation checker's blind labels (`docs/analysis/limits_checker.json`; the owner's call,
  2026-11-21, for everywhere the result is stated, and `tests/test_explanation_checker.py`
  checks it). It replaced the IP slack check's rule (`docs/analysis/limits_claims.md`,
  `scripts/limits_claims.py`), whose count was the headline from 2026-11-20: against those
  labels the rule doesn't measure the regenerated text (ADR-0009's update and
  `review/explain_dev_limits/RESULTS.md`, both written from that record).
- **The demo's disagreement badge** (2026-11-20, the owner's requests, after R1 was supported).
  In the Flags card (outside the README screenshot's clip, so `docs/demo.png` is unchanged),
  each verified answer shows "Samples disagree — lower confidence" or "Samples agree", what it
  compared, the study's measured precision, recall and base rate, and a link to
  `docs/resampling/RESULTS.md`. The counts are `pipeline.MEASURED`, copied because the image
  has no `results/`, and `tests/test_demo.py` checks them against `results/resampling.json`.
  The flag is the study's (`pipeline.disagreement`, its rules and its `all_agree` and
  `same_answer`): the answer and the other formulation samples must agree, and so must Claude's
  direct answer. Each example replays with the settings its replies were made with
  (`pipeline.profile_for`). **"Freight cars"** (the owner's request): the follow-up's test
  problem `complexlp:195`, chosen to show the warning, replaying six of the resampling run's
  own replies (samples 3 to 7 and the no-solver answer; no checklist or explanation, which the
  study never asked for): verified, flagged and wrong (5,875 against the key's 11,370). It's
  licensed text (`DATA_NOTICE.md`; the page shows its source) and an exception to "demos use
  dev problems only" (CLAUDE.md). The four written examples compare five samples and the
  direct answer since the owner's refresh (2026-11-21, open item 19), and all agree: paint
  1,600, baristas 16, crates 2,370, feed 370, every sample and the direct answer alike.
- **The explanation checker's finding** (2026-11-19, exploratory, Claude's labels, not a
  person's: `docs/analysis/explanation_checker.md` and its JSON). On NL4Opt's dev split no
  explanation used a wrong number, so the number check had nothing to catch (its few flags
  were correctly computed numbers); but about a quarter of the explanations made a false claim
  with every number correct, nearly all about integer programs: a constraint with slack called
  "not limiting" when dropping it changes the integer optimum. No number check can see that;
  open item 16 is what to do about it. The README's limitations say so in an exploratory
  bullet checked against the JSON.
- **The IP slack-claim check** (2026-11-19, exploratory, Claude's labels:
  `docs/analysis/ip_slack_check.md`, `scripts/ip_slack_check.py` and its JSON). From the saved
  dev explanations only, each claim that a constraint doesn't limit an integer program's answer
  (or isn't binding) is tested by solving the model again without it, CBC cross-checked by
  HiGHS. Its rule and flags were committed and pushed (`4b6acd0`) before its one score against
  the 88 labels; the numbers are in its JSON, and its doc says what it misses. No README claim
  changed. It ran while the owner's paid resampling run was going (started 2026-11-19 in this
  checkout, `runs/resampling`): nothing the resampling freeze checks was touched.
- **The README's first screen** (2026-11-19, the owner's request): a 3-line summary, a
  headline figure (`docs/headline.png`: NL4Opt's accuracy per condition and the follow-up's two
  pre-registered differences, with 95% intervals) and a cost and latency table (per answer:
  cost, median and p90 latency), all from `scripts/headline.py`. The figure's numbers are
  copied from the two results files; the table's are computed from the committed test runs'
  logs, which give each condition's total cost and median latency exactly as the results files
  do (the script refuses otherwise), and land in `results/headline.json`. Tests check the record
  (`tests/test_headline.py`) and the README's table against it (`tests/test_readme_numbers.py`,
  `TABLE`: a new exception to the README-number rule, on the owner's request); CI's `pictures`
  job draws the figure. `scripts/reproduce.py` is unchanged.
- **The polish list of 2026-11-18** (the owner's; each item its own commit, CI green each
  time, no API calls; decisions at the end of this file):
  - **The static demo** (item 1): `scripts/static_demo.py` builds the examples page as a
    static site from the demo app's own responses, CI's `static-demo` job checks it in
    headless Chromium, and `deploy-pages` publishes it from `main` to
    `https://max25r.github.io/opt-agent/` (linked at the top of the README) once Pages is
    on. ADR-0008 records why.
  - **The code tour** (item 2): `docs/DESIGN.md` opens with "Read the code in 10 minutes",
    six modules in the order one problem meets them, each opening with a docstring that says
    what it does and why (`agent.py`, `schema.py`, `solver.py` and `verify.py` got fuller
    ones; docstrings only). `tests/test_code_tour.py` keeps its links and docstrings current.
  - **The ADRs** (item 4) were already in `docs/adr/` (0001-0007); 0008 came with item 1.
  - **The README's fresh read** (item 3): tighter where it repeated itself or ran long, with
    no claim or number added or changed; the static page's note is shorter too.
  - **Five proposed next steps** (item 5): open item 14, none started.
- **The owner's list of 2026-11-19** (each item its own commit, CI green each time):
  - **Pages** (item 0): on, and the static demo is live (open item 13).
  - **The disagreement detector** (item 1): `docs/analysis/disagreement_detector.md`. Its
    rules were committed and pushed (`50b30f2`) before its one run; the run (no API calls)
    is in `disagreement_detector.json`, and `scripts/disagreement_detector.py` refuses to run
    again. Exploratory. Every signal passed its pre-declared real-signal rule on the
    follow-up, so the doc proposes a pre-registered resampling study (open item 15). No
    README claim changed, so no limitations line was added.
  - **The Agent Skill** (item 4): `skills/opt-agent/` (`SKILL.md` and two scripts that need
    only PuLP 4 and SciPy), tested on the paint example's cached replies
    (`tests/test_skill.py`), mentioned in the README, and listed in the repository's own
    plugin marketplace (`.claude-plugin/marketplace.json`).
  - **The README's exploratory detector line** (owner, 2026-11-19): one Limitations bullet
    labeled "Exploratory", its numbers checked against `docs/analysis/disagreement_detector.json`
    by `tests/test_readme_numbers.py` and left out of the results-file check (CLAUDE.md's hard
    rule names the exception).
  - **Item 3, after the owner's paid run** (2026-11-19, $0.0399 on 103 calls, ledger
    `logs/spend/paid-2026-11-19.jsonl`): the explanation checker's evaluation is written up
    (`docs/analysis/explanation_checker.md`, its JSON and `scripts/explanation_checker.py`;
    the run is committed in `runs/explain-dev/`, pruned to the 180 replies it replays, and the
    labels in `review/explain_dev/`), and the README's limitation says what it found, in an
    exploratory bullet checked against its record. The fix-step example: none of the 15 tries
    failed its first attempt, so nothing was added to the demo
    (`docs/analysis/fix_step_tries.json`; ADR-0007's action item stays open).
  - **The plugin marketplace and Agensi** (later list): CI's `plugin` job installs Claude
    Code 2.1.311, validates `.claude-plugin/marketplace.json` and installs the skill from it
    as the README says; the skill's scripts are executable, as Agensi asks (open item 17).
  - **The resampling study** (later list): drafted, approved by the owner with three edits,
    built (runner, analysis, gate, tests) and frozen at `resampling-freeze`; run by the owner
    and analyzed on 2026-11-20 (above).
  - **The paid command** (item 2, run by the owner on 2026-11-19): `scripts/paid_dev_and_demo.py`.
    Part 1 explains every verified single-shot answer on NL4Opt's dev split (all 92
    formulations replay from `runs/dev-1`; 88 explanation calls) for the explanation
    checker's study, whose protocol was committed first (`docs/analysis/explanation_checker.md`).
    Part 2 tries three candidate examples (`demo.examples.FIX_STEP_CANDIDATES`, each with a
    units or percentage trap and a hand-checked answer) for one whose first model fails and
    whose revision is verified and right. `--plan`: worst case $0.75 + $0.37, expected about
    $0.09; hard cap $0.30. Prices re-checked on the pricing page (2026-11-19): unchanged.
- **Since 2026-11-16** (the owner's list of 2026-11-17, each item its own commit, CI green
  each time; no API calls):
  - CI's jobs have `timeout-minutes` as a hang guard (10; 30 for reproduce), and a new
    `types` job runs mypy on `src/`. The reproduce job runs the whole suite under coverage
    and fails if the README's coverage badge (`docs/badges/coverage.json`,
    `scripts/coverage_badge.py`) is more than a point off. mypy and coverage come from the
    optional `requirements-checks.lock`.
  - **Two exploratory, post hoc analyses** in `docs/analysis/` (the numbers are in their own
    JSON files; nothing in them is a result of record): why every wrong answer of the solver
    conditions was wrong (`failure_types.md`: a taxonomy committed before classifying, and
    the classifying is Claude's, not a person's), and a silent-failure detector whose rule
    was committed before its one run (`silent_detector.md`; it refuses to run again).
  - The README's architecture diagram follows problem, Claude, model, CBC, checks,
    explanation; `docs/adr/` holds retrospective decision records.
  - The owner's interview notes are in `private/` (git-ignored, never committed).
  - The final review's nice-to-have items are done (item 7).
  - Later on 2026-11-18 (the owner's second list): the two bugs mypy found are fixed (item 8);
    the failure-type figure's legend is below the plots; wherever the answer-key-dispute share
    appears, it leads with problems (13 of the 35 follow-up problems with a wrong answer, 8 of
    M6's 18; the failure-type table counts problems before answers) and says an LLM judge
    flagged them, not verified by a person; and `docs/analysis/dispute_spotcheck.md` lists 10
    disputed follow-up problems (seeded) for a person to check (item 9). The owner's wording
    rule: a dispute share always leads with the problem count and its denominator, and frozen
    files keep their wording.
- **M7's demo and M8 are done** (2026-11-15): the demo (`src/opt_agent/demo/`, Docker, CI),
  `scripts/reproduce.py` (every number replayed and rebuilt from the tags, in CI), the
  rewritten README, and the IE 2310 kit (`docs/ie2310/`). The decisions are at the end of
  this file.
- **M6 is done and frozen.** Tag `m6-freeze` = `8f522c0`, the commit both test runs ran on.
  Result of record: the pre-registered strict accuracy (`results/eval.json`). The M6 reports and
  `results/eval.json` rebuild byte-identical from the tag (`scripts/reproduce.py`, in CI;
  checked again from a fresh clone on 2026-11-15).
- **Amendments:** 1 and 2 are in the frozen `docs/PREREGISTRATION.md`; 3, 4 and 5 are in
  `docs/amendments/`, tagged.
- **M7, the follow-up study: done.** On LLM4OR's cleaned ComplexLP (86) and IndustryOR (42),
  128 problems, 3 samples, 4 conditions (baseline, single-shot, self-correction, checklist
  revision), Claude Haiku 5.5.
  - **Pre-registration** `docs/FOLLOWUP_PREREGISTRATION.md`, approved and frozen 2026-11-13
    (`docs/followup/FREEZE.json`, approval at `f2bd2e3`; tag `followup-freeze` = `f36e812`).
  - **Run** `runs/followup-test` (committed, commit `7cfe7bb`): one pass at `f36e812`, clean
    tree, fingerprint equal to the approval's; 1536 answers, 0 errored; $2.7176 on 1252 calls.
  - **Results** (primary: the unexposed problems): H2, single-shot minus baseline,
    **detected** on the sign-flip test, though McNemar on majority isn't significant and
    part of it comes from baseline replies cut off at max_tokens; H1, checklist revision
    minus single-shot, **inconclusive**. The numbers are in `results/followup.json` only
    (rendered in `docs/followup/RESULTS.md` and the README).
  - **Write-up:** `docs/followup/RESULTS.md` and the README's "Harder problems" subsection,
    every number from `results/followup.json` (`scripts/followup_results.py`), checked by
    `tests/test_readme_numbers.py` and `tests/test_followup_results.py`.
  - **Deviations** (`docs/followup/DEVIATIONS.md`): 2, the 5b key-dispute check **wasn't
    performed** (owner, 2026-11-15, for time, before any encoding or judging): no
    corrected-key row, the raw keys are the result of record, and the 15 trigger problems
    are listed by label; whether any are key errors is unknown. 1 (Gemini JSON encodings)
    is superseded by 2. The dispute plan (`review/followup_disputes/README.md`) is marked
    not run; its packets are git-ignored and `scripts/historical/dispute_packets.py` is kept.
  - **Run notes** (`docs/followup/RUN_NOTES.md`): HiGHS's debug print, and where problem text
    is committed.
  - **Dev:** `docs/FOLLOWUP_DEV_LOG.md` (checklist revision 1; revision 2 unused; the smoke
    run; the bug fixes made before the freeze, including CBC's optimum at an infeasible point).
- **Data notice** (`DATA_NOTICE.md`, linked from the README's "License and sources"
  section; `LICENSE` is the plain MIT text, so GitHub detects it): MIT covers the code only. `runs/` holds problem text and answers from Mamo
  ComplexLP (CC BY-SA 4.0) and ORLM's IndustryOR (CC BY-NC 4.0), as cleaned by LLM4OR at
  `75962df` (no license stated), plus NL4Opt (MIT). History was kept (owner, 2026-11-15):
  rewriting it would break `followup-freeze` and the commit in `FREEZE.json`.
- **Spend:** $5.47 of the $20 credit ($0.98 before the follow-up, $0.1775 for the
  condition-4 dev smoke run, $2.7176 for the test run, $0.0139 for the demo examples'
  replies, $0.0399 for the paid run of 2026-11-19, ledger
  `logs/spend/paid-2026-11-19.jsonl`, and $1.4884 for the resampling study's run, ledger
  `runs/resampling/spend.jsonl`, and $0.0358 for ADR-0009's dev regeneration, ledger
  `runs/explain-dev-limits/spend.jsonl`, and $0.0136 for the demo's refresh, ledger
  `logs/spend/demo-examples.jsonl`). About $4.80 of November's $10 limit is left; it resets
  on December 1.

## Open items
1. ~~M7 demo~~ and ~~M8's README and reproduce script~~: done 2026-11-15.
2. **Left for the owner, on GitHub:** the repository's description and topics (its
   settings). Suggested: the description from `pyproject.toml`, and the topics `llm`,
   `operations-research`, `linear-programming`, `evaluation`, `claude`. The earlier audit's
   docs fixes (`docs/audit/2026-11-review.md`, section 5) are done, except renaming the
   `owner` source of the 4 rule-set `either` labels: that changes `integrality.json`, an
   input of the frozen answer key, so it's left as is (`docs/DESIGN.md` explains them).
2a. ~~The README's screenshot~~: done 2026-11-15. It's `scripts/screenshot.py`'s own output
   from the owner's Mac, byte-stable (`test_the_picture_is_byte_stable`); `frame()`'s rules
   and what CI's Linux fonts taught it are in the script and `tests/test_screenshot.py`, and
   CI's `pictures` job checks a Linux capture's margins (artifact `demo-screenshot`).
3. ~~A CI check of the `followup-freeze` tag~~: done 2026-11-15 (`followup_freeze.tag_problems`,
   see "Decisions made without the owner" below).
4. ~~`amendment-5.md`'s status line~~: fixed 2026-11-15 (only that line, as for Amendment 4).
5. **Known and unfixed since M6** (the one list; CLAUDE.md points here): the integrality
   rule matches ingredient names (`docs/amendments/DEVIATIONS.md`, section 3);
   `DEV_WALKTHROUGH.md` predates the owner's milestone 3 corrections (whether to regenerate
   it is the owner's call); no Farkas certificate for infeasible LPs; the agent CLI needs a
   key even when every call is cached (the demo's examples mode and `scripts/reproduce.py`
   don't).
6. **Optional, exploratory only:** the 5b check could still be run later
   (`review/followup_disputes/README.md`), at the commit its script ran at
   (`scripts/historical/README.md`); anything it found would be post hoc, never the result
   of record. The failure-type analysis is a reason to: an LLM judge (Claude) flagged the key on 13
   of the 35 follow-up problems with a wrong answer, not verified by a person, some checkable
   by arithmetic (the routing keys that are two separate round trips;
   `docs/analysis/failure_types.md`). `docs/analysis/dispute_spotcheck.md` draws 10 of the
   disputed problems (seeded) for a person to check first.
7. **The final review** (2026-11-15): `docs/audit/2026-11-final-review.md`. Its mechanical
   fixes, its must-fix items (M1-M5) and its should-fix items (S1-S11) are done, on the
   owner's go-ahead (2026-11-16), except what only the owner can do (item 2) and what would
   change frozen inputs. Its nice-to-have items are done (2026-11-18), except the two it
   marks as notes: stale status lines in frozen or tagged files, and the lightweight
   `followup-freeze` tag (no tag is rewritten). Its status line says so.
8. ~~Two possible bugs mypy found~~: fixed 2026-11-18, each with a regression test, and
   neither affected the studies. `integrality.Integrality` refuses a judges' label without
   `replaced` (`packets.claude_label` returned None for one, which the agreement statistic
   would have counted as a disagreement), and `solver.solve` returns ERROR, a loud failure,
   when CBC leaves an LP's constraint without a dual (it raised a TypeError that would end a
   run). The evidence: every judges' label in the committed data keeps `replaced` (all 40 in
   the blind sample, the statistic's only input); an instrumented replay of the three
   committed runs in their tags' trees found no unset dual in 2,726 LP solves (16,309
   constraints) and no difference; `scripts/reproduce.py` matches; and the ground truth and
   perturbed splits rebuild byte for byte with the fixed solver.
9. **The dispute spot-check, for a person** (the owner or a teammate; not Claude):
   `docs/analysis/dispute_spotcheck.md` has an empty verdict column for 10 problems (key
   wrong, model wrong, both defensible, can't tell). Filling it in is the cheapest step
   toward item 6. It's exploratory: a verdict never changes a result of record. Only the
   verdict column is edited by hand: `python scripts/dispute_spotcheck.py` keeps the
   verdicts when it writes the doc again, and `tests/test_dispute_spotcheck.py` checks the
   rest against the script's output (when LLM4OR's data is present).
10. **A latent quirk, unfixed (owner's call):** `packets.claude_label` returns `either` for the
   owner's 4 `either` labels, though their `replaced` holds Claude's label. None is in the
   blind sample, the agreement statistic's only input, so no number depends on it; a fix
   (`return label.replaced` whenever it's set) would change no result.
11. **Left to the IE 2310 teammate:** the time study, the flow charts and the project summary
   in `docs/ie2310/` (never written by Claude).
12. **ADRs:** `docs/adr/` holds the retrospective 0001-0007, 0008 (the static demo,
   2026-11-18), 0009 (what limits an integer program, 2026-11-20) and an index (`README.md`);
   add a new one for any new design decision.
13. ~~Turn on Pages~~: done 2026-11-19 by the owner (Settings > Pages > Source: GitHub
   Actions), then a manual CI run on `365d23e` deployed it. Checked through the public API
   and a browser: every job of that run passed, `deploy-pages` included, and
   `https://max25r.github.io/opt-agent/` serves the static demo, stamped `365d23e`, all four
   examples verified and matching. Every push to `main` now redeploys it. (The public
   `GET /repos/.../pages` answers 404 without a token, so it can't show whether Pages is on;
   CI's check sends the job's token.)
14. **The proposals of 2026-11-18** (item 5 of the polish list), where each stands:
   1. A person fills in the dispute spot-check (item 9): **open**, 1-2 hours, $0. An LLM judge
      flagged the key on 13 of the 35 follow-up problems with a wrong answer, not verified by
      a person.
   2. A demo example whose first model fails: **tried, none found** (the owner's paid run of
      2026-11-19, `scripts/paid_dev_and_demo.py` part 2): three candidates with units or
      percentage traps (`demo.examples.FIX_STEP_CANDIDATES`), five samples each, and all 15
      first models were right (`docs/analysis/fix_step_tries.json`), so the demo is
      unchanged and ADR-0007's action item stays open. Another try needs a trap Haiku
      actually falls into (a paid run, the owner's).
   3. Sample agreement as a silent-failure signal: **done, exploratory**, as the disagreement
      detector (`docs/analysis/disagreement_detector.md`); it led to item 15.
   4. The explanation checker evaluated on dev: **done, exploratory**
      (`docs/analysis/explanation_checker.md`; the finding is under "Current state"; open
      item 16 follows from it).
   5. A second model under its own pre-registration and cap (ADR-0006's ladder): **open**, 2-3
      days plus a paid run sized by `evaluate --plan`; the budget is the owner's call.
15. ~~The resampling study~~: run (the owner's, 2026-11-19) and analyzed (2026-11-20); R1
   is supported ("Current state").
16. **The explanation checker's blind spot** (from item 14.4; ADR-0004, action item 3): false
   claims about slack in integer programs. Options: a check that tests each "not limiting"
   claim by re-solving without the constraint: **done, exploratory** (2026-11-19,
   `docs/analysis/ip_slack_check.md`; its numbers are in its JSON): it finds a claim only when
   its rule can parse it from the free text, which is its weak part. Computing each
   constraint's effect with the solver and giving the explainer those facts: **done** as
   ADR-0009 (2026-11-20), regenerated and compared on dev (exploratory,
   `docs/analysis/limits_claims.md`); its open steps are refreshing the demo's two integer
   examples (open item 19's paid run) and the Agent Skill. Not started:
   placeholders instead of free-form explanations; or telling the explanation prompt that slack
   doesn't mean "not limiting" in an integer program (a prompt change: dev only, and a new
   evaluation).
17. **The Agensi listing:** the owner uploads `skills/opt-agent/` to agensi.io by hand (its
   format: `name` equals the folder, a short description, executable scripts; all done).
   The repository's own plugin marketplace stays while CI's `plugin` job passes.
18. **The README's exploratory bullets** (the disagreement detector, the explanation checker)
   are checked against `docs/analysis/*.json`, not the results files: the one exception to
   the hard rule (CLAUDE.md). The resampling study's numbers are in
   `results/resampling.json`, and the README's subsection about it is checked against that
   file.
19. ~~The demo's refresh~~: done 2026-11-21. `scripts/cache_examples.py` (the owner's paid run,
   cap $0.15) cached four more formulation samples of each written example (the badge's
   five-sample half) and the two integer examples' explanations with ADR-0009's limits: 18
   calls, $0.0136 (`--plan` had said worst case $0.08, expected about $0.03). "Freight cars"
   needed none. The run landed at 00:20-00:22 EST (an earlier report of it had left nothing
   here), and `pipeline.REFRESHED` turned on; a test refuses it while anything is missing.
20. ~~The explanation checker on ADR-0009's regenerated explanations~~: done 2026-11-21
   (`docs/analysis/limits_claims.md`, last section; `docs/analysis/limits_checker.json`). Four
   blind Claude subagents labeled `review/explain_dev_limits/` in a session (no API call), and
   `scripts/explanation_checker.py score --after` scored it: 22 → 11 explanations with a false
   claim, comparable by the owner's rule (15 of 15 shared LP entries alike). Exploratory,
   Claude's labels. Since the owner's call of 2026-11-21, its integer-program count, 21 → 10,
   is ADR-0009's headline, in place of the rule's. The rule's precision and recall against
   these labels, the pairs (post hoc, the owner's requests) and Claude's reading of what the
   labeled false claims are: `review/explain_dev_limits/RESULTS.md` and ADR-0009's update,
   from the same record.

## Environment (read before running anything)
- **The owner's Mac is Apple Silicon** (`uname -m` says `arm64`), where all three studies ran and
  where CI's `reproduce` job runs (`macos-15`); CBC comes from `cbcbox` 2.929 because later
  builds crash there (CLAUDE.md).
- **No `gh`.** Read CI from the public GitHub API with `curl` and `jq`:
  `api.github.com/repos/Max25R/opt-agent/actions/runs?head_sha=SHA` for the run, then
  `.../actions/runs/RUN_ID/jobs` for each job's name, status and conclusion. In the sandbox a
  command needs the host listed (`api.github.com`; `github.com` for `git push`).
- **CI's jobs:** test (3.12, 3.13), types, reproduce (macOS), demo-image, pictures, plugin
  (Claude Code's CLI validates the marketplace and installs the skill from it), static-demo
  and deploy-pages (main only).
- **CI waits are capped at 30 minutes** (owner): poll every minute or two; if it isn't done
  by then, stop and report each job's name and status instead of waiting. A normal run takes
  about 10 minutes (the macOS `reproduce` job is the long one). The jobs' `timeout-minutes`
  (10; 30 for reproduce) are a hang guard, not a speed alarm: don't tighten them.
- **Claude Code's sandbox** can't: start a browser (Chromium can't register its Mach port,
  so `scripts/screenshot.py` runs only outside it, or in CI's `pictures` job); open or reach
  local ports (EPERM; the demo is checked in the desktop app's browser pane, or by CI's
  `demo-image` job); or make paid calls (Python's TLS fails with `OSStatus -26276`, and the
  budget rules forbid it anyway: paid runs are the owner's, in their terminal, after
  `--plan`). Changing sandbox settings is the owner's decision.
- **pip in the sandbox** fails TLS too: `pip install --use-deprecated=legacy-certs ...` uses
  certifi's bundle and works.
- **zsh:** write `${tag}:path`, not `$tag:path` (`:s` is a zsh modifier, so `git show
  $t:src/...` silently shows nothing). Use `$TMPDIR` for scratch files, and set
  `MPLCONFIGDIR="$TMPDIR/mpl"` before matplotlib (the home directory isn't writable).
- **Long commands** (the suite, `reproduce.py`, `failure_types.py build`, the ground-truth
  rebuild) take 2-5 minutes: run them in the background, one heavy job at a time.

## Gotchas
- **The analyses' working files** (`review/failure_types/`, git-ignored: they hold problem
  text) come from `python scripts/failure_cases.py` (a replay in each tag's tree, no key);
  `python scripts/failure_types.py build` needs them and the labels there. The detector
  never runs again (`docs/analysis/silent_detector.json` exists); its doc's results section
  rebuilds with `python scripts/silent_detector_report.py`.
- **mypy:** new code must keep `python -m mypy` clean; a `type: ignore` needs its code and a
  reason on the line. The coverage badge moves only when `scripts/coverage_badge.py` is
  rerun after a full suite with all the data, and CI fails if it's more than a point off.
- **All three studies are frozen at their tags, not at HEAD.** Any change under
  `src/opt_agent/` (and to the frozen docs, the lock, `split.json` or the LLM4OR files) makes
  `python -m opt_agent.freeze`, `followup_freeze` and `resampling_freeze` report a mismatch
  (and `resampling.problems`, so `scripts/resampling_results.py`'s build, refuse at HEAD).
  For the follow-up that also means `followup.load_test` raises `FreezeError`, so
  `python -m opt_agent.followup_report runs/followup-test` and `scripts/followup_results.py`
  (the build) stop working at HEAD, as they should. To rebuild, run
  `python scripts/reproduce.py`: it extracts each tag's tree with `git archive` into a
  temporary directory (`opt_agent.frozen`; no worktree, so it works in the sandbox and CI),
  copies in the run files and the LLM4OR data, and runs the tag's own code there.
  The tag checks (`freeze.tag_problems`, `followup_freeze.tag_problems`) read each approval
  and every frozen file from git's objects, so a change at HEAD never fails them.
- **Never edit frozen files:** `docs/FOLLOWUP_PREREGISTRATION.md` (its status paragraph still
  reads like a draft's after the first sentence; leave it), `docs/followup/judge_prompt.md`,
  `docs/followup/FREEZE.json`, `docs/PREREGISTRATION.md`, `docs/FREEZE.json`. Record changes as
  deviations or amendments instead.
- **Tests mustn't assume a freeze state.** Since the follow-up was frozen, tests that need
  "not frozen" point `followup_freeze.FREEZE_PATH` at an empty temporary path (the
  `not_frozen` fixture) or patch `PREREGISTRATION_PATH`; five tests broke on this at the
  freeze and were fixed on 2026-11-15.
- **README numbers:** the NL4Opt results subsection and `docs/EVALUATION.md` come from
  `results/eval.json`, the "Harder problems" subsection and `docs/followup/RESULTS.md` from
  `results/followup.json`, the cost and latency table at the top from `results/headline.json`
  (`python scripts/headline.py` rebuilds it and the figure), and the rest of the README is
  checked against both results files. Write
  results in digits; the test matches by value at the shown precision, and signs count.
- **Problem text is licensed data.** Don't commit new problem text or keys outside `runs/`
  without updating `DATA_NOTICE.md`; dispute packets and prompts are git-ignored. IndustryOR
  material is non-commercial only.
- **HiGHS prints `HighsMipSolverData::transformNewIntegerFeasibleSolution tmpSolver.run();`**
  on some MIPs (about 40 times in the test run). Harmless as far as the checks show:
  `docs/followup/RUN_NOTES.md`.
- `runs/` is git-ignored: commit a run directory with `git add -f`. The M6 dev runs
  (`runs/dev-1`, `dev-2-baseline`, `dev-perturbed-*`, `smoke`) and `logs/` are local only.
- `.env` is read only with `OPT_AGENT_LIVE=1`, so unsetting `ANTHROPIC_API_KEY` guarantees
  no spend. Paid runs happen in the owner's terminal (the sandbox breaks Python's TLS); give
  the commands and the `--plan` cost first.
- The LLM4OR data is in `data/external/` (git-ignored; `docs/EXTERNAL_DATA.md`), so CI's test
  job skips every test that needs data and copies `amendment_5` in `eval.json` forward. The
  `reproduce` job fetches all the data (LLM4OR's, and `python -m opt_agent.data`), rebuilds
  every number, then runs the whole suite with Pillow, where no test may skip.
- M6 rebuild order: `opt_agent.report`, then `scripts/amendment3.py`, then
  `scripts/eval_json.py`. CI checks the M6 freeze against its tag (`fetch-depth: 0`), so push
  tags with commits.

## Decisions made without the owner (session of 2026-11-15)
Logged here as the owner asked: the simplest reasonable option, where the request didn't say.
- **Step 0, the freeze checks.** `freeze.approval_at_tag` reads a study's approval and every
  file its fingerprint names from git's objects at the tag; M6's `tag_problems` and the new
  `followup_freeze.tag_problems` both use it (the LLM4OR data is git-ignored, so a local copy
  is checked against the tag's approval instead). `check()` still compares the working tree,
  because it gates a new test run, and it now refuses at HEAD for both studies. The rebuild
  runs the tag's code in a `git archive` tree (`opt_agent.frozen.Tree`) rather than HEAD's,
  so a later refactor can't silently change a number; `scripts/reproduce.py` started with the
  follow-up (3 files, byte for byte, about 5 s). Checked: with a throwaway edit under
  `src/opt_agent/` and fastapi/uvicorn added to the lock, the whole suite passed (988) and
  the follow-up rebuilt byte for byte; the edit was reverted.
- **Step 1, the demo** (`src/opt_agent/demo/`; FastAPI is imported only there, and it's the
  `demo` extra). fastapi 0.163.1 and uvicorn 0.54.0 (with starlette, click, annotated-doc)
  are pinned in `requirements.lock`, installed with the old lock as a constraint, so no study
  package moved; each tag keeps its own lock, which the rebuild checks.
  - **Modes.** Examples (default) replays the examples through `api.ReplayOnlyClient`, which
    has no key and sends nothing; other text gets 404. Live needs `OPT_AGENT_LIVE=1`; with it
    and no key the app refuses to start rather than quietly falling back. The examples
    replay for free in live mode too.
  - **Live guards.** One solve at a time (a second request gets 429, not a queue of paid
    calls); at most 4,000 characters (413); every reply capped at 8,000 tokens, half the
    studies' 16,000 (`api.max_tokens_cap`, a ContextVar read where requests are built, so
    the cap is in what's sent, hashed and cached; M6's longest formulation reply was 3,409
    tokens); and `budget.BudgetedClient` with a $0.50 cap by default
    (`OPT_AGENT_DEMO_CAP_USD`, ledger `logs/spend/demo.jsonl`). `api.UNFINISHED`'s cut-off
    message no longer names 16,000, since the demo's cap differs (the frozen code keeps its
    own message; `scripts/followup_results.py` matches the frozen one).
  - **Pipeline.** Self-correction (3 attempts, as evaluated), plus the report-only estimate
    and checklist and the explanation: up to 6 calls per problem.
  - **Examples.** Four original problems (paint production, café staffing, produce shipping,
    cattle feed), each with a hand-checked answer that a test re-derives with both solvers;
    only the staffing one is integer-sensitive (LP 15.4, integer 16). The page says whether
    a verified answer matches it, which is the point verification can't make on its own.
    Their replies go in `src/opt_agent/demo/replies/` (not `cache/`, which `.gitignore`
    ignores), written by `scripts/cache_examples.py` (paid; the owner runs it).
  - **Image.** `python:3.13-slim`, the whole lock (dev tools included: one lock is simpler
    than two), the package installed with its page and replies, a non-root user. CI's
    `demo-image` job builds it, smoke-tests `/health`, the examples and the paint example's
    replay (`scripts/demo_smoke.py`), and checks that live mode without a key won't start.
  - The sandbox can't bind or reach local ports, so the page was checked in the desktop
    app's browser pane with fake replies in a scratch directory (never committed).
  - **The examples' replies** (owner's terminal, 2026-11-15): 16 calls, $0.0139. Replayed
    with no key, all four are verified and equal their hand-checked answers, with no
    low-confidence or checklist flag; their models read the text correctly. So no example
    needed the silent-failure label the owner asked for in case one missed.
    `test_each_committed_example_replays_and_matches_its_hand_checked_answer` pins this.
- **Step 2, reproduce and the README.**
  - **`scripts/reproduce.py`** runs each study's frozen code in its tag's tree. It replays
    every committed answer from the run's cache through `scripts/replay_run.py` (a client
    that refuses every request; everything recorded must match except time and what was paid
    or cached), then rebuilds both M6 reports (the Amendment 3 row included), both follow-up
    files and both results files byte for byte. Locally: all 3,078 answers replay and all 6
    files match, in about 3.5 minutes. The M6 write-up scripts are copied in from HEAD,
    since they were written after the freeze against the same package.
  - **Linux versus macOS (CI, 2026-11-15).** On ubuntu-latest, M6 replayed and rebuilt
    exactly, but the follow-up didn't: for `industryor:29`, checklist revision, sample 1, CBC
    returned another optimal solution of the same model, so the checklist's rule 4 (a
    difference the optimum shows can't have changed the answer is a note) turned its flags
    into notes and no revision was made; the committed run (macOS) revised, to the same
    status and objective. And `stats.sign_flip_exact` gave four p-values that differ in their
    16th digit (floating-point sums), which changes the bytes of `followup_report.json` and
    `results/followup.json`, not any reported number. So the job runs on `macos-15`, the
    studies' platform; the frozen code can't be changed, and both differences are recorded
    here and in `scripts/reproduce.py`'s docstring.
  - **CI's `reproduce` job** fetches LLM4OR's data first (`scripts/fetch_llm4or.py`: a
    sparse clone at the pinned commit, every file checked against the hashes the studies
    recorded, never committed). Without the data there's no follow-up or Amendment 5 to
    check, so the script refuses rather than skipping.
  - **The README** was rewritten for a short read: pitch, screenshot, results, limitations,
    quickstart, reproduce, a diagram, positioning, links. The M6 write-up moved verbatim to
    `docs/EVALUATION.md` and the design sections to `docs/DESIGN.md`.
    `tests/test_readme_numbers.py` now checks the whole README (fenced code left out) against
    both results files, each results subsection against its own file, and
    `docs/EVALUATION.md` against `eval.json`.
  - **The screenshot.** No headless browser can start inside Claude Code's sandbox (macOS
    denies Chromium's Mach port registration), so `docs/demo.png` was captured in the
    desktop app's browser pane from the real demo (examples mode, the committed replies) and
    cropped. `scripts/screenshot.py` captures it headlessly (Playwright, the app in-process,
    no port), and CI's `pictures` job runs it and keeps a 2x PNG as the `demo-screenshot`
    artifact; either can replace the committed image.
  - Playwright and matplotlib are pinned in the optional `requirements-docs.lock` (owner's
    request, 2026-11-15), installed on top with requirements.lock as a constraint; neither
    freeze fingerprints it, and `tests/test_lock.py` checks it never re-pins a package of
    requirements.lock. The name says what it's for: requirements.lock already holds the
    `dev` extra (pytest, ruff, hypothesis). CI's `pictures` job (was `screenshot`) installs
    it from a fresh clone and runs both picture scripts. The demo page now renders the
    explanations' **bold** (DOM nodes only, no innerHTML).
- **Step 3, the IE 2310 kit** (`docs/ie2310/`; no rubric was in the repository, so the layout
  is my choice). `summary.md` (about 830 words, plain English, framed as verification versus
  validation), `figures/` (accuracy with 95% intervals, silent and loud failures, cost; one
  panel per study, light mode, the dataviz reference palette's first two slots), and
  `numbers.md`/`numbers.csv` (every number with its JSON field; per-answer costs marked
  derived), all from `scripts/ie2310.py`. Tests keep the table current and check every
  number in the summary against the results files. The palette validator couldn't run (no
  Node.js here); the two colors are the reference palette's slots 1 and 2, which it
  documents as validated. Nothing of the teammate's parts (time study, flow charts,
  summary) was written.

## Decisions made without the owner (session of 2026-11-18, the polish list)
Logged as the owner asked: the simplest reasonable option, where the request didn't say.
- **Item 1, the static demo.**
  - **Computed at build time, not in the browser** (ADR-0008): a browser can't run CBC, so
    Pyodide would have dropped the CBC-versus-HiGHS cross-check. The build runs the demo app
    in-process (TestClient, examples mode, the committed replies) and saves the bytes of
    `/health`, `/examples` and each example's `/solve`; a test compares them with the app's
    answers. The page says plainly that the solving happened when the site was built.
  - **One page, two modes:** `page.html` says `data-site="server"`; the build switches it to
    `static` and stamps the commit (left out if tracked files have uncommitted changes).
    Static mode fetches relative paths (the site lives under `/opt-agent/`) and never posts;
    other text gets an examples-only refusal, as examples mode's 404 does. The app serves the
    page unchanged, so the local demo and `docs/demo.png` are unaffected.
  - **In `ci.yml`, not a separate workflow,** so the deploy waits for the tests:
    `static-demo` builds and checks the site on every push and pull request and uploads the
    Pages artifact; `deploy-pages` (needs `test` and `static-demo`) runs on `main` only, and
    only when the Pages API says the source is GitHub Actions, so CI stays green until the
    owner turns Pages on. `workflow_dispatch` was added so a deploy can be started by hand.
    `actions/upload-pages-artifact@v5` and `actions/deploy-pages@v5`, the current releases.
  - **The browser check** (`scripts/static_demo.py --check`, CI only: the sandbox can't start
    Chromium) loads the site under a base path with every request answered from the
    directory, as `scripts/screenshot.py` does: each example verified and matching its
    hand-checked answer, other text refused, no page error, and no request but GETs of the
    site's files. Locally the page was checked in the desktop app's browser pane, in both
    modes (a static server on the built site, and the app).
- **Item 2, the code tour.** The six follow one problem: `agent.py` (the map), `formulate.py`,
  `schema.py`, `solver.py`, `verify.py`, `self_correct.py`; `api.py`, `evaluate.py` and
  `scoring.py` are named after them as the evaluation's part, since the replay story is the
  evaluation's, not one problem's. The modules' code is unchanged, so both studies still
  rebuild byte for byte (`scripts/reproduce.py`).
- **Item 3, the README's fresh read.** Read as a recruiter (60 seconds: the title, the demo
  link, the pitch, the table, the screenshot) and as an engineer (10 minutes: results,
  limitations, how it works, reproduce). The top already worked; the edits are where text
  repeated itself or ran long: the pitch's long sentence split in two; NL4Opt's paragraph no
  longer restates the summary, and its dispute share leads with the count (6 of the 8 problems
  all three conditions got wrong), as the owner's wording rule asks, which also fixed the same
  share-first heading in `docs/EVALUATION.md`; H1's pre-registered reading said once;
  Limitations no longer repeats H2's caveats, and the integrality-rule bug joined the
  answer-key bullet; the demo, reproduce and development notes are shorter; the code tour is
  linked from "How it works" and "More detail". No claim or number was added or changed
  (`tests/test_readme_numbers.py`). The static page's note was shortened in the same pass (on a
  phone it ran to nine lines above the examples). Headings are unchanged: the static page links
  to `#try-the-demo`.

## Decisions made without the owner (session of 2026-11-19)
- **Item 1, the disagreement detector.** The unit is one single-shot answer that reported
  one, as for the number-coverage detector, so the two compare on the same 380 follow-up
  answers. "Same answer" is each grader's own code at its tag (`followup_report.same_answer`,
  1e-4; M6's status plus `ground_truth.same_value`, 1e-6), run inside the tag's tree; three
  samples agree only if every pair does, since a tolerance isn't transitive. NL4Opt has one
  sample and no checklist condition, so only (c) applies there and (d) is (c). For NL4Opt's
  "without the disputed problems", the analogue of the follow-up's 13 is the 5 main-run
  problems the same failure-type classification flagged. The real-signal rule (precision's
  lower 95% Wilson end above the base rate, with and without the disputes) was fixed before
  the run, knowing the intervals are too narrow, as a screen for a pre-registered study. After
  the run, only the results table's layout changed (the base rate's interval added, which the
  owner asked for); the counts are the one run's.
- **Item 4, the Agent Skill.** "Free listing" was first read as the free route the plugin
  docs describe, the repository's own marketplace file; the owner then said it meant a free
  listing on agensi.io, which they upload by hand (2026-11-19). For Agensi, the scripts got a
  shebang and the executable bit (its format asks for both; the skill's `name` already
  matches its folder). The repository's marketplace stays only while CI's `plugin` job
  (`claude plugin validate`, the CLI pinned at 2.1.311) passes; otherwise it and the README's
  install commands go. It passes, with no login, and the job also runs the README's two
  install commands against the checkout (`claude plugin marketplace add ./`, then `install`),
  so they're tested too. Validating `skills/opt-agent` alone fails by design: it has no
  manifest, the docs' single-skill layout, which the marketplace entry describes. The
  plugin's root is `skills/opt-agent/` itself (a plugin with `SKILL.md` at its root loads as
  one skill), so an install copies that folder, not the 80 MB repository; no `version`, so
  updates follow the commit. The helpers are a short, self-contained restatement of the
  project's checks (bounds, integrality, constraints, objective, the LP duality certificate,
  the explanation's number rule, the same regex and rounding as `explain.py`); they leave out
  the improving-ray check and the feasibility solve that settles CBC's infeasible or
  unbounded labels, so there a CBC-HiGHS disagreement is the only guard, and SKILL.md says to
  report no answer then. PuLP 4 only: the scripts stop with a clear message on PuLP 2. The
  `claude` CLI isn't on this machine, so `claude plugin validate .` wasn't run;
  `test_the_repository_is_a_marketplace_for_the_skill` checks the fields the docs require.
- **Item 2, the paid command.** One script, one `BudgetedClient`, one ledger
  (`logs/spend/paid-2026-11-19.jsonl`), for both parts. Part 1 uses single-shot (as M6) on
  dev only, so every formulation replays from M6's dev cache and only explanations are paid;
  it writes the rows to `runs/explain-dev/`, and Claude labels them afterwards from a sheet
  without the checker's flags (the protocol says how). Part 2 needs no change to the demo:
  each try has its own cache folder (an unsalted key, a fresh reply), so the chosen try's
  files replay in `src/opt_agent/demo/replies/` as they are; its first five samples per
  candidate are tried in order and the first that shows the loop is kept, every try recorded
  in `logs/demo-fix-step/tries.json` for the label. The traps (minutes against hours, grams
  against kilograms, 40% read as 40 vans) were chosen so that a literal misreading is
  infeasible, which is what sends Claude the conflicting constraints; whether Haiku falls
  into one is the run's question, and if no try does, nothing is chosen. The cap ($0.30) is
  about three times the expected cost: it binds only if replies run far longer than the
  demo examples' did.
- **Item 3, the labels.** Four Claude subagents labeled one batch each from sheets without
  the checker's flags (the protocol's blind step); three raised the same question about
  integer programs, settled for all four before scoring (`explanation_checker.md`, "Labeling
  decisions"). Three of the resulting false claims were re-solved with the project's solver
  and confirmed. Agreement between labelers wasn't measured. The run's cache was seeded with
  all of `runs/dev-1`'s cache, so it was pruned to what the run replays before committing
  (`scripts/explanation_checker.py prune`, which replays every explanation first).
- **The resampling study's build (after the owner's approval with three edits).**
  - **Units:** "verified" is read from the follow-up's own item records: a single-shot item
    holds only a confirmed answer, so a confirmed optimum (status "optimal") is verified. On
    the 121 problems, 359 of the follow-up's 363 single-shot answers were, so the expected
    units are 120 and the power was recomputed on those answers' rates (0.97 as seen, 0.46 if
    weaker; `docs/resampling/power.md`).
  - **Missing answers:** the unit is always a verified answer, so a missing answer anywhere
    differs from it and sets the flag with no special case; in R2's majority only verified
    answers vote, and a problem with no 3 agreeing ones has no majority answer (wrong).
  - **The same settings as the follow-up** are checked from the files, not assumed: for all 121
    problems the study's formulation and baseline requests have the follow-up's sample-0 cache
    keys (`resampling_freeze.requests_differ`, part of `unfinished()` and a test that runs
    where LLM4OR's data is, as in CI's reproduce job).
  - **The runner** has its own six cells rather than `evaluate.py`'s full cross of conditions
    and samples, but each call goes through `evaluate.run_item`, the follow-up's per-item
    code; Amendment 1 is a cell's fourth errored line, after which it isn't retried and the
    analysis reads it as no answer. `followup.read_sealed`/`read_test` are the follow-up's
    readers without its gate, used only behind `resampling_freeze.check()`.
  - **The freeze** was written by Claude because the owner asked for it in chat (the approval
    records that in `approved_by`); it covers every source file, so the tag's parent is the
    approved commit and the tag is the commit that adds `FREEZE.json`, as for the follow-up.
    CLAUDE.md and this file aren't fingerprinted, so updating them keeps the freeze matching.
  - **The freeze commit's own CI run failed** (`4c2105e`, the tag's commit): the coverage
    check, since the new modules' command lines and status paths had no tests and the total
    fell more than a point under the README's badge. Tests added in `a66ec07` (no change to
    any frozen input) brought it back within the point, and CI passes from there on. Nothing
    about the frozen inputs was wrong; `python -m opt_agent.resampling_freeze` verifies the tag.
