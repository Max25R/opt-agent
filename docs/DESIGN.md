# How opt-agent works

The design, moved here from the README on 2026-11-15: how the solver layer is verified,
how the agent works, how the NL4Opt answer key was built, and where everything lives.

## How the solver layer is verified

The solver's own word isn't trusted. Every solve in the pipeline is checked three ways
at run time:

1. **Plain arithmetic** (`verify.py`): bounds, integrality, every constraint, and the
   objective, without any solver. For an LP it also checks optimality itself: CBC's own
   duals must form a certificate (the right signs, reduced costs that only push against
   finite bounds, and zero duality gap).
2. **A second solver:** CBC (via PuLP) and HiGHS (via SciPy, no PuLP) must agree on the
   status and the optimal objective. When they don't, no answer is reported.
3. **Certified statuses:** "unbounded" needs a feasible point and an improving ray (a
   direction along which the objective improves forever), both checked by arithmetic, and
   a claimed optimum is overruled only by such a ray (`rays.py`). "Infeasible" comes from
   a feasibility solve that both solvers must agree on. A time-out is reported as one.

What run-time arithmetic doesn't prove: that a MIP's optimum is optimal, and that an
infeasible model is infeasible (there's no Farkas certificate yet). Those rest on the
two solvers agreeing.

The test suite adds three more kinds of evidence:

4. **Known answers:** textbook problems (Wyndor Glass, Reddy Mikks) and hand-solved ones,
   including shadow prices checked against finite differences.
5. **Random problems:** Hypothesis generates LPs and MIPs; CBC and HiGHS must agree, and
   both must pass the run-time checks.
6. **Metamorphic relations:** scaling the objective, flipping min/max, adding a redundant
   constraint, or reordering everything must change the answer in a known way.

Problems these checks found, each with a regression test:

- PuLP 4 returns max-problem duals with flipped signs.
- CBC mislabels some unbounded problems as infeasible, and some infeasible ones as
  unbounded. Statuses are decided by a feasibility solve, and "unbounded" also needs a
  certified ray.
- CBC's integer preprocessing returned a wrong "optimal" answer on a 3-variable MIP.
  Preprocessing is now off.
- CBC can't always prove integer infeasibility over unbounded integer variables. It hits
  its time limit and reports `timeout` rather than guessing.
- With free variables, CBC (on an LP) and HiGHS (on a MIP) each claimed "optimal" for an
  unbounded model, but only in one variable order. Found by the reordering test; fixed by
  the improving-ray check, not by changing solver settings (turning off CBC's scaling
  caused new false optima).
- HiGHS returned a fractional value (2.5) for an integer variable with a fractional bound,
  which made the cross-check report a false disagreement (found by the audit). Both solvers
  now get integer bounds rounded inward, and an integer variable with no whole number in its
  bounds is infeasible by arithmetic.

## How the agent works

1. **Formulate:** Claude turns the problem text into our `LPModel` through structured
   output. The API guarantees JSON with the schema's shape, and `schema.py` then checks
   the meaning (declared variables, sane bounds). A failure becomes a readable error.
2. **Self-correct:** if the reply is unusable, or the model is infeasible or unbounded
   (by both solvers' verdict), Claude gets the error back and revises (3 attempts at
   most). For an infeasible model the feedback names the conflicting constraints (an
   irreducible infeasible subset), and it warns against dropping requirements, because
   some problems are infeasible as written. The loop stops without revising when Claude
   returns the same model, refuses, or when the failure isn't Claude's: the solvers
   disagree, one times out, or the API call fails (then the problem counts as failed).
   Revisions that delete or loosen a constraint (its right-hand side or coefficients), flip
   a constraint's direction, change an equation at all, loosen a bound, relax integrality,
   remove a variable, drop one from the objective or negate its coefficient there, or flip
   the objective are flagged. Constraints are compared by structure, so a renamed, reordered
   or rewritten row isn't a change. Every attempt is logged as one JSONL line.
3. **Solve and verify** with both solvers and the checks above. An answer is *confirmed*
   when they agree and the checks pass (for any status), and *verified* when it's also an
   optimum. This is about the solution of Claude's model, not whether the model matches
   the text; that's what the evaluation is for.
4. **Explain** verified answers only, from solver facts: the values, the objective, which
   constraints bind, the slack, and shadow prices. Every number in the explanation must be
   a correct rounding of a fact or an input, or it's flagged. That checks where a number
   comes from, not whether the sentence is true: "10 trips move 1,000 fish" passes when 10
   and 1,000 are both facts. A refused, cut-off or empty explanation is flagged too.
5. **Low confidence** (optional, `--estimate`: one more call): Claude also answers directly,
   with no solver, and a confirmed answer that disagrees with that estimate is marked low
   confidence. Verification can't see a wrong model; a disagreeing direct answer is a cheap
   sign of one. It changes no answer, check or revision.

## Ground truth

NL4Opt's test set has human-annotated formulations but no answers. Rather than borrow a
third-party answer key, `ground_truth.py` builds one from the raw annotations:

1. **Convert** each annotation to our schema (`nl4opt.py`). The semantics follow the
   official baseline's converter, except in two places where that code is mathematically
   wrong; the competition never solved the models, so its bugs went unnoticed.
2. **Reject, never repair** annotations that contradict themselves or the text: one
   variable annotated twice, empty terms, or an operator that contradicts the wording
   ("more than" annotated as <=). Mentions resolve by the variable name they contain, so a
   wrong `order_mapping` is overridden, with a note.
3. **Solve twice, then pick:** NL4Opt doesn't say which variables are integers, so every
   problem is solved as an LP and as an all-integer program, each cross-checked with
   HiGHS and plain arithmetic. A per-problem integrality label picks the answer. Wherever
   the choice changes the answer the label is a hand label (`data/nl4opt/integrality.json`),
   elsewhere a rule sets it.
4. **Accept strict wording either way:** the annotation scheme has no strict operators, so
   "more than" is annotated as >=. For integer problems the answer with that wording read
   strictly (x > y as x >= y + 1) is stored too, and either is accepted (`strict.py`).
5. **Review by hand** every problem with no optimum, a do-nothing optimum, an unlisted
   variable, an overridden `order_mapping`, or a disagreement with
   [ORLM's](https://huggingface.co/datasets/CardinalOperations/NL4OPT) GPT-4-made answers
   (`data/nl4opt/reviews.json`).
6. **Score only what's trusted:** a problem is scorable if it converted, its answer is
   confirmed by HiGHS and the arithmetic checks, no annotation error found in review
   changes it, and it wasn't used while building the agent (`exclusions.json`).

**Who decided what.** Claude (the AI model that wrote this code) wrote every hand review and
most hand labels. The owner decided the rest. Claude's work was checked by the owner on dev,
and by LLM judges on test:

- *Dev split:* the owner set the integrality labels for the problems in the dev
  walkthrough, and confirmed (and corrected) the dev reviews, except one that was written
  after the walkthrough. The other dev hand labels are Claude's.
- *Test split:* every hand label and every review is Claude's. Two LLM judges from
  different vendors checked them instead of the owner (pre-registration, Amendment 2):
  - **Integrality labels:** they labeled a blind sample and the "says LP" problems. Where
    they disagree, either answer is accepted.
  - **Reviews:** they judged the reviews that an external cross-check against
    ORLMBenchmark couldn't cover. Accuracy is also reported without the reviews they
    disputed, and the hard cases they didn't confirm are excluded.

  All of this was settled under the rules in
  [`docs/PREREGISTRATION.md`](PREREGISTRATION.md), which was approved and frozen
  (`docs/FREEZE.json`) before any test run.

Every count, including who labeled and confirmed what, lives in the generated
[`data/nl4opt/ground_truth/REPORT.md`](../data/nl4opt/ground_truth/REPORT.md).

## Project structure

```
src/opt_agent/
  schema.py solution.py       # the LP/MIP schema (the contract between Claude and the solver)
  solver.py highs.py          # CBC through PuLP, and HiGHS through SciPy (no PuLP)
  verify.py rays.py           # solver-free checks, LP duality certificates, certified rays
  api.py budget.py pricing.py # every Claude call: one request dict, retries, cache, dollar cap
  formulate.py self_correct.py feedback.py changes.py explain.py agent.py   # the pipeline
  baseline.py checklist.py    # the no-solver baseline, the formulation checklist
  nl4opt.py ground_truth.py integrality.py strict.py perturb.py orlm.py      # NL4Opt's key
  evaluate.py report.py scoring.py run_results.py stats.py                  # milestone 6
  followup.py followup_report.py                                            # the follow-up
  freeze.py followup_freeze.py frozen.py   # the freezes, checked at their tags; frozen code
  packets.py taxonomy.py blind_grading.py external_check.py                 # hand checks
  demo/                       # the web demo: app, page, examples and their cached replies
data/nl4opt/                  # the committed ground truth, reviews, labels, exclusions
data/followup/split.json      # the follow-up's dev/test split (the data itself isn't committed)
docs/                         # pre-registrations, amendments, deviations, write-ups, audit
review/                       # hand-check packets, the judges' replies, the filled-in sheets
runs/                         # the committed test runs: results, logs, cached replies
results/                      # eval.json and followup.json: every reported number
scripts/
  reproduce.py replay_run.py fetch_llm4or.py   # rebuild every number from the tags, no key
  eval_json.py amendment3.py amendment4.py amendment5.py followup_results.py
  cache_examples.py demo_smoke.py screenshot.py   # the demo's replies, smoke test, picture
tests/                        # unit, property, metamorphic, ground-truth and demo tests
Dockerfile                    # the demo image (CI builds and smoke-tests it)
requirements.lock             # exact versions of every package; CI installs from it
```

