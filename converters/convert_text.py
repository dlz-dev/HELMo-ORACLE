from typing import List

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def process_text_file(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """
    Loads a text file and splits it into smaller chunks for vector indexing.
    Extracts the beginning of the document to serve as global context.
    """
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    # Extracting global context (first 300 characters of the file)
    full_text = documents[0].page_content
    global_context = full_text[:300].strip() + "..."

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False
    )

    chunks = text_splitter.split_documents(documents)

    # Injecting the global context into the metadata of each chunk
    for chunk in chunks:
        chunk.metadata["global_context"] = global_context

    return chunks
