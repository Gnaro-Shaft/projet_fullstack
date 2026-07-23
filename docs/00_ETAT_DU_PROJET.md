# État du projet au 23 juillet 2026

## Sources

Cette synthèse s'appuie sur :

1. le dépôt fourni après mise à jour de `main` ;
2. le fichier `readme.md` ;
3. la synthèse d'avancement de Cédric ;
4. l'inventaire des 26 tests présents.

Le code est la source de vérité pour l'implémentation. Les statuts d'exécution et de déploiement sont présentés comme communiqués par l'équipe lorsqu'ils ne sont pas vérifiables hors de GitHub et Fly.io.

## Réalisé et vérifié dans le code

- connecteur EUR-Lex / Cellar pour flux RSS ou Atom ;
- téléchargement des notices sur une fenêtre glissante de sept jours ;
- normalisation du titre, identifiant, URL, date, date d'entrée en vigueur, statut et résumé ;
- hash SHA-256 des notices EUR-Lex ;
- synchronisation différentielle Service-Public et EUR-Lex ;
- workflow GitHub Actions quotidien à `02:17 UTC` ;
- lancement manuel du workflow par `workflow_dispatch` ;
- métadonnées juridiques stockées dans Qdrant ;
- journalisation des requêtes sans question brute ;
- hash de la question, longueur de réponse et sources utilisées ;
- anonymisation de la question avant l'appel Mistral ;
- anonymisation supplémentaire de la réponse ;
- bandeau indiquant l'usage d'une IA ;
- disclaimer précisant l'absence d'avis juridique personnalisé ;
- affichage des dates et statuts des sources ;
- endpoint `DELETE /documents/{document_id}` ;
- protection de la suppression par `X-Admin-Key` ;
- workflow de test et déploiement sur chaque push de `main` ;
- déploiements Fly.io backend et frontend séparés ;
- Qdrant en mémoire dans les tests CI ;
- 26 fonctions de test présentes dans le dépôt.

## Résultats communiqués par Cédric

- sprint techniquement validé ;
- tests locaux : `26 passed` ;
- backend et frontend déployés automatiquement après succès des tests ;
- synchronisations Service-Public et EUR-Lex exécutées quotidiennement ;
- réindexation limitée aux nouveautés et modifications.

Ces éléments sont cohérents avec les workflows et le code fournis. La présente analyse n'a pas accès aux historiques d'exécution GitHub Actions ni aux consoles Fly.io.

## Points restant à faire

### Enrichissement EUR-Lex

Le connecteur indexe actuellement les notices du flux : titre, identifiant, URL, date, statut et résumé éventuel. Il ne télécharge pas systématiquement le texte complet des règlements et directives.

### Administration

La clé `X-Admin-Key` protège la suppression, mais il manque :

- une authentification administrateur complète ;
- une limitation des tentatives ;
- un audit spécifique des suppressions ;
- une interface d'administration séparée.

### Validation publique

Il reste à tester :

- plusieurs utilisateurs simultanés ;
- des questions variées ;
- l'affichage des sources, dates et statuts ;
- les erreurs Mistral et Qdrant ;
- les temps de réponse ;
- l'anonymisation en conditions réelles.

### Affichage des sources

Les sources secondaires peuvent être nombreuses. Une évolution possible consiste à n'afficher que trois ou quatre sources principales tout en conservant davantage de fragments dans le contexte interne.

### Historique

Aucune persistance permanente des conversations n'est implémentée. Le frontend conserve uniquement l'échange courant dans la session et le remplace à la question suivante.

## Écarts et dette documentaire

- Le `readme.md` reste centré sur Service-Public et ne décrit pas encore EUR-Lex, les workflows, l'audit, l'administration et la CI/CD.
- Le nom `Jarvis AI API` apparaît encore dans FastAPI, tandis que l'interface et la documentation utilisent TrustRAG-CX / Assistant Service Public.
- `requirements.txt` contient des dépendances sans usage visible dans le code fourni : Haystack, Gradio, PostgreSQL, S3 et MLflow.
- `pytest` est déclaré deux fois dans `requirements.txt`.
- `SPACY_MODEL` et `PII_ENABLE_NER` sont dupliqués dans `.env.example`.
