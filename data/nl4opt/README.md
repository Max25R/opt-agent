# NL4Opt data

- `raw/` (git-ignored): NL4Opt's `generation_data/{dev,test}.jsonl`, pinned to commit
  `49f1e0d` and checked by SHA-256. Re-fetch with `python -m opt_agent.data`.
- `ground_truth/` (committed, generated): our models and answers, built from the raw
  annotations by `python -m opt_agent.ground_truth`. `REPORT.md` summarizes them.
  `DEV_WALKTHROUGH.md` comes from `python scripts/dev_walkthrough.py`.
- `reviews.json` (committed, hand-written): the verdict for every problem the automatic
  checks flag, each with the reason, checked against the problem text.

The problem texts and annotations come from the
[NL4Opt competition](https://github.com/nl4opt/nl4opt-competition) and are used under its
MIT License (see `LICENSE` in this folder).

ORLM's answer set ([CardinalOperations/NL4OPT](https://huggingface.co/datasets/CardinalOperations/NL4OPT),
CC BY-NC 4.0) is downloaded to `../thirdparty/` for a cross-check only, and isn't
redistributed here.
