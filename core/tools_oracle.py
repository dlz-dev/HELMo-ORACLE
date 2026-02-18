from langchain_core.tools import tool
from core.vector_manager import VectorManager


@tool
def search_knowledge_base(query: str) -> str:
    """
    Searches the Oracle's complete database for any information.
    Use this for any inquiry regarding the game world, including its lore,
    entities, items, locations, mechanics, or specific categories.
    """
    gv = VectorManager()
    vecteur_query = gv.embeddings_model.embed_query(query)
    resultats = gv.search_similar(vecteur_query, k=3)

    contexte = "\n\n".join([f"Extrait : {res[0]}" for res in resultats])
    return contexte