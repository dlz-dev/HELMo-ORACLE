# 🔮 HeLMO Oracle

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-FF6B6B?logo=langchain&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)


**HeLMO Oracle** est un chatbot RAG *(Retrieval-Augmented Generation)* développé dans le cadre d'un projet académique à **HeLMO** (Haute École Libre Mosane).

Dans sa version actuelle, l'Oracle est spécialisé sur l'univers du jeu **Dofus** (MMORPG d'Ankama) — les données ont été choisies par l'équipe faute de corpus fourni. L'architecture est conçue pour être générique : n'importe quel corpus de données peut être ingéré pour créer un Oracle sur mesure.

**Équipe** : Tim · Maxime · Arnaud

---

## Architecture

```
HeLMO-Oracle/
├── api/          ← Backend Python (FastAPI)
│   ├── core/     ← RAG pipeline, mémoire, sessions, PII
│   ├── converters/   ← Parseurs CSV, JSON, MD, TXT, PDF, Unstructured
│   ├── providers/    ← Groq, OpenAI, Anthropic, Gemini
│   ├── config/       ← Prompts système (prompt.txt, prompt_guardian.txt, …)
│   └── data/         ← Fichiers lore à ingérer
└── web/          ← Frontend Next.js (Vercel AI SDK)
    ├── app/      ← Pages : Oracle, Sources, Admin
    └── components/   ← Chat, Sessions, Admin panel
```

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
- **Compte Supabase** (base PostgreSQL + extension pgvector) — ou Docker (voir ci-dessous)
- **Clé API Groq** (gratuit, suffisant pour démarrer)

---

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/ton-org/helmo-oracle.git
cd helmo-oracle
```

### 2. Configurer la base de données

#### Option A — Supabase (recommandé pour le cloud)

Dans le **SQL Editor** de ton projet Supabase, exécute ce script une seule fois :

```sql
-- Extension vectorielle
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents (base de connaissances RAG)
CREATE TABLE IF NOT EXISTS documents (
  id          SERIAL PRIMARY KEY,
  content     TEXT,
  vecteur     VECTOR(768),
  metadata    JSONB,
  ingested_at TIMESTAMPTZ DEFAULT now(),
  fts_vector  TSVECTOR
);

CREATE INDEX IF NOT EXISTS idx_documents_cosine
  ON documents USING ivfflat (vecteur vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_documents_fts
  ON documents USING gin(fts_vector);

CREATE OR REPLACE FUNCTION update_fts_vector() RETURNS TRIGGER AS $$
BEGIN
  new.fts_vector := to_tsvector('french', new.content);
  RETURN new;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trig_update_fts
  BEFORE INSERT OR UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_fts_vector();

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

-- Profils utilisateurs (complète auth.users)
CREATE TABLE IF NOT EXISTS profiles (
  id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  first_name TEXT,
  last_name  TEXT
);
```

#### Option B — Docker (local, 100% autonome)

Le service base de données est intégré dans `api/docker-compose.yml` sous un **profile optionnel** — il ne démarre que si on l'active explicitement.

```bash
# Démarrer backend + base de données locale
docker compose --profile db up -d
```

Puis adapter `api/.env` :
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oracle
SUPABASE_URL=        # laisser vide
SUPABASE_ANON_KEY=   # laisser vide
```

> Les fonctionnalités d'authentification (sessions par utilisateur) nécessitent Supabase Auth. En mode Docker, toutes les conversations sont anonymes.

---

### 3. Backend (api/)

```bash
cd api

# Créer et activer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# Installer les dépendances
pip install -r requirements.txt

# Télécharger le modèle spaCy (pour le PII masking)
python -m spacy download fr_core_news_sm
```

Créer le fichier `.env` :

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # Mac/Linux
```

Remplir `.env` avec tes valeurs :

```env
# Base de données
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>

# LLM (Groq obligatoire, les autres optionnels)
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Guardian (validation des fichiers à l'ingestion)
GUARDIAN_PROVIDER=groq
GUARDIAN_MODEL=llama-3.1-8b-instant

# Unstructured.io (pour PDF et DOCX)
UNSTRUCTURED_API_KEY=
UNSTRUCTURED_SERVER_URL=https://api.unstructuredapp.io/general/v0/general
```

Créer les prompts système :

```bash
# Windows
copy config\prompt.example.txt config\prompt.txt

# Mac/Linux
cp config/prompt.example.txt config/prompt.txt
```

> Les prompts `prompt_context.txt`, `prompt_guardian.txt` et `prompt_summary.txt` sont déjà présents dans `config/`. Modifie-les pour adapter l'Oracle à un autre domaine.

Lancer le backend :

```bash
python api.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 4. Frontend (web/)

```bash
cd web

npm install

copy env.local.example .env.local    # Windows
# cp env.local.example .env.local    # Mac/Linux
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

## Ingestion des données

1. Place tes fichiers dans `api/data/files/`
   - Formats supportés : `.csv`, `.json`, `.md`, `.txt`, `.pdf`, `.docx`
   - Les fichiers doivent commencer par `lore_` (ex: `lore_bestiaire.json`)

2. Va sur `http://localhost:3000/admin`

3. Connecte-toi avec le mot de passe admin (`oracle` par défaut)

4. Dans la section **Ingestion**, clique **Lancer l'ingestion**

> Le Guardian valide automatiquement chaque fichier via LLM avant ingestion.
> Les fichiers rejetés sont déplacés dans `api/data/quarantine/`.

---

## Utilisation

| URL | Description |
|-----|-------------|
| `http://localhost:3000` | Interface de chat |
| `http://localhost:3000/sources` | Archives ingérées |
| `http://localhost:3000/admin` | Panel d'administration |
| `http://localhost:8000/docs` | API Swagger |

**Panel Admin** — permet de :
- Choisir le provider LLM et le modèle
- Ajuster la température et le nombre de chunks RAG (K)
- Saisir et sauvegarder les clés API
- Tester la connexion au provider
- Lancer une ingestion
- Consulter les logs système (paginés, 15 par page)

**Feedback utilisateur** — En bas de la barre latérale, les utilisateurs peuvent noter chaque conversation de 1 à 5 étoiles et laisser un commentaire. Les feedbacks sont visibles dans les logs (`source = FEEDBACK`) et dans la table `feedback` Supabase.

---

## Adapter l'Oracle à un autre domaine

Tout ce qui est spécifique à Dofus est isolé dans les fichiers de config :

| Fichier | Rôle |
|---------|------|
| `api/config/prompt.txt` | Personnalité et règles de l'Oracle |
| `api/config/prompt_guardian.txt` | Critères de validation des documents ingérés |
| `api/config/prompt_context.txt` | Description automatique des documents lors de l'ingestion |
| `api/config/prompt_summary.txt` | Résumé de conversation pour la mémoire long terme |

Aucune modification de code nécessaire — seuls ces fichiers texte sont à adapter.

---

## Variables d'environnement — référence complète

### api/.env

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DATABASE_URL` | URL de connexion PostgreSQL (pgvector) | — |
| `SUPABASE_URL` | URL du projet Supabase | — |
| `SUPABASE_ANON_KEY` | Clé publique Supabase | — |
| `LOG_DATABASE_URL` | URL Supabase pour logs/profils (optionnel, = DATABASE_URL si absent) | — |
| `GROQ_API_KEY` | Clé API Groq | — |
| `OPENAI_API_KEY` | Clé API OpenAI | — |
| `ANTHROPIC_API_KEY` | Clé API Anthropic | — |
| `GOOGLE_API_KEY` | Clé API Google Gemini | — |
| `GUARDIAN_PROVIDER` | Provider du Guardian | `groq` |
| `GUARDIAN_MODEL` | Modèle du Guardian | `llama-3.1-8b-instant` |
| `UNSTRUCTURED_API_KEY` | Clé Unstructured.io (PDF/DOCX) | — |
| `CONTEXT_PROMPT` | Prompt contexte (si pas de fichier .txt) | — |
| `GUARDIAN_PROMPT` | Prompt guardian (si pas de fichier .txt) | — |
| `SUMMARY_PROMPT` | Prompt résumé (si pas de fichier .txt) | — |
| `K_SEMANTIC` | Candidats recherche sémantique | `10` |
| `K_BM25` | Candidats recherche BM25 | `10` |
| `K_FINAL` | Chunks retournés après fusion | `5` |
| `FTS_LANG` | Langue pour le full-text search | `french` |

### web/.env.local

| Variable | Description |
|----------|-------------|
| `BACKEND_API_URL` | URL du backend FastAPI |
| `NEXT_PUBLIC_ADMIN_PASSWORD` | Mot de passe page /admin |
| `NEXT_PUBLIC_SUPABASE_URL` | URL Supabase (pour sessions) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clé Supabase (pour sessions) |

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.12, FastAPI, LangGraph |
| Embeddings | `intfloat/multilingual-e5-base` (HuggingFace, local) |
| Base vectorielle | Supabase / Docker + pgvector |
| Recherche | Cosine similarity + BM25 + RRF fusion |
| LLM | Groq / OpenAI / Anthropic / Gemini |
| Frontend | Next.js 15, Vercel AI SDK, Tailwind CSS |
| Ingestion | LlamaIndex, Unstructured.io |

---

*HeLMO Oracle — Projet académique HeLMO · 2025*