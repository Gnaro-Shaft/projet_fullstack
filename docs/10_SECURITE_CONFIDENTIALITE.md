# Sécurité et confidentialité

## Anonymisation

### Entrée

La question est anonymisée avant la création de l'embedding et avant la génération Mistral.

### Sortie

La réponse du modèle est anonymisée une seconde fois avant d'être renvoyée.

### Données couvertes

Toujours actives :

- adresses e-mail ;
- numéros de téléphone français.

Optionnelles avec `PII_ENABLE_NER=true` :

- personnes ;
- organisations ;
- lieux.

Le NER est désactivé par défaut pour éviter les faux positifs.

## Logs

Le journal d'audit ne stocke pas la question en clair. Il stocke son SHA-256, qui permet de rapprocher deux questions identiques mais ne constitue pas un anonymat parfait pour des questions courtes ou prévisibles.

## Administration

La suppression nécessite `X-Admin-Key`. La clé :

- doit être longue et aléatoire ;
- doit être stockée dans un secret ;
- ne doit jamais être committée ;
- doit être distincte des clés Mistral, Qdrant et Fly.io.

## Interface

Le frontend indique explicitement que :

- l'assistant utilise une IA ;
- les réponses doivent être vérifiées à la source ;
- la réponse ne constitue pas un avis juridique personnalisé.

## Risques résiduels

- absence de rate limiting ;
- clé administrateur unique ;
- pas d'audit des suppressions ;
- fichier d'audit local non chiffré ;
- hash de question vulnérable à une attaque par dictionnaire ;
- URL de sources potentiellement malformées ;
- NER optionnel et couverture PII incomplète ;
- dépendance à des services externes.

## Recommandations prioritaires

1. authentification d'administration ;
2. journal d'audit des suppressions ;
3. limitation des requêtes et tentatives ;
4. politique de rétention du fichier d'audit ;
5. chiffrement et stockage centralisé des logs en production ;
6. tests PII sur données réalistes ;
7. validation stricte des URL affichées.
