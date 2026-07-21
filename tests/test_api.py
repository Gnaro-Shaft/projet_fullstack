from fastapi.testclient import TestClient

from services.main import app


class FakeLLM:
    async def get_response(self, message: str) -> str:
        return f"Réponse : {message}"


def test_ping() -> None:
    with TestClient(app) as client:
        response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "pong"}


def test_chat() -> None:
    with TestClient(app) as client:
        app.state.llm = FakeLLM()
        response = client.post("/chat", json={"message": "Bonjour"})

    assert response.status_code == 200
    assert response.json() == {"response": "Réponse : Bonjour"}


def test_chat_rejects_empty_message() -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422
