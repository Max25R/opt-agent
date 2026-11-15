# Follow-up test run: notes

Checks on `runs/followup-test` made after the run, with no API calls. They change no result.

## HiGHS's "transformNewIntegerFeasibleSolution" message (2026-11-15)

The run printed `HighsMipSolverData::transformNewIntegerFeasibleSolution tmpSolver.run();`
about 40 times. It comes from HiGHS's MIP solver (through SciPy 1.18.1's `milp`), from the
routine that, by its name, turns a new integer-feasible solution back into one of the
original problem and runs a second solver on it. HiGHS's source wasn't read for this note,
so what follows rests on what the solves give, not on what the message means. It is printed
to C's stdout, not returned, so the run's logs don't hold it.

**Which solves.** Every distinct model in the run's attempt log (412) was solved again with
HiGHS, with its C-level output captured per solve. 8 models print it, 14 times in all; each
was solved 3 times in the run (one per solver condition), so 42 prints, the "about 40".
All 8 are MIPs, from 3 problems: `complexlp:143`, `complexlp:158` and `complexlp:167`.

**Did it change a verification result? No.** For each of the 8:
- HiGHS and CBC reach the same status and objective (`verify.same_answer`);
- both solutions pass the arithmetic checks (`verify.check_solution`: every bound, row and
  integrality, and the objective recomputed);
- the re-solve gives exactly what the run logged (status and objective, CBC and HiGHS).

So whatever that path does, the solution it returned agrees with CBC's and checks out by
arithmetic, and no verification result depends on it. As far as these checks can tell, the
message is harmless logging.

## Problem text in the committed runs (2026-11-15)

**The scan** (no API calls; paths and counts printed, never text). For each of the 153 LLM4OR
problems (111 ComplexLP, 42 IndustryOR), a 60-character stretch of its text found in no other
problem's text was searched for in every blob of the git history (152 problems have such a
stretch). Found, at HEAD only:
- all 128 follow-up test problems' text in `runs/followup-test/` (`cache/`, `attempts.jsonl`);
- all 25 ComplexLP dev problems' text in `runs/dev-checklist/`, `runs/dev-checklist-revision/`
  and `runs/dev-checklist-rev1/attempts.jsonl`.

Every API request holds its problem's text, so this is by construction. No data file, doc,
test or earlier version holds it. Smaller pieces: `results.jsonl`'s checklist flags quote
short phrases, `followup_report.json` gives the keys of the 15 disputed problems, and the dev
log cites one dev key.

**Licenses:** ComplexLP (Mamo) is CC BY-SA 4.0, IndustryOR (ORLM's dataset card) CC BY-NC 4.0,
and LLM4OR's cleaned versions state none.

**Decision (owner, 2026-11-15): keep the history and add a notice.** Rewriting history
would break the `followup-freeze` tag and the commit recorded in `docs/followup/FREEZE.json`.
[`DATA_NOTICE.md`](../../DATA_NOTICE.md) says the MIT license covers the code only, gives the
attribution and terms for each source (IndustryOR-derived material is non-commercial only;
ComplexLP-derived material is ShareAlike), and offers removal on request. The README's
Sources section and `LICENSE` point to it.
