import json
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.download_service_public import download_if_changed


class FakeResponse:
    headers = {"ETag": '"version-1"', "Last-Modified": "Mon, 01 Jan 2026 00:00:00 GMT"}

    def read(self) -> bytes:
        return b"archive-content"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_download_creates_archive_and_manifest(tmp_path) -> None:
    with patch("scripts.download_service_public.urlopen", return_value=FakeResponse()):
        changed = download_if_changed(url="https://example.test/archive.zip", data_dir=tmp_path)

    assert changed is True
    assert (tmp_path / "vosdroits-current.zip").read_bytes() == b"archive-content"
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["etag"] == '"version-1"'
    assert manifest["source_url"] == "https://example.test/archive.zip"


def test_download_skips_when_server_returns_not_modified(tmp_path) -> None:
    (tmp_path / "manifest.json").write_text('{"etag":"old"}')
    not_modified = HTTPError("https://example.test/archive.zip", 304, "Not Modified", None, None)

    with patch("scripts.download_service_public.urlopen", side_effect=not_modified):
        changed = download_if_changed(url="https://example.test/archive.zip", data_dir=tmp_path)

    assert changed is False
