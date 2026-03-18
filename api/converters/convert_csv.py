import csv
import json
import os
from typing import List, Tuple, Dict, Any

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

def load_csv_data(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Reads a CSV file, converts each row to JSON (text), and chunks it.
    
    Args:
        file_path (str): The path to the CSV file.
        chunk_size (int): The maximum chunk size.
        chunk_overlap (int): The overlap between chunks.
        
    Returns:
        List[Tuple[str, Dict[str, Any]]]: A list of tuples (text, metadata).
    """
    file_name = os.path.basename(file_path)
    documents = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as file:
            sample = file.read(1024)
            file.seek(0)
            
            # Automatic deduction of the delimiter (comma, semicolon, etc.)
            dialect = csv.Sniffer().sniff(sample)
            reader = csv.DictReader(file, dialect=dialect)
            
            for row in reader:
                item_name = row.get("name") or row.get("nom") or row.get("id")
                metadata: Dict[str, Any] = {"source": file_name}
                if item_name:
                    metadata["item_name"] = str(item_name)

                # Serialize the row so the LLM understands the key-value structure
                chunk_text = json.dumps(row, ensure_ascii=False)
                documents.append(Document(text=chunk_text, metadata=metadata))

    except csv.Error as e:
        print(f"WARNING: Unrecognized CSV format or empty file ignored ({file_name}): {e}")
        return []
    except UnicodeDecodeError as e:
        print(f"WARNING: UTF-8 encoding error for {file_name}: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Unexpected error while reading {file_name}: {e}")
        return []

    if not documents:
        return []
    
    # Chunking with LlamaIndex (secures rows containing very long texts)
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents(documents)

    return [(node.get_content(), node.metadata) for node in nodes]