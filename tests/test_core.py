"""
Unit tests for SettingsManager, AIClient, and TextHandler.
These tests do not require a display (no PyQt5 widgets are instantiated).
"""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ──────────────────────────────────────────────────────────────────────
# SettingsManager tests
# ──────────────────────────────────────────────────────────────────────


class TestSettingsManager(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_manager(self):
        from app.settings_manager import SettingsManager

        mgr = SettingsManager.__new__(SettingsManager)
        mgr.config_dir = self._tmp_path
        mgr.config_file = self._tmp_path / "config.json"
        from app.settings_manager import DEFAULT_SETTINGS

        mgr.settings = DEFAULT_SETTINGS.copy()
        return mgr

    def test_defaults_are_loaded(self):
        from app.settings_manager import DEFAULT_SETTINGS

        mgr = self._make_manager()
        for key, value in DEFAULT_SETTINGS.items():
            self.assertEqual(mgr.get(key), value)

    def test_set_and_get(self):
        mgr = self._make_manager()
        mgr.set("api_key", "sk-test")
        self.assertEqual(mgr.get("api_key"), "sk-test")

    def test_save_and_reload(self):
        from app.settings_manager import SettingsManager, DEFAULT_SETTINGS

        mgr = self._make_manager()
        mgr.set("api_key", "sk-saved")
        mgr.set("model", "gpt-4o")

        # Reload from the same file
        mgr2 = SettingsManager.__new__(SettingsManager)
        mgr2.config_dir = self._tmp_path
        mgr2.config_file = self._tmp_path / "config.json"
        mgr2.settings = DEFAULT_SETTINGS.copy()
        mgr2.load()

        self.assertEqual(mgr2.get("api_key"), "sk-saved")
        self.assertEqual(mgr2.get("model"), "gpt-4o")

    def test_update_merges_keys(self):
        mgr = self._make_manager()
        original_prompt = mgr.get("prompt")
        mgr.update({"api_key": "key123", "temperature": 0.9})
        self.assertEqual(mgr.get("api_key"), "key123")
        self.assertAlmostEqual(mgr.get("temperature"), 0.9)
        self.assertEqual(mgr.get("prompt"), original_prompt)

    def test_get_missing_key_returns_default(self):
        mgr = self._make_manager()
        self.assertIsNone(mgr.get("nonexistent_key"))
        self.assertEqual(mgr.get("nonexistent_key", "fallback"), "fallback")

    def test_corrupt_config_does_not_crash(self):
        from app.settings_manager import SettingsManager, DEFAULT_SETTINGS

        mgr = SettingsManager.__new__(SettingsManager)
        mgr.config_dir = self._tmp_path
        mgr.config_file = self._tmp_path / "config.json"
        mgr.settings = DEFAULT_SETTINGS.copy()

        # Write invalid JSON
        with open(mgr.config_file, "w") as f:
            f.write("{bad json}")

        mgr.load()  # should not raise
        self.assertEqual(mgr.get("model"), DEFAULT_SETTINGS["model"])


# ──────────────────────────────────────────────────────────────────────
# AIClient tests
# ──────────────────────────────────────────────────────────────────────


class TestAIClient(unittest.TestCase):
    def _make_settings(self):
        s = MagicMock()
        s.get = MagicMock(
            side_effect=lambda key, default=None: {
                "api_key": "sk-test",
                "api_base_url": "https://api.openai.com/v1",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 100,
                "prompt": "请润色：",
            }.get(key, default)
        )
        return s

    def test_polish_text_calls_on_success(self):
        from app.ai_client import AIClient

        settings = self._make_settings()
        client = AIClient(settings)

        # Mock OpenAI client response
        mock_choice = MagicMock()
        mock_choice.message.content = "润色后的文字"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        done = threading.Event()
        results = []

        def on_success(text):
            results.append(text)
            done.set()

        with patch("app.ai_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_instance

            client.polish_text("原始文字", on_success)
            done.wait(timeout=5)

        self.assertEqual(results, ["润色后的文字"])

    def test_polish_text_calls_on_error_on_exception(self):
        from app.ai_client import AIClient

        settings = self._make_settings()
        client = AIClient(settings)

        done = threading.Event()
        errors = []

        def on_error(msg):
            errors.append(msg)
            done.set()

        with patch("app.ai_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.side_effect = RuntimeError("API error")
            MockOpenAI.return_value = mock_instance

            client.polish_text("text", lambda x: None, on_error)
            done.wait(timeout=5)

        self.assertEqual(len(errors), 1)
        self.assertIn("API error", errors[0])

    def test_polish_text_falls_back_to_on_success_when_no_error_cb(self):
        from app.ai_client import AIClient

        settings = self._make_settings()
        client = AIClient(settings)

        done = threading.Event()
        results = []

        def on_success(text):
            results.append(text)
            done.set()

        with patch("app.ai_client.OpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.side_effect = RuntimeError("oops")
            MockOpenAI.return_value = mock_instance

            client.polish_text("text", on_success)
            done.wait(timeout=5)

        self.assertEqual(len(results), 1)
        self.assertIn("[错误]", results[0])


# ──────────────────────────────────────────────────────────────────────
# TextHandler tests (non-Windows, no real Win32 calls)
# ──────────────────────────────────────────────────────────────────────


class TestTextHandler(unittest.TestCase):
    def test_has_target_false_initially(self):
        from app.text_handler import TextHandler

        th = TextHandler()
        self.assertFalse(th.has_target)

    def test_no_crash_on_non_windows(self):
        """TextHandler methods should not raise on non-Windows platforms."""
        from app.text_handler import TextHandler

        th = TextHandler()
        text = th.capture_text()  # should return ""
        self.assertEqual(text, "")
        result = th.replace_text("hello")  # should return False
        self.assertFalse(result)

    def test_target_window_title_empty_without_target(self):
        from app.text_handler import TextHandler

        th = TextHandler()
        self.assertEqual(th.target_window_title(), "")


# ──────────────────────────────────────────────────────────────────────
# MODEL_PRESETS sanity checks
# ──────────────────────────────────────────────────────────────────────


class TestModelPresets(unittest.TestCase):
    def test_all_presets_have_model_and_url(self):
        from app.settings_manager import MODEL_PRESETS

        for name, preset in MODEL_PRESETS.items():
            if name == "自定义":
                continue
            self.assertIn("model", preset, f"{name} missing 'model'")
            self.assertIn("api_base_url", preset, f"{name} missing 'api_base_url'")
            self.assertTrue(preset["model"], f"{name} has empty model")
            self.assertTrue(preset["api_base_url"], f"{name} has empty api_base_url")

    def test_custom_preset_exists(self):
        from app.settings_manager import MODEL_PRESETS

        self.assertIn("自定义", MODEL_PRESETS)

    def test_default_settings_model_matches_a_preset(self):
        from app.settings_manager import DEFAULT_SETTINGS, MODEL_PRESETS

        default_model = DEFAULT_SETTINGS["model"]
        models_in_presets = [v.get("model") for v in MODEL_PRESETS.values()]
        self.assertIn(default_model, models_in_presets)


if __name__ == "__main__":
    unittest.main()
