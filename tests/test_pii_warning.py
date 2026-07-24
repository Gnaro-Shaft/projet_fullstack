import logging

from app.pii import PIIAnonymizer


def test_spacy_model_missing_logs_warning(caplog):
    caplog.set_level(logging.WARNING)
    anon = PIIAnonymizer(model_name="fr_model_inexistant", enable_ner=True)
    assert anon.nlp is not None
    assert "Modèle spaCy" in caplog.text
    assert "fr_model_inexistant" in caplog.text
