import json

from app.audit import AuditLogger


def test_compact_removes_tombstones_and_deleted_entries(tmp_path):
    audit = AuditLogger(str(tmp_path / "audit.jsonl"))
    e1 = audit.record_chat("question 1", "réponse 1", [])
    e2 = audit.record_chat("question 2", "réponse 2", [])
    e3 = audit.record_chat("question 3", "réponse 3", [])
    assert audit.chat_count() == 3

    audit.delete_entry(e1["request_id"])
    audit.delete_entry(e2["request_id"])
    assert audit.chat_count() == 1

    removed = audit.compact(force=True)
    assert removed == 4
    assert audit.chat_count() == 1

    lines = audit.path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    assert json.loads(lines[0])["request_id"] == e3["request_id"]


def test_compact_noop_when_below_threshold(tmp_path):
    audit = AuditLogger(str(tmp_path / "audit.jsonl"))
    audit.record_chat("question", "réponse", [])
    audit.delete_entry("nonexistent")
    result = audit.compact(threshold=0.9)
    assert result == 0


def test_compact_returns_zero_for_empty_file(tmp_path):
    audit = AuditLogger(str(tmp_path / "audit.jsonl"))
    assert audit.compact(force=True) == 0
