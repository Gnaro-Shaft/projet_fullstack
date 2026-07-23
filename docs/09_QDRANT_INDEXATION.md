# Qdrant et indexation

## Modes

### Cloud ou serveur

```env
QDRANT_URL=https://...
QDRANT_API_KEY=...
```

### Mémoire

```env
QDRANT_URL=:memory:
```

Le mode mémoire est utilisé par les tests CI.

## Collection

La collection est créée à la première indexation avec :

- dimension déduite du premier vecteur ;
- distance cosinus ;
- index de payload `document_id` et `source`.

## Écritures

### Indexation générique

`upsert` génère des UUID aléatoires et stocke un payload générique `text` / `metadata`.

### Synchronisation de corpus

`replace_document` :

1. filtre sur `document_id` et `source` ;
2. supprime les fragments existants ;
3. insère les fragments courants avec UUIDv5 déterministes.

## Lecture des versions

`list_document_hashes(source)` parcourt les points et récupère le dernier `source_hash` par document. Ce mécanisme permet de ne recalculer les embeddings que lorsque le contenu a changé.

## Suppression ciblée

`delete_document(document_id, source)` supprime tous les fragments correspondant aux deux critères.

## Recherche

`search` retourne le texte, l'identifiant, le titre, l'URL, les dates, le statut, les métadonnées et le score Qdrant.
