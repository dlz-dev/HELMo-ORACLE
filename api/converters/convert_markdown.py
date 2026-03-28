import os
from typing import List, Tuple, Dict, Any

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter


def parse_markdown(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Reads a Markdown file, extracts its hierarchy, and chunks the content.
    Headers (H1, H2, etc.) are automatically transformed into metadata.
    
    Args:
        file_path (str): The path to the Markdown file.
        chunk_size (int): The maximum chunk size.
        chunk_overlap (int): The overlap between chunks.
        
    Returns:
        List[Tuple[str, Dict[str, Any]]]: A list of tuples (text, metadata).
    """
    with open(file_path, "r", encoding="utf-8", errors="strict") as f:
        md_text = f.read()

    file_name = os.path.basename(file_path)
    doc = Document(text=md_text, metadata={"source": file_name})

    # MarkdownNodeParser is excellent because it attaches parent headers
    # to subsections in the metadata (e.g., 'Header_1': 'Main Title')
    md_parser = MarkdownNodeParser()
    nodes_with_headers = md_parser.get_nodes_from_documents([doc])

    # Re-chunking to respect the fixed context window
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    final_nodes = text_splitter.get_nodes_from_documents(nodes_with_headers)

    return [(node.get_content(), node.metadata) for node in final_nodes]
