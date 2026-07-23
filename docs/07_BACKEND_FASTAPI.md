# Backend FastAPI

## Application

- module : `services.main` ;
- objet : `app` ;
- titre actuel : `Jarvis AI API` ;
- version : `0.1.0`.

Le cycle de vie initialise un client Mistral, un magasin Qdrant, un anonymiseur et un journal d'audit.

## Routes

| Méthode | Route | Usage |
|---|---|---|
| `GET` | `/` | Message d'accueil |
| `GET` | `/ping` | Santé minimale |
| `GET` | `/qdrant/health` | Test de connexion Qdrant |
| `POST` | `/documents` | Indexation générique de documents |
| `POST` | `/chat` | Question RAG |
| `DELETE` | `/documents/{document_id}` | Suppression ciblée par source |

## Contrat `/chat`

Requête :

```json
{"message": "Quelles sont les conditions pour obtenir un logement social ?"}
```

Réponse :

```json
{
  "response": "…",
  "sources": [
    {
      "document_id": "F869",
      "title": "…",
      "url": "…",
      "modified_at": "…",
      "effective_at": null,
      "status": "published",
      "score": 0.82,
      "rerank_score": 0.76
    }
  ]
}
```

Le champ `text` des fragments n'est pas exposé au frontend.

## Suppression administrative

```bash
curl -X DELETE \
  "http://localhost:8000/documents/F123?source=service-public-vdd" \
  -H "X-Admin-Key: $ADMIN_API_KEY"
```

La comparaison de la clé utilise `secrets.compare_digest`.

## Limites

- aucune authentification utilisateur ;
- aucune limitation de débit ;
- aucune trace dédiée aux suppressions ;
- aucun identifiant de requête transmis depuis le client ;
- gestion d'erreur frontend volontairement simple.
