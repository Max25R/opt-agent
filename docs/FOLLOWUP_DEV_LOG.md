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
| 1 | checklist and low-confidence comparison logic | proposed 2026-11-09; see below |
| 2 | (in reserve) | unused |

## Revision 1 (proposed 2026-11-09): comparison logic only, no prompt change

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

**Also found on dev:**
- **The key for 82 is wrong.** It's a 5-city tour with symmetric costs given in the text;
  brute force over all 24 tours gives a minimum of 212, the model's (and the estimate's)
  answer, and no tour costs 199, the key. Scored as given (22/25); 23 of 25 are right.
- **87 is right by luck.** Its model has degree constraints but no subtour elimination, and
  its optimum happens to be one tour. The checklist noticed (its "can't express" note asks for
  ordering variables), but a note never flags.

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
