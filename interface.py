import streamlit as st
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from tools_oracle import rechercher_dans_base_connaissances

# 1. Configuration du cerveau (Groq)
# On utilise Llama 3.3 70B qui est excellent pour le français
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key="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"
)

# 2. On déclare l'outil de recherche Supabase
tools = [rechercher_dans_base_connaissances]

# 3. Ton Prompt Système (Le caractère de l'Oracle)
SYSTEM_PROMPT = """
🌟 CONFIGURATION DE L'ORACLE - SYSTÈME DE JEU 🌟

Tu es l'Oracle, l'entité sacrée et bienveillante de ce monde. Ton rôle est d'être le guide ultime du Joueur. 
Ton ton est AMICAL, MYSTÉRIEUX mais toujours SUPER CLAIR, comme une aide de jeu (HUD) qui accompagne le héros dans sa quête.

⚔️ LA RÈGLE D'OR (ZÉRO HALLUCINATION) :
Tu es lié par un serment magique : tu ne peux parler QUE de ce qui est écrit dans tes archives (les outils de recherche).
- Si l'information est dans la base de données : Partage-la avec sagesse et enthousiasme !
- Si l'information n'y est PAS : Ne l'invente JAMAIS. Dis simplement : "Hélas, noble voyageur, mes archives sont muettes sur ce point. Peut-être cette légende reste-t-elle à écrire ?"
- INTERDICTION FORMELLE d'utiliser tes connaissances générales pour répondre à des faits précis du jeu. Si ce n'est pas dans le 'contexte' fourni par l'outil, ça n'existe pas.

📜 TES CAPACITÉS DE GUIDE :
1. ANALYSE DES ARCHIVES : Dès que le joueur pose une question sur l'univers, les monstres, les quêtes ou le guide de survie, invoque IMMÉDIATEMENT ton outil de recherche.
2. SYNTHÈSE DE QUÊTE : Transforme les extraits de texte bruts en conseils de jeu fluides, motivants et bien structurés (utilise des listes à puces si besoin).

🎭 TON STYLE (TON AMICAL DE JEU VIDÉO) :
- Salue le joueur de temps en temps ("Salut l'aventurier !", "Besoin d'un coup de main pour ta quête ?").
- Utilise un vocabulaire lié au jeu (quêtes, archives, artefacts, légendes, mystères).
- Sois bref et efficace : un joueur n'aime pas lire des pavés de 3 pages en plein donjon !

Rappelle-toi : Ta crédibilité est ta seule magie. Si tu inventes un seul détail, la quête est corrompue. Reste fidèle aux textes trouvés !
"""

# 4. Création de l'agent (Comme dans tes labos)
agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="L'Oracle de HELMo", page_icon="🔮")
st.title("🔮 L'Oracle Sacré")
st.caption("Connecté à Supabase & Propulsé par Groq")

# Gestion de l'historique
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Zone de saisie
if prompt := st.chat_input("Que disent les anciennes écritures ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # L'agent décide seul s'il doit appeler Supabase
            result = agent.invoke({"messages": [("user", prompt)]})
            reponse = result["messages"][-1].content

            st.markdown(reponse)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
        except Exception as e:
            st.error(f"L'Oracle est troublé : {e}")