import asyncio
import json

from scripts.evaluate_golden_set import evaluate_golden_set


class FakeLLM:
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeQdrant:
    def search(self, vector, limit=12):
        return [
            {"document_id": "F869", "text": "logement social conditions", "score": 0.9},
            {"document_id": "F999", "text": "information générale", "score": 0.8},
        ]


def test_golden_set_calculates_recall(tmp_path) -> None:
    golden_path = tmp_path / "golden.json"
    golden_path.write_text(
        json.dumps(
            [
                {
                    "question": "Quelles sont les conditions pour obtenir un logement social ?",
                    "expected_document_id": "F869",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = asyncio.run(evaluate_golden_set(FakeLLM(), FakeQdrant(), golden_path))

    assert result["recall_at_k"] == 1.0
    assert result["hits"] == 1
