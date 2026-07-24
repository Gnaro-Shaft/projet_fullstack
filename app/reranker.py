"""Reranking local et explicable des résultats Qdrant."""

import re
import unicodedata
from typing import Any


def _words(text: str) -> set[str]:
    """Transforme un texte en mots comparables, sans accents ni ponctuation."""
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )
    return set(re.findall(r"[a-z0-9]{3,}", without_accents))


def _keyword_score(question: str, document: str) -> float:
    """Mesure la proportion de mots de la question présents dans le document."""
    question_words = _words(question)
    if not question_words:
        return 0.0
    return len(question_words & _words(document)) / len(question_words)


def rerank_results(
    question: str,
    results: list[dict[str, Any]],
    top_k: int = 4,
    deduplicate: bool = True,
) -> list[dict[str, Any]]:
    """Réordonne les candidats avec un mélange similarité + mots-clés.

    Qdrant fournit déjà un score sémantique. Les mots-clés ajoutent un signal
    simple et lisible, utile pour les numéros de formulaires et termes précis.
    """
    best_result_by_document = {}
    ranked_results = []
    for position, result in enumerate(results):
        semantic_score = float(result.get("score", 0.0))
        # Le titre est important : il contient souvent le sujet exact de la fiche.
        searchable_text = f"{result.get('title', '')} {result.get('text', '')}"
        keyword_score = _keyword_score(question, searchable_text)
        # Le score de mots-clés uniquement sur le titre pour le filrage "hors-sujet"
        title_keyword_score = _keyword_score(question, result.get('title', ''))
        result_with_score = dict(result)
        result_with_score["rerank_score"] = 0.95 * semantic_score + 0.05 * keyword_score
        result_with_score["keyword_score"] = keyword_score
        result_with_score["title_keyword_score"] = title_keyword_score
        document_key = result.get("document_id") or f"result-{position}"

        if not deduplicate:
            ranked_results.append(result_with_score)
            continue

        # Plusieurs fragments peuvent appartenir à la même fiche.
        # L'UI doit afficher une seule citation par fiche, celle qui a le meilleur score.
        previous_result = best_result_by_document.get(document_key)
        if previous_result is None or result_with_score["rerank_score"] > previous_result["rerank_score"]:
            best_result_by_document[document_key] = result_with_score

    if deduplicate:
        ranked_results = list(best_result_by_document.values())
    ranked_results.sort(key=lambda item: item["rerank_score"], reverse=True)
    return ranked_results[:top_k]
