import unittest
from unittest.mock import patch, mock_open
from pathlib import Path
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

    @patch("builtins.open", new_callable=mock_open, read_data="search:\n  k_final: 42")
    @patch("yaml.safe_load")
    def test_load_config(self, mock_yaml, mock_file):
        """Vérifie le chargement du fichier YAML."""
        mock_yaml.return_value = {"search": {"k_final": 42}}

        utils.load_config.cache_clear()
        config = utils.load_config()

        self.assertEqual(config["search"]["k_final"], 42)
        # On vérifie que le chemin utilisé est bien celui défini dans utils
        mock_file.assert_called_with(utils.CONFIG_PATH, "r", encoding="utf-8")

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
    def test_load_api_key_legacy_structure(self, mock_cfg):
        """Teste la compatibilité avec l'ancienne structure d'API key."""
        mock_cfg.return_value = {
            "api": {"api_key": "legacy-key-678"}
        }
        key = utils.load_api_key()
        self.assertEqual(key, "legacy-key-678")

    def test_prompts_presence(self):
        """Vérifie que les prompts internes sont bien définis."""
        self.assertIn("{sample}", utils._CONTEXT_PROMPT)
        self.assertIn("Dofus", utils._GUARDIAN_PROMPT)


if __name__ == "__main__":
    unittest.main()