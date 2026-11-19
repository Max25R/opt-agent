"""The demo as a static site, for GitHub Pages: the examples page with no server, no API key
and no API call, replaying the committed cached replies.

A browser can't run CBC, so the site holds the demo's answers rather than recomputing them:
the build runs the real demo app in-process (FastAPI's TestClient, examples mode, with the
committed replies in src/opt_agent/demo/replies/), asks it what the page asks (GET /health,
GET /examples, and POST /solve for each example), and saves each response's bytes as a file
next to the page. The page, switched to data-site="static", reads those files instead of
calling the app. So the static page shows exactly what the local demo shows, computed by the
same pipeline (every reply replayed, both solvers, the arithmetic checks) when the site was
built: by CI, on every push (.github/workflows/ci.yml, jobs static-demo and deploy-pages).

The site:
    index.html         page.html in static mode, stamped with the commit it was built from
    health.json        GET /health
    examples.json      GET /examples
    solve/<id>.json    POST /solve for each example

The commit stamp is left out when tracked files have uncommitted changes, since the page
couldn't say what built it. A build refuses to finish if any response isn't a 200.

`--check DIR` opens a built site in headless Chromium (Playwright, from the optional
requirements-docs.lock) under a base path, as GitHub Pages serves it, and answers every
request from DIR: nothing listens on a port and nothing is sent. Each example's button must
give a verified answer that matches its hand-checked one, other text must get the
examples-only refusal, the page must raise no error, and it must ask for nothing but GETs of
the site's own files.

Run:  python scripts/static_demo.py [--out build/site]
      python scripts/static_demo.py --check build/site
"""

import argparse
import json
import mimetypes
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER, STATIC = 'data-site="server"', 'data-site="static"'
ORIGIN, BASE = "http://pages.invalid", "/opt-agent/"  # never resolved: every request is routed
BROWSERS_OWN = {ORIGIN + "/favicon.ico"}  # asked for by the browser, not the page


def commit() -> str | None:
    """HEAD's commit, or None if tracked files have changed (or there's no git)."""
    try:
        git = ["git", "-C", str(ROOT)]
        sha = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True,
                             check=True).stdout.strip()  # fmt: skip
        dirty = subprocess.run([*git, "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, check=True).stdout  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        return None
    return None if dirty.strip() else sha


def static_page(page: str, sha: str | None) -> str:
    """page.html switched to static mode, with the commit stamp if there is one."""
    if page.count(SERVER) != 1:
        raise ValueError(f"page.html must say {SERVER} exactly once")
    stamp = f' data-commit="{sha}"' if sha else ""
    return page.replace(SERVER, STATIC + stamp)


def responses() -> dict[str, bytes]:
    """Each site file's path and bytes, as the demo app answers in examples mode."""
    from fastapi.testclient import TestClient

    from opt_agent.demo.app import Settings, create_app

    web = TestClient(create_app(Settings(mode="examples")))
    answers = {"health.json": web.get("/health"), "examples.json": web.get("/examples")}
    for example in answers["examples.json"].json():
        answers[f"solve/{example['id']}.json"] = web.post(
            "/solve", json={"problem": example["text"]}
        )
    failed = {path: r.status_code for path, r in answers.items() if r.status_code != 200}
    if failed:
        raise SystemExit(f"the demo app didn't answer: {failed}")
    return {path: r.content for path, r in answers.items()}


def build(out: Path) -> None:
    from opt_agent.demo.app import PAGE

    if out.exists():
        if not (out / "health.json").is_file():  # only ever replace an earlier build
            raise SystemExit(f"{out} exists and isn't a built site: choose another --out")
        shutil.rmtree(out)
    sha = commit()
    page = static_page(PAGE.read_text(encoding="utf-8"), sha)
    files = {"index.html": page.encode()} | responses()
    for path, content in files.items():
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_bytes(content)
    stamp = f"built from {sha[:7]}" if sha else "no commit stamp (uncommitted changes)"
    print(f"wrote {len(files)} files to {out}, {stamp}")


def check(site: Path) -> None:
    from playwright.sync_api import sync_playwright

    examples = json.loads((site / "examples.json").read_text())
    asked, errors = [], []

    def serve(route, request) -> None:
        asked.append((request.method, request.url))
        path = request.url.removeprefix(ORIGIN + BASE).split("?")[0] or "index.html"
        file = site / path
        own = request.method == "GET" and request.url.startswith(ORIGIN + BASE)
        if not own or not file.is_file():
            route.fulfill(status=404, body="not found")
            return
        kind = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        route.fulfill(status=200, body=file.read_bytes(), content_type=kind)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/*", serve)
        for example in examples:  # a fresh load each time, so the result shown is this one's
            page.goto(ORIGIN + BASE)
            page.get_by_role("button", name=example["title"]).click()
            page.wait_for_selector("#result:not([hidden])")
            verdict = page.get_attribute("#verdict", "class") or ""
            answer = page.inner_text("#answer")
            if "ok" not in verdict.split() or "Matches the hand-checked answer" not in answer:
                raise SystemExit(f"{example['id']}: not verified and matching: {answer!r}")
            print(f"{example['id']}: verified, matches the hand-checked answer")
        page.goto(ORIGIN + BASE)
        if not page.is_visible("#static-note"):
            raise SystemExit("the static page doesn't say what it is")
        page.fill("#problem", "Maximize x + y subject to x + y <= 4.")
        page.click("#solve")
        page.wait_for_selector("#error:not([hidden])")
        if "example problems only" not in page.inner_text("#error"):
            raise SystemExit("other text didn't get the examples-only refusal")
        print("other text: refused, nothing sent")
        browser.close()
    own = [(m, u) for m, u in asked if m == "GET" and u.startswith(ORIGIN + BASE)]
    strays = [(m, u) for m, u in asked if (m, u) not in own and u not in BROWSERS_OWN]
    if errors or strays:
        raise SystemExit(f"page errors: {errors}; requests outside the site: {strays}")
    print(f"static site check passed: {len(own)} GETs of the site's own files, nothing else")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build or check the demo's static site.")
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "site")
    parser.add_argument("--check", type=Path, metavar="DIR", help="check a built site")
    args = parser.parse_args(argv)
    if args.check:
        check(args.check)
    else:
        build(args.out)


if __name__ == "__main__":
    main()
