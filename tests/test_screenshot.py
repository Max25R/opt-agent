"""scripts/screenshot.py's frame: the committed docs/demo.png is exactly what it captures, so
a rerun reproduces the picture without cropping by hand. No browser here (CI's pictures job
captures one and checks its margins); the margin checks need Pillow, which is in the
optional requirements-docs.lock, so they're skipped without it."""

import importlib.util
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PICTURE = ROOT / "docs" / "demo.png"
spec = importlib.util.spec_from_file_location("screenshot", ROOT / "scripts" / "screenshot.py")
screenshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screenshot)

# The two cards' boxes (CSS pixels) in the owner's capture that docs/demo.png comes from:
# the problem card's top at 192, the explanation card's bottom at 1270, the column 948 wide.
PROBLEM = {"x": 76, "y": 192, "width": 948, "height": 292}
EXPLANATION = {"x": 76, "y": 1097, "width": 948, "height": 173}


def png_size(path: Path) -> tuple[int, int]:
    return struct.unpack(">II", path.read_bytes()[16:24])  # the IHDR chunk's width, height


def test_the_frame_is_the_committed_pictures():
    clip = screenshot.frame(PROBLEM, EXPLANATION)
    assert clip == {"x": 62.5, "y": 178.0, "width": 975.0, "height": 1105.5}
    size = (clip["width"] * screenshot.SCALE, clip["height"] * screenshot.SCALE)
    assert size == png_size(PICTURE) == (1950, 2211)


def test_the_frame_lands_on_whole_device_pixels():
    clip = screenshot.frame(PROBLEM | {"y": 190.3}, EXPLANATION | {"height": 172.9})
    assert all((value * screenshot.SCALE).is_integer() for value in clip.values())
    assert clip["y"] <= 190.3 - screenshot.MARGIN_TOP  # rounded outward, never into a card


def test_the_committed_picture_has_the_frames_margins():
    pytest.importorskip("PIL")
    assert screenshot.margins(PICTURE) == screenshot.expected_margins() == (28, 27, 27, 27)
    screenshot.main(["--check", str(PICTURE)])  # passes


def test_a_picture_framed_otherwise_fails_the_check(tmp_path):
    image = pytest.importorskip("PIL.Image")
    picture = image.new("RGB", (200, 160), (247, 247, 245))
    picture.paste((255, 255, 255), (40, 28, 160, 133))  # a card with 40 px at the sides
    picture.save(tmp_path / "other.png")
    assert screenshot.margins(tmp_path / "other.png") == (28, 40, 27, 40)
    with pytest.raises(SystemExit, match="not the frame"):
        screenshot.main(["--check", str(tmp_path / "other.png")])
