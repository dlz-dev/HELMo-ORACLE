from langchain_core.tools import tool
from core.vector_manager import VectorManager


@tool
def search_knowledge_base(query: str) -> str:
    """
    Searches for information in the Oracle's archives.
    Use this for any questions regarding legends, quests, or the survival guide.
    """
    gv = VectorManager()
    vecteur_query = gv.embeddings_model.embed_query(query)
    resultats = gv.search_similar(vecteur_query, k=3)

    contexte = "\n\n".join([f"Extrait : {res[0]}" for res in resultats])
    return contexte