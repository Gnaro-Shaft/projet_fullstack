"""Évaluation multidimensionnelle de la qualité des réponses RAG.

Mesure 4 dimensions via LLM-as-judge + vérifications automatisées :
  - retrieval_success : le document attendu est-il dans les sources ?
  - faithfulness      : la réponse reste-t-elle fidèle au contexte ?
  - completeness      : les faits attendus sont-ils couverts ?
  - hallucination     : la réponse invente-t-elle des informations ?
  - source_usage      : les sources sont-elles correctement citées ?
"""

import argparse
import asyncio
import json
import logging
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
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("rag_eval")

GOLDEN_SET_PATH = Path("tests/fixtures/golden_set.json")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "mistral-small-latest")

JUDGE_SYSTEM_PROMPT = """Tu évalues la qualité d'une réponse générée par un assistant RAG.

Tu reçois :
- Une **question** utilisateur
- Un **contexte** (les documents sources fournis à l'assistant)
- Une **réponse** de l'assistant

Tu dois noter chaque dimension de 0 à 5 :

1. **faithfulness** (fidélité au contexte) :
   - 5 : Tous les faits de la réponse sont présents dans le contexte.
   - 3 : La plupart des faits sont dans le contexte, 1-2 éléments mineurs ne le sont pas.
   - 0 : La réponse ignore complètement le contexte.

2. **completeness** (complétude par rapport à la question) :
   - 5 : La réponse couvre tous les aspects importants de la question.
   - 3 : La réponse couvre l'essentiel mais oublie des détails utiles.
   - 0 : La réponse ne répond pas à la question posée.

3. **hallucination_absence** (absence d'invention) :
   - 5 : Aucune information inventée. Tout est dans le contexte.
   - 3 : 1-2 éléments mineurs non présents dans le contexte, mais non contradictoires.
   - 0 : La réponse contient des informations fausses ou inventées majeures.

4. **source_usage** (citation des sources) :
   - 5 : Les sources sont correctement citées avec titres, dates ou URLs.
   - 3 : Les sources sont mentionnées mais de façon vague.
   - 0 : Aucune mention des sources.

Réponds UNIQUEMENT avec un objet JSON valide :
{"faithfulness": <int>, "completeness": <int>, "hallucination_absence": <int>, "source_usage": <int>, "explanation": "<brève justification>"}"""


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


async def fetch_chat_response(question: str) -> dict[str, Any]:
    import httpx

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(f"{BACKEND_URL}/chat", json={"message": question})
        response.raise_for_status()
        return response.json()


async def judge_response(llm: MistralClient, question: str, response: str, context: list[str]) -> dict[str, Any]:
    judge_prompt = f"""Question : {question}

Contexte (documents sources) :
{"".join(f"\n--- Document {i+1} ---\n{doc}" for i, doc in enumerate(context))}

Réponse de l'assistant :
{response}"""
    try:
        result = (await llm.get_response(judge_prompt, context=[JUDGE_SYSTEM_PROMPT])).text
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1]
            result = result.rsplit("\n```", 1)[0]
        first_brace = result.find("{")
        last_brace = result.rfind("}")
        if first_brace != -1 and last_brace != -1:
            result = result[first_brace : last_brace + 1]
        return json.loads(result)
    except Exception as e:
        logger.warning("Judge failed for question: %s", e)
        return {"faithfulness": 1, "completeness": 3, "hallucination_absence": 1, "source_usage": 1, "explanation": f"Judge parse error (fallback): {e}"}


def evaluation_from_sources(sources: list[dict], expected_doc_id: str, expected_key_facts: list[str]) -> dict[str, Any]:
    retrieved_ids = [s.get("document_id") for s in sources]
    retrieval_success = expected_doc_id in retrieved_ids
    all_text = " ".join(s.get("text", "") + " " + s.get("title", "") for s in sources)
    facts_found = sum(1 for fact in expected_key_facts if fact.lower() in all_text.lower())
    return {
        "retrieval_success": retrieval_success,
        "retrieved_ids": retrieved_ids,
        "expected_id": expected_doc_id,
        "key_facts_coverage": facts_found / len(expected_key_facts) if expected_key_facts else 0.0,
    }


async def replay_rag_pipeline(llm: MistralClient, qdrant: QdrantStore, question: str) -> list[dict[str, Any]]:
    """Rejoue exactement le même pipeline RAG que le endpoint /chat.

    Embedding → search Qdrant → rerank top_k=8 (sans déduplication, comme
    le vrai endpoint). Retourne les chunks avec le texte intégral.
    """
    vectors = await llm.get_embeddings([question])
    candidates = qdrant.search(vectors[0], limit=12)
    context_chunks = rerank_results(question, candidates, top_k=8, deduplicate=False)
    return context_chunks


def format_chunk_for_judge(chunk: dict[str, Any]) -> str:
    return (
        f"Titre : {chunk.get('title', 'Non précisé')}\n"
        f"Source : {chunk.get('source', 'Non précisée')}\n"
        f"Date : {chunk.get('modified_at', 'Non précisée')}\n"
        f"URL : {chunk.get('url', 'Non précisée')}\n"
        f"Contenu : {chunk.get('text', '(non récupéré)')}"
    )


async def evaluate_rag_quality(
    llm: MistralClient | None = None,
    qdrant: QdrantStore | None = None,
    backend_url: str | None = None,
) -> dict[str, Any]:
    global BACKEND_URL
    if backend_url:
        BACKEND_URL = backend_url

    llm = llm or MistralClient()
    qdrant = qdrant or QdrantStore()
    questions = load_golden_set()
    results = []

    for item in questions:
        question = item["question"]
        expected_id = item["expected_document_id"]
        key_facts = item.get("expected_key_facts", [])
        requires_source = item.get("requires_source_citation", True)

        logger.info("Évaluation : %s", question[:60])

        try:
            chat_response = await fetch_chat_response(question)
            response_text = chat_response.get("response", "")
            sources = chat_response.get("sources", [])
        except Exception as e:
            results.append({
                "question": question,
                "expected_document_id": expected_id,
                "error": str(e),
                "retrieval_success": False,
                "faithfulness": 0,
                "completeness": 0,
                "hallucination_absence": 0,
                "source_usage": 0,
                "overall": 0.0,
            })
            continue

        auto_eval = evaluation_from_sources(sources, expected_id, key_facts)

        replayed_chunks = await replay_rag_pipeline(llm, qdrant, question)

        context_chunks = [format_chunk_for_judge(c) for c in replayed_chunks]

        judge_result = await judge_response(llm, question, response_text, context_chunks)

        scores = {
            "faithfulness": judge_result.get("faithfulness", 0),
            "completeness": judge_result.get("completeness", 0),
            "hallucination_absence": judge_result.get("hallucination_absence", 0),
            "source_usage": judge_result.get("source_usage", 0),
        }
        max_score = 5
        overall = sum(scores.values()) / (4 * max_score)

        results.append({
            "question": question,
            "expected_document_id": expected_id,
            "response_preview": response_text[:200],
            "error": None,
            **auto_eval,
            **scores,
            "judge_explanation": judge_result.get("explanation", ""),
            "overall": round(overall, 3),
        })

    return compute_summary(results)


def compute_summary(results: list[dict]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {"error": "Aucun résultat", "results": []}

    retrieval_ok = sum(1 for r in results if r.get("retrieval_success"))
    faithfulness_avg = sum(r.get("faithfulness", 0) for r in results) / total
    completeness_avg = sum(r.get("completeness", 0) for r in results) / total
    hallucination_avg = sum(r.get("hallucination_absence", 0) for r in results) / total
    source_usage_avg = sum(r.get("source_usage", 0) for r in results) / total
    overall_avg = sum(r.get("overall", 0) for r in results) / total
    errors = [r for r in results if r.get("error")]

    return {
        "summary": {
            "total_questions": total,
            "retrieval_success_rate": round(retrieval_ok / total, 3),
            "avg_faithfulness": round(faithfulness_avg, 2),
            "avg_completeness": round(completeness_avg, 2),
            "avg_hallucination_absence": round(hallucination_avg, 2),
            "avg_source_usage": round(source_usage_avg, 2),
            "overall_quality": round(overall_avg, 3),
            "errors": len(errors),
        },
        "results": results,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default=BACKEND_URL)
    parser.add_argument("--output", default="data/evaluation/rag_quality_report.json")
    parser.add_argument("--print", action="store_true", help="Affiche le rapport dans la console")
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="Score overall minimum (0-1). Exit code 1 si en dessous.",
    )
    parser.add_argument(
        "--min-faithfulness", type=float, default=None,
        help="Score faithfulness minimum /5.",
    )
    parser.add_argument(
        "--min-hallucination", type=float, default=None,
        help="Score hallucination_absence minimum /5.",
    )
    args = parser.parse_args()

    llm = MistralClient()
    qdrant = QdrantStore()
    report = await evaluate_rag_quality(llm=llm, qdrant=qdrant, backend_url=args.backend_url)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Rapport sauvegardé : {output_path}")

    if args.print:
        s = report["summary"]
        print(f"\n=== RAPPORT QUALITÉ RAG ===")
        print(f"Questions : {s['total_questions']}")
        print(f"Retrieval success : {s['retrieval_success_rate']:.1%}")
        print(f"Fidélité : {s['avg_faithfulness']}/5")
        print(f"Complétude : {s['avg_completeness']}/5")
        print(f"Absence d'hallucination : {s['avg_hallucination_absence']}/5")
        print(f"Usage des sources : {s['avg_source_usage']}/5")
        print(f"Score global : {s['overall_quality']:.1%}")
        print(f"Erreurs : {s['errors']}")
        if s['errors']:
            for r in report["results"]:
                if r.get("error"):
                    print(f"  - {r['question'][:50]} : {r['error']}")
        for r in report["results"]:
            if r.get("error"):
                continue
            print(f"\n  {r['question'][:50]}")
            print(f"    Retrieval: {'✅' if r['retrieval_success'] else '❌'} | Fidélité: {r['faithfulness']}/5 | Complétude: {r['completeness']}/5 | Anti-hallucination: {r['hallucination_absence']}/5 | Sources: {r['source_usage']}/5")

    failures = []
    s = report["summary"]
    if args.threshold is not None and s["overall_quality"] < args.threshold:
        failures.append(f"Overall {s['overall_quality']:.1%} < {args.threshold:.0%}")
    if args.min_faithfulness is not None and s["avg_faithfulness"] < args.min_faithfulness:
        failures.append(f"Faithfulness {s['avg_faithfulness']}/5 < {args.min_faithfulness}/5")
    if args.min_hallucination is not None and s["avg_hallucination_absence"] < args.min_hallucination:
        failures.append(f"Hallucination {s['avg_hallucination_absence']}/5 < {args.min_hallucination}/5")
    if s["errors"] > 0:
        failures.append(f"{s['errors']} erreur(s) lors de l'évaluation")

    history_path = Path("data/eval_history.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    commit = "unknown"
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        pass
    history_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "commit": commit,
        "summary": s,
        "params": {
            "threshold": args.threshold,
            "min_faithfulness": args.min_faithfulness,
            "min_hallucination": args.min_hallucination,
        },
    }
    history.append(history_entry)
    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Historique sauvegardé : {history_path} ({len(history)} runs)")

    if failures:
        print(f"\n❌ QUALITY GATE FAILED: {'; '.join(failures)}")
        raise SystemExit(1)
    else:
        print(f"\n✅ Quality gate passed")


if __name__ == "__main__":
    asyncio.run(main())
