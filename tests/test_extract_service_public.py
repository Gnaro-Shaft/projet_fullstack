import zipfile

from scripts.extract_service_public import extract_documents, split_into_chunks

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Publication xmlns:dc="http://purl.org/dc/elements/1.1/" ID="F123" spUrl="https://example.test/F123">
  <dc:title>Titre de démonstration</dc:title>
  <dc:date>modified 2026-07-21</dc:date>
  <Introduction><Texte><Paragraphe>Introduction utile.</Paragraphe></Texte></Introduction>
  <ListeSituations><Situation><Texte><Paragraphe>Contenu principal utile.</Paragraphe></Texte></Situation></ListeSituations>
</Publication>"""


def test_extract_documents_reads_publication_content(tmp_path) -> None:
    archive_path = tmp_path / "service-public.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("F123.xml", SAMPLE_XML)
        archive.writestr("R456.xml", SAMPLE_XML)

    documents = extract_documents(archive_path)

    assert len(documents) == 1
    document = documents[0]
    assert document.document_id == "F123"
    assert document.title == "Titre de démonstration"
    assert document.url == "https://example.test/F123"
    assert document.text == "Introduction utile. Contenu principal utile."
    assert len(document.source_hash) == 64


def test_split_into_chunks_keeps_the_final_chunk_once() -> None:
    chunks = split_into_chunks("a" * 2_500, size=1_000, overlap=200)

    assert len(chunks) == 3
    assert chunks[-1] == "a" * 900
