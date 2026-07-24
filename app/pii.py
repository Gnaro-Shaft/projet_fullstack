"""Anonymisation simple des données personnelles avant et après le RAG."""

import logging
import os
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import spacy
except ImportError:  # pragma: no cover - dépendance optionnelle en environnement minimal
    spacy = None


@dataclass
class AnonymizationResult:
    """Texte anonymisé et types de données personnelles détectés."""

    text: str
    detected_types: list[str]


class PIIAnonymizer:
    """Masque les PII déterministes et les entités reconnues par spaCy."""

    EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+33\s?[1-9](?:[\s.-]?\d{2}){4}|0[1-9](?:[\s.-]?\d{2}){4})(?!\d)")

    def __init__(self, model_name: str | None = None, enable_ner: bool | None = None) -> None:
        self.model_name = model_name or os.getenv("SPACY_MODEL", "fr_core_news_sm")
        self.enable_ner = (
            enable_ner
            if enable_ner is not None
            else os.getenv("PII_ENABLE_NER", "true").lower() in {"1", "true", "yes"}
        )
        if not self.enable_ner:
            # Le NER est opt-in : un modèle mal calibré peut dégrader une réponse.
            self.nlp = None
            return

        if spacy is None:
            self.nlp = None
            return

        try:
            self.nlp = spacy.load(self.model_name)
        except OSError:
            logger.warning(
                "Modèle spaCy '%s' non trouvé — fallback sur spacy.blank('fr') "
                "(NER limité aux regex email/téléphone). Installez avec: "
                "python -m spacy download %s",
                self.model_name, self.model_name,
            )
            self.nlp = spacy.blank("fr")

    def anonymize(self, text: str) -> AnonymizationResult:
        detected_types = []

        # On remplace d'abord les formats faciles à détecter avec des regex.
        text, email_count = self._replace_pattern(text, self.EMAIL_PATTERN, "[EMAIL]")
        if email_count:
            detected_types.append("EMAIL")
        text, phone_count = self._replace_pattern(text, self.PHONE_PATTERN, "[TELEPHONE]")
        if phone_count:
            detected_types.append("TELEPHONE")

        # spaCy repère ensuite les personnes, organisations et lieux.
        document = self.nlp(text) if self.nlp is not None else None
        replacements = {
            "PER": "[PERSONNE]",
            "ORG": "[ORGANISATION]",
            "LOC": "[LIEU]",
        }
        for entity in reversed(document.ents if document is not None else []):
            replacement = replacements.get(entity.label_)
            if replacement:
                text = text[: entity.start_char] + replacement + text[entity.end_char :]
                detected_types.append(entity.label_)

        return AnonymizationResult(text=text, detected_types=sorted(set(detected_types)))

    @staticmethod
    def _replace_pattern(text: str, pattern: re.Pattern, replacement: str) -> tuple[str, int]:
        return pattern.subn(replacement, text)
