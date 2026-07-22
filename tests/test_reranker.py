from services.reranker import rerank_results


def test_reranker_combines_semantic_and_keyword_scores() -> None:
    results = rerank_results(
        "obtenir un logement social",
        [
            {"text": "Les conditions du logement social.", "score": 0.70},
            {"text": "Les démarches administratives générales.", "score": 0.90},
        ],
    )

    assert results[0]["text"] == "Les conditions du logement social."
    assert "rerank_score" in results[0]


def test_reranker_keeps_one_result_per_document() -> None:
    results = rerank_results(
        "logement social",
        [
            {"document_id": "F869", "title": "Logement social", "text": "fragment 1", "score": 0.80},
            {"document_id": "F869", "title": "Logement social", "text": "fragment 2", "score": 0.90},
            {"document_id": "F2326", "title": "Handicap étudiant", "text": "fragment", "score": 0.70},
        ],
    )

    assert [result["document_id"] for result in results] == ["F869", "F2326"]
    assert results[0]["text"] == "fragment 2"


def test_reranker_can_keep_multiple_chunks_for_context() -> None:
    results = rerank_results(
        "logement social",
        [
            {"document_id": "F869", "title": "Logement social", "text": "revenus", "score": 0.90},
            {"document_id": "F869", "title": "Logement social", "text": "dossier", "score": 0.80},
        ],
        top_k=2,
        deduplicate=False,
    )

    assert len(results) == 2
