# 🔮 HeLMO Oracle

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Auth%20%2F%20Logs-3ECF8E?logo=supabase&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-FF6B6B?logo=langchain&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)

**HeLMO Oracle** est un moteur RAG *(Retrieval-Augmented Generation)* générique développé dans le cadre d'un projet académique à **HeLMO** (Haute École Libre Mosane).

La démo tourne sur le lore de **Dofus** (MMORPG d'Ankama), mais l'architecture est entièrement générique : n'importe quel corpus de documents peut être ingéré pour créer un Oracle sur mesure, sans modifier une seule ligne de code.

**Équipe** : Tim · Maxime · Arnaud

---

## Démo en ligne

| Service | URL |
|---------|-----|
| Interface de chat | https://oracle.dlzteam.com |
| Page vitrine | https://tritech.dlzteam.com |
| API backend | https://api.dlzteam.com/docs |

---

## Architecture

```
HeLMO-Oracle/
├── api/              ← Backend Python (FastAPI) — Docker sur Digital Ocean
│   ├── core/         ← Pipeline RAG, mémoire, sessions, PII
│   ├── converters/   ← Parseurs CSV, JSON, MD, TXT, PDF, Unstructured
│   ├── providers/    ← Groq, OpenAI, Anthropic, Gemini
│   ├── config/       ← Prompts système (prompt.txt, prompt_guardian.txt, …)
│   └── data/         ← Fichiers à ingérer / quarantaine
└── web/              ← Frontend Next.js — Vercel
    ├── app/          ← Pages : Oracle, Sources, Admin
    └── components/   ← Chat, Sessions, Admin panel
```

**Deux bases de données séparées :**

| Base | Hébergement | Rôle |
|------|-------------|------|
| PostgreSQL + pgvector | Digital Ocean (ou Docker local) | Documents, embeddings, recherche vectorielle |
| Supabase | Supabase cloud | Auth utilisateurs, sessions de chat, logs, feedback |

**Flux RAG :**
```
Question utilisateur
  → Recherche hybride (cosine pgvector + BM25 tsvector + fusion RRF)
  → Agent LangGraph avec outil search_knowledge_base
  → LLM (Groq / OpenAI / Anthropic / Gemini)
  → Réponse streamée (Vercel AI SDK)
```

---

## Prérequis

- **Python 3.12**
- **Node.js 22+**
- **Docker & Docker Compose** (pour le backend en production)
- **Un projet Supabase** (gratuit) — pour l'auth, les sessions et les logs
- **Une base PostgreSQL + pgvector** — Digital Ocean, Supabase ou Docker local
- **Clé API Groq** (gratuit, suffisant pour démarrer)

---

## Installation locale — mode 100% local (sans Supabase)

> Idéal pour tester rapidement sans créer de compte externe.

```bash
git clone https://github.com/dlz-dev/helmo-oracle.git
cd helmo-oracle

# 1. Lancer la base vectorielle locale (Docker)
cd api
docker compose --profile db up -d

# 2. Configurer le backend
cp .env.example .env
# Dans api/.env : laisser SUPABASE_URL et LOG_DATABASE_URL vides
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oracle
# ENV=local

# 3. Lancer le backend
python -m venv .venv && source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
python api.py

# 4. Configurer et lancer le frontend
cd ../web
npm install
cp .env.local.example .env.local
# Dans web/.env.local : mettre NEXT_PUBLIC_LOCAL_MODE=true et BACKEND_API_URL=http://127.0.0.1:8000
npm run dev
```

En mode local :
- **Pas de compte Supabase requis**
- **Pas d'authentification** — accès direct à l'Oracle
- **Sessions** sauvegardées en fichiers JSON dans `api/storage/`
- **Logs** uniquement dans les fichiers locaux (pas de vue `/logs` dans le panel admin)
- **Panel admin** accessible directement

---

## Installation locale (développement)

### 1. Cloner le repo

```bash
git clone https://github.com/dlz-dev/helmo-oracle.git
cd helmo-oracle
```

### 2. Configurer Supabase (auth, sessions, logs)

Crée un projet sur [supabase.com](https://supabase.com), puis dans le **SQL Editor** exécute :

```sql
-- Sessions de conversation
CREATE TABLE IF NOT EXISTS chat_sessions (
  session_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title       TEXT,
  provider    TEXT,
  model       TEXT,
  messages    JSONB DEFAULT '[]',
  summary     TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Logs système
CREATE TABLE IF NOT EXISTS logs (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  level      TEXT NOT NULL,
  source     TEXT NOT NULL,
  message    TEXT,
  metadata   JSONB,
  user_id    UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Feedbacks utilisateurs
CREATE TABLE IF NOT EXISTS feedback (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id TEXT,
  user_id    UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment    TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE feedback DISABLE ROW LEVEL SECURITY;

-- Profils utilisateurs
CREATE TABLE IF NOT EXISTS profiles (
  id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  first_name TEXT,
  last_name  TEXT,
  role       TEXT DEFAULT 'etudiant'
);
```

### 3. Configurer la base vectorielle (documents)

#### Option A — Docker local (recommandé pour démarrer)

```bash
cd api
docker compose --profile db up -d
```

La base est accessible sur `localhost:5432`. Le schéma est appliqué automatiquement depuis `api/config/schema.sql`.

#### Option B — PostgreSQL externe (Digital Ocean, Supabase, etc.)

Exécute le fichier `api/config/schema.sql` sur ta base PostgreSQL.

> La base vectorielle doit avoir l'extension **pgvector** activée.

### 4. Backend (api/)

```bash
cd api
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
python -m spacy download fr_core_news_sm

cp .env.example .env          # Mac/Linux
# copy .env.example .env      # Windows
```

Remplir `api/.env` :

```env
# Base vectorielle (documents)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oracle

# Supabase (auth, sessions, logs)
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
LOG_DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres

# LLM (Groq obligatoire, les autres optionnels)
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Guardian
GUARDIAN_PROVIDER=groq
GUARDIAN_MODEL=llama-3.1-8b-instant

# Unstructured.io (PDF/DOCX avancé, optionnel)
UNSTRUCTURED_API_KEY=
UNSTRUCTURED_SERVER_URL=https://api.unstructuredapp.io/general/v0/general
```

Lancer le backend :

```bash
python api.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 5. Frontend (web/)

```bash
cd web
npm install

cp .env.local.example .env.local   # Mac/Linux
# copy .env.local.example .env.local  # Windows
```

Remplir `web/.env.local` :

```env
BACKEND_API_URL=http://localhost:8000
NEXT_PUBLIC_ADMIN_PASSWORD=oracle
NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
```

Lancer le frontend :

```bash
npm run dev
# → http://localhost:3000
```

---

## Déploiement en production

L'architecture de production utilise :
- **Digital Ocean** — serveur VPS avec Docker Compose (backend + pgvector)
- **Vercel** — frontend Next.js (déploiement automatique sur push)
- **Supabase** — auth, sessions, logs (cloud managé)
- **Nginx** — reverse proxy avec SSL (Certbot)

```bash
# Sur le serveur
cd /opt/oracle
git pull origin main
docker compose up -d --build
```

---

## Ingestion des données

1. Place tes fichiers dans `api/data/files/`
   - Formats supportés : `.csv`, `.json`, `.md`, `.txt`, `.pdf`, `.docx`
   - Les fichiers doivent commencer par `lore_` (ex: `lore_bestiaire.json`)

2. Va sur `/admin`

3. Dans la section **Ingestion**, clique **Lancer l'ingestion**

> Le Guardian valide automatiquement chaque fichier via LLM avant ingestion.
> Les fichiers rejetés sont déplacés dans `api/data/quarantine/`.
> Les doublons sont détectés automatiquement via SHA-256 (ré-ingestion sans doublon).

---

## Adapter l'Oracle à un autre domaine

Tout ce qui est spécifique à Dofus est isolé dans les fichiers de config. **Aucune modification de code nécessaire.**

| Fichier | Rôle |
|---------|------|
| `api/config/prompt.txt` | Personnalité et règles de l'Oracle |
| `api/config/prompt_guardian.txt` | Critères de validation des documents ingérés |
| `api/config/prompt_context.txt` | Description automatique des documents lors de l'ingestion |
| `api/config/prompt_summary.txt` | Résumé de conversation pour la mémoire long terme |

---

## Utilisation

| URL | Description |
|-----|-------------|
| `http://localhost:3000` | Interface de chat |
| `http://localhost:3000/sources` | Archives ingérées |
| `http://localhost:3000/admin` | Panel d'administration |
| `http://localhost:8000/docs` | API Swagger |
| `http://localhost:8000/mcp` | Serveur MCP (Claude Desktop, Cursor) |

**Panel Admin** :
- Choisir le provider LLM et le modèle
- Ajuster la température et le nombre de chunks RAG (K)
- Saisir et sauvegarder les clés API
- Tester la connexion au provider
- Lancer une ingestion
- Consulter les logs système

---

## Variables d'environnement — référence complète

### api/.env

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DATABASE_URL` | URL PostgreSQL+pgvector (documents) | — |
| `SUPABASE_URL` | URL du projet Supabase | — |
| `SUPABASE_ANON_KEY` | Clé publique Supabase | — |
| `LOG_DATABASE_URL` | URL Supabase pour logs/profils | — |
| `GROQ_API_KEY` | Clé API Groq | — |
| `OPENAI_API_KEY` | Clé API OpenAI | — |
| `ANTHROPIC_API_KEY` | Clé API Anthropic | — |
| `GOOGLE_API_KEY` | Clé API Google Gemini | — |
| `GUARDIAN_PROVIDER` | Provider du Guardian | `groq` |
| `GUARDIAN_MODEL` | Modèle du Guardian | `llama-3.1-8b-instant` |
| `UNSTRUCTURED_API_KEY` | Clé Unstructured.io (PDF/DOCX) | — |
| `K_SEMANTIC` | Candidats recherche sémantique | `10` |
| `K_BM25` | Candidats recherche BM25 | `10` |
| `K_FINAL` | Chunks retournés après fusion | `5` |
| `FTS_LANG` | Langue pour le full-text search | `french` |

### web/.env.local

| Variable | Description |
|----------|-------------|
| `BACKEND_API_URL` | URL du backend FastAPI |
| `NEXT_PUBLIC_ADMIN_PASSWORD` | Mot de passe page /admin |
| `NEXT_PUBLIC_SUPABASE_URL` | URL Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clé Supabase |

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.12, FastAPI, LangGraph |
| Embeddings | `intfloat/multilingual-e5-base` (HuggingFace, local) |
| Base vectorielle | PostgreSQL + pgvector (Digital Ocean / Docker) |
| Auth / Sessions / Logs | Supabase |
| Recherche | Cosine similarity + BM25 + RRF fusion |
| LLM | Groq / OpenAI / Anthropic / Gemini |
| Frontend | Next.js 15, Vercel AI SDK, Tailwind CSS |
| Ingestion | LlamaIndex, Unstructured.io |
| Déploiement | Docker Compose (DO) + Vercel + Nginx |
| Protocole IA | MCP (Model Context Protocol) |

---

*HeLMO Oracle — Projet académique HeLMO · 2026*
