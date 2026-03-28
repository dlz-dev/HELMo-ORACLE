import os
from typing import List, Tuple, Dict, Any

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter


def process_pdf_file(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[
    Tuple[str, Dict[str, Any]]]:
    """
    Loads a PDF file, extracts the text, and chunks it into segments.
    
    Args:
        file_path (str): The absolute or relative path to the PDF file.
        chunk_size (int): The maximum chunk size (in tokens/characters depending on the splitter).
        chunk_overlap (int): The number of overlapping elements between two chunks.
        
    Returns:
        List[Tuple[str, Dict[str, Any]]]: A list of tuples containing the text and its metadata based on the pages.
    """
    reader = SimpleDirectoryReader(input_files=[file_path])
    documents = reader.load_data()

    file_name = os.path.basename(file_path)

    for doc in documents:
        doc.metadata["source"] = file_name
        # Duplication of 'page_label' to 'page_number' for backward compatibility
        if "page_label" in doc.metadata:
            doc.metadata["page_number"] = doc.metadata["page_label"]

    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents(documents)

    return [(node.get_content(), node.metadata) for node in nodes]
