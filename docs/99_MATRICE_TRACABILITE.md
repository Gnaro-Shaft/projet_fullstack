# Matrice de traçabilité

| Affirmation | Source dans le dépôt |
|---|---|
| Anonymisation avant et après Mistral | `services/main.py`, `services/pii.py` |
| Recherche de 12 candidats | `services/main.py` |
| Contexte de 8 fragments | `services/main.py` |
| Reranking 65 % sémantique / 35 % lexical | `services/reranker.py` |
| Hash et synchronisation Service-Public | `scripts/extract_service_public.py`, `scripts/sync_service_public.py` |
| UUIDv5 déterministes | `services/qdrant_store.py` |
| Notices EUR-Lex RSS/Atom | `scripts/legal_feed_eurlex.py` |
| Sync différentielle EUR-Lex | `scripts/sync_legal_feed.py` |
| Workflow quotidien et manuel | `.github/workflows/sync-feeds.yml` |
| Tests avant déploiement | `.github/workflows/fly-deploy.yml` |
| Qdrant en mémoire en CI | `.github/workflows/fly-deploy.yml`, `services/qdrant_store.py` |
| Déploiement séparé | `fly.toml`, `fly.frontend.toml`, workflow |
| Suppression protégée | `services/main.py`, `tests/test_api.py` |
| Dates et statut dans Qdrant | `services/qdrant_store.py` |
| Dates et statut dans Streamlit | `frontend/streamlit_app.py` |
| Bandeau IA et disclaimer | `frontend/streamlit_app.py`, `tests/test_compliance.py` |
| Audit sans question brute | `services/audit.py`, `tests/test_audit.py` |
| 26 tests présents | `tests/` |
| `26 passed` | Résultat communiqué par Cédric |
| Pas d'historique permanent | `frontend/streamlit_app.py` |
| EUR-Lex sans texte complet systématique | `scripts/legal_feed_eurlex.py` et synthèse de Cédric |
