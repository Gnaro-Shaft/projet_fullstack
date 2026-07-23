# ADR-001 — Synchronisation différentielle par hash

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Les corpus officiels évoluent régulièrement. Une réindexation intégrale consomme des appels d'embeddings et augmente les temps de traitement.

## Décision

Comparer un SHA-256 de chaque document au hash stocké dans Qdrant et ne réindexer que les nouveautés ou modifications.

## Raisons

- réduction du coût d'embedding ;
- exécutions quotidiennes réalistes ;
- détection uniforme pour Service-Public et EUR-Lex.

## Conséquences positives

- synchronisation plus rapide ;
- moins d'appels externes ;
- remplacement cohérent de tous les fragments d'un document.

## Limites et risques

- toute évolution de l'extracteur pouvant modifier le contenu logique doit influencer le hash ;
- les suppressions Service-Public ne sont détectées que lors d'une synchronisation complète.

## Références

- `scripts/sync_service_public.py`
- `scripts/sync_legal_feed.py`
- `services/qdrant_store.py`
