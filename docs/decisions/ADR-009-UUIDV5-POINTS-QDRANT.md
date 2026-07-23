# ADR-009 — UUIDv5 déterministes pour les fragments

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Les fragments doivent conserver un identifiant stable entre synchronisations.

## Décision

Construire l'UUIDv5 à partir de la source, du document et de l'index de fragment.

## Raisons

- déterminisme ;
- compatibilité avec les identifiants Qdrant ;
- traçabilité.

## Conséquences positives

- remplacement prévisible ;
- absence de duplication par identifiant lors d'un même découpage.

## Limites et risques

- un changement de chunking peut déplacer les identifiants ;
- le remplacement supprime d'abord l'ancien document.

## Références

- `services/qdrant_store.py`
