# ADR-002 — Reranking local hybride

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

La similarité vectorielle peut privilégier un passage sémantiquement proche sans contenir un terme administratif ou numéro précis.

## Décision

Combiner 65 % de score Qdrant et 35 % de recouvrement lexical.

## Raisons

- logique explicable ;
- aucune dépendance à un second modèle ;
- amélioration des termes précis.

## Conséquences positives

- coût nul par requête ;
- comportement testable ;
- titres pris en compte.

## Limites et risques

- pondération empirique ;
- pas de compréhension syntaxique ;
- moins performant qu'un cross-encoder sur certains cas.

## Références

- `services/reranker.py`
- `tests/test_reranker.py`
