import json
from pathlib import Path


def test_golden_set_contains_reference_questions() -> None:
    golden_set_path = Path(__file__).parent / "fixtures" / "golden_set.json"
    questions = json.loads(golden_set_path.read_text(encoding="utf-8"))

    assert 8 <= len(questions) <= 10
    assert all(item["question"] and item["expected_document_id"] for item in questions)
