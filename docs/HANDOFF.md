# Handoff (2026-11-18, end of session)

Read CLAUDE.md first (rules, budget, gotchas), then this file: where things stand, every
open item, and the environment. A new session needs nothing else; the full record of
decisions is `docs/HISTORY.md`.

## Start here (a new session)
1. `source .venv/bin/activate` (`python` isn't on the path without it), `unset
   ANTHROPIC_API_KEY`, then `git status` and `git log --oneline -5`: the tree should be clean
   at the last commit on `main`, pushed, with CI green (its status: see Environment).
2. Read "Open items" below. Nothing is in progress; every open item is optional or the
   owner's.
3. Before committing: `ruff check . && ruff format --check .`, `python -m mypy`, and
   `HYPOTHESIS_PROFILE=ci python -m pytest` (about 3 minutes; with all the data here, nothing
   skips). After a change under `src/opt_agent/`, `python scripts/reproduce.py` (about 4
   minutes, no key) must still say every answer replays and all 6 files match.

## Current state
- **Everything is committed and pushed** (`main`, 2026-11-18; tags `m6-freeze`,
  `amendment-3`, `amendment-4`, `amendment-5`, `followup-freeze`), and CI's jobs (test on
  3.12 and 3.13, types, reproduce, demo-image, pictures, static-demo, deploy-pages) pass on
  the last commit. No API call was made after 2026-11-15.
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
- **Spend:** $3.89 of the $20 credit ($0.98 before the follow-up, $0.1775 for the
  condition-4 dev smoke run, $2.7176 for the test run, $0.0139 for the demo examples'
  replies). About $6.38 of November's $10 limit is left; it resets on December 1.

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
   2026-11-18) and an index (`README.md`); add a new one for any new design decision.
13. ~~Turn on Pages~~: done 2026-11-19 by the owner (Settings > Pages > Source: GitHub
   Actions), then a manual CI run on `365d23e` deployed it. Checked through the public API
   and a browser: every job of that run passed, `deploy-pages` included, and
   `https://max25r.github.io/opt-agent/` serves the static demo, stamped `365d23e`, all four
   examples verified and matching. Every push to `main` now redeploys it. (The public
   `GET /repos/.../pages` answers 404 without a token, so it can't show whether Pages is on;
   CI's check sends the job's token.)
14. **Proposed next (2026-11-18, item 5 of the polish list; none started, each the owner's
   call):**
   1. A person fills in the dispute spot-check (item 9): 1-2 hours, $0. An LLM judge flagged
      the key on 13 of the 35 follow-up problems with a wrong answer, not verified by a
      person; 10 verdicts are the cheapest real evidence of how many are key errors.
   2. A demo example whose first model fails, so the static page shows the fix step
      (ADR-0007's open action item): about 2 hours, plus a paid caching run of a few cents
      in the owner's terminal (`scripts/cache_examples.py --plan` first).
   3. Sample agreement as a silent-failure signal, on the follow-up's 3 committed samples per
      problem, with the rule committed before its one run as for the silent detector: about
      half a day, $0, exploratory (ADR-0001's open question).
   4. The explanation checker evaluated on dev's verified answers (ADR-0004's revisit), so
      "every number traced to the solver" becomes a measured result: about a day, a few
      cents of dev calls in the owner's terminal.
   5. A second model under its own pre-registration and cap (ADR-0006's model ladder): 2-3
      days plus a paid run sized by `evaluate --plan` at the current prices; the budget is
      the owner's call.
15. **The resampling study: drafted, not approved, not frozen, not run** (the owner said yes
   to drafting it, 2026-11-19): `docs/RESAMPLING_PREREGISTRATION.md`, with its power in
   `docs/resampling/power.md` (`scripts/resampling_power.py`, seeded). Fresh samples (single-shot
   3 to 7, baseline 3) on the follow-up's 121 unexposed problems, one unit per problem,
   one-sided Fisher exact test; about $1.44, hard cap $3.00. Before any call: the owner's
   approval, a runner and an analysis script with tests, and the owner's freeze
   (`docs/resampling/FREEZE.json`, tag `resampling-freeze`).

## Environment (read before running anything)
- **The owner's Mac is Apple Silicon** (`uname -m` says `arm64`), where both studies ran and
  where CI's `reproduce` job runs (`macos-15`); CBC comes from `cbcbox` 2.929 because later
  builds crash there (CLAUDE.md).
- **No `gh`.** Read CI from the public GitHub API with `curl` and `jq`:
  `api.github.com/repos/Max25R/opt-agent/actions/runs?head_sha=SHA` for the run, then
  `.../actions/runs/RUN_ID/jobs` for each job's name, status and conclusion. In the sandbox a
  command needs the host listed (`api.github.com`; `github.com` for `git push`).
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
- **Both studies are frozen at their tags, not at HEAD.** Any change under `src/opt_agent/`
  (and to the frozen docs, the lock, `split.json` or the LLM4OR files) makes
  `python -m opt_agent.freeze` and `python -m opt_agent.followup_freeze` report a mismatch.
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
  `results/followup.json`, and the rest of the README is checked against both. Write
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
