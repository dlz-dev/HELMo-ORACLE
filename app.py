import os

import streamlit as st
import yaml
from langgraph.prebuilt import create_react_agent

from core.tools_oracle import search_knowledge_base
from providers import get_llm, get_available_models, PROVIDER_LABELS

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
# Sidebar — LLM provider selector
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Oracle Configuration")

    # Provider selection
    provider_options = list(PROVIDER_LABELS.keys())
    provider_display = list(PROVIDER_LABELS.values())

    default_provider = config.get("llm", {}).get("default_provider", "groq")
    default_provider_idx = provider_options.index(default_provider) if default_provider in provider_options else 0

    selected_provider_label = st.selectbox(
        "🌐 LLM Provider",
        options=provider_display,
        index=default_provider_idx,
    )
    selected_provider = provider_options[provider_display.index(selected_provider_label)]

    # Model selection — dynamic list based on provider
    available_models = get_available_models(selected_provider, config)

    default_model = config.get("llm", {}).get("default_model", available_models[0])
    default_model_idx = available_models.index(default_model) if default_model in available_models else 0

    selected_model = st.selectbox(
        "🧩 Model",
        options=available_models,
        index=default_model_idx,
    )

    # Temperature override
    temperature = st.slider(
        "🌡️ Temperature",
        min_value=0.0,
        max_value=1.0,
        value=float(config.get("llm", {}).get("temperature", 0)),
        step=0.05,
    )

    # Local note for Ollama
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
    Cached per (provider, model, temperature) combination.
    A new agent is created only when the user changes settings.
    """
    print(f"🔮 Oracle initialized — provider={provider_key}, model={model}, temp={temp}")

    llm = get_llm(
        provider_key=provider_key,
        model=model,
        config={**_config, "llm": {**_config.get("llm", {}), "temperature": temp}},
    )

    tools = [search_knowledge_base]
    return create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


# Resolve current config override for temperature
config_with_temp = {
    **config,
    "llm": {**config.get("llm", {}), "temperature": temperature},
}

try:
    agent = load_agent(selected_provider, selected_model, temperature, config)
    st.caption(f"Connected to **{selected_provider_label}** · `{selected_model}`")
except Exception as e:
    st.error(f"⚠️ Could not initialize the Oracle: {e}")
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
            st.error(f"The Oracle is troubled: {e}")