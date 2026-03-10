import os
from typing import List, Tuple

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter


def process_pdf_file(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, dict]]:
    """
    Charge un fichier PDF, extrait le texte et le découpe en segments avec LlamaIndex.
    Les numéros de page sont automatiquement ajoutés aux métadonnées.
    """
    # 1. Chargement du PDF via le lecteur standard de LlamaIndex
    reader = SimpleDirectoryReader(input_files=[file_path])
    documents = reader.load_data()

    nom_fichier = os.path.basename(file_path)
    for doc in documents:
        doc.metadata["source"] = nom_fichier

        # Le SimpleDirectoryReader de LlamaIndex crée une clé 'page_label',
        # on la duplique en 'page_number' pour garder la compatibilité avec ton existant.
        if "page_label" in doc.metadata:
            doc.metadata["page_number"] = doc.metadata["page_label"]

    # 2. Découpage en fragments (Nodes)
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents(documents)

    return [(node.get_content(), node.metadata) for node in nodes]