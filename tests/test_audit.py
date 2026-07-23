import json

from services.audit import AuditLogger


def test_audit_log_contains_sources_without_raw_question(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    AuditLogger(str(path)).record_chat(
        "Mon email est alice@example.com",
        "Réponse anonymisée",
        [{"document_id": "F123", "url": "https://example.test/F123", "modified_at": "2026-01-01"}],
    )

    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["event"] == "chat"
    assert event["sources"][0]["document_id"] == "F123"
    assert "alice@example.com" not in path.read_text(encoding="utf-8")
