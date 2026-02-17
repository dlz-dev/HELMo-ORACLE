import os
from typing import List, Tuple

import psycopg
import yaml
from langchain_huggingface import HuggingFaceEmbeddings
from pgvector.psycopg import register_vector

# Directory structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"config.yaml not found at this place : {CONFIG_PATH}")

with open(CONFIG_PATH, "r", encoding='utf-8') as f:
    config = yaml.safe_load(f)


class VectorManager:
    """
    Handles connections to the PostgreSQL/Supabase database and manages
    vector operations using pgvector.
    """

    def __init__(self):
        # Configuration de la connexion
        self.conn = psycopg.connect(
            host=config['database']['host'],
            dbname=config['database']['dbname'],
            user=config['database']['user'],
            password=config['database']['password'],
            port=config['database']['port'],
            sslmode='require'
        )
        register_vector(self.conn)

        # Le modèle d'IA pour transformer le texte en vecteurs
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    def add_document(self, text: str) -> None:
        """
        Generates an embedding for the text and saves it to the database.

        Args:
            text (str): The text content to be vectorized and stored.
        """
        # Vector generation (size 384 for this specific model)
        vector = self.embeddings_model.embed_query(text)

        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (content, vecteur) VALUES (%s, %s)",
                (text, vector)
            )
        self.conn.commit()

    def search_similar(self, query_vector: List[float], k: int = 3) -> List[Tuple[str, float]]:
        """
        Performs a semantic search to find the closest text passages.

        Args:
            query_vector (List[float]): The vector representation of the user's question.
            k (int): Number of similar results to return.

        Returns:
            List[Tuple[str, float]]: List of tuples containing (content, distance).
        """
        with self.conn.cursor() as cur:
            # Using the Euclidean distance operator (<->) provided by pgvector
            # '::vector' cast ensures the database interprets the list as a vector
            cur.execute(
                "SELECT content, vecteur <-> %s::vector as distance FROM documents ORDER BY distance LIMIT %s",
                (query_vector, k)
            )
            return cur.fetchall()
