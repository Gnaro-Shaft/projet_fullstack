# ADR-005 — Streamlit pour le frontend

- **Statut** : Accepté
- **Date documentaire** : 23 juillet 2026

## Contexte

L'équipe a besoin d'une interface rapide à développer pour tester et présenter le chatbot.

## Décision

Utiliser Streamlit comme frontend séparé.

## Raisons

- faible coût de développement ;
- composants de chat ;
- déploiement Python simple.

## Conséquences positives

- itération UX rapide ;
- code compact ;
- affichage des sources.

## Limites et risques

- personnalisation et gestion d'état limitées ;
- pas de frontend multi-utilisateur sophistiqué ;
- dépendance au rerun Streamlit.

## Références

- `frontend/streamlit_app.py`
- `Dockerfile.streamlit`
