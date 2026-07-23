# Déploiement Fly.io

## Applications

| Application | Fichier | Port interne | Dockerfile |
|---|---|---:|---|
| Backend FastAPI | `fly.toml` | 8000 | `Dockerfile` |
| Frontend Streamlit | `fly.frontend.toml` | 8501 | `Dockerfile.streamlit` |

Les deux applications utilisent la région `cdg`, HTTPS forcé et arrêt/démarrage automatique des machines.

## Backend

Le Dockerfile :

- part de Python 3.13 slim ;
- installe `requirements.txt` ;
- copie `config`, `services` et `scripts` ;
- lance Uvicorn sur le port 8000.

## Frontend

Le Dockerfile Streamlit :

- installe uniquement `requirements.frontend.txt` ;
- copie le frontend ;
- utilise la variable `PORT` fournie par Fly.io.

## Secrets backend

Exemples :

```bash
fly secrets set \
  MISTRAL_API_KEY="..." \
  QDRANT_URL="..." \
  QDRANT_API_KEY="..." \
  QDRANT_COLLECTION="..." \
  ADMIN_API_KEY="..." \
  --app projet-fullstack
```

## Secret frontend

```bash
fly secrets set \
  BACKEND_URL="https://projet-fullstack.fly.dev" \
  --app trustrag-frontend
```

## Déploiement manuel

```bash
flyctl deploy --config fly.toml --app projet-fullstack --remote-only
flyctl deploy --config fly.frontend.toml --app trustrag-frontend --remote-only
```

## Déploiement automatique

Tout push sur `main` lance les tests puis les deux déploiements.

## Vérifications

```bash
curl https://projet-fullstack.fly.dev/ping
curl https://projet-fullstack.fly.dev/qdrant/health
```

Vérifier ensuite l'application Streamlit depuis plusieurs appareils et réseaux.
