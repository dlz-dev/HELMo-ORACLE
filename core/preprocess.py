# liste des imports
import re
import string
import unicodedata

class QuestionProcessor:
    def __init__(self):
        # charger les modèles plus tard
        pass

    def clean_text(self, text):
        """Regroupe les étapes 2.1 à 2.6"""

        # étape 2.2
        text = text.lower()

        # Nettoyage des accents (utile en français)
        text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != 'Mn')

        # 2.6 retirer la ponctuation
        text = text.translate(str.maketrans('', '', string.punctuation))

        # 2.3 Tokenisation + 2.4 + 2.5 (simplifié pour débuter)
        # on découpe mot par mot et on peut filtrer les mots de moins de 3 lettres
        words = text.split()

        return ''.join(words)

    def vectoriser(self, cleaned_text):
        """étape 2.7 : transformer le texte en chiffres pour l'IA"""
        # c'est ici qu'on fera appel au modèle de vectorisation
        # pour l'instant on retourne juste un message de debug
        print(f"DEBUG : Prêt à vectoriser : {cleaned_text}")
        return None 