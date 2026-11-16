"""docs/demo.png: the demo after it solves one example, captured headlessly and framed as
committed, so a rerun reproduces the file without cropping by hand.

The app runs in-process (FastAPI's TestClient), in examples mode with the committed replies,
and Playwright's headless Chromium loads the page from it: every request the page makes is
routed to the TestClient. So nothing listens on a port, nothing needs a key, and nothing is
sent anywhere. The page is used as a visitor would use it (an example's button), and the
capture waits for a verified answer.

**The frame** (frame()) is the problem card through the explanation card, with the answer,
the verification and Claude's model between them, and the page background around them:
14 px above (the problem card's own top margin) and 13.5 px on the other sides; at 2x that's
28 and 27 device pixels. The page's own title block is left out, since the README has the
title and the pitch. Only that range is captured (a clip screenshot, in a viewport tall
enough to hold it), never the full page. The picture is saved through Pillow
(optimize=True), as the committed one was, so the same rendering gives the same bytes. With
another machine's fonts the cards' heights change, but the frame doesn't.

`--check PATH` reports a picture's margins and fails unless they're the frame's, to within
one device pixel (another machine's fonts can put a border between two pixels). CI's
pictures job runs it on its own capture.

Playwright and Pillow are pinned in the optional requirements-docs.lock:
    pip install -r requirements-docs.lock -c requirements.lock
    python -m playwright install --only-shell chromium
Run:  python scripts/screenshot.py [--example paint] [--out docs/demo.png]
      python scripts/screenshot.py --check docs/demo.png
"""

import argparse
import io
import math
import sys
from pathlib import Path

from opt_agent.demo.examples import BY_ID

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://demo.invalid"  # never resolved: every request is routed in-process
WIDTH = 1100  # CSS pixels
HEIGHT = 2400  # CSS pixels: tall enough to hold the frame; capture() refuses if it isn't
SCALE = 2  # device pixels per CSS pixel, for a sharp image
MARGIN_TOP, MARGIN = 14, 13.5  # CSS pixels of page background around the cards


def frame(first: dict, last: dict) -> dict:
    """The clip, in CSS pixels, from the top of `first` to the bottom of `last` (two element
    boxes in one column, as Playwright's bounding_box() gives them), with the margins, its
    edges on whole device pixels."""
    left = min(first["x"], last["x"]) - MARGIN
    right = max(first["x"] + first["width"], last["x"] + last["width"]) + MARGIN
    top = first["y"] - MARGIN_TOP
    bottom = last["y"] + last["height"] + MARGIN
    left, top = (math.floor(v * SCALE) / SCALE for v in (left, top))
    right, bottom = (math.ceil(v * SCALE) / SCALE for v in (right, bottom))
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def expected_margins() -> tuple[int, int, int, int]:
    """The frame's margins in device pixels: top, left, bottom, right."""
    top, side = round(MARGIN_TOP * SCALE), round(MARGIN * SCALE)
    return top, side, side, side


def capture(example: str, out: Path) -> tuple[int, int]:
    from fastapi.testclient import TestClient
    from PIL import Image
    from playwright.sync_api import sync_playwright

    from opt_agent.demo.app import Settings, create_app

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
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT},
                                device_scale_factor=SCALE, color_scheme="light")  # fmt: skip
        page.route(f"{ORIGIN}/**", serve)
        page.goto(f"{ORIGIN}/")
        page.get_by_role("button", name=BY_ID[example].title).click()
        page.wait_for_selector("#result:not([hidden])")
        if "ok" not in (page.get_attribute("#verdict", "class") or "").split():
            sys.exit(f"{example} didn't come out verified, so nothing was captured")
        problem = page.locator(".card").filter(has=page.locator("#problem")).bounding_box()
        clip = frame(problem, page.locator("#explanation-card").bounding_box())
        if clip["y"] + clip["height"] > HEIGHT:
            sys.exit(f"the frame ends below the {HEIGHT} px viewport: raise HEIGHT")
        png = page.screenshot(clip=clip)
        browser.close()
    picture = Image.open(io.BytesIO(png)).convert("RGB")
    picture.save(out, optimize=True)
    return picture.size


def margins(path: Path) -> tuple[int, int, int, int]:
    """Rows or columns of plain page background along each edge: top, left, bottom, right."""
    from PIL import Image

    image = Image.open(path).convert("RGB")
    pixels, (width, height) = image.load(), image.size
    background = pixels[0, 0]

    def plain_row(y: int) -> bool:
        return all(pixels[x, y] == background for x in range(width))

    def plain_column(x: int) -> bool:
        return all(pixels[x, y] == background for y in range(height))

    return (
        next(y for y in range(height) if not plain_row(y)),
        next(x for x in range(width) if not plain_column(x)),
        next(y for y in range(height) if not plain_row(height - 1 - y)),
        next(x for x in range(width) if not plain_column(width - 1 - x)),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Capture the demo page headlessly.")
    parser.add_argument("--example", default="paint", choices=sorted(BY_ID))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "demo.png")
    parser.add_argument("--check", type=Path, metavar="PATH",
                        help="only check a picture's margins against the frame")  # fmt: skip
    args = parser.parse_args(argv)
    if args.check:
        found, expected = margins(args.check), expected_margins()
        print(f"{args.check}: margins {found} (top, left, bottom, right); the frame's {expected}")
        if any(abs(f - e) > 1 for f, e in zip(found, expected, strict=True)):
            sys.exit("not the frame: a margin differs by more than one device pixel")
        return
    width, height = capture(args.example, args.out)
    print(f"wrote {args.out} ({width}x{height} px: the problem card through the explanation)")


if __name__ == "__main__":
    main()
