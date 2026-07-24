"""Test d'intégration avec Qdrant réel (Docker) et pipeline complet.

Ce test nécessite Qdrant accessible via QDRANT_URL (par défaut http://localhost:6333).
Il utilise un FakeLLM pour éviter la dépendance à l'API Mistral en CI.
"""

import asyncio
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from app.audit import AuditLogger
from app.llm import LlmResponse
from app.main import app
from app.pii import PIIAnonymizer
from app.qdrant_store import QdrantStore
from app.qdrant_store import QdrantStoreError
from app.rag.pipeline import RagPipeline


class FakeLLM:
    def __init__(self, embeddings_dim: int = 4):
        self.embeddings_dim = embeddings_dim

    async def get_response(self, message: str, context=None) -> LlmResponse:
        if context:
            titles = []
            for c in context:
                for line in c.split("\n"):
                    if line.startswith("Titre :"):
                        titles.append(line.replace("Titre : ", "").strip())
            sources = ", ".join(titles) if titles else "documents"
            text = f"Réponse basée sur : {sources}"
        else:
            text = "Réponse sans contexte."
        return LlmResponse(text=text, input_tokens=10, output_tokens=5)

    async def get_response_stream(self, message: str, context=None):
        full = (await self.get_response(message, context)).text
        for char in full:
            yield char

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.embeddings_dim for _ in texts]


def _await(coro):
    return asyncio.run(coro)


def _wait_for_qdrant(url: str, timeout: int = 30) -> bool:
    """Attend que Qdrant soit joignable (loop avec retry)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            QdrantStore(url=url, collection_name="test_health").healthcheck()
            return True
        except QdrantStoreError:
            time.sleep(1)
    return False


@pytest.fixture
def qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333")


@pytest.fixture
def integration_rag(qdrant_url: str, monkeypatch) -> RagPipeline:
    if not _wait_for_qdrant(qdrant_url):
        pytest.skip(f"Qdrant inaccessible sur {qdrant_url}")
    monkeypatch.setenv("QDRANT_URL", qdrant_url)
    monkeypatch.setenv("QDRANT_COLLECTION", "test_integration")
    monkeypatch.setenv("ADMIN_API_KEY", "integration-test-key")
    llm = FakeLLM(embeddings_dim=4)
    qdrant = QdrantStore(url=qdrant_url, collection_name="test_integration")
    pii = PIIAnonymizer(enable_ner=False)
    audit = AuditLogger(path="/tmp/test_audit_integration.jsonl")
    return RagPipeline(llm=llm, qdrant=qdrant, pii=pii, audit=audit)


@pytest.mark.integration
def test_index_and_search(integration_rag: RagPipeline) -> None:
    pipeline = integration_rag
    texts = ["Paris est la capitale de la France.", "Lyon est une ville française."]
    vectors = _await(pipeline.llm.get_embeddings(texts))
    docs = [{"text": t, "metadata": {"source": "test"}} for t in texts]
    indexed = pipeline.qdrant.upsert(docs, vectors)
    assert indexed == 2


@pytest.mark.integration
def test_chat_endpoint(integration_rag: RagPipeline) -> None:
    pipeline = integration_rag
    texts = [
        "Le RSA est versé sous conditions de ressources.",
        "Le montant du RSA dépend de la composition du foyer.",
    ]
    vectors = _await(pipeline.llm.get_embeddings(texts))
    docs = [{"text": t, "metadata": {"source": "test", "document_id": "F000"}} for t in texts]
    pipeline.qdrant.upsert(docs, vectors)

    with TestClient(app) as client:
        app.state.rag = pipeline
        response = client.post("/chat", json={"message": "RSA conditions"})

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0


def test_healthcheck_returns_200_with_fake_llm() -> None:
    """Le healthcheck retourne 200 car FakeLLM répond (pas d'exception API)."""
    with TestClient(app) as client:
        app.state.rag = RagPipeline(
            llm=FakeLLM(),
            qdrant=QdrantStore(url=":memory:", collection_name="test_health_fake"),
            pii=PIIAnonymizer(enable_ner=False),
            audit=AuditLogger(path="/tmp/test_audit_health.jsonl"),
        )
        response = client.get("/health")
    assert response.status_code == 200
    detail = json.loads(response.json()["detail"])
    assert detail["llm"] == "unexpected"


@pytest.mark.integration
def test_delete_document(integration_rag: RagPipeline, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "integration-test-key")
    pipeline = integration_rag
    doc_id = "F999"
    text = "Document a supprimer."
    vector = _await(pipeline.llm.get_embeddings([text]))
    pipeline.qdrant.replace_document(
        document_id=doc_id,
        documents=[{"document_id": doc_id, "chunk_index": 0, "title": "Test", "url": "", "modified_at": "", "source_hash": "abc", "text": text}],
        vectors=vector,
        source="test-source",
    )

    with TestClient(app) as client:
        app.state.rag = pipeline
        response = client.delete(
            f"/documents/{doc_id}?source=test-source",
            headers={"X-Admin-Key": "integration-test-key"},
        )
    assert response.status_code == 200
    assert response.json()["deleted"] is True
