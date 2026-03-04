import os

import streamlit as st
import yaml
from langgraph.prebuilt import create_react_agent

from core.tools_oracle import search_knowledge_base
from providers import get_llm, get_available_models, PROVIDER_LABELS
from providers.error_handler import handle_llm_error, OracleError

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
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = st.secrets["prompts"]["system_prompt"]

# ─────────────────────────────────────────────────────────────────
# Page setup
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="HELMo's Oracle", page_icon="🔮")
st.title("🔮 The Sacred Oracle")

# ─────────────────────────────────────────────────────────────────
# Error display helper
# ─────────────────────────────────────────────────────────────────
def display_error(err: OracleError) -> None:
    """
    Renders a structured, user-friendly error card in the Streamlit chat.
    Three layers of information:
      1. A clear title & plain-English explanation  → for everyone
      2. An actionable suggestion                   → for everyone
      3. A collapsible technical detail             → for developers
    """
    st.error(
        f"**{err.icon} {err.title}**\n\n"
        f"{err.message}\n\n"
        f"💡 **What to do:** {err.suggestion}"
    )

    # Collapsible technical details — visible but not intrusive
    with st.expander("🔧 Technical details (for developers)"):
        st.code(
            f"Error type : {err.error_type.value}\n"
            f"Provider   : {err.provider}\n"
            f"Model      : {err.model}\n"
            f"Detail     : {err.technical_msg}",
            language="text",
        )


# ─────────────────────────────────────────────────────────────────
# Sidebar — LLM provider selector
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Oracle Configuration")

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

    selected_model = st.selectbox(
        "🧩 Model",
        options=available_models,
        index=default_model_idx,
    )

    temperature = st.slider(
        "🌡️ Temperature",
        min_value=0.0,
        max_value=1.0,
        value=float(config.get("llm", {}).get("temperature", 0)),
        step=0.05,
    )

    if selected_provider == "ollama":
        ollama_url = config.get("llm", {}).get("ollama", {}).get("base_url", "http://localhost:11434")
        st.caption(f"🏠 Connecting to local Ollama at `{ollama_url}`")
        st.caption("Make sure Ollama is running: `ollama serve`")

    st.divider()
    st.caption("Changes apply on next message.")

# ─────────────────────────────────────────────────────────────────
# Agent factory — recreated when provider/model changes
# ─────────────────────────────────────────────────────────────────
@st.cache_resource(hash_funcs={dict: lambda d: str(sorted(d.items()))})
def load_agent(provider_key: str, model: str, temp: float, _config: dict):
    """
    Creates the LangGraph ReAct agent.
    Cached per (provider, model, temperature) — rebuilt only when settings change.
    """
    print(f"🔮 Oracle initialized — provider={provider_key}, model={model}, temp={temp}")

    llm = get_llm(
        provider_key=provider_key,
        model=model,
        config={**_config, "llm": {**_config.get("llm", {}), "temperature": temp}},
    )

    tools = [search_knowledge_base]
    return create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


# ── Agent init (errors here = config/key problem, block the whole app) ──────
try:
    agent = load_agent(selected_provider, selected_model, temperature, config)
    st.caption(f"Connected to **{selected_provider_label}** · `{selected_model}`")

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
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("What do the ancient scriptures say?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [
        ("user" if msg["role"] == "user" else "assistant", msg["content"])
        for msg in st.session_state.messages
    ]

    with st.chat_message("assistant"):
        try:
            with st.spinner("The Oracle is consulting the stars..."):
                result = agent.invoke({"messages": history})
                response = result["messages"][-1].content

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            # Chat errors — shown inline, app stays alive
            oracle_error = handle_llm_error(e, provider=selected_provider, model=selected_model)
            display_error(oracle_error)