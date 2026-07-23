# ADR-004 — FastAPI pour le backend

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Le projet doit exposer des contrats HTTP typés et une documentation interactive.

## Décision

Utiliser FastAPI et Pydantic pour l'API.

## Raisons

- validation automatique ;
- OpenAPI / Swagger ;
- prise en charge async ;
- intégration Python directe.

## Conséquences positives

- contrats clairs ;
- tests avec TestClient ;
- erreurs de validation 422 automatiques.

## Limites et risques

- les appels Qdrant synchrones doivent passer dans un threadpool ;
- l'orchestration reste concentrée dans `services/main.py`.

## Références

- `services/main.py`
- `tests/test_api.py`
