import json

from app.audit import AuditLogger


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


def test_delete_entry_marks_as_deleted(tmp_path) -> None:
    audit = AuditLogger(str(tmp_path / "audit.jsonl"))
    entry = audit.record_chat("question", "réponse", [])
    rid = entry["request_id"]
    assert audit.chat_count() == 1

    result = audit.delete_entry(rid)
    assert result is True
    assert audit.chat_count() == 0
    assert rid not in audit.active_entry_ids()


def test_delete_nonexistent_entry_returns_false(tmp_path) -> None:
    audit = AuditLogger(str(tmp_path / "audit.jsonl"))
    result = audit.delete_entry("nonexistent-id")
    assert result is False


def test_delete_entry_does_not_remove_file(tmp_path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLogger(str(audit_path))
    entry = audit.record_chat("question", "réponse", [])
    audit.delete_entry(entry["request_id"])
    lines = [json.loads(l) for l in audit_path.read_text(encoding="utf-8").strip().split("\n")]
    assert len(lines) == 2
    assert lines[0]["event"] == "chat"
    assert lines[1]["event"] == "__deleted__"
