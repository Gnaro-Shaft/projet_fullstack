# ADR-003 — Absence de persistance permanente des conversations

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

Les questions administratives peuvent contenir des données personnelles.

## Décision

Conserver uniquement l'échange courant dans la session Streamlit et ne pas utiliser de base de conversations.

## Raisons

- minimisation des données ;
- réduction de la surface de conformité ;
- architecture simple.

## Conséquences positives

- pas de stockage durable de conversations ;
- pas de mécanisme de suppression utilisateur à maintenir.

## Limites et risques

- pas de mémoire multi-tour ;
- pas de reprise de session ;
- analyse d'usage limitée.

## Références

- `frontend/streamlit_app.py`
- synthèse de Cédric
