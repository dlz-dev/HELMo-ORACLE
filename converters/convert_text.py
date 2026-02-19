from typing import List

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def process_text_file(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """
    Loads a text file and splits it into smaller chunks for vector indexing.
    """
    # Loading the document
    # TextLoader is robust for UTF-8 encoded text files
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    # Chunking (Splitting)
    # RecursiveCharacterTextSplitter is recommended for generic text as it
    # tries to keep paragraphs and sentences together.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False
    )

    chunks = text_splitter.split_documents(documents)

    return chunks
