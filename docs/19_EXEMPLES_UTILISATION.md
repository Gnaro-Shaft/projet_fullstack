# Exemples reproductibles

## Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Quelles sont les conditions pour obtenir un logement social ?"}'
```

## Indexation générique

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "text": "Paris est la capitale de la France.",
        "metadata": {"source": "demo"}
      }
    ]
  }'
```

## Suppression Service-Public

```bash
curl -X DELETE \
  "http://localhost:8000/documents/F123?source=service-public-vdd" \
  -H "X-Admin-Key: $ADMIN_API_KEY"
```

## Suppression EUR-Lex

```bash
curl -X DELETE \
  "http://localhost:8000/documents/eurlex-IDENTIFIANT?source=eurlex-rss" \
  -H "X-Admin-Key: $ADMIN_API_KEY"
```

## Synchronisation limitée

```bash
python -m scripts.sync_service_public --limit 10
python -m scripts.sync_legal_feed --limit 10
```

## Workflow quotidien manuel

Dans GitHub :

1. ouvrir **Actions** ;
2. choisir **Synchronize legal feeds** ;
3. cliquer **Run workflow** ;
4. sélectionner `main` ;
5. lancer et consulter les deux étapes de synchronisation.

## Vérification de conformité UI

```bash
python -m pytest -q tests/test_compliance.py
```

## Vérification Qdrant en mémoire

```bash
QDRANT_URL=:memory: \
QDRANT_COLLECTION=test_documents \
python -m pytest -q tests/test_qdrant_store.py
```
