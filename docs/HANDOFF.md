# Handoff (2026-11-11)

Read CLAUDE.md first (rules, budget, gotchas). This file is where things stand.

## Current state
- **M6 is done and frozen.** Tag `m6-freeze` = `8f522c0`, the commit both test runs ran on
  (`docs/FREEZE.json` approves its parent `3b39a55`). Result of record: 264/274 strict per
  condition (`results/eval.json`). The rebuild from the tag was byte-identical on 2026-11-09.
- **Amendments:** 1 and 2 are in the frozen `docs/PREREGISTRATION.md`; 3, 4 and 5 are in
  `docs/amendments/`, tagged `amendment-3` (ad04f1e), `amendment-4` (5f10814) and
  `amendment-5` (1cb05ed). `amendment-5.md`'s status line still says "not tagged": fix only
  that line, as was done for 4.
- **Audit:** `docs/audit/2026-11-review.md`. The integrality-rule bug timeline is in
  `docs/amendments/DEVIATIONS.md`, section 3.
- **M7 part 1 (robustness), done:** integer bounds rounded inward in both solvers;
  `PulpSolverError` is a loud error; change flags compare constraints by structure; the cache
  key leaves out the SDK-built schema (M6's caches are found through `Cache`'s index); a
  report-only low-confidence flag (`--estimate`); a sample index (`Cache(dir, sample=n)`,
  `evaluate --sample n`; sample 0 replays every existing cache).
- **Formulation checklist (report-only, `--checklist`), built, with revision 1 applied**
  (`docs/FOLLOWUP_DEV_LOG.md`):
  - dev run `runs/dev-checklist`: 22/25 by the key, 23/25 truly right, $0.19;
  - its $0 re-score `runs/dev-checklist-rev1`: checklist flags on 3 of 23 truly right answers,
    low confidence on 1;
  - mutation recall ($0, `scripts/mutation_recall.py`): 173/178 (97%; 94-99%) for either
    check. It's an upper bound, since the checks were made for the correct models.
- **Follow-up pre-registration: drafted, not approved** (`docs/FOLLOWUP_PREREGISTRATION.md`).
  The owner's decisions of 2026-11-10 and 2026-11-11 are in its section 0. Power:
  `docs/followup/power.md` (`scripts/followup_power.py`, seed 20261109): H2 powered for about
  15 pp (independent discordance), H1 for about 8 pp (shared samples: conditions 2-4 share
  every sample's first reply). Dev revision 2 is declared unused; the checklist stays at revision 1.
- **Built for the freeze (uncommitted until the owner reviews it), no API calls:**
  - condition 4, `checklist-revision` (`agent.run(checklist_revision=True)`,
    `self_correct.revise_once`, `feedback.for_checklist`): single-shot, then one revision when
    a confirmed optimum gets checklist flags; kept only if it's a confirmed optimum. An API
    error in its checklist or revision call makes the pair errored (Amendment 1);
  - unused variables dropped with a note (`schema.drop_unused`, `formulate.parse_with_drops`,
    `Formulation.dropped`, `Item.dropped`, the attempt log's `dropped`);
  - the run protocol: follow-up splits in hash order (`followup.in_run_order`), several
    samples in one directory under one cap (`evaluate --sample 0 1 2`), every sample and
    condition of a problem before the next;
  - conditions 2, 3 and 4 share their first reply per problem and sample (mocked test,
    `tests/test_shared_first_reply.py`);
  - `stats.sign_flip_exact` (exact, brute-force tested); the analysis,
    `src/opt_agent/followup_report.py`, tested on synthetic answers.
- **Spend:** $0.98 of the $20 credit; about $9.29 of November's $10 limit is left.
- **Unpushed:** the last 4 commits on `main` (`git push origin main`), plus the uncommitted
  follow-up work above.

## Gotchas
- `runs/` is git-ignored: commit a run directory with `git add -f`.
- `.env` is read only with `OPT_AGENT_LIVE=1`, so unsetting `ANTHROPIC_API_KEY` guarantees
  no spend. Paid runs happen in the owner's terminal (the sandbox breaks Python's TLS); give
  the commands and the `--plan` cost first.
- **Follow-up test is sealed** until its pre-registration is frozen. `followup.load` raises
  `Sealed`; never read a test problem's text or answer. Problems seen before the split are
  listed in `docs/FOLLOWUP_SPLIT.md` (generated, and a test compares its bytes, so don't
  edit it by hand). The data is in `data/external/` (git-ignored; `docs/EXTERNAL_DATA.md`).
- **Dev tuning:** every dev change gets an entry in `docs/FOLLOWUP_DEV_LOG.md`. The budget is
  2 revisions (1 used). Re-score dev at $0 with `scripts/rescore_dev.py`.
- The checklist's prompt was designed after seeing the M6 test failures: any M6 number from
  it is exploratory and never goes in `results/eval.json` or the README.
- `amendment_5` in `eval.json` is copied forward in CI (no LLM4OR data there);
  `tests/test_amendment5.py` recomputes it only where the data exists.
- M6 rebuild order: `opt_agent.report`, then `scripts/amendment3.py`, then
  `scripts/eval_json.py`. CI checks the freeze against the tag (`fetch-depth: 0`), so push
  tags with commits.

## Next steps
1. **Dev smoke run of condition 4** (owner's terminal; cap $0.75, the owner's, 2026-11-11):
   the commands are in `docs/FOLLOWUP_DEV_LOG.md`. Then `python -m opt_agent.followup_report
   runs/dev-checklist-revision` and look for bugs (not tuning). A fix is allowed only where the
   code doesn't do what revision 1 specifies, logged in the dev log.
2. **The follow-up freeze tool: built** (`src/opt_agent/followup_freeze.py`; `approve` is the
   owner's step). `followup.load_sealed` reads a test split only after `check()` passes.
   The test split is wired into `evaluate` (`--split followup-test`, labels as ids), keys are
   parsed by format alone (`followup.parse_key`; all 128 are numbers, checked in aggregate),
   and a `max_tokens` reply is scored, never re-run (draft sections 0, 4 and 6). Since
   2026-11-13: a rounding clause for non-whole keys, and the 5b judge prompt
   (`docs/followup/judge_prompt.md`, frozen).
3. **Approval, freeze and tag** by the owner; then the test run (4 conditions x 3 samples,
   128 problems, `--cap 6.00`).
4. **M7 demo:** FastAPI `POST /solve`, one HTML page and a Dockerfile.
5. **M8:** README rewrite; one reproduce script (rebuild plus a cache replay, no key); the
   audit's docs fixes (section 5).
