"""Synchronise les notices EUR-Lex du flux configuré dans Qdrant."""

import argparse
import asyncio
from dataclasses import asdict

from dotenv import load_dotenv

from scripts.legal_feed_eurlex import fetch_feed
from services.llm import MistralClient
from services.qdrant_store import QdrantStore


load_dotenv()
SOURCE = "eurlex-rss"


async def synchronize(limit: int | None = None) -> dict[str, int]:
    documents = fetch_feed()
    if limit is not None:
        documents = documents[:limit]

    llm = MistralClient()
    qdrant = QdrantStore()
    existing_hashes = qdrant.list_document_hashes(SOURCE)
    indexed = 0
    skipped = 0

    for document in documents:
        if existing_hashes.get(document.document_id) == document.source_hash:
            skipped += 1
            continue
        vector = (await llm.get_embeddings([document.text]))[0]
        payload = asdict(document)
        payload["chunk_index"] = 0
        qdrant.replace_document(
            document_id=document.document_id,
            documents=[payload],
            vectors=[vector],
            source=SOURCE,
        )
        indexed += 1

    result = {"indexed": indexed, "skipped": skipped}
    print(f"Synchronisation EUR-Lex terminée : {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Nombre maximal de notices à traiter.")
    args = parser.parse_args()
    asyncio.run(synchronize(limit=args.limit))
