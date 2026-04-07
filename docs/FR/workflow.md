# 🔮 HELMo Oracle — Workflow Diagrams

## 1. Architecture globale

```mermaid
flowchart LR
    subgraph WEB ["🌐 web/ — Next.js 15 (Vercel)"]
        direction TB
        UI["Chat · Sources · Admin"]
        ROUTES["API Routes\n/api/chat\n/api/sessions\n/api/sources\n/api/admin/*\n/api/feedback"]
        UI --> ROUTES
    end

    subgraph BOT ["🤖 bot/ — Nuxt 4 (Vercel)"]
        direction TB
        DISCORD["Discord Adapter\n(@chat-adapter/discord)"]
        WHATSAPP["WhatsApp / Teams\n(adaptateurs disponibles)"]
    end

    subgraph API ["⚙️ api/ — FastAPI (Digital Ocean)"]
        direction TB
        FASTAPI["api.py\nFastAPI + Uvicorn"]
        MCP_SRV["mcp_server.py\nMCP /mcp\nsearch_knowledge_base · list_sources"]
        CORE["core/\nagent · context · database · pipeline"]
        PROV["providers/\nGroq · OpenAI · Anthropic · Gemini · Ollama"]
        JUDGE["core/agent/judge.py\nLLM Judge asynchrone"]
        FASTAPI --> CORE
        FASTAPI --> PROV
        FASTAPI --> MCP_SRV
        FASTAPI -.->|"async background"| JUDGE
    end

    ROUTES -->|"HTTP + SSE\n(Vercel AI Data Stream)"| FASTAPI
    BOT -->|"MCP SSE\nhttps://api.dlzteam.com/mcp"| MCP_SRV

    subgraph DB ["🗄️ Base de données"]
        direction TB
        DB_PG[("Digital Ocean\nPostgres + pgvector")]
        DB_SUP[("Supabase\nlogs · profiles · feedback")]
    end

    subgraph INFRA ["⚙️ Services Communs"]
        direction TB
        EMBED["Ollama\nnomic-embed-text\n768 dim — Late Chunking"]
        UNSTRUCT["Unstructured.io\n(PDF · DOCX)"]
    end

    CORE <-->|"SQL + pgvector"| DB_PG
    CORE <-->|"psycopg logs"| DB_SUP
    CORE <-->|"embeddings"| EMBED
    CORE -->|"parsing"| UNSTRUCT

    style WEB     fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style BOT     fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style API     fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style DB      fill:#0f172a,stroke:#334155,color:#94a3b8
    style DB_PG   fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style DB_SUP  fill:#1e1e2e,stroke:#38bdf8,color:#e2e8f0
    style INFRA   fill:#0f172a,stroke:#334155,color:#94a3b8
```

---

## 2. Pipeline d'ingestion

> Déclenché via `POST /ingest` (Admin UI) ou `watcher.py` (Watchdog automatique sur `data/new_files/`).

```mermaid
flowchart TD
    INPUT(["data/new_files/\nlore_*.csv .json .txt\n.pdf .docx .md"]) --> GUARD

    subgraph GUARD ["Guardian — validation LLM"]
        G1{"Contenu Dofus/MMORPG ?"}
        G1 -->|"Non"| G2(["data/quarantine/"])
        G1 -->|"Oui"| G3["Accepté"]
    end

    G3 --> CTX

    subgraph CTX ["Contextualisation (ingestion.py)"]
        C1["LLM génère une description\nglobale du fichier (3000 chars max)"]
        C2["global_context stocké\nen metadata de chaque chunk"]
        C1 --> C2
    end

    CTX --> ROUTE

    subgraph ROUTE ["Routage par format"]
        direction LR
        R1["convert_csv · convert_json\nconvert_text · convert_markdown · convert_pdf"]
        R2["Unstructured.io\nHI_RES pdf/docx · FAST autres"]
    end

    ROUTE --> HASH

    subgraph HASH ["Déduplication SHA256"]
        H1["SHA256 du contenu brut\n→ chunk_hash"]
        H2{"chunk_hash déjà\ndans la DB ?"}
        H1 --> H2
        H2 -->|"Oui"| SKIP(["Skip — doublon ignoré"])
        H2 -->|"Non"| LC
    end

    subgraph LC ["Late Chunking (late_chunking.py)"]
        L1["Pour chunk i :\nContexte = chunks[i-3 .. i-1]"]
        L2["Texte enrichi :\nContext: ... Chunk: ..."]
        L3["embed_documents(contextual_texts)\nnomic-embed-text — 768 dim"]
        L1 --> L2 --> L3
    end

    LC --> DB

    subgraph DB ["Vector Store — Digital Ocean pgvector"]
        D1["INSERT documents\n(content, vector, metadata, chunk_hash)"]
        D2["Trigger auto → fts_vector\nIVFFlat cosine + GIN FTS (BM25)"]
        D1 --> D2
    end

    DB --> ARCHIVE(["data/files/\n(archive après ingestion)"])
    DB --> LOG

    subgraph LOG ["Logs — Supabase + oracle.log"]
        LG["source · chunks insérés · doublons · durée"]
    end

    style GUARD  fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style CTX    fill:#1e1e2e,stroke:#8b5cf6,color:#e2e8f0
    style ROUTE  fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style HASH   fill:#1e1e2e,stroke:#ec4899,color:#e2e8f0
    style LC     fill:#1e1e2e,stroke:#f87171,color:#e2e8f0
    style DB     fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style LOG    fill:#1e1e2e,stroke:#475569,color:#94a3b8
    style INPUT  fill:#312e81,stroke:#818cf8,color:#e2e8f0
    style G2     fill:#3b0f0f,stroke:#dc2626,color:#e2e8f0
    style SKIP   fill:#3b0f0f,stroke:#dc2626,color:#e2e8f0
    style ARCHIVE fill:#1e1e2e,stroke:#475569,color:#94a3b8
```

---

## 3. Flux de conversation — Chat Web (Vercel AI SDK + streamdown.ai)

> Rendu des tokens en temps réel via le protocole **Vercel AI Data Stream v1**.  
> Visualisation live possible sur **https://streamdown.ai/** (coller l'URL de l'API).

```mermaid
flowchart TD
    U(["Utilisateur"]) -->|"Question"| FRONTEND

    subgraph FRONTEND ["Next.js — useChat()"]
        direction TB
        SDK["Vercel AI SDK\nuseChat() — streaming natif"]
        PROXY["POST /api/chat\n→ proxy Next.js"]
        SDK --> PROXY
    end

    PROXY -->|"POST /chat\nmessage · session_id · provider · model\ntemperature · k_final · user_id"| FASTAPI

    subgraph FASTAPI ["FastAPI — event_stream()"]
        direction TB
        PII["PIIManager\nmask_text() — spaCy + Regex"]
        SESSION["SessionManager\nload/create session\nstockage JSON par user_id"]
        MEMORY["MemoryManager\nbuild_agent_input()\nrésumé automatique si overflow"]
        PII --> SESSION --> MEMORY
    end

    MEMORY -->|"historique LangChain"| AGENT

    subgraph AGENT ["LangGraph — create_react_agent"]
        A1["system prompt (config/prompt.txt)\n+ archives disponibles"]
        A2["ReAct loop\nObserve → Think → Act"]
        A1 --> A2
    end

    A2 -->|"tool_call: search_knowledge_base"| TOOL

    subgraph TOOL ["tools_oracle.py"]
        T1["embed_query(query)\nnomic-embed-text"]
        T2["VectorManager.search_hybrid()"]
        T3["archives_sacrees XML\ninjected dans le contexte agent"]
        T1 --> T2 --> T3
    end

    subgraph VM ["VectorManager — recherche hybride"]
        S1["Cosine pgvector"]
        S2["BM25 (FTS GIN)"]
        RRF["RRF Fusion\nk_final resultats"]
        S1 --> RRF
        S2 --> RRF
    end

    DB_PG[("Digital Ocean\nPostgres + pgvector")]

    T2 <--> VM
    VM <--> DB_PG

    T3 -->|"contexte RAG"| A2
    A2 -->|"réponse finale"| STREAM

    subgraph STREAM ["SSE FastAPI → AI Data Stream"]
        ST1["session_id · text chunks (0:)\ncot sources (2:) · done (d:) · error (3:)"]
    end

    STREAM -->|"tokens en temps réel"| U

    subgraph PROV ["Providers LLM"]
        direction LR
        P1["Groq"] --- P2["OpenAI"] --- P3["Anthropic"] --- P4["Gemini"] --- P5["Ollama"]
    end

    AGENT <-->|"API call"| PROV

    subgraph POST ["Tâches asynchrones (background)"]
        BG1["MemoryManager.compress()\nsi overflow tokens"]
        BG2["LLM Judge\ncontext_relevance · faithfulness\nanswer_relevance · context_coverage"]
    end

    STREAM -.->|"asyncio.create_task"| POST

    style FRONTEND fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style FASTAPI  fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style AGENT    fill:#1e1e2e,stroke:#a78bfa,color:#e2e8f0
    style TOOL     fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style VM       fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style DB_PG    fill:#1e1e2e,stroke:#059669,color:#e2e8f0
    style STREAM   fill:#1e1e2e,stroke:#38bdf8,color:#e2e8f0
    style PROV     fill:#1e1e2e,stroke:#6366f1,color:#e2e8f0
    style POST     fill:#1e1e2e,stroke:#475569,color:#94a3b8
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

---

## 6. Flux de conversation — Chat via MCP (Model Context Protocol)

> Le serveur MCP est monté sur **`https://api.dlzteam.com/mcp`** (FastAPI `app.mount("/mcp", ...)`).  
> Tout client MCP compatible peut se connecter et appeler les outils RAG directement.

```mermaid
flowchart LR
    subgraph CLIENTS ["Clients MCP (Host)"]
        direction TB
        CL1["Claude Desktop\n(Anthropic)"]
        CL2["Cursor / VS Code\n(Copilot MCP)"]
        CL3["Bot Nuxt\n(bot/server/lib/bot.ts)"]
        CL4["Tout client MCP\n(SSE transport)"]
    end

    subgraph TRANSPORT ["Transport SSE"]
        TR["GET https://api.dlzteam.com/mcp\nContent-Type: text/event-stream"]
    end

    subgraph MCP_SRV ["mcp_server.py — FastMCP"]
        direction TB
        T1["search_knowledge_base(query, k)\nRecherche hybride Cosine+BM25+RRF\nRetourne extraits + score + confiance"]
        T2["list_sources()\nListe les documents ingérés\navec nb chunks et date"]
    end

    subgraph ORACLE_CORE ["Oracle RAG Core"]
        VM["VectorManager\nsearch_hybrid()"]
        DB[("Digital Ocean pgvector")]
        VM <--> DB
    end

    CLIENTS -->|"tool_call JSON"| TRANSPORT
    TRANSPORT --> MCP_SRV
    T1 --> VM
    T2 --> VM
    MCP_SRV -->|"tool_result"| TRANSPORT
    TRANSPORT -->|"réponse structurée"| CLIENTS

    style CLIENTS  fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style TRANSPORT fill:#1e1e2e,stroke:#38bdf8,color:#e2e8f0
    style MCP_SRV  fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style ORACLE_CORE fill:#1e1e2e,stroke:#059669,color:#e2e8f0
```

---

## 7. Flux de conversation — Chat via Bot (Chat SDK)

> Implémenté avec le **Chat SDK** (`chat` + `@chat-adapter/*`) sur Nuxt 4.  
> **Discord** est opérationnel. **WhatsApp** et **Teams** sont supportés par les adaptateurs disponibles.

```mermaid
flowchart TD
    subgraph PLATFORMS ["Plateformes de messagerie"]
        direction LR
        DC["Discord\n(Gateway WS + Webhook)"]
        WA["WhatsApp\n(adaptateur disponible)"]
        TM["Teams / autres\n(adaptateur disponible)"]
    end

    subgraph BOT ["bot/ — Nuxt 4 (Vercel)"]
        direction TB
        PLUGIN["server/plugins/bot.ts\ninitBot() au démarrage"]
        LIB["server/lib/bot.ts\nChat SDK — singleton"]
        GW["GET /api/discord/gateway\nWebSocket Discord — cron Vercel 9min"]
        WH["POST /api/webhooks/:platform\nReception interactions / slash commands"]
        PLUGIN --> LIB
    end

    subgraph CHATCORE ["Chat SDK Core"]
        direction TB
        EV1["onNewMention(thread)\nAbonnement + message de bienvenue"]
        EV2["onSubscribedMessage(thread, msg)\nFetch 20 derniers messages\n→ toAiMessages()"]
        STATE["RedisState\nHistorique multi-tour persisté"]
        EV1 --> STATE
        EV2 --> STATE
    end

    subgraph AI_LAYER ["Couche IA — AI SDK"]
        direction TB
        MODEL["Groq llama-3.3-70b-versatile\n(primaire)\nAnthropic (fallback optionnel)"]
        MCP_CLI["MCP Client\nexperimental_createMCPClient\ntransport: SSE"]
        TOOLS["mcpTools\nsearch_knowledge_base\nlist_sources"]
        STREAM_AI["streamText()\nmaxSteps: 5\n→ thread.post(result.fullStream)"]
        MODEL --> STREAM_AI
        MCP_CLI --> TOOLS
        TOOLS --> STREAM_AI
    end

    subgraph MCP_REMOTE ["MCP Server FastAPI"]
        MCP["https://api.dlzteam.com/mcp\nsearch_knowledge_base · list_sources"]
        RAG[("Digital Ocean pgvector")]
        MCP --> RAG
    end

    DC -->|"mention / message"| BOT
    WA -.->|"(futur)"| BOT
    TM -.->|"(futur)"| BOT
    BOT --> CHATCORE
    CHATCORE --> AI_LAYER
    MCP_CLI -->|"SSE tool_call"| MCP_REMOTE
    MCP_REMOTE -->|"tool_result"| MCP_CLI
    AI_LAYER -->|"réponse streamée"| BOT
    BOT -->|"message progressif"| PLATFORMS

    style PLATFORMS fill:#1e1e2e,stroke:#7c3aed,color:#e2e8f0
    style BOT       fill:#1e1e2e,stroke:#f59e0b,color:#e2e8f0
    style CHATCORE  fill:#1e1e2e,stroke:#a78bfa,color:#e2e8f0
    style AI_LAYER  fill:#1e1e2e,stroke:#38bdf8,color:#e2e8f0
    style MCP_REMOTE fill:#1e1e2e,stroke:#059669,color:#e2e8f0
```

### Connexions possibles résumées

| Canal | Technologie | Statut | Appel RAG |
|---|---|---|---|
| **Web Chat** | Next.js + Vercel AI SDK `useChat()` | Opérationnel | `POST /chat` (SSE direct) |
| **MCP Client** (Claude Desktop, Cursor…) | MCP SSE | Opérationnel | `GET /mcp` → `search_knowledge_base` |
| **Discord Bot** | Chat SDK + `@chat-adapter/discord` | Opérationnel | MCP SSE → `search_knowledge_base` |
| **WhatsApp Bot** | Chat SDK + `@chat-adapter/whatsapp` | Disponible | MCP SSE → `search_knowledge_base` |
| **Teams / autres** | Chat SDK + adaptateur dédié | Disponible | MCP SSE → `search_knowledge_base` |