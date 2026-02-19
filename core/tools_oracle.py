from langchain_core.tools import tool

from core.vector_manager import VectorManager


@tool
def search_knowledge_base(query: str) -> str:
    """
    Searches the Oracle's complete database for any information.
    """
    gv = VectorManager()
    vecteur_query = gv.embeddings_model.embed_query(query)

    # resultats contient maintenant (content, distance, metadata)
    resultats = gv.search_similar(vecteur_query, k=3)

    # On formate le contexte pour que le LLM sache d'où vient l'information
    contexte_lignes = []
    for res in resultats:
        contenu = res[0]
        metadata = res[2]
        source = metadata.get('source', 'Archive inconnue')
        contexte_lignes.append(f"[Source: {source}]\nExtrait : {contenu}")

    return "\n\n".join(contexte_lignes)
