import os

import streamlit as st
import yaml
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from tools_oracle import search_knowledge_base

# CHEMIN CONFIG
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

# CHEMIN PROMPT
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "config", "prompt.txt")

# ======================================

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Alert: config.yaml not found at: {CONFIG_PATH}")

with open(CONFIG_PATH, "r", encoding='utf-8') as f:
    config = yaml.safe_load(f)

with open(PROMPT_PATH, "r", encoding='utf-8') as f:
    system_prompt = f.read()

# 1. Initialization of the LLM with Groq
llm = ChatGroq(
    model=config["api"]["model"],
    temperature=config["api"]["temperature"],
    api_key=config["api"]["api_key"]
)

# 2. Tools
tools = [search_knowledge_base]

# 3. Sys Prompt
SYSTEM_PROMPT = system_prompt

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
if prompt := st.chat_input("Que disent les anciennes écritures ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # L'agent décide seul s'il doit appeler Supabase
            result = agent.invoke({"messages": [("user", prompt)]})
            reponse = result["messages"][-1].content

            st.markdown(reponse)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
        except Exception as e:
            st.error(f"L'Oracle est troublé : {e}")

# streamlit run app.py