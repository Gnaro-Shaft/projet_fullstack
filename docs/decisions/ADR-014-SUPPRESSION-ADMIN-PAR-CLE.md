# ADR-014 — Suppression ciblée protégée par clé

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Un document obsolète ou incorrect doit pouvoir être retiré sans réindexer tout le corpus.

## Décision

Exposer une route DELETE protégée par l'en-tête `X-Admin-Key`.

## Raisons

- opération simple ;
- suppression par `document_id` et `source` ;
- usage compatible avec les scripts d'administration.

## Conséquences positives

- correction ciblée rapide ;
- pas d'accès public anonyme.

## Limites et risques

- clé statique unique ;
- pas de rate limiting ;
- pas d'audit de suppression ;
- pas de gestion de rôles.

## Références

- `services/main.py`
- `services/qdrant_store.py`
- `tests/test_api.py`
