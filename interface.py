import streamlit as st
from core.gestionnaire_vecteurs import GestionnaireVecteurs

# Configuration de la page
st.set_page_config(page_title="L'Oracle de Solara", page_icon="🔮")

st.title("L'Oracle")
st.markdown("Pose une question à tes documents stockés dans la base vectorielle.")


# Initialisation du gestionnaire (on le met en cache pour éviter de recharger le modèle à chaque clic)
@st.cache_resource
def get_gestionnaire():
    return GestionnaireVecteurs()


oracle = get_gestionnaire()

# Zone de saisie
question = st.text_input("Ta question :", placeholder="Que dit le document sur...")

if st.button("Interroger l'Oracle"):
    if question:
        with st.spinner("L'Oracle réfléchit..."):
            # 1. On transforme la question en vecteur
            vecteur_question = oracle.embeddings_model.embed_query(question)

            # 2. On cherche dans la DB (on prend les 3 meilleurs résultats)
            resultats = oracle.rechercher_similaires(vecteur_question, k=3)

            if resultats:
                st.subheader("Résultats les plus pertinents :")
                for i, (contenu, distance) in enumerate(resultats):
                    with st.expander(f"Source {i + 1} (Score de proximité : {round(float(distance), 4)})"):
                        st.write(contenu)
            else:
                st.warning("L'Oracle n'a rien trouvé dans la base.")
    else:
        st.error("Écris quelque chose avant de cliquer !")