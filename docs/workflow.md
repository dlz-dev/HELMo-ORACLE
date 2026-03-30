# 🔮 HELMo Oracle — Workflow Diagrams

## 1. Architecture globale

```mermaid
flowchart LR
    subgraph WEB ["🌐 web/ — Next.js 15"]
        direction TB
        UI["Chat · Sources · Admin"]
        ROUTES["API Routes\n/api/chat\n/api/sessions\n/api/sources\n/api/admin/*"]
        UI --> ROUTES
    end

    subgraph API ["⚙️ api/ — FastAPI"]
        direction TB
        FASTAPI["api.py\nFastAPI + Uvicorn"]
        CORE["core/\nagent · context · database · pipeline"]
        PROV["providers/\nGroq · OpenAI · Anthropic · Gemini · Ollama"]
        FASTAPI --> CORE
        FASTAPI --> PROV
    end

    ROUTES -->|"HTTP + SSE"| FASTAPI

    subgraph DEPLOIEMENT ["🚀 Déploiement"]
        direction LR
        subgraph CLOUD ["☁️ Cloud Mode"]
            DB_CLOUD[("Supabase\npgvector")]
        end
        subgraph LOCAL ["💻 Local Mode"]
            DB_LOCAL[("ChromaDB\n(local)")]
        end
    end

    subgraph INFRA ["⚙️ Services Communs"]
        direction TB
        EMBED["HuggingFace\nmultilingual-e5-base\n(local)"]
        UNSTRUCT["Unstructured.io\n(PDF · DOCX)"]
    end

    CORE <-->|"SQL"| DB_CLOUD
    CORE <-->|"SDK"| DB_LOCAL
    CORE <-->|"embeddings"| EMBED
    CORE -->|"parsing"| UNSTRUCT

    style WEB     fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style API     fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style DEPLOIEMENT fill:#0f172a,stroke:#334155,color:#94a3b8
    style CLOUD fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style LOCAL fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style INFRA   fill:#0f172a,stroke:#334155,color:#94a3b8
```

---

## 2. Pipeline d'ingestion

```mermaid
flowchart TD
    INPUT([📁 data/files/\nlore_*.csv · .json · .txt\n.pdf · .docx · .md]) --> GUARD

    subgraph GUARD ["🛡️ Guardian — validation LLM"]
        G1{"Contenu Dofus/MMORPG ?"}
        G1 -->|"❌ Non"| G2(["🗑️ data/quarantine/"])
        G1 -->|"✅ Oui"| G3["Accepté"]
    end

    G3 --> CTX

    subgraph CTX ["🧠 Contextualisation"]
        C1["LLM génère une description\nglobale du fichier (3000 chars)"]
        C2["Préfixée à chaque chunk\n→ meilleure précision RAG"]
        C1 --> C2
    end

    CTX --> ROUTE

    subgraph ROUTE ["🔀 Routage par format"]
        direction LR
        R1["convert_csv · convert_json\nconvert_text · convert_markdown · convert_pdf"]
        R2["Unstructured.io\nHI_RES (pdf/docx) · FAST (autres)"]
    end

    ROUTE --> HASH

    subgraph HASH ["#️⃣ Hash Chunks"]
        H1["SHA256(chunk_content)\n→ chunk_hash"]
    end

    HASH --> EMBED

    subgraph EMBED ["⚡ Embeddings — local"]
        E1["intfloat/multilingual-e5-base\n768 dimensions · HuggingFace"]
        E2["get_text_embedding(chunk)"]
        E1 --> E2
    end

    EMBED --> DB

    subgraph DB ["🗄️ Vector Store"]
        direction LR
        subgraph DB_CLOUD ["☁️ Supabase pgvector"]
            D1["INSERT documents\n(content, vecteur, metadata, chunk_hash)"]
            D2["Trigger auto → fts_vector\nindex IVFFlat cosine + GIN FTS"]
            D1 --> D2
        end
        subgraph DB_LOCAL ["💻 ChromaDB"]
            D3["upsert documents\n(content, vecteur, metadata, chunk_hash)"]
        end
    end

    subgraph LOG ["📋 Logs — oracle.log"]
        L1["Fichier accepté/rejeté · chunks insérés/skippés"]
    end

    DB --> LOG

    style GUARD  fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style CTX    fill:#1e1e2e,stroke:#8b5cf6,color:#e2e8f0
    style ROUTE  fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style HASH   fill:#1e1e2e,stroke:#ec4899,color:#e2e8f0
    style EMBED  fill:#1e1e2e,stroke:#f87171,color:#e2e8f0
    style DB     fill:#0f172a,stroke:#334155,color:#94a3b8
    style DB_CLOUD fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style DB_LOCAL fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style LOG    fill:#1e1e2e,stroke:#475569,color:#94a3b8
    style INPUT  fill:#312e81,stroke:#818cf8,color:#e2e8f0
    style G2     fill:#3b0f0f,stroke:#dc2626,color:#e2e8f0
```

---

## 3. Flux de conversation (Runtime)

```mermaid
flowchart TD
    U([👤 Utilisateur]) -->|"💬 Question"| FRONTEND

    subgraph FRONTEND ["🌐 Next.js — useChat()"]
        direction TB
        SDK["Vercel AI SDK\nuseChat() — streaming natif"]
        PROXY["POST /api/chat\n→ proxy vers FastAPI"]
        SDK --> PROXY
    end

    PROXY -->|"POST /api/chat\n{messages, session_id, provider, model}"| FASTAPI

    subgraph FASTAPI ["⚙️ FastAPI — _generate_stream()"]
        direction TB
        PII["🔒 PII Manager\nmask_text() — spaCy + Regex"]
        SESSION["SessionManager\nload/create session\nJSON local"]
        MEMORY["MemoryManager\nbuild_agent_input()\nrésumé si overflow"]
        PII --> SESSION --> MEMORY
    end

    MEMORY -->|"historique LangChain messages"| AGENT

    subgraph AGENT ["🤖 LangGraph — create_react_agent"]
        A1["system prompt enrichi\n+ archives disponibles"]
        A2["ReAct loop\nObserve → Think → Act"]
        A1 --> A2
    end

    A2 -->|"tool_call: search_knowledge_base"| TOOL

    subgraph TOOL ["🔧 tools_oracle.py"]
        T1["get_query_embedding(query)"]
        T2["search()"]
        T3["<archives_sacrees>...</archives_sacrees>"]
        T1 --> T2 --> T3
    end

    subgraph DBS ["🗄️ Vector Stores"]
        DB_CLOUD[("☁️ Supabase pgvector")]
        DB_LOCAL[("💻 ChromaDB")]
    end

    subgraph VM ["📊 VectorManager — recherche"]
        subgraph VM_CLOUD ["☁️ Hybride (Supabase)"]
            direction LR
            S1["🔵 Cosine"]
            S2["🟠 BM25"]
            RRF["⚖️ RRF Fusion"]
            S1 --> RRF
            S2 --> RRF
        end
        subgraph VM_LOCAL ["💻 Sémantique (ChromaDB)"]
            S3["🔵 Cosine"]
        end
    end

    T2 <--> VM
    VM_CLOUD <--> DB_CLOUD
    VM_LOCAL <--> DB_LOCAL

    T3 -->|"contexte RAG"| A2
    A2 -->|"réponse finale"| STREAM

    subgraph STREAM ["📡 Streaming SSE"]
        ST1["Vercel AI data stream protocol\n0:token · 3:error · d:finish"]
    end

    STREAM -->|"tokens en temps réel"| U

    subgraph PROV ["🌐 Providers LLM"]
        direction LR
        P1["⚡ Groq"] --- P2["🤖 OpenAI"] --- P3["🧠 Anthropic"] --- P4["✨ Gemini"] --- P5["🏠 Ollama"]
    end

    AGENT <-->|"API call"| PROV

    subgraph LOG ["📋 Logs"]
        LG["provider · model · session · sources · tokens"]
    end

    STREAM --> LOG

    style FRONTEND fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style FASTAPI  fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style AGENT    fill:#1e1e2e,stroke:#a78bfa,color:#e2e8f0
    style TOOL     fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style DBS      fill:#0f172a,stroke:#334155,color:#94a3b8
    style VM       fill:#0f172a,stroke:#334155,color:#94a3b8
    style VM_CLOUD fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style VM_LOCAL fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style STREAM   fill:#1e1e2e,stroke:#38bdf8,color:#e2e8f0
    style PROV     fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style LOG      fill:#1e1e2e,stroke:#475569,color:#94a3b8
    style U        fill:#312e81,stroke:#818cf8,color:#e2e8f0
```

---

## 4. Architecture des modules

```mermaid
graph LR
    subgraph ENTRY ["Points d'entrée"]
        APIP["api.py\nFastAPI"]
        WATCH["watcher.py\nWatchdog"]
    end

    subgraph CORE ["core/"]
        subgraph AGENT ["agent/"]
            TO["tools_oracle.py"]
            GU["guardian.py"]
        end
        subgraph CONTEXT ["context/"]
            SM["session_manager.py"]
            ME["memory_manager.py"]
        end
        subgraph DATABASE ["database/"]
            VM["vector_manager.py"]
        end
        subgraph PIPELINE ["pipeline/"]
            IN["ingestion.py"]
            PI["pii_manager.py"]
            PR["preprocess.py"]
        end
    end

    subgraph CONV ["converters/"]
        CV["csv · md · txt · json\npdf · unstructured"]
    end

    subgraph PROV ["providers/"]
        PV["groq · openai\nanthropic · gemini · ollama"]
    end

    subgraph CONF ["config/"]
        PT["prompt.txt"]
        ENV[".env"]
    end

    APIP -->|"chat stream"| TO
    APIP -->|"PII mask"| PI
    APIP --> SM
    APIP --> ME
    APIP --> VM
    APIP --> PV
    APIP -->|"ingest trigger"| IN
    TO --> VM
    TO --> GU
    IN --> GU
    IN --> VM
    IN --> PI
    IN --> CV
    WATCH --> IN
    GU --> PV
    ME --> SM
    APIP -.-> PT
    APIP -.-> ENV

    style ENTRY    fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style CORE     fill:#0f172a,stroke:#334155,color:#94a3b8
    style AGENT    fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style CONTEXT  fill:#1e1e2e,stroke:#0891b2,color:#e2e8f0
    style DATABASE fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style PIPELINE fill:#1e1e2e,stroke:#dc2626,color:#e2e8f0
    style CONV     fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style PROV     fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style CONF     fill:#1e1e2e,stroke:#475569,color:#e2e8f0
```

---

## 5. Panel Admin

```mermaid
flowchart LR
    subgraph ADMIN ["🔐 /admin — AdminPanel"]
        direction TB
        AUTH["Authentification\n(local mode: bypass)"]
        MODE[" sélecteur Cloud/Local\n(Navbar)"]
        MODEL["Modèle IA\nprovider · model · temp · K\n→ localStorage"]
        KEYS["Clés API\n→ localStorage"]
        TEST["Test Provider\nPOST /api/admin/test"]
        LOGS["Logs système\nGET /api/admin/logs\nauto-refresh 3s"]
        HEALTH["Health Check\nGET /api/admin/health"]
        INGEST["Ingestion\nPOST /api/admin/ingest\nPOLL /api/admin/ingest/status"]
    end

    subgraph BACKEND ["⚙️ FastAPI"]
        T["/test"]
        L["/logs"]
        H["/health/full"]
        I["/ingest"]
        IS["/ingest/status"]
    end

    AUTH --> MODE
    MODE --> MODEL
    MODEL --> KEYS
    KEYS --> TEST
    TEST --> T
    LOGS --> L
    HEALTH --> H
    INGEST --> I
    INGEST --> IS

    style ADMIN   fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style BACKEND fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style AUTH    fill:#312e81,stroke:#818cf8,color:#e2e8f0
```