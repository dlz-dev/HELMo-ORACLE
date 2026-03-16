"""
Handles Personally Identifiable Information (PII) masking using a hybrid approach.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import spacy


class PIIManager:
    """
    Manages PII masking using Regex for structured data and Spacy NER for 
    unstructured entities. Implements a Singleton pattern for the Spacy model.
    """

    _nlp_model: Optional[Any] = None

    def __init__(self, model_name: str = "fr_core_news_sm") -> None:
        """
        Initializes the PII Manager and loads the model if not already present.

        Args:
            model_name (str): The name of the Spacy model to load.
        """
        self.model_name = model_name
        self._ensure_model_loaded()

        self.patterns: Dict[str, str] = {
            "[EMAIL]": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[PHONE]": r"\b(?:\+?\d{1,3})?[-.]?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}\b",
            "[IP_ADDR]": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        }

    @classmethod
    def _ensure_model_loaded(cls) -> None:
        """
        Loads the Spacy model into the class variable safely.
        Disables unnecessary pipeline components for speed optimization.
        """
        if cls._nlp_model is None:
            try:
                cls._nlp_model = spacy.load(
                    "fr_core_news_sm",
                    disable=["parser", "tagger", "attribute_ruler", "lemmatizer"],
                )
            except OSError:
                print("⚠️ Spacy model not found. Downloading 'fr_core_news_sm'...")
                from spacy.cli import download

                download("fr_core_news_sm")
                cls._nlp_model = spacy.load(
                    "fr_core_news_sm",
                    disable=["parser", "tagger", "attribute_ruler", "lemmatizer"],
                )

    def mask_text(self, text: str) -> str:
        """
        Sanitizes text by removing predefined patterns and recognized entities.

        Args:
            text (str): The raw text to process.

        Returns:
            str: The sanitized text with PII masked.
        """
        if not text:
            return ""

        masked_text = text

        for placeholder, pattern in self.patterns.items():
            masked_text = re.sub(pattern, placeholder, masked_text)

        doc = self._nlp_model(masked_text)

        replacements: List[Tuple[str, str]] = []
        for ent in doc.ents:
            if ent.label_ == "PER":
                replacements.append((ent.text, "[PERSON]"))
            elif ent.label_ == "LOC":
                replacements.append((ent.text, "[LOCATION]"))
            elif ent.label_ == "ORG":
                replacements.append((ent.text, "[ORG]"))

        # Sort replacements by length descending to prevent partial masking issues
        replacements.sort(key=lambda x: len(x[0]), reverse=True)

        for original, mask in replacements:
            # Using regex word boundaries ensures we don't partially mask substrings
            escaped_original = re.escape(original)
            pattern = rf"\b{escaped_original}\b"
            masked_text = re.sub(pattern, mask, masked_text)

        return " ".join(masked_text.split())