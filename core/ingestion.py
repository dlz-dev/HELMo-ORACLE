import json
import os

from converters import convert_csv, convert_markdown, convert_text, convert_json
from core.vector_manager import VectorManager


def seed_database() -> None:
    """
    Browse the source files, cut them into fragments and insert them into the vector database with their metadata.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(current_dir, "..", "data", "files")

    print("Ingestion started")
    db_manager = VectorManager()

    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)
        extension = os.path.splitext(file_name)[1].lower()

        chunks_to_insert = []
        base_metadata = {"source": file_name}

        if extension == '.csv':
            data = convert_csv.load_csv_data(file_path)
            for row in data:
                json_string = json.dumps(row, ensure_ascii=False)
                chunks_to_insert.append((json_string, base_metadata))

        elif extension == '.md':
            documents = convert_markdown.parse_markdown(file_path)
            for doc in documents:
                chunks_to_insert.append((doc.page_content, doc.metadata))

        elif extension == '.txt':
            documents = convert_text.process_text_file(file_path)
            for doc in documents:
                chunks_to_insert.append((doc.page_content, base_metadata))

        elif extension == '.json':
            data_chunks = convert_json.parse_json(file_path)
            for text_chunk, specific_metadata in data_chunks:
                merged_metadata = base_metadata.copy()
                merged_metadata.update(specific_metadata)

                chunks_to_insert.append((text_chunk, merged_metadata))
        else:
            continue

        if chunks_to_insert:
            for text_chunk, metadata_chunk in chunks_to_insert:
                db_manager.add_document(text_chunk, metadata=metadata_chunk)

            # Un seul print propre et informatif par fichier
            print(f"✅ {file_name} treated : {len(chunks_to_insert)} chunks inserted.")

    print("Ingestion done !")


if __name__ == "__main__":
    seed_database()

# TRUNCATE TABLE documents RESTART IDENTITY;
