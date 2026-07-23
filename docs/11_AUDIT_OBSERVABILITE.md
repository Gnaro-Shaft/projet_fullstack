# Audit et observabilité

## Journal de chat

Par défaut :

```text
data/audit/chat_audit.jsonl
```

Chaque ligne contient :

```json
{
  "event": "chat",
  "request_id": "uuid",
  "timestamp": "ISO-8601 UTC",
  "question_sha256": "…",
  "response_length": 412,
  "sources": [
    {
      "document_id": "F123",
      "url": "https://…",
      "modified_at": "2026-01-01",
      "effective_at": null,
      "status": "published"
    }
  ]
}
```

La question et la réponse ne sont pas stockées en clair. Le code journalise la longueur de la réponse, pas son contenu.

## Logs applicatifs

Un message de niveau INFO indique l'identifiant de requête et le nombre de sources.

## Ce qui manque

- latence par étape ;
- statut HTTP ;
- nombre de candidats et de fragments ;
- modèle utilisé ;
- coût ou volume de tokens ;
- erreurs structurées ;
- métriques Mistral et Qdrant ;
- traces distribuées ;
- audit de suppression ;
- politique de rotation du JSONL.

## Recommandation

Pour une production durable, utiliser un format structuré unique et un stockage centralisé, tout en définissant une politique de minimisation et de rétention.
