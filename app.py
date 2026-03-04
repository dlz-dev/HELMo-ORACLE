import os
import re

import streamlit as st
import yaml
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.prebuilt import create_react_agent

from core.memory_manager import MemoryManager
from core.session_manager import SessionManager, _is_cloud
from core.tools_oracle import get_search_tool
from core.vector_manager import VectorManager
from providers import get_llm, get_available_models, PROVIDER_LABELS
from providers.error_handler import handle_llm_error, OracleError


# ─────────────────────────────────────────────────────────────────
# Response formatter — fixes LLM plain text → proper Markdown
# ─────────────────────────────────────────────────────────────────
def _format_response(text: str) -> str:
    """
    Converts LLM plain-text output to proper Markdown for Streamlit rendering.

    Fixes:
    - Bullet points: • or · at line start  →  proper "- " markdown list items
    - Section headers: short lines ending with ":"  →  **bold header**
    - Cleans up excessive blank lines (max 1 consecutive blank line)
    """
    lines = text.split("\n")
    formatted = []

    for line in lines:
        stripped = line.strip()

        # Convert bullet characters to markdown list items
        if stripped.startswith("•") or stripped.startswith("·"):
            line = "- " + stripped[1:].strip()

        # Section headers: short line ending with ":" → bold
        elif (
                stripped.endswith(":")
                and len(stripped) < 60
                and not stripped.startswith("-")
                and not stripped.startswith("*")
                and not stripped.startswith("[")  # avoid mangling [Source: ...]
        ):
            line = f"\n**{stripped}**"

        else:
            line = stripped if stripped else ""

        formatted.append(line)

    # Remove excessive blank lines (max 1 consecutive)
    result = "\n".join(formatted)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


# ─────────────────────────────────────────────────────────────────
# Config & Prompt loading
# ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")
PROMPT_PATH = os.path.join(BASE_DIR, "config", "prompt.txt")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
else:
    config = st.secrets

if os.path.exists(PROMPT_PATH):
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        BASE_SYSTEM_PROMPT = f.read()
else:
    BASE_SYSTEM_PROMPT = st.secrets["prompts"]["system_prompt"]

# ─────────────────────────────────────────────────────────────────
# Page setup
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="HELMo's Oracle", page_icon="🔮")
st.title("🔮 The Sacred Oracle")


# ─────────────────────────────────────────────────────────────────
# Singletons
# ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_embeddings_model() -> HuggingFaceEmbeddings:
    """
    Single shared instance of the embedding model.
    Prevents duplicate PyTorch loading across VectorManager and all embeddings consumers.
    which causes: "Cannot copy out of meta tensor; no data!"
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )


@st.cache_resource
def get_vector_manager() -> VectorManager:
    """
    Single shared VectorManager — reuses the shared embedding model.
    Prevents PyTorch from loading the model multiple times.
    """
    return VectorManager(embeddings_model=get_embeddings_model())


@st.cache_resource
def get_session_manager() -> SessionManager:
    return SessionManager()


@st.cache_resource
def get_memory_manager() -> MemoryManager:
    max_tokens = config.get("memory", {}).get("max_recent_tokens", 2000)
    min_recent = config.get("memory", {}).get("min_recent_messages", 4)
    return MemoryManager(max_recent_tokens=max_tokens, min_recent_messages=min_recent)


sm = get_session_manager()
mm = get_memory_manager()
vm = get_vector_manager()


# ─────────────────────────────────────────────────────────────────
# Error display helper
# ─────────────────────────────────────────────────────────────────
def display_error(err: OracleError) -> None:
    st.error(
        f"**{err.icon} {err.title}**\n\n"
        f"{err.message}\n\n"
        f"💡 **What to do:** {err.suggestion}"
    )
    with st.expander("🔧 Technical details (for developers)"):
        st.code(
            f"Error type : {err.error_type.value}\n"
            f"Provider   : {err.provider}\n"
            f"Model      : {err.model}\n"
            f"Detail     : {err.technical_msg}",
            language="text",
        )


# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Oracle Configuration")

    # ── Logged-in user (cloud only) ───────────────────────────────
    if _is_cloud():
        try:
            user = st.experimental_user
            if user and user.email:
                st.caption(f"👤 Connected as **{user.name or user.email}**")
        except Exception:
            pass
        st.divider()

    # ── LLM Provider & Model ──────────────────────────────────────
    provider_options = list(PROVIDER_LABELS.keys())
    provider_display = list(PROVIDER_LABELS.values())

    default_provider = config.get("llm", {}).get("default_provider", "groq")
    default_provider_idx = (
        provider_options.index(default_provider)
        if default_provider in provider_options else 0
    )

    selected_provider_label = st.selectbox(
        "🌐 LLM Provider",
        options=provider_display,
        index=default_provider_idx,
    )
    selected_provider = provider_options[provider_display.index(selected_provider_label)]

    available_models = get_available_models(selected_provider, config)
    default_model = config.get("llm", {}).get("default_model", available_models[0])
    default_model_idx = (
        available_models.index(default_model)
        if default_model in available_models else 0
    )
    selected_model = st.selectbox("🧩 Model", options=available_models, index=default_model_idx)

    temperature = st.slider(
        "🌡️ Temperature",
        min_value=0.0, max_value=1.0,
        value=float(config.get("llm", {}).get("temperature", 0)),
        step=0.05,
    )

    if selected_provider == "ollama":
        ollama_url = config.get("llm", {}).get("ollama", {}).get("base_url", "http://localhost:11434")
        st.caption(f"🏠 Connecting to Ollama at `{ollama_url}`")
        st.caption("Make sure Ollama is running: `ollama serve`")

    st.divider()

    # ── Session management ────────────────────────────────────────
    st.subheader("💬 Sessions")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ New", use_container_width=True):
            new_session = sm.new_session(provider=selected_provider, model=selected_model)
            st.session_state.current_session = new_session
            st.rerun()
    with col2:
        if st.button("🗑️ Delete", use_container_width=True):
            if "current_session" in st.session_state:
                sm.delete(st.session_state.current_session["session_id"])
                del st.session_state.current_session
                st.rerun()

    # Past sessions list
    past_sessions = sm.list_sessions()
    if past_sessions:
        st.caption(f"📁 {len(past_sessions)} saved session(s) — backend: `{sm.backend_name}`")
        for s in past_sessions:
            # Highlight active session
            is_active = (
                    "current_session" in st.session_state
                    and st.session_state.current_session["session_id"] == s["session_id"]
            )
            label = f"{'▶ ' if is_active else ''}{s['title'][:35]}"
            if st.button(label, key=f"sess_{s['session_id']}", use_container_width=True):
                loaded = sm.load(s["session_id"])
                if loaded:
                    st.session_state.current_session = loaded
                    st.rerun()
    else:
        st.caption("No saved sessions yet.")

    st.divider()
    st.caption("Changes apply on next message.")

# ─────────────────────────────────────────────────────────────────
# Session init
# ─────────────────────────────────────────────────────────────────
if "current_session" not in st.session_state:
    st.session_state.current_session = sm.new_session(
        provider=selected_provider,
        model=selected_model,
    )

session = st.session_state.current_session


# ─────────────────────────────────────────────────────────────────
# Agent factory
# ─────────────────────────────────────────────────────────────────
@st.cache_resource(hash_funcs={dict: lambda d: str(sorted(d.items()))})
def load_llm(provider_key: str, model: str, temp: float, _config: dict):
    """
    The LLM is cached by (provider, model, temperature) — expensive to create.
    The agent is NOT cached because its system prompt changes with memory summaries.
    Separating the two avoids stale agents serving wrong context.
    """
    print(f"🔮 LLM initialized — provider={provider_key}, model={model}, temp={temp}")
    return get_llm(
        provider_key=provider_key,
        model=model,
        config={**_config, "llm": {**_config.get("llm", {}), "temperature": temp}},
    )


try:
    # LLM is cached (costly) — agent is rebuilt fresh each run (cheap, avoids stale cache)
    llm = load_llm(selected_provider, selected_model, temperature, config)

    # Build enriched prompt with current memory summary injected
    enriched_prompt, _ = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)

    # Always fresh — no cache — system prompt reflects current session memory
    search_tool = get_search_tool(vm)
    agent = create_react_agent(llm, [search_tool], prompt=enriched_prompt)

    st.caption(f"Connected to **{selected_provider_label}** · `{selected_model}`")

    # Show memory status in caption if a summary exists
    if session.get("summary"):
        word_count = len(session["summary"].split())
        st.caption(f"🧠 Memory active — {len(session['messages'])} recent messages + {word_count}-word summary")

except Exception as e:
    oracle_error = handle_llm_error(e, provider=selected_provider, model=selected_model)
    st.error(
        f"**{oracle_error.icon} {oracle_error.title}**\n\n"
        f"The Oracle could not start.\n\n"
        f"{oracle_error.message}\n\n"
        f"💡 **What to do:** {oracle_error.suggestion}"
    )
    with st.expander("🔧 Technical details (for developers)"):
        st.code(
            f"Error type : {oracle_error.error_type.value}\n"
            f"Provider   : {oracle_error.provider}\n"
            f"Model      : {oracle_error.model}\n"
            f"Detail     : {oracle_error.technical_msg}",
            language="text",
        )
    st.stop()

# ─────────────────────────────────────────────────────────────────
# Chat UI
# ─────────────────────────────────────────────────────────────────

# Display current session title
if session.get("title") and session["title"] != "New conversation":
    st.caption(f"📖 **{session['title']}**")

# Render existing messages
for msg in session.get("messages", []):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("What do the ancient scriptures say?"):

    # Add user message to session
    session["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build history from recent window (memory-aware)
    _, history = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)

    with st.chat_message("assistant"):
        try:
            with st.spinner("The Oracle is consulting the stars..."):
                result = agent.invoke({"messages": history})
                response = _format_response(result["messages"][-1].content)

            st.markdown(response)

            # Add assistant response to session
            session["messages"].append({"role": "assistant", "content": response})

            # ── Memory compression (if needed) ────────────────────
            if mm.needs_summarization(session["messages"], session.get("summary", "")):
                with st.spinner("🧠 The Oracle is consolidating its memory..."):
                    session = mm.compress(session, llm)
                    st.session_state.current_session = session

            # ── Persist session ───────────────────────────────────
            session["provider"] = selected_provider
            session["model"] = selected_model
            sm.save(session)
            st.session_state.current_session = session

        except Exception as e:
            oracle_error = handle_llm_error(e, provider=selected_provider, model=selected_model)
            display_error(oracle_error)
