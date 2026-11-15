# Data notice

**The MIT license in [`LICENSE`](LICENSE) covers this project's code only.** Some committed
files hold problem text and answers from other people's benchmarks. Those parts stay under
their own licenses, below, and the MIT license doesn't apply to them.

## The follow-up's problems (ComplexLP and IndustryOR, as cleaned by LLM4OR)

**Where the text is.** The run records under `runs/` hold the full problem text, because
every API request sent a problem's text and every record keeps its request:
- `runs/followup-test/` (the follow-up test run: `cache/`, `attempts.jsonl`; `results.jsonl`
  quotes short phrases of the text in its checklist flags);
- `runs/dev-checklist/`, `runs/dev-checklist-revision/` and
  `runs/dev-checklist-rev1/attempts.jsonl` (follow-up dev runs).

**Answers.** `runs/followup-test/followup_report.json` lists the benchmark's answer (the key)
for the problems under dispute, and the follow-up docs cite a few keys.

**The version used.** Both benchmarks as cleaned by LLM4OR (Xiao et al., "A Survey of
Optimization Modeling Meets LLMs: Progress and Future Directions", arXiv:2508.10047),
<https://github.com/LLM4OR/LLM4OR>, commit `75962df5ddf531906fda76f8708c658114e63c0e`,
folder `static/clean_benchmarks/`. **LLM4OR states no license** for its cleaned versions;
the originals' licenses follow. The text and answers are reproduced as they appear in those
files, embedded in this project's API request and response records; nothing else was
changed. Details: [`docs/EXTERNAL_DATA.md`](docs/EXTERNAL_DATA.md).

| benchmark | from | license | what it means here |
|---|---|---|---|
| **ComplexLP** (`complexlp:<id>`) | the Mamo benchmark: Huang et al., "LLMs for Mathematical Modeling: Towards Bridging the Gap between Natural and Mathematical Languages", arXiv:2405.13144; <https://github.com/FreedomIntelligence/Mamo> | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | **ShareAlike**: material derived from ComplexLP is shared under CC BY-SA 4.0 too, with this attribution |
| **IndustryOR** (`industryor:<line>`) | ORLM: Huang, Tang et al., "ORLM: A Customizable Framework in Training Large Models for Automated Optimization Modeling", arXiv:2405.17743; <https://huggingface.co/datasets/CardinalOperations/IndustryOR> (code: <https://github.com/Cardinal-Operations/ORLM>) | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (the dataset card's) | **Non-commercial only**: material derived from IndustryOR may not be used commercially |

A record holds one problem, so its label (`complexlp:14`, `industryor:7`) tells which
license applies.

## Milestone 6's problems (NL4Opt)

`runs/test/`, `runs/test-perturbed/` and `data/nl4opt/` hold NL4Opt problem text and
annotations: Ramamonjison et al., "NL4Opt Competition: Formulating Optimization Problems
Based on Their Natural Language Descriptions" (NeurIPS 2022 Competition Track), MIT license,
Copyright (c) 2022 Huawei Technologies ([`data/nl4opt/LICENSE`](data/nl4opt/LICENSE)). The perturbed problems change
NL4Opt's numbers (the rule is in `src/opt_agent/perturb.py`; counts in
`data/nl4opt/ground_truth/PERTURBED.md`). ORLM's NL4Opt answers (CC BY-NC 4.0) are a
cross-check only and are never committed.

## Removal on request

If you hold rights in any of this material and want it removed, open an issue on this
repository, and it will be removed.
