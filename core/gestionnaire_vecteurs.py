import psycopg
from pgvector.psycopg import register_vector
from langchain_huggingface import HuggingFaceEmbeddings
import os
import yaml

# On définit la racine du projet (un niveau au dessus de 'core')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Alerte : Le fichier config.yaml est introuvable à cet endroit : {CONFIG_PATH}")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)


class GestionnaireVecteurs:
    def __init__(self):
        # Configuration de la connexion
        self.conn = psycopg.connect(
            host=config['database']['host'],
            dbname=config['database']['dbname'],
            user=config['database']['user'],
            password=config['database']['password'],
            port=config['database']['port'],
            sslmode='require'  # <-- C'est ça qui permet de parler à Supabase
        )
        register_vector(self.conn)

        # Le modèle d'IA pour transformer le texte en vecteurs
        self.embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def ajouter_document(self, texte):
        """transforme et ajoute en base """
        # génération du vecteur (taille 384)
        vecteur = self.embeddings_model.embed_query(texte)

        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (content, vecteur) VALUES (%s, %s)",
                (texte, vecteur)
            )
        self.conn.commit()

    def rechercher_similaires(self, vecteur_question, k=3):
        """cherche les passages les plus proches du coup"""
        with self.conn.cursor() as cur:
            # distance euclidienne
            # :: vector pour préciser que c'est un vecteur sinon il galère le boss
            cur.execute(
                "SELECT content, vecteur <-> %s::vector as distance FROM documents ORDER BY distance LIMIT %s",
                (vecteur_question, k)
            )
            return cur.fetchall()