import unittest
from unittest.mock import MagicMock, patch, mock_open

from core.agent.tools_oracle import get_search_tool, CONFIDENCE_THRESHOLD_HIGH
from core.agent.guardian import is_valid_lore_file


class TestOracleTool(unittest.TestCase):
    """Tests unitaires pour l'outil de recherche Oracle."""

    def setUp(self):
        """Configuration initiale : Mock du VectorManager et de la session Streamlit."""
        self.mock_vm = MagicMock()
        # Simulation du retour du modèle d'embeddings
        self.mock_vm.embeddings_model.get_query_embedding.return_value = [0.1, 0.2, 0.3]

        # On définit un dictionnaire vide pour simuler st.session_state
        self.state_data = {}
        # On patche le dictionnaire session_state dans le module cible
        self.patcher = patch('core.agent.tools_oracle.st.session_state', self.state_data)
        self.patcher.start()

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.patcher.stop()

    def test_search_knowledge_base_high_confidence(self):
        """Vérifie le format XML et le calcul de confiance 'high'."""
        # Simulation d'un résultat avec un score élevé (RRF > 0.025)
        self.mock_vm.search_hybrid.return_value = [
            ("Contenu sacré", CONFIDENCE_THRESHOLD_HIGH + 0.01, {"source": "Bible.txt"})
        ]

        search_tool = get_search_tool(self.mock_vm, k_final=1)
        result = search_tool.invoke("Ma question")

        # Vérifications de structure
        self.assertIn("<archives_sacrees>", result)
        self.assertIn("[Source: Bible.txt]", result)
        # Vérification de l'état interne stocké pour l'UI
        self.assertEqual(self.state_data["_cot_results"][0]["confidence"], "high")

    def test_search_no_results(self):
        """Vérifie le message de retour quand aucun document n'est trouvé."""
        self.mock_vm.search_hybrid.return_value = []

        search_tool = get_search_tool(self.mock_vm)
        result = search_tool.invoke("Vide")

        self.assertIn("No documents found", result)


class TestGuardian(unittest.TestCase):
    """Tests unitaires pour le validateur de fichiers Guardian."""

    @patch('core.agent.guardian.os.path.splitext')
    def test_pdf_auto_accept(self, mock_splitext):
        """Vérifie que les PDF sont acceptés par défaut (conversion Unstructured)."""
        mock_splitext.return_value = ('mon_fichier', '.pdf')
        self.assertTrue(is_valid_lore_file("test.pdf"))

    @patch('core.agent.guardian.load_config')
    @patch('core.agent.guardian.get_llm')
    def test_guardian_rejection(self, mock_get_llm, mock_load_config):
        """Vérifie le rejet d'un fichier si le LLM ne valide pas le contenu."""
        # Mock de la configuration et de la réponse LLM
        mock_load_config.return_value = {"guardian": {"provider": "test", "model": "test"}}
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "NON"  # Le prompt est en français
        mock_get_llm.return_value = mock_llm

        # Simulation de lecture de fichier et de split
        with patch('builtins.open', mock_open(read_data="Contenu inapproprié")):
            with patch('core.agent.guardian.os.path.splitext', return_value=('test', '.txt')):
                result = is_valid_lore_file("test.txt")

        self.assertFalse(result)

    def test_read_error_handling(self):
        """Vérifie que le Guardian rejette un fichier en cas d'erreur de lecture."""
        # On patche open dans le module guardian pour simuler une erreur fatale
        with patch('core.agent.guardian.open', side_effect=Exception("Erreur critique")):
            with patch('core.agent.guardian.os.path.splitext', return_value=('erreur', '.txt')):
                result = is_valid_lore_file("erreur.txt")
                self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()