"""Incrementally synchronise the Service-Public XML archive into Qdrant."""

import asyncio
import argparse
from collections import defaultdict
from dataclasses import asdict

from scripts.download_service_public import download_if_changed
from scripts.extract_service_public import extract_documents
from services.llm import MistralClient
from services.qdrant_store import QdrantStore

from dotenv import load_dotenv

load_dotenv()

SOURCE = "service-public-vdd"
EMBEDDING_BATCH_SIZE = 32


async def create_embeddings(llm: MistralClient, texts: list[str]) -> list[list[float]]:
    vectors = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        vectors.extend(await llm.get_embeddings(texts[start : start + EMBEDDING_BATCH_SIZE]))
    return vectors


async def synchronize(
    llm: MistralClient | None = None,
    qdrant: QdrantStore | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, int | bool]:
    """Download, extract, and update only documents whose source content changed."""
    if offset < 0 or (limit is not None and limit <= 0):
        raise ValueError("offset must be positive and limit must be greater than zero.")
    changed = download_if_changed()
    grouped_documents = defaultdict(list)

    for document in extract_documents():
        grouped_documents[document.document_id].append(document)

    document_groups = list(grouped_documents.items())

    if limit is not None:
        document_groups = document_groups[offset : offset + limit]
    elif offset:
        document_groups = document_groups[offset:]

    llm = llm or MistralClient()
    qdrant = qdrant or QdrantStore()
    existing_hashes = qdrant.list_document_hashes(SOURCE)
    indexed = 0
    skipped = 0

    for document_id, chunks in document_groups:
        if existing_hashes.get(document_id) == chunks[0].source_hash:
            skipped += 1
            continue

        vectors = await create_embeddings(llm, [chunk.text for chunk in chunks])
        qdrant.replace_document(
            document_id=document_id,
            documents=[asdict(chunk) for chunk in chunks],
            vectors=vectors,
            source=SOURCE,
        )
        indexed += 1

    deleted_ids = set()

    if limit is None and offset == 0:
        deleted_ids = set(existing_hashes) - set(document_id for document_id, _ in document_groups)
    for document_id in deleted_ids:
        qdrant.delete_document(document_id, SOURCE)

    result = {
        "archive_changed": changed,
        "indexed": indexed,
        "skipped": skipped,
        "deleted": len(deleted_ids),
    }
    print(f"Synchronisation terminée : {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        help="Nombre maximal de fiches à indexer pour un test.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Position de départ dans les fiches à traiter.",
    )
    args = parser.parse_args()

    asyncio.run(synchronize(limit=args.limit, offset=args.offset))
