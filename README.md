# 🔮 HELMo Oracle

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-FF6B6B?logo=langchain&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-20.10-2496ED?logo=docker&logoColor=white)
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
    -   [Plus de détails sur le pipeline d'ingestion](./docs/ingestion.md)

-   **Recherche Hybride Performante** :
    -   Combine la **recherche sémantique** (similarité vectorielle) et la **recherche par mots-clés** (BM25).
    -   Utilise **Reciprocal Rank Fusion (RRF)** pour fusionner intelligemment les résultats.
    -   [Comprendre la recherche hybride](./docs/hybrid_search.md)

-   **Sécurité et Confidentialité** :
    -   Anonymisation automatique des données personnelles (**PII Masking**) avant l'envoi aux LLMs.
    -   [Comment fonctionne le PII Masking ?](./docs/pii_masking.md)

-   **Interface Réactive** :
    -   Streaming des réponses en temps réel grâce au **Vercel AI SDK**.
    -   [L'utilité du Vercel AI SDK](./docs/ai_sdk.md)

-   **Supervision Humaine (Human-in-the-Loop)** :
    -   Mécanismes de validation et de correction pour améliorer continuellement la pertinence du système.
    -   [En savoir plus sur notre approche HITL](./docs/human_in_the_loop.md)

---

## Prérequis

-   **Python 3.12**
-   **Node.js 22+**
-   **Docker & Docker Compose**
-   **Clés API** :
    -   Au minimum, une clé **Groq** (gratuite) est nécessaire pour faire fonctionner l'agent.
    -   Pour l'ingestion de fichiers `.pdf` ou `.docx`, une clé **Unstructured.io** est fortement recommandée.

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

### Option 2 : Mode Cloud (avec Supabase et PostgreSQL)

Ce mode utilise une base de données PostgreSQL (locale ou distante) pour les vecteurs et Supabase pour l'authentification, les sessions et les logs.

1.  **Configurer la base vectorielle (PostgreSQL + pgvector)**
    -   **Option A (Docker local)** : `cd api && docker compose --profile db up -d`
    -   **Option B (Base distante)** : Assurez-vous que l'extension `pgvector` est activée et exécutez le script `api/config/schema.sql`.

2.  **Configurer Supabase**
    -   Créez un projet sur [supabase.com](https://supabase.com).
    -   Exécutez le contenu du fichier `api/config/supabase_schema.sql` dans l'éditeur SQL de Supabase pour créer les tables `chat_sessions`, `logs`, etc.

3.  **Configurer le backend (`api/.env`)**
    -   Remplissez `DATABASE_URL` avec l'URL de votre base PostgreSQL.
    -   Remplissez `SUPABASE_URL`, `SUPABASE_ANON_KEY`, et `LOG_DATABASE_URL` avec les informations de votre projet Supabase.
    -   Renseignez les clés API (`GROQ_API_KEY`, etc.).

4.  **Configurer le frontend (`web/.env.local`)**
    -   `NEXT_PUBLIC_LOCAL_MODE=false`
    -   Remplissez `NEXT_PUBLIC_SUPABASE_URL` et `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

5.  **Lancez les applications** comme décrit dans le mode local.

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