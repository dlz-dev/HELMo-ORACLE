import string
import unicodedata

from typing import List
from langchain_huggingface import HuggingFaceEmbeddings


class QuestionProcessor:
    """
    Handles text cleaning and transformation of user queries into vector embeddings.
    """

    def __init__(self):
        print(f"Chargement de l'Oracle...")
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    def preprocess_text(self, text: str) -> str:
        """
        Cleans the input text by lowercasing, removing accents, and stripping punctuation.

        Args:
            text (str): The raw user query.

        Returns:
            str: The cleaned and normalized text.
        """
        text = text.lower()
        text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        text = text.translate(str.maketrans('', '', string.punctuation))
        return text.strip()

    def vectorize_text(self, text: str) -> List[float]:
        """
        Transforms a text string into a numerical vector (embedding).

        Args:
            text (str): The preprocessed text.

        Returns:
            List[float]: A list of 384 numbers representing the text's semantics.
        """
        # The embed_query method returns a list of floats compatible with pgvector
        return self.embeddings_model.embed_query(text)
