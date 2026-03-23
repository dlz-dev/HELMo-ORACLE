"""
HELMo Oracle — Serveur MCP (Model Context Protocol)

Expose le pipeline RAG comme un serveur MCP standard monté dans FastAPI.
Accessible via : https://api.dlzteam.com/mcp

Outils exposés :
  - search_knowledge_base : recherche hybride (cosine + BM25 + RRF)
  - list_sources           : liste les sources ingérées dans la base
"""

from mcp.server.fastmcp import FastMCP

from core.agent.tools_oracle import CONFIDENCE_THRESHOLD_HIGH, CONFIDENCE_THRESHOLD_MEDIUM

# ── Instance MCP ───────────────────────────────────────────────────────────────
mcp = FastMCP(
    "helmo-oracle",
    instructions=(
        "Tu es connecté aux Archives Sacrées de HELMo Oracle. "
        "Utilise search_knowledge_base pour interroger la base de connaissances Dofus, "
        "et list_sources pour voir les documents disponibles."
    ),
)

# Référence partagée vers le VectorManager (injectée par api.py au démarrage)
_vm = None


def setup(vm) -> None:
    """Injecte le VectorManager partagé depuis api.py."""
    global _vm
    _vm = vm


# ── Outil 1 : Recherche hybride ────────────────────────────────────────────────
@mcp.tool()
def search_knowledge_base(query: str, k: int = 5) -> str:
    """
    Recherche dans les archives de HELMo Oracle.

    Utilise une recherche hybride (similarité cosine + BM25 keyword search)
    fusionnée par Reciprocal Rank Fusion (RRF) pour un rappel maximal.

    Args:
        query : La question ou les mots-clés à rechercher.
        k     : Nombre de résultats à retourner (défaut: 5).

    Returns:
        Les extraits les plus pertinents avec leur source et niveau de confiance.
    """
    if _vm is None:
        return "Erreur : VectorManager non initialisé."

    query = query.strip()[:500]
    if not query:
        return "Requête vide."

    query_vector = _vm.embeddings_model.get_query_embedding(query)
    results = _vm.search_hybrid(query=query, query_vector=query_vector, k_final=k)

    if not results:
        return "Aucun document trouvé pour cette requête."

    lines = []
    for content, rrf_score, metadata in results:
        source = metadata.get("source", "Source inconnue")
        if rrf_score >= CONFIDENCE_THRESHOLD_HIGH:
            confidence = "🟢 HIGH"
        elif rrf_score >= CONFIDENCE_THRESHOLD_MEDIUM:
            confidence = "🟡 MEDIUM"
        else:
            confidence = "🔴 LOW"

        lines.append(
            f"[Source: {source}] [{confidence}] [Score RRF: {round(rrf_score, 4)}]\n{content}"
        )

    return "\n\n---\n\n".join(lines)


# ── Outil 2 : Liste des sources ────────────────────────────────────────────────
@mcp.tool()
def list_sources() -> str:
    """
    Liste tous les documents ingérés dans la base de connaissances.

    Returns:
        La liste des sources disponibles avec leur nombre de chunks et date d'ingestion.
    """
    if _vm is None:
        return "Erreur : VectorManager non initialisé."

    sources = _vm.list_sources()
    if not sources:
        return "Aucune source disponible dans la base."

    lines = [f"📚 {len(sources)} source(s) disponible(s) :\n"]
    for s in sources:
        lines.append(
            f"• {s['source']} — {s['chunk_count']} chunks — ingéré le {s['ingested_at']}"
        )

    return "\n".join(lines)


# ── Lancement standalone (test local) ─────────────────────────────────────────
if __name__ == "__main__":
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from core.database.vector_manager import VectorManager

    _embeddings = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-base")
    setup(VectorManager(embeddings_model=_embeddings))
    mcp.run()
