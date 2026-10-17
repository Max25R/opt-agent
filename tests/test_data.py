import hashlib
import io

import pytest

from opt_agent import data
from opt_agent.data import Source, fetch


def source_for(content: bytes) -> Source:
    return Source(
        "x/file.txt", "https://example.invalid/file.txt", hashlib.sha256(content).hexdigest()
    )


def fake_download(content: bytes):
    return lambda url, timeout, context: io.BytesIO(content)


def no_network(*args, **kwargs):
    raise AssertionError("fetch shouldn't download an intact file")


def test_intact_file_is_not_downloaded_again(tmp_path, monkeypatch):
    content = b"pinned content"
    (tmp_path / "x").mkdir()
    (tmp_path / "x/file.txt").write_bytes(content)
    monkeypatch.setattr(data.urllib.request, "urlopen", no_network)
    assert fetch(source_for(content), tmp_path).read_bytes() == content


def test_missing_file_is_downloaded_and_verified(tmp_path, monkeypatch):
    content = b"pinned content"
    monkeypatch.setattr(data.urllib.request, "urlopen", fake_download(content))
    assert fetch(source_for(content), tmp_path).read_bytes() == content


def test_a_changed_download_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(data.urllib.request, "urlopen", fake_download(b"tampered"))
    with pytest.raises(RuntimeError, match="doesn't match its pinned SHA-256"):
        fetch(source_for(b"pinned content"), tmp_path)
    assert not (tmp_path / "x/file.txt").exists()
