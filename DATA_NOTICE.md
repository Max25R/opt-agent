# Data notice

**The MIT license in [`LICENSE`](LICENSE) covers this project's code only.** (`LICENSE` is
the plain MIT text, so that GitHub recognizes it; this notice is where the rest is said.)
Benchmark problem text and answers in this repository, mostly under `runs/` and `data/`, and
also in `review/`, `tests/` and short quotes in `docs/`, keep their own licenses, below; the
MIT license doesn't apply to them.

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
annotations, and so do the review packets and prompts under `review/` (for example
`review/test_reviews/PACKET.md`), the test fixtures `tests/problems.py` and `tests/fakes.py`,
and short quotes in `docs/`: Ramamonjison et al., "NL4Opt Competition: Formulating Optimization Problems
Based on Their Natural Language Descriptions" (NeurIPS 2022 Competition Track), MIT license,
Copyright (c) 2022 Huawei Technologies ([`data/nl4opt/LICENSE`](data/nl4opt/LICENSE)). The perturbed problems change
NL4Opt's numbers (the rule is in `src/opt_agent/perturb.py`; counts in
`data/nl4opt/ground_truth/PERTURBED.md`).

**ORLM's NL4Opt answers.** ORLM's answer set for NL4Opt (Huang, Tang et al., arXiv:2405.17743;
<https://huggingface.co/datasets/CardinalOperations/NL4OPT>,
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)) was a cross-check for the
answer key. The file itself isn't committed, but some of its answers are cited one problem at
a time, as the reason for a review ("ORLM says 18", "matching ORLM"):
- in `data/nl4opt/reviews.json`, and copied from it into `data/nl4opt/ground_truth/`
  (`test.json`, `test-perturbed.json` and `REPORT.md`);
- in the owner's review packet, `review/test_reviews/`;
- in one string in `src/opt_agent/external_check.py` ("ORLM found no solution"), which is in
  the demo's Docker image.

Those answers stay under CC BY-NC 4.0: **non-commercial only**, with this attribution.

**ORLMBenchmark's NL4Opt answers.** The external cross-check compared our test answers with
the corrected NL4OPT in ORLMBenchmark (`chenyitian-shanshu/ORLMBenchmark`, `NL4OPT.jsonl`,
revision `54ca621`, Apache-2.0), from the authors of the SIRL paper (arXiv:2505.11792). The
file isn't committed; `review/external_check.md` cites some of its answers. Its NL4OPT file is ORLM's answer set with corrections, so an answer it shares
with ORLM's is arguably ORLM's too: treat those as CC BY-NC 4.0, as above.

**LLM4OR's NL4Opt answers.** Amendment 5 compares our answers with LLM4OR's cleaned NL4Opt
(the LLM4OR release above, no license stated). Its files aren't committed, but
`docs/amendments/amendment-5.md` and `results/eval.json` (its `amendment_5` entry) cite some
of its answers and which problems it removed.

## The failure-type analysis (`docs/analysis/`)

`docs/analysis/fixes/` holds corrected versions of Claude's models for problems of both
studies (their variable names and numbers come from the problems), and
`docs/analysis/failure_types.csv` short notes on what went wrong, in this project's words. No
problem text is quoted. Each file keeps the license of its problem, which its name gives
(`test__` and `test-perturbed__`: NL4Opt, MIT; `followup-test__complexlp-`: ComplexLP, CC BY-SA
4.0; `followup-test__industryor-`: IndustryOR, CC BY-NC 4.0, non-commercial only).

## The demo's examples (this project's own)

The four example problems in `src/opt_agent/demo/examples.py` (paint production, café
staffing, produce shipping, cattle feed) were written for this project, and their cached
replies (`src/opt_agent/demo/replies/`) are Claude's answers to them. Both are covered by the
MIT license with the code. `tests/test_demo.py` checks that no example shares 8 words in a
row with any NL4Opt problem.

## Removal on request

If you hold rights in any of this material and want it removed, open an issue on this
repository, and it will be removed.
