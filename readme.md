# Projet FULSTACK

API FastAPI qui combine Mistral et Qdrant pour répondre à partir de documents indexés.

## Démarrer en local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# renseigner MISTRAL_API_KEY dans .env
uvicorn services.main:app --reload
```

L'API est disponible sur `http://localhost:8000` et sa documentation sur
`http://localhost:8000/docs`.

```bash
curl http://localhost:8000/ping
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Bonjour"}'
```

## Qdrant / RAG

Configure `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION` et
`MISTRAL_API_KEY` dans `.env`, puis indexe tes documents :

```bash
curl -X POST http://localhost:8000/documents \
  -H 'Content-Type: application/json' \
  -d '{"documents":[{"text":"Paris est la capitale de la France.","metadata":{"source":"démo"}}]}'

curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Quelle est la capitale de la France ?"}'
```

`GET /qdrant/health` vérifie la connexion. Avec Docker, `docker compose up --build`
lance aussi Qdrant localement ; l'API s'y connecte automatiquement.

## Télécharger la source Service-Public

Le script conserve localement la dernière archive XML et un manifeste de version
dans `data/raw/service-public/`. Il utilise l'en-tête `ETag` : si la source n'a
pas changé, aucun fichier n'est téléchargé.

```bash
python scripts/download_service_public.py
```

Les archives et leurs manifestes sont volontairement ignorés par Git.

Pour vérifier l'extraction des fiches `F*.xml` en fragments indexables :

```bash
python scripts/extract_service_public.py
```

Pour synchroniser les fiches modifiées dans Qdrant :

```bash
python scripts/sync_service_public.py
```

Le premier lancement indexe toutes les fiches ; les suivants ne créent des
embeddings que pour les fiches nouvelles ou modifiées.

Pour mesurer le retrieval sur les questions de référence :

```bash
python -m scripts.evaluate_golden_set
```

Le résultat affiche le `recall@4` et les IDs effectivement retrouvés.

## Synchroniser EUR-Lex

Le connecteur EUR-Lex récupère les notifications récentes, identifie les
documents par leur numéro CELEX, télécharge le texte intégral disponible, le
découpe en fragments et crée les embeddings dans Qdrant.

```bash
# Tester avec une seule notice
python -m scripts.sync_legal_feed --limit 1

# Synchroniser les notices disponibles
python -m scripts.sync_legal_feed

# Réindexer des notices déjà présentes (après une correction du connecteur)
python -m scripts.sync_legal_feed --limit 20 --force-full-text
```

Les documents déjà à jour sont ignorés grâce à leur hash. Certains actes
peuvent rester en métadonnées seules si EUR-Lex renvoie `404` pour leur texte
intégral ; ils restent néanmoins consultables comme sources.

En cas de quota Mistral (`429`), le script attend automatiquement puis reporte
le document concerné. Il suffit de relancer la synchronisation plus tard.

Pour utiliser uniquement les notices sans télécharger les textes complets :

```bash
python -m scripts.sync_legal_feed --metadata-only
```

Le scheduler quotidien peut lancer les deux sources :

```bash
# Exécuter une synchronisation puis quitter (utile pour un cron)
python -m scripts.scheduler --once

# Lancer une boucle toutes les 24 heures
python -m scripts.scheduler --interval 86400
```

## Déploiement Fly.io

Les deux applications Fly.io utilisent leurs fichiers de configuration dédiés :

```bash
# Backend FastAPI
fly deploy --config fly.toml --app projet-fullstack

# Frontend Streamlit
fly deploy --config fly.frontend.toml --app trustrag-frontend
```

Les secrets ne doivent pas être commités dans Git. Ils se configurent avec
`fly secrets set`, par exemple :

```bash
fly secrets set \
  MISTRAL_API_KEY="..." \
  QDRANT_URL="..." \
  QDRANT_API_KEY="..." \
  QDRANT_COLLECTION="documents" \
  ADMIN_API_KEY="..." \
  --app projet-fullstack
```

Le frontend doit pointer vers l'URL publique du backend :

```bash
fly secrets set BACKEND_URL="https://projet-fullstack.fly.dev" \
  --app trustrag-frontend
```

Le workflow GitHub Actions `.github/workflows/fly-deploy.yml` exécute les tests
à chaque push sur `main`, puis déploie automatiquement le backend et le
frontend. Le workflow `.github/workflows/sync-feeds.yml` lance les
synchronisations quotidiennes ; ses secrets GitHub doivent contenir les mêmes
valeurs Mistral et Qdrant que l'environnement de production.

Après un déploiement, vérifier :

```bash
curl https://projet-fullstack.fly.dev/ping
curl https://projet-fullstack.fly.dev/qdrant/health
```

## Interface Streamlit

Dans un second terminal, démarre l'interface :

```bash
streamlit run frontend/streamlit_app.py
```

Elle utilise `BACKEND_URL` (par défaut `http://localhost:8000`) et affiche
l'historique du chat ainsi que les sources officielles retournées par l'API.

Les appels Mistral retentent automatiquement les erreurs temporaires (`429`,
`500`, `502`, `503`, `504`). `MISTRAL_MAX_RETRIES` permet de régler le nombre
de tentatives.

L'API anonymise les e-mails et téléphones avec des règles déterministes. La
reconnaissance spaCy des personnes, organisations et lieux est désactivée par
défaut pour éviter les faux positifs ; elle peut être activée après validation :

```bash
python -m spacy download fr_core_news_sm
```

```env
PII_ENABLE_NER=true
```

## Tests

```bash
pytest
```

## Docker

```bash
docker compose up --build
```

L'interface Gradio reste volontairement séparée de l'API.
