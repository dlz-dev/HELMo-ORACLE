import re
import spacy
import logging

# Configure logging
logger = logging.getLogger(__name__)


class PIIManager:
    """
    Handles Personally Identifiable Information (PII) masking using a hybrid approach:
    1. Regex for structured data (Emails, Phones, IPs) - Ultra Fast.
    2. Spacy NER for unstructured entities (Names, Locations) - Optimized.

    Implements a Singleton pattern for the Spacy model to avoid reloading logic.
    """

    _nlp_model = None  # Class variable to hold the model in memory (Singleton)

    def __init__(self, model_name="fr_core_news_sm"):
        """
        Initialize the PII Manager.
        Loads the model only if it hasn't been loaded yet.
        """
        self.model_name = model_name
        self._ensure_model_loaded()

        # ─── REGEX PATTERNS (The Fast Lane) ─────────────────────────────
        self.patterns = {
            '[EMAIL]': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[PHONE]': r'(?:\+?\d{1,3})?[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}',
            '[IP_ADDR]': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            # You can add IBAN or Credit Card patterns here
        }

    @classmethod
    def _ensure_model_loaded(cls):
        """
        Loads the Spacy model into the class variable if not already present.
        Optimized: Disables 'parser' and 'tagger' for speed (we only need NER).
        """
        if cls._nlp_model is None:
            try:
                logger.info("Loading Spacy NER model... (This happens only once)")
                # 'parser' and 'tagger' are heavy and useless for just Entity Recognition.
                # Disabling them makes the process much faster.
                cls._nlp_model = spacy.load("fr_core_news_sm",
                                            disable=["parser", "tagger", "attribute_ruler", "lemmatizer"])
            except OSError:
                logger.warning("Spacy model not found. Downloading 'fr_core_news_sm'...")
                from spacy.cli import download
                download("fr_core_news_sm")
                cls._nlp_model = spacy.load("fr_core_news_sm",
                                            disable=["parser", "tagger", "attribute_ruler", "lemmatizer"])

    def mask_text(self, text: str) -> str:
        """
        Main function to sanitize text.
        """
        if not text:
            return ""

        masked_text = text

        # 1. Apply Regex (Instantaneous)
        for placeholder, pattern in self.patterns.items():
            masked_text = re.sub(pattern, placeholder, masked_text)

        # 2. Apply NER (Optimized execution)
        # Process the text with the pre-loaded model
        doc = self._nlp_model(masked_text)

        # We collect replacements first to avoid index shifting issues during replacement
        replacements = []
        for ent in doc.ents:
            if ent.label_ == "PER":
                replacements.append((ent.text, "[PERSON]"))
            elif ent.label_ == "LOC":
                replacements.append((ent.text, "[LOCATION]"))
            elif ent.label_ == "ORG":
                replacements.append((ent.text, "[ORG]"))

        # Apply replacements (simple string replace for safety,
        # though regex with boundaries is safer for production)
        for original, mask in replacements:
            masked_text = masked_text.replace(original, mask)

        return masked_text