import unittest
from unittest.mock import patch, MagicMock, call
import os
from core.ingestion import


class TestSeedDatabase(unittest.TestCase):

    @patch('main.VectorManager')  # Mock de la base de données
    @patch('main.convert_text')  # Mock du module texte
    @patch('main.convert_markdown')  # Mock du module markdown
    @patch('main.convert_csv')  # Mock du module csv
    @patch('main.os')  # Mock du système de fichiers (os)
    def test_seed_database_csv(self, mock_os, mock_csv, mock_md, mock_txt, MockVectorManager):
        """Test le flux complet pour un fichier CSV."""

        # 1. Configuration des mocks
        # On simule la présence d'un seul fichier CSV
        mock_os.listdir.return_value = ['data.csv']
        mock_os.path.splitext.return_value = ('data', '.csv')
        mock_os.path.join.side_effect = lambda *args: "/".join(args)  # Simule un chemin simple

        # On simule le retour du convertisseur CSV (liste de dicts)
        mock_csv.load_csv_data.return_value = [
            {'nom': 'Alice', 'role': 'Admin'},
            {'nom': 'Bob', 'role': 'User'}
        ]

        # On récupère l'instance mockée du VectorManager pour vérifier les appels
        db_instance = MockVectorManager.return_value

        # 2. Exécution
        seed_database()

        # 3. Vérifications
        # Vérifie que le bon convertisseur a été appelé
        mock_csv.load_csv_data.assert_called_once()
        mock_md.parse_markdown.assert_not_called()

        # Vérifie la transformation des données (dict -> string) et l'insertion
        # Ligne 1: "nom: Alice role: Admin"
        # Ligne 2: "nom: Bob role: User"
        expected_calls = [
            call("nom: Alice role: Admin"),
            call("nom: Bob role: User")
        ]
        db_instance.add_document.assert_has_calls(expected_calls, any_order=True)

    @patch('main.VectorManager')
    @patch('main.convert_text')
    @patch('main.convert_markdown')
    @patch('main.convert_csv')
    @patch('main.os')
    def test_seed_database_markdown(self, mock_os, mock_csv, mock_md, mock_txt, MockVectorManager):
        """Test le flux complet pour un fichier Markdown."""

        # 1. Configuration
        mock_os.listdir.return_value = ['readme.md']
        mock_os.path.splitext.return_value = ('readme', '.md')

        # Le parseur MD retourne une liste de dicts avec une clé 'content'
        mock_md.parse_markdown.return_value = [
            {'type': 'header', 'content': '# Titre'},
            {'type': 'paragraph', 'content': 'Contenu du paragraphe'}
        ]

        db_instance = MockVectorManager.return_value

        # 2. Exécution
        seed_database()

        # 3. Vérifications
        mock_md.parse_markdown.assert_called_once()
        mock_csv.load_csv_data.assert_not_called()

        # Vérifie l'insertion
        expected_calls = [
            call('# Titre'),
            call('Contenu du paragraphe')
        ]
        db_instance.add_document.assert_has_calls(expected_calls)

    @patch('main.VectorManager')
    @patch('main.convert_text')
    @patch('main.convert_markdown')
    @patch('main.convert_csv')
    @patch('main.os')
    def test_seed_database_text(self, mock_os, mock_csv, mock_md, mock_txt, MockVectorManager):
        """Test le flux complet pour un fichier Texte."""

        # 1. Configuration
        mock_os.listdir.return_value = ['notes.txt']
        mock_os.path.splitext.return_value = ('notes', '.txt')

        # LangChain retourne des objets Document, on doit simuler cet objet
        doc1 = MagicMock()
        doc1.page_content = "Premier chunk de texte"
        doc2 = MagicMock()
        doc2.page_content = "Deuxième chunk"

        mock_txt.process_text_file.return_value = [doc1, doc2]

        db_instance = MockVectorManager.return_value

        # 2. Exécution
        seed_database()

        # 3. Vérifications
        mock_txt.process_text_file.assert_called_once()

        expected_calls = [
            call("Premier chunk de texte"),
            call("Deuxième chunk")
        ]
        db_instance.add_document.assert_has_calls(expected_calls)

    @patch('main.VectorManager')
    @patch('main.convert_text')
    @patch('main.convert_markdown')
    @patch('main.convert_csv')
    @patch('main.os')
    def test_seed_database_ignored_files(self, mock_os, mock_csv, mock_md, mock_txt, MockVectorManager):
        """Test que les fichiers non supportés (ex: .png) sont ignorés."""

        mock_os.listdir.return_value = ['image.png', 'script.py']

        # On configure splitext pour retourner les bonnes extensions
        def splitext_side_effect(filename):
            if filename == 'image.png': return ('image', '.png')
            if filename == 'script.py': return ('script', '.py')
            return (filename, '')

        mock_os.path.splitext.side_effect = splitext_side_effect

        db_instance = MockVectorManager.return_value

        seed_database()

        # Aucun convertisseur ne doit être appelé
        mock_csv.load_csv_data.assert_not_called()
        mock_md.parse_markdown.assert_not_called()
        mock_txt.process_text_file.assert_not_called()

        # Aucune insertion en base ne doit être faite
        db_instance.add_document.assert_not_called()


if __name__ == '__main__':
    unittest.main()