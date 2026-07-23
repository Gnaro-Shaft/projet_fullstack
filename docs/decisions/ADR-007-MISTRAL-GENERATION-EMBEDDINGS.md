# ADR-007 — Mistral pour la génération et les embeddings

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Le pipeline nécessite un modèle de génération francophone et un modèle d'embedding accessible par API.

## Décision

Utiliser l'API Mistral pour les deux usages.

## Raisons

- interface unique ;
- support du français ;
- modèles configurables par variables d'environnement.

## Conséquences positives

- client commun ;
- retries centralisés ;
- remplacement de modèle sans changer l'orchestration.

## Limites et risques

- dépendance réseau et tarifaire ;
- limites de débit ;
- absence de fallback fournisseur.

## Références

- `services/llm.py`
- `.env.example`
