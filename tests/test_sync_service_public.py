import asyncio
from unittest.mock import patch

from scripts.extract_service_public import ServicePublicDocument
from scripts.sync_service_public import synchronize


def document(document_id: str, source_hash: str) -> ServicePublicDocument:
    return ServicePublicDocument(
        document_id=document_id,
        title="Titre",
        url=f"https://example.test/{document_id}",
        modified_at="2026-07-21",
        source_hash=source_hash,
        text="Texte de démonstration",
    )


class FakeLLM:
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class FakeQdrant:
    def __init__(self) -> None:
        self.hashes = {"F-unchanged": "same", "F-removed": "old"}
        self.replaced = []
        self.deleted = []

    def list_document_hashes(self, source: str) -> dict[str, str]:
        return self.hashes

    def replace_document(self, **kwargs) -> int:
        self.replaced.append(kwargs["document_id"])
        return len(kwargs["documents"])

    def delete_document(self, document_id: str, source: str) -> None:
        self.deleted.append(document_id)


def test_synchronize_only_indexes_changed_documents() -> None:
    qdrant = FakeQdrant()
    documents = [document("F-unchanged", "same"), document("F-new", "new")]

    with patch("scripts.sync_service_public.download_if_changed", return_value=False), patch(
        "scripts.sync_service_public.extract_documents", return_value=documents
    ):
        result = asyncio.run(synchronize(llm=FakeLLM(), qdrant=qdrant))

    assert result == {"archive_changed": False, "indexed": 1, "skipped": 1, "deleted": 1}
    assert qdrant.replaced == ["F-new"]
    assert qdrant.deleted == ["F-removed"]
