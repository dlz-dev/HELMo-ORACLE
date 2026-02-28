import os
import streamlit as st
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    config = st.secrets

ADMIN_PASSWORD = config["admin"]["password"]
DATA_DIR = os.path.join(BASE_DIR, "data", "files")

st.set_page_config(page_title="Oracle Admin")
st.title("Oracle — Administration")

# Authentification
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Admin password", type="password")
    if st.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop()

# Interface admin
st.success("Connected as administrator")

uploaded_file = st.file_uploader(
    "Drop a file to feed the Oracle",
    type=["csv", "json", "md", "txt"]
)

if uploaded_file is not None:
    file_path = os.path.join(DATA_DIR, uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with st.spinner(f"Ingesting {uploaded_file.name}..."):
        try:
            from core.ingestion import seed_database_single_file
            seed_database_single_file(file_path)
            st.success(f"✅ {uploaded_file.name} successfully ingested ! The Oracle can now answer questions about it.")
        except Exception as e:
            st.error(f"Ingestion error : {e}")