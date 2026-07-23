"""Connecteur minimal pour un flux RSS/Atom EUR-Lex / Cellar."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree


DEFAULT_FEED_URL = "http://publications.europa.eu/webapi/notification/ingestion"


class LegalFeedError(Exception):
    """Erreur explicite du connecteur Legal Feeds."""


@dataclass
class LegalFeedDocument:
    """Document normalisé, prêt à être envoyé au pipeline d'embeddings."""

    document_id: str
    title: str
    url: str
    text: str
    modified_at: str | None
    effective_at: str | None
    status: str
    source_hash: str


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ElementTree.Element, names: set[str]) -> str | None:
    for child in element.iter():
        if _local_name(child.tag) in names and child.text and child.text.strip():
            return " ".join(child.text.split())
    return None


def parse_feed(xml_content: bytes, source: str = "eurlex") -> list[LegalFeedDocument]:
    """Parse un flux RSS ou Atom sans dépendance externe."""
    root = ElementTree.fromstring(xml_content)
    entries = [element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}]
    documents = []
    for index, entry in enumerate(entries):
        title = _child_text(entry, {"title"}) or f"EUR-Lex document {index + 1}"
        url = _child_text(entry, {"link", "id", "identifier"}) or ""
        for child in entry:
            if _local_name(child.tag) == "link" and child.attrib.get("href"):
                url = child.attrib["href"]
                break
        identifier = _child_text(entry, {"guid", "id", "identifier"}) or url or f"item-{index}"
        document_id = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:16]
        published = _child_text(entry, {"pubdate", "published", "updated", "date"})
        effective_at = _child_text(entry, {"effectivedate", "inforcefrom", "entryintoforce"})
        summary = _child_text(entry, {"description", "summary", "content"}) or ""
        text = f"{title}. {summary}".strip()
        source_hash = hashlib.sha256(
            "|".join((title, url, published or "", effective_at or "", text)).encode("utf-8")
        ).hexdigest()
        documents.append(
            LegalFeedDocument(
                document_id=f"{source}-{document_id}",
                title=title,
                url=url,
                text=text,
                modified_at=published,
                effective_at=effective_at,
                status="published",
                source_hash=source_hash,
            )
        )
    return documents


def fetch_feed(url: str | None = None, timeout: int = 30) -> list[LegalFeedDocument]:
    """Télécharge le flux EUR-Lex configuré et retourne les documents normalisés."""
    feed_url = url or os.getenv("EURLEX_FEED_URL")
    if not feed_url:
        # Cellar exige une période pour le canal ingestion. On récupère les
        # sept derniers jours afin de garder le connecteur léger.
        start_date = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
        feed_url = (
            f"{DEFAULT_FEED_URL}?startDate={start_date}"
            "&type=UPDATE&wemiClasses=work,event&page=1"
        )
    # Cellar attend un format unique dans l'en-tête Accept.
    request = Request(feed_url, headers={"Accept": "application/rss+xml"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return parse_feed(response.read())
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")[:300].strip()
        suffix = f" — {details}" if details else ""
        raise LegalFeedError(f"EUR-Lex a refusé le flux (HTTP {error.code}) : {error.reason}{suffix}") from error
    except URLError as error:
        raise LegalFeedError(f"Flux EUR-Lex inaccessible : {error.reason}") from error


if __name__ == "__main__":
    documents = fetch_feed()
    print(json.dumps([asdict(document) for document in documents], indent=2, ensure_ascii=False))
