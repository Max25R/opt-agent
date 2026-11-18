# Failure types (exploratory, post hoc)

**Status.** The taxonomy and the rules below were fixed on 2026-11-17 and committed before any
wrong answer was examined; the classification, counts and figure come after that commit (see
`git log -- docs/analysis/failure_types.md`). Neither study pre-registered this analysis, so
everything in it is exploratory and post hoc. The results of record are in `results/eval.json`
and `results/followup.json`.

**Who classifies.** Claude (an LLM: Claude Opus 5.5, in Claude Code), not a person. No label is
checked by the owner. A label is an LLM's reading of the text, the model and the key, checked
by re-solving where possible (rule 3).

M6 also has its own pre-registered taxonomy (`src/opt_agent/taxonomy.py`; labels by two LLM
judges, `review/taxonomy/test/`), for its main test run only. This is a different list, the
owner's, applied to both studies. It's classified without reading those labels, which are
compared with it afterwards.

## What is classified

- **M6** (NL4Opt): every wrong answer of the two solver conditions, single-shot and
  self-correction, in the test run (`runs/test`) and the perturbed run (`runs/test-perturbed`),
  scored as in the result of record (strict accuracy, scorable problems).
- **The follow-up** (ComplexLP and IndustryOR): every wrong answer of the three solver
  conditions, single-shot, self-correction and checklist revision, in every sample, on all 128
  problems (the 7 exposed ones marked), scored against the raw keys as in
  `runs/followup-test/followup_report.json`'s failure counts.
- **The checklist's 8 right-to-wrong revisions**, labeled by the error the revision added to a
  model that was right.
- Not the baseline: it writes no model, so there's no model error to name.

A wrong answer is **loud** (no answer) or **silent** (an answer, but not the key's).

## The types

| Type | The model's error |
|---|---|
| wrong objective | It optimizes the wrong quantity or in the wrong sense: maximize for minimize, revenue for profit, or a whole term left out or added. |
| missing constraint | A requirement the text states has no constraint or bound in the model. |
| wrong number/coefficient | The structure is right, but a number from the text's data is wrong: a different value, a value on the wrong variable or constraint, or a wrong sum or product. |
| wrong inequality direction | `<=` for `>=` or the reverse, or an inequality for an equation or the reverse, where no accepted reading allows it. |
| integrality | Integer variables where the key's answer needs continuous ones, or the reverse. |
| units/misread quantity | A statement of the text read wrongly: a unit (minutes for hours), a percentage, a rate for a total, a ratio or comparison built backwards, or a limit applied to the wrong set of things (one combined limit read as one per item, or the reverse). |
| answer-key dispute | No error is found in the model: it's a defensible reading of the text, and the key is wrong or rests on another defensible reading. Needs a stated reason. |
| other | Anything else, with a named sub-label: **no usable model** (a loud failure without a model), **extra constraint** (a requirement the text doesn't state), **wrong variables** (a decision missing or modeled wrongly), or something new, named. |

## Rules

1. **One primary type per wrong answer**, plus any secondary ones. If fixing one error alone
   gives the key's answer, that error is primary; otherwise the primary is the first of the
   model's errors in the table's order. Answer-key dispute applies only when no model error is
   found.
2. **Evidence.** M6's key comes with a reference model (built from NL4Opt's annotations), so a
   model is compared with it. The follow-up's keys are numbers only, so a model is compared with
   the text.
3. **Re-solving.** For each silent failure the classifier writes a corrected model: the model
   with the labeled errors fixed and nothing else changed. Both solvers solve it.
   **Confirmed** means its answer is right under the study's own scoring; **unconfirmed** means
   it isn't, and the label stands, marked. A corrected model comes from the text, never from
   fitting the key. For a dispute, the note says which reading the model followed and what the
   key would need. A loud failure without a model has nothing to re-solve.
4. **One label per distinct model.** Answers to the same problem with the same model (for
   example, single-shot's and self-correction's when self-correction didn't revise) share a
   label, and the counts count answers.
5. **No problem text is quoted** (it's licensed data, `DATA_NOTICE.md`). Each example says what
   went wrong in the classifier's own words, by problem ID.
6. **The list is fixed.** No type is added, merged or split once classifying starts. A case that
   fits none is "other", with a named sub-label.
