"""Extract indexable documents from the Service-Public XML archive."""

import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

ARCHIVE_PATH = Path("data/raw/service-public/vosdroits-current.zip")
DC_NAMESPACE = {"dc": "http://purl.org/dc/elements/1.1/"}

MAX_XML_FILES = 10_000
MAX_XML_SIZE = 2_000_000  # 2 MiB per source document


@dataclass
class ServicePublicDocument:
    document_id: str
    title: str
    url: str
    modified_at: str | None
    source_hash: str
    text: str
    chunk_index: int = 0


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_into_chunks(text: str, size: int = 1_200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks, preferring sentence boundaries."""
    if size <= overlap:
        raise ValueError("Chunk size must be greater than overlap.")

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            sentence_end = text.rfind(". ", start, end)
            if sentence_end > start + size // 2:
                end = sentence_end + 1

        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - overlap

    return [chunk for chunk in chunks if chunk]


def extract_documents(archive_path: Path = ARCHIVE_PATH) -> list[ServicePublicDocument]:
    """Extract content chunks from F*.xml publications in an archive."""
    documents = []
    with zipfile.ZipFile(archive_path) as archive:
        xml_files = [
            entry
            for entry in archive.infolist()
            if entry.filename.startswith("F") and entry.filename.endswith(".xml")
        ]
        if len(xml_files) > MAX_XML_FILES:
            raise ValueError("Too many XML files in the archive.")

        for entry in xml_files:
            if entry.file_size > MAX_XML_SIZE:
                continue

            raw_xml = archive.read(entry)
            root = ElementTree.fromstring(raw_xml)
            if root.tag != "Publication":
                continue

            document_id = root.attrib.get("ID")
            title = root.findtext("dc:title", namespaces=DC_NAMESPACE)
            body = " ".join(
                " ".join(node.itertext())
                for node in (root.find("Introduction"), root.find("ListeSituations"))
                if node is not None
            )
            text = normalize_text(body)
            if not document_id or not title or not text:
                continue

            source_hash = hashlib.sha256(raw_xml).hexdigest()
            for index, chunk in enumerate(split_into_chunks(text)):
                documents.append(
                    ServicePublicDocument(
                        document_id=document_id,
                        title=normalize_text(title),
                        url=root.attrib.get("spUrl", ""),
                        modified_at=root.findtext("dc:date", namespaces=DC_NAMESPACE),
                        source_hash=source_hash,
                        text=chunk,
                        chunk_index=index,
                    )
                )
    return documents


if __name__ == "__main__":
    documents = extract_documents()
    print(f"{len(documents)} fragments extraits.")
