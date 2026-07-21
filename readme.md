# Jarvis AI API

API FastAPI minimale qui envoie les messages à Mistral.

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

## Tests

```bash
pytest
```

## Docker

```bash
docker compose up --build
```

Qdrant et l'interface Gradio ne sont volontairement pas inclus dans cette
première version. Ils seront ajoutés une fois le chat validé.
