# Architecture générale

## Vue fonctionnelle

```mermaid
flowchart TB
    subgraph Utilisateur
      U[Navigateur]
    end

    subgraph Présentation
      ST[Streamlit]
    end

    subgraph API
      FA[FastAPI]
      PII[PIIAnonymizer]
      RR[Reranker local]
      AL[AuditLogger]
    end

    subgraph Services externes
      MI[Mistral API]
      QD[(Qdrant)]
      FLY[Fly.io]
    end

    subgraph Sources
      SP[Archive XML Service-Public]
      EU[Flux EUR-Lex / Cellar]
    end

    subgraph Automatisation
      GA1[Workflow sync quotidien / manuel]
      GA2[Workflow tests + déploiement sur main]
    end

    U --> ST
    ST -->|POST /chat| FA
    FA --> PII
    PII -->|question anonymisée| MI
    MI -->|vecteur| FA
    FA --> QD
    QD -->|12 candidats| RR
    RR -->|8 fragments de contexte| MI
    MI -->|réponse| PII
    PII --> FA
    FA --> AL
    FA --> ST

    GA1 --> SP
    GA1 --> EU
    SP -->|extraction + hash| MI
    EU -->|normalisation + hash| MI
    MI --> QD

    GA2 -->|pytest, Qdrant mémoire| FA
    GA2 --> FLY
```

## Vue du parcours d'une question

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant S as Streamlit
    participant A as FastAPI
    participant P as Anonymiseur
    participant M as Mistral
    participant Q as Qdrant
    participant R as Reranker
    participant L as Audit

    U->>S: Question
    S->>A: POST /chat
    A->>P: Anonymiser la question
    P-->>A: Question nettoyée
    A->>M: Créer l'embedding
    M-->>A: Vecteur
    A->>Q: Rechercher 12 candidats
    Q-->>A: Fragments + scores + métadonnées
    A->>R: Reranker
    R-->>A: 8 fragments de contexte
    A->>M: Générer à partir du contexte
    M-->>A: Réponse
    A->>P: Anonymiser la sortie
    A->>L: Écrire l'événement sans question brute
    A-->>S: Réponse + sources publiques
    S-->>U: Réponse, dates, statuts, liens
```

## Composants

| Composant | Responsabilité | Fichier principal |
|---|---|---|
| Streamlit | Saisie, réponse, avertissements et sources | `frontend/streamlit_app.py` |
| FastAPI | Contrats HTTP et orchestration | `services/main.py` |
| PIIAnonymizer | Masquage e-mails, téléphones et NER optionnel | `services/pii.py` |
| MistralClient | Embeddings, génération et retries | `services/llm.py` |
| QdrantStore | Stockage, recherche, hash et suppression | `services/qdrant_store.py` |
| Reranker | Combinaison score vectoriel / mots-clés | `services/reranker.py` |
| AuditLogger | Trace JSONL sans question brute | `services/audit.py` |
| Service-Public | Téléchargement, extraction et sync | `scripts/*service_public.py` |
| EUR-Lex | Lecture du flux et sync différentielle | `scripts/legal_feed_eurlex.py`, `scripts/sync_legal_feed.py` |
| GitHub Actions | Tests, déploiements et synchronisations | `.github/workflows/*.yml` |

## PowerPoint et Mermaid

Le diagramme PowerPoint est utile pour la présentation et les vues détaillées. Mermaid sert de vue de référence versionnée avec le code. Les deux doivent rester cohérents, sans chercher à dupliquer toutes les slides dans Markdown.
