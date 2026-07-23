# Installation et configuration

## Prérequis

- Python 3.13 recommandé, car les images Docker et workflows utilisent cette version ;
- compte Mistral ;
- Qdrant Cloud ou Qdrant local ;
- Git ;
- Docker facultatif pour le lancement conteneurisé.

## Environnement Python

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Sous Windows PowerShell :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
```

Renseigner au minimum :

```env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=jarvis_documents
MISTRAL_API_KEY=...
BACKEND_URL=http://localhost:8000
ADMIN_API_KEY=une-cle-longue-et-aleatoire
```

Ne jamais committer `.env`.

## Backend

```bash
python -m uvicorn services.main:app --reload
```

## Frontend

```bash
python -m streamlit run frontend/streamlit_app.py
```

## Docker Compose

```bash
docker compose up --build
```

Cette commande démarre l'API et Qdrant local. Le frontend Streamlit n'est pas inclus dans le `docker-compose.yml` actuel ; il se lance séparément ou via son Dockerfile.

## Vérifications

```bash
curl http://localhost:8000/ping
curl http://localhost:8000/qdrant/health
```

## Points de vigilance

- `QDRANT_URL` est obligatoire au démarrage de l'application.
- `MISTRAL_API_KEY` est nécessaire pour les embeddings et la génération.
- `ADMIN_API_KEY` est nécessaire pour autoriser la suppression ciblée.
- Le NER spaCy est désactivé par défaut ; les regex e-mail et téléphone restent actives.
