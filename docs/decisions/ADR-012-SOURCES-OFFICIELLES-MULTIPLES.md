# ADR-012 — Sources officielles multiples

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Service-Public couvre les démarches françaises, tandis qu'EUR-Lex couvre les actes européens.

## Décision

Indexer les deux sources dans une collection avec un champ `source`.

## Raisons

- couverture complémentaire ;
- pipeline commun d'embeddings et de recherche ;
- filtrage et suppression par source.

## Conséquences positives

- extension progressive du corpus ;
- métadonnées homogènes.

## Limites et risques

- granularité et richesse très différentes ;
- notices EUR-Lex encore moins complètes ;
- classement inter-source à évaluer.

## Références

- `scripts/sync_service_public.py`
- `scripts/sync_legal_feed.py`
- `services/qdrant_store.py`
