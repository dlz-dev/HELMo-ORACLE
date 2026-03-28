import unittest
from pathlib import Path
from unittest.mock import patch

import core.utils.utils as utils


class TestUtils(unittest.TestCase):

    def test_paths_definitions(self):
        """Vérifie que les chemins de base sont bien des objets Path."""
        self.assertIsInstance(utils.BASE_DIR, Path)
        self.assertIsInstance(utils.DATA_DIR, Path)
        self.assertTrue(str(utils.DATA_DIR).endswith("data"))

    def test_format_response_cleaning(self):
        """Vérifie le nettoyage des préfixes et des espaces."""
        raw_text = "Analyse: Voici le contenu.\n\n\nTrop d'espaces."
        expected = "Voici le contenu.\n\nTrop d'espaces."
        self.assertEqual(utils.format_response(raw_text), expected)

    def test_load_config(self):
        """Vérifie que load_config retourne bien un dict avec les clés attendues."""
        utils.load_config.cache_clear()
        config = utils.load_config()
        self.assertIn("database", config)
        self.assertIn("llm", config)
        self.assertIn("guardian", config)
        self.assertIn("search", config)

    @patch("core.utils.utils.load_config")
    def test_load_api_key_new_structure(self, mock_cfg):
        """Teste l'extraction de l'API key avec la nouvelle structure multi-provider."""
        mock_cfg.return_value = {
            "guardian": {"provider": "openai"},
            "llm": {
                "openai": {"api_key": "sk-12345"}
            }
        }
        key = utils.load_api_key()
        self.assertEqual(key, "sk-12345")

    @patch("core.utils.utils.load_config")
    def test_load_api_key_missing_returns_empty(self, mock_cfg):
        """Vérifie que load_api_key retourne une chaîne vide si la clé est absente."""
        mock_cfg.return_value = {
            "guardian": {"provider": "groq"},
            "llm": {"groq": {}}
        }
        key = utils.load_api_key()
        self.assertEqual(key, "")

    def test_prompts_presence(self):
        """Vérifie que les prompts internes sont bien définis."""
        self.assertIn("{sample}", utils._CONTEXT_PROMPT)
        self.assertIn("Dofus", utils._GUARDIAN_PROMPT)


if __name__ == "__main__":
    unittest.main()
