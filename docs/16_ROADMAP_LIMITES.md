# Roadmap, limites et risques

## Priorité 1 — Enrichissement EUR-Lex

Télécharger et indexer le texte complet des actes au lieu de se limiter aux notices. C'est l'amélioration fonctionnelle principale.

## Priorité 2 — Validation publique

- plusieurs utilisateurs simultanés ;
- questions variées ;
- sources et dates ;
- panne Mistral ;
- panne Qdrant ;
- temps de réponse ;
- anonymisation réelle.

## Priorité 3 — Administration

- authentification dédiée ;
- limitation des tentatives ;
- audit des suppressions ;
- interface séparée ;
- rotation des clés.

## Priorité 4 — Qualité d'affichage

- limiter les sources visibles ;
- conserver plus de fragments dans le contexte ;
- nettoyer la typographie ;
- mieux présenter les statuts juridiques.

## Priorité 5 — Observabilité

- métriques de latence ;
- erreurs par dépendance ;
- volume de tokens ;
- suivi des synchronisations ;
- alertes CI/CD ;
- politique de rétention.

## Historique de conversations

Il n'est pas implémenté. Cette décision protège la confidentialité et simplifie l'architecture, mais empêche les usages multi-tours et la reprise de session. Toute évolution doit commencer par une analyse de finalité, base légale, rétention, chiffrement et droits d'accès.

## Dette technique visible

- dépendances inutilisées ou anticipées ;
- noms de produit incohérents ;
- duplications dans `.env.example` et `requirements.txt` ;
- README d'origine incomplet ;
- absence de typage strict des sources publiques ;
- absence de tests de charge ;
- absence de rate limiting ;
- audit local sans rotation.
