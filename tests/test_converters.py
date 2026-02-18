import unittest
import tempfile
import os
from langchain_core.documents import Document
from unittest.mock import patch, mock_open
from converters.convert_csv import load_csv_data
from converters.convert_markdown import parse_markdown
from converters.convert_text import process_text_file


class TestLoadCsvData(unittest.TestCase):

    def test_load_csv_nominal(self):
        """Test le cas normal : un fichier CSV valide."""
        csv_content = "name,age\nAlice,30\nBob,25"

        # On simule l'ouverture du fichier avec le contenu ci-dessus
        with patch("builtins.open", mock_open(read_data=csv_content)):
            result = load_csv_data("dummy_path.csv")

        expected = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"}
        ]
        self.assertEqual(result, expected)

    def test_load_csv_empty(self):
        """Test avec un fichier vide."""
        with patch("builtins.open", mock_open(read_data="")):
            result = load_csv_data("empty.csv")

        self.assertEqual(result, [])

    def test_file_not_found(self):
        """Test si le fichier n'existe pas (doit lever FileNotFoundError)."""
        # On fait en sorte que open lève une erreur
        with patch("builtins.open", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                load_csv_data("non_existent.csv")

    def test_load_csv_headers_only(self):
        """Test un fichier qui n'a que des en-têtes mais pas de données."""
        csv_content = "col1,col2"
        with patch("builtins.open", mock_open(read_data=csv_content)):
            result = load_csv_data("headers_only.csv")

        self.assertEqual(result, [])


class TestParseMarkdown(unittest.TestCase):

    def test_nominal_parsing(self):
        """Test un scénario standard avec différents types."""
        md_content = "# Header\n\nParagraph text.\n- List item"

        with patch("builtins.open", mock_open(read_data=md_content)):
            result = parse_markdown("dummy.md")

        self.assertEqual(len(result), 3)

        # Test Header
        self.assertEqual(result[0]['type'], 'heading')
        self.assertEqual(result[0]['line_number'], 1)

        # Test Paragraph (Notez que la ligne vide est sautée, donc ligne 3)
        self.assertEqual(result[1]['type'], 'paragraph')
        self.assertEqual(result[1]['line_number'], 3)

        # Test List
        self.assertEqual(result[2]['type'], 'list_item')

    def test_strip_behavior(self):
        """Vérifie que les espaces inutiles sont retirés."""
        md_content = "   # Indented Header   "

        with patch("builtins.open", mock_open(read_data=md_content)):
            result = parse_markdown("dummy.md")

        self.assertEqual(result[0]['content'], "# Indented Header")
        self.assertEqual(result[0]['type'], 'heading')

    def test_empty_lines_logic(self):
        """Vérifie que les lignes vides ou avec espaces seuls sont ignorées."""
        md_content = "Line 1\n\n   \nLine 4"

        with patch("builtins.open", mock_open(read_data=md_content)):
            result = parse_markdown("dummy.md")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['line_number'], 1)
        self.assertEqual(result[1]['line_number'], 4)

    class TestProcessTextFile(unittest.TestCase):

        def setUp(self):
            """
            Create a temporary text file for testing.
            """
            self.test_content = (
                "This is a test document.\n\n"
                "It contains multiple paragraphs.\n\n"
                "We want to split it into chunks for vector indexing."
            )

            self.temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                delete=False,
                encoding="utf-8",
                suffix=".txt"
            )
            self.temp_file.write(self.test_content)
            self.temp_file.close()

        def tearDown(self):
            """
            Remove temporary file after tests.
            """
            os.remove(self.temp_file.name)

        def test_returns_list_of_documents(self):
            chunks = process_text_file(self.temp_file.name)

            self.assertIsInstance(chunks, list)
            self.assertTrue(all(isinstance(chunk, Document) for chunk in chunks))

        def test_chunking_occurs(self):
            chunks = process_text_file(
                self.temp_file.name,
                chunk_size=30,
                chunk_overlap=0
            )

            # Should produce more than one chunk
            self.assertGreater(len(chunks), 1)

        def test_chunk_size_respected(self):
            chunk_size = 40
            chunks = process_text_file(
                self.temp_file.name,
                chunk_size=chunk_size,
                chunk_overlap=0
            )

            for chunk in chunks:
                self.assertLessEqual(len(chunk.page_content), chunk_size)

        def test_chunk_overlap(self):
            chunk_size = 50
            chunk_overlap = 10

            chunks = process_text_file(
                self.temp_file.name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            if len(chunks) > 1:
                first_chunk = chunks[0].page_content
                second_chunk = chunks[1].page_content

                # Vérifie que la fin du premier chunk correspond
                # au début du second chunk (overlap)
                self.assertEqual(
                    first_chunk[-chunk_overlap:],
                    second_chunk[:chunk_overlap]
                )

        def test_metadata_contains_source(self):
            chunks = process_text_file(self.temp_file.name)

            for chunk in chunks:
                self.assertIn("source", chunk.metadata)
                self.assertEqual(chunk.metadata["source"], self.temp_file.name)


if __name__ == '__main__':
    unittest.main()
