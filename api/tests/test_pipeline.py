import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from core.pipeline import generate_document_context, seed_database
from core.pipeline.pii_manager import PIIManager
from core.pipeline.preprocess import QuestionProcessor


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
        mock_load.assert_called_once()

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
        mock_load.assert_called_once()

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

    @patch("core.pipeline.preprocess.OllamaEmbeddings")
    def setUp(self, mock_ollama):
        self.mock_model = MagicMock()
        mock_ollama.return_value = self.mock_model
        self.processor = QuestionProcessor()

    def test_preprocess_text_logic(self):
        """Vérifie la normalisation : minuscules, suppression accents et ponctuation."""
        raw = "  Dofus : L'Émeraude est MAGIQUE !!! "
        expected = "dofus lemeraude est magique"
        self.assertEqual(self.processor.preprocess_text(raw), expected)

    def test_vectorize_text(self):
        self.mock_model.embed_query.return_value = [0.1, 0.2, 0.3]
        result = self.processor.vectorize_text("test")
        self.assertEqual(result, [0.1, 0.2, 0.3])
        self.mock_model.embed_query.assert_called_once_with("test")

    def test_preprocess_without_spaces(self):
        """Vérifie le comportement si les mots sont séparés par de la ponctuation sans espaces."""
        raw = "Dofus:L'Emeraude"
        expected = "dofuslemeraude"
        self.assertEqual(self.processor.preprocess_text(raw), expected)


class TestIngestionPipeline(unittest.TestCase):
    """Tests pour le pipeline d'ingestion de lore."""

    @patch("core.pipeline.ingestion._import_providers", return_value=lambda provider_key, **kwargs: MagicMock())
    def test_generate_document_context_success(self, mock_import_providers):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Résumé du lore"
        mock_import_providers.return_value = lambda: mock_llm
        m_open = mock_open(read_data="Il était une fois...")
        with patch("builtins.open", m_open):
            ctx = generate_document_context(Path("lore_test.txt"), mock_llm)
        self.assertEqual(ctx, "Résumé du lore")
        mock_llm.invoke.assert_called_once()

    @patch('pathlib.Path.iterdir')
    @patch('core.pipeline.ingestion.is_valid_lore_file', return_value=True)
    @patch('core.pipeline.ingestion.VectorManager')
    @patch('converters.convert_text.process_text_file')
    @patch('core.utils.utils.load_config', return_value={})
    @patch('core.utils.utils.load_api_key', return_value="key")
    def test_seed_database_flow(self, mock_key, mock_cfg, mock_conv, mock_db, mock_valid, mock_iter):
        fake_file = MagicMock(spec=Path)
        fake_file.name = "lore_iroise.txt"
        fake_file.suffix = ".txt"
        fake_file.is_file.return_value = True
        mock_iter.return_value = [fake_file]

        mock_conv.return_value = [("Contenu chunk", {"page": 1})]
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance

        with patch("core.pipeline.ingestion._import_providers", return_value=lambda: None), \
                patch('shutil.move'):
            seed_database()

        mock_db_instance.add_document.assert_called_once_with(
            "Contenu chunk", metadata={"source": "lore_iroise.txt", "page": 1}
        )
        mock_valid.assert_called_once()
        mock_conv.assert_called_once()


if __name__ == "__main__":
    unittest.main()
