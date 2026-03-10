import os
from typing import List, Tuple

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

def parse_markdown(file_path: str) -> List[Tuple[str, dict]]:
    """
    Lit un fichier Markdown, extrait la hiérarchie des titres (Phase 1),
    et découpe le contenu en fragments optimisés pour l'embedding LlamaIndex.
    """
    with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
        md_text = f.read()

    nom_fichier = os.path.basename(file_path)
    doc = Document(text=md_text, metadata={"source": nom_fichier})

    # 1. Découpage basé sur la structure (Les titres deviennent des métadonnées)
    md_parser = MarkdownNodeParser()
    nodes_with_headers = md_parser.get_nodes_from_documents([doc])

    # 2. Redécoupage par taille pour éviter les chunks trop lourds
    # 512 est idéal pour le modèle intfloat/multilingual-e5-base
    text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    final_nodes = text_splitter.get_nodes_from_documents(nodes_with_headers)

    return [(node.get_content(), node.metadata) for node in final_nodes]