import os

import streamlit as st
import yaml
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from core.tools_oracle import search_knowledge_base

# CHEMIN CONFIG
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

# CHEMIN PROMPT
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "config", "prompt.txt")

# ======================================

# Gestion hybride Config (Local) / Secrets (Cloud)
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    # Si le fichier n'existe pas, on récupère les données dans st.secrets
    config = {
        "api": {
            "model": st.secrets["api"]["model"],
            "temperature": st.secrets["api"]["temperature"],
            "api_key": st.secrets["api"]["api_key"]
        }
    }

# --- CHARGEMENT DU PROMPT ---
if os.path.exists(PROMPT_PATH):
    # En local, on lit le fichier
    with open(PROMPT_PATH, "r", encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read()
else:
    # Sur Streamlit Cloud, on prend le secret
    SYSTEM_PROMPT = st.secrets["prompts"]["system_prompt"]

# 1. Initialization of the LLM with Groq
llm = ChatGroq(
    model=config["api"]["model"],
    temperature=config["api"]["temperature"],
    api_key=config["api"]["api_key"]
)

# 2. Tools
tools = [search_knowledge_base]

# 4. Create Agent
agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="L'Oracle de HELMo", page_icon="🔮")
st.title("🔮 L'Oracle Sacré")
st.caption("Connecté à Supabase & Propulsé par Groq")

# Gestion de l'historique
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Zone de saisie
# ---- UPDATE TIM -> mise en place d'une mémoire, au lieu d'envoyer juste le prompt on envoie tout le contenu de la conv
if prompt := st.chat_input("Que disent les anciennes écritures ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    # création d'une liste
    # transfo de l'historique de streamlit
    history = []
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "assistant"
        history.append((role, msg["content"]))

    with st.chat_message("assistant"):
        try:
            # on envoie tout l'historique pas juste le dernier truc
            result = agent.invoke({"messages": history})
            reponse = result["messages"][-1].content

            st.markdown(reponse)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
        except Exception as e:
            st.error(f"L'Oracle est troublé : {e}")

# streamlit run app.py
