"""
AI client for Politeness Auto Refiner.
Uses the OpenAI-compatible API interface, supporting GPT, DeepSeek, Qwen, etc.
"""
import threading
from typing import Callable, Optional

from openai import OpenAI


class AIClient:
    """Wrapper around the OpenAI-compatible API for text polishing."""

    def __init__(self, settings_manager):
        self.settings = settings_manager

    def _make_client(self) -> OpenAI:
        api_key = self.settings.get("api_key", "")
        base_url = self.settings.get("api_base_url", "https://api.openai.com/v1")
        return OpenAI(api_key=api_key, base_url=base_url)

    def polish_text(
        self,
        text: str,
        on_success: Callable[[str], None],
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Polish the given text asynchronously.

        Calls on_success(refined_text) on completion, or on_error(message) on failure.
        The callbacks are invoked from a background thread; callers should use
        Qt signals/slots to safely update the UI.
        """

        def _run():
            try:
                client = self._make_client()
                prompt = self.settings.get("prompt", "")
                model = self.settings.get("model", "gpt-3.5-turbo")
                temperature = float(self.settings.get("temperature", 0.7))
                max_tokens = int(self.settings.get("max_tokens", 1000))

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{prompt}\n{text}",
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                refined = response.choices[0].message.content or ""
                on_success(refined)
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                if on_error:
                    on_error(msg)
                else:
                    on_success(f"[错误] {msg}")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
