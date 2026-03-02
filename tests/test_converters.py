import unittest
import tempfile
import os
import json
from converters.convert_json import parse_json
from langchain_core.documents import Document
from converters.convert_csv import load_csv_data
from converters.convert_markdown import parse_markdown
from converters.convert_text import process_text_file


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

        try:
            result = load_csv_data(tmp_path)
            expected = [
                {"name": "Alice", "age": "30"},
                {"name": "Bob", "age": "25"}
            ]
            self.assertEqual(result, expected)
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
        """Test si le fichier n'existe pas (doit lever FileNotFoundError)."""
        with self.assertRaises(FileNotFoundError):
            load_csv_data("chemin_totalement_invente_qui_n_existe_pas.csv")

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
        # Le MarkdownHeaderTextSplitter va retirer le "# Header" du texte
        # et le placer dans les metadata sous la clé "Header 1".
        md_content = "# Header\n\nParagraph text.\n- List item"
        tmp_path = create_temp_file(md_content, ".md")

        try:
            result = parse_markdown(tmp_path)

            # Avec Langchain, ce texte entier est regroupé sous un seul Document
            self.assertEqual(len(result), 1)

            # Vérification du type
            self.assertIsInstance(result[0], Document)

            # Vérification du contenu (le titre a été extrait)
            self.assertEqual(result[0].page_content, "Paragraph text.\n- List item")

            # Vérification des métadonnées (Titre + Source)
            self.assertEqual(result[0].metadata["Header 1"], "Header")
            self.assertEqual(result[0].metadata["source"], os.path.basename(tmp_path))

        finally:
            os.remove(tmp_path)

    def test_multiple_headers_logic(self):
        """Vérifie que le découpage sépare bien les sections selon les en-têtes (H1, H2)."""
        md_content = "# Title 1\n\nContent for title 1.\n\n## Title 2\n\nContent for title 2."
        tmp_path = create_temp_file(md_content, ".md")

        try:
            result = parse_markdown(tmp_path)

            # On attend 2 documents car il y a deux sections distinctes
            self.assertEqual(len(result), 2)

            # Vérification du premier chunk
            self.assertEqual(result[0].page_content, "Content for title 1.")
            self.assertEqual(result[0].metadata["Header 1"], "Title 1")

            # Vérification du second chunk (qui hérite du H1 et possède son propre H2)
            self.assertEqual(result[1].page_content, "Content for title 2.")
            self.assertEqual(result[1].metadata["Header 1"], "Title 1")
            self.assertEqual(result[1].metadata["Header 2"], "Title 2")

        finally:
            os.remove(tmp_path)

    def test_chunking_size_logic(self):
        """Vérifie que le RecursiveCharacterTextSplitter coupe les gros blocs (chunk_size=500)."""
        # Création d'un très long texte de 600 caractères
        long_text = "A" * 600
        md_content = f"# Big Header\n\n{long_text}"
        tmp_path = create_temp_file(md_content, ".md")

        try:
            result = parse_markdown(tmp_path)

            # Le texte dépassant les 500 caractères, il doit être découpé en plusieurs morceaux
            self.assertGreater(len(result), 1)

            # Chaque morceau doit conserver les métadonnées de l'en-tête
            for chunk in result:
                self.assertEqual(chunk.metadata["Header 1"], "Big Header")
                self.assertLessEqual(len(chunk.page_content), 500)

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

    def tearDown(self):
        """Nettoie le fichier temporaire après les tests."""
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_returns_list_of_documents(self):
        chunks = process_text_file(self.tmp_path)
        self.assertIsInstance(chunks, list)
        self.assertTrue(all(isinstance(chunk, Document) for chunk in chunks))

    def test_chunking_occurs(self):
        chunks = process_text_file(
            self.tmp_path,
            chunk_size=30,
            chunk_overlap=0
        )
        self.assertGreater(len(chunks), 1)

    def test_chunk_size_respected(self):
        chunk_size = 40
        chunks = process_text_file(
            self.tmp_path,
            chunk_size=chunk_size,
            chunk_overlap=0
        )
        for chunk in chunks:
            self.assertLessEqual(len(chunk.page_content), chunk_size)

    def test_chunk_overlap(self):
        long_string = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        tmp_path = create_temp_file(long_string, ".txt")

        try:
            chunk_size = 30
            chunk_overlap = 10
            chunks = process_text_file(
                tmp_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            if len(chunks) > 1:
                first_chunk = chunks[0].page_content
                second_chunk = chunks[1].page_content
                self.assertEqual(
                    first_chunk[-chunk_overlap:],
                    second_chunk[:chunk_overlap]
                )
        finally:
            os.remove(tmp_path)

    def test_metadata_contains_source(self):
        chunks = process_text_file(self.tmp_path)
        for chunk in chunks:
            self.assertIn("source", chunk.metadata)
            self.assertEqual(chunk.metadata["source"], self.tmp_path)


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

        try:
            result = parse_json(tmp_path)

            # On s'attend à 4 chunks (1 par utilisateur dans la liste)
            self.assertEqual(len(result), 4)

            # Vérification du premier élément (clé 'id' extraite en 'item_name')
            self.assertEqual(result[0][0], '{"id": 101, "role": "admin"}')
            self.assertEqual(result[0][1], {"category": "utilisateurs", "item_name": "101"})

            # Vérification du deuxième (clé 'name' extraite)
            self.assertEqual(result[1][1], {"category": "utilisateurs", "item_name": "Alice"})

            # Vérification du troisième (clé 'nom' extraite)
            self.assertEqual(result[2][1], {"category": "utilisateurs", "item_name": "Bob"})

            # Vérification du quatrième (sans identifiant, il a juste la catégorie)
            self.assertEqual(result[3][1], {"category": "utilisateurs"})

        finally:
            os.remove(tmp_path)

    def test_dict_with_single_object_and_raw_value(self):
        """Teste un dictionnaire avec un sous-dictionnaire et une valeur brute."""
        json_data = {
            "config": {"theme": "dark", "lang": "fr"},
            "version": 2.0
        }
        tmp_path = create_temp_file(json.dumps(json_data), ".json")

        try:
            result = parse_json(tmp_path)
            self.assertEqual(len(result), 2)

            # Vérification de l'objet unique
            self.assertEqual(result[0][0], '{"theme": "dark", "lang": "fr"}')
            self.assertEqual(result[0][1], {"category": "config"})

            # Vérification de la valeur brute (castée en string)
            self.assertEqual(result[1][0], "2.0")
            self.assertEqual(result[1][1], {"category": "version"})

        finally:
            os.remove(tmp_path)

    def test_direct_list(self):
        """Teste le scénario où le JSON est directement une liste au niveau racine (sans parent_key)."""
        json_data = [
            {"id": "A1", "value": 10},
            {"value": 20}
        ]
        tmp_path = create_temp_file(json.dumps(json_data), ".json")

        try:
            result = parse_json(tmp_path)
            self.assertEqual(len(result), 2)

            # Les items ont un item_name mais pas de category
            self.assertEqual(result[0][0], '{"id": "A1", "value": 10}')
            self.assertEqual(result[0][1], {"item_name": "A1"})

            self.assertEqual(result[1][0], '{"value": 20}')
            self.assertEqual(result[1][1], {})

        finally:
            os.remove(tmp_path)

    def test_primitive_root(self):
        """Teste le cas extrême où le JSON est juste une valeur primitive (ex: juste une chaîne de caractères)."""
        json_data = "Just a simple string"
        tmp_path = create_temp_file(json.dumps(json_data), ".json")

        try:
            result = parse_json(tmp_path)
            self.assertEqual(len(result), 1)

            self.assertEqual(result[0][0], "Just a simple string")
            self.assertEqual(result[0][1], {})  # Métadonnées vides

        finally:
            os.remove(tmp_path)


if __name__ == '__main__':
    unittest.main()