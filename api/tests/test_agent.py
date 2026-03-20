import unittest
from unittest.mock import MagicMock, patch, mock_open

from ..core.agent.tools_oracle import get_search_tool, CONFIDENCE_THRESHOLD_HIGH
from ..core.agent.guardian import is_valid_lore_file


class TestOracleTool(unittest.TestCase):
    """Tests unitaires pour l'outil de recherche Oracle."""

    def setUp(self):
        self.mock_vm = MagicMock()
        self.mock_vm.embeddings_model.get_query_embedding.return_value = [0.1, 0.2, 0.3]

    def test_search_high_confidence(self):
        """Vérifie le format XML et le calcul de confiance 'high'."""
        self.mock_vm.search_hybrid.return_value = [
            ("Contenu sacré", CONFIDENCE_THRESHOLD_HIGH + 0.01, {"source": "bestiaire.json"})
        ]
        cot_storage = []
        search_tool = get_search_tool(self.mock_vm, k_final=1, cot_storage=cot_storage)
        result = search_tool.invoke("C'est quoi un bwak ?")

        self.assertIn("<archives_sacrees>", result)
        self.assertIn("[Source: bestiaire.json]", result)
        self.assertEqual(len(cot_storage), 1)
        self.assertEqual(cot_storage[0]["confidence"], "high")
        self.assertEqual(cot_storage[0]["source"], "bestiaire.json")
        self.mock_vm.search_hybrid.assert_called_once()
        self.mock_vm.embeddings_model.get_query_embedding.assert_called_once()

    def test_search_medium_confidence(self):
        """Vérifie le calcul de confiance 'medium'."""
        from ..core.agent.tools_oracle import CONFIDENCE_THRESHOLD_MEDIUM
        self.mock_vm.search_hybrid.return_value = [
            ("Contenu partiel", CONFIDENCE_THRESHOLD_MEDIUM + 0.001, {"source": "lore.txt"})
        ]
        cot_storage = []
        search_tool = get_search_tool(self.mock_vm, k_final=1, cot_storage=cot_storage)
        search_tool.invoke("Question")

        self.assertEqual(cot_storage[0]["confidence"], "medium")
        self.mock_vm.search_hybrid.assert_called_once()

    def test_search_no_results(self):
        """Vérifie le message de retour quand aucun document n'est trouvé."""
        self.mock_vm.search_hybrid.return_value = []
        cot_storage = []
        search_tool = get_search_tool(self.mock_vm, cot_storage=cot_storage)
        result = search_tool.invoke("Vide")

        self.assertIn("No documents found", result)
        self.assertEqual(len(cot_storage), 0)
        self.mock_vm.search_hybrid.assert_called_once()

    def test_empty_query_sanitized(self):
        """Vérifie que les queries vides sont gérées proprement."""
        self.mock_vm.search_hybrid.return_value = []
        search_tool = get_search_tool(self.mock_vm)
        result = search_tool.invoke("   ")
        self.assertIn("archives_sacrees", result)

    def test_cot_storage_cleared_between_calls(self):
        """Vérifie que le cot_storage est vidé à chaque nouvel appel."""
        self.mock_vm.search_hybrid.return_value = [
            ("Chunk 1", 0.03, {"source": "a.txt"})
        ]
        cot_storage = [{"source": "ancien", "content": "vieux", "rrf_score": 0.1, "confidence": "high"}]
        search_tool = get_search_tool(self.mock_vm, k_final=1, cot_storage=cot_storage)
        search_tool.invoke("Question")

        self.assertEqual(len(cot_storage), 1)
        self.assertEqual(cot_storage[0]["source"], "a.txt")


class TestGuardian(unittest.TestCase):
    """Tests unitaires pour le validateur de fichiers Guardian."""

    @patch('core.agent.guardian.os.path.splitext')
    def test_pdf_auto_accept(self, mock_splitext):
        """Vérifie que les PDF sont acceptés par défaut."""
        mock_splitext.return_value = ('mon_fichier', '.pdf')
        self.assertTrue(is_valid_lore_file("test.pdf"))
        mock_splitext.assert_called_once_with("test.pdf")

    @patch('core.agent.guardian.load_config')
    @patch('core.agent.guardian.get_llm')
    def test_guardian_rejection(self, mock_get_llm, mock_load_config):
        """Vérifie le rejet d'un fichier si le LLM ne valide pas le contenu."""
        mock_load_config.return_value = {"guardian": {"provider": "test", "model": "test"}}
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "NON"
        mock_get_llm.return_value = mock_llm

        with patch('builtins.open', mock_open(read_data="Contenu inapproprié")):
            with patch('core.agent.guardian.os.path.splitext', return_value=('test', '.txt')):
                result = is_valid_lore_file("test.txt")

        self.assertFalse(result)
        mock_get_llm.assert_called_once()
        mock_llm.invoke.assert_called_once()

    @patch('core.agent.guardian.load_config')
    @patch('core.agent.guardian.get_llm')
    def test_guardian_acceptance(self, mock_get_llm, mock_load_config):
        """Vérifie l'acceptation d'un fichier valide."""
        mock_load_config.return_value = {"guardian": {"provider": "test", "model": "test"}}
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "OUI"
        mock_get_llm.return_value = mock_llm

        with patch('builtins.open', mock_open(read_data="Données Dofus valides")):
            with patch('core.agent.guardian.os.path.splitext', return_value=('lore_test', '.txt')):
                result = is_valid_lore_file("lore_test.txt")

        self.assertTrue(result)
        mock_llm.invoke.assert_called_once()

    def test_read_error_handling(self):
        """Vérifie que le Guardian rejette un fichier en cas d'erreur de lecture."""
        with patch('core.agent.guardian.open', side_effect=Exception("Erreur critique")):
            with patch('core.agent.guardian.os.path.splitext', return_value=('erreur', '.txt')):
                result = is_valid_lore_file("erreur.txt")
                self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()