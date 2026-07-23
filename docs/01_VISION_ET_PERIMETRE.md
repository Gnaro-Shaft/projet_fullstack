# Vision et périmètre

## Finalité

TrustRAG-CX aide un utilisateur à retrouver et comprendre des informations administratives et juridiques à partir de sources officielles.

Le produit réduit le temps de recherche, mais ne remplace ni le texte officiel ni un professionnel du droit.

## Sources actuellement intégrées

### Service-Public

Corpus XML de fiches administratives françaises, découpé en fragments et indexé dans Qdrant.

### EUR-Lex / Cellar

Notices issues d'un flux RSS ou Atom européen. Le connecteur actuel fournit surtout les métadonnées et le résumé éventuel, pas systématiquement le texte juridique intégral.

## Capacités

- recherche sémantique ;
- correction lexicale par reranking ;
- génération strictement guidée par le contexte ;
- citations avec URL et métadonnées ;
- synchronisation différentielle ;
- automatisation quotidienne ;
- anonymisation de données sensibles ;
- audit technique minimal ;
- déploiement backend et frontend séparé.

## Non-objectifs actuels

- conseil juridique personnalisé ;
- garantie d'exhaustivité juridique ;
- mémoire conversationnelle permanente ;
- authentification des usagers ;
- interface complète d'administration ;
- stockage du texte complet de tout EUR-Lex ;
- résilience de production démontrée par tests de charge.

## Principes

1. **Sources officielles avant génération.**
2. **Pas d'invention lorsqu'une information manque.**
3. **Minimisation des données personnelles.**
4. **Mise à jour différentielle plutôt que réindexation systématique.**
5. **Traçabilité entre réponse et sources.**
6. **Déploiement conditionné par les tests.**
