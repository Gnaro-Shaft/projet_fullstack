"""Synchronise les notices EUR-Lex du flux configuré dans Qdrant."""

import argparse
import asyncio
from dataclasses import asdict

from dotenv import load_dotenv

from scripts.extract_service_public import split_into_chunks
from scripts.legal_feed_eurlex import enrich_documents, fetch_feed
from services.llm import MistralAPIError, MistralClient
from services.qdrant_store import QdrantStore


load_dotenv()
SOURCE = "eurlex-rss"
EMBEDDING_BATCH_SIZE = 8


async def embed_with_retry(llm: MistralClient, texts: list[str], attempts: int = 4) -> list[list[float]] | None:
    """Réessaie les lots après un 429, puis reporte le document."""
    for attempt in range(attempts):
        try:
            vectors: list[list[float]] = []
            for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                vectors.extend(
                    await llm.get_embeddings(texts[start : start + EMBEDDING_BATCH_SIZE])
                )
                # Petit espace entre lots pour respecter les limites de débit.
                if start + EMBEDDING_BATCH_SIZE < len(texts):
                    await asyncio.sleep(0.5)
            return vectors
        except MistralAPIError as error:
            if "429" not in str(error):
                raise
            delay = 2 ** attempt
            print(f"Limite Mistral atteinte, nouvelle tentative dans {delay}s.")
            await asyncio.sleep(delay)
    print("Limite Mistral toujours atteinte : document reporté.")
    return None


async def synchronize(
    limit: int | None = None,
    enrich_full_text: bool = True,
    force: bool = False,
) -> dict[str, int]:
    # On limite avant le téléchargement des textes complets : un flux peut
    # contenir plusieurs centaines de notices et chaque texte est coûteux.
    documents = fetch_feed(enrich_full_text=False)
    if limit is not None:
        documents = documents[:limit]
    if enrich_full_text:
        documents = enrich_documents(documents)

    llm = MistralClient()
    qdrant = QdrantStore()
    existing_hashes = qdrant.list_document_hashes(SOURCE)
    indexed = 0
    skipped = 0

    for document in documents:
        if not force and existing_hashes.get(document.document_id) == document.source_hash:
            skipped += 1
            continue
        # Les règlements peuvent être longs : on les découpe comme le corpus
        # Service-Public afin de garder des passages précis au moment du RAG.
        chunks = split_into_chunks(document.text)
        payloads = []
        for chunk_index, chunk_text in enumerate(chunks):
            payload = asdict(document)
            payload["text"] = chunk_text
            payload["chunk_index"] = chunk_index
            payloads.append(payload)
        # Mistral impose une limite de tokens par requête. Un acte européen
        # peut contenir beaucoup de fragments : on envoie donc plusieurs
        # petits lots au lieu de tout transmettre en une seule fois.
        texts = [payload["text"] for payload in payloads]
        vectors = await embed_with_retry(llm, texts)
        if vectors is None:
            skipped += 1
            continue
        qdrant.replace_document(
            document_id=document.document_id,
            documents=payloads,
            vectors=vectors,
            source=SOURCE,
        )
        indexed += 1

    result = {"indexed": indexed, "skipped": skipped}
    print(f"Synchronisation EUR-Lex terminée : {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Nombre maximal de notices à traiter.")
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="N'utilise que les notices (secours si EUR-Lex est temporairement indisponible).",
    )
    parser.add_argument(
        "--force-full-text",
        action="store_true",
        help="Réindexe les notices déjà présentes pour tenter le téléchargement complet.",
    )
    args = parser.parse_args()
    asyncio.run(
        synchronize(
            limit=args.limit,
            enrich_full_text=not args.metadata_only,
            force=args.force_full_text,
        )
    )
