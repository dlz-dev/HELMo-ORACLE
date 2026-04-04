# 🏛️ Architecture et Sécurité Backend : HELMo Oracle

## 1. Vue d'ensemble du Système

HELMo Oracle repose sur une architecture hybride séparant le moteur d'Intelligence Artificielle de la gestion des utilisateurs.

**Moteur RAG (FastAPI — `api.py`)** : Expose une API RESTful. Il interagit avec une base de données vectorielle hébergée sur Digital Ocean (PostgreSQL + `pgvector`) pour la recherche documentaire. Il gère également l'ingestion des documents et communique avec divers LLMs (Groq, OpenAI, Anthropic, Gemini) via LangGraph/ReAct.

**Gestion Utilisateurs & État (Supabase)** : Gère l'authentification (OAuth), le stockage des sessions de chat, les logs système et les feedbacks. Le backend FastAPI maintient deux connexions distinctes vers Supabase :
- Un **client Python `supabase-py`** (via `SUPABASE_ANON_KEY`) utilisé pour les insertions de feedback.
- Une **connexion `psycopg` directe** (via `LOG_DATABASE_URL`) dédiée aux logs, avec reconnexion automatique assurée par `_ensure_log_conn()`.

**Frontend (Next.js/Vercel)** : Communique avec Supabase pour l'authentification (récupération du JWT) et avec l'API FastAPI pour les requêtes de chat. Le `user_id` (UUID extrait du JWT Supabase) est transmis explicitement à chaque requête vers FastAPI.

---

## 2. Base de Données et Sécurité (PostgreSQL & RLS)

Le schéma de base de données (`schema_docker.sql`) intègre la sécurité directement au niveau de la donnée grâce au **Row Level Security (RLS)**.

> ⚠️ **Note sur les environnements** : Le fichier `schema_docker.sql` fourni correspond au mode **Docker/hors-Supabase** (sans foreign key vers `auth.users`). En production Supabase, la fonction `auth.uid()` est disponible car `auth.users` est géré nativement — les politiques RLS ci-dessous s'appliquent donc uniquement en contexte Supabase.

### 2.1. Séparation des Privilèges

**Backend FastAPI (`Service Role`)** : Possède un accès complet en lecture/écriture à toutes les tables, contournant le RLS, afin de gérer les vecteurs, d'écrire les logs globaux et d'orchestrer l'application.

**Frontend (`Authenticated Role` via PostgREST)** : Accède aux données de manière restreinte. L'identité est garantie par le JWT fourni par Supabase Auth. La fonction `auth.uid()` est utilisée pour filtrer les accès en temps réel.

### 2.2. Matrice des Politiques RLS

Toutes les tables sensibles ont le RLS activé (`ENABLE ROW LEVEL SECURITY`).

| Table | Politique RLS (Rôle : `authenticated`) | Description |
| :--- | :--- | :--- |
| `documents` | *Aucun accès direct* | Réservé au backend FastAPI pour l'ingestion et la recherche RAG. |
| `chat_sessions` | `ALL` (USING `auth.uid() = user_id`) | Les utilisateurs ne peuvent lire, modifier ou supprimer que leurs propres historiques de conversation. |
| `feedback` | `INSERT` (WITH CHECK `auth.uid() = user_id`) | Un utilisateur peut soumettre une note (1–5) et un commentaire, liés à son identité. |
| `logs` | `INSERT` (WITH CHECK `true`) | Le frontend peut insérer des logs d'erreurs, mais la lecture est strictement bloquée pour les rôles non-admin. |
| `profiles` | `SELECT` / `UPDATE` | Lecture publique ou restreinte selon l'implémentation frontend ; mise à jour limitée à son propre profil. |

---

## 3. Pipeline de Traitement — `/chat`

L'endpoint `POST /chat` est le cœur du système. Il orchestre plusieurs couches de traitement avant de retourner une réponse.

### 3.1. Masquage des PII (`PIIManager` — `pii_manager.py`)

Avant tout envoi au LLM, le message utilisateur est **anonymisé** par le `PIIManager`. Ce module applique une approche hybride :

1. **Regex structurées** : détection et remplacement des adresses email (`[EMAIL]`), numéros de téléphone (`[PHONE]`) et adresses IP (`[IP_ADDR]`).
2. **NER via SpaCy** (`fr_core_news_sm`) : reconnaissance et remplacement des entités nommées — personnes (`[PERSON]`), lieux (`[LOCATION]`), organisations (`[ORG]`). Le modèle SpaCy est chargé en **Singleton** pour éviter les rechargements à chaque requête. Les remplacements sont triés par longueur décroissante pour éviter les masquages partiels de sous-chaînes.

### 3.2. Gestion de la Mémoire Contextuelle (`MemoryManager` — `memory_manager.py`)

Le `MemoryManager` implémente une stratégie **SummaryBuffer** pour maintenir le contexte conversationnel dans les limites du budget de tokens :

- Une **fenêtre glissante** (`_get_recent_window`) conserve les messages récents tant que leur total estimé (1 token ≈ 3 caractères) reste sous `max_recent_tokens` (défaut : 1200), avec un minimum garanti de `min_recent_messages` messages (défaut : 4).
- Quand la fenêtre déborde (`needs_summarization`), les messages les plus anciens sont **compressés** (`compress`) : un LLM génère un résumé cumulatif qui est stocké dans `session["summary"]`.
- Ce résumé est ensuite **injecté dans le prompt système** (`build_agent_input`) comme contexte mémoriel, permettant à l'agent de connaître l'historique même si les messages bruts ont été élagués.

### 3.3. Flux complet d'une requête `/chat`

```
Frontend (Next.js)
    │  POST /chat { message, user_id, session_id, provider, model, ... }
    ▼
PIIManager.mask_text(message)          ← Anonymisation PII (Regex + SpaCy NER)
    │
    ▼
SessionManager.load / new_session()    ← Chargement ou création de session
    │
    ▼
MemoryManager.build_agent_input()      ← Fenêtre glissante + résumé injecté
    │
    ▼
LangGraph ReAct Agent                  ← LLM + outil de recherche vectorielle (pgvector)
    │
    ▼
MemoryManager.needs_summarization()    ← Compression si dépassement du budget tokens
    │
    ▼
SessionManager.save()                  ← Persistance Supabase ou JSON local
    │
    ▼
{ session_id, response, cot_results }  → Frontend
```

---

## 4. Gestion des Sessions (`SessionManager` — `session_manager.py`)

Le module `session_manager.py` implémente un design pattern **Strategy** pour gérer la persistance des conversations selon l'environnement.

### 4.1. Routage par environnement

| Condition | Backend activé | Stockage |
| :--- | :--- | :--- |
| `ENV=production` + Supabase accessible | `_SupabaseBackend` | Table `chat_sessions` (Supabase) |
| `ENV=production` + Supabase inaccessible | `_LocalBackend` (fallback) | Fichiers JSON (`STORAGE_DIR/<user_id>/`) |
| `ENV=local` (défaut) | `_LocalBackend` | Fichiers JSON (`STORAGE_DIR/local_dev/`) |

### 4.2. Scoping par `user_id`

Le `SessionManager` est instancié **par requête** dans `api.py` via `_get_sm(user_id)`. Si un `user_id` UUID valide est fourni (transmis par le frontend depuis le JWT Supabase), il est utilisé directement. Sinon, le système bascule sur `get_current_user_id()` (variable d'environnement `USER_ID`) ou `"anonymous_local"` en dernier recours.

### 4.3. Auto-titrage des sessions

Lors du premier message utilisateur, le titre de la session (`"New conversation"`) est automatiquement remplacé par les 60 premiers caractères du message, via `_make_title()`.

---

## 5. API Endpoints Complets (FastAPI)

### 5.1. Santé et Monitoring

| Méthode | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | — | Statut basique : connectivité DB (`pgvector`) et modèle embeddings. |
| `GET` | `/health/full` | — | Vérification approfondie : DB, embeddings (avec latence ms), et test live de chaque provider LLM configuré (Groq, OpenAI, Anthropic, Gemini). Retourne `"degraded"` si l'un des composants est en erreur. |

### 5.2. Conversations (RAG)

| Méthode | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/chat` | — | Point d'entrée principal. Masque les PII, exécute l'agent ReAct, gère la mémoire contextuelle et retourne `{ session_id, response, cot_results }`. |
| `GET` | `/sessions` | — | Liste les sessions de l'utilisateur (`?user_id=<uuid>`). |
| `POST` | `/sessions` | — | Crée une nouvelle session vide (`?provider=&model=&user_id=`). |
| `GET` | `/sessions/{id}` | — | Charge le détail d'une session (messages, résumé, métadonnées). |
| `DELETE` | `/sessions/{id}` | — | Supprime une session. |
| `PATCH` | `/sessions/{id}/rename` | — | Renomme une session (`{ "title": "..." }`). |

### 5.3. Ingestion de Documents

| Méthode | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/ingest` | API Key (`X-Api-Key`) | Upload de fichiers. Lance un thread asynchrone qui : valide (Guardian), convertit (CSV/MD/TXT/JSON/PDF/autre), génère un contexte global via LLM, vectorise et archive. Les fichiers invalides sont mis en quarantaine. |
| `GET` | `/ingest/status` | — | Retourne l'état en cours de l'ingestion (`running`, `last_status`, `last_message`). |
| `GET` | `/archives` | — | Liste les sources documentaires déjà ingérées (via `VectorManager`). |

### 5.4. Système

| Méthode | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/logs` | API Key (`X-Api-Key`) | Récupération paginée des logs Supabase avec filtres optionnels `level` et `source`. Inclut les profils utilisateurs (jointure `profiles`). |
| `DELETE` | `/logs` | API Key (`X-Api-Key`) | Efface le fichier de logs local (n'affecte pas la base Supabase). |
| `POST` | `/feedback` | — | Insère un retour utilisateur (`rating` 1–5, `comment` optionnel). Écrit également une entrée dans les logs DB via `log_to_db_sync`. |
| `GET` | `/providers/{provider}/models` | — | Liste les modèles disponibles pour un provider donné (`groq`, `openai`, `anthropic`, `gemini`). |

### 5.5. MCP Server

| Endpoint | Description |
| :--- | :--- |
| `/mcp/*` | Point de montage du serveur MCP (`streamable_http_app`). Expose les outils Oracle pour une intégration avec des clients compatibles MCP. |

---

## 6. Sécurité des Endpoints

Deux niveaux d'accès sont définis :

**Accès libre** : Les endpoints publics (`/chat`, `/sessions`, `/feedback`, `/health`, etc.) ne requièrent pas d'authentification côté FastAPI. La sécurité repose sur le RLS Supabase via le `user_id` transmis dans le corps de la requête, validé comme UUID avant usage.

**Accès admin (API Key)** : Les endpoints sensibles (`/ingest`, `/logs`) sont protégés par le header `X-Api-Key`, vérifié contre la variable d'environnement `API_SECRET_KEY`. Un header manquant ou invalide retourne une `HTTP 401`.