# ADR-006 — Qdrant comme base vectorielle

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Le système doit stocker des embeddings, filtrer par métadonnées et remplacer des documents.

## Décision

Utiliser Qdrant avec distance cosinus et index de payload.

## Raisons

- recherche vectorielle native ;
- filtres `document_id` / `source` ;
- client Python ;
- mode mémoire pour les tests.

## Conséquences positives

- même abstraction en local, CI et cloud ;
- synchronisation différentielle ;
- suppression ciblée.

## Limites et risques

- dépendance externe en production ;
- cohérence dimension de vecteur / collection ;
- gestion des secrets.

## Références

- `services/qdrant_store.py`
- `docker-compose.yml`
