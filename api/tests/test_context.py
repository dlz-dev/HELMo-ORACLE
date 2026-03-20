import unittest
from unittest.mock import MagicMock, patch
import os
import shutil

from ..core.context.memory_manager import MemoryManager
from ..core.context import SessionManager, _make_title


class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.max_tokens = 1200
        self.mm = MemoryManager(max_recent_tokens=self.max_tokens, min_recent_messages=2)
        self.mock_llm = MagicMock()
        self.mock_llm.complete.return_value.text = "Résumé de test"

    def test_estimate_tokens(self):
        from ..core.context.memory_manager import _estimate_tokens
        self.assertEqual(_estimate_tokens("ABCDEFGHIJKL"), 4)
        self.assertEqual(_estimate_tokens(""), 1)

    def test_needs_summarization(self):
        messages = [{"role": "user", "content": "Hello"}]
        self.assertFalse(self.mm.needs_summarization(messages, ""))

        long_messages = [{"role": "user", "content": "Token " * 200}] * 5
        self.assertTrue(self.mm.needs_summarization(long_messages, ""))

    def test_compress_logic(self):
        session = {
            "messages": [
                {"role": "user", "content": "M1"}, {"role": "assistant", "content": "R1"},
                {"role": "user", "content": "M2"}, {"role": "assistant", "content": "R2"}
            ],
            "summary": ""
        }

        with patch.object(self.mm, '_get_recent_window') as mock_window:
            mock_window.return_value = session["messages"][2:]
            updated_session = self.mm.compress(session, self.mock_llm)

            self.assertEqual(len(updated_session["messages"]), 2)
            self.assertEqual(updated_session["summary"], "Résumé de test")
            self.assertEqual(updated_session["messages"][0]["content"], "M2")
            # Vérifie que le LLM a bien été appelé pour générer le résumé
            self.mock_llm.complete.assert_called_once()
            call_args = self.mock_llm.complete.call_args[0][0]
            self.assertIn("M1", call_args)
            self.assertIn("R1", call_args)

    def test_build_agent_input(self):
        session = {
            "messages": [{"role": "user", "content": "Hello"}],
            "summary": "Résumé existant"
        }
        base_prompt = "Système de base"

        # Test avec résumé
        enriched, history = self.mm.build_agent_input(session, base_prompt)
        self.assertIn("Résumé existant", enriched)
        self.assertIn(base_prompt, enriched)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], ("user", "Hello"))

        # Test sans résumé — le prompt enrichi doit être égal au prompt de base
        session["summary"] = ""
        enriched_no_sum, history_no_sum = self.mm.build_agent_input(session, base_prompt)
        self.assertEqual(enriched_no_sum, base_prompt)
        self.assertEqual(len(history_no_sum), 1)


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = "./test_storage_tmp"
        self.patch_is_cloud = patch('core.context.session_manager._is_cloud', return_value=False)
        self.patch_storage = patch('core.context.session_manager.STORAGE_DIR', self.test_dir)

        self.patch_is_cloud.start()
        self.patch_storage.start()
        self.sm = SessionManager()

    def tearDown(self):
        self.patch_is_cloud.stop()
        self.patch_storage.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_make_title(self):
        text = "Ceci est un message très long qui doit être tronqué pour le titre"
        title = _make_title(text)
        self.assertTrue(title.endswith("…"))
        self.assertLessEqual(len(title), 61)

    def test_session_lifecycle(self):
        session = self.sm.new_session(provider="Mock", model="TestModel")
        session_id = session["session_id"]

        session["messages"].append({"role": "user", "content": "Mon nouveau sujet"})
        self.sm.save(session)

        loaded = self.sm.load(session_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["title"], "Mon nouveau sujet")

        self.sm.delete(session_id)
        self.assertIsNone(self.sm.load(session_id))


if __name__ == "__main__":
    unittest.main()