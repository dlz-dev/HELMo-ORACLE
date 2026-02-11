import psycopg
from pgvector.psycopg import register_vector
from langchain_huggingface import HuggingFaceEmbeddings


class GestionnaireVecteurs:
    def __init__(self):
        # Configuration de la connexion
        self.conn = psycopg.connect(
            dbname="vector_app_db",
            user="admin",
            password="supersecret",
            host="localhost",
            port="5432"
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
                "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
                (texte, vecteur)
            )
        self.conn.commit()

    def rechercher_similaires(self, vecteur_question, k=3):
        """cherche les passages les plus proches du coup"""
        with self.conn.cursor() as cur:
            # distance euclidienne
            # :: vector pour préciser que c'est un vecteur sinon il galère le boss
            cur.execute(
                "SELECT content, embedding <-> %s::vector as distance FROM documents ORDER BY distance LIMIT %s",
                (vecteur_question, k)
            )
            return cur.fetchall()