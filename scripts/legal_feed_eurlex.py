"""Connecteur minimal pour un flux RSS/Atom EUR-Lex / Cellar."""

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree


DEFAULT_FEED_URL = "http://publications.europa.eu/webapi/notification/ingestion"
EURLEX_HTML_URL = "https://eur-lex.europa.eu/legal-content/{language}/TXT/HTML/?uri=CELEX:{celex}"
CELLAR_XML_URL = "http://publications.europa.eu/resource/celex/{celex}?language={language}"


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


def extract_celex(document: LegalFeedDocument | ElementTree.Element) -> str | None:
    """Retourne l'identifiant CELEX présent dans une notice EUR-Lex.

    Le flux peut placer l'identifiant dans ``guid``, ``id`` ou dans un
    élément XML imbriqué ``notifEntry:identifier``. On accepte les deux
    formes courantes : ``CELEX:32024R0001`` et ``32024R0001``.
    """
    if isinstance(document, LegalFeedDocument):
        # L'URL de la notice est plus fiable que l'identifiant interne haché.
        candidates = (document.url, document.text, document.document_id)
    else:
        candidates = [" ".join(element.itertext()) for element in document.iter()]
    for candidate in candidates:
        match = re.search(r"CELEX\s*[:/]\s*([0-9]{4,}[A-Z][0-9A-Z.()-]+)", candidate or "", re.I)
        if not match:
            # Un CELEX commence par le numéro de secteur, l'année, puis une
            # lettre de type d'acte (ex. 32024R0001). Cela évite de prendre
            # par erreur les identifiants techniques hexadécimaux du flux.
            match = re.search(r"\b(\d[0-9]{4}[A-Z][0-9]{4,})\b", candidate or "", re.I)
        if match:
            return match.group(1).upper()
    return None


class _HtmlTextExtractor:
    """Petit extracteur HTML sans dépendance supplémentaire."""

    from html.parser import HTMLParser

    class Parser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.parts: list[str] = []
            self.skip_depth = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag.lower() in {"script", "style", "noscript", "svg"}:
                self.skip_depth += 1
            elif tag.lower() in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
                self.parts.append(" ")

        def handle_endtag(self, tag: str) -> None:
            if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
                self.skip_depth -= 1
            elif tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
                self.parts.append(" ")

        def handle_data(self, data: str) -> None:
            if not self.skip_depth:
                self.parts.append(data)


def html_to_text(content: bytes) -> str:
    """Convertit la page HTML EUR-Lex en texte propre pour le chunking."""
    parser = _HtmlTextExtractor.Parser()
    parser.feed(content.decode("utf-8", errors="replace"))
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def build_full_text_url(celex: str, language: str = "FR") -> str:
    """Construit le lien stable EUR-Lex vers le texte intégral HTML."""
    return EURLEX_HTML_URL.format(language=language.upper(), celex=celex)


def fetch_document_text(celex: str, language: str = "FR", timeout: int = 30) -> tuple[str, str]:
    """Télécharge le texte intégral, avec repli sur le XML Cellar officiel."""
    html_url = build_full_text_url(celex, language)
    request = Request(html_url, headers={"Accept": "text/html", "User-Agent": "TrustRAG/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            text = html_to_text(response.read())
        if len(text) >= 200:
            return text, html_url
    except (HTTPError, URLError):
        pass

    # Le endpoint Cellar fournit le XML légal lorsque la page HTML n'est
    # pas disponible (acte récent, traduction absente, etc.).
    xml_url = CELLAR_XML_URL.format(language=language.lower(), celex=celex)
    request = Request(xml_url, headers={"Accept": "application/xml;notice=tree", "User-Agent": "TrustRAG/1.0"})
    with urlopen(request, timeout=timeout) as response:
        root = ElementTree.fromstring(response.read())
    text = re.sub(r"\s+", " ", " ".join(root.itertext())).strip()
    if len(text) < 200:
        raise LegalFeedError(f"Texte intégral EUR-Lex vide pour {celex}.")
    return text, xml_url


def enrich_documents(documents: list[LegalFeedDocument], language: str = "FR", timeout: int = 30) -> list[LegalFeedDocument]:
    """Ajoute le texte intégral à chaque notice, sans bloquer toute la synchro."""
    enriched: list[LegalFeedDocument] = []
    for document in documents:
        celex = extract_celex(document)
        if not celex:
            enriched.append(document)
            continue
        try:
            full_text, full_url = fetch_document_text(celex, language, timeout)
            source_hash = hashlib.sha256(
                "|".join((document.title, full_url, document.modified_at or "", document.effective_at or "", full_text)).encode("utf-8")
            ).hexdigest()
            enriched.append(
                LegalFeedDocument(
                    document_id=f"eurlex-{celex}", title=document.title, url=full_url,
                    text=full_text, modified_at=document.modified_at,
                    effective_at=document.effective_at, status=document.status,
                    source_hash=source_hash,
                )
            )
        except (HTTPError, URLError, ElementTree.ParseError, LegalFeedError) as error:
            # Une notice reste indexable même si son texte n'est momentanément
            # pas publié. Elle sera retentée lors du prochain passage.
            print(f"Texte intégral indisponible pour {celex}: {error}")
            enriched.append(
                LegalFeedDocument(
                    document_id=document.document_id,
                    title=document.title,
                    url=document.url,
                    text=document.text,
                    modified_at=document.modified_at,
                    effective_at=document.effective_at,
                    status="metadata-only",
                    # Le marqueur évite de considérer cette notice comme
                    # définitivement à jour lors du prochain scheduler.
                    source_hash=hashlib.sha256(
                        f"{document.source_hash}|metadata-only".encode("utf-8")
                    ).hexdigest(),
                )
            )
    return enriched


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
        # Certaines notifications placent le CELEX dans un attribut XML
        # (resource/about) plutôt que dans le texte de ``guid``.
        entry_serialized = ElementTree.tostring(entry, encoding="unicode")
        celex_match = re.search(
            r"CELEX\s*[:/]\s*(\d[0-9]{4}[A-Z][0-9]{4,})",
            f"{identifier} {url} {entry_serialized}",
            re.IGNORECASE,
        )
        celex = celex_match.group(1).upper() if celex_match else None
        source_hash = hashlib.sha256(
            "|".join((title, url, published or "", effective_at or "", text)).encode("utf-8")
        ).hexdigest()
        documents.append(
            LegalFeedDocument(
                document_id=f"{source}-{celex}" if celex else f"{source}-{document_id}",
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


def fetch_feed(url: str | None = None, timeout: int = 30, enrich_full_text: bool = True) -> list[LegalFeedDocument]:
    """Télécharge le flux EUR-Lex configuré et retourne les documents normalisés."""
    feed_url = url or os.getenv("EURLEX_FEED_URL")
    if not feed_url:
        # Cellar exige une période pour le canal ingestion. On récupère les
        # sept derniers jours afin de garder le connecteur léger.
        start_date = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
        feed_url = (
            f"{DEFAULT_FEED_URL}?startDate={start_date}"
            # ``work`` correspond aux actes juridiques. Les ``event`` sont
            # des notifications techniques sans texte intégral exploitable.
            "&type=UPDATE&wemiClasses=work&page=1"
        )
    # Cellar attend un format unique dans l'en-tête Accept.
    request = Request(feed_url, headers={"Accept": "application/rss+xml"})
    try:
        with urlopen(request, timeout=timeout) as response:
            documents = parse_feed(response.read())
            return enrich_documents(documents, timeout=timeout) if enrich_full_text else documents
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")[:300].strip()
        suffix = f" — {details}" if details else ""
        raise LegalFeedError(f"EUR-Lex a refusé le flux (HTTP {error.code}) : {error.reason}{suffix}") from error
    except URLError as error:
        raise LegalFeedError(f"Flux EUR-Lex inaccessible : {error.reason}") from error


if __name__ == "__main__":
    documents = fetch_feed()
    print(json.dumps([asdict(document) for document in documents], indent=2, ensure_ascii=False))
