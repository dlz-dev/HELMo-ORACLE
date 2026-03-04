import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def process_pdf_file(file_path: str, chunk_size: int = 800, chunk_overlap: int = 80) -> List[Document]:
    """
    Charge un fichier PDF, extrait le texte et le découpe en segments.
    Ajoute le numéro de page et la source aux métadonnées.
    """
    # 1. Chargement du PDF (découpage automatique par page)
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    # 2. Configuration du splitter
    # Note : Le format PDF étant souvent plus dense, on peut augmenter légèrement le chunk_size
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    # 3. Découpage en documents
    chunks = text_splitter.split_documents(pages)

    # 4. Enrichissement des métadonnées
    nom_fichier = os.path.basename(file_path)
    for chunk in chunks:
        chunk.metadata["source"] = nom_fichier
        # 'page' est déjà inclus par PyPDFLoader, mais on peut s'assurer qu'il est explicite
        if "page" in chunk.metadata:
            chunk.metadata["page_number"] = chunk.metadata["page"] + 1

    return chunks