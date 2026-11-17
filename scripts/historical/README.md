# Historical scripts

Scripts that did their job at an earlier commit and don't run at HEAD as they are. They're
kept so the record is complete; nothing current depends on them, and both make no API calls.

| script | what it did | where it ran | why it doesn't run at HEAD |
|---|---|---|---|
| `rescore_dev.py` | re-scored a follow-up dev run from its cache at $0, after a change to the pipeline (`docs/FOLLOWUP_DEV_LOG.md`) | `ba8b151` (2026-11-09: revision 1, `runs/dev-checklist` into `runs/dev-checklist-rev1`), and again for the smoke run of condition 4 after the CBC fix (logged in `f2bd2e3`, 2026-11-13) | HEAD's requests no longer match the ones those runs cached, so its refuse-all client stops at the first cache miss, by design |
| `dispute_packets.py` | wrote section 5b's packets for the key-dispute check (`review/followup_disputes/`), which wasn't performed (`docs/followup/DEVIATIONS.md`, deviation 2) | `29b7c99` (2026-11-15), whose `src/` and lock are identical to tag `followup-freeze`: the git-ignored packets and the committed `MANIFEST.json`; `--prompts` never ran | it reads the sealed test split (`followup.load_test`), which opens only on the follow-up's frozen inputs |

To run one again, use a separate checkout of the commit it ran at, for example
`git worktree add ../opt-agent-29b7c99 29b7c99`, with its own environment
(`requirements.lock` and `pip install --no-deps -e .`) and the git-ignored data the script
reads (LLM4OR's, from `python scripts/fetch_llm4or.py`). At that commit the script is
`scripts/<name>.py`. Anything the 5b check found now would be exploratory and post hoc, never
the result of record.
