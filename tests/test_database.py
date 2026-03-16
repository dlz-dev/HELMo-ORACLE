import unittest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from core.database.vector_manager import VectorManager


class TestVectorManager(unittest.TestCase):

    @patch('core.database.vector_manager.register_vector')
    @patch('core.database.vector_manager.psycopg.connect')
    @patch('core.database.vector_manager.HuggingFaceEmbedding')
    @patch('core.database.vector_manager.load_config')
    def setUp(self, mock_load_config, mock_embedding, mock_connect, mock_register):
        mock_load_config.return_value = {
            "database": {"connection_string": "postgresql://user:pass@localhost:5432/db"}
        }

        self.mock_conn = MagicMock()
        mock_connect.return_value = self.mock_conn

        self.mock_cur = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cur

        self.mock_embed_model = MagicMock()
        mock_embedding.return_value = self.mock_embed_model

        self.manager = VectorManager()

    def test_add_document_formatting(self):
        text = "Contenu de test"
        metadata = {"Header 1": "Chapitre 1"}
        self.mock_embed_model.get_text_embedding.return_value = [0.1, 0.2]

        self.manager.add_document(text, metadata)

        self.mock_embed_model.get_text_embedding.assert_called_with(
            "Chapter: Chapitre 1\n\nContent: Contenu de test"
        )
        self.assertTrue(self.mock_cur.execute.called)

    def test_search_semantic_query(self):
        query_vector = [0.1, 0.2]
        self.mock_cur.fetchall.return_value = [("content", 0.1, {})]

        results = self.manager.search_semantic(query_vector, k=5)

        self.assertEqual(len(results), 1)
        args, _ = self.mock_cur.execute.call_args
        self.assertIn("<=>", args[0])

    def test_search_hybrid_rrf_logic(self):
        self.manager.search_semantic = MagicMock(return_value=[
            ("Doc A", 0.1, {}), ("Doc B", 0.2, {})
        ])
        self.manager.search_bm25 = MagicMock(return_value=[
            ("Doc B", 0.9, {}), ("Doc C", 0.8, {})
        ])

        results = self.manager.search_hybrid("query", [0.1], k_final=3)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][0], "Doc B")

    def test_list_sources_mapping(self):
        now = datetime.now(timezone.utc)
        self.mock_cur.fetchall.return_value = [("file.pdf", 5, "Context", now)]

        sources = self.manager.list_sources()

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source"], "file.pdf")
        self.assertEqual(sources[0]["chunk_count"], 5)
        self.assertTrue(isinstance(sources[0]["ingested_at"], str))

    def test_list_sources_empty(self):
        self.mock_cur.fetchall.return_value = []
        self.assertEqual(self.manager.list_sources(), [])


if __name__ == '__main__':
    unittest.main()