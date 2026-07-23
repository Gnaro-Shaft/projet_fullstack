from fastapi.testclient import TestClient

from services.main import app


class FakeLLM:
    async def get_response(self, message: str, context=None) -> str:
        return f"Réponse : {message}"

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class FakeQdrant:
    deleted = []

    def healthcheck(self) -> None:
        return None

    def upsert(self, documents, vectors) -> int:
        return len(documents)

    def search(self, vector, limit=4):
        return [{"text": "Paris est la capitale de la France.", "metadata": {}, "score": 0.99}]

    def delete_document(self, document_id, source):
        self.deleted.append((document_id, source))


def test_ping() -> None:
    with TestClient(app) as client:
        response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "pong"}


def test_chat() -> None:
    with TestClient(app) as client:
        app.state.llm = FakeLLM()
        app.state.qdrant = FakeQdrant()
        response = client.post("/chat", json={"message": "Bonjour"})

    assert response.status_code == 200
    assert response.json()["response"] == "Réponse : Bonjour"
    assert response.json()["sources"][0]["score"] == 0.99


def test_chat_rejects_empty_message() -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


def test_index_documents() -> None:
    with TestClient(app) as client:
        app.state.llm = FakeLLM()
        app.state.qdrant = FakeQdrant()
        response = client.post("/documents", json={"documents": [{"text": "Paris est en France."}]})

    assert response.status_code == 201
    assert response.json() == {"indexed": 1}


def test_delete_document(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    fake_qdrant = FakeQdrant()
    with TestClient(app) as client:
        app.state.llm = FakeLLM()
        app.state.qdrant = fake_qdrant
        response = client.delete(
            "/documents/F123?source=service-public-vdd",
            headers={"X-Admin-Key": "test-admin-key"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "F123",
        "source": "service-public-vdd",
        "deleted": True,
    }
    assert fake_qdrant.deleted == [("F123", "service-public-vdd")]


def test_delete_document_requires_admin_key(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    with TestClient(app) as client:
        response = client.delete("/documents/F123")

    assert response.status_code == 403
