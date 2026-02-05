import os
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

OPENWEBUI_URL = "https://chat.ai-labs.helmo.be"
API_KEY = "sk-a6a2056cf5b44080b8df36e6126914e1"

os.environ["OPENAI_API_KEY"] = API_KEY

llm = ChatOpenAI(
    model="gpt-oss:120b",
    base_url=f"{OPENWEBUI_URL}/api",
    api_key=API_KEY,
    temperature=0
)


def transformer_txt(chemin_fichier):
    # Création modèle embeddings (petit modèle local)
    print("Chargement du modèle d'embedding...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Chargement
    loader = TextLoader(f"{chemin_fichier}", encoding="utf-8")
    docs = loader.load()

    # Découpage (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)

    # Stockage dans ChromaDB (Base locale)
    print("Création de la base vectorielle...")
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )


