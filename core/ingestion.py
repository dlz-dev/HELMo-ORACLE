import os

from converters import convert_csv, convert_markdown, convert_text, convert_json  # Adds convert_json
from core.vector_manager import VectorManager


def seed_database() -> None:
    """
    Browse the source files, cut them into fragments and insert them into the vector database with their metadata.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(current_dir, "..", "data", "files")

    db_manager = VectorManager()

    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)
        extension = os.path.splitext(file_name)[1].lower()

        chunks_to_insert = []

        base_metadata = {"source": file_name}

        if extension == '.csv':
            data = convert_csv.load_csv_data(file_path)
            for row in data:
                row_string = " ".join([f"{key}: {value}" for key, value in row.items()])
                chunks_to_insert.append((row_string, base_metadata))

        elif extension == '.md':
            documents = convert_markdown.parse_markdown(file_path)
            for doc in documents:
                chunks_to_insert.append((doc.page_content, doc.metadata))

        elif extension == '.txt':
            documents = convert_text.process_text_file(file_path)
            for doc in documents:
                chunks_to_insert.append((doc.page_content, base_metadata))

        elif extension == '.json':
            print(f"Processing JSON: {file_name}")
            data_chunks = convert_json.parse_json(file_path)
            for chunk in data_chunks:
                chunks_to_insert.append((chunk, base_metadata))

        # Insertion into the database
        if chunks_to_insert:
            print(f"Inserting {len(chunks_to_insert)} chunks from {file_name}...")
            for text_chunk, metadata_chunk in chunks_to_insert:
                db_manager.add_document(text_chunk, metadata=metadata_chunk)
            print(f"Finished processing: {file_name}")


if __name__ == "__main__":
    seed_database()

# TRUNCATE TABLE documents RESTART IDENTITY;
