"""
Settings manager for Politeness Auto Refiner.
Persists configuration to a JSON file in the user's AppData directory.
"""
import json
import os
from pathlib import Path

DEFAULT_SETTINGS = {
    "model": "gpt-3.5-turbo",
    "api_key": "",
    "api_base_url": "https://api.openai.com/v1",
    "prompt": "你是一个研究生，正在给王老师发消息，请你使用礼貌性的语气润色以下消息：",
    "temperature": 0.7,
    "max_tokens": 1000,
}

# Predefined model presets with their base URLs
MODEL_PRESETS = {
    "OpenAI - GPT-3.5 Turbo": {
        "model": "gpt-3.5-turbo",
        "api_base_url": "https://api.openai.com/v1",
    },
    "OpenAI - GPT-4o": {
        "model": "gpt-4o",
        "api_base_url": "https://api.openai.com/v1",
    },
    "OpenAI - GPT-4 Turbo": {
        "model": "gpt-4-turbo",
        "api_base_url": "https://api.openai.com/v1",
    },
    "DeepSeek - deepseek-chat": {
        "model": "deepseek-chat",
        "api_base_url": "https://api.deepseek.com/v1",
    },
    "通义千问 - qwen-turbo": {
        "model": "qwen-turbo",
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "通义千问 - qwen-plus": {
        "model": "qwen-plus",
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "通义千问 - qwen-max": {
        "model": "qwen-max",
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "自定义": {
        "model": "",
        "api_base_url": "",
    },
}


class SettingsManager:
    """Manages application settings with JSON persistence."""

    def __init__(self):
        if os.name == "nt":
            app_data = os.environ.get("APPDATA", Path.home())
        else:
            app_data = Path.home() / ".config"
        self.config_dir = Path(app_data) / "PolitenessRefiner"
        self.config_file = self.config_dir / "config.json"
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Load settings from disk."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.settings.update(saved)
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def save(self):
        """Persist settings to disk."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def update(self, new_settings: dict):
        self.settings.update(new_settings)
        self.save()
