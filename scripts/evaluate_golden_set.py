"""Mesure la qualité du retrieval sur les questions de référence."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.llm import MistralClient
from app.qdrant_store import QdrantStore
from app.reranker import rerank_results

load_dotenv()

GOLDEN_SET_PATH = Path("tests/fixtures/golden_set.json")


async def evaluate_golden_set(
    llm: MistralClient,
    qdrant: QdrantStore,
    golden_set_path: Path = GOLDEN_SET_PATH,
    top_k: int = 4,
) -> dict[str, Any]:
    """Retourne le recall@k et le détail de chaque question testée."""
    questions = json.loads(golden_set_path.read_text(encoding="utf-8"))
    details = []

    for item in questions:
        question = item["question"]
        expected_id = item["expected_document_id"]

        # Même étape d'embedding que pour une vraie question utilisateur.
        query_vector = (await llm.get_embeddings([question]))[0]
        candidates = qdrant.search(query_vector, limit=12)
        sources = rerank_results(question, candidates, top_k=top_k)
        retrieved_ids = [source.get("document_id") for source in sources]

        details.append(
            {
                "question": question,
                "expected_document_id": expected_id,
                "retrieved_document_ids": retrieved_ids,
                "hit": expected_id in retrieved_ids,
            }
        )

    hits = sum(detail["hit"] for detail in details)
    return {
        "recall_at_k": hits / len(details) if details else 0.0,
        "k": top_k,
        "hits": hits,
        "total": len(details),
        "details": details,
    }


async def main(top_k: int = 4) -> None:
    result = await evaluate_golden_set(MistralClient(), QdrantStore(), top_k=top_k)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=4)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.top_k))
