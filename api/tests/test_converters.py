import unittest
import tempfile
import os
import json

from unittest.mock import patch, MagicMock
from llama_index.core import Document

from converters.convert_json import parse_json
from converters.convert_csv import load_csv_data
from converters.convert_markdown import parse_markdown
from converters.convert_text import process_text_file
from converters.convert_pdf import process_pdf_file
from converters.convert_unstructured import process_with_unstructured


def create_temp_file(content: str, suffix: str) -> str:
    """Helper global pour créer un vrai fichier temporaire et renvoyer son chemin."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=suffix) as tmp:
        tmp.write(content)
        return tmp.name


class TestLoadCsvData(unittest.TestCase):

    def test_load_csv_nominal(self):
        """Test le cas normal : un fichier CSV valide."""
        csv_content = "name,age\nAlice,30\nBob,25"
        tmp_path = create_temp_file(csv_content, ".csv")
        file_name = os.path.basename(tmp_path)

        try:
            result = load_csv_data(tmp_path)

            # On s'attend à une liste de tuples (texte, metadata)
            self.assertEqual(len(result), 2)

            # chunk 1
            self.assertEqual(json.loads(result[0][0]), {"name": "Alice", "age": "30"})
            self.assertEqual(result[0][1], {"source": file_name, "item_name": "Alice"})

            # chunk 2
            self.assertEqual(json.loads(result[1][0]), {"name": "Bob", "age": "25"})
            self.assertEqual(result[1][1], {"source": file_name, "item_name": "Bob"})
        finally:
            os.remove(tmp_path)

    def test_load_csv_empty(self):
        """Test avec un fichier vide."""
        tmp_path = create_temp_file("", ".csv")

        try:
            result = load_csv_data(tmp_path)
            self.assertEqual(result, [])
        finally:
            os.remove(tmp_path)

    def test_file_not_found(self):
        """Test si le fichier n'existe pas (le convertisseur attrape l'erreur et renvoie une liste vide)."""
        result = load_csv_data("chemin_totalement_invente_qui_n_existe_pas.csv")
        self.assertEqual(result, [])

    def test_load_csv_headers_only(self):
        """Test un fichier qui n'a que des en-têtes mais pas de données."""
        csv_content = "col1,col2"
        tmp_path = create_temp_file(csv_content, ".csv")

        try:
            result = load_csv_data(tmp_path)
            self.assertEqual(result, [])
        finally:
            os.remove(tmp_path)


class TestParseMarkdown(unittest.TestCase):

    def test_nominal_parsing(self):
        """Test un scénario standard avec extraction des en-têtes dans les métadonnées."""
        md_content = "# Header\n\nParagraph text.\n- List item"
        tmp_path = create_temp_file(md_content, ".md")
        file_name = os.path.basename(tmp_path)

        try:
            result = parse_markdown(tmp_path)

            self.assertGreaterEqual(len(result), 1)
            text, metadata = result[0]

            self.assertIn("Paragraph text.", text)

            self.assertIn("header_path", metadata, f"Clé manquante. Métadonnées réelles : {metadata}")
            self.assertEqual(metadata.get("source"), file_name)

        finally:
            os.remove(tmp_path)

    def test_multiple_headers_logic(self):
        """Vérifie que le découpage sépare bien les sections."""
        md_content = "# Title 1\n\nContent for title 1.\n\n## Title 2\n\nContent for title 2."
        tmp_path = create_temp_file(md_content, ".md")

        try:
            result = parse_markdown(tmp_path)

            self.assertGreaterEqual(len(result), 2)

            # Vérification du premier chunk
            self.assertIn("Content for title 1.", result[0][0])
            self.assertIn("header_path", result[0][1])

            # Vérification du second chunk
            self.assertIn("Content for title 2.", result[-1][0])
            self.assertIn("header_path", result[-1][1])

        finally:
            os.remove(tmp_path)

    def test_chunking_size_logic(self):
        """Vérifie que le découpeur coupe les gros blocs."""
        long_text = "Ceci est une longue phrase pour forcer le découpage du texte en markdown. " * 50
        md_content = f"# Big Header\n\n{long_text}"
        tmp_path = create_temp_file(md_content, ".md")

        try:
            # On force une taille de chunk petite (mais suffisante pour les métadonnées)
            result = parse_markdown(tmp_path, chunk_size=100, chunk_overlap=0)

            self.assertGreater(len(result), 1)
            for text, metadata in result:
                self.assertIn("header_path", metadata)

        finally:
            os.remove(tmp_path)


class TestProcessTextFile(unittest.TestCase):

    def setUp(self):
        """Crée un fichier texte temporaire pour la suite de tests."""
        self.test_content = (
            "This is a test document.\n\n"
            "It contains multiple paragraphs.\n\n"
            "We want to split it into chunks for vector indexing."
        )
        self.tmp_path = create_temp_file(self.test_content, ".txt")
        self.file_name = os.path.basename(self.tmp_path)

    def tearDown(self):
        """Nettoie le fichier temporaire après les tests."""
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_returns_list_of_tuples(self):
        chunks = process_text_file(self.tmp_path)
        self.assertIsInstance(chunks, list)
        self.assertTrue(all(isinstance(chunk, tuple) and len(chunk) == 2 for chunk in chunks))

    def test_chunking_occurs(self):
        # La taille est en tokens pour LlamaIndex, une valeur très basse force le découpage
        long_text = "Ceci est une longue phrase destinée à forcer le découpage du document en plusieurs morceaux. " * 50
        tmp_path_long = create_temp_file(long_text, ".txt")

        try:
            chunks = process_text_file(tmp_path_long, chunk_size=100, chunk_overlap=0)
            self.assertGreater(len(chunks), 1)
        finally:
            os.remove(tmp_path_long)

    def test_metadata_contains_source(self):
        chunks = process_text_file(self.tmp_path)
        for text, metadata in chunks:
            self.assertIn("source", metadata)
            self.assertEqual(metadata["source"], self.file_name)


class TestParseJson(unittest.TestCase):

    def test_dict_with_list_of_objects(self):
        """Teste un dictionnaire contenant une liste d'objets et l'extraction de 'id', 'name' ou 'nom'."""
        json_data = {
            "utilisateurs": [
                {"id": 101, "role": "admin"},
                {"name": "Alice", "age": 30},
                {"nom": "Bob", "job": "dev"},
                {"age": 25}  # Pas d'identifiant
            ]
        }
        tmp_path = create_temp_file(json.dumps(json_data), ".json")
        file_name = os.path.basename(tmp_path)

        try:
            result = parse_json(tmp_path)

            self.assertEqual(len(result), 4)

            self.assertEqual(result[0][0], '{"id": 101, "role": "admin"}')
            self.assertEqual(result[0][1], {"source": file_name, "category": "utilisateurs", "item_name": "101"})

            self.assertEqual(result[1][1], {"source": file_name, "category": "utilisateurs", "item_name": "Alice"})
            self.assertEqual(result[2][1], {"source": file_name, "category": "utilisateurs", "item_name": "Bob"})
            self.assertEqual(result[3][1], {"source": file_name, "category": "utilisateurs"})

        finally:
            os.remove(tmp_path)

    def test_dict_with_single_object_and_raw_value(self):
        """Teste un dictionnaire avec un sous-dictionnaire et une valeur brute."""
        json_data = {
            "config": {"theme": "dark", "lang": "fr"},
            "version": 2.0
        }
        tmp_path = create_temp_file(json.dumps(json_data), ".json")
        file_name = os.path.basename(tmp_path)

        try:
            result = parse_json(tmp_path)
            self.assertEqual(len(result), 2)

            self.assertEqual(result[0][0], '{"theme": "dark", "lang": "fr"}')
            self.assertEqual(result[0][1], {"source": file_name, "category": "config"})

            self.assertEqual(result[1][0], "2.0")
            self.assertEqual(result[1][1], {"source": file_name, "category": "version"})

        finally:
            os.remove(tmp_path)

    def test_direct_list(self):
        """Teste le scénario où le JSON est directement une liste au niveau racine (sans parent_key)."""
        json_data = [
            {"id": "A1", "value": 10},
            {"value": 20}
        ]
        tmp_path = create_temp_file(json.dumps(json_data), ".json")
        file_name = os.path.basename(tmp_path)

        try:
            result = parse_json(tmp_path)
            self.assertEqual(len(result), 2)

            self.assertEqual(result[0][0], '{"id": "A1", "value": 10}')
            self.assertEqual(result[0][1], {"source": file_name, "item_name": "A1"})

            self.assertEqual(result[1][0], '{"value": 20}')
            self.assertEqual(result[1][1], {"source": file_name})

        finally:
            os.remove(tmp_path)

    def test_primitive_root(self):
        """Teste le cas extrême où le JSON est juste une valeur primitive (ex: juste une chaîne de caractères)."""
        json_data = "Just a simple string"
        tmp_path = create_temp_file(json.dumps(json_data), ".json")
        file_name = os.path.basename(tmp_path)

        try:
            result = parse_json(tmp_path)
            self.assertEqual(len(result), 1)

            self.assertEqual(result[0][0], "Just a simple string")
            self.assertEqual(result[0][1], {"source": file_name})

        finally:
            os.remove(tmp_path)


class TestProcessPdfFile(unittest.TestCase):

    @patch('converters.convert_pdf.SimpleDirectoryReader')
    def test_process_pdf_file_nominal(self, MockReader):
        """Teste le traitement PDF en simulant (mockant) le lecteur de LlamaIndex."""
        # Configuration du mock pour simuler ce que SimpleDirectoryReader renverrait normalement
        mock_instance = MockReader.return_value
        mock_instance.load_data.return_value = [
            Document(text="Contenu de la page 1 du PDF simulé.", metadata={"page_label": "1"}),
            Document(text="Contenu de la page 2. Un peu plus long pour tester le découpage.",
                     metadata={"page_label": "2"})
        ]

        file_name = "rapport_financier.pdf"

        # Appel de la fonction (le mock intercepte la lecture du fichier)
        result = process_pdf_file(file_name, chunk_size=50)

        # Vérifications
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 2)

        # Vérification du premier chunk
        text, metadata = result[0]
        self.assertIn("page 1", text)
        self.assertEqual(metadata["source"], file_name)
        # Vérifie la duplication de la clé demandée dans ton script
        self.assertEqual(metadata["page_number"], "1")
        self.assertEqual(metadata["page_label"], "1")


class TestProcessWithUnstructured(unittest.TestCase):

    @patch('converters.convert_unstructured.load_config')
    @patch('converters.convert_unstructured.UnstructuredClient')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b"dummy binary data")
    def test_process_with_unstructured_nominal(self, mock_file, MockClient, mock_load_config):
        """Teste l'appel Unstructured en simulant la configuration, le client API et le fichier."""
        # 1. Simuler la configuration
        mock_load_config.return_value = {
            "llm": {
                "unstructured": {"api_key": "cle_secrete_fictive", "server_url": "http://api.fictive.com"}
            }
        }

        # 2. Simuler la réponse de l'API Unstructured
        mock_client_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.elements = [
            {"text": "Titre principal du document", "type": "Title", "metadata": {"page_number": 1}},
            {"text": "Ceci est un paragraphe extrait par l'API.", "type": "NarrativeText",
             "metadata": {"page_number": 1}}
        ]
        mock_client_instance.general.partition.return_value = mock_response

        file_name = "document_complexe.docx"

        # Appel de la fonction
        result = process_with_unstructured(file_name, chunk_size=100)

        # Vérifications
        self.assertGreaterEqual(len(result), 2)

        text, metadata = result[0]
        self.assertEqual(text, "Titre principal du document")
        self.assertEqual(metadata["source"], file_name)
        self.assertEqual(metadata["method"], "unstructured")
        self.assertEqual(metadata["type"], "Title")
        self.assertEqual(metadata["page_number"], "1")

    @patch('converters.convert_unstructured.load_config')
    def test_missing_config_returns_empty(self, mock_load_config):
        """Teste le comportement si les clés d'API sont absentes du config.yaml."""
        # Simulation d'une configuration vide
        mock_load_config.return_value = {}

        result = process_with_unstructured("document.docx")

        # Doit renvoyer une liste vide et imprimer une erreur (interceptable mais on teste juste le retour ici)
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()