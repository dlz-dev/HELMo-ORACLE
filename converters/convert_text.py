import os
from typing import List, Tuple

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter


def process_text_file(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, dict]]:
    """
    Charge un fichier texte et le découpe en fragments pour l'indexation vectorielle.
    Extrait le début du document pour servir de contexte global.
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        full_text = f.read()

    nom_fichier = os.path.basename(file_path)

    # Extraction du contexte global (300 premiers caractères)
    global_context = full_text[:300].strip() + "..."

    # Création du Document LlamaIndex avec les métadonnées initiales
    doc = Document(text=full_text, metadata={
        "source": nom_fichier,
        "global_context": global_context
    })

    # Découpage avec le splitter optimisé
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents([doc])

    return [(node.get_content(), node.metadata) for node in nodes]