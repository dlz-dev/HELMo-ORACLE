# 🔮 The Sacred Oracle - RAG Project

This project aims to design an **intelligent Oracle** capable of answering questions about a video game universe by relying on a **RAG (Retrieval-Augmented Generation)** architecture. It ensures context-aware responses by searching through ancient archives stored in a vector database.

---

## 🌟 Features

* **RAG Architecture**: Uses semantic search to provide accurate, data-driven answers rather than relying on general LLM knowledge.
* **Multilingual Embeddings**: Powered by the `paraphrase-multilingual-MiniLM-L12-v2` model to capture meaning across different languages.
* **Agentic Search**: A ReAct agent autonomously decides when to consult the knowledge base using specialized tools.
* **Interactive UI**: A sleek chat interface built with **Streamlit** for an immersive "Oracle" experience.
* **Strict Guardrails**: Zero-hallucination policy enforced through rigorous system prompts, ensuring the Oracle only speaks from its archives.

---

## 🛠️ Prerequisites

* **Python 3.12**: The project is optimized for this version to ensure library stability.
* **Docker Desktop**: Required to run the local PostgreSQL/pgvector instance if not using a cloud provider.
* **Supabase Account**: (Optional) For hosting your PostgreSQL database with vector support in the cloud.

---

## 🚀 Setup & Installation

### 1. Database & API Configuration

First, you need to prepare your environment variables and database connection.

* **Supabase**: Create a project and enable the `pgvector` extension.
* **Groq API**: Obtain an API key to access high-speed LLMs like `llama-3.3-70b-versatile`.

### 2. Configuration Files

Navigate to the `config/` directory and create the following files:

| File | Purpose | Template |
| --- | --- | --- |
| **`config.yaml`** | Stores database credentials and API settings. | Use `config.example.yaml`. |
| **`prompt.txt`** | Defines the Oracle's personality and rules. | Use `prompt.example.txt` as a base. |

> [!IMPORTANT]
> Ensure your `config.yaml` includes your `api_key` and correct database `host`.

### 3. Data Ingestion

Place your raw knowledge files in the `data/files/` directory. The project supports the following formats:

* **CSV**: For structured data like Bestiaries or Item lists.
* **Markdown (.md)**: Great for guides and long-form survival instructions.
* **Text (.txt)**: For ancient legends and lore.

Run the ingestion script to vectorize and store your data:

```bash
python -m core.ingestion

```

### 4. Launching the Oracle

Once the database is seeded, start the interactive interface:

```bash
streamlit run app.py

```

---

## 🏗️ Project Structure

* **`converters/`**: Scripts to clean and standardize heterogeneous data formats.
* **`core/`**: The "brain" of the project, handling vectorization and database management.
* **`data/files/`**: Your source archives.
* **`tools_oracle.py`**: Custom LangChain tools for database retrieval.