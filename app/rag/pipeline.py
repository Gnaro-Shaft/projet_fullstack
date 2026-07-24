import asyncio
from dataclasses import dataclass
from typing import Any

from app.audit import AuditLogger
from app.llm import MistralClient
from app.pii import PIIAnonymizer
from app.qdrant_store import QdrantStore
from app.reranker import rerank_results


@dataclass
class RagResult:
    response: str
    sources: list[dict[str, Any]]
    anonymized_question: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class RagPipeline:
    def __init__(
        self,
        llm: MistralClient,
        qdrant: QdrantStore,
        pii: PIIAnonymizer,
        audit: AuditLogger,
        top_k: int = 8,
        search_limit: int = 30,
    ) -> None:
        self.llm = llm
        self.qdrant = qdrant
        self.pii = pii
        self.audit = audit
        self.top_k = top_k
        self.search_limit = search_limit

    async def execute(self, message: str, min_relevance: float = 0.4, min_title_keyword: float = 0.2) -> RagResult:
        anonymized = self.pii.anonymize(message).text

        vector = (await self.llm.get_embeddings([anonymized]))[0]
        candidates = await asyncio.to_thread(self.qdrant.search, vector, self.search_limit)

        context_chunks = rerank_results(message, candidates, top_k=self.top_k, deduplicate=False)
        source_chunks = rerank_results(message, context_chunks, top_k=self.top_k, deduplicate=True)

        good_chunks = [
            c for c in context_chunks
            if c.get("rerank_score", 0) >= min_relevance
            and c.get("title_keyword_score", 0) >= min_title_keyword
        ]
        if not good_chunks:
            no_result = "Je ne trouve pas cette information dans les documents disponibles."
            return RagResult(response=no_result, sources=[], anonymized_question=anonymized)

        context_chunks = good_chunks
        source_chunks = rerank_results(message, context_chunks, top_k=self.top_k, deduplicate=True)

        llm_context = self._format_context(context_chunks)
        llm_result = await self.llm.get_response(anonymized, llm_context)
        safe_response = self.pii.anonymize(llm_result.text).text

        _NO_SOURCE_PATTERNS = ["ne peux pas répondre", "ne trouve pas", "ne concerne pas"]
        if any(p in safe_response.lower() for p in _NO_SOURCE_PATTERNS):
            public_sources = []
        else:
            public_sources = [{k: v for k, v in s.items() if k != "text"} for s in source_chunks]
        return RagResult(
            response=safe_response, sources=public_sources,
            anonymized_question=anonymized,
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
        )

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
