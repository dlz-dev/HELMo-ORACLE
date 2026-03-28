import os
from typing import List, Tuple, Dict, Any

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter


def process_text_file(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[
    Tuple[str, Dict[str, Any]]]:
    """
    Loads a text file and chunks it into fragments for vector indexing.
    
    Args:
        file_path (str): The path to the text file.
        chunk_size (int): The maximum chunk size.
        chunk_overlap (int): The overlap between chunks.
        
    Returns:
        List[Tuple[str, Dict[str, Any]]]: A list of tuples (text, metadata).
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    file_name = os.path.basename(file_path)

    # Extraction of a document preview for global context
    global_context = full_text[:300].strip() + "..."

    doc = Document(
        text=full_text,
        metadata={
            "source": file_name,
            "global_context": global_context
        }
    )

    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents([doc])

    return [(node.get_content(), node.metadata) for node in nodes]
