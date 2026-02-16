from langchain_core.tools import tool
from core.gestionnaire_vecteurs import GestionnaireVecteurs


@tool
def rechercher_dans_base_connaissances(query: str):
    """
    Recherche des informations dans les archives de l'Oracle.
    À utiliser pour toute question sur les légendes, les quêtes ou le guide de survie.
    """
    gv = GestionnaireVecteurs()
    # On cherche les 3 meilleurs extraits
    # (rechercher_similaires s'occupe déjà de transformer la query en vecteur)
    vecteur_query = gv.embeddings_model.embed_query(query)
    resultats = gv.rechercher_similaires(vecteur_query, k=3)

    # On nettoie le texte pour le donner au LLM
    contexte = "\n\n".join([f"Extrait : {res[0]}" for res in resultats])
    return contexte