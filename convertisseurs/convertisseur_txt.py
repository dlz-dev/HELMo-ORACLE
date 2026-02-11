import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# OPENWEBUI_URL = "https://chat.ai-labs.helmo.be"
# API_KEY = "sk-a6a2056cf5b44080b8df36e6126914e1"
#
# os.environ["OPENAI_API_KEY"] = API_KEY
#
# llm = ChatOpenAI(
#     model="gpt-oss:120b",
#     base_url=f"{OPENWEBUI_URL}/api",
#     api_key=API_KEY,
#     temperature=0
# )


def transformer_txt(chemin_fichier):
    # Création modèle embeddings (petit modèle local)
    # embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Chargement
    loader = TextLoader(f"{chemin_fichier}", encoding="utf-8")
    docs = loader.load()

    # Découpage (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)

    return splits


# [Note pour Max] : J'ai supprimé la configuration de ChatOpenAI et Chroma d'ici
# parce que si on laisse la configuration ici, le modèle est rechargé à chaque
# fois qu'on importe ce fichier
# Maintenant, on appelle transformer_txt() et on donne le résultat au 'core'
# je pense que c'est juste mais, confirmez-moi ça



