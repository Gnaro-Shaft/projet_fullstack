# Référence de configuration

| Variable | Service | Obligatoire | Valeur par défaut | Usage |
|---|---|---:|---|---|
| `QDRANT_URL` | Backend / sync | Oui | — | URL Qdrant ou `:memory:` |
| `QDRANT_API_KEY` | Backend / sync | Cloud | — | Authentification Qdrant |
| `QDRANT_COLLECTION` | Backend / sync | Non | `documents` | Collection |
| `MISTRAL_API_KEY` | Backend / sync | Oui | — | Appels Mistral |
| `MISTRAL_URL` | Backend / sync | Non | API Mistral v1 | URL de base |
| `MISTRAL_MODEL` | Backend | Non | `mistral-small-latest` | Génération |
| `MISTRAL_EMBEDDING_MODEL` | Backend / sync | Non | `mistral-embed` | Embeddings |
| `MISTRAL_MAX_RETRIES` | Backend | Non | `5` | Retries |
| `SPACY_MODEL` | Backend | Non | `fr_core_news_sm` | NER |
| `PII_ENABLE_NER` | Backend | Non | `false` | Active le NER |
| `FASTAPI_PORT` | Backend local | Non | `8000` | Port direct |
| `BACKEND_URL` | Frontend | Non | `http://localhost:8000` | URL API |
| `ADMIN_API_KEY` | Backend | Suppression | — | Clé d'administration |
| `AUDIT_LOG_PATH` | Backend | Non | `data/audit/chat_audit.jsonl` | Journal JSONL |
| `LOG_LEVEL` | Backend | Non | `INFO` | Niveau de logs |
| `EURLEX_FEED_URL` | Sync EUR-Lex | Non | URL Cellar calculée | Flux personnalisé |
| `SYNC_INTERVAL_SECONDS` | Scheduler local | Non | `86400` | Intervalle |
