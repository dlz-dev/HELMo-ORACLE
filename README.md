# 🔮 HELMo Oracle

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-FF6B6B?logo=langchain&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-20.10-2496ED?logo=docker&logoColor=white)
![Plotly Dash](https://img.shields.io/badge/Dash-2.18-0080FF?logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)

**HELMo Oracle** est un moteur RAG *(Retrieval-Augmented Generation)* générique développé dans le cadre d'un projet académique à **HELMo** (Haute École Libre Mosane).

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

## Fonctionnalités Clés

-   **Mode de Déploiement Flexible** :
    -   **☁️ Mode Cloud** : Utilise Supabase pour l'authentification et une base PostgreSQL distante pour une solution de production robuste.
    -   **💻 Mode Local** : Fonctionne 100% hors ligne avec une base de données vectorielle locale (ChromaDB) et un système de session basé sur des fichiers JSON. Idéal pour le développement et les tests rapides.

-   **Pipeline d'Ingestion Avancé** :
    -   Validation automatique du contenu par un LLM (**Guardian**).
    -   Détection des doublons grâce au **hachage des chunks**.
    -   Support multi-format (`.pdf`, `.docx`, `.md`, `.csv`, `.json`, `.txt`).
    -   **Late chunking contextuel** : chaque chunk est embedé avec le contexte de ses voisins grâce à `nomic-embed-text` via Ollama (8 192 tokens de contexte).
    -   [Plus de détails sur le pipeline d'ingestion](docs/FR/ingestion.md)

-   **Recherche Hybride Performante** :
    -   Combine la **recherche sémantique** (similarité vectorielle) et la **recherche par mots-clés** (BM25).
    -   Utilise **Reciprocal Rank Fusion (RRF)** pour fusionner intelligemment les résultats.
    -   [Comprendre la recherche hybride](docs/FR/hybrid_search.md)

-   **Sécurité et Confidentialité** :
    -   Anonymisation automatique des données personnelles (**PII Masking**) avant l'envoi aux LLMs.
    -   [Comment fonctionne le PII Masking ?](docs/FR/pii_masking.md)

-   **Interface Réactive** :
    -   Streaming des réponses en temps réel grâce au **Vercel AI SDK**.
    -   [L'utilité du Vercel AI SDK](docs/FR/ai_sdk.md)

-   **Supervision Humaine (Human-in-the-Loop)** :
    -   Mécanismes de validation et de correction pour améliorer continuellement la pertinence du système.
    -   [En savoir plus sur notre approche HITL](docs/FR/human_in_the_loop.md)

---

## Prérequis

-   **Python 3.12** (mode local uniquement)
-   **Node.js 22+**
-   **Docker & Docker Compose** (requis pour le backend en production)
-   **Clés API** :
    -   Au minimum, une clé **Groq** (gratuite) est nécessaire pour faire fonctionner l'agent.
    -   Pour l'ingestion de fichiers `.pdf` ou `.docx`, une clé **Unstructured.io** est fortement recommandée.

> Le modèle d'embedding (`nomic-embed-text`) est téléchargé automatiquement dans un conteneur Ollama dédié. Aucune installation manuelle de modèle n'est requise.

---

## Installation

Le projet peut être configuré de deux manières : un mode 100% local pour un démarrage rapide, ou un mode Cloud complet pour le développement et la production.

### Option 1 : Mode 100% Local (Recommandé pour commencer)

Ce mode utilise **ChromaDB** comme base vectorielle locale et ne nécessite **aucun compte externe** (pas de Supabase).

1.  **Cloner le repo**
    ```bash
    git clone https://github.com/dlz-dev/helmo-oracle.git
    cd helmo-oracle
    ```

2.  **Configurer et lancer le backend (`api/`)**
    ```bash
    cd api
    cp .env.example .env
    ```
    Modifiez `api/.env` :
    -   Assurez-vous que `DATABASE_URL`, `SUPABASE_URL` et `LOG_DATABASE_URL` sont **vides ou commentés**.
    -   Renseignez votre clé `GROQ_API_KEY`.
    -   (Optionnel) Renseignez votre clé `UNSTRUCTURED_API_KEY` pour les PDF/DOCX.

    ```bash
    python -m venv .venv
    # Sur Windows: .venv\Scripts\activate
    # Sur Mac/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    python -m spacy download fr_core_news_sm
    python api.py
    ```

3.  **Configurer et lancer le frontend (`web/`)**
    ```bash
    cd ../web
    npm install
    cp .env.local.example .env.local
    ```
    Modifiez `web/.env.local` :
    -   `NEXT_PUBLIC_LOCAL_MODE=true`
    -   `BACKEND_API_URL=http://127.0.0.1:8000`

    ```bash
    npm run dev
    ```

Votre Oracle est maintenant accessible sur `http://localhost:3000`.

### Option 2 : Mode Cloud avec Docker (recommandé pour la production)

Ce mode utilise **Docker Compose** pour orchestrer le backend et le service d'embedding, avec Supabase pour la base vectorielle, l'authentification et les logs.

#### 1. Configurer Supabase

-   Créez un projet sur [supabase.com](https://supabase.com).
-   Activez l'extension `vector` : **Settings > Database > Extensions > vector**.
-   Exécutez `api/config/schema_supabase.sql` dans l'éditeur SQL de Supabase.

> **Si la colonne `vecteur` existait déjà avec une autre dimension**, exécutez d'abord ce script de migration avant de lancer l'ingestion :
> ```sql
> DROP INDEX IF EXISTS idx_documents_cosine;
> TRUNCATE TABLE public.documents;
> ALTER TABLE public.documents ALTER COLUMN vecteur TYPE vector(768);
> CREATE INDEX idx_documents_cosine
>   ON public.documents USING ivfflat (vecteur vector_cosine_ops) WITH (lists = 100);
> ```

#### 2. Configurer les variables d'environnement

```bash
cd api
cp .env.example .env
```

Dans `api/.env`, renseignez :
-   `DATABASE_URL` — URL PostgreSQL de Supabase (onglet **Settings > Database**).
-   `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `LOG_DATABASE_URL`.
-   `GROQ_API_KEY` (et autres clés LLM selon vos besoins).
-   `API_SECRET_KEY` — clé secrète pour protéger les routes d'administration.

#### 3. Construire et démarrer les conteneurs

```bash
cd api
docker compose up --build -d
```

Cela démarre deux conteneurs :
-   `backend` — l'API FastAPI sur le port `8000`.
-   `embedding_service` — Ollama sur le port `11434`, avec persistance dans `./ollama_data/`.

#### 4. Télécharger le modèle d'embedding (première fois uniquement)

```bash
docker exec embedding_service ollama pull nomic-embed-text
```

Le modèle est persisté dans le volume `./ollama_data/` — cette commande n'est à exécuter qu'**une seule fois**.

#### 5. Vérifier que tout fonctionne

```bash
# Santé globale de l'API
curl http://localhost:8000/health

# Test du service Ollama
curl http://localhost:11434/api/tags
```

#### 6. Configurer et lancer le frontend

```bash
cd ../web
npm install
cp .env.local.example .env.local
```

Dans `web/.env.local` :
-   `NEXT_PUBLIC_LOCAL_MODE=false`
-   `BACKEND_API_URL=http://localhost:8000`
-   `NEXT_PUBLIC_SUPABASE_URL` et `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

```bash
npm run dev
```

---

### Commandes Docker utiles

| Commande | Description |
|----------|-------------|
| `docker compose up --build -d` | Build et démarrage complet |
| `docker compose up -d` | Démarrage sans rebuild |
| `docker compose down` | Arrêt des conteneurs |
| `docker compose logs backend -f` | Logs du backend en temps réel |
| `docker exec embedding_service ollama pull nomic-embed-text` | (Re)télécharger le modèle |
| `docker exec embedding_service ollama list` | Lister les modèles installés |

---

## Adapter l'Oracle à votre domaine

Pour faire de l'Oracle un expert sur un autre sujet, **aucune modification de code n'est nécessaire**. Il suffit d'adapter les prompts.

1.  **Placez vos documents** dans le dossier `api/data/files/`.
2.  **Modifiez les prompts** dans le dossier `api/config/` :
    -   `prompt.txt`: Définit la **personnalité** et les règles de base de l'agent. C'est le fichier le plus important à adapter.
    -   `prompt_guardian.txt`: Décrit les **critères de pertinence** pour accepter ou rejeter un document lors de l'ingestion.
    -   `prompt_context.txt`: Guide le LLM pour générer une **description globale** de chaque document.
    -   `prompt_summary.txt`: Instruction pour résumer les conversations et maintenir une mémoire à long terme.
3.  **Lancez une ingestion** depuis le panel d'administration (`/admin`).

---

## Panel d'Administration (`/admin`)

Le panel admin est le centre de contrôle de l'Oracle.

-   **Gestion des Modèles** : Choisissez le fournisseur (Groq, OpenAI, etc.) et le modèle à utiliser.
-   **Configuration des Clés API** : Saisissez et testez vos clés API.
-   **Ingestion de Données** : Lancez et suivez le processus d'ingestion de nouveaux documents.
-   **Logs Système** : Consultez les logs en temps réel (disponible uniquement en mode Cloud).

---

*HELMo Oracle — Projet académique HELMo · 2026*
