# ADR-008 — Anonymisation aux frontières du LLM

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Les questions peuvent contenir des coordonnées ou entités personnelles.

## Décision

Anonymiser avant embeddings/génération et anonymiser à nouveau la réponse.

## Raisons

- limiter l'exposition au fournisseur ;
- protéger contre la reproduction d'une PII dans la sortie.

## Conséquences positives

- protection en profondeur ;
- règles déterministes testables.

## Limites et risques

- couverture incomplète ;
- NER désactivé par défaut ;
- risque de faux positifs si activé.

## Références

- `services/main.py`
- `services/pii.py`
- `tests/test_pii.py`
