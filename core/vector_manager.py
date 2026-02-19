import json
import os
from typing import List, Tuple

import psycopg
import streamlit as st
import yaml
from langchain_huggingface import HuggingFaceEmbeddings
from pgvector.psycopg import register_vector

# Directory structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

if os.path.exists(CONFIG_PATH):
    # LOCAL: Read the YAML file
    with open(CONFIG_PATH, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    # CLOUD: Use Streamlit Secrets
    config = st.secrets


class VectorManager:
    """
    Handles connections to the PostgreSQL/Supabase database and manages
    vector operations using pgvector.
    """

    def __init__(self):
        if 'connection_string' in config['database']:
            self.conn = psycopg.connect(
                config['database']['connection_string'],
                autocommit=True
            )
        else:
            self.conn = psycopg.connect(
                host=config['database']['host'],
                dbname=config['database']['dbname'],
                user=config['database']['user'],
                password=config['database']['password'],
                port=int(config['database']['port']),
                sslmode='require'
            )

        register_vector(self.conn)
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    def add_document(self, text: str, metadata: dict = None) -> None:
        """
        Generates an embedding and saves the text WITH its metadata.
        """
        if metadata is None:
            metadata = {}

        vector = self.embeddings_model.embed_query(text)

        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (content, vecteur, metadata) VALUES (%s, %s, %s)",
                (text, vector, json.dumps(metadata))
            )
        self.conn.commit()

    def search_similar(self, query_vector: List[float], k: int = 3) -> List[Tuple[str, float, dict]]:
        """
        Semantic search that also returns metadata.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT content, vecteur <-> %s::vector as distance, metadata FROM documents ORDER BY distance LIMIT %s",
                (query_vector, k)
            )
            return cur.fetchall()