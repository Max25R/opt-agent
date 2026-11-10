# Handoff (2026-11-09)

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
- **Spend:** $0.98 of the $20 credit; about $9.29 of November's $10 limit is left.
- **Unpushed:** the last 4 commits on `main` (`git push origin main`).

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

## Open pre-registration decisions (from the dev log)
1. **The unused-variable rule:** keep rejecting (self-correction fixes it with one line) or
   drop unused variables with a note (that changes answers). On dev it made 2 of 25 replies
   unusable (118, 137).
2. **Answer keys:** whether and how to check keys before scoring (the dev key for 82 is
   wrong; brute force where a problem is small enough).
3. **Seen problems:** keep the 7 seen before the split (all follow-up test) or leave them out.
4. Also to fix in the pre-registration: the 4th condition's trigger rule, how 3 samples
   aggregate per problem, the 1e-4 tolerance for external keys, and whether revision 2 is
   used.

## Next steps
1. **Follow-up pre-registration** (a new draft, then the owner's approval and a freeze tag):
   4 conditions x 3 samples on the 128 follow-up test problems (86 ComplexLP + 42
   IndustryOR): baseline, single-shot, self-correction, and checklist-triggered revision.
   That last one is new code (revise when the checklist flags something, with the flags as
   feedback); build it and run it on dev first. Projected cost from dev actuals, scaled by
   length: about $3.29, or $4.94 with a 1.5x margin.
2. **M7 demo:** FastAPI `POST /solve`, one HTML page and a Dockerfile, returning the answer
   with its checks (confirmed, low confidence, checklist flags).
3. **M8:** README rewrite (result first, the lenient and sensitivity rows, the six key errors
   explained, a diagram, no TODOs); one reproduce script (rebuild plus a cache replay, with no
   key); the audit's docs fixes (section 5).
