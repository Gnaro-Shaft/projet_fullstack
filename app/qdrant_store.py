import os
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from qdrant_client import QdrantClient, models


class QdrantStoreError(Exception):
    """Raised when Qdrant cannot store or retrieve documents."""


class QdrantStore:
    def __init__(self, url: str | None = None, api_key: str | None = None, collection_name: str | None = None) -> None:
        self.url = url or os.getenv("QDRANT_URL")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "documents")
        if not self.url:
            raise QdrantStoreError("QDRANT_URL is not configured.")
        self.client = (
            QdrantClient(":memory:")
            if self.url == ":memory:"
            else QdrantClient(url=self.url, api_key=self.api_key, timeout=10)
        )

    def healthcheck(self) -> None:
        try:
            self.client.get_collections()
        except Exception as error:
            raise QdrantStoreError("Qdrant is unavailable.") from error

    def _ensure_collection(self, vector_size: int) -> None:
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )

            # Les index sont nécessaires aux filtres utilisés pendant la synchronisation.
            self._ensure_payload_indexes()
        except Exception as error:
            raise QdrantStoreError(
                "Unable to initialise the Qdrant collection."
            ) from error

    def upsert(self, documents: list[dict[str, Any]], vectors: list[list[float]]) -> int:
        if len(documents) != len(vectors) or not vectors:
            raise QdrantStoreError("Documents and embeddings must have the same non-zero length.")
        self._ensure_collection(len(vectors[0]))
        points = [models.PointStruct(id=str(uuid4()), vector=vector, payload={"text": document["text"], "metadata": document.get("metadata", {})}) for document, vector in zip(documents, vectors, strict=True)]
        try:
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
        except Exception as error:
            raise QdrantStoreError("Unable to store documents in Qdrant.") from error
        return len(points)

    def replace_document(
        self,
        document_id: str,
        documents: list[dict[str, Any]],
        vectors: list[list[float]],
        source: str,
    ) -> int:
        """Replace every indexed chunk for a source document atomically enough for syncs."""
        if len(documents) != len(vectors) or not vectors:
            raise QdrantStoreError("Documents and embeddings must have the same non-zero length.")
        if any(document.get("document_id") != document_id for document in documents):
            raise QdrantStoreError("Every chunk must belong to the requested document.")

        self._ensure_collection(len(vectors[0]))
        document_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                ),
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=source),
                ),
            ]
        )
        points = [
            models.PointStruct(
                # Qdrant point ids are integers or UUIDs. UUID v5 stays stable across syncs.
                id=str(uuid5(NAMESPACE_URL, f"{source}:{document_id}:{document['chunk_index']}")),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "chunk_index": document["chunk_index"],
                    "title": document["title"],
                    "url": document["url"],
                    "modified_at": document["modified_at"],
                    "effective_at": document.get("effective_at"),
                    "status": document.get("status", "published"),
                    "source_hash": document["source_hash"],
                    "text": document["text"],
                    "source": source,
                },
            )
            for document, vector in zip(documents, vectors, strict=True)
        ]
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=document_filter),
                wait=True,
            )
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
        except Exception as error:
            raise QdrantStoreError(f"Unable to replace document {document_id} in Qdrant.") from error
        return len(points)

    def list_document_hashes(self, source: str) -> dict[str, str]:
        """Return the latest indexed content hash for every document of a source."""
        if not self.client.collection_exists(self.collection_name):
            return {}

        self._ensure_payload_indexes()
        hashes = {}
        offset = None
        try:
            while True:
                records, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="source",
                                match=models.MatchValue(value=source),
                            )
                        ]
                    ),
                    with_payload=["document_id", "source_hash"],
                    limit=256,
                    offset=offset,
                )
                for record in records:
                    hashes[record.payload["document_id"]] = record.payload["source_hash"]
                if offset is None:
                    return hashes
        except Exception as error:
            raise QdrantStoreError("Unable to read document versions from Qdrant.") from error

    def delete_document(self, document_id: str, source: str) -> None:
        document_filter = models.Filter(
            must=[
                models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
                models.FieldCondition(key="source", match=models.MatchValue(value=source)),
            ]
        )
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=document_filter),
                wait=True,
            )
        except Exception as error:
            raise QdrantStoreError(f"Unable to delete document {document_id} from Qdrant.") from error

    def search(self, vector: list[float], limit: int = 12) -> list[dict[str, Any]]:
        """Retourne les candidats Qdrant avec leurs métadonnées de source."""
        try:
            hits = self.client.query_points(collection_name=self.collection_name, query=vector, limit=limit, with_payload=True).points
        except Exception as error:
            raise QdrantStoreError("Unable to search Qdrant.") from error
        results = []
        for hit in hits:
            payload = hit.payload or {}
            title = payload.get("title")
            # Compatibilité avec les anciennes notices indexées avant la
            # correction du connecteur EUR-Lex.
            if not title or str(title).startswith("$item."):
                title = f"Acte EUR-Lex {payload.get('document_id', 'inconnu').removeprefix('eurlex-')}"
            results.append(
                {
                    "text": payload.get("text", ""),
                    "document_id": payload.get("document_id"),
                    "title": title,
                    "url": (payload.get("url") or "").replace("service-public.gouv.fr", "service-public.fr"),
                    "modified_at": payload.get("modified_at"),
                    "effective_at": payload.get("effective_at"),
                    "status": payload.get("status"),
                    "source": payload.get("source"),
                    "metadata": payload.get("metadata", {}),
                    "score": hit.score,
                }
            )
        return results

    def _ensure_payload_indexes(self) -> None:
        for field_name in ("document_id", "source"):
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
                wait=True,
            )
