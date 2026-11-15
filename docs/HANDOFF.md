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
- **Spend:** $3.88 of the $20 credit ($0.98 before the follow-up, $0.1775 for the
  condition-4 dev smoke run, $2.7176 for the test run). About $6.39 of November's $10 limit
  is left; it resets on December 1.

## Open items
1. **M7 demo** (the rest of milestone 7; needs the owner's go-ahead): FastAPI `POST /solve`,
   one HTML page, a Dockerfile.
2. **M8:** README polish (diagram, results table; its `## Limitations` section is still
   `_TODO._`); one reproduce script (rebuild plus a cache replay, no key; the CLI still needs
   a key even when every call is cached); the audit's docs fixes (`docs/audit/`, section 5);
   repo description and topics.
3. **A CI check of the `followup-freeze` tag**, like M6's `freeze.tag_problems` (not built).
   Until then, nothing in CI shows the follow-up's frozen inputs are still at the tag.
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
  (the build) stop working at HEAD, and `test_rebuilding_gives_the_committed_json` skips.
  Rendering still works (`scripts/followup_results.py --render`, from the committed JSON).
  To rebuild, check out the tag (`git worktree add ../opt-agent-followup followup-freeze`,
  in the owner's terminal: the sandbox can't add worktrees) and link `data/external/` into it.
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
