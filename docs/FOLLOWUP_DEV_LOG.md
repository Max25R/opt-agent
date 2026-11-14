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
| 2 | (in reserve) | **declared unused** (owner, 2026-11-10): the checklist stays at revision 1 |

**From 2026-11-10 (owner):** while building the follow-up's freeze code, fixing a bug (code
not doing what revision 1 specifies) is allowed and gets an entry here; changing what gets
flagged is not. One so far: see the smoke run of condition 4 below.

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

## Smoke run of condition 4 (2026-11-11; bug-finding only, not a revision)

**Cap: $0.75, set by the owner on 2026-11-11.** `--plan` gave at most 75 paid calls and at
most $0.7056. Run by the owner from their terminal, condition 4 alone, sample 0, all 25 dev
problems, in the pre-registered order:

```bash
OPT_AGENT_LIVE=1 python -m opt_agent.evaluate --split complexlp-dev --all --conditions checklist-revision --sample 0 --out runs/dev-checklist-revision --cap 0.75
python -m opt_agent.followup_report runs/dev-checklist-revision
```

**Result** (`runs/dev-checklist-revision`): 24/25 by the key (82 is the known bad key; see
above), 0 errored pairs, 57 paid calls, $0.1775. Dev results are for finding bugs only; the
checklist stays at revision 1 and nothing was tuned.
- **Revisions:** 7 (100, 118, 119, 135, 137, 142, 144), all kept (each reached a confirmed
  optimum), every one with the same objective as before. All 7 were right before and after:
  0 right to wrong, 0 wrong to right. 82, the one wrong answer, got no flags.
- **Flags** (47; 29 "extra", 14 "coefficient", 4 "objective"): one flag per flagged row, not
  duplicates. 100, 118, 119, 135 and 137 are the known flow-conservation omission (revision 1
  left it). 142 and 144 are a "coefficient" flag per demand row: the text gives `>= d`, the
  model `== d`. Revision 1 flags a stricter row that binds at the optimum, and an equation
  always binds, so this is what revision 1 specifies; changing it would be a revision, and
  revision 2 is declared unused. Sampling decides it: in the first dev run, 142's model wrote
  `>=`, so it didn't show then. These two revisions cost about $0.006 and changed no answer.
- **Unused variables:** one drop with a note (119); it was right.
- **Output tokens:** the largest single call used 12,593 of 16,000 (a checklist call); no call
  stopped at `max_tokens`.
- **Bug fixed** (code not doing what was specified; owner's rule of 2026-11-10):
  `followup_report.py` wrote `NaN` into its JSON for sample agreement with one sample (and
  would have for an empty subset). JSON has no NaN; these are now `null`, and the report is
  written with `allow_nan=False`. Test: `test_one_sample_gives_no_agreement_and_no_nan`.

## Key-format check (2026-11-12, $0; not a revision)

The owner asked how the follow-up keys parse before writing the parsing rule. Neither
split's text, ids or values were shown: `scripts/key_formats.py` prints, per benchmark, how
many keys the old parser (`float`) reads as finite numbers, a shape mask (digit -> 9, letter
-> a) with a count for the rest, and how the new rule (`followup.parse_key`) reads them.

| keys | finite numbers | other shapes | `parse_key` | equal to `float` |
|---|---|---|---|---|
| ComplexLP follow-up test: 86 | 86 | none | 86 optimal | 86 |
| IndustryOR follow-up test: 42 | 42 | none | 42 optimal | 42 |

The 25 ComplexLP dev keys are numbers written as text (`"14.0"`). So no problem is left out
for its key, and the rule changes no key's value. The rule itself is section 4 of the draft
(owner, 2026-11-12).

## Bug fixed while connecting the test split (2026-11-12)

`followup_report.contrast` crashed on a row with no complete problems: an empty list became a
float array, and `~` (not) fails on floats. That happens when every complete problem is
exposed, or when a run stopped before finishing one. The majority arrays are now boolean.
Test: `test_the_report_uses_labels_and_lists_unscorable_keys` (both made-up problems are
exposed, so the primary row is empty).

## Aggregate prompt-length check (2026-11-11, $0; logged 2026-11-13)

For the test run's cost projection, Claude computed the mean and maximum character count of
the problem texts per benchmark. It printed only those four numbers, no text or ids:
ComplexLP follow-up test mean 1,774 (max 3,732), IndustryOR mean 1,365 (max 10,869), against
ComplexLP dev's mean 1,983. The projection (draft section 6) scales IndustryOR by 0.69.

## Key-precision check (2026-11-13, $0; not a revision)

The owner asked whether 1e-4 relative is safe for rounded keys. `scripts/key_formats.py` now
also prints, per benchmark, counts of keys by decimal places as written and, for keys that
aren't whole numbers, by significant figures. No ids or values.

| | ComplexLP (86) | IndustryOR (42) | both (128) |
|---|---|---|---|
| decimal places written: 0 | 8 | 26 | 34 |
| 1 | 77 | 13 | 90 |
| 2 | 1 | 2 | 3 |
| 3+ | 0 | 1 | 1 |
| whole numbers ("14", "14.0") | 84 | 37 | 121 |
| not whole: <= 3 significant figures | 0 | 1 | 1 |
| 4 | 1 | 0 | 1 |
| 5+ | 1 | 4 | 5 |

Two non-whole keys have fewer than 5 significant figures, so 1e-4 alone could fail an exact
answer. The owner's rule (2026-11-13, draft section 4, follow-up only): an optimum is also
right if it rounds to a non-whole key at the key's written decimals; whole-number keys stay
at 1e-4. `followup.right_by` and `followup.written_decimals`; the report counts answers right
only by rounding. On the dev smoke run it changes nothing (every dev key is whole).

## Solver bug fixed before the freeze (2026-11-13; predates the follow-up)

**Found by** the CBC-vs-HiGHS property test (`tests/test_crosscheck.py::test_cbc_and_highs_agree`),
on a random model Hypothesis had saved, during the full-suite run of 2026-11-13. The same
failure reproduces at HEAD (`e213060`), so it predates the follow-up's code; nothing in M7
introduced it. It's a solver fix, not a checklist revision.

**The bug.** For an unbounded LP (`CBC_INFEASIBLE_OPTIMUM_BUG` in `tests/problems.py`: x1 >= 0
with a +1 objective coefficient, in no constraint), CBC (cbcbox 2.929) reports "Optimal",
about 3.05e22, at a point that breaks a bound (x3 = 100 against x3 <= 1). The improving-ray
check certifies rays only from a feasible point, so it couldn't refute the claim, and `solve`
returned it as optimal. HiGHS says unbounded. Downstream it was always loud: the arithmetic
check fails on that point and the solvers disagree, so `Result.confirmed` was False. But
self-correction stopped on "solvers disagree" instead of sending "unbounded" feedback.

**The fix** (`solver._solve`): a claimed optimum whose point fails `verify.feasibility_problems`
(the same check, at the same tolerance, as `check_solution`) is settled like an "infeasible or
unbounded" label: a feasibility solve; no feasible point gives infeasible; a feasible point
and an improving ray certified from it give unbounded; otherwise ERROR (loud), never the
claimed optimum. Since `check_solution` already rejected every such point, the fix can't take
away a confirmed answer; it can only settle one that was loud.

**Tests:** `test_regression_cbc_optimum_at_an_infeasible_point` (known answer: unbounded, the
ray along x1, HiGHS agreeing; it also asserts that CBC's raw claim still shows the bug), the
no-ray case (ERROR), the infeasible-model case (infeasible), and a feasible optimum left
alone. The property test passes.

**Effect on existing results: none.** Every distinct model logged in `runs/test` (274),
`runs/test-perturbed` (241), `runs/dev-1` (92), `runs/dev-perturbed-1` (85),
`runs/dev-checklist` (25) and `runs/dev-checklist-revision` (31) was re-solved locally: in
none is CBC's raw claim an optimum at an infeasible point, so the fix changes no logged solve.
Also checked with the fix in place, all at $0:
- the NL4Opt ground truth and perturbed splits rebuilt byte-identical (`python -m
  opt_agent.ground_truth`, then `python -m opt_agent.perturb`);
- M6: `runs/test/report.json`, `runs/test-perturbed/report.json` and `results/eval.json`
  rebuilt byte-identical (`opt_agent.report` on both runs, `scripts/amendment3.py runs/test`,
  `scripts/eval_json.py`);
- this smoke run: replayed through the fixed pipeline from its cache with a client that
  refuses any call (`scripts/rescore_dev.py`): all 25 pairs give the same answer, revision
  and flags, and `followup_report.json` is unchanged.
