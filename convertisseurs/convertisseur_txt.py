from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def transformer_txt(chemin_fichier):
    # Chargement
    loader = TextLoader(f"{chemin_fichier}", encoding="utf-8")
    docs = loader.load()

    # Découpage (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)

    return splits


