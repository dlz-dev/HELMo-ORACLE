import unittest
from unittest.mock import patch, MagicMock, mock_open
from langchain_core.documents import Document
import datetime

from core.pipeline.ingestion import seed_database
from core.pipeline.preprocess import QuestionProcessor
from core.database.vector_manager import VectorManager

# ─────────────────────────────────────────────────────────────────
# Constantes partagées
# ─────────────────────────────────────────────────────────────────
FAKE_CONFIG = {"guardian": {"provider": "groq", "model": "gemma2-9b-it"}}
FAKE_API_KEY = "fake_api_key"

# On mocke les couches système/config/API globalement pour isoler seed_database()
@patch("core.pipeline.ingestion.os.makedirs")
@patch("core.pipeline.ingestion.shutil.move")
@patch("core.pipeline.ingestion.get_llm")
@patch("core.pipeline.ingestion.is_valid_lore_file", return_value=True)
@patch("core.pipeline.ingestion.load_api_key", return_value=FAKE_API_KEY)
@patch("core.pipeline.ingestion._load_config", return_value=FAKE_CONFIG)
@patch("builtins.open", new_callable=mock_open, read_data="fake lore content")
class TestSeedDatabase(unittest.TestCase):

    @patch("core.pipeline.ingestion.os.listdir")
    @patch("core.pipeline.ingestion.VectorManager")
    @patch("core.pipeline.ingestion.convert_text.process_text_file")
    @patch("core.pipeline.ingestion.convert_markdown.parse_markdown")
    @patch("core.pipeline.ingestion.convert_csv.load_csv_data")
    def test_csv_file_processing(self, mock_load_csv, mock_parse_md, mock_process_text, mock_vector_manager, mock_listdir, *args):
        mock_listdir.return_value = ["lore_test.csv"]
        mock_load_csv.return_value = [{"name": "Alice", "age": 30}]
        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        seed_database()

        self.assertGreaterEqual(mock_db_instance.add_document.call_count, 1)

    @patch("core.pipeline.ingestion.os.listdir")
    @patch("core.pipeline.ingestion.VectorManager")
    @patch("core.pipeline.ingestion.convert_text.process_text_file")
    @patch("core.pipeline.ingestion.convert_markdown.parse_markdown")
    @patch("core.pipeline.ingestion.convert_csv.load_csv_data")
    def test_markdown_file_processing(self, mock_load_csv, mock_parse_md, mock_process_text, mock_vector_manager, mock_listdir, *args):
        mock_listdir.return_value = ["lore_doc.md"]
        mock_parse_md.return_value = [Document(page_content="Section 1", metadata={})]
        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        seed_database()
        self.assertEqual(mock_db_instance.add_document.call_count, 1)

    @patch("core.pipeline.ingestion.os.listdir")
    @patch("core.pipeline.ingestion.VectorManager")
    @patch("core.pipeline.ingestion.convert_text.process_text_file")
    @patch("core.pipeline.ingestion.convert_markdown.parse_markdown")
    @patch("core.pipeline.ingestion.convert_csv.load_csv_data")
    def test_text_file_processing(self, mock_load_csv, mock_parse_md, mock_process_text, mock_vector_manager, mock_listdir, *args):
        mock_listdir.return_value = ["lore_file.txt"]
        mock_process_text.return_value = [Document(page_content="Chunk 1", metadata={})]
        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance

        seed_database()
        self.assertEqual(mock_db_instance.add_document.call_count, 1)

    @patch("core.pipeline.ingestion.os.listdir")
    @patch("core.pipeline.ingestion.VectorManager")
    def test_unsupported_file_extension(self, mock_vector_manager, mock_listdir, *args):
        mock_listdir.return_value = ["lore_image.png"]
        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance
        seed_database()
        mock_db_instance.add_document.assert_not_called()

    @patch("core.pipeline.ingestion.os.listdir")
    @patch("core.pipeline.ingestion.VectorManager")
    @patch("core.pipeline.ingestion.convert_csv.load_csv_data")
    def test_empty_csv_file(self, mock_load_csv, mock_vector_manager, mock_listdir, *args):
        mock_listdir.return_value = ["lore_empty.csv"]
        mock_load_csv.return_value = []
        mock_db_instance = MagicMock()
        mock_vector_manager.return_value = mock_db_instance
        seed_database()
        mock_db_instance.add_document.assert_not_called()


class TestQuestionProcessor(unittest.TestCase):
    @patch("core.pipeline.preprocess.HuggingFaceEmbeddings")
    def setUp(self, mock_embeddings_class):
        self.mock_model = MagicMock()
        mock_embeddings_class.return_value = self.mock_model
        self.processor = QuestionProcessor()

    def test_preprocess_text_combined(self):
        text = "  HéLLo, Ça Vâ !!! "
        result = self.processor.preprocess_text(text)
        self.assertEqual(result, "hello ca va")

    def test_vectorize_text_calls_model(self):
        fake_vector = [0.1] * 384
        self.mock_model.embed_query.return_value = fake_vector
        result = self.processor.vectorize_text("test")
        self.assertEqual(result, fake_vector)


class TestVectorManager(unittest.TestCase):
    @patch("core.database.vector_manager.register_vector")
    @patch("core.database.vector_manager.psycopg.connect")
    @patch("core.database.vector_manager.HuggingFaceEmbeddings")
    def setUp(self, mock_embeddings_class, mock_connect, mock_register_vector):
        self.mock_conn = MagicMock()
        mock_connect.return_value = self.mock_conn
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_model = MagicMock()
        mock_embeddings_class.return_value = self.mock_model
        self.vector_manager = VectorManager()

    def test_add_document_calls_embed_and_insert(self):
        fake_vector = [0.1] * 384
        self.mock_model.embed_query.return_value = fake_vector
        self.vector_manager.add_document("hello world")

        args, _ = self.mock_cursor.execute.call_args
        self.assertEqual(args[1][:3], ("hello world", fake_vector, "{}"))

    def test_search_similar_default_k(self):
        self.mock_cursor.fetchall.return_value = []
        query_vector = [0.5] * 384
        self.vector_manager.search_similar(query_vector)
        args, _ = self.mock_cursor.execute.call_args
        self.assertEqual(args[1][1], 5)

    def test_vector_manager_initialization(self):
        self.assertIsNotNone(self.vector_manager.conn)

if __name__ == "__main__":
    unittest.main()