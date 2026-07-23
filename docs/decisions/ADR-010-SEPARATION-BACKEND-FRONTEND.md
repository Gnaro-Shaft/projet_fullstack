# ADR-010 — Séparation backend et frontend

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

L'API et l'interface ont des dépendances, ports et cycles de déploiement différents.

## Décision

Créer deux images et deux applications Fly.io.

## Raisons

- responsabilités isolées ;
- frontend avec dépendances minimales ;
- évolutions indépendantes.

## Conséquences positives

- images plus ciblées ;
- panne ou redéploiement isolable ;
- URL backend configurable.

## Limites et risques

- configuration `BACKEND_URL` ;
- deux jeux de secrets et tokens ;
- deux applications à superviser.

## Références

- `Dockerfile`
- `Dockerfile.streamlit`
- `fly.toml`
- `fly.frontend.toml`
