# Handoff (2026-11-15)

Read CLAUDE.md first (rules, budget, gotchas). This file is where things stand.

## Current state
- **Everything is committed and pushed** (`main` at `f57d993` when this was written; tags
  `m6-freeze`, `amendment-3`, `amendment-4`, `amendment-5`, `followup-freeze`).
- **M6 is done and frozen.** Tag `m6-freeze` = `8f522c0`, the commit both test runs ran on.
  Result of record: 264/274 strict per condition (`results/eval.json`). The M6 reports and
  `results/eval.json` still rebuild byte-identical at HEAD (checked 2026-11-13, after the CBC
  fix below).
- **Amendments:** 1 and 2 are in the frozen `docs/PREREGISTRATION.md`; 3, 4 and 5 are in
  `docs/amendments/`, tagged.
- **M7, the follow-up study: done.** On LLM4OR's cleaned ComplexLP (86) and IndustryOR (42),
  128 problems, 3 samples, 4 conditions (baseline, single-shot, self-correction, checklist
  revision), Claude Haiku 5.5.
  - **Pre-registration** `docs/FOLLOWUP_PREREGISTRATION.md`, approved and frozen 2026-11-13
    (`docs/followup/FREEZE.json`, approval at `f2bd2e3`; tag `followup-freeze` = `f36e812`).
  - **Run** `runs/followup-test` (committed, commit `7cfe7bb`): one pass at `f36e812`, clean
    tree, fingerprint equal to the approval's; 1536 answers, 0 errored; $2.7176 on 1252 calls.
  - **Results** (primary: the 121 unexposed problems): H2, single-shot minus baseline,
    +6.34 pp, **detected** on the sign-flip test (Holm p 0.0445, 95% CI 1.4 to 11.6 pp);
    McNemar on majority isn't significant (Holm p 0.24); 1.38 pp of it comes from 8 baseline
    replies cut off at max_tokens (descriptive). H1, checklist revision minus single-shot,
    +0.6 pp, **inconclusive**: no difference larger than 4 pp.
  - **Write-up:** `docs/followup/RESULTS.md` and the README's "Follow-up evaluation" section,
    every number from `results/followup.json` (`scripts/followup_results.py`), checked by
    `tests/test_readme_numbers.py` and `tests/test_followup_results.py`.
  - **Deviations** (`docs/followup/DEVIATIONS.md`): 2, the 5b key-dispute check **wasn't
    performed** (owner, 2026-11-15, for time, before any encoding or judging): no
    corrected-key row, the raw keys are the result of record, and the 15 trigger problems
    are listed by label; whether any are key errors is unknown. 1 (Gemini JSON encodings)
    is superseded by 2. The dispute plan (`review/followup_disputes/README.md`) is marked
    not run; its packets are git-ignored and `scripts/dispute_packets.py` is kept.
  - **Run notes** (`docs/followup/RUN_NOTES.md`): HiGHS's debug print, and where problem text
    is committed.
  - **Dev:** `docs/FOLLOWUP_DEV_LOG.md` (checklist revision 1; revision 2 unused; the smoke
    run; the bug fixes made before the freeze, including CBC's optimum at an infeasible point).
- **Data notice** (`DATA_NOTICE.md`, linked from the README's Sources section and the end of
  `LICENSE`): MIT covers the code only. `runs/` holds problem text and answers from Mamo
  ComplexLP (CC BY-SA 4.0) and ORLM's IndustryOR (CC BY-NC 4.0), as cleaned by LLM4OR at
  `75962df` (no license stated), plus NL4Opt (MIT). History was kept (owner, 2026-11-15):
  rewriting it would break `followup-freeze` and the commit in `FREEZE.json`.
- **Spend:** $3.89 of the $20 credit ($0.98 before the follow-up, $0.1775 for the
  condition-4 dev smoke run, $2.7176 for the test run, $0.0139 for the demo examples'
  replies). About $6.38 of November's $10 limit is left; it resets on December 1.

## Open items
1. **M7 demo** (the rest of milestone 7; needs the owner's go-ahead): FastAPI `POST /solve`,
   one HTML page, a Dockerfile.
2. **M8:** README polish (diagram, results table; its `## Limitations` section is still
   `_TODO._`); one reproduce script (rebuild plus a cache replay, no key; the CLI still needs
   a key even when every call is cached); the audit's docs fixes (`docs/audit/`, section 5);
   repo description and topics.
3. ~~A CI check of the `followup-freeze` tag~~: done 2026-11-15 (`followup_freeze.tag_problems`,
   see "Decisions made without the owner" below).
4. **`amendment-5.md`'s status line** still says "DRAFT ... not tagged", though it is tagged
   `amendment-5` (1cb05ed). Fix only that line, as was done for Amendment 4.
5. **Known and unfixed since M6:** the integrality rule matches ingredient names (see
   CLAUDE.md and `docs/amendments/DEVIATIONS.md`, section 3); `DEV_WALKTHROUGH.md` predates
   the owner's milestone 3 corrections; no Farkas certificate for infeasible LPs.
6. **Optional, exploratory only:** the 5b check could still be run later
   (`review/followup_disputes/README.md`); anything it found would be post hoc, never the
   result of record.

## Gotchas
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
- **README numbers:** the Evaluation section comes from `results/eval.json`, the Follow-up
  evaluation section and `docs/followup/RESULTS.md` from `results/followup.json`. Write
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
- The LLM4OR data is in `data/external/` (git-ignored; `docs/EXTERNAL_DATA.md`), so CI skips
  every test that needs it. `amendment_5` in `eval.json` is copied forward in CI.
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
    no port), and CI's `screenshot` job runs it and keeps a 2x PNG as the `demo-screenshot`
    artifact; either can replace the committed image.
  - Playwright and matplotlib aren't in the lock: they only make pictures, and each script's
    docstring pins its install. The demo page now renders the explanations' **bold** (DOM
    nodes only, no innerHTML).

