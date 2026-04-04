"""
Handles the preprocessing and embedding of textual queries.
"""

import os
import string
from typing import List

import unicodedata
from langchain_community.embeddings import OllamaEmbeddings


class QuestionProcessor:
    """
    Handles text cleaning and transformation of user queries into vector embeddings.
    """

    def __init__(self) -> None:
        """
        Initializes the Ollama embedding model for vectorizing queries.
        """
        print("🔮 Loading the Oracle embedding model...")
        self.embeddings_model = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    def preprocess_text(self, text: str) -> str:
        """
        Cleans the input text by lowercasing, removing accents, and stripping punctuation.

        Args:
            text (str): The raw text to process.

        Returns:
            str: The normalized, clean text.
        """
        text = text.lower()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
        )
        text = text.translate(str.maketrans("", "", string.punctuation))
        return " ".join(text.split())

    def vectorize_text(self, text: str) -> List[float]:
        """
        Transforms a text string into a numerical vector representation.

        Args:
            text (str): The cleaned text to embed.

        Returns:
            List[float]: The generated text embedding compatible with pgvector.
        """
        return self.embeddings_model.embed_query(text)
