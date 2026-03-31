# Documentation API — HELMo ORACLE

## Table des matières

1. [Introduction à REST et FastAPI](#introduction-à-rest-et-fastapi)
2. [Architecture de l'API](#architecture-de-lapi)
3. [Authentification](#authentification)
4. [Endpoints FastAPI (Backend)](#endpoints-fastapi-backend)
   - [Santé & Statut](#santé--statut)
   - [Providers & Modèles](#providers--modèles)
   - [Sessions](#sessions)
   - [Chat & RAG](#chat--rag)
   - [Base de connaissances](#base-de-connaissances)
   - [Ingestion de documents](#ingestion-de-documents)
   - [Logs](#logs)
   - [Feedback](#feedback)
5. [Routes Next.js (Frontend)](#routes-nextjs-frontend)
6. [MCP (Model Context Protocol)](#mcp-model-context-protocol)
7. [Codes de réponse HTTP](#codes-de-réponse-http)

---

## Introduction à REST et FastAPI

### Qu'est-ce que REST ?

**REST** (Representational State Transfer) est un style d'architecture pour concevoir des APIs web. Une API REST repose sur quelques principes fondamentaux :

- **Ressources** : tout est une ressource identifiée par une URL (ex: `/sessions`, `/logs`)
- **Méthodes HTTP** : les actions sont exprimées par des verbes HTTP standardisés

| Méthode | Usage | Idempotent | Corps |
|---------|-------|-----------|-------|
| `GET` | Lire une ressource | Oui | Non |
| `POST` | Créer une ressource | Non | Oui |
| `PUT` | Remplacer une ressource | Oui | Oui |
| `PATCH` | Modifier partiellement | Non | Oui |
| `DELETE` | Supprimer une ressource | Oui | Non |

- **Stateless** : chaque requête est indépendante, le serveur ne garde pas d'état entre deux appels
- **Représentation** : les données sont échangées en JSON (généralement)

### Qu'est-ce que FastAPI ?

[FastAPI](https://fastapi.tiangolo.com/) est un framework Python moderne pour construire des APIs REST. Il repose sur :

- **Starlette** : framework ASGI bas niveau (gestion des requêtes HTTP)
- **Pydantic** : validation et sérialisation des données via des schémas Python typés
- **OpenAPI / Swagger** : documentation interactive auto-générée à `/docs`

**Avantages clés :**
- Typage Python natif → validation automatique des entrées/sorties
- Documentation Swagger générée sans effort à `http://localhost:8000/docs`
- Support natif de l'asynchrone (`async/await`)
- Performances proches de Node.js (grâce à Uvicorn/ASGI)

**Exemple de route FastAPI :**
```python
@app.get("/sessions/{session_id}")
async def get_session(session_id: str, user_id: Optional[str] = None):
    # session_id vient de l'URL, user_id est un query param optionnel
    return {"session_id": session_id, "messages": [...]}
```

### Structure d'une requête HTTP

```
POST /chat HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-Api-Key: secret-key          ← Header d'authentification (si requis)

{                              ← Corps (body) en JSON
  "message": "Qui est Socrate ?",
  "session_id": null,
  "provider": "groq"
}
```

---

## Architecture de l'API

```
┌────────────────────────────────────────────────────┐
│              Navigateur / Client                   │
└──────────────────────┬─────────────────────────────┘
                       │ HTTP
┌──────────────────────▼─────────────────────────────┐
│         Next.js  (web/, port 3000)                 │
│   /api/*  →  routes proxy vers le backend          │
│   /api/admin/*  →  routes admin protégées          │
└──────────────────────┬─────────────────────────────┘
                       │ HTTP interne
┌──────────────────────▼─────────────────────────────┐
│         FastAPI  (api/, port 8000)                 │
│   Uvicorn · ASGI · Python                          │
│                                                    │
│   ┌──────────┐  ┌─────────────┐  ┌─────────────┐  │
│   │ Sessions │  │  Chat/RAG   │  │   Ingest    │  │
│   └──────────┘  └─────────────┘  └─────────────┘  │
│   ┌──────────┐  ┌─────────────┐  ┌─────────────┐  │
│   │   Logs   │  │  Feedback   │  │   Health    │  │
│   └──────────┘  └─────────────┘  └─────────────┘  │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│              Supabase (PostgreSQL + pgvector)       │
│   documents · sessions · logs · feedback           │
└────────────────────────────────────────────────────┘
```

**URLs de base :**
- Backend FastAPI : `http://localhost:8000`
- Documentation interactive (Swagger) : `http://localhost:8000/docs`
- Frontend Next.js : `http://localhost:3000`

---

## Authentification

Certains endpoints sont protégés par une clé API transmise dans un header HTTP.

| Mécanisme | Header | Valeur | Endpoints concernés |
|-----------|--------|--------|---------------------|
| Clé API admin | `X-Api-Key` | Valeur de `API_SECRET_KEY` | `/ingest`, `/logs` (DELETE) |
| ID utilisateur | Query param `user_id` | UUID Supabase Auth | Endpoints `/sessions` |
| Mot de passe admin | Body JSON | Hash SHA-256 | `/api/admin/auth` (Next.js) |

**Exemple avec clé API :**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "X-Api-Key: votre-cle-secrete" \
  -F "files=@document.pdf"
```

---

## Endpoints FastAPI (Backend)

> Base URL : `http://localhost:8000`

---

### Santé & Statut

#### `GET /health`

Vérifie l'état de base du service (connexion base de données, modèle d'embeddings).

**Authentification :** aucune

**Réponse 200 :**
```json
{
  "status": "ok",
  "database": "connected",
  "documents_count": 142,
  "embeddings_model": "multilingual-e5-base"
}
```

---

#### `GET /health/full`

Vérifie tous les composants : base de données, embeddings, et chaque provider LLM (Groq, OpenAI, Anthropic, Gemini). Inclut les latences.

**Authentification :** aucune

**Réponse 200 :**
```json
{
  "status": "ok",
  "database": "connected",
  "embeddings": "ok",
  "providers": {
    "groq": { "status": "ok", "latency_ms": 312 },
    "openai": { "status": "ok", "latency_ms": 540 },
    "anthropic": { "status": "error", "detail": "API key missing" },
    "gemini": { "status": "ok", "latency_ms": 420 }
  }
}
```

---

### Providers & Modèles

#### `GET /providers/{provider}/models`

Liste les modèles disponibles pour un provider LLM.

**Authentification :** aucune

**Paramètres de chemin :**
| Paramètre | Type | Valeurs acceptées |
|-----------|------|-------------------|
| `provider` | string | `groq`, `openai`, `anthropic`, `gemini` |

**Exemple :**
```bash
GET /providers/groq/models
```

**Réponse 200 :**
```json
{
  "provider": "groq",
  "models": [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768"
  ]
}
```

---

### Sessions

Les sessions représentent des conversations. Elles stockent l'historique des messages et les paramètres LLM utilisés.

#### `GET /sessions`

Liste les sessions d'un utilisateur (ou toutes les sessions si `user_id` est absent).

**Authentification :** aucune

**Query params :**
| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `user_id` | UUID string | Non | Filtre par utilisateur |

**Réponse 200 :**
```json
{
  "sessions": [
    {
      "id": "a1b2c3d4-...",
      "title": "Question sur Platon",
      "created_at": "2025-03-28T10:00:00Z",
      "provider": "groq",
      "model": "llama-3.1-8b-instant"
    }
  ]
}
```

---

#### `POST /sessions`

Crée une nouvelle session de conversation.

**Authentification :** aucune

**Query params :**
| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `provider` | string | Non | Provider LLM (défaut : groq) |
| `model` | string | Non | Modèle LLM |
| `user_id` | UUID string | Non | Associe la session à un utilisateur |

**Réponse 201 :**
```json
{
  "session_id": "a1b2c3d4-...",
  "created_at": "2025-03-28T10:00:00Z"
}
```

---

#### `GET /sessions/{session_id}`

Récupère une session avec son historique de messages.

**Authentification :** aucune

**Paramètres de chemin :**
| Paramètre | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID string | Identifiant de la session |

**Query params :**
| Paramètre | Type | Requis |
|-----------|------|--------|
| `user_id` | UUID string | Non |

**Réponse 200 :**
```json
{
  "session_id": "a1b2c3d4-...",
  "title": "Question sur Socrate",
  "messages": [
    { "role": "user", "content": "Qui est Socrate ?" },
    { "role": "assistant", "content": "Socrate est un philosophe grec..." }
  ]
}
```

---

#### `DELETE /sessions/{session_id}`

Supprime une session et son historique.

**Authentification :** aucune

**Paramètres de chemin :**
| Paramètre | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID string | Identifiant de la session |

**Réponse 200 :**
```json
{ "deleted": true }
```

---

#### `PATCH /sessions/{session_id}/rename`

Renomme le titre d'une session.

**Authentification :** aucune

**Corps de la requête :**
```json
{ "title": "Nouveau titre" }
```

**Réponse 200 :**
```json
{ "session_id": "a1b2c3d4-...", "title": "Nouveau titre" }
```

---

### Chat & RAG

#### `POST /chat`

Point d'entrée principal. Envoie un message, déclenche le pipeline RAG (recherche vectorielle + LLM), et retourne la réponse.

**Authentification :** aucune

**Pipeline interne :**
1. Masquage des données personnelles (PII)
2. Recherche hybride dans la base de connaissances (cosinus + BM25 + RRF)
3. Construction du prompt avec le contexte récupéré
4. Génération de la réponse via l'agent LangGraph (ReAct)
5. Enregistrement dans l'historique de la session

**Corps de la requête :**
```json
{
  "session_id": "a1b2c3d4-...",
  "message": "Explique-moi la théorie des Idées de Platon",
  "user_id": "uuid-optionnel",
  "provider": "groq",
  "model": "llama-3.1-8b-instant",
  "temperature": 0.0,
  "k_final": 5
}
```

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `session_id` | UUID \| null | Non | `null` pour créer une nouvelle session automatiquement |
| `message` | string | **Oui** | Question de l'utilisateur |
| `user_id` | UUID | Non | Identifiant utilisateur |
| `provider` | string | Non | Provider LLM (défaut : groq) |
| `model` | string | Non | Modèle à utiliser |
| `temperature` | float [0.0–2.0] | Non | Créativité du modèle (défaut : 0.0) |
| `k_final` | integer | Non | Nombre de chunks récupérés (défaut : 5) |

**Réponse 200 :**
```json
{
  "session_id": "a1b2c3d4-...",
  "response": "La théorie des Idées de Platon postule que...",
  "cot_results": []
}
```

---

### Base de connaissances

#### `GET /archives`

Liste tous les documents ingérés dans la base de connaissances vectorielle.

**Authentification :** aucune

**Réponse 200 :**
```json
{
  "sources": [
    {
      "source": "philosophie_grecque.pdf",
      "chunk_count": 87,
      "ingested_at": "2025-03-20T14:30:00Z"
    },
    {
      "source": "cours_ethique.md",
      "chunk_count": 34,
      "ingested_at": "2025-03-22T09:15:00Z"
    }
  ]
}
```

---

### Ingestion de documents

#### `POST /ingest`

Ingère un ou plusieurs documents dans la base de connaissances. Le traitement s'exécute en arrière-plan.

**Authentification :** `X-Api-Key` requis

**Formats acceptés :** CSV, JSON, PDF, Markdown, TXT, DOCX

**Corps de la requête :** `multipart/form-data`
```
files: <fichier1.pdf>
files: <fichier2.md>
```

**Pipeline d'ingestion :**
1. **Guardian** — validation LLM (le document correspond-il au domaine ?)
2. **Conversion** — parsers spécifiques par format (ou Unstructured.io)
3. **Contextualisation** — résumé global généré par LLM
4. **Chunking** — découpage en segments
5. **Embeddings** — `multilingual-e5-base` (768 dimensions)
6. **Vectorisation** — stockage dans Supabase pgvector

**Réponse 202 :**
```json
{
  "started": true,
  "files": ["philosophie_grecque.pdf", "cours_ethique.md"]
}
```

---

#### `GET /ingest/status`

Retourne le statut de la dernière ingestion en cours ou terminée.

**Authentification :** aucune

**Réponse 200 :**
```json
{
  "running": false,
  "last_status": "success",
  "last_message": "2 fichiers ingérés avec succès"
}
```

---

### Logs

#### `GET /logs`

Récupère les logs applicatifs stockés dans Supabase avec filtres optionnels.

**Authentification :** `X-Api-Key` requis

**Query params :**
| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `lines` | integer | 100 | Nombre de logs à retourner |
| `offset` | integer | 0 | Pagination (décalage) |
| `level` | string | — | Filtre par niveau (`INFO`, `WARNING`, `ERROR`) |
| `source` | string | — | Filtre par source (ex: `RAG_PROFILING`) |

**Réponse 200 :**
```json
{
  "logs": [
    {
      "id": "uuid",
      "created_at": "2025-03-28T10:30:00Z",
      "level": "INFO",
      "source": "RAG_PROFILING",
      "message": "Context retrieval finished",
      "metadata": { "duration_seconds": 0.234 },
      "profiles": { "first_name": "John", "last_name": "Doe" }
    }
  ]
}
```

---

#### `DELETE /logs`

Vide le fichier de log local (ne supprime pas les logs en base de données).

**Authentification :** `X-Api-Key` requis

**Réponse 200 :**
```json
{ "cleared": true }
```

---

### Feedback

#### `POST /feedback`

Enregistre un retour utilisateur (note + commentaire optionnel) en base de données.

**Authentification :** aucune

**Corps de la requête :**
```json
{
  "session_id": "a1b2c3d4-...",
  "user_id": "uuid-optionnel",
  "rating": 4,
  "comment": "Réponse très pertinente !"
}
```

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `session_id` | UUID | Non | Session concernée |
| `user_id` | UUID | Non | Utilisateur |
| `rating` | integer [1–5] | **Oui** | Note de 1 à 5 |
| `comment` | string | Non | Commentaire libre |

**Réponse 201 :**
```json
{ "saved": true }
```

---

## Routes Next.js (Frontend)

> Base URL : `http://localhost:3000/api`

Ces routes sont des **proxies** vers le backend FastAPI. Elles ajoutent l'identifiant utilisateur extrait de la session Supabase Auth, puis transfèrent la requête au backend.

| Méthode | Route Next.js | Proxy vers FastAPI | Auth requise |
|---------|--------------|-------------------|--------------|
| `POST` | `/api/chat` | `POST /chat` | Session utilisateur |
| `GET` | `/api/sessions` | `GET /sessions` | Session utilisateur |
| `POST` | `/api/sessions` | `POST /sessions` | Session utilisateur |
| `GET` | `/api/sessions/[id]` | `GET /sessions/{id}` | Session utilisateur |
| `DELETE` | `/api/sessions/[id]` | `DELETE /sessions/{id}` | Session utilisateur |
| `GET` | `/api/sources` | `GET /archives` | Aucune |
| `POST` | `/api/feedback` | `POST /feedback` | Session utilisateur |
| `POST` | `/api/admin/auth` | — (validation locale) | Mot de passe admin |
| `GET` | `/api/admin/health` | `GET /health/full` | Aucune |
| `POST` | `/api/admin/ingest` | `POST /ingest` | `X-Api-Key` |
| `GET` | `/api/admin/ingest/status` | `GET /ingest/status` | `X-Api-Key` |
| `GET` | `/api/admin/logs` | `GET /logs` | `X-Api-Key` |

---

## MCP (Model Context Protocol)

Le serveur MCP est monté sur `/mcp` dans FastAPI. Il expose des outils utilisables par des agents LLM compatibles MCP.

**URL :** `http://localhost:8000/mcp`

### Outil : `search_knowledge_base`

Effectue une recherche hybride (cosinus + BM25 + RRF) dans la base de connaissances.

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `query` | string (max 500 chars) | **Oui** | Requête en langage naturel |
| `k` | integer | Non (défaut : 5) | Nombre de résultats |

**Retourne :** résultats formatés avec source, score de confiance, score RRF.

---

### Outil : `list_sources`

Liste tous les documents ingérés avec leur nombre de chunks et date d'ingestion.

**Paramètres :** aucun

**Retourne :** liste Markdown des sources disponibles.

---

## Codes de réponse HTTP

| Code | Signification | Contexte typique |
|------|--------------|-----------------|
| `200 OK` | Succès | GET, PATCH, DELETE réussis |
| `201 Created` | Ressource créée | POST /sessions, POST /feedback |
| `202 Accepted` | Traitement en cours | POST /ingest (background) |
| `400 Bad Request` | Paramètres invalides | Body malformé, champ manquant |
| `401 Unauthorized` | Clé API manquante ou invalide | Endpoints protégés par `X-Api-Key` |
| `404 Not Found` | Ressource introuvable | Session inexistante |
| `422 Unprocessable Entity` | Validation échouée (Pydantic) | Type incorrect, contrainte violée |
| `500 Internal Server Error` | Erreur serveur | Erreur LLM, base de données inaccessible |
