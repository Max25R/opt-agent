# How opt-agent works

A ten-minute tour of the code, then the design (moved here from the README on 2026-11-15):
how the solver layer is verified, how the agent works, how the NL4Opt answer key was built,
and where everything lives. Why it's built this way, the options weighed and what each
choice cost are in the decision records, [`docs/adr/`](adr/README.md).

## Read the code in 10 minutes

Six files in `src/opt_agent/`, in this order, follow one problem through the pipeline. Each
opens with a docstring that says what it does and why.

1. [`agent.py`](../src/opt_agent/agent.py): start at `run()`, the whole pipeline in one short
   function, and `Result`, which defines a *confirmed* and a *verified* answer.
2. [`formulate.py`](../src/opt_agent/formulate.py): the prompt, and the structured-output
   request that turns the problem text into a model.
3. [`schema.py`](../src/opt_agent/schema.py): the contract that reply must meet: the API
   guarantees its shape, and the validators check its meaning.
4. [`solver.py`](../src/opt_agent/solver.py): CBC through PuLP, and what its answer must
   survive to count: a feasible point, no improving ray, statuses settled by a second solve.
5. [`verify.py`](../src/opt_agent/verify.py): the checks that need no solver: every
   constraint and the objective by arithmetic, and an LP's optimality certificate.
6. [`self_correct.py`](../src/opt_agent/self_correct.py): what happens when an attempt fails:
   the feedback Claude gets, the revisions that get flagged, and when the loop stops.

Then the evaluation: [`api.py`](../src/opt_agent/api.py) caches every call by its request, so
a run replays with no key; [`evaluate.py`](../src/opt_agent/evaluate.py) records what each
condition answered; and [`scoring.py`](../src/opt_agent/scoring.py) scores it afterwards.

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
   direction along which the objective improves forever), both checked by arithmetic. A
   claimed optimum is overruled by such a ray (`rays.py`), or when the point CBC calls
   optimal breaks the model's own bounds or constraints: then the model is settled as for an
   "infeasible or unbounded" label. "Infeasible" comes from a feasibility solve that both
   solvers must agree on. A time-out is reported as one.

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
- CBC claimed an optimum at an infeasible point of an unbounded LP (x3 = 100 against
  x3 <= 1; `CBC_INFEASIBLE_OPTIMUM_BUG`, found by the CBC-vs-HiGHS property test). A claimed
  optimum's feasibility is now checked before anything else.
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
   changes it, and it isn't excluded (`exclusions.json`: 4 test problems, the 2 used while
   building the agent and the 2 that Amendment 2's rules exclude).

**Who decided what.** Claude (the AI model that wrote this code) wrote every hand review and
most hand integrality labels. The other labels are the owner's or the LLM judges' (each
label's source is recorded in `data/nl4opt/integrality.json`). Claude's work was checked by
the owner on dev, and by LLM judges on test:

- *Dev split:* the owner set the integrality labels for the problems in the dev
  walkthrough, and confirmed (and corrected) the dev reviews, except one that was written
  after the walkthrough. The other dev hand labels are Claude's.
- *Test split:* every review, and every hand label but 48, is Claude's. Two LLM judges from
  different vendors checked them instead of the owner (pre-registration, Amendment 2):
  - **Integrality labels:** they labeled a blind sample and the "says LP" problems, 44 in
    all, and their combined labels replaced Claude's there (source `judge`). Where they
    disagree, either answer is accepted. The other 4 are `either` labels that the owner's
    decision rules for the reviews set (source `owner`).
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
  resampling.py resampling_report.py resampling_freeze.py   # the resampling study (frozen, not run)
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
  static_demo.py              # the demo as a static site (GitHub Pages), built and checked in CI
skills/opt-agent/             # the Agent Skill: SKILL.md, and two scripts needing only PuLP and SciPy
.claude-plugin/               # marketplace.json: the repository as a plugin marketplace for the skill
tests/                        # unit, property, metamorphic, ground-truth and demo tests
Dockerfile                    # the demo image (CI builds and smoke-tests it)
requirements.lock             # exact versions of every package; CI installs from it
```

