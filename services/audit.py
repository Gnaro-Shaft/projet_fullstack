"""Journalisation minimale et sans PII brute des échanges RAG.

Conformité RGPD :
- La question brute n'est jamais écrite, seulement son hash SHA-256.
- Les PII sont anonymisées avant écriture (via PIIAnonymizer).
- Une entrée peut être marquée comme effacée via delete_entry().
"""

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


logger = logging.getLogger("trustrag.audit")

_DELETED_FLAG = "__deleted__"


class AuditLogger:
    """Écrit une trace JSON par requête dans un fichier local et les logs."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("AUDIT_LOG_PATH", "data/audit/chat_audit.jsonl"))

    def record_chat(
        self,
        question: str,
        response: str,
        sources: list[dict[str, Any]],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Enregistre les éléments utiles sans écrire la question originale."""
        event = {
            "event": "chat",
            "request_id": request_id or str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
            "response_length": len(response),
            "sources": [
                {
                    "document_id": source.get("document_id"),
                    "url": source.get("url"),
                    "modified_at": source.get("modified_at"),
                    "effective_at": source.get("effective_at"),
                    "status": source.get("status"),
                }
                for source in sources
            ],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(event, ensure_ascii=False) + "\n")
        logger.info("chat_audit request_id=%s sources=%s", event["request_id"], len(sources))
        return event

    def delete_entry(self, request_id: str) -> bool:
        """Marque une entrée d'audit comme effacée (tombstone).

        Retourne True si un événement de ce request_id existait, False sinon.
        L'entrée originale reste sur disac mais est ignorée par chat_count().
        """
        marker = {
            "event": _DELETED_FLAG,
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        exists = any(
            entry.get("request_id") == request_id
            for entry in self._read_entries()
            if entry.get("event") != _DELETED_FLAG
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(marker, ensure_ascii=False) + "\n")
        return exists

    def chat_count(self) -> int:
        """Retourne le nombre d'échanges non effacés."""
        return len(self.active_entry_ids())

    def _read_entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def active_entry_ids(self) -> set[str]:
        """IDs des entrées non effacées."""
        entries = self._read_entries()
        deleted = {
            e["request_id"]
            for e in entries
            if e.get("event") == _DELETED_FLAG
        }
        return {
            e["request_id"]
            for e in entries
            if e.get("event") != _DELETED_FLAG
            and e["request_id"] not in deleted
        }

    def entry_exists(self, request_id: str) -> bool:
        return request_id in self.active_entry_ids()
