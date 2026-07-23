"""Journalisation minimale et sans PII brute des échanges RAG."""

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


logger = logging.getLogger("trustrag.audit")


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
