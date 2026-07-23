# Tests et validation

## Suite présente

Le dépôt contient 26 tests couvrant :

- téléchargement Service-Public ;
- extraction XML et bloc `Texte` ;
- chunking ;
- synchronisation différentielle ;
- remplacement des fragments Qdrant ;
- Qdrant en mémoire ;
- reranking ;
- retries Mistral ;
- anonymisation PII ;
- API ;
- endpoint de suppression ;
- audit ;
- conformité de l'interface ;
- parseur EUR-Lex ;
- golden set et recall.

## Exécution locale

```bash
python -m pytest -q
```

Résultat communiqué par Cédric :

```text
26 passed
```

## CI

La CI fixe :

```env
QDRANT_URL=:memory:
QDRANT_COLLECTION=test_documents
```

Elle n'utilise donc pas les secrets Qdrant de production pour tester.

## Golden set

Le fichier `tests/fixtures/golden_set.json` contient dix questions de référence. Deux niveaux existent :

- `scripts/evaluate_golden_set.py` mesure le retrieval ;
- `scripts/validate_chat.py` teste le parcours via `/chat`.

Un score `1,0` a été communiqué lors du sprint précédent. Il doit être interprété dans le contexte du jeu de dix questions et ne prouve pas la performance générale sur toutes les formulations.

## Validation complémentaire recommandée

- jeu de 25 questions variées ;
- questions hors périmètre ;
- données personnelles ;
- erreurs Mistral ;
- erreurs Qdrant ;
- latence ;
- concurrence ;
- précision des dates et statuts ;
- qualité des sources secondaires ;
- textes EUR-Lex complets lorsqu'ils seront ajoutés.
