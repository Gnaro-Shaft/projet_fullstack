# Projet FULLSTACK

API FastAPI + Mistral + Qdrant + Streamlit — assistant RAG aux démarches administratives françaises.

## Démarrer en local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# renseigner MISTRAL_API_KEY dans .env
uvicorn app.main:app --reload
```

API sur `http://localhost:8000`, docs sur `http://localhost:8000/docs`.

```bash
curl http://localhost:8000/ping
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Bonjour"}'
```

## Interface Streamlit

```bash
streamlit run frontend/streamlit_app.py
```

Navigation multi-page (Chat → Dashboard), feedback persistant via API, affichage des sources et temps de réponse.

## Dashboard monitoring

Pages dans `frontend/pages/` :

| Page | Fonctionnalités |
|---|---|
| `📊_Dashboard.py` | Cartes KPIs, line chart temps réponse, bar chart volume, tokens (input/output), répartition statuts (OK/ERR/NS), top sources, évolution qualité RAG |

Le dashboard lit `/audit/recent` et `/metrics` (protégé par `X-Admin-Key`).

## Endpoints API

| Endpoint | Description |
|---|---|
| `GET /ping` | Healthcheck simple |
| `GET /health` | Vérifie Qdrant + embeddings + LLM (retourne JSON, `503` si défaillant) |
| `GET /metrics` | Métriques JSON : uptime, requêtes, docs indexés, tokens total, erreurs, latences (p50/p95/p99), top sources |
| `POST /chat` | Réponse RAG complète (sources + tokens) |
| `POST /chat/stream` | Réponse SSE token par token (avec tokens dans l'audit log) |
| `POST /documents` | Indexe des documents dans Qdrant |
| `GET /qdrant/health` | État de Qdrant |
| `POST /feedback` | Enregistre un feedback (`request_id` + `score`: positive/negative) |
| `DELETE /audit/{request_id}` | Marque une entrée comme effacée (RGPD) |
| `GET /audit/recent` | Dernières entrées d'audit (protégé par `X-Admin-Key`) |
| `GET /eval/history` | Historique des évaluations qualité RAG |

### Rate limiting

Middleware FastAPI — 30 requêtes/min/IP par défaut. Configurable via `RATE_LIMIT_PER_MINUTE`.

### Authentification

Les endpoints sensibles (`/audit/recent`, entrées par request_id) nécessitent l'en-tête `X-Admin-Key` correspondant à la variable d'environnement `ADMIN_API_KEY`.

## Qdrant / RAG

Configure `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION` et `MISTRAL_API_KEY` :

```bash
curl -X POST http://localhost:8000/documents \
  -H 'Content-Type: application/json' \
  -d '{"documents":[{"text":"Paris est la capitale de la France.","metadata":{"source":"démo"}}]}'
```

`docker compose up --build` lance Qdrant localement.

## Sources de données

### Service-Public

```bash
python scripts/download_service_public.py   # archive XML (ETag)
python scripts/extract_service_public.py     # extraction en fragments
python scripts/sync_service_public.py        # indexation Qdrant
python -m scripts.evaluate_golden_set        # Hit@1/3/5 + MRR sur questions de référence
```

### EUR-Lex

```bash
python -m scripts.sync_legal_feed --limit 1       # test
python -m scripts.sync_legal_feed                  # toutes les notices
python -m scripts.sync_legal_feed --force-full-text # réindexation forcée
python -m scripts.sync_legal_feed --metadata-only  # sans texte intégral
```

### Scheduler

```bash
python -m scripts.scheduler --once             # une sync puis quitte
python -m scripts.scheduler --interval 86400   # boucle 24h
```

## Évaluation qualité RAG

LLM-as-judge (Mistral) sur 4 dimensions via le golden set enrichi (`tests/fixtures/golden_set.json`) :

| Dimension | Score | Définition |
|---|---|---|
| **Fidélité** | 0–5 | Fidélité au contexte |
| **Complétude** | 0–5 | Couvre tous les aspects |
| **Absence d'hallucination** | 0–5 | Aucune information inventée |
| **Usage des sources** | 0–5 | Sources correctement citées |

```bash
python -m scripts.evaluate_rag_quality --print
python -m scripts.evaluate_rag_quality --output data/evaluation/rag_report.json
# Avec quality gate (CI) :
python -m scripts.evaluate_rag_quality --threshold 0.7 --min-faithfulness 3.5 --min-hallucination 3.5
```

L'historique est sauvegardé dans `data/eval_history.json` et consultable via `GET /eval/history`.

## Token tracking

`LlmResponse` contient `input_tokens` et `output_tokens`. Enregistrés dans l'audit log pour chaque appel RAG, y compris en streaming (capture du champ `usage` du dernier chunk Mistral).

## Feedback utilisateur

`POST /feedback` avec `request_id` + `score` (`positive`/`negative`). Stocké dans l'audit log. L'interface Streamlit envoie les pouces à l'API.

## Audit log & RGPD

- Question hashée (SHA-256), PII anonymisées avant écriture
- IP anonymisée (dernier octet masqué)
- Droit à l'effacement : `DELETE /audit/{request_id}` écrit un tombstone
- Compaction automatique au-delà de 30% de tombstones via `AuditLogger.compact()`
- Consultation : `GET /audit/recent` (protégé par `ADMIN_API_KEY`)

## PII / NER spaCy

Anonymisation regex (email, téléphone) + NER optionnel (personnes, organisations, lieux).

```bash
python -m spacy download fr_core_news_sm
```

```env
PII_ENABLE_NER=true
```

Un `logger.warning` signale si le modèle spaCy est absent (fallback silencieux évité).

## Retry & résilience

Les appels Mistral retentent automatiquement (`429`, `500`, `502`, `503`, `504`). `MISTRAL_MAX_RETRIES` (défaut: 5). Backoff exponentiel + `Retry-After`.

## Tests

```bash
pytest
```

- Unitaires + intégration Qdrant (Docker/memory)
- FakeLLM pour les tests sans appel Mistral
- Couverture minimale 50% (`pytest-cov`, échoue en dessous)
- Linting ruff (CI bloque si non conforme)

## CI / CD

Workflow `.github/workflows/fly-deploy.yml` (déclenché sur `push main`) :

| Step | Description |
|---|---|
| Ruff | Vérifie le style |
| Pytest --cov | Tests + couverture ≥ 50% |
| Tests intégration | Qdrant docker + FakeLLM |
| Quality gate | Golden set eval, bloque si overall < 70%, faithfulness < 3.5/5, hallucination < 3.5/5 |
| Fly deploy | Déploie backend + frontend |
| Smoke test | `curl /ping` après déploiement |

Les synchronisations quotidiennes via `.github/workflows/sync-feeds.yml`.

## Docker

```bash
docker compose up --build
```

## Déploiement Fly.io

```bash
# Backend
fly deploy --config fly.toml --app projet-fullstack

# Frontend
fly deploy --config fly.frontend.toml --app trustrag-frontend
```

Secrets :

```bash
fly secrets set \
  MISTRAL_API_KEY="..." \
  QDRANT_URL="..." \
  QDRANT_API_KEY="..." \
  QDRANT_COLLECTION="documents" \
  ADMIN_API_KEY="..." \
  --app projet-fullstack

fly secrets set BACKEND_URL="https://projet-fullstack.fly.dev" \
  --app trustrag-frontend
```

Vérification post-déploiement :

```bash
curl https://projet-fullstack.fly.dev/ping
curl https://projet-fullstack.fly.dev/qdrant/health
curl -H "X-Admin-Key: $ADMIN_API_KEY" https://projet-fullstack.fly.dev/metrics
```
