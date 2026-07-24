
from scripts.evaluate_rag_quality import compute_summary, evaluation_from_sources, load_golden_set


def test_golden_set_contains_enriched_fields() -> None:
    questions = load_golden_set()
    for item in questions:
        assert "expected_key_facts" in item
        assert "anti_facts" in item
        assert "requires_date" in item
        assert "requires_source_citation" in item
        assert isinstance(item["expected_key_facts"], list)
        assert len(item["expected_key_facts"]) >= 2


def test_evaluation_from_sources_detects_retrieval_success() -> None:
    sources = [
        {"document_id": "F2169", "title": "Assurance vacances étranger", "text": "assurance voyage couverture médicale", "url": "https://example.com/F2169"},
    ]
    result = evaluation_from_sources(sources, "F2169", ["assurance"])
    assert result["retrieval_success"] is True
    assert result["expected_id"] == "F2169"
    assert result["key_facts_coverage"] == 1.0


def test_evaluation_from_sources_detects_retrieval_failure() -> None:
    sources = [
        {"document_id": "F9999", "title": "Autre fiche", "text": "autre contenu", "url": "https://example.com/F9999"},
    ]
    result = evaluation_from_sources(sources, "F2169", ["assurance"])
    assert result["retrieval_success"] is False


def test_compute_summary_empty() -> None:
    report = compute_summary([])
    assert "error" in report


def test_compute_summary_single_result() -> None:
    results = [
        {
            "question": "Test?",
            "expected_document_id": "F123",
            "retrieval_success": True,
            "faithfulness": 5,
            "completeness": 4,
            "hallucination_absence": 5,
            "source_usage": 3,
            "overall": 0.85,
            "error": None,
        }
    ]
    report = compute_summary(results)
    s = report["summary"]
    assert s["total_questions"] == 1
    assert s["retrieval_success_rate"] == 1.0
    assert s["overall_quality"] == 0.85


def test_compute_summary_multiple_results() -> None:
    results = [
        {"retrieval_success": True, "faithfulness": 5, "completeness": 5, "hallucination_absence": 5, "source_usage": 5, "overall": 1.0, "error": None},
        {"retrieval_success": False, "faithfulness": 2, "completeness": 3, "hallucination_absence": 4, "source_usage": 1, "overall": 0.5, "error": None},
    ]
    report = compute_summary(results)
    s = report["summary"]
    assert s["total_questions"] == 2
    assert s["retrieval_success_rate"] == 0.5
    assert s["errors"] == 0


def test_compute_summary_counts_errors() -> None:
    results = [
        {"retrieval_success": False, "faithfulness": 0, "completeness": 0, "hallucination_absence": 0, "source_usage": 0, "overall": 0.0, "error": "API timeout"},
    ]
    report = compute_summary(results)
    assert report["summary"]["errors"] == 1
