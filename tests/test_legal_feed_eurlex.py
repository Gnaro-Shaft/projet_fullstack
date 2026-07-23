from scripts.legal_feed_eurlex import parse_feed


RSS_FIXTURE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <guid>CELEX:32024R0001</guid>
    <title>Règlement européen de démonstration</title>
    <link>https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32024R0001</link>
    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
    <description>Texte et statut du règlement.</description>
  </item>
</channel></rss>""".encode("utf-8")


def test_parse_eurlex_feed_extracts_legal_metadata() -> None:
    documents = parse_feed(RSS_FIXTURE)

    assert len(documents) == 1
    document = documents[0]
    assert document.document_id.startswith("eurlex-")
    assert document.title == "Règlement européen de démonstration"
    assert document.url.startswith("https://eur-lex.europa.eu")
    assert document.modified_at == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert document.status == "published"
    assert len(document.source_hash) == 64
