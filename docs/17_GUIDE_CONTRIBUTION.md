# Guide de contribution

## Flux recommandé

1. mettre `main` à jour ;
2. créer une branche courte ;
3. modifier code, tests et documentation ;
4. exécuter les tests ;
5. committer ;
6. pousser la branche ;
7. ouvrir une Pull Request vers `main`.

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/nom-court
```

## Qualité attendue

Toute évolution doit inclure :

- un test automatisé ;
- une mise à jour documentaire ;
- une gestion d'erreur ;
- une vérification de confidentialité ;
- une description de migration si le payload Qdrant change.

## Documentation

- Mermaid pour la vue versionnée ;
- PowerPoint pour la présentation détaillée ;
- ADR pour toute décision structurante ;
- exemples reproductibles ;
- état « existant », « déclaré » ou « prévu » explicite.

## Fichiers à ne pas committer

- `.env` ;
- `.venv/` ;
- archives XML ;
- manifestes locaux ;
- caches ;
- fichiers d'audit réels ;
- dossier privé d'entretien.

Le fichier `data/audit/chat_audit.jsonl` présent dans l'archive ressemble à une donnée d'exécution et devrait normalement être ignoré ou remplacé par un exemple synthétique.
