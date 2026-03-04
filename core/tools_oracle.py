from langchain_core.tools import tool
from core.vector_manager import VectorManager


@tool
def search_knowledge_base(query: str) -> str:
    """
    Searches the Oracle's complete database for any information.
    """
    gv = VectorManager()
    vecteur_query = gv.embeddings_model.embed_query(query)

    resultats = gv.search_similar(vecteur_query, k=5)

    contexte_lignes = []
    for res in resultats:
        contenu = res[0]
        metadata = res[2]
        source = metadata.get('source', 'Unknown archive')
        contexte_lignes.append(f"[Source: {source}]\nExcerpt: {contenu}")

    formatted_results = "\n\n".join(contexte_lignes)

    # We wrap the result in XML tags so that the AI reads it carefully (code injection)
    return f"<archives_sacrees>\n{formatted_results}\n</archives_sacrees>"
