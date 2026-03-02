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
        Uses Contextual Embedding to enrich the vector before saving.
        """
        if metadata is None:
            metadata = {}

        # 1. Prepare the contextualized text for the embedding model
        text_to_embed = text

        # If it's a long text file with a global context
        if "global_context" in metadata:
            text_to_embed = f"Global Context: {metadata['global_context']}\n\nContent: {text}"

        # If it's a Markdown file (headers from Phase 1)
        elif "Header 1" in metadata:
            text_to_embed = f"Chapter: {metadata['Header 1']}\n\nContent: {text}"

        # If it's a JSON file (categories and items)
        elif "category" in metadata and "item_name" in metadata:
            text_to_embed = f"Category: {metadata['category']} | Item: {metadata['item_name']}\n\nContent: {text}"

        # 2. Vectorize the RICH text (context + content)
        vector = self.embeddings_model.embed_query(text_to_embed)

        # 3. Save the ORIGINAL text in the database (so the Oracle reads the clean version)
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