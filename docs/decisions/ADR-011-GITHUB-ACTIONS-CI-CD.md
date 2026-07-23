# ADR-011 — GitHub Actions pour CI/CD et synchronisations

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Les tests, déploiements et mises à jour de corpus doivent être reproductibles.

## Décision

Utiliser deux workflows : push `main` pour tests/déploiements et cron/manuel pour les feeds.

## Raisons

- proximité avec le dépôt ;
- secrets gérés par GitHub ;
- déclencheurs natifs.

## Conséquences positives

- déploiement bloqué si tests en échec ;
- automatisation quotidienne ;
- lancement manuel disponible.

## Limites et risques

- dépendance GitHub ;
- absence de notification dédiée ;
- consommation de minutes CI.

## Références

- `.github/workflows/fly-deploy.yml`
- `.github/workflows/sync-feeds.yml`
