# liste des imports
import re
import string
import unicodedata
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


class QuestionProcessor:
    def __init__(self):
        # Charger les modèles plus tard
        # On charge le modèle une seule fois à l'init
        print(f"Chargement de l'Oracle (modèle IA)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

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

    def vectoriser(self, cleaned_text):
        """étape 2.7 : transformer le texte en chiffres pour l'IA"""
        # On transforme la phrase en une liste de 384 nombres
        embedding = self.model.encode(cleaned_text)
        return embedding

    def comparer(self, vecteur_question, vecteur_base):
        """Calcule la ressemblance entre deux vecteurs (entre 0 et 1)"""
        # remodeler les vecteurs pour sklearn
        v_q = vecteur_question.reshape(1, -1)
        v_b = vecteur_base.reshape(1, -1)

        score = cosine_similarity(v_q, v_b)
        return score[0][0]