import os

import streamlit as st
import yaml
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from core.tools_oracle import search_knowledge_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")
PROMPT_PATH = os.path.join(BASE_DIR, "config", "prompt.txt")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    config = {
        "api": {
            "model": st.secrets["api"]["model"],
            "temperature": st.secrets["api"]["temperature"],
            "api_key": st.secrets["api"]["api_key"]
        }
    }

if os.path.exists(PROMPT_PATH):
    with open(PROMPT_PATH, "r", encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = st.secrets["prompts"]["system_prompt"]

llm = ChatGroq(
    model=config["api"]["model"],
    temperature=config["api"]["temperature"],
    api_key=config["api"]["api_key"]
)

tools = [search_knowledge_base]

agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

st.set_page_config(page_title="HELMo's Oracle", page_icon="🔮")
st.title("🔮 The Sacred Oracle")
st.caption("Connected to Supabase & Powered by Groq")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("What do the ancient scriptures say?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = []
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "assistant"
        history.append((role, msg["content"]))

    with st.chat_message("assistant"):
        try:
            with st.spinner("The Oracle is consulting the stars..."):
                result = agent.invoke({"messages": history})
                reponse = result["messages"][-1].content

            st.markdown(reponse)

            st.session_state.messages.append({"role": "assistant", "content": reponse})

        except Exception as e:
            st.error(f"The Oracle is troubled: {e}")
