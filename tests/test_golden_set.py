import json
from pathlib import Path


def test_golden_set_contains_reference_questions() -> None:
    golden_set_path = Path(__file__).parent / "fixtures" / "golden_set.json"
    questions = json.loads(golden_set_path.read_text(encoding="utf-8"))

    assert len(questions) >= 8
    for item in questions:
        assert item["question"]
        assert item["expected_document_id"]
        assert isinstance(item.get("expected_key_facts"), list)
        assert isinstance(item.get("anti_facts"), list)
        assert "requires_date" in item
        assert "requires_source_citation" in item
