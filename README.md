# 🔮 HeLMO Oracle

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-FF6B6B?logo=langchain&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)


**HeLMO Oracle** est un chatbot RAG *(Retrieval-Augmented Generation)* développé dans le cadre d'un projet académique à **HeLMO** (Haute École Libre Mosane).

Dans sa version actuelle, l'Oracle est spécialisé sur l'univers du jeu **Dofus** (MMORPG d'Ankama) — les données ont été choisies par l'équipe faute de corpus fourni. L'architecture est conçue pour être générique : n'importe quel corpus de données peut être ingéré pour créer un Oracle sur mesure.

**Équipe** : Tim · Maxime · Arnau

---

## Architecture

```
HeLMO-Oracle/
├── api/          ← Backend Python (FastAPI)
│   ├── core/     ← RAG pipeline, mémoire, sessions, PII
│   ├── converters/   ← Parseurs CSV, JSON, MD, TXT, PDF, Unstructured
│   ├── providers/    ← Groq, OpenAI, Anthropic, Gemini, Ollama
│   ├── config/       ← prompt.txt (personnalité de l'Oracle)
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
  → LLM (Groq / OpenAI / Anthropic / Gemini / Ollama)
  → Réponse streamée (Vercel AI SDK)
```

---

## Prérequis

- **Python 3.12**
- **Node.js 22+**
- **Compte Supabase** (base PostgreSQL + extension pgvector)
- **Clé API Groq** (gratuit, suffisant pour démarrer)

---

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/ton-org/helmo-oracle.git
cd helmo-oracle
```

### 2. Configurer Supabase

Dans le **SQL Editor** de ton projet Supabase, exécute ce script une seule fois :

```sql
-- Extension vectorielle
create extension if not exists vector;

-- Table des documents
create table if not exists documents (
  id          serial primary key,
  content     text,
  vecteur     vector(768),
  metadata    jsonb,
  ingested_at timestamptz default now(),
  fts_vector  tsvector
);

-- Index vectoriel cosine (créer après avoir ingéré des données)
create index if not exists idx_documents_cosine
  on documents using ivfflat (vecteur vector_cosine_ops) with (lists = 100);

-- Index full-text search
create index if not exists idx_documents_fts
  on documents using gin(fts_vector);

-- Trigger auto mise à jour fts_vector
create or replace function update_fts_vector() returns trigger as $$
begin
  new.fts_vector := to_tsvector('french', new.content);
  return new;
end;
$$ language plpgsql;

create or replace trigger trig_update_fts
  before insert or update on documents
  for each row execute function update_fts_vector();
```

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

Créer le prompt système :

```bash
copy config\prompt.example.txt config\prompt.txt    # Windows
# cp config/prompt.example.txt config/prompt.txt    # Mac/Linux
```

Lancer le backend :

```bash
python api.py
# python -m uvicorn api:app --reload --port 8000 → même chose mais avec rechargement auto
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 4. Frontend (web/)

```bash
cd web

# Installer les dépendances
npm install

# Créer le fichier d'environnement
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

4. Dans la section **Ingestion**, entre le chemin absolu vers `api/data/files/` et clique **Lancer l'ingestion**

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

---

## Variables d'environnement — référence complète

### api/.env

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DATABASE_URL` | URL de connexion PostgreSQL | — |
| `SUPABASE_URL` | URL du projet Supabase | — |
| `SUPABASE_ANON_KEY` | Clé publique Supabase | — |
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
| `NEXT_PUBLIC_SUPABASE_URL` | URL Supabase (pour sessions) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clé Supabase (pour sessions) |

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.12, FastAPI, LangGraph |
| Embeddings | `intfloat/multilingual-e5-base` (HuggingFace, local) |
| Base vectorielle | Supabase + pgvector |
| Recherche | Cosine similarity + BM25 + RRF fusion |
| LLM | Groq / OpenAI / Anthropic / Gemini / Ollama |
| Frontend | Next.js 15, Vercel AI SDK, Tailwind CSS |
| Ingestion | LlamaIndex, Unstructured.io |

---

*HeLMO Oracle — Projet académique HeLMO · 2025*