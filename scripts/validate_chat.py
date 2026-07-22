"""Valide plusieurs questions via l'API FastAPI en une seule commande."""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

GOLDEN_SET_PATH = Path("tests/fixtures/golden_set.json")
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def ask_backend(client: httpx.Client, backend_url: str, question: str) -> dict:
    """Envoie une question et retourne la réponse JSON du backend."""
    response = client.post(f"{backend_url}/chat", json={"message": question})
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Valide l'API /chat sur le golden set.")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    args = parser.parse_args()

    questions = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    details = []

    try:
        with httpx.Client(timeout=90.0) as client:
            for item in questions:
                result = ask_backend(client, args.backend_url, item["question"])
                source_ids = [source.get("document_id") for source in result.get("sources", [])]
                details.append(
                    {
                        "question": item["question"],
                        "expected_document_id": item["expected_document_id"],
                        "source_found": item["expected_document_id"] in source_ids,
                        "sources": source_ids,
                        "response_preview": result.get("response", "")[:120],
                    }
                )

            # Vérifie que l'anonymisation empêche l'email de ressortir.
            pii_result = ask_backend(
                client,
                args.backend_url,
                "Je suis Alice, mon email est alice@example.com. Quelles sont les conditions pour un logement social ?",
            )
            pii_ok = "alice@example.com" not in pii_result.get("response", "")
    except (httpx.HTTPError, OSError, json.JSONDecodeError) as error:
        print(f"Validation impossible : {error}", file=sys.stderr)
        return 1

    source_hits = sum(detail["source_found"] for detail in details)
    report = {
        "source_recall": source_hits / len(details) if details else 0.0,
        "sources_found": source_hits,
        "total_questions": len(details),
        "pii_anonymized": pii_ok,
        "details": details,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if source_hits == len(details) and pii_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
