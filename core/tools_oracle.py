from langchain_core.tools import tool

from core.vector_manager import VectorManager


@tool
def search_knowledge_base(query: str) -> str:
    """
    Searches the Oracle's complete database for any information.
    Uses hybrid search (semantic cosine + BM25 keywords) fused with
    Reciprocal Rank Fusion for maximum recall on both conceptual
    questions and exact term lookups (item names, codes, proper nouns).
    """
    vm = VectorManager()

    # Embed the query once — reused by both semantic and hybrid search
    query_vector = vm.embeddings_model.embed_query(query)

    # Hybrid search: semantic + BM25 + RRF fusion
    results = vm.search_hybrid(query=query, query_vector=query_vector)

    if not results:
        return "<archives_sacrees>\nAucun document trouvé pour cette requête.\n</archives_sacrees>"

    contexte_lignes = []
    for content, rrf_score, metadata in results:
        source = metadata.get("source", "Unknown archive")
        contexte_lignes.append(f"[Source: {source}]\nExcerpt: {content}")

    formatted_results = "\n\n".join(contexte_lignes)

    # XML wrapping — prevents prompt injection from retrieved content
    return f"<archives_sacrees>\n{formatted_results}\n</archives_sacrees>"
