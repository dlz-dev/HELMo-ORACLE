import unittest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from core.ingestion import seed_database
from core.preprocess import QuestionProcessor
from core.vector_manager import VectorManager


class TestSeedDatabase(unittest.TestCase):

    @patch("core.ingestion.os.listdir")
    @patch("core.ingestion.VectorManager")
    @patch("core.ingestion.convert_text.process_text_file")
    @patch("core.ingestion.convert_markdown.parse_markdown")
    @patch("core.ingestion.convert_csv.load_csv_data")
    def test_csv_file_processing(
            self,
            mock_load_csv,
            mock_parse_md,
            mock_process_text,
            mock_vector_manager,
            mock_listdir
    ):
        # Setup
        mock_listdir.return_value = ["test.csv"]

        mock_load_csv.return_value = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        # Execute
        seed_database()

        # Assert
        self.assertEqual(mock_db_instance.add_document.call_count, 2)

        expected_calls = [
            unittest.mock.call("name: Alice age: 30"),
            unittest.mock.call("name: Bob age: 25"),
        ]

        mock_db_instance.add_document.assert_has_calls(expected_calls, any_order=False)

    @patch("core.ingestion.os.listdir")
    @patch("core.ingestion.VectorManager")
    @patch("core.ingestion.convert_text.process_text_file")
    @patch("core.ingestion.convert_markdown.parse_markdown")
    @patch("core.ingestion.convert_csv.load_csv_data")
    def test_markdown_file_processing(
            self,
            mock_load_csv,
            mock_parse_md,
            mock_process_text,
            mock_vector_manager,
            mock_listdir
    ):
        mock_listdir.return_value = ["doc.md"]

        mock_parse_md.return_value = [
            {"content": "Section 1"},
            {"content": "Section 2"},
        ]

        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        seed_database()

        self.assertEqual(mock_db_instance.add_document.call_count, 2)
        mock_db_instance.add_document.assert_any_call("Section 1")
        mock_db_instance.add_document.assert_any_call("Section 2")

    @patch("core.ingestion.os.listdir")
    @patch("core.ingestion.VectorManager")
    @patch("core.ingestion.convert_text.process_text_file")
    @patch("core.ingestion.convert_markdown.parse_markdown")
    @patch("core.ingestion.convert_csv.load_csv_data")
    def test_text_file_processing(
            self,
            mock_load_csv,
            mock_parse_md,
            mock_process_text,
            mock_vector_manager,
            mock_listdir
    ):
        mock_listdir.return_value = ["file.txt"]

        mock_process_text.return_value = [
            Document(page_content="Chunk 1"),
            Document(page_content="Chunk 2"),
        ]

        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        seed_database()

        self.assertEqual(mock_db_instance.add_document.call_count, 2)
        mock_db_instance.add_document.assert_any_call("Chunk 1")
        mock_db_instance.add_document.assert_any_call("Chunk 2")

    @patch("core.ingestion.os.listdir")
    @patch("core.ingestion.VectorManager")
    def test_unsupported_file_extension(self, mock_vector_manager, mock_listdir):
        mock_listdir.return_value = ["image.png"]

        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        seed_database()

        # Aucun document ne doit être inséré
        mock_db_instance.add_document.assert_not_called()

    @patch("core.ingestion.os.listdir")
    @patch("core.ingestion.VectorManager")
    @patch("core.ingestion.convert_csv.load_csv_data")
    def test_empty_csv_file(self, mock_load_csv, mock_vector_manager, mock_listdir):
        mock_listdir.return_value = ["empty.csv"]
        mock_load_csv.return_value = []

        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        seed_database()

        mock_db_instance.add_document.assert_not_called()


class TestQuestionProcessor(unittest.TestCase):

    @patch("core.preprocess.HuggingFaceEmbeddings")
    def setUp(self, mock_embeddings_class):
        """
        Mock the HuggingFace model so we don't load the real one.
        """
        self.mock_model = MagicMock()
        mock_embeddings_class.return_value = self.mock_model
        self.processor = QuestionProcessor()

    def test_preprocess_text_lowercase(self):
        text = "BONJOUR"
        result = self.processor.preprocess_text(text)
        self.assertEqual(result, "bonjour")

    def test_preprocess_text_remove_accents(self):
        text = "éàçôù"
        result = self.processor.preprocess_text(text)
        self.assertEqual(result, "eacou")

    def test_preprocess_text_remove_punctuation(self):
        text = "Bonjour, comment ça va ?!"
        result = self.processor.preprocess_text(text)
        self.assertEqual(result, "bonjour comment ca va")

    def test_preprocess_text_strip_whitespace(self):
        text = "   Bonjour   "
        result = self.processor.preprocess_text(text)
        self.assertEqual(result, "bonjour")

    def test_preprocess_text_combined(self):
        text = "  HéLLo, Ça Vâ !!! "
        result = self.processor.preprocess_text(text)
        self.assertEqual(result, "hello ca va")

    def test_vectorize_text_calls_model(self):
        fake_vector = [0.1] * 384
        self.mock_model.embed_query.return_value = fake_vector

        result = self.processor.vectorize_text("test")

        self.mock_model.embed_query.assert_called_once_with("test")
        self.assertEqual(result, fake_vector)

    def test_vectorize_text_returns_list_of_floats(self):
        fake_vector = [0.1, 0.2, 0.3]
        self.mock_model.embed_query.return_value = fake_vector

        result = self.processor.vectorize_text("hello")

        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(x, float) for x in result))


class TestVectorManager(unittest.TestCase):

    @patch("core.vector_manager.register_vector")
    @patch("core.vector_manager.psycopg.connect")
    @patch("core.vector_manager.HuggingFaceEmbeddings")
    def setUp(self, mock_embeddings_class, mock_connect, mock_register_vector):
        """
        Mock:
        - Database connection
        - Embedding model
        - pgvector registration
        """

        # Mock DB connection
        self.mock_conn = MagicMock()
        mock_connect.return_value = self.mock_conn

        # Mock cursor context manager
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor

        # Mock embedding model
        self.mock_model = MagicMock()
        mock_embeddings_class.return_value = self.mock_model

        self.vector_manager = VectorManager()

    def test_add_document_calls_embed_and_insert(self):
        fake_vector = [0.1] * 384
        self.mock_model.embed_query.return_value = fake_vector

        self.vector_manager.add_document("hello world")

        # Vérifie que l'embedding est généré
        self.mock_model.embed_query.assert_called_once_with("hello world")

        # Vérifie l'exécution SQL
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args

        self.assertIn("INSERT INTO documents", args[0])
        self.assertEqual(args[1], ("hello world", fake_vector))

        # Vérifie commit
        self.mock_conn.commit.assert_called_once()

    def test_search_similar_executes_correct_query(self):
        fake_results = [("text1", 0.12), ("text2", 0.25)]
        self.mock_cursor.fetchall.return_value = fake_results

        query_vector = [0.1] * 384
        result = self.vector_manager.search_similar(query_vector, k=2)

        # Vérifie exécution SQL
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args

        self.assertIn("SELECT content", args[0])
        self.assertEqual(args[1], (query_vector, 2))

        # Vérifie retour
        self.assertEqual(result, fake_results)

    def test_search_similar_default_k(self):
        self.mock_cursor.fetchall.return_value = []

        query_vector = [0.5] * 384
        self.vector_manager.search_similar(query_vector)

        args, _ = self.mock_cursor.execute.call_args

        # Vérifie que k=3 par défaut
        self.assertEqual(args[1][1], 3)

    def test_vector_manager_initialization(self):
        """
        Vérifie que la connexion et le modèle sont bien initialisés
        """
        self.assertIsNotNone(self.vector_manager.conn)
        self.assertIsNotNone(self.vector_manager.embeddings_model)


if __name__ == "__main__":
    unittest.main()
