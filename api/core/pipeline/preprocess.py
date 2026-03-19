"""
Handles the preprocessing and embedding of textual queries.
"""

import string
import unicodedata
from typing import List

from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class QuestionProcessor:
    """
    Handles text cleaning and transformation of user queries into vector embeddings.
    """

    def __init__(self) -> None:
        """
        Initializes the HuggingFace embedding model for vectorizing queries.
        """
        print("🔮 Loading the Oracle embedding model...")
        self.embeddings_model = HuggingFaceEmbedding(
            model_name="intfloat/multilingual-e5-base"
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
        return self.embeddings_model.get_query_embedding(text)