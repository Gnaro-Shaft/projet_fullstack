"""Download and version the Service-Public 'Vos droits et démarches' archive."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SOURCE_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/"
    "0ed10f28-d197-4324-97b3-037f625095ac"
)
DATA_DIR = Path("data/raw/service-public")


def load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def download_if_changed(url: str = SOURCE_URL, data_dir: Path = DATA_DIR) -> bool:
    """Download the archive only when its ETag changed.

    Returns ``True`` when a new local archive was written, otherwise ``False``.
    """
    archive_path = data_dir / "vosdroits-current.zip"
    manifest_path = data_dir / "manifest.json"
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(manifest_path)

    headers = {}
    if etag := manifest.get("etag"):
        headers["If-None-Match"] = etag

    try:
        with urlopen(Request(url, headers=headers), timeout=60) as response:
            content = response.read()
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
    except HTTPError as error:
        if error.code == 304:
            print("Aucune mise à jour : archive déjà à jour.")
            return False
        raise

    temporary_path = archive_path.with_suffix(".tmp")
    temporary_path.write_bytes(content)
    temporary_path.replace(archive_path)

    manifest_path.write_text(
        json.dumps(
            {
                "source_url": url,
                "etag": etag,
                "last_modified": last_modified,
                "downloaded_at": datetime.now(UTC).isoformat(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "filename": archive_path.name,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("Nouvelle archive enregistrée.")
    return True


if __name__ == "__main__":
    download_if_changed()
