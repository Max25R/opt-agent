# Follow-up dev log

Every change made on the follow-up dev split (`docs/FOLLOWUP_SPLIT.md`), and every
measurement it rests on, gets an entry here, in order. The **dev-tuning budget is 2
revisions in all**, prompt or diff logic. Nothing here may use a follow-up test problem's text
or answer: those stay sealed until the follow-up pre-registration is frozen.

The formulation checklist's prompt was designed after seeing the M6 test failures, so it's
tuned here, on dev, and any number it gives on M6 test is exploratory ("prompt designed after
seeing these failures") and stays out of `results/eval.json` and the README's results.

## Budget

| revision | what | status |
|---|---|---|
| 1 | checklist and low-confidence comparison logic | applied 2026-11-09; see below |
| 2 | (in reserve) | unused |

## Revision 1 (applied 2026-11-09): comparison logic only, no prompt change

**Evidence.** `runs/dev-checklist` (commit `0e4a193`): the 25 ComplexLP dev problems,
single-shot with `--estimate --checklist`; 73 paid calls, $0.19; 22 of 25 right by the key.
Diagnosed from the cached replies with local solves only ($0).
- **Checklist:** flags on 17 of the 22 answers scored right, up to 40 a problem, and on 82
  (right; see below), so 18 of the 23 truly right answers. Almost none were errors:
  - binary upper bounds (0 <= x <= 1 on integer variables): 112 "extra" flags;
  - rows that use variables no requirement uses, i.e. modeling devices: subtour-elimination
    rows with position variables (74, 82), linked capacity rows `sum(x) - cap * open <= 0`
    (165), stock-balance rows (41): 49 "extra";
  - requirements the model's rows imply (165's `sum(x) <= 814` follows from the linked row
    and `open <= 1`): 18 "missing";
  - "=" against ">=" on demand rows, which the model's optimum satisfies anyway: 34
    "coefficient";
  - integrality on subtour positions, which can be continuous: 4;
  - flow conservation at intermediate nodes, which the checklist doesn't list (100, 119,
    135), and one objective equal only through conservation (135): real checklist
    omissions, 17 "extra" and 1 "objective".
- **Low confidence:** on 5 answers, all right. On 19, 20, 30 and 39 the estimate equals the
  model's LP relaxation (it ignored integrality); on 142 it is an arithmetic slip (469286
  against 469200). It missed nothing: see 82.

**The changes**, all in the comparison, so they're re-scored from the cached replies at $0:
1. **Binary domain:** 0 <= x <= 1 on an integer variable is its domain, not a row, so it is
   never "extra".
2. **Auxiliary variables:** a row that uses a variable no requirement uses is a modeling
   device (subtour elimination, linking): noted, never "extra". Integrality isn't checked
   for such a variable.
3. **Implication, both ways** (local LP solves): a model row the checklist's requirements
   imply isn't "extra"; a requirement the model's rows imply isn't "missing" or "coefficient".
4. **Answer relevance:** a requirement the model's optimum satisfies isn't flagged (adding a
   constraint the optimum already meets can't change the answer); an "extra" row that doesn't
   bind at the optimum isn't flagged (exact for an LP, a heuristic for a MIP).
5. **Low confidence:** an estimate equal to the LP relaxation of an integer model is an
   integrality-only difference, left to the checklist's integrality check: a note, not a flag.

**Expected on dev** (simulated before applying; in-sample, so optimistic): checklist flags on
3 of the 23 truly right answers (was 18), 18 flags in all (was 235); low confidence on 1 (was
5). Left as they are: the flow-conservation omissions in 100, 119 and 135 (a prompt line would
be revision 2).

**Applied** in `checklist.review` (rules 1 to 4; it now takes the model's optimum) and
`agent.confidence` (rule 5), each rule with its tests first (`tests/test_checklist_rev1.py`).
One refinement while applying rule 3, found by an existing test: a coefficient pair is judged
both ways. It's flagged if the model is looser (the requirement isn't implied and the optimum
violates it) or stricter (the model's row isn't implied by the requirements, uses no
auxiliary variable, and binds at the optimum). Implying the requirement alone would have
hidden a stricter wrong coefficient (`8000p + 200t >= 1e6` for `8000p + 2000t >= 1e6`). On
dev every coefficient pair was the looser kind, so the expected numbers didn't move.

**Re-scored at $0** (`scripts/rescore_dev.py runs/dev-checklist runs/dev-checklist-rev1`):
every pair replayed through the pipeline from the run's cache, with a client that refuses any
call. Every answer, cost and estimate is the same, and nothing was paid. The result is
exactly the simulation's:
- checklist flags on 3 of the 23 truly right answers (100, 119, 135: the flow conservation the
  checklist doesn't list), 18 flags (17 "extra", 1 "objective");
- low confidence on 1 (142, the estimate's arithmetic slip).

**Also found on dev:**
- **The key for 82 is wrong.** It's a 5-city tour with symmetric costs given in the text;
  brute force over all 24 tours gives a minimum of 212, the model's (and the estimate's)
  answer, and no tour costs 199, the key. Scored as given (22/25); 23 of 25 are right.
- **87 is right by luck.** Its model has degree constraints but no subtour elimination, and
  its optimum happens to be one tour. The checklist noticed (its "can't express" note asks for
  ordering variables), but a note never flags.

## Measurement: mutation recall after revision 1 (2026-11-09, $0; not a revision)

`scripts/mutation_recall.py` (seed 20261109, up to 3 mutants of each type per model): the 22
dev models scored right, each broken in small known ways, against the run's cached checklist
and estimate for that problem, with local solves only. Types: drop one constraint, flip one
inequality, scale one coefficient by 2 or 0.5, move one non-zero right-hand side by 20%, make
one integer variable continuous, add one invented `x_i >= x_j`. A mutant counts only if it
changes the optimum. **Caught** means the check says something about the mutant it didn't
say about the original (a new checklist flag, or low confidence the original didn't have), so
the original's false positives don't count. Result: `runs/dev-checklist-rev1/mutation_recall.json`.

| mutation | n | checklist | low confidence | either |
|---|---|---|---|---|
| drop | 37 | 35/37 (95%; 82-99%) | 34/37 (92%; 79-97%) | 37/37 (100%; 91-100%) |
| flip | 49 | 45/49 (92%; 81-97%) | 45/49 (92%; 81-97%) | 48/49 (98%; 89-100%) |
| scale | 14 | 13/14 (93%; 69-99%) | 13/14 (93%; 69-99%) | 14/14 (100%; 78-100%) |
| rhs | 45 | 38/45 (84%; 71-92%) | 42/45 (93%; 82-98%) | 45/45 (100%; 92-100%) |
| continuous | 21 | 14/21 (67%; 45-83%) | 13/21 (62%; 41-79%) | 17/21 (81%; 60-92%) |
| invent | 12 | 12/12 (100%; 76-100%) | 11/12 (92%; 65-99%) | 12/12 (100%; 76-100%) |
| **all** | **178** | **157/178 (88%; 83-92%)** | **158/178 (89%; 83-93%)** | **173/178 (97%; 94-99%)** |

95% Wilson intervals. **Discarded** (undetectable by design, or not a model): 356 generated;
167 didn't change the optimum (scale 52, invent 54, continuous 33, drop 17, rhs 9, flip 2), 11
the schema rejects (a dropped row was a variable's only one), 0 the solver couldn't solve.

**What this does and doesn't show.** It's an upper bound on recall for real errors. Each
mutant is judged against a checklist and an estimate made for the *correct* model, so both are
independent of the mutation. A real error comes from Claude's own reading of the text, and the
checklist and the estimate are Claude's too, so they can share it: on dev, the estimate shared
the model's answer on 82 (there the key was wrong), and on M6 test (exploratory) the estimate
caught 3 of single-shot's 4 real failures. The weakest type is integrality (81% for either),
since an auxiliary variable's kind isn't checked (rule 2) and a continuous mutant can match
the estimate's own integrality slip. In-sample on dev; no revision was made from it.

## Pre-registration decisions (for the follow-up, not dev tuning)

- **The unused-variable rule.** `schema.py` rejects a model with a variable that has no
  nonzero coefficient. On dev it made 2 of 25 replies unusable (118, 137: an unused arc in a
  network problem), and both direct estimates were right. Keep it (and let self-correction fix
  it: the feedback is one line), or drop unused variables with a note: it changes answers, so
  the pre-registration decides, not dev tuning.
- **Answer keys.** The dev key for 82 is wrong. Whether, and how, the follow-up checks keys
  before scoring (for example, brute force where a problem is small enough) is decided before
  the test split is opened.
- **The seen problems** listed in `docs/FOLLOWUP_SPLIT.md`: keep or leave out of scoring.
