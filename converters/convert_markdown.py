import os
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def parse_markdown(file_path: str) -> List[Document]:
    """
    Reads a Markdown file, extracts the heading hierarchy (Phase 1),
    and splits the content into chunks of reasonable size.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # Define which headings to track
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    # Split first by structure (Headings become metadata)
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(md_text)

    # Split again by size to avoid excessively large chunks (Your concern!)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    splits = text_splitter.split_documents(md_header_splits)

    nom_fichier = os.path.basename(file_path)
    for split in splits:
        split.metadata["source"] = nom_fichier

    return splits