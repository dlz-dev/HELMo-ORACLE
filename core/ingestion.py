import os

from converters import convert_csv, convert_markdown, convert_text
from core.vector_manager import VectorManager


def seed_database() -> None:
    """
    Scans the data directory, processes files based on their extension,
    and inserts the resulting chunks into the vector database.
    """
    # Define paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(current_dir, "..", "data", "files")

    print(f"Source folder detected: {os.path.abspath(input_folder)}")

    # Initialize the vector manager (connecting to Docker/Database)
    # We assume GestionnaireVecteurs is now VectorManager
    db_manager = VectorManager()
    print("Database connection successful. Starting ingestion...")

    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)
        extension = os.path.splitext(file_name)[1].lower()

        chunks_to_insert = []

        # Process based on file format
        if extension == '.csv':
            print(f"Processing CSV: {file_name}")
            data = convert_csv.load_csv_data(file_path)
            for row in data:
                # Convert dict row to a single descriptive string
                row_string = " ".join([f"{key}: {value}" for key, value in row.items()])
                chunks_to_insert.append(row_string)

        elif extension == '.md':
            print(f"Processing Markdown: {file_name}")
            data = convert_markdown.parse_markdown(file_path)
            for item in data:
                chunks_to_insert.append(item['content'])

        elif extension == '.txt':
            print(f"Processing Text: {file_name}")
            documents = convert_text.process_text_file(file_path)
            for doc in documents:
                chunks_to_insert.append(doc.page_content)

        # Insertion into the Vector Database
        if chunks_to_insert:
            print(f"Inserting {len(chunks_to_insert)} chunks into the database...")
            for chunk in chunks_to_insert:
                db_manager.add_document(chunk)
            print(f"Finished processing: {file_name}")

    if __name__ == "__main__":
        seed_database()
