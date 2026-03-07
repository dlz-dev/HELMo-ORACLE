import os
import re

import streamlit as st
import yaml
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.prebuilt import create_react_agent

from core.agent.tools_oracle import get_search_tool
from core.context.memory_manager import MemoryManager
from core.context.session_manager import SessionManager, _is_cloud
from core.database.vector_manager import VectorManager
from core.pipeline.pii_manager import PIIManager
from providers import get_llm, get_available_models, PROVIDER_LABELS
from providers.error_handler import handle_llm_error, OracleError


# ─────────────────────────────────────────────────────────────────
# Response formatter
# ─────────────────────────────────────────────────────────────────
def _format_response(text: str) -> str:
    # Supprime les balises "Analyse:" ou "Analysis:" si l'IA les met quand même
    text = re.sub(r"^(Analyse|Analysis|Context)\s*:?", "", text, flags=re.IGNORECASE | re.MULTILINE)

    # Nettoie les espaces inutiles
    text = text.strip()

    # Évite les accumulations de sauts de ligne (max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


# ─────────────────────────────────────────────────────────────────
# Config & Prompt
# ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")
PROMPT_PATH = os.path.join(BASE_DIR, "config", "prompt.txt")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
else:
    config = st.secrets

if os.path.exists(PROMPT_PATH):
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        BASE_SYSTEM_PROMPT = f.read()
else:
    BASE_SYSTEM_PROMPT = st.secrets["prompts"]["system_prompt"]

# ─────────────────────────────────────────────────────────────────
# Page setup
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="HELMo's Oracle", page_icon="🔮", layout="wide")


# ─────────────────────────────────────────────────────────────────
# Singletons (@st.cache_resource)
# ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_embeddings_model() -> HuggingFaceEmbeddings:
    """Single PyTorch instance — prevents 'Cannot copy out of meta tensor' crash."""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )


@st.cache_resource
def get_vector_manager() -> VectorManager:
    return VectorManager(embeddings_model=get_embeddings_model())


@st.cache_resource
def get_session_manager() -> SessionManager:
    return SessionManager()


@st.cache_resource
def get_memory_manager() -> MemoryManager:
    max_tokens = config.get("memory", {}).get("max_recent_tokens", 1200)
    min_recent = config.get("memory", {}).get("min_recent_messages", 4)
    return MemoryManager(max_recent_tokens=max_tokens, min_recent_messages=min_recent)


sm = get_session_manager()
mm = get_memory_manager()
vm = get_vector_manager()
pii = PIIManager()  # Singleton — modèle spaCy chargé une seule fois


# ─────────────────────────────────────────────────────────────────
# Error display
# ─────────────────────────────────────────────────────────────────
def display_error(err: OracleError) -> None:
    st.error(f"**{err.icon} {err.title}**\n\n{err.message}\n\n💡 **What to do:** {err.suggestion}")
    with st.expander("🔧 Technical details"):
        st.code(
            f"Error type : {err.error_type.value}\n"
            f"Provider   : {err.provider}\n"
            f"Model      : {err.model}\n"
            f"Detail     : {err.technical_msg}",
            language="text",
        )


# ─────────────────────────────────────────────────────────────────
# Chain-of-Thought expander
# ─────────────────────────────────────────────────────────────────
def _render_cot(cot_results: list[dict]) -> None:
    if not cot_results:
        return

    icons = {"high": "🟢", "medium": "🟡", "low": "🔴"}
    labels = {"high": "forte", "medium": "modérée", "low": "faible"}
    all_low = all(r["confidence"] == "low" for r in cot_results)

    with st.expander(f"🔍 Archives consultées ({len(cot_results)} sources)", expanded=False):
        if all_low:
            st.warning(
                "⚠️ Les archives sont peu précises sur ce sujet. "
                "Voici ce qui s'en rapproche le plus — fiabilité limitée."
            )
        for i, r in enumerate(cot_results):
            icon = icons[r["confidence"]]
            label = labels[r["confidence"]]
            preview = r["content"][:240].replace("\n", " ")
            if len(r["content"]) > 240:
                preview += "…"
            st.markdown(f"**{icon} `{r['source']}`** — correspondance {label} · score `{r['rrf_score']}`")
            st.caption(f"> {preview}")
            if i < len(cot_results) - 1:
                st.divider()


# ─────────────────────────────────────────────────────────────────
# VIEW: Archives Dashboard
# ─────────────────────────────────────────────────────────────────
def view_archives():
    st.title("🗄️ Archives Sacrées")
    st.markdown("Explorez les documents et connaissances ingérés dans la mémoire de l'Oracle.")

    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Actualiser la base", use_container_width=True):
            st.session_state.pop("_db_sources", None)
            st.rerun()

    # Chargement des sources
    if "_db_sources" not in st.session_state:
        with st.spinner("Lecture des parchemins..."):
            st.session_state["_db_sources"] = vm.list_sources()

    db_sources: list[dict] = st.session_state.get("_db_sources", [])

    if not db_sources:
        st.info("La bibliothèque est vide.", icon="🕸️")
        return

    # Metrics
    total_files = len(db_sources)
    total_chunks = sum(s["chunk_count"] for s in db_sources)

    m1, m2, m3 = st.columns(3)
    m1.metric("📜 Fichiers", total_files)
    m2.metric("🧩 Fragments (Chunks)", total_chunks)
    m3.metric("🧠 Base Vectorielle", "Active")

    st.divider()

    # Affichage des fichiers sous forme de tableau interactif ou cartes
    # On trie par date d'ingestion (plus récent en haut si dispo, sinon alphabétique)
    sorted_sources = sorted(db_sources, key=lambda x: x.get('source', ''))

    for src in sorted_sources:
        with st.expander(f"📄 **{src['source']}** ({src['chunk_count']} chunks)"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown("**Contexte Global (généré par IA) :**")
                st.info(src.get("global_context", "Aucun contexte disponible."), icon="📝")
            with c2:
                st.caption("🕒 Ingéré le :")
                st.text(src.get("ingested_at", "?"))

                # Simulation d'un aperçu des métadonnées brutes
                with st.popover("Données brutes"):
                    st.json(src)


# ─────────────────────────────────────────────────────────────────
# VIEW: Chat Oracle
# ─────────────────────────────────────────────────────────────────
def view_chat(selected_provider, selected_model, temperature, k_final):
    st.title("🔮 The Sacred Oracle")

    # Session Init
    if "current_session" not in st.session_state:
        st.session_state.current_session = sm.new_session(
            provider=selected_provider, model=selected_model,
        )
    session = st.session_state.current_session

    if session.get("title") and session["title"] != "New conversation":
        st.caption(f"📖 **{session['title']}**")

    # ── Starter prompts ───────────────────────────────────────────
    if not session.get("messages"):
        st.info(
            "**L'Oracle répond uniquement depuis ses archives Dofus.** "
            "Soyez précis : classe, niveau, objectif.\n\n"
            "Exemple : *« Je joue Iop niveau 120, quel équipement viser pour le donjon Tal Kasha ? »*",
            icon="💡",
        )

        STARTERS = [
            ("🗺️ Débuter", "Je suis tout nouveau sur Dofus. Par où commencer et quelle classe choisir ?"),
            ("⚔️ Combat", "Explique-moi les mécaniques de combat : PA, PM, portée, défis de combat."),
            ("🏰 Donjons", "Comment fonctionne un donjon ? Comment se préparer et quoi apporter ?"),
            ("💰 Kamas", "Quelles sont les meilleures façons de gagner des kamas quand on débute ?"),
            ("🌍 Histoire", "Raconte-moi le lore de Dofus : Ogrest, le Monde des Douze, les Dofus primaires."),
            ("🎭 Classe", "Quelles sont toutes les classes disponibles et leurs rôles en groupe ?"),
        ]

        cols = st.columns(3)
        for i, (label, question) in enumerate(STARTERS):
            with cols[i % 3]:
                if st.button(label, use_container_width=True, key=f"start_{i}"):
                    st.session_state["_inject_prompt"] = question
                    st.rerun()

    # Inject starter prompt
    if "_inject_prompt" in st.session_state:
        injected = st.session_state.pop("_inject_prompt")
        session["messages"].append({"role": "user", "content": injected})
        sm.save(session)
        st.session_state.current_session = session

    # ── Render History ────────────────────────────────────────────
    for msg in session.get("messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("_cot"):
                _render_cot(msg["_cot"])

    # ── Input & Agent Logic ───────────────────────────────────────
    prompt = st.chat_input("Posez votre question aux archives sacrées…")

    # Initialize Agent
    try:
        @st.cache_resource(hash_funcs={dict: lambda d: str(sorted(d.items()))})
        def load_llm(provider_key: str, model: str, temp: float, _config: dict):
            return get_llm(
                provider_key=provider_key,
                model=model,
                config={**_config, "llm": {**_config.get("llm", {}), "temperature": temp}},
            )

        llm = load_llm(selected_provider, selected_model, temperature, config)
        enriched_prompt, history = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)
        search_tool = get_search_tool(vm, k_final=k_final)
        agent = create_react_agent(llm, [search_tool], prompt=enriched_prompt)

    except Exception as e:
        st.error(f"Erreur d'initialisation de l'agent : {e}")
        return

    # Check for pending processing
    messages = session.get("messages", [])
    has_pending = (
            messages and messages[-1]["role"] == "user"
            and (len(messages) == 1 or messages[-2]["role"] == "assistant"
                 or (len(messages) >= 2 and messages[-2]["role"] == "user"))
    )

    if prompt:
        # Masquer les PII avant stockage et envoi au LLM
        # L'utilisateur voit son message original ; le LLM reçoit la version masquée
        prompt_masked = pii.mask(prompt)
        session["messages"].append({"role": "user", "content": prompt_masked})
        with st.chat_message("user"):
            st.markdown(prompt)  # Affichage original (non masqué) pour l'UX
        sm.save(session)
        st.session_state.current_session = session
        has_pending = True

    if has_pending and session["messages"][-1]["role"] == "user":
        _, history = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)

        with st.chat_message("assistant"):
            try:
                with st.spinner("L'Oracle consulte les astres…"):
                    result = agent.invoke({"messages": history})
                    response = _format_response(result["messages"][-1].content)

                cot_results = st.session_state.get("_cot_results", [])
                _render_cot(cot_results)
                st.markdown(response)

                session["messages"].append({
                    "role": "assistant",
                    "content": response,
                    "_cot": cot_results,
                })

                if mm.needs_summarization(session["messages"], session.get("summary", "")):
                    with st.spinner("🧠 Consolidation de la mémoire…"):
                        session = mm.compress(session, llm)
                        st.session_state.current_session = session

                session["provider"] = selected_provider
                session["model"] = selected_model
                sm.save(session)
                st.session_state.current_session = session

            except Exception as e:
                oracle_error = handle_llm_error(e, provider=selected_provider, model=selected_model)
                display_error(oracle_error)


# ─────────────────────────────────────────────────────────────────
# Sidebar & Main Execution
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── User Info ────────────────────────────────────────────────
    if _is_cloud():
        try:
            user = st.experimental_user
            if user and user.email:
                st.caption(f"👤 **{user.name or user.email}**")
        except Exception:
            pass

    # ── Navigation ───────────────────────────────────────────────
    st.subheader("Navigation")
    page_selection = st.radio(
        "Mode",
        ["🔮 Oracle", "🗄️ Archives"],
        label_visibility="collapsed"
    )
    st.divider()

    # ── Contextual Sidebar Content ───────────────────────────────

    # > Settings (Only relevant for Chat)
    if page_selection == "🔮 Oracle":
        with st.popover("⚙️ Paramètres IA", use_container_width=True):
            st.markdown("**Modèle**")
            provider_options = list(PROVIDER_LABELS.keys())
            provider_display = list(PROVIDER_LABELS.values())
            default_provider = config.get("llm", {}).get("default_provider", "groq")
            default_provider_idx = (
                provider_options.index(default_provider)
                if default_provider in provider_options else 0
            )
            selected_provider_label = st.selectbox(
                "Provider", options=provider_display, index=default_provider_idx,
                label_visibility="collapsed",
            )
            selected_provider = provider_options[provider_display.index(selected_provider_label)]

            available_models = get_available_models(selected_provider, config)
            default_model = config.get("llm", {}).get("default_model", available_models[0])
            default_model_idx = (
                available_models.index(default_model) if default_model in available_models else 0
            )
            selected_model = st.selectbox(
                "Modèle", options=available_models, index=default_model_idx,
            )

            st.markdown("**Génération**")
            temperature = st.slider(
                "🌡️ Température", min_value=0.0, max_value=1.0,
                value=float(config.get("llm", {}).get("temperature", 0.0)), step=0.05,
            )

            st.markdown("**Recherche**")
            default_k = config.get("search", {}).get("k_final", 5)
            k_final = st.slider(
                "📚 Sources (K)", min_value=1, max_value=15,
                value=default_k, step=1,
            )

        st.divider()

        # > Sessions Management (Only relevant for Chat)
        st.subheader("💬 Sessions")
        col_new, col_del = st.columns(2)
        with col_new:
            if st.button("✨ Nouvelle", use_container_width=True):
                new_s = sm.new_session(provider=selected_provider, model=selected_model)
                st.session_state.current_session = new_s
                st.session_state.pop("_rename_sid", None)
                st.rerun()
        with col_del:
            if st.button("🗑️ Effacer", use_container_width=True):
                if "current_session" in st.session_state:
                    sm.delete(st.session_state.current_session["session_id"])
                    del st.session_state.current_session
                    st.session_state.pop("_rename_sid", None)
                    st.rerun()

        past_sessions = sm.list_sessions()
        if past_sessions:
            st.caption(f"📁 {len(past_sessions)} session(s)")
            for s in past_sessions:
                sid = s["session_id"]
                is_active = (
                        "current_session" in st.session_state
                        and st.session_state.current_session["session_id"] == sid
                )

                if st.session_state.get("_rename_sid") == sid:
                    new_title = st.text_input(
                        "Nouveau nom", value=s["title"],
                        key=f"ri_{sid}", label_visibility="collapsed",
                    )
                    ok, cancel = st.columns(2)
                    if ok.button("✅", key=f"rok_{sid}"):
                        loaded = sm.load(sid)
                        if loaded and new_title.strip():
                            loaded["title"] = new_title.strip()
                            sm.save(loaded)
                            if is_active: st.session_state.current_session = loaded
                        st.session_state.pop("_rename_sid")
                        st.rerun()
                    if cancel.button("❌", key=f"rno_{sid}"):
                        st.session_state.pop("_rename_sid")
                        st.rerun()
                else:
                    bt, edt = st.columns([5, 1])
                    prefix = "▶ " if is_active else ""
                    if bt.button(f"{prefix}{s['title'][:28]}", key=f"s_{sid}", use_container_width=True):
                        loaded = sm.load(sid)
                        if loaded:
                            st.session_state.current_session = loaded
                            st.rerun()
                    if edt.button("✏️", key=f"re_{sid}"):
                        st.session_state["_rename_sid"] = sid
                        st.rerun()
    else:
        # Defaults for Archives view (since we don't show the params)
        selected_provider = "groq"
        selected_model = "llama3-70b-8192"
        temperature = 0.0
        k_final = 5
        st.info("Mode exploration activé.\nLes sessions de chat sont masquées.")

# ─────────────────────────────────────────────────────────────────
# Routeur principal
# ─────────────────────────────────────────────────────────────────
if page_selection == "🔮 Oracle":
    view_chat(selected_provider, selected_model, temperature, k_final)
elif page_selection == "🗄️ Archives":
    view_archives()
