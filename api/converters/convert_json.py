import json
import os
from typing import List, Tuple, Dict, Any

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter


def parse_json(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Reads a JSON file, extracts logical objects, and chunks them.
    
    Args:
        file_path (str): The path to the JSON file.
        chunk_size (int): The maximum chunk size.
        chunk_overlap (int): The overlap between chunks.
        
    Returns:
        List[Tuple[str, Dict[str, Any]]]: A list of tuples (text, metadata).
    """
    file_name = os.path.basename(file_path)
    documents = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"WARNING: Invalid or badly encoded JSON file ignored ({file_name}): {e}")
        return []
    except Exception as e:
        print(f"ERROR: Unexpected error while reading {file_name}: {e}")
        return []

    def _extract_item_name(item_dict: Dict[str, Any]) -> str:
        """Helper to find a relevant entity name for metadata."""
        return str(item_dict.get("name") or item_dict.get("nom") or item_dict.get("id") or "")

    # Case 1: The JSON is a dictionary at the root
    if isinstance(data, dict):
        for parent_key, parent_value in data.items():
            if isinstance(parent_value, list):
                for item in parent_value:
                    metadata: Dict[str, Any] = {"source": file_name, "category": parent_key}
                    if isinstance(item, dict) and (name := _extract_item_name(item)):
                        metadata["item_name"] = name
                    documents.append(Document(text=json.dumps(item, ensure_ascii=False), metadata=metadata))

            elif isinstance(parent_value, dict):
                metadata = {"source": file_name, "category": parent_key}
                documents.append(Document(text=json.dumps(parent_value, ensure_ascii=False), metadata=metadata))

            else:
                metadata = {"source": file_name, "category": parent_key}
                documents.append(Document(text=str(parent_value), metadata=metadata))

    # Case 2: The JSON is a list at the root
    elif isinstance(data, list):
        for item in data:
            metadata = {"source": file_name}
            if isinstance(item, dict) and (name := _extract_item_name(item)):
                metadata["item_name"] = name
            documents.append(Document(text=json.dumps(item, ensure_ascii=False), metadata=metadata))

    # Case 3: Base type (rare at the root, but possible)
    else:
        documents.append(Document(text=str(data), metadata={"source": file_name}))

    if not documents:
        return []

    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents(documents)

    return [(node.get_content(), node.metadata) for node in nodes]
