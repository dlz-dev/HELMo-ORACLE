import os
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def parse_markdown(file_path: str) -> List[Document]:
    """
    Lit un fichier Markdown, extrait la hiérarchie des titres (Phase 1)
    et découpe le contenu en chunks de taille raisonnable.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # 1. On définit quels titres on veut suivre
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    # 2. On découpe d'abord par structure (Les titres deviennent des métadonnées)
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(md_text)

    # 3. On redécoupe par taille pour éviter les chunks trop énormes (Ta préoccupation !)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    splits = text_splitter.split_documents(md_header_splits)

    nom_fichier = os.path.basename(file_path)
    for split in splits:
        split.metadata["source"] = nom_fichier

    return splits
