from scripts.legal_feed_eurlex import (
    build_full_text_url,
    extract_celex,
    html_to_text,
    parse_feed,
)


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
    assert extract_celex(document) == "32024R0001"


def test_full_text_helpers_build_stable_link_and_remove_html_noise() -> None:
    assert build_full_text_url("32024R0001") == (
        "https://eur-lex.europa.eu/legal-content/FR/TXT/HTML/?uri=CELEX:32024R0001"
    )
    text = html_to_text(b"<html><head><style>.x{}</style></head><body><h1>Titre</h1><p>Texte <b>legal</b>.</p><script>ignore()</script></body></html>")
    assert text == "Titre Texte legal."


def test_parse_feed_supports_nested_celex_identifier() -> None:
    xml = b'''<?xml version="1.0"?><feed xmlns:notifEntry="urn:test">
      <entry><title>Directive</title><notifEntry:identifier>CELEX:32024L0002</notifEntry:identifier></entry>
    </feed>'''
    document = parse_feed(xml)[0]
    assert extract_celex(document) == "32024L0002"


def test_parse_feed_supports_celex_in_resource_attribute() -> None:
    xml = '''<?xml version="1.0"?><rss><channel><item resource="https://eur-lex.europa.eu/eli/reg/2024/1/oj?uri=CELEX:32024R0001"><title>Règlement</title></item></channel></rss>'''.encode()
    assert extract_celex(parse_feed(xml)[0]) == "32024R0001"
