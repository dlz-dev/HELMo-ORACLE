"""
LangGraph tool — searches the knowledge base and exposes raw results
with RRF confidence scores for Chain-of-Thought display in the UI.

Results are stored in st.session_state["_cot_results"] so they survive
Streamlit's execution model without relying on a mutable Python global.
"""

from langchain_core.tools import tool
import streamlit as st

from core.database.vector_manager import VectorManager

# RRF score thresholds for confidence classification
# These are empirical values for the paraphrase-multilingual-MiniLM-L12-v2 model
_CONF_HIGH   = 0.025   # both semantic + BM25 agree
_CONF_MEDIUM = 0.010   # one method found it strongly


def get_search_tool(vm: VectorManager, k_final: int = 5):
    """
    Factory returning a LangGraph tool bound to the shared VectorManager.
    Stores raw results in st.session_state["_cot_results"] for CoT display.

    Args:
        vm:      Shared VectorManager singleton from app.py
        k_final: Number of results to retrieve (from sidebar K slider)
    """

    @tool
    def search_knowledge_base(query: str) -> str:
        """
        Searches the Oracle's complete database for any information.
        Uses hybrid search (semantic cosine + BM25 keywords) fused with
        Reciprocal Rank Fusion for maximum recall on both conceptual
        questions and exact term lookups (item names, codes, proper nouns).
        """
        st.session_state["_cot_results"] = []

        query_vector = vm.embeddings_model.get_query_embedding(query)
        results = vm.search_hybrid(query=query, query_vector=query_vector, k_final=k_final)

        if not results:
            return "<archives_sacrees>\nAucun document trouvé pour cette requête.\n</archives_sacrees>"

        cot_entries = []
        contexte_lignes = []

        for content, rrf_score, metadata in results:
            source = metadata.get("source", "Archive inconnue")

            if rrf_score >= _CONF_HIGH:
                confidence = "high"
            elif rrf_score >= _CONF_MEDIUM:
                confidence = "medium"
            else:
                confidence = "low"

            cot_entries.append({
                "source":     source,
                "content":    content,
                "rrf_score":  round(rrf_score, 4),
                "confidence": confidence,
            })
            contexte_lignes.append(f"[Source: {source}]\nExcerpt: {content}")

        st.session_state["_cot_results"] = cot_entries

        return f"<archives_sacrees>\n{chr(10).join(contexte_lignes)}\n</archives_sacrees>"

    return search_knowledge_base