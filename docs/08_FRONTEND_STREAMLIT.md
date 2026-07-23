# Frontend Streamlit

## Fonctionnalités

- formulaire de question ;
- appel HTTP vers `BACKEND_URL/chat` ;
- spinner pendant la recherche ;
- affichage d'une seule question et d'une seule réponse ;
- cartes de sources ;
- date de modification ;
- date d'entrée en vigueur ;
- statut ;
- bandeau « Assistant utilisant une IA » ;
- disclaimer juridique.

## Confidentialité de session

`st.session_state.messages` conserve uniquement l'échange courant. À chaque nouvelle question, l'ancien échange est remplacé.

Cette absence de persistance durable réduit la collecte de données, mais empêche :

- la reprise d'une conversation ;
- l'analyse multi-tour ;
- le suivi utilisateur ;
- la récupération après fermeture de session.

## Configuration backend

```env
BACKEND_URL=https://url-du-backend.example
```

Le code retire le slash final avant de construire `/chat`.

## Affichage des sources

Toutes les sources renvoyées par l'API sont affichées. Une amélioration prévue consiste à limiter l'affichage aux trois ou quatre principales, sans réduire le contexte interne du modèle.

## Erreurs

Une erreur HTTP est convertie en message :

```text
Le backend est indisponible : …
```

Une UX de production devrait distinguer indisponibilité réseau, erreur Mistral, erreur Qdrant et délai dépassé.
