from app.pii import PIIAnonymizer


def test_anonymizer_masks_email_and_phone() -> None:
    anonymizer = PIIAnonymizer(model_name="model-not-installed-for-test")

    result = anonymizer.anonymize("Contactez alice@example.com au 06 12 34 56 78.")

    assert "alice@example.com" not in result.text
    assert "06 12 34 56 78" not in result.text
    assert "[EMAIL]" in result.text
    assert "[TELEPHONE]" in result.text
    assert set(result.detected_types) == {"EMAIL", "TELEPHONE"}


def test_anonymizer_uses_spacy_entities_when_available() -> None:
    anonymizer = PIIAnonymizer(model_name="model-not-installed-for-test", enable_ner=True)
    anonymizer.nlp = lambda text: type("Document", (), {"ents": []})()

    result = anonymizer.anonymize("Une demande est en cours.")

    assert result.text == "Une demande est en cours."


def test_anonymizer_does_not_corrupt_public_text_by_default() -> None:
    anonymizer = PIIAnonymizer(model_name="model-not-installed-for-test")

    result = anonymizer.anonymize("Consultez https://www.service-public.gouv.fr/vosdroits/F869.")

    assert result.text == "Consultez https://www.service-public.gouv.fr/vosdroits/F869."
