import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from core.pipeline.pii_manager import PIIManager
from core.pipeline.preprocess import QuestionProcessor
from core.pipeline.ingestion import generate_document_context, seed_database


class TestPIIManager(unittest.TestCase):
    """Tests pour le masquage des données sensibles (Regex + Spacy)."""

    def setUp(self):
        PIIManager._nlp_model = None

    def _setup_mock_spacy(self, mock_load, entities=None):
        mock_model = MagicMock()
        mock_doc = MagicMock()
        ents = []
        for ent_data in (entities or []):
            ent = MagicMock()
            ent.text = ent_data["text"]
            ent.label_ = ent_data["label_"]
            ents.append(ent)
        mock_doc.ents = ents
        mock_model.return_value = mock_doc
        mock_load.return_value = mock_model

    @patch("core.pipeline.pii_manager.spacy.load")
    def test_mask_regex_patterns(self, mock_load):
        self._setup_mock_spacy(mock_load)
        manager = PIIManager()
        text = "Contact: test@gmail.com, Tel: 0612345678, IP: 192.168.1.1"
        expected = "Contact: [EMAIL], Tel: [PHONE], IP: [IP_ADDR]"
        self.assertEqual(manager.mask_text(text), expected)

    @patch("core.pipeline.pii_manager.spacy.load")
    def test_mask_ner_entities(self, mock_load):
        entities = [
            {"text": "Yugo", "label_": "PER"},
            {"text": "Amakna", "label_": "LOC"},
            {"text": "Ankama", "label_": "ORG"}
        ]
        self._setup_mock_spacy(mock_load, entities)
        manager = PIIManager()
        text = "Yugo de Amakna travaille chez Ankama."
        expected = "[PERSON] de [LOCATION] travaille chez [ORG]."
        self.assertEqual(manager.mask_text(text), expected)

    @patch("core.pipeline.pii_manager.spacy.load")
    def test_mask_without_spaces(self, mock_load):  # Ajout de mock_load ici
        """Vérifie que le masquage fonctionne même sans espaces après la ponctuation."""
        self._setup_mock_spacy(mock_load)

        manager = PIIManager()
        text = "Tel:0612345678,Mail:test@helmo.be"
        expected = "Tel:[PHONE],Mail:[EMAIL]"
        self.assertEqual(manager.mask_text(text), expected)


class TestQuestionProcessor(unittest.TestCase):
    """Tests pour le prétraitement et la vectorisation."""

    @patch("core.pipeline.preprocess.HuggingFaceEmbedding")
    def setUp(self, mock_hf):
        self.mock_model = MagicMock()
        mock_hf.return_value = self.mock_model
        self.processor = QuestionProcessor()

    def test_preprocess_text_logic(self):
        """Vérifie la normalisation : minuscules, suppression accents et ponctuation."""
        raw = "  Dofus : L'Émeraude est MAGIQUE !!! "
        expected = "dofus lemeraude est magique"
        self.assertEqual(self.processor.preprocess_text(raw), expected)

    def test_vectorize_text(self):
        self.mock_model.get_query_embedding.return_value = [0.1, 0.2, 0.3]
        result = self.processor.vectorize_text("test")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    def test_preprocess_without_spaces(self):
        """Vérifie le comportement si les mots sont séparés par de la ponctuation sans espaces."""
        raw = "Dofus:L'Emeraude"
        expected = "dofuslemeraude"
        self.assertEqual(self.processor.preprocess_text(raw), expected)


class TestIngestionPipeline(unittest.TestCase):
    """Tests pour le pipeline d'ingestion de lore."""

    @patch("core.pipeline.ingestion.get_llm")
    def test_generate_document_context_success(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Résumé du lore"
        m_open = mock_open(read_data="Il était une fois...")
        with patch("builtins.open", m_open):
            ctx = generate_document_context(Path("lore_test.txt"), mock_llm)
        self.assertEqual(ctx, "Résumé du lore")

    @patch("core.pipeline.ingestion.Path.iterdir")
    @patch("core.pipeline.ingestion.is_valid_lore_file", return_value=True)
    @patch("core.pipeline.ingestion.VectorManager")
    @patch("core.pipeline.ingestion.convert_text.process_text_file")
    @patch("core.pipeline.ingestion.load_config", return_value={})
    @patch("core.pipeline.ingestion.load_api_key", return_value="key")
    def test_seed_database_flow(self, mock_key, mock_cfg, mock_conv, mock_db, mock_valid, mock_iter):
        fake_file = MagicMock(spec=Path)
        fake_file.name = "lore_iroise.txt"
        fake_file.suffix = ".txt"
        fake_file.is_file.return_value = True
        mock_iter.return_value = [fake_file]

        mock_conv.return_value = [("Contenu chunk", {"page": 1})]
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance

        with patch("core.pipeline.ingestion.get_llm", return_value=None):
            seed_database()

        self.assertTrue(mock_db_instance.add_document.called)


if __name__ == "__main__":
    unittest.main()