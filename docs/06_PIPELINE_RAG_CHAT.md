# Pipeline RAG et chat

## Étapes

1. validation Pydantic de la question ;
2. anonymisation de la question ;
3. embedding Mistral ;
4. récupération de 12 candidats Qdrant ;
5. reranking local ;
6. sélection de 8 fragments pour le contexte ;
7. déduplication des sources affichées ;
8. génération Mistral ;
9. anonymisation de la réponse ;
10. journalisation ;
11. retour de la réponse et des sources.

## Reranking

Le score final est :

```text
0,65 × score sémantique + 0,35 × score lexical
```

Le score lexical mesure la proportion de mots significatifs de la question présents dans le titre et le texte.

Le contexte conserve plusieurs fragments d'une même fiche, alors que les citations sont dédupliquées par `document_id`.

## Prompt de génération

Le modèle doit :

- répondre uniquement à partir du contexte ;
- ne pas inventer de chiffre, date, délai, condition, lien ou procédure ;
- signaler explicitement les informations absentes ;
- inviter à consulter la source officielle ;
- produire une réponse concise.

## Absence de résultat

Lorsque le reranking ne retourne aucun fragment :

```text
Je ne trouve pas cette information dans les documents disponibles.
```

## Gestion des erreurs

Les erreurs Mistral et Qdrant sont transformées en réponse HTTP `503`.

Mistral retente les statuts `429`, `500`, `502`, `503` et `504` avec `Retry-After` ou backoff exponentiel.
