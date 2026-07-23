import asyncio
from dataclasses import dataclass, field
from typing import Any

from services.audit import AuditLogger
from services.llm import MistralClient
from services.pii import PIIAnonymizer
from services.qdrant_store import QdrantStore
from services.reranker import rerank_results


@dataclass
class RagResult:
    response: str
    sources: list[dict[str, Any]]


class RagPipeline:
    def __init__(
        self,
        llm: MistralClient,
        qdrant: QdrantStore,
        pii: PIIAnonymizer,
        audit: AuditLogger,
        top_k: int = 8,
        search_limit: int = 12,
    ) -> None:
        self.llm = llm
        self.qdrant = qdrant
        self.pii = pii
        self.audit = audit
        self.top_k = top_k
        self.search_limit = search_limit

    async def execute(self, message: str) -> RagResult:
        anonymized = self.pii.anonymize(message).text

        vector = (await self.llm.get_embeddings([anonymized]))[0]
        candidates = await asyncio.to_thread(self.qdrant.search, vector, self.search_limit)

        context_chunks = rerank_results(message, candidates, top_k=self.top_k, deduplicate=False)
        source_chunks = rerank_results(message, context_chunks, top_k=self.top_k, deduplicate=True)

        if not context_chunks:
            no_result = "Je ne trouve pas cette information dans les documents disponibles."
            self.audit.record_chat(anonymized, no_result, [])
            return RagResult(response=no_result, sources=[])

        llm_context = self._format_context(context_chunks)
        response = await self.llm.get_response(anonymized, llm_context)
        response = self.pii.anonymize(response).text

        public_sources = [{k: v for k, v in s.items() if k != "text"} for s in source_chunks]
        self.audit.record_chat(anonymized, response, public_sources)

        return RagResult(response=response, sources=public_sources)

    @staticmethod
    def _format_context(chunks: list[dict[str, Any]]) -> list[str]:
        return [
            (
                f"Titre : {chunk.get('title') or 'Non précisé'}\n"
                f"Source : {chunk.get('source') or 'Non précisée'}\n"
                f"Date de mise à jour : {chunk.get('modified_at') or 'Non précisée'}\n"
                f"URL : {chunk.get('url') or 'Non précisée'}\n"
                f"Contenu : {chunk['text']}"
            )
            for chunk in chunks
        ]
