"""docs/demo.png: the demo's page after it solves one example, captured headlessly.

The app runs in-process (FastAPI's TestClient), in examples mode with the committed replies,
and Playwright's headless Chromium loads the page from it: every request the page makes is
routed to the TestClient. So nothing listens on a port, nothing needs a key, and nothing is
sent anywhere. The page is used as a visitor would use it (an example's button), and the
capture runs from the top of the page to the end of the explanation, once it's shown.

Playwright isn't one of the project's dependencies (not in requirements.lock):
    pip install playwright==1.65.2 && python -m playwright install --only-shell chromium
Run:  python scripts/screenshot.py [--example paint] [--out docs/demo.png]
"""

import argparse
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from opt_agent.demo.app import Settings, create_app
from opt_agent.demo.examples import BY_ID

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://demo.invalid"  # never resolved: every request is routed in-process
WIDTH = 1100  # CSS pixels; captured at 2x for a sharp image


def capture(example: str, out: Path) -> None:
    web = TestClient(create_app(Settings(mode="examples")))

    def serve(route, request) -> None:
        response = web.request(
            request.method, request.url.removeprefix(ORIGIN) or "/",
            content=request.post_data_buffer,
            headers={"content-type": request.headers.get("content-type", "text/plain")},
        )  # fmt: skip
        route.fulfill(status=response.status_code, body=response.content,
                      headers={"content-type": response.headers["content-type"]})  # fmt: skip

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": 900},
                                device_scale_factor=2, color_scheme="light")  # fmt: skip
        page.route(f"{ORIGIN}/**", serve)
        page.goto(f"{ORIGIN}/")
        page.get_by_role("button", name=BY_ID[example].title).click()
        page.wait_for_selector("#result:not([hidden])")
        box = page.locator("#explanation-card").bounding_box()
        height = box["y"] + box["height"] + 24
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": WIDTH, "height": height})
        browser.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Capture the demo page headlessly.")
    parser.add_argument("--example", default="paint", choices=sorted(BY_ID))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "demo.png")
    args = parser.parse_args(argv)
    capture(args.example, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
