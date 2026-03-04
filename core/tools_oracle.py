"""
LangGraph tool used by the Oracle agent to search the knowledge base.

The VectorManager is NOT instantiated here — it is injected via
get_search_tool() from app.py, which passes the shared @st.cache_resource
singleton. This prevents duplicate PyTorch embedding model loading which
causes: "Cannot copy out of meta tensor; no data!"
"""

from langchain_core.tools import tool

from core.vector_manager import VectorManager


def get_search_tool(vm: VectorManager):
    """
    Factory that returns a LangGraph-compatible search tool bound to
    the shared VectorManager singleton from app.py.

    Usage in app.py:
        search_tool = get_search_tool(vm)
        agent = create_react_agent(llm, [search_tool], prompt=...)
    """

    @tool
    def search_knowledge_base(query: str) -> str:
        """
        Searches the Oracle's complete database for any information.
        Uses hybrid search (semantic cosine + BM25 keywords) fused with
        Reciprocal Rank Fusion for maximum recall on both conceptual
        questions and exact term lookups (item names, codes, proper nouns).
        """
        # Embed using the shared model — no new PyTorch instance created
        query_vector = vm.embeddings_model.embed_query(query)

        results = vm.search_hybrid(query=query, query_vector=query_vector)

        if not results:
            return "<archives_sacrees>\nAucun document trouvé pour cette requête.\n</archives_sacrees>"

        contexte_lignes = []
        for content, rrf_score, metadata in results:
            source = metadata.get("source", "Unknown archive")
            contexte_lignes.append(f"[Source: {source}]\nExcerpt: {content}")

        formatted_results = "\n\n".join(contexte_lignes)

        return f"<archives_sacrees>\n{formatted_results}\n</archives_sacrees>"

    return search_knowledge_base
