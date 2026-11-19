# ADR-0008: A static copy of the examples page, computed when CI builds it

- **Status:** Accepted
- **Date:** 2026-11-18
- **Deciders:** Max asked for a no-server demo on GitHub Pages; Claude Code chose how
  (logged in [`HANDOFF.md`](../HANDOFF.md))

## Context

The demo runs locally (ADR-0007), so a reader has to install Docker or Python to see it. GitHub
Pages serves static files only: nothing on it can run CBC, HiGHS or Python, and nothing on it
may hold a key.

## Decision

`scripts/static_demo.py` builds the site in CI: it runs the demo app in-process (FastAPI's
TestClient, examples mode, the committed replies), asks it what the page asks (`/health`,
`/examples`, and `/solve` for each example), and saves each response's bytes next to the page.
The same `page.html`, built with `data-site="static"`, reads those files by relative paths and
sends nothing; other text gets the examples-only refusal. CI checks the built site in headless
Chromium and deploys it from `main` once the tests pass.

## Options Considered

### Option A: Responses computed at build time (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one build script, a mode switch in the page, two CI jobs |
| API cost | None: every reply replays from the committed cache |
| Verifiability | High: the saved responses are the app's own bytes (a test compares them), and the browser check requires every example verified and equal to its hand-checked answer |
| Reproducibility | High: rebuilt from the committed replies on every push, stamped with its commit |

**Pros:** the page shows exactly what the local demo shows, with one page to maintain.
**Cons:** the browser recomputes nothing: the solving happened in CI, which the page says.

### Option B: The pipeline in the browser (Pyodide)

| Dimension | Assessment |
|---|---|
| Complexity | High: the package and SciPy in WebAssembly, tens of megabytes per visit |
| API cost | None, with the same cached replies |
| Verifiability | Lower: CBC has no browser build, so the CBC-versus-HiGHS cross-check can't run |
| Reproducibility | A second runtime whose numerics would need their own checks |

**Pros:** the solving happens in front of the visitor. **Cons:** it drops the cross-check that
ADR-0003 makes the core of verification.

### Option C: A hosted server in examples mode

| Dimension | Assessment |
|---|---|
| Complexity | Medium: a host, cold starts, upkeep |
| API cost | None in examples mode; one setting away from paid calls |
| Verifiability | The same as the local demo |
| Reproducibility | The same as the local demo |

**Pros:** the real app, live. **Cons:** a running service to keep up for four fixed answers.

## Trade-off Analysis

The examples' answers are fixed by their committed replies, so computing them once per build
loses nothing a visitor could see, and keeps both solvers in the loop. Option B buys in-browser
solving at the cost of the cross-check; Option C buys a live server that adds nothing here.

## Consequences

- Easier: a reader sees the demo from a link, and CI rebuilds and checks it on every push.
- Harder: Pages has to be switched on once, in the repository's settings (Source: GitHub
  Actions); until then the deploy job is skipped, not failed.
- Revisit: if the examples ever include an attempt that fails first (ADR-0007), the static page
  shows it with no change.

## Action Items

1. [x] The build script, the page's static mode, the tests and the CI jobs (2026-11-18).
2. [ ] Settings > Pages > Source: GitHub Actions (the owner's).
