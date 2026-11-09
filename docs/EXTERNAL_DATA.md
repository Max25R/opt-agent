# External data

Data from outside the project, kept in `data/external/` and **not committed** (git-ignored),
with where it came from and how to check it. Nothing here is used by milestone 6: its
ground truth, runs and results are frozen (tag `m6-freeze`).

## LLM4OR cleaned benchmarks (`data/external/llm4or-clean/`)

**Source.** The cleaned benchmark collection of Xiao et al. 2025, "A Survey of Optimization
Modeling Meets LLMs: Progress and Future Directions" (arXiv 2508.10047, IJCAI 2025). The
paper points to its portal, https://llm4or.github.io/LLM4OR, which links the cleaned data:
https://github.com/LLM4OR/LLM4OR/tree/master/static/clean_benchmarks

| | |
|---|---|
| Repository | https://github.com/LLM4OR/LLM4OR |
| Commit | `75962df5ddf531906fda76f8708c658114e63c0e` (master, 2025-08-30, "add arxiv link and citation") |
| Tree `static/clean_benchmarks` | `2cd387a3bf7991104a4df582f6fd50d2ccf7bb03` |
| Retrieved | 2026-11-08 |
| License | **None stated** (no LICENSE file; the README gives none). So it isn't committed here. The originals carry their own: NL4Opt is MIT; IndustryOR comes from ORLM, and ComplexLP from MAMO. |

The portal says error samples were tagged with an "error" label. The files hold no such
label, and the counts below are far smaller than the originals (NL4Opt 289, IndustryOR
100, ComplexLP 211), so the error samples appear to have been removed instead.

**What was copied** (only these three; the folder also has EasyLP, NL4LP, ComplexOR and
ReSocratic):

| here | from `static/clean_benchmarks/` | items | git blob/tree at the commit | SHA-256 |
|---|---|---|---|---|
| `NL4Opt/prob_*/description.txt`, `sample.json` | `NL4Opt/` | 214 | tree `2e31f376ca3d8d4716f872a92c8569598bab0800` | `ce544464946e83514bd73b2e82e9f3cb50d7d64076fc1c81e9e176d09e5e88c8` (of the sorted `shasum -a 256` list of the 428 files) |
| `IndustryOR.jsonl` | `IndustryOR.jsonl` | 42 | blob `aef84d4334ee787041f3c107530553ec91966f3f` | `d7c2c05377ade5bc6a401ebf3075f0e00fa91068439761e5b46fa3045ffc19b5` |
| `Mamo_complex_lp_clean.jsonl` | `Mamo/Mamo_complex_lp_clean.jsonl` | 111 | blob `8afd44175e8146c419ca897e5a5b1f831356a7f2` | `28e10dff1146ff635673293b5730abb3d7efa2f7bbe91de60fe67b729dfe7a0d` |

Left out on purpose: each NL4Opt problem's `code_example.py` (a function stub; foreign code
is never run here) and the `.DS_Store` files.

**Formats.**
- NL4Opt: `description.txt` is the problem text. `sample.json` is
  `[{"input": {decision: value, ...}, "output": [objective]}]`: an optimal solution and its
  objective. One problem has `"output": [null]` (no optimum).
- IndustryOR: one JSON object per line with `en_question`, `en_answer` (the objective, as a
  string), `question_type` (`LP`, `IP` or `MIP`) and `difficulty`.
- ComplexLP: one JSON object per line with `id`, `Question`, `Answer` (a string), `Type`
  (`complex_lp`) and `Category`.

**To fetch it again** (the clone goes outside the repository, since the sandbox refuses a
nested `.git`; then copy the files as above and compare the hashes):

```bash
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/LLM4OR/LLM4OR.git "$TMPDIR/llm4or"
cd "$TMPDIR/llm4or" && git sparse-checkout set --no-cone static/clean_benchmarks && git checkout 75962df5ddf531906fda76f8708c658114e63c0e
```
