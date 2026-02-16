import string
import unicodedata
from langchain_huggingface import HuggingFaceEmbeddings


class QuestionProcessor:
    def __init__(self):
        # On charge le modèle une seule fois à l'init
        print(f"Chargement de l'Oracle...")
        self.embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def clean_text(self, text):
        """Regroupe les étapes 2.1 à 2.6"""

        # étape 2.2
        text = text.lower()

        # Nettoyage des accents (utile en français)
        text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

        # 2.6 retirer la ponctuation
        text = text.translate(str.maketrans('', '', string.punctuation))

        # 2.3 Tokenisation + 2.4 + 2.5 (simplifié pour débuter)
        # on découpe mot par mot et on peut filtrer les mots de moins de 3 lettres
        return text.strip()

    def vectoriser(self, text):
        """étape 2.7 : transformer le texte en chiffres pour l'IA"""
        # On transforme la phrase en une liste de 384 nombres
        return self.embeddings_model.embed_query(text)