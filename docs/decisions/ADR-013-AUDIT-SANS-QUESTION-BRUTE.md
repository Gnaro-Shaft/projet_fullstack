# ADR-013 — Audit sans question brute

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

L'équipe veut tracer les requêtes et sources sans conserver directement le contenu sensible.

## Décision

Stocker un hash de la question, la longueur de réponse et les métadonnées de sources.

## Raisons

- minimisation ;
- suivi technique de base ;
- format JSONL simple.

## Conséquences positives

- pas de question brute dans le journal ;
- événements faciles à analyser.

## Limites et risques

- hash réidentifiable pour texte prévisible ;
- aucune rotation ;
- observabilité limitée.

## Références

- `services/audit.py`
- `tests/test_audit.py`
