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
