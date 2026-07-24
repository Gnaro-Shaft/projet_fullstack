"""Mesure la qualité du retrieval sur les questions de référence."""

import argparse
import asyncio
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.llm import MistralClient
from app.qdrant_store import QdrantStore
from app.reranker import rerank_results

load_dotenv()

GOLDEN_SET_PATH = Path("tests/fixtures/golden_set.json")
EVAL_HISTORY_PATH = Path(os.getenv("EVAL_HISTORY_PATH", "data/eval_history.json"))


async def evaluate_golden_set(
    llm: MistralClient,
    qdrant: QdrantStore,
    golden_set_path: Path = GOLDEN_SET_PATH,
    top_k: int = 5,
) -> dict[str, Any]:
    """Retourne le Hit@k, MRR et le détail de chaque question testée."""
    questions = json.loads(golden_set_path.read_text(encoding="utf-8"))
    details = []

    for item in questions:
        question = item["question"]
        expected_id = item["expected_document_id"]

        query_vector = (await llm.get_embeddings([question]))[0]
        candidates = qdrant.search(query_vector, limit=12)
        sources = rerank_results(question, candidates, top_k=max(top_k, 5))
        retrieved_ids = [source.get("document_id") for source in sources]

        rank = next(
            (i + 1 for i, rid in enumerate(retrieved_ids) if rid == expected_id),
            None,
        )

        details.append(
            {
                "question": question,
                "expected_document_id": expected_id,
                "retrieved_document_ids": retrieved_ids,
                "hit": expected_id in retrieved_ids,
                "hit_at_1": expected_id in retrieved_ids[:1],
                "hit_at_3": expected_id in retrieved_ids[:3],
                "hit_at_5": expected_id in retrieved_ids[:5],
                "rank": rank,
                "reciprocal_rank": 1.0 / rank if rank else 0.0,
            }
        )

    total = len(details)
    hits = sum(d["hit"] for d in details)
    rr_sum = sum(d["reciprocal_rank"] for d in details)
    return {
        "hit_at_k": hits / total if total else 0.0,
        "k": top_k,
        "hit_at_1": sum(d["hit_at_1"] for d in details) / total if total else 0.0,
        "hit_at_3": sum(d["hit_at_3"] for d in details) / total if total else 0.0,
        "hit_at_5": sum(d["hit_at_5"] for d in details) / total if total else 0.0,
        "mrr": rr_sum / total if total else 0.0,
        "hits": hits,
        "total": total,
        "details": details,
    }


async def main(top_k: int = 5) -> None:
    result = await evaluate_golden_set(MistralClient(), QdrantStore(), top_k=top_k)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    commit = "unknown"
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        pass
    history_entry = {
        "type": "retrieval",
        "timestamp": datetime.now(UTC).isoformat(),
        "commit": commit,
        "summary": {
            "hit_at_1": result["hit_at_1"],
            "hit_at_3": result["hit_at_3"],
            "hit_at_5": result["hit_at_5"],
            "mrr": result["mrr"],
            "k": top_k,
            "total": result["total"],
        },
        "params": {"top_k": top_k},
    }
    EVAL_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = json.loads(EVAL_HISTORY_PATH.read_text(encoding="utf-8")) if EVAL_HISTORY_PATH.exists() else []
    history.append(history_entry)
    EVAL_HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Historique sauvegardé : {EVAL_HISTORY_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.top_k))
