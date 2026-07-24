from app.qdrant_store import QdrantStore


def test_replace_document_removes_obsolete_chunks() -> None:
    store = QdrantStore(url=":memory:", collection_name="service_public_test")
    old_chunks = [
        {
            "document_id": "F2169",
            "chunk_index": 0,
            "title": "Titre",
            "url": "https://example.test/F2169",
            "modified_at": "2026-07-21",
            "source_hash": "old",
            "text": "Ancien premier fragment",
        },
        {
            "document_id": "F2169",
            "chunk_index": 1,
            "title": "Titre",
            "url": "https://example.test/F2169",
            "modified_at": "2026-07-21",
            "source_hash": "old",
            "text": "Ancien second fragment",
        },
    ]
    new_chunk = [{**old_chunks[0], "source_hash": "new", "text": "Nouveau fragment"}]

    assert store.replace_document("F2169", old_chunks, [[1.0, 0.0], [0.9, 0.1]], "service-public-vdd") == 2
    assert store.list_document_hashes("service-public-vdd") == {"F2169": "old"}
    assert store.replace_document("F2169", new_chunk, [[1.0, 0.0]], "service-public-vdd") == 1

    results = store.search([1.0, 0.0], limit=10)
    assert len(results) == 1
    assert results[0]["text"] == "Nouveau fragment"
    assert store.list_document_hashes("service-public-vdd") == {"F2169": "new"}
